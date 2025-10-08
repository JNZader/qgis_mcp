"""
QGIS MCP Server - Model Context Protocol Server for QGIS

This MCP server allows Claude Desktop (and other MCP clients) to interact with QGIS.

Usage with Claude Desktop:
    Add to claude_desktop_config.json:

    {
      "mcpServers": {
        "qgis": {
          "command": "python",
          "args": ["-m", "qgis_mcp_server"],
          "env": {
            "QGIS_PREFIX_PATH": "C:\\Program Files\\QGIS 3.28"
          }
        }
      }
    }
"""

__version__ = "1.0.0"

from .server import main

__all__ = ["main"]
