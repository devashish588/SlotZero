from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import threading
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

import app as slotzero
from test_reschedule import booking, snapshot
from test_phase2 import accounts, block_data, schedule_data
from test_phase3 import book, notice


def change(client, user, appointment_id, action, **data):
    return client.post(f"/appointments/{appointment_id}/{action}",
                       data={"csrf_token": user["csrf_token"], **data}, follow_redirects=False)


@pytest.mark.parametrize("remaining,allowed", [(7201, True), (7200, True), (7199, False), (7199.5, False)])
def test_cancel_exact_cutoff_history_and_release(booking, monkeypatch, remaining, allowed):
    client, _, user, _, appointment_id, slots = booking
    start = slotzero.db_to_dt(slots[0]["start_utc"])
    now = start - timedelta(seconds=remaining)
    monkeypatch.setattr(slotzero, "utc_now", lambda: now)
    before = snapshot()
    result = notice(change(client, user, appointment_id, "cancel", now="1900-01-01"))
    after = snapshot()
    if not allowed:
        assert "2 hours" in result and after == before
        return
    assert "Appointment cancelled" in result
    old, new = before["appointments"][0], after["appointments"][0]
    assert new == {**old, "status": "cancelled", "updated_at": slotzero.dt_to_db(now)}
    event = after["appointment_events"][-1]
    assert event["action"] == "cancelled" and event["actor_id"] == user["id"]
    assert event["created_at"] == slotzero.dt_to_db(now)
    assert json.loads(event["details"]) == {"old_start_utc": old["start_utc"], "old_end_utc": old["end_utc"]}
    assert after["appointment_events"][:-1] == before["appointment_events"]
    available = slotzero.get_available_slots(old["doctor_id"], start.date(), user["timezone"])
    assert slots[0]["start_utc"] in [s["start_utc"] for s in available]
    assert "already cancelled" in notice(change(client, user, appointment_id, "cancel"))
    assert snapshot() == after
    assert "Cancelled" in client.get("/patient/dashboard").text


@pytest.mark.parametrize("case", ["occupied", "blocked", "invalid", "naive", "fraction", "outside", "past", "cancelled"])
def test_failed_reschedule_preserves_entire_state(booking, accounts, case):
    client, _, user, _, appointment_id, slots = booking
    target = slots[2]["start_utc"]
    if case == "blocked":
        doctor, doctor_user = accounts["meera"]
        assert "added" in notice(doctor.post("/doctor/blocks", data=block_data(doctor_user, start_time="10:00", end_time="10:30"), follow_redirects=False))
    elif case == "cancelled":
        change(client, user, appointment_id, "cancel")
    else:
        target = {"occupied": slots[1]["start_utc"], "invalid": "invalid", "naive": "2026-11-02T10:00:00",
                  "fraction": "2026-11-02T10:00:00.5Z", "outside": "2026-11-02T20:00:00Z",
                  "past": "2026-10-30T10:00:00Z"}[case]
    before = snapshot()
    assert "notice_type=error" in notice(change(client, user, appointment_id, "reschedule", slot_start=target))
    assert snapshot() == before


def test_successful_reschedule_audit_and_duplicate(booking):
    client, _, user, _, appointment_id, slots = booking
    before = snapshot()
    assert "successfully" in notice(change(client, user, appointment_id, "reschedule", slot_start=slots[2]["start_utc"]))
    after = snapshot()
    event = after["appointment_events"][-1]
    assert len(after["appointments"]) == len(before["appointments"])
    assert event["actor_id"] == user["id"] and event["created_at"] == slotzero.dt_to_db(slotzero.utc_now())
    assert event["old_start_utc"] == slots[0]["start_utc"] and event["new_start_utc"] == slots[2]["start_utc"]
    assert json.loads(event["details"]) == {"old_start_utc": slots[0]["start_utc"], "old_end_utc": slots[0]["end_utc"],
                                          "new_start_utc": slots[2]["start_utc"], "new_end_utc": slots[2]["end_utc"]}
    assert "already at that time" in notice(change(client, user, appointment_id, "reschedule", slot_start=slots[2]["start_utc"]))
    assert snapshot() == after


