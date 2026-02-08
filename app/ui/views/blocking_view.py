"""
Blocking Analysis View - Real-time blocking chain visualization
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QSplitter, QTextEdit,
    QFrame, QHeaderView, QMessageBox, QMenu, QGroupBox,
    QGridLayout, QScrollArea, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsRectItem, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QPointF, QRectF
from PyQt6.QtGui import QFont, QColor, QPen, QBrush, QPainter

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors
from app.core.logger import get_logger
from app.database.connection import get_connection_manager

logger = get_logger('ui.blocking_view')


@dataclass
class BlockingSession:
    """Blocking session data model"""
    session_id: int
    blocking_session_id: int
    wait_type: str
    wait_seconds: float
    database_name: str
    current_statement: str
    login_name: str
    host_name: str
    program_name: str
    cpu_seconds: float = 0
    blocker_query: str = ""


class BlockingWorker(QThread):
    """Background worker for fetching blocking data"""
    
    data_ready = pyqtSignal(list, list, dict)  # blocking_sessions, head_blockers, lock_details
    error_occurred = pyqtSignal(str)
    
    def run(self):
        """Fetch blocking information"""
        try:
            conn_mgr = get_connection_manager()
            active_conn = conn_mgr.active_connection
            
            if not active_conn or not active_conn.is_connected:
                self.data_ready.emit([], [], {})
                return
            
            # 1. Get blocking chain
            blocking_query = """
            WITH BlockingTree AS (
                SELECT 
                    r.session_id,
                    r.blocking_session_id,
                    r.wait_type,
                    r.wait_time / 1000 AS wait_seconds,
                    r.cpu_time / 1000 AS cpu_seconds,
                    DB_NAME(r.database_id) AS database_name,
                    SUBSTRING(st.text, (r.statement_start_offset/2)+1, 
                        ((CASE r.statement_end_offset
                            WHEN -1 THEN DATALENGTH(st.text)
                            ELSE r.statement_end_offset
                        END - r.statement_start_offset)/2)+1) AS current_statement,
                    s.login_name,
                    s.host_name,
                    s.program_name
                FROM sys.dm_exec_requests r
                JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
                CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) st
                WHERE r.blocking_session_id > 0
            )
            SELECT 
                blocked.session_id AS blocked_session,
                blocked.blocking_session_id AS blocker_session,
                blocked.wait_type,
                blocked.wait_seconds,
                blocked.cpu_seconds,
                blocked.database_name,
                blocked.current_statement AS blocked_query,
                blocked.login_name AS blocked_login,
                blocked.host_name AS blocked_host,
                blocked.program_name AS blocked_program,
                ISNULL(blocker.text, '') AS blocker_query
            FROM BlockingTree blocked
            LEFT JOIN sys.dm_exec_requests blocker_r ON blocked.blocking_session_id = blocker_r.session_id
            OUTER APPLY sys.dm_exec_sql_text(blocker_r.sql_handle) blocker
            ORDER BY blocked.wait_seconds DESC
            """
            
            blocking_results = active_conn.execute_query(blocking_query)
            
            blocking_sessions = []
            for row in blocking_results:
                session = BlockingSession(
                    session_id=row.get('blocked_session', 0),
                    blocking_session_id=row.get('blocker_session', 0),
                    wait_type=row.get('wait_type', ''),
                    wait_seconds=row.get('wait_seconds', 0) or 0,
                    database_name=row.get('database_name', ''),
                    current_statement=row.get('blocked_query', '') or '',
                    login_name=row.get('blocked_login', ''),
                    host_name=row.get('blocked_host', ''),
                    program_name=row.get('blocked_program', ''),
                    cpu_seconds=row.get('cpu_seconds', 0) or 0,
                    blocker_query=row.get('blocker_query', '') or ''
                )
                blocking_sessions.append(session)
            
            # 2. Get head blockers
            head_blocker_query = """
            SELECT DISTINCT
                r.blocking_session_id AS head_blocker_session,
                s.login_name,
                s.host_name,
                s.program_name,
                s.status,
                s.cpu_time / 1000 AS cpu_seconds,
                s.memory_usage * 8 AS memory_kb,
                DB_NAME(r.database_id) AS database_name,
                ISNULL(st.text, '') AS blocker_query,
                (SELECT COUNT(*) FROM sys.dm_exec_requests WHERE blocking_session_id = r.blocking_session_id) AS blocked_count
            FROM sys.dm_exec_requests r
            JOIN sys.dm_exec_sessions s ON r.blocking_session_id = s.session_id
            OUTER APPLY sys.dm_exec_sql_text(
                (SELECT sql_handle FROM sys.dm_exec_requests WHERE session_id = r.blocking_session_id)
            ) st
            WHERE r.blocking_session_id NOT IN (
                SELECT session_id FROM sys.dm_exec_requests WHERE blocking_session_id > 0
            )
            AND r.blocking_session_id > 0
            ORDER BY blocked_count DESC
            """
            
            head_blockers = active_conn.execute_query(head_blocker_query)
            
            # 3. Get lock summary
            lock_query = """
            SELECT 
                l.request_session_id AS session_id,
                DB_NAME(l.resource_database_id) AS database_name,
                l.resource_type,
                l.request_mode,
                l.request_status,
                COUNT(*) AS lock_count
            FROM sys.dm_tran_locks l
            WHERE l.request_session_id != @@SPID
            GROUP BY l.request_session_id, l.resource_database_id, l.resource_type, l.request_mode, l.request_status
            ORDER BY lock_count DESC
            """
            
            lock_details = {}
            try:
                lock_results = active_conn.execute_query(lock_query)
                for row in lock_results:
                    sid = row.get('session_id', 0)
                    if sid not in lock_details:
                        lock_details[sid] = []
                    lock_details[sid].append(row)
            except:
                pass
            
            self.data_ready.emit(blocking_sessions, head_blockers, lock_details)
            
        except Exception as e:
            logger.error(f"Blocking worker error: {e}")
            self.error_occurred.emit(str(e))


class BlockingGraphWidget(QGraphicsView):
    """Visual graph representation of blocking chains"""
    
    session_selected = pyqtSignal(int)  # session_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        
        self._nodes: Dict[int, QGraphicsEllipseItem] = {}
        self._edges: List[QGraphicsLineItem] = []
        self._labels: Dict[int, QGraphicsTextItem] = {}
        
    def clear_graph(self):
        """Clear all graph elements"""
        self._scene.clear()
        self._nodes.clear()
        self._edges.clear()
        self._labels.clear()
    
    def build_graph(self, blocking_sessions: List[BlockingSession], head_blockers: List[Dict]):
        """Build the blocking chain graph"""
        self.clear_graph()
        
        if not blocking_sessions and not head_blockers:
            # Show "No blocking" message
            text = self._scene.addText("✅ No Active Blocking")
            text.setDefaultTextColor(QColor(Colors.SUCCESS))
            text.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            text.setPos(50, 50)
            return
        
        # Collect all unique sessions
        all_sessions = set()
        edges = []
        
        for session in blocking_sessions:
            all_sessions.add(session.session_id)
            all_sessions.add(session.blocking_session_id)
            edges.append((session.blocking_session_id, session.session_id, session.wait_seconds))
        
        # Identify head blockers (sessions that block others but aren't blocked)
        blockers = {s.blocking_session_id for s in blocking_sessions}
        blocked = {s.session_id for s in blocking_sessions}
        head_blocker_ids = blockers - blocked
        
        # Layout nodes in a tree structure
        levels = self._calculate_levels(all_sessions, edges, head_blocker_ids)
        
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
        
        # Draw edges first (so they appear behind nodes)
        for blocker_id, blocked_id, wait_seconds in edges:
            if blocker_id in positions and blocked_id in positions:
                x1, y1 = positions[blocker_id]
                x2, y2 = positions[blocked_id]
                
                # Color based on wait time
                if wait_seconds > 30:
                    color = QColor("#EF4444")  # Red
                elif wait_seconds > 10:
                    color = QColor("#F59E0B")  # Amber
                else:
                    color = QColor("#6366F1")  # Indigo
                
                pen = QPen(color, 2)
                line = self._scene.addLine(x1, y1 + node_radius, x2, y2 - node_radius, pen)
                self._edges.append(line)
                
                # Add wait time label on edge
                mid_x = (x1 + x2) / 2
                mid_y = (y1 + y2) / 2
                wait_label = self._scene.addText(f"{wait_seconds:.0f}s")
                wait_label.setDefaultTextColor(color)
                wait_label.setFont(QFont("Segoe UI", 9))
                wait_label.setPos(mid_x + 5, mid_y - 10)
        
        # Draw nodes
        for sid, (x, y) in positions.items():
            is_head = sid in head_blocker_ids
            
            # Node color
            if is_head:
                color = QColor("#EF4444")  # Red for head blockers
                border_color = QColor("#B91C1C")
            elif sid in blocked:
                color = QColor("#F59E0B")  # Amber for blocked
                border_color = QColor("#D97706")
            else:
                color = QColor("#3B82F6")  # Blue for others
                border_color = QColor("#1D4ED8")
            
            # Draw node
            node = self._scene.addEllipse(
                x - node_radius, y - node_radius,
                node_radius * 2, node_radius * 2,
                QPen(border_color, 3),
                QBrush(color)
            )
            node.setData(0, sid)  # Store session_id
            self._nodes[sid] = node
            
            # Session ID label
            label = self._scene.addText(str(sid))
            label.setDefaultTextColor(QColor("white"))
            label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            label.setPos(x - 15, y - 10)
            self._labels[sid] = label
            
            # Head blocker indicator
            if is_head:
                crown = self._scene.addText("👑")
                crown.setFont(QFont("Segoe UI Emoji", 14))
                crown.setPos(x - 12, y - node_radius - 25)
        
        # Adjust scene rect
        self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
    
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
        if item and isinstance(item, QGraphicsEllipseItem):
            sid = item.data(0)
            if sid:
                self.session_selected.emit(sid)
        super().mousePressEvent(event)


class StatCard(QFrame):
    """Circle stat card for summary panel - GUI-05 Style"""
    
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
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
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
        color = self.STATUS_COLORS.get(status, Colors.SUCCESS)
        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: 700; background: transparent; border: none;"
        )
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle_layout.addWidget(self._value_label)
        
        # Title with icon
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; background: transparent;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(circle)
        layout.addWidget(title_label)
    
    def update_value(self, value: str, status: str = "normal"):
        color = self.STATUS_COLORS.get(status, Colors.SUCCESS)
        self._value_label.setText(value)
        self._value_label.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: 700; background: transparent; border: none;"
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
        self._blocking_sessions: List[BlockingSession] = []
        self._head_blockers: List[Dict] = []
        self._lock_details: Dict[int, List] = {}
        self._selected_session: Optional[int] = None
        self._worker: Optional[BlockingWorker] = None
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self.refresh)
    
    @property
    def view_title(self) -> str:
        return "Blocking Analysis"
    
    def _setup_ui(self) -> None:
        """Setup the blocking view UI"""
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("🔒 Blocking Analysis")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Auto-refresh toggle
        self._auto_refresh_btn = QPushButton("⏸️ Auto-Refresh: ON")
        self._auto_refresh_btn.setCheckable(True)
        self._auto_refresh_btn.setChecked(True)
        self._auto_refresh_btn.clicked.connect(self._toggle_auto_refresh)
        self._auto_refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px 16px;
                color: {Colors.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {Colors.BACKGROUND};
            }}
            QPushButton:checked {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """)
        header_layout.addWidget(self._auto_refresh_btn)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setStyleSheet(f"""
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
        """)
        header_layout.addWidget(refresh_btn)
        
        self._main_layout.addLayout(header_layout)
        
        # Summary cards
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(16)
        
        self._total_blocking_card = StatCard("Total Blocking", "0", "🔒", "success")
        self._head_blocker_card = StatCard("Head Blockers", "0", "👑", "success")
        self._max_wait_card = StatCard("Max Wait", "0s", "⏱️", "success")
        self._affected_card = StatCard("Affected Sessions", "0", "👥", "success")
        
        summary_layout.addWidget(self._total_blocking_card)
        summary_layout.addWidget(self._head_blocker_card)
        summary_layout.addWidget(self._max_wait_card)
        summary_layout.addWidget(self._affected_card)
        summary_layout.addStretch()
        
        self._main_layout.addLayout(summary_layout)
        self._main_layout.addSpacing(16)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: transparent;
                width: 8px;
            }
        """)
        
        # Left panel: Graph + Tree
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        
        # Tabs for Graph and Tree view
        self._view_tabs = QTabWidget()
        self._view_tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
                background-color: {Colors.SURFACE};
            }}
            QTabBar::tab {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 16px;
                margin-right: 4px;
                color: {Colors.TEXT_SECONDARY};
            }}
            QTabBar::tab:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """)
        
        # Graph view tab
        self._graph_widget = BlockingGraphWidget()
        self._graph_widget.session_selected.connect(self._on_session_selected)
        self._view_tabs.addTab(self._graph_widget, "📊 Graph View")
        
        # Tree view tab
        self._tree_widget = QTreeWidget()
        self._tree_widget.setHeaderLabels([
            "Session ID", "Wait Type", "Wait Time", "Database", "Login", "Host"
        ])
        self._tree_widget.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
                color: {Colors.TEXT_PRIMARY};
            }}
            QTreeWidget::item {{
                padding: 8px 4px;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QTreeWidget::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {Colors.BACKGROUND};
                color: {Colors.TEXT_PRIMARY};
                padding: 8px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
                font-weight: 600;
            }}
        """)
        self._tree_widget.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._tree_widget.itemClicked.connect(self._on_tree_item_clicked)
        self._tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree_widget.customContextMenuRequested.connect(self._show_context_menu)
        self._view_tabs.addTab(self._tree_widget, "🌲 Tree View")
        
        left_layout.addWidget(self._view_tabs)
        
        # Head blockers list
        head_group = QGroupBox("👑 Head Blockers")
        head_group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
                font-weight: bold;
                color: {Colors.TEXT_PRIMARY};
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }}
        """)
        head_layout = QVBoxLayout(head_group)
        
        self._head_blockers_tree = QTreeWidget()
        self._head_blockers_tree.setHeaderLabels([
            "Session", "Login", "Host", "Program", "Blocked Count", "CPU (s)"
        ])
        self._head_blockers_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: transparent;
                border: none;
                color: {Colors.TEXT_PRIMARY};
            }}
            QTreeWidget::item {{
                padding: 6px 4px;
            }}
            QTreeWidget::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """)
        self._head_blockers_tree.setMaximumHeight(150)
        self._head_blockers_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._head_blockers_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._head_blockers_tree.customContextMenuRequested.connect(self._show_head_blocker_menu)
        head_layout.addWidget(self._head_blockers_tree)
        
        left_layout.addWidget(head_group)
        
        splitter.addWidget(left_widget)
        
        # Right panel: Session details
        right_widget = QFrame()
        right_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
        """)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(16, 16, 16, 16)
        
        # Details header
        details_header = QLabel("📋 Session Details")
        details_header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: bold; font-size: 14px;")
        right_layout.addWidget(details_header)
        
        self._details_label = QLabel("Select a session to view details")
        self._details_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        self._details_label.setWordWrap(True)
        right_layout.addWidget(self._details_label)
        
        # Query text area
        query_label = QLabel("📝 Current Query:")
        query_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 600; margin-top: 12px;")
        right_layout.addWidget(query_label)
        
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
        right_layout.addWidget(self._query_text, 1)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self._kill_btn = QPushButton("⚠️ Kill Session")
        self._kill_btn.setEnabled(False)
        self._kill_btn.clicked.connect(self._kill_selected_session)
        self._kill_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ERROR};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #DC2626;
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_SECONDARY};
            }}
        """)
        action_layout.addWidget(self._kill_btn)
        
        action_layout.addStretch()
        right_layout.addLayout(action_layout)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])
        
        self._main_layout.addWidget(splitter, 1)
        
        # Status bar
        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        self._main_layout.addWidget(self._status_label)
    
    def _toggle_auto_refresh(self):
        """Toggle auto-refresh"""
        if self._auto_refresh_btn.isChecked():
            self._auto_refresh_btn.setText("⏸️ Auto-Refresh: ON")
            self._refresh_timer.start(5000)  # 5 seconds
        else:
            self._auto_refresh_btn.setText("▶️ Auto-Refresh: OFF")
            self._refresh_timer.stop()
    
    def refresh(self) -> None:
        """Refresh blocking data"""
        if not self._is_initialized:
            return
            
        if self._worker and self._worker.isRunning():
            return
        
        self._status_label.setText("🔄 Refreshing...")
        
        self._worker = BlockingWorker()
        self._worker.data_ready.connect(self._on_data_ready)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.start()
    
    def _on_data_ready(self, blocking_sessions: List[BlockingSession], 
                       head_blockers: List[Dict], lock_details: Dict):
        """Handle data received"""
        self._blocking_sessions = blocking_sessions
        self._head_blockers = head_blockers
        self._lock_details = lock_details
        
        # Update summary cards
        total = len(blocking_sessions)
        heads = len(head_blockers)
        max_wait = max((s.wait_seconds for s in blocking_sessions), default=0)
        affected = len(set(s.session_id for s in blocking_sessions))
        
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
        
        # Update graph
        self._graph_widget.build_graph(blocking_sessions, head_blockers)
        
        # Update tree
        self._update_tree()
        
        # Update head blockers list
        self._update_head_blockers()
        
        # Update status
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._status_label.setText(f"✅ Last updated: {timestamp}")
    
    def _on_error(self, error: str):
        """Handle error"""
        self._status_label.setText(f"⚠️ Error: {error}")
        logger.error(f"Blocking view error: {error}")
    
    def _update_tree(self):
        """Update blocking tree"""
        self._tree_widget.clear()
        
        # Build tree structure
        # Group by blocker
        blockers = {}
        for session in self._blocking_sessions:
            if session.blocking_session_id not in blockers:
                blockers[session.blocking_session_id] = []
            blockers[session.blocking_session_id].append(session)
        
        # Add items
        for blocker_id, blocked_sessions in blockers.items():
            # Blocker item (root)
            blocker_item = QTreeWidgetItem([
                f"🔴 {blocker_id} (Blocker)",
                "", "", "", "", ""
            ])
            blocker_item.setData(0, Qt.ItemDataRole.UserRole, blocker_id)
            blocker_item.setForeground(0, QColor(Colors.ERROR))
            self._tree_widget.addTopLevelItem(blocker_item)
            
            # Blocked sessions (children)
            for session in blocked_sessions:
                wait_color = QColor(Colors.ERROR) if session.wait_seconds > 30 else (
                    QColor("#F59E0B") if session.wait_seconds > 10 else QColor(Colors.TEXT_PRIMARY)
                )
                
                child_item = QTreeWidgetItem([
                    f"🟡 {session.session_id}",
                    session.wait_type,
                    f"{session.wait_seconds:.0f}s",
                    session.database_name,
                    session.login_name,
                    session.host_name
                ])
                child_item.setData(0, Qt.ItemDataRole.UserRole, session.session_id)
                child_item.setForeground(2, wait_color)
                blocker_item.addChild(child_item)
            
            blocker_item.setExpanded(True)
    
    def _update_head_blockers(self):
        """Update head blockers list"""
        self._head_blockers_tree.clear()
        
        for blocker in self._head_blockers:
            item = QTreeWidgetItem([
                str(blocker.get('head_blocker_session', '')),
                blocker.get('login_name', ''),
                blocker.get('host_name', ''),
                blocker.get('program_name', ''),
                str(blocker.get('blocked_count', 0)),
                f"{blocker.get('cpu_seconds', 0):.1f}"
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, blocker.get('head_blocker_session'))
            item.setForeground(0, QColor(Colors.ERROR))
            self._head_blockers_tree.addTopLevelItem(item)
    
    def _on_session_selected(self, session_id: int):
        """Handle session selection from graph"""
        self._selected_session = session_id
        self._update_session_details(session_id)
        self._kill_btn.setEnabled(True)
    
    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click"""
        session_id = item.data(0, Qt.ItemDataRole.UserRole)
        if session_id:
            self._selected_session = session_id
            self._update_session_details(session_id)
            self._kill_btn.setEnabled(True)
    
    def _update_session_details(self, session_id: int):
        """Update session details panel"""
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
            details = f"""
<b>Session ID:</b> {session.session_id}<br>
<b>Blocked By:</b> {session.blocking_session_id}<br>
<b>Wait Type:</b> {session.wait_type}<br>
<b>Wait Time:</b> {session.wait_seconds:.1f} seconds<br>
<b>Database:</b> {session.database_name}<br>
<b>Login:</b> {session.login_name}<br>
<b>Host:</b> {session.host_name}<br>
<b>Program:</b> {session.program_name}<br>
<b>CPU Time:</b> {session.cpu_seconds:.1f} seconds
"""
            self._details_label.setText(details)
            self._query_text.setPlainText(session.current_statement or "No query available")
        else:
            # Check in head blockers
            for blocker in self._head_blockers:
                if blocker.get('head_blocker_session') == session_id:
                    details = f"""
<b>Session ID:</b> {session_id} <span style="color: {Colors.ERROR};">(HEAD BLOCKER)</span><br>
<b>Login:</b> {blocker.get('login_name', '')}<br>
<b>Host:</b> {blocker.get('host_name', '')}<br>
<b>Program:</b> {blocker.get('program_name', '')}<br>
<b>Status:</b> {blocker.get('status', '')}<br>
<b>Blocked Sessions:</b> {blocker.get('blocked_count', 0)}<br>
<b>CPU Time:</b> {blocker.get('cpu_seconds', 0):.1f} seconds<br>
<b>Memory:</b> {blocker.get('memory_kb', 0):,} KB
"""
                    self._details_label.setText(details)
                    self._query_text.setPlainText(blocker.get('blocker_query', '') or "No query available")
                    return
            
            self._details_label.setText(f"Session {session_id} selected")
            self._query_text.clear()
    
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
        
        kill_action = menu.addAction("⚠️ Kill Session")
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
        
        kill_action = menu.addAction("⚠️ Kill Head Blocker")
        kill_action.triggered.connect(lambda: self._kill_session(session_id))
        
        menu.exec(self._head_blockers_tree.mapToGlobal(position))
    
    def _kill_selected_session(self):
        """Kill the currently selected session"""
        if self._selected_session:
            self._kill_session(self._selected_session)
    
    def _kill_session(self, session_id: int):
        """Kill a session"""
        reply = QMessageBox.warning(
            self,
            "Kill Session",
            f"Are you sure you want to kill session {session_id}?\n\n"
            "This will terminate the session and rollback any active transaction.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            conn_mgr = get_connection_manager()
            active_conn = conn_mgr.active_connection
            
            if not active_conn or not active_conn.is_connected:
                QMessageBox.warning(self, "Error", "No active database connection")
                return
            
            # Execute KILL command
            active_conn.execute_query(f"KILL {session_id}")
            
            QMessageBox.information(
                self, "Success", 
                f"Session {session_id} has been terminated."
            )
            
            # Refresh data
            self.refresh()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to kill session {session_id}:\n{str(e)}"
            )
            logger.error(f"Kill session error: {e}")
    
    def on_show(self) -> None:
        """Called when view is shown"""
        if not self._is_initialized:
            return
        self.refresh()
        if self._auto_refresh_btn.isChecked():
            self._refresh_timer.start(5000)
    
    def on_hide(self) -> None:
        """Called when view is hidden"""
        self._refresh_timer.stop()
