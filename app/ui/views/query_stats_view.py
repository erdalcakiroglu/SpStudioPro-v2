"""
Query Stats View - GUI-05 Modern Design
Execution stats, CPU, IO and duration trends for workload.
"""

from typing import Optional, List
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QScrollArea,
    QFrame, QSizePolicy, QListWidget, QListWidgetItem,
    QDialog, QPlainTextEdit, QMessageBox, QGraphicsDropShadowEffect,
    QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QFontMetrics, QPainter, QColor, QPen

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors, create_circle_stat_card, Theme as ThemeStyles
from app.core.logger import get_logger
from app.services.query_stats_service import QueryStatsService
from app.models.query_stats_models import (
    QueryStats, 
    QueryStatsFilter, 
    QueryPriority,
    PlanStability,
)
from app.database.queries.query_store_queries import PRIORITY_COLORS
from app.ui.components.code_editor import CodeEditor
from app.ui.components.plan_viewer import PlanViewerWidget
from app.analysis.plan_parser import PlanParser

logger = get_logger('ui.query_stats')


class CircularProgressWidget(QWidget):
    """Circular spinning progress indicator"""
    
    def __init__(self, parent=None, size: int = 48, color: str = "#6366f1"):
        super().__init__(parent)
        self._size = size
        self._color = QColor(color)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(size, size)
        
    def start(self):
        """Start spinning animation"""
        self._timer.start(50)  # 20 FPS
        
    def stop(self):
        """Stop spinning animation"""
        self._timer.stop()
        
    def _rotate(self):
        self._angle = (self._angle + 10) % 360
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate dimensions
        margin = 4
        diameter = self._size - 2 * margin
        
        # Draw arc
        pen = QPen(self._color)
        pen.setWidth(4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # Draw spinning arc (270 degrees)
        painter.drawArc(margin, margin, diameter, diameter, 
                       self._angle * 16, 270 * 16)


class LoadingOverlay(QWidget):
    """Loading overlay with circular spinner"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._setup_ui()
        
    def _setup_ui(self):
        self.setStyleSheet("background-color: rgba(255, 255, 255, 0.9);")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Spinner
        self._spinner = CircularProgressWidget(self, size=56, color=Colors.SECONDARY)
        layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Loading text
        self._label = QLabel("Loading...")
        self._label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 14px;
                font-weight: 500;
                background: transparent;
                margin-top: 12px;
            }}
        """)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignCenter)
        
    def set_text(self, text: str):
        """Set loading message"""
        self._label.setText(text)
        
    def showEvent(self, event):
        super().showEvent(event)
        self._spinner.start()
        
    def hideEvent(self, event):
        super().hideEvent(event)
        self._spinner.stop()


