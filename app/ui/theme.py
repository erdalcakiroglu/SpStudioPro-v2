"""
Theme management for SQL Performance AI Platform
Supports Dark and Light themes with QSS styling
Modern Enterprise Design with Teal accent
"""

from pathlib import Path
from typing import Optional
from enum import Enum

from PyQt6.QtWidgets import QApplication, QWidget, QFrame, QVBoxLayout, QLabel
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import QObject, pyqtSignal, Qt

from app.core.constants import Theme as ThemeEnum
from app.core.logger import get_logger

logger = get_logger('ui.theme')


# ---------------------------------------------------------------------
# COLOR CONSTANTS - Modern Enterprise Design (GUI-05 Style)
# ---------------------------------------------------------------------
class Colors:
    """Modern enterprise color palette - Teal accent"""
    # Primary - Teal (Ana marka rengi)
    PRIMARY = "#0e8a9d"
    PRIMARY_HOVER = "#0d7a8b"
    PRIMARY_PRESSED = "#0a5f6f"
    PRIMARY_LIGHT = "#e4f0f4"
    
    # Secondary - Indigo/Mor (Aksiyon butonları)
    SECONDARY = "#6366f1"
    SECONDARY_HOVER = "#4f46e5"
    SECONDARY_PRESSED = "#4338ca"
    SECONDARY_LIGHT = "#e0e7ff"
    
    # Danger - Kırmızı
    DANGER = "#dc2626"
    DANGER_HOVER = "#b91c1c"
    DANGER_PRESSED = "#991b1b"
    DANGER_LIGHT = "#fef2f2"
    
    # Success - Yeşil
    SUCCESS = "#10b981"
    SUCCESS_HOVER = "#059669"
    SUCCESS_LIGHT = "#d1fae5"
    
    # Warning - Turuncu
    WARNING = "#f59e0b"
    WARNING_HOVER = "#d97706"
    WARNING_LIGHT = "#fef3c7"
    
    # Info - Mavi
    INFO = "#3b82f6"
    INFO_HOVER = "#2563eb"
    INFO_LIGHT = "#dbeafe"
    
    # Background
    BACKGROUND = "#f5f7fb"
    CARD_BG = "#ffffff"
    CODE_BG = "#111827"
    CODE_GUTTER = "#0f172a"
    SURFACE = "#ffffff"
    
    # Sidebar
    SIDEBAR_BG = "#ffffff"
    SIDEBAR_HOVER = "#e4f0f4"
    SIDEBAR_TEXT = "#27313d"
    SIDEBAR_TEXT_HOVER = "#0e8a9d"
    SIDEBAR_ACTIVE_BG = "#0e8a9d"
    SIDEBAR_ACTIVE_TEXT = "#FFFFFF"
    SIDEBAR_SECTION = "#8b93a2"
    
    # Borders
    BORDER = "#e5e7eb"
    BORDER_LIGHT = "#eef2f7"
    BORDER_DARK = "#d1d5db"
    BORDER_CODE = "#1f2937"
    
    # Text
    TEXT_PRIMARY = "#1f2937"
    TEXT_SECONDARY = "#6b7280"
    TEXT_MUTED = "#9ca3af"
    TEXT_HEADER = "#374151"
    TEXT_CODE = "#e5e7eb"
    
    # Status Colors
    ERROR = "#ef4444"
    PURPLE = "#8B5CF6"


