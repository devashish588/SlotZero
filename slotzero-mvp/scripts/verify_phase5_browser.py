"""Optional installed-Playwright QA; starts loopback Uvicorn with a disposable DB.

Run from slotzero-mvp: py scripts/verify_phase5_browser.py
Evidence is retained in a new OS temporary directory; no app DB is touched.
"""
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).resolve().parents[1]


def main():
    evidence = Path(tempfile.mkdtemp(prefix="slotzero-phase5-browser-"))
    db = evidence / "qa.db"
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "SLOTZERO_DB_PATH": str(db), "SLOTZERO_COOKIE_SECURE": "false"}
    day = (datetime.now(timezone.utc) + timedelta(days=4)).date()
    date = day.isoformat()
    findings, errors, checks = [], [], []

    def accept_dialog(dialog):
        dialog.accept()

    def sql(query, args=()):
        with sqlite3.connect(db) as conn:
            return conn.execute(query, args).fetchall()

    def goto(page, path):
        response = page.goto(base + path)
        page.wait_for_load_state("networkidle")
        assert response.status == 200, (path, response.status)

    def notice(page, message):
        expect(page.locator(".notice")).to_contain_text(message)

    def submit(page, selector):
        page.locator(selector).click()
        page.wait_for_load_state("networkidle")

    def responsive(page, name):
        for width in (1440, 1280, 768, 375):
            page.set_viewport_size({"width": width, "height": 900})
            page.screenshot(path=str(evidence / f"{name}-{width}.png"), full_page=True)
            overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
            clipped = page.locator("input:not([type=hidden]),select,textarea,button,a.button").evaluate_all(
                "els => els.filter(e => {const r=e.getBoundingClientRect();return r.width && (r.left < -1 || r.right > innerWidth+1)}).map(e=>e.outerHTML.slice(0,140))")
            if overflow or clipped:
                findings.append({"page": name, "width": width, "overflow": overflow, "clipped": clipped})
            if page.locator('.topbar').count():
                expect(page.get_by_role('button', name='Sign out')).to_be_visible()
            for timestamp in page.locator('.appointment-main small').all():
                assert timestamp.evaluate('e => e.scrollWidth <= e.clientWidth'), timestamp.inner_text()
        page.set_viewport_size({"width": 1440, "height": 900})

    with (evidence / "server.log").open("w") as log:
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env, stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    with urlopen(base + "/health", timeout=1) as response:
                        assert response.status == 200
                    break
                except OSError:
                    assert server.poll() is None, "Uvicorn failed; inspect server.log"
                    time.sleep(.1)
            else:
                raise AssertionError("Server startup timeout")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                print("Chromium", browser.version, "Evidence", evidence, flush=True)
                contexts = {}
                pages = {}
                for name, zone in (("meera", "Europe/London"), ("alex", "America/New_York"), ("asha", "Asia/Kolkata"), ("sam", "America/New_York")):
                    context = browser.new_context(viewport={"width": 1440, "height": 900}, timezone_id=zone)
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("dialog", accept_dialog)
                    goto(page, "/")
                    if name == "meera":
                        pending = page.evaluate("""() => {
                            const form = document.querySelector('form');
                            const button = form.querySelector('button');
                            const submit = () => form.dispatchEvent(new SubmitEvent('submit', {bubbles:true, cancelable:true, submitter:button}));
                            const first = submit();
                            const busy = form.getAttribute('aria-busy');
                            const indicator = getComputedStyle(button, '::after').content;
                            const repeated = submit();
                            window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted:true}));
                            return {first, busy, indicator, repeated, restored: !form.hasAttribute('aria-busy') && !button.hasAttribute('aria-disabled')};
                        }""")
                        assert pending == {'first': True, 'busy': 'true', 'indicator': '" …"', 'repeated': False, 'restored': True}, pending
                        checks.append('busy indicator CSS, repeat-submit suppression and pageshow recovery')
                        responsive(page, "login")
                    page.locator('[name=email]').fill(f"{name}@slotzero.demo")
                    page.locator('[name=password]').fill(f"{name.title()}@123")
                    submit(page, 'button[type=submit]')
                    expect(page.locator(".timezone-chip")).to_contain_text(zone)
                    assert page.url.endswith("/doctor/dashboard" if name in ("meera", "alex") else "/patient/dashboard")
                    contexts[name], pages[name] = context, page
                checks.append("four real logins, role redirects and IANA zone labels")
                meera, alex, asha, sam = (pages[n] for n in ("meera", "alex", "asha", "sam"))
                expect(asha.locator("body")).to_contain_text("Schedule not configured")
                for doctor in (meera, alex):
                    doctor.locator('[name=schedule_text]').fill("\n".join(f"{w}: 09:00-12:00,13:00-17:00" for w in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")))
                    doctor.locator('[name=consultation_minutes]').select_option("15")
                    submit(doctor, 'form[action="/doctor/schedule"] button')
                    notice(doctor, "updated")
                    doctor.locator('[name=consultation_minutes]').select_option("30")
                    submit(doctor, 'form[action="/doctor/schedule"] button')
                    notice(doctor, "updated")
                alex_before = sql("SELECT * FROM schedules WHERE doctor_id=2")
                meera.locator('[name=block_date]').fill(date)
                meera.locator('[name=start_time]').fill("11:00")
                meera.locator('[name=end_time]').fill("11:30")
                meera.locator('[name=label]').fill("Synthetic QA break")
                submit(meera, 'form[action="/doctor/blocks"] button')
                notice(meera, "added")
                assert sql("SELECT * FROM schedules WHERE doctor_id=2") == alex_before
                assert not sql("SELECT * FROM blocked_periods WHERE doctor_id=2")
                checks.append("split hours, duration changes, block creation and doctor isolation")
                goto(asha, "/patient/dashboard")
                asha.locator('[name=name]').fill("Meera")
                asha.locator('[name=availability_date]').fill(date)
                submit(asha, '.filter-bar button')
                assert asha.locator(".doctor-card").count() == 1
                specialty = asha.locator(".specialty").inner_text()
                asha.locator('[name=name]').fill("")
                asha.locator('[name=specialization]').fill(specialty)
                submit(asha, '.filter-bar button')
                assert asha.locator(".doctor-card").count() == 1
                asha.locator('[name=name]').fill("NoSuchDoctor")
                submit(asha, '.filter-bar button')
                expect(asha.locator("body")).to_contain_text("No doctors match")
                goto(asha, f"/doctors/1?date={date}")
                goto(sam, f"/doctors/1?date={date}")
                assert asha.locator(".slot-card-form").count() == 13
                first_start = asha.locator('[name=slot_start]').first.input_value()
                booking_data = {name: asha.locator(f'.slot-card-form input[name={name}]').first.input_value() for name in ("csrf_token", "doctor_id", "slot_start", "idempotency_key")}
                responsive(asha, "booking")
                asha.remove_listener("dialog", accept_dialog)
                asha.once("dialog", lambda dialog: dialog.dismiss())
                submit(asha, '.slot-card-form button >> nth=0')
                assert sql("SELECT COUNT(*) FROM appointments") == [(0,)]
                assert asha.locator('form[aria-busy=true]').count() == 0
                asha.on("dialog", accept_dialog)
                busy_seen = []

                def inspect_submission(message):
                    if message.text.startswith('QA_BUSY:'):
                        busy_seen.append(message.text)

                asha.on('console', inspect_submission)
                asha.evaluate("document.addEventListener('submit', e => console.log('QA_BUSY:' + e.target.getAttribute('aria-busy') + ':' + e.submitter.getAttribute('aria-disabled')))")
                # Manipulated patient identity must be ignored in favour of the session.
                asha.locator('.slot-card-form').first.evaluate("e => { const i=document.createElement('input');i.type='hidden';i.name='patient_id';i.value='4';e.append(i); }")
                submit(asha, '.slot-card-form button >> nth=0')
                asha.remove_listener('console', inspect_submission)
                assert busy_seen == ['QA_BUSY:true:true']
                notice(asha, "Appointment confirmed")
                expect(asha.locator(".appointment-row")).to_contain_text("Asia/Kolkata")
                appointment_id = sql("SELECT id FROM appointments WHERE patient_id=3 AND status='confirmed'")[0][0]
                local = datetime.fromisoformat(first_start.replace('Z', '+00:00')).astimezone(ZoneInfo('Asia/Kolkata'))
                expect(asha.locator('.appointment-main')).to_contain_text(local.strftime('%a, %d %b %Y · %I:%M %p'))
                goto(meera, f"/doctor/dashboard?date={date}")
                expect(meera.locator(".doctor-appointment-row")).to_contain_text("Asha Verma")
                expect(meera.locator('.doctor-appointment-row')).to_contain_text('09:00 AM')
                goto(alex, f"/doctor/dashboard?date={date}")
                assert alex.locator(".doctor-appointment-row").count() == 0
                # Sam submits the stale slot that was visible before Asha booked.
                submit(sam, '.slot-card-form button >> nth=0')
                notice(sam, "just become unavailable")
                assert sam.locator(f'input[name=slot_start][value="{first_start}"]').count() == 0
                retry = asha.request.post(base + "/appointments/book", form=booking_data)
                assert "already confirmed" in retry.text()
                assert sql("SELECT COUNT(*) FROM appointments")[0][0] == 1
                checks.append("search, empty results, dynamic slots, book, stale conflict refresh, idempotency, both dashboards")
                responsive(asha, "patient-dashboard")
                responsive(meera, "doctor-dashboard")
                # Conflict messages must be visible and preserve the booking.
                meera.locator('[name=block_date]').fill(date)
                meera.locator('[name=start_time]').fill("09:00")
                meera.locator('[name=end_time]').fill("09:30")
                submit(meera, 'form[action="/doctor/blocks"] button')
                notice(meera, f"overlaps confirmed appointment #{appointment_id}")
                meera.locator('[name=schedule_text]').fill("Mon:")
                submit(meera, 'form[action="/doctor/schedule"] button')
                notice(meera, "Schedule not saved")
                goto(asha, "/patient/dashboard")
                submit(asha, f'form[action="/appointments/{appointment_id}/cancel"] button')
                notice(asha, "Appointment cancelled")
                goto(asha, f"/doctors/1?date={date}")
                assert asha.locator(f'input[value="{first_start}"]').count() == 1
                submit(asha, '.slot-card-form button >> nth=0')
                notice(asha, "Appointment confirmed")
                appointment_id = sql("SELECT id FROM appointments WHERE patient_id=3 AND status='confirmed'")[0][0]
                goto(sam, f"/doctors/1?date={date}")
                occupied = sam.locator('[name=slot_start]').first.input_value()
                submit(sam, '.slot-card-form button >> nth=0')
                notice(sam, "Appointment confirmed")
                goto(asha, f"/appointments/{appointment_id}/reschedule?date={date}")
                current = asha.locator(".current-booking").inner_text()
                if "Asia/Kolkata" not in current:
                    findings.append({"page": "reschedule", "issue": "current booking lacks patient-local time and IANA label", "text": current})
                responsive(asha, "reschedule")
                before = sql("SELECT * FROM appointments WHERE id=?", (appointment_id,))
                events = sql("SELECT * FROM appointment_events")
                csrf = asha.locator('[name=csrf_token]').first.input_value()
                bad = asha.request.post(base + f"/appointments/{appointment_id}/reschedule", form={"csrf_token": csrf, "slot_start": occupied})
                asha.goto(bad.url)
                notice(asha, "original appointment is unchanged")
                assert sql("SELECT * FROM appointments WHERE id=?", (appointment_id,)) == before
                assert sql("SELECT * FROM appointment_events") == events
                replacement = asha.locator('[name=slot_start]').nth(1).input_value()
                submit(asha, '.slot-card-form button >> nth=1')
                notice(asha, "successfully rescheduled")
                assert sql("SELECT start_utc FROM appointments WHERE id=?", (appointment_id,))[0][0] == replacement
                expect(asha.locator("#history")).to_contain_text("Rescheduled")
                expect(asha.locator("#history")).to_contain_text("Cancelled")
                checks.append("cancel releases slot, rebook, failed reschedule rollback, valid reschedule and history")
                # Book Alex as Sam; verify New York doctor and patient see one UTC instant.
                goto(sam, f"/doctors/2?date={date}")
                alex_start = sam.locator('[name=slot_start]').first.input_value()
                submit(sam, '.slot-card-form button >> nth=0')
                notice(sam, "Appointment confirmed")
                goto(alex, f"/doctor/dashboard?date={date}")
                expect(alex.locator(".doctor-appointment-row")).to_contain_text("Sam Taylor")
                assert sql("SELECT start_utc FROM appointments WHERE doctor_id=2")[0][0] == alex_start
                expect(alex.locator('.doctor-appointment-row')).to_contain_text('09:00 AM')
                expect(sam.locator('.appointment-main').filter(has_text='Dr. Alex Morgan')).to_contain_text('09:00 AM')
                checks.append('cancelled confirmation does not submit; visible busy state; forged patient ID ignored; four local-time dashboards')
                # Direct HTTP uses browser cookies and real session CSRF tokens.
                csrf = asha.locator('[name=csrf_token]').first.input_value()
                state = sql("SELECT * FROM appointments"), sql("SELECT * FROM appointment_events"), sql("SELECT * FROM schedules")
                sam_id = sql("SELECT id FROM appointments WHERE patient_id=4 LIMIT 1")[0][0]
                for path in ("/doctor/dashboard",):
                    assert asha.request.get(base + path).status == 403
                assert asha.request.get(base + f"/appointments/{sam_id}/reschedule").status == 404
                assert sam.request.get(base + f"/appointments/{appointment_id}/reschedule").status == 404
                assert asha.request.post(base + "/doctor/schedule", form={"csrf_token": csrf, "schedule_text": "Mon:", "consultation_minutes": "30"}).status == 403
                assert asha.request.post(base + f"/appointments/{appointment_id}/cancel", form={}).status == 422
                assert asha.request.post(base + f"/appointments/{appointment_id}/cancel", form={"csrf_token": "invalid"}).status == 403
                assert asha.request.post(base + f"/appointments/{sam_id}/cancel", form={"csrf_token": csrf, "patient_id": "4"}).status == 404
                assert asha.request.post(base + "/appointments/book", form={"csrf_token": csrf, "doctor_id": "bad", "slot_start": "bad", "idempotency_key": "bad"}).status == 422
                assert alex.request.get(base + "/doctor/dashboard?doctor_id=1").text().find("Asha Verma") == -1
                anonymous = browser.new_context()
                assert anonymous.request.get(base + "/patient/dashboard", max_redirects=0).status == 303
                anonymous.add_cookies([{"name": "slotzero_session", "value": "invalid", "url": base}])
                assert anonymous.request.get(base + "/doctor/dashboard", max_redirects=0).status == 303
                assert (sql("SELECT * FROM appointments"), sql("SELECT * FROM appointment_events"), sql("SELECT * FROM schedules")) == state
                assert asha.request.get(base + "/slotzero.db").status == 404
                assert asha.request.get(base + "/static/../qa.db").status == 404
                checks.append("real HTTP role, ownership, forged identity, CSRF, malformed input, invalid session and DB exposure checks")
                for doctor, transition, start in ((meera, '2027-03-28', '01:30'), (alex, '2027-03-14', '02:30'), (meera, '2027-10-31', '01:30'), (alex, '2027-11-07', '01:30')):
                    goto(doctor, '/doctor/dashboard')
                    doctor.locator('[name=block_date]').fill(transition)
                    doctor.locator('[name=start_time]').fill(start)
                    doctor.locator('[name=end_time]').fill('04:00')
                    submit(doctor, 'form[action="/doctor/blocks"] button')
                    notice(doctor, 'does not exist' if '-03-' in transition else 'ambiguous')
                assert sql('SELECT COUNT(*) FROM blocked_periods') == [(1,)]
                goto(asha, '/doctors/1?date=2020-01-01')
                expect(asha.locator('body')).to_contain_text('No open times')
                assert asha.locator('.slot-card-form').count() == 0
                anonymous.clear_cookies()
                registration = anonymous.new_page()
                goto(registration, '/register')
                responsive(registration, 'registration')
                # The relocated sign-out remains usable at mobile width and revokes the session.
                asha.set_viewport_size({'width': 375, 'height': 900})
                submit(asha, 'form[action="/logout"] button')
                assert '/login' in asha.url
                assert asha.request.get(base + '/patient/dashboard', max_redirects=0).status == 303
                checks.append('four browser DST gap/fold notices, unavailable-date empty state, mobile sign-out and session revocation')
                assert not errors, errors
                browser.close()
            assert sql("PRAGMA integrity_check") == [("ok",)]
            assert sql("PRAGMA foreign_key_check") == []
            assert not sql("SELECT a.id,b.id FROM appointments a JOIN appointments b ON a.id<b.id AND a.doctor_id=b.doctor_id AND a.start_utc<b.end_utc AND a.end_utc>b.start_utc WHERE a.status='confirmed' AND b.status='confirmed'")
            assert not sql("SELECT a.id FROM appointments a JOIN blocked_periods b ON a.doctor_id=b.doctor_id AND a.start_utc<b.end_utc AND a.end_utc>b.start_utc WHERE a.status='confirmed'")
            assert sql("SELECT action,COUNT(*) FROM appointment_events GROUP BY action ORDER BY action") == [("booked", 4), ("cancelled", 1), ("rescheduled", 1)]
            checks.append("SQLite integrity, foreign keys, zero overlaps, six expected successful audit events")
            result = {"checks": checks, "findings": findings, "javascript_errors": errors, "date": date}
            (evidence / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps(result, indent=2), flush=True)
            assert not findings, "UI findings recorded in results.json"
        finally:
            server.terminate()
            server.wait(timeout=15)


if __name__ == "__main__":
    main()
