"""
Enhanced security module for QGIS MCP
Implements all FASE 0 and FASE 1 security improvements
"""

import ast
import hmac
import os
import secrets
import time
import unicodedata
import urllib.parse
import threading
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

try:
    from qgis.core import QgsMessageLog, Qgis
    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False


class SecurityException(Exception):
    """Raised when a security violation is detected"""
    pass


class ImprovedCodeSandbox:
    """
    AST-based code sandbox with whitelist approach
    Replaces regex-based blacklist with proper AST validation
    """

    # Allowed AST node types
    ALLOWED_NODES: Set[type] = {
        ast.Module, ast.Expr, ast.Assign, ast.AnnAssign, ast.AugAssign,
        ast.Name, ast.Constant, ast.Num, ast.Str, ast.Bytes,
        ast.List, ast.Tuple, ast.Set, ast.Dict,
        ast.BinOp, ast.UnaryOp, ast.Compare, ast.BoolOp,
        ast.IfExp, ast.If, ast.For, ast.While, ast.Break, ast.Continue,
        ast.FunctionDef, ast.Return, ast.Pass,
        ast.Call, ast.Attribute, ast.Subscript, ast.Index, ast.Slice,
        ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp,
        ast.comprehension,
        ast.Load, ast.Store, ast.Del,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
        ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd,
        ast.And, ast.Or, ast.Not, ast.Invert, ast.UAdd, ast.USub,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.Is, ast.IsNot, ast.In, ast.NotIn,
        ast.arg, ast.arguments, ast.keyword,
    }

    # Allowed built-in functions
    ALLOWED_BUILTINS: Set[str] = {
        'True', 'False', 'None',
        'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter',
        'float', 'int', 'isinstance', 'len', 'list', 'map', 'max',
        'min', 'range', 'reversed', 'round', 'set', 'sorted', 'str',
        'sum', 'tuple', 'zip', 'print',
    }

    # Allowed QGIS modules and their permitted classes/functions
    ALLOWED_MODULES: Dict[str, List[str]] = {
        'qgis.core': [
            'QgsProject', 'QgsVectorLayer', 'QgsRasterLayer', 'QgsFeature',
            'QgsGeometry', 'QgsPoint', 'QgsPointXY', 'QgsRectangle',
            'QgsCoordinateReferenceSystem', 'QgsCoordinateTransform',
            'QgsField', 'QgsFields', 'QgsExpression', 'QgsFeatureRequest',
            'QgsWkbTypes', 'QgsLayerTreeLayer', 'QgsLayerTreeGroup',
            'QgsMapLayer', 'QgsVectorFileWriter', 'QgsRasterFileWriter',
        ],
        'qgis.utils': ['iface'],
        'PyQt5.QtCore': ['QVariant', 'Qt', 'QDateTime', 'QDate', 'QTime'],
        'PyQt5.QtGui': ['QColor'],
    }

    # Dangerous attributes that should never be accessed
    DANGEROUS_ATTRS: Set[str] = {
        '__builtins__', '__globals__', '__locals__', '__dict__',
        '__class__', '__bases__', '__subclasses__', '__import__',
        '__code__', '__closure__', '__func__', '__self__',
        'func_globals', 'func_code', 'gi_frame', 'gi_code',
    }

    # Dangerous function names
    DANGEROUS_FUNCTIONS: Set[str] = {
        'eval', 'exec', 'compile', '__import__',
        'open', 'input', 'exit', 'quit',
        'help', 'vars', 'dir', 'globals', 'locals',
        'getattr', 'setattr', 'delattr', 'hasattr',
        'breakpoint', 'memoryview', 'bytearray',
    }

    def __init__(self, max_code_length: int = 102400, timeout_seconds: int = 30):
        """
        Initialize code sandbox

        Args:
            max_code_length: Maximum allowed code length (100KB default)
            timeout_seconds: Maximum execution time (30s default)
        """
        self.max_code_length = max_code_length
        self.timeout_seconds = timeout_seconds

    def validate_code(self, code: str) -> None:
        """
        Validate code using AST whitelist approach

        Args:
            code: Python code to validate

        Raises:
            SecurityException: If code violates security policies
        """
        # Check code length
        if len(code) > self.max_code_length:
            raise SecurityException(
                f"Code exceeds maximum length of {self.max_code_length} characters"
            )

        # Parse code into AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SecurityException(f"Invalid Python syntax: {e}")

        # Walk AST and validate each node
        for node in ast.walk(tree):
            node_type = type(node)

            # Check if node type is allowed
            if node_type not in self.ALLOWED_NODES:
                raise SecurityException(
                    f"Disallowed operation: {node_type.__name__} at line {getattr(node, 'lineno', '?')}"
                )

            # Validate imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._validate_import(node)

            # Validate function calls
            if isinstance(node, ast.Call):
                self._validate_call(node)

            # Validate attribute access
            if isinstance(node, ast.Attribute):
                self._validate_attribute(node)

            # Validate name access
            if isinstance(node, ast.Name):
                self._validate_name(node)

    def _validate_import(self, node: ast.AST) -> None:
        """Validate import statements"""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                if module not in self.ALLOWED_MODULES:
                    raise SecurityException(
                        f"Import not allowed: {module} at line {node.lineno}"
                    )

        elif isinstance(node, ast.ImportFrom):
            module = node.module
            if module not in self.ALLOWED_MODULES:
                raise SecurityException(
                    f"Import not allowed: {module} at line {node.lineno}"
                )

            # Validate specific imports
            allowed_names = self.ALLOWED_MODULES.get(module, [])
            for alias in node.names:
                if alias.name == '*':
                    raise SecurityException(
                        f"Wildcard imports not allowed at line {node.lineno}"
                    )
                if alias.name not in allowed_names:
                    raise SecurityException(
                        f"Import not allowed: {module}.{alias.name} at line {node.lineno}"
                    )

    def _validate_call(self, node: ast.Call) -> None:
        """Validate function calls"""
        # Check direct function calls by name
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.DANGEROUS_FUNCTIONS:
                raise SecurityException(
                    f"Dangerous function call: {func_name} at line {node.lineno}"
                )

        # Check method calls
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in self.DANGEROUS_FUNCTIONS:
                raise SecurityException(
                    f"Dangerous method call: {attr} at line {node.lineno}"
                )

    def _validate_attribute(self, node: ast.Attribute) -> None:
        """Validate attribute access"""
        if node.attr in self.DANGEROUS_ATTRS:
            raise SecurityException(
                f"Dangerous attribute access: {node.attr} at line {node.lineno}"
            )

    def _validate_name(self, node: ast.Name) -> None:
        """Validate name references"""
        if node.id in self.DANGEROUS_FUNCTIONS and isinstance(node.ctx, ast.Load):
            raise SecurityException(
                f"Access to dangerous name: {node.id} at line {node.lineno}"
            )

    def create_safe_namespace(self) -> dict:
        """
        Create restricted namespace for code execution

        Returns:
            Dictionary with safe builtins and QGIS objects
        """
        # Create minimal builtins
        safe_builtins = {
            name: __builtins__[name] if isinstance(__builtins__, dict) else getattr(__builtins__, name)
            for name in self.ALLOWED_BUILTINS
            if (isinstance(__builtins__, dict) and name in __builtins__) or
               (not isinstance(__builtins__, dict) and hasattr(__builtins__, name))
        }

        namespace = {
            '__builtins__': safe_builtins,
        }

        # Add QGIS objects if available
        if HAS_QGIS:
            from qgis.core import QgsProject
            from qgis.utils import iface

            namespace.update({
                'QgsProject': QgsProject,
                'iface': iface,
                'project': QgsProject.instance(),
            })

        return namespace

    def execute_with_timeout(self, code: str) -> Any:
        """
        Execute code with timeout and resource limits

        Args:
            code: Validated Python code to execute

        Returns:
            Result of code execution

        Raises:
            TimeoutError: If execution exceeds timeout
            SecurityException: If code validation fails
        """
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Code execution timeout after {self.timeout_seconds} seconds")

        # Validate first
        self.validate_code(code)

        # Create safe namespace
        namespace = self.create_safe_namespace()

        # Set timeout (Unix only)
        if hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout_seconds)

        try:
            exec(code, namespace)
            return namespace.get('result', None)
        finally:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)  # Cancel timeout


