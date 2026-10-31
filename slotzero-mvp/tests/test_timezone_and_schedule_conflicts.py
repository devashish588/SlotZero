from urllib.parse import unquote_plus

from fastapi.testclient import TestClient

import app as slotzero
from test_reschedule import booking


def login(client, email, password):
    response = client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return slotzero.get_current_user(type("Request", (), {"cookies": client.cookies})())


def test_patient_timezone_persists_and_only_changes_displayed_instant(booking):
    patient_client, _, patient, _, appointment_id, slots = booking
    original_start = slots[0]["start_utc"]
    original_end = slots[0]["end_utc"]

    changed = patient_client.post(
        "/patient/timezone",
        data={"csrf_token": patient["csrf_token"], "timezone_name": "Europe/London"},
        follow_redirects=False,
    )
    assert changed.status_code == 303
    assert "notice_type=success" in changed.headers["location"]

    with slotzero.read_db() as conn:
        user_row = conn.execute("SELECT timezone FROM users WHERE id=?", (patient["id"],)).fetchone()
        appointment = conn.execute(
            "SELECT start_utc, end_utc FROM appointments WHERE id=?", (appointment_id,)
        ).fetchone()
    assert user_row["timezone"] == "Europe/London"
    assert appointment["start_utc"] == original_start
    assert appointment["end_utc"] == original_end

    dashboard = patient_client.get("/patient/dashboard")
    assert dashboard.status_code == 200
    assert "Europe/London" in dashboard.text
    assert "Mon, 02 Nov 2026" in dashboard.text
    assert "09:00 AM" in dashboard.text

    patient_client.post("/logout", data={"csrf_token": patient["csrf_token"]}, follow_redirects=False)
    logged_in = login(patient_client, "asha@slotzero.demo", "Asha@123")
    assert logged_in["timezone"] == "Europe/London"
    assert "Europe/London" in patient_client.get("/patient/dashboard").text


def test_timezone_rejects_invalid_and_unauthorized_updates(booking):
    patient_client, other_client, patient, stranger, _, _ = booking
    before = patient["timezone"]

    invalid = patient_client.post(
        "/patient/timezone",
        data={"csrf_token": patient["csrf_token"], "timezone_name": "UTC"},
        follow_redirects=False,
    )
    assert invalid.status_code == 303
    assert "notice_type=error" in invalid.headers["location"]
    assert unquote_plus(invalid.headers["location"]).find("supported time zones") >= 0

    doctor_client = TestClient(slotzero.app)
    try:
        doctor = login(doctor_client, "meera@slotzero.demo", "Meera@123")
        forbidden = doctor_client.post(
            "/patient/timezone",
            data={"csrf_token": doctor["csrf_token"], "timezone_name": "America/New_York"},
            follow_redirects=False,
        )
        assert forbidden.status_code == 403
    finally:
        doctor_client.close()

    # The endpoint has no user-id input; another patient can only update their
    # own authenticated profile.
    other_response = other_client.post(
        "/patient/timezone",
        data={"csrf_token": stranger["csrf_token"], "timezone_name": "Europe/London"},
        follow_redirects=False,
    )
    assert other_response.status_code == 303
    with slotzero.read_db() as conn:
        patient_zone = conn.execute("SELECT timezone FROM users WHERE id=?", (patient["id"],)).fetchone()["timezone"]
        stranger_zone = conn.execute("SELECT timezone FROM users WHERE id=?", (stranger["id"],)).fetchone()["timezone"]
    assert patient_zone == before
    assert stranger_zone == "Europe/London"


def test_schedule_conflict_identifies_appointment_and_succeeds_after_resolution(booking):
    patient_client, other_client, patient, stranger, appointment_id, _ = booking
    doctor_client = TestClient(slotzero.app)
    doctor = login(doctor_client, "meera@slotzero.demo", "Meera@123")
    empty_schedule = "\n".join(["Mon:", "Tue:", "Wed:", "Thu:", "Fri:", "Sat:", "Sun:"])

    blocked = doctor_client.post(
        "/doctor/schedule",
        data={
            "csrf_token": doctor["csrf_token"],
            "schedule_text": empty_schedule,
            "consultation_minutes": 30,
        },
        follow_redirects=False,
    )
    assert blocked.status_code == 303
    location = blocked.headers["location"]
    message = unquote_plus(location)
    assert f"appointment #{appointment_id}" in message
    assert "Asha Verma" in message
    assert "Mon, 02 Nov 2026" in message
    assert "09:00 AM - 09:30 AM" in message or "09:00 AM" in message
    assert "Europe/London" in message
    assert "date=2026-11-02" in location
    assert location.endswith("#appointments")
    assert "existing cancellation or rescheduling workflow" in message

    cancelled = patient_client.post(
        f"/appointments/{appointment_id}/cancel",
        data={"csrf_token": patient["csrf_token"]},
        follow_redirects=False,
    )
    assert cancelled.status_code == 303
    with slotzero.read_db() as conn:
        other_appointment_id = conn.execute(
            "SELECT id FROM appointments WHERE patient_id=? AND status='confirmed'",
            (stranger["id"],),
        ).fetchone()["id"]
    other_cancelled = other_client.post(
        f"/appointments/{other_appointment_id}/cancel",
        data={"csrf_token": stranger["csrf_token"]},
        follow_redirects=False,
    )
    assert other_cancelled.status_code == 303

    saved = doctor_client.post(
        "/doctor/schedule",
        data={
            "csrf_token": doctor["csrf_token"],
            "schedule_text": empty_schedule,
            "consultation_minutes": 30,
        },
        follow_redirects=False,
    )
    assert saved.status_code == 303
    assert "notice_type=success" in saved.headers["location"]
    with slotzero.read_db() as conn:
        schedule_rows = conn.execute(
            "SELECT intervals_json FROM schedules WHERE doctor_id=?",
            (doctor["id"],),
        ).fetchall()
        appointment_status = conn.execute(
            "SELECT status FROM appointments WHERE id=?", (appointment_id,)
        ).fetchone()["status"]
    assert all(row["intervals_json"] == "[]" for row in schedule_rows)
    assert appointment_status == "cancelled"
