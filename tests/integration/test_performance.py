"""
Performance benchmarks and tests

Tests cover:
- Message throughput
- Serialization performance
- Rate limiter performance
- Path validation performance
- Code sandbox performance
- Memory usage
- Concurrent operations
"""

import pytest
import time
import gc


@pytest.mark.slow
class TestSerializationPerformance:
    """Test serialization performance"""

    def test_json_serialization_speed(self, protocol_handler, performance_timer):
        """Benchmark JSON serialization speed"""
        message = {
            'type': 'get_features',
            'id': 'msg_001',
            'data': {
                'layer_id': 'layer_123',
                'limit': 100,
                'bbox': {'xmin': 0, 'ymin': 0, 'xmax': 10, 'ymax': 10}
            }
        }

        iterations = 10000

        with performance_timer:
            for _ in range(iterations):
                data = protocol_handler.serialize(message)
                protocol_handler.deserialize(data)

        elapsed = performance_timer.elapsed
        ops_per_sec = iterations / elapsed

        print(f"\nJSON: {ops_per_sec:.0f} serialize/deserialize ops/sec")
        assert ops_per_sec > 5000  # Should handle at least 5000 ops/sec

    def test_msgpack_serialization_speed(self, msgpack_protocol, performance_timer):
        """Benchmark MessagePack serialization speed"""
        message = {
            'type': 'get_features',
            'id': 'msg_001',
            'data': {
                'layer_id': 'layer_123',
                'limit': 100,
                'bbox': {'xmin': 0, 'ymin': 0, 'xmax': 10, 'ymax': 10}
            }
        }

        iterations = 10000

        with performance_timer:
            for _ in range(iterations):
                data = msgpack_protocol.serialize(message)
                msgpack_protocol.deserialize(data)

        elapsed = performance_timer.elapsed
        ops_per_sec = iterations / elapsed

        print(f"\nMessagePack: {ops_per_sec:.0f} serialize/deserialize ops/sec")
        assert ops_per_sec > 5000


@pytest.mark.slow
class TestRateLimiterPerformance:
    """Test rate limiter performance"""

    def test_rate_limiter_throughput(self, rate_limiter, performance_timer):
        """Benchmark rate limiter throughput"""
        client = "127.0.0.1:50001"
        iterations = 10000

        with performance_timer:
            for _ in range(iterations):
                rate_limiter.check_rate_limit(client, 'cheap')

        elapsed = performance_timer.elapsed
        ops_per_sec = iterations / elapsed

        print(f"\nRate limiter: {ops_per_sec:.0f} checks/sec")
        assert ops_per_sec > 10000  # Should handle at least 10k checks/sec

    def test_rate_limiter_memory_usage(self, rate_limiter):
        """Test rate limiter memory usage with many clients"""
        # Create many clients
        num_clients = 1000

        gc.collect()
        # Note: Actual memory measurement would require psutil or similar
        # This test just ensures it doesn't crash

        for i in range(num_clients):
            client = f"127.0.0.1:{50000 + i}"
            rate_limiter.check_rate_limit(client, 'normal')

        # Should have stored data for all clients
        assert len(rate_limiter.request_history) <= num_clients * 4  # 4 operation types


@pytest.mark.slow
class TestPathValidatorPerformance:
    """Test path validator performance"""

    def test_path_validation_speed(self, path_validator, temp_file, performance_timer):
        """Benchmark path validation speed"""
        path = str(temp_file)
        iterations = 1000

        with performance_timer:
            for _ in range(iterations):
                path_validator.validate_path(path, operation='read')

        elapsed = performance_timer.elapsed
        ops_per_sec = iterations / elapsed

        print(f"\nPath validation: {ops_per_sec:.0f} validations/sec")
        assert ops_per_sec > 500  # Should handle at least 500 validations/sec


@pytest.mark.slow
class TestCodeSandboxPerformance:
    """Test code sandbox performance"""

    def test_code_validation_speed(self, sandbox, performance_timer):
        """Benchmark code validation speed"""
        code = """
x = [1, 2, 3, 4, 5]
y = [i * 2 for i in x if i > 2]
result = sum(y)
"""
        iterations = 1000

        with performance_timer:
            for _ in range(iterations):
                sandbox.validate_code(code)

        elapsed = performance_timer.elapsed
        ops_per_sec = iterations / elapsed

        print(f"\nCode validation: {ops_per_sec:.0f} validations/sec")
        assert ops_per_sec > 100  # AST parsing is expensive, but should still be fast


