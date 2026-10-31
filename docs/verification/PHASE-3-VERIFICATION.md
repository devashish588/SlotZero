# Phase 3 — Dynamic availability and conflict-free booking

Date: 2026-10-31 (Asia/Calcutta). Authorized scope is the user's Phase 3 instruction.
FastAPI, SQLite, existing forms, authentication and previous work are retained.
No commit, staging, push, deployment, migration or dependency installation occurred.

## Requirement reconciliation

Read AGENTS.md, all three earlier phase reports, scheduling/decision documents,
schema, connection/transaction helpers, availability and appointment handlers,
doctor configuration, patient forms, JavaScript and existing tests. The official
`docs/reference/SlotZero_Participant_Brief.pdf` remains missing. This matrix uses
the explicit Phase 3 requirements; no independent PDF reconciliation is claimed.

| Requirement | Existing implementation | Initial status | Phase 3 action |
|---|---|---|---|
| Dynamic availability | `_get_available_slots`, no stored slot results | Implemented | Retain; restrict occupancy reads to doctor-local date; test |
| Doctor working hours | Per-doctor weekday JSON ranges, split shifts | Implemented | Verify full containment and lunch-break boundaries |
| Appointment duration | `doctors.consultation_minutes`, 15/30/60 CHECK | Implemented | Verify all lengths and server-owned end time |
| Blocked periods | UTC periods, half-open overlap checks | Implemented | Verify partial/cross-day occupancy and stale-page rejection |
| Existing appointment conflicts | Only `confirmed` appointments occupy time | Implemented | Verify overlap/adjacency, cancellation reopening, INSERT/UPDATE triggers |
| Concurrent booking protection | WAL, immediate transaction, timeout, overlap triggers | Partial verification | Prove separate-process races; handle actual timeout errors |
| Duplicate submission protection | Form key and UNIQUE(patient_id,idempotency_key) | Implemented | Verify retries, changed payloads, cancellation and simultaneous duplicates |
| Past appointment rejection | Date check and start strictly after current UTC time | Implemented | Verify old dates, elapsed/current slots and clearer past-date message |

Additional findings: fractional request timestamps were silently truncated into
valid slots; a stale profile could be returned for a user no longer holding the
doctor role; the page did not distinguish no configured hours from a past date.
New tests reproduced these failures before the fixes.

## Existing versus changed functionality

Retained the existing generator, interval helper, IANA conversions, doctor-local
date selection, booking form and POST/redirect/GET workflow. The server derives
duration and end time from the stored doctor configuration; client patient IDs,
roles, duration and end-time fields cannot override the session or slot generator.
Only `confirmed` blocks availability; `cancelled` remains stored but releases time.

Changes in `app.py` and `templates/doctor_detail.html`:

- Doctor lookup now requires a matching doctor-role user and profile. There is no
  activation/deactivation field or workflow in this MVP. Existing doctor role plus
  profile is the available eligibility model; no new lifecycle was invented.
- Occupancy queries filter by doctor and the requested local calendar day's UTC
  bounds, rather than loading that doctor's entire history. They run once per
  generated day, not once per candidate slot. The upper query bound is inclusive
  through the day's last second, matching second-resolution UTC storage; actual
  conflict checks still use half-open intervals. Cross-midnight occupancy remains
  included when its end extends into the selected day.
- Booking rejects fractional-second input instead of rounding it into a different
  instant. Naive/malformed timestamps remain rejected; equivalent aware offsets
  referring to the same instant remain supported. Blank-only idempotency keys are
  rejected, and the existing 100-character limit remains.
- SQLITE_BUSY/SQLITE_LOCKED booking errors now produce a controlled retry notice
  after rollback instead of an unhandled lock exception. Other OperationalErrors
  still propagate, so unrelated database faults are not mislabeled as contention.
- Patient detail now distinguishes no configured hours, past dates and ordinary
  fully booked/unavailable days, without exposing private block reasons.
- The reschedule caller of the stricter shared doctor lookup now handles an
  unavailable doctor with an error notice and preserves the original appointment.
  Cancellation rules, rescheduling cutoff and rescheduling write logic are unchanged.

