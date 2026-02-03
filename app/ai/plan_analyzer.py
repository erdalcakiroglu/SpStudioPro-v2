"""
Execution Plan Analyzer - Parse and extract insights from SQL Server execution plans

Bu modül XML execution plan'ı analiz ederek:
1. Pahalı operatörleri tespit eder
2. Uyarıları çıkarır
3. Missing index önerilerini bulur
4. Actual vs Estimated row farklarını tespit eder
5. AI'a zengin context sağlar
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.core.logger import get_logger

logger = get_logger('ai.plan_analyzer')


class OperatorType(Enum):
    """SQL Server execution plan operatör türleri"""
    # Scans (Pahalı)
    TABLE_SCAN = "Table Scan"
    CLUSTERED_INDEX_SCAN = "Clustered Index Scan"
    INDEX_SCAN = "Index Scan"
    
    # Seeks (İyi)
    CLUSTERED_INDEX_SEEK = "Clustered Index Seek"
    INDEX_SEEK = "Index Seek"
    
    # Lookups (Potansiyel sorun)
    KEY_LOOKUP = "Key Lookup"
    RID_LOOKUP = "RID Lookup"
    
    # Joins
    NESTED_LOOPS = "Nested Loops"
    HASH_MATCH = "Hash Match"
    MERGE_JOIN = "Merge Join"
    
    # Sorts (Memory pressure)
    SORT = "Sort"
    
    # Spools
    TABLE_SPOOL = "Table Spool"
    INDEX_SPOOL = "Index Spool"
    
    # Aggregations
    HASH_AGGREGATE = "Hash Match (Aggregate)"
    STREAM_AGGREGATE = "Stream Aggregate"
    
    # Others
    PARALLELISM = "Parallelism"
    COMPUTE_SCALAR = "Compute Scalar"
    FILTER = "Filter"
    TOP = "Top"


@dataclass
class PlanOperator:
    """Execution plan operatörü"""
    name: str
    physical_op: str
    logical_op: str
    estimated_rows: float
    actual_rows: float = 0
    estimated_cost: float = 0
    actual_cost: float = 0
    cpu_cost: float = 0
    io_cost: float = 0
    subtree_cost: float = 0
    parallel: bool = False
    warnings: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def row_estimate_accuracy(self) -> float:
        """Actual vs Estimated row doğruluğu (1.0 = mükemmel)"""
        if self.estimated_rows == 0:
            return 0.0 if self.actual_rows > 0 else 1.0
        return min(self.actual_rows, self.estimated_rows) / max(self.actual_rows, self.estimated_rows)
    
    @property
    def has_bad_estimate(self) -> bool:
        """Kötü tahmin mi? (10x veya daha fazla fark)"""
        if self.estimated_rows == 0 or self.actual_rows == 0:
            return False
        ratio = max(self.actual_rows, self.estimated_rows) / max(min(self.actual_rows, self.estimated_rows), 1)
        return ratio >= 10


@dataclass
class MissingIndex:
    """Missing index önerisi"""
    database: str
    schema_name: str
    table_name: str
    equality_columns: List[str]
    inequality_columns: List[str]
    include_columns: List[str]
    impact: float  # 0-100
    
    def to_create_statement(self) -> str:
        """CREATE INDEX ifadesi oluştur"""
        cols = self.equality_columns + self.inequality_columns
        col_str = ", ".join(cols) if cols else ""
        
        idx_name = f"IX_{self.table_name}_{'_'.join(cols[:2])}" if cols else f"IX_{self.table_name}_suggested"
        
        sql = f"CREATE NONCLUSTERED INDEX [{idx_name}]\n"
        sql += f"ON [{self.schema_name}].[{self.table_name}] ({col_str})"
        
        if self.include_columns:
            sql += f"\nINCLUDE ({', '.join(self.include_columns)})"
        
        sql += ";"
        return sql


@dataclass
class PlanWarning:
    """Execution plan uyarısı"""
    warning_type: str
    message: str
    severity: str  # "High", "Medium", "Low"
    operator: Optional[str] = None
    recommendation: str = ""


@dataclass
class PlanInsights:
    """Execution plan'dan çıkarılan tüm bilgiler"""
    # Genel bilgiler
    total_cost: float = 0
    statement_type: str = ""
    optimization_level: str = ""
    reason_for_early_termination: str = ""
    
    # Paralellik
    is_parallel: bool = False
    degree_of_parallelism: int = 0
    
    # Operatörler
    operators: List[PlanOperator] = field(default_factory=list)
    expensive_operators: List[str] = field(default_factory=list)
    
    # Problemler
    warnings: List[PlanWarning] = field(default_factory=list)
    missing_indexes: List[MissingIndex] = field(default_factory=list)
    
    # İstatistikler
    estimated_rows: float = 0
    actual_rows: float = 0
    
    # Özet
    has_table_scan: bool = False
    has_key_lookup: bool = False
    has_sort_warning: bool = False
    has_hash_spill: bool = False
    has_implicit_conversion: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """AI prompt için dict'e dönüştür"""
        return {
            "total_cost": self.total_cost,
            "is_parallel": self.is_parallel,
            "dop": self.degree_of_parallelism,
            "warnings": [w.message for w in self.warnings],
            "expensive_operators": self.expensive_operators,
            "missing_indexes": [
                {
                    "table": f"{mi.schema_name}.{mi.table_name}",
                    "equality_columns": mi.equality_columns,
                    "include_columns": mi.include_columns,
                    "impact": mi.impact
                }
                for mi in self.missing_indexes
            ],
            "has_table_scan": self.has_table_scan,
            "has_key_lookup": self.has_key_lookup,
            "has_implicit_conversion": self.has_implicit_conversion,
            "row_estimate_issues": any(op.has_bad_estimate for op in self.operators)
        }
    
    def get_summary(self) -> str:
        """İnsan tarafından okunabilir özet"""
        lines = []
        
        if self.is_parallel:
            lines.append(f"⚡ Paralel plan (DOP: {self.degree_of_parallelism})")
        
        if self.has_table_scan:
            lines.append("⚠️ Table Scan tespit edildi - Index gerekebilir")
        
        if self.has_key_lookup:
            lines.append("⚠️ Key Lookup tespit edildi - Covering index önerilir")
        
        if self.has_implicit_conversion:
            lines.append("⚠️ Implicit Conversion - Index kullanımını engelleyebilir")
        
        if self.has_sort_warning:
            lines.append("⚠️ Sort Warning - Memory grant yetersiz olabilir")
        
        if self.has_hash_spill:
            lines.append("⚠️ Hash Spill - TempDB'ye yazma var")
        
        if self.missing_indexes:
            lines.append(f"📈 {len(self.missing_indexes)} missing index önerisi")
        
        if not lines:
            lines.append("✅ Önemli bir sorun tespit edilmedi")
        
        return "\n".join(lines)


