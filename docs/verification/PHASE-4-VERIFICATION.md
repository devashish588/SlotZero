# Phase 4 — Appointment lifecycle and time-zone verification

Date: 2026-10-31 (Asia/Calcutta). Scope: the supplied Phase 4 request. FastAPI,
SQLite, existing sessions/forms, overlap triggers and prior phase changes remain.
No staging, commit, push, deployment, dependency installation or schema migration.

## Authority, inspection and plan

Read AGENTS.md, all four Phase 0–3 reports, current scheduling/product decisions,
route contracts, schema, lifecycle handlers, generator, dashboard views/templates,
and existing fixtures/tests. No nested AGENTS.md, formal Brain or participant PDF
was found in the repository. In particular,
`docs/reference/SlotZero_Participant_Brief.pdf` is still absent. Requirements here
come from the explicit Phase 4 request; PDF reconciliation is not claimed.

Initial Git: `master`, pre-existing modified README and untracked app/docs/workspace.
A pre-edit copy was retained outside the repository. No existing work was discarded.
Plan: reproduce 108-test baseline; inspect policy and transaction callers; close
lifecycle/audit/date gaps; add focused independent-connection and IANA tests; run
full regression and separate startup; inspect diffs and update existing root docs.
Affected code is limited to app.py and three appointment/search templates, with
one new regression file. No new documentation hierarchy or Brain was created.

## Cancellation policy and boundary

The existing authenticated, CSRF-protected patient handler verifies ownership and
confirmed status under `BEGIN IMMEDIATE`. It permits `start - server_now >= 2h`.
Exactly two hours is permitted. More than two hours is permitted. Less than two
hours, including half a second less, is rejected. Server `utc_now()` now retains
microseconds for policy evaluation; persisted timestamps remain UTC to the second.
Submitted client clocks/identity fields do not determine the decision.

Cancellation updates status and updated_at; it never deletes the appointment.
Actor, original start and event timestamp remain in the audit row; new event
details additionally preserve original start/end as JSON. Existing event rows
are unchanged. Availability excludes cancelled occupancy after commit. Repeated
cancellation returns an already-cancelled error notice with no second event.

Tests cover 7201, 7200, 7199 and 7199.5 seconds remaining, release, history,
foreign ownership/role/CSRF, rollback on audit failure, and concurrent duplicates.

## Atomic rescheduling and audit

Retained the same-row, same-ID transaction design. After `BEGIN IMMEDIATE`, reload
the owned confirmed appointment, check existing eligibility, reload doctor/zone,
generate availability excluding the original, and match the exact requested UTC
instant. Generation rechecks working hours, duration, blocks, confirmed occupancy
and future start. Only then update start/end and insert the audit event. Commit
both together; any write failure rolls back both. Failed replacements leave full
appointment/event snapshots identical. No cancel-then-create sequence exists.

Added fractional timestamp rejection consistent with booking. An identical
current start/end retry returns already-at-that-time without changing timestamps
or adding an event. New reschedule details store full old/new start/end intervals
as JSON in the existing details TEXT field. Old/new start columns still support
the existing history UI. Historical text details remain valid; no guessed end-time
backfill was attempted. Only overlap-trigger IntegrityErrors become unavailable
notices; unrelated integrity/operational faults propagate after rollback.

**Preserved product policy:** ADR-009 and the existing product/scheduling docs
explicitly apply the two-hour cutoff to rescheduling as an assumption requiring
product confirmation. This phase introduces no new restriction and retains/tests
that existing GET/POST policy, including exact equality. The official cancellation
wording alone does not establish this rescheduling policy. Product confirmation
or an authorized policy change remains a delivery decision.

## SQLite contention and concurrent methodology

Cancellation, rescheduling, block creation and block deletion now catch genuine
SQLITE_BUSY/SQLITE_LOCKED OperationalErrors and return the existing 303/error-notice
workflow after rollback. Booking retains its Phase 3 handler; schedule saving
retains its controlled failure handler. Production timeout remains 15 seconds.
Real lock tests hold a separate writer connection and use a 50ms test-only timeout
for each of five lifecycle/configuration paths; all return controlled errors.