# ---------------------------------------------------------------------
# THEME STYLE GENERATORS - Modern Button & Component Styles
# ---------------------------------------------------------------------
class Theme:
    """Merkezi tema yönetimi - Tüm stiller burada tanımlanır."""
    
    # Font Sizes
    FONT_XS = "10px"
    FONT_SM = "11px"
    FONT_BASE = "12px"
    FONT_LG = "13px"
    FONT_XL = "14px"
    FONT_2XL = "16px"
    
    @classmethod
    def btn_primary(cls, size: str = "md") -> str:
        """Primary buton - Ana aksiyon (Teal renk).
        Kullanım: Kaydet, Bağlan, Ana işlem butonları
        """
        sizes = {
            "sm": ("4px 10px", cls.FONT_SM, "6px"),
            "md": ("6px 14px", cls.FONT_BASE, "8px"),
            "lg": ("8px 20px", cls.FONT_LG, "8px"),
        }
        padding, font_size, radius = sizes.get(size, sizes["md"])
        return f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: #ffffff;
                border: none;
                border-radius: {radius};
                padding: {padding};
                font-size: {font_size};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER_DARK};
                color: {Colors.TEXT_MUTED};
            }}
        """
    
    @classmethod
    def btn_secondary(cls, size: str = "md") -> str:
        """Secondary buton - İkincil aksiyon (Mor/Indigo renk).
        Kullanım: Run Audit, Refresh, Analyze gibi aksiyonlar
        """
        sizes = {
            "sm": ("4px 10px", cls.FONT_SM, "6px"),
            "md": ("6px 14px", cls.FONT_BASE, "8px"),
            "lg": ("8px 20px", cls.FONT_LG, "8px"),
        }
        padding, font_size, radius = sizes.get(size, sizes["md"])
        return f"""
            QPushButton {{
                background-color: {Colors.SECONDARY};
                color: #ffffff;
                border: none;
                border-radius: {radius};
                padding: {padding};
                font-size: {font_size};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.SECONDARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Colors.SECONDARY_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER_DARK};
                color: {Colors.TEXT_MUTED};
            }}
        """
    
    @classmethod
    def btn_danger(cls, size: str = "md") -> str:
        """Danger buton - Tehlikeli işlemler (Kırmızı).
        Kullanım: Sil, Kill Session, Remove
        """
        sizes = {
            "sm": ("4px 10px", cls.FONT_SM, "6px"),
            "md": ("6px 14px", cls.FONT_BASE, "8px"),
            "lg": ("8px 20px", cls.FONT_LG, "8px"),
        }
        padding, font_size, radius = sizes.get(size, sizes["md"])
        return f"""
            QPushButton {{
                background-color: {Colors.DANGER};
                color: #ffffff;
                border: none;
                border-radius: {radius};
                padding: {padding};
                font-size: {font_size};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.DANGER_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Colors.DANGER_PRESSED};
            }}
        """
    
    @classmethod
    def btn_ghost(cls, size: str = "md") -> str:
        """Ghost buton - Hafif görünüm, arka plan gri.
        Kullanım: Geri, İptal, Copy Script gibi düşük öncelikli
        """
        sizes = {
            "sm": ("4px 10px", cls.FONT_SM, "6px"),
            "md": ("6px 14px", cls.FONT_BASE, "6px"),
            "lg": ("8px 20px", cls.FONT_LG, "8px"),
        }
        padding, font_size, radius = sizes.get(size, sizes["md"])
        return f"""
            QPushButton {{
                background-color: #f3f4f6;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: {radius};
                padding: {padding};
                font-size: {font_size};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_PRIMARY};
                border-color: {Colors.BORDER_DARK};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BORDER_DARK};
            }}
        """
    
    @classmethod
    def btn_outline(cls, color: str = "primary", size: str = "md") -> str:
        """Outline buton - Sadece çerçeveli, şeffaf arka plan.
        Colors: primary, secondary, danger
        """
        colors = {
            "primary": (Colors.PRIMARY, Colors.PRIMARY_HOVER, Colors.PRIMARY_LIGHT),
            "secondary": (Colors.SECONDARY, Colors.SECONDARY_HOVER, Colors.SECONDARY_LIGHT),
            "danger": (Colors.DANGER, Colors.DANGER_HOVER, Colors.DANGER_LIGHT),
        }
        sizes = {
            "sm": ("4px 10px", cls.FONT_SM, "6px"),
            "md": ("6px 14px", cls.FONT_BASE, "6px"),
            "lg": ("8px 20px", cls.FONT_LG, "8px"),
        }
        main_color, hover_color, light_bg = colors.get(color, colors["primary"])
        padding, font_size, radius = sizes.get(size, sizes["md"])
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {main_color};
                border: 1px solid {main_color};
                border-radius: {radius};
                padding: {padding};
                font-size: {font_size};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {light_bg};
                border-color: {hover_color};
                color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {main_color};
                color: #ffffff;
            }}
        """
    
    @classmethod
    def btn_toggle(cls) -> str:
        """Toggle buton - Açık/Kapalı durumlu (checkable).
        Kullanım: Auto-Refresh ON/OFF
        """
        return f"""
            QPushButton {{
                background-color: {Colors.SECONDARY};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: {cls.FONT_BASE};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.SECONDARY_HOVER};
            }}
            QPushButton:checked {{
                background-color: {Colors.SECONDARY};
            }}
            QPushButton:!checked {{
                background-color: {Colors.TEXT_MUTED};
            }}
        """
    
    @classmethod
    def btn_small_action(cls) -> str:
        """Küçük aksiyon butonu - Test, Edit, Delete"""
        return f"""
            QPushButton {{
                background-color: #f3f4f6;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: {cls.FONT_SM};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_PRIMARY};
            }}
        """
    
    @classmethod
    def card_style(cls) -> str:
        """Standart kart stili"""
        return f"""
            QFrame {{
                background-color: {Colors.CARD_BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """
    
    @classmethod
    def card_with_accent(cls, color: str = "primary") -> str:
        """Üst kenarlıklı kart (accent color)"""
        accent_colors = {
            "primary": Colors.PRIMARY,
            "secondary": Colors.SECONDARY,
            "success": Colors.SUCCESS,
            "warning": Colors.WARNING,
            "danger": Colors.DANGER,
            "info": Colors.INFO,
        }
        accent = accent_colors.get(color, Colors.PRIMARY)
        return f"""
            QFrame {{
                background-color: {Colors.CARD_BG};
                border: 1px solid {Colors.BORDER};
                border-top: 3px solid {accent};
                border-radius: 10px;
            }}
        """
    
    @classmethod
    def table_style(cls) -> str:
        """Modern tablo stili"""
        return f"""
            QTableWidget {{
                border: none;
                background-color: transparent;
                gridline-color: {Colors.BORDER};
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: #f3f4f6;
                color: {Colors.TEXT_HEADER};
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                font-weight: 600;
                font-size: 11px;
            }}
            QTableWidget::item {{
                padding: 8px 10px;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.SECONDARY_LIGHT};
                color: {Colors.TEXT_PRIMARY};
            }}
            QTableWidget::item:hover {{
                background-color: {Colors.PRIMARY_LIGHT};
            }}
        """
    
    @classmethod
    def input_style(cls) -> str:
        """Input field stili"""
        return f"""
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {Colors.CARD_BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
                font-size: {cls.FONT_BASE};
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {Colors.PRIMARY};
            }}
            QLineEdit:disabled {{
                background-color: #f3f4f6;
                color: {Colors.TEXT_MUTED};
            }}
        """
    
    @classmethod
    def combobox_style(cls) -> str:
        """ComboBox stili"""
        return f"""
            QComboBox {{
                background-color: {Colors.CARD_BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px 12px;
                color: {Colors.TEXT_PRIMARY};
                font-size: {cls.FONT_BASE};
                min-height: 20px;
            }}
            QComboBox:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {Colors.TEXT_SECONDARY};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.CARD_BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                selection-background-color: {Colors.PRIMARY_LIGHT};
                selection-color: {Colors.TEXT_PRIMARY};
                padding: 4px;
            }}
        """
    
    @classmethod
    def provider_card_style(cls) -> str:
        """Provider/Connection card stili"""
        return f"""
            QFrame#ProviderCard, QFrame#ConnectionCard {{
                background-color: {Colors.CARD_BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
            }}
            QFrame#ProviderCard:hover, QFrame#ConnectionCard:hover {{
                border-color: {Colors.PRIMARY};
                background-color: {Colors.PRIMARY_LIGHT};
            }}
        """
    
    @classmethod
    def scrollbar_style(cls) -> str:
        """Scrollbar stili"""
        return f"""
            QScrollBar:vertical {{
                background-color: {Colors.BACKGROUND};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BORDER_DARK};
                border-radius: 5px;
                min-height: 30px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {Colors.TEXT_MUTED};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background-color: {Colors.BACKGROUND};
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {Colors.BORDER_DARK};
                border-radius: 5px;
                min-width: 30px;
                margin: 2px;
            }}
        """


