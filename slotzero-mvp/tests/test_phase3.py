from datetime import datetime, timedelta, timezone
import multiprocessing
import os
import sqlite3
from urllib.parse import unquote_plus

import pytest
from fastapi.testclient import TestClient

import app as slotzero
from test_reschedule import booking, snapshot
from test_phase2 import accounts, block_data, schedule_data


DAY = slotzero.parse_date("2026-11-02")


def book(client, user, doctor_id, start="2026-11-02T10:00:00Z", key="phase3", **extra):
    return client.post("/appointments/book", data={"csrf_token": user["csrf_token"], "doctor_id": doctor_id,
        "slot_start": start, "idempotency_key": key, **extra}, follow_redirects=False)


def notice(response):
    assert response.status_code == 303
    return unquote_plus(response.headers["location"])


@pytest.mark.parametrize("start", ["2026-11-02T10:00:00.5Z", "2026-11-02T10:00:00", "invalid"])
def test_invalid_timestamp_is_not_reinterpreted(accounts, start):
    client, user = accounts["asha"]
    before = snapshot()
    response = book(client, user, accounts["meera"][1]["id"], start=start)
    assert "Invalid appointment time" in notice(response)
    assert snapshot() == before


def test_booking_lock_timeout_is_controlled(accounts, monkeypatch):
    client, user = accounts["asha"]
    doctor_id = accounts["meera"][1]["id"]
    original_connect = slotzero.db_connect
    before = snapshot()
    with slotzero.transaction(immediate=True):
        def short_timeout():
            conn = original_connect()
            conn.execute("PRAGMA busy_timeout=50")
            return conn
        monkeypatch.setattr(slotzero, "db_connect", short_timeout)
        response = book(client, user, doctor_id, key="busy-retry")
        assert "busy" in notice(response) and "notice_type=error" in notice(response)
    assert snapshot() == before
    assert "Appointment confirmed" in notice(book(client, user, doctor_id, key="busy-retry"))


@pytest.mark.parametrize("doctor_case", ["missing", "patient", "role_changed"])
def test_only_existing_doctor_accounts_are_bookable(accounts, doctor_case):
    client, user = accounts["asha"]
    doctor_id = accounts["meera"][1]["id"]
    if doctor_case == "missing":
        doctor_id = 999999
    elif doctor_case == "patient":
        doctor_id = user["id"]
    else:
        with slotzero.transaction() as conn:
            conn.execute("UPDATE users SET role='patient' WHERE id=?", (doctor_id,))
    before = snapshot()
    assert slotzero.get_available_slots(doctor_id, DAY, "Asia/Kolkata") == []
    assert client.get(f"/doctors/{doctor_id}").status_code == 404
    assert "no longer available" in notice(book(client, user, doctor_id))
    assert snapshot() == before


def test_unavailable_doctor_preserves_reschedule(accounts, booking):
    client, user = accounts["asha"]
    with slotzero.transaction() as conn:
        conn.execute("UPDATE users SET role='patient' WHERE id=?", (accounts["meera"][1]["id"],))
    before = snapshot()
    response = client.post(f"/appointments/{booking[4]}/reschedule", data={"csrf_token": user["csrf_token"],
        "slot_start": "2026-11-02T10:00:00Z"}, follow_redirects=False)
    assert "original appointment is unchanged" in notice(response)
    assert snapshot() == before


@pytest.mark.parametrize("case,message", [("no_schedule", "has not configured working hours"),
    ("past", "date is in the past"), ("blocked", "fully booked or unavailable")])
def test_patient_empty_states(accounts, case, message):
    client, _ = accounts["asha"]
    doctor_id = accounts["alex"][1]["id"]
    day = "2026-11-02"
    if case == "past":
        day = "2026-10-30"
    elif case == "blocked":
        doctor, user = accounts["alex"]
        doctor.post("/doctor/schedule", data=schedule_data(user, schedule_text="Mon: 12:00-13:00"))
        doctor.post("/doctor/blocks", data=block_data(user))
    response = client.get(f"/doctors/{doctor_id}?date={day}")
    assert response.status_code == 200 and message in response.text
    assert 'action="/appointments/book"' not in response.text


