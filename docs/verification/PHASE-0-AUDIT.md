# Phase 0 — SlotZero repository audit

Date: 2026-10-31 (Asia/Calcutta). Scope: inspect and prepare only; no application
implementation, dependency installation, deployment, or push. Architecture below
is a proposal, not a replacement for existing accepted decisions.

## A. Repository status

| Item | Observed result |
|---|---|
| Repository | https://github.com/devashish588/SlotZero |
| Local root | `D:\Ai course\Projects\MedaVida project` (confirmed by Git) |
| Intended default | `main`, supplied by the user |
| Actual remote default | No branch yet: GitHub reports `isEmpty: true`, empty default branch name; `git ls-remote` returns no refs |
| Current local branch | `master`, preserved |
| Starting commit | `500b9e5` — chore: initial preparation baseline (design system, skills, hackathon workspace, AGENTS.md) |
| Initial origin | None |
| Configured origin | `https://github.com/devashish588/SlotZero.git` for fetch/push |
| Initial working tree | No tracked changes; untracked `docs/`, `hackathon_workspace/`, `slotzero-mvp/` |

Local identity is supported by the SlotZero app, README and decision documents.
Remote emptiness does not describe this local checkout. No branch was renamed,
history rewritten, user file discarded, or change pushed. Only Phase 0 files are
eligible for this task's commit; pre-existing untracked material remains separate.

## B. Environment

| Tool | Verified version/status |
|---|---|
| Node.js | 22.23.1 |
| npm | 10.9.8 |
| Git | 2.52.0.windows.1 |
| Python | 3.14.4 through `py`; `python` is absent from PATH |
| SQLite | 3.50.4 bundled with Python |
| TypeScript | `tsc` not on PATH; no application TypeScript manifest found |
| FastAPI | Installed 0.139.2; requirements pin 0.128.2 |
| Uvicorn | Installed/pinned 0.48.0 |
| Jinja2 | Installed/pinned 3.1.6 |
| pytest | Installed 9.0.3; requirements pin 9.0.2 |
| httpx | Installed/pinned 0.28.1 |
| python-multipart | Installed 0.0.29; requirements pin 0.0.20 |
| tzdata | Installed 2026.2; requirements specify >=2025.2 |
| GitHub CLI | Available; successfully read repository metadata |
| psql, sqlite3 CLI, Docker | Not found on PATH; this does not prove absence elsewhere |

No project virtual environment was found. No app Next.js, Tailwind, Prisma or
package.json configuration exists; package manifests inside skills are tooling,
not the application. No PostgreSQL service, Neon account, Vercel project or hosting
credentials were verified. Python and GitHub checks required execution outside
the restricted sandbox; they succeeded. No dependencies were installed or changed.

## C. Existing assets and instructions

The full visible file inventory and folder tree were inspected, excluding Git
internals and generated dependency contents. Significant structure:

```text
AGENTS.md, .gitignore, opencode.json, skills-lock.json
.agents/skills/                 repository development skills
.opencode/skills/               design/UI/brand skills and configuration
.impeccable/                    local tool preparation
design-system/medavida/         MASTER.md, IMPLEMENTATION.md, tokens, auth override
docs/                          18 existing engineering documents
slotzero-mvp/
  app.py                       FastAPI routes, schema, auth, scheduling
  templates/                   eight HTML templates
  static/                      CSS and JavaScript
  tests/test_core.py            eight tests
  scripts/create_doctor.py      operator provisioning
  requirements*.txt, pytest.ini, Procfile, start.ps1
  README.md, .env.example, .gitignore, docs/
hackathon_workspace/            stages 00_PREPARATION through 10_OPERATIONS
  00_PREPARATION/backups/       existing preparation ZIP
```

Preserve all of these, including the untracked application and backup. The 18
existing root documents and application documentation copies have matching hashes.
They were not merged or overwritten. The root AGENTS.md was read; no nested
AGENTS.md or Copilot instruction file was found in the visible inventory.

The existing ignore files already exclude environment secrets, dependencies,
Python caches and app SQLite files; `.env.example` contains configuration only.
No replacement scaffold, second environment example, or second AGENTS.md is needed.
The backup archive has not been inspected for secrets and must not be bulk-staged.

