# SlotZero Documentation Pack

**Project:** SlotZero — Conflict-Free Doctor Appointment Scheduler  
**Challenge:** MedaVida AI SDE Intern Program  
**Document set:** MVP handoff, engineering reference, testing and demo preparation  
**Status:** Describes the current local MVP unless a section is explicitly labelled *Recommendation*, *Assumption* or *Not implemented*.

## Start here

| Order | Document | Purpose |
|---:|---|---|
| 1 | [Product Requirements Specification](product/01-PRODUCT-REQUIREMENTS.md) | Problem, scope, actors, functional and quality requirements |
| 2 | [User Flows and Use Cases](product/02-USER-FLOWS-AND-USE-CASES.md) | Doctor, patient, booking, cancellation and reschedule journeys |
| 3 | [System Architecture](architecture/03-SYSTEM-ARCHITECTURE.md) | Runtime components, request flow and key design choices |
| 4 | [Database Design](architecture/04-DATABASE-DESIGN.md) | Tables, relationships, constraints and data lifecycle |
| 5 | [Route and Interface Contracts](architecture/05-ROUTES-AND-INTERFACE-CONTRACTS.md) | Implemented routes, inputs, access rules and responses |
| 6 | [Scheduling and Time-zone Rules](architecture/06-SCHEDULING-AND-TIMEZONES.md) | Slot generation, UTC storage, DST and overlap behaviour |
| 7 | [Security and Privacy](architecture/07-SECURITY-AND-PRIVACY.md) | Authentication, authorization, session and privacy controls |
| 8 | [Test Plan and Verification](verification/08-TEST-PLAN-AND-VERIFICATION.md) | Test coverage, commands, results and unverified areas |
| 9 | [Setup and Deployment Runbook](operations/09-SETUP-AND-DEPLOYMENT.md) | Windows setup, configuration, operations and deployment caveats |
| 10 | [User Guide](product/10-USER-GUIDE.md) | How demo doctors and patients use the application |
| 11 | [Demo and Submission Pack](product/11-DEMO-AND-SUBMISSION-PACK.md) | Demo script, eight-slide outline, LinkedIn draft and checklist |
| 12 | [Decision Log](decisions/12-DECISION-LOG.md) | Architecture decisions and explicit assumptions |
| 13 | [Requirements Traceability](product/13-REQUIREMENTS-TRACEABILITY.md) | Challenge requirement → implementation → verification |
| 14 | [Risk Register and Roadmap](operations/14-RISK-REGISTER-AND-ROADMAP.md) | Known risks, priorities and next releases |
| 15 | [Known Limitations](operations/15-KNOWN-LIMITATIONS.md) | Honest boundaries of this MVP |
| — | [Product and Technical Decisions](decisions/PRODUCT_AND_TECHNICAL_DECISIONS.md) | Initial consolidated decisions from the implementation |
| — | [Verification Record](verification/VERIFICATION.md) | Existing build verification record |

## Evidence labels

- **Implemented:** confirmed in the current source tree.
- **Verified:** exercised by an automated test or a command run during this documentation pass.
- **Challenge requirement:** explicitly requested in the MedaVida participant brief.
- **Assumption:** a product choice made where the brief does not prescribe behaviour.
- **Recommendation:** proposed future engineering work, not current functionality.
- **Not implemented:** intentionally excluded or still outstanding.

## Source of truth and change control

1. The MedaVida participant brief defines challenge scope and judging expectations.
2. The current source code defines what this MVP actually does.
3. This documentation explains the source and records assumptions; it must not override the code or challenge brief.
4. When code changes, update the affected document and the traceability matrix in the same task.
5. Never mark a test or deployment verified without running it and recording the environment and result.

## Current implementation snapshot

- Server-rendered FastAPI application using Jinja2 templates and vanilla JavaScript/CSS.
- SQLite persistence, WAL mode, immediate write transactions, overlap triggers and idempotency uniqueness.
- Two user-facing roles: doctor and patient. No admin portal.
- Doctor identities are seeded; doctor schedules are empty until configured.
- Public registration creates patient accounts only.
- Appointment instants are stored in UTC; only `Asia/Kolkata`, `Europe/London` and `America/New_York` are allowed.
- Current Phase 5 result: `170 passed`, one dependency warning; see
  [Phase 5 verification](verification/PHASE-5-VERIFICATION.md) for Chromium workflows, responsive
  checks, focused UI fixes and the pending Phase 6 delivery checklist.
  See [Phase 4 verification](verification/PHASE-4-VERIFICATION.md) for lifecycle, independent-connection
  races, exact cancellation boundaries and IANA/DST evidence. All previous 108
  cases remain passing. [Phase 3](verification/PHASE-3-VERIFICATION.md) retains separate-process booking evidence.
- Doctors can view their profile and configure their own supported IANA timezone.
- Not deployed publicly by this documentation task.

## Verification reports

- [Phase 0](verification/PHASE-0-AUDIT.md)
- [Phase 1](verification/PHASE-1-VERIFICATION.md)
- [Phase 2](verification/PHASE-2-VERIFICATION.md)
- [Phase 3](verification/PHASE-3-VERIFICATION.md)
- [Phase 4](verification/PHASE-4-VERIFICATION.md)
- [Phase 5](verification/PHASE-5-VERIFICATION.md)
- [Repository organization](verification/REPOSITORY-ORGANIZATION-REPORT.md)

Canonical context lives here; no separate Brain directory exists. The official brief is absent; no empty reference directory was created.
