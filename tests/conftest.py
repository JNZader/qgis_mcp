"""
Pytest configuration and shared fixtures for QGIS MCP test suite

This module provides reusable fixtures for all test modules.
"""

import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

# Add plugin to path
sys.path.insert(0, str(Path(__file__).parent.parent / "qgis_mcp_plugin"))

from protocol import BufferedProtocolHandler, ProtocolHandler
from security_improved import (
    AuthenticationManager,
    EnhancedPathValidator,
    ImprovedCodeSandbox,
    ImprovedRateLimiter,
    SecureTokenStorage,
)
from tls_handler import TLSHandler

# ============================================================================
# Mock QGIS Components
# ============================================================================


class MockQgsMessageLog:
    """Mock QGIS message log"""

    @staticmethod
    def logMessage(message, tag, level):
        print(f"[{tag}] {message}")


class MockQgis:
    """Mock QGIS constants"""

    Info = 0
    Warning = 1
    Critical = 2
    Success = 3


class MockQgsProject:
    """Mock QGIS project"""

    def __init__(self):
        self._layers = {}
        self._layer_tree_root = MockLayerTreeRoot()

    @staticmethod
    def instance():
        return _mock_project_instance

    def mapLayers(self):
        return self._layers

    def mapLayer(self, layer_id):
        return self._layers.get(layer_id)

    def addMapLayer(self, layer):
        self._layers[layer.id()] = layer
        return layer

    def layerTreeRoot(self):
        return self._layer_tree_root


class MockLayerTreeRoot:
    """Mock layer tree root"""

    def findLayer(self, layer_id):
        return MockLayerTreeNode()


class MockLayerTreeNode:
    """Mock layer tree node"""

    def isVisible(self):
        return True


class MockQgsVectorLayer:
    """Mock QGIS vector layer"""

    def __init__(self, path, name, provider):
        self._id = f"layer_{id(self)}"
        self._name = name
        self._path = path
        self._valid = True
        self._features = []
        self._fields = []
        self._spatial_index = False

    def id(self):
        return self._id

    def name(self):
        return self._name

    def isValid(self):
        return self._valid

    def type(self):
        return 0  # VectorLayer

    def featureCount(self):
        return len(self._features)

    def hasSpatialIndex(self):
        return self._spatial_index

    def fields(self):
        return self._fields


# Global mock project instance
_mock_project_instance = MockQgsProject()


# ============================================================================
# Fixtures: File System
# ============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file for testing"""
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")
    return test_file


@pytest.fixture
def temp_gis_file(temp_dir):
    """Create a temporary GIS file for testing"""
    gis_file = temp_dir / "test.geojson"
    gis_file.write_text('{"type": "FeatureCollection", "features": []}')
    return gis_file


@pytest.fixture
def allowed_directories(temp_dir):
    """List of allowed directories for path validation"""
    return [temp_dir, Path.home(), Path.cwd()]


# ============================================================================
# Fixtures: Security Components
# ============================================================================


@pytest.fixture
def sandbox():
    """Create a code sandbox instance"""
    return ImprovedCodeSandbox(max_code_length=10240, timeout_seconds=5)


@pytest.fixture
def path_validator(allowed_directories):
    """Create a path validator instance"""
    return EnhancedPathValidator(allowed_directories=allowed_directories)


@pytest.fixture
def rate_limiter():
    """Create a rate limiter instance"""
    return ImprovedRateLimiter()


@pytest.fixture
def auth_manager():
    """Create an authentication manager instance"""
    manager = AuthenticationManager()
    yield manager
    # Cleanup: delete any stored tokens
    try:
        manager.storage.delete_token()
    except:
        pass


@pytest.fixture
def token_storage():
    """Create a secure token storage instance"""
    storage = SecureTokenStorage()
    yield storage
    # Cleanup: delete any stored tokens
    try:
        storage.delete_token()
    except:
        pass


# ============================================================================
# Fixtures: Protocol Handlers
# ============================================================================


@pytest.fixture
def protocol_handler():
    """Create a protocol handler instance"""
    return ProtocolHandler(use_msgpack=False, validate_schema=True)


@pytest.fixture
def buffered_protocol():
    """Create a buffered protocol handler instance"""
    return BufferedProtocolHandler(use_msgpack=False, validate_schema=True)


