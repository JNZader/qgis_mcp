"""
TLS/SSL Handler for QGIS MCP
Implements network encryption with self-signed certificates
"""

import ssl
import socket
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

try:
    from OpenSSL import crypto
    HAS_OPENSSL = True
except ImportError:
    HAS_OPENSSL = False

try:
    from qgis.core import QgsMessageLog, Qgis
    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False


class TLSHandler:
    """Manage TLS/SSL encryption for QGIS MCP"""

    def __init__(self, cert_dir: Optional[Path] = None):
        """
        Initialize TLS handler

        Args:
            cert_dir: Directory to store certificates (default: ~/.qgis_mcp/certs)
        """
        if cert_dir is None:
            cert_dir = Path.home() / '.qgis_mcp' / 'certs'

        self.cert_dir = cert_dir
        self.cert_dir.mkdir(parents=True, exist_ok=True)

        self.cert_file = self.cert_dir / 'server.crt'
        self.key_file = self.cert_dir / 'server.key'

    def ensure_certificates(self) -> None:
        """Generate self-signed certificates if they don't exist"""
        if self.cert_file.exists() and self.key_file.exists():
            # Check if certificates are still valid
            if self._certificates_valid():
                return
            else:
                if HAS_QGIS:
                    QgsMessageLog.logMessage(
                        "Certificates expired, regenerating...",
                        "QGIS MCP TLS",
                        Qgis.Warning
                    )

        if not HAS_OPENSSL:
            raise ImportError(
                "PyOpenSSL is required for TLS support. "
                "Install with: pip install pyOpenSSL"
            )

        self._generate_certificates()

    def _certificates_valid(self) -> bool:
        """Check if existing certificates are still valid"""
        try:
            import ssl
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # Try to load the certificate
            with open(self.cert_file, 'rb') as f:
                cert_data = f.read()

            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)

            # Check expiration
            expiry_date = datetime.strptime(
                cert.get_notAfter().decode('ascii'),
                '%Y%m%d%H%M%SZ'
            )

            # If expires in less than 30 days, regenerate
            if expiry_date - datetime.utcnow() < timedelta(days=30):
                return False

            return True
        except Exception:
            return False

    def _generate_certificates(self) -> None:
        """Generate self-signed certificates"""
        # Generate key pair
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 4096)

        # Generate certificate
        cert = crypto.X509()

        # Set certificate details
        cert.get_subject().C = "US"
        cert.get_subject().ST = "State"
        cert.get_subject().L = "City"
        cert.get_subject().O = "QGIS MCP"
        cert.get_subject().OU = "Localhost Server"
        cert.get_subject().CN = "localhost"

        # Add Subject Alternative Names for localhost
        san_list = [
            b"DNS:localhost",
            b"DNS:*.localhost",
            b"IP:127.0.0.1",
            b"IP:::1"  # IPv6 localhost
        ]

        cert.add_extensions([
            crypto.X509Extension(
                b"subjectAltName",
                False,
                b",".join(san_list)
            ),
            crypto.X509Extension(
                b"basicConstraints",
                True,
                b"CA:FALSE"
            ),
            crypto.X509Extension(
                b"keyUsage",
                True,
                b"digitalSignature,keyEncipherment"
            ),
            crypto.X509Extension(
                b"extendedKeyUsage",
                False,
                b"serverAuth"
            ),
        ])

        # Set validity period (1 year)
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(365 * 24 * 60 * 60)  # 1 year

        # Self-sign
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.sign(key, 'sha256')

        # Write certificate file
        with open(self.cert_file, 'wb') as f:
            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
        self.cert_file.chmod(0o644)

        # Write private key file
        with open(self.key_file, 'wb') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
        self.key_file.chmod(0o600)  # Private key must be restricted

        if HAS_QGIS:
            QgsMessageLog.logMessage(
                f"Generated new TLS certificates at {self.cert_dir}",
                "QGIS MCP TLS",
                Qgis.Info
            )

    def create_server_context(self) -> ssl.SSLContext:
        """
        Create SSL context for server

        Returns:
            Configured SSL context for server-side
        """
        self.ensure_certificates()

        # Create context with secure defaults
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

        # Load certificate and key
        context.load_cert_chain(
            certfile=str(self.cert_file),
            keyfile=str(self.key_file)
        )

        # Set secure protocol version (TLS 1.2 or higher)
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        # Disable compression to prevent CRIME attack
        context.options |= ssl.OP_NO_COMPRESSION

        # Set secure ciphers
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')

        return context

    def create_client_context(self, verify_cert: bool = False) -> ssl.SSLContext:
        """
        Create SSL context for client

        Args:
            verify_cert: Whether to verify server certificate (use False for self-signed)

        Returns:
            Configured SSL context for client-side
        """
        # Create context
        context = ssl.create_default_context()

        if not verify_cert:
            # For self-signed certificates
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            # For production with proper certificates
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED

            # Optionally add custom CA certificate
            if self.cert_file.exists():
                context.load_verify_locations(cafile=str(self.cert_file))

        # Set secure protocol version
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        return context

    def wrap_socket(
        self,
        sock: socket.socket,
        server_side: bool = True,
        verify_cert: bool = False
    ) -> ssl.SSLSocket:
        """
        Wrap socket with TLS/SSL

        Args:
            sock: Socket to wrap
            server_side: True for server, False for client
            verify_cert: Whether to verify certificates (client-side only)

        Returns:
            SSL-wrapped socket
        """
        if server_side:
            context = self.create_server_context()
        else:
            context = self.create_client_context(verify_cert=verify_cert)

        return context.wrap_socket(sock, server_side=server_side)

    def get_certificate_info(self) -> dict:
        """
        Get information about current certificates

        Returns:
            Dictionary with certificate information
        """
        if not self.cert_file.exists():
            return {"status": "no_certificate"}

        try:
            with open(self.cert_file, 'rb') as f:
                cert_data = f.read()

            cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert_data)

            not_before = datetime.strptime(
                cert.get_notBefore().decode('ascii'),
                '%Y%m%d%H%M%SZ'
            )
            not_after = datetime.strptime(
                cert.get_notAfter().decode('ascii'),
                '%Y%m%d%H%M%SZ'
            )

            subject = cert.get_subject()

            return {
                "status": "valid",
                "subject": {
                    "CN": subject.CN,
                    "O": subject.O,
                    "OU": subject.OU,
                },
                "valid_from": not_before.isoformat(),
                "valid_until": not_after.isoformat(),
                "days_remaining": (not_after - datetime.utcnow()).days,
                "serial_number": cert.get_serial_number(),
                "signature_algorithm": cert.get_signature_algorithm().decode('ascii'),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
