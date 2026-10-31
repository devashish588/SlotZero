# SlotZero — Test Plan and Verification

## Latest result — Phase 5, 2026-10-31

Final complete suite: **170 passed, 0 failed, 0 skipped, 1 existing dependency
warning in 119.49s**, installed Python 3.14.4 environment. All previous 169 tests
remain unchanged. `py scripts/verify_phase5_browser.py` additionally passes real
Chromium/HTTP patient, doctor, lifecycle and security workflows, DST notices,
mobile logout, loading state and 24 page/viewport captures. Post-browser SQLite
integrity/foreign-key/overlap/audit checks pass. This optional script requires the
already-installed Playwright/browser; it installs nothing and uses a temporary DB.
See [Phase 5](PHASE-5-VERIFICATION.md) for exact commands, evidence and limits.
Historical checklists below are not independent current verification claims.
Pinned environment, intended host, other browser engines and formal accessibility
or penetration tests remain unverified.

Previous Phase 4 execution (2026-10-31): `py -m pytest -q -p no:cacheprovider` → **169 passed,
0 failed, 1 warning in 105.05s**. All previous 108 cases plus 61 Phase 4 cases pass.
Focused Phase 4: **61 passed in 32.32s**. Baseline before edits: **108 passed in
69.74s**. No old tests were edited, skipped or removed. New coverage comprises 31
lifecycle/security/rollback/locking cases and 30 IANA/DST/date/demo cases. Seven
races synchronize independent SQLite connections at `BEGIN IMMEDIATE`. Separate
Uvicorn startup and real authenticated HTTP smoke checks passed. See
[Phase 4 verification](PHASE-4-VERIFICATION.md) for detailed results and limits.

Previous Phase 3: **108 passed, 1 warning in 70.06s**; focused **37 passed in
27.39s**. [Phase 3 verification](PHASE-3-VERIFICATION.md) records separate-process
booking overlap, adjacency and idempotency races.

Previous Phase 2 execution: `py -m pytest -q -p no:cacheprovider` → **71 passed,
1 warning in 37.44s**. This includes 59 Phase 2 cases and all 12 previous cases.
The initial focused Phase 2 run passed 55 cases; four further cases were added
before the full run. Startup was also checked through a separate Uvicorn process
with a temporary SQLite database and real HTTP requests. See
[Phase 2 verification](PHASE-2-VERIFICATION.md). Older results below are historical.

## 1. Purpose

This document records the current automated test suite and the verification executed while preparing this documentation pack. A passing automated suite is evidence for covered scenarios only; it is not proof of production readiness.

## 2. Test environment verified in this build

- Python: 3.13.5 (artifact build environment)
- FastAPI: 0.128.2
- Starlette: 0.50.0
- Jinja2: 3.1.6
- Uvicorn: 0.48.0
- pytest: 9.0.2
- httpx: 0.28.1

The README specifies Python 3.11+ as the intended runtime. A real Windows 11 installation has not been verified in this build environment.

## 3. Commands

```powershell
# Install application dependencies
pip install -r requirements.txt

# Install test dependencies
pip install -r requirements-dev.txt

# Run automated tests
pytest -q

# Compile-check app and tests
python -m compileall -q app.py tests
```

## 4. Current test inventory

The current source has eight pytest test functions. They cover:

| Test | Coverage |
|---|---|
| `test_schedule_parser_supports_split_shifts_and_closed_days` | Multiple intervals and closed weekdays |
| `test_schedule_parser_rejects_overlapping_ranges` | Rejection of overlapping ranges |
| `test_dst_nonexistent_london_time_is_rejected` | London DST gap rejection |
| `test_dst_ambiguous_london_time_is_rejected` | London DST fold rejection |
| `test_normal_local_time_converts_to_utc` | Normal London time conversion |
| `test_invalid_dates_and_naive_timestamps_are_rejected` | Invalid date/naive timestamp validation |
| `test_interval_overlap_allows_adjacent_bookings` | Half-open interval boundaries |
| `test_demo_database_booking_guard_and_role_separation` | Role checks, schedule/block behaviour, ownership, idempotency, DB trigger, race booking, reschedule, cancellation, event history and dashboards |

The timezone and schedule-conflict regression tests additionally cover:

- Patient timezone changes, persistence after logout/login, and appointment
  display conversion without changing stored UTC instants.
- Invalid and role-unauthorized timezone updates.
- Conflict details in the doctor's timezone, a calendar route to the exact
  conflicting date, and successful retry after all confirmed conflicts are
  legitimately resolved.

## 5. Verification result observed during documentation

Command executed: `pytest -q`  
Result: **8 passed in 1.35s**.

This is the result of the current local artifact test run, not a claim about an external deployment or the user's Windows machine.

The existing verification record also notes successful page smoke checks for login, register, patient dashboard after login, doctor detail after patient login, and doctor dashboard after doctor login, plus compile check.

## 6. Manual acceptance checklist

- [ ] Doctor login succeeds with demo credentials.
- [ ] Doctor can configure weekday hours and duration.
- [ ] Doctor can block a future free interval.
- [ ] Doctor cannot block or schedule away a confirmed appointment.
- [ ] Patient can register with one supported time zone.
- [ ] Patient can discover/filter doctors.
- [ ] Patient sees slots in their own timezone and doctor's timezone.
- [ ] Patient can book an available slot.
- [ ] Second patient cannot book the same slot.
- [ ] Patient cannot cancel/reschedule another patient's appointment.
- [ ] Cancellation inside the two-hour window is rejected.
- [ ] Eligible cancellation releases the slot.
- [ ] Eligible reschedule moves the booking and logs the change.
- [ ] Failed reschedule leaves the original appointment unchanged.
- [ ] Asha/Meera and Asha/Alex timezone demonstrations are correct.
- [ ] DST gap and fold cases are rejected as documented.
- [ ] UI is usable at phone viewport sizes.
- [ ] App is restarted and database persistence is confirmed on the intended host.

## 7. Additional tests recommended before production

- DST gap/fold tests for New York and Kolkata (where relevant to rules).
- Start/end across DST transition and elapsed-duration tests.
- Schedule edits that change consultation duration while bookings exist.
- Block deletion ownership and malformed block inputs.
- Patient registration duplicates, long/invalid values and timezone tampering.
- Session expiry and logout invalidation.
- CSRF missing, wrong and replayed tokens.
- Large-volume slot generation and database lock contention.
- SQLite process restart and WAL persistence.
- Production PostgreSQL constraint and multi-worker concurrency tests after migration.
- Browser-level tests on Chrome/Edge mobile and desktop.

## 8. What was not verified

- Public deployment and judge access.
- Real Windows/PowerShell setup.
- Multi-instance hosting or production traffic.
- External email, SMS, calendar or payment integrations (not implemented).
- Formal security audit or accessibility audit.
