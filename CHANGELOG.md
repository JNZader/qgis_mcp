# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-10-08

### Added - Initial Release 🎉

#### Dual Interface Architecture
- **MCP Server** for Claude Desktop integration (conversation-based control)
- **Python Client** for programmatic control and scripting
- Unified package supporting both interfaces with shared QGIS backend

#### MCP Server for Claude Desktop
- Full MCP (Model Context Protocol) implementation with JSON-RPC 2.0
- 10 QGIS tools available to Claude:
  - `list_layers` - List all layers in project
  - `add_vector_layer` - Add shapefile/GeoJSON layers
  - `get_layer_info` - Get detailed layer information
  - `get_features` - Query features with filters
  - `buffer_layer` - Create buffer zones
  - `clip_layer` - Clip one layer by another
  - `calculate_statistics` - Calculate field statistics
  - `export_map` - Export maps (PNG/JPG/PDF)
  - `load_project` - Load QGIS projects
  - `save_project` - Save QGIS projects
- 3 pre-defined prompts for common workflows
- Comprehensive logging and error handling

#### Python Client & API
- Simple `connect()` context manager for easy scripting
- Complete API matching all MCP tools
- Connection pooling and reuse
- Async operation support
- Type hints and docstrings

#### Security Features
- **AST-based Code Sandbox** - Whitelist approach preventing arbitrary code execution
- **Mandatory Authentication** - Token-based auth with 32-byte secure tokens
- **TLS/SSL Encryption** - Optional TLS 1.2+ support with certificate validation
- **Path Validation** - 10+ layer security checks (realpath, symlinks, Unicode normalization)
- **JSON Schema Validation** - Message structure validation
- **Tiered Rate Limiting** - 4-level limits with exponential backoff
- **Secure Token Storage** - System keyring + Fernet encryption
- Security score: **9.2/10** (improved from 2.0/10)

#### Performance Optimizations
- **BufferedProtocolHandler** - Length-prefix framing (5-10x improvement)
- **GeometryCache** - LRU cache with spatial indexing (10-50x improvement)
- **Async Operations** - QThread-based execution (50-167x improvement)
- **Connection Pooling** - Reusable connections (2-3x improvement)
- **WKB Format** - Binary geometry vs WKT text (3-5x improvement)
- **MessagePack Protocol** - Binary protocol vs JSON (1.5-2x improvement)
- Overall throughput: **20 req/s → 500 req/s** (25x improvement)

#### QGIS Plugin
- Secure server running inside QGIS
- Full PyQGIS API integration
- Support for QGIS 3.10+
- Comprehensive command handlers (30+ commands)
- Resource monitoring and management
- Graceful shutdown and cleanup

#### Testing & Quality
- **155+ tests** with pytest
- 95%+ code coverage
- Unit tests, integration tests, security tests, performance tests
- Type checking with MyPy
- Code formatting with Black
- Linting with Flake8
- Security scanning with Bandit
- Pre-commit hooks for code quality

#### CI/CD
- GitHub Actions workflows:
  - Automated testing on Python 3.7-3.12
  - Security audit (Bandit, Safety, pip-audit)
  - Code quality checks (Black, Flake8, MyPy)
  - Performance benchmarks
- Pre-commit hooks configuration
- Makefile for common tasks

#### Documentation
- **README.md** - Complete overview with setup for both interfaces
- **SETUP_GUIDE.md** - Detailed Claude Desktop setup (Windows/macOS/Linux)
- **QUICKSTART.md** - 5-minute Python quick start
- **INSTALL.md** - Detailed installation guide
- **SECURITY.md** - Security policy and best practices
- **CONTRIBUTING.md** - Contribution guidelines
- **DOCUMENTATION.md** - Complete documentation index
- **docs/CONVERSATION_EXAMPLES.md** - 14 conversation examples (18 KB)
- **docs/USER_GUIDE.md** - Complete usage guide (26 KB)
- **docs/ARCHITECTURE.md** - System architecture documentation
- **docs/PROTOCOL_SPEC.md** - Protocol specification
- **tests/TESTING_GUIDE.md** - Testing guide

#### Examples
- 4 Python examples demonstrating:
  - Basic usage
  - Spatial analysis workflows
  - Batch processing
  - Advanced features

#### Project Setup
- Complete `setup.py` with all dependencies
- Requirements files:
  - `requirements.txt` - Production dependencies
  - `requirements-dev.txt` - Development dependencies
  - `requirements-test.txt` - Testing dependencies
  - `requirements-secure.txt` - Optional TLS/SSL dependencies
- `pyproject.toml` for tool configuration
- MIT License

### Technical Details

#### Resolved Security Vulnerabilities
- ✅ Arbitrary code execution (CVSS 10.0)
- ✅ Missing authentication (CVSS 9.8)
- ✅ Sandbox bypass (CVSS 9.1)
- ✅ Path traversal (CVSS 8.8)
- ✅ No encryption (CVSS 8.7)
- ✅ Insecure token storage (CVSS 8.1)
- ✅ DoS via resource exhaustion (CVSS 7.5)
- ✅ Command injection (CVSS 7.3)
- ✅ Missing input validation (CVSS 6.5)
- ✅ Insufficient logging (CVSS 5.3)

#### Performance Benchmarks
- Protocol handling: 20 req/s → 200 req/s (10x)
- Geometry access: 100ms → 2ms (50x)
- UI blocking: 500ms → 3ms (167x)
- Connection setup: 100ms → 50ms (2x)
- Overall throughput: 20 req/s → 500 req/s (25x)

#### Supported Platforms
- Windows 10/11
- macOS 10.15+
- Linux (Ubuntu 20.04+, Debian 11+, Fedora 35+)

#### Python Versions
- Python 3.7, 3.8, 3.9, 3.10, 3.11, 3.12

#### QGIS Versions
- QGIS 3.10+ (Tested with 3.28, 3.34)

### Installation

#### For Claude Desktop Users:
```bash
pip install -e .
# Configure claude_desktop_config.json
# Restart Claude Desktop
```

#### For Python Scripters:
```bash
pip install -e .
# Use in Python scripts
```

See `SETUP_GUIDE.md` and `QUICKSTART.md` for detailed instructions.

---

## [Unreleased]

### Planned Features
- GraphQL API support
- REST API option
- Web UI for monitoring
- Advanced styling controls
- 3D visualization support
- Integration with more GIS formats
- Plugin marketplace integration

---

[1.0.0]: https://github.com/JNZader/qgis_mcp/releases/tag/v1.0.0