@pytest.mark.parametrize("duration,expected", [(15, 6), (30, 3), (60, 1)])
def test_slots_fit_single_split_interval(accounts, duration, expected):
    client, user = accounts["alex"]
    response = client.post("/doctor/schedule", data=schedule_data(user,
        schedule_text="Mon: 09:00-10:10,10:20-11:00", consultation_minutes=duration))
    assert "updated" in response.text
    slots = slotzero.get_available_slots(user["id"], DAY, "Asia/Kolkata")
    assert len(slots) == expected
    for slot in slots:
        start, end = slotzero.db_to_dt(slot["start_utc"]), slotzero.db_to_dt(slot["end_utc"])
        assert end - start == timedelta(minutes=duration)
        assert (datetime(2026, 11, 2, 14, tzinfo=timezone.utc) <= start < end <= datetime(2026, 11, 2, 15, 10, tzinfo=timezone.utc)
                or datetime(2026, 11, 2, 15, 20, tzinfo=timezone.utc) <= start < end <= datetime(2026, 11, 2, 16, tzinfo=timezone.utc))


@pytest.mark.parametrize("zone,start_utc,patient_clock", [
    ("Europe/London", "2026-11-02T09:00:00Z", "02:30 PM"),
    ("America/New_York", "2026-11-02T14:00:00Z", "07:30 PM"),
    ("Asia/Kolkata", "2026-11-02T03:30:00Z", "09:00 AM"),
])
def test_booking_same_instant_in_both_dashboards(accounts, zone, start_utc, patient_clock):
    doctor, doctor_user = accounts["alex"]
    patient, user = accounts["asha"]
    doctor.post("/doctor/schedule", data=schedule_data(doctor_user, timezone_name=zone, schedule_text="Mon: 09:00-10:00"))
    discovery = patient.get("/patient/dashboard")
    assert any(row["id"] == doctor_user["id"] for row in discovery.context["doctors"])
    page = patient.get(f"/doctors/{doctor_user['id']}?date=2026-11-02")
    assert page.context["slots"][0]["start_utc"] == start_utc
    assert patient_clock in page.context["slots"][0]["patient_time"]
    assert "09:00 AM" in page.context["slots"][0]["doctor_time"]
    assert "Appointment confirmed" in notice(book(patient, user, doctor_user["id"], start=start_utc))
    patient_row = next(a for a in patient.get("/patient/dashboard").context["upcoming"] if a["doctor_id"] == doctor_user["id"])
    doctor_row = doctor.get("/doctor/dashboard?date=2026-11-02").context["appointments"][0]
    assert patient_row["id"] == doctor_row["id"]
    assert patient_row["start_utc"] == doctor_row["start_utc"] == start_utc
    assert patient_clock in patient_row["start_display"] and "09:00 AM" in doctor_row["start_display"]


def test_partial_overlaps_and_adjacent_boundaries(accounts):
    doctor, doctor_user = accounts["alex"]
    patient, user = accounts["asha"]
    doctor_id = doctor_user["id"]
    doctor.post("/doctor/schedule", data=schedule_data(doctor_user, timezone_name="Europe/London", schedule_text="Mon: 09:00-12:00"))
    assert "Appointment confirmed" in notice(book(patient, user, doctor_id))
    # Shift the candidate grid in this isolated DB to exercise both partial overlaps.
    with slotzero.transaction() as conn:
        conn.execute("UPDATE schedules SET intervals_json=? WHERE doctor_id=? AND weekday=0", ('[["09:15","12:00"]]', doctor_id))
    starts = [slot["start_utc"] for slot in slotzero.get_available_slots(doctor_id, DAY, "Asia/Kolkata")]
    assert starts == ["2026-11-02T09:15:00Z", "2026-11-02T10:45:00Z", "2026-11-02T11:15:00Z"]
    before = snapshot()
    for clock in ("09:45", "10:00", "10:15"):
        assert "unavailable" in notice(book(patient, user, doctor_id, start=f"2026-11-02T{clock}:00Z", key=clock))
    assert snapshot() == before
    doctor.post("/doctor/schedule", data=schedule_data(doctor_user, timezone_name="Europe/London", schedule_text="Mon: 09:00-12:00"))
    for clock in ("09:30", "10:30"):
        assert "Appointment confirmed" in notice(book(patient, user, doctor_id, start=f"2026-11-02T{clock}:00Z", key=clock))


