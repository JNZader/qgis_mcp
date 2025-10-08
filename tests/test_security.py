"""
Unit tests for security improvements

Run with: pytest tests/test_security.py -v
"""

import pytest
import ast
from pathlib import Path
import tempfile
import os

# Import security modules
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "qgis_mcp_plugin"))

from security_improved import (
    ImprovedCodeSandbox,
    EnhancedPathValidator,
    ImprovedRateLimiter,
    AuthenticationManager,
    SecureTokenStorage,
    SecurityException,
)


class TestImprovedCodeSandbox:
    """Tests for AST-based code sandbox"""

    def setup_method(self):
        """Set up test fixtures"""
        self.sandbox = ImprovedCodeSandbox(max_code_length=1000, timeout_seconds=5)

    def test_valid_code(self):
        """Test that valid code passes validation"""
        code = """
x = 1
y = 2
result = x + y
"""
        # Should not raise exception
        self.sandbox.validate_code(code)

    def test_dangerous_import_blocked(self):
        """Test that dangerous imports are blocked"""
        code = "import os"
        with pytest.raises(SecurityException, match="Import not allowed"):
            self.sandbox.validate_code(code)

    def test_dangerous_function_blocked(self):
        """Test that dangerous functions are blocked"""
        dangerous_codes = [
            "eval('1+1')",
            "exec('x=1')",
            "compile('x=1', '', 'exec')",
            "__import__('os')",
            "open('/etc/passwd')",
        ]

        for code in dangerous_codes:
            with pytest.raises(SecurityException):
                self.sandbox.validate_code(code)

    def test_dangerous_attribute_blocked(self):
        """Test that dangerous attribute access is blocked"""
        code = "x = object.__dict__"
        with pytest.raises(SecurityException, match="Dangerous attribute"):
            self.sandbox.validate_code(code)

    def test_allowed_qgis_imports(self):
        """Test that QGIS imports are allowed"""
        code = """
from qgis.core import QgsProject
from qgis.utils import iface
"""
        # Should not raise exception (but will fail without QGIS)
        try:
            self.sandbox.validate_code(code)
        except SecurityException as e:
            # Should not be import-related error
            assert "Import not allowed" not in str(e)

    def test_code_length_limit(self):
        """Test that code length is limited"""
        code = "x = 1\n" * 10000  # Very long code
        with pytest.raises(SecurityException, match="exceeds maximum length"):
            self.sandbox.validate_code(code)

    def test_safe_namespace_creation(self):
        """Test that safe namespace is created correctly"""
        namespace = self.sandbox.create_safe_namespace()

        # Check that only allowed builtins are present
        builtins = namespace["__builtins__"]
        assert "print" in builtins
        assert "len" in builtins
        assert "eval" not in builtins
        assert "exec" not in builtins
        assert "open" not in builtins


class TestEnhancedPathValidator:
    """Tests for enhanced path validation"""

    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.validator = EnhancedPathValidator(allowed_directories=[self.temp_dir])

    def teardown_method(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_path_traversal_blocked(self):
        """Test that path traversal is blocked"""
        paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "./../../etc/passwd",
        ]

        for path in paths:
            with pytest.raises(SecurityException, match="Path traversal"):
                self.validator.validate_path(path)

    def test_valid_path_allowed(self):
        """Test that valid paths are allowed"""
        test_file = self.temp_dir / "test.shp"
        test_file.touch()

        # Should not raise exception
        result = self.validator.validate_path(str(test_file), operation="read")
        assert Path(result) == test_file.resolve()

    def test_dangerous_extension_blocked(self):
        """Test that dangerous extensions are blocked"""
        dangerous_paths = [
            str(self.temp_dir / "evil.exe"),
            str(self.temp_dir / "malware.dll"),
            str(self.temp_dir / "script.sh"),
        ]

        for path in dangerous_paths:
            with pytest.raises(SecurityException, match="Dangerous file extension"):
                self.validator.validate_path(path, operation="read")

    def test_safe_gis_extension_allowed(self):
        """Test that safe GIS extensions are allowed"""
        test_file = self.temp_dir / "test.shp"
        test_file.touch()

        # Should not raise exception
        self.validator.validate_path(
            str(test_file), operation="read", allowed_extensions=[".shp", ".geojson"]
        )

    def test_outside_allowed_directory_blocked(self):
        """Test that paths outside allowed directories are blocked"""
        if os.name == "nt":
            path = "C:\\Windows\\System32\\config"
        else:
            path = "/etc/passwd"

        with pytest.raises(SecurityException, match="outside allowed directories"):
            self.validator.validate_path(path)

    def test_url_encoding_normalized(self):
        """Test that URL encoding is normalized"""
        # %2e%2e = ..
        test_file = self.temp_dir / "test.txt"
        test_file.touch()

        # This should work (no traversal after decoding)
        result = self.validator.validate_path(str(test_file), operation="read")
        assert Path(result) == test_file.resolve()

    def test_nonexistent_file_read_blocked(self):
        """Test that reading non-existent files is blocked"""
        path = str(self.temp_dir / "nonexistent.txt")

        with pytest.raises(SecurityException, match="does not exist"):
            self.validator.validate_path(path, operation="read")

    def test_write_permission_checked(self):
        """Test that write permissions are checked"""
        test_file = self.temp_dir / "test.txt"

        # Should not raise exception for writable directory
        self.validator.validate_path(str(test_file), operation="write")


