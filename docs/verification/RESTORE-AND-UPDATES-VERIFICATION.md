# Restoration and targeted updates — 2026-11-01

## User authority and result

The user rejected the green redesign and requested the previous navy/card version with larger visible fonts, correct workspace highlighting, easier weekly scheduling, a separate notification bell/pop-ups for both roles, optional Google Calendar sync and a website review. The user selected Google sync and subsequently said Google OAuth is not configured yet: include setup instructions. The scope/architecture extension is explicit, not inferred from the original hackathon requirements.

Restored all seven original templates and the original stylesheet from commit `2df0d49`, then applied the requested changes. This is a new forward change, not a history rewrite. The rejected green CSS/base token files were removed; its historical reports remain marked superseded. No user video, presentation or unrelated untracked artifact was changed.

## Implemented

- Previous navy sidebar, white cards, page compositions, original content and application wiring restored. Local Lexend headings/Source Sans 3 body remain as the requested font change; task text/body/input sizes are increased, and explicit font-size declarations have a 13px minimum. Placeholder/notice/slot contrast defects discovered in restored CSS were corrected without changing its visual identity.
- Workspace active selection follows the pathname/hash, including Working hours, Blocked time, patient appointments and browser back/forward. `aria-current` matches the selected link. All destinations remain available through the mobile menu.
- Doctor weekly editor shows named days, native start/end pickers, add/remove split ranges and closed days. It serializes the original `schedule_text` form contract; the text fallback remains for manual/no-script use. End-before-start is checked in the editor; all ranges, overlap, DST and confirmed-booking protections remain server-validated. No hours are pre-seeded.
- Separate top-bar SVG bell with the latest 30 role-scoped appointment events, unread count, mark-read and timestamps in the selected user zone. A patient sees only their own appointment events; a doctor sees only their schedule's events. Query parameters cannot change that scope. JSON is authenticated/no-store; no tokens or other patients' records are sent.
- Dismissible in-app pop-ups acknowledge local changes and new appointment events. Updates poll every 15 seconds while the document is visible and refresh on return to the tab. Panels and toasts are mutually exclusive while reading updates. Escape restores focus. A Refresh appointments action reloads the current date/hash when server-rendered agenda content is stale. Read state is browser-local and no email/SMS/OS-push delivery is claimed.
- Optional doctor-only Google OAuth with least-privilege app-created-calendar scope, ten-minute one-use session-bound hashed state, encrypted refresh credentials, fixed HTTPS API hosts, redirect rejection and generic error handling. Manual Sync now exports confirmed future/ongoing appointments to a separate calendar with generic titles and opaque deterministic IDs. Repeated sync updates events, reflects moves/cancellations and leaves foreign/untagged events alone. No patient identity is exported; local appointments are never changed by a Google API failure. Partial external failure is disclosed and retry is duplicate-safe. Disconnect clears stored credentials and attempts revocation.

Google is **not live-connected or live-verified**. The UI is honestly disabled until operator configuration exists. Weekly availability is still managed in SlotZero; no primary-calendar import, automatic export, Google-to-SlotZero availability change or global calendar-conflict guarantee is claimed. The [setup guide](../operations/GOOGLE-CALENDAR-SETUP.md) contains the Google Cloud/OAuth steps and official references.

## Files and dependencies

Restored/changed seven templates, static/styles.css and static/app.js; added static/enhancements.css. Backend changes are confined to the private notification feed, optional calendar routes/context and two additive tables for connections/OAuth states. Added google_calendar.py and tests/test_updates.py. `cryptography==50.0.2` is the sole runtime dependency added, to encrypt refresh credentials; no Google SDK, frontend framework or notification service was introduced. The package was already installed in the execution environment.

Updated existing browser scripts to open the text fallback and distinguish submit buttons from the new editor controls; no original security/lifecycle assertions were removed. The focused script now exercises the actual weekly editor and notification panels. PRODUCT.md, DESIGN.md, the design sidecar/surface brief, canonical index, requirements/decisions, known limitations, READMEs and setup/verification records were actually updated. There is no separate Brain directory.

## Verification executed

