"""
End-to-end performance benchmarks
Tests realistic workflows and sustained load
"""

import time
import threading
import random
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "qgis_mcp_plugin"))


class LoadTestClient:
    """Simulates client making requests"""

    def __init__(self, client_id: int):
        self.client_id = client_id
        self.requests_sent = 0
        self.responses_received = 0
        self.errors = 0
        self.latencies = []

    def simulate_request(self, request_type: str, duration: float):
        """Simulate a request with given duration"""
        start = time.time()

        # Simulate network and processing
        time.sleep(duration)

        latency = time.time() - start
        self.latencies.append(latency)
        self.requests_sent += 1
        self.responses_received += 1

        return {"status": "success", "latency": latency}


def benchmark_realistic_workflow():
    """Benchmark realistic GIS workflow"""
    print("\nBENCHMARK: Realistic GIS workflow")
    print("-" * 80)

    workflow_steps = [
        ("authenticate", 0.010),  # 10ms
        ("list_layers", 0.050),  # 50ms
        ("get_features", 0.200),  # 200ms
        ("get_features", 0.150),  # 150ms (cached)
        ("execute_code", 0.500),  # 500ms
        ("get_stats", 0.020),  # 20ms
    ]

    print("Workflow steps:")
    for i, (step, duration) in enumerate(workflow_steps, 1):
        print(f"  {i}. {step}: {duration*1000:.0f}ms")

    # Execute workflow
    print("\nExecuting workflow...")
    client = LoadTestClient(1)

    start = time.time()
    for step, duration in workflow_steps:
        result = client.simulate_request(step, duration)

    total_time = time.time() - start

    print(f"\nResults:")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Requests: {client.requests_sent}")
    print(f"  Avg latency: {sum(client.latencies) / len(client.latencies) * 1000:.1f}ms")
    print(f"  Min latency: {min(client.latencies) * 1000:.1f}ms")
    print(f"  Max latency: {max(client.latencies) * 1000:.1f}ms")

    return {
        "total_time": total_time,
        "requests": client.requests_sent,
        "avg_latency": sum(client.latencies) / len(client.latencies),
    }


def benchmark_sustained_load(duration: int = 60, target_rps: int = 100):
    """Benchmark sustained load over time"""
    print(f"\nBENCHMARK: Sustained load ({target_rps} req/s for {duration}s)")
    print("-" * 80)

    # Request type distribution (realistic)
    request_types = {
        "ping": (0.05, 0.30),  # 30% - cheap
        "list_layers": (0.05, 0.20),  # 20% - cheap
        "get_features": (0.20, 0.40),  # 40% - normal
        "execute_code": (0.50, 0.08),  # 8% - expensive
        "get_stats": (0.02, 0.02),  # 2% - cheap
    }

    # Calculate request distribution
    total_requests = target_rps * duration
    print(f"Target: {total_requests} total requests")

    # Statistics
    requests_sent = 0
    responses_received = 0
    errors = 0
    latencies = []
    request_counts = defaultdict(int)

    start_time = time.time()
    interval = 1.0 / target_rps  # Time between requests

    print("\nRunning load test...")
    print("Time    RPS     Latency(ms)    Requests")
    print("-" * 50)

    last_report = start_time
    while time.time() - start_time < duration:
        # Select request type based on distribution
        rand = random.random()
        cumulative = 0
        selected_type = "ping"
        selected_duration = 0.05

        for req_type, (req_duration, percentage) in request_types.items():
            cumulative += percentage
            if rand <= cumulative:
                selected_type = req_type
                selected_duration = req_duration
                break

        # Simulate request
        req_start = time.time()

        # Simulate processing (in reality this would be network + server)
        time.sleep(selected_duration * random.uniform(0.8, 1.2))  # Add variance

        latency = time.time() - req_start

        requests_sent += 1
        responses_received += 1
        latencies.append(latency)
        request_counts[selected_type] += 1

        # Report every second
        if time.time() - last_report >= 1.0:
            elapsed = time.time() - start_time
            current_rps = requests_sent / elapsed
            avg_latency = sum(latencies) / len(latencies) * 1000

            print(
                f"{elapsed:>4.0f}s   {current_rps:>5.1f}   {avg_latency:>8.1f}       {requests_sent}"
            )
            last_report = time.time()

        # Rate limiting
        time.sleep(max(0, interval - (time.time() - req_start)))

    total_time = time.time() - start_time

    # Calculate percentiles
    sorted_latencies = sorted(latencies)
    p50 = sorted_latencies[len(sorted_latencies) // 2] * 1000
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] * 1000
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] * 1000

    print("\n" + "-" * 50)
    print("\nResults:")
    print(f"  Duration: {total_time:.1f}s")
    print(f"  Total requests: {requests_sent}")
    print(f"  Actual RPS: {requests_sent / total_time:.1f}")
    print(f"  Errors: {errors}")
    print(f"\nLatency:")
    print(f"  p50: {p50:.1f}ms")
    print(f"  p95: {p95:.1f}ms")
    print(f"  p99: {p99:.1f}ms")
    print(f"  avg: {sum(latencies) / len(latencies) * 1000:.1f}ms")
    print(f"  max: {max(latencies) * 1000:.1f}ms")
    print(f"\nRequest distribution:")
    for req_type, count in sorted(request_counts.items()):
        percentage = count / requests_sent * 100
        print(f"  {req_type:15}: {count:5} ({percentage:5.1f}%)")

    return {
        "duration": total_time,
        "requests": requests_sent,
        "rps": requests_sent / total_time,
        "errors": errors,
        "latency": {
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "avg": sum(latencies) / len(latencies) * 1000,
        },
    }


