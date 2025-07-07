"""
Configuration Modal for Aurora UI

This module provides a comprehensive configuration dialog that integrates
with Aurora's config manager and includes MCP server management with auto-discovery.
"""

import json
from typing import Any, List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QPushButton,
    QLabel, QTextEdit, QScrollArea, QFrame,
    QMessageBox, QProgressBar,
    QFileDialog, QListWidget, QListWidgetItem,
    QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

from app.config.config_manager import config_manager
from app.config.config_api import ConfigAPI
from app.helpers.aurora_logger import log_info, log_error, log_debug


class MCPDiscoveryWorker(QThread):
    """Worker thread for MCP server discovery"""
    discovery_finished = pyqtSignal(dict)
    progress_update = pyqtSignal(str)

    def run(self):
        try:
            self.progress_update.emit("Discovering MCP servers...")
            result = ConfigAPI.discover_mcp_servers()
            self.discovery_finished.emit(result)
        except Exception as e:
            log_error(f"MCP discovery error: {e}")
            self.discovery_finished.emit({"success": False, "error": str(e)})


class ConfigField:
    """Represents a configuration field with its metadata"""

    def __init__(self, key: str, value: Any, field_type: str = "auto",
                 description: str = "", choices: List[str] = None,
                 min_val: float = None, max_val: float = None):
        self.key = key
        self.value = value
        self.field_type = field_type
        self.description = description
        self.choices = choices or []
        self.min_val = min_val
        self.max_val = max_val

        # Auto-detect field type if not specified
        if field_type == "auto":
            self.field_type = self._detect_type()

    def _detect_type(self) -> str:
        """Auto-detect the field type based on value"""
        if isinstance(self.value, bool):
            return "bool"
        elif isinstance(self.value, int):
            return "int"
        elif isinstance(self.value, float):
            return "float"
        elif isinstance(self.value, str):
            if len(self.value) > 100:
                return "text"
            return "string"
        elif isinstance(self.value, (list, tuple)):
            return "list"
        elif isinstance(self.value, dict):
            return "dict"
        else:
            return "string"