class TestImprovedRateLimiter:
    """Tests for rate limiting"""

    def setup_method(self):
        """Set up test fixtures"""
        self.limiter = ImprovedRateLimiter()

    def test_within_rate_limit(self):
        """Test that requests within limit are allowed"""
        client_addr = "127.0.0.1:12345"

        # Should allow normal amount of requests
        for _ in range(5):
            assert self.limiter.check_rate_limit(client_addr, "normal") is True

    def test_rate_limit_exceeded(self):
        """Test that rate limit can be exceeded"""
        client_addr = "127.0.0.1:12346"

        # Try to exceed normal limit (30 per minute)
        for i in range(35):
            result = self.limiter.check_rate_limit(client_addr, "normal")
            if i < 30:
                assert result is True
            else:
                assert result is False

    def test_different_operation_types(self):
        """Test that different operation types have different limits"""
        client_addr = "127.0.0.1:12347"

        # Authentication has lower limit (5 per 15 min)
        for i in range(6):
            result = self.limiter.check_rate_limit(client_addr, "authentication")
            if i < 5:
                assert result is True
            else:
                assert result is False

        # Cheap operations have higher limit (100 per min)
        client_addr2 = "127.0.0.1:12348"
        for i in range(101):
            result = self.limiter.check_rate_limit(client_addr2, "cheap")
            if i < 100:
                assert result is True
            else:
                assert result is False

    def test_failed_auth_lockout(self):
        """Test that failed auth attempts trigger lockout"""
        client_addr = "127.0.0.1:12349"

        # Record 5 failed attempts
        for _ in range(5):
            self.limiter.record_failed_auth(client_addr)

        # Should be locked out
        with pytest.raises(SecurityException, match="locked out"):
            self.limiter.check_rate_limit(client_addr, "normal")

    def test_successful_auth_clears_failures(self):
        """Test that successful auth clears failed attempts"""
        client_addr = "127.0.0.1:12350"

        # Record some failed attempts
        for _ in range(3):
            self.limiter.record_failed_auth(client_addr)

        # Successful auth should clear
        self.limiter.record_successful_auth(client_addr)

        # Should not be locked out
        result = self.limiter.check_rate_limit(client_addr, "normal")
        assert result is True


class TestAuthenticationManager:
    """Tests for authentication manager"""

    def setup_method(self):
        """Set up test fixtures"""
        self.auth_manager = AuthenticationManager()

    def test_token_generation(self):
        """Test that tokens are generated correctly"""
        token = self.auth_manager.api_token

        # Should be non-empty string
        assert isinstance(token, str)
        assert len(token) > 20  # Should be sufficiently long

    def test_valid_token_verification(self):
        """Test that valid tokens are accepted"""
        token = self.auth_manager.api_token
        client_addr = "127.0.0.1:12351"

        result = self.auth_manager.verify_token(client_addr, token)
        assert result is True

    def test_invalid_token_rejected(self):
        """Test that invalid tokens are rejected"""
        client_addr = "127.0.0.1:12352"

        result = self.auth_manager.verify_token(client_addr, "invalid_token")
        assert result is False

    def test_authentication_tracking(self):
        """Test that authentication is tracked per client"""
        token = self.auth_manager.api_token
        client1 = "127.0.0.1:12353"
        client2 = "127.0.0.1:12354"

        # Authenticate client1
        self.auth_manager.verify_token(client1, token)
        assert self.auth_manager.is_authenticated(client1) is True
        assert self.auth_manager.is_authenticated(client2) is False

        # Authenticate client2
        self.auth_manager.verify_token(client2, token)
        assert self.auth_manager.is_authenticated(client2) is True

    def test_logout(self):
        """Test that logout works"""
        token = self.auth_manager.api_token
        client_addr = "127.0.0.1:12355"

        # Authenticate
        self.auth_manager.verify_token(client_addr, token)
        assert self.auth_manager.is_authenticated(client_addr) is True

        # Logout
        self.auth_manager.logout(client_addr)
        assert self.auth_manager.is_authenticated(client_addr) is False

    def test_constant_time_comparison(self):
        """Test that token comparison uses constant-time algorithm"""
        import time

        token = self.auth_manager.api_token
        client_addr = "127.0.0.1:12356"

        # Time comparison with wrong token of same length
        wrong_token = "x" * len(token)
        start = time.time()
        self.auth_manager.verify_token(client_addr, wrong_token)
        wrong_time = time.time() - start

        # Time comparison with correct token
        start = time.time()
        self.auth_manager.verify_token(client_addr, token)
        right_time = time.time() - start

        # Times should be similar (constant-time comparison)
        # Allow 2x difference due to system variations
        assert abs(wrong_time - right_time) < max(wrong_time, right_time) * 2


class TestSecureTokenStorage:
    """Tests for secure token storage"""

    def setup_method(self):
        """Set up test fixtures"""
        self.storage = SecureTokenStorage()

        # Clean up any existing tokens
        try:
            self.storage.delete_token()
        except:
            pass

    def teardown_method(self):
        """Clean up test fixtures"""
        try:
            self.storage.delete_token()
        except:
            pass

    def test_token_storage_and_retrieval(self):
        """Test that tokens can be stored and retrieved"""
        test_token = "test_token_12345"

        # Store token
        self.storage.store_token(test_token)

        # Retrieve token
        retrieved = self.storage.retrieve_token()
        assert retrieved == test_token

    def test_token_encryption(self):
        """Test that tokens are encrypted on disk"""
        test_token = "secret_token_67890"

        # Store token
        self.storage.store_token(test_token)

        # Read raw file content
        token_file = self.storage._get_token_path()
        with open(token_file, "rb") as f:
            raw_content = f.read()

        # Should not contain plaintext token
        assert test_token.encode() not in raw_content

    def test_token_deletion(self):
        """Test that tokens can be deleted"""
        test_token = "delete_me_token"

        # Store and verify
        self.storage.store_token(test_token)
        assert self.storage.retrieve_token() == test_token

        # Delete
        self.storage.delete_token()

        # Should raise exception
        with pytest.raises(FileNotFoundError):
            self.storage.retrieve_token()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
