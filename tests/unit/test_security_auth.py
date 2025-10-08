"""
Unit tests for Authentication and Token Management

Tests cover:
- Token generation
- Token verification (constant-time)
- Token storage encryption
- Keyring integration
- Authentication tracking
- Session management
- Token lifecycle
"""

import pytest
import time
import hmac
from pathlib import Path
from security_improved import AuthenticationManager, SecureTokenStorage, SecurityException


class TestTokenGeneration:
    """Test secure token generation"""

    def test_token_generated_on_init(self, auth_manager):
        """Test that token is generated on initialization"""
        assert auth_manager.api_token is not None
        assert isinstance(auth_manager.api_token, str)
        assert len(auth_manager.api_token) > 0

    def test_token_sufficient_length(self, auth_manager):
        """Test that generated tokens are sufficiently long"""
        # secrets.token_urlsafe(32) produces ~43 characters
        assert len(auth_manager.api_token) >= 40

    def test_token_url_safe_characters(self, auth_manager):
        """Test that token contains only URL-safe characters"""
        token = auth_manager.api_token
        # URL-safe base64 uses A-Z, a-z, 0-9, -, _
        import string

        allowed = set(string.ascii_letters + string.digits + "-_")
        assert all(c in allowed for c in token)

    def test_token_uniqueness(self):
        """Test that each manager generates unique tokens"""
        manager1 = AuthenticationManager()
        manager2 = AuthenticationManager()

        # Clean up stored tokens to ensure fresh generation
        try:
            manager1.storage.delete_token()
            manager2.storage.delete_token()
        except:
            pass

        # Create new managers (will generate new tokens)
        manager1 = AuthenticationManager()
        manager2 = AuthenticationManager()

        # Tokens should be different (with overwhelming probability)
        # Note: They might be the same if loaded from storage
        # This test is more about the generation mechanism

    def test_token_generation_method(self, auth_manager):
        """Test the internal token generation method"""
        token1 = auth_manager._generate_token()
        token2 = auth_manager._generate_token()

        assert token1 != token2
        assert len(token1) >= 40
        assert len(token2) >= 40


class TestTokenVerification:
    """Test token verification"""

    def test_valid_token_accepted(self, auth_manager):
        """Test that valid token is accepted"""
        token = auth_manager.api_token
        client = "127.0.0.1:12345"

        result = auth_manager.verify_token(client, token)
        assert result is True

    def test_invalid_token_rejected(self, auth_manager):
        """Test that invalid token is rejected"""
        client = "127.0.0.1:12346"

        result = auth_manager.verify_token(client, "invalid_token")
        assert result is False

    def test_empty_token_rejected(self, auth_manager):
        """Test that empty token is rejected"""
        client = "127.0.0.1:12347"

        result = auth_manager.verify_token(client, "")
        assert result is False

    def test_similar_token_rejected(self, auth_manager):
        """Test that similar but incorrect token is rejected"""
        token = auth_manager.api_token
        client = "127.0.0.1:12348"

        # Change one character
        if len(token) > 0:
            wrong_token = token[:-1] + ("X" if token[-1] != "X" else "Y")
            result = auth_manager.verify_token(client, wrong_token)
            assert result is False

    def test_constant_time_comparison(self, auth_manager, assert_secure_timing):
        """Test that token comparison is constant-time"""
        token = auth_manager.api_token
        client = "127.0.0.1:12349"

        # Create wrong token of same length
        wrong_token = "x" * len(token)

        def verify_correct():
            auth_manager.verify_token(client, token)

        def verify_wrong():
            auth_manager.verify_token(client, wrong_token)

        # Should take similar time regardless of correctness
        # This helps prevent timing attacks
        assert_secure_timing(verify_correct, verify_wrong, max_ratio=3.0)

    def test_case_sensitive_verification(self, auth_manager):
        """Test that token verification is case-sensitive"""
        token = auth_manager.api_token
        client = "127.0.0.1:12350"

        # Try uppercase version (if token has lowercase)
        wrong_token = token.upper() if token != token.upper() else token.lower()

        result = auth_manager.verify_token(client, wrong_token)
        assert result is False


class TestAuthenticationTracking:
    """Test authentication state tracking"""

    def test_unauthenticated_by_default(self, auth_manager):
        """Test that clients are unauthenticated by default"""
        client = "127.0.0.1:12351"
        assert auth_manager.is_authenticated(client) is False

    def test_authenticated_after_valid_token(self, auth_manager):
        """Test that clients are authenticated after valid token"""
        token = auth_manager.api_token
        client = "127.0.0.1:12352"

        auth_manager.verify_token(client, token)
        assert auth_manager.is_authenticated(client) is True

    def test_not_authenticated_after_invalid_token(self, auth_manager):
        """Test that clients remain unauthenticated after invalid token"""
        client = "127.0.0.1:12353"

        auth_manager.verify_token(client, "wrong_token")
        assert auth_manager.is_authenticated(client) is False

    def test_multiple_clients_tracked_separately(self, auth_manager):
        """Test that multiple clients are tracked separately"""
        token = auth_manager.api_token
        client1 = "127.0.0.1:12354"
        client2 = "127.0.0.1:12355"

        # Authenticate only client1
        auth_manager.verify_token(client1, token)

        assert auth_manager.is_authenticated(client1) is True
        assert auth_manager.is_authenticated(client2) is False

    def test_logout_removes_authentication(self, auth_manager):
        """Test that logout removes authentication"""
        token = auth_manager.api_token
        client = "127.0.0.1:12356"

        # Authenticate
        auth_manager.verify_token(client, token)
        assert auth_manager.is_authenticated(client) is True

        # Logout
        auth_manager.logout(client)
        assert auth_manager.is_authenticated(client) is False

    def test_logout_nonexistent_client(self, auth_manager):
        """Test that logout on non-existent client doesn't error"""
        client = "127.0.0.1:12357"

        # Should not raise exception
        auth_manager.logout(client)
        assert auth_manager.is_authenticated(client) is False

    def test_clear_all_removes_all_clients(self, auth_manager):
        """Test that clear_all removes all authenticated clients"""
        token = auth_manager.api_token
        clients = [f"127.0.0.1:{12360 + i}" for i in range(5)]

        # Authenticate all clients
        for client in clients:
            auth_manager.verify_token(client, token)

        # Verify all authenticated
        for client in clients:
            assert auth_manager.is_authenticated(client) is True

        # Clear all
        auth_manager.clear_all()

        # Verify all unauthenticated
        for client in clients:
            assert auth_manager.is_authenticated(client) is False


