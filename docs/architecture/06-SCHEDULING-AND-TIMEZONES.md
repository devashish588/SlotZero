# SlotZero — Scheduling and Time-zone Rules

## 1. Supported zones

Only the following IANA identifiers are accepted in the MVP:

| IANA zone | Example user |
|---|---|
| `Asia/Kolkata` | Asha |
| `Europe/London` | Dr. Meera |
| `America/New_York` | Dr. Alex and Sam |

Do not replace these identifiers with fixed UTC offsets. London and New York offsets vary seasonally.

## 2. Source data

- Doctor timezone: stored on the doctor account's `users.timezone` field.
- Doctors can change that zone with weekly hours and duration on their dashboard.
  The change preserves appointment/block UTC instants and rechecks existing active
  bookings against the proposed zone and hours before saving anything.
- Doctor working hours: recurring local wall-clock ranges keyed by weekday.
- Consultation duration: doctor-level setting, 15/30/60 minutes.
- Blocked periods: explicit UTC intervals created from doctor-local date/time input.
- Active occupancy: confirmed appointments stored as UTC intervals.
- Patient timezone: stored on the patient account and used for display.

## 3. Slot generation algorithm

For a requested doctor-local calendar date:

1. Load doctor and doctor IANA zone.
2. Reject dates before the current doctor-local date.
3. Load that weekday's working intervals.
4. Load the doctor's confirmed appointments and blocked periods overlapping the
   selected local day's UTC bounds, once per generation rather than once per slot.
5. For each working interval, start at the opening local time.
6. Step forward in increments equal to the doctor's consultation duration.
7. Keep a candidate only if its full duration fits before the interval's closing time.
8. Strictly convert candidate local start and end to UTC.
9. Reject candidates that hit a daylight-saving gap/fold or whose elapsed UTC duration differs from configured duration.
10. Reject candidates starting in the past.
11. Reject any candidate overlapping a confirmed appointment or block.
12. Render retained slot start in both patient and doctor time zones.

Slots are generated at request time; slot rows are not stored in the database.
Doctor lookup requires a matching profile and doctor-role user; there is no separate
account activation flag. Booking regenerates availability inside `BEGIN IMMEDIATE`
and rejects fractional timestamps rather than rounding them to valid slot starts.
See [Phase 3 verification](../verification/PHASE-3-VERIFICATION.md) for tested concurrency boundaries.

## 4. Interval semantics

The system uses half-open intervals `[start, end)`. Two intervals overlap when:

```text
existing_start < new_end AND existing_end > new_start
```

Examples:

| Existing | Requested | Outcome |
|---|---|---|
| 10:00–10:30 | 10:00–10:30 | Reject |
| 10:00–10:30 | 10:15–10:45 | Reject |
| 10:00–10:30 | 10:30–11:00 | Allow |
| 10:00–10:30 | 09:30–10:00 | Allow |

A candidate must fit entirely inside one working-hours interval; it cannot cross a break or bridge two separate intervals.

## 5. UTC storage and local display

- Database appointment and blocked-period starts/ends are normalized to UTC and serialized with `Z`.
- A booking has one canonical instant, not a separate time per user.
- Doctor dashboard converts the instant to the doctor's zone.
- Patient dashboard converts the instant to the patient's zone.
- Slot selection shows both local representations and their zone labels.

## 6. DST policy

The helper `local_to_utc_strict()` tries both `fold` values and round-trips through UTC.

| Local wall-time condition | MVP policy |
|---|---|
| Normal/unambiguous time | Accept and convert to UTC |
| Nonexistent time during spring-forward gap | Reject |
| Ambiguous time during fall-back fold | Reject; user must choose another time |

The slot generator skips candidate slot boundaries that cannot be strictly resolved. Doctor-entered blocked periods reject invalid wall times with a message.

## 7. Cancellation and rescheduling

- Cancellation is permitted when at least two hours remain before appointment start, including exact equality. The server clock retains subsecond precision for this decision; storage timestamps remain second-resolution UTC.
- After cancellation, status becomes `cancelled`; it no longer occupies availability.
- Reschedule checks the replacement first and updates the existing appointment in one immediate transaction. Identical current-slot retries make no change and add no event. Cancellation and rescheduling audit details preserve full old/new UTC intervals; historical events remain unchanged. Busy/locked writes return controlled retry notices.
- **Assumption:** the same two-hour cutoff is applied to rescheduling, although the challenge states the two-hour rule explicitly for cancellation only.

## 8. Schedule-change safety

- A doctor cannot create a block overlapping a confirmed appointment.
- A doctor cannot save a weekly schedule that excludes a future confirmed appointment.
- The application returns a policy message; it does not silently cancel/remove bookings.

## 9. Important date semantics

- Doctor detail and doctor dashboard date selectors are explicitly doctor-local calendar dates.
- Slot display uses patient and doctor time zones.
- Patient availability-date filtering uses the patient's local midnight through the next local midnight, converted separately to UTC (a 23/24/25-hour window where appropriate). Generate each intersecting doctor-local day and retain starts in that half-open window. The View slots link opens the first matching doctor-local day. Booking/reschedule pages display the full patient-local date and time.

## 10. Recommended future hardening

- Phase 4 verifies London/New York gaps and folds in 2026/2027, ordinary seasonal Kolkata conversions, transition-boundary slot skipping, and patient-local DST calendar windows. See [Phase 4 evidence](../verification/PHASE-4-VERIFICATION.md).
- Consider user-selectable ambiguous fold handling if product needs require it.
- Clarify whether the two-hour rescheduling cutoff should remain or be relaxed.
- If supporting overnight working windows, change the schedule model; the current parser expects same-day intervals with end after start.