class ThemeColors:
    """Color definitions for themes"""
    
    # Dark Theme Colors
    DARK = {
        # Backgrounds
        'bg_primary': '#1a1a1a',
        'bg_secondary': '#242424',
        'bg_tertiary': '#2a2a2a',
        'bg_sidebar': '#0d0d0d',
        'bg_hover': '#333333',
        'bg_selected': '#094771',
        'bg_input': '#2d2d2d',
        
        # Text
        'text_primary': '#ffffff',
        'text_secondary': '#cccccc',
        'text_muted': '#888888',
        'text_disabled': '#555555',
        
        # Borders
        'border_primary': '#3a3a3a',
        'border_secondary': '#2a2a2a',
        'border_focus': '#0066ff',
        
        # Accent
        'accent_primary': '#0066ff',
        'accent_secondary': '#00aa66',
        'accent_hover': '#0077ff',
        
        # Status
        'success': '#4ade80',
        'warning': '#fbbf24',
        'error': '#ef4444',
        'info': '#60a5fa',
        
        # Code
        'code_bg': '#1e1e1e',
        'code_keyword': '#569cd6',
        'code_string': '#ce9178',
        'code_comment': '#6a9955',
        'code_function': '#dcdcaa',
    }
    
    # Light Theme Colors - GUI-05 Style (Teal Accent)
    LIGHT = {
        # Backgrounds
        'bg_primary': '#f5f7fb',  # Main background
        'bg_secondary': '#ffffff',  # Cards, surfaces
        'bg_tertiary': '#f3f4f6',  # Subtle backgrounds
        'bg_sidebar': '#ffffff',  # Sidebar background
        'bg_hover': '#e4f0f4',  # Hover states (teal tint)
        'bg_selected': '#0e8a9d',  # Selected state (teal)
        'bg_input': '#ffffff',
        
        # Text
        'text_primary': '#27313d',  # Primary text
        'text_secondary': '#4c5667',  # Secondary text
        'text_muted': '#8b93a2',  # Muted/section labels
        'text_disabled': '#9ca3af',
        
        # Borders
        'border_primary': '#dde2eb',  # Primary borders
        'border_secondary': '#e5e7eb',  # Subtle borders
        'border_focus': '#0e8a9d',  # Focus state (teal)
        
        # Accent - Teal primary
        'accent_primary': '#0e8a9d',  # Teal - main accent
        'accent_secondary': '#6366f1',  # Indigo - secondary actions
        'accent_hover': '#0d7a8b',  # Teal hover
        
        # Status
        'success': '#10b981',
        'warning': '#f59e0b',
        'error': '#ef4444',
        'info': '#3b82f6',
        
        # Code
        'code_bg': '#111827',  # Dark code background
        'code_keyword': '#569cd6',
        'code_string': '#ce9178',
        'code_comment': '#6a9955',
        'code_function': '#dcdcaa',
    }


