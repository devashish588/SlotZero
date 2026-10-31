# AGENTS.md — MedaVida Project

## Project authority
- The official hackathon challenge is the source of truth for requirements.
- Never invent product requirements or assume features.
- Brain, once established, is the authoritative project context.
- Respect human approval for major scope and architectural changes.

## Before implementation
- Read the applicable Brain documents, AGENTS.md, and relevant existing code.
- Understand the task before changing files.
- Inspect existing implementations and reuse them where appropriate.
- Prepare a plan for non-trivial changes.
- Identify affected files and acceptance criteria.

## Implementation
- Prefer complete vertical slices over disconnected frontend/backend development.
- Work in small, focused tasks.
- Avoid unrelated modifications.
- Avoid unnecessary dependencies and overengineering.
- Follow the approved architecture and design system.
- Do not change approved decisions silently.

## Definition of Done
A task is complete only when:
1. Implementation is finished.
2. Relevant tests have been executed.
3. Results have been reviewed.
4. Relevant errors have been addressed.
5. Git changes have been inspected.
6. Brain documentation has been updated when Brain exists.
7. Remaining limitations have been reported honestly.

## Git
- Maintain recoverable working states.
- Inspect git diff before committing.
- Commit meaningful changes after successful verification.
- Never discard user changes or rewrite history without approval.
- Never commit secrets.

## Brain
- Once the official challenge is received, establish the minimum useful Brain documentation.
- Record project status, requirements, decisions, assumptions, risks, implementation progress, tests, and unresolved issues.
- Update relevant Brain documents after every meaningful task.
- Never report Brain as updated unless the files were actually changed.

## Reporting
After each task, report:
- What changed.
- Files created or modified.
- Tests and verification performed.
- Git status.
- Brain updates.
- Remaining risks and next permitted action.
