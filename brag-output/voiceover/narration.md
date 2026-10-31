# SlotZero — Indian English narration

## The pitch — One slot. One confirmed booking.

Two patients choose the same appointment. Who gets it? Slot Zero gives one clear confirmation, while helping doctors and patients stay in sync across time zones.

## Getting started — A workspace for each role

Start at the sign-in page. Doctors enter their scheduling workspace. Patients enter their own dashboard to find a doctor and manage appointments.

## Patient onboarding — Create your patient account

New patients can register with their name, email, a password of at least ten characters, and a supported time zone. Doctor accounts are provisioned separately.

## Doctor workflow — Your hours become availability

Dr. Meera sets her London time zone, weekly working hours and a thirty-minute consultation length. Split shifts leave room for lunch. Fifteen and sixty-minute appointments are also supported.

## Doctor workflow — Make room for time off

She can add a dated blocked period for a break or time off. The scheduler removes these periods from availability and rejects changes that conflict with confirmed appointments.

## Patient workflow — Find the right doctor

Now Asha signs in from India. She searches by doctor name, specialization, or availability date. Each doctor card shows the consultation length, time zone and available slots.

## Patient workflow — Choose a date and time

She opens Dr. Meera's profile and chooses a date on the doctor's calendar. Slots come from working hours, blocked periods and existing bookings, rather than a fixed timetable.

## Time zones — One appointment. Local times.

The same slot appears in both local times. In this example, ten in the morning in London is three thirty in the afternoon in Kolkata, and five in New York.

## Patient workflow — Book with a final availability check

Asha selects Book and confirms. The server checks the slot again before saving. Her confirmed appointment appears on her dashboard, with reschedule and cancel actions beside it.

## Doctor workflow — The same booking reaches the doctor

On Dr. Meera's daily calendar, the same booking appears with Asha's details and the doctor's local time. Both views represent the same appointment stored in coordinated universal time.

## Booking protection — A clear answer for the second patient

If Sam submits the same slot after Asha, he receives an unavailable notice. In this shared-database demo, transaction checks and overlap protection keep that slot to one confirmed booking.

## Manage appointments — Choose a replacement safely

When plans change, Asha opens Reschedule and selects a replacement. The move succeeds only if that time is still available. A failed move keeps her original booking confirmed.

## Manage appointments — New time saved. Old slot released.

After a successful move, her dashboard shows the new time and the previous slot becomes available again. The activity log records the change.

## Manage appointments — Cancel while eligible

Cancellation and rescheduling require at least two hours before the appointment starts in this prototype. Cancelling releases the slot, so another patient can book it if it remains eligible.

## Stay in sync — Keep a record of every change

Both workspaces keep appointment activity. Patients can also change their display time zone. Local times update while the underlying appointment stays the same.

## Try the prototype — Appointments, in sync.

That's Slot Zero: doctor-controlled availability, patient self-service, and conflict-checked bookings across India, London and New York. Explore the prototype today. This demonstration uses fictional data; reminders and payments are not included.