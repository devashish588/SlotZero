import hashlib
import json
import sqlite3
from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient

import app as slotzero
from test_reschedule import booking, snapshot  # Reuse Phase 1's isolated bookings and clock.


@pytest.fixture
def accounts(booking):
    owner, other, patient, stranger, appointment_id, slots = booking
    with ExitStack() as stack:
        result = {"asha": (owner, patient), "sam": (other, stranger)}
        for name in ("meera", "alex"):
            client = stack.enter_context(TestClient(slotzero.app))
            response = client.post("/login", data={"email": f"{name}@slotzero.demo", "password": f"{name.title()}@123"}, follow_redirects=False)
            assert response.status_code == 303
            result[name] = (client, slotzero.get_current_user(type("Request", (), {"cookies": client.cookies})()))
        result["anonymous"] = (stack.enter_context(TestClient(slotzero.app)), {})
        yield result


def state():
    with slotzero.read_db() as conn:
        return {table: [tuple(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1,2")]
                for table in ("users", "doctors", "schedules", "blocked_periods", "appointments", "appointment_events")}


def schedule_data(user, **changes):
    return {"csrf_token": user["csrf_token"], "schedule_text": "Mon: 09:00-12:00,13:00-17:00\nTue:",
            "consultation_minutes": 30, "timezone_name": user["timezone"], **changes}


def block_data(user, **changes):
    return {"csrf_token": user["csrf_token"], "block_date": "2026-11-02", "start_time": "12:00",
            "end_time": "13:00", "label": "Break", **changes}


PROTECTED = [
    ("GET", "/doctor/dashboard"), ("GET", "/patient/dashboard"), ("GET", "/doctors/1"),
    ("GET", "/appointments/1/reschedule"), ("POST", "/doctor/schedule"),
    ("POST", "/doctor/blocks"), ("POST", "/doctor/blocks/1/delete"),
    ("POST", "/appointments/book"), ("POST", "/appointments/1/cancel"),
    ("POST", "/appointments/1/reschedule"), ("POST", "/logout"),
]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_anonymous_requests_rejected(accounts, method, path):
    before = state()
    response = accounts["anonymous"][0].request(method, path, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/login"
    assert state() == before


@pytest.mark.parametrize("session_kind", ["invalid", "expired", "logged_out"])
def test_invalid_sessions(accounts, session_kind):
    client, user = accounts["meera"]
    raw = client.cookies.get("slotzero_session")
    if session_kind == "expired":
        with slotzero.transaction() as conn:
            conn.execute("UPDATE sessions SET expires_at=? WHERE user_id=?", ("2026-10-31T00:00:00Z", user["id"]))
    elif session_kind == "logged_out":
        client.post("/logout", data={"csrf_token": user["csrf_token"]})
    else:
        raw = "forged-token"
    client.cookies.clear()
    client.cookies.set("slotzero_session", raw)
    before = state()
    for method, path in PROTECTED:
        response = client.request(method, path, follow_redirects=False)
        assert response.status_code == 303 and response.headers["location"] == "/login"
    assert state() == before


def test_roles_ownership_and_private_views(accounts, booking):
    _, _, _, _, appointment_id, slots = booking
    before = state()
    patient, patient_user = accounts["asha"]
    doctor, doctor_user = accounts["alex"]
    for path, data in [("/doctor/schedule", schedule_data(patient_user)), ("/doctor/blocks", block_data(patient_user)),
                       ("/doctor/blocks/1/delete", {"csrf_token": patient_user["csrf_token"]})]:
        assert patient.post(path, data={**data, "role": "doctor", "user_id": doctor_user["id"]}).status_code == 403
    assert patient.get("/doctor/dashboard").status_code == 403
    assert doctor.get("/patient/dashboard").status_code == 403
    assert doctor.get("/doctors/1").status_code == 403
    assert doctor.get(f"/appointments/{appointment_id}/reschedule").status_code == 403
    for path, extra in [("/appointments/book", {"doctor_id": 1, "idempotency_key": "forged"}),
                        (f"/appointments/{appointment_id}/reschedule", {}), (f"/appointments/{appointment_id}/cancel", {})]:
        assert doctor.post(path, data={"csrf_token": doctor_user["csrf_token"], "slot_start": slots[2]["start_utc"], **extra}).status_code == 403
    other, stranger = accounts["sam"]
    assert other.get(f"/appointments/{appointment_id}/reschedule").status_code == 404
    for action in ("cancel", "reschedule"):
        assert other.post(f"/appointments/{appointment_id}/{action}", data={"csrf_token": stranger["csrf_token"], "slot_start": slots[2]["start_utc"], "patient_id": patient_user["id"]}).status_code == 404
    assert {a["patient_id"] for a in patient.get(f"/patient/dashboard?patient_id={stranger['id']}").context["upcoming"]} == {patient_user["id"]}
    meera, meera_user = accounts["meera"]
    own = meera.get(f"/doctor/dashboard?date=2026-11-02&doctor_id={doctor_user['id']}")
    assert len(own.context["appointments"]) == 2
    assert {a["doctor_id"] for a in own.context["appointments"]} == {meera_user["id"]}
    foreign = doctor.get(f"/doctor/dashboard?date=2026-11-02&doctor_id={meera_user['id']}")
    assert foreign.context["appointments"] == [] and foreign.context["history"] == []
    assert foreign.context["profile"]["id"] == doctor_user["id"]
    assert state() == before


@pytest.mark.parametrize("duration", [15, 30, 60])
@pytest.mark.parametrize("zone", slotzero.ALLOWED_ZONES)
def test_doctor_configuration_and_ownership(accounts, duration, zone):
    client, user = accounts["alex"]
    meera_id = accounts["meera"][1]["id"]
    before = state()
    response = client.post("/doctor/schedule", data=schedule_data(user, consultation_minutes=duration, timezone_name=zone, doctor_id=meera_id))
    assert response.status_code == 200 and "updated" in response.text
    assert response.context["profile"]["consultation_minutes"] == duration
    assert response.context["user"]["timezone"] == zone
    assert user["email"] in response.text and user["full_name"] in response.text
    assert f'value="{zone}" selected' in response.text
    with slotzero.read_db() as conn:
        rows = conn.execute("SELECT * FROM schedules WHERE doctor_id=? ORDER BY weekday", (user["id"],)).fetchall()
        assert len(rows) == 7
        assert json.loads(rows[0]["intervals_json"]) == [["09:00", "12:00"], ["13:00", "17:00"]]
        assert json.loads(rows[1]["intervals_json"]) == []
    after = state()
    for table in ("users", "doctors", "schedules"):
        assert [row for row in before[table] if row[0] == meera_id] == [row for row in after[table] if row[0] == meera_id]
    assert before["appointments"] == after["appointments"]
    slots = slotzero.get_available_slots(user["id"], slotzero.parse_date("2026-11-02"), "Asia/Kolkata")
    assert len(slots) == 420 // duration


@pytest.mark.parametrize("changes", [
    {"schedule_text": "Funday: 09:00-12:00"}, {"schedule_text": "Monjunk: 09:00-12:00"},
    {"schedule_text": "Mon: 12:00-09:00"}, {"schedule_text": "Mon: 09:00-09:00"},
    {"schedule_text": "Mon: 09:00-12:00,11:00-13:00"}, {"schedule_text": "Mon: 25:00-26:00"},
    {"schedule_text": "Mon: 09:00-12:00\nMon:"}, {"schedule_text": "Mon: 09:00"},
    {"schedule_text": "Mon: 09:00Z-12:00"}, {"schedule_text": "Mon: 09:00:00.1-12:00"},
    {"schedule_text": "Mon: 0900-1200"}, {"schedule_text": "Mon: 09:00-12:00,"},
    {"schedule_text": "   "}, {"consultation_minutes": 45}, {"consultation_minutes": "bad"},
    {"timezone_name": "UTC"}, {"timezone_name": "+05:30"}, {"timezone_name": "Fake/Zone"},
])
def test_invalid_configuration_is_atomic(accounts, changes):
    client, user = accounts["alex"]
    before = state()
    response = client.post("/doctor/schedule", data=schedule_data(user, **changes), follow_redirects=False)
    assert response.status_code == 422 or (response.status_code == 303 and "notice_type=error" in response.headers["location"])
    assert state() == before


def test_schedule_and_timezone_changes_preserve_bookings(accounts):
    client, user = accounts["meera"]
    before = state()
    for changes in ({"schedule_text": "Mon:"}, {"timezone_name": "America/New_York"}):
        response = client.post("/doctor/schedule", data=schedule_data(user, **changes))
        assert "exclude an existing confirmed appointment" in response.text
        assert state() == before
    response = client.post("/doctor/schedule", data=schedule_data(user, timezone_name="America/New_York", schedule_text="Mon: 04:00-07:00"))
    assert "updated" in response.text
    assert state()["appointments"] == before["appointments"]
    assert state()["appointment_events"] == before["appointment_events"]


@pytest.mark.parametrize("changes", [
    {"block_date": "2026-02-31"}, {"block_date": "2026-10-31"},
    {"start_time": "14:00"}, {"start_time": "13:00"}, {"start_time": "bad"},
    {"start_time": "12:00Z"}, {"start_time": "25:00"},
    {"block_date": "2027-03-28", "start_time": "01:15", "end_time": "02:00"},
    {"block_date": "2027-10-31", "start_time": "01:15", "end_time": "02:00"},
])
def test_invalid_blocks_preserve_data(accounts, changes):
    client, user = accounts["meera"]
    before = state()
    response = client.post("/doctor/blocks", data=block_data(user, **changes), follow_redirects=False)
    assert response.status_code == 303 and "notice_type=error" in response.headers["location"]
    assert state() == before


def test_blocks_conflicts_ownership_and_availability(accounts, booking):
    client, user = accounts["meera"]
    other, other_user = accounts["alex"]
    before = snapshot()
    response = client.post("/doctor/blocks", data=block_data(user, start_time="09:00", end_time="09:30"))
    assert f"appointment #{booking[4]}" in response.text
    with slotzero.read_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM blocked_periods").fetchone()[0] == 0
    response = client.post("/doctor/blocks", data=block_data(user, start_time="10:00", end_time="10:30", doctor_id=other_user["id"]))
    assert "Unavailable period added" in response.text
    with slotzero.read_db() as conn:
        block = dict(conn.execute("SELECT * FROM blocked_periods").fetchone())
    assert block["doctor_id"] == user["id"] and block["start_utc"] == "2026-11-02T10:00:00Z"
    assert all(slot["start_utc"] != block["start_utc"] for slot in slotzero.get_available_slots(user["id"], slotzero.parse_date("2026-11-02"), "Asia/Kolkata"))
    other.post(f"/doctor/blocks/{block['id']}/delete", data={"csrf_token": other_user["csrf_token"]})
    assert other.get("/doctor/dashboard").context["blocked_periods"] == []
    with slotzero.read_db() as conn:
        assert dict(conn.execute("SELECT * FROM blocked_periods").fetchone()) == block
    client.post(f"/doctor/blocks/{block['id']}/delete", data={"csrf_token": user["csrf_token"]})
    assert any(slot["start_utc"] == block["start_utc"] for slot in slotzero.get_available_slots(user["id"], slotzero.parse_date("2026-11-02"), "Asia/Kolkata"))
    assert snapshot() == before


def test_csrf_and_unsupported_methods(accounts):
    before = state()
    for name, paths in [("meera", ["/doctor/schedule", "/doctor/blocks", "/doctor/blocks/1/delete"]),
                        ("asha", ["/appointments/book", "/appointments/1/cancel", "/appointments/1/reschedule", "/logout"])]:
        client, user = accounts[name]
        data = {**schedule_data(user), **block_data(user), "slot_start": "2026-11-02T10:00:00Z", "doctor_id": 1, "idempotency_key": "csrf"}
        for path in paths:
            for token in (None, "forged", accounts["sam"][1]["csrf_token"]):
                payload = {k: v for k, v in data.items() if k != "csrf_token"}
                if token is not None:
                    payload["csrf_token"] = token
                assert client.post(path, data=payload).status_code in (403, 422)
            for method in ("PUT", "PATCH", "DELETE"):
                assert client.request(method, path, data=data).status_code == 405
    assert state() == before


def test_registration_session_storage_and_database_integrity(accounts):
    client, _ = accounts["anonymous"]
    response = client.post("/register", data={"full_name": "Role Attempt", "email": "role@example.test", "password": "test-password-123", "timezone_name": "Asia/Kolkata", "role": "doctor"})
    assert response.status_code == 200
    with slotzero.read_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email='role@example.test'").fetchone()
        assert row["role"] == "patient" and row["password_hash"].startswith("scrypt$")
        assert conn.execute("SELECT * FROM doctors WHERE user_id=?", (row["id"],)).fetchone() is None
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        raw = accounts["meera"][0].cookies.get("slotzero_session")
        assert conn.execute("SELECT * FROM sessions WHERE token_hash=?", (hashlib.sha256(raw.encode()).hexdigest(),)).fetchone()
        assert conn.execute("SELECT * FROM sessions WHERE token_hash=?", (raw,)).fetchone() is None
        for sql in ["UPDATE users SET role='admin' WHERE id=1", "UPDATE doctors SET consultation_minutes=45 WHERE user_id=1",
                    "INSERT INTO schedules VALUES(999999,0,'[]')", "INSERT INTO schedules VALUES(1,7,'[]')"]:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(sql)


def test_existing_demo_accounts_and_restart_are_preserved(accounts):
    before = state()
    slotzero.init_db()
    assert state() == before
    for name, role, zone in [("meera", "doctor", "Europe/London"), ("alex", "doctor", "America/New_York"),
                             ("asha", "patient", "Asia/Kolkata"), ("sam", "patient", "America/New_York")]:
        assert accounts[name][1]["role"] == role
        assert accounts[name][1]["timezone"] == zone


@pytest.mark.parametrize("field", ["schedule_text", "consultation_minutes"])
def test_incomplete_schedule_rejected(accounts, field):
    client, user = accounts["alex"]
    before = state()
    payload = schedule_data(user)
    del payload[field]
    response = client.post("/doctor/schedule", data=payload)
    assert response.status_code == 422 and field in response.text
    assert state() == before


def test_legacy_schedule_form_and_blocks_after_zone_change(accounts):
    client, user = accounts["alex"]
    payload = schedule_data(user)
    del payload["timezone_name"]
    assert "updated" in client.post("/doctor/schedule", data=payload).text
    assert client.get("/doctor/dashboard").context["user"]["timezone"] == "America/New_York"
    assert "updated" in client.post("/doctor/schedule", data=schedule_data(user, timezone_name="Asia/Kolkata")).text
    assert "Unavailable period added" in client.post("/doctor/blocks", data=block_data(user)).text
    with slotzero.read_db() as conn:
        block = conn.execute("SELECT * FROM blocked_periods WHERE doctor_id=?", (user["id"],)).fetchone()
        assert block["start_utc"] == "2026-11-02T06:30:00Z"
    client.post("/doctor/schedule", data=schedule_data(user, timezone_name="Europe/London"))
    with slotzero.read_db() as conn:
        assert dict(conn.execute("SELECT * FROM blocked_periods WHERE id=?", (block["id"],)).fetchone()) == dict(block)
