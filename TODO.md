# Project TODO List

This file tracks the major features and tasks for the HWA Neuromorphic Dashboard application.

## Phase 1: Core Application & UI (Completed)
- [x] Initial research and project setup.
- [x] Basic Flask backend (`app.py`).
- [x] Initial frontend structure (`index.html`, `config.html`, `help.html`).
- [x] HWA API Connector (`hwa_connector.py`) with basic authentication.
- [x] Configuration page to save connection details.
- [x] System tray integration (`pystray`) for desktop-like experience.
- [x] Autostart with Windows functionality.

## Phase 2: Dynamic Dashboard & UI/UX Enhancements (In Progress)
- [x] **Task 2.1: Dynamic Widget Layout:** Implement a `dashboard_layout.json` to define widgets dynamically.
- [x] **Task 2.2: Draggable Widgets:** Use `SortableJS` to allow users to reorder widgets.
- [ ] **Task 2.3: Advanced Windowing System:**
    - [ ] Replace the basic modal pop-ups with a more robust windowing library (e.g., WinBox.js or similar).
    - [ ] Windows must be independently draggable, resizable, and minimizable.
    - [ ] Implement the "emerging from button" animation effect.
- [ ] **Task 2.4: Dynamic Dashboard Configuration UI:**
    - [ ] Create a UI for users to visually create, edit, and save their own `dashboard_layout.json` configurations.

## Phase 3: SDK Expansion & Actions (In Progress)
- [x] **Task 3.1: Cancel Job Action:**
    - [x] Implement `cancel_job` in the `HWAConnector`.
    - [x] Add the corresponding API endpoint in `app.py`.
    - [x] Add a "Cancel" button and logic to the frontend job detail view.
    - [x] Write an automated test to verify the feature.
- [ ] **Task 3.2: More SDK Actions:**
    - [ ] Systematically add more actions to the SDK (e.g., hold job, release job, rerun job).
    - [ ] Expose these actions through the backend and frontend as needed.

## Phase 4: Bug Fixes & Finalization
- [ ] **Task 4.1: Investigate Systray Icon Issue:**
    - [ ] Research and resolve why the systray icon may not be appearing correctly on the user's system.
    - [ ] Provide clear instructions for running the application to ensure tray functionality.
- [ ] **Task 4.2: Final Code Review and Cleanup:**
    - [ ] Address all feedback from code reviews.
    - [ ] Ensure the codebase is clean, commented, and well-documented.
    - [ ] Final round of testing.
