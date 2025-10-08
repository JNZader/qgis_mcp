"""
Integration tests for Authentication Flow

Tests cover:
- Complete authentication workflow
- Token lifecycle
- Multi-client authentication
- Authentication persistence
- Failed authentication handling
- Rate limiting during auth
- Session management
"""

import pytest
import time


class TestAuthenticationFlow:
    """Test complete authentication flow"""

    def test_complete_auth_workflow(self, auth_manager, rate_limiter):
        """Test complete authentication workflow"""
        client = "127.0.0.1:30001"
        token = auth_manager.api_token

        # 1. Client starts unauthenticated
        assert auth_manager.is_authenticated(client) is False

        # 2. Client attempts authentication
        result = auth_manager.verify_token(client, token)
        assert result is True

        # 3. Client is now authenticated
        assert auth_manager.is_authenticated(client) is True

        # 4. Record successful auth in rate limiter
        rate_limiter.record_successful_auth(client)

        # 5. Client can make requests
        assert rate_limiter.check_rate_limit(client, "normal") is True

    def test_failed_auth_workflow(self, auth_manager, rate_limiter):
        """Test failed authentication workflow"""
        client = "127.0.0.1:30002"

        # 1. Client attempts auth with wrong token
        result = auth_manager.verify_token(client, "wrong_token")
        assert result is False

        # 2. Record failed auth
        rate_limiter.record_failed_auth(client)

        # 3. Client remains unauthenticated
        assert auth_manager.is_authenticated(client) is False

        # 4. Failed attempt is tracked
        assert client in rate_limiter.failed_auth_attempts

    def test_multiple_failed_auths_lead_to_lockout(self, auth_manager, rate_limiter):
        """Test that multiple failures lead to lockout"""
        client = "127.0.0.1:30003"

        # Try 5 times with wrong token
        for i in range(5):
            result = auth_manager.verify_token(client, "wrong_token")
            assert result is False
            rate_limiter.record_failed_auth(client)

        # Should be locked out
        from security_improved import SecurityException

        with pytest.raises(SecurityException, match="locked out"):
            rate_limiter.check_rate_limit(client, "normal")

    def test_successful_auth_after_failures(self, auth_manager, rate_limiter):
        """Test successful auth after some failures"""
        client = "127.0.0.1:30004"
        token = auth_manager.api_token

        # Fail a few times
        for i in range(3):
            auth_manager.verify_token(client, "wrong_token")
            rate_limiter.record_failed_auth(client)

        # Then succeed
        result = auth_manager.verify_token(client, token)
        assert result is True
        rate_limiter.record_successful_auth(client)

        # Should clear failures
        assert client not in rate_limiter.failed_auth_attempts

        # Should be authenticated
        assert auth_manager.is_authenticated(client) is True


class TestMultiClientAuthentication:
    """Test authentication with multiple clients"""

    def test_multiple_clients_separate_auth(self, auth_manager):
        """Test that multiple clients have separate authentication"""
        token = auth_manager.api_token
        client1 = "127.0.0.1:30005"
        client2 = "127.0.0.1:30006"
        client3 = "127.0.0.1:30007"

        # Authenticate only client1 and client3
        auth_manager.verify_token(client1, token)
        auth_manager.verify_token(client3, token)

        # Check states
        assert auth_manager.is_authenticated(client1) is True
        assert auth_manager.is_authenticated(client2) is False
        assert auth_manager.is_authenticated(client3) is True

    def test_logout_affects_only_one_client(self, auth_manager):
        """Test that logout affects only the specific client"""
        token = auth_manager.api_token
        client1 = "127.0.0.1:30008"
        client2 = "127.0.0.1:30009"

        # Authenticate both
        auth_manager.verify_token(client1, token)
        auth_manager.verify_token(client2, token)

        # Logout client1
        auth_manager.logout(client1)

        # Check states
        assert auth_manager.is_authenticated(client1) is False
        assert auth_manager.is_authenticated(client2) is True

    def test_clear_all_clients(self, auth_manager):
        """Test clearing all authenticated clients"""
        token = auth_manager.api_token
        clients = [f"127.0.0.1:{30010 + i}" for i in range(5)]

        # Authenticate all
        for client in clients:
            auth_manager.verify_token(client, token)

        # Verify all authenticated
        for client in clients:
            assert auth_manager.is_authenticated(client) is True

        # Clear all
        auth_manager.clear_all()

        # Verify all logged out
        for client in clients:
            assert auth_manager.is_authenticated(client) is False


