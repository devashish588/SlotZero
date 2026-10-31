"""Capture the existing app with disposable fictional state; assert the filmed workflow."""
import base64
from contextlib import ExitStack
from datetime import date, datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
APP = ROOT.parents[1] / "slotzero-mvp"
PROJECT = ROOT / "composition"
ASSETS = PROJECT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)
SOURCE = ROOT.parent / "composition" / "assets"
for filename in ("gsap.min.js", "music.mp3"):
    shutil.copy2(SOURCE / filename, ASSETS / filename)
shutil.copytree(SOURCE / "fonts", ASSETS / "fonts", dirs_exist_ok=True)
font_css = ""
for family, stem in (("Manrope", "manrope"), ("DM Sans", "dm-sans")):
    encoded = base64.b64encode((ASSETS / "fonts" / f"{stem}.woff2").read_bytes()).decode()
    font_css += f"@font-face{{font-family:'{family}';font-weight:100 900;src:url(data:font/woff2;base64,{encoded})}}"

spec = importlib.util.spec_from_file_location("slotzero_workflow", APP / "app.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
evidence = {"source": "Current SlotZero templates", "data": "Fictional demo accounts in disposable SQLite database", "example_day": "2026-11-02", "production_writes": False, "checks": []}

with tempfile.TemporaryDirectory(prefix="slotzero-narrated-") as scratch, ExitStack() as stack:
    app.DB_PATH = str(Path(scratch) / "fictional.db")
    app.utc_now = lambda: datetime(2026, 11, 1, tzinfo=timezone.utc)
    doctor, asha, sam = [stack.enter_context(TestClient(app.app)) for _ in range(3)]

    def signin(client, person):
        result = client.post("/login", data={"email": person + "@slotzero.demo", "password": person.title() + "@123"}, follow_redirects=False)
        assert result.status_code == 303
        return app.get_current_user(type("Request", (), {"cookies": client.cookies})())

    meera, patient, other = signin(doctor, "meera"), signin(asha, "asha"), signin(sam, "sam")
    doc_id = meera["id"]
    result = doctor.post("/doctor/schedule", data={"csrf_token": meera["csrf_token"], "timezone_name": "Europe/London", "consultation_minutes": 30,
        "schedule_text": "\n".join(f"{day}: 09:00-12:00,13:00-17:00" if index < 5 else f"{day}:" for index, day in enumerate(app.WEEKDAYS))}, follow_redirects=True)
    assert "Working hours, time zone and appointment duration updated" in result.text
    result = doctor.post("/doctor/blocks", data={"csrf_token": meera["csrf_token"], "block_date": "2026-11-02", "start_time": "14:00", "end_time": "15:00", "label": "Personal time"}, follow_redirects=True)
    assert "Unavailable period added" in result.text
    slots = app.get_available_slots(doc_id, date(2026, 11, 2), "Asia/Kolkata")
    assert "2026-11-02T12:00:00Z" not in [x["start_utc"] for x in slots]
    assert "2026-11-02T14:00:00Z" not in [x["start_utc"] for x in slots]
    evidence["checks"].append("Weekly split shifts, 30-minute slots and dated block applied; lunch and blocked times excluded")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1080}, device_scale_factor=1.5)
        page.route("**/*", lambda route: route.abort())

        def show(html):
            html = re.sub(r"<script\b[^>]*>.*?</script>|<link\b[^>]*>", "", html, flags=re.S)
            page.set_content(html)
            page.add_style_tag(content=(APP / "static/styles.css").read_text(encoding="utf-8") + font_css + ".demo-panel{display:none!important}")
            page.evaluate("document.fonts.ready")

        def capture(name, html, selector, css=""):
            show(html)
            if css:
                page.add_style_tag(content=css)
            page.locator(selector).screenshot(path=str(ASSETS / f"{name}.png"))

        capture("signin", asha.get("/login").text if not asha.cookies else TestClient(app.app).get("/login").text, ".auth-card-wrap")
        capture("register", asha.get("/register").text, ".auth-card-wrap")
        setup = doctor.get("/doctor/dashboard?date=2026-11-02").text
        # Wider capture is a responsive rendering of the existing card, not a recreated UI.
        wide = ".settings-grid{grid-template-columns:1fr!important;width:1000px}.settings-card{width:1000px}.settings-card form{display:grid;grid-template-columns:1fr 1fr;gap:16px 30px}.settings-card form p{grid-column:1/-1}.settings-card form label:nth-of-type(2){grid-row:2/5;grid-column:2}.settings-card form .button{align-self:end}"
        capture("schedule", setup, "#schedule", wide)
        capture("blocks", setup, "#blocks", ".settings-grid{grid-template-columns:1fr!important;width:900px}.settings-card{width:900px}")
        discovery = asha.get("/patient/dashboard?availability_date=2026-11-02&name=Meera").text
        capture("discover", discovery, "#doctors", ".doctor-grid{grid-template-columns:1fr}.doctor-card{max-width:none}")
        detail = asha.get(f"/doctors/{doc_id}?date=2026-11-02").text
        capture("slots", detail, ".booking-main-card", ".slot-card-form:nth-child(n+5){display:none}.booking-layout{grid-template-columns:1fr;width:1000px}")

        booked = asha.post("/appointments/book", data={"csrf_token": patient["csrf_token"], "doctor_id": doc_id, "slot_start": "2026-11-02T10:00:00Z", "idempotency_key": "narrated-asha"}, follow_redirects=True)
        assert "Appointment confirmed" in booked.text
        with app.read_db() as conn:
            appt = dict(conn.execute("SELECT * FROM appointments WHERE patient_id=?", (patient["id"],)).fetchone())
        appt_id = appt["id"]
        capture("confirmed", booked.text, ".appointments-section")
        capture("booking-notice", booked.text, ".notice")
        calendar = doctor.get("/doctor/dashboard?date=2026-11-02").text
        assert "Asha Verma" in calendar
        capture("calendar", calendar, "#appointments")
        conflict = sam.post("/appointments/book", data={"csrf_token": other["csrf_token"], "doctor_id": doc_id, "slot_start": "2026-11-02T10:00:00Z", "idempotency_key": "narrated-sam"}, follow_redirects=True)
        assert "just become unavailable" in conflict.text
        with app.read_db() as conn:
            assert conn.execute("SELECT count(*) FROM appointments WHERE status='confirmed'").fetchone()[0] == 1
        capture("conflict", conflict.text, ".notice")
        evidence["checks"].append("Asha confirmed at 10:00 UTC; Sam's later request for the identical slot rejected; exactly one confirmed row")
        block_conflict = doctor.post("/doctor/blocks", data={"csrf_token": meera["csrf_token"], "block_date": "2026-11-02", "start_time": "10:00", "end_time": "11:00", "label": "Conflicting time off"}, follow_redirects=True)
        assert "overlaps confirmed appointment" in block_conflict.text
        evidence["checks"].append("Doctor block overlapping Asha's confirmed booking rejected")

        replacement = asha.get(f"/appointments/{appt_id}/reschedule?date=2026-11-02").text
        capture("reschedule", replacement, ".content-wrap", ".slot-card-form:nth-child(n+3){display:none}.content-wrap{width:1080px;flex:initial}.booking-layout{grid-template-columns:1fr}.reschedule-header h1{font-size:38px}")
        failed = asha.post(f"/appointments/{appt_id}/reschedule", data={"csrf_token": patient["csrf_token"], "slot_start": "2026-11-02T14:00:00Z"}, follow_redirects=True)
        assert "original appointment is unchanged" in failed.text
        with app.read_db() as conn:
            assert conn.execute("SELECT start_utc FROM appointments WHERE id=?", (appt_id,)).fetchone()[0] == "2026-11-02T10:00:00Z"
        moved = asha.post(f"/appointments/{appt_id}/reschedule", data={"csrf_token": patient["csrf_token"], "slot_start": "2026-11-02T11:00:00Z"}, follow_redirects=True)
        assert "successfully rescheduled" in moved.text
        assert "2026-11-02T10:00:00Z" in [x["start_utc"] for x in app.get_available_slots(doc_id, date(2026, 11, 2), "Asia/Kolkata")]
        capture("moved", moved.text, ".appointments-section")
        evidence["checks"].append("Failed move preserved original; successful move to 11:00 UTC released 10:00 UTC")
        zone = asha.post("/patient/timezone", data={"csrf_token": patient["csrf_token"], "timezone_name": "America/New_York"})
        assert zone.status_code == 200
        with app.read_db() as conn:
            assert conn.execute("SELECT start_utc FROM appointments WHERE id=?", (appt_id,)).fetchone()[0] == "2026-11-02T11:00:00Z"
        evidence["checks"].append("Patient display-zone change preserved appointment's UTC instant")
        asha.post("/patient/timezone", data={"csrf_token": patient["csrf_token"], "timezone_name": "Asia/Kolkata"})
        cancelled = asha.post(f"/appointments/{appt_id}/cancel", data={"csrf_token": patient["csrf_token"]}, follow_redirects=True)
        assert "Appointment cancelled. The slot is available again" in cancelled.text
        assert "2026-11-02T11:00:00Z" in [x["start_utc"] for x in app.get_available_slots(doc_id, date(2026, 11, 2), "Asia/Kolkata")]
        capture("cancelled", cancelled.text, ".notice")
        capture("history", cancelled.text, "#history")
        with app.read_db() as conn:
            assert conn.execute("SELECT status FROM appointments WHERE id=?", (appt_id,)).fetchone()[0] == "cancelled"
            actions = [x[0] for x in conn.execute("SELECT action FROM appointment_events ORDER BY id")]
            assert actions == ["booked", "rescheduled", "cancelled"]
        evidence["checks"].append("Eligible cancellation released 11:00 UTC; history contains booked, rescheduled and cancelled events")
        browser.close()

evidence["temporary_database_removed"] = True
(ROOT / "workflow-evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
print(json.dumps(evidence, indent=2))
