"""
Dashboard View - Server overview and quick stats with Modern Enterprise Design
Based on GUI-05.py design - 4x4 Metric Cards Grid
"""

from typing import Optional, Dict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QGridLayout, QSizePolicy, QMessageBox,
    QPushButton, QComboBox, QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors
from app.ui.theme import Colors, Theme as ThemeStyles
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
        # Compact spacing to help the full dashboard fit without vertical scrolling.
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        
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
        # Add a touch of bottom padding to avoid glyph descenders getting clipped on some DPI/font combos.
        self.value_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 24px; font-weight: 600; padding-bottom: 2px;"
        )
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
        # Slightly taller to avoid clipping at some DPI settings.
        self.setMinimumHeight(108)
    
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


class MetricBarRow(QWidget):
    """Compact metric row with value + progress bar (Wait Categories style)."""

    _STATUS_COLORS = {
        "good": Colors.SUCCESS,
        "bad": Colors.ERROR,
        "warning": Colors.WARNING,
        "normal": Colors.PRIMARY,
    }

    _STATUS_GAUGE = {
        "good": 20.0,
        "normal": 40.0,
        "warning": 70.0,
        "bad": 90.0,
    }

    def __init__(self, label: str, unit: str = "", help_text: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._unit = str(unit or "").strip()
        self._help_text = str(help_text or "").strip()
        self._setup_ui(str(label or ""))

    def _setup_ui(self, label: str) -> None:
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._name_label = QLabel(label)
        if self._help_text:
            self._name_label.setToolTip(self._help_text)
        self._name_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600; background: transparent;"
        )
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._name_label.setMinimumWidth(110)
        layout.addWidget(self._name_label)

        colon = QLabel(":")
        colon.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600; background: transparent;"
        )
        colon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        colon.setFixedWidth(10)
        layout.addWidget(colon)

        self._value_label = QLabel("--")
        self._value_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 11px; font-weight: 700; background: transparent;"
        )
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._value_label.setMinimumWidth(86)
        layout.addWidget(self._value_label)

        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(10)
        self._bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self._bar, 1)

        self._pct_label = QLabel("")
        self._pct_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; font-weight: 700; background: transparent;"
        )
        self._pct_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._pct_label.setFixedWidth(54)
        layout.addWidget(self._pct_label)

        self._apply_bar_style(self._STATUS_COLORS["normal"])

    @staticmethod
    def _safe_float(value: object) -> Optional[float]:
        try:
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return float(value)
            text = str(value).strip().replace(",", "")
            if not text:
                return None
            return float(text)
        except Exception:
            return None

    def _apply_bar_style(self, color: str) -> None:
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {Colors.BORDER};
                border-radius: 5px;
                background: {Colors.BACKGROUND};
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 4px;
            }}
        """)
        self._pct_label.setStyleSheet(
            f"color: {color}; font-size: 10px; font-weight: 700; background: transparent;"
        )

    def set_value(self, value: str, status: str = "normal") -> None:
        status_key = str(status or "normal").strip().lower()
        accent = self._STATUS_COLORS.get(status_key, self._STATUS_COLORS["normal"])

        raw_num = self._safe_float(value)
        unit = self._unit
        if unit == "%":
            display_value = f"{int(raw_num) if raw_num is not None else str(value)}%"
            pct = float(max(0.0, min(100.0, raw_num if raw_num is not None else 0.0)))
        else:
            display_value = str(value)
            if unit:
                display_value = f"{display_value} {unit}"
            pct = float(self._STATUS_GAUGE.get(status_key, self._STATUS_GAUGE["normal"]))

        self._value_label.setText(display_value)
        self._apply_bar_style(accent)
        self._bar.setValue(int(max(0.0, min(100.0, pct)) * 10.0))
        self._pct_label.setText(f"{pct:.1f}%")


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
        self._metric_rows: Dict[str, MetricBarRow] = {}
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
        # Compact overall padding/spacing so the full dashboard can fit without vertical scrolling.
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(12)
        
        # Header row with title and refresh controls
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)
        
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
        self._cmb_refresh_rate.currentIndexChanged.connect(self._on_refresh_rate_changed)
        self._cmb_refresh_rate.setStyleSheet(ThemeStyles.combobox_style())
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
        scroll_layout.setSpacing(12)
        
        # Grouped Metrics Sections (keep MetricCard look; change only grouping/layout)
        self._create_metrics_sections(scroll_layout)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        self._main_layout.addWidget(main_widget)
    
    def _create_metrics_sections(self, parent_layout: QVBoxLayout) -> None:
        """Create grouped metric sections in the requested order (cards unchanged)."""

        def add_section(title: str, metrics_data: list[tuple[str, str, str, str]]) -> None:
            section_widget = QWidget()
            section_widget.setStyleSheet("background: transparent;")
            section_layout = QVBoxLayout(section_widget)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(4)

            header = QLabel(title)
            header.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;"
            )
            section_layout.addWidget(header)

            panel = QFrame()
            panel.setObjectName("MetricPanel")
            panel.setStyleSheet(f"""
                QFrame#MetricPanel {{
                    background-color: {Colors.SURFACE};
                    border: 0.5px solid {Colors.BORDER};
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
            panel_layout = QVBoxLayout(panel)
            panel_layout.setContentsMargins(10, 10, 10, 10)
            panel_layout.setSpacing(6)

            rows_grid = QGridLayout()
            rows_grid.setContentsMargins(0, 0, 0, 0)
            rows_grid.setHorizontalSpacing(16)
            rows_grid.setVerticalSpacing(8)

            for idx, (key, card_title, unit, help_text) in enumerate(metrics_data):
                row_widget = MetricBarRow(card_title, unit, help_text)
                self._metric_rows[key] = row_widget
                row = idx // 2
                col = idx % 2
                rows_grid.addWidget(row_widget, row, col)

            rows_grid.setColumnStretch(0, 1)
            rows_grid.setColumnStretch(1, 1)
            panel_layout.addLayout(rows_grid)
            section_layout.addWidget(panel)
            parent_layout.addWidget(section_widget)

        # 1) SERVER HEALTH
        add_section(
            "SERVER HEALTH",
            [
                (
                    "os_cpu",
                    "CPU %",
                    "%",
                    "Overall OS CPU utilization (all cores).\n\n"
                    "Use this to understand whether the host is CPU-bound. If OS CPU is high but SQL CPU is low, "
                    "the pressure may be coming from another process. Sustained >80-90% typically indicates CPU pressure.",
                ),
                (
                    "sql_cpu",
                    "SQL CPU %",
                    "%",
                    "SQL Server process CPU utilization.\n\n"
                    "Helps answer: 'Is SQL Server the main CPU consumer?'. Compare with OS CPU. "
                    "Sustained high SQL CPU usually correlates with CPU-heavy queries, excessive parallelism, or high compilation.",
                ),
                (
                    "active_sessions",
                    "Active Sessions",
                    "",
                    "Count of active user sessions (non-system).\n\n"
                    "A sudden increase can indicate connection storms, long-running requests, or application pooling issues. "
                    "Use together with Top Queries / Blocking to pinpoint the cause.",
                ),
                (
                    "runnable_queue",
                    "Runnable Queue",
                    "",
                    "CPU scheduler pressure (SOS scheduler contention).\n\n"
                    "Computed as: SUM(max(current_tasks_count - active_workers_count, 0)) across VISIBLE ONLINE schedulers "
                    "from sys.dm_os_schedulers.\n\n"
                    "Non-zero means there are workers ready to run but not getting CPU. Sustained values (e.g., >5) are a strong "
                    "signal of a real CPU bottleneck.",
                ),
            ],
        )

        # 2) MEMORY HEALTH
        add_section(
            "MEMORY HEALTH",
            [
                (
                    "total_memory",
                    "Total Memory",
                    "MB",
                    "SQL Server Total Server Memory (MB).\n\n"
                    "This is the current amount of memory SQL Server has committed for its memory manager "
                    "(perf counter: 'Total Server Memory (KB)').\n\n"
                    "In steady state it usually approaches Target Memory. If it stays far below Target, "
                    "SQL may be under external memory pressure or constrained by configuration (e.g., max server memory).",
                ),
                (
                    "target_memory",
                    "Target Memory",
                    "MB",
                    "SQL Server Target Server Memory (MB).\n\n"
                    "This is how much memory SQL Server wants to use based on current conditions "
                    "(perf counter: 'Target Server Memory (KB)').\n\n"
                    "If Target is low relative to the host, review 'max server memory' and OS memory pressure. "
                    "If Total is close to Target but PLE is low, workload may be churning the buffer pool.",
                ),
                (
                    "ple",
                    "PLE",
                    "sec",
                    "Page Life Expectancy (seconds).\n\n"
                    "Approximate time a data page stays in the buffer pool. Higher is generally better, but the 'right' value "
                    "depends on RAM size and workload.\n\n"
                    "Sharp drops usually indicate buffer churn (large scans, memory grants, or external memory pressure).",
                ),
                (
                    "buffer_cache",
                    "Buffer Hit Ratio",
                    "%",
                    "Buffer Cache Hit Ratio (%).\n\n"
                    "Derived from Buffer Manager performance counters. It represents how often pages are served from memory "
                    "instead of disk.\n\n"
                    "Typically >95% in many OLTP workloads, but trends matter more than a single snapshot. "
                    "Use with PLE and IO latency to understand read pressure.",
                ),
            ],
        )

        # 3) WORKLOAD (Failed Logins intentionally removed)
        add_section(
            "WORKLOAD",
            [
                (
                    "batch_requests",
                    "Batch/sec",
                    "req/s",
                    "Batch Requests/sec (throughput).\n\n"
                    "Computed from the cumulative 'Batch Requests/sec' performance counter using delta/time "
                    "over the current refresh interval.\n\n"
                    "Use this as a high-level workload intensity signal. Sudden spikes often correlate with CPU/IO increases.",
                ),
                (
                    "transactions",
                    "Transactions/sec",
                    "tx/s",
                    "Transactions/sec (throughput).\n\n"
                    "Computed from the cumulative 'Transactions/sec' performance counter using delta/time "
                    "over the current refresh interval.\n\n"
                    "Helpful to compare with Batch/sec to understand how many requests are truly transactional.",
                ),
                (
                    "compilations",
                    "Compilations/sec",
                    "c/s",
                    "SQL Compilations/sec.\n\n"
                    "Computed from the cumulative 'SQL Compilations/sec' counter using delta/time.\n\n"
                    "High compilations relative to Batch/sec can indicate ad-hoc queries, missing parameterization, "
                    "or excessive plan cache churn. This can drive CPU usage without increasing throughput.",
                ),
                (
                    "recompilations",
                    "Recomp/sec",
                    "rc/s",
                    "SQL Re-Compilations/sec.\n\n"
                    "Computed from the cumulative 'SQL Re-Compilations/sec' counter using delta/time.\n\n"
                    "Recompiles can be caused by statistics changes, temp table usage, schema changes, or RECOMPILE hints. "
                    "Consistently high recompiles are worth investigating as they add CPU overhead.",
                ),
            ],
        )

        # 4) IO
        add_section(
            "IO",
            [
                (
                    "io_read_latency",
                    "IO Read Latency",
                    "ms",
                    "Average read latency in milliseconds.\n\n"
                    "Calculated from sys.dm_io_virtual_file_stats as (io_stall_read_ms / num_of_reads) and averaged.\n\n"
                    "Rough guidance: <5ms is excellent, 5-20ms is moderate, >20ms often indicates storage pressure "
                    "(or a workload generating random reads).",
                ),
                (
                    "io_write_latency",
                    "IO Write Latency",
                    "ms",
                    "Average write latency in milliseconds.\n\n"
                    "Calculated from sys.dm_io_virtual_file_stats as (io_stall_write_ms / num_of_writes) and averaged.\n\n"
                    "Sustained high write latency can impact checkpoint, tempdb activity, and overall throughput. "
                    "Correlate with Log Write Latency and wait types like WRITELOG / PAGEIOLATCH_*.",
                ),
                (
                    "log_write_latency",
                    "Log Write Latency",
                    "ms",
                    "Average transaction log write latency in milliseconds.\n\n"
                    "Calculated from sys.dm_io_virtual_file_stats for LOG files only.\n\n"
                    "High values often show up as WRITELOG waits and can severely impact commit latency. "
                    "Check storage, log file placement, and any synchronous replication settings.",
                ),
                (
                    "disk_queue_length",
                    "Disk Queue Length",
                    "",
                    "Pending IO requests (best-effort proxy).\n\n"
                    "Collected as COUNT(*) from sys.dm_io_pending_io_requests.\n\n"
                    "0 is typical. Sustained higher values mean IO is backing up (storage cannot keep up). "
                    "Correlate with IO latency and IO-related waits.",
                ),
            ],
        )

        # 5) TEMPDB
        add_section(
            "TEMPDB",
            [
                (
                    "tempdb_usage",
                    "TempDB Usage",
                    "%",
                    "TempDB data file space usage (%).\n\n"
                    "Computed from tempdb.sys.dm_db_file_space_usage.\n\n"
                    "High usage may indicate heavy temp table usage, sorts/hashes spilling, version store growth, "
                    "or large index operations. Consider tempdb sizing and workload patterns.",
                ),
                (
                    "tempdb_log_used",
                    "TempDB Log Used",
                    "%",
                    "TempDB transaction log used (%).\n\n"
                    "Collected from tempdb.sys.dm_db_log_space_usage (used_log_space_in_percent).\n\n"
                    "If this grows quickly, look for long-running transactions, heavy version store activity, "
                    "or large tempdb writes that keep the log active.",
                ),
                (
                    "pfs_gam_waits",
                    "PFS/GAM Waits",
                    "",
                    "TempDB allocation contention signal (best-effort).\n\n"
                    "Counts current PAGELATCH waits on TempDB allocation bitmap pages (PFS/GAM/SGAM; page_id 1/2/3) "
                    "from sys.dm_os_waiting_tasks.\n\n"
                    "Non-zero values can indicate allocation hot spots. Common mitigations include multiple TempDB data files "
                    "and removing excessive tempdb allocation pressure from the workload.",
                ),
            ],
        )

        # WAIT CATEGORIES panel removed per UI request.
    
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
        if metric_key in self._metric_rows:
            self._metric_rows[metric_key].set_value(value, status)
        elif metric_key in self._metric_cards:
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
            
            # SERVER HEALTH
            self.update_metric(
                "os_cpu",
                str(metrics.cpu_percent),
                "normal" if metrics.cpu_percent < 70 else ("warning" if metrics.cpu_percent < 90 else "bad"),
            )

            sql_cpu = getattr(metrics, "sql_cpu_percent", metrics.cpu_percent)
            self.update_metric(
                "sql_cpu",
                str(sql_cpu),
                "normal" if sql_cpu < 70 else ("warning" if sql_cpu < 90 else "bad"),
            )

            self.update_metric(
                "active_sessions",
                str(metrics.active_sessions),
                "normal"
                if metrics.active_sessions < 50
                else ("warning" if metrics.active_sessions < 100 else "bad"),
            )

            runnable_q = getattr(metrics, "runnable_queue", 0)
            self.update_metric(
                "runnable_queue",
                str(runnable_q),
                "good" if runnable_q < 5 else ("warning" if runnable_q < 20 else "bad"),
            )

            # MEMORY HEALTH
            total_mem = getattr(metrics, "total_server_memory_mb", 0)
            target_mem = getattr(metrics, "target_server_memory_mb", 0)
            total_status = "normal"
            if target_mem > 0 and total_mem > 0:
                ratio = total_mem / target_mem
                total_status = "good" if ratio >= 0.9 else ("warning" if ratio >= 0.75 else "bad")
            self.update_metric("total_memory", str(total_mem), total_status)
            self.update_metric("target_memory", str(target_mem), "normal")

            self.update_metric(
                "ple",
                str(metrics.ple_seconds),
                "good" if metrics.ple_seconds > 300 else ("warning" if metrics.ple_seconds > 60 else "bad"),
            )

            buffer_cache = getattr(metrics, "buffer_cache_hit_ratio", 99)
            self.update_metric(
                "buffer_cache",
                str(buffer_cache),
                "good" if buffer_cache > 95 else ("warning" if buffer_cache > 90 else "bad"),
            )

            # WORKLOAD
            self.update_metric("batch_requests", str(metrics.batch_requests), "normal")
            transactions = getattr(metrics, "transactions_per_sec", 0)
            self.update_metric("transactions", str(transactions), "normal")

            compilations = getattr(metrics, "compilations_per_sec", 0)
            self.update_metric(
                "compilations",
                str(compilations),
                "normal" if compilations < 1000 else ("warning" if compilations < 5000 else "bad"),
            )

            recomp = getattr(metrics, "recompilations_per_sec", 0)
            self.update_metric(
                "recompilations",
                str(recomp),
                "good" if recomp == 0 else ("warning" if recomp < 100 else "bad"),
            )

            # IO
            read_latency = getattr(metrics, "read_latency_ms", metrics.disk_latency_ms)
            self.update_metric(
                "io_read_latency",
                str(int(read_latency)),
                "good" if read_latency < 5 else ("warning" if read_latency < 20 else "bad"),
            )

            write_latency = getattr(metrics, "write_latency_ms", metrics.disk_latency_ms)
            self.update_metric(
                "io_write_latency",
                str(int(write_latency)),
                "good" if write_latency < 5 else ("warning" if write_latency < 20 else "bad"),
            )

            log_latency = getattr(metrics, "log_write_latency_ms", 0)
            self.update_metric(
                "log_write_latency",
                str(int(log_latency)),
                "good" if log_latency < 5 else ("warning" if log_latency < 20 else "bad"),
            )

            disk_q = getattr(metrics, "disk_queue_length", 0)
            self.update_metric(
                "disk_queue_length",
                str(disk_q),
                "good" if disk_q < 2 else ("warning" if disk_q < 10 else "bad"),
            )

            # TEMPDB
            tempdb_usage = getattr(metrics, "tempdb_usage_percent", 0)
            self.update_metric(
                "tempdb_usage",
                str(tempdb_usage),
                "good" if tempdb_usage < 50 else ("warning" if tempdb_usage < 80 else "bad"),
            )

            tempdb_log = getattr(metrics, "tempdb_log_used_percent", getattr(metrics, "tempdb_percent", 0))
            self.update_metric(
                "tempdb_log_used",
                str(tempdb_log),
                "good" if tempdb_log < 50 else ("warning" if tempdb_log < 80 else "bad"),
            )

            pfs_gam = getattr(metrics, "pfs_gam_waits", 0)
            self.update_metric(
                "pfs_gam_waits",
                str(pfs_gam),
                "good" if pfs_gam == 0 else ("warning" if pfs_gam < 10 else "bad"),
            )

            self._has_loaded_once = True

        except Exception as e:
            logger.error(f"Failed to refresh dashboard stats: {e}")