class ConfigWidget(QWidget):
    """Widget for editing a single configuration field"""

    value_changed = pyqtSignal(str, object)  # key, new_value

    def __init__(self, field: ConfigField, parent=None):
        super().__init__(parent)
        self.field = field
        self.widget = None
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create appropriate widget based on field type
        if self.field.field_type == "bool":
            self.widget = QCheckBox()
            self.widget.setChecked(bool(self.field.value))
            self.widget.stateChanged.connect(self._on_bool_changed)

        elif self.field.field_type == "int":
            self.widget = QSpinBox()
            if self.field.min_val is not None:
                self.widget.setMinimum(int(self.field.min_val))
            else:
                self.widget.setMinimum(-999999)
            if self.field.max_val is not None:
                self.widget.setMaximum(int(self.field.max_val))
            else:
                self.widget.setMaximum(999999)
            self.widget.setValue(int(self.field.value))
            self.widget.valueChanged.connect(self._on_int_changed)

        elif self.field.field_type == "float":
            self.widget = QDoubleSpinBox()
            self.widget.setDecimals(3)
            if self.field.min_val is not None:
                self.widget.setMinimum(float(self.field.min_val))
            else:
                self.widget.setMinimum(-999999.0)
            if self.field.max_val is not None:
                self.widget.setMaximum(float(self.field.max_val))
            else:
                self.widget.setMaximum(999999.0)
            self.widget.setValue(float(self.field.value))
            self.widget.valueChanged.connect(self._on_float_changed)

        elif self.field.field_type == "choice" and self.field.choices:
            self.widget = QComboBox()
            self.widget.addItems(self.field.choices)
            if str(self.field.value) in self.field.choices:
                self.widget.setCurrentText(str(self.field.value))
            self.widget.currentTextChanged.connect(self._on_choice_changed)

        elif self.field.field_type == "text" or (isinstance(self.field.value, str) and len(str(self.field.value)) > 100):
            self.widget = QTextEdit()
            self.widget.setMaximumHeight(100)
            self.widget.setPlainText(str(self.field.value))
            self.widget.textChanged.connect(self._on_text_changed)

        elif isinstance(self.field.value, list):
            # Handle lists as comma-separated values or JSON
            self.widget = QLineEdit()
            if all(isinstance(item, (str, int, float, bool)) for item in self.field.value):
                # Simple list - show as comma-separated
                self.widget.setText(", ".join(str(item) for item in self.field.value))
                self.widget.setPlaceholderText("Comma-separated values")
            else:
                # Complex list - show as JSON
                self.widget.setText(json.dumps(self.field.value, indent=2))
                self.widget.setPlaceholderText("JSON array")
            self.widget.textChanged.connect(self._on_list_changed)

        elif isinstance(self.field.value, dict):
            # Handle small dicts as JSON
            self.widget = QTextEdit() if len(json.dumps(self.field.value)) > 50 else QLineEdit()
            formatted_json = json.dumps(self.field.value, indent=2)
            if isinstance(self.widget, QTextEdit):
                self.widget.setMaximumHeight(100)
                self.widget.setPlainText(formatted_json)
                self.widget.textChanged.connect(self._on_dict_changed)
            else:
                self.widget.setText(formatted_json)
                self.widget.textChanged.connect(self._on_dict_changed_line)
            self.widget.setPlaceholderText("JSON object")

        else:  # string or unknown
            self.widget = QLineEdit()
            self.widget.setText(str(self.field.value))
            self.widget.textChanged.connect(self._on_string_changed)

        layout.addWidget(self.widget)

        # Add description tooltip if available
        if self.field.description:
            self.widget.setToolTip(self.field.description)

    def _on_bool_changed(self, state):
        self.value_changed.emit(self.field.key, state == Qt.CheckState.Checked.value)

    def _on_int_changed(self, value):
        self.value_changed.emit(self.field.key, value)

    def _on_float_changed(self, value):
        self.value_changed.emit(self.field.key, value)

    def _on_choice_changed(self, text):
        self.value_changed.emit(self.field.key, text)

    def _on_text_changed(self):
        text = self.widget.toPlainText()
        # Try to parse as JSON for dicts/lists in text areas
        if self.field.field_type in ["list", "dict"]:
            try:
                value = json.loads(text)
                self.value_changed.emit(self.field.key, value)
            except json.JSONDecodeError:
                # Keep as string if invalid JSON
                self.value_changed.emit(self.field.key, text)
        else:
            self.value_changed.emit(self.field.key, text)

    def _on_list_changed(self, text):
        try:
            # Try to parse as JSON first
            if text.strip().startswith('['):
                value = json.loads(text)
            else:
                # Parse as comma-separated values
                if text.strip():
                    items = [item.strip() for item in text.split(',')]
                    # Try to convert to appropriate types
                    value = []
                    for item in items:
                        if item.lower() in ['true', 'false']:
                            value.append(item.lower() == 'true')
                        elif item.isdigit():
                            value.append(int(item))
                        elif '.' in item and item.replace('.', '').isdigit():
                            value.append(float(item))
                        else:
                            value.append(item)
                else:
                    value = []
            self.value_changed.emit(self.field.key, value)
        except (json.JSONDecodeError, ValueError):
            # Keep as string if parsing fails
            self.value_changed.emit(self.field.key, text)

    def _on_dict_changed(self):
        text = self.widget.toPlainText()
        try:
            value = json.loads(text)
            self.value_changed.emit(self.field.key, value)
        except json.JSONDecodeError:
            # Keep as string if invalid JSON
            self.value_changed.emit(self.field.key, text)

    def _on_dict_changed_line(self, text):
        try:
            value = json.loads(text)
            self.value_changed.emit(self.field.key, value)
        except json.JSONDecodeError:
            # Keep as string if invalid JSON
            self.value_changed.emit(self.field.key, text)

    def _on_string_changed(self, text):
        self.value_changed.emit(self.field.key, text)


