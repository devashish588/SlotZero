from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google_calendar as gcal

BASE_DIR = Path(__file__).resolve().parent


def load_env_file() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()
_default_db_path = "/tmp/slotzero.db" if os.getenv("VERCEL") == "1" else "slotzero.db"
_db_path_setting = Path(os.getenv("SLOTZERO_DB_PATH", _default_db_path))
DB_PATH = str(_db_path_setting if _db_path_setting.is_absolute() else (BASE_DIR / _db_path_setting).resolve())
COOKIE_SECURE = os.getenv("SLOTZERO_COOKIE_SECURE", "false").lower() == "true"
SESSION_DAYS = 7
UTC = timezone.utc
ALLOWED_ZONES = ("Asia/Kolkata", "Europe/London", "America/New_York")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    yield


app = FastAPI(title="SlotZero", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ---------------------------------------------------------------------------
# Database and core utilities
# ---------------------------------------------------------------------------

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def read_db():
    conn = db_connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(immediate: bool = False):
    conn = db_connect()
    try:
        conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def utc_now() -> datetime:
    return datetime.now(UTC)


def dt_to_db(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("A timezone-aware datetime is required")
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def db_to_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("A timezone-aware timestamp is required")
    return parsed.astimezone(UTC)


def local_to_utc_strict(local_dt: datetime, zone_name: str) -> datetime:
    """Convert a naive local datetime, rejecting DST gaps and folds."""
    if local_dt.tzinfo is not None:
        raise ValueError("Expected a local datetime without timezone information")
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Unsupported time zone") from exc

    candidates: dict[datetime, datetime] = {}
    for fold in (0, 1):
        aware = local_dt.replace(tzinfo=zone, fold=fold)
        utc_value = aware.astimezone(UTC)
        round_trip = utc_value.astimezone(zone).replace(tzinfo=None)
        if round_trip == local_dt:
            candidates[utc_value] = aware

    if not candidates:
        raise ValueError("That local time does not exist because of a daylight-saving clock change")
    if len(candidates) > 1:
        raise ValueError("That local time is ambiguous because clocks change; choose another time")
    return next(iter(candidates.keys()))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$", 2)
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with read_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('doctor','patient')),
                timezone TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS doctors (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                specialization TEXT NOT NULL,
                bio TEXT NOT NULL DEFAULT '',
                consultation_minutes INTEGER NOT NULL DEFAULT 30 CHECK(consultation_minutes IN (15,30,60))
            );
            CREATE TABLE IF NOT EXISTS schedules (
                doctor_id INTEGER NOT NULL REFERENCES doctors(user_id) ON DELETE CASCADE,
                weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
                intervals_json TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY(doctor_id, weekday)
            );
            CREATE TABLE IF NOT EXISTS blocked_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL REFERENCES doctors(user_id) ON DELETE CASCADE,
                start_utc TEXT NOT NULL,
                end_utc TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT 'Unavailable',
                created_at TEXT NOT NULL,
                CHECK(start_utc < end_utc)
            );
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL REFERENCES doctors(user_id),
                patient_id INTEGER NOT NULL REFERENCES users(id),
                start_utc TEXT NOT NULL,
                end_utc TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('confirmed','cancelled')),
                idempotency_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(patient_id, idempotency_key),
                CHECK(start_utc < end_utc)
            );
            CREATE INDEX IF NOT EXISTS idx_appointments_doctor_time
                ON appointments(doctor_id, status, start_utc, end_utc);
            CREATE INDEX IF NOT EXISTS idx_appointments_patient_time
                ON appointments(patient_id, start_utc);
            CREATE TRIGGER IF NOT EXISTS prevent_appointment_overlap_insert
            BEFORE INSERT ON appointments
            WHEN NEW.status='confirmed' AND EXISTS (
                SELECT 1 FROM appointments a
                WHERE a.doctor_id=NEW.doctor_id AND a.status='confirmed'
                  AND NEW.start_utc < a.end_utc AND NEW.end_utc > a.start_utc
            )
            BEGIN
                SELECT RAISE(ABORT, 'appointment_overlap');
            END;
            CREATE TRIGGER IF NOT EXISTS prevent_appointment_overlap_update
            BEFORE UPDATE OF doctor_id,start_utc,end_utc,status ON appointments
            WHEN NEW.status='confirmed' AND EXISTS (
                SELECT 1 FROM appointments a
                WHERE a.doctor_id=NEW.doctor_id AND a.id<>NEW.id AND a.status='confirmed'
                  AND NEW.start_utc < a.end_utc AND NEW.end_utc > a.start_utc
            )
            BEGIN
                SELECT RAISE(ABORT, 'appointment_overlap');
            END;
            CREATE TABLE IF NOT EXISTS appointment_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
                actor_id INTEGER NOT NULL REFERENCES users(id),
                action TEXT NOT NULL,
                old_start_utc TEXT,
                new_start_utc TEXT,
                created_at TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                csrf_token TEXT NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS google_calendar_connections (
                doctor_id INTEGER PRIMARY KEY REFERENCES doctors(user_id) ON DELETE CASCADE,
                refresh_cipher TEXT NOT NULL,
                calendar_id TEXT NOT NULL,
                namespace TEXT NOT NULL,
                last_synced TEXT
            );
            CREATE TABLE IF NOT EXISTS google_calendar_states (
                state_hash TEXT PRIMARY KEY,
                doctor_id INTEGER NOT NULL REFERENCES doctors(user_id) ON DELETE CASCADE,
                session_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            """
        )

    # Seed atomically only when the database is empty. No appointments or slot
    # results are seeded; all availability is generated dynamically.
    with transaction(immediate=True) as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
        if count == 0:
            now = dt_to_db(utc_now())
            demo_users = [
                ("Dr. Meera Sharma", "meera@slotzero.demo", "Meera@123", "doctor", "Europe/London"),
                ("Dr. Alex Morgan", "alex@slotzero.demo", "Alex@123", "doctor", "America/New_York"),
                ("Asha Verma", "asha@slotzero.demo", "Asha@123", "patient", "Asia/Kolkata"),
                ("Sam Taylor", "sam@slotzero.demo", "Sam@123", "patient", "America/New_York"),
            ]
            for name, email, password, role, zone in demo_users:
                cur = conn.execute(
                    "INSERT INTO users(full_name,email,password_hash,role,timezone,created_at) VALUES(?,?,?,?,?,?)",
                    (name, email, hash_password(password), role, zone, now),
                )
                user_id = cur.lastrowid
                if role == "doctor":
                    specialization = "General Practitioner" if "Meera" in name else "Family Medicine"
                    bio = (
                        "Thoughtful, patient-first consultations with a focus on everyday health."
                        if "Meera" in name else
                        "Experienced in preventive care and long-term family health."
                    )
                    conn.execute(
                        "INSERT INTO doctors(user_id,specialization,bio,consultation_minutes) VALUES(?,?,?,30)",
                        (user_id, specialization, bio),
                    )


def get_current_user(request: Request) -> dict[str, Any] | None:
    raw_token = request.cookies.get("slotzero_session")
    if not raw_token:
        return None
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    with read_db() as conn:
        row = conn.execute(
            "SELECT u.*, s.csrf_token, s.expires_at FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?",
            (token_hash,),
        ).fetchone()
    if not row or db_to_dt(row["expires_at"]) <= utc_now():
        return None
    return dict(row)


def require_user(request: Request) -> dict[str, Any]:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_role(user: dict[str, Any], role: str) -> None:
    if user["role"] != role:
        raise HTTPException(status_code=403, detail="You do not have permission to access this page.")


def check_csrf(user: dict[str, Any], submitted: str) -> None:
    if not submitted or not hmac.compare_digest(user["csrf_token"], submitted):
        raise HTTPException(status_code=403, detail="Your session token expired. Refresh the page and try again.")


def flash_redirect(path: str, message: str, kind: str = "success") -> RedirectResponse:
    from urllib.parse import quote, urlsplit, urlunsplit
    parts = urlsplit(path)
    separator = "&" if parts.query else ""
    query = f"{parts.query}{separator}notice={quote(message)}&notice_type={kind}"
    location = urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
    return RedirectResponse(location, status_code=303)


def render(request: Request, template: str, user: dict[str, Any] | None = None, status_code: int = 200, **context):
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={"user": user, "csrf_token": user["csrf_token"] if user else "", **context},
        status_code=status_code,
    )


def parse_date(value: str | None, fallback: date | None = None) -> date:
    if not value:
        return fallback or date.today()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Enter a valid calendar date in YYYY-MM-DD format.") from exc


def parse_schedule_text(raw: str) -> dict[int, list[list[str]]]:
    """Expected one line per weekday: Mon: 09:00-12:00,13:00-17:00"""
    parsed: dict[int, list[list[str]]] = {i: [] for i in range(7)}
    seen: set[int] = set()
    for line_number, raw_line in enumerate(raw.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"Schedule line {line_number} must look like Mon: 09:00-12:00,13:00-17:00")
        day_label, ranges_text = line.split(":", 1)
        day_label = day_label.strip().title()
        if day_label not in WEEKDAYS:
            raise ValueError(f"Unknown weekday on schedule line {line_number}")
        weekday = WEEKDAYS.index(day_label)
        if weekday in seen:
            raise ValueError(f"{day_label} appears more than once")
        seen.add(weekday)
        ranges = ranges_text.split(",") if ranges_text.strip() else []
        for item in (part.strip() for part in ranges):
            if "-" not in item:
                raise ValueError(f"Invalid time range '{item}'")
            start_raw, end_raw = (part.strip() for part in item.split("-", 1))
            if not all(re.fullmatch(r"[0-9]{2}:[0-9]{2}", value) for value in (start_raw, end_raw)):
                raise ValueError(f"Invalid time in '{item}'. Use HH:MM.")
            try:
                start_time, end_time = time.fromisoformat(start_raw), time.fromisoformat(end_raw)
            except ValueError as exc:
                raise ValueError(f"Invalid time in '{item}'. Use HH:MM.") from exc
            if start_time >= end_time:
                raise ValueError(f"Time range '{item}' must end after it starts and use HH:MM")
            parsed[weekday].append([start_time.strftime("%H:%M"), end_time.strftime("%H:%M")])
        parsed[weekday].sort(key=lambda pair: pair[0])
        for previous, current in zip(parsed[weekday], parsed[weekday][1:]):
            if previous[1] > current[0]:
                raise ValueError(f"Working-hour ranges overlap on {day_label}")
    if not seen:
        raise ValueError("Enter weekday lines; use Mon: with no ranges for a day off.")
    return parsed


def schedule_to_text(conn: sqlite3.Connection, doctor_id: int) -> str:
    lines = []
    for weekday in range(7):
        row = conn.execute("SELECT intervals_json FROM schedules WHERE doctor_id=? AND weekday=?", (doctor_id, weekday)).fetchone()
        intervals = json.loads(row["intervals_json"]) if row else []
        ranges = ",".join(f"{start}-{end}" for start, end in intervals)
        lines.append(f"{WEEKDAYS[weekday]}: {ranges}")
    return "\n".join(lines)


def doctor_record(conn: sqlite3.Connection, doctor_id: int):
    return conn.execute(
        "SELECT u.id,u.full_name,u.email,u.timezone,d.specialization,d.bio,d.consultation_minutes "
        "FROM users u JOIN doctors d ON d.user_id=u.id WHERE u.id=? AND u.role='doctor'", (doctor_id,)
    ).fetchone()


def interval_overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and a_end > b_start


def _get_available_slots(
    conn: sqlite3.Connection,
    doctor_id: int,
    local_day: date,
    patient_zone: str,
    exclude_appointment_id: int | None = None,
) -> list[dict[str, str]]:
    doctor = doctor_record(conn, doctor_id)
    if not doctor:
        return []
    doctor_zone = doctor["timezone"]
    try:
        zone = ZoneInfo(doctor_zone)
    except ZoneInfoNotFoundError:
        return []
    now = utc_now()
    if local_day < now.astimezone(zone).date():
        return []

    schedule_row = conn.execute(
        "SELECT intervals_json FROM schedules WHERE doctor_id=? AND weekday=?",
        (doctor_id, local_day.weekday()),
    ).fetchone()
    if not schedule_row:
        return []
    intervals = json.loads(schedule_row["intervals_json"])
    if not intervals:
        return []

    day_start = dt_to_db(datetime.combine(local_day, time.min, zone))
    day_end = dt_to_db(datetime.combine(local_day, time.max, zone))
    params: list[Any] = [doctor_id, day_end, day_start]
    appt_sql = (
        "SELECT id,start_utc,end_utc FROM appointments WHERE doctor_id=? AND status='confirmed' "
        "AND start_utc<=? AND end_utc>?"
    )
    if exclude_appointment_id is not None:
        appt_sql += " AND id<>?"
        params.append(exclude_appointment_id)
    bookings = conn.execute(appt_sql, params).fetchall()
    blocks = conn.execute(
        "SELECT start_utc,end_utc FROM blocked_periods WHERE doctor_id=? AND start_utc<=? AND end_utc>?",
        (doctor_id, day_end, day_start),
    ).fetchall()
    busy = [(db_to_dt(row["start_utc"]), db_to_dt(row["end_utc"])) for row in bookings]
    busy += [(db_to_dt(row["start_utc"]), db_to_dt(row["end_utc"])) for row in blocks]

    duration = int(doctor["consultation_minutes"])
    slots: list[dict[str, str]] = []
    for interval_start, interval_end in intervals:
        start_clock = time.fromisoformat(interval_start)
        end_clock = time.fromisoformat(interval_end)
        cursor = datetime.combine(local_day, start_clock)
        interval_end_dt = datetime.combine(local_day, end_clock)
        while cursor + timedelta(minutes=duration) <= interval_end_dt:
            local_end = cursor + timedelta(minutes=duration)
            try:
                start_utc = local_to_utc_strict(cursor, doctor_zone)
                end_utc = local_to_utc_strict(local_end, doctor_zone)
            except ValueError:
                cursor += timedelta(minutes=duration)
                continue
            if (end_utc - start_utc) != timedelta(minutes=duration):
                cursor += timedelta(minutes=duration)
                continue
            if start_utc > now and not any(interval_overlaps(start_utc, end_utc, b_start, b_end) for b_start, b_end in busy):
                patient_local = start_utc.astimezone(ZoneInfo(patient_zone))
                doctor_local = start_utc.astimezone(zone)
                slots.append({
                    "start_utc": dt_to_db(start_utc),
                    "end_utc": dt_to_db(end_utc),
                    "doctor_time": doctor_local.strftime("%a, %d %b · %I:%M %p"),
                    "patient_time": patient_local.strftime("%a, %d %b · %I:%M %p"),
                    "patient_zone": patient_zone,
                    "doctor_zone": doctor_zone,
                })
            cursor += timedelta(minutes=duration)
    return slots


def get_available_slots(doctor_id: int, local_day: date, patient_zone: str, exclude_appointment_id: int | None = None):
    with read_db() as conn:
        return _get_available_slots(conn, doctor_id, local_day, patient_zone, exclude_appointment_id)


def find_slot(slots: list[dict[str, str]], requested_start: str) -> dict[str, str] | None:
    normalized = dt_to_db(db_to_dt(requested_start))
    return next((slot for slot in slots if slot["start_utc"] == normalized), None)


def appointment_view(row: sqlite3.Row | dict[str, Any], viewer_zone: str, conn: sqlite3.Connection) -> dict[str, Any]:
    data = dict(row)
    start = db_to_dt(data["start_utc"])
    end = db_to_dt(data["end_utc"])
    data["start_display"] = start.astimezone(ZoneInfo(viewer_zone)).strftime("%a, %d %b %Y · %I:%M %p")
    data["end_display"] = end.astimezone(ZoneInfo(viewer_zone)).strftime("%I:%M %p")
    data["viewer_zone"] = viewer_zone
    return data


def doctor_schedule_contains(
    zone_name: str, schedule: dict[int, list[list[str]]], start_utc: str, end_utc: str
) -> bool:
    zone = ZoneInfo(zone_name)
    start_local = db_to_dt(start_utc).astimezone(zone)
    end_local = db_to_dt(end_utc).astimezone(zone)
    if start_local.date() != end_local.date():
        return False
    intervals = schedule.get(start_local.weekday(), [])
    start_clock = start_local.strftime("%H:%M")
    end_clock = end_local.strftime("%H:%M")
    return any(start_clock >= open_time and end_clock <= close_time for open_time, close_time in intervals)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse("/doctor/dashboard" if user["role"] == "doctor" else "/patient/dashboard", status_code=303)
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html")


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    with read_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE", (email.strip(),)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return flash_redirect("/login", "Email or password is incorrect.", "error")
    raw_token = secrets.token_urlsafe(36)
    csrf_token = secrets.token_urlsafe(24)
    expires = utc_now() + timedelta(days=SESSION_DAYS)
    with transaction(immediate=True) as conn:
        conn.execute(
            "INSERT INTO sessions(token_hash,csrf_token,user_id,expires_at) VALUES(?,?,?,?)",
            (hashlib.sha256(raw_token.encode()).hexdigest(), csrf_token, row["id"], dt_to_db(expires)),
        )
    destination = "/doctor/dashboard" if row["role"] == "doctor" else "/patient/dashboard"
    response = RedirectResponse(destination, status_code=303)
    response.set_cookie(
        "slotzero_session", raw_token, max_age=SESSION_DAYS * 86400,
        httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/",
    )
    return response


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return render(request, "register.html")


@app.post("/register")
def register(
    full_name: str = Form(...), email: str = Form(...), password: str = Form(...),
    timezone_name: str = Form(...),
):
    full_name, email = full_name.strip(), email.strip().lower()
    if len(full_name) < 2 or len(full_name) > 80:
        return flash_redirect("/register", "Enter a name between 2 and 80 characters.", "error")
    if len(password) < 10:
        return flash_redirect("/register", "Use a password with at least 10 characters.", "error")
    if timezone_name not in ALLOWED_ZONES:
        return flash_redirect("/register", "Choose one of the supported time zones.", "error")
    try:
        with transaction(immediate=True) as conn:
            conn.execute(
                "INSERT INTO users(full_name,email,password_hash,role,timezone,created_at) VALUES(?,?,?,'patient',?,?)",
                (full_name, email, hash_password(password), timezone_name, dt_to_db(utc_now())),
            )
    except sqlite3.IntegrityError:
        return flash_redirect("/register", "An account with that email already exists.", "error")
    return flash_redirect("/login", "Account created. Sign in to find a doctor.")


@app.post("/logout")
def logout(request: Request, user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...)):
    check_csrf(user, csrf_token)
    raw_token = request.cookies.get("slotzero_session")
    if raw_token:
        with transaction(immediate=True) as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(raw_token.encode()).hexdigest(),))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("slotzero_session", path="/")
    return response


@app.post("/patient/timezone")
def update_patient_timezone(
    user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...), timezone_name: str = Form(...)
):
    require_role(user, "patient")
    check_csrf(user, csrf_token)
    if timezone_name not in ALLOWED_ZONES:
        return flash_redirect("/patient/dashboard", "Choose one of the supported time zones.", "error")
    try:
        with transaction(immediate=True) as conn:
            conn.execute("UPDATE users SET timezone=? WHERE id=?", (timezone_name, user["id"]))
    except sqlite3.Error:
        return flash_redirect("/patient/dashboard", "Could not update time zone. Please try again.", "error")
    return flash_redirect("/patient/dashboard", "Time zone updated. Appointment times now display in your new zone.")


# ---------------------------------------------------------------------------
# Patient experience
# ---------------------------------------------------------------------------

@app.get("/patient/dashboard", response_class=HTMLResponse)
def patient_dashboard(
    request: Request, user: dict[str, Any] = Depends(require_user),
    name: str = "", availability_date: str = "",
):
    require_role(user, "patient")
    default_day = utc_now().astimezone(ZoneInfo(user["timezone"])).date()
    try:
        selected_day = parse_date(availability_date, default_day)
    except ValueError as exc:
        return flash_redirect("/patient/dashboard", str(exc), "error")
    with read_db() as conn:
        doctor_choices = conn.execute(
            "SELECT u.full_name FROM users u JOIN doctors d ON d.user_id=u.id "
            "WHERE u.role='doctor' ORDER BY u.full_name"
        ).fetchall()
        query = (
            "SELECT u.id,u.full_name,u.timezone,d.specialization,d.bio,d.consultation_minutes "
            "FROM users u JOIN doctors d ON d.user_id=u.id WHERE u.role='doctor'"
        )
        params: list[Any] = []
        if name.strip():
            query += " AND u.full_name LIKE ?"
            params.append(f"%{name.strip()}%")
        query += " ORDER BY u.full_name"
        doctor_rows = conn.execute(query, params).fetchall()
        doctors = []
        patient_zone = ZoneInfo(user["timezone"])
        day_start = datetime.combine(selected_day, time.min, patient_zone).astimezone(UTC)
        day_end = datetime.combine(selected_day + timedelta(days=1), time.min, patient_zone).astimezone(UTC)
        for row in doctor_rows:
            doctor_zone = ZoneInfo(row["timezone"])
            doctor_day = day_start.astimezone(doctor_zone).date()
            slots = []
            while doctor_day <= (day_end - timedelta(microseconds=1)).astimezone(doctor_zone).date():
                slots.extend(slot for slot in _get_available_slots(conn, row["id"], doctor_day, user["timezone"])
                             if day_start <= db_to_dt(slot["start_utc"]) < day_end)
                doctor_day += timedelta(days=1)
            if availability_date and not slots:
                continue
            item = dict(row)
            schedule_rows = conn.execute("SELECT intervals_json FROM schedules WHERE doctor_id=?", (row["id"],)).fetchall()
            item["has_schedule"] = any(json.loads(schedule_row["intervals_json"]) for schedule_row in schedule_rows)
            item["slot_date"] = (db_to_dt(slots[0]["start_utc"]).astimezone(doctor_zone).date().isoformat()
                                 if slots else selected_day.isoformat())
            item["available_count"] = len(slots)
            item["next_slot"] = slots[0]["patient_time"] if slots else None
            doctors.append(item)
        appt_rows = conn.execute(
            "SELECT a.*,u.full_name AS doctor_name,d.specialization,u.timezone AS doctor_timezone "
            "FROM appointments a JOIN users u ON u.id=a.doctor_id JOIN doctors d ON d.user_id=u.id "
            "WHERE a.patient_id=? AND a.status='confirmed' AND a.start_utc>=? ORDER BY a.start_utc LIMIT 5",
            (user["id"], dt_to_db(utc_now())),
        ).fetchall()
        upcoming = [appointment_view(row, user["timezone"], conn) for row in appt_rows if db_to_dt(row["start_utc"]) > utc_now()]
        total = conn.execute("SELECT COUNT(*) AS n FROM appointments WHERE patient_id=? AND status='confirmed' AND start_utc>=?", (user["id"], dt_to_db(utc_now()))).fetchone()["n"]
        history_rows = conn.execute(
            "SELECT e.action,e.created_at,e.old_start_utc,e.new_start_utc,e.details,u.full_name AS actor_name, "
            "d.full_name AS doctor_name FROM appointment_events e "
            "JOIN appointments a ON a.id=e.appointment_id JOIN users u ON u.id=e.actor_id "
            "JOIN users d ON d.id=a.doctor_id WHERE a.patient_id=? ORDER BY e.created_at DESC LIMIT 6",
            (user["id"],),
        ).fetchall()
        history = []
        for event in history_rows:
            item = dict(event)
            item["created_display"] = db_to_dt(item["created_at"]).astimezone(ZoneInfo(user["timezone"])).strftime("%d %b %Y · %I:%M %p")
            item["old_display"] = db_to_dt(item["old_start_utc"]).astimezone(ZoneInfo(user["timezone"])).strftime("%d %b · %I:%M %p") if item["old_start_utc"] else None
            item["new_display"] = db_to_dt(item["new_start_utc"]).astimezone(ZoneInfo(user["timezone"])).strftime("%d %b · %I:%M %p") if item["new_start_utc"] else None
            history.append(item)
    return render(
        request, "patient_dashboard.html", user, doctors=doctors, upcoming=upcoming, history=history,
        total_appointments=total, selected_day=selected_day.isoformat(), name=name,
            doctor_choices=doctor_choices,
            allowed_zones=ALLOWED_ZONES,
    )


@app.get("/doctors/{doctor_id}", response_class=HTMLResponse)
def doctor_detail(
    doctor_id: int, request: Request, user: dict[str, Any] = Depends(require_user), date_value: str = Query("", alias="date"),
):
    require_role(user, "patient")
    with read_db() as conn:
        doctor = doctor_record(conn, doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        fallback = utc_now().astimezone(ZoneInfo(doctor["timezone"])).date()
        try:
            selected_day = parse_date(date_value, fallback)
        except ValueError as exc:
            return flash_redirect(f"/doctors/{doctor_id}", str(exc), "error")
        slots = _get_available_slots(conn, doctor_id, selected_day, user["timezone"])
        empty_message = "Try another date. The doctor may be fully booked or unavailable."
        if selected_day < fallback:
            empty_message = "This date is in the past. Choose today or a future date."
        elif not slots:
            schedules = conn.execute("SELECT intervals_json FROM schedules WHERE doctor_id=?", (doctor_id,)).fetchall()
            if not any(json.loads(row["intervals_json"]) for row in schedules):
                empty_message = "This doctor has not configured working hours. Please choose another doctor or check back later."
    return render(request, "doctor_detail.html", user, doctor=dict(doctor), slots=slots,
                  selected_day=selected_day.isoformat(), empty_message=empty_message)


@app.post("/appointments/book")
def book_appointment(
    request: Request, user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...),
    doctor_id: int = Form(...), slot_start: str = Form(...), idempotency_key: str = Form(...),
):
    require_role(user, "patient")
    check_csrf(user, csrf_token)
    if len(idempotency_key) > 100 or not idempotency_key.strip():
        return flash_redirect(f"/doctors/{doctor_id}", "Invalid booking request. Refresh and try again.", "error")
    try:
        requested_start = db_to_dt(slot_start)
        if requested_start.microsecond:
            raise ValueError("Appointment times must match a generated slot exactly")
    except (ValueError, TypeError):
        return flash_redirect(f"/doctors/{doctor_id}", "Invalid appointment time.", "error")

    try:
        with transaction(immediate=True) as conn:
            existing = conn.execute(
                "SELECT * FROM appointments WHERE patient_id=? AND idempotency_key=?",
                (user["id"], idempotency_key),
            ).fetchone()
            if existing:
                if existing["doctor_id"] == doctor_id and existing["start_utc"] == dt_to_db(requested_start):
                    if existing["status"] == "confirmed":
                        return flash_redirect("/patient/dashboard", "Your booking is already confirmed.")
                    return flash_redirect("/patient/dashboard", "This request was already used and its appointment is cancelled. Refresh to make a new booking.", "error")
                return flash_redirect("/patient/dashboard", "This request key was already used for another booking.", "error")

            doctor = doctor_record(conn, doctor_id)
            if not doctor:
                return flash_redirect("/patient/dashboard", "That doctor is no longer available.", "error")
            local_day = requested_start.astimezone(ZoneInfo(doctor["timezone"])).date()
            slots = _get_available_slots(conn, doctor_id, local_day, user["timezone"])
            slot = find_slot(slots, slot_start)
            if not slot:
                return flash_redirect(f"/doctors/{doctor_id}?date={local_day.isoformat()}", "That slot has just become unavailable. Choose another time.", "error")
            now_db = dt_to_db(utc_now())
            cur = conn.execute(
                "INSERT INTO appointments(doctor_id,patient_id,start_utc,end_utc,status,idempotency_key,created_at,updated_at) "
                "VALUES(?,?,?,?, 'confirmed',?,?,?)",
                (doctor_id, user["id"], slot["start_utc"], slot["end_utc"], idempotency_key, now_db, now_db),
            )
            appointment_id = cur.lastrowid
            conn.execute(
                "INSERT INTO appointment_events(appointment_id,actor_id,action,new_start_utc,created_at,details) VALUES(?,?,?,?,?,?)",
                (appointment_id, user["id"], "booked", slot["start_utc"], now_db, "Patient created appointment"),
            )
    except sqlite3.IntegrityError:
        return flash_redirect(f"/doctors/{doctor_id}", "That slot was booked by someone else. Please choose another.", "error")
    except sqlite3.OperationalError as exc:
        if (getattr(exc, "sqlite_errorcode", 0) & 0xFF) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            raise
        return flash_redirect(f"/doctors/{doctor_id}", "Booking is busy. Please retry the same request shortly.", "error")
    return flash_redirect("/patient/dashboard", "Appointment confirmed. You’re all set.")


@app.post("/appointments/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int, user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...),
):
    require_role(user, "patient")
    check_csrf(user, csrf_token)
    try:
        with transaction(immediate=True) as conn:
            row = conn.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
            if not row or row["patient_id"] != user["id"]:
                raise HTTPException(status_code=404, detail="Appointment not found")
            if row["status"] != "confirmed":
                return flash_redirect("/patient/dashboard", "This appointment is already cancelled.", "error")
            if db_to_dt(row["start_utc"]) - utc_now() < timedelta(hours=2):
                return flash_redirect("/patient/dashboard", "Cancellations are allowed up to 2 hours before the appointment.", "error")
            now_db = dt_to_db(utc_now())
            conn.execute("UPDATE appointments SET status='cancelled',updated_at=? WHERE id=?", (now_db, appointment_id))
            conn.execute(
                "INSERT INTO appointment_events(appointment_id,actor_id,action,old_start_utc,created_at,details) VALUES(?,?,?,?,?,?)",
                (appointment_id, user["id"], "cancelled", row["start_utc"], now_db,
                 json.dumps({"old_start_utc": row["start_utc"], "old_end_utc": row["end_utc"]})),
            )
    except sqlite3.OperationalError as exc:
        if (getattr(exc, "sqlite_errorcode", 0) & 0xFF) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            raise
        return flash_redirect("/patient/dashboard", "Scheduling is busy. Please retry shortly.", "error")
    return flash_redirect("/patient/dashboard", "Appointment cancelled. The slot is available again.")


@app.get("/appointments/{appointment_id}/reschedule", response_class=HTMLResponse)
def reschedule_page(
    appointment_id: int, request: Request, user: dict[str, Any] = Depends(require_user), date_value: str = Query("", alias="date"),
):
    require_role(user, "patient")
    with read_db() as conn:
        row = conn.execute(
            "SELECT a.*,u.full_name AS doctor_name,u.timezone AS doctor_timezone,d.specialization "
            "FROM appointments a JOIN users u ON u.id=a.doctor_id JOIN doctors d ON d.user_id=u.id "
            "WHERE a.id=? AND a.patient_id=?", (appointment_id, user["id"]),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if row["status"] != "confirmed":
            return flash_redirect("/patient/dashboard", "Only confirmed appointments can be rescheduled.", "error")
        if db_to_dt(row["start_utc"]) - utc_now() < timedelta(hours=2):
            return flash_redirect("/patient/dashboard", "Rescheduling is allowed up to 2 hours before the appointment.", "error")
        fallback = db_to_dt(row["start_utc"]).astimezone(ZoneInfo(row["doctor_timezone"])).date()
        try:
            selected_day = parse_date(date_value, fallback)
        except ValueError as exc:
            return flash_redirect(f"/appointments/{appointment_id}/reschedule", str(exc), "error")
        slots = _get_available_slots(conn, row["doctor_id"], selected_day, user["timezone"], exclude_appointment_id=appointment_id)
        appointment = appointment_view(row, user["timezone"], conn)
    return render(request, "reschedule.html", user, appointment=appointment, slots=slots, selected_day=selected_day.isoformat())


@app.post("/appointments/{appointment_id}/reschedule")
def reschedule_appointment(
    appointment_id: int, user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...), slot_start: str = Form(...),
):
    require_role(user, "patient")
    check_csrf(user, csrf_token)
    try:
        requested_start = db_to_dt(slot_start)
        if requested_start.microsecond:
            raise ValueError("Appointment times must match a generated slot exactly")
    except (ValueError, TypeError):
        return flash_redirect("/patient/dashboard", "Invalid appointment time.", "error")
    try:
        with transaction(immediate=True) as conn:
            row = conn.execute("SELECT * FROM appointments WHERE id=?", (appointment_id,)).fetchone()
            if not row or row["patient_id"] != user["id"]:
                raise HTTPException(status_code=404, detail="Appointment not found")
            if row["status"] != "confirmed":
                return flash_redirect("/patient/dashboard", "Only confirmed appointments can be rescheduled.", "error")
            if db_to_dt(row["start_utc"]) - utc_now() < timedelta(hours=2):
                return flash_redirect("/patient/dashboard", "Rescheduling is allowed up to 2 hours before the appointment.", "error")
            doctor = doctor_record(conn, row["doctor_id"])
            if not doctor:
                return flash_redirect("/patient/dashboard", "That doctor is no longer available. Your original appointment is unchanged.", "error")
            local_day = requested_start.astimezone(ZoneInfo(doctor["timezone"])).date()
            slots = _get_available_slots(conn, row["doctor_id"], local_day, user["timezone"], exclude_appointment_id=appointment_id)
            slot = find_slot(slots, slot_start)
            if not slot:
                return flash_redirect(f"/appointments/{appointment_id}/reschedule?date={local_day.isoformat()}", "That slot is no longer available. Your original appointment is unchanged.", "error")
            if row["start_utc"] == slot["start_utc"] and row["end_utc"] == slot["end_utc"]:
                return flash_redirect("/patient/dashboard", "Your appointment is already at that time.")
            now_db = dt_to_db(utc_now())
            conn.execute(
                "UPDATE appointments SET start_utc=?,end_utc=?,updated_at=? WHERE id=?",
                (slot["start_utc"], slot["end_utc"], now_db, appointment_id),
            )
            conn.execute(
                "INSERT INTO appointment_events(appointment_id,actor_id,action,old_start_utc,new_start_utc,created_at,details) VALUES(?,?,?,?,?,?,?)",
                (appointment_id, user["id"], "rescheduled", row["start_utc"], slot["start_utc"], now_db,
                 json.dumps({"old_start_utc": row["start_utc"], "old_end_utc": row["end_utc"],
                             "new_start_utc": slot["start_utc"], "new_end_utc": slot["end_utc"]})),
            )
    except sqlite3.OperationalError as exc:
        if (getattr(exc, "sqlite_errorcode", 0) & 0xFF) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            raise
        return flash_redirect("/patient/dashboard", "Scheduling is busy. Please retry shortly.", "error")
    except sqlite3.IntegrityError as exc:
        if str(exc) != "appointment_overlap":
            raise
        return flash_redirect("/patient/dashboard", "That replacement is unavailable. Your original appointment is unchanged.", "error")
    return flash_redirect("/patient/dashboard", "Appointment successfully rescheduled.")


# ---------------------------------------------------------------------------
# Doctor experience
# ---------------------------------------------------------------------------

@app.get("/doctor/dashboard", response_class=HTMLResponse)
def doctor_dashboard(request: Request, user: dict[str, Any] = Depends(require_user), date_value: str = Query("", alias="date")):
    require_role(user, "doctor")
    try:
        selected_day = parse_date(date_value, utc_now().astimezone(ZoneInfo(user["timezone"])).date())
    except ValueError as exc:
        return flash_redirect("/doctor/dashboard", str(exc), "error")
    with read_db() as conn:
        profile = doctor_record(conn, user["id"])
        schedule_text = schedule_to_text(conn, user["id"])
        calendar = conn.execute('SELECT last_synced FROM google_calendar_connections WHERE doctor_id=?', (user['id'],)).fetchone()
        rows = conn.execute(
            "SELECT a.*,p.full_name AS patient_name,p.email AS patient_email,p.timezone AS patient_timezone "
            "FROM appointments a JOIN users p ON p.id=a.patient_id "
            "WHERE a.doctor_id=? AND a.status='confirmed' ORDER BY a.start_utc",
            (user["id"],),
        ).fetchall()
        appointments = [appointment_view(row, user["timezone"], conn) for row in rows]
        appointments = [a for a in appointments if db_to_dt(a["start_utc"]).astimezone(ZoneInfo(user["timezone"])).date() == selected_day]
        upcoming_count = conn.execute(
            "SELECT COUNT(*) AS n FROM appointments WHERE doctor_id=? AND status='confirmed' AND start_utc>=?",
            (user["id"], dt_to_db(utc_now())),
        ).fetchone()["n"]
        blocked = conn.execute("SELECT * FROM blocked_periods WHERE doctor_id=? ORDER BY start_utc", (user["id"],)).fetchall()
        blocked_display = []
        for block in blocked[:8]:
            block_item = dict(block)
            block_item["start_display"] = db_to_dt(block_item["start_utc"]).astimezone(ZoneInfo(user["timezone"])).strftime("%d %b · %I:%M %p")
            block_item["end_display"] = db_to_dt(block_item["end_utc"]).astimezone(ZoneInfo(user["timezone"])).strftime("%I:%M %p")
            blocked_display.append(block_item)
        history_rows = conn.execute(
            "SELECT e.action,e.created_at,e.old_start_utc,e.new_start_utc,e.details,u.full_name AS actor_name, "
            "p.full_name AS patient_name FROM appointment_events e "
            "JOIN appointments a ON a.id=e.appointment_id JOIN users u ON u.id=e.actor_id "
            "JOIN users p ON p.id=a.patient_id WHERE a.doctor_id=? ORDER BY e.created_at DESC LIMIT 6",
            (user["id"],),
        ).fetchall()
        history = []
        for event in history_rows:
            item = dict(event)
            item["created_display"] = db_to_dt(item["created_at"]).astimezone(ZoneInfo(user["timezone"])).strftime("%d %b %Y · %I:%M %p")
            item["old_display"] = db_to_dt(item["old_start_utc"]).astimezone(ZoneInfo(user["timezone"])).strftime("%d %b · %I:%M %p") if item["old_start_utc"] else None
            item["new_display"] = db_to_dt(item["new_start_utc"]).astimezone(ZoneInfo(user["timezone"])).strftime("%d %b · %I:%M %p") if item["new_start_utc"] else None
            history.append(item)
    return render(
        request, "doctor_dashboard.html", user, profile=dict(profile), schedule_text=schedule_text,
        appointments=appointments, history=history, selected_day=selected_day.isoformat(), upcoming_count=upcoming_count,
        blocked_periods=blocked_display, allowed_zones=ALLOWED_ZONES,
        calendar_connected=calendar is not None, calendar_last_synced=calendar['last_synced'] if calendar else None,
        calendar_configured=gcal.configured(),
    )


@app.post("/doctor/schedule")
def update_schedule(
    user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...),
    schedule_text: str = Form(...), consultation_minutes: int = Form(...),
    timezone_name: str | None = Form(None),
):
    require_role(user, "doctor")
    check_csrf(user, csrf_token)
    if timezone_name is not None and timezone_name not in ALLOWED_ZONES:
        return flash_redirect("/doctor/dashboard", "Choose one of the supported time zones.", "error")
    if consultation_minutes not in (15, 30, 60):
        return flash_redirect("/doctor/dashboard", "Appointment duration must be 15, 30 or 60 minutes.", "error")
    try:
        schedule = parse_schedule_text(schedule_text)
    except ValueError as exc:
        return flash_redirect("/doctor/dashboard", str(exc), "error")
    try:
        with transaction(immediate=True) as conn:
            zone_name = timezone_name if timezone_name is not None else doctor_record(conn, user["id"])["timezone"]
            active = conn.execute(
                "SELECT a.id, a.start_utc, a.end_utc, p.full_name AS patient_name "
                "FROM appointments a JOIN users p ON p.id=a.patient_id "
                "WHERE a.doctor_id=? AND a.status='confirmed' AND a.end_utc>?",
                (user["id"], dt_to_db(utc_now())),
            ).fetchall()
            for appt in active:
                if not doctor_schedule_contains(zone_name, schedule, appt["start_utc"], appt["end_utc"]):
                    doctor_zone = ZoneInfo(zone_name)
                    appt_start = db_to_dt(appt["start_utc"]).astimezone(doctor_zone)
                    appt_end = db_to_dt(appt["end_utc"]).astimezone(doctor_zone)
                    appt_date = appt_start.strftime("%a, %d %b %Y")
                    appt_time = f"{appt_start.strftime('%I:%M %p')} – {appt_end.strftime('%I:%M %p')}"
                    appointment_path = f"/doctor/dashboard?date={appt_start.date().isoformat()}#appointments"
                    return flash_redirect(
                        appointment_path,
                        f"Schedule not saved: it would exclude an existing confirmed appointment #{appt['id']} with {appt['patient_name']} on {appt_date} at {appt_time} ({zone_name}). "
                        f"View it on your calendar, use the existing cancellation or rescheduling workflow, then retry the schedule change.",
                        "error"
                    )
            for weekday, intervals in schedule.items():
                conn.execute(
                    "INSERT INTO schedules(doctor_id,weekday,intervals_json) VALUES(?,?,?) "
                    "ON CONFLICT(doctor_id,weekday) DO UPDATE SET intervals_json=excluded.intervals_json",
                    (user["id"], weekday, json.dumps(intervals)),
                )
            conn.execute("UPDATE doctors SET consultation_minutes=? WHERE user_id=?", (consultation_minutes, user["id"]))
            conn.execute("UPDATE users SET timezone=? WHERE id=?", (zone_name, user["id"]))
    except sqlite3.Error:
        return flash_redirect("/doctor/dashboard", "Could not save the schedule. Please try again.", "error")
    return flash_redirect("/doctor/dashboard", "Working hours, time zone and appointment duration updated.")


@app.post("/doctor/blocks")
def create_block(
    user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...),
    block_date: str = Form(...), start_time: str = Form(...), end_time: str = Form(...), label: str = Form("Unavailable"),
):
    require_role(user, "doctor")
    check_csrf(user, csrf_token)
    try:
        local_day = date.fromisoformat(block_date)
        if not all(re.fullmatch(r"[0-9]{2}:[0-9]{2}", value) for value in (start_time, end_time)):
            raise ValueError("Enter local start and end times in HH:MM format.")
        start_local = datetime.combine(local_day, time.fromisoformat(start_time))
        end_local = datetime.combine(local_day, time.fromisoformat(end_time))
        if end_local <= start_local:
            raise ValueError("End time must be after start time on the same day.")
    except ValueError as exc:
        return flash_redirect("/doctor/dashboard", str(exc), "error")
    try:
        with transaction(immediate=True) as conn:
            try:
                zone_name = doctor_record(conn, user["id"])["timezone"]
                start_utc = local_to_utc_strict(start_local, zone_name)
                end_utc = local_to_utc_strict(end_local, zone_name)
                if end_utc <= start_utc or start_utc <= utc_now():
                    raise ValueError("Choose a future blocked period with a valid end time.")
            except ValueError as exc:
                return flash_redirect("/doctor/dashboard", str(exc), "error")
            conflict = conn.execute(
                "SELECT a.id, a.start_utc, a.end_utc, p.full_name AS patient_name "
                "FROM appointments a JOIN users p ON p.id=a.patient_id "
                "WHERE a.doctor_id=? AND a.status='confirmed' AND a.start_utc<? AND a.end_utc>? LIMIT 1",
                (user["id"], dt_to_db(end_utc), dt_to_db(start_utc)),
            ).fetchone()
            if conflict:
                doctor_zone = ZoneInfo(zone_name)
                appt_start = db_to_dt(conflict["start_utc"]).astimezone(doctor_zone)
                appt_end = db_to_dt(conflict["end_utc"]).astimezone(doctor_zone)
                appt_date = appt_start.strftime("%a, %d %b %Y")
                appt_time = f"{appt_start.strftime('%I:%M %p')} – {appt_end.strftime('%I:%M %p')}"
                appointment_path = f"/doctor/dashboard?date={appt_start.date().isoformat()}#appointments"
                return flash_redirect(
                    appointment_path,
                    f"This block overlaps confirmed appointment #{conflict['id']} with {conflict['patient_name']} on {appt_date} at {appt_time} ({zone_name}). "
                    f"View it on your calendar, use the existing cancellation or rescheduling workflow, then retry adding the blocked period.",
                    "error"
                )
            conn.execute(
                "INSERT INTO blocked_periods(doctor_id,start_utc,end_utc,label,created_at) VALUES(?,?,?,?,?)",
                (user["id"], dt_to_db(start_utc), dt_to_db(end_utc), label.strip()[:80] or "Unavailable", dt_to_db(utc_now())),
            )
    except sqlite3.OperationalError as exc:
        if (getattr(exc, "sqlite_errorcode", 0) & 0xFF) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            raise
        return flash_redirect("/doctor/dashboard", "Scheduling is busy. Please retry shortly.", "error")
    return flash_redirect("/doctor/dashboard", "Unavailable period added.")


@app.post("/doctor/blocks/{block_id}/delete")
def delete_block(block_id: int, user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...)):
    require_role(user, "doctor")
    check_csrf(user, csrf_token)
    try:
        with transaction(immediate=True) as conn:
            conn.execute("DELETE FROM blocked_periods WHERE id=? AND doctor_id=?", (block_id, user["id"]))
    except sqlite3.OperationalError as exc:
        if (getattr(exc, "sqlite_errorcode", 0) & 0xFF) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            raise
        return flash_redirect("/doctor/dashboard", "Scheduling is busy. Please retry shortly.", "error")
    return flash_redirect("/doctor/dashboard", "Blocked period removed.")


@app.get('/notifications')
def notifications(user: dict[str, Any] = Depends(require_user)):
    role_column = 'doctor_id' if user['role'] == 'doctor' else 'patient_id'
    with read_db() as conn:
        rows = conn.execute(
            f'SELECT e.id,e.action,e.created_at,a.start_utc,u.full_name AS actor_name FROM appointment_events e '
            f'JOIN appointments a ON a.id=e.appointment_id JOIN users u ON u.id=e.actor_id '
            f'WHERE a.{role_column}=? ORDER BY e.id DESC LIMIT 30',
            (user['id'],),
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        day = db_to_dt(item.pop('start_utc')).astimezone(ZoneInfo(user['timezone'])).date()
        item['href'] = f'/doctor/dashboard?date={day}#appointments' if user['role'] == 'doctor' else '/patient/dashboard#appointments'
        items.append(item)
    return JSONResponse({'items': items}, headers={'Cache-Control': 'no-store'})


@app.post('/doctor/calendar/connect')
def calendar_connect(user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...)):
    from urllib.parse import urlencode
    require_role(user, 'doctor')
    check_csrf(user, csrf_token)
    try:
        config = gcal.settings()
        state = secrets.token_urlsafe(32)
        with transaction(immediate=True) as conn:
            if conn.execute('SELECT 1 FROM google_calendar_connections WHERE doctor_id=?', (user['id'],)).fetchone():
                return flash_redirect('/doctor/dashboard#schedule', 'Google Calendar is already connected.')
            conn.execute('DELETE FROM google_calendar_states WHERE doctor_id=? OR expires_at<?', (user['id'], dt_to_db(utc_now())))
            conn.execute('INSERT INTO google_calendar_states VALUES(?,?,?,?)', (
                hashlib.sha256(state.encode()).hexdigest(), user['id'],
                hashlib.sha256(user['csrf_token'].encode()).hexdigest(), dt_to_db(utc_now() + timedelta(minutes=10)),
            ))
        query = urlencode({'client_id': config['CLIENT_ID'], 'redirect_uri': config['REDIRECT_URI'],
                           'response_type': 'code', 'scope': gcal.SCOPE, 'state': state,
                           'access_type': 'offline', 'prompt': 'consent'})
        return RedirectResponse('https://accounts.google.com/o/oauth2/v2/auth?' + query, status_code=303)
    except gcal.CalendarError as exc:
        return flash_redirect('/doctor/dashboard#schedule', str(exc), 'error')


@app.get('/doctor/calendar/callback')
def calendar_callback(request: Request, user: dict[str, Any] = Depends(require_user), state: str = '', code: str = '', error: str = ''):
    require_role(user, 'doctor')
    # The one-use authorization code must not appear in subsequent access logs.
    request.scope['query_string'] = b''
    with transaction(immediate=True) as conn:
        row = conn.execute('SELECT * FROM google_calendar_states WHERE state_hash=?', (hashlib.sha256(state.encode()).hexdigest(),)).fetchone()
        valid = row and row['doctor_id'] == user['id'] and row['expires_at'] > dt_to_db(utc_now()) and hmac.compare_digest(
            row['session_hash'], hashlib.sha256(user['csrf_token'].encode()).hexdigest())
        if not valid:
            raise HTTPException(status_code=403, detail='Calendar authorization expired or did not match this session. Connect again.')
        conn.execute('DELETE FROM google_calendar_states WHERE state_hash=?', (row['state_hash'],))
    try:
        if error or not code:
            raise gcal.CalendarError('Google Calendar connection was not authorized. You can try again.')
        config = gcal.settings()
        token = gcal.tokens(code=code, redirect_uri=config['REDIRECT_URI'], grant_type='authorization_code')
        if gcal.SCOPE not in token.get('scope', '').split() or not token.get('refresh_token'):
            raise gcal.CalendarError('Calendar permission was not granted. Connect again and allow calendar access.')
        calendar = gcal.request_json('POST', gcal.API + '/calendars', token['access_token'],
                                     {'summary': 'SlotZero appointments', 'timeZone': user['timezone']})
        if not isinstance(calendar.get('id'), str) or not calendar['id']:
            raise gcal.CalendarError()
        with transaction(immediate=True) as conn:
            conn.execute('INSERT INTO google_calendar_connections(doctor_id,refresh_cipher,calendar_id,namespace) VALUES(?,?,?,?)',
                         (user['id'], gcal.encrypt(token['refresh_token']), calendar['id'], secrets.token_hex(16)))
        return flash_redirect('/doctor/dashboard#schedule', 'Google Calendar connected. Use Sync now to export appointments.')
    except (gcal.CalendarError, sqlite3.Error) as exc:
        message = str(exc) if isinstance(exc, gcal.CalendarError) else 'Could not store the calendar connection. Try again.'
        return flash_redirect('/doctor/dashboard#schedule', message, 'error')


@app.post('/doctor/calendar/sync')
def calendar_sync(user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...)):
    require_role(user, 'doctor')
    check_csrf(user, csrf_token)
    try:
        with read_db() as conn:
            connection = conn.execute('SELECT * FROM google_calendar_connections WHERE doctor_id=?', (user['id'],)).fetchone()
            if not connection:
                raise gcal.CalendarError('Connect Google Calendar before syncing.')
            now = dt_to_db(utc_now())
            appointments = conn.execute("SELECT id,start_utc,end_utc FROM appointments WHERE doctor_id=? AND status='confirmed' AND end_utc>?", (user['id'], now)).fetchall()
        token = gcal.tokens(refresh_token=gcal.decrypt(connection['refresh_cipher']), grant_type='refresh_token')
        if token.get('refresh_token'):
            with transaction(immediate=True) as conn:
                conn.execute('UPDATE google_calendar_connections SET refresh_cipher=? WHERE doctor_id=?', (gcal.encrypt(token['refresh_token']), user['id']))
        gcal.sync(token['access_token'], connection['calendar_id'], connection['namespace'], appointments, now)
        with transaction(immediate=True) as conn:
            conn.execute('UPDATE google_calendar_connections SET last_synced=? WHERE doctor_id=?', (dt_to_db(utc_now()), user['id']))
        return flash_redirect('/doctor/dashboard#schedule', 'Google Calendar is up to date. Local bookings are unchanged.')
    except gcal.CalendarError as exc:
        return flash_redirect('/doctor/dashboard#schedule', str(exc) + ' Some Google changes may already have completed; retry safely. Local bookings are unchanged.', 'error')
    except sqlite3.Error:
        return flash_redirect('/doctor/dashboard#schedule', 'Could not record calendar sync status. Retry safely; local bookings are unchanged.', 'error')


@app.post('/doctor/calendar/disconnect')
def calendar_disconnect(user: dict[str, Any] = Depends(require_user), csrf_token: str = Form(...)):
    require_role(user, 'doctor')
    check_csrf(user, csrf_token)
    with read_db() as conn:
        connection = conn.execute('SELECT refresh_cipher FROM google_calendar_connections WHERE doctor_id=?', (user['id'],)).fetchone()
    message = 'Google Calendar disconnected. Existing exported events remain in Google.'
    if connection:
        try:
            gcal.request_json('POST', 'https://oauth2.googleapis.com/revoke', data={'token': gcal.decrypt(connection['refresh_cipher'])}, form=True)
        except gcal.CalendarError:
            message += ' Also remove SlotZero access in your Google account permissions.'
        with transaction(immediate=True) as conn:
            conn.execute('DELETE FROM google_calendar_connections WHERE doctor_id=?', (user['id'],))
            conn.execute('DELETE FROM google_calendar_states WHERE doctor_id=?', (user['id'],))
    return flash_redirect('/doctor/dashboard#schedule', message)


@app.middleware('http')
async def private_calendar_responses(request: Request, call_next):
    response = await call_next(request)
    if request.scope['path'] == '/doctor/calendar/callback':
        request.scope['query_string'] = b''
    if request.url.path.startswith('/doctor/calendar'):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@app.get("/health")
def health():
    return {"status": "ok", "service": "slotzero"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
