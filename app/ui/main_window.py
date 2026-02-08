"""
Main application window - Modern Enterprise Design
"""

from typing import Optional, Dict, Type

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QStatusBar, QLabel, QMessageBox,
    QFrame, QComboBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QCloseEvent, QFont

from app.core.constants import (
    APP_NAME, 
    DEFAULT_WINDOW_WIDTH, 
    DEFAULT_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
)
from app.core.config import get_settings, update_settings
from app.core.logger import get_logger
from app.database.connection import get_connection_manager
from app.ui.theme import ThemeManager, apply_theme, Colors, Theme as ThemeStyles
from app.ui.components.sidebar import Sidebar, DarkSidebar
from app.ui.views.base_view import BaseView
from app.ui.views.chat_view import ChatView
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.settings_view import SettingsView
from app.ui.views.query_stats_view import QueryStatsView
from app.ui.views.index_advisor_view import IndexAdvisorView
from app.ui.views.security_view import SecurityView
from app.ui.views.sp_explorer_view import ObjectExplorerView
from app.ui.views.jobs_view import JobsView
from app.ui.views.wait_stats_view import WaitStatsView
from app.ui.views.blocking_view import BlockingView

logger = get_logger('ui.main')


# ---------------------------------------------------------------------
# INFO BAR - Bottom status bar with modern design (GUI-05 Style)
# ---------------------------------------------------------------------
class InfoBar(QFrame):
    """Modern bottom info bar with connection combos and model status - Light theme"""
    
    # Signals
    server_changed = pyqtSignal(str)  # profile_id
    database_changed = pyqtSignal(str)  # database_name
    model_changed = pyqtSignal(str)  # provider_id
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("InfoBar")
        self.setFixedHeight(44)
        self._current_profile_id: Optional[str] = None
        self._is_loading = False  # Prevent recursive signals
        
        # GUI-05 style - light background
        self.setStyleSheet(f"""
            QFrame#InfoBar {{
                background-color: {Colors.SURFACE};
                border-top: 1px solid {Colors.BORDER};
            }}
        """)
        self._build_ui()
        self._load_profiles()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(8)

        # Status indicator container
        status_container = QWidget()
        status_container.setStyleSheet("background: transparent;")
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)

        # Status dot
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px; background: transparent;")
        status_layout.addWidget(self._status_dot)

        # Status text
        self._status_text = QLabel("Disconnected")
        self._status_text.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        self._status_text.setFont(QFont("Segoe UI", 10))
        status_layout.addWidget(self._status_text)

        # Separator
        sep1 = QLabel("•")
        sep1.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; background: transparent;")
        status_layout.addWidget(sep1)

        # Server label
        self._server_label = QLabel("Server:")
        self._server_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        status_layout.addWidget(self._server_label)

        # Server ComboBox
        self._server_combo = QComboBox()
        self._server_combo.setMinimumWidth(180)
        self._server_combo.setMaximumWidth(250)
        self._server_combo.setStyleSheet(self._combo_style())
        self._server_combo.currentIndexChanged.connect(self._on_server_changed)
        status_layout.addWidget(self._server_combo)

        # Separator
        sep2 = QLabel("•")
        sep2.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; background: transparent;")
        status_layout.addWidget(sep2)

        # Database label
        self._db_label = QLabel("Database:")
        self._db_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        status_layout.addWidget(self._db_label)

        # Database ComboBox
        self._database_combo = QComboBox()
        self._database_combo.setMinimumWidth(150)
        self._database_combo.setMaximumWidth(200)
        self._database_combo.setStyleSheet(self._combo_style())
        self._database_combo.currentIndexChanged.connect(self._on_database_changed)
        status_layout.addWidget(self._database_combo)

        layout.addWidget(status_container)
        layout.addStretch()

        # Separator
        sep3 = QLabel("•")
        sep3.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; background: transparent;")
        status_layout.addWidget(sep3)

        # Version label
        self._version_label = QLabel("Version:")
        self._version_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        status_layout.addWidget(self._version_label)

        # Version value (short)
        self._version_value = QLabel("-")
        self._version_value.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; background: transparent;")
        self._version_value.setToolTip("SQL Server version")
        status_layout.addWidget(self._version_value)

        # Right side - AI Model selector
        ai_container = QWidget()
        ai_container.setStyleSheet("background: transparent;")
        ai_layout = QHBoxLayout(ai_container)
        ai_layout.setContentsMargins(0, 0, 0, 0)
        ai_layout.setSpacing(8)
        
        # AI Model label
        self._ai_label = QLabel("🤖 AI Model:")
        self._ai_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;")
        ai_layout.addWidget(self._ai_label)
        
        # AI Model ComboBox
        self._ai_model_combo = QComboBox()
        self._ai_model_combo.setMinimumWidth(180)
        self._ai_model_combo.setMaximumWidth(250)
        self._ai_model_combo.setStyleSheet(self._combo_style())
        self._ai_model_combo.currentIndexChanged.connect(self._on_ai_model_changed)
        ai_layout.addWidget(self._ai_model_combo)
        
        # Status indicator
        self._ai_status = QLabel("●")
        self._ai_status.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 10px; background: transparent;")
        self._ai_status.setToolTip("Ready")
        ai_layout.addWidget(self._ai_status)
        
        layout.addWidget(ai_container)
        
        # Load AI models
        self._load_ai_models()

    def _combo_style(self) -> str:
        """ComboBox style for light background - GUI-05 style"""
        return ThemeStyles.combobox_style()

    def _load_profiles(self) -> None:
        """Load connection profiles into server combo"""
        from app.services.connection_store import get_connection_store
        
        self._is_loading = True
        self._server_combo.clear()
        self._server_combo.addItem("-- Select Server --", None)
        
        store = get_connection_store()
        profiles = store.get_all()
        
        for profile in profiles:
            display = f"{profile.server}" if not profile.name else f"{profile.name} ({profile.server})"
            self._server_combo.addItem(display, profile.id)
        
        self._is_loading = False

    def _find_profile_index(self, profile_id: str) -> int:
        for i in range(self._server_combo.count()):
            if self._server_combo.itemData(i) == profile_id:
                return i
        return -1

    def _on_server_changed(self, index: int) -> None:
        """Handle server selection change"""
        if self._is_loading or index < 0:
            return
        
        profile_id = self._server_combo.itemData(index)
        if profile_id is None:
            self._database_combo.clear()
            return
        
        self._current_profile_id = profile_id
        self._load_databases_for_profile(profile_id)
        self.server_changed.emit(profile_id)

    def _load_databases_for_profile(self, profile_id: str) -> None:
        """Load databases for selected server"""
        from app.services.connection_store import get_connection_store
        
        self._is_loading = True
        self._database_combo.clear()
        
        store = get_connection_store()
        profile = store.get(profile_id)
        
        if not profile:
            self._is_loading = False
            return
        
        # Try to get databases from existing connection or create temp connection
        conn_mgr = get_connection_manager()
        conn = conn_mgr.get_connection(profile_id)
        
        if conn and conn.is_connected:
            self._fetch_and_populate_databases(conn, profile.database)
        else:
            # Just show the profile's default database
            self._database_combo.addItem(profile.database, profile.database)
        
        self._is_loading = False

    def _fetch_and_populate_databases(self, conn, current_db: str = "") -> None:
        """Fetch database list from connection"""
        try:
            query = "SELECT name FROM sys.databases WHERE state = 0 AND name NOT IN ('model', 'tempdb') ORDER BY name"
            results = conn.execute_query(query)
            
            current_index = 0
            for i, row in enumerate(results):
                db_name = row.get('name', row.get('NAME', ''))
                if db_name:
                    self._database_combo.addItem(db_name, db_name)
                    if db_name == current_db:
                        current_index = i
            
            if current_index >= 0:
                self._database_combo.setCurrentIndex(current_index)
        except Exception as e:
            logger.warning(f"Failed to fetch databases: {e}")
            if current_db:
                self._database_combo.addItem(current_db, current_db)

    def _on_database_changed(self, index: int) -> None:
        """Handle database selection change"""
        if self._is_loading or index < 0:
            return
        
        db_name = self._database_combo.itemData(index)
        if db_name:
            self.database_changed.emit(db_name)

    def refresh_profiles(self) -> None:
        """Refresh the profiles list"""
        current_id = self._current_profile_id
        self._load_profiles()
        if current_id:
            index = self._find_profile_index(current_id)
            if index >= 0:
                self._is_loading = True
                self._server_combo.setCurrentIndex(index)
                self._is_loading = False
                self._current_profile_id = current_id
                self._load_databases_for_profile(current_id)
            else:
                self._current_profile_id = None
                self._database_combo.clear()

    def set_connected(
        self,
        server: str,
        database: str,
        product_version: str = "",
        major_version: int = 0,
        edition: str = ""
    ) -> None:
        """Update to show connected state"""
        self._status_dot.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 10px; background: transparent;")
        self._status_text.setText("Connected")
        self._update_version_display(product_version, major_version, edition)
        
        # Select the matching profile in combo
        self._is_loading = True
        for i in range(self._server_combo.count()):
            profile_id = self._server_combo.itemData(i)
            if profile_id:
                from app.services.connection_store import get_connection_store
                store = get_connection_store()
                profile = store.get(profile_id)
                if profile and profile.server == server:
                    self._server_combo.setCurrentIndex(i)
                    self._current_profile_id = profile_id
                    
                    # Load databases and select current
                    conn_mgr = get_connection_manager()
                    conn = conn_mgr.get_connection(profile_id)
                    if conn and conn.is_connected:
                        self._database_combo.clear()
                        self._fetch_and_populate_databases(conn, database)
                    break
        self._is_loading = False

    def set_disconnected(self) -> None:
        """Update to show disconnected state"""
        self._status_dot.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px; background: transparent;")
        self._status_text.setText("Disconnected")
        self._version_value.setText("-")
        self._version_value.setToolTip("SQL Server version")
        self._is_loading = True
        self._server_combo.setCurrentIndex(0)
        self._database_combo.clear()
        self._is_loading = False

    def update_strings(self) -> None:
        """Update UI strings for i18n support"""
        # This method can be called when language changes
        pass

    def _update_version_display(self, product_version: str, major_version: int, edition: str) -> None:
        short_version = self._format_short_version(product_version, major_version)
        tooltip_parts = []
        if product_version:
            tooltip_parts.append(f"Product: {product_version}")
        if edition:
            tooltip_parts.append(f"Edition: {edition}")
        tooltip = " | ".join(tooltip_parts) if tooltip_parts else "SQL Server version"
        self._version_value.setText(short_version or "-")
        self._version_value.setToolTip(tooltip)

    @staticmethod
    def _format_short_version(product_version: str, major_version: int) -> str:
        if major_version:
            from app.core.constants import SQL_SERVER_VERSIONS
            friendly = SQL_SERVER_VERSIONS.get(major_version, f"v{major_version}")
            year = friendly.replace("SQL Server ", "") if friendly.startswith("SQL Server ") else friendly
            if product_version:
                major_str = product_version.split(".")[0]
                return f"{year} ({major_str}.x)"
            return str(year)
        if product_version:
            major_str = product_version.split(".")[0]
            return f"v{major_str}.x"
        return ""

    def _load_ai_models(self) -> None:
        """Load AI models from settings"""
        from app.core.config import get_settings
        
        self._is_loading = True
        self._ai_model_combo.clear()
        
        settings = get_settings()
        providers = settings.ai.providers
        active_id = settings.ai.active_provider_id
        
        if not providers:
            # Default Ollama provider
            self._ai_model_combo.addItem(f"🦙 Ollama ({settings.ai.model})", "default_ollama")
        else:
            current_index = 0
            for i, (provider_id, config) in enumerate(providers.items()):
                provider_type = config.get("type", "ollama")
                model_name = config.get("model", "unknown")
                
                # Icon based on type
                if provider_type == "ollama":
                    icon = "🦙"
                elif provider_type == "openai":
                    icon = "🤖"
                elif provider_type == "deepseek":
                    icon = "🔮"
                else:
                    icon = "⚡"
                
                display_name = f"{icon} {provider_type.title()} ({model_name})"
                self._ai_model_combo.addItem(display_name, provider_id)
                
                if provider_id == active_id:
                    current_index = i
            
            self._ai_model_combo.setCurrentIndex(current_index)
        
        self._is_loading = False
    
    def _on_ai_model_changed(self, index: int) -> None:
        """Handle AI model selection change"""
        if self._is_loading or index < 0:
            return
        
        provider_id = self._ai_model_combo.itemData(index)
        if provider_id:
            self.model_changed.emit(provider_id)
            self._update_ai_status("Ready")
    
    def _update_ai_status(self, status: str) -> None:
        """Update AI status indicator"""
        if status == "Ready":
            self._ai_status.setStyleSheet("color: #22c55e; font-size: 10px; background: transparent;")
            self._ai_status.setToolTip("Ready")
        elif status == "Loading":
            self._ai_status.setStyleSheet("color: #f97316; font-size: 10px; background: transparent;")
            self._ai_status.setToolTip("Loading...")
        else:
            self._ai_status.setStyleSheet("color: #ef4444; font-size: 10px; background: transparent;")
            self._ai_status.setToolTip(status)
    
    def refresh_ai_models(self) -> None:
        """Refresh AI models list (call after settings change)"""
        self._load_ai_models()

    def set_model_status(self, model: str, status: str = "Ready") -> None:
        """Update model status display - now refreshes combo"""
        self._load_ai_models()
        self._update_ai_status(status)


