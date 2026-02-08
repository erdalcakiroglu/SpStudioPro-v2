"""
SQL Agent Jobs Service - Job monitoring and management
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from app.database.connection import get_connection_manager
from app.database.queries.jobs_queries import (
    JobsQueries,
    JobStatus,
    get_status_color,
    format_duration,
)
from app.core.logger import get_logger

logger = get_logger('services.jobs')


@dataclass
class Job:
    """SQL Agent Job"""
    job_id: str
    name: str
    description: str = ""
    enabled: bool = True
    category: str = ""
    owner: str = ""
    is_running: bool = False
    last_run_status: Optional[int] = None
    last_run_date: Optional[datetime] = None
    last_run_duration: int = 0
    next_run_date: Optional[datetime] = None
    
    @property
    def status_color(self) -> str:
        if self.is_running:
            return get_status_color(JobStatus.IN_PROGRESS.value)
        if self.last_run_status is not None:
            return get_status_color(self.last_run_status)
        return get_status_color(JobStatus.UNKNOWN.value)
    
    @property
    def status_text(self) -> str:
        if self.is_running:
            return "Running"
        if self.last_run_status == 0:
            return "Failed"
        elif self.last_run_status == 1:
            return "Succeeded"
        elif self.last_run_status == 2:
            return "Retry"
        elif self.last_run_status == 3:
            return "Canceled"
        return "Unknown"
    
    @property
    def duration_text(self) -> str:
        return format_duration(self.last_run_duration)


@dataclass
class FailedJob:
    """Failed job execution"""
    job_name: str
    step_id: int
    step_name: str
    run_datetime: datetime
    duration: int
    message: str
    
    @property
    def duration_text(self) -> str:
        return format_duration(self.duration)


@dataclass
class RunningJob:
    """Currently running job"""
    job_name: str
    start_time: datetime
    running_seconds: int
    current_step: str = ""
    
    @property
    def running_text(self) -> str:
        if self.running_seconds < 60:
            return f"{self.running_seconds}s"
        elif self.running_seconds < 3600:
            return f"{self.running_seconds // 60}m {self.running_seconds % 60}s"
        else:
            hours = self.running_seconds // 3600
            mins = (self.running_seconds % 3600) // 60
            return f"{hours}h {mins}m"


@dataclass
class JobsSummary:
    """Jobs summary statistics"""
    total_jobs: int = 0
    enabled_jobs: int = 0
    disabled_jobs: int = 0
    running_jobs: int = 0
    failed_24h: int = 0
    
    # Job lists
    jobs: List[Job] = field(default_factory=list)
    failed_jobs: List[FailedJob] = field(default_factory=list)
    running_jobs_list: List[RunningJob] = field(default_factory=list)
    
    # Timestamp
    collected_at: datetime = field(default_factory=datetime.now)


class JobsService:
    """
    Service for SQL Agent Jobs monitoring
    """
    
    _instance: Optional['JobsService'] = None
    
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
    
    def get_jobs_summary(self) -> JobsSummary:
        """Get comprehensive jobs summary"""
        summary = JobsSummary()
        
        if not self.is_connected:
            logger.warning("No active connection for jobs service")
            return summary
        
        conn = self.connection

        # Get summary stats (with permission-safe fallback).
        try:
            result = conn.execute_query(JobsQueries.JOBS_SUMMARY)
        except Exception as e:
            if self._is_sysjobactivity_permission_error(e):
                logger.warning(
                    "No SELECT permission on msdb.dbo.sysjobactivity; "
                    "falling back to jobs summary without running_jobs."
                )
                result = conn.execute_query(JobsQueries.JOBS_SUMMARY_NO_ACTIVITY)
            else:
                logger.error(f"Error collecting jobs summary stats: {e}")
                result = []

        if result:
            row = result[0]
            summary.total_jobs = row.get('total_jobs', 0) or 0
            summary.enabled_jobs = row.get('enabled_jobs', 0) or 0
            summary.disabled_jobs = row.get('disabled_jobs', 0) or 0
            summary.running_jobs = row.get('running_jobs', 0) or 0

        # Get failed count.
        try:
            failed_result = conn.execute_query(JobsQueries.FAILED_JOBS_COUNT)
            if failed_result:
                summary.failed_24h = failed_result[0].get('failed_job_count', 0) or 0
        except Exception as e:
            logger.warning(f"Error getting failed jobs count: {e}")

        # Get detail lists. These methods already degrade gracefully.
        summary.jobs = self._get_all_jobs(conn)
        summary.failed_jobs = self._get_failed_jobs(conn)
        summary.running_jobs_list = self._get_running_jobs(conn)
        summary.collected_at = datetime.now()
        
        return summary

    @staticmethod
    def _is_sysjobactivity_permission_error(error: Exception) -> bool:
        text = str(error or "").lower()
        return (
            "sysjobactivity" in text
            and ("permission was denied" in text or "(229)" in text)
        )
    
    def _get_all_jobs(self, conn) -> List[Job]:
        """Get all jobs"""
        jobs = []
        try:
            result = conn.execute_query(JobsQueries.ALL_JOBS)
            for row in result or []:
                jobs.append(Job(
                    job_id=str(row.get('job_id', '')),
                    name=row.get('job_name', '') or '',
                    description=row.get('description', '') or '',
                    enabled=bool(row.get('enabled', 0)),
                    category=row.get('category_name', '') or '',
                    owner=row.get('owner', '') or '',
                    is_running=bool(row.get('is_running', 0)),
                    last_run_status=row.get('last_run_status'),
                    last_run_date=row.get('last_run_date'),
                    last_run_duration=row.get('last_run_duration', 0) or 0,
                    next_run_date=row.get('next_run_datetime'),
                ))
        except Exception as e:
            logger.warning(f"Error getting all jobs: {e}")
        return jobs
    
    def _get_failed_jobs(self, conn) -> List[FailedJob]:
        """Get failed jobs (last 24h)"""
        jobs = []
        try:
            result = conn.execute_query(JobsQueries.FAILED_JOBS_24H)
            for row in result or []:
                jobs.append(FailedJob(
                    job_name=row.get('job_name', '') or '',
                    step_id=row.get('step_id', 0) or 0,
                    step_name=row.get('step_name', '') or '',
                    run_datetime=row.get('run_datetime'),
                    duration=row.get('run_duration', 0) or 0,
                    message=row.get('message', '') or '',
                ))
        except Exception as e:
            logger.warning(f"Error getting failed jobs: {e}")
        return jobs
    
    def _get_running_jobs(self, conn) -> List[RunningJob]:
        """Get currently running jobs"""
        jobs = []
        try:
            result = conn.execute_query(JobsQueries.RUNNING_JOBS)
            for row in result or []:
                jobs.append(RunningJob(
                    job_name=row.get('job_name', '') or '',
                    start_time=row.get('start_time'),
                    running_seconds=row.get('running_seconds', 0) or 0,
                    current_step=row.get('current_step', '') or '',
                ))
        except Exception as e:
            logger.warning(f"Error getting running jobs: {e}")
        return jobs
    
    def get_job_history(self, job_id: str) -> List[Dict[str, Any]]:
        """Get job execution history"""
        if not self.is_connected:
            return []
        
        try:
            # Note: This would need parameterized query support
            query = JobsQueries.JOB_HISTORY.replace('?', f"'{job_id}'")
            result = self.connection.execute_query(query)
            return result or []
        except Exception as e:
            logger.warning(f"Error getting job history: {e}")
        return []
    
    def get_job_steps(self, job_id: str) -> List[Dict[str, Any]]:
        """Get job steps"""
        if not self.is_connected:
            return []
        
        try:
            query = JobsQueries.JOB_STEPS.replace('?', f"'{job_id}'")
            result = self.connection.execute_query(query)
            return result or []
        except Exception as e:
            logger.warning(f"Error getting job steps: {e}")
        return []
    
    def get_success_rates(self) -> List[Dict[str, Any]]:
        """Get job success rates (last 7 days)"""
        if not self.is_connected:
            return []
        
        try:
            result = self.connection.execute_query(JobsQueries.JOB_SUCCESS_RATE)
            return result or []
        except Exception as e:
            logger.warning(f"Error getting success rates: {e}")
        return []


def get_jobs_service() -> JobsService:
    """Get singleton jobs service instance"""
    return JobsService()
