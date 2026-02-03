"""
Query Template Library - 50+ Hazır SQL Template

DBA ve performans analizi için sık kullanılan SQL sorguları.
Intent Detection System ile entegre çalışır.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.ai.intent_detector import Intent


@dataclass
class QueryTemplate:
    """SQL Query Template"""
    id: str
    name: str
    description: str
    category: str
    sql: str
    parameters: List[str] = None
    tags: List[str] = None
    intent: Intent = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.tags is None:
            self.tags = []


class TemplateCategory(Enum):
    """Query template categories"""
    PERFORMANCE = "performance"
    WAIT_STATS = "wait_stats"
    BLOCKING = "blocking"
    INDEX = "index"
    SERVER_HEALTH = "server_health"
    DATABASE = "database"
    SECURITY = "security"
    JOBS = "jobs"
    BACKUP = "backup"
    TEMPDB = "tempdb"
    OBJECTS = "objects"
    MAINTENANCE = "maintenance"


# ═══════════════════════════════════════════════════════════════════════════
# QUERY TEMPLATES - 50+ Hazır Sorgu
# ═══════════════════════════════════════════════════════════════════════════

QUERY_TEMPLATES: List[QueryTemplate] = [
    
    # ═══════════════════════════════════════════════════════════
    # PERFORMANCE QUERIES (1-10)
    # ═══════════════════════════════════════════════════════════
    
    QueryTemplate(
        id="perf_001",
        name="Top 10 CPU Intensive Queries",
        description="En çok CPU kullanan 10 sorguyu listeler",
        category=TemplateCategory.PERFORMANCE.value,
        intent=Intent.CPU_INTENSIVE,
        tags=["cpu", "performance", "top"],
        sql="""
SELECT TOP 10
    SUBSTRING(st.text, (qs.statement_start_offset/2)+1, 
        ((CASE qs.statement_end_offset
            WHEN -1 THEN DATALENGTH(st.text)
            ELSE qs.statement_end_offset
        END - qs.statement_start_offset)/2)+1) AS query_text,
    qs.total_worker_time / 1000 AS total_cpu_ms,
    qs.execution_count,
    qs.total_worker_time / qs.execution_count / 1000 AS avg_cpu_ms,
    qs.last_execution_time
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
ORDER BY qs.total_worker_time DESC;
"""
    ),
    
    QueryTemplate(
        id="perf_002",
        name="Top 10 IO Intensive Queries",
        description="En çok I/O yapan 10 sorguyu listeler",
        category=TemplateCategory.PERFORMANCE.value,
        intent=Intent.IO_INTENSIVE,
        tags=["io", "performance", "logical reads"],
        sql="""
SELECT TOP 10
    SUBSTRING(st.text, (qs.statement_start_offset/2)+1, 
        ((CASE qs.statement_end_offset
            WHEN -1 THEN DATALENGTH(st.text)
            ELSE qs.statement_end_offset
        END - qs.statement_start_offset)/2)+1) AS query_text,
    qs.total_logical_reads,
    qs.total_physical_reads,
    qs.execution_count,
    qs.total_logical_reads / qs.execution_count AS avg_logical_reads,
    qs.last_execution_time
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
ORDER BY qs.total_logical_reads DESC;
"""
    ),
    
    QueryTemplate(
        id="perf_003",
        name="Top 10 Slowest Queries",
        description="En yavaş çalışan 10 sorguyu listeler",
        category=TemplateCategory.PERFORMANCE.value,
        intent=Intent.SLOW_QUERIES,
        tags=["slow", "duration", "performance"],
        sql="""
SELECT TOP 10
    SUBSTRING(st.text, (qs.statement_start_offset/2)+1, 
        ((CASE qs.statement_end_offset
            WHEN -1 THEN DATALENGTH(st.text)
            ELSE qs.statement_end_offset
        END - qs.statement_start_offset)/2)+1) AS query_text,
    qs.total_elapsed_time / 1000 AS total_duration_ms,
    qs.execution_count,
    qs.total_elapsed_time / qs.execution_count / 1000 AS avg_duration_ms,
    qs.last_execution_time
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
WHERE qs.execution_count > 0
ORDER BY avg_duration_ms DESC;
"""
    ),
    
    QueryTemplate(
        id="perf_004",
        name="Most Frequently Executed Queries",
        description="En sık çalıştırılan sorguları listeler",
        category=TemplateCategory.PERFORMANCE.value,
        intent=Intent.FREQUENT_QUERIES,
        tags=["frequent", "execution", "count"],
        sql="""
SELECT TOP 20
    SUBSTRING(st.text, 1, 200) AS query_text,
    qs.execution_count,
    qs.total_elapsed_time / 1000 AS total_ms,
    qs.total_worker_time / 1000 AS total_cpu_ms,
    qs.total_logical_reads,
    qs.last_execution_time
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
ORDER BY qs.execution_count DESC;
"""
    ),
    
    QueryTemplate(
        id="perf_005",
        name="Currently Running Queries",
        description="Şu anda çalışan sorguları gösterir",
        category=TemplateCategory.PERFORMANCE.value,
        intent=Intent.LONG_RUNNING,
        tags=["running", "active", "current"],
        sql="""
SELECT 
    r.session_id,
    r.status,
    r.start_time,
    DATEDIFF(SECOND, r.start_time, GETDATE()) AS duration_seconds,
    r.command,
    r.wait_type,
    r.wait_time / 1000 AS wait_seconds,
    r.blocking_session_id,
    r.cpu_time / 1000 AS cpu_seconds,
    r.logical_reads,
    SUBSTRING(st.text, (r.statement_start_offset/2)+1, 
        ((CASE r.statement_end_offset
            WHEN -1 THEN DATALENGTH(st.text)
            ELSE r.statement_end_offset
        END - r.statement_start_offset)/2)+1) AS current_statement,
    s.login_name,
    s.host_name,
    DB_NAME(r.database_id) AS database_name
FROM sys.dm_exec_requests r
JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) st
WHERE r.session_id != @@SPID
AND s.is_user_process = 1
ORDER BY r.start_time;
"""
    ),
    
    QueryTemplate(
        id="perf_006",
        name="Expensive Queries by Total Cost",
        description="Toplam maliyete göre pahalı sorgular",
        category=TemplateCategory.PERFORMANCE.value,
        intent=Intent.EXPENSIVE_QUERIES,
        tags=["expensive", "cost", "total"],
        sql="""
SELECT TOP 20
    SUBSTRING(st.text, 1, 200) AS query_text,
    (qs.total_worker_time + qs.total_elapsed_time + qs.total_logical_reads) / 1000 AS total_cost,
    qs.total_worker_time / 1000 AS cpu_ms,
    qs.total_elapsed_time / 1000 AS duration_ms,
    qs.total_logical_reads AS reads,
    qs.execution_count,
    qs.last_execution_time
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
ORDER BY total_cost DESC;
"""
    ),
    
    QueryTemplate(
        id="perf_007",
        name="Query Plan Cache Usage",
        description="Plan cache kullanım durumu",
        category=TemplateCategory.PERFORMANCE.value,
        intent=Intent.EXPLAIN_PLAN,
        tags=["plan", "cache", "memory"],
        sql="""
SELECT 
    objtype AS object_type,
    COUNT(*) AS plan_count,
    SUM(CAST(size_in_bytes AS BIGINT)) / 1024 / 1024 AS total_mb,
    AVG(usecounts) AS avg_use_count,
    SUM(usecounts) AS total_uses