def generate_dark_theme() -> str:
    """Generate Dark theme QSS"""
    c = ThemeColors.DARK
    return f'''
/* ============================================
   SQL Performance AI - Dark Theme
   ============================================ */

/* === Global === */
QWidget {{
    background-color: {c['bg_primary']};
    color: {c['text_primary']};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {c['bg_primary']};
}}

/* === Sidebar === */
#sidebar {{
    background-color: {c['bg_sidebar']};
    border-right: 1px solid {c['border_secondary']};
}}

#sidebar QPushButton {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    text-align: left;
    color: {c['text_muted']};
}}

#sidebar QPushButton:hover {{
    background-color: {c['bg_hover']};
    color: {c['text_primary']};
}}

#sidebar QPushButton:checked {{
    background-color: {c['bg_selected']};
    color: {c['text_primary']};
}}

#sidebar QPushButton#navButton {{
    font-size: 14px;
    padding: 10px 12px;
}}

/* === Content Area === */
#contentArea {{
    background-color: {c['bg_primary']};
}}

/* === Inputs === */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {c['bg_input']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {c['text_primary']};
    selection-background-color: {c['accent_primary']};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {c['border_focus']};
}}

QLineEdit:disabled {{
    background-color: {c['bg_tertiary']};
    color: {c['text_disabled']};
}}

/* === Chat Input === */
#chatInput {{
    background-color: {c['bg_secondary']};
    border: 1px solid {c['border_primary']};
    border-radius: 24px;
    padding: 12px 20px;
    font-size: 14px;
}}

#chatInput:focus {{
    border-color: {c['accent_primary']};
}}

/* === Buttons === */
QPushButton {{
    background-color: {c['bg_tertiary']};
    border: 1px solid {c['border_primary']};
    border-radius: 6px;
    padding: 8px 16px;
    color: {c['text_primary']};
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {c['bg_hover']};
    border-color: {c['border_focus']};
}}

QPushButton:pressed {{
    background-color: {c['bg_selected']};
}}

QPushButton:disabled {{
    background-color: {c['bg_tertiary']};
    color: {c['text_disabled']};
    border-color: {c['border_secondary']};
}}

QPushButton#primaryButton {{
    background-color: {c['accent_primary']};
    border: none;
    color: white;
}}

QPushButton#primaryButton:hover {{
    background-color: {c['accent_hover']};
}}

/* === Tables === */
QTableView, QTreeView, QListView {{
    background-color: {c['bg_primary']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    gridline-color: {c['border_secondary']};
    selection-background-color: {c['bg_selected']};
}}

QTableView::item, QTreeView::item, QListView::item {{
    padding: 8px;
    border-bottom: 1px solid {c['border_secondary']};
}}

QTableView::item:hover, QTreeView::item:hover, QListView::item:hover {{
    background-color: {c['bg_hover']};
}}

QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {{
    background-color: {c['bg_selected']};
    color: {c['text_primary']};
}}

QHeaderView::section {{
    background-color: {c['bg_secondary']};
    color: {c['text_secondary']};
    padding: 10px;
    border: none;
    border-bottom: 1px solid {c['border_primary']};
    font-weight: 600;
}}

/* === ScrollBars === */
QScrollBar:vertical {{
    background-color: {c['bg_primary']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {c['bg_tertiary']};
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {c['bg_hover']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {c['bg_primary']};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {c['bg_tertiary']};
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}}

/* === Tabs === */
QTabWidget::pane {{
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    background-color: {c['bg_primary']};
}}

QTabBar::tab {{
    background-color: {c['bg_secondary']};
    border: 1px solid {c['border_primary']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 16px;
    color: {c['text_muted']};
}}

QTabBar::tab:selected {{
    background-color: {c['bg_primary']};
    color: {c['text_primary']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {c['bg_hover']};
}}

/* === Splitter === */
QSplitter::handle {{
    background-color: {c['border_secondary']};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* === ToolTip === */
QToolTip {{
    background-color: {c['bg_tertiary']};
    color: {c['text_primary']};
    border: 1px solid {c['border_primary']};
    border-radius: 4px;
    padding: 6px 10px;
}}

/* === Menu === */
QMenu {{
    background-color: {c['bg_secondary']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {c['bg_selected']};
}}

/* === ComboBox === */
QComboBox {{
    background-color: {c['bg_input']};
    border: 1px solid {c['border_primary']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {c['text_primary']};
}}

QComboBox:hover {{
    border-color: {c['border_focus']};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {c['bg_secondary']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    selection-background-color: {c['bg_selected']};
}}

/* === Progress Bar === */
QProgressBar {{
    background-color: {c['bg_secondary']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    height: 20px;
    text-align: center;
    color: {c['text_primary']};
}}

QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['accent_primary']}, stop:1 {c['accent_secondary']});
    border-radius: 7px;
}}

/* === Dialog === */
QDialog {{
    background-color: {c['bg_primary']};
}}

/* === GroupBox === */
QGroupBox {{
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {c['text_secondary']};
}}

/* === Status Bar === */
QStatusBar {{
    background-color: {c['bg_secondary']};
    border-top: 1px solid {c['border_secondary']};
    color: {c['text_muted']};
}}

/* === Chat Messages === */
#userMessage {{
    background-color: {c['accent_primary']};
    border-radius: 18px 18px 4px 18px;
    padding: 12px 16px;
    color: white;
}}

#aiMessage {{
    background-color: {c['bg_secondary']};
    border-radius: 18px 18px 18px 4px;
    padding: 12px 16px;
    color: {c['text_primary']};
}}

/* === Code Block === */
#codeBlock {{
    background-color: {c['code_bg']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}}

/* === Cards === */
#card {{
    background-color: {c['bg_secondary']};
    border: 1px solid {c['border_primary']};
    border-radius: 12px;
    padding: 16px;
}}

#card:hover {{
    border-color: {c['accent_primary']};
}}

/* === Status Indicators === */
#statusSuccess {{
    color: {c['success']};
}}

#statusWarning {{
    color: {c['warning']};
}}

#statusError {{
    color: {c['error']};
}}

#statusInfo {{
    color: {c['info']};
}}
'''