@pytest.mark.parametrize("action", ["cancel", "reschedule"])
def test_lifecycle_ownership_role_and_csrf(booking, accounts, action):
    client, other, user, stranger, appointment_id, slots = booking
    before = snapshot()
    assert change(other, stranger, appointment_id, action, slot_start=slots[2]["start_utc"]).status_code == 404
    doctor, doctor_user = accounts["meera"]
    assert change(doctor, doctor_user, appointment_id, action, slot_start=slots[2]["start_utc"]).status_code == 403
    assert client.post(f"/appointments/{appointment_id}/{action}", data={"csrf_token": "forged", "slot_start": slots[2]["start_utc"]}).status_code == 403
    assert snapshot() == before


@pytest.mark.parametrize("remaining,allowed", [(7200, True), (7199, False)])
def test_existing_documented_reschedule_cutoff(booking, monkeypatch, remaining, allowed):
    client, _, user, _, appointment_id, slots = booking
    monkeypatch.setattr(slotzero, "utc_now", lambda: slotzero.db_to_dt(slots[0]["start_utc"]) - timedelta(seconds=remaining))
    before = snapshot()
    response = notice(change(client, user, appointment_id, "reschedule", slot_start=slots[2]["start_utc"]))
    assert ("successfully" in response) == allowed
    if not allowed:
        assert snapshot() == before
        assert "2 hours" in notice(client.get(f"/appointments/{appointment_id}/reschedule", follow_redirects=False))


@pytest.mark.parametrize("action", ["cancel", "reschedule", "block", "delete_block", "schedule"])
def test_real_writer_timeout_is_controlled(booking, accounts, monkeypatch, action):
    client, _, user, _, appointment_id, slots = booking
    doctor, doctor_user = accounts["meera"]
    original_connect = slotzero.db_connect
    before = snapshot()
    with slotzero.transaction(immediate=True):
        def short_timeout():
            conn = original_connect()
            conn.execute("PRAGMA busy_timeout=50")
            return conn
        monkeypatch.setattr(slotzero, "db_connect", short_timeout)
        if action == "block":
            response = doctor.post("/doctor/blocks", data=block_data(doctor_user), follow_redirects=False)
        elif action == "delete_block":
            response = doctor.post("/doctor/blocks/999/delete", data={"csrf_token": doctor_user["csrf_token"]}, follow_redirects=False)
        elif action == "schedule":
            response = doctor.post("/doctor/schedule", data=schedule_data(doctor_user), follow_redirects=False)
        else:
            response = change(client, user, appointment_id, action, slot_start=slots[2]["start_utc"])
        assert "notice_type=error" in notice(response)
    assert snapshot() == before


@pytest.mark.parametrize("action", ["cancel", "reschedule"])
def test_audit_failure_rolls_back_lifecycle(booking, action):
    client, _, user, _, appointment_id, slots = booking
    before = snapshot()
    with slotzero.transaction() as conn:
        conn.execute("CREATE TRIGGER fail_event BEFORE INSERT ON appointment_events BEGIN SELECT RAISE(ABORT,'forced audit failure'); END")
    with pytest.raises(sqlite3.IntegrityError, match="forced audit failure"):
        change(client, user, appointment_id, action, slot_start=slots[2]["start_utc"])
    assert snapshot() == before


