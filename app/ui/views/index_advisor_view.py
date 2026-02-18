"""
Index Advisor View - Deterministic index analysis with structured AI handoff.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from time import perf_counter
import json
from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QGraphicsDropShadowEffect,
    QPushButton, QSplitter, QTextEdit, QDialog, QScrollArea,
    QAbstractItemView, QMenu, QComboBox, QSlider, QCheckBox,
    QFileDialog, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QItemSelectionModel
from PyQt6.QtGui import QFont, QColor, QAction

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors, Theme
from app.ui.theme import Colors, Theme as ThemeStyles
from app.database.connection import get_connection_manager
from app.core.logger import get_logger
from app.models.analysis_context import AnalysisContext
from app.services.app_event_bus import get_app_event_bus
from app.services.missing_index_service import get_missing_index_service
from app.services.index_analyzer_service import (
    IndexAnalyzer,
    IndexAdvisorTelemetry,
    count_context_matches,
)
from app.ui.workers.ai_tune_worker import AITuneWorker
from app.ui.components.code_editor import CodeEditor

logger = get_logger("ui.index_advisor")


# Display / query limits
MAX_INDEX_ROWS = 200
MIN_INDEX_SCORE_EFFECTIVE = 75
MIN_INDEX_SCORE_WEAK = 50

class NumericTableWidgetItem(QTableWidgetItem):
    """Table item that sorts using a numeric value when provided."""

    def __init__(self, text: str, numeric_value: Optional[float] = None):
        super().__init__(text)
        self._numeric_value = numeric_value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            if self._numeric_value is not None and other._numeric_value is not None:
                return self._numeric_value < other._numeric_value
        return super().__lt__(other)


class SummaryStatTile(QFrame):
    """Square summary stat tile for footer (Blocking Analysis style)."""

    SCALE = 0.62
    BASE_TILE_SIZE = 98
    BASE_VALUE_FONT_SIZE = 18
    BASE_TITLE_FONT_SIZE = 10

    def __init__(self, title: str, value: str, accent: str = "#6366f1", parent=None):
        super().__init__(parent)
        self._accent = str(accent or Colors.PRIMARY)
        self._setup_ui(title, value)

    def _setup_ui(self, title: str, value: str) -> None:
        self.setStyleSheet("background-color: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        tile = QFrame()
        tile_size = max(28, int(self.BASE_TILE_SIZE * self.SCALE))
        tile.setFixedSize(tile_size, tile_size)
        tile.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: {max(6, min(12, int(tile_size * 0.2)))}px;
            }}
        """)
        tile_layout = QVBoxLayout(tile)
        tile_layout.setContentsMargins(0, 0, 0, 0)
        tile_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._value_label = QLabel(str(value))
        value_font_size = max(11, int(self.BASE_VALUE_FONT_SIZE * self.SCALE))
        self._value_label.setStyleSheet(
            f"color: {self._accent}; font-size: {value_font_size}px; font-weight: 700; background: transparent; border: none;"
        )
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile_layout.addWidget(self._value_label)

        self._title_label = QLabel(str(title))
        title_font_size = max(9, int(self.BASE_TITLE_FONT_SIZE * self.SCALE))
        self._title_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: {title_font_size}px; font-weight: 700; background: transparent;"
        )
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setWordWrap(True)

        layout.addWidget(tile, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._title_label, alignment=Qt.AlignmentFlag.AlignHCenter)

    def update_value(self, value: str, accent: str = None) -> None:
        self._value_label.setText(str(value))
        if accent:
            self.set_accent(str(accent))

    def set_accent(self, accent: str) -> None:
        self._accent = str(accent or self._accent)
        value_font_size = max(11, int(self.BASE_VALUE_FONT_SIZE * self.SCALE))
        self._value_label.setStyleSheet(
            f"color: {self._accent}; font-size: {value_font_size}px; font-weight: 700; background: transparent; border: none;"
        )


