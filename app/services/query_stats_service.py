"""
Query Stats Service

Bu servis Query Store ve DMV'lerden performans verilerini çeker,
işler ve UI katmanına sunar.

Temel Sorumluluklar:
- Query Store aktiflik kontrolü
- Version-aware sorgu seçimi
- Veri çekme ve model dönüşümü
- Metrik hesaplamaları
"""

from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING, Callable
from datetime import datetime
from copy import deepcopy
import json
import logging
import time
import traceback
import uuid
import re
import xml.etree.ElementTree as ET
from collections import deque, OrderedDict
from threading import Lock, Thread, Event

from app.core.logger import get_logger
# Circular import prevention: from app.database.connection import get_connection_manager, DatabaseConnection
if TYPE_CHECKING:
    from app.database.connection import DatabaseConnection
from app.database.version_detector import SQLFeature, VersionDetector
from app.database.queries.query_store_queries import (
    QueryStoreQueries, 
    TimeRange, 
    SortOption,
)
from app.models.query_stats_models import (
    QueryStats,
    QueryMetrics,
    WaitProfile,
    PlanInfo,
    TrendData,
    QueryStoreStatus,
    QueryStatsFilter,
    QueryPriority,
)
from app.core.exceptions import (
    ConnectionError as DBConnectionError,
    ConnectionTimeoutError,
    QueryExecutionError,
    QueryTimeoutError,
    PermissionDeniedError,
    TaskCancelledError,
)
from app.services.query_stats_contract import IQueryStatsService

logger = get_logger('services.query_stats')