def generate_light_theme() -> str:
    """Generate Light theme QSS - GUI-05 Modern Style"""
    c = ThemeColors.LIGHT
    return f'''
/* ============================================
   SQL Performance AI - Light Theme (GUI-05 Style)
   Modern Enterprise Design with Teal Accent
   ============================================ */

/* === Global === */
QWidget {{
    background-color: {c['bg_primary']};
    color: {c['text_primary']};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    font-size: 12px;
}}

QMainWindow {{
    background-color: {c['bg_primary']};
}}

/* === Sidebar === */
#sidebar {{
    background-color: {c['bg_sidebar']};
    border-right: 1px solid {c['border_primary']};
}}

#sidebar QPushButton {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 12px;
    text-align: left;
    color: {c['text_primary']};
    font-size: 13px;
}}

#sidebar QPushButton:hover {{
    background-color: {c['bg_hover']};
    color: {c['accent_primary']};
}}

#sidebar QPushButton:checked {{
    background-color: {c['bg_selected']};
    color: #ffffff;
}}

/* === Content Area === */
#contentArea {{
    background-color: {c['bg_primary']};
}}

#ContentWrapper {{
    background-color: {c['bg_primary']};
}}

/* === Inputs === */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {c['bg_input']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {c['text_primary']};
    selection-background-color: {c['accent_primary']};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {c['border_focus']};
    background-color: {c['bg_input']};
}}

QLineEdit#SearchField {{
    border-radius: 18px;
    border: 1px solid {c['border_primary']};
    padding: 0 16px;
    background-color: #f7f9fc;
}}

QLineEdit#SearchField:focus {{
    border: 1px solid {c['accent_primary']};
    background-color: {c['bg_input']};
}}

/* === Chat Input === */
#chatInput {{
    background-color: {c['bg_secondary']};
    border: 1px solid {c['border_primary']};
    border-radius: 24px;
    padding: 12px 20px;
    font-size: 14px;
}}

#chatInput:focus {{
    border-color: {c['accent_primary']};
}}

/* === Buttons === */
QPushButton {{
    background-color: {c['bg_tertiary']};
    border: 1px solid {c['border_primary']};
    border-radius: 6px;
    padding: 8px 16px;
    color: {c['text_primary']};
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {c['bg_hover']};
    border-color: {c['border_focus']};
}}

QPushButton:pressed {{
    background-color: {c['border_primary']};
}}

QPushButton:disabled {{
    background-color: {c['bg_tertiary']};
    color: {c['text_disabled']};
    border-color: {c['border_secondary']};
}}

QPushButton#primaryButton, QPushButton#AddConnectionButton {{
    background-color: {c['accent_primary']};
    border: none;
    color: white;
    font-weight: 600;
}}

QPushButton#primaryButton:hover, QPushButton#AddConnectionButton:hover {{
    background-color: {c['accent_hover']};
}}

QPushButton#SidebarButton {{
    text-align: left;
    padding-left: 12px;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    color: {c['text_primary']};
    background-color: transparent;
}}

QPushButton#SidebarButton:hover {{
    background-color: {c['bg_hover']};
}}

QPushButton#SidebarButton:checked {{
    background-color: {c['accent_primary']};
    color: #ffffff;
}}

QPushButton#TopIconButton {{
    border: none;
    background-color: transparent;
    border-radius: 16px;
    font-size: 14px;
}}

QPushButton#TopIconButton:hover {{
    background-color: {c['bg_hover']};
}}

/* === Cards === */
QFrame#Card {{
    background-color: {c['bg_secondary']};
    border-radius: 16px;
    border: 1px solid {c['border_secondary']};
}}

QFrame#Card:hover {{
    border-color: {c['accent_primary']};
}}

/* === Tables === */
QTableView, QTreeView, QListView, QTableWidget {{
    background-color: {c['bg_secondary']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    gridline-color: {c['border_secondary']};
    selection-background-color: #e0e7ff;
}}

QTableView::item, QTreeView::item, QListView::item, QTableWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid {c['border_secondary']};
}}

QTableView::item:hover, QTableWidget::item:hover {{
    background-color: {c['bg_hover']};
}}

QTableView::item:selected, QTableWidget::item:selected {{
    background-color: #e0e7ff;
    color: {c['text_primary']};
}}

QHeaderView::section {{
    background-color: #f3f4f6;
    color: {c['text_secondary']};
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {c['border_primary']};
    font-weight: 600;
    font-size: 11px;
}}

/* === ScrollBars === */
QScrollBar:vertical {{
    background-color: {c['bg_primary']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {c['border_primary']};
    border-radius: 5px;
    min-height: 30px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {c['text_muted']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {c['bg_primary']};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: {c['border_primary']};
    border-radius: 5px;
    min-width: 30px;
    margin: 2px;
}}

/* === Tabs === */
QTabWidget#SettingsTabs::pane {{
    border: 1px solid {c['border_primary']};
    border-radius: 10px;
    background: {c['bg_secondary']};
}}

QTabWidget::pane {{
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    background-color: {c['bg_secondary']};
}}

QTabBar::tab {{
    padding: 6px 14px;
    border-radius: 8px;
    margin-right: 4px;
    font-size: 12px;
    color: {c['text_secondary']};
    background-color: transparent;
}}

QTabBar::tab:selected {{
    background-color: {c['accent_primary']};
    color: #ffffff;
}}

QTabBar::tab:hover {{
    background-color: {c['bg_hover']};
}}

/* === TopBar === */
QFrame#TopBar {{
    background-color: {c['bg_secondary']};
    border-bottom: 1px solid {c['border_primary']};
}}

/* === InfoBar === */
QFrame#InfoBar, QFrame#infoBar {{
    background-color: {c['bg_secondary']};
    border-top: 1px solid {c['border_primary']};
}}

/* === Progress Bar === */
QProgressBar {{
    background-color: {c['bg_tertiary']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    height: 20px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['accent_primary']}, stop:1 {c['accent_secondary']});
    border-radius: 7px;
}}

/* === ComboBox === */
QComboBox {{
    background-color: {c['bg_input']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    padding: 6px 12px;
    color: {c['text_primary']};
    min-height: 20px;
}}

QComboBox:hover {{
    border-color: {c['accent_primary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {c['text_secondary']};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {c['bg_secondary']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    selection-background-color: {c['bg_hover']};
    selection-color: {c['text_primary']};
    padding: 4px;
}}

/* === GroupBox === */
QGroupBox {{
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {c['text_secondary']};
}}

/* === Labels === */
QLabel#Logo {{
    font-size: 14px;
    font-weight: 600;
    color: {c['text_primary']};
}}

QLabel#SidebarSectionLabel {{
    font-size: 10px;
    letter-spacing: 1px;
    color: {c['text_muted']};
}}

QLabel#PageTitle {{
    font-size: 20px;
    font-weight: 600;
    color: {c['text_primary']};
}}

QLabel#PageSubtitle {{
    font-size: 13px;
    color: {c['text_secondary']};
}}

QLabel#CardTitle {{
    font-size: 15px;
    font-weight: 600;
    color: {c['text_primary']};
}}

QLabel#CardText {{
    font-size: 13px;
    color: {c['text_secondary']};
}}

QLabel#TopTitle {{
    font-size: 18px;
    font-weight: 600;
    color: {c['text_primary']};
}}

/* === Status Indicators === */
#statusSuccess {{ color: {c['success']}; }}
#statusWarning {{ color: {c['warning']}; }}
#statusError {{ color: {c['error']}; }}
#statusInfo {{ color: {c['info']}; }}

/* === Dialog === */
QDialog {{
    background-color: {c['bg_secondary']};
}}

/* === ToolTip === */
QToolTip {{
    background-color: {c['bg_secondary']};
    color: {c['text_primary']};
    border: 1px solid {c['border_primary']};
    border-radius: 4px;
    padding: 6px 10px;
}}

/* === Menu === */
QMenu {{
    background-color: {c['bg_secondary']};
    border: 1px solid {c['border_primary']};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {c['bg_hover']};
}}
'''


