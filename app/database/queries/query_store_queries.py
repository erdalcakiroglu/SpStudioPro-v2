"""
Query Store SQL Templates for Query Stats Module

Bu modül Query Store'dan performans verisi çeken SQL şablonlarını içerir.
SQL Server 2016+ (Query Store) ve eski sürümler için DMV fallback destekler.

Referans: Section 24.9 - Query Store Sorguları
"""

from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum


class TimeRange(str, Enum):
    """Zaman aralığı seçenekleri"""
    LAST_24H = "24h"
    LAST_7D = "7d"
    LAST_30D = "30d"
    CUSTOM = "custom"
    
    @property
    def days(self) -> int:
        """Gün sayısını döndür"""
        mapping = {
            "24h": 1,
            "7d": 7,
            "30d": 30,
            "custom": 7,  # default
        }
        return mapping.get(self.value, 7)


class SortOption(str, Enum):
    """Sıralama seçenekleri"""
    IMPACT_SCORE = "impact_score"
    AVG_DURATION = "avg_duration"
    TOTAL_CPU = "total_cpu"
    EXECUTION_COUNT = "execution_count"
    LOGICAL_READS = "logical_reads"


@dataclass
class QueryTemplate:
    """SQL sorgu şablonu"""
    name: str
    description: str
    min_version: int  # Minimum SQL Server major version
    sql: str
    parameters: list


