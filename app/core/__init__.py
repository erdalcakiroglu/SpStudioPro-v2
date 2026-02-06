"""
Core module - Configuration, constants, exceptions, and utilities

Provides:
- Settings/Config management
- Custom exceptions
- Error codes and handling
- Retry policies
- Logging
"""

from app.core.config import Settings, get_settings
from app.core.constants import *
from app.core.exceptions import *
from app.core.error_codes import (
    ErrorCode,
    ErrorInfo,
    ErrorSeverity,
    get_error_info,
    format_error_message,
)
from app.core.error_handler import (
    ErrorHandler,
    HandledError,
    get_error_handler,
    setup_error_handler,
    handle_error,
    error_boundary,
    ErrorBoundaryContext,
    show_error_message,
)
from app.core.retry import (
    RetryPolicy,
    RetryConfig,
    RetryExhausted,
    RETRY_QUICK,
    RETRY_STANDARD,
    RETRY_PATIENT,
    RETRY_DATABASE,
    RETRY_AI,
    with_retry,
    retry_on,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Error Codes
    "ErrorCode",
    "ErrorInfo",
    "ErrorSeverity",
    "get_error_info",
    "format_error_message",
    # Error Handler
    "ErrorHandler",
    "HandledError",
    "get_error_handler",
    "setup_error_handler",
    "handle_error",
    "error_boundary",
    "ErrorBoundaryContext",
    "show_error_message",
    # Retry
    "RetryPolicy",
    "RetryConfig",
    "RetryExhausted",
    "RETRY_QUICK",
    "RETRY_STANDARD",
    "RETRY_PATIENT",
    "RETRY_DATABASE",
    "RETRY_AI",
    "with_retry",
    "retry_on",
]