class MainWindow(QMainWindow):
    """
    Main application window
    
    Contains:
    - Sidebar navigation
    - Stacked views for different screens
    - Status bar
    """
    
    def __init__(self):
        super().__init__()
        
        self._views: Dict[str, BaseView] = {}
        self._current_view_id: Optional[str] = None
        
        self._setup_window()
        self._setup_ui()
        self._setup_views()
        self._connect_signals()
        self._apply_settings()
        
        # Initial status update
        active_conn = get_connection_manager().active_connection
        if active_conn:
            self.update_connection_status(True, active_conn.profile.server, active_conn.profile.database)
        
        # Show first enabled view by default
        start_view = self._get_first_enabled_view_id()
        self._navigate_to(start_view or "settings")
        
        logger.info("Main window initialized")
    
    def _setup_window(self) -> None:
        """Setup window properties"""
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        
        # Load window size from settings
        settings = get_settings()
        if settings.ui.window_maximized:
            self.showMaximized()
        else:
            self.resize(settings.ui.window_width, settings.ui.window_height)
        
        # Center on screen
        screen = self.screen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.width()) // 2
            y = (screen_geo.height() - self.height()) // 2
            self.move(x, y)
    
    def _setup_ui(self) -> None:
        """Setup main UI layout with modern enterprise design"""
        # Central widget
        central_widget = QWidget()
        central_widget.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        self.setCentralWidget(central_widget)
        
        # Root vertical layout
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        
        # Middle section: sidebar + content
        middle_widget = QWidget()
        middle_layout = QHBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        
        # Dark Sidebar
        self._sidebar = DarkSidebar()
        middle_layout.addWidget(self._sidebar)
        
        # Content area
        content_widget = QWidget()
        content_widget.setObjectName("contentArea")
        content_widget.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Stacked widget for views
        self._view_stack = QStackedWidget()
        content_layout.addWidget(self._view_stack)
        
        middle_layout.addWidget(content_widget, 1)
        root_layout.addWidget(middle_widget, 1)
        
        # Bottom info bar
        self._info_bar = InfoBar()
        root_layout.addWidget(self._info_bar)
    
    def _setup_status_bar(self) -> None:
        """Setup status bar - now handled by InfoBar"""
        # InfoBar replaces the traditional status bar
        pass
    
    def _setup_views(self) -> None:
        """Create and register views"""
        # Register views
        view_classes: Dict[str, Type[BaseView]] = {
            "chat": ChatView,
            "dashboard": DashboardView,
            "query_stats": QueryStatsView,
            "index_advisor": IndexAdvisorView,
            "security": SecurityView,
            "sp_explorer": ObjectExplorerView,
            "wait_stats": WaitStatsView,
            "blocking": BlockingView,
            "jobs": JobsView,
            "settings": SettingsView,
        }
        
        for view_id, view_class in view_classes.items():
            view = view_class()
            self._register_view(view_id, view)
    
    def _register_view(self, view_id: str, view: BaseView) -> None:
        """Register a view with the stack"""
        self._views[view_id] = view
        self._view_stack.addWidget(view)
        logger.debug(f"Registered view: {view_id}")
    
    def _connect_signals(self) -> None:
        """Connect signals and slots"""
        # Sidebar navigation
        self._sidebar.navigation_changed.connect(self._navigate_to)
        
        # Settings changes
        if "settings" in self._views:
            self._views["settings"].settings_changed.connect(self._on_settings_changed)
            self._views["settings"].connections_changed.connect(self._on_connections_changed)
        
        # Chat messages
        if "chat" in self._views:
            self._views["chat"].message_sent.connect(self._on_chat_message)

        # Dashboard quick actions
        if "dashboard" in self._views:
            self._views["dashboard"].action_requested.connect(self._navigate_to)

        # Connection changes
        get_connection_manager().connection_changed.connect(self.update_connection_status)
        
        # InfoBar server/database quick switch
        self._info_bar.server_changed.connect(self._on_infobar_server_changed)
        self._info_bar.database_changed.connect(self._on_infobar_database_changed)
        self._info_bar.model_changed.connect(self._on_infobar_model_changed)
    
    def _apply_settings(self) -> None:
        """Apply settings (theme, etc.)"""
        settings = get_settings()
        apply_theme(settings.ui.theme)
        
        # Reload LLM providers so the default provider is ready at startup
        from app.ai.llm_client import get_llm_client
        get_llm_client().reload_providers()
        
        # Update info bar model status
        self._info_bar.set_model_status(settings.ai.model)
        self._apply_navigation_visibility()

    def _get_navigation_visibility(self) -> Dict[str, bool]:
        """Return merged navigation visibility settings with safe defaults."""
        defaults = {
            item.id: True
            for item in (DarkSidebar.MAIN_NAV_ITEMS + DarkSidebar.TOOLS_NAV_ITEMS)
        }
        saved_map = getattr(get_settings().ui, "navigation_visibility", {}) or {}
        for menu_id in defaults.keys():
            if menu_id in saved_map:
                defaults[menu_id] = bool(saved_map.get(menu_id))
        return defaults

    def _get_first_enabled_view_id(self, visibility: Optional[Dict[str, bool]] = None) -> Optional[str]:
        """Return first enabled view id according to sidebar order."""
        visibility = visibility or self._get_navigation_visibility()
        ordered_ids = [item.id for item in (DarkSidebar.MAIN_NAV_ITEMS + DarkSidebar.TOOLS_NAV_ITEMS)]
        for view_id in ordered_ids:
            if visibility.get(view_id, True) and view_id in self._views:
                return view_id
        return "settings" if "settings" in self._views else None

    def _apply_navigation_visibility(self) -> None:
        """Apply menu visibility to sidebar and keep current view valid."""
        visibility = self._get_navigation_visibility()
        self._sidebar.set_menu_visibility(visibility)

        if self._current_view_id and self._current_view_id != "settings":
            if not visibility.get(self._current_view_id, True):
                fallback = self._get_first_enabled_view_id(visibility)
                if fallback and fallback != self._current_view_id:
                    self._navigate_to(fallback)
    
    def _navigate_to(self, view_id: str) -> None:
        """Navigate to a view"""
        if view_id != "settings":
            visibility = self._get_navigation_visibility()
            if not visibility.get(view_id, True):
                logger.info(f"Navigation blocked for disabled view: {view_id}")
                return

        if view_id not in self._views:
            logger.warning(f"View not found: {view_id}")
            return
        
        # Hide current view
        if self._current_view_id and self._current_view_id in self._views:
            self._views[self._current_view_id].on_hide()
        
        # Get view
        view = self._views[view_id]
        
        # Initialize if needed
        view.initialize()
        
        # Switch to view
        self._view_stack.setCurrentWidget(view)
        self._current_view_id = view_id
        
        # Update sidebar
        self._sidebar.set_current(view_id)
        
        # Notify view
        view.on_show()
        
        logger.debug(f"Navigated to: {view_id}")
    
    def _on_settings_changed(self) -> None:
        """Handle settings change"""
        self._apply_settings()
        logger.info("Settings applied")

    def _on_connections_changed(self) -> None:
        """Refresh server list when connection profiles change"""
        self._info_bar.refresh_profiles()
        logger.info("Connection profiles refreshed in info bar")
    
    def _on_chat_message(self, message: str) -> None:
        """Handle chat message from user"""
        logger.info(f"Chat message received: {message[:50]}...")
        
        chat_view = self._views.get("chat")
        if not chat_view:
            return
        
        # Show loading indicator
        chat_view.add_loading_indicator()
        
        # Process with AI in background thread
        from app.ui.components.chat_worker import ChatWorker
        
        self._chat_worker = ChatWorker(message)
        self._chat_worker.response_ready.connect(self._on_ai_response)
        self._chat_worker.error_occurred.connect(self._on_ai_error)
        self._chat_worker.processing_finished.connect(self._on_ai_finished)
        self._chat_worker.start()
    
    def _on_ai_response(self, response: str) -> None:
        """Handle AI response"""
        chat_view = self._views.get("chat")
        if chat_view:
            chat_view.remove_loading_indicator()
            chat_view.add_ai_response(response)
    
    def _on_ai_error(self, error: str) -> None:
        """Handle AI error"""
        chat_view = self._views.get("chat")
        if chat_view:
            chat_view.remove_loading_indicator()
            chat_view.add_ai_response(f"⚠️ An error occurred: {error}")
    
    def _on_ai_finished(self) -> None:
        """Handle AI processing finished"""
        chat_view = self._views.get("chat")
        if chat_view:
            chat_view.remove_loading_indicator()
    
    def update_connection_status(
        self, 
        connected: bool, 
        server: str = "",
        database: str = ""
    ) -> None:
        """Update connection status display"""
        if connected:
            conn_mgr = get_connection_manager()
            active_conn = conn_mgr.active_connection
            
            if active_conn and active_conn.info:
                info = active_conn.info
                # Update info bar with full details
                self._info_bar.set_connected(
                    server=server,
                    database=database,
                    product_version=info.product_version,
                    major_version=info.major_version,
                    edition=info.edition
                )
            else:
                self._info_bar.set_connected(server=server, database=database)

            self._sidebar.update_connection_status(True, server, database)
            
            # Update dashboard
            if "dashboard" in self._views:
                self._views["dashboard"].update_server_info(server)
        else:
            self._info_bar.set_disconnected()
            self._sidebar.update_connection_status(False)
    
    def _on_infobar_server_changed(self, profile_id: str) -> None:
        """Handle server change from info bar"""
        from app.services.connection_store import get_connection_store
        
        store = get_connection_store()
        profile = store.get(profile_id)
        
        if not profile:
            logger.warning(f"Profile not found: {profile_id}")
            return
        
        conn_mgr = get_connection_manager()
        
        # Check if already connected to this profile
        existing_conn = conn_mgr.get_connection(profile_id)
        if existing_conn and existing_conn.is_connected:
            conn_mgr.set_active(profile_id)
            self.update_connection_status(True, profile.server, profile.database)
            logger.info(f"Switched to existing connection: {profile.server}")
            return
        
        # Create new connection
        try:
            conn_mgr.connect(profile)
            logger.info(f"Connected to server: {profile.server}")
        except Exception as e:
            self.show_error("Connection Error", f"Failed to connect to {profile.server}: {e}")
            logger.error(f"Connection failed: {e}")
    
    def _on_infobar_database_changed(self, database: str) -> None:
        """Handle database change from info bar"""
        conn_mgr = get_connection_manager()
        active_conn = conn_mgr.active_connection
        
        if not active_conn or not active_conn.is_connected:
            logger.warning("No active connection for database change")
            return
        
        try:
            # Change database using USE statement
            active_conn.execute_query(f"USE [{database}]")
            
            # Update profile's database
            active_conn.profile.database = database
            
            # Update UI
            self.update_connection_status(True, active_conn.profile.server, database)
            logger.info(f"Switched to database: {database}")
            
            # Refresh views that depend on database context
            self._refresh_database_dependent_views()
        except Exception as e:
            self.show_error("Database Error", f"Failed to switch to {database}: {e}")
            logger.error(f"Database switch failed: {e}")
    
    def _refresh_database_dependent_views(self) -> None:
        """Refresh views that depend on database context"""
        # Refresh Object Explorer if visible
        if "sp_explorer" in self._views:
            sp_view = self._views["sp_explorer"]
            if hasattr(sp_view, 'refresh'):
                sp_view.refresh()
        
        # Refresh Query Stats if visible
        if "query_stats" in self._views:
            qs_view = self._views["query_stats"]
            if hasattr(qs_view, 'refresh'):
                qs_view.refresh()
    
    def _on_infobar_model_changed(self, provider_id: str) -> None:
        """Handle AI model change from info bar"""
        from app.core.config import update_settings
        
        try:
            # Update active provider in settings
            update_settings(ai={"active_provider_id": provider_id})
            logger.info(f"Changed active AI provider to: {provider_id}")
            
            # Show confirmation (optional, can be removed)
            # self.show_info("AI Model", f"AI model changed to: {provider_id}")
        except Exception as e:
            self.show_error("AI Model Error", f"Failed to change AI model: {e}")
            logger.error(f"AI model change failed: {e}")
    
    def show_error(self, title: str, message: str) -> None:
        """Show error dialog"""
        QMessageBox.critical(self, title, message)
    
    def show_warning(self, title: str, message: str) -> None:
        """Show warning dialog"""
        QMessageBox.warning(self, title, message)
    
    def show_info(self, title: str, message: str) -> None:
        """Show info dialog"""
        QMessageBox.information(self, title, message)
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close"""
        # Save window state
        try:
            update_settings(
                ui={
                    'window_width': self.width(),
                    'window_height': self.height(),
                    'window_maximized': self.isMaximized(),
                    'sidebar_collapsed': self._sidebar.is_collapsed,
                }
            )
        except Exception as e:
            logger.error(f"Failed to save window state: {e}")
        
        logger.info("Application closing")
        event.accept()