class QueryStatsView(BaseView):
    """
    Query Statistics View - GUI-05 Style
    Shows query performance stats in a clean list format
    """
    
    query_selected = pyqtSignal(int)  # query_id
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._service = QueryStatsService()
        self._queries: List[QueryStats] = []
        self._current_filter = QueryStatsFilter()
    
    @property
    def view_title(self) -> str:
        return "Query Statistics"
    
    def _setup_ui(self) -> None:
        """Setup Query Statistics UI - GUI-05 Style"""
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        
        # Main container
        main_widget = QWidget()
        main_widget.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(12)
        
        # Title
        title = QLabel("Query Statistics")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY}; 
            font-size: 20px; 
            font-weight: 700;
            background: transparent;
        """)
        main_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Execution stats, CPU, IO and duration trends for your workload.")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; background: transparent;")
        main_layout.addWidget(subtitle)
        
        # ═══════════════════════════════════════════════════════════
        # FILTERS PANEL
        # ═══════════════════════════════════════════════════════════
        filters_panel = QFrame()
        filters_panel.setObjectName("Card")
        filters_panel.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        filters_layout = QHBoxLayout(filters_panel)
        filters_layout.setContentsMargins(12, 12, 12, 12)
        filters_layout.setSpacing(12)
        
        # Duration filter
        duration_label = QLabel("Duration:")
        duration_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 500;")
        filters_layout.addWidget(duration_label)
        
        self._cmb_duration = QComboBox()
        self._cmb_duration.setMinimumWidth(140)
        self._cmb_duration.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._cmb_duration.addItems(["Last 24 Hours", "Last 7 Days", "Last 30 Days"])
        self._cmb_duration.setCurrentIndex(0)
        self._cmb_duration.setStyleSheet(self._get_combo_style())
        self._cmb_duration.currentIndexChanged.connect(self._on_filter_changed)
        filters_layout.addWidget(self._cmb_duration)
        
        # Order By filter
        order_label = QLabel("Order By:")
        order_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 500;")
        filters_layout.addWidget(order_label)
        
        self._cmb_order = QComboBox()
        self._cmb_order.setMinimumWidth(160)
        self._cmb_order.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._cmb_order.addItems([
            "Impact Score",
            "Average Duration",
            "Total CPU",
            "Execution Count",
            "Logical Reads"
        ])
        self._cmb_order.setCurrentIndex(0)
        self._cmb_order.setStyleSheet(self._get_combo_style())
        self._cmb_order.currentIndexChanged.connect(self._on_filter_changed)
        filters_layout.addWidget(self._cmb_order)
        
        # Search filter
        search_label = QLabel("Search:")
        search_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 500;")
        filters_layout.addWidget(search_label)
        
        self._txt_search = QLineEdit()
        self._txt_search.setPlaceholderText("Search query name...")
        self._txt_search.setMinimumWidth(250)
        self._txt_search.setStyleSheet(f"""
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
        """)
        self._txt_search.textChanged.connect(self._on_search_changed)
        filters_layout.addWidget(self._txt_search)
        
        filters_layout.addStretch()
        main_layout.addWidget(filters_panel)
        
        # ═══════════════════════════════════════════════════════════
        # RESULTS PANEL
        # ═══════════════════════════════════════════════════════════
        results_panel = QFrame()
        results_panel.setObjectName("Card")
        results_panel.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(0)
        
        # Queries list
        self._queries_list = QListWidget()
        self._queries_list.setMinimumHeight(350)
        self._queries_list.setSpacing(0)
        self._queries_list.setUniformItemSizes(False)
        self._queries_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                outline: none;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {Colors.BORDER};
                padding: 0px;
                margin: 0px;
                background-color: {Colors.SURFACE};
            }}
            QListWidget::item:hover {{
                background-color: #f8fafc;
            }}
            QListWidget::item:selected {{
                background-color: {Colors.PRIMARY_LIGHT};
            }}
        """)
        self._queries_list.itemDoubleClicked.connect(self._on_query_double_clicked)
        results_layout.addWidget(self._queries_list)
        
        main_layout.addWidget(results_panel, stretch=1)
        
        self._main_layout.addWidget(main_widget)
        
        # Loading overlay (hidden by default)
        self._loading_overlay = LoadingOverlay(self)
        self._loading_overlay.hide()
    
    def _get_combo_style(self) -> str:
        """Get ComboBox style - GUI-05 style"""
        return ThemeStyles.combobox_style()
    
    def _add_query_item(self, query: QueryStats) -> None:
        """Add a query item to the list - GUI-05 style"""
        # Create item widget
        item_widget = QWidget()
        item_widget.setObjectName("QueryItemWidget")
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(12, 8, 12, 8)
        item_layout.setSpacing(12)
        
        # Get priority color
        priority = query.priority
        priority_info = PRIORITY_COLORS.get(priority.value, PRIORITY_COLORS.get("info", {"color": "#6b7280"}))
        border_color = priority_info.get("color", "#6b7280")
        
        # Calculate height based on warning presence
        has_warning = query.plan_stability == PlanStability.PROBLEM
        
        # Left border (priority indicator)
        border_frame = QFrame()
        border_frame.setObjectName("PriorityBar")
        border_frame.setFixedWidth(4)
        border_frame.setStyleSheet(f"""
            QFrame#PriorityBar {{
                background-color: {border_color};
                border-radius: 2px;
                min-height: 36px;
            }}
        """)
        item_layout.addWidget(border_frame)
        
        # Content
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)
        
        # Query name
        name_label = QLabel(query.display_name)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: 600;
                font-size: 12px;
                background-color: transparent;
                border: none;
            }}
        """)
        content_layout.addWidget(name_label)
        
        # Stats row
        metrics = query.metrics
        last_exec = self._format_last_execution(query.last_execution)
        stats_text = (
            f"Avg: {metrics.avg_duration_ms:.0f}ms  •  "
            f"P95: {metrics.p95_duration_ms:.0f}ms  •  "
            f"Exec: {metrics.total_executions:,}  •  "
            f"Plans: {metrics.plan_count}  •  "
            f"Last: {last_exec}"
        )
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 11px;
                background-color: transparent;
                border: none;
            }}
        """)
        content_layout.addWidget(stats_label)
        
        # Warning message if problem
        if has_warning:
            warning_label = QLabel("⚠  Multiple plans detected - possible parameter sniffing")
            warning_label.setStyleSheet("""
                QLabel {
                    color: #ea580c;
                    font-size: 10px;
                    background-color: transparent;
                    border: none;
                }
            """)
            content_layout.addWidget(warning_label)
        
        item_layout.addLayout(content_layout, stretch=1)
        
        # Right side container for impact and change
        right_container = QWidget()
        right_container.setFixedWidth(60)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        
        # Impact score
        impact = metrics.impact_score
        impact_label = QLabel(f"{impact:.1f}")
        impact_label.setStyleSheet(f"""
            QLabel {{
                color: {border_color};
                font-weight: 700;
                font-size: 14px;
                background-color: transparent;
                border: none;
            }}
        """)
        impact_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(impact_label)
        
        # Change percentage
        change = metrics.change_percent
        change_text = f"{'↑' if change > 0 else '↓' if change < 0 else '–'} {abs(change):.0f}%"
        change_label = QLabel(change_text)
        change_color = "#ef4444" if change > 0 else "#22c55e" if change < 0 else "#9ca3af"
        change_label.setStyleSheet(f"""
            QLabel {{
                color: {change_color};
                font-size: 10px;
                background-color: transparent;
                border: none;
            }}
        """)
        change_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_layout.addWidget(change_label)
        
        right_layout.addStretch()
        item_layout.addWidget(right_container)
        
        # Calculate proper height based on content
        item_height = 76 if has_warning else 60
        
        # Add item to list
        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(0, item_height))
        list_item.setData(Qt.ItemDataRole.UserRole, query)
        self._queries_list.addItem(list_item)
        self._queries_list.setItemWidget(list_item, item_widget)

    def _format_last_execution(self, value: Optional[datetime]) -> str:
        """Format last execution timestamp for list view"""
        if not value:
            return "N/A"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        return str(value)
    
    def _on_query_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle query item double-click - open detail dialog"""
        query = item.data(Qt.ItemDataRole.UserRole)
        if query:
            dialog = QueryDetailDialog(query, self._service, self)
            dialog.exec()
    
    def _on_filter_changed(self) -> None:
        """Handle filter change"""
        self._refresh_data()
    
    def _on_search_changed(self, text: str) -> None:
        """Handle search text change"""
        self._current_filter.search_text = text
        self._filter_list()
    
    def _filter_list(self) -> None:
        """Filter visible items based on search"""
        search_text = self._txt_search.text().lower()
        for i in range(self._queries_list.count()):
            item = self._queries_list.item(i)
            query = item.data(Qt.ItemDataRole.UserRole)
            if query:
                visible = not search_text or search_text in query.display_name.lower()
                item.setHidden(not visible)
    
    def resizeEvent(self, event):
        """Handle resize to position loading overlay"""
        super().resizeEvent(event)
        if hasattr(self, '_loading_overlay'):
            self._loading_overlay.setGeometry(self.rect())
    
    def _show_loading(self, message: str = "Loading..."):
        """Show loading overlay"""
        self._loading_overlay.set_text(message)
        self._loading_overlay.setGeometry(self.rect())
        self._loading_overlay.raise_()
        self._loading_overlay.show()
        # Process events to show overlay immediately
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
    
    def _hide_loading(self):
        """Hide loading overlay"""
        self._loading_overlay.hide()
    
    def on_show(self) -> None:
        """View shown"""
        if not self._is_initialized:
            return
        self._refresh_data()
    
    def refresh(self) -> None:
        """Refresh data"""
        if not self._is_initialized:
            return
        self._refresh_data()
    
    def _refresh_data(self) -> None:
        """Refresh query data from service"""
        self._queries_list.clear()
        
        # Check connection
        if not self._service.is_connected:
            self._show_placeholder("Please connect to a database first.")
            logger.debug("Query stats refresh skipped: No active connection")
            return
        
        # Show loading
        self._show_loading("Loading queries...")
        
        # Build filter
        duration_map = {0: 1, 1: 7, 2: 30}
        order_map = {
            0: "impact_score",
            1: "avg_duration",
            2: "total_cpu",
            3: "execution_count",
            4: "logical_reads"
        }
        
        self._current_filter.days = duration_map.get(self._cmb_duration.currentIndex(), 1)
        self._current_filter.order_by = order_map.get(self._cmb_order.currentIndex(), "impact_score")
        
        try:
            self._queries = self._service.get_top_queries(self._current_filter)
            
            self._hide_loading()
            
            if not self._queries:
                self._show_placeholder("No queries matched this filter.")
                return
            
            for query in self._queries:
                self._add_query_item(query)
                
            logger.info(f"Loaded {len(self._queries)} queries")
            
        except Exception as e:
            self._hide_loading()
            logger.error(f"Failed to load queries: {e}")
            self._show_placeholder(f"Error loading queries: {str(e)}")
    
    def _show_placeholder(self, message: str) -> None:
        """Show placeholder message in list"""
        self._queries_list.clear()
        
        placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_widget)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        placeholder_label = QLabel(message)
        placeholder_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_MUTED};
                font-size: 14px;
                padding: 40px;
                background: transparent;
            }}
        """)
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)
        
        list_item = QListWidgetItem()
        list_item.setSizeHint(QSize(0, 120))
        self._queries_list.addItem(list_item)
        self._queries_list.setItemWidget(list_item, placeholder_widget)