Seven new races use two independent authenticated TestClients on worker threads,
independent SQLite connections and one shared temporary file. An SQL trace barrier
synchronizes both immediately before `BEGIN IMMEDIATE`; assertions verify two
distinct worker thread IDs reached it. No Python lock serializes application
writes. SQLite provides write serialization. Parent initialization is complete
before workers issue HTTP requests. Prior Phase 3 separate-process races also
remain in the full suite and pass unchanged.

| Race | Verified outcome |
|---|---|
| Two cancellations of one appointment | One cancellation event; one already-cancelled notice |
| Cancellation versus booking released slot | Original cancelled once; booking either rejects before release or succeeds after release; no overlap |
| Reschedule versus competing replacement booking | Exactly one new event/success; loser rejects; losing original preserved |
| Two patients rescheduling into overlapping replacement | Exactly one reschedule; other appointment and its history unchanged |
| Duplicate reschedule | One reschedule event; one already-at-that-time response |
| Booking versus doctor block | Exactly one operation succeeds; no committed block/booking overlap |
| Booking versus doctor hours change | Exactly one operation succeeds; all confirmed bookings remain inside committed hours |

Every race checks no overlapping active appointments, no block/appointment
overlap, confirmed containment in final hours, and `PRAGMA integrity_check = ok`.
Writer acquisition order is deliberately unspecified; assertions accept only
valid serialized outcomes. These are concurrency correctness tests, not load
benchmarks or a guarantee for storage without reliable SQLite file locks.

## UTC, date boundaries and required demonstration

Kept Python ZoneInfo and strict round-trip conversion. Doctor hours remain local;
appointment start/end persist as normalized UTC Z instants. Patient/doctor views
convert the same stored instants with visible IANA labels. No fixed offsets or
new date library were added. The full patient-local date/time now appears in
booking/reschedule slot labels, avoiding missing-date ambiguity across midnight.

Fixed the patient availability-date filter: convert patient midnight and next
midnight separately to UTC; generate intersecting doctor-local dates and keep
starts in that half-open window. View slots links use the first matching doctor
date. Detail/reschedule and doctor dashboard date selectors remain doctor-local.
Default dashboard dates now use the common server clock in the viewer's zone.
Tests include previous UTC dates, next UTC dates and 23/25-hour local DST days.

Authenticated integration tests use the four existing synthetic accounts:
Dr. Meera (Europe/London), Dr. Alex (America/New_York), Asha (Asia/Kolkata), and
Sam (America/New_York). Real schedule and booking routes generate and persist
appointments; no route response is hardcoded. Expected constants are independent
test assertions. Both dashboards and the database must agree on exact start/end.

| Doctor-local 10:00 booking | Persisted UTC start | Asha local display |
|---|---|---|
| Meera, 2026-11-02 | 2026-11-02T10:00:00Z | 15:30 Asia/Kolkata |
| Alex, 2026-11-02 | 2026-11-02T15:00:00Z | 20:30 Asia/Kolkata |
| Meera, 2027-07-05 | 2027-07-05T09:00:00Z | 14:30 Asia/Kolkata |
| Alex, 2027-07-05 | 2027-07-05T14:00:00Z | 19:30 Asia/Kolkata |

## DST results and policy

Actual installed IANA data (`tzdata 2026.2`) is used. Strict conversion rejects
nonexistent spring times and ambiguous autumn times; no arbitrary fold is chosen.
Generator skips candidates whose start/end cannot resolve, or whose elapsed UTC
duration differs from configured duration. Doctor block forms reject gaps/folds
with a notice; explicit-offset booking requests cannot bypass generated slots.

| Zone | Spring gap example | Autumn fold example |
|---|---|---|
| Europe/London | 2026-03-29 01:30; 2027-03-28 01:30 | 2026-10-25 01:30; 2027-10-31 01:30 |
| America/New_York | 2026-03-08 02:30; 2027-03-14 02:30 | 2026-11-01 01:30; 2027-11-07 01:30 |

