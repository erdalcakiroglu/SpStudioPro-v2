"""
Dashboard Queries - SQL Server monitoring metrics
"""


class DashboardQueries:
    """SQL queries for Dashboard metrics"""
    
    # ==========================================================================
    # PERFORMANCE METRICS
    # ==========================================================================
    
    # Active Sessions (excluding system processes)
    ACTIVE_SESSIONS = """
    SELECT COUNT(*) AS active_sessions
    FROM sys.dm_exec_sessions s
    WHERE s.is_user_process = 1
      AND s.session_id > 50
      AND s.status IN ('running', 'runnable')
      AND s.program_name NOT LIKE 'SQLAgent%'
      AND s.program_name NOT LIKE 'DatabaseMail%'
      AND s.program_name NOT LIKE 'Report Server%'
    """
    
    # CPU Usage (percentage)
    CPU_USAGE = """
    SELECT TOP 1
        CAST(100 - record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'INT') AS INT) AS cpu_percent
    FROM (
        SELECT TOP 1 
            CONVERT(XML, record) AS record
        FROM sys.dm_os_ring_buffers
        WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
          AND record LIKE '%<SystemHealth>%'
        ORDER BY timestamp DESC
    ) AS cpu_ring
    """
    
    # CPU Usage (alternative using performance counters)
    CPU_USAGE_ALT = """
    SELECT 
        CAST(
            (SELECT cntr_value FROM sys.dm_os_performance_counters 
             WHERE counter_name = 'CPU usage %' AND instance_name = '_Total')
        AS INT) AS cpu_percent
    """
    
    # Memory Usage
    MEMORY_USAGE = """
    SELECT 
        total_physical_memory_kb / 1024 AS total_memory_mb,
        available_physical_memory_kb / 1024 AS available_memory_mb,
        CAST((1.0 - (CAST(available_physical_memory_kb AS FLOAT) / total_physical_memory_kb)) * 100 AS INT) AS memory_percent
    FROM sys.dm_os_sys_memory
    """
    
    # SQL Server Memory Usage
    SQL_MEMORY_USAGE = """
    SELECT 
        physical_memory_in_use_kb / 1024 AS sql_memory_mb,
        locked_page_allocations_kb / 1024 AS locked_pages_mb,
        memory_utilization_percentage AS sql_memory_percent
    FROM sys.dm_os_process_memory
    """
    
    # Blocking Sessions
    BLOCKING_SESSIONS = """
    SELECT 
        COUNT(DISTINCT blocking_session_id) AS blocking_count,
        COUNT(*) AS blocked_count,
        MAX(wait_time / 1000) AS max_wait_seconds
    FROM sys.dm_exec_requests
    WHERE blocking_session_id > 0
    """
    
    # Batch Requests per Second
    BATCH_REQUESTS = """
    SELECT 
        cntr_value AS batch_requests_total
    FROM sys.dm_os_performance_counters
    WHERE counter_name = 'Batch Requests/sec'
      AND object_name LIKE '%SQL Statistics%'
    """
    
    # ==========================================================================
    # STORAGE & I/O METRICS
    # ==========================================================================
    
    # Disk IOPS (Read/Write)
    DISK_IOPS = """
    SELECT 
        SUM(num_of_reads) AS total_reads,
        SUM(num_of_writes) AS total_writes,
        SUM(num_of_bytes_read) / 1024 / 1024 AS total_read_mb,
        SUM(num_of_bytes_written) / 1024 / 1024 AS total_write_mb
    FROM sys.dm_io_virtual_file_stats(NULL, NULL)
    """
    
    # Disk Latency (ms)
    DISK_LATENCY = """
    SELECT 
        AVG(CASE WHEN num_of_reads > 0 
            THEN CAST(io_stall_read_ms AS FLOAT) / num_of_reads 
            ELSE 0 END) AS avg_read_latency_ms,
        AVG(CASE WHEN num_of_writes > 0 
            THEN CAST(io_stall_write_ms AS FLOAT) / num_of_writes 
            ELSE 0 END) AS avg_write_latency_ms,
        AVG(CASE WHEN (num_of_reads + num_of_writes) > 0 
            THEN CAST(io_stall AS FLOAT) / (num_of_reads + num_of_writes) 
            ELSE 0 END) AS avg_total_latency_ms
    FROM sys.dm_io_virtual_file_stats(NULL, NULL)
    """
    
    # Page Life Expectancy
    PAGE_LIFE_EXPECTANCY = """
    SELECT 
        cntr_value AS ple_seconds
    FROM sys.dm_os_performance_counters
    WHERE counter_name = 'Page life expectancy'
      AND object_name LIKE '%Buffer Manager%'
    """
    
    # TempDB Usage
    TEMPDB_USAGE = """
    SELECT 
        SUM(user_object_reserved_page_count + internal_object_reserved_page_count + 
            version_store_reserved_page_count + mixed_extent_page_count) * 8 / 1024 AS used_mb,
        SUM(unallocated_extent_page_count) * 8 / 1024 AS free_mb,
        CAST(
            SUM(user_object_reserved_page_count + internal_object_reserved_page_count + 
                version_store_reserved_page_count + mixed_extent_page_count) * 100.0 /
            NULLIF(SUM(user_object_reserved_page_count + internal_object_reserved_page_count + 
                version_store_reserved_page_count + mixed_extent_page_count + unallocated_extent_page_count), 0)
        AS INT) AS usage_percent
    FROM tempdb.sys.dm_db_file_space_usage
    """
    
    # ==========================================================================
    # ALERTS & MAINTENANCE
    # ==========================================================================
    
    # Last Backup Dates (per database)
    LAST_BACKUPS = """
    SELECT 
        d.name AS database_name,
        MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END) AS last_full_backup,
        MAX(CASE WHEN b.type = 'I' THEN b.backup_finish_date END) AS last_diff_backup,
        MAX(CASE WHEN b.type = 'L' THEN b.backup_finish_date END) AS last_log_backup,
        DATEDIFF(HOUR, MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END), GETDATE()) AS hours_since_full,
        DATEDIFF(MINUTE, MAX(CASE WHEN b.type = 'L' THEN b.backup_finish_date END), GETDATE()) AS minutes_since_log
    FROM sys.databases d
    LEFT JOIN msdb.dbo.backupset b ON d.name = b.database_name
    WHERE d.database_id > 4  -- Exclude system databases
      AND d.state = 0  -- Online
    GROUP BY d.name
    ORDER BY hours_since_full DESC
    """
    
    # Summary of Last Backups (aggregated)
    BACKUP_SUMMARY = """
    SELECT 
        COUNT(DISTINCT CASE WHEN hours_since_full IS NULL OR hours_since_full > 24 THEN database_name END) AS no_recent_full,
        COUNT(DISTINCT CASE WHEN hours_since_full <= 24 THEN database_name END) AS recent_full_count,
        MIN(last_full_backup) AS oldest_full_backup,
        MAX(last_full_backup) AS newest_full_backup
    FROM (
        SELECT 
            d.name AS database_name,
            MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END) AS last_full_backup,
            DATEDIFF(HOUR, MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END), GETDATE()) AS hours_since_full
        FROM sys.databases d
        LEFT JOIN msdb.dbo.backupset b ON d.name = b.database_name
        WHERE d.database_id > 4 AND d.state = 0
        GROUP BY d.name
    ) x
    """
    
    # Error Log Critical Errors (last 24 hours) - using temp table approach
    ERROR_LOG_CRITICAL = """
    CREATE TABLE #ErrorLog (
        LogDate DATETIME,
        ProcessInfo NVARCHAR(100),
        Text NVARCHAR(MAX)
    );
    
    INSERT INTO #ErrorLog
    EXEC xp_readerrorlog 0, 1, N'Error';
    
    SELECT TOP 10
        LogDate,
        ProcessInfo,
        Text AS ErrorMessage
    FROM #ErrorLog
    WHERE LogDate > DATEADD(HOUR, -24, GETDATE())
    ORDER BY LogDate DESC;
    
    DROP TABLE #ErrorLog;
    """
    
    # Error Log Count (last 24 hours) - simplified
    ERROR_LOG_COUNT = """
    CREATE TABLE #ErrorLog (
        LogDate DATETIME,
        ProcessInfo NVARCHAR(100),
        Text NVARCHAR(MAX)
    );
    
    INSERT INTO #ErrorLog
    EXEC xp_readerrorlog 0, 1, N'Error';
    
    SELECT COUNT(*) AS error_count
    FROM #ErrorLog
    WHERE LogDate > DATEADD(HOUR, -24, GETDATE());
    
    DROP TABLE #ErrorLog;
    """
    
    # Severity errors from sys.messages (alternative)
    SEVERITY_ERRORS = """
    SELECT COUNT(*) AS critical_count
    FROM sys.dm_exec_requests r
    WHERE r.status = 'suspended'
      AND r.wait_type LIKE '%ERROR%'
    """
    
    # Failed Jobs (last 24 hours)
    FAILED_JOBS = """
    SELECT 
        j.name AS job_name,
        h.step_name,
        h.message,
        msdb.dbo.agent_datetime(h.run_date, h.run_time) AS run_datetime,
        h.run_duration
    FROM msdb.dbo.sysjobs j
    JOIN msdb.dbo.sysjobhistory h ON j.job_id = h.job_id
    WHERE h.run_status = 0  -- Failed
      AND h.step_id > 0  -- Exclude job outcome row
      AND msdb.dbo.agent_datetime(h.run_date, h.run_time) > DATEADD(HOUR, -24, GETDATE())
    ORDER BY msdb.dbo.agent_datetime(h.run_date, h.run_time) DESC
    """
    
    # Failed Jobs Count
    FAILED_JOBS_COUNT = """
    SELECT 
        COUNT(DISTINCT j.job_id) AS failed_job_count,
        COUNT(*) AS total_failures
    FROM msdb.dbo.sysjobs j
    JOIN msdb.dbo.sysjobhistory h ON j.job_id = h.job_id
    WHERE h.run_status = 0
      AND h.step_id > 0
      AND msdb.dbo.agent_datetime(h.run_date, h.run_time) > DATEADD(HOUR, -24, GETDATE())
    """
    
    # ==========================================================================
    # ADDITIONAL METRICS
    # ==========================================================================
    
    # Slow Queries (last hour)
    SLOW_QUERIES_COUNT = """
    SELECT COUNT(*) AS slow_query_count
    FROM sys.dm_exec_query_stats qs
    WHERE qs.last_execution_time > DATEADD(HOUR, -1, GETDATE())
      AND (qs.total_elapsed_time / NULLIF(qs.execution_count, 0)) / 1000 > 1000  -- > 1 second avg
    """
    
    # Top Wait Type
    TOP_WAIT_TYPE = """
    SELECT TOP 1
        wait_type,
        wait_time_ms,
        CAST(wait_time_ms * 100.0 / NULLIF(SUM(wait_time_ms) OVER(), 0) AS DECIMAL(5,2)) AS wait_percent
    FROM sys.dm_os_wait_stats
    WHERE wait_type NOT IN (
        'SLEEP_TASK', 'BROKER_TASK_STOP', 'BROKER_TO_FLUSH', 'CLR_AUTO_EVENT',
        'CLR_MANUAL_EVENT', 'CLR_SEMAPHORE', 'DBMIRROR_DBM_EVENT', 'DBMIRROR_EVENTS_QUEUE',
        'DBMIRROR_WORKER_QUEUE', 'DBMIRRORING_CMD', 'DIRTY_PAGE_POLL', 'DISPATCHER_QUEUE_SEMAPHORE',
        'FT_IFTS_SCHEDULER_IDLE_WAIT', 'FT_IFTSHC_MUTEX', 'HADR_CLUSAPI_CALL', 'HADR_FILESTREAM_IOMGR_IOCOMPLETION',
        'HADR_LOGCAPTURE_WAIT', 'HADR_NOTIFICATION_DEQUEUE', 'HADR_TIMER_TASK', 'HADR_WORK_QUEUE',
        'LAZYWRITER_SLEEP', 'LOGMGR_QUEUE', 'ONDEMAND_TASK_QUEUE', 'PARALLEL_REDO_WORKER_WAIT_WORK',
        'PREEMPTIVE_HADR_LEASE_MECHANISM', 'PREEMPTIVE_SP_SERVER_DIAGNOSTICS', 'QDS_ASYNC_QUEUE',
        'QDS_CLEANUP_STALE_QUERIES_TASK_MAIN_LOOP_SLEEP', 'QDS_PERSIST_TASK_MAIN_LOOP_SLEEP',
        'REQUEST_FOR_DEADLOCK_SEARCH', 'SLEEP_SYSTEMTASK', 'SQLTRACE_BUFFER_FLUSH',
        'SQLTRACE_INCREMENTAL_FLUSH_SLEEP', 'WAITFOR', 'XE_DISPATCHER_WAIT', 'XE_TIMER_EVENT',
        'CHECKPOINT_QUEUE', 'CHKPT', 'BROKER_RECEIVE_WAITFOR', 'WAIT_XTP_CKPT_CLOSE'
    )
      AND wait_time_ms > 0
    ORDER BY wait_time_ms DESC
    """
    
    # All metrics in one query (combined for efficiency)
    ALL_METRICS = """
    SELECT
        -- Sessions
        (SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE is_user_process = 1) AS active_sessions,
        
        -- Blocking
        (SELECT COUNT(DISTINCT blocking_session_id) FROM sys.dm_exec_requests WHERE blocking_session_id > 0) AS blocking_count,
        
        -- PLE
        (SELECT cntr_value FROM sys.dm_os_performance_counters 
         WHERE counter_name = 'Page life expectancy' AND object_name LIKE '%Buffer Manager%') AS ple_seconds,
        
        -- Batch Requests
        (SELECT cntr_value FROM sys.dm_os_performance_counters 
         WHERE counter_name = 'Batch Requests/sec') AS batch_requests,
        
        -- Memory
        (SELECT memory_utilization_percentage FROM sys.dm_os_process_memory) AS sql_memory_percent
    """
