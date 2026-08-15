#!/usr/bin/env bash
# TWS/HWA interactive session guard for conman and composer.
#
# Usage:
#   ./tws_guard.sh conman [args...]
#   ./tws_guard.sh composer [args...]
#
# Or create symlinks named conman_guard / composer_guard and call them directly.
#
# Goal: if the interactive session/TTY disappears or this wrapper dies,
# terminate the guarded TWS process instead of allowing it to remain orphaned.
#
# Requirements: Linux (/proc mounted), bash, GNU coreutils (fractional sleep).
#
# Limitations (by design):
#   - Only the direct child (conman/composer) is guarded; processes it may
#     spawn are out of scope.
#   - If the wrapper is killed with SIGKILL the watchdog still terminates the
#     child, but the pidfile in ${TMPDIR:-/tmp} can be left behind.
#   - TTY-loss detection is heuristic: deleted /dev/pts fds 0-2 or tty_nr == 0.
#
# Changelog (hardened 2026-08-14):
#   - FIX (critical): arguments are now forwarded to conman/composer also when
#     the script is invoked directly ("./tws_guard.sh conman -optfile x ...");
#     previously they were silently dropped unless called via symlink.
#   - FIX: source "$TWA_ENV_FILE" with 'set +u' so third-party env files that
#     reference unset variables no longer kill the wrapper.
#   - Hardening: zombie-aware liveness checks (a zombie is treated as gone),
#     avoiding false "still_running" alarms and useless SIGKILL escalations.
#   - Hardening: "${ARGS[@]+...}" expansion keeps 'set -u' safe on bash < 4.4.
#   - Hardening: signal handlers wait up to 2s for the child identity and log
#     CRIT if it never appears; watchdog logs when it gives up waiting.

set -u

CHECK_INTERVAL="${TWS_GUARD_CHECK_INTERVAL:-2}"
TERM_GRACE="${TWS_GUARD_TERM_GRACE:-3}"
TWA_ENV_FILE="${TWA_ENV_FILE:-/opt/hwa/wa/twa_env.sh}"
LOG_TAG="tws_guard"

PIDFILE=""
WATCHDOG_PID=""
CHILD_PID=""
CHILD_START=""
APP=""
BIN=""
ORIGINAL_TTY=""
WRAPPER_START=""
HAD_TTY="no"

log_msg() {
    local level="$1"; shift
    logger -t "$LOG_TAG" -p "user.${level}" -- "$*" 2>/dev/null || true
}

usage() {
    cat <<'USAGE' >&2
Usage:
  tws_guard.sh conman [arguments...]
  tws_guard.sh composer [arguments...]

Optional symlinks:
  conman_guard   -> tws_guard.sh
  composer_guard -> tws_guard.sh

Environment variables:
  TWS_GUARD_CHECK_INTERVAL  Watchdog interval in seconds (default: 2)
  TWS_GUARD_TERM_GRACE      Seconds to wait after SIGTERM (default: 3)
  TWA_ENV_FILE              TWS environment file (default: /opt/hwa/wa/twa_env.sh)
USAGE
}

resolve_app() {
    local invoked_as
    invoked_as="$(basename -- "$0")"

    case "$invoked_as" in
        conman_guard)
            APP="conman"
            ;;
        composer_guard)
            APP="composer"
            ;;
        *)
            if [ "$#" -lt 1 ]; then
                usage
                exit 2
            fi
            APP="$1"
            shift
            ;;
    esac

    # Always forward the remaining arguments to the guarded binary.
    ARGS=("$@")

    case "$APP" in
        conman|composer) ;;
        *)
            echo "ERROR: only 'conman' and 'composer' are allowed." >&2
            exit 2
            ;;
    esac

    BIN="$(type -P "$APP" 2>/dev/null || true)"

    if [ -z "$BIN" ] && [ -r "$TWA_ENV_FILE" ]; then
        # Third-party env files may reference unset variables; do not let
        # 'set -u' abort the wrapper while sourcing them.
        set +u
        # shellcheck disable=SC1090
        . "$TWA_ENV_FILE"
        set -u
        BIN="$(type -P "$APP" 2>/dev/null || true)"
    fi

    if [ -z "$BIN" ]; then
        echo "ERROR: '$APP' not found in PATH, even after trying $TWA_ENV_FILE" >&2
        exit 127
    fi
}

process_starttime() {
    local pid="$1"
    [ -r "/proc/$pid/stat" ] || return 1
    awk '
        {
            line = $0
            if (!sub(/^[0-9]+ \(.+\) /, "", line)) exit 1
            count = split(line, field, / +/)
            if (count < 20) exit 1
            print field[20]
        }
    ' "/proc/$pid/stat" 2>/dev/null
}

