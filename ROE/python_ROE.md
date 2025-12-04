# Python ROE - Linter Requirements

## MANDATORY RUFF LINTER COMPLIANCE

ALL Python code MUST be validated with Ruff linter with ZERO errors and ZERO warnings.

### Absolute Requirements:

1. **USE Ruff linter after generating ANY code**
   - Run `ruff check .` on all generated Python files
   - Run `ruff format .` to ensure proper formatting

2. **CORRECT all warnings and errors before completing the job**
   - Address every single warning
   - Fix every single error
   - No exceptions allowed

3. **MAKE corrections immediately**
   - Do not present code with linter issues
   - Auto-fix with `ruff check --fix .` where possible
   - Manually fix issues that cannot be auto-fixed

4. **NEVER allow warnings or errors**
   - Zero tolerance policy
   - Code with linter issues is NOT production-ready
   - All deliverables MUST be 100% Ruff-compliant

### Ruff Configuration:
- All Ruff rules and configurations are defined in `pyproject.toml`
- Follow project-specific Ruff settings
- Do not disable rules without explicit justification

### Pre-Delivery Checklist:
- [ ] `ruff check .` returns zero errors
- [ ] `ruff check .` returns zero warnings
- [ ] `ruff format --check .` passes (code is formatted)
- [ ] `mypy .` passes type checking (if applicable)

### If linting fails, you MUST:
1. Fix all issues
2. Re-run linter to verify
3. Repeat until clean
4. Only then present the code

**Ruff compliance is NON-NEGOTIABLE and MANDATORY for all Python code.**

## Linter Installation

Ruff has been added to project dependencies:
- `requirements.txt` includes `ruff==0.8.4`
- `pyproject.toml` includes `ruff = "^0.8"` in dev dependencies

## Usage Commands

```bash
# Check for linting issues
ruff check .

# Auto-fix issues where possible
ruff check --fix .

# Check formatting
ruff format --check .

# Apply formatting
ruff format .

# Type checking (MyPy)
mypy .
```

## Why Ruff?

Ruff is 10-100x faster than traditional linters and implements 700+ rules from:
- Flake8 (and all its plugins)
- pylint
- pycodestyle
- pyflakes
- isort
- pydocstyle
- And 20+ more tools

It replaces the entire traditional linting stack with a single, blazingly fast tool.
