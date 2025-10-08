"""
Pytest fixtures for performance benchmarks
"""

import pytest
import socket
import json
import struct
from typing import Dict, Any

try:
    import msgpack

    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False


class BenchmarkClient:
    """Simple client for benchmarking protocol operations"""

    def __init__(self, host: str = "127.0.0.1", port: int = 9876):
        self.host = host
        self.port = port
        self.socket = None

    def connect(self):
        """Connect to server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.socket.settimeout(30.0)

    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()
            self.socket = None

    def send_message(self, message: Dict[str, Any], use_msgpack: bool = True):
        """Send message using length-prefix protocol"""
        if use_msgpack and HAS_MSGPACK:
            data = msgpack.packb(message, use_bin_type=True)
        else:
            data = json.dumps(message).encode("utf-8")

        # Pack with length prefix
        header = struct.pack("!I", len(data))
        self.socket.sendall(header + data)

    def receive_message(self, use_msgpack: bool = True) -> Dict[str, Any]:
        """Receive message using length-prefix protocol"""
        # Read header
        header = self._recv_exact(4)
        length = struct.unpack("!I", header)[0]

        # Read message
        data = self._recv_exact(length)

        # Deserialize
        if use_msgpack and HAS_MSGPACK:
            return msgpack.unpackb(data, raw=False)
        else:
            return json.loads(data.decode("utf-8"))

    def _recv_exact(self, num_bytes: int) -> bytes:
        """Receive exactly num_bytes"""
        chunks = []
        bytes_received = 0

        while bytes_received < num_bytes:
            chunk = self.socket.recv(min(num_bytes - bytes_received, 8192))
            if not chunk:
                raise ConnectionError("Socket closed")
            chunks.append(chunk)
            bytes_received += len(chunk)

        return b"".join(chunks)

    def request(
        self, msg_type: str, data: Dict[str, Any] = None, msg_id: str = "1"
    ) -> Dict[str, Any]:
        """Send request and get response"""
        message = {"type": msg_type, "id": msg_id, "data": data or {}}

        self.send_message(message)
        return self.receive_message()


@pytest.fixture
def benchmark_client():
    """Fixture for benchmark client"""
    client = BenchmarkClient()
    yield client
    if client.socket:
        client.disconnect()


@pytest.fixture
def mock_qgis_project(monkeypatch):
    """Mock QGIS project for testing without QGIS"""

    class MockLayer:
        def __init__(self, layer_id, name, layer_type="vector"):
            self._id = layer_id
            self._name = name
            self._type = layer_type

        def id(self):
            return self._id

        def name(self):
            return self._name

        def type(self):
            return 0 if self._type == "vector" else 1

        def featureCount(self):
            return 1000

        def hasSpatialIndex(self):
            return True

    class MockProject:
        def __init__(self):
            self.layers = {
                "layer1": MockLayer("layer1", "Test Layer 1"),
                "layer2": MockLayer("layer2", "Test Layer 2"),
                "layer3": MockLayer("layer3", "Test Raster", "raster"),
            }

        def mapLayers(self):
            return self.layers

        def mapLayer(self, layer_id):
            return self.layers.get(layer_id)

    project = MockProject()
    return project


@pytest.fixture
def sample_features():
    """Generate sample feature data for testing"""
    features = []
    for i in range(1000):
        features.append(
            {
                "id": i,
                "attributes": {"name": f"Feature {i}", "value": i * 10, "category": f"Cat{i % 5}"},
                "geometry": {"type": "Point", "coordinates": [i * 0.1, i * 0.1]},
            }
        )
    return features


@pytest.fixture
def performance_results():
    """Container for collecting performance results"""
    return {"tests": [], "summary": {}}


def record_benchmark(results: dict, test_name: str, metrics: dict):
    """Helper to record benchmark results"""
    results["tests"].append({"name": test_name, "metrics": metrics})
