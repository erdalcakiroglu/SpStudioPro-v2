"""
Wait Statistics View - Modern Enterprise Design
"""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QComboBox,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QInputDialog,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QTabWidget,
    QHeaderView,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QFont
from app.ui.theme import Colors, Theme as ThemeStyles
from app.ui.views.base_view import BaseView
from app.core.logger import get_logger
from app.services.app_event_bus import get_app_event_bus
from app.services.blocking_service import BlockingChainAnalysis
from app.services.wait_stats_service import (
    WaitBaselineComparison,
    WaitComparativeAnalysis,
    WaitAlert,
    WaitAlertThresholds,
    CustomWaitCategoryRule,
    MultiServerWaitSnapshot,
    WaitPlanCorrelation,
    WaitStatsFilter,
    WaitScheduleConfig,
    WaitMonitoringTarget,
    WaitSignature,
    get_wait_stats_service,
    WaitSummary,
    WaitStat,
    WaitTrendPoint,
    WaitStatsMetrics,
)
from app.database.queries.wait_stats_queries import (
    WaitCategory,
    get_category_color,
    resolve_wait_category_text,
)
from app.models.analysis_context import AnalysisContext
from app.ui.workers.wait_stats_refresh_worker import (
    WaitStatsRefreshWorker,
    WaitStatsRefreshPayload,
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

    def __init__(
        self,
        wait: WaitStat,
        impact_score: float = 0.0,
        baseline_delta_pct: float = 0.0,
        trend_series: Optional[List[int]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._wait = wait
        self._impact_score = max(0.0, float(impact_score or 0.0))
        self._baseline_delta_pct = float(baseline_delta_pct or 0.0)
        self._trend_series = list(trend_series or [])
        self._setup_ui()

    def _setup_ui(self):
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(72)
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
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(16)

        # Category indicator
        indicator = QFrame()
        indicator.setFixedSize(4, 40)
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

        details_label = QLabel(self._format_details_text())
        details_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 10px;")
        details_label.setWordWrap(True)
        info_layout.addWidget(details_label)

        sparkline_label = QLabel(f"Trend(7d): {self._build_ascii_sparkline(self._trend_series)}")
        sparkline_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 10px;")
        info_layout.addWidget(sparkline_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Metrics
        metrics = [
            ("Wait Time", self._format_ms(self._wait.wait_time_ms)),
            ("Tasks", f"{self._wait.waiting_tasks:,}"),
            ("Percent", f"{self._wait.wait_percent:.1f}%"),
            ("Max Wait", self._format_ms(self._wait.max_wait_time_ms)),
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

    def _format_details_text(self) -> str:
        total_sr = int(self._wait.signal_wait_ms or 0) + int(self._wait.resource_wait_ms or 0)
        signal_pct = 0.0
        if total_sr > 0:
            signal_pct = (int(self._wait.signal_wait_ms or 0) * 100.0) / float(total_sr)
        resource_pct = max(0.0, 100.0 - signal_pct) if total_sr > 0 else 0.0
        baseline_txt = f"{self._baseline_delta_pct:+.1f}%"
        return (
            f"Impact={self._impact_score:,.1f} | "
            f"Signal/Resource={signal_pct:.1f}%/{resource_pct:.1f}% | "
            f"Baseline={baseline_txt} | "
            f"Action={self._recommended_action()}"
        )

    @staticmethod
    def _build_ascii_sparkline(series: List[int]) -> str:
        values = [max(0, int(v or 0)) for v in list(series or [])]
        if len(values) < 2:
            return "[n/a]"
        if len(values) > 8:
            values = values[-8:]
        max_val = max(values) or 1
        bar_chars = "._-:=+*#"
        points: List[str] = []
        for value in values:
            ratio = float(value) / float(max_val)
            level = int(round(ratio * 8))
            if level <= 0:
                points.append(".")
            else:
                points.append(bar_chars[min(7, level - 1)])
        trend = "up" if values[-1] > values[0] else ("down" if values[-1] < values[0] else "flat")
        return f"[{''.join(points)}|{trend}]"

    def _recommended_action(self) -> str:
        wait_name = str(self._wait.wait_type or "").upper()
        if wait_name.startswith(("PAGEIOLATCH", "WRITELOG", "IO_COMPLETION", "BACKUP", "ASYNC_IO_COMPLETION")):
            return "Check disk latency"
        if wait_name.startswith(("LCK_",)):
            return "Inspect blockers"
        if wait_name.startswith(("CXPACKET", "CXCONSUMER", "CXSYNC")):
            return "Review MAXDOP"
        if wait_name.startswith(("PAGELATCH", "LATCH_")):
            return "Check hot pages/TempDB"
        if wait_name.startswith(("RESOURCE_SEMAPHORE", "CMEMTHREAD")):
            return "Review memory grants"
        return "Correlate with query plan"


class WaitStatsAutomationWorker(QThread):
    """Background worker for scheduled snapshot/report generation."""

    completed = pyqtSignal(int, bool)  # reports_generated, snapshot_written
    failed = pyqtSignal(str)

    def __init__(
        self,
        service,
        payload: WaitStatsRefreshPayload,
        schedule_config: WaitScheduleConfig,
        parent=None,
    ):
        super().__init__(parent)
        self._service = service
        self._payload = payload
        self._schedule_config = schedule_config

    def run(self) -> None:
        try:
            if self.isInterruptionRequested():
                return
            payload = self._payload
            export_payload = self._service.build_export_payload(
                summary=payload.summary,
                waits_to_render=payload.waits_to_render,
                signatures=payload.signatures,
                baseline=payload.baseline_comparison,
                trend_points=payload.trend_points,
                trend_days=payload.trend_days,
                wait_chain=payload.blocking_analysis,
                alerts=payload.alerts,
                thresholds=payload.thresholds,
                comparative=payload.comparative_analysis,
                custom_category_breakdown=payload.custom_category_breakdown,
                custom_category_rules=payload.custom_category_rules,
                multi_server=payload.multi_server_snapshots,
                plan_correlation=payload.plan_correlation,
                filters=payload.filters,
            )
            if self.isInterruptionRequested():
                return
            wrote_snapshot = self._service.append_scheduled_snapshot(payload.summary)
            if self.isInterruptionRequested():
                return
            reports = self._service.write_automated_reports(export_payload, config=self._schedule_config)
            self.completed.emit(len(reports), bool(wrote_snapshot))
        except Exception as ex:
            self.failed.emit(str(ex))


class WaitStatsView(BaseView):
    """Wait Statistics view with modern enterprise design"""

    uses_app_event_bus_context = True
    MAX_BLOCKING_TREE_NODES = 600
    CATEGORY_ORDER = [
        WaitCategory.CPU,
        WaitCategory.IO,
        WaitCategory.LOCK,
        WaitCategory.LATCH,
        WaitCategory.MEMORY,
        WaitCategory.NETWORK,
        WaitCategory.BUFFER,
        WaitCategory.OTHER,
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = get_wait_stats_service()
        self._blocking_service = self._service.get_blocking_service()
        self._summary_health_label: Optional[QLabel] = None
        self._summary_value_labels: Dict[str, QLabel] = {}
        self._category_value_labels: Dict[WaitCategory, QLabel] = {}
        self._category_percent_labels: Dict[WaitCategory, QLabel] = {}
        self._category_progress_bars: Dict[WaitCategory, QProgressBar] = {}
        self._action_plan_label: Optional[QLabel] = None
        self._alerts_block: Optional[QFrame] = None
        self._schedule_status_badge: Optional[QLabel] = None
        self._monitor_status_badge: Optional[QLabel] = None
        self._custom_status_label: Optional[QLabel] = None
        self._multi_server_status_label: Optional[QLabel] = None
        self._multi_server_table: Optional[QTreeWidget] = None
        self._status_card: Optional[QFrame] = None
        self._analysis_context: Optional[AnalysisContext] = None
        self._refresh_worker: Optional[WaitStatsRefreshWorker] = None
        self._last_metrics: Optional[WaitStatsMetrics] = None
        self._last_payload: Optional[WaitStatsRefreshPayload] = None
        self._trend_points_cache: List[WaitTrendPoint] = []
        self._trend_source_cache: str = "none"
        self._trend_days_cache: int = 7
        self._schedule_worker: Optional[WaitStatsAutomationWorker] = None
        self._render_token: int = 0
        self._trend_days: int = 7
        self._alert_thresholds: WaitAlertThresholds = self._service.load_alert_thresholds()
        self._schedule_config: WaitScheduleConfig = self._service.load_schedule_config()
        self._last_schedule_run: Optional[datetime] = None
        self._monitor_timer = QTimer(self)
        self._monitor_timer.setInterval(5000)
        self._monitor_timer.timeout.connect(self._on_monitor_tick)
        get_app_event_bus().signals.query_analyzed.connect(self._on_query_analyzed_event)
    
    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")

        card_style = f"""
            QFrame#Card {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """
        section_title_style = (
            f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; "
            f"font-weight: 700; background: transparent;"
        )
        section_subtitle_style = (
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; background: transparent;"
        )
        text_box_style = f"""
            QTextEdit {{
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                background: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                padding: 8px;
                font-size: 11px;
            }}
        """
        insight_block_style = f"""
            QFrame#InsightBlock {{
                background: {Colors.BACKGROUND};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
        """
        insight_block_title_style = (
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; "
            f"font-weight: 700; background: transparent;"
        )
        primary_button_style = ThemeStyles.btn_primary("md")
        action_button_style = ThemeStyles.btn_ghost("md")
        filter_spin_style = f"""
            QSpinBox {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 4px 8px;
                min-height: 22px;
                selection-background-color: {Colors.PRIMARY};
                selection-color: #ffffff;
            }}
            QSpinBox:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QSpinBox:focus {{
                border-color: {Colors.PRIMARY};
            }}
            QSpinBox:disabled {{
                background-color: {Colors.BORDER_LIGHT};
                color: {Colors.TEXT_MUTED};
            }}
            QSpinBox::up-button,
            QSpinBox::down-button {{
                width: 14px;
                border: none;
                background: transparent;
            }}
        """

        def _create_insight_block(title_text: str):
            block = QFrame()
            block.setObjectName("InsightBlock")
            block.setStyleSheet(insight_block_style)
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(10, 8, 10, 8)
            block_layout.setSpacing(6)
            block_title = QLabel(title_text)
            block_title.setStyleSheet(insight_block_title_style)
            block_layout.addWidget(block_title)
            return block, block_layout

        main_widget = QWidget()
        main_widget.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(12)

        header_card = QFrame()
        header_card.setObjectName("Card")
        header_card.setStyleSheet(card_style)
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(14, 14, 14, 14)
        header_layout.setSpacing(12)

        header_left = QVBoxLayout()
        header_left.setSpacing(4)

        self._context_label = QLabel("")
        self._context_label.setVisible(False)
        self._context_label.setStyleSheet(
            f"color: {Colors.PRIMARY}; font-size: 12px; font-weight: 600; background: transparent;"
        )
        header_left.addWidget(self._context_label)

        header_layout.addLayout(header_left, stretch=1)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setStyleSheet(primary_button_style)
        self._refresh_btn.clicked.connect(self.refresh)
        actions_layout.addWidget(self._refresh_btn)

        self._set_baseline_btn = QPushButton("Set Baseline")
        self._set_baseline_btn.setStyleSheet(action_button_style)
        self._set_baseline_btn.clicked.connect(self._on_set_baseline_clicked)
        actions_layout.addWidget(self._set_baseline_btn)

        self._export_btn = QPushButton("Export")
        self._export_btn.setStyleSheet(action_button_style)
        self._export_btn.clicked.connect(self._on_export_clicked)
        actions_layout.addWidget(self._export_btn)

        header_layout.addLayout(actions_layout)
        main_layout.addWidget(header_card)

        filter_card = QFrame()
        filter_card.setObjectName("Card")
        filter_card.setStyleSheet(card_style)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(14, 10, 14, 10)
        filter_layout.setSpacing(10)

        trend_lbl = QLabel("Trend Window:")
        trend_lbl.setStyleSheet(section_subtitle_style)
        filter_layout.addWidget(trend_lbl)

        self._trend_combo = QComboBox()
        self._trend_combo.addItem("7 Days", 7)
        self._trend_combo.addItem("30 Days", 30)
        self._trend_combo.addItem("90 Days", 90)
        self._trend_combo.currentIndexChanged.connect(self._on_trend_window_changed)
        self._trend_combo.setMaximumWidth(120)
        filter_layout.addWidget(self._trend_combo)
        ThemeStyles.style_combobox_instance(self._trend_combo)
        filter_layout.addSpacing(6)

        db_lbl = QLabel("DB Filter:")
        db_lbl.setStyleSheet(section_subtitle_style)
        filter_layout.addWidget(db_lbl)

        self._db_filter_combo = QComboBox()
        self._db_filter_combo.setEditable(True)
        self._db_filter_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._db_filter_combo.setMaximumWidth(170)
        self._db_filter_combo.addItem("All Databases", "")
        filter_layout.addWidget(self._db_filter_combo)
        ThemeStyles.style_combobox_instance(self._db_filter_combo)
        filter_layout.addSpacing(6)

        app_lbl = QLabel("App Filter:")
        app_lbl.setStyleSheet(section_subtitle_style)
        filter_layout.addWidget(app_lbl)

        self._app_filter_combo = QComboBox()
        self._app_filter_combo.setEditable(True)
        self._app_filter_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._app_filter_combo.setMaximumWidth(180)
        self._app_filter_combo.addItem("All Applications", "")
        filter_layout.addWidget(self._app_filter_combo)
        ThemeStyles.style_combobox_instance(self._app_filter_combo)
        filter_layout.addSpacing(6)

        min_lbl = QLabel("Min Wait:")
        min_lbl.setStyleSheet(section_subtitle_style)
        filter_layout.addWidget(min_lbl)

        self._min_wait_filter_spin = QSpinBox()
        self._min_wait_filter_spin.setRange(0, 60_000_000)
        self._min_wait_filter_spin.setSingleStep(1000)
        self._min_wait_filter_spin.setValue(100)
        self._min_wait_filter_spin.setSuffix(" ms")
        self._min_wait_filter_spin.setMinimumWidth(124)
        self._min_wait_filter_spin.setMaximumWidth(132)
        self._min_wait_filter_spin.setStyleSheet(filter_spin_style)
        filter_layout.addWidget(self._min_wait_filter_spin)
        filter_layout.addSpacing(4)

        self._apply_filter_btn = QPushButton("Apply Filter")
        self._apply_filter_btn.setStyleSheet(action_button_style)
        self._apply_filter_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(self._apply_filter_btn)
        filter_layout.addStretch(1)

        # Updated-in badge: keep it inside Trend Window panel and right-aligned.
        self._status_label = QLabel("Ready.")
        self._status_label.setStyleSheet(
            f"color: {Colors.TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        filter_layout.addWidget(self._status_label, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        main_layout.addWidget(filter_card)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedSize(0, 0)
        self._progress_bar.setVisible(False)

        insight_card = QFrame()
        insight_card.setObjectName("Card")
        insight_card.setStyleSheet(card_style)
        insight_layout = QVBoxLayout(insight_card)
        insight_layout.setContentsMargins(12, 10, 12, 10)
        insight_layout.setSpacing(8)

        insight_title = QLabel("Insights")
        insight_title.setStyleSheet(section_title_style)
        insight_layout.addWidget(insight_title)

        alerts_block, alerts_block_layout = _create_insight_block("Alerts")
        self._alerts_block = alerts_block
        self._alert_label = QLabel("No active wait alerts.")
        self._alert_label.setWordWrap(True)
        self._alert_label.setStyleSheet(
            f"color: {Colors.SUCCESS}; font-size: 12px; background: transparent;"
        )
        alerts_block_layout.addWidget(self._alert_label)
        insight_layout.addWidget(alerts_block)

        analysis_row = QHBoxLayout()
        analysis_row.setContentsMargins(0, 0, 0, 0)
        analysis_row.setSpacing(8)

        signature_block, signature_block_layout = _create_insight_block("Signature")
        self._signature_label = QLabel("Signature analysis will appear after refresh.")
        self._signature_label.setWordWrap(True)
        self._signature_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;"
        )
        signature_block_layout.addWidget(self._signature_label)

        comparison_block, comparison_block_layout = _create_insight_block("Before / After")
        self._comparison_label = QLabel("Capture both BEFORE and AFTER snapshots to compare change impact.")
        self._comparison_label.setWordWrap(True)
        self._comparison_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;"
        )
        comparison_block_layout.addWidget(self._comparison_label)

        analysis_row.addWidget(signature_block, 1)
        analysis_row.addWidget(comparison_block, 1)
        insight_layout.addLayout(analysis_row)

        actions_block, actions_block_layout = _create_insight_block("Actions")
        insight_action_button_style = f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
                min-height: 21px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_LIGHT};
                color: {Colors.TEXT_PRIMARY};
                border-color: {Colors.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BORDER};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER_LIGHT};
                color: {Colors.TEXT_MUTED};
                border-color: {Colors.BORDER};
            }}
        """
        compare_row = QWidget()
        compare_row.setStyleSheet("background: transparent;")
        compare_row.setMinimumHeight(34)
        compare_layout = QHBoxLayout(compare_row)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        compare_layout.setSpacing(6)

        self._save_before_btn = QPushButton("Save Before")
        self._save_before_btn.setStyleSheet(insight_action_button_style)
        self._save_before_btn.setMinimumWidth(82)
        self._save_before_btn.setMinimumHeight(22)
        self._save_before_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._save_before_btn.setEnabled(True)
        self._save_before_btn.clicked.connect(self._on_save_before_clicked)
        compare_layout.addWidget(self._save_before_btn, 1)

        self._save_after_btn = QPushButton("Save After")
        self._save_after_btn.setStyleSheet(insight_action_button_style)
        self._save_after_btn.setMinimumWidth(82)
        self._save_after_btn.setMinimumHeight(22)
        self._save_after_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._save_after_btn.setEnabled(True)
        self._save_after_btn.clicked.connect(self._on_save_after_clicked)
        compare_layout.addWidget(self._save_after_btn, 1)

        self._compare_btn = QPushButton("Compare")
        self._compare_btn.setStyleSheet(insight_action_button_style)
        self._compare_btn.setMinimumWidth(76)
        self._compare_btn.setMinimumHeight(22)
        self._compare_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._compare_btn.setEnabled(True)
        self._compare_btn.clicked.connect(self._on_compare_clicked)
        compare_layout.addWidget(self._compare_btn, 1)

        self._custom_add_btn = QPushButton("Custom Category")
        self._custom_add_btn.setStyleSheet(insight_action_button_style)
        self._custom_add_btn.setMinimumWidth(108)
        self._custom_add_btn.setMinimumHeight(22)
        self._custom_add_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._custom_add_btn.setEnabled(True)
        self._custom_add_btn.clicked.connect(self._on_add_custom_rule_clicked)
        compare_layout.addWidget(self._custom_add_btn, 1)

        self._custom_remove_btn = QPushButton("Remove Custom")
        self._custom_remove_btn.setStyleSheet(insight_action_button_style)
        self._custom_remove_btn.setMinimumWidth(100)
        self._custom_remove_btn.setMinimumHeight(22)
        self._custom_remove_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._custom_remove_btn.setEnabled(True)
        self._custom_remove_btn.clicked.connect(self._on_remove_custom_rule_clicked)
        compare_layout.addWidget(self._custom_remove_btn, 1)
        actions_block_layout.addWidget(compare_row)
        insight_layout.addWidget(actions_block)

        ops_row = QHBoxLayout()
        ops_row.setContentsMargins(0, 0, 0, 0)
        ops_row.setSpacing(8)

        plan_block, plan_block_layout = _create_insight_block("Wait / Plan")
        self._plan_correlation_label = QLabel("Wait/Plan correlation not available.")
        self._plan_correlation_label.setWordWrap(True)
        self._plan_correlation_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;"
        )
        plan_block_layout.addWidget(self._plan_correlation_label)

        monitoring_block, monitoring_block_layout = _create_insight_block("Monitoring")
        self._monitoring_status_label = QLabel("Monitoring targets: none configured.")
        self._monitoring_status_label.setWordWrap(True)
        self._monitoring_status_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;"
        )
        monitoring_block_layout.addWidget(self._monitoring_status_label)

        ops_row.addWidget(plan_block, 1)
        ops_row.addWidget(monitoring_block, 1)
        insight_layout.addLayout(ops_row)

        action_block, action_block_layout = _create_insight_block("Actionable Intelligence")
        self._action_plan_label = QLabel("Waiting for diagnostics...")
        self._action_plan_label.setWordWrap(True)
        self._action_plan_label.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; background: transparent;"
        )
        action_block_layout.addWidget(self._action_plan_label)
        insight_layout.addWidget(action_block)

        summary_card = QFrame()
        summary_card.setObjectName("Card")
        summary_card.setStyleSheet(card_style)
        summary_card_layout = QVBoxLayout(summary_card)
        summary_card_layout.setContentsMargins(12, 10, 12, 10)
        summary_card_layout.setSpacing(8)
        summary_card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        summary_title = QLabel("Summary")
        summary_title.setStyleSheet(section_title_style)
        summary_card_layout.addWidget(summary_title)

        self._summary_health_label = QLabel("Health: Waiting for refresh...")
        self._summary_health_label.setWordWrap(True)
        self._summary_health_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 700; background: transparent;"
        )
        summary_card_layout.addWidget(self._summary_health_label)

        summary_values = QWidget()
        summary_values.setStyleSheet("background: transparent;")
        summary_values_layout = QGridLayout(summary_values)
        summary_values_layout.setContentsMargins(0, 0, 0, 0)
        summary_values_layout.setHorizontalSpacing(6)
        summary_values_layout.setVerticalSpacing(6)
        summary_values_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        summary_items = [
            ("total_wait", "Total Wait"),
            ("signal_wait", "Signal Wait"),
            ("resource_wait", "Resource Wait"),
            ("current_waits", "Current Waiters"),
        ]
        for row_idx, (key, label) in enumerate(summary_items):
            name_label = QLabel(label)
            name_label.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600; background: transparent;"
            )
            name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            name_label.setMinimumWidth(98)
            colon_label = QLabel(":")
            colon_label.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600; background: transparent;"
            )
            colon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label = QLabel("--")
            value_label.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; font-weight: 700; background: transparent;"
            )
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            summary_values_layout.addWidget(name_label, row_idx, 0)
            summary_values_layout.addWidget(colon_label, row_idx, 1)
            summary_values_layout.addWidget(value_label, row_idx, 2)
            self._summary_value_labels[key] = value_label
        summary_values_layout.setColumnStretch(2, 1)
        summary_card_layout.addWidget(summary_values)

        category_card = QFrame()
        category_card.setObjectName("Card")
        category_card.setStyleSheet(card_style)
        category_card_layout = QVBoxLayout(category_card)
        category_card_layout.setContentsMargins(12, 10, 12, 10)
        category_card_layout.setSpacing(8)
        category_card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        category_title = QLabel("Wait Categories")
        category_title.setStyleSheet(section_title_style)
        category_card_layout.addWidget(category_title)

        category_values = QWidget()
        category_values.setStyleSheet("background: transparent;")
        category_values_layout = QGridLayout(category_values)
        category_values_layout.setContentsMargins(0, 0, 0, 0)
        category_values_layout.setHorizontalSpacing(6)
        category_values_layout.setVerticalSpacing(6)
        category_values_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        for row_idx, category in enumerate(self.CATEGORY_ORDER):
            name_label = QLabel(category.value)
            name_label.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600; background: transparent;"
            )
            name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            name_label.setMinimumWidth(74)
            colon_label = QLabel(":")
            colon_label.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600; background: transparent;"
            )
            colon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label = QLabel("-- ms")
            value_label.setStyleSheet(
                f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; font-weight: 700; background: transparent;"
            )
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(10)
            category_color = get_category_color(category)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 1px solid {Colors.BORDER};
                    border-radius: 5px;
                    background: {Colors.BACKGROUND};
                }}
                QProgressBar::chunk {{
                    background: {category_color};
                    border-radius: 4px;
                }}
            """)
            pct_label = QLabel("0.0%")
            pct_label.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 10px; font-weight: 700; background: transparent;"
            )
            pct_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            category_values_layout.addWidget(name_label, row_idx, 0)
            category_values_layout.addWidget(colon_label, row_idx, 1)
            category_values_layout.addWidget(value_label, row_idx, 2)
            category_values_layout.addWidget(bar, row_idx, 3)
            category_values_layout.addWidget(pct_label, row_idx, 4)
            self._category_value_labels[category] = value_label
            self._category_progress_bars[category] = bar
            self._category_percent_labels[category] = pct_label
        category_values_layout.setColumnStretch(2, 1)
        category_values_layout.setColumnStretch(3, 2)
        category_card_layout.addWidget(category_values)

        insight_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        summary_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        category_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        right_top_row = QWidget()
        right_top_row.setStyleSheet("background: transparent;")
        right_top_row_layout = QHBoxLayout(right_top_row)
        right_top_row_layout.setContentsMargins(0, 0, 0, 0)
        right_top_row_layout.setSpacing(10)
        right_top_row_layout.addWidget(summary_card, 1)
        right_top_row_layout.addWidget(category_card, 1)

        right_panel = QWidget()
        right_panel.setStyleSheet("background: transparent;")
        right_panel_layout = QVBoxLayout(right_panel)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)
        right_panel_layout.setSpacing(10)
        right_panel_layout.addWidget(right_top_row)
        right_panel_layout.addWidget(insight_card, 1)

        self._content_tabs = QTabWidget()
        self._content_tabs.setStyleSheet(ThemeStyles.tab_widget_style())

        waits_tab = QWidget()
        waits_tab.setStyleSheet("background: transparent;")
        waits_tab_layout = QVBoxLayout(waits_tab)
        waits_tab_layout.setContentsMargins(10, 10, 10, 10)
        waits_tab_layout.setSpacing(8)

        waits_title = QLabel("Top Wait Types")
        waits_title.setStyleSheet(section_title_style)
        waits_tab_layout.addWidget(waits_title)

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

        placeholder = QLabel("Loading wait statistics...")
        placeholder.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 32px;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._waits_layout.addWidget(placeholder)
        self._waits_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._waits_scroll = QScrollArea()
        self._waits_scroll.setWidgetResizable(True)
        self._waits_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._waits_scroll.setStyleSheet("background: transparent;")
        self._waits_scroll.setWidget(self._waits_container)
        waits_tab_layout.addWidget(self._waits_scroll, stretch=1)

        self._content_tabs.addTab(waits_tab, "Top Waits")

        trend_tab = QWidget()
        trend_tab.setStyleSheet("background: transparent;")
        trend_tab_layout = QVBoxLayout(trend_tab)
        trend_tab_layout.setContentsMargins(10, 10, 10, 10)
        trend_tab_layout.setSpacing(8)

        trend_header = QWidget()
        trend_header.setStyleSheet("background: transparent;")
        trend_header_layout = QHBoxLayout(trend_header)
        trend_header_layout.setContentsMargins(0, 0, 0, 0)
        trend_header_layout.setSpacing(8)

        trend_title = QLabel("Trend & Blocking")
        trend_title.setStyleSheet(section_title_style)
        trend_header_layout.addWidget(trend_title)
        trend_header_layout.addStretch()

        trend_mode_label = QLabel("Display:")
        trend_mode_label.setStyleSheet(section_subtitle_style)
        trend_header_layout.addWidget(trend_mode_label)

        self._trend_display_combo = QComboBox()
        self._trend_display_combo.setMaximumWidth(190)
        self._trend_display_combo.addItem("Daily Summary", "summary")
        self._trend_display_combo.addItem("Dominant Category", "dominant")
        self._trend_display_combo.addItem("Category Breakdown", "breakdown")
        ThemeStyles.style_combobox_instance(self._trend_display_combo)
        self._trend_display_combo.currentIndexChanged.connect(self._on_trend_display_mode_changed)
        trend_header_layout.addWidget(self._trend_display_combo)
        trend_tab_layout.addWidget(trend_header)

        self._trend_text = QTextEdit()
        self._trend_text.setReadOnly(True)
        self._trend_text.setPlaceholderText("Historical trend (7/30/90 day) will be shown here...")
        self._trend_text.setMinimumHeight(120)
        self._trend_text.setStyleSheet(text_box_style)
        trend_tab_layout.addWidget(self._trend_text)

        self._blocking_tree = QTreeWidget()
        self._blocking_tree.setHeaderLabels(["Session", "Wait", "Wait ms", "Database", "Login"])
        self._blocking_tree.setAlternatingRowColors(True)
        self._blocking_tree.setRootIsDecorated(True)
        self._blocking_tree.setMinimumHeight(180)
        self._blocking_tree.setStyleSheet(f"""
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
        trend_tab_layout.addWidget(self._blocking_tree, stretch=1)

        self._content_tabs.addTab(trend_tab, "Trend & Blocking")

        automation_tab = QWidget()
        automation_tab.setStyleSheet("background: transparent;")
        automation_layout = QVBoxLayout(automation_tab)
        automation_layout.setContentsMargins(14, 14, 14, 14)
        automation_layout.setSpacing(12)

        automation_panel = QFrame()
        automation_panel.setObjectName("AutomationPanel")
        automation_panel.setStyleSheet(f"""
            QFrame#AutomationPanel {{
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 10px;
            }}
            QFrame#AutomationCard {{
                background: #ffffff;
                border: 1px solid #e1e4e8;
                border-radius: 8px;
            }}
            QFrame#AutomationCard:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QFrame#AutomationPanel QCheckBox {{
                color: #334155;
                font-size: 11px;
                font-weight: 600;
                spacing: 6px;
                background: transparent;
            }}
            QFrame#AutomationPanel QCheckBox:hover {{
                color: #1f2937;
            }}
            QFrame#AutomationPanel QCheckBox:disabled {{
                color: #94a3b8;
            }}
            QFrame#AutomationPanel QSpinBox,
            QFrame#AutomationPanel QDoubleSpinBox {{
                background: #ffffff;
                color: #1f2937;
                border: 1px solid #cfd6dd;
                border-radius: 6px;
                padding: 4px 6px;
                min-height: 22px;
                selection-background-color: {Colors.PRIMARY};
                selection-color: #ffffff;
            }}
            QFrame#AutomationPanel QSpinBox:hover,
            QFrame#AutomationPanel QDoubleSpinBox:hover {{
                border-color: {Colors.PRIMARY};
            }}
            QFrame#AutomationPanel QSpinBox:focus,
            QFrame#AutomationPanel QDoubleSpinBox:focus {{
                border-color: {Colors.PRIMARY};
            }}
            QFrame#AutomationPanel QSpinBox:disabled,
            QFrame#AutomationPanel QDoubleSpinBox:disabled {{
                background: #f3f4f6;
                color: #64748b;
                border-color: #d9dee5;
            }}
            QFrame#AutomationPanel QSpinBox::up-button,
            QFrame#AutomationPanel QSpinBox::down-button,
            QFrame#AutomationPanel QDoubleSpinBox::up-button,
            QFrame#AutomationPanel QDoubleSpinBox::down-button {{
                width: 16px;
                border: none;
                background: transparent;
            }}
            QFrame#AutomationPanel QTextEdit {{
                background: #ffffff;
                color: #2c3e50;
                border: 1px solid #dfe4ea;
                border-radius: 6px;
                selection-background-color: {Colors.PRIMARY};
                selection-color: #ffffff;
            }}
        """)
        automation_panel_layout = QVBoxLayout(automation_panel)
        automation_panel_layout.setContentsMargins(18, 16, 18, 16)
        automation_panel_layout.setSpacing(14)

        schedule_title = QLabel("Automation")
        schedule_title.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: #212529; "
            f"background: transparent; padding-bottom: 6px; border-bottom: 2px solid {Colors.PRIMARY};"
        )
        automation_panel_layout.addWidget(schedule_title)

        automation_button_style = f"""
            QPushButton {{
                background: #ffffff;
                color: #2c3e50;
                border: 1px solid #cfd6dd;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 700;
                min-height: 30px;
            }}
            QPushButton:hover {{
                background: #eaf7fa;
                border-color: {Colors.PRIMARY};
                color: #1f2937;
            }}
            QPushButton:pressed {{
                background: #dff1f6;
            }}
            QPushButton:disabled {{
                background: #f3f4f6;
                color: {Colors.TEXT_MUTED};
                border-color: {Colors.BORDER};
            }}
        """

        status_badge_base = (
            "padding: 2px 8px; border-radius: 10px; font-size: 10px; "
            "font-weight: 700; color: #ffffff;"
        )
        card_title_style = "color: #2c3e50; font-size: 15px; font-weight: 700; background: transparent;"
        card_hint_style = "color: #5a6c7d; font-size: 12px; background: transparent;"

        top_cards_row = QHBoxLayout()
        top_cards_row.setContentsMargins(0, 0, 0, 0)
        top_cards_row.setSpacing(12)

        # Card 1: Scheduled Snapshot
        schedule_card = QFrame()
        schedule_card.setObjectName("AutomationCard")
        schedule_card_layout = QVBoxLayout(schedule_card)
        schedule_card_layout.setContentsMargins(14, 12, 14, 12)
        schedule_card_layout.setSpacing(10)

        schedule_header = QHBoxLayout()
        schedule_header.setContentsMargins(0, 0, 0, 0)
        schedule_header.setSpacing(8)
        schedule_header_lbl = QLabel("Scheduled Snapshot")
        schedule_header_lbl.setStyleSheet(card_title_style)
        schedule_header.addWidget(schedule_header_lbl)
        schedule_header.addStretch()
        self._schedule_status_badge = QLabel("Inactive")
        self._schedule_status_badge.setStyleSheet(status_badge_base + "background: #94a3b8;")
        schedule_header.addWidget(self._schedule_status_badge)
        schedule_card_layout.addLayout(schedule_header)

        schedule_hint = QLabel("Automatic wait snapshot + report generation")
        schedule_hint.setStyleSheet(card_hint_style)
        schedule_card_layout.addWidget(schedule_hint)

        schedule_cfg = QFrame()
        schedule_cfg.setStyleSheet("background: #f8f9fa; border: 1px solid #e7eaee; border-radius: 6px;")
        schedule_cfg_layout = QVBoxLayout(schedule_cfg)
        schedule_cfg_layout.setContentsMargins(10, 8, 10, 8)
        schedule_cfg_layout.setSpacing(8)

        self._schedule_enabled_chk = QCheckBox("Scheduled Snapshot Enabled")
        self._schedule_enabled_chk.setChecked(bool(self._schedule_config.enabled))
        self._schedule_enabled_chk.stateChanged.connect(self._on_schedule_settings_changed)
        schedule_cfg_layout.addWidget(self._schedule_enabled_chk)

        schedule_interval_row = QHBoxLayout()
        schedule_interval_row.setContentsMargins(0, 0, 0, 0)
        schedule_interval_row.setSpacing(8)
        every_label = QLabel("Every")
        every_label.setStyleSheet(section_subtitle_style)
        schedule_interval_row.addWidget(every_label)

        self._schedule_interval_spin = QSpinBox()
        self._schedule_interval_spin.setRange(1, 720)
        self._schedule_interval_spin.setValue(int(self._schedule_config.interval_minutes or 15))
        self._schedule_interval_spin.setSuffix(" min")
        self._schedule_interval_spin.setMaximumWidth(95)
        self._schedule_interval_spin.valueChanged.connect(self._on_schedule_settings_changed)
        schedule_interval_row.addWidget(self._schedule_interval_spin)
        schedule_interval_row.addStretch()
        schedule_cfg_layout.addLayout(schedule_interval_row)

        self._save_schedule_btn = QPushButton("Save Schedule")
        self._save_schedule_btn.setStyleSheet(automation_button_style)
        self._save_schedule_btn.clicked.connect(self._on_save_schedule_clicked)
        schedule_cfg_layout.addWidget(self._save_schedule_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        schedule_card_layout.addWidget(schedule_cfg)

        top_cards_row.addWidget(schedule_card, 1)

        # Card 2: Alert Configuration
        alert_card = QFrame()
        alert_card.setObjectName("AutomationCard")
        alert_card_layout = QVBoxLayout(alert_card)
        alert_card_layout.setContentsMargins(14, 12, 14, 12)
        alert_card_layout.setSpacing(10)

        alert_header = QHBoxLayout()
        alert_header.setContentsMargins(0, 0, 0, 0)
        alert_header.setSpacing(8)
        alert_header_lbl = QLabel("5s Alert Monitor")
        alert_header_lbl.setStyleSheet(card_title_style)
        alert_header.addWidget(alert_header_lbl)
        alert_header.addStretch()
        self._monitor_status_badge = QLabel("Active")
        self._monitor_status_badge.setStyleSheet(status_badge_base + "background: #10b981;")
        alert_header.addWidget(self._monitor_status_badge)
        alert_card_layout.addLayout(alert_header)

        alert_hint = QLabel("Real-time threshold based monitoring")
        alert_hint.setStyleSheet(card_hint_style)
        alert_card_layout.addWidget(alert_hint)

        monitor_cfg = QFrame()
        monitor_cfg.setStyleSheet("background: #f8f9fa; border: 1px solid #e7eaee; border-radius: 6px;")
        monitor_cfg_layout = QVBoxLayout(monitor_cfg)
        monitor_cfg_layout.setContentsMargins(10, 8, 10, 8)
        monitor_cfg_layout.setSpacing(8)

        self._monitor_enabled_chk = QCheckBox("Enable 5s Monitor")
        self._monitor_enabled_chk.setChecked(True)
        self._monitor_enabled_chk.stateChanged.connect(self._on_monitor_toggle_changed)
        monitor_cfg_layout.addWidget(self._monitor_enabled_chk)

        monitor_threshold_grid = QGridLayout()
        monitor_threshold_grid.setContentsMargins(0, 0, 0, 0)
        monitor_threshold_grid.setHorizontalSpacing(8)
        monitor_threshold_grid.setVerticalSpacing(8)

        total_wait_lbl = QLabel("Total Wait >=")
        total_wait_lbl.setStyleSheet(section_subtitle_style)
        monitor_threshold_grid.addWidget(total_wait_lbl, 0, 0)

        self._th_total_wait_spin = QSpinBox()
        self._th_total_wait_spin.setRange(1_000, 2_000_000_000)
        self._th_total_wait_spin.setSingleStep(100_000)
        self._th_total_wait_spin.setValue(int(self._alert_thresholds.total_wait_time_ms))
        self._th_total_wait_spin.setSuffix(" ms")
        self._th_total_wait_spin.setMaximumWidth(120)
        monitor_threshold_grid.addWidget(self._th_total_wait_spin, 0, 1)

        lock_lbl = QLabel("Lock >=")
        lock_lbl.setStyleSheet(section_subtitle_style)
        monitor_threshold_grid.addWidget(lock_lbl, 1, 0)

        self._th_lock_wait_spin = QDoubleSpinBox()
        self._th_lock_wait_spin.setRange(0.0, 100.0)
        self._th_lock_wait_spin.setSingleStep(0.5)
        self._th_lock_wait_spin.setDecimals(1)
        self._th_lock_wait_spin.setValue(float(self._alert_thresholds.lock_wait_percent))
        self._th_lock_wait_spin.setSuffix(" %")
        self._th_lock_wait_spin.setMaximumWidth(95)
        monitor_threshold_grid.addWidget(self._th_lock_wait_spin, 1, 1)

        blocked_lbl = QLabel("Blocked >=")
        blocked_lbl.setStyleSheet(section_subtitle_style)
        monitor_threshold_grid.addWidget(blocked_lbl, 2, 0)

        self._th_blocked_spin = QSpinBox()
        self._th_blocked_spin.setRange(1, 10000)
        self._th_blocked_spin.setValue(int(self._alert_thresholds.blocked_sessions))
        self._th_blocked_spin.setMaximumWidth(90)
        monitor_threshold_grid.addWidget(self._th_blocked_spin, 2, 1)
        monitor_cfg_layout.addLayout(monitor_threshold_grid)

        self._save_threshold_btn = QPushButton("Save Thresholds")
        self._save_threshold_btn.setStyleSheet(automation_button_style)
        self._save_threshold_btn.clicked.connect(self._on_save_thresholds_clicked)
        monitor_cfg_layout.addWidget(self._save_threshold_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        alert_card_layout.addWidget(monitor_cfg)
        top_cards_row.addWidget(alert_card, 1)

        # Card 3: Custom Categories
        custom_card = QFrame()
        custom_card.setObjectName("AutomationCard")
        custom_card_layout = QVBoxLayout(custom_card)
        custom_card_layout.setContentsMargins(14, 12, 14, 12)
        custom_card_layout.setSpacing(10)

        custom_header = QHBoxLayout()
        custom_header.setContentsMargins(0, 0, 0, 0)
        custom_header.setSpacing(8)
        custom_header_lbl = QLabel("Custom Category Rules")
        custom_header_lbl.setStyleSheet(card_title_style)
        custom_header.addWidget(custom_header_lbl)
        custom_header.addStretch()
        self._custom_status_label = QLabel("0 configured")
        self._custom_status_label.setStyleSheet(
            "padding: 2px 8px; border-radius: 10px; font-size: 10px; "
            "font-weight: 700; color: #0f766e; background: #ccfbf1;"
        )
        custom_header.addWidget(self._custom_status_label)
        custom_card_layout.addLayout(custom_header)

        custom_hint = QLabel("Create custom wait groups for focused diagnostics")
        custom_hint.setStyleSheet(card_hint_style)
        custom_card_layout.addWidget(custom_hint)

        self._custom_rules_text = QTextEdit()
        self._custom_rules_text.setReadOnly(True)
        self._custom_rules_text.setPlaceholderText("Custom category rules and totals...")
        self._custom_rules_text.setMinimumHeight(118)
        self._custom_rules_text.setStyleSheet(f"""
            QTextEdit {{
                background: #ffffff;
                border: 1px solid #dfe4ea;
                border-radius: 6px;
                color: #2c3e50;
                padding: 8px;
                font-size: 11px;
            }}
        """)
        custom_card_layout.addWidget(self._custom_rules_text)

        custom_btn_row = QHBoxLayout()
        custom_btn_row.setContentsMargins(0, 0, 0, 0)
        custom_btn_row.setSpacing(8)
        self._automation_custom_add_btn = QPushButton("Add Category")
        self._automation_custom_add_btn.setStyleSheet(automation_button_style)
        self._automation_custom_add_btn.clicked.connect(self._on_add_custom_rule_clicked)
        custom_btn_row.addWidget(self._automation_custom_add_btn)

        self._automation_custom_remove_btn = QPushButton("Remove Category")
        self._automation_custom_remove_btn.setStyleSheet(automation_button_style)
        self._automation_custom_remove_btn.clicked.connect(self._on_remove_custom_rule_clicked)
        custom_btn_row.addWidget(self._automation_custom_remove_btn)
        custom_btn_row.addStretch()
        custom_card_layout.addLayout(custom_btn_row)

        top_cards_row.addWidget(custom_card, 1)
        automation_panel_layout.addLayout(top_cards_row)

        # Multi-server table card
        multi_card = QFrame()
        multi_card.setObjectName("AutomationCard")
        multi_card_layout = QVBoxLayout(multi_card)
        multi_card_layout.setContentsMargins(14, 12, 14, 12)
        multi_card_layout.setSpacing(10)

        multi_header = QHBoxLayout()
        multi_header.setContentsMargins(0, 0, 0, 0)
        multi_header.setSpacing(8)
        multi_title = QLabel("Multi-Server Wait Time Comparison")
        multi_title.setStyleSheet(card_title_style)
        multi_header.addWidget(multi_title)
        multi_header.addStretch()
        self._multi_server_status_label = QLabel("No data")
        self._multi_server_status_label.setStyleSheet(
            "padding: 2px 8px; border-radius: 10px; font-size: 10px; "
            "font-weight: 700; color: #475569; background: #e2e8f0;"
        )
        multi_header.addWidget(self._multi_server_status_label)
        multi_card_layout.addLayout(multi_header)

        target_row = QWidget()
        target_row.setStyleSheet("background: transparent;")
        target_row_layout = QHBoxLayout(target_row)
        target_row_layout.setContentsMargins(0, 0, 0, 0)
        target_row_layout.setSpacing(8)

        self._add_monitor_target_btn = QPushButton("Add Server Target")
        self._add_monitor_target_btn.setStyleSheet(automation_button_style)
        self._add_monitor_target_btn.clicked.connect(self._on_add_monitor_target_clicked)
        target_row_layout.addWidget(self._add_monitor_target_btn)

        self._remove_monitor_target_btn = QPushButton("Remove Target")
        self._remove_monitor_target_btn.setStyleSheet(automation_button_style)
        self._remove_monitor_target_btn.clicked.connect(self._on_remove_monitor_target_clicked)
        target_row_layout.addWidget(self._remove_monitor_target_btn)

        self._push_metrics_btn = QPushButton("Push Metrics Now")
        self._push_metrics_btn.setStyleSheet(automation_button_style)
        self._push_metrics_btn.clicked.connect(self._on_push_metrics_clicked)
        target_row_layout.addWidget(self._push_metrics_btn)
        target_row_layout.addStretch()
        multi_card_layout.addWidget(target_row)

        self._multi_server_table = QTreeWidget()
        self._multi_server_table.setHeaderLabels(
            ["Server", "Database", "Total Wait", "Signal %", "Top Category", "Delta(window)"]
        )
        self._multi_server_table.setAlternatingRowColors(True)
        self._multi_server_table.setRootIsDecorated(False)
        self._multi_server_table.setMinimumHeight(160)
        self._multi_server_table.setStyleSheet(f"""
            QTreeWidget {{
                border: 1px solid #dfe4ea;
                border-radius: 8px;
                background: #ffffff;
                color: #2c3e50;
                font-size: 11px;
            }}
            QHeaderView::section {{
                background: #f1f5f9;
                color: #334155;
                border: none;
                border-bottom: 1px solid #dfe4ea;
                padding: 6px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)
        multi_header_view = self._multi_server_table.header()
        multi_header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        multi_header_view.setStretchLastSection(True)
        multi_card_layout.addWidget(self._multi_server_table, stretch=1)
        automation_panel_layout.addWidget(multi_card, stretch=1)

        automation_layout.addWidget(automation_panel)

        self._content_tabs.addTab(automation_tab, "Automation")

        tabs_card = QFrame()
        tabs_card.setObjectName("Card")
        tabs_card.setStyleSheet(card_style)
        tabs_layout = QVBoxLayout(tabs_card)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(0)
        tabs_layout.addWidget(self._content_tabs)

        center_split = QWidget()
        center_split.setStyleSheet("background: transparent;")
        center_split_layout = QHBoxLayout(center_split)
        center_split_layout.setContentsMargins(0, 0, 0, 0)
        center_split_layout.setSpacing(12)
        center_split_layout.addWidget(tabs_card, 3)
        center_split_layout.addWidget(right_panel, 2, Qt.AlignmentFlag.AlignTop)

        main_layout.addWidget(center_split, stretch=1)
        self._main_layout.addWidget(main_widget)

    @staticmethod
    def _set_badge(label: Optional[QLabel], text: str, fg: str, bg: str) -> None:
        if label is None:
            return
        label.setText(str(text or ""))
        label.setStyleSheet(
            "padding: 2px 8px; border-radius: 10px; font-size: 10px; "
            f"font-weight: 700; color: {fg}; background: {bg};"
        )

    def _refresh_automation_badges(self) -> None:
        schedule_running = bool(self._schedule_worker and self._schedule_worker.isRunning())
        schedule_enabled = bool(getattr(self, "_schedule_enabled_chk", None) and self._schedule_enabled_chk.isChecked())
        monitor_enabled = bool(getattr(self, "_monitor_enabled_chk", None) and self._monitor_enabled_chk.isChecked())

        if schedule_running:
            self._set_badge(self._schedule_status_badge, "Running", "#1d4ed8", "#dbeafe")
        elif schedule_enabled:
            self._set_badge(self._schedule_status_badge, "Active", "#047857", "#d1fae5")
        else:
            self._set_badge(self._schedule_status_badge, "Inactive", "#475569", "#e2e8f0")

        if monitor_enabled:
            self._set_badge(self._monitor_status_badge, "Active", "#047857", "#d1fae5")
        else:
            self._set_badge(self._monitor_status_badge, "❌ Paused", "#9a3412", "#ffedd5")

    def on_show(self) -> None:
        """Called when view becomes visible"""
        if self._analysis_context is None:
            cached_ctx = self._service.get_last_context()
            if cached_ctx:
                self._analysis_context = cached_ctx
                self._context_label.setVisible(True)
                self._context_label.setText(
                    f"Focus context: {cached_ctx.object_full_name or 'Query ' + str(cached_ctx.query_id)}"
                )
        if hasattr(self, "_monitor_enabled_chk") and self._monitor_enabled_chk.isChecked():
            self._monitor_timer.start()
        self._refresh_monitoring_target_status()
        self._refresh_automation_badges()
        self.refresh()
    
    def on_hide(self) -> None:
        """Called when view is hidden"""
        if hasattr(self, "_monitor_timer"):
            self._monitor_timer.stop()
        if self._refresh_worker and self._refresh_worker.isRunning():
            self._refresh_worker.cancel()
        if self._schedule_worker and self._schedule_worker.isRunning():
            self._schedule_worker.requestInterruption()

    def receive_analysis_context(self, context: AnalysisContext) -> None:
        """Receive context and switch to query-level wait correlation when available."""
        self._analysis_context = context
        self._service.receive_context(context)
        self._context_label.setVisible(True)
        self._context_label.setText(
            f"Focus context: {context.object_full_name or 'Query ' + str(context.query_id)}"
        )
        if self._is_initialized:
            self.refresh()

    def _on_query_analyzed_event(self, context_obj: object) -> None:
        context = context_obj if isinstance(context_obj, AnalysisContext) else None
        if context is None:
            return
        if str(getattr(context, "target_module", "") or "").strip() != "wait_stats":
            return
        self.receive_analysis_context(context)

    @staticmethod
    def _map_query_wait_category(category_text: str) -> WaitCategory:
        return resolve_wait_category_text(category_text)

    def _on_trend_window_changed(self, _index: int) -> None:
        data = self._trend_combo.currentData()
        self._trend_days = int(data or 7)
        if self._is_initialized:
            self.refresh()

    def _on_trend_display_mode_changed(self, _index: int) -> None:
        self._render_trend(
            self._trend_points_cache,
            self._trend_source_cache,
            self._trend_days_cache,
        )

    def _on_monitor_toggle_changed(self, _state: int) -> None:
        enabled = self._monitor_enabled_chk.isChecked()
        if enabled and self._is_initialized:
            self._monitor_timer.start()
        else:
            self._monitor_timer.stop()
        self._refresh_automation_badges()

    def _on_monitor_tick(self) -> None:
        if not self._is_initialized:
            return
        if not self._monitor_enabled_chk.isChecked():
            return
        if self._refresh_worker and self._refresh_worker.isRunning():
            return
        if not self._service.is_connected:
            return
        self.refresh()

    def _on_save_thresholds_clicked(self) -> None:
        thresholds = WaitAlertThresholds(
            total_wait_time_ms=int(self._th_total_wait_spin.value()),
            lock_wait_percent=float(self._th_lock_wait_spin.value()),
            io_wait_percent=float(self._alert_thresholds.io_wait_percent),
            blocked_sessions=int(self._th_blocked_spin.value()),
            chain_depth=int(self._alert_thresholds.chain_depth),
            single_wait_ms=int(self._alert_thresholds.single_wait_ms),
        )
        if self._service.save_alert_thresholds(thresholds):
            self._alert_thresholds = thresholds
            self._set_status("Alert thresholds saved.", Colors.SUCCESS)
            self._refresh_automation_badges()
            return
        self._set_status("Failed to save alert thresholds.", Colors.ERROR)
    
    def refresh(self) -> None:
        """Refresh wait statistics"""
        if not self._is_initialized:
            logger.debug("Wait stats refresh skipped: View not initialized")
            return

        if self._refresh_worker and self._refresh_worker.isRunning():
            self._set_status("Refresh already in progress...", Colors.TEXT_SECONDARY)
            return

        if not self._service.is_connected:
            self._set_status("Please connect to a database first.", Colors.WARNING)
            return

        self._render_token += 1
        self.set_loading(True)
        self._refresh_btn.setEnabled(False)
        self._set_progress(5, "Starting background refresh...")
        db_filter = str(self._db_filter_combo.currentData() or self._db_filter_combo.currentText() or "").strip()
        app_filter = str(self._app_filter_combo.currentData() or self._app_filter_combo.currentText() or "").strip()
        if db_filter.lower().startswith("all "):
            db_filter = ""
        if app_filter.lower().startswith("all "):
            app_filter = ""
        min_wait_ms = int(self._min_wait_filter_spin.value() if hasattr(self, "_min_wait_filter_spin") else 0)

        self._refresh_worker = WaitStatsRefreshWorker(
            service=self._service,
            blocking_service=self._blocking_service,
            context=self._analysis_context,
            trend_days=self._trend_days,
            database_filter=db_filter,
            application_filter=app_filter,
            min_wait_time_ms=min_wait_ms,
            parent=self,
        )
        self._refresh_worker.progress_updated.connect(self._on_refresh_progress)
        self._refresh_worker.refresh_completed.connect(self._on_refresh_completed)
        self._refresh_worker.refresh_failed.connect(self._on_refresh_failed)
        self._refresh_worker.telemetry_captured.connect(self._on_refresh_telemetry)
        self._refresh_worker.finished.connect(self._on_refresh_worker_finished)
        self._refresh_worker.start()

    def _set_status(self, message: str, color: str = Colors.TEXT_SECONDARY) -> None:
        self._status_label.setText(str(message or ""))
        self._status_label.setStyleSheet(
            f"color: {color}; font-size: 11px; background: transparent;"
        )

    def _set_progress(self, percent: int, message: str) -> None:
        value = max(0, min(100, int(percent)))
        self._progress_bar.setValue(value)
        self._set_status(message)

    def _on_refresh_progress(self, percent: int, message: str) -> None:
        self._set_progress(percent, message)

    def _on_refresh_telemetry(self, telemetry_obj: object) -> None:
        telemetry = telemetry_obj if isinstance(telemetry_obj, WaitStatsMetrics) else None
        if telemetry is None:
            return
        self._last_metrics = telemetry
        contract = telemetry.to_lightweight_contract()
        logger.info(f"WaitStats telemetry {json.dumps(contract, ensure_ascii=False)}")

    def _on_refresh_completed(self, payload_obj: object) -> None:
        payload = payload_obj if isinstance(payload_obj, WaitStatsRefreshPayload) else None
        if payload is None:
            self._set_status("Refresh completed with an invalid payload.", Colors.WARNING)
            return

        self._last_payload = payload
        self._render_token += 1
        token = self._render_token
        self._apply_refresh_payload_ui(token, payload, step=0)

    def _apply_refresh_payload_ui(self, token: int, payload: WaitStatsRefreshPayload, step: int) -> None:
        if token != self._render_token:
            return

        steps = [
            lambda: self._update_ui(payload.summary),
            lambda: self._render_trend(payload.trend_points, payload.trend_source, payload.trend_days),
            lambda: self._update_waits_list(
                payload.waits_to_render if payload.correlation_used else payload.summary.top_waits,
                trend_points=payload.trend_points,
                baseline=payload.baseline_comparison,
                total_wait_ms=payload.summary.total_wait_time_ms,
            ),
            lambda: self._render_signature_baseline(payload.signatures, payload.baseline_comparison),
            lambda: self._render_wait_chain(payload.blocking_analysis),
            lambda: self._render_alerts(payload.alerts, payload.thresholds),
            lambda: self._render_comparative(payload.comparative_analysis),
            lambda: self._render_action_plan(
                summary=payload.summary,
                waits=payload.waits_to_render if payload.correlation_used else payload.summary.top_waits,
                alerts=payload.alerts,
                signatures=payload.signatures,
                baseline=payload.baseline_comparison,
                trend_points=payload.trend_points,
            ),
            lambda: self._render_custom_category_rules(payload.custom_category_rules, payload.custom_category_breakdown),
            lambda: self._render_multi_server(payload.multi_server_snapshots),
            lambda: self._render_plan_correlation(payload.plan_correlation),
            lambda: self._refresh_filter_options(payload.summary),
            self._refresh_monitoring_target_status,
            lambda: self._run_scheduled_automation(payload),
        ]

        if step >= len(steps):
            self._finalize_refresh_status(payload)
            return
        try:
            steps[step]()
        except Exception as ex:
            logger.warning(f"WaitStats UI step failed [step={step}]: {ex}")
        QTimer.singleShot(0, lambda: self._apply_refresh_payload_ui(token, payload, step + 1))

    def _finalize_refresh_status(self, payload: WaitStatsRefreshPayload) -> None:
        telemetry = payload.telemetry if isinstance(payload.telemetry, WaitStatsMetrics) else self._last_metrics
        duration_ms = int(getattr(telemetry, "load_duration_ms", 0) or 0)
        rows_rendered = len(payload.waits_to_render or [])

        if telemetry and telemetry.partial_data:
            self._set_status(
                f"Completed with partial data in {duration_ms} ms (rows={rows_rendered}).",
                Colors.WARNING,
            )
            return

        mode_text = "query" if payload.correlation_used else "server"
        alerts_count = len(payload.alerts or [])
        self._set_status(
            f"Updated in {duration_ms} ms | mode={mode_text} | waits={rows_rendered} | alerts={alerts_count}",
            Colors.TEXT_MUTED,
        )

    def _on_refresh_failed(self, error: str) -> None:
        logger.error(f"Error refreshing wait stats: {error}")
        self._render_token += 1
        self._set_progress(0, f"Refresh failed: {error}")
        self._set_status(f"Refresh failed: {error}", Colors.ERROR)

    def _on_refresh_worker_finished(self) -> None:
        self.set_loading(False)
        self._refresh_btn.setEnabled(True)
        self._refresh_worker = None

    def _render_signature_baseline(
        self,
        signatures: List[WaitSignature],
        baseline: WaitBaselineComparison,
    ) -> None:
        primary = signatures[0] if signatures else None
        if primary is None:
            self._signature_label.setText("No wait signature detected yet.")
            return

        evidence = "; ".join(primary.evidence[:2]) if primary.evidence else "No direct evidence."
        baseline_text = str(getattr(baseline, "summary", "") or "No baseline configured.")
        self._signature_label.setText(
            f"{primary.title} ({primary.confidence * 100:.0f}% confidence)\n"
            f"Evidence: {evidence}\n"
            f"Baseline: {baseline_text}"
        )

    def _render_trend(self, trend_points: List[WaitTrendPoint], source: str, days: int) -> None:
        self._trend_points_cache = list(trend_points or [])
        self._trend_source_cache = str(source or "none")
        self._trend_days_cache = max(1, int(days or 7))

        if not trend_points:
            self._trend_text.setPlainText(
                f"No historical trend data for {days} days. Source={source or 'none'}."
            )
            return

        mode = str(self._trend_display_combo.currentData() or "summary")
        if mode == "dominant":
            self._render_trend_mode_dominant(trend_points, source, days)
            return
        if mode == "breakdown":
            self._render_trend_mode_breakdown(trend_points, source, days)
            return

        self._render_trend_mode_summary(trend_points, source, days)

    def _render_trend_mode_summary(self, trend_points: List[WaitTrendPoint], source: str, days: int) -> None:
        lines = [
            f"Trend window: {days} days",
            f"Source: {source}",
            "",
            "Date | Total Wait ms | Dominant Category | Dominant ms",
            "-" * 72,
        ]
        for point in trend_points:
            lines.append(
                f"{point.trend_date} | {int(point.total_wait_ms):,} | "
                f"{point.dominant_category} | {int(point.dominant_wait_ms):,}"
            )
        self._trend_text.setPlainText("\n".join(lines))

    def _render_trend_mode_dominant(self, trend_points: List[WaitTrendPoint], source: str, days: int) -> None:
        lines = [
            f"Trend window: {days} days",
            f"Source: {source}",
            "",
            "Date | Dominant | Share % | Total Wait ms",
            "-" * 70,
        ]
        for point in trend_points:
            dominant = str(point.dominant_category or "Other")
            pct = float((point.category_percent or {}).get(dominant, 0.0) or 0.0)
            lines.append(
                f"{point.trend_date} | {dominant} | {pct:.1f}% | {int(point.total_wait_ms):,}"
            )
        self._trend_text.setPlainText("\n".join(lines))

    def _render_trend_mode_breakdown(self, trend_points: List[WaitTrendPoint], source: str, days: int) -> None:
        lines = [
            f"Trend window: {days} days",
            f"Source: {source}",
            "",
            "Date | Top Categories (share / wait ms)",
            "-" * 78,
        ]
        for point in trend_points:
            category_wait = dict(point.category_wait_ms or {})
            if not category_wait:
                lines.append(f"{point.trend_date} | n/a")
                continue
            ordered = sorted(category_wait.items(), key=lambda item: int(item[1] or 0), reverse=True)
            top_parts = []
            for name, wait_ms in ordered[:3]:
                pct = float((point.category_percent or {}).get(str(name), 0.0) or 0.0)
                top_parts.append(f"{name}: {pct:.1f}% ({int(wait_ms or 0):,})")
            lines.append(f"{point.trend_date} | " + "; ".join(top_parts))
        self._trend_text.setPlainText("\n".join(lines))

    def _render_wait_chain(self, chain: BlockingChainAnalysis) -> None:
        self._blocking_tree.clear()
        self._blocking_tree.setHeaderLabels(["Session", "Wait", "Wait ms", "Database", "Login"])
        sessions = list(chain.blocking_sessions or [])
        if not sessions:
            self._blocking_tree.setHeaderLabels(["Session", "Wait", "Wait ms", "Database", "Login"])
            placeholder = QTreeWidgetItem(["No active blocking chains", "", "", "", ""])
            self._blocking_tree.addTopLevelItem(placeholder)
            return

        session_by_id = {int(item.session_id): item for item in sessions}
        by_blocker: Dict[int, List[BlockingSession]] = {}
        for item in sessions:
            blocker_id = int(item.blocking_session_id or 0)
            if blocker_id <= 0:
                continue
            by_blocker.setdefault(blocker_id, []).append(item)
        for blocker_id in list(by_blocker.keys()):
            by_blocker[blocker_id] = sorted(
                list(by_blocker.get(blocker_id, [])),
                key=lambda x: float(x.wait_seconds or 0.0),
                reverse=True,
            )

        head_ids = [int(item.session_id or 0) for item in list(chain.head_blockers or []) if int(item.session_id or 0) > 0]
        if not head_ids:
            blocking_ids = {int(item.blocking_session_id or 0) for item in sessions if int(item.blocking_session_id or 0) > 0}
            blocked_ids = {int(item.session_id or 0) for item in sessions if int(item.session_id or 0) > 0}
            head_ids = sorted(blocking_ids - blocked_ids) or sorted(blocking_ids)

        head_map = {int(item.session_id): item for item in list(chain.head_blockers or []) if int(item.session_id or 0) > 0}
        max_nodes = max(50, int(self.MAX_BLOCKING_TREE_NODES))
        rendered_nodes = 0
        truncated = False

        def make_root_item(session_id: int) -> QTreeWidgetItem:
            head = head_map.get(session_id)
            if head is None:
                fallback = session_by_id.get(session_id)
                return QTreeWidgetItem(
                    [
                        f"SPID {session_id} (root)",
                        "",
                        "",
                        str(getattr(fallback, "database_name", "") or ""),
                        str(getattr(fallback, "login_name", "") or ""),
                    ]
                )
            return QTreeWidgetItem(
                [
                    f"SPID {session_id} (root)",
                    "",
                    "",
                    str(head.database_name or ""),
                    str(head.login_name or ""),
                ]
            )

        def make_blocked_item(blocked_session: BlockingSession) -> QTreeWidgetItem:
            wait_ms = int(round(float(blocked_session.wait_seconds or 0.0) * 1000.0))
            return QTreeWidgetItem(
                [
                    f"SPID {int(blocked_session.session_id or 0)}",
                    str(blocked_session.wait_type or ""),
                    f"{wait_ms:,}",
                    str(blocked_session.database_name or ""),
                    str(blocked_session.login_name or ""),
                ]
            )

        def attach(parent_item: QTreeWidgetItem, blocker_id: int, visited: set[int]) -> None:
            nonlocal rendered_nodes, truncated
            for child in by_blocker.get(blocker_id, []):
                if rendered_nodes >= max_nodes:
                    truncated = True
                    return
                child_id = int(child.session_id or 0)
                child_item = make_blocked_item(child)
                parent_item.addChild(child_item)
                rendered_nodes += 1
                if child_id in visited:
                    child_item.addChild(QTreeWidgetItem(["Cycle detected", "", "", "", ""]))
                    continue
                attach(child_item, child_id, visited | {child_id})

        for root_id in head_ids:
            if rendered_nodes >= max_nodes:
                truncated = True
                break
            root_item = make_root_item(root_id)
            self._blocking_tree.addTopLevelItem(root_item)
            rendered_nodes += 1
            attach(root_item, root_id, {root_id})

        if truncated:
            self._blocking_tree.addTopLevelItem(
                QTreeWidgetItem(
                    [
                        f"Truncated view at {rendered_nodes:,} nodes for responsiveness",
                        "",
                        "",
                        "",
                        "",
                    ]
                )
            )

        self._blocking_tree.expandToDepth(2)

    def _render_alerts(self, alerts: List[WaitAlert], thresholds: WaitAlertThresholds) -> None:
        block_style_default = f"""
            QFrame#InsightBlock {{
                background: {Colors.BACKGROUND};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
            }}
        """
        if self._alerts_block is not None:
            self._alerts_block.setStyleSheet(block_style_default)

        if not alerts:
            self._alert_label.setStyleSheet(
                f"color: {Colors.SUCCESS}; font-size: 12px; background: transparent;"
            )
            self._alert_label.setText(
                "No active wait alerts.\n"
                f"Thresholds: wait>={thresholds.total_wait_time_ms:,}ms | "
                f"lock>={thresholds.lock_wait_percent:.1f}% | blocked>={thresholds.blocked_sessions}"
            )
            return

        critical_count = sum(1 for alert in alerts if str(alert.severity).lower() == "critical")
        color = Colors.ERROR if critical_count > 0 else Colors.WARNING
        if self._alerts_block is not None:
            bg_tone = "#fef2f2" if critical_count > 0 else "#fffbeb"
            border_tone = Colors.ERROR if critical_count > 0 else Colors.WARNING
            self._alerts_block.setStyleSheet(f"""
                QFrame#InsightBlock {{
                    background: {bg_tone};
                    border: 1px solid {border_tone};
                    border-radius: 6px;
                }}
            """)
        self._alert_label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 700; background: transparent;"
        )
        lines = [
            f"- [{str(alert.severity).upper()}] {alert.title}: {alert.message}"
            for alert in alerts[:3]
        ]
        extra = f"\n+{len(alerts) - 3} more alert(s)" if len(alerts) > 3 else ""
        self._alert_label.setText(f"{len(alerts)} active alert(s)\n" + "\n".join(lines) + extra)

    def _render_comparative(self, analysis: WaitComparativeAnalysis) -> None:
        status = str(analysis.status or "insufficient-data")
        if status == "improved":
            color = Colors.SUCCESS
        elif status == "degraded":
            color = Colors.ERROR
        elif status == "stable":
            color = Colors.WARNING
        else:
            color = Colors.TEXT_SECONDARY
        self._comparison_label.setStyleSheet(
            f"color: {color}; font-size: 12px; background: transparent;"
        )
        summary_text = str(analysis.summary or "Before/After comparison unavailable.")
        status_label = status.replace("-", " ").title()
        self._comparison_label.setText(f"Status: {status_label}\n{summary_text}")

    def _render_custom_category_rules(
        self,
        rules: List[CustomWaitCategoryRule],
        breakdown: Dict[str, int],
    ) -> None:
        lines: List[str] = ["Custom Category Rules:"]
        if rules:
            for rule in rules:
                state = "ON" if rule.enabled else "OFF"
                lines.append(f"- {rule.name} [{state}] => /{rule.pattern}/")
        else:
            lines.append("- No custom categories configured.")

        lines.append("")
        lines.append("Current Wait Time by Custom Category:")
        if breakdown:
            for name, wait_ms in breakdown.items():
                lines.append(f"- {name}: {int(wait_ms):,} ms")
        else:
            lines.append("- No waits matched custom categories.")
        self._custom_rules_text.setPlainText("\n".join(lines))
        if self._custom_status_label is not None:
            enabled_count = sum(1 for item in (rules or []) if item.enabled)
            total_count = len(rules or [])
            if total_count <= 0:
                self._custom_status_label.setText("0 configured")
                self._custom_status_label.setStyleSheet(
                    "padding: 2px 8px; border-radius: 10px; font-size: 10px; "
                    "font-weight: 700; color: #475569; background: #e2e8f0;"
                )
            else:
                self._custom_status_label.setText(f"{enabled_count}/{total_count} active")
                self._custom_status_label.setStyleSheet(
                    "padding: 2px 8px; border-radius: 10px; font-size: 10px; "
                    "font-weight: 700; color: #0f766e; background: #ccfbf1;"
                )

    def _render_multi_server(self, snapshots: List[MultiServerWaitSnapshot]) -> None:
        table = self._multi_server_table
        if table is None:
            return

        table.clear()
        if not snapshots:
            placeholder = QTreeWidgetItem(
                ["No data", "-", "-", "-", "-", "Connect additional servers over time."]
            )
            table.addTopLevelItem(placeholder)
            if self._multi_server_status_label is not None:
                self._multi_server_status_label.setText("No data")
                self._multi_server_status_label.setStyleSheet(
                    "padding: 2px 8px; border-radius: 10px; font-size: 10px; "
                    "font-weight: 700; color: #475569; background: #e2e8f0;"
                )
            return

        for item in snapshots[:40]:
            delta_value = int(item.delta_wait_ms_window or 0)
            if delta_value > 0:
                delta_text = f"+{delta_value:,}"
            elif delta_value < 0:
                delta_text = f"{delta_value:,}"
            else:
                delta_text = "0"

            top_category = str(item.top_category or "")
            if item.signal_wait_percent >= 70.0:
                top_category = f"{top_category} (High Signal)"

            node = QTreeWidgetItem(
                [
                    str(item.server or ""),
                    str(item.database or ""),
                    self._format_time(int(item.total_wait_time_ms or 0)),
                    f"{float(item.signal_wait_percent or 0.0):.1f}%",
                    top_category,
                    delta_text,
                ]
            )
            table.addTopLevelItem(node)

        if self._multi_server_status_label is not None:
            self._multi_server_status_label.setText(f"{len(snapshots)} server snapshot(s)")
            self._multi_server_status_label.setStyleSheet(
                "padding: 2px 8px; border-radius: 10px; font-size: 10px; "
                "font-weight: 700; color: #0369a1; background: #e0f2fe;"
            )

    def _render_plan_correlation(self, correlation: WaitPlanCorrelation) -> None:
        if correlation.query_id <= 0:
            self._plan_correlation_label.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;"
            )
            self._plan_correlation_label.setText(
                "Wait/Plan correlation requires query context.\nNavigate from Query Statistics."
            )
            return

        color = Colors.SUCCESS if correlation.plan_available else Colors.WARNING
        findings = "; ".join(correlation.findings[:2]) if correlation.findings else "No strong wait-plan linkage detected."
        rec = correlation.recommendations[0] if correlation.recommendations else "Capture additional executions for stronger correlation."
        self._plan_correlation_label.setStyleSheet(
            f"color: {color}; font-size: 12px; background: transparent;"
        )
        self._plan_correlation_label.setText(
            f"Query {correlation.query_id} ({correlation.confidence * 100:.0f}% confidence)\n"
            f"Categories: {', '.join(correlation.dominant_wait_categories or ['n/a'])}\n"
            f"Findings: {findings}\n"
            f"Action: {rec}"
        )

    def _refresh_filter_options(self, summary: WaitSummary) -> None:
        databases = self._collect_distinct_filter_values(
            values=[str(w.database_name or "") for w in (summary.current_waits or [])],
            max_items=200,
        )
        apps = self._collect_distinct_filter_values(
            values=[str(w.program_name or "") for w in (summary.current_waits or [])],
            max_items=250,
        )

        current_db_text = str(self._db_filter_combo.currentText() or "")
        current_app_text = str(self._app_filter_combo.currentText() or "")
        self._db_filter_combo.blockSignals(True)
        self._app_filter_combo.blockSignals(True)
        self._db_filter_combo.clear()
        self._db_filter_combo.addItem("All Databases", "")
        for db in databases[:200]:
            self._db_filter_combo.addItem(db, db)
        self._db_filter_combo.setCurrentText(current_db_text if current_db_text else "All Databases")
        self._app_filter_combo.clear()
        self._app_filter_combo.addItem("All Applications", "")
        for app in apps[:250]:
            self._app_filter_combo.addItem(app, app)
        self._app_filter_combo.setCurrentText(current_app_text if current_app_text else "All Applications")
        self._db_filter_combo.blockSignals(False)
        self._app_filter_combo.blockSignals(False)

    @staticmethod
    def _collect_distinct_filter_values(values: List[str], max_items: int) -> List[str]:
        seen = set()
        out: List[str] = []
        limit = max(1, int(max_items or 1))
        for raw in values or []:
            text = str(raw or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            out.append(text)
            if len(out) >= limit:
                break
        out.sort(key=lambda value: value.lower())
        return out

    def _on_schedule_settings_changed(self, _value: int) -> None:
        self._schedule_config.enabled = bool(self._schedule_enabled_chk.isChecked())
        self._schedule_config.interval_minutes = int(self._schedule_interval_spin.value())
        self._refresh_automation_badges()

    def _on_save_schedule_clicked(self) -> None:
        self._on_schedule_settings_changed(0)
        if self._service.save_schedule_config(self._schedule_config):
            self._set_status("Scheduled snapshot config saved.", Colors.SUCCESS)
            self._refresh_automation_badges()
            return
        self._set_status("Failed to save schedule config.", Colors.ERROR)

    def _run_scheduled_automation(self, payload: WaitStatsRefreshPayload) -> None:
        self._on_schedule_settings_changed(0)
        if not self._schedule_config.enabled:
            return
        if self._schedule_worker and self._schedule_worker.isRunning():
            return
        now = datetime.now()
        if self._last_schedule_run is not None:
            min_delta = timedelta(minutes=max(1, int(self._schedule_config.interval_minutes)))
            if (now - self._last_schedule_run) < min_delta:
                return

        self._schedule_worker = WaitStatsAutomationWorker(
            service=self._service,
            payload=payload,
            schedule_config=self._schedule_config,
            parent=self,
        )
        self._last_schedule_run = now
        self._schedule_worker.completed.connect(self._on_schedule_worker_completed)
        self._schedule_worker.failed.connect(self._on_schedule_worker_failed)
        self._schedule_worker.finished.connect(self._on_schedule_worker_finished)
        self._refresh_automation_badges()
        self._schedule_worker.start()

    def _on_schedule_worker_completed(self, report_count: int, snapshot_written: bool) -> None:
        logger.info(
            f"Scheduled wait automation completed [reports={int(report_count)}, snapshot={bool(snapshot_written)}]"
        )

    def _on_schedule_worker_failed(self, error: str) -> None:
        logger.warning(f"Scheduled wait automation failed: {error}")

    def _on_schedule_worker_finished(self) -> None:
        self._schedule_worker = None
        self._refresh_automation_badges()

    def _refresh_monitoring_target_status(self) -> None:
        targets = self._service.load_monitoring_targets()
        if not targets:
            self._monitoring_status_label.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;"
            )
            self._monitoring_status_label.setText("Monitoring targets: none configured.")
            return
        enabled = [t for t in targets if t.enabled]
        label_text = ", ".join(f"{t.name}({t.payload_format})" for t in enabled[:5])
        more = ""
        if len(enabled) > 5:
            more = f" +{len(enabled) - 5} more"
        self._monitoring_status_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; background: transparent;"
        )
        header_text = f"Enabled: {len(enabled)}/{len(targets)}"
        if label_text:
            self._monitoring_status_label.setText(f"{header_text}\n{label_text}{more}")
        else:
            self._monitoring_status_label.setText(header_text)

    def _on_add_monitor_target_clicked(self) -> None:
        name, ok = QInputDialog.getText(self, "Monitoring Target", "Target Name:")
        if not ok:
            return
        url, ok = QInputDialog.getText(self, "Monitoring Target", "Target URL (HTTP POST):")
        if not ok:
            return
        fmt, ok = QInputDialog.getItem(
            self,
            "Monitoring Target",
            "Payload Format:",
            ["json", "prometheus"],
            editable=False,
        )
        if not ok:
            return
        if self._service.add_monitoring_target(name=name, url=url, payload_format=fmt):
            self._set_status("Monitoring target saved.", Colors.SUCCESS)
            self._refresh_monitoring_target_status()
            return
        self._set_status("Failed to save monitoring target.", Colors.ERROR)

    def _on_remove_monitor_target_clicked(self) -> None:
        targets = self._service.load_monitoring_targets()
        if not targets:
            self._set_status("No monitoring target to remove.", Colors.WARNING)
            return
        labels = [f"{t.name} :: {t.url}" for t in targets]
        selected, ok = QInputDialog.getItem(
            self,
            "Remove Monitoring Target",
            "Select target:",
            labels,
            editable=False,
        )
        if not ok or not selected:
            return
        candidate = str(selected).split(" :: ", 1)[0].strip()
        if self._service.remove_monitoring_target(candidate):
            self._set_status("Monitoring target removed.", Colors.SUCCESS)
            self._refresh_monitoring_target_status()
            return
        self._set_status("Monitoring target removal failed.", Colors.ERROR)

    def _on_push_metrics_clicked(self) -> None:
        payload = self._last_payload
        if payload is None:
            self._set_status("Refresh wait stats before pushing metrics.", Colors.WARNING)
            return
        result = self._service.push_metrics_to_monitoring_targets(
            summary=payload.summary,
            chain=payload.blocking_analysis,
            alerts=payload.alerts,
        )
        success = int(result.get("success", 0) or 0)
        failed = int(result.get("failed", 0) or 0)
        if failed > 0:
            self._set_status(f"Monitoring push complete: success={success}, failed={failed}.", Colors.WARNING)
        else:
            self._set_status(f"Monitoring push complete: success={success}, failed={failed}.", Colors.SUCCESS)

    def _on_save_before_clicked(self) -> None:
        payload = self._last_payload
        if payload is None:
            self._set_status("Refresh before capturing BEFORE snapshot.", Colors.WARNING)
            return
        if self._service.save_comparative_snapshot("before", payload.summary):
            self._set_status("BEFORE snapshot captured.", Colors.SUCCESS)
            self._render_comparative(self._service.compare_before_after())
            return
        self._set_status("Failed to capture BEFORE snapshot.", Colors.ERROR)

    def _on_save_after_clicked(self) -> None:
        payload = self._last_payload
        if payload is None:
            self._set_status("Refresh before capturing AFTER snapshot.", Colors.WARNING)
            return
        if self._service.save_comparative_snapshot("after", payload.summary):
            self._set_status("AFTER snapshot captured.", Colors.SUCCESS)
            self._render_comparative(self._service.compare_before_after())
            return
        self._set_status("Failed to capture AFTER snapshot.", Colors.ERROR)

    def _on_compare_clicked(self) -> None:
        self._render_comparative(self._service.compare_before_after())

    def _on_add_custom_rule_clicked(self) -> None:
        name, ok = QInputDialog.getText(self, "Custom Category", "Category Name:")
        if not ok:
            return
        pattern, ok = QInputDialog.getText(self, "Custom Category", "Regex Pattern:")
        if not ok:
            return
        if self._service.add_custom_category_rule(name, pattern):
            self._set_status("Custom category rule saved.", Colors.SUCCESS)
            self.refresh()
            return
        self._set_status("Failed to save custom category rule (check regex).", Colors.ERROR)

    def _on_remove_custom_rule_clicked(self) -> None:
        rules = self._service.load_custom_category_rules()
        if not rules:
            self._set_status("No custom category rule to remove.", Colors.WARNING)
            return
        labels = [f"{rule.name} :: {rule.pattern}" for rule in rules]
        selected, ok = QInputDialog.getItem(
            self,
            "Remove Custom Category",
            "Select rule:",
            labels,
            editable=False,
        )
        if not ok or not selected:
            return
        parts = str(selected).split(" :: ", 1)
        name = parts[0].strip()
        pattern = parts[1].strip() if len(parts) > 1 else None
        if self._service.remove_custom_category_rule(name=name, pattern=pattern):
            self._set_status("Custom category rule removed.", Colors.SUCCESS)
            self.refresh()
            return
        self._set_status("Custom category rule could not be removed.", Colors.ERROR)

    def _on_set_baseline_clicked(self) -> None:
        payload = self._last_payload
        if payload is None:
            self._set_status("Refresh wait statistics before setting baseline.", Colors.WARNING)
            return

        if self._service.save_baseline(payload.summary):
            self._set_status("Baseline saved successfully.", Colors.SUCCESS)
            self.refresh()
            return
        self._set_status("Failed to save baseline.", Colors.ERROR)

    def _on_export_clicked(self) -> None:
        payload = self._last_payload
        if payload is None:
            self._set_status("No data to export. Refresh first.", Colors.WARNING)
            return

        default_name = f"wait_stats_export_{payload.summary.collected_at.strftime('%Y%m%d_%H%M%S')}"
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Wait Statistics",
            default_name,
            "CSV (*.csv);;JSON (*.json);;Markdown (*.md)",
        )
        if not file_path:
            return

        export_payload = self._service.build_export_payload(
            summary=payload.summary,
            waits_to_render=payload.waits_to_render,
            signatures=payload.signatures,
            baseline=payload.baseline_comparison,
            trend_points=payload.trend_points,
            trend_days=payload.trend_days,
            wait_chain=payload.blocking_analysis,
            alerts=payload.alerts,
            thresholds=payload.thresholds,
            comparative=payload.comparative_analysis,
            custom_category_breakdown=payload.custom_category_breakdown,
            custom_category_rules=payload.custom_category_rules,
            multi_server=payload.multi_server_snapshots,
            plan_correlation=payload.plan_correlation,
            filters=payload.filters,
        )

        try:
            path = Path(file_path)
            ext = path.suffix.lower()
            if not ext:
                if "csv" in str(selected_filter).lower():
                    ext = ".csv"
                elif "json" in str(selected_filter).lower():
                    ext = ".json"
                else:
                    ext = ".md"
                path = path.with_suffix(ext)

            if ext == ".json":
                self._export_json(path, export_payload)
            elif ext == ".md":
                self._export_markdown(path, export_payload)
            else:
                self._export_csv(path, export_payload)

            QMessageBox.information(self, "Export Complete", f"Wait stats exported:\n{path}")
            self._set_status(f"Exported wait stats to {path.name}", Colors.SUCCESS)
        except Exception as ex:
            QMessageBox.critical(self, "Export Failed", str(ex))
            self._set_status(f"Export failed: {ex}", Colors.ERROR)

    @staticmethod
    def _export_json(path: Path, payload: Dict[str, object]) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)

    @staticmethod
    def _export_csv(path: Path, payload: Dict[str, object]) -> None:
        summary = dict(payload.get("summary", {}) or {})
        top_waits = list(payload.get("top_waits", []) or [])
        trend = list(payload.get("trend", []) or [])
        signatures = list(payload.get("signatures", []) or [])
        alerts = list(payload.get("alerts", []) or [])
        wait_chain = dict(payload.get("wait_chain", {}) or {})
        comparative = dict(payload.get("before_after_comparison", {}) or {})
        custom_categories = dict(payload.get("custom_categories", {}) or {})
        multi_server = list(payload.get("multi_server", []) or [])
        plan_correlation = dict(payload.get("wait_plan_correlation", {}) or {})
        filters = dict(payload.get("filters", {}) or {})

        rows: List[Dict[str, object]] = []
        rows.append(
            {
                "section": "summary",
                "generated_at": payload.get("generated_at", ""),
                "trend_window_days": payload.get("trend_window_days", 0),
                "total_wait_time_ms": summary.get("total_wait_time_ms", 0),
                "signal_wait_percent": summary.get("signal_wait_percent", 0.0),
                "resource_wait_percent": summary.get("resource_wait_percent", 0.0),
            }
        )

        for sig in signatures:
            rows.append(
                {
                    "section": "signature",
                    "signature_title": sig.get("title", ""),
                    "signature_confidence": sig.get("confidence", 0.0),
                    "dominant_category": sig.get("dominant_category", ""),
                    "recommendation": sig.get("recommendation", ""),
                }
            )

        for wait in top_waits:
            rows.append(
                {
                    "section": "top_wait",
                    "wait_type": wait.get("wait_type", ""),
                    "category": wait.get("category", ""),
                    "wait_time_ms": wait.get("wait_time_ms", 0),
                    "wait_percent": wait.get("wait_percent", 0.0),
                    "waiting_tasks": wait.get("waiting_tasks", 0),
                }
            )

        for point in trend:
            rows.append(
                {
                    "section": "trend",
                    "trend_date": point.get("trend_date", ""),
                    "total_wait_ms": point.get("total_wait_ms", 0),
                    "dominant_category": point.get("dominant_category", ""),
                    "dominant_wait_ms": point.get("dominant_wait_ms", 0),
                }
            )

        rows.append(
            {
                "section": "wait_chain_summary",
                "chain_count": wait_chain.get("chain_count", 0),
                "total_blocked_sessions": wait_chain.get("total_blocked_sessions", 0),
                "total_blocking_sessions": wait_chain.get("total_blocking_sessions", 0),
                "max_chain_depth": wait_chain.get("max_chain_depth", 0),
                "chain_summary": wait_chain.get("summary", ""),
            }
        )

        for alert in alerts:
            rows.append(
                {
                    "section": "alert",
                    "alert_id": alert.get("alert_id", ""),
                    "severity": alert.get("severity", ""),
                    "title": alert.get("title", ""),
                    "message": alert.get("message", ""),
                    "metric_value": alert.get("metric_value", 0),
                    "threshold_value": alert.get("threshold_value", 0),
                }
            )

        rows.append(
            {
                "section": "before_after",
                "status": comparative.get("status", ""),
                "delta_total_wait_ms": comparative.get("delta_total_wait_ms", 0),
                "delta_signal_wait_percent": comparative.get("delta_signal_wait_percent", 0.0),
                "comparison_summary": comparative.get("summary", ""),
            }
        )

        rows.append(
            {
                "section": "plan_correlation",
                "query_id": plan_correlation.get("query_id", 0),
                "plan_available": plan_correlation.get("plan_available", False),
                "confidence": plan_correlation.get("confidence", 0.0),
                "findings": "; ".join(plan_correlation.get("findings", []) or []),
            }
        )

        rows.append(
            {
                "section": "filters",
                "database_filter": filters.get("database_name", ""),
                "application_filter": filters.get("application_name", ""),
                "time_window_days": filters.get("time_window_days", 0),
                "min_wait_time_ms": filters.get("min_wait_time_ms", 0),
            }
        )

        for cat_name, wait_ms in dict(custom_categories.get("wait_time_ms_by_category", {}) or {}).items():
            rows.append(
                {
                    "section": "custom_category",
                    "custom_category_name": cat_name,
                    "wait_time_ms": wait_ms,
                }
            )

        for item in multi_server:
            rows.append(
                {
                    "section": "multi_server",
                    "server": item.get("server", ""),
                    "database": item.get("database", ""),
                    "total_wait_time_ms": item.get("total_wait_time_ms", 0),
                    "signal_wait_percent": item.get("signal_wait_percent", 0.0),
                    "top_category": item.get("top_category", ""),
                    "delta_wait_ms_window": item.get("delta_wait_ms_window", 0),
                }
            )

        fieldnames = sorted({key for row in rows for key in row.keys()})
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _export_markdown(path: Path, payload: Dict[str, object]) -> None:
        summary = dict(payload.get("summary", {}) or {})
        signatures = list(payload.get("signatures", []) or [])
        top_waits = list(payload.get("top_waits", []) or [])
        trend = list(payload.get("trend", []) or [])
        baseline = dict(payload.get("baseline_comparison", {}) or {})
        wait_chain = dict(payload.get("wait_chain", {}) or {})
        alerts = list(payload.get("alerts", []) or [])
        comparative = dict(payload.get("before_after_comparison", {}) or {})
        custom_categories = dict(payload.get("custom_categories", {}) or {})
        multi_server = list(payload.get("multi_server", []) or [])
        plan_correlation = dict(payload.get("wait_plan_correlation", {}) or {})
        filters = dict(payload.get("filters", {}) or {})

        lines: List[str] = [
            "# Wait Statistics Export",
            "",
            f"- Generated: {payload.get('generated_at', '')}",
            f"- Trend Window: {payload.get('trend_window_days', 0)} days",
            "",
            "## Summary",
            "",
            f"- Total Wait Time (ms): {summary.get('total_wait_time_ms', 0):,}",
            f"- Signal Wait %: {summary.get('signal_wait_percent', 0.0):.2f}",
            f"- Resource Wait %: {summary.get('resource_wait_percent', 0.0):.2f}",
            "",
            "## Baseline Comparison",
            "",
            f"- Status: {baseline.get('status', 'n/a')}",
            f"- Notes: {baseline.get('summary', '')}",
            "",
            "## Before / After",
            "",
            f"- Status: {comparative.get('status', 'n/a')}",
            f"- Summary: {comparative.get('summary', '')}",
            "",
            "## Alerts",
            "",
        ]
        if alerts:
            for alert in alerts:
                lines.append(
                    f"- [{alert.get('severity', '').upper()}] **{alert.get('title', '')}**: {alert.get('message', '')}"
                )
        else:
            lines.append("- No active alerts.")

        lines.extend(
            [
                "",
                "## Wait Chain",
                "",
                f"- Summary: {wait_chain.get('summary', '')}",
                f"- Chains: {wait_chain.get('chain_count', 0)}",
                f"- Blocked Sessions: {wait_chain.get('total_blocked_sessions', 0)}",
                f"- Max Depth: {wait_chain.get('max_chain_depth', 0)}",
                "",
                "## Custom Categories",
                "",
            ]
        )
        custom_totals = dict(custom_categories.get("wait_time_ms_by_category", {}) or {})
        if custom_totals:
            for name, wait_ms in custom_totals.items():
                lines.append(f"- {name}: {int(wait_ms):,} ms")
        else:
            lines.append("- No custom category matches.")

        lines.extend(
            [
                "",
                "## Wait/Plan Correlation",
                "",
                f"- Query ID: {plan_correlation.get('query_id', 0)}",
                f"- Plan Available: {plan_correlation.get('plan_available', False)}",
                f"- Confidence: {float(plan_correlation.get('confidence', 0.0) or 0.0) * 100:.0f}%",
            ]
        )
        findings = list(plan_correlation.get("findings", []) or [])
        if findings:
            for finding in findings[:5]:
                lines.append(f"- {finding}")
        else:
            lines.append("- No correlation findings.")

        lines.extend(
            [
                "",
                "## Active Filters",
                "",
                f"- Database: {filters.get('database_name', '') or '*'}",
                f"- Application: {filters.get('application_name', '') or '*'}",
                f"- Time Window (days): {filters.get('time_window_days', 0)}",
                f"- Minimum Wait (ms): {filters.get('min_wait_time_ms', 0)}",
                "",
                "## Multi-Server Comparison",
                "",
            ]
        )
        if multi_server:
            lines.extend(
                [
                    "| Server | Database | Total Wait ms | Signal % | Top Category | Delta(ms) |",
                    "|---|---|---:|---:|---|---:|",
                ]
            )
            for item in multi_server[:20]:
                lines.append(
                    f"| {item.get('server', '')} | {item.get('database', '')} | "
                    f"{int(item.get('total_wait_time_ms', 0) or 0):,} | "
                    f"{float(item.get('signal_wait_percent', 0.0) or 0.0):.2f} | "
                    f"{item.get('top_category', '')} | "
                    f"{int(item.get('delta_wait_ms_window', 0) or 0):+,} |"
                )
        else:
            lines.append("- No multi-server data.")

        lines.extend(
            [
                "",
            "## Signatures",
            "",
            ]
        )
        if signatures:
            for sig in signatures:
                lines.extend(
                    [
                        f"- **{sig.get('title', '')}** ({float(sig.get('confidence', 0.0)) * 100:.0f}%): "
                        f"{sig.get('recommendation', '')}",
                    ]
                )
        else:
            lines.append("- No signatures.")

        lines.extend(
            [
                "",
                "## Top Waits",
                "",
                "| Wait Type | Category | Wait ms | Wait % |",
                "|---|---|---:|---:|",
            ]
        )
        for wait in top_waits:
            lines.append(
                f"| {wait.get('wait_type', '')} | {wait.get('category', '')} | "
                f"{int(wait.get('wait_time_ms', 0) or 0):,} | {float(wait.get('wait_percent', 0.0) or 0.0):.2f} |"
            )

        lines.extend(
            [
                "",
                "## Trend",
                "",
                "| Date | Total Wait ms | Dominant Category |",
                "|---|---:|---|",
            ]
        )
        for point in trend:
            lines.append(
                f"| {point.get('trend_date', '')} | {int(point.get('total_wait_ms', 0) or 0):,} | "
                f"{point.get('dominant_category', '')} |"
            )

        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))
    
    def _update_ui(self, summary: WaitSummary):
        """Update UI with new data"""
        total_wait_text = self._format_time(summary.total_wait_time_ms)
        if self._summary_value_labels:
            self._summary_value_labels["total_wait"].setText(total_wait_text)
            self._summary_value_labels["signal_wait"].setText(f"{summary.signal_wait_percent:.1f} %")
            self._summary_value_labels["resource_wait"].setText(f"{summary.resource_wait_percent:.1f} %")
            self._summary_value_labels["current_waits"].setText(str(len(summary.current_waits)))

            self._summary_value_labels["resource_wait"].setStyleSheet(
                f"color: {self._severity_color(summary.resource_wait_percent)}; "
                f"font-size: 12px; font-weight: 700; background: transparent;"
            )
            self._summary_value_labels["signal_wait"].setStyleSheet(
                f"color: {self._severity_color(summary.signal_wait_percent, warning=20.0, critical=35.0)}; "
                f"font-size: 12px; font-weight: 700; background: transparent;"
            )
            self._summary_value_labels["total_wait"].setStyleSheet(
                f"color: {self._severity_color(float(summary.total_wait_time_ms), warning=2_000_000, critical=8_000_000)}; "
                f"font-size: 12px; font-weight: 700; background: transparent;"
            )
            self._summary_value_labels["current_waits"].setStyleSheet(
                f"color: {self._severity_color(float(len(summary.current_waits)), warning=5, critical=12)}; "
                f"font-size: 12px; font-weight: 700; background: transparent;"
            )

        if self._summary_health_label is not None:
            if summary.resource_wait_percent >= 80.0:
                health_color = Colors.ERROR
                health_text = f"CRITICAL: Resource Wait {summary.resource_wait_percent:.1f}%"
            elif summary.resource_wait_percent >= 60.0:
                health_color = Colors.WARNING
                health_text = f"WARNING: Resource Wait {summary.resource_wait_percent:.1f}%"
            else:
                health_color = Colors.SUCCESS
                health_text = f"HEALTHY: Resource Wait {summary.resource_wait_percent:.1f}%"
            self._summary_health_label.setStyleSheet(
                f"color: {health_color}; font-size: 12px; font-weight: 800; background: transparent;"
            )
            self._summary_health_label.setText(health_text)

        category_stats = summary.category_stats or {}
        total_category_wait = max(1, sum(int(v or 0) for v in category_stats.values()))
        for category in self.CATEGORY_ORDER:
            wait_time = int(category_stats.get(category, 0) or 0)
            label = self._category_value_labels.get(category)
            if label is not None:
                label.setText(self._format_ms_compact(wait_time))
            pct = (float(wait_time) * 100.0) / float(total_category_wait)
            pct_label = self._category_percent_labels.get(category)
            if pct_label is not None:
                pct_label.setText(f"{pct:.1f}%")
                pct_label.setStyleSheet(
                    f"color: {self._severity_color(pct, warning=10.0, critical=20.0)}; "
                    f"font-size: 10px; font-weight: 700; background: transparent;"
                )
            bar = self._category_progress_bars.get(category)
            if bar is not None:
                bar.setValue(max(0, min(1000, int(round(pct * 10.0)))))

    @staticmethod
    def _severity_color(value: float, warning: float = 10.0, critical: float = 20.0) -> str:
        numeric = float(value or 0.0)
        if numeric >= float(critical):
            return Colors.ERROR
        if numeric >= float(warning):
            return Colors.WARNING
        return Colors.SUCCESS

    def _build_category_trend_series(self, trend_points: List[WaitTrendPoint]) -> Dict[str, List[int]]:
        series: Dict[str, List[int]] = {}
        for point in list(trend_points or []):
            cats = dict(point.category_wait_ms or {})
            for category_name, wait_ms in cats.items():
                key = str(resolve_wait_category_text(str(category_name)).value)
                series.setdefault(key, []).append(int(wait_ms or 0))
        return series

    def _render_action_plan(
        self,
        summary: WaitSummary,
        waits: List[WaitStat],
        alerts: List[WaitAlert],
        signatures: List[WaitSignature],
        baseline: WaitBaselineComparison,
        trend_points: List[WaitTrendPoint],
    ) -> None:
        if self._action_plan_label is None:
            return

        waits_list = list(waits or [])
        wait_name_set = {str(item.wait_type or "").upper() for item in waits_list}
        dominant_signature = signatures[0] if signatures else None
        io_pct = float(summary.category_stats.get(WaitCategory.IO, 0) or 0) * 100.0 / float(
            max(1, sum(int(v or 0) for v in (summary.category_stats or {}).values()))
        )

        root_causes: List[str] = []
        controls: List[str] = []
        quick_fixes: List[str] = []

        if io_pct >= 60.0 or (dominant_signature and dominant_signature.signature_id == "io_bottleneck"):
            root_causes.append(f"I/O bottleneck suspected (I/O share {io_pct:.1f}%).")
            controls.extend(
                [
                    "sp_BlitzFirst @SinceStartup=1 ile I/O pressure kontrol et.",
                    "sys.dm_io_virtual_file_stats ile file-level latency incele.",
                    "TempDB file count/autogrowth ve backup schedule overlap dogrula.",
                ]
            )
            quick_fixes.extend(
                [
                    "Backup compression etkinligini kontrol et.",
                    "Data/log auto-growth adimlarini buyut (kucuk artislardan kacin).",
                ]
            )

        if any(name.startswith(("BACKUPBUFFER", "BACKUPIO", "ASYNC_IO_COMPLETION")) for name in wait_name_set):
            root_causes.append("Backup/storage pipeline contention detected.")
            controls.extend(
                [
                    "Backup penceresinde concurrent job cakismalarini kontrol et.",
                    "Backup hedefi icin network throughput ve latency olc.",
                ]
            )
            quick_fixes.append("Backup joblarini zamanlayarak cakismayi azalt.")

        if any(name.startswith("WRITELOG") for name in wait_name_set):
            root_causes.append("WRITELOG pressure indicates transaction log latency risk.")
            controls.extend(
                [
                    "Log file disk latency ve queue depth degerlerini incele.",
                    "VLF sayisini kontrol et (DBCC LOGINFO / dm_db_log_info).",
                    "Log auto-growth boyutlandirmasini dogrula.",
                ]
            )
            quick_fixes.append("Log dosyasini hizli depolamaya tasi veya growth adimini optimize et.")

        if any(name.startswith("CX") for name in wait_name_set) and any(name.startswith("PAGELATCH") for name in wait_name_set):
            root_causes.append("Parallelism + latch contention overlap observed.")
            controls.append("MAXDOP ve cost threshold for parallelism degerlerini gozden gecir.")
            quick_fixes.append("Yuksek paralel queryler icin DOP limitini test et.")

        if baseline.baseline_available and baseline.delta_total_wait_ms > 0:
            root_causes.append(f"Degradation vs baseline: delta wait {baseline.delta_total_wait_ms:+,} ms.")
            controls.append("Before/After diff'i kategori bazinda dogrula.")

        if trend_points:
            latest = trend_points[-1]
            earliest = trend_points[0]
            if int(latest.total_wait_ms or 0) > int(earliest.total_wait_ms or 0):
                root_causes.append("Trend direction is increasing over selected window.")

        if not root_causes:
            root_causes.append("No dominant root cause auto-detected. Investigate top waits and active blockers.")
        if not controls:
            controls.append("Top waits icin Query Statistics ekraninda query correlation calistir.")
        if not quick_fixes:
            quick_fixes.append("Min Wait filtresini 100ms+ ile daraltip en yuksek impact satirlarini incele.")

        def _lines(items: List[str], numbered: bool = False) -> List[str]:
            out: List[str] = []
            for idx, item in enumerate(items[:5], start=1):
                prefix = f"{idx}. " if numbered else "- "
                out.append(f"{prefix}{item}")
            return out

        alert_head = "No active alert."
        if alerts:
            critical_count = sum(1 for alert in alerts if str(alert.severity).lower() == "critical")
            alert_head = f"Active Alerts: {len(alerts)} (critical={critical_count})"

        text_lines = [
            f"[Alert Detayi] {alert_head}",
            "",
            "[Muhtemel Kok Neden]",
            *_lines(root_causes),
            "",
            "[Onerilen Kontroller]",
            *_lines(controls, numbered=True),
            "",
            "[Hizli Fix Aksiyonlari]",
            *_lines(quick_fixes),
        ]
        self._action_plan_label.setText("\n".join(text_lines))

    def _update_waits_list(
        self,
        waits: List[WaitStat],
        trend_points: Optional[List[WaitTrendPoint]] = None,
        baseline: Optional[WaitBaselineComparison] = None,
        total_wait_ms: int = 0,
    ):
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

        waits_to_show = list(waits or [])[:15]
        trend_by_category = self._build_category_trend_series(trend_points or [])
        baseline_deltas = dict((baseline.delta_category_wait_ms if baseline else {}) or {})
        total_wait_ref = max(1, int(total_wait_ms or sum(int(w.wait_time_ms or 0) for w in waits_to_show) or 1))

        # Add wait rows
        for wait in waits_to_show:
            impact_score = (float(wait.wait_time_ms or 0) * float(wait.waiting_tasks or 0)) / float(total_wait_ref)
            category_key = str(wait.category.value)
            baseline_delta = float(baseline_deltas.get(category_key, 0) or 0)
            baseline_delta_pct = 0.0
            if wait.wait_time_ms and int(wait.wait_time_ms) > 0:
                baseline_delta_pct = (baseline_delta * 100.0) / float(max(1, int(wait.wait_time_ms)))
            row = WaitStatRow(
                wait,
                impact_score=impact_score,
                baseline_delta_pct=baseline_delta_pct,
                trend_series=trend_by_category.get(category_key, []),
            )
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

    def _format_ms_compact(self, ms: int) -> str:
        """Format milliseconds with compact K/M suffix for inline category text."""
        if ms >= 1_000_000:
            return f"{ms / 1_000_000:.1f}M ms"
        if ms >= 1_000:
            return f"{ms / 1_000:.1f}K ms"
        return f"{ms} ms"
