# SlotZero — Product & Technical Decisions

## Product model

- There are two user-facing portals: Doctor and Patient.
- Doctors are provisioned by the clinic/operator (seeded in this MVP); there is no separate admin dashboard.
- Doctor identities are seeded, but working hours are initially empty and must be configured by the doctor.
- Patient registration is public and always creates the `patient` role server-side.
- Doctors manage their own availability and see only appointments assigned to them.
- Patients see only their own appointments and may manage only those appointments.

## Scheduling rules

- Appointment durations: 15, 30, or 60 minutes, selected by the doctor.
- Working hours: recurring weekly intervals in the doctor's local IANA timezone; multiple ranges per day are allowed.
- Slot generation: derived at request time from working hours minus blocked periods and active confirmed bookings.
- Appointment instants: stored as UTC; display: converted to the viewer's IANA timezone.
- DST gaps and folds: reject both nonexistent and ambiguous local wall times.
- Overlap: half-open interval comparison; exact adjacency is allowed.
- Cancellation: allowed when at least two hours remain before start.
- Rescheduling: validate the replacement before updating; update the existing appointment atomically; this MVP applies the same two-hour cutoff as cancellation.
- A schedule change or blocked period that conflicts with a confirmed appointment is rejected; it does not delete, cancel, or hide that booking.

## Concurrency and persistence

SQLite is used to keep the challenge MVP easy to run without Docker. Each booking/reschedule obtains a `BEGIN IMMEDIATE` transaction, recomputes availability, and writes only if the slot is still open. SQLite serializes writers for the database file. Database triggers block overlapping confirmed appointments even if a future code path forgets the application check. A unique patient/idempotency-key pair prevents duplicate submission retries.

This is a single-instance strategy, not a horizontally scaled production architecture. Move to PostgreSQL with a `tstzrange` exclusion constraint before multi-instance deployment.

## Security boundaries

- Doctor accounts are seeded; public registration cannot assign the doctor role.
- Passwords are stored using salted scrypt hashes.
- Sessions use random opaque tokens; only token hashes are persisted.
- Session cookies are HttpOnly and SameSite=Lax; enable Secure behind HTTPS.
- Authenticated form submissions carry CSRF tokens.
- Every protected route checks role; appointment operations additionally verify patient ownership or doctor ownership.
- Demo identities and appointments are fictional. Never enter actual patient data.

## Explicit assumptions

1. The brief says patients can cancel up to two hours before an appointment. For a consistent and predictable first release, this MVP applies the same cutoff to rescheduling. This is configurable product policy, not an explicit wording from the brief.
2. A doctor cannot save a schedule change or a blocked period that conflicts with an existing confirmed appointment. The doctor must resolve those bookings first.
3. The doctor-date picker uses the doctor's local calendar date; displayed slot times include the patient's and doctor's local representations.
4. Ambiguous DST local times are rejected instead of presenting a choice of UTC offset/fold.
5. Appointment completion is not automated in the MVP; past confirmed bookings remain in history but are excluded from upcoming appointments and availability calculations.
