"""
Sidebar Navigation Component - Modern Enterprise Design (GUI-05 Style)
Light theme with Teal accent
"""

from typing import Optional, List, Dict
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFrame, QSpacerItem, QSizePolicy,
    QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor

from app.core.constants import ICONS
from app.ui.theme import Colors


@dataclass
class NavItem:
    """Navigation item data"""
    id: str
    label: str
    icon: str
    tooltip: str = ""


class DarkSidebar(QWidget):
    """
    Modern sidebar navigation with enterprise design - GUI-05 Style
    Light background with Teal accent
    
    Signals:
        navigation_changed: Emitted when nav item selected, passes item id
        page_changed: Emitted when page index changes
    """
    
    navigation_changed = pyqtSignal(str)
    page_changed = pyqtSignal(int)

    # Navigation items - MAIN MENU section
    MAIN_NAV_ITEMS: List[NavItem] = [
        NavItem("chat", "Chat", "💬", "AI Chat Assistant"),
        NavItem("dashboard", "Dashboard", "🏠", "Server Overview"),
        NavItem("sp_explorer", "Object Explorer", "📁", "Browse DB Objects"),
        NavItem("query_stats", "Query Statistics", "📊", "Query Statistics"),
        NavItem("index_advisor", "Index Advisor", "⚡", "Index Recommendations"),
    ]
    
    # Navigation items - TOOLS section
    TOOLS_NAV_ITEMS: List[NavItem] = [
        NavItem("blocking", "Blocking Analysis", "🔒", "Blocking Chain Visualization"),
        NavItem("security", "Security Audit", "🛡️", "Security Analysis"),
        NavItem("jobs", "Scheduled Jobs", "⏱️", "SQL Agent Jobs"),
        NavItem("wait_stats", "Wait Statistics", "📈", "Wait Stats Analysis"),
    ]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        self.setAutoFillBackground(True)
        
        # Set light background - GUI-05 style
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(Colors.SIDEBAR_BG))
        self.setPalette(palette)
        
        self._nav_buttons: dict[str, QPushButton] = {}
        self._current_nav_id: Optional[str] = None
        self._collapsed = False
        self._main_nav_ids = [item.id for item in self.MAIN_NAV_ITEMS]
        self._tools_nav_ids = [item.id for item in self.TOOLS_NAV_ITEMS]
        
        # Store labels for i18n
        self._main_label: Optional[QLabel] = None
        self._tools_label: Optional[QLabel] = None
        
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main sidebar frame
        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("Sidebar")
        sidebar_frame.setStyleSheet(f"""
            QFrame#Sidebar {{
                background-color: {Colors.SIDEBAR_BG};
                border-right: 1px solid {Colors.BORDER};
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # ─── Logo Section ───
        logo_container = QWidget()
        logo_container.setStyleSheet(f"background-color: {Colors.SIDEBAR_BG};")
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(20, 24, 20, 20)
        logo_layout.setSpacing(2)

        # Logo row
        logo_row = QHBoxLayout()
        logo_row.setSpacing(12)

        logo_icon = QLabel("⚡")
        logo_icon.setStyleSheet(f"""
            color: {Colors.PRIMARY};
            font-size: 28px;
            background: transparent;
        """)
        logo_icon.setFont(QFont("Segoe UI", 24))
        logo_row.addWidget(logo_icon)

        logo_text_container = QVBoxLayout()
        logo_text_container.setSpacing(0)

        self._logo_text = QLabel("DB Performance")
        self._logo_text.setObjectName("Logo")
        self._logo_text.setStyleSheet(f"""
            color: {Colors.SIDEBAR_TEXT};
            font-size: 14px;
            font-weight: 600;
            background: transparent;
        """)
        self._logo_text.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        logo_text_container.addWidget(self._logo_text)

        self._logo_subtext = QLabel("STUDIO")
        self._logo_subtext.setStyleSheet(f"""
            color: {Colors.SIDEBAR_SECTION};
            font-size: 9px;
            letter-spacing: 2px;
            background: transparent;
        """)
        self._logo_subtext.setFont(QFont("Segoe UI", 8))
        logo_text_container.addWidget(self._logo_subtext)

        logo_row.addLayout(logo_text_container)
        logo_row.addStretch()
        logo_layout.addLayout(logo_row)
        sidebar_layout.addWidget(logo_container)

        # ─── Navigation Container ───
        nav_container = QWidget()
        nav_container.setStyleSheet(f"background-color: {Colors.SIDEBAR_BG};")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(12, 8, 12, 8)
        nav_layout.setSpacing(2)

        # Section label - MAIN MENU
        self._main_label = QLabel("MAIN MENU")
        self._main_label.setObjectName("SidebarSectionLabel")
        self._main_label.setStyleSheet(f"""
            color: {Colors.SIDEBAR_SECTION};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
            padding: 8px 12px 4px 12px;
            background: transparent;
        """)
        self._main_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        nav_layout.addWidget(self._main_label)

        # Main navigation buttons
        for item in self.MAIN_NAV_ITEMS:
            btn = self._create_nav_button(item)
            self._nav_buttons[item.id] = btn
            nav_layout.addWidget(btn)

        nav_layout.addSpacing(12)

        # Section label - TOOLS
        self._tools_label = QLabel("TOOLS")
        self._tools_label.setObjectName("SidebarSectionLabel")
        self._tools_label.setStyleSheet(f"""
            color: {Colors.SIDEBAR_SECTION};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
            padding: 8px 12px 4px 12px;
            background: transparent;
        """)
        self._tools_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        nav_layout.addWidget(self._tools_label)

        # Tools navigation buttons
        for item in self.TOOLS_NAV_ITEMS:
            btn = self._create_nav_button(item)
            self._nav_buttons[item.id] = btn
            nav_layout.addWidget(btn)

        nav_layout.addStretch()
        sidebar_layout.addWidget(nav_container, 1)

        # ─── Bottom Section ───
        bottom_container = QWidget()
        bottom_container.setStyleSheet(f"""
            background-color: {Colors.SIDEBAR_BG};
            border-top: 1px solid {Colors.BORDER};
        """)
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(12, 12, 12, 16)
        bottom_layout.setSpacing(4)

        # Settings button
        settings_item = NavItem("settings", "Settings", "⚙️", "Application Settings")
        settings_btn = self._create_nav_button(settings_item)
        self._nav_buttons["settings"] = settings_btn
        bottom_layout.addWidget(settings_btn)

        # Connection indicator
        self._connection_indicator = self._create_connection_indicator()
        bottom_layout.addWidget(self._connection_indicator)

        # User info
        user_container = self._create_user_info()
        bottom_layout.addWidget(user_container)

        sidebar_layout.addWidget(bottom_container)
        layout.addWidget(sidebar_frame)

        # Set first button as active
        if self._nav_buttons:
            first_key = list(self._nav_buttons.keys())[0]
            self._set_button_active(first_key)

    def _create_nav_button(self, item: NavItem) -> QPushButton:
        """Create a navigation button - GUI-05 style"""
        btn = QPushButton(f"  {item.icon}   {item.label}")
        btn.setObjectName("SidebarButton")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 11))
        btn.setFixedHeight(42)
        btn.setToolTip(item.tooltip or item.label)
        btn.setStyleSheet(self._get_nav_button_style(False))
        btn.clicked.connect(lambda: self._on_nav_click(item.id))
        return btn

    def _get_nav_button_style(self, checked: bool) -> str:
        """Get stylesheet for nav button based on state - Teal accent"""
        if checked:
            return f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: #ffffff;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 12px;
                    text-align: left;
                    font-weight: 600;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_HOVER};
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Colors.SIDEBAR_TEXT};
                    border: none;
                    border-radius: 8px;
                    padding: 10px 12px;
                    text-align: left;
                    font-weight: 500;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {Colors.SIDEBAR_HOVER};
                    color: {Colors.PRIMARY};
                }}
            """

    def _create_connection_indicator(self) -> QWidget:
        """Create connection status indicator"""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # Status dot
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px; background: transparent;")
        layout.addWidget(self._status_dot)

        # Connection label
        self._conn_label = QLabel("Not connected")
        self._conn_label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 11px;
            background: transparent;
        """)
        self._conn_label.setWordWrap(True)
        layout.addWidget(self._conn_label, 1)

        return container

    def _create_user_info(self) -> QWidget:
        """Create user info section at bottom"""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 4)
        layout.setSpacing(10)

        # Avatar circle
        avatar = QLabel("EC")
        avatar.setObjectName("AvatarCircle")
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(f"""
            QLabel#AvatarCircle {{
                background-color: {Colors.PRIMARY};
                color: white;
                border-radius: 16px;
                font-weight: 600;
                font-size: 11px;
            }}
        """)
        layout.addWidget(avatar)

        # User name
        user_label = QLabel("DBA User")
        user_label.setObjectName("SidebarUserLabel")
        user_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 11px;
            background: transparent;
        """)
        layout.addWidget(user_label, 1)

        return container

    def _on_nav_click(self, item_id: str) -> None:
        """Handle navigation button click"""
        self._set_button_active(item_id)
        self.navigation_changed.emit(item_id)
        
        # Also emit page index for compatibility
        all_items = self.MAIN_NAV_ITEMS + self.TOOLS_NAV_ITEMS + [NavItem("settings", "Settings", "⚙️")]
        for i, item in enumerate(all_items):
            if item.id == item_id:
                self.page_changed.emit(i)
                break

    def _set_button_active(self, item_id: str) -> None:
        """Set a button as active and deactivate others"""
        for nav_id, btn in self._nav_buttons.items():
            is_active = nav_id == item_id
            btn.setChecked(is_active)
            btn.setStyleSheet(self._get_nav_button_style(is_active))
        
        self._current_nav_id = item_id

    def _refresh_section_visibility(self) -> None:
        """Show/hide section labels based on visible buttons."""
        if self._main_label:
            self._main_label.setVisible(
                any(self._nav_buttons.get(nav_id) and self._nav_buttons[nav_id].isVisible()
                    for nav_id in self._main_nav_ids)
            )
        if self._tools_label:
            self._tools_label.setVisible(
                any(self._nav_buttons.get(nav_id) and self._nav_buttons[nav_id].isVisible()
                    for nav_id in self._tools_nav_ids)
            )

    def get_first_visible_nav_id(self) -> Optional[str]:
        """Return first visible navigation id. Falls back to settings."""
        ordered_ids = self._main_nav_ids + self._tools_nav_ids + ["settings"]
        for nav_id in ordered_ids:
            btn = self._nav_buttons.get(nav_id)
            if btn and btn.isVisible():
                return nav_id
        return None

    def set_menu_visibility(self, visibility: Dict[str, bool]) -> None:
        """
        Apply menu visibility settings.
        `settings` button is always kept visible to avoid lock-out.
        """
        for nav_id, btn in self._nav_buttons.items():
            if nav_id == "settings":
                btn.setVisible(True)
                continue
            btn.setVisible(bool(visibility.get(nav_id, True)))

        self._refresh_section_visibility()

        # If current item becomes hidden, switch visual active state to first visible item.
        if self._current_nav_id:
            current_btn = self._nav_buttons.get(self._current_nav_id)
            if current_btn and not current_btn.isVisible():
                fallback_id = self.get_first_visible_nav_id()
                if fallback_id:
                    self._set_button_active(fallback_id)

    def set_current(self, item_id: str) -> None:
        """Set the currently selected navigation item"""
        if item_id in self._nav_buttons:
            self._set_button_active(item_id)

    def get_current(self) -> Optional[str]:
        """Get currently selected navigation item id"""
        return self._current_nav_id

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed

    def update_connection_status(
        self, 
        connected: bool, 
        server: str = "", 
        database: str = ""
    ) -> None:
        """Update connection indicator - GUI-05 style"""
        if connected:
            self._status_dot.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 10px; background: transparent;")
            display = server
            if database:
                display = f"{server} / {database}"
            self._conn_label.setText(display)
            self._conn_label.setStyleSheet(f"""
                color: {Colors.TEXT_SECONDARY};
                font-size: 11px;
                background: transparent;
            """)
        else:
            self._status_dot.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px; background: transparent;")
            self._conn_label.setText("Not connected")
            self._conn_label.setStyleSheet(f"""
                color: {Colors.TEXT_MUTED};
                font-size: 11px;
                background: transparent;
            """)

    # Properties for accessing labels (for i18n)
    @property
    def logo(self) -> QLabel:
        return self._logo_text
    
    @property
    def main_menu_label(self) -> QLabel:
        return self._main_label
    
    @property
    def tools_label(self) -> QLabel:
        return self._tools_label

    # Button accessors for i18n
    @property
    def btn_dashboard(self) -> QPushButton:
        return self._nav_buttons.get("dashboard")
    
    @property
    def btn_object_explorer(self) -> QPushButton:
        return self._nav_buttons.get("sp_explorer")
    
    @property
    def btn_query_stats(self) -> QPushButton:
        return self._nav_buttons.get("query_stats")
    
    @property
    def btn_perf_advisor(self) -> QPushButton:
        return self._nav_buttons.get("index_advisor")
    
    @property
    def btn_blocking(self) -> QPushButton:
        return self._nav_buttons.get("blocking")
    
    @property
    def btn_security(self) -> QPushButton:
        return self._nav_buttons.get("security")
    
    @property
    def btn_jobs(self) -> QPushButton:
        return self._nav_buttons.get("jobs")
    
    @property
    def btn_waits(self) -> QPushButton:
        return self._nav_buttons.get("wait_stats")


# Alias for backward compatibility
Sidebar = DarkSidebar
