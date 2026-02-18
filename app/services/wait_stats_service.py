"""
Wait Statistics Service - SQL Server wait analysis
"""

from __future__ import annotations

import json
import re
import csv
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter, sleep
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.logger import get_logger
from app.database.connection import get_connection_manager
from app.database.queries.wait_stats_queries import (
    WaitCategory,
    WaitStatsQueries,
    get_category_color,
    get_wait_category,
    resolve_wait_category_text,
)
from app.models.analysis_context import AnalysisContext
from app.services.analysis_message_bus import get_analysis_message_bus
from app.services.blocking_service import BlockingService

logger = get_logger("services.wait_stats")

MAX_HISTORY_SNAPSHOTS = 4000
MAX_TELEMETRY_SNAPSHOTS = 5000


@dataclass
class WaitStat:
    """Single wait type statistics"""

    wait_type: str
    category: WaitCategory
    waiting_tasks: int = 0
    wait_time_ms: int = 0
    max_wait_time_ms: int = 0
    signal_wait_ms: int = 0
    resource_wait_ms: int = 0
    wait_percent: float = 0.0
    cumulative_percent: float = 0.0

    @property
    def category_color(self) -> str:
        return get_category_color(self.category)


@dataclass
class CurrentWait:
    """Currently waiting task"""

    session_id: int
    wait_type: str
    wait_time_ms: int
    wait_resource: str
    blocking_session_id: int
    login_name: str
    host_name: str
    program_name: str
    database_name: str
    current_statement: str


@dataclass
class WaitSummary:
    """Wait statistics summary"""

    total_wait_types: int = 0
    total_waiting_tasks: int = 0
    total_wait_time_ms: int = 0
    total_signal_wait_ms: int = 0
    total_resource_wait_ms: int = 0
    max_single_wait_ms: int = 0
    signal_wait_percent: float = 0.0
    resource_wait_percent: float = 0.0
    category_stats: Dict[WaitCategory, int] = field(default_factory=dict)
    top_waits: List[WaitStat] = field(default_factory=list)
    all_waits: List[WaitStat] = field(default_factory=list)
    current_waits: List[CurrentWait] = field(default_factory=list)
    collected_at: datetime = field(default_factory=datetime.now)


