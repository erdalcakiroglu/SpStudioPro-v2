"""
SQL Server version detection and feature availability
"""

from typing import Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum

from app.core.constants import SQL_SERVER_VERSIONS
from app.core.logger import get_logger

logger = get_logger('database.version')


class SQLFeature(str, Enum):
    """SQL Server features that vary by version"""
    
    # Query Store (2016+)
    QUERY_STORE = "query_store"
    
    # Temporal Tables (2016+)
    TEMPORAL_TABLES = "temporal_tables"
    
    # JSON Support (2016+)
    JSON_SUPPORT = "json_support"
    
    # Graph Tables (2017+)
    GRAPH_TABLES = "graph_tables"
    
    # Resumable Index (2017+)
    RESUMABLE_INDEX = "resumable_index"
    
    # Intelligent Query Processing (2019+)
    INTELLIGENT_QP = "intelligent_qp"
    
    # Accelerated Database Recovery (2019+)
    ADR = "accelerated_database_recovery"
    
    # UTF-8 Support (2019+)
    UTF8_SUPPORT = "utf8_support"
    
    # Ledger (2022+)
    LEDGER = "ledger"
    
    # Parameter Sensitive Plan (2022+)
    PSP_OPTIMIZATION = "psp_optimization"
    
    # sys.dm_os_host_info (2017+)
    DM_OS_HOST_INFO = "dm_os_host_info"
    
    # sys.dm_db_page_info (2019+)
    DM_DB_PAGE_INFO = "dm_db_page_info"


# Feature availability by minimum version
FEATURE_MIN_VERSIONS = {
    SQLFeature.QUERY_STORE: 13,         # 2016
    SQLFeature.TEMPORAL_TABLES: 13,     # 2016
    SQLFeature.JSON_SUPPORT: 13,        # 2016
    SQLFeature.GRAPH_TABLES: 14,        # 2017
    SQLFeature.RESUMABLE_INDEX: 14,     # 2017
    SQLFeature.DM_OS_HOST_INFO: 14,     # 2017
    SQLFeature.INTELLIGENT_QP: 15,      # 2019
    SQLFeature.ADR: 15,                 # 2019
    SQLFeature.UTF8_SUPPORT: 15,        # 2019
    SQLFeature.DM_DB_PAGE_INFO: 15,     # 2019
    SQLFeature.LEDGER: 16,              # 2022
    SQLFeature.PSP_OPTIMIZATION: 16,    # 2022
}


@dataclass
class SQLServerVersion:
    """SQL Server version information"""
    
    major_version: int = 0
    minor_version: int = 0
    build_number: int = 0
    product_level: str = ""  # RTM, SP1, SP2, CU1, etc.
    edition: str = ""
    engine_edition: int = 0  # 1=Personal, 2=Standard, 3=Enterprise, 4=Express, 5=Azure DB
    
    full_version_string: str = ""
    
    # Computed fields
    _available_features: Set[SQLFeature] = field(default_factory=set)
    
    def __post_init__(self):
        self._compute_available_features()
    
    def _compute_available_features(self) -> None:
        """Compute which features are available for this version"""
        self._available_features = set()
        
        for feature, min_version in FEATURE_MIN_VERSIONS.items():
            if self.major_version >= min_version:
                self._available_features.add(feature)
    
    @property
    def friendly_name(self) -> str:
        """Get friendly version name like 'SQL Server 2019'"""
        return SQL_SERVER_VERSIONS.get(self.major_version, f"SQL Server (v{self.major_version})")
    
    @property
    def is_azure(self) -> bool:
        """Check if this is an Azure SQL instance"""
        return self.engine_edition in (5, 6, 8)
    
    @property
    def is_express(self) -> bool:
        """Check if this is Express edition"""
        return self.engine_edition == 4 or 'Express' in self.edition
    
    @property
    def available_features(self) -> Set[SQLFeature]:
        """Get set of available features"""
        return self._available_features
    
    def supports(self, feature: SQLFeature) -> bool:
        """Check if a specific feature is supported"""
        return feature in self._available_features
    
    def get_version_string(self) -> str:
        """Get formatted version string"""
        parts = [self.friendly_name]
        
        if self.product_level:
            parts.append(f"({self.product_level})")
        
        if self.is_azure:
            parts.append("- Azure")
        elif self.edition:
            parts.append(f"- {self.edition}")
        
        return " ".join(parts)


class VersionDetector:
    """
    Detects SQL Server version and available features
    """
    
    VERSION_QUERY = """
    SELECT 
        SERVERPROPERTY('ProductMajorVersion') AS MajorVersion,
        SERVERPROPERTY('ProductMinorVersion') AS MinorVersion,
        SERVERPROPERTY('ProductBuild') AS BuildNumber,
        SERVERPROPERTY('ProductLevel') AS ProductLevel,
        SERVERPROPERTY('Edition') AS Edition,
        SERVERPROPERTY('EngineEdition') AS EngineEdition,
        @@VERSION AS FullVersion
    """
    
    @classmethod
    def detect(cls, connection) -> SQLServerVersion:
        """
        Detect SQL Server version from a database connection
        
        Args:
            connection: DatabaseConnection instance
        
        Returns:
            SQLServerVersion with detected information
        """
        try:
            results = connection.execute_query(cls.VERSION_QUERY)
            
            if not results:
                logger.warning("Could not detect SQL Server version")
                return SQLServerVersion()
            
            row = results[0]
            
            version = SQLServerVersion(
                major_version=int(row.get('MajorVersion') or 0),
                minor_version=int(row.get('MinorVersion') or 0),
                build_number=int(row.get('BuildNumber') or 0),
                product_level=str(row.get('ProductLevel') or ''),
                edition=str(row.get('Edition') or ''),
                engine_edition=int(row.get('EngineEdition') or 0),
                full_version_string=str(row.get('FullVersion') or ''),
            )
            
            logger.info(f"Detected: {version.get_version_string()}")
            logger.info(f"Available features: {len(version.available_features)}")
            
            return version
            
        except Exception as e:
            logger.error(f"Failed to detect SQL Server version: {e}")
            return SQLServerVersion()
    
    @classmethod
    def get_query_for_feature(
        cls, 
        feature: SQLFeature, 
        version: SQLServerVersion,
        fallback_query: Optional[str] = None
    ) -> Optional[str]:
        """
        Get appropriate query based on version and feature availability
        
        Args:
            feature: Feature to check
            version: Detected SQL Server version
            fallback_query: Query to use if feature not available
        
        Returns:
            Query string or None if not available
        """
        if version.supports(feature):
            return None  # Caller should use the modern query
        return fallback_query
