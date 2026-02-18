"""
Execution Plan XML Parser

SQL Server execution plan XML'ini parse ederek operatör ağacını oluşturur.
SSMS tarzı görselleştirme için gerekli verileri çıkarır.

Desteklenen Plan Formatları:
- Query Store (sys.query_store_plan.query_plan)
- DMV (sys.dm_exec_query_plan)
- SHOWPLAN XML

Referans: https://docs.microsoft.com/en-us/sql/relational-databases/showplan-logical-and-physical-operators-reference
"""

import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any, Tuple
import copy
import hashlib
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from threading import Lock

from app.core.logger import get_logger

logger = get_logger('analysis.plan_parser')

# SQL Server Showplan XML namespace
SHOWPLAN_NS = {
    'sp': 'http://schemas.microsoft.com/sqlserver/2004/07/showplan'
}


class OperatorType(str, Enum):
    """Plan operatör tipleri"""
    # Scan operatörleri
    TABLE_SCAN = "Table Scan"
    CLUSTERED_INDEX_SCAN = "Clustered Index Scan"
    INDEX_SCAN = "Index Scan"
    
    # Seek operatörleri
    CLUSTERED_INDEX_SEEK = "Clustered Index Seek"
    INDEX_SEEK = "Index Seek"
    
    # Join operatörleri
    NESTED_LOOPS = "Nested Loops"
    HASH_MATCH = "Hash Match"
    MERGE_JOIN = "Merge Join"
    
    # Aggregate operatörleri
    HASH_AGGREGATE = "Hash Match"
    STREAM_AGGREGATE = "Stream Aggregate"
    
    # Sort operatörleri
    SORT = "Sort"
    TOP = "Top"
    
    # Diğer operatörler
    FILTER = "Filter"
    COMPUTE_SCALAR = "Compute Scalar"
    CONCATENATION = "Concatenation"
    CONSTANT_SCAN = "Constant Scan"
    KEY_LOOKUP = "Key Lookup"
    RID_LOOKUP = "RID Lookup"
    PARALLELISM = "Parallelism"
    SEQUENCE = "Sequence"
    SPOOL = "Spool"
    TABLE_SPOOL = "Table Spool"
    INDEX_SPOOL = "Index Spool"
    SEGMENT = "Segment"
    SEQUENCE_PROJECT = "Sequence Project"
    
    # Insert/Update/Delete
    INSERT = "Insert"
    UPDATE = "Update"
    DELETE = "Delete"
    CLUSTERED_INDEX_INSERT = "Clustered Index Insert"
    CLUSTERED_INDEX_UPDATE = "Clustered Index Update"
    CLUSTERED_INDEX_DELETE = "Clustered Index Delete"
    
    # Diğer
    SELECT = "SELECT"
    RESULT = "Result"
    UNKNOWN = "Unknown"


class WarningType(str, Enum):
    """Plan uyarı tipleri"""
    NO_JOIN_PREDICATE = "NoJoinPredicate"
    COLUMNS_WITH_NO_STATISTICS = "ColumnsWithNoStatistics"
    SPILL_TO_TEMPDB = "SpillToTempDb"
    IMPLICIT_CONVERSION = "PlanAffectingConvert"
    UNMATCHED_INDEXES = "UnmatchedIndexes"
    MISSING_INDEX = "MissingIndex"
    MEMORY_GRANT_WARNING = "MemoryGrantWarning"
    WAIT_WARNING = "WaitWarning"


@dataclass
class PlanWarning:
    """Plan uyarısı"""
    warning_type: str
    message: str
    severity: str = "warning"  # warning, error, info
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MissingIndex:
    """Eksik index önerisi"""
    database: str
    schema_name: str
    table_name: str
    impact: float  # 0-100
    equality_columns: List[str] = field(default_factory=list)
    inequality_columns: List[str] = field(default_factory=list)
    include_columns: List[str] = field(default_factory=list)
    
    @property
    def create_statement(self) -> str:
        """CREATE INDEX statement oluştur"""
        cols = []
        if self.equality_columns:
            cols.extend(self.equality_columns)
        if self.inequality_columns:
            cols.extend(self.inequality_columns)
        
        stmt = f"CREATE NONCLUSTERED INDEX IX_{self.table_name}_missing\n"
        stmt += f"ON [{self.schema_name}].[{self.table_name}] ({', '.join(cols)})"
        
        if self.include_columns:
            stmt += f"\nINCLUDE ({', '.join(self.include_columns)})"
        
        return stmt


