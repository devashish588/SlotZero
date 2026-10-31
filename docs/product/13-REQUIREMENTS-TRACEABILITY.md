# SlotZero — Requirements Traceability Matrix

This matrix connects the MedaVida brief to the current implementation and verification evidence. A code path existing is not the same as a full external deployment test.

The original brief is still unavailable. Phase 4 is verified against the user's
explicit request. Latest result: **169 passed**, including all previous 108 cases.
[Phase 4 evidence](../verification/PHASE-4-VERIFICATION.md) supersedes older lifecycle, date-filter
and DST coverage statements. [Phase 3](../verification/PHASE-3-VERIFICATION.md) retains the
separate-process booking evidence; [Phase 2](../verification/PHASE-2-VERIFICATION.md) covers
broader authorization/configuration cases.

| Challenge requirement | Current implementation | Evidence / verification | Status |
|---|---|---|---|
| Doctor and patient login | `/login`, session table, role redirect | TestClient role/dashboard flow | Implemented; covered |
| Server-side role enforcement | `require_role()` on protected routes | Patient denied doctor dashboard in test | Implemented; covered |
| Patient registration | `/register`, server inserts `patient` role | Source review; route smoke test | Implemented |
| Browse/filter doctors | Patient dashboard name/specialization/date filters | Patient-local midnight/cross-zone/DST integration cases | Implemented; covered |
| Doctor working days/ranges | `/doctor/schedule`, split local intervals | Schedule parser tests | Implemented; covered |
| Durations 15/30/60 | Doctor profile duration check | Source review | Implemented |
| Blocked periods | `/doctor/blocks`, delete route | Schedule/block integration test | Implemented; covered |
| Slot must fit hours | Dynamic slot generator checks duration within one interval | Source review and schedule tests | Implemented |
| Dynamic availability | Generated from hours, blocks and confirmed appointments | Integration test verifies block/release | Implemented; covered |
| No overlapping appointments | Transaction recheck + SQLite triggers | INSERT/UPDATE overlap tests; synchronized separate-process booking race | Implemented; covered for shared local DB file |
| Exact adjacency allowed | Half-open interval predicate | Interval test | Implemented; covered |
| Cancellation within 2h rejected | Cancellation handler checks two-hour threshold | Exact/above/below two hours, including fractional second | Implemented; covered |
| Cancelled slot reusable | Cancelled status excluded from busy appointments | Integration test | Implemented; covered |
| Safe rescheduling | Validate replacement, update same row and event transactionally | Integration test verifies updated row and event | Implemented; covered |
| Failed reschedule preserves original | No update if replacement slot unavailable | Full snapshots for occupied/blocked/malformed/past/cancelled and audit-write failures | Implemented; covered |
| Duplicate request protection | Unique patient/idempotency key + retry lookup | Sequential/changed/cancelled payloads and concurrent same-key requests | Implemented; covered |
| History | `appointment_events` records actor, action, timestamps and old/new starts | Integration test event count | Implemented; covered |
| Three IANA zones | Allowed zones list and `ZoneInfo` conversion | Winter/summer conversions and authenticated demo dashboards | Implemented; all three covered |
| DST gap rejection | strict local time conversion | London/New York 2026/2027 helper and workflow tests | Implemented; covered |
| DST fold rejection | strict local time conversion | London/New York 2026/2027 rejection tests | Implemented; covered |
| Patient ↔ doctor timezone view | Patient and doctor local display, including current reschedule booking | Phase 5 four real browser contexts and Phase 4 UTC/date tests | Verified in tested Chromium/HTTP scope |
| Mobile usability | Responsive CSS and visible header sign-out | Phase 5 1440/1280/768/375px checks; wrapped time labels | Verified Chromium viewports; formal accessibility/real devices unverified |
| Useful empty/error states | Jinja templates + notice redirects | Phase 5 browser no-results/no-slots, stale conflict, lifecycle and DST notices | Verified tested workflows |
| Deployed prototype | No deployed URL in this package | Not performed here | Outstanding |
| ZIP, PDF slides, 2–3 min video, LinkedIn post | Outline/draft provided in submission pack | User must create/publish/submit | Outstanding user deliverables |

## Evidence notes

- Historical initial documentation verification was `8 passed`; latest Phase 5 is `170 passed`, plus the standalone Chromium QA script.
- A real public deployment was not performed.
- The participant brief is the reference for challenge requirements; the source code is the reference for current implementation behaviour.
- Phase 4 resolves the patient-local date-filter caveat; Phase 5 adds browser evidence. See `PHASE-5-VERIFICATION.md` for scope, remaining environment/demo-auth gates and the Phase 6 checklist.