class EnhancedPathValidator:
    """
    Enhanced path validation with comprehensive security checks
    Prevents path traversal, symlink attacks, and other path-based exploits
    """

    # Dangerous file extensions
    DANGEROUS_EXTENSIONS: Set[str] = {
        '.exe', '.dll', '.so', '.dylib', '.sh', '.bat', '.cmd', '.ps1',
        '.vbs', '.js', '.jar', '.app', '.deb', '.rpm', '.msi',
    }

    # Safe extensions for GIS data
    SAFE_GIS_EXTENSIONS: Set[str] = {
        '.shp', '.geojson', '.json', '.kml', '.kmz', '.gml', '.gpkg',
        '.tif', '.tiff', '.jpg', '.jpeg', '.png', '.asc', '.grd',
        '.qgs', '.qgz', '.sqlite', '.db', '.csv', '.txt',
    }

    def __init__(self, allowed_directories: Optional[List[Path]] = None):
        """
        Initialize path validator

        Args:
            allowed_directories: List of allowed base directories
        """
        if allowed_directories is None:
            # Default allowed directories
            allowed_directories = [
                Path.home(),
                Path.cwd(),
                Path('/tmp') if os.name != 'nt' else Path(os.environ.get('TEMP', 'C:\\Temp')),
            ]

        self.allowed_directories = [Path(d).resolve() for d in allowed_directories]

    def validate_path(
        self,
        path_str: str,
        operation: str = 'read',
        allowed_extensions: Optional[List[str]] = None
    ) -> str:
        """
        Enhanced path validation with comprehensive security checks

        Args:
            path_str: Path to validate
            operation: Operation type ('read', 'write', 'execute')
            allowed_extensions: List of allowed file extensions

        Returns:
            Canonical path string if valid

        Raises:
            SecurityException: If path fails validation
        """
        # 1. Early rejection of obvious attacks
        if not path_str or not path_str.strip():
            raise SecurityException("Empty path not allowed")

        if '..' in path_str:
            raise SecurityException("Path traversal pattern detected")

        if path_str.startswith('\\\\') and os.name == 'nt':
            raise SecurityException("UNC paths not allowed")

        # 2. Decode URL encoding
        path_str = urllib.parse.unquote(path_str)

        # 3. Normalize Unicode
        path_str = unicodedata.normalize('NFKC', path_str)

        # 4. Convert to Path and resolve (follows symlinks)
        try:
            path = Path(path_str).expanduser()
            canonical_path = path.resolve(strict=False)
        except (ValueError, OSError) as e:
            raise SecurityException(f"Invalid path: {e}")

        # 5. Get real path (additional symlink resolution)
        try:
            real_path = os.path.realpath(canonical_path)
            canonical_path = Path(real_path)
        except (ValueError, OSError) as e:
            raise SecurityException(f"Path resolution failed: {e}")

        # 6. Check if path is within allowed directories
        path_is_allowed = False
        for allowed_dir in self.allowed_directories:
            try:
                canonical_path.relative_to(allowed_dir)
                path_is_allowed = True
                break
            except ValueError:
                continue

        if not path_is_allowed:
            raise SecurityException(
                f"Path outside allowed directories: {canonical_path}\n"
                f"Allowed: {', '.join(str(d) for d in self.allowed_directories)}"
            )

        # 7. Check for dangerous extensions
        if canonical_path.suffix.lower() in self.DANGEROUS_EXTENSIONS:
            raise SecurityException(
                f"Dangerous file extension: {canonical_path.suffix}"
            )

        # 8. Check allowed extensions if specified
        if allowed_extensions:
            if canonical_path.suffix.lower() not in allowed_extensions:
                raise SecurityException(
                    f"File extension {canonical_path.suffix} not allowed. "
                    f"Allowed: {', '.join(allowed_extensions)}"
                )

        # 9. Check for Windows alternate data streams
        if ':' in canonical_path.name and os.name == 'nt':
            raise SecurityException("Windows alternate data streams not allowed")

        # 10. Verify path exists (for read operations)
        if operation == 'read':
            if not canonical_path.exists():
                raise SecurityException(f"Path does not exist: {canonical_path}")

        # 11. Check permissions
        if operation == 'read' and canonical_path.exists():
            if not os.access(canonical_path, os.R_OK):
                raise SecurityException(f"No read permission: {canonical_path}")
        elif operation == 'write':
            if canonical_path.exists() and not os.access(canonical_path, os.W_OK):
                raise SecurityException(f"No write permission: {canonical_path}")
            elif not canonical_path.exists():
                # Check parent directory
                parent = canonical_path.parent
                if not parent.exists() or not os.access(parent, os.W_OK):
                    raise SecurityException(f"No write permission to parent: {parent}")

        return str(canonical_path)


