# Improvement Plan 04: Configuration Templates for User Experience

## Overview
This plan focuses on improving the initial user experience by providing clear configuration templates that help users get started quickly while maintaining security best practices. Rather than expanding core functionality, this plan adds documentation and example configurations to reduce setup friction.

## Problem Statement
New users face uncertainty when configuring the Homeschool project:
- Unclear which values need to be changed from defaults
- Security concerns about hardcoded credentials in example configs
- Difficulty understanding which settings are critical vs. optional
- No clear distinction between development and production configurations

## Solution
Provide two configuration templates that serve different user needs:

### 1. open_config.yaml (Development/Local Use)
- Designed for first-time users and local development
- Contains clear placeholder values with comments
- Minimal credential requirements with prominent warnings
- Development-friendly paths and settings
- Educational comments explaining each section

### 2. locked_down_config.yaml (Production/Security-Focused)
- Designed for users concerned about security and privacy
- Strong security defaults and recommendations
- Placeholders requiring deliberate credential configuration
- Guidance on securing sensitive values
- Production-ready path examples

## Implementation Details

### Template Structure
Both templates will maintain the same structure as the existing config.yaml:
- hardware
- network
- paths
- embedding
- chromadb
- sync
- jan

### open_config.yaml Features
- Clear "CHANGE_ME" placeholders with context
- Development-friendly defaults (temp directories, localhost binding)
- Verbose comments explaining purpose of each setting
- Instructions for generating secure tokens
- Example values that are obviously placeholders
- Warning headers about not using in production

### locked_down_config.yaml Features
- Security-focused comments and warnings
- Guidance on creating strong credentials
- Examples of secure path configurations
- Notes about network exposure and binding considerations
- Recommendations for credential management (env vars, secret managers)
- Hardening suggestions for each section

### Integration with Existing Workflow
- Templates placed in repository root or docs/ directory
- Updated README to reference both templates
- Clear instructions: "Copy open_config.yaml to config.yaml to get started"
- Documentation on when to use each template
- No changes to config loading logic - maintains backward compatibility

## Acceptance Criteria
1. Both template files are present and syntactically valid YAML
2. open_config.yaml enables successful first-run with minimal changes
3. locked_down_config.yaml includes security best practices guidance
4. Templates are referenced in README and setup documentation
5. Existing config.yaml remains unchanged for backward compatibility
6. Both templates pass basic YAML validation

## Implementation Order
1. Create open_config.yaml template based on current config
2. Create locked_down_config.yaml with security enhancements
3. Update documentation to reference new templates
4. Verify templates work as expected through basic validation

## Dependencies
- No new code dependencies required
- Uses existing configuration loading system
- Documentation updates only

## Risk Assessment
- Low risk: Only adds documentation/files
- No impact on existing functionality
- Backward compatible with current config.yaml
- Reduces user support burden by clarifying setup process

## Success Metrics
- Reduction in configuration-related support questions
- Successful first-time setup using open_config.yaml
- Adoption of locked_down_config.yaml by security-conscious users
- Clear separation between development and production guidance