@pytest.mark.parametrize("race", ["cancel_cancel", "cancel_book", "move_book", "move_move", "duplicate_move", "book_block", "book_schedule"])
def test_lifecycle_race_independent_connections(booking, accounts, monkeypatch, race):
    _, _, _, _, appointment_id, slots = booking
    doctor_id = accounts["meera"][1]["id"]
    with slotzero.read_db() as conn:
        other_id = conn.execute("SELECT id FROM appointments WHERE patient_id=?", (accounts["sam"][1]["id"],)).fetchone()[0]
    before = snapshot()
    target = slots[2]["start_utc"]
    def operation(name, action, appt=appointment_id, start=target):
        client, user = accounts[name]
        return (client.cookies.get("slotzero_session"), f"/appointments/{appt}/{action}",
                {"csrf_token": user["csrf_token"], "slot_start": start})
    def booking_op(start):
        cookie, _, data = operation("sam", "book", start=start)
        return cookie, "/appointments/book", {**data, "doctor_id": doctor_id, "idempotency_key": "race"}
    if race == "cancel_cancel":
        operations = [operation("asha", "cancel")] * 2
    elif race == "cancel_book":
        operations = [operation("asha", "cancel"), booking_op(slots[0]["start_utc"])]
    elif race == "move_book":
        operations = [operation("asha", "reschedule"), booking_op(target)]
    elif race == "move_move":
        operations = [operation("asha", "reschedule"), operation("sam", "reschedule", appt=other_id)]
    elif race == "duplicate_move":
        operations = [operation("asha", "reschedule")] * 2
    else:
        doctor, user = accounts["meera"]
        path, data = ("/doctor/blocks", block_data(user, start_time="10:00", end_time="10:30")) if race == "book_block" else (
            "/doctor/schedule", schedule_data(user, schedule_text="Mon: 09:00-10:00"))
        operations = [booking_op(target), (doctor.cookies.get("slotzero_session"), path, data)]
    barrier = threading.Barrier(2)
    original_connect = slotzero.db_connect
    connections = []
    reached = []
    def connect():
        conn = original_connect()
        connections.append(conn)
        def trace(sql):
            if sql == "BEGIN IMMEDIATE":
                barrier.wait(timeout=10)
                reached.append(threading.get_ident())
        conn.set_trace_callback(trace)
        return conn
    monkeypatch.setattr(slotzero, "db_connect", connect)
    # No lifespan in workers: the parent has initialized the shared file already.
    def send(op):
        cookie, path, data = op
        client = TestClient(slotzero.app)
        try:
            client.cookies.set("slotzero_session", cookie)
            return notice(client.post(path, data=data, follow_redirects=False))
        finally:
            client.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        messages = list(pool.map(send, operations))
    monkeypatch.setattr(slotzero, "db_connect", original_connect)
    assert len(set(reached)) == 2 and len({id(c) for c in connections}) >= 2
    after = snapshot()
    new_events = after["appointment_events"][len(before["appointment_events"]):]
    if race in ("cancel_cancel", "duplicate_move"):
        assert len(new_events) == 1
        assert sum("already" in m for m in messages) == 1
    elif race == "cancel_book":
        assert after["appointments"][0]["status"] == "cancelled"
        assert sum(e["action"] == "cancelled" for e in new_events) == 1
        assert len(new_events) in (1, 2)
    elif race in ("move_book", "move_move"):
        assert len(new_events) == 1
        assert sum("notice_type=error" in m for m in messages) == 1
        for old, new in zip(before["appointments"], after["appointments"]):
            if not any(e["appointment_id"] == old["id"] for e in new_events):
                assert old == new
    else:
        assert sum("notice_type=error" in m for m in messages) == 1
    with slotzero.read_db() as conn:
        assert conn.execute("SELECT a.id FROM appointments a JOIN appointments b ON a.id<b.id AND a.doctor_id=b.doctor_id "
                            "WHERE a.status='confirmed' AND b.status='confirmed' AND a.start_utc<b.end_utc AND a.end_utc>b.start_utc").fetchall() == []
        assert conn.execute("SELECT a.id FROM appointments a JOIN blocked_periods b ON a.doctor_id=b.doctor_id "
                            "WHERE a.status='confirmed' AND a.start_utc<b.end_utc AND a.end_utc>b.start_utc").fetchall() == []
        for appt in conn.execute("SELECT * FROM appointments WHERE status='confirmed'"):
            doctor = slotzero.doctor_record(conn, appt["doctor_id"])
            schedule = {r["weekday"]: json.loads(r["intervals_json"]) for r in conn.execute("SELECT * FROM schedules WHERE doctor_id=?", (appt["doctor_id"],))}
            assert slotzero.doctor_schedule_contains(doctor["timezone"], schedule, appt["start_utc"], appt["end_utc"])
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


@pytest.mark.parametrize("zone,wall,message", [
    ("Europe/London", "2026-03-29T01:30", "does not exist"),
    ("Europe/London", "2026-10-25T01:30", "ambiguous"),
    ("America/New_York", "2026-03-08T02:30", "does not exist"),
    ("America/New_York", "2026-11-01T01:30", "ambiguous"),
    ("Europe/London", "2027-03-28T01:30", "does not exist"),
    ("Europe/London", "2027-10-31T01:30", "ambiguous"),
    ("America/New_York", "2027-03-14T02:30", "does not exist"),
    ("America/New_York", "2027-11-07T01:30", "ambiguous"),
])
def test_dst_strict_iana_gap_and_fold(zone, wall, message):
    with pytest.raises(ValueError, match=message):
        slotzero.local_to_utc_strict(datetime.fromisoformat(wall), zone)


