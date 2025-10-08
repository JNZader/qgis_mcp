# Installation Guide

Complete installation instructions for all platforms.

---

## System Requirements

### Server (QGIS Plugin)

- **QGIS:** 3.10 or later
- **Python:** 3.7+ (included with QGIS)
- **Operating System:** Windows, Linux, or macOS
- **Disk Space:** ~10 MB
- **RAM:** 512 MB minimum (1 GB+ recommended)

### Client (Python Library)

- **Python:** 3.7+
- **pip:** Latest version
- **Operating System:** Any (Windows, Linux, macOS)
- **Disk Space:** ~5 MB

---

## Quick Installation

### 1. Install Server

```bash
# Clone repository
git clone https://github.com/your-username/qgis_mcp.git
cd qgis_mcp

# Install dependencies
pip install -r requirements.txt

# Copy to QGIS plugins directory
# See platform-specific instructions below
```

### 2. Install Client

```bash
pip install -e .
```

### 3. Enable Plugin

1. Open QGIS
2. `Plugins → Manage and Install Plugins`
3. Find "QGIS MCP Server"
4. Click checkbox to enable

---

## Platform-Specific Installation

### Windows

**QGIS Plugin Directory:**
```
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
```

**Installation:**

```batch
REM Method 1: Using xcopy
xcopy /E /I qgis_mcp_plugin "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\qgis_mcp_plugin"

REM Method 2: Manual
REM 1. Open Windows Explorer
REM 2. Navigate to %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\
REM 3. Create folder "qgis_mcp_plugin"
REM 4. Copy all files from qgis_mcp_plugin/ into it
```

**Install client:**

```batch
REM Using pip
pip install -e .

REM Or using Python directly
python -m pip install -e .
```

---

### Linux

**QGIS Plugin Directory:**
```
~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

**Installation:**

```bash
# Install server
cp -r qgis_mcp_plugin ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/

# Install dependencies
pip3 install -r requirements.txt

# Install client
pip3 install -e .
```

**Alternative (using setup script):**

```bash
chmod +x install.sh
./install.sh
```

---

### macOS

**QGIS Plugin Directory:**
```
~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/
```

**Installation:**

```bash
# Install server
cp -r qgis_mcp_plugin ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/

# Install dependencies
pip3 install -r requirements.txt

# Install client
pip3 install -e .
```

---

## Installation from Source

### Clone Repository

```bash
git clone https://github.com/your-username/qgis_mcp.git
cd qgis_mcp
```

### Install Dependencies

**Required:**
```bash
pip install -r requirements.txt
```

**Development (optional):**
```bash
pip install -r requirements-dev.txt
```

### Build from Source

```bash
# Build distribution
python setup.py sdist bdist_wheel

# Install
pip install dist/qgis_mcp-*.whl
```

---

## Docker Installation (Experimental)

**Coming soon!**

```bash
# Pull image
docker pull qgis-mcp/server:latest

# Run container
docker run -p 9876:9876 qgis-mcp/server
```

---

## Verification

### Verify Server Installation

1. Open QGIS
2. Go to `Plugins → Manage and Install Plugins`
3. Search for "QGIS MCP Server"
4. Should appear in "Installed" tab

**Or check Python console:**

```python
# In QGIS Python Console
from qgis_mcp_plugin import __version__
print(f"QGIS MCP Server version: {__version__}")
```

### Verify Client Installation

```bash
# Check installation
python -c "import qgis_mcp; print(qgis_mcp.__version__)"

# Should output: 2.0.0 (or current version)
```

### Full Test

**Start server (in QGIS Python Console):**

```python
from qgis_mcp_plugin import start_optimized_server

server = start_optimized_server(port=9876)
# Copy token from QGIS message log
```

**Test connection (in terminal):**

```python
from qgis_mcp import connect

with connect(port=9876, token="YOUR_TOKEN") as client:
    info = client.get_qgis_info()
    print(f"✓ Connected to QGIS {info['version']}")
```

---

## Troubleshooting Installation

### "Module not found: qgis_mcp"

**Problem:** Client not installed

**Solution:**
```bash
# Ensure you're in the project directory
cd /path/to/qgis_mcp

# Install in editable mode
pip install -e .

# Or install from wheel
pip install dist/qgis_mcp-*.whl
```

### "Plugin not found in QGIS"

**Problem:** Plugin not in correct directory

**Solution:**
1. Check plugin directory path (see platform-specific above)
2. Verify folder name is exactly `qgis_mcp_plugin`
3. Restart QGIS
4. Enable plugin in Plugin Manager

### "Permission denied"

**Problem:** Insufficient permissions

**Solution (Linux/macOS):**
```bash
sudo pip3 install -r requirements.txt
# Or use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Solution (Windows):**
- Run Command Prompt as Administrator
- Or install in user directory: `pip install --user -e .`

### "QGIS plugins directory not found"

**Problem:** Custom QGIS profile

**Solution:**
1. Find your QGIS profile directory:
   - QGIS → Settings → User Profiles → Open Active Profile Folder
2. Navigate to `python/plugins/`
3. Copy `qgis_mcp_plugin/` there

### "Dependency conflicts"

**Problem:** Conflicting Python packages

**Solution:**
```bash
# Use virtual environment
python -m venv qgis_mcp_env
source qgis_mcp_env/bin/activate  # Linux/macOS
# or
qgis_mcp_env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

---

## Upgrading

### Upgrade Server

```bash
# Pull latest code
git pull origin main

# Copy to QGIS plugins directory (overwrite)
# Windows:
xcopy /E /I /Y qgis_mcp_plugin "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\qgis_mcp_plugin"

# Linux/macOS:
cp -rf qgis_mcp_plugin ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/

# Restart QGIS
```

### Upgrade Client

```bash
# From source
git pull origin main
pip install -e . --upgrade

# From PyPI (when published)
pip install --upgrade qgis-mcp
```

---

## Uninstallation

### Uninstall Server

**Method 1: QGIS Plugin Manager**
1. Open QGIS
2. `Plugins → Manage and Install Plugins`
3. Find "QGIS MCP Server"
4. Click "Uninstall"

**Method 2: Manual**

```bash
# Windows
rmdir /S "%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\qgis_mcp_plugin"

# Linux/macOS
rm -rf ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/qgis_mcp_plugin
```

### Uninstall Client

```bash
pip uninstall qgis-mcp
```

---

## Next Steps

After installation:

1. **Quick Start** → [QUICKSTART.md](QUICKSTART.md)
2. **Examples** → [examples/](examples/)
3. **User Guide** → [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

---

## Support

**Installation issues?**

1. Check [Troubleshooting](#troubleshooting-installation) above
2. See [docs/troubleshooting.md](docs/troubleshooting.md)
3. Ask in [GitHub Discussions](https://github.com/your-username/qgis_mcp/discussions)
4. Report bugs in [GitHub Issues](https://github.com/your-username/qgis_mcp/issues)

---

**Installation complete!** Proceed to [QUICKSTART.md](QUICKSTART.md) to start using QGIS MCP.
