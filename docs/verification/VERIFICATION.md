# Verification Record

> Historical initial verification record: the original eight-test result below is preserved. See [Phase 5](PHASE-5-VERIFICATION.md) for the current application verification reference and [repository organization](REPOSITORY-ORGANIZATION-REPORT.md) for this cleanup run.

Build-time checks executed in the artifact environment:

- Python: 3.13.5
- FastAPI: 0.128.2
- Starlette: 0.50.0
- Jinja2: 3.1.6
- Uvicorn: 0.48.0
- pytest: 9.0.2
- httpx: 0.28.1

## Automated tests

Command: `pytest -q`

Result: **8 passed**.

Coverage includes:

1. Split-shift weekly schedule parsing and overlapping-range validation.
2. DST nonexistent and ambiguous local-time rejection.
3. Conversion of a normal London local time to UTC.
4. Half-open interval behaviour (adjacent slots accepted, overlapping slots rejected).
5. Invalid dates and timezone-naive timestamps rejected.
6. Patient/doctor role separation and booking ownership checks.
7. Doctor schedule updates, rejection of a schedule change that would invalidate a confirmed booking, adding/removing blocks, and live availability recalculation.
8. Duplicate submission idempotency, database overlap trigger, and two simultaneous booking requests where exactly one confirmed appointment is stored.
9. Atomic rescheduling, cancellation, slot release, and appointment event records.

## Page smoke checks

FastAPI TestClient requests returned HTTP 200 for:

- `/login`
- `/register`
- `/patient/dashboard` after patient login
- `/doctors/{doctor_id}` after patient login
- `/doctor/dashboard` after doctor login

`python -m compileall -q app.py tests` completed successfully.

## Not verified

- A real Windows 11 / PowerShell installation.
- Deployment to a public hosting provider.
- Production multi-instance operation.
- External email, SMS, calendar or payment integrations (not implemented).