@pytest.mark.parametrize("zone,winter,summer", [
    ("Europe/London", "2027-01-04T09:00:00Z", "2027-07-05T08:00:00Z"),
    ("America/New_York", "2027-01-04T14:00:00Z", "2027-07-05T13:00:00Z"),
    ("Asia/Kolkata", "2027-01-04T03:30:00Z", "2027-07-05T03:30:00Z"),
])
def test_ordinary_seasonal_iana_conversion(zone, winter, summer):
    for day, expected in (("2027-01-04", winter), ("2027-07-05", summer)):
        actual = slotzero.local_to_utc_strict(datetime.fromisoformat(day + "T09:00"), zone)
        assert slotzero.dt_to_db(actual) == expected


@pytest.mark.parametrize("name,day,start,end,invalid_start,message", [
    ("meera", "2027-03-28", "01:00", "02:00", "2027-03-28T01:00:00Z", "does not exist"),
    ("meera", "2027-10-31", "01:00", "02:00", "2027-10-31T01:00:00Z", "ambiguous"),
    ("alex", "2027-03-14", "02:00", "03:00", "2027-03-14T07:00:00Z", "does not exist"),
    ("alex", "2027-11-07", "01:00", "02:00", "2027-11-07T06:00:00Z", "ambiguous"),
])
def test_dst_workflows_reject_invalid_wall_times(accounts, name, day, start, end, invalid_start, message):
    doctor, doctor_user = accounts[name]
    patient, user = accounts["asha"]
    hours = f"Mon: 09:00-12:00\nSun: {start}-{end}"
    assert "updated" in notice(doctor.post("/doctor/schedule", data=schedule_data(doctor_user, schedule_text=hours), follow_redirects=False))
    slots = slotzero.get_available_slots(doctor_user["id"], slotzero.parse_date(day), user["timezone"])
    assert slots == []
    before = snapshot()
    response = doctor.post("/doctor/blocks", data=block_data(doctor_user, block_date=day, start_time=start, end_time=end), follow_redirects=False)
    assert message in notice(response)
    assert "unavailable" in notice(book(patient, user, doctor_user["id"], start=invalid_start))
    assert snapshot() == before
    with slotzero.read_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM blocked_periods").fetchone()[0] == 0


@pytest.mark.parametrize("name,day,expected,patient_clock", [
    ("meera", "2026-11-02", "2026-11-02T10:00:00Z", "03:30 PM"),
    ("alex", "2026-11-02", "2026-11-02T15:00:00Z", "08:30 PM"),
    ("meera", "2027-07-05", "2027-07-05T09:00:00Z", "02:30 PM"),
    ("alex", "2027-07-05", "2027-07-05T14:00:00Z", "07:30 PM"),
])
def test_synthetic_accounts_same_utc_instant(accounts, name, day, expected, patient_clock):
    doctor, doctor_user = accounts[name]
    patient, user = accounts["asha"]
    assert user["timezone"] == "Asia/Kolkata"
    assert accounts["sam"][1]["timezone"] == "America/New_York"
    assert "updated" in notice(doctor.post("/doctor/schedule", data=schedule_data(doctor_user, schedule_text="Mon: 09:00-12:00"), follow_redirects=False))
    available = patient.get(f"/doctors/{doctor_user['id']}?date={day}")
    chosen = next(s for s in available.context["slots"] if s["start_utc"] == expected)
    assert patient_clock in chosen["patient_time"] and "10:00 AM" in chosen["doctor_time"]
    assert "confirmed" in notice(book(patient, user, doctor_user["id"], start=chosen["start_utc"]))
    patient_view = patient.get("/patient/dashboard")
    doctor_view = doctor.get(f"/doctor/dashboard?date={day}")
    p = next(a for a in patient_view.context["upcoming"] if a["start_utc"] == expected)
    d = next(a for a in doctor_view.context["appointments"] if a["id"] == p["id"])
    assert p["start_utc"] == d["start_utc"] == expected
    assert p["end_utc"] == d["end_utc"] == slotzero.dt_to_db(slotzero.db_to_dt(expected) + timedelta(minutes=30))
    assert patient_clock in p["start_display"] and "10:00 AM" in d["start_display"]
    assert user["timezone"] in patient_view.text and doctor_user["timezone"] in doctor_view.text
    with slotzero.read_db() as conn:
        row = conn.execute("SELECT * FROM appointments WHERE id=?", (p["id"],)).fetchone()
        assert row["start_utc"] == expected and row["end_utc"] == p["end_utc"]