Design reuse: preserve the teal/green tokens, Figtree/Noto Sans typography and
accessibility guidance. `IMPLEMENTATION.md` describes an older Next.js mock-auth
concept, including localStorage sessions and MFA demo flows; it conflicts with
the current FastAPI decision log. It is not evidence that those features are
SlotZero requirements or that its mock authentication is suitable for the app.

**Authority gap:** no original Participant Brief or formally established Brain
was found. The existing docs claim to summarize the brief, but that cannot be
independently confirmed here. Keep this audit as current context in `docs/`; do
not create a competing Brain hierarchy. Establish minimum Brain context when the
official brief is supplied, using the existing documentation where practical.

## D. Architecture proposal

**Recommendation:** retain FastAPI + Jinja2 + existing CSS/JavaScript and SQLite
for the local single-instance challenge baseline. This reuses implemented
vertical flows and avoids a rewrite before requirements are reconciled. Existing
ADRs 007 and 011 already describe this direction; their recorded acceptance is
preserved, not independently asserted as fresh human approval.

| Option | Benefit | Cost / decision |
|---|---|---|
| Existing FastAPI + SQLite | Smallest change, existing workflows and tests, no external database setup | Persistent local disk, serialized writes; appropriate only for agreed single-instance demo |
| FastAPI + PostgreSQL | Reuses UI/auth/scheduling while enabling shared database persistence | Driver, migrations, SQL changes and concurrency verification; preferred migration if hosting needs multiple instances |
| Next.js + TypeScript + Tailwind + Prisma + PostgreSQL | Candidate unified TypeScript stack | Rewrites working flows and adds build/auth/migration decisions; not justified solely by the initial empty-remote assumption |

Frontend remains server-rendered templates; backend owns identity, permissions,
availability and state transitions. Keep the existing app structure for now.
Separate scheduling, authentication and persistence modules only when a focused
implementation task makes it useful; no speculative folder hierarchy is needed.

### Data model evaluation

| Entity | Current mapping and important fields | Relationships / constraints / proposal |
|---|---|---|
| User | `users`: id, name, email, password_hash, role, timezone, created_at | Unique case-insensitive email; doctor/patient role check. One user has many sessions and patient appointments. Consider DB timezone allowlist in a future migration. |
| DoctorProfile | `doctors`: user_id, specialization, bio, consultation_minutes | Optional 1:1 user profile; PK/FK user_id; duration check 15/30/60. Timezone currently belongs to User, not doctors. |
| DoctorSchedule | `schedules`: doctor_id, weekday, intervals_json | Many weekdays per doctor; composite PK and weekday check. JSON is simple but interval validity is application-enforced. Normalized interval rows improve DB validation at migration cost. |
| BlockedPeriod | `blocked_periods`: id, doctor_id, start/end UTC, label, created_at | Many per doctor; FK and start < end. Propose doctor/time index if needed by query volume. |
| Appointment | `appointments`: doctor_id, patient_id, start/end UTC, status, idempotency_key, timestamps | FKs, positive interval, confirmed/cancelled check, unique patient/key; doctor/status/time and patient/time indexes; overlap triggers on INSERT and UPDATE. Patient role is enforced by application, not FK alone. |
| AppointmentAuditLog | `appointment_events`: appointment_id, actor_id, action, old/new start UTC, created_at, details | Many events per appointment, actor FK. Propose appointment/time index and old/new end values for full interval history. Current cascade delete is not immutable auditing; retention policy remains undecided. |

`sessions` additionally stores hashed opaque tokens, user_id, CSRF token and expiry.
Propose expiry/user indexes if cleanup or user-wide revocation requires them.
Do not add entities or lifecycle states solely because they are common elsewhere.

Lifecycle: booking creates `confirmed`; rescheduling retains the same confirmed
appointment ID while atomically updating times; cancellation changes to
`cancelled` and releases occupancy. Past records remain confirmed. Each mutation
writes an audit event in its transaction. Completion/no-show states are not
requirements established by this audit.