class QueryStoreQueries:
    """
    Query Store ve DMV sorgularını yöneten sınıf.
    
    Temel Prensipler:
    - Query Store aktifse birincil veri kaynağı olarak kullan
    - SQL Server 2016 öncesi için DMV fallback
    - Tüm sorgular parametreli (SQL injection koruması)
    """
    
    # ==========================================================================
    # QUERY STORE KONTROL SORGULARI
    # ==========================================================================
    
    CHECK_QUERY_STORE_ENABLED = """
    SELECT 
        CAST(d.is_query_store_on AS INT) AS is_enabled,
        qso.desired_state_desc,
        qso.actual_state_desc,
        qso.current_storage_size_mb,
        qso.max_storage_size_mb
    FROM sys.databases d
    CROSS JOIN sys.database_query_store_options qso
    WHERE d.name = DB_NAME()
    """
    
    # ==========================================================================
    # ANA SORGULAR - QUERY STORE (SQL Server 2016+)
    # ==========================================================================
    
    # Top N yavaş sorgu (Impact Score ile)
    TOP_QUERIES_BY_DURATION = """
    WITH QueryMetrics AS (
        SELECT 
            q.query_id,
            q.query_hash,
            CAST(qt.query_sql_text AS NVARCHAR(MAX)) AS query_text,
            OBJECT_NAME(q.object_id) AS object_name,
            OBJECT_SCHEMA_NAME(q.object_id) AS schema_name,
            COUNT(DISTINCT p.plan_id) AS plan_count,
            SUM(rs.count_executions) AS total_executions,
            AVG(rs.avg_duration) / 1000.0 AS avg_duration_ms,
            AVG(rs.avg_cpu_time) / 1000.0 AS avg_cpu_ms,
            AVG(rs.avg_logical_io_reads) AS avg_logical_reads,
            AVG(rs.avg_logical_io_writes) AS avg_logical_writes,
            AVG(rs.avg_physical_io_reads) AS avg_physical_reads,
            MAX(rs.last_execution_time) AS last_execution,
            -- P95 Duration yaklaşık hesabı
            MAX(rs.max_duration) / 1000.0 AS max_duration_ms
        FROM sys.query_store_query q
        JOIN sys.query_store_query_text qt ON q.query_text_id = qt.query_text_id
        JOIN sys.query_store_plan p ON q.query_id = p.query_id
        JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
        JOIN sys.query_store_runtime_stats_interval rsi 
            ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
        WHERE rsi.start_time > DATEADD(day, -:days, GETDATE())
        GROUP BY q.query_id, q.query_hash, CAST(qt.query_sql_text AS NVARCHAR(MAX)), q.object_id
    )
    SELECT TOP (:top_n)
        query_id,
        query_hash,
        query_text,
        object_name,
        schema_name,
        plan_count,
        total_executions,
        avg_duration_ms,
        avg_cpu_ms,
        avg_logical_reads,
        avg_logical_writes,
        avg_physical_reads,
        last_execution,
        max_duration_ms,
        -- Impact Score = P95 Duration × Execution Count / 1000
        (max_duration_ms * total_executions / 1000.0) AS impact_score
    FROM QueryMetrics
    ORDER BY 
        CASE :sort_by
            WHEN 'impact_score' THEN (max_duration_ms * total_executions / 1000.0)
            WHEN 'avg_duration' THEN avg_duration_ms
            WHEN 'total_cpu' THEN avg_cpu_ms * total_executions
            WHEN 'execution_count' THEN total_executions
            WHEN 'logical_reads' THEN avg_logical_reads
            ELSE (max_duration_ms * total_executions / 1000.0)
        END DESC
    """
    
    # Sorgu bazlı Wait İstatistikleri (SQL Server 2017+)
    QUERY_WAIT_STATS = """
    SELECT 
        ws.wait_category_desc AS wait_category,
        SUM(ws.total_query_wait_time_ms) AS total_wait_ms,
        CAST(SUM(ws.total_query_wait_time_ms) * 100.0 / 
            NULLIF(SUM(SUM(ws.total_query_wait_time_ms)) OVER(), 0) AS DECIMAL(5,2)) AS wait_percent
    FROM sys.query_store_wait_stats ws
    JOIN sys.query_store_runtime_stats_interval rsi 
        ON ws.runtime_stats_interval_id = rsi.runtime_stats_interval_id
    JOIN sys.query_store_plan p ON ws.plan_id = p.plan_id
    WHERE p.query_id = :query_id
      AND rsi.start_time > DATEADD(day, -:days, GETDATE())
    GROUP BY ws.wait_category_desc
    ORDER BY total_wait_ms DESC
    """
    
    # Plan Stability Analizi
    QUERY_PLAN_STABILITY = """
    SELECT 
        p.plan_id,
        p.query_plan_hash,
        p.is_forced_plan,
        p.force_failure_count,
        MIN(rs.first_execution_time) AS first_seen,
        MAX(rs.last_execution_time) AS last_seen,
        SUM(rs.count_executions) AS execution_count,
        AVG(rs.avg_duration) / 1000.0 AS avg_duration_ms,
        STDEV(rs.avg_duration) / 1000.0 AS stdev_duration_ms
    FROM sys.query_store_plan p
    JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
    JOIN sys.query_store_runtime_stats_interval rsi 
        ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
    WHERE p.query_id = :query_id
      AND rsi.start_time > DATEADD(day, -:days, GETDATE())
    GROUP BY p.plan_id, p.query_plan_hash, p.is_forced_plan, p.force_failure_count
    ORDER BY execution_count DESC
    """
    
    # Günlük Trend Verisi
    QUERY_DAILY_TREND = """
    SELECT 
        CAST(rsi.start_time AS DATE) AS trend_date,
        SUM(rs.count_executions) AS daily_executions,
        AVG(rs.avg_duration) / 1000.0 AS avg_duration_ms,
        AVG(rs.avg_cpu_time) / 1000.0 AS avg_cpu_ms,
        AVG(rs.avg_logical_io_reads) AS avg_logical_reads
    FROM sys.query_store_plan p
    JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
    JOIN sys.query_store_runtime_stats_interval rsi 
        ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
    WHERE p.query_id = :query_id
      AND rsi.start_time > DATEADD(day, -:days, GETDATE())
    GROUP BY CAST(rsi.start_time AS DATE)
    ORDER BY trend_date
    """
    
    # Sorgu Detayı
    QUERY_DETAIL = """
    SELECT 
        q.query_id,
        q.query_hash,
        CAST(qt.query_sql_text AS NVARCHAR(MAX)) AS query_text,
        OBJECT_NAME(q.object_id) AS object_name,
        OBJECT_SCHEMA_NAME(q.object_id) AS schema_name,
        q.initial_compile_start_time,
        q.last_compile_start_time,
        q.last_execution_time,
        q.avg_compile_duration / 1000.0 AS avg_compile_duration_ms,
        q.count_compiles,
        q.avg_bind_duration / 1000.0 AS avg_bind_duration_ms,
        q.avg_optimize_duration / 1000.0 AS avg_optimize_duration_ms
    FROM sys.query_store_query q
    JOIN sys.query_store_query_text qt ON q.query_text_id = qt.query_text_id
    WHERE q.query_id = :query_id
    """
    
    # ==========================================================================
    # FALLBACK SORGULAR - DMV (Eski SQL Server sürümleri için)
    # ==========================================================================
    
    # DMV tabanlı top queries (Query Store yoksa)
    # NOT: Object_name'e göre gruplandı - aynı SP'nin tüm statement'ları tek satırda
    DMV_TOP_QUERIES = """
    WITH QueryStats AS (
        SELECT 
            COALESCE(OBJECT_NAME(st.objectid, st.dbid), 
                     LEFT(SUBSTRING(st.text, (qs.statement_start_offset/2) + 1, 100), 80)) AS object_name,
            OBJECT_SCHEMA_NAME(st.objectid, st.dbid) AS schema_name,
            st.objectid,
            st.dbid,
            qs.execution_count,
            qs.total_elapsed_time,
            qs.total_worker_time,
            qs.total_logical_reads,
            qs.total_logical_writes,
            qs.total_physical_reads,
            qs.last_execution_time,
            qs.max_elapsed_time,
            qs.query_hash
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        WHERE qs.last_execution_time > DATEADD(day, -:days, GETDATE())
          AND st.text NOT LIKE '%sys.%'
          AND st.dbid = DB_ID()
    )
    SELECT TOP (:top_n)
        MIN(query_hash) AS query_hash,
        object_name AS query_text,
        object_name,
        schema_name,
        DB_NAME() AS database_name,
        SUM(execution_count) AS total_executions,
        SUM(total_elapsed_time / 1000.0) / NULLIF(SUM(execution_count), 0) AS avg_duration_ms,
        SUM(total_worker_time / 1000.0) / NULLIF(SUM(execution_count), 0) AS avg_cpu_ms,
        SUM(total_logical_reads) / NULLIF(SUM(execution_count), 0) AS avg_logical_reads,
        SUM(total_logical_writes) / NULLIF(SUM(execution_count), 0) AS avg_logical_writes,
        SUM(total_physical_reads) / NULLIF(SUM(execution_count), 0) AS avg_physical_reads,
        MAX(last_execution_time) AS last_execution,
        MAX(max_elapsed_time / 1000.0) AS max_duration_ms,
        COUNT(DISTINCT query_hash) AS plan_count,
        -- Impact Score: Max Duration × Total Executions / 1000
        (MAX(max_elapsed_time / 1000.0) * SUM(execution_count) / 1000.0) AS impact_score
    FROM QueryStats
    WHERE object_name IS NOT NULL
    GROUP BY object_name, schema_name
    ORDER BY 
        CASE :sort_by
            WHEN 'impact_score' THEN (MAX(max_elapsed_time / 1000.0) * SUM(execution_count) / 1000.0)
            WHEN 'avg_duration' THEN SUM(total_elapsed_time / 1000.0) / NULLIF(SUM(execution_count), 0)
            WHEN 'total_cpu' THEN SUM(total_worker_time)
            WHEN 'execution_count' THEN SUM(execution_count)
            WHEN 'logical_reads' THEN SUM(total_logical_reads)
            ELSE (MAX(max_elapsed_time / 1000.0) * SUM(execution_count) / 1000.0)
        END DESC
    """
    
    # DMV tabanlı wait stats (sunucu geneli)
    DMV_WAIT_STATS = """
    SELECT TOP 10
        wait_type AS wait_category,
        wait_time_ms AS total_wait_ms,
        CAST(wait_time_ms * 100.0 / NULLIF(SUM(wait_time_ms) OVER(), 0) AS DECIMAL(5,2)) AS wait_percent
    FROM sys.dm_os_wait_stats
    WHERE wait_type NOT IN (
        'SLEEP_TASK', 'BROKER_EVENTHANDLER', 'BROKER_RECEIVE_WAITFOR',
        'BROKER_TASK_STOP', 'BROKER_TO_FLUSH', 'BROKER_TRANSMITTER',
        'CHECKPOINT_QUEUE', 'CHKPT', 'CLR_AUTO_EVENT', 'CLR_MANUAL_EVENT',
        'CLR_SEMAPHORE', 'DBMIRROR_DBM_EVENT', 'DBMIRROR_EVENTS_QUEUE',
        'DBMIRROR_WORKER_QUEUE', 'DBMIRRORING_CMD', 'DIRTY_PAGE_POLL',
        'DISPATCHER_QUEUE_SEMAPHORE', 'EXECSYNC', 'FSAGENT',
        'FT_IFTS_SCHEDULER_IDLE_WAIT', 'FT_IFTSHC_MUTEX', 'HADR_CLUSAPI_CALL',
        'HADR_FILESTREAM_IOMGR_IOCOMPLETION', 'HADR_LOGCAPTURE_WAIT',
        'HADR_NOTIFICATION_DEQUEUE', 'HADR_TIMER_TASK', 'HADR_WORK_QUEUE',
        'KSOURCE_WAKEUP', 'LAZYWRITER_SLEEP', 'LOGMGR_QUEUE',
        'MEMORY_ALLOCATION_EXT', 'ONDEMAND_TASK_QUEUE',
        'PREEMPTIVE_XE_GETTARGETSTATE', 'PWAIT_ALL_COMPONENTS_INITIALIZED',
        'PWAIT_DIRECTLOGCONSUMER_GETNEXT', 'QDS_PERSIST_TASK_MAIN_LOOP_SLEEP',
        'QDS_ASYNC_QUEUE', 'QDS_CLEANUP_STALE_QUERIES_TASK_MAIN_LOOP_SLEEP',
        'QDS_SHUTDOWN_QUEUE', 'REDO_THREAD_PENDING_WORK', 'REQUEST_FOR_DEADLOCK_SEARCH',
        'RESOURCE_QUEUE', 'SERVER_IDLE_CHECK', 'SLEEP_BPOOL_FLUSH', 'SLEEP_DBSTARTUP',
        'SLEEP_DCOMSTARTUP', 'SLEEP_MASTERDBREADY', 'SLEEP_MASTERMDREADY',
        'SLEEP_MASTERUPGRADED', 'SLEEP_MSDBSTARTUP', 'SLEEP_SYSTEMTASK', 'SLEEP_TASK',
        'SLEEP_TEMPDBSTARTUP', 'SNI_HTTP_ACCEPT', 'SP_SERVER_DIAGNOSTICS_SLEEP',
        'SQLTRACE_BUFFER_FLUSH', 'SQLTRACE_INCREMENTAL_FLUSH_SLEEP',
        'SQLTRACE_WAIT_ENTRIES', 'WAIT_FOR_RESULTS', 'WAITFOR',
        'WAITFOR_TASKSHUTDOWN', 'WAIT_XTP_RECOVERY',
        'WAIT_XTP_HOST_WAIT', 'WAIT_XTP_OFFLINE_CKPT_NEW_LOG',
        'WAIT_XTP_CKPT_CLOSE', 'XE_DISPATCHER_JOIN', 'XE_DISPATCHER_WAIT',
        'XE_TIMER_EVENT'
    )
    AND wait_time_ms > 0
    ORDER BY wait_time_ms DESC
    """
    
    # ==========================================================================
    # TREND HESAPLAMA SORGULARI
    # ==========================================================================
    
    # Son 7 gün vs önceki 7 gün karşılaştırması (Trend Katsayısı için)
    QUERY_TREND_COMPARISON = """
    WITH RecentStats AS (
        SELECT 
            p.query_id,
            AVG(rs.avg_duration) AS recent_avg_duration,
            SUM(rs.count_executions) AS recent_executions
        FROM sys.query_store_plan p
        JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
        JOIN sys.query_store_runtime_stats_interval rsi 
            ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
        WHERE rsi.start_time > DATEADD(day, -7, GETDATE())
        GROUP BY p.query_id
    ),
    PreviousStats AS (
        SELECT 
            p.query_id,
            AVG(rs.avg_duration) AS previous_avg_duration,
            SUM(rs.count_executions) AS previous_executions
        FROM sys.query_store_plan p
        JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
        JOIN sys.query_store_runtime_stats_interval rsi 
            ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
        WHERE rsi.start_time BETWEEN DATEADD(day, -14, GETDATE()) AND DATEADD(day, -7, GETDATE())
        GROUP BY p.query_id
    )
    SELECT 
        r.query_id,
        r.recent_avg_duration / 1000.0 AS recent_avg_ms,
        ISNULL(p.previous_avg_duration, r.recent_avg_duration) / 1000.0 AS previous_avg_ms,
        CASE 
            WHEN p.previous_avg_duration IS NULL OR p.previous_avg_duration = 0 THEN 1.0
            ELSE r.recent_avg_duration / p.previous_avg_duration
        END AS trend_coefficient,
        CASE 
            WHEN p.previous_avg_duration IS NULL THEN 0
            WHEN p.previous_avg_duration = 0 THEN 0
            ELSE CAST((r.recent_avg_duration - p.previous_avg_duration) * 100.0 / p.previous_avg_duration AS DECIMAL(10,2))
        END AS change_percent
    FROM RecentStats r
    LEFT JOIN PreviousStats p ON r.query_id = p.query_id
    WHERE r.query_id = :query_id
    """
    
    # ==========================================================================
    # EXECUTION PLAN SORGULARI
    # ==========================================================================
    
    # Query Store'dan plan XML'i al
    QUERY_PLAN_XML = """
    SELECT 
        p.plan_id,
        p.query_id,
        p.query_plan_hash,
        p.is_forced_plan,
        p.is_natively_compiled,
        p.force_failure_count,
        p.last_force_failure_reason_desc,
        CAST(p.query_plan AS NVARCHAR(MAX)) AS query_plan_xml,
        p.plan_group_id,
        MIN(rs.first_execution_time) AS first_execution_time,
        MAX(rs.last_execution_time) AS last_execution_time,
        SUM(rs.count_executions) AS total_executions,
        AVG(rs.avg_duration) / 1000.0 AS avg_duration_ms,
        AVG(rs.avg_cpu_time) / 1000.0 AS avg_cpu_ms,
        AVG(rs.avg_logical_io_reads) AS avg_logical_reads
    FROM sys.query_store_plan p
    LEFT JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
    WHERE p.query_id = :query_id
    GROUP BY p.plan_id, p.query_id, p.query_plan_hash, p.is_forced_plan,
             p.is_natively_compiled, p.force_failure_count, 
             p.last_force_failure_reason_desc, CAST(p.query_plan AS NVARCHAR(MAX)),
             p.plan_group_id
    ORDER BY total_executions DESC
    """
    
    # Tek plan için XML (plan_id ile)
    SINGLE_PLAN_XML = """
    SELECT 
        p.plan_id,
        p.query_id,
        p.query_plan_hash,
        CAST(p.query_plan AS NVARCHAR(MAX)) AS query_plan_xml,
        p.is_forced_plan,
        p.is_natively_compiled
    FROM sys.query_store_plan p
    WHERE p.plan_id = :plan_id
    """
    
    # DMV'den execution plan (Query Store yoksa veya cached plan için)
    DMV_CACHED_PLAN = """
    SELECT TOP 1
        qs.plan_handle,
        qs.query_hash,
        qs.query_plan_hash,
        CAST(qp.query_plan AS NVARCHAR(MAX)) AS query_plan_xml,
        qs.execution_count,
        qs.total_elapsed_time / 1000.0 AS total_duration_ms,
        qs.total_worker_time / 1000.0 AS total_cpu_ms,
        qs.total_logical_reads,
        qs.creation_time,
        qs.last_execution_time
    FROM sys.dm_exec_query_stats qs
    CROSS APPLY sys.dm_exec_query_plan(qs.plan_handle) qp
    WHERE qs.query_hash = :query_hash
    ORDER BY qs.last_execution_time DESC
    """
    
    # Nesne (SP/Function) için plan
    DMV_OBJECT_PLAN = """
    SELECT 
        p.plan_handle,
        p.objtype,
        p.usecounts,
        p.size_in_bytes,
        CAST(qp.query_plan AS NVARCHAR(MAX)) AS query_plan_xml,
        st.text AS query_text,
        p.cacheobjtype
    FROM sys.dm_exec_cached_plans p
    CROSS APPLY sys.dm_exec_query_plan(p.plan_handle) qp
    CROSS APPLY sys.dm_exec_sql_text(p.plan_handle) st
    WHERE p.objtype IN ('Proc', 'Prepared', 'Adhoc')
      AND st.objectid = OBJECT_ID(:object_name)
    ORDER BY p.usecounts DESC
    """
    
    # Plan operatör istatistikleri (Query Store 2017+)
    PLAN_OPERATOR_STATS = """
    SELECT 
        p.plan_id,
        p.query_id,
        AVG(rs.avg_rowcount) AS avg_rowcount,
        AVG(rs.avg_query_max_used_memory) AS avg_memory_grant_kb,
        AVG(rs.avg_tempdb_space_used) AS avg_tempdb_kb,
        MAX(rs.max_rowcount) AS max_rowcount,
        MAX(rs.max_query_max_used_memory) AS max_memory_grant_kb,
        MAX(rs.max_tempdb_space_used) AS max_tempdb_kb
    FROM sys.query_store_plan p
    JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
    WHERE p.plan_id = :plan_id
    GROUP BY p.plan_id, p.query_id
    """
    
    # ==========================================================================
    # YARDIMCI METODLAR
    # ==========================================================================
    
    @classmethod
    def get_top_queries_sql(cls, use_query_store: bool = True) -> str:
        """
        Top queries sorgusunu döndür.
        
        Args:
            use_query_store: Query Store kullanılsın mı?
        
        Returns:
            SQL sorgu string'i
        """
        if use_query_store:
            return cls.TOP_QUERIES_BY_DURATION
        return cls.DMV_TOP_QUERIES
    
    @classmethod
    def get_wait_stats_sql(cls, use_query_store: bool = True, has_wait_stats: bool = True) -> str:
        """
        Wait stats sorgusunu döndür.
        
        Args:
            use_query_store: Query Store kullanılsın mı?
            has_wait_stats: Query Store Wait Stats var mı? (SQL 2017+)
        
        Returns:
            SQL sorgu string'i
        """
        if use_query_store and has_wait_stats:
            return cls.QUERY_WAIT_STATS
        return cls.DMV_WAIT_STATS