class SecureTokenStorage:
    """
    Secure token storage using system keyring or encrypted file
    """

    SERVICE_NAME = "qgis_mcp"

    def __init__(self):
        """Initialize secure token storage"""
        self.keyring_available = self._check_keyring()

        if not self.keyring_available and HAS_QGIS:
            QgsMessageLog.logMessage(
                "System keyring not available, using encrypted file storage",
                "QGIS MCP Security",
                Qgis.Warning
            )

    def _check_keyring(self) -> bool:
        """Check if system keyring is available"""
        try:
            import keyring
            keyring.get_keyring()
            return True
        except (ImportError, Exception):
            return False

    def store_token(self, token: str) -> None:
        """
        Store token securely

        Args:
            token: Authentication token to store
        """
        if self.keyring_available:
            import keyring
            keyring.set_password(self.SERVICE_NAME, "auth_token", token)
        else:
            self._store_encrypted_token(token)

    def retrieve_token(self) -> str:
        """
        Retrieve token securely

        Returns:
            Authentication token

        Raises:
            FileNotFoundError: If no token is stored
        """
        if self.keyring_available:
            import keyring
            token = keyring.get_password(self.SERVICE_NAME, "auth_token")
            if token:
                return token

        return self._retrieve_encrypted_token()

    def delete_token(self) -> None:
        """Delete stored token"""
        if self.keyring_available:
            try:
                import keyring
                keyring.delete_password(self.SERVICE_NAME, "auth_token")
            except Exception:
                pass

        # Delete file-based token
        token_file = self._get_token_path()
        if token_file.exists():
            token_file.unlink()

    def _get_token_path(self) -> Path:
        """Get path to encrypted token file"""
        token_dir = Path.home() / '.qgis_mcp'
        token_dir.mkdir(parents=True, exist_ok=True)
        return token_dir / 'auth_token.enc'

    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key"""
        from cryptography.fernet import Fernet

        key_file = Path.home() / '.qgis_mcp' / '.key'
        key_file.parent.mkdir(parents=True, exist_ok=True)

        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            key_file.chmod(0o600)
            return key

    def _store_encrypted_token(self, token: str) -> None:
        """Store token encrypted in file"""
        from cryptography.fernet import Fernet

        key = self._get_encryption_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(token.encode())

        token_file = self._get_token_path()
        with open(token_file, 'wb') as f:
            f.write(encrypted)
        token_file.chmod(0o600)

    def _retrieve_encrypted_token(self) -> str:
        """Retrieve encrypted token from file"""
        from cryptography.fernet import Fernet

        token_file = self._get_token_path()
        if not token_file.exists():
            raise FileNotFoundError("No stored token found")

        key = self._get_encryption_key()
        fernet = Fernet(key)

        with open(token_file, 'rb') as f:
            encrypted = f.read()

        return fernet.decrypt(encrypted).decode()


class ImprovedRateLimiter:
    """
    Enhanced rate limiter with tiered limits and exponential backoff
    """

    def __init__(self):
        """Initialize rate limiter"""
        # Different limits for different operation types
        self.limits: Dict[str, Dict[str, int]] = {
            'authentication': {'max': 5, 'window': 900},      # 5 per 15 min
            'expensive': {'max': 10, 'window': 600},          # 10 per 10 min
            'normal': {'max': 30, 'window': 60},              # 30 per min
            'cheap': {'max': 100, 'window': 60}               # 100 per min
        }

        self.request_history: Dict[str, List[float]] = {}
        self.failed_auth_attempts: Dict[str, List[float]] = {}
        self.lockouts: Dict[str, float] = {}
        self._lock = threading.Lock()

    def check_rate_limit(self, client_addr: str, operation_type: str = 'normal') -> bool:
        """
        Check if request is within rate limits

        Args:
            client_addr: Client address (IP:port)
            operation_type: Type of operation (authentication, expensive, normal, cheap)

        Returns:
            True if within limits, False otherwise

        Raises:
            SecurityException: If client is locked out
        """
        with self._lock:
            now = time.time()

            # Check if client is locked out
            if client_addr in self.lockouts:
                lockout_until = self.lockouts[client_addr]
                if now < lockout_until:
                    remaining = int(lockout_until - now)
                    raise SecurityException(
                        f"Client locked out. Try again in {remaining} seconds"
                    )
                else:
                    del self.lockouts[client_addr]

            # Get limits for operation type
            limits = self.limits.get(operation_type, self.limits['normal'])
            max_requests = limits['max']
            window_seconds = limits['window']

            # Initialize history
            key = f"{client_addr}:{operation_type}"
            if key not in self.request_history:
                self.request_history[key] = []

            # Remove old requests
            cutoff = now - window_seconds
            self.request_history[key] = [
                t for t in self.request_history[key] if t > cutoff
            ]

            # Check limit
            if len(self.request_history[key]) >= max_requests:
                return False

            # Add current request
            self.request_history[key].append(now)

            # Periodic cleanup
            if len(self.request_history) > 1000:
                self._cleanup_old_clients(now)

            return True

    def record_failed_auth(self, client_addr: str) -> None:
        """
        Record failed authentication attempt

        Args:
            client_addr: Client address
        """
        with self._lock:
            now = time.time()

            if client_addr not in self.failed_auth_attempts:
                self.failed_auth_attempts[client_addr] = []

            # Remove attempts older than 1 hour
            cutoff = now - 3600
            self.failed_auth_attempts[client_addr] = [
                t for t in self.failed_auth_attempts[client_addr] if t > cutoff
            ]

            # Add current failure
            self.failed_auth_attempts[client_addr].append(now)

            # Calculate lockout duration (exponential backoff)
            attempt_count = len(self.failed_auth_attempts[client_addr])

            if attempt_count >= 5:
                # Lockout duration: 2^(attempts-5) minutes, max 60 min
                lockout_duration = min(60 * 60, 60 * (2 ** (attempt_count - 5)))
                self.lockouts[client_addr] = now + lockout_duration

                if HAS_QGIS:
                    QgsMessageLog.logMessage(
                        f"Client {client_addr} locked out for {lockout_duration}s "
                        f"after {attempt_count} failed attempts",
                        "QGIS MCP Security",
                        Qgis.Critical
                    )

    def record_successful_auth(self, client_addr: str) -> None:
        """
        Clear failed attempts on successful auth

        Args:
            client_addr: Client address
        """
        with self._lock:
            if client_addr in self.failed_auth_attempts:
                del self.failed_auth_attempts[client_addr]
            if client_addr in self.lockouts:
                del self.lockouts[client_addr]

    def _cleanup_old_clients(self, now: float) -> None:
        """Remove clients with no recent requests"""
        cutoff = now - max(limit['window'] for limit in self.limits.values()) * 2

        to_remove = [
            key for key, requests in self.request_history.items()
            if not requests or max(requests) < cutoff
        ]

        for key in to_remove:
            del self.request_history[key]


class AuthenticationManager:
    """
    Enhanced authentication manager with secure token storage
    """

    def __init__(self):
        """Initialize authentication manager"""
        self.storage = SecureTokenStorage()
        self.authenticated_clients: Set[str] = set()
        self.session_tokens: Dict[str, str] = {}
        self._lock = threading.Lock()

        # Try to load existing token, or generate new one
        try:
            self.api_token = self.storage.retrieve_token()
        except FileNotFoundError:
            self.api_token = self._generate_token()
            self.storage.store_token(self.api_token)

    def _generate_token(self) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(32)

    def verify_token(self, client_addr: str, provided_token: str) -> bool:
        """
        Verify authentication token (constant-time comparison)

        Args:
            client_addr: Client address
            provided_token: Token provided by client

        Returns:
            True if token is valid
        """
        if hmac.compare_digest(self.api_token, provided_token):
            with self._lock:
                self.authenticated_clients.add(client_addr)
            return True
        return False

    def is_authenticated(self, client_addr: str) -> bool:
        """Check if client is authenticated"""
        with self._lock:
            return client_addr in self.authenticated_clients

    def logout(self, client_addr: str) -> None:
        """Remove client authentication"""
        with self._lock:
            self.authenticated_clients.discard(client_addr)

    def clear_all(self) -> None:
        """Clear all authenticated clients"""
        with self._lock:
            self.authenticated_clients.clear()