FROM sys.dm_exec_cached_plans
GROUP BY objtype
ORDER BY total_mb DESC;
"""
    ),
    
    QueryTemplate(
        id="perf_008",
        name="Single-Use Ad-Hoc Queries",
        description="Tek kullanımlık ad-hoc sorguları bulur (plan cache şişmesi)",
        category=TemplateCategory.PERFORMANCE.value,
        intent=Intent.ANALYZE_QUERY,
        tags=["adhoc", "single-use", "plan cache"],
        sql="""
SELECT TOP 50
    SUBSTRING(st.text, 1, 200) AS query_text,
    cp.usecounts,
    cp.size_in_bytes / 1024 AS size_kb,
    cp.cacheobjtype,
    qs.execution_count
FROM sys.dm_exec_cached_plans cp
CROSS APPLY sys.dm_exec_sql_text(cp.plan_handle) st
LEFT JOIN sys.dm_exec_query_stats qs ON cp.plan_handle = qs.plan_handle
WHERE cp.objtype = 'Adhoc'
AND cp.usecounts = 1
ORDER BY cp.size_in_bytes DESC;
"""
    ),
    
    QueryTemplate(
        id="perf_009",
        name="Parameter Sniffing Suspects",
        description="Parameter sniffing şüphelilerini bulur",
        category=TemplateCategory.PERFORMANCE.value,
        intent=Intent.ANALYZE_QUERY,
        tags=["parameter sniffing", "variance", "performance"],
        sql="""
SELECT 
    OBJECT_NAME(qp.objectid) AS object_name,
    COUNT(DISTINCT qs.plan_handle) AS plan_count,
    SUM(qs.execution_count) AS total_executions,
    AVG(qs.total_elapsed_time / qs.execution_count) / 1000 AS avg_duration_ms,
    MAX(qs.total_elapsed_time / qs.execution_count) / 1000 AS max_duration_ms,
    MIN(qs.total_elapsed_time / qs.execution_count) / 1000 AS min_duration_ms
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_query_plan(qs.plan_handle) qp
WHERE qp.objectid IS NOT NULL
AND qs.execution_count > 10
GROUP BY qp.objectid
HAVING COUNT(DISTINCT qs.plan_handle) > 1
ORDER BY plan_count DESC;
"""
    ),
    
    QueryTemplate(
        id="perf_010",
        name="Batch Requests per Second",
        description="Saniyede işlenen batch sayısı",
        category=TemplateCategory.PERFORMANCE.value,
        intent=Intent.SERVER_STATUS,
        tags=["batch", "throughput", "performance"],
        sql="""
SELECT 
    cntr_value AS batch_requests_per_sec
FROM sys.dm_os_performance_counters
WHERE counter_name = 'Batch Requests/sec';
"""
    ),
    
    # ═══════════════════════════════════════════════════════════
    # WAIT STATS QUERIES (11-17)
    # ═══════════════════════════════════════════════════════════
    
    QueryTemplate(
        id="wait_001",
        name="Top Wait Types",
        description="En çok bekleme yapılan wait type'ları",
        category=TemplateCategory.WAIT_STATS.value,
        intent=Intent.TOP_WAITS,
        tags=["wait", "top", "statistics"],
        sql="""
SELECT TOP 20
    wait_type,
    wait_time_ms / 1000 AS wait_seconds,
    waiting_tasks_count,
    wait_time_ms / NULLIF(waiting_tasks_count, 0) AS avg_wait_ms,
    signal_wait_time_ms / 1000 AS signal_wait_seconds,
    CAST(100.0 * wait_time_ms / SUM(wait_time_ms) OVER() AS DECIMAL(5,2)) AS wait_percent
FROM sys.dm_os_wait_stats
WHERE wait_type NOT IN (
    'SLEEP_TASK', 'BROKER_TASK_STOP', 'WAITFOR', 'LAZYWRITER_SLEEP',
    'XE_DISPATCHER_WAIT', 'REQUEST_FOR_DEADLOCK_SEARCH', 'SQLTRACE_BUFFER_FLUSH',
    'CLR_AUTO_EVENT', 'CLR_MANUAL_EVENT', 'BROKER_EVENTHANDLER', 'CHECKPOINT_QUEUE',
    'FT_IFTS_SCHEDULER_IDLE_WAIT', 'XE_TIMER_EVENT', 'BROKER_TO_FLUSH',
    'BROKER_RECEIVE_WAITFOR', 'HADR_FILESTREAM_IOMGR_IOCOMPLETION',
    'DIRTY_PAGE_POLL', 'SP_SERVER_DIAGNOSTICS_SLEEP'
)
AND wait_time_ms > 0
ORDER BY wait_time_ms DESC;
"""
    ),
    
    QueryTemplate(
        id="wait_002",
        name="Signal vs Resource Wait",
        description="Signal ve Resource wait oranı",
        category=TemplateCategory.WAIT_STATS.value,
        intent=Intent.SIGNAL_WAITS,
        tags=["signal", "resource", "cpu"],
        sql="""
SELECT 
    SUM(signal_wait_time_ms) AS total_signal_wait_ms,
    SUM(wait_time_ms - signal_wait_time_ms) AS total_resource_wait_ms,
    SUM(wait_time_ms) AS total_wait_ms,
    CAST(100.0 * SUM(signal_wait_time_ms) / SUM(wait_time_ms) AS DECIMAL(5,2)) AS signal_wait_percent,
    CAST(100.0 * SUM(wait_time_ms - signal_wait_time_ms) / SUM(wait_time_ms) AS DECIMAL(5,2)) AS resource_wait_percent
FROM sys.dm_os_wait_stats
WHERE wait_time_ms > 0;
"""
    ),
    
    QueryTemplate(
        id="wait_003",
        name="I/O Related Waits",
        description="I/O ile ilgili wait'ler",
        category=TemplateCategory.WAIT_STATS.value,
        intent=Intent.WAIT_BY_TYPE,
        tags=["io", "pageiolatch", "disk"],
        sql="""
SELECT 
    wait_type,
    wait_time_ms / 1000 AS wait_seconds,
    waiting_tasks_count,
    wait_time_ms / NULLIF(waiting_tasks_count, 0) AS avg_wait_ms
FROM sys.dm_os_wait_stats
WHERE wait_type LIKE 'PAGEIOLATCH%'
OR wait_type LIKE 'WRITELOG%'
OR wait_type LIKE 'IO_COMPLETION%'
ORDER BY wait_time_ms DESC;
"""
    ),
    
    QueryTemplate(
        id="wait_004",
        name="Lock Related Waits",
        description="Kilit ile ilgili wait'ler",
        category=TemplateCategory.WAIT_STATS.value,
        intent=Intent.LOCK_ANALYSIS,
        tags=["lock", "lck_", "blocking"],
        sql="""
SELECT 
    wait_type,
    wait_time_ms / 1000 AS wait_seconds,
    waiting_tasks_count,
    wait_time_ms / NULLIF(waiting_tasks_count, 0) AS avg_wait_ms
FROM sys.dm_os_wait_stats
WHERE wait_type LIKE 'LCK_%'
ORDER BY wait_time_ms DESC;
"""
    ),
    
    QueryTemplate(
        id="wait_005",
        name="Parallelism Waits (CXPACKET)",
        description="Parallelism ile ilgili wait'ler",
        category=TemplateCategory.WAIT_STATS.value,
        intent=Intent.WAIT_BY_TYPE,
        tags=["parallel", "cxpacket", "maxdop"],
        sql="""
