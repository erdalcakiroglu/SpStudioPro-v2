"""
AI Module - SQL Server Performance Analysis with AI

Modules:
- llm_client: Unified multi-provider LLM client (Ollama, OpenAI, Anthropic, DeepSeek, Azure)
- ollama_client: Enhanced Ollama-specific client with model management
- prompts: Advanced prompt engineering and few-shot examples  
- plan_analyzer: Execution plan XML parsing
- response_validator: AI output validation and sanitization
- analysis_service: Main analysis orchestrator
- chat_service: Conversational AI assistant
- intent_detector: Natural language intent detection
- cache: Intelligent caching for AI responses
- self_reflection: Confidence scoring and validation
"""

# Unified LLM Client (Multi-provider support)
from app.ai.llm_client import (
    UnifiedLLMClient,
    get_llm_client,
    generate_response,
    check_llm_connection,
    LLMConfig,
    LLMProviderType,
    BaseLLMProvider,
    OllamaProvider,
    OpenAIProvider,
    AnthropicProvider,
    DeepSeekProvider,
    AzureOpenAIProvider,
)

# Legacy Ollama client (for backwards compatibility)
from app.ai.ollama_client import (
    OllamaClient,
    GenerationOptions,
    RecommendedModel,
    SQL_OPTIMIZATION_OPTIONS,
    CODE_GENERATION_OPTIONS,
    CHAT_OPTIONS,
)

from app.ai.prompts import (
    AdvancedPromptBuilder,
    PromptType,
    PromptContext,
    get_system_prompt,
    get_best_practices,
)

from app.ai.plan_analyzer import (
    ExecutionPlanAnalyzer,
    PlanInsights,
    PlanOperator,
    PlanWarning,
    MissingIndex,
    analyze_plan,
    get_plan_summary,
    get_plan_for_ai,
)

from app.ai.response_validator import (
    AIResponseValidator,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    DangerLevel,
    validate_response,
    sanitize_response,
    get_quality_score,
)

from app.ai.analysis_service import AIAnalysisService

from app.ai.cache import (
    AIAnalysisCache,
    get_ai_cache,
    CacheConfig,
    CacheLevel,
    cached_analysis,
)

from app.ai.self_reflection import (
    SelfReflectionEngine,
    AnalysisConfidence,
    ConfidenceLevel,
    HallucinationDetector,
    ApplicabilityChecker,
    SeverityCalibrator,
    create_confidence_display,
)

__all__ = [
    # Unified LLM Client
    'UnifiedLLMClient',
    'get_llm_client',
    'generate_response',
    'check_llm_connection',
    'LLMConfig',
    'LLMProviderType',
    'BaseLLMProvider',
    'OllamaProvider',
    'OpenAIProvider',
    'AnthropicProvider',
    'DeepSeekProvider',
    'AzureOpenAIProvider',
    
    # Legacy Ollama Client
    'OllamaClient',
    'GenerationOptions',
    'RecommendedModel',
    'SQL_OPTIMIZATION_OPTIONS',
    'CODE_GENERATION_OPTIONS', 
    'CHAT_OPTIONS',
    
    # Prompts
    'AdvancedPromptBuilder',
    'PromptType',
    'PromptContext',
    'get_system_prompt',
    'get_best_practices',
    
    # Plan Analyzer
    'ExecutionPlanAnalyzer',
    'PlanInsights',
    'PlanOperator',
    'PlanWarning',
    'MissingIndex',
    'analyze_plan',
    'get_plan_summary',
    'get_plan_for_ai',
    
    # Response Validator
    'AIResponseValidator',
    'ValidationResult',
    'ValidationIssue',
    'ValidationSeverity',
    'DangerLevel',
    'validate_response',
    'sanitize_response',
    'get_quality_score',
    
    # Services
    'AIAnalysisService',
    
    # Cache
    'AIAnalysisCache',
    'get_ai_cache',
    'CacheConfig',
    'CacheLevel',
    'cached_analysis',
    
    # Self-Reflection
    'SelfReflectionEngine',
    'AnalysisConfidence',
    'ConfidenceLevel',
    'HallucinationDetector',
    'ApplicabilityChecker',
    'SeverityCalibrator',
    'create_confidence_display',
]
