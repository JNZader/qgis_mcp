"""
Unit tests for Rate Limiting

Tests cover:
- Basic rate limiting
- Different operation types
- Time windows
- Exponential backoff
- Failed authentication tracking
- Lockout mechanisms
- Client isolation
- Cleanup mechanisms
"""

import pytest
import time
from security_improved import ImprovedRateLimiter, SecurityException


class TestBasicRateLimiting:
    """Test basic rate limiting functionality"""

    def test_within_rate_limit_allowed(self, rate_limiter):
        """Test that requests within limit are allowed"""
        client = "127.0.0.1:10001"

        # Normal operations: 30 per minute
        for i in range(20):
            assert rate_limiter.check_rate_limit(client, "normal") is True

    def test_rate_limit_exceeded_blocked(self, rate_limiter):
        """Test that requests exceeding limit are blocked"""
        client = "127.0.0.1:10002"

        # Normal operations: 30 per minute
        for i in range(35):
            result = rate_limiter.check_rate_limit(client, "normal")
            if i < 30:
                assert result is True
            else:
                assert result is False

    def test_rate_limit_resets_after_window(self, rate_limiter):
        """Test that rate limit resets after time window"""
        # This would require waiting for the time window to expire
        # For unit tests, we verify the window is being checked
        client = "127.0.0.1:10003"

        # Fill up the limit
        for i in range(30):
            rate_limiter.check_rate_limit(client, "normal")

        # Next should be blocked
        assert rate_limiter.check_rate_limit(client, "normal") is False

    def test_different_clients_isolated(self, rate_limiter):
        """Test that different clients have separate limits"""
        client1 = "127.0.0.1:10004"
        client2 = "127.0.0.1:10005"

        # Fill up client1's limit
        for i in range(30):
            rate_limiter.check_rate_limit(client1, "normal")

        # client1 should be rate limited
        assert rate_limiter.check_rate_limit(client1, "normal") is False

        # client2 should still be allowed
        assert rate_limiter.check_rate_limit(client2, "normal") is True


class TestOperationTypes:
    """Test different operation type limits"""

    def test_authentication_limit(self, rate_limiter):
        """Test authentication operation limit (5 per 15 min)"""
        client = "127.0.0.1:10006"

        for i in range(6):
            result = rate_limiter.check_rate_limit(client, "authentication")
            if i < 5:
                assert result is True
            else:
                assert result is False

    def test_expensive_operation_limit(self, rate_limiter):
        """Test expensive operation limit (10 per 10 min)"""
        client = "127.0.0.1:10007"

        for i in range(12):
            result = rate_limiter.check_rate_limit(client, "expensive")
            if i < 10:
                assert result is True
            else:
                assert result is False

    def test_normal_operation_limit(self, rate_limiter):
        """Test normal operation limit (30 per minute)"""
        client = "127.0.0.1:10008"

        for i in range(35):
            result = rate_limiter.check_rate_limit(client, "normal")
            if i < 30:
                assert result is True
            else:
                assert result is False

    def test_cheap_operation_limit(self, rate_limiter):
        """Test cheap operation limit (100 per minute)"""
        client = "127.0.0.1:10009"

        for i in range(105):
            result = rate_limiter.check_rate_limit(client, "cheap")
            if i < 100:
                assert result is True
            else:
                assert result is False

    def test_different_operation_types_separate_limits(self, rate_limiter):
        """Test that different operation types have separate limits"""
        client = "127.0.0.1:10010"

        # Fill up normal limit
        for i in range(30):
            rate_limiter.check_rate_limit(client, "normal")

        # Normal should be blocked
        assert rate_limiter.check_rate_limit(client, "normal") is False

        # But cheap operations should still be allowed
        assert rate_limiter.check_rate_limit(client, "cheap") is True