SELECT 
    wait_type,
    wait_time_ms / 1000 AS wait_seconds,
    waiting_tasks_count,
    wait_time_ms / NULLIF(waiting_tasks_count, 0) AS avg_wait_ms,
    CAST(100.0 * wait_time_ms / (SELECT SUM(wait_time_ms) FROM sys.dm_os_wait_stats WHERE wait_time_ms > 0) AS DECIMAL(5,2)) AS wait_percent
FROM sys.dm_os_wait_stats
WHERE wait_type IN ('CXPACKET', 'CXCONSUMER', 'CXSYNC_PORT', 'CXSYNC_CONSUMER')
ORDER BY wait_time_ms DESC;
"""
    ),
    
    QueryTemplate(
        id="wait_006",
        name="Memory Related Waits",
        description="Memory ile ilgili wait'ler",
        category=TemplateCategory.WAIT_STATS.value,
        intent=Intent.WAIT_BY_TYPE,
        tags=["memory", "resource_semaphore", "grant"],
        sql="""
SELECT 
    wait_type,
    wait_time_ms / 1000 AS wait_seconds,
    waiting_tasks_count,
    wait_time_ms / NULLIF(waiting_tasks_count, 0) AS avg_wait_ms
FROM sys.dm_os_wait_stats
WHERE wait_type IN (
    'RESOURCE_SEMAPHORE', 'RESOURCE_SEMAPHORE_QUERY_COMPILE',
    'CMEMTHREAD', 'SOS_VIRTUALMEMORY_LOW', 'LOWFAIL_MEMMGR_QUEUE'
)
ORDER BY wait_time_ms DESC;
"""
    ),
    
    QueryTemplate(
        id="wait_007",
        name="Current Waiting Tasks",
        description="Şu anda bekleyen task'lar",
        category=TemplateCategory.WAIT_STATS.value,
        intent=Intent.WAIT_ANALYSIS,
        tags=["current", "waiting", "active"],
        sql="""
SELECT 
    wt.session_id,
    wt.wait_type,
    wt.wait_duration_ms / 1000 AS wait_seconds,
    wt.blocking_session_id,
    wt.resource_description,
    st.text AS query_text,
    s.login_name,
    s.host_name
FROM sys.dm_os_waiting_tasks wt
JOIN sys.dm_exec_sessions s ON wt.session_id = s.session_id
CROSS APPLY sys.dm_exec_sql_text(
    (SELECT sql_handle FROM sys.dm_exec_requests WHERE session_id = wt.session_id)
) st
WHERE wt.session_id != @@SPID
ORDER BY wt.wait_duration_ms DESC;
"""
    ),
    
    # ═══════════════════════════════════════════════════════════
    # BLOCKING QUERIES (18-22)
    # ═══════════════════════════════════════════════════════════
    
    QueryTemplate(
        id="block_001",
        name="Blocking Chain",
        description="Blocking zincirini gösterir",
        category=TemplateCategory.BLOCKING.value,
        intent=Intent.BLOCKING_SESSIONS,
        tags=["blocking", "chain", "lock"],
        sql="""
WITH BlockingTree AS (
    SELECT 
        r.session_id,
        r.blocking_session_id,
        r.wait_type,
        r.wait_time / 1000 AS wait_seconds,
        r.cpu_time / 1000 AS cpu_seconds,
        DB_NAME(r.database_id) AS database_name,
        SUBSTRING(st.text, (r.statement_start_offset/2)+1, 
            ((CASE r.statement_end_offset
                WHEN -1 THEN DATALENGTH(st.text)
                ELSE r.statement_end_offset
            END - r.statement_start_offset)/2)+1) AS current_statement,
        s.login_name,
        s.host_name,
        s.program_name
    FROM sys.dm_exec_requests r
    JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
    CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) st
    WHERE r.blocking_session_id > 0
)
SELECT 
    blocked.session_id AS blocked_session,
    blocked.blocking_session_id AS blocker_session,
    blocked.wait_type,
    blocked.wait_seconds,
    blocked.database_name,
    blocked.current_statement AS blocked_query,
    blocked.login_name AS blocked_login,
    blocked.host_name AS blocked_host,
    blocker.text AS blocker_query
FROM BlockingTree blocked
LEFT JOIN sys.dm_exec_requests blocker_r ON blocked.blocking_session_id = blocker_r.session_id
OUTER APPLY sys.dm_exec_sql_text(blocker_r.sql_handle) blocker
ORDER BY blocked.wait_seconds DESC;
"""
    ),
    
    QueryTemplate(
        id="block_002",
        name="Head Blockers",
        description="Asıl blocker'ları bulur (zincirin başı)",
        category=TemplateCategory.BLOCKING.value,
        intent=Intent.BLOCKING_SESSIONS,
        tags=["head", "blocker", "root"],
        sql="""
SELECT DISTINCT
    r.blocking_session_id AS head_blocker_session,
    s.login_name,
    s.host_name,
    s.program_name,
    st.text AS blocker_query,
    (SELECT COUNT(*) FROM sys.dm_exec_requests WHERE blocking_session_id = r.blocking_session_id) AS blocked_count
FROM sys.dm_exec_requests r
JOIN sys.dm_exec_sessions s ON r.blocking_session_id = s.session_id
CROSS APPLY sys.dm_exec_sql_text(
    (SELECT sql_handle FROM sys.dm_exec_requests WHERE session_id = r.blocking_session_id)
) st
WHERE r.blocking_session_id NOT IN (
    SELECT session_id FROM sys.dm_exec_requests WHERE blocking_session_id > 0
)
AND r.blocking_session_id > 0
ORDER BY blocked_count DESC;
"""
    ),
    
    QueryTemplate(
        id="block_003",
        name="Lock Details",
        description="Detaylı kilit bilgisi",
        category=TemplateCategory.BLOCKING.value,
        intent=Intent.LOCK_ANALYSIS,
        tags=["lock", "detail", "resource"],
        sql="""
SELECT 
    l.request_session_id AS session_id,
    DB_NAME(l.resource_database_id) AS database_name,
    l.resource_type,
    l.resource_subtype,
    l.resource_description,
    l.request_mode,
    l.request_status,
    l.request_owner_type,
    OBJECT_NAME(p.object_id) AS object_name
FROM sys.dm_tran_locks l
LEFT JOIN sys.partitions p ON l.resource_associated_entity_id = p.hobt_id
WHERE l.request_session_id != @@SPID
ORDER BY l.request_session_id, l.resource_type;
"""
    ),
    
    QueryTemplate(
        id="block_004",
        name="Active Sessions",
        description="Aktif kullanıcı oturumları",
        category=TemplateCategory.BLOCKING.value,
        intent=Intent.ACTIVE_SESSIONS,
        tags=["session", "active", "connection"],
        sql="""
SELECT 
    s.session_id,
    s.login_name,
    s.host_name,
    s.program_name,
    s.status,
    s.cpu_time / 1000 AS cpu_seconds,
    s.memory_usage * 8 AS memory_kb,
    s.reads,
    s.writes,
    s.last_request_start_time,
    DB_NAME(s.database_id) AS current_database,
    c.client_net_address,
    c.connect_time
