"""
Benchmark async operations
Tests async vs sync execution and threading overhead
"""

import time
import threading
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "qgis_mcp_plugin"))

from async_executor import AsyncCommandExecutor, AsyncOperationManager, OperationStatus


def simulate_long_operation(duration: float = 1.0, _progress_callback=None):
    """Simulate long-running operation"""
    steps = 10
    step_duration = duration / steps

    for i in range(steps):
        time.sleep(step_duration)
        if _progress_callback:
            _progress_callback(int((i + 1) / steps * 100), f"Step {i+1}/{steps}")

    return {"result": "completed", "duration": duration}


def benchmark_sync_vs_async():
    """Compare synchronous vs asynchronous execution"""
    num_operations = 5
    operation_duration = 1.0  # 1 second each

    print("\nBENCHMARK: Sync vs Async execution")
    print("-" * 80)

    # SYNCHRONOUS (blocking)
    print(f"Synchronous execution ({num_operations} operations):")
    start = time.time()

    for i in range(num_operations):
        result = simulate_long_operation(operation_duration)

    sync_time = time.time() - start
    print(f"  Total time: {sync_time:.2f}s")
    print(f"  User waited: {sync_time:.2f}s (blocking)")

    # ASYNCHRONOUS (non-blocking)
    print(f"\nAsynchronous execution ({num_operations} operations):")
    start = time.time()

    manager = AsyncOperationManager()
    request_ids = []

    # Start all operations
    for i in range(num_operations):
        request_id = f"op_{i}"
        manager.start_operation(
            request_id=request_id,
            command_type="test",
            handler=simulate_long_operation,
            params={"duration": operation_duration},
            timeout=10.0,
        )
        request_ids.append(request_id)

    response_time = time.time() - start
    print(f"  Response time: {response_time:.3f}s (non-blocking!)")

    # Wait for all to complete
    completed = 0
    while completed < num_operations:
        time.sleep(0.1)
        completed = sum(
            1 for rid in request_ids if manager.get_status(rid)["status"] in ("completed", "failed")
        )

    async_time = time.time() - start
    print(f"  Total time: {async_time:.2f}s (background)")
    print(f"  User experience: {response_time:.3f}s perceived wait")
    print(f"  UI improvement: {sync_time / response_time:.0f}x faster response")

    return {
        "sync_time": sync_time,
        "async_response_time": response_time,
        "async_total_time": async_time,
        "ui_improvement": sync_time / response_time,
    }


def benchmark_concurrent_operations():
    """Benchmark multiple concurrent async operations"""
    operation_counts = [1, 2, 5, 10]

    print("\nBENCHMARK: Concurrent async operations")
    print("-" * 80)

    results = {}

    for count in operation_counts:
        manager = AsyncOperationManager(max_concurrent=20)

        start = time.time()

        # Start operations
        request_ids = []
        for i in range(count):
            request_id = f"op_{i}"
            manager.start_operation(
                request_id=request_id,
                command_type="test",
                handler=simulate_long_operation,
                params={"duration": 1.0},
                timeout=10.0,
            )
            request_ids.append(request_id)

        # Wait for completion
        while True:
            statuses = [manager.get_status(rid)["status"] for rid in request_ids]
            if all(s in ("completed", "failed") for s in statuses):
                break
            time.sleep(0.1)

        elapsed = time.time() - start

        results[count] = {
            "operations": count,
            "elapsed_seconds": elapsed,
            "expected_serial": count * 1.0,
            "speedup": (count * 1.0) / elapsed,
        }

        print(
            f"{count:>2} operations: {elapsed:.2f}s (expected serial: {count * 1.0:.2f}s, speedup: {results[count]['speedup']:.1f}x)"
        )

    return results


def benchmark_async_overhead():
    """Measure overhead of async execution"""
    iterations = 100

    print("\nBENCHMARK: Async overhead")
    print("-" * 80)

    # Direct execution
    print("Direct execution:")
    start = time.time()

    for i in range(iterations):
        result = simulate_long_operation(0.01)  # 10ms operation

    direct_time = time.time() - start
    print(f"  Time: {direct_time:.3f}s")
    print(f"  Avg per operation: {direct_time / iterations * 1000:.2f}ms")

    # Async execution
    print("\nAsync execution:")
    manager = AsyncOperationManager(max_concurrent=20)

    start = time.time()
    request_ids = []

    for i in range(iterations):
        request_id = f"op_{i}"
        manager.start_operation(
            request_id=request_id,
            command_type="test",
            handler=simulate_long_operation,
            params={"duration": 0.01},
            timeout=5.0,
        )
        request_ids.append(request_id)

    # Wait for all
    while True:
        completed = sum(
            1 for rid in request_ids if manager.get_status(rid)["status"] in ("completed", "failed")
        )
        if completed == iterations:
            break
        time.sleep(0.01)

    async_time = time.time() - start
    print(f"  Time: {async_time:.3f}s")
    print(f"  Avg per operation: {async_time / iterations * 1000:.2f}ms")
    print(f"  Overhead: {(async_time - direct_time) / direct_time * 100:.1f}%")

    return {
        "direct_time": direct_time,
        "async_time": async_time,
        "overhead_percent": (async_time - direct_time) / direct_time * 100,
    }


