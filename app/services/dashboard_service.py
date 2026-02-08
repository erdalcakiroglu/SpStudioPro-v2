"""
Dashboard Service - Server monitoring metrics
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from app.database.connection import get_connection_manager
from app.database.queries.dashboard_queries import DashboardQueries
from app.core.logger import get_logger

logger = get_logger('services.dashboard')


@dataclass
class DashboardMetrics:
    """Dashboard metrics data model - Extended for GUI-05 style dashboard"""
    
    # ---------------------------------------------------------------------
    # SERVER HEALTH
    # ---------------------------------------------------------------------
    active_sessions: int = 0
    cpu_percent: int = 0  # OS Total CPU
    sql_cpu_percent: int = 0  # SQL Process CPU
    runnable_queue: int = 0  # SUM(current_tasks_count - active_workers_count) over schedulers
    workers_count: int = 0  # SUM(current_workers_count) over schedulers
    
    # ---------------------------------------------------------------------
    # MEMORY HEALTH
    # ---------------------------------------------------------------------
    total_server_memory_mb: int = 0
    target_server_memory_mb: int = 0
    available_memory_mb: int = 0  # Available OS Memory (kept; not always shown)
    ple_seconds: int = 0  # Page Life Expectancy
    buffer_cache_hit_ratio: int = 99  # Buffer Cache Hit %
    
    # ---------------------------------------------------------------------
    # WORKLOAD
    # ---------------------------------------------------------------------
    batch_requests: int = 0  # Batch Requests/sec (calculated)
    transactions_per_sec: int = 0  # Transactions/sec (calculated)
    compilations_per_sec: int = 0  # SQL Compilations/sec (calculated)
    recompilations_per_sec: int = 0  # SQL Re-Compilations/sec (calculated)

    # ---------------------------------------------------------------------
    # IO
    # ---------------------------------------------------------------------
    read_latency_ms: float = 0.0  # IO Read Latency
    write_latency_ms: float = 0.0  # IO Write Latency
    log_write_latency_ms: float = 0.0  # Log Write Latency
    disk_queue_length: int = 0  # Pending IO requests (proxy)
    most_stressed_db: str = ""  # DB name (best-effort)
    most_stressed_db_latency_ms: float = 0.0  # Avg latency for selected DB
    
    # ---------------------------------------------------------------------
    # TEMPDB
    # ---------------------------------------------------------------------
    tempdb_usage_percent: int = 0  # TempDB Usage %
    tempdb_log_used_percent: int = 0  # TempDB Log Used %
    pfs_gam_waits: int = 0  # Current PFS/GAM/SGAM latch waits (best-effort)

    # ---------------------------------------------------------------------
    # WAIT CATEGORIES
    # ---------------------------------------------------------------------
    cpu_wait_percent: int = 0
    io_wait_percent: int = 0
    lock_wait_percent: int = 0
    memory_wait_percent: int = 0
    signal_wait_percent: int = 0  # Signal Wait % (kept; used elsewhere)

    # ---------------------------------------------------------------------
    # BLOCKING (legacy / optional)
    # ---------------------------------------------------------------------
    blocked_sessions: int = 0  # Blocked Sessions count
    blocking_spid: int = 0  # Head blocker SPID
    runnable_tasks: int = 0  # Legacy runnable tasks count (older definition)
    tempdb_percent: int = 0  # Legacy TempDB percent (kept; mapped to tempdb_log_used_percent)
    
    # Legacy fields (for backward compatibility)
    memory_percent: int = 0
    blocking_count: int = 0
    disk_read_iops: int = 0
    disk_write_iops: int = 0
    disk_latency_ms: float = 0.0
    slow_queries: int = 0
    
    # Alerts
    last_full_backup: Optional[datetime] = None
    hours_since_full: int = 0
    last_log_backup: Optional[datetime] = None
    minutes_since_log: int = 0
    error_count: int = 0
    failed_jobs: int = 0
    
    # Top Wait
    top_wait_type: str = ""
    top_wait_ms: int = 0
    
    # Timestamp
    collected_at: datetime = field(default_factory=datetime.now)


class DashboardService:
    """
    Service for collecting dashboard metrics
    """
    
    _instance: Optional['DashboardService'] = None
    _last_batch_requests: int = 0
    _last_batch_time: Optional[datetime] = None
    _last_transactions: int = 0
    _last_transactions_time: Optional[datetime] = None
    _last_compilations: int = 0
    _last_compilations_time: Optional[datetime] = None
    _last_recompilations: int = 0
    _last_recompilations_time: Optional[datetime] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def connection(self):
        """Get active database connection"""
        conn_mgr = get_connection_manager()
        return conn_mgr.active_connection
    
    @property
    def is_connected(self) -> bool:
        """Check if connected"""
        conn = self.connection
        return conn is not None and conn.is_connected
    
    def get_all_metrics(self) -> DashboardMetrics:
        """Collect all dashboard metrics - Extended for GUI-05 style dashboard"""
        metrics = DashboardMetrics()
        
        if not self.is_connected:
            logger.warning("No active connection for dashboard metrics")
            return metrics
        
        conn = self.connection
        
        try:
            # Server Health
            metrics.active_sessions = self._get_active_sessions(conn)
            cpu_info = self._get_cpu_info(conn)
            metrics.cpu_percent = cpu_info.get('os_cpu', 0)
            metrics.sql_cpu_percent = cpu_info.get('sql_cpu', 0)
            sched = self._get_scheduler_health(conn)
            metrics.runnable_queue = sched.get('runnable_queue', 0)
            metrics.workers_count = sched.get('workers_count', 0)
            
            # Memory Health
            mem_mgr = self._get_sql_memory_manager(conn)
            metrics.total_server_memory_mb = mem_mgr.get('total_server_memory_mb', 0)
            metrics.target_server_memory_mb = mem_mgr.get('target_server_memory_mb', 0)
            metrics.available_memory_mb = self._get_available_memory(conn)  # informational
            metrics.ple_seconds = self._get_ple(conn)
            metrics.buffer_cache_hit_ratio = self._get_buffer_cache_hit(conn)

            # Workload
            metrics.batch_requests = self._get_batch_requests(conn)
            metrics.transactions_per_sec = self._get_transactions_per_sec(conn)
            metrics.compilations_per_sec = self._get_compilations_per_sec(conn)
            metrics.recompilations_per_sec = self._get_recompilations_per_sec(conn)
            
            # IO
            latencies = self._get_io_latencies(conn)
            metrics.read_latency_ms = latencies.get('read', 0)
            metrics.write_latency_ms = latencies.get('write', 0)
            metrics.log_write_latency_ms = latencies.get('log', 0)
            metrics.disk_queue_length = self._get_disk_queue_length(conn)

            # Waits
            metrics.signal_wait_percent = self._get_signal_wait_percent(conn)
            wait_cats = self._get_wait_category_percents(conn)
            metrics.cpu_wait_percent = wait_cats.get('cpu_wait_percent', 0)
            metrics.io_wait_percent = wait_cats.get('io_wait_percent', 0)
            metrics.lock_wait_percent = wait_cats.get('lock_wait_percent', 0)
            metrics.memory_wait_percent = wait_cats.get('memory_wait_percent', 0)
            
            # TempDB
            metrics.tempdb_usage_percent = self._get_tempdb_usage(conn)
            metrics.tempdb_log_used_percent = self._get_tempdb_log_used(conn)
            metrics.pfs_gam_waits = self._get_tempdb_pfs_gam_waits(conn)
            metrics.tempdb_percent = metrics.tempdb_log_used_percent  # Legacy mapping

            # Blocking (optional)
            blocking_info = self._get_blocking_info(conn)
            metrics.blocked_sessions = blocking_info.get('blocked_count', 0)
            metrics.blocking_spid = blocking_info.get('head_blocker', 0)
            metrics.blocking_count = metrics.blocked_sessions  # Legacy
            metrics.runnable_tasks = self._get_runnable_tasks(conn)
            
            # Legacy: disk latency (average of read/write)
            metrics.disk_latency_ms = (metrics.read_latency_ms + metrics.write_latency_ms) / 2
            
            # Legacy: memory percent
            metrics.memory_percent = self._get_memory_usage(conn)
            
            # Storage I/O
            disk_iops = self._get_disk_iops(conn)
            metrics.disk_read_iops = disk_iops.get('reads', 0)
            metrics.disk_write_iops = disk_iops.get('writes', 0)
            
            # Alerts
            backup_info = self._get_backup_info(conn)
            metrics.last_full_backup = backup_info.get('last_full')
            metrics.hours_since_full = backup_info.get('hours_since_full', 0)
            metrics.last_log_backup = backup_info.get('last_log')
            metrics.minutes_since_log = backup_info.get('minutes_since_log', 0)
            
            metrics.failed_jobs = self._get_failed_jobs_count(conn)
            metrics.error_count = self._get_error_log_count(conn)
            metrics.slow_queries = self._get_slow_queries(conn)
            
            # Top Wait
            wait_info = self._get_top_wait(conn)
            metrics.top_wait_type = wait_info.get('wait_type', '')
            metrics.top_wait_ms = wait_info.get('wait_ms', 0)
            
            metrics.collected_at = datetime.now()
            
        except Exception as e:
            logger.error(f"Error collecting dashboard metrics: {e}")
        
        return metrics
    
    def _get_active_sessions(self, conn) -> int:
        """Get active session count"""
        try:
            result = conn.execute_query(DashboardQueries.ACTIVE_SESSIONS)
            if result:
                return result[0].get('active_sessions', 0)
        except Exception as e:
            logger.warning(f"Error getting active sessions: {e}")
        return 0
    
    def _get_cpu_usage(self, conn) -> int:
        """Get CPU usage percentage"""
        try:
            result = conn.execute_query(DashboardQueries.CPU_USAGE)
            if result:
                return result[0].get('cpu_percent', 0) or 0
        except Exception:
            # Try alternative query
            try:
                result = conn.execute_query(DashboardQueries.CPU_USAGE_ALT)
                if result:
                    return result[0].get('cpu_percent', 0) or 0
            except Exception as e:
                logger.warning(f"Error getting CPU usage: {e}")
        return 0
    
    def _get_memory_usage(self, conn) -> int:
        """Get memory usage percentage"""
        try:
            result = conn.execute_query(DashboardQueries.SQL_MEMORY_USAGE)
            if result:
                return result[0].get('sql_memory_percent', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting memory usage: {e}")
        return 0
    
    def _get_blocking_count(self, conn) -> int:
        """Get blocking session count"""
        try:
            result = conn.execute_query(DashboardQueries.BLOCKING_SESSIONS)
            if result:
                return result[0].get('blocking_count', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting blocking count: {e}")
        return 0
    
    def _get_batch_requests(self, conn) -> int:
        """Get batch requests per second (calculated)"""
        try:
            result = conn.execute_query(DashboardQueries.BATCH_REQUESTS)
            if result:
                current_value = result[0].get('batch_requests_total', 0) or 0
                current_time = datetime.now()
                
                if self._last_batch_requests > 0 and self._last_batch_time:
                    elapsed = (current_time - self._last_batch_time).total_seconds()
                    if elapsed > 0:
                        batch_per_sec = int((current_value - self._last_batch_requests) / elapsed)
                        self._last_batch_requests = current_value
                        self._last_batch_time = current_time
                        return max(0, batch_per_sec)
                
                self._last_batch_requests = current_value
                self._last_batch_time = current_time
                return 0
        except Exception as e:
            logger.warning(f"Error getting batch requests: {e}")
        return 0
    
    def _get_ple(self, conn) -> int:
        """Get Page Life Expectancy"""
        try:
            result = conn.execute_query(DashboardQueries.PAGE_LIFE_EXPECTANCY)
            if result:
                return result[0].get('ple_seconds', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting PLE: {e}")
        return 0
    
    def _get_tempdb_usage(self, conn) -> int:
        """Get TempDB usage percentage"""
        try:
            result = conn.execute_query(DashboardQueries.TEMPDB_USAGE)
            if result:
                return result[0].get('usage_percent', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting TempDB usage: {e}")
        return 0
    
    def _get_slow_queries(self, conn) -> int:
        """Get slow queries count (last hour)"""
        try:
            result = conn.execute_query(DashboardQueries.SLOW_QUERIES_COUNT)
            if result:
                return result[0].get('slow_query_count', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting slow queries: {e}")
        return 0
    
    def _get_disk_latency(self, conn) -> float:
        """Get average disk latency"""
        try:
            result = conn.execute_query(DashboardQueries.DISK_LATENCY)
            if result:
                return result[0].get('avg_total_latency_ms', 0) or 0.0
        except Exception as e:
            logger.warning(f"Error getting disk latency: {e}")
        return 0.0
    
    def _get_disk_iops(self, conn) -> Dict[str, int]:
        """Get disk IOPS"""
        try:
            result = conn.execute_query(DashboardQueries.DISK_IOPS)
            if result:
                return {
                    'reads': result[0].get('total_reads', 0) or 0,
                    'writes': result[0].get('total_writes', 0) or 0
                }
        except Exception as e:
            logger.warning(f"Error getting disk IOPS: {e}")
        return {'reads': 0, 'writes': 0}
    
    def _get_backup_info(self, conn) -> Dict[str, Any]:
        """Get backup information"""
        try:
            result = conn.execute_query(DashboardQueries.BACKUP_SUMMARY)
            if result:
                row = result[0]
                return {
                    'no_recent_full': row.get('no_recent_full', 0) or 0,
                    'last_full': row.get('newest_full_backup'),
                    'hours_since_full': 0,  # Calculate if needed
                    'last_log': None,
                    'minutes_since_log': 0
                }
        except Exception as e:
            logger.warning(f"Error getting backup info: {e}")
        return {}
    
    def _get_failed_jobs_count(self, conn) -> int:
        """Get failed jobs count (last 24 hours)"""
        try:
            result = conn.execute_query(DashboardQueries.FAILED_JOBS_COUNT)
            if result:
                return result[0].get('failed_job_count', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting failed jobs: {e}")
        return 0
    
    def _get_error_log_count(self, conn) -> int:
        """Get error log count (last 24 hours)"""
        try:
            # Avoid xp_readerrorlog if permission is missing.
            try:
                perm = conn.execute_query(DashboardQueries.ERROR_LOG_CAN_READ)
                can_exec = (perm and (perm[0].get("can_exec", 0) or 0) == 1)
            except Exception:
                can_exec = False

            if not can_exec:
                result = conn.execute_query(DashboardQueries.ERROR_LOG_COUNT_FALLBACK)
                if result:
                    return result[0].get('error_count', 0) or 0
                return 0

            result = conn.execute_query(DashboardQueries.ERROR_LOG_COUNT)
            if result:
                return result[0].get('error_count', 0) or 0
        except Exception as e:
            # xp_readerrorlog may require sysadmin; always fallback quietly.
            logger.info("Error log count via xp_readerrorlog failed; using ring buffer fallback.")
            try:
                result = conn.execute_query(DashboardQueries.ERROR_LOG_COUNT_FALLBACK)
                if result:
                    return result[0].get('error_count', 0) or 0
            except Exception as fallback_error:
                logger.warning(f"Error getting error log count (fallback): {fallback_error}")
        return 0
    
    def get_error_log_details(self) -> list:
        """Get error log details (last 24 hours)"""
        if not self.is_connected:
            return []
        
        try:
            result = self.connection.execute_query(DashboardQueries.ERROR_LOG_CRITICAL)
            return result or []
        except Exception as e:
            logger.warning(f"Error getting error log details: {e}")
        return []
    
    def _get_top_wait(self, conn) -> Dict[str, Any]:
        """Get top wait type"""
        try:
            result = conn.execute_query(DashboardQueries.TOP_WAIT_TYPE)
            if result:
                return {
                    'wait_type': result[0].get('wait_type', ''),
                    'wait_ms': result[0].get('wait_time_ms', 0) or 0
                }
        except Exception as e:
            logger.warning(f"Error getting top wait: {e}")
        return {'wait_type': '', 'wait_ms': 0}
    
    # =========================================================================
    # NEW METRICS FOR GUI-05 STYLE DASHBOARD
    # =========================================================================
    
    def _get_cpu_info(self, conn) -> Dict[str, int]:
        """Get both OS and SQL CPU usage"""
        try:
            query = """
            SELECT TOP 1
                record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int') AS system_idle,
                record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') AS sql_cpu
            FROM (
                SELECT TOP 1 CONVERT(xml, record) AS record
                FROM sys.dm_os_ring_buffers
                WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
                ORDER BY timestamp DESC
            ) AS x
            """
            result = conn.execute_query(query)
            if result:
                system_idle = result[0].get('system_idle', 100) or 100
                sql_cpu = result[0].get('sql_cpu', 0) or 0
                os_cpu = 100 - system_idle
                return {'os_cpu': os_cpu, 'sql_cpu': sql_cpu}
        except Exception as e:
            logger.warning(f"Error getting CPU info: {e}")
            # Fallback to simple CPU query
            cpu = self._get_cpu_usage(conn)
            return {'os_cpu': cpu, 'sql_cpu': cpu}
        return {'os_cpu': 0, 'sql_cpu': 0}
    
    def _get_available_memory(self, conn) -> int:
        """Get available OS memory in MB"""
        try:
            query = """
            SELECT available_physical_memory_kb / 1024 AS available_mb
            FROM sys.dm_os_sys_memory
            """
            result = conn.execute_query(query)
            if result:
                return result[0].get('available_mb', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting available memory: {e}")
        return 0

    def _get_scheduler_health(self, conn) -> Dict[str, int]:
        """
        Get scheduler health signals.

        Runnable Queue Pressure (requested definition):
        SUM(current_tasks_count - active_workers_count) across VISIBLE ONLINE schedulers.
        """
        try:
            query = """
            SELECT
                SUM(
                    CASE
                        WHEN current_tasks_count > active_workers_count
                            THEN current_tasks_count - active_workers_count
                        ELSE 0
                    END
                ) AS runnable_queue,
                SUM(current_workers_count) AS workers_count
            FROM sys.dm_os_schedulers
            WHERE status = 'VISIBLE ONLINE'
              AND is_online = 1
            """
            result = conn.execute_query(query)
            if result:
                return {
                    'runnable_queue': result[0].get('runnable_queue', 0) or 0,
                    'workers_count': result[0].get('workers_count', 0) or 0,
                }
        except Exception as e:
            logger.warning(f"Error getting scheduler health: {e}")
        return {'runnable_queue': 0, 'workers_count': 0}

    def _get_sql_memory_manager(self, conn) -> Dict[str, int]:
        """Get SQL Server Total/Target Server Memory from performance counters (MB)."""
        try:
            query = """
            SELECT
                CAST(MAX(CASE WHEN counter_name = 'Total Server Memory (KB)' THEN cntr_value END) / 1024 AS INT) AS total_server_memory_mb,
                CAST(MAX(CASE WHEN counter_name = 'Target Server Memory (KB)' THEN cntr_value END) / 1024 AS INT) AS target_server_memory_mb
            FROM sys.dm_os_performance_counters
            WHERE object_name LIKE '%Memory Manager%'
              AND counter_name IN ('Total Server Memory (KB)', 'Target Server Memory (KB)')
            """
            result = conn.execute_query(query)
            if result:
                return {
                    'total_server_memory_mb': result[0].get('total_server_memory_mb', 0) or 0,
                    'target_server_memory_mb': result[0].get('target_server_memory_mb', 0) or 0,
                }
        except Exception as e:
            logger.warning(f"Error getting SQL memory manager counters: {e}")
        return {'total_server_memory_mb': 0, 'target_server_memory_mb': 0}
    
    def _get_buffer_cache_hit(self, conn) -> int:
        """Get buffer cache hit ratio percentage"""
        try:
            query = """
            SELECT 
                CAST(
                    (CAST(a.cntr_value AS DECIMAL(18,2)) / 
                     NULLIF(CAST(b.cntr_value AS DECIMAL(18,2)), 0)) * 100.0 
                AS INT) AS buffer_cache_hit_ratio
            FROM sys.dm_os_performance_counters a
            JOIN sys.dm_os_performance_counters b 
                ON a.object_name = b.object_name
            WHERE a.counter_name = 'Buffer cache hit ratio'
              AND b.counter_name = 'Buffer cache hit ratio base'
              AND a.object_name LIKE '%Buffer Manager%'
            """
            result = conn.execute_query(query)
            if result:
                return result[0].get('buffer_cache_hit_ratio', 99) or 99
        except Exception as e:
            logger.warning(f"Error getting buffer cache hit: {e}")
        return 99
    
    def _get_transactions_per_sec(self, conn) -> int:
        """Get transactions per second (calculated)"""
        try:
            query = """
            SELECT cntr_value AS transactions_per_sec
            FROM sys.dm_os_performance_counters
            WHERE counter_name = 'Transactions/sec'
              AND instance_name = '_Total'
            """
            result = conn.execute_query(query)
            if result:
                current_value = result[0].get('transactions_per_sec', 0) or 0
                current_time = datetime.now()

                if self._last_transactions > 0 and self._last_transactions_time:
                    elapsed = (current_time - self._last_transactions_time).total_seconds()
                    if elapsed > 0:
                        delta = current_value - self._last_transactions
                        if delta < 0:
                            # Counter reset or wrap; restart baseline
                            self._last_transactions = current_value
                            self._last_transactions_time = current_time
                            return 0
                        tx_per_sec = int(delta / elapsed)
                        self._last_transactions = current_value
                        self._last_transactions_time = current_time
                        return max(0, tx_per_sec)

                self._last_transactions = current_value
                self._last_transactions_time = current_time
                return 0
        except Exception as e:
            logger.warning(f"Error getting transactions/sec: {e}")
        return 0

    def _get_compilations_per_sec(self, conn) -> int:
        """Get SQL Compilations/sec (calculated from bulk counter)."""
        try:
            query = """
            SELECT cntr_value AS compilations_total
            FROM sys.dm_os_performance_counters
            WHERE counter_name = 'SQL Compilations/sec'
              AND object_name LIKE '%SQL Statistics%'
            """
            result = conn.execute_query(query)
            if result:
                current_value = result[0].get('compilations_total', 0) or 0
                current_time = datetime.now()

                if self._last_compilations > 0 and self._last_compilations_time:
                    elapsed = (current_time - self._last_compilations_time).total_seconds()
                    if elapsed > 0:
                        delta = current_value - self._last_compilations
                        if delta < 0:
                            self._last_compilations = current_value
                            self._last_compilations_time = current_time
                            return 0
                        per_sec = int(delta / elapsed)
                        self._last_compilations = current_value
                        self._last_compilations_time = current_time
                        return max(0, per_sec)

                self._last_compilations = current_value
                self._last_compilations_time = current_time
                return 0
        except Exception as e:
            logger.warning(f"Error getting compilations/sec: {e}")
        return 0

    def _get_recompilations_per_sec(self, conn) -> int:
        """Get SQL Re-Compilations/sec (calculated from bulk counter)."""
        try:
            query = """
            SELECT cntr_value AS recompilations_total
            FROM sys.dm_os_performance_counters
            WHERE counter_name = 'SQL Re-Compilations/sec'
              AND object_name LIKE '%SQL Statistics%'
            """
            result = conn.execute_query(query)
            if result:
                current_value = result[0].get('recompilations_total', 0) or 0
                current_time = datetime.now()

                if self._last_recompilations > 0 and self._last_recompilations_time:
                    elapsed = (current_time - self._last_recompilations_time).total_seconds()
                    if elapsed > 0:
                        delta = current_value - self._last_recompilations
                        if delta < 0:
                            self._last_recompilations = current_value
                            self._last_recompilations_time = current_time
                            return 0
                        per_sec = int(delta / elapsed)
                        self._last_recompilations = current_value
                        self._last_recompilations_time = current_time
                        return max(0, per_sec)

                self._last_recompilations = current_value
                self._last_recompilations_time = current_time
                return 0
        except Exception as e:
            logger.warning(f"Error getting re-compilations/sec: {e}")
        return 0
    
    def _get_io_latencies(self, conn) -> Dict[str, float]:
        """Get read, write, and log write latencies in ms"""
        try:
            query = """
            SELECT 
                AVG(CASE WHEN num_of_reads > 0 
                    THEN CAST(io_stall_read_ms AS FLOAT) / num_of_reads 
                    ELSE 0 END) AS avg_read_latency_ms,
                AVG(CASE WHEN num_of_writes > 0 
                    THEN CAST(io_stall_write_ms AS FLOAT) / num_of_writes 
                    ELSE 0 END) AS avg_write_latency_ms
            FROM sys.dm_io_virtual_file_stats(NULL, NULL)
            """
            result = conn.execute_query(query)
            read_lat = 0.0
            write_lat = 0.0
            if result:
                read_lat = result[0].get('avg_read_latency_ms', 0) or 0
                write_lat = result[0].get('avg_write_latency_ms', 0) or 0
            
            # Get log write latency separately
            log_query = """
            SELECT 
                AVG(CASE WHEN num_of_writes > 0 
                    THEN CAST(io_stall_write_ms AS FLOAT) / num_of_writes 
                    ELSE 0 END) AS avg_log_latency_ms
            FROM sys.dm_io_virtual_file_stats(NULL, NULL) vfs
            JOIN sys.master_files mf ON vfs.database_id = mf.database_id 
                AND vfs.file_id = mf.file_id
            WHERE mf.type_desc = 'LOG'
            """
            log_result = conn.execute_query(log_query)
            log_lat = 0.0
            if log_result:
                log_lat = log_result[0].get('avg_log_latency_ms', 0) or 0
            
            return {'read': read_lat, 'write': write_lat, 'log': log_lat}
        except Exception as e:
            logger.warning(f"Error getting IO latencies: {e}")
        return {'read': 0, 'write': 0, 'log': 0}

    def _get_disk_queue_length(self, conn) -> int:
        """Best-effort disk queue length proxy using pending IO requests."""
        try:
            query = "SELECT COUNT(*) AS disk_queue_length FROM sys.dm_io_pending_io_requests"
            result = conn.execute_query(query)
            if result:
                return result[0].get('disk_queue_length', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting disk queue length: {e}")
        return 0

    def _get_most_stressed_db(self, conn) -> Dict[str, Any]:
        """Return DB with highest average IO latency (best-effort, cumulative)."""
        try:
            query = """
            WITH dbio AS (
                SELECT
                    database_id,
                    SUM(io_stall_read_ms + io_stall_write_ms) AS stall_ms,
                    SUM(num_of_reads + num_of_writes) AS io_count
                FROM sys.dm_io_virtual_file_stats(NULL, NULL)
                GROUP BY database_id
            )
            SELECT TOP 1
                DB_NAME(database_id) AS database_name,
                CAST(CASE WHEN io_count > 0 THEN stall_ms * 1.0 / io_count ELSE 0 END AS DECIMAL(10,2)) AS avg_latency_ms
            FROM dbio
            WHERE database_id NOT IN (32767)
            ORDER BY avg_latency_ms DESC, stall_ms DESC
            """
            result = conn.execute_query(query)
            if result:
                return {
                    'database_name': result[0].get('database_name') or '',
                    'avg_latency_ms': float(result[0].get('avg_latency_ms', 0) or 0),
                }
        except Exception as e:
            logger.warning(f"Error getting most stressed DB: {e}")
        return {'database_name': '', 'avg_latency_ms': 0.0}
    
    def _get_signal_wait_percent(self, conn) -> int:
        """Get signal wait percentage (CPU scheduler inefficiency)"""
        try:
            query = """
            SELECT 
                CASE WHEN SUM(wait_time_ms) > 0 
                    THEN CAST(SUM(signal_wait_time_ms) * 100.0 / SUM(wait_time_ms) AS INT)
                    ELSE 0 
                END AS signal_wait_percent
            FROM sys.dm_os_wait_stats
            WHERE wait_type NOT IN (
                'CLR_SEMAPHORE', 'LAZYWRITER_SLEEP', 'RESOURCE_QUEUE', 
                'SLEEP_TASK', 'SLEEP_SYSTEMTASK', 'SQLTRACE_BUFFER_FLUSH', 
                'WAITFOR', 'LOGMGR_QUEUE', 'CHECKPOINT_QUEUE',
                'REQUEST_FOR_DEADLOCK_SEARCH', 'XE_TIMER_EVENT', 
                'BROKER_TO_FLUSH', 'BROKER_TASK_STOP', 'CLR_MANUAL_EVENT',
                'CLR_AUTO_EVENT', 'DISPATCHER_QUEUE_SEMAPHORE', 
                'FT_IFTS_SCHEDULER_IDLE_WAIT', 'XE_DISPATCHER_WAIT', 
                'XE_DISPATCHER_JOIN', 'SQLTRACE_INCREMENTAL_FLUSH_SLEEP'
            )
            """
            result = conn.execute_query(query)
            if result:
                return result[0].get('signal_wait_percent', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting signal wait percent: {e}")
        return 0

    def _get_wait_category_percents(self, conn) -> Dict[str, int]:
        """Compute wait category distribution percentages (best-effort)."""
        try:
            query = """
            WITH w AS (
                SELECT wait_type, wait_time_ms
                FROM sys.dm_os_wait_stats
                WHERE wait_time_ms > 0
                  AND wait_type NOT IN (
                    'CLR_SEMAPHORE', 'LAZYWRITER_SLEEP', 'RESOURCE_QUEUE',
                    'SLEEP_TASK', 'SLEEP_SYSTEMTASK', 'SQLTRACE_BUFFER_FLUSH',
                    'WAITFOR', 'LOGMGR_QUEUE', 'CHECKPOINT_QUEUE',
                    'REQUEST_FOR_DEADLOCK_SEARCH', 'XE_TIMER_EVENT',
                    'BROKER_TO_FLUSH', 'BROKER_TASK_STOP', 'CLR_MANUAL_EVENT',
                    'CLR_AUTO_EVENT', 'DISPATCHER_QUEUE_SEMAPHORE',
                    'FT_IFTS_SCHEDULER_IDLE_WAIT', 'XE_DISPATCHER_WAIT',
                    'XE_DISPATCHER_JOIN', 'SQLTRACE_INCREMENTAL_FLUSH_SLEEP'
                  )
            ),
            tot AS (
                SELECT SUM(wait_time_ms) AS total_ms FROM w
            ),
            cat AS (
                SELECT
                    SUM(CASE
                        WHEN wait_type IN ('SOS_SCHEDULER_YIELD', 'THREADPOOL')
                             OR wait_type LIKE 'CX%'
                            THEN wait_time_ms ELSE 0 END) AS cpu_ms,
                    SUM(CASE
                        WHEN wait_type LIKE 'PAGEIOLATCH_%'
                             OR wait_type IN ('IO_COMPLETION', 'ASYNC_IO_COMPLETION', 'ASYNC_NETWORK_IO', 'WRITELOG', 'LOGBUFFER', 'BACKUPIO')
                            THEN wait_time_ms ELSE 0 END) AS io_ms,
                    SUM(CASE
                        WHEN wait_type LIKE 'LCK_M_%'
                            THEN wait_time_ms ELSE 0 END) AS lock_ms,
                    SUM(CASE
                        WHEN wait_type IN ('RESOURCE_SEMAPHORE', 'RESOURCE_SEMAPHORE_QUERY_COMPILE', 'MEMORY_GRANT_UPDATE')
                             OR wait_type LIKE 'MEMORY_%'
                            THEN wait_time_ms ELSE 0 END) AS mem_ms
                FROM w
            )
            SELECT
                CAST(cat.cpu_ms * 100.0 / NULLIF(tot.total_ms, 0) AS INT) AS cpu_wait_percent,
                CAST(cat.io_ms * 100.0 / NULLIF(tot.total_ms, 0) AS INT) AS io_wait_percent,
                CAST(cat.lock_ms * 100.0 / NULLIF(tot.total_ms, 0) AS INT) AS lock_wait_percent,
                CAST(cat.mem_ms * 100.0 / NULLIF(tot.total_ms, 0) AS INT) AS memory_wait_percent
            FROM cat CROSS JOIN tot
            """
            result = conn.execute_query(query)
            if result:
                return {
                    'cpu_wait_percent': result[0].get('cpu_wait_percent', 0) or 0,
                    'io_wait_percent': result[0].get('io_wait_percent', 0) or 0,
                    'lock_wait_percent': result[0].get('lock_wait_percent', 0) or 0,
                    'memory_wait_percent': result[0].get('memory_wait_percent', 0) or 0,
                }
        except Exception as e:
            logger.warning(f"Error getting wait category percents: {e}")
        return {'cpu_wait_percent': 0, 'io_wait_percent': 0, 'lock_wait_percent': 0, 'memory_wait_percent': 0}
    
    def _get_blocking_info(self, conn) -> Dict[str, int]:
        """Get blocking info: count of blocked sessions and head blocker SPID"""
        try:
            query = """
            SELECT 
                COUNT(*) AS blocked_count,
                ISNULL(MIN(blocking_session_id), 0) AS head_blocker
            FROM sys.dm_exec_requests
            WHERE blocking_session_id > 0
            """
            result = conn.execute_query(query)
            if result:
                return {
                    'blocked_count': result[0].get('blocked_count', 0) or 0,
                    'head_blocker': result[0].get('head_blocker', 0) or 0
                }
        except Exception as e:
            logger.warning(f"Error getting blocking info: {e}")
        return {'blocked_count': 0, 'head_blocker': 0}
    
    def _get_runnable_tasks(self, conn) -> int:
        """Get count of runnable tasks waiting for CPU"""
        try:
            query = """
            SELECT COUNT(*) AS runnable_tasks
            FROM sys.dm_os_tasks
            WHERE task_state = 'RUNNABLE'
            """
            result = conn.execute_query(query)
            if result:
                return result[0].get('runnable_tasks', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting runnable tasks: {e}")
        return 0

    def _get_tempdb_log_used(self, conn) -> int:
        """Get TempDB log used percentage."""
        try:
            query = """
            SELECT CAST(used_log_space_in_percent AS INT) AS log_used_percent
            FROM tempdb.sys.dm_db_log_space_usage
            """
            result = conn.execute_query(query)
            if result:
                return result[0].get('log_used_percent', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting TempDB log used percent: {e}")
        return 0

    def _get_tempdb_pfs_gam_waits(self, conn) -> int:
        """
        Best-effort: count current PAGELATCH waits on TempDB allocation bitmap pages (PFS/GAM/SGAM).

        This detects page_id IN (1,2,3) for database_id=2 in resource_description.
        """
        try:
            query = """
            SELECT COUNT(*) AS pfs_gam_waits
            FROM sys.dm_os_waiting_tasks
            WHERE wait_type LIKE 'PAGELATCH_%'
              AND resource_description LIKE '2:%'
              AND TRY_CONVERT(
                    INT,
                    PARSENAME(
                        REPLACE(
                            LEFT(resource_description, CHARINDEX(' ', resource_description + ' ') - 1),
                            ':', '.'
                        ),
                        1
                    )
                  ) IN (1, 2, 3)
            """
            result = conn.execute_query(query)
            if result:
                return result[0].get('pfs_gam_waits', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting TempDB PFS/GAM waits: {e}")
        return 0
    
    def get_failed_jobs_list(self) -> list:
        """Get list of failed jobs with details"""
        if not self.is_connected:
            return []
        
        try:
            result = self.connection.execute_query(DashboardQueries.FAILED_JOBS)
            return result or []
        except Exception as e:
            logger.warning(f"Error getting failed jobs list: {e}")
        return []
    
    def get_backup_details(self) -> list:
        """Get backup details per database"""
        if not self.is_connected:
            return []
        
        try:
            result = self.connection.execute_query(DashboardQueries.LAST_BACKUPS)
            return result or []
        except Exception as e:
            logger.warning(f"Error getting backup details: {e}")
        return []


def get_dashboard_service() -> DashboardService:
    """Get singleton dashboard service instance"""
    return DashboardService()
