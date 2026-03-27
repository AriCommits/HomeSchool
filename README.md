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

### 1. Configuration
Choose one of the configuration templates and copy it to `config.yaml`:
```bash
# For development/local use:
cp open_config.yaml config.yaml

# OR for production/security-focused use:
cp locked_down_config.yaml config.yaml
```

Then edit `config.yaml` to set:
- `paths.vault`: Path to your Obsidian vault
- `paths.model_store`: Directory containing your .gguf model files  
- `chromadb.auth_token`: Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`

### 2. Start Required Services
```bash
# Start Jan AI (load your preferred model)
# Start AnythingLLM Desktop (optional, for RAG)

# Start Homeschool services
cd .docker
docker compose up -d chromadb
```

### 3. Process Your Notes
```bash
# From project root
python -m homeschool sync
```

### 4. Review Results
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