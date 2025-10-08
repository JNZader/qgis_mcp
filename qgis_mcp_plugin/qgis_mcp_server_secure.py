"""
QGIS MCP Secure Server - Production-ready with comprehensive security

Features:
- Localhost-only binding (127.0.0.1)
- Mandatory authentication with secure token storage
- Rate limiting per operation type
- TLS/SSL support (optional)
- Buffer size limits (10MB)
- Message validation with JSON Schema
- AST-based code sandbox
- Enhanced path validation
- No information disclosure in errors
- Thread-safe operation
"""

import socket
import threading
import time
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime

try:
    from qgis.core import QgsMessageLog, Qgis, QgsProject
    from qgis.utils import iface
    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False
    print("Warning: QGIS not available, running in standalone mode")

from .security_improved import (
    SecurityException,
    ImprovedCodeSandbox,
    EnhancedPathValidator,
    ImprovedRateLimiter,
    AuthenticationManager
)
from .protocol import BufferedProtocolHandler, ProtocolException
from .tls_handler import TLSHandler
from .optimization import OptimizedFeatureAccess, PaginatedLayerAccess, PerformanceMonitor


class SecureQGISMCPServer:
    """
    Secure QGIS MCP Server with comprehensive security hardening

    Security Features:
    - Forced localhost-only binding
    - Mandatory authentication
    - Rate limiting with exponential backoff
    - TLS/SSL encryption support
    - Buffer overflow protection
    - Message validation
    - Code sandbox with AST whitelist
    - Path traversal prevention
    - Generic error messages (no info disclosure)
    """

    MAX_BUFFER_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_CONNECTIONS = 10  # Limit concurrent connections

    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 9876,
        use_tls: bool = False,
        require_auth: bool = True,
        allowed_directories: Optional[list] = None
    ):
        """
        Initialize secure QGIS MCP server

        Args:
            host: Host to bind to (forced to 127.0.0.1 for security)
            port: Port number
            use_tls: Enable TLS/SSL encryption
            require_auth: Require authentication (strongly recommended)
            allowed_directories: List of allowed directories for file operations

        Raises:
            SecurityException: If attempting to bind to non-localhost address
        """
        # SECURITY: Force localhost-only binding
        if host not in ('127.0.0.1', 'localhost', '::1'):
            raise SecurityException(
                "For security reasons, only localhost binding is allowed. "
                "Use SSH port forwarding or VPN for remote access."
            )

        self.host = '127.0.0.1'  # Always force IPv4 localhost
        self.port = port
        self.use_tls = use_tls
        self.require_auth = require_auth

        # Security components
        self.auth_manager = AuthenticationManager()
        self.rate_limiter = ImprovedRateLimiter()
        self.sandbox = ImprovedCodeSandbox(max_code_length=102400, timeout_seconds=30)
        self.path_validator = EnhancedPathValidator(allowed_directories=allowed_directories)

        # Protocol handler with validation
        self.protocol = BufferedProtocolHandler(use_msgpack=True, validate_schema=True)

        # TLS handler
        self.tls_handler = TLSHandler() if use_tls else None

        # Performance optimization
        self.feature_access = OptimizedFeatureAccess()
        self.perf_monitor = PerformanceMonitor()

        # Server state
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.client_threads: list = []
        self.active_connections = 0
        self._conn_lock = threading.Lock()

        # Command handlers
        self.command_handlers: Dict[str, Callable] = {
            'authenticate': self._handle_authenticate,
            'list_layers': self._handle_list_layers,
            'get_features': self._handle_get_features,
            'load_layer': self._handle_load_layer,
            'execute_code': self._handle_execute_code,
            'get_stats': self._handle_get_stats,
            'ping': self._handle_ping,
        }

        if HAS_QGIS:
            QgsMessageLog.logMessage(
                f"Secure QGIS MCP Server initialized on {self.host}:{self.port}",
                "QGIS MCP Secure",
                Qgis.Info
            )

            if self.require_auth:
                token = self.auth_manager.api_token
                QgsMessageLog.logMessage(
                    f"Authentication token: {token}",
                    "QGIS MCP Secure",
                    Qgis.Info
                )

    def start(self) -> None:
        """Start the secure server"""
        if self.running:
            raise RuntimeError("Server is already running")

        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to localhost only
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(self.MAX_CONNECTIONS)

        self.running = True

        if HAS_QGIS:
            QgsMessageLog.logMessage(
                f"Secure server listening on {self.host}:{self.port}",
                "QGIS MCP Secure",
                Qgis.Success
            )

        # Accept connections in main thread
        try:
            while self.running:
                self.server_socket.settimeout(1.0)  # Allow checking self.running

                try:
                    client_socket, client_addr = self.server_socket.accept()

                    # Check connection limit
                    with self._conn_lock:
                        if self.active_connections >= self.MAX_CONNECTIONS:
                            if HAS_QGIS:
                                QgsMessageLog.logMessage(
                                    f"Connection limit reached, rejecting {client_addr}",
                                    "QGIS MCP Secure",
                                    Qgis.Warning
                                )
                            client_socket.close()
                            continue

                        self.active_connections += 1

                    # Wrap with TLS if enabled
                    if self.use_tls and self.tls_handler:
                        try:
                            client_socket = self.tls_handler.wrap_socket(
                                client_socket,
                                server_side=True
                            )
                        except Exception as e:
                            if HAS_QGIS:
                                QgsMessageLog.logMessage(
                                    f"TLS handshake failed: {type(e).__name__}",
                                    "QGIS MCP Secure",
                                    Qgis.Critical
                                )
                            client_socket.close()
                            with self._conn_lock:
                                self.active_connections -= 1
                            continue

                    # Handle client in new thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_addr),
                        daemon=True
                    )
                    client_thread.start()
                    self.client_threads.append(client_thread)

                except socket.timeout:
                    continue
                except OSError:
                    break

        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the server gracefully"""
        if not self.running:
            return

        self.running = False

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

        # Wait for client threads to finish (with timeout)
        for thread in self.client_threads:
            thread.join(timeout=2.0)

        if HAS_QGIS:
            QgsMessageLog.logMessage(
                "Secure server stopped",
                "QGIS MCP Secure",
                Qgis.Info
            )

    def _handle_client(self, client_socket: socket.socket, client_addr: tuple) -> None:
        """
        Handle individual client connection

        Args:
            client_socket: Client socket
            client_addr: Client address (IP, port)
        """
        client_id = f"{client_addr[0]}:{client_addr[1]}"
        protocol_handler = BufferedProtocolHandler(use_msgpack=True, validate_schema=True)
        authenticated = not self.require_auth  # If auth not required, start authenticated

        if HAS_QGIS:
            QgsMessageLog.logMessage(
                f"Client connected: {client_id}",
                "QGIS MCP Secure",
                Qgis.Info
            )

        try:
            client_socket.settimeout(60.0)  # 60 second timeout

            while self.running:
                # Receive data
                try:
                    data = client_socket.recv(8192)
                    if not data:
                        break

                    # Feed to protocol handler
                    protocol_handler.feed_data(data)

                    # Check buffer size
                    if protocol_handler.get_buffer_size() > self.MAX_BUFFER_SIZE:
                        if HAS_QGIS:
                            QgsMessageLog.logMessage(
                                f"Buffer overflow from {client_id} - closing connection",
                                "QGIS MCP Secure",
                                Qgis.Critical
                            )
                        self._send_error(client_socket, "1", "Request too large")
                        break

                    # Try to read complete messages
                    while True:
                        try:
                            message = protocol_handler.try_read_message()
                            if not message:
                                break

                            # Process message
                            response = self._process_message(
                                message,
                                client_id,
                                authenticated
                            )

                            # Update authentication status
                            if message.get('type') == 'authenticate' and response.get('success'):
                                authenticated = True

                            # Send response
                            self.protocol.send_message(client_socket, response)

                        except ProtocolException as e:
                            if HAS_QGIS:
                                QgsMessageLog.logMessage(
                                    f"Protocol error from {client_id}: {type(e).__name__}",
                                    "QGIS MCP Secure",
                                    Qgis.Warning
                                )
                            self._send_error(client_socket, "0", "Invalid request format")
                            break

                except socket.timeout:
                    if HAS_QGIS:
                        QgsMessageLog.logMessage(
                            f"Client timeout: {client_id}",
                            "QGIS MCP Secure",
                            Qgis.Info
                        )
                    break
                except socket.error:
                    break

        except Exception as e:
            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Unexpected error handling {client_id}: {type(e).__name__}",
                    "QGIS MCP Secure",
                    Qgis.Critical
                )
        finally:
            client_socket.close()
            with self._conn_lock:
                self.active_connections -= 1

            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Client disconnected: {client_id}",
                    "QGIS MCP Secure",
                    Qgis.Info
                )

    def _process_message(
        self,
        message: Dict[str, Any],
        client_id: str,
        authenticated: bool
    ) -> Dict[str, Any]:
        """
        Process client message with security checks

        Args:
            message: Validated message dictionary
            client_id: Client identifier
            authenticated: Whether client is authenticated

        Returns:
            Response dictionary
        """
        start_time = time.time()
        msg_id = message.get('id', '0')
        msg_type = message.get('type', 'unknown')

        try:
            # Authentication check
            if self.require_auth and not authenticated and msg_type != 'authenticate':
                if HAS_QGIS:
                    QgsMessageLog.logMessage(
                        f"Unauthenticated request from {client_id}: {msg_type}",
                        "QGIS MCP Secure",
                        Qgis.Warning
                    )
                return {
                    'type': 'response',
                    'id': msg_id,
                    'success': False,
                    'error': 'Authentication required'
                }

            # Get operation type for rate limiting
            operation_type = self._get_operation_type(msg_type)

            # Rate limiting check
            try:
                if not self.rate_limiter.check_rate_limit(client_id, operation_type):
                    if HAS_QGIS:
                        QgsMessageLog.logMessage(
                            f"Rate limit exceeded for {client_id}: {msg_type}",
                            "QGIS MCP Secure",
                            Qgis.Warning
                        )
                    return {
                        'type': 'response',
                        'id': msg_id,
                        'success': False,
                        'error': 'Rate limit exceeded. Please slow down.'
                    }
            except SecurityException as e:
                # Client is locked out
                return {
                    'type': 'response',
                    'id': msg_id,
                    'success': False,
                    'error': str(e)
                }

            # Get handler
            handler = self.command_handlers.get(msg_type)
            if not handler:
                return {
                    'type': 'response',
                    'id': msg_id,
                    'success': False,
                    'error': f'Unknown command type: {msg_type}'
                }

            # Execute handler
            result = handler(message, client_id)

            # Record performance
            elapsed = time.time() - start_time
            self.perf_monitor.record_command(msg_type, elapsed)

            return {
                'type': 'response',
                'id': msg_id,
                'success': True,
                'data': result
            }

        except SecurityException as e:
            # Security violation - log but don't reveal details
            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Security violation from {client_id}: {type(e).__name__}",
                    "QGIS MCP Secure",
                    Qgis.Critical
                )
            return {
                'type': 'response',
                'id': msg_id,
                'success': False,
                'error': 'Operation not permitted'
            }
        except Exception as e:
            # Generic error - don't reveal details
            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Error processing {msg_type} from {client_id}: {type(e).__name__}",
                    "QGIS MCP Secure",
                    Qgis.Critical
                )
                # Log full traceback internally
                QgsMessageLog.logMessage(
                    traceback.format_exc(),
                    "QGIS MCP Secure",
                    Qgis.Critical
                )
            return {
                'type': 'response',
                'id': msg_id,
                'success': False,
                'error': 'Internal server error'
            }

    def _get_operation_type(self, msg_type: str) -> str:
        """Map message type to rate limiting category"""
        if msg_type == 'authenticate':
            return 'authentication'
        elif msg_type in ('execute_code', 'load_layer'):
            return 'expensive'
        elif msg_type in ('ping', 'get_stats'):
            return 'cheap'
        else:
            return 'normal'

    def _send_error(self, client_socket: socket.socket, msg_id: str, error: str) -> None:
        """Send error response"""
        try:
            response = {
                'type': 'response',
                'id': msg_id,
                'success': False,
                'error': error
            }
            self.protocol.send_message(client_socket, response)
        except:
            pass

    # Command Handlers

    def _handle_authenticate(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Handle authentication request"""
        data = message.get('data', {})
        token = data.get('token', '')

        if self.auth_manager.verify_token(client_id, token):
            self.rate_limiter.record_successful_auth(client_id)
            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Client authenticated: {client_id}",
                    "QGIS MCP Secure",
                    Qgis.Success
                )
            return {'authenticated': True}
        else:
            self.rate_limiter.record_failed_auth(client_id)
            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Authentication failed: {client_id}",
                    "QGIS MCP Secure",
                    Qgis.Warning
                )
            raise SecurityException("Invalid authentication token")

    def _handle_list_layers(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Handle list layers request"""
        if not HAS_QGIS:
            raise RuntimeError("QGIS not available")

        data = message.get('data', {})
        offset = data.get('offset', 0)
        limit = data.get('limit', 50)

        return PaginatedLayerAccess.get_layers_paginated(offset=offset, limit=limit)

    def _handle_get_features(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Handle get features request"""
        if not HAS_QGIS:
            raise RuntimeError("QGIS not available")

        data = message.get('data', {})
        return self.feature_access.get_features_optimized(**data)

    def _handle_load_layer(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Handle load layer request"""
        if not HAS_QGIS:
            raise RuntimeError("QGIS not available")

        data = message.get('data', {})
        path = data.get('path', '')
        layer_name = data.get('layer_name')

        # Validate path
        validated_path = self.path_validator.validate_path(
            path,
            operation='read',
            allowed_extensions=list(EnhancedPathValidator.SAFE_GIS_EXTENSIONS)
        )

        # Load layer using QGIS
        from qgis.core import QgsVectorLayer, QgsRasterLayer

        # Try vector first
        layer = QgsVectorLayer(validated_path, layer_name or Path(validated_path).stem, 'ogr')

        if not layer.isValid():
            # Try raster
            layer = QgsRasterLayer(validated_path, layer_name or Path(validated_path).stem)

        if not layer.isValid():
            raise ValueError(f"Could not load layer from: {Path(validated_path).name}")

        # Add to project
        QgsProject.instance().addMapLayer(layer)

        return {
            'layer_id': layer.id(),
            'layer_name': layer.name(),
            'type': 'vector' if isinstance(layer, QgsVectorLayer) else 'raster'
        }

    def _handle_execute_code(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Handle code execution request"""
        if not HAS_QGIS:
            raise RuntimeError("QGIS not available")

        data = message.get('data', {})
        code = data.get('code', '')

        # Validate and execute with sandbox
        self.sandbox.validate_code(code)
        result = self.sandbox.execute_with_timeout(code)

        return {
            'executed': True,
            'result': str(result) if result is not None else None
        }

    def _handle_get_stats(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Handle get statistics request"""
        return {
            'performance': self.perf_monitor.get_performance_report(),
            'cache': self.feature_access.geometry_cache.get_stats(),
            'server': {
                'uptime_seconds': int(time.time() - getattr(self, '_start_time', time.time())),
                'active_connections': self.active_connections,
                'total_connections': len(self.client_threads)
            }
        }

    def _handle_ping(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Handle ping request"""
        return {
            'pong': True,
            'timestamp': datetime.now().isoformat(),
            'server_version': '2.0.0-secure'
        }


def start_secure_server(
    port: int = 9876,
    use_tls: bool = False,
    require_auth: bool = True
) -> SecureQGISMCPServer:
    """
    Start secure QGIS MCP server

    Args:
        port: Port number
        use_tls: Enable TLS/SSL encryption
        require_auth: Require authentication (strongly recommended)

    Returns:
        Running server instance
    """
    server = SecureQGISMCPServer(
        host='127.0.0.1',
        port=port,
        use_tls=use_tls,
        require_auth=require_auth
    )

    # Start in background thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    return server