FROM sys.dm_exec_sessions s
LEFT JOIN sys.dm_exec_connections c ON s.session_id = c.session_id
WHERE s.is_user_process = 1
AND s.session_id != @@SPID
ORDER BY s.cpu_time DESC;
"""
    ),
    
    QueryTemplate(
        id="block_005",
        name="Recent Deadlocks",
        description="Son deadlock bilgileri (system_health)",
        category=TemplateCategory.BLOCKING.value,
        intent=Intent.DEADLOCKS,
        tags=["deadlock", "history", "xevent"],
        sql="""
;WITH DeadlockEvents AS (
    SELECT 
        xdr.value('@timestamp', 'datetime2') AS event_time,
        xdr.query('.') AS deadlock_graph
    FROM (
        SELECT CAST(target_data AS XML) AS target_data
        FROM sys.dm_xe_session_targets st
        JOIN sys.dm_xe_sessions s ON s.address = st.event_session_address
        WHERE s.name = 'system_health'
        AND st.target_name = 'ring_buffer'
    ) AS data
    CROSS APPLY target_data.nodes('RingBufferTarget/event[@name="xml_deadlock_report"]') AS XEventData(xdr)
)
SELECT TOP 10
    event_time,
    deadlock_graph
FROM DeadlockEvents
ORDER BY event_time DESC;
"""
    ),
    
    # ═══════════════════════════════════════════════════════════
    # INDEX QUERIES (23-30)
    # ═══════════════════════════════════════════════════════════
    
    QueryTemplate(
        id="idx_001",
        name="Missing Indexes",
        description="Eksik index önerileri",
        category=TemplateCategory.INDEX.value,
        intent=Intent.MISSING_INDEXES,
        tags=["missing", "index", "recommendation"],
        sql="""
SELECT TOP 25
    OBJECT_NAME(d.object_id) AS table_name,
    d.equality_columns,
    d.inequality_columns,
    d.included_columns,
    s.user_seeks,
    s.user_scans,
    s.avg_user_impact,
    s.avg_total_user_cost,
    'CREATE NONCLUSTERED INDEX IX_' + OBJECT_NAME(d.object_id) + '_' + CAST(d.index_handle AS VARCHAR(10)) +
    ' ON ' + d.statement + ' (' + ISNULL(d.equality_columns, '') + 
    CASE WHEN d.inequality_columns IS NOT NULL THEN ', ' + d.inequality_columns ELSE '' END + ')' +
    CASE WHEN d.included_columns IS NOT NULL THEN ' INCLUDE (' + d.included_columns + ')' ELSE '' END AS create_statement
FROM sys.dm_db_missing_index_details d
JOIN sys.dm_db_missing_index_groups g ON d.index_handle = g.index_handle
JOIN sys.dm_db_missing_index_group_stats s ON g.index_group_handle = s.group_handle
WHERE d.database_id = DB_ID()
ORDER BY s.avg_user_impact * s.user_seeks DESC;
"""
    ),
    
    QueryTemplate(
        id="idx_002",
        name="Unused Indexes",
        description="Hiç kullanılmayan index'ler",
        category=TemplateCategory.INDEX.value,
        intent=Intent.UNUSED_INDEXES,
        tags=["unused", "index", "drop"],
        sql="""
SELECT 
    OBJECT_SCHEMA_NAME(i.object_id) AS schema_name,
    OBJECT_NAME(i.object_id) AS table_name,
    i.name AS index_name,
    i.type_desc,
    s.user_seeks,
    s.user_scans,
    s.user_lookups,
    s.user_updates,
    (SELECT SUM(a.used_pages) * 8 FROM sys.allocation_units a
     JOIN sys.partitions p ON a.container_id = p.partition_id
     WHERE p.object_id = i.object_id AND p.index_id = i.index_id) AS size_kb
FROM sys.indexes i
LEFT JOIN sys.dm_db_index_usage_stats s 
    ON i.object_id = s.object_id AND i.index_id = s.index_id AND s.database_id = DB_ID()
WHERE i.type > 0  -- Non-heap
AND OBJECTPROPERTY(i.object_id, 'IsMsShipped') = 0
AND (s.user_seeks + s.user_scans + s.user_lookups) = 0
OR s.object_id IS NULL
ORDER BY size_kb DESC;
"""
    ),
    
    QueryTemplate(
        id="idx_003",
        name="Index Usage Statistics",
        description="Index kullanım istatistikleri",
        category=TemplateCategory.INDEX.value,
        intent=Intent.INDEX_USAGE,
        tags=["usage", "statistics", "index"],
        sql="""
SELECT 
    OBJECT_SCHEMA_NAME(i.object_id) AS schema_name,
    OBJECT_NAME(i.object_id) AS table_name,
    i.name AS index_name,
    i.type_desc,
    s.user_seeks,
    s.user_scans,
    s.user_lookups,
    s.user_updates,
    s.last_user_seek,
    s.last_user_scan,
    CAST(100.0 * s.user_seeks / NULLIF(s.user_seeks + s.user_scans + s.user_lookups, 0) AS DECIMAL(5,2)) AS seek_percent
FROM sys.indexes i
JOIN sys.dm_db_index_usage_stats s 
    ON i.object_id = s.object_id AND i.index_id = s.index_id
WHERE s.database_id = DB_ID()
AND OBJECTPROPERTY(i.object_id, 'IsMsShipped') = 0
ORDER BY (s.user_seeks + s.user_scans + s.user_lookups) DESC;
"""
    ),
    
    QueryTemplate(
        id="idx_004",
        name="Index Fragmentation",
        description="Index fragmentation durumu",
        category=TemplateCategory.INDEX.value,
        intent=Intent.INDEX_FRAGMENTATION,
        tags=["fragmentation", "rebuild", "reorganize"],
        sql="""
SELECT 
    OBJECT_SCHEMA_NAME(ips.object_id) AS schema_name,
    OBJECT_NAME(ips.object_id) AS table_name,
    i.name AS index_name,
    i.type_desc,
    ips.avg_fragmentation_in_percent,
    ips.page_count,
    ips.avg_page_space_used_in_percent,
    CASE 
        WHEN ips.avg_fragmentation_in_percent > 30 THEN 'REBUILD'
        WHEN ips.avg_fragmentation_in_percent > 10 THEN 'REORGANIZE'
        ELSE 'OK'
    END AS recommendation
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
WHERE ips.avg_fragmentation_in_percent > 5
AND ips.page_count > 1000
ORDER BY ips.avg_fragmentation_in_percent DESC;
"""
    ),
    
    QueryTemplate(
        id="idx_005",
        name="Duplicate Indexes",
        description="Çakışan/duplicate index'ler",
        category=TemplateCategory.INDEX.value,
        intent=Intent.DUPLICATE_INDEXES,
        tags=["duplicate", "overlapping", "redundant"],
        sql="""
;WITH IndexColumns AS (
    SELECT 
        OBJECT_SCHEMA_NAME(i.object_id) AS schema_name,
        OBJECT_NAME(i.object_id) AS table_name,
        i.name AS index_name,
        i.index_id,
        i.object_id,
        (SELECT STRING_AGG(c.name, ', ') WITHIN GROUP (ORDER BY ic.key_ordinal)
         FROM sys.index_columns ic
         JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
         WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id AND ic.is_included_column = 0
        ) AS key_columns
    FROM sys.indexes i
    WHERE i.type > 0
    AND OBJECTPROPERTY(i.object_id, 'IsMsShipped') = 0
)
SELECT 
    i1.schema_name,
    i1.table_name,
    i1.index_name AS index_1,
    i2.index_name AS index_2,
    i1.key_columns