@pytest.mark.slow
class TestAuthenticationPerformance:
    """Test authentication performance"""

    def test_token_verification_speed(self, auth_manager, performance_timer):
        """Benchmark token verification speed"""
        token = auth_manager.api_token
        client = "127.0.0.1:50002"
        iterations = 10000

        with performance_timer:
            for _ in range(iterations):
                auth_manager.verify_token(client, token)

        elapsed = performance_timer.elapsed
        ops_per_sec = iterations / elapsed

        print(f"\nToken verification: {ops_per_sec:.0f} verifications/sec")
        assert ops_per_sec > 5000  # Should be very fast (constant-time comparison)


@pytest.mark.slow
class TestConcurrentPerformance:
    """Test concurrent operation performance"""

    def test_concurrent_rate_limit_checks(self, rate_limiter):
        """Test rate limiter under concurrent load"""
        import threading

        num_threads = 10
        checks_per_thread = 1000
        results = []

        def worker(thread_id):
            client = f"127.0.0.1:{51000 + thread_id}"
            count = 0
            for _ in range(checks_per_thread):
                if rate_limiter.check_rate_limit(client, 'cheap'):
                    count += 1
            results.append(count)

        start = time.perf_counter()

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        elapsed = time.perf_counter() - start
        total_checks = num_threads * checks_per_thread
        ops_per_sec = total_checks / elapsed

        print(f"\nConcurrent rate limiting: {ops_per_sec:.0f} checks/sec")
        print(f"Total successful checks: {sum(results)}")

        assert ops_per_sec > 5000  # Should handle concurrent load well

    def test_concurrent_authentication(self, auth_manager):
        """Test authentication under concurrent load"""
        import threading

        token = auth_manager.api_token
        num_threads = 20
        results = []

        def worker(thread_id):
            client = f"127.0.0.1:{52000 + thread_id}"
            success = auth_manager.verify_token(client, token)
            results.append(success)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        # All should succeed
        assert all(results)
        assert len(results) == num_threads


@pytest.mark.slow
class TestProtocolPerformance:
    """Test protocol performance"""

    def test_message_packing_speed(self, protocol_handler, performance_timer):
        """Benchmark message packing speed"""
        message = {'type': 'ping', 'id': 'msg_001'}
        iterations = 10000

        with performance_timer:
            for _ in range(iterations):
                protocol_handler.pack_message(message)

        elapsed = performance_timer.elapsed
        ops_per_sec = iterations / elapsed

        print(f"\nMessage packing: {ops_per_sec:.0f} packs/sec")
        assert ops_per_sec > 5000

    def test_buffered_protocol_throughput(self, buffered_protocol, performance_timer):
        """Benchmark buffered protocol throughput"""
        from protocol import ProtocolHandler

        handler = ProtocolHandler(use_msgpack=False, validate_schema=True)
        messages = [{'type': 'ping', 'id': f'msg_{i:05d}'} for i in range(100)]

        # Pack all messages
        packed_data = b''.join(handler.pack_message(msg) for msg in messages)

        iterations = 100

        with performance_timer:
            for _ in range(iterations):
                buffered_protocol.clear_buffer()
                buffered_protocol.feed_data(packed_data)

                for _ in range(len(messages)):
                    buffered_protocol.try_read_message()

        elapsed = performance_timer.elapsed
        messages_per_sec = (len(messages) * iterations) / elapsed

        print(f"\nBuffered protocol: {messages_per_sec:.0f} messages/sec")
        assert messages_per_sec > 5000


@pytest.mark.slow
class TestMemoryEfficiency:
    """Test memory efficiency"""

    def test_rate_limiter_cleanup(self, rate_limiter):
        """Test that rate limiter cleans up old data"""
        # Add many clients
        for i in range(2000):
            client = f"127.0.0.1:{60000 + i}"
            rate_limiter.check_rate_limit(client, 'normal')

        # Should trigger cleanup at 1000+ clients
        # Verify size is bounded
        assert len(rate_limiter.request_history) < 2000

    def test_buffered_protocol_memory(self, buffered_protocol):
        """Test buffered protocol memory management"""
        # Feed data in chunks
        chunk_size = 1024
        num_chunks = 100

        for _ in range(num_chunks):
            data = b'x' * chunk_size
            buffered_protocol.feed_data(data)

            # Clear periodically to prevent overflow
            if buffered_protocol.get_buffer_size() > 50000:
                buffered_protocol.clear_buffer()

        # Buffer should be manageable
        assert buffered_protocol.get_buffer_size() < buffered_protocol.MAX_MESSAGE_SIZE


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])  # -s to show print output
