"""
Secure QGIS MCP Client with connection pooling, automatic authentication,
TLS support, and reconnection handling.

Features:
- Thread-safe connection pooling
- Automatic authentication
- TLS/SSL support
- Automatic reconnection on failure
- Request timeout handling
- Message validation
- Token management
"""

import socket
import threading
import time
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
from queue import Queue, Empty
from contextlib import contextmanager

# Import protocol and TLS handler from plugin (should be available in Python path)
try:
    from qgis_mcp_plugin.protocol import ProtocolHandler, ProtocolException
    from qgis_mcp_plugin.tls_handler import TLSHandler
    from qgis_mcp_plugin.security_improved import SecureTokenStorage
except ImportError:
    # Fallback for standalone usage
    import sys
    plugin_path = Path(__file__).parent.parent.parent / 'qgis_mcp_plugin'
    sys.path.insert(0, str(plugin_path))
    from protocol import ProtocolHandler, ProtocolException
    from tls_handler import TLSHandler
    from security_improved import SecureTokenStorage


class ClientException(Exception):
    """Raised when client operation fails"""
    pass


class ConnectionPool:
    """Thread-safe connection pool for socket connections"""

    def __init__(
        self,
        host: str,
        port: int,
        max_connections: int = 5,
        use_tls: bool = False,
        connection_timeout: float = 10.0
    ):
        """
        Initialize connection pool

        Args:
            host: Server host
            port: Server port
            max_connections: Maximum number of pooled connections
            use_tls: Use TLS/SSL encryption
            connection_timeout: Connection timeout in seconds
        """
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.use_tls = use_tls
        self.connection_timeout = connection_timeout

        self._pool: Queue = Queue(maxsize=max_connections)
        self._active_connections = 0
        self._lock = threading.Lock()
        self._protocol = ProtocolHandler(use_msgpack=True, validate_schema=True)
        self._tls_handler = TLSHandler() if use_tls else None

    def _create_connection(self) -> socket.socket:
        """
        Create new socket connection

        Returns:
            Connected socket

        Raises:
            ClientException: If connection fails
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.connection_timeout)
            sock.connect((self.host, self.port))

            # Wrap with TLS if enabled
            if self.use_tls and self._tls_handler:
                sock = self._tls_handler.wrap_socket(
                    sock,
                    server_side=False,
                    verify_cert=False  # Self-signed certificates
                )

            return sock

        except (socket.error, OSError) as e:
            raise ClientException(f"Connection failed: {e}")

    @contextmanager
    def get_connection(self):
        """
        Get connection from pool (context manager)

        Yields:
            Socket connection

        Raises:
            ClientException: If connection cannot be acquired
        """
        conn = None
        try:
            # Try to get existing connection from pool
            try:
                conn = self._pool.get_nowait()
            except Empty:
                # Create new connection if under limit
                with self._lock:
                    if self._active_connections < self.max_connections:
                        self._active_connections += 1
                        conn = self._create_connection()
                    else:
                        # Wait for available connection
                        conn = self._pool.get(timeout=self.connection_timeout)

            # Verify connection is still alive
            if not self._is_connection_alive(conn):
                conn.close()
                conn = self._create_connection()

            yield conn

        except Exception as e:
            # Close broken connection
            if conn:
                try:
                    conn.close()
                except:
                    pass
                conn = None
            raise

        finally:
            # Return connection to pool
            if conn:
                try:
                    self._pool.put_nowait(conn)
                except:
                    # Pool is full, close connection
                    conn.close()
                    with self._lock:
                        self._active_connections -= 1

    def _is_connection_alive(self, sock: socket.socket) -> bool:
        """
        Check if connection is still alive

        Args:
            sock: Socket to check

        Returns:
            True if connection is alive
        """
        try:
            # Use MSG_PEEK to check without consuming data
            sock.setblocking(False)
            data = sock.recv(1, socket.MSG_PEEK)
            sock.setblocking(True)
            return True
        except (socket.error, OSError):
            return False

    def close_all(self) -> None:
        """Close all pooled connections"""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except:
                pass

        with self._lock:
            self._active_connections = 0


class SecureQGISMCPClient:
    """
    Secure QGIS MCP Client with connection pooling and automatic authentication

    Features:
    - Thread-safe connection pooling
    - Automatic authentication with token management
    - TLS/SSL support
    - Automatic reconnection on failures
    - Request timeout handling
    - Message validation
    """

    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 9876,
        token: Optional[str] = None,
        use_tls: bool = False,
        auto_authenticate: bool = True,
        max_connections: int = 5,
        request_timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize secure QGIS MCP client

        Args:
            host: Server host
            port: Server port
            token: Authentication token (retrieved from storage if not provided)
            use_tls: Use TLS/SSL encryption
            auto_authenticate: Automatically authenticate on first request
            max_connections: Maximum pooled connections
            request_timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.auto_authenticate = auto_authenticate
        self.request_timeout = request_timeout
        self.max_retries = max_retries

        # Token management
        self.token_storage = SecureTokenStorage()
        self.token = token
        if not self.token and auto_authenticate:
            try:
                self.token = self.token_storage.retrieve_token()
            except FileNotFoundError:
                raise ClientException(
                    "No authentication token found. "
                    "Please provide token or run server first to generate one."
                )

        # Connection pool
        self.pool = ConnectionPool(
            host=host,
            port=port,
            max_connections=max_connections,
            use_tls=use_tls,
            connection_timeout=10.0
        )

        # Protocol handler
        self.protocol = ProtocolHandler(use_msgpack=True, validate_schema=True)

        # Authentication state
        self.authenticated = False
        self._auth_lock = threading.Lock()

    def _ensure_authenticated(self, conn: socket.socket) -> None:
        """
        Ensure connection is authenticated

        Args:
            conn: Socket connection

        Raises:
            ClientException: If authentication fails
        """
        with self._auth_lock:
            if self.authenticated:
                return

            if not self.token:
                raise ClientException("No authentication token available")

            # Send authentication request
            auth_msg = {
                'type': 'authenticate',
                'id': str(uuid.uuid4()),
                'data': {'token': self.token}
            }

            try:
                self.protocol.send_message(conn, auth_msg)
                response = self.protocol.receive_message(conn, timeout=self.request_timeout)

                if not response:
                    raise ClientException("No response from server")

                if not response.get('success'):
                    error = response.get('error', 'Unknown error')
                    raise ClientException(f"Authentication failed: {error}")

                self.authenticated = True

            except (socket.error, ProtocolException) as e:
                raise ClientException(f"Authentication error: {e}")

    def send_request(
        self,
        msg_type: str,
        data: Optional[Dict[str, Any]] = None,
        skip_auth: bool = False
    ) -> Dict[str, Any]:
        """
        Send request to server with automatic retry

        Args:
            msg_type: Message type
            data: Message data
            skip_auth: Skip authentication (for authenticate command)

        Returns:
            Response data dictionary

        Raises:
            ClientException: If request fails after retries
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                with self.pool.get_connection() as conn:
                    # Authenticate if needed
                    if not skip_auth and self.auto_authenticate:
                        self._ensure_authenticated(conn)

                    # Build message
                    message = {
                        'type': msg_type,
                        'id': str(uuid.uuid4()),
                    }
                    if data:
                        message['data'] = data

                    # Send request
                    self.protocol.send_message(conn, message)

                    # Receive response
                    response = self.protocol.receive_message(conn, timeout=self.request_timeout)

                    if not response:
                        raise ClientException("No response from server")

                    if not response.get('success'):
                        error = response.get('error', 'Unknown error')
                        raise ClientException(f"Server error: {error}")

                    return response.get('data', {})

            except (socket.error, ProtocolException, ClientException) as e:
                last_error = e
                # Reset authentication state on connection error
                with self._auth_lock:
                    self.authenticated = False

                if attempt < self.max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = 0.5 * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    break

        # All retries failed
        raise ClientException(f"Request failed after {self.max_retries} attempts: {last_error}")

    def authenticate(self, token: Optional[str] = None) -> bool:
        """
        Explicitly authenticate with server

        Args:
            token: Authentication token (uses stored token if not provided)

        Returns:
            True if authentication successful

        Raises:
            ClientException: If authentication fails
        """
        if token:
            self.token = token

        with self._auth_lock:
            self.authenticated = False

        try:
            with self.pool.get_connection() as conn:
                self._ensure_authenticated(conn)
            return True
        except ClientException:
            raise

    def ping(self) -> Dict[str, Any]:
        """
        Ping server

        Returns:
            Ping response data
        """
        return self.send_request('ping')

    def list_layers(self, offset: int = 0, limit: int = 50) -> Dict[str, Any]:
        """
        List QGIS layers

        Args:
            offset: Pagination offset
            limit: Maximum number of layers

        Returns:
            Layer list with metadata
        """
        return self.send_request('list_layers', {'offset': offset, 'limit': limit})

    def get_features(
        self,
        layer_id: str,
        limit: int = 100,
        bbox: Optional[Dict[str, float]] = None,
        filter_expression: Optional[str] = None,
        attributes_only: bool = False,
        simplify_tolerance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get features from layer

        Args:
            layer_id: Layer ID
            limit: Maximum features to return
            bbox: Bounding box filter
            filter_expression: Attribute filter expression
            attributes_only: Skip geometry
            simplify_tolerance: Geometry simplification tolerance

        Returns:
            Features data
        """
        data = {
            'layer_id': layer_id,
            'limit': limit
        }

        if bbox:
            data['bbox'] = bbox
        if filter_expression:
            data['filter_expression'] = filter_expression
        if attributes_only:
            data['attributes_only'] = attributes_only
        if simplify_tolerance:
            data['simplify_tolerance'] = simplify_tolerance

        return self.send_request('get_features', data)

    def load_layer(self, path: str, layer_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load layer from file

        Args:
            path: File path
            layer_name: Optional layer name

        Returns:
            Layer information
        """
        data = {'path': path}
        if layer_name:
            data['layer_name'] = layer_name

        return self.send_request('load_layer', data)

    def execute_code(self, code: str) -> Dict[str, Any]:
        """
        Execute Python code on server

        Args:
            code: Python code to execute

        Returns:
            Execution result

        Warning:
            This is a powerful operation. Code is executed in a sandbox
            but should still be used with caution.
        """
        return self.send_request('execute_code', {'code': code})

    def get_stats(self) -> Dict[str, Any]:
        """
        Get server statistics

        Returns:
            Server statistics
        """
        return self.send_request('get_stats')

    def close(self) -> None:
        """Close all connections"""
        self.pool.close_all()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience function
def connect(
    host: str = '127.0.0.1',
    port: int = 9876,
    token: Optional[str] = None,
    use_tls: bool = False
) -> SecureQGISMCPClient:
    """
    Create and connect secure QGIS MCP client

    Args:
        host: Server host
        port: Server port
        token: Authentication token
        use_tls: Use TLS/SSL encryption

    Returns:
        Connected client instance

    Example:
        >>> with connect() as client:
        ...     layers = client.list_layers()
        ...     print(layers)
    """
    return SecureQGISMCPClient(
        host=host,
        port=port,
        token=token,
        use_tls=use_tls,
        auto_authenticate=True
    )