FROM IndexColumns i1
JOIN IndexColumns i2 ON i1.object_id = i2.object_id 
    AND i1.index_id < i2.index_id
    AND i1.key_columns = i2.key_columns;
"""
    ),
    
    QueryTemplate(
        id="idx_006",
        name="Index Size Analysis",
        description="Index boyut analizi",
        category=TemplateCategory.INDEX.value,
        intent=Intent.INDEX_SIZE,
        tags=["size", "space", "storage"],
        sql="""
SELECT 
    OBJECT_SCHEMA_NAME(i.object_id) AS schema_name,
    OBJECT_NAME(i.object_id) AS table_name,
    i.name AS index_name,
    i.type_desc,
    SUM(a.used_pages) * 8 / 1024 AS size_mb,
    SUM(a.total_pages) * 8 / 1024 AS total_mb,
    SUM(p.rows) AS row_count
FROM sys.indexes i
JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
JOIN sys.allocation_units a ON p.partition_id = a.container_id
WHERE OBJECTPROPERTY(i.object_id, 'IsMsShipped') = 0
GROUP BY i.object_id, i.name, i.type_desc
ORDER BY size_mb DESC;
"""
    ),
    
    QueryTemplate(
        id="idx_007",
        name="Index Operational Stats",
        description="Index operasyonel istatistikleri",
        category=TemplateCategory.INDEX.value,
        intent=Intent.INDEX_USAGE,
        tags=["operational", "stats", "detail"],
        sql="""
SELECT 
    OBJECT_NAME(ios.object_id) AS table_name,
    i.name AS index_name,
    ios.leaf_insert_count,
    ios.leaf_update_count,
    ios.leaf_delete_count,
    ios.range_scan_count,
    ios.singleton_lookup_count,
    ios.page_lock_count,
    ios.page_lock_wait_count,
    ios.row_lock_count,
    ios.row_lock_wait_count
FROM sys.dm_db_index_operational_stats(DB_ID(), NULL, NULL, NULL) ios
JOIN sys.indexes i ON ios.object_id = i.object_id AND ios.index_id = i.index_id
WHERE OBJECTPROPERTY(ios.object_id, 'IsMsShipped') = 0
ORDER BY (ios.leaf_insert_count + ios.leaf_update_count + ios.leaf_delete_count) DESC;
"""
    ),
    
    QueryTemplate(
        id="idx_008",
        name="Heaps Without Clustered Index",
        description="Clustered index'i olmayan tablolar (heap)",
        category=TemplateCategory.INDEX.value,
        intent=Intent.INDEX_USAGE,
        tags=["heap", "no clustered", "performance"],
        sql="""
SELECT 
    OBJECT_SCHEMA_NAME(t.object_id) AS schema_name,
    t.name AS table_name,
    p.rows AS row_count,
    SUM(a.used_pages) * 8 / 1024 AS size_mb
FROM sys.tables t
JOIN sys.partitions p ON t.object_id = p.object_id
JOIN sys.allocation_units a ON p.partition_id = a.container_id
WHERE t.type = 'U'
AND NOT EXISTS (
    SELECT 1 FROM sys.indexes i 
    WHERE i.object_id = t.object_id AND i.type = 1
)
GROUP BY t.object_id, t.name, p.rows
HAVING SUM(a.used_pages) > 128  -- > 1 MB
ORDER BY size_mb DESC;
"""
    ),
    
    # ═══════════════════════════════════════════════════════════
    # SERVER HEALTH QUERIES (31-38)
    # ═══════════════════════════════════════════════════════════
    
    QueryTemplate(
        id="srv_001",
        name="Server Memory Status",
        description="Sunucu memory durumu",
        category=TemplateCategory.SERVER_HEALTH.value,
        intent=Intent.MEMORY_STATUS,
        tags=["memory", "buffer", "cache"],
        sql="""
SELECT 
    physical_memory_in_use_kb / 1024 AS memory_used_mb,
    locked_page_allocations_kb / 1024 AS locked_pages_mb,
    virtual_address_space_reserved_kb / 1024 AS virtual_reserved_mb,
    virtual_address_space_committed_kb / 1024 AS virtual_committed_mb,
    memory_utilization_percentage,
    available_commit_limit_kb / 1024 AS available_commit_mb,
    process_physical_memory_low,
    process_virtual_memory_low
FROM sys.dm_os_process_memory;
"""
    ),
    
    QueryTemplate(
        id="srv_002",
        name="Page Life Expectancy",
        description="Buffer pool sayfa ömrü",
        category=TemplateCategory.SERVER_HEALTH.value,
        intent=Intent.PAGE_LIFE,
        tags=["ple", "buffer", "memory"],
        sql="""
SELECT 
    object_name,
    counter_name,
    cntr_value AS ple_seconds,
    CASE 
        WHEN cntr_value < 300 THEN 'CRITICAL - Memory Pressure'
        WHEN cntr_value < 1000 THEN 'WARNING - Monitor Closely'
        ELSE 'OK'
    END AS status
FROM sys.dm_os_performance_counters
WHERE counter_name = 'Page life expectancy'
AND object_name LIKE '%Buffer Manager%';
"""
    ),
    
    QueryTemplate(
        id="srv_003",
        name="CPU Usage History",
        description="CPU kullanım geçmişi",
        category=TemplateCategory.SERVER_HEALTH.value,
        intent=Intent.CPU_STATUS,
        tags=["cpu", "history", "ring buffer"],
        sql="""
;WITH CPUUsage AS (
    SELECT 
        record.value('(./Record/@id)[1]', 'int') AS record_id,
        record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int') AS system_idle,
        record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') AS sql_cpu,
        DATEADD(ms, -1 * (ts_now - timestamp), GETDATE()) AS event_time
    FROM (
        SELECT 
            timestamp,
            CONVERT(xml, record) AS record,
            cpu_ticks / (cpu_ticks/ms_ticks) AS ts_now
        FROM sys.dm_os_ring_buffers
        CROSS JOIN sys.dm_os_sys_info
        WHERE ring_buffer_type = 'RING_BUFFER_SCHEDULER_MONITOR'
    ) AS t
)
SELECT TOP 60
    event_time,
    100 - system_idle AS total_cpu_percent,
    sql_cpu AS sql_cpu_percent,
    100 - system_idle - sql_cpu AS other_cpu_percent
FROM CPUUsage
ORDER BY event_time DESC;
"""
    ),
    
    QueryTemplate(
        id="srv_004",
        name="Database File I/O Stats",
        description="Veritabanı dosyası I/O istatistikleri",
        category=TemplateCategory.SERVER_HEALTH.value,
        intent=Intent.DISK_STATUS,
        tags=["io", "disk", "latency"],
        sql="""
