"""
Penetration testing scenarios

Tests cover:
- Code injection attacks
- Path traversal attacks
- Authentication bypass attempts
- Rate limiting bypass attempts
- Buffer overflow attacks
- Protocol manipulation
- Timing attacks
- Privilege escalation attempts
"""

import pytest
import time
import socket


@pytest.mark.security
class TestCodeInjectionAttacks:
    """Test resistance to code injection attacks"""

    def test_eval_injection_blocked(self, sandbox, malicious_python_codes):
        """Test that eval injection is blocked"""
        from security_improved import SecurityException

        for malicious_code in malicious_python_codes:
            with pytest.raises(SecurityException):
                sandbox.validate_code(malicious_code)

    def test_import_injection_blocked(self, sandbox):
        """Test that import injection is blocked"""
        from security_improved import SecurityException

        injection_attempts = [
            "__import__('os').system('ls')",
            "getattr(__builtins__, '__import__')('os')",
            "globals()['__builtins__']['__import__']('os')",
            "[i for i in ().__class__.__bases__[0].__subclasses__() if i.__name__ == 'Popen'][0]",
        ]

        for attempt in injection_attempts:
            with pytest.raises(SecurityException):
                sandbox.validate_code(attempt)

    def test_attribute_access_injection_blocked(self, sandbox):
        """Test that attribute access injection is blocked"""
        from security_improved import SecurityException

        attempts = [
            "[].__class__.__mro__[1].__subclasses__()",
            "().__class__.__bases__[0].__subclasses__()",
            "object.__subclasses__()",
            "''.__class__.__mro__[1].__subclasses__()",
        ]

        for attempt in attempts:
            with pytest.raises(SecurityException):
                sandbox.validate_code(attempt)

    def test_lambda_injection_blocked(self, sandbox):
        """Test that lambda injection is blocked"""
        from security_improved import SecurityException

        attempts = [
            "(lambda: __import__('os'))() ",
            "(lambda: eval('1+1'))()",
            "[x for x in (lambda: __import__('os'))()],",
        ]

        for attempt in attempts:
            with pytest.raises(SecurityException):
                sandbox.validate_code(attempt)


@pytest.mark.security
class TestPathTraversalAttacks:
    """Test resistance to path traversal attacks"""

    def test_all_traversal_attempts_blocked(self, path_validator, path_traversal_attempts):
        """Test that all path traversal attempts are blocked"""
        from security_improved import SecurityException

        for attempt in path_traversal_attempts:
            with pytest.raises(SecurityException):
                path_validator.validate_path(attempt)

    def test_encoded_traversal_blocked(self, path_validator):
        """Test that encoded path traversal is blocked"""
        from security_improved import SecurityException

        encoded_attempts = [
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # ..%2f..%2fetc%2fpasswd
            "..%252f..%252f..%252fetc%252fpasswd",  # Double encoded
            "%2e%2e\\%2e%2e\\etc\\passwd",  # Mixed encoding
        ]

        for attempt in encoded_attempts:
            with pytest.raises(SecurityException):
                path_validator.validate_path(attempt)

    def test_symlink_attack_blocked(self, path_validator, temp_dir):
        """Test that symlink attacks are blocked"""
        import os
        from security_improved import SecurityException

        if os.name == 'nt':
            pytest.skip("Symlink test for Unix-like systems")

        # Try to create symlink to sensitive file
        link_path = temp_dir / "evil_link"

        try:
            link_path.symlink_to("/etc/passwd")

            # Should be blocked (resolves outside allowed directories)
            with pytest.raises(SecurityException):
                path_validator.validate_path(str(link_path))
        except OSError:
            pytest.skip("Cannot create symlink")

    def test_unicode_traversal_blocked(self, path_validator):
        """Test that Unicode normalization doesn't allow traversal"""
        from security_improved import SecurityException

        # Unicode variations of '..'
        unicode_attempts = [
            "\uff0e\uff0e/etc/passwd",  # Fullwidth periods
            "..\u2215etc\u2215passwd",  # Division slash
        ]

        for attempt in unicode_attempts:
            with pytest.raises(SecurityException):
                path_validator.validate_path(attempt)