| Check | Result |
|---|---|
| Final `py -m pytest -q -p no:cacheprovider` | **191 passed**, one existing Starlette/AnyIO deprecation warning, 185.75s |
| Targeted `py -m pytest -q tests/test_updates.py -p no:cacheprovider` | 16 passed; final post-notification-link rerun 5.84s, one same warning. The 191-test complete suite preceded that presentation-link addition; targeted tests and browser workflow passed again afterward. |
| `py scripts/verify_phase5_browser.py` | Exit 0; original nine workflow/security/integrity groups, no findings/JS errors |
| `py scripts/verify_redesign_browser.py` final | Exit 0; no findings, JS errors or external requests |
| Responsive evidence | 375/768/1280/1440/1920px layout, label, target and representative contrast checks; 844×390 landscape; desktop/tablet/phone screenshots |
| New UI assertions | Weekly native pickers, invalid end time, split-shift serialization, text fallback, hash/back selection, patient/doctor populated panels, unread/mark-read, real cancellation arriving in an open panel without toast overlap, Escape focus and refresh removing the cancelled appointment row |
| Calendar tests | Role/CSRF denial; notification ownership/forged query isolation; OAuth scope, session binding, expiration and replay; encrypted storage/no secret markup; missing consent; idempotent export, move and cancellation; preservation of unrelated events/local bookings; malformed provider/host rejection; disconnect/revocation failure |
| JavaScript/Python syntax | `node --check static/app.js` and compileall passed |
| Design documentation | Effective navy color/token/font parity, documented schema-v2 sidecar, seven component references and source-size floor validated by documenter |
| Git whitespace | `git diff --check` passed after correcting added Markdown trailing whitespace |

No separate frontend build or TypeScript command exists. Actual Uvicorn startup/HTTP, Python regressions, JS syntax and browser workflows are the relevant checks. No clean pinned-environment rebuild or formal dependency vulnerability audit is claimed; installed FastAPI still differs from the requirements pin, as documented previously.

Initial new-test failure was a wrong synthetic Sam surname in a new assertion, corrected to the existing seed. The first browser attempt matched added weekly buttons with an old broad submit selector; narrowed it to the actual submit button. A restored-layout audit found low placeholder/notice/slot contrast and an unlabeled day picker; fixed and reran. No test was weakened to hide an application defect.

Final screenshot/result evidence: `.design-qa/redesign/run-oc9mn70v/`. Notification links now open the affected doctor's local calendar date, with date-specific API/browser assertions. The independent full review used `run-gx_stpsi` and returned **ship** after valid open-panel recaptures; its two follow-up suggestions (picker wording and agenda refresh cue) were then implemented and scored **resolved**, scope-limited ship. No comp or new visual-world workshop was used because the user's previous-version request fixed the visual authority. The review sampled code/screenshots and is not a formal security/accessibility certification. Physical devices, screen readers, Safari/Firefox and real Google consent/API calls were not checked.

## Running app and data preservation

The loopback site was restarted at `http://localhost:8000`; health and login returned healthy/200. A consistent SQLite backup was taken into ignored `.design-qa/runtime-backups/` before startup added the optional tables. Existing bookings/accounts were preserved; no DB reset or seed schedule was applied to the running application. All automated workflows used disposable databases. The server is left running for user review.

## Website review: suggested next fixes

1. **Complete Google setup and live-test with synthetic appointments.** Check connect, repeated sync, reschedule, cancellation, revoked access and reconnect against the intended Google account. This is the remaining activation step, not a code/test success claim.
2. **Reduce repeated weekly editing if needed.** A Copy hours to selected days control or collapsed daily rows would reduce the long mobile form. Not implemented without further preference; the present editor supports every existing split shift directly.
3. **Retain unsaved fields on server validation errors.** Current redirect/notice handling can make doctors re-enter rejected schedule/block edits. Preserve the submitted values and link errors to the relevant day/range in a later focused task.
4. **Choose delivery beyond an open tab if needed.** Email/SMS or background push requires separate consent/configuration and delivery infrastructure. Current in-app polling is explicit; it is not a reminder service.
5. **Keep the existing public-release gates.** Account recovery, login throttling, real credentials, HTTPS/Secure cookies, persistent backups/retention and broader browser/accessibility/security review remain prerequisites for real use. This task does not turn the synthetic-data MVP into a production healthcare service.

Next permitted action: inspect the running restored UI and configure Google using the supplied guide. Public deployment and additional convenience features remain separate tasks.

The shared docs/INDEX.md also contains concurrent interview-preparation edits. Its working-tree navigation update is preserved but excluded from this task's commit, along with the separately staged interview documents; no unrelated staging is reset or committed.

## Doctor navigation and picker follow-up (2026-11-01)

The patient doctor-name field is now a native dropdown populated from all configured doctors, including when results are filtered. The existing server-side name filter and availability rules remain unchanged. On the doctor dashboard, Working hours and Blocked time now show their respective card independently; Overview still shows the full dashboard. The selected working-hours view uses a two-column week layout on wider screens and one column on narrow screens. No booking or Google sync behavior changed.

Verification: 17 update tests passed; the focused dropdown assertion covers filtered results. The browser workflow passed with zero findings, JavaScript errors or external requests, including new visibility assertions for both workspace links and browser Back. Evidence: `.design-qa/redesign/run-pbihb2ng/`. `node --check` and `git diff --check` passed. Live Google OAuth remains unconfigured and was not tested.
