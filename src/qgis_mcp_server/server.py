#!/usr/bin/env python3
"""
QGIS MCP Server - MCP Protocol Implementation

This server exposes QGIS functionality through the Model Context Protocol,
allowing Claude Desktop and other MCP clients to interact with QGIS.

Protocol: MCP (Model Context Protocol)
Transport: stdio
Format: JSON-RPC 2.0
"""

import sys
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('qgis_mcp_server.log'), logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


class QGISMCPServer:
    """MCP Server for QGIS integration"""

    def __init__(self):
        self.qgis_app = None
        self.project = None
        self._initialize_qgis()

    def _initialize_qgis(self):
        """Initialize QGIS application"""
        try:
            from qgis.core import QgsApplication, QgsProject

            # Initialize QGIS
            QgsApplication.setPrefixPath(Path(sys.prefix) / "qgis", True)
            self.qgis_app = QgsApplication([], False)
            self.qgis_app.initQgis()

            self.project = QgsProject.instance()
            logger.info("QGIS initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize QGIS: {e}")
            raise

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "tools/list":
                result = self._handle_list_tools()
            elif method == "tools/call":
                result = self._handle_call_tool(params)
            elif method == "prompts/list":
                result = self._handle_list_prompts()
            elif method == "prompts/get":
                result = self._handle_get_prompt(params)
            else:
                raise ValueError(f"Unknown method: {method}")

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "protocolVersion": "0.1.0",
            "serverInfo": {
                "name": "qgis-mcp-server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {},
                "prompts": {}
            }
        }

    def _handle_list_tools(self) -> Dict[str, Any]:
        """List available tools"""
        return {
            "tools": [
                {
                    "name": "list_layers",
                    "description": "List all layers in the current QGIS project",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "add_vector_layer",
                    "description": "Add a vector layer to QGIS from a file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the vector file (shapefile, GeoJSON, etc.)"
                            },
                            "name": {
                                "type": "string",
                                "description": "Name for the layer in QGIS"
                            }
                        },
                        "required": ["path", "name"]
                    }
                },
                {
                    "name": "get_layer_info",
                    "description": "Get detailed information about a specific layer",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "layer_name": {
                                "type": "string",
                                "description": "Name of the layer"
                            }
                        },
                        "required": ["layer_name"]
                    }
                },
                {
                    "name": "get_features",
                    "description": "Get features from a layer with optional filtering",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "layer_name": {
                                "type": "string",
                                "description": "Name of the layer"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of features to return",
                                "default": 10
                            },
                            "filter": {
                                "type": "string",
                                "description": "Optional filter expression (e.g., 'population > 1000000')"
                            }
                        },
                        "required": ["layer_name"]
                    }
                },
                {
                    "name": "buffer_layer",
                    "description": "Create a buffer around features in a layer",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "layer_name": {
                                "type": "string",
                                "description": "Name of the input layer"
                            },
                            "distance": {
                                "type": "number",
                                "description": "Buffer distance in layer units"
                            },
                            "output_name": {
                                "type": "string",
                                "description": "Name for the output buffer layer"
                            }
                        },
                        "required": ["layer_name", "distance", "output_name"]
                    }
                },
                {
                    "name": "clip_layer",
                    "description": "Clip one layer by another layer's extent",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "input_layer": {
                                "type": "string",
                                "description": "Name of the layer to clip"
                            },
                            "clip_layer": {
                                "type": "string",
                                "description": "Name of the layer to use as clip boundary"
                            },
                            "output_name": {
                                "type": "string",
                                "description": "Name for the clipped output layer"
                            }
                        },
                        "required": ["input_layer", "clip_layer", "output_name"]
                    }
                },
                {
                    "name": "calculate_statistics",
                    "description": "Calculate statistics for a field in a layer",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "layer_name": {
                                "type": "string",
                                "description": "Name of the layer"
                            },
                            "field_name": {
                                "type": "string",
                                "description": "Name of the field to analyze"
                            }
                        },
                        "required": ["layer_name", "field_name"]
                    }
                },
                {
                    "name": "export_map",
                    "description": "Export current map view as an image",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "output_path": {
                                "type": "string",
                                "description": "Path where to save the image"
                            },
                            "width": {
                                "type": "integer",
                                "description": "Image width in pixels",
                                "default": 1920
                            },
                            "height": {
                                "type": "integer",
                                "description": "Image height in pixels",
                                "default": 1080
                            },
                            "format": {
                                "type": "string",
                                "enum": ["PNG", "JPG", "PDF"],
                                "description": "Output format",
                                "default": "PNG"
                            }
                        },
                        "required": ["output_path"]
                    }
                },
                {
                    "name": "load_project",
                    "description": "Load a QGIS project file",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "Path to the .qgs or .qgz project file"
                            }
                        },
                        "required": ["project_path"]
                    }
                },
                {
                    "name": "save_project",
                    "description": "Save current QGIS project",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "Path where to save the project"
                            }
                        },
                        "required": ["project_path"]
                    }
                }
            ]
        }

    def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")

        # Import QGIS modules
        from qgis.core import (
            QgsVectorLayer, QgsProject, QgsFeature,
            QgsProcessingFeedback, QgsProcessing
        )
        import processing

        try:
            if tool_name == "list_layers":
                layers = []
                for layer_id, layer in self.project.mapLayers().items():
                    layers.append({
                        "id": layer_id,
                        "name": layer.name(),
                        "type": layer.type().name if hasattr(layer.type(), 'name') else str(layer.type()),
                        "featureCount": layer.featureCount() if hasattr(layer, 'featureCount') else 0,
                        "crs": layer.crs().authid() if layer.crs() else "Unknown"
                    })

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(layers)} layers:\n" +
                                   "\n".join([f"- {l['name']} ({l['type']}, {l['featureCount']} features)"
                                            for l in layers])
                        }
                    ]
                }

            elif tool_name == "add_vector_layer":
                path = arguments["path"]
                name = arguments["name"]

                layer = QgsVectorLayer(path, name, "ogr")
                if not layer.isValid():
                    raise ValueError(f"Failed to load layer from {path}")

                self.project.addMapLayer(layer)

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Successfully added layer '{name}' with {layer.featureCount()} features"
                        }
                    ]
                }

            elif tool_name == "get_layer_info":
                layer_name = arguments["layer_name"]
                layers = self.project.mapLayersByName(layer_name)

                if not layers:
                    raise ValueError(f"Layer '{layer_name}' not found")

                layer = layers[0]
                fields = [f.name() for f in layer.fields()]
                extent = layer.extent()

                info = {
                    "name": layer.name(),
                    "type": layer.type().name if hasattr(layer.type(), 'name') else str(layer.type()),
                    "featureCount": layer.featureCount() if hasattr(layer, 'featureCount') else 0,
                    "crs": layer.crs().authid(),
                    "extent": {
                        "xMin": extent.xMinimum(),
                        "yMin": extent.yMinimum(),
                        "xMax": extent.xMaximum(),
                        "yMax": extent.yMaximum()
                    },
                    "fields": fields
                }

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(info, indent=2)
                        }
                    ]
                }

            elif tool_name == "get_features":
                layer_name = arguments["layer_name"]
                limit = arguments.get("limit", 10)
                filter_expr = arguments.get("filter")

                layers = self.project.mapLayersByName(layer_name)
                if not layers:
                    raise ValueError(f"Layer '{layer_name}' not found")

                layer = layers[0]

                # Get features
                if filter_expr:
                    layer.setSubsetString(filter_expr)

                features = []
                for i, feature in enumerate(layer.getFeatures()):
                    if i >= limit:
                        break

                    features.append({
                        "id": feature.id(),
                        "attributes": dict(zip(
                            [f.name() for f in layer.fields()],
                            feature.attributes()
                        ))
                    })

                # Clear filter
                if filter_expr:
                    layer.setSubsetString("")

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(features, indent=2, default=str)
                        }
                    ]
                }

            elif tool_name == "buffer_layer":
                layer_name = arguments["layer_name"]
                distance = arguments["distance"]
                output_name = arguments["output_name"]

                layers = self.project.mapLayersByName(layer_name)
                if not layers:
                    raise ValueError(f"Layer '{layer_name}' not found")

                input_layer = layers[0]

                # Run buffer processing
                result = processing.run("native:buffer", {
                    'INPUT': input_layer,
                    'DISTANCE': distance,
                    'SEGMENTS': 10,
                    'END_CAP_STYLE': 0,
                    'JOIN_STYLE': 0,
                    'OUTPUT': 'memory:' + output_name
                })

                output_layer = result['OUTPUT']
                output_layer.setName(output_name)
                self.project.addMapLayer(output_layer)

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Created buffer layer '{output_name}' with {output_layer.featureCount()} features"
                        }
                    ]
                }

            elif tool_name == "clip_layer":
                input_layer_name = arguments["input_layer"]
                clip_layer_name = arguments["clip_layer"]
                output_name = arguments["output_name"]

                input_layers = self.project.mapLayersByName(input_layer_name)
                clip_layers = self.project.mapLayersByName(clip_layer_name)

                if not input_layers:
                    raise ValueError(f"Input layer '{input_layer_name}' not found")
                if not clip_layers:
                    raise ValueError(f"Clip layer '{clip_layer_name}' not found")

                result = processing.run("native:clip", {
                    'INPUT': input_layers[0],
                    'OVERLAY': clip_layers[0],
                    'OUTPUT': 'memory:' + output_name
                })

                output_layer = result['OUTPUT']
                output_layer.setName(output_name)
                self.project.addMapLayer(output_layer)

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Created clipped layer '{output_name}' with {output_layer.featureCount()} features"
                        }
                    ]
                }

            elif tool_name == "calculate_statistics":
                layer_name = arguments["layer_name"]
                field_name = arguments["field_name"]

                layers = self.project.mapLayersByName(layer_name)
                if not layers:
                    raise ValueError(f"Layer '{layer_name}' not found")

                layer = layers[0]

                # Get field index
                field_index = layer.fields().indexOf(field_name)
                if field_index == -1:
                    raise ValueError(f"Field '{field_name}' not found in layer")

                # Calculate statistics
                values = [f.attributes()[field_index] for f in layer.getFeatures()
                         if f.attributes()[field_index] is not None]

                if not values:
                    raise ValueError(f"No valid values found for field '{field_name}'")

                # Try numeric statistics
                try:
                    values = [float(v) for v in values]
                    stats = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "sum": sum(values),
                        "mean": sum(values) / len(values),
                        "field": field_name
                    }
                except (ValueError, TypeError):
                    # Non-numeric field
                    stats = {
                        "count": len(values),
                        "unique_values": len(set(values)),
                        "field": field_name
                    }

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(stats, indent=2)
                        }
                    ]
                }

            elif tool_name == "export_map":
                output_path = arguments["output_path"]
                width = arguments.get("width", 1920)
                height = arguments.get("height", 1080)
                format_type = arguments.get("format", "PNG")

                from qgis.core import QgsMapSettings, QgsMapRendererParallelJob
                from qgis.PyQt.QtCore import QSize

                # Setup map settings
                settings = QgsMapSettings()
                settings.setLayers(self.project.mapLayers().values())
                settings.setOutputSize(QSize(width, height))
                settings.setExtent(self.project.mapLayers().values()[0].extent() if self.project.mapLayers() else None)

                # Render
                render = QgsMapRendererParallelJob(settings)
                render.start()
                render.waitForFinished()

                image = render.renderedImage()
                image.save(output_path, format_type)

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Map exported to {output_path} ({width}x{height}, {format_type})"
                        }
                    ]
                }

            elif tool_name == "load_project":
                project_path = arguments["project_path"]

                if not Path(project_path).exists():
                    raise ValueError(f"Project file not found: {project_path}")

                self.project.read(project_path)
                layers = self.project.mapLayers()

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Loaded project from {project_path} with {len(layers)} layers"
                        }
                    ]
                }

            elif tool_name == "save_project":
                project_path = arguments["project_path"]

                self.project.write(project_path)

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Project saved to {project_path}"
                        }
                    ]
                }

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            }

    def _handle_list_prompts(self) -> Dict[str, Any]:
        """List available prompts"""
        return {
            "prompts": [
                {
                    "name": "analyze_layer",
                    "description": "Analyze a GIS layer and provide insights",
                    "arguments": [
                        {
                            "name": "layer_name",
                            "description": "Name of the layer to analyze",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "create_map",
                    "description": "Guide user through creating a map with specific layers",
                    "arguments": [
                        {
                            "name": "purpose",
                            "description": "Purpose of the map (e.g., 'show population density')",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "spatial_analysis",
                    "description": "Help design a spatial analysis workflow",
                    "arguments": [
                        {
                            "name": "objective",
                            "description": "What you want to analyze",
                            "required": True
                        }
                    ]
                }
            ]
        }

    def _handle_get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific prompt"""
        name = params.get("name")
        arguments = params.get("arguments", {})

        if name == "analyze_layer":
            layer_name = arguments.get("layer_name", "")
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Please analyze the layer '{layer_name}' and provide insights about:\n"
                                   f"- Feature count and distribution\n"
                                   f"- Attribute statistics\n"
                                   f"- Spatial extent and CRS\n"
                                   f"- Data quality observations\n"
                                   f"- Suggested visualizations or analyses"
                        }
                    }
                ]
            }

        elif name == "create_map":
            purpose = arguments.get("purpose", "")
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"I want to create a map to {purpose}. Please:\n"
                                   f"1. List available layers\n"
                                   f"2. Suggest which layers to include\n"
                                   f"3. Recommend styling and symbology\n"
                                   f"4. Guide me through the map creation process"
                        }
                    }
                ]
            }

        elif name == "spatial_analysis":
            objective = arguments.get("objective", "")
            return {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"I want to {objective}. Please:\n"
                                   f"1. Understand available data\n"
                                   f"2. Design an analysis workflow\n"
                                   f"3. Execute the analysis step by step\n"
                                   f"4. Interpret and visualize results"
                        }
                    }
                ]
            }

        raise ValueError(f"Unknown prompt: {name}")

    def run(self):
        """Run the MCP server (stdio transport)"""
        logger.info("Starting QGIS MCP Server...")

        try:
            for line in sys.stdin:
                if not line.strip():
                    continue

                try:
                    request = json.loads(line)
                    response = self.handle_request(request)
                    print(json.dumps(response), flush=True)

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON: {e}")
                    continue

        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
        finally:
            if self.qgis_app:
                self.qgis_app.exitQgis()


def main():
    """Main entry point"""
    server = QGISMCPServer()
    server.run()


if __name__ == "__main__":
    main()
