# SlotZero — MedaVida

Conflict-Free Doctor Appointment Scheduler. This repository contains an existing
FastAPI/Jinja2/SQLite MVP and MedaVida design preparation.

- [Phase 0 audit, architecture proposal and next steps](docs/PHASE-0-AUDIT.md)
- [Application setup and usage](slotzero-mvp/README.md)
- [Existing engineering documentation](docs/INDEX.md)
- [Repository instructions](AGENTS.md)
- [Design system](design-system/medavida/MASTER.md)

The official SlotZero Participant Brief is the requirements authority. The original
brief is not present in this checkout; existing requirement summaries still need
reconciliation against it. Phase 1 requires human approval.

## Layout

`slotzero-mvp/` contains the application, templates, static assets, tests, dependency
files and `.env.example`. `docs/` contains engineering context; the existing
`slotzero-mvp/docs/` copy is preserved. `design-system/` contains reusable visual
assets. `hackathon_workspace/` contains preparation folders and a local backup.
`.agents/` and `.opencode/` contain skills and tool configuration.

## Scheduling invariants

Generate availability from doctor schedules, blocked periods and active bookings;
never hardcode available slots. Enforce roles and ownership server-side. Revalidate
booking and rescheduling inside transactions and retain database-level overlap
protection. Store appointment instants in UTC and use `Asia/Kolkata`,
`Europe/London`, and `America/New_York` for conversion and display. Test critical
scheduling operations and verify changes before declaring completion.

The current SQLite implementation requires a persistent database file and a
single-instance deployment model. Hosting and any PostgreSQL migration remain
approval decisions. Do not deploy the existing demo credentials publicly.

## Current verification

On 2026-10-31, the existing suite passed: **8 tests, 1 dependency deprecation
warning**, using the installed Python 3.14.4 environment. This environment differs
from the pinned requirements. A schema probe also confirmed an untested
reschedule-page query error; see the audit before treating the MVP as demo-ready.
