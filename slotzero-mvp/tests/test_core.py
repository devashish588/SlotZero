from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

import pytest

import app as slotzero


def test_schedule_parser_supports_split_shifts_and_closed_days():
    parsed = slotzero.parse_schedule_text(
        "Mon: 09:00-12:00,13:00-17:00\nTue: 10:00-15:00\nWed:\nThu: 09:00-11:00\nFri:\nSat:\nSun:"
    )
    assert parsed[0] == [["09:00", "12:00"], ["13:00", "17:00"]]
    assert parsed[1] == [["10:00", "15:00"]]
    assert parsed[2] == []


def test_schedule_parser_rejects_overlapping_ranges():
    with pytest.raises(ValueError, match="overlap"):
        slotzero.parse_schedule_text("Mon: 09:00-12:00,11:30-13:00")


def test_dst_nonexistent_london_time_is_rejected():
    with pytest.raises(ValueError, match="does not exist"):
        slotzero.local_to_utc_strict(datetime(2026, 3, 29, 1, 30), "Europe/London")


def test_dst_ambiguous_london_time_is_rejected():
    with pytest.raises(ValueError, match="ambiguous"):
        slotzero.local_to_utc_strict(datetime(2026, 10, 25, 1, 30), "Europe/London")


def test_normal_local_time_converts_to_utc():
    result = slotzero.local_to_utc_strict(datetime(2026, 11, 2, 10, 0), "Europe/London")
    assert result.tzinfo == timezone.utc
    assert result.hour == 10  # London is on GMT on this date.




def test_invalid_dates_and_naive_timestamps_are_rejected():
    with pytest.raises(ValueError, match="valid calendar date"):
        slotzero.parse_date("2026-02-31")
    with pytest.raises(ValueError, match="timezone-aware"):
        slotzero.db_to_dt("2026-11-02T09:00:00")


def test_interval_overlap_allows_adjacent_bookings():
    base = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)
    assert not slotzero.interval_overlaps(base, base + timedelta(minutes=30), base + timedelta(minutes=30), base + timedelta(hours=1))
    assert slotzero.interval_overlaps(base, base + timedelta(minutes=30), base + timedelta(minutes=15), base + timedelta(minutes=45))


