"""
Database module - SQL Server connection and query execution
"""

from app.database.connection import (
    DatabaseConnection, 
    ConnectionManager,
    get_connection_manager,
    get_available_odbc_drivers,
    get_best_odbc_driver,
)
from app.database.version_detector import VersionDetector, SQLServerVersion, SQLFeature
from app.database.queries import QueryStoreQueries

__all__ = [
    "DatabaseConnection",
    "ConnectionManager", 
    "get_connection_manager",
    "get_available_odbc_drivers",
    "get_best_odbc_driver",
    "VersionDetector",
    "SQLServerVersion",
    "SQLFeature",
    "QueryStoreQueries",
]