class QueryStatsService(IQueryStatsService):
    """
    Query Stats iş mantığı servisi
    
    Kullanım:
        service = QueryStatsService()
        stats = service.get_top_queries(filter)
        detail = service.get_query_detail(query_id)
    """
    
    _OBS_LOCK = Lock()
    _LOAD_DURATIONS_MS = deque(maxlen=500)
    _LOAD_SUCCESS_COUNT = 0
    _LOAD_ERROR_COUNT = 0
    _LOAD_CANCELLED_COUNT = 0
    _SOURCE_USAGE: Dict[str, int] = {}
    _SORT_BY_USAGE: Dict[str, int] = {}
    _CACHE_LOCK = Lock()
    _QUERY_STORE_TTL_SECONDS = 300
    _PERMISSION_TTL_SECONDS = 300
    _TOP_QUERIES_TTL_SECONDS = 30
    _QUERY_STORE_CACHE: Dict[str, Tuple[float, QueryStoreStatus]] = {}
    _PERMISSION_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _SQL_VERSION_CACHE: Dict[str, int] = {}
    _TOP_QUERIES_CACHE: Dict[str, Tuple[float, List[QueryStats], List[str], int]] = {}
    _PLAN_XML_CACHE_MAX = 50
    _MAX_UI_QUERY_TEXT_CHARS = 10000
    _PLAN_XML_CACHE: "OrderedDict[Tuple[str, str], str]" = OrderedDict()
    _QUERY_TO_PLAN_KEY: Dict[int, Tuple[str, str]] = {}
    _BG_REFRESH_THREAD: Optional[Thread] = None
    _BG_REFRESH_STOP = Event()
    _BG_REFRESH_INTERVAL_SECONDS = 300

    def __init__(
        self,
        connection: Optional['DatabaseConnection'] = None,
        connection_manager_provider: Optional[Callable[[], Any]] = None,
    ):
        """
        Args:
            connection: Veritabanı bağlantısı (None ise aktif bağlantı kullanılır)
            connection_manager_provider: Aktif connection manager provider (DI için)
        """
        self._connection = connection
        self._connection_manager_provider = connection_manager_provider
        self._query_store_status: Optional[QueryStoreStatus] = None
        self._sql_version: Optional[int] = None
        self._runtime_warnings: List[str] = []
        self._last_error: Optional[Dict[str, str]] = None
        self._last_total_count: int = 0

    # ==========================================================================
    # ERROR/RETRY HELPERS
    # ==========================================================================

    @staticmethod
    def classify_error_type(exc: Exception) -> str:
        """Classify exception into a stable UI-friendly error type."""
        if isinstance(exc, TaskCancelledError):
            return "cancelled"
        if isinstance(exc, (ConnectionTimeoutError, QueryTimeoutError, TimeoutError)):
            return "timeout"
        if isinstance(exc, DBConnectionError):
            return "connection"
        if isinstance(exc, PermissionDeniedError):
            return "permission"
        if isinstance(exc, QueryExecutionError):
            text = str(exc).lower()
            if "query_store" in text:
                return "query_store"
            if "timeout" in text:
                return "timeout"
            if "permission" in text or "denied" in text:
                return "permission"
            return "sql"
        text = str(exc).lower()
        if "cancelled" in text or "canceled" in text or "operation cancelled by user" in text:
            return "cancelled"
        if "query_store" in text:
            return "query_store"
        if "timeout" in text:
            return "timeout"
        if "login failed" in text or "cannot open server" in text or "communication link failure" in text:
            return "connection"
        if "permission" in text or "denied" in text:
            return "permission"
        return "unknown"

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        """Return True if retry may succeed for this error."""
        if isinstance(exc, (ConnectionTimeoutError, QueryTimeoutError, TimeoutError)):
            return True
        if isinstance(exc, DBConnectionError):
            return True
        text = str(exc).lower()
        transient_markers = (
            "timeout",
            "temporarily unavailable",
            "transport-level error",
            "communication link failure",
            "connection was forcibly closed",
            "deadlock victim",
            "could not open a connection",
        )
        return any(marker in text for marker in transient_markers)

    @staticmethod
    def _user_friendly_error_message(error_type: str, original: Exception) -> str:
        if error_type == "cancelled":
            return "Loading cancelled by user."
        if error_type == "connection":
            return "Database connection lost. Please verify connectivity and try again."
        if error_type == "timeout":
            return "Query timed out. Please retry or narrow the time range/filter."
        if error_type == "permission":
            return "Insufficient permissions for Query Statistics queries."
        if error_type == "query_store":
            return "Query Store query failed. DMV fallback was attempted."
        if error_type == "sql":
            return "SQL execution failed while loading query statistics."
        return f"Unexpected error while loading query statistics: {original}"

    def get_user_friendly_error_message(self, exc: Exception) -> str:
        error_type = self.classify_error_type(exc)
        return self._user_friendly_error_message(error_type, exc)

    def _record_error(self, error_type: str, message: str) -> None:
        self._last_error = {"type": str(error_type or "unknown"), "message": str(message or "")}

    def _clear_error(self) -> None:
        self._last_error = None

    def get_last_error(self) -> Optional[Dict[str, str]]:
        return dict(self._last_error) if isinstance(self._last_error, dict) else None

    def _add_warning(self, message: str) -> None:
        text = str(message or "").strip()
        if not text:
            return
        if text not in self._runtime_warnings:
            self._runtime_warnings.append(text)

    def clear_runtime_warnings(self) -> None:
        self._runtime_warnings = []

    def get_runtime_warnings(self) -> List[str]:
        return list(self._runtime_warnings)

    def get_last_total_count(self) -> int:
        return int(self._last_total_count or 0)

    def _invalidate_runtime_cache(self) -> None:
        """Clear all connection-sensitive runtime cache fields."""
        self._query_store_status = None
        self._sql_version = None

    def _get_connection_cache_key(self) -> str:
        """Build a stable cache key for the active connection context."""
        conn = self.connection
        if not conn:
            return "no_connection"
        profile = getattr(conn, "profile", None)
        profile_id = str(getattr(profile, "id", "") or "")
        server = str(getattr(profile, "server", "") or "")
        database = str(getattr(profile, "database", "") or "")
        if profile_id:
            return f"{profile_id}|{server}|{database}"
        return f"{server}|{database}"

    def _make_top_queries_cache_key(
        self,
        filter_obj: QueryStatsFilter,
        use_qs: bool,
        include_sensitive_data: bool = False,
    ) -> str:
        payload = {
            "conn": self._get_connection_cache_key(),
            "source": "query_store" if use_qs else "dmv",
            "include_sensitive_data": bool(include_sensitive_data),
            "days": int(getattr(filter_obj, "time_range_days", 0) or 0),
            "sort_by": str(getattr(filter_obj, "sort_by", "") or ""),
            "top_n": int(getattr(filter_obj, "top_n", 0) or 0),
            "offset": int(getattr(filter_obj, "offset", 0) or 0),
            "page_size": int(getattr(filter_obj, "page_size", 0) or 0),
            "search_text": str(getattr(filter_obj, "search_text", "") or "").strip().lower(),
            "min_executions": int(getattr(filter_obj, "min_executions", 0) or 0),
            "min_duration_ms": float(getattr(filter_obj, "min_duration_ms", 0.0) or 0.0),
            "object_name_filter": str(getattr(filter_obj, "object_name_filter", "") or "").strip().lower(),
            "priority_filter": str(getattr(getattr(filter_obj, "priority_filter", None), "value", "") or ""),
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)

    def _get_cached_query_store_status(self, connection_key: str) -> Optional[QueryStoreStatus]:
        now = time.time()
        with self._CACHE_LOCK:
            item = self._QUERY_STORE_CACHE.get(connection_key)
            if not item:
                return None
            cached_at, status = item
            if (now - float(cached_at)) > float(self._QUERY_STORE_TTL_SECONDS):
                self._QUERY_STORE_CACHE.pop(connection_key, None)
                return None
            return deepcopy(status)

    def _set_cached_query_store_status(self, connection_key: str, status: QueryStoreStatus) -> None:
        with self._CACHE_LOCK:
            self._QUERY_STORE_CACHE[connection_key] = (time.time(), deepcopy(status))

    def _get_cached_top_queries(self, cache_key: str) -> Optional[Tuple[List[QueryStats], List[str], int]]:
        now = time.time()
        with self._CACHE_LOCK:
            item = self._TOP_QUERIES_CACHE.get(cache_key)
            if not item:
                return None
            cached_at, queries, warnings, total_count = item
            if (now - float(cached_at)) > float(self._TOP_QUERIES_TTL_SECONDS):
                self._TOP_QUERIES_CACHE.pop(cache_key, None)
                return None
            return deepcopy(queries), list(warnings or []), int(total_count or 0)

    def _set_cached_top_queries(
        self,
        cache_key: str,
        queries: List[QueryStats],
        warnings: List[str],
        total_count: int,
    ) -> None:
        with self._CACHE_LOCK:
            self._TOP_QUERIES_CACHE[cache_key] = (
                time.time(),
                deepcopy(list(queries or [])),
                list(warnings or []),
                int(total_count or 0),
            )

    def _get_cached_plan_xml(self, query_id: int, query_hash: Optional[str] = None) -> Optional[str]:
        with self._CACHE_LOCK:
            key = self._QUERY_TO_PLAN_KEY.get(int(query_id))
            if key and key in self._PLAN_XML_CACHE:
                xml = self._PLAN_XML_CACHE.pop(key)
                self._PLAN_XML_CACHE[key] = xml
                return xml
            qh = str(query_hash or "").strip()
            if qh:
                for existing_key in list(self._PLAN_XML_CACHE.keys())[::-1]:
                    if existing_key[0] == qh:
                        xml = self._PLAN_XML_CACHE.pop(existing_key)
                        self._PLAN_XML_CACHE[existing_key] = xml
                        self._QUERY_TO_PLAN_KEY[int(query_id)] = existing_key
                        return xml
        return None

    def _set_cached_plan_xml(
        self,
        query_id: int,
        query_hash: Optional[str],
        plan_hash: Optional[str],
        plan_xml: str,
    ) -> None:
        qh = str(query_hash or f"query_id:{int(query_id)}")
        ph = str(plan_hash or "unknown_plan")
        key = (qh, ph)
        with self._CACHE_LOCK:
            if key in self._PLAN_XML_CACHE:
                self._PLAN_XML_CACHE.pop(key)
            self._PLAN_XML_CACHE[key] = str(plan_xml or "")
            self._QUERY_TO_PLAN_KEY[int(query_id)] = key
            while len(self._PLAN_XML_CACHE) > int(self._PLAN_XML_CACHE_MAX):
                old_key, _ = self._PLAN_XML_CACHE.popitem(last=False)
                stale_ids = [qid for qid, pkey in self._QUERY_TO_PLAN_KEY.items() if pkey == old_key]
                for qid in stale_ids:
                    self._QUERY_TO_PLAN_KEY.pop(qid, None)

    @classmethod
    def invalidate_global_cache(cls, clear_sql_version: bool = False) -> None:
        """Clear shared caches across all QueryStatsService instances."""
        with cls._CACHE_LOCK:
            cls._QUERY_STORE_CACHE.clear()
            cls._PERMISSION_CACHE.clear()
            cls._TOP_QUERIES_CACHE.clear()
            cls._PLAN_XML_CACHE.clear()
            cls._QUERY_TO_PLAN_KEY.clear()
            if clear_sql_version:
                cls._SQL_VERSION_CACHE.clear()
        try:
            from app.analysis.plan_parser import PlanParser
            PlanParser.clear_cache()
        except Exception:
            pass

    def invalidate_connection_cache(self, clear_sql_version: bool = False) -> None:
        """Clear shared caches for current connection context."""
        conn_key = self._get_connection_cache_key()
        conn_marker = f"\"conn\": \"{conn_key}\""
        with self._CACHE_LOCK:
            self._QUERY_STORE_CACHE.pop(conn_key, None)
            self._PERMISSION_CACHE.pop(conn_key, None)
            if clear_sql_version:
                self._SQL_VERSION_CACHE.pop(conn_key, None)
            keys_to_remove = [k for k in self._TOP_QUERIES_CACHE.keys() if conn_marker in k]
            for key in keys_to_remove:
                self._TOP_QUERIES_CACHE.pop(key, None)
        self._invalidate_runtime_cache()

    def invalidate_top_queries_cache(self) -> None:
        """Invalidate only top-queries result cache for current connection."""
        conn_key = self._get_connection_cache_key()
        conn_marker = f"\"conn\": \"{conn_key}\""
        with self._CACHE_LOCK:
            keys_to_remove = [k for k in self._TOP_QUERIES_CACHE.keys() if conn_marker in k]
            for key in keys_to_remove:
                self._TOP_QUERIES_CACHE.pop(key, None)

    def warm_cache(self, force_refresh: bool = False) -> None:
        """Preload Query Store status cache for current connection."""
        if not self.is_connected:
            return
        self.check_query_store_status(force_refresh=force_refresh)

    @classmethod
    def warm_cache_async(cls, connection: Optional['DatabaseConnection'] = None) -> None:
        """Trigger async cache warm-up after connection activation."""
        def _runner(conn_obj: Optional['DatabaseConnection']) -> None:
            try:
                svc = QueryStatsService(connection=conn_obj)
                svc.warm_cache(force_refresh=False)
            except Exception as e:
                logger.debug(f"Query stats warm cache failed: {e}")

        Thread(target=_runner, args=(connection,), daemon=True, name="QueryStatsWarmup").start()
        cls.start_background_refresh()

    @classmethod
    def _background_refresh_loop(cls) -> None:
        while not cls._BG_REFRESH_STOP.wait(float(cls._BG_REFRESH_INTERVAL_SECONDS)):
            try:
                from app.database.connection import get_connection_manager
                conn_mgr = get_connection_manager()
                active_conn = conn_mgr.active_connection
                if active_conn and active_conn.is_connected:
                    svc = QueryStatsService(connection=active_conn)
                    svc.check_query_store_status(force_refresh=True)
            except Exception as e:
                logger.debug(f"Query stats background cache refresh failed: {e}")

    @classmethod
    def start_background_refresh(cls) -> None:
        """Start shared background refresh loop (5 min default)."""
        with cls._CACHE_LOCK:
            if cls._BG_REFRESH_THREAD and cls._BG_REFRESH_THREAD.is_alive():
                return
            cls._BG_REFRESH_STOP.clear()
            cls._BG_REFRESH_THREAD = Thread(
                target=cls._background_refresh_loop,
                daemon=True,
                name="QueryStatsCacheRefresh",
            )
            cls._BG_REFRESH_THREAD.start()

    @classmethod
    def stop_background_refresh(cls) -> None:
        """Stop shared background refresh loop."""
        cls._BG_REFRESH_STOP.set()

    @staticmethod
    def _get_or_create_correlation_id(correlation_id: Optional[str] = None) -> str:
        token = str(correlation_id or "").strip()
        if token:
            return token[:64]
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _sanitize_sql(sql: Optional[str], max_len: int = 400) -> str:
        text = " ".join(str(sql or "").split())
        if len(text) > max_len:
            return f"{text[:max_len]}..."
        return text

    @staticmethod
    def _sanitize_query_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not params:
            return {}
        sanitized: Dict[str, Any] = {}
        for key, value in params.items():
            key_str = str(key)
            if value is None:
                sanitized[key_str] = None
                continue
            if isinstance(value, (int, float, bool)):
                sanitized[key_str] = value
                continue
            value_text = str(value)
            if len(value_text) > 80:
                sanitized[key_str] = {"len": len(value_text), "preview": value_text[:40]}
            else:
                sanitized[key_str] = value_text
        return sanitized

    @staticmethod
    def _sanitize_filter(filter_obj: Optional[QueryStatsFilter]) -> Dict[str, Any]:
        if not filter_obj:
            return {}
        return {
            "time_range_days": int(getattr(filter_obj, "time_range_days", 0) or 0),
            "sort_by": str(getattr(filter_obj, "sort_by", "") or ""),
            "top_n": int(getattr(filter_obj, "top_n", 0) or 0),
            "offset": int(getattr(filter_obj, "offset", 0) or 0),
            "page_size": int(getattr(filter_obj, "page_size", 0) or 0),
            "search_text_len": len(str(getattr(filter_obj, "search_text", "") or "")),
            "min_executions": int(getattr(filter_obj, "min_executions", 0) or 0),
            "min_duration_ms": float(getattr(filter_obj, "min_duration_ms", 0.0) or 0.0),
            "has_object_name_filter": bool(getattr(filter_obj, "object_name_filter", None)),
            "priority_filter": str(getattr(getattr(filter_obj, "priority_filter", None), "value", "") or ""),
        }

    def _get_cached_permission_status(self, connection_key: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        with self._CACHE_LOCK:
            item = self._PERMISSION_CACHE.get(connection_key)
            if not item:
                return None
            cached_at, payload = item
            if (now - float(cached_at)) > float(self._PERMISSION_TTL_SECONDS):
                self._PERMISSION_CACHE.pop(connection_key, None)
                return None
            return deepcopy(payload)

    def _set_cached_permission_status(self, connection_key: str, payload: Dict[str, Any]) -> None:
        with self._CACHE_LOCK:
            self._PERMISSION_CACHE[connection_key] = (time.time(), deepcopy(payload))

    @staticmethod
    def redact_sql_literals(sql_text: Optional[str]) -> str:
        """Redact string and long numeric literals while keeping SQL structure visible."""
        return str(sql_text or "")

    @staticmethod
    def redact_plan_expression_literals(expression: Optional[str]) -> str:
        """Redact constants inside execution plan scalar expressions."""
        return str(expression or "")

    def sanitize_plan_xml(self, plan_xml: Optional[str]) -> str:
        """Remove sensitive literals/parameter values from execution plan XML."""
        return str(plan_xml or "")

    def _get_connection_context(self) -> Dict[str, Any]:
        conn = self.connection
        if not conn:
            return {"connected": False}

        profile = getattr(conn, "profile", None)
        info = getattr(conn, "info", None)
        return {
            "connected": bool(getattr(conn, "is_connected", False)),
            "server": str(getattr(profile, "server", "") or ""),
            "database": str(getattr(profile, "database", "") or ""),
            "driver": str(getattr(profile, "driver", "") or ""),
            "auth_method": str(getattr(getattr(profile, "auth_method", None), "value", "") or ""),
            "database_name": str(getattr(info, "database_name", "") or ""),
            "major_version": int(getattr(info, "major_version", 0) or 0),
        }

    def _to_non_negative_float(
        self,
        value: Any,
        field_name: str,
        row_id: str,
    ) -> float:
        try:
            number = float(value or 0.0)
        except Exception:
            self._add_warning(f"Invalid numeric value for {field_name} ({row_id}); replaced with 0.")
            return 0.0
        if number < 0:
            self._add_warning(f"Negative value for {field_name} ({row_id}); clamped to 0.")
            return 0.0
        return number

    def _to_positive_int(
        self,
        value: Any,
        field_name: str,
        row_id: str,
    ) -> int:
        try:
            number = int(value or 0)
        except Exception:
            self._add_warning(f"Invalid integer value for {field_name} ({row_id}); replaced with 0.")
            return 0
        if number < 0:
            self._add_warning(f"Negative value for {field_name} ({row_id}); clamped to 0.")
            return 0
        return number

    def _sanitize_query_text(
        self,
        query_text: Any,
        row_id: str,
        include_sensitive_data: bool = False,
    ) -> str:
        text = str(query_text or "").strip()
        if not text:
            self._add_warning(f"Missing query text ({row_id}); displaying as N/A.")
            return "N/A"
        if len(text) > int(self._MAX_UI_QUERY_TEXT_CHARS):
            self._add_warning(
                f"Query text too long ({row_id}); truncated to {self._MAX_UI_QUERY_TEXT_CHARS} chars."
            )
            text = text[: int(self._MAX_UI_QUERY_TEXT_CHARS)] + "\n-- [truncated for UI]"
        return text

    def _sanitize_top_query_row(
        self,
        row: Dict[str, Any],
        is_query_store: bool,
        include_sensitive_data: bool = False,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(row, dict):
            self._add_warning("Invalid query row type; skipped.")
            return None

        safe = dict(row)
        raw_id = safe.get("query_id")
        query_hash = str(safe.get("query_hash", "") or "").strip()
        row_id = (
            f"query_id={raw_id}"
            if raw_id is not None
            else (f"query_hash={query_hash[:16]}" if query_hash else "query=unknown")
        )

        if is_query_store and raw_id is None:
            self._add_warning("Skipped Query Store row with missing query_id.")
            return None

        executions = self._to_positive_int(safe.get("total_executions", 0), "total_executions", row_id)
        if executions <= 0:
            self._add_warning(f"Skipped row with non-positive execution count ({row_id}).")
            return None
        safe["total_executions"] = executions

        safe["avg_duration_ms"] = self._to_non_negative_float(
            safe.get("avg_duration_ms", 0), "avg_duration_ms", row_id
        )
        safe["max_duration_ms"] = self._to_non_negative_float(
            safe.get("max_duration_ms", 0), "max_duration_ms", row_id
        )
        safe["avg_cpu_ms"] = self._to_non_negative_float(
            safe.get("avg_cpu_ms", 0), "avg_cpu_ms", row_id
        )
        safe["avg_logical_reads"] = self._to_non_negative_float(
            safe.get("avg_logical_reads", 0), "avg_logical_reads", row_id
        )
        safe["avg_logical_writes"] = self._to_non_negative_float(
            safe.get("avg_logical_writes", 0), "avg_logical_writes", row_id
        )
        safe["avg_physical_reads"] = self._to_non_negative_float(
            safe.get("avg_physical_reads", 0), "avg_physical_reads", row_id
        )
        safe["impact_score"] = self._to_non_negative_float(
            safe.get("impact_score", 0), "impact_score", row_id
        )
        safe["plan_count"] = max(
            1,
            self._to_positive_int(safe.get("plan_count", 1), "plan_count", row_id),
        )

        safe["query_text"] = self._sanitize_query_text(
            safe.get("query_text"),
            row_id,
            include_sensitive_data=include_sensitive_data,
        )

        object_name = safe.get("object_name")
        if object_name is None or str(object_name).strip() == "":
            safe["object_name"] = "N/A"

        if not query_hash:
            generated_hash = f"missing_hash_{abs(hash(safe['query_text'])) % 10_000_000}"
            safe["query_hash"] = generated_hash
            self._add_warning(f"Missing query hash ({row_id}); generated fallback hash.")

        return safe

    def _validate_plan_xml_well_formed(
        self,
        plan_xml: str,
        query_id: Optional[int] = None,
        plan_id: Optional[int] = None,
    ) -> bool:
        xml_text = str(plan_xml or "").strip()
        if not xml_text:
            return False
        try:
            ET.fromstring(xml_text)
            return True
        except ET.ParseError as e:
            q = int(query_id or 0)
            p = int(plan_id or 0)
            self._add_warning(
                f"Corrupt execution plan XML detected for query {q} (plan {p})."
            )
            self._log_structured(
                logging.ERROR,
                "corrupt_plan_xml_detected",
                query_id=q,
                plan_id=p,
                error_message=str(e),
                xml_preview=xml_text[:320],
            )
            logger.error(f"Corrupt plan XML [query_id={q}, plan_id={p}]: {e}")
            return False

    def _log_structured(
        self,
        level: int,
        event: str,
        correlation_id: Optional[str] = None,
        **fields: Any,
    ) -> None:
        payload: Dict[str, Any] = {
            "event": str(event or "unknown_event"),
            "component": "query_stats_service",
            "correlation_id": self._get_or_create_correlation_id(correlation_id),
            "timestamp_utc": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        }
        payload.update(fields)
        logger.log(level, json.dumps(payload, ensure_ascii=True, default=str))

    @classmethod
    def _percentile(cls, values: List[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(float(v) for v in values)
        rank = max(0, min(len(ordered) - 1, int(round((percentile / 100.0) * (len(ordered) - 1)))))
        return float(ordered[rank])

    @classmethod
    def _record_load_outcome(cls, duration_ms: float, outcome: str) -> None:
        with cls._OBS_LOCK:
            cls._LOAD_DURATIONS_MS.append(max(0.0, float(duration_ms)))
            if outcome == "success":
                cls._LOAD_SUCCESS_COUNT += 1
            elif outcome == "cancelled":
                cls._LOAD_CANCELLED_COUNT += 1
            else:
                cls._LOAD_ERROR_COUNT += 1

    @classmethod
    def _record_usage(cls, source: str, sort_by: str) -> None:
        source_key = str(source or "unknown")
        sort_key = str(sort_by or "unknown")
        with cls._OBS_LOCK:
            cls._SOURCE_USAGE[source_key] = int(cls._SOURCE_USAGE.get(source_key, 0)) + 1
            cls._SORT_BY_USAGE[sort_key] = int(cls._SORT_BY_USAGE.get(sort_key, 0)) + 1

    @classmethod
    def get_observability_metrics(cls) -> Dict[str, Any]:
        with cls._OBS_LOCK:
            durations = [float(v) for v in cls._LOAD_DURATIONS_MS]
            success_count = int(cls._LOAD_SUCCESS_COUNT)
            error_count = int(cls._LOAD_ERROR_COUNT)
            cancelled_count = int(cls._LOAD_CANCELLED_COUNT)
            source_usage = {k: int(v) for k, v in cls._SOURCE_USAGE.items()}
            sort_usage = {k: int(v) for k, v in cls._SORT_BY_USAGE.items()}

        measured_count = len(durations)
        denominator = max(1, success_count + error_count)
        return {
            "sample_size": measured_count,
            "success_count": success_count,
            "error_count": error_count,
            "cancelled_count": cancelled_count,
            "avg_load_time_ms": round(sum(durations) / measured_count, 2) if measured_count else 0.0,
            "p95_load_time_ms": round(cls._percentile(durations, 95), 2) if measured_count else 0.0,
            "error_rate": round(error_count / denominator, 4),
            "source_usage": source_usage,
            "sort_by_usage": sort_usage,
        }

    def export_observability_metrics(self) -> Dict[str, Any]:
        """Expose aggregated Query Statistics load metrics for app-level monitoring."""
        return self.get_observability_metrics()

    @staticmethod
    def _raise_if_cancelled(cancel_check: Optional[Callable[[], bool]] = None) -> None:
        if cancel_check is None:
            return
        try:
            cancelled = bool(cancel_check())
        except Exception:
            cancelled = False
        if cancelled:
            raise TaskCancelledError("Query statistics load was cancelled.")

    def _execute_query_with_retry(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        operation_name: str = "query",
        max_attempts: int = 3,
        initial_backoff_seconds: float = 0.4,
        cancel_check: Optional[Callable[[], bool]] = None,
        correlation_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute query with exponential backoff for transient failures."""
        conn = self.connection
        if not conn or not conn.is_connected:
            raise DBConnectionError("No active database connection")

        backoff = max(0.1, float(initial_backoff_seconds))
        last_error: Optional[Exception] = None
        safe_sql = self._sanitize_sql(sql)
        safe_params = self._sanitize_query_params(params)
        corr = self._get_or_create_correlation_id(correlation_id)
        for attempt in range(1, max(1, int(max_attempts)) + 1):
            self._raise_if_cancelled(cancel_check)
            attempt_start = time.perf_counter()
            self._log_structured(
                logging.DEBUG,
                "query_execute_attempt",
                correlation_id=corr,
                operation=operation_name,
                attempt=attempt,
                max_attempts=max_attempts,
                sql=safe_sql,
                params=safe_params,
            )
            try:
                rows = conn.execute_query(sql, params)
                duration_ms = round((time.perf_counter() - attempt_start) * 1000.0, 2)
                self._log_structured(
                    logging.DEBUG,
                    "query_execute_success",
                    correlation_id=corr,
                    operation=operation_name,
                    attempt=attempt,
                    duration_ms=duration_ms,
                    row_count=len(rows) if isinstance(rows, list) else 0,
                )
                return rows
            except Exception as e:
                last_error = e
                self._raise_if_cancelled(cancel_check)
                if isinstance(e, DBConnectionError) or self.classify_error_type(e) == "connection":
                    self.invalidate_connection_cache(clear_sql_version=False)
                transient = self._is_transient_error(e)
                error_type = self.classify_error_type(e)
                duration_ms = round((time.perf_counter() - attempt_start) * 1000.0, 2)
                level = logging.WARNING if transient and attempt < max_attempts else logging.ERROR
                self._log_structured(
                    level,
                    "query_execute_error",
                    correlation_id=corr,
                    operation=operation_name,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    transient=transient,
                    duration_ms=duration_ms,
                    error_type=error_type,
                    error_message=str(e),
                    sql=safe_sql,
                    params=safe_params,
                    connection=self._get_connection_context(),
                    stack_trace=traceback.format_exc(),
                )
                if (not transient) or attempt >= max_attempts:
                    raise
                logger.warning(
                    f"{operation_name} failed (attempt {attempt}/{max_attempts}): {e}. "
                    f"Retrying in {backoff:.1f}s..."
                )
                waited = 0.0
                while waited < backoff:
                    self._raise_if_cancelled(cancel_check)
                    step = min(0.1, backoff - waited)
                    time.sleep(step)
                    waited += step
                backoff = min(backoff * 2.0, 3.0)

        if last_error is not None:
            raise last_error
        return []
    
    @property
    def connection(self) -> Optional['DatabaseConnection']:
        """Aktif veritabanı bağlantısı"""
        if self._connection:
            return self._connection

        conn_mgr = None
        if callable(self._connection_manager_provider):
            try:
                conn_mgr = self._connection_manager_provider()
            except Exception as e:
                logger.warning(f"Custom connection manager provider failed: {e}")

        if conn_mgr is None:
            from app.database.connection import get_connection_manager

            conn_mgr = get_connection_manager()

        return getattr(conn_mgr, "active_connection", None)
    
    @property
    def is_connected(self) -> bool:
        """Bağlantı var mı?"""
        conn = self.connection
        return conn is not None and conn.is_connected

    def cancel_current_operation(self) -> bool:
        """Request cancellation for the currently running DB operation."""
        conn = self.connection
        if not conn or not conn.is_connected:
            return False
        cancel_fn = getattr(conn, "cancel_active_query", None)
        if not callable(cancel_fn):
            return False
        try:
            return bool(cancel_fn())
        except Exception as e:
            logger.debug(f"Failed to cancel current operation: {e}")
            return False
    
    def _get_sql_version(self) -> int:
        """SQL Server major version'ı al"""
        if self._sql_version is not None:
            return self._sql_version
        
        conn = self.connection
        if not conn or not conn.info:
            return 0

        connection_key = self._get_connection_cache_key()
        with self._CACHE_LOCK:
            cached_version = self._SQL_VERSION_CACHE.get(connection_key)
        if cached_version is not None:
            self._sql_version = int(cached_version or 0)
            return self._sql_version

        self._sql_version = int(conn.info.major_version or 0)
        with self._CACHE_LOCK:
            self._SQL_VERSION_CACHE[connection_key] = self._sql_version
        return self._sql_version
    
    def _supports_query_store(self) -> bool:
        """Query Store destekleniyor mu? (SQL 2016+)"""
        return self._get_sql_version() >= 13
    
    def _supports_query_store_wait_stats(self) -> bool:
        """Query Store Wait Stats destekleniyor mu? (SQL 2017+)"""
        return self._get_sql_version() >= 14
    
    # ==========================================================================
    # QUERY STORE DURUM KONTROLÜ
    # ==========================================================================
    
    def check_query_store_status(self, force_refresh: bool = False) -> QueryStoreStatus:
        """
        Query Store durumunu kontrol et
        
        Returns:
            QueryStoreStatus modeli
        """
        if not self.is_connected:
            logger.warning("No active connection for Query Store check")
            return QueryStoreStatus(is_enabled=False)

        connection_key = self._get_connection_cache_key()
        if not force_refresh:
            cached = self._get_cached_query_store_status(connection_key)
            if cached is not None:
                self._query_store_status = cached
                return cached

        if not self._supports_query_store():
            logger.info(f"SQL Server version {self._get_sql_version()} does not support Query Store")
            disabled = QueryStoreStatus(is_enabled=False)
            self._query_store_status = disabled
            self._set_cached_query_store_status(connection_key, disabled)
            return disabled
        
        try:
            results = self._execute_query_with_retry(
                QueryStoreQueries.CHECK_QUERY_STORE_ENABLED,
                operation_name="check_query_store_status",
            )
            
            if not results:
                return QueryStoreStatus(is_enabled=False)
            
            row = results[0]
            status = QueryStoreStatus(
                is_enabled=bool(row.get('is_enabled', 0)),
                desired_state=str(row.get('desired_state_desc', '') or ''),
                actual_state=str(row.get('actual_state_desc', '') or ''),
                current_storage_mb=float(row.get('current_storage_size_mb', 0) or 0),
                max_storage_mb=float(row.get('max_storage_size_mb', 0) or 0),
                query_capture_mode=str(row.get('query_capture_mode_desc', '') or ''),
                stale_query_threshold_days=int(row.get('stale_query_threshold_days', 0) or 0),
                size_based_cleanup_mode=str(row.get('size_based_cleanup_mode_desc', '') or ''),
            )
            
            self._query_store_status = status
            self._set_cached_query_store_status(connection_key, status)
            logger.info(f"Query Store status: enabled={status.is_enabled}, state={status.actual_state}")
            
            return status
            
        except Exception as e:
            self.invalidate_connection_cache(clear_sql_version=False)
            logger.error(f"Failed to check Query Store status: {e}")
            return QueryStoreStatus(is_enabled=False)
    
    def use_query_store(self, force_refresh: bool = False) -> bool:
        """Query Store kullanılmalı mı?"""
        status = self.check_query_store_status(force_refresh=force_refresh)
        self._query_store_status = status
        return bool(status.is_operational)

    def get_permission_status(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Check module permissions and return graceful-degradation flags.

        Returns:
            {
              has_view_server_state: bool,
              can_read_sql_modules: bool,
              module_enabled: bool,
              source_code_enabled: bool,
              warnings: List[str],
              missing_permissions: List[str],
              documentation_url: str,
            }
        """
        docs_url = (
            "https://learn.microsoft.com/sql/relational-databases/security/permissions-database-engine"
        )
        default_payload = {
            "has_view_server_state": False,
            "can_read_sql_modules": False,
            "module_enabled": False,
            "source_code_enabled": False,
            "warnings": ["No active database connection."],
            "missing_permissions": ["VIEW SERVER STATE", "VIEW DEFINITION/SELECT on sys.sql_modules"],
            "documentation_url": docs_url,
        }
        if not self.is_connected:
            return default_payload

        connection_key = self._get_connection_cache_key()
        if not force_refresh:
            cached = self._get_cached_permission_status(connection_key)
            if cached is not None:
                return cached

        warnings: List[str] = []
        missing: List[str] = []
        has_view_server_state = False
        can_read_sql_modules = False

        try:
            perm_rows = self._execute_query_with_retry(
                "SELECT CAST(HAS_PERMS_BY_NAME(NULL, NULL, 'VIEW SERVER STATE') AS INT) AS has_perm",
                operation_name="permission_check_view_server_state",
                max_attempts=1,
            )
            has_view_server_state = bool(int((perm_rows[0] or {}).get("has_perm", 0) or 0)) if perm_rows else False
        except Exception as exc:
            warnings.append(f"VIEW SERVER STATE permission check failed: {exc}")

        if not has_view_server_state:
            missing.append("VIEW SERVER STATE")
            warnings.append(
                "Missing VIEW SERVER STATE. Query Statistics is disabled for this connection."
            )

        try:
            vd_rows = self._execute_query_with_retry(
                "SELECT CAST(HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DEFINITION') AS INT) AS has_perm",
                operation_name="permission_check_view_definition",
                max_attempts=1,
            )
            has_view_definition = bool(int((vd_rows[0] or {}).get("has_perm", 0) or 0)) if vd_rows else False
            can_read_sql_modules = bool(has_view_definition)

            self._execute_query_with_retry(
                "SELECT TOP (1) definition FROM sys.sql_modules",
                operation_name="permission_check_sql_modules_select",
                max_attempts=1,
            )
            can_read_sql_modules = True
        except Exception as exc:
            warnings.append(f"sys.sql_modules access check failed: {exc}")

        if not can_read_sql_modules:
            missing.append("VIEW DEFINITION/SELECT on sys.sql_modules")
            warnings.append(
                "Source code view is unavailable: missing VIEW DEFINITION or SELECT access on sys.sql_modules."
            )

        payload = {
            "has_view_server_state": bool(has_view_server_state),
            "can_read_sql_modules": bool(can_read_sql_modules),
            "module_enabled": bool(has_view_server_state),
            "source_code_enabled": bool(can_read_sql_modules),
            "warnings": warnings,
            "missing_permissions": missing,
            "documentation_url": docs_url,
        }
        self._set_cached_permission_status(connection_key, payload)
        return payload

    def get_module_health(
        self,
        min_retention_days: int = 1,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Proactive health check for Query Statistics module.
        Includes Query Store configuration and connection pool pressure checks.
        """
        corr = self._get_or_create_correlation_id(correlation_id)
        warnings: List[str] = []
        qs_status: Optional[QueryStoreStatus] = None
        pool_health: Dict[str, Any] = {}
        docs_url = (
            "https://learn.microsoft.com/sql/relational-databases/performance/"
            "monitoring-performance-by-using-the-query-store"
        )
        query_store_guidance: List[str] = []
        query_count = 0
        most_recent_execution = None
        hours_since_last_execution: Optional[float] = None
        is_data_recent = False
        quality_state = "red"
        permissions_status = self.get_permission_status(force_refresh=False)

        if not self.is_connected:
            warnings.append("No active database connection for Query Statistics health check.")
            report = {
                "healthy": False,
                "warnings": warnings,
                "permissions": permissions_status,
                "query_store": {
                    "quality_state": "red",
                    "guidance": ["Connect to a database to evaluate Query Store health."],
                    "documentation_url": docs_url,
                },
                "pool": {},
            }
            self._log_structured(
                logging.WARNING,
                "query_stats_health_check",
                correlation_id=corr,
                healthy=False,
                warnings=warnings,
                query_store={},
                pool={},
            )
            return report

        try:
            if not bool(permissions_status.get("has_view_server_state", False)):
                quality_state = "red"
                for msg in list(permissions_status.get("warnings", []) or []):
                    if msg not in warnings:
                        warnings.append(msg)
            elif not bool(permissions_status.get("source_code_enabled", False)):
                for msg in list(permissions_status.get("warnings", []) or []):
                    if "Source code view is unavailable" in str(msg or "") and msg not in warnings:
                        warnings.append(msg)

            if self._supports_query_store():
                qs_status = self.check_query_store_status(force_refresh=False)
                if not qs_status.is_enabled:
                    quality_state = "red"
                    warnings.append(
                        "Query Store is disabled. Recommendation: enable Query Store for this database "
                        "(ALTER DATABASE [db] SET QUERY_STORE = ON)."
                    )
                    query_store_guidance.append("Enable Query Store for richer and more accurate analysis results.")
                elif str(qs_status.actual_state or "").upper() != "READ_WRITE":
                    quality_state = "red"
                    warnings.append(
                        "Query Store is not in READ_WRITE state. Recommendation: investigate READ_ONLY reason "
                        "and switch to READ_WRITE for full Query Statistics coverage."
                    )
                    query_store_guidance.append("Switch Query Store to READ_WRITE state to collect fresh runtime data.")
                else:
                    quality_state = "green"
                    try:
                        quality_rows = self._execute_query_with_retry(
                            QueryStoreQueries.QUERY_STORE_DATA_QUALITY,
                            operation_name="query_store_data_quality",
                            correlation_id=corr,
                        )
                        if quality_rows:
                            qrow = quality_rows[0]
                            query_count = int(qrow.get("query_count", 0) or 0)
                            most_recent_execution = qrow.get("most_recent_execution")

                        if query_count <= 0:
                            quality_state = "yellow"
                            warnings.append(
                                "Query Store is enabled but has no captured query data yet."
                            )
                            query_store_guidance.append("Run workload queries to generate Query Store data.")

                        if most_recent_execution is not None:
                            dt_value = None
                            if isinstance(most_recent_execution, datetime):
                                dt_value = most_recent_execution
                            else:
                                try:
                                    dt_value = datetime.fromisoformat(str(most_recent_execution).replace("Z", "+00:00"))
                                except Exception:
                                    dt_value = None
                            if dt_value is not None:
                                delta = datetime.now(dt_value.tzinfo) - dt_value
                                hours_since_last_execution = max(0.0, delta.total_seconds() / 3600.0)
                                is_data_recent = hours_since_last_execution <= 24.0
                            else:
                                is_data_recent = False
                        if most_recent_execution is None:
                            quality_state = "yellow" if quality_state != "red" else quality_state
                            warnings.append(
                                "Query Store data recency could not be verified (no runtime executions found)."
                            )
                            query_store_guidance.append("Execute queries and refresh to populate runtime stats.")
                        elif not is_data_recent:
                            quality_state = "yellow" if quality_state != "red" else quality_state
                            warnings.append(
                                f"Query Store data is stale (last execution ~{hours_since_last_execution:.1f}h ago)."
                            )
                            query_store_guidance.append(
                                "Run recent workload queries to refresh Query Store statistics."
                            )
                    except Exception as quality_error:
                        quality_state = "yellow" if quality_state != "red" else quality_state
                        warnings.append(f"Query Store quality check failed: {quality_error}")
                        query_store_guidance.append(
                            "Review Query Store runtime stats views and permissions."
                        )

                if not qs_status.has_min_retention(max(1, int(min_retention_days))):
                    quality_state = "yellow" if quality_state != "red" else quality_state
                    warnings.append(
                        f"Query Store retention is below {max(1, int(min_retention_days))} day(s). "
                        "Recommendation: set CLEANUP_POLICY(STALE_QUERY_THRESHOLD_DAYS >= 1)."
                    )
                    query_store_guidance.append("Increase Query Store retention to at least 1 day.")

                if qs_status.storage_percent >= 90:
                    quality_state = "yellow" if quality_state != "red" else quality_state
                    warnings.append(
                        f"Query Store storage is high ({qs_status.storage_percent:.1f}%). "
                        "Recommendation: increase max storage or tune cleanup policy."
                    )
                elif qs_status.storage_percent >= 80:
                    quality_state = "yellow" if quality_state != "red" else quality_state
                    warnings.append(
                        f"Query Store storage is approaching limit ({qs_status.storage_percent:.1f}%). "
                        "Monitor growth to avoid READ_ONLY transitions."
                    )

                if qs_status.size_based_cleanup_mode and qs_status.size_based_cleanup_mode.upper() != "AUTO":
                    quality_state = "yellow" if quality_state != "red" else quality_state
                    warnings.append(
                        "Query Store size-based cleanup mode is not AUTO. Recommendation: enable AUTO cleanup "
                        "for safer storage management."
                    )
            else:
                quality_state = "red"
                warnings.append(
                    "SQL Server version does not support Query Store. Query Statistics will use DMV fallback."
                )
                query_store_guidance.append(
                    "Upgrade SQL Server version or continue using DMV fallback with limited historical depth."
                )

            conn = self.connection
            if conn:
                pool_health_fn = getattr(conn, "get_pool_health", None)
                if callable(pool_health_fn):
                    pool_health = pool_health_fn() or {}

            if pool_health:
                utilization = float(pool_health.get("utilization_pct", 0.0) or 0.0)
                queue_depth = int(pool_health.get("queue_depth_estimate", 0) or 0)
                if bool(pool_health.get("is_exhausted", False)):
                    warnings.append(
                        "Connection pool is exhausted. Recommendation: reduce concurrent requests or increase "
                        "pool capacity."
                    )
                elif utilization >= 85.0:
                    warnings.append(
                        f"Connection pool utilization is high ({utilization:.1f}%). "
                        "Monitor for request contention."
                    )
                if queue_depth > 0:
                    warnings.append(
                        f"Connection pool queue depth is elevated ({queue_depth}). "
                        "Some requests may be waiting for a free connection."
                    )
        except Exception as e:
            quality_state = "yellow" if quality_state != "red" else quality_state
            warnings.append(f"Health check failed: {e}")
            self._log_structured(
                logging.ERROR,
                "query_stats_health_check_error",
                correlation_id=corr,
                error_message=str(e),
                stack_trace=traceback.format_exc(),
            )

        report = {
            "healthy": len(warnings) == 0,
            "warnings": warnings,
            "permissions": permissions_status,
            "query_store": {
                "is_enabled": bool(qs_status.is_enabled) if qs_status else False,
                "desired_state": str(qs_status.desired_state) if qs_status else "",
                "actual_state": str(qs_status.actual_state) if qs_status else "",
                "query_capture_mode": str(qs_status.query_capture_mode) if qs_status else "",
                "storage_percent": float(qs_status.storage_percent) if qs_status else 0.0,
                "stale_query_threshold_days": int(qs_status.stale_query_threshold_days) if qs_status else 0,
                "size_based_cleanup_mode": str(qs_status.size_based_cleanup_mode) if qs_status else "",
                "query_count": int(query_count or 0),
                "most_recent_execution": most_recent_execution,
                "hours_since_last_execution": float(hours_since_last_execution or 0.0),
                "is_data_recent": bool(is_data_recent),
                "quality_state": quality_state,
                "guidance": query_store_guidance,
                "documentation_url": docs_url,
            },
            "pool": pool_health,
        }
        self._log_structured(
            logging.INFO if report["healthy"] else logging.WARNING,
            "query_stats_health_check",
            correlation_id=corr,
            healthy=report["healthy"],
            warnings=warnings,
            permissions=permissions_status,
            query_store=report["query_store"],
            pool=pool_health,
        )
        return report
    
    # ==========================================================================
    # TOP QUERIES (LİSTE GÖRÜNÜMÜ)
    # ==========================================================================
    
    def get_top_queries(
        self, 
        filter: Optional[QueryStatsFilter] = None,
        raise_on_error: bool = False,
        cancel_check: Optional[Callable[[], bool]] = None,
        correlation_id: Optional[str] = None,
        force_refresh: bool = False,
        include_sensitive_data: bool = False,
    ) -> List[QueryStats]:
        """
        En yavaş/etkili sorguları getir
        
        Args:
            filter: Filtreleme seçenekleri
        
        Returns:
            QueryStats listesi
        """
        corr = self._get_or_create_correlation_id(correlation_id)
        load_start = time.perf_counter()
        row_count = 0
        outcome = "error"
        error_type = ""

        self.clear_runtime_warnings()
        self._clear_error()
        self._last_total_count = 0
        try:
            self._raise_if_cancelled(cancel_check)
            if not self.is_connected:
                msg = "No active connection"
                logger.warning(msg)
                self._record_error("connection", msg)
                error_type = "connection"
                if raise_on_error:
                    raise DBConnectionError(msg)
                return []
            
            filter = filter or QueryStatsFilter()
            use_qs = self.use_query_store(force_refresh=force_refresh)

            if use_qs:
                source_reason = "query_store_operational"
            elif not self._supports_query_store():
                source_reason = "sql_version_not_supported"
            elif self._query_store_status is None:
                source_reason = "query_store_status_unavailable"
            else:
                state = str(self._query_store_status.actual_state or "unknown").lower()
                source_reason = f"query_store_state_{state}"
            
            # Sorguyu seç
            sql = QueryStoreQueries.get_top_queries_sql(use_query_store=use_qs)
            
            # Parametreleri hazırla
            params = filter.to_params()
            safe_filter = self._sanitize_filter(filter)
            source_name = "query_store" if use_qs else "dmv"
            self._record_usage(source_name, str(getattr(filter, "sort_by", "") or "unknown"))
            cache_key = self._make_top_queries_cache_key(
                filter,
                use_qs,
                include_sensitive_data=include_sensitive_data,
            )

            if force_refresh:
                self.invalidate_top_queries_cache()
            else:
                cached_payload = self._get_cached_top_queries(cache_key)
                if cached_payload is not None:
                    cached_queries, cached_warnings, cached_total_count = cached_payload
                    self.clear_runtime_warnings()
                    for warn in cached_warnings:
                        self._add_warning(warn)
                    self._last_total_count = int(cached_total_count or len(cached_queries))
                    outcome = "success"
                    row_count = len(cached_queries)
                    self._log_structured(
                        logging.INFO,
                        "query_stats_cache_hit",
                        correlation_id=corr,
                        cache="top_queries",
                        row_count=row_count,
                        source=source_name,
                        cache_ttl_seconds=self._TOP_QUERIES_TTL_SECONDS,
                    )
                    return cached_queries
            
            self._log_structured(
                logging.INFO,
                "query_stats_source_selected",
                correlation_id=corr,
                source=source_name,
                reason=source_reason,
                filter=safe_filter,
                params=self._sanitize_query_params(params),
                connection=self._get_connection_context(),
            )
            logger.info(f"Fetching top queries (Query Store: {use_qs}, days: {params['days']})")

            try:
                results = self._execute_query_with_retry(
                    sql,
                    params=params,
                    operation_name="get_top_queries.query_store" if use_qs else "get_top_queries.dmv",
                    cancel_check=cancel_check,
                    correlation_id=corr,
                )
            except Exception as primary_error:
                primary_type = self.classify_error_type(primary_error)
                error_type = primary_type
                if primary_type == "cancelled":
                    friendly = self._user_friendly_error_message(primary_type, primary_error)
                    self._record_error(primary_type, friendly)
                    outcome = "cancelled"
                    if raise_on_error:
                        raise primary_error
                    logger.info("Top queries load cancelled.")
                    return []
                if use_qs:
                    self._add_warning(
                        "Query Store path failed; results are loaded from DMV fallback and may be limited."
                    )
                    self.invalidate_connection_cache(clear_sql_version=False)
                    self._log_structured(
                        logging.WARNING,
                        "query_stats_source_fallback",
                        correlation_id=corr,
                        from_source="query_store",
                        to_source="dmv",
                        reason="query_store_query_failed",
                        primary_error_type=primary_type,
                        primary_error_message=str(primary_error),
                    )
                    try:
                        fallback_sql = QueryStoreQueries.get_top_queries_sql(use_query_store=False)
                        results = self._execute_query_with_retry(
                            fallback_sql,
                            params=params,
                            operation_name="get_top_queries.dmv_fallback",
                            cancel_check=cancel_check,
                            correlation_id=corr,
                        )
                        use_qs = False
                        self._record_usage("dmv_fallback", str(getattr(filter, "sort_by", "") or "unknown"))
                    except Exception as fallback_error:
                        fallback_type = self.classify_error_type(fallback_error)
                        error_type = fallback_type
                        if fallback_type == "cancelled":
                            friendly = self._user_friendly_error_message(fallback_type, fallback_error)
                            self._record_error(fallback_type, friendly)
                            outcome = "cancelled"
                            if raise_on_error:
                                raise fallback_error
                            logger.info("Top queries load cancelled during fallback.")
                            return []
                        friendly = self._user_friendly_error_message(fallback_type, fallback_error)
                        self._record_error(fallback_type, friendly)
                        if raise_on_error:
                            raise fallback_error
                        logger.error(f"Failed to get top queries (fallback): {fallback_error}")
                        return []
                else:
                    friendly = self._user_friendly_error_message(primary_type, primary_error)
                    self._record_error(primary_type, friendly)
                    if raise_on_error:
                        raise primary_error
                    logger.error(f"Failed to get top queries: {primary_error}")
                    return []
            
            if not results:
                outcome = "success"
                row_count = 0
                logger.info("No queries found")
                cache_key = self._make_top_queries_cache_key(
                    filter,
                    use_qs,
                    include_sensitive_data=include_sensitive_data,
                )
                offset_value = int(getattr(filter, "offset", 0) or 0)
                if offset_value <= 0:
                    self._last_total_count = 0
                self._set_cached_top_queries(
                    cache_key,
                    [],
                    self.get_runtime_warnings(),
                    int(self._last_total_count or 0),
                )
                return []
            
            # Sonuçları modele dönüştür
            queries = []
            total_count_from_sql = 0
            for row in results:
                self._raise_if_cancelled(cancel_check)
                safe_row = self._sanitize_top_query_row(
                    row,
                    is_query_store=use_qs,
                    include_sensitive_data=include_sensitive_data,
                )
                if safe_row is None:
                    continue
                total_count_from_sql = max(
                    int(total_count_from_sql or 0),
                    int(safe_row.get("total_count", 0) or 0),
                )
                query_stats = self._row_to_query_stats(
                    safe_row,
                    use_qs,
                    include_sensitive_data=include_sensitive_data,
                )
                
                # Filtreleme uygula
                if filter.search_text:
                    search_lower = filter.search_text.lower()
                    if search_lower not in query_stats.display_name.lower():
                        if search_lower not in query_stats.query_text.lower():
                            continue
                
                if filter.min_executions > 0:
                    if query_stats.metrics.total_executions < filter.min_executions:
                        continue
                
                if filter.min_duration_ms > 0:
                    if query_stats.metrics.avg_duration_ms < filter.min_duration_ms:
                        continue
                
                if filter.priority_filter:
                    if query_stats.priority != filter.priority_filter:
                        continue
                
                queries.append(query_stats)

            if results and not queries:
                self._add_warning(
                    "All query rows were filtered out due to data quality validation checks."
                )
            
            outcome = "success"
            row_count = len(queries)
            if total_count_from_sql > 0:
                self._last_total_count = int(total_count_from_sql)
            else:
                self._last_total_count = max(self._last_total_count, len(queries))
            logger.info(f"Found {len(queries)} queries")
            cache_key = self._make_top_queries_cache_key(
                filter,
                use_qs,
                include_sensitive_data=include_sensitive_data,
            )
            self._set_cached_top_queries(
                cache_key,
                queries,
                self.get_runtime_warnings(),
                int(self._last_total_count or len(queries)),
            )
            return queries
        except Exception as e:
            error_type = self.classify_error_type(e)
            if error_type == "cancelled":
                outcome = "cancelled"
            self._log_structured(
                logging.ERROR,
                "query_stats_unhandled_error",
                correlation_id=corr,
                error_type=error_type,
                error_message=str(e),
                connection=self._get_connection_context(),
                stack_trace=traceback.format_exc(),
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - load_start) * 1000.0, 2)
            self._record_load_outcome(duration_ms, outcome)
            self._log_structured(
                logging.INFO if outcome == "success" else logging.WARNING,
                "query_stats_load_complete",
                correlation_id=corr,
                outcome=outcome,
                duration_ms=duration_ms,
                row_count=row_count,
                error_type=error_type,
                warnings=self.get_runtime_warnings(),
                metrics=self.get_observability_metrics(),
            )
    
    def _row_to_query_stats(
        self,
        row: Dict[str, Any],
        is_query_store: bool,
        include_sensitive_data: bool = False,
    ) -> QueryStats:
        """
        Veritabanı satırını QueryStats modeline dönüştür
        """
        metrics = QueryMetrics(
            avg_duration_ms=float(row.get('avg_duration_ms', 0) or 0),
            max_duration_ms=float(row.get('max_duration_ms', 0) or 0),
            avg_cpu_ms=float(row.get('avg_cpu_ms', 0) or 0),
            avg_logical_reads=float(row.get('avg_logical_reads', 0) or 0),
            avg_logical_writes=float(row.get('avg_logical_writes', 0) or 0),
            avg_physical_reads=float(row.get('avg_physical_reads', 0) or 0),
            total_executions=int(row.get('total_executions', 0) or 0),
            plan_count=int(row.get('plan_count', 1) or 1),
            impact_score=float(row.get('impact_score', 0) or 0),
        )
        
        # query_id kontrolü - DMV'de olmayabilir
        query_id = row.get('query_id')
        if query_id is None:
            # DMV sonucu için query_hash'ten basit bir ID oluştur
            query_hash = str(row.get('query_hash', ''))
            query_id = hash(query_hash) % 1000000
        
        return QueryStats(
            query_id=int(query_id),
            query_hash=str(row.get('query_hash', '') or ''),
            query_text=self._sanitize_query_text(
                row.get('query_text', ''),
                f"query_id={int(query_id or 0)}",
                include_sensitive_data=include_sensitive_data,
            ),
            object_name=row.get('object_name'),
            schema_name=row.get('schema_name'),
            metrics=metrics,
            last_execution=row.get('last_execution'),
        )
    
    # ==========================================================================
    # SORGU DETAYI
    # ==========================================================================
    
    def get_query_detail(
        self,
        query_id: int,
        days: int = 7,
        include_sensitive_data: bool = False,
    ) -> Optional[QueryStats]:
        """
        Sorgu detayını getir
        
        Args:
            query_id: Sorgu ID
            days: Kaç günlük veri
        
        Returns:
            Detaylı QueryStats veya None
        """
        if not self.is_connected:
            return None
        
        if not self.use_query_store():
            logger.warning("Query Store not available for detail view")
            return None
        
        try:
            # Temel bilgileri al
            detail_result = self._execute_query_with_retry(
                QueryStoreQueries.QUERY_DETAIL,
                {"query_id": query_id},
                operation_name="get_query_detail",
            )
            
            if not detail_result:
                return None
            
            row = detail_result[0]
            
            # QueryStats oluştur
            query_stats = QueryStats(
                query_id=query_id,
                query_hash=str(row.get('query_hash', '') or ''),
                query_text=self._sanitize_query_text(
                    row.get('query_text', ''),
                    f"query_id={int(query_id or 0)}",
                    include_sensitive_data=include_sensitive_data,
                ),
                object_name=row.get('object_name'),
                schema_name=row.get('schema_name'),
                first_compile_time=row.get('initial_compile_start_time'),
                last_compile_time=row.get('last_compile_start_time'),
                last_execution=row.get('last_execution_time'),
            )
            
            # Metrikleri al (ayrı sorgu ile)
            query_stats.metrics = self._get_query_metrics(query_id, days)
            
            # Wait profile'ı al
            query_stats.wait_profile = self.get_query_wait_stats(query_id, days)
            
            # Plan bilgilerini al
            query_stats.plans = self.get_query_plans(query_id, days)
            
            # Trend verilerini al
            query_stats.daily_trend = self.get_query_trend(query_id, days)
            
            # Trend katsayısını hesapla
            trend_info = self._get_trend_coefficient(query_id)
            if trend_info:
                query_stats.metrics.trend_coefficient = trend_info[0]
                query_stats.metrics.change_percent = trend_info[1]
            
            # Impact score'u yeniden hesapla
            query_stats.metrics.calculate_impact_score()
            
            return query_stats
            
        except Exception as e:
            logger.error(f"Failed to get query detail for {query_id}: {e}")
            return None
    
    def _get_query_metrics(self, query_id: int, days: int) -> QueryMetrics:
        """Sorgu metriklerini al"""
        # TOP_QUERIES sorgusunu tek sorgu için kullan
        sql = """
        SELECT 
            COUNT(DISTINCT p.plan_id) AS plan_count,
            SUM(rs.count_executions) AS total_executions,
            AVG(rs.avg_duration) / 1000.0 AS avg_duration_ms,
            AVG(rs.avg_cpu_time) / 1000.0 AS avg_cpu_ms,
            AVG(rs.avg_logical_io_reads) AS avg_logical_reads,
            AVG(rs.avg_logical_io_writes) AS avg_logical_writes,
            AVG(rs.avg_physical_io_reads) AS avg_physical_reads,
            MAX(rs.max_duration) / 1000.0 AS max_duration_ms
        FROM sys.query_store_query q
        JOIN sys.query_store_plan p ON q.query_id = p.query_id
        JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
        JOIN sys.query_store_runtime_stats_interval rsi 
            ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
        WHERE q.query_id = :query_id
          AND rsi.start_time > DATEADD(day, -:days, GETDATE())
        """
        
        try:
            results = self._execute_query_with_retry(
                sql,
                {"query_id": query_id, "days": days},
                operation_name="get_query_metrics",
            )
            
            if not results:
                return QueryMetrics()
            
            row = results[0]
            row_id = f"query_id={int(query_id or 0)}"
            return QueryMetrics(
                avg_duration_ms=self._to_non_negative_float(row.get('avg_duration_ms', 0), "avg_duration_ms", row_id),
                max_duration_ms=self._to_non_negative_float(row.get('max_duration_ms', 0), "max_duration_ms", row_id),
                avg_cpu_ms=self._to_non_negative_float(row.get('avg_cpu_ms', 0), "avg_cpu_ms", row_id),
                avg_logical_reads=self._to_non_negative_float(row.get('avg_logical_reads', 0), "avg_logical_reads", row_id),
                avg_logical_writes=self._to_non_negative_float(row.get('avg_logical_writes', 0), "avg_logical_writes", row_id),
                avg_physical_reads=self._to_non_negative_float(row.get('avg_physical_reads', 0), "avg_physical_reads", row_id),
                total_executions=self._to_positive_int(row.get('total_executions', 0), "total_executions", row_id),
                plan_count=max(1, self._to_positive_int(row.get('plan_count', 1), "plan_count", row_id)),
            )
            
        except Exception as e:
            logger.error(f"Failed to get metrics for query {query_id}: {e}")
            return QueryMetrics()
    
    # ==========================================================================
    # WAIT STATS
    # ==========================================================================
    
    def get_query_wait_stats(self, query_id: int, days: int = 7) -> List[WaitProfile]:
        """
        Sorgu bazlı wait istatistiklerini getir
        
        Args:
            query_id: Sorgu ID
            days: Kaç günlük veri
        
        Returns:
            WaitProfile listesi
        """
        if not self.is_connected:
            return []
        
        # SQL 2017+ gerekli
        if not self._supports_query_store_wait_stats():
            logger.info("Query Store Wait Stats requires SQL Server 2017+")
            return self._get_server_wait_stats()
        
        try:
            results = self._execute_query_with_retry(
                QueryStoreQueries.QUERY_WAIT_STATS,
                {"query_id": query_id, "days": days},
                operation_name="get_query_wait_stats",
            )
            
            waits = []
            for row in results:
                waits.append(WaitProfile(
                    category=str(row.get('wait_category', 'Unknown') or 'Unknown'),
                    total_wait_ms=float(row.get('total_wait_ms', 0) or 0),
                    wait_percent=float(row.get('wait_percent', 0) or 0),
                ))
            
            return waits
            
        except Exception as e:
            logger.error(f"Failed to get wait stats for query {query_id}: {e}")
            return []
    
    def _get_server_wait_stats(self) -> List[WaitProfile]:
        """Sunucu geneli wait stats (fallback)"""
        if not self.is_connected:
            return []
        
        try:
            results = self._execute_query_with_retry(
                QueryStoreQueries.DMV_WAIT_STATS,
                operation_name="get_server_wait_stats",
            )
            
            waits = []
            for row in results:
                waits.append(WaitProfile(
                    category=str(row.get('wait_category', 'Unknown') or 'Unknown'),
                    total_wait_ms=float(row.get('total_wait_ms', 0) or 0),
                    wait_percent=float(row.get('wait_percent', 0) or 0),
                ))
            
            return waits
            
        except Exception as e:
            logger.error(f"Failed to get server wait stats: {e}")
            return []
    
    # ==========================================================================
    # PLAN STABILITY
    # ==========================================================================
    
    def get_query_plans(self, query_id: int, days: int = 7) -> List[PlanInfo]:
        """
        Sorgunun execution plan'larını getir
        
        Args:
            query_id: Sorgu ID
            days: Kaç günlük veri
        
        Returns:
            PlanInfo listesi
        """
        if not self.is_connected or not self.use_query_store():
            return []
        
        try:
            results = self._execute_query_with_retry(
                QueryStoreQueries.QUERY_PLAN_STABILITY,
                {"query_id": query_id, "days": days},
                operation_name="get_query_plans",
            )
            
            plans = []
            for row in results:
                plans.append(PlanInfo(
                    plan_id=int(row.get('plan_id', 0) or 0),
                    plan_hash=str(row.get('query_plan_hash', '') or ''),
                    is_forced=bool(row.get('is_forced_plan', False)),
                    force_failure_count=int(row.get('force_failure_count', 0) or 0),
                    first_seen=row.get('first_seen'),
                    last_seen=row.get('last_seen'),
                    execution_count=int(row.get('execution_count', 0) or 0),
                    avg_duration_ms=float(row.get('avg_duration_ms', 0) or 0),
                    stdev_duration_ms=float(row.get('stdev_duration_ms', 0) or 0),
                ))
            
            return plans
            
        except Exception as e:
            logger.error(f"Failed to get plans for query {query_id}: {e}")
            return []
    
    # ==========================================================================
    # TREND ANALİZİ
    # ==========================================================================
    
    def get_query_trend(self, query_id: int, days: int = 7) -> List[TrendData]:
        """
        Sorgunun günlük trend verisini getir
        
        Args:
            query_id: Sorgu ID
            days: Kaç günlük veri
        
        Returns:
            TrendData listesi
        """
        if not self.is_connected or not self.use_query_store():
            return []
        
        try:
            results = self._execute_query_with_retry(
                QueryStoreQueries.QUERY_DAILY_TREND,
                {"query_id": query_id, "days": days},
                operation_name="get_query_trend",
            )
            
            trends = []
            for row in results:
                trends.append(TrendData(
                    date=row.get('trend_date'),
                    executions=int(row.get('daily_executions', 0) or 0),
                    avg_duration_ms=float(row.get('avg_duration_ms', 0) or 0),
                    avg_cpu_ms=float(row.get('avg_cpu_ms', 0) or 0),
                    avg_logical_reads=float(row.get('avg_logical_reads', 0) or 0),
                ))
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get trend for query {query_id}: {e}")
            return []
    
    def _get_trend_coefficient(self, query_id: int) -> Optional[Tuple[float, float]]:
        """
        Trend katsayısını hesapla
        
        Returns:
            (trend_coefficient, change_percent) tuple veya None
        """
        if not self.is_connected or not self.use_query_store():
            return None
        
        try:
            results = self._execute_query_with_retry(
                QueryStoreQueries.QUERY_TREND_COMPARISON,
                {"query_id": query_id},
                operation_name="get_trend_coefficient",
            )
            
            if not results:
                return None
            
            row = results[0]
            trend_coef = float(row.get('trend_coefficient', 1.0) or 1.0)
            change_pct = float(row.get('change_percent', 0) or 0)
            
            return (trend_coef, change_pct)
            
        except Exception as e:
            logger.error(f"Failed to get trend coefficient for query {query_id}: {e}")
            return None
    
    # ==========================================================================
    # QUERY TEXT
    # ==========================================================================
    
    def get_query_text(self, query_id: int, include_sensitive_data: bool = False) -> Optional[str]:
        """
        Sorgu için SQL metnini getir
        
        Args:
            query_id: Sorgu ID
        
        Returns:
            SQL text string veya None
        """
        if not self.is_connected:
            return None
        
        if not self.use_query_store():
            return None
        
        try:
            results = self._execute_query_with_retry(
                QueryStoreQueries.QUERY_DETAIL,
                {"query_id": query_id},
                operation_name="get_query_text",
            )
            
            if not results:
                return None
            
            row = results[0]
            query_text = row.get('query_text')
            return query_text
            
        except Exception as e:
            logger.error(f"Failed to get query text for query {query_id}: {e}")
            return None

    def get_object_definition(
        self,
        object_name: str,
        schema_name: Optional[str] = None,
        include_sensitive_data: bool = False,
    ) -> Optional[str]:
        """
        Nesne (SP/Function/View) definition'ını getir.

        Args:
            object_name: Nesne adı
            schema_name: Şema adı (opsiyonel)

        Returns:
            SQL definition string veya None
        """
        if not self.is_connected or not object_name:
            return None

        try:
            if schema_name is None and "." in object_name:
                parts = object_name.split(".", 1)
                if len(parts) == 2:
                    schema_name, object_name = parts[0], parts[1]

            query = """
            SELECT sm.definition
            FROM sys.sql_modules sm
            JOIN sys.objects o ON sm.object_id = o.object_id
            WHERE o.name = :object_name
              AND (:schema_name IS NULL OR SCHEMA_NAME(o.schema_id) = :schema_name)
            """
            results = self._execute_query_with_retry(
                query,
                {"object_name": object_name, "schema_name": schema_name},
                operation_name="get_object_definition",
            )
            if not results:
                return None
            definition = results[0].get('definition')
            return definition
        except Exception as e:
            logger.error(f"Failed to get object definition for {schema_name}.{object_name}: {e}")
            return None
    
    # ==========================================================================
    # EXECUTION PLAN
    # ==========================================================================
    
    def get_query_plan_xml(
        self,
        query_id: int,
        query_hash: Optional[str] = None,
        include_sensitive_data: bool = False,
    ) -> Optional[str]:
        """
        Sorgu için execution plan XML'ini getir
        
        Args:
            query_id: Sorgu ID
        
        Returns:
            Plan XML string veya None
        """
        if not self.is_connected:
            logger.debug("Not connected, cannot get plan XML")
            return None
        
        if not self.use_query_store():
            logger.info("Query Store not available for plan XML")
            return None
        
        try:
            cached_xml = self._get_cached_plan_xml(query_id, query_hash=query_hash)
            if cached_xml:
                logger.debug(f"Plan XML cache hit for query_id: {query_id}")
                return cached_xml if include_sensitive_data else self.sanitize_plan_xml(cached_xml)

            logger.debug(f"Fetching plan XML for query_id: {query_id}")
            results = self._execute_query_with_retry(
                QueryStoreQueries.QUERY_PLAN_XML,
                {"query_id": query_id},
                operation_name="get_query_plan_xml",
            )
            
            if not results:
                logger.debug(f"No plan found for query_id: {query_id}")
                return None
            
            # En çok kullanılan planı döndür
            row = results[0]
            plan_xml = row.get('query_plan_xml')
            plan_id = row.get("plan_id")
            if "plan_handle" in row and row.get("plan_handle") is None:
                self._add_warning(f"Missing plan_handle for query {int(query_id)} plan fetch request.")
            if plan_id is None:
                self._add_warning(f"Plan metadata missing for query {int(query_id)}; plan cannot be loaded.")
                logger.warning(f"Plan fetch skipped due to missing plan_id [query_id={int(query_id)}]")
                return None
            if plan_xml:
                if not self._validate_plan_xml_well_formed(
                    str(plan_xml),
                    query_id=int(query_id),
                    plan_id=int(plan_id or 0),
                ):
                    return None
                plan_hash = row.get('query_plan_hash')
                effective_query_hash = str(query_hash or row.get('query_hash') or "")
                self._set_cached_plan_xml(
                    query_id=int(query_id),
                    query_hash=effective_query_hash,
                    plan_hash=str(plan_hash or ""),
                    plan_xml=str(plan_xml),
                )
                logger.debug(f"Got plan XML for query_id {query_id}: {len(plan_xml)} chars")
            if not include_sensitive_data:
                return self.sanitize_plan_xml(plan_xml)
            return plan_xml
            
        except Exception as e:
            logger.error(f"Failed to get plan XML for query {query_id}: {e}")
            return None
    
    def get_plan_xml_by_id(self, plan_id: int, include_sensitive_data: bool = False) -> Optional[str]:
        """
        Plan ID ile execution plan XML'ini getir
        
        Args:
            plan_id: Plan ID
        
        Returns:
            Plan XML string veya None
        """
        if not self.is_connected or not self.use_query_store():
            return None
        
        try:
            results = self._execute_query_with_retry(
                QueryStoreQueries.SINGLE_PLAN_XML,
                {"plan_id": plan_id},
                operation_name="get_plan_xml_by_id",
            )
            
            if not results:
                return None
            
            row = results[0]
            plan_xml = row.get('query_plan_xml')
            if not plan_xml:
                return None
            if not self._validate_plan_xml_well_formed(
                str(plan_xml),
                query_id=int(row.get("query_id", 0) or 0),
                plan_id=int(plan_id or 0),
            ):
                return None
            if not include_sensitive_data:
                return self.sanitize_plan_xml(plan_xml)
            return plan_xml
            
        except Exception as e:
            logger.error(f"Failed to get plan XML for plan {plan_id}: {e}")
            return None

    # ==========================================================================
    # CROSS-MODULE CONTEXT
    # ==========================================================================

    def build_analysis_context(
        self,
        query: QueryStats,
        target_module: str = "",
        reason: str = "",
    ):
        """
        Build shared AnalysisContext from a query row/detail object.
        """
        from app.models.analysis_context import AnalysisContext

        conn = self.connection
        db_name = ""
        if conn and getattr(conn, "profile", None):
            db_name = str(getattr(conn.profile, "database", "") or "")
        if not db_name and conn and getattr(conn, "info", None):
            db_name = str(getattr(conn.info, "database_name", "") or "")

        plan_hash = ""
        plans = getattr(query, "plans", []) or []
        if plans:
            plan_hash = str(getattr(plans[0], "plan_hash", "") or "")

        return AnalysisContext(
            query_id=int(getattr(query, "query_id", 0) or 0),
            query_hash=str(getattr(query, "query_hash", "") or ""),
            plan_hash=plan_hash,
            database_name=db_name,
            object_name=str(getattr(query, "object_name", "") or ""),
            schema_name=getattr(query, "schema_name", None),
            source_module="query_stats",
            target_module=str(target_module or ""),
            metadata={"reason": str(reason or "")},
        )

    def emit_context(self, context) -> int:
        """
        Publish AnalysisContext to shared message bus.
        """
        from app.services.analysis_message_bus import get_analysis_message_bus

        delivered = get_analysis_message_bus().publish(context)
        logger.info(
            "Analysis context published "
            f"[target={getattr(context, 'target_module', '')}, delivered={delivered}]"
        )
        return delivered
    
    # ==========================================================================
    # REFRESH / CACHE
    # ==========================================================================
    
    def refresh(self, force_refresh: bool = True) -> None:
        """Cache'i temizle ve durumu yeniden kontrol et"""
        self._invalidate_runtime_cache()
        if force_refresh:
            self.invalidate_connection_cache(clear_sql_version=False)
        self.check_query_store_status(force_refresh=force_refresh)