class ExecutionPlanAnalyzer:
    """
    SQL Server Execution Plan XML analyzer
    
    Usage:
        analyzer = ExecutionPlanAnalyzer()
        insights = analyzer.analyze(plan_xml)
        
        print(insights.get_summary())
        print(insights.to_dict())
    """
    
    # XML namespaces
    NAMESPACES = {
        'sp': 'http://schemas.microsoft.com/sqlserver/2004/07/showplan'
    }
    
    # Pahalı operatörler listesi
    EXPENSIVE_OPERATORS = {
        "Table Scan",
        "Clustered Index Scan", 
        "Index Scan",
        "Key Lookup",
        "RID Lookup",
        "Sort",
        "Hash Match",
        "Table Spool",
    }
    
    def analyze(self, plan_xml: str) -> PlanInsights:
        """
        Execution plan XML'i analiz et
        
        Args:
            plan_xml: SQL Server execution plan XML string
            
        Returns:
            PlanInsights with all extracted information
        """
        insights = PlanInsights()
        
        if not plan_xml or not plan_xml.strip():
            logger.warning("Empty plan XML provided")
            return insights
        
        try:
            # Parse XML
            root = ET.fromstring(plan_xml)
            
            # Extract general info
            self._extract_general_info(root, insights)
            
            # Extract operators
            self._extract_operators(root, insights)
            
            # Extract missing indexes
            self._extract_missing_indexes(root, insights)
            
            # Extract warnings
            self._extract_warnings(root, insights)
            
            # Analyze and set flags
            self._analyze_operators(insights)
            
            logger.info(f"Plan analysis complete: {len(insights.operators)} operators, "
                       f"{len(insights.warnings)} warnings, {len(insights.missing_indexes)} missing indexes")
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse plan XML: {e}")
            insights.warnings.append(PlanWarning(
                warning_type="ParseError",
                message=f"Plan XML parse hatası: {str(e)}",
                severity="High"
            ))
        except Exception as e:
            logger.error(f"Plan analysis error: {e}")
            insights.warnings.append(PlanWarning(
                warning_type="AnalysisError",
                message=f"Plan analiz hatası: {str(e)}",
                severity="Medium"
            ))
        
        return insights
    
    def _extract_general_info(self, root: ET.Element, insights: PlanInsights) -> None:
        """Genel plan bilgilerini çıkar"""
        # Statement info
        stmt = root.find('.//sp:StmtSimple', self.NAMESPACES)
        if stmt is not None:
            insights.statement_type = stmt.get('StatementType', '')
            cost = stmt.get('StatementSubTreeCost')
            if cost:
                insights.total_cost = float(cost)
            
            # Optimization info
            opt = stmt.get('StatementOptmLevel', '')
            insights.optimization_level = opt
            
            early_term = stmt.get('StatementOptmEarlyAbortReason', '')
            insights.reason_for_early_termination = early_term
        
        # Parallelism check
        parallelism = root.find('.//sp:RelOp[@PhysicalOp="Parallelism"]', self.NAMESPACES)
        if parallelism is not None:
            insights.is_parallel = True
            # Try to get DOP
            runtime = root.find('.//sp:QueryPlan', self.NAMESPACES)
            if runtime is not None:
                dop = runtime.get('DegreeOfParallelism')
                if dop:
                    insights.degree_of_parallelism = int(dop)
    
    def _extract_operators(self, root: ET.Element, insights: PlanInsights) -> None:
        """Tüm operatörleri çıkar"""
        for relop in root.findall('.//sp:RelOp', self.NAMESPACES):
            physical_op = relop.get('PhysicalOp', '')
            logical_op = relop.get('LogicalOp', '')
            
            # Cost info
            estimated_cost = float(relop.get('EstimateCPU', 0)) + float(relop.get('EstimateIO', 0))
            subtree_cost = float(relop.get('EstimatedTotalSubtreeCost', 0))
            
            # Row estimates
            estimated_rows = float(relop.get('EstimateRows', 0))
            
            # Actual rows (if actual plan)
            actual_rows = 0
            runtime_info = relop.find('.//sp:RunTimeInformation/sp:RunTimeCountersPerThread', self.NAMESPACES)
            if runtime_info is not None:
                actual_rows = float(runtime_info.get('ActualRows', 0))
            
            # Create operator object
            op = PlanOperator(
                name=physical_op,
                physical_op=physical_op,
                logical_op=logical_op,
                estimated_rows=estimated_rows,
                actual_rows=actual_rows,
                estimated_cost=estimated_cost,
                subtree_cost=subtree_cost,
                cpu_cost=float(relop.get('EstimateCPU', 0)),
                io_cost=float(relop.get('EstimateIO', 0)),
                parallel=relop.get('Parallel', '0') == '1'
            )
            
            # Check for warnings
            warnings = relop.findall('.//sp:Warnings/*', self.NAMESPACES)
            for w in warnings:
                op.warnings.append(w.tag.replace('{' + self.NAMESPACES['sp'] + '}', ''))
            
            insights.operators.append(op)
            
            # Track expensive operators
            if physical_op in self.EXPENSIVE_OPERATORS:
                if physical_op not in insights.expensive_operators:
                    insights.expensive_operators.append(physical_op)
    
    def _extract_missing_indexes(self, root: ET.Element, insights: PlanInsights) -> None:
        """Missing index önerilerini çıkar"""
        for mig in root.findall('.//sp:MissingIndexGroup', self.NAMESPACES):
            impact = float(mig.get('Impact', 0))
            
            mi_elem = mig.find('.//sp:MissingIndex', self.NAMESPACES)
            if mi_elem is not None:
                database = mi_elem.get('Database', '').strip('[]')
                schema = mi_elem.get('Schema', 'dbo').strip('[]')
                table = mi_elem.get('Table', '').strip('[]')
                
                # Equality columns
                eq_cols = []
                for col in mi_elem.findall('.//sp:ColumnGroup[@Usage="EQUALITY"]/sp:Column', self.NAMESPACES):
                    eq_cols.append(col.get('Name', '').strip('[]'))
                
                # Inequality columns
                ineq_cols = []
                for col in mi_elem.findall('.//sp:ColumnGroup[@Usage="INEQUALITY"]/sp:Column', self.NAMESPACES):
                    ineq_cols.append(col.get('Name', '').strip('[]'))
                
                # Include columns
                inc_cols = []
                for col in mi_elem.findall('.//sp:ColumnGroup[@Usage="INCLUDE"]/sp:Column', self.NAMESPACES):
                    inc_cols.append(col.get('Name', '').strip('[]'))
                
                insights.missing_indexes.append(MissingIndex(
                    database=database,
                    schema_name=schema,
                    table_name=table,
                    equality_columns=eq_cols,
                    inequality_columns=ineq_cols,
                    include_columns=inc_cols,
                    impact=impact
                ))
    
    def _extract_warnings(self, root: ET.Element, insights: PlanInsights) -> None:
        """Plan uyarılarını çıkar"""
        # Implicit conversions
        for conv in root.findall('.//sp:Warnings/sp:PlanAffectingConvert', self.NAMESPACES):
            conv_type = conv.get('ConvertIssue', '')
            expression = conv.get('Expression', '')
            
            insights.warnings.append(PlanWarning(
                warning_type="ImplicitConversion",
                message=f"Implicit conversion: {conv_type} - {expression}",
                severity="Medium",
                recommendation="Veri tiplerini eşleştirin veya explicit CAST kullanın"
            ))
            insights.has_implicit_conversion = True
        
        # Sort warnings
        for sort_warn in root.findall('.//sp:Warnings/sp:SortWarning', self.NAMESPACES):
            sort_type = sort_warn.get('SortSpillDetails', '')
            
            insights.warnings.append(PlanWarning(
                warning_type="SortWarning",
                message=f"Sort spill to TempDB: {sort_type}",
                severity="Medium",
                recommendation="Memory grant artırın veya sorguyu optimize edin"
            ))
            insights.has_sort_warning = True
        
        # Hash spill warnings  
        for hash_warn in root.findall('.//sp:Warnings/sp:HashWarning', self.NAMESPACES):
            hash_type = hash_warn.get('HashSpillDetails', '')
            
            insights.warnings.append(PlanWarning(
                warning_type="HashSpill",
                message=f"Hash spill to TempDB: {hash_type}",
                severity="Medium",
                recommendation="Memory grant artırın veya join stratejisini değiştirin"
            ))
            insights.has_hash_spill = True
        
        # No stats warnings
        for no_stats in root.findall('.//sp:Warnings/sp:NoStats', self.NAMESPACES):
            insights.warnings.append(PlanWarning(
                warning_type="NoStatistics",
                message="İstatistik bilgisi eksik - tahminler yanlış olabilir",
                severity="High",
                recommendation="UPDATE STATISTICS çalıştırın"
            ))
        
        # Columns with no statistics
        for col_no_stats in root.findall('.//sp:Warnings/sp:ColumnsWithNoStatistics', self.NAMESPACES):
            insights.warnings.append(PlanWarning(
                warning_type="ColumnsNoStats",
                message="Bazı kolonlarda istatistik yok",
                severity="Medium",
                recommendation="CREATE STATISTICS ile kolon istatistiği oluşturun"
            ))
    
    def _analyze_operators(self, insights: PlanInsights) -> None:
        """Operatörleri analiz et ve flag'leri ayarla"""
        for op in insights.operators:
            # Table scan check
            if op.physical_op == "Table Scan":
                insights.has_table_scan = True
                insights.warnings.append(PlanWarning(
                    warning_type="TableScan",
                    message=f"Table Scan tespit edildi",
                    severity="High",
                    operator=op.name,
                    recommendation="Bu tablo için uygun index oluşturun"
                ))
            
            # Key lookup check
            if op.physical_op in ("Key Lookup", "RID Lookup"):
                insights.has_key_lookup = True
                insights.warnings.append(PlanWarning(
                    warning_type="KeyLookup",
                    message=f"{op.physical_op} tespit edildi",
                    severity="Medium",
                    operator=op.name,
                    recommendation="Covering index ile lookup'ı ortadan kaldırın"
                ))
            
            # Bad row estimates
            if op.has_bad_estimate:
                insights.warnings.append(PlanWarning(
                    warning_type="BadEstimate",
                    message=f"Kötü row tahmini: Est={op.estimated_rows:.0f}, Act={op.actual_rows:.0f}",
                    severity="Medium",
                    operator=op.name,
                    recommendation="İstatistikleri güncelleyin veya histogram'ı kontrol edin"
                ))


def analyze_plan(plan_xml: str) -> PlanInsights:
    """Shortcut function for plan analysis"""
    analyzer = ExecutionPlanAnalyzer()
    return analyzer.analyze(plan_xml)


def get_plan_summary(plan_xml: str) -> str:
    """Get human-readable plan summary"""
    insights = analyze_plan(plan_xml)
    return insights.get_summary()


def get_plan_for_ai(plan_xml: str) -> Dict[str, Any]:
    """Get plan insights formatted for AI prompt"""
    insights = analyze_plan(plan_xml)
    return insights.to_dict()
