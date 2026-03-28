# Plan 08: Project Review, Risk Assessment, and Remediation Roadmap

## Objective
Perform a practical hardening pass across the Homeschool project by prioritizing high-impact security vulnerabilities, reliability flaws, and maintainability issues discovered during review.

## Scope Reviewed
- Runtime code in `homeschool/`
- Docker runtime in `.docker/`
- Local configuration and templates (`config.yaml`, `.env.example`, `open_config.yaml`, `locked_down_config.yaml`)
- Supporting operational files (`.gitignore`, requirements)

## Executive Assessment
Current posture: **medium-high risk** for local development environments and **high risk** if reused as-is in shared machines or production-like setups.

Primary reasons:
- Secret handling is unsafe in repository and container build flow.
- Path containment checks are present but rely on string prefix checks that are bypass-prone.
- Docker/runtime security controls are partially implemented but inconsistent.
- There is duplicated code under `.docker/homeschool/` and `homeschool/`, increasing drift and patch inconsistency risk.

## Findings and Priority

### P0 (Fix Immediately)
1. **Credential leakage risk in tracked config files**
   - Evidence: `config.yaml` contains a real-looking `chromadb.auth_token`.
   - Risk: token compromise, unauthorized data access.
   - Action:
     - Rotate token immediately.
     - Replace real values in repo-tracked config with placeholders.
     - Add secret scanning in CI.

2. **Container image may bake secrets at build time**
   - Evidence: `.docker/Dockerfile` contains `COPY config.yaml .`.
   - Risk: secrets persist in image layers, cache, and registry.
   - Action:
     - Remove `COPY config.yaml .` from image build.
     - Mount config at runtime only.
     - Add `.dockerignore` and ensure `config.yaml`, `.env`, and local data are excluded from build context.

3. **Path traversal guard uses string prefix checks**
   - Evidence: `homeschool/sync.py`, `homeschool/media_handler.py` use `str(path).startswith(...)` logic.
   - Risk: bypass via path-prefix collisions (for example `/vault` vs `/vault_evil`).
   - Action:
     - Replace with canonical path checks using `Path.resolve()` + `Path.is_relative_to()` (or safe equivalent for older Python).
     - Centralize helper function for containment checks.
     - Add regression tests for traversal and prefix-collision cases.

4. **Direct AnkiConnect upload should be replaced with offline package export**
   - Evidence: current flow depends on runtime API calls to Anki via `homeschool/anki_connect.py`.
   - Risk: larger attack surface (local API exposure, transport assumptions, plugin behavior drift).
   - Action:
     - Replace direct upload with generation of `.apkg` output files.
     - Require manual import into Anki by the user.
     - Validate package content (filenames, media types, size limits) before export.

### P1 (Next Sprint)
5. **Runtime/code duplication across `homeschool/` and `.docker/homeschool/`**
   - Risk: security fixes applied in one tree but not the other.
   - Action:
     - Move to single source package build path.
     - Eliminate mirrored code directory in `.docker/homeschool/`.
     - Add CI check that prevents duplicate runtime modules.

6. **Weak repository hygiene for sensitive/local artifacts**
   - Evidence: `.gitignore` currently minimal.
   - Risk: accidental commits of `.env`, `config.yaml`, `*.pyc`, coverage files, local DB/manifests.
   - Action:
     - Expand `.gitignore` for Python, dotenv, local config, build/test artifacts.
     - Introduce pre-commit hooks (`detect-secrets`, `ruff`, `pytest` smoke).

7. **Docker hardening partially ineffective / inconsistent**
   - Evidence: compose uses `deploy.resources` (ignored in non-Swarm), and healthcheck Python snippet references `sys.exit` without `import sys`.
   - Risk: false health status, unreliable resource controls.
   - Action:
     - Fix healthcheck command correctness.
     - Use Compose-compatible resource settings where applicable.
     - Add `read_only`, `tmpfs`, explicit `user`, and strict mount strategy where feasible.

8. **Migration risk during AnkiConnect deprecation**
   - Evidence: existing workflow and docs assume live AnkiConnect integration.
   - Risk: broken user workflows and inconsistent card/media behavior during transition.
   - Action:
     - Add a compatibility phase: keep legacy mode behind explicit opt-in.
     - Make `.apkg` export the default path for sync outputs.
     - Update docs and CLI UX with clear manual import instructions.

