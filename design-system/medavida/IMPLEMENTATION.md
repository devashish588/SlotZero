> **Legacy reference:** historical Next.js / `medavida-web` specification. The current FastAPI/Jinja2 application does not implement this automatically.

# MedaVida — Auth & Dashboard Implementation Spec

> Source of truth for visual rules: `design-system/medavida/MASTER.md`
> Page overrides: `design-system/medavida/pages/auth.md`
> Stack: Next.js (App Router) + Tailwind CSS v4 + shadcn/ui. App root: `medavida-web/`

## Approved user flows

### 1. Sign in
1. `/sign-in` — email + password (paste allowed, `autocomplete="username" | "current-password"`).
2. Client validation (blur) + submit; **focusable error summary** links to invalid fields, inline field errors retained (`aria-describedby`).
3. Wrong credentials → generic error ("Invalid email or password"), non-cognitive recovery path (forgot-password link). 5 consecutive failures → 30 s lockout with live countdown.
4. Enrolled user (demo) → `/verify` (MFA OTP). Correct + MFA off → session set → `/dashboard`.

### 2. MFA verification (`/verify`)
1. 6-digit code via `input-otp`, `autocomplete="one-time-code"`, paste allowed.
2. Wrong code → inline error, up to 5 attempts, then resend period.
3. Resend with 30 s countdown (button disabled until 0).
4. Non-cognitive alternative: "Email me a login link" (demo notice).
5. Success → session → `/dashboard`.

### 3. Sign up (`/sign-up`)
1. Full name, work email, password (show/hide toggle, strength meter with `aria-live`), terms checkbox.
2. Submit → email verification `/verify?next=signup` (same OTP flow, enrols no MFA) → session → `/dashboard`.
3. Existing account → link to `/sign-in`.

### 4. Forgot password (`/forgot-password`)
1. Email → success state (aria-live) "check your inbox" always (no account enumeration).
2. Link back to sign-in.

### 5. Reset password (`/reset-password?token=…`)
1. New password + confirm, strength meter, mismatch inline error.
2. Success state → CTA to `/sign-in`.

### 6. Authenticated dashboard (`/dashboard`)
- Guarded two ways: `src/proxy.ts` (cookie fast-fail → `/sign-in`) + client session check.
- Shell: sidebar (App link semantics, ≥44 px targets), header with org + user menu (sign out), brand band with "DEMO" notice.
- Surface 1: 4 KPI stat cards. Surface 2: Patient queue panel (demo rows, status badges not color-only). Surface 3: Activity panel with empty state ("Connect your data").
- `prefers-reduced-motion` respected everywhere.

## Mock auth contract
- Session in `localStorage` + `mv_session` cookie (8 h expiry) — **demo only**; real app needs server-side sessions.
- Seeded demo user: `dr.reyes@medavida.health` / `MedaVida2026!`, MFA code `401203`.
- Never stores password; generic auth errors; no enumeration.

## Component inventory
- Auth shell (split layout, skip link, brand panel), AuthLogo
- `PasswordInput` (toggle, aria), `PasswordStrength`, `ErrorSummary`, `FieldError`, `CountdownResend`
- OTP flow (shadcn `input-otp`), KPI cards, StatusBadge, EmptyState, DashboardShell (Sidebar + Header + UserMenu)