process_tty_nr() {
    local pid="$1"
    [ -r "/proc/$pid/stat" ] || return 1
    awk '
        {
            line = $0
            if (!sub(/^[0-9]+ \(.+\) /, "", line)) exit 1
            count = split(line, field, / +/)
            if (count < 5) exit 1
            print field[5]
        }
    ' "/proc/$pid/stat" 2>/dev/null
}

process_state() {
    local pid="$1"
    [ -r "/proc/$pid/stat" ] || return 1
    awk '
        {
            line = $0
            if (!sub(/^[0-9]+ \(.+\) /, "", line)) exit 1
            count = split(line, field, / +/)
            if (count < 1) exit 1
            print field[1]
        }
    ' "/proc/$pid/stat" 2>/dev/null
}

same_process() {
    local pid="$1"
    local expected_start="$2"
    local current
    current="$(process_starttime "$pid" 2>/dev/null || true)"
    [ -n "$current" ] && [ "$current" = "$expected_start" ]
}

# A zombie still matches same_process (same starttime) but is already dead;
# treat it as gone so we do not escalate to SIGKILL or log false alarms.
process_gone_or_zombie() {
    local pid="$1"
    local expected_start="$2"
    local state
    same_process "$pid" "$expected_start" || return 0
    state="$(process_state "$pid" 2>/dev/null || true)"
    [ "$state" = "Z" ] || [ "$state" = "X" ]
}

load_identity() {
    local identity_file="$1"
    local pid start extra

    [ -s "$identity_file" ] || return 1
    IFS=' ' read -r pid start extra < "$identity_file" || return 1
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    [[ "$start" =~ ^[0-9]+$ ]] || return 1
    [ -z "${extra:-}" ] || return 1

    LOADED_PID="$pid"
    LOADED_START="$start"
}

load_identity_retry() {
    local identity_file="$1"
    local max_attempts="${2:-20}"
    local attempts=0

    while ! load_identity "$identity_file"; do
        attempts=$((attempts + 1))
        [ "$attempts" -ge "$max_attempts" ] && return 1
        sleep 0.1
    done
}

validate_settings() {
    [[ "$CHECK_INTERVAL" =~ ^[1-9][0-9]*$ ]] && [ "$CHECK_INTERVAL" -le 60 ] || {
        echo "ERROR: TWS_GUARD_CHECK_INTERVAL must be an integer from 1 to 60." >&2
        exit 2
    }
    [[ "$TERM_GRACE" =~ ^[0-9]+$ ]] && [ "$TERM_GRACE" -le 300 ] || {
        echo "ERROR: TWS_GUARD_TERM_GRACE must be an integer from 0 to 300." >&2
        exit 2
    }
}

check_pty_deleted() {
    local pid="$1"
    for fd in 0 1 2; do
        if readlink "/proc/$pid/fd/$fd" 2>/dev/null | grep -q "/dev/pts/.* (deleted)"; then
            return 0
        fi
    done
    return 1
}

terminate_guarded_process() {
    local pid="$1"
    local expected_start="$2"
    local reason="$3"

    process_gone_or_zombie "$pid" "$expected_start" && return 0

    log_msg warning "action=terminate app=$APP pid=$pid reason=$reason signal=TERM"
    if ! kill -TERM "$pid" 2>/dev/null; then
        log_msg err "action=terminate_failed app=$APP pid=$pid reason=$reason signal=TERM"
        return 1
    fi

    local waited=0
    while ! process_gone_or_zombie "$pid" "$expected_start"; do
        if [ "$waited" -ge "$TERM_GRACE" ]; then
            process_gone_or_zombie "$pid" "$expected_start" && return 0
            log_msg err "action=terminate app=$APP pid=$pid reason=$reason signal=KILL"
            if ! kill -KILL "$pid" 2>/dev/null; then
                log_msg err "action=terminate_failed app=$APP pid=$pid reason=$reason signal=KILL"
                return 1
            fi
            sleep 0.1
            if ! process_gone_or_zombie "$pid" "$expected_start"; then
                log_msg err "action=still_running app=$APP pid=$pid reason=$reason"
                return 1
            fi
            return 0
        fi
        sleep 1
        waited=$((waited + 1))
    done
}

