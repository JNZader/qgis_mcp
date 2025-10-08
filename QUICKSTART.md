# Quick Start Guide

Get up and running with QGIS MCP in **5 minutes**.

---

## Step 1: Install (2 minutes)

### Install the Server (QGIS Plugin)

```bash
# Clone the repository
git clone https://github.com/your-username/qgis_mcp.git
cd qgis_mcp

# Copy to QGIS plugins directory
# Windows:
xcopy /E /I qgis_mcp_plugin "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\qgis_mcp_plugin"

# Linux/macOS:
cp -r qgis_mcp_plugin ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

### Install the Client (Python)

```bash
pip install -e .
```

---

## Step 2: Start Server (1 minute)

### In QGIS:

1. Open QGIS
2. `Plugins → Manage and Install Plugins`
3. Enable "QGIS MCP Server"

### In QGIS Python Console:

```python
from qgis_mcp_plugin import start_optimized_server

server = start_optimized_server(port=9876, require_auth=True)
```

### **IMPORTANT:** Copy the authentication token from QGIS message log!

---

## Step 3: Connect (2 minutes)

### Set your token:

```bash
# Linux/macOS
export QGIS_MCP_TOKEN="paste-your-token-here"

# Windows (CMD)
set QGIS_MCP_TOKEN=paste-your-token-here

# Windows (PowerShell)
$env:QGIS_MCP_TOKEN="paste-your-token-here"
```

### Test connection:

```python
from qgis_mcp import connect

with connect(port=9876) as client:
    info = client.get_qgis_info()
    print(f"Connected to QGIS {info['version']}")

    layers = client.list_layers()
    print(f"Found {len(layers)} layers")
```

---

## You're Ready!

✅ Server running in QGIS
✅ Client connected
✅ Token configured

### What's next?

**Try the examples:**

```bash
# Basic operations
python examples/basic_usage.py

# Geoprocessing workflow
python examples/geoprocessing_workflow.py

# Map rendering
python examples/map_rendering.py
```

**Read the docs:**

- **User Guide:** `docs/USER_GUIDE.md` - Complete usage guide
- **API Reference:** `docs/api-reference.md` - All available commands
- **Troubleshooting:** `docs/troubleshooting.md` - Common issues

---

## Common First Steps

### List all layers:

```python
from qgis_mcp import connect

with connect(port=9876) as client:
    layers = client.list_layers()

    for layer in layers:
        print(f"{layer['name']} - {layer['feature_count']} features")
```

### Get features from a layer:

```python
with connect(port=9876) as client:
    layers = client.list_layers()
    layer_id = layers[0]['id']

    features = client.get_features(layer_id, limit=10)

    for feature in features:
        print(feature['attributes'])
```

### Run geoprocessing:

```python
with connect(port=9876) as client:
    result = client.execute_processing(
        algorithm="native:buffer",
        parameters={
            "INPUT": "layer_id_here",
            "DISTANCE": 1000,
            "OUTPUT": "memory:"
        }
    )

    print(f"Buffer created: {result['OUTPUT']}")
```

### Render a map:

```python
with connect(port=9876) as client:
    map_image = client.render_map(
        width=1920,
        height=1080,
        format="PNG"
    )

    with open("map.png", "wb") as f:
        f.write(map_image)
```

---

## Need Help?

- **Troubleshooting:** `docs/troubleshooting.md`
- **Full Guide:** `docs/USER_GUIDE.md`
- **GitHub Issues:** Report bugs
- **GitHub Discussions:** Ask questions

---

**Happy mapping!** 🗺️
