# SlotZero — narrated workflow pitch

Completed 2026-10-31. A separate **2 minute 51 second, 1080p** product walkthrough with **Aditya, Indian English**, generated through the connected HeyGen account using HeyGen Voice (Orca). The original 25-second pitch is preserved.

## Deliverables

- [Finished MP4](slotzero-workflow-voiceover.mp4): 171.134 seconds, 1920×1080, 30 fps, H.264/AAC, 9.7 MB.
- [Narration MP3](composition/assets/narration.mp3): 168.803 seconds, voice only.
- [Narration script](narration.md), [scene timings](scene-timing.json) and [editable composition](composition/index.html).
- [Poster](poster.jpg), [decoded final-frame sheet](final-contact-sheet.jpg), [credits](CREDITS.md) and [review](REVIEW.md).

The sixteen scenes cover the pitch, sign-in, patient registration, doctor hours, blocked periods, patient discovery, slot selection, time zones, booking, doctor calendar, a rejected competing request, safe rescheduling, slot release, cancellation, activity history and the prototype CTA. Selected screenshots are rendered from the existing app, with fictional state and panel widths adjusted for video. This is a narrated walkthrough, not an uninterrupted live screen recording.

## Verification

- `prepare-workflow.py` passed six groups of assertions in a disposable SQLite database: working hours and blocked-time exclusion; one confirmation and a rejected competing request; overlapping doctor block rejection; safe failed/successful rescheduling and released old slot; unchanged UTC instant after display-zone change; cancellation, release and event history. The temporary database was removed. Public login and the doctor workspace were inspected; no deployed booking or schedule was written.
- `build-video.py` aligned all **432 words** exactly with HeyGen's returned timestamps and checked every scene boundary. Timing: 0.3 seconds of lead, continuous narration and two seconds after the voice ends.
- Final HyperFrames check passed with **zero errors and zero warnings** across lint, runtime, layout, motion, contrast, craft and audio. All **28 sampled DOM-text contrast checks** passed. Screenshot text was visually reviewed and is not counted in that measurement.
- Beat sheets, phone sheets, a cut boundary and eight decoded final frames were reviewed. Product fine print reads best full-screen on desktop.
- `verify-media.py` confirmed **5,134 frames**, the expected dimensions/codecs/duration and a complete FFmpeg decode without errors. Final audio mean **−19.9 dB**, peak **−3.2 dB**. No mix clipping was detected. No subjective listening review is claimed.

Evidence: `workflow-evidence.json`, `speech-metadata.json`, `check.json`, `media-verification.json`, `media-info.json` and `snapshots.json`. Verbose logs, render scratch files and the full review-frame set remain local and are ignored by Git.

## Rebuild

The rendered project uses local assets and does not require HeyGen access again. With Node.js 22+, Chrome, FFmpeg and FFprobe available:

```powershell
cd brag-output/voiceover/composition
npm run dev
npm run check
npm run render
```

If the system temporary drive is short of space, set process-local `TEMP` and `TMP` to an existing folder on a drive with several GB free before rendering. This delivery used `.render-tmp/` on the project drive. The preview was checked over HTTP before export and stopped after review.

Regenerating screenshots requires the app's Python dependencies and Playwright. The preparation script runs only against its disposable database. Rebuilding timing and scenes uses the existing `narration.json` and `speech-metadata.json`; it does not generate speech. A new narration request requires the user's chosen HeyGen connection and the speech tool's retry rules.

## Limits and next action

No deployment persistence, public simultaneous booking race, full application regression suite or subjective accent/listening review was performed in this media task. Application code and existing presentations were not changed. Canonical project context was updated in `docs/product/11-DEMO-AND-SUBMISSION-PACK.md`; there is no separate Brain directory. Review the video with sound before sharing, and include the music attribution from `CREDITS.md`. No public upload or submission was made.