SELECT 
    DB_NAME(vfs.database_id) AS database_name,
    mf.name AS file_name,
    mf.physical_name,
    mf.type_desc,
    vfs.num_of_reads,
    vfs.num_of_writes,
    vfs.io_stall_read_ms,
    vfs.io_stall_write_ms,
    CASE WHEN vfs.num_of_reads = 0 THEN 0 
         ELSE vfs.io_stall_read_ms / vfs.num_of_reads END AS avg_read_latency_ms,
    CASE WHEN vfs.num_of_writes = 0 THEN 0 
         ELSE vfs.io_stall_write_ms / vfs.num_of_writes END AS avg_write_latency_ms,
    vfs.num_of_bytes_read / 1024 / 1024 AS read_mb,
    vfs.num_of_bytes_written / 1024 / 1024 AS write_mb
FROM sys.dm_io_virtual_file_stats(NULL, NULL) vfs
JOIN sys.master_files mf ON vfs.database_id = mf.database_id AND vfs.file_id = mf.file_id
ORDER BY (vfs.io_stall_read_ms + vfs.io_stall_write_ms) DESC;
"""
    ),
    
    QueryTemplate(
        id="srv_005",
        name="Connection Summary",
        description="Bağlantı özeti",
        category=TemplateCategory.SERVER_HEALTH.value,
        intent=Intent.CONNECTION_COUNT,
        tags=["connection", "session", "count"],
        sql="""
SELECT 
    DB_NAME(database_id) AS database_name,
    login_name,
    COUNT(*) AS connection_count,
    SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running,
    SUM(CASE WHEN status = 'sleeping' THEN 1 ELSE 0 END) AS sleeping,
    MAX(last_request_start_time) AS last_activity
FROM sys.dm_exec_sessions
WHERE is_user_process = 1
GROUP BY database_id, login_name
ORDER BY connection_count DESC;
"""
    ),
    
    QueryTemplate(
        id="srv_006",
        name="Buffer Pool Usage by Database",
        description="Veritabanlarına göre buffer pool kullanımı",
        category=TemplateCategory.SERVER_HEALTH.value,
        intent=Intent.BUFFER_POOL,
        tags=["buffer", "pool", "cache"],
        sql="""
SELECT 
    DB_NAME(database_id) AS database_name,
    COUNT(*) * 8 / 1024 AS cached_mb,
    COUNT(*) AS page_count,
    CAST(100.0 * COUNT(*) / (SELECT COUNT(*) FROM sys.dm_os_buffer_descriptors) AS DECIMAL(5,2)) AS buffer_percent
FROM sys.dm_os_buffer_descriptors
GROUP BY database_id
ORDER BY cached_mb DESC;
"""
    ),
    
    QueryTemplate(
        id="srv_007",
        name="SQL Server Configuration",
        description="SQL Server konfigürasyon ayarları",
        category=TemplateCategory.SERVER_HEALTH.value,
        intent=Intent.SERVER_STATUS,
        tags=["config", "setting", "sp_configure"],
        sql="""
SELECT 
    name,
    value AS configured_value,
    value_in_use AS running_value,
    minimum,
    maximum,
    is_dynamic,
    is_advanced
FROM sys.configurations
WHERE value != value_in_use
OR name IN (
    'max server memory (MB)', 'min server memory (MB)',
    'max degree of parallelism', 'cost threshold for parallelism',
    'optimize for ad hoc workloads', 'max worker threads'
)
ORDER BY name;
"""
    ),
    
    QueryTemplate(
        id="srv_008",
        name="Error Log Recent Errors",
        description="Error log son hatalar",
        category=TemplateCategory.SERVER_HEALTH.value,
        intent=Intent.SERVER_STATUS,
        tags=["error", "log", "recent"],
        sql="""
CREATE TABLE #ErrorLog (LogDate DATETIME, ProcessInfo NVARCHAR(100), Text NVARCHAR(MAX));
INSERT INTO #ErrorLog EXEC xp_readerrorlog 0, 1, N'error';
SELECT TOP 50 * FROM #ErrorLog ORDER BY LogDate DESC;
DROP TABLE #ErrorLog;
"""
    ),
    
    # ═══════════════════════════════════════════════════════════
    # DATABASE QUERIES (39-43)
    # ═══════════════════════════════════════════════════════════
    
    QueryTemplate(
        id="db_001",
        name="Database Size",
        description="Veritabanı boyutları",
        category=TemplateCategory.DATABASE.value,
        intent=Intent.DATABASE_SIZE,
        tags=["size", "database", "space"],
        sql="""
SELECT 
    DB_NAME(database_id) AS database_name,
    type_desc AS file_type,
    name AS file_name,
    physical_name,
    size * 8 / 1024 AS size_mb,
    max_size,
    growth,
    is_percent_growth
FROM sys.master_files
ORDER BY database_id, type;
"""
    ),
    
    QueryTemplate(
        id="db_002",
        name="Database Space Used",
        description="Veritabanı kullanılan alan",
        category=TemplateCategory.DATABASE.value,
        intent=Intent.DATABASE_SIZE,
        tags=["space", "used", "free"],
        sql="""
SELECT 
    DB_NAME() AS database_name,
    name AS file_name,
    type_desc,
    size * 8 / 1024 AS size_mb,
    FILEPROPERTY(name, 'SpaceUsed') * 8 / 1024 AS used_mb,
    (size - FILEPROPERTY(name, 'SpaceUsed')) * 8 / 1024 AS free_mb,
    CAST(100.0 * FILEPROPERTY(name, 'SpaceUsed') / size AS DECIMAL(5,2)) AS used_percent
FROM sys.database_files;
"""
    ),
    
    QueryTemplate(
        id="db_003",
        name="Transaction Log Usage",
        description="Transaction log kullanımı",
        category=TemplateCategory.DATABASE.value,
        intent=Intent.LOG_USAGE,
        tags=["log", "transaction", "usage"],
        sql="""
SELECT 
    DB_NAME(database_id) AS database_name,
    CAST(total_log_size_in_bytes / 1024.0 / 1024 AS DECIMAL(10,2)) AS log_size_mb,
    CAST(used_log_space_in_bytes / 1024.0 / 1024 AS DECIMAL(10,2)) AS used_mb,
    CAST(used_log_space_in_percent AS DECIMAL(5,2)) AS used_percent,
    log_space_in_bytes_since_last_backup / 1024 / 1024 AS since_backup_mb
FROM sys.dm_db_log_space_usage;
"""
    ),
    
    QueryTemplate(
        id="db_004",
        name="Table Sizes",
        description="Tablo boyutları",
        category=TemplateCategory.DATABASE.value,
        intent=Intent.TABLE_INFO,
        tags=["table", "size", "rows"],
        sql="""
SELECT 
    OBJECT_SCHEMA_NAME(t.object_id) AS schema_name,
    t.name AS table_name,
    SUM(p.rows) AS row_count,
    SUM(a.total_pages) * 8 / 1024 AS total_mb,
    SUM(a.used_pages) * 8 / 1024 AS used_mb,
    SUM(a.data_pages) * 8 / 1024 AS data_mb
FROM sys.tables t
JOIN sys.indexes i ON t.object_id = i.object_id
JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
JOIN sys.allocation_units a ON p.partition_id = a.container_id
GROUP BY t.object_id, t.name
ORDER BY total_mb DESC;
"""
    ),
    
    QueryTemplate(
        id="db_005",
        name="Auto Growth Events",
        description="Otomatik büyüme olayları",
        category=TemplateCategory.DATABASE.value,
        intent=Intent.DATABASE_GROWTH,
        tags=["growth", "auto", "event"],
        sql="""
