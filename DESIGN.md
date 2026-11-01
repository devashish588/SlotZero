---
name: SlotZero
description: Restored navy scheduling workspace with readable local fonts and targeted
  enhancements.
colors:
  navy: '#101b2d'
  navy-2: '#17263d'
  ink: '#18263a'
  muted: '#526278'
  line: '#dce3eb'
  paper: '#f6f8fb'
  white: '#fff'
  mint: '#ddf5eb'
  green: '#16865e'
  green-dark: '#116c4b'
  lav: '#eee9ff'
  amber: '#fff0d8'
  red: '#c84d4d'
  primary-fill: '#13875e'
  primary-hover: '#0f704e'
  nav-selected: '#23364e'
  nav-label: '#9cabc0'
  outline-ink: '#40516a'
  confirmed-bg: '#e9f7ef'
typography:
  display:
    fontFamily: Lexend, Segoe UI, sans-serif
    fontSize: 32px
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: -1px
  headline:
    fontFamily: Lexend, Segoe UI, sans-serif
    fontSize: 23px
    fontWeight: 700
    letterSpacing: -0.7px
  body:
    fontFamily: Source Sans 3, Segoe UI, sans-serif
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: Source Sans 3, Segoe UI, sans-serif
    fontSize: 15px
    fontWeight: 700
  supporting:
    fontFamily: Source Sans 3, Segoe UI, sans-serif
    fontSize: 13px
    fontWeight: 400
rounded:
  button: 9px
  nav: 10px
  stat-card: 14px
  panel: 15px
  status: 20px
spacing:
  '8': 8px
  '12': 12px
  '16': 16px
  '20': 20px
  '24': 24px
components:
  button-primary:
    backgroundColor: '{colors.primary-fill}'
    textColor: '{colors.white}'
    rounded: '{rounded.button}'
    padding: 10px 16px
  button-dark:
    backgroundColor: '{colors.navy}'
    textColor: '{colors.white}'
    rounded: '{rounded.button}'
    padding: 10px 16px
  button-outline:
    backgroundColor: '{colors.white}'
    textColor: '{colors.outline-ink}'
    rounded: '{rounded.button}'
    padding: 10px 16px
  input:
    backgroundColor: '{colors.white}'
    textColor: '#34445a'
    rounded: '{rounded.button}'
    padding: 11px 12px
  nav-active:
    backgroundColor: '{colors.nav-selected}'
    textColor: '{colors.white}'
    rounded: '{rounded.nav}'
  work-card:
    backgroundColor: '{colors.white}'
    rounded: '{rounded.panel}'
    padding: 20px
  status-confirmed:
    backgroundColor: '{colors.confirmed-bg}'
    textColor: '{colors.green}'
    rounded: '{rounded.status}'
    padding: 6px 9px
---

# Design System: SlotZero

## Overview

**Creative North Star: "The restored navy workspace"**

On 2026-11-01 the user explicitly rejected the green care-register redesign and requested the previous navy/card design back, with larger readable fonts and targeted functional updates. That reversal supersedes the former green direction and its surface contract. Preserve the restored compositions rather than treating the earlier redesign as authority.

The implementation source is slotzero-mvp/static/styles.css, restored from 2df0d49 with its readable font floor, followed by enhancements.css for local fonts, readability and new widgets. This document extracts that effective cascade. Frontmatter entries matching root variables keep their existing names; component-specific literal colors remain descriptive snapshots, not a competing CSS token implementation. This is a light-theme site, with a dark navy navigation rail rather than a dark-mode option.

**Key Characteristics:**
- Navy navigation, pale gray work background and white rounded cards.
- Green primary actions with lavender and amber accents retained in the original cards.
- Local Lexend headings and Source Sans 3 body content.
- Existing screen compositions plus focused navigation, schedule and update widgets.

## Colors

### Primary

Navy and its second shade establish the shell. Green and green-dark support actions, time slots and focus; mint provides a light complementary surface. The primary filled button retains its original component-specific green fill and deeper hover. These are extracted separately from the general green variable because the source still distinguishes them.

### Secondary

Lavender and amber remain the original supporting card accents. The rejected redesign's single-accent restriction no longer applies.

### Neutral

Ink, muted, line, paper and white keep their source names. The enhancement stylesheet overrides muted and line with darker effective values; the frontmatter records those final values. Active navigation uses the original selected-navy literal, white text and mint inset marker. Supporting literal colors remain in the legacy source, so future work should inspect the effective cascade before assuming every color is tokenized.

### Semantic states

Red identifies destructive actions and notification counts. Existing success, information and error notices retain their original distinct tinted backgrounds and text. Meaning is also present in text and controls rather than color alone.

**The Restored Identity Rule.** Keep the navy/card compositions; targeted usability changes must not reintroduce the rejected green visual world.

## Typography