watchdog() {
    local wrapper_pid="$1"
    local wrapper_start="$2"
    local pidfile="$3"
    local had_tty="$4"

    trap '' HUP INT QUIT

    local child=""
    local child_start=""
    local loops=0
    local tty_errors=0

    while [ -z "$child" ]; do
        if load_identity "$pidfile"; then
            child="$LOADED_PID"
            child_start="$LOADED_START"
            break
        fi

        loops=$((loops + 1))
        if [ "$loops" -ge 30 ]; then
            log_msg warning "event=watchdog_no_identity app=$APP wrapper_pid=$wrapper_pid"
            exit 0
        fi
        sleep 0.2
    done

    while ! process_gone_or_zombie "$child" "$child_start"; do
        if ! same_process "$wrapper_pid" "$wrapper_start"; then
            terminate_guarded_process "$child" "$child_start" "wrapper_gone"
            exit 0
        fi

        if [ "$had_tty" = "yes" ]; then
            if check_pty_deleted "$child"; then
                terminate_guarded_process "$child" "$child_start" "pty_deleted"
                exit 0
            fi

            local tty_now=""
            if tty_now="$(process_tty_nr "$child")"; then
                tty_errors=0
                if [ "$tty_now" = "0" ]; then
                    terminate_guarded_process "$child" "$child_start" "tty_lost"
                    exit 0
                fi
            else
                tty_errors=$((tty_errors + 1))
                if [ "$tty_errors" -ge 3 ]; then
                    log_msg err "event=tty_check_failed app=$APP pid=$child"
                    tty_errors=0
                fi
            fi
        fi

        sleep "$CHECK_INTERVAL"
    done
}

on_hup() {
    log_msg warning "event=wrapper_signal app=$APP wrapper_pid=$$ signal=HUP"
    if load_identity_retry "$PIDFILE"; then
        terminate_guarded_process "$LOADED_PID" "$LOADED_START" "wrapper_hup" || true
    else
        log_msg crit "event=no_identity app=$APP wrapper_pid=$$ signal=HUP action=exit_without_terminate"
    fi
    exit 129
}

on_term() {
    log_msg warning "event=wrapper_signal app=$APP wrapper_pid=$$ signal=TERM"
    if load_identity_retry "$PIDFILE"; then
        terminate_guarded_process "$LOADED_PID" "$LOADED_START" "wrapper_term" || true
    else
        log_msg crit "event=no_identity app=$APP wrapper_pid=$$ signal=TERM action=exit_without_terminate"
    fi
    exit 143
}

cleanup() {
    if [ -n "$WATCHDOG_PID" ]; then
        kill -TERM "$WATCHDOG_PID" 2>/dev/null || true
    fi
    [ -n "$PIDFILE" ] && rm -f -- "$PIDFILE"
}

main() {
    ARGS=()
    validate_settings
    resolve_app "$@"

    WRAPPER_START="$(process_starttime "$$" 2>/dev/null || true)"
    [ -n "$WRAPPER_START" ] || {
        echo "ERROR: Linux /proc is required." >&2
        exit 1
    }

    local wrapper_tty_nr
    wrapper_tty_nr="$(process_tty_nr "$$" 2>/dev/null || true)"
    if [ -n "$wrapper_tty_nr" ] && [ "$wrapper_tty_nr" != "0" ]; then
        ORIGINAL_TTY="$(tty 2>/dev/null || true)"
        [ -n "$ORIGINAL_TTY" ] || ORIGINAL_TTY="attached"
        HAD_TTY="yes"
    else
        ORIGINAL_TTY="none"
        HAD_TTY="no"
    fi

    PIDFILE="$(mktemp "${TMPDIR:-/tmp}/tws_guard.${APP}.XXXXXX")" || exit 1
    chmod 600 "$PIDFILE" || exit 1

    trap on_hup HUP
    trap on_term TERM
    trap ":" INT QUIT
    trap cleanup EXIT

    log_msg notice "event=start app=$APP wrapper_pid=$$ user=$(id -un) tty=$ORIGINAL_TTY bin=$BIN"

    watchdog "$$" "$WRAPPER_START" "$PIDFILE" "$HAD_TTY" </dev/null >/dev/null 2>&1 &
    WATCHDOG_PID=$!

    (
        child_start="$(process_starttime "$BASHPID" 2>/dev/null || true)"
        [ -n "$child_start" ] || exit 125
        printf '%s %s\n' "$BASHPID" "$child_start" > "$PIDFILE"
        # ${ARGS[@]+...}: safe with 'set -u' on bash < 4.4 when ARGS is empty.
        exec "$BIN" ${ARGS[@]+"${ARGS[@]}"}
    ) <&0 >&1 2>&2 &
    CHILD_PID=$!

    local rc=0
    while :; do
        wait "$CHILD_PID"
        rc=$?

        if load_identity "$PIDFILE"; then
            CHILD_START="$LOADED_START"
            same_process "$CHILD_PID" "$CHILD_START" || break
        else
            kill -0 "$CHILD_PID" 2>/dev/null || break
        fi
    done

    log_msg notice "event=exit app=$APP child_pid=${CHILD_PID:-unknown} rc=$rc"

    return "$rc"
}

main "$@"