@dataclass
class PlanOperator:
    """
    Execution plan operatörü
    
    Her operatör aşağıdaki bilgileri içerir:
    - Temel bilgiler (tip, isim, maliyet)
    - I/O ve CPU maliyetleri
    - Tahmini ve gerçek satır sayıları
    - Alt operatörler (children)
    - Uyarılar
    """
    # Temel bilgiler
    node_id: int = 0
    physical_op: str = ""
    logical_op: str = ""
    operator_type: OperatorType = OperatorType.UNKNOWN
    
    # Maliyet bilgileri
    estimated_cost: float = 0.0
    subtree_cost: float = 0.0
    estimated_cpu_cost: float = 0.0
    estimated_io_cost: float = 0.0
    cost_percent: float = 0.0  # Toplam içindeki yüzde
    
    # Satır tahminleri
    estimated_rows: float = 0.0
    actual_rows: Optional[int] = None  # Actual plan için
    estimated_row_size: int = 0
    
    # Parallelism
    parallel: bool = False
    estimated_degree: int = 1
    
    # Nesne bilgisi (tablo/index)
    object_name: str = ""
    database_name: str = ""
    schema_name: str = ""
    index_name: str = ""
    
    # Predicates
    seek_predicates: str = ""
    predicates: str = ""
    
    # Memory
    memory_grant_kb: int = 0
    spill_to_tempdb: bool = False
    
    # Hiyerarşi
    children: List['PlanOperator'] = field(default_factory=list)
    parent: Optional['PlanOperator'] = None
    depth: int = 0
    
    # Uyarılar
    warnings: List[PlanWarning] = field(default_factory=list)
    
    @property
    def display_name(self) -> str:
        """Gösterim adı"""
        name = self.physical_op or self.logical_op or "Unknown"
        if self.object_name:
            name += f"\n[{self.object_name}]"
        if self.index_name and self.index_name != self.object_name:
            name += f"\n({self.index_name})"
        return name
    
    @property
    def short_name(self) -> str:
        """Kısa gösterim adı"""
        return self.physical_op or self.logical_op or "Unknown"
    
    @property
    def has_warnings(self) -> bool:
        """Uyarı var mı?"""
        return len(self.warnings) > 0
    
    @property
    def is_expensive(self) -> bool:
        """Pahalı operatör mü? (>25% maliyet)"""
        return self.cost_percent > 25
    
    @property
    def is_scan(self) -> bool:
        """Scan operatörü mü?"""
        return "Scan" in self.physical_op
    
    @property
    def is_seek(self) -> bool:
        """Seek operatörü mü?"""
        return "Seek" in self.physical_op
    
    @property
    def is_lookup(self) -> bool:
        """Key/RID Lookup mu?"""
        return "Lookup" in self.physical_op
    
    @property
    def icon_name(self) -> str:
        """Operatör ikonu adı"""
        op = self.physical_op.lower().replace(" ", "_")
        
        icon_map = {
            "table_scan": "⚠️",
            "clustered_index_scan": "📊",
            "index_scan": "📊",
            "clustered_index_seek": "✅",
            "index_seek": "✅",
            "nested_loops": "🔄",
            "hash_match": "🔗",
            "merge_join": "⚡",
            "sort": "📶",
            "filter": "🔍",
            "key_lookup": "⚠️",
            "rid_lookup": "⚠️",
            "parallelism": "🔀",
            "compute_scalar": "📐",
            "top": "🔝",
            "select": "📋",
        }
        
        for key, icon in icon_map.items():
            if key in op:
                return icon
        
        return "⚙️"
    
    @property
    def status_color(self) -> str:
        """Durum rengi"""
        if self.has_warnings or self.spill_to_tempdb:
            return "#ef4444"  # Kırmızı
        if self.is_scan or self.is_lookup:
            return "#f97316"  # Turuncu
        if self.is_expensive:
            return "#eab308"  # Sarı
        return "#22c55e"  # Yeşil
    
    def get_all_operators(self) -> List['PlanOperator']:
        """Tüm operatörleri düz liste olarak döndür"""
        result = [self]
        for child in self.children:
            result.extend(child.get_all_operators())
        return result


