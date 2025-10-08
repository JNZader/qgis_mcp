"""
QGIS MCP Optimized Server - Performance-enhanced version
Extends SecureQGISMCPServer with async operations, caching, and optimizations

Features:
- Async command execution for long operations
- Enhanced geometry caching with invalidation
- Connection pooling with worker threads
- Batch processing support
- Progress reporting
- Performance monitoring and metrics
"""

import uuid
import time
from typing import Dict, Any, Optional, Callable
from pathlib import Path

try:
    from qgis.core import QgsMessageLog, Qgis, QgsProject, QgsVectorLayer, QgsRasterLayer
    from qgis.utils import iface
    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False

from .qgis_mcp_server_secure import SecureQGISMCPServer
from .async_executor import get_async_manager, OperationStatus
from .optimization import (
    GeometryCache,
    OptimizedFeatureAccess,
    PaginatedLayerAccess,
    PerformanceMonitor
)
from .security_improved import SecurityException


class OptimizedQGISMCPServer(SecureQGISMCPServer):
    """
    Optimized QGIS MCP Server with performance enhancements

    Enhancements:
    - Async execution for long operations
    - Enhanced caching with invalidation
    - Batch processing
    - Progress reporting
    - Better resource management
    """

    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 9876,
        use_tls: bool = False,
        require_auth: bool = True,
        allowed_directories: Optional[list] = None,
        enable_async: bool = True,
        cache_size: int = 1000,
        max_async_operations: int = 10
    ):
        """
        Initialize optimized QGIS MCP server

        Args:
            host: Host to bind to (forced to 127.0.0.1)
            port: Port number
            use_tls: Enable TLS/SSL
            require_auth: Require authentication
            allowed_directories: Allowed directories for file operations
            enable_async: Enable async command execution
            cache_size: Geometry cache size
            max_async_operations: Maximum concurrent async operations
        """
        # Initialize parent
        super().__init__(
            host=host,
            port=port,
            use_tls=use_tls,
            require_auth=require_auth,
            allowed_directories=allowed_directories
        )

        # Async support
        self.enable_async = enable_async
        if self.enable_async:
            self.async_manager = get_async_manager()
            self.async_manager.max_concurrent = max_async_operations

        # Enhanced caching
        self.geometry_cache = GeometryCache(max_size=cache_size)
        self.feature_access = OptimizedFeatureAccess()
        self.feature_access.geometry_cache = self.geometry_cache

        # Register async command handlers
        self.command_handlers.update({
            'execute_code_async': self._handle_execute_code_async,
            'render_map_async': self._handle_render_map_async,
            'execute_processing_async': self._handle_execute_processing_async,
            'get_features_async': self._handle_get_features_async,
            'check_async_status': self._handle_check_async_status,
            'cancel_async_operation': self._handle_cancel_async_operation,
            'list_async_operations': self._handle_list_async_operations,
            'clear_cache': self._handle_clear_cache,
            'invalidate_layer_cache': self._handle_invalidate_layer_cache,
        })

        if HAS_QGIS:
            QgsMessageLog.logMessage(
                f"Optimized QGIS MCP Server initialized (cache_size={cache_size}, "
                f"async_enabled={enable_async})",
                "QGIS MCP Optimized",
                Qgis.Info
            )

    # ==================== Enhanced Command Handlers ====================

    def _handle_get_features(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Enhanced get_features with caching and optimization"""
        if not HAS_QGIS:
            raise RuntimeError("QGIS not available")

        data = message.get('data', {})

        # Use optimized feature access
        result = self.feature_access.get_features_optimized(**data)

        return result

    def _handle_list_layers(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Enhanced list_layers with pagination"""
        if not HAS_QGIS:
            raise RuntimeError("QGIS not available")

        data = message.get('data', {})
        offset = data.get('offset', 0)
        limit = data.get('limit', 50)

        return PaginatedLayerAccess.get_layers_paginated(offset=offset, limit=limit)

    def _handle_get_stats(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Enhanced statistics with cache and async metrics"""
        base_stats = super()._handle_get_stats(message, client_id)

        # Add async stats if enabled
        if self.enable_async:
            base_stats['async_operations'] = self.async_manager.get_stats()

        # Enhanced cache stats
        base_stats['cache'] = self.geometry_cache.get_stats()

        return base_stats

    # ==================== Async Command Handlers ====================

    def _handle_execute_code_async(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Execute Python code asynchronously"""
        if not self.enable_async:
            raise RuntimeError("Async operations not enabled")

        if not HAS_QGIS:
            raise RuntimeError("QGIS not available")

        data = message.get('data', {})
        code = data.get('code', '')
        timeout = data.get('timeout', 300)

        # Generate request ID
        request_id = data.get('request_id', str(uuid.uuid4()))

        # Validate code with sandbox
        self.sandbox.validate_code(code)

        # Create async handler
        def async_handler(_progress_callback=None, **kwargs):
            if _progress_callback:
                _progress_callback(10, "Validating code...")

            result = self.sandbox.execute_with_timeout(code)

            if _progress_callback:
                _progress_callback(100, "Code executed")

            return {
                'executed': True,
                'result': str(result) if result is not None else None
            }

        # Start async operation
        result = self.async_manager.start_operation(
            request_id=request_id,
            command_type='execute_code',
            handler=async_handler,
            params={},
            timeout=timeout
        )

        return {
            'request_id': request_id,
            'status': result.status.value,
            'message': 'Code execution started asynchronously'
        }

    def _handle_render_map_async(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Render map asynchronously"""
        if not self.enable_async:
            raise RuntimeError("Async operations not enabled")

        if not HAS_QGIS:
            raise RuntimeError("QGIS not available")

        data = message.get('data', {})
        request_id = data.get('request_id', str(uuid.uuid4()))
        timeout = data.get('timeout', 300)

        # Create async handler
        def async_handler(_progress_callback=None, **render_params):
            if _progress_callback:
                _progress_callback(10, "Preparing map canvas...")

            # Import here to avoid circular imports
            from qgis.core import QgsMapSettings, QgsMapRendererCustomPainterJob
            from PyQt5.QtGui import QImage, QPainter
            from PyQt5.QtCore import QSize
            import base64
            from io import BytesIO

            if _progress_callback:
                _progress_callback(30, "Setting up renderer...")

            # Get parameters
            width = render_params.get('width', 800)
            height = render_params.get('height', 600)
            extent = render_params.get('extent')
            layer_ids = render_params.get('layer_ids', [])

            # Setup map settings
            settings = QgsMapSettings()
            settings.setOutputSize(QSize(width, height))

            if extent:
                from qgis.core import QgsRectangle
                rect = QgsRectangle(
                    extent['xmin'], extent['ymin'],
                    extent['xmax'], extent['ymax']
                )
                settings.setExtent(rect)
            elif iface:
                settings.setExtent(iface.mapCanvas().extent())

            # Set layers
            if layer_ids:
                layers = [QgsProject.instance().mapLayer(lid) for lid in layer_ids]
                layers = [l for l in layers if l is not None]
                settings.setLayers(layers)
            elif iface:
                settings.setLayers(iface.mapCanvas().layers())

            if _progress_callback:
                _progress_callback(50, "Rendering map...")

            # Create image
            image = QImage(QSize(width, height), QImage.Format_ARGB32)
            image.fill(0)  # Transparent background

            # Render
            painter = QPainter(image)
            job = QgsMapRendererCustomPainterJob(settings, painter)
            job.renderSynchronously()
            painter.end()

            if _progress_callback:
                _progress_callback(90, "Encoding image...")

            # Convert to base64 PNG
            buffer = BytesIO()
            image.save(buffer, "PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode('ascii')

            if _progress_callback:
                _progress_callback(100, "Render complete")

            return {
                'image_base64': img_base64,
                'format': 'png',
                'width': width,
                'height': height
            }

        # Start async operation
        result = self.async_manager.start_operation(
            request_id=request_id,
            command_type='render_map',
            handler=async_handler,
            params=data,
            timeout=timeout
        )

        return {
            'request_id': request_id,
            'status': result.status.value,
            'message': 'Map rendering started asynchronously'
        }

    def _handle_execute_processing_async(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Execute QGIS processing algorithm asynchronously"""
        if not self.enable_async:
            raise RuntimeError("Async operations not enabled")

        if not HAS_QGIS:
            raise RuntimeError("QGIS not available")

        data = message.get('data', {})
        request_id = data.get('request_id', str(uuid.uuid4()))
        algorithm_id = data.get('algorithm_id')
        parameters = data.get('parameters', {})
        timeout = data.get('timeout', 600)  # 10 minutes for processing

        if not algorithm_id:
            raise ValueError("algorithm_id is required")

        # Create async handler
        def async_handler(_progress_callback=None, **kwargs):
            import processing
            from processing.core.Processing import Processing

            if _progress_callback:
                _progress_callback(10, f"Loading algorithm: {algorithm_id}")

            # Initialize processing
            Processing.initialize()

            # Get algorithm
            alg = processing.algorithmById(algorithm_id)
            if not alg:
                raise ValueError(f"Algorithm not found: {algorithm_id}")

            if _progress_callback:
                _progress_callback(20, "Preparing parameters...")

            # Run algorithm
            if _progress_callback:
                _progress_callback(30, "Running algorithm...")

            result = processing.run(algorithm_id, parameters)

            if _progress_callback:
                _progress_callback(100, "Algorithm complete")

            # Convert result to serializable format
            serializable_result = {}
            for key, value in result.items():
                if isinstance(value, (str, int, float, bool, type(None))):
                    serializable_result[key] = value
                else:
                    serializable_result[key] = str(value)

            return {
                'algorithm_id': algorithm_id,
                'result': serializable_result
            }

        # Start async operation
        result = self.async_manager.start_operation(
            request_id=request_id,
            command_type='execute_processing',
            handler=async_handler,
            params={'algorithm_id': algorithm_id, 'parameters': parameters},
            timeout=timeout
        )

        return {
            'request_id': request_id,
            'status': result.status.value,
            'message': f'Processing algorithm {algorithm_id} started asynchronously'
        }

    def _handle_get_features_async(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Get features asynchronously for large queries"""
        if not self.enable_async:
            raise RuntimeError("Async operations not enabled")

        if not HAS_QGIS:
            raise RuntimeError("QGIS not available")

        data = message.get('data', {})
        request_id = data.get('request_id', str(uuid.uuid4()))
        timeout = data.get('timeout', 300)

        # Create async handler
        def async_handler(_progress_callback=None, **query_params):
            if _progress_callback:
                _progress_callback(10, "Starting feature query...")

            result = self.feature_access.get_features_optimized(**query_params)

            if _progress_callback:
                _progress_callback(100, f"Retrieved {result['returned_features']} features")

            return result

        # Start async operation
        result = self.async_manager.start_operation(
            request_id=request_id,
            command_type='get_features',
            handler=async_handler,
            params=data,
            timeout=timeout
        )

        return {
            'request_id': request_id,
            'status': result.status.value,
            'message': 'Feature query started asynchronously'
        }

    def _handle_check_async_status(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Check status of async operation"""
        if not self.enable_async:
            raise RuntimeError("Async operations not enabled")

        data = message.get('data', {})
        request_id = data.get('request_id')

        if not request_id:
            raise ValueError("request_id is required")

        status = self.async_manager.get_status(request_id)

        if not status:
            raise ValueError(f"Operation not found: {request_id}")

        return status

    def _handle_cancel_async_operation(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Cancel async operation"""
        if not self.enable_async:
            raise RuntimeError("Async operations not enabled")

        data = message.get('data', {})
        request_id = data.get('request_id')

        if not request_id:
            raise ValueError("request_id is required")

        cancelled = self.async_manager.cancel_operation(request_id)

        return {
            'request_id': request_id,
            'cancelled': cancelled,
            'message': 'Operation cancelled' if cancelled else 'Operation not found or already completed'
        }

    def _handle_list_async_operations(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """List all async operations"""
        if not self.enable_async:
            raise RuntimeError("Async operations not enabled")

        operations = self.async_manager.list_operations()

        return {
            'operations': operations,
            'total': len(operations)
        }

    # ==================== Cache Management ====================

    def _handle_clear_cache(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Clear all caches"""
        stats_before = self.geometry_cache.get_stats()

        self.geometry_cache.clear()
        self.feature_access.clear_cache()

        if HAS_QGIS:
            QgsMessageLog.logMessage(
                "All caches cleared",
                "QGIS MCP Optimized",
                Qgis.Info
            )

        return {
            'cleared': True,
            'stats_before': stats_before,
            'stats_after': self.geometry_cache.get_stats()
        }

    def _handle_invalidate_layer_cache(self, message: Dict[str, Any], client_id: str) -> Dict[str, Any]:
        """Invalidate cache for specific layer"""
        data = message.get('data', {})
        layer_id = data.get('layer_id')

        if not layer_id:
            raise ValueError("layer_id is required")

        # Clear all cache entries for this layer
        # This is a simple implementation - could be optimized with layer-based indexing
        cleared = 0
        for key in list(self.geometry_cache.cache.cache.keys()):
            if key.startswith(f"{layer_id}_"):
                del self.geometry_cache.cache.cache[key]
                cleared += 1

        if HAS_QGIS:
            QgsMessageLog.logMessage(
                f"Invalidated {cleared} cache entries for layer {layer_id}",
                "QGIS MCP Optimized",
                Qgis.Info
            )

        return {
            'layer_id': layer_id,
            'cleared_entries': cleared
        }

    # ==================== Cleanup ====================

    def stop(self) -> None:
        """Stop server and cleanup resources"""
        # Cancel all async operations
        if self.enable_async:
            cancelled = self.async_manager.cancel_all()
            if HAS_QGIS and cancelled > 0:
                QgsMessageLog.logMessage(
                    f"Cancelled {cancelled} async operations on shutdown",
                    "QGIS MCP Optimized",
                    Qgis.Warning
                )

        # Call parent stop
        super().stop()


def start_optimized_server(
    port: int = 9876,
    use_tls: bool = False,
    require_auth: bool = True,
    enable_async: bool = True,
    cache_size: int = 1000
) -> OptimizedQGISMCPServer:
    """
    Start optimized QGIS MCP server

    Args:
        port: Port number
        use_tls: Enable TLS/SSL
        require_auth: Require authentication
        enable_async: Enable async operations
        cache_size: Geometry cache size

    Returns:
        Running optimized server instance
    """
    import threading

    server = OptimizedQGISMCPServer(
        host='127.0.0.1',
        port=port,
        use_tls=use_tls,
        require_auth=require_auth,
        enable_async=enable_async,
        cache_size=cache_size
    )

    # Start in background thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    return server
