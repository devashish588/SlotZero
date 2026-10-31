# SlotZero — MedaVida

Conflict-free doctor appointment scheduling for the MedaVida AI SDE Intern challenge. The official participant brief remains authoritative; its original file is absent and summaries need reconciliation.

**FastAPI + Jinja2 + SQLite + vanilla JavaScript/CSS.** Features include patient registration, role-specific dashboards, doctor schedules/timezones/blocks, doctor search, dynamic availability, booking, cancellation, atomic rescheduling and appointment audit history.

**Synthetic data only.** Do not enter real patient or business information.

## Setup and verification

Use the [application setup guide](slotzero-mvp/README.md) for commands, demo accounts and detailed usage.

On **2026-10-31**, Phase 5 recorded **170 passed**, one dependency warning, using installed Python 3.14.4. Dependencies differ from requirements pins; clean pinned-environment reproducibility remains unverified. See [Phase 5 evidence](docs/verification/PHASE-5-VERIFICATION.md) and the [cleanup rerun](docs/verification/REPOSITORY-ORGANIZATION-REPORT.md).

**Deployment: locally verified; public deployment not yet verified.** Hosting, access gate, HTTPS, persistence/restore and release decisions remain pending. Shared demo accounts are sandbox identities. See [deployment gates](docs/operations/09-SETUP-AND-DEPLOYMENT.md) and [limitations](docs/operations/15-KNOWN-LIMITATIONS.md).

## Scheduling and security invariants

Generate availability from doctor hours, blocks and active bookings. Revalidate booking/rescheduling inside transactions with database overlap protection and idempotency. Failed rescheduling preserves the original appointment. Cancellation requires at least two hours; applying that cutoff to rescheduling remains an assumption.

Enforce roles, ownership and authenticated mutation CSRF on the server. Store UTC instants; display through `Asia/Kolkata`, `Europe/London` and `America/New_York`, rejecting DST gaps/folds. SQLite requires one instance sharing a persistent database file.

## Navigation and structure

- [Engineering documentation index](docs/INDEX.md)
- [Repository instructions](AGENTS.md)
- [Legacy design references](design-system/README.md)

```text
slotzero-mvp/     App, README, templates, static, six test files, scripts and config
docs/
  INDEX.md       Canonical documentation navigation
  product/       Requirements, flows, user/demo guides and traceability
  architecture/  Architecture, database, routes, scheduling and security
  decisions/     Product and technical decisions
  operations/    Setup, risks and limitations
  verification/  Phase 0–5 and repository organization evidence
design-system/   Legacy visual references
.agents/         Preserved agent skills
.opencode/       Preserved skills, configuration and local dependencies
.impeccable/     Local preferences
```

Preparation files and redundant documentation copies are preserved in the external recovery backup recorded in the organization report. No submission ZIP was generated.
