import logging
import re
import asyncio
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core import config
from src.hwa_connector import HWAClient
from src.security import get_api_key, load_key, decrypt_password

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


async def get_hwa_client():
    """
    Dependency to provide an initialized HWAClient.
    It now reads directly from the centralized config module.
    """
    if not config.HWA_HOSTNAME or not config.HWA_USERNAME:
        raise HTTPException(
            status_code=503,
            detail="HWA connection details are not configured in config.ini or environment variables.",
        )

    # Decrypt password if it exists
    decrypted_password = None
    if config.HWA_PASSWORD:
        try:
            key = load_key()
            decrypted_password = decrypt_password(
                config.HWA_PASSWORD.encode("utf-8"), key
            )
        except Exception as e:
            logging.error(f"Failed to decrypt HWA password: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to process HWA credentials."
            )

    try:
        client = HWAClient(
            hostname=config.HWA_HOSTNAME,
            port=config.HWA_PORT,
            username=config.HWA_USERNAME,
            password=decrypted_password,
        )
        async with client as active_client:
            yield active_client
    except Exception as e:
        logging.error(f"Failed to create HWAClient: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not connect to HWA.")


def is_oql_query_safe(query: str) -> bool:
    blocked_keywords = [
        "DELETE",
        "UPDATE",
        "INSERT",
        "CARRYFORWARD",
        "CANCEL",
        "HOLD",
        "RELEASE",
        "RERUN",
        "SUBMIT",
    ]
    for keyword in blocked_keywords:
        if re.search(r"\b" + keyword + r"\b", query, re.IGNORECASE):
            logging.warning(f"Blocked OQL query with keyword: {keyword}")
            return False
    return True


@router.get("/api/dashboard_data", tags=["HWA"])
@limiter.limit("120/minute")
async def get_dashboard_data(
    request: Request, client: HWAClient = Depends(get_hwa_client)
):
    # Use ExceptionGroup in Python 3.11+ for concurrent tasks
    try:
        results = await asyncio.gather(
            client.plan.query_job_streams(), client.model.query_workstations()
        )
        all_job_streams, all_workstations = results
    except Exception as e:
        logging.error(f"Error fetching dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard data.")

    jobs_abend = [j for j in all_job_streams if j.get("status", "").lower() == "abend"]
    jobs_running = [j for j in all_job_streams if j.get("status", "").lower() == "exec"]
    return {
        "abend_count": len(jobs_abend),
        "running_count": len(jobs_running),
        "total_job_stream_count": len(all_job_streams),
        "total_workstation_count": len(all_workstations),
        "job_streams": all_job_streams,
        "workstations": all_workstations,
        "jobs_abend": jobs_abend,
        "jobs_running": jobs_running,
    }


@router.get("/api/oql", tags=["HWA"], dependencies=[Depends(get_api_key)])
@limiter.limit("60/minute")
async def execute_oql(
    request: Request,
    q: str = Query(..., min_length=3, max_length=1024),
    source: str = "plan",
    client: HWAClient = Depends(get_hwa_client),
):
    if not is_oql_query_safe(q):
        raise HTTPException(
            status_code=400, detail="Query contains potentially harmful keywords."
        )

    if source == "model":
        return await client.model.execute_oql_query(q)
    return await client.plan.execute_oql_query(q)


async def _job_action_endpoint(
    action: str, plan_id: str, job_id: str, client: HWAClient
):
    action_map = {
        "cancel": client.plan.cancel_job,
        "rerun": client.plan.rerun_job,
        "hold": client.plan.hold_job,
        "release": client.plan.release_job,
    }
    if action not in action_map:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    result = await action_map[action](job_id, plan_id)
    return {
        "success": True,
        "message": f"'{action.capitalize()}' command sent.",
        "details": result,
    }


@router.put(
    "/api/plan/{plan_id}/job/{job_id}/action/{action}",
    tags=["HWA"],
    dependencies=[Depends(get_api_key)],
)
@limiter.limit("10/minute")
async def job_action(
    request: Request,
    plan_id: str,
    job_id: str,
    action: str,
    client: HWAClient = Depends(get_hwa_client),
):
    return await _job_action_endpoint(action, plan_id, job_id, client)
