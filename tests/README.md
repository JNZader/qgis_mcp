# QGIS MCP Test Suite

Comprehensive test suite for QGIS MCP security improvements.

## Overview

This test suite provides **150+ test cases** covering:

- **Unit Tests**: Component-level testing
- **Integration Tests**: End-to-end workflows
- **Security Tests**: Penetration testing and fuzzing

## Test Coverage

### Unit Tests (105+ tests)

#### `test_security_sandbox.py` (30+ tests)
- Valid code execution
- Dangerous imports blocking (os, sys, subprocess, etc.)
- Dangerous function blocking (eval, exec, compile, etc.)
- Dangerous attribute blocking (__builtins__, __globals__, etc.)
- AST node whitelisting
- Code length limits
- Timeout enforcement
- Namespace isolation
- Bypass attempt prevention

#### `test_security_auth.py` (25+ tests)
- Token generation (cryptographically secure)
- Token verification (constant-time comparison)
- Token storage encryption
- Keyring integration
- Authentication tracking
- Session management
- Multi-client authentication
- Token lifecycle

#### `test_security_paths.py` (30+ tests)
- Path traversal attacks (.., ../, encoded variations)
- Symlink attacks
- UNC path attacks (Windows)
- URL encoding bypasses
- Unicode normalization bypasses
- Null byte injection
- Windows alternate data streams
- Dangerous file extensions
- Allowed directory restrictions
- Permission checks

#### `test_security_ratelimit.py` (20+ tests)
- Basic rate limiting
- Different operation types (auth, expensive, normal, cheap)
- Time window enforcement
- Exponential backoff
- Failed authentication tracking
- Lockout mechanisms
- Client isolation
- Cleanup mechanisms
- Thread safety

#### `test_protocol.py` (20+ tests)
- Message serialization/deserialization (JSON & MessagePack)
- Length-prefix framing
- JSON Schema validation
- Message size limits
- Buffered protocol
- Socket communication
- Error handling

#### `test_tls.py` (10+ tests)
- Certificate generation (RSA 4096-bit)
- Certificate validation
- TLS context creation
- Socket wrapping
- Certificate expiration
- Secure cipher configuration
- Server/client modes

### Integration Tests (25+ tests)

#### `test_auth_flow.py` (15+ tests)
- Complete authentication workflow
- Token lifecycle
- Multi-client authentication
- Authentication persistence
- Failed authentication handling
- Rate limiting during auth
- Session management

#### `test_server_client.py` (15+ tests)
- Full request-response cycle
- Protocol integration
- Authentication integration
- Rate limiting integration
- Error handling
- Connection management
- Concurrent clients

#### `test_performance.py` (15+ tests - benchmarks)
- Message throughput (10k+ ops/sec target)
- Serialization performance
- Rate limiter performance
- Path validation performance
- Code sandbox performance
- Memory efficiency
- Concurrent operations

### Security Tests (25+ tests)

#### `test_penetration.py` (15+ tests)
- Code injection attacks
- Path traversal attacks
- Authentication bypass attempts
- Rate limiting bypass attempts
- Buffer overflow attacks
- Protocol manipulation
- Timing attacks
- DoS resistance

#### `test_fuzzing.py` (10+ tests)
- Random input fuzzing
- Boundary value testing
- Type confusion
- Special character injection
- Integer overflow/underflow
- Combined attack vectors

## Running Tests

### Install Dependencies

```bash
pip install pytest pytest-cov pytest-timeout
pip install -r requirements-secure.txt
```

### Run All Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=qgis_mcp_plugin --cov-report=html --cov-report=term

# Specific category
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/security/ -v
```

### Run Specific Test Files

```bash
# Sandbox tests
pytest tests/unit/test_security_sandbox.py -v

# Authentication tests
pytest tests/unit/test_security_auth.py -v

# Path validation tests
pytest tests/unit/test_security_paths.py -v

# Penetration tests
pytest tests/security/test_penetration.py -v
```

### Test Markers

```bash
# Run only security tests
pytest -m security -v

# Run only integration tests
pytest -m integration -v

# Skip slow tests
pytest -m "not slow" -v

# Run only slow tests (benchmarks)
pytest -m slow -v
```

### Coverage Target

**Target: 85%+ code coverage**

```bash
# Generate coverage report
pytest tests/ --cov=qgis_mcp_plugin --cov-report=html

