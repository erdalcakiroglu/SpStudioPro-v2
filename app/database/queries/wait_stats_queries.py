"""
Wait Statistics Queries - SQL Server wait analysis
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class WaitCategory(Enum):
    """Wait type categories"""
    CPU = "CPU"
    IO = "I/O"
    LOCK = "Lock"
    LATCH = "Latch"
    MEMORY = "Memory"
    NETWORK = "Network"
    BUFFER = "Buffer"
    CLR = "CLR"
    OTHER = "Other"


# Wait type to category mapping
WAIT_CATEGORIES: Dict[str, WaitCategory] = {
    # CPU waits
    'SOS_SCHEDULER_YIELD': WaitCategory.CPU,
    'THREADPOOL': WaitCategory.CPU,
    'CXPACKET': WaitCategory.CPU,
    'CXCONSUMER': WaitCategory.CPU,
    'CXSYNC_PORT': WaitCategory.CPU,
    'CXSYNC_CONSUMER': WaitCategory.CPU,
    'EXCHANGE': WaitCategory.CPU,
    
    # I/O waits
    'PAGEIOLATCH_SH': WaitCategory.IO,
    'PAGEIOLATCH_EX': WaitCategory.IO,
    'PAGEIOLATCH_UP': WaitCategory.IO,
    'PAGEIOLATCH_DT': WaitCategory.IO,
    'PAGEIOLATCH_NL': WaitCategory.IO,
    'PAGEIOLATCH_KP': WaitCategory.IO,
    'WRITELOG': WaitCategory.IO,
    'IO_COMPLETION': WaitCategory.IO,
    'ASYNC_IO_COMPLETION': WaitCategory.IO,
    'ASYNC_NETWORK_IO': WaitCategory.NETWORK,
    'BACKUPIO': WaitCategory.IO,
    'BACKUPBUFFER': WaitCategory.IO,
    
    # Lock waits
    'LCK_M_S': WaitCategory.LOCK,
    'LCK_M_X': WaitCategory.LOCK,
    'LCK_M_U': WaitCategory.LOCK,
    'LCK_M_IS': WaitCategory.LOCK,
    'LCK_M_IX': WaitCategory.LOCK,
    'LCK_M_SIU': WaitCategory.LOCK,
    'LCK_M_SIX': WaitCategory.LOCK,
    'LCK_M_UIX': WaitCategory.LOCK,
    'LCK_M_BU': WaitCategory.LOCK,
    'LCK_M_RS_S': WaitCategory.LOCK,
    'LCK_M_RS_U': WaitCategory.LOCK,
    'LCK_M_RIn_NL': WaitCategory.LOCK,
    'LCK_M_SCH_S': WaitCategory.LOCK,
    'LCK_M_SCH_M': WaitCategory.LOCK,
    
    # Latch waits
    'PAGELATCH_SH': WaitCategory.LATCH,
    'PAGELATCH_EX': WaitCategory.LATCH,
    'PAGELATCH_UP': WaitCategory.LATCH,
    'PAGELATCH_DT': WaitCategory.LATCH,
    'PAGELATCH_NL': WaitCategory.LATCH,
    'PAGELATCH_KP': WaitCategory.LATCH,
    'LATCH_SH': WaitCategory.LATCH,
    'LATCH_EX': WaitCategory.LATCH,
    'LATCH_UP': WaitCategory.LATCH,
    'LATCH_DT': WaitCategory.LATCH,
    'LATCH_NL': WaitCategory.LATCH,
    
    # Memory waits
    'RESOURCE_SEMAPHORE': WaitCategory.MEMORY,
    'RESOURCE_SEMAPHORE_QUERY_COMPILE': WaitCategory.MEMORY,
    'RESOURCE_SEMAPHORE_MUTEX': WaitCategory.MEMORY,
    'CMEMTHREAD': WaitCategory.MEMORY,
    'SOS_RESERVEDMEMBLOCKLIST': WaitCategory.MEMORY,
    
    # Buffer waits
    'BUFFER': WaitCategory.BUFFER,
    'DBMIRROR_DBM_MUTEX': WaitCategory.BUFFER,
    
    # Network waits
    'ASYNC_NETWORK_IO': WaitCategory.NETWORK,
    'NET_WAITFOR_PACKET': WaitCategory.NETWORK,
    
    # CLR waits
    'CLR_AUTO_EVENT': WaitCategory.CLR,
    'CLR_CRST': WaitCategory.CLR,
    'CLR_JOIN': WaitCategory.CLR,
    'CLR_MANUAL_EVENT': WaitCategory.CLR,
    'CLR_MEMORY_SPY': WaitCategory.CLR,
    'CLR_MONITOR': WaitCategory.CLR,
    'CLR_RWLOCK_READER': WaitCategory.CLR,
    'CLR_RWLOCK_WRITER': WaitCategory.CLR,
    'CLR_SEMAPHORE': WaitCategory.CLR,
    'CLR_TASK_START': WaitCategory.CLR,
}


# Category colors for UI
CATEGORY_COLORS: Dict[WaitCategory, str] = {
    WaitCategory.CPU: "#EF4444",      # Red
    WaitCategory.IO: "#F59E0B",       # Amber
    WaitCategory.LOCK: "#8B5CF6",     # Purple
    WaitCategory.LATCH: "#EC4899",    # Pink
    WaitCategory.MEMORY: "#3B82F6",   # Blue
    WaitCategory.NETWORK: "#10B981",  # Green
    WaitCategory.BUFFER: "#6366F1",   # Indigo
    WaitCategory.CLR: "#14B8A6",      # Teal
    WaitCategory.OTHER: "#64748B",    # Slate
}


class WaitStatsQueries:
    """SQL queries for Wait Statistics"""
    
    # Benign waits to exclude from analysis
    BENIGN_WAITS = """
        'BROKER_EVENTHANDLER', 'BROKER_RECEIVE_WAITFOR', 'BROKER_TASK_STOP',
        'BROKER_TO_FLUSH', 'BROKER_TRANSMITTER', 'CHECKPOINT_QUEUE',
        'CHKPT', 'CLR_AUTO_EVENT', 'CLR_MANUAL_EVENT', 'CLR_SEMAPHORE',
        'DBMIRROR_DBM_EVENT', 'DBMIRROR_DBM_MUTEX', 'DBMIRROR_EVENTS_QUEUE',
        'DBMIRRORING_CMD', 'DIRTY_PAGE_POLL', 'DISPATCHER_QUEUE_SEMAPHORE',
        'EXECSYNC', 'FSAGENT', 'FT_IFTS_SCHEDULER_IDLE_WAIT', 'FT_IFTSHC_MUTEX',
        'HADR_CLUSAPI_CALL', 'HADR_FILESTREAM_IOMGR_IOCOMPLETION',
        'HADR_LOGCAPTURE_WAIT', 'HADR_NOTIFICATION_DEQUEUE',
        'HADR_TIMER_TASK', 'HADR_WORK_QUEUE', 'KSOURCE_WAKEUP',
        'LAZYWRITER_SLEEP', 'LOGMGR_QUEUE', 'MEMORY_ALLOCATION_EXT',
        'ONDEMAND_TASK_QUEUE', 'PARALLEL_REDO_DRAIN_WORKER',
        'PARALLEL_REDO_LOG_CACHE', 'PARALLEL_REDO_TRAN_LIST',
        'PARALLEL_REDO_WORKER_SYNC', 'PARALLEL_REDO_WORKER_WAIT_WORK',
        'PREEMPTIVE_HADR_LEASE_MECHANISM', 'PREEMPTIVE_SP_SERVER_DIAGNOSTICS',
        'PREEMPTIVE_OS_LIBRARYOPS', 'PREEMPTIVE_OS_COMOPS',
        'PREEMPTIVE_OS_CRYPTOPS', 'PREEMPTIVE_OS_PIPEOPS',
        'PREEMPTIVE_OS_AUTHENTICATIONOPS', 'PREEMPTIVE_OS_GENERICOPS',
        'PREEMPTIVE_OS_VERIFYTRUST', 'PREEMPTIVE_OS_FILEOPS',
        'PREEMPTIVE_OS_DEVICEOPS', 'PREEMPTIVE_OS_QUERYREGISTRY',
        'PREEMPTIVE_OS_WRITEFILE', 'PREEMPTIVE_XE_CALLBACKEXECUTE',
        'PREEMPTIVE_XE_DISPATCHER', 'PREEMPTIVE_XE_GETTARGETSTATE',
        'PREEMPTIVE_XE_SESSIONCOMMIT', 'PREEMPTIVE_XE_TARGETINIT',
        'PREEMPTIVE_XE_TARGETFINALIZE', 'PWAIT_ALL_COMPONENTS_INITIALIZED',
        'PWAIT_DIRECTLOGCONSUMER_GETNEXT', 'QDS_ASYNC_QUEUE',
        'QDS_CLEANUP_STALE_QUERIES_TASK_MAIN_LOOP_SLEEP',
        'QDS_PERSIST_TASK_MAIN_LOOP_SLEEP', 'QDS_SHUTDOWN_QUEUE',
        'REDO_THREAD_PENDING_WORK', 'REQUEST_FOR_DEADLOCK_SEARCH',
        'RESOURCE_QUEUE', 'SERVER_IDLE_CHECK', 'SLEEP_BPOOL_FLUSH',
        'SLEEP_DBSTARTUP', 'SLEEP_DCOMSTARTUP', 'SLEEP_MASTERDBREADY',
        'SLEEP_MASTERMDREADY', 'SLEEP_MASTERUPGRADED', 'SLEEP_MSDBSTARTUP',
        'SLEEP_SYSTEMTASK', 'SLEEP_TASK', 'SLEEP_TEMPDBSTARTUP',
        'SNI_HTTP_ACCEPT', 'SOS_WORK_DISPATCHER', 'SP_SERVER_DIAGNOSTICS_SLEEP',
        'SQLTRACE_BUFFER_FLUSH', 'SQLTRACE_INCREMENTAL_FLUSH_SLEEP',
        'SQLTRACE_WAIT_ENTRIES', 'WAIT_FOR_RESULTS', 'WAITFOR',
        'WAITFOR_TASKSHUTDOWN', 'WAIT_XTP_HOST_WAIT', 'WAIT_XTP_OFFLINE_CKPT_NEW_LOG',
        'WAIT_XTP_CKPT_CLOSE', 'WAIT_XTP_RECOVERY', 'XE_BUFFERMGR_ALLPROCESSED_EVENT',
        'XE_DISPATCHER_JOIN', 'XE_DISPATCHER_WAIT', 'XE_LIVE_TARGET_TVF',
        'XE_TIMER_EVENT'
    """
    
    # Top wait types (excluding benign waits)
    TOP_WAITS = f"""
    SELECT TOP 20
        wait_type,
        waiting_tasks_count,
        wait_time_ms,
        max_wait_time_ms,
        signal_wait_time_ms,
        wait_time_ms - signal_wait_time_ms AS resource_wait_time_ms,
        CAST(100.0 * wait_time_ms / NULLIF(SUM(wait_time_ms) OVER(), 0) AS DECIMAL(5,2)) AS wait_percent,
        CAST(100.0 * SUM(wait_time_ms) OVER(ORDER BY wait_time_ms DESC) / 
             NULLIF(SUM(wait_time_ms) OVER(), 0) AS DECIMAL(5,2)) AS cumulative_percent
    FROM sys.dm_os_wait_stats
    WHERE wait_type NOT IN ({BENIGN_WAITS})
      AND wait_time_ms > 0
    ORDER BY wait_time_ms DESC
    """
    
    # Wait stats summary
    WAIT_SUMMARY = f"""
    SELECT 
        COUNT(*) AS total_wait_types,
        SUM(waiting_tasks_count) AS total_waiting_tasks,
        SUM(wait_time_ms) AS total_wait_time_ms,
        SUM(signal_wait_time_ms) AS total_signal_wait_ms,
        SUM(wait_time_ms - signal_wait_time_ms) AS total_resource_wait_ms,
        MAX(max_wait_time_ms) AS max_single_wait_ms
    FROM sys.dm_os_wait_stats
    WHERE wait_type NOT IN ({BENIGN_WAITS})
      AND wait_time_ms > 0
    """
    
    # Wait stats by category (for pie chart)
    WAITS_BY_CATEGORY = f"""
    SELECT 
        wait_type,
        wait_time_ms,
        waiting_tasks_count
    FROM sys.dm_os_wait_stats
    WHERE wait_type NOT IN ({BENIGN_WAITS})
      AND wait_time_ms > 0
    ORDER BY wait_time_ms DESC
    """
    
    # Current waiting tasks
    CURRENT_WAITS = """
    SELECT 
        r.session_id,
        r.wait_type,
        r.wait_time AS wait_time_ms,
        r.wait_resource,
        r.blocking_session_id,
        s.login_name,
        s.host_name,
        s.program_name,
        DB_NAME(r.database_id) AS database_name,
        SUBSTRING(st.text, (r.statement_start_offset/2)+1,
            ((CASE r.statement_end_offset
                WHEN -1 THEN DATALENGTH(st.text)
                ELSE r.statement_end_offset
            END - r.statement_start_offset)/2) + 1) AS current_statement
    FROM sys.dm_exec_requests r
    JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
    CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) st
    WHERE r.wait_type IS NOT NULL
      AND r.session_id <> @@SPID
    ORDER BY r.wait_time DESC
    """
    
    # Signal vs Resource wait ratio
    SIGNAL_VS_RESOURCE = f"""
    SELECT 
        CAST(SUM(signal_wait_time_ms) * 100.0 / NULLIF(SUM(wait_time_ms), 0) AS DECIMAL(5,2)) AS signal_wait_percent,
        CAST(SUM(wait_time_ms - signal_wait_time_ms) * 100.0 / NULLIF(SUM(wait_time_ms), 0) AS DECIMAL(5,2)) AS resource_wait_percent
    FROM sys.dm_os_wait_stats
    WHERE wait_type NOT IN ({BENIGN_WAITS})
      AND wait_time_ms > 0
    """
    
    # Clear wait stats (admin operation)
    CLEAR_WAIT_STATS = """
    DBCC SQLPERF('sys.dm_os_wait_stats', CLEAR) WITH NO_INFOMSGS
    """
    
    # Latch stats
    LATCH_STATS = """
    SELECT TOP 10
        latch_class,
        waiting_requests_count,
        wait_time_ms,
        max_wait_time_ms
    FROM sys.dm_os_latch_stats
    WHERE wait_time_ms > 0
    ORDER BY wait_time_ms DESC
    """
    
    # Spinlock stats (SQL 2008 R2+)
    SPINLOCK_STATS = """
    SELECT TOP 10
        name,
        collisions,
        spins,
        spins_per_collision,
        sleep_time,
        backoffs
    FROM sys.dm_os_spinlock_stats
    WHERE collisions > 0
    ORDER BY spins DESC
    """


def get_wait_category(wait_type: str) -> WaitCategory:
    """Get category for a wait type"""
    return WAIT_CATEGORIES.get(wait_type, WaitCategory.OTHER)


def get_category_color(category: WaitCategory) -> str:
    """Get color for a wait category"""
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS[WaitCategory.OTHER])
