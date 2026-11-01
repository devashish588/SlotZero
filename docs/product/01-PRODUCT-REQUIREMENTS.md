# SlotZero — Product Requirements Specification

## 1. Document purpose

This specification turns the MedaVida SlotZero participant brief into a buildable, testable definition for the MVP. The challenge brief remains authoritative if a conflict arises.

## 2. Product summary

SlotZero is a web application for conflict-free doctor appointment scheduling. Doctors manage their own weekly availability and blocked periods. Patients discover doctors, view generated open slots, book, cancel and reschedule appointments. The system must prevent overlapping active appointments for the same doctor and display the same appointment instant correctly in the doctor's and patient's local time zones.

## 3. Problem statement

A clinic currently coordinates appointments manually. This creates risks of two patients selecting the same slot, cancelled appointments remaining unavailable, and doctors/patients misreading appointment times because they use different time zones.

## 4. Product goals

1. Make doctor availability configurable without hardcoded slot results.
2. Let patients find a doctor and complete an appointment workflow.
3. Ensure only one active appointment can occupy an overlapping period for a doctor.
4. Preserve appointments when schedule changes or rescheduling fail.
5. Enforce doctor/patient permissions on the server.
6. Keep one UTC appointment instant and render it in the viewer's supported IANA zone.
7. Demonstrate the required London, India and New York scenarios.

## 5. Non-goals for this MVP

- Separate admin or clinic-management portal.
- Public doctor registration or automated doctor verification.
- Payments, insurance, prescriptions or medical records.
- Video consultations, messaging or chatbot.
- Email/SMS reminders or calendar-provider integration were outside the original challenge MVP. The user's 2026-11-01 extension authorizes in-app update notifications and optional manual Google Calendar export; see ADR-013. Email/SMS, automatic/two-way calendar availability sync and payments remain outside this extension.
- Multi-clinic tenancy or multiple locations per doctor.
- Real patient or business data.

## 6. User roles and account model

### Doctor

- Doctor accounts are provisioned by the clinic/operator using the seed process or the server-side `scripts/create_doctor.py` utility.
- Public registration cannot create a doctor role.
- Doctor identity has a name, email, specialization and one supported IANA time zone.
- Doctor sets their own weekly working intervals and consultation duration.
- Doctor can add/remove their own blocked periods and view appointments assigned to them.

### Patient

- Patient can register publicly.
- Public registration always assigns the `patient` role on the server.
- Patient selects one supported IANA time zone at registration.
- Patient can discover doctors and manage only their own appointments.

### Admin / operator

- No admin portal or admin role is implemented.
- The clinic/operator is an out-of-band account-provisioning actor who runs the doctor creation utility.

## 7. Functional requirements

| ID | Requirement | MVP behaviour |
|---|---|---|
| FR-01 | Login | Doctors and patients can log in with email/password. |
| FR-02 | Patient registration | Public registration creates patient accounts only. |
| FR-03 | Doctor provisioning | Seeded doctors and a CLI utility create doctor accounts. |
| FR-04 | Role-specific areas | Doctor and patient routes enforce role on the server. |
| FR-05 | Doctor profile discovery | Patient can browse/filter by doctor name and specialization. |
| FR-06 | Availability filter | Patient can request doctors with open slots for a selected date. See the date-filter caveat in Known Limitations. |
| FR-07 | Weekly schedule | Doctor can set working days and multiple local-time intervals per day. |
| FR-08 | Duration | Doctor chooses 15, 30 or 60 minutes. |
| FR-09 | Blocked time | Doctor can add and remove date-specific unavailable periods. |
| FR-10 | Dynamic slots | Server generates slots from weekly hours, blocks and confirmed appointments. |
| FR-11 | Slot fit | A slot must fit fully inside one working interval. |
| FR-12 | Booking | Patient can book an available slot. Server recomputes availability before insert. |
| FR-13 | Conflict protection | Overlapping confirmed appointments for the same doctor are rejected. Adjacent intervals are allowed. |
| FR-14 | Duplicate protection | A patient/idempotency-key unique constraint prevents repeated submission from creating duplicates. |
| FR-15 | Cancellation | Patient can cancel their own confirmed appointment if at least two hours remain. |
| FR-16 | Rescheduling | Patient can move their own appointment only after a replacement slot is validated; the same appointment record is updated atomically. |
| FR-17 | Audit history | Booking, cancellation and rescheduling events record actor and time, with old/new times where applicable. |
| FR-18 | Time zones | Use exactly the three required IANA zones; store appointment instants in UTC. |
| FR-19 | Invalid input | Reject invalid dates, unsupported zones, invalid schedule ranges and unavailable slots with a user-facing message. |
| FR-20 | Health check | `/health` returns a minimal service status JSON response. |

## 8. Quality requirements

### Correctness and consistency

- Booking decisions must be made on the server, not trusted from a prior availability page.
- The database must independently reject overlapping confirmed appointments.
- A failed reschedule must not alter the original appointment.
- A doctor schedule/block update must not silently remove existing confirmed appointments.

### Security

- Server-side role checks and ownership checks are mandatory.
- Protected state-changing forms require a CSRF token.
- Passwords are stored as salted scrypt hashes.
- Session cookie is HttpOnly and SameSite=Lax; Secure must be enabled on HTTPS deployment.

### Usability

- Separate doctor and patient dashboards.
- Show patient and doctor local times together on slot selection.
- Explain unavailable slots and policy failures in plain language.
- Responsive layout for phone-sized screens.

### Portability

- Runs as one Python web service without a separate frontend build process.
- `tzdata` is included to support IANA zones on Windows hosts without an OS timezone database.

## 9. Acceptance criteria

The MVP is considered challenge-demo ready when a reviewer can:

1. Log in as a doctor and configure hours/duration.
2. Log in as a patient and see dynamically generated slots.
3. Book a slot and see it on both dashboards in their respective time zones.
4. Attempt to book an occupied slot as another patient and be rejected.
5. Cancel an eligible booking and see the slot become available again.
6. Reschedule an eligible booking and verify the original remains intact if the new slot is unavailable.
7. Confirm a patient cannot access another patient's appointment by changing the URL/ID.
8. See that a doctor cannot access another doctor's schedule or bookings.
9. Demonstrate DST gap/fold rejection for the relevant zones.
10. Review the audit events for booking, cancellation and rescheduling.

## 10. Product assumptions

- The two demo doctors are initial accounts only; their working hours are not pre-populated.
- Cancellation is blocked when fewer than two hours remain before appointment start.
- **Assumption:** the MVP applies the same two-hour cutoff to rescheduling. The challenge explicitly specifies this cutoff for cancellation but does not expressly specify a reschedule cutoff.
- Ambiguous DST local times are rejected rather than asking the user to choose a fold/offset.
- A doctor cannot save a new schedule or blocked period that overlaps an existing confirmed appointment; they must resolve the booking first.
- Past appointments remain in the confirmed record history; no automatic completed status transition exists.

## 11. Source reference

Based on the MedaVida SlotZero Participant Brief, especially pages 1–5: people and schedules, scheduling rules, exact time zones, website requirements, failure cases, submission contents and timing.