class ThemeManager(QObject):
    """
    Manages application themes
    
    Signals:
        theme_changed: Emitted when theme changes, passes new theme name
    """
    
    theme_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_theme: ThemeEnum = ThemeEnum.LIGHT  # Default to light theme
        self._themes: dict[ThemeEnum, str] = {
            ThemeEnum.DARK: generate_dark_theme(),
            ThemeEnum.LIGHT: generate_light_theme(),
        }
    
    @property
    def current_theme(self) -> ThemeEnum:
        return self._current_theme
    
    def set_theme(self, theme: ThemeEnum) -> None:
        """Set and apply a theme"""
        if theme == ThemeEnum.SYSTEM:
            # Detect system theme (simplified - use light for modern look)
            theme = ThemeEnum.LIGHT
        
        self._current_theme = theme
        self._apply_to_app()
        self.theme_changed.emit(theme.value)
        logger.info(f"Theme changed to: {theme.value}")
    
    def toggle_theme(self) -> ThemeEnum:
        """Toggle between dark and light themes"""
        new_theme = ThemeEnum.LIGHT if self._current_theme == ThemeEnum.DARK else ThemeEnum.DARK
        self.set_theme(new_theme)
        return new_theme
    
    def get_stylesheet(self, theme: Optional[ThemeEnum] = None) -> str:
        """Get QSS stylesheet for a theme"""
        theme = theme or self._current_theme
        return self._themes.get(theme, self._themes[ThemeEnum.LIGHT])
    
    def get_color(self, color_name: str) -> str:
        """Get a specific color for current theme"""
        colors = ThemeColors.DARK if self._current_theme == ThemeEnum.DARK else ThemeColors.LIGHT
        return colors.get(color_name, '#ffffff')
    
    def _apply_to_app(self) -> None:
        """Apply theme to QApplication"""
        app = QApplication.instance()
        if app:
            stylesheet = self.get_stylesheet()
            app.setStyleSheet(stylesheet)


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get the global ThemeManager instance"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def apply_theme(theme: ThemeEnum) -> None:
    """Convenience function to apply a theme"""
    manager = get_theme_manager()
    manager.set_theme(theme)


