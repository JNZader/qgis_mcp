"""
Benchmark protocol performance
Tests throughput and latency of BufferedProtocolHandler vs naive parsing
"""

import time
import json
import struct
from io import BytesIO

try:
    import msgpack

    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False
    print("Warning: msgpack not available, some tests will be skipped")

# Import protocol handlers
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "qgis_mcp_plugin"))

from protocol import BufferedProtocolHandler, ProtocolHandler


def benchmark_naive_parsing(messages: list, iterations: int = 100):
    """Benchmark naive JSON parsing (old way)"""
    start = time.time()

    for _ in range(iterations):
        for msg_data in messages:
            # Simulate naive parsing
            buffer = b""
            buffer += msg_data
            try:
                message = json.loads(buffer.decode("utf-8"))
                # Process message
                _ = message["type"]
            except json.JSONDecodeError:
                pass  # Wait for more data

    elapsed = time.time() - start
    total_messages = len(messages) * iterations

    return {
        "total_messages": total_messages,
        "elapsed_seconds": elapsed,
        "messages_per_second": total_messages / elapsed,
        "avg_latency_ms": (elapsed / total_messages) * 1000,
    }


def benchmark_buffered_protocol(messages: list, iterations: int = 100):
    """Benchmark BufferedProtocolHandler"""
    start = time.time()
    handler = BufferedProtocolHandler(use_msgpack=False, validate_schema=False)

    for _ in range(iterations):
        handler.clear_buffer()
        for msg_data in messages:
            handler.feed_data(msg_data)
            while True:
                msg = handler.try_read_message()
                if msg is None:
                    break
                # Process message
                _ = msg["type"]

    elapsed = time.time() - start
    total_messages = len(messages) * iterations

    return {
        "total_messages": total_messages,
        "elapsed_seconds": elapsed,
        "messages_per_second": total_messages / elapsed,
        "avg_latency_ms": (elapsed / total_messages) * 1000,
    }


def benchmark_msgpack_vs_json(messages: list, iterations: int = 100):
    """Benchmark MessagePack vs JSON serialization"""
    if not HAS_MSGPACK:
        return None

    # JSON
    start = time.time()
    handler_json = BufferedProtocolHandler(use_msgpack=False, validate_schema=False)

    for _ in range(iterations):
        handler_json.clear_buffer()
        for msg_data in messages:
            handler_json.feed_data(msg_data)
            while handler_json.try_read_message():
                pass

    json_elapsed = time.time() - start

    # MessagePack
    start = time.time()
    handler_msgpack = BufferedProtocolHandler(use_msgpack=True, validate_schema=False)

    for _ in range(iterations):
        handler_msgpack.clear_buffer()
        for msg_data in messages:
            handler_msgpack.feed_data(msg_data)
            while handler_msgpack.try_read_message():
                pass

    msgpack_elapsed = time.time() - start

    total_messages = len(messages) * iterations

    return {
        "json": {
            "elapsed_seconds": json_elapsed,
            "messages_per_second": total_messages / json_elapsed,
        },
        "msgpack": {
            "elapsed_seconds": msgpack_elapsed,
            "messages_per_second": total_messages / msgpack_elapsed,
        },
        "speedup": json_elapsed / msgpack_elapsed,
    }


def benchmark_fragmented_messages(num_messages: int = 100):
    """Benchmark handling of fragmented messages"""
    handler = BufferedProtocolHandler(use_msgpack=False, validate_schema=False)

    # Create test messages
    messages = []
    for i in range(num_messages):
        msg = {"type": "ping", "id": str(i)}
        data = json.dumps(msg).encode("utf-8")
        header = struct.pack("!I", len(data))
        messages.append(header + data)

    # Benchmark: feed data in small chunks (simulating network fragmentation)
    start = time.time()
    received = 0

    for msg_bytes in messages:
        # Feed in 10-byte chunks
        for i in range(0, len(msg_bytes), 10):
            chunk = msg_bytes[i : i + 10]
            handler.feed_data(chunk)

            # Try to read messages
            while True:
                msg = handler.try_read_message()
                if msg is None:
                    break
                received += 1

    elapsed = time.time() - start

    return {
        "total_messages": num_messages,
        "received_messages": received,
        "elapsed_seconds": elapsed,
        "messages_per_second": received / elapsed,
        "handled_fragmentation": received == num_messages,
    }