class MCPServerWidget(QWidget):
    """Widget for managing a single MCP server configuration"""

    server_changed = pyqtSignal(str, dict)  # server_name, config
    server_removed = pyqtSignal(str)  # server_name

    def __init__(self, server_name: str, server_config: dict, parent=None):
        super().__init__(parent)
        self.server_name = server_name
        self.server_config = server_config.copy()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header with server name and remove button
        header_layout = QHBoxLayout()

        name_label = QLabel(f"<b>{self.server_name}</b>")
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self.server_removed.emit(self.server_name))
        header_layout.addWidget(remove_btn)

        layout.addLayout(header_layout)

        # Configuration form
        form_layout = QFormLayout()

        # Enabled checkbox
        self.enabled_cb = QCheckBox()
        self.enabled_cb.setChecked(self.server_config.get("enabled", True))
        self.enabled_cb.stateChanged.connect(self._on_config_changed)
        form_layout.addRow("Enabled:", self.enabled_cb)

        # Transport
        self.transport_combo = QComboBox()
        self.transport_combo.addItems(["stdio", "streamable_http", "sse", "websocket"])
        transport = self.server_config.get("transport", "stdio")
        if transport in ["stdio", "streamable_http", "sse", "websocket"]:
            self.transport_combo.setCurrentText(transport)
        self.transport_combo.currentTextChanged.connect(self._on_config_changed)
        form_layout.addRow("Transport:", self.transport_combo)

        # Command (for stdio)
        self.command_edit = QLineEdit()
        self.command_edit.setText(self.server_config.get("command", ""))
        self.command_edit.textChanged.connect(self._on_config_changed)
        form_layout.addRow("Command:", self.command_edit)

        # Args (for stdio)
        self.args_edit = QLineEdit()
        args = self.server_config.get("args", [])
        if isinstance(args, list):
            self.args_edit.setText(json.dumps(args))
        else:
            self.args_edit.setText(str(args))
        self.args_edit.textChanged.connect(self._on_config_changed)
        form_layout.addRow("Arguments:", self.args_edit)

        # URL (for HTTP transports)
        self.url_edit = QLineEdit()
        self.url_edit.setText(self.server_config.get("url", ""))
        self.url_edit.textChanged.connect(self._on_config_changed)
        form_layout.addRow("URL:", self.url_edit)

        # Environment variables
        self.env_edit = QTextEdit()
        self.env_edit.setMaximumHeight(60)
        env = self.server_config.get("env", {})
        if isinstance(env, dict):
            self.env_edit.setPlainText(json.dumps(env, indent=2))
        else:
            self.env_edit.setPlainText(str(env))
        self.env_edit.textChanged.connect(self._on_config_changed)
        form_layout.addRow("Environment:", self.env_edit)

        layout.addLayout(form_layout)

        # Add a separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

    def _on_config_changed(self):
        """Update server config when any field changes"""
        self.server_config = {
            "enabled": self.enabled_cb.isChecked(),
            "transport": self.transport_combo.currentText(),
            "command": self.command_edit.text(),
            "url": self.url_edit.text()
        }

        # Parse args as JSON
        try:
            args_text = self.args_edit.text().strip()
            if args_text:
                self.server_config["args"] = json.loads(args_text)
            else:
                self.server_config["args"] = []
        except json.JSONDecodeError:
            self.server_config["args"] = [self.args_edit.text()]

        # Parse env as JSON
        try:
            env_text = self.env_edit.toPlainText().strip()
            if env_text:
                self.server_config["env"] = json.loads(env_text)
            else:
                self.server_config["env"] = {}
        except json.JSONDecodeError:
            self.server_config["env"] = {}

        self.server_changed.emit(self.server_name, self.server_config)


