"""
Blocking Analysis View - Real-time blocking chain visualization
"""

from typing import Optional, List, Dict
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QSplitter, QTextEdit, QTableWidget, QTableWidgetItem,
    QFrame, QHeaderView, QMessageBox, QMenu, QGroupBox,
    QGridLayout, QScrollArea, QGraphicsView, QGraphicsScene, QFileDialog,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem, QGraphicsPolygonItem,
    QGraphicsRectItem, QTabWidget, QComboBox, QSpinBox, QLineEdit, QApplication,
    QSystemTrayIcon
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPointF, QRectF, QPropertyAnimation
from PyQt6.QtGui import QFont, QColor, QPen, QBrush, QPainter, QImage, QPolygonF

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors, Theme as ThemeStyles
from app.ui.components.modern_combobox import ModernComboBox, SearchableComboBox
from app.core.config import get_settings
from app.core.logger import get_logger
from app.models.blocking_models import BlockingSession, LockInfo
from app.services.blocking_service import BlockingService, BlockingChainAnalysis
from app.services.blocking_exceptions import (
    ConnectionError as BlockingConnectionError,
    QueryExecutionError as BlockingQueryExecutionError,
    BlockingAnalysisError,
)

logger = get_logger('ui.blocking_view')


class BlockingWorker(QThread):
    """Background worker for fetching blocking data"""
    
    data_ready = pyqtSignal(list, list, dict)  # blocking_sessions, head_blockers, lock_details
    error_occurred = pyqtSignal(str)

    def __init__(self, service: Optional[BlockingService] = None, parent=None):
        super().__init__(parent)
        self._service = service or BlockingService()
    
    def run(self):
        """Fetch blocking information"""
        try:
            if not self._service.is_connected:
                raise BlockingConnectionError("No active database connection.")
            analysis = self._service.analyze_blocking_chains()
            self.data_ready.emit(
                analysis.blocking_sessions,
                analysis.head_blocker_rows,
                analysis.lock_details_by_session,
            )
        except BlockingConnectionError as e:
            self.error_occurred.emit(f"Connection error: {e}")
        except BlockingQueryExecutionError as e:
            self.error_occurred.emit(f"Query execution error: {e}")
        except BlockingAnalysisError as e:
            self.error_occurred.emit(f"Blocking analysis error: {e}")
        except Exception as e:
            logger.error(f"Blocking worker error: {e}")
            self.error_occurred.emit(f"Unexpected error: {e}")


class BlockingGraphWidget(QGraphicsView):
    """Visual graph representation of blocking chains"""
    
    session_selected = pyqtSignal(int)  # session_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        
        self._nodes: Dict[int, object] = {}
        self._edges: List[QGraphicsLineItem] = []
        self._labels: Dict[int, QGraphicsTextItem] = {}
        self._zoom_factor: float = 1.0
        
    def clear_graph(self):
        """Clear all graph elements"""
        self._scene.clear()
        self._nodes.clear()
        self._edges.clear()
        self._labels.clear()
        self.resetTransform()
        self._zoom_factor = 1.0
    
    def build_graph(self, blocking_sessions: List[BlockingSession], head_blockers: List[Dict]):
        """Build the blocking chain graph"""
        self.clear_graph()
        
        if not blocking_sessions and not head_blockers:
            # Show "No blocking" message
            text = self._scene.addText("No Active Blocking")
            text.setDefaultTextColor(QColor(Colors.SUCCESS))
            text.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            text.setPos(50, 50)
            return
        
        # Collect all unique sessions and blocking edges
        all_sessions: set[int] = set()
        edges: list[tuple[int, int, BlockingSession]] = []
        session_by_id: Dict[int, BlockingSession] = {}
        for session in list(blocking_sessions or []):
            blocker_id = int(session.blocking_session_id or 0)
            blocked_id = int(session.session_id or 0)
            if blocker_id <= 0 or blocked_id <= 0:
                continue
            all_sessions.add(blocker_id)
            all_sessions.add(blocked_id)
            edges.append((blocker_id, blocked_id, session))
            session_by_id[blocked_id] = session
        
        # Identify head blockers (sessions that block others but aren't blocked)
        blockers = {int(s.blocking_session_id or 0) for s in blocking_sessions if int(s.blocking_session_id or 0) > 0}
        blocked = {int(s.session_id or 0) for s in blocking_sessions if int(s.session_id or 0) > 0}
        head_blocker_ids = blockers - blocked
        if not head_blocker_ids:
            head_blocker_ids = {
                int(row.get("head_blocker_session", 0))
                for row in list(head_blockers or [])
                if int(row.get("head_blocker_session", 0)) > 0
            }
        
        # Layout nodes in a tree structure
        raw_edges = [(blocker_id, blocked_id, float(session.wait_seconds or 0.0)) for blocker_id, blocked_id, session in edges]
        levels = self._calculate_levels(all_sessions, raw_edges, set(head_blocker_ids))
        level_by_session: Dict[int, int] = {}
        for level, sessions in levels.items():
            for sid in sessions:
                level_by_session[int(sid)] = int(level)
        
        node_radius = 35
        h_spacing = 120
        v_spacing = 100
        
        # Position nodes
        positions = {}
        for level, sessions in sorted(levels.items()):
            y = level * v_spacing + 50
            total_width = len(sessions) * h_spacing
            start_x = (600 - total_width) / 2 + h_spacing / 2
            
            for i, sid in enumerate(sorted(sessions)):
                x = start_x + i * h_spacing
                positions[sid] = (x, y)
        
        max_wait_seconds = max((float(item.wait_seconds or 0.0) for item in blocking_sessions), default=1.0)

        # Draw edges first (so they appear behind nodes)
        for blocker_id, blocked_id, blocked_session in edges:
            if blocker_id in positions and blocked_id in positions:
                x1, y1 = positions[blocker_id]
                x2, y2 = positions[blocked_id]

                ratio = max(0.0, min(1.0, float(blocked_session.wait_seconds or 0.0) / max(1.0, max_wait_seconds)))
                red = 76 + int(180 * ratio)
                green = 175 - int(110 * ratio)
                blue = 80 - int(30 * ratio)
                color = QColor(max(0, min(255, red)), max(0, min(255, green)), max(0, min(255, blue)))
                width = 1.0 + (3.0 * ratio)
                pen = QPen(color, width)
                line = self._scene.addLine(x1, y1 + node_radius, x2, y2 - node_radius, pen)
                self._edges.append(line)
                
                # Add wait time label on edge
                mid_x = (x1 + x2) / 2
                mid_y = (y1 + y2) / 2
                wait_label = self._scene.addText(blocked_session.format_wait_time())
                wait_label.setDefaultTextColor(color)
                wait_label.setFont(QFont("Segoe UI", 9))
                wait_label.setPos(mid_x + 5, mid_y - 10)
        
        # Draw nodes
        for sid, (x, y) in positions.items():
            is_head = sid in head_blocker_ids
            blocked_session = session_by_id.get(int(sid))
            node_depth = int(level_by_session.get(int(sid), 0))
            
            # Node color
            if is_head:
                color = QColor("#EF4444")  # Red for head blockers
                border_color = QColor("#B91C1C")
            elif blocked_session is not None:
                color = QColor(str(blocked_session.severity_color))
                border_color = color.darker(140)
            else:
                color = QColor("#3B82F6")  # Blue for others
                border_color = QColor("#1D4ED8")
            
            # Draw node: head blockers as diamond, blocked sessions as circles.
            if is_head:
                diamond = QPolygonF(
                    [
                        QPointF(x, y - node_radius),
                        QPointF(x + node_radius, y),
                        QPointF(x, y + node_radius),
                        QPointF(x - node_radius, y),
                    ]
                )
                node = self._scene.addPolygon(diamond, QPen(border_color, 3), QBrush(color))
            else:
                node = self._scene.addEllipse(
                    x - node_radius,
                    y - node_radius,
                    node_radius * 2,
                    node_radius * 2,
                    QPen(border_color, 3),
                    QBrush(color),
                )
            node.setData(0, sid)  # Store session_id
            self._nodes[sid] = node
            
            # Session ID label
            label = self._scene.addText(str(sid))
            label.setDefaultTextColor(QColor("white"))
            label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            label.setPos(x - 15, y - 10)
            self._labels[sid] = label
            depth_label = self._scene.addText(f"D{node_depth}")
            depth_label.setDefaultTextColor(QColor(Colors.TEXT_SECONDARY))
            depth_label.setFont(QFont("Segoe UI", 8))
            depth_label.setPos(x - 10, y + node_radius + 2)
            
            # Head blocker indicator
            if is_head:
                pass
        
        # Adjust scene rect
        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
    
    def _calculate_levels(self, all_sessions: set, edges: list, head_blocker_ids: set) -> Dict[int, set]:
        """Calculate tree levels for sessions"""
        levels = {}
        
        # Head blockers are level 0
        levels[0] = head_blocker_ids.copy() if head_blocker_ids else set()
        
        # Build adjacency for blocked sessions
        blocking_map = {}  # blocker -> [blocked]
        for blocker_id, blocked_id, _ in edges:
            if blocker_id not in blocking_map:
                blocking_map[blocker_id] = []
            blocking_map[blocker_id].append(blocked_id)
        
        # BFS to assign levels
        assigned = set(levels[0])
        current_level = 0
        
        while len(assigned) < len(all_sessions):
            current_level += 1
            levels[current_level] = set()
            
            for sid in levels[current_level - 1]:
                if sid in blocking_map:
                    for blocked_id in blocking_map[sid]:
                        if blocked_id not in assigned:
                            levels[current_level].add(blocked_id)
                            assigned.add(blocked_id)
            
            # Safety: add any remaining sessions
            if not levels[current_level]:
                for sid in all_sessions - assigned:
                    levels[current_level].add(sid)
                    assigned.add(sid)
                break
        
        return levels
    
    def mousePressEvent(self, event):
        """Handle click on nodes"""
        item = self.itemAt(event.pos())
        if item:
            sid = item.data(0)
            if sid is None and item.parentItem() is not None:
                sid = item.parentItem().data(0)
            if sid:
                self.session_selected.emit(int(sid))
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        if angle == 0:
            return
        step = 1.15 if angle > 0 else 0.87
        new_zoom = self._zoom_factor * step
        if new_zoom < 0.3 or new_zoom > 3.5:
            return
        self._zoom_factor = new_zoom
        self.scale(step, step)

    @property
    def scene_ref(self) -> QGraphicsScene:
        return self._scene