Authentication: retain server-side sessions with random tokens, hashed token
storage, salted scrypt password hashes, expiry, CSRF, HttpOnly/SameSite cookies,
and Secure cookies under HTTPS. Enforce role and ownership on every protected
operation. Public registration must assign patient role server-side. Demo-account
provisioning, rate limiting and password recovery need review before public use.

Concurrency: current booking/rescheduling uses `BEGIN IMMEDIATE`, recalculates
availability, writes appointment plus audit atomically and relies on overlap
triggers and idempotency uniqueness. SQLite permits only one concurrent writer;
busy/timeout behavior needs explicit handling under load. See [SQLite transaction
documentation](https://www.sqlite.org/lang_transaction.html).

For PostgreSQL, propose a partial GiST exclusion constraint on doctor equality
and `tstzrange(start_utc,end_utc,'[)')` overlap for confirmed appointments, with
`btree_gist`, positive-duration checks and idempotency uniqueness. Use an explicit
SQL migration for this guarantee regardless of ORM. Lock a common doctor row
for schedule/block/booking mutations so availability changes serialize too; an
appointment-only exclusion constraint cannot prevent a racing blocked-period
insert. Rescheduling must lock its appointment and use the same transaction.
Handle constraint conflicts as slot-unavailable, with bounded retries for
retryable transaction failures. This is proposed, not implemented. See
[PostgreSQL range constraints](https://www.postgresql.org/docs/current/rangetypes.html#RANGETYPES-CONSTRAINT).

Time zones: keep weekly hours as local weekday/time ranges in the doctor's IANA
zone; generate slots dynamically and convert actual instants to UTC. Current
SQLite stores normalized UTC text; PostgreSQL would use timestamptz. Display using
Asia/Kolkata, Europe/London and America/New_York. Keep strict DST round-trip checks;
current policy rejects gaps and folds. Confirm patient-local date-search semantics
and whether fold selection is needed rather than silently changing policy.

Deployment: current app needs an ASGI host with persistent storage, HTTPS, cookie
configuration and backups. A Vercel deployment would require shared external
persistence rather than reliance on the current SQLite file. Vercel supports a
Python runtime, so Next.js is not inherently required; its filesystem is read-only
except temporary scratch space. See [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python).
Neon/PostgreSQL is a candidate, not provisioned or selected. Before migration,
verify extension support, connection limits/pooling, TLS, migration execution,
backup/restore and environment configuration. No deployment success is claimed.

## E. Critical risks and verification

1. **Confirmed reschedule-page defect:** `reschedule_page` selects `d.timezone`
   from `doctors`, but timezone is on `users`. Executing that column reference
   against the extracted schema in an in-memory SQLite database produced
   `no such column: d.timezone`. The existing test exercises reschedule POST,
   not the GET form page. Fix and add a route regression test in Phase 1.
2. **Requirements gap:** original brief unavailable; two-hour reschedule cutoff,
   patient date semantics and other claimed requirements need source verification.
3. **Double booking / concurrency:** guards exist, but passing one two-request
   race does not establish correctness under all races or multiple processes.
   Explicitly test update overlap, failed-reschedule preservation and conflicts
   involving schedule changes/blocks; do not transplant SQLite triggers unchanged
   into a different database concurrency model.
4. **Authorization:** server checks exist; expand negative role/ownership and
   missing/invalid CSRF coverage. Static demo credentials and absent rate limiting
   prevent treating the current app as ready for public users.
5. **Time zones / DST:** London gap/fold tests exist; New York transitions,
   Kolkata conversion and cross-zone date boundaries need explicit cases.
6. **Deployment:** no host verified; ephemeral SQLite storage risks data loss.
   Persistent disk or an approved database migration is prerequisite.
7. **Reproducibility:** installed FastAPI/pytest/multipart differ from pins.
   Passing results below do not verify a clean installation of requirements.
8. **Recovery/context:** MVP and prior docs are untracked; avoid bulk commits,
   especially the unreviewed backup. Duplicate docs can drift.

Commands/results in this audit:

- Git root/status/branch/log/remotes checked; authenticated GitHub metadata and
  remote refs confirm an empty remote. Origin configured and read back.
- `py -m pytest -q -p no:cacheprovider` in `slotzero-mvp`: **8 passed, 1 warning**
  (1.14 seconds). Warning is Starlette TestClient's deprecated AnyIO BlockingPortal
  alias. Tests use temporary databases; no application/demo database was started.
- In-memory schema-only probe confirmed the reschedule query defect without
  creating accounts or appointments.
- Tool/package versions queried; all 18 existing documentation pairs hash-match.
- Existing historical verification records were not rewritten as current results.
- No browser, deployment, exact-pinned-environment or production-load verification
  was performed. No application bug was changed during this preparation phase.

## F. Initial implementation plan — approval required

1. **Phase 1 — reconcile and establish baseline.** Obtain the original brief;
   reconcile requirements and existing decisions; establish minimal Brain context;
   confirm date/search and rescheduling policies. Reproduce pinned dependencies
   in an isolated environment. Fix the reschedule-page query with a failing-then-
   passing GET regression test. Review and commit the existing MVP separately.
2. **Phase 2 — identity and doctor configuration.** Verify server sessions, CSRF,
   role/ownership boundaries, operator doctor provisioning, schedules and blocks
   as complete UI-to-database workflows. Remove deployment reliance on demo users.
3. **Phase 3 — availability.** Verify dynamic generation, split shifts, duration,
   blocked time, past times, three-zone conversion and DST/date boundaries; resolve
   the approved patient-date semantics in both filtering and display.
4. **Phase 4 — appointment integrity.** Verify booking, idempotency, cancellation,
   atomic rescheduling, audit consistency and races. If shared hosting is approved,
   implement PostgreSQL migrations/constraints and rerun concurrency checks there.
5. **Phase 5 — integrated UX and hardening.** Apply existing visual tokens without
   importing unrelated mock-auth requirements; test responsive/accessibility flows,
   negative authorization paths and error handling. Address selected public-demo
   security requirements and synchronize canonical documentation.
6. **Phase 6 — deployment and submission.** After deployment approval, configure
   hosting/database/HTTPS, verify persistence and restore, smoke-test both roles and
   critical conflicts, then prepare evidence and submission material against the
   actual brief. Never claim a deployed URL until independently verified.

## G. First implementation recommendation

After Phase 1 approval and source reconciliation, implement a regression-tested
repair of the reschedule GET page: join the doctor's User record for timezone
(the existing query already aliases that record as `u`), then test that the owner
can open an eligible confirmed appointment's reschedule form and another patient
cannot. Retain the original booking on failed rescheduling. This closes a concrete
broken vertical flow before adding any new framework or feature.

## Relevant tools and skills

- Architecture/context: existing decision log plus `documentation-and-adrs`;
  `source-driven-development` for future framework-specific implementation.
- Frontend: existing MedaVida design system and `webapp-testing`; use one UI skill
  if a design task needs it, rather than stacking overlapping design plugins.
- Backend/database: Python, SQLite, pytest, SQL constraints and existing route
  tests. `api-and-interface-design` is relevant if interfaces change; Prisma is
  not needed for the current Python implementation.
- Security: `security-and-hardening` and focused `code-review-and-quality` review.
- Deployment: existing Procfile/start script and GitHub CLI; select provider tools
  only after hosting approval. No additional plugins/dependencies are necessary
  for Phase 0. Repository OpenCode configurations are preserved, not reconfigured.

## Preparation change record and acceptance

- Added root `README.md` and this report only; configured `.git/config` origin.
- Preserved root AGENTS.md, ignore files, app environment example, all existing
  application files, design assets and previous documentation.
- Existing app folder structure is already sufficient; no new scaffold created.
- No formal Brain updated: none exists and the official brief is still missing.
  This report records current status, assumptions, risks, evidence and next tasks.
- Phase 0 acceptance: repository/environment audited, minimal entry point added,
  proposal and phased plan documented, existing tests run, discovered defect
  reported, and changes reviewed. Full development readiness remains conditional
  on the source brief and reproducible runtime setup.
- Stop here. Phase 1 requires the user's explicit approval under this task request.
