"""
Optimization module for QGIS MCP
Provides caching, spatial indexing, and efficient data access
"""

import base64
from typing import Dict, Any, Optional, List, Set
from collections import OrderedDict
from qgis.core import (
    QgsProject, QgsMapLayer, QgsFeatureRequest, QgsExpression,
    QgsRectangle, QgsWkbTypes, QgsMessageLog, Qgis
)


class LRUCache:
    """Least Recently Used cache implementation"""

    def __init__(self, max_size: int = 1000):
        self.cache = OrderedDict()
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, moving it to end (most recently used)"""
        if key not in self.cache:
            return None

        # Move to end
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: Any) -> None:
        """Put value in cache, evicting oldest if at capacity"""
        if key in self.cache:
            # Update existing key
            self.cache.move_to_end(key)
        else:
            # Add new key, evict oldest if needed
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

        self.cache[key] = value

    def clear(self) -> None:
        """Clear the cache"""
        self.cache.clear()

    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)


class GeometryCache:
    """Cache for simplified geometries"""

    def __init__(self, max_size: int = 1000):
        self.cache = LRUCache(max_size)
        self.hits = 0
        self.misses = 0

    def get_geometry(self, layer_id: str, feature_id: int) -> Optional[Dict[str, Any]]:
        """Get cached geometry data"""
        key = f"{layer_id}_{feature_id}"
        geom_data = self.cache.get(key)

        if geom_data:
            self.hits += 1
        else:
            self.misses += 1

        return geom_data

    def put_geometry(self, layer_id: str, feature_id: int, geom_data: Dict[str, Any]):
        """Cache geometry data"""
        key = f"{layer_id}_{feature_id}"
        self.cache.put(key, geom_data)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "size": self.cache.size(),
            "max_size": self.cache.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2)
        }

    def clear(self):
        """Clear cache and statistics"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0


