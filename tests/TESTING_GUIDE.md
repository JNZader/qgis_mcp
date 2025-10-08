# Testing Guide

How to run and use the QGIS MCP test suite.

---

## Quick Start

### Run All Tests

```bash
# Run all tests
pytest tests/

# With coverage
pytest tests/ --cov --cov-report=html

# View coverage report
open htmlcov/index.html  # or start htmlcov/index.html on Windows
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Security tests
pytest tests/security/

# Performance benchmarks
python tests/performance/run_all_benchmarks.py
```

---

## Test Structure

```
tests/
├── conftest.py               # Shared fixtures (30+)
├── test_quick.py             # Quick smoke test
│
├── unit/                     # Unit tests (105+ tests)
│   ├── test_security_sandbox.py     # Code sandbox tests
│   ├── test_security_auth.py        # Authentication tests
│   ├── test_security_paths.py       # Path validation tests
│   ├── test_security_ratelimit.py   # Rate limiting tests
│   ├── test_protocol.py             # Protocol tests
│   └── test_tls.py                  # TLS/SSL tests
│
├── integration/              # Integration tests (25+ tests)
│   ├── test_auth_flow.py            # Auth workflow
│   ├── test_server_client.py        # Server-client integration
│   └── test_performance.py          # Performance integration
│
├── security/                 # Security tests (25+ tests)
│   ├── test_penetration.py          # Penetration testing
│   └── test_fuzzing.py              # Fuzzing tests
│
└── performance/              # Performance benchmarks (40+)
    ├── benchmark_protocol.py        # Protocol performance
    ├── benchmark_cache.py           # Cache performance
    ├── benchmark_features.py        # Feature access
    ├── benchmark_async.py           # Async operations
    ├── benchmark_end_to_end.py      # End-to-end
    └── run_all_benchmarks.py        # Run all benchmarks
```

---

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Includes:
# - pytest
# - pytest-cov (coverage)
# - pytest-xdist (parallel)
# - pytest-timeout
# - pytest-mock
```

### Basic Usage

```bash
# Run all tests
pytest

# Run with output
pytest -v

# Run specific file
pytest tests/unit/test_security_sandbox.py

# Run specific test
pytest tests/unit/test_security_sandbox.py::test_allowed_operations

# Run with keyword filter
pytest -k "auth"  # Runs all tests with "auth" in name
```

### Advanced Usage

```bash
# Parallel execution (faster)
pytest -n auto

# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Verbose output
pytest -vv

# Only failed tests from last run
pytest --lf

# Run tests that failed, then all
pytest --ff
```

### Coverage

```bash
# Run with coverage
pytest --cov=qgis_mcp_plugin --cov=src/qgis_mcp

# HTML report
pytest --cov --cov-report=html

# Terminal report with missing lines
pytest --cov --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov --cov-fail-under=80
```

---

## Test Categories

### 1. Unit Tests (Fast, ~105 tests)

**Purpose:** Test individual components in isolation

**Run:**
```bash
pytest tests/unit/ -v
```

**Coverage:**
- Security sandbox (code validation)
- Authentication (token management)
- Path validation (security checks)
- Rate limiting (tiered limits)
- Protocol (message handling)
- TLS/SSL (encryption)

**Example test:**
```python
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
```

### 2. Integration Tests (Medium speed, ~25 tests)

**Purpose:** Test component interactions

**Run:**
```bash
pytest tests/integration/ -v
```

**Coverage:**
- Authentication flow (end-to-end)
- Server-client communication
- Performance integration

**Example test:**
```python
def test_auth_flow_complete():
    """Test complete authentication flow"""
    # Start server
    server = start_server()

    # Get token
    token = server.get_token()

    # Connect client
    client = connect(token=token)

    # Verify authenticated
    assert client.get_qgis_info()
```

### 3. Security Tests (Slow, ~25 tests)

**Purpose:** Security validation and penetration testing

**Run:**
```bash
pytest tests/security/ -v
```

**Coverage:**
- Penetration testing (attack scenarios)
- Fuzzing (random inputs)
- Vulnerability detection

**Example test:**
```python
def test_path_traversal_blocked():
    """Test that path traversal attacks are blocked"""
    validator = EnhancedPathValidator()

    malicious_paths = [
        "../../../etc/passwd",
        "..\\..\\Windows\\System32",
        "/etc/passwd",
    ]

    for path in malicious_paths:
        with pytest.raises(SecurityException):
            validator.validate_path(path)
