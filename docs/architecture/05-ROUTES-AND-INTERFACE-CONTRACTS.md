# SlotZero — Route and Interface Contracts

## 1. Important implementation note

The current MVP is a server-rendered web application. Most user actions submit HTML forms and receive redirects with a `notice` query parameter. These are not JSON REST endpoints. The only current JSON route is `/health`.

All paths below are implemented in `app.py` unless marked otherwise.

## 2. Route catalogue

| Method | Path | Access | Purpose / behaviour |
|---|---|---|---|
| GET | `/` | Public/authenticated | Redirect to login or role-specific dashboard |
| GET | `/login` | Public | Render login form |
| POST | `/login` | Public | Verify credentials, create session, set cookie |
| GET | `/register` | Public | Render patient registration form |
| POST | `/register` | Public | Create patient account only |
| POST | `/logout` | Authenticated | CSRF-check, delete session, clear cookie |
| GET | `/patient/dashboard` | Patient | Search/filter doctors; show own upcoming appointments and activity |
| POST | `/patient/timezone` | Patient | CSRF-protected update of the authenticated patient's supported IANA timezone |
| GET | `/doctors/{doctor_id}` | Patient | Doctor profile and dynamically generated available slots |
| POST | `/appointments/book` | Patient | Recheck and create booking atomically |
| POST | `/appointments/{appointment_id}/cancel` | Patient owner | Cancel eligible booking |
| GET | `/appointments/{appointment_id}/reschedule` | Patient owner | View replacement slots |
| POST | `/appointments/{appointment_id}/reschedule` | Patient owner | Validate and atomically update appointment |
| GET | `/doctor/dashboard` | Doctor | Own schedule, blocks, bookings and audit history |
| POST | `/doctor/schedule` | Doctor | Save weekly working intervals and duration |
| POST | `/doctor/blocks` | Doctor | Add unavailable period |
| POST | `/doctor/blocks/{block_id}/delete` | Owning doctor | Remove own blocked period |
| GET | `/health` | Public | Return minimal service health JSON |

## 3. Authentication and form conventions

- Authenticated requests use the `slotzero_session` cookie.
- Session tokens are random; only a SHA-256 hash is persisted.
- Every authenticated state-changing form includes `csrf_token`.
- The route verifies the CSRF token against the session record.
- Role checks are performed server-side using the authenticated user record.
- Appointment IDs are not treated as authorization; ownership is checked on the server.

## 4. Registration contract

`POST /register` fields:

| Field | Required | Validation |
|---|---|---|
| `full_name` | Yes | 2–80 characters after trim |
| `email` | Yes | Unique case-insensitive email |
| `password` | Yes | Minimum 10 characters |
| `timezone_name` | Yes | Exactly one of the supported IANA names |

The handler assigns `role='patient'` in SQL. A client-supplied role is not accepted.

## 5. Patient timezone contract

`POST /patient/timezone` fields:

- `csrf_token`
- `timezone_name`: exactly one of `Asia/Kolkata`, `Europe/London`, or
  `America/New_York`

The route updates the user identified by the authenticated session only. It
does not accept a user ID, does not update appointments, and returns a redirect
with success or error feedback. Appointment UTC instants remain unchanged;
subsequent dashboard rendering converts them to the newly selected zone.

## 6. Login contract

`POST /login` fields: `email`, `password`. On success a session is created with a seven-day expiry; cookie flags are HttpOnly and SameSite=Lax, with Secure controlled by `SLOTZERO_COOKIE_SECURE`. The browser is redirected according to the account role. Failure uses a generic incorrect-email-or-password message.

## 7. Doctor schedule contract

`POST /doctor/schedule` fields:

- `csrf_token`
- `schedule_text`: one line for each weekday, e.g. `Mon: 09:00-12:00,13:00-17:00`
- `consultation_minutes`: one of `15`, `30`, `60`
- `timezone_name`: supported IANA identifier; the current UI supplies it. Older
  callers may omit it to retain the persisted timezone.

