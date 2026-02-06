"""
Custom exceptions for SQL Performance AI Platform
"""

from typing import Optional, Any


class SQLPerfAIError(Exception):
    """Base exception for all application errors"""
    
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(SQLPerfAIError):
    """Configuration related errors"""
    pass


class InvalidSettingsError(ConfigurationError):
    """Invalid settings value"""
    pass


# =============================================================================
# Database Errors
# =============================================================================


class DatabaseError(SQLPerfAIError):
    """Base database error"""
    pass


class ConnectionError(DatabaseError):
    """Database connection failed"""
    
    def __init__(self, message: str, server: Optional[str] = None, 
                 database: Optional[str] = None, **kwargs):
        details = {"server": server, "database": database, **kwargs}
        super().__init__(message, details)


class ConnectionTimeoutError(ConnectionError):
    """Connection timed out"""
    pass


class AuthenticationError(DatabaseError):
    """Authentication failed"""
    pass


class QueryExecutionError(DatabaseError):
    """Query execution failed"""
    
    def __init__(self, message: str, query: Optional[str] = None, **kwargs):
        details = {"query": query[:500] if query else None, **kwargs}
        super().__init__(message, details)


class QueryTimeoutError(QueryExecutionError):
    """Query execution timed out"""
    pass


class PermissionDeniedError(DatabaseError):
    """Insufficient permissions"""
    pass


class UnsupportedVersionError(DatabaseError):
    """SQL Server version not supported"""
    
    def __init__(self, version: int, min_required: int = 11):
        message = f"SQL Server version {version} is not supported. Minimum required: {min_required}"
        super().__init__(message, {"version": version, "min_required": min_required})


# =============================================================================
# AI/LLM Errors
# =============================================================================


class AIError(SQLPerfAIError):
    """Base AI/LLM error"""
    pass


class LLMConnectionError(AIError):
    """Cannot connect to LLM service"""
    pass


class LLMTimeoutError(AIError):
    """LLM response timed out"""
    pass


class LLMResponseError(AIError):
    """Invalid or unexpected LLM response"""
    pass


class IntentDetectionError(AIError):
    """Failed to detect user intent"""
    pass


class CodeGenerationError(AIError):
    """Failed to generate optimized code"""
    pass


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(SQLPerfAIError):
    """Base validation error"""
    pass


class SQLSyntaxError(ValidationError):
    """SQL syntax is invalid"""
    
    def __init__(self, message: str, line_number: Optional[int] = None, **kwargs):
        details = {"line_number": line_number, **kwargs}
        super().__init__(message, details)


class SecurityValidationError(ValidationError):
    """Security validation failed"""
    
    def __init__(self, message: str, pattern: Optional[str] = None, **kwargs):
        details = {"pattern": pattern, **kwargs}
        super().__init__(message, details)


class SemanticValidationError(ValidationError):
    """Semantic validation failed (object not found, etc.)"""
    pass


# =============================================================================
# UI Errors
# =============================================================================


class UIError(SQLPerfAIError):
    """UI related errors"""
    pass


class ThemeLoadError(UIError):
    """Failed to load theme"""
    pass


class ViewNotFoundError(UIError):
    """Requested view does not exist"""
    pass


# =============================================================================
# Service Errors
# =============================================================================


class ServiceError(SQLPerfAIError):
    """Service layer errors"""
    pass


class ConnectionProfileError(ServiceError):
    """Connection profile related errors"""
    pass


class CredentialStoreError(ServiceError):
    """Credential storage errors"""
    pass


class CacheError(ServiceError):
    """Cache related errors"""
    pass


# =============================================================================
# Analysis Errors
# =============================================================================


class AnalysisError(SQLPerfAIError):
    """Analysis related errors"""
    pass


class ExecutionPlanError(AnalysisError):
    """Failed to parse or analyze execution plan"""
    pass


class MetadataLoadError(AnalysisError):
    """Failed to load metadata"""
    pass


# =============================================================================
# Collector Errors
# =============================================================================


class CollectorError(SQLPerfAIError):
    """Base error for data collectors"""
    
    def __init__(
        self,
        message: str,
        collector_name: Optional[str] = None,
        step_name: Optional[str] = None,
        is_retryable: bool = False,
        **kwargs
    ):
        details = {
            "collector": collector_name,
            "step": step_name,
            "retryable": is_retryable,
            **kwargs
        }
        super().__init__(message, details)
        self.collector_name = collector_name
        self.step_name = step_name
        self.is_retryable = is_retryable


class CollectorTimeoutError(CollectorError):
    """Collection step timed out"""
    
    def __init__(self, collector_name: str, timeout_seconds: int, **kwargs):
        message = f"Collector '{collector_name}' timed out after {timeout_seconds}s"
        super().__init__(
            message,
            collector_name=collector_name,
            is_retryable=True,
            timeout_seconds=timeout_seconds,
            **kwargs
        )


class CollectorSkippedError(CollectorError):
    """Collection step was skipped"""
    
    def __init__(self, collector_name: str, reason: str, **kwargs):
        message = f"Collector '{collector_name}' skipped: {reason}"
        super().__init__(
            message,
            collector_name=collector_name,
            is_retryable=False,
            skip_reason=reason,
            **kwargs
        )


class SourceCodeNotFoundError(CollectorError):
    """Source code could not be retrieved"""
    
    def __init__(self, object_name: str, **kwargs):
        message = f"Source code not found for '{object_name}'"
        super().__init__(
            message,
            collector_name="source_code",
            is_retryable=False,
            object_name=object_name,
            **kwargs
        )


class QueryStoreDisabledError(CollectorError):
    """Query Store is not enabled"""
    
    def __init__(self, database: str, **kwargs):
        message = f"Query Store is disabled for database '{database}'"
        super().__init__(
            message,
            collector_name="query_store",
            is_retryable=False,
            database=database,
            **kwargs
        )


class PlanNotFoundError(CollectorError):
    """Execution plan could not be found"""
    
    def __init__(self, object_name: str, **kwargs):
        message = f"Execution plan not found for '{object_name}'"
        super().__init__(
            message,
            collector_name="plan_xml",
            is_retryable=True,
            object_name=object_name,
            **kwargs
        )


class CollectionPipelineError(CollectorError):
    """Pipeline execution failed"""
    
    def __init__(self, message: str, failed_steps: Optional[list] = None, **kwargs):
        super().__init__(
            message,
            collector_name="pipeline",
            is_retryable=False,
            failed_steps=failed_steps or [],
            **kwargs
        )


# =============================================================================
# Task Errors
# =============================================================================


class TaskError(SQLPerfAIError):
    """Async task errors"""
    pass


class TaskCancelledError(TaskError):
    """Task was cancelled"""
    pass


class TaskTimeoutError(TaskError):
    """Task timed out"""
    pass


# =============================================================================
# Retry Errors
# =============================================================================


class RetryError(SQLPerfAIError):
    """Retry related errors"""
    pass


class RetryExhaustedError(RetryError):
    """All retry attempts exhausted"""
    
    def __init__(self, message: str, attempts: int, last_exception: Optional[Exception] = None):
        details = {
            "attempts": attempts,
            "last_error": str(last_exception) if last_exception else None,
        }
        super().__init__(message, details)
        self.attempts = attempts
        self.last_exception = last_exception
