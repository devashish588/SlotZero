---
name: SlotZero
description: A readable care register for appointments across time zones.
colors:
  accent: "#176449"
  accent-deep: "#104d38"
  accent-ink: "#f6fff8"
  focus: "#147354"
  paper: "#f3f6f2"
  paper-2: "#e9efea"
  paper-3: "#dbe9df"
  surface: "#fdfefd"
  ink: "#18372e"
  ink-2: "#304d42"
  muted: "#52665c"
  rule: "#cfdbd2"
  input-edge: "#778d7f"
  shell: "#153e32"
  shell-2: "#255342"
  shell-ink: "#f1f7ee"
  shell-muted: "#c0d7c7"
  shell-rule: "#47705b"
  error: "#9e3531"
  error-paper: "#fbeeea"
  success: "#176449"
  success-paper: "#e0eee5"
  info-paper: "#e9efea"
typography:
  display:
    fontFamily: "Lexend, Segoe UI, sans-serif"
    fontSize: "2rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Lexend, Segoe UI, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Lexend, Segoe UI, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Source Sans 3, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Source Sans 3, Segoe UI, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.5
  supporting:
    fontFamily: "Source Sans 3, Segoe UI, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  input: "8px"
  card: "12px"
spacing:
  3xs: "2px"
  2xs: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  2xl: "64px"
  3xl: "96px"
  space-20: "20px"
  space-32: "32px"
  space-48: "48px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    rounded: "{rounded.input}"
    padding: "12px 20px"
  button-primary-hover:
    backgroundColor: "{colors.accent-deep}"
    textColor: "{colors.accent-ink}"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.accent}"
    rounded: "{rounded.input}"
    padding: "12px 20px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.input}"
    padding: "12px"
  nav-active:
    backgroundColor: "{colors.shell-2}"
    textColor: "{colors.shell-ink}"
    rounded: "{rounded.input}"
    padding: "12px"
  status-confirmed:
    textColor: "{colors.success}"
  work-surface:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "32px"
---

# Design System: SlotZero

## Overview

**Creative North Star: "The care register"**

SlotZero uses a forest-green shell and pale green work areas to frame a readable scheduling tool. Names, dates and paired local times carry the hierarchy. The identity is expressed through type, restrained color and aligned rows rather than decorative medical imagery.

The system is light-theme only. Flat work surfaces, visible field boundaries and compact summaries support repeated tasks; account screens reuse the same palette and type at a larger scale. Product truth remains in PRODUCT.md and the canonical project documents. This file records the built visual system, whose implementation source is slotzero-mvp/static/tokens.css, base.css and styles.css; it does not introduce a second token implementation.

**Key Characteristics:**
- Forest shell, light work surfaces and one deep-green action color.
- Lexend headings with readable Source Sans 3 controls and content.
- Aligned appointment rows with explicit time-zone names.
- Flat containers, clear boundaries and state-driven motion.

## Colors

### Primary

Deep care green marks primary actions, meaningful availability and active selections. Its deeper companion is the hover state; pale ink remains readable on the filled action. Focus has its own green token and switches to shell ink on dark navigation.

### Neutral

Forest shell and its lighter selected surface establish navigation. Pale paper, secondary paper and green-tinted paper separate the document ground, quiet feedback and current-booking summaries. Near-white surfaces hold forms. Green-black ink, secondary ink and muted text distinguish information hierarchy; rule and input-edge tokens keep dividers quieter than interactive boundaries.

### Semantic states

Success, error and information pair foreground and background tokens. State text always carries the meaning; color is additional evidence. No independent secondary brand accent is implemented.

**The State Has Words Rule.** Confirmation, failure and selection remain understandable without color.

## Typography

Lexend is the heading face; Source Sans 3 carries body text, labels, buttons and supporting information. Both are locally served variable WOFF2 fonts with Segoe UI and sans-serif fallbacks and font-display swap. License and source details live beside the fonts.

The frontmatter records the base hierarchy. Headings use one weight, balanced wrapping and modest negative tracking; body text keeps natural tracking. Supporting text is 14px, while normal text and form entry are 16px. Forms commonly use 600-weight labels at the body size; filter labels use the smaller label role. Numerals in times, summaries and appointment metadata are tabular. Explanatory copy is capped around 65–70 characters where the layout permits.

