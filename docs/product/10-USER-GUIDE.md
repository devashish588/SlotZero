# SlotZero — User Guide

## 1. Sign in

Open the application URL and use a supplied demo account, or register as a patient. The app redirects users to a dashboard based on the role stored on the account.

### Demo accounts

| Person | Role | Email | Password | Time zone |
|---|---|---|---|---|
| Dr. Meera Sharma | Doctor | `meera@slotzero.demo` | `Meera@123` | `Europe/London` |
| Dr. Alex Morgan | Doctor | `alex@slotzero.demo` | `Alex@123` | `America/New_York` |
| Asha Verma | Patient | `asha@slotzero.demo` | `Asha@123` | `Asia/Kolkata` |
| Sam Taylor | Patient | `sam@slotzero.demo` | `Sam@123` | `America/New_York` |

## 2. Doctor guide

### Configure weekly working hours

1. Sign in as a doctor.
2. Find the Working Hours section of the dashboard.
3. Enter one line per weekday using abbreviated day labels and 24-hour clock values.
4. Example:

```text
Mon: 09:00-12:00,13:00-17:00
Tue: 09:00-12:00,13:00-17:00
Wed: 09:00-12:00,13:00-17:00
Thu: 09:00-12:00,13:00-17:00
Fri: 09:00-12:00,13:00-17:00
Sat:
Sun:
```

5. Choose your IANA timezone and 15, 30 or 60 minutes. Your profile is shown above the settings.
6. Save. If the new hours or timezone would exclude an active confirmed appointment,
   the application rejects the whole change. Existing bookings and blocks keep
   their UTC instants when the timezone changes.

### Add a break or unavailable period

1. Select a future date in the doctor's own local calendar.
2. Enter start and end times and an optional label.
3. Save the block.
4. If it overlaps a confirmed booking, the block is rejected and the notice identifies
   an affected appointment ID; the appointment remains unchanged. Blocks cover one
   local day; add separate blocks for a holiday spanning multiple days.

### View appointments

Choose a date on the doctor dashboard. Appointments assigned to the signed-in doctor appear in the doctor's timezone. The doctor cannot view another doctor's bookings.

## 3. Patient guide

### Register

1. Open Register.
2. Enter name, email and a password of at least 10 characters.
3. Select one supported IANA time zone: `Asia/Kolkata`, `Europe/London` or `America/New_York`.
4. Create the account and sign in.

Public registration creates a patient account only. Patients cannot choose the doctor role.

### Find a doctor

1. Use the doctor name and specialization filters.
2. Optionally choose an availability date.
3. Open a doctor profile to view slots.
4. The date selector on the doctor profile is the doctor's local calendar date.

### Book

1. Select an available slot.
2. Review the displayed patient-local time and doctor-local time.
3. Confirm booking.
4. On success, the appointment appears under Your Next Appointments.
5. If another patient wins the same slot first, the app reports that the slot is no longer available.

### Cancel

1. Find the appointment under Your Next Appointments.
2. Select Cancel and confirm.
3. Cancellation is permitted only when at least two hours remain before start.
4. The slot is then eligible to appear as available again if schedule and block rules permit it.

### Reschedule

1. Select Reschedule on an upcoming appointment.
2. Choose a replacement date and slot.
3. Confirm the move.
4. The existing appointment is updated only if the replacement is still available.
5. If the move fails, the original appointment remains confirmed.

The MVP currently uses the same two-hour cutoff for rescheduling as cancellation; this is an implementation assumption.

## 4. Time-zone display

The slot list shows the selected time in the patient's zone and the doctor's zone. Appointment dashboards show times in the signed-in user's zone. The zone label should be included when communicating the appointment time outside the app.

## 5. Safe demo practices

- Use fictional names and sample appointment data only.
- Do not enter symptoms, diagnoses, medical records or real patient data.
- Do not share demo credentials in a public post beyond the intended judge instructions.
- Sign out after a demo session on a shared machine.
