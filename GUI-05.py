import sys
from pathlib import Path
import json
from functools import partial

from PyQt6.QtCore import Qt, QSize, QTimer, QDateTime, pyqtSignal
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QPushButton,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QSizePolicy,
    QSpacerItem,
    QDialog,
    QTabWidget,
    QFormLayout,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QDialogButtonBox,
    QGroupBox,
    QMessageBox,
    QScrollArea,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QSplitter,
    QPlainTextEdit,

)

# ------------------- THEME SYSTEM -------------------

class Theme:
    """Merkezi tema yönetimi - Tüm stiller burada tanımlanır."""
    
    # ==================== RENKLER ====================
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
    
    # Background
    BACKGROUND = "#f5f7fb"
    CARD_BG = "#ffffff"
    CODE_BG = "#111827"
    CODE_GUTTER = "#0f172a"
    
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
    
    # Font Sizes
    FONT_XS = "10px"
    FONT_SM = "11px"
    FONT_BASE = "12px"
    FONT_LG = "13px"
    FONT_XL = "14px"
    FONT_2XL = "16px"
    
    # ==================== BUTTON STYLES ====================
    
    @classmethod
    def btn_primary(cls, size: str = "md") -> str:
        """Primary buton - Ana aksiyon (Teal renk).
        Kullanım: Kaydet, Bağlan, Ana işlem butonları
        Sizes: sm, md, lg
        """
        sizes = {
            "sm": ("4px 10px", cls.FONT_SM, "6px"),
            "md": ("6px 14px", cls.FONT_BASE, "8px"),
            "lg": ("8px 20px", cls.FONT_LG, "8px"),
        }
        padding, font_size, radius = sizes.get(size, sizes["md"])
        return f"""
            QPushButton {{
                background-color: {cls.PRIMARY};
                color: #ffffff;
                border: none;
                border-radius: {radius};
                padding: {padding};
                font-size: {font_size};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {cls.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {cls.PRIMARY_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {cls.BORDER_DARK};
                color: {cls.TEXT_MUTED};
            }}
        """
    
    @classmethod
    def btn_secondary(cls, size: str = "md") -> str:
        """Secondary buton - İkincil aksiyon (Mor/Indigo renk).
        Kullanım: Run Audit, Refresh, Analyze gibi aksiyonlar
        Sizes: sm, md, lg
        """
        sizes = {
            "sm": ("4px 10px", cls.FONT_SM, "6px"),
            "md": ("6px 14px", cls.FONT_BASE, "8px"),
            "lg": ("8px 20px", cls.FONT_LG, "8px"),
        }
        padding, font_size, radius = sizes.get(size, sizes["md"])
        return f"""
            QPushButton {{
                background-color: {cls.SECONDARY};
                color: #ffffff;
                border: none;
                border-radius: {radius};
                padding: {padding};
                font-size: {font_size};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {cls.SECONDARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {cls.SECONDARY_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {cls.BORDER_DARK};
                color: {cls.TEXT_MUTED};
            }}
        """
    
    @classmethod
    def btn_danger(cls, size: str = "md") -> str:
        """Danger buton - Tehlikeli işlemler (Kırmızı).
        Kullanım: Sil, Kill Session, Remove
        Sizes: sm, md, lg
        """
        sizes = {
            "sm": ("4px 10px", cls.FONT_SM, "6px"),
            "md": ("6px 14px", cls.FONT_BASE, "8px"),
            "lg": ("8px 20px", cls.FONT_LG, "8px"),
        }
        padding, font_size, radius = sizes.get(size, sizes["md"])
        return f"""
            QPushButton {{
                background-color: {cls.DANGER};
                color: #ffffff;
                border: none;
                border-radius: {radius};
                padding: {padding};
                font-size: {font_size};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {cls.DANGER_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {cls.DANGER_PRESSED};
            }}
        """
    
    @classmethod
    def btn_ghost(cls, size: str = "md") -> str:
        """Ghost buton - Hafif görünüm, arka plan gri.
        Kullanım: Geri, İptal, Copy Script gibi düşük öncelikli
        Sizes: sm, md, lg
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
                color: {cls.TEXT_SECONDARY};
                border: 1px solid {cls.BORDER};
                border-radius: {radius};
                padding: {padding};
                font-size: {font_size};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {cls.BORDER};
                color: {cls.TEXT_PRIMARY};
                border-color: {cls.BORDER_DARK};
            }}
            QPushButton:pressed {{
                background-color: {cls.BORDER_DARK};
            }}
        """
    
    @classmethod
    def btn_outline(cls, color: str = "primary", size: str = "md") -> str:
        """Outline buton - Sadece çerçeveli, şeffaf arka plan.
        Kullanım: Alternatif aksiyonlar
        Colors: primary, secondary, danger
        Sizes: sm, md, lg
        """
        colors = {
            "primary": (cls.PRIMARY, cls.PRIMARY_HOVER, cls.PRIMARY_LIGHT),
            "secondary": (cls.SECONDARY, cls.SECONDARY_HOVER, cls.SECONDARY_LIGHT),
            "danger": (cls.DANGER, cls.DANGER_HOVER, cls.DANGER_LIGHT),
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
                background-color: {cls.SECONDARY};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: {cls.FONT_BASE};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {cls.SECONDARY_HOVER};
            }}
            QPushButton:checked {{
                background-color: {cls.SECONDARY};
            }}
            QPushButton:!checked {{
                background-color: {cls.TEXT_MUTED};
            }}
            QPushButton:!checked:hover {{
                background-color: {cls.TEXT_SECONDARY};
            }}
        """
    
    @classmethod
    def btn_small_action(cls) -> str:
        """Küçük aksiyon butonu - Card içi aksiyonlar.
        Kullanım: Edit, Test Connection gibi card içi butonlar
        """
        return f"""
            QPushButton {{
                background-color: #f8fafc;
                color: {cls.TEXT_SECONDARY};
                border: 1px solid {cls.BORDER};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: {cls.FONT_SM};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {cls.BORDER};
                color: {cls.TEXT_PRIMARY};
                border-color: {cls.BORDER_DARK};
            }}
            QPushButton:pressed {{
                background-color: {cls.BORDER_DARK};
            }}
        """
    
    @classmethod
    def btn_small_danger(cls) -> str:
        """Küçük danger butonu - Silme işlemleri.
        Kullanım: Remove, Delete gibi card içi silme butonları
        """
        return f"""
            QPushButton {{
                background-color: {cls.DANGER_LIGHT};
                color: {cls.DANGER};
                border: 1px solid #fecaca;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: {cls.FONT_SM};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #fee2e2;
                border-color: #fca5a5;
            }}
            QPushButton:pressed {{
                background-color: #fecaca;
            }}
        """
    
    @classmethod
    def btn_icon(cls, size: int = 32) -> str:
        """Icon buton - Sadece ikon içeren yuvarlak buton.
        Kullanım: Settings, Notifications gibi toolbar ikonları
        """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {cls.TEXT_SECONDARY};
                border: none;
                border-radius: {size // 2}px;
                min-width: {size}px;
                max-width: {size}px;
                min-height: {size}px;
                max-height: {size}px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {cls.PRIMARY_LIGHT};
                color: {cls.TEXT_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {cls.BORDER};
            }}
        """
    
    @classmethod
    def btn_help(cls) -> str:
        """Help butonu - Küçük yuvarlak ? işareti.
        Kullanım: Metrik kartlarında yardım ikonu
        """
        return f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {cls.BORDER_DARK};
                border-radius: 8px;
                color: {cls.TEXT_SECONDARY};
                font-weight: bold;
                font-size: 10px;
                min-width: 16px;
                max-width: 16px;
                min-height: 16px;
                max-height: 16px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: #f3f4f6;
                border-color: {cls.TEXT_MUTED};
            }}
        """
    
    # ==================== LEGACY METHODS (Geriye uyumluluk) ====================
    
    @classmethod
    def primary_button_style(cls) -> str:
        """Legacy: Primary buton stili."""
        return cls.btn_primary("md")
    
    @classmethod
    def secondary_button_style(cls) -> str:
        """Legacy: Secondary buton stili."""
        return cls.btn_secondary("md")
    
    @classmethod
    def danger_text_button_style(cls) -> str:
        """Legacy: Danger text butonu."""
        return cls.btn_small_danger()
    
    @classmethod
    def auto_refresh_button_style(cls) -> str:
        """Legacy: Auto-refresh toggle butonu."""
        return cls.btn_toggle()
    
    @classmethod
    def refresh_button_style(cls) -> str:
        """Legacy: Refresh butonu."""
        return cls.btn_secondary("md")
    
    # ==================== TABLE STYLES ====================
    
    @classmethod
    def table_style(cls) -> str:
        """QTableWidget için standart stil.
        
        Özellikler:
        - Header: Sola dayalı, bold, gri arka plan
        - Satırlar: Açık alt çizgi, hover efekti
        - Seçim: Mor tonlu highlight
        """
        return f"""
            QTableWidget {{
                border: none;
                background-color: transparent;
                gridline-color: {cls.BORDER};
                font-size: {cls.FONT_SM};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {cls.BORDER_LIGHT};
                color: {cls.TEXT_PRIMARY};
            }}
            QTableWidget::item:hover {{
                background-color: #f9fafb;
            }}
            QTableWidget::item:selected {{
                background-color: {cls.SECONDARY_LIGHT};
                color: {cls.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: #f8fafc;
                color: {cls.TEXT_HEADER};
                padding: 10px 12px;
                border: none;
                border-bottom: 2px solid {cls.BORDER};
                font-weight: 700;
                font-size: {cls.FONT_SM};
                text-align: left;
            }}
            QHeaderView::section:hover {{
                background-color: #f1f5f9;
            }}
            QScrollBar:vertical {{
                width: 8px;
                background-color: transparent;
            }}
            QScrollBar::handle:vertical {{
                background-color: {cls.BORDER_DARK};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {cls.TEXT_MUTED};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """
    
    @classmethod
    def table_style_compact(cls) -> str:
        """Kompakt tablo stili - daha az padding."""
        return f"""
            QTableWidget {{
                border: none;
                background-color: transparent;
                gridline-color: {cls.BORDER};
                font-size: {cls.FONT_SM};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {cls.BORDER_LIGHT};
                color: {cls.TEXT_PRIMARY};
            }}
            QTableWidget::item:hover {{
                background-color: #f9fafb;
            }}
            QTableWidget::item:selected {{
                background-color: {cls.SECONDARY_LIGHT};
                color: {cls.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: #f8fafc;
                color: {cls.TEXT_HEADER};
                padding: 6px 8px;
                border: none;
                border-bottom: 2px solid {cls.BORDER};
                font-weight: 700;
                font-size: {cls.FONT_XS};
                text-align: left;
            }}
            QScrollBar:vertical {{
                width: 6px;
                background-color: transparent;
            }}
            QScrollBar::handle:vertical {{
                background-color: {cls.BORDER_DARK};
                border-radius: 3px;
            }}
        """
    
    @classmethod
    def table_style_bordered(cls) -> str:
        """Çerçeveli tablo stili - card içinde kullanım için."""
        return f"""
            QTableWidget {{
                border: 1px solid {cls.BORDER};
                border-radius: 8px;
                background-color: {cls.CARD_BG};
                gridline-color: {cls.BORDER};
                font-size: {cls.FONT_SM};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {cls.BORDER_LIGHT};
                color: {cls.TEXT_PRIMARY};
            }}
            QTableWidget::item:hover {{
                background-color: #f9fafb;
            }}
            QTableWidget::item:selected {{
                background-color: {cls.SECONDARY_LIGHT};
                color: {cls.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: #f8fafc;
                color: {cls.TEXT_HEADER};
                padding: 10px 12px;
                border: none;
                border-bottom: 2px solid {cls.BORDER};
                font-weight: 700;
                font-size: {cls.FONT_SM};
                text-align: left;
            }}
            QHeaderView::section:first {{
                border-top-left-radius: 8px;
            }}
            QHeaderView::section:last {{
                border-top-right-radius: 8px;
            }}
            QScrollBar:vertical {{
                width: 8px;
                background-color: transparent;
            }}
            QScrollBar::handle:vertical {{
                background-color: {cls.BORDER_DARK};
                border-radius: 4px;
            }}
        """
    
    @staticmethod
    def setup_table(table, stretch_last: bool = True, row_height: int = 36, compact: bool = False) -> None:
        """QTableWidget için standart ayarları uygular.
        
        Args:
            table: QTableWidget instance
            stretch_last: Son sütunu genişlet
            row_height: Satır yüksekliği (varsayılan 36px)
            compact: Kompakt stil kullan (daha küçük padding)
        """
        from PyQt6.QtWidgets import QAbstractItemView, QHeaderView
        from PyQt6.QtCore import Qt
        
        # Davranış ayarları
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(False)
        table.setShowGrid(False)
        
        # Header ayarları - SOLA DAYALI ve BOLD
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(row_height)
        table.horizontalHeader().setHighlightSections(False)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        if stretch_last:
            table.horizontalHeader().setStretchLastSection(True)
        
        # Sütun genişlikleri içeriğe göre ayarla
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Stil uygula
        if compact:
            table.setStyleSheet(Theme.table_style_compact())
        else:
            table.setStyleSheet(Theme.table_style())
    
    @staticmethod
    def setup_readonly_table(table, row_height: int = 32) -> None:
        """Salt okunur tablo için ayarlar (seçim yok).
        
        Args:
            table: QTableWidget instance  
            row_height: Satır yüksekliği
        """
        from PyQt6.QtWidgets import QAbstractItemView, QHeaderView
        from PyQt6.QtCore import Qt
        
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setShowGrid(False)
        
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(row_height)
        table.horizontalHeader().setHighlightSections(False)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        table.setStyleSheet(Theme.table_style_compact())
    
    # ==================== CARD STYLES ====================
    
    @classmethod
    def card_style(cls, object_name: str = "Card") -> str:
        """Card container için ortak stil (10px radius)."""
        return f"""
            #{object_name} {{
                background-color: {cls.CARD_BG};
                border: 1px solid {cls.BORDER};
                border-radius: 10px;
            }}
        """
    
    @classmethod
    def card_style_8(cls, object_name: str = "Card") -> str:
        """Card container için 8px radius stil."""
        return f"""
            #{object_name} {{
                background-color: {cls.CARD_BG};
                border: 1px solid {cls.BORDER};
                border-radius: 8px;
            }}
        """
    
    @classmethod
    def list_widget_style(cls) -> str:
        """QListWidget için ortak stil."""
        return f"""
            QListWidget {{
                border: 1px solid {cls.BORDER};
                border-radius: 4px;
                background-color: {cls.CARD_BG};
                outline: none;
            }}
            QListWidget::item {{
                padding: 6px 6px;
                margin: 0px 2px;
                border-radius: 4px;
                font-size: {cls.FONT_BASE};
            }}
            QListWidget::item:hover {{
                background-color: #f3f4f6;
                border: 1px solid {cls.BORDER_DARK};
            }}
            QListWidget::item:selected {{
                background-color: #dbeafe;
                color: #0369a1;
                font-weight: 500;
                border: 1px solid #06b6d4;
            }}
            QScrollBar:vertical {{
                width: 6px;
                background-color: transparent;
            }}
            QScrollBar::handle:vertical {{
                background-color: {cls.BORDER_DARK};
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {cls.TEXT_MUTED};
            }}
        """
    
    @classmethod
    def queries_list_style(cls) -> str:
        """Query listesi için stil."""
        return f"""
            QListWidget {{
                border: none;
                background-color: transparent;
                outline: none;
            }}
            QListWidget::item {{
                padding: 0px;
                margin: 0px;
                border: none;
            }}
            QScrollBar:vertical {{
                width: 6px;
                background-color: transparent;
            }}
            QScrollBar::handle:vertical {{
                background-color: {cls.BORDER_DARK};
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {cls.TEXT_MUTED};
            }}
        """
    
    @classmethod
    def search_input_style(cls) -> str:
        """Arama input stili."""
        return f"""
            QLineEdit {{
                border: 1px solid {cls.BORDER};
                border-radius: 4px;
                padding: 6px 8px;
                font-size: {cls.FONT_SM};
            }}
            QLineEdit:focus {{
                border: 1px solid #3b82f6;
            }}
        """
    
    @classmethod
    def code_editor_style(cls) -> str:
        """Kod editörü stili."""
        return f"""
            QPlainTextEdit {{
                background-color: {cls.CODE_BG};
                color: {cls.TEXT_CODE};
                border: 1px solid {cls.BORDER_CODE};
                border-radius: 6px;
                padding: 10px;
                font-family: 'Courier New';
                font-size: {cls.FONT_SM};
            }}
        """
    
    @classmethod
    def tab_widget_style(cls) -> str:
        """Tab widget stili."""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {cls.BORDER};
                border-radius: 8px;
                background: {cls.CARD_BG};
            }}
            QTabBar::tab {{
                background-color: #f3f4f6;
                border: 1px solid {cls.BORDER};
                border-bottom: none;
                padding: 6px 12px;
                margin-right: 4px;
                font-size: {cls.FONT_SM};
            }}
            QTabBar::tab:selected {{
                background-color: {cls.SECONDARY};
                color: #ffffff;
            }}
        """
    
    @classmethod
    def splitter_style(cls) -> str:
        """Splitter stili."""
        return f"""
            QSplitter {{
                background-color: transparent;
            }}
            QSplitter::handle {{
                background-color: {cls.BORDER_DARK};
                width: 8px;
                margin: 0px 2px;
                border-radius: 2px;
            }}
            QSplitter::handle:hover {{
                background-color: #3b82f6;
            }}
        """
    
    @classmethod
    def provider_card_style(cls) -> str:
        """Provider/Connection card stili."""
        return f"""
            QFrame#ProviderCard {{
                background-color: {cls.CARD_BG};
                border: 1px solid {cls.BORDER_LIGHT};
                border-radius: 8px;
                padding: 12px;
            }}
        """
    
    @classmethod
    def connection_card_style(cls) -> str:
        """Connection card stili."""
        return f"""
            QFrame#ConnectionCard {{
                background-color: {cls.CARD_BG};
                border: 1px solid {cls.BORDER_LIGHT};
                border-radius: 8px;
                padding: 12px;
            }}
        """
    
    @classmethod
    def session_detail_box_style(cls) -> str:
        """Session detail box stili."""
        return f"""
            background-color: #f8fafc;
            border: 1px solid {cls.BORDER};
            border-radius: 6px;
            padding: 6px 8px;
            color: {cls.TEXT_SECONDARY};
            font-size: {cls.FONT_SM};
        """
    
    @classmethod
    def query_box_style(cls) -> str:
        """Query box stili."""
        return f"""
            QPlainTextEdit {{
                background-color: #f3f4f6;
                border: 1px solid {cls.BORDER};
                border-radius: 6px;
                padding: 8px;
                color: {cls.TEXT_SECONDARY};
                font-size: {cls.FONT_SM};
            }}
        """


# ------------------- LANGUAGE SYSTEM -------------------

# Custom ComboBox that opens upward
class TopComboBox(QComboBox):
    """ComboBox that opens with upward preference."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaxVisibleItems(10)


# ------------------- LANGUAGE SYSTEM -------------------

LOCALES_DIR = Path(__file__).parent / "locales"
CURRENT_LANGUAGE = "English"
TRANSLATIONS = {}


def create_circle_stat_card(title: str, value: str, accent: str) -> QFrame:
    wrapper = QFrame()
    wrapper.setStyleSheet("background-color: transparent; border: none;")
    wrapper_layout = QVBoxLayout(wrapper)
    wrapper_layout.setContentsMargins(0, 0, 0, 0)
    wrapper_layout.setSpacing(6)
    wrapper_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

    circle = QFrame()
    circle.setFixedSize(90, 90)
    circle.setStyleSheet("""
        QFrame {
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 45px;
        }
    """)
    circle_layout = QVBoxLayout(circle)
    circle_layout.setContentsMargins(0, 0, 0, 0)
    circle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    value_label = QLabel(value)
    value_label.setStyleSheet(
        f"color: {accent}; font-size: 18px; font-weight: 700; background: transparent; border: none;"
    )
    value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    circle_layout.addWidget(value_label)

    title_label = QLabel(title)
    title_label.setStyleSheet("color: #6b7280; font-size: 10px;")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    wrapper_layout.addWidget(circle)
    wrapper_layout.addWidget(title_label)
    return wrapper


def load_language(lang: str) -> dict:
    """Load language file from locales directory."""
    global CURRENT_LANGUAGE, TRANSLATIONS
    
    lang_map = {
        "English": "en.json",
        "Turkish": "tr.json",
        "German": "de.json",
    }
    
    filename = lang_map.get(lang, "en.json")
    filepath = LOCALES_DIR / filename
    
    try:
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                TRANSLATIONS = json.load(f)
                CURRENT_LANGUAGE = lang
                return TRANSLATIONS
    except Exception as e:
        print(f"[WARN] Language load failed: {e}")
    
    return {}


def t(key: str, default: str = "") -> str:
    """Translate a key to current language."""
    keys = key.split(".")
    value = TRANSLATIONS
    
    try:
        for k in keys:
            value = value[k]
        return str(value)
    except (KeyError, TypeError):
        return default or key


# ------------------- SETTINGS (JSON) -------------------

APP_DIR = Path.home() / ".db_performance_studio"
SETTINGS_FILE = APP_DIR / "settings.json"

DEFAULT_SETTINGS = {
    "general": {
        "language": "English",
        "autostart_minimized": False,
        "telemetry": False,
        "auto_update": True,
        "version": "1.0.0",
        "build": "20260127",
        "copyright": "© 2026 DB Performance Studio",
        "license": "Free",
        "expire_date": "",
    },
    "llm": {
        "provider": "Local (HF Transformers)",
        "model": "mistral-7b-instruct",
        "context_window": 4096,
        "temperature": 0.7,
        "stream": True,
        "custom_system_prompt": False,
        "providers": [],
    },
    "database": {
        "engine": "SQL Server",
        "environment": "Development",
        "connection_profile": "Default Profile",
        "integrated_auth": True,
        "readonly": False,
        "connections": [],
    },
    "appearance": {
        "theme": "system",
        "accent": "teal",
        "font_size": 10,
        "compact": False,
        "animations": True,
    },
}


def load_settings() -> dict:
    """settings.json dosyasını oku, yoksa varsayılanı döndür."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged = json.loads(json.dumps(DEFAULT_SETTINGS))
                for section, values in data.items():
                    if section in merged and isinstance(values, dict):
                        merged[section].update(values)
                return merged
    except Exception as e:
        print(f"[WARN] Settings load failed: {e}")

    return json.loads(json.dumps(DEFAULT_SETTINGS))


def save_settings(settings: dict) -> None:
    """Ayarları settings.json dosyasına yaz."""
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] Settings save failed: {e}")