@pytest.mark.parametrize("zone,day,hours,expected_count,doctor_day", [
    ("America/New_York", "2026-11-03", "Mon: 23:00-23:30", 1, "2026-11-02"),
    ("America/New_York", "2026-11-02", "Mon: 23:00-23:30", 0, None),
    ("Europe/London", "2026-11-03", "Mon: 23:00-23:30", 1, "2026-11-02"),
    ("Asia/Kolkata", "2026-11-02", "Mon: 00:00-00:30", 1, "2026-11-02"),
    ("America/New_York", "2027-03-14", "Sun: 00:00-04:00", 5, "2027-03-14"),
    ("Europe/London", "2027-10-31", "Sun: 00:00-04:00", 5, "2027-10-31"),
])
def test_patient_local_calendar_filter_and_doctor_date_link(accounts, zone, day, hours, expected_count, doctor_day):
    doctor, doctor_user = accounts["alex"]
    patient, user = accounts["asha"]
    assert "updated" in notice(doctor.post("/doctor/schedule", data=schedule_data(doctor_user, timezone_name=zone, schedule_text=hours), follow_redirects=False))
    response = patient.get(f"/patient/dashboard?name=Alex&availability_date={day}")
    doctors = response.context["doctors"]
    if not expected_count:
        assert doctors == []
        return
    assert len(doctors) == 1 and doctors[0]["available_count"] == expected_count
    assert doctors[0]["slot_date"] == doctor_day
    assert f"/doctors/{doctor_user['id']}?date={doctor_day}" in response.text
    page = patient.get(f"/doctors/{doctor_user['id']}?date={doctor_day}")
    matching = [s for s in page.context["slots"] if slotzero.db_to_dt(s["start_utc"]).astimezone(ZoneInfo(user["timezone"])).date().isoformat() == day]
    assert len(matching) == expected_count
    assert all(s["patient_time"] in page.text for s in matching)
    assert "Asia/Kolkata" in response.text


def test_doctor_dashboard_calendar_midnight(accounts):
    doctor, doctor_user = accounts["alex"]
    patient, user = accounts["asha"]
    doctor.post("/doctor/schedule", data=schedule_data(doctor_user, schedule_text="Mon: 23:00-23:30"))
    slots = slotzero.get_available_slots(doctor_user["id"], slotzero.parse_date("2026-11-02"), user["timezone"])
    assert slots[0]["start_utc"] == "2026-11-03T04:00:00Z"
    assert "confirmed" in notice(book(patient, user, doctor_user["id"], start=slots[0]["start_utc"]))
    assert len(doctor.get("/doctor/dashboard?date=2026-11-02").context["appointments"]) == 1
    assert doctor.get("/doctor/dashboard?date=2026-11-03").context["appointments"] == []


@pytest.mark.parametrize("zone,day,start,end", [
    ("America/New_York", "2027-03-14", "2027-03-14T05:00:00Z", "2027-03-15T04:00:00Z"),
    ("America/New_York", "2027-11-07", "2027-11-07T04:00:00Z", "2027-11-08T05:00:00Z"),
    ("Europe/London", "2027-03-28", "2027-03-28T00:00:00Z", "2027-03-28T23:00:00Z"),
    ("Europe/London", "2027-10-31", "2027-10-30T23:00:00Z", "2027-11-01T00:00:00Z"),
])
def test_patient_dst_calendar_bounds(accounts, zone, day, start, end):
    doctor, doctor_user = accounts["alex"]
    patient, user = accounts["sam"]
    with slotzero.transaction() as conn:
        conn.execute("UPDATE users SET timezone=? WHERE id=?", (zone, user["id"]))
    hours = "\n".join(f"{weekday}: 00:00-23:30" for weekday in slotzero.WEEKDAYS)
    doctor.post("/doctor/schedule", data=schedule_data(doctor_user, timezone_name="Asia/Kolkata", schedule_text=hours))
    lower, upper = slotzero.db_to_dt(start), slotzero.db_to_dt(end)
    expected = []
    doctor_day = lower.astimezone(ZoneInfo("Asia/Kolkata")).date()
    while doctor_day <= upper.astimezone(ZoneInfo("Asia/Kolkata")).date():
        expected.extend(s for s in slotzero.get_available_slots(doctor_user["id"], doctor_day, zone)
                        if lower <= slotzero.db_to_dt(s["start_utc"]) < upper)
        doctor_day += timedelta(days=1)
    response = patient.get(f"/patient/dashboard?name=Alex&availability_date={day}")
    assert response.context["doctors"][0]["available_count"] == len(expected)
    assert len(expected) > 40
    assert all(slotzero.db_to_dt(s["start_utc"]).astimezone(ZoneInfo(zone)).date().isoformat() == day for s in expected)
