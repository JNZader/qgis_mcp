"""
QGIS MCP - Secure Model Context Protocol for QGIS

This package provides a secure, production-ready MCP implementation for QGIS
with comprehensive security features including authentication, rate limiting,
TLS/SSL support, and code sandboxing.

Security Features:
- Localhost-only binding
- Mandatory authentication
- Rate limiting with exponential backoff
- TLS/SSL encryption support
- AST-based code sandbox
- Path traversal prevention
- Buffer overflow protection
- Message validation

Usage:

Server (QGIS Plugin):
    from qgis_mcp_plugin.qgis_mcp_server_secure import start_secure_server

    # Start server with authentication
    server = start_secure_server(port=9876, require_auth=True)

Client:
    from qgis_mcp import connect

    # Connect to server
    with connect(port=9876) as client:
        layers = client.list_layers()
        features = client.get_features(layer_id='layer_1', limit=100)
"""

from .qgis_mcp_client_secure import (
    SecureQGISMCPClient,
    ClientException,
    connect
)

__version__ = '2.0.0-secure'
__all__ = [
    'SecureQGISMCPClient',
    'ClientException',
    'connect',
]