def test_block_exclusion_and_date_boundaries(accounts):
    doctor, user = accounts["alex"]
    doctor.post("/doctor/schedule", data=schedule_data(user, timezone_name="Asia/Kolkata", schedule_text="Mon: 00:00-01:00", consultation_minutes=15))
    with slotzero.transaction() as conn:
        for start, end in [("2026-11-01T18:20:00Z", "2026-11-01T18:40:00Z"),
                           ("2026-11-02T18:30:00Z", "2026-11-02T19:30:00Z")]:
            conn.execute("INSERT INTO blocked_periods(doctor_id,start_utc,end_utc,created_at) VALUES(?,?,?,?)",
                (user["id"], start, end, slotzero.dt_to_db(slotzero.utc_now())))
    starts = [slot["start_utc"] for slot in slotzero.get_available_slots(user["id"], DAY, "Asia/Kolkata")]
    assert starts == ["2026-11-01T18:45:00Z", "2026-11-01T19:00:00Z", "2026-11-01T19:15:00Z"]


def test_past_and_cancelled_appointments(accounts, booking, monkeypatch):
    client, user = accounts["asha"]
    doctor_id = accounts["meera"][1]["id"]
    assert slotzero.get_available_slots(doctor_id, slotzero.parse_date("2026-10-26"), "Asia/Kolkata") == []
    assert "unavailable" in notice(book(client, user, doctor_id, start="2026-10-26T10:00:00Z"))
    response = client.post(f"/appointments/{booking[4]}/cancel", data={"csrf_token": user["csrf_token"]}, follow_redirects=False)
    assert "cancelled" in notice(response)
    assert "2026-11-02T09:00:00Z" in [s["start_utc"] for s in slotzero.get_available_slots(doctor_id, DAY, "Asia/Kolkata")]
    monkeypatch.setattr(slotzero, "utc_now", lambda: datetime(2026, 11, 2, 10, tzinfo=timezone.utc))
    slots = slotzero.get_available_slots(doctor_id, DAY, "Asia/Kolkata")
    assert slots[0]["start_utc"] == "2026-11-02T10:30:00Z"
    before = snapshot()
    assert "unavailable" in notice(book(client, user, doctor_id, start="2026-11-02T10:00:00Z", key="now"))
    assert snapshot() == before


@pytest.mark.parametrize("change", ["hours", "duration", "zone", "block", "booking"])
def test_stale_availability_rechecked(accounts, change):
    patient, user = accounts["asha"]
    doctor, doctor_user = accounts["meera"]
    doctor_id = doctor_user["id"]
    target = "2026-11-02T10:30:00Z"
    page = patient.get(f"/doctors/{doctor_id}?date=2026-11-02")
    assert target in [s["start_utc"] for s in page.context["slots"]]
    if change == "hours":
        doctor.post("/doctor/schedule", data=schedule_data(doctor_user, schedule_text="Mon: 09:00-10:00"))
    elif change == "duration":
        doctor.post("/doctor/schedule", data=schedule_data(doctor_user, consultation_minutes=60))
    elif change == "zone":
        doctor.post("/doctor/schedule", data=schedule_data(doctor_user, timezone_name="America/New_York", schedule_text="Mon: 04:00-05:00"))
    elif change == "block":
        doctor.post("/doctor/blocks", data=block_data(doctor_user, start_time="10:30", end_time="11:00"))
    else:
        other, stranger = accounts["sam"]
        assert "Appointment confirmed" in notice(book(other, stranger, doctor_id, start=target, key="taken"))
    before = snapshot()
    rejected = book(patient, user, doctor_id, start=target)
    assert "unavailable" in notice(rejected)
    assert "unavailable" in patient.get(rejected.headers["location"]).text
    assert snapshot() == before


