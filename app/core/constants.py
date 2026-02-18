"""
Application constants and enumerations
"""

from enum import Enum, auto
from typing import Final

# =============================================================================
# Application Info
# =============================================================================

APP_NAME: Final[str] = "SQL Perf AI"
APP_VERSION: Final[str] = "1.0.0"
APP_AUTHOR: Final[str] = "Erdal Cakiroglu"
APP_ORGANIZATION: Final[str] = "SQL Perf AI"

# =============================================================================
# File Paths
# =============================================================================

CONFIG_FILE: Final[str] = "settings.json"
CONNECTIONS_FILE: Final[str] = "connections.json"
LOG_FILE: Final[str] = "app.log"

# =============================================================================
# UI Constants
# =============================================================================

SIDEBAR_WIDTH_EXPANDED: Final[int] = 220
SIDEBAR_WIDTH_COLLAPSED: Final[int] = 60
SIDEBAR_ANIMATION_DURATION: Final[int] = 200

DEFAULT_WINDOW_WIDTH: Final[int] = 1400
DEFAULT_WINDOW_HEIGHT: Final[int] = 900
MIN_WINDOW_WIDTH: Final[int] = 1000
MIN_WINDOW_HEIGHT: Final[int] = 700

# =============================================================================
# Database Constants
# =============================================================================

DEFAULT_QUERY_TIMEOUT: Final[int] = 30  # seconds
MAX_QUERY_TIMEOUT: Final[int] = 300  # seconds
DEFAULT_CONNECTION_TIMEOUT: Final[int] = 15  # seconds

# ODBC Driver preferences (newest to oldest)
ODBC_DRIVER_PREFERENCES: Final[list[str]] = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "ODBC Driver 13 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
]

# =============================================================================
# AI/LLM Constants
# =============================================================================

DEFAULT_OLLAMA_HOST: Final[str] = "http://localhost:11434"
DEFAULT_MODEL: Final[str] = "codellama"
DEFAULT_TEMPERATURE: Final[float] = 0.1
DEFAULT_MAX_TOKENS: Final[int] = 4096
AI_RESPONSE_TIMEOUT: Final[int] = 300  # seconds
MAX_RETRY_ATTEMPTS: Final[int] = 3

# =============================================================================
# Cache Constants
# =============================================================================

CACHE_TTL_SHORT: Final[int] = 60  # 1 minute
CACHE_TTL_MEDIUM: Final[int] = 300  # 5 minutes
CACHE_TTL_LONG: Final[int] = 3600  # 1 hour
CACHE_TTL_VERY_LONG: Final[int] = 86400  # 24 hours

MAX_MEMORY_CACHE_SIZE: Final[int] = 100  # MB
MAX_DISK_CACHE_SIZE: Final[int] = 500  # MB

# =============================================================================
# Enumerations
# =============================================================================


class Theme(str, Enum):
    """Application theme options"""
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


class Language(str, Enum):
    """Supported languages"""
    ENGLISH = "en"
    TURKISH = "tr"
    GERMAN = "de"


class AuthMethod(str, Enum):
    """Authentication methods"""
    SQL_SERVER = "sql_server"
    WINDOWS = "windows"
    LDAP = "ldap"


class ConnectionStatus(str, Enum):
    """Database connection status"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class ObjectType(str, Enum):
    """SQL Server object types"""
    SERVER = "server"
    DATABASE = "database"
    FOLDER = "folder"
    STORED_PROCEDURE = "stored_procedure"
    TRIGGER = "trigger"
    VIEW = "view"
    TABLE = "table"
    INDEX = "index"
    FUNCTION = "function"


class AnalysisCategory(str, Enum):
    """Analysis categories for queries"""
    QUERY_PERFORMANCE = "query_performance"
    INDEX_ANALYSIS = "index_analysis"
    WAIT_STATISTICS = "wait_statistics"
    BLOCKING = "blocking"
    SP_ANALYSIS = "sp_analysis"
    TRIGGER_ANALYSIS = "trigger_analysis"
    VIEW_ANALYSIS = "view_analysis"
    SECURITY = "security"
    SERVER_HEALTH = "server_health"
    JOBS = "jobs"
    BACKUP = "backup"


class ValidationSeverity(str, Enum):
    """AI output validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class TaskStatus(str, Enum):
    """Async task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# SQL Server Version Mapping
# =============================================================================

SQL_SERVER_VERSIONS: Final[dict[int, str]] = {
    16: "SQL Server 2022",
    15: "SQL Server 2019",
    14: "SQL Server 2017",
    13: "SQL Server 2016",
    12: "SQL Server 2014",
    11: "SQL Server 2012",
    10: "SQL Server 2008/2008 R2",
}

# =============================================================================
# Icons (Unicode)
# =============================================================================

ICONS: Final[dict[str, str]] = {
    "server": "🖥️",
    "database": "🗄️",
    "folder": "📁",
    "stored_procedure": "🔧",
    "trigger": "⚡",
    "view": "👁️",
    "table": "📋",
    "index": "📊",
    "warning": "⚠️",
    "error": "❌",
    "success": "✅",
    "loading": "🔄",
    "chat": "💬",
    "settings": "⚙️",
    "search": "🔍",
    "security": "🛡️",
    "performance": "📈",
    "jobs": "📋",
}
