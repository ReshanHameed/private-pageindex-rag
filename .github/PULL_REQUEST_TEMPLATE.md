## Description
Briefly describe what this PR solves, what was changed, and the rationale.

## Linked Issue
Closes # (issue number)

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Checklist
Please verify the following guidelines are met before submitting:

- [ ] **Privacy Guarantees**: Changes do not call external APIs, vector databases, or hosted inference providers. All data remains local.
- [ ] **Backend Tests**: All existing backend tests pass. If code logic changed, new unit/integration tests are included.
    ```bash
    python -m pytest -v
    ```
- [ ] **Frontend Quality**:
    - [ ] No TypeScript compilation issues: `npx tsc --noEmit` inside `frontend/` passes.
    - [ ] Linter reports zero errors: `npm run lint` passes.
    - [ ] Compilation succeeds: `npm run build` succeeds.
- [ ] **Compatibility**: Verified functionality on both PowerShell and bash environments.
- [ ] **Documentation**: `docs/STRUCTURE.md` or other documentation files updated if this PR changes project file structure or adds features.
- [ ] **Agent Handoff**: `docs/AGENT_MEMORY.md` updated with date, changes, files, and verification results if you are an AI developer agent.
