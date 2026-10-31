# SlotZero — Risk Register and Roadmap

## 1. Risk register

| ID | Risk | Impact | Current mitigation | Next action |
|---|---|---|---|---|
| R-01 | Two patients book same doctor/time concurrently | Critical | Immediate transaction, recheck, DB overlap trigger, idempotency key | Repeat race test under deployed DB; PostgreSQL constraint before scale |
| R-02 | Wrong time shown across time zones/DST | High | UTC instants, IANA zones, strict DST gap/fold rejection | Add cross-zone transition tests and end-to-end screenshots |
| R-03 | Patient accesses another patient's booking | Critical | Server ownership check and 404 for non-owned appointment | Add broader authorization regression suite |
| R-04 | Doctor account created by untrusted user | High | No public doctor registration; operator CLI only | Add verified admin onboarding only if production need exists |
| R-05 | Doctor schedule change invalidates booking | High | Reject conflicting schedule/block changes | Add explicit doctor workflow for resolving affected appointments |
| R-06 | SQLite used in multi-instance deployment | Critical | MVP is documented as single-instance | Migrate to PostgreSQL before horizontal scaling |
| R-07 | Demo credentials exposed | High | Fictional accounts and warning | Rotate/disable before public demo; never reuse passwords |
| R-08 | Deployed host has ephemeral disk | High | Deployment checklist calls out persistent storage | Verify host volume or use managed PostgreSQL |
| R-09 | Date filter interpreted in wrong calendar zone | Medium | Known limitation documented | Define semantics and convert date per doctor or patient timezone |
| R-10 | No login rate limiting/password reset | Medium/High | Local demo-only warning | Add throttling, password reset and account recovery before public users |
| R-11 | Audit events retained indefinitely | Medium | No policy currently | Define retention and deletion rules |
| R-12 | Reschedule cutoff assumption differs from expected policy | Medium | Same 2-hour cutoff used and disclosed | Confirm with challenge owner/product owner |

## 2. Release priorities

### P0 — Before a judge demo

- Deploy and verify the prototype URL.
- Provision credentials on the deployed instance.
- Configure doctor schedules on the deployed database.
- Run the exact booking conflict scenario on deployment.
- Verify Asha/Meera and Asha/Alex timezone display.
- Record the demo video and prepare PDF slides.
- Verify all links in a private browser.

### P1 — Before merging into a longer-lived product

- Resolve patient dashboard date-filter timezone semantics.
- Add a formal failed-reschedule integration test.
- Add cross-zone DST tests for London and New York.
- Add session expiry/CSRF regression tests.
- Add stronger input constraints and UX validation.
- Add migration management for database changes.

### P2 — Production hardening

- Migrate to PostgreSQL and test multi-instance booking concurrency.
- Add login rate limiting, account recovery and session management.
- Add secure secret management and environment-specific configuration.
- Add monitoring, structured logs and incident alerts.
- Add backup/restore runbook and audit retention policy.
- Complete accessibility, performance and security reviews.

### P3 — Optional product features (only after core reliability)

- Email/SMS reminders.
- Clinic admin/verified doctor onboarding.
- Appointment completion state and cancellation reason.
- Calendar integration.
- Patient reschedule policy configuration.
- Multi-clinic support, only if business requirements demand it.

## 3. Product principle

Do not add optional features at the expense of booking correctness, permission boundaries, time-zone correctness or demo reliability.
