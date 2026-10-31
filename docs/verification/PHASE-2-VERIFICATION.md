# Phase 2 — Authorization and doctor configuration verification

Date: 2026-10-31 (Asia/Calcutta). Scope authorized by the supplied Phase 2 task.
Phase 3 has not started. No commit, staging, push, deployment, migration or package
installation was performed.

## Authority and baseline

Read root AGENTS.md, Phase 0 and Phase 1 reports, existing security, scheduling,
schema, route, user-guide and decision documents, application routes, templates,
provisioning script and tests. The original
`docs/reference/SlotZero_Participant_Brief.pdf` is missing, and no alternate brief
was found in the repository filename search. Requirements here come from the
user's supplied implementation reference. No formal Brain exists; current context
continues in the existing root docs rather than a competing hierarchy.

Baseline: **12 passed, 1 warning in 2.89s**. Repository remains on `master` at
`6aa6a74`. Contrary to the historical shorthand, the entire application is
untracked, not merely a tracked app with Phase 1 modifications. A pre-edit copy
was retained outside the repository for comparison. Existing user work was kept.

## Authorization audit

- Email/password authentication verifies salted scrypt hashes. Doctor accounts
  come from initial demo provisioning or the operator CLI; public signup inserts
  `patient` in SQL regardless of submitted role. Only doctor/patient roles exist.
- Login generates an opaque random cookie token. SQLite stores its SHA-256 hash,
  user ID, independent CSRF token and seven-day expiry. Every protected request
  joins the session to the current user row and checks expiry. Logout deletes the
  session. Cookie is HttpOnly, SameSite=Lax, with Secure controlled by configuration.
- All protected handlers depend on `require_user`; role-specific handlers call
  `require_role`. Identity and role come from the database-backed session. Extra
  client user/doctor/patient IDs do not change the actor.
- Patient dashboard/history queries filter by authenticated patient ID. Cancel
  and reschedule require ownership; foreign or nonexistent appointments return 404.
  Doctor dashboard, schedule writes, blocks and history use authenticated doctor
  ID. Block deletion includes both block ID and doctor ID in SQL.
- Doctor listing/profile/available slots are intentional patient-facing data.
  Doctor-private blocks, bookings and audit history are not exposed there.
- Authenticated mutations check session-bound CSRF. Missing fields return 422;
  incorrect tokens return 403. Anonymous/invalid/expired sessions redirect to login.
  Wrong roles return 403. PUT/PATCH/DELETE are not implemented and return 405.
- UI controls are not the only protection. Tests send direct HTTP requests with
  forged IDs/roles and another session's CSRF token. No confirmed role or ownership
  bypass was found, so the existing authorization architecture was retained.
- Deleting an absent/foreign block remains an idempotent no-op with the existing
  success redirect. The test confirms the other doctor's block remains intact.

## Existing functionality and focused changes

Already present: four required demo accounts and zones, doctor profiles, daily
booking/history views, per-doctor weekly schedules, split shifts, 15/30/60-minute
durations, same-day blocks, block deletion, ownership checks and transactional
booking-preserving conflict checks. Accounts were reused; restart does not reseed
a populated database. No admin role or additional account architecture was added.

Added/changed:

1. Dashboard displays the doctor's name, email, specialization and biography.
2. Doctor can select any of the three supported IANA zones. Zone, hours and duration
   save atomically. The proposed zone is used to validate active confirmed bookings
   before writing; rejected changes leave all records unchanged. Existing appointment
   and block UTC instants are preserved. Older forms omitting timezone retain the
   stored zone, preserving the existing route callers.
3. Schedule parser now rejects arbitrary weekday suffixes, non-HH:MM values,
   timezone-bearing clocks, fractions, incomplete comma lists and whitespace-only
   submissions. Previously some were silently accepted/truncated; mixed aware/naive
   clocks could cause a TypeError. Explicit empty day lines remain valid days off.
4. Blocks require HH:MM local clocks, preventing malformed mixed clock inputs from
   causing a server error. Current timezone is loaded within the immediate write
   transaction, so a concurrent zone update cannot leave conversion using stale
   pre-transaction session data. Past periods and DST gaps/folds remain rejected.
5. Block conflicts identify an affected appointment ID and explicitly preserve the
   booking. Existing redirect/error-notice semantics are retained (303, not 409).

These are configuration and input-validation defects/gaps, not a discovered
authorization bypass. No unrelated booking logic or Phase 1 fixes were replaced.

## Database audit

No schema change or migration was necessary. `users.timezone` already stores the
doctor's zone. Doctors have a user PK/FK; schedules have doctor FK plus composite
doctor/weekday PK; blocks and appointments reference doctors; appointments reference
patients and events reference appointment/actor. Session tokens have a primary key.
Every connection enables foreign keys. Existing duration, weekday, role, status,
positive-interval and idempotency constraints and appointment overlap triggers remain.
Doctor/status/time and patient/time indexes support booking queries; the composite
schedule key supports per-doctor lookup. No speculative indexes were added.

Tests confirm enabled foreign keys, clean `foreign_key_check` and `integrity_check`,
invalid role/duration/weekday and missing-doctor rejection, seed idempotence, preserved
bookings/events and cross-doctor isolation. All databases used were temporary.
No normal application database was created or modified.

