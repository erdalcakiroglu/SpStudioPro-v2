"""
Logging configuration for SQL Performance AI Platform
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

from app.core.constants import APP_NAME, LOG_FILE


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',      # Reset
    }
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, 
                 use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and self._supports_color()
    
    @staticmethod
    def _supports_color() -> bool:
        """Check if terminal supports colors"""
        if sys.platform == 'win32':
            # Windows 10+ supports ANSI colors
            return True
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


class SQLPerfAILogger:
    """Application logger with file and console handlers"""
    
    _instance: Optional['SQLPerfAILogger'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.logger = logging.getLogger(APP_NAME)
        self.logger.setLevel(logging.DEBUG)
        self._handlers: dict[str, logging.Handler] = {}
        self._initialized = True
    
    def setup(
        self,
        level: str = "INFO",
        log_dir: Optional[Path] = None,
        file_enabled: bool = True,
        max_file_size_mb: int = 10,
        backup_count: int = 5,
        retention_days: int = 7,
        console_colors: bool = True,
    ) -> logging.Logger:
        """
        Configure logging with file and console handlers
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
            file_enabled: Enable file logging
            max_file_size_mb: Max size of each log file in MB
            backup_count: Number of backup files to keep
            retention_days: Number of days to keep daily rotated logs
            console_colors: Use colored output in console
        
        Returns:
            Configured logger instance
        """
        # Clear existing handlers
        self.logger.handlers.clear()
        self._handlers.clear()
        
        # Set level
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Console handler
        # Ensure stdout handles unicode on Windows
        if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except Exception:
                pass

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        console_formatter = ColoredFormatter(
            fmt=console_format,
            datefmt="%H:%M:%S",
            use_colors=console_colors
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        self._handlers['console'] = console_handler
        
        # File handler
        if file_enabled and log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / LOG_FILE
            
            # Daily rotation with day-based retention for production troubleshooting.
            file_handler = TimedRotatingFileHandler(
                log_file,
                when='midnight',
                interval=1,
                backupCount=max(1, int(retention_days or backup_count)),
                encoding='utf-8'
            )
            file_handler.suffix = "%Y-%m-%d"
            file_handler.setLevel(logging.DEBUG)  # File gets all levels
            
            file_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
            file_formatter = logging.Formatter(
                fmt=file_format,
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            self._handlers['file'] = file_handler
        
        return self.logger
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Get a child logger with optional name"""
        if name:
            return self.logger.getChild(name)
        return self.logger
    
    def set_level(self, level: str) -> None:
        """Change logging level at runtime"""
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        if 'console' in self._handlers:
            self._handlers['console'].setLevel(log_level)


# Module-level functions for convenience

_app_logger: Optional[SQLPerfAILogger] = None


def setup_logging(
    level: str = "INFO",
    log_dir: Optional[Path] = None,
    file_enabled: bool = True,
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    retention_days: int = 7,
) -> logging.Logger:
    """
    Setup application logging
    
    This should be called once at application startup.
    """
    global _app_logger
    _app_logger = SQLPerfAILogger()
    return _app_logger.setup(
        level=level,
        log_dir=log_dir,
        file_enabled=file_enabled,
        max_file_size_mb=max_file_size_mb,
        backup_count=backup_count,
        retention_days=retention_days,
    )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance
    
    Args:
        name: Optional name for child logger (e.g., 'database', 'ai', 'ui')
    
    Returns:
        Logger instance
    
    Example:
        >>> logger = get_logger('database')
        >>> logger.info('Connected to server')
    """
    global _app_logger
    if _app_logger is None:
        # Setup with defaults if not initialized
        _app_logger = SQLPerfAILogger()
        _app_logger.setup()
    
    return _app_logger.get_logger(name)


def log_exception(logger: logging.Logger, exc: Exception, message: str = "") -> None:
    """
    Log an exception with full traceback
    
    Args:
        logger: Logger instance
        exc: Exception to log
        message: Additional context message
    """
    if message:
        logger.error(f"{message}: {exc}", exc_info=True)
    else:
        logger.error(f"Exception occurred: {exc}", exc_info=True)


class LogContext:
    """
    Context manager for logging operation timing
    
    Example:
        >>> with LogContext(logger, "Loading metadata"):
        ...     load_metadata()
        # Logs: "Loading metadata... started"
        # Logs: "Loading metadata... completed in 1.23s"
    """
    
    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time: Optional[datetime] = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.log(self.level, f"{self.operation}... started")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is not None:
            self.logger.error(f"{self.operation}... failed after {duration:.2f}s: {exc_val}")
        else:
            self.logger.log(self.level, f"{self.operation}... completed in {duration:.2f}s")
        
        return False  # Don't suppress exceptions
