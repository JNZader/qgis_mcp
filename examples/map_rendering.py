#!/usr/bin/env python3
"""
Map Rendering Example

This example demonstrates:
- Rendering maps at different resolutions
- Exporting to different formats (PNG, JPG, PDF)
- Rendering specific extents
- Batch map generation

Prerequisites:
- QGIS MCP Server running
- At least one layer loaded in QGIS
"""

from qgis_mcp import connect
import os
from pathlib import Path

def main():
    token = os.getenv('QGIS_MCP_TOKEN')
    if not token:
        print("ERROR: Set QGIS_MCP_TOKEN environment variable")
        return

    # Create output directory
    output_dir = Path("map_outputs")
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("QGIS MCP - Map Rendering Example")
    print("=" * 70)
    print(f"\nOutput directory: {output_dir.absolute()}")

    with connect(port=9876, token=token) as client:
        # Check if layers are loaded
        print("\n[1/5] Checking layers...")
        layers = client.list_layers()

        if not layers:
            print("ERROR: No layers loaded in QGIS!")
            print("Please load some layers first.")
            return

        print(f"✓ Found {len(layers)} layers")

        # Render 1: Screen resolution (96 DPI)
        print("\n[2/5] Rendering screen resolution map (96 DPI)...")

        screen_map = client.render_map(
            width=1920,
            height=1080,
            dpi=96,
            format="PNG"
        )

        screen_path = output_dir / "map_screen.png"
        with open(screen_path, "wb") as f:
            f.write(screen_map)

        print(f"✓ Saved: {screen_path}")
        print(f"  Size: {len(screen_map) / 1024:.1f} KB")

        # Render 2: Print resolution (300 DPI)
        print("\n[3/5] Rendering print resolution map (300 DPI, PDF)...")

        print_map = client.render_map(
            width=3300,   # A4 width at 300 DPI
            height=2550,  # A4 height at 300 DPI
            dpi=300,
            format="PDF"
        )

        print_path = output_dir / "map_print.pdf"
        with open(print_path, "wb") as f:
            f.write(print_map)

        print(f"✓ Saved: {print_path}")
        print(f"  Size: {len(print_map) / 1024:.1f} KB")

        # Render 3: JPG (smaller file size)
        print("\n[4/5] Rendering compressed map (JPG)...")

        jpg_map = client.render_map(
            width=1920,
            height=1080,
            dpi=96,
            format="JPG",
            quality=85
        )

        jpg_path = output_dir / "map_compressed.jpg"
        with open(jpg_path, "wb") as f:
            f.write(jpg_map)

        print(f"✓ Saved: {jpg_path}")
        print(f"  Size: {len(jpg_map) / 1024:.1f} KB")

        # Render 4: Custom extent
        print("\n[5/5] Rendering custom extent...")

        # Get extent from first layer
        first_layer = layers[0]
        extent = first_layer.get('extent')

        if extent:
            # Calculate center and zoom out 10%
            xmin, ymin, xmax, ymax = extent
            x_margin = (xmax - xmin) * 0.1
            y_margin = (ymax - ymin) * 0.1

            custom_extent = [
                xmin - x_margin,
                ymin - y_margin,
                xmax + x_margin,
                ymax + y_margin
            ]

            custom_map = client.render_map(
                width=1024,
                height=768,
                dpi=96,
                format="PNG",
                extent=custom_extent
            )

            custom_path = output_dir / "map_custom_extent.png"
            with open(custom_path, "wb") as f:
                f.write(custom_map)

            print(f"✓ Saved: {custom_path}")
            print(f"  Extent: {custom_extent}")

        # Bonus: Batch render multiple formats
        print("\n[Bonus] Batch rendering all formats...")

        formats = {
            "PNG": {"format": "PNG"},
            "JPG": {"format": "JPG", "quality": 90},
            "PDF": {"format": "PDF"},
        }

        for name, params in formats.items():
            print(f"  - Rendering {name}...", end=" ")

            map_data = client.render_map(
                width=800,
                height=600,
                dpi=150,
                **params
            )

            ext = name.lower()
            batch_path = output_dir / f"map_batch.{ext}"

            with open(batch_path, "wb") as f:
                f.write(map_data)

            print(f"✓ ({len(map_data) / 1024:.1f} KB)")

    print("\n" + "=" * 70)
    print("✓ Map rendering completed!")
    print(f"\nGenerated maps in: {output_dir.absolute()}")
    print("\nFiles created:")

    for file in sorted(output_dir.glob("*")):
        size_kb = file.stat().st_size / 1024
        print(f"  - {file.name} ({size_kb:.1f} KB)")

    print("=" * 70)


if __name__ == "__main__":
    main()
