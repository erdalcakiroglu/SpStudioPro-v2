"""
Dashboard View - Server overview and quick stats with Modern Enterprise Design
Based on GUI-05.py design - 4x4 Metric Cards Grid
"""

from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QComboBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors
from app.core.logger import get_logger
from app.database.connection import get_connection_manager

logger = get_logger('ui.dashboard')


class MetricCard(QFrame):
    """A card widget for displaying performance metrics - GUI-05 style."""
    
    def __init__(
        self, 
        title: str, 
        value: str = "0", 
        unit: str = "",
        help_text: str = "",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.help_text = help_text
        self._setup_ui(title, value, unit)
    
    def _setup_ui(self, title: str, value: str, unit: str) -> None:
        # Card styling - GUI-05 style
        self.setStyleSheet(f"""
            #MetricCard {{
                background-color: {Colors.SURFACE};
                border: 0.5px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 8px;
            }}
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
        title_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 700;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Help button
        if self.help_text:
            help_btn = QPushButton("?")
            help_btn.setFixedSize(16, 16)
            help_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {Colors.BORDER_DARK};
                    border-radius: 8px;
                    color: {Colors.TEXT_SECONDARY};
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
                    border-color: {Colors.TEXT_MUTED};
                }}
            """)
            help_btn.clicked.connect(self._show_help)
            title_layout.addWidget(help_btn)
        
        layout.addLayout(title_layout)
        
        # Value label
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 24px; font-weight: 600;")
        layout.addWidget(self.value_label)
        
        # Unit label
        if unit:
            self.unit_label = QLabel(unit)
            self.unit_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
            layout.addWidget(self.unit_label)
        else:
            self.unit_label = None
        
        layout.addStretch()
        
        # Sizing
        self.setMinimumHeight(100)
    
    def _show_help(self):
        """Show help dialog."""
        help_dialog = QMessageBox(self)
        help_dialog.setWindowTitle("Help")
        help_dialog.setText(self.help_text)
        help_dialog.setIcon(QMessageBox.Icon.Information)
        help_dialog.setStyleSheet(f"""
            QMessageBox {{
                background-color: {Colors.SURFACE};
            }}
            QMessageBox QLabel {{
                color: {Colors.TEXT_PRIMARY};
            }}
            QMessageBox QPushButton {{
                min-width: 60px;
                padding: 4px 12px;
                background-color: {Colors.PRIMARY};
                color: #ffffff;
                border: none;
                border-radius: 4px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        help_dialog.exec()
    
    def set_value(self, value: str, status: str = "normal") -> None:
        """Update the value and status."""
        self.value_label.setText(value)
        if status == "good":
            color = Colors.SUCCESS
        elif status == "bad":
            color = Colors.ERROR
        elif status == "warning":
            color = Colors.WARNING
        else:
            color = Colors.TEXT_PRIMARY
        self.value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 600;")


class DashboardView(BaseView):
    """
    Server overview dashboard - GUI-05 style
    Shows key metrics in a 4x4 grid with refresh controls
    """
    
    action_requested = pyqtSignal(str)
    
    # Refresh intervals in milliseconds
    REFRESH_INTERVALS = {
        "5s": 5000,
        "15s": 15000,
        "30s": 30000,
        "60s": 60000,
    }
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._metric_cards: Dict[str, MetricCard] = {}
        self._last_server = ""
        self._last_version = ""
        self._is_refreshing = False
        self._has_loaded_once = False
        
        # Refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
    
    @property
    def view_title(self) -> str:
        return "Dashboard"
    
    def _setup_ui(self) -> None:
        """Setup dashboard UI with modern enterprise design - GUI-05 style"""
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        
        # Main layout with padding
        main_widget = QWidget()
        main_widget.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(32, 24, 32, 24)
        main_layout.setSpacing(16)
        
        # Header row with title and refresh controls
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)
        
        # Title
        title = QLabel("Dashboard")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY}; 
            font-size: 20px; 
            font-weight: 700;
            background: transparent;
        """)
        header_row.addWidget(title)
        header_row.addStretch()
        
        # Refresh rate label
        refresh_label = QLabel("Refresh rate:")
        refresh_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        header_row.addWidget(refresh_label)
        
        # Refresh rate combo
        self._cmb_refresh_rate = QComboBox()
        self._cmb_refresh_rate.setMinimumWidth(80)
        self._cmb_refresh_rate.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._cmb_refresh_rate.addItems(["5s", "15s", "30s", "60s"])
        self._cmb_refresh_rate.setCurrentIndex(1)  # Default 15s
        self._cmb_refresh_rate.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {Colors.TEXT_SECONDARY};
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                selection-background-color: {Colors.PRIMARY_LIGHT};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        self._cmb_refresh_rate.currentIndexChanged.connect(self._on_refresh_rate_changed)
        header_row.addWidget(self._cmb_refresh_rate)
        
        # Stop/Start button (default: stopped)
        self._btn_refresh_stop = QPushButton("Start")
        self._btn_refresh_stop.setFixedHeight(26)
        self._btn_refresh_stop.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        self._btn_refresh_stop.clicked.connect(self._toggle_refresh)
        header_row.addWidget(self._btn_refresh_stop)
        
        main_layout.addLayout(header_row)
        
        # Subtitle
        self._subtitle_label = QLabel(
            "High-level overview of server health, workload and alerts. Rates are averaged over the last refresh interval."
        )
        self._subtitle_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px; background: transparent;")
        main_layout.addWidget(self._subtitle_label)
        
        # Scroll area for metrics
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ 
                border: none; 
                background-color: transparent; 
            }}
            QScrollBar:vertical {{
                width: 8px;
                background-color: transparent;
            }}
            QScrollBar::handle:vertical {{
                background-color: {Colors.BORDER_DARK};
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {Colors.TEXT_MUTED};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(16)
        
        # Performance Metrics Section - 4x4 Grid
        metrics_grid = self._create_metrics_grid()
        scroll_layout.addLayout(metrics_grid)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        self._main_layout.addWidget(main_widget)
    
    def _create_metrics_grid(self) -> QGridLayout:
        """Create performance metrics grid - GUI-05 style (4x4)"""
        # Metrics data: (key, title, unit, help_text)
        metrics_data = [
            # Row 1
            ("active_sessions", "Active Sessions", "", "Number of currently active sessions connected to the database."),
            ("os_cpu", "OS Total CPU %", "%", "Total CPU usage percentage across all processors on the operating system."),
            ("sql_cpu", "SQL Process CPU %", "%", "CPU usage percentage for the SQL Server process specifically."),
            ("os_memory", "Available OS Memory (MB)", "MB", "Amount of free memory available in megabytes on the operating system."),
            
            # Row 2
            ("ple", "PLE (sec)", "sec", "Page Life Expectancy - average time a page stays in the buffer pool (higher is better)."),
            ("buffer_cache", "Buffer Cache Hit Ratio %", "%", "Percentage of page requests found in buffer cache without disk I/O."),
            ("batch_requests", "Batch Requests / sec", "req/s", "Number of batch requests received per second."),
            ("transactions", "Transactions / sec (avg)", "tx/s", "Average committed transactions per second over the last refresh interval."),
            
            # Row 3
            ("io_read_latency", "IO Read Latency (ms)", "ms", "Average time in milliseconds for a read operation to complete."),
            ("io_write_latency", "IO Write Latency (ms)", "ms", "Average time in milliseconds for a write operation to complete."),
            ("log_write_latency", "Log Write Latency (ms)", "ms", "Average time in milliseconds for transaction log writes to complete."),
            ("signal_wait", "Signal Wait %", "%", "Percentage of time threads spent waiting for CPU (scheduler inefficiency)."),
            
            # Row 4
            ("blocked_sessions", "Blocked Sessions", "", "Number of sessions currently blocked waiting for a resource."),
            ("runnable_tasks", "Runnable Tasks", "", "Number of tasks waiting to run on the scheduler."),
            ("tempdb_log_used", "TempDB Log Used %", "%", "Percentage of temporary database transaction log currently in use."),
            ("blocking", "Blocking", "", "SPID of the session currently blocking another session (0 if none)."),
        ]
        
        grid = QGridLayout()
        grid.setSpacing(12)
        
        for idx, (key, title, unit, help_text) in enumerate(metrics_data):
            card = MetricCard(title, "0", unit, help_text)
            self._metric_cards[key] = card
            row = idx // 4
            col = idx % 4
            grid.addWidget(card, row, col)
        
        # Set equal column stretch
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)
        
        return grid
    
    def _on_refresh_rate_changed(self, index: int) -> None:
        """Handle refresh rate change"""
        if self._is_refreshing:
            interval_text = self._cmb_refresh_rate.currentText()
            interval = self.REFRESH_INTERVALS.get(interval_text, 15000)
            self._refresh_timer.setInterval(interval)
            logger.info(f"Refresh rate changed to {interval_text}")
    
    def _toggle_refresh(self) -> None:
        """Toggle auto-refresh on/off"""
        if self._is_refreshing:
            # Stop refreshing
            self._refresh_timer.stop()
            self._is_refreshing = False
            self._btn_refresh_stop.setText("Start")
            self._btn_refresh_stop.setStyleSheet(f"""
                QPushButton {{
                    background-color: {Colors.PRIMARY};
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {Colors.PRIMARY_HOVER};
                }}
            """)
            logger.info("Auto-refresh stopped")
        else:
            # Start refreshing
            interval_text = self._cmb_refresh_rate.currentText()
            interval = self.REFRESH_INTERVALS.get(interval_text, 15000)
            self._refresh_timer.setInterval(interval)
            self._refresh_timer.start()
            self._is_refreshing = True
            self._btn_refresh_stop.setText("Stop")
            self._btn_refresh_stop.setStyleSheet(f"""
                QPushButton {{
                    background-color: #f3f4f6;
                    color: {Colors.TEXT_PRIMARY};
                    border: 1px solid {Colors.BORDER};
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {Colors.BORDER};
                }}
            """)
            self.refresh()  # Immediate refresh
            logger.info(f"Auto-refresh started ({interval_text})")
    
    def update_server_info(self, server: str, version: str = "") -> None:
        """Update server connection info"""
        self._last_server = server
        self._last_version = version

    def on_show(self) -> None:
        """Refresh when view is shown"""
        if not self._is_initialized:
            return
        if not self._has_loaded_once:
            self.refresh()
        if self._is_refreshing:
            interval_text = self._cmb_refresh_rate.currentText()
            interval = self.REFRESH_INTERVALS.get(interval_text, 15000)
            self._refresh_timer.setInterval(interval)
            self._refresh_timer.start()

    def on_hide(self) -> None:
        """Stop refresh when view is hidden"""
        self._refresh_timer.stop()
    
    def update_metric(self, metric_key: str, value: str, status: str = "normal") -> None:
        """Update a specific metric value"""
        if metric_key in self._metric_cards:
            self._metric_cards[metric_key].set_value(value, status)
    
    def refresh(self) -> None:
        """Refresh dashboard data from SQL Server"""
        if not self._is_initialized:
            return
            
        from app.services.dashboard_service import get_dashboard_service
        
        service = get_dashboard_service()
        
        if not service.is_connected:
            logger.debug("Dashboard refresh skipped: No active connection")
            return

        logger.info("Refreshing dashboard stats...")
        
        try:
            metrics = service.get_all_metrics()
            
            # Active Sessions
            self.update_metric("active_sessions", str(metrics.active_sessions),
                             "normal" if metrics.active_sessions < 50 else ("warning" if metrics.active_sessions < 100 else "bad"))
            
            # OS Total CPU %
            self.update_metric("os_cpu", str(metrics.cpu_percent),
                             "normal" if metrics.cpu_percent < 70 else ("warning" if metrics.cpu_percent < 90 else "bad"))
            
            # SQL Process CPU %
            sql_cpu = getattr(metrics, 'sql_cpu_percent', metrics.cpu_percent)
            self.update_metric("sql_cpu", str(sql_cpu),
                             "normal" if sql_cpu < 70 else ("warning" if sql_cpu < 90 else "bad"))
            
            # Available OS Memory (MB)
            os_memory = getattr(metrics, 'available_memory_mb', 0)
            self.update_metric("os_memory", str(os_memory),
                             "good" if os_memory > 2048 else ("warning" if os_memory > 512 else "bad"))
            
            # PLE (sec)
            self.update_metric("ple", str(metrics.ple_seconds),
                             "good" if metrics.ple_seconds > 300 else ("warning" if metrics.ple_seconds > 60 else "bad"))
            
            # Buffer Cache Hit Ratio %
            buffer_cache = getattr(metrics, 'buffer_cache_hit_ratio', 99)
            self.update_metric("buffer_cache", str(buffer_cache),
                             "good" if buffer_cache > 95 else ("warning" if buffer_cache > 90 else "bad"))
            
            # Batch Requests / sec
            self.update_metric("batch_requests", str(metrics.batch_requests), "normal")
            
            # Transactions / sec
            transactions = getattr(metrics, 'transactions_per_sec', 0)
            self.update_metric("transactions", str(transactions), "normal")
            
            # IO Read Latency (ms)
            read_latency = getattr(metrics, 'read_latency_ms', metrics.disk_latency_ms)
            self.update_metric("io_read_latency", str(int(read_latency)),
                             "good" if read_latency < 5 else ("warning" if read_latency < 20 else "bad"))
            
            # IO Write Latency (ms)
            write_latency = getattr(metrics, 'write_latency_ms', metrics.disk_latency_ms)
            self.update_metric("io_write_latency", str(int(write_latency)),
                             "good" if write_latency < 5 else ("warning" if write_latency < 20 else "bad"))
            
            # Log Write Latency (ms)
            log_latency = getattr(metrics, 'log_write_latency_ms', 0)
            self.update_metric("log_write_latency", str(int(log_latency)),
                             "good" if log_latency < 5 else ("warning" if log_latency < 20 else "bad"))
            
            # Signal Wait %
            signal_wait = getattr(metrics, 'signal_wait_percent', 0)
            self.update_metric("signal_wait", str(signal_wait),
                             "good" if signal_wait < 10 else ("warning" if signal_wait < 25 else "bad"))
            
            # Blocked Sessions
            self.update_metric("blocked_sessions", str(metrics.blocking_count),
                             "good" if metrics.blocking_count == 0 else ("warning" if metrics.blocking_count < 3 else "bad"))
            
            # Runnable Tasks
            runnable_tasks = getattr(metrics, 'runnable_tasks', 0)
            self.update_metric("runnable_tasks", str(runnable_tasks),
                             "normal" if runnable_tasks < 10 else ("warning" if runnable_tasks < 50 else "bad"))
            
            # TempDB Log Used %
            self.update_metric("tempdb_log_used", str(metrics.tempdb_percent),
                             "good" if metrics.tempdb_percent < 50 else ("warning" if metrics.tempdb_percent < 80 else "bad"))
            
            # Blocking (head blocker SPID)
            blocking_spid = getattr(metrics, 'blocking_spid', 0)
            self.update_metric("blocking", str(blocking_spid),
                             "good" if blocking_spid == 0 else "bad")

            self._has_loaded_once = True
            
        except Exception as e:
            logger.error(f"Failed to refresh dashboard stats: {e}")
