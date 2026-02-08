"""
Wait Statistics View - Modern Enterprise Design
"""
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QSplitter, QProgressBar,
    QSizePolicy, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors, CircleStatCard
from app.core.logger import get_logger
from app.services.wait_stats_service import (
    get_wait_stats_service,
    WaitSummary,
    WaitStat,
    CurrentWait,
)
from app.database.queries.wait_stats_queries import (
    WaitCategory,
    get_category_color,
)

logger = get_logger('views.wait_stats')


class WaitCategoryCard(QFrame):
    """Circle card showing wait category statistics - GUI-05 Style"""
    
    def __init__(self, category: WaitCategory, parent=None):
        super().__init__(parent)
        self._category = category
        self._color = get_category_color(category)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet("background-color: transparent; border: none;")
        self.setFixedSize(108, 124)  # Fixed size for consistent layout (+8%)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        
        # Circle
        circle = QFrame()
        circle.setFixedSize(98, 98)
        circle.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 49px;
            }}
        """)
        circle_layout = QVBoxLayout(circle)
        circle_layout.setContentsMargins(0, 0, 0, 0)
        circle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Value
        self._value_label = QLabel("0 ms")
        self._value_label.setStyleSheet(
            f"color: {self._color}; font-size: 18px; font-weight: 700; background: transparent; border: none;"
        )
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle_layout.addWidget(self._value_label)
        
        # Category name below circle
        self._name_label = QLabel(self._category.value)
        self._name_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; background: transparent;")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(circle, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._name_label, alignment=Qt.AlignmentFlag.AlignHCenter)
    
    def update_value(self, wait_time_ms: int, percent: float):
        """Update the card with new values"""
        if wait_time_ms >= 1_000_000:
            value_text = f"{wait_time_ms / 1_000_000:.1f}M ms"
        elif wait_time_ms >= 1_000:
            value_text = f"{wait_time_ms / 1_000:.1f}K ms"
        else:
            value_text = f"{wait_time_ms} ms"
        
        self._value_label.setText(value_text)


class WaitStatRow(QFrame):
    """Row showing a single wait type"""
    
    def __init__(self, wait: WaitStat, parent=None):
        super().__init__(parent)
        self._wait = wait
        self._setup_ui()
    
    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(56)
        self.setStyleSheet(f"""
            QFrame {{
                background: {Colors.SURFACE};
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QFrame:hover {{
                background: {Colors.BACKGROUND};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        # Category indicator
        indicator = QFrame()
        indicator.setFixedSize(4, 32)
        indicator.setStyleSheet(f"background: {self._wait.category_color}; border-radius: 2px;")
        layout.addWidget(indicator)
        
        # Wait type info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(self._wait.wait_type)
        name_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 500; font-size: 13px;")
        info_layout.addWidget(name_label)
        
        category_label = QLabel(self._wait.category.value)
        category_label.setStyleSheet(f"color: {self._wait.category_color}; font-size: 11px;")
        info_layout.addWidget(category_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Metrics
        metrics = [
            ("Wait Time", self._format_ms(self._wait.wait_time_ms)),
            ("Tasks", f"{self._wait.waiting_tasks:,}"),
            ("Percent", f"{self._wait.wait_percent:.1f}%"),
        ]
        
        for label, value in metrics:
            metric_layout = QVBoxLayout()
            metric_layout.setSpacing(0)
            
            value_lbl = QLabel(value)
            value_lbl.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: bold; font-size: 13px;")
            value_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            metric_layout.addWidget(value_lbl)
            
            label_lbl = QLabel(label)
            label_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 10px;")
            label_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            metric_layout.addWidget(label_lbl)
            
            layout.addLayout(metric_layout)
    
    def _format_ms(self, ms: int) -> str:
        if ms >= 3_600_000:  # Hours
            return f"{ms / 3_600_000:.1f}h"
        elif ms >= 60_000:  # Minutes
            return f"{ms / 60_000:.1f}m"
        elif ms >= 1_000:  # Seconds
            return f"{ms / 1_000:.1f}s"
        return f"{ms}ms"


class WaitStatsView(BaseView):
    """Wait Statistics view with modern enterprise design"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = get_wait_stats_service()
        self._category_cards: Dict[WaitCategory, WaitCategoryCard] = {}
        self._summary_cards: Dict[str, QFrame] = {}
    
    def _setup_ui(self):
        # Title section
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left side - title
        title_left = QVBoxLayout()
        title_left.setSpacing(8)
        
        title = QLabel("⏱️ Wait Statistics")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_left.addWidget(title)
        
        subtitle = QLabel("Real-time SQL Server wait statistics analysis")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        title_left.addWidget(subtitle)
        
        title_layout.addLayout(title_left)
        title_layout.addStretch()
        
        # Right side - refresh button
        self._refresh_btn = QPushButton("🔄 Refresh")
        self._refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {Colors.PRIMARY_HOVER};
            }}
        """)
        self._refresh_btn.clicked.connect(self.refresh)
        title_layout.addWidget(self._refresh_btn)
        
        self._main_layout.addWidget(title_container)
        self._main_layout.addSpacing(12)
        
        # ═══════════════════════════════════════════════════════════════════
        # SUMMARY CARDS
        # ═══════════════════════════════════════════════════════════════════
        summary_title = QLabel("📊 Summary")
        summary_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: bold; background: transparent;")
        self._main_layout.addWidget(summary_title)
        self._main_layout.addSpacing(8)
        
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(16)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        
        # Summary stat cards
        summary_items = [
            ("total_wait", "Total Wait Time", "--", "⏱️"),
            ("signal_wait", "Signal Wait", "--%", "📡"),
            ("resource_wait", "Resource Wait", "--%", "💾"),
            ("current_waits", "Current Waiters", "--", "👥"),
        ]
        
        for card_id, label, value, icon in summary_items:
            card = self._create_summary_card(icon, label, value)
            self._summary_cards[card_id] = card
            summary_layout.addWidget(card)
        
        summary_layout.addStretch()
        self._main_layout.addLayout(summary_layout)
        self._main_layout.addSpacing(16)
        
        # ═══════════════════════════════════════════════════════════════════
        # CATEGORY BREAKDOWN
        # ═══════════════════════════════════════════════════════════════════
        category_title = QLabel("📈 Wait Categories")
        category_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: bold; background: transparent;")
        self._main_layout.addWidget(category_title)
        self._main_layout.addSpacing(8)
        
        category_layout = QHBoxLayout()
        category_layout.setSpacing(16)
        category_layout.setContentsMargins(0, 0, 0, 0)
        
        categories = [
            WaitCategory.CPU, WaitCategory.IO, WaitCategory.LOCK,
            WaitCategory.LATCH, WaitCategory.MEMORY, WaitCategory.NETWORK,
            WaitCategory.BUFFER, WaitCategory.OTHER
        ]
        
        for category in categories:
            card = WaitCategoryCard(category)
            self._category_cards[category] = card
            category_layout.addWidget(card)
        
        category_layout.addStretch()
        self._main_layout.addLayout(category_layout)
        self._main_layout.addSpacing(12)
        
        # ═══════════════════════════════════════════════════════════════════
        # TOP WAITS LIST
        # ═══════════════════════════════════════════════════════════════════
        waits_title = QLabel("🔝 Top Wait Types")
        waits_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: bold; background: transparent;")
        self._main_layout.addWidget(waits_title)
        self._main_layout.addSpacing(8)
        
        # Waits container with scroll
        self._waits_container = QFrame()
        self._waits_container.setStyleSheet(f"""
            QFrame {{
                background: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        self._waits_layout = QVBoxLayout(self._waits_container)
        self._waits_layout.setContentsMargins(0, 0, 0, 0)
        self._waits_layout.setSpacing(0)
        
        # Placeholder
        placeholder = QLabel("Loading wait statistics...")
        placeholder.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 32px;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._waits_layout.addWidget(placeholder)
        
        self._waits_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Scroll area for waits list (prevents row compression on smaller windows)
        self._waits_scroll = QScrollArea()
        self._waits_scroll.setWidgetResizable(True)
        self._waits_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._waits_scroll.setStyleSheet("background: transparent;")
        self._waits_scroll.setWidget(self._waits_container)
        
        self._main_layout.addWidget(self._waits_scroll, stretch=1)
    
    def _create_summary_card(self, icon: str, label: str, value: str) -> CircleStatCard:
        """Create a circle summary stat card - GUI-05 style"""
        title = f"{icon} {label}"
        return CircleStatCard(title, value, Colors.SECONDARY)
    
    def _update_summary_card(self, card_id: str, value: str):
        """Update a summary card value"""
        if card_id in self._summary_cards:
            card = self._summary_cards[card_id]
            if isinstance(card, CircleStatCard):
                card.update_value(value)
            else:
                value_lbl = card.findChild(QLabel, "value")
                if value_lbl:
                    value_lbl.setText(value)
    
    def on_show(self) -> None:
        """Called when view becomes visible"""
        self.refresh()
    
    def on_hide(self) -> None:
        """Called when view is hidden"""
        pass
    
    def refresh(self) -> None:
        """Refresh wait statistics"""
        if not self._is_initialized:
            logger.debug("Wait stats refresh skipped: View not initialized")
            return
            
        if not self._service.is_connected:
            logger.debug("Wait stats refresh skipped: No active connection")
            return
        
        logger.info("Refreshing wait statistics...")
        
        try:
            summary = self._service.get_wait_summary()
            self._update_ui(summary)
        except Exception as e:
            logger.error(f"Error refreshing wait stats: {e}")
    
    def _update_ui(self, summary: WaitSummary):
        """Update UI with new data"""
        # Update summary cards
        total_wait_text = self._format_time(summary.total_wait_time_ms)
        self._update_summary_card("total_wait", total_wait_text)
        self._update_summary_card("signal_wait", f"{summary.signal_wait_percent:.1f}%")
        self._update_summary_card("resource_wait", f"{summary.resource_wait_percent:.1f}%")
        self._update_summary_card("current_waits", str(len(summary.current_waits)))
        
        # Update category cards
        total_category_time = sum(summary.category_stats.values()) or 1
        for category, wait_time in summary.category_stats.items():
            if category in self._category_cards:
                percent = (wait_time / total_category_time) * 100
                self._category_cards[category].update_value(wait_time, percent)
        
        # Update top waits list
        self._update_waits_list(summary.top_waits)
    
    def _update_waits_list(self, waits: List[WaitStat]):
        """Update the top waits list"""
        # Clear existing
        while self._waits_layout.count():
            item = self._waits_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not waits:
            placeholder = QLabel("No significant waits detected")
            placeholder.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 32px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._waits_layout.addWidget(placeholder)
            return
        
        # Add wait rows
        for wait in waits[:15]:  # Show top 15
            row = WaitStatRow(wait)
            self._waits_layout.addWidget(row)
        
        self._waits_layout.addStretch()
    
    def _format_time(self, ms: int) -> str:
        """Format milliseconds to human readable"""
        if ms >= 86_400_000:  # Days
            return f"{ms / 86_400_000:.1f} days"
        elif ms >= 3_600_000:  # Hours
            return f"{ms / 3_600_000:.1f} hours"
        elif ms >= 60_000:  # Minutes
            return f"{ms / 60_000:.1f} min"
        elif ms >= 1_000:  # Seconds
            return f"{ms / 1_000:.1f} sec"
        return f"{ms} ms"
