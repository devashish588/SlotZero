from datetime import datetime, timezone
from urllib.parse import unquote_plus

import pytest
from fastapi.testclient import TestClient

import app as slotzero


@pytest.fixture
def booking(tmp_path, monkeypatch):
    monkeypatch.setattr(slotzero, "DB_PATH", str(tmp_path / "reschedule.db"))
    monkeypatch.setattr(slotzero, "utc_now", lambda: datetime(2026, 11, 1, tzinfo=timezone.utc))
    with TestClient(slotzero.app) as owner, TestClient(slotzero.app) as other:
        def login(client, email, password):
            assert client.post("/login", data={"email": email, "password": password}, follow_redirects=False).status_code == 303
            return slotzero.get_current_user(type("Request", (), {"cookies": client.cookies})())

        patient = login(owner, "asha@slotzero.demo", "Asha@123")
        stranger = login(other, "sam@slotzero.demo", "Sam@123")
        with slotzero.transaction(immediate=True) as conn:
            doctor = conn.execute("SELECT user_id FROM doctors JOIN users ON users.id=doctors.user_id WHERE email='meera@slotzero.demo'").fetchone()[0]
            conn.execute("INSERT INTO schedules(doctor_id,weekday,intervals_json) VALUES(?,0,?)", (doctor, '[["09:00","12:00"]]'))

        slots = slotzero.get_available_slots(doctor, slotzero.parse_date("2026-11-02"), patient["timezone"])
        for client, user, slot, key in [(owner, patient, slots[0], "owner"), (other, stranger, slots[1], "other")]:
            response = client.post("/appointments/book", data={"csrf_token": user["csrf_token"], "doctor_id": doctor, "slot_start": slot["start_utc"], "idempotency_key": key}, follow_redirects=False)
            assert response.status_code == 303
        with slotzero.read_db() as conn:
            appointment_id = conn.execute("SELECT id FROM appointments WHERE patient_id=?", (patient["id"],)).fetchone()[0]
        yield owner, other, patient, stranger, appointment_id, slots


def snapshot():
    with slotzero.read_db() as conn:
        return {table: [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY id")] for table in ("appointments", "appointment_events")}


def test_reschedule_page_renders_doctor_timezone_and_replacement_slots(booking):
    owner, _, _, _, appointment_id, slots = booking
    before = snapshot()
    response = owner.get(f"/appointments/{appointment_id}/reschedule")
    assert response.status_code == 200
    assert response.context["appointment"]["id"] == appointment_id
    assert response.context["appointment"]["doctor_timezone"] == "Europe/London"
    assert 'value="2026-11-02"' in response.text
    assert "Europe/London" in response.text
    assert f'value="{slots[2]["start_utc"]}"' in response.text
    assert f'value="{slots[1]["start_utc"]}"' not in response.text
    assert f'action="/appointments/{appointment_id}/reschedule"' in response.text
    assert snapshot() == before


@pytest.mark.parametrize("replacement, message", [(1, "no longer available"), ("invalid", "Invalid appointment time")])
def test_failed_reschedule_preserves_all_bookings_and_history(booking, replacement, message):
    owner, _, patient, _, appointment_id, slots = booking
    before = snapshot()
    response = owner.post(f"/appointments/{appointment_id}/reschedule", data={"csrf_token": patient["csrf_token"], "slot_start": slots[replacement]["start_utc"] if isinstance(replacement, int) else replacement}, follow_redirects=False)
    assert response.status_code == 303
    assert message in unquote_plus(response.headers["location"])
    assert snapshot() == before
    assert message in owner.get(response.headers["location"]).text


def test_reschedule_rejects_other_patient_and_invalid_date(booking):
    owner, other, _, stranger, appointment_id, slots = booking
    before = snapshot()
    url = f"/appointments/{appointment_id}/reschedule"
    assert other.get(url).status_code == 404
    assert other.post(url, data={"csrf_token": stranger["csrf_token"], "slot_start": slots[2]["start_utc"]}).status_code == 404
    invalid = owner.get(url + "?date=2026-02-31", follow_redirects=False)
    assert invalid.status_code == 303
    assert "valid calendar date" in unquote_plus(invalid.headers["location"])
    assert owner.get("/appointments/999999/reschedule").status_code == 404
    assert snapshot() == before
