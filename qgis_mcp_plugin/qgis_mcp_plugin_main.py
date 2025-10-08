"""
QGIS MCP Plugin Main - QGIS Plugin Integration

This module provides the QGIS plugin interface for the secure MCP server.
"""

from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsMessageLog, Qgis

from .qgis_mcp_server_secure import SecureQGISMCPServer


class QGISMCPPlugin:
    """QGIS MCP Plugin - Secure server integration"""

    def __init__(self, iface):
        """
        Initialize plugin

        Args:
            iface: QGIS interface instance
        """
        self.iface = iface
        self.server: SecureQGISMCPServer = None
        self.actions = []

    def initGui(self):
        """Initialize plugin GUI"""
        # Create action for starting server
        icon = QIcon()
        self.start_action = QAction(
            icon,
            "Start Secure MCP Server",
            self.iface.mainWindow()
        )
        self.start_action.triggered.connect(self.start_server)
        self.start_action.setEnabled(True)
        self.start_action.setCheckable(False)

        # Create action for stopping server
        self.stop_action = QAction(
            icon,
            "Stop MCP Server",
            self.iface.mainWindow()
        )
        self.stop_action.triggered.connect(self.stop_server)
        self.stop_action.setEnabled(False)
        self.stop_action.setCheckable(False)

        # Add toolbar button and menu item
        self.iface.addPluginToMenu("&QGIS MCP Secure", self.start_action)
        self.iface.addPluginToMenu("&QGIS MCP Secure", self.stop_action)

        self.actions.append(self.start_action)
        self.actions.append(self.stop_action)

        QgsMessageLog.logMessage(
            "QGIS MCP Secure Plugin loaded",
            "QGIS MCP Secure",
            Qgis.Info
        )

    def unload(self):
        """Remove plugin menu items and icons"""
        # Stop server if running
        if self.server and self.server.running:
            self.stop_server()

        # Remove menu items
        for action in self.actions:
            self.iface.removePluginMenu("&QGIS MCP Secure", action)

    def start_server(self):
        """Start the secure MCP server"""
        if self.server and self.server.running:
            QMessageBox.warning(
                self.iface.mainWindow(),
                "Server Already Running",
                "MCP server is already running."
            )
            return

        try:
            # Create and start server
            self.server = SecureQGISMCPServer(
                host='127.0.0.1',
                port=9876,
                use_tls=False,
                require_auth=True
            )

            # Start in background thread
            import threading
            server_thread = threading.Thread(target=self.server.start, daemon=True)
            server_thread.start()

            # Update UI
            self.start_action.setEnabled(False)
            self.stop_action.setEnabled(True)

            # Show token to user
            token = self.server.auth_manager.api_token
            QMessageBox.information(
                self.iface.mainWindow(),
                "Server Started",
                f"QGIS MCP Server started on 127.0.0.1:9876\n\n"
                f"Authentication Token:\n{token}\n\n"
                f"Use this token in your client applications."
            )

            QgsMessageLog.logMessage(
                "Secure MCP server started successfully",
                "QGIS MCP Secure",
                Qgis.Success
            )

        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Server Start Failed",
                f"Failed to start MCP server:\n{str(e)}"
            )
            QgsMessageLog.logMessage(
                f"Failed to start server: {e}",
                "QGIS MCP Secure",
                Qgis.Critical
            )

    def stop_server(self):
        """Stop the MCP server"""
        if not self.server or not self.server.running:
            return

        try:
            self.server.stop()

            # Update UI
            self.start_action.setEnabled(True)
            self.stop_action.setEnabled(False)

            QMessageBox.information(
                self.iface.mainWindow(),
                "Server Stopped",
                "QGIS MCP Server has been stopped."
            )

            QgsMessageLog.logMessage(
                "Secure MCP server stopped",
                "QGIS MCP Secure",
                Qgis.Info
            )

        except Exception as e:
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Server Stop Failed",
                f"Failed to stop MCP server:\n{str(e)}"
            )
            QgsMessageLog.logMessage(
                f"Failed to stop server: {e}",
                "QGIS MCP Secure",
                Qgis.Critical
            )