;WITH AutoGrowth AS (
    SELECT 
        CAST(event_data AS XML) AS event_xml
    FROM sys.fn_xe_file_target_read_file(
        'system_health*.xel', NULL, NULL, NULL
    )
    WHERE object_name = 'database_file_size_change'
)
SELECT TOP 50
    event_xml.value('(event/@timestamp)[1]', 'datetime2') AS event_time,
    event_xml.value('(event/data[@name="database_name"]/value)[1]', 'nvarchar(256)') AS database_name,
    event_xml.value('(event/data[@name="file_name"]/value)[1]', 'nvarchar(256)') AS file_name,
    event_xml.value('(event/data[@name="size_change_kb"]/value)[1]', 'bigint') / 1024 AS size_change_mb,
    event_xml.value('(event/data[@name="is_automatic"]/value)[1]', 'bit') AS is_automatic
FROM AutoGrowth
ORDER BY event_time DESC;
"""
    ),
    
    # ═══════════════════════════════════════════════════════════
    # TEMPDB QUERIES (44-46)
    # ═══════════════════════════════════════════════════════════
    
    QueryTemplate(
        id="temp_001",
        name="TempDB Space Usage",
        description="TempDB alan kullanımı",
        category=TemplateCategory.TEMPDB.value,
        intent=Intent.TEMPDB_USAGE,
        tags=["tempdb", "space", "usage"],
        sql="""
SELECT 
    SUM(user_object_reserved_page_count) * 8 / 1024 AS user_objects_mb,
    SUM(internal_object_reserved_page_count) * 8 / 1024 AS internal_objects_mb,
    SUM(version_store_reserved_page_count) * 8 / 1024 AS version_store_mb,
    SUM(unallocated_extent_page_count) * 8 / 1024 AS free_space_mb,
    SUM(mixed_extent_page_count) * 8 / 1024 AS mixed_extents_mb
FROM tempdb.sys.dm_db_file_space_usage;
"""
    ),
    
    QueryTemplate(
        id="temp_002",
        name="TempDB Usage by Session",
        description="Session bazında TempDB kullanımı",
        category=TemplateCategory.TEMPDB.value,
        intent=Intent.TEMPDB_USAGE,
        tags=["tempdb", "session", "who"],
        sql="""
SELECT TOP 20
    ss.session_id,
    ss.login_name,
    ss.host_name,
    ss.program_name,
    tsu.user_objects_alloc_page_count * 8 / 1024 AS user_objects_mb,
    tsu.user_objects_dealloc_page_count * 8 / 1024 AS user_objects_dealloc_mb,
    tsu.internal_objects_alloc_page_count * 8 / 1024 AS internal_objects_mb,
    st.text AS current_query
FROM tempdb.sys.dm_db_session_space_usage tsu
JOIN sys.dm_exec_sessions ss ON tsu.session_id = ss.session_id
OUTER APPLY sys.dm_exec_sql_text(
    (SELECT sql_handle FROM sys.dm_exec_requests WHERE session_id = tsu.session_id)
) st
WHERE tsu.user_objects_alloc_page_count + tsu.internal_objects_alloc_page_count > 0
ORDER BY (tsu.user_objects_alloc_page_count + tsu.internal_objects_alloc_page_count) DESC;
"""
    ),
    
    QueryTemplate(
        id="temp_003",
        name="Version Store Usage",
        description="Version store kullanımı (snapshot isolation)",
        category=TemplateCategory.TEMPDB.value,
        intent=Intent.VERSION_STORE,
        tags=["version store", "snapshot", "isolation"],
        sql="""
SELECT 
    DB_NAME(database_id) AS database_name,
    reserved_page_count * 8 / 1024 AS reserved_mb,
    reserved_space_kb / 1024 AS reserved_space_mb
FROM sys.dm_tran_version_store_space_usage
WHERE reserved_page_count > 0
ORDER BY reserved_page_count DESC;
"""
    ),
    
    # ═══════════════════════════════════════════════════════════
    # SECURITY QUERIES (47-50)
    # ═══════════════════════════════════════════════════════════
    
    QueryTemplate(
        id="sec_001",
        name="Server Logins",
        description="Server login listesi",
        category=TemplateCategory.SECURITY.value,
        intent=Intent.LOGIN_INFO,
        tags=["login", "security", "user"],
        sql="""
SELECT 
    name AS login_name,
    type_desc AS login_type,
    is_disabled,
    create_date,
    modify_date,
    default_database_name,
    LOGINPROPERTY(name, 'PasswordLastSetTime') AS password_last_set,
    LOGINPROPERTY(name, 'IsLocked') AS is_locked,
    LOGINPROPERTY(name, 'IsExpired') AS is_expired
FROM sys.server_principals
WHERE type IN ('S', 'U', 'G')
ORDER BY name;
"""
    ),
    
    QueryTemplate(
        id="sec_002",
        name="Sysadmin Members",
        description="Sysadmin rolü üyeleri",
        category=TemplateCategory.SECURITY.value,
        intent=Intent.ROLE_MEMBERS,
        tags=["sysadmin", "role", "member"],
        sql="""
SELECT 
    sp.name AS login_name,
    sp.type_desc AS login_type,
    sp.is_disabled,
    sp.create_date
FROM sys.server_role_members rm
JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
JOIN sys.server_principals sp ON rm.member_principal_id = sp.principal_id
WHERE r.name = 'sysadmin'
ORDER BY sp.name;
"""
    ),
    
    QueryTemplate(
        id="sec_003",
        name="Database Permissions",
        description="Veritabanı izinleri",
        category=TemplateCategory.SECURITY.value,
        intent=Intent.PERMISSIONS,
        tags=["permission", "grant", "database"],
        sql="""
SELECT 
    dp.name AS principal_name,
    dp.type_desc AS principal_type,
    o.name AS object_name,
    o.type_desc AS object_type,
    p.permission_name,
    p.state_desc AS permission_state
FROM sys.database_permissions p
JOIN sys.database_principals dp ON p.grantee_principal_id = dp.principal_id
LEFT JOIN sys.objects o ON p.major_id = o.object_id
WHERE dp.name NOT IN ('public', 'guest')
AND p.type != 'CO'
ORDER BY dp.name, o.name;
"""
    ),
    
    QueryTemplate(
        id="sec_004",
        name="Orphaned Users",
        description="Yetim kullanıcılar (login'i olmayan)",
        category=TemplateCategory.SECURITY.value,
        intent=Intent.ORPHANED_USERS,
        tags=["orphan", "user", "no login"],
        sql="""
SELECT 
    dp.name AS user_name,
    dp.type_desc AS user_type,
    dp.create_date,
    dp.sid
FROM sys.database_principals dp
LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid
WHERE dp.type IN ('S', 'U')
AND dp.name NOT IN ('dbo', 'guest', 'INFORMATION_SCHEMA', 'sys')
AND sp.sid IS NULL;
"""
    ),
    
    # ═══════════════════════════════════════════════════════════
    # BACKUP QUERIES (51-53)
    # ═══════════════════════════════════════════════════════════
    
    QueryTemplate(
        id="bak_001",
        name="Last Backup Status",
        description="Son backup durumu",
        category=TemplateCategory.BACKUP.value,
        intent=Intent.LAST_BACKUP,
        tags=["backup", "last", "status"],
        sql="""