@pytest.mark.security
class TestAuthenticationBypassAttempts:
    """Test resistance to authentication bypass"""

    def test_empty_token_bypass_blocked(self, auth_manager):
        """Test that empty token doesn't bypass auth"""
        client = "127.0.0.1:70001"

        result = auth_manager.verify_token(client, "")
        assert result is False
        assert auth_manager.is_authenticated(client) is False

    def test_null_byte_injection_blocked(self, auth_manager):
        """Test that null byte injection doesn't work"""
        client = "127.0.0.1:70002"
        token = auth_manager.api_token

        # Try token with null byte
        malicious_token = token + "\x00"
        result = auth_manager.verify_token(client, malicious_token)
        assert result is False

    def test_timing_attack_resistance(self, auth_manager, assert_secure_timing):
        """Test resistance to timing attacks"""
        token = auth_manager.api_token
        client = "127.0.0.1:70003"

        # Create wrong token of same length
        wrong_token = "x" * len(token)

        def verify_correct():
            auth_manager.verify_token(client, token)

        def verify_wrong():
            auth_manager.verify_token(client, wrong_token)

        # Timing should be constant
        assert_secure_timing(verify_correct, verify_wrong, max_ratio=3.0)

    def test_sql_injection_in_token(self, auth_manager):
        """Test that SQL injection in token doesn't cause issues"""
        client = "127.0.0.1:70004"

        sql_injection_tokens = [
            "' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--",
            "1' OR '1' = '1')) /*",
        ]

        for malicious_token in sql_injection_tokens:
            result = auth_manager.verify_token(client, malicious_token)
            assert result is False

    def test_token_length_manipulation(self, auth_manager):
        """Test that token length manipulation doesn't bypass auth"""
        token = auth_manager.api_token
        client = "127.0.0.1:70005"

        # Try various length manipulations
        attempts = [
            token + "extra",  # Too long
            token[:-5],  # Too short
            token * 2,  # Doubled
            token[:len(token)//2],  # Half
        ]

        for attempt in attempts:
            result = auth_manager.verify_token(client, attempt)
            assert result is False


@pytest.mark.security
class TestRateLimitBypassAttempts:
    """Test resistance to rate limit bypass"""

    def test_different_ports_counted_separately(self, rate_limiter):
        """Test that different ports from same IP are counted separately"""
        # This is correct behavior - each connection is unique
        base_ip = "127.0.0.1"

        for port in range(71001, 71011):
            client = f"{base_ip}:{port}"
            result = rate_limiter.check_rate_limit(client, 'normal')
            # Each should be allowed (they're different clients)
            assert result is True

    def test_ip_spoofing_not_possible(self, rate_limiter):
        """Test that IP spoofing doesn't bypass rate limits"""
        # Rate limiter uses client identifier as provided
        # In real server, this comes from socket.getpeername()
        # which cannot be spoofed
        client = "127.0.0.1:71012"

        # Fill up the limit
        for _ in range(30):
            rate_limiter.check_rate_limit(client, 'normal')

        # Should be rate limited
        assert rate_limiter.check_rate_limit(client, 'normal') is False

        # Trying with "different" IP (but same client identifier) won't help
        assert rate_limiter.check_rate_limit(client, 'normal') is False

    def test_lockout_cannot_be_bypassed(self, rate_limiter):
        """Test that lockout cannot be bypassed"""
        from security_improved import SecurityException

        client = "127.0.0.1:71013"

        # Trigger lockout
        for _ in range(5):
            rate_limiter.record_failed_auth(client)

        # Should be locked out for all operation types
        for op_type in ['authentication', 'expensive', 'normal', 'cheap']:
            with pytest.raises(SecurityException, match="locked out"):
                rate_limiter.check_rate_limit(client, op_type)


@pytest.mark.security
class TestBufferOverflowAttacks:
    """Test resistance to buffer overflow attacks"""

    def test_message_size_limit_enforced(self, protocol_handler):
        """Test that message size limits are enforced"""
        from protocol import ProtocolException

        # Try to create oversized message
        huge_data = "x" * (protocol_handler.MAX_MESSAGE_SIZE + 1)
        message = {'type': 'ping', 'id': 'msg_001', 'data': huge_data}

        with pytest.raises(ProtocolException, match="too large"):
            protocol_handler.pack_message(message)

    def test_buffer_overflow_protection(self, buffered_protocol):
        """Test buffered protocol overflow protection"""
        from protocol import ProtocolException

        # Try to overflow buffer
        huge_chunk = b"x" * (buffered_protocol.MAX_MESSAGE_SIZE + 1)

        with pytest.raises(ProtocolException, match="Buffer overflow"):
            buffered_protocol.feed_data(huge_chunk)

    def test_incremental_buffer_overflow(self, buffered_protocol):
        """Test protection against incremental buffer overflow"""
        from protocol import ProtocolException

        chunk_size = 1000000  # 1MB chunks
        chunks_to_overflow = (buffered_protocol.MAX_MESSAGE_SIZE // chunk_size) + 2

        # Try to incrementally overflow
        with pytest.raises(ProtocolException, match="Buffer overflow"):
            for _ in range(chunks_to_overflow):
                buffered_protocol.feed_data(b"x" * chunk_size)

    def test_code_length_limit_enforced(self, sandbox):
        """Test that code length limits are enforced"""
        from security_improved import SecurityException

        huge_code = "x = 1\n" * 100000  # Very long code

        with pytest.raises(SecurityException, match="exceeds maximum length"):
            sandbox.validate_code(huge_code)


@pytest.mark.security
class TestProtocolManipulation:
    """Test resistance to protocol manipulation"""

    def test_invalid_message_length_rejected(self, buffered_protocol):
        """Test that invalid message lengths are rejected"""
        from protocol import ProtocolException
        import struct

        # Create header with impossible size
        invalid_size = buffered_protocol.MAX_MESSAGE_SIZE + 1
        header = struct.pack(buffered_protocol.MESSAGE_HEADER_FORMAT, invalid_size)

        buffered_protocol.feed_data(header)

        with pytest.raises(ProtocolException, match="exceeds limit"):
            buffered_protocol.try_read_message()

    def test_zero_length_message_rejected(self, buffered_protocol):
        """Test that zero-length messages are rejected"""
        from protocol import ProtocolException
        import struct

        header = struct.pack(buffered_protocol.MESSAGE_HEADER_FORMAT, 0)

        buffered_protocol.feed_data(header)

        with pytest.raises(ProtocolException, match="zero length"):
            buffered_protocol.try_read_message()

    def test_malformed_json_rejected(self, buffered_protocol):
        """Test that malformed JSON is rejected"""
        from protocol import ProtocolException
        import struct

        malformed_json = b'{"type": invalid, "id": "msg_001"}'
        header = struct.pack(
            buffered_protocol.MESSAGE_HEADER_FORMAT,
            len(malformed_json)
        )

        buffered_protocol.feed_data(header + malformed_json)

        with pytest.raises(ProtocolException):
            buffered_protocol.try_read_message()

    def test_schema_violation_rejected(self, protocol_handler):
        """Test that schema violations are rejected"""
        from protocol import ProtocolException

        invalid_messages = [
            {'type': 'ping'},  # Missing id
            {'id': 'msg_001'},  # Missing type
            {'type': '', 'id': 'msg_001'},  # Empty type
            {'type': 'ping', 'id': 'msg_001', 'extra': 'field'},  # Extra field
        ]

        for msg in invalid_messages:
            with pytest.raises(ProtocolException):
                protocol_handler.pack_message(msg)


@pytest.mark.security
class TestDenialOfServiceResistance:
    """Test resistance to DoS attacks"""

    def test_rapid_connections_handled(self, rate_limiter):
        """Test that rapid connections are rate limited"""
        client = "127.0.0.1:72001"

        # Try to make very many requests very quickly
        successful = 0
        for _ in range(200):
            if rate_limiter.check_rate_limit(client, 'cheap'):
                successful += 1

        # Should have hit the limit (100 for cheap operations)
        assert successful == 100

    def test_slowloris_attack_timeout(self, socket_pair):
        """Test that slow data transmission times out"""
        server_sock, client_sock = socket_pair

        # Set timeout on server
        server_sock.settimeout(1.0)

        # Send data very slowly (partial message)
        client_sock.send(b"\x00")  # Just one byte

        # Server should timeout trying to receive complete message
        from protocol import ProtocolHandler
        handler = ProtocolHandler()

        with pytest.raises((TimeoutError, socket.timeout)):
            handler.receive_message(server_sock, timeout=1.0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
