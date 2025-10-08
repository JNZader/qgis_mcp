# Complete Setup Guide

Step-by-step instructions to get QGIS working in Claude Desktop.

---

## 📋 Prerequisites

Before you begin, make sure you have:

- ✅ **Claude Desktop** installed ([Download here](https://claude.ai/download))
- ✅ **QGIS 3.10+** installed ([Download here](https://qgis.org/download))
- ✅ **Python 3.7+** (usually comes with QGIS)
- ✅ **pip** (Python package installer)

---

## 🚀 Installation Steps

### Step 1: Install QGIS MCP Server

**Option A: From source (recommended for now)**

```bash
# Clone or download this repository
cd qgis_mcp_claude

# Install the MCP server
pip install -e .
```

**Option B: From PyPI (when published)**

```bash
pip install qgis-mcp-server
```

**Verify installation:**

```bash
python -m qgis_mcp_server --version
# Should output: 1.0.0
```

---

### Step 2: Find Your QGIS Installation Path

You need to know where QGIS is installed on your system.

#### Windows

**Common locations:**
```
C:\Program Files\QGIS 3.28
C:\Program Files\QGIS 3.34
C:\OSGeo4W\apps\qgis
C:\OSGeo4W64\apps\qgis
```

**How to find it:**
1. Open QGIS Desktop
2. Go to `Settings → Options → System`
3. Look for "QGIS_PREFIX_PATH" - that's your path!

**Or check in File Explorer:**
```
C:\Program Files\
```
Look for folders starting with "QGIS"

#### macOS

**Common location:**
```
/Applications/QGIS.app
```

**How to find it:**
1. Open Finder
2. Go to Applications
3. Find QGIS
4. Right-click → Show Package Contents
5. The full path is `/Applications/QGIS.app`

#### Linux

**Common locations:**
```
/usr
/usr/local
/opt/qgis
```

**How to find it:**
```bash
which qgis
# Usually shows: /usr/bin/qgis

# QGIS prefix is typically:
/usr
```

---

### Step 3: Configure Claude Desktop

#### Find Claude Desktop Config File

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```
Full path: `C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json`

**macOS:**
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

**If the file doesn't exist:**
Create it! The directory should exist after installing Claude Desktop.

```bash
# Windows (PowerShell)
New-Item -ItemType File -Path "$env:APPDATA\Claude\claude_desktop_config.json"

# macOS/Linux
touch ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

#### Edit Configuration File

Open the config file in a text editor and add:

**Windows Configuration:**

```json
{
  "mcpServers": {
    "qgis": {
      "command": "python",
      "args": [
        "-m",
        "qgis_mcp_server"
      ],
      "env": {
        "QGIS_PREFIX_PATH": "C:\\Program Files\\QGIS 3.28",
        "PYTHONPATH": "C:\\Program Files\\QGIS 3.28\\apps\\qgis\\python",
        "PATH": "C:\\Program Files\\QGIS 3.28\\bin;C:\\Program Files\\QGIS 3.28\\apps\\qgis\\bin"
      }
    }
  }
}
```

**⚠️ IMPORTANT:**
- Replace `C:\\Program Files\\QGIS 3.28` with YOUR QGIS path (from Step 2)
- Use double backslashes `\\` in Windows paths
- Update the version number (3.28, 3.34, etc.) to match your installation

**macOS Configuration:**

```json
{
  "mcpServers": {
    "qgis": {
      "command": "python3",
      "args": [
        "-m",
        "qgis_mcp_server"
      ],
      "env": {
        "QGIS_PREFIX_PATH": "/Applications/QGIS.app/Contents/MacOS",
        "PYTHONPATH": "/Applications/QGIS.app/Contents/Resources/python",
        "DYLD_LIBRARY_PATH": "/Applications/QGIS.app/Contents/MacOS/lib"
      }
    }
  }
}
```

**Linux Configuration:**

```json
{
  "mcpServers": {
    "qgis": {
      "command": "python3",
      "args": [
        "-m",
        "qgis_mcp_server"
      ],
      "env": {
        "QGIS_PREFIX_PATH": "/usr",
        "PYTHONPATH": "/usr/share/qgis/python",
        "LD_LIBRARY_PATH": "/usr/lib"
      }
    }
  }
}
```

---

### Step 4: Restart Claude Desktop

**Completely close and reopen Claude Desktop:**

**Windows:**
1. Right-click Claude in system tray
2. Click "Quit"
3. Reopen Claude Desktop

**macOS:**
1. Press Cmd+Q to quit
2. Reopen from Applications

**Linux:**
1. Close all Claude windows
2. Kill process if needed: `pkill claude`
3. Reopen Claude Desktop

---

### Step 5: Test the Connection

In Claude Desktop, try this:

```
List all available QGIS tools
```

**Expected response:**

Claude should list 10 tools:
- list_layers
- add_vector_layer
- get_layer_info
- get_features
- buffer_layer
- clip_layer
- calculate_statistics
- export_map
- load_project
- save_project

**If it works:** 🎉 You're all set!

**If not:** See Troubleshooting below

---

## 🔧 Troubleshooting

### Problem: "Server not found" or "Connection failed"

**Check 1: Verify installation**
```bash
python -m qgis_mcp_server
```
Should start without errors (will wait for input)

Press Ctrl+C to exit

**Check 2: Verify QGIS Python**
```bash
python -c "from qgis.core import QgsApplication; print('QGIS OK')"
```
Should print "QGIS OK"

If it fails:
- Your QGIS_PREFIX_PATH is wrong
- QGIS Python packages not in Python path

**Check 3: Check server logs**

Look for: `qgis_mcp_server.log` in:
- Windows: `C:\Users\YourUsername\qgis_mcp_server.log`
- macOS/Linux: `~/qgis_mcp_server.log`

Open it to see error details

---

### Problem: "QGIS not found" or Import errors

**Solution 1: Fix QGIS_PREFIX_PATH**

Your path is wrong. To find the correct path:

**Windows:**
```powershell
# Open PowerShell
dir "C:\Program Files" | findstr QGIS
# Shows: QGIS 3.28, QGIS 3.34, etc.

# Your path is likely:
# C:\Program Files\QGIS 3.XX
```

**macOS:**
```bash
ls -la /Applications | grep QGIS
# Shows: QGIS.app

# Your path is:
# /Applications/QGIS.app
```

**Linux:**
```bash
dpkg -L qgis | grep bin/qgis
# Shows install location

# Prefix is usually: /usr
```

**Solution 2: Fix PYTHONPATH**

PYTHONPATH must point to QGIS Python packages.

**Windows:**
```
PYTHONPATH = C:\Program Files\QGIS 3.28\apps\qgis\python
```

**macOS:**
```
PYTHONPATH = /Applications/QGIS.app/Contents/Resources/python
```

**Linux:**
```
PYTHONPATH = /usr/share/qgis/python
```

Test it:
```bash
# Windows
python -c "import sys; sys.path.append('C:\\Program Files\\QGIS 3.28\\apps\\qgis\\python'); from qgis.core import QgsApplication; print('OK')"

# macOS/Linux
python3 -c "import sys; sys.path.append('/usr/share/qgis/python'); from qgis.core import QgsApplication; print('OK')"
```

---

### Problem: Config file not being read

**Check 1: File location**

Make sure the config file is in the RIGHT place:

**Windows:**
```
C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json
```

**Not in:**
- Desktop
- Documents
- Claude install directory

**macOS:**
```
/Users/YourUsername/Library/Application Support/Claude/claude_desktop_config.json
```

**Check 2: Valid JSON**

Copy your config to [JSONLint](https://jsonlint.com/) to validate.

Common errors:
- Missing commas
- Missing quotes
- Wrong brackets

**Check 3: Restart properly**

You MUST completely quit and reopen Claude Desktop.

Closing the window is NOT enough!

---

### Problem: Permission Denied

**Windows Solution:**

Run as administrator (once):
```powershell
# Right-click PowerShell → Run as Administrator
pip install -e . --user
```

**macOS/Linux Solution:**

```bash
# Use --user flag
pip install -e . --user

# Or use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

---

### Problem: Tools appear but fail to execute

**Common causes:**

1. **No QGIS project loaded**
   - Tools need an active QGIS project
   - Solution: Create/load a project first

2. **Wrong layer names**
   - Layer names are case-sensitive
   - Solution: Use exact names from `list_layers`

3. **Invalid paths**
   - Use absolute paths, not relative
   - Solution: `C:\full\path\to\file.shp` not `file.shp`

4. **CRS issues**
   - Layers in different coordinate systems
   - Solution: Reproject layers first

---

## ✅ Verification Checklist

Go through this checklist to ensure everything is set up:

- [ ] QGIS Desktop installed and working
- [ ] Python can import QGIS: `python -c "from qgis.core import QgsApplication"`
- [ ] MCP server installed: `python -m qgis_mcp_server`
- [ ] Config file exists at correct location
- [ ] Config file has correct QGIS paths
- [ ] Config file is valid JSON
- [ ] Claude Desktop completely restarted
- [ ] Claude can list QGIS tools

If all checked, you should be good to go!

---

## 🎓 Next Steps

Now that you're set up:

1. **Try examples:** See `docs/CONVERSATION_EXAMPLES.md`
2. **Load some data:** Ask Claude to load a shapefile
3. **Explore tools:** Ask "What can you do with QGIS?"
4. **Run analysis:** Try a buffer or clip operation

---

## 🆘 Still Having Issues?

If you've tried everything and it still doesn't work:

1. **Check logs:** `qgis_mcp_server.log`
2. **Test manually:**
   ```bash
   python -m qgis_mcp_server
   # Paste this:
   {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
   # Press Enter
   # Should see a response
   ```
3. **Create an issue:** Include:
   - Operating system
   - QGIS version
   - Python version
   - Error messages
   - Config file (remove sensitive paths)

---

**Good luck!** 🚀
