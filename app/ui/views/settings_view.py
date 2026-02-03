"""
Settings View - Application configuration with multi-LLM support
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import requests
from app.core.config import get_settings, update_settings, Settings
from app.core.constants import Language, Theme, AuthMethod
from app.core.logger import get_logger
from app.models.connection_profile import ConnectionProfile
from app.services.connection_store import get_connection_store
from app.services.credential_store import get_credential_store
from app.database.connection import DatabaseConnection, AuthenticationError, ConnectionError as DBConnectionError, get_available_odbc_drivers, get_connection_manager
from app.ui.views.base_view import BaseView

logger = get_logger("ui.settings")


class LLMProvider(Enum):
    """Supported LLM providers"""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    DEEPSEEK = "deepseek"


class LLMTestWorker(QThread):
    """Worker thread for testing LLM connections"""

    test_completed = pyqtSignal(str, bool, str)  # provider_id, success, message

    def __init__(self, provider_config: Dict[str, Any]):
        super().__init__()
        self.provider_config = provider_config

    def run(self):
        """Test LLM connection in background thread"""
        try:
            provider_type = self.provider_config.get("type", "ollama")
            provider_id = self.provider_config.get("id", "default")

            if provider_type == LLMProvider.OLLAMA.value:
                success, message = self._test_ollama()
            elif provider_type == LLMProvider.OPENAI.value:
                success, message = self._test_openai()
            elif provider_type == LLMProvider.ANTHROPIC.value:
                success, message = self._test_anthropic()
            elif provider_type == LLMProvider.AZURE_OPENAI.value:
                success, message = self._test_azure_openai()
            elif provider_type == LLMProvider.DEEPSEEK.value:
                success, message = self._test_deepseek()
            else:
                success, message = False, f"Unknown provider type: {provider_type}"

            self.test_completed.emit(provider_id, success, message)

        except Exception as e:
            logger.error(f"Test worker error: {e}")
            self.test_completed.emit(
                self.provider_config.get("id", "default"),
                False,
                f"Connection test failed: {str(e)}",
            )

    def _test_ollama(self) -> tuple[bool, str]:
        """Test Ollama connection"""
        try:
            host = self.provider_config.get("host", "http://localhost:11434")
            model = self.provider_config.get("model", "codellama")
            
            # Test 1: Check if Ollama is running
            response = requests.get(f"{host}/api/tags", timeout=5)
            if response.status_code != 200:
                return False, f"❌ Ollama returned error: {response.status_code}"
            
            # Test 2: Check if model exists
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            
            if model in models or any(m.startswith(f"{model}:") for m in models):
                return True, f"✅ Ollama is running and model '{model}' is available."
            else:
                available = ", ".join(models[:3]) + ("..." if len(models) > 3 else "")
                return True, f"⚠️ Ollama is running, but model '{model}' not found.\nAvailable models: {available or 'None'}"

        except requests.exceptions.ConnectionError:
            return False, "❌ Could not connect to Ollama. Is it running?"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"

    def _test_openai(self) -> tuple[bool, str]:
        """Test OpenAI connection"""
        api_key = self.provider_config.get("api_key", "")
        model = self.provider_config.get("model", "gpt-4o")
        
        if not api_key:
            return False, "❌ OpenAI API key not provided"

        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
            
            if response.status_code == 200:
                return True, f"✅ OpenAI API key is valid.\nModel: {model}"
            elif response.status_code == 401:
                return False, "❌ Invalid OpenAI API key."
            else:
                return False, f"❌ OpenAI API error: {response.status_code}\n{response.text[:100]}"
        except Exception as e:
            return False, f"❌ Connection error: {str(e)}"

    def _test_anthropic(self) -> tuple[bool, str]:
        """Test Anthropic connection"""
        api_key = self.provider_config.get("api_key", "")
        model = self.provider_config.get("model", "claude-3-5-sonnet-20241022")
        
        if not api_key:
            return False, "❌ Anthropic API key not provided"

        try:
            # Anthropic requires a POST request to test
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            # Simple message request with max_tokens=1 to minimize cost
            data = {
                "model": model,
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Ping"}]
            }
            response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=10)
            
            if response.status_code in [200, 400]: # 400 might mean model mismatch but key is valid
                if response.status_code == 200:
                    return True, f"✅ Anthropic API key is valid.\nModel: {model}"
                else:
                    return False, f"❌ Anthropic error: {response.json().get('error', {}).get('message', 'Unknown error')}"
            elif response.status_code == 401:
                return False, "❌ Invalid Anthropic API key."
            else:
                return False, f"❌ Anthropic API error: {response.status_code}"
        except Exception as e:
            return False, f"❌ Connection error: {str(e)}"

    def _test_azure_openai(self) -> tuple[bool, str]:
        """Test Azure OpenAI connection"""
        api_key = self.provider_config.get("api_key", "")
        endpoint = self.provider_config.get("endpoint", "")
        deployment = self.provider_config.get("deployment", "")

        if not api_key or not endpoint:
            return False, "❌ Azure OpenAI API key or endpoint not provided"

        try:
            headers = {"api-key": api_key}
            url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version=2023-05-15"
            data = {
                "messages": [{"role": "user", "content": "Ping"}],
                "max_tokens": 1
            }
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                return True, f"✅ Azure OpenAI connection successful."
            elif response.status_code == 401:
                return False, "❌ Invalid Azure API key."
            else:
                return False, f"❌ Azure error: {response.status_code}\n{response.text[:100]}"
        except Exception as e:
            return False, f"❌ Connection error: {str(e)}"

    def _test_deepseek(self) -> tuple[bool, str]:
        """Test DeepSeek connection"""
        api_key = self.provider_config.get("api_key", "")
        model = self.provider_config.get("model", "deepseek-chat")
        
        if not api_key:
            return False, "❌ DeepSeek API key not provided"

        try:
            # DeepSeek is OpenAI compatible
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get("https://api.deepseek.com/models", headers=headers, timeout=10)
            
            if response.status_code == 200:
                return True, f"✅ DeepSeek API key is valid.\nModel: {model}"
            elif response.status_code == 401:
                return False, "❌ Invalid DeepSeek API key."
            else:
                return False, f"❌ DeepSeek API error: {response.status_code}"
        except Exception as e:
            return False, f"❌ Connection error: {str(e)}"


class LLMProviderWidget(QWidget):
    """Widget for configuring a single LLM provider"""

    test_requested = pyqtSignal(str)  # provider_id
    remove_requested = pyqtSignal(str)  # provider_id
    set_default_requested = pyqtSignal(str)  # provider_id

    def __init__(self, provider_id: str, config: Dict[str, Any], is_default: bool = False, parent=None):
        super().__init__(parent)
        self.provider_id = provider_id
        self.config = config
        self.is_default = is_default
        self._setup_ui()

    def _setup_ui(self):
        """Setup provider configuration UI"""
        layout = QVBoxLayout(self)

        # Header with provider type and remove button
        header_layout = QHBoxLayout()

        provider_type = self.config.get("type", "ollama")
        self.header_label = QLabel()
        self._update_header_label()
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        # Default button
        self.default_btn = QPushButton("Set as Default")
        self.default_btn.setFixedWidth(100)
        self.default_btn.clicked.connect(lambda: self.set_default_requested.emit(self.provider_id))
        self.default_btn.setVisible(not self.is_default)
        header_layout.addWidget(self.default_btn)

        # Test button
        self.test_btn = QPushButton("Test")
        self.test_btn.setFixedWidth(80)
        self.test_btn.clicked.connect(lambda: self.test_requested.emit(self.provider_id))
        header_layout.addWidget(self.test_btn)

        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.setFixedWidth(80)
        remove_btn.setStyleSheet("""
            QPushButton { 
                color: #EF4444; 
                border: 1px solid #EF4444;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #EF4444;
                color: white;
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self.provider_id))
        header_layout.addWidget(remove_btn)

        layout.addLayout(header_layout)

        # Configuration form
        form_layout = QFormLayout()

        # Common fields
        self.name_edit = QLineEdit(self.config.get("name", self.provider_id))
        form_layout.addRow("Name:", self.name_edit)

        # Provider-specific fields
        if provider_type == LLMProvider.OLLAMA.value:
            self._setup_ollama_fields(form_layout)
        elif provider_type == LLMProvider.OPENAI.value:
            self._setup_openai_fields(form_layout)
        elif provider_type == LLMProvider.ANTHROPIC.value:
            self._setup_anthropic_fields(form_layout)
        elif provider_type == LLMProvider.AZURE_OPENAI.value:
            self._setup_azure_fields(form_layout)
        elif provider_type == LLMProvider.DEEPSEEK.value:
            self._setup_deepseek_fields(form_layout)

        layout.addLayout(form_layout)

        # Test result area
        self.test_result = QTextEdit()
        self.test_result.setMaximumHeight(60)
        self.test_result.setVisible(False)
        layout.addWidget(self.test_result)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #E2E8F0; max-height: 1px;")
        layout.addWidget(separator)

    def _update_header_label(self):
        """Update header label with default status"""
        provider_type = self.config.get("type", "ollama")
        status = " (DEFAULT)" if self.is_default else ""
        self.header_label.setText(f"🤖 {provider_type.upper()} - {self.provider_id}{status}")
        self.header_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        if self.is_default:
            self.header_label.setStyleSheet("color: #10B981;")  # Green for default
        else:
            self.header_label.setStyleSheet("color: #0F172A;")

    def set_is_default(self, is_default: bool):
        """Update default status"""
        self.is_default = is_default
        self.default_btn.setVisible(not is_default)
        self._update_header_label()

    def _setup_ollama_fields(self, form_layout):
        """Setup Ollama-specific fields"""
        self.host_edit = QLineEdit(self.config.get("host", "http://localhost:11434"))
        form_layout.addRow("Host:", self.host_edit)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(
            [
                "codellama",
                "codellama:13b",
                "mistral",
                "mixtral",
                "llama2",
                "sqlcoder",
                "deepseek-coder",
            ]
        )
        self.model_combo.setCurrentText(self.config.get("model", "codellama"))
        form_layout.addRow("Model:", self.model_combo)

    def _setup_openai_fields(self, form_layout):
        """Setup OpenAI-specific fields"""
        key_container = QWidget()
        key_layout = QHBoxLayout(key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)

        self.api_key_edit = QLineEdit(self.config.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter OpenAI API Key (sk-...)")
        key_layout.addWidget(self.api_key_edit)

        show_key_btn = QPushButton("👁️")
        show_key_btn.setFixedSize(30, 24)
        show_key_btn.setCheckable(True)
        show_key_btn.clicked.connect(lambda checked: self._toggle_password_visibility(checked, self.api_key_edit))
        key_layout.addWidget(show_key_btn)

        form_layout.addRow("API Key:", key_container)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(
            ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
        )
        self.model_combo.setCurrentText(self.config.get("model", "gpt-4o"))
        form_layout.addRow("Model:", self.model_combo)

    def _setup_anthropic_fields(self, form_layout):
        """Setup Anthropic-specific fields"""
        key_container = QWidget()
        key_layout = QHBoxLayout(key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)

        self.api_key_edit = QLineEdit(self.config.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter Anthropic API Key (sk-ant-...)")
        key_layout.addWidget(self.api_key_edit)

        show_key_btn = QPushButton("👁️")
        show_key_btn.setFixedSize(30, 24)
        show_key_btn.setCheckable(True)
        show_key_btn.clicked.connect(lambda checked: self._toggle_password_visibility(checked, self.api_key_edit))
        key_layout.addWidget(show_key_btn)

        form_layout.addRow("API Key:", key_container)

        self.model_combo = QComboBox()
        self.model_combo.addItems(
            [
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ]
        )
        self.model_combo.setCurrentText(self.config.get("model", "claude-3-5-sonnet-20241022"))
        form_layout.addRow("Model:", self.model_combo)

    def _setup_azure_fields(self, form_layout):
        """Setup Azure OpenAI-specific fields"""
        key_container = QWidget()
        key_layout = QHBoxLayout(key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)

        self.api_key_edit = QLineEdit(self.config.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        key_layout.addWidget(self.api_key_edit)

        show_key_btn = QPushButton("👁️")
        show_key_btn.setFixedSize(30, 24)
        show_key_btn.setCheckable(True)
        show_key_btn.clicked.connect(lambda checked: self._toggle_password_visibility(checked, self.api_key_edit))
        key_layout.addWidget(show_key_btn)

        form_layout.addRow("API Key:", key_container)

        self.endpoint_edit = QLineEdit(self.config.get("endpoint", ""))
        self.endpoint_edit.setPlaceholderText("https://your-resource.openai.azure.com")
        form_layout.addRow("Endpoint:", self.endpoint_edit)

        self.deployment_edit = QLineEdit(self.config.get("deployment", ""))
        form_layout.addRow("Deployment:", self.deployment_edit)

    def _setup_deepseek_fields(self, form_layout):
        """Setup DeepSeek-specific fields"""
        key_container = QWidget()
        key_layout = QHBoxLayout(key_container)
        key_layout.setContentsMargins(0, 0, 0, 0)

        self.api_key_edit = QLineEdit(self.config.get("api_key", ""))
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Enter DeepSeek API Key (sk-...)")
        key_layout.addWidget(self.api_key_edit)

        show_key_btn = QPushButton("👁️")
        show_key_btn.setFixedSize(30, 24)
        show_key_btn.setCheckable(True)
        show_key_btn.clicked.connect(lambda checked: self._toggle_password_visibility(checked, self.api_key_edit))
        key_layout.addWidget(show_key_btn)

        form_layout.addRow("API Key:", key_container)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(["deepseek-chat", "deepseek-coder"])
        self.model_combo.setCurrentText(self.config.get("model", "deepseek-chat"))
        form_layout.addRow("Model:", self.model_combo)

    def _toggle_password_visibility(self, checked, line_edit):
        """Toggle password visibility for API key fields"""
        if checked:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        config = {
            "id": self.provider_id,
            "type": self.config.get("type"),
            "name": self.name_edit.text(),
        }

        provider_type = self.config.get("type")

        if provider_type == LLMProvider.OLLAMA.value:
            config.update(
                {
                    "host": self.host_edit.text(),
                    "model": self.model_combo.currentText(),
                }
            )
        elif provider_type in [
            LLMProvider.OPENAI.value,
            LLMProvider.ANTHROPIC.value,
            LLMProvider.DEEPSEEK.value,
        ]:
            config.update(
                {
                    "api_key": self.api_key_edit.text(),
                    "model": self.model_combo.currentText(),
                }
            )
        elif provider_type == LLMProvider.AZURE_OPENAI.value:
            config.update(
                {
                    "api_key": self.api_key_edit.text(),
                    "endpoint": self.endpoint_edit.text(),
                    "deployment": self.deployment_edit.text(),
                }
            )

        return config

    def show_test_result(self, success: bool, message: str):
        """Show test result"""
        self.test_result.setVisible(True)
        self.test_result.setPlainText(message)

        if success:
            self.test_result.setStyleSheet("color: #10B981; background-color: #F0FDF4; border: 1px solid #86EFAC; border-radius: 8px;")
        else:
            self.test_result.setStyleSheet("color: #EF4444; background-color: #FEF2F2; border: 1px solid #FCA5A5; border-radius: 8px;")


class ConnectionEditDialog(QDialog):
    """Dialog for adding or editing a database connection"""

    def __init__(self, profile: Optional[ConnectionProfile] = None, parent=None):
        super().__init__(parent)
        self.profile = profile or ConnectionProfile()
        self.is_edit = profile is not None
        self.credential_store = get_credential_store()
        self._setup_ui()
        if self.is_edit:
            self._load_data()

    def _setup_ui(self):
        self.setWindowTitle("Edit Connection" if self.is_edit else "Add Connection")
        self.setMinimumWidth(450)
        layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Production Server")
        form_layout.addRow("Connection Name:", self.name_edit)

        self.server_edit = QLineEdit()
        self.server_edit.setPlaceholderText("e.g. localhost or 10.0.0.1")
        form_layout.addRow("Server / Instance:", self.server_edit)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(1433)
        form_layout.addRow("Port:", self.port_spin)

        self.database_edit = QLineEdit()
        self.database_edit.setPlaceholderText("master")
        self.database_edit.setText("master")
        form_layout.addRow("Default Database:", self.database_edit)

        self.auth_combo = QComboBox()
        self.auth_combo.addItem("SQL Server Authentication", AuthMethod.SQL_SERVER.value)
        self.auth_combo.addItem("Windows Authentication", AuthMethod.WINDOWS.value)
        self.auth_combo.currentIndexChanged.connect(self._on_auth_method_changed)
        form_layout.addRow("Authentication:", self.auth_combo)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("sa")
        form_layout.addRow("Username:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Leave empty to keep existing" if self.is_edit else "")
        form_layout.addRow("Password:", self.password_edit)

        self.driver_combo = QComboBox()
        self.driver_combo.addItem("Auto-select best available", None)
        for driver in get_available_odbc_drivers():
            self.driver_combo.addItem(driver, driver)
        form_layout.addRow("ODBC Driver:", self.driver_combo)

        layout.addLayout(form_layout)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        self.encrypt_check = QCheckBox("Encrypt Connection")
        self.encrypt_check.setChecked(True)
        self.trust_cert_check = QCheckBox("Trust Server Certificate")
        options_layout.addWidget(self.encrypt_check)
        options_layout.addWidget(self.trust_cert_check)
        layout.addWidget(options_group)

        # Buttons
        button_box = QHBoxLayout()
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_box.addWidget(test_btn)
        button_box.addStretch()
        button_box.addWidget(cancel_btn)
        button_box.addWidget(save_btn)
        layout.addLayout(button_box)

    def _on_auth_method_changed(self):
        is_sql = self.auth_combo.currentData() == AuthMethod.SQL_SERVER.value
        self.username_edit.setEnabled(is_sql)
        self.password_edit.setEnabled(is_sql)

    def _load_data(self):
        self.name_edit.setText(self.profile.name)
        self.server_edit.setText(self.profile.server)
        self.port_spin.setValue(self.profile.port)
        self.database_edit.setText(self.profile.database)
        
        idx = self.auth_combo.findData(self.profile.auth_method.value)
        if idx >= 0:
            self.auth_combo.setCurrentIndex(idx)
        
        self.username_edit.setText(self.profile.username)
        self.encrypt_check.setChecked(self.profile.encrypt)
        self.trust_cert_check.setChecked(self.profile.trust_server_certificate)
        
        if self.profile.driver:
            idx = self.driver_combo.findData(self.profile.driver)
            if idx >= 0:
                self.driver_combo.setCurrentIndex(idx)
                
        self._on_auth_method_changed()

    def get_profile(self) -> ConnectionProfile:
        self.profile.name = self.name_edit.text()
        self.profile.server = self.server_edit.text()
        self.profile.port = self.port_spin.value()
        self.profile.database = self.database_edit.text()
        self.profile.auth_method = AuthMethod(self.auth_combo.currentData())
        self.profile.username = self.username_edit.text()
        self.profile.encrypt = self.encrypt_check.isChecked()
        self.profile.trust_server_certificate = self.trust_cert_check.isChecked()
        self.profile.driver = self.driver_combo.currentData()
        return self.profile

    def get_password(self) -> Optional[str]:
        pwd = self.password_edit.text()
        return pwd if pwd else None

    def _test_connection(self):
        """Test the database connection with current inputs"""
        profile = self.get_profile()
        password = self.get_password()
        
        # Temporary store password if provided
        if password:
            self.credential_store.set_password(profile.id, password)
        
        try:
            conn = DatabaseConnection(profile)
            if conn.connect():
                info = conn.info
                msg = f"✅ Connection Successful!\n\nServer: {info.server_name}\nVersion: {info.server_version}\nEdition: {info.edition}"
                QMessageBox.information(self, "Success", msg)
                conn.disconnect()
            else:
                QMessageBox.critical(self, "Error", f"❌ Connection failed: {conn.last_error}")
        except AuthenticationError as e:
            QMessageBox.critical(self, "Auth Error", f"❌ Authentication failed: {str(e)}")
        except DBConnectionError as e:
            QMessageBox.critical(self, "Connection Error", f"❌ Connection failed: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Unexpected Error", f"❌ An unexpected error occurred: {str(e)}")


class SettingsView(BaseView):
    """
    Application settings view with multi-LLM support

    Signals:
        settings_changed: Emitted when settings are saved
    """

    settings_changed = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._test_worker = None
        self._llm_providers: Dict[str, LLMProviderWidget] = {}
        self._provider_counter = 1
        self._active_provider_id = "default_ollama"

    @property
    def view_title(self) -> str:
        return "Settings"

    def _apply_modern_styles(self) -> None:
        """Apply modern light theme styles"""
        from app.ui.theme import Colors
        
        self.setStyleSheet(f"""
            /* Background */
            SettingsView {{
                background-color: {Colors.BACKGROUND};
            }}
            
            /* GroupBox */
            QGroupBox {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
                margin-top: 16px;
                padding: 16px;
                padding-top: 28px;
                font-weight: 600;
                color: {Colors.TEXT_PRIMARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 12px;
                color: {Colors.TEXT_SECONDARY};
                font-size: 13px;
                font-weight: 600;
            }}
            
            /* TabWidget */
            QTabWidget::pane {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
                padding: 16px;
            }}
            QTabBar::tab {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 24px;
                color: {Colors.TEXT_SECONDARY};
                font-weight: 500;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.SURFACE};
                color: {Colors.PRIMARY};
                font-weight: 600;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: #F8FAFC;
                color: {Colors.TEXT_PRIMARY};
            }}
            
            /* Labels */
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                background: transparent;
            }}
            
            /* LineEdit */
            QLineEdit {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 10px 14px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 13px;
            }}
            QLineEdit:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QLineEdit:focus {{
                border-color: {Colors.PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {Colors.TEXT_MUTED};
            }}
            
            /* ComboBox */
            QComboBox {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 10px 14px;
                color: {Colors.TEXT_PRIMARY};
                min-height: 20px;
            }}
            QComboBox:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                selection-background-color: {Colors.PRIMARY}18;
                color: {Colors.TEXT_PRIMARY};
                padding: 4px;
            }}
            
            /* SpinBox */
            QSpinBox {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QSpinBox:hover {{
                border-color: {Colors.PRIMARY};
            }}
            
            /* CheckBox */
            QCheckBox {{
                color: {Colors.TEXT_PRIMARY};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {Colors.BORDER};
                border-radius: 4px;
                background-color: {Colors.SURFACE};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.PRIMARY};
                border-color: {Colors.PRIMARY};
            }}
            
            /* QPushButton */
            QPushButton {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 10px 20px;
                color: {Colors.TEXT_PRIMARY};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #F8FAFC;
                border-color: {Colors.PRIMARY};
            }}
            QPushButton#primaryButton {{
                background-color: {Colors.PRIMARY};
                border: none;
                color: white;
                font-weight: 600;
            }}
            QPushButton#primaryButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton#dangerButton {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.ERROR};
                color: {Colors.ERROR};
            }}
            QPushButton#dangerButton:hover {{
                background-color: {Colors.ERROR};
                color: white;
            }}
            
            /* TextEdit */
            QTextEdit {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
            
            /* TableWidget */
            QTableWidget {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                gridline-color: {Colors.BORDER};
                color: {Colors.TEXT_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY}18;
                color: {Colors.PRIMARY};
            }}
            QHeaderView::section {{
                background-color: #F8FAFC;
                color: {Colors.TEXT_SECONDARY};
                padding: 10px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                font-weight: 600;
            }}
            
            /* ScrollArea */
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            
            /* ScrollBar */
            QScrollBar:vertical {{
                background-color: {Colors.SURFACE};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BORDER};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {Colors.TEXT_MUTED};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            /* Frame separator */
            QFrame[frameShape="4"] {{
                background-color: {Colors.BORDER};
                max-height: 1px;
            }}
        """)

    def _setup_ui(self) -> None:
        """Setup settings UI with modern design"""
        from app.ui.theme import Colors
        
        # Apply modern styles
        self._apply_modern_styles()
        
        # Title
        title = QLabel("⚙️ Settings")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self._main_layout.addWidget(title)

        self._main_layout.addSpacing(16)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "General")
        tabs.addTab(self._create_ai_tab(), "AI / LLM")
        tabs.addTab(self._create_database_tab(), "Database")
        tabs.addTab(self._create_appearance_tab(), "Appearance")

        self._main_layout.addWidget(tabs)

        # Action buttons
        buttons_layout = QHBoxLayout()

        # Reset to defaults button
        self._reset_btn = QPushButton("Reset to Defaults")
        self._reset_btn.setObjectName("dangerButton")
        self._reset_btn.clicked.connect(self._reset_settings)
        buttons_layout.addWidget(self._reset_btn)

        buttons_layout.addStretch()

        # Save button
        self._save_btn = QPushButton("Save Settings")
        self._save_btn.setObjectName("primaryButton")
        self._save_btn.setFixedWidth(150)
        self._save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(self._save_btn)

        self._main_layout.addLayout(buttons_layout)

    def _create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # Language group
        lang_group = QGroupBox("Language")
        lang_layout = QFormLayout(lang_group)

        self._language_combo = QComboBox()
        self._language_combo.addItem("English", Language.ENGLISH.value)
        self._language_combo.addItem("Türkçe", Language.TURKISH.value)
        self._language_combo.addItem("Deutsch", Language.GERMAN.value)
        lang_layout.addRow("Interface Language:", self._language_combo)

        layout.addWidget(lang_group)

        # Startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QFormLayout(startup_group)

        self._auto_connect_check = QCheckBox("Auto-connect to last server")
        startup_layout.addRow(self._auto_connect_check)

        self._check_updates_check = QCheckBox("Check for updates on startup")
        self._check_updates_check.setChecked(True)
        startup_layout.addRow(self._check_updates_check)

        layout.addWidget(startup_group)

        # Application info
        info_group = QGroupBox("Application Info")
        info_layout = QFormLayout(info_group)

        info_layout.addRow("Version:", QLabel("1.0.0"))
        info_layout.addRow("Build:", QLabel("2025.01.15"))
        info_layout.addRow("Author:", QLabel("Erdal Cakiroglu"))

        # Show logs button
        logs_btn = QPushButton("Show Application Logs")
        logs_btn.clicked.connect(self._show_logs)
        info_layout.addRow("", logs_btn)

        layout.addWidget(info_group)

        layout.addStretch()
        return widget

    def _create_ai_tab(self) -> QWidget:
        """Create AI/LLM settings tab with multi-provider support"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # Header with add button
        header_layout = QHBoxLayout()
        header_label = QLabel("🤖 LLM Providers")
        header_label.setFont(QFont("", 14, QFont.Weight.Bold))
        header_layout.addWidget(header_label)

        header_layout.addStretch()

        # Add provider dropdown and button
        self._add_provider_combo = QComboBox()
        self._add_provider_combo.addItem("Add Ollama Provider", LLMProvider.OLLAMA.value)
        self._add_provider_combo.addItem("Add OpenAI Provider", LLMProvider.OPENAI.value)
        self._add_provider_combo.addItem("Add Anthropic Provider", LLMProvider.ANTHROPIC.value)
        self._add_provider_combo.addItem("Add Azure OpenAI", LLMProvider.AZURE_OPENAI.value)
        self._add_provider_combo.addItem("Add DeepSeek Provider", LLMProvider.DEEPSEEK.value)
        header_layout.addWidget(self._add_provider_combo)

        add_btn = QPushButton("Add Provider")
        add_btn.clicked.connect(self._add_provider)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Providers container (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._providers_widget = QWidget()
        self._providers_layout = QVBoxLayout(self._providers_widget)
        self._providers_layout.addStretch()

        scroll_area.setWidget(self._providers_widget)
        layout.addWidget(scroll_area)

        # Prompt rules editor
        prompt_group = QGroupBox("AI Prompt Kuralları")
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_layout.setSpacing(8)

        prompt_actions = QHBoxLayout()
        prompt_actions.addStretch()
        reset_prompt_btn = QPushButton("Reset Prompt Rules")
        reset_prompt_btn.clicked.connect(self._reset_prompt_rules_ui)
        prompt_actions.addWidget(reset_prompt_btn)
        prompt_layout.addLayout(prompt_actions)

        prompt_help = QLabel(
            "Not: {base_system} ve {base_user} yer tutucuları ile varsayılan promptu dahil edebilirsiniz."
        )
        prompt_help.setStyleSheet("color: #64748b; font-size: 11px;")
        prompt_layout.addWidget(prompt_help)

        self._prompt_tabs = QTabWidget()
        self._prompt_tabs.setMinimumHeight(320)

        # Global instructions tab
        global_tab = QWidget()
        global_layout = QVBoxLayout(global_tab)
        global_layout.setContentsMargins(8, 8, 8, 8)
        self._ai_global_instructions = QTextEdit()
        self._ai_global_instructions.setPlaceholderText("Tüm AI analizleri için ortak talimatlar...")
        self._ai_global_instructions.setMinimumHeight(120)
        global_layout.addWidget(self._ai_global_instructions)
        self._prompt_tabs.addTab(global_tab, "Global")

        # Query analysis tab
        query_tab = QWidget()
        query_layout = QFormLayout(query_tab)
        self._ai_query_system_edit = QTextEdit()
        self._ai_query_system_edit.setPlaceholderText("Query Analysis - System prompt override")
        self._ai_query_system_edit.setMinimumHeight(100)
        self._ai_query_user_edit = QTextEdit()
        self._ai_query_user_edit.setPlaceholderText("Query Analysis - User prompt override")
        self._ai_query_user_edit.setMinimumHeight(100)
        query_layout.addRow("System Prompt:", self._ai_query_system_edit)
        query_layout.addRow("User Prompt:", self._ai_query_user_edit)
        self._prompt_tabs.addTab(query_tab, "Query Analysis")

        # SP analysis tab
        sp_tab = QWidget()
        sp_layout = QFormLayout(sp_tab)
        self._ai_sp_system_edit = QTextEdit()
        self._ai_sp_system_edit.setPlaceholderText("SP Analysis - System prompt override")
        self._ai_sp_system_edit.setMinimumHeight(100)
        self._ai_sp_user_edit = QTextEdit()
        self._ai_sp_user_edit.setPlaceholderText("SP Analysis - User prompt override")
        self._ai_sp_user_edit.setMinimumHeight(100)
        sp_layout.addRow("System Prompt:", self._ai_sp_system_edit)
        sp_layout.addRow("User Prompt:", self._ai_sp_user_edit)
        self._prompt_tabs.addTab(sp_tab, "SP Analysis")

        # SP code only tab
        sp_code_tab = QWidget()
        sp_code_layout = QFormLayout(sp_code_tab)
        self._ai_sp_code_system_edit = QTextEdit()
        self._ai_sp_code_system_edit.setPlaceholderText("SP Code Only - System prompt override")
        self._ai_sp_code_system_edit.setMinimumHeight(100)
        self._ai_sp_code_user_edit = QTextEdit()
        self._ai_sp_code_user_edit.setPlaceholderText("SP Code Only - User prompt override")
        self._ai_sp_code_user_edit.setMinimumHeight(100)
        sp_code_layout.addRow("System Prompt:", self._ai_sp_code_system_edit)
        sp_code_layout.addRow("User Prompt:", self._ai_sp_code_user_edit)
        self._prompt_tabs.addTab(sp_code_tab, "SP Code Only")

        # Index recommendation tab
        index_tab = QWidget()
        index_layout = QFormLayout(index_tab)
        self._ai_index_system_edit = QTextEdit()
        self._ai_index_system_edit.setPlaceholderText("Index Recommendation - System prompt override")
        self._ai_index_system_edit.setMinimumHeight(100)
        self._ai_index_user_edit = QTextEdit()
        self._ai_index_user_edit.setPlaceholderText("Index Recommendation - User prompt override")
        self._ai_index_user_edit.setMinimumHeight(100)
        index_layout.addRow("System Prompt:", self._ai_index_system_edit)
        index_layout.addRow("User Prompt:", self._ai_index_user_edit)
        self._prompt_tabs.addTab(index_tab, "Index Recommendation")

        prompt_layout.addWidget(self._prompt_tabs)
        layout.addWidget(prompt_group)

        return widget

    def _reset_prompt_rules_ui(self) -> None:
        """Reset AI prompt rules UI fields to defaults."""
        defaults = Settings().ai.prompt_rules
        self._ai_global_instructions.setPlainText(
            (defaults.get("global_instructions") or "").strip()
        )
        overrides = defaults.get("overrides") or {}

        def _set_override(key: str, system_edit: QTextEdit, user_edit: QTextEdit):
            data = overrides.get(key, {}) or {}
            system_edit.setPlainText((data.get("system") or "").strip())
            user_edit.setPlainText((data.get("user") or "").strip())

        _set_override("query_analysis", self._ai_query_system_edit, self._ai_query_user_edit)
        _set_override("sp_optimization", self._ai_sp_system_edit, self._ai_sp_user_edit)
        _set_override("sp_code_only", self._ai_sp_code_system_edit, self._ai_sp_code_user_edit)
        _set_override("index_recommendation", self._ai_index_system_edit, self._ai_index_user_edit)

    def _create_database_tab(self) -> QWidget:
        """Create database settings tab with connection management"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # Connections management
        conn_group = QGroupBox("Database Connections")
        conn_layout = QVBoxLayout(conn_group)

        # Toolbar
        toolbar = QHBoxLayout()
        add_conn_btn = QPushButton("Add Connection")
        add_conn_btn.clicked.connect(self._add_connection)
        toolbar.addWidget(add_conn_btn)
        toolbar.addStretch()
        conn_layout.addLayout(toolbar)

        # Connections table
        self._conn_table = QTableWidget()
        self._conn_table.setColumnCount(4)
        self._conn_table.setHorizontalHeaderLabels(["Name", "Server", "Auth", "Actions"])
        self._conn_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._conn_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._conn_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._conn_table.setMinimumHeight(320)
        conn_layout.addWidget(self._conn_table)

        layout.addWidget(conn_group)

        # Query + Cache settings (side by side)
        settings_row = QHBoxLayout()
        settings_row.setSpacing(16)

        query_group = QGroupBox("General Query Settings")
        query_layout = QFormLayout(query_group)

        self._query_timeout_spin = QSpinBox()
        self._query_timeout_spin.setRange(1, 600)
        self._query_timeout_spin.setValue(30)
        self._query_timeout_spin.setSuffix(" seconds")
        query_layout.addRow("Query Timeout:", self._query_timeout_spin)

        self._conn_timeout_spin = QSpinBox()
        self._conn_timeout_spin.setRange(1, 120)
        self._conn_timeout_spin.setValue(15)
        self._conn_timeout_spin.setSuffix(" seconds")
        query_layout.addRow("Connection Timeout:", self._conn_timeout_spin)

        settings_row.addWidget(query_group, 1)

        cache_group = QGroupBox("Cache Settings")
        cache_layout = QFormLayout(cache_group)

        self._cache_enabled_check = QCheckBox("Enable query result caching")
        self._cache_enabled_check.setChecked(True)
        cache_layout.addRow(self._cache_enabled_check)

        self._cache_ttl_spin = QSpinBox()
        self._cache_ttl_spin.setRange(60, 86400)
        self._cache_ttl_spin.setValue(300)
        self._cache_ttl_spin.setSuffix(" seconds")
        cache_layout.addRow("Cache TTL:", self._cache_ttl_spin)

        # Cache control buttons
        cache_buttons = QHBoxLayout()

        clear_cache_btn = QPushButton("Clear Cache")
        clear_cache_btn.clicked.connect(self._clear_cache)
        cache_buttons.addWidget(clear_cache_btn)

        cache_info_btn = QPushButton("Cache Info")
        cache_info_btn.clicked.connect(self._show_cache_info)
        cache_buttons.addWidget(cache_info_btn)

        cache_buttons.addStretch()
        cache_layout.addRow("", cache_buttons)

        settings_row.addWidget(cache_group, 1)
        layout.addLayout(settings_row)

        layout.addStretch()
        return widget

    def _add_connection(self):
        """Add a new database connection"""
        dialog = ConnectionEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            profile = dialog.get_profile()
            password = dialog.get_password()
            
            store = get_connection_store()
            store.add(profile)
            
            if password:
                get_credential_store().set_password(profile.id, password)
            
            self._refresh_conn_table()
            logger.info(f"Connection added: {profile.name}")

    def _edit_connection(self, profile_id: str):
        """Edit an existing database connection"""
        store = get_connection_store()
        profile = store.get(profile_id)
        if not profile:
            return

        dialog = ConnectionEditDialog(profile, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_profile = dialog.get_profile()
            password = dialog.get_password()
            
            store.update(updated_profile)
            
            if password:
                get_credential_store().set_password(profile_id, password)
            
            self._refresh_conn_table()
            logger.info(f"Connection updated: {updated_profile.name}")

    def _delete_connection(self, profile_id: str):
        """Delete a database connection"""
        store = get_connection_store()
        profile = store.get(profile_id)
        if not profile:
            return

        reply = QMessageBox.question(
            self,
            "Delete Connection",
            f"Are you sure you want to delete the connection '{profile.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            store.delete(profile_id)
            get_credential_store().delete_password(profile_id)
            self._refresh_conn_table()
            logger.info(f"Connection deleted: {profile_id}")

    def _refresh_conn_table(self):
        """Refresh the connections table"""
        store = get_connection_store()
        profiles = store.get_all()
        conn_mgr = get_connection_manager()
        active_id = conn_mgr.active_connection.profile.id if conn_mgr.active_connection else None
        
        self._conn_table.setRowCount(len(profiles))
        for i, profile in enumerate(profiles):
            is_active = profile.id == active_id
            
            # Name with indicator if active
            name_text = f"● {profile.name}" if is_active else profile.name
            name_item = QTableWidgetItem(name_text)
            if is_active:
                name_item.setFont(QFont("", -1, QFont.Weight.Bold))
                name_item.setForeground(Qt.GlobalColor.green)
            self._conn_table.setItem(i, 0, name_item)
            
            self._conn_table.setItem(i, 1, QTableWidgetItem(profile.server))
            self._conn_table.setItem(i, 2, QTableWidgetItem(profile.auth_method.value))
            
            # Actions buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            actions_layout.setSpacing(4)
            
            # Connect/Disconnect Button
            if is_active:
                conn_btn = QPushButton("Disconnect")
                conn_btn.setStyleSheet("background-color: #3d3d3d; color: white;")
                conn_btn.clicked.connect(lambda checked, pid=profile.id: self._disconnect_from_database(pid))
            else:
                conn_btn = QPushButton("Connect")
                conn_btn.setStyleSheet("background-color: #2e7d32; color: white; font-weight: bold;")
                conn_btn.clicked.connect(lambda checked, pid=profile.id: self._connect_to_database(pid))
            conn_btn.setFixedWidth(80)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedWidth(50)
            edit_btn.clicked.connect(lambda checked, pid=profile.id: self._edit_connection(pid))
            
            delete_btn = QPushButton("Delete")
            delete_btn.setFixedWidth(60)
            delete_btn.setObjectName("dangerButton")
            delete_btn.clicked.connect(lambda checked, pid=profile.id: self._delete_connection(pid))
            
            actions_layout.addWidget(conn_btn)
            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(delete_btn)
            actions_layout.addStretch()
            
            self._conn_table.setCellWidget(i, 3, actions_widget)

    def _connect_to_database(self, profile_id: str):
        """Connect to a specific database profile"""
        store = get_connection_store()
        profile = store.get(profile_id)
        if not profile:
            return

        try:
            conn_mgr = get_connection_manager()
            # If already connected to something else, disconnect first
            if conn_mgr.active_connection:
                conn_mgr.disconnect_all()
            
            # Connect
            conn_mgr.connect(profile)
            self._refresh_conn_table()
            
            # Notify user
            QMessageBox.information(self, "Connected", f"Successfully connected to {profile.name}")
            
            # Update settings to remember last connection
            update_settings(last_connection_id=profile_id)
            
        except Exception as e:
            logger.error(f"Failed to connect to {profile.name}: {e}")
            QMessageBox.critical(self, "Connection Failed", f"Could not connect to {profile.name}:\n{str(e)}")

    def _disconnect_from_database(self, profile_id: str):
        """Disconnect from database"""
        get_connection_manager().disconnect_all()
        self._refresh_conn_table()
        logger.info(f"Disconnected from database profile: {profile_id}")

    def _create_appearance_tab(self) -> QWidget:
        """Create appearance settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        # Theme group
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)

        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Dark", Theme.DARK.value)
        self._theme_combo.addItem("Light", Theme.LIGHT.value)
        self._theme_combo.addItem("System", Theme.SYSTEM.value)
        theme_layout.addRow("Theme:", self._theme_combo)

        layout.addWidget(theme_group)

        # Font group
        font_group = QGroupBox("Fonts")
        font_layout = QFormLayout(font_group)

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(10, 24)
        self._font_size_spin.setValue(13)
        self._font_size_spin.setSuffix(" px")
        font_layout.addRow("UI Font Size:", self._font_size_spin)

        self._code_font_size_spin = QSpinBox()
        self._code_font_size_spin.setRange(10, 24)
        self._code_font_size_spin.setValue(12)
        self._code_font_size_spin.setSuffix(" px")
        font_layout.addRow("Code Font Size:", self._code_font_size_spin)

        self._line_numbers_check = QCheckBox("Show line numbers in code editor")
        self._line_numbers_check.setChecked(True)
        font_layout.addRow(self._line_numbers_check)

        layout.addWidget(font_group)

        layout.addStretch()
        return widget

    def _add_provider(self):
        """Add a new LLM provider"""
        provider_type = self._add_provider_combo.currentData()
        provider_id = f"provider_{self._provider_counter}"
        self._provider_counter += 1

        # Create default config
        config = {
            "id": provider_id,
            "type": provider_type,
            "name": f"{provider_type.title()} Provider {self._provider_counter - 1}",
        }

        # Add provider-specific defaults
        if provider_type == LLMProvider.OLLAMA.value:
            config.update({"host": "http://localhost:11434", "model": "codellama"})
        elif provider_type == LLMProvider.OPENAI.value:
            config.update({"api_key": "", "model": "gpt-4o"})
        elif provider_type == LLMProvider.ANTHROPIC.value:
            config.update({"api_key": "", "model": "claude-3-5-sonnet-20241022"})
        elif provider_type == LLMProvider.AZURE_OPENAI.value:
            config.update({"api_key": "", "endpoint": "", "deployment": ""})
        elif provider_type == LLMProvider.DEEPSEEK.value:
            config.update({"api_key": "", "model": "deepseek-chat"})

        # Create provider widget
        is_first = len(self._llm_providers) == 0
        provider_widget = LLMProviderWidget(provider_id, config, is_default=is_first, parent=self)
        provider_widget.test_requested.connect(self._test_provider)
        provider_widget.remove_requested.connect(self._remove_provider)
        provider_widget.set_default_requested.connect(self._set_default_provider)

        # Add to layout (before the stretch)
        self._providers_layout.insertWidget(self._providers_layout.count() - 1, provider_widget)

        self._llm_providers[provider_id] = provider_widget
        
        if is_first:
            self._active_provider_id = provider_id

        # Force UI update
        self._providers_widget.adjustSize()

        logger.info(f"Added {provider_type} provider: {provider_id}")

    def _set_default_provider(self, provider_id: str):
        """Set a provider as default"""
        self._active_provider_id = provider_id
        for pid, widget in self._llm_providers.items():
            widget.set_is_default(pid == provider_id)
        
        logger.info(f"Set default provider to: {provider_id}")

    def _remove_provider(self, provider_id: str):
        """Remove LLM provider"""
        if provider_id in self._llm_providers:
            widget = self._llm_providers[provider_id]
            self._providers_layout.removeWidget(widget)
            widget.deleteLater()
            del self._llm_providers[provider_id]

            logger.info(f"Removed provider: {provider_id}")

    def _test_provider(self, provider_id: str):
        """Test specific provider connection"""
        if self._test_worker and self._test_worker.isRunning():
            return

        if provider_id not in self._llm_providers:
            return

        provider_widget = self._llm_providers[provider_id]
        config = provider_widget.get_config()

        # Start test worker
        self._test_worker = LLMTestWorker(config)
        self._test_worker.test_completed.connect(self._on_test_completed)
        self._test_worker.start()

        # Disable test button temporarily
        provider_widget.test_btn.setEnabled(False)
        provider_widget.test_btn.setText("Testing...")

        logger.info(f"Testing provider {provider_id}: {config}")

    @pyqtSlot(str, bool, str)
    def _on_test_completed(self, provider_id: str, success: bool, message: str):
        """Handle provider test completion"""
        if provider_id in self._llm_providers:
            provider_widget = self._llm_providers[provider_id]
            provider_widget.test_btn.setEnabled(True)
            provider_widget.test_btn.setText("Test")
            provider_widget.show_test_result(success, message)

        logger.info(f"Provider {provider_id} test completed: {success} - {message}")

    def _load_settings(self) -> None:
        """Load current settings into UI"""
        settings = get_settings()

        # General
        idx = self._language_combo.findData(settings.ui.language.value)
        if idx >= 0:
            self._language_combo.setCurrentIndex(idx)

        # Database
        self._query_timeout_spin.setValue(settings.database.query_timeout)
        self._conn_timeout_spin.setValue(settings.database.connection_timeout)
        self._cache_enabled_check.setChecked(settings.cache.enabled)
        self._cache_ttl_spin.setValue(settings.cache.default_ttl)

        # Appearance
        idx = self._theme_combo.findData(settings.ui.theme.value)
        if idx >= 0:
            self._theme_combo.setCurrentIndex(idx)
        self._font_size_spin.setValue(settings.ui.font_size)
        self._code_font_size_spin.setValue(settings.ui.code_font_size)
        self._line_numbers_check.setChecked(getattr(settings.ui, "show_line_numbers", True))

        # Load LLM providers
        self._load_llm_providers()

        # Load AI prompt rules
        prompt_rules = getattr(settings.ai, "prompt_rules", None) or {}
        self._ai_global_instructions.setPlainText(
            (prompt_rules.get("global_instructions") or "").strip()
        )
        overrides = prompt_rules.get("overrides") or {}

        def _set_override(key: str, system_edit: QTextEdit, user_edit: QTextEdit):
            data = overrides.get(key, {}) or {}
            system_edit.setPlainText((data.get("system") or "").strip())
            user_edit.setPlainText((data.get("user") or "").strip())

        _set_override("query_analysis", self._ai_query_system_edit, self._ai_query_user_edit)
        _set_override("sp_optimization", self._ai_sp_system_edit, self._ai_sp_user_edit)
        _set_override("sp_code_only", self._ai_sp_code_system_edit, self._ai_sp_code_user_edit)
        _set_override("index_recommendation", self._ai_index_system_edit, self._ai_index_user_edit)

    def _load_llm_providers(self):
        """Load saved LLM providers"""
        settings = get_settings()
        self._active_provider_id = settings.ai.active_provider_id

        # Clear existing widgets if any
        for provider_id in list(self._llm_providers.keys()):
            self._remove_provider(provider_id)

        # Load from settings
        if settings.ai.providers:
            for provider_id, config in settings.ai.providers.items():
                is_default = (provider_id == self._active_provider_id)
                provider_widget = LLMProviderWidget(provider_id, config, is_default=is_default, parent=self)
                provider_widget.test_requested.connect(self._test_provider)
                provider_widget.remove_requested.connect(self._remove_provider)
                provider_widget.set_default_requested.connect(self._set_default_provider)

                self._providers_layout.insertWidget(
                    self._providers_layout.count() - 1, provider_widget
                )

                self._llm_providers[provider_id] = provider_widget
                
                # Update counter to avoid ID conflicts
                if provider_id.startswith("provider_"):
                    try:
                        num = int(provider_id.split("_")[1])
                        self._provider_counter = max(self._provider_counter, num + 1)
                    except (ValueError, IndexError):
                        pass
        else:
            # Default Ollama provider if none exist
            default_config = {
                "id": "default_ollama",
                "type": LLMProvider.OLLAMA.value,
                "name": "Default Ollama",
                "host": "http://localhost:11434",
                "model": "codellama",
            }

            self._active_provider_id = "default_ollama"
            provider_widget = LLMProviderWidget("default_ollama", default_config, is_default=True, parent=self)
            provider_widget.test_requested.connect(self._test_provider)
            provider_widget.remove_requested.connect(self._remove_provider)
            provider_widget.set_default_requested.connect(self._set_default_provider)

            self._providers_layout.insertWidget(self._providers_layout.count() - 1, provider_widget)

            self._llm_providers["default_ollama"] = provider_widget

    def _save_settings(self) -> None:
        """Save settings"""
        try:
            # Collect LLM provider configurations
            llm_providers = {}
            for provider_id, widget in self._llm_providers.items():
                llm_providers[provider_id] = widget.get_config()

            update_settings(
                ui={
                    "theme": Theme(self._theme_combo.currentData()),
                    "language": Language(self._language_combo.currentData()),
                    "font_size": self._font_size_spin.value(),
                    "code_font_size": self._code_font_size_spin.value(),
                    "show_line_numbers": self._line_numbers_check.isChecked(),
                },
                database={
                    "query_timeout": self._query_timeout_spin.value(),
                    "connection_timeout": self._conn_timeout_spin.value(),
                },
                cache={
                    "enabled": self._cache_enabled_check.isChecked(),
                    "default_ttl": self._cache_ttl_spin.value(),
                },
                ai={
                    "providers": llm_providers,
                    "active_provider_id": self._active_provider_id,
                    "prompt_rules": {
                        "global_instructions": self._ai_global_instructions.toPlainText().strip(),
                        "overrides": {
                            "query_analysis": {
                                "system": self._ai_query_system_edit.toPlainText().strip(),
                                "user": self._ai_query_user_edit.toPlainText().strip(),
                            },
                            "sp_optimization": {
                                "system": self._ai_sp_system_edit.toPlainText().strip(),
                                "user": self._ai_sp_user_edit.toPlainText().strip(),
                            },
                            "sp_code_only": {
                                "system": self._ai_sp_code_system_edit.toPlainText().strip(),
                                "user": self._ai_sp_code_user_edit.toPlainText().strip(),
                            },
                            "index_recommendation": {
                                "system": self._ai_index_system_edit.toPlainText().strip(),
                                "user": self._ai_index_user_edit.toPlainText().strip(),
                            },
                        },
                    },
                },
            )

            logger.info("Settings saved successfully")
            self.settings_changed.emit()

            # Show success message
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("Settings Saved")
            msg.setText("Settings have been saved successfully!")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

            # Show error message
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Save Error")
            msg.setText(f"Failed to save settings:\n{str(e)}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

    def _reset_settings(self) -> None:
        """Reset settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from app.core.config import reset_settings

                reset_settings()

                # Clear all LLM providers and reload
                for provider_id in list(self._llm_providers.keys()):
                    self._remove_provider(provider_id)

                self._load_settings()
                logger.info("Settings reset to defaults")
                self.settings_changed.emit()

                # Show success message
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Settings Reset")
                msg.setText("Settings have been reset to defaults!")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()

            except Exception as e:
                logger.error(f"Failed to reset settings: {e}")

                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle("Reset Error")
                msg.setText(f"Failed to reset settings:\n{str(e)}")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()


    def _clear_cache(self) -> None:
        """Clear application cache"""
        try:
            settings = get_settings()
            cache_dir = settings.app_dir / "cache"

            if cache_dir.exists():
                import shutil

                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)

                logger.info("Cache cleared successfully")

                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Cache Cleared")
                msg.setText("Application cache has been cleared successfully!")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()
            else:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Cache Info")
                msg.setText("No cache found to clear.")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("Clear Cache Error")
            msg.setText(f"Failed to clear cache:\n{str(e)}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

    def _show_cache_info(self) -> None:
        """Show cache information"""
        try:
            settings = get_settings()
            cache_dir = settings.app_dir / "cache"

            if cache_dir.exists():
                # Calculate cache size
                total_size = 0
                file_count = 0
                for file_path in cache_dir.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        file_count += 1

                size_mb = total_size / (1024 * 1024)

                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Cache Information")
                msg.setText(
                    f"Cache Directory: {cache_dir}\nFiles: {file_count}\nSize: {size_mb:.2f} MB"
                )
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()
            else:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Cache Information")
                msg.setText("No cache directory found.")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()

        except Exception as e:
            logger.error(f"Failed to get cache info: {e}")

    def _show_logs(self) -> None:
        """Show application logs"""
        try:
            settings = get_settings()
            log_file = settings.app_dir / "logs" / "app.log"

            if log_file.exists():
                # Read last 100 lines
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    recent_lines = lines[-100:]  # Last 100 lines

                # Create a dialog to show logs
                dialog = QDialog(self)
                dialog.setWindowTitle("Application Logs")
                dialog.setModal(True)
                dialog.resize(800, 600)

                layout = QVBoxLayout(dialog)

                log_text = QTextEdit()
                log_text.setPlainText("".join(recent_lines))
                log_text.setReadOnly(True)
                log_text.setFont(QFont("Consolas", 10))
                layout.addWidget(log_text)

                close_btn = QPushButton("Close")
                close_btn.clicked.connect(dialog.close)

                btn_layout = QHBoxLayout()
                btn_layout.addStretch()
                btn_layout.addWidget(close_btn)
                layout.addLayout(btn_layout)

                dialog.exec()

            else:
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Logs")
                msg.setText("No log file found.")
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg.exec()

        except Exception as e:
            logger.error(f"Failed to show logs: {e}")

    def on_show(self) -> None:
        """Load settings when view is shown"""
        if not self._is_initialized:
            return
        self._load_settings()
        self._refresh_conn_table()
