"""
Async Command Executor for QGIS MCP Server
Provides non-blocking execution of long-running operations with progress reporting
"""

import time
import threading
import traceback
from typing import Dict, Any, Optional, Callable
from enum import Enum
from datetime import datetime

try:
    from PyQt5.QtCore import QThread, pyqtSignal, QObject
    HAS_QT = True
except ImportError:
    HAS_QT = False
    print("Warning: PyQt5 not available, async operations will use threading.Thread")

try:
    from qgis.core import QgsMessageLog, Qgis
    HAS_QGIS = True
except ImportError:
    HAS_QGIS = False


class OperationStatus(Enum):
    """Status of async operation"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AsyncOperationResult:
    """Result container for async operations"""

    def __init__(self, request_id: str):
        self.request_id = request_id
        self.status = OperationStatus.PENDING
        self.progress = 0
        self.progress_message = ""
        self.result = None
        self.error = None
        self.start_time = time.time()
        self.end_time = None
        self.cancelled = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        elapsed = (self.end_time or time.time()) - self.start_time

        return {
            "request_id": self.request_id,
            "status": self.status.value,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "result": self.result,
            "error": self.error,
            "elapsed_seconds": round(elapsed, 2),
            "completed": self.status in (OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.CANCELLED, OperationStatus.TIMEOUT)
        }


if HAS_QT:
    class AsyncCommandExecutor(QThread):
        """
        Qt-based async command executor
        Runs commands in separate thread with progress reporting
        """

        # Signals for communication
        finished = pyqtSignal(str, object)  # request_id, result
        progress = pyqtSignal(str, int, str)  # request_id, percentage, message
        error = pyqtSignal(str, str)  # request_id, error_message

        def __init__(
            self,
            request_id: str,
            command_type: str,
            handler: Callable,
            params: Dict[str, Any],
            timeout: Optional[float] = None
        ):
            """
            Initialize async executor

            Args:
                request_id: Unique request identifier
                command_type: Type of command to execute
                handler: Function to execute
                params: Parameters for handler
                timeout: Timeout in seconds (None for no timeout)
            """
            super().__init__()
            self.request_id = request_id
            self.command_type = command_type
            self.handler = handler
            self.params = params
            self.timeout = timeout or 300.0  # 5 minutes default
            self.cancelled = False
            self.result_obj = AsyncOperationResult(request_id)

        def run(self):
            """Execute command in thread"""
            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Starting async operation: {self.request_id} ({self.command_type})",
                    "QGIS MCP Async",
                    Qgis.Info
                )

            self.result_obj.status = OperationStatus.RUNNING
            self.progress.emit(self.request_id, 0, "Starting...")

            try:
                # Execute with timeout monitoring
                result = self._execute_with_timeout()

                if not self.cancelled:
                    self.result_obj.status = OperationStatus.COMPLETED
                    self.result_obj.result = result
                    self.result_obj.progress = 100
                    self.result_obj.end_time = time.time()

                    self.progress.emit(self.request_id, 100, "Completed")
                    self.finished.emit(self.request_id, result)

                    if HAS_QGIS:
                        QgsMessageLog.logMessage(
                            f"Async operation completed: {self.request_id}",
                            "QGIS MCP Async",
                            Qgis.Success
                        )

            except TimeoutError:
                self.result_obj.status = OperationStatus.TIMEOUT
                self.result_obj.error = f"Operation timed out after {self.timeout}s"
                self.result_obj.end_time = time.time()

                error_msg = f"Timeout after {self.timeout}s"
                self.error.emit(self.request_id, error_msg)

                if HAS_QGIS:
                    QgsMessageLog.logMessage(
                        f"Async operation timeout: {self.request_id}",
                        "QGIS MCP Async",
                        Qgis.Warning
                    )

            except Exception as e:
                self.result_obj.status = OperationStatus.FAILED
                self.result_obj.error = str(e)
                self.result_obj.end_time = time.time()

                error_msg = f"{type(e).__name__}: {str(e)}"
                self.error.emit(self.request_id, error_msg)

                if HAS_QGIS:
                    QgsMessageLog.logMessage(
                        f"Async operation failed: {self.request_id}\n{traceback.format_exc()}",
                        "QGIS MCP Async",
                        Qgis.Critical
                    )

        def _execute_with_timeout(self) -> Any:
            """Execute handler with timeout monitoring"""
            start_time = time.time()

            # Create progress callback
            def report_progress(percent: int, message: str = ""):
                if self.cancelled:
                    raise InterruptedError("Operation cancelled")

                self.result_obj.progress = percent
                self.result_obj.progress_message = message
                self.progress.emit(self.request_id, percent, message)

                # Check timeout
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Operation exceeded {self.timeout}s timeout")

            # Add progress callback to params
            params_with_progress = self.params.copy()
            params_with_progress['_progress_callback'] = report_progress

            # Execute handler
            result = self.handler(**params_with_progress)

            return result

        def cancel(self):
            """Cancel the operation"""
            self.cancelled = True
            self.result_obj.status = OperationStatus.CANCELLED
            self.result_obj.cancelled = True
            self.result_obj.end_time = time.time()

            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Async operation cancelled: {self.request_id}",
                    "QGIS MCP Async",
                    Qgis.Info
                )

else:
    # Fallback to threading.Thread if Qt not available
    class AsyncCommandExecutor(threading.Thread):
        """Fallback async executor using threading.Thread"""

        def __init__(
            self,
            request_id: str,
            command_type: str,
            handler: Callable,
            params: Dict[str, Any],
            timeout: Optional[float] = None
        ):
            super().__init__(daemon=True)
            self.request_id = request_id
            self.command_type = command_type
            self.handler = handler
            self.params = params
            self.timeout = timeout or 300.0
            self.cancelled = False
            self.result_obj = AsyncOperationResult(request_id)
            self._callbacks = {'finished': [], 'progress': [], 'error': []}

        def run(self):
            """Execute command in thread"""
            self.result_obj.status = OperationStatus.RUNNING
            self._emit('progress', self.request_id, 0, "Starting...")

            try:
                result = self._execute_with_timeout()

                if not self.cancelled:
                    self.result_obj.status = OperationStatus.COMPLETED
                    self.result_obj.result = result
                    self.result_obj.progress = 100
                    self.result_obj.end_time = time.time()

                    self._emit('progress', self.request_id, 100, "Completed")
                    self._emit('finished', self.request_id, result)

            except TimeoutError:
                self.result_obj.status = OperationStatus.TIMEOUT
                self.result_obj.error = f"Operation timed out after {self.timeout}s"
                self.result_obj.end_time = time.time()
                self._emit('error', self.request_id, f"Timeout after {self.timeout}s")

            except Exception as e:
                self.result_obj.status = OperationStatus.FAILED
                self.result_obj.error = str(e)
                self.result_obj.end_time = time.time()
                self._emit('error', self.request_id, f"{type(e).__name__}: {str(e)}")

        def _execute_with_timeout(self) -> Any:
            """Execute handler with timeout monitoring"""
            start_time = time.time()

            def report_progress(percent: int, message: str = ""):
                if self.cancelled:
                    raise InterruptedError("Operation cancelled")

                self.result_obj.progress = percent
                self.result_obj.progress_message = message
                self._emit('progress', self.request_id, percent, message)

                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Operation exceeded {self.timeout}s timeout")

            params_with_progress = self.params.copy()
            params_with_progress['_progress_callback'] = report_progress

            return self.handler(**params_with_progress)

        def cancel(self):
            """Cancel the operation"""
            self.cancelled = True
            self.result_obj.status = OperationStatus.CANCELLED
            self.result_obj.cancelled = True
            self.result_obj.end_time = time.time()

        def connect_signal(self, signal_name: str, callback: Callable):
            """Connect callback to signal"""
            if signal_name in self._callbacks:
                self._callbacks[signal_name].append(callback)

        def _emit(self, signal_name: str, *args):
            """Emit signal to connected callbacks"""
            for callback in self._callbacks.get(signal_name, []):
                try:
                    callback(*args)
                except Exception as e:
                    print(f"Error in callback: {e}")


class AsyncOperationManager:
    """
    Manages async operations lifecycle
    Tracks running operations, provides status queries, and cleanup
    """

    def __init__(self, max_concurrent: int = 10, cleanup_after: int = 3600):
        """
        Initialize operation manager

        Args:
            max_concurrent: Maximum concurrent operations
            cleanup_after: Seconds after which to cleanup completed operations
        """
        self.max_concurrent = max_concurrent
        self.cleanup_after = cleanup_after
        self.operations: Dict[str, AsyncCommandExecutor] = {}
        self._lock = threading.Lock()

    def start_operation(
        self,
        request_id: str,
        command_type: str,
        handler: Callable,
        params: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> AsyncOperationResult:
        """
        Start async operation

        Args:
            request_id: Unique request identifier
            command_type: Type of command
            handler: Function to execute
            params: Parameters for handler
            timeout: Timeout in seconds

        Returns:
            AsyncOperationResult with initial status

        Raises:
            RuntimeError: If too many concurrent operations
        """
        with self._lock:
            # Check if operation already exists
            if request_id in self.operations:
                raise ValueError(f"Operation {request_id} already exists")

            # Check concurrent limit
            active_count = sum(
                1 for op in self.operations.values()
                if op.result_obj.status == OperationStatus.RUNNING
            )

            if active_count >= self.max_concurrent:
                raise RuntimeError(
                    f"Too many concurrent operations ({active_count}/{self.max_concurrent}). "
                    "Please wait for some to complete."
                )

            # Create and start executor
            executor = AsyncCommandExecutor(
                request_id=request_id,
                command_type=command_type,
                handler=handler,
                params=params,
                timeout=timeout
            )

            # Store executor
            self.operations[request_id] = executor

            # Start execution
            executor.start()

            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Started async operation: {request_id} ({command_type})",
                    "QGIS MCP Async",
                    Qgis.Info
                )

            return executor.result_obj

    def get_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get operation status

        Args:
            request_id: Request identifier

        Returns:
            Status dictionary or None if not found
        """
        with self._lock:
            executor = self.operations.get(request_id)
            if not executor:
                return None

            return executor.result_obj.to_dict()

    def cancel_operation(self, request_id: str) -> bool:
        """
        Cancel running operation

        Args:
            request_id: Request identifier

        Returns:
            True if cancelled, False if not found or already completed
        """
        with self._lock:
            executor = self.operations.get(request_id)
            if not executor:
                return False

            if executor.result_obj.status not in (OperationStatus.PENDING, OperationStatus.RUNNING):
                return False

            executor.cancel()

            if HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Cancelled async operation: {request_id}",
                    "QGIS MCP Async",
                    Qgis.Info
                )

            return True

    def cleanup_completed(self) -> int:
        """
        Remove completed operations older than cleanup_after seconds

        Returns:
            Number of operations cleaned up
        """
        with self._lock:
            now = time.time()
            to_remove = []

            for request_id, executor in self.operations.items():
                result = executor.result_obj

                # Check if completed and old enough
                if result.end_time and (now - result.end_time > self.cleanup_after):
                    to_remove.append(request_id)

            # Remove old operations
            for request_id in to_remove:
                del self.operations[request_id]

            if to_remove and HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Cleaned up {len(to_remove)} completed async operations",
                    "QGIS MCP Async",
                    Qgis.Info
                )

            return len(to_remove)

    def list_operations(self) -> List[Dict[str, Any]]:
        """
        List all tracked operations

        Returns:
            List of operation status dictionaries
        """
        with self._lock:
            return [
                executor.result_obj.to_dict()
                for executor in self.operations.values()
            ]

    def cancel_all(self) -> int:
        """
        Cancel all running operations

        Returns:
            Number of operations cancelled
        """
        with self._lock:
            cancelled = 0
            for executor in self.operations.values():
                if executor.result_obj.status in (OperationStatus.PENDING, OperationStatus.RUNNING):
                    executor.cancel()
                    cancelled += 1

            if cancelled and HAS_QGIS:
                QgsMessageLog.logMessage(
                    f"Cancelled {cancelled} async operations",
                    "QGIS MCP Async",
                    Qgis.Warning
                )

            return cancelled

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about async operations

        Returns:
            Dictionary with operation statistics
        """
        with self._lock:
            stats = {
                "total_operations": len(self.operations),
                "by_status": {},
                "max_concurrent": self.max_concurrent
            }

            for executor in self.operations.values():
                status = executor.result_obj.status.value
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            return stats


# Global async operation manager instance
_global_async_manager: Optional[AsyncOperationManager] = None


def get_async_manager() -> AsyncOperationManager:
    """Get or create global async operation manager"""
    global _global_async_manager

    if _global_async_manager is None:
        _global_async_manager = AsyncOperationManager(
            max_concurrent=10,
            cleanup_after=3600  # 1 hour
        )

    return _global_async_manager
