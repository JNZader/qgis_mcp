# QGIS MCP User Guide

Complete guide for using QGIS MCP Server in your projects.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Working with Layers](#working-with-layers)
5. [Geoprocessing](#geoprocessing)
6. [Map Rendering](#map-rendering)
7. [Project Management](#project-management)
8. [Custom Code Execution](#custom-code-execution)
9. [Performance Optimization](#performance-optimization)
10. [Security Best Practices](#security-best-practices)
11. [Use Cases](#use-cases)

---

## Introduction

QGIS MCP (Model Context Protocol) Server allows you to control QGIS programmatically from external applications. Think of it as a **remote control for QGIS**.

### What can you do?

- **Automate workflows** - Batch process hundreds of files
- **Build web services** - Create GIS REST APIs
- **Integrate with AI** - Let AI agents manipulate spatial data
- **Remote GIS** - Control QGIS from anywhere (via SSH tunnel)
- **Scripting** - Automate repetitive QGIS tasks

### Architecture

```
┌──────────────────┐         ┌──────────────────┐
│  Your Python     │  MCP    │  QGIS MCP        │
│  Application     │ ◄─────► │  Server Plugin   │
│                  │ (Port)  │                  │
└──────────────────┘         └────────┬─────────┘
                                      │
                             ┌────────▼─────────┐
                             │  QGIS Desktop    │
                             │  (PyQGIS)        │
                             └──────────────────┘
```

---

## Installation

### Server Installation (QGIS Plugin)

**Step 1: Install QGIS**

Download from https://qgis.org/ (v3.10 or later)

**Step 2: Install the plugin**

```bash
# Clone repository
git clone https://github.com/your-username/qgis_mcp.git
cd qgis_mcp

# Install to QGIS plugins directory
# Windows:
xcopy /E /I qgis_mcp_plugin "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\qgis_mcp_plugin"

# Linux/macOS:
cp -r qgis_mcp_plugin ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

**Step 3: Enable plugin in QGIS**

1. Open QGIS
2. `Plugins → Manage and Install Plugins`
3. Enable "QGIS MCP Server"

### Client Installation (Python Library)

```bash
# Install from source
cd qgis_mcp
pip install -e .

# Or install from PyPI (when published)
pip install qgis-mcp
```

---

## Getting Started

### Starting the Server

**Option 1: From QGIS Python Console**

```python
from qgis_mcp_plugin import start_optimized_server

server = start_optimized_server(
    port=9876,
    require_auth=True,
    enable_async=True
)
```

**Option 2: From QGIS Plugin Menu**

1. `Plugins → QGIS MCP → Start Server`
2. Configure settings in dialog
3. Click "Start"

**Important:** Copy the authentication token shown in QGIS message log!

### Your First Connection

```python
from qgis_mcp import connect

# Use the token from QGIS
with connect(port=9876, token="YOUR_TOKEN_HERE") as client:
    # Test connection
    info = client.get_qgis_info()
    print(f"Connected to QGIS {info['version']}")

    # List layers
    layers = client.list_layers()
    print(f"Found {len(layers)} layers")
```

### Setting Up Authentication

**Method 1: Environment Variable (Recommended)**

```bash
# Linux/macOS
export QGIS_MCP_TOKEN="your-token-here"

# Windows (CMD)
set QGIS_MCP_TOKEN=your-token-here

# Windows (PowerShell)
$env:QGIS_MCP_TOKEN="your-token-here"
```

```python
# Now connect without token parameter
client = connect(port=9876)
```

**Method 2: Config File**

```python
# Token saved in ~/.qgis_mcp/token
# Connect automatically
client = connect(port=9876)
```

**Method 3: Direct Parameter**

```python
client = connect(port=9876, token="your-token")
```

---

## Working with Layers

### Listing Layers

```python
with connect(port=9876) as client:
    layers = client.list_layers()

    for layer in layers:
        print(f"Name: {layer['name']}")
        print(f"Type: {layer['type']}")  # 'vector' or 'raster'
        print(f"CRS: {layer['crs']}")
        print(f"Features: {layer['feature_count']}")
        print(f"Extent: {layer['extent']}")
        print("---")
```

**Output:**

```
Name: Cities
Type: vector
CRS: EPSG:4326
Features: 150
Extent: [-180.0, -90.0, 180.0, 90.0]
---
```

### Adding Vector Layers

```python
with connect(port=9876) as client:
    # Add Shapefile
    result = client.add_vector_layer(
        path="/path/to/cities.shp",
        name="World Cities"
    )

    layer_id = result['layer_id']
    print(f"Layer added with ID: {layer_id}")

    # Add GeoJSON
    client.add_vector_layer(
        path="/path/to/data.geojson",
        name="My GeoJSON Layer"
    )

    # Add from PostGIS
    client.add_vector_layer(
        path="host=localhost dbname=gis user=postgres password=secret table=cities (geom)",
        provider="postgres",
        name="PostGIS Cities"
    )
```

### Adding Raster Layers

```python
with connect(port=9876) as client:
    # Add GeoTIFF
    result = client.add_raster_layer(
        path="/path/to/elevation.tif",
        name="DEM"
    )

    # Add WMS layer
    client.add_raster_layer(
        path="url=http://example.com/wms?SERVICE=WMS&VERSION=1.3.0",
        provider="wms",
        name="WMS Layer"
    )
```

### Getting Features

**Basic feature retrieval:**

```python
with connect(port=9876) as client:
    layers = client.list_layers()
    layer_id = layers[0]['id']

    # Get first 10 features
    features = client.get_features(
        layer_id=layer_id,
        limit=10
    )

    for feature in features:
        print(f"Feature ID: {feature['id']}")
        print(f"Geometry: {feature['geometry']}")  # WKB format
        print(f"Attributes: {feature['attributes']}")
```

**Spatial filtering (bounding box):**

```python
# Get features in specific area
features = client.get_features(
    layer_id=layer_id,
    bbox=[-10.0, 40.0, 5.0, 50.0],  # [west, south, east, north]
    limit=100
)
```

**Attribute filtering:**

```python
# Get features with specific attribute
features = client.get_features(
    layer_id=layer_id,
    filter_expression="population > 1000000",
    limit=50
)
```

### Working with Geometry

Features use **WKB (Well-Known Binary)** format for efficiency.

**Convert WKB to WKT (human-readable):**

```python
from shapely import wkb, wkt

# Get feature
feature = features[0]
geometry_wkb = feature['geometry']

# Convert to shapely geometry
geom = wkb.loads(bytes.fromhex(geometry_wkb))

# Print as WKT
print(wkt.dumps(geom))
# Output: POINT (10.5 45.3)

# Access coordinates
print(f"X: {geom.x}, Y: {geom.y}")
```

**Working with geometries:**

```python
from shapely import wkb
from shapely.ops import transform
import pyproj

# Get feature geometry
geom_wkb = feature['geometry']
geom = wkb.loads(bytes.fromhex(geom_wkb))

# Calculate area
area = geom.area
print(f"Area: {area}")

# Buffer geometry
buffered = geom.buffer(1000)  # 1000 meters

# Reproject geometry
project = pyproj.Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True).transform
geom_projected = transform(project, geom)
```

---

## Geoprocessing

Execute any QGIS processing algorithm remotely.

### Finding Algorithms

```python
with connect(port=9876) as client:
    algorithms = client.get_processing_algorithms()

    # Filter by name
    buffer_algs = [alg for alg in algorithms if 'buffer' in alg.lower()]
    print(buffer_algs)
```

### Buffer Operation

```python
with connect(port=9876) as client:
    result = client.execute_processing(
        algorithm="native:buffer",
        parameters={
            "INPUT": layer_id,
            "DISTANCE": 1000,  # meters
            "SEGMENTS": 10,
            "END_CAP_STYLE": 0,  # Round
            "JOIN_STYLE": 0,  # Round
            "OUTPUT": "memory:"  # In-memory layer
        }
    )

    buffered_layer_id = result['OUTPUT']
    print(f"Buffered layer: {buffered_layer_id}")
```

### Clip Operation

```python
# Clip layer by polygon
result = client.execute_processing(
    algorithm="native:clip",
    parameters={
        "INPUT": input_layer_id,
        "OVERLAY": clip_layer_id,
        "OUTPUT": "memory:"
    }
)
```

### Intersection

```python
# Find intersection of two layers
result = client.execute_processing(
    algorithm="native:intersection",
    parameters={
        "INPUT": layer1_id,
        "OVERLAY": layer2_id,
        "OUTPUT": "/path/to/output.shp"  # Save to file
    }
)
```

### Dissolve

```python
# Dissolve features by attribute
result = client.execute_processing(
    algorithm="native:dissolve",
    parameters={
        "INPUT": layer_id,
        "FIELD": ["country"],  # Dissolve by country
        "OUTPUT": "memory:"
    }
)
```

### Field Calculator

```python
# Calculate new field
result = client.execute_processing(
    algorithm="qgis:fieldcalculator",
    parameters={
        "INPUT": layer_id,
        "FIELD_NAME": "area_km2",
        "FIELD_TYPE": 0,  # Float
        "FIELD_LENGTH": 10,
        "FIELD_PRECISION": 2,
        "FORMULA": "$area / 1000000",  # Convert to km²
        "OUTPUT": "memory:"
    }
)
```

### Complex Workflow

```python
with connect(port=9876) as client:
    # Step 1: Buffer
    buffered = client.execute_processing(
        algorithm="native:buffer",
        parameters={
            "INPUT": cities_layer_id,
            "DISTANCE": 5000,
            "OUTPUT": "memory:"
        }
    )

    # Step 2: Dissolve buffers
    dissolved = client.execute_processing(
        algorithm="native:dissolve",
        parameters={
            "INPUT": buffered['OUTPUT'],
            "OUTPUT": "memory:"
        }
    )

    # Step 3: Clip to study area
    final = client.execute_processing(
        algorithm="native:clip",
        parameters={
            "INPUT": dissolved['OUTPUT'],
            "OVERLAY": study_area_id,
            "OUTPUT": "/path/to/final_result.shp"
        }
    )

    print(f"Workflow complete: {final['OUTPUT']}")
```

### Async Processing (Long Operations)

For operations that take minutes/hours:

```python
with connect(port=9876) as client:
    # Start operation async
    operation_id = client.execute_processing_async(
        algorithm="native:buffer",
        parameters={...}
    )

    print(f"Operation started: {operation_id}")

    # Monitor progress
    while True:
        status = client.get_operation_status(operation_id)

        if status['state'] == 'completed':
            result = client.get_operation_result(operation_id)
            print(f"Complete: {result}")
            break
        elif status['state'] == 'failed':
            print(f"Failed: {status['error']}")
            break
        else:
            progress = status.get('progress', 0)
            print(f"Progress: {progress}%")
            time.sleep(2)
```

---

## Map Rendering

Generate map images programmatically.

### Basic Map Rendering

```python
with connect(port=9876) as client:
    # Render current map view
    image_bytes = client.render_map(
        width=1920,
        height=1080,
        dpi=300,
        format="PNG"
    )

    # Save to file
    with open("map.png", "wb") as f:
        f.write(image_bytes)
```

### Custom Extent

```python
# Render specific area
image_bytes = client.render_map(
    width=800,
    height=600,
    dpi=96,
    format="PNG",
    extent=[-10.0, 40.0, 5.0, 50.0]  # [west, south, east, north]
)
```

### Export Formats

```python
# PNG (raster, lossless)
png_data = client.render_map(format="PNG")

# JPG (raster, smaller file)
jpg_data = client.render_map(format="JPG", quality=85)

# PDF (vector, for printing)
pdf_data = client.render_map(format="PDF", dpi=300)

# SVG (vector, for editing)
svg_data = client.render_map(format="SVG")
```

### High-Resolution Maps

```python
# For printing (300 DPI)
map_print = client.render_map(
    width=3300,   # A4 width at 300 DPI (11 inches)
    height=2550,  # A4 height at 300 DPI (8.5 inches)
    dpi=300,
    format="PDF"
)
```

### Batch Map Generation

```python
with connect(port=9876) as client:
    # Define map extents
    extents = {
        "north": [-5, 50, 5, 55],
        "center": [-5, 45, 5, 50],
        "south": [-5, 40, 5, 45]
    }

    # Generate maps
    for name, extent in extents.items():
        image = client.render_map(
            width=800,
            height=600,
            extent=extent,
            format="PNG"
        )

        with open(f"map_{name}.png", "wb") as f:
            f.write(image)

    print("All maps generated!")
```

---

## Project Management

### Creating Projects

```python
with connect(port=9876) as client:
    # Create new empty project
    client.create_project()

    # Add layers
    client.add_vector_layer("/path/to/data1.shp", "Layer 1")
    client.add_vector_layer("/path/to/data2.shp", "Layer 2")

    # Save project
    client.save_project("/path/to/my_project.qgs")
```

### Loading Projects

```python
with connect(port=9876) as client:
    # Load existing project
    client.load_project("/path/to/existing_project.qgs")

    # Now work with loaded layers
    layers = client.list_layers()
```

### Project Workflows

```python
with connect(port=9876) as client:
    # 1. Load base project
    client.load_project("/templates/base_map.qgs")

    # 2. Add custom data
    client.add_vector_layer("/data/new_data.shp", "New Data")

    # 3. Run analysis
    result = client.execute_processing(
        algorithm="native:buffer",
        parameters={...}
    )

    # 4. Save as new project
    client.save_project("/projects/analysis_2024.qgs")

    # 5. Render map
    map_image = client.render_map(width=1920, height=1080)
    with open("/output/map.png", "wb") as f:
        f.write(map_image)
```

---

## Custom Code Execution

Execute Python code in QGIS environment (sandboxed for security).

### Basic Code Execution

```python
with connect(port=9876) as client:
    code = """
    from qgis.core import QgsProject

    # Get layer count
    layers = QgsProject.instance().mapLayers()
    result = len(layers)
    """

    layer_count = client.execute_code(code)
    print(f"Layers: {layer_count}")
```

### Working with Layers

```python
code = """
from qgis.core import QgsProject

# Get all layer names
layers = QgsProject.instance().mapLayers()
result = {
    layer_id: layer.name()
    for layer_id, layer in layers.items()
}
"""

layer_names = client.execute_code(code)
print(layer_names)
```

### Custom Analysis

```python
code = """
from qgis.core import QgsProject, QgsFeature

# Calculate total population
layer = QgsProject.instance().mapLayersByName('Cities')[0]
total_pop = sum(f['population'] for f in layer.getFeatures())

result = {
    'total_population': total_pop,
    'feature_count': layer.featureCount(),
    'average_population': total_pop / layer.featureCount()
}
"""

stats = client.execute_code(code)
print(f"Total population: {stats['total_population']:,}")
print(f"Average: {stats['average_population']:,.0f}")
```

### Security Note

Code execution is **sandboxed**. Only safe QGIS operations are allowed:

✅ Allowed:

- `qgis.core` and `qgis.gui` modules
- `PyQt5.QtCore` and `PyQt5.QtGui`
- Math operations
- List/dict operations

❌ Not allowed:

- File system access (`open()`, `os`, `pathlib`)
- Network operations (`urllib`, `requests`)
- System commands (`subprocess`, `os.system`)
- Dangerous imports (`eval`, `exec`, `__import__`)

---

## Performance Optimization

### Enable Async Operations

For better UI responsiveness:

```python
server = start_optimized_server(
    enable_async=True  # Long operations don't block QGIS
)
```

### Adjust Cache Size

For better feature access performance:

```python
server = start_optimized_server(
    cache_size=10000  # Cache up to 10,000 features
)
```

**Recommendations:**

- Small projects (<1000 features): `cache_size=1000`
- Medium projects (1000-10,000 features): `cache_size=5000`
- Large projects (>10,000 features): `cache_size=10000`

### Use Connection Pooling

For high-throughput scenarios:

```python
from qgis_mcp import SecureQGISMCPClient

client = SecureQGISMCPClient(
    host='localhost',
    port=9876,
    token='your-token',
    max_connections=10  # Reuse connections
)

# Use pooled connections
for i in range(100):
    with client.get_connection() as conn:
        layers = conn.list_layers()
```

### Enable Binary Protocol

For faster serialization:

```python
server = start_optimized_server(
    use_msgpack=True  # 1.5-2x faster than JSON
)
```

### Batch Operations

Instead of:

```python
# Slow: 100 separate calls
for feature_id in range(100):
    feature = client.get_feature(layer_id, feature_id)
```

Do:

```python
# Fast: Single call
features = client.get_features(layer_id, limit=100)
```

### Performance Monitoring

```python
with connect(port=9876) as client:
    stats = client.get_performance_stats()

    print(f"Cache hits: {stats['cache_hits']}")
    print(f"Cache misses: {stats['cache_misses']}")
    print(f"Hit rate: {stats['cache_hit_rate']:.1%}")
    print(f"Active async ops: {stats['active_async_operations']}")
```

---

## Security Best Practices

### 1. Always Enable Authentication

```python
# ✅ GOOD
server = start_optimized_server(require_auth=True)

# ❌ BAD - Never do this!
server = start_optimized_server(require_auth=False)
```

### 2. Use TLS/SSL in Production

```python
# ✅ GOOD - Encrypted
server = start_optimized_server(
    require_auth=True,
    use_tls=True
)

client = connect(port=9876, use_tls=True, verify_cert=False)
```

### 3. Bind to Localhost Only

Server automatically binds to `127.0.0.1` (localhost only).

**Never** expose to public internet!

### 4. Use SSH Tunnels for Remote Access

```bash
# On your local machine
ssh -L 9876:localhost:9876 user@remote-server

# Now connect to localhost (tunneled)
python
>>> from qgis_mcp import connect
>>> client = connect(port=9876)
```

### 5. Rotate Tokens Regularly

```python
# Generate new token monthly
server.stop()
server = start_optimized_server(require_auth=True)
# New token displayed in log
```

### 6. Store Tokens Securely

```bash
# ✅ GOOD - Environment variable
export QGIS_MCP_TOKEN="secret-token"

# ✅ GOOD - Encrypted config
# Stored in system keyring

# ❌ BAD - Hardcoded in scripts
client = connect(token="my-secret-token-123")  # Don't commit this!
```

### 7. Monitor Access

```python
with connect(port=9876) as client:
    stats = client.get_performance_stats()

    # Check for unusual activity
    if stats['total_requests'] > 10000:
        print("Warning: High request volume!")
```

---

## Use Cases

### Use Case 1: Automated Map Generation

**Scenario:** Generate 100 maps for different regions every night

```python
import time
from qgis_mcp import connect

regions = [...]  # List of region extents

with connect(port=9876) as client:
    # Load base project
    client.load_project("/templates/region_map.qgs")

    for i, region in enumerate(regions):
        # Update extent
        map_image = client.render_map(
            width=1920,
            height=1080,
            dpi=300,
            extent=region['extent'],
            format="PDF"
        )

        # Save
        with open(f"/output/region_{region['name']}.pdf", "wb") as f:
            f.write(map_image)

        print(f"Generated {i+1}/{len(regions)}")
```

### Use Case 2: GIS REST API

**Scenario:** Build a web service that serves GIS data

```python
from flask import Flask, jsonify, request
from qgis_mcp import connect

app = Flask(__name__)

@app.route('/layers')
def get_layers():
    with connect(port=9876) as client:
        layers = client.list_layers()
    return jsonify(layers)

@app.route('/features/<layer_id>')
def get_features(layer_id):
    bbox = request.args.get('bbox')  # "west,south,east,north"

    with connect(port=9876) as client:
        features = client.get_features(
            layer_id=layer_id,
            bbox=[float(x) for x in bbox.split(',')],
            limit=100
        )
    return jsonify(features)

@app.route('/buffer', methods=['POST'])
def buffer_layer():
    data = request.json
    with connect(port=9876) as client:
        result = client.execute_processing(
            algorithm="native:buffer",
            parameters={
                "INPUT": data['layer_id'],
                "DISTANCE": data['distance'],
                "OUTPUT": "memory:"
            }
        )
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Use Case 3: AI Agent Integration

**Scenario:** Let an AI agent manipulate GIS data

```python
from qgis_mcp import connect

class GISAgent:
    def __init__(self):
        self.client = connect(port=9876).__enter__()

    def analyze_region(self, region_name):
        """AI asks: What's the population in this region?"""
        # Get region layer
        layers = self.client.list_layers()
        region_layer = next(l for l in layers if l['name'] == 'Regions')

        # Filter features
        features = self.client.get_features(
            layer_id=region_layer['id'],
            filter_expression=f"name = '{region_name}'"
        )

        # Calculate total
        total_pop = sum(f['attributes']['population'] for f in features)
        return total_pop

    def create_buffer_map(self, city, distance_km):
        """AI asks: Show me a 10km buffer around this city"""
        # Find city
        layers = self.client.list_layers()
        cities_layer = next(l for l in layers if l['name'] == 'Cities')

        features = self.client.get_features(
            layer_id=cities_layer['id'],
            filter_expression=f"name = '{city}'"
        )

        if not features:
            return None

        # Create buffer
        result = self.client.execute_processing(
            algorithm="native:buffer",
            parameters={
                "INPUT": cities_layer['id'],
                "DISTANCE": distance_km * 1000,  # Convert to meters
                "OUTPUT": "memory:"
            }
        )

        # Render map
        map_image = self.client.render_map(width=800, height=600)
        return map_image

agent = GISAgent()
population = agent.analyze_region("California")
print(f"Population: {population:,}")
```

### Use Case 4: Batch Processing Pipeline

**Scenario:** Process 1000 shapefiles overnight

```python
import os
from pathlib import Path
from qgis_mcp import connect

input_dir = Path("/data/input")
output_dir = Path("/data/output")

with connect(port=9876) as client:
    shapefiles = list(input_dir.glob("*.shp"))

    for i, shapefile in enumerate(shapefiles):
        print(f"Processing {i+1}/{len(shapefiles)}: {shapefile.name}")

        # Add layer
        result = client.add_vector_layer(
            path=str(shapefile),
            name=shapefile.stem
        )
        layer_id = result['layer_id']

        # Process: Reproject to WGS84
        reprojected = client.execute_processing(
            algorithm="native:reprojectlayer",
            parameters={
                "INPUT": layer_id,
                "TARGET_CRS": "EPSG:4326",
                "OUTPUT": "memory:"
            }
        )

        # Process: Simplify
        simplified = client.execute_processing(
            algorithm="native:simplifygeometries",
            parameters={
                "INPUT": reprojected['OUTPUT'],
                "TOLERANCE": 0.001,
                "OUTPUT": str(output_dir / f"{shapefile.stem}_processed.shp")
            }
        )

        print(f"  Saved: {simplified['OUTPUT']}")
```

### Use Case 5: Real-Time Monitoring Dashboard

**Scenario:** Display live GIS data on a dashboard

```python
import streamlit as st
from qgis_mcp import connect

st.title("GIS Monitor Dashboard")

# Connect to QGIS
client = connect(port=9876).__enter__()

# Sidebar
st.sidebar.header("Layers")
layers = client.list_layers()
selected_layer = st.sidebar.selectbox(
    "Select Layer",
    options=[l['name'] for l in layers]
)

# Get layer ID
layer_id = next(l['id'] for l in layers if l['name'] == selected_layer)

# Main content
col1, col2 = st.columns(2)

with col1:
    st.subheader("Layer Info")
    layer_info = next(l for l in layers if l['id'] == layer_id)
    st.write(f"Type: {layer_info['type']}")
    st.write(f"Features: {layer_info['feature_count']}")
    st.write(f"CRS: {layer_info['crs']}")

with col2:
    st.subheader("Statistics")
    features = client.get_features(layer_id, limit=1000)
    st.write(f"Loaded: {len(features)} features")

# Map
st.subheader("Map Preview")
map_image = client.render_map(width=800, height=600, format="PNG")
st.image(map_image)

# Refresh button
if st.button("Refresh"):
    st.rerun()
```

---

## Next Steps

**You're now ready to use QGIS MCP!**

- **Try examples:** See `examples/` directory
- **API reference:** See `docs/api-reference.md`
- **Troubleshooting:** See `docs/troubleshooting.md`
- **Security guide:** See `SECURITY.md`

**Need help?**

- GitHub Issues: Report bugs
- GitHub Discussions: Ask questions
