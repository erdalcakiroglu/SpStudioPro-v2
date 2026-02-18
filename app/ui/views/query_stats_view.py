"""
Query Stats View - GUI-05 Modern Design
Execution stats, CPU, IO and duration trends for workload.
"""

from typing import Optional, List, Dict, Set, Any, Callable
from datetime import datetime
import threading
import uuid
import csv
import asyncio
import json
from html import escape
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QLineEdit, QPushButton, QScrollArea,
    QFrame, QSizePolicy, QListWidget, QListWidgetItem,
    QDialog, QPlainTextEdit, QTextEdit, QMessageBox, QGraphicsDropShadowEffect,
    QTabWidget, QProgressBar, QCheckBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QListView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QPropertyAnimation, QEasingCurve, QThread
from PyQt6.QtGui import QFont, QFontMetrics, QPainter, QColor, QPen

from app.ui.views.base_view import BaseView
from app.ui.views.query_stats_controllers import (
    QueryStatsDetailController,
    QueryStatsListController,
    QueryStatsToolbarController,
)
from app.ui.theme import Colors, Theme as ThemeStyles
from app.core.logger import get_logger
from app.services.query_stats_contract import IQueryStatsService
from app.services.service_factory import ServiceFactory
from app.models.query_stats_models import (
    QueryStats, 
    QueryStatsFilter, 
)
from app.ui.components.code_editor import CodeEditor
from app.ui.components.plan_viewer import PlanViewerWidget
from app.analysis.plan_parser import PlanParser
from app.models.analysis_context import AnalysisContext
from app.services.query_ai_context_pipeline import QueryAIContextPipeline
from app.ai.llm_client import get_llm_client

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

    cancel_requested = pyqtSignal()
    
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

        self._progress = QProgressBar()
        self._progress.setFixedWidth(260)
        self._progress.setRange(0, 0)  # Indeterminate by default
        self._progress.setTextVisible(True)
        self._progress.setFormat("%p%")
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_SECONDARY};
                text-align: center;
                height: 16px;
                margin-top: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.PRIMARY};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self._progress, alignment=Qt.AlignmentFlag.AlignCenter)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
                margin-top: 12px;
            }}
            QPushButton:hover {{
                border: 1px solid {Colors.PRIMARY};
                color: {Colors.PRIMARY};
                background-color: #f8fafc;
            }}
        """)
        self._cancel_btn.clicked.connect(lambda _checked=False: self.cancel_requested.emit())
        layout.addWidget(self._cancel_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
    def set_text(self, text: str):
        """Set loading message"""
        self._label.setText(text)

    def set_progress(self, current: int, total: int, determinate: bool = True) -> None:
        """Update progress bar mode/value."""
        if not determinate or int(total) <= 0:
            self._progress.setRange(0, 0)
            self._progress.setFormat("Working...")
            return
        safe_total = max(1, int(total))
        safe_current = max(0, min(int(current), safe_total))
        self._progress.setRange(0, safe_total)
        self._progress.setValue(safe_current)
        self._progress.setFormat(f"{safe_current}/{safe_total} (%p%)")
        
    def showEvent(self, event):
        super().showEvent(event)
        self._spinner.start()
        
    def hideEvent(self, event):
        super().hideEvent(event)
        self._spinner.stop()


class QueryStatsLoadWorker(QThread):
    """Background loader for top query statistics."""

    loaded = pyqtSignal(int, object, object, int, object)   # request_id, List[QueryStats], List[str], total_count, health_report
    failed = pyqtSignal(int, str, str, object, object) # request_id, error_message, error_type, List[str], health_report
    progress = pyqtSignal(int, int, int, str, bool)  # request_id, current, total, message, determinate

    def __init__(
        self,
        request_id: int,
        filter_snapshot: QueryStatsFilter,
        include_sensitive_data: bool = False,
        service_factory: Optional[Callable[[], IQueryStatsService]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._request_id = int(request_id)
        self._filter_snapshot = filter_snapshot
        self._include_sensitive_data = bool(include_sensitive_data)
        self._service_factory = service_factory or ServiceFactory.create_query_stats_service
        self._service = self._service_factory()
        self._cancel_event = threading.Event()
        self._correlation_id = uuid.uuid4().hex[:12]
        self._health_warnings: List[str] = []
        self._health_report: Dict[str, Any] = {}

    def _is_cancelled(self) -> bool:
        return self.isInterruptionRequested() or self._cancel_event.is_set()

    def cancel(self) -> None:
        self._cancel_event.set()
        self.requestInterruption()
        try:
            self._service.cancel_current_operation()
        except Exception:
            pass

    def _emit_progress(self, current: int, total: int, message: str, determinate: bool = True) -> None:
        if self._is_cancelled():
            return
        self.progress.emit(
            int(self._request_id),
            int(current),
            int(total),
            str(message or ""),
            bool(determinate),
        )

    def run(self) -> None:
        try:
            if self._is_cancelled():
                return
            self._emit_progress(0, 4, "Connecting to database... (0/4)", determinate=True)
            logger.info(
                f"Query stats load started [request_id={self._request_id}, correlation_id={self._correlation_id}]"
            )
            if self._service.is_connected:
                self._emit_progress(1, 4, "Checking Query Store status... (1/4)", determinate=True)
                self._service.refresh(force_refresh=False)
                health = self._service.get_module_health(correlation_id=self._correlation_id)
                self._health_warnings = list(health.get("warnings", []) or [])
                self._health_report = dict(health or {})
            self._emit_progress(0, 0, "Fetching query statistics...", determinate=False)
            queries = self._service.get_top_queries(
                self._filter_snapshot,
                raise_on_error=True,
                cancel_check=self._is_cancelled,
                correlation_id=self._correlation_id,
                include_sensitive_data=self._include_sensitive_data,
            )
            self._emit_progress(3, 4, "Processing results... (3/4)", determinate=True)
            warnings = self._service.get_runtime_warnings()
            merged_warnings: List[str] = []
            for w in [*self._health_warnings, *warnings]:
                text = str(w or "").strip()
                if text and text not in merged_warnings:
                    merged_warnings.append(text)
            if self._is_cancelled():
                return
            self._emit_progress(4, 4, f"Complete! Loaded {len(queries)} queries. (4/4)", determinate=True)
            logger.info(
                f"Query stats load completed [request_id={self._request_id}, correlation_id={self._correlation_id}]"
            )
            total_count = int(self._service.get_last_total_count() or len(queries))
            self.loaded.emit(self._request_id, queries, merged_warnings, total_count, self._health_report)
        except Exception as e:
            error_type = self._service.classify_error_type(e)
            error_message = self._service.get_user_friendly_error_message(e)
            logger.error(
                f"Query stats load failed [request_id={self._request_id}, "
                f"correlation_id={self._correlation_id}, error_type={error_type}]: {error_message}"
            )
            self.failed.emit(
                self._request_id,
                error_message,
                error_type,
                self._health_warnings,
                self._health_report,
            )


class BatchAIAnalysisWorker(QThread):
    """Parallel batch AI analysis worker for selected queries."""

    progress = pyqtSignal(int, int, str, str)  # completed, total, query_name, status
    analysis_finished = pyqtSignal(object)  # List[Dict[str, Any]]
    failed = pyqtSignal(str)

    def __init__(
        self,
        queries: List[QueryStats],
        include_sensitive_data: bool = False,
        service_factory: Optional[Callable[[], IQueryStatsService]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._queries = list(queries or [])
        self._include_sensitive_data = bool(include_sensitive_data)
        self._cancel_event = threading.Event()
        self._service_factory = service_factory or ServiceFactory.create_query_stats_service
        self._service = self._service_factory()
        self._pipeline = QueryAIContextPipeline(self._service)

    def cancel(self) -> None:
        self._cancel_event.set()
        self.requestInterruption()
        try:
            self._service.cancel_current_operation()
        except Exception:
            pass

    def _is_cancelled(self) -> bool:
        return self.isInterruptionRequested() or self._cancel_event.is_set()

    async def _analyze_parallel(self, contexts: List[Dict[str, Any]], max_concurrency: int = 3) -> List[Dict[str, Any]]:
        semaphore = asyncio.Semaphore(max(1, int(max_concurrency)))
        completed = 0
        total = len(contexts)
        results: List[Dict[str, Any]] = []

        async def _run_one(ctx: Dict[str, Any]) -> Dict[str, Any]:
            query_name = str(ctx.get("query_name", "Query"))
            query_id = int(ctx.get("query_id", 0) or 0)
            quality = dict(ctx.get("analysis_context_quality", {}) or {})
            start = datetime.utcnow()

            if self._is_cancelled():
                return {
                    "query_id": query_id,
                    "query_name": query_name,
                    "success": False,
                    "duration_ms": 0.0,
                    "error": "Cancelled",
                    "analysis": "",
                    "quality_score": int(quality.get("score", 0) or 0),
                    "quality_confidence": str(quality.get("confidence", "Low") or "Low"),
                }

            async with semaphore:
                service = None
                try:
                    from app.ai.analysis_service import AIAnalysisService

                    service = AIAnalysisService()
                    response = await service.analyze_from_context(ctx)
                    elapsed = (datetime.utcnow() - start).total_seconds() * 1000.0
                    success = not str(response or "").strip().startswith("⚠️")
                    return {
                        "query_id": query_id,
                        "query_name": query_name,
                        "success": bool(success),
                        "duration_ms": round(elapsed, 2),
                        "error": "" if success else "AI analysis returned warning/error response",
                        "analysis": str(response or ""),
                        "quality_score": int(quality.get("score", 0) or 0),
                        "quality_confidence": str(quality.get("confidence", "Low") or "Low"),
                    }
                except Exception as exc:
                    elapsed = (datetime.utcnow() - start).total_seconds() * 1000.0
                    return {
                        "query_id": query_id,
                        "query_name": query_name,
                        "success": False,
                        "duration_ms": round(elapsed, 2),
                        "error": str(exc),
                        "analysis": "",
                        "quality_score": int(quality.get("score", 0) or 0),
                        "quality_confidence": str(quality.get("confidence", "Low") or "Low"),
                    }

        tasks = [asyncio.create_task(_run_one(ctx)) for ctx in contexts]
        for future in asyncio.as_completed(tasks):
            if self._is_cancelled():
                for task in tasks:
                    task.cancel()
                break
            item = await future
            results.append(item)
            completed += 1
            status = "OK" if bool(item.get("success")) else "ERROR"
            self.progress.emit(
                int(completed),
                int(total),
                str(item.get("query_name", "Query")),
                status,
            )
        return results

    def run(self) -> None:
        try:
            if not self._queries:
                self.analysis_finished.emit([])
                return

            contexts: List[Dict[str, Any]] = []
            for idx, query in enumerate(self._queries, start=1):
                if self._is_cancelled():
                    break
                analysis_context = self._service.build_analysis_context(
                    query=query,
                    target_module="ai_batch_analysis",
                    reason="query_stats_batch_ai_analysis",
                )
                context = self._pipeline.build_context(
                    analysis_context,
                    include_sensitive_data=self._include_sensitive_data,
                )
                contexts.append(context)
                self.progress.emit(
                    int(idx),
                    int(max(1, len(self._queries))),
                    str(query.display_name or f"Query {query.query_id}"),
                    "CONTEXT",
                )

            if self._is_cancelled():
                self.analysis_finished.emit([])
                return

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(self._analyze_parallel(contexts, max_concurrency=3))
            finally:
                loop.close()

            self.analysis_finished.emit(results)
        except Exception as e:
            self.failed.emit(str(e))


class BatchAnalysisResultDialog(QDialog):
    """Summary dialog for batch AI analysis results with export options."""

    def __init__(self, results: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self._results = list(results or [])
        self.setWindowTitle("Batch AI Analysis Results")
        self.resize(1100, 640)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        total = len(self._results)
        success = len([r for r in self._results if bool(r.get("success"))])
        failed = total - success
        avg_ms = (
            sum(float(r.get("duration_ms", 0.0) or 0.0) for r in self._results) / float(max(1, total))
            if total > 0
            else 0.0
        )
        summary = QLabel(
            f"Total: {total} | Success: {success} | Failed: {failed} | Avg Duration: {avg_ms:.1f} ms"
        )
        summary.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; font-weight: 600;")
        layout.addWidget(summary)

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            ["Query", "Status", "Duration (ms)", "Quality", "Confidence", "Error"]
        )
        table.setRowCount(total)
        for i, row in enumerate(self._results):
            status_text = "OK" if bool(row.get("success")) else "ERROR"
            values = [
                str(row.get("query_name", "")),
                status_text,
                f"{float(row.get('duration_ms', 0.0) or 0.0):.2f}",
                str(row.get("quality_score", "")),
                str(row.get("quality_confidence", "")),
                str(row.get("error", "")),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 1:
                    if status_text == "OK":
                        item.setForeground(QColor(Colors.SUCCESS))
                    else:
                        item.setForeground(QColor(Colors.ERROR))
                table.setItem(i, col, item)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(table, stretch=1)

        self._markdown = QPlainTextEdit()
        self._markdown.setReadOnly(True)
        self._markdown.setPlainText(self._build_markdown_summary())
        self._markdown.setStyleSheet(
            f"QPlainTextEdit {{ background-color: #f8fafc; border: 1px solid {Colors.BORDER}; border-radius: 8px; }}"
        )
        layout.addWidget(self._markdown, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(export_csv_btn)

        export_html_btn = QPushButton("Export HTML")
        export_html_btn.clicked.connect(self._export_html)
        btn_layout.addWidget(export_html_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _build_markdown_summary(self) -> str:
        lines = ["# Batch AI Analysis Report", ""]
        for row in self._results:
            status_text = "OK" if bool(row.get("success")) else "ERROR"
            lines.append(f"## {row.get('query_name', 'Query')} [{status_text}]")
            lines.append(f"- Duration (ms): {float(row.get('duration_ms', 0.0) or 0.0):.2f}")
            lines.append(f"- Context Quality: {row.get('quality_score', 0)} ({row.get('quality_confidence', 'Low')})")
            err = str(row.get("error", "") or "").strip()
            if err:
                lines.append(f"- Error: {err}")
            lines.append("")
            analysis = str(row.get("analysis", "") or "").strip()
            if analysis:
                lines.append(analysis)
                lines.append("")
        return "\n".join(lines)

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Batch Report CSV", "batch_ai_report.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["query_id", "query_name", "status", "duration_ms", "quality_score", "quality_confidence", "error"]
                )
                for row in self._results:
                    writer.writerow(
                        [
                            int(row.get("query_id", 0) or 0),
                            str(row.get("query_name", "")),
                            "OK" if bool(row.get("success")) else "ERROR",
                            float(row.get("duration_ms", 0.0) or 0.0),
                            int(row.get("quality_score", 0) or 0),
                            str(row.get("quality_confidence", "")),
                            str(row.get("error", "")),
                        ]
                    )
            QMessageBox.information(self, "Export CSV", "Batch report exported successfully.")
        except Exception as exc:
            QMessageBox.warning(self, "Export CSV", f"Failed to export CSV: {exc}")

    def _export_html(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Batch Report HTML", "batch_ai_report.html", "HTML Files (*.html)")
        if not path:
            return
        try:
            rows = []
            for row in self._results:
                status_text = "OK" if bool(row.get("success")) else "ERROR"
                color = "#16a34a" if status_text == "OK" else "#dc2626"
                analysis_text = escape(str(row.get("analysis", "") or ""))
                rows.append(
                    f"<tr>"
                    f"<td>{escape(str(row.get('query_name', '')))}</td>"
                    f"<td style='color:{color};font-weight:600'>{status_text}</td>"
                    f"<td>{float(row.get('duration_ms', 0.0) or 0.0):.2f}</td>"
                    f"<td>{int(row.get('quality_score', 0) or 0)}</td>"
                    f"<td>{escape(str(row.get('quality_confidence', '')))}</td>"
                    f"<td>{escape(str(row.get('error', '')))}</td>"
                    f"</tr>"
                    f"<tr><td colspan='6'><pre style='white-space:pre-wrap'>{analysis_text}</pre></td></tr>"
                )
            html = (
                "<html><head><meta charset='utf-8'><title>Batch AI Analysis Report</title></head>"
                "<body style='font-family:Segoe UI,Arial,sans-serif'>"
                "<h2>Batch AI Analysis Report</h2>"
                "<table border='1' cellspacing='0' cellpadding='6' style='border-collapse:collapse;width:100%'>"
                "<thead><tr><th>Query</th><th>Status</th><th>Duration (ms)</th><th>Quality</th><th>Confidence</th><th>Error</th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table></body></html>"
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            QMessageBox.information(self, "Export HTML", "Batch report exported successfully.")
        except Exception as exc:
            QMessageBox.warning(self, "Export HTML", f"Failed to export HTML: {exc}")


class QueryStatsView(BaseView):
    """
    Query Statistics View - GUI-05 Style
    Shows query performance stats in a clean list format
    """
    
    query_selected = pyqtSignal(int)  # query_id
    cross_module_navigation_requested = pyqtSignal(str, object)  # target_view_id, AnalysisContext
    _DURATION_INDEX_TO_DAYS = {0: 1, 1: 7, 2: 30}
    _DURATION_DAYS_TO_INDEX = {1: 0, 7: 1, 30: 2}
    _ORDER_INDEX_TO_VALUE = {
        0: "impact_score",
        1: "avg_duration",
        2: "total_cpu",
        3: "execution_count",
        4: "logical_reads",
    }
    _ORDER_VALUE_TO_INDEX = {
        "impact_score": 0,
        "avg_duration": 1,
        "total_cpu": 2,
        "execution_count": 3,
        "logical_reads": 4,
    }
    _TOP_N_VALUES = [500, 1000, 2000, 5000]
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        service: Optional[IQueryStatsService] = None,
        service_factory: Optional[Callable[[], IQueryStatsService]] = None,
    ):
        super().__init__(parent)
        if service_factory is not None:
            self._service_factory = service_factory
        elif service is not None:
            self._service_factory = lambda: service
        else:
            self._service_factory = ServiceFactory.create_query_stats_service
        self._service = service or self._service_factory()
        self._context_pipeline = QueryAIContextPipeline(self._service)
        self._queries: List[QueryStats] = []
        self._current_filter = QueryStatsFilter()
        self._load_worker: Optional[QueryStatsLoadWorker] = None
        self._batch_ai_worker: Optional[BatchAIAnalysisWorker] = None
        self._batch_ai_total_queries: int = 0
        self._active_load_request_id: int = 0
        self._suspend_filter_events = False
        self._last_filter_db_key: str = ""
        self._checked_query_ids: Set[int] = set()
        self._query_checkboxes: Dict[int, QCheckBox] = {}
        self._query_item_by_id: Dict[int, QListWidgetItem] = {}
        self._page_size: int = 100
        self._loaded_count: int = 0
        self._total_count: int = 0
        self._has_more_results: bool = False
        self._show_sensitive_data: bool = False
        self._cloud_ai_sensitive_opt_in: bool = False
        self._permission_status: Dict[str, Any] = {}
        self._filter_save_timer = QTimer(self)
        self._filter_save_timer.setSingleShot(True)
        self._filter_save_timer.timeout.connect(self._persist_current_filter_state)
        self._list_controller = QueryStatsListController(self)
        self._detail_controller = QueryStatsDetailController(self, self._service, QueryDetailDialog)
        self._toolbar_controller = QueryStatsToolbarController(self, self._service)
    
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
        
        self._health_label = QLabel("Query Store Health: checking...")
        self._health_label.setToolTip(
            "Minimum Query Statistics permissions:\n"
            "- VIEW SERVER STATE\n"
            "- VIEW DEFINITION (or SELECT on sys.sql_modules for source code view)"
        )
        self._health_label.setStyleSheet(f"""
            QLabel {{
                color: #92400e;
                background-color: #fffbeb;
                border: 1px solid #f59e0b;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)
        main_layout.addWidget(self._health_label)
        
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
        self._cmb_duration.currentIndexChanged.connect(self._on_filter_changed)
        self._cmb_duration.setStyleSheet(ThemeStyles.combobox_style())
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
        self._cmb_order.currentIndexChanged.connect(self._on_filter_changed)
        self._cmb_order.setStyleSheet(ThemeStyles.combobox_style())
        filters_layout.addWidget(self._cmb_order)

        # Result limit filter
        limit_label = QLabel("Limit:")
        limit_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 500;")
        filters_layout.addWidget(limit_label)

        self._cmb_limit = QComboBox()
        self._cmb_limit.setMinimumWidth(96)
        self._cmb_limit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        for value in self._TOP_N_VALUES:
            self._cmb_limit.addItem(f"Top {value}", value)
        self._cmb_limit.setCurrentIndex(1)  # Top 1000 default
        self._cmb_limit.currentIndexChanged.connect(self._on_filter_changed)
        filters_layout.addWidget(self._cmb_limit)
        
        # Search filter
        search_label = QLabel("Search:")
        self._cmb_limit.setStyleSheet(ThemeStyles.combobox_style())
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

        self._chk_sensitive = QCheckBox("Show Sensitive Data")
        self._chk_sensitive.setChecked(False)
        self._chk_sensitive.setToolTip(
            "OFF (default): literals are redacted in SQL text and execution plans.\n"
            "ON: raw values are visible in this session after explicit confirmation."
        )
        self._chk_sensitive.setStyleSheet(f"""
            QCheckBox {{
                color: {Colors.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 600;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {Colors.BORDER_DARK};
                border-radius: 3px;
                background-color: {Colors.SURFACE};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.TEXT_PRIMARY};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.TEXT_PRIMARY};
                border-color: {Colors.TEXT_PRIMARY};
                image: none;
            }}
            QCheckBox:disabled {{
                color: {Colors.TEXT_MUTED};
            }}
            QCheckBox::indicator:disabled {{
                background-color: {Colors.BORDER_LIGHT};
                border-color: {Colors.BORDER};
            }}
        """)
        self._chk_sensitive.stateChanged.connect(self._on_sensitive_data_toggled)
        filters_layout.addWidget(self._chk_sensitive)
        
        filters_layout.addStretch()

        self._btn_reset_filters = QPushButton("Reset to Defaults")
        self._btn_reset_filters.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_reset_filters.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                color: {Colors.PRIMARY};
                border: 1px solid {Colors.PRIMARY};
                background-color: #f8fafc;
            }}
        """)
        self._btn_reset_filters.clicked.connect(self._reset_filters_to_defaults)
        filters_layout.addWidget(self._btn_reset_filters)

        main_layout.addWidget(filters_panel)

        # Batch operations bar
        batch_bar = QFrame()
        batch_bar.setObjectName("Card")
        batch_bar.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)
        batch_layout = QHBoxLayout(batch_bar)
        batch_layout.setContentsMargins(12, 10, 12, 10)
        batch_layout.setSpacing(8)

        self._btn_batch_ops = QPushButton("Batch Operations")
        self._btn_batch_ops.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_batch_ops.setStyleSheet(self._btn_reset_filters.styleSheet())
        self._btn_batch_ops.clicked.connect(self._show_batch_operations_menu)
        batch_layout.addWidget(self._btn_batch_ops)

        self._btn_select_top_cpu = QPushButton("Select Top 10 by CPU")
        self._btn_select_top_cpu.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_select_top_cpu.setStyleSheet(self._btn_reset_filters.styleSheet())
        self._btn_select_top_cpu.clicked.connect(self._select_top_10_by_cpu)
        batch_layout.addWidget(self._btn_select_top_cpu)

        self._btn_clear_selection = QPushButton("Clear Selection")
        self._btn_clear_selection.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_clear_selection.setStyleSheet(self._btn_reset_filters.styleSheet())
        self._btn_clear_selection.clicked.connect(self._clear_query_selection)
        batch_layout.addWidget(self._btn_clear_selection)

        self._selected_count_label = QLabel("Selected: 0")
        self._selected_count_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"
        )
        batch_layout.addStretch()
        batch_layout.addWidget(self._selected_count_label)
        main_layout.addWidget(batch_bar)

        # Runtime warning banner (degraded mode / partial data notices)
        self._warning_label = QLabel("")
        self._warning_label.setWordWrap(True)
        self._warning_label.setVisible(False)
        self._warning_label.setStyleSheet(f"""
            QLabel {{
                color: #92400e;
                background-color: #fffbeb;
                border: 1px solid #f59e0b;
                border-radius: 6px;
                padding: 8px 10px;
                font-size: 11px;
            }}
        """)
        main_layout.addWidget(self._warning_label)
        
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
        self._queries_list.setSpacing(2)
        self._queries_list.setUniformItemSizes(True)
        self._queries_list.setLayoutMode(QListView.LayoutMode.Batched)
        self._queries_list.setBatchSize(50)
        self._queries_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._queries_list.setStyleSheet(ThemeStyles.listbox_style())
        self._queries_list.itemDoubleClicked.connect(self._on_query_double_clicked)
        self._queries_list.itemSelectionChanged.connect(self._update_selected_count_label)
        self._queries_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._queries_list.customContextMenuRequested.connect(self._show_query_context_menu)
        results_layout.addWidget(self._queries_list)

        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 8, 10, 8)
        footer_layout.setSpacing(8)
        self._results_count_label = QLabel("Showing 0 of 0 results")
        self._results_count_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"
        )
        footer_layout.addWidget(self._results_count_label)
        footer_layout.addStretch()

        self._btn_load_more = QPushButton("Load More")
        self._btn_load_more.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_load_more.setStyleSheet(self._btn_reset_filters.styleSheet())
        self._btn_load_more.clicked.connect(self._load_more_results)
        self._btn_load_more.setVisible(False)
        footer_layout.addWidget(self._btn_load_more)
        results_layout.addWidget(footer)
        
        main_layout.addWidget(results_panel, stretch=1)
        
        self._main_layout.addWidget(main_widget)
        
        # Loading overlay (hidden by default)
        self._loading_overlay = LoadingOverlay(self)
        self._loading_overlay.cancel_requested.connect(self._cancel_current_load)
        self._loading_overlay.hide()
    
    def _add_query_item(self, query: QueryStats) -> None:
        self._list_controller.add_query_item(query)

    def _format_last_execution(self, value: Optional[datetime]) -> str:
        return self._list_controller.format_last_execution(value)
    
    def _on_query_double_clicked(self, item: QListWidgetItem) -> None:
        self._list_controller.on_query_double_clicked(item)

    def _open_query_detail(self, query: QueryStats, start_tab: int = 0) -> None:
        self._detail_controller.open_query_detail(query, start_tab=start_tab)

    def _build_analysis_context(self, query: QueryStats, target_module: str, reason: str) -> AnalysisContext:
        return self._detail_controller.build_analysis_context(query, target_module, reason)

    def _emit_navigation_context(self, target_view: str, context: AnalysisContext) -> None:
        self._detail_controller.emit_navigation_context(target_view, context)

    def _show_query_context_menu(self, position) -> None:
        self._detail_controller.show_query_context_menu(position)

    def _navigate_to_missing_indexes(self, query: QueryStats) -> None:
        self._detail_controller.navigate_to_missing_indexes(query)

    def _navigate_to_wait_stats(self, query: QueryStats) -> None:
        self._detail_controller.navigate_to_wait_stats(query)

    def _get_active_database_filter_key(self) -> str:
        return self._toolbar_controller.get_active_database_filter_key()

    def _build_filter_state_payload(self) -> Dict[str, object]:
        return self._toolbar_controller.build_filter_state_payload()

    def _apply_filter_state_payload(self, payload: Dict[str, object]) -> None:
        self._toolbar_controller.apply_filter_state_payload(payload)

    def _load_persisted_filter_state(self, force: bool = False) -> None:
        self._toolbar_controller.load_persisted_filter_state(force=force)

    def _persist_current_filter_state(self) -> None:
        self._toolbar_controller.persist_current_filter_state()

    def _clear_persisted_filter_state_for_current_db(self) -> None:
        self._toolbar_controller.clear_persisted_filter_state_for_current_db()

    def _reset_filters_to_defaults(self) -> None:
        self._toolbar_controller.reset_filters_to_defaults()

    def _on_query_checked(self, query_id: int, checked: bool) -> None:
        self._list_controller.on_query_checked(query_id, checked)

    def _get_selected_queries(self) -> List[QueryStats]:
        return self._list_controller.get_selected_queries()

    def _update_selected_count_label(self) -> None:
        self._list_controller.update_selected_count_label()

    def _update_results_count_label(self) -> None:
        self._list_controller.update_results_count_label()

    def _load_more_results(self) -> None:
        self._list_controller.load_more_results()

    def _clear_query_selection(self) -> None:
        self._list_controller.clear_query_selection()

    def _select_top_10_by_cpu(self) -> None:
        self._list_controller.select_top_10_by_cpu()

    def _show_batch_operations_menu(self) -> None:
        self._toolbar_controller.show_batch_operations_menu()

    def _is_active_ai_provider_local(self) -> bool:
        try:
            return bool(get_llm_client().is_active_provider_local())
        except Exception:
            return False

    def _resolve_ai_sensitive_context_policy(self) -> bool:
        """
        Returns True when raw (unredacted) query text/plan XML can be sent to AI.
        """
        if not self._show_sensitive_data:
            return False
        if self._is_active_ai_provider_local():
            return True
        if self._cloud_ai_sensitive_opt_in:
            return True

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Sensitive Data Consent")
        box.setText("Cloud AI provider detected.")
        box.setInformativeText(
            "Raw query text and plan literals may include sensitive data.\n"
            "Do you want to allow sending unredacted data for this session?"
        )
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        decision = box.exec()
        allow = decision == QMessageBox.StandardButton.Yes
        if allow:
            self._cloud_ai_sensitive_opt_in = True
            logger.warning("Sensitive AI context enabled for cloud provider by explicit user consent.")
        return allow

    def _on_sensitive_data_toggled(self, state: int) -> None:
        checked = bool(state == int(Qt.CheckState.Checked.value))
        if checked:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle("Show Sensitive Data")
            box.setText("Sensitive data visibility is currently OFF by default.")
            box.setInformativeText(
                "Enabling this may expose literals (PII/secrets) in SQL text and plan XML.\n"
                "Do you want to enable it for this session?"
            )
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.setDefaultButton(QMessageBox.StandardButton.No)
            if box.exec() != QMessageBox.StandardButton.Yes:
                self._chk_sensitive.blockSignals(True)
                self._chk_sensitive.setChecked(False)
                self._chk_sensitive.blockSignals(False)
                self._show_sensitive_data = False
                return
            self._show_sensitive_data = True
            logger.warning("Sensitive data display enabled for Query Statistics (session opt-in).")
        else:
            self._show_sensitive_data = False
            self._cloud_ai_sensitive_opt_in = False
            logger.info("Sensitive data display disabled for Query Statistics.")

        if self._is_initialized:
            self._service.invalidate_top_queries_cache()
            self._refresh_data(reset_list=True)

    def _analyze_selected_with_ai(self) -> None:
        selected = self._get_selected_queries()
        if not selected:
            QMessageBox.information(self, "Batch Analysis", "Select one or more queries first.")
            return
        if self._batch_ai_worker and self._batch_ai_worker.isRunning():
            QMessageBox.information(self, "Batch Analysis", "A batch AI analysis is already running.")
            return

        top = selected[:10]
        include_sensitive_for_ai = self._resolve_ai_sensitive_context_policy()
        self._batch_ai_total_queries = len(top)
        self._show_loading(f"Preparing batch AI analysis for {len(top)} queries...")
        self._update_loading_progress(0, max(1, len(top) * 2), "Building AI contexts...", determinate=True)

        self._batch_ai_worker = BatchAIAnalysisWorker(
            top,
            include_sensitive_data=include_sensitive_for_ai,
            service_factory=self._service_factory,
            parent=self,
        )
        self._batch_ai_worker.progress.connect(self._on_batch_ai_progress)
        self._batch_ai_worker.analysis_finished.connect(self._on_batch_ai_finished)
        self._batch_ai_worker.failed.connect(self._on_batch_ai_failed)
        self._batch_ai_worker.finished.connect(self._on_batch_ai_worker_finished)
        self._batch_ai_worker.start()

    def _on_batch_ai_progress(self, completed: int, total: int, query_name: str, status: str) -> None:
        total_safe = max(1, int(total or 1))
        done = max(0, min(int(completed or 0), total_safe))
        phase = str(status or "").upper()
        full_total = max(1, total_safe * 2)
        if phase == "CONTEXT":
            display_done = done
        else:
            display_done = total_safe + done
        display_done = max(0, min(display_done, full_total))
        if phase == "CONTEXT":
            msg = f"Preparing context: {query_name} ({done}/{total_safe})"
        else:
            msg = f"AI analyzing: {query_name} [{phase}] ({done}/{total_safe})"
        self._update_loading_progress(display_done, full_total, msg, determinate=True)

    def _on_batch_ai_finished(self, results_obj: object) -> None:
        self._batch_ai_total_queries = 0
        self._hide_loading()
        results = results_obj if isinstance(results_obj, list) else []
        if not results:
            QMessageBox.information(self, "Batch Analysis", "Batch AI analysis finished with no results.")
            return
        dialog = BatchAnalysisResultDialog(results, self)
        dialog.exec()

    def _on_batch_ai_failed(self, error_message: str) -> None:
        self._batch_ai_total_queries = 0
        self._hide_loading()
        QMessageBox.warning(self, "Batch Analysis", f"Batch AI analysis failed: {error_message}")

    def _on_batch_ai_worker_finished(self) -> None:
        self._batch_ai_total_queries = 0
        worker = self.sender()
        if worker is self._batch_ai_worker:
            self._batch_ai_worker = None
        if worker is not None:
            try:
                worker.deleteLater()
            except Exception:
                pass

    def _export_selected_to_csv(self) -> None:
        selected = self._get_selected_queries()
        if not selected:
            QMessageBox.information(self, "Export CSV", "Select one or more queries first.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Selected Queries",
            "query_stats_selected.csv",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "query_id",
                        "query_name",
                        "priority",
                        "avg_duration_ms",
                        "p95_duration_ms",
                        "avg_cpu_ms",
                        "avg_logical_reads",
                        "total_executions",
                        "plan_count",
                        "impact_score",
                        "last_execution",
                    ]
                )
                for query in selected:
                    m = query.metrics
                    writer.writerow(
                        [
                            int(query.query_id or 0),
                            query.display_name,
                            query.priority.value,
                            float(m.avg_duration_ms or 0.0),
                            float(m.p95_duration_ms or 0.0),
                            float(m.avg_cpu_ms or 0.0),
                            float(m.avg_logical_reads or 0.0),
                            int(m.total_executions or 0),
                            int(m.plan_count or 0),
                            float(m.impact_score or 0.0),
                            self._format_last_execution(query.last_execution),
                        ]
                    )
            QMessageBox.information(self, "Export CSV", f"Exported {len(selected)} queries to CSV.")
        except Exception as e:
            QMessageBox.warning(self, "Export CSV", f"Failed to export CSV: {e}")

    def _compare_selected_queries(self) -> None:
        selected = self._get_selected_queries()
        if len(selected) < 2:
            QMessageBox.information(self, "Compare Queries", "Select at least 2 queries to compare.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Compare Selected Queries")
        dialog.resize(980, 420)
        layout = QVBoxLayout(dialog)
        table = QTableWidget()
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(
            [
                "Query",
                "Avg Duration (ms)",
                "P95 Duration (ms)",
                "Avg CPU (ms)",
                "Avg Reads",
                "Executions",
                "Plans",
                "Impact",
            ]
        )
        table.setRowCount(len(selected))
        for i, query in enumerate(selected):
            m = query.metrics
            values = [
                query.display_name,
                f"{float(m.avg_duration_ms or 0.0):.1f}",
                f"{float(m.p95_duration_ms or 0.0):.1f}",
                f"{float(m.avg_cpu_ms or 0.0):.1f}",
                f"{float(m.avg_logical_reads or 0.0):,.0f}",
                f"{int(m.total_executions or 0):,}",
                f"{int(m.plan_count or 0)}",
                f"{float(m.impact_score or 0.0):.1f}",
            ]
            for col, value in enumerate(values):
                table.setItem(i, col, QTableWidgetItem(value))
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 8):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(table)
        dialog.exec()
    
    def _on_filter_changed(self) -> None:
        self._toolbar_controller.on_filter_changed()
    
    def _on_search_changed(self, text: str) -> None:
        self._toolbar_controller.on_search_changed(text)
    
    def _filter_list(self) -> None:
        self._list_controller.filter_list()
    
    def resizeEvent(self, event):
        """Handle resize to position loading overlay"""
        super().resizeEvent(event)
        if hasattr(self, '_loading_overlay'):
            self._loading_overlay.setGeometry(self.rect())
    
    def _show_loading(self, message: str = "Loading..."):
        """Show loading overlay"""
        self._loading_overlay.set_text(message)
        self._loading_overlay.set_progress(0, 0, determinate=False)
        self._loading_overlay.setGeometry(self.rect())
        self._loading_overlay.raise_()
        self._loading_overlay.show()
        # Process events to show overlay immediately
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

    def _update_loading_progress(
        self,
        current: int,
        total: int,
        message: str,
        determinate: bool = True,
    ) -> None:
        self._loading_overlay.set_text(message or "Loading...")
        self._loading_overlay.set_progress(current, total, determinate=determinate)
    
    def _hide_loading(self):
        """Hide loading overlay"""
        self._loading_overlay.hide()

    def _clear_runtime_warning(self) -> None:
        self._warning_label.setVisible(False)
        self._warning_label.setText("")

    def _show_runtime_warning(self, warnings: List[str]) -> None:
        clean = [str(w).strip() for w in (warnings or []) if str(w).strip()]
        if not clean:
            self._clear_runtime_warning()
            return
        text = " | ".join(clean[:2])
        self._warning_label.setText(f"Warning: {text}")
        self._warning_label.setVisible(True)

    def _set_health_indicator(self, state: str, text: str) -> None:
        value = str(state or "yellow").strip().lower()
        if value == "green":
            fg = "#166534"
            bg = "#dcfce7"
            bd = "#22c55e"
        elif value == "red":
            fg = "#991b1b"
            bg = "#fef2f2"
            bd = "#ef4444"
        else:
            fg = "#92400e"
            bg = "#fffbeb"
            bd = "#f59e0b"
        self._health_label.setStyleSheet(
            f"QLabel {{ color: {fg}; background-color: {bg}; border: 1px solid {bd}; "
            f"border-radius: 6px; padding: 6px 10px; font-size: 11px; font-weight: 600; }}"
        )
        self._health_label.setText(str(text or "Query Store Health: unknown"))

    def _update_health_indicator_from_report(self, health_obj: object) -> None:
        report = health_obj if isinstance(health_obj, dict) else {}
        perms = report.get("permissions", {}) if isinstance(report, dict) else {}
        if perms and not bool(perms.get("module_enabled", True)):
            docs = str(perms.get("documentation_url", "") or "")
            text = "Query Store Health: RED | missing VIEW SERVER STATE permission."
            if docs:
                text += f" | Docs: {docs}"
            self._set_health_indicator("red", text)
            return

        qs = report.get("query_store", {}) if isinstance(report, dict) else {}
        state = str(qs.get("quality_state", "yellow") or "yellow").lower()
        enabled = bool(qs.get("is_enabled", False))
        actual_state = str(qs.get("actual_state", "") or "")
        query_count = int(qs.get("query_count", 0) or 0)
        is_recent = bool(qs.get("is_data_recent", False))
        guidance = qs.get("guidance", []) if isinstance(qs.get("guidance", []), list) else []
        docs = str(qs.get("documentation_url", "") or "")

        if state == "green":
            text = f"Query Store Health: GREEN | recent data | queries={query_count}"
        elif state == "red":
            text = (
                "Query Store Health: RED | disabled/non-operational -> using DMV fallback."
                if (not enabled or actual_state.upper() != "READ_WRITE")
                else "Query Store Health: RED"
            )
        else:
            stale_part = "stale data" if not is_recent else "partial issues"
            text = f"Query Store Health: YELLOW | {stale_part} | queries={query_count}"

        if guidance:
            text += f" | Guidance: {str(guidance[0])}"
        if docs:
            text += f" | Docs: {docs}"
        if perms and not bool(perms.get("source_code_enabled", True)):
            text += " | Source code view limited (missing VIEW DEFINITION/sys.sql_modules access)."
        self._set_health_indicator(state, text)
    
    def on_show(self) -> None:
        """View shown"""
        if not self._is_initialized:
            return
        self._load_persisted_filter_state(force=False)
        self.refresh(force_refresh=False)
    
    def refresh(self, force_refresh: bool = True) -> None:
        """Refresh data"""
        if not self._is_initialized:
            return
        self._load_persisted_filter_state(force=False)
        # Reset Query Store/version cache so DB/server switches are reflected.
        if self._service.is_connected:
            self._service.refresh(force_refresh=force_refresh)
        self._refresh_data(reset_list=True)

    def on_hide(self) -> None:
        """Stop pending background loads when view is hidden."""
        if self._filter_save_timer.isActive():
            self._filter_save_timer.stop()
            self._persist_current_filter_state()
        self._invalidate_pending_load()
        if self._batch_ai_worker and self._batch_ai_worker.isRunning():
            self._batch_ai_worker.cancel()
        self._hide_loading()

    def _cancel_current_load(self) -> None:
        """Cancel current background load on user request."""
        batch_running = bool(self._batch_ai_worker and self._batch_ai_worker.isRunning())
        load_running = bool(self._load_worker and self._load_worker.isRunning())
        is_load_more = int(getattr(self._current_filter, "offset", 0) or 0) > 0

        if load_running:
            self._invalidate_pending_load()
        if batch_running and self._batch_ai_worker:
            self._batch_ai_worker.cancel()
        self._hide_loading()
        if load_running:
            if not is_load_more:
                self._show_placeholder("Loading cancelled by user.")
            logger.info("Query stats loading cancelled by user.")
        elif batch_running:
            logger.info("Batch AI analysis cancelled by user.")
    
    def _refresh_data(self, reset_list: bool = True) -> None:
        """Refresh query data from service."""
        if reset_list:
            self._queries_list.clear()
            self._clear_runtime_warning()
            self._query_checkboxes.clear()
            self._query_item_by_id.clear()
            self._checked_query_ids.clear()
            self._loaded_count = 0
            self._total_count = 0
            self._has_more_results = False
            self._update_selected_count_label()
            self._update_results_count_label()
        
        # Check connection
        if not self._service.is_connected:
            self._invalidate_pending_load()
            self._set_health_indicator("red", "Query Store Health: RED | not connected.")
            self._has_more_results = False
            self._update_results_count_label()
            self._show_placeholder("Please connect to a database first.")
            logger.debug("Query stats refresh skipped: No active connection")
            return

        try:
            self._permission_status = self._service.get_permission_status(force_refresh=False)
        except Exception as exc:
            self._permission_status = {}
            logger.warning(f"Permission pre-check failed: {exc}")

        if not bool(self._permission_status.get("module_enabled", True)):
            self._invalidate_pending_load()
            self._set_health_indicator(
                "red",
                "Query Store Health: RED | missing VIEW SERVER STATE permission.",
            )
            warnings = list(self._permission_status.get("warnings", []) or [])
            if warnings:
                self._show_runtime_warning(warnings)
            self._show_placeholder(
                "Query Statistics requires VIEW SERVER STATE permission.\n"
                "Grant permission and retry."
            )
            self._has_more_results = False
            self._update_results_count_label()
            return

        source_enabled = bool(self._permission_status.get("source_code_enabled", True))
        if not source_enabled:
            self._show_runtime_warning(
                ["Source code view is disabled (missing VIEW DEFINITION / sys.sql_modules access)."]
            )
        
        # Show loading
        self._set_health_indicator("yellow", "Query Store Health: checking...")
        self._show_loading("Connecting to database..." if reset_list else "Loading more results...")

        # Build filter snapshot from UI
        self._current_filter.time_range_days = self._DURATION_INDEX_TO_DAYS.get(self._cmb_duration.currentIndex(), 1)
        self._current_filter.sort_by = self._ORDER_INDEX_TO_VALUE.get(self._cmb_order.currentIndex(), "impact_score")
        self._current_filter.top_n = int(self._cmb_limit.currentData() or 1000)
        self._current_filter.page_size = int(self._page_size or 100)
        self._current_filter.offset = int(self._loaded_count if not reset_list else 0)
        
        request_id = self._active_load_request_id + 1
        self._active_load_request_id = request_id
        filter_snapshot = QueryStatsFilter(
            time_range_days=self._current_filter.time_range_days,
            sort_by=self._current_filter.sort_by,
            top_n=self._current_filter.top_n,
            offset=self._current_filter.offset,
            page_size=self._current_filter.page_size,
            search_text=self._current_filter.search_text,
            min_executions=self._current_filter.min_executions,
            min_duration_ms=self._current_filter.min_duration_ms,
            object_name_filter=self._current_filter.object_name_filter,
            priority_filter=self._current_filter.priority_filter,
        )

        if self._load_worker and self._load_worker.isRunning():
            self._load_worker.cancel()

        self._load_worker = QueryStatsLoadWorker(
            request_id,
            filter_snapshot,
            include_sensitive_data=self._show_sensitive_data,
            service_factory=self._service_factory,
            parent=self,
        )
        self._load_worker.loaded.connect(self._on_queries_loaded)
        self._load_worker.failed.connect(self._on_queries_failed)
        self._load_worker.progress.connect(self._on_load_progress)
        self._load_worker.finished.connect(self._on_load_worker_finished)
        self._load_worker.start()

    def _invalidate_pending_load(self) -> None:
        """Invalidate outstanding load requests and interrupt active worker."""
        self._active_load_request_id += 1
        if self._load_worker and self._load_worker.isRunning():
            self._load_worker.cancel()

    def _on_load_progress(
        self,
        request_id: int,
        current: int,
        total: int,
        message: str,
        determinate: bool,
    ) -> None:
        """Handle progressive status updates from background worker."""
        if int(request_id) != int(self._active_load_request_id):
            return
        self._update_loading_progress(
            current=int(current),
            total=int(total),
            message=str(message or "Loading..."),
            determinate=bool(determinate),
        )

    def _on_queries_loaded(
        self,
        request_id: int,
        queries_obj: object,
        warnings_obj: object,
        total_count: int,
        health_obj: object,
    ) -> None:
        """Handle successful background load."""
        if int(request_id) != int(self._active_load_request_id):
            return
        count = len(queries_obj) if isinstance(queries_obj, list) else 0
        self._update_loading_progress(1, 1, f"Complete! Loaded {count} queries.", determinate=True)
        self._hide_loading()
        self._update_health_indicator_from_report(health_obj)
        page_queries = queries_obj if isinstance(queries_obj, list) else []
        warnings = warnings_obj if isinstance(warnings_obj, list) else []
        if not bool(self._permission_status.get("source_code_enabled", True)):
            warnings = list(warnings) + [
                "Source code view is disabled (missing VIEW DEFINITION / sys.sql_modules access)."
            ]
        self._show_runtime_warning(warnings)
        is_load_more = int(getattr(self._current_filter, "offset", 0) or 0) > 0
        if not page_queries and not is_load_more:
            self._queries = []
            self._loaded_count = 0
            self._total_count = int(total_count or 0)
            self._has_more_results = False
            self._update_results_count_label()
            self._show_placeholder("No queries matched this filter.")
            return
        if not is_load_more:
            self._queries = []
            self._queries_list.clear()
            self._query_checkboxes.clear()
            self._query_item_by_id.clear()
            self._checked_query_ids.clear()
        if page_queries:
            self._queries.extend(page_queries)
            for query in page_queries:
                self._add_query_item(query)

        self._loaded_count = len(self._queries)
        limit_cap = int(self._current_filter.top_n or self._total_count or 0)
        if limit_cap > 0:
            self._total_count = min(int(total_count or self._loaded_count), limit_cap)
        else:
            self._total_count = int(total_count or self._loaded_count)
        self._has_more_results = bool(
            self._loaded_count < self._total_count and len(page_queries) > 0
        )
        self._update_results_count_label()
        self._filter_list()
        self._update_selected_count_label()
        logger.info(
            f"Loaded queries page: page_count={len(page_queries)}, "
            f"loaded_total={self._loaded_count}, available={self._total_count}"
        )

    def _on_queries_failed(
        self,
        request_id: int,
        error: str,
        error_type: str,
        warnings_obj: object,
        health_obj: object,
    ) -> None:
        """Handle failed background load."""
        if int(request_id) != int(self._active_load_request_id):
            return
        self._hide_loading()
        self._update_health_indicator_from_report(health_obj)
        warnings = warnings_obj if isinstance(warnings_obj, list) else []
        self._show_runtime_warning(warnings)
        logger.error(f"Failed to load queries [{error_type}]: {error}")
        is_load_more = int(getattr(self._current_filter, "offset", 0) or 0) > 0
        if error_type == "cancelled":
            if not is_load_more:
                self._show_placeholder("Loading cancelled by user.")
            return
        if not is_load_more:
            self._show_placeholder(f"Error loading queries: {error}")
        self._has_more_results = False if not self._queries else self._has_more_results
        self._update_results_count_label()
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Query Statistics")
        box.setText(error)
        box.setInformativeText("Do you want to retry now?")
        box.setStandardButtons(
            QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Retry)
        if box.exec() == QMessageBox.StandardButton.Retry:
            self._refresh_data(reset_list=True)

    def _on_load_worker_finished(self) -> None:
        """Cleanup worker object on completion."""
        worker = self.sender()
        if worker is self._load_worker:
            self._load_worker = None
        if worker is not None:
            try:
                worker.deleteLater()
            except Exception:
                pass
    
    def _show_placeholder(self, message: str) -> None:
        self._list_controller.show_placeholder(message)


class QueryDetailDialog(QDialog):
    """Query Detail Dialog - GUI-05 Style"""
    
    def __init__(
        self,
        query: QueryStats,
        service: IQueryStatsService,
        parent=None,
        start_tab: int = 0,
        show_sensitive_data: bool = False,
        permission_status: Optional[Dict[str, Any]] = None,
        cloud_sensitive_opt_in: bool = False,
    ):
        super().__init__(parent)
        self.query = query
        self.service = service
        self._start_tab = int(start_tab or 0)
        self._show_sensitive_data = bool(show_sensitive_data)
        self._permission_status = dict(permission_status or {})
        self._cloud_sensitive_opt_in = bool(cloud_sensitive_opt_in)
        self._context_pipeline = QueryAIContextPipeline(self.service)
        self._ai_worker = None
        self._ai_stage_order = ["context", "connect", "analyze", "metrics", "optimize", "format"]
        self._last_ai_request_payload = None
        self._last_ai_request_file_path = None
        self.setWindowTitle(query.display_name)
        self.setMinimumSize(1200, 700)
        self.resize(1200, 700)
        self._setup_ui()
    
    def _setup_ui(self):
        self._apply_dialog_style()
        
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
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet(ThemeStyles.btn_ghost(size="md"))
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
        analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        analyze_btn.setStyleSheet(ThemeStyles.btn_secondary(size="md"))
        analyze_btn.clicked.connect(self._analyze_with_ai)
        header_layout.addWidget(analyze_btn)
        self._analyze_btn = analyze_btn
        
        main_layout.addWidget(header)
        
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
        self._content_tabs.setStyleSheet(ThemeStyles.tab_widget_style())
        
        # Tab 1: Source Code
        source_tab = QWidget()
        source_tab.setStyleSheet("background: transparent;")
        source_layout = QVBoxLayout(source_tab)
        source_layout.setContentsMargins(14, 12, 14, 12)
        source_layout.setSpacing(8)
        
        self._code_editor = CodeEditor(theme_override="light")
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

        self._ai_context_label = QLabel("Context Quality: N/A")
        self._ai_context_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"
        )
        ai_layout.addWidget(self._ai_context_label)

        self._ai_status_label = QLabel("Ready to analyze.")
        self._ai_status_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: 11px;
            background-color: #f8fafc;
            border: 1px dashed {Colors.BORDER};
            border-radius: 6px;
            padding: 6px 10px;
        """)
        ai_layout.addWidget(self._ai_status_label)

        self._ai_progress = QProgressBar()
        self._ai_progress.setTextVisible(False)
        self._ai_progress.setFixedHeight(6)
        self._ai_progress.setRange(0, 100)
        self._ai_progress.setValue(0)
        self._ai_progress.setVisible(False)
        self._ai_progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: {Colors.BORDER};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.PRIMARY};
                border-radius: 3px;
            }}
        """)
        ai_layout.addWidget(self._ai_progress)

        self._ai_result_area = QTextEdit()
        self._ai_result_area.setReadOnly(True)
        self._ai_result_area.setPlaceholderText("Click 'Analyze with AI' above to run analysis.")
        self._ai_result_area.setStyleSheet(f"""
            QTextEdit {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
                background-color: #f8fafc;
                border: 1px dashed {Colors.BORDER};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        ai_layout.addWidget(self._ai_result_area, stretch=1)

        ai_button_row = QHBoxLayout()
        ai_button_row.addStretch()

        self._ai_copy_btn = QPushButton("Copy Text")
        self._ai_copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ai_copy_btn.setEnabled(False)
        self._ai_copy_btn.setStyleSheet(ThemeStyles.btn_default(size="md"))
        self._ai_copy_btn.clicked.connect(self._copy_ai_result)
        ai_button_row.addWidget(self._ai_copy_btn)

        self._ai_save_btn = QPushButton("Save Report")
        self._ai_save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ai_save_btn.setEnabled(False)
        self._ai_save_btn.setStyleSheet(ThemeStyles.btn_default(size="md"))
        self._ai_save_btn.clicked.connect(self._save_ai_result)
        ai_button_row.addWidget(self._ai_save_btn)

        self._ai_save_request_btn = QPushButton("Save LLM Request")
        self._ai_save_request_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ai_save_request_btn.setEnabled(False)
        self._ai_save_request_btn.setStyleSheet(ThemeStyles.btn_default(size="md"))
        self._ai_save_request_btn.clicked.connect(self._save_ai_request_payload)
        ai_button_row.addWidget(self._ai_save_request_btn)

        ai_layout.addLayout(ai_button_row)

        self._content_tabs.addTab(ai_tab, "🤖 AI Analysis")
        
        left_layout.addWidget(self._content_tabs)
        content_layout.addWidget(left_panel, stretch=1)
        if not bool(self._permission_status.get("source_code_enabled", True)):
            self._content_tabs.setTabToolTip(
                0,
                "Source code requires VIEW DEFINITION or SELECT on sys.sql_modules.",
            )
        
        main_layout.addWidget(content_widget, stretch=1)

        # ═══════════════════════════════════════════════════════════
        # METRICS SUMMARY (Footer)
        # ═══════════════════════════════════════════════════════════
        metrics = self.query.metrics
        stats_text = (
            f"Avg Duration: {metrics.avg_duration_ms:.0f}ms | "
            f"P95 Duration: {metrics.p95_duration_ms:.0f}ms | "
            f"Avg CPU: {metrics.avg_cpu_ms:.0f}ms | "
            f"Avg Reads: {metrics.avg_logical_reads:,.0f} | "
            f"Executions: {metrics.total_executions:,} | "
            f"Plans: {metrics.plan_count}"
        )

        stats_footer = QFrame()
        stats_footer.setStyleSheet(
            f"background-color: {Colors.SURFACE}; border-top: 1px solid {Colors.BORDER};"
        )
        stats_footer_layout = QHBoxLayout(stats_footer)
        stats_footer_layout.setContentsMargins(20, 8, 20, 8)
        stats_footer_layout.setSpacing(8)

        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: 11px; font-weight: 600;"
        )
        stats_label.setToolTip(stats_text)
        stats_footer_layout.addWidget(stats_label)
        stats_footer_layout.addStretch()
        main_layout.addWidget(stats_footer)
        
        # Load source code and execution plan
        self._load_source_code()
        self._load_execution_plan()
        if hasattr(self, "_content_tabs"):
            tab_index = max(0, min(self._content_tabs.count() - 1, self._start_tab))
            self._content_tabs.setCurrentIndex(tab_index)

    def _apply_dialog_style(self) -> None:
        """Apply Query Statistics standard styles to the detail dialog."""
        shared_controls = BaseView._shared_controls_stylesheet()
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {Colors.BACKGROUND};
            }}
            {shared_controls}
            {ThemeStyles.scrollbar_style()}
            """
        )
    
    def _load_source_code(self):
        """Load source code for the query"""
        try:
            if not bool(self._permission_status.get("source_code_enabled", True)):
                self._code_editor.set_text(
                    "-- Source code view is disabled for this connection.\n"
                    "-- Missing VIEW DEFINITION / SELECT on sys.sql_modules."
                )
                return

            # Prefer object definition when object name is available
            if self.query.object_name:
                definition = self.service.get_object_definition(
                    self.query.object_name,
                    getattr(self.query, 'schema_name', None),
                    include_sensitive_data=True,
                )
                if definition:
                    self._code_editor.set_text(definition)
                    return

            # Fallback to query text
            query_text = getattr(self.query, 'query_text', None)
            if query_text:
                self._code_editor.set_text(str(query_text or ""))
                return

            # Try to get from service (Query Store)
            code = self.service.get_query_text(
                self.query.query_id,
                include_sensitive_data=True,
            )
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
            plan_xml = self.service.get_query_plan_xml(
                self.query.query_id,
                query_hash=getattr(self.query, "query_hash", None),
                include_sensitive_data=self._show_sensitive_data,
            )
            
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

    def _is_active_ai_provider_local(self) -> bool:
        try:
            return bool(get_llm_client().is_active_provider_local())
        except Exception:
            return False

    def _resolve_ai_sensitive_context_policy(self) -> bool:
        if not self._show_sensitive_data:
            return False
        if self._is_active_ai_provider_local():
            return True
        if self._cloud_sensitive_opt_in:
            return True

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Sensitive Data Consent")
        box.setText("Cloud AI provider detected.")
        box.setInformativeText(
            "Raw SQL literals and plan values can include PII/secrets.\n"
            "Allow sending unredacted context for this session?"
        )
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        allow = box.exec() == QMessageBox.StandardButton.Yes
        if allow:
            self._cloud_sensitive_opt_in = True
            if self.parent() is not None and hasattr(self.parent(), "_cloud_ai_sensitive_opt_in"):
                try:
                    setattr(self.parent(), "_cloud_ai_sensitive_opt_in", True)
                except Exception:
                    pass
            logger.warning("Sensitive AI context enabled for cloud provider by explicit user consent.")
        return allow
    
    def _analyze_with_ai(self):
        """Run AI analysis on the query"""
        try:
            from app.ui.components.ai_worker import AIAnalysisWorker

            include_sensitive_for_ai = self._resolve_ai_sensitive_context_policy()
            analysis_context = self.service.build_analysis_context(
                query=self.query,
                target_module="ai_analysis",
                reason="query_detail_ai_analysis",
            )
            context = self._context_pipeline.build_context(
                analysis_context,
                include_sensitive_data=include_sensitive_for_ai,
            )

            # Optional server-level metrics for additional AI context.
            try:
                from app.services.dashboard_service import get_dashboard_service

                dash_service = get_dashboard_service()
                if dash_service.is_connected:
                    dash = dash_service.get_all_metrics()
                    context["server_metrics"] = {
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

            quality = context.get("analysis_context_quality", {}) or {}
            quality_score = int(quality.get("score", 0) or 0)
            quality_conf = str(quality.get("confidence", "Low") or "Low")
            self_critique = bool(quality.get("self_critique_enabled", False))
            self._ai_context_label.setText(
                f"Context Quality: {quality_score}/100 ({quality_conf}) | "
                f"Self-critique: {'ON' if self_critique else 'OFF'}"
            )

            if self._ai_worker is not None and self._ai_worker.isRunning():
                self._ai_status_label.setText("AI analysis is already running...")
                self._content_tabs.setCurrentIndex(2)
                return

            self._content_tabs.setCurrentIndex(2)
            self._ai_result_area.clear()
            self._last_ai_request_payload = None
            self._last_ai_request_file_path = None
            self._ai_status_label.setText("Preparing AI analysis...")
            self._ai_status_label.setStyleSheet(f"""
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
                background-color: #eef2ff;
                border: 1px solid #c7d2fe;
                border-radius: 6px;
                padding: 6px 10px;
            """)
            self._ai_progress.setVisible(True)
            self._ai_progress.setValue(5)
            if hasattr(self, "_analyze_btn"):
                self._analyze_btn.setEnabled(False)
            if hasattr(self, "_ai_save_request_btn"):
                self._ai_save_request_btn.setEnabled(False)

            self._ai_worker = AIAnalysisWorker(context=context)
            self._ai_worker.progress.connect(self._on_ai_worker_progress)
            self._ai_worker.finished.connect(self._on_ai_worker_finished)
            self._ai_worker.error.connect(self._on_ai_worker_error)
            self._ai_worker.start()
        except ImportError as e:
            logger.error(f"AI module not available: {e}")
            QMessageBox.information(self, "AI Analysis", "AI analysis module not available.")
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            QMessageBox.warning(self, "Error", f"AI analysis failed: {e}")

    def _on_ai_worker_progress(self, stage: str, message: str) -> None:
        if stage in self._ai_stage_order:
            idx = self._ai_stage_order.index(stage)
            total = max(len(self._ai_stage_order), 1)
            progress = int(((idx + 1) / total) * 100)
            self._ai_progress.setValue(progress)
        self._ai_status_label.setText(message or "Analyzing...")

    def _on_ai_worker_finished(self, result: str) -> None:
        self._ai_progress.setValue(100)
        self._ai_status_label.setText("Analysis completed.")
        self._ai_status_label.setStyleSheet(f"""
            color: #166534;
            font-size: 11px;
            background-color: #dcfce7;
            border: 1px solid #bbf7d0;
            border-radius: 6px;
            padding: 6px 10px;
        """)
        self._ai_result_area.setMarkdown(result or "")
        self._ai_result_area.setStyleSheet(f"""
            QTextEdit {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 11px;
                background-color: #f0fdf4;
                border: 1px solid #d1fae5;
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        try:
            if self._ai_worker is not None:
                self._last_ai_request_payload = self._ai_worker.service.get_last_request_payload()
                self._last_ai_request_file_path = self._ai_worker.service.get_last_request_file_path()
        except Exception:
            self._last_ai_request_payload = None
            self._last_ai_request_file_path = None
        if hasattr(self, "_ai_copy_btn"):
            self._ai_copy_btn.setEnabled(True)
        if hasattr(self, "_ai_save_btn"):
            self._ai_save_btn.setEnabled(True)
        if hasattr(self, "_ai_save_request_btn"):
            self._ai_save_request_btn.setEnabled(bool(self._last_ai_request_payload))
        if hasattr(self, "_analyze_btn"):
            self._analyze_btn.setEnabled(True)

    def _on_ai_worker_error(self, error_msg: str) -> None:
        self._ai_progress.setValue(0)
        self._ai_status_label.setText("AI analysis failed.")
        self._ai_status_label.setStyleSheet(f"""
            color: #991b1b;
            font-size: 11px;
            background-color: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 6px;
            padding: 6px 10px;
        """)
        self._ai_result_area.setText(f"❌ Error: {error_msg}")
        self._ai_result_area.setStyleSheet(f"""
            QTextEdit {{
                color: #991b1b;
                font-size: 11px;
                background-color: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        if hasattr(self, "_ai_copy_btn"):
            self._ai_copy_btn.setEnabled(False)
        if hasattr(self, "_ai_save_btn"):
            self._ai_save_btn.setEnabled(False)
        if hasattr(self, "_ai_save_request_btn"):
            self._ai_save_request_btn.setEnabled(False)
        if hasattr(self, "_analyze_btn"):
            self._analyze_btn.setEnabled(True)

    def _copy_ai_result(self) -> None:
        from PyQt6.QtWidgets import QApplication

        text = self._ai_result_area.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Copy", "No AI analysis result to copy.")
            return
        QApplication.clipboard().setText(text)
        self._ai_status_label.setText("Result copied to clipboard.")

    def _save_ai_result(self) -> None:
        text = self._ai_result_area.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Report", "No AI analysis result to save.")
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save AI Report",
            f"AI_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            "HTML (*.html);;Markdown (*.md);;Text (*.txt)"
        )
        if not path:
            return

        try:
            lower_path = path.lower()
            if lower_path.endswith(".html") or "HTML" in selected_filter:
                content = self._ai_result_area.toHtml()
            else:
                content = self._ai_result_area.toPlainText()

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._ai_status_label.setText("Report saved successfully.")
        except Exception as exc:
            QMessageBox.warning(self, "Report", f"Failed to save report: {exc}")

    def _save_ai_request_payload(self) -> None:
        payload = self._last_ai_request_payload
        if not payload:
            QMessageBox.information(self, "LLM Request", "No LLM request payload available.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save LLM Request Payload",
            f"LLM_Request_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON (*.json)"
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._ai_status_label.setText("LLM request saved successfully.")
        except Exception as exc:
            QMessageBox.warning(self, "LLM Request", f"Failed to save LLM request: {exc}")