def test_modified_identity_duration_and_slot_end_are_not_trusted(accounts):
    client, user = accounts["asha"]
    doctor_id = accounts["meera"][1]["id"]
    assert "Appointment confirmed" in notice(book(client, user, doctor_id,
        patient_id=accounts["sam"][1]["id"], consultation_minutes=60, slot_end="2026-11-02T11:00:00Z", role="doctor"))
    with slotzero.read_db() as conn:
        row = conn.execute("SELECT * FROM appointments WHERE idempotency_key='phase3'").fetchone()
    assert row["patient_id"] == user["id"]
    assert row["end_utc"] == "2026-11-02T10:30:00Z"
    before = snapshot()
    for start in ("2026-11-02T10:01:00Z", "2026-11-02T12:00:00Z"):
        assert "unavailable" in notice(book(client, user, doctor_id, start=start, key=start))
    assert snapshot() == before


def test_idempotency_retries_do_not_duplicate_or_repurpose(accounts):
    client, user = accounts["asha"]
    doctor_id = accounts["meera"][1]["id"]
    assert "Appointment confirmed" in notice(book(client, user, doctor_id))
    before = snapshot()
    assert "already confirmed" in notice(book(client, user, doctor_id, start="2026-11-02T15:30:00+05:30"))
    assert "already used for another booking" in notice(book(client, user, doctor_id, start="2026-11-02T10:30:00Z"))
    assert "already used for another booking" in notice(book(client, user, accounts["alex"][1]["id"]))
    assert snapshot() == before
    appointment_id = before["appointments"][-1]["id"]
    client.post(f"/appointments/{appointment_id}/cancel", data={"csrf_token": user["csrf_token"]})
    cancelled = snapshot()
    assert "appointment is cancelled" in notice(book(client, user, doctor_id))
    assert snapshot() == cancelled
    other, stranger = accounts["sam"]
    assert "Appointment confirmed" in notice(book(other, stranger, doctor_id))


@pytest.mark.parametrize("key", ["   ", "x" * 101])
def test_invalid_idempotency_key(accounts, key):
    client, user = accounts["asha"]
    before = snapshot()
    assert "Invalid booking request" in notice(book(client, user, accounts["meera"][1]["id"], key=key))
    assert snapshot() == before


def test_fully_booked_day_and_no_schedule_booking(accounts):
    doctor, doctor_user = accounts["meera"]
    patient, user = accounts["asha"]
    doctor.post("/doctor/schedule", data=schedule_data(doctor_user, schedule_text="Mon: 09:00-10:00"))
    page = patient.get(f"/doctors/{doctor_user['id']}?date=2026-11-02")
    assert page.context["slots"] == [] and "fully booked or unavailable" in page.text
    before = snapshot()
    assert "unavailable" in notice(book(patient, user, accounts["alex"][1]["id"]))
    assert snapshot() == before


@pytest.mark.parametrize("start,end", [("09:45", "10:15"), ("10:15", "10:45"), ("10:00", "10:30")])
def test_database_triggers_reject_overlap_on_insert_and_update(accounts, start, end):
    patient, user = accounts["asha"]
    doctor_id = accounts["meera"][1]["id"]
    assert "Appointment confirmed" in notice(book(patient, user, doctor_id))
    with slotzero.read_db() as conn:
        params = (doctor_id, user["id"], f"2026-11-02T{start}:00Z", f"2026-11-02T{end}:00Z", "direct", "2026-11-01T00:00:00Z", "2026-11-01T00:00:00Z")
        sql = "INSERT INTO appointments(doctor_id,patient_id,start_utc,end_utc,idempotency_key,created_at,updated_at,status) VALUES(?,?,?,?,?,?,?,?)"
        with pytest.raises(sqlite3.IntegrityError, match="appointment_overlap"):
            conn.execute(sql, (*params, "confirmed"))
        cancelled = conn.execute(sql, (*params, "cancelled")).lastrowid
        with pytest.raises(sqlite3.IntegrityError, match="appointment_overlap"):
            conn.execute("UPDATE appointments SET status='confirmed' WHERE id=?", (cancelled,))
        assert conn.execute("SELECT status FROM appointments WHERE id=?", (cancelled,)).fetchone()[0] == "cancelled"