### P2 (Stabilization and Quality)
9. **Config and module design issues reduce reliability**
   - Evidence examples:
     - `homeschool/transaction.py` loads config at import time.
     - `homeschool/deduplication.py` uses object access pattern that can fail (`.get` on non-dict config object).
     - `--force-regen` CLI flag is defined but not wired into sync behavior.
   - Risk: runtime failures, hard-to-test side effects, feature drift.
   - Action:
     - Refactor to lazy config loading and dependency injection.
     - Fix dedup config access and add unit tests.
     - Implement or remove `--force-regen` until supported.

10. **Supply chain and dependency governance gaps**
   - Evidence: no lockfile/pinning strategy for primary runtime outside Docker image scope.
   - Risk: unpredictable builds and latent vulnerable transitive updates.
   - Action:
     - Adopt pinned dependencies for runtime/dev.
     - Add `pip-audit`/`safety` and Dependabot (or equivalent).
     - Define update cadence and security patch SLA.

## Remediation Roadmap

### Phase 1 (0-3 days): Contain Active Risk
- Rotate all exposed tokens and invalidate previous credentials.
- Remove secret-bearing config from tracked state; commit sanitized templates only.
- Update Docker build flow to stop copying `config.yaml` into images.
- Strengthen `.gitignore` and add immediate secret scan.

### Phase 2 (3-7 days): Fix Core Security Controls
- Replace all path containment checks with canonical safe helper.
- Implement `.apkg` export pipeline and validate package payload limits.
- Fix compose healthcheck and validate container hardening options.
- Add tests for traversal, symlink, and package-validation scenarios.

### Phase 3 (1-2 weeks): Reliability + Architecture
- Remove runtime code duplication between host and Docker trees.
- Refactor config lifecycle to avoid import-time side effects.
- Fix deduplication config access and sync flag wiring (`--force-regen`).
- Expand CI to include security and regression checks.

### Phase 4 (2-4 weeks): Operational Maturity
- Add dependency vulnerability scanning and update workflow.
- Define secure deployment profile (local-only vs remote-accessed).
- Add lightweight security runbook (token rotation, incident response, backups, validation steps).

## Implementation Backlog (Actionable)

1. Secret rotation + repo cleanup (P0)
2. Dockerfile/config handling hardening (P0)
3. Unified safe path utility + test coverage (P0)
4. Replace AnkiConnect sync with `.apkg` export + validation (P0)
5. Remove duplicate runtime trees (`.docker/homeschool`) (P1)
6. `.gitignore` + pre-commit security hooks (P1)
7. Compose health/resource/hardening fixes (P1)
8. Transaction/dedup/refactor reliability fixes (P2)
9. Dependency pinning + security scans in CI (P2)

## APKG Implementation Details

- **Default sync artifact**
  - `python -m homeschool sync` writes an Anki package (`.apkg`) to a local export directory.
  - Users import the package manually in Anki (`File -> Import`).

- **CLI/UX behavior**
  - Print the absolute package path and import instructions at the end of sync.
  - Keep any AnkiConnect/live-sync path as explicit legacy opt-in only during migration.

- **Exporter design**
  - Add `homeschool/apkg_exporter.py` with a small API:
    - `sanitize_media_filename(name)`
    - `validate_media_file(path)`
    - `export_apkg(cards, output_path, deck_name, media_files)`
  - Use `genanki` for package creation; fail with clear install guidance if unavailable.

- **Validation constraints**
  - Media filename must be basename-only (no separators, no traversal, normalized characters).
  - Allowlisted extensions only (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`, `.mp3`, `.wav`).
  - Per-file size limit and total package size limit enforced before build.

- **Deck/model strategy**
  - Start with deterministic Basic model (Front/Back) and stable model/deck IDs.
  - Map frontmatter deck if present; otherwise use database-scoped default deck.

- **Test coverage**
  - Unit tests for media filename sanitization and size/extension validation.
  - Integration test for sync output producing `.apkg` and user-facing path instructions.

## Acceptance Criteria
- No real credentials exist in tracked files.
- `docker build` output does not contain runtime secrets or host config.
- Path traversal and symlink-escape test suite passes.
- Exported `.apkg` rejects unsafe media entries and oversized payloads.
- Single canonical runtime source is used by both local and container execution.
- CI fails on secret leaks, known vulnerable dependencies, and critical security test regressions.

## Suggested Validation Commands
```bash
# tests
python -m pytest

# dependency/security
pip-audit

# optional secret scan
detect-secrets scan --all-files
```

## Notes
- This plan intentionally prioritizes controls that reduce blast radius quickly (secret handling, path safety, build hygiene) before broader refactors.