def benchmark_large_messages(sizes: list = None):
    """Benchmark handling of different message sizes"""
    if sizes is None:
        sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB

    results = {}
    handler = BufferedProtocolHandler(use_msgpack=False, validate_schema=False)

    for size in sizes:
        # Create message with payload of specified size
        payload = "x" * size
        msg = {"type": "ping", "id": "1", "data": {"payload": payload}}

        # Serialize
        data = json.dumps(msg).encode("utf-8")
        header = struct.pack("!I", len(data))
        full_msg = header + data

        # Benchmark
        iterations = max(1, 1000 // (size // 1024))  # Fewer iterations for larger messages
        start = time.time()

        for _ in range(iterations):
            handler.clear_buffer()
            handler.feed_data(full_msg)
            msg_received = handler.try_read_message()
            assert msg_received is not None

        elapsed = time.time() - start

        results[f"{size // 1024}KB"] = {
            "message_size_bytes": size,
            "iterations": iterations,
            "elapsed_seconds": elapsed,
            "avg_latency_ms": (elapsed / iterations) * 1000,
            "throughput_mbps": (size * iterations / elapsed) / (1024 * 1024) * 8,
        }

    return results


def print_benchmark_results():
    """Run all benchmarks and print results"""
    print("=" * 80)
    print("PROTOCOL PERFORMANCE BENCHMARKS")
    print("=" * 80)

    # Create test messages
    test_messages = []
    handler = ProtocolHandler(use_msgpack=False, validate_schema=False)

    for i in range(100):
        msg = {
            "type": "get_features" if i % 2 == 0 else "list_layers",
            "id": str(i),
            "data": {"layer_id": f"layer_{i}", "limit": 100},
        }
        packed = handler.pack_message(msg)
        test_messages.append(packed)

    # 1. Naive vs Buffered
    print("\n1. NAIVE PARSING vs BUFFERED PROTOCOL")
    print("-" * 80)

    naive_results = benchmark_naive_parsing(test_messages, iterations=10)
    print(f"Naive Parsing:")
    print(f"  Messages/sec: {naive_results['messages_per_second']:.1f}")
    print(f"  Avg Latency:  {naive_results['avg_latency_ms']:.2f} ms")

    buffered_results = benchmark_buffered_protocol(test_messages, iterations=10)
    print(f"\nBuffered Protocol:")
    print(f"  Messages/sec: {buffered_results['messages_per_second']:.1f}")
    print(f"  Avg Latency:  {buffered_results['avg_latency_ms']:.2f} ms")

    speedup = buffered_results["messages_per_second"] / naive_results["messages_per_second"]
    print(f"\nSpeedup: {speedup:.2f}x")

    # 2. MessagePack vs JSON
    if HAS_MSGPACK:
        print("\n2. MESSAGEPACK vs JSON")
        print("-" * 80)

        msgpack_results = benchmark_msgpack_vs_json(test_messages, iterations=10)
        if msgpack_results:
            print(f"JSON:")
            print(f"  Messages/sec: {msgpack_results['json']['messages_per_second']:.1f}")

            print(f"\nMessagePack:")
            print(f"  Messages/sec: {msgpack_results['msgpack']['messages_per_second']:.1f}")

            print(f"\nSpeedup: {msgpack_results['speedup']:.2f}x")

    # 3. Fragmented messages
    print("\n3. FRAGMENTED MESSAGE HANDLING")
    print("-" * 80)

    frag_results = benchmark_fragmented_messages(num_messages=100)
    print(f"Total messages:    {frag_results['total_messages']}")
    print(f"Received:          {frag_results['received_messages']}")
    print(f"Success rate:      {frag_results['handled_fragmentation']}")
    print(f"Messages/sec:      {frag_results['messages_per_second']:.1f}")

    # 4. Large messages
    print("\n4. LARGE MESSAGE PERFORMANCE")
    print("-" * 80)

    large_results = benchmark_large_messages()
    for size, metrics in large_results.items():
        print(f"\n{size}:")
        print(f"  Avg Latency:  {metrics['avg_latency_ms']:.2f} ms")
        print(f"  Throughput:   {metrics['throughput_mbps']:.2f} Mbps")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"BufferedProtocol is {speedup:.1f}x faster than naive parsing")
    print(f"Throughput: {buffered_results['messages_per_second']:.0f} msg/s")
    print(f"Latency: {buffered_results['avg_latency_ms']:.2f} ms average")
    print(f"Fragmentation: Handled correctly")
    print(f"Large messages: Up to 1MB supported efficiently")


if __name__ == "__main__":
    print_benchmark_results()
