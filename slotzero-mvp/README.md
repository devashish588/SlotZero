# SlotZero — Conflict-Free Doctor Appointment Scheduler

A runnable MVP for the MedaVida participant challenge. It includes seeded demo doctors, patient registration, separate patient/doctor dashboards, dynamic availability, booking, cancellation, rescheduling, audit events, and timezone-aware display for the three required IANA zones.

> This is a hackathon/demo MVP. Use fictional data only. Do not enter real patient or business information.

## Stack

- Python 3.11+ (3.13 tested in this build environment)
- FastAPI + Jinja2 + vanilla JavaScript/CSS
- SQLite with WAL mode, `BEGIN IMMEDIATE` write transactions, and database triggers that reject overlapping confirmed appointments
- Python `zoneinfo` + the `tzdata` package for `Asia/Kolkata`, `Europe/London`, and `America/New_York` (including Windows systems without a system IANA database)

The app deliberately uses server-rendered pages so the MVP has one deployable service and no separate frontend build step.

## Run locally (Windows PowerShell)

```powershell
cd "path\to\slotzero-mvp"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>.

The SQLite database is created automatically as `slotzero.db` on first startup. To reset the demo data, stop the server and delete `slotzero.db` (and its `-wal` / `-shm` files); the four demo accounts will be seeded again. No appointment is pre-seeded.

## Demo accounts

| Role | Login | Password | Time zone |
|---|---|---|---|
| Doctor | `meera@slotzero.demo` | `Meera@123` | `Europe/London` |
| Doctor | `alex@slotzero.demo` | `Alex@123` | `America/New_York` |
| Patient | `asha@slotzero.demo` | `Asha@123` | `Asia/Kolkata` |
| Patient | `sam@slotzero.demo` | `Sam@123` | `America/New_York` |

Public registration creates patient accounts only. Doctor accounts are provisioned by the initial seed; there is no separate admin portal and no public doctor registration. Working hours are intentionally **not** seeded: each doctor must set their weekly schedule and appointment length in the Doctor dashboard before patients can book.

**Before any public deployment:** replace the demo passwords, configure HTTPS, set `SLOTZERO_COOKIE_SECURE=true`, use a production database, and do not use real patient data.

### Provision another doctor without an admin portal

A clinic operator can create doctor accounts from the server terminal. The script prompts for the password (so it is not placed in the command history):

```powershell
python .\scripts\create_doctor.py --name "Dr. Priya Rao" --email "priya@example.test" --specialization "Dermatology" --timezone "Asia/Kolkata"
```

The new doctor starts with no working hours and must configure their schedule after signing in. Public registration cannot create doctor accounts or assign roles.

## Main workflows

### Doctor

1. Sign in with a seeded doctor account.
2. Configure the initially empty weekly schedule in the doctor's own timezone. Use one line per weekday, for example `Mon: 09:00-12:00,13:00-17:00`.
3. Choose an appointment length of 15, 30, or 60 minutes.
4. Add blocked periods for breaks, leave, or other unavailability.
5. Review appointments for the selected local date.

If a proposed schedule or blocked period would overlap a confirmed booking, the change is rejected. Existing appointments are not silently removed.

### Patient

1. Register or sign in with Asha / Sam.
2. Search doctors by name or specialization, and optionally filter doctors with slots on a selected date.
3. Open a doctor, select a date on that doctor's calendar, and choose a slot displayed in both the patient's and doctor's time zones.
4. Book, cancel (at least two hours before start), or reschedule (MVP applies the same two-hour cutoff).

The date picker on a doctor page is explicitly the **doctor's local calendar date**. Slot buttons show the start time in the patient's timezone and the corresponding doctor's local time.

## Scheduling and correctness notes

- Doctor working hours are recurring local-time intervals. Multiple intervals per day are supported.
- Slots are generated at request time from working hours, blocked periods, and confirmed appointments. Slots are not stored or hardcoded.
- Appointment start/end are stored as UTC instants (`...Z`). Display values are converted at render time using the viewer's IANA timezone.
- Local wall times in a DST gap are rejected. Ambiguous local times in a DST fold are also rejected and the user must choose another time.
- Overlap uses half-open intervals: `existing_start < new_end AND existing_end > new_start`. Adjacent appointments are allowed.
- Booking is rechecked inside a write transaction. SQLite serializes writers; database triggers independently reject overlapping confirmed appointments. A unique `(patient_id, idempotency_key)` constraint protects repeated submissions.
- Rescheduling updates the same appointment inside one transaction and logs the old/new UTC start. If the new slot is unavailable, the original booking remains untouched.
- Appointment events record who booked, cancelled, or rescheduled and when. The patient sees events for their appointments; the doctor sees events for appointments on their schedule.
- Every protected POST checks the authenticated user's CSRF token and each operation checks role and ownership on the server.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest -q
```

The tests cover strict DST conversion, schedule parsing, overlap boundaries, booking conflict protection (including simultaneous requests), role separation, ownership checks, schedule/block protection, rescheduling, cancellation, and audit events.

## Environment

Copy `.env.example` to `.env` and set:

- `SLOTZERO_DB_PATH` — SQLite file path (default: `./slotzero.db` beside `app.py`)
- `SLOTZERO_COOKIE_SECURE` — set `true` when served over HTTPS

The app loads a project-root `.env` file (without overriding variables already set in the environment). Configure the same variables in your hosting platform for deployment.

On Vercel, the default database path is `/tmp/slotzero.db` because the deployed
application directory is read-only. Vercel's `/tmp` storage is ephemeral and
must not be treated as durable appointment storage; use a host with a persistent
volume or migrate the database layer to managed PostgreSQL before relying on
cross-invocation data persistence.

## Known MVP limitations / next production steps

- SQLite is appropriate for a single-instance demo and serializes all writes. For multi-instance production, migrate to PostgreSQL and use a database exclusion constraint on `(doctor_id, tstzrange(start_utc, end_utc, '[)'))` for confirmed appointments, in addition to transactions.
- No email/SMS reminders, calendar sync, payments, doctor verification workflow, or admin UI; these are intentionally out of scope for the challenge MVP.
- Doctor accounts are seeded and demo passwords are static until changed by the operator.
- The two-hour cutoff is applied to both cancellation and rescheduling as a conservative MVP policy; the brief explicitly specifies the cancellation cutoff, while the reschedule cutoff is an implementation assumption.
- There is no automated appointment-completion status transition. Past appointments remain in confirmed history but do not appear in the patient's upcoming list.
- Add rate limiting, password reset, audit-log retention policy, secure secret management, backups, and operational monitoring before real-world use.

## Engineering documentation

See the canonical [index](../docs/INDEX.md), [Phase 5 evidence](../docs/verification/PHASE-5-VERIFICATION.md), and [deployment gates](../docs/operations/09-SETUP-AND-DEPLOYMENT.md).
