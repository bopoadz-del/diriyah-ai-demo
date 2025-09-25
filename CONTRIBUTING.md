# Contributing to Diriyah Brain AI

Thank you for your interest in contributing!

## Development Setup
1. Clone the repo and install dependencies:
   ```bash
   cp .env.example .env
   make up
   ```

2. Run tests:
   ```bash
   make test
   ```

3. Run pre-commit checks before pushing:
   ```bash
   pre-commit install
   pre-commit run --all-files
   ```

## Pull Requests
- Fork the repository and create a feature branch.
- Ensure all tests pass and code is linted.
- Submit a PR with a clear description of your changes.
