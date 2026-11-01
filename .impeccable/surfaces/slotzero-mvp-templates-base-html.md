---
version: 1
slug: "slotzero-mvp-templates-base-html"
primary_target: "slotzero-mvp/templates/base.html"
related_targets: ["slotzero-mvp/templates/login.html","slotzero-mvp/templates/register.html","slotzero-mvp/templates/patient_dashboard.html","slotzero-mvp/templates/doctor_dashboard.html","slotzero-mvp/templates/doctor_detail.html","slotzero-mvp/templates/reschedule.html","slotzero-mvp/static/styles.css","slotzero-mvp/static/enhancements.css"]
---

# SlotZero restoration and targeted updates

Mode: Operate. On 2026-11-01 the user rejected the prior green redesign and explicitly requested restoration of the navy/card design from 2df0d49, retaining local readable fonts and targeted usability/features. This replaces the earlier direction contract; its seed and flat green visual rules no longer govern these screens.

## Current scope

Preserve the six existing screens and their original card compositions. Improve readable task text, active path/hash navigation and access to every role link on mobile. Add a day-by-day native-time weekly editor with split shifts and text fallback; a role-scoped notification bell/feed with dismissible update toast; and optional doctor-authorized manual calendar export with honest unconfigured state.

## Boundaries

PRODUCT.md and the canonical project documents retain product and scheduling authority. DESIGN.md records the effective navy styles.css plus enhancements.css cascade. No stock imagery, invented metrics, new marketing sections or visual-world workshop is required. Calendar configuration and live OAuth are separate operational gates; manual export never changes SlotZero availability.

## Verification status

Record tests and rendered findings in the task verification report. This brief makes no screenshot, accessibility-pass or live calendar claim; implementation remains subject to independent review.
