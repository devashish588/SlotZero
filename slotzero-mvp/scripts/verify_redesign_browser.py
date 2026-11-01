"""Optional Playwright UI regressions; uses a disposable SQLite DB and loopback server.

Run from slotzero-mvp: py scripts/verify_redesign_browser.py
Screenshots and results remain in .design-qa/redesign/<unique run>/ at the repo root.
The existing phase-5 browser script covers the deeper booking/security lifecycle.
"""
import json
import os
import re
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
AUDIT = """() => {
  const issues = [];
  const visible = e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
  const identify = e => e.id || e.name || e.textContent.trim().slice(0, 70) || e.tagName;
  for (const e of document.querySelectorAll('input:not([type=hidden]),select,textarea')) {
    if (visible(e) && (!e.labels?.length || !Array.from(e.labels).some(l => l.textContent.trim())))
      issues.push('Missing visible label: ' + identify(e));
  }
  if (document.documentElement.scrollWidth > innerWidth + 1) issues.push('Document overflow');
  for (const e of document.querySelectorAll('input:not([type=hidden]),select,textarea,button,a.button')) {
    if (!visible(e)) continue;
    const r = e.getBoundingClientRect();
    if (r.left < -1 || r.right > innerWidth + 1) issues.push('Clipped control: ' + identify(e));
    if (r.height < 43.5 || r.width < 43.5) issues.push('Small control: ' + identify(e));
  }
  const rgb = color => (color.match(/[\\d.]+/g) || []).map(Number);
  const luminance = color => rgb(color).slice(0,3).map(c => {
    c /= 255; return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4;
  }).reduce((sum, c, i) => sum + c * [.2126,.7152,.0722][i], 0);
  const background = e => {
    while (e) {
      const c = getComputedStyle(e).backgroundColor, channels = rgb(c);
      if (channels.length === 3 || channels[3] === 1) return c;
      e = e.parentElement;
    }
    return 'rgb(255,255,255)';
  };
  for (const e of document.querySelectorAll('.muted,.nav-item,.notice,.notice span,.button,input[placeholder]')) {
    if (!visible(e)) continue;
    const s = getComputedStyle(e), pseudo = e.matches('input[placeholder]') ? getComputedStyle(e,'::placeholder') : s;
    const a = luminance(pseudo.color), b = luminance(background(e));
    const ratio = (Math.max(a,b) + .05) / (Math.min(a,b) + .05);
    const large = parseFloat(s.fontSize) >= 24 || (parseFloat(s.fontSize) >= 18.66 && +s.fontWeight >= 700);
    if (ratio < (large ? 3 : 4.5)) issues.push('Low contrast ' + ratio.toFixed(2) + ': ' + identify(e));
  }
  return issues;
}"""