All eight examples reject as expected. Four authenticated 2027 transition
workflows reject invalid blocks/bookings and preserve state. Ordinary winter and
summer 09:00 conversions pass in all three zones; Kolkata remains 03:30 UTC in
both seasons. Patient-local DST date tests cover both zones' 23/25-hour days.

## Executed verification

Commands run in `slotzero-mvp`, using `py -m pytest ... -q -p no:cacheprovider`:

- Pre-edit full baseline: **108 passed, 0 failed, 1 warning in 69.74s**.
- Initial lifecycle-focused file: **31 passed in 17.93s**, one warning.
- Expanded intermediate file: **55 passed, 2 failed in 29.03s**, one warning.
  Both failures were new expected slot-count assertions: strict boundary policy
  yields five valid half-hour slots in the tested 00:00–04:00 transition windows,
  rather than four. Corrected these expectations after inspecting valid start/end
  boundaries; no existing test or application validation was weakened.
- Final Phase 4 focused file: **61 passed, 0 failed, 1 warning in 32.32s**:
  31 lifecycle/security/locking/rollback cases and 30 time-zone/DST/date/demo cases.
- Final full suite: **169 passed, 0 failed, 0 skipped, 1 warning in 105.05s**.
  All previous 108 plus 61 new cases pass. All four previous test files are
  byte-identical to the pre-edit snapshot.
- Separate Uvicorn process, temporary database, real loopback HTTP: `/health`
  200 with expected JSON, `/login` 200, authenticated patient and doctor dashboards
  200, `/static/app.js` 200. Process stopped afterward.

The warning is the existing Starlette/AnyIO BlockingPortal deprecation. Tests use
the installed environment, not a clean exact-pinned dependency installation.
No regular application database was created or modified. No visual-browser result
is claimed; authenticated HTML and response context were verified through ASGI,
plus real HTTP startup smoke checks.

## Files, review and acceptance

Application changes: `slotzero-mvp/app.py`, templates `patient_dashboard.html`,
`doctor_detail.html`, `reschedule.html`; added `tests/test_phase4.py`.
Documentation changes: root README, docs INDEX, database design (04), route
contracts (05), scheduling (06), test verification (08), traceability (13), known
limitations (15), and this report. App's historical documentation copy and earlier
phase reports remain unchanged. No schema, index, migration, dependency or config
change. Full interval audit data uses the existing details field.

Reviewed application/template diffs against the external snapshot, new tests and
documentation changes; Git tracked/untracked whitespace checks passed. Git remains
dirty on `master` with the pre-existing untracked app/docs/workspace and modified
README. No staging, commit or push. No formal Brain exists or is claimed updated;
the existing root docs carry current context.

All supplied Phase 4 acceptance criteria pass in the local automated scope:
exact cancellation cutoff, reopening/history retention, atomic reschedule and
failure preservation, concurrent lifecycle/audit consistency, no active overlap,
consistent UTC dashboards, all three IANA zones, gap/fold rejection and all prior
108 tests. Browser visual verification and independent PDF reconciliation remain
outstanding, so this is not a public-production certification.

## Remaining risks and recommended delivery work

Obtain/reconcile the official PDF and confirm ADR-009 rescheduling policy; reproduce
the pinned environment; perform browser/mobile/accessibility checks; prepare and
review final demo/submission artifacts. Evaluate secure hosting with persistent
SQLite storage, HTTPS, rotated demo credentials and appropriate auth hardening
only under separate deployment authorization. No later phase was started.

SQLite still serializes writers and requires one shared database file with working
file locks. Supported HTTP schedule/block writes coordinate transactions; direct
operator SQL block writes lack a block/appointment trigger. Earlier audit rows
cannot reconstruct end times absent from their original data. Idempotent current
slot retries do not add events; rescheduling has no request ledger/version token
to distinguish an intentionally repeated move from an old form submitted after
another distinct move. Existing retention/security/deployment limits remain.