@pytest.fixture
def msgpack_protocol():
    """Create a MessagePack protocol handler if available"""
    try:
        import msgpack

        return ProtocolHandler(use_msgpack=True, validate_schema=True)
    except ImportError:
        pytest.skip("msgpack not available")


# ============================================================================
# Fixtures: TLS/SSL
# ============================================================================


@pytest.fixture
def tls_handler(temp_dir):
    """Create a TLS handler instance"""
    try:
        handler = TLSHandler(cert_dir=temp_dir / "certs")
        return handler
    except ImportError:
        pytest.skip("PyOpenSSL not available")


@pytest.fixture
def tls_socket_pair(tls_handler):
    """Create a pair of connected TLS sockets"""
    # Create server socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)

    port = server_sock.getsockname()[1]

    # Create client socket in background
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect_client():
        client_sock.connect(("127.0.0.1", port))

    client_thread = threading.Thread(target=connect_client)
    client_thread.start()

    # Accept connection
    conn, addr = server_sock.accept()
    client_thread.join()

    # Wrap with TLS
    server_ssl = tls_handler.wrap_socket(conn, server_side=True)
    client_ssl = tls_handler.wrap_socket(client_sock, server_side=False)

    yield server_ssl, client_ssl

    # Cleanup
    server_ssl.close()
    client_ssl.close()
    server_sock.close()


# ============================================================================
# Fixtures: Network
# ============================================================================


@pytest.fixture
def socket_pair():
    """Create a pair of connected sockets for testing"""
    # Create server socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)

    port = server_sock.getsockname()[1]

    # Create client socket
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect in background thread
    def connect_client():
        client_sock.connect(("127.0.0.1", port))

    client_thread = threading.Thread(target=connect_client)
    client_thread.start()

    # Accept connection
    conn, addr = server_sock.accept()
    client_thread.join()

    yield conn, client_sock

    # Cleanup
    conn.close()
    client_sock.close()
    server_sock.close()


@pytest.fixture
def free_port():
    """Get a free port for testing"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


# ============================================================================
# Fixtures: Mock QGIS Environment
# ============================================================================


@pytest.fixture
def mock_qgis(monkeypatch):
    """Mock QGIS environment for testing without QGIS installation"""
    # Create mock modules
    mock_qgis_core = MagicMock()
    mock_qgis_core.QgsMessageLog = MockQgsMessageLog
    mock_qgis_core.Qgis = MockQgis
    mock_qgis_core.QgsProject = MockQgsProject
    mock_qgis_core.QgsVectorLayer = MockQgsVectorLayer

    mock_qgis_utils = MagicMock()
    mock_qgis_utils.iface = MagicMock()

    # Patch sys.modules
    monkeypatch.setitem(sys.modules, "qgis", MagicMock())
    monkeypatch.setitem(sys.modules, "qgis.core", mock_qgis_core)
    monkeypatch.setitem(sys.modules, "qgis.utils", mock_qgis_utils)

    return {"core": mock_qgis_core, "utils": mock_qgis_utils, "project": _mock_project_instance}


# ============================================================================
# Fixtures: Test Data
# ============================================================================


@pytest.fixture
def valid_python_code():
    """Sample valid Python code for testing"""
    return """