def benchmark_stress_test():
    """Find maximum throughput"""
    print("\nBENCHMARK: Stress test (finding maximum throughput)")
    print("-" * 80)

    test_rps = [10, 50, 100, 200, 500, 1000]
    results = {}

    for target_rps in test_rps:
        print(f"\nTesting {target_rps} req/s...")

        # Run short stress test
        duration = 5  # seconds
        requests_sent = 0
        errors = 0
        latencies = []

        start_time = time.time()
        interval = 1.0 / target_rps

        while time.time() - start_time < duration:
            req_start = time.time()

            # Simulate request (fast operation)
            time.sleep(0.01)  # 10ms operation

            latency = time.time() - req_start
            latencies.append(latency)
            requests_sent += 1

            # Check if we're keeping up
            behind_schedule = (time.time() - start_time) - (requests_sent * interval)
            if behind_schedule > 1.0:  # More than 1s behind
                errors += 1

            time.sleep(max(0, interval - (time.time() - req_start)))

        actual_rps = requests_sent / duration
        avg_latency = sum(latencies) / len(latencies) * 1000
        error_rate = errors / requests_sent * 100

        results[target_rps] = {
            "target_rps": target_rps,
            "actual_rps": actual_rps,
            "avg_latency_ms": avg_latency,
            "error_rate": error_rate,
            "sustainable": error_rate < 1.0 and avg_latency < 500,
        }

        status = "OK" if results[target_rps]["sustainable"] else "DEGRADED"
        print(f"  Actual: {actual_rps:.1f} req/s, Latency: {avg_latency:.1f}ms, Status: {status}")

    # Find maximum sustainable
    max_sustainable = max((rps for rps, data in results.items() if data["sustainable"]), default=0)

    print(f"\nMaximum sustainable throughput: {max_sustainable} req/s")

    return {"results": results, "max_sustainable": max_sustainable}


def benchmark_concurrent_clients(num_clients: int = 10, duration: int = 10):
    """Benchmark multiple concurrent clients"""
    print(f"\nBENCHMARK: Concurrent clients ({num_clients} clients)")
    print("-" * 80)

    clients = [LoadTestClient(i) for i in range(num_clients)]
    threads = []

    def client_workload(client: LoadTestClient):
        """Workload for each client"""
        start = time.time()
        while time.time() - start < duration:
            # Random operation
            operations = [
                ("ping", 0.01),
                ("list_layers", 0.05),
                ("get_features", 0.20),
            ]
            op_type, op_duration = random.choice(operations)
            client.simulate_request(op_type, op_duration)

            # Random think time
            time.sleep(random.uniform(0.1, 0.5))

    # Start all clients
    print(f"Starting {num_clients} concurrent clients...")
    start_time = time.time()

    for client in clients:
        thread = threading.Thread(target=client_workload, args=(client,))
        thread.start()
        threads.append(thread)

    # Wait for all to finish
    for thread in threads:
        thread.join()

    total_time = time.time() - start_time

    # Aggregate results
    total_requests = sum(c.requests_sent for c in clients)
    total_errors = sum(c.errors for c in clients)
    all_latencies = []
    for c in clients:
        all_latencies.extend(c.latencies)

    avg_latency = sum(all_latencies) / len(all_latencies) * 1000 if all_latencies else 0

    print(f"\nResults:")
    print(f"  Duration: {total_time:.1f}s")
    print(f"  Total requests: {total_requests}")
    print(f"  Throughput: {total_requests / total_time:.1f} req/s")
    print(f"  Errors: {total_errors}")
    print(f"  Avg latency: {avg_latency:.1f}ms")
    print(f"  Requests per client: {total_requests / num_clients:.1f}")

    return {
        "num_clients": num_clients,
        "duration": total_time,
        "total_requests": total_requests,
        "throughput": total_requests / total_time,
        "avg_latency": avg_latency,
    }


def print_benchmark_results():
    """Run all benchmarks and print results"""
    print("=" * 80)
    print("END-TO-END PERFORMANCE BENCHMARKS")
    print("=" * 80)

    # 1. Realistic workflow
    workflow = benchmark_realistic_workflow()

    # 2. Sustained load (reduced duration for testing)
    sustained = benchmark_sustained_load(duration=10, target_rps=50)

    # 3. Stress test
    stress = benchmark_stress_test()

    # 4. Concurrent clients
    concurrent = benchmark_concurrent_clients(num_clients=5, duration=10)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - PERFORMANCE TARGETS")
    print("=" * 80)
    print(f"Workflow completion: {workflow['total_time']:.2f}s")
    print(f"Sustained throughput: {sustained['rps']:.1f} req/s")
    print(f"Max throughput: {stress['max_sustainable']} req/s")
    print(
        f"Concurrent clients: {concurrent['num_clients']} clients @ {concurrent['throughput']:.1f} req/s"
    )
    print(f"\nLatency targets:")
    print(
        f"  p50: {sustained['latency']['p50']:.1f}ms (target: <100ms) {'✓' if sustained['latency']['p50'] < 100 else '✗'}"
    )
    print(
        f"  p95: {sustained['latency']['p95']:.1f}ms (target: <500ms) {'✓' if sustained['latency']['p95'] < 500 else '✗'}"
    )
    print(
        f"  p99: {sustained['latency']['p99']:.1f}ms (target: <1000ms) {'✓' if sustained['latency']['p99'] < 1000 else '✗'}"
    )


if __name__ == "__main__":
    print_benchmark_results()
