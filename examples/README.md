# QGIS MCP Examples

Complete working examples demonstrating all major features.

---

## Quick Start

**Prerequisites:**
1. QGIS MCP Server running in QGIS (port 9876)
2. Authentication token set in environment variable
3. Client library installed

**Setup:**

```bash
# Set your token (get it from QGIS message log)
export QGIS_MCP_TOKEN="your-token-here"

# Install client
cd ..
pip install -e .
```

---

## Examples

### 1. Basic Usage (`basic_usage.py`)

**What it demonstrates:**
- Connecting to the server
- Listing layers
- Getting features
- Simple geoprocessing (buffer)
- Performance statistics

**Run it:**
```bash
python basic_usage.py
```

**Expected output:**
```
✓ Connected to QGIS 3.28.0
✓ Found 3 layers
✓ Retrieved 5 features
✓ Buffer created successfully!
```

**Use this when:** You're learning the basics or testing your setup

---

### 2. Geoprocessing Workflow (`geoprocessing_workflow.py`)

**What it demonstrates:**
- Complete geoprocessing pipeline
- Multiple processing steps (buffer → dissolve → clip)
- Field calculations
- Statistics extraction
- Exporting results

**Run it:**
```bash
python geoprocessing_workflow.py
```

**Expected output:**
```
✓ Buffer created
✓ Dissolved
✓ Clipped to study area
✓ Area calculated
Total area: 1,234.56 km²
```

**Use this when:** You need to chain multiple geoprocessing operations

**Requirements:**
- At least 2 vector layers loaded in QGIS

---

### 3. Map Rendering (`map_rendering.py`)

**What it demonstrates:**
- Rendering maps at different resolutions
- Multiple export formats (PNG, JPG, PDF)
- Custom extents
- Batch rendering

**Run it:**
```bash
python map_rendering.py
```

**Expected output:**
```
✓ Saved: map_outputs/map_screen.png (1920x1080, 96 DPI)
✓ Saved: map_outputs/map_print.pdf (A4, 300 DPI)
✓ Saved: map_outputs/map_compressed.jpg
```

**Use this when:** You need to generate map images programmatically

**Output:** Files in `map_outputs/` directory

---

### 4. Async Operations (`async_operations.py`)

**What it demonstrates:**
- Running long operations asynchronously
- Progress monitoring
- Parallel operations
- Canceling operations

**Run it:**
```bash
python async_operations.py
```

**Expected output:**
```
✓ Operation started: abc12345...
Progress: [████████████████░░░░░░] 75%
✓ Operation completed!
```

**Use this when:** You have long-running operations (large datasets, complex algorithms)

---

### 5. Advanced Client (`advanced_client.py`)

**What it demonstrates:**
- Connection pooling
- Retry logic
- Error handling
- Performance optimization

**Run it:**
```bash
python advanced_client.py
```

**Use this when:** Building production applications with high performance requirements

---

## Running All Examples

```bash
# Make sure server is running and token is set
export QGIS_MCP_TOKEN="your-token"

# Run all examples
for script in *.py; do
    echo "Running $script..."
    python "$script"
    echo ""
done
```

---

## Troubleshooting

### "Connection refused"

**Problem:** Can't connect to server

**Solutions:**
1. Check if server is running in QGIS:
   ```python
   # In QGIS Python Console
   from qgis_mcp_plugin import start_optimized_server
   server = start_optimized_server(port=9876)
   ```

2. Verify port number (default: 9876)
3. Check firewall settings

### "Authentication failed"

**Problem:** Token rejected

**Solutions:**
1. Copy correct token from QGIS message log
2. Set environment variable:
   ```bash
   export QGIS_MCP_TOKEN="paste-token-here"
   ```
3. Check for spaces or newlines in token

### "No layers found"

**Problem:** Examples need layers but none loaded

**Solution:**
Load some sample data in QGIS first:
1. Open QGIS
2. `Layer → Add Layer → Add Vector Layer`
3. Load any shapefile/GeoJSON/GeoPackage

### "Module not found: qgis_mcp"

**Problem:** Client library not installed

**Solution:**
```bash
cd /path/to/qgis_mcp
pip install -e .
```

---

## Creating Your Own Examples

**Template:**

```python
#!/usr/bin/env python3
"""
My Custom Example

Description of what this example does.
"""

from qgis_mcp import connect
import os

def main():
    token = os.getenv('QGIS_MCP_TOKEN')
    if not token:
        print("ERROR: Set QGIS_MCP_TOKEN environment variable")
        return

    with connect(port=9876, token=token) as client:
        # Your code here
        layers = client.list_layers()
        print(f"Found {len(layers)} layers")

if __name__ == "__main__":
    main()
```

**Run it:**
```bash
chmod +x my_example.py
python my_example.py
```

---

## Next Steps

- **User Guide:** `../docs/USER_GUIDE.md` - Complete usage guide
- **API Reference:** `../docs/api-reference.md` - All available methods
- **Troubleshooting:** `../docs/troubleshooting.md` - Common issues

---

## Need Help?

- **GitHub Issues:** Report bugs or request features
- **GitHub Discussions:** Ask questions
- **Documentation:** Check `docs/` directory

Happy mapping! 🗺️
