# Plan: CLI Integration for Setup & Uninstall

## Overview
Convert the bash setup.sh to Python CLI commands and add a new uninstall command with flexible removal options. Implement shell completions and version/auto-update features.

## Files to Create/Modify

### New Files
1. `homeschool/cli_helpers.py` - All helper functions using pathlib
2. `completions/bash/homeschool` - Bash completion script
3. `completions/zsh/_homeschool` - Zsh completion function
4. `completions/powershell/homeschool.ps1` - PowerShell completion

### Modified Files
1. `homeschool/cli.py` - Add setup, uninstall, version, completions commands
2. `homeschool/config.py` - Change manifest path from `.sovereign_brain` to `.homeschool`
3. `homeschool/note_tracker.py` - Update hardcoded paths
4. `.docker/homeschool/config.py` - Update manifest path
5. `.docker/homeschool/note_tracker.py` - Update hardcoded paths
6. `README.md` - Update Quick Start section
7. `setup.sh` - Add deprecation notice

## Implementation Order

### Phase 1: Manifest Path Changes
- Update DEFAULT_MANIFEST_DIR in config.py to Path.home() / ".homeschool"
- Update hardcoded paths in note_tracker.py
- Update .docker/homeschool/* files
- Update comments in config.yaml files

### Phase 2: Helper Functions
- Create cli_helpers.py with all pathlib-based helper functions
- Include Docker operations, user interaction, config management, uninstall operations

### Phase 3: CLI Commands
- Update cli.py with new subcommands: setup, uninstall, version, completions
- Update main() function to register new subparsers

### Phase 4: Shell Completions
- Create completion scripts for bash, zsh, and powershell

### Phase 5: Documentation
- Update README.md Quick Start section
- Deprecate setup.sh

### Phase 6: Testing
- Verify all new commands work correctly
- Test uninstall options
- Verify manifest directory uses .homeschool

## Detailed Command Specifications

### setup command
```
python -m homeschool setup [--non-interactive] [--no-start]
```

### uninstall command
```
python -m homeschool uninstall [--confirm LEVEL] [--keep-data] [--remove-repo] [--remove-git]
```

### version command
```
python -m homeschool version
```

### completions command
```
python -m homeschool completions <shell>
```

## Testing Checklist

- [ ] Docker detection in init command
- [ ] Interactive setup with path validation
- [ ] Non-interactive setup mode
- [ ] Skip to editor option
- [ ] Version command with update checking
- [ ] Soft uninstall (--confirm 1)
- [ ] Full uninstall (--confirm 2) with token export
- [ ] Complete uninstall (--confirm 3 --remove-repo)
- [ ] Shell completion installation
- [ ] Manifest directory correctly uses ~/.homeschool