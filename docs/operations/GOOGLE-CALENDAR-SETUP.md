# Optional Google Calendar connection

This feature is implemented but **not live-connected or verified against a real Google account**. The user chose to add OAuth configuration later. The weekly editor and in-app notifications work without Google.

## What sync does

Each doctor explicitly connects their own Google account. SlotZero creates a separate **SlotZero appointments** calendar and requests only `calendar.app.created`, which permits management of app-created calendars. It does not read the doctor's primary calendar. Confirmed future and ongoing SlotZero appointments export with a generic title, exact UTC start/end and an opaque app marker. No patient names, emails, notes or medical information are exported.

Click **Sync now** after booking, cancellation or rescheduling. Sync updates the same event IDs and removes app-owned future events that are no longer confirmed. It never deletes unrelated/untagged Google events. Google edits are not imported into SlotZero; recurring working hours and all conflict/eligibility rules remain in SlotZero. This is manual one-way export, not automatic or two-way availability sync.

## Configure locally

1. In your own Google Cloud project, enable the **Google Calendar API**. Configure the OAuth consent screen and add the intended doctor Google accounts as test users when using a testing app.
2. Create an OAuth client of type **Web application**. Register the exact authorized redirect URI `http://localhost:8000/doctor/calendar/callback`. Production requires the corresponding HTTPS URI for the real app host.
3. Copy the client's ID and secret into the ignored `slotzero-mvp/.env`, using the keys below. Do not paste credentials into chat or commit them.

   ```dotenv
   SLOTZERO_GOOGLE_CLIENT_ID=your-client-id
   SLOTZERO_GOOGLE_CLIENT_SECRET=your-client-secret
   SLOTZERO_GOOGLE_REDIRECT_URI=http://localhost:8000/doctor/calendar/callback
   SLOTZERO_GOOGLE_TOKEN_KEY=your-generated-fernet-key
   ```

4. Generate the encryption key once in your own terminal: `py -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Put it into `.env`; retain it securely with deployment secrets. Install the project's requirements, which now include `cryptography==50.0.2` for encryption of refresh credentials at rest. Do not replace the key casually: existing connections cannot decrypt after a key change and must reconnect unless you explicitly migrate them.
5. Restart SlotZero. Open and sign in at **http://localhost:8000**, matching the callback's hostname; `localhost` and `127.0.0.1` have different browser cookies. Open **Working hours → Google Calendar → Connect Google Calendar**, then complete Google's consent flow yourself.
6. Click **Sync now**. Check the new calendar and repeat sync after a booking, move or cancellation. Verify the intended Google account, date/time display and cancellation behavior with synthetic appointments before relying on it.

Missing or invalid configuration displays an honest disabled connection state. Credentials are not inferred, created in Google Cloud, or committed by the implementation task. A Google consent/application-verification requirement may still apply before broader use.

## Disconnect and failures

Disconnect removes the locally stored encrypted refresh token and attempts Google's token revocation. Previously exported events/calendar remain in Google for the owner to remove. If revocation cannot be reached, the UI directs the doctor to remove SlotZero's grant in Google Account permissions as well.

A failed sync leaves local bookings unchanged. Some external operations may already have succeeded; the error states this and the deterministic event IDs make retry safe from duplicate creation. The last-success timestamp advances only after a complete sync. External changes during a manual sync can require another sync; it is not a live cross-system transaction. Do not treat Google as a second booking authority.

OAuth state is random, stored as a hash, bound to the doctor's current server session, expires after ten minutes and is consumed once. Refresh credentials are Fernet-encrypted with the separately configured key; access tokens are not persisted. API requests use fixed HTTPS Google hosts, reject redirects and use timeouts. Callback query strings are cleared before application access logging and responses are no-store/no-referrer; configure proxy/platform logs to redact callback query strings too. No application code can guarantee a third-party proxy's log policy.

## Official references

- [Google web-server OAuth](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google Calendar authorization scopes](https://developers.google.com/workspace/calendar/api/auth)
- [Create an app-owned secondary calendar](https://developers.google.com/workspace/calendar/api/v3/reference/calendars/insert)
- [Calendar event resource and IDs](https://developers.google.com/workspace/calendar/api/v3/reference/events)

These informed the implementation; mocked API tests do not substitute for the live consent/sync check in step 6.