@dataclass
class WaitSignature:
    """Detected wait pattern/signature."""

    signature_id: str
    title: str
    dominant_category: WaitCategory
    confidence: float
    evidence: List[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class WaitBaselineSnapshot:
    """Persisted baseline snapshot."""

    captured_at: datetime
    total_wait_time_ms: int
    signal_wait_percent: float
    resource_wait_percent: float
    category_stats: Dict[str, int] = field(default_factory=dict)
    top_wait_types: List[str] = field(default_factory=list)


@dataclass
class WaitBaselineComparison:
    """Baseline comparison result."""

    baseline_available: bool = False
    baseline_captured_at: Optional[datetime] = None
    baseline_age_hours: float = 0.0
    delta_total_wait_ms: int = 0
    delta_signal_wait_percent: float = 0.0
    delta_resource_wait_percent: float = 0.0
    delta_category_wait_ms: Dict[str, int] = field(default_factory=dict)
    status: str = "no-baseline"
    summary: str = "No baseline configured."


@dataclass
class WaitTrendPoint:
    """Historical trend point for a single day."""

    trend_date: str
    total_wait_ms: int
    dominant_category: str
    dominant_wait_ms: int
    category_wait_ms: Dict[str, int] = field(default_factory=dict)
    category_percent: Dict[str, float] = field(default_factory=dict)


@dataclass
class CustomWaitCategoryRule:
    """User-defined wait category rule."""

    name: str
    pattern: str
    color: str = "#64748B"
    enabled: bool = True


@dataclass
class WaitAlertThresholds:
    """Threshold configuration for real-time alerts."""

    total_wait_time_ms: int = 2_000_000
    lock_wait_percent: float = 15.0
    io_wait_percent: float = 30.0
    blocked_sessions: int = 3
    chain_depth: int = 3
    single_wait_ms: int = 60_000


@dataclass
class WaitAlert:
    """Triggered threshold alert."""

    alert_id: str
    severity: str
    title: str
    message: str
    metric_value: float
    threshold_value: float
    triggered_at: datetime = field(default_factory=datetime.now)


@dataclass
class WaitComparativeSnapshot:
    """Persisted before/after snapshot."""

    slot: str
    captured_at: datetime
    total_wait_time_ms: int
    signal_wait_percent: float
    resource_wait_percent: float
    category_stats: Dict[str, int] = field(default_factory=dict)


@dataclass
class WaitComparativeAnalysis:
    """Before/after comparison output."""

    before_available: bool = False
    after_available: bool = False
    before_captured_at: Optional[datetime] = None
    after_captured_at: Optional[datetime] = None
    delta_total_wait_ms: int = 0
    delta_signal_wait_percent: float = 0.0
    delta_resource_wait_percent: float = 0.0
    delta_category_wait_ms: Dict[str, int] = field(default_factory=dict)
    status: str = "insufficient-data"
    summary: str = "Capture both BEFORE and AFTER snapshots to compare change impact."


@dataclass
class WaitStatsFilter:
    """Advanced filter for wait views."""

    database_name: str = ""
    application_name: str = ""
    time_window_days: int = 7
    min_wait_time_ms: int = 0


@dataclass
class WaitPlanCorrelation:
    """Correlation between wait profile and query execution plan."""

    query_id: int = 0
    plan_available: bool = False
    dominant_wait_categories: List[str] = field(default_factory=list)
    plan_summary: str = ""
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class MultiServerWaitSnapshot:
    """Latest wait snapshot per server/database."""

    server: str
    database: str
    captured_at: datetime
    total_wait_time_ms: int
    signal_wait_percent: float
    top_category: str
    delta_wait_ms_window: int = 0


@dataclass
class WaitMonitoringTarget:
    """External monitoring integration target."""

    name: str
    url: str
    payload_format: str = "json"  # json or prometheus
    enabled: bool = True
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class WaitScheduleConfig:
    """Scheduled snapshot/report configuration."""

    enabled: bool = False
    interval_minutes: int = 15
    output_dir: str = ""
    formats: List[str] = field(default_factory=lambda: ["json", "md"])


@dataclass
class WaitStatsMetrics:
    """Refresh telemetry for wait statistics collection."""

    load_duration_ms: int = 0
    query_count: int = 0
    total_retries: int = 0
    retry_counts: Dict[str, int] = field(default_factory=dict)
    query_durations_ms: Dict[str, int] = field(default_factory=dict)
    rows_by_operation: Dict[str, int] = field(default_factory=dict)
    partial_data: bool = False
    connection_lost: bool = False
    error_count: int = 0
    errors: List[str] = field(default_factory=list)
    correlation_used: bool = False
    correlation_rows: int = 0
    top_waits_count: int = 0
    current_waits_count: int = 0
    signatures_detected: int = 0
    primary_signature: str = ""
    baseline_available: bool = False
    baseline_delta_total_wait_ms: int = 0
    trend_source: str = ""
    trend_points: int = 0
    wait_chain_nodes: int = 0
    wait_chain_edges: int = 0
    wait_chain_roots: int = 0
    alerts_triggered: int = 0
    critical_alerts: int = 0
    custom_category_rules: int = 0
    comparative_status: str = ""
    multi_server_snapshots: int = 0
    plan_correlation_available: bool = False
    plan_correlation_confidence: float = 0.0
    collected_at: datetime = field(default_factory=datetime.now)

    def to_lightweight_contract(self) -> Dict[str, Any]:
        """Compact telemetry payload for low-overhead logging/export."""
        return {
            "collected_at": self.collected_at.isoformat(timespec="seconds"),
            "load_duration_ms": int(self.load_duration_ms or 0),
            "query_count": int(self.query_count or 0),
            "total_retries": int(self.total_retries or 0),
            "partial_data": bool(self.partial_data),
            "connection_lost": bool(self.connection_lost),
            "error_count": int(self.error_count or 0),
            "top_waits_count": int(self.top_waits_count or 0),
            "current_waits_count": int(self.current_waits_count or 0),
            "signatures_detected": int(self.signatures_detected or 0),
            "primary_signature": str(self.primary_signature or ""),
            "trend_source": str(self.trend_source or ""),
            "trend_points": int(self.trend_points or 0),
            "wait_chain_edges": int(self.wait_chain_edges or 0),
            "alerts_triggered": int(self.alerts_triggered or 0),
            "critical_alerts": int(self.critical_alerts or 0),
            "comparative_status": str(self.comparative_status or ""),
            "multi_server_snapshots": int(self.multi_server_snapshots or 0),
            "plan_correlation_available": bool(self.plan_correlation_available),
            "plan_correlation_confidence": float(self.plan_correlation_confidence or 0.0),
            "errors": [str(item) for item in list(self.errors or [])[:5]],
        }


class WaitStatsService:
    """
    Service for collecting and analyzing wait statistics.
    """

    _instance: Optional["WaitStatsService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._last_context = None
            cls._instance._is_subscribed = False
            cls._instance._ensure_subscription()
        return cls._instance

    def _ensure_subscription(self) -> None:
        if self._is_subscribed:
            return
        get_analysis_message_bus().subscribe("wait_stats", self.receive_context)
        self._is_subscribed = True

    @property
    def connection(self):
        """Get active database connection."""
        conn_mgr = get_connection_manager()
        return conn_mgr.active_connection

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        conn = self.connection
        return conn is not None and conn.is_connected

    def get_blocking_service(self) -> BlockingService:
        """Lazily provision unified blocking service for cross-view reuse."""
        service = getattr(self, "_blocking_service", None)
        if service is None:
            service = BlockingService()
            setattr(self, "_blocking_service", service)
        return service

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value or 0)
        except Exception:
            return 0

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    def _active_server_database(self) -> Tuple[str, str]:
        conn = self.connection
        if conn is None:
            return "unknown", "unknown"
        profile = getattr(conn, "profile", None)
        server = str(getattr(profile, "server", "") or "unknown")
        database = str(getattr(profile, "database", "") or "unknown")
        return server, database

    @staticmethod
    def _is_connection_error(exc: Exception) -> bool:
        text = str(exc).lower()
        markers = (
            "not connected",
            "connection",
            "communication link failure",
            "forcibly closed",
            "transport-level error",
            "08s01",
            "08001",
            "connection reset",
            "server has gone away",
        )
        return any(marker in text for marker in markers)

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        text = str(exc).lower()
        markers = (
            "timeout",
            "deadlock victim",
            "temporarily unavailable",
            "transport-level error",
            "communication link failure",
            "connection was forcibly closed",
            "could not open a connection",
            "try again",
        )
        return any(marker in text for marker in markers)

    def _baseline_file_path(self) -> Path:
        path = get_settings().data_dir / "wait_stats_baseline.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _history_file_path(self) -> Path:
        path = get_settings().data_dir / "wait_stats_history.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _scheduled_history_file_path(self) -> Path:
        path = get_settings().data_dir / "wait_stats_scheduled_history.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _custom_categories_file_path(self) -> Path:
        path = get_settings().data_dir / "wait_stats_custom_categories.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _thresholds_file_path(self) -> Path:
        path = get_settings().data_dir / "wait_stats_alert_thresholds.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _comparative_file_path(self) -> Path:
        path = get_settings().data_dir / "wait_stats_before_after.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _schedule_config_file_path(self) -> Path:
        path = get_settings().data_dir / "wait_stats_schedule_config.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _monitoring_targets_file_path(self) -> Path:
        path = get_settings().data_dir / "wait_stats_monitoring_targets.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _telemetry_file_path(self) -> Path:
        path = get_settings().data_dir / "wait_stats_telemetry.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _scheduled_reports_dir(self) -> Path:
        root = get_settings().data_dir / "reports" / "wait_stats"
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception:
            return default

    @staticmethod
    def _write_json(path: Path, payload: Any) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def _execute_query_with_retry(
        self,
        conn: Any,
        sql: str,
        operation_name: str,
        params: Optional[Dict[str, Any]] = None,
        max_attempts: int = 3,
        base_backoff_seconds: float = 0.2,
        retry_callback: Optional[Callable[[str, int, int, float, Exception], None]] = None,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Execute DB query with retry for transient failures.

        Returns:
            rows, retries_used, duration_ms
        """
        started = perf_counter()
        attempts = max(1, int(max_attempts))
        backoff = max(0.05, float(base_backoff_seconds))
        last_error: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            if not self.is_connected:
                err = RuntimeError("No active database connection")
                setattr(err, "wait_retry_attempts", attempt - 1)
                raise err

            try:
                rows = conn.execute_query(sql, params)
                duration_ms = int((perf_counter() - started) * 1000)
                return list(rows or []), attempt - 1, duration_ms
            except Exception as ex:
                last_error = ex
                retryable = self._is_transient_error(ex)
                if (not retryable) or attempt >= attempts:
                    setattr(ex, "wait_retry_attempts", attempt - 1)
                    raise

                if callable(retry_callback):
                    try:
                        retry_callback(operation_name, attempt, attempts, backoff, ex)
                    except Exception:
                        pass

                logger.warning(
                    f"{operation_name} failed (attempt {attempt}/{attempts}): {ex}. "
                    f"Retrying in {backoff:.2f}s..."
                )
                sleep(backoff)
                backoff = min(backoff * 2.0, 1.5)

        if last_error is not None:
            raise last_error
        return [], 0, int((perf_counter() - started) * 1000)

    def _map_top_wait_rows(self, rows: List[Dict[str, Any]]) -> List[WaitStat]:
        waits: List[WaitStat] = []
        for row in rows or []:
            wait_type = str(row.get("wait_type", "") or "")
            waits.append(
                WaitStat(
                    wait_type=wait_type,
                    category=get_wait_category(wait_type),
                    waiting_tasks=self._safe_int(row.get("waiting_tasks_count", 0)),
                    wait_time_ms=self._safe_int(row.get("wait_time_ms", 0)),
                    max_wait_time_ms=self._safe_int(row.get("max_wait_time_ms", 0)),
                    signal_wait_ms=self._safe_int(row.get("signal_wait_time_ms", 0)),
                    resource_wait_ms=self._safe_int(row.get("resource_wait_time_ms", 0)),
                    wait_percent=self._safe_float(row.get("wait_percent", 0)),
                    cumulative_percent=self._safe_float(row.get("cumulative_percent", 0)),
                )
            )
        return waits

    def _map_all_wait_rows(self, rows: List[Dict[str, Any]]) -> List[WaitStat]:
        waits: List[WaitStat] = []
        for row in rows or []:
            wait_type = str(row.get("wait_type", "") or "")
            waits.append(
                WaitStat(
                    wait_type=wait_type,
                    category=get_wait_category(wait_type),
                    waiting_tasks=self._safe_int(row.get("waiting_tasks_count", 0)),
                    wait_time_ms=self._safe_int(row.get("wait_time_ms", 0)),
                    max_wait_time_ms=0,
                    signal_wait_ms=0,
                    resource_wait_ms=0,
                    wait_percent=0.0,
                    cumulative_percent=0.0,
                )
            )
        return waits

    def _map_category_rows(self, rows: List[Dict[str, Any]]) -> Dict[WaitCategory, int]:
        stats = {cat: 0 for cat in WaitCategory}
        for row in rows or []:
            wait_type = str(row.get("wait_type", "") or "")
            wait_time = self._safe_int(row.get("wait_time_ms", 0))
            category = get_wait_category(wait_type)
            stats[category] += wait_time
        return stats

    def _map_current_wait_rows(self, rows: List[Dict[str, Any]]) -> List[CurrentWait]:
        waits: List[CurrentWait] = []
        for row in rows or []:
            waits.append(
                CurrentWait(
                    session_id=self._safe_int(row.get("session_id", 0)),
                    wait_type=str(row.get("wait_type", "") or ""),
                    wait_time_ms=self._safe_int(row.get("wait_time_ms", 0)),
                    wait_resource=str(row.get("wait_resource", "") or ""),
                    blocking_session_id=self._safe_int(row.get("blocking_session_id", 0)),
                    login_name=str(row.get("login_name", "") or ""),
                    host_name=str(row.get("host_name", "") or ""),
                    program_name=str(row.get("program_name", "") or ""),
                    database_name=str(row.get("database_name", "") or ""),
                    current_statement=str(row.get("current_statement", "") or ""),
                )
            )
        return waits

    def _append_history_snapshot(self, summary: WaitSummary) -> None:
        """Append refresh snapshot for fallback trending."""
        try:
            history_path = self._history_file_path()
            server, database = self._active_server_database()
            snapshot = {
                "captured_at": summary.collected_at.isoformat(),
                "server": server,
                "database": database,
                "total_wait_time_ms": int(summary.total_wait_time_ms or 0),
                "signal_wait_percent": float(summary.signal_wait_percent or 0.0),
                "resource_wait_percent": float(summary.resource_wait_percent or 0.0),
                "category_stats": {
                    str(category.value): int(value or 0)
                    for category, value in (summary.category_stats or {}).items()
                },
            }

            with open(history_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(snapshot, ensure_ascii=False) + "\n")

            # Keep file bounded.
            try:
                with open(history_path, "r", encoding="utf-8") as handle:
                    lines = handle.readlines()
                if len(lines) > MAX_HISTORY_SNAPSHOTS:
                    lines = lines[-MAX_HISTORY_SNAPSHOTS:]
                    with open(history_path, "w", encoding="utf-8") as handle:
                        handle.writelines(lines)
            except Exception:
                pass
        except Exception as ex:
            logger.debug(f"Failed to append wait stats history snapshot: {ex}")

    def _load_recent_history(self, days: int) -> List[Dict[str, Any]]:
        path = self._history_file_path()
        if not path.exists():
            return []

        cutoff = datetime.now() - timedelta(days=max(1, int(days)))
        rows: List[Dict[str, Any]] = []
        try:
            with open(path, "r", encoding="utf-8") as handle:
                for line in handle:
                    raw = line.strip()
                    if not raw:
                        continue
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        continue
                    ts = payload.get("captured_at")
                    try:
                        captured_at = datetime.fromisoformat(str(ts))
                    except Exception:
                        continue
                    if captured_at < cutoff:
                        continue
                    rows.append(payload)
        except Exception as ex:
            logger.debug(f"Failed to read wait stats history: {ex}")
        return rows

    def _trim_jsonl_file(self, path: Path, max_lines: int) -> None:
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
            if len(lines) <= max_lines:
                return
            trimmed = lines[-max_lines:]
            with open(path, "w", encoding="utf-8") as handle:
                handle.writelines(trimmed)
        except Exception as ex:
            logger.debug(f"Failed to trim jsonl file {path.name}: {ex}")

    def record_refresh_telemetry(self, metrics: WaitStatsMetrics) -> bool:
        """Persist compact refresh telemetry for ops visibility."""
        if not isinstance(metrics, WaitStatsMetrics):
            return False
        path = self._telemetry_file_path()
        payload = metrics.to_lightweight_contract()
        try:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            # Periodic maintenance to keep telemetry bounded.
            if int(path.stat().st_size or 0) > 8 * 1024 * 1024:
                self._trim_jsonl_file(path, MAX_TELEMETRY_SNAPSHOTS)
            return True
        except Exception as ex:
            logger.debug(f"Failed to record wait stats telemetry: {ex}")
            return False

    def save_baseline(self, summary: WaitSummary) -> bool:
        """Persist baseline snapshot for later comparison."""
        try:
            baseline = {
                "captured_at": datetime.now().isoformat(),
                "total_wait_time_ms": int(summary.total_wait_time_ms or 0),
                "signal_wait_percent": float(summary.signal_wait_percent or 0.0),
                "resource_wait_percent": float(summary.resource_wait_percent or 0.0),
                "category_stats": {
                    str(category.value): int(value or 0)
                    for category, value in (summary.category_stats or {}).items()
                },
                "top_wait_types": [str(wait.wait_type or "") for wait in (summary.top_waits or [])[:10]],
            }
            with open(self._baseline_file_path(), "w", encoding="utf-8") as handle:
                json.dump(baseline, handle, indent=2)
            return True
        except Exception as ex:
            logger.warning(f"Failed to save wait stats baseline: {ex}")
            return False

    def load_baseline(self) -> Optional[WaitBaselineSnapshot]:
        """Load baseline snapshot if available."""
        path = self._baseline_file_path()
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            captured_at = datetime.fromisoformat(str(payload.get("captured_at")))
            return WaitBaselineSnapshot(
                captured_at=captured_at,
                total_wait_time_ms=self._safe_int(payload.get("total_wait_time_ms", 0)),
                signal_wait_percent=self._safe_float(payload.get("signal_wait_percent", 0.0)),
                resource_wait_percent=self._safe_float(payload.get("resource_wait_percent", 0.0)),
                category_stats={
                    str(k): self._safe_int(v)
                    for k, v in dict(payload.get("category_stats", {}) or {}).items()
                },
                top_wait_types=[str(x) for x in list(payload.get("top_wait_types", []) or [])],
            )
        except Exception as ex:
            logger.warning(f"Failed to load wait stats baseline: {ex}")
            return None

    def compare_to_baseline(self, summary: WaitSummary) -> WaitBaselineComparison:
        """Compare current wait snapshot with baseline."""
        baseline = self.load_baseline()
        if baseline is None:
            return WaitBaselineComparison()

        current_cats = {
            str(category.value): int(value or 0)
            for category, value in (summary.category_stats or {}).items()
        }
        all_keys = sorted(set(current_cats.keys()) | set(baseline.category_stats.keys()))
        delta_cats = {
            key: self._safe_int(current_cats.get(key, 0)) - self._safe_int(baseline.category_stats.get(key, 0))
            for key in all_keys
        }

        delta_total = self._safe_int(summary.total_wait_time_ms) - self._safe_int(baseline.total_wait_time_ms)
        delta_signal = self._safe_float(summary.signal_wait_percent) - baseline.signal_wait_percent
        delta_resource = self._safe_float(summary.resource_wait_percent) - baseline.resource_wait_percent

        status = "stable"
        if delta_total > 0:
            status = "degraded"
        elif delta_total < 0:
            status = "improved"

        age_hours = max(0.0, (datetime.now() - baseline.captured_at).total_seconds() / 3600.0)
        summary_text = (
            f"Baseline {status}: Δwait={delta_total:+,} ms, "
            f"Δsignal={delta_signal:+.2f}%, age={age_hours:.1f}h"
        )
        return WaitBaselineComparison(
            baseline_available=True,
            baseline_captured_at=baseline.captured_at,
            baseline_age_hours=age_hours,
            delta_total_wait_ms=delta_total,
            delta_signal_wait_percent=delta_signal,
            delta_resource_wait_percent=delta_resource,
            delta_category_wait_ms=delta_cats,
            status=status,
            summary=summary_text,
        )

    def analyze_wait_signatures(self, summary: WaitSummary) -> List[WaitSignature]:
        """
        Identify dominant wait signatures (CPU/IO/Lock patterns, etc.).
        """
        category_totals = summary.category_stats or {}
        total_wait_ms = max(1, int(sum(category_totals.values()) or summary.total_wait_time_ms or 1))
        top_waits = list(summary.top_waits or [])

        def cat_percent(category: WaitCategory) -> float:
            return float(category_totals.get(category, 0) or 0) * 100.0 / float(total_wait_ms)

        def has_top_wait(prefixes: Tuple[str, ...]) -> bool:
            normalized = tuple(str(p).upper() for p in prefixes)
            for item in top_waits:
                wt = str(getattr(item, "wait_type", "") or "").upper()
                if any(wt.startswith(prefix) for prefix in normalized):
                    return True
            return False

        signatures: List[WaitSignature] = []

        cpu_pct = cat_percent(WaitCategory.CPU)
        if cpu_pct >= 25.0 or has_top_wait(("SOS_SCHEDULER", "THREADPOOL", "CX")):
            signatures.append(
                WaitSignature(
                    signature_id="cpu_pressure",
                    title="CPU Pressure",
                    dominant_category=WaitCategory.CPU,
                    confidence=min(0.99, max(0.5, cpu_pct / 100.0 + 0.35)),
                    evidence=[
                        f"CPU waits share: {cpu_pct:.1f}%",
                        "Top waits include scheduler/parallelism indicators.",
                    ],
                    recommendation="Review runnable queue, high-CPU queries, and parallelism settings.",
                )
            )

        io_pct = cat_percent(WaitCategory.IO)
        if io_pct >= 25.0 or has_top_wait(("PAGEIO", "WRITELOG", "IO_COMPLETION")):
            signatures.append(
                WaitSignature(
                    signature_id="io_bottleneck",
                    title="I/O Bottleneck",
                    dominant_category=WaitCategory.IO,
                    confidence=min(0.99, max(0.5, io_pct / 100.0 + 0.35)),
                    evidence=[
                        f"I/O waits share: {io_pct:.1f}%",
                        "Top waits include PAGEIOLATCH/WRITELOG patterns.",
                    ],
                    recommendation="Validate storage latency, file layout, and heavy read/write query patterns.",
                )
            )

        lock_pct = cat_percent(WaitCategory.LOCK)
        if lock_pct >= 12.0 or has_top_wait(("LCK_",)):
            signatures.append(
                WaitSignature(
                    signature_id="lock_contention",
                    title="Lock Contention",
                    dominant_category=WaitCategory.LOCK,
                    confidence=min(0.99, max(0.5, lock_pct / 100.0 + 0.4)),
                    evidence=[
                        f"Lock waits share: {lock_pct:.1f}%",
                        "Top waits include LCK_* patterns.",
                    ],
                    recommendation="Check blocking chains, transaction scope, and indexing for lock escalation risk.",
                )
            )

        mem_pct = cat_percent(WaitCategory.MEMORY)
        if mem_pct >= 10.0 or has_top_wait(("RESOURCE_SEMAPHORE", "CMEMTHREAD")):
            signatures.append(
                WaitSignature(
                    signature_id="memory_pressure",
                    title="Memory Grant Pressure",
                    dominant_category=WaitCategory.MEMORY,
                    confidence=min(0.99, max(0.45, mem_pct / 100.0 + 0.4)),
                    evidence=[
                        f"Memory waits share: {mem_pct:.1f}%",
                        "Top waits include RESOURCE_SEMAPHORE/CMEMTHREAD indicators.",
                    ],
                    recommendation="Inspect grant-heavy plans, cardinality estimates, and memory settings.",
                )
            )

        latch_pct = cat_percent(WaitCategory.LATCH)
        if latch_pct >= 12.0 or has_top_wait(("PAGELATCH", "LATCH_")):
            signatures.append(
                WaitSignature(
                    signature_id="latch_contention",
                    title="Latch Contention",
                    dominant_category=WaitCategory.LATCH,
                    confidence=min(0.99, max(0.45, latch_pct / 100.0 + 0.4)),
                    evidence=[
                        f"Latch waits share: {latch_pct:.1f}%",
                        "Top waits include PAGELATCH/LATCH_* indicators.",
                    ],
                    recommendation="Check hot pages (TempDB/object allocation) and reduce page-level contention.",
                )
            )

        net_pct = cat_percent(WaitCategory.NETWORK)
        if net_pct >= 10.0 or has_top_wait(("ASYNC_NETWORK_IO", "NET_")):
            signatures.append(
                WaitSignature(
                    signature_id="network_pressure",
                    title="Network Throughput Pressure",
                    dominant_category=WaitCategory.NETWORK,
                    confidence=min(0.95, max(0.4, net_pct / 100.0 + 0.35)),
                    evidence=[
                        f"Network waits share: {net_pct:.1f}%",
                        "Top waits include ASYNC_NETWORK_IO/NET_* patterns.",
                    ],
                    recommendation="Inspect client fetch behavior, packet latency, and large result-set consumers.",
                )
            )

        if not signatures:
            signatures.append(
                WaitSignature(
                    signature_id="balanced_profile",
                    title="Balanced Wait Profile",
                    dominant_category=WaitCategory.OTHER,
                    confidence=0.6,
                    evidence=["No dominant wait signature crossed thresholds."],
                    recommendation="Continue monitoring; correlate with workload spikes for deeper root-cause.",
                )
            )
        signatures.sort(key=lambda s: s.confidence, reverse=True)
        return signatures

    def get_historical_trend(self, days: int = 7) -> Tuple[List[WaitTrendPoint], str]:
        """
        Historical wait trend for 7/30/90 day style views.
        Source: Query Store (preferred) or local snapshot fallback.
        """
        requested_days = max(1, int(days or 7))
        if self.is_connected and self.connection is not None:
            try:
                rows, _retries, _duration_ms = self._execute_query_with_retry(
                    conn=self.connection,
                    sql=WaitStatsQueries.HISTORICAL_WAIT_TREND,
                    params={"days": requested_days},
                    operation_name="historical_wait_trend",
                    max_attempts=2,
                )
                if rows:
                    return self._build_trend_from_query_store_rows(rows), "query_store"
            except Exception as ex:
                logger.info(f"Historical trend Query Store fallback to local history: {ex}")

        history_rows = self._load_recent_history(requested_days)
        if history_rows:
            return self._build_trend_from_local_history(history_rows), "local_history"
        return [], "none"

    def _build_trend_from_query_store_rows(self, rows: List[Dict[str, Any]]) -> List[WaitTrendPoint]:
        grouped: Dict[str, Dict[str, int]] = {}
        for row in rows or []:
            trend_date_obj = row.get("trend_date")
            if isinstance(trend_date_obj, datetime):
                date_key = trend_date_obj.date().isoformat()
            else:
                date_key = str(trend_date_obj or "")
                if " " in date_key:
                    date_key = date_key.split(" ", 1)[0]
            if not date_key:
                continue
            category = resolve_wait_category_text(str(row.get("wait_category", "") or ""))
            cat_key = str(category.value)
            grouped.setdefault(date_key, {})
            grouped[date_key][cat_key] = grouped[date_key].get(cat_key, 0) + self._safe_int(row.get("total_wait_ms", 0))

        points: List[WaitTrendPoint] = []
        for date_key in sorted(grouped.keys()):
            categories = grouped[date_key]
            total_wait = sum(categories.values())
            dominant_category = max(categories, key=lambda k: categories.get(k, 0)) if categories else "Other"
            dominant_wait = self._safe_int(categories.get(dominant_category, 0))
            pct = {
                cat: (self._safe_int(value) * 100.0 / float(max(1, total_wait)))
                for cat, value in categories.items()
            }
            points.append(
                WaitTrendPoint(
                    trend_date=date_key,
                    total_wait_ms=total_wait,
                    dominant_category=dominant_category,
                    dominant_wait_ms=dominant_wait,
                    category_wait_ms={cat: self._safe_int(v) for cat, v in categories.items()},
                    category_percent={cat: round(float(v), 2) for cat, v in pct.items()},
                )
            )
        return points

    def _build_trend_from_local_history(self, rows: List[Dict[str, Any]]) -> List[WaitTrendPoint]:
        grouped: Dict[str, Dict[str, int]] = {}
        for row in rows:
            ts = str(row.get("captured_at", "") or "")
            if not ts:
                continue
            try:
                captured = datetime.fromisoformat(ts)
                date_key = captured.date().isoformat()
            except Exception:
                continue
            cat_stats = dict(row.get("category_stats", {}) or {})
            grouped.setdefault(date_key, {})
            for category_name, wait_ms in cat_stats.items():
                key = str(resolve_wait_category_text(category_name).value)
                grouped[date_key][key] = grouped[date_key].get(key, 0) + self._safe_int(wait_ms)

        points: List[WaitTrendPoint] = []
        for date_key in sorted(grouped.keys()):
            categories = grouped[date_key]
            total_wait = sum(categories.values())
            dominant_category = max(categories, key=lambda k: categories.get(k, 0)) if categories else "Other"
            dominant_wait = self._safe_int(categories.get(dominant_category, 0))
            pct = {
                cat: (self._safe_int(value) * 100.0 / float(max(1, total_wait)))
                for cat, value in categories.items()
            }
            points.append(
                WaitTrendPoint(
                    trend_date=date_key,
                    total_wait_ms=total_wait,
                    dominant_category=dominant_category,
                    dominant_wait_ms=dominant_wait,
                    category_wait_ms={cat: self._safe_int(v) for cat, v in categories.items()},
                    category_percent={cat: round(float(v), 2) for cat, v in pct.items()},
                )
            )
        return points

    def load_custom_category_rules(self) -> List[CustomWaitCategoryRule]:
        payload = self._read_json(self._custom_categories_file_path(), default=[])
        rules: List[CustomWaitCategoryRule] = []
        for item in list(payload or []):
            try:
                name = str(item.get("name", "") or "").strip()
                pattern = str(item.get("pattern", "") or "").strip()
                if not name or not pattern:
                    continue
                rules.append(
                    CustomWaitCategoryRule(
                        name=name,
                        pattern=pattern,
                        color=str(item.get("color", "#64748B") or "#64748B"),
                        enabled=bool(item.get("enabled", True)),
                    )
                )
            except Exception:
                continue
        return rules

    def save_custom_category_rules(self, rules: List[CustomWaitCategoryRule]) -> bool:
        payload = [asdict(rule) for rule in (rules or [])]
        return self._write_json(self._custom_categories_file_path(), payload)

    def add_custom_category_rule(self, name: str, pattern: str, color: str = "#64748B") -> bool:
        clean_name = str(name or "").strip()
        clean_pattern = str(pattern or "").strip()
        if not clean_name or not clean_pattern:
            return False
        try:
            re.compile(clean_pattern, re.IGNORECASE)
        except re.error:
            return False

        rules = self.load_custom_category_rules()
        for rule in rules:
            if rule.name.lower() == clean_name.lower() and rule.pattern == clean_pattern:
                return True
        rules.append(CustomWaitCategoryRule(name=clean_name, pattern=clean_pattern, color=color, enabled=True))
        return self.save_custom_category_rules(rules)

    def remove_custom_category_rule(self, name: str, pattern: Optional[str] = None) -> bool:
        clean_name = str(name or "").strip().lower()
        clean_pattern = str(pattern or "").strip() if pattern else None
        rules = self.load_custom_category_rules()
        kept: List[CustomWaitCategoryRule] = []
        removed = False
        for rule in rules:
            if removed:
                kept.append(rule)
                continue
            match_name = rule.name.lower() == clean_name
            match_pattern = clean_pattern is None or rule.pattern == clean_pattern
            if match_name and match_pattern:
                removed = True
                continue
            kept.append(rule)
        if not removed:
            return False
        return self.save_custom_category_rules(kept)

    def build_custom_category_breakdown(
        self,
        waits: List[WaitStat],
        rules: Optional[List[CustomWaitCategoryRule]] = None,
    ) -> Dict[str, int]:
        active_rules = [rule for rule in (rules or self.load_custom_category_rules()) if rule.enabled]
        if not active_rules:
            return {}

        compiled: List[Tuple[CustomWaitCategoryRule, re.Pattern[str]]] = []
        for rule in active_rules:
            try:
                compiled.append((rule, re.compile(rule.pattern, re.IGNORECASE)))
            except re.error:
                logger.warning(f"Skipping invalid custom wait category regex: {rule.pattern}")

        totals: Dict[str, int] = {}
        for wait in waits or []:
            wait_type = str(wait.wait_type or "")
            for rule, pattern in compiled:
                if pattern.search(wait_type):
                    totals[rule.name] = totals.get(rule.name, 0) + self._safe_int(wait.wait_time_ms)
                    break
        return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))

    @staticmethod
    def _severity_order(value: str) -> int:
        mapping = {"critical": 0, "warning": 1, "info": 2}
        return mapping.get(str(value or "").lower(), 9)

    def load_alert_thresholds(self) -> WaitAlertThresholds:
        payload = dict(self._read_json(self._thresholds_file_path(), default={}) or {})
        defaults = WaitAlertThresholds()
        return WaitAlertThresholds(
            total_wait_time_ms=max(1, self._safe_int(payload.get("total_wait_time_ms", defaults.total_wait_time_ms))),
            lock_wait_percent=max(0.0, self._safe_float(payload.get("lock_wait_percent", defaults.lock_wait_percent))),
            io_wait_percent=max(0.0, self._safe_float(payload.get("io_wait_percent", defaults.io_wait_percent))),
            blocked_sessions=max(1, self._safe_int(payload.get("blocked_sessions", defaults.blocked_sessions))),
            chain_depth=max(1, self._safe_int(payload.get("chain_depth", defaults.chain_depth))),
            single_wait_ms=max(1, self._safe_int(payload.get("single_wait_ms", defaults.single_wait_ms))),
        )

    def save_alert_thresholds(self, thresholds: WaitAlertThresholds) -> bool:
        payload = {
            "total_wait_time_ms": int(thresholds.total_wait_time_ms or 0),
            "lock_wait_percent": float(thresholds.lock_wait_percent or 0.0),
            "io_wait_percent": float(thresholds.io_wait_percent or 0.0),
            "blocked_sessions": int(thresholds.blocked_sessions or 0),
            "chain_depth": int(thresholds.chain_depth or 0),
            "single_wait_ms": int(thresholds.single_wait_ms or 0),
        }
        return self._write_json(self._thresholds_file_path(), payload)

    def evaluate_threshold_alerts(
        self,
        summary: WaitSummary,
        chain: Any,
        thresholds: Optional[WaitAlertThresholds] = None,
    ) -> List[WaitAlert]:
        limits = thresholds or self.load_alert_thresholds()
        alerts: List[WaitAlert] = []

        total_wait_ms = self._safe_int(summary.total_wait_time_ms)
        total_category_wait = max(1, sum((summary.category_stats or {}).values()))
        lock_wait_pct = (self._safe_int((summary.category_stats or {}).get(WaitCategory.LOCK, 0)) * 100.0) / float(total_category_wait)
        io_wait_pct = (self._safe_int((summary.category_stats or {}).get(WaitCategory.IO, 0)) * 100.0) / float(total_category_wait)
        resource_wait_ratio = self._safe_float(summary.resource_wait_percent)
        max_current_wait = max((self._safe_int(w.wait_time_ms) for w in (summary.current_waits or [])), default=0)
        waits = list(summary.top_waits or [])
        total_top_wait_ms = max(1, sum(self._safe_int(item.wait_time_ms) for item in waits))
        pageiolatch_ms = sum(
            self._safe_int(item.wait_time_ms) for item in waits if str(item.wait_type or "").upper().startswith("PAGEIOLATCH")
        )
        pageiolatch_pct = float(pageiolatch_ms) * 100.0 / float(total_top_wait_ms)
        async_io_ms = sum(
            self._safe_int(item.wait_time_ms)
            for item in waits
            if str(item.wait_type or "").upper().startswith(("ASYNC_IO_COMPLETION", "BACKUPBUFFER", "BACKUPIO"))
        )
        async_io_pct = float(async_io_ms) * 100.0 / float(total_top_wait_ms)
        cx_ms = sum(
            self._safe_int(item.wait_time_ms)
            for item in waits
            if str(item.wait_type or "").upper().startswith(("CXPACKET", "CXCONSUMER", "CXSYNC"))
        )
        cx_pct = float(cx_ms) * 100.0 / float(total_top_wait_ms)
        latch_wait_pct = (self._safe_int((summary.category_stats or {}).get(WaitCategory.LATCH, 0)) * 100.0) / float(total_category_wait)

        if total_wait_ms >= limits.total_wait_time_ms:
            total_wait_severity = "critical" if total_wait_ms >= max(limits.total_wait_time_ms * 5, 30_000_000) else "warning"
            alerts.append(
                WaitAlert(
                    alert_id="total_wait_high",
                    severity=total_wait_severity,
                    title="Total Wait Time Threshold Breached",
                    message=f"Total wait time {total_wait_ms:,} ms is above threshold {limits.total_wait_time_ms:,} ms.",
                    metric_value=float(total_wait_ms),
                    threshold_value=float(limits.total_wait_time_ms),
                )
            )

        if lock_wait_pct >= limits.lock_wait_percent:
            alerts.append(
                WaitAlert(
                    alert_id="lock_wait_high",
                    severity="critical" if lock_wait_pct >= max(25.0, limits.lock_wait_percent * 1.5) else "warning",
                    title="Lock Wait Pressure",
                    message=f"Lock wait share is {lock_wait_pct:.1f}% (threshold {limits.lock_wait_percent:.1f}%).",
                    metric_value=lock_wait_pct,
                    threshold_value=limits.lock_wait_percent,
                )
            )

        if io_wait_pct >= limits.io_wait_percent:
            alerts.append(
                WaitAlert(
                    alert_id="io_wait_high",
                    severity="critical" if io_wait_pct >= max(50.0, limits.io_wait_percent * 1.8) else "warning",
                    title="I/O Wait Pressure",
                    message=f"I/O wait share is {io_wait_pct:.1f}% (threshold {limits.io_wait_percent:.1f}%).",
                    metric_value=io_wait_pct,
                    threshold_value=limits.io_wait_percent,
                )
            )

        if resource_wait_ratio >= 80.0:
            alerts.append(
                WaitAlert(
                    alert_id="resource_wait_ratio_high",
                    severity="critical" if resource_wait_ratio >= 90.0 else "warning",
                    title="Resource Wait Ratio High",
                    message=(
                        f"Resource wait ratio is {resource_wait_ratio:.1f}% "
                        "(recommended < 80.0%)."
                    ),
                    metric_value=resource_wait_ratio,
                    threshold_value=80.0,
                )
            )

        if pageiolatch_pct >= 30.0:
            alerts.append(
                WaitAlert(
                    alert_id="pageiolatch_share_high",
                    severity="warning",
                    title="PAGEIOLATCH Dominance",
                    message=f"PAGEIOLATCH waits account for {pageiolatch_pct:.1f}% of top wait time.",
                    metric_value=pageiolatch_pct,
                    threshold_value=30.0,
                )
            )

        if async_io_pct >= 20.0:
            alerts.append(
                WaitAlert(
                    alert_id="async_io_spike",
                    severity="warning",
                    title="ASYNC/BACKUP I/O Spike",
                    message=f"ASYNC_IO/BACKUP waits represent {async_io_pct:.1f}% of top wait time.",
                    metric_value=async_io_pct,
                    threshold_value=20.0,
                )
            )

        if cx_pct >= 10.0 and latch_wait_pct >= 10.0:
            alerts.append(
                WaitAlert(
                    alert_id="parallel_latch_combo",
                    severity="warning",
                    title="Parallelism + Latch Combo",
                    message=(
                        f"CX waits {cx_pct:.1f}% with latch share {latch_wait_pct:.1f}% "
                        "suggests MAXDOP/parallelism tuning opportunity."
                    ),
                    metric_value=max(cx_pct, latch_wait_pct),
                    threshold_value=10.0,
                )
            )

        chain_blocked_sessions = self._chain_total_blocked_sessions(chain)
        chain_depth = self._chain_max_depth(chain)

        if chain_blocked_sessions >= limits.blocked_sessions:
            alerts.append(
                WaitAlert(
                    alert_id="blocked_sessions_high",
                    severity="critical",
                    title="Blocked Session Count High",
                    message=(
                        f"{chain_blocked_sessions} blocked session(s) detected "
                        f"(threshold {limits.blocked_sessions})."
                    ),
                    metric_value=float(chain_blocked_sessions),
                    threshold_value=float(limits.blocked_sessions),
                )
            )

        if chain_depth >= limits.chain_depth:
            alerts.append(
                WaitAlert(
                    alert_id="blocking_depth_high",
                    severity="critical",
                    title="Blocking Chain Depth High",
                    message=f"Blocking chain depth {chain_depth} (threshold {limits.chain_depth}).",
                    metric_value=float(chain_depth),
                    threshold_value=float(limits.chain_depth),
                )
            )

        if max_current_wait >= limits.single_wait_ms:
            alerts.append(
                WaitAlert(
                    alert_id="single_wait_high",
                    severity="warning",
                    title="Long Individual Wait Detected",
                    message=f"Longest active wait is {max_current_wait:,} ms (threshold {limits.single_wait_ms:,} ms).",
                    metric_value=float(max_current_wait),
                    threshold_value=float(limits.single_wait_ms),
                )
            )

        return sorted(alerts, key=lambda item: (self._severity_order(item.severity), -item.metric_value))

    @staticmethod
    def _summary_snapshot(summary: WaitSummary, slot: str) -> Dict[str, Any]:
        return {
            "slot": slot,
            "captured_at": datetime.now().isoformat(),
            "total_wait_time_ms": int(summary.total_wait_time_ms or 0),
            "signal_wait_percent": float(summary.signal_wait_percent or 0.0),
            "resource_wait_percent": float(summary.resource_wait_percent or 0.0),
            "category_stats": {
                str(category.value): int(value or 0)
                for category, value in (summary.category_stats or {}).items()
            },
        }

    def save_comparative_snapshot(self, slot: str, summary: WaitSummary) -> bool:
        clean_slot = str(slot or "").strip().lower()
        if clean_slot not in {"before", "after"}:
            return False
        payload = dict(self._read_json(self._comparative_file_path(), default={}) or {})
        payload[clean_slot] = self._summary_snapshot(summary, clean_slot)
        return self._write_json(self._comparative_file_path(), payload)

    def _load_comparative_snapshots(self) -> Dict[str, WaitComparativeSnapshot]:
        payload = dict(self._read_json(self._comparative_file_path(), default={}) or {})
        snapshots: Dict[str, WaitComparativeSnapshot] = {}
        for slot in ("before", "after"):
            raw = payload.get(slot)
            if not isinstance(raw, dict):
                continue
            try:
                snapshots[slot] = WaitComparativeSnapshot(
                    slot=slot,
                    captured_at=datetime.fromisoformat(str(raw.get("captured_at"))),
                    total_wait_time_ms=self._safe_int(raw.get("total_wait_time_ms", 0)),
                    signal_wait_percent=self._safe_float(raw.get("signal_wait_percent", 0.0)),
                    resource_wait_percent=self._safe_float(raw.get("resource_wait_percent", 0.0)),
                    category_stats={
                        str(k): self._safe_int(v)
                        for k, v in dict(raw.get("category_stats", {}) or {}).items()
                    },
                )
            except Exception:
                continue
        return snapshots

    def compare_before_after(self) -> WaitComparativeAnalysis:
        snapshots = self._load_comparative_snapshots()
        before = snapshots.get("before")
        after = snapshots.get("after")
        if not before or not after:
            return WaitComparativeAnalysis(
                before_available=before is not None,
                after_available=after is not None,
                before_captured_at=before.captured_at if before else None,
                after_captured_at=after.captured_at if after else None,
            )

        delta_total = after.total_wait_time_ms - before.total_wait_time_ms
        delta_signal = after.signal_wait_percent - before.signal_wait_percent
        delta_resource = after.resource_wait_percent - before.resource_wait_percent
        all_keys = sorted(set(before.category_stats.keys()) | set(after.category_stats.keys()))
        delta_cats = {
            key: self._safe_int(after.category_stats.get(key, 0)) - self._safe_int(before.category_stats.get(key, 0))
            for key in all_keys
        }

        if delta_total < 0:
            status = "improved"
        elif delta_total > 0:
            status = "degraded"
        else:
            status = "stable"

        summary = (
            f"Before/After {status}: Δwait={delta_total:+,} ms, "
            f"Δsignal={delta_signal:+.2f}%, "
            f"before={before.captured_at.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"after={after.captured_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return WaitComparativeAnalysis(
            before_available=True,
            after_available=True,
            before_captured_at=before.captured_at,
            after_captured_at=after.captured_at,
            delta_total_wait_ms=delta_total,
            delta_signal_wait_percent=delta_signal,
            delta_resource_wait_percent=delta_resource,
            delta_category_wait_ms=delta_cats,
            status=status,
            summary=summary,
        )

    def filter_current_waits(
        self,
        waits: List[CurrentWait],
        database_name: str = "",
        application_name: str = "",
        min_wait_time_ms: int = 0,
    ) -> List[CurrentWait]:
        db_filter = str(database_name or "").strip().lower()
        app_filter = str(application_name or "").strip().lower()
        min_wait = max(0, int(min_wait_time_ms or 0))
        filtered: List[CurrentWait] = []
        for wait in waits or []:
            if min_wait and self._safe_int(wait.wait_time_ms) < min_wait:
                continue
            if db_filter and db_filter not in str(wait.database_name or "").lower():
                continue
            if app_filter and app_filter not in str(wait.program_name or "").lower():
                continue
            filtered.append(wait)
        return filtered

    def build_waits_from_current_waits(self, waits: List[CurrentWait], limit: int = 15) -> List[WaitStat]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in waits or []:
            key = str(item.wait_type or "")
            if key not in grouped:
                grouped[key] = {
                    "wait_type": key,
                    "wait_time_ms": 0,
                    "waiting_tasks": 0,
                }
            grouped[key]["wait_time_ms"] += self._safe_int(item.wait_time_ms)
            grouped[key]["waiting_tasks"] += 1
        total_wait = max(1, sum(int(v["wait_time_ms"]) for v in grouped.values()))
        ordered = sorted(grouped.values(), key=lambda x: int(x["wait_time_ms"]), reverse=True)[: max(1, int(limit))]
        waits_out: List[WaitStat] = []
        running = 0.0
        for row in ordered:
            wait_time_ms = self._safe_int(row.get("wait_time_ms", 0))
            pct = float(wait_time_ms) * 100.0 / float(total_wait)
            running += pct
            wait_type = str(row.get("wait_type", "") or "")
            waits_out.append(
                WaitStat(
                    wait_type=wait_type,
                    category=get_wait_category(wait_type),
                    waiting_tasks=self._safe_int(row.get("waiting_tasks", 0)),
                    wait_time_ms=wait_time_ms,
                    wait_percent=round(pct, 2),
                    cumulative_percent=round(running, 2),
                )
            )
        return waits_out

    def get_multi_server_wait_comparison(self, days: int = 7, max_servers: int = 20) -> List[MultiServerWaitSnapshot]:
        rows = self._load_recent_history(days=max(1, int(days or 7)))
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            server = str(row.get("server", "") or "unknown")
            database = str(row.get("database", "") or "unknown")
            key = f"{server}|{database}"
            grouped.setdefault(key, []).append(row)

        snapshots: List[MultiServerWaitSnapshot] = []
        for key, items in grouped.items():
            if not items:
                continue
            parsed: List[Tuple[datetime, Dict[str, Any]]] = []
            for item in items:
                try:
                    parsed.append((datetime.fromisoformat(str(item.get("captured_at"))), item))
                except Exception:
                    continue
            if not parsed:
                continue
            parsed.sort(key=lambda x: x[0])
            first_ts, first_item = parsed[0]
            last_ts, last_item = parsed[-1]
            del first_ts  # used for ordering only
            first_total = self._safe_int(first_item.get("total_wait_time_ms", 0))
            last_total = self._safe_int(last_item.get("total_wait_time_ms", 0))
            cat_stats = dict(last_item.get("category_stats", {}) or {})
            top_category = "Other"
            if cat_stats:
                top_category = str(max(cat_stats, key=lambda c: self._safe_int(cat_stats.get(c, 0))) or "Other")
            server, database = key.split("|", 1)
            snapshots.append(
                MultiServerWaitSnapshot(
                    server=server,
                    database=database,
                    captured_at=last_ts,
                    total_wait_time_ms=last_total,
                    signal_wait_percent=self._safe_float(last_item.get("signal_wait_percent", 0.0)),
                    top_category=top_category,
                    delta_wait_ms_window=last_total - first_total,
                )
            )

        snapshots.sort(key=lambda s: (s.total_wait_time_ms, s.delta_wait_ms_window), reverse=True)
        return snapshots[: max(1, int(max_servers or 20))]

    def load_schedule_config(self) -> WaitScheduleConfig:
        payload = dict(self._read_json(self._schedule_config_file_path(), default={}) or {})
        return WaitScheduleConfig(
            enabled=bool(payload.get("enabled", False)),
            interval_minutes=max(1, self._safe_int(payload.get("interval_minutes", 15))),
            output_dir=str(payload.get("output_dir", "") or ""),
            formats=[
                str(item).strip().lower()
                for item in list(payload.get("formats", ["json", "md"]) or ["json", "md"])
                if str(item).strip().lower() in {"json", "md", "csv"}
            ] or ["json", "md"],
        )

    def save_schedule_config(self, config: WaitScheduleConfig) -> bool:
        payload = {
            "enabled": bool(config.enabled),
            "interval_minutes": max(1, self._safe_int(config.interval_minutes)),
            "output_dir": str(config.output_dir or ""),
            "formats": [f for f in list(config.formats or []) if str(f).lower() in {"json", "md", "csv"}] or ["json"],
        }
        return self._write_json(self._schedule_config_file_path(), payload)

    def append_scheduled_snapshot(self, summary: WaitSummary) -> bool:
        server, database = self._active_server_database()
        row = {
            "captured_at": datetime.now().isoformat(),
            "server": server,
            "database": database,
            "total_wait_time_ms": int(summary.total_wait_time_ms or 0),
            "signal_wait_percent": float(summary.signal_wait_percent or 0.0),
            "resource_wait_percent": float(summary.resource_wait_percent or 0.0),
            "category_stats": {
                str(category.value): int(value or 0)
                for category, value in (summary.category_stats or {}).items()
            },
        }
        try:
            with open(self._scheduled_history_file_path(), "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            return True
        except Exception as ex:
            logger.warning(f"Failed to append scheduled wait snapshot: {ex}")
            return False

    def write_automated_reports(
        self,
        export_payload: Dict[str, Any],
        config: Optional[WaitScheduleConfig] = None,
    ) -> List[Path]:
        cfg = config or self.load_schedule_config()
        out_dir = Path(cfg.output_dir) if str(cfg.output_dir or "").strip() else self._scheduled_reports_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        generated_at = str(export_payload.get("generated_at", datetime.now().isoformat()) or datetime.now().isoformat())
        ts = generated_at.replace(":", "").replace("-", "").replace("T", "_").replace(" ", "_")[:15]
        server, database = self._active_server_database()
        prefix = f"wait_stats_{server.replace('\\\\', '_').replace('/', '_')}_{database}_{ts}"
        written: List[Path] = []

        formats = [str(x).lower() for x in list(cfg.formats or [])]
        for fmt in formats:
            path = out_dir / f"{prefix}.{fmt}"
            try:
                if fmt == "json":
                    with open(path, "w", encoding="utf-8") as handle:
                        json.dump(export_payload, handle, indent=2, ensure_ascii=False)
                elif fmt == "csv":
                    summary = dict(export_payload.get("summary", {}) or {})
                    waits = list(export_payload.get("top_waits", []) or [])
                    rows: List[Dict[str, Any]] = [
                        {
                            "section": "summary",
                            "generated_at": export_payload.get("generated_at", ""),
                            "server": server,
                            "database": database,
                            "total_wait_time_ms": summary.get("total_wait_time_ms", 0),
                            "signal_wait_percent": summary.get("signal_wait_percent", 0.0),
                            "resource_wait_percent": summary.get("resource_wait_percent", 0.0),
                        }
                    ]
                    for wait in waits:
                        rows.append(
                            {
                                "section": "top_wait",
                                "wait_type": wait.get("wait_type", ""),
                                "category": wait.get("category", ""),
                                "wait_time_ms": wait.get("wait_time_ms", 0),
                                "wait_percent": wait.get("wait_percent", 0.0),
                            }
                        )
                    fieldnames = sorted({key for row in rows for key in row.keys()})
                    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                        writer = csv.DictWriter(handle, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(rows)
                elif fmt == "md":
                    summary = dict(export_payload.get("summary", {}) or {})
                    alerts = list(export_payload.get("alerts", []) or [])
                    top_waits = list(export_payload.get("top_waits", []) or [])
                    lines = [
                        "# Wait Stats Automated Report",
                        "",
                        f"- Generated: {export_payload.get('generated_at', '')}",
                        f"- Server: {server}",
                        f"- Database: {database}",
                        "",
                        "## Summary",
                        "",
                        f"- Total Wait (ms): {int(summary.get('total_wait_time_ms', 0) or 0):,}",
                        f"- Signal Wait %: {float(summary.get('signal_wait_percent', 0.0) or 0.0):.2f}",
                        f"- Resource Wait %: {float(summary.get('resource_wait_percent', 0.0) or 0.0):.2f}",
                        "",
                        "## Alerts",
                        "",
                    ]
                    if alerts:
                        for alert in alerts:
                            lines.append(f"- [{alert.get('severity', '').upper()}] {alert.get('title', '')}: {alert.get('message', '')}")
                    else:
                        lines.append("- No active alerts.")
                    lines.extend(
                        [
                            "",
                            "## Top Waits",
                            "",
                            "| Wait Type | Category | Wait ms | Wait % |",
                            "|---|---|---:|---:|",
                        ]
                    )
                    for wait in top_waits[:20]:
                        lines.append(
                            f"| {wait.get('wait_type', '')} | {wait.get('category', '')} | "
                            f"{int(wait.get('wait_time_ms', 0) or 0):,} | {float(wait.get('wait_percent', 0.0) or 0.0):.2f} |"
                        )
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write("\n".join(lines))
                else:
                    continue
                written.append(path)
            except Exception as ex:
                logger.warning(f"Failed to write automated wait report [{fmt}]: {ex}")
        return written

    def load_monitoring_targets(self) -> List[WaitMonitoringTarget]:
        payload = list(self._read_json(self._monitoring_targets_file_path(), default=[]) or [])
        targets: List[WaitMonitoringTarget] = []
        for row in payload:
            try:
                url = str(row.get("url", "") or "").strip()
                if not url:
                    continue
                targets.append(
                    WaitMonitoringTarget(
                        name=str(row.get("name", url) or url),
                        url=url,
                        payload_format=str(row.get("payload_format", "json") or "json").strip().lower(),
                        enabled=bool(row.get("enabled", True)),
                        headers={
                            str(k): str(v)
                            for k, v in dict(row.get("headers", {}) or {}).items()
                            if str(k).strip()
                        },
                    )
                )
            except Exception:
                continue
        return targets

    def save_monitoring_targets(self, targets: List[WaitMonitoringTarget]) -> bool:
        payload = [asdict(t) for t in list(targets or [])]
        return self._write_json(self._monitoring_targets_file_path(), payload)

    def add_monitoring_target(
        self,
        name: str,
        url: str,
        payload_format: str = "json",
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        clean_url = str(url or "").strip()
        if not clean_url:
            return False
        fmt = str(payload_format or "json").strip().lower()
        if fmt not in {"json", "prometheus"}:
            fmt = "json"
        targets = self.load_monitoring_targets()
        for target in targets:
            if target.url == clean_url:
                return True
        targets.append(
            WaitMonitoringTarget(
                name=str(name or clean_url),
                url=clean_url,
                payload_format=fmt,
                enabled=True,
                headers={str(k): str(v) for k, v in dict(headers or {}).items()},
            )
        )
        return self.save_monitoring_targets(targets)

    def remove_monitoring_target(self, name_or_url: str) -> bool:
        needle = str(name_or_url or "").strip().lower()
        if not needle:
            return False
        targets = self.load_monitoring_targets()
        kept = [t for t in targets if (t.name.lower() != needle and t.url.lower() != needle)]
        if len(kept) == len(targets):
            return False
        return self.save_monitoring_targets(kept)

    def _chain_total_blocked_sessions(self, chain: Any) -> int:
        if chain is None:
            return 0
        explicit = getattr(chain, "total_blocked_sessions", None)
        if explicit is not None:
            return self._safe_int(explicit)
        sessions = list(getattr(chain, "blocking_sessions", []) or [])
        return len(sessions)

    def _chain_total_blocking_sessions(self, chain: Any) -> int:
        if chain is None:
            return 0
        explicit = getattr(chain, "total_blocking_sessions", None)
        if explicit is not None:
            return self._safe_int(explicit)
        chain_count = getattr(chain, "chain_count", None)
        if chain_count is not None:
            return self._safe_int(chain_count)
        sessions = list(getattr(chain, "blocking_sessions", []) or [])
        blocker_ids = {self._safe_int(getattr(item, "blocking_session_id", 0)) for item in sessions}
        blocker_ids.discard(0)
        return len(blocker_ids)

    def _chain_max_depth(self, chain: Any) -> int:
        if chain is None:
            return 0
        explicit = getattr(chain, "max_chain_depth", None)
        if explicit is not None:
            return self._safe_int(explicit)
        return 0

    def _build_wait_chain_export_block(self, wait_chain: Any) -> Dict[str, Any]:
        if wait_chain is None:
            return {
                "summary": "No active blocking chains.",
                "chain_count": 0,
                "total_blocked_sessions": 0,
                "total_blocking_sessions": 0,
                "max_chain_depth": 0,
                "root_blockers": [],
                "nodes": [],
                "edges": [],
            }

        if hasattr(wait_chain, "nodes") and hasattr(wait_chain, "edges"):
            return {
                "summary": str(getattr(wait_chain, "summary", "") or "No active blocking chains."),
                "chain_count": self._safe_int(getattr(wait_chain, "chain_count", 0)),
                "total_blocked_sessions": self._safe_int(getattr(wait_chain, "total_blocked_sessions", 0)),
                "total_blocking_sessions": self._safe_int(getattr(wait_chain, "total_blocking_sessions", 0)),
                "max_chain_depth": self._safe_int(getattr(wait_chain, "max_chain_depth", 0)),
                "root_blockers": list(getattr(wait_chain, "root_blockers", []) or []),
                "nodes": [asdict(node) for node in list(getattr(wait_chain, "nodes", []) or [])],
                "edges": [asdict(edge) for edge in list(getattr(wait_chain, "edges", []) or [])],
            }

        sessions = list(getattr(wait_chain, "blocking_sessions", []) or [])
        head_blockers = list(getattr(wait_chain, "head_blockers", []) or [])
        root_blockers = [self._safe_int(getattr(item, "session_id", 0)) for item in head_blockers if self._safe_int(getattr(item, "session_id", 0)) > 0]
        nodes: List[Dict[str, Any]] = []
        for item in sessions:
            nodes.append(
                {
                    "session_id": self._safe_int(getattr(item, "session_id", 0)),
                    "blocking_session_id": self._safe_int(getattr(item, "blocking_session_id", 0)),
                    "wait_type": str(getattr(item, "wait_type", "") or ""),
                    "wait_time_ms": self._safe_int(float(getattr(item, "wait_seconds", 0.0) or 0.0) * 1000.0),
                    "database_name": str(getattr(item, "database_name", "") or ""),
                    "login_name": str(getattr(item, "login_name", "") or ""),
                    "host_name": str(getattr(item, "host_name", "") or ""),
                    "program_name": str(getattr(item, "program_name", "") or ""),
                    "current_statement": str(getattr(item, "current_statement", "") or ""),
                }
            )
        edges = [
            {
                "blocker_session_id": self._safe_int(getattr(item, "blocking_session_id", 0)),
                "blocked_session_id": self._safe_int(getattr(item, "session_id", 0)),
                "wait_type": str(getattr(item, "wait_type", "") or ""),
                "wait_time_ms": self._safe_int(float(getattr(item, "wait_seconds", 0.0) or 0.0) * 1000.0),
            }
            for item in sessions
            if self._safe_int(getattr(item, "blocking_session_id", 0)) > 0 and self._safe_int(getattr(item, "session_id", 0)) > 0
        ]

        return {
            "summary": str(getattr(wait_chain, "summary", "") or "No active blocking chains."),
            "chain_count": self._safe_int(getattr(wait_chain, "chain_count", 0)),
            "total_blocked_sessions": self._chain_total_blocked_sessions(wait_chain),
            "total_blocking_sessions": self._chain_total_blocking_sessions(wait_chain),
            "max_chain_depth": self._chain_max_depth(wait_chain),
            "root_blockers": root_blockers,
            "nodes": nodes,
            "edges": edges,
        }

    def _build_prometheus_payload(
        self,
        summary: WaitSummary,
        chain: Any,
        alerts: List[WaitAlert],
    ) -> str:
        server, database = self._active_server_database()
        blocked_sessions = self._chain_total_blocked_sessions(chain)
        max_depth = self._chain_max_depth(chain)
        labels = f'server="{server}",database="{database}"'
        lines = [
            f"sqlperf_wait_total_wait_time_ms{{{labels}}} {int(summary.total_wait_time_ms or 0)}",
            f"sqlperf_wait_signal_percent{{{labels}}} {float(summary.signal_wait_percent or 0.0):.4f}",
            f"sqlperf_wait_resource_percent{{{labels}}} {float(summary.resource_wait_percent or 0.0):.4f}",
            f"sqlperf_wait_blocked_sessions{{{labels}}} {int(blocked_sessions or 0)}",
            f"sqlperf_wait_chain_depth{{{labels}}} {int(max_depth or 0)}",
            f"sqlperf_wait_alert_count{{{labels}}} {len(alerts or [])}",
        ]
        for category, wait_ms in (summary.category_stats or {}).items():
            cat = str(category.value).replace('"', "").replace("\\", "_").replace(" ", "_")
            lines.append(f'sqlperf_wait_category_wait_time_ms{{{labels},category="{cat}"}} {int(wait_ms or 0)}')
        return "\n".join(lines) + "\n"

    def push_metrics_to_monitoring_targets(
        self,
        summary: WaitSummary,
        chain: Any,
        alerts: List[WaitAlert],
        targets: Optional[List[WaitMonitoringTarget]] = None,
        timeout_seconds: int = 5,
    ) -> Dict[str, Any]:
        selected = [t for t in list(targets or self.load_monitoring_targets()) if t.enabled]
        if not selected:
            return {"success": 0, "failed": 0, "results": []}

        server, database = self._active_server_database()
        json_payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "server": server,
            "database": database,
            "summary": {
                "total_wait_time_ms": int(summary.total_wait_time_ms or 0),
                "signal_wait_percent": float(summary.signal_wait_percent or 0.0),
                "resource_wait_percent": float(summary.resource_wait_percent or 0.0),
                "category_stats": {
                    str(category.value): int(value or 0)
                    for category, value in (summary.category_stats or {}).items()
                },
            },
            "wait_chain": {
                "blocked_sessions": int(self._chain_total_blocked_sessions(chain) or 0),
                "blocking_sessions": int(self._chain_total_blocking_sessions(chain) or 0),
                "max_depth": int(self._chain_max_depth(chain) or 0),
            },
            "alerts": [asdict(alert) | {"triggered_at": alert.triggered_at.isoformat(timespec="seconds")} for alert in (alerts or [])],
        }
        prom_payload = self._build_prometheus_payload(summary, chain, alerts)

        results: List[Dict[str, Any]] = []
        success = 0
        failed = 0
        try:
            import requests
        except Exception as ex:
            logger.warning(f"Monitoring push skipped (requests unavailable): {ex}")
            return {"success": 0, "failed": len(selected), "results": [{"target": t.name, "status": "failed", "error": "requests unavailable"} for t in selected]}

        for target in selected:
            fmt = str(target.payload_format or "json").strip().lower()
            headers = dict(target.headers or {})
            try:
                if fmt == "prometheus":
                    headers.setdefault("Content-Type", "text/plain; version=0.0.4")
                    resp = requests.post(target.url, data=prom_payload.encode("utf-8"), headers=headers, timeout=timeout_seconds)
                else:
                    headers.setdefault("Content-Type", "application/json")
                    resp = requests.post(target.url, json=json_payload, headers=headers, timeout=timeout_seconds)
                if int(resp.status_code) >= 400:
                    failed += 1
                    results.append(
                        {
                            "target": target.name,
                            "status": "failed",
                            "code": int(resp.status_code),
                            "error": str(resp.text or "")[:400],
                        }
                    )
                else:
                    success += 1
                    results.append({"target": target.name, "status": "success", "code": int(resp.status_code)})
            except Exception as ex:
                failed += 1
                results.append({"target": target.name, "status": "failed", "error": str(ex)})

        return {"success": success, "failed": failed, "results": results}

    def get_wait_plan_correlation(
        self,
        context: Optional[AnalysisContext] = None,
        days: int = 7,
    ) -> WaitPlanCorrelation:
        ctx = context or self._last_context
        query_id = int(getattr(ctx, "query_id", 0) or 0) if ctx else 0
        if query_id <= 0:
            return WaitPlanCorrelation()

        wait_rows = self.get_query_wait_correlation(ctx, days=days)
        waits_sorted = sorted(wait_rows, key=lambda x: float(x.get("wait_percent", 0.0) or 0.0), reverse=True)
        dominant_categories = [
            str(resolve_wait_category_text(str(item.get("category", "") or "")).value)
            for item in waits_sorted[:3]
        ]

        category_pct: Dict[str, float] = {}
        for item in waits_sorted:
            cat = str(resolve_wait_category_text(str(item.get("category", "") or "")).value)
            category_pct[cat] = category_pct.get(cat, 0.0) + float(item.get("wait_percent", 0.0) or 0.0)

        plan_xml = ""
        plan_summary = ""
        findings: List[str] = []
        recs: List[str] = []
        confidence = 0.25
        plan_available = False

        try:
            from app.services.query_stats_service import QueryStatsService
            from app.ai.plan_analyzer import ExecutionPlanAnalyzer

            qs_service = QueryStatsService()
            plan_xml = str(qs_service.get_query_plan_xml(query_id=query_id, include_sensitive_data=False) or "")
            if plan_xml:
                plan_available = True
                insights = ExecutionPlanAnalyzer().analyze(plan_xml)
                plan_summary = insights.get_summary()
                confidence += 0.3

                lock_pct = float(category_pct.get(WaitCategory.LOCK.value, 0.0))
                io_pct = float(category_pct.get(WaitCategory.IO.value, 0.0))
                cpu_pct = float(category_pct.get(WaitCategory.CPU.value, 0.0))
                memory_pct = float(category_pct.get(WaitCategory.MEMORY.value, 0.0))

                if lock_pct >= 15.0 and insights.has_table_scan:
                    findings.append("Lock waits align with table/index scans in execution plan.")
                    recs.append("Reduce scan footprint with selective indexes and shorter transactions.")
                if io_pct >= 20.0 and (insights.has_key_lookup or insights.has_hash_spill or insights.has_sort_warning):
                    findings.append("I/O waits correlate with key lookup/sort or spill behavior in plan.")
                    recs.append("Validate covering indexes and memory grant quality to reduce I/O pressure.")
                if cpu_pct >= 20.0 and insights.is_parallel:
                    findings.append(f"CPU waits correlate with parallel plan shape (DOP={insights.degree_of_parallelism}).")
                    recs.append("Review MAXDOP and cost threshold with query-level tuning.")
                if memory_pct >= 10.0 and (insights.has_sort_warning or insights.has_hash_spill):
                    findings.append("Memory waits correlate with sort/hash pressure observed in plan warnings.")
                    recs.append("Inspect cardinality estimates and right-size memory grants.")

                if not findings and insights.warnings:
                    findings.extend([str(w.message) for w in insights.warnings[:2]])
                if not recs and insights.missing_indexes:
                    recs.append("Validate missing index suggestions in a controlled workload test.")
        except Exception as ex:
            logger.info(f"Plan correlation unavailable for query_id={query_id}: {ex}")

        if waits_sorted:
            confidence += 0.2
        if findings:
            confidence += 0.2
        confidence = min(0.95, max(0.0, confidence))

        return WaitPlanCorrelation(
            query_id=query_id,
            plan_available=plan_available,
            dominant_wait_categories=dominant_categories,
            plan_summary=plan_summary,
            findings=findings[:6],
            recommendations=recs[:6],
            confidence=confidence,
        )

    def get_wait_summary_with_metrics(
        self,
        max_attempts: int = 3,
        base_backoff_seconds: float = 0.2,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        retry_callback: Optional[Callable[[str, int, int, float, Exception], None]] = None,
    ) -> Tuple[WaitSummary, WaitStatsMetrics]:
        """
        Collect wait summary with retry and telemetry.
        Returns safe defaults on partial failures; never raises.
        """
        started = perf_counter()
        summary = WaitSummary()
        metrics = WaitStatsMetrics()

        if not self.is_connected:
            metrics.connection_lost = True
            metrics.partial_data = True
            metrics.error_count = 1
            metrics.errors.append("No active connection for wait stats.")
            logger.warning("No active connection for wait stats")
            metrics.load_duration_ms = int((perf_counter() - started) * 1000)
            return summary, metrics

        conn = self.connection
        if conn is None:
            metrics.connection_lost = True
            metrics.partial_data = True
            metrics.error_count = 1
            metrics.errors.append("Connection handle is unavailable.")
            metrics.load_duration_ms = int((perf_counter() - started) * 1000)
            return summary, metrics

        def emit_progress(percent: int, message: str) -> None:
            if not callable(progress_callback):
                return
            try:
                progress_callback(int(percent), str(message or ""))
            except Exception:
                pass

        def run_query(operation_name: str, sql: str, percent: int, message: str) -> List[Dict[str, Any]]:
            emit_progress(percent, message)
            metrics.query_count += 1
            try:
                rows, retries_used, duration_ms = self._execute_query_with_retry(
                    conn=conn,
                    sql=sql,
                    operation_name=operation_name,
                    max_attempts=max_attempts,
                    base_backoff_seconds=base_backoff_seconds,
                    retry_callback=retry_callback,
                )
                metrics.total_retries += int(retries_used)
                metrics.retry_counts[operation_name] = int(retries_used)
                metrics.query_durations_ms[operation_name] = int(duration_ms)
                metrics.rows_by_operation[operation_name] = len(rows or [])
                return rows
            except Exception as ex:
                retries_used = int(getattr(ex, "wait_retry_attempts", 0) or 0)
                metrics.total_retries += retries_used
                metrics.retry_counts[operation_name] = retries_used
                metrics.partial_data = True
                metrics.error_count += 1
                metrics.errors.append(f"{operation_name}: {ex}")
                if self._is_connection_error(ex):
                    metrics.connection_lost = True
                logger.warning(f"Wait stats step failed [{operation_name}]: {ex}")
                return []

        emit_progress(5, "Starting wait statistics refresh...")

        summary_rows = run_query("wait_summary", WaitStatsQueries.WAIT_SUMMARY, 15, "Collecting summary metrics...")
        if summary_rows:
            row = summary_rows[0]
            summary.total_wait_types = self._safe_int(row.get("total_wait_types", 0))
            summary.total_waiting_tasks = self._safe_int(row.get("total_waiting_tasks", 0))
            summary.total_wait_time_ms = self._safe_int(row.get("total_wait_time_ms", 0))
            summary.total_signal_wait_ms = self._safe_int(row.get("total_signal_wait_ms", 0))
            summary.total_resource_wait_ms = self._safe_int(row.get("total_resource_wait_ms", 0))
            summary.max_single_wait_ms = self._safe_int(row.get("max_single_wait_ms", 0))

        ratio_rows = run_query("signal_vs_resource", WaitStatsQueries.SIGNAL_VS_RESOURCE, 30, "Calculating signal/resource ratio...")
        if ratio_rows:
            row = ratio_rows[0]
            summary.signal_wait_percent = self._safe_float(row.get("signal_wait_percent", 0))
            summary.resource_wait_percent = self._safe_float(row.get("resource_wait_percent", 0))

        top_rows = run_query("top_waits", WaitStatsQueries.TOP_WAITS, 50, "Loading top wait types...")
        summary.top_waits = self._map_top_wait_rows(top_rows)

        category_rows = run_query("waits_by_category", WaitStatsQueries.WAITS_BY_CATEGORY, 70, "Aggregating category totals...")
        summary.category_stats = self._map_category_rows(category_rows)
        summary.all_waits = self._map_all_wait_rows(category_rows)

        current_rows = run_query("current_waits", WaitStatsQueries.CURRENT_WAITS, 88, "Loading active waiters...")
        summary.current_waits = self._map_current_wait_rows(current_rows)
        summary.collected_at = datetime.now()

        self._append_history_snapshot(summary)

        metrics.top_waits_count = len(summary.top_waits)
        metrics.current_waits_count = len(summary.current_waits)
        metrics.collected_at = summary.collected_at
        metrics.load_duration_ms = int((perf_counter() - started) * 1000)
        emit_progress(100, "Wait statistics refresh completed.")
        return summary, metrics

    def get_wait_summary(self) -> WaitSummary:
        """Get comprehensive wait statistics summary."""
        summary, _metrics = self.get_wait_summary_with_metrics()
        return summary

    def _get_top_waits(self, conn) -> List[WaitStat]:
        """Get top wait types."""
        try:
            result, _retries, _duration = self._execute_query_with_retry(
                conn=conn,
                sql=WaitStatsQueries.TOP_WAITS,
                operation_name="top_waits",
            )
            return self._map_top_wait_rows(result)
        except Exception as e:
            logger.warning(f"Error getting top waits: {e}")
            return []

    def _calculate_category_stats(self, conn) -> Dict[WaitCategory, int]:
        """Calculate wait time by category."""
        try:
            result, _retries, _duration = self._execute_query_with_retry(
                conn=conn,
                sql=WaitStatsQueries.WAITS_BY_CATEGORY,
                operation_name="waits_by_category",
            )
            return self._map_category_rows(result)
        except Exception as e:
            logger.warning(f"Error calculating category stats: {e}")
            return {cat: 0 for cat in WaitCategory}

    def _get_current_waits(self, conn) -> List[CurrentWait]:
        """Get currently waiting tasks."""
        try:
            result, _retries, _duration = self._execute_query_with_retry(
                conn=conn,
                sql=WaitStatsQueries.CURRENT_WAITS,
                operation_name="current_waits",
            )
            return self._map_current_wait_rows(result)
        except Exception as e:
            logger.warning(f"Error getting current waits: {e}")
            return []

    def clear_wait_stats(self) -> bool:
        """Clear wait statistics (requires admin privileges)."""
        if not self.is_connected:
            return False

        try:
            self.connection.execute_query(WaitStatsQueries.CLEAR_WAIT_STATS)
            logger.info("Wait statistics cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Error clearing wait stats: {e}")
            return False

    def get_latch_stats(self) -> List[Dict[str, Any]]:
        """Get latch statistics."""
        if not self.is_connected:
            return []

        try:
            result = self.connection.execute_query(WaitStatsQueries.LATCH_STATS)
            return result or []
        except Exception as e:
            logger.warning(f"Error getting latch stats: {e}")
        return []

    def build_export_payload(
        self,
        summary: WaitSummary,
        waits_to_render: List[WaitStat],
        signatures: List[WaitSignature],
        baseline: WaitBaselineComparison,
        trend_points: List[WaitTrendPoint],
        trend_days: int,
        wait_chain: Optional[Any] = None,
        alerts: Optional[List[WaitAlert]] = None,
        thresholds: Optional[WaitAlertThresholds] = None,
        comparative: Optional[WaitComparativeAnalysis] = None,
        custom_category_breakdown: Optional[Dict[str, int]] = None,
        custom_category_rules: Optional[List[CustomWaitCategoryRule]] = None,
        multi_server: Optional[List[MultiServerWaitSnapshot]] = None,
        plan_correlation: Optional[WaitPlanCorrelation] = None,
        filters: Optional[WaitStatsFilter] = None,
    ) -> Dict[str, Any]:
        """
        Build normalized export payload for CSV/JSON/Markdown serializers.
        """
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "trend_window_days": int(trend_days or 7),
            "summary": {
                "total_wait_types": int(summary.total_wait_types or 0),
                "total_waiting_tasks": int(summary.total_waiting_tasks or 0),
                "total_wait_time_ms": int(summary.total_wait_time_ms or 0),
                "total_signal_wait_ms": int(summary.total_signal_wait_ms or 0),
                "total_resource_wait_ms": int(summary.total_resource_wait_ms or 0),
                "max_single_wait_ms": int(summary.max_single_wait_ms or 0),
                "signal_wait_percent": float(summary.signal_wait_percent or 0.0),
                "resource_wait_percent": float(summary.resource_wait_percent or 0.0),
                "collected_at": summary.collected_at.isoformat(timespec="seconds"),
                "category_stats": {
                    str(category.value): int(value or 0)
                    for category, value in (summary.category_stats or {}).items()
                },
            },
            "top_waits": [
                {
                    "wait_type": str(wait.wait_type or ""),
                    "category": str(wait.category.value),
                    "waiting_tasks": int(wait.waiting_tasks or 0),
                    "wait_time_ms": int(wait.wait_time_ms or 0),
                    "wait_percent": float(wait.wait_percent or 0.0),
                    "cumulative_percent": float(wait.cumulative_percent or 0.0),
                    "signal_wait_ms": int(wait.signal_wait_ms or 0),
                    "resource_wait_ms": int(wait.resource_wait_ms or 0),
                }
                for wait in (waits_to_render or [])
            ],
            "signatures": [asdict(sig) | {"dominant_category": sig.dominant_category.value} for sig in (signatures or [])],
            "baseline_comparison": {
                "baseline_available": bool(baseline.baseline_available),
                "baseline_captured_at": baseline.baseline_captured_at.isoformat(timespec="seconds")
                if baseline.baseline_captured_at
                else None,
                "baseline_age_hours": float(baseline.baseline_age_hours or 0.0),
                "delta_total_wait_ms": int(baseline.delta_total_wait_ms or 0),
                "delta_signal_wait_percent": float(baseline.delta_signal_wait_percent or 0.0),
                "delta_resource_wait_percent": float(baseline.delta_resource_wait_percent or 0.0),
                "delta_category_wait_ms": dict(baseline.delta_category_wait_ms or {}),
                "status": str(baseline.status or ""),
                "summary": str(baseline.summary or ""),
            },
            "trend": [
                {
                    "trend_date": str(point.trend_date),
                    "total_wait_ms": int(point.total_wait_ms or 0),
                    "dominant_category": str(point.dominant_category or ""),
                    "dominant_wait_ms": int(point.dominant_wait_ms or 0),
                    "category_wait_ms": dict(point.category_wait_ms or {}),
                    "category_percent": dict(point.category_percent or {}),
                }
                for point in (trend_points or [])
            ],
            "wait_chain": self._build_wait_chain_export_block(wait_chain),
            "alerts": [
                {
                    "alert_id": str(alert.alert_id or ""),
                    "severity": str(alert.severity or ""),
                    "title": str(alert.title or ""),
                    "message": str(alert.message or ""),
                    "metric_value": float(alert.metric_value or 0.0),
                    "threshold_value": float(alert.threshold_value or 0.0),
                    "triggered_at": alert.triggered_at.isoformat(timespec="seconds"),
                }
                for alert in list(alerts or [])
            ],
            "thresholds": asdict(thresholds) if thresholds else asdict(self.load_alert_thresholds()),
            "before_after_comparison": {
                "before_available": bool((comparative.before_available if comparative else False)),
                "after_available": bool((comparative.after_available if comparative else False)),
                "before_captured_at": comparative.before_captured_at.isoformat(timespec="seconds")
                if comparative and comparative.before_captured_at
                else None,
                "after_captured_at": comparative.after_captured_at.isoformat(timespec="seconds")
                if comparative and comparative.after_captured_at
                else None,
                "delta_total_wait_ms": int((comparative.delta_total_wait_ms if comparative else 0) or 0),
                "delta_signal_wait_percent": float((comparative.delta_signal_wait_percent if comparative else 0.0) or 0.0),
                "delta_resource_wait_percent": float((comparative.delta_resource_wait_percent if comparative else 0.0) or 0.0),
                "delta_category_wait_ms": dict((comparative.delta_category_wait_ms if comparative else {}) or {}),
                "status": str((comparative.status if comparative else "insufficient-data") or "insufficient-data"),
                "summary": str(
                    (comparative.summary if comparative else "Capture both BEFORE and AFTER snapshots to compare.")
                    or "Capture both BEFORE and AFTER snapshots to compare."
                ),
            },
            "custom_categories": {
                "rules": [asdict(rule) for rule in list(custom_category_rules or [])],
                "wait_time_ms_by_category": dict(custom_category_breakdown or {}),
            },
            "filters": asdict(filters) if filters else {},
            "multi_server": [
                {
                    "server": item.server,
                    "database": item.database,
                    "captured_at": item.captured_at.isoformat(timespec="seconds"),
                    "total_wait_time_ms": int(item.total_wait_time_ms or 0),
                    "signal_wait_percent": float(item.signal_wait_percent or 0.0),
                    "top_category": str(item.top_category or ""),
                    "delta_wait_ms_window": int(item.delta_wait_ms_window or 0),
                }
                for item in list(multi_server or [])
            ],
            "wait_plan_correlation": {
                "query_id": int((plan_correlation.query_id if plan_correlation else 0) or 0),
                "plan_available": bool((plan_correlation.plan_available if plan_correlation else False)),
                "dominant_wait_categories": list((plan_correlation.dominant_wait_categories if plan_correlation else []) or []),
                "plan_summary": str((plan_correlation.plan_summary if plan_correlation else "") or ""),
                "findings": list((plan_correlation.findings if plan_correlation else []) or []),
                "recommendations": list((plan_correlation.recommendations if plan_correlation else []) or []),
                "confidence": float((plan_correlation.confidence if plan_correlation else 0.0) or 0.0),
            },
        }

    # ==========================================================================
    # CROSS-MODULE CONTEXT
    # ==========================================================================

    def receive_context(self, context: AnalysisContext) -> None:
        """Receive context from Query Statistics or message bus."""
        self._last_context = context
        logger.info(
            "WaitStatsService received context "
            f"[query_id={context.query_id}, object={context.object_full_name}]"
        )

    def get_last_context(self) -> Optional[AnalysisContext]:
        return self._last_context

    def get_query_wait_correlation(
        self,
        context: Optional[AnalysisContext] = None,
        days: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Query-level wait distribution using Query Store wait stats when available.
        """
        ctx = context or self._last_context
        if not ctx:
            return []

        query_id = int(getattr(ctx, "query_id", 0) or 0)
        if query_id <= 0:
            return []

        try:
            from app.services.query_stats_service import QueryStatsService

            service = QueryStatsService()
            waits = service.get_query_wait_stats(query_id, days=days)
            result: List[Dict[str, Any]] = []
            for item in waits or []:
                result.append(
                    {
                        "category": str(getattr(item, "category", "") or ""),
                        "display_name": str(getattr(item, "display_name", "") or ""),
                        "wait_percent": float(getattr(item, "wait_percent", 0.0) or 0.0),
                        "total_wait_ms": float(getattr(item, "total_wait_ms", 0.0) or 0.0),
                    }
                )
            return result
        except Exception as e:
            logger.warning(f"Failed to fetch query wait correlation: {e}")
            return []


def get_wait_stats_service() -> WaitStatsService:
    """Get singleton wait stats service instance."""
    return WaitStatsService()
