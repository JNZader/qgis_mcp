# Contributing to QGIS MCP

Thank you for your interest in contributing! This guide will help you get started.

---

## How Can I Contribute?

### 1. Reporting Bugs

**Before submitting:**
- Check existing [Issues](https://github.com/your-username/qgis_mcp/issues)
- Try the latest version
- Read [Troubleshooting](docs/troubleshooting.md)

**When submitting:**
- Use the bug report template
- Include:
  - QGIS version
  - Python version
  - Operating system
  - Steps to reproduce
  - Expected vs actual behavior
  - Error messages/logs

### 2. Suggesting Features

**Before suggesting:**
- Check [Discussions](https://github.com/your-username/qgis_mcp/discussions)
- Review roadmap (if available)

**When suggesting:**
- Use the feature request template
- Explain the use case
- Describe proposed solution
- Consider alternatives

### 3. Contributing Code

**Process:**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

---

## Development Setup

### Prerequisites

- Python 3.7+
- QGIS 3.10+
- Git

### Setup Steps

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/qgis_mcp.git
cd qgis_mcp

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 3. Install development dependencies
pip install -r requirements-dev.txt

# 4. Install pre-commit hooks
pre-commit install

# 5. Run tests
pytest tests/
```

---

## Code Standards

### Python Style

We use:
- **Black** for code formatting
- **Flake8** for linting
- **Mypy** for type checking

**Before committing:**

```bash
# Format code
black qgis_mcp_plugin/ src/ tests/

# Check linting
flake8 qgis_mcp_plugin/ src/ tests/

# Check types
mypy qgis_mcp_plugin/ src/ --strict
```

**Or use make:**

```bash
make format
make lint
make typecheck
make quality  # All of the above
```

### Code Guidelines

1. **Follow PEP 8**
   - Line length: 100 characters
   - Use type hints
   - Document functions/classes

2. **Write tests**
   - Unit tests for new functions
   - Integration tests for workflows
   - Aim for >80% coverage

3. **Document your code**
   - Docstrings for public APIs
   - Comments for complex logic
   - Update relevant docs/

4. **Keep commits clean**
   - One logical change per commit
   - Clear commit messages
   - Reference issues (#123)

### Example

```python
def calculate_buffer_distance(
    layer_id: str,
    distance: float,
    units: str = "meters"
) -> float:
    """
    Calculate buffer distance in layer's CRS units.

    Args:
        layer_id: Layer ID to buffer
        distance: Buffer distance
        units: Distance units ("meters", "feet", "degrees")

    Returns:
        Buffer distance in layer CRS units

    Raises:
        ValueError: If units not supported
        LayerNotFoundError: If layer doesn't exist

    Example:
        >>> calc_buffer_distance("layer_1", 1000, "meters")
        1000.0
    """
    # Implementation
    pass
```

---

## Testing

### Running Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/unit/test_security_sandbox.py

# Specific test
pytest tests/unit/test_security_sandbox.py::test_allowed_operations

# With coverage
pytest tests/ --cov --cov-report=html

# Watch mode (re-run on changes)
pytest-watch
```

### Writing Tests

**Test structure:**

```python
import pytest
from qgis_mcp_plugin.security_improved import ImprovedCodeSandbox

def test_sandbox_allows_safe_code():
    """Test that sandbox allows safe QGIS operations"""
    sandbox = ImprovedCodeSandbox()

    code = """
    from qgis.core import QgsProject
    layers = QgsProject.instance().mapLayers()
    result = len(layers)
    """

    # Should not raise
    sandbox.validate_code(code)

def test_sandbox_blocks_dangerous_code():
    """Test that sandbox blocks dangerous operations"""
    sandbox = ImprovedCodeSandbox()

    code = """
    import os
    os.system('rm -rf /')  # Dangerous!
    """

    with pytest.raises(SecurityException):
        sandbox.validate_code(code)
```

**Coverage requirements:**
- Overall: ≥80%
- New code: ≥90%
- Security code: 100%

---

## Pull Request Process

### 1. Before Submitting

- [ ] Tests pass (`pytest tests/`)
- [ ] Code formatted (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make typecheck`)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)

### 2. Submitting

**Title format:**
```
[Type] Short description

Examples:
[Feature] Add support for WFS layers
[Fix] Resolve authentication token expiry issue
[Docs] Update installation guide
[Refactor] Simplify protocol handling
[Test] Add integration tests for geoprocessing
```

**Description template:**

```markdown
## Description
Brief description of changes

## Motivation
Why is this change needed?

## Changes
- Change 1
- Change 2

## Testing
How was this tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Passes CI checks
```

### 3. Review Process

1. **Automated checks** run (CI/CD)
2. **Code review** by maintainers
3. **Feedback addressed**
4. **Approved and merged**

**Review criteria:**
- Functionality correct
- Tests adequate
- Code quality high
- Documentation complete
- Security implications considered

---

## Commit Messages

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code refactoring
- `test`: Add/update tests
- `chore`: Maintenance

### Examples

**Good:**

```
feat(server): Add async operation support

Implements async execution for long-running operations
using QThread. Includes progress monitoring and
cancellation support.

Closes #123
```

```
fix(auth): Resolve token expiry issue

Tokens were expiring after 24 hours instead of 30 days.
Fixed timestamp calculation in token validation.

Fixes #456
```

**Bad:**

```
Update stuff
```

```
Fixed bug
```

---

## Documentation

### What to Document

1. **Code changes:**
   - Update docstrings
   - Add inline comments for complex logic

2. **API changes:**
   - Update `docs/api-reference.md`
   - Add examples

3. **New features:**
   - Update `docs/USER_GUIDE.md`
   - Add to `README.md` (if major)
   - Create example in `examples/`

4. **Breaking changes:**
   - Update `CHANGELOG.md`
   - Add migration guide

### Documentation Style

- **Clear and concise**
- **Examples included**
- **Code blocks tested**
- **Links to related docs**

---

## Release Process

(For maintainers)

### 1. Version Bump

```bash
# Update version in:
# - qgis_mcp_plugin/__init__.py
# - setup.py
# - pyproject.toml
```

### 2. Update CHANGELOG

```markdown
## [2.1.0] - 2025-10-15

### Added
- New feature X
- New feature Y

### Fixed
- Bug Z

### Changed
- Improvement W
```

### 3. Create Release

```bash
# Tag version
git tag -a v2.1.0 -m "Release v2.1.0"
git push origin v2.1.0

# GitHub Actions automatically:
# - Runs tests
# - Builds distributions
# - Creates GitHub release
# - Publishes to PyPI
```

---

## Community

### Code of Conduct

Be respectful and inclusive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

**Expected behavior:**
- Be welcoming and friendly
- Be patient and respectful
- Accept constructive criticism
- Focus on what's best for the community

**Unacceptable behavior:**
- Harassment or discrimination
- Trolling or insulting comments
- Public or private harassment
- Publishing others' private information

### Communication

- **GitHub Issues:** Bug reports, feature requests
- **GitHub Discussions:** Questions, ideas, general discussion
- **Pull Requests:** Code contributions

---

## Questions?

- **General questions:** GitHub Discussions
- **Bug reports:** GitHub Issues
- **Security issues:** security@your-domain.com (private)

---

**Thank you for contributing to QGIS MCP!** 🎉