# ------------------- SETTINGS DIALOG -------------------


class SettingsDialog(QDialog):
    language_changed = pyqtSignal(str)
    
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("settings.title", "Settings"))
        self.resize(640, 420)

        # Dışarıdan gelen settings referansını tutuyoruz
        self.settings = settings
        self.parent_window = parent

        self._init_ui()
        self._load_from_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("SettingsTabs")

        # Sekme widget'larını oluşturup referans tutuyoruz
        self.tab_general = QWidget()
        self.tab_llm = QWidget()
        self.tab_db = QWidget()
        self.tab_appearance = QWidget()

        self._build_general_tab()
        self._build_llm_tab()
        self._build_database_tab()
        self._build_appearance_tab()

        self.tabs.addTab(self.tab_general, "General")
        self.tabs.addTab(self.tab_llm, "LLM")
        self.tabs.addTab(self.tab_db, "Database")
        self.tabs.addTab(self.tab_appearance, "Appearance")

        main_layout.addWidget(self.tabs)

        # Butonlar: OK / Cancel / Apply
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        self.button_box.accepted.connect(self._handle_ok)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._handle_apply
        )

        main_layout.addWidget(self.button_box)

    # ---------- TAB UI OLUŞTURMA ----------

    def _build_general_tab(self):
        layout = QFormLayout(self.tab_general)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setVerticalSpacing(10)

        # Settings section
        self.lbl_language = QLabel(t("settings.language", "Language:"))
        self.cmb_language = TopComboBox()
        self.cmb_language.addItems(["English", "Turkish", "German"])
        self.cmb_language.currentTextChanged.connect(self._on_language_changed)

        self.chk_autostart = QCheckBox(t("settings.autostart_minimized", "Start application minimized in system tray"))
        self.chk_telemetry = QCheckBox(t("settings.telemetry", "Allow anonymous usage analytics"))
        self.chk_update = QCheckBox(t("settings.auto_update", "Check for updates automatically"))

        layout.addRow(self.lbl_language, self.cmb_language)
        layout.addRow("", self.chk_autostart)
        layout.addRow("", self.chk_telemetry)
        layout.addRow("", self.chk_update)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addRow("", sep)

        # Application Info section
        self.lbl_app_info = QLabel(t("settings.application_info", "Application Info"))
        app_info_font = self.lbl_app_info.font()
        app_info_font.setBold(True)
        app_info_font.setPointSize(app_info_font.pointSize() + 1)
        self.lbl_app_info.setFont(app_info_font)
        layout.addRow("", self.lbl_app_info)

        self.lbl_version = QLabel()
        self.lbl_build = QLabel()
        self.lbl_copyright = QLabel()
        
        self.lbl_license = QLabel(t("settings.license", "License:"))
        self.cmb_license = TopComboBox()
        self.cmb_license.addItems(["Free", "Trial", "Commercial"])
        
        self.lbl_expire = QLabel(t("settings.expire_date", "Expire Date:"))
        self.txt_expire_date = QLineEdit()
        self.txt_expire_date.setPlaceholderText("YYYY-MM-DD (leave blank if no expiration)")

        layout.addRow(t("settings.version", "Version:"), self.lbl_version)
        layout.addRow(t("settings.build", "Build:"), self.lbl_build)
        layout.addRow(t("settings.copyright", "Copyright:"), self.lbl_copyright)
        layout.addRow(self.lbl_license, self.cmb_license)
        layout.addRow(self.lbl_expire, self.txt_expire_date)

    def _build_llm_tab(self):
        layout = QVBoxLayout(self.tab_llm)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        self.lbl_llm_providers = QLabel(t("settings.llm_providers", "LLM Providers"))
        title_font = self.lbl_llm_providers.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 1)
        self.lbl_llm_providers.setFont(title_font)
        header.addWidget(self.lbl_llm_providers)
        header.addStretch()
        
        self.btn_add_provider = QPushButton(t("settings.add_new_provider", "+ Add New Provider"))
        self.btn_add_provider.setFixedHeight(32)
        self.btn_add_provider.setObjectName("AddConnectionButton")
        self.btn_add_provider.clicked.connect(self._handle_add_provider)
        header.addWidget(self.btn_add_provider)
        
        layout.addLayout(header)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)
        
        # Providers scroll area
        scroll = QFrame()
        scroll.setObjectName("ProvidersScroll")
        self.providers_layout = QVBoxLayout(scroll)
        self.providers_layout.setContentsMargins(0, 0, 0, 0)
        self.providers_layout.setSpacing(8)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        layout.addWidget(scroll_area)
        
        self.providers_layout.addStretch()

    def _build_database_tab(self):
        layout = QVBoxLayout(self.tab_db)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        self.lbl_db_connections = QLabel(t("settings.database_connections", "Database Connections"))
        title_font = self.lbl_db_connections.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 1)
        self.lbl_db_connections.setFont(title_font)
        header.addWidget(self.lbl_db_connections)
        header.addStretch()
        
        self.btn_add_connection = QPushButton(t("settings.add_new_connection", "+ Add New Connection"))
        self.btn_add_connection.setFixedHeight(32)
        self.btn_add_connection.setObjectName("AddConnectionButton")
        self.btn_add_connection.clicked.connect(self._handle_add_connection)
        header.addWidget(self.btn_add_connection)
        
        layout.addLayout(header)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)
        
        # Connections scroll area
        scroll = QFrame()
        scroll.setObjectName("ConnectionsScroll")
        self.connections_layout = QVBoxLayout(scroll)
        self.connections_layout.setContentsMargins(0, 0, 0, 0)
        self.connections_layout.setSpacing(8)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        layout.addWidget(scroll_area)
        
        self.connections_layout.addStretch()

    def _build_appearance_tab(self):
        layout = QFormLayout(self.tab_appearance)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setVerticalSpacing(10)

        # Theme combo box - dynamic based on language
        self.theme_keys = ["system", "light", "dark", "solarized"]
        self.cmb_theme = TopComboBox()
        self._populate_theme_combo()

        # Accent combo box - dynamic based on language
        self.accent_keys = ["teal", "blue", "purple", "orange", "green"]
        self.cmb_accent = TopComboBox()
        self._populate_accent_combo()

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 18)

        self.chk_compact = QCheckBox(t("settings.compact_layout", "Use compact layout (denser tables)"))
        self.chk_animations = QCheckBox(t("settings.enable_animations", "Enable subtle animations"))

        self.lbl_theme = QLabel(t("settings.theme", "Theme:"))
        self.lbl_accent = QLabel(t("settings.appearance", "Accent color:"))
        self.lbl_font_size = QLabel(t("settings.appearance", "Base font size:"))

        layout.addRow(self.lbl_theme, self.cmb_theme)
        layout.addRow(self.lbl_accent, self.cmb_accent)
        layout.addRow(self.lbl_font_size, self.spin_font_size)
        layout.addRow("", self.chk_compact)
        layout.addRow("", self.chk_animations)
    
    def _populate_theme_combo(self):
        """Populate theme combo box with translated options."""
        self.cmb_theme.clear()
        for key in self.theme_keys:
            display_text = t(f"themes.{key}", key.capitalize())
            self.cmb_theme.addItem(display_text, key)
    
    def _populate_accent_combo(self):
        """Populate accent combo box with translated options."""
        self.cmb_accent.clear()
        for key in self.accent_keys:
            display_text = t(f"accents.{key}", key.capitalize())
            self.cmb_accent.addItem(display_text, key)

    # ---------- SETTINGS <-> UI SENKRON ----------

    def _load_from_settings(self):
        """self.settings içinden widget'ları doldur."""
        s = self.settings

        # General
        lang = s["general"].get("language", "English")
        idx = self.cmb_language.findText(lang)
        if idx >= 0:
            self.cmb_language.setCurrentIndex(idx)

        self.chk_autostart.setChecked(s["general"].get("autostart_minimized", False))
        self.chk_telemetry.setChecked(s["general"].get("telemetry", False))
        self.chk_update.setChecked(s["general"].get("auto_update", True))

        # Application Info
        self.lbl_version.setText(s["general"].get("version", "1.0.0"))
        self.lbl_build.setText(s["general"].get("build", "20260127"))
        self.lbl_copyright.setText(s["general"].get("copyright", "© 2026 DB Performance Studio"))
        
        license_type = s["general"].get("license", "Free")
        idx = self.cmb_license.findText(license_type)
        if idx >= 0:
            self.cmb_license.setCurrentIndex(idx)
        
        self.txt_expire_date.setText(s["general"].get("expire_date", ""))

        # LLM - Load providers
        self._refresh_providers_display()

        # Database - Load connections
        self._refresh_connections_display()

        # Appearance
        theme = s["appearance"].get("theme", "system")
        idx = self.cmb_theme.findData(theme)
        if idx >= 0:
            self.cmb_theme.setCurrentIndex(idx)

        accent = s["appearance"].get("accent", "teal")
        idx = self.cmb_accent.findData(accent)
        if idx >= 0:
            self.cmb_accent.setCurrentIndex(idx)

        self.spin_font_size.setValue(int(s["appearance"].get("font_size", 10)))
        self.chk_compact.setChecked(s["appearance"].get("compact", False))
        self.chk_animations.setChecked(s["appearance"].get("animations", True))

    def _apply_to_settings(self):
        """Widget değerlerini self.settings içine yaz."""
        s = self.settings

        s["general"]["language"] = self.cmb_language.currentText()
        s["general"]["autostart_minimized"] = self.chk_autostart.isChecked()
        s["general"]["telemetry"] = self.chk_telemetry.isChecked()
        s["general"]["auto_update"] = self.chk_update.isChecked()
        
        # Application Info
        s["general"]["license"] = self.cmb_license.currentText()
        s["general"]["expire_date"] = self.txt_expire_date.text().strip()

        # LLM providers are already stored in self.settings during add/edit/delete operations

        s["appearance"]["theme"] = self.cmb_theme.currentData() or "system"
        s["appearance"]["accent"] = self.cmb_accent.currentData() or "teal"
        s["appearance"]["font_size"] = int(self.spin_font_size.value())
        s["appearance"]["compact"] = self.chk_compact.isChecked()
        s["appearance"]["animations"] = self.chk_animations.isChecked()

    # ---------- BUTON HANDLER'LARI ----------

    def _handle_apply(self):
        self._apply_to_settings()
        save_settings(self.settings)
        self._notify_language_change()

    def _handle_ok(self):
        self._apply_to_settings()
        save_settings(self.settings)
        self._notify_language_change()
        self.accept()

    def _on_language_changed(self, lang: str):
        """Handle language change - update TRANSLATIONS and UI strings."""
        load_language(lang)
        self._update_dialog_strings()
    
    def _update_dialog_strings(self):
        """Update all dialog UI strings based on current language."""
        # Window title
        self.setWindowTitle(t("settings.title", "Settings"))
        
        # Tab names
        self.tabs.setTabText(0, t("settings.general", "General"))
        self.tabs.setTabText(1, t("settings.llm", "LLM"))
        self.tabs.setTabText(2, t("settings.database", "Database"))
        self.tabs.setTabText(3, t("settings.appearance", "Appearance"))
        
        # General tab
        self.lbl_language.setText(t("settings.language", "Language:"))
        self.chk_autostart.setText(t("settings.autostart_minimized", "Start application minimized in system tray"))
        self.chk_telemetry.setText(t("settings.telemetry", "Allow anonymous usage analytics"))
        self.chk_update.setText(t("settings.auto_update", "Check for updates automatically"))
        self.lbl_app_info.setText(t("settings.application_info", "Application Info"))
        self.lbl_license.setText(t("settings.license", "License:"))
        self.lbl_expire.setText(t("settings.expire_date", "Expire Date:"))
        
        # LLM tab
        self.lbl_llm_providers.setText(t("settings.llm_providers", "LLM Providers"))
        self.btn_add_provider.setText(t("settings.add_new_provider", "+ Add New Provider"))
        
        # Database tab
        self.lbl_db_connections.setText(t("settings.database_connections", "Database Connections"))
        self.btn_add_connection.setText(t("settings.add_new_connection", "+ Add New Connection"))
        
        # Appearance tab
        self.lbl_theme.setText(t("settings.theme", "Theme:"))
        self.lbl_accent.setText(t("settings.appearance", "Accent color:"))
        self.lbl_font_size.setText(t("settings.appearance", "Base font size:"))
        self.chk_compact.setText(t("settings.compact_layout", "Use compact layout (denser tables)"))
        self.chk_animations.setText(t("settings.enable_animations", "Enable subtle animations"))
        
        # Repopulate theme and accent combos with translated text
        current_theme = self.cmb_theme.currentData()
        current_accent = self.cmb_accent.currentData()
        self._populate_theme_combo()
        self._populate_accent_combo()
        
        # Restore selected values
        if current_theme:
            idx = self.cmb_theme.findData(current_theme)
            if idx >= 0:
                self.cmb_theme.setCurrentIndex(idx)
        if current_accent:
            idx = self.cmb_accent.findData(current_accent)
            if idx >= 0:
                self.cmb_accent.setCurrentIndex(idx)
        
        # Button box
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText(t("settings.ok", "OK"))
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(t("settings.cancel", "Cancel"))
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).setText(t("settings.apply", "Apply"))
    
    def _notify_language_change(self):
        """Notify parent window about language change."""
        if self.parent_window and hasattr(self.parent_window, '_on_language_changed'):
            self.parent_window._on_language_changed()

    # ---------- LLM PROVIDER HANDLERS ----------

    def _refresh_providers_display(self):
        """Display saved LLM providers as cards."""
        # Clear existing cards
        while self.providers_layout.count() > 1:  # Keep stretch
            item = self.providers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        providers = self.settings.get("llm", {}).get("providers", [])
        
        if not providers:
            no_prov_label = QLabel("No providers configured yet.")
            no_prov_label.setStyleSheet("color: #8b93a2; font-style: italic;")
            self.providers_layout.insertWidget(0, no_prov_label)
        else:
            for idx, prov in enumerate(providers):
                card = self._create_provider_card(idx, prov)
                self.providers_layout.insertWidget(idx, card)
    
    def _create_provider_card(self, idx: int, prov: dict) -> QFrame:
        """Create a provider card widget."""
        card = QFrame()
        card.setObjectName("ProviderCard")
        card.setStyleSheet(Theme.provider_card_style())
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header row: name and buttons
        header = QHBoxLayout()
        
        name_label = QLabel(prov.get("name", "Unknown"))
        name_font = name_label.font()
        name_font.setBold(True)
        name_label.setFont(name_font)
        header.addWidget(name_label)
        
        # Default badge
        if prov.get("is_default", False):
            default_badge = QLabel("DEFAULT")
            default_badge.setStyleSheet("""
                QLabel {
                    background-color: #e8f5e9;
                    color: #2e7d32;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: 600;
                }
            """)
            header.addWidget(default_badge)
        
        header.addStretch()
        
        btn_test = QPushButton(t("connection.test", "Test"))
        btn_test.setFixedWidth(50)
        btn_test.setFixedHeight(28)
        btn_test.setStyleSheet(Theme.btn_small_action())
        btn_test.clicked.connect(partial(self._handle_test_provider, idx))
        header.addWidget(btn_test)
        
        btn_edit = QPushButton(t("common.edit", "Edit"))
        btn_edit.setFixedWidth(50)
        btn_edit.setFixedHeight(28)
        btn_edit.setStyleSheet(Theme.btn_small_action())
        btn_edit.clicked.connect(partial(self._handle_edit_provider, idx))
        header.addWidget(btn_edit)
        
        btn_delete = QPushButton(t("common.remove", "Remove"))
        btn_delete.setFixedWidth(60)
        btn_delete.setFixedHeight(28)
        btn_delete.setStyleSheet(Theme.btn_small_danger())
        btn_delete.clicked.connect(partial(self._handle_delete_provider, idx))
        header.addWidget(btn_delete)
        
        layout.addLayout(header)
        
        # Details
        prov_type = prov.get("provider_type", "Unknown")
        model = prov.get("model", "N/A")
        details = QLabel(f"{prov_type} • Model: {model}")
        details.setStyleSheet("color: #6b7380; font-size: 11px;")
        layout.addWidget(details)
        
        return card
    
    def _handle_add_provider(self):
        """Open dialog to add new provider."""
        dlg = LLMProviderDialog(self)
        if dlg.exec():
            if "providers" not in self.settings.get("llm", {}):
                self.settings["llm"]["providers"] = []
            
            self.settings["llm"]["providers"].append(dlg.data)
            self._refresh_providers_display()
    
    def _handle_edit_provider(self, idx: int):
        """Open dialog to edit existing provider."""
        providers = self.settings.get("llm", {}).get("providers", [])
        if 0 <= idx < len(providers):
            prov_data = providers[idx].copy()
            dlg = LLMProviderDialog(self, prov_data)
            if dlg.exec():
                self.settings["llm"]["providers"][idx] = dlg.data
                self._refresh_providers_display()
    
    def _handle_delete_provider(self, idx: int):
        """Delete a provider."""
        providers = self.settings.get("llm", {}).get("providers", [])
        if 0 <= idx < len(providers):
            reply = QMessageBox.question(
                self,
                t("common.confirm", "Confirm"),
                t("settings.confirm_delete_provider", "Delete provider '{name}'?").format(
                    name=providers[idx].get("name", "Unknown")
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                del self.settings["llm"]["providers"][idx]
                self._refresh_providers_display()
    
    def _handle_test_provider(self, idx: int):
        """Test a provider connection."""
        providers = self.settings.get("llm", {}).get("providers", [])
        if 0 <= idx < len(providers):
            prov = providers[idx]
            msg = f"Testing provider: {prov.get('name', 'Unknown')}\nType: {prov.get('provider_type', 'N/A')}\nModel: {prov.get('model', 'N/A')}\n\nTest connection logic will be implemented here."
            QMessageBox.information(self, "Test Provider", msg)

    # ---------- DATABASE CONNECTION HANDLERS ----------

    def _refresh_connections_display(self):
        """Display saved connections as cards."""
        # Clear existing cards
        while self.connections_layout.count() > 1:  # Keep stretch
            item = self.connections_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        connections = self.settings.get("database", {}).get("connections", [])
        
        if not connections:
            no_conn_label = QLabel("No connections configured yet.")
            no_conn_label.setStyleSheet("color: #8b93a2; font-style: italic;")
            self.connections_layout.insertWidget(0, no_conn_label)
        else:
            for idx, conn in enumerate(connections):
                card = self._create_connection_card(idx, conn)
                self.connections_layout.insertWidget(idx, card)
    
    def _create_connection_card(self, idx: int, conn: dict) -> QFrame:
        """Create a connection card widget."""
        card = QFrame()
        card.setObjectName("ConnectionCard")
        card.setStyleSheet(Theme.connection_card_style())
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header row: name and buttons
        header = QHBoxLayout()
        
        name_label = QLabel(conn.get("name", "Unknown"))
        name_font = name_label.font()
        name_font.setBold(True)
        name_label.setFont(name_font)
        header.addWidget(name_label)
        
        env_badge = QLabel(conn.get("environment", ""))
        env_badge.setStyleSheet("""
            QLabel {
                background-color: #e4f0f4;
                color: #0e8a9d;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
            }
        """)
        header.addWidget(env_badge)
        
        header.addStretch()
        
        btn_edit = QPushButton(t("common.edit", "Edit"))
        btn_edit.setFixedWidth(50)
        btn_edit.setFixedHeight(28)
        btn_edit.setStyleSheet(Theme.btn_small_action())
        btn_edit.clicked.connect(partial(self._handle_edit_connection, idx))
        header.addWidget(btn_edit)
        
        btn_delete = QPushButton(t("common.delete", "Delete"))
        btn_delete.setFixedWidth(60)
        btn_delete.setFixedHeight(28)
        btn_delete.setStyleSheet(Theme.btn_small_danger())
        btn_delete.clicked.connect(partial(self._handle_delete_connection, idx))
        header.addWidget(btn_delete)
        
        layout.addLayout(header)
        
        # Details
        details = QLabel(
            f"{conn.get('engine', 'N/A')} • {conn.get('server', 'N/A')} • {conn.get('database', 'N/A')}"
        )
        details.setStyleSheet("color: #6b7380; font-size: 11px;")
        layout.addWidget(details)
        
        return card
    
    def _handle_add_connection(self):
        """Open dialog to add new connection."""
        dlg = ConnectionEditorDialog(self)
        if dlg.exec():
            connections = self.settings.get("database", {}).get("connections", [])
            if "connections" not in self.settings.get("database", {}):
                self.settings["database"]["connections"] = []
            
            self.settings["database"]["connections"].append(dlg.data)
            self._refresh_connections_display()
    
    def _handle_edit_connection(self, idx: int):
        """Open dialog to edit existing connection."""
        connections = self.settings.get("database", {}).get("connections", [])
        if 0 <= idx < len(connections):
            conn_data = connections[idx].copy()
            dlg = ConnectionEditorDialog(self, conn_data)
            if dlg.exec():
                self.settings["database"]["connections"][idx] = dlg.data
                self._refresh_connections_display()
    
    def _handle_delete_connection(self, idx: int):
        """Delete a connection."""
        connections = self.settings.get("database", {}).get("connections", [])
        if 0 <= idx < len(connections):
            reply = QMessageBox.question(
                self,
                t("common.confirm", "Confirm"),
                t("settings.confirm_delete_connection", "Delete connection '{name}'?").format(
                    name=connections[idx].get("name", "Unknown")
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                del self.settings["database"]["connections"][idx]
                self._refresh_connections_display()


# LLMProviderDialog Arayuzu
class LLMProviderDialog(QDialog):
    """LLM provider ekleme / düzenleme dialog'u."""

    def __init__(self, parent=None, data: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("LLM Provider")
        self.resize(600, 400)

        self.data = data or {}
        self._init_ui()
        self._load_from_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Provider info
        info_box = QGroupBox("Provider Information")
        info_layout = QFormLayout(info_box)
        info_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        info_layout.setVerticalSpacing(8)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g., DeepSeek API")

        self.cmb_type = TopComboBox()
        self.cmb_type.addItems(["DeepSeek", "Ollama", "OpenAI", "Local (HF Transformers)"])
        self.cmb_type.currentTextChanged.connect(self._on_provider_type_changed)

        info_layout.addRow("Provider Name:", self.txt_name)
        info_layout.addRow("Provider Type:", self.cmb_type)

        # Connection details
        conn_box = QGroupBox("Connection Details")
        self.conn_layout = QFormLayout(conn_box)
        self.conn_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.conn_layout.setVerticalSpacing(8)

        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText("API Key")

        self.txt_host = QLineEdit()
        self.txt_host.setPlaceholderText("e.g., http://localhost:11434")

        self.txt_model = QLineEdit()
        self.txt_model.setPlaceholderText("e.g., deepseek-chat, mistral-7b")

        self.chk_default = QCheckBox("Set as default provider")

        self.row_api_key = self.conn_layout.rowCount()
        self.conn_layout.addRow("API Key:", self.txt_api_key)
        
        self.row_host = self.conn_layout.rowCount()
        self.conn_layout.addRow("Host/URL:", self.txt_host)
        
        self.row_model = self.conn_layout.rowCount()
        self.conn_layout.addRow("Model:", self.txt_model)
        
        self.conn_layout.addRow("", self.chk_default)

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_test = QPushButton(t("connection.test", "Test Connection"))
        btn_box.addButton(self.btn_test, QDialogButtonBox.ButtonRole.ActionRole)

        btn_box.accepted.connect(self._handle_save)
        btn_box.rejected.connect(self.reject)
        self.btn_test.clicked.connect(self._handle_test)

        main_layout.addWidget(info_box)
        main_layout.addWidget(conn_box)
        main_layout.addWidget(btn_box)

        self._on_provider_type_changed()

    def _on_provider_type_changed(self):
        """Show/hide fields based on provider type."""
        prov_type = self.cmb_type.currentText()
        
        # Show API Key for: DeepSeek, OpenAI
        self._set_form_row_visible(self.row_api_key, prov_type in ["DeepSeek", "OpenAI"])
        
        # Show Host for: Ollama, Local
        self._set_form_row_visible(self.row_host, prov_type in ["Ollama", "Local (HF Transformers)"])

    def _load_from_data(self):
        """Load data from edit mode."""
        d = self.data
        self.txt_name.setText(d.get("name", ""))
        self._set_combo_text(self.cmb_type, d.get("provider_type", "DeepSeek"))
        self.txt_api_key.setText(d.get("api_key", ""))
        self.txt_host.setText(d.get("host", ""))
        self.txt_model.setText(d.get("model", ""))
        self.chk_default.setChecked(bool(d.get("is_default", False)))

    def _set_form_row_visible(self, row: int, visible: bool) -> None:
        """Qt sürüm uyumluluğu için form satırı görünürlüğünü yönet."""
        if hasattr(self.conn_layout, "setRowVisible"):
            self.conn_layout.setRowVisible(row, visible)
            return
        for role in (QFormLayout.ItemRole.LabelRole, QFormLayout.ItemRole.FieldRole):
            item = self.conn_layout.itemAt(row, role)
            if item and item.widget():
                item.widget().setVisible(visible)

    def _collect_data(self) -> dict:
        """Collect data from widgets."""
        return {
            "name": self.txt_name.text().strip(),
            "provider_type": self.cmb_type.currentText(),
            "api_key": self.txt_api_key.text(),
            "host": self.txt_host.text().strip(),
            "model": self.txt_model.text().strip(),
            "is_default": self.chk_default.isChecked(),
        }

    @staticmethod
    def _set_combo_text(combo: QComboBox, text: str):
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _handle_save(self):
        d = self._collect_data()

        if not d["name"]:
            QMessageBox.warning(self, "Validation", "Provider name is required.")
            return
        if not d["model"]:
            QMessageBox.warning(self, "Validation", "Model name is required.")
            return

        self.data = d
        self.accept()

    def _handle_test(self):
        d = self._collect_data()
        msg = f"Testing {d['provider_type']} provider: {d['name']}\nModel: {d['model']}\n\nTest logic will be implemented here."
        QMessageBox.information(self, "Test Provider", msg)


# ConnectionEditorDialog Arayuzu
class ConnectionEditorDialog(QDialog):
    """Tek bir database connection profili ekleme / düzenleme dialog'u."""

    def __init__(self, parent=None, data: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Database Connection")
        self.resize(700, 520)

        # Dışarıdan veri geldiyse edit, yoksa yeni
        self.data = data or {}

        self._init_ui()
        self._load_from_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ---------- Top: Basic info ----------
        top_box = QGroupBox("Connection Profile")
        top_layout = QFormLayout(top_box)
        top_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        top_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        top_layout.setVerticalSpacing(8)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("GGB-Prod-OLTP01")

        self.cmb_env = TopComboBox()
        self.cmb_env.addItems(["Production", "Staging", "Development", "Local"])

        self.cmb_engine = TopComboBox()
        self.cmb_engine.addItems(["SQL Server", "PostgreSQL", "Oracle", "MySQL", "ODBC Driver"])

        env_engine_row = QWidget()
        env_engine_layout = QHBoxLayout(env_engine_row)
        env_engine_layout.setContentsMargins(0, 0, 0, 0)
        env_engine_layout.setSpacing(8)
        env_engine_layout.addWidget(self.cmb_env)
        env_engine_layout.addWidget(self.cmb_engine)

        top_layout.addRow("Connection name:", self.txt_name)
        top_layout.addRow("Environment / Engine:", env_engine_row)

        # ---------- Server & Database ----------
        server_box = QGroupBox("Server & Database")
        server_layout = QFormLayout(server_box)
        server_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        server_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        server_layout.setVerticalSpacing(8)

        self.txt_server = QLineEdit()
        self.txt_server.setPlaceholderText("P-KKDB01.ggb.local or 10.10.1.23")

        self.txt_instance = QLineEdit()
        self.txt_instance.setPlaceholderText("(optional)")

        self.spin_port = QSpinBox()
        self.spin_port.setRange(1, 65535)
        self.spin_port.setValue(1433)

        inst_port_row = QWidget()
        inst_port_layout = QHBoxLayout(inst_port_row)
        inst_port_layout.setContentsMargins(0, 0, 0, 0)
        inst_port_layout.setSpacing(8)
        inst_port_layout.addWidget(self.txt_instance, stretch=2)
        inst_port_layout.addWidget(self.spin_port, stretch=1)

        self.txt_database = QLineEdit()
        self.txt_database.setPlaceholderText("Database name (e.g. CoreBanking)")

        server_layout.addRow("Server / Host:", self.txt_server)
        server_layout.addRow("Instance / Port:", inst_port_row)
        server_layout.addRow("Database:", self.txt_database)

        # ---------- Authentication ----------
        auth_box = QGroupBox("Authentication")
        auth_layout = QFormLayout(auth_box)
        auth_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        auth_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        auth_layout.setVerticalSpacing(8)

        self.cmb_auth = TopComboBox()
        self.cmb_auth.addItems(["Integrated / Domain", "SQL / DB Login"])

        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("DOMAIN\\username or db_user")

        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_password.setPlaceholderText("Password")

        self.txt_schema = QLineEdit()
        self.txt_schema.setPlaceholderText("(optional, e.g. dbo / public)")

        self.chk_readonly = QCheckBox("Use read-only intent")

        schema_row = QWidget()
        schema_layout = QHBoxLayout(schema_row)
        schema_layout.setContentsMargins(0, 0, 0, 0)
        schema_layout.setSpacing(8)
        schema_layout.addWidget(self.txt_schema)
        schema_layout.addWidget(self.chk_readonly)

        auth_layout.addRow("Authentication:", self.cmb_auth)
        auth_layout.addRow("Username:", self.txt_user)
        auth_layout.addRow("Password:", self.txt_password)
        auth_layout.addRow("Default schema / Read-only:", schema_row)

        # ---------- Advanced ----------
        adv_box = QGroupBox("Advanced")
        adv_layout = QFormLayout(adv_box)
        adv_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        adv_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        adv_layout.setVerticalSpacing(8)

        self.txt_app_name = QLineEdit()
        self.txt_app_name.setText("DB Performance Studio")

        self.chk_encrypt = QCheckBox("Encrypt connection")
        self.chk_trust = QCheckBox("Trust server certificate")

        encrypt_row = QWidget()
        encrypt_layout = QHBoxLayout(encrypt_row)
        encrypt_layout.setContentsMargins(0, 0, 0, 0)
        encrypt_layout.setSpacing(8)
        encrypt_layout.addWidget(self.chk_encrypt)
        encrypt_layout.addWidget(self.chk_trust)
        encrypt_layout.addStretch()

        self.spin_conn_timeout = QSpinBox()
        self.spin_conn_timeout.setRange(1, 600)
        self.spin_conn_timeout.setValue(15)

        self.spin_cmd_timeout = QSpinBox()
        self.spin_cmd_timeout.setRange(5, 3600)
        self.spin_cmd_timeout.setValue(30)

        adv_layout.addRow("Application name:", self.txt_app_name)

        timeouts_row = QWidget()
        timeouts_layout = QHBoxLayout(timeouts_row)
        timeouts_layout.setContentsMargins(0, 0, 0, 0)
        timeouts_layout.setSpacing(8)
        timeouts_layout.addWidget(QLabel("Conn timeout (s):"))
        timeouts_layout.addWidget(self.spin_conn_timeout)
        timeouts_layout.addSpacing(12)
        timeouts_layout.addWidget(QLabel("Cmd timeout (s):"))
        timeouts_layout.addWidget(self.spin_cmd_timeout)
        timeouts_layout.addStretch()

        adv_layout.addRow("Security:", encrypt_row)
        adv_layout.addRow("", timeouts_row)

        # ---------- Butonlar ----------
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_test = QPushButton(t("connection.test", "Test Connection"))
        btn_box.addButton(self.btn_test, QDialogButtonBox.ButtonRole.ActionRole)

        btn_box.accepted.connect(self._handle_save)
        btn_box.rejected.connect(self.reject)
        self.btn_test.clicked.connect(self._handle_test_connection)

        # ---------- Ana layout'a ekle ----------
        main_layout.addWidget(top_box)
        main_layout.addWidget(server_box)
        main_layout.addWidget(auth_box)
        main_layout.addWidget(adv_box)
        main_layout.addWidget(btn_box)

    # --------- Data <-> UI ---------

    def _load_from_data(self):
        """Eğer edit modundaysak, self.data içinden widget'ları doldur."""
        d = self.data

        self.txt_name.setText(d.get("name", ""))
        self._set_combo_text(self.cmb_env, d.get("environment", "Development"))
        self._set_combo_text(self.cmb_engine, d.get("engine", "SQL Server"))

        self.txt_server.setText(d.get("server", ""))
        self.txt_instance.setText(d.get("instance", ""))
        self.spin_port.setValue(int(d.get("port", 1433)))
        self.txt_database.setText(d.get("database", ""))

        self._set_combo_text(self.cmb_auth, d.get("auth_type", "Integrated / Domain"))
        self.txt_user.setText(d.get("username", ""))
        self.txt_password.setText(d.get("password", ""))
        self.txt_schema.setText(d.get("schema", ""))
        self.chk_readonly.setChecked(bool(d.get("readonly", False)))

        self.txt_app_name.setText(d.get("application_name", "DB Performance Studio"))
        self.chk_encrypt.setChecked(bool(d.get("encrypt", False)))
        self.chk_trust.setChecked(bool(d.get("trust_cert", False)))
        self.spin_conn_timeout.setValue(int(d.get("conn_timeout", 15)))
        self.spin_cmd_timeout.setValue(int(d.get("cmd_timeout", 30)))

    def _collect_data(self) -> dict:
        """Widget'lardan dict şeklinde data üret."""
        return {
            "name": self.txt_name.text().strip(),
            "environment": self.cmb_env.currentText(),
            "engine": self.cmb_engine.currentText(),
            "server": self.txt_server.text().strip(),
            "instance": self.txt_instance.text().strip(),
            "port": int(self.spin_port.value()),
            "database": self.txt_database.text().strip(),
            "auth_type": self.cmb_auth.currentText(),
            "username": self.txt_user.text().strip(),
            "password": self.txt_password.text(),  # şimdilik plain
            "schema": self.txt_schema.text().strip(),
            "readonly": self.chk_readonly.isChecked(),
            "application_name": self.txt_app_name.text().strip(),
            "encrypt": self.chk_encrypt.isChecked(),
            "trust_cert": self.chk_trust.isChecked(),
            "conn_timeout": int(self.spin_conn_timeout.value()),
            "cmd_timeout": int(self.spin_cmd_timeout.value()),
        }

    # --------- Helpers & Handlers ---------

    @staticmethod
    def _set_combo_text(combo: QComboBox, text: str):
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _handle_save(self):
        d = self._collect_data()

        if not d["name"]:
            QMessageBox.warning(self, "Validation", "Connection name is required.")
            return
        if not d["server"]:
            QMessageBox.warning(self, "Validation", "Server / Host is required.")
            return
        if not d["database"]:
            QMessageBox.warning(self, "Validation", "Database name is required.")
            return

        self.data = d
        self.accept()

    def _handle_test_connection(self):
        # Şimdilik sadece dummy – ileride gerçek engine testine bağlarız
        d = self._collect_data()
        msg = (
            f"Testing connection to {d['server']}:{d['port']} / {d['database']}\n\n"
            "This is a placeholder. Here you will plug in real DB test logic."
        )
        QMessageBox.information(self, t("connection.test", "Test Connection"), msg)

# ------------------- MAIN UI (SIDEBAR & PAGES) -------------------


class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)
        self.logo = None
        self.main_menu_label = None
        self.tools_label = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Üst logo / app adı
        self.logo = QLabel(t("app.title", "DB Performance Studio"))
        self.logo.setObjectName("Logo")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.logo.setFixedHeight(32)
        layout.addWidget(self.logo)

        layout.addSpacing(8)

        # --- MAIN MENU başlığı ---
        self.main_menu_label = QLabel(t("sidebar.main_menu", "MAIN MENU"))
        self.main_menu_label.setObjectName("SidebarSectionLabel")
        main_font = self.main_menu_label.font()
        main_font.setPointSize(main_font.pointSize() + 2)
        main_font.setBold(True)
        self.main_menu_label.setFont(main_font)
        layout.addWidget(self.main_menu_label)

        # Separator line
        main_separator = QFrame()
        main_separator.setFrameShape(QFrame.Shape.HLine)
        main_separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(main_separator)

        layout.addSpacing(4)

        # Main Menu butonları
        self.btn_dashboard = self._create_nav_button(t("sidebar.dashboard", "Dashboard"))
        self.btn_object_explorer = self._create_nav_button(t("sidebar.object_explorer", "Object Explorer"))
        self.btn_query_stats = self._create_nav_button(t("sidebar.query_stats", "Query Statistics"))
        self.btn_perf_advisor = self._create_nav_button(t("sidebar.perf_advisor", "Index Advisor"))

        for btn in [
            self.btn_dashboard,
            self.btn_object_explorer,
            self.btn_query_stats,
            self.btn_perf_advisor,
        ]:
            layout.addWidget(btn)

        layout.addSpacing(8)

        # --- TOOLS başlığı ---
        self.tools_label = QLabel(t("sidebar.tools", "TOOLS"))
        self.tools_label.setObjectName("SidebarSectionLabel")
        tools_font = self.tools_label.font()
        tools_font.setPointSize(tools_font.pointSize() + 2)
        tools_font.setBold(True)
        self.tools_label.setFont(tools_font)
        layout.addWidget(self.tools_label)

        # Separator line
        tools_separator = QFrame()
        tools_separator.setFrameShape(QFrame.Shape.HLine)
        tools_separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(tools_separator)

        layout.addSpacing(4)

        # Tools butonları
        self.btn_blocking = self._create_nav_button(t("sidebar.blocking", "Blocking Analysis"))
        self.btn_security = self._create_nav_button(t("sidebar.security", "Security Audit"))
        self.btn_jobs = self._create_nav_button(t("sidebar.jobs", "Scheduled Jobs"))
        self.btn_waits = self._create_nav_button(t("sidebar.waits", "Wait Statistics"))

        for btn in [
            self.btn_blocking,
            self.btn_security,
            self.btn_jobs,
            self.btn_waits,
        ]:
            layout.addWidget(btn)

        layout.addStretch()

        # Alt kısım: hesap / profil
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)

        avatar = QLabel("EC")
        avatar.setObjectName("AvatarCircle")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(32, 32)

        user_label = QLabel("Erdal Cakıroğlu")
        user_label.setObjectName("SidebarUserLabel")

        footer.addWidget(avatar)
        footer.addWidget(user_label)
        footer.addStretch()

        layout.addLayout(footer)

    def _create_nav_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setToolTip(text)
        btn.setObjectName("SidebarButton")
        btn.setFixedHeight(36)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        return btn
    
    def update_strings(self):
        """Update all sidebar strings."""
        self.logo.setText(t("app.title", "DB Performance Studio"))
        self.main_menu_label.setText(t("sidebar.main_menu", "MAIN MENU"))
        self.tools_label.setText(t("sidebar.tools", "TOOLS"))
        self.btn_dashboard.setText(t("sidebar.dashboard", "Dashboard"))
        self.btn_object_explorer.setText(t("sidebar.object_explorer", "Object Explorer"))
        self.btn_query_stats.setText(t("sidebar.query_stats", "Query Statistics"))
        self.btn_perf_advisor.setText(t("sidebar.perf_advisor", "Index Advisor"))
        self.btn_blocking.setText(t("sidebar.blocking", "Blocking Analysis"))
        self.btn_security.setText(t("sidebar.security", "Security Audit"))
        self.btn_jobs.setText(t("sidebar.jobs", "Scheduled Jobs"))
        self.btn_waits.setText(t("sidebar.waits", "Wait Statistics"))


class TopBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(72)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(16)

        title = QLabel("DB Performance Studio")
        title.setObjectName("TopTitle")
        layout.addWidget(title)

        layout.addSpacerItem(QSpacerItem(12, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search sessions, queries or objects...")
        self.search.setObjectName("SearchField")
        self.search.setMinimumHeight(40)
        layout.addWidget(self.search, stretch=1)

        self.btn_globe = self._icon_button("🔔")
        self.btn_settings = self._icon_button("⚙")
        self.btn_mic = self._icon_button("❓")

        layout.addWidget(self.btn_globe)
        layout.addWidget(self.btn_settings)
        layout.addWidget(self.btn_mic)

        profile = QLabel("Erdal C.")
        profile.setObjectName("ProfileLabel")
        layout.addWidget(profile)

    def _icon_button(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("TopIconButton")
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn


class InfoBar(QFrame):
    """Information bar showing connection status, server, database, and AI model."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoBar")
        self.setFixedHeight(48)
        self.is_connected = False
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Left side: Connection status, Server, Database
        left_layout = QHBoxLayout()
        left_layout.setSpacing(12)

        # Connection status indicator
        self.lbl_status = QLabel("●")
        self.lbl_status.setStyleSheet("color: #d32f2f; font-size: 16px; background-color: transparent;")
        self.lbl_status.setFixedWidth(20)
        left_layout.addWidget(self.lbl_status)

        self.lbl_connection = QLabel(t("connection.disconnect", "Disconnected"))
        self.lbl_connection.setStyleSheet("color: #d32f2f; font-weight: 600;")
        left_layout.addWidget(self.lbl_connection)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setFrameShadow(QFrame.Shadow.Sunken)
        sep1.setFixedWidth(1)
        left_layout.addWidget(sep1)

        # Server combo
        self.lbl_server = QLabel(t("connection.server", "Server:"))
        left_layout.addWidget(self.lbl_server)
        
        self.cmb_server = TopComboBox()
        self.cmb_server.setMinimumWidth(150)
        self.cmb_server.addItem("(None)")
        left_layout.addWidget(self.cmb_server)

        # Database combo
        self.lbl_database = QLabel(t("connection.database", "Database:"))
        left_layout.addWidget(self.lbl_database)
        
        self.cmb_database = TopComboBox()
        self.cmb_database.setMinimumWidth(150)
        self.cmb_database.addItem("(None)")
        left_layout.addWidget(self.cmb_database)

        layout.addLayout(left_layout)
        layout.addStretch()

        # Right side: AI Model and green dot
        right_layout = QHBoxLayout()
        right_layout.setSpacing(12)

        # AI Model combo
        self.lbl_model = QLabel(t("settings.ai_model", "AI Model:"))
        right_layout.addWidget(self.lbl_model)
        
        self.cmb_model = TopComboBox()
        self.cmb_model.setMinimumWidth(200)
        right_layout.addWidget(self.cmb_model)
        self.refresh_from_settings()

        # Green dot indicator
        self.lbl_ai_status = QLabel("●")
        self.lbl_ai_status.setStyleSheet("color: #2e7d32; font-size: 16px;")
        self.lbl_ai_status.setFixedWidth(20)
        right_layout.addWidget(self.lbl_ai_status)

        layout.addLayout(right_layout)

    def _populate_models(self, settings: dict | None = None):
        """Populate AI models from settings."""
        self.cmb_model.clear()
        providers = (settings or load_settings()).get("llm", {}).get("providers", [])
        
        if providers:
            for provider in providers:
                name = provider.get("name", "Unknown")
                self.cmb_model.addItem(name)
        else:
            self.cmb_model.addItem("(None)")

    def _populate_servers(self, settings: dict | None = None):
        """Populate servers from settings."""
        self.cmb_server.clear()
        connections = (settings or load_settings()).get("database", {}).get("connections", [])
        
        if connections:
            for conn in connections:
                name = conn.get("name", "Unknown")
                self.cmb_server.addItem(name)
        else:
            self.cmb_server.addItem("(None)")

    def _populate_databases(self, settings: dict | None = None):
        """Populate databases from settings."""
        self.cmb_database.clear()
        connections = (settings or load_settings()).get("database", {}).get("connections", [])
        databases = []
        for conn in connections:
            db_name = conn.get("database", "")
            if db_name and db_name not in databases:
                databases.append(db_name)

        if databases:
            for db_name in databases:
                self.cmb_database.addItem(db_name)
        else:
            self.cmb_database.addItem("(None)")

    def set_connected(self, is_connected: bool, server_name: str = ""):
        """Set connection status."""
        self.is_connected = is_connected
        if is_connected:
            self.lbl_status.setStyleSheet("color: #2e7d32; font-size: 16px;")
            self.lbl_connection.setText(t("connection.connect", "Connected"))
            self.lbl_connection.setStyleSheet("color: #2e7d32; font-weight: 600;")
        else:
            self.lbl_status.setStyleSheet("color: #d32f2f; font-size: 16px;")
            self.lbl_connection.setText(t("connection.disconnect", "Disconnected"))
            self.lbl_connection.setStyleSheet("color: #d32f2f; font-weight: 600;")

    def update_strings(self):
        """Update UI strings based on language."""
        self.lbl_server.setText(t("connection.server", "Server:"))
        self.lbl_database.setText(t("connection.database", "Database:"))
        self.lbl_model.setText(t("settings.ai_model", "AI Model:"))
        
        status_text = t("connection.connect", "Connected") if self.is_connected else t("connection.disconnect", "Disconnected")
        self.lbl_connection.setText(status_text)

    def refresh_from_settings(self, settings: dict | None = None):
        """Refresh model/server/database combos from settings."""
        self._populate_models(settings)
        self._populate_servers(settings)
        self._populate_databases(settings)


class MetricCard(QFrame):
    """A card widget for displaying performance metrics."""
    def __init__(self, title: str, value: str = "N/A", unit: str = "", status: str = "normal", help_text: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.help_text = help_text
        self.setStyleSheet("""
            #MetricCard {
                background-color: #ffffff;
                border: 0.5px solid #e2e7f0;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Title and help button layout
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        
        # Title label
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #6b7280; font-size: 12px; font-weight: 700;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Help button
        if help_text:
            help_btn = QPushButton("?")
            help_btn.setFixedSize(16, 16)
            help_btn.setStyleSheet(Theme.btn_help())
            help_btn.clicked.connect(self._show_help)
            title_layout.addWidget(help_btn)
        
        layout.addLayout(title_layout)
        
        # Value label
        self.value_label = QLabel(value)
        value_style = "color: #00a651;" if status == "good" else "color: #d32f2f;" if status == "bad" else "color: #1f2937;"
        self.value_label.setStyleSheet(f"{value_style} font-size: 24px; font-weight: 600;")
        layout.addWidget(self.value_label)
        
        # Unit label
        if unit:
            unit_label = QLabel(unit)
            unit_label.setStyleSheet("color: #9ca3af; font-size: 11px;")
            layout.addWidget(unit_label)
        
        layout.addStretch()
    
    def _show_help(self):
        """Show help dialog."""
        from PyQt6.QtWidgets import QMessageBox
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.setText(self.help_text)
        help_dialog.setIcon(QMessageBox.Icon.Information)
        help_dialog.setStyleSheet("""
            QMessageBox {
                background-color: #ffffff;
            }
            QMessageBox QLabel {
                color: #1f2937;
            }
            QMessageBox QPushButton {
                min-width: 60px;
                padding: 4px 12px;
                background-color: #3b82f6;
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }
            QMessageBox QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        help_dialog.exec()
    
    def set_value(self, value: str, status: str = "normal"):
        """Update the value and status."""
        self.value_label.setText(value)
        value_style = "color: #00a651;" if status == "good" else "color: #d32f2f;" if status == "bad" else "color: #1f2937;"
        self.value_label.setStyleSheet(f"{value_style} font-size: 24px; font-weight: 600;")


class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title_label = None
        self.subtitle_label = None
        self.cmb_refresh_rate = None
        self.btn_refresh_stop = None
        self.metric_cards = {}
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(16)

        # Title row with refresh controls
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        self.title_label = QLabel(t("pages.dashboard_title", "Dashboard"))
        self.title_label.setObjectName("PageTitle")
        header_row.addWidget(self.title_label)
        header_row.addStretch()

        refresh_label = QLabel("Refresh rate:")
        refresh_label.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: 600;")
        header_row.addWidget(refresh_label)

        self.cmb_refresh_rate = TopComboBox()
        self.cmb_refresh_rate.setMinimumWidth(110)
        self.cmb_refresh_rate.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.cmb_refresh_rate.addItems(["5s", "15s", "30s", "60s"])
        self.cmb_refresh_rate.setCurrentIndex(1)
        self.cmb_refresh_rate.setStyleSheet("""
            QComboBox {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                background-color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        header_row.addWidget(self.cmb_refresh_rate)

        self.btn_refresh_stop = QPushButton("Stop")
        self.btn_refresh_stop.setFixedHeight(26)
        self.btn_refresh_stop.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #1f2937;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
        """)
        header_row.addWidget(self.btn_refresh_stop)

        main_layout.addLayout(header_row)

        self.subtitle_label = QLabel(t("pages.dashboard_subtitle", "High-level overview of server health, workload and alerts."))
        self.subtitle_label.setObjectName("PageSubtitle")
        main_layout.addWidget(self.subtitle_label)

        # Scroll area for metrics
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        scroll.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                width: 8px;
                background-color: transparent;
            }
            QScrollBar::handle:vertical {
                background-color: #d1d5db;
                border-radius: 4px;
            }
        """)
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)
        
        # Performance Metrics Section
        perf_section = self._create_metrics_section()
        scroll_layout.addLayout(perf_section)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
    
    def _create_metrics_section(self):
        """Create performance metrics section."""
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(12)
        
        # Metrics grid
        metrics_data = [
            ("Active Sessions", "0", "", "Number of currently active sessions connected to the database."),
            ("OS Total CPU %", "0", "%", "Total CPU usage percentage across all processors on the operating system."),
            ("SQL Process CPU %", "0", "%", "CPU usage percentage for the SQL Server process specifically."),
            ("Available OS Memory (MB)", "0", "MB", "Amount of free memory available in megabytes on the operating system."),
            ("PLE (sec)", "0", "sec", "Page Life Expectancy - average time a page stays in the buffer pool (higher is better)."),
            ("Buffer Cache Hit Ratio %", "0", "%", "Percentage of page requests found in buffer cache without disk I/O."),
            ("Batch Requests / sec", "0", "req/s", "Number of batch requests received per second."),
            ("Transactions / sec", "0", "tx/s", "Number of transactions committed per second."),
            ("IO Read Latency (ms)", "0", "ms", "Average time in milliseconds for a read operation to complete."),
            ("IO Write Latency (ms)", "0", "ms", "Average time in milliseconds for a write operation to complete."),
            ("Log Write Latency (ms)", "0", "ms", "Average time in milliseconds for transaction log writes to complete."),
            ("Signal Wait %", "0", "%", "Percentage of time threads spent waiting for CPU (scheduler inefficiency)."),
            ("Blocked Sessions", "0", "", "Number of sessions currently blocked waiting for a resource."),
            ("Runnable Tasks", "0", "", "Number of tasks waiting to run on the scheduler."),
            ("TempDB Log Used %", "0", "%", "Percentage of temporary database transaction log currently in use."),
            ("Blocking", "0", "", "SPID of the session currently blocking another session (0 if none)."),
        ]
        
        grid = QGridLayout()
        grid.setSpacing(12)
        
        for idx, (title, value, unit, help_text) in enumerate(metrics_data):
            card = MetricCard(title, value, unit, "normal", help_text)
            self.metric_cards[title] = card
            row = idx // 4
            col = idx % 4
            grid.addWidget(card, row, col)
        
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)
        
        section_layout.addLayout(grid)
        
        return section_layout
    
    def _update_strings(self):
        """Update UI strings based on current language."""
        self.title_label.setText(t("pages.dashboard_title", "Dashboard"))
        self.subtitle_label.setText(t("pages.dashboard_subtitle", "High-level overview of server health, workload and alerts."))
    
    def update_metric(self, metric_name: str, value: str, status: str = "normal"):
        """Update a specific metric value."""
        if metric_name in self.metric_cards:
            self.metric_cards[metric_name].set_value(value, status)


class FinancePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.title_label = None
        self.subtitle_label = None
        self.cmb_duration = None
        self.cmb_order = None
        self.txt_search = None
        self.queries_list = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(12)

        # Set transparent background
        self.setStyleSheet("background-color: transparent;")

        # Title and subtitle
        self.title_label = QLabel(t("pages.query_stats_title", "Query Statistics"))
        self.title_label.setObjectName("PageTitle")
        main_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(t("pages.query_stats_subtitle", "Execution stats, CPU, IO and duration trends for your workload."))
        self.subtitle_label.setObjectName("PageSubtitle")
        main_layout.addWidget(self.subtitle_label)

        # Filters Panel
        filters_panel = QFrame()
        filters_panel.setObjectName("Card")
        filters_panel.setStyleSheet(Theme.card_style_8())
        filters_layout = QHBoxLayout(filters_panel)
        filters_layout.setContentsMargins(12, 12, 12, 12)
        filters_layout.setSpacing(12)

        # Duration filter
        duration_label = QLabel("Duration:")
        duration_label.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: 500;")
        self.cmb_duration = TopComboBox()
        self.cmb_duration.setMinimumWidth(140)
        self.cmb_duration.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.cmb_duration.addItems(["Last 24 Hours", "Last 7 Days", "Last 30 Days"])
        self.cmb_duration.setCurrentIndex(0)
        
        # Order filter
        order_label = QLabel("Order By:")
        order_label.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: 500;")
        self.cmb_order = TopComboBox()
        self.cmb_order.setMinimumWidth(160)
        self.cmb_order.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.cmb_order.addItems([
            "Impact Score",
            "Average Duration",
            "Total CPU",
            "Execution Count",
            "Logical Reads"
        ])
        self.cmb_order.setCurrentIndex(0)

        # Search box
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: 500;")
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search query name...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
        """)
        self.txt_search.setMinimumWidth(250)

        filters_layout.addWidget(duration_label)
        filters_layout.addWidget(self.cmb_duration)
        filters_layout.addWidget(order_label)
        filters_layout.addWidget(self.cmb_order)
        filters_layout.addWidget(search_label)
        filters_layout.addWidget(self.txt_search)
        filters_layout.addStretch()

        main_layout.addWidget(filters_panel)

        # Results Panel
        results_panel = QFrame()
        results_panel.setObjectName("Card")
        results_panel.setStyleSheet(Theme.card_style_8())
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(0)

        # Queries list
        self.queries_list = QListWidget()
        self.queries_list.setMinimumHeight(350)
        self.queries_list.setStyleSheet(Theme.queries_list_style())
        
        # Sample queries
        self._add_query_item(
            "1006_Sp_DBA_CriticalError_Alert",
            "Avg: 174ms",
            "P95: 1419ms",
            "Exec: 91",
            "Plans: 7",
            "129.2",
            "#ef4444",  # red
            "Çoklu plan tespit edildi - Parametre sniffing olası"
        )
        self._add_query_item(
            "1011_Sp_DBA_LoginFailure_Alert",
            "Avg: 70ms",
            "P95: 209ms",
            "Exec: 3",
            "Plans: 3",
            "0.6",
            "#f59e0b",  # amber
            None
        )
        self._add_query_item(
            "1007_Sp_DBA_JobFailure_Alert",
            "Avg: 0ms",
            "P95: 8ms",
            "Exec: 170",
            "Plans: 4",
            "1.4",
            "#10b981",  # green
            "Çoklu plan tespit edildi - Parametre sniffing olası"
        )

        results_layout.addWidget(self.queries_list)
        main_layout.addWidget(results_panel, stretch=1)
        main_layout.addStretch()

        # Connect item double click signal
        self.queries_list.itemDoubleClicked.connect(self._on_query_item_clicked)

    def _add_query_item(self, name, avg, p95, exec_count, plans, impact, border_color, warning=None):
        """Add a query item to the list."""
        from PyQt6.QtWidgets import QListWidgetItem
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(12, 12, 12, 12)
        item_layout.setSpacing(12)

        # Left border
        border_frame = QFrame()
        border_frame.setStyleSheet(f"background-color: {border_color}; border-radius: 2px;")
        border_frame.setFixedWidth(4)
        item_layout.addWidget(border_frame)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        # Query name
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        content_layout.addWidget(name_label)

        # Stats row
        stats_text = f"{avg}  {p95}  {exec_count}  {plans}"
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        content_layout.addWidget(stats_label)

        # Warning message if present
        if warning:
            warning_label = QLabel(f"⚠  {warning}")
            warning_label.setStyleSheet("color: #ea580c; font-size: 10px;")
            content_layout.addWidget(warning_label)

        item_layout.addLayout(content_layout, stretch=1)

        # Impact score (right side)
        impact_label = QLabel(impact)
        impact_label.setStyleSheet(f"color: {border_color}; font-weight: 700; font-size: 13px;")
        impact_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item_layout.addWidget(impact_label)

        # Change percentage
        change_label = QLabel("– 0%")
        change_label.setStyleSheet("color: #9ca3af; font-size: 10px;")
        change_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item_layout.addWidget(change_label)

        # Add item to list
        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())
        # Store query data in item
        list_item.setData(Qt.ItemDataRole.UserRole, {
            "name": name,
            "avg": avg.replace("Avg: ", ""),
            "p95": p95.replace("P95: ", ""),
            "exec_count": exec_count.replace("Exec: ", ""),
            "plans": plans.replace("Plans: ", ""),
            "impact": impact,
            "border_color": border_color,
            "warning": warning
        })
        self.queries_list.addItem(list_item)
        self.queries_list.setItemWidget(list_item, item_widget)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: #e5e7eb;")
        sep_item = QListWidgetItem()
        sep_item.setSizeHint(QSize(0, 1))
        self.queries_list.addItem(sep_item)
        self.queries_list.setItemWidget(sep_item, separator)
    
    def _on_query_item_clicked(self, item):
        """Handle query item click - open detail dialog."""
        # Skip separator items
        if item.sizeHint().height() <= 1:
            return
        
        query_data = item.data(Qt.ItemDataRole.UserRole)
        if query_data:
            dialog = QueryDetailDialog(query_data, self)
            dialog.exec()
    
    def _update_strings(self):
        """Update UI strings based on current language."""
        self.title_label.setText(t("pages.query_stats_title", "Query Statistics"))
        self.subtitle_label.setText(t("pages.query_stats_subtitle", "Execution stats, CPU, IO and duration trends for your workload."))


class QueryDetailDialog(QDialog):
    """Dialog for displaying query execution details."""
    
    def __init__(self, query_data, parent=None):
        super().__init__(parent)
        self.query_data = query_data
        self.setWindowTitle(query_data["name"])
        self.setGeometry(100, 100, 1200, 700)
        self.setStyleSheet("background-color: #f9fafb;")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with back button and title
        header = QFrame()
        header.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #e5e7eb;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(12)

        back_btn = QPushButton(f"← {t('common.back', 'Back')}")
        back_btn.setStyleSheet(Theme.btn_ghost())
        back_btn.clicked.connect(self.reject)
        header_layout.addWidget(back_btn)

        title_label = QLabel(self.query_data["name"])
        title_label.setStyleSheet("""
            color: #1f2937;
            font-weight: 600;
            font-size: 16px;
            padding: 4px 8px;
            border-radius: 6px;
            background-color: #f8fafc;
            border: 1px solid #eef2f7;
        """)
        title_label.setToolTip(self.query_data["name"])
        title_label.setMaximumWidth(700)
        fm = QFontMetrics(title_label.font())
        elided = fm.elidedText(self.query_data["name"], Qt.TextElideMode.ElideRight, 680)
        title_label.setText(elided)
        header_layout.addWidget(title_label, stretch=1)

        analyze_btn = QPushButton(t("common.analyze_with_ai", "Analyze with AI"))
        analyze_btn.setStyleSheet(Theme.btn_secondary())
        header_layout.addWidget(analyze_btn)
        main_layout.addWidget(header)

        # Stats row
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            background-color: #ffffff;
            border-bottom: 1px solid #eef2f7;
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(20, 12, 20, 12)
        stats_layout.setSpacing(12)

        stats = [
            ("Avg Duration", self.query_data["avg"]),
            ("P95 Duration", self.query_data["p95"]),
            ("Avg CPU", "113 ms"),
            ("Avg Reads", "981"),
            ("Executions", self.query_data["exec_count"]),
            ("Plans", self.query_data["plans"])
        ]

        for label, value in stats:
            stats_layout.addWidget(create_circle_stat_card(label, value, "#6366f1"))

        stats_layout.addStretch()
        main_layout.addWidget(stats_frame)

        main_layout.addSpacing(12)

        # Content area with tabs
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(20, 0, 20, 20)
        content_layout.setSpacing(16)

        # Left side - Source Code tab
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 12, 14, 12)
        left_layout.setSpacing(10)

        source_title = QLabel("📝 Source Code")
        source_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        left_layout.addWidget(source_title)

        code_container = QFrame()
        code_container.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1f2937;
                border-radius: 6px;
            }
        """)
        code_container_layout = QHBoxLayout(code_container)
        code_container_layout.setContentsMargins(0, 0, 0, 0)
        code_container_layout.setSpacing(0)

        gutter = QLabel("1\n2\n3\n4\n5")
        gutter.setStyleSheet("""
            QLabel {
                background-color: #0f172a;
                color: #9ca3af;
                padding: 10px 8px;
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
                font-family: 'Courier New';
                font-size: 11px;
            }
        """)
        gutter.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        gutter.setFixedWidth(36)
        code_container_layout.addWidget(gutter)

        code_editor = QPlainTextEdit()
        code_editor.setPlainText(
            f"CREATE PROCEDURE {self.query_data['name']}\nAS\nBEGIN\n    -- Query code will appear here\nEND"
        )
        code_editor.setReadOnly(True)
        code_editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #111827;
                color: #9ae6b4;
                border: none;
                padding: 10px;
                font-family: 'Courier New';
                font-size: 11px;
            }
        """)
        code_container_layout.addWidget(code_editor, stretch=1)
        left_layout.addWidget(code_container, stretch=1)

        content_layout.addWidget(left_panel, stretch=1)

        # Right side - AI Analysis and Plan Stability
        right_panel_layout = QVBoxLayout()
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.setSpacing(16)

        # AI Analysis
        ai_frame = QFrame()
        ai_frame.setStyleSheet("background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;")
        ai_layout = QVBoxLayout(ai_frame)
        ai_layout.setContentsMargins(14, 12, 14, 12)
        ai_layout.setSpacing(8)

        ai_title = QLabel("🤖 AI Analysis")
        ai_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        ai_layout.addWidget(ai_title)

        ai_text = QLabel(t("common.analyze_hint_ai", "Click 'Analyze with AI' above to run analysis."))
        ai_text.setWordWrap(True)
        ai_text.setStyleSheet("""
            color: #6b7280;
            font-size: 11px;
            line-height: 1.5;
            background-color: #f8fafc;
            border: 1px dashed #e5e7eb;
            border-radius: 6px;
            padding: 10px;
        """)
        ai_layout.addWidget(ai_text, stretch=1)

        right_panel_layout.addWidget(ai_frame)

        # Plan Stability
        plan_frame = QFrame()
        plan_frame.setStyleSheet("background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 10px;")
        plan_layout = QVBoxLayout(plan_frame)
        plan_layout.setContentsMargins(14, 12, 14, 12)
        plan_layout.setSpacing(8)

        plan_title_row = QHBoxLayout()
        plan_title_row.setContentsMargins(0, 0, 0, 0)
        plan_title_row.setSpacing(8)

        plan_title = QLabel("📋 Plan Stability")
        plan_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        plan_title_row.addWidget(plan_title)
        plan_title_row.addStretch()

        plan_badge = QLabel("Unstable" if self.query_data["warning"] else "Stable")
        plan_badge.setStyleSheet("""
            color: #ffffff;
            font-size: 10px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 10px;
        """ + ("background-color: #ef4444;" if self.query_data["warning"] else "background-color: #10b981;"))
        plan_title_row.addWidget(plan_badge)
        plan_layout.addLayout(plan_title_row)

        if self.query_data["warning"]:
            plan_text = QLabel(f"🔴 Problem ({self.query_data['plans']} plan) - {self.query_data['warning']}")
            plan_text.setWordWrap(True)
            plan_text.setStyleSheet("""
                color: #b91c1c;
                font-size: 11px;
                font-weight: 600;
                background-color: #fef2f2;
                border: 1px solid #fee2e2;
                border-radius: 6px;
                padding: 8px 10px;
            """)
        else:
            plan_text = QLabel("✅ Stabil - Tek plan tespit edildi")
            plan_text.setWordWrap(True)
            plan_text.setStyleSheet("""
                color: #047857;
                font-size: 11px;
                font-weight: 600;
                background-color: #ecfdf5;
                border: 1px solid #d1fae5;
                border-radius: 6px;
                padding: 8px 10px;
            """)
        
        plan_layout.addWidget(plan_text, stretch=1)

        right_panel_layout.addWidget(plan_frame)

        content_widget = QWidget()
        content_widget.setLayout(right_panel_layout)
        content_layout.addWidget(content_widget)

        main_content = QWidget()
        main_content.setLayout(content_layout)
        main_layout.addWidget(main_content, stretch=1)


class DiscoverPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.title_label = None
        self.subtitle_label = None
        self.cmb_database = None
        self.cmb_object_type = None
        self.txt_search = None
        self.objects_list = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(12)
        
        # Set transparent background for the page
        self.setStyleSheet("background-color: transparent;")

        # Title and subtitle
        self.title_label = QLabel(t("pages.object_explorer_title", "Object Explorer"))
        self.title_label.setObjectName("PageTitle")
        main_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(t("pages.object_explorer_subtitle", "Explore database objects and properties."))
        self.subtitle_label.setObjectName("PageSubtitle")
        main_layout.addWidget(self.subtitle_label)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        splitter.setStyleSheet(Theme.splitter_style())

        # Left panel (20% width)
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_panel.setMinimumWidth(220)
        left_panel.setMaximumWidth(400)
        left_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        left_panel.setStyleSheet(Theme.card_style_8())
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        # --- Filters Section ---
        filters_title = QLabel("Filters")
        filters_title.setObjectName("CardTitle")
        filters_title.setStyleSheet("color: #1f2937; font-size: 13px; font-weight: 600;")
        left_layout.addWidget(filters_title)

        # Database filter
        db_label = QLabel("Database:")
        db_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        left_layout.addWidget(db_label)
        
        self.cmb_database = TopComboBox()
        self.cmb_database.setMinimumWidth(150)
        self.cmb_database.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cmb_database.addItems(["(None)", "master", "tempdb", "model", "msdb"])
        self.cmb_database.setCurrentIndex(0)
        left_layout.addWidget(self.cmb_database)

        # Object Type filter
        type_label = QLabel("Object Type:")
        type_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        left_layout.addWidget(type_label)
        
        self.cmb_object_type = TopComboBox()
        self.cmb_object_type.setMinimumWidth(150)
        self.cmb_object_type.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        object_types = [
            "All Objects",
            "Stored Procedures",
            "Views",
            "Triggers",
            "Functions",
            "Tables",
            "Indexes"
        ]
        self.cmb_object_type.addItems(object_types)
        self.cmb_object_type.setCurrentIndex(0)
        left_layout.addWidget(self.cmb_object_type)

        # Search filter
        search_label = QLabel("Search:")
        search_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        left_layout.addWidget(search_label)
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search by name...")
        self.txt_search.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e5e7eb;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
        """)
        left_layout.addWidget(self.txt_search)

        left_layout.addSpacing(12)

        # --- Objects Section ---
        objects_title = QLabel("Objects")
        objects_title.setObjectName("CardTitle")
        objects_title.setStyleSheet("color: #1f2937; font-size: 13px; font-weight: 600;")
        left_layout.addWidget(objects_title)

        # Objects list
        self.objects_list = QListWidget()
        self.objects_list.setMinimumHeight(300)
        self.objects_list.setStyleSheet(Theme.list_widget_style())
        self.objects_list.addItem("🔷 dbo.TRG_SetAppliedDateToEFMigrationHistory")
        self.objects_list.addItem("🔶 dbo.vw_ChangeWithCustomFields")
        self.objects_list.addItem("🔶 dbo.vw_ContinualImprovementWithCustomFields")
        self.objects_list.addItem("🔶 dbo.vw_ProblemsWithCustomFields")
        self.objects_list.addItem("🔶 dbo.vw_Ticket_IncidentWithCustomFields")
        self.objects_list.addItem("🔶 dbo.vw_Ticket_ServiceRequestWithCustomFields")
        left_layout.addWidget(self.objects_list)

        left_layout.addStretch()

        # Right panel (80% width - for future content like source code)
        right_panel = QFrame()
        right_panel.setObjectName("Card")
        right_panel.setMinimumWidth(400)
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_panel.setStyleSheet(Theme.card_style_8())
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Source code tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("ObjectExplorerTabs")
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabs.setStyleSheet("""
            QTabWidget {
                background-color: transparent;
                border: none;
            }
            QTabBar::tab {
                background-color: #f3f4f6;
                border: 1px solid #e5e7eb;
                border-bottom: 2px solid #e5e7eb;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0891b2;
                color: #ffffff;
                border-bottom: 2px solid #0891b2;
            }
            QTabWidget::pane {
                border: 1px solid #e5e7eb;
                border-top: none;
            }
        """)
        
        source_tab = QWidget()
        source_layout = QVBoxLayout(source_tab)
        source_layout.setContentsMargins(12, 12, 12, 12)
        source_label = QLabel("Source Code")
        source_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        source_layout.addWidget(source_label)
        source_layout.addWidget(QLabel("Select an object to view details..."))
        self.tabs.addTab(source_tab, "Source Code")

        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        stats_layout.setContentsMargins(12, 12, 12, 12)
        stats_label = QLabel("Statistics")
        stats_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        stats_layout.addWidget(stats_label)
        stats_layout.addWidget(QLabel("Object statistics will appear here..."))
        self.tabs.addTab(stats_tab, "Statistics")

        relations_tab = QWidget()
        relations_layout = QVBoxLayout(relations_tab)
        relations_layout.setContentsMargins(12, 12, 12, 12)
        relations_label = QLabel("Relations")
        relations_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        relations_layout.addWidget(relations_label)
        relations_layout.addWidget(QLabel("Object relations will appear here..."))
        self.tabs.addTab(relations_tab, "Relations")

        right_layout.addWidget(self.tabs)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial stretch factors (25% left, 75% right) - responsive
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        # Allow collapsible panels and smooth resizing
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        main_layout.addWidget(splitter, stretch=1)
    
    def _update_strings(self):
        """Update UI strings based on current language."""
        self.title_label.setText(t("pages.object_explorer_title", "Object Explorer"))
        self.subtitle_label.setText(t("pages.object_explorer_subtitle", "Explore database objects and properties."))


class BlockingAnalysisPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_updated_label = None
        self.auto_refresh_btn = None
        self.refresh_combo = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_now)
        self.init_ui()
        self._set_refresh_interval(self.refresh_combo.currentData())
        self._refresh_now()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        title = QLabel("🔒 Blocking Analysis")
        title.setObjectName("PageTitle")
        header_row.addWidget(title)
        header_row.addStretch()

        self.auto_refresh_btn = QPushButton("⏱ Auto-Refresh: ON")
        self.auto_refresh_btn.setCheckable(True)
        self.auto_refresh_btn.setChecked(True)
        self.auto_refresh_btn.setFixedHeight(34)
        self.auto_refresh_btn.setStyleSheet(Theme.btn_toggle())
        self.auto_refresh_btn.toggled.connect(self._toggle_auto_refresh)
        header_row.addWidget(self.auto_refresh_btn)

        self.refresh_combo = TopComboBox()
        self.refresh_combo.setFixedHeight(34)
        self.refresh_combo.addItem("5s", 5)
        self.refresh_combo.addItem("15s", 15)
        self.refresh_combo.addItem("30s", 30)
        self.refresh_combo.addItem("60s", 60)
        self.refresh_combo.setCurrentIndex(1)
        self.refresh_combo.currentIndexChanged.connect(
            lambda: self._set_refresh_interval(self.refresh_combo.currentData())
        )
        header_row.addWidget(self.refresh_combo)

        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.setFixedHeight(34)
        refresh_btn.setStyleSheet(Theme.btn_secondary())
        refresh_btn.clicked.connect(self._refresh_now)
        header_row.addWidget(refresh_btn)

        layout.addLayout(header_row)

        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(0, 0, 0, 0)
        stats_row.setSpacing(12)
        stats_row.addWidget(create_circle_stat_card("🧱 Total Blocking", "0", "#10b981"))
        stats_row.addWidget(create_circle_stat_card("🧠 Head Blockers", "0", "#10b981"))
        stats_row.addWidget(create_circle_stat_card("⏳ Max Wait", "0s", "#10b981"))
        stats_row.addWidget(create_circle_stat_card("👥 Affected Sessions", "0", "#10b981"))
        stats_row.addStretch()
        layout.addLayout(stats_row)

        main_row = QHBoxLayout()
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(12)

        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_panel.setStyleSheet("""
            #Card {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: #ffffff;
            }
            QTabBar::tab {
                background-color: #f3f4f6;
                border: 1px solid #e5e7eb;
                border-bottom: none;
                padding: 6px 12px;
                margin-right: 4px;
                font-size: 11px;
            }
            QTabBar::tab:selected {
                background-color: #6366f1;
                color: #ffffff;
            }
        """)

        graph_tab = QWidget()
        graph_layout = QVBoxLayout(graph_tab)
        graph_layout.setContentsMargins(12, 12, 12, 12)
        graph_layout.setSpacing(8)
        graph_label = QLabel("✅ No Active Blocking")
        graph_label.setStyleSheet("color: #10b981; font-size: 14px; font-weight: 600;")
        graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        graph_layout.addStretch()
        graph_layout.addWidget(graph_label)
        graph_layout.addStretch()
        tabs.addTab(graph_tab, "📊 Graph View")

        tree_tab = QWidget()
        tree_layout = QVBoxLayout(tree_tab)
        tree_layout.setContentsMargins(12, 12, 12, 12)
        tree_layout.addWidget(QLabel("Tree view will appear here..."))
        tabs.addTab(tree_tab, "🌲 Tree View")

        left_layout.addWidget(tabs, stretch=1)
        main_row.addWidget(left_panel, stretch=3)

        right_panel = QFrame()
        right_panel.setObjectName("Card")
        right_panel.setStyleSheet("""
            #Card {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        session_title = QLabel("📋 Session Details")
        session_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        right_layout.addWidget(session_title)

        session_box = QLabel("Select a session to view details")
        session_box.setStyleSheet("""
            background-color: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 6px 8px;
            color: #6b7280;
            font-size: 11px;
        """)
        right_layout.addWidget(session_box)

        query_title = QLabel("📌 Current Query:")
        query_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        right_layout.addWidget(query_title)

        query_box = QPlainTextEdit()
        query_box.setReadOnly(True)
        query_box.setPlainText("No query selected")
        query_box.setStyleSheet("""
            QPlainTextEdit {
                background-color: #f3f4f6;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 8px;
                color: #6b7280;
                font-size: 11px;
            }
        """)
        right_layout.addWidget(query_box, stretch=1)

        kill_btn = QPushButton("⚠ Kill Session")
        kill_btn.setFixedHeight(32)
        kill_btn.setStyleSheet(Theme.btn_outline("danger", "sm"))
        right_layout.addWidget(kill_btn)

        main_row.addWidget(right_panel, stretch=2)
        layout.addLayout(main_row, stretch=1)

        table_card = QFrame()
        table_card.setObjectName("Card")
        table_card.setStyleSheet(Theme.card_style())
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(12, 12, 12, 12)
        table_layout.setSpacing(8)

        table_title = QLabel("👑 Head Blockers")
        table_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        table_layout.addWidget(table_title)

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(
            ["Session", "Login", "Host", "Program", "Blocked Count", "CPU (s)"]
        )
        Theme.setup_table(table)
        table_layout.addWidget(table)
        layout.addWidget(table_card)

        self.last_updated_label = QLabel("🕒 Last updated: --:--:--")
        self.last_updated_label.setStyleSheet("color: #6b7280; font-size: 10px;")
        layout.addWidget(self.last_updated_label)


    def _toggle_auto_refresh(self, checked: bool):
        if checked:
            self.auto_refresh_btn.setText("⏱ Auto-Refresh: ON")
            self._set_refresh_interval(self.refresh_combo.currentData())
        else:
            self.auto_refresh_btn.setText("⏱ Auto-Refresh: OFF")
            self.timer.stop()

    def _set_refresh_interval(self, seconds: int | None):
        if not seconds:
            return
        if self.auto_refresh_btn.isChecked():
            self.timer.start(int(seconds) * 1000)

    def _refresh_now(self):
        now = QDateTime.currentDateTime().toString("HH:mm:ss")
        if self.last_updated_label:
            self.last_updated_label.setText(f"🕒 Last updated: {now}")


class SecurityAuditPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        title = QLabel("🛡️ Security Audit")
        title.setObjectName("PageTitle")
        header_row.addWidget(title)
        header_row.addStretch()

        run_btn = QPushButton("🔍 Run Audit")
        run_btn.setFixedHeight(34)
        run_btn.setStyleSheet(Theme.btn_secondary())
        header_row.addWidget(run_btn)
        layout.addLayout(header_row)

        subtitle = QLabel("SQL Server security analysis and recommendations")
        subtitle.setStyleSheet("color: #6b7380; font-size: 12px;")
        layout.addWidget(subtitle)

        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 0, 0, 0)
        cards_row.setSpacing(12)
        cards_row.addWidget(create_circle_stat_card("🔴 Critical", "3", "#ef4444"))
        cards_row.addWidget(create_circle_stat_card("🟠 High", "6", "#f97316"))
        cards_row.addWidget(create_circle_stat_card("🟡 Medium", "9", "#eab308"))
        cards_row.addWidget(create_circle_stat_card("🔵 Low", "12", "#3b82f6"))
        cards_row.addWidget(create_circle_stat_card("👤 Total Logins", "42", "#6366f1"))
        cards_row.addWidget(create_circle_stat_card("👑 Sysadmins", "2", "#8b5cf6"))
        layout.addLayout(cards_row)

        tables_row = QHBoxLayout()
        tables_row.setContentsMargins(0, 0, 0, 0)
        tables_row.setSpacing(12)

        issues_card = QFrame()
        issues_card.setObjectName("Card")
        issues_card.setStyleSheet("""
            #Card {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }
        """)
        issues_layout = QVBoxLayout(issues_card)
        issues_layout.setContentsMargins(12, 12, 12, 12)
        issues_layout.setSpacing(8)

        issues_title = QLabel("⚠ Security Issues")
        issues_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        issues_layout.addWidget(issues_title)

        issues_box = QPlainTextEdit()
        issues_box.setReadOnly(True)
        issues_box.setPlainText(
            "- sa login enabled\n"
            "- Guest user has CONNECT permission\n"
            "- xp_cmdshell is enabled\n"
            "- TRUSTWORTHY database setting ON\n"
            "- Weak password policy detected\n"
            "- Public role has ALTER permissions"
        )
        issues_box.setStyleSheet("""
            QPlainTextEdit {
                background-color: #f8fafc;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 10px;
                color: #6b7280;
                font-size: 11px;
            }
        """)
        issues_layout.addWidget(issues_box, stretch=1)

        tables_row.addWidget(issues_card, stretch=3)

        logins_card = QFrame()
        logins_card.setObjectName("Card")
        logins_card.setStyleSheet("""
            #Card {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }
        """)
        logins_layout = QVBoxLayout(logins_card)
        logins_layout.setContentsMargins(12, 12, 12, 12)
        logins_layout.setSpacing(8)

        logins_title = QLabel("👤 Server Logins")
        logins_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        logins_layout.addWidget(logins_title)

        logins_table = QTableWidget(4, 4)
        logins_table.setHorizontalHeaderLabels(["Login", "Type", "Default DB", "Status"])
        Theme.setup_readonly_table(logins_table)
        logins_table.setItem(0, 0, QTableWidgetItem("sa"))
        logins_table.setItem(0, 1, QTableWidgetItem("SQL Login"))
        logins_table.setItem(0, 2, QTableWidgetItem("master"))
        logins_table.setItem(0, 3, QTableWidgetItem("Enabled"))
        logins_table.setItem(1, 0, QTableWidgetItem("report_user"))
        logins_table.setItem(1, 1, QTableWidgetItem("SQL Login"))
        logins_table.setItem(1, 2, QTableWidgetItem("Reporting"))
        logins_table.setItem(1, 3, QTableWidgetItem("Enabled"))
        logins_table.setItem(2, 0, QTableWidgetItem("DOMAIN\\etl_srv"))
        logins_table.setItem(2, 1, QTableWidgetItem("Windows"))
        logins_table.setItem(2, 2, QTableWidgetItem("DBA_DB"))
        logins_table.setItem(2, 3, QTableWidgetItem("Enabled"))
        logins_table.setItem(3, 0, QTableWidgetItem("old_admin"))
        logins_table.setItem(3, 1, QTableWidgetItem("SQL Login"))
        logins_table.setItem(3, 2, QTableWidgetItem("master"))
        logins_table.setItem(3, 3, QTableWidgetItem("Disabled"))
        logins_layout.addWidget(logins_table, stretch=1)
        tables_row.addWidget(logins_card, stretch=2)

        layout.addLayout(tables_row, stretch=1)


class ScheduledJobsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.last_updated_label = None
        self.auto_refresh_btn = None
        self.refresh_combo = None
        self.jobs_table = None
        self.running_table = None
        self.failed_table = None
        self.detail_label = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_now)
        self.init_ui()
        self._set_refresh_interval(self.refresh_combo.currentData())
        self._refresh_now()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        title = QLabel("⚙ SQL Agent Jobs")
        title.setObjectName("PageTitle")
        header_row.addWidget(title)
        header_row.addStretch()

        self.auto_refresh_btn = QPushButton("⏱ Auto-Refresh: ON")
        self.auto_refresh_btn.setCheckable(True)
        self.auto_refresh_btn.setChecked(True)
        self.auto_refresh_btn.setFixedHeight(34)
        self.auto_refresh_btn.setStyleSheet(Theme.btn_toggle())
        self.auto_refresh_btn.toggled.connect(self._toggle_auto_refresh)
        header_row.addWidget(self.auto_refresh_btn)

        self.refresh_combo = TopComboBox()
        self.refresh_combo.setFixedHeight(34)
        self.refresh_combo.addItem("5s", 5)
        self.refresh_combo.addItem("15s", 15)
        self.refresh_combo.addItem("30s", 30)
        self.refresh_combo.addItem("60s", 60)
        self.refresh_combo.setCurrentIndex(1)
        self.refresh_combo.currentIndexChanged.connect(
            lambda: self._set_refresh_interval(self.refresh_combo.currentData())
        )
        header_row.addWidget(self.refresh_combo)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedHeight(34)
        refresh_btn.setStyleSheet(Theme.btn_secondary())
        refresh_btn.clicked.connect(self._refresh_now)
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        subtitle = QLabel("Monitor and manage SQL Server Agent jobs")
        subtitle.setStyleSheet("color: #6b7380; font-size: 12px;")
        layout.addWidget(subtitle)

        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(0, 0, 0, 0)
        cards_row.setSpacing(12)
        cards_row.addWidget(create_circle_stat_card("📋 Total Jobs", "24", "#6366f1"))
        cards_row.addWidget(create_circle_stat_card("✅ Enabled", "20", "#10b981"))
        cards_row.addWidget(create_circle_stat_card("▶ Running", "2", "#3b82f6"))
        cards_row.addWidget(create_circle_stat_card("❌ Failed (24h)", "1", "#ef4444"))
        layout.addLayout(cards_row)

        tables_row = QHBoxLayout()
        tables_row.setContentsMargins(0, 0, 0, 0)
        tables_row.setSpacing(12)

        all_jobs_card = QFrame()
        all_jobs_card.setObjectName("Card")
        all_jobs_card.setStyleSheet(Theme.card_style())
        all_jobs_layout = QVBoxLayout(all_jobs_card)
        all_jobs_layout.setContentsMargins(12, 12, 12, 12)
        all_jobs_layout.setSpacing(8)
        all_jobs_title = QLabel("📄 All Jobs")
        all_jobs_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        all_jobs_layout.addWidget(all_jobs_title)

        self.jobs_table = QTableWidget(5, 5)
        self.jobs_table.setHorizontalHeaderLabels(["Job", "Status", "Schedule", "Last Run", "Owner"])
        Theme.setup_table(self.jobs_table, compact=True)
        sample_jobs = [
            ("ETL_Daily_Load", "Running", "Daily 01:00", "Today 01:02", "sa"),
            ("Index_Rebuild_Weekly", "Enabled", "Sun 02:00", "Sun 02:15", "dba"),
            ("Cleanup_Old_Backups", "Enabled", "Daily 03:00", "Today 03:00", "sa"),
            ("Report_Refresh", "Running", "Hourly", "10:00", "report_user"),
            ("Legacy_Job_Archive", "Failed", "Weekly", "Mon 01:14", "old_admin"),
        ]
        for row, (job, status, sched, last_run, owner) in enumerate(sample_jobs):
            self.jobs_table.setItem(row, 0, QTableWidgetItem(job))
            self.jobs_table.setItem(row, 1, QTableWidgetItem(status))
            self.jobs_table.setItem(row, 2, QTableWidgetItem(sched))
            self.jobs_table.setItem(row, 3, QTableWidgetItem(last_run))
            self.jobs_table.setItem(row, 4, QTableWidgetItem(owner))
        self.jobs_table.itemSelectionChanged.connect(self._on_job_selected)
        all_jobs_layout.addWidget(self.jobs_table, stretch=1)
        tables_row.addWidget(all_jobs_card, stretch=3)

        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(12)

        running_card = QFrame()
        running_card.setObjectName("Card")
        running_card.setStyleSheet("""
            #Card {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-top: 3px solid #3b82f6;
                border-radius: 10px;
            }
        """)
        running_layout = QVBoxLayout(running_card)
        running_layout.setContentsMargins(12, 12, 12, 12)
        running_layout.setSpacing(8)
        running_title = QLabel("▶ Running Jobs")
        running_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        running_layout.addWidget(running_title)
        self.running_table = QTableWidget(2, 3)
        self.running_table.setHorizontalHeaderLabels(["Job", "Started", "Step"])
        Theme.setup_readonly_table(self.running_table)
        self.running_table.setItem(0, 0, QTableWidgetItem("ETL_Daily_Load"))
        self.running_table.setItem(0, 1, QTableWidgetItem("01:02"))
        self.running_table.setItem(0, 2, QTableWidgetItem("Extract"))
        self.running_table.setItem(1, 0, QTableWidgetItem("Report_Refresh"))
        self.running_table.setItem(1, 1, QTableWidgetItem("10:00"))
        self.running_table.setItem(1, 2, QTableWidgetItem("Refresh Cache"))
        running_layout.addWidget(self.running_table, stretch=1)
        right_col.addWidget(running_card)

        failed_card = QFrame()
        failed_card.setObjectName("Card")
        failed_card.setStyleSheet("""
            #Card {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-top: 3px solid #ef4444;
                border-radius: 10px;
            }
        """)
        failed_layout = QVBoxLayout(failed_card)
        failed_layout.setContentsMargins(12, 12, 12, 12)
        failed_layout.setSpacing(8)
        failed_title = QLabel("❌ Failed Jobs (Last 24h)")
        failed_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        failed_layout.addWidget(failed_title)
        self.failed_table = QTableWidget(1, 3)
        self.failed_table.setHorizontalHeaderLabels(["Job", "Time", "Reason"])
        Theme.setup_readonly_table(self.failed_table)
        self.failed_table.setItem(0, 0, QTableWidgetItem("Legacy_Job_Archive"))
        self.failed_table.setItem(0, 1, QTableWidgetItem("01:14"))
        self.failed_table.setItem(0, 2, QTableWidgetItem("Login failed"))
        failed_layout.addWidget(self.failed_table, stretch=1)
        right_col.addWidget(failed_card)

        tables_row.addLayout(right_col, stretch=2)
        layout.addLayout(tables_row, stretch=1)

        detail_card = QFrame()
        detail_card.setObjectName("Card")
        detail_card.setStyleSheet("""
            #Card {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }
        """)
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setSpacing(8)
        detail_title = QLabel("🧾 Job Details")
        detail_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        detail_layout.addWidget(detail_title)
        self.detail_label = QLabel("Select a job to view details")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        detail_layout.addWidget(self.detail_label)
        layout.addWidget(detail_card)

        self.last_updated_label = QLabel("🕒 Last updated: --:--:--")
        self.last_updated_label.setStyleSheet("color: #6b7380; font-size: 10px;")
        layout.addWidget(self.last_updated_label)


    def _toggle_auto_refresh(self, checked: bool):
        if checked:
            self.auto_refresh_btn.setText("⏱ Auto-Refresh: ON")
            self.refresh_combo.setEnabled(True)
            self._set_refresh_interval(self.refresh_combo.currentData())
        else:
            self.auto_refresh_btn.setText("⏱ Auto-Refresh: OFF")
            self.refresh_combo.setEnabled(False)
            self.timer.stop()

    def _set_refresh_interval(self, seconds: int | None):
        if not seconds:
            return
        if self.auto_refresh_btn.isChecked():
            self.timer.start(int(seconds) * 1000)

    def _refresh_now(self):
        now = QDateTime.currentDateTime().toString("HH:mm:ss")
        if self.last_updated_label:
            self.last_updated_label.setText(f"🕒 Last updated: {now}")

    def _on_job_selected(self):
        if not self.jobs_table or not self.detail_label:
            return
        selected = self.jobs_table.selectedItems()
        if not selected:
            self.detail_label.setText("Select a job to view details")
            return
        row = selected[0].row()
        job = self.jobs_table.item(row, 0).text()
        status = self.jobs_table.item(row, 1).text()
        sched = self.jobs_table.item(row, 2).text()
        last_run = self.jobs_table.item(row, 3).text()
        owner = self.jobs_table.item(row, 4).text()
        self.detail_label.setText(
            f"Job: {job}\nStatus: {status}\nSchedule: {sched}\nLast Run: {last_run}\nOwner: {owner}"
        )


class WaitStatisticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        title = QLabel("⏱ Wait Statistics")
        title.setObjectName("PageTitle")
        header_row.addWidget(title)
        header_row.addStretch()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedHeight(34)
        refresh_btn.setStyleSheet(Theme.btn_secondary())
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        subtitle = QLabel("Real-time SQL Server wait statistics analysis")
        subtitle.setStyleSheet("color: #6b7380; font-size: 12px;")
        layout.addWidget(subtitle)

        summary_title = QLabel("📊 Summary")
        summary_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        layout.addWidget(summary_title)

        summary_row = QHBoxLayout()
        summary_row.setContentsMargins(0, 0, 0, 0)
        summary_row.setSpacing(12)
        summary_row.addWidget(create_circle_stat_card("⏳ Total Wait Time", "3.5d", "#6366f1"))
        summary_row.addWidget(create_circle_stat_card("📡 Signal Wait", "4.5%", "#f59e0b"))
        summary_row.addWidget(create_circle_stat_card("🧱 Resource Wait", "95.5%", "#3b82f6"))
        summary_row.addWidget(create_circle_stat_card("👥 Current Waiters", "3", "#10b981"))
        summary_row.addStretch()
        layout.addLayout(summary_row)

        categories_title = QLabel("📈 Wait Categories")
        categories_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        layout.addWidget(categories_title)

        categories_row = QHBoxLayout()
        categories_row.setContentsMargins(0, 0, 0, 0)
        categories_row.setSpacing(12)
        categories_row.addWidget(create_circle_stat_card("CPU", "18.1M ms", "#ef4444"))
        categories_row.addWidget(create_circle_stat_card("I/O", "263.0M ms", "#f59e0b"))
        categories_row.addWidget(create_circle_stat_card("Lock", "5.0M ms", "#8b5cf6"))
        categories_row.addWidget(create_circle_stat_card("Latch", "3.4M ms", "#ec4899"))
        categories_row.addWidget(create_circle_stat_card("Memory", "56.8K ms", "#3b82f6"))
        categories_row.addWidget(create_circle_stat_card("Network", "7.8M ms", "#10b981"))
        categories_row.addWidget(create_circle_stat_card("Buffer", "0 ms", "#6366f1"))
        categories_row.addWidget(create_circle_stat_card("Other", "8.3M ms", "#6b7280"))
        categories_row.addStretch()
        layout.addLayout(categories_row)

        top_title = QLabel("🏆 Top Wait Types")
        top_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        layout.addWidget(top_title)

        top_card = QFrame()
        top_card.setObjectName("Card")
        top_card.setStyleSheet(Theme.card_style())
        top_layout = QVBoxLayout(top_card)
        top_layout.setContentsMargins(12, 12, 12, 12)
        top_layout.setSpacing(8)

        top_table = QTableWidget(8, 4)
        top_table.setHorizontalHeaderLabels(["Wait Type", "Wait Time", "Signal %", "Category"])
        Theme.setup_readonly_table(top_table)
        sample_waits = [
            ("CXPACKET", "41.2M ms", "2.3%", "CPU"),
            ("PAGEIOLATCH_SH", "33.8M ms", "1.1%", "I/O"),
            ("LCK_M_S", "5.0M ms", "0.4%", "Lock"),
            ("WRITELOG", "4.6M ms", "0.9%", "I/O"),
            ("LATCH_EX", "3.4M ms", "0.3%", "Latch"),
            ("MEMORY_ALLOCATION_EXT", "0.6M ms", "0.1%", "Memory"),
            ("ASYNC_NETWORK_IO", "0.4M ms", "0.2%", "Network"),
            ("SOS_SCHEDULER_YIELD", "0.3M ms", "4.5%", "CPU"),
        ]
        for row, (wtype, wtime, signal, cat) in enumerate(sample_waits):
            top_table.setItem(row, 0, QTableWidgetItem(wtype))
            top_table.setItem(row, 1, QTableWidgetItem(wtime))
            top_table.setItem(row, 2, QTableWidgetItem(signal))
            top_table.setItem(row, 3, QTableWidgetItem(cat))
        top_layout.addWidget(top_table)
        layout.addWidget(top_card, stretch=1)


class IndexAdvisorPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title_label = None
        self.subtitle_label = None
        self.layout_vbox = None
        self.init_ui()

    def init_ui(self):
        self.layout_vbox = QVBoxLayout(self)
        self.layout_vbox.setContentsMargins(24, 20, 24, 20)
        self.layout_vbox.setSpacing(16)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        header_left = QVBoxLayout()
        header_left.setContentsMargins(0, 0, 0, 0)
        header_left.setSpacing(4)

        self.title_label = QLabel(t("pages.perf_advisor_title", "Index Advisor"))
        self.title_label.setObjectName("PageTitle")
        self.subtitle_label = QLabel("DBA_DB için eksik index önerileri")
        self.subtitle_label.setStyleSheet("color: #10b981; font-size: 12px;")

        header_left.addWidget(self.title_label)
        header_left.addWidget(self.subtitle_label)
        header_row.addLayout(header_left)
        header_row.addStretch()

        refresh_btn = QPushButton(t("common.refresh", "Refresh"))
        refresh_btn.setFixedHeight(34)
        refresh_btn.setStyleSheet(Theme.btn_secondary())
        header_row.addWidget(refresh_btn)
        self.layout_vbox.addLayout(header_row)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(0, 0, 0, 0)
        stats_row.setSpacing(12)
        stats_row.addWidget(create_circle_stat_card("Toplam Öneri", "1", "#6366f1"))
        stats_row.addWidget(create_circle_stat_card("Yüksek Etkili", "1", "#10b981"))
        stats_row.addWidget(create_circle_stat_card("Tahmini Kazanım", "%91", "#f59e0b"))
        stats_row.addStretch()
        self.layout_vbox.addLayout(stats_row)

        # Main content
        main_row = QHBoxLayout()
        main_row.setContentsMargins(0, 0, 0, 0)
        main_row.setSpacing(12)

        # Left panel - missing index list
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_panel.setStyleSheet("""
            #Card {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 10px;
            }
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(8)

        left_title = QLabel("Missing Index Önerileri")
        left_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        left_layout.addWidget(left_title)

        left_sep = QFrame()
        left_sep.setFrameShape(QFrame.Shape.HLine)
        left_sep.setStyleSheet("color: #e5e7eb;")
        left_layout.addWidget(left_sep)

        table = QTableWidget(1, 6)
        table.setHorizontalHeaderLabels(["Tablo", "Etki %", "Equality", "Inequality", "Include", "Seeks"])
        table.setItem(0, 0, QTableWidgetItem("dbo.MissingIndexSnapshot"))
        table.setItem(0, 1, QTableWidgetItem("91%"))
        table.setItem(0, 2, QTableWidgetItem("sample_time"))
        table.setItem(0, 3, QTableWidgetItem("[sample_time]"))
        table.setItem(0, 4, QTableWidgetItem("[os_total_cpu_pct] ..."))
        table.setItem(0, 5, QTableWidgetItem("4"))
        Theme.setup_table(table, compact=True)
        left_layout.addWidget(table, stretch=1)
        main_row.addWidget(left_panel, stretch=3)

        # Right panel - details
        right_panel = QFrame()
        right_panel.setObjectName("Card")
        right_panel.setStyleSheet(Theme.card_style())
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        right_title = QLabel("📌 Index Detayı")
        right_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        right_layout.addWidget(right_title)

        right_sep = QFrame()
        right_sep.setFrameShape(QFrame.Shape.HLine)
        right_sep.setStyleSheet("color: #e5e7eb;")
        right_layout.addWidget(right_sep)

        script_label = QLabel("CREATE INDEX Script:")
        script_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        right_layout.addWidget(script_label)

        script_editor = QPlainTextEdit()
        script_editor.setReadOnly(True)
        script_editor.setPlainText(
            "CREATE NONCLUSTERED INDEX [IX_InstancePerfSnapshot_sample_time]\n"
            "ON [dbo].[InstancePerfSnapshot] ([sample_time])\n"
            "INCLUDE ([os_total_cpu_pct], [sqlproc_cpu_pct], [os_mem_available_mb],\n"
            "[batch_requests_per_sec], [transactions_per_sec], [io_read_latency_ms],\n"
            "[io_write_latency_ms], [log_write_latency_ms], [signal_wait_pct],\n"
            "[blocked_session_count], [runnable_tasks_count_total], [ple_seconds],\n"
            "[tempdb_version_store_kb], [tempdb_log_used_pct],\n"
            "[buffer_cache_hit_ratio_pct], [deadlocks_per_sec])"
        )
        script_editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #111827;
                color: #e5e7eb;
                border: 1px solid #1f2937;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Courier New';
                font-size: 11px;
            }
        """)
        right_layout.addWidget(script_editor, stretch=1)

        copy_btn = QPushButton(t("common.copy_script", "Copy Script"))
        copy_btn.setFixedHeight(34)
        copy_btn.setStyleSheet(Theme.btn_ghost())
        right_layout.addWidget(copy_btn)

        ai_row = QHBoxLayout()
        ai_row.setContentsMargins(0, 0, 0, 0)
        ai_row.setSpacing(8)
        ai_title = QLabel("🧠 AI Analiz")
        ai_title.setStyleSheet("color: #1f2937; font-weight: 600; font-size: 12px;")
        ai_row.addWidget(ai_title)
        ai_row.addStretch()
        ai_btn = QPushButton(t("common.analyze", "Analyze"))
        ai_btn.setFixedHeight(32)
        ai_btn.setStyleSheet(Theme.btn_secondary("sm"))
        ai_row.addWidget(ai_btn)
        right_layout.addLayout(ai_row)

        ai_box = QFrame()
        ai_box.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px dashed #e5e7eb;
                border-radius: 6px;
            }
        """)
        ai_box_layout = QVBoxLayout(ai_box)
        ai_box_layout.setContentsMargins(10, 10, 10, 10)
        ai_box_layout.setSpacing(4)
        ai_placeholder = QLabel(t("common.analyze_hint_index", "Select an index and click 'Analyze'."))
        ai_placeholder.setStyleSheet("color: #6b7280; font-size: 11px;")
        ai_placeholder.setWordWrap(True)
        ai_box_layout.addWidget(ai_placeholder)
        right_layout.addWidget(ai_box, stretch=1)

        main_row.addWidget(right_panel, stretch=2)
        self.layout_vbox.addLayout(main_row, stretch=1)
    
    def _update_strings(self):
        """Update UI strings based on current language."""
        self.title_label.setText(t("pages.perf_advisor_title", "Index Advisor"))
        self.subtitle_label.setText("DBA_DB için eksik index önerileri")