class ConfigurationModal(QDialog):
    """Main configuration modal dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_changes = {}
        self.mcp_servers = {}
        self.discovery_worker = None
        self.setup_ui()
        self.load_configuration()

    def setup_ui(self):
        self.setWindowTitle("Aurora Configuration")
        self.setModal(True)
        self.resize(900, 700)

        layout = QVBoxLayout(self)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self.create_general_tab()
        self.create_plugins_tab()
        self.create_ui_tab()
        self.create_mcp_tab()
        self.create_advanced_tab()

        # Buttons
        button_layout = QHBoxLayout()

        # Reset button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        # Apply button
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_changes)
        button_layout.addWidget(apply_btn)

        # OK button
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept_changes)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

    def create_general_tab(self):
        """Create the general configuration tab"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "General")

        layout = QVBoxLayout(tab)

        # Create scroll area for config fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        self.general_layout = QFormLayout(content_widget)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # This will be populated by load_configuration()

    def create_plugins_tab(self):
        """Create the plugins configuration tab"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "Plugins")

        layout = QVBoxLayout(tab)

        # Create scroll area for plugin fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        self.plugins_layout = QFormLayout(content_widget)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def create_ui_tab(self):
        """Create the UI configuration tab"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "User Interface")

        layout = QVBoxLayout(tab)

        # Create scroll area for UI fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        self.ui_layout = QFormLayout(content_widget)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def create_mcp_tab(self):
        """Create the MCP servers configuration tab"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "MCP Servers")

        layout = QVBoxLayout(tab)

        # Top section with discovery and add buttons
        top_layout = QHBoxLayout()

        # MCP status
        self.mcp_status_label = QLabel("Loading MCP status...")
        top_layout.addWidget(self.mcp_status_label)

        top_layout.addStretch()

        # Discovery button
        self.discover_btn = QPushButton("Discover Servers")
        self.discover_btn.clicked.connect(self.discover_mcp_servers)
        top_layout.addWidget(self.discover_btn)

        # Add server button
        add_server_btn = QPushButton("Add Server")
        add_server_btn.clicked.connect(self.add_mcp_server)
        top_layout.addWidget(add_server_btn)

        layout.addLayout(top_layout)

        # Progress bar for discovery
        self.discovery_progress = QProgressBar()
        self.discovery_progress.setVisible(False)
        layout.addWidget(self.discovery_progress)

        # Scroll area for MCP servers
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.mcp_content_widget = QWidget()
        self.mcp_servers_layout = QVBoxLayout(self.mcp_content_widget)
        self.mcp_servers_layout.addStretch()  # Add stretch at bottom

        scroll.setWidget(self.mcp_content_widget)
        layout.addWidget(scroll)

        # Update MCP status
        QTimer.singleShot(100, self.update_mcp_status)

    def create_advanced_tab(self):
        """Create the advanced configuration tab"""
        tab = QWidget()
        self.tab_widget.addTab(tab, "Advanced")

        layout = QVBoxLayout(tab)

        # Raw config editor
        label = QLabel("Raw Configuration (JSON):")
        layout.addWidget(label)

        self.raw_config_edit = QTextEdit()
        self.raw_config_edit.setFont(QFont("Courier", 10))
        layout.addWidget(self.raw_config_edit)

        # Buttons for raw config
        raw_buttons = QHBoxLayout()

        load_btn = QPushButton("Load from File")
        load_btn.clicked.connect(self.load_config_from_file)
        raw_buttons.addWidget(load_btn)

        save_btn = QPushButton("Save to File")
        save_btn.clicked.connect(self.save_config_to_file)
        raw_buttons.addWidget(save_btn)

        raw_buttons.addStretch()

        validate_btn = QPushButton("Validate JSON")
        validate_btn.clicked.connect(self.validate_raw_config)
        raw_buttons.addWidget(validate_btn)

        layout.addLayout(raw_buttons)

    def load_configuration(self):
        """Load current configuration into the UI"""
        try:
            # Get full configuration
            config = config_manager.get_config_dict()

            # Organize config by categories
            self.load_category_config("general", config, self.general_layout)
            self.load_category_config("plugins", config.get("plugins", {}), self.plugins_layout)
            self.load_category_config("ui", config.get("ui", {}), self.ui_layout)

            # Load MCP servers
            self.load_mcp_servers(config.get("mcp", {}).get("servers", {}))

            # Load raw config
            self.raw_config_edit.setPlainText(json.dumps(config, indent=2))

        except Exception as e:
            log_error(f"Error loading configuration: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load configuration: {e}")

    def load_category_config(self, category: str, config_data: dict, layout: QFormLayout):
        """Load configuration fields for a specific category recursively"""
        self._load_config_recursive(category, config_data, layout, prefix="")

    def _load_config_recursive(self, category: str, config_data: dict, layout: QFormLayout, prefix: str = ""):
        """Recursively load configuration with proper type-based widgets"""
        # Get metadata from config manager instead of hardcoded method
        field_metadata = config_manager.get_field_metadata()

        for key, value in config_data.items():
            if category == "general" and key in ["plugins", "ui", "mcp"]:
                continue  # Skip sub-categories in general tab

            # Build the full key path
            if prefix:
                full_key = f"{prefix}.{key}"
                display_key = f"{prefix.split('.')[-1]}.{key}" if '.' in prefix else f"{prefix}.{key}"
            else:
                full_key = f"{category}.{key}" if category != "general" else key
                display_key = key

            # Check if this is a nested dictionary that should be expanded
            if isinstance(value, dict) and len(value) > 0:
                # Always expand dictionaries that contain configuration options
                # Only treat as single field if explicitly marked in metadata
                metadata = field_metadata.get(full_key, {})
                should_expand = metadata.get("expand_dict", True)

                # Special case: always expand 'options' dictionaries and common config containers
                if key in ["options", "config", "settings"] or should_expand:
                    # Add a group separator for nested configs
                    indent_level = full_key.count('.') - (1 if category != "general" else 0)
                    indent = "  " * indent_level

                    separator_label = QLabel(f"<b>{indent}{display_key.replace('_', ' ').title()}</b>")
                    separator_style = "color: #666; margin-top: 10px; margin-bottom: 5px;"
                    if indent_level > 0:
                        separator_style += f" margin-left: {indent_level * 15}px;"
                    separator_label.setStyleSheet(separator_style)
                    layout.addRow(separator_label)

                    # Recursively add nested fields with indentation
                    self._load_config_recursive(category, value, layout, full_key)
                    continue
                else:
                    # Treat as single JSON field
                    pass  # Fall through to create single field

            # Create field for primitive values or dictionaries marked as single fields
            metadata = field_metadata.get(full_key, {})

            field = ConfigField(
                key=full_key,
                value=value,
                field_type=metadata.get("type", "auto"),
                description=metadata.get("description", ""),
                choices=metadata.get("choices", []),
                min_val=metadata.get("min", None),
                max_val=metadata.get("max", None)
            )

            widget = ConfigWidget(field)
            widget.value_changed.connect(self.on_config_changed)

            # Create label with proper formatting and indentation
            indent_level = full_key.count('.') - (1 if category != "general" else 0)
            indent = "  " * indent_level
            label_text = f"{indent}{display_key.replace('_', ' ').title()}:"
            label = QLabel(label_text)

            if field.description:
                label.setToolTip(field.description)

            # Style nested fields slightly differently
            if indent_level > 0:
                label.setStyleSheet(f"color: #444; font-size: 12px; margin-left: {indent_level * 15}px;")
                widget.setStyleSheet(f"margin-left: {indent_level * 15}px;")

            layout.addRow(label, widget)

    def load_mcp_servers(self, servers_config: dict):
        """Load MCP servers configuration"""
        # Clear existing server widgets
        while self.mcp_servers_layout.count() > 1:  # Keep the stretch
            child = self.mcp_servers_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.mcp_servers = servers_config.copy()

        # Add server widgets
        for server_name, server_config in servers_config.items():
            server_widget = MCPServerWidget(server_name, server_config)
            server_widget.server_changed.connect(self.on_mcp_server_changed)
            server_widget.server_removed.connect(self.remove_mcp_server)

            # Insert before the stretch
            self.mcp_servers_layout.insertWidget(
                self.mcp_servers_layout.count() - 1, server_widget
            )

    def on_config_changed(self, key: str, value: Any):
        """Handle configuration field changes"""
        self.config_changes[key] = value
        log_debug(f"Config changed: {key} = {value}")

    def on_mcp_server_changed(self, server_name: str, config: dict):
        """Handle MCP server configuration changes"""
        self.mcp_servers[server_name] = config

    def add_mcp_server(self):
        """Add a new MCP server"""
        name, ok = QInputDialog.getText(
            self, "Add MCP Server", "Server name:"
        )

        if ok and name.strip():
            server_name = name.strip()
            if server_name in self.mcp_servers:
                QMessageBox.warning(
                    self, "Warning",
                    f"Server '{server_name}' already exists."
                )
                return

            # Default server configuration
            default_config = {
                "enabled": True,
                "transport": "stdio",
                "command": "python",
                "args": [],
                "url": "",
                "env": {}
            }

            self.mcp_servers[server_name] = default_config

            # Add widget
            server_widget = MCPServerWidget(server_name, default_config)
            server_widget.server_changed.connect(self.on_mcp_server_changed)
            server_widget.server_removed.connect(self.remove_mcp_server)

            # Insert before the stretch
            self.mcp_servers_layout.insertWidget(
                self.mcp_servers_layout.count() - 1, server_widget
            )

    def remove_mcp_server(self, server_name: str):
        """Remove an MCP server"""
        reply = QMessageBox.question(
            self, "Confirm Removal",
            f"Are you sure you want to remove server '{server_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Remove from config
            if server_name in self.mcp_servers:
                del self.mcp_servers[server_name]

            # Remove widget
            for i in range(self.mcp_servers_layout.count() - 1):  # Exclude stretch
                widget = self.mcp_servers_layout.itemAt(i).widget()
                if isinstance(widget, MCPServerWidget) and widget.server_name == server_name:
                    widget.deleteLater()
                    break

    def discover_mcp_servers(self):
        """Discover available MCP servers"""
        if self.discovery_worker and self.discovery_worker.isRunning():
            return

        self.discover_btn.setEnabled(False)
        self.discovery_progress.setVisible(True)
        self.discovery_progress.setRange(0, 0)  # Indeterminate progress

        self.discovery_worker = MCPDiscoveryWorker()
        self.discovery_worker.discovery_finished.connect(self.on_discovery_finished)
        self.discovery_worker.progress_update.connect(self.discovery_progress.setFormat)
        self.discovery_worker.start()

    def on_discovery_finished(self, result: dict):
        """Handle discovery results"""
        self.discover_btn.setEnabled(True)
        self.discovery_progress.setVisible(False)

        if result.get("success"):
            servers = result.get("servers", {})
            if servers:
                self.show_discovery_results(servers)
            else:
                QMessageBox.information(
                    self, "Discovery Complete",
                    "No MCP servers were discovered."
                )
        else:
            error = result.get("error", "Unknown error")
            QMessageBox.critical(
                self, "Discovery Failed",
                f"Failed to discover MCP servers: {error}"
            )

    def show_discovery_results(self, servers: dict):
        """Show discovery results and allow user to add servers"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Discovered MCP Servers")
        dialog.resize(600, 400)

        layout = QVBoxLayout(dialog)

        label = QLabel("Select servers to add to configuration:")
        layout.addWidget(label)

        # List widget with checkboxes
        server_list = QListWidget()
        for server_name, server_info in servers.items():
            item = QListWidgetItem(f"{server_name} ({server_info.get('transport', 'Unknown')})")
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, server_name)
            server_list.addItem(item)

        layout.addWidget(server_list)

        # Buttons
        button_layout = QHBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(lambda: self.select_all_servers(server_list, True))
        button_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(lambda: self.select_all_servers(server_list, False))
        button_layout.addWidget(select_none_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        add_btn = QPushButton("Add Selected")
        add_btn.clicked.connect(lambda: self.add_selected_servers(dialog, server_list, servers))
        button_layout.addWidget(add_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def select_all_servers(self, server_list: QListWidget, select: bool):
        """Select/deselect all servers in the list"""
        state = Qt.CheckState.Checked if select else Qt.CheckState.Unchecked
        for i in range(server_list.count()):
            server_list.item(i).setCheckState(state)

    def add_selected_servers(self, dialog: QDialog, server_list: QListWidget, servers: dict):
        """Add selected servers to configuration"""
        selected_servers = []
        for i in range(server_list.count()):
            item = server_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                server_name = item.data(Qt.ItemDataRole.UserRole)
                selected_servers.append(server_name)

        if not selected_servers:
            QMessageBox.information(dialog, "No Selection", "Please select at least one server.")
            return

        # Add servers to configuration
        added_count = 0
        for server_name in selected_servers:
            if server_name in self.mcp_servers:
                continue  # Skip existing servers

            server_info = servers[server_name]
            server_config = {
                "enabled": True,
                "transport": server_info.get("transport", "stdio"),
                "command": server_info.get("command", ""),
                "args": server_info.get("args", []),
                "url": server_info.get("url", ""),
                "env": server_info.get("env", {})
            }

            self.mcp_servers[server_name] = server_config

            # Add widget
            server_widget = MCPServerWidget(server_name, server_config)
            server_widget.server_changed.connect(self.on_mcp_server_changed)
            server_widget.server_removed.connect(self.remove_mcp_server)

            # Insert before the stretch
            self.mcp_servers_layout.insertWidget(
                self.mcp_servers_layout.count() - 1, server_widget
            )
            added_count += 1

        dialog.accept()

        QMessageBox.information(
            self, "Servers Added",
            f"Added {added_count} MCP servers to configuration."
        )

    def update_mcp_status(self):
        """Update MCP status display"""
        try:
            status = ConfigAPI.get_mcp_status()
            if status.get("error"):
                status_text = f"Error: {status['error']}"
            else:
                enabled = status.get("enabled", False)
                initialized = status.get("initialized", False)
                tool_count = status.get("tool_count", 0)

                status_text = f"Enabled: {enabled}, Initialized: {initialized}, Tools: {tool_count}"

            self.mcp_status_label.setText(f"MCP Status: {status_text}")

        except Exception as e:
            self.mcp_status_label.setText(f"MCP Status: Error - {e}")

    def validate_raw_config(self):
        """Validate the raw JSON configuration"""
        try:
            json.loads(self.raw_config_edit.toPlainText())
            QMessageBox.information(self, "Valid", "Configuration JSON is valid.")
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Invalid JSON", f"Invalid JSON: {e}")

    def load_config_from_file(self):
        """Load configuration from a file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    config_text = f.read()
                self.raw_config_edit.setPlainText(config_text)
                QMessageBox.information(self, "Loaded", "Configuration loaded from file.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def save_config_to_file(self):
        """Save configuration to a file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration", "aurora_config.json", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.raw_config_edit.toPlainText())
                QMessageBox.information(self, "Saved", "Configuration saved to file.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        reply = QMessageBox.question(
            self, "Reset Configuration",
            "Are you sure you want to reset all configuration to defaults? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Reset to defaults (this would need implementation in config_manager)
                # For now, just reload current config
                self.config_changes.clear()
                self.load_configuration()
                QMessageBox.information(self, "Reset", "Configuration reset to defaults.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset configuration: {e}")

    def apply_changes(self):
        """Apply configuration changes without closing dialog"""
        try:
            self.save_configuration()
            QMessageBox.information(self, "Applied", "Configuration changes applied successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply changes: {e}")

    def accept_changes(self):
        """Apply changes and close dialog"""
        try:
            self.save_configuration()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")

    def save_configuration(self):
        """Save all configuration changes"""
        try:
            # Apply field changes
            for key, value in self.config_changes.items():
                config_manager.set(key, value)

            # Apply MCP server changes
            if self.mcp_servers:
                config_manager.set("mcp.servers", self.mcp_servers)

            # Try to apply raw config if modified
            try:
                raw_config = json.loads(self.raw_config_edit.toPlainText())
                # Only apply if significantly different
                current_config = config_manager.get_config_dict()
                if raw_config != current_config:
                    # This would need a method to replace entire config
                    log_info("Raw config differs from current - manual merge needed")
            except json.JSONDecodeError:
                # Ignore invalid JSON in raw editor
                pass

            # Reload modules that depend on configuration
            self.reload_dependent_modules()

            log_info("Configuration saved successfully")

        except Exception as e:
            log_error(f"Error saving configuration: {e}")
            raise

    def reload_dependent_modules(self):
        """Reload modules that depend on configuration changes"""
        try:
            # Reload MCP servers if changed
            if "mcp.servers" in self.config_changes or self.mcp_servers:
                log_info("Reloading MCP servers...")
                ConfigAPI.reload_mcp_servers()

            # Notify UI of theme changes
            if "ui.dark_mode" in self.config_changes:
                log_info("UI theme change detected - restart may be required")

            # Clear changes after applying
            self.config_changes.clear()

        except Exception as e:
            log_error(f"Error reloading modules: {e}")
            # Don't raise - configuration was saved successfully