The account-screen brand statement is the deliberate larger exception: Lexend 500 at 56px with 1.1 line height, reduced to 48px below 80rem and absent on narrow account layouts. Main greetings reduce to 28px on phones; section headings reduce to 22px. The brand strapline is 12px, not the body-text baseline.

**The Reading First Rule.** Preserve complete names, dates and zone names; wrap supporting text rather than silently clipping it.

## Layout

The desktop shell retains a fixed 232px role-navigation rail. The main content container caps at 1280px including its gutters; extra desktop width increases outer space rather than stretching the reading measure. Gutters are 40px, reduced to 24px below 75rem and 16px below 40rem. The spacing steps in the frontmatter are the implemented shared scale; 20px, 32px and 48px remain named intermediate steps.

Doctor discovery uses broad ruled rows under its filters, appointments use an agenda, and settings share a two-column surface. Booking keeps the actual slot list next to a 256px guidance column; at 80rem the guidance moves below. Slot lists use two shrinkable tracks and become one track on phones. Settings stack below 60rem.

Below 60rem the rail becomes a full-width header with a keyboard-operable menu. Below 40rem filters and metadata reflow, action targets remain usable, and summary rows compact without dropping their values. Account pages use a split composition on desktop and a single form column below 60rem. These are responsive arrangements of the existing screens, not alternate products.

## Elevation & Depth

Tonal layering and rules provide depth at rest. The time-zone dropdown alone uses the menu shadow (0 12px 32px #18372e24). Navigation selection uses an inset one-pixel outline rather than elevation. Containers do not acquire ambient shadows on hover.

**The Flat Workbench Rule.** Use surface tone and dividers for work areas; reserve the floating shadow for an overlay.

## Shapes

Controls use gently curved input corners; shared work surfaces use the larger card corners recorded above. Inputs have a one-pixel edge; visible focus has a three-pixel outline and a three-pixel offset. Avatars remain circular. Dividers are one pixel and image-bearing or content grids use shrinkable tracks. Both document axes prevent incidental horizontal overflow through the base stylesheet's horizontal clip rule; responsive checks must still catch clipped content rather than treating that rule as a fix.

## Components

### Buttons and inputs

Filled primary and transparent outline buttons share a minimum 48px height, shape, typography and press response. Actual padding is recorded in the frontmatter. Primary hover deepens the green; outline hover uses tinted paper. Compact icon and text actions retain 44px targets. Inputs have a minimum 48px height, persistent labels and readable placeholders. User-invalid fields use the error edge. Disabled or pending buttons show reduced emphasis; busy forms show progress text and suppress repeated submissions.

### Navigation and statuses

Navigation is sentence case, with a 48px minimum row, SVG icons and an explicit current-page state. Hover and current selection use the lighter shell tone. Mobile expansion exposes aria-expanded and keeps links available without JavaScript. Confirmed status is compact green text without a surrounding pill; notices use a nonshrinking label beside their message. Errors are focusable alerts, success is polite status, and empty states explain what belongs in the region.

### Work surfaces and paired times

Settings occupy one near-white surface with a divider between jobs rather than nested cards. Doctor, appointment, block and history rows use rules and spacing. The two-zone slot row puts patient-local time first, doctor time and zone beneath, and a booking action beside it. The reschedule summary keeps the current booking visible before replacement selection. These are live data presentations, not decorative mockups.

### Motion

The 120ms micro duration covers press feedback; the 220ms short duration covers dropdown state. Both use the shared ease-out curve. Press translates by one pixel; the dropdown enters with a four-pixel shift and opacity. The pending spinner rotates linearly over one second. Reduced-motion mode removes press transforms, transitions, spinner rotation and dropdown animation while preserving visible state. No page-load choreography or scroll hijacking is implemented.

## Do's and Don'ts

### Do:
- Do reuse the shipped CSS tokens and the same input and button variants on every screen.
- Do keep full time-zone labels and paired appointment times readable at mobile widths.
- Do retain visible labels, immediate focus indicators and meaningful status text.
- Do use light surfaces, green-black navigation and flat ruled work areas consistently.

### Don't:
- Don't introduce a competing palette, font system or unimplemented dark theme.
- Don't replace live appointment data with invented metrics, testimonials or mock bookings.
- Don't use tracked-cap eyebrows, decorative glyph icons or nested cards.
- Don't hide content behind entrance effects or remove state feedback for reduced-motion users.
