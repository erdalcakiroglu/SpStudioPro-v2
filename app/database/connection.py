"""
Database connection management for SQL Server
"""

import asyncio
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

import pyodbc
from PyQt6.QtCore import QObject, pyqtSignal
from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from app.models.connection_profile import ConnectionProfile, AuthMethod
# Circular import prevention: from app.services.credential_store import get_credential_store
from app.core.constants import ODBC_DRIVER_PREFERENCES, ConnectionStatus
from app.core.config import get_settings
from app.core.logger import get_logger
from app.core.exceptions import (
    ConnectionError, 
    ConnectionTimeoutError, 
    AuthenticationError,
    QueryExecutionError,
    QueryTimeoutError,
)

logger = get_logger('database.connection')


def get_available_odbc_drivers() -> List[str]:
    """Get list of available SQL Server ODBC drivers"""
    try:
        drivers = pyodbc.drivers()
        sql_drivers = [d for d in drivers if 'SQL Server' in d]
        return sql_drivers
    except Exception as e:
        logger.error(f"Failed to get ODBC drivers: {e}")
        return []


def get_best_odbc_driver() -> Optional[str]:
    """Get the best available ODBC driver"""
    available = get_available_odbc_drivers()
    
    for preferred in ODBC_DRIVER_PREFERENCES:
        if preferred in available:
            return preferred
    
    # Return first available if no preferred found
    return available[0] if available else None


@dataclass
class ConnectionInfo:
    """Connection metadata"""
    server_version: str = ""
    product_version: str = ""
    server_name: str = ""
    database_name: str = ""
    edition: str = ""
    is_azure: bool = False
    major_version: int = 0
    connected_at: Optional[datetime] = None