class CircleStatCard(QFrame):
    """
    Circle stat card widget - GUI-05 Style
    
    A circular card displaying a value with a title below.
    Supports value updates and accent color changes.
    """
    
    def __init__(self, title: str, value: str, accent: str = "#6366f1", parent=None):
        super().__init__(parent)
        self._accent = accent
        self._setup_ui(title, value, accent)
    
    def _setup_ui(self, title: str, value: str, accent: str):
        self.setStyleSheet("background-color: transparent; border: none;")
        self.setFixedSize(100, 115)  # Fixed size for consistent layout
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        
        # Circle
        self._circle = QFrame()
        self._circle.setFixedSize(90, 90)
        self._circle.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 45px;
            }}
        """)
        circle_layout = QVBoxLayout(self._circle)
        circle_layout.setContentsMargins(0, 0, 0, 0)
        circle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Value label
        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(
            f"color: {accent}; font-size: 18px; font-weight: 700; background: transparent; border: none;"
        )
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle_layout.addWidget(self._value_label)
        
        # Title label
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; background: transparent;")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setWordWrap(True)
        
        layout.addWidget(self._circle, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._title_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    
    def update_value(self, value: str, accent: str = None):
        """Update the displayed value and optionally the accent color"""
        self._value_label.setText(value)
        if accent:
            self._accent = accent
            self._value_label.setStyleSheet(
                f"color: {accent}; font-size: 18px; font-weight: 700; background: transparent; border: none;"
            )
    
    def set_accent(self, accent: str):
        """Set the accent color"""
        self._accent = accent
        self._value_label.setStyleSheet(
            f"color: {accent}; font-size: 18px; font-weight: 700; background: transparent; border: none;"
        )


def create_circle_stat_card(title: str, value: str, accent: str = "#6366f1") -> CircleStatCard:
    """
    Create a circle stat card widget - GUI-05 Style
    
    Args:
        title: Label text below the circle
        value: Value text inside the circle
        accent: Accent color for the value text
    
    Returns:
        CircleStatCard widget
    """
    return CircleStatCard(title, value, accent)
