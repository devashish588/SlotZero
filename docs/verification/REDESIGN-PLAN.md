# SlotZero redesign — 2026-11-01

## Scope and acceptance

The user authorized a complete visual redesign and confirmed that documented scope and scheduling rules stay unchanged. Six screens: `/login` (also `/`), `/register`, `/patient/dashboard`, `/doctors/{doctor_id}`, `/appointments/{appointment_id}/reschedule`, `/doctor/dashboard`. All are working app screens, including account access. Preserve backend, factual copy, navigation, forms, identity/CSRF/idempotency fields and JS selectors. Preserve unrelated untracked user artifacts; changes are isolated by explicit file scope rather than stashing those artifacts.

Edit: all seven existing templates, static/styles.css, static/app.js. Create: static/tokens.css, static/base.css, licensed local fonts, PRODUCT.md, DESIGN.md, design context and verification records, focused browser regression checks. Delete: no routes or component trees. No framework, runtime package or animation dependency is needed.

Acceptance: real registration/login, role navigation, filters, zone updates, schedule/block editing, dynamic booking, cancellation/rescheduling and history remain working. Keyboard navigation, 44px targets, readable contrast, reduced motion, no clipping at 375/768/1280/1440/1920, readable errors/empty states and pending feedback. Execute original regression suite and browser workflow; inspect screenshots and Git diff.

## Research and direction

UI/UX Pro Max generated a healthcare system; its testimonial-carousel/neumorphism suggestions do not fit a transactional app and are rejected. Focused typography results recommended Lexend + Source Sans 3 for healthcare readability. The HTML stack search supplied applicable label/control guidance only; no Tailwind is introduced. Hallmark's existing-site workflow and app-screen exceptions apply. Impeccable initialized product context and ran its Operate concept seed (reference `seed:56c3d1f7b144a19c`); the first offline roll was retried successfully with its API. The user's explicit instruction to explore and select the strongest direction delegates selection here, superseding a separate skill preference ballot.

Three viable directions compared: care register (green, precise time columns, friendly readable type), transit timetable (cobalt, denser rows, stark numerals), practice notebook (warm neutrals, editorial type, paperlike settings). Care register wins on existing brand continuity, patient readability and slot clarity. The shell remains familiar; typography, density, surfaces and time alignment carry the new identity. Hallmark dealt Dose, Wayfind and Furrow; Dose's green/ink balance informs the selected approach, while retained-brand app scaffolding prevents importing themed ornament. No plastic/glass, grain, decorative hero, stock photographs or simulated data is introduced. The split-flap, dance-score, coded record-sleeve and centre-rail reference challengers lose product clarity for these patient tasks. Their useful discipline is aligned time rows and consistent rhythm, not their visual costume.

## Direction contract

THESIS: Make the real two-zone appointment list the memorable object; distinguish care selection from booking commitment without adding marketing sections.

OWN-WORLD: Green-black navigation, pale green ground, clear work surfaces, one deep-green action, Lexend headings and Source Sans 3 content. Restrained edge/radius language; time data aligns and wraps without abbreviation.

STORY: Sign in, find a doctor, choose a doctor-local date, compare both zones and confirm. Doctors see the daily agenda before adjusting availability.

FIRST VIEWPORT: Existing role navigation at left, readable identity and zone at top, compact greeting/stat strip, filters immediately above the directory. On booking pages profile, date and actual slots lead. Account pages put a clear form beside the existing brand statement and supported-zone content. Signature interaction: local/doctor time pairing remains visible through booking and replacement selection; pending submission indicates state without hiding content.

FORM: Working care register; code-led app scope, selected under the user's delegated direction choice. `seed:56c3d1f7b144a19c`.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Baseline

Existing Playwright lifecycle check passed with zero findings/JS errors outside the sandbox; screenshots at `C:/Users/hp/AppData/Local/Temp/slotzero-phase5-browser-n_gdf2n7`. Inspected login and patient dashboard. Clear working journeys stay. Tiny supporting type, weak contrast, symbol icons, tracked-cap labels and nested cards are replaced. Hallmark baseline: 301 FAIL, 165 REFLEX, 27 WARN; its render tier could not find puppeteer-core. Baseline static findings include false positives from unrendered Jinja, documented separately from browser evidence. First sandbox pytest/browser attempts encountered temporary-fixture permissions; verification is retried with sufficient local access.
