# Phase 1 — MVP stabilization and rescheduling repair

Date: 2026-10-31 (Asia/Calcutta). Phase 0 approved by the Phase 1 task request.

## Investigation and changes

The patient dashboard links to `GET /appointments/{appointment_id}/reschedule`.
That route checks the patient role, queries the owned appointment with its doctor,
checks eligibility, selects a doctor-local calendar date, generates replacement
slots excluding the current appointment, and renders `reschedule.html`. Each slot
form posts a UTC start and CSRF token to the same route. The POST revalidates
ownership/eligibility and availability inside an immediate write transaction,
updates the same appointment and writes its audit event before redirecting.

The GET query selected `d.timezone AS doctor_timezone`, but `d` is the `doctors`
profile table and has no timezone column. The joined `users` table (`u`) owns that
field. This raised `sqlite3.OperationalError: no such column: d.timezone` before
the form could render. Other inspected doctor lookups use `u.timezone`; this
incorrect column reference appeared only in the reschedule GET. Existing tests
exercised the POST without opening the form, so the original eight passed.

Changed only that selected column to `u.timezone`, preserving joins, ownership
filter, alias, dates, template and POST contract.

A further route test found `flash_redirect` always appended `?notice=` even when
the path already contained `?date=`. Rejected replacement bookings therefore
redirected to a malformed date parameter and lost their intended error notice.
The helper now chooses `&` when the path already has a query. The test follows
the redirect and verifies that the actual rendered page displays the rejection.
This helper change also corrects other existing query-bearing notice redirects;
no template or appointment-write logic was changed.

## Tests and evidence

New `tests/test_reschedule.py` uses a pytest fixture with a temporary database,
fixed UTC clock, application lifespan startup, real authenticated TestClient
sessions, configured doctor hours and two bookings created through the booking
route. It does not use or modify the application's regular database.

1. Before the SQL fix, the focused page test failed at `reschedule_page` with
   `sqlite3.OperationalError: no such column: d.timezone` (1 failed).
2. After the SQL fix, the full suite yielded 11 passed / 1 failed: the new
   rendered-error assertion exposed the malformed notice redirect described above.
3. After the separator fix, `py -m pytest -q -p no:cacheprovider` yielded
   **12 passed, 0 failed, 1 warning in 2.59s**. This includes all eight original
   tests unchanged and four new test cases.

New cases verify the correct appointment, doctor timezone, default doctor-local
date, replacement form and available slot rendering, exclusion of another booking,
rejection of occupied/malformed replacement starts, understandable rendered error
messages, invalid calendar date handling, nonexistent appointment 404, and another
patient's GET/POST denial. Full appointment and event snapshots stay unchanged
after failed moves and read-only/error/access requests. Existing tests retain
successful rescheduling, audit events, cancellation and concurrent booking checks.

One warning remains: Starlette TestClient uses the deprecated AnyIO
`BlockingPortal` alias. No tests were skipped, removed or downgraded.
TestClient exercised the real local ASGI application and HTML rendering with
startup/shutdown; no separate listening server or browser was launched.

## Dependencies and limitations

Installed versions were rechecked: FastAPI 0.139.2 versus pin 0.128.2,
pytest 9.0.3 versus pin 9.0.2, python-multipart 0.0.29 versus pin 0.0.20;
Starlette 1.2.0 is installed and httpx is 0.28.1. These differ from the historical
artifact environment. The reproduced error is a nonexistent SQL column and the
second defect is URL construction; neither requires dependency changes. No
dependencies were installed/upgraded and exact pinned-environment compatibility
has not been established. Keep environment reproducibility as a separate task.

The original Participant Brief remains missing. Tests preserve existing behavior
and do not claim independent verification of official requirements. Reschedule
cutoff policy, patient-local date-search semantics, broader timezone/DST coverage,
public-demo authentication hardening and deployment persistence remain open as
recorded in Phase 0. No formal Brain exists; this document records current progress,
verification and outstanding decisions without creating a competing hierarchy.

## Files and Git review

- Modified `slotzero-mvp/app.py`: timezone column and redirect separator only.
- Added `slotzero-mvp/tests/test_reschedule.py`: focused fixture and regression cases.
- Updated root `README.md`: current status and verification link.
- Added this verification record; Phase 0 remains a historical audit.

The application diff was compared against a pre-edit temporary snapshot because
the existing MVP is untracked. New tests and documentation were reviewed in full;
tracked and no-index whitespace checks were performed. No secrets or unrelated
preparation/backup changes were added. No commit, staging or push was performed,
as explicitly required by the Phase 1 request. Branch remains `master` at
`6aa6a74`; existing untracked app/docs/preparation remain untracked.

## Next permitted action

Before further feature work, obtain the official brief, reconcile the open policy
decisions and reproduce the pinned runtime in isolation. Then follow Phase 0's
Phase 2 plan: verify sessions, CSRF, role/ownership boundaries, operator doctor
provisioning and doctor schedules/blocks as complete workflows. Phase 2 has not
started and requires user approval.