# Open coverage report
# Windows: start htmlcov/index.html
# Linux/Mac: xdg-open htmlcov/index.html
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── __init__.py
│
├── unit/                    # Unit tests (105+ tests)
│   ├── __init__.py
│   ├── test_security_sandbox.py      # 30+ tests
│   ├── test_security_auth.py         # 25+ tests
│   ├── test_security_paths.py        # 30+ tests
│   ├── test_security_ratelimit.py    # 20+ tests
│   ├── test_protocol.py              # 20+ tests
│   └── test_tls.py                   # 10+ tests
│
├── integration/             # Integration tests (25+ tests)
│   ├── __init__.py
│   ├── test_auth_flow.py             # 15+ tests
│   ├── test_server_client.py         # 15+ tests
│   └── test_performance.py           # 15+ benchmarks
│
└── security/                # Security tests (25+ tests)
    ├── __init__.py
    ├── test_penetration.py           # 15+ tests
    └── test_fuzzing.py               # 10+ tests
```

## Fixtures (conftest.py)

### File System Fixtures
- `temp_dir`: Temporary directory
- `temp_file`: Temporary file
- `temp_gis_file`: Temporary GIS file
- `allowed_directories`: Allowed directories list

### Security Component Fixtures
- `sandbox`: Code sandbox instance
- `path_validator`: Path validator instance
- `rate_limiter`: Rate limiter instance
- `auth_manager`: Authentication manager
- `token_storage`: Token storage

### Protocol Fixtures
- `protocol_handler`: Protocol handler (JSON)
- `buffered_protocol`: Buffered protocol handler
- `msgpack_protocol`: MessagePack protocol handler

### Network Fixtures
- `socket_pair`: Connected socket pair
- `free_port`: Free port number
- `tls_handler`: TLS handler
- `tls_socket_pair`: TLS-wrapped socket pair

### Test Data Fixtures
- `valid_python_code`: Safe Python code samples
- `malicious_python_codes`: Malicious code samples
- `path_traversal_attempts`: Path traversal attack samples
- `dangerous_file_paths`: Dangerous file path samples
- `safe_gis_paths`: Safe GIS file paths
- `valid_messages`: Valid protocol messages
- `invalid_messages`: Invalid protocol messages

### Utility Fixtures
- `performance_timer`: Performance measurement timer
- `assert_secure_timing`: Timing attack resistance checker
- `mock_qgis`: Mock QGIS environment

## Key Security Tests

### 1. Code Injection Prevention
- ✅ AST-based whitelist approach
- ✅ Blocks eval, exec, compile, __import__
- ✅ Blocks dangerous attributes (__builtins__, __globals__, etc.)
- ✅ Prevents import of unauthorized modules
- ✅ Namespace isolation

### 2. Path Traversal Prevention
- ✅ Blocks .. and encoded variants
- ✅ Resolves symlinks
- ✅ Validates against allowed directories
- ✅ Blocks UNC paths (Windows)
- ✅ Blocks alternate data streams (Windows)

### 3. Authentication Security
- ✅ Cryptographically secure tokens (secrets.token_urlsafe)
- ✅ Constant-time comparison (timing attack resistance)
- ✅ Token encryption at rest (Fernet)
- ✅ Failed attempt tracking
- ✅ Exponential backoff lockout

### 4. Rate Limiting
- ✅ Tiered limits by operation type
- ✅ Per-client tracking
- ✅ Lockout after failed auth attempts
- ✅ Thread-safe implementation
- ✅ Automatic cleanup

### 5. Protocol Security
- ✅ Length-prefix framing (prevents buffer overflow)
- ✅ JSON Schema validation
- ✅ Message size limits (10MB)
- ✅ Type validation
- ✅ No information disclosure in errors

### 6. TLS/SSL
- ✅ RSA 4096-bit certificates
- ✅ TLS 1.2+ minimum
- ✅ Secure cipher configuration
- ✅ Certificate expiration handling

## Continuous Integration

Add to your CI/CD pipeline:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - run: pip install -r requirements-secure.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/ --cov=qgis_mcp_plugin --cov-report=xml
      - uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

## Troubleshooting

### QGIS Not Available
Tests requiring QGIS will be automatically skipped. Mock QGIS fixtures are provided for most tests.

### PyOpenSSL Not Available
TLS tests will be skipped if PyOpenSSL is not installed:
```bash
pip install pyOpenSSL
```

### MessagePack Not Available
MessagePack tests will be skipped if not installed:
```bash
pip install msgpack
```

### Slow Tests Timeout
Increase timeout for slow tests:
```bash
pytest tests/ --timeout=300  # 5 minutes
```

## Test Statistics

- **Total Tests**: 155+
- **Unit Tests**: 105+
- **Integration Tests**: 25+
- **Security Tests**: 25+
- **Target Coverage**: 85%+
- **Execution Time**: ~30-60 seconds (fast tests), ~2-5 minutes (all tests including slow)

## Contributing

When adding new features:

1. Write tests first (TDD)
2. Ensure all existing tests pass
3. Maintain 85%+ coverage
4. Add integration tests for workflows
5. Add security tests for attack vectors
6. Update this README

## License

Same as QGIS MCP project.