x = 1
y = 2
result = x + y
print(result)
"""


@pytest.fixture
def malicious_python_codes():
    """Sample malicious Python code for testing"""
    return [
        # Import attacks
        "import os; os.system('rm -rf /')",
        "import subprocess; subprocess.run(['ls'])",
        "__import__('os').system('whoami')",
        # Eval/exec attacks
        'eval(\'__import__("os").system("ls")\')',
        "exec('import os; os.system(\"pwd\")')",
        # File access
        "open('/etc/passwd').read()",
        "open('C:\\\\Windows\\\\System32\\\\config\\\\SAM').read()",
        # Attribute access
        "[].__class__.__bases__[0].__subclasses__()",
        "().__class__.__bases__[0].__subclasses__()[104].__init__.__globals__['sys']",
        # Function access
        "getattr(__builtins__, 'eval')('1+1')",
        "vars()['__builtins__']['exec']('import os')",
    ]


@pytest.fixture
def path_traversal_attempts():
    """Sample path traversal attempts"""
    return [
        "../../../etc/passwd",
        "..\\..\\..\\Windows\\System32",
        "./../../etc/shadow",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
        "..%252f..%252f..%252fetc%252fpasswd",  # Double URL encoded
        "....//....//....//etc/passwd",  # Double dot-slash
        "..;/..;/..;/etc/passwd",  # Semicolon bypass
    ]


@pytest.fixture
def dangerous_file_paths(temp_dir):
    """Sample dangerous file paths"""
    return [
        temp_dir / "malware.exe",
        temp_dir / "virus.dll",
        temp_dir / "script.sh",
        temp_dir / "payload.bat",
        temp_dir / "trojan.cmd",
        temp_dir / "exploit.ps1",
    ]


@pytest.fixture
def safe_gis_paths(temp_dir):
    """Sample safe GIS file paths"""
    paths = [
        temp_dir / "data.shp",
        temp_dir / "features.geojson",
        temp_dir / "layer.gpkg",
        temp_dir / "raster.tif",
    ]
    # Create the files
    for path in paths:
        path.touch()
    return paths


# ============================================================================
# Fixtures: Message Data
# ============================================================================


@pytest.fixture
def valid_messages():
    """Sample valid protocol messages"""
    return [
        {"type": "authenticate", "id": "msg_001", "data": {"token": "test_token_1234567890"}},
        {"type": "ping", "id": "msg_002"},
        {"type": "list_layers", "id": "msg_003", "data": {"offset": 0, "limit": 10}},
        {"type": "get_features", "id": "msg_004", "data": {"layer_id": "layer_123", "limit": 100}},
    ]


@pytest.fixture
def invalid_messages():
    """Sample invalid protocol messages"""
    return [
        # Missing required fields
        {"type": "ping"},  # Missing id
        {"id": "msg_001"},  # Missing type
        # Invalid field values
        {"type": "", "id": "msg_001"},  # Empty type
        {"type": "x" * 100, "id": "msg_001"},  # Type too long
        # Invalid data
        {"type": "authenticate", "id": "msg_001", "data": {}},  # Missing token
        {"type": "authenticate", "id": "msg_001", "data": {"token": "short"}},  # Token too short
        # Additional properties
        {"type": "ping", "id": "msg_001", "extra": "not_allowed"},
        # Wrong types
        {"type": 123, "id": "msg_001"},  # Type not string
        {"type": "ping", "id": ["not", "string"]},  # ID wrong type
    ]


# ============================================================================
# Fixtures: Performance
# ============================================================================


@pytest.fixture
def performance_timer():
    """Timer for performance measurements"""

    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None

        def start(self):
            self.start_time = time.perf_counter()

        def stop(self):
            if self.start_time:
                self.elapsed = time.perf_counter() - self.start_time
                return self.elapsed
            return None

        def __enter__(self):
            self.start()
            return self

        def __exit__(self, *args):
            self.stop()

    return Timer()


# ============================================================================
# Utility Functions
# ============================================================================


@pytest.fixture
def assert_secure_timing():
    """Fixture to assert constant-time operations (timing attack resistance)"""

    def _assert(func1, func2, max_ratio=2.0, iterations=100):
        """
        Assert that two functions have similar execution times

        Args:
            func1: First function to test
            func2: Second function to test
            max_ratio: Maximum allowed ratio between times
            iterations: Number of iterations to run
        """
        # Warmup
        for _ in range(10):
            func1()
            func2()

        # Measure
        time1 = time.perf_counter()
        for _ in range(iterations):
            func1()
        time1 = time.perf_counter() - time1

        time2 = time.perf_counter()
        for _ in range(iterations):
            func2()
        time2 = time.perf_counter() - time2

        ratio = max(time1, time2) / min(time1, time2)
        assert ratio < max_ratio, f"Timing difference too large: {ratio:.2f}x"

    return _assert


# ============================================================================
# Hooks
# ============================================================================


def pytest_configure(config):
    """Configure pytest"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "security: marks tests as security-related")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "requires_qgis: marks tests that require QGIS installation")


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Skip tests requiring QGIS if not available
    skip_qgis = pytest.mark.skip(reason="QGIS not available")

    try:
        import qgis

        has_qgis = True
    except ImportError:
        has_qgis = False

    if not has_qgis:
        for item in items:
            if "requires_qgis" in item.keywords:
                item.add_marker(skip_qgis)