class DatabaseConnection:
    """
    SQL Server database connection manager
    
    Handles connection lifecycle, query execution, and connection pooling.
    """
    
    def __init__(self, profile: ConnectionProfile):
        self.profile = profile
        self._engine: Optional[Engine] = None
        self._status: ConnectionStatus = ConnectionStatus.DISCONNECTED
        self._info: Optional[ConnectionInfo] = None
        self._last_error: Optional[str] = None
        
        from app.services.credential_store import get_credential_store
        self._credential_store = get_credential_store()
        self._settings = get_settings()
    
    @property
    def status(self) -> ConnectionStatus:
        return self._status
    
    @property
    def info(self) -> Optional[ConnectionInfo]:
        return self._info
    
    @property
    def is_connected(self) -> bool:
        return self._status == ConnectionStatus.CONNECTED
    
    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
    
    def _build_connection_string(self) -> str:
        """Build full connection string with password"""
        # Get ODBC driver
        driver = self.profile.driver or get_best_odbc_driver()
        if not driver:
            raise ConnectionError("No SQL Server ODBC driver found")

        server = self.profile.server
        if "\\" in server:
            server_value = server if self.profile.port == 1433 else f"{server},{self.profile.port}"
        else:
            server_value = f"{server},{self.profile.port}"
        
        parts = [
            f"DRIVER={{{driver}}}",
            f"SERVER={server_value}",
            f"DATABASE={self.profile.database}",
            f"APP={{{self.profile.application_name}}}",
            f"Connect Timeout={self.profile.connection_timeout}",
        ]
        
        # Authentication
        if self.profile.auth_method == AuthMethod.SQL_SERVER:
            password = self._credential_store.get_password(self.profile.id)
            if not password:
                raise AuthenticationError("No password found for this connection")
            parts.append(f"UID={self.profile.username}")
            parts.append(f"PWD={password}")
        elif self.profile.auth_method == AuthMethod.WINDOWS:
            parts.append("Trusted_Connection=yes")
        
        # Encryption
        if self.profile.encrypt:
            parts.append("Encrypt=yes")
        
        if self.profile.trust_server_certificate:
            parts.append("TrustServerCertificate=yes")
        
        return ";".join(parts)
    
    def connect(self) -> bool:
        """
        Establish database connection
        
        Returns:
            True if connection successful
        
        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        if self.is_connected:
            return True
        
        self._status = ConnectionStatus.CONNECTING
        self._last_error = None
        
        try:
            connection_string = self._build_connection_string()
            
            # Create SQLAlchemy engine with connection pooling
            self._engine = create_engine(
                f"mssql+pyodbc:///?odbc_connect={connection_string}",
                poolclass=QueuePool,
                pool_size=self._settings.database.max_pool_size,
                pool_recycle=self._settings.database.pool_recycle,
                pool_pre_ping=True,
                echo=self._settings.database.echo_sql,
            )
            
            # Test connection and get server info
            self._fetch_server_info()
            
            self._status = ConnectionStatus.CONNECTED
            logger.info(f"Connected to {self.profile.server}/{self.profile.database}")
            
            return True
            
        except pyodbc.InterfaceError as e:
            self._handle_connection_error(f"Connection interface error: {e}")
        except pyodbc.OperationalError as e:
            error_msg = str(e)
            if "Login failed" in error_msg:
                self._handle_connection_error(f"Authentication failed: {e}", AuthenticationError)
            elif "timeout" in error_msg.lower():
                self._handle_connection_error(f"Connection timed out: {e}", ConnectionTimeoutError)
            else:
                self._handle_connection_error(f"Connection failed: {e}")
        except Exception as e:
            self._handle_connection_error(f"Unexpected connection error: {e}")
        
        return False
    
    def _handle_connection_error(self, message: str, exc_class=ConnectionError) -> None:
        """Handle connection errors"""
        self._status = ConnectionStatus.ERROR
        self._last_error = message
        self._engine = None
        logger.error(message)
        raise exc_class(message, server=self.profile.server, database=self.profile.database)
    
    def _fetch_server_info(self) -> None:
        """Fetch server version and metadata"""
        # Cast to standard types to avoid "ODBC SQL type -16" errors with some drivers
        query = """
        SELECT 
            CAST(@@VERSION AS NVARCHAR(MAX)) AS FullVersion,
            CAST(@@SERVERNAME AS NVARCHAR(255)) AS ServerName,
            CAST(DB_NAME() AS NVARCHAR(128)) AS DatabaseName,
            CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)) AS ProductVersion,
            CAST(SERVERPROPERTY('ProductMajorVersion') AS INT) AS MajorVersion,
            CAST(SERVERPROPERTY('Edition') AS NVARCHAR(128)) AS Edition,
            CAST(SERVERPROPERTY('EngineEdition') AS INT) AS EngineEdition
        """
        
        with self._engine.connect() as conn:
            result = conn.execute(text(query)).fetchone()
            
            engine_edition = result[6]
            is_azure = engine_edition in (5, 6, 8)  # Azure SQL Database, Azure SQL DW, Azure SQL MI
            
            self._info = ConnectionInfo(
                server_version=result[0],
                product_version=result[3],
                server_name=result[1],
                database_name=result[2],
                edition=result[5],
                is_azure=is_azure,
                major_version=int(result[4]) if result[4] else 0,
                connected_at=datetime.now(),
            )
    
    def disconnect(self) -> None:
        """Close database connection"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        
        self._status = ConnectionStatus.DISCONNECTED
        self._info = None
        logger.info(f"Disconnected from {self.profile.server}")
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return results
        
        Args:
            query: SQL query string
            params: Query parameters
            timeout: Query timeout in seconds
        
        Returns:
            List of dictionaries with column names as keys
        
        Raises:
            QueryExecutionError: If query fails
            QueryTimeoutError: If query times out
        """
        if not self.is_connected:
            raise QueryExecutionError("Not connected to database")
        
        timeout = timeout or self._settings.database.query_timeout
        
        try:
            with self._engine.connect() as conn:
                # Set query timeout
                conn.execute(text(f"SET LOCK_TIMEOUT {timeout * 1000}"))

                # Use raw cursor for multi-statement batches (e.g., temp tables)
                requires_raw = ("#ErrorLog" in query) or ("xp_readerrorlog" in query)
                if requires_raw and not params:
                    raw_conn = conn.connection
                    cursor = raw_conn.cursor()
                    cursor.execute("SET NOCOUNT ON")
                    cursor.execute(query)

                    # Advance to the first result set that returns rows
                    while cursor.description is None and cursor.nextset():
                        pass

                    if cursor.description:
                        columns = [col[0] for col in cursor.description]
                        rows = cursor.fetchall()
                        return [dict(zip(columns, row)) for row in rows]
                    return []
                
                # Execute query
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))
                
                # Fetch results
                if result.returns_rows:
                    columns = result.keys()
                    rows = result.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                
                return []
                
        except pyodbc.OperationalError as e:
            if "timeout" in str(e).lower():
                raise QueryTimeoutError(f"Query timed out after {timeout}s", query=query)
            raise QueryExecutionError(f"Query failed: {e}", query=query)
        except Exception as e:
            raise QueryExecutionError(f"Query execution error: {e}", query=query)
    
    def execute_scalar(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute query and return single value"""
        results = self.execute_query(query, params)
        if results and len(results) > 0:
            first_row = results[0]
            if first_row:
                return list(first_row.values())[0]
        return None
    
    def execute_non_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Execute a non-query (INSERT, UPDATE, DELETE) and return affected rows
        
        Note: This should only be used for safe operations like
        SET commands, not for modifying user data.
        """
        if not self.is_connected:
            raise QueryExecutionError("Not connected to database")
        
        try:
            with self._engine.connect() as conn:
                if params:
                    result = conn.execute(text(query), params)
                else:
                    result = conn.execute(text(query))
                conn.commit()
                return result.rowcount
        except Exception as e:
            raise QueryExecutionError(f"Non-query execution error: {e}", query=query)
    
    def test_connection(self) -> bool:
        """Test if connection is still alive"""
        if not self._engine:
            return False
        
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False


class ConnectionManager(QObject):
    """
    Manages multiple database connections
    
    Provides a central point for connection management across the application.
    
    Signals:
        connection_changed: Emitted when active connection changes
    """
    
    connection_changed = pyqtSignal(bool, str, str)  # connected, server, database
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connections: Dict[str, DatabaseConnection] = {}
        self._active_connection_id: Optional[str] = None
    
    @property
    def active_connection(self) -> Optional[DatabaseConnection]:
        """Get the currently active connection"""
        if self._active_connection_id:
            return self._connections.get(self._active_connection_id)
        return None
    
    def connect(self, profile: ConnectionProfile) -> DatabaseConnection:
        """Create and establish a connection"""
        # Check if already connected
        if profile.id in self._connections:
            conn = self._connections[profile.id]
            if conn.is_connected:
                self._active_connection_id = profile.id
                self.connection_changed.emit(True, profile.server, profile.database)
                return conn
        
        # Create new connection
        conn = DatabaseConnection(profile)
        conn.connect()
        
        self._connections[profile.id] = conn
        self._active_connection_id = profile.id
        self.connection_changed.emit(True, profile.server, profile.database)
        
        return conn
    
    def disconnect(self, profile_id: str) -> None:
        """Disconnect a specific connection"""
        if profile_id in self._connections:
            self._connections[profile_id].disconnect()
            del self._connections[profile_id]
            
            if self._active_connection_id == profile_id:
                self._active_connection_id = None
                self.connection_changed.emit(False, "", "")
    
    def disconnect_all(self) -> None:
        """Disconnect all connections"""
        for conn in self._connections.values():
            conn.disconnect()
        self._connections.clear()
        self._active_connection_id = None
        self.connection_changed.emit(False, "", "")
    
    def set_active(self, profile_id: str) -> bool:
        """Set the active connection"""
        if profile_id in self._connections:
            self._active_connection_id = profile_id
            return True
        return False
    
    def get_connection(self, profile_id: str) -> Optional[DatabaseConnection]:
        """Get a specific connection"""
        return self._connections.get(profile_id)


# Global connection manager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get the global ConnectionManager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
