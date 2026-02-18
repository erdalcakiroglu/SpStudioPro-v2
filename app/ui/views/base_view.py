"""
Base view class for all application views - Modern Enterprise Design
"""

from typing import Optional
from abc import ABC, abstractmethod

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QShowEvent
from PyQt6.QtCore import pyqtSignal

from app.ui.theme import Colors, Theme


class BaseView(QWidget):
    """
    Abstract base class for all application views
    
    Provides common functionality:
    - Standard layout setup
    - Loading state management
    - Error display
    - Refresh capability
    """
    
    # Signals
    loading_started = pyqtSignal()
    loading_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._is_loading = False
        self._is_initialized = False
        self._explicit_view_stylesheet = ""
        
        # Apply modern background + shared controls style baseline
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        
        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(32, 24, 32, 32)
        self._main_layout.setSpacing(16)

    def setStyleSheet(self, styleSheet: str) -> None:
        """
        Enforce Query Statistics-aligned baseline styles across all views.
        View-level style remains intact and is merged with shared control styles.
        """
        self._explicit_view_stylesheet = str(styleSheet or "")
        merged = f"{self._explicit_view_stylesheet}\n{self._shared_controls_stylesheet()}"
        super().setStyleSheet(merged)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        try:
            Theme.style_pushbuttons_in_widget(self)
        except Exception:
            pass

    @staticmethod
    def _shared_controls_stylesheet() -> str:
        return f"""
            {Theme.combobox_style()}
            {Theme.listbox_style()}
            {Theme.tab_widget_style()}
            {Theme.btn_default()}

            QCheckBox {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 600;
                spacing: 6px;
            }}
            QCheckBox:hover {{
                color: {Colors.TEXT_PRIMARY};
            }}
            QCheckBox:disabled {{
                color: {Colors.TEXT_MUTED};
            }}

            QLineEdit {{
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border: 1px solid {Colors.PRIMARY};
            }}
            QLineEdit::placeholder {{
                color: {Colors.TEXT_MUTED};
            }}

            QMenu {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                color: {Colors.TEXT_PRIMARY};
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: #f8fafc;
                color: {Colors.PRIMARY};
            }}
        """
    
    @property
    def view_id(self) -> str:
        """Unique identifier for this view"""
        return self.__class__.__name__.lower().replace('view', '')
    
    @property
    def view_title(self) -> str:
        """Display title for this view"""
        return self.__class__.__name__.replace('View', '')
    
    @property
    def is_loading(self) -> bool:
        return self._is_loading
    
    def initialize(self) -> None:
        """
        Initialize the view (called when first shown)
        Override in subclasses for lazy initialization
        """
        if not self._is_initialized:
            self._setup_ui()
            self._is_initialized = True
    
    @abstractmethod
    def _setup_ui(self) -> None:
        """Setup the view UI - must be implemented by subclasses"""
        pass
    
    def refresh(self) -> None:
        """Refresh view data - override in subclasses"""
        pass
    
    def set_loading(self, loading: bool) -> None:
        """Set loading state"""
        self._is_loading = loading
        if loading:
            self.loading_started.emit()
        else:
            self.loading_finished.emit()
    
    def show_error(self, message: str) -> None:
        """Show error message"""
        self.error_occurred.emit(message)
    
    def on_show(self) -> None:
        """Called when view becomes visible - override for custom behavior"""
        pass
    
    def on_hide(self) -> None:
        """Called when view is hidden - override for custom behavior"""
        pass
