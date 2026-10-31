# SlotZero — Setup and Deployment Runbook

## Phase 5 release gate — 2026-10-31

Local suite and Chromium workflows pass; **public deployment remains BLOCKED**.
The installed environment differs from pins and global `pip check` reports an
unrelated llama-index/transformers conflict. A clean pinned environment has not
been tested. No packages were installed in Phase 5; commands below are setup
instructions, not a claim that this exact setup was reproduced.

Recommended judging configuration: a dedicated synthetic-only instance behind a
host/reverse-proxy access gate, HTTPS, `SLOTZERO_COOKIE_SECURE=true`, absolute durable
`SLOTZERO_DB_PATH`, and one SQLite app instance. Gate every app route and prevent
direct-origin bypass. Share gate access privately. Existing advertised sample
accounts remain shared sandbox identities, never a production security boundary;
they must have no path to production data/volumes/secrets. Private app credential
rotation would also require updating/removing stale public login hints. No gate,
rotation, hosting, backup restore or TLS configuration was implemented here.

See [Phase 5 verification and precise Phase 6 checklist](../verification/PHASE-5-VERIFICATION.md)
before using the historical hosting checklist below. Phase 6 requires separate
authorization; unrestricted public demo access and real-patient use are not ready.

## 1. Local prerequisites

- Windows 10/11 or another Python-capable development environment.
- Python 3.11 or later (README runtime requirement).
- PowerShell for the commands below.
- Internet access to install Python packages.

Docker and Node.js are not required by the current MVP.

## 2. Windows PowerShell setup

Extract `slotzero-mvp.zip`, then run PowerShell from the extracted `slotzero-mvp` folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

Alternatively, run the supplied `start.ps1` from PowerShell after reviewing it.

## 3. Test setup

```powershell
pip install -r requirements-dev.txt
pytest -q
```

## 4. Environment variables

`.env.example`:

| Variable | Default | Meaning |
|---|---|---|
| `SLOTZERO_DB_PATH` | `./slotzero.db` | SQLite database path; relative paths resolve from project directory |
| `SLOTZERO_COOKIE_SECURE` | `false` | Set `true` when cookies are served over HTTPS |

When `VERCEL=1`, the app defaults `SLOTZERO_DB_PATH` to `/tmp/slotzero.db`
so the FastAPI function can start on Vercel's read-only deployment filesystem.
That location is temporary, not durable, and is only a boot/runtime fallback.
Do not use it for a persistent judge or production database; use a persistent
volume or managed PostgreSQL instead.

The app loads `.env` from project root and does not override variables already defined in the environment.

## 5. Database lifecycle

- `slotzero.db` is created automatically on first application startup.
- Demo users are seeded only if the users table is empty.
- Doctor working schedules are not pre-seeded.
- No appointment or precomputed slot is seeded.
- To reset a disposable demo database: stop the app, back up if needed, then delete the database plus any `-wal` and `-shm` files. On next startup demo identities are seeded again.

Do not delete a database containing data that must be retained.

## 6. Demo accounts

| Role | Email | Password | Zone |
|---|---|---|---|
| Doctor | `meera@slotzero.demo` | `Meera@123` | `Europe/London` |
| Doctor | `alex@slotzero.demo` | `Alex@123` | `America/New_York` |
| Patient | `asha@slotzero.demo` | `Asha@123` | `Asia/Kolkata` |
| Patient | `sam@slotzero.demo` | `Sam@123` | `America/New_York` |

These are demo credentials only. Replace/disable them before any public or real-user environment.

## 7. Provision another doctor

The utility creates a doctor identity from the server terminal; the password is requested interactively so it is not written to command history:

```powershell
python .\scripts\create_doctor.py --name "Dr. Priya Rao" --email "priya@example.test" --specialization "Dermatology" --timezone "Asia/Kolkata"
```

The utility validates the selected timezone against the three allowed zones, checks password length/confirmation and inserts user + doctor profile. The new doctor starts with no working hours.

## 8. Demo hosting checklist

Before deploying an online judge demo:

- [ ] Select a host that supports the Python app and a persistent writable disk, or migrate to managed PostgreSQL.
- [ ] Confirm whether the filesystem persists across deploys/restarts.
- [ ] Configure `SLOTZERO_DB_PATH` to the durable volume if using SQLite.
- [ ] Set `SLOTZERO_COOKIE_SECURE=true` behind HTTPS.
- [ ] Confirm the hosting platform provides HTTPS.
- [ ] Seed/provision demo accounts on the deployed instance.
- [ ] Log in as both doctor and patient using a private/incognito browser.
- [ ] Configure doctor schedules on the deployed instance.
- [ ] Execute a complete booking/cancel/reschedule workflow after deploy.
- [ ] Verify the judge can access the deployed URL without local network/VPN dependencies.
- [ ] Keep the database file and credentials out of the source ZIP.

## 9. Production deployment is not the current configuration

For production use, migrate from SQLite to PostgreSQL before horizontal scaling. Add migration tooling, secure secret management, backups, observability, login rate limiting, password reset, retention policies and a security review. Do not use ephemeral local storage for the production database.

## 10. Troubleshooting

| Symptom | Check |
|---|---|
| `py` not found | Install Python and enable the Windows Python launcher/PATH |
| Activation blocked | Use an approved PowerShell execution policy for the current user or invoke the venv Python directly |
| Package install fails | Confirm internet, Python version and pip output |
| Port 8000 in use | Stop the other process or use another port, e.g. `--port 8010` |
| Demo login fails | Confirm correct DB path; reset only a disposable database if necessary |
| No slots appear | Doctor must configure hours; chosen date must be in the future and have free time |
| Time-zone database missing | Confirm `tzdata` dependency is installed |
| Deployed data disappears | Host filesystem may be ephemeral; configure durable storage or PostgreSQL |