## Booking transaction and SQLite strategy

The application uses `sqlite3` directly, not an ORM. Each connection uses
`isolation_level=None`, so the context manager explicitly owns BEGIN/commit/rollback.
Connection timeout is 15 seconds and PRAGMA busy_timeout is 15000 milliseconds.
WAL mode and foreign keys are enabled on connections.

1. Validate authenticated patient role, session-bound CSRF, request key and aware
   timestamp. No client identity is used as the booking actor.
2. Open a new connection and execute `BEGIN IMMEDIATE` before the final read/write
   sequence. There is no nested pre-existing ORM transaction.
3. Check persisted patient/key idempotency state under the write lock.
4. Reload the doctor, duration and timezone. Regenerate requested-day availability
   using current hours, blocks, confirmed appointments and current time.
5. Match the requested instant to a generated slot; reject stale/unavailable input.
6. Insert appointment and its booked audit event, then commit together. Any failure
   rolls back. A forced audit-write failure test confirms no partial appointment.

SQLite serializes writers to the same database file, including separate processes.
The loser of an overlapping race waits, then regenerates availability after the
winner commits and receives the existing conflict redirect. INSERT and UPDATE
triggers independently reject overlapping confirmed intervals. No Python process
lock or browser-only check is used as the correctness mechanism. Schedule/block
writes already use immediate transactions as well.

Results follow existing server-rendered conventions: 303 success/error notices,
422 missing/typed-invalid fields, 403 wrong role/CSRF, protected-page login redirect,
404 missing doctor pages. This phase did not introduce a JSON API or replace form
redirects with 201/409 responses.

## Idempotency and data integrity

The existing form renders a request key once for the booking action; JavaScript
does not regenerate it on submit. Reposting the same form/body after a lost response
reuses the key. SQLite persists it on the appointment with a unique patient/key
constraint. Matching confirmed retries return an already-confirmed result without
another appointment or audit event. Reuse with another doctor/start is rejected.
Retrying a cancelled request does not resurrect it. Different patients have separate
key namespaces. Concurrent same-patient/key submissions were tested in separate
processes and persisted one appointment/event.

Page refresh creates a new form/action key; it is not the same idempotency request.
Overlap checks still protect the occupied slot. After rescheduling, an old payload
is rejected if it no longer matches the stored start; no duplicate is created.
No idempotency retention policy or independent request ledger was added.

No schema, index or data migration was needed. Existing appointment indexes,
constraints and triggers are retained. The configured local `slotzero.db` does not
exist; there were no regular database records to inspect or modify. Tests use the
real schema and seeded users in file-backed temporary databases. Database trigger
tests and integrity checks execute against those databases. No database was deleted
or recreated to apply changes.

## Tests and concurrent methodology

All new cases are in `slotzero-mvp/tests/test_phase3.py`, reusing the Phase 1 booking
fixture and Phase 2 authenticated accounts. Prior tests are unchanged.

- Baseline full suite: **71 passed, 0 failed, 1 warning in 41.50s**.
- Initial focused regression run before fixes: **5 failed, 5 passed**, one warning.
  Failures exposed timestamp truncation, an unhandled real lock timeout, stale
  doctor-role lookup and two missing empty-state explanations.
- Intermediate new suite: **31 passed**, one warning in 21.95s.
- Final focused Phase 3 suite: **37 passed, 0 failed, 1 warning in 27.39s**.
- Final full suite (`py -m pytest -q -p no:cacheprovider`): **108 passed, 0 failed,
  1 warning in 70.06s**. All 71 previous cases plus 37 new cases passed; no skips.

The 37 cases cover all durations, uneven split intervals, partial overlaps on both
sides, adjacency, real bookings and blocks, past/current times, cancellation
reopening, fully occupied/no-schedule days, normal conversions for all three zones,
same appointment instants on both dashboards, stale hours/duration/zone/block/booking
changes, invalid times/keys, forged identity/duration/end, repeated requests, database
INSERT/UPDATE overlap triggers and rollback when event insertion fails.

