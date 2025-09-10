# Kiro Agent Hooks

This directory contains agent hooks that automate development workflows in the Forkscout project.

## Hook Types

- **Code Quality Hooks**: Automated testing, linting, and formatting on code changes
- **Documentation Hooks**: Automatic documentation updates when features are added
- **Spec Validation Hooks**: Consistency checking for spec files
- **Test Automation Hooks**: Comprehensive test execution on relevant changes

## Hook Configuration

Each hook is defined as a JSON configuration file that specifies:
- Trigger conditions (file patterns, events)
- Actions to execute
- Dependencies and requirements
- Success/failure criteria

## Usage

Hooks are automatically triggered by Kiro when the specified conditions are met. They can also be manually executed for testing and validation purposes.