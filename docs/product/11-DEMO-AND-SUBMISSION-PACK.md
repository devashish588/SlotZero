# SlotZero — Demo and Submission Pack

## 1. Demo objective

Tell one short story that proves SlotZero solves the challenge: a doctor configures availability, a patient books, the doctor sees the same booking, a competing patient cannot double-book, and the booking can be safely changed. Include timezone handling.

### Delivered narrated walkthrough — 2026-10-31

A separate [2 minute 51 second workflow pitch](../../brag-output/voiceover/slotzero-workflow-voiceover.mp4) now covers sign-in/registration, doctor hours and blocked time, patient discovery and booking, dual-zone display, doctor confirmation, a rejected competing request, safe rescheduling, cancellation, slot release and history. It uses Aditya's Indian English voice through the user's connected HeyGen account, with background music beneath the narration. The existing 25-second launch film is preserved.

The walkthrough uses actual locally rendered templates with fictional state, not an uninterrupted recording of the public deployment. The disposable fixture asserted the demonstrated lifecycle and exactly one confirmation after sequential competing requests. HyperFrames checks passed with zero errors/warnings; the final 1920×1080 H.264/AAC file fully decoded and its audio peaked at −3.2 dB. This task did not rerun public-deployment concurrency/persistence tests or provide a subjective listening review.

See the [media handoff and verification](../../brag-output/voiceover/README.md), [script](../../brag-output/voiceover/narration.md) and [music credit](../../brag-output/voiceover/CREDITS.md). Review with sound before sharing. No public upload or submission was made.

## 2. Suggested 2–3 minute demo script

> **0:00–0:15 — Problem and product**  
> “SlotZero is a conflict-free appointment scheduler for doctors and patients working across India, London and New York. The key is that availability is generated dynamically and every booking is revalidated by the backend.”
>
> **0:15–0:40 — Doctor setup**  
> Sign in as Dr. Meera. Show `Europe/London`. Configure weekday working hours with a lunch break and choose 30-minute consultations. Explain that no slots are hardcoded.
>
> **0:40–1:05 — Patient discovery and booking**  
> Sign in as Asha in `Asia/Kolkata`. Find Dr. Meera, select a future date on the doctor's calendar, compare the patient and doctor time labels, and book a slot.
>
> **1:05–1:25 — Doctor confirmation**  
> Sign back in as Dr. Meera and show the appointment on the doctor's dashboard in London local time. Explain that both dashboards represent the same UTC instant.
>
> **1:25–1:50 — Conflict prevention**  
> Sign in as Sam and attempt the exact same slot. Show the rejected booking. Explain that the transaction rechecks availability and a database trigger rejects overlapping confirmed appointments; the test suite also races two requests and asserts only one row is confirmed.
>
> **1:50–2:15 — Manage the appointment**  
> As Asha, reschedule or cancel the booking. Show the activity history and availability update. Mention the two-hour cancellation rule.
>
> **2:15–2:40 — Time zones and close**  
> Show the relevant timezone labels and explain UTC storage plus IANA conversion, with DST gap/fold times rejected. Close with the project’s key engineering principle: correctness before extra features.

Adjust timings to fit a clean 2–3 minute recording. Use the deployed build, not a local-only URL, for the final judge video.

## 3. Demo preparation checklist

- [ ] Deployed URL opens in a private/incognito window.
- [ ] Demo users exist on the deployed database.
- [ ] Doctor schedules are configured on the deployed database.
- [ ] Select a future working day with at least two available 30-minute slots.
- [ ] Ensure one slot is free for Asha and the exact same slot can be attempted by Sam.
- [ ] Ensure no existing confirmed appointment or blocked period consumes the selected slot.
- [ ] Have patient and doctor credentials ready in a private, controlled note.
- [ ] Run the booking-conflict scenario before recording.
- [ ] Prepare one eligible appointment for cancellation/reschedule demo.
- [ ] Have a timezone/DST example prepared and verified.
- [ ] Record one uninterrupted backup demo.
- [ ] Verify video link permissions before submitting.

## 4. Eight-slide PDF outline (challenge maximum: 8 slides)