Local variable Lexend replaces Manrope for headings and selected emphasized values; local Source Sans 3 replaces DM Sans for body copy and controls. Both load from the app's WOFF2 files with matching font preloads, declared variable weight ranges and font-display swap. No external font stylesheet is loaded. Segoe UI and sans-serif are fallback families. Textarea schedule syntax retains its original monospace treatment.

Normal body text and form entry are 16px. Main workspace headings are 32px, section headings 23px, card headings and slot times commonly 19px, and action labels 15px. Supporting working content generally uses 13â€“15px. Mobile workspace headings reduce to 28px and sections to 22px. Existing bold weights are preserved: large workspace headings use 800; button and form labels use 700. The account headline remains a larger Lexend treatment, not a new landing-page composition.

The readability update raises explicit font-size declarations below 13px to 13px across the restored and enhancement stylesheets, including branding and summary labels. Supporting content retains that 13px floor while body and entry text remain larger. This source-level rule is not a completed accessibility audit.

**The Readable Task Rule.** Keep entry fields at 16px and preserve readable appointment, zone and schedule details; do not shrink task text to fit decoration.

## Layout

The restored desktop shell uses a 252px fixed rail, reduced to 220px below 1100px. Main content caps at 1160px including its padding, with original 42px desktop gutters, 28px below 1100px and 16px on small phones. Doctor discovery remains a card grid, summaries remain cards, booking remains a main card beside its guidance card, and appointments/history retain their original layouts. Settings stack to one column below 1100px.

The targeted mobile navigation fix takes effect at 960px: the rail becomes a full-width header with an expandable menu exposing every role link. It replaces the old icon-only or hidden navigation behavior. Navigation selection follows both path and hash, including back/forward changes. At 640px the header wraps, content grids stack and the original mobile card arrangements remain.

Notifications anchor to the bell on desktop and use a viewport-positioned panel on compact layouts. Update toasts are dismissible and constrained to the viewport. The visual weekly editor uses one fieldset per weekday, with paired start/end inputs and controls for split shifts; it serializes to the existing schedule text contract. The original text editor remains the fallback.

## Elevation & Depth

The restored system uses bordered rounded cards with small soft shadows. Doctor cards lift slightly on hover; notifications and toasts use the existing shared shadow. The root shadow is 0 12px 32px rgba(28,43,65,.055). The translucent sticky topbar and original account background treatment are retained. This is a restoration of the user's design, not the earlier flat-workbench system.

## Shapes

The original corner vocabulary is intentionally varied: buttons and form fields use 9px, navigation 10px, summary cards 14px and principal work cards 15px. Status labels retain their pill shape. New notification surfaces follow the existing rounded-card language rather than defining another shape system. Icon and text actions have a 44px minimum hit target; form entry is at least 46px high in the enhancement layer.

## Components

### Actions and fields

Primary green, dark navy and white outline buttons retain their existing variants and original content. Enhancements increase target sizes and text, preserve native validation and add visible keyboard focus. Pending forms show their existing progress text and suppress duplicate submission. The visual weekly-hours inputs use native time fields and retain the server's schedule validation; adding another range expresses a split shift, not a new scheduling model.

### Workspace navigation

The selected item reflects the full destination, including working-hours and blocked-time anchors. The mobile menu exposes aria-expanded, keyboard Escape and every role destination. Active markers remain the restored source's visual treatment.

### Notifications

The bell opens a role-scoped appointment-update feed. A count indicates unread activity; Mark all read updates the local read state, and the panel includes loading, empty and error messages. New booking, cancellation and rescheduling events can produce a dismissible status toast. The feed polls every 15 seconds while the page is open. These widgets do not imply email, SMS or push delivery.

### Google Calendar

The doctor's settings card contains an optional Google Calendar connection and manual Sync now action. It exports appointments to a dedicated calendar; it is not automatic live sync and does not replace SlotZero availability. Missing OAuth configuration renders an honest disabled-setup explanation. Patient names are not exported. No live Google connection is claimed by this design record.

### Motion and feedback

The targeted toast enters over 180ms with the shared ease-out curve and an eight-pixel upward offset. Button and icon press feedback translates one pixel. Existing hover and loading treatments remain. Reduced-motion rules stop toast and spinner animation, press transforms, smooth scrolling and transitions without removing the final state.

## Do's and Don'ts

### Do:
- Do preserve the user's restored navy shell, card grid and screen compositions.
- Do layer narrow readability and widget styles through enhancements.css after styles.css.
- Do use the locally served Lexend and Source Sans 3 fonts with reliable fallbacks.
- Do keep split shifts, update state and calendar setup status explicit and truthful.

### Don't:
- Don't reapply the rejected green care-register direction or its flat-row layouts.
- Don't describe manual calendar export as automatic live synchronization.
- Don't claim complete contrast compliance or live OAuth verification from source inspection.
- Don't let UI changes alter the validated scheduling rules or booking authority.
