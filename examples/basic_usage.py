#!/usr/bin/env python3
"""
Basic QGIS MCP Usage Example

This example demonstrates the fundamental operations:
- Connecting to the server
- Listing layers
- Getting features
- Basic geoprocessing

Prerequisites:
- QGIS MCP Server running in QGIS (port 9876)
- Authentication token set in environment variable QGIS_MCP_TOKEN
"""

from qgis_mcp import connect
import os

def main():
    # Get token from environment variable
    token = os.getenv('QGIS_MCP_TOKEN')
    if not token:
        print("ERROR: Please set QGIS_MCP_TOKEN environment variable")
        print("Example: export QGIS_MCP_TOKEN='your-token-here'")
        return

    print("=" * 60)
    print("QGIS MCP - Basic Usage Example")
    print("=" * 60)

    # Connect to QGIS
    with connect(port=9876, token=token) as client:
        # Test connection
        print("\n[1/5] Testing connection...")
        info = client.get_qgis_info()
        print(f"✓ Connected to QGIS {info['version']}")
        print(f"  Platform: {info['platform']}")

        # List layers
        print("\n[2/5] Listing layers...")
        layers = client.list_layers()
        print(f"✓ Found {len(layers)} layers:")

        for i, layer in enumerate(layers, 1):
            print(f"  {i}. {layer['name']}")
            print(f"     Type: {layer['type']}")
            print(f"     Features: {layer['feature_count']}")
            print(f"     CRS: {layer['crs']}")

        if not layers:
            print("  (No layers loaded. Load some layers in QGIS first!)")
            return

        # Get features from first layer
        print("\n[3/5] Getting features from first layer...")
        layer_id = layers[0]['id']
        layer_name = layers[0]['name']

        features = client.get_features(
            layer_id=layer_id,
            limit=5  # Get first 5 features
        )

        print(f"✓ Retrieved {len(features)} features from '{layer_name}':")

        for i, feature in enumerate(features, 1):
            print(f"\n  Feature {i}:")
            print(f"    ID: {feature['id']}")
            print(f"    Attributes: {feature['attributes']}")
            print(f"    Geometry: {feature['geometry'][:50]}...")  # First 50 chars

        # Execute simple processing
        if len(layers) > 0 and layers[0]['type'] == 'vector':
            print("\n[4/5] Running buffer operation...")

            try:
                result = client.execute_processing(
                    algorithm="native:buffer",
                    parameters={
                        "INPUT": layer_id,
                        "DISTANCE": 1000,  # 1000 meters
                        "SEGMENTS": 10,
                        "OUTPUT": "memory:"  # In-memory layer
                    }
                )

                buffered_layer_id = result['OUTPUT']
                print(f"✓ Buffer created successfully!")
                print(f"  Output layer ID: {buffered_layer_id}")

            except Exception as e:
                print(f"✗ Buffer operation failed: {e}")
        else:
            print("\n[4/5] Skipping buffer (no vector layers)")

        # Get performance stats
        print("\n[5/5] Getting performance statistics...")
        stats = client.get_performance_stats()

        print(f"✓ Server performance:")
        print(f"  Total requests: {stats.get('total_requests', 0)}")
        print(f"  Cache hits: {stats.get('cache_hits', 0)}")
        print(f"  Cache misses: {stats.get('cache_misses', 0)}")

        if stats.get('cache_hits', 0) + stats.get('cache_misses', 0) > 0:
            hit_rate = stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses']) * 100
            print(f"  Cache hit rate: {hit_rate:.1f}%")

    print("\n" + "=" * 60)
    print("✓ Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