### Slide 1 — SlotZero

**Conflict-Free Doctor Appointment Scheduler**  
MedaVida hackathon · Problem, team/individual identification and one-line value proposition.

### Slide 2 — The problem

- Manual appointment coordination creates double-booking risk.
- Cancelled slots may remain blocked.
- Doctor and patient local times can differ.
- Trust depends on consistency and clear ownership.

### Slide 3 — Product solution

- Two user-facing portals: doctor and patient.
- Operator-provisioned doctor identities; no admin dashboard.
- Doctors set weekly hours and blocked time.
- Patients discover doctors and manage their own bookings.

### Slide 4 — End-to-end workflow

Visual: doctor schedule → dynamic availability → patient selection → server recheck → confirmed appointment → doctor/patient dashboards.

### Slide 5 — Architecture and data integrity

- FastAPI + Jinja2 + Python.
- SQLite transactional write path for the MVP.
- UTC appointment instants and IANA time zones.
- Overlap trigger and idempotency uniqueness.
- Note future PostgreSQL migration for multi-instance production.

### Slide 6 — Time zones and edge cases

- `Asia/Kolkata`, `Europe/London`, `America/New_York`.
- One UTC instant, viewer-specific local time.
- DST gaps/folds rejected.
- Adjacent appointments allowed; overlapping appointments rejected.

### Slide 7 — Validation and hardest engineering problem

- Eight automated tests currently pass.
- Concurrent booking race test: one winner only.
- Ownership and role tests.
- Atomic reschedule and slot-release checks.
- Hardest problem: maintaining booking correctness under concurrency and timezone conversion.

### Slide 8 — Demo, limitations and next steps

- Link/QR to deployed demo and video.
- Current limitations: SQLite single-instance, no reminders, no admin UI, no password reset.
- Next: PostgreSQL, rate limiting, operational monitoring and broader timezone/browser testing.

## 5. Suggested LinkedIn post draft

> I built **SlotZero**, a conflict-free doctor appointment scheduler, during the MedaVida AI SDE Intern hackathon.
>
> The challenge looked simple at first: let patients book appointments. The real engineering challenge was making those bookings reliable when two people choose the same slot and when doctors and patients live in different time zones.
>
> SlotZero lets doctors configure weekly availability and blocked periods, while patients can discover doctors, book, cancel and reschedule appointments. The backend rechecks every booking, protects against overlapping appointments, and stores appointment instants in UTC for consistent timezone display across India, London and New York.
>
> One of the most important parts was testing the race condition: two requests competing for one slot must never create two confirmed appointments.
>
> This build reinforced a lesson I value as an engineer: a polished interface matters, but correctness and trustworthy system behaviour matter more.
>
> Demo: [ADD DEMO VIDEO LINK]  
> Live prototype: [ADD DEPLOYED URL]  
> Code: [ADD REPOSITORY OR ZIP LINK]
>
> #MedaVida #SlotZero #SoftwareEngineering #AIHackathon #BackendEngineering #FastAPI
>
> Before publishing, add the required tags/mentions for MedaVida, Christina Camacho, Mallikarjuna Mudiam, Mahesh Das and team members as requested by the participant brief. Do not claim features or test results that are not in the submitted build.

## 6. Submission checklist from the participant brief

- [ ] Source code ZIP contains app and README setup instructions.
- [ ] ZIP excludes `.env`, secrets, dependency folders and large generated artifacts.
- [ ] Working deployed prototype link is accessible.
- [ ] Doctor and patient judge credentials or safe access instructions are included.
- [ ] Slides PDF has no more than eight slides.
- [ ] Demo video is 2–3 minutes and shows doctor availability, patient booking, doctor bookings, cancellation/rescheduling and one conflict or timezone case.
- [ ] LinkedIn post includes demo video/link and required tags.
- [ ] All links open in a private/incognito browser.
- [ ] Submission form is completed before the stated deadline.
- [ ] Code freeze is respected after submission deadline.

The participant brief lists submission through `forms.gle/H8dHiUdMusJA5n4E7` and states the deadline as 5:00 PM on the event day. Verify the current organizer instructions before submitting; this document does not submit anything.