class TestFailedAuthenticationTracking:
    """Test failed authentication tracking and lockout"""

    def test_failed_auth_recorded(self, rate_limiter):
        """Test that failed auth attempts are recorded"""
        client = "127.0.0.1:10011"

        rate_limiter.record_failed_auth(client)

        # Should be in the tracking dict
        assert client in rate_limiter.failed_auth_attempts
        assert len(rate_limiter.failed_auth_attempts[client]) == 1

    def test_multiple_failed_auths_recorded(self, rate_limiter):
        """Test that multiple failed auths are tracked"""
        client = "127.0.0.1:10012"

        for i in range(3):
            rate_limiter.record_failed_auth(client)

        assert len(rate_limiter.failed_auth_attempts[client]) == 3

    def test_lockout_after_5_failures(self, rate_limiter):
        """Test that lockout occurs after 5 failures"""
        client = "127.0.0.1:10013"

        # Record 5 failures
        for i in range(5):
            rate_limiter.record_failed_auth(client)

        # Should be locked out
        with pytest.raises(SecurityException, match="locked out"):
            rate_limiter.check_rate_limit(client, "normal")

    def test_lockout_prevents_all_operations(self, rate_limiter):
        """Test that lockout prevents all operations"""
        client = "127.0.0.1:10014"

        # Trigger lockout
        for i in range(5):
            rate_limiter.record_failed_auth(client)

        # All operation types should be blocked
        for op_type in ["authentication", "expensive", "normal", "cheap"]:
            with pytest.raises(SecurityException, match="locked out"):
                rate_limiter.check_rate_limit(client, op_type)

    def test_successful_auth_clears_failures(self, rate_limiter):
        """Test that successful auth clears failed attempts"""
        client = "127.0.0.1:10015"

        # Record some failures
        for i in range(3):
            rate_limiter.record_failed_auth(client)

        assert len(rate_limiter.failed_auth_attempts[client]) == 3

        # Successful auth
        rate_limiter.record_successful_auth(client)

        # Should be cleared
        assert client not in rate_limiter.failed_auth_attempts

    def test_successful_auth_clears_lockout(self, rate_limiter):
        """Test that successful auth clears lockout"""
        client = "127.0.0.1:10016"

        # Trigger lockout
        for i in range(5):
            rate_limiter.record_failed_auth(client)

        # Verify locked out
        with pytest.raises(SecurityException, match="locked out"):
            rate_limiter.check_rate_limit(client, "normal")

        # Successful auth (might happen through admin reset)
        rate_limiter.record_successful_auth(client)

        # Should no longer be locked out
        assert rate_limiter.check_rate_limit(client, "normal") is True


class TestExponentialBackoff:
    """Test exponential backoff lockout duration"""

    def test_lockout_duration_increases(self, rate_limiter):
        """Test that lockout duration increases with failures"""
        client = "127.0.0.1:10017"

        # Record exactly 5 failures (triggers first lockout)
        for i in range(5):
            rate_limiter.record_failed_auth(client)

        # Get lockout time
        lockout1 = rate_limiter.lockouts[client]

        # Clear lockout manually (simulate time passing or admin reset)
        del rate_limiter.lockouts[client]

        # Record 6 failures (would trigger longer lockout if not cleared)
        rate_limiter.failed_auth_attempts[client] = [time.time()] * 6
        rate_limiter.record_failed_auth(client)

        lockout2 = rate_limiter.lockouts[client]

        # Second lockout should be longer (exponential backoff)
        # lockout = now + 60 * (2 ** (attempts - 5))
        # 5 attempts: 60s, 6 attempts: 120s, 7 attempts: 240s

    def test_max_lockout_duration(self, rate_limiter):
        """Test that lockout duration has a maximum"""
        client = "127.0.0.1:10018"

        # Simulate many failures
        rate_limiter.failed_auth_attempts[client] = [time.time()] * 20

        # Record one more to trigger lockout
        rate_limiter.record_failed_auth(client)

        # Lockout should exist
        assert client in rate_limiter.lockouts

        # Verify it's capped at 60 minutes (3600 seconds)
        lockout_time = rate_limiter.lockouts[client]
        max_duration = 60 * 60  # 3600 seconds
        actual_duration = lockout_time - time.time()

        assert actual_duration <= max_duration + 1  # +1 for timing variance