@dataclass
class ExecutionPlan:
    """
    Tam execution plan
    
    İçerir:
    - Plan metadata (compile time, version)
    - Root operatör ve alt ağaç
    - Missing index önerileri
    - Plan uyarıları
    - Toplam maliyetler
    """
    # Metadata
    plan_id: Optional[int] = None
    query_id: Optional[int] = None
    plan_hash: str = ""
    
    # Compile bilgisi
    compile_time: Optional[datetime] = None
    compile_cpu: float = 0.0
    compile_memory: int = 0
    
    # Statement bilgisi
    statement_text: str = ""
    statement_type: str = ""
    
    # Root operatör
    root_operator: Optional[PlanOperator] = None
    
    # Toplam maliyetler
    total_cost: float = 0.0
    total_estimated_rows: float = 0.0
    
    # Parallelism
    degree_of_parallelism: int = 1
    
    # Uyarılar ve öneriler
    warnings: List[PlanWarning] = field(default_factory=list)
    missing_indexes: List[MissingIndex] = field(default_factory=list)
    
    # Plan XML (orijinal)
    plan_xml: str = ""
    
    @property
    def operator_count(self) -> int:
        """Toplam operatör sayısı"""
        if not self.root_operator:
            return 0
        return len(self.root_operator.get_all_operators())
    
    @property
    def has_warnings(self) -> bool:
        """Uyarı var mı?"""
        if self.warnings:
            return True
        if self.root_operator:
            for op in self.root_operator.get_all_operators():
                if op.has_warnings:
                    return True
        return False
    
    @property
    def has_scans(self) -> bool:
        """Table/Index scan var mı?"""
        if not self.root_operator:
            return False
        return any(op.is_scan for op in self.root_operator.get_all_operators())
    
    @property
    def has_lookups(self) -> bool:
        """Key/RID lookup var mı?"""
        if not self.root_operator:
            return False
        return any(op.is_lookup for op in self.root_operator.get_all_operators())
    
    @property
    def expensive_operators(self) -> List[PlanOperator]:
        """Pahalı operatörleri döndür (>10% maliyet)"""
        if not self.root_operator:
            return []
        return [op for op in self.root_operator.get_all_operators() if op.cost_percent > 10]


