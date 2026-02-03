"""
Base view class for all application views - Modern Enterprise Design
"""

from typing import Optional
from abc import ABC, abstractmethod

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal

from app.ui.theme import Colors


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
        
        # Apply modern background
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        
        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(32, 24, 32, 32)
        self._main_layout.setSpacing(16)
    
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