class StatCard(QFrame):
    """Stat card for footer summary (Blocking Analysis)."""

    # Footer cards in Blocking Analysis (bottom-right). Slightly larger than the compact default.
    CIRCLE_SCALE = 0.62
    BASE_CIRCLE_SIZE = 98
    BASE_VALUE_FONT_SIZE = 18
    BASE_TITLE_FONT_SIZE = 10
    
    STATUS_COLORS = {
        "error": Colors.ERROR,
        "warning": "#F59E0B",
        "success": Colors.SUCCESS,
        "normal": Colors.TEXT_PRIMARY,
    }
    
    def __init__(self, title: str, value: str, icon: str, status: str = "normal"):
        super().__init__()
        self._status = status
        self._setup_ui(title, value, icon, status)
    
    def _setup_ui(self, title: str, value: str, icon: str, status: str):
        self.setStyleSheet("background-color: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        # Square tile
        circle_size = max(28, int(self.BASE_CIRCLE_SIZE * self.CIRCLE_SCALE))
        circle_radius = max(6, min(12, int(circle_size * 0.2)))
        circle = QFrame()
        circle.setFixedSize(circle_size, circle_size)
        circle.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {circle_radius}px;
            }}
        """)
        circle_layout = QVBoxLayout(circle)
        circle_layout.setContentsMargins(0, 0, 0, 0)
        circle_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Value
        color = self.STATUS_COLORS.get(status, Colors.SUCCESS)
        value_font_size = max(11, int(self.BASE_VALUE_FONT_SIZE * self.CIRCLE_SCALE))
        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(
            f"color: {color}; font-size: {value_font_size}px; font-weight: 700; background: transparent; border: none;"
        )
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle_layout.addWidget(self._value_label)

        title_text = f"{icon} {title}".strip() if str(icon or "").strip() else str(title)
        title_font_size = max(9, int(self.BASE_TITLE_FONT_SIZE * self.CIRCLE_SCALE))
        title_label = QLabel(title_text)
        title_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: {title_font_size}px; font-weight: 700; background: transparent;"
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setWordWrap(True)

        layout.addWidget(circle)
        layout.addWidget(title_label)
    
    def update_value(self, value: str, status: str = "normal"):
        color = self.STATUS_COLORS.get(status, Colors.SUCCESS)
        value_font_size = max(11, int(self.BASE_VALUE_FONT_SIZE * self.CIRCLE_SCALE))
        self._value_label.setText(value)
        self._value_label.setStyleSheet(
            f"color: {color}; font-size: {value_font_size}px; font-weight: 700; background: transparent; border: none;"
        )


class BlockingView(BaseView):
    """
    Blocking Analysis View
    
    Features:
    - Real-time blocking chain visualization (tree/graph)
    - Head blocker identification
    - Session details panel
    - Kill session capability
    - Auto-refresh
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocking_service = BlockingService()
        self._notification_rules = self._blocking_service.load_notification_rules()
        self._webhook_settings = self._blocking_service.load_webhook_settings()
        self._blocking_sessions: List[BlockingSession] = []
        self._filtered_sessions: List[BlockingSession] = []
        self._head_blockers: List[Dict] = []
        self._lock_details: Dict[int, List] = {}
        self._visible_lock_rows: List[Dict[str, str]] = []
        self._selected_session: Optional[int] = None
        self._worker: Optional[BlockingWorker] = None
        self._history_rows: List[Dict] = []
        self._latest_alerts = []
        self._last_notification_key: str = ""
        self._last_notification_at: Optional[datetime] = None
        self._notification_cooldown_seconds: int = 60
        self._saved_filters: Dict[str, Dict[str, object]] = {}
        self._inspector_animation: Optional[QPropertyAnimation] = None
        self._last_error_popup_message: str = ""
        self._last_error_popup_at: Optional[datetime] = None
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self.refresh)
    
    @property
    def view_title(self) -> str:
        return "Blocking Analysis"
    
    def _setup_ui(self) -> None:
        """Setup the blocking view UI"""
        primary_btn_style = f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                color: white;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER_DARK};
                color: {Colors.TEXT_MUTED};
            }}
        """
        ghost_btn_style = f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 8px;
                padding: 8px 14px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {Colors.PRIMARY};
                color: {Colors.PRIMARY};
                background-color: {Colors.PRIMARY_LIGHT};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER_LIGHT};
                color: {Colors.TEXT_MUTED};
                border-color: {Colors.BORDER};
            }}
        """
        danger_btn_style = """
            QPushButton {
                background: #D32F2F;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #B71C1C;
            }
            QPushButton:disabled {
                background: #F4C7C3;
                color: #8A1C1C;
            }
        """
        chip_btn_style = f"""
            QPushButton {{
                background: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 8px;
                padding: 6px 12px;
                color: {Colors.TEXT_PRIMARY};
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {Colors.PRIMARY};
                background: {Colors.PRIMARY_LIGHT};
            }}
            QPushButton:checked {{
                background: {Colors.PRIMARY};
                border-color: {Colors.PRIMARY};
                color: white;
            }}
        """

        # Header
        header_layout = QHBoxLayout()
        
        header_layout.addStretch()
        
        # Auto-refresh toggle
        self._auto_refresh_btn = QPushButton("Auto-Refresh: ON")
        self._auto_refresh_btn.setCheckable(True)
        self._auto_refresh_btn.setChecked(True)
        self._auto_refresh_btn.clicked.connect(self._toggle_auto_refresh)
        self._auto_refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 8px;
                padding: 8px 16px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_LIGHT};
                border-color: {Colors.PRIMARY};
            }}
            QPushButton:checked {{
                background-color: {Colors.PRIMARY};
                color: white;
                border-color: {Colors.PRIMARY};
            }}
        """)
        header_layout.addWidget(self._auto_refresh_btn)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Now")
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setStyleSheet(primary_btn_style)
        header_layout.addWidget(refresh_btn)

        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.clicked.connect(self._export_snapshot_csv)
        export_csv_btn.setStyleSheet(ghost_btn_style)
        header_layout.addWidget(export_csv_btn)

        export_report_btn = QPushButton("Report")
        export_report_btn.clicked.connect(self._generate_blocking_report)
        export_report_btn.setStyleSheet(ghost_btn_style)
        header_layout.addWidget(export_report_btn)

        export_audit_btn = QPushButton("Audit CSV")
        export_audit_btn.clicked.connect(self._export_audit_csv)
        export_audit_btn.setStyleSheet(ghost_btn_style)
        header_layout.addWidget(export_audit_btn)

        export_history_btn = QPushButton("History CSV")
        export_history_btn.clicked.connect(self._export_history_csv)
        export_history_btn.setStyleSheet(ghost_btn_style)
        header_layout.addWidget(export_history_btn)

        ai_brief_btn = QPushButton("AI Brief")
        ai_brief_btn.clicked.connect(self._show_ai_brief)
        ai_brief_btn.setStyleSheet(ghost_btn_style)
        header_layout.addWidget(ai_brief_btn)
        
        self._main_layout.addLayout(header_layout)

        self._severity_banner = QLabel("No active critical blocking")
        self._severity_banner.setStyleSheet(
            "background: #E8F5E9; color: #1B5E20; border: 1px solid #A5D6A7; "
            "border-radius: 8px; padding: 8px 12px; font-weight: 600;"
        )
        self._main_layout.addWidget(self._severity_banner)

        self._quick_summary_label = QLabel("0 Critical | 0 Medium | 0 Low")
        self._quick_summary_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        self._main_layout.addWidget(self._quick_summary_label)

        quick_action_box = QGroupBox("Quick Action Panel")
        quick_action_box.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
                background: {Colors.SURFACE};
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }}
        """)
        quick_action_layout = QHBoxLayout(quick_action_box)
        quick_action_layout.setContentsMargins(10, 10, 10, 10)
        self._quick_action_label = QLabel("No blocker recommendation yet.")
        self._quick_action_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        quick_action_layout.addWidget(self._quick_action_label, 1)
        self._investigate_top_btn = QPushButton("Investigate")
        self._investigate_top_btn.clicked.connect(self._investigate_top_blocker)
        self._investigate_top_btn.setEnabled(False)
        self._investigate_top_btn.setStyleSheet(ghost_btn_style)
        quick_action_layout.addWidget(self._investigate_top_btn)
        self._kill_top_btn = QPushButton("Kill Top Blocker")
        self._kill_top_btn.setEnabled(False)
        self._kill_top_btn.clicked.connect(self._kill_top_blocker)
        self._kill_top_btn.setStyleSheet(danger_btn_style)
        quick_action_layout.addWidget(self._kill_top_btn)
        self._main_layout.addWidget(quick_action_box)

        # Summary cards (moved to footer bottom-right)
        self._total_blocking_card = StatCard("Total Blocking", "0", "", "success")
        self._head_blocker_card = StatCard("Head Blockers", "0", "", "success")
        self._max_wait_card = StatCard("Max Wait", "0s", "", "success")
        self._affected_card = StatCard("Affected Sessions", "0", "", "success")
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: transparent;
                width: 8px;
            }
        """)
        
        # Left panel: Graph + Tree (card container like Query Statistics)
        left_widget = QFrame()
        left_widget.setObjectName("Card")
        left_widget.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(16)
        
        # Tab-based navigation: Filter, Timeline, Tree, Graph, Details
        self._view_tabs = QTabWidget()
        self._view_tabs.setStyleSheet(ThemeStyles.tab_widget_style())

        filter_tab = QWidget()
        filter_tab.setStyleSheet(f"background-color: {Colors.SURFACE};")
        filter_tab_layout = QVBoxLayout(filter_tab)
        filter_tab_layout.setContentsMargins(0, 0, 0, 0)
        filter_tab_layout.setSpacing(0)

        filter_scroll = QScrollArea()
        filter_scroll.setWidgetResizable(True)
        filter_scroll.setFrameShape(QFrame.Shape.NoFrame)
        filter_scroll.setStyleSheet("border: none; background: transparent;")
        filter_tab_layout.addWidget(filter_scroll)

        filter_content = QWidget()
        filter_content.setObjectName("BlockingFilterContent")
        filter_content.setStyleSheet(f"""
            QWidget#BlockingFilterContent {{
                background: transparent;
            }}
            QWidget#BlockingFilterContent QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
                font-weight: 600;
            }}
            QWidget#BlockingFilterContent QGroupBox {{
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 10px;
                margin-top: 7px;
                padding-top: 11px;
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                font-weight: 600;
            }}
            QWidget#BlockingFilterContent QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                font-size: 13px;
                font-weight: 600;
                color: {Colors.TEXT_HEADER};
                background-color: {Colors.SURFACE};
            }}
            QWidget#BlockingFilterContent QLineEdit,
            QWidget#BlockingFilterContent QSpinBox {{
                min-height: 28px;
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 6px;
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                padding: 2px 7px;
            }}
            QWidget#BlockingFilterContent QLineEdit:focus,
            QWidget#BlockingFilterContent QSpinBox:focus {{
                border-color: {Colors.PRIMARY};
            }}
        """)
        filter_layout = QVBoxLayout(filter_content)
        filter_layout.setContentsMargins(9, 9, 9, 11)
        filter_layout.setSpacing(9)

        quick_filter_group = QGroupBox("Quick Filters")
        quick_filter_layout = QHBoxLayout(quick_filter_group)
        quick_filter_layout.setContentsMargins(9, 9, 9, 9)
        quick_filter_layout.setSpacing(7)
        self._critical_only_btn = QPushButton("Critical Only")
        self._critical_only_btn.setCheckable(True)
        self._critical_only_btn.clicked.connect(self._on_filter_changed)
        self._critical_only_btn.setStyleSheet(chip_btn_style)
        quick_filter_layout.addWidget(self._critical_only_btn)
        self._production_only_btn = QPushButton("Production DB")
        self._production_only_btn.setCheckable(True)
        self._production_only_btn.clicked.connect(self._on_filter_changed)
        self._production_only_btn.setStyleSheet(chip_btn_style)
        quick_filter_layout.addWidget(self._production_only_btn)
        self._head_only_btn = QPushButton("Head Blockers")
        self._head_only_btn.setCheckable(True)
        self._head_only_btn.clicked.connect(self._on_filter_changed)
        self._head_only_btn.setStyleSheet(chip_btn_style)
        quick_filter_layout.addWidget(self._head_only_btn)
        quick_filter_layout.addStretch()
        filter_layout.addWidget(quick_filter_group)

        advanced_group = QGroupBox("Advanced Filters")
        advanced_grid = QGridLayout(advanced_group)
        advanced_grid.setContentsMargins(9, 9, 9, 9)
        advanced_grid.setHorizontalSpacing(7)
        advanced_grid.setVerticalSpacing(7)

        advanced_grid.addWidget(QLabel("Database"), 0, 0)
        self._filter_db_combo = SearchableComboBox("Search database...")
        self._filter_db_combo.currentIndexChanged.connect(self._on_filter_changed)
        advanced_grid.addWidget(self._filter_db_combo, 0, 1)

        advanced_grid.addWidget(QLabel("User"), 0, 2)
        self._filter_user_combo = SearchableComboBox("Search user...")
        self._filter_user_combo.currentIndexChanged.connect(self._on_filter_changed)
        advanced_grid.addWidget(self._filter_user_combo, 0, 3)

        advanced_grid.addWidget(QLabel("Application"), 1, 0)
        self._filter_app_combo = SearchableComboBox("Search application...")
        self._filter_app_combo.currentIndexChanged.connect(self._on_filter_changed)
        advanced_grid.addWidget(self._filter_app_combo, 1, 1)

        advanced_grid.addWidget(QLabel("Severity"), 1, 2)
        self._filter_severity_combo = ModernComboBox("Select severity")
        self._filter_severity_combo.addItems(["All", "Critical", "High", "Medium", "Low"])
        self._filter_severity_combo.set_item_description(0, "Show all severities.")
        self._filter_severity_combo.set_item_description(1, "Wait time >= 60 seconds.")
        self._filter_severity_combo.set_item_description(2, "Wait time between 30 and 60 seconds.")
        self._filter_severity_combo.set_item_description(3, "Wait time between 5 and 30 seconds.")
        self._filter_severity_combo.set_item_description(4, "Wait time below 5 seconds.")
        self._filter_severity_combo.currentIndexChanged.connect(self._on_filter_changed)
        advanced_grid.addWidget(self._filter_severity_combo, 1, 3)

        advanced_grid.addWidget(QLabel("Min Wait (ms)"), 2, 0)
        self._filter_min_wait_spin = QSpinBox()
        self._filter_min_wait_spin.setRange(0, 3_600_000)
        self._filter_min_wait_spin.setSingleStep(1000)
        self._filter_min_wait_spin.valueChanged.connect(self._on_filter_changed)
        advanced_grid.addWidget(self._filter_min_wait_spin, 2, 1)

        advanced_grid.addWidget(QLabel("Max Wait (ms)"), 2, 2)
        self._filter_max_wait_spin = QSpinBox()
        self._filter_max_wait_spin.setRange(0, 3_600_000)
        self._filter_max_wait_spin.setValue(0)
        self._filter_max_wait_spin.setSingleStep(1000)
        self._filter_max_wait_spin.valueChanged.connect(self._on_filter_changed)
        advanced_grid.addWidget(self._filter_max_wait_spin, 2, 3)
        filter_layout.addWidget(advanced_group)

        saved_group = QGroupBox("Saved Filters")
        saved_row = QHBoxLayout(saved_group)
        saved_row.setContentsMargins(9, 9, 9, 9)
        saved_row.setSpacing(7)
        self._saved_filter_combo = ModernComboBox("Select saved filter")
        saved_row.addWidget(self._saved_filter_combo, 1)
        apply_saved_btn = QPushButton("Apply Saved")
        apply_saved_btn.clicked.connect(self._apply_saved_filter)
        apply_saved_btn.setStyleSheet(ghost_btn_style)
        saved_row.addWidget(apply_saved_btn)
        save_current_btn = QPushButton("Save Current")
        save_current_btn.clicked.connect(self._save_current_filter)
        save_current_btn.setStyleSheet(ghost_btn_style)
        saved_row.addWidget(save_current_btn)
        delete_saved_btn = QPushButton("Delete")
        delete_saved_btn.clicked.connect(self._delete_saved_filter)
        delete_saved_btn.setStyleSheet(ghost_btn_style)
        saved_row.addWidget(delete_saved_btn)
        filter_layout.addWidget(saved_group)

        alert_group = QGroupBox("Smart Alerts")
        notification_row = QHBoxLayout(alert_group)
        notification_row.setContentsMargins(9, 9, 9, 9)
        notification_row.setSpacing(7)
        notification_row.addWidget(QLabel("DB contains"))
        self._alert_db_contains_input = QLineEdit()
        self._alert_db_contains_input.setPlaceholderText("prod")
        self._alert_db_contains_input.setText(str(self._notification_rules.database_contains or ""))
        notification_row.addWidget(self._alert_db_contains_input, 1)
        notification_row.addWidget(QLabel("Min Severity"))
        self._alert_min_severity_combo = ModernComboBox("Select alert severity")
        self._alert_min_severity_combo.addItems(["critical", "warning", "info"])
        self._alert_min_severity_combo.set_item_description(0, "Only critical alerts trigger notifications.")
        self._alert_min_severity_combo.set_item_description(1, "Critical and warning alerts trigger notifications.")
        self._alert_min_severity_combo.set_item_description(2, "All alerts trigger notifications.")
        self._set_combo_value(self._alert_min_severity_combo, str(self._notification_rules.min_severity or "critical"))
        notification_row.addWidget(self._alert_min_severity_combo)
        notification_row.addWidget(QLabel("Min Chain"))
        self._alert_min_chain_spin = QSpinBox()
        self._alert_min_chain_spin.setRange(1, 100)
        self._alert_min_chain_spin.setValue(int(self._notification_rules.min_chain_count or 1))
        notification_row.addWidget(self._alert_min_chain_spin)
        notification_row.addWidget(QLabel("Cooldown(s)"))
        self._notification_cooldown_spin = QSpinBox()
        self._notification_cooldown_spin.setRange(10, 3600)
        self._notification_cooldown_spin.setValue(self._notification_cooldown_seconds)
        self._notification_cooldown_spin.valueChanged.connect(self._on_notification_config_changed)
        notification_row.addWidget(self._notification_cooldown_spin)
        self._sound_alert_btn = QPushButton("Sound")
        self._sound_alert_btn.setCheckable(True)
        self._sound_alert_btn.setChecked(True)
        self._sound_alert_btn.setStyleSheet(chip_btn_style)
        notification_row.addWidget(self._sound_alert_btn)
        save_rules_btn = QPushButton("Save Rules")
        save_rules_btn.clicked.connect(self._save_notification_rules)
        save_rules_btn.setStyleSheet(primary_btn_style)
        notification_row.addWidget(save_rules_btn)
        filter_layout.addWidget(alert_group)

        webhook_group = QGroupBox("Webhook")
        webhook_row = QHBoxLayout(webhook_group)
        webhook_row.setContentsMargins(9, 9, 9, 9)
        webhook_row.setSpacing(7)
        self._webhook_enabled_btn = QPushButton("Webhook Enabled")
        self._webhook_enabled_btn.setCheckable(True)
        self._webhook_enabled_btn.setChecked(bool(self._webhook_settings.enabled))
        self._webhook_enabled_btn.setStyleSheet(chip_btn_style)
        webhook_row.addWidget(self._webhook_enabled_btn)
        webhook_row.addWidget(QLabel("URL"))
        self._webhook_url_input = QLineEdit()
        self._webhook_url_input.setPlaceholderText("https://hooks.slack.com/services/...")
        self._webhook_url_input.setText(str(self._webhook_settings.url or ""))
        webhook_row.addWidget(self._webhook_url_input, 1)
        webhook_row.addWidget(QLabel("Channel"))
        self._webhook_channel_input = QLineEdit()
        self._webhook_channel_input.setPlaceholderText("#dba-alerts")
        self._webhook_channel_input.setText(str(self._webhook_settings.channel or ""))
        webhook_row.addWidget(self._webhook_channel_input)
        save_webhook_btn = QPushButton("Save Webhook")
        save_webhook_btn.clicked.connect(self._save_webhook_settings)
        save_webhook_btn.setStyleSheet(ghost_btn_style)
        webhook_row.addWidget(save_webhook_btn)
        test_webhook_btn = QPushButton("Test Webhook")
        test_webhook_btn.clicked.connect(self._test_webhook_alert)
        test_webhook_btn.setStyleSheet(primary_btn_style)
        webhook_row.addWidget(test_webhook_btn)
        filter_layout.addWidget(webhook_group)
        filter_layout.addStretch()

        ThemeStyles.style_comboboxes_in_widget(filter_content)

        filter_scroll.setWidget(filter_content)
        self._view_tabs.addTab(filter_tab, "Filter")

        # Graph view tab
        graph_tab = QWidget()
        graph_layout = QVBoxLayout(graph_tab)
        graph_layout.setContentsMargins(6, 6, 6, 6)
        graph_layout.setSpacing(6)
        self._graph_widget = BlockingGraphWidget()
        self._graph_widget.session_selected.connect(self._on_session_selected)
        graph_layout.addWidget(self._graph_widget, 1)
        graph_bottom_row = QHBoxLayout()
        export_graph_btn = QPushButton("Export PNG")
        export_graph_btn.clicked.connect(self._export_graph_png)
        export_graph_btn.setStyleSheet(ghost_btn_style)
        graph_bottom_row.addWidget(export_graph_btn)
        graph_bottom_row.addStretch()
        self._minimap_view = QGraphicsView()
        self._minimap_view.setInteractive(False)
        self._minimap_view.setFixedSize(220, 120)
        self._minimap_view.setStyleSheet(
            f"background: {Colors.BACKGROUND}; border: 1px solid {Colors.BORDER}; border-radius: 6px;"
        )
        graph_bottom_row.addWidget(self._minimap_view)
        graph_layout.addLayout(graph_bottom_row)
        self._view_tabs.addTab(graph_tab, "Graph")
        
        # Tree view tab
        self._tree_widget = QTreeWidget()
        self._tree_widget.setHeaderLabels([
            "Session ID", "Wait Type", "Wait Time", "Depth", "Database", "Login", "Host"
        ])
        self._tree_widget.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
            }}
            QTreeWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
            QTreeWidget::item:hover {{
                background-color: {Colors.PRIMARY_LIGHT};
            }}
            QTreeWidget::item:selected {{
                background-color: {Colors.SECONDARY_LIGHT};
                color: {Colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BACKGROUND};
                color: {Colors.TEXT_PRIMARY};
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                font-weight: 700;
                font-size: 11px;
            }}
        """)
        self._tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._tree_widget.itemClicked.connect(self._on_tree_item_clicked)
        self._tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree_widget.customContextMenuRequested.connect(self._show_context_menu)
        self._view_tabs.addTab(self._tree_widget, "Tree")

        timeline_tab = QWidget()
        timeline_tab.setStyleSheet(f"background-color: {Colors.SURFACE};")
        timeline_layout = QVBoxLayout(timeline_tab)
        timeline_layout.setContentsMargins(12, 12, 12, 12)
        timeline_layout.setSpacing(8)
        self._timeline_summary_label = QLabel("Timeline: awaiting snapshots")
        self._timeline_summary_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        timeline_layout.addWidget(self._timeline_summary_label)
        self._timeline_tree = QTreeWidget()
        self._timeline_tree.setHeaderLabels(["Captured At", "Chains", "Depth", "Total Wait (ms)", "Kill Marker"])
        self._timeline_tree.setAlternatingRowColors(True)
        self._timeline_tree.setRootIsDecorated(False)
        self._timeline_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
            }}
            QTreeWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
            QTreeWidget::item:hover {{
                background-color: {Colors.PRIMARY_LIGHT};
            }}
            QTreeWidget::item:selected {{
                background-color: {Colors.SECONDARY_LIGHT};
                color: {Colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BACKGROUND};
                color: {Colors.TEXT_PRIMARY};
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                font-weight: 700;
                font-size: 11px;
            }}
        """)
        self._timeline_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        timeline_layout.addWidget(self._timeline_tree, 1)
        self._view_tabs.addTab(timeline_tab, "Timeline")

        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_layout.setContentsMargins(8, 8, 8, 8)
        details_layout.setSpacing(8)
        self._head_blockers_tree = QTreeWidget()
        self._head_blockers_tree.setHeaderLabels([
            "Session", "Login", "Host", "Program", "Blocked Count", "CPU (s)"
        ])
        self._head_blockers_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
            }}
            QTreeWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
            QTreeWidget::item:hover {{
                background-color: {Colors.PRIMARY_LIGHT};
            }}
            QTreeWidget::item:selected {{
                background-color: {Colors.SECONDARY_LIGHT};
                color: {Colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BACKGROUND};
                color: {Colors.TEXT_PRIMARY};
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                font-weight: 700;
                font-size: 11px;
            }}
        """)
        self._head_blockers_tree.setMaximumHeight(150)
        self._head_blockers_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._head_blockers_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._head_blockers_tree.customContextMenuRequested.connect(self._show_head_blocker_menu)
        details_layout.addWidget(self._head_blockers_tree, 0, Qt.AlignmentFlag.AlignTop)
        details_layout.addStretch(1)
        self._view_tabs.addTab(details_tab, "Details")

        left_layout.addWidget(self._view_tabs)
        
        splitter.addWidget(left_widget)
        
        # Right panel: Session inspector drawer
        right_widget = QFrame()
        right_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        # Session Inspector: +7% wider for readability
        right_widget.setMinimumWidth(428)
        right_widget.setMaximumWidth(556)
        self._inspector_panel = right_widget
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(16, 16, 16, 16)
        
        # Inspector header
        details_header = QLabel("Session Inspector")
        details_header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: bold; font-size: 14px;")
        right_layout.addWidget(details_header)

        self._inspector_meta_label = QLabel("Select a session to inspect.")
        self._inspector_meta_label.setWordWrap(True)
        self._inspector_meta_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        right_layout.addWidget(self._inspector_meta_label)

        self._inspector_tabs = QTabWidget()
        self._inspector_tabs.setUsesScrollButtons(True)
        self._inspector_tabs.setStyleSheet(ThemeStyles.tab_widget_style())
        inspector_tab_bar = self._inspector_tabs.tabBar()
        inspector_tab_bar.setUsesScrollButtons(True)
        inspector_tab_bar.setElideMode(Qt.TextElideMode.ElideRight)

        sql_tab = QWidget()
        sql_layout = QVBoxLayout(sql_tab)
        self._details_label = QLabel("No session selected.")
        self._details_label.setWordWrap(True)
        self._details_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        sql_layout.addWidget(self._details_label)
        self._query_text = QTextEdit()
        self._query_text.setReadOnly(True)
        self._query_text.setPlaceholderText("No query selected")
        self._query_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.BACKGROUND};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px;
                color: {Colors.TEXT_PRIMARY};
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
            }}
        """)
        sql_layout.addWidget(self._query_text, 1)
        self._inspector_tabs.addTab(sql_tab, "SQL Statement")

        locks_tab = QWidget()
        locks_layout = QVBoxLayout(locks_tab)
        locks_layout.setContentsMargins(0, 0, 0, 0)
        locks_layout.setSpacing(4)
        locks_layout.addWidget(self._create_lock_details_panel())
        self._inspector_tabs.addTab(locks_tab, "Locks")

        plan_tab = QWidget()
        plan_layout = QVBoxLayout(plan_tab)
        self._plan_text = QTextEdit()
        self._plan_text.setReadOnly(True)
        self._plan_text.setPlaceholderText("Execution plan view is not available for this session in current build.")
        self._plan_text.setStyleSheet(
            f"background: {Colors.BACKGROUND}; border: 1px solid {Colors.BORDER}; border-radius: 8px;"
        )
        plan_layout.addWidget(self._plan_text, 1)
        self._inspector_tabs.addTab(plan_tab, "Execution Plan")

        impact_tab = QWidget()
        impact_layout = QVBoxLayout(impact_tab)
        self._impact_label = QLabel("Impact analysis will appear after session selection.")
        self._impact_label.setWordWrap(True)
        self._impact_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        impact_layout.addWidget(self._impact_label)
        self._inspector_tabs.addTab(impact_tab, "Impact Analysis")

        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        self._inspector_history_tree = QTreeWidget()
        self._inspector_history_tree.setHeaderLabels(["First Seen", "Last Seen", "Occurrences", "Peak Wait (ms)"])
        self._inspector_history_tree.setAlternatingRowColors(True)
        self._inspector_history_tree.setRootIsDecorated(False)
        self._inspector_history_tree.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                background: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
            }}
            QTreeWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
            QTreeWidget::item:hover {{
                background-color: {Colors.PRIMARY_LIGHT};
            }}
            QTreeWidget::item:selected {{
                background-color: {Colors.SECONDARY_LIGHT};
                color: {Colors.TEXT_PRIMARY};
            }}
            QHeaderView::section {{
                background-color: {Colors.BACKGROUND};
                color: {Colors.TEXT_PRIMARY};
                padding: 8px 10px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                font-weight: 700;
                font-size: 11px;
            }}
        """)
        self._inspector_history_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        history_layout.addWidget(self._inspector_history_tree, 1)
        self._inspector_tabs.addTab(history_tab, "History")

        right_layout.addWidget(self._inspector_tabs, 1)

        insights_group = QGroupBox("DBA Productivity Insights")
        insights_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                color: {Colors.TEXT_PRIMARY};
                font-weight: 600;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }}
        """)
        insights_layout = QVBoxLayout(insights_group)
        insights_layout.setContentsMargins(10, 10, 10, 10)
        insights_layout.setSpacing(6)

        self._alerts_label = QLabel("Alerts: none")
        self._alerts_label.setWordWrap(True)
        self._alerts_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        insights_layout.addWidget(self._alerts_label)

        self._ai_label = QLabel("AI: waiting for first snapshot")
        self._ai_label.setWordWrap(True)
        self._ai_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        insights_layout.addWidget(self._ai_label)
        right_layout.addWidget(insights_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self._kill_btn = QPushButton("Kill Session")
        self._kill_btn.setEnabled(False)
        self._kill_btn.clicked.connect(self._kill_selected_session)
        self._kill_btn.setStyleSheet(danger_btn_style)
        action_layout.addWidget(self._kill_btn)
        
        action_layout.addStretch()
        right_layout.addLayout(action_layout)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([690, 410])
        
        self._main_layout.addWidget(splitter, 1)
        
        # Footer: Status bar (left) + summary cards (bottom-right)
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(12)
        footer_layout.addWidget(self._status_label, 1)

        summary_container = QWidget()
        summary_layout = QHBoxLayout(summary_container)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(12)
        summary_layout.addWidget(self._total_blocking_card)
        summary_layout.addWidget(self._head_blocker_card)
        summary_layout.addWidget(self._max_wait_card)
        summary_layout.addWidget(self._affected_card)

        footer_layout.addWidget(
            summary_container,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )

        self._main_layout.addLayout(footer_layout)
        self._load_saved_filters()
        ThemeStyles.style_comboboxes_in_widget(self)

        # Scrollbar styling: match Object Explorer "Objects" list scrollbar across Blocking Analysis subcomponents.
        scrollbar_style = f"""
            QAbstractScrollArea::corner {{
                background: transparent;
            }}

            QScrollBar:vertical {{
                border: none;
                background-color: {Colors.BORDER_LIGHT};
                width: 8px;
                border-radius: 4px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BORDER_DARK};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {Colors.TEXT_MUTED};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
                height: 0px;
            }}

            QScrollBar:horizontal {{
                border: none;
                background-color: {Colors.BORDER_LIGHT};
                height: 8px;
                border-radius: 4px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {Colors.BORDER_DARK};
                border-radius: 4px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {Colors.TEXT_MUTED};
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: transparent;
                width: 0px;
            }}
        """
        self.setStyleSheet((self.styleSheet() or "") + scrollbar_style)

    def _create_lock_details_panel(self) -> QWidget:
        """Create lock details panel for the selected session."""
        panel = QFrame()
        panel.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QLabel("Lock Details")
        header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 700; font-size: 13px;")
        layout.addWidget(header)

        self._lock_table = QTableWidget()
        self._lock_table.setColumnCount(5)
        self._lock_table.setHorizontalHeaderLabels([
            "Resource Type",
            "Lock Mode",
            "Status",
            "Resource",
            "Count",
        ])
        self._lock_table.setAlternatingRowColors(True)
        self._lock_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._lock_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._lock_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._lock_table.cellClicked.connect(self._on_lock_row_clicked)
        self._lock_table.setMinimumHeight(170)
        self._lock_table.setMaximumHeight(240)
        self._lock_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                color: {Colors.TEXT_PRIMARY};
                gridline-color: {Colors.BORDER};
                font-size: 11px;
            }}
            QHeaderView::section {{
                background-color: {Colors.BACKGROUND};
                color: {Colors.TEXT_PRIMARY};
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                padding: 8px 10px;
            }}
            QTableWidget::item {{
                padding: 6px 8px;
                border-bottom: 1px solid {Colors.BORDER_LIGHT};
            }}
            QTableWidget::item:hover {{
                background-color: {Colors.PRIMARY_LIGHT};
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.SECONDARY_LIGHT};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        header_obj = self._lock_table.horizontalHeader()
        header_obj.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_obj.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_obj.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_obj.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header_obj.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._lock_table)

        self._populate_lock_details_table(None)
        return panel

    @staticmethod
    def _saved_filters_path():
        path = get_settings().data_dir / "blocking_saved_filters.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _load_saved_filters(self) -> None:
        path = self._saved_filters_path()
        self._saved_filters = {}
        if path.exists():
            try:
                import json

                with open(path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if isinstance(payload, dict):
                    self._saved_filters = {
                        str(k): dict(v)
                        for k, v in payload.items()
                        if isinstance(v, dict)
                    }
            except Exception as ex:
                logger.debug(f"Failed to load saved blocking filters: {ex}")
        self._saved_filter_combo.clear()
        self._saved_filter_combo.addItem("-- Saved Filters --")
        for name in sorted(self._saved_filters.keys()):
            self._saved_filter_combo.addItem(name)

    def _persist_saved_filters(self) -> None:
        try:
            import json

            with open(self._saved_filters_path(), "w", encoding="utf-8") as handle:
                json.dump(self._saved_filters, handle, indent=2, ensure_ascii=False)
        except Exception as ex:
            logger.debug(f"Failed to save blocking filters: {ex}")

    def _current_filter_payload(self) -> Dict[str, object]:
        return {
            "critical_only": bool(self._critical_only_btn.isChecked()),
            "production_only": bool(self._production_only_btn.isChecked()),
            "head_only": bool(self._head_only_btn.isChecked()),
            "database": str(self._filter_db_combo.currentText() or "All"),
            "user": str(self._filter_user_combo.currentText() or "All"),
            "application": str(self._filter_app_combo.currentText() or "All"),
            "severity": str(self._filter_severity_combo.currentText() or "All"),
            "min_wait_ms": int(self._filter_min_wait_spin.value()),
            "max_wait_ms": int(self._filter_max_wait_spin.value()),
        }

    def _apply_filter_payload(self, payload: Dict[str, object]) -> None:
        self._critical_only_btn.setChecked(bool(payload.get("critical_only", False)))
        self._production_only_btn.setChecked(bool(payload.get("production_only", False)))
        self._head_only_btn.setChecked(bool(payload.get("head_only", False)))
        self._set_combo_value(self._filter_db_combo, str(payload.get("database", "All")))
        self._set_combo_value(self._filter_user_combo, str(payload.get("user", "All")))
        self._set_combo_value(self._filter_app_combo, str(payload.get("application", "All")))
        self._set_combo_value(self._filter_severity_combo, str(payload.get("severity", "All")))
        self._filter_min_wait_spin.setValue(max(0, int(payload.get("min_wait_ms", 0) or 0)))
        self._filter_max_wait_spin.setValue(max(0, int(payload.get("max_wait_ms", 0) or 0)))

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: str) -> None:
        index = combo.findText(str(value))
        if index >= 0:
            combo.setCurrentIndex(index)

    def _save_current_filter(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "Save Filter", "Filter name:")
        clean = str(name or "").strip()
        if not ok or not clean:
            return
        self._saved_filters[clean] = self._current_filter_payload()
        self._persist_saved_filters()
        self._load_saved_filters()
        self._set_status(f"Saved filter '{clean}'", Colors.SUCCESS)

    def _apply_saved_filter(self) -> None:
        name = str(self._saved_filter_combo.currentText() or "").strip()
        if not name or name.startswith("--"):
            return
        payload = self._saved_filters.get(name)
        if not payload:
            return
        self._apply_filter_payload(payload)
        self._on_filter_changed()
        self._set_status(f"Applied filter '{name}'", Colors.SUCCESS)

    def _delete_saved_filter(self) -> None:
        name = str(self._saved_filter_combo.currentText() or "").strip()
        if not name or name.startswith("--"):
            return
        if name not in self._saved_filters:
            return
        del self._saved_filters[name]
        self._persist_saved_filters()
        self._load_saved_filters()
        self._set_status(f"Deleted filter '{name}'", Colors.WARNING)

    @staticmethod
    def _is_production_database(name: str) -> bool:
        value = str(name or "").lower()
        return any(token in value for token in ("prod", "prd", "live"))

    def _filter_sessions(self, sessions: List[BlockingSession]) -> List[BlockingSession]:
        source = list(sessions or [])
        if not source:
            return []
        db_name = str(self._filter_db_combo.currentText() or "All")
        user_name = str(self._filter_user_combo.currentText() or "All")
        app_name = str(self._filter_app_combo.currentText() or "All")
        severity = str(self._filter_severity_combo.currentText() or "All").lower()
        min_wait_ms = int(self._filter_min_wait_spin.value() or 0)
        max_wait_ms = int(self._filter_max_wait_spin.value() or 0)
        critical_only = bool(self._critical_only_btn.isChecked())
        production_only = bool(self._production_only_btn.isChecked())
        head_only = bool(self._head_only_btn.isChecked())

        blocker_ids = {int(item.blocking_session_id or 0) for item in source if int(item.blocking_session_id or 0) > 0}
        blocked_ids = {int(item.session_id or 0) for item in source if int(item.session_id or 0) > 0}
        head_ids = blocker_ids - blocked_ids

        filtered: List[BlockingSession] = []
        for item in source:
            wait_ms = int(round(float(item.wait_seconds or 0.0) * 1000.0))
            if min_wait_ms and wait_ms < min_wait_ms:
                continue
            if max_wait_ms and wait_ms > max_wait_ms:
                continue
            if db_name not in {"", "All"} and str(item.database_name or "") != db_name:
                continue
            if user_name not in {"", "All"} and str(item.login_name or "") != user_name:
                continue
            if app_name not in {"", "All"} and str(item.program_name or "") != app_name:
                continue
            if severity not in {"", "all"} and str(item.severity.value).lower() != severity:
                continue
            if critical_only and str(item.severity.value).lower() != "critical":
                continue
            if production_only and not self._is_production_database(str(item.database_name or "")):
                continue
            if head_only and int(item.blocking_session_id or 0) not in head_ids:
                continue
            filtered.append(item)
        return filtered

    def _refresh_filter_options(self, sessions: List[BlockingSession]) -> None:
        def _rebuild_combo(combo: QComboBox, values: List[str]) -> None:
            current = str(combo.currentText() or "All")
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("All")
            for value in values:
                if value:
                    combo.addItem(value)
            idx = combo.findText(current)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

        db_values = sorted({str(item.database_name or "") for item in sessions if str(item.database_name or "")})
        user_values = sorted({str(item.login_name or "") for item in sessions if str(item.login_name or "")})
        app_values = sorted({str(item.program_name or "") for item in sessions if str(item.program_name or "")})
        _rebuild_combo(self._filter_db_combo, db_values)
        _rebuild_combo(self._filter_user_combo, user_values)
        _rebuild_combo(self._filter_app_combo, app_values)

    def _on_filter_changed(self, *_args) -> None:
        self._filtered_sessions = self._filter_sessions(self._blocking_sessions)
        self._render_visuals()
        self._update_quick_action()

    def _on_notification_config_changed(self, value: int) -> None:
        self._notification_cooldown_seconds = max(10, int(value or 10))

    def _save_notification_rules(self) -> None:
        self._notification_rules.min_severity = str(self._alert_min_severity_combo.currentText() or "critical").lower()
        self._notification_rules.min_chain_count = max(1, int(self._alert_min_chain_spin.value() or 1))
        self._notification_rules.database_contains = str(self._alert_db_contains_input.text() or "").strip()
        if self._blocking_service.save_notification_rules(self._notification_rules):
            self._set_status("Notification rules saved.", Colors.SUCCESS)
            return
        self._set_status("Failed to save notification rules.", Colors.ERROR)

    def _save_webhook_settings(self) -> None:
        self._webhook_settings.enabled = bool(self._webhook_enabled_btn.isChecked())
        self._webhook_settings.url = str(self._webhook_url_input.text() or "").strip()
        self._webhook_settings.channel = str(self._webhook_channel_input.text() or "").strip()
        if self._blocking_service.save_webhook_settings(self._webhook_settings):
            self._set_status("Webhook settings saved.", Colors.SUCCESS)
            return
        self._set_status("Failed to save webhook settings.", Colors.ERROR)

    def _test_webhook_alert(self) -> None:
        self._save_webhook_settings()
        if not self._webhook_settings.enabled:
            self._set_status("Webhook disabled; enable it before test.", Colors.WARNING)
            return
        analysis = self._build_current_analysis()
        alerts = list(self._latest_alerts or self._blocking_service.evaluate_alerts(analysis))
        if not alerts:
            from app.services.blocking_service import BlockingAlert

            alerts = [
                BlockingAlert(
                    alert_id="test_alert",
                    severity="info",
                    title="Blocking webhook test",
                    message="Test message from Blocking Analysis view.",
                    metric_value=0.0,
                    threshold_value=0.0,
                )
            ]
        ok = self._blocking_service.send_alert_webhook(
            alerts=alerts,
            analysis=analysis,
            settings=self._webhook_settings,
        )
        if ok:
            self._set_status("Webhook test sent.", Colors.SUCCESS)
            return
        self._set_status("Webhook test failed.", Colors.ERROR)

    def _render_visuals(self) -> None:
        sessions = list(self._filtered_sessions or self._blocking_sessions or [])
        self._graph_widget.build_graph(sessions, self._head_blockers)
        self._update_tree()
        self._update_head_blockers()
        if hasattr(self, "_minimap_view"):
            try:
                self._minimap_view.setScene(self._graph_widget.scene_ref)
                self._minimap_view.fitInView(
                    self._graph_widget.scene_ref.sceneRect(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                )
            except Exception:
                pass

    def _set_status(self, text: str, color: str = Colors.TEXT_SECONDARY) -> None:
        self._status_label.setText(str(text))
        self._status_label.setStyleSheet(f"color: {color}; font-size: 11px;")
    
    def _toggle_auto_refresh(self):
        """Toggle auto-refresh"""
        if self._auto_refresh_btn.isChecked():
            if not self._blocking_service.is_connected:
                self._auto_refresh_btn.setChecked(False)
                self._auto_refresh_btn.setText("Auto-Refresh: OFF")
                self._refresh_timer.stop()
                self._set_disconnected_state()
                return
            self._auto_refresh_btn.setText("Auto-Refresh: ON")
            self._refresh_timer.start(5000)  # 5 seconds
        else:
            self._auto_refresh_btn.setText("Auto-Refresh: OFF")
            self._refresh_timer.stop()

    def _set_disconnected_state(self) -> None:
        """Show a friendly hint when no active DB connection exists."""
        self._status_label.setText("No active database connection. Connect in Settings to use Blocking Analysis.")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        try:
            self._severity_banner.setText("Connect to a database to start blocking analysis.")
            self._severity_banner.setStyleSheet(
                f"background: {Colors.INFO_LIGHT}; color: {Colors.INFO}; border: 1px solid {Colors.BORDER}; "
                "border-radius: 8px; padding: 8px 12px; font-weight: 600;"
            )
        except Exception:
            pass
        try:
            self._quick_action_label.setText("No connection: quick actions disabled.")
            self._investigate_top_btn.setEnabled(False)
            self._kill_top_btn.setEnabled(False)
        except Exception:
            pass
    
    def refresh(self) -> None:
        """Refresh blocking data"""
        if not self._is_initialized:
            return
            
        if self._worker and self._worker.isRunning():
            return

        if not self._blocking_service.is_connected:
            self._refresh_timer.stop()
            self._set_disconnected_state()
            return
        
        self._status_label.setText("Refreshing...")
        
        self._worker = BlockingWorker(service=self._blocking_service)
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()
    
    def _on_data_ready(self, blocking_sessions: List[BlockingSession], 
                       head_blockers: List[Dict], lock_details: Dict):
        """Handle data received"""
        self._blocking_sessions = list(blocking_sessions or [])
        self._head_blockers = list(head_blockers or [])
        self._lock_details = dict(lock_details or {})
        self._refresh_filter_options(self._blocking_sessions)
        self._filtered_sessions = self._filter_sessions(self._blocking_sessions)
        sessions_for_metrics = list(self._filtered_sessions or self._blocking_sessions)
        
        # Update summary cards
        total = len(sessions_for_metrics)
        heads = len(
            {
                int(item.blocking_session_id or 0)
                for item in sessions_for_metrics
                if int(item.blocking_session_id or 0) > 0
            }
        )
        max_wait = max((s.wait_seconds for s in sessions_for_metrics), default=0)
        affected = len(set(s.session_id for s in sessions_for_metrics))
        
        self._total_blocking_card.update_value(
            str(total), 
            "success" if total == 0 else ("warning" if total < 5 else "error")
        )
        self._head_blocker_card.update_value(
            str(heads),
            "success" if heads == 0 else ("warning" if heads < 3 else "error")
        )
        self._max_wait_card.update_value(
            f"{max_wait:.0f}s",
            "success" if max_wait < 5 else ("warning" if max_wait < 30 else "error")
        )
        self._affected_card.update_value(
            str(affected),
            "success" if affected == 0 else ("warning" if affected < 5 else "error")
        )

        self._render_visuals()

        # Keep lock table in sync after refresh
        if self._selected_session:
            self._update_session_details(int(self._selected_session))
        else:
            self._populate_lock_details_table(None)

        self._update_severity_banner(sessions_for_metrics)
        self._update_timeline_tab()
        self._update_productivity_insights()
        self._update_quick_action()
        self._notify_alerts_if_needed()
        
        # Update status
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._status_label.setText(f"Last updated: {timestamp}")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
    
    def _on_error(self, error: str):
        """Handle error"""
        self._status_label.setText(f"Error: {error}")
        self._status_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 11px;")
        now = datetime.now()
        should_show_dialog = True
        if self._last_error_popup_message == str(error or "") and self._last_error_popup_at:
            should_show_dialog = (now - self._last_error_popup_at) > timedelta(seconds=30)
        if should_show_dialog:
            QMessageBox.critical(
                self,
                "Blocking Analysis Error",
                f"Failed to refresh blocking data:\n\n{error}",
                QMessageBox.StandardButton.Ok,
            )
            self._last_error_popup_message = str(error or "")
            self._last_error_popup_at = now
        logger.error(f"Blocking view error: {error}")

    def _update_severity_banner(self, sessions: List[BlockingSession]) -> None:
        critical = sum(1 for item in sessions if str(item.severity.value).lower() == "critical")
        high = sum(1 for item in sessions if str(item.severity.value).lower() == "high")
        medium = sum(1 for item in sessions if str(item.severity.value).lower() == "medium")
        low = sum(1 for item in sessions if str(item.severity.value).lower() == "low")

        self._quick_summary_label.setText(f"{critical} Critical | {high} High | {medium} Medium | {low} Low")

        if critical > 0:
            self._severity_banner.setText(f"CRITICAL blocking detected ({critical} critical session)")
            self._severity_banner.setStyleSheet(
                "background: #FDEAEA; color: #B71C1C; border: 1px solid #EF9A9A; "
                "border-radius: 8px; padding: 8px 12px; font-weight: 700;"
            )
        elif high > 0:
            self._severity_banner.setText(f"High blocking pressure ({high} high severity session)")
            self._severity_banner.setStyleSheet(
                "background: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2; "
                "border-radius: 8px; padding: 8px 12px; font-weight: 600;"
            )
        elif medium > 0:
            self._severity_banner.setText(f"Moderate blocking ({medium} medium severity session)")
            self._severity_banner.setStyleSheet(
                "background: #FFF3E0; color: #E65100; border: 1px solid #FFCC80; "
                "border-radius: 8px; padding: 8px 12px; font-weight: 600;"
            )
        else:
            self._severity_banner.setText("No active critical blocking")
            self._severity_banner.setStyleSheet(
                "background: #E8F5E9; color: #1B5E20; border: 1px solid #A5D6A7; "
                "border-radius: 8px; padding: 8px 12px; font-weight: 600;"
            )

    def _find_top_blocker_id(self) -> int:
        sessions = list(self._filtered_sessions or self._blocking_sessions or [])
        if not sessions:
            return 0
        impact: Dict[int, Dict[str, float]] = {}
        for item in sessions:
            blocker_id = int(item.blocking_session_id or 0)
            if blocker_id <= 0:
                continue
            bucket = impact.setdefault(blocker_id, {"blocked": 0.0, "wait_ms": 0.0})
            bucket["blocked"] += 1.0
            bucket["wait_ms"] += float(item.wait_seconds or 0.0) * 1000.0
        if not impact:
            return 0
        ranked = sorted(
            impact.items(),
            key=lambda kv: (kv[1]["blocked"] * 100000.0 + kv[1]["wait_ms"]),
            reverse=True,
        )
        return int(ranked[0][0] if ranked else 0)

    def _update_quick_action(self) -> None:
        top_id = self._find_top_blocker_id()
        if top_id <= 0:
            self._quick_action_label.setText("No blocker recommendation yet.")
            self._investigate_top_btn.setEnabled(False)
            self._kill_top_btn.setEnabled(False)
            return
        blocked_count = sum(
            1 for item in list(self._filtered_sessions or self._blocking_sessions) if int(item.blocking_session_id or 0) == top_id
        )
        total_wait = sum(
            int(round(float(item.wait_seconds or 0.0) * 1000.0))
            for item in list(self._filtered_sessions or self._blocking_sessions)
            if int(item.blocking_session_id or 0) == top_id
        )
        self._quick_action_label.setText(
            f"Session {top_id} blocks {blocked_count} session(s), total impacted wait {total_wait:,} ms."
        )
        self._investigate_top_btn.setEnabled(True)
        self._kill_top_btn.setEnabled(True)
        self._investigate_top_btn.setProperty("session_id", top_id)
        self._kill_top_btn.setProperty("session_id", top_id)

    def _investigate_top_blocker(self) -> None:
        session_id = int(self._investigate_top_btn.property("session_id") or 0)
        if session_id <= 0:
            return
        self._selected_session = session_id
        self._update_session_details(session_id)
        self._inspector_tabs.setCurrentIndex(3)

    def _kill_top_blocker(self) -> None:
        session_id = int(self._kill_top_btn.property("session_id") or 0)
        if session_id <= 0:
            return
        self._kill_session(session_id)

    def _update_timeline_tab(self) -> None:
        try:
            snapshots = self._blocking_service.get_history_snapshots(minutes=24 * 60)
            audit_rows = self._blocking_service.get_kill_audit_rows(limit=1000)
        except Exception as ex:
            logger.debug(f"Failed to load timeline data: {ex}")
            snapshots = []
            audit_rows = []

        if not snapshots:
            self._timeline_summary_label.setText("Timeline: no history in selected window.")
            self._timeline_tree.clear()
            return

        self._history_rows = list(snapshots)
        latest = snapshots[-1]
        day_count = len(snapshots)
        avg_wait = int(sum(int(row.get("total_wait_time", 0) or 0) for row in snapshots) / max(1, day_count))
        max_depth = max(int(row.get("max_chain_depth", 0) or 0) for row in snapshots)
        self._timeline_summary_label.setText(
            f"Last 24h snapshots={day_count} | avg_wait={avg_wait:,} ms | "
            f"peak_depth={max_depth} | latest_wait={int(latest.get('total_wait_time', 0) or 0):,} ms"
        )
        self._timeline_tree.clear()
        kill_markers = {str(row.get("timestamp", "") or "")[:16] for row in audit_rows if bool(row.get("success", False))}
        for row in snapshots[-180:]:
            captured_at = str(row.get("captured_at", "") or "")
            marker = "⛔" if captured_at[:16] in kill_markers else ""
            item = QTreeWidgetItem(
                [
                    captured_at.replace("T", " "),
                    str(int(row.get("chain_count", 0) or 0)),
                    str(int(row.get("max_chain_depth", 0) or 0)),
                    f"{int(row.get('total_wait_time', 0) or 0):,}",
                    marker,
                ]
            )
            if marker:
                item.setForeground(4, QColor("#C62828"))
            self._timeline_tree.addTopLevelItem(item)

    def _notify_alerts_if_needed(self) -> None:
        try:
            analysis = self._build_current_analysis()
            alerts = self._blocking_service.evaluate_alerts(analysis)
        except Exception as ex:
            logger.debug(f"Failed to evaluate blocking alerts for notification: {ex}")
            return
        self._latest_alerts = list(alerts or [])
        if not alerts:
            return
        severity_rank = {"critical": 3, "warning": 2, "info": 1}
        min_level = str(self._alert_min_severity_combo.currentText() or self._notification_rules.min_severity or "critical").lower()
        min_rank = severity_rank.get(min_level, 3)
        selected_alerts = [item for item in alerts if severity_rank.get(str(item.severity).lower(), 0) >= min_rank]
        if not selected_alerts:
            return
        min_chain = max(1, int(self._alert_min_chain_spin.value() or self._notification_rules.min_chain_count or 1))
        if int(analysis.chain_count or 0) < min_chain:
            return
        db_rule = str(self._alert_db_contains_input.text() or self._notification_rules.database_contains or "").strip().lower()
        if db_rule:
            db_values = {str(item.database_name or "").lower() for item in list(self._filtered_sessions or self._blocking_sessions)}
            if not any(db_rule in value for value in db_values):
                return
        key = ",".join(sorted(str(item.alert_id) for item in selected_alerts))
        now = datetime.now()
        if self._last_notification_key == key and self._last_notification_at:
            elapsed = (now - self._last_notification_at).total_seconds()
            if elapsed < float(self._notification_cooldown_seconds):
                return
        self._last_notification_key = key
        self._last_notification_at = now
        critical_count = sum(1 for item in selected_alerts if str(item.severity).lower() == "critical")
        message = (
            f"{len(selected_alerts)} blocking alert(s) active "
            f"(critical={critical_count}, chain_count={int(analysis.chain_count or 0)})."
        )
        self._set_status(f"{message}", Colors.ERROR)
        if self._sound_alert_btn.isChecked():
            QApplication.beep()
        self._show_desktop_notification("Blocking Alert", message)
        try:
            if bool(self._webhook_enabled_btn.isChecked()):
                self._webhook_settings.enabled = True
                self._webhook_settings.url = str(self._webhook_url_input.text() or "").strip()
                self._webhook_settings.channel = str(self._webhook_channel_input.text() or "").strip()
                self._blocking_service.send_alert_webhook(
                    alerts=selected_alerts,
                    analysis=analysis,
                    settings=self._webhook_settings,
                )
        except Exception as ex:
            logger.debug(f"Failed to send webhook notification: {ex}")

    def _show_desktop_notification(self, title: str, message: str) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = getattr(self, "_notification_tray", None)
        if tray is None:
            tray = QSystemTrayIcon(self.windowIcon(), self)
            tray.setVisible(True)
            self._notification_tray = tray
        tray.showMessage(str(title), str(message), QSystemTrayIcon.MessageIcon.Warning, 5000)

    def _export_graph_png(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Blocking Graph",
            f"blocking_graph_{timestamp}.png",
            "PNG Files (*.png);;All Files (*)",
        )
        if not target_path:
            return
        rect = self._graph_widget.scene_ref.itemsBoundingRect()
        if rect.isNull():
            QMessageBox.information(self, "Export Graph", "No graph data to export.")
            return
        image = QImage(int(rect.width() + 40), int(rect.height() + 40), QImage.Format.Format_ARGB32)
        image.fill(QColor(255, 255, 255, 0))
        painter = QPainter(image)
        self._graph_widget.scene_ref.render(
            painter,
            target=QRectF(20, 20, rect.width(), rect.height()),
            source=rect,
        )
        painter.end()
        if image.save(target_path):
            self._set_status(f"Graph exported: {target_path}", Colors.SUCCESS)
        else:
            self._set_status("Failed to export graph image.", Colors.ERROR)
    
    def _update_tree(self):
        """Update blocking tree"""
        self._tree_widget.clear()
        sessions = list(self._filtered_sessions or self._blocking_sessions or [])
        if not sessions:
            self._tree_widget.addTopLevelItem(
                QTreeWidgetItem(["No active blocking chains", "", "", "", "", "", ""])
            )
            return

        by_blocker: Dict[int, List[BlockingSession]] = {}
        session_by_id: Dict[int, BlockingSession] = {}
        blocked_ids: set[int] = set()
        for session in sessions:
            blocker_id = int(session.blocking_session_id or 0)
            blocked_id = int(session.session_id or 0)
            if blocker_id <= 0 or blocked_id <= 0:
                continue
            by_blocker.setdefault(blocker_id, []).append(session)
            blocked_ids.add(blocked_id)
            session_by_id[blocked_id] = session
        for blocker_id in list(by_blocker.keys()):
            by_blocker[blocker_id] = sorted(
                list(by_blocker.get(blocker_id, [])),
                key=lambda x: float(x.wait_seconds or 0.0),
                reverse=True,
            )

        blocker_ids = set(by_blocker.keys())
        root_ids = sorted(blocker_ids - blocked_ids) or sorted(blocker_ids)
        max_wait_seconds = max((float(item.wait_seconds or 0.0) for item in sessions), default=1.0)

        def _make_root_item(root_id: int) -> QTreeWidgetItem:
            root_session = session_by_id.get(root_id)
            item = QTreeWidgetItem(
                [
                    f"{root_id} (Blocker)",
                    "",
                    "",
                    "D0",
                    str(getattr(root_session, "database_name", "") or ""),
                    str(getattr(root_session, "login_name", "") or ""),
                    str(getattr(root_session, "host_name", "") or ""),
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, root_id)
            item.setForeground(0, QColor(Colors.ERROR))
            return item

        def _attach_children(parent_item: QTreeWidgetItem, blocker_id: int, level: int, visited: set[int]) -> None:
            for child in by_blocker.get(blocker_id, []):
                child_id = int(child.session_id or 0)
                child_item = QTreeWidgetItem(
                    [
                        f"{child_id}",
                        str(child.wait_type or ""),
                        child.format_wait_time(),
                        f"D{max(1, int(level))}",
                        str(child.database_name or ""),
                        str(child.login_name or ""),
                        str(child.host_name or ""),
                    ]
                )
                child_item.setData(0, Qt.ItemDataRole.UserRole, child_id)
                child_item.setForeground(2, QColor(child.severity_color))
                child_item.setBackground(2, self._wait_heatmap_color(child.wait_seconds, max_wait_seconds))
                parent_item.addChild(child_item)
                if child_id in visited:
                    child_item.addChild(QTreeWidgetItem(["Cycle detected", "", "", "", "", "", ""]))
                    continue
                _attach_children(child_item, child_id, level + 1, visited | {child_id})

        for root_id in root_ids:
            root_item = _make_root_item(root_id)
            self._tree_widget.addTopLevelItem(root_item)
            _attach_children(root_item, root_id, 1, {root_id})
            root_item.setExpanded(True)
    
    def _update_head_blockers(self):
        """Update head blockers list"""
        self._head_blockers_tree.clear()
        visible_blockers = {
            int(item.blocking_session_id or 0)
            for item in list(self._filtered_sessions or self._blocking_sessions or [])
            if int(item.blocking_session_id or 0) > 0
        }
        for blocker in self._head_blockers:
            blocker_id = int(blocker.get("head_blocker_session", 0) or 0)
            if visible_blockers and blocker_id not in visible_blockers:
                continue
            item = QTreeWidgetItem([
                str(blocker_id),
                blocker.get('login_name', ''),
                blocker.get('host_name', ''),
                blocker.get('program_name', ''),
                str(blocker.get('blocked_count', 0)),
                f"{blocker.get('cpu_seconds', 0):.1f}"
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, blocker_id)
            item.setForeground(0, QColor(Colors.ERROR))
            self._head_blockers_tree.addTopLevelItem(item)
    
    def _on_session_selected(self, session_id: int):
        """Handle session selection from graph"""
        self._selected_session = session_id
        self._update_session_details(session_id)
    
    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click"""
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        if session_id:
            self._selected_session = session_id
            self._update_session_details(session_id)
    
    def _update_session_details(self, session_id: int):
        """Update session details panel"""
        self._populate_lock_details_table(session_id)
        self._slide_in_inspector()

        # Find session info
        session = None
        for s in self._blocking_sessions:
            if s.session_id == session_id:
                session = s
                break
            if s.blocking_session_id == session_id:
                # It's a blocker, show blocker info
                pass
        
        if session:
            blocked_sessions = session.get_blocked_sessions(self._blocking_sessions)
            chain_depth = session.calculate_chain_depth(self._blocking_sessions)
            details = f"""
<b>Session ID:</b> {session.session_id}<br>
<b>Blocked By:</b> {session.blocking_session_id}<br>
<b>Wait Type:</b> {session.wait_type}<br>
<b>Wait Time:</b> {session.format_wait_time()}<br>
<b>Database:</b> {session.database_name}<br>
<b>Login:</b> {session.login_name}<br>
<b>Host:</b> {session.host_name}<br>
<b>Program:</b> {session.program_name}<br>
<b>CPU Time:</b> {session.cpu_seconds:.1f} seconds<br>
<b>Severity:</b> <span style="color: {session.severity_color};">{session.severity.value.upper()}</span><br>
<b>Safe to Kill:</b> {'Yes' if session.is_safe_to_kill() else f'No ({session.kill_safety_reason()})'}<br>
<b>Directly Blocking:</b> {len(blocked_sessions)} session(s)<br>
<b>Chain Depth:</b> {chain_depth}<br>
{self._build_lock_details_html(session.session_id)}
"""
            self._details_label.setText(details)
            self._query_text.setPlainText(session.current_statement or "No query available")
            self._kill_btn.setEnabled(bool(session.is_safe_to_kill()))
            self._inspector_meta_label.setText(
                f"Session {session.session_id} | {session.login_name or 'unknown'}@{session.host_name or 'unknown'}"
            )
            self._impact_label.setText(self._build_impact_analysis_text(session_id))
            self._render_execution_plan(session_id)
            self._update_inspector_history(session_id)
        else:
            # Check in head blockers
            for blocker in self._head_blockers:
                if blocker.get('head_blocker_session') == session_id:
                    blocker_model = BlockingSession(
                        session_id=int(session_id or 0),
                        blocking_session_id=0,
                        wait_seconds=0.0,
                        status=str(blocker.get("status", "") or ""),
                        program_name=str(blocker.get("program_name", "") or ""),
                        is_user_process=True,
                    )
                    details = f"""
<b>Session ID:</b> {session_id} <span style="color: {Colors.ERROR};">(HEAD BLOCKER)</span><br>
<b>Login:</b> {blocker.get('login_name', '')}<br>
<b>Host:</b> {blocker.get('host_name', '')}<br>
<b>Program:</b> {blocker.get('program_name', '')}<br>
<b>Status:</b> {blocker.get('status', '')}<br>
<b>Safe to Kill:</b> {'Yes' if blocker_model.is_safe_to_kill() else f'No ({blocker_model.kill_safety_reason()})'}<br>
<b>Blocked Sessions:</b> {blocker.get('blocked_count', 0)}<br>
<b>CPU Time:</b> {blocker.get('cpu_seconds', 0):.1f} seconds<br>
<b>Memory:</b> {blocker.get('memory_kb', 0):,} KB<br>
{self._build_lock_details_html(session_id)}
"""
                    self._details_label.setText(details)
                    self._query_text.setPlainText(blocker.get('blocker_query', '') or "No query available")
                    self._kill_btn.setEnabled(bool(blocker_model.is_safe_to_kill()))
                    self._inspector_meta_label.setText(
                        f"Head blocker {session_id} | {blocker.get('login_name', '')}@{blocker.get('host_name', '')}"
                    )
                    self._impact_label.setText(self._build_impact_analysis_text(session_id))
                    self._render_execution_plan(session_id)
                    self._update_inspector_history(session_id)
                    return
            
            self._details_label.setText(f"Session {session_id} selected")
            self._query_text.clear()
            self._kill_btn.setEnabled(int(session_id or 0) > 0)
            self._inspector_meta_label.setText(f"Session {session_id}")
            self._impact_label.setText(self._build_impact_analysis_text(session_id))
            self._render_execution_plan(session_id)
            self._update_inspector_history(session_id)

    def _render_execution_plan(self, session_id: int) -> None:
        try:
            plan_payload = self._blocking_service.get_session_execution_plan(session_id)
        except Exception as ex:
            self._plan_text.setPlainText(f"Execution plan retrieval failed: {ex}")
            return
        if not bool(plan_payload.get("plan_available", False)):
            self._plan_text.setPlainText(str(plan_payload.get("summary", "No execution plan available.")))
            return
        summary = str(plan_payload.get("summary", "") or "")
        warnings = [str(item) for item in list(plan_payload.get("warnings", []) or []) if str(item).strip()]
        plan_xml = str(plan_payload.get("plan_xml", "") or "")
        xml_preview = plan_xml[:4000] + ("\n...\n[truncated]" if len(plan_xml) > 4000 else "")
        lines = [
            "Execution Plan Summary",
            "",
            summary or "No summary available.",
            "",
        ]
        if warnings:
            lines.append("Warnings:")
            lines.extend([f"- {item}" for item in warnings[:10]])
            lines.append("")
        lines.extend(["Plan XML Preview:", "", xml_preview or "(empty)"])
        self._plan_text.setPlainText("\n".join(lines))

    def _build_impact_analysis_text(self, session_id: int) -> str:
        sessions = list(self._blocking_sessions or [])
        if not sessions:
            return "No active chain information."
        children_by_blocker: Dict[int, List[int]] = {}
        wait_by_session: Dict[int, int] = {}
        safe_to_kill = True
        for item in sessions:
            blocker_id = int(item.blocking_session_id or 0)
            blocked_id = int(item.session_id or 0)
            if blocker_id > 0 and blocked_id > 0:
                children_by_blocker.setdefault(blocker_id, []).append(blocked_id)
            wait_by_session[blocked_id] = int(round(float(item.wait_seconds or 0.0) * 1000.0))
            if blocked_id == session_id:
                safe_to_kill = bool(item.is_safe_to_kill())

        def _walk(node: int, visited: set[int]) -> set[int]:
            if node in visited:
                return set()
            impacted: set[int] = set()
            for child in children_by_blocker.get(node, []):
                impacted.add(child)
                impacted |= _walk(child, visited | {node})
            return impacted

        impacted_sessions = sorted(_walk(int(session_id), set()))
        unblock_count = len(impacted_sessions)
        peak_impacted_wait = max((wait_by_session.get(item, 0) for item in impacted_sessions), default=0)
        total_impacted_wait = sum(wait_by_session.get(item, 0) for item in impacted_sessions)
        if not safe_to_kill:
            risk = "CRITICAL"
        elif unblock_count >= 8 or peak_impacted_wait >= 120_000:
            risk = "HIGH"
        elif unblock_count >= 4 or peak_impacted_wait >= 60_000:
            risk = "MEDIUM"
        else:
            risk = "LOW"
        recovery_seconds = max(5, int(round((total_impacted_wait / 1000.0) * 0.15)))
        lines = [
            f"Kill impact for session {session_id}",
            f"- Sessions that may unblock: {unblock_count}",
            f"- Peak impacted wait: {peak_impacted_wait:,} ms",
            f"- Aggregate impacted wait: {total_impacted_wait:,} ms",
            f"- Risk assessment: {risk}",
            f"- Estimated recovery time: {recovery_seconds}s",
        ]
        if not safe_to_kill:
            lines.append("- Warning: session safety checks flagged this session as unsafe.")
        return "\n".join(lines)

    def _update_inspector_history(self, session_id: int) -> None:
        self._inspector_history_tree.clear()
        try:
            recurring = self._blocking_service.get_recurring_blockers(days=7, min_occurrences=1)
        except Exception as ex:
            logger.debug(f"Failed to load recurring blocker history: {ex}")
            recurring = []
        matches = [item for item in recurring if int(item.session_id or 0) == int(session_id or 0)]
        if not matches:
            self._inspector_history_tree.addTopLevelItem(
                QTreeWidgetItem(["-", "-", "0", "0"])
            )
            return
        row = matches[0]
        self._inspector_history_tree.addTopLevelItem(
            QTreeWidgetItem(
                [
                    row.first_seen.isoformat(timespec="seconds") if row.first_seen else "-",
                    row.last_seen.isoformat(timespec="seconds") if row.last_seen else "-",
                    str(int(row.occurrences)),
                    f"{int(row.peak_wait_ms):,}",
                ]
            )
        )

    def _slide_in_inspector(self) -> None:
        if not hasattr(self, "_inspector_panel"):
            return
        current_width = int(self._inspector_panel.maximumWidth() or 400)
        if current_width >= 400:
            return
        self._inspector_animation = QPropertyAnimation(self._inspector_panel, b"maximumWidth", self)
        self._inspector_animation.setDuration(180)
        self._inspector_animation.setStartValue(current_width)
        self._inspector_animation.setEndValue(420)
        self._inspector_animation.start()

    def _build_lock_details_html(self, session_id: int) -> str:
        locks = list(self._lock_details.get(int(session_id or 0), []) or [])
        if not locks:
            return "<b>Locks:</b> No lock details available"

        def _lock_count(row: Dict) -> int:
            try:
                return int(float(row.get("lock_count", 0) or 0))
            except (TypeError, ValueError):
                return 0

        rendered = []
        for lock_row in sorted(locks, key=_lock_count, reverse=True)[:8]:
            resource_type = str(lock_row.get("resource_type", "") or "")
            request_mode = str(lock_row.get("request_mode", "") or "")
            request_status = str(lock_row.get("request_status", "") or "")
            resource_text = self._format_lock_resource(lock_row)
            lock_count = _lock_count(lock_row)
            rendered.append(
                f"{resource_type}/{self._lock_mode_badge(request_mode)}/{request_status} "
                f"{resource_text} ({lock_count})"
            )
        joined = ", ".join(rendered)
        return f"<b>Locks:</b> {joined}"

    @staticmethod
    def _format_lock_resource(lock_row: Dict) -> str:
        direct_resource = str(lock_row.get("resource", "") or "").strip()
        if direct_resource:
            return direct_resource
        database_name = str(lock_row.get("database_name", "") or "").strip()
        resource_description = str(lock_row.get("resource_description", "") or "").strip()
        if database_name and resource_description:
            return f"[{database_name}] {resource_description}"
        if database_name:
            return f"[{database_name}]"
        if resource_description:
            return resource_description
        return str(lock_row.get("resource_type", "") or "")

    @staticmethod
    def _mode_background_color(mode: str) -> QColor:
        clean_mode = str(mode or "").upper()
        if clean_mode in {"X", "IX", "SIX", "UIX"}:
            return QColor("#FEE2E2")
        if clean_mode in {"S", "IS"}:
            return QColor("#DCFCE7")
        if clean_mode in {"U", "IU"}:
            return QColor("#FEF3C7")
        return QColor("transparent")

    @staticmethod
    def _status_foreground_color(status: str) -> QColor:
        clean_status = str(status or "").upper()
        if clean_status == "WAIT":
            return QColor(Colors.ERROR)
        if clean_status == "CONVERT":
            return QColor("#B45309")
        return QColor(Colors.TEXT_PRIMARY)

    @staticmethod
    def _lock_mode_badge(mode: str) -> str:
        clean_mode = str(mode or "").upper()
        return clean_mode

    @staticmethod
    def _wait_heatmap_color(wait_seconds: float, max_wait_seconds: float) -> QColor:
        safe_max = max(1.0, float(max_wait_seconds or 1.0))
        ratio = max(0.0, min(1.0, float(wait_seconds or 0.0) / safe_max))
        # From soft yellow to soft red.
        red = 255
        green = int(248 - (ratio * 120))
        blue = int(220 - (ratio * 150))
        return QColor(red, max(80, green), max(60, blue), 170)

    def _on_lock_row_clicked(self, row: int, _column: int) -> None:
        if row < 0 or row >= len(self._visible_lock_rows):
            return
        lock_row = self._visible_lock_rows[row]
        mode = str(lock_row.get("request_mode", "") or "")
        status = str(lock_row.get("request_status", "") or "")
        resource = self._format_lock_resource(lock_row)
        session_id = int(lock_row.get("session_id", 0) or 0)
        self._status_label.setText(
            f"Lock selected | SPID {session_id} | {self._lock_mode_badge(mode)} | {status} | {resource}"
        )
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")

    def _populate_lock_details_table(self, session_id: Optional[int]) -> None:
        if not hasattr(self, "_lock_table"):
            return

        self._visible_lock_rows = []
        if not session_id:
            self._lock_table.setRowCount(1)
            placeholder = QTableWidgetItem("Select a session to view lock details")
            placeholder.setForeground(QColor(Colors.TEXT_SECONDARY))
            self._lock_table.setItem(0, 0, placeholder)
            for column in range(1, 5):
                self._lock_table.setItem(0, column, QTableWidgetItem(""))
            return

        locks = list(self._lock_details.get(int(session_id), []) or [])
        if not locks:
            self._lock_table.setRowCount(1)
            empty = QTableWidgetItem("No lock details")
            empty.setForeground(QColor(Colors.TEXT_SECONDARY))
            self._lock_table.setItem(0, 0, empty)
            for column in range(1, 5):
                self._lock_table.setItem(0, column, QTableWidgetItem(""))
            return

        def _lock_count(row: Dict) -> int:
            try:
                return int(float(row.get("lock_count", 0) or 0))
            except (TypeError, ValueError):
                return 0

        ordered = sorted(locks, key=_lock_count, reverse=True)
        self._visible_lock_rows = list(ordered)
        self._lock_table.setRowCount(len(ordered))
        for idx, lock_row in enumerate(ordered):
            resource_type = str(lock_row.get("resource_type", "") or "")
            request_mode = str(lock_row.get("request_mode", "") or "")
            request_status = str(lock_row.get("request_status", "") or "")
            resource_text = self._format_lock_resource(lock_row)
            lock_count = _lock_count(lock_row)

            resource_type_item = QTableWidgetItem(resource_type)
            mode_item = QTableWidgetItem(self._lock_mode_badge(request_mode))
            status_item = QTableWidgetItem(request_status)
            resource_item = QTableWidgetItem(resource_text)
            count_item = QTableWidgetItem(str(lock_count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            mode_item.setBackground(self._mode_background_color(request_mode))
            status_item.setForeground(self._status_foreground_color(request_status))

            self._lock_table.setItem(idx, 0, resource_type_item)
            self._lock_table.setItem(idx, 1, mode_item)
            self._lock_table.setItem(idx, 2, status_item)
            self._lock_table.setItem(idx, 3, resource_item)
            self._lock_table.setItem(idx, 4, count_item)

    def _build_current_analysis(self) -> BlockingChainAnalysis:
        head_sessions: List[BlockingSession] = []
        for row in list(self._head_blockers or []):
            head_id = int(row.get("head_blocker_session", 0) or 0)
            if head_id <= 0:
                continue
            head_wait = max(
                (
                    float(item.wait_seconds or 0.0)
                    for item in list(self._blocking_sessions or [])
                    if int(item.blocking_session_id or 0) == head_id
                ),
                default=0.0,
            )
            head_sessions.append(
                BlockingSession(
                    session_id=head_id,
                    blocking_session_id=0,
                    wait_seconds=head_wait,
                    database_name=str(row.get("database_name", "") or ""),
                    login_name=str(row.get("login_name", "") or ""),
                    host_name=str(row.get("host_name", "") or ""),
                    program_name=str(row.get("program_name", "") or ""),
                    current_statement=str(row.get("blocker_query", "") or ""),
                    blocker_query=str(row.get("blocker_query", "") or ""),
                )
            )
        lock_items: List[LockInfo] = []
        for session_id, rows in dict(self._lock_details or {}).items():
            sid = int(session_id or 0)
            for row in list(rows or []):
                try:
                    lock_count = int(float(row.get("lock_count", 0) or 0))
                except (TypeError, ValueError):
                    lock_count = 0
                lock_items.append(
                    LockInfo(
                        session_id=sid,
                        database_name=str(row.get("database_name", "") or ""),
                        resource_type=str(row.get("resource_type", "") or ""),
                        resource_description=str(row.get("resource_description", "") or ""),
                        resource=str(row.get("resource", "") or ""),
                        request_mode=str(row.get("request_mode", "") or ""),
                        request_status=str(row.get("request_status", "") or ""),
                        lock_count=lock_count,
                    )
                )
        total_wait_ms = sum(int(round(float(item.wait_seconds or 0.0) * 1000.0)) for item in list(self._blocking_sessions or []))
        return BlockingChainAnalysis(
            blocking_sessions=list(self._blocking_sessions or []),
            head_blockers=head_sessions,
            lock_details=lock_items,
            chain_count=len(head_sessions),
            max_chain_depth=max((item.calculate_chain_depth(self._blocking_sessions) for item in list(self._blocking_sessions or [])), default=0),
            total_wait_time=total_wait_ms,
            critical_blockers=[item for item in head_sessions if float(item.wait_seconds or 0.0) > 30.0],
            analysis_timestamp=datetime.now(),
            head_blocker_rows=list(self._head_blockers or []),
            lock_details_by_session=dict(self._lock_details or {}),
        )

    def _update_productivity_insights(self) -> None:
        if not hasattr(self, "_alerts_label") or not hasattr(self, "_ai_label"):
            return
        if not self._blocking_sessions:
            self._alerts_label.setText("Alerts: none")
            self._ai_label.setText("AI: no active blocking sessions")
            return
        analysis = self._build_current_analysis()
        alerts = self._blocking_service.evaluate_alerts(analysis)
        self._latest_alerts = list(alerts or [])
        recommendations = self._blocking_service.generate_ai_recommendations(analysis, top_n=2)
        cache_metrics = self._blocking_service.get_cache_metrics()
        recurring = self._blocking_service.get_recurring_blockers(days=7, min_occurrences=2)

        if not alerts:
            self._alerts_label.setText(
                "Alerts: no active threshold violations | "
                f"cache hit-rate={float(cache_metrics.get('hit_rate', 0.0)) * 100.0:.0f}%"
            )
            self._alerts_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
        else:
            critical_count = sum(1 for item in alerts if str(item.severity).lower() == "critical")
            first = alerts[0]
            self._alerts_label.setText(
                f"Alerts: {len(alerts)} active (critical={critical_count}) | {first.title} | "
                f"cache={float(cache_metrics.get('hit_rate', 0.0)) * 100.0:.0f}%"
            )
            alert_color = Colors.ERROR if critical_count > 0 else "#B45309"
            self._alerts_label.setStyleSheet(f"color: {alert_color}; font-size: 11px;")

        if not recommendations:
            self._ai_label.setText("AI: no recommendation")
            self._ai_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        else:
            top = recommendations[0]
            first_action = str(top.actions[0]) if top.actions else ""
            recurring_text = ""
            if recurring:
                recurring_text = f" | recurring blocker SPID {int(recurring[0].session_id)}"
            self._ai_label.setText(f"AI: {top.title}. {first_action}{recurring_text}")
            severity = str(top.severity).lower()
            color = Colors.ERROR if severity == "critical" else ("#B45309" if severity == "warning" else Colors.TEXT_SECONDARY)
            self._ai_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _export_snapshot_csv(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Blocking Snapshot",
            f"blocking_snapshot_{timestamp}.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not target_path:
            return
        try:
            analysis = self._build_current_analysis() if self._blocking_sessions else None
            rows = self._blocking_service.export_blocking_snapshot_csv(target_path, analysis=analysis)
            self._status_label.setText(f"Snapshot exported: {rows} row(s)")
            self._status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
        except Exception as ex:
            QMessageBox.critical(self, "Export Error", f"Failed to export snapshot CSV:\n{ex}")
            self._on_error(f"Export snapshot failed: {ex}")

    def _export_audit_csv(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Kill Audit Log",
            f"blocking_kill_audit_{timestamp}.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not target_path:
            return
        try:
            rows = self._blocking_service.export_audit_logs_csv(target_path)
            self._status_label.setText(f"Audit log exported: {rows} row(s)")
            self._status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
        except Exception as ex:
            QMessageBox.critical(self, "Export Error", f"Failed to export audit CSV:\n{ex}")
            self._on_error(f"Export audit failed: {ex}")

    def _export_history_csv(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Blocking History",
            f"blocking_history_{timestamp}.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not target_path:
            return
        try:
            rows = self._blocking_service.export_blocking_history_csv(target_path, days=30)
            self._status_label.setText(f"Blocking history exported: {rows} row(s)")
            self._status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
        except Exception as ex:
            QMessageBox.critical(self, "Export Error", f"Failed to export history CSV:\n{ex}")
            self._on_error(f"Export history failed: {ex}")

    def _show_ai_brief(self) -> None:
        try:
            analysis = self._build_current_analysis() if self._blocking_sessions else None
            brief = self._blocking_service.generate_ai_brief(analysis=analysis, top_n=4)
            QMessageBox.information(self, "Blocking AI Brief", brief)
        except Exception as ex:
            QMessageBox.critical(self, "AI Brief Error", f"Failed to generate AI brief:\n{ex}")
            self._on_error(f"AI brief failed: {ex}")

    def _generate_blocking_report(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Generate Blocking Report",
            f"blocking_report_{timestamp}.md",
            "Markdown Files (*.md);;Text Files (*.txt);;All Files (*)",
        )
        if not target_path:
            return
        try:
            analysis = self._build_current_analysis() if self._blocking_sessions else None
            self._blocking_service.generate_blocking_report(target_path, analysis=analysis)
            self._status_label.setText("Blocking report generated")
            self._status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px;")
        except Exception as ex:
            QMessageBox.critical(self, "Report Error", f"Failed to generate blocking report:\n{ex}")
            self._on_error(f"Generate report failed: {ex}")
    
    def _show_context_menu(self, position):
        """Show context menu for tree item"""
        item = self._tree_widget.itemAt(position)
        if not item:
            return
        
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not session_id:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """)
        
        kill_action = menu.addAction("Kill Session")
        kill_action.triggered.connect(lambda: self._kill_session(session_id))
        
        menu.exec(self._tree_widget.mapToGlobal(position))
    
    def _show_head_blocker_menu(self, position):
        """Show context menu for head blocker"""
        item = self._head_blockers_tree.itemAt(position)
        if not item:
            return
        
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not session_id:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """)
        
        kill_action = menu.addAction("Kill Head Blocker")
        kill_action.triggered.connect(lambda: self._kill_session(session_id))
        
        menu.exec(self._head_blockers_tree.mapToGlobal(position))
    
    def _kill_selected_session(self):
        """Kill the currently selected session"""
        if self._selected_session:
            self._kill_session(self._selected_session)
    
    def _kill_session(self, session_id: int):
        """Kill a session"""
        safe_session_id = int(session_id or 0)
        if safe_session_id <= 0:
            QMessageBox.warning(self, "Invalid Session", "Session id must be greater than zero.")
            return

        reply = QMessageBox.warning(
            self,
            "Kill Session",
            f"Are you sure you want to kill session {safe_session_id}?\n\n"
            "This will terminate the session and rollback any active transaction.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            kill_result = self._blocking_service.kill_session(
                safe_session_id,
                killed_by="ui.blocking_view",
            )
        except Exception as ex:
            QMessageBox.critical(
                self,
                "Error",
                f"Unexpected error killing session {safe_session_id}:\n{ex}",
                QMessageBox.StandardButton.Ok,
            )
            logger.error(f"Unexpected kill session error: {ex}")
            return
        if not kill_result.success:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to kill session {safe_session_id}:\n{kill_result.error or 'Unknown error'}",
            )
            logger.error(f"Kill session rejected/failed: {kill_result.error}")
            return

        QMessageBox.information(
            self,
            "Success",
            f"Session {safe_session_id} has been terminated.",
        )

        # Refresh data
        self.refresh()
    
    def on_show(self) -> None:
        """Called when view is shown"""
        if not self._is_initialized:
            return
        if not self._blocking_service.is_connected:
            self._refresh_timer.stop()
            self._set_disconnected_state()
            return
        self.refresh()
        if self._auto_refresh_btn.isChecked():
            self._refresh_timer.start(5000)
    
    def on_hide(self) -> None:
        """Called when view is hidden"""
        self._refresh_timer.stop()