def test_booking_event_failure_rolls_back_insert(accounts):
    client, user = accounts["asha"]
    before = snapshot()
    with slotzero.read_db() as conn:
        conn.execute("CREATE TRIGGER fail_test_event BEFORE INSERT ON appointment_events BEGIN SELECT RAISE(ABORT, 'test failure'); END")
    response = book(client, user, accounts["meera"][1]["id"])
    assert "notice_type=error" in notice(response)
    assert snapshot() == before


def _booking_process(db_path, cookie, payload, barrier, results):
    """Each spawned process has its own ASGI app and SQLite connections."""
    slotzero.DB_PATH = db_path
    slotzero.utc_now = lambda: datetime(2026, 11, 1, tzinfo=timezone.utc)
    original_connect = slotzero.db_connect
    reached_lock = False

    def connect():
        conn = original_connect()
        def trace(sql):
            nonlocal reached_lock
            if sql == "BEGIN IMMEDIATE":
                barrier.wait(timeout=15)
                reached_lock = True
        conn.set_trace_callback(trace)
        return conn

    slotzero.db_connect = connect
    client = TestClient(slotzero.app)
    try:
        client.cookies.set("slotzero_session", cookie)
        response = client.post("/appointments/book", data=payload, follow_redirects=False)
        results.put((os.getpid(), reached_lock, response.status_code, response.headers.get("location", "")))
    finally:
        client.close()


@pytest.mark.parametrize("race", ["same_slot", "adjacent", "duplicate"])
def test_concurrent_booking_across_processes(accounts, race):
    context = multiprocessing.get_context("spawn")
    barrier, results = context.Barrier(2), context.Queue()
    doctor_id = accounts["meera"][1]["id"]
    before = snapshot()
    workers = []
    for index, name in enumerate(("asha", "asha" if race == "duplicate" else "sam")):
        client, user = accounts[name]
        payload = {"csrf_token": user["csrf_token"], "doctor_id": doctor_id,
            "slot_start": "2026-11-02T10:30:00Z" if race == "adjacent" and index else "2026-11-02T10:00:00Z",
            "idempotency_key": "concurrent-same" if race == "duplicate" else f"concurrent-{index}"}
        workers.append(context.Process(target=_booking_process,
            args=(slotzero.DB_PATH, client.cookies.get("slotzero_session"), payload, barrier, results)))
    try:
        for worker in workers:
            worker.start()
        replies = [results.get(timeout=25) for _ in workers]
        for worker in workers:
            worker.join(timeout=5)
            assert worker.exitcode == 0
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
        results.close()
    assert len({reply[0] for reply in replies}) == 2
    assert all(reply[1] and reply[2] == 303 for reply in replies)
    messages = [unquote_plus(reply[3]) for reply in replies]
    assert sum("Appointment confirmed" in message for message in messages) == (2 if race == "adjacent" else 1)
    if race == "same_slot":
        assert sum("unavailable" in message and "notice_type=error" in message for message in messages) == 1
    elif race == "duplicate":
        assert sum("already confirmed" in message for message in messages) == 1
    after = snapshot()
    expected = 2 if race == "adjacent" else 1
    assert len(after["appointments"]) - len(before["appointments"]) == expected
    assert len(after["appointment_events"]) - len(before["appointment_events"]) == expected
    with slotzero.read_db() as conn:
        assert conn.execute("SELECT a.id FROM appointments a JOIN appointments b ON a.id<b.id AND a.doctor_id=b.doctor_id "
            "WHERE a.status='confirmed' AND b.status='confirmed' AND a.start_utc<b.end_utc AND a.end_utc>b.start_utc").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
