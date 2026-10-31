# SlotZero narrated workflow pitch

Goal: explain the implemented doctor and patient workflow through Asha and Dr. Meera's appointment, ending with the live prototype link.

Output: a separate editable HyperFrames project, 1920 × 1080, 30 fps; H.264/AAC MP4 plus narration audio and script. Preserve the original 25-second film.

Story: use the existing short film's booking conflict as the hook, then follow sign-in → registration → doctor hours and blocks → patient discovery → dual-zone slots → confirmation → doctor calendar → rejected competing request → safe reschedule → cancellation → activity history → CTA. This extends the established storyboard rather than changing the product pitch.

Timing: approximately three minutes, finalized against generated narration. Each scene lasts for its voice segment plus 0.6 seconds. Titles and product screens settle within 0.6 seconds. At least two seconds on the final CTA.

Look: actual locally rendered app screens on paper #f6f8fb and navy #101b2d; green #16865e, mint #90e2bc. Reuse Manrope 800 for 64–90 px titles and DM Sans for 28–34 px explanatory copy. 192 px title-safe horizontal margins; no fake product UI, metrics, medical outcomes or customer data. Reuse the existing browser-device-stage treatment where useful. Product UI is cropped to the relevant section, not squeezed into an unreadable full page.

Motion: deterministic paused GSAP timelines; cuts between steps, one 0.45-second settle and a focus cue inside each shot. Readable holds are deliberate and tagged. No decorative camera drift. Use the actual booking result and rejection notices as proof.

Sound: requested natural Indian English narration through HeyGen after account connection, at a clear conversational pace. Existing credited music under speech at reduced gain, with fades. No voice cloning or avatar. Narration provider remains HeyGen unless the user changes that preference.

Scope: only new media assets, scripts and handoff documentation in this folder, plus a relevant project documentation update. Application code, database and deployment are not changed. Capture an isolated temporary SQLite database with fictional users and fixed example dates. No real patient data. The live login and doctor workspace were inspected read-only apart from routine sign-in.

Acceptance: cover all sixteen narration beats; assert booking, conflict, reschedule, cancellation and release in the isolated fixture; check the composition and inspect representative frames; validate final dimensions, duration, audio presence, full decode and loudness. Do not claim subjective listening review if unavailable. Do not claim public deployment concurrency or persistence was tested.

Affected files: narration.json, narration.md, prepare-workflow.py, workflow-evidence.json, composition/assets, composition/index.html and scene files, final media, README.md and docs/product/11-DEMO-AND-SUBMISSION-PACK.md. No application callers, fixtures or exports are changed.

Banned: credential panels, production-readiness claims, fabricated functionality, stock doctor images, avatar footage, gradients, particles, floating UI loops, unreadable full-page screenshots and background music competing with speech.
