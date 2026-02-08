"""
SQL Agent Jobs Queries - Job monitoring and management
"""

from enum import Enum
from typing import Dict


class JobStatus(Enum):
    """Job execution status"""
    FAILED = 0
    SUCCEEDED = 1
    RETRY = 2
    CANCELED = 3
    IN_PROGRESS = 4
    UNKNOWN = 5


class JobRunStatus(Enum):
    """Job current run status"""
    IDLE = 1
    RUNNING = 2
    WAITING_FOR_THREAD = 3
    BETWEEN_RETRIES = 4


# Status colors for UI
STATUS_COLORS: Dict[JobStatus, str] = {
    JobStatus.FAILED: "#EF4444",      # Red
    JobStatus.SUCCEEDED: "#10B981",   # Green
    JobStatus.RETRY: "#F59E0B",       # Amber
    JobStatus.CANCELED: "#64748B",    # Gray
    JobStatus.IN_PROGRESS: "#3B82F6", # Blue
    JobStatus.UNKNOWN: "#94A3B8",     # Light gray
}


class JobsQueries:
    """SQL queries for SQL Agent Jobs"""
    
    # All jobs with current status
    ALL_JOBS = """
    SELECT 
        j.job_id,
        j.name AS job_name,
        j.description,
        j.enabled,
        j.date_created,
        j.date_modified,
        c.name AS category_name,
        SUSER_SNAME(j.owner_sid) AS owner,
        CASE ja.run_requested_date
            WHEN NULL THEN 0
            ELSE 1
        END AS is_running,
        ja.run_requested_date,
        ja.run_requested_source,
        ja.last_executed_step_id,
        ja.last_executed_step_date,
        ja.stop_execution_date,
        -- Last run info
        (SELECT TOP 1 run_status FROM msdb.dbo.sysjobhistory h 
         WHERE h.job_id = j.job_id AND h.step_id = 0 
         ORDER BY h.run_date DESC, h.run_time DESC) AS last_run_status,
        (SELECT TOP 1 msdb.dbo.agent_datetime(h.run_date, h.run_time) 
         FROM msdb.dbo.sysjobhistory h 
         WHERE h.job_id = j.job_id AND h.step_id = 0 
         ORDER BY h.run_date DESC, h.run_time DESC) AS last_run_date,
        (SELECT TOP 1 h.run_duration FROM msdb.dbo.sysjobhistory h 
         WHERE h.job_id = j.job_id AND h.step_id = 0 
         ORDER BY h.run_date DESC, h.run_time DESC) AS last_run_duration,
        -- Next run info
        js.next_run_date,
        js.next_run_time,
        CASE WHEN js.next_run_date > 0 
             THEN msdb.dbo.agent_datetime(js.next_run_date, js.next_run_time) 
             ELSE NULL END AS next_run_datetime
    FROM msdb.dbo.sysjobs j
    LEFT JOIN msdb.dbo.syscategories c ON j.category_id = c.category_id
    LEFT JOIN msdb.dbo.sysjobactivity ja ON j.job_id = ja.job_id
        AND ja.session_id = (SELECT MAX(session_id) FROM msdb.dbo.sysjobactivity)
    LEFT JOIN msdb.dbo.sysjobschedules js ON j.job_id = js.job_id
    ORDER BY j.name
    """
    
    # Jobs summary
    JOBS_SUMMARY = """
    SELECT 
        COUNT(*) AS total_jobs,
        SUM(CASE WHEN j.enabled = 1 THEN 1 ELSE 0 END) AS enabled_jobs,
        SUM(CASE WHEN j.enabled = 0 THEN 1 ELSE 0 END) AS disabled_jobs,
        (SELECT COUNT(DISTINCT job_id) FROM msdb.dbo.sysjobactivity 
         WHERE run_requested_date IS NOT NULL AND stop_execution_date IS NULL
         AND session_id = (SELECT MAX(session_id) FROM msdb.dbo.sysjobactivity)) AS running_jobs
    FROM msdb.dbo.sysjobs j
    """

    # Fallback summary when caller has no SELECT permission on msdb.dbo.sysjobactivity.
    JOBS_SUMMARY_NO_ACTIVITY = """
    SELECT
        COUNT(*) AS total_jobs,
        SUM(CASE WHEN j.enabled = 1 THEN 1 ELSE 0 END) AS enabled_jobs,
        SUM(CASE WHEN j.enabled = 0 THEN 1 ELSE 0 END) AS disabled_jobs,
        CAST(0 AS INT) AS running_jobs
    FROM msdb.dbo.sysjobs j
    """
    
    # Failed jobs (last 24 hours)
    FAILED_JOBS_24H = """
    SELECT 
        j.name AS job_name,
        h.step_id,
        h.step_name,
        h.run_status,
        msdb.dbo.agent_datetime(h.run_date, h.run_time) AS run_datetime,
        h.run_duration,
        h.message
    FROM msdb.dbo.sysjobs j
    JOIN msdb.dbo.sysjobhistory h ON j.job_id = h.job_id
    WHERE h.run_status = 0  -- Failed
      AND h.step_id > 0     -- Exclude job outcome row
      AND msdb.dbo.agent_datetime(h.run_date, h.run_time) > DATEADD(HOUR, -24, GETDATE())
    ORDER BY msdb.dbo.agent_datetime(h.run_date, h.run_time) DESC
    """
    
    # Failed jobs count
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
    
    # Job history (for a specific job)
    JOB_HISTORY = """
    SELECT TOP 50
        h.step_id,
        h.step_name,
        h.run_status,
        msdb.dbo.agent_datetime(h.run_date, h.run_time) AS run_datetime,
        h.run_duration,
        h.retries_attempted,
        h.message
    FROM msdb.dbo.sysjobhistory h
    WHERE h.job_id = ?
    ORDER BY h.run_date DESC, h.run_time DESC
    """
    
    # Currently running jobs
    RUNNING_JOBS = """
    SELECT 
        j.name AS job_name,
        ja.run_requested_date AS start_time,
        DATEDIFF(SECOND, ja.run_requested_date, GETDATE()) AS running_seconds,
        ja.last_executed_step_id,
        (SELECT step_name FROM msdb.dbo.sysjobsteps s 
         WHERE s.job_id = j.job_id AND s.step_id = ja.last_executed_step_id) AS current_step
    FROM msdb.dbo.sysjobs j
    JOIN msdb.dbo.sysjobactivity ja ON j.job_id = ja.job_id
    WHERE ja.run_requested_date IS NOT NULL
      AND ja.stop_execution_date IS NULL
      AND ja.session_id = (SELECT MAX(session_id) FROM msdb.dbo.sysjobactivity)
    ORDER BY ja.run_requested_date
    """
    
    # Job schedules
    JOB_SCHEDULES = """
    SELECT 
        j.name AS job_name,
        s.name AS schedule_name,
        s.enabled AS schedule_enabled,
        s.freq_type,
        s.freq_interval,
        s.freq_subday_type,
        s.freq_subday_interval,
        s.active_start_date,
        s.active_start_time,
        s.active_end_date,
        s.active_end_time,
        CASE WHEN js.next_run_date > 0 
             THEN msdb.dbo.agent_datetime(js.next_run_date, js.next_run_time) 
             ELSE NULL END AS next_run
    FROM msdb.dbo.sysjobs j
    JOIN msdb.dbo.sysjobschedules js ON j.job_id = js.job_id
    JOIN msdb.dbo.sysschedules s ON js.schedule_id = s.schedule_id
    WHERE j.enabled = 1
    ORDER BY j.name, s.name
    """
    
    # Job steps
    JOB_STEPS = """
    SELECT 
        step_id,
        step_name,
        subsystem,
        command,
        database_name,
        on_success_action,
        on_fail_action,
        retry_attempts,
        retry_interval
    FROM msdb.dbo.sysjobsteps
    WHERE job_id = ?
    ORDER BY step_id
    """
    
    # Jobs by category
    JOBS_BY_CATEGORY = """
    SELECT 
        c.name AS category_name,
        COUNT(*) AS job_count,
        SUM(CASE WHEN j.enabled = 1 THEN 1 ELSE 0 END) AS enabled_count
    FROM msdb.dbo.sysjobs j
    JOIN msdb.dbo.syscategories c ON j.category_id = c.category_id
    GROUP BY c.name
    ORDER BY job_count DESC
    """
    
    # Job success rate (last 7 days)
    JOB_SUCCESS_RATE = """
    SELECT 
        j.name AS job_name,
        COUNT(*) AS total_runs,
        SUM(CASE WHEN h.run_status = 1 THEN 1 ELSE 0 END) AS successful_runs,
        SUM(CASE WHEN h.run_status = 0 THEN 1 ELSE 0 END) AS failed_runs,
        CAST(SUM(CASE WHEN h.run_status = 1 THEN 1 ELSE 0 END) * 100.0 / 
             NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS success_rate
    FROM msdb.dbo.sysjobs j
    JOIN msdb.dbo.sysjobhistory h ON j.job_id = h.job_id
    WHERE h.step_id = 0  -- Job outcome only
      AND msdb.dbo.agent_datetime(h.run_date, h.run_time) > DATEADD(DAY, -7, GETDATE())
    GROUP BY j.name
    HAVING COUNT(*) > 0
    ORDER BY success_rate ASC, failed_runs DESC
    """
    
    # Long running jobs (current)
    LONG_RUNNING_JOBS = """
    SELECT 
        j.name AS job_name,
        ja.run_requested_date AS start_time,
        DATEDIFF(MINUTE, ja.run_requested_date, GETDATE()) AS running_minutes,
        AVG(h.run_duration) AS avg_duration_hhmmss
    FROM msdb.dbo.sysjobs j
    JOIN msdb.dbo.sysjobactivity ja ON j.job_id = ja.job_id
    LEFT JOIN msdb.dbo.sysjobhistory h ON j.job_id = h.job_id AND h.step_id = 0
    WHERE ja.run_requested_date IS NOT NULL
      AND ja.stop_execution_date IS NULL
      AND ja.session_id = (SELECT MAX(session_id) FROM msdb.dbo.sysjobactivity)
    GROUP BY j.name, ja.run_requested_date
    HAVING DATEDIFF(MINUTE, ja.run_requested_date, GETDATE()) > 30
    ORDER BY running_minutes DESC
    """


def get_status_color(status: int) -> str:
    """Get color for job status"""
    try:
        job_status = JobStatus(status)
        return STATUS_COLORS.get(job_status, STATUS_COLORS[JobStatus.UNKNOWN])
    except ValueError:
        return STATUS_COLORS[JobStatus.UNKNOWN]


def format_duration(duration: int) -> str:
    """Format HHMMSS duration to readable string"""
    if not duration:
        return "--"
    
    hours = duration // 10000
    minutes = (duration % 10000) // 100
    seconds = duration % 100
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"