Critical races use Windows-compatible multiprocessing **spawn**, two distinct PIDs,
independent ASGI TestClients and independent SQLite connections to the same temporary
file. Parent creates real authenticated sessions; each child sends the session cookie
and CSRF token. A multiprocessing barrier in the connection's SQL trace callback
synchronizes both processes immediately before `BEGIN IMMEDIATE` attempts to acquire
the write lock. Both must report reaching that point. No shared in-memory connection
or global application lock serializes the race accidentally.

| Concurrent scenario | Exact outcome in focused run |
|---|---|
| Two patients, identical overlapping slot | One newly confirmed booking/event; one controlled unavailable error |
| Two patients, adjacent slots | Two newly confirmed bookings/events |
| Same patient's duplicate key/body, separate processes | One newly confirmed booking/event; one already-confirmed response |

All child processes exit successfully; every response is 303 with the asserted
semantic notice. An SQL self-join verifies zero overlapping confirmed appointments,
and `PRAGMA integrity_check` returns `ok`. The database overlap tests additionally
exercise different-start partial overlaps, not only identical intervals.

A separate real writer-lock test lowers timeout to 50ms **only on test connections**,
holds the lock, and verifies a controlled busy notice with no new appointment/event.
After release, retrying the same request succeeds. Production remains at 15 seconds.

## Startup, preservation and review

A separate Uvicorn process started on loopback with a new temporary DB. Real HTTP
GET `/health` returned 200 with expected JSON; `/login` returned 200 and rendered
the login form. The process was stopped. Patient and doctor booking workflows were
exercised with actual ASGI authentication, HTML rendering and temporary persistence.

Pre-edit snapshot is retained outside the repository. Byte comparisons confirm
`test_core.py`, `test_reschedule.py`, `test_phase2.py` and the Phase 2 doctor template
are unchanged. Phase 1's query and redirect fixes remain. Reviewed the app/template
diffs against that snapshot, new tests and documentation; performed Git whitespace
checks. No existing tests were deleted, skipped or weakened.

Files changed: application `app.py`, patient `templates/doctor_detail.html`, new
`tests/test_phase3.py`, root `README.md`, this report, docs index, scheduling rules,
route contracts, test verification and requirements traceability. Existing root
docs record project context; no formal Brain exists, and none is claimed updated.
Earlier phase reports and the app's historical docs copy are preserved.

Git remains on `master` at `6aa6a74`; the existing app/docs/preparation files remain
untracked and README remains modified. Nothing was staged, committed or pushed.

## Acceptance and remaining limits

Every supplied Phase 3 acceptance criterion passed in this local verification:
real schedules, correct duration/interval containment, block and confirmed-booking
exclusion, cancelled-slot reopening, adjacency, overlap rejection, transactional
revalidation, concurrent safety, idempotency, all previous tests and startup.
The result is 108 passing tests and successful live HTTP startup; it does not
certify requirements against the missing original PDF or prove unlimited-load behavior.

The official PDF is still missing. No activation flag was inferred. Patient dashboard
date-search semantics remain the documented open question; doctor detail dates remain
explicitly doctor-local. Comprehensive DST testing and unusual calendar extremes are
not claimed. Installed dependency/pin differences and the Starlette/AnyIO deprecation
warning remain; no environment changes were made. No browser visual/accessibility,
load, public deployment or filesystem/network-storage stress testing was performed.

Correctness assumes all app workers share the same SQLite file on storage with
working SQLite locks; separate database copies do not coordinate. Writer throughput
is serialized, and contention can return the bounded retry response. Existing
direct-SQL block writes are not protected by a block/appointment DB trigger; supported
HTTP writes use the protected transaction. Demo authentication and persistence
deployment limits from Phase 2 remain.

Recommended Phase 4: after authorization, verify cancellation/reschedule boundary
policies, concurrent lifecycle mutations and audit consistency; expand DST and
cross-zone date cases and reconcile the official brief. Do not migrate or deploy
without the relevant scope decision. Phase 4 has not started.
