# SlotZero — Security and Privacy

## 1. Security objectives

1. Prevent patient/doctor role escalation.
2. Prevent cross-patient and cross-doctor appointment access.
3. Prevent forged authenticated form submissions.
4. Protect stored credentials and session identifiers.
5. Prevent concurrent booking conflicts and duplicate retries.
6. Avoid handling real patient information in a hackathon demo.

## 2. Implemented controls

| Area | Current control |
|---|---|
| Public registration | Always assigns `patient` role server-side |
| Doctor provisioning | Seed/CLI only; no public doctor signup |
| Password storage | Salted scrypt hash; plaintext is not stored |
| Session ID | Random opaque token; SHA-256 token hash stored in DB |
| Session cookie | HttpOnly, SameSite=Lax; Secure controlled by env setting |
| Session expiry | Seven days |
| CSRF | Session-bound token checked on authenticated state-changing forms |
| Role checks | Protected routes enforce doctor or patient role |
| Ownership | Appointment reads/changes include authenticated patient or doctor ownership checks |
| Booking integrity | Transactional recheck, DB overlap triggers and idempotency uniqueness |
| Database | SQLite foreign keys enabled per connection |

## 3. Role and data access matrix

| Resource/action | Patient | Doctor |
|---|---|---|
| Browse doctor profiles | Yes | Not a doctor dashboard feature |
| View live open slots | Yes | Own schedule context |
| Manage weekly schedule | No | Own only |
| Add/remove blocked time | No | Own only |
| View appointment details | Own appointments | Appointments assigned to own doctor ID |
| Cancel appointment | Own, if policy permits | No patient cancellation route |
| Reschedule appointment | Own, if policy permits | No patient reschedule route |
| View another patient's booking | No | Only patient details on bookings assigned to that doctor |
| View another doctor's bookings | No | No |

## 4. Demo data and safe use

The four demo users are fictional. The app is intended for evaluation with synthetic data only. Never enter real patient, medical, business or customer information. The static demo passwords must not be reused outside a local demo.

## 5. Required pre-deployment actions

- Replace demo credentials or disable demo users.
- Set `SLOTZERO_COOKIE_SECURE=true` when served over HTTPS.
- Terminate TLS at a trusted hosting provider and enforce HTTPS.
- Use a production database and durable backups.
- Store secrets in the host's secret manager, not in source control.
- Review cookie/session expiry and session revocation behaviour.
- Add rate limiting and brute-force protections to login/registration.
- Add password reset and credential rotation if real accounts are introduced.
- Add structured logs, monitoring and alerting without logging passwords, session tokens or sensitive user content.
- Define retention and deletion rules for appointments and audit events.
- Conduct a security review before processing real health-related or patient data.

## 6. Current gaps / limitations

- No login rate limiting, account lockout or CAPTCHA.
- No password reset or change-password UI.
- No doctor verification workflow; doctor accounts are operator-provisioned.
- No general admin role or admin portal.
- `SLOTZERO_COOKIE_SECURE` defaults to `false`; it must be changed for HTTPS deployment.
- No explicit production secret manager integration.
- No audit log retention/deletion process.
- No comprehensive penetration test or dependency vulnerability scan recorded.
- Health endpoint is not a database readiness probe.

## 7. Threat scenarios to test

Phase 2 exercised the scenarios below, including forged resource IDs and roles,
expired/invalid/revoked sessions, missing/forged/another session's CSRF token and
unsupported PUT/PATCH/DELETE methods. No authorization bypass was found in the
tested routes. See [the dated audit](../verification/PHASE-2-VERIFICATION.md) for boundaries and
remaining risks; this is not a comprehensive penetration test.

- Patient edits a URL appointment ID to access another patient's record.
- Patient attempts `/doctor/dashboard` or `/doctor/schedule`.
- Doctor attempts patient-only booking/cancellation endpoints.
- Doctor changes block ID to delete another doctor's block.
- Anonymous user submits a state-changing form.
- Authenticated user submits missing/incorrect CSRF token.
- User submits unsupported timezone, naive timestamp or manipulated slot start.
- Two patients race for one slot.
- Same booking request is submitted more than once.