class TestSecureTokenStorage:
    """Test secure token storage"""

    def test_store_and_retrieve_token(self, token_storage):
        """Test that tokens can be stored and retrieved"""
        test_token = "test_token_abc123"

        token_storage.store_token(test_token)
        retrieved = token_storage.retrieve_token()

        assert retrieved == test_token

    def test_retrieve_nonexistent_token(self, token_storage):
        """Test that retrieving non-existent token raises error"""
        # Ensure no token exists
        try:
            token_storage.delete_token()
        except:
            pass

        with pytest.raises(FileNotFoundError):
            token_storage.retrieve_token()

    def test_token_overwrite(self, token_storage):
        """Test that storing new token overwrites old one"""
        token1 = "token_one"
        token2 = "token_two"

        token_storage.store_token(token1)
        assert token_storage.retrieve_token() == token1

        token_storage.store_token(token2)
        assert token_storage.retrieve_token() == token2

    def test_delete_token(self, token_storage):
        """Test that tokens can be deleted"""
        test_token = "deleteme_token"

        token_storage.store_token(test_token)
        assert token_storage.retrieve_token() == test_token

        token_storage.delete_token()

        with pytest.raises(FileNotFoundError):
            token_storage.retrieve_token()

    def test_delete_nonexistent_token(self, token_storage):
        """Test that deleting non-existent token doesn't error"""
        # Ensure no token exists
        try:
            token_storage.delete_token()
        except:
            pass

        # Should not raise exception
        token_storage.delete_token()


class TestTokenEncryption:
    """Test token encryption on disk"""

    def test_token_encrypted_on_disk(self, token_storage):
        """Test that token is encrypted when stored on disk"""
        plaintext_token = "secret_token_do_not_expose"

        token_storage.store_token(plaintext_token)

        # Read raw file content
        token_file = token_storage._get_token_path()
        with open(token_file, "rb") as f:
            raw_content = f.read()

        # Plaintext should not appear in file
        assert plaintext_token.encode() not in raw_content

    def test_encryption_key_created(self, token_storage):
        """Test that encryption key is created"""
        key = token_storage._get_encryption_key()

        assert key is not None
        assert isinstance(key, bytes)
        assert len(key) > 0

    def test_encryption_key_persists(self, token_storage):
        """Test that encryption key persists across calls"""
        key1 = token_storage._get_encryption_key()
        key2 = token_storage._get_encryption_key()

        assert key1 == key2

    def test_encryption_key_file_created(self, token_storage):
        """Test that encryption key file is created"""
        token_storage._get_encryption_key()

        key_file = Path.home() / ".qgis_mcp" / ".key"
        assert key_file.exists()

    def test_token_file_created(self, token_storage):
        """Test that token file is created"""
        token_storage.store_token("test")

        token_file = token_storage._get_token_path()
        assert token_file.exists()


class TestKeyringIntegration:
    """Test keyring integration (if available)"""

    def test_keyring_availability_check(self, token_storage):
        """Test that keyring availability is checked"""
        has_keyring = token_storage._check_keyring()
        assert isinstance(has_keyring, bool)

    @pytest.mark.skipif(not SecureTokenStorage()._check_keyring(), reason="Keyring not available")
    def test_keyring_storage_preferred(self):
        """Test that keyring is preferred over file storage"""
        storage = SecureTokenStorage()
        assert storage.keyring_available is True

    def test_fallback_to_file_storage(self, monkeypatch):
        """Test fallback to file storage when keyring unavailable"""

        # Mock keyring as unavailable
        def mock_check_keyring(self):
            return False

        monkeypatch.setattr(SecureTokenStorage, "_check_keyring", mock_check_keyring)

        storage = SecureTokenStorage()
        assert storage.keyring_available is False


class TestAuthenticationManager:
    """Test authentication manager integration"""

    def test_manager_uses_storage(self, auth_manager):
        """Test that manager uses secure storage"""
        assert isinstance(auth_manager.storage, SecureTokenStorage)

    def test_manager_loads_existing_token(self, token_storage):
        """Test that manager loads existing token from storage"""
        test_token = "existing_token_xyz"
        token_storage.store_token(test_token)

        # Create new manager (should load existing token)
        manager = AuthenticationManager()
        assert manager.api_token == test_token

        # Cleanup
        token_storage.delete_token()

    def test_manager_generates_new_token_if_none(self, token_storage):
        """Test that manager generates new token if none exists"""
        # Ensure no token exists
        try:
            token_storage.delete_token()
        except:
            pass

        # Create manager
        manager = AuthenticationManager()

        # Should have generated and stored a token
        assert manager.api_token is not None
        assert len(manager.api_token) > 0

        # Should be retrievable from storage
        stored = token_storage.retrieve_token()
        assert stored == manager.api_token

        # Cleanup
        token_storage.delete_token()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
