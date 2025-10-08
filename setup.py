#!/usr/bin/env python3
"""
QGIS MCP - Setup Script

Unified package with:
- MCP Server for Claude Desktop
- Python Client for scripting
- QGIS Plugin (secure server)
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="qgis-mcp",
    version="1.0.0",
    description="Control QGIS with AI (Claude Desktop) or Python - Secure MCP server and client",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="QGIS MCP Contributors",
    author_email="",
    url="https://github.com/JNZader/qgis_mcp",
    license="MIT",

    packages=find_packages(where="src") + ["qgis_mcp_plugin"],
    package_dir={"": "src"},

    # Include QGIS plugin
    package_data={
        "qgis_mcp_plugin": ["*.txt", "*.md"],
    },

    python_requires=">=3.7",

    install_requires=[
        # Protocol dependencies
        "msgpack>=1.0.7",
        "jsonschema>=4.20.0",
        # Security
        "cryptography>=41.0.7",
        "keyring>=24.3.0",
        # Additional
        "certifi>=2023.11.17",
    ],

    extras_require={
        "dev": [
            # Testing
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "pytest-xdist>=3.5.0",
            "pytest-timeout>=2.2.0",
            "pytest-mock>=3.12.0",
            # Code Quality
            "black>=23.12.1",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
            "radon>=6.0.1",
            # Security
            "bandit>=1.7.6",
            "safety>=3.0.1",
            "pip-audit>=2.6.3",
            # Pre-commit
            "pre-commit>=3.6.0",
        ],
        "tls": [
            "pyOpenSSL>=23.3.0",
        ],
    },

    entry_points={
        "console_scripts": [
            # MCP Server for Claude Desktop
            "qgis-mcp-server=qgis_mcp_server:main",
        ],
    },

    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Communications",
        "Framework :: AsyncIO",
    ],

    keywords="qgis gis mcp claude ai geospatial python automation",

    project_urls={
        "Documentation": "https://github.com/JNZader/qgis_mcp",
        "Source": "https://github.com/JNZader/qgis_mcp",
        "Tracker": "https://github.com/JNZader/qgis_mcp/issues",
        "Changelog": "https://github.com/JNZader/qgis_mcp/blob/main/CHANGELOG.md",
    },
)