# Wait kategorileri için mapping (UI'da kullanılacak)
WAIT_CATEGORY_MAPPING = {
    # Query Store wait kategorileri
    "Unknown": {"display": "Unknown", "color": "#888888", "icon": "❓"},
    "CPU": {"display": "CPU", "color": "#ef4444", "icon": "⚡"},
    "Worker Thread": {"display": "Worker Thread", "color": "#f97316", "icon": "👷"},
    "Lock": {"display": "Lock", "color": "#eab308", "icon": "🔒"},
    "Latch": {"display": "Latch", "color": "#84cc16", "icon": "🔄"},
    "Buffer Latch": {"display": "Buffer Latch", "color": "#22c55e", "icon": "📦"},
    "Buffer IO": {"display": "Buffer IO", "color": "#14b8a6", "icon": "💾"},
    "Compilation": {"display": "Compilation", "color": "#06b6d4", "icon": "🔨"},
    "SQL CLR": {"display": "SQL CLR", "color": "#0ea5e9", "icon": "🔷"},
    "Mirroring": {"display": "Mirroring", "color": "#3b82f6", "icon": "🪞"},
    "Transaction": {"display": "Transaction", "color": "#6366f1", "icon": "📋"},
    "Idle": {"display": "Idle", "color": "#8b5cf6", "icon": "😴"},
    "Preemptive": {"display": "Preemptive", "color": "#a855f7", "icon": "⏸️"},
    "Service Broker": {"display": "Service Broker", "color": "#d946ef", "icon": "📨"},
    "Tran Log IO": {"display": "Tran Log IO", "color": "#ec4899", "icon": "📝"},
    "Network IO": {"display": "Network IO", "color": "#f43f5e", "icon": "🌐"},
    "Parallelism": {"display": "Parallelism", "color": "#fb7185", "icon": "🔀"},
    "Memory": {"display": "Memory", "color": "#fda4af", "icon": "🧠"},
    "User Wait": {"display": "User Wait", "color": "#fecaca", "icon": "👤"},
    "Tracing": {"display": "Tracing", "color": "#fed7aa", "icon": "📊"},
    "Full Text Search": {"display": "Full Text Search", "color": "#fef08a", "icon": "🔍"},
    "Other Disk IO": {"display": "Other Disk IO", "color": "#bef264", "icon": "💿"},
    "Replication": {"display": "Replication", "color": "#86efac", "icon": "🔁"},
    "Log Rate Governor": {"display": "Log Rate Governor", "color": "#6ee7b7", "icon": "⚖️"},
}

# Öncelik renk kodları (Section 24.6)
PRIORITY_COLORS = {
    "critical": {"color": "#ef4444", "icon": "🔴", "label": "Kritik"},
    "high": {"color": "#f97316", "icon": "🟠", "label": "Yüksek"},
    "medium": {"color": "#eab308", "icon": "🟡", "label": "Orta"},
    "low": {"color": "#22c55e", "icon": "🟢", "label": "Düşük"},
    "info": {"color": "#6b7280", "icon": "⚪", "label": "Bilgi"},
}