class PlanParser:
    """
    Execution Plan XML Parser
    
    Kullanım:
        parser = PlanParser()
        plan = parser.parse(xml_string)
        
        # Operatörleri listele
        for op in plan.root_operator.get_all_operators():
            print(f"{op.display_name}: {op.cost_percent}%")
    """
    
    _PARSED_PLAN_CACHE_MAX = 50
    _PARSED_PLAN_CACHE: "OrderedDict[str, ExecutionPlan]" = OrderedDict()
    _CACHE_LOCK = Lock()

    def __init__(self):
        self._total_cost = 0.0

    @classmethod
    def clear_cache(cls) -> None:
        with cls._CACHE_LOCK:
            cls._PARSED_PLAN_CACHE.clear()

    @classmethod
    def cache_info(cls) -> Dict[str, int]:
        with cls._CACHE_LOCK:
            return {"size": len(cls._PARSED_PLAN_CACHE), "max_size": int(cls._PARSED_PLAN_CACHE_MAX)}

    @staticmethod
    def _make_cache_key(xml_string: str) -> str:
        return hashlib.sha1(str(xml_string or "").encode("utf-8", errors="ignore")).hexdigest()

    @classmethod
    def _get_cached_plan(cls, cache_key: str) -> Optional[ExecutionPlan]:
        with cls._CACHE_LOCK:
            cached = cls._PARSED_PLAN_CACHE.get(cache_key)
            if cached is None:
                return None
            cls._PARSED_PLAN_CACHE.move_to_end(cache_key)
            return copy.deepcopy(cached)

    @classmethod
    def _set_cached_plan(cls, cache_key: str, plan: ExecutionPlan) -> None:
        with cls._CACHE_LOCK:
            cls._PARSED_PLAN_CACHE[cache_key] = copy.deepcopy(plan)
            cls._PARSED_PLAN_CACHE.move_to_end(cache_key)
            while len(cls._PARSED_PLAN_CACHE) > int(cls._PARSED_PLAN_CACHE_MAX):
                cls._PARSED_PLAN_CACHE.popitem(last=False)
    
    def parse(self, xml_string: str) -> Optional[ExecutionPlan]:
        """
        Plan XML'ini parse et
        
        Args:
            xml_string: Showplan XML string
        
        Returns:
            ExecutionPlan veya None (hata durumunda)
        """
        if not xml_string or not xml_string.strip():
            logger.warning("Empty plan XML")
            return None

        cache_key = self._make_cache_key(xml_string)
        cached_plan = self._get_cached_plan(cache_key)
        if cached_plan is not None:
            logger.debug("Plan parser cache hit")
            return cached_plan
        
        try:
            # XML'i parse et
            root = ET.fromstring(xml_string)
            
            # Namespace kontrolü
            if root.tag.startswith('{'):
                # Namespace'li XML
                ns = {'sp': root.tag.split('}')[0].strip('{')}
            else:
                ns = SHOWPLAN_NS
            
            plan = ExecutionPlan(plan_xml=xml_string)
            
            # Batch'i bul
            batch = root.find('.//sp:Batch', ns)
            if batch is None:
                batch = root.find('.//Batch')
            
            if batch is None:
                # Direkt ShowPlanXML altında ara
                stmt = root.find('.//sp:StmtSimple', ns)
                if stmt is None:
                    stmt = root.find('.//StmtSimple')
            else:
                stmt = batch.find('.//sp:StmtSimple', ns)
                if stmt is None:
                    stmt = batch.find('.//StmtSimple')
            
            if stmt is None:
                logger.warning("No statement found in plan XML")
                return plan
            
            # Statement bilgisi
            plan.statement_text = stmt.get('StatementText', '')
            plan.statement_type = stmt.get('StatementType', '')
            
            # Compile bilgisi
            plan.compile_cpu = float(stmt.get('StatementCompCpu', 0))
            plan.compile_memory = int(stmt.get('StatementCompMem', 0))
            
            # Missing indexes
            plan.missing_indexes = self._parse_missing_indexes(stmt, ns)
            
            # RelOp (root operatör) bul
            query_plan = stmt.find('.//sp:QueryPlan', ns)
            if query_plan is None:
                query_plan = stmt.find('.//QueryPlan')
            
            if query_plan is not None:
                # DOP
                plan.degree_of_parallelism = int(query_plan.get('DegreeOfParallelism', 1))
                
                # Root RelOp
                rel_op = query_plan.find('sp:RelOp', ns)
                if rel_op is None:
                    rel_op = query_plan.find('RelOp')
                
                if rel_op is not None:
                    # İlk geçişte toplam maliyeti hesapla
                    self._total_cost = float(rel_op.get('EstimatedTotalSubtreeCost', 0))
                    plan.total_cost = self._total_cost
                    
                    # Operatör ağacını oluştur
                    plan.root_operator = self._parse_rel_op(rel_op, ns, depth=0)
            
            # Plan-level uyarıları topla
            plan.warnings = self._collect_plan_warnings(plan)
            
            logger.info(f"Parsed plan: {plan.operator_count} operators, cost={plan.total_cost:.4f}")
            self._set_cached_plan(cache_key, plan)
            return plan
            
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return None
        except Exception as e:
            logger.error(f"Plan parse error: {e}")
            return None
    
    def _parse_rel_op(
        self, 
        rel_op_elem: ET.Element, 
        ns: dict, 
        depth: int = 0,
        node_id: int = 0
    ) -> PlanOperator:
        """RelOp elementini parse et"""
        op = PlanOperator(
            node_id=node_id,
            depth=depth
        )
        
        # Temel özellikler
        op.physical_op = rel_op_elem.get('PhysicalOp', '')
        op.logical_op = rel_op_elem.get('LogicalOp', '')
        op.estimated_cost = float(rel_op_elem.get('EstimatedTotalSubtreeCost', 0))
        op.subtree_cost = op.estimated_cost
        op.estimated_rows = float(rel_op_elem.get('EstimateRows', 0))
        op.estimated_row_size = int(rel_op_elem.get('AvgRowSize', 0))
        op.parallel = rel_op_elem.get('Parallel', '0') == '1'
        
        # Maliyet yüzdesi
        if self._total_cost > 0:
            op.cost_percent = (op.estimated_cost / self._total_cost) * 100
        
        # I/O ve CPU maliyetleri
        op.estimated_io_cost = float(rel_op_elem.get('EstimateIO', 0))
        op.estimated_cpu_cost = float(rel_op_elem.get('EstimateCPU', 0))
        
        # Operatör tipini belirle
        op.operator_type = self._get_operator_type(op.physical_op)
        
        # Nesne bilgisi (tablo, index)
        self._parse_object_info(rel_op_elem, op, ns)
        
        # Predicates
        self._parse_predicates(rel_op_elem, op, ns)
        
        # Warnings
        self._parse_warnings(rel_op_elem, op, ns)
        
        # Memory grant
        memory_elem = rel_op_elem.find('.//sp:MemoryGrant', ns)
        if memory_elem is None:
            memory_elem = rel_op_elem.find('.//MemoryGrant')
        if memory_elem is not None:
            op.memory_grant_kb = int(memory_elem.get('SerialDesiredMemory', 0))
        
        # Child RelOp'ları bul
        child_id = node_id + 1
        for child_rel_op in rel_op_elem.findall('sp:RelOp', ns):
            child = self._parse_rel_op(child_rel_op, ns, depth + 1, child_id)
            child.parent = op
            op.children.append(child)
            child_id += len(child.get_all_operators())
        
        # Namespace'siz de dene
        if not op.children:
            for child_rel_op in rel_op_elem.findall('RelOp'):
                child = self._parse_rel_op(child_rel_op, ns, depth + 1, child_id)
                child.parent = op
                op.children.append(child)
                child_id += len(child.get_all_operators())
        
        # İç içe operatörler (örn: IndexScan içindeki RelOp)
        for inner_elem in rel_op_elem:
            for inner_rel_op in inner_elem.findall('sp:RelOp', ns):
                child = self._parse_rel_op(inner_rel_op, ns, depth + 1, child_id)
                child.parent = op
                op.children.append(child)
                child_id += len(child.get_all_operators())
            
            # Namespace'siz
            for inner_rel_op in inner_elem.findall('RelOp'):
                if inner_rel_op not in rel_op_elem.findall('RelOp'):
                    child = self._parse_rel_op(inner_rel_op, ns, depth + 1, child_id)
                    child.parent = op
                    op.children.append(child)
                    child_id += len(child.get_all_operators())
        
        return op
    
    def _get_operator_type(self, physical_op: str) -> OperatorType:
        """Physical op'tan operatör tipini belirle"""
        op_lower = physical_op.lower()
        
        type_map = {
            "table scan": OperatorType.TABLE_SCAN,
            "clustered index scan": OperatorType.CLUSTERED_INDEX_SCAN,
            "index scan": OperatorType.INDEX_SCAN,
            "clustered index seek": OperatorType.CLUSTERED_INDEX_SEEK,
            "index seek": OperatorType.INDEX_SEEK,
            "nested loops": OperatorType.NESTED_LOOPS,
            "hash match": OperatorType.HASH_MATCH,
            "merge join": OperatorType.MERGE_JOIN,
            "sort": OperatorType.SORT,
            "top": OperatorType.TOP,
            "filter": OperatorType.FILTER,
            "compute scalar": OperatorType.COMPUTE_SCALAR,
            "key lookup": OperatorType.KEY_LOOKUP,
            "rid lookup": OperatorType.RID_LOOKUP,
            "parallelism": OperatorType.PARALLELISM,
        }
        
        for key, op_type in type_map.items():
            if key in op_lower:
                return op_type
        
        return OperatorType.UNKNOWN
    
    def _parse_object_info(self, rel_op: ET.Element, op: PlanOperator, ns: dict) -> None:
        """Nesne bilgisini parse et"""
        # IndexScan, TableScan vb. içindeki Object elementini bul
        for child in rel_op:
            obj = child.find('sp:Object', ns)
            if obj is None:
                obj = child.find('Object')
            
            if obj is not None:
                op.database_name = obj.get('Database', '').strip('[]')
                op.schema_name = obj.get('Schema', '').strip('[]')
                op.object_name = obj.get('Table', '').strip('[]')
                op.index_name = obj.get('Index', '').strip('[]')
                break
    
    def _parse_predicates(self, rel_op: ET.Element, op: PlanOperator, ns: dict) -> None:
        """Predicate bilgilerini parse et"""
        # SeekPredicates
        seek_elem = rel_op.find('.//sp:SeekPredicates', ns)
        if seek_elem is None:
            seek_elem = rel_op.find('.//SeekPredicates')
        
        if seek_elem is not None:
            op.seek_predicates = self._extract_scalar_string(seek_elem)
        
        # Predicate
        pred_elem = rel_op.find('.//sp:Predicate', ns)
        if pred_elem is None:
            pred_elem = rel_op.find('.//Predicate')
        
        if pred_elem is not None:
            op.predicates = self._extract_scalar_string(pred_elem)
    
    def _extract_scalar_string(self, elem: ET.Element) -> str:
        """ScalarOperator'dan string çıkar"""
        # Basitleştirilmiş - gerçek implementasyon daha karmaşık olabilir
        text_parts = []
        for col in elem.iter():
            if 'Column' in col.tag:
                col_name = col.get('Column', '')
                if col_name:
                    text_parts.append(col_name)
            if 'Const' in col.tag:
                val = col.get('ConstValue', '')
                if val:
                    text_parts.append(val)
        
        return ' '.join(text_parts)[:200]  # İlk 200 karakter
    
    def _parse_warnings(self, rel_op: ET.Element, op: PlanOperator, ns: dict) -> None:
        """Uyarıları parse et"""
        warnings_elem = rel_op.find('.//sp:Warnings', ns)
        if warnings_elem is None:
            warnings_elem = rel_op.find('.//Warnings')
        
        if warnings_elem is None:
            return
        
        for child in warnings_elem:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            
            warning = PlanWarning(
                warning_type=tag,
                message=self._get_warning_message(tag, child),
                severity="warning"
            )
            op.warnings.append(warning)
            
            # Spill kontrolü
            if 'Spill' in tag:
                op.spill_to_tempdb = True
    
    def _get_warning_message(self, warning_type: str, elem: ET.Element) -> str:
        """Uyarı mesajı oluştur"""
        messages = {
            "NoJoinPredicate": "Join predicate is missing - may result in a Cartesian product",
            "SpillToTempDb": "Spill to TempDB occurred - memory grant may be insufficient",
            "ColumnsWithNoStatistics": "Columns without statistics were detected",
            "PlanAffectingConvert": "Implicit conversion is negatively affecting the plan",
            "UnmatchedIndexes": "Unmatched/unused index references were detected",
        }
        
        return messages.get(warning_type, f"Warning: {warning_type}")
    
    def _parse_missing_indexes(self, stmt: ET.Element, ns: dict) -> List[MissingIndex]:
        """Missing index önerilerini parse et"""
        missing = []
        
        for mi_group in stmt.findall('.//sp:MissingIndexGroup', ns):
            impact = float(mi_group.get('Impact', 0))
            
            for mi in mi_group.findall('.//sp:MissingIndex', ns):
                index = MissingIndex(
                    database=mi.get('Database', '').strip('[]'),
                    schema_name=mi.get('Schema', '').strip('[]'),
                    table_name=mi.get('Table', '').strip('[]'),
                    impact=impact
                )
                
                # Equality columns
                for col_group in mi.findall('sp:ColumnGroup', ns):
                    usage = col_group.get('Usage', '')
                    for col in col_group.findall('sp:Column', ns):
                        col_name = col.get('Name', '').strip('[]')
                        if usage == 'EQUALITY':
                            index.equality_columns.append(col_name)
                        elif usage == 'INEQUALITY':
                            index.inequality_columns.append(col_name)
                        elif usage == 'INCLUDE':
                            index.include_columns.append(col_name)
                
                missing.append(index)
        
        # Namespace'siz de dene
        if not missing:
            for mi_group in stmt.findall('.//MissingIndexGroup'):
                impact = float(mi_group.get('Impact', 0))
                
                for mi in mi_group.findall('.//MissingIndex'):
                    index = MissingIndex(
                        database=mi.get('Database', '').strip('[]'),
                        schema_name=mi.get('Schema', '').strip('[]'),
                        table_name=mi.get('Table', '').strip('[]'),
                        impact=impact
                    )
                    
                    for col_group in mi.findall('ColumnGroup'):
                        usage = col_group.get('Usage', '')
                        for col in col_group.findall('Column'):
                            col_name = col.get('Name', '').strip('[]')
                            if usage == 'EQUALITY':
                                index.equality_columns.append(col_name)
                            elif usage == 'INEQUALITY':
                                index.inequality_columns.append(col_name)
                            elif usage == 'INCLUDE':
                                index.include_columns.append(col_name)
                    
                    missing.append(index)
        
        return missing
    
    def _collect_plan_warnings(self, plan: ExecutionPlan) -> List[PlanWarning]:
        """Plan seviyesi uyarıları topla"""
        warnings = []
        
        if plan.has_scans:
            warnings.append(PlanWarning(
                warning_type="TableScan",
                message="Table veya Index Scan tespit edildi - Index eklemeyi düşünün",
                severity="warning"
            ))
        
        if plan.has_lookups:
            warnings.append(PlanWarning(
                warning_type="KeyLookup",
                message="Key/RID Lookup tespit edildi - Covering index eklemeyi düşünün",
                severity="warning"
            ))
        
        if plan.missing_indexes:
            warnings.append(PlanWarning(
                warning_type="MissingIndex",
                message=f"{len(plan.missing_indexes)} adet missing index önerisi var",
                severity="info"
            ))
        
        return warnings