class QueryDetailDialog(QDialog):
    """Query Detail Dialog - GUI-05 Style"""
    
    def __init__(self, query: QueryStats, service: QueryStatsService, parent=None):
        super().__init__(parent)
        self.query = query
        self.service = service
        self.setWindowTitle(query.display_name)
        self.setMinimumSize(1200, 700)
        self.resize(1200, 700)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ═══════════════════════════════════════════════════════════
        # HEADER
        # ═══════════════════════════════════════════════════════════
        header = QFrame()
        header.setStyleSheet(f"background-color: {Colors.SURFACE}; border-bottom: 1px solid {Colors.BORDER};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(12)
        
        # Back button
        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #f3f4f6;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        back_btn.clicked.connect(self.reject)
        header_layout.addWidget(back_btn)
        
        # Title
        title_label = QLabel(self.query.display_name)
        title_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-weight: 600;
            font-size: 16px;
            padding: 4px 8px;
            border-radius: 6px;
            background-color: #f8fafc;
            border: 1px solid {Colors.BORDER};
        """)
        title_label.setMaximumWidth(700)
        fm = QFontMetrics(title_label.font())
        elided = fm.elidedText(self.query.display_name, Qt.TextElideMode.ElideRight, 680)
        title_label.setText(elided)
        title_label.setToolTip(self.query.display_name)
        header_layout.addWidget(title_label, stretch=1)
        
        # Analyze with AI button
        analyze_btn = QPushButton("Analyze with AI")
        analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        analyze_btn.clicked.connect(self._analyze_with_ai)
        header_layout.addWidget(analyze_btn)
        
        main_layout.addWidget(header)
        
        # ═══════════════════════════════════════════════════════════
        # STATS ROW
        # ═══════════════════════════════════════════════════════════
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"background-color: {Colors.SURFACE}; border-bottom: 1px solid {Colors.BORDER};")
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(20, 12, 20, 12)
        stats_layout.setSpacing(16)
        
        metrics = self.query.metrics
        stats_data = [
            ("Avg Duration", f"{metrics.avg_duration_ms:.0f}ms"),
            ("P95 Duration", f"{metrics.p95_duration_ms:.0f}ms"),
            ("Avg CPU", f"{metrics.avg_cpu_ms:.0f}ms"),
            ("Avg Reads", f"{metrics.avg_logical_reads:,.0f}"),
            ("Executions", f"{metrics.total_executions:,}"),
            ("Plans", f"{metrics.plan_count}")
        ]
        
        for label_text, value_text in stats_data:
            stat_card = create_circle_stat_card(label_text, value_text, "#6366f1")
            stats_layout.addWidget(stat_card)
        
        stats_layout.addStretch()
        main_layout.addWidget(stats_frame)
        
        # ═══════════════════════════════════════════════════════════
        # CONTENT AREA
        # ═══════════════════════════════════════════════════════════
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 16, 20, 20)
        content_layout.setSpacing(16)
        
        # Left side - Tabbed content (Source Code & Execution Plan)
        left_panel = QFrame()
        left_panel.setStyleSheet(f"background-color: {Colors.SURFACE}; border: 1px solid {Colors.BORDER}; border-radius: 10px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Tab widget for Source Code and Execution Plan
        self._content_tabs = QTabWidget()
        self._content_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {Colors.SURFACE};
                border: none;
                border-top: 1px solid {Colors.BORDER};
            }}
            QTabBar::tab {{
                background-color: transparent;
                border: none;
                border-bottom: 3px solid transparent;
                padding: 10px 16px;
                color: {Colors.TEXT_SECONDARY};
                font-weight: 500;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                color: {Colors.PRIMARY};
                border-bottom-color: {Colors.PRIMARY};
                font-weight: 600;
            }}
            QTabBar::tab:hover:!selected {{
                color: {Colors.TEXT_PRIMARY};
                background-color: rgba(14, 138, 157, 0.06);
            }}
        """)
        
        # Tab 1: Source Code
        source_tab = QWidget()
        source_tab.setStyleSheet("background: transparent;")
        source_layout = QVBoxLayout(source_tab)
        source_layout.setContentsMargins(14, 12, 14, 12)
        source_layout.setSpacing(8)
        
        self._code_editor = CodeEditor()
        self._code_editor.setReadOnly(True)
        source_layout.addWidget(self._code_editor, stretch=1)
        
        self._content_tabs.addTab(source_tab, "📝 Source Code")
        
        # Tab 2: Execution Plan
        plan_tab = QWidget()
        plan_tab.setStyleSheet(f"background: {Colors.BACKGROUND};")
        plan_layout = QVBoxLayout(plan_tab)
        plan_layout.setContentsMargins(8, 8, 8, 8)
        plan_layout.setSpacing(0)
        
        self._plan_viewer = PlanViewerWidget()
        self._plan_viewer.set_plan_stability(self.query.plan_stability, self.query.metrics.plan_count)
        plan_layout.addWidget(self._plan_viewer)
        
        self._content_tabs.addTab(plan_tab, "📊 Execution Plan")

        # Tab 3: AI Analysis
        ai_tab = QWidget()
        ai_tab.setStyleSheet("background: transparent;")
        ai_layout = QVBoxLayout(ai_tab)
        ai_layout.setContentsMargins(14, 12, 14, 12)
        ai_layout.setSpacing(8)

        ai_title = QLabel("🤖 AI Analysis")
        ai_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600; font-size: 12px;")
        ai_layout.addWidget(ai_title)

        self._ai_result_label = QLabel("Click 'Analyze with AI' above to run analysis.")
        self._ai_result_label.setWordWrap(True)
        self._ai_result_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 11px;
            background-color: #f8fafc;
            border: 1px dashed {Colors.BORDER};
            border-radius: 6px;
            padding: 10px;
        """)
        ai_layout.addWidget(self._ai_result_label, stretch=1)

        self._content_tabs.addTab(ai_tab, "🤖 AI Analysis")
        
        left_layout.addWidget(self._content_tabs)
        content_layout.addWidget(left_panel, stretch=1)
        
        main_layout.addWidget(content_widget, stretch=1)
        
        # Load source code and execution plan
        self._load_source_code()
        self._load_execution_plan()
    
    def _load_source_code(self):
        """Load source code for the query"""
        try:
            # Prefer object definition when object name is available
            if self.query.object_name:
                definition = self.service.get_object_definition(
                    self.query.object_name,
                    getattr(self.query, 'schema_name', None)
                )
                if definition:
                    self._code_editor.set_text(definition)
                    return

            # Fallback to query text
            query_text = getattr(self.query, 'query_text', None)
            if query_text:
                self._code_editor.set_text(query_text)
                return

            # Try to get from service (Query Store)
            code = self.service.get_query_text(self.query.query_id)
            if code:
                self._code_editor.set_text(code)
            else:
                if self.query.object_name:
                    self._code_editor.set_text(
                        f"-- Object: {self.query.display_name}\n"
                        "-- Definition not available (permissions or encrypted object).\n"
                        f"-- Query ID: {self.query.query_id}"
                    )
                else:
                    self._code_editor.set_text(
                        f"-- Query ID: {self.query.query_id}\n-- Source code not available"
                    )
        except Exception as e:
            logger.error(f"Failed to load source code: {e}")
            self._code_editor.set_text(f"-- Error loading source code: {e}")
    
    def _load_execution_plan(self):
        """Load execution plan for the query"""
        try:
            logger.debug(f"Loading execution plan for query_id: {self.query.query_id}")
            
            # Get plan XML from service
            plan_xml = self.service.get_query_plan_xml(self.query.query_id)
            
            if plan_xml:
                logger.debug(f"Got plan XML ({len(plan_xml)} chars), parsing...")
                # Parse the plan
                parser = PlanParser()
                plan = parser.parse(plan_xml)
                
                if plan:
                    self._plan_viewer.set_plan(plan)
                    
                    # Update tab title with warnings count
                    warning_count = len(plan.warnings)
                    missing_count = len(plan.missing_indexes)
                    
                    if warning_count > 0 or missing_count > 0:
                        self._content_tabs.setTabText(1, f"📊 Execution Plan ⚠️")
                    else:
                        self._content_tabs.setTabText(1, "📊 Execution Plan")
                    
                    logger.info(f"Loaded execution plan with {plan.operator_count} operators")
                else:
                    self._plan_viewer.set_plan(None)
                    logger.warning("Failed to parse execution plan XML")
            else:
                self._plan_viewer.set_plan(None)
                logger.info(f"No execution plan available for query_id: {self.query.query_id}")
                
        except Exception as e:
            logger.error(f"Failed to load execution plan: {e}", exc_info=True)
            self._plan_viewer.set_plan(None)
    
    def _analyze_with_ai(self):
        """Run AI analysis on the query"""
        try:
            from app.ui.components.ai_dialog import AIAnalysisDialog
            
            # Build richer context for AI
            query_text = ""
            if hasattr(self._code_editor, 'toPlainText'):
                query_text = self._code_editor.toPlainText()
            elif hasattr(self._code_editor, 'text'):
                query_text = self._code_editor.text()

            # Try to pull richer details from Query Store
            detail = self.service.get_query_detail(self.query.query_id, days=7) or self.query
            metrics = detail.metrics if detail else self.query.metrics

            wait_profile = {}
            if hasattr(detail, 'wait_profile') and detail.wait_profile:
                for w in detail.wait_profile:
                    wait_profile[w.display_name] = w.wait_percent

            stats_table = [
                {"metric": "Avg Duration", "value": f"{metrics.avg_duration_ms:.0f}", "unit": "ms"},
                {"metric": "P95 Duration", "value": f"{metrics.p95_duration_ms:.0f}", "unit": "ms"},
                {"metric": "Avg CPU", "value": f"{metrics.avg_cpu_ms:.0f}", "unit": "ms"},
                {"metric": "Avg Logical Reads", "value": f"{metrics.avg_logical_reads:,.0f}", "unit": ""},
                {"metric": "Executions", "value": f"{metrics.total_executions:,}", "unit": ""},
                {"metric": "Plan Count", "value": f"{metrics.plan_count}", "unit": ""},
            ]

            # Pull minimal server metrics for performance context
            server_metrics = {}
            try:
                from app.services.dashboard_service import get_dashboard_service
                dash_service = get_dashboard_service()
                if dash_service.is_connected:
                    dash = dash_service.get_all_metrics()
                    server_metrics = {
                        "os_cpu_percent": dash.cpu_percent,
                        "sql_cpu_percent": dash.sql_cpu_percent,
                        "available_memory_mb": dash.available_memory_mb,
                        "ple_seconds": dash.ple_seconds,
                        "buffer_cache_hit_ratio": dash.buffer_cache_hit_ratio,
                        "batch_requests_per_sec": dash.batch_requests,
                        "transactions_per_sec": dash.transactions_per_sec,
                        "io_read_latency_ms": int(dash.read_latency_ms),
                        "io_write_latency_ms": int(dash.write_latency_ms),
                        "log_write_latency_ms": int(dash.log_write_latency_ms),
                        "signal_wait_percent": dash.signal_wait_percent,
                    }
            except Exception as e:
                logger.debug(f"Failed to load server metrics for AI context: {e}")

            context = {
                'query_name': self.query.display_name,
                'query_id': self.query.query_id,
                'query_text': query_text,
                'object_name': getattr(detail, 'object_name', None) or self.query.object_name,
                'schema_name': getattr(detail, 'schema_name', None) or getattr(self.query, 'schema_name', None),
                'metrics': {
                    'avg_duration_ms': metrics.avg_duration_ms,
                    'p95_duration_ms': metrics.p95_duration_ms,
                    'avg_cpu_ms': metrics.avg_cpu_ms,
                    'avg_logical_reads': metrics.avg_logical_reads,
                    'total_executions': metrics.total_executions,
                    'plan_count': metrics.plan_count,
                    'change_percent': metrics.change_percent,
                },
                'wait_profile': wait_profile,
                'plan_stability': detail.plan_stability.value if detail and detail.plan_stability else 'unknown',
                'stats_table': stats_table,
                'server_metrics': server_metrics,
            }
            
            # Dialog otomatik olarak analizi başlatır
            dialog = AIAnalysisDialog(context, self, auto_start=True)
            if dialog.exec():
                # Update AI result label with summary
                result = dialog.get_result()
                if result:
                    # Sonucu kısalt ve göster
                    display_text = result[:500] + "..." if len(result) > 500 else result
                    self._ai_result_label.setText(display_text)
                    self._ai_result_label.setStyleSheet(f"""
                        QLabel {{
                            color: {Colors.TEXT_PRIMARY};
                            font-size: 11px;
                            background-color: #f0fdf4;
                            border: 1px solid #d1fae5;
                            border-radius: 6px;
                            padding: 10px;
                        }}
                    """)
        except ImportError as e:
            logger.error(f"AI module not available: {e}")
            QMessageBox.information(self, "AI Analysis", "AI analysis module not available.")
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            QMessageBox.warning(self, "Error", f"AI analysis failed: {e}")
