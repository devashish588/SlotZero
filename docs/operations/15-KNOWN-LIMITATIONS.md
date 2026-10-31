# SlotZero — Known Limitations and Open Issues

This document is intentionally explicit. A limitation is not a failure if it is understood, scoped and accurately represented during a demo.

## 1. MVP limitations

1. **SQLite single-instance model:** suitable for a local/single-instance hackathon demo; not a horizontally scalable production architecture.
2. **No admin portal:** doctor identities are created by seed data or the server-side CLI utility.
3. **Static demo credentials:** demo accounts use static fictional passwords until changed/removed by an operator.
4. **No password reset/change UI:** account recovery is not implemented.
5. **No login rate limiting:** brute-force controls are not implemented.
6. **No email/SMS notifications:** confirmation is shown in the application only.
7. **No calendar integration or payments:** intentionally out of scope.
8. **No appointment completion state:** past confirmed appointments remain in history; no scheduled status transition marks them completed.
9. **No audit retention policy:** appointment event history is retained without a defined expiry process.
10. **No deep health/readiness check:** `/health` only returns a basic service response.
11. **No recorded public deployment:** this package is a local runnable artifact; a deployed URL must be created and independently verified.
12. **No formal accessibility or penetration test:** visual responsiveness and basic controls exist, but no formal audit has been recorded.

## 2. Date-filter semantics

Phase 4 resolves the patient-date caveat: dashboard filtering uses patient-local
calendar boundaries converted with IANA data, including 23/25-hour days. Doctor
detail/reschedule selectors remain doctor-local and links use a matching doctor
date. A doctor-detail page may include other patient-local dates because its
selector intentionally covers the whole doctor-local day.

## 3. Rescheduling policy assumption

The MVP applies a two-hour cutoff to both cancellation and rescheduling. The challenge clearly specifies cancellation up to two hours before start, but does not expressly state a rescheduling cutoff. Confirm whether the product owner expects rescheduling to follow the same rule.

## 4. Time-zone test coverage

Phase 4 adds actual IANA London/New York spring-gap and autumn-fold tests for
2026/2027, ordinary winter/summer conversion in all three zones, authenticated
Asha/Meera and Asha/Alex dashboard demonstrations, and cross-midnight/DST date
filters. Gaps and folds are rejected; no fold picker exists. Phase 5 verifies
Chromium workflows at four widths and four browser DST error notices. Other
engines, real devices and formal accessibility verification remain outstanding.
See `PHASE-4-VERIFICATION.md` and `PHASE-5-VERIFICATION.md`.

## 5. Production blockers

Do not use this MVP with real patient data until at least:

- PostgreSQL or another production-grade shared persistence strategy is in place.
- HTTPS and Secure cookies are configured.
- Demo accounts are removed/rotated.
- Rate limiting and account recovery are implemented.
- Secrets, backups, monitoring and retention policies exist.
- Security and privacy reviews are complete.

## 6. Open decisions

- Should rescheduling have the same two-hour cutoff as cancellation?
- Should an ambiguous DST fold be rejected permanently or should the UI let users choose the first/second occurrence?
- Should the doctor be allowed to alter hours around a confirmed appointment after explicitly notifying/reconfirming the patient, or should the current rejection policy remain?
- What should happen to past appointments in the lifecycle: remain confirmed, become completed automatically, or be archived?