```

### 4. Performance Benchmarks (~40 benchmarks)

**Purpose:** Measure and track performance

**Run:**
```bash
python tests/performance/run_all_benchmarks.py
```

**Coverage:**
- Protocol handling speed
- Cache performance
- Feature access speed
- Async operations
- End-to-end throughput

**Example benchmark:**
```python
def benchmark_protocol_send_receive():
    """Benchmark protocol send/receive"""
    protocol = BufferedProtocolHandler()

    start = time.time()
    for i in range(1000):
        message = {"type": "ping", "id": str(i)}
        protocol.send_message(sock, message)
        response = protocol.receive_message(sock)

    elapsed = time.time() - start
    print(f"1000 messages: {elapsed:.2f}s ({1000/elapsed:.0f} msg/s)")
```

---

## Common Test Scenarios

### Testing Authentication

```bash
# Run all auth tests
pytest -k "auth"

# Just token validation
pytest tests/unit/test_security_auth.py::test_token_validation

# Auth workflow
pytest tests/integration/test_auth_flow.py
```

### Testing Security

```bash
# All security tests
pytest tests/security/

# Code sandbox only
pytest tests/unit/test_security_sandbox.py

# Path validation
pytest tests/unit/test_security_paths.py

# Penetration tests
pytest tests/security/test_penetration.py
```

### Testing Performance

```bash
# Quick performance check
pytest tests/integration/test_performance.py

# Full benchmarks
python tests/performance/run_all_benchmarks.py

# Specific benchmark
python tests/performance/benchmark_protocol.py
```

---

## Continuous Integration

Tests run automatically on:

### Every Push/PR

```yaml
# .github/workflows/security-tests.yml
- Python 3.10, 3.11, 3.12
- Ubuntu, Windows, macOS
- All test suites
- Coverage report to Codecov
```

### Code Quality Checks

```yaml
# .github/workflows/code-quality.yml
- Black formatting
- Flake8 linting
- Mypy type checking
- Radon complexity
```

**Run locally:**
```bash
make quality  # Run all quality checks
```

---

## Writing Tests

### Test Template

```python
import pytest
from qgis_mcp_plugin.module import ClassName

def test_feature_works():
    """Test that feature works correctly"""
    # Arrange
    instance = ClassName()
    input_data = {...}

    # Act
    result = instance.method(input_data)

    # Assert
    assert result == expected_value

def test_feature_handles_error():
    """Test that feature handles errors"""
    instance = ClassName()

    with pytest.raises(ExpectedException):
        instance.method(invalid_input)
```

### Using Fixtures

```python
@pytest.fixture
def mock_server():
    """Create mock server for testing"""
    server = MockServer()
    yield server
    server.cleanup()

def test_with_fixture(mock_server):
    """Test using fixture"""
    response = mock_server.handle_request(...)
    assert response['status'] == 'success'
```

### Best Practices

1. **One assertion per test** (when possible)
2. **Clear test names** (describe what's tested)
3. **Arrange-Act-Assert** pattern
4. **Use fixtures** for setup/teardown
5. **Mock external dependencies**
6. **Test edge cases** (empty, null, max)
7. **Test error conditions**

---

## Troubleshooting Tests

### Tests Hang

**Problem:** Tests don't complete

**Solution:**
```bash
# Add timeout
pytest --timeout=10

# Find slow tests
pytest --durations=10
```

### Import Errors

**Problem:** Module not found

**Solution:**
```bash
# Install in editable mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Fixture Errors

**Problem:** Fixture not found

**Solution:**
- Check `conftest.py` is present
- Verify fixture scope
- Check fixture name spelling

### Random Failures

**Problem:** Tests fail intermittently

**Solution:**
```bash
# Run multiple times
pytest --count=10

# Find flaky tests
pytest --flake-finder --flake-runs=10
```

---

## Test Coverage Goals

```
┌──────────────────────────────────────┐
│         COVERAGE TARGETS              │
├──────────────────────────────────────┤
│  Overall:              ≥80%          │
│  Security modules:     ≥95%          │
│  Protocol handling:    ≥90%          │
│  Server code:          ≥85%          │
│  Client code:          ≥80%          │
└──────────────────────────────────────┘
```

**Current coverage: 85%+** ✅

---

## Quick Commands

```bash
# Quick smoke test
pytest tests/test_quick.py

# All tests with coverage
make test

# Just security
make test-security

# Just unit tests
make test-unit

# Code quality + tests
make all
```

---

## Next Steps

- **Run tests** - Verify everything works
- **Add tests** - When adding features
- **Check coverage** - Maintain ≥80%
- **Review failures** - Fix broken tests

---

**Need help?** See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines.
