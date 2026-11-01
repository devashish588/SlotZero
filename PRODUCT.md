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

Keep existing authentication, roles, ownership, CSRF, booking transactions, idempotency, cancellation, atomic rescheduling and audit history. Keep doctor-local date selection and accurate IANA-zone display for Asia/Kolkata, Europe/London and America/New_York. Working hours start empty. Do not invent appointments, metrics, testimonials, integrations or doctor registration. The two-hour rescheduling cutoff remains a documented assumption, unchanged by this task.

## Brand Commitments

Preserve SlotZero's name and existing S0 mark. A premium visual redesign is authorized, with all factual content and functionality preserved.

## Evidence on Hand

Six existing screens, live synthetic demo accounts, dynamically generated slots, existing tests and browser verification. No licensed photography, testimonials or customer statistics are supplied or required for these working screens.

## Product Principles

- Preserve confirmed appointments and display their times accurately.
- Make the next task clear for each role.
- Communicate empty, pending, successful and failed states honestly.
- Keep the existing single-service architecture.

## Accessibility & Inclusion

Semantic HTML, keyboard operation, visible focus, accessible forms, readable contrast, touch targets and reduced-motion support are explicit redesign requirements.
