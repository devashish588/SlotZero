import hashlib
import json
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
import app as slotzero
import google_calendar as gcal
from test_phase2 import accounts
from test_reschedule import booking, snapshot


@pytest.fixture
def calendar_config(monkeypatch):
    for key, value in {'CLIENT_ID': 'test-client', 'CLIENT_SECRET': 'test-secret',
                       'REDIRECT_URI': 'http://localhost:8000/doctor/calendar/callback',
                       'TOKEN_KEY': Fernet.generate_key().decode()}.items():
        monkeypatch.setenv('SLOTZERO_GOOGLE_' + key, value)


def test_notification_isolation(accounts):
    asha = accounts['asha'][0].get('/notifications')
    meera = accounts['meera'][0].get('/notifications')
    assert {item['actor_name'] for item in asha.json()['items']} == {'Asha Verma'}
    assert len(meera.json()['items']) == 2
    assert all(item['href'] == '/doctor/dashboard?date=2026-11-02#appointments' for item in meera.json()['items'])
    assert asha.json()['items'][0]['href'] == '/patient/dashboard#appointments'
    assert {item['actor_name'] for item in meera.json()['items']} == {'Asha Verma', 'Sam Taylor'}
    assert accounts['alex'][0].get('/notifications').json()['items'] == []
    assert accounts['alex'][0].get('/notifications?doctor_id=1&patient_id=3').json()['items'] == []
    assert {item['actor_name'] for item in accounts['sam'][0].get('/notifications').json()['items']} == {'Sam Taylor'}
    assert set(item['id'] for item in asha.json()['items']).isdisjoint(
        item['id'] for item in accounts['sam'][0].get('/notifications').json()['items'])
    assert 'no-store' in meera.headers['cache-control']
    assert accounts['anonymous'][0].get('/notifications', follow_redirects=False).status_code == 303
    assert 'refresh_cipher' not in meera.text and 'patient_email' not in meera.text


@pytest.mark.parametrize('action', ['connect', 'sync', 'disconnect'])
def test_calendar_role_and_csrf(accounts, action):
    url = '/doctor/calendar/' + action
    for name in ('asha', 'sam'):
        client, user = accounts[name]
        assert client.post(url, data={'csrf_token': user['csrf_token']}).status_code == 403
    assert accounts['meera'][0].post(url, data={'csrf_token': 'invalid'}).status_code == 403
    assert accounts['anonymous'][0].post(url, data={'csrf_token': 'invalid'}, follow_redirects=False).status_code == 303


def start_calendar(accounts):
    client, user = accounts['meera']
    response = client.post('/doctor/calendar/connect', data={'csrf_token': user['csrf_token']}, follow_redirects=False)
    assert response.status_code == 303
    query = parse_qs(urlsplit(response.headers['location']).query)
    assert query['scope'] == [gcal.SCOPE] and query['access_type'] == ['offline']
    return query['state'][0]


def test_calendar_state_session_expiry_and_replay(accounts, calendar_config, monkeypatch):
    state = start_calendar(accounts)
    with slotzero.read_db() as conn:
        row = conn.execute('SELECT * FROM google_calendar_states').fetchone()
        assert row['state_hash'] == hashlib.sha256(state.encode()).hexdigest()
        assert state not in json.dumps(dict(row))
    callback = '/doctor/calendar/callback?state=' + state + '&error=access_denied'
    assert accounts['alex'][0].get(callback).status_code == 403
    assert accounts['meera'][0].get(callback, follow_redirects=False).status_code == 303
    assert accounts['meera'][0].get(callback).status_code == 403
    state = start_calendar(accounts)
    with slotzero.transaction() as conn:
        conn.execute("UPDATE google_calendar_states SET expires_at='2000-01-01T00:00:00Z'")
    assert accounts['meera'][0].get('/doctor/calendar/callback?state=' + state).status_code == 403


def test_calendar_callback_encrypts_credentials(accounts, calendar_config, monkeypatch):
    state = start_calendar(accounts)
    monkeypatch.setattr(gcal, 'tokens', lambda **kw: {'access_token': 'access-secret', 'refresh_token': 'refresh-secret', 'scope': gcal.SCOPE})
    monkeypatch.setattr(gcal, 'request_json', lambda *args, **kw: {'id': 'owned-calendar'})
    response = accounts['meera'][0].get('/doctor/calendar/callback?state=' + state + '&code=one-use-code', follow_redirects=False)
    assert response.status_code == 303 and response.headers['cache-control'] == 'no-store'
    assert response.headers['referrer-policy'] == 'no-referrer'
    with slotzero.read_db() as conn:
        row = conn.execute('SELECT * FROM google_calendar_connections').fetchone()
        assert row['calendar_id'] == 'owned-calendar'
        assert 'refresh-secret' not in row['refresh_cipher']
        assert gcal.decrypt(row['refresh_cipher']) == 'refresh-secret'
    page = accounts['meera'][0].get('/doctor/dashboard')
    assert 'refresh-secret' not in page.text and 'access-secret' not in page.text
    assert 'Sync now' in page.text


def test_missing_permission_never_creates_calendar(accounts, calendar_config, monkeypatch):
    state = start_calendar(accounts)
    monkeypatch.setattr(gcal, 'tokens', lambda **kw: {'access_token': 'token', 'refresh_token': 'refresh', 'scope': ''})
    monkeypatch.setattr(gcal, 'request_json', lambda *args, **kw: pytest.fail('Must not call Google without consented scope'))
    response = accounts['meera'][0].get('/doctor/calendar/callback?state=' + state + '&code=code', follow_redirects=False)
    assert response.status_code == 303 and 'error' in response.headers['location']
    with slotzero.read_db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM google_calendar_connections').fetchone()[0] == 0


