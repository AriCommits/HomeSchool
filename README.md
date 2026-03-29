# Homeschool

Homeschool is a local-first study workflow that turns Markdown notes into flashcards and exports Anki packages (`.apkg`) for manual import.

## Overview

Homeschool scans your vault, extracts `question::answer` cards, stores semantic data in ChromaDB, and builds Anki packages you import yourself.

- Local-first processing by default
- Manual sync and export control
- Multi-database sync targets
- APKG export instead of live AnkiConnect upload

## Key Features

- **Manual Sync**: Run sync only when you want updates
- **APKG Export**: Writes timestamped `.apkg` files for Anki `File -> Import`
- **Database Scoping**: Sync a specific configured database with `--database`
- **Force Regeneration**: Rebuild all card embeddings with `--force-regen`
- **Path Safety**: Canonical vault-path containment checks for sync boundaries
- **Secure Defaults**: Placeholder tokens in tracked configs and hardened Docker settings

## Requirements

- Python 3.11+
- Docker with Docker Compose
- Anki desktop app (for manual package import)

## Quick Start

### 1) Initialize config

```bash
python -m homeschool init
```

This creates a `config.yaml` template in your current directory.

### 2) Configure paths and token

Edit `config.yaml` and set:

- `paths.vault`
- `paths.model_store`
- `chromadb.auth_token` (not `CHANGE_ME`)

Generate a token:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3) Run setup

```bash
python -m homeschool setup
```

### 4) Sync and export package

```bash
python -m homeschool sync
```

You will see the generated package path, then import it in Anki:

1. Open Anki
2. `File -> Import`
3. Select the generated `.apkg`

## CLI Commands

- `python -m homeschool init` create config template
- `python -m homeschool setup` interactive setup
- `python -m homeschool sync` sync and export APKG
- `python -m homeschool sync --database <name>` sync one configured database
- `python -m homeschool sync --force-regen` clear and rebuild collection data before sync
- `python -m homeschool status` check system status
- `python -m homeschool logs` show logging guidance
- `python -m homeschool reset --confirm` reset system state
- `python -m homeschool version` show version/check updates
- `python -m homeschool uninstall` uninstall workflow

## Docker Notes

- Compose file: `.docker/compose.yaml`
- Build uses project root context and `.docker/Dockerfile`
- `config.yaml` is mounted at runtime (not copied into image)
- Sync worker is hardened with read-only root filesystem, dropped capabilities, and resource limits

Start services manually if needed:

```bash
docker compose -f .docker/compose.yaml up -d chromadb
```

## Security Notes

- Keep real secrets out of tracked files (`config.yaml`, `.env`)
- Use placeholder values in committed config files
- Secret scanning is integrated in CI for tracked files
- Dependency auditing is integrated in CI for runtime requirements

## Project Structure

```text
.
|- .docker/
|- .github/
|- homeschool/
|  |- __main__.py
|  |- apkg_exporter.py
|  |- cli.py
|  |- config.py
|  |- path_security.py
|  `- sync.py
|- tests/
|- config.yaml
|- open_config.yaml
|- locked_down_config.yaml
`- requirements-dev.txt
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -r .docker/requirements.txt
python -m pytest
```

Optional checks:

```bash
detect-secrets-hook <tracked-files>
pip-audit -r .docker/requirements.txt
```

## Workflows and Plans

- Learning and local AI workflow docs: `docs/`
- Project planning and audits: `.opencode/plans/`
