"""
Index Advisor View - Deterministic index analysis with structured AI handoff.
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import json
from PyQt6.QtWidgets import (
    QLabel, QVBoxLayout, QHBoxLayout, QWidget, QTableWidget, 
    QTableWidgetItem, QHeaderView, QFrame, QGraphicsDropShadowEffect,
    QPushButton, QSplitter, QTextEdit, QDialog, QScrollArea,
    QAbstractItemView, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QAction

from app.ui.views.base_view import BaseView
from app.ui.theme import Colors, CircleStatCard
from app.database.connection import get_connection_manager
from app.core.logger import get_logger

logger = get_logger("ui.index_advisor")


# Classification thresholds (PART 1)
MIN_SEEKS_EFFECTIVE = 100
MIN_READ_WRITE_RATIO_EFFECTIVE = 3.0
MAX_FRAGMENTATION_EFFECTIVE = 10.0
MAX_KEY_BYTES_EFFECTIVE = 450

MAX_READS_WEAK = 100
MIN_SEEKS_WEAK = 1

MIN_FRAGMENTATION_MAINTENANCE = 10.0
MAX_PAGE_SPACE_USED_MAINTENANCE = 60.0
MAX_STATS_AGE_DAYS = 30
MAX_PAGE_LOCK_WAIT_MS = 1000

MIN_UNUSED_INDEX_AGE_DAYS = 90
MIN_INDEX_SCORE_EFFECTIVE = 75
MIN_INDEX_SCORE_WEAK = 50
MIN_INDEX_SCORE_MAINTENANCE = 25
MIN_SCAN_DOMINANT_READS_WEAK = 50
MAX_READ_WRITE_RATIO_UNNECESSARY = 0.2
MIN_WRITES_UNNECESSARY = 100

# Composite scoring (PART 3)
BASE_SCORE = 50
HIGH_USAGE_SEEKS_THRESHOLD = 1000
MID_USAGE_SEEKS_THRESHOLD = 100

RATIO_EXCELLENT = 10.0
RATIO_GOOD = 5.0
RATIO_MIN_EFFECTIVE = 3.0
RATIO_WRITE_HEAVY = 1.0

FRAGMENTATION_HIGH = 30.0
FRAGMENTATION_MEDIUM = 10.0
SELECTIVITY_LOW = 0.01
LOW_FRAGMENTATION_THRESHOLD = 5.0
HIGH_SELECTIVITY_THRESHOLD = 0.5
WIDE_INDEX_KEY_BYTES = 900

# Special cases (PART 8)
MIN_FK_INDEX_SCORE = 50
SMALL_TABLE_ROW_THRESHOLD = 1000
SMALL_TABLE_PENALTY = 10
FILTERED_INDEX_EFFECTIVE_SEEKS = 10
COLUMNSTORE_OPEN_ROWGROUP_WARNING_THRESHOLD = 5

# Display / query limits
MAX_INDEX_ROWS = 200


class DuplicateType(str, Enum):
    NOT_DUPLICATE = "NotDuplicate"
    EXACT_DUPLICATE = "ExactDuplicate"
    REDUNDANT_SUBSET = "RedundantSubset"
    LEFTMOST_PREFIX = "LeftmostPrefix"


@dataclass
class IndexColumnMeta:
    name: str
    is_nullable: bool
    is_fixed_length: bool
    data_type: str


class IndexAnalyzer:
    """Deterministic index analyzer based on .cursorrules_index INDEX ANALYSIS RULES."""

    @staticmethod
    def _split_columns(value: str) -> List[str]:
        if not value:
            return []
        cols = []
        for c in str(value).split(","):
            cleaned = c.strip()
            if cleaned:
                cols.append(cleaned)
        return cols

    @staticmethod
    def calculate_read_write_ratio(index_data: Dict[str, Any]) -> float:
        reads = (
            int(index_data.get("user_seeks", 0) or 0) +
            int(index_data.get("user_scans", 0) or 0) +
            int(index_data.get("user_lookups", 0) or 0)
        )
        writes = int(index_data.get("user_updates", 0) or 0)
        return float(reads) if writes == 0 else float(reads) / float(writes)

    @staticmethod
    def calculate_selectivity(distinct_values: int, total_rows: int) -> float:
        return 0.0 if total_rows == 0 else float(distinct_values) / float(total_rows)

    @staticmethod
    def calculate_key_length_score(total_key_bytes: int) -> int:
        if total_key_bytes <= 100:
            return 10
        if total_key_bytes <= 450:
            return 5
        if total_key_bytes <= 900:
            return 2
        return 0

    @staticmethod
    def calculate_column_score(col: IndexColumnMeta) -> int:
        score = 0
        if not col.is_nullable:
            score += 2
        if col.is_fixed_length:
            score += 1
        if col.data_type in {"int", "bigint", "datetime2"}:
            score += 1
        return score

    def check_duplicate(self, idx1: Dict[str, Any], idx2: Dict[str, Any]) -> DuplicateType:
        keys1 = idx1.get("key_columns_list", [])
        keys2 = idx2.get("key_columns_list", [])
        inc1 = idx1.get("included_columns_list", [])
        inc2 = idx2.get("included_columns_list", [])

        if keys1 == keys2 and inc1 == inc2:
            return DuplicateType.EXACT_DUPLICATE

        if len(keys1) <= len(keys2) and keys2[:len(keys1)] == keys1:
            return DuplicateType.LEFTMOST_PREFIX

        if keys1 == keys2 and all(c in inc2 for c in inc1):
            return DuplicateType.REDUNDANT_SUBSET

        return DuplicateType.NOT_DUPLICATE

    def calculate_index_score(self, index: Dict[str, Any]) -> int:
        score = BASE_SCORE

        user_seeks = int(index.get("user_seeks", 0) or 0)
        if user_seeks >= HIGH_USAGE_SEEKS_THRESHOLD:
            score += 20
        elif user_seeks >= MID_USAGE_SEEKS_THRESHOLD:
            score += 10

        ratio = float(index.get("read_write_ratio", 0) or 0)
        if ratio >= RATIO_EXCELLENT:
            score += 20
        elif ratio >= RATIO_GOOD:
            score += 10
        elif ratio >= RATIO_MIN_EFFECTIVE:
            score += 5
        elif ratio < RATIO_WRITE_HEAVY:
            score -= 20

        key_bytes = int(index.get("key_column_total_bytes", 0) or 0)
        score += self.calculate_key_length_score(key_bytes)
        if bool(index.get("all_columns_not_null", False)):
            score += 5
        if bool(index.get("all_columns_fixed_length", False)):
            score += 5

        frag = float(index.get("avg_fragmentation_in_percent", 0) or 0)
        if frag >= FRAGMENTATION_HIGH:
            score -= 30
        elif frag >= FRAGMENTATION_MEDIUM:
            score -= 10

        if bool(index.get("is_duplicate", False)):
            score -= 40

        selectivity = float(index.get("selectivity_ratio", 0) or 0)
        is_filtered = bool(index.get("is_filtered", False))
        if selectivity < SELECTIVITY_LOW and not is_filtered:
            score -= 15

        return max(0, min(100, score))

    def classify(self, index: Dict[str, Any]) -> str:
        classification, _ = self._classify_with_reason(index)
        return classification

    def _classify_with_reason(self, index: Dict[str, Any]) -> tuple[str, str]:
        reads = (
            int(index.get("user_seeks", 0) or 0) +
            int(index.get("user_scans", 0) or 0) +
            int(index.get("user_lookups", 0) or 0)
        )
        seeks = int(index.get("user_seeks", 0) or 0)
        scans = int(index.get("user_scans", 0) or 0)
        ratio = float(index.get("read_write_ratio", 0) or 0)
        frag = float(index.get("avg_fragmentation_in_percent", 0) or 0)
        key_bytes = int(index.get("key_column_total_bytes", 0) or 0)
        page_space = float(index.get("avg_page_space_used_in_percent", 100) or 100)
        page_lock_wait = float(index.get("page_lock_wait_in_ms", 0) or 0)
        days_stats = int(index.get("days_since_last_stats_update", 0) or 0)
        days_since_create = int(index.get("days_since_create", 0) or 0)
        is_exact_dup = bool(index.get("is_exact_duplicate", False))
        is_leftmost_dup = bool(index.get("is_leftmost_duplicate", False))
        is_duplicate = bool(index.get("is_duplicate", False))
        updates = int(index.get("user_updates", 0) or 0)
        score = int(index.get("score", 0) or 0)

        if (
            is_exact_dup or
            is_leftmost_dup
        ):
            return "UNNECESSARY", "DUPLICATE_OR_LEFT_PREFIX"

        if reads == 0 and days_since_create > MIN_UNUSED_INDEX_AGE_DAYS:
            return "UNNECESSARY", "NO_READS_OVER_90_DAYS"

        if reads <= 5 and ratio <= MAX_READ_WRITE_RATIO_UNNECESSARY and updates >= MIN_WRITES_UNNECESSARY and not is_duplicate:
            return "UNNECESSARY", "WRITE_COST_OUTWEIGHS_READ_VALUE"

        if (
            frag >= MIN_FRAGMENTATION_MAINTENANCE or
            page_space < MAX_PAGE_SPACE_USED_MAINTENANCE or
            days_stats > MAX_STATS_AGE_DAYS or
            page_lock_wait > MAX_PAGE_LOCK_WAIT_MS
        ):
            return "NEEDS_MAINTENANCE", "FRAGMENTATION_OR_STATS_OR_CONTENTION"

        if scans >= MIN_SCAN_DOMINANT_READS_WEAK and seeks == 0 and not is_duplicate:
            return "WEAK", "SCAN_DOMINANT_ACCESS_PATTERN"

        if (
            seeks >= MIN_SEEKS_EFFECTIVE and
            ratio >= MIN_READ_WRITE_RATIO_EFFECTIVE and
            frag < MAX_FRAGMENTATION_EFFECTIVE and
            key_bytes <= MAX_KEY_BYTES_EFFECTIVE
        ):
            return "EFFECTIVE", "HIGH_USAGE_BALANCED_AND_HEALTHY"

        if (
            ((seeks + scans) < MAX_READS_WEAK or ratio < MIN_READ_WRITE_RATIO_EFFECTIVE) and
            seeks >= MIN_SEEKS_WEAK and
            not is_duplicate
        ):
            return "WEAK", "LOW_USAGE_OR_LOW_RATIO"

        if score >= MIN_INDEX_SCORE_EFFECTIVE:
            return "EFFECTIVE", "SCORE_BASED_EFFECTIVE"
        if score >= MIN_INDEX_SCORE_WEAK:
            return "WEAK", "SCORE_BASED_WEAK"
        if score >= MIN_INDEX_SCORE_MAINTENANCE:
            return "NEEDS_MAINTENANCE", "SCORE_BASED_MAINTENANCE"
        return "UNNECESSARY", "SCORE_BASED_UNNECESSARY"

    @staticmethod
    def generate_flags(index: Dict[str, Any]) -> List[str]:
        flags: List[str] = []

        ratio = float(index.get("read_write_ratio", 0) or 0)
        frag = float(index.get("avg_fragmentation_in_percent", 0) or 0)
        selectivity = float(index.get("selectivity_ratio", 0) or 0)
        key_bytes = int(index.get("key_column_total_bytes", 0) or 0)
        seeks = int(index.get("user_seeks", 0) or 0)
        scans = int(index.get("user_scans", 0) or 0)
        days_stats = int(index.get("days_since_last_stats_update", 0) or 0)

        if ratio >= 10:
            flags.append("EXCELLENT_READ_WRITE_RATIO")
        if frag < LOW_FRAGMENTATION_THRESHOLD:
            flags.append("LOW_FRAGMENTATION")
        if selectivity >= HIGH_SELECTIVITY_THRESHOLD:
            flags.append("HIGH_SELECTIVITY")
        if key_bytes <= 100:
            flags.append("NARROW_INDEX")
        if bool(index.get("all_columns_not_null", False)):
            flags.append("NO_NULLABLE_COLUMNS")
        if seeks >= HIGH_USAGE_SEEKS_THRESHOLD:
            flags.append("HIGH_USAGE")

        if ratio < 1:
            flags.append("WRITE_HEAVY")
        if frag >= FRAGMENTATION_HIGH:
            flags.append("HIGHLY_FRAGMENTED")
        if selectivity < SELECTIVITY_LOW:
            flags.append("LOW_SELECTIVITY")
        if key_bytes > WIDE_INDEX_KEY_BYTES:
            flags.append("WIDE_INDEX")
        if days_stats > MAX_STATS_AGE_DAYS:
            flags.append("STALE_STATISTICS")
        if seeks == 0 and scans == 0:
            flags.append("ZERO_READS")

        return flags

    @staticmethod
    def _generate_warnings(index: Dict[str, Any]) -> List[str]:
        warnings: List[str] = []
        duplicate_type = index.get("duplicate_type", DuplicateType.NOT_DUPLICATE.value)
        if duplicate_type == DuplicateType.EXACT_DUPLICATE.value:
            warnings.append("EXACT_DUPLICATE_INDEX")
        elif duplicate_type == DuplicateType.LEFTMOST_PREFIX.value:
            warnings.append("LEFTMOST_PREFIX_DUPLICATE")
        elif duplicate_type == DuplicateType.REDUNDANT_SUBSET.value:
            warnings.append("REDUNDANT_SUBSET_DUPLICATE")

        if float(index.get("avg_fragmentation_in_percent", 0) or 0) >= 30:
            warnings.append("REBUILD_RECOMMENDED")
        if int(index.get("days_since_last_stats_update", 0) or 0) > MAX_STATS_AGE_DAYS:
            warnings.append("UPDATE_STATISTICS_RECOMMENDED")
        if int(index.get("table_rows", 0) or 0) < SMALL_TABLE_ROW_THRESHOLD and str(index.get("type_desc", "")).upper() != "CLUSTERED":
            warnings.append("INDEX_ON_SMALL_TABLE")
        return warnings

    @staticmethod
    def _generate_recommendations(index: Dict[str, Any]) -> List[str]:
        recs: List[str] = []
        cls = index.get("classification", "")
        if cls in {"UNNECESSARY"}:
            recs.append("DROP_OR_DISABLE_CANDIDATE")
        if cls in {"NEEDS_MAINTENANCE"}:
            frag = float(index.get("avg_fragmentation_in_percent", 0) or 0)
            if frag >= FRAGMENTATION_HIGH:
                recs.append("ALTER_INDEX_REBUILD")
            elif frag >= FRAGMENTATION_MEDIUM:
                recs.append("ALTER_INDEX_REORGANIZE")
        if "STALE_STATISTICS" in index.get("flags", []):
            recs.append("UPDATE_STATISTICS_WITH_FULLSCAN_REVIEW")
        if "WRITE_HEAVY" in index.get("flags", []):
            recs.append("REVIEW_WRITE_OVERHEAD")
        if "LOW_SELECTIVITY" in index.get("flags", []):
            recs.append("REVIEW_LEADING_COLUMN_SELECTIVITY")
        if not recs:
            recs.append("MONITOR_AND_KEEP")
        return recs

    @staticmethod
    def _to_bool(value: Any) -> bool:
        return bool(int(value)) if isinstance(value, (int, float)) else bool(value)

    def apply_special_case_rules(self, index: Dict[str, Any]) -> None:
        if self._to_bool(index.get("is_primary_key")) or self._to_bool(index.get("is_unique_constraint")):
            index["classification"] = "EFFECTIVE_MANDATORY"
            index["classification_reason"] = "MANDATORY_PK_OR_UNIQUE_CONSTRAINT"
            index["score"] = 100
            index.setdefault("flags", []).append("MANDATORY_CONSTRAINT")
            return

        if self._to_bool(index.get("supports_fk")) and int(index.get("user_seeks", 0) or 0) == 0:
            index["classification"] = "WEAK_BUT_NECESSARY_FK"
            index["classification_reason"] = "FK_SUPPORT_WITH_LOW_DIRECT_USAGE"
            index["score"] = max(int(index.get("score", 0) or 0), MIN_FK_INDEX_SCORE)
            index.setdefault("flags", []).append("FK_SUPPORT_INDEX")

        if int(index.get("table_rows", 0) or 0) < SMALL_TABLE_ROW_THRESHOLD and str(index.get("type_desc", "")).upper() != "CLUSTERED":
            index.setdefault("warnings", []).append("INDEX_ON_SMALL_TABLE")
            index["score"] = max(0, int(index.get("score", 0) or 0) - SMALL_TABLE_PENALTY)

        if self._to_bool(index.get("is_filtered")) and int(index.get("user_seeks", 0) or 0) >= FILTERED_INDEX_EFFECTIVE_SEEKS:
            index.setdefault("flags", []).append("EFFECTIVE_FILTERED_INDEX")

        if str(index.get("type_desc", "")).upper() == "CLUSTERED COLUMNSTORE":
            open_rg = int(index.get("open_rowgroup_count", 0) or 0)
            if open_rg > COLUMNSTORE_OPEN_ROWGROUP_WARNING_THRESHOLD:
                index.setdefault("warnings", []).append("EXCESSIVE_DELTASTORE_ROWGROUPS")
                index["classification"] = "NEEDS_MAINTENANCE"
                index["classification_reason"] = "COLUMNSTORE_DELTASTORE_PRESSURE"

    @staticmethod
    def _classification_confidence(reason: str) -> str:
        reason_text = str(reason or "").upper()
        if reason_text.startswith("SCORE_BASED_"):
            return "MEDIUM"
        if not reason_text:
            return "LOW"
        return "HIGH"

    @staticmethod
    def _score_band(score: int) -> str:
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 50:
            return "C"
        if score >= 25:
            return "D"
        return "E"

    def analyze(self, raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for row in raw_rows:
            item = dict(row)
            item["table_name"] = str(item.get("table_name", "") or "")
            item["schema_name"] = str(item.get("schema_name", "") or "dbo")
            item["index_name"] = str(item.get("index_name", "") or "")
            item["key_columns_list"] = self._split_columns(item.get("key_columns", ""))
            item["included_columns_list"] = self._split_columns(item.get("included_columns", ""))
            item["read_write_ratio"] = self.calculate_read_write_ratio(item)
            hist_steps = int(item.get("histogram_steps", 0) or 0)
            table_rows = int(item.get("table_rows", 0) or 0)
            item["selectivity_ratio"] = self.calculate_selectivity(hist_steps, table_rows)
            item["days_since_last_stats_update"] = int(item.get("days_since_last_stats_update", 9999) or 9999)
            item["days_since_create"] = int(item.get("days_since_create", 0) or 0)
            item["is_filtered"] = self._to_bool(item.get("is_filtered", False))
            item["all_columns_not_null"] = self._to_bool(item.get("all_columns_not_null", False))
            item["all_columns_fixed_length"] = self._to_bool(item.get("all_columns_fixed_length", False))
            item["supports_fk"] = self._to_bool(item.get("supports_fk", False))
            item["is_primary_key"] = self._to_bool(item.get("is_primary_key", False))
            item["is_unique_constraint"] = self._to_bool(item.get("is_unique_constraint", False))
            normalized.append(item)

        self._apply_duplicate_detection(normalized)

        outputs: List[Dict[str, Any]] = []
        for item in normalized:
            item["score"] = self.calculate_index_score(item)
            classification, reason = self._classify_with_reason(item)
            item["classification"] = classification
            item["classification_reason"] = reason
            item["classification_confidence"] = self._classification_confidence(reason)
            item["score_band"] = self._score_band(int(item.get("score", 0) or 0))
            item["flags"] = self.generate_flags(item)
            item["warnings"] = self._generate_warnings(item)
            item["computed_recommendations"] = self._generate_recommendations(item)
            self.apply_special_case_rules(item)
            item["classification_confidence"] = self._classification_confidence(item.get("classification_reason", ""))
            item["score"] = max(0, min(100, int(item.get("score", 0) or 0)))
            item["score_band"] = self._score_band(int(item.get("score", 0) or 0))
            outputs.append(self._to_output(item))

        outputs.sort(key=lambda x: int(x.get("Score", 0)), reverse=True)
        return outputs

    def _apply_duplicate_detection(self, rows: List[Dict[str, Any]]) -> None:
        by_table: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            key = f"{row.get('schema_name', '')}.{row.get('table_name', '')}"
            by_table.setdefault(key, []).append(row)

        for table_rows in by_table.values():
            for row in table_rows:
                row["duplicate_type"] = DuplicateType.NOT_DUPLICATE.value
                row["is_duplicate"] = False
                row["is_exact_duplicate"] = False
                row["is_leftmost_duplicate"] = False

            for i, left in enumerate(table_rows):
                for j, right in enumerate(table_rows):
                    if i == j:
                        continue
                    dup_type = self.check_duplicate(left, right)
                    if dup_type != DuplicateType.NOT_DUPLICATE:
                        left["duplicate_type"] = dup_type.value
                        left["is_duplicate"] = True
                        left["is_exact_duplicate"] = dup_type == DuplicateType.EXACT_DUPLICATE
                        left["is_leftmost_duplicate"] = dup_type == DuplicateType.LEFTMOST_PREFIX
                        break

    @staticmethod
    def _to_output(item: Dict[str, Any]) -> Dict[str, Any]:
        table_name = f"{item.get('schema_name', 'dbo')}.{item.get('table_name', '')}"
        page_count = int(item.get("page_count", 0) or 0)
        size_mb = round((page_count * 8.0) / 1024.0, 2)
        return {
            "IndexName": item.get("index_name", ""),
            "TableName": table_name,
            "Classification": item.get("classification", "WEAK"),
            "ClassificationReason": item.get("classification_reason", ""),
            "ClassificationConfidence": item.get("classification_confidence", "LOW"),
            "ScoreBand": item.get("score_band", "E"),
            "Score": int(item.get("score", 0) or 0),
            "Metrics": {
                "UserSeeks": int(item.get("user_seeks", 0) or 0),
                "UserScans": int(item.get("user_scans", 0) or 0),
                "UserUpdates": int(item.get("user_updates", 0) or 0),
                "ReadWriteRatio": round(float(item.get("read_write_ratio", 0) or 0), 2),
                "FragmentationPercent": round(float(item.get("avg_fragmentation_in_percent", 0) or 0), 2),
                "PageCount": page_count,
                "SizeMB": size_mb,
                "SelectivityRatio": round(float(item.get("selectivity_ratio", 0) or 0), 4),
                "DaysSinceLastStatsUpdate": int(item.get("days_since_last_stats_update", 0) or 0),
            },
            "Properties": {
                "KeyColumns": item.get("key_columns_list", []),
                "IncludedColumns": item.get("included_columns_list", []),
                "KeyLengthBytes": int(item.get("key_column_total_bytes", 0) or 0),
                "IsUnique": bool(item.get("is_unique", False)),
                "IsFiltered": bool(item.get("is_filtered", False)),
                "FillFactor": int(item.get("fill_factor", 0) or 0),
                "IsPrimaryKey": bool(item.get("is_primary_key", False)),
                "SupportsFK": bool(item.get("supports_fk", False)),
            },
            "Flags": item.get("flags", []),
            "Warnings": item.get("warnings", []),
            "ComputedRecommendations": item.get("computed_recommendations", []),
            "Internal": {
                "SchemaName": item.get("schema_name", "dbo"),
                "TableObjectName": item.get("table_name", ""),
                "TypeDesc": item.get("type_desc", ""),
                "FilterDefinition": item.get("filter_definition", ""),
                "DuplicateType": item.get("duplicate_type", DuplicateType.NOT_DUPLICATE.value),
                "UserLookups": int(item.get("user_lookups", 0) or 0),
                "LastUserSeek": item.get("last_user_seek"),
                "LastUserScan": item.get("last_user_scan"),
                "LeafInsertCount": int(item.get("leaf_insert_count", 0) or 0),
                "LeafUpdateCount": int(item.get("leaf_update_count", 0) or 0),
                "LeafDeleteCount": int(item.get("leaf_delete_count", 0) or 0),
                "RangeScanCount": int(item.get("range_scan_count", 0) or 0),
                "SingletonLookupCount": int(item.get("singleton_lookup_count", 0) or 0),
                "PageLockWaitCount": int(item.get("page_lock_wait_count", 0) or 0),
                "PageLockWaitInMs": float(item.get("page_lock_wait_in_ms", 0) or 0),
                "PageIOLatchWaitCount": int(item.get("page_io_latch_wait_count", 0) or 0),
                "PageIOLatchWaitInMs": float(item.get("page_io_latch_wait_in_ms", 0) or 0),
                "RowLockWaitCount": int(item.get("row_lock_wait_count", 0) or 0),
                "RowLockWaitInMs": float(item.get("row_lock_wait_in_ms", 0) or 0),
                "AvgPageSpaceUsedInPercent": float(item.get("avg_page_space_used_in_percent", 0) or 0),
                "RecordCount": int(item.get("record_count", 0) or 0),
                "ForwardedRecordCount": int(item.get("forwarded_record_count", 0) or 0),
                "LastStatsUpdate": item.get("last_stats_update"),
                "ModificationCounter": int(item.get("modification_counter", 0) or 0),
                "RowsSampled": int(item.get("rows_sampled", 0) or 0),
                "TableRows": int(item.get("table_rows", 0) or 0),
                "AllColumnsNotNull": bool(item.get("all_columns_not_null", False)),
                "AllColumnsFixedLength": bool(item.get("all_columns_fixed_length", False)),
                "ClassificationReason": item.get("classification_reason", ""),
                "ClassificationConfidence": item.get("classification_confidence", "LOW"),
                "ScoreBand": item.get("score_band", "E"),
            },
        }


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
            system_prompt = (
                "You are analyzing PRE-CLASSIFIED index data. Each index has been scored (0-100) "
                "using deterministic rules. Your job is to:\n"
                "1. Explain WHY the classification was given (interpret flags/warnings)\n"
                "2. Provide actionable recommendations\n"
                "3. Prioritize by score (fix score <25 first)\n"
                "4. Keep all output strictly in English\n\n"
                "DO NOT re-classify indexes. Trust the computed scores and classifications."
            )

            user_payload = {
                "request_type": "index_analysis_preclassified",
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "index": self.index_data,
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
            return response
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
            "## 📊 Deterministic Index Analysis (Fallback)",
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
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_indexes: List[Dict] = []
        self._analyzer = IndexAnalyzer()
    
    @property
    def view_title(self) -> str:
        return "Index Advisor"
    
    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND};")
        
        # Title section
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(16)
        
        # Title and subtitle
        title_text_layout = QVBoxLayout()
        title_text_layout.setSpacing(4)
        
        title = QLabel("📊 Index Advisor")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title_text_layout.addWidget(title)
        
        self.status_label = QLabel("Connect to a database")
        self.status_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 14px; background: transparent;")
        self.status_label.setFont(QFont("Segoe UI", 13))
        title_text_layout.addWidget(self.status_label)
        
        title_layout.addLayout(title_text_layout)
        title_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        refresh_btn.clicked.connect(self.refresh)
        title_layout.addWidget(refresh_btn)
        
        self._main_layout.addWidget(title_container)
        self._main_layout.addSpacing(20)
        
        # Summary cards
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(16)
        
        self._total_card = self._create_summary_card("Total Indexes", "0", Colors.PRIMARY)
        self._high_impact_card = self._create_summary_card("Needs Action", "0", Colors.WARNING)
        self._estimated_gain_card = self._create_summary_card("Average Score", "0", Colors.SUCCESS)
        
        summary_layout.addWidget(self._total_card)
        summary_layout.addWidget(self._high_impact_card)
        summary_layout.addWidget(self._estimated_gain_card)
        summary_layout.addStretch()
        
        self._main_layout.addLayout(summary_layout)
        self._main_layout.addSpacing(20)
        
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
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.itemClicked.connect(self._on_index_selected)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.SURFACE};
                border: none;
                gridline-color: {Colors.BORDER};
                color: {Colors.TEXT_PRIMARY};
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.PRIMARY}18;
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
        detail_header = QLabel("📝 Index Details")
        detail_header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: 600;")
        detail_layout.addWidget(detail_header)
        
        # CREATE INDEX script
        script_label = QLabel("CREATE INDEX Script:")
        script_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 500;")
        detail_layout.addWidget(script_label)
        
        self._script_text = QTextEdit()
        self._script_text.setReadOnly(True)
        self._script_text.setPlaceholderText("Select an index...")
        self._script_text.setMaximumHeight(150)
        self._script_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1E293B;
                color: #E2E8F0;
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        detail_layout.addWidget(self._script_text)
        
        # Copy button
        copy_btn = QPushButton("📋 Copy Script")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #F1F5F9;
            }}
        """)
        copy_btn.clicked.connect(self._copy_script)
        detail_layout.addWidget(copy_btn)
        
        # AI Analysis section
        ai_header = QHBoxLayout()
        ai_label = QLabel("🤖 AI Analysis")
        ai_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 14px; font-weight: 600;")
        ai_header.addWidget(ai_label)
        
        self._ai_btn = QPushButton("Analyze")
        self._ai_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ai_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
        """)
        self._ai_btn.clicked.connect(self._run_ai_analysis)
        ai_header.addWidget(self._ai_btn)
        ai_header.addStretch()
        
        detail_layout.addLayout(ai_header)
        
        self._ai_result = QTextEdit()
        self._ai_result.setReadOnly(True)
        self._ai_result.setPlaceholderText("Select an index and click 'Analyze'...")
        self._ai_result.setStyleSheet(f"""
            QTextEdit {{
                background-color: #F8FAFC;
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }}
        """)
        detail_layout.addWidget(self._ai_result, 1)
        
        splitter.addWidget(detail_card)
        splitter.setSizes([600, 400])
        
        self._main_layout.addWidget(splitter, 1)
    
    def _create_summary_card(self, title: str, value: str, color: str) -> CircleStatCard:
        """Create a circle summary stat card - GUI-05 style"""
        return CircleStatCard(title, value, color)
    
    def _update_summary_card(self, card: CircleStatCard, value: str):
        """Update summary card value"""
        card.update_value(value)
    
    def on_show(self):
        if not self._is_initialized:
            return
        self.refresh()
        
    def refresh(self):
        if not self._is_initialized:
            return
        conn = get_connection_manager().active_connection
        if not conn or not conn.is_connected:
            self.status_label.setText("Please connect to a database first.")
            self.status_label.setStyleSheet(f"color: {Colors.WARNING}; font-size: 14px; background: transparent;")
            return
            
        self.status_label.setText(f"📊 Deterministic index analysis for {conn.profile.database}")
        self.status_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 14px; background: transparent;")
        
        try:
            try:
                results = conn.execute_query(self._build_index_collection_query())
            except Exception as ex:
                logger.warning(f"Primary index collection query failed, trying legacy fallback: {ex}")
                results = conn.execute_query(self._build_index_collection_query_legacy())
            analyzed = self._analyzer.analyze(results or [])

            self._current_indexes = analyzed
            self.table.setRowCount(len(analyzed))

            needs_action_count = 0
            total_score = 0

            self.table.setSortingEnabled(False)
            for i, idx_data in enumerate(analyzed):
                score = int(idx_data.get("Score", 0) or 0)
                metrics = idx_data.get("Metrics", {}) or {}
                props = idx_data.get("Properties", {}) or {}
                ratio = float(metrics.get("ReadWriteRatio", 0) or 0)
                frag = float(metrics.get("FragmentationPercent", 0) or 0)
                seeks = int(metrics.get("UserSeeks", 0) or 0)
                writes = int(metrics.get("UserUpdates", 0) or 0)
                classification = str(idx_data.get("Classification", "WEAK"))

                total_score += score
                if score < MIN_INDEX_SCORE_WEAK:
                    needs_action_count += 1

                table_item = QTableWidgetItem(str(idx_data.get("TableName", "")))
                index_item = QTableWidgetItem(str(idx_data.get("IndexName", "")))
                class_item = QTableWidgetItem(classification)
                score_item = NumericTableWidgetItem(f"{score}", float(score))
                ratio_item = NumericTableWidgetItem(f"{ratio:.2f}", float(ratio))
                frag_item = NumericTableWidgetItem(f"{frag:.2f}", float(frag))
                seeks_item = NumericTableWidgetItem(f"{seeks:,}", float(seeks))
                writes_item = NumericTableWidgetItem(f"{writes:,}", float(writes))

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

                key_cols = ", ".join(props.get("KeyColumns", [])[:2]) if isinstance(props.get("KeyColumns"), list) else ""
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

            self._update_summary_card(self._total_card, str(len(analyzed)))
            self._update_summary_card(self._high_impact_card, str(needs_action_count))
            avg_score = (total_score / len(analyzed)) if analyzed else 0
            self._update_summary_card(self._estimated_gain_card, f"{avg_score:.0f}")
            self.table.setSortingEnabled(True)
                
        except Exception as e:
            logger.error(f"Failed to load index analysis: {e}")
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 14px; background: transparent;")

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
        row = self.table.currentRow()
        if row < 0 or row >= len(self._current_indexes):
            return
        
        idx = self._current_indexes[row]
        script = self._generate_create_index_script(idx)
        self._script_text.setPlainText(script)
        self._ai_result.setMarkdown(self._build_deterministic_summary(idx))
    
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
        script = self._script_text.toPlainText()
        if script:
            QApplication.clipboard().setText(script)
    
    def _show_context_menu(self, position):
        """Show context menu"""
        row = self.table.currentRow()
        if row < 0:
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
                padding: 10px 20px;
                color: {Colors.TEXT_PRIMARY};
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {Colors.PRIMARY};
                color: white;
            }}
        """)
        
        copy_action = QAction("📋 Copy Script", self)
        copy_action.triggered.connect(self._copy_script)
        menu.addAction(copy_action)
        
        ai_action = QAction("🤖 Analyze with AI", self)
        ai_action.triggered.connect(self._run_ai_analysis)
        menu.addAction(ai_action)
        
        menu.exec(self.table.mapToGlobal(position))
    
    def _run_ai_analysis(self):
        """Run AI analysis on selected index"""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._current_indexes):
            self._ai_result.setMarkdown("⚠️ Please select an index first.")
            return
        
        idx = self._current_indexes[row]
        self._ai_btn.setEnabled(False)
        self._ai_result.setMarkdown("⏳ Preparing AI analysis with deterministic scoring...")
        
        self._worker = IndexAnalysisWorker(idx)
        self._worker.finished.connect(self._on_ai_finished)
        self._worker.error.connect(self._on_ai_error)
        self._worker.start()
    
    def _on_ai_finished(self, result: str):
        """Handle AI analysis completion"""
        self._ai_result.setMarkdown(result)
        self._ai_btn.setEnabled(True)
    
    def _on_ai_error(self, error: str):
        """Handle AI analysis error"""
        self._ai_result.setMarkdown(f"⚠️ Error: {error}")
        self._ai_btn.setEnabled(True)

    @staticmethod
    def _build_deterministic_summary(idx: Dict[str, Any]) -> str:
        metrics = idx.get("Metrics", {}) or {}
        flags = idx.get("Flags", []) or []
        warnings = idx.get("Warnings", []) or []
        recs = idx.get("ComputedRecommendations", []) or []
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
        return "\n".join(lines)
