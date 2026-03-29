Got it — and yes, I’ll do it.  
I’m currently in **read-only plan mode**, so I can’t actually write the file yet, but here is the exact markdown ready to save as:

`/.opencode/plans/plan_09_cleanup_stale_files.md`

```markdown
# Plan 09: Cleanup of Stale/Deprecated Config and Env Files

## Objective
Remove stale/deprecated files, reduce config/token drift, and align repo state with the current `python -m homeschool` workflow.

## Confirmed Decisions
- Remove stale local files (`.env`, caches, duplicate venv artifacts).
- Remove deprecated tracked files no longer used by current flow.
- Untrack `config.yaml` from git (keep local file, stop tracking it).
- Keep template/reference files used for onboarding/security guidance.

## Current State Summary
- Current runtime flow uses `config.yaml` as source of truth and passes env vars at runtime from CLI.
- `.env` is not required for normal CLI sync flow.
- `config.yaml` is currently tracked, even though `.gitignore` now ignores it.
- `homeschool/generate_compose_env.py` appears stale and unused.
- `.docker/config.yaml` appears stale since compose mounts `../config.yaml`.
- `setup.sh` is marked deprecated in-file.

## Scope

### Remove (local-only, ignored/artifacts)
- `.env`
- `.docker/.env`
- `.coverage`
- `.pytest_cache/`
- `homeschool/__pycache__/`
- `venv/` (if `.venv/` is the active env)

### Remove (tracked deprecated files)
- `homeschool/generate_compose_env.py`
- `.docker/config.yaml`
- `setup.sh`

### Keep (still useful)
- `.env.example` (optional reference for manual docker users)
- `open_config.yaml`
- `locked_down_config.yaml`
- `config.yaml` (keep local working file, but untrack from git)

## Execution Plan

## Phase 1: Safety + Inventory
1. Capture current git status and tracked candidate files.
2. Confirm local `config.yaml` stays on disk after untracking.
3. Confirm no active scripts/tools still call removed files.

## Phase 2: Local Artifact Cleanup
1. Delete local stale files/directories listed in local-only section.
2. Ensure `.gitignore` continues to ignore these paths.

## Phase 3: Repository Cleanup
1. Remove deprecated tracked files:
   - `homeschool/generate_compose_env.py`
   - `.docker/config.yaml`
   - `setup.sh`
2. Untrack `config.yaml` from git index (keep local file present).

## Phase 4: Documentation Alignment
1. Update `README.md` to:
   - clarify `config.yaml` is local and untracked
   - clarify `.env` is optional and mainly for manual compose workflows
   - remove references to deleted deprecated files/scripts
2. Keep references to `open_config.yaml` and `locked_down_config.yaml`.

## Phase 5: Validation
1. Run tests (`pytest`).
2. Run `python -m homeschool setup --no-start` (config validation path).
3. Run `python -m homeschool sync` smoke check.
4. Verify git status:
   - no accidental secret files staged
   - removed files absent
   - `config.yaml` no longer tracked

## Risks and Mitigations
- **Risk:** Accidental loss of local config.
  - **Mitigation:** Untrack, do not delete local `config.yaml`; verify file exists after untracking.
- **Risk:** Hidden dependency on deprecated script.
  - **Mitigation:** grep before deletion, update docs and references.
- **Risk:** Team confusion about `.env`.
  - **Mitigation:** explicitly document when `.env` is optional vs required.

## Acceptance Criteria
- `config.yaml` is no longer tracked by git but remains locally usable.
- Deprecated files are removed from repo.
- Local stale artifacts cleaned.
- README accurately reflects current workflow.
- Tests pass and sync still runs.

## Optional Commit Message
`chore: remove stale config artifacts and untrack local config`
```

If you want, once plan mode is lifted I can immediately create this file under `.opencode/plans/` and then execute it step-by-step.