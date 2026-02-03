"""
Wait Statistics Service - SQL Server wait analysis
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from app.database.connection import get_connection_manager
from app.database.queries.wait_stats_queries import (
    WaitStatsQueries,
    WaitCategory,
    get_wait_category,
    get_category_color,
)
from app.core.logger import get_logger

logger = get_logger('services.wait_stats')


@dataclass
class WaitStat:
    """Single wait type statistics"""
    wait_type: str
    category: WaitCategory
    waiting_tasks: int = 0
    wait_time_ms: int = 0
    max_wait_time_ms: int = 0
    signal_wait_ms: int = 0
    resource_wait_ms: int = 0
    wait_percent: float = 0.0
    cumulative_percent: float = 0.0
    
    @property
    def category_color(self) -> str:
        return get_category_color(self.category)


@dataclass
class CurrentWait:
    """Currently waiting task"""
    session_id: int
    wait_type: str
    wait_time_ms: int
    wait_resource: str
    blocking_session_id: int
    login_name: str
    host_name: str
    program_name: str
    database_name: str
    current_statement: str


@dataclass
class WaitSummary:
    """Wait statistics summary"""
    total_wait_types: int = 0
    total_waiting_tasks: int = 0
    total_wait_time_ms: int = 0
    total_signal_wait_ms: int = 0
    total_resource_wait_ms: int = 0
    max_single_wait_ms: int = 0
    signal_wait_percent: float = 0.0
    resource_wait_percent: float = 0.0
    
    # Category breakdown
    category_stats: Dict[WaitCategory, int] = field(default_factory=dict)
    
    # Top waits
    top_waits: List[WaitStat] = field(default_factory=list)
    
    # Current waits
    current_waits: List[CurrentWait] = field(default_factory=list)
    
    # Timestamp
    collected_at: datetime = field(default_factory=datetime.now)


class WaitStatsService:
    """
    Service for collecting and analyzing wait statistics
    """
    
    _instance: Optional['WaitStatsService'] = None
    
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
    
    def get_wait_summary(self) -> WaitSummary:
        """Get comprehensive wait statistics summary"""
        summary = WaitSummary()
        
        if not self.is_connected:
            logger.warning("No active connection for wait stats")
            return summary
        
        conn = self.connection
        
        try:
            # Get summary stats
            result = conn.execute_query(WaitStatsQueries.WAIT_SUMMARY)
            if result:
                row = result[0]
                summary.total_wait_types = row.get('total_wait_types', 0) or 0
                summary.total_waiting_tasks = row.get('total_waiting_tasks', 0) or 0
                summary.total_wait_time_ms = row.get('total_wait_time_ms', 0) or 0
                summary.total_signal_wait_ms = row.get('total_signal_wait_ms', 0) or 0
                summary.total_resource_wait_ms = row.get('total_resource_wait_ms', 0) or 0
                summary.max_single_wait_ms = row.get('max_single_wait_ms', 0) or 0
            
            # Get signal vs resource ratio
            ratio_result = conn.execute_query(WaitStatsQueries.SIGNAL_VS_RESOURCE)
            if ratio_result:
                row = ratio_result[0]
                summary.signal_wait_percent = float(row.get('signal_wait_percent', 0) or 0)
                summary.resource_wait_percent = float(row.get('resource_wait_percent', 0) or 0)
            
            # Get top waits
            summary.top_waits = self._get_top_waits(conn)
            
            # Calculate category breakdown
            summary.category_stats = self._calculate_category_stats(conn)
            
            # Get current waits
            summary.current_waits = self._get_current_waits(conn)
            
            summary.collected_at = datetime.now()
            
        except Exception as e:
            logger.error(f"Error collecting wait stats: {e}")
        
        return summary
    
    def _get_top_waits(self, conn) -> List[WaitStat]:
        """Get top wait types"""
        waits = []
        try:
            result = conn.execute_query(WaitStatsQueries.TOP_WAITS)
            for row in result or []:
                wait_type = row.get('wait_type', '')
                waits.append(WaitStat(
                    wait_type=wait_type,
                    category=get_wait_category(wait_type),
                    waiting_tasks=row.get('waiting_tasks_count', 0) or 0,
                    wait_time_ms=row.get('wait_time_ms', 0) or 0,
                    max_wait_time_ms=row.get('max_wait_time_ms', 0) or 0,
                    signal_wait_ms=row.get('signal_wait_time_ms', 0) or 0,
                    resource_wait_ms=row.get('resource_wait_time_ms', 0) or 0,
                    wait_percent=float(row.get('wait_percent', 0) or 0),
                    cumulative_percent=float(row.get('cumulative_percent', 0) or 0),
                ))
        except Exception as e:
            logger.warning(f"Error getting top waits: {e}")
        return waits
    
    def _calculate_category_stats(self, conn) -> Dict[WaitCategory, int]:
        """Calculate wait time by category"""
        stats = {cat: 0 for cat in WaitCategory}
        try:
            result = conn.execute_query(WaitStatsQueries.WAITS_BY_CATEGORY)
            for row in result or []:
                wait_type = row.get('wait_type', '')
                wait_time = row.get('wait_time_ms', 0) or 0
                category = get_wait_category(wait_type)
                stats[category] += wait_time
        except Exception as e:
            logger.warning(f"Error calculating category stats: {e}")
        return stats
    
    def _get_current_waits(self, conn) -> List[CurrentWait]:
        """Get currently waiting tasks"""
        waits = []
        try:
            result = conn.execute_query(WaitStatsQueries.CURRENT_WAITS)
            for row in result or []:
                waits.append(CurrentWait(
                    session_id=row.get('session_id', 0) or 0,
                    wait_type=row.get('wait_type', '') or '',
                    wait_time_ms=row.get('wait_time_ms', 0) or 0,
                    wait_resource=row.get('wait_resource', '') or '',
                    blocking_session_id=row.get('blocking_session_id', 0) or 0,
                    login_name=row.get('login_name', '') or '',
                    host_name=row.get('host_name', '') or '',
                    program_name=row.get('program_name', '') or '',
                    database_name=row.get('database_name', '') or '',
                    current_statement=row.get('current_statement', '') or '',
                ))
        except Exception as e:
            logger.warning(f"Error getting current waits: {e}")
        return waits
    
    def clear_wait_stats(self) -> bool:
        """Clear wait statistics (requires admin privileges)"""
        if not self.is_connected:
            return False
        
        try:
            self.connection.execute_query(WaitStatsQueries.CLEAR_WAIT_STATS)
            logger.info("Wait statistics cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Error clearing wait stats: {e}")
            return False
    
    def get_latch_stats(self) -> List[Dict[str, Any]]:
        """Get latch statistics"""
        if not self.is_connected:
            return []
        
        try:
            result = self.connection.execute_query(WaitStatsQueries.LATCH_STATS)
            return result or []
        except Exception as e:
            logger.warning(f"Error getting latch stats: {e}")
        return []


def get_wait_stats_service() -> WaitStatsService:
    """Get singleton wait stats service instance"""
    return WaitStatsService()