class TestAuthenticationPersistence:
    """Test authentication token persistence"""

    def test_token_persists_across_manager_instances(self, token_storage):
        """Test that token persists across manager instances"""
        from security_improved import AuthenticationManager

        # Create first manager and store token
        manager1 = AuthenticationManager()
        token1 = manager1.api_token

        # Create second manager (should load same token)
        manager2 = AuthenticationManager()
        token2 = manager2.api_token

        assert token1 == token2

        # Cleanup
        token_storage.delete_token()

    def test_token_storage_encryption(self, token_storage):
        """Test that stored tokens are encrypted"""
        test_token = "secret_integration_token"

        # Store token
        token_storage.store_token(test_token)

        # Read raw file
        token_file = token_storage._get_token_path()
        with open(token_file, "rb") as f:
            raw_content = f.read()

        # Plaintext should not be in file
        assert test_token.encode() not in raw_content

        # But should retrieve correctly
        retrieved = token_storage.retrieve_token()
        assert retrieved == test_token


class TestRateLimitingDuringAuth:
    """Test rate limiting during authentication"""

    def test_auth_attempts_rate_limited(self, auth_manager, rate_limiter):
        """Test that authentication attempts are rate limited"""
        client = "127.0.0.1:30011"

        # Authentication has limit of 5 per 15 minutes
        for i in range(6):
            result = rate_limiter.check_rate_limit(client, "authentication")
            if i < 5:
                assert result is True
            else:
                assert result is False

    def test_failed_auth_and_rate_limit_interaction(self, auth_manager, rate_limiter):
        """Test interaction between failed auth and rate limiting"""
        client = "127.0.0.1:30012"

        # Try to authenticate many times (wrong token)
        for i in range(10):
            # Check rate limit
            try:
                if not rate_limiter.check_rate_limit(client, "authentication"):
                    break

                # Attempt authentication
                auth_manager.verify_token(client, "wrong_token")
                rate_limiter.record_failed_auth(client)
            except:
                break

        # Should have hit either rate limit or lockout
        from security_improved import SecurityException

        try:
            result = rate_limiter.check_rate_limit(client, "authentication")
            # If we got here, we hit rate limit but not lockout yet
            assert result is False or client in rate_limiter.lockouts
        except SecurityException:
            # Hit lockout instead
            pass


class TestSessionManagement:
    """Test session management"""

    def test_session_lifecycle(self, auth_manager):
        """Test complete session lifecycle"""
        client = "127.0.0.1:30013"
        token = auth_manager.api_token

        # 1. Start: Unauthenticated
        assert auth_manager.is_authenticated(client) is False

        # 2. Authenticate
        auth_manager.verify_token(client, token)
        assert auth_manager.is_authenticated(client) is True

        # 3. Do work (represented by checking auth status)
        for _ in range(5):
            assert auth_manager.is_authenticated(client) is True

        # 4. Logout
        auth_manager.logout(client)
        assert auth_manager.is_authenticated(client) is False

    def test_concurrent_sessions(self, auth_manager):
        """Test multiple concurrent sessions"""
        token = auth_manager.api_token
        clients = [f"127.0.0.1:{30020 + i}" for i in range(10)]

        # All authenticate
        for client in clients:
            auth_manager.verify_token(client, token)

        # All should be authenticated
        for client in clients:
            assert auth_manager.is_authenticated(client) is True

        # Logout half
        for client in clients[:5]:
            auth_manager.logout(client)

        # Check states
        for client in clients[:5]:
            assert auth_manager.is_authenticated(client) is False
        for client in clients[5:]:
            assert auth_manager.is_authenticated(client) is True


class TestAuthenticationEdgeCases:
    """Test edge cases in authentication"""

    def test_empty_token_authentication(self, auth_manager):
        """Test authentication with empty token"""
        client = "127.0.0.1:30014"

        result = auth_manager.verify_token(client, "")
        assert result is False

    def test_none_token_authentication(self, auth_manager):
        """Test authentication with None token"""
        client = "127.0.0.1:30015"

        # Should handle gracefully
        try:
            result = auth_manager.verify_token(client, None)
            assert result is False
        except:
            # If it raises, that's also acceptable behavior
            pass

    def test_very_long_token(self, auth_manager):
        """Test authentication with very long token"""
        client = "127.0.0.1:30016"

        long_token = "x" * 10000
        result = auth_manager.verify_token(client, long_token)
        assert result is False

    def test_token_with_special_characters(self, auth_manager):
        """Test authentication with special characters"""
        client = "127.0.0.1:30017"

        special_token = "token!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        result = auth_manager.verify_token(client, special_token)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