The parser requires abbreviated weekdays and exact `HH:MM` local times. It rejects
unknown/duplicate weekdays, blank submissions, incomplete comma-separated ranges,
offsets, seconds, reversed intervals and overlapping ranges. Empty weekday ranges
mean closed; omitted weekdays are also closed. Schedule, duration and timezone
save atomically and are rejected if the proposed zone/hours exclude an active
confirmed appointment. Ownership always comes from the session.

## 8. Blocked-period contract

`POST /doctor/blocks` fields:

- `csrf_token`
- `block_date` (doctor-local ISO date)
- `start_time` and `end_time` (doctor-local clock values)
- `label` (optional, trimmed and limited to 80 characters)

The local interval is strictly converted to UTC. Past periods, invalid/nonexistent/ambiguous local times and conflicts with confirmed appointments are rejected.
Clock values must be `HH:MM`. Conversion reads the doctor's current stored timezone
inside the write transaction. Conflict notices identify an affected appointment ID.
Validation/conflict notices use the existing 303 redirect convention, not HTTP 409.

`POST /doctor/blocks/{block_id}/delete` takes `csrf_token`. The delete query includes both block ID and authenticated doctor ID, preventing cross-doctor deletion.

## 8. Booking contract

`POST /appointments/book` fields:

| Field | Meaning |
|---|---|
| `csrf_token` | Authenticated session CSRF token |
| `doctor_id` | Target doctor user ID |
| `slot_start` | UTC timestamp previously emitted by generated availability |
| `idempotency_key` | Request retry key, required and at most 100 characters |

Server processing:

1. Require patient role and validate CSRF.
2. Parse timezone-aware `slot_start`.
3. Start immediate write transaction.
4. Check whether this patient/idempotency key was already used.
5. Reload doctor, derive the doctor's local calendar date from the requested instant, regenerate availability and match the UTC start.
6. Insert confirmed appointment and booking event.
7. Database trigger and unique constraint independently protect integrity.
8. Commit or report a conflict.

Phase 3 retains this transaction and form-response contract. Doctor lookup requires
a doctor-role user/profile; nonzero fractional seconds and whitespace-only request
keys are rejected. SQLITE_BUSY/SQLITE_LOCKED after the configured wait returns a
303 error notice asking for a retry. Retrying the same body/key is idempotent.
Availability pages distinguish missing working hours and past dates from ordinary
fully booked/unavailable days. No private block reason is exposed.

## 9. Cancellation contract

`POST /appointments/{appointment_id}/cancel` requires patient role, CSRF and ownership. The appointment must be confirmed and at least two hours before the start. Exact equality at two hours is allowed; even a fraction of a second less is rejected using the server UTC clock. Success changes status to `cancelled` and records actor, time and original UTC interval in the same immediate transaction. Repeats return an already-cancelled notice without another event.

## 10. Rescheduling contract

`GET /appointments/{appointment_id}/reschedule` and POST counterpart both enforce patient ownership. The replacement slot is generated while excluding the appointment being moved. POST checks the same two-hour cutoff used for cancellation in this MVP (an explicit product assumption), updates the same appointment row and inserts a reschedule event atomically. Fractional/naive/invalid input is rejected. An identical current-slot retry adds no event. Full old/new intervals are JSON in the existing event details field. Failed replacements leave all appointment/event data unchanged. Busy/locked lifecycle and block writes return 303 error notices after rollback; unrelated database faults propagate.

## 11. Patient dashboard query parameters

`GET /patient/dashboard` accepts:

- `name`
- `specialization`
- `availability_date`

The selected date is patient-local. Its midnight-to-next-midnight UTC window filters starts generated across intersecting doctor-local days. View slots links use the first matching doctor-local date. The doctor detail/reschedule selectors remain explicitly doctor-local.

## 12. Doctor dashboard query parameter

`GET /doctor/dashboard?date=YYYY-MM-DD` selects a date in the doctor's own IANA time zone.

## 13. Health response

`GET /health` returns:

```json
{"status":"ok","service":"slotzero"}
```

This is a basic process health response, not a deep readiness probe.

## 14. Not currently exposed

- No JSON CRUD API for doctors, slots or appointments.
- No API key or third-party client authentication.
- No webhooks.
- No external notification interface.
