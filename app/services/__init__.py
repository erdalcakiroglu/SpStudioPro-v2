"""
Services module - Business logic and workflows
"""

from app.services.connection_store import ConnectionStore, get_connection_store
from app.services.credential_store import CredentialStore, get_credential_store
from app.services.query_stats_service import QueryStatsService
from app.services.query_stats_contract import IQueryStatsService
from app.services.service_factory import ServiceFactory
from app.services.missing_index_service import MissingIndexService, get_missing_index_service
from app.services.index_analyzer_service import (
    IndexAnalyzer,
    IndexAdvisorTelemetry,
    count_context_matches,
)
from app.services.blocking_service import (
    BlockingService,
    BlockingSnapshot,
    BlockingChainAnalysis,
    KillResult,
    LockInfo,
)
from app.services.blocking_exceptions import (
    BlockingAnalysisError,
    ConnectionError as BlockingConnectionError,
    QueryExecutionError as BlockingQueryExecutionError,
    KillOperationError,
)
from app.repositories.blocking_repository import (
    IBlockingRepository,
    BlockingRepository,
    CachedBlockingRepository,
)

__all__ = [
    "ConnectionStore",
    "get_connection_store",
    "CredentialStore", 
    "get_credential_store",
    "IQueryStatsService",
    "QueryStatsService",
    "ServiceFactory",
    "MissingIndexService",
    "get_missing_index_service",
    "IndexAnalyzer",
    "IndexAdvisorTelemetry",
    "count_context_matches",
    "BlockingService",
    "BlockingSnapshot",
    "BlockingChainAnalysis",
    "KillResult",
    "LockInfo",
    "BlockingAnalysisError",
    "BlockingConnectionError",
    "BlockingQueryExecutionError",
    "KillOperationError",
    "IBlockingRepository",
    "BlockingRepository",
    "CachedBlockingRepository",
]