class OptimizedFeatureAccess:
    """Optimized feature access with spatial indexing and caching"""

    def __init__(self):
        self.geometry_cache = GeometryCache(max_size=1000)

    def get_features_optimized(
        self,
        layer_id: str,
        limit: int = 100,
        bbox: Optional[Dict[str, float]] = None,
        filter_expression: Optional[str] = None,
        attributes_only: bool = False,
        simplify_tolerance: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get features with optimizations

        Args:
            layer_id: Layer ID
            limit: Maximum number of features
            bbox: Bounding box for spatial filter
            filter_expression: Attribute filter expression
            attributes_only: Skip geometry if True
            simplify_tolerance: Simplify geometries if > 0

        Returns:
            Dictionary with features and metadata
        """
        project = QgsProject.instance()

        if layer_id not in project.mapLayers():
            raise ValueError(f"Layer not found: {layer_id}")

        layer = project.mapLayer(layer_id)

        if layer.type() != QgsMapLayer.VectorLayer:
            raise ValueError(f"Layer is not a vector layer: {layer_id}")

        # Build optimized feature request
        request = QgsFeatureRequest()

        # Spatial filter (uses spatial index!)
        if bbox:
            rect = QgsRectangle(
                bbox['xmin'], bbox['ymin'],
                bbox['xmax'], bbox['ymax']
            )
            request.setFilterRect(rect)

        # Attribute filter (pushed to provider level)
        if filter_expression:
            expr = QgsExpression(filter_expression)
            if not expr.isValid():
                raise ValueError(f"Invalid expression: {expr.parserErrorString()}")
            request.setFilterExpression(expr)

        # Limit at request level
        request.setLimit(limit)

        # Only fetch needed attributes
        if attributes_only:
            request.setFlags(QgsFeatureRequest.NoGeometry)

        # Use spatial index if available
        if layer.hasSpatialIndex():
            request.setFlags(request.flags() | QgsFeatureRequest.UseSpatialIndex)

        # Get field names once
        field_names = [field.name() for field in layer.fields()]
        field_types = [field.typeName() for field in layer.fields()]

        # Fetch features
        features_data = []

        for feature in layer.getFeatures(request):
            # Efficient attribute extraction by index
            attrs = {}
            for idx, field_name in enumerate(field_names):
                value = feature.attribute(idx)

                # Handle special types
                if value is None:
                    attrs[field_name] = None
                elif field_types[idx] in ('QDate', 'QDateTime', 'QTime'):
                    attrs[field_name] = str(value)
                else:
                    attrs[field_name] = value

            # Optimized geometry handling
            geom_data = None
            if not attributes_only and feature.hasGeometry():
                geom_data = self._get_geometry_data(
                    layer_id,
                    feature,
                    simplify_tolerance
                )

            features_data.append({
                "id": feature.id(),
                "attributes": attrs,
                "geometry": geom_data
            })

        return {
            "layer_id": layer_id,
            "total_features": layer.featureCount(),
            "returned_features": len(features_data),
            "features": features_data,
            "fields": list(zip(field_names, field_types)),
            "has_spatial_index": layer.hasSpatialIndex(),
            "cache_stats": self.geometry_cache.get_stats()
        }

    def _get_geometry_data(
        self,
        layer_id: str,
        feature,
        simplify_tolerance: Optional[float] = None
    ) -> Dict[str, Any]:
        """Get geometry data with caching"""
        # Check cache first
        cached_geom = self.geometry_cache.get_geometry(layer_id, feature.id())
        if cached_geom:
            return cached_geom

        geometry = feature.geometry()

        # Simplify if requested
        if simplify_tolerance and simplify_tolerance > 0:
            geometry = geometry.simplify(simplify_tolerance)

        # Use efficient WKB format instead of WKT
        wkb_bytes = geometry.asWkb()

        geom_data = {
            "type": QgsWkbTypes.displayString(geometry.wkbType()),
            "format": "wkb_base64",
            "data": base64.b64encode(wkb_bytes).decode('ascii'),
            "bbox": geometry.boundingBox().asWktCoordinates()
        }

        # Cache the result
        self.geometry_cache.put_geometry(layer_id, feature.id(), geom_data)

        return geom_data

    def clear_cache(self):
        """Clear geometry cache"""
        self.geometry_cache.clear()
        QgsMessageLog.logMessage(
            "Geometry cache cleared",
            "QGIS MCP Performance",
            Qgis.Info
        )


class PaginatedLayerAccess:
    """Paginated access to layer lists"""

    MAX_LAYERS_PER_PAGE = 100

    @staticmethod
    def get_layers_paginated(
        offset: int = 0,
        limit: int = 50,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get layers with pagination

        Args:
            offset: Starting index
            limit: Maximum layers to return

        Returns:
            Paginated layer list with metadata
        """
        project = QgsProject.instance()
        all_layers = list(project.mapLayers().items())

        # Apply pagination
        total_count = len(all_layers)
        end = min(offset + limit, total_count, PaginatedLayerAccess.MAX_LAYERS_PER_PAGE)
        layers_subset = all_layers[offset:end]

        layers = []
        layer_tree_root = project.layerTreeRoot()

        for layer_id, layer in layers_subset:
            layer_node = layer_tree_root.findLayer(layer_id)

            layer_info = {
                "id": layer_id,
                "name": layer.name(),
                "type": PaginatedLayerAccess._get_layer_type(layer),
                "visible": layer_node.isVisible() if layer_node else False
            }

            # Add type-specific info
            if layer.type() == QgsMapLayer.VectorLayer:
                layer_info.update({
                    "feature_count": layer.featureCount(),
                    "geometry_type": QgsWkbTypes.displayString(layer.wkbType()),
                    "has_spatial_index": layer.hasSpatialIndex()
                })
            elif layer.type() == QgsMapLayer.RasterLayer:
                layer_info.update({
                    "width": layer.width(),
                    "height": layer.height(),
                    "band_count": layer.bandCount()
                })

            layers.append(layer_info)

        return {
            "layers": layers,
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            "returned": len(layers),
            "has_more": end < total_count
        }

    @staticmethod
    def _get_layer_type(layer) -> str:
        """Helper to get layer type as string"""
        if layer.type() == QgsMapLayer.VectorLayer:
            geom_type = layer.geometryType()
            return f"vector_{QgsWkbTypes.geometryDisplayString(geom_type)}"
        elif layer.type() == QgsMapLayer.RasterLayer:
            return "raster"
        else:
            return str(layer.type())


class PerformanceMonitor:
    """Monitor and log performance metrics"""

    def __init__(self):
        self.command_stats = {}

    def record_command(self, command_type: str, elapsed_time: float):
        """Record command execution time"""
        if command_type not in self.command_stats:
            self.command_stats[command_type] = {
                "count": 0,
                "total_time": 0,
                "min_time": float('inf'),
                "max_time": 0
            }

        stats = self.command_stats[command_type]
        stats["count"] += 1
        stats["total_time"] += elapsed_time
        stats["min_time"] = min(stats["min_time"], elapsed_time)
        stats["max_time"] = max(stats["max_time"], elapsed_time)

        # Log slow commands
        if elapsed_time > 1.0:
            QgsMessageLog.logMessage(
                f"SLOW COMMAND: {command_type} took {elapsed_time:.2f}s",
                "QGIS MCP Performance",
                Qgis.Warning
            )

    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance statistics"""
        commands = []

        for cmd_type, stats in self.command_stats.items():
            avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0

            commands.append({
                "command": cmd_type,
                "calls": stats["count"],
                "total_time": round(stats["total_time"], 3),
                "avg_time": round(avg_time, 3),
                "min_time": round(stats["min_time"], 3),
                "max_time": round(stats["max_time"], 3)
            })

        # Sort by total time
        commands.sort(key=lambda x: x["total_time"], reverse=True)

        return {
            "commands": commands,
            "total_commands": sum(c["calls"] for c in commands)
        }

    def reset(self):
        """Reset all statistics"""
        self.command_stats.clear()
