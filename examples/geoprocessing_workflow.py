#!/usr/bin/env python3
"""
Geoprocessing Workflow Example

This example demonstrates a complete geoprocessing workflow:
1. Load input data
2. Buffer points
3. Dissolve buffers
4. Clip to study area
5. Calculate statistics
6. Export results

Prerequisites:
- QGIS MCP Server running
- Sample data files (or use your own)
"""

from qgis_mcp import connect
import os
from pathlib import Path

def main():
    token = os.getenv('QGIS_MCP_TOKEN')
    if not token:
        print("ERROR: Set QGIS_MCP_TOKEN environment variable")
        return

    print("=" * 70)
    print("QGIS MCP - Geoprocessing Workflow Example")
    print("=" * 70)

    with connect(port=9876, token=token) as client:
        print("\n[Step 1/6] Loading layers...")

        # Get existing layers
        layers = client.list_layers()

        if len(layers) < 2:
            print("ERROR: This example needs at least 2 vector layers loaded in QGIS")
            print("Please load some sample data first!")
            return

        # Use first two layers
        input_layer = layers[0]
        clip_layer = layers[1]

        print(f"✓ Input layer: {input_layer['name']} ({input_layer['feature_count']} features)")
        print(f"✓ Clip layer: {clip_layer['name']} ({clip_layer['feature_count']} features)")

        # Step 2: Buffer
        print("\n[Step 2/6] Creating buffer (5km)...")

        buffer_result = client.execute_processing(
            algorithm="native:buffer",
            parameters={
                "INPUT": input_layer['id'],
                "DISTANCE": 5000,  # 5 kilometers
                "SEGMENTS": 16,
                "END_CAP_STYLE": 0,  # Round
                "JOIN_STYLE": 0,  # Round
                "DISSOLVE": False,
                "OUTPUT": "memory:buffered"
            }
        )

        buffered_layer_id = buffer_result['OUTPUT']
        print(f"✓ Buffer created: {buffered_layer_id}")

        # Step 3: Dissolve
        print("\n[Step 3/6] Dissolving buffers...")

        dissolve_result = client.execute_processing(
            algorithm="native:dissolve",
            parameters={
                "INPUT": buffered_layer_id,
                "FIELD": [],  # Dissolve all into one
                "OUTPUT": "memory:dissolved"
            }
        )

        dissolved_layer_id = dissolve_result['OUTPUT']
        print(f"✓ Dissolved: {dissolved_layer_id}")

        # Step 4: Clip
        print("\n[Step 4/6] Clipping to study area...")

        clip_result = client.execute_processing(
            algorithm="native:clip",
            parameters={
                "INPUT": dissolved_layer_id,
                "OVERLAY": clip_layer['id'],
                "OUTPUT": "memory:clipped"
            }
        )

        clipped_layer_id = clip_result['OUTPUT']
        print(f"✓ Clipped: {clipped_layer_id}")

        # Step 5: Calculate area
        print("\n[Step 5/6] Calculating area...")

        area_result = client.execute_processing(
            algorithm="qgis:fieldcalculator",
            parameters={
                "INPUT": clipped_layer_id,
                "FIELD_NAME": "area_km2",
                "FIELD_TYPE": 0,  # Float
                "FIELD_LENGTH": 10,
                "FIELD_PRECISION": 2,
                "FORMULA": "$area / 1000000",  # Convert m² to km²
                "OUTPUT": "memory:with_area"
            }
        )

        final_layer_id = area_result['OUTPUT']
        print(f"✓ Area calculated: {final_layer_id}")

        # Step 6: Get statistics
        print("\n[Step 6/6] Extracting statistics...")

        # Get features from final layer
        final_features = client.get_features(
            layer_id=final_layer_id,
            limit=100
        )

        total_area = sum(f['attributes'].get('area_km2', 0) for f in final_features)

        print(f"✓ Analysis complete!")
        print(f"\nResults:")
        print(f"  - Input features: {input_layer['feature_count']}")
        print(f"  - Buffered features: {len(final_features)}")
        print(f"  - Total area: {total_area:,.2f} km²")

        # Optional: Export to file
        print("\n[Optional] Exporting to file...")

        export_path = "/tmp/geoprocessing_result.gpkg"  # Change as needed

        try:
            export_result = client.execute_processing(
                algorithm="native:package",
                parameters={
                    "LAYERS": [final_layer_id],
                    "OUTPUT": export_path,
                    "OVERWRITE": True
                }
            )

            print(f"✓ Exported to: {export_path}")

        except Exception as e:
            print(f"✗ Export failed: {e}")
            print(f"  (You can manually save the 'with_area' layer in QGIS)")

    print("\n" + "=" * 70)
    print("✓ Geoprocessing workflow completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