Limits: FKs alone do not assert that a doctor profile's user has the doctor role or
that appointment patient_id refers to a patient-role user. Provisioning and HTTP
handlers enforce these invariants. Timezone allowlist and interval JSON validity
remain application-enforced. Direct operator SQL requires care. Block/session/event
indexes beyond existing keys can be evaluated with future volume; no migration or
rollback procedure is needed for this change.

## Verification and acceptance

Commands run from `slotzero-mvp`:

- Baseline `py -m pytest -q -p no:cacheprovider`: **12 passed**, 1 warning.
- Initial focused `py -m pytest tests/test_phase2.py -q -p no:cacheprovider`:
  **55 passed**, 1 warning in 34.61s.
- Final `py -m pytest -q -p no:cacheprovider`: **71 passed**, 1 warning in 37.44s
  after four additional cases and final implementation review. No skips or deletions.
- Separate Uvicorn process bound to loopback with a temporary database: `/health`
  returned 200 and expected JSON; `/login` returned 200 and rendered HTML form.
  Process was stopped afterward. TestClient also ran real application lifespan and
  rendered doctor/patient workflows, without dependency overrides for authentication.
- Reviewed app/template no-index diffs against the pre-edit snapshot, the new tests
  and documentation. Core and Phase 1 test-file hashes match the snapshot. The
  reschedule timezone query and query-bearing redirect separator remain intact.
- Tracked and untracked-file whitespace checks passed. No files were staged.

| Phase 2 acceptance criterion | Result / evidence |
|---|---|
| Server-side roles and protected access | Pass: anonymous, invalid/expired/revoked sessions, both wrong-role directions |
| Patients cannot manage schedules/blocks | Pass: direct mutations and forged role/identity fields denied |
| Doctors manage only own schedule | Pass: forged doctor_id cannot affect the other doctor's configuration |
| Appointment privacy and ownership | Pass: cross-patient GET/POST denied; doctor views/history restricted to self |
| Doctor profile/configuration view | Pass: rendered identity, settings and selected zone |
| Working days and split intervals | Pass: saved/reloaded intervals, closed days and generated slot counts |
| Supported durations | Pass: 15/30/60 for each zone; unsupported/non-numeric durations rejected |
| IANA timezone storage/validation | Pass: all three zones, invalid/fixed-offset identifiers rejected, legacy callers preserved |
| Invalid/incomplete schedules | Pass: invalid weekday/time/order/overlap/duplicates/empty/missing input rejected atomically |
| Blocked periods | Pass: own create/delete, past/invalid/DST input rejection, cross-doctor deletion isolation |
| Existing bookings preserved | Pass: block conflicts identify booking; rejected schedule/zone updates preserve data; successful updates retain instants |
| CSRF and manual methods | Pass: missing/forged/foreign tokens rejected; PUT/PATCH/DELETE return 405 |
| Phase 1 regressions | Pass: all original 12 tests retained and passing |

Every supplied Phase 2 acceptance criterion passed within this local automated
scope. This does not certify compliance with the missing original PDF.

## Runtime and dependencies

| Component | Observed | Requirements |
|---|---|---|
| Python | 3.14.4 | No Python pin |
| SQLite | 3.50.4 | Python bundled |
| FastAPI | 0.139.2 | 0.128.2 |
| Uvicorn | 0.48.0 | 0.48.0 |
| Jinja2 | 3.1.6 | 3.1.6 |
| pytest | 9.0.3 | 9.0.2 |
| httpx | 0.28.1 | 0.28.1 |
| python-multipart | 0.0.29 | 0.0.20 |
| tzdata | 2026.2 | >=2025.2 |
| Starlette | 1.2.0 | Transitive, not directly pinned |

The one warning is Starlette TestClient's deprecated AnyIO BlockingPortal alias.
No package or environment settings were changed. Tests establish the installed
environment only; a clean exact-pinned installation remains unverified.

## Files and context updates

- Modified `slotzero-mvp/app.py` and `templates/doctor_dashboard.html`.
- Added `slotzero-mvp/tests/test_phase2.py`, reusing the Phase 1 booking fixture
  and snapshot helper without rewriting or duplicating that infrastructure.
- Added this report; updated root `README.md`, `docs/INDEX.md`, route contracts,
  scheduling rules, security evidence, test record, user guide and traceability.
- No formal Brain was created/updated because the official brief remains missing.
  Existing root docs record current status, changes, tests, risks and next steps.
  Historical Phase 0/1 records and the app's older docs copy remain preserved;
  use root docs for current Phase 2 evidence.
- Git remains dirty on `master` at `6aa6a74`, with the pre-existing untracked app,
  docs and preparation material. Nothing committed or pushed.

## Remaining risks and next permitted action

Official requirement reconciliation is pending the PDF. No visual-browser,
accessibility, public deployment, comprehensive penetration or load test was run.
Demo credentials, absent login rate limiting and default non-Secure cookies remain
public-deployment limitations. SQLite remains the single-instance MVP persistence.
Blocks remain same-day; multi-day holidays require one block per day. The timezone
setting is limited to the three existing supported zones. No new cross-day UI or
arbitrary-zone support was inferred.

Recommended next: obtain/reconcile the brief and reproduce pinned dependencies in
isolation; then, on authorization, Phase 3 availability verification covering
patient-local date semantics, cross-zone boundaries and New York DST. Phase 3 was
not started, and the rescheduling cutoff assumption was not changed.
