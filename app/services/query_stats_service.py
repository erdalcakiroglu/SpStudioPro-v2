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

from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
from datetime import datetime

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

logger = get_logger('services.query_stats')


class QueryStatsService:
    """
    Query Stats iş mantığı servisi
    
    Kullanım:
        service = QueryStatsService()
        stats = service.get_top_queries(filter)
        detail = service.get_query_detail(query_id)
    """
    
    def __init__(self, connection: Optional['DatabaseConnection'] = None):
        """
        Args:
            connection: Veritabanı bağlantısı (None ise aktif bağlantı kullanılır)
        """
        self._connection = connection
        self._query_store_status: Optional[QueryStoreStatus] = None
        self._sql_version: Optional[int] = None
    
    @property
    def connection(self) -> Optional['DatabaseConnection']:
        """Aktif veritabanı bağlantısı"""
        if self._connection:
            return self._connection
        
        from app.database.connection import get_connection_manager
        conn_mgr = get_connection_manager()
        return conn_mgr.active_connection
    
    @property
    def is_connected(self) -> bool:
        """Bağlantı var mı?"""
        conn = self.connection
        return conn is not None and conn.is_connected
    
    def _get_sql_version(self) -> int:
        """SQL Server major version'ı al"""
        if self._sql_version is not None:
            return self._sql_version
        
        conn = self.connection
        if not conn or not conn.info:
            return 0
        
        self._sql_version = conn.info.major_version
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
    
    def check_query_store_status(self) -> QueryStoreStatus:
        """
        Query Store durumunu kontrol et
        
        Returns:
            QueryStoreStatus modeli
        """
        if not self.is_connected:
            logger.warning("No active connection for Query Store check")
            return QueryStoreStatus(is_enabled=False)
        
        if not self._supports_query_store():
            logger.info(f"SQL Server version {self._get_sql_version()} does not support Query Store")
            return QueryStoreStatus(is_enabled=False)
        
        try:
            conn = self.connection
            results = conn.execute_query(QueryStoreQueries.CHECK_QUERY_STORE_ENABLED)
            
            if not results:
                return QueryStoreStatus(is_enabled=False)
            
            row = results[0]
            status = QueryStoreStatus(
                is_enabled=bool(row.get('is_enabled', 0)),
                desired_state=str(row.get('desired_state_desc', '') or ''),
                actual_state=str(row.get('actual_state_desc', '') or ''),
                current_storage_mb=float(row.get('current_storage_size_mb', 0) or 0),
                max_storage_mb=float(row.get('max_storage_size_mb', 0) or 0),
            )
            
            self._query_store_status = status
            logger.info(f"Query Store status: enabled={status.is_enabled}, state={status.actual_state}")
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to check Query Store status: {e}")
            return QueryStoreStatus(is_enabled=False)
    
    def use_query_store(self) -> bool:
        """Query Store kullanılmalı mı?"""
        if self._query_store_status is None:
            self.check_query_store_status()
        
        return (
            self._query_store_status is not None and 
            self._query_store_status.is_operational
        )
    
    # ==========================================================================
    # TOP QUERIES (LİSTE GÖRÜNÜMÜ)
    # ==========================================================================
    
    def get_top_queries(
        self, 
        filter: Optional[QueryStatsFilter] = None
    ) -> List[QueryStats]:
        """
        En yavaş/etkili sorguları getir
        
        Args:
            filter: Filtreleme seçenekleri
        
        Returns:
            QueryStats listesi
        """
        if not self.is_connected:
            logger.warning("No active connection")
            return []
        
        filter = filter or QueryStatsFilter()
        use_qs = self.use_query_store()
        
        try:
            # Sorguyu seç
            sql = QueryStoreQueries.get_top_queries_sql(use_query_store=use_qs)
            
            # Parametreleri hazırla
            params = filter.to_params()
            
            logger.info(f"Fetching top queries (Query Store: {use_qs}, days: {params['days']})")
            
            conn = self.connection
            results = conn.execute_query(sql, params)
            
            if not results:
                logger.info("No queries found")
                return []
            
            # Sonuçları modele dönüştür
            queries = []
            for row in results:
                query_stats = self._row_to_query_stats(row, use_qs)
                
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
            
            logger.info(f"Found {len(queries)} queries")
            return queries
            
        except Exception as e:
            logger.error(f"Failed to get top queries: {e}")
            return []
    
    def _row_to_query_stats(self, row: Dict[str, Any], is_query_store: bool) -> QueryStats:
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
            query_text=str(row.get('query_text', '') or ''),
            object_name=row.get('object_name'),
            schema_name=row.get('schema_name'),
            metrics=metrics,
            last_execution=row.get('last_execution'),
        )
    
    # ==========================================================================
    # SORGU DETAYI
    # ==========================================================================
    
    def get_query_detail(self, query_id: int, days: int = 7) -> Optional[QueryStats]:
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
            conn = self.connection
            
            # Temel bilgileri al
            detail_result = conn.execute_query(
                QueryStoreQueries.QUERY_DETAIL,
                {"query_id": query_id}
            )
            
            if not detail_result:
                return None
            
            row = detail_result[0]
            
            # QueryStats oluştur
            query_stats = QueryStats(
                query_id=query_id,
                query_hash=str(row.get('query_hash', '') or ''),
                query_text=str(row.get('query_text', '') or ''),
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
            conn = self.connection
            results = conn.execute_query(sql, {"query_id": query_id, "days": days})
            
            if not results:
                return QueryMetrics()
            
            row = results[0]
            return QueryMetrics(
                avg_duration_ms=float(row.get('avg_duration_ms', 0) or 0),
                max_duration_ms=float(row.get('max_duration_ms', 0) or 0),
                avg_cpu_ms=float(row.get('avg_cpu_ms', 0) or 0),
                avg_logical_reads=float(row.get('avg_logical_reads', 0) or 0),
                avg_logical_writes=float(row.get('avg_logical_writes', 0) or 0),
                avg_physical_reads=float(row.get('avg_physical_reads', 0) or 0),
                total_executions=int(row.get('total_executions', 0) or 0),
                plan_count=int(row.get('plan_count', 1) or 1),
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
            conn = self.connection
            results = conn.execute_query(
                QueryStoreQueries.QUERY_WAIT_STATS,
                {"query_id": query_id, "days": days}
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
            conn = self.connection
            results = conn.execute_query(QueryStoreQueries.DMV_WAIT_STATS)
            
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
            conn = self.connection
            results = conn.execute_query(
                QueryStoreQueries.QUERY_PLAN_STABILITY,
                {"query_id": query_id, "days": days}
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
            conn = self.connection
            results = conn.execute_query(
                QueryStoreQueries.QUERY_DAILY_TREND,
                {"query_id": query_id, "days": days}
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
            conn = self.connection
            results = conn.execute_query(
                QueryStoreQueries.QUERY_TREND_COMPARISON,
                {"query_id": query_id}
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
    
    def get_query_text(self, query_id: int) -> Optional[str]:
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
            conn = self.connection
            results = conn.execute_query(
                QueryStoreQueries.QUERY_DETAIL,
                {"query_id": query_id}
            )
            
            if not results:
                return None
            
            row = results[0]
            return row.get('query_text')
            
        except Exception as e:
            logger.error(f"Failed to get query text for query {query_id}: {e}")
            return None

    def get_object_definition(self, object_name: str, schema_name: Optional[str] = None) -> Optional[str]:
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
            conn = self.connection
            results = conn.execute_query(query, {"object_name": object_name, "schema_name": schema_name})
            if not results:
                return None
            return results[0].get('definition')
        except Exception as e:
            logger.error(f"Failed to get object definition for {schema_name}.{object_name}: {e}")
            return None
    
    # ==========================================================================
    # EXECUTION PLAN
    # ==========================================================================
    
    def get_query_plan_xml(self, query_id: int) -> Optional[str]:
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
            logger.debug(f"Fetching plan XML for query_id: {query_id}")
            conn = self.connection
            results = conn.execute_query(
                QueryStoreQueries.QUERY_PLAN_XML,
                {"query_id": query_id}
            )
            
            if not results:
                logger.debug(f"No plan found for query_id: {query_id}")
                return None
            
            # En çok kullanılan planı döndür
            row = results[0]
            plan_xml = row.get('query_plan_xml')
            if plan_xml:
                logger.debug(f"Got plan XML for query_id {query_id}: {len(plan_xml)} chars")
            return plan_xml
            
        except Exception as e:
            logger.error(f"Failed to get plan XML for query {query_id}: {e}")
            return None
    
    def get_plan_xml_by_id(self, plan_id: int) -> Optional[str]:
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
            conn = self.connection
            results = conn.execute_query(
                QueryStoreQueries.SINGLE_PLAN_XML,
                {"plan_id": plan_id}
            )
            
            if not results:
                return None
            
            return results[0].get('query_plan_xml')
            
        except Exception as e:
            logger.error(f"Failed to get plan XML for plan {plan_id}: {e}")
            return None
    
    # ==========================================================================
    # REFRESH / CACHE
    # ==========================================================================
    
    def refresh(self) -> None:
        """Cache'i temizle ve durumu yeniden kontrol et"""
        self._query_store_status = None
        self._sql_version = None
        self.check_query_store_status()
