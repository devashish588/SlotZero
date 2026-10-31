from test_reschedule import booking, snapshot


def test_reschedule_current_booking_uses_patient_local_time(booking):
    owner, _, _, _, appointment_id, _ = booking
    before = snapshot()
    response = owner.get(f"/appointments/{appointment_id}/reschedule")
    current = response.text.split('class="current-booking"', 1)[1].split('</section>', 1)[0]
    assert "Mon, 02 Nov 2026 · 02:30 PM – 03:00 PM · Asia/Kolkata" in current
    assert snapshot() == before
