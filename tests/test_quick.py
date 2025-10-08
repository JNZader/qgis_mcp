"""
Quick smoke tests to verify basic functionality

Run with: pytest tests/test_quick.py -v

These tests run quickly and verify that the basic security
components are working correctly.
"""

import pytest


def test_sandbox_import():
    """Test that sandbox module can be imported"""
    from security_improved import ImprovedCodeSandbox
    sandbox = ImprovedCodeSandbox()
    assert sandbox is not None


def test_sandbox_basic_validation():
    """Test basic code validation"""
    from security_improved import ImprovedCodeSandbox
    sandbox = ImprovedCodeSandbox()

    # Valid code should pass
    sandbox.validate_code("x = 1 + 2")

    # Dangerous code should fail
    from security_improved import SecurityException
    with pytest.raises(SecurityException):
        sandbox.validate_code("import os")


def test_path_validator_import():
    """Test that path validator can be imported"""
    from security_improved import EnhancedPathValidator
    validator = EnhancedPathValidator()
    assert validator is not None


def test_path_validator_basic():
    """Test basic path validation"""
    from security_improved import EnhancedPathValidator, SecurityException

    validator = EnhancedPathValidator()

    # Path traversal should be blocked
    with pytest.raises(SecurityException):
        validator.validate_path("../../../etc/passwd")


def test_rate_limiter_import():
    """Test that rate limiter can be imported"""
    from security_improved import ImprovedRateLimiter
    limiter = ImprovedRateLimiter()
    assert limiter is not None


def test_rate_limiter_basic():
    """Test basic rate limiting"""
    from security_improved import ImprovedRateLimiter

    limiter = ImprovedRateLimiter()
    client = "127.0.0.1:12345"

    # Should allow first request
    assert limiter.check_rate_limit(client, 'normal') is True


def test_auth_manager_import():
    """Test that auth manager can be imported"""
    from security_improved import AuthenticationManager
    manager = AuthenticationManager()
    assert manager is not None


def test_auth_manager_basic():
    """Test basic authentication"""
    from security_improved import AuthenticationManager

    manager = AuthenticationManager()
    token = manager.api_token
    client = "127.0.0.1:12346"

    # Valid token should work
    assert manager.verify_token(client, token) is True

    # Invalid token should fail
    assert manager.verify_token(client, "wrong_token") is False


def test_protocol_handler_import():
    """Test that protocol handler can be imported"""
    from protocol import ProtocolHandler
    handler = ProtocolHandler()
    assert handler is not None


def test_protocol_handler_basic():
    """Test basic protocol operations"""
    from protocol import ProtocolHandler

    handler = ProtocolHandler(use_msgpack=False, validate_schema=True)

    message = {'type': 'ping', 'id': 'msg_001'}

    # Should serialize and deserialize
    data = handler.serialize(message)
    result = handler.deserialize(data)

    assert result == message


def test_tls_handler_import():
    """Test that TLS handler can be imported"""
    try:
        from tls_handler import TLSHandler
        # TLS handler might not be available without PyOpenSSL
    except ImportError:
        pytest.skip("PyOpenSSL not available")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
