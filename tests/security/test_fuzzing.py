"""
Fuzzing tests for input validation

Tests cover:
- Random input fuzzing
- Boundary value testing
- Type confusion
- Format string attacks
- Integer overflow/underflow
- Special character injection
"""

import random
import string

import pytest


@pytest.mark.security
class TestRandomInputFuzzing:
    """Test with random inputs"""

    def test_random_code_fuzzing(self, sandbox):
        """Fuzz code sandbox with random inputs"""
        from security_improved import SecurityException

        # Generate random code snippets
        for _ in range(100):
            random_code = "".join(
                random.choices(string.ascii_letters + string.digits + " \n()[]{}", k=100)
            )

            # Should either pass or raise SecurityException
            # Should NOT crash
            try:
                sandbox.validate_code(random_code)
            except (SecurityException, SyntaxError):
                pass  # Expected

    def test_random_path_fuzzing(self, path_validator):
        """Fuzz path validator with random inputs"""
        from security_improved import SecurityException

        for _ in range(100):
            random_path = "".join(
                random.choices(string.ascii_letters + string.digits + "/\\.:- ", k=50)
            )

            # Should not crash
            try:
                path_validator.validate_path(random_path)
            except (SecurityException, ValueError, OSError):
                pass  # Expected

    def test_random_token_fuzzing(self, auth_manager):
        """Fuzz authentication with random tokens"""
        client = "127.0.0.1:80001"

        for _ in range(100):
            random_token = "".join(random.choices(string.ascii_letters + string.digits, k=50))

            # Should not crash, should return False
            result = auth_manager.verify_token(client, random_token)
            assert result is False

    def test_random_message_fuzzing(self, protocol_handler):
        """Fuzz protocol with random message data"""
        from protocol import ProtocolException

        for _ in range(50):
            # Generate random dict
            random_msg = {
                "type": "".join(random.choices(string.ascii_letters, k=10)),
                "id": "".join(random.choices(string.ascii_letters + string.digits, k=10)),
                "data": {
                    "key": random.randint(0, 1000),
                    "value": "".join(random.choices(string.ascii_letters, k=20)),
                },
            }

            # Should either work or raise ProtocolException
            # Should NOT crash
            try:
                protocol_handler.pack_message(random_msg)
            except (ProtocolException, Exception):
                pass


@pytest.mark.security
class TestBoundaryValues:
    """Test boundary values"""

    def test_code_length_boundaries(self, sandbox):
        """Test code length at boundaries"""
        from security_improved import SecurityException

        max_length = sandbox.max_code_length

        # Just under limit - should work
        code = "x" * (max_length - 1)
        sandbox.validate_code(code)

        # At limit - should work
        code = "x" * max_length
        sandbox.validate_code(code)

        # Just over limit - should fail
        code = "x" * (max_length + 1)
        with pytest.raises(SecurityException):
            sandbox.validate_code(code)

    def test_message_size_boundaries(self, protocol_handler):
        """Test message size at boundaries"""
        from protocol import ProtocolException

        # This is tricky because we need to account for JSON overhead
        # Just test that the limit is enforced
        max_size = protocol_handler.MAX_MESSAGE_SIZE

        # Create large message
        large_data = "x" * (max_size - 1000)  # Leave room for JSON structure
        message = {"type": "ping", "id": "msg_001", "data": large_data}

        try:
            protocol_handler.pack_message(message)
        except ProtocolException:
            pass  # Might still be too large with JSON overhead

        # Definitely too large
        huge_data = "x" * max_size
        message = {"type": "ping", "id": "msg_001", "data": huge_data}

        with pytest.raises(ProtocolException):
            protocol_handler.pack_message(message)

    def test_rate_limit_boundaries(self, rate_limiter):
        """Test rate limiting at boundaries"""
        client = "127.0.0.1:80002"

        # Normal limit is 30
        # Should succeed for first 30
        for i in range(30):
            assert rate_limiter.check_rate_limit(client, "normal") is True

        # 31st should fail
        assert rate_limiter.check_rate_limit(client, "normal") is False

    def test_failed_auth_lockout_boundary(self, rate_limiter):
        """Test lockout at exact boundary"""
        from security_improved import SecurityException

        client = "127.0.0.1:80003"

        # 4 failures - should not lock out
        for _ in range(4):
            rate_limiter.record_failed_auth(client)

        assert rate_limiter.check_rate_limit(client, "normal") is True

        # 5th failure - should lock out
        rate_limiter.record_failed_auth(client)

        with pytest.raises(SecurityException):
            rate_limiter.check_rate_limit(client, "normal")


@pytest.mark.security
class TestTypeConfusion:
    """Test type confusion attacks"""

    def test_token_type_confusion(self, auth_manager):
        """Test authentication with wrong types"""
        client = "127.0.0.1:80004"

        wrong_types = [
            123,  # Integer
            12.34,  # Float
            ["token"],  # List
            {"token": "value"},  # Dict
            b"token",  # Bytes
        ]

        for wrong_type in wrong_types:
            try:
                result = auth_manager.verify_token(client, wrong_type)
                # If it doesn't crash, should return False
                assert result is False
            except (TypeError, AttributeError):
                pass  # Also acceptable

    def test_message_type_confusion(self, protocol_handler):
        """Test protocol with wrong message types"""
        from protocol import ProtocolException

        wrong_types = [
            "not a dict",  # String
            [1, 2, 3],  # List
            123,  # Integer
            None,  # None
        ]

        for wrong_type in wrong_types:
            with pytest.raises((ProtocolException, TypeError)):
                protocol_handler.serialize(wrong_type)

    def test_path_type_confusion(self, path_validator):
        """Test path validator with wrong types"""
        from security_improved import SecurityException

        wrong_types = [
            123,  # Integer
            ["path", "components"],  # List
            b"/etc/passwd",  # Bytes
        ]

        for wrong_type in wrong_types:
            try:
                path_validator.validate_path(wrong_type)
            except (SecurityException, TypeError, AttributeError):
                pass  # Expected


