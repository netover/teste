# Testing Strategy

This document outlines the testing strategy for the HWA Neuromorphic Dashboard project, focusing on best practices established during the resolution of testing framework conflicts.

## 1. Overview

The project uses `pytest` as its primary test runner. The test suite is divided into several categories:
-   **Unit Tests** (`tests/unit/`): For testing individual components in isolation.
-   **Integration Tests** (`tests/integration/`): For testing the interaction between multiple components.
-   **End-to-End (E2E) Tests** (`tests/e2e/`): For testing the full application stack from the user's perspective, using Playwright.

## 2. The `pytest-asyncio` vs. `pytest-xprocess` Conflict

A critical technical challenge was identified during development: a fundamental conflict between the `pytest-asyncio` and `pytest-xprocess` plugins.

-   **`pytest-asyncio`** is used to run `async` test functions.
-   **`pytest-xprocess`** is used to run the FastAPI backend server in a separate process for E2E and some integration tests.

When tests that require the `backend_server` fixture (and thus `pytest-xprocess`) are run in the same `pytest` session as tests that use `async` functions (and thus `pytest-asyncio`), an event loop conflict occurs. This leads to `RuntimeError: Runner.run() cannot be called from a running event loop` and causes the test suite to fail unpredictably.

## 3. The Solution: Separated Test Runs

To resolve this conflict and ensure a stable and reliable testing process, the test suite **must** be executed in two separate, isolated groups.

### Group 1: Non-Server-Dependent Tests

This group includes all unit tests and integration tests that do not require a live backend server process. They can be run together without issue.

**Command:**
```bash
python -m pytest tests/unit/ tests/integration/monitoring/ tests/integration/database/
```

### Group 2: Server-Dependent Tests

This group includes all tests that depend on the `backend_server` fixture, which starts a live server process.

**Command:**
```bash
python -m pytest tests/e2e/ tests/integration/api/ tests/integration/ml/
```

By separating the runs, we ensure that the `pytest-xprocess` event loop management does not interfere with the `pytest-asyncio` event loop management. This is the official testing doctrine for this project until a more advanced solution (e.g., containerized test runners) is implemented.