SELECT 
    d.name AS database_name,
    d.recovery_model_desc,
    MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END) AS last_full_backup,
    MAX(CASE WHEN b.type = 'I' THEN b.backup_finish_date END) AS last_diff_backup,
    MAX(CASE WHEN b.type = 'L' THEN b.backup_finish_date END) AS last_log_backup,
    DATEDIFF(HOUR, MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END), GETDATE()) AS hours_since_full,
    DATEDIFF(MINUTE, MAX(CASE WHEN b.type = 'L' THEN b.backup_finish_date END), GETDATE()) AS minutes_since_log
FROM sys.databases d
LEFT JOIN msdb.dbo.backupset b ON d.name = b.database_name
WHERE d.database_id > 4
GROUP BY d.name, d.recovery_model_desc
ORDER BY hours_since_full DESC;
"""
    ),
    
    QueryTemplate(
        id="bak_002",
        name="Backup History",
        description="Backup geçmişi",
        category=TemplateCategory.BACKUP.value,
        intent=Intent.BACKUP_HISTORY,
        tags=["backup", "history", "detail"],
        sql="""
SELECT TOP 50
    database_name,
    CASE type
        WHEN 'D' THEN 'Full'
        WHEN 'I' THEN 'Differential'
        WHEN 'L' THEN 'Log'
        WHEN 'F' THEN 'File/Filegroup'
    END AS backup_type,
    backup_start_date,
    backup_finish_date,
    DATEDIFF(SECOND, backup_start_date, backup_finish_date) AS duration_seconds,
    backup_size / 1024 / 1024 AS size_mb,
    compressed_backup_size / 1024 / 1024 AS compressed_mb,
    CAST(100.0 * compressed_backup_size / NULLIF(backup_size, 0) AS DECIMAL(5,2)) AS compression_ratio,
    physical_device_name
FROM msdb.dbo.backupset b
JOIN msdb.dbo.backupmediafamily m ON b.media_set_id = m.media_set_id
ORDER BY backup_finish_date DESC;
"""
    ),
    
    QueryTemplate(
        id="bak_003",
        name="Databases Without Recent Backup",
        description="Yakın zamanda backup alınmamış veritabanları",
        category=TemplateCategory.BACKUP.value,
        intent=Intent.BACKUP_STATUS,
        tags=["backup", "missing", "alert"],
        sql="""
SELECT 
    d.name AS database_name,
    d.recovery_model_desc,
    MAX(b.backup_finish_date) AS last_backup,
    DATEDIFF(DAY, MAX(b.backup_finish_date), GETDATE()) AS days_since_backup,
    CASE 
        WHEN MAX(b.backup_finish_date) IS NULL THEN 'NEVER BACKED UP'
        WHEN DATEDIFF(DAY, MAX(b.backup_finish_date), GETDATE()) > 7 THEN 'CRITICAL'
        WHEN DATEDIFF(DAY, MAX(b.backup_finish_date), GETDATE()) > 1 THEN 'WARNING'
        ELSE 'OK'
    END AS status
FROM sys.databases d
LEFT JOIN msdb.dbo.backupset b ON d.name = b.database_name
WHERE d.database_id > 4
AND d.state = 0
GROUP BY d.name, d.recovery_model_desc
HAVING MAX(b.backup_finish_date) IS NULL
   OR DATEDIFF(DAY, MAX(b.backup_finish_date), GETDATE()) > 1
ORDER BY days_since_backup DESC;
"""
    ),
    
    # ═══════════════════════════════════════════════════════════
    # JOBS QUERIES (54-55)
    # ═══════════════════════════════════════════════════════════
    
    QueryTemplate(
        id="job_001",
        name="Failed Jobs Last 24 Hours",
        description="Son 24 saatte başarısız olan job'lar",
        category=TemplateCategory.JOBS.value,
        intent=Intent.FAILED_JOBS,
        tags=["job", "failed", "error"],
        sql="""
SELECT 
    j.name AS job_name,
    h.step_name,
    msdb.dbo.agent_datetime(h.run_date, h.run_time) AS run_datetime,
    h.run_duration,
    h.message
FROM msdb.dbo.sysjobs j
JOIN msdb.dbo.sysjobhistory h ON j.job_id = h.job_id
WHERE h.run_status = 0  -- Failed
AND h.step_id > 0
AND msdb.dbo.agent_datetime(h.run_date, h.run_time) > DATEADD(HOUR, -24, GETDATE())
ORDER BY msdb.dbo.agent_datetime(h.run_date, h.run_time) DESC;
"""
    ),
    
    QueryTemplate(
        id="job_002",
        name="Currently Running Jobs",
        description="Şu anda çalışan job'lar",
        category=TemplateCategory.JOBS.value,
        intent=Intent.RUNNING_JOBS,
        tags=["job", "running", "active"],
        sql="""
SELECT 
    j.name AS job_name,
    ja.start_execution_date,
    DATEDIFF(MINUTE, ja.start_execution_date, GETDATE()) AS running_minutes,
    js.step_name AS current_step
FROM msdb.dbo.sysjobactivity ja
JOIN msdb.dbo.sysjobs j ON ja.job_id = j.job_id
LEFT JOIN msdb.dbo.sysjobsteps js ON ja.job_id = js.job_id AND ja.last_executed_step_id = js.step_id - 1
WHERE ja.session_id = (SELECT MAX(session_id) FROM msdb.dbo.sysjobactivity)
AND ja.start_execution_date IS NOT NULL
AND ja.stop_execution_date IS NULL
ORDER BY ja.start_execution_date;
"""
    ),
]


# ═══════════════════════════════════════════════════════════════════════════
# TEMPLATE ACCESS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def get_all_templates() -> List[QueryTemplate]:
    """Get all query templates"""
    return QUERY_TEMPLATES


def get_templates_by_category(category: str) -> List[QueryTemplate]:
    """Get templates by category"""
    return [t for t in QUERY_TEMPLATES if t.category == category]


def get_template_by_id(template_id: str) -> Optional[QueryTemplate]:
    """Get template by ID"""
    for t in QUERY_TEMPLATES:
        if t.id == template_id:
            return t
    return None


def get_template_for_intent(intent: Intent) -> Optional[str]:
    """Get first matching template SQL for an intent"""
    for t in QUERY_TEMPLATES:
        if t.intent == intent:
            return t.sql.strip()
    return None


def search_templates(query: str) -> List[QueryTemplate]:
    """Search templates by name, description, or tags"""
    query_lower = query.lower()
    results = []
    
    for t in QUERY_TEMPLATES:
        # Search in name
        if query_lower in t.name.lower():
            results.append(t)
            continue
        
        # Search in description
        if query_lower in t.description.lower():
            results.append(t)
            continue
        
        # Search in tags
        if any(query_lower in tag.lower() for tag in t.tags):
            results.append(t)
            continue
    
    return results


def get_template_categories() -> List[Dict[str, str]]:
    """Get all template categories with counts"""
    categories = {}
    for t in QUERY_TEMPLATES:
        if t.category not in categories:
            categories[t.category] = 0
        categories[t.category] += 1
    
    return [
        {"category": cat, "count": count}
        for cat, count in sorted(categories.items())
    ]


def get_templates_summary() -> Dict[str, int]:
    """Get summary of templates"""
    return {
        "total": len(QUERY_TEMPLATES),
        "categories": len(set(t.category for t in QUERY_TEMPLATES)),
        "with_intent": len([t for t in QUERY_TEMPLATES if t.intent is not None])
    }