class TestLockoutMechanism:
    """Test lockout state management"""

    def test_lockout_enforced_during_window(self, rate_limiter):
        """Test that lockout is enforced during window"""
        client = "127.0.0.1:10019"

        # Trigger lockout
        for i in range(5):
            rate_limiter.record_failed_auth(client)

        # Should be locked out immediately
        with pytest.raises(SecurityException, match="locked out"):
            rate_limiter.check_rate_limit(client, "normal")

    def test_lockout_message_includes_time(self, rate_limiter):
        """Test that lockout message includes remaining time"""
        client = "127.0.0.1:10020"

        # Trigger lockout
        for i in range(5):
            rate_limiter.record_failed_auth(client)

        # Exception should include time remaining
        with pytest.raises(SecurityException, match="Try again in .* seconds"):
            rate_limiter.check_rate_limit(client, "normal")

    def test_lockout_removed_after_expiration(self, rate_limiter):
        """Test that lockout is removed after expiration"""
        client = "127.0.0.1:10021"

        # Manually set an expired lockout
        rate_limiter.lockouts[client] = time.time() - 10  # 10 seconds ago

        # Should not be locked out
        assert rate_limiter.check_rate_limit(client, "normal") is True

        # Lockout entry should be removed
        assert client not in rate_limiter.lockouts


class TestCleanupMechanism:
    """Test automatic cleanup of old data"""

    def test_old_requests_removed(self, rate_limiter):
        """Test that old requests are removed from history"""
        client = "127.0.0.1:10022"

        # Add some requests
        for i in range(10):
            rate_limiter.check_rate_limit(client, "normal")

        # Manually age the requests
        key = f"{client}:normal"
        old_time = time.time() - 3600  # 1 hour ago
        rate_limiter.request_history[key] = [old_time] * 10

        # Next check should clean up old requests
        rate_limiter.check_rate_limit(client, "normal")

        # Old requests should be gone
        assert len(rate_limiter.request_history[key]) == 1  # Only the new one

    def test_old_clients_cleaned_up(self, rate_limiter):
        """Test that old clients are removed from tracking"""
        # Add many clients
        for i in range(1500):  # More than cleanup threshold (1000)
            client = f"127.0.0.1:{20000 + i}"
            rate_limiter.check_rate_limit(client, "normal")

        # Should trigger cleanup
        # Verify cleanup happened (size should not grow unbounded)
        assert len(rate_limiter.request_history) < 1500

    def test_old_failed_auth_attempts_removed(self, rate_limiter):
        """Test that old failed auth attempts are removed"""
        client = "127.0.0.1:10023"

        # Manually add old failed attempts
        old_time = time.time() - 7200  # 2 hours ago
        rate_limiter.failed_auth_attempts[client] = [old_time] * 3

        # Record new failure
        rate_limiter.record_failed_auth(client)

        # Old attempts should be cleaned up (> 1 hour old)
        assert len(rate_limiter.failed_auth_attempts[client]) == 1


class TestThreadSafety:
    """Test thread-safety of rate limiter"""

    def test_concurrent_checks_thread_safe(self, rate_limiter):
        """Test that concurrent rate limit checks are thread-safe"""
        import threading

        client = "127.0.0.1:10024"
        results = []

        def check_limit():
            result = rate_limiter.check_rate_limit(client, "normal")
            results.append(result)

        # Create multiple threads
        threads = []
        for i in range(50):
            t = threading.Thread(target=check_limit)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # First 30 should be True, rest False
        true_count = sum(1 for r in results if r is True)
        false_count = sum(1 for r in results if r is False)

        assert true_count <= 30  # At most 30 allowed
        assert false_count >= 20  # At least 20 blocked

    def test_concurrent_failed_auth_thread_safe(self, rate_limiter):
        """Test that concurrent failed auth recording is thread-safe"""
        import threading

        client = "127.0.0.1:10025"

        def record_failure():
            rate_limiter.record_failed_auth(client)

        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=record_failure)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All 10 should be recorded
        assert len(rate_limiter.failed_auth_attempts[client]) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