def main():
    evidence_root = ROOT.parent / '.design-qa' / 'redesign'
    evidence_root.mkdir(parents=True, exist_ok=True)
    evidence = Path(tempfile.mkdtemp(prefix='run-', dir=evidence_root))
    db = evidence / 'qa.db'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    env = {**os.environ, 'SLOTZERO_DB_PATH': str(db), 'SLOTZERO_COOKIE_SECURE': 'false'}
    date = (datetime.now(timezone.utc) + timedelta(days=4)).date().isoformat()
    findings, errors, external, checks = [], [], [], []

    def goto(page, path):
        response = page.goto(base + path)
        assert response.status == 200, (path, response.status)
        page.evaluate('document.fonts.ready')

    def submit(page, selector):
        page.locator(selector).click()
        page.wait_for_load_state('networkidle')

    def login(page, name):
        goto(page, '/login')
        page.locator('[name=email]').fill(f'{name}@slotzero.demo')
        page.locator('[name=password]').fill(f'{name.title()}@123')
        submit(page, 'form[action="/login"] button[type=submit]')

    def capture(page, name):
        page.evaluate('document.fonts.ready')
        assert page.evaluate('document.fonts.check(\'16px "Lexend"\') && document.fonts.check(\'16px "Source Sans 3"\')')
        for width in (1440, 1280, 1920, 768, 375):
            page.set_viewport_size({'width': width, 'height': 900})
            issues = page.evaluate(AUDIT)
            if issues:
                findings.append({'page': name, 'width': width, 'issues': issues})
            if width in (1440, 768, 375):
                page.screenshot(path=str(evidence / f'{name}-{width}.png'), full_page=True, animations='disabled')
        page.set_viewport_size({'width': 1440, 'height': 900})
        html = re.sub(r'href="[^"]*/static/styles.css"', 'href="../../../slotzero-mvp/static/styles.css"', page.content())
        (evidence / f'{name}.html').write_text(html, encoding='utf-8')
        page.set_viewport_size({'width': 844, 'height': 390})
        issues = page.evaluate(AUDIT)
        if issues:
            findings.append({'page': name, 'width': 844, 'height': 390, 'issues': issues})
        page.set_viewport_size({'width': 1440, 'height': 900})

    with (evidence / 'server.log').open('w') as log:
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', str(port)], cwd=ROOT, env=env, stdout=log, stderr=log)
        try:
            for _ in range(100):
                try:
                    with urlopen(base + '/health', timeout=1) as response:
                        assert response.status == 200
                    break
                except OSError:
                    assert server.poll() is None, 'Server exited; inspect server.log'
                    time.sleep(.1)
            else:
                raise AssertionError('Server startup timeout')
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(viewport={'width': 1440, 'height': 900})
                context.on('request', lambda request: external.append(request.url) if not request.url.startswith(base + '/') else None)
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('dialog', lambda dialog: dialog.accept())
                goto(page, '/login')
                page.locator('.skip-link').focus()
                page.keyboard.press('Enter')
                expect(page.locator('#main-content')).to_be_focused()
                page.locator('[data-copy-email="asha@slotzero.demo"]').click()
                expect(page.locator('[name=email]')).to_have_value('asha@slotzero.demo')
                expect(page.locator('[name=password]')).to_have_value('Asha@123')
                capture(page, 'login')
                page.locator('[name=password]').fill('wrong-password')
                submit(page, 'form[action="/login"] button[type=submit]')
                expect(page.locator('.notice[role=alert]')).to_be_focused()
                capture(page, 'login-error')
                goto(page, '/register')
                capture(page, 'register')
                page.locator('[name=full_name]').fill('Redesign Test Patient')
                page.locator('[name=email]').fill('redesign@example.test')
                page.locator('[name=password]').fill('Synthetic-only-123')
                page.locator('[name=timezone_name]').select_option('Asia/Kolkata')
                submit(page, 'form[action="/register"] button[type=submit]')
                expect(page.locator('.notice')).to_contain_text('Account created')
                checks.append('skip link, demo autofill, login error focus, registration submission and local fonts')
                login(page, 'asha')
                capture(page, 'patient-empty')
                page.set_viewport_size({'width': 375, 'height': 900})
                menu, nav = page.locator('.menu-toggle'), page.locator('#workspace-nav')
                expect(nav).to_be_hidden()
                menu.click()
                expect(menu).to_have_attribute('aria-expanded', 'true')
                nav.locator('a').first.focus()
                page.keyboard.press('Escape')
                expect(menu).to_be_focused()
                expect(nav).to_be_hidden()
                menu.click()
                page.keyboard.press('Escape')
                expect(nav).to_be_hidden()
                menu.click()
                nav.get_by_role('link', name='My appointments').click()
                expect(nav).to_be_hidden()
                expect(page.locator('#main-content')).to_be_focused()
                page.set_viewport_size({'width': 1440, 'height': 900})
                expect(nav).to_be_visible()
                expect(menu).to_be_hidden()
                trigger, options = page.locator('#timezone-trigger'), page.locator('.timezone-option')
                trigger.focus()
                page.keyboard.press('ArrowDown')
                expect(page.locator('#timezone-dropdown')).to_be_visible()
                page.keyboard.press('Home')
                expect(options.first).to_be_focused()
                page.keyboard.press('ArrowDown')
                expect(options.nth(1)).to_be_focused()
                page.keyboard.press('ArrowUp')
                expect(options.first).to_be_focused()
                page.keyboard.press('End')
                expect(options.last).to_be_focused()
                page.keyboard.press('Escape')
                expect(trigger).to_be_focused()
                trigger.click()
                page.keyboard.press('Enter')
                expect(trigger).to_be_focused()
                expect(page.locator('#timezone-dropdown')).to_be_hidden()
                page.keyboard.press('ArrowDown')
                page.keyboard.press('Tab')
                expect(page.locator('#timezone-dropdown')).to_be_hidden()
                assert page.evaluate('document.activeElement.tagName') != 'BODY'
                page.route('**/patient/timezone', lambda route: route.abort('failed'))
                trigger.click()
                options.filter(has_text='Europe/London').click()
                expect(page.locator('#timezone-message[role=status]')).to_contain_text('Failed to update')
                expect(trigger).to_be_enabled()
                page.unroute('**/patient/timezone')
                for zone in ('America/New_York', 'Asia/Kolkata'):
                    page.locator('#timezone-trigger').click()
                    page.locator(f'.timezone-option[data-zone="{zone}"]').click()
                    expect(page.locator('.timezone-chip')).to_have_text(zone)
                page.emulate_media(reduced_motion='reduce')
                assert page.locator('.spinner').evaluate('e => getComputedStyle(e).animationName') == 'none'
                page.emulate_media(reduced_motion='no-preference')
                page.locator('[name=specialization]').fill('No Such Specialty')
                submit(page, '.filter-bar button')
                expect(page.locator('body')).to_contain_text('No doctors match')
                capture(page, 'patient-filter-empty')
                checks.append('responsive menu, keyboard listbox, recoverable timezone network failure, reduced motion and empty filtering')
                doctor = browser.new_page(viewport={'width': 1440, 'height': 900})
                doctor.on('pageerror', lambda error: errors.append(str(error)))
                login(doctor, 'meera')
                doctor.locator('a[href="/doctor/dashboard#schedule"]').click()
                expect(doctor.locator('a[href="/doctor/dashboard#schedule"]')).to_have_class('nav-item active')
                expect(doctor.locator('#schedule')).to_be_visible()
                expect(doctor.locator('#blocks')).to_be_hidden()
                doctor.locator('a[href="/doctor/dashboard#blocks"]').click()
                expect(doctor.locator('a[href="/doctor/dashboard#blocks"]')).to_have_class('nav-item active')
                expect(doctor.locator('#blocks')).to_be_visible()
                expect(doctor.locator('#schedule')).to_be_hidden()
                doctor.go_back()
                expect(doctor.locator('a[href="/doctor/dashboard#schedule"]')).to_have_class('nav-item active')
                expect(doctor.locator('#schedule')).to_be_visible()
                doctor.get_by_role('button', name='Add Monday hours', exact=True).click()
                monday = doctor.locator('.weekly-day').first
                monday.get_by_label('Monday start time', exact=True).fill('09:00')
                monday.get_by_label('Monday end time', exact=True).fill('08:00')
                assert not monday.get_by_label('Monday end time', exact=True).evaluate('e => e.checkValidity()')
                monday.get_by_label('Monday end time', exact=True).fill('12:00')
                doctor.get_by_role('button', name='Add Monday hours', exact=True).click()
                monday.get_by_label('Monday start time', exact=True).nth(1).fill('13:00')
                monday.get_by_label('Monday end time', exact=True).nth(1).fill('17:00')
                doctor.locator('#schedule-text-toggle').click()
                assert 'Mon: 09:00-12:00,13:00-17:00' in doctor.locator('[name=schedule_text]').input_value()
                doctor.locator('[name=schedule_text]').fill('\n'.join(f'{day}: 09:00-12:00,13:00-17:00' for day in ('Mon','Tue','Wed','Thu','Fri','Sat','Sun')))
                submit(doctor, 'form[action="/doctor/schedule"] button[type=submit]')
                expect(doctor.locator('.notice')).to_contain_text('updated')
                doctor.locator('[name=label]').fill('Synthetic test break')
                doctor.locator('[name=block_date]').fill(date)
                doctor.locator('[name=start_time]').fill('11:00')
                doctor.locator('[name=end_time]').fill('11:30')
                submit(doctor, 'form[action="/doctor/blocks"] button')
                capture(doctor, 'doctor-settings')
                goto(page, f'/doctors/1?date={date}')
                expect(page.locator('.slot-card-form').first).to_be_visible()
                capture(page, 'doctor-slots')
                submit(page, '.slot-card-form button >> nth=0')
                expect(page.locator('.notice')).to_contain_text('Appointment confirmed')
                capture(page, 'patient-booked')
                with sqlite3.connect(db) as conn:
                    appointment = conn.execute("SELECT id FROM appointments WHERE patient_id=3 AND status='confirmed'").fetchone()[0]
                goto(page, f'/appointments/{appointment}/reschedule?date={date}')
                expect(page.locator('.current-booking')).to_contain_text('Asia/Kolkata')
                capture(page, 'reschedule')
                page.locator('#notification-bell').click()
                expect(page.locator('#notification-items')).to_contain_text('appointment booked')
                capture(page, 'patient-notifications-open')
                page.keyboard.press('Escape')
                goto(doctor, f'/doctor/dashboard?date={date}')
                expect(doctor.locator('.doctor-appointment-row')).to_contain_text('Asha Verma')
                capture(doctor, 'doctor-agenda')
                doctor.locator('#notification-bell').click()
                expect(doctor.locator('#notification-items')).to_contain_text('Asha Verma')
                expect(doctor.locator('#notification-items a').first).to_have_attribute('href', f'/doctor/dashboard?date={date}#appointments')
                expect(doctor.locator('#notification-count')).to_have_text('1')
                expect(doctor.locator('#update-toast')).to_contain_text('appointment booked')
                capture(doctor, 'notifications-open')
                goto(page, '/patient/dashboard')
                submit(page, f'form[action="/appointments/{appointment}/cancel"] button')
                doctor.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
                expect(doctor.locator('#notification-items')).to_contain_text('appointment cancelled')
                expect(doctor.locator('#notification-panel')).to_be_visible()
                expect(doctor.locator('#update-toast')).to_be_hidden()
                capture(doctor, 'notifications-incoming-open')
                doctor.locator('#notifications-read').click()
                expect(doctor.locator('#notification-count')).to_be_hidden()
                page.keyboard.press('Escape')
                doctor.keyboard.press('Escape')
                expect(doctor.locator('#notification-panel')).to_be_hidden()
                expect(doctor.locator('#notification-bell')).to_be_focused()
                capture(doctor, 'notifications')
                doctor.locator('#notification-bell').click()
                doctor.locator('#notifications-refresh').click()
                expect(doctor.locator('.doctor-appointment-row')).to_have_count(0)
                checks.append('workspace hash/back selection, weekly split-shift serialization/validation and doctor update bell/toast/read state')
                checks.append('schedule and block forms, live dual-zone slots, booking, current-booking reschedule and doctor agenda')
                assert not external, external
                assert not errors, errors
                assert not findings, 'UI findings recorded in results.json'
                browser.close()
        finally:
            server.terminate()
            server.wait(timeout=15)
            result = {'checks': checks, 'findings': findings, 'javascript_errors': errors, 'external_requests': external, 'evidence': str(evidence)}
            (evidence / 'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