def benchmark_progress_reporting():
    """Benchmark progress reporting performance"""
    print("\nBENCHMARK: Progress reporting")
    print("-" * 80)

    # With progress reporting
    print("With progress callbacks:")
    progress_updates = []

    def progress_callback(percent: int, message: str):
        progress_updates.append((percent, message))

    start = time.time()
    result = simulate_long_operation(1.0, _progress_callback=progress_callback)
    with_progress_time = time.time() - start

    print(f"  Time: {with_progress_time:.3f}s")
    print(f"  Progress updates: {len(progress_updates)}")

    # Without progress reporting
    print("\nWithout progress callbacks:")
    start = time.time()
    result = simulate_long_operation(1.0, _progress_callback=None)
    without_progress_time = time.time() - start

    print(f"  Time: {without_progress_time:.3f}s")
    print(
        f"  Overhead: {(with_progress_time - without_progress_time) / without_progress_time * 100:.1f}%"
    )

    return {
        "with_progress": with_progress_time,
        "without_progress": without_progress_time,
        "progress_updates": len(progress_updates),
        "overhead_percent": (with_progress_time - without_progress_time)
        / without_progress_time
        * 100,
    }


def benchmark_cancellation():
    """Benchmark operation cancellation"""
    print("\nBENCHMARK: Operation cancellation")
    print("-" * 80)

    manager = AsyncOperationManager()

    # Start long operation
    request_id = "cancel_test"
    manager.start_operation(
        request_id=request_id,
        command_type="test",
        handler=simulate_long_operation,
        params={"duration": 10.0},  # 10 second operation
        timeout=20.0,
    )

    # Wait a bit then cancel
    time.sleep(0.5)

    cancel_start = time.time()
    cancelled = manager.cancel_operation(request_id)
    cancel_time = time.time() - cancel_start

    print(f"Cancellation:")
    print(f"  Cancelled: {cancelled}")
    print(f"  Cancel time: {cancel_time * 1000:.2f}ms")

    # Verify status
    time.sleep(0.1)
    status = manager.get_status(request_id)
    print(f"  Final status: {status['status']}")
    print(f"  Operation stopped: {status['status'] == 'cancelled'}")

    return {
        "cancelled": cancelled,
        "cancel_time_ms": cancel_time * 1000,
        "final_status": status["status"],
    }


def benchmark_timeout_handling():
    """Benchmark timeout enforcement"""
    print("\nBENCHMARK: Timeout handling")
    print("-" * 80)

    manager = AsyncOperationManager()

    # Operation that will timeout
    timeout_duration = 1.0
    operation_duration = 3.0

    request_id = "timeout_test"
    start = time.time()

    manager.start_operation(
        request_id=request_id,
        command_type="test",
        handler=simulate_long_operation,
        params={"duration": operation_duration},
        timeout=timeout_duration,
    )

    # Wait for timeout
    while True:
        status = manager.get_status(request_id)
        if status["status"] in ("timeout", "failed", "completed"):
            break
        time.sleep(0.1)

    elapsed = time.time() - start

    print(f"Timeout enforcement:")
    print(f"  Timeout: {timeout_duration}s")
    print(f"  Operation duration: {operation_duration}s")
    print(f"  Actual elapsed: {elapsed:.2f}s")
    print(f"  Status: {status['status']}")
    print(f"  Timeout enforced: {status['status'] == 'timeout'}")
    print(f"  Accuracy: {abs(elapsed - timeout_duration) * 1000:.0f}ms deviation")

    return {
        "timeout": timeout_duration,
        "elapsed": elapsed,
        "status": status["status"],
        "accuracy_ms": abs(elapsed - timeout_duration) * 1000,
    }


def print_benchmark_results():
    """Run all benchmarks and print results"""
    print("=" * 80)
    print("ASYNC OPERATIONS PERFORMANCE BENCHMARKS")
    print("=" * 80)

    # 1. Sync vs Async
    sync_async = benchmark_sync_vs_async()

    # 2. Concurrent operations
    concurrent = benchmark_concurrent_operations()

    # 3. Async overhead
    overhead = benchmark_async_overhead()

    # 4. Progress reporting
    progress = benchmark_progress_reporting()

    # 5. Cancellation
    cancellation = benchmark_cancellation()

    # 6. Timeout handling
    timeout = benchmark_timeout_handling()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - ASYNC BENEFITS")
    print("=" * 80)
    print(f"1. UI responsiveness: {sync_async['ui_improvement']:.0f}x faster response to user")
    print(
        f"2. Concurrent execution: {max(r['speedup'] for r in concurrent.values()):.1f}x speedup for parallel tasks"
    )
    print(f"3. Overhead: {overhead['overhead_percent']:.1f}% (acceptable for operations > 100ms)")
    print(f"4. Progress reporting: {progress['overhead_percent']:.1f}% overhead")
    print(f"5. Cancellation: {cancellation['cancel_time_ms']:.0f}ms response time")
    print(f"6. Timeout accuracy: {timeout['accuracy_ms']:.0f}ms deviation")
    print(f"\nRECOMMENDATION: Use async for operations > 500ms")


if __name__ == "__main__":
    print_benchmark_results()
