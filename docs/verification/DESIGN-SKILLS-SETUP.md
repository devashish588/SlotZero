# Design skill installation — 2026-11-01

Installed project-local Codex tooling using the user-requested commands:

- `npx --yes ui-ux-pro-max-cli init --ai codex`
- `npx --yes impeccable install --providers=codex --scope=project`
- `npx --yes skills add nutlope/hallmark --agent codex --yes`

All three commands exited successfully after retrying outside the network-restricted sandbox. The initial sandbox attempts failed with npm DNS errors.

UI/UX Pro Max, Impeccable and Hallmark are installed under `.agents/skills/`. Impeccable also installed companion skills, its Windows engine v0.1.18 and `.codex/hooks.json`. Hallmark added its source/hash to `skills-lock.json`. Verified all three SKILL.md files and Hallmark's redesign reference exist; inspected Git changes and hook configuration. Installer output flagged Hallmark as High Risk (Gen), zero Socket alerts and Medium Risk (Snyk); no independent security audit was performed.

This task installs tooling only. The attached redesign brief remains pending; no website source, product decisions or runtime dependencies changed. Application tests and browser checks were not run. Newly installed skills should be available on the next chat turn; assistant restart may be needed for discovery. Impeccable design-context initialization is still pending.

Existing untracked presentation and video artifacts were preserved and excluded from this change.

`git diff --cached --check` reported upstream whitespace issues in installed skill files. Those vendor files were preserved as distributed; this was not a clean whitespace check.
