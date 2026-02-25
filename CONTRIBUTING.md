# Contributing to Gemini Visual Design

## Ways to Contribute

- Report bugs via GitHub Issues
- Suggest features or improvements
- Submit pull requests
- Add prompt templates for new use cases
- Improve documentation

## Development Setup

```bash
# Clone the repo
git clone https://github.com/BeckhamLabsLLC/gemini-visual-design.git
cd gemini-visual-design

# Install with dev dependencies
pip install -e ".[dev]"

# Set your API key (needed for integration tests)
export GEMINI_API_KEY="your-key"
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_image_utils.py -v

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/
```

## Code Style

- Formatter/linter: **ruff** (configured in `pyproject.toml`)
- Line length: **100** characters
- Quote style: **double quotes**
- Import sorting: ruff's isort-compatible `I` rule
- Target Python: **3.10+**

## PR Process

1. Fork the repo and create a feature branch
2. Make your changes with tests
3. Run `pytest` and `ruff check` to verify
4. Submit a PR with a clear description of what changed and why

## Bug Reports

Include:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version and OS
- Relevant error output

## Feature Requests

Open an issue describing:
- The use case
- Proposed behavior
- Any prompt templates or tool parameters that would be needed