class IndexRefreshWorker(QThread):
    """Main index collection + deterministic analysis in background."""

    progress_updated = pyqtSignal(int, str)  # (percent, message)
    refresh_completed = pyqtSignal(list)  # analyzed results
    refresh_failed = pyqtSignal(str)
    telemetry_captured = pyqtSignal(object)  # IndexAdvisorTelemetry

    def __init__(
        self,
        connection: Any,
        analyzer: IndexAnalyzer,
        context: Optional[AnalysisContext] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._connection = connection
        self._analyzer = analyzer
        self._context = context

    def run(self) -> None:
        started = perf_counter()
        fallback_used = False
        try:
            self.progress_updated.emit(10, "Collecting index metadata...")
            try:
                results = self._connection.execute_query(IndexAdvisorView._build_index_collection_query())
            except Exception as ex:
                fallback_used = True
                logger.warning(f"Primary index collection query failed, trying legacy fallback: {ex}")
                self.progress_updated.emit(25, "Primary query failed, switching to legacy fallback...")
                results = self._connection.execute_query(IndexAdvisorView._build_index_collection_query_legacy())

            rows_collected = len(results or [])
            self.progress_updated.emit(60, f"Running deterministic analysis for {rows_collected} rows...")
            analyzed, timings = self._analyzer.analyze_with_timings(results or [])

            telemetry = IndexAdvisorTelemetry(
                load_duration_ms=int((perf_counter() - started) * 1000),
                rows_collected=rows_collected,
                rows_analyzed=len(analyzed),
                fallback_used=fallback_used,
                context_match_count=count_context_matches(analyzed, self._context),
                duplicate_detection_duration_ms=int(timings.get("duplicate_detection_duration_ms", 0) or 0),
                classification_duration_ms=int(timings.get("classification_duration_ms", 0) or 0),
            )
            self.telemetry_captured.emit(telemetry)
            self.progress_updated.emit(100, f"Completed analysis for {len(analyzed)} indexes.")
            self.refresh_completed.emit(analyzed)
        except Exception as ex:
            self.refresh_failed.emit(str(ex))


class IndexUsageTrendWorker(QThread):
    """Background worker for Query Store based index usage trend."""

    trend_loaded = pyqtSignal(str, object)  # request_key, rows
    trend_failed = pyqtSignal(str, str)  # request_key, error

    def __init__(self, connection: Any, index_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._connection = connection
        self._index_data = dict(index_data or {})
        self._request_key = f"{self._index_data.get('TableName', '')}|{self._index_data.get('IndexName', '')}"

    def run(self) -> None:
        try:
            table_full = str(self._index_data.get("TableName", "") or "")
            if "." in table_full:
                schema_name, table_name = table_full.split(".", 1)
            else:
                schema_name, table_name = "dbo", table_full
            index_name = str(self._index_data.get("IndexName", "") or "")
            if not table_name or not index_name:
                self.trend_loaded.emit(self._request_key, [])
                return

            query = """
            DECLARE @schema_name NVARCHAR(256) = :schema_name;
            DECLARE @table_name  NVARCHAR(256) = :table_name;
            DECLARE @index_name  NVARCHAR(256) = :index_name;

            WITH plan_stats AS (
                SELECT
                    CAST(rs.last_execution_time AS DATE) AS execution_day,
                    rs.count_executions,
                    rs.avg_logical_io_reads,
                    TRY_CAST(p.query_plan AS XML) AS plan_xml
                FROM sys.query_store_runtime_stats rs
                JOIN sys.query_store_plan p ON rs.plan_id = p.plan_id
                WHERE rs.last_execution_time >= DATEADD(DAY, -30, SYSUTCDATETIME())
            )
            SELECT
                execution_day AS [day],
                SUM(CAST(count_executions AS BIGINT)) AS executions,
                SUM(CAST(avg_logical_io_reads * count_executions AS FLOAT)) AS total_reads
            FROM plan_stats
            WHERE
                plan_xml IS NOT NULL
                AND plan_xml.exist('//*[local-name()=\"Object\"
                    and (@Schema = sql:variable(\"@schema_name\") or @Schema = concat(\"[\", sql:variable(\"@schema_name\"), \"]\"))
                    and (@Table  = sql:variable(\"@table_name\")  or @Table  = concat(\"[\", sql:variable(\"@table_name\"),  \"]\"))
                    and (@Index  = sql:variable(\"@index_name\")  or @Index  = concat(\"[\", sql:variable(\"@index_name\"),  \"]\"))
                ]') = 1
            GROUP BY execution_day
            ORDER BY execution_day
            OPTION (RECOMPILE);
            """
            rows = self._connection.execute_query(
                query,
                {
                    "schema_name": schema_name,
                    "table_name": table_name,
                    "index_name": index_name,
                },
            ) or []
            self.trend_loaded.emit(self._request_key, rows)
        except Exception as ex:
            self.trend_failed.emit(self._request_key, str(ex))


class IndexAnalysisWorker(QThread):
    """Background worker for AI index analysis on pre-classified JSON."""
    
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, index_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.index_data = index_data
    
    def run(self):
        import asyncio
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._analyze())
                self.finished.emit(result)
            finally:
                loop.close()
        except Exception as e:
            self.error.emit(str(e))
    
    async def _analyze(self) -> str:
        """Analyze pre-classified index output with AI."""
        from app.ai.analysis_service import AIAnalysisService
         
        try:
            service = AIAnalysisService()
            sql_version = service._get_sql_version_string()
            from app.ai.prompts.rules import apply_template, resolve_active_locale
            from app.ai.prompts.yaml_store import PromptRulesStore

            locale = resolve_active_locale()
            store = PromptRulesStore()
            global_instructions = store.load_rule(locale, "global").user.strip()
            rule = store.load_rule(locale, "index_analysis_preclassified")
            system_tmpl = rule.system
            instruction_tmpl = rule.user
            tmpl_values = {
                "global_instructions": global_instructions,
                "sql_version": sql_version or "",
            }
            system_prompt = apply_template(system_tmpl, tmpl_values).strip()
            instruction_prompt = apply_template(instruction_tmpl, tmpl_values).strip()
 
            user_payload = {
                "request_type": "index_analysis_preclassified",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "sql_version": sql_version,
                "index": self.index_data,
                "instruction_prompt": instruction_prompt,
                "output_contract": {
                    "format": "markdown",
                    "sections": [
                        "Executive Summary",
                        "Classification Rationale",
                        "Priority Actions (Immediate vs Follow-up)",
                        "Risks and Trade-offs",
                    ],
                },
            }
 
            response = await service.llm_client.generate(
                prompt=json.dumps(user_payload, ensure_ascii=False),
                system_prompt=system_prompt,
                provider_id=service.provider_id,
                temperature=0.1,
                max_tokens=3000,
            )
            validation = service.response_validator.validate(response)
            sanitized = validation.sanitized_response
            sanitized = service._append_version_compat_notes(sanitized, validation)
            return sanitized
        except Exception:
            return self._generate_fallback()
    
    def _generate_fallback(self) -> str:
        d = self.index_data
        idx = d.get("IndexName", "N/A")
        table = d.get("TableName", "N/A")
        score = int(d.get("Score", 0) or 0)
        cls = d.get("Classification", "WEAK")
        cls_reason = d.get("ClassificationReason", "")
        flags = d.get("Flags", [])
        warnings = d.get("Warnings", [])
        recs = d.get("ComputedRecommendations", [])

        lines = [
            "## Deterministic Index Analysis (Fallback)",
            "",
            f"- **Index:** {idx}",
            f"- **Table:** {table}",
            f"- **Classification:** {cls}",
            f"- **Classification Reason:** {cls_reason}",
            f"- **Score:** {score}/100",
            "",
            "### Flags",
        ]
        if flags:
            lines.extend([f"- {f}" for f in flags])
        else:
            lines.append("- (none)")

        lines.append("")
        lines.append("### Warnings")
        if warnings:
            lines.extend([f"- {w}" for w in warnings])
        else:
            lines.append("- (none)")

        lines.append("")
        lines.append("### Computed Recommendations")
        if recs:
            lines.extend([f"- {r}" for r in recs])
        else:
            lines.append("- MONITOR_AND_KEEP")
        return "\n".join(lines)


class IndexAdvisorView(BaseView):
    """Index Advisor view with modern enterprise design and AI analysis"""

    uses_app_event_bus_context = True
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._all_indexes: List[Dict[str, Any]] = []
        self._current_indexes: List[Dict] = []
        self._analyzer = IndexAnalyzer()
        self._refresh_worker: Optional[IndexRefreshWorker] = None
        self._trend_worker: Optional[IndexUsageTrendWorker] = None
        self._ai_worker: Optional[QThread] = None
        self._ai_stream_buffer: str = ""
        self._trend_rows_by_key: Dict[str, List[Dict[str, Any]]] = {}
        self._trend_request_key: str = ""
        self._last_telemetry: Optional[IndexAdvisorTelemetry] = None
        self._missing_index_service = get_missing_index_service()
        self._analysis_context: Optional[AnalysisContext] = None
        get_app_event_bus().signals.query_analyzed.connect(self._on_query_analyzed_event)
    
    @property
    def view_title(self) -> str:
        return "Index Advisor"
    
    def _setup_ui(self):
        # Keep whitespace consistent with card surfaces (avoid visible gray bands).
        self.setStyleSheet(f"background-color: {Colors.SURFACE};")
        
        # Title section
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(16)
        
        # Title and subtitle
        title_text_layout = QVBoxLayout()
        title_text_layout.setSpacing(4)
        
        self.status_label = QLabel("Connect to a database")
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        self.status_label.setFont(QFont("Segoe UI", 13))
        title_text_layout.addWidget(self.status_label)

        self._context_label = QLabel("")
        self._context_label.setVisible(False)
        self._context_label.setStyleSheet(
            f"color: {Colors.PRIMARY}; font-size: 12px; background: transparent;"
        )
        title_text_layout.addWidget(self._context_label)
        
        title_layout.addLayout(title_text_layout)
        title_layout.addStretch()
        
        # Refresh button
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.setStyleSheet(self._primary_button_style(padding="10px 20px", border_radius=8, font_size=13))
        self._refresh_btn.clicked.connect(self.refresh)
        title_layout.addWidget(self._refresh_btn)
        
        self._main_layout.addWidget(title_container)
        self._main_layout.addSpacing(12)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: transparent; }")
        
        # Left: Table card
        table_card = QFrame()
        table_card.setObjectName("tableCard")
        table_card.setStyleSheet(f"""
            QFrame#tableCard {{
                background-color: {Colors.SURFACE};
                border-radius: 16px;
                border: 1px solid {Colors.BORDER};
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(15, 23, 42, 15))
        table_card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)
        
        # Card header
        card_header = QLabel("Deterministic Index Analysis")
        card_header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: 600;")
        card_layout.addWidget(card_header)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        table_filter_label = QLabel("Table:")
        table_filter_label.setStyleSheet(self._filter_label_style())
        filter_row.addWidget(table_filter_label)
        self._table_filter = QComboBox()
        self._table_filter.setMinimumWidth(180)
        self._table_filter.addItem("All")
        self._table_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self._table_filter)
        self._table_filter.setStyleSheet(ThemeStyles.combobox_style())
        class_filter_label = QLabel("Class:")
        class_filter_label.setStyleSheet(self._filter_label_style())
        filter_row.addWidget(class_filter_label)
        self._class_filter = QComboBox()
        self._class_filter.setMinimumWidth(150)
        self._class_filter.addItem("All")
        self._class_filter.addItems(
            ["EFFECTIVE", "EFFECTIVE_MANDATORY", "WEAK", "WEAK_BUT_NECESSARY_FK", "NEEDS_MAINTENANCE", "UNNECESSARY"]
        )
        self._class_filter.setStyleSheet(ThemeStyles.combobox_style())
        self._class_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self._class_filter)

        score_filter_label = QLabel("Score ≥")
        score_filter_label.setStyleSheet(self._filter_label_style())
        filter_row.addWidget(score_filter_label)
        self._score_filter = QSlider(Qt.Orientation.Horizontal)
        self._score_filter.setRange(0, 100)
        self._score_filter.setValue(0)
        self._score_filter.setStyleSheet(self._slider_style())
        self._score_filter.valueChanged.connect(self._on_score_filter_changed)
        filter_row.addWidget(self._score_filter, 1)
        self._score_filter_label = QLabel("0")
        self._score_filter_label.setMinimumWidth(24)
        self._score_filter_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 700;")
        filter_row.addWidget(self._score_filter_label)

        self._needs_attention_only = QCheckBox("Needs Attention Only")
        self._needs_attention_only.setStyleSheet(self._checkbox_style())
        self._needs_attention_only.setChecked(True)
        self._needs_attention_only.stateChanged.connect(self._apply_filters)
        filter_row.addWidget(self._needs_attention_only)
        card_layout.addLayout(filter_row)
        
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Table", "Index", "Class", "Score", "Read/Write", "Frag %", "Seeks", "Writes"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setFixedHeight(32)
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.itemClicked.connect(self._on_index_selected)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.SURFACE};
                border: none;
                gridline-color: {Colors.BORDER};
                color: {Colors.TEXT_PRIMARY};
                outline: 0;
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QTableWidget::item:focus {{
                outline: none;
                border: none;
            }}
            QTableWidget::item:hover {{
                background-color: rgba(14, 138, 157, 0.06);
            }}
            QTableWidget::item:selected {{
                background-color: rgba(14, 138, 157, 0.14);
                color: {Colors.PRIMARY};
            }}
            QTableWidget::item:selected:focus {{
                outline: none;
                border: none;
            }}
            QTableWidget::item:selected:hover {{
                background-color: rgba(14, 138, 157, 0.14);
            }}
            QTableCornerButton::section {{
                background-color: {Colors.SURFACE};
                border: none;
                border-bottom: 2px solid {Colors.BORDER};
            }}
            QHeaderView::section {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_SECONDARY};
                padding: 6px 8px;
                border: none;
                border-bottom: 2px solid {Colors.BORDER};
                font-weight: 600;
                font-size: 12px;
            }}
        """)
        card_layout.addWidget(self.table)

        # Batch actions
        batch_row = QHBoxLayout()
        batch_row.setSpacing(10)
        self._select_needs_action = QCheckBox("Select All Needs Action")
        self._select_needs_action.setStyleSheet(self._checkbox_style())
        self._select_needs_action.stateChanged.connect(self._on_select_needs_action_changed)
        batch_row.addWidget(self._select_needs_action)

        self._batch_script_btn = QPushButton("Generate Maintenance Script")
        self._batch_script_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._batch_script_btn.setStyleSheet(self._secondary_button_style())
        self._batch_script_btn.clicked.connect(self._generate_batch_script_from_selection)
        batch_row.addWidget(self._batch_script_btn)

        self._export_report_btn = QPushButton("Export Analysis Report")
        self._export_report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._export_report_btn.setStyleSheet(self._secondary_button_style())
        self._export_report_btn.clicked.connect(self._export_analysis_report)
        batch_row.addWidget(self._export_report_btn)
        batch_row.addStretch()
        card_layout.addLayout(batch_row)
        
        splitter.addWidget(table_card)
        
        # Right: Detail panel
        detail_card = QFrame()
        detail_card.setObjectName("detailCard")
        detail_card.setStyleSheet(f"""
            QFrame#detailCard {{
                background-color: {Colors.SURFACE};
                border-radius: 16px;
                border: 1px solid {Colors.BORDER};
            }}
        """)
        
        detail_shadow = QGraphicsDropShadowEffect()
        detail_shadow.setBlurRadius(20)
        detail_shadow.setXOffset(0)
        detail_shadow.setYOffset(4)
        detail_shadow.setColor(QColor(15, 23, 42, 15))
        detail_card.setGraphicsEffect(detail_shadow)
        
        detail_layout = QVBoxLayout(detail_card)
        detail_layout.setContentsMargins(20, 20, 20, 20)
        detail_layout.setSpacing(12)
        
        # Detail header
        detail_header = QLabel("Index Details")
        detail_header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: 600;")
        detail_layout.addWidget(detail_header)

        details_tabs = QTabWidget()
        details_tabs.setStyleSheet(
            self._detail_tabs_style()
            + f"""
            QTabWidget {{
                background-color: transparent;
            }}
            QTabBar {{
                background-color: transparent;
            }}
            """
        )

        # Tab 1: Script
        script_tab = QWidget()
        script_tab.setStyleSheet("background: transparent;")
        script_layout = QVBoxLayout(script_tab)
        script_layout.setContentsMargins(12, 12, 12, 12)
        script_layout.setSpacing(10)
        self._script_text = CodeEditor(theme_override="light")
        self._script_text.setReadOnly(True)
        self._script_text.set_text("-- Select an index...")
        script_layout.addWidget(self._script_text, 1)
        copy_btn = QPushButton("Copy Script")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(self._secondary_button_style())
        copy_btn.clicked.connect(self._copy_script)
        script_layout.addWidget(copy_btn)
        details_tabs.addTab(script_tab, "Script")

        # Tab 2: Metrics
        metrics_tab = QWidget()
        metrics_tab.setStyleSheet("background: transparent;")
        metrics_layout = QVBoxLayout(metrics_tab)
        metrics_layout.setContentsMargins(12, 12, 12, 12)
        metrics_layout.setSpacing(10)
        self._metrics_text = QTextEdit()
        self._metrics_text.setReadOnly(True)
        self._metrics_text.setPlaceholderText("Select an index to view current metrics...")
        self._metrics_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-size: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
            }}
        """)
        metrics_layout.addWidget(self._metrics_text, 1)
        details_tabs.addTab(metrics_tab, "Metrics")

        # Tab 3: AI Analysis
        ai_tab = QWidget()
        ai_tab.setStyleSheet("background: transparent;")
        ai_layout = QVBoxLayout(ai_tab)
        ai_layout.setContentsMargins(12, 12, 12, 12)
        ai_layout.setSpacing(10)
        ai_header = QHBoxLayout()
        ai_label = QLabel("AI Analysis")
        ai_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
        ai_header.addWidget(ai_label)
        self._ai_btn = QPushButton("Analyze")
        self._ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ai_btn.setStyleSheet(self._primary_button_style(padding="6px 14px", border_radius=6, font_size=12))
        self._ai_btn.clicked.connect(self._run_ai_analysis)
        ai_header.addWidget(self._ai_btn)
        ai_header.addStretch()
        ai_layout.addLayout(ai_header)
        self._ai_result = QTextEdit()
        self._ai_result.setReadOnly(True)
        self._ai_result.setPlaceholderText("Select an index and click 'Analyze'...")
        self._ai_result.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }}
        """)
        ai_layout.addWidget(self._ai_result, 1)
        details_tabs.addTab(ai_tab, "AI Analysis")

        # Tab 4: History
        history_tab = QWidget()
        history_tab.setStyleSheet("background: transparent;")
        history_layout = QVBoxLayout(history_tab)
        history_layout.setContentsMargins(12, 12, 12, 12)
        history_layout.setSpacing(10)
        self._trend_text = QTextEdit()
        self._trend_text.setReadOnly(True)
        self._trend_text.setPlaceholderText("Select an index to load usage trend...")
        self._trend_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
            }}
        """)
        history_layout.addWidget(self._trend_text, 1)
        details_tabs.addTab(history_tab, "History")

        detail_layout.addWidget(details_tabs, 1)
        
        splitter.addWidget(detail_card)
        splitter.setSizes([600, 400])

        self._main_layout.addWidget(splitter, 1)

        # Footer summary cards (bottom-right) like Blocking Analysis
        self._total_card = self._create_summary_card("Total Indexes", "0", Colors.PRIMARY)
        self._high_impact_card = self._create_summary_card("Needs Action", "0", Colors.WARNING)
        self._estimated_gain_card = self._create_summary_card("Average Score", "0", Colors.SUCCESS)

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(12)
        footer_layout.addStretch(1)

        summary_container = QWidget()
        summary_layout = QHBoxLayout(summary_container)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(12)
        summary_layout.addWidget(self._total_card)
        summary_layout.addWidget(self._high_impact_card)
        summary_layout.addWidget(self._estimated_gain_card)

        footer_layout.addWidget(
            summary_container,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        self._main_layout.addLayout(footer_layout)

    @staticmethod
    def _filter_label_style() -> str:
        return f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"

    @staticmethod
    def _checkbox_style() -> str:
        return (
            f"QCheckBox {{ color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600; }}"
            f"QCheckBox:hover {{ color: {Colors.TEXT_PRIMARY}; }}"
            f"QCheckBox:disabled {{ color: {Colors.TEXT_MUTED}; }}"
        )

    @staticmethod
    def _secondary_button_style() -> str:
        return f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 7px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                color: {Colors.PRIMARY};
                border: 1px solid {Colors.PRIMARY};
                background-color: #f8fafc;
            }}
            QPushButton:pressed {{
                background-color: #eef2ff;
            }}
            QPushButton:disabled {{
                color: {Colors.TEXT_MUTED};
                background-color: #f8fafc;
                border: 1px solid {Colors.BORDER};
            }}
        """

    @staticmethod
    def _primary_button_style(padding: str = "8px 16px", border_radius: int = 6, font_size: int = 12) -> str:
        return f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {int(border_radius)}px;
                padding: {padding};
                font-size: {int(font_size)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton:disabled {{
                background-color: {Colors.BORDER};
                color: {Colors.TEXT_MUTED};
            }}
        """

    @staticmethod
    def _detail_tabs_style() -> str:
        return ThemeStyles.tab_widget_style()

    @staticmethod
    def _menu_style() -> str:
        return f"""
            QMenu {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                color: {Colors.TEXT_PRIMARY};
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: #f8fafc;
                color: {Colors.PRIMARY};
            }}
        """

    @staticmethod
    def _slider_style() -> str:
        return f"""
            QSlider::groove:horizontal {{
                border: 1px solid {Colors.BORDER};
                height: 6px;
                background: {Colors.SURFACE};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {Colors.PRIMARY_LIGHT};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {Colors.PRIMARY};
                border: 1px solid {Colors.PRIMARY_HOVER};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {Colors.PRIMARY_HOVER};
            }}
        """
    
    def _create_summary_card(self, title: str, value: str, color: str) -> SummaryStatTile:
        return SummaryStatTile(title, value, color)

    def _update_summary_card(self, card: SummaryStatTile, value: str):
        """Update summary card value"""
        card.update_value(value)
    
    def on_show(self):
        if not self._is_initialized:
            return
        if self._analysis_context is None:
            cached_ctx = self._missing_index_service.get_last_context()
            if cached_ctx is not None:
                self._analysis_context = cached_ctx
                self._context_label.setVisible(True)
                self._context_label.setText(
                    f"Focus context: {cached_ctx.object_full_name or 'Query ' + str(cached_ctx.query_id)}"
                )
        self.refresh()

    def receive_analysis_context(self, context: AnalysisContext) -> None:
        """Receive cross-module context and focus this view on relevant object indexes."""
        self._analysis_context = context
        self._missing_index_service.receive_context(context)
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
        if str(getattr(context, "target_module", "") or "").strip() != "index_advisor":
            return
        self.receive_analysis_context(context)

    @staticmethod
    def _normalize_name(value: str) -> str:
        return str(value or "").strip().lower().replace("[", "").replace("]", "")

    def _matches_context(self, idx_data: Dict, context: AnalysisContext) -> bool:
        table_name = self._normalize_name(idx_data.get("TableName", ""))
        object_name = self._normalize_name(context.object_name)
        object_full_name = self._normalize_name(context.object_full_name)
        if not table_name:
            return False
        if object_full_name and table_name == object_full_name:
            return True
        if object_name and (table_name == object_name or table_name.endswith(f".{object_name}")):
            return True
        return False
        
    def refresh(self):
        if not self._is_initialized:
            return
        conn = get_connection_manager().active_connection
        if not conn or not conn.is_connected:
            self.status_label.setText("Please connect to a database first.")
            self.status_label.setStyleSheet(f"color: {Colors.WARNING}; font-size: 14px; background: transparent;")
            return
        if self._refresh_worker and self._refresh_worker.isRunning():
            self.status_label.setText("Refresh already in progress...")
            self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 14px; background: transparent;")
            return

        self.set_loading(True)
        self._refresh_btn.setEnabled(False)
        self.status_label.setText(f"Deterministic index analysis for {conn.profile.database}...")
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 14px; background: transparent;")

        self._refresh_worker = IndexRefreshWorker(
            connection=conn,
            analyzer=self._analyzer,
            context=self._analysis_context,
            parent=self,
        )
        self._refresh_worker.progress_updated.connect(self._on_refresh_progress)
        self._refresh_worker.refresh_completed.connect(self._on_refresh_completed)
        self._refresh_worker.refresh_failed.connect(self._on_refresh_failed)
        self._refresh_worker.telemetry_captured.connect(self._on_refresh_telemetry)
        self._refresh_worker.finished.connect(self._on_refresh_worker_finished)
        self._refresh_worker.start()

    def _on_refresh_progress(self, percent: int, message: str) -> None:
        self.status_label.setText(f"{message} ({int(percent)}%)")
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 14px; background: transparent;")

    def _on_refresh_telemetry(self, telemetry_obj: object) -> None:
        telemetry = telemetry_obj if isinstance(telemetry_obj, IndexAdvisorTelemetry) else None
        if telemetry is None:
            return
        self._last_telemetry = telemetry
        logger.info(
            "IndexAdvisor telemetry "
            f"[load_ms={telemetry.load_duration_ms}, rows_collected={telemetry.rows_collected}, "
            f"rows_analyzed={telemetry.rows_analyzed}, fallback={telemetry.fallback_used}, "
            f"context_matches={telemetry.context_match_count}, duplicate_ms={telemetry.duplicate_detection_duration_ms}, "
            f"classification_ms={telemetry.classification_duration_ms}]"
        )

    @staticmethod
    def _class_display(classification: str) -> str:
        cls = str(classification or "").upper()
        return cls

    @staticmethod
    def _is_needs_attention(idx_data: Dict[str, Any]) -> bool:
        classification = str(idx_data.get("Classification", "") or "")
        score = int(idx_data.get("Score", 0) or 0)
        return classification in {"UNNECESSARY", "NEEDS_MAINTENANCE"} or score < MIN_INDEX_SCORE_WEAK

    def _on_score_filter_changed(self, value: int) -> None:
        self._score_filter_label.setText(str(int(value)))
        self._apply_filters()

    def _populate_table_filter_values(self, indexes: List[Dict[str, Any]]) -> None:
        current_text = self._table_filter.currentText()
        self._table_filter.blockSignals(True)
        self._table_filter.clear()
        self._table_filter.addItem("All")
        table_names = sorted({str(x.get("TableName", "") or "") for x in indexes if str(x.get("TableName", "") or "").strip()})
        self._table_filter.addItems(table_names)
        idx = self._table_filter.findText(current_text)
        self._table_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self._table_filter.blockSignals(False)

    def _filter_indexes(self, indexes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        table_name = str(self._table_filter.currentText() or "All")
        class_name = str(self._class_filter.currentText() or "All")
        min_score = int(self._score_filter.value())
        needs_attention_only = bool(self._needs_attention_only.isChecked())

        filtered: List[Dict[str, Any]] = []
        for item in indexes:
            if table_name != "All" and str(item.get("TableName", "")) != table_name:
                continue
            if class_name != "All" and str(item.get("Classification", "")) != class_name:
                continue
            if int(item.get("Score", 0) or 0) < min_score:
                continue
            if needs_attention_only and not self._is_needs_attention(item):
                continue
            filtered.append(item)
        return filtered

    def _render_table(self, indexes: List[Dict[str, Any]]) -> None:
        self._current_indexes = list(indexes or [])
        self.table.setRowCount(len(self._current_indexes))
        self.table.setSortingEnabled(False)

        for i, idx_data in enumerate(self._current_indexes):
            score = int(idx_data.get("Score", 0) or 0)
            metrics = idx_data.get("Metrics", {}) or {}
            props = idx_data.get("Properties", {}) or {}
            ratio = float(metrics.get("ReadWriteRatio", 0) or 0)
            frag = float(metrics.get("FragmentationPercent", 0) or 0)
            seeks = int(metrics.get("UserSeeks", 0) or 0)
            writes = int(metrics.get("UserUpdates", 0) or 0)
            classification = str(idx_data.get("Classification", "WEAK"))
            cls_reason = str(idx_data.get("ClassificationReason", "") or "")

            table_item = QTableWidgetItem(str(idx_data.get("TableName", "")))
            index_item = QTableWidgetItem(str(idx_data.get("IndexName", "")))
            class_item = QTableWidgetItem(self._class_display(classification))
            class_item.setToolTip(f"{classification}\nReason: {cls_reason or '(none)'}")
            score_item = NumericTableWidgetItem(f"{score}", float(score))
            ratio_item = NumericTableWidgetItem(f"{ratio:.2f}", float(ratio))
            frag_item = NumericTableWidgetItem(f"{frag:.2f}", float(frag))
            seeks_item = NumericTableWidgetItem(f"{seeks:,}", float(seeks))
            writes_item = NumericTableWidgetItem(f"{writes:,}", float(writes))

            for cell in [table_item, index_item, class_item, score_item, ratio_item, frag_item, seeks_item, writes_item]:
                cell.setData(Qt.ItemDataRole.UserRole, idx_data)

            if score >= MIN_INDEX_SCORE_EFFECTIVE:
                score_item.setForeground(QColor(Colors.SUCCESS))
            elif score >= MIN_INDEX_SCORE_WEAK:
                score_item.setForeground(QColor(Colors.WARNING))
            else:
                score_item.setForeground(QColor(Colors.ERROR))

            if classification in {"UNNECESSARY", "NEEDS_MAINTENANCE"}:
                class_item.setForeground(QColor(Colors.WARNING))
            elif classification in {"EFFECTIVE_MANDATORY", "EFFECTIVE"}:
                class_item.setForeground(QColor(Colors.SUCCESS))
            elif classification in {"WEAK", "WEAK_BUT_NECESSARY_FK"}:
                class_item.setForeground(QColor("#F97316"))

            key_cols = ", ".join(props.get("KeyColumns", [])[:3]) if isinstance(props.get("KeyColumns"), list) else ""
            if key_cols:
                table_item.setToolTip(f"Key Columns: {key_cols}")

            self.table.setItem(i, 0, table_item)
            self.table.setItem(i, 1, index_item)
            self.table.setItem(i, 2, class_item)
            self.table.setItem(i, 3, score_item)
            self.table.setItem(i, 4, ratio_item)
            self.table.setItem(i, 5, frag_item)
            self.table.setItem(i, 6, seeks_item)
            self.table.setItem(i, 7, writes_item)

            numeric_font = QFont("Segoe UI", 10)
            score_item.setFont(numeric_font)
            ratio_item.setFont(numeric_font)
            frag_item.setFont(numeric_font)
            seeks_item.setFont(numeric_font)
            writes_item.setFont(numeric_font)

        filtered_count = len(self._current_indexes)
        needs_action_count = sum(1 for x in self._current_indexes if self._is_needs_attention(x))
        total_score = sum(int(x.get("Score", 0) or 0) for x in self._current_indexes)
        avg_score = (total_score / filtered_count) if filtered_count else 0
        self._update_summary_card(self._total_card, str(filtered_count))
        self._update_summary_card(self._high_impact_card, str(needs_action_count))
        self._update_summary_card(self._estimated_gain_card, f"{avg_score:.0f}")
        self.table.setSortingEnabled(True)

    def _apply_filters(self, *_args) -> None:
        filtered = self._filter_indexes(self._all_indexes)
        self._render_table(filtered)

    def _on_refresh_completed(self, analyzed: List[Dict[str, Any]]) -> None:
        self._all_indexes = list(analyzed or [])
        self._populate_table_filter_values(self._all_indexes)
        self._apply_filters()

        if self._analysis_context:
            focused = self._missing_index_service.filter_indexes_for_context(
                self._all_indexes,
                self._analysis_context,
            )
            if focused and self._select_index_in_table(focused[0]):
                self.status_label.setText(
                    f"Focused on {self._analysis_context.object_full_name} "
                    f"({len(focused)} matching indexes)"
                )
            else:
                self.status_label.setText(
                    f"Loaded {len(self._current_indexes)} indexes - no direct match for "
                    f"{self._analysis_context.object_full_name}"
                )
        elif self._last_telemetry:
            self.status_label.setText(
                f"Loaded {len(self._current_indexes)} indexes in {self._last_telemetry.load_duration_ms} ms"
            )
        else:
            self.status_label.setText(f"Deterministic index analysis loaded ({len(self._current_indexes)} indexes)")

        self.status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 14px; background: transparent;")

    @staticmethod
    def _build_sparkline(values: List[float]) -> str:
        if not values:
            return "(no historical data)"
        blocks = "▁▂▃▄▅▆▇█"
        mn = min(values)
        mx = max(values)
        if mx <= mn:
            return blocks[3] * len(values)
        chars: List[str] = []
        for val in values:
            pos = int(((val - mn) / (mx - mn)) * (len(blocks) - 1))
            chars.append(blocks[max(0, min(len(blocks) - 1, pos))])
        return "".join(chars)

    def _extract_index_payload(self, item: Optional[QTableWidgetItem]) -> Optional[Dict[str, Any]]:
        if item is None:
            return None
        payload = item.data(Qt.ItemDataRole.UserRole)
        return payload if isinstance(payload, dict) else None

    def _get_current_selected_index(self) -> Optional[Dict[str, Any]]:
        return self._extract_index_payload(self.table.currentItem())

    def _select_index_in_table(self, idx_data: Dict[str, Any]) -> bool:
        target_name = str(idx_data.get("IndexName", "") or "")
        target_table = str(idx_data.get("TableName", "") or "")
        for row in range(self.table.rowCount()):
            cell = self.table.item(row, 0)
            payload = self._extract_index_payload(cell)
            if not payload:
                continue
            if (
                str(payload.get("IndexName", "") or "") == target_name
                and str(payload.get("TableName", "") or "") == target_table
            ):
                self.table.selectRow(row)
                self.table.scrollToItem(cell)
                self._on_index_selected(cell)
                return True
        return False

    def _start_usage_trend_loading(self, idx_data: Dict[str, Any]) -> None:
        conn = get_connection_manager().active_connection
        if not conn or not conn.is_connected:
            self._trend_text.setPlainText("Trend unavailable: no active database connection.")
            return
        self._trend_request_key = f"{idx_data.get('TableName', '')}|{idx_data.get('IndexName', '')}"
        self._trend_text.setPlainText("Loading Query Store usage trend...")

        self._trend_worker = IndexUsageTrendWorker(conn, idx_data, self)
        self._trend_worker.trend_loaded.connect(self._on_trend_loaded)
        self._trend_worker.trend_failed.connect(self._on_trend_failed)
        self._trend_worker.start()

    def _on_trend_loaded(self, request_key: str, rows_obj: object) -> None:
        if request_key != self._trend_request_key:
            return
        rows = list(rows_obj or [])
        self._trend_rows_by_key[request_key] = rows
        if not rows:
            self._trend_text.setPlainText(
                "No Query Store trend data for this index in the last 30 days.\n"
                "Tip: Ensure Query Store is enabled and workload has executed."
            )
            return

        reads: List[float] = []
        executions_total = 0
        reads_total = 0.0
        for row in rows:
            executions = int(row.get("executions", 0) or 0)
            total_reads = float(row.get("total_reads", 0) or 0)
            executions_total += executions
            reads_total += total_reads
            reads.append(total_reads)

        spark = self._build_sparkline(reads)
        lines = [
            f"Reads Sparkline: {spark}",
            f"Data Points: {len(rows)} day(s)",
            f"Total Executions: {executions_total:,}",
            f"Total Logical Reads: {reads_total:,.0f}",
            "",
            "Recent Days:",
        ]
        for row in rows[-7:]:
            lines.append(
                f"- {row.get('day')}: exec={int(row.get('executions', 0) or 0):,}, "
                f"reads={float(row.get('total_reads', 0) or 0):,.0f}"
            )
        self._trend_text.setPlainText("\n".join(lines))

    def _on_trend_failed(self, request_key: str, error: str) -> None:
        if request_key != self._trend_request_key:
            return
        self._trend_text.setPlainText(f"Trend unavailable (Query Store): {error}")

    def _get_selected_indexes(self) -> List[Dict[str, Any]]:
        selected: List[Dict[str, Any]] = []
        selected_rows = self.table.selectionModel().selectedRows()
        for model_index in selected_rows:
            row = int(model_index.row())
            payload = self._extract_index_payload(self.table.item(row, 0))
            if payload:
                selected.append(payload)
        return selected

    def _on_select_needs_action_changed(self, state: int) -> None:
        checked = state == int(Qt.CheckState.Checked.value)
        self.table.clearSelection()
        if not checked:
            return
        model = self.table.selectionModel()
        for row in range(self.table.rowCount()):
            payload = self._extract_index_payload(self.table.item(row, 0))
            if payload and self._is_needs_attention(payload):
                model.select(
                    self.table.model().index(row, 0),
                    QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
                )

    @staticmethod
    def _quote_two_part_name(table_full: str) -> str:
        if "." in table_full:
            schema_name, table_name = table_full.split(".", 1)
        else:
            schema_name, table_name = "dbo", table_full
        return f"[{schema_name}].[{table_name}]"

    def _generate_batch_maintenance_script(self, indexes: List[Dict[str, Any]]) -> str:
        conn = get_connection_manager().active_connection
        database_name = str(conn.profile.database) if conn and conn.profile else "YourDatabase"
        lines: List[str] = [
            "-- Index Maintenance Batch",
            f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"-- Selected Indexes: {len(indexes)}",
            f"USE [{database_name}];",
            "GO",
            "",
        ]
        action_idx = 0
        for idx_data in indexes:
            classification = str(idx_data.get("Classification", "") or "")
            index_name = str(idx_data.get("IndexName", "") or "")
            table_name = str(idx_data.get("TableName", "") or "")
            metrics = idx_data.get("Metrics", {}) or {}
            props = idx_data.get("Properties", {}) or {}
            frag = float(metrics.get("FragmentationPercent", 0) or 0)

            if classification == "NEEDS_MAINTENANCE":
                action_idx += 1
                lines.append(f"-- {action_idx}. Maintenance for {index_name}")
                if frag >= 30.0:
                    lines.append(f"ALTER INDEX [{index_name}] ON {self._quote_two_part_name(table_name)} REBUILD WITH (ONLINE = ON);")
                else:
                    lines.append(f"ALTER INDEX [{index_name}] ON {self._quote_two_part_name(table_name)} REORGANIZE;")
                lines.append("")
            elif classification == "UNNECESSARY":
                if bool(props.get("IsPrimaryKey", False)):
                    lines.append(f"-- Skip {index_name}: primary key index")
                    continue
                action_idx += 1
                lines.append(f"-- {action_idx}. Drop unnecessary index {index_name}")
                lines.append(f"DROP INDEX [{index_name}] ON {self._quote_two_part_name(table_name)};")
                lines.append("")

        if action_idx == 0:
            lines.append("-- No direct maintenance/drop action generated for selected rows.")
            lines.append("-- Select indexes classified as NEEDS_MAINTENANCE or UNNECESSARY.")
        return "\n".join(lines)

    def _generate_batch_script_from_selection(self) -> None:
        indexes = self._get_selected_indexes()
        if not indexes:
            self.status_label.setText("Select one or more indexes first.")
            self.status_label.setStyleSheet(f"color: {Colors.WARNING}; font-size: 14px; background: transparent;")
            return
        script = self._generate_batch_maintenance_script(indexes)
        self._script_text.set_text(script)
        self.status_label.setText(f"Batch maintenance script generated for {len(indexes)} indexes.")
        self.status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 14px; background: transparent;")

    def _build_analysis_report_markdown(self, indexes: List[Dict[str, Any]]) -> str:
        lines: List[str] = [
            "# Index Advisor Analysis Report",
            "",
            f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- Row Count: {len(indexes)}",
            "",
            "| Table | Index | Classification | Score | Read/Write | Fragmentation |",
            "|---|---|---:|---:|---:|---:|",
        ]
        for item in indexes:
            metrics = item.get("Metrics", {}) or {}
            lines.append(
                f"| {item.get('TableName', '')} | {item.get('IndexName', '')} | {item.get('Classification', '')} "
                f"| {int(item.get('Score', 0) or 0)} | {float(metrics.get('ReadWriteRatio', 0) or 0):.2f} "
                f"| {float(metrics.get('FragmentationPercent', 0) or 0):.2f}% |"
            )
            consolidation = item.get("ConsolidationSuggestion")
            if isinstance(consolidation, dict):
                lines.append(
                    f"|  |  | Consolidation |  |  | {consolidation.get('message', '')} "
                    f"(~{float(consolidation.get('estimated_space_savings_mb', 0) or 0):.2f} MB) |"
                )
        return "\n".join(lines)

    def _export_analysis_report(self) -> None:
        indexes = self._get_selected_indexes() or self._current_indexes
        if not indexes:
            self.status_label.setText("No rows available to export.")
            self.status_label.setStyleSheet(f"color: {Colors.WARNING}; font-size: 14px; background: transparent;")
            return

        default_name = f"index_advisor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Index Analysis Report", default_name, "Markdown (*.md)")
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write(self._build_analysis_report_markdown(indexes))
            QMessageBox.information(self, "Export Complete", f"Report exported:\n{file_path}")
        except Exception as ex:
            QMessageBox.critical(self, "Export Failed", str(ex))

    def _on_refresh_failed(self, error: str) -> None:
        logger.error(f"Failed to load index analysis: {error}")
        self.status_label.setText(f"Error: {str(error)}")
        self.status_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 14px; background: transparent;")

    def _on_refresh_worker_finished(self) -> None:
        self.set_loading(False)
        self._refresh_btn.setEnabled(True)

    @staticmethod
    def _build_index_collection_query() -> str:
        """Collect required DMV metrics for deterministic index evaluation."""
        return f"""
        SELECT TOP ({MAX_INDEX_ROWS})
            s.name AS schema_name,
            o.name AS table_name,
            i.name AS index_name,
            i.type_desc,
            i.is_unique,
            i.is_primary_key,
            i.is_unique_constraint,
            i.has_filter AS is_filtered,
            i.filter_definition,
            i.fill_factor,
            o.create_date,
            DATEDIFF(DAY, o.create_date, GETDATE()) AS days_since_create,

            ISNULL(us.user_seeks, 0) AS user_seeks,
            ISNULL(us.user_scans, 0) AS user_scans,
            ISNULL(us.user_lookups, 0) AS user_lookups,
            ISNULL(us.user_updates, 0) AS user_updates,
            us.last_user_seek,
            us.last_user_scan,

            ISNULL(ios.leaf_insert_count, 0) AS leaf_insert_count,
            ISNULL(ios.leaf_update_count, 0) AS leaf_update_count,
            ISNULL(ios.leaf_delete_count, 0) AS leaf_delete_count,
            ISNULL(ios.range_scan_count, 0) AS range_scan_count,
            ISNULL(ios.singleton_lookup_count, 0) AS singleton_lookup_count,
            ISNULL(ios.page_lock_wait_count, 0) AS page_lock_wait_count,
            ISNULL(ios.page_lock_wait_in_ms, 0) AS page_lock_wait_in_ms,
            ISNULL(ios.page_io_latch_wait_count, 0) AS page_io_latch_wait_count,
            ISNULL(ios.page_io_latch_wait_in_ms, 0) AS page_io_latch_wait_in_ms,
            ISNULL(ios.row_lock_wait_count, 0) AS row_lock_wait_count,
            ISNULL(ios.row_lock_wait_in_ms, 0) AS row_lock_wait_in_ms,

            ISNULL(ips.avg_fragmentation_in_percent, 0) AS avg_fragmentation_in_percent,
            ISNULL(ips.avg_page_space_used_in_percent, 100) AS avg_page_space_used_in_percent,
            ISNULL(ips.page_count, 0) AS page_count,
            ISNULL(ips.record_count, 0) AS record_count,
            ISNULL(ips.forwarded_record_count, 0) AS forwarded_record_count,

            STATS_DATE(i.object_id, i.index_id) AS last_stats_update,
            ISNULL(DATEDIFF(DAY, STATS_DATE(i.object_id, i.index_id), GETDATE()), 9999) AS days_since_last_stats_update,
            ISNULL(sp.modification_counter, 0) AS modification_counter,
            ISNULL(sp.rows, 0) AS table_rows,
            ISNULL(sp.rows_sampled, 0) AS rows_sampled,
            ISNULL(hs.histogram_steps, 0) AS histogram_steps,

            ISNULL(cols.key_columns, '') AS key_columns,
            ISNULL(cols.included_columns, '') AS included_columns,
            ISNULL(cols.key_column_total_bytes, 0) AS key_column_total_bytes,
            ISNULL(cols.all_columns_not_null, 0) AS all_columns_not_null,
            ISNULL(cols.all_columns_fixed_length, 0) AS all_columns_fixed_length,

            ISNULL(fk.supports_fk, 0) AS supports_fk,
            ISNULL(cs.open_rowgroup_count, 0) AS open_rowgroup_count
        FROM sys.indexes i
        JOIN sys.objects o ON i.object_id = o.object_id
        JOIN sys.schemas s ON o.schema_id = s.schema_id
        LEFT JOIN sys.dm_db_index_usage_stats us
            ON us.database_id = DB_ID()
            AND us.object_id = i.object_id
            AND us.index_id = i.index_id
        OUTER APPLY sys.dm_db_index_operational_stats(DB_ID(), i.object_id, i.index_id, NULL) ios
        OUTER APPLY (
            SELECT TOP 1
                avg_fragmentation_in_percent,
                avg_page_space_used_in_percent,
                page_count,
                record_count,
                forwarded_record_count
            FROM sys.dm_db_index_physical_stats(DB_ID(), i.object_id, i.index_id, NULL, 'LIMITED')
        ) ips
        OUTER APPLY sys.dm_db_stats_properties(i.object_id, i.index_id) sp
        OUTER APPLY (
            SELECT COUNT(*) AS histogram_steps
            FROM sys.dm_db_stats_histogram(i.object_id, i.index_id)
        ) hs
        OUTER APPLY (
            SELECT
                STUFF((
                    SELECT ', ' + QUOTENAME(c.name)
                    FROM sys.index_columns ic2
                    JOIN sys.columns c
                        ON ic2.object_id = c.object_id
                        AND ic2.column_id = c.column_id
                    WHERE ic2.object_id = i.object_id
                      AND ic2.index_id = i.index_id
                      AND ic2.is_included_column = 0
                    ORDER BY ic2.key_ordinal
                    FOR XML PATH(''), TYPE
                ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS key_columns,
                STUFF((
                    SELECT ', ' + QUOTENAME(c.name)
                    FROM sys.index_columns ic2
                    JOIN sys.columns c
                        ON ic2.object_id = c.object_id
                        AND ic2.column_id = c.column_id
                    WHERE ic2.object_id = i.object_id
                      AND ic2.index_id = i.index_id
                      AND ic2.is_included_column = 1
                    ORDER BY c.column_id
                    FOR XML PATH(''), TYPE
                ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS included_columns,
                SUM(
                    CASE
                        WHEN ic2.is_included_column = 0
                        THEN CASE WHEN c.max_length = -1 THEN 8000 ELSE c.max_length END
                        ELSE 0
                    END
                ) AS key_column_total_bytes,
                MIN(CASE WHEN c.is_nullable = 1 THEN 0 ELSE 1 END) AS all_columns_not_null,
                MIN(
                    CASE
                        WHEN t.name IN ('varchar', 'nvarchar', 'varbinary', 'text', 'ntext', 'image', 'xml')
                             OR c.max_length = -1
                        THEN 0
                        ELSE 1
                    END
                ) AS all_columns_fixed_length
            FROM sys.index_columns ic2
            JOIN sys.columns c
                ON ic2.object_id = c.object_id
                AND ic2.column_id = c.column_id
            JOIN sys.types t
                ON c.user_type_id = t.user_type_id
            WHERE ic2.object_id = i.object_id
              AND ic2.index_id = i.index_id
        ) cols
        OUTER APPLY (
            SELECT
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM sys.foreign_key_columns fkc
                        JOIN sys.index_columns fic
                            ON fic.object_id = i.object_id
                            AND fic.index_id = i.index_id
                            AND fic.column_id = fkc.parent_column_id
                            AND fic.key_ordinal > 0
                        WHERE fkc.parent_object_id = i.object_id
                    ) THEN 1 ELSE 0
                END AS supports_fk
        ) fk
        OUTER APPLY (
            SELECT COUNT(*) AS open_rowgroup_count
            FROM sys.dm_db_column_store_row_group_physical_stats rg
            WHERE rg.object_id = i.object_id
              AND rg.index_id = i.index_id
              AND rg.state_desc = 'OPEN'
        ) cs
        WHERE o.type = 'U'
          AND i.index_id > 0
          AND i.is_hypothetical = 0
        ORDER BY
            (ISNULL(us.user_seeks, 0) + ISNULL(us.user_scans, 0) + ISNULL(us.user_lookups, 0)) DESC,
            i.name;
        """

    @staticmethod
    def _build_index_collection_query_legacy() -> str:
        """Fallback query for environments without sys.dm_db_stats_histogram."""
        return IndexAdvisorView._build_index_collection_query().replace(
            "OUTER APPLY (\n            SELECT COUNT(*) AS histogram_steps\n            FROM sys.dm_db_stats_histogram(i.object_id, i.index_id)\n        ) hs",
            "OUTER APPLY (SELECT CAST(0 AS BIGINT) AS histogram_steps) hs"
        )
    
    def _on_index_selected(self, item):
        """Handle index selection"""
        idx = self._extract_index_payload(item) or self._get_current_selected_index()
        if not idx:
            return

        script = self._generate_create_index_script(idx)
        self._script_text.set_text(script)
        self._metrics_text.setPlainText(self._build_metrics_snapshot(idx))
        self._ai_result.setMarkdown(self._build_deterministic_summary(idx))
        self._start_usage_trend_loading(idx)
    
    def _generate_create_index_script(self, idx: Dict) -> str:
        """Generate CREATE INDEX script from deterministic output."""
        internal = idx.get("Internal", {}) or {}
        props = idx.get("Properties", {}) or {}
        table_full = str(idx.get("TableName", "dbo.TableName"))
        if "." in table_full:
            schema, table = table_full.split(".", 1)
        else:
            schema, table = "dbo", table_full

        idx_name = str(idx.get("IndexName", "IX_Table_Col"))
        type_desc = str(internal.get("TypeDesc", "NONCLUSTERED")).upper()
        unique_kw = "UNIQUE " if bool(props.get("IsUnique", False)) else ""
        filter_def = str(internal.get("FilterDefinition", "") or "").strip()
        fill_factor = int(props.get("FillFactor", 0) or 0)

        key_columns = props.get("KeyColumns", [])
        included_columns = props.get("IncludedColumns", [])
        if isinstance(key_columns, list) and key_columns:
            key_sql = ", ".join(key_columns)
        else:
            key_sql = "[Column1]"

        if "COLUMNSTORE" in type_desc:
            script = (
                f"CREATE {unique_kw}{type_desc} INDEX [{idx_name}]\n"
                f"ON [{schema}].[{table}]"
            )
        else:
            script = (
                f"CREATE {unique_kw}{type_desc} INDEX [{idx_name}]\n"
                f"ON [{schema}].[{table}] ({key_sql})"
            )

        if "COLUMNSTORE" not in type_desc and isinstance(included_columns, list) and included_columns:
            script += f"\nINCLUDE ({', '.join(included_columns)})"
        if filter_def:
            script += f"\nWHERE {filter_def}"

        with_options: List[str] = ["ONLINE = ON"]
        if fill_factor > 0:
            with_options.append(f"FILLFACTOR = {fill_factor}")
        script += f"\nWITH ({', '.join(with_options)});"
        return script
    
    def _copy_script(self):
        """Copy script to clipboard"""
        from PyQt6.QtWidgets import QApplication
        script = self._script_text.text()
        if script:
            QApplication.clipboard().setText(script)
    
    def _show_context_menu(self, position):
        """Show context menu"""
        row = self.table.rowAt(position.y())
        if row >= 0:
            self.table.selectRow(row)
            if self.table.item(row, 0):
                self.table.setCurrentItem(self.table.item(row, 0))
        if not self._get_current_selected_index():
            return
        
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_style())
        
        copy_action = QAction("Copy Script", self)
        copy_action.triggered.connect(self._copy_script)
        menu.addAction(copy_action)
        
        ai_action = QAction("Analyze with AI", self)
        ai_action.triggered.connect(self._run_ai_analysis)
        menu.addAction(ai_action)
        
        menu.exec(self.table.mapToGlobal(position))
    
    def _run_ai_analysis(self):
        """Run AI analysis on selected index"""
        idx = self._get_current_selected_index()
        if not idx:
            self._ai_result.setMarkdown("Please select an index first.")
            return

        self._ai_btn.setEnabled(False)
        self._ai_stream_buffer = ""
        self._ai_result.setMarkdown("Preparing AI analysis (Object Explorer pipeline)...")

        object_info = self._build_object_explorer_style_index_object_info(idx)
        self._ai_worker = AITuneWorker(object_info, mode="analyze", deep_mode=False, skip_cache=False, parent=self)
        self._ai_worker.analysis_ready.connect(self._on_ai_finished)
        self._ai_worker.error.connect(self._on_ai_error)
        self._ai_worker.progress.connect(self._on_ai_progress)
        self._ai_worker.response_chunk.connect(self._on_ai_stream_chunk)
        self._ai_worker.start()
    
    def _on_ai_finished(self, result: str):
        """Handle AI analysis completion"""
        self._ai_result.setMarkdown(result)
        self._ai_btn.setEnabled(True)
        self._ai_stream_buffer = ""
    
    def _on_ai_error(self, error: str):
        """Handle AI analysis error"""
        self._ai_result.setMarkdown(f"Error: {error}")
        self._ai_btn.setEnabled(True)
        self._ai_stream_buffer = ""

    def _on_ai_progress(self, percentage: int, step: str) -> None:
        if self._ai_stream_buffer:
            return
        self._ai_result.setPlainText(f"{step} ({percentage}%)")

    def _on_ai_stream_chunk(self, chunk: str) -> None:
        if not chunk:
            return
        self._ai_stream_buffer += str(chunk)
        self._ai_result.setPlainText(self._ai_stream_buffer)

    @staticmethod
    def _sanitize_two_part_name(value: str) -> str:
        text = str(value or "").strip().replace("[", "").replace("]", "")
        return text

    def _collect_missing_index_recommendations_for_table(
        self,
        conn: Any,
        table_full: str,
    ) -> List[Dict[str, Any]]:
        """
        Best-effort missing index DMV query for a specific table.
        Returns a list compatible with the AI analysis input schema.
        """
        try:
            safe_table = self._sanitize_two_part_name(table_full)
            if not safe_table:
                return []
            query = """
            SELECT TOP 5
                mid.equality_columns,
                mid.inequality_columns,
                mid.included_columns,
                mid.statement,
                migs.avg_user_impact,
                migs.avg_total_user_cost,
                migs.user_seeks,
                migs.user_scans,
                (migs.avg_total_user_cost * migs.avg_user_impact * (migs.user_seeks + migs.user_scans)) AS impact_score
            FROM sys.dm_db_missing_index_details mid
            JOIN sys.dm_db_missing_index_groups mig ON mid.index_handle = mig.index_handle
            JOIN sys.dm_db_missing_index_group_stats migs ON mig.index_group_handle = migs.group_handle
            WHERE mid.database_id = DB_ID()
              AND mid.object_id = OBJECT_ID(:table_full)
            ORDER BY impact_score DESC;
            """
            rows = conn.execute_query(query, {"table_full": safe_table}) or []
            return [dict(r) for r in rows if isinstance(r, dict)]
        except Exception as ex:
            logger.debug(f"Missing index DMV collection failed: {ex}")
            return []

    @staticmethod
    def _index_row_to_existing_index_entry(idx_row: Dict[str, Any]) -> Dict[str, Any]:
        metrics = idx_row.get("Metrics", {}) or {}
        props = idx_row.get("Properties", {}) or {}
        internal = idx_row.get("Internal", {}) or {}
        key_cols = props.get("KeyColumns", []) or []
        inc_cols = props.get("IncludedColumns", []) or []

        def _join_cols(cols: Any) -> str:
            if isinstance(cols, list):
                return ", ".join([str(c) for c in cols if str(c or "").strip()])
            return str(cols or "")

        return {
            "name": idx_row.get("IndexName", ""),
            "type": internal.get("TypeDesc", ""),
            "is_unique": bool(props.get("IsUnique", False)),
            "is_pk": bool(props.get("IsPrimaryKey", False)),
            "supports_fk": bool(props.get("SupportsFK", False)),
            "key_columns": _join_cols(key_cols),
            "include_columns": _join_cols(inc_cols),
            "seeks": int(metrics.get("UserSeeks", 0) or 0),
            "scans": int(metrics.get("UserScans", 0) or 0),
            "lookups": int(internal.get("UserLookups", 0) or 0),
            "updates": int(metrics.get("UserUpdates", 0) or 0),
            "page_count": int(metrics.get("PageCount", 0) or 0),
            "avg_fragmentation_in_percent": float(metrics.get("FragmentationPercent", 0) or 0),
            "fill_factor": int(props.get("FillFactor", 0) or 0),
            "has_filter": bool(props.get("IsFiltered", False)),
            "filter_definition": str(internal.get("FilterDefinition", "") or ""),
            "key_column_total_bytes": int(props.get("KeyLengthBytes", 0) or 0),
            "days_since_last_stats_update": int(metrics.get("DaysSinceLastStatsUpdate", 0) or 0),
            "table_rows": int(internal.get("TableRows", 0) or 0),
            "all_columns_not_null": bool(internal.get("AllColumnsNotNull", False)),
            "all_columns_fixed_length": bool(internal.get("AllColumnsFixedLength", False)),
        }

    def _build_object_explorer_style_index_object_info(self, idx: Dict[str, Any]) -> Dict[str, Any]:
        conn = get_connection_manager().active_connection
        db_name = ""
        if conn is not None:
            try:
                db_name = str(getattr(conn.info, "database_name", "") or "")
            except Exception:
                db_name = ""
            if not db_name:
                try:
                    db_name = str(getattr(getattr(conn, "profile", None), "database", "") or "")
                except Exception:
                    db_name = ""

        table_full = str(idx.get("TableName", "") or "")
        index_name = str(idx.get("IndexName", "") or "")
        full_name = f"{table_full}.{index_name}".strip(".")

        script = self._generate_create_index_script(idx)
        request_key = f"{table_full}|{index_name}"
        trend_rows = self._trend_rows_by_key.get(request_key, [])

        # Existing indexes for this table (collector format expected by AIAnalysisService).
        same_table = [r for r in (self._all_indexes or []) if str(r.get("TableName", "") or "") == table_full]
        if not same_table:
            same_table = [idx]
        existing_indexes = [
            {
                "table": table_full,
                "indexes": [self._index_row_to_existing_index_entry(r) for r in same_table],
            }
        ]

        missing_indexes = []
        if conn and getattr(conn, "is_connected", False):
            missing_indexes = self._collect_missing_index_recommendations_for_table(conn, table_full)

        metrics = idx.get("Metrics", {}) or {}
        props = idx.get("Properties", {}) or {}
        internal = idx.get("Internal", {}) or {}

        stats = {
            "index_name": index_name,
            "table_name": table_full,
            "score": int(idx.get("Score", 0) or 0),
            "classification": str(idx.get("Classification", "") or ""),
            "metrics": metrics,
            "properties": props,
            "internal": {
                "duplicate_type": internal.get("DuplicateType", ""),
                "user_lookups": internal.get("UserLookups", 0),
                "last_user_seek": internal.get("LastUserSeek"),
                "last_user_scan": internal.get("LastUserScan"),
            },
            "flags": idx.get("Flags", []) or [],
            "warnings": idx.get("Warnings", []) or [],
            "computed_recommendations": idx.get("ComputedRecommendations", []) or [],
        }

        context_warning = (
            "Index Advisor context: analysis is performed for a single index using deterministic snapshot data. "
            "Stored procedure source code and execution plan may be unavailable."
        )
        completeness = {
            "quality_level": "partial",
            "has_source_code": True,
            "has_execution_stats": True,
            "has_execution_plan": False,
            "has_query_store": bool(trend_rows),
        }

        return {
            "database": db_name,
            "full_name": full_name or index_name or table_full or "Index",
            "object_type_code": "INDEX",
            "object_type": "INDEX",
            "object_resolution": {
                "object_resolved": True,
                "database": db_name,
                "full_name": full_name,
                "object_type_code": "INDEX",
                "object_type": "INDEX",
                "object_id": None,
            },
            "source_code": script,
            "stats": stats,
            "depends_on": [],
            "used_by": [],
            "missing_indexes": missing_indexes,
            "wait_stats": [],
            "query_store": {
                "status": {"is_operational": bool(trend_rows)},
                "index_usage_trend_30d": trend_rows,
            },
            "plan_xml": "",
            "plan_meta": {},
            "plan_insights": {},
            "existing_indexes": existing_indexes,
            "view_metadata": {},
            "parameter_sniffing": {},
            "historical_trend": {"index_usage_trend_30d": trend_rows},
            "memory_grants": {},
            "completeness": completeness,
            "context_warning": context_warning,
            "collection_log": [
                "Index Advisor: deterministic index snapshot (Metrics/Properties/Flags/Warns)",
                f"Existing Indexes: {len(existing_indexes[0].get('indexes', []))} index(es) for {table_full}",
                f"Missing Index DMVs: {len(missing_indexes)} row(s)",
                f"Query Store Trend Rows: {len(trend_rows)} day(s)",
            ],
        }

    @staticmethod
    def _build_metrics_snapshot(idx: Dict[str, Any]) -> str:
        metrics = idx.get("Metrics", {}) or {}
        props = idx.get("Properties", {}) or {}
        internal = idx.get("Internal", {}) or {}
        consolidation = idx.get("ConsolidationSuggestion")

        lines = [
            "Current Stats",
            "-------------",
            f"Index: {idx.get('IndexName', '')}",
            f"Table: {idx.get('TableName', '')}",
            f"Classification: {idx.get('Classification', '')}",
            f"Score: {int(idx.get('Score', 0) or 0)}",
            "",
            "Usage",
            f"- User Seeks: {int(metrics.get('UserSeeks', 0) or 0):,}",
            f"- User Scans: {int(metrics.get('UserScans', 0) or 0):,}",
            f"- User Updates: {int(metrics.get('UserUpdates', 0) or 0):,}",
            f"- Read/Write Ratio: {float(metrics.get('ReadWriteRatio', 0) or 0):.2f}",
            "",
            "Storage",
            f"- Fragmentation: {float(metrics.get('FragmentationPercent', 0) or 0):.2f}%",
            f"- Page Count: {int(metrics.get('PageCount', 0) or 0):,}",
            f"- Size MB: {float(metrics.get('SizeMB', 0) or 0):.2f}",
            "",
            "Design",
            f"- Key Columns: {', '.join(props.get('KeyColumns', []) or []) or '(none)'}",
            f"- Include Columns: {', '.join(props.get('IncludedColumns', []) or []) or '(none)'}",
            f"- Key Length Bytes: {int(props.get('KeyLengthBytes', 0) or 0)}",
            f"- Fill Factor: {int(props.get('FillFactor', 0) or 0)}",
            f"- Is Unique: {bool(props.get('IsUnique', False))}",
            f"- Is Filtered: {bool(props.get('IsFiltered', False))}",
            f"- Is Primary Key: {bool(props.get('IsPrimaryKey', False))}",
            "",
            "Diagnostics",
            f"- Duplicate Type: {internal.get('DuplicateType', '')}",
            f"- Days Since Stats Update: {int(metrics.get('DaysSinceLastStatsUpdate', 0) or 0)}",
        ]
        if isinstance(consolidation, dict):
            lines.extend(
                [
                    "",
                    "Consolidation Candidate",
                    f"- Partner Index: {consolidation.get('partner_index', '')}",
                    f"- Message: {consolidation.get('message', '')}",
                    f"- Estimated Savings: {float(consolidation.get('estimated_space_savings_mb', 0) or 0):.2f} MB",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def _build_deterministic_summary(idx: Dict[str, Any]) -> str:
        metrics = idx.get("Metrics", {}) or {}
        flags = idx.get("Flags", []) or []
        warnings = idx.get("Warnings", []) or []
        recs = idx.get("ComputedRecommendations", []) or []
        consolidation = idx.get("ConsolidationSuggestion")
        classification = str(idx.get("Classification", "") or "")
        score = int(idx.get("Score", 0) or 0)
        cls_reason = str(idx.get("ClassificationReason", "") or "")
        cls_conf = str(idx.get("ClassificationConfidence", "") or "")
        score_band = str(idx.get("ScoreBand", "") or "")

        reads = int(metrics.get("UserSeeks", 0) or 0) + int(metrics.get("UserScans", 0) or 0)
        writes = int(metrics.get("UserUpdates", 0) or 0)
        ratio = float(metrics.get("ReadWriteRatio", 0) or 0)
        frag = float(metrics.get("FragmentationPercent", 0) or 0)
        summary_sentence = (
            f"This index is classified as **{classification}** with score **{score}/100** "
            f"(band **{score_band}**, confidence **{cls_conf}**). "
            f"Observed load: **{reads} reads / {writes} writes**, read-write ratio **{ratio:.2f}**, "
            f"fragmentation **{frag:.2f}%**."
        )

        lines = [
            "## Deterministic Analysis Snapshot",
            "",
            "### Executive Summary",
            summary_sentence,
            "",
            f"- **Index:** {idx.get('IndexName', '')}",
            f"- **Table:** {idx.get('TableName', '')}",
            f"- **Classification:** {classification}",
            f"- **Classification Reason:** {cls_reason or '(none)'}",
            f"- **Score:** {score}/100",
            f"- **Score Band:** {score_band or '(n/a)'}",
            "",
            "### Metrics",
            f"- Read/Write Ratio: {metrics.get('ReadWriteRatio', 0)}",
            f"- Fragmentation: {metrics.get('FragmentationPercent', 0)}%",
            f"- User Seeks: {metrics.get('UserSeeks', 0)}",
            f"- User Updates: {metrics.get('UserUpdates', 0)}",
            f"- Selectivity Ratio: {metrics.get('SelectivityRatio', 0)}",
            "",
            "### Flags",
        ]
        if flags:
            lines.extend([f"- {f}" for f in flags])
        else:
            lines.append("- (none)")

        lines.append("")
        lines.append("### Warnings")
        if warnings:
            lines.extend([f"- {w}" for w in warnings])
        else:
            lines.append("- (none)")

        lines.append("")
        lines.append("### Computed Recommendations")
        if recs:
            lines.extend([f"- {r}" for r in recs])
        else:
            lines.append("- MONITOR_AND_KEEP")

        if isinstance(consolidation, dict):
            lines.append("")
            lines.append("### Consolidation Suggestion")
            lines.append(f"- Type: {consolidation.get('type', '')}")
            lines.append(f"- Partner Index: {consolidation.get('partner_index', '')}")
            lines.append(f"- Action: {consolidation.get('action', '')}")
            lines.append(f"- Message: {consolidation.get('message', '')}")
            lines.append(
                f"- Estimated Space Savings: {float(consolidation.get('estimated_space_savings_mb', 0) or 0):.2f} MB"
            )
        return "\n".join(lines)