def test_demo_database_booking_guard_and_role_separation(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    db_path = tmp_path / "slotzero-test.db"
    monkeypatch.setattr(slotzero, "DB_PATH", str(db_path))
    slotzero.init_db()
    client = TestClient(slotzero.app)

    # Patient cannot access a doctor-only dashboard.
    login = client.post("/login", data={"email": "asha@slotzero.demo", "password": "Asha@123"}, follow_redirects=False)
    assert login.status_code == 303
    assert client.get("/doctor/dashboard").status_code == 403

    with slotzero.read_db() as conn:
        doctor_id = conn.execute("SELECT id FROM users WHERE email='meera@slotzero.demo'").fetchone()["id"]

    # The seeded doctor has no hours. The doctor must configure their own schedule.
    doctor_client = TestClient(slotzero.app)
    doctor_client.post("/login", data={"email": "meera@slotzero.demo", "password": "Meera@123"}, follow_redirects=False)
    doctor_user = slotzero.get_current_user(type("Req", (), {"cookies": {"slotzero_session": doctor_client.cookies.get("slotzero_session")}})())
    doctor_csrf = doctor_user["csrf_token"]
    setup_schedule = "\n".join([
        "Mon: 09:00-12:00,13:00-17:00", "Tue: 09:00-12:00,13:00-17:00",
        "Wed: 09:00-12:00,13:00-17:00", "Thu: 09:00-12:00,13:00-17:00",
        "Fri: 09:00-12:00,13:00-17:00", "Sat:", "Sun:",
    ])
    schedule_saved = doctor_client.post("/doctor/schedule", data={
        "csrf_token": doctor_csrf, "schedule_text": setup_schedule, "consultation_minutes": 30,
    }, follow_redirects=False)
    assert schedule_saved.status_code == 303

    # Find a future weekday after the doctor has configured working hours.
    doctor_zone = "Europe/London"
    today = slotzero.utc_now().astimezone(slotzero.ZoneInfo(doctor_zone)).date()
    target_day = next(today + timedelta(days=offset) for offset in range(1, 10) if (today + timedelta(days=offset)).weekday() < 5)
    slots = slotzero.get_available_slots(doctor_id, target_day, "Asia/Kolkata")
    assert slots, "seeded weekdays should generate slots"
    selected = slots[0]

    csrf = slotzero.get_current_user(type("Req", (), {"cookies": {"slotzero_session": client.cookies.get("slotzero_session")}})())
    csrf_token = csrf["csrf_token"]
    booking_data = {
        "csrf_token": csrf_token,
        "doctor_id": doctor_id,
        "slot_start": selected["start_utc"],
        "idempotency_key": "pytest-asha-booking-1",
    }
    booked = client.post("/appointments/book", data=booking_data, follow_redirects=False)
    assert booked.status_code == 303

    # Doctor cannot block an existing booking or save working hours that
    # exclude it. A separate open interval can be blocked and restored.
    booked_start = slotzero.db_to_dt(selected["start_utc"]).astimezone(slotzero.ZoneInfo(doctor_zone))
    booked_end = slotzero.db_to_dt(selected["end_utc"]).astimezone(slotzero.ZoneInfo(doctor_zone))
    rejected_block = doctor_client.post("/doctor/blocks", data={
        "csrf_token": doctor_csrf, "block_date": booked_start.date().isoformat(),
        "start_time": booked_start.strftime("%H:%M"), "end_time": booked_end.strftime("%H:%M"), "label": "Break",
    }, follow_redirects=False)
    assert "overlaps" in rejected_block.headers["location"]
    empty_schedule = "\n".join(["Mon:", "Tue:", "Wed:", "Thu:", "Fri:", "Sat:", "Sun:"])
    rejected_schedule = doctor_client.post("/doctor/schedule", data={
        "csrf_token": doctor_csrf, "schedule_text": empty_schedule, "consultation_minutes": 30,
    }, follow_redirects=False)
    assert "exclude" in rejected_schedule.headers["location"]

    open_slot = slots[3]
    open_start = slotzero.db_to_dt(open_slot["start_utc"]).astimezone(slotzero.ZoneInfo(doctor_zone))
    open_end = slotzero.db_to_dt(open_slot["end_utc"]).astimezone(slotzero.ZoneInfo(doctor_zone))
    created_block = doctor_client.post("/doctor/blocks", data={
        "csrf_token": doctor_csrf, "block_date": open_start.date().isoformat(),
        "start_time": open_start.strftime("%H:%M"), "end_time": open_end.strftime("%H:%M"), "label": "Break",
    }, follow_redirects=False)
    assert created_block.status_code == 303
    assert all(slot["start_utc"] != open_slot["start_utc"] for slot in slotzero.get_available_slots(doctor_id, target_day, "Asia/Kolkata"))
    with slotzero.read_db() as conn:
        block_id = conn.execute("SELECT id FROM blocked_periods WHERE doctor_id=? AND label='Break'", (doctor_id,)).fetchone()["id"]
    doctor_client.post(f"/doctor/blocks/{block_id}/delete", data={"csrf_token": doctor_csrf}, follow_redirects=False)
    assert any(slot["start_utc"] == open_slot["start_utc"] for slot in slotzero.get_available_slots(doctor_id, target_day, "Asia/Kolkata"))

    # A second patient cannot cancel the first patient's booking by ID.
    sam = TestClient(slotzero.app)
    sam.post("/login", data={"email": "sam@slotzero.demo", "password": "Sam@123"}, follow_redirects=False)
    sam_user = slotzero.get_current_user(type("Req", (), {"cookies": {"slotzero_session": sam.cookies.get("slotzero_session")}})())
    with slotzero.read_db() as conn:
        first_appointment_id = conn.execute("SELECT id FROM appointments WHERE patient_id=(SELECT id FROM users WHERE email='asha@slotzero.demo')").fetchone()["id"]
    forbidden_cancel = sam.post(
        f"/appointments/{first_appointment_id}/cancel", data={"csrf_token": sam_user["csrf_token"]}, follow_redirects=False
    )
    assert forbidden_cancel.status_code == 404

    # Same patient retry with same idempotency key creates only one record.
    client.post("/appointments/book", data=booking_data, follow_redirects=False)
    with slotzero.db_connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM appointments WHERE patient_id=(SELECT id FROM users WHERE email='asha@slotzero.demo')").fetchone()["n"]
    assert count == 1

    # A second patient trying the same slot is rejected, and the DB trigger
    # independently blocks direct overlapping confirmed inserts.
    response = sam.post(
        "/appointments/book",
        data={"csrf_token": sam_user["csrf_token"], "doctor_id": doctor_id, "slot_start": selected["start_utc"], "idempotency_key": "pytest-sam-booking-1"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "unavailable" in response.headers["location"] or "another" in response.headers["location"] or "booked" in response.headers["location"]

    with slotzero.db_connect() as conn:
        appt = conn.execute("SELECT * FROM appointments WHERE id=1").fetchone()
        with pytest.raises(Exception):
            conn.execute(
                "INSERT INTO appointments(doctor_id,patient_id,start_utc,end_utc,status,idempotency_key,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (doctor_id, sam_user["id"], appt["start_utc"], appt["end_utc"], "confirmed", "direct-overlap", appt["created_at"], appt["updated_at"]),
            )

    # The appointment can be rescheduled atomically, then cancelled. The old
    # slot is released once the booking is cancelled.
    with slotzero.db_connect() as conn:
        appointment_id = conn.execute("SELECT id FROM appointments WHERE patient_id=(SELECT id FROM users WHERE email='asha@slotzero.demo')").fetchone()["id"]
    moved = client.post(
        f"/appointments/{appointment_id}/reschedule",
        data={"csrf_token": csrf_token, "slot_start": slots[1]["start_utc"]},
        follow_redirects=False,
    )
    assert moved.status_code == 303
    with slotzero.db_connect() as conn:
        appointment = conn.execute("SELECT start_utc,status FROM appointments WHERE id=?", (appointment_id,)).fetchone()
    assert appointment["start_utc"] == slots[1]["start_utc"]
    assert appointment["status"] == "confirmed"

    cancelled = client.post(
        f"/appointments/{appointment_id}/cancel", data={"csrf_token": csrf_token}, follow_redirects=False
    )
    assert cancelled.status_code == 303
    with slotzero.db_connect() as conn:
        appointment = conn.execute("SELECT status FROM appointments WHERE id=?", (appointment_id,)).fetchone()
        event_count = conn.execute("SELECT COUNT(*) AS n FROM appointment_events WHERE appointment_id=?", (appointment_id,)).fetchone()["n"]
    assert appointment["status"] == "cancelled"
    assert event_count == 3
    assert any(slot["start_utc"] == slots[0]["start_utc"] for slot in slotzero.get_available_slots(doctor_id, target_day, "Asia/Kolkata"))

    # Two independent authenticated sessions race for the same fresh slot.
    race_slot = slots[2]
    race_payload_asha = {"csrf_token": csrf_token, "doctor_id": doctor_id, "slot_start": race_slot["start_utc"], "idempotency_key": "race-asha"}
    race_payload_sam = {"csrf_token": sam_user["csrf_token"], "doctor_id": doctor_id, "slot_start": race_slot["start_utc"], "idempotency_key": "race-sam"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        race_results = list(pool.map(lambda args: args[0].post("/appointments/book", data=args[1], follow_redirects=False), [(client, race_payload_asha), (sam, race_payload_sam)]))
    assert all(result.status_code == 303 for result in race_results)
    with slotzero.db_connect() as conn:
        race_count = conn.execute("SELECT COUNT(*) AS n FROM appointments WHERE doctor_id=? AND start_utc=? AND status='confirmed'", (doctor_id, race_slot["start_utc"])).fetchone()["n"]
    assert race_count == 1

    # Patient can see their own dashboard, and a doctor can see their own.
    assert client.get("/patient/dashboard").status_code == 200
    assert doctor_client.get("/doctor/dashboard").status_code == 200
    doctor_client.close()
    sam.close()
    client.close()