def test_export_sync_updates_cancels_and_isolates(monkeypatch):
    remote = {'unrelated': {'id': 'unrelated', 'summary': 'Personal event'}}
    def fake(method, url, token=None, data=None, **kwargs):
        if method == 'GET':
            return {'items': list(remote.values())}
        if method == 'POST':
            assert data['id'] not in remote
            remote[data['id']] = dict(data)
        elif method == 'PATCH':
            remote[url.rsplit('/', 1)[1]].update(data)
        elif method == 'DELETE':
            del remote[url.rsplit('/', 1)[1]]
        return {}
    monkeypatch.setattr(gcal, 'request_json', fake)
    appointments = [{'id': 7, 'start_utc': '2026-11-02T09:00:00Z', 'end_utc': '2026-11-02T09:30:00Z', 'patient_name': 'Never exported'}]
    gcal.sync('token', 'owned', 'namespace', appointments, '2026-11-01T00:00:00Z')
    gcal.sync('token', 'owned', 'namespace', appointments, '2026-11-01T00:00:00Z')
    assert len(remote) == 2 and 'Never exported' not in json.dumps(remote)
    appointments[0]['start_utc'] = '2026-11-02T10:00:00Z'
    appointments[0]['end_utc'] = '2026-11-02T10:30:00Z'
    gcal.sync('token', 'owned', 'namespace', appointments, '2026-11-01T00:00:00Z')
    assert len(remote) == 2 and any(e.get('start', {}).get('dateTime') == appointments[0]['start_utc'] for e in remote.values())
    gcal.sync('token', 'owned', 'namespace', [], '2026-11-01T00:00:00Z')
    assert list(remote) == ['unrelated']


def test_failed_sync_preserves_local_data(accounts, calendar_config, monkeypatch):
    client, user = accounts['meera']
    with slotzero.transaction() as conn:
        conn.execute('INSERT INTO google_calendar_connections VALUES(?,?,?,?,NULL)', (user['id'], gcal.encrypt('refresh'), 'calendar', 'namespace'))
    before = snapshot()
    def fail(**kw):
        raise gcal.CalendarError()
    monkeypatch.setattr(gcal, 'tokens', fail)
    response = client.post('/doctor/calendar/sync', data={'csrf_token': user['csrf_token']}, follow_redirects=False)
    assert 'error' in response.headers['location'] and snapshot() == before
    with slotzero.read_db() as conn:
        assert conn.execute('SELECT last_synced FROM google_calendar_connections').fetchone()[0] is None


def test_configuration_disabled_without_credentials(monkeypatch):
    for name in ('CLIENT_ID', 'CLIENT_SECRET', 'REDIRECT_URI', 'TOKEN_KEY'):
        monkeypatch.delenv('SLOTZERO_GOOGLE_' + name, raising=False)
    assert not gcal.configured()
    with pytest.raises(gcal.CalendarError):
        gcal.settings()


@pytest.mark.parametrize('url', ['http://www.googleapis.com/calendar/v3', 'https://example.test/steal', 'https://oauth2.googleapis.com@evil.test/token'])
def test_calendar_credentials_never_sent_to_unapproved_hosts(url):
    with pytest.raises(gcal.CalendarError):
        gcal.request_json('POST', url, 'must-not-leave', {'token': 'secret'})


def test_calendar_rejects_malformed_provider_data_before_mutation(monkeypatch):
    calls = []
    def fake(method, *args, **kwargs):
        calls.append(method)
        return {'items': [{'id': '../foreign', 'extendedProperties': {'private': {'slotzero': 'namespace'}}}]}
    monkeypatch.setattr(gcal, 'request_json', fake)
    with pytest.raises(gcal.CalendarError):
        gcal.sync('token', 'owned', 'namespace', [], '2026-11-01T00:00:00Z')
    assert calls == ['GET']


def test_calendar_state_cannot_move_between_same_doctor_sessions(accounts, calendar_config):
    state = start_calendar(accounts)
    with TestClient(slotzero.app) as second:
        second.post('/login', data={'email': 'meera@slotzero.demo', 'password': 'Meera@123'})
        assert second.get('/doctor/calendar/callback?state=' + state + '&error=access_denied').status_code == 403
    assert accounts['meera'][0].get('/doctor/calendar/callback?state=' + state + '&error=access_denied', follow_redirects=False).status_code == 303


def test_disconnect_removes_credentials_even_when_google_is_unreachable(accounts, calendar_config, monkeypatch):
    client, user = accounts['meera']
    with slotzero.transaction() as conn:
        conn.execute('INSERT INTO google_calendar_connections VALUES(?,?,?,?,NULL)', (user['id'], gcal.encrypt('refresh'), 'calendar', 'namespace'))
    def fail(*args, **kwargs):
        raise gcal.CalendarError()
    monkeypatch.setattr(gcal, 'request_json', fail)
    response = client.post('/doctor/calendar/disconnect', data={'csrf_token': user['csrf_token']}, follow_redirects=False)
    assert response.status_code == 303 and 'permissions' in response.headers['location']
    with slotzero.read_db() as conn:
        assert conn.execute('SELECT COUNT(*) FROM google_calendar_connections').fetchone()[0] == 0
