"""
Query Stats Data Models

Bu modül Query Stats modülü için veri modellerini içerir.
Section 24.4 ve 24.8'deki tanımlara uygun olarak tasarlanmıştır.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class QueryPriority(str, Enum):
    """Sorgu öncelik seviyesi (Section 24.6)"""
    CRITICAL = "critical"   # Impact > 90, Plan Count > 4
    HIGH = "high"           # Impact 70-90, Trend > 30%
    MEDIUM = "medium"       # Impact 40-70, Plan Count 2-3
    LOW = "low"             # Impact < 40, Stabil
    INFO = "info"           # Yeni sorgu, yetersiz veri


class PlanStability(str, Enum):
    """Plan stabilite durumu"""
    STABLE = "stable"       # 1 plan - 🟢
    ATTENTION = "attention" # 2-3 plan - 🟡
    PROBLEM = "problem"     # 4+ plan - 🔴


@dataclass
class WaitProfile:
    """
    Sorgu bazlı wait profili
    
    Wait kategorileri ve yüzdeleri içerir.
    """
    category: str
    total_wait_ms: float
    wait_percent: float
    
    @property
    def display_name(self) -> str:
        """Kategori gösterim adı"""
        from app.database.queries.query_store_queries import WAIT_CATEGORY_MAPPING
        mapping = WAIT_CATEGORY_MAPPING.get(self.category, {})
        return mapping.get("display", self.category)
    
    @property
    def color(self) -> str:
        """Kategori rengi"""
        from app.database.queries.query_store_queries import WAIT_CATEGORY_MAPPING
        mapping = WAIT_CATEGORY_MAPPING.get(self.category, {})
        return mapping.get("color", "#888888")
    
    @property
    def icon(self) -> str:
        """Kategori ikonu"""
        from app.database.queries.query_store_queries import WAIT_CATEGORY_MAPPING
        mapping = WAIT_CATEGORY_MAPPING.get(self.category, {})
        return mapping.get("icon", "❓")


@dataclass
class PlanInfo:
    """
    Execution plan bilgisi
    """
    plan_id: int
    plan_hash: str
    is_forced: bool = False
    force_failure_count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    execution_count: int = 0
    avg_duration_ms: float = 0.0
    stdev_duration_ms: float = 0.0


@dataclass
class TrendData:
    """
    Günlük/saatlik trend verisi
    """
    date: datetime
    executions: int = 0
    avg_duration_ms: float = 0.0
    avg_cpu_ms: float = 0.0
    avg_logical_reads: float = 0.0


@dataclass
class QueryMetrics:
    """
    Temel sorgu metrikleri (Section 24.4.1)
    """
    # Temel Metrikler
    avg_duration_ms: float = 0.0
    max_duration_ms: float = 0.0  # P95 yaklaşımı için max kullanılıyor
    avg_cpu_ms: float = 0.0
    avg_logical_reads: float = 0.0
    avg_logical_writes: float = 0.0
    avg_physical_reads: float = 0.0
    total_executions: int = 0
    plan_count: int = 1
    
    # Türetilmiş Skorlar (Section 24.4.2)
    impact_score: float = 0.0
    stability_score: float = 0.0
    io_bound_ratio: float = 0.0
    
    # Trend bilgisi
    trend_coefficient: float = 1.0  # >1 kötüleşme, <1 iyileşme
    change_percent: float = 0.0     # Yüzdelik değişim
    
    @property
    def p95_duration_ms(self) -> float:
        """P95 duration tahmini (max kullanılıyor)"""
        return self.max_duration_ms
    
    def calculate_impact_score(self) -> float:
        """
        Impact Score hesapla
        
        Formula: P95 Duration × Execution Count × Trend Katsayısı / 1000
        """
        self.impact_score = (
            self.p95_duration_ms * 
            self.total_executions * 
            self.trend_coefficient / 1000.0
        )
        return self.impact_score
    
    def calculate_stability_score(self, plan_change_count: int = 0, latency_variance: float = 0.0) -> float:
        """
        Stability Score hesapla
        
        Formula: 1 / (Plan Değişim Sayısı + Latency Varyansı)
        """
        denominator = plan_change_count + latency_variance
        if denominator <= 0:
            self.stability_score = 1.0
        else:
            self.stability_score = 1.0 / denominator
        return self.stability_score


@dataclass
class QueryStats:
    """
    Tam sorgu istatistikleri modeli
    
    Liste ve detay görünümlerinde kullanılır.
    """
    # Tanımlayıcılar
    query_id: int = 0
    query_hash: str = ""
    query_text: str = ""
    object_name: Optional[str] = None  # SP/Function adı
    schema_name: Optional[str] = None
    
    # Metrikler
    metrics: QueryMetrics = field(default_factory=QueryMetrics)
    
    # Wait profili
    wait_profile: List[WaitProfile] = field(default_factory=list)
    
    # Plan bilgisi
    plans: List[PlanInfo] = field(default_factory=list)
    
    # Trend verisi
    daily_trend: List[TrendData] = field(default_factory=list)
    
    # Zaman damgaları
    last_execution: Optional[datetime] = None
    first_compile_time: Optional[datetime] = None
    last_compile_time: Optional[datetime] = None
    
    @property
    def priority(self) -> QueryPriority:
        """
        Öncelik seviyesini hesapla (Section 24.6)
        
        Returns:
            QueryPriority enum değeri
        """
        impact = self.metrics.impact_score
        plan_count = self.metrics.plan_count
        change_percent = self.metrics.change_percent
        
        # Kritik: Impact > 90 veya Plan Count > 4
        if impact > 90 or plan_count > 4:
            return QueryPriority.CRITICAL
        
        # Yüksek: Impact 70-90 veya Trend > 30%
        if impact > 70 or change_percent > 30:
            return QueryPriority.HIGH
        
        # Orta: Impact 40-70 veya Plan Count 2-3
        if impact > 40 or plan_count in (2, 3):
            return QueryPriority.MEDIUM
        
        # Düşük: Impact < 40, stabil
        if impact > 0:
            return QueryPriority.LOW
        
        # Bilgi: Yeni sorgu, yetersiz veri
        return QueryPriority.INFO
    
    @property
    def plan_stability(self) -> PlanStability:
        """
        Plan stabilite durumunu hesapla
        
        Returns:
            PlanStability enum değeri
        """
        plan_count = self.metrics.plan_count
        
        if plan_count <= 1:
            return PlanStability.STABLE
        elif plan_count <= 3:
            return PlanStability.ATTENTION
        else:
            return PlanStability.PROBLEM
    
    @property
    def dominant_wait(self) -> Optional[WaitProfile]:
        """En yüksek wait kategorisini döndür"""
        if not self.wait_profile:
            return None
        return max(self.wait_profile, key=lambda w: w.wait_percent)
    
    @property
    def is_io_bound(self) -> bool:
        """IO-bound sorgu mu?"""
        dominant = self.dominant_wait
        if not dominant:
            return False
        return dominant.category in ("Buffer IO", "Other Disk IO", "Tran Log IO")
    
    @property
    def is_cpu_bound(self) -> bool:
        """CPU-bound sorgu mu?"""
        dominant = self.dominant_wait
        if not dominant:
            return False
        return dominant.category == "CPU"
    
    @property
    def display_name(self) -> str:
        """Gösterim adı"""
        if self.object_name:
            if self.schema_name:
                return f"{self.schema_name}.{self.object_name}"
            return self.object_name
        # Query text'in ilk 50 karakteri
        text = self.query_text.strip()[:50]
        return text + "..." if len(self.query_text) > 50 else text
    
    @property
    def trend_direction(self) -> str:
        """Trend yönü ikonu"""
        change = self.metrics.change_percent
        if change > 10:
            return "↑"  # Kötüleşme
        elif change < -10:
            return "↓"  # İyileşme
        return "→"  # Stabil
    
    def to_ai_context(self) -> Dict[str, Any]:
        """
        AI Engine için context JSON oluştur (Section 24.8)
        
        Returns:
            Section 17.6 formatına uygun dict
        """
        return {
            "query_stats_context": {
                "query_id": self.query_id,
                "query_hash": self.query_hash,
                
                "metrics": {
                    "avg_duration_ms": round(self.metrics.avg_duration_ms, 2),
                    "p95_duration_ms": round(self.metrics.p95_duration_ms, 2),
                    "avg_cpu_ms": round(self.metrics.avg_cpu_ms, 2),
                    "avg_logical_reads": round(self.metrics.avg_logical_reads, 0),
                    "execution_count": self.metrics.total_executions,
                    "plan_count": self.metrics.plan_count,
                },
                
                "trend": {
                    "duration_change_percent": round(self.metrics.change_percent, 2),
                    "direction": "increasing" if self.metrics.change_percent > 0 else "decreasing",
                    "regression_detected": self.metrics.change_percent > 30,
                },
                
                "wait_profile": {
                    w.category.lower().replace(" ", "_") + "_percent": round(w.wait_percent, 2)
                    for w in self.wait_profile[:5]  # Top 5 wait
                } if self.wait_profile else {},
                
                "stability": {
                    "plan_changes_7d": self.metrics.plan_count,
                    "latency_variance": round(1.0 / max(self.metrics.stability_score, 0.01), 2),
                    "param_sensitivity_suspected": self.plan_stability == PlanStability.PROBLEM,
                }
            }
        }


@dataclass
class QueryStoreStatus:
    """
    Query Store durumu
    """
    is_enabled: bool = False
    desired_state: str = ""
    actual_state: str = ""
    current_storage_mb: float = 0.0
    max_storage_mb: float = 0.0
    
    @property
    def is_operational(self) -> bool:
        """Query Store çalışıyor mu?"""
        return self.is_enabled and self.actual_state == "READ_WRITE"
    
    @property
    def storage_percent(self) -> float:
        """Depolama kullanım yüzdesi"""
        if self.max_storage_mb <= 0:
            return 0.0
        return (self.current_storage_mb / self.max_storage_mb) * 100


@dataclass
class QueryStatsFilter:
    """
    Query Stats filtreleme seçenekleri
    """
    time_range_days: int = 7
    sort_by: str = "impact_score"
    top_n: int = 50
    search_text: str = ""
    min_executions: int = 0
    min_duration_ms: float = 0.0
    object_name_filter: Optional[str] = None
    priority_filter: Optional[QueryPriority] = None
    
    def to_params(self) -> Dict[str, Any]:
        """SQL sorgu parametrelerine dönüştür"""
        return {
            "days": self.time_range_days,
            "sort_by": self.sort_by,
            "top_n": self.top_n,
        }
