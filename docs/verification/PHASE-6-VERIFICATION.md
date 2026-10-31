# Phase 6 — Patient timezone interaction and schedule-conflict UX

## Scope

This phase verifies the two SlotZero bug fixes:

1. Patients can change their timezone from the dashboard using an accessible
   dropdown. The authenticated session controls whose profile is updated.
2. Doctor schedule and blocked-period conflicts identify the exact confirmed
   appointment and link back to its doctor-local calendar date without
   bypassing conflict protection.

## Implementation evidence

- `slotzero-mvp/app.py`
  - Added `POST /patient/timezone` with role, CSRF, and allowlist checks.
  - Preserved appointment `start_utc` and `end_utc` during profile updates.
  - Added doctor-local appointment details and calendar routing to conflict
    feedback.
  - Kept conflict checks inside the existing immediate transaction.
- `slotzero-mvp/templates/patient_dashboard.html`
  - Added keyboard-accessible timezone trigger, supported-zone options, and
    saving/feedback states.
- `slotzero-mvp/static/app.js`
  - Added dropdown open/close behavior, outside-click and Escape handling,
    duplicate-submission protection, and reload after a successful save.
- `slotzero-mvp/static/styles.css`
  - Added dropdown, focus, saving, spinner, and feedback styling.
- `slotzero-mvp/tests/test_timezone_and_schedule_conflicts.py`
  - Added regression coverage for timezone persistence/display/authorization
    and schedule conflict identification/resolution.

## Verification commands

```powershell
cd "slotzero-mvp"
python -m py_compile app.py tests\test_timezone_and_schedule_conflicts.py
python -m pytest -q
```

## Results

- Focused timezone and conflict tests: **3 passed**.
- Full regression suite: **175 passed, 1 warning**.
- Warning: Starlette's `anyio.abc.BlockingPortal` compatibility alias is
  deprecated; this is emitted by the installed dependency and is unrelated to
  the changes.

## Explicit invariants verified

- Patient timezone updates use the authenticated session and reject unsupported
  zones.
- Logout/login and page reload retain the selected timezone.
- Appointment UTC start/end values remain unchanged while rendered local times
  change.
- Confirmed appointments continue to block schedule and blocked-period changes.
- Conflict feedback includes appointment identity, patient, doctor-local date
  and time, and a route to the relevant doctor calendar date.
- Once all affected confirmed appointments are legitimately cancelled, the
  schedule update succeeds.
