# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Patients discover doctors, choose available appointments and manage bookings. Doctors configure availability, block time and review patient appointments.

## Product Purpose

SlotZero is the MedaVida hackathon's conflict-free appointment scheduling demo. The user confirmed on 2026-11-01 that the documented product scope and scheduling rules must be preserved throughout the redesign.

## Operating Context

FastAPI/Jinja2, SQLite and vanilla JavaScript/CSS. Synthetic data only. This is a locally verified demo, not a production healthcare service. Canonical context remains in docs/INDEX.md and the documents it links. The original challenge brief is absent.

## Capabilities and Constraints

Keep existing authentication, roles, ownership, CSRF, booking transactions, idempotency, cancellation, atomic rescheduling and audit history. Keep doctor-local date selection and accurate IANA-zone display for Asia/Kolkata, Europe/London and America/New_York. Working hours start empty. Do not invent appointments, metrics, testimonials or doctor registration. The two-hour rescheduling cutoff remains a documented assumption. On 2026-11-01 the user additionally authorized an easier weekly-hours editor, in-app appointment notifications and optional Google Calendar sync. The integration is a manual, doctor-authorized export to a separate app-created calendar; Google edits do not alter SlotZero availability or booking rules. Google OAuth configuration/consent is required before live use.

## Brand Commitments

Preserve SlotZero's name and existing S0 mark. On 2026-11-01 the user rejected the green redesign and explicitly requested restoration of the previous navy/card layout, with larger readable fonts and targeted workflow fixes. That instruction supersedes the earlier visual redesign direction.

## Evidence on Hand

Six existing screens, live synthetic demo accounts, dynamically generated slots, existing tests and browser verification. No licensed photography, testimonials or customer statistics are supplied or required for these working screens.

## Product Principles

- Preserve confirmed appointments and display their times accurately.
- Make the next task clear for each role.
- Communicate empty, pending, successful and failed states honestly.
- Keep the existing single-service architecture.

## Accessibility & Inclusion

Semantic HTML, keyboard operation, visible focus, accessible forms, readable contrast, touch targets and reduced-motion support are explicit redesign requirements.
