#!/usr/bin/env python3
"""
Async Operations Example

Demonstrates handling long-running operations without blocking:
- Starting async operations
- Monitoring progress
- Getting results
- Running multiple operations in parallel

Prerequisites:
- QGIS MCP Server running with async enabled
- Large dataset for demonstration
"""

from qgis_mcp import connect
import os
import time

def main():
    token = os.getenv('QGIS_MCP_TOKEN')
    if not token:
        print("ERROR: Set QGIS_MCP_TOKEN environment variable")
        return

    print("=" * 70)
    print("QGIS MCP - Async Operations Example")
    print("=" * 70)

    with connect(port=9876, token=token) as client:
        # Get layers
        print("\n[Setup] Getting layers...")
        layers = client.list_layers()

        if not layers or layers[0]['type'] != 'vector':
            print("ERROR: Need at least one vector layer")
            return

        layer_id = layers[0]['id']
        layer_name = layers[0]['name']

        print(f"✓ Using layer: {layer_name}")

        # Example 1: Single async operation
        print("\n[Example 1/3] Single async operation")
        print("-" * 70)

        print("Starting buffer operation (async)...")
        operation_id = client.execute_processing_async(
            algorithm="native:buffer",
            parameters={
                "INPUT": layer_id,
                "DISTANCE": 5000,
                "OUTPUT": "memory:"
            }
        )

        print(f"✓ Operation started: {operation_id}")

        # Monitor progress
        print("Monitoring progress:")
        while True:
            status = client.get_operation_status(operation_id)

            state = status['state']
            progress = status.get('progress', 0)

            if state == 'running':
                print(f"  Progress: {progress}%", end='\r')
                time.sleep(0.5)

            elif state == 'completed':
                print(f"  Progress: 100% - Complete!     ")
                result = client.get_operation_result(operation_id)
                print(f"✓ Result: {result['OUTPUT']}")
                break

            elif state == 'failed':
                print(f"✗ Failed: {status.get('error', 'Unknown error')}")
                break

        # Example 2: Multiple parallel operations
        print("\n[Example 2/3] Multiple parallel operations")
        print("-" * 70)

        # Start multiple buffer operations with different distances
        distances = [1000, 2000, 3000, 5000]
        operations = {}

        print("Starting operations...")
        for distance in distances:
            op_id = client.execute_processing_async(
                algorithm="native:buffer",
                parameters={
                    "INPUT": layer_id,
                    "DISTANCE": distance,
                    "OUTPUT": "memory:"
                }
            )
            operations[op_id] = distance
            print(f"  ✓ Buffer {distance}m: {op_id[:8]}...")

        # Wait for all to complete
        print("\nWaiting for completion...")
        completed = 0

        while completed < len(operations):
            for op_id, distance in operations.items():
                status = client.get_operation_status(op_id)

                if status['state'] == 'completed' and op_id in operations:
                    result = client.get_operation_result(op_id)
                    print(f"  ✓ Buffer {distance}m complete: {result['OUTPUT']}")
                    operations.pop(op_id)  # Remove from tracking
                    completed += 1
                    break  # Restart loop

                elif status['state'] == 'failed':
                    print(f"  ✗ Buffer {distance}m failed")
                    operations.pop(op_id)
                    completed += 1
                    break

            time.sleep(0.5)

        print(f"✓ All operations completed!")

        # Example 3: Progress monitoring with callback
        print("\n[Example 3/3] Progress monitoring with visual indicator")
        print("-" * 70)

        def progress_bar(progress, width=40):
            """Create a progress bar"""
            filled = int(width * progress / 100)
            bar = "█" * filled + "░" * (width - filled)
            return f"[{bar}] {progress}%"

        print("Starting large buffer operation...")
        operation_id = client.execute_processing_async(
            algorithm="native:buffer",
            parameters={
                "INPUT": layer_id,
                "DISTANCE": 10000,
                "SEGMENTS": 32,  # More detail = longer operation
                "OUTPUT": "memory:"
            }
        )

        print(f"Operation ID: {operation_id}\n")

        while True:
            status = client.get_operation_status(operation_id)
            state = status['state']
            progress = status.get('progress', 0)

            if state == 'running':
                print(f"\r{progress_bar(progress)}", end='')
                time.sleep(0.3)

            elif state == 'completed':
                print(f"\r{progress_bar(100)}")
                result = client.get_operation_result(operation_id)
                print(f"\n✓ Operation completed!")
                print(f"  Result: {result['OUTPUT']}")
                break

            elif state == 'failed':
                print(f"\r{progress_bar(progress)}")
                print(f"\n✗ Operation failed: {status.get('error')}")
                break

        # Bonus: Cancel operation
        print("\n[Bonus] Canceling operation")
        print("-" * 70)

        print("Starting operation...")
        operation_id = client.execute_processing_async(
            algorithm="native:buffer",
            parameters={
                "INPUT": layer_id,
                "DISTANCE": 1000,
                "OUTPUT": "memory:"
            }
        )

        print(f"  Operation started: {operation_id[:8]}...")
        time.sleep(1)  # Let it run a bit

        print("  Canceling operation...")
        client.cancel_operation(operation_id)

        # Check status
        status = client.get_operation_status(operation_id)
        print(f"  ✓ Status: {status['state']}")

    print("\n" + "=" * 70)
    print("✓ Async operations example completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
