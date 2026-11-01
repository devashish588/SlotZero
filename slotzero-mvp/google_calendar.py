"""Optional, doctor-authorized export to an app-owned Google calendar."""
import hashlib
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

from cryptography.fernet import Fernet, InvalidToken

SCOPE = 'https://www.googleapis.com/auth/calendar.app.created'
API = 'https://www.googleapis.com/calendar/v3'
TOKEN_URL = 'https://oauth2.googleapis.com/token'


class CalendarError(Exception):
    def __init__(self, message='Google Calendar is unavailable. Retry or reconnect your account.', status=None):
        super().__init__(message)
        self.status = status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CalendarError('Google redirected an API request. Retry later; credentials were not forwarded.')


def settings():
    values = {name: os.getenv('SLOTZERO_GOOGLE_' + name, '') for name in
              ('CLIENT_ID', 'CLIENT_SECRET', 'REDIRECT_URI', 'TOKEN_KEY')}
    if not all(values.values()):
        raise CalendarError('Google Calendar is not enabled. Ask the clinic operator to configure it.')
    url = urlsplit(values['REDIRECT_URI'])
    if (url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1'))
            or url.path != '/doctor/calendar/callback' or url.query or url.fragment or url.username):
        raise CalendarError('Google Calendar callback configuration is invalid.')
    try:
        Fernet(values['TOKEN_KEY'].encode())
    except (ValueError, TypeError):
        raise CalendarError('Google Calendar encryption configuration is invalid.') from None
    return values


def configured():
    try:
        settings()
        return True
    except CalendarError:
        return False


def encrypt(value):
    return Fernet(settings()['TOKEN_KEY'].encode()).encrypt(value.encode()).decode()


def decrypt(value):
    try:
        return Fernet(settings()['TOKEN_KEY'].encode()).decrypt(value.encode()).decode()
    except InvalidToken:
        raise CalendarError('Calendar credentials cannot be read. Reconnect Google Calendar.') from None


def request_json(method, url, token=None, data=None, form=False, etag=None):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ('www.googleapis.com', 'oauth2.googleapis.com') or parsed.username:
        raise CalendarError('Calendar API address is not allowed.')
    headers = {'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if etag:
        if not isinstance(etag, str) or '\r' in etag or '\n' in etag:
            raise CalendarError()
        headers['If-Match'] = etag
    body = None
    if data is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded' if form else 'application/json'
        body = (urlencode(data) if form else json.dumps(data)).encode()
    try:
        with build_opener(NoRedirect).open(Request(url, data=body, headers=headers, method=method), timeout=15) as response:
            raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise CalendarError('Google returned too much data. Retry the sync.')
            result = json.loads(raw) if raw else {}
            if not isinstance(result, dict):
                raise CalendarError()
            return result
    except HTTPError as exc:
        # Never expose Google's response body, authorization code or tokens.
        status = exc.code
        exc.close()
        raise CalendarError(status=status) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise CalendarError() from None


def tokens(**grant):
    config = settings()
    result = request_json('POST', TOKEN_URL, data={
        'client_id': config['CLIENT_ID'], 'client_secret': config['CLIENT_SECRET'], **grant,
    }, form=True)
    if not isinstance(result.get('access_token'), str) or not result['access_token']:
        raise CalendarError('Google did not grant calendar access. Reconnect and allow calendar access.')
    if not isinstance(result.get('scope', ''), str) or not isinstance(result.get('refresh_token', ''), str):
        raise CalendarError()
    return result


def sync(token, calendar_id, namespace, appointments, now):
    """Export future/ongoing bookings; never touch untagged Google events."""
    root = API + '/calendars/' + quote(calendar_id, safe='') + '/events'
    remote = {}
    page = None
    seen_pages = set()
    while True:
        query = {'privateExtendedProperty': 'slotzero=' + namespace, 'timeMin': now,
                 'maxResults': 2500, 'showDeleted': 'false'}
        if page:
            query['pageToken'] = page
        result = request_json('GET', root + '?' + urlencode(query), token)
        events = result.get('items', [])
        if not isinstance(events, list):
            raise CalendarError()
        for event in events:
            if not isinstance(event, dict):
                raise CalendarError()
            properties = event.get('extendedProperties', {})
            private = properties.get('private', {}) if isinstance(properties, dict) else {}
            if isinstance(private, dict) and private.get('slotzero') == namespace:
                if not isinstance(event.get('id'), str) or not re.fullmatch(r'[a-v0-9]{5,1024}', event['id']):
                    raise CalendarError()
                remote[event['id']] = event
        page = result.get('nextPageToken')
        if not page:
            break
        if not isinstance(page, str) or page in seen_pages or len(seen_pages) >= 100:
            raise CalendarError('Google pagination did not finish. No sync was applied.')
        seen_pages.add(page)
    desired = {}
    for appointment in appointments:
        event_id = hashlib.sha256(f'{namespace}:{appointment["id"]}'.encode()).hexdigest()
        desired[event_id] = {
            'summary': 'SlotZero appointment',
            'status': 'confirmed',
            'start': {'dateTime': appointment['start_utc'], 'timeZone': 'UTC'},
            'end': {'dateTime': appointment['end_utc'], 'timeZone': 'UTC'},
            'extendedProperties': {'private': {'slotzero': namespace}},
        }
    changed = 0
    for event_id, payload in desired.items():
        event = remote.get(event_id)
        if event:
            request_json('PATCH', root + '/' + event_id, token, payload, etag=event.get('etag'))
        else:
            try:
                request_json('POST', root, token, {'id': event_id, **payload})
            except CalendarError as exc:
                if exc.status != 409:
                    raise
                existing = request_json('GET', root + '/' + event_id, token)
                properties = existing.get('extendedProperties', {})
                private = properties.get('private', {}) if isinstance(properties, dict) else {}
                if not isinstance(private, dict) or private.get('slotzero') != namespace:
                    raise CalendarError('A Google event conflict needs attention. No foreign event was changed.')
                request_json('PATCH', root + '/' + event_id, token, payload, etag=existing.get('etag'))
        changed += 1
    for event_id, event in remote.items():
        if event_id not in desired:
            try:
                request_json('DELETE', root + '/' + quote(event_id, safe=''), token, etag=event.get('etag'))
            except CalendarError as exc:
                if exc.status not in (404, 410):
                    raise
            changed += 1
    return changed