# ------------------- MAIN WINDOW -------------------


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = load_settings()
        
        # Load initial language
        initial_lang = self.settings["general"].get("language", "English")
        load_language(initial_lang)

        self.setWindowTitle(t("app.title", "DB Performance Studio"))
        self.resize(1320, 780)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)

        content_wrapper = QFrame()
        content_wrapper.setObjectName("ContentWrapper")
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.topbar = TopBar()
        content_layout.addWidget(self.topbar)

        self.pages = QStackedWidget()
        self.page_home = HomePage()
        self.page_discover = DiscoverPage()
        self.page_blocking = BlockingAnalysisPage()
        self.page_security = SecurityAuditPage()
        self.page_jobs = ScheduledJobsPage()
        self.page_waits = WaitStatisticsPage()
        self.page_spaces = QWidget()
        self.page_finance = FinancePage()
        self.page_index_advisor = IndexAdvisorPage()

        self.pages.addWidget(self.page_home)
        self.pages.addWidget(self.page_discover)
        self.pages.addWidget(self.page_blocking)
        self.pages.addWidget(self.page_security)
        self.pages.addWidget(self.page_jobs)
        self.pages.addWidget(self.page_waits)
        self.pages.addWidget(self.page_spaces)
        self.pages.addWidget(self.page_finance)
        self.pages.addWidget(self.page_index_advisor)

        content_layout.addWidget(self.pages)
        
        # Information bar (bottom)
        self.infobar = InfoBar()
        content_layout.addWidget(self.infobar)

        main_layout.addWidget(content_wrapper, stretch=1)

        self.statusBar().showMessage("Ready")

        self._connect_signals()
        self._apply_style()
        self._apply_settings_to_ui()

        # Dashboard default seçili
        self.sidebar.btn_dashboard.setChecked(True)
        self.pages.setCurrentWidget(self.page_home)

    def _connect_signals(self):
        self.sidebar.btn_dashboard.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.page_home)
        )
        self.sidebar.btn_object_explorer.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.page_discover)
        )
        self.sidebar.btn_blocking.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.page_blocking)
        )
        self.sidebar.btn_security.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.page_security)
        )
        self.sidebar.btn_jobs.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.page_jobs)
        )
        self.sidebar.btn_waits.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.page_waits)
        )
        self.sidebar.btn_query_stats.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.page_finance)
        )
        self.sidebar.btn_perf_advisor.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.page_index_advisor)
        )


        self.topbar.btn_settings.clicked.connect(self._open_settings_dialog)

    def _apply_style(self):
        self.setStyleSheet(
            """
        QWidget#ContentWrapper {
            background-color: #f5f7fb;
        }

        QFrame#Sidebar {
            background-color: #ffffff;
            border-right: 1px solid #dde2eb;
        }

        QLabel#Logo {
            font-size: 14px;
            font-weight: 600;
            color: #27313d;
        }

        QLabel#SidebarSectionLabel {
            font-size: 10px;
            letter-spacing: 1px;
            color: #8b93a2;
        }

        QLabel#SidebarUserLabel {
            font-size: 11px;
            color: #4c5667;
        }

        QLabel#AvatarCircle {
            background-color: #0e8a9d;
            color: white;
            border-radius: 16px;
            font-weight: 600;
        }

        QPushButton#SidebarButton {
            text-align: left;
            padding-left: 12px;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            color: #27313d;
            background-color: transparent;
        }
        QPushButton#SidebarButton:hover {
            background-color: #e4f0f4;
        }
        QPushButton#SidebarButton:checked {
            background-color: #0e8a9d;
            color: #ffffff;
        }

        QFrame#TopBar {
            background-color: #fdfefe;
            border-bottom: 1px solid #dde2eb;
        }

        QFrame#InfoBar {
            background-color: #fdfefe;
            border-top: 1px solid #dde2eb;
        }

        QLabel#TopTitle {
            font-size: 18px;
            font-weight: 600;
            color: #27313d;
        }

        QLineEdit#SearchField {
            border-radius: 18px;
            border: 1px solid #d5dde8;
            padding: 0 16px;
            background-color: #f7f9fc;
        }
        QLineEdit#SearchField:focus {
            border: 1px solid #0e8a9d;
            background-color: #ffffff;
        }

        QPushButton#TopIconButton {
            border: none;
            background-color: transparent;
            border-radius: 16px;
            font-size: 14px;
        }
        QPushButton#TopIconButton:hover {
            background-color: #e4f0f4;
        }

        QLabel#ProfileLabel {
            padding-left: 8px;
            color: #4c5667;
        }

        QLabel#PageTitle {
            font-size: 20px;
            font-weight: 600;
            color: #27313d;
        }
        QLabel#PageSubtitle {
            font-size: 13px;
            color: #6b7380;
        }

        QFrame#Card {
            background-color: #ffffff;
            border-radius: 16px;
            border: 1px solid #e2e7f0;
        }

        QLabel#CardTitle {
            font-size: 15px;
            font-weight: 600;
            color: #27313d;
        }

        QLabel#CardText {
            font-size: 13px;
            color: #6b7380;
        }

        QTabWidget#SettingsTabs::pane {
            border: 1px solid #dde2eb;
            border-radius: 10px;
            background: #fdfefe;
        }

        QTabBar::tab {
            padding: 6px 14px;
            border-radius: 8px;
            margin-right: 4px;
            font-size: 12px;
            color: #4c5667;
        }
        QTabBar::tab:selected {
            background-color: #0e8a9d;
            color: #ffffff;
        }
        QTabBar::tab:hover {
            background-color: #e4f0f4;
        }

        QPushButton#AddConnectionButton {
            background-color: #0e8a9d;
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 500;
            padding: 6px 12px;
        }
        QPushButton#AddConnectionButton:hover {
            background-color: #0d7a8b;
        }
        QPushButton#AddConnectionButton:pressed {
            background-color: #0a5f6f;
        }
        """
        )

    def _apply_settings_to_ui(self):
        font_size = self.settings["appearance"].get("font_size", 10)
        f = self.font()
        f.setPointSize(font_size)
        self.setFont(f)

    def _open_settings_dialog(self):
        dlg = SettingsDialog(self.settings, self)
        if dlg.exec():
            self._apply_settings_to_ui()
            self.infobar.refresh_from_settings(self.settings)
    
    def _on_language_changed(self):
        """Called when language is changed in settings."""
        lang = self.settings["general"].get("language", "English")
        load_language(lang)
        # UI stringlerini güncellemek için tüm metinleri yeniden ayarla
        self._update_ui_strings()
    
    def _update_ui_strings(self):
        """Update all UI strings based on current language."""
        # Window
        self.setWindowTitle(t("app.title", "DB Performance Studio"))
        
        # Top bar
        self.topbar.search.setPlaceholderText(t("topbar.search", "Search sessions, queries or objects..."))
        
        # Sidebar
        self.sidebar.logo.setText(t("app.title", "DB Performance Studio"))
        self.sidebar.main_menu_label.setText(t("sidebar.main_menu", "MAIN MENU"))
        self.sidebar.tools_label.setText(t("sidebar.tools", "TOOLS"))
        self.sidebar.btn_dashboard.setText(t("sidebar.dashboard", "Dashboard"))
        self.sidebar.btn_object_explorer.setText(t("sidebar.object_explorer", "Object Explorer"))
        self.sidebar.btn_query_stats.setText(t("sidebar.query_stats", "Query Statistics"))
        self.sidebar.btn_perf_advisor.setText(t("sidebar.perf_advisor", "Index Advisor"))
        self.sidebar.btn_blocking.setText(t("sidebar.blocking", "Blocking Analysis"))
        self.sidebar.btn_security.setText(t("sidebar.security", "Security Audit"))
        self.sidebar.btn_jobs.setText(t("sidebar.jobs", "Scheduled Jobs"))
        self.sidebar.btn_waits.setText(t("sidebar.waits", "Wait Statistics"))
        
        # Info bar
        self.infobar.update_strings()
        
        # Page titles
        self.page_home._update_strings()
        self.page_discover._update_strings()
        self.page_finance._update_strings()
        self.page_index_advisor._update_strings()


def main():
    app = QApplication(sys.argv)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