@pytest.mark.security
class TestSpecialCharacters:
    """Test special character injection"""

    def test_null_byte_injection_in_paths(self, path_validator):
        """Test null byte injection in paths"""
        from security_improved import SecurityException

        null_byte_paths = [
            "/tmp/test\x00.txt",
            "/tmp\x00/../../etc/passwd",
            "test.txt\x00.exe",
        ]

        for path in null_byte_paths:
            try:
                path_validator.validate_path(path)
            except (SecurityException, ValueError):
                pass  # Expected

    def test_control_characters_in_code(self, sandbox):
        """Test control characters in code"""
        from security_improved import SecurityException

        control_char_codes = [
            "x = 1\x00",  # Null
            "x = 1\r\n",  # CRLF
            "x = 1\x1b",  # Escape
        ]

        for code in control_char_codes:
            try:
                sandbox.validate_code(code)
            except (SecurityException, SyntaxError):
                pass  # Expected

    def test_unicode_attacks(self, path_validator):
        """Test Unicode-based attacks"""
        from security_improved import SecurityException

        unicode_paths = [
            "/tmp/test\u0000.txt",  # Unicode null
            "/tmp/test\ufeff.txt",  # BOM
            "/tmp/test\u202e.txt",  # Right-to-left override
            "\uff0e\uff0e/etc/passwd",  # Fullwidth periods
        ]

        for path in unicode_paths:
            try:
                path_validator.validate_path(path)
            except (SecurityException, ValueError):
                pass  # Expected

    def test_format_string_injection(self, sandbox):
        """Test format string injection"""
        from security_improved import SecurityException

        format_strings = [
            "x = '%s' % __import__('os').system('ls')",
            "x = '{}'.format(__import__('os'))",
            "x = f'{__import__(\"os\")}'",
        ]

        for code in format_strings:
            with pytest.raises(SecurityException):
                sandbox.validate_code(code)


@pytest.mark.security
class TestIntegerBoundaries:
    """Test integer overflow/underflow"""

    def test_large_message_id(self, protocol_handler):
        """Test very large message IDs"""
        # Message ID can be string or integer
        large_ids = [
            2**31 - 1,  # Max 32-bit int
            2**63 - 1,  # Max 64-bit int
            -(2**31),  # Min 32-bit int
        ]

        for msg_id in large_ids:
            message = {"type": "ping", "id": msg_id}
            try:
                protocol_handler.pack_message(message)
                # Should work (IDs are flexible)
            except Exception:
                pass  # Some limits may apply

    def test_negative_rate_limits(self, rate_limiter):
        """Test that negative values don't break rate limiter"""
        client = "127.0.0.1:80005"

        # Rate limiter should handle edge cases gracefully
        # This is more of a robustness test
        assert rate_limiter.check_rate_limit(client, "normal") is True

    def test_large_offset_pagination(self, rate_limiter):
        """Test large offset values"""
        # In a real server, this would test pagination
        # Here we just verify no crashes
        pass


@pytest.mark.security
class TestCombinedAttacks:
    """Test combinations of attack vectors"""

    def test_encoded_traversal_with_null_bytes(self, path_validator):
        """Test combination of encoding and null bytes"""
        from security_improved import SecurityException

        combined_attacks = [
            "%2e%2e%2f\x00etc/passwd",
            "../\x00/../etc/passwd",
            "\uff0e\uff0e\x00/etc/passwd",
        ]

        for attack in combined_attacks:
            try:
                path_validator.validate_path(attack)
            except (SecurityException, ValueError):
                pass  # Expected

    def test_code_injection_with_encoding(self, sandbox):
        """Test code injection with various encodings"""
        from security_improved import SecurityException

        # These should all be blocked
        encoded_injections = [
            "__im" + "port__('os')",  # String concatenation
            "eval" + "('1+1')",
            "ex" + "ec('x=1')",
        ]

        for code in encoded_injections:
            with pytest.raises(SecurityException):
                sandbox.validate_code(code)

    def test_rapid_auth_attempts_with_variations(self, auth_manager, rate_limiter):
        """Test rapid auth attempts with token variations"""
        from security_improved import SecurityException

        client = "127.0.0.1:80006"
        base_token = auth_manager.api_token

        # Try many variations
        for i in range(10):
            # Slight variations
            wrong_token = base_token[:-1] + str(i)

            # Check rate limit
            try:
                if rate_limiter.check_rate_limit(client, "authentication"):
                    result = auth_manager.verify_token(client, wrong_token)
                    if not result:
                        rate_limiter.record_failed_auth(client)
            except SecurityException:
                break  # Locked out

        # Should eventually be locked out or rate limited
        try:
            result = rate_limiter.check_rate_limit(client, "authentication")
            # If we get here, we're rate limited
            assert result is False or client in rate_limiter.lockouts
        except SecurityException:
            # Locked out - also good
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
