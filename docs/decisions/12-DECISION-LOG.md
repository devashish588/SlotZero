# SlotZero — Architecture Decision Log

## ADR-013 — Restore previous UI and add targeted scheduling updates

**Status:** Accepted by explicit user request, 2026-11-01
**Decision:** The user rejected the green redesign and requested the previous navy/card composition with readable fonts, correct path/hash navigation selection, a day-by-day weekly editor and an in-app notification bell/pop-ups. Weekly pickers serialize the existing schedule_text contract; server validation and booking rules remain unchanged. Notifications reuse role-scoped appointment events, poll while the page is open and keep browser-local read state.

The user additionally selected Google Calendar sync. Implement optional doctor OAuth with encrypted refresh credentials and manual export to a separate app-created calendar, without patient identities. Two additive tables store encrypted connection metadata and expiring hashed OAuth states; this does not change login/session roles or existing appointment tables. Google is not an availability/booking authority. Real OAuth consent and live sync remain pending user configuration; see the [setup guide](../operations/GOOGLE-CALENDAR-SETUP.md). No automatic synchronization, personal-calendar import or OS push delivery is claimed.

**Consequence:** The earlier green visual direction is superseded; historical redesign evidence remains historical. Existing deployment/MVP limitations still apply.

This log records current decisions and makes assumptions explicit. Status describes the current MVP, not a claim of production approval.

## ADR-001 — Two user-facing portals; no admin dashboard

**Status:** Accepted for MVP  
**Decision:** Deliver doctor and patient portals only. Doctor identities are provisioned by seed data or an operator CLI utility.  
**Reason:** The challenge requires doctors to manage schedules and patients to book; a separate admin UI is not required to demonstrate that workflow.  
**Consequence:** No public doctor registration or in-app doctor approval exists.

## ADR-002 — Seed doctor identities, not schedules or appointments

**Status:** Accepted for MVP  
**Decision:** Seed Dr. Meera and Dr. Alex accounts, but leave weekly schedules empty and do not seed appointments or slot results.  
**Reason:** The participant brief says example accounts are for testing and asks the site to let users create/edit schedules and bookings; slot results must not be hardcoded.  
**Consequence:** Doctor must configure hours before a patient can book.

## ADR-003 — Patient role is assigned by server

**Status:** Accepted for MVP  
**Decision:** Public registration always inserts role `patient`.  
**Reason:** Prevent role escalation by a modified client request.  
**Consequence:** New doctors must be provisioned out-of-band by operator.

## ADR-004 — Weekly local working hours; UTC appointment instants

**Status:** Accepted for MVP  
**Decision:** Store recurring hours as local wall-clock ranges keyed by weekday, interpreted in the doctor's IANA zone. Store actual appointments/blocks as UTC instants.  
**Reason:** Doctor availability is defined in the doctor's location; a booking must represent one instant everywhere.  
**Consequence:** Convert at boundaries; never store a fixed UTC offset as a substitute for an IANA zone.

## ADR-005 — Reject DST gaps and folds

**Status:** Accepted for MVP  
**Decision:** Reject nonexistent and ambiguous local wall times.  
**Reason:** Simple and deterministic behaviour avoids accidentally assigning the wrong instant.  
**Consequence:** Users must select another time; a future UX could present both folds explicitly.

## ADR-006 — Half-open appointment intervals

**Status:** Accepted for MVP  
**Decision:** Represent interval occupancy as `[start, end)`.  
**Reason:** Adjacent consultations can meet exactly at a boundary without overlapping.  
**Consequence:** Overlap predicate is `existing_start < new_end AND existing_end > new_start`.

## ADR-007 — SQLite transactional guard for the hackathon MVP

**Status:** Accepted for single-instance MVP only  
**Decision:** Use SQLite WAL, `BEGIN IMMEDIATE`, application-level recheck, DB overlap triggers and patient/idempotency uniqueness.  
**Reason:** No Docker or external database is required for the local demo; all data can be stored in one local DB file.  
**Consequence:** SQLite serializes writes and is not the recommended horizontally scaled production database. Migrate to PostgreSQL with a range exclusion constraint before multi-instance deployment.

## ADR-008 — Atomic reschedule updates same appointment

**Status:** Accepted for MVP  
**Decision:** Validate replacement slot and update the existing appointment row plus audit event inside one transaction.  
**Reason:** Failed reschedules must preserve the current booking and history continuity.  
**Consequence:** Appointment ID remains stable across reschedules.

## ADR-009 — Apply two-hour cutoff to rescheduling

**Status:** Assumption requiring product confirmation  
**Decision:** MVP applies the two-hour cutoff to both cancellation and rescheduling.  
**Reason:** A conservative and consistent initial policy.  
**Important:** The challenge explicitly states a two-hour cutoff for cancellation; it does not clearly prescribe the same cutoff for rescheduling. Confirm with challenge owner/product decision-maker if possible.

## ADR-010 — Reject schedule/block changes that conflict with confirmed bookings

**Status:** Accepted for MVP  
**Decision:** Do not silently cancel or hide existing appointments. Reject a conflicting schedule update or block request.  
**Reason:** Preserve user trust and existing commitments.  
**Consequence:** Doctor must resolve affected bookings before changing that availability.

## ADR-011 — Server-rendered pages for the challenge

**Status:** Accepted for MVP  
**Decision:** Use FastAPI + Jinja2 forms and redirects, with minimal vanilla JS/CSS.  
**Reason:** One deployable service and smaller frontend/backend integration surface.  
**Consequence:** No public JSON business API or independent SPA is provided.

## ADR-012 — Known date-filter semantics need refinement

**Status:** Open follow-up  
**Decision so far:** Doctor detail calendar date is doctor-local. Patient dashboard availability filter forwards one date string to each doctor's slot generator.  
**Risk:** A patient-local date may differ from a doctor's local calendar date near date boundaries.  
**Next:** Clarify product semantics (patient-local search date vs doctor-local appointment date) and convert per doctor or label the filter explicitly. See Known Limitations.
