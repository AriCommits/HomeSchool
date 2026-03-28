# Homeschool

A personal knowledge management and learning assistant that helps you process educational notes into effective study materials using local AI tools.

## Overview

Homeschool is a privacy-focused, local-first system that transforms your class notes into:
- Anki flashcards (cloze deletion, image occlusion, multiple choice)
- Short answer review questions
- Concept summaries and extensions
- Answers to your questions

The system emphasizes manual control, privacy, and ease of use.

## Key Features

- **Manual Sync Control**: Run `python -m homeschool sync` when you want to process notes
- **Privacy-First**: All processing happens locally by default
- **Flexible AI Integration**: Works with Jan AI, AnythingLLM, and other local tools
- **Obsidian Compatible**: Designed to work with your existing note-taking workflow
- **Anki Integration**: Generates flashcards ready for import into Anki
- **Configurable**: Adjust behavior through `config.yaml`

## Configuration Templates

To help you get started, we provide two configuration templates:

1. **open_config.yaml** - For development and local use
   - Contains clear placeholders with comments
   - Development-friendly defaults
   - Copy to `config.yaml` and replace CHANGE_ME values

2. **locked_down_config.yaml** - For production and security-focused deployments
   - Security best practices and guidance
   - Strong credential requirements
   - Hardening recommendations
   - Copy to `config.yaml` and thoroughly review/adjust

See the templates in the repository root for detailed instructions.

## Quick Start

### First-Time Setup
Homeschool uses a three-step workflow:

1. **Initialize** - Create configuration template:
   ```bash
   python -m homeschool init
   ```
   This checks Docker availability and creates a template config.

2. **Configure** - Interactive setup wizard:
   ```bash
   python -m homeschool setup
   ```
   This will:
   - Guide you through configuring required paths and settings
   - Create a personalized config.yaml file
   - Launch Docker services using docker compose

3. **Sync** - Process your notes:
   ```bash
   python -m homeschool sync
   ```

You only need to run the setup wizard once. For subsequent runs, use:
```bash
python -m homeschool sync
```

### Shell Completions
Enable tab completion for your shell:
```bash
# Bash
python -m homeschool completions bash
# Add to ~/.bashrc: source ~/.bash_completions/homeschool

# Zsh  
python -m homeschool completions zsh
# Add to ~/.zshrc: fpath+=(~/.zsh_completions) && compinit

# PowerShell
python -m homeschool completions powershell
# Add to $PROFILE: . ~/Documents/PowerShell/homeschool.ps1
```

### Common Commands

| Command | Description |
|---------|-------------|
| `python -m homeschool init` | Create example configuration |
| `python -m homeschool setup` | Interactive setup wizard |
| `python -m homeschool sync` | Sync notes to Anki |
| `python -m homeschool status` | Check system status |
| `python -m homeschool logs` | View log instructions |
| `python -m homeschool reset` | Reset system (requires confirmation) |
| `python -m homeschool version` | Show version and check for updates |
| `python -m homeschool uninstall` | Uninstall Homeschool |

### Manual Configuration (Alternative)
If you prefer manual configuration:

1. Choose one of the configuration templates and copy it to `config.yaml`:
```bash
# For development/local use:
cp open_config.yaml config.yaml

# OR for production/security-focused use:
cp locked_down_config.yaml config.yaml
```

2. Edit `config.yaml` to set:
- `paths.vault`: Path to your Obsidian vault
- `paths.model_store`: Directory containing your .gguf model files  
- `chromadb.auth_token`: Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`

3. Start required services:
```bash
# Start Jan AI (load your preferred model)
# Start AnythingLLM Desktop (optional, for RAG)

# Start Homeschool services
cd .docker
docker compose up -d
```

4. Process your notes:
```bash
# From project root
python -m homeschool sync
```

5. Review results:
- Check Anki for new flashcards (requires manual confirmation)
- Review generated questions and summaries in your vault
- Process continues until you stop it

## Workflows

See the `docs/` directory for detailed workflows:
- [Learning Workflow](docs/Learning%20Workflow.md) - How to generate study materials from notes
- [Local AI Workflow](docs/Local%20AI%20Workflow.md) - Local-first AI setup for development

## Development

Homeschool is structured as a Python package. For development:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install pyyaml structlog

# Run tests
python -m pytest
```

## Contributing

See `.opencode/plans/improvement_plan.md` for planned enhancements.

## License

[Specify your license here]

## Acknowledgments

- Built with open-source tools including ChromaDB, Jan AI, and Continue
- Inspired by privacy-focused, local-first AI workflows