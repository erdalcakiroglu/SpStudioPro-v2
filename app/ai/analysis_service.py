"""
AI Analysis Service - Enhanced SQL Performance Analysis

Gelişmiş özellikler:
- Multi-provider support (Ollama, OpenAI, Anthropic, DeepSeek, Azure)
- Advanced prompt engineering
- Few-shot learning
- Execution plan analysis
- Response validation
- AI Self-Reflection with confidence scoring
- Intelligent caching
"""

from typing import Dict, Any, Optional, Tuple, List, Callable
from datetime import datetime
import json
import re
from pathlib import Path
from app.ai.llm_client import get_llm_client, UnifiedLLMClient
from app.ai.prompts import AdvancedPromptBuilder, PromptType, PromptContext
from app.ai.plan_analyzer import ExecutionPlanAnalyzer, PlanInsights
from app.ai.response_validator import AIResponseValidator, ValidationResult
from app.ai.index_payload import build_index_analysis_dataset_v2, anonymize_identifier
from app.ai.object_analyzers import create_object_analyzer_for_type, SUPPORTED_OBJECT_TYPES
from app.ai.self_reflection import (
    SelfReflectionEngine, 
    AnalysisConfidence,
    ConfidenceLevel,
    create_confidence_display,
)
from app.ai.cache import AIAnalysisCache, get_ai_cache
from app.models.query_stats_models import QueryStats
from app.core.logger import get_logger
from app.core.config import get_settings, ensure_app_dirs
from app.database.connection import get_connection_manager
from app.core.constants import SQL_SERVER_VERSIONS

logger = get_logger('ai.analysis')


class AIAnalysisService:
    """
    Gelişmiş SQL sorgu analiz servisi
    
    Features:
    - Multi-provider support (aktif provider otomatik kullanılır)
    - Advanced prompts with few-shot examples
    - Execution plan parsing and insights
    - Response validation and quality scoring
    """
    AUTO_EXECUTIVE_SUMMARY_MARKER = "## Executive Summary (Auto-Generated)"
    SELF_REFLECTION_RETRY_ENABLED = True
    SELF_REFLECTION_RETRY_MIN_SCORE = 0.68
    SELF_REFLECTION_RETRY_MIN_FAILED_VALIDATIONS = 2
    SELF_REFLECTION_RETRY_MIN_IMPROVEMENT = 0.03
    
    def __init__(self, provider_id: Optional[str] = None, enable_cache: bool = True):
        """
        Args:
            provider_id: Belirli bir provider kullan (None = aktif provider)
            enable_cache: Cache kullanımını etkinleştir
        """
        self.llm_client = get_llm_client()
        self.provider_id = provider_id  # None = aktif provider kullanılır
        self.plan_analyzer = ExecutionPlanAnalyzer()
        self.response_validator = AIResponseValidator()
        
        # Cache
        self._enable_cache = enable_cache
        self._cache = get_ai_cache() if enable_cache else None
        
        # Self-reflection engine (created per-analysis)
        self._last_confidence: Optional[AnalysisConfidence] = None
        self._last_request_payload: Optional[Dict[str, Any]] = None
        self._last_request_file_path: Optional[str] = None
    
    async def analyze_query(
        self, 
        query_stats: QueryStats, 
        plan_xml: Optional[str] = None,
        validate_response: bool = True
    ) -> str:
        """
        Bir SQL sorgusunu ve metriklerini analiz eder.
        
        Args:
            query_stats: Sorgu istatistikleri
            plan_xml: Opsiyonel execution plan XML'i
            validate_response: AI yanıtını doğrula
            
        Returns:
            AI analizi sonucu (Markdown formatında)
        """
        try:
            logger.info(f"Starting AI analysis for query {query_stats.query_id}")
            
            # Context oluştur
            context = query_stats.to_ai_context()
            metrics = context["query_stats_context"]["metrics"]
            waits = context["query_stats_context"]["wait_profile"]
            stability = context["query_stats_context"]["stability"]
            stats_table = [
                {"metric": "Avg Duration", "value": f"{metrics.get('avg_duration_ms', 0):.0f}", "unit": "ms"},
                {"metric": "P95 Duration", "value": f"{metrics.get('p95_duration_ms', 0):.0f}", "unit": "ms"},
                {"metric": "Avg CPU", "value": f"{metrics.get('avg_cpu_ms', 0):.0f}", "unit": "ms"},
                {"metric": "Avg Logical Reads", "value": f"{metrics.get('avg_logical_reads', 0):,.0f}", "unit": ""},
                {"metric": "Executions", "value": f"{metrics.get('execution_count', 0):,}", "unit": ""},
                {"metric": "Plan Count", "value": f"{metrics.get('plan_count', 0)}", "unit": ""},
            ]
            
            # Plan analizi (varsa)
            plan_insights = None
            if plan_xml:
                plan_insights = self.plan_analyzer.analyze(plan_xml)
                logger.info(f"Plan analysis: {len(plan_insights.warnings)} warnings, "
                           f"{len(plan_insights.missing_indexes)} missing indexes")
            
            # Gelişmiş prompt oluştur
            system_prompt, user_prompt = AdvancedPromptBuilder.build_analysis_prompt(
                query_text=query_stats.query_text,
                metrics=metrics,
                wait_profile=waits,
                stability_info=stability,
                plan_insights=plan_insights.to_dict() if plan_insights else None,
                context=PromptContext(
                    sql_version=self._get_sql_version_string(),
                    additional_context={
                        "object_name": query_stats.object_name,
                        "schema_name": query_stats.schema_name,
                        "stats_table": stats_table,
                        "query_id": query_stats.query_id,
                    }
                )
            )
            
            self._log_analysis_request(
                query_id=query_stats.query_id,
                query_name=query_stats.display_name,
                system_prompt=system_prompt,
                user_prompt=self._build_json_user_prompt(
                    request_type="query_analysis",
                    metadata={
                        "query_id": query_stats.query_id,
                        "query_name": query_stats.display_name,
                        "sql_version": self._get_sql_version_string(),
                    },
                    instruction_prompt=user_prompt,
                    input_data=context,
                    output_contract={
                        "format": "markdown",
                        "goal": "performance_analysis_with_recommendations",
                    },
                ),
                context_data=context,
            )

            llm_json_prompt = self._build_json_user_prompt(
                request_type="query_analysis",
                metadata={
                    "query_id": query_stats.query_id,
                    "query_name": query_stats.display_name,
                    "sql_version": self._get_sql_version_string(),
                },
                instruction_prompt=user_prompt,
                input_data=context,
                output_contract={
                    "format": "markdown",
                    "goal": "performance_analysis_with_recommendations",
                },
            )
            
            # AI'dan yanıt al (aktif veya belirtilen provider ile)
            response = await self.llm_client.generate(
                prompt=llm_json_prompt,
                system_prompt=system_prompt,
                provider_id=self.provider_id,
                temperature=0.1,
                max_tokens=4096,
            )
            
            # Response validation
            if validate_response:
                validation = self.response_validator.validate(response)
                
                if not validation.is_valid:
                    logger.warning(f"Response validation failed: {validation.get_summary()}")
                    response = validation.sanitized_response
                    # Add quality score summary
                    response += f"\n\n---\n📊 **Recommendation Quality Score:** {validation.quality_score:.0f}/100"
                    
                    if validation.blocked_commands:
                        response += "\n⚠️ **Warning:** Some potentially dangerous commands were filtered."
                else:
                    response += f"\n\n---\n📊 **Recommendation Quality Score:** {validation.quality_score:.0f}/100"
            
            self._log_analysis_result(
                query_id=query_stats.query_id,
                query_name=query_stats.display_name,
                response=response,
            )
            return response
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return f"⚠️ An error occurred during analysis: {str(e)}"

    async def analyze_from_context(
        self,
        context: Dict[str, Any],
        validate_response: bool = True
    ) -> str:
        """
        Context dictionary ile analiz yapar (UI'dan gelen zengin context için).
        """
        try:
            query_text = context.get('query_text', '')
            metrics = context.get('metrics', {})
            wait_profile = context.get('wait_profile') or {}
            server_metrics = context.get('server_metrics') or {}
            stability_info = {
                "plan_count": metrics.get('plan_count', 'N/A'),
                "plan_changes_7d": metrics.get('plan_count', 'N/A'),
                "param_sensitivity_suspected": context.get('plan_stability') == "problem",
            }
            stats_table = context.get('stats_table')
            server_table = None
            if server_metrics:
                server_table = [
                    {"metric": "OS CPU", "value": f"{server_metrics.get('os_cpu_percent', 0)}", "unit": "%"},
                    {"metric": "SQL CPU", "value": f"{server_metrics.get('sql_cpu_percent', 0)}", "unit": "%"},
                    {"metric": "Available Memory", "value": f"{server_metrics.get('available_memory_mb', 0):,}", "unit": "MB"},
                    {"metric": "PLE", "value": f"{server_metrics.get('ple_seconds', 0):,}", "unit": "sec"},
                    {"metric": "Buffer Cache Hit", "value": f"{server_metrics.get('buffer_cache_hit_ratio', 0)}", "unit": "%"},
                    {"metric": "Batch Requests", "value": f"{server_metrics.get('batch_requests_per_sec', 0)}", "unit": "req/s"},
                    {"metric": "Transactions", "value": f"{server_metrics.get('transactions_per_sec', 0)}", "unit": "tx/s"},
                    {"metric": "IO Read Latency", "value": f"{server_metrics.get('io_read_latency_ms', 0)}", "unit": "ms"},
                    {"metric": "IO Write Latency", "value": f"{server_metrics.get('io_write_latency_ms', 0)}", "unit": "ms"},
                    {"metric": "Log Write Latency", "value": f"{server_metrics.get('log_write_latency_ms', 0)}", "unit": "ms"},
                    {"metric": "Signal Wait", "value": f"{server_metrics.get('signal_wait_percent', 0)}", "unit": "%"},
                ]

            prompt_context = PromptContext(
                sql_version=self._get_sql_version_string(),
                additional_context={
                    "object_name": context.get('object_name'),
                    "schema_name": context.get('schema_name'),
                    "stats_table": stats_table,
                    "server_stats_table": server_table,
                    "query_id": context.get('query_id'),
                }
            )

            system_prompt, user_prompt = AdvancedPromptBuilder.build_analysis_prompt(
                query_text=query_text,
                metrics=metrics,
                wait_profile=wait_profile,
                stability_info=stability_info,
                plan_insights=None,
                context=prompt_context
            )

            self._log_analysis_request(
                query_id=context.get('query_id'),
                query_name=context.get('query_name', 'Query'),
                system_prompt=system_prompt,
                user_prompt=self._build_json_user_prompt(
                    request_type="query_analysis_context",
                    metadata={
                        "query_id": context.get('query_id'),
                        "query_name": context.get('query_name', 'Query'),
                        "sql_version": self._get_sql_version_string(),
                    },
                    instruction_prompt=user_prompt,
                    input_data=context,
                    output_contract={
                        "format": "markdown",
                        "goal": "performance_analysis_with_recommendations",
                    },
                ),
                context_data=context,
            )

            llm_json_prompt = self._build_json_user_prompt(
                request_type="query_analysis_context",
                metadata={
                    "query_id": context.get('query_id'),
                    "query_name": context.get('query_name', 'Query'),
                    "sql_version": self._get_sql_version_string(),
                },
                instruction_prompt=user_prompt,
                input_data=context,
                output_contract={
                    "format": "markdown",
                    "goal": "performance_analysis_with_recommendations",
                },
            )

            response = await self.llm_client.generate(
                prompt=llm_json_prompt,
                system_prompt=system_prompt,
                provider_id=self.provider_id,
                temperature=0.1,
                max_tokens=4096,
            )

            if validate_response:
                validation = self.response_validator.validate(response)
                if not validation.is_valid:
                    response = validation.sanitized_response
                    response += f"\n\n---\n📊 **Recommendation Quality Score:** {validation.quality_score:.0f}/100"
                    if validation.blocked_commands:
                        response += "\n⚠️ **Warning:** Some potentially dangerous commands were filtered."
                else:
                    response += f"\n\n---\n📊 **Recommendation Quality Score:** {validation.quality_score:.0f}/100"

            self._log_analysis_result(
                query_id=context.get('query_id'),
                query_name=context.get('query_name', 'Query'),
                response=response,
            )

            return response
        except Exception as e:
            logger.error(f"AI context analysis failed: {e}")
            return f"⚠️ An error occurred during analysis: {str(e)}"

    @staticmethod
    def _resolve_object_type_for_analysis(
        object_type: str,
        object_resolution: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Resolve canonical object type from already-normalized upstream data.
        Layer-2 (Object Explorer) is the source of truth for normalization.
        """
        candidate = str(object_type or "").strip().upper()
        if not candidate and isinstance(object_resolution, dict):
            candidate = str(object_resolution.get("object_type", "") or "").strip().upper()
        if candidate not in SUPPORTED_OBJECT_TYPES:
            return "OBJECT"
        return candidate
    
    async def analyze_object(
        self,
        source_code: str,
        object_name: str,
        object_type: str = "",
        database_name: str = "",
        object_resolution: Dict[str, Any] = None,
        stats: Dict[str, Any] = None,
        missing_indexes: list = None,
        dependencies: list = None,
        query_store: Dict[str, Any] = None,
        plan_xml: str = None,
        plan_meta: Dict[str, Any] = None,
        plan_insights: Dict[str, Any] = None,
        existing_indexes: list = None,
        parameter_sniffing: Dict[str, Any] = None,
        historical_trend: Dict[str, Any] = None,
        memory_grants: Dict[str, Any] = None,
        completeness: Dict[str, Any] = None,
        context_warning: str = None,
        deep_analysis: bool = False,                     # NEW: Deep analysis mode
        skip_cache: bool = False,                         # NEW: Skip cache
        streaming: bool = False,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, Optional[AnalysisConfidence]]:
        """
        Database object analysis - Advanced Performance Analysis
        
        Features:
        - Intelligent caching
        - Self-reflection with confidence scoring
        - Deep analysis mode for complex procedures
        - Graceful degradation when data is incomplete
        
        Args:
            source_code: object source code
            object_name: object name
            stats: Çalışma istatistikleri
            missing_indexes: Missing index önerileri
            dependencies: Bağımlılıklar
            query_store: Query Store verileri
            plan_xml: Execution plan XML
            plan_meta: Plan metadata
            plan_insights: ExecutionPlanAnalyzer sonuçları
            existing_indexes: Mevcut index bilgileri
            parameter_sniffing: Parameter sniffing analizi
            historical_trend: Performans trendi
            memory_grants: Memory grant bilgileri
            completeness: Data collection completeness info
            context_warning: Warning about missing data for AI
            deep_analysis: Enable deep analysis mode (3x tokens, ~20% better accuracy)
            skip_cache: Force fresh analysis (skip cache)
            
        Returns:
            Tuple of (AI analysis markdown, AnalysisConfidence)
        """
        try:
            self._last_request_payload = None
            self._last_request_file_path = None
            quality_level = "unknown"
            if completeness:
                quality_level = completeness.get('quality_level', 'unknown')
            normalized_object_type = self._resolve_object_type_for_analysis(
                object_type=object_type,
                object_resolution=object_resolution,
            )
            analyzer = create_object_analyzer_for_type(normalized_object_type)
            requires_index_policy = bool(getattr(analyzer, "requires_index_policy", False))
            logger.info(
                f"Starting object analysis for {object_name} "
                f"(type: {normalized_object_type}, data quality: {quality_level}, deep: {deep_analysis})"
            )

            plan_signal_summary = self._build_plan_signal_summary(
                source_code=source_code,
                plan_insights=plan_insights or {},
                query_store=query_store or {},
            )
            environment_policy = self._collect_environment_policy_context(database_name)
            if not isinstance(object_resolution, dict):
                object_resolution = {"object_resolved": True, "object_id": None}
            object_resolution = dict(object_resolution)
            if "object_type" not in object_resolution:
                object_resolution["object_type"] = normalized_object_type

            # Build context dict for self-reflection
            context = self._build_context_dict(
                source_code, object_name, stats, missing_indexes, dependencies,
                query_store, plan_xml, plan_meta, plan_insights, existing_indexes,
                parameter_sniffing, historical_trend, memory_grants, completeness,
                object_resolution, plan_signal_summary, environment_policy, normalized_object_type,
            )
            index_gate: Dict[str, Any] = {
                "allowed": True,
                "coverage_ratio": 0.0,
                "usage_coverage_ratio": 0.0,
                "usage_window_days": 14,
                "missing_data_hints": [],
                "policy_reason": "index_policy_not_required_for_object_type",
            }
            if requires_index_policy:
                index_gate = self._evaluate_index_coverage_and_usage(
                    existing_indexes=existing_indexes,
                    object_resolution=object_resolution,
                    sargability_flags=plan_signal_summary.get("sargability_flags", []),
                )
                hints = index_gate.get("missing_data_hints", [])
                if not missing_indexes:
                    hints = list(hints) + ["missing_index_dmvs(mi_score,mi_columns_signature)"]
                if not environment_policy.get("engine_edition"):
                    hints = list(hints) + ["environment_policy(engine_edition,compat_level,maintenance_window_minutes)"]
                # Stable dedup for hints list.
                seen = set()
                deduped_hints = []
                for h in hints:
                    if h in seen:
                        continue
                    seen.add(h)
                    deduped_hints.append(h)
                index_gate["missing_data_hints"] = deduped_hints
            context["index_recommendation_gate"] = index_gate

            missing_indexes_for_prompt = missing_indexes
            effective_context_warning = context_warning
            if requires_index_policy and not index_gate.get("allowed", False):
                # Enforce mandatory validation gate before any index recommendation generation.
                missing_indexes_for_prompt = []
                gate_warning = (
                    "Index recommendation gate is BLOCKED: "
                    "existing index coverage + dm_db_index_usage_stats validation is missing/insufficient."
                )
                if effective_context_warning:
                    effective_context_warning = f"{effective_context_warning}\n{gate_warning}"
                else:
                    effective_context_warning = gate_warning
                hints = index_gate.get("missing_data_hints", [])
                if hints:
                    effective_context_warning += "\nMissing data hints: " + ", ".join(str(h) for h in hints)
            
            missing_indexes_for_prompt_anon = self._anonymize_missing_indexes(missing_indexes_for_prompt)
            existing_indexes_for_prompt_anon = self._anonymize_existing_indexes(existing_indexes)

            # Build prompt
            system_prompt, user_prompt = AdvancedPromptBuilder.build_sp_optimization_prompt(
                source_code=source_code,
                object_name=object_name,
                stats=stats,
                missing_indexes=missing_indexes_for_prompt_anon,
                dependencies=dependencies,
                query_store=query_store,
                plan_xml=plan_xml,
                plan_meta=plan_meta,
                plan_insights=plan_insights,
                existing_indexes=existing_indexes_for_prompt_anon,
                parameter_sniffing=parameter_sniffing,
                historical_trend=historical_trend,
                memory_grants=memory_grants,
                completeness=completeness,
                context_warning=effective_context_warning,
                context=PromptContext(sql_version=self._get_sql_version_string())
            )
            
            # Add deep analysis enhancement if requested
            if deep_analysis:
                try:
                    reflection_engine = SelfReflectionEngine(context)
                    enhancement = reflection_engine.get_deep_analysis_prompt_enhancement()
                    user_prompt = enhancement + "\n\n" + user_prompt
                except Exception as e:
                    logger.warning(f"Deep analysis enhancement skipped: {e}")

            analyzer_profile = analyzer.build_profile(
                index_gate=index_gate,
                environment_policy=environment_policy,
            )
            for block in analyzer_profile.prompt_blocks:
                block_text = str(block or "").strip()
                if block_text:
                    user_prompt += f"\n\n{block_text}"
            user_prompt += (
                "\n\n### RESPONSE LANGUAGE\n"
                "- Output must be English only.\n"
                "- Do not include Turkish text in headers, explanations, or recommendations.\n"
            )

            llm_json_prompt = self._build_json_user_prompt(
                request_type=analyzer_profile.request_type,
                metadata={
                    "object_name": object_name,
                    "object_type": normalized_object_type,
                    "analysis_mode": "deep" if deep_analysis else "standard",
                    "sql_version": self._get_sql_version_string(),
                },
                instruction_prompt=user_prompt,
                input_data=self._build_sp_analysis_json_input(
                    source_code=source_code,
                    object_name=object_name,
                    object_type=normalized_object_type,
                    stats=stats,
                    missing_indexes=missing_indexes_for_prompt_anon,
                    dependencies=dependencies,
                    query_store=query_store,
                    plan_xml=plan_xml,
                    plan_meta=plan_meta,
                    plan_insights=plan_insights,
                    existing_indexes=existing_indexes_for_prompt_anon,
                    parameter_sniffing=parameter_sniffing,
                    historical_trend=historical_trend,
                    memory_grants=memory_grants,
                    completeness=completeness,
                    context_warning=effective_context_warning,
                    index_recommendation_gate=index_gate,
                    object_resolution=object_resolution,
                    plan_signal_summary=plan_signal_summary,
                    environment_policy=environment_policy,
                ),
                output_contract={
                    "format": "markdown",
                    "sections": analyzer_profile.sections,
                    "section_requirements": analyzer_profile.section_requirements,
                },
            )
            prompt_payload = self._parse_json_user_prompt(llm_json_prompt)
            prompt_input = (
                prompt_payload.get("input_data", {})
                if isinstance(prompt_payload.get("input_data", {}), dict)
                else {}
            )
            auto_exec_summary = self._build_auto_executive_summary_markdown(
                object_name=object_name,
                stats=stats or {},
                historical_trend=historical_trend or {},
                index_pre_analysis=prompt_input.get("index_pre_analysis", {}),
                plan_signal_summary=plan_signal_summary or {},
                index_recommendation_gate=index_gate or {},
            )

            # Check cache first (unless skip_cache or deep_analysis)
            if self._cache and not skip_cache and not deep_analysis:
                cached = self._cache.get_analysis(object_name, source_code, "optimization")
                if cached:
                    logger.info(f"Cache hit for {object_name}")
                    # Preserve would-be request payload so UI can export it even on cache hits.
                    self._last_request_payload = self._build_export_request_payload(
                        query_id=None,
                        query_name=object_name,
                        system_prompt=system_prompt,
                        user_prompt=llm_json_prompt,
                        context_data=context,
                        cache_hit=True,
                        llm_request_performed=False,
                    )
                    self._last_request_file_path = None

                    # Re-run self-reflection on cached result
                    cached = self._ensure_auto_executive_summary(cached, auto_exec_summary)
                    confidence = self._run_self_reflection(cached, context)
                    return cached, confidence

            self._log_analysis_request(
                query_id=None,
                query_name=object_name,
                system_prompt=system_prompt,
                user_prompt=llm_json_prompt,
                context_data=context,
            )
            
            if streaming:
                response = await self.llm_client.generate_streaming(
                    prompt=llm_json_prompt,
                    system_prompt=system_prompt,
                    provider_id=self.provider_id,
                    temperature=0.1 if not deep_analysis else 0.05,  # Lower temp for deep
                    on_chunk=on_chunk,
                )
            else:
                response = await self.llm_client.generate(
                    prompt=llm_json_prompt,
                    system_prompt=system_prompt,
                    provider_id=self.provider_id,
                    temperature=0.1 if not deep_analysis else 0.05,  # Lower temp for deep
                )

            response = await self._continue_report_if_truncated(
                response=response,
                system_prompt=system_prompt,
            )

            # Validate
            validation = self.response_validator.validate(response)
            response = validation.sanitized_response
            if requires_index_policy and not index_gate.get("allowed", False):
                response = self._enforce_no_index_recommendations(response, index_gate)
            response = self._ensure_auto_executive_summary(response, auto_exec_summary)
             
            # Run self-reflection
            confidence = self._run_self_reflection(response, context)
            refinement_applied = False
            if self._should_run_self_reflection_refinement(confidence, deep_analysis=deep_analysis):
                logger.info(
                    f"Self-reflection refinement triggered for {object_name} "
                    f"(confidence={confidence.percentage}%, failed_validations={confidence.failed_validations})"
                )
                refined_response = await self._run_self_reflection_refinement_pass(
                    previous_response=response,
                    confidence=confidence,
                    system_prompt=system_prompt,
                    object_name=object_name,
                    object_type=normalized_object_type,
                    analyzer_profile=analyzer_profile,
                )
                if refined_response:
                    refined_response = await self._continue_report_if_truncated(
                        response=refined_response,
                        system_prompt=system_prompt,
                    )
                    refined_validation = self.response_validator.validate(refined_response)
                    refined_response = refined_validation.sanitized_response
                    if requires_index_policy and not index_gate.get("allowed", False):
                        refined_response = self._enforce_no_index_recommendations(refined_response, index_gate)
                    refined_response = self._ensure_auto_executive_summary(refined_response, auto_exec_summary)
                    refined_confidence = self._run_self_reflection(refined_response, context)
                    if self._is_refinement_improved(confidence, refined_confidence):
                        response = refined_response
                        validation = refined_validation
                        confidence = refined_confidence
                        refinement_applied = True
                        logger.info(
                            f"Self-reflection refinement accepted for {object_name} "
                            f"(new_confidence={confidence.percentage}%)"
                        )
                    else:
                        logger.info(f"Self-reflection refinement discarded for {object_name} (no meaningful improvement)")
            self._last_confidence = confidence
             
            # Add confidence info to response
            response += f"\n\n---\n📊 **Recommendation Quality Score:** {validation.quality_score:.0f}/100"
            response += f"\n{confidence.emoji} **Analysis Confidence:** {confidence.percentage}% ({confidence.level.value})"
            if refinement_applied:
                response += "\nℹ️ **Self-Reflection Refinement:** Applied a second-pass correction due to low confidence."
            
            if confidence.warnings:
                response += "\n\n**⚠️ Validation Warnings:**"
                for warning in confidence.warnings[:3]:
                    response += f"\n- {warning}"
            
            if confidence.deep_analysis_recommended and not deep_analysis:
                response += "\n\n💡 *Deep Analysis mode is recommended for a more comprehensive review.*"
            
            # Cache the result (only standard analysis, not deep)
            if self._cache and not deep_analysis:
                self._cache.set_analysis(object_name, source_code, response, "optimization")
            
            self._log_analysis_result(
                query_id=None,
                query_name=object_name,
                response=response,
            )
            
            return response, confidence
            
        except Exception as e:
            logger.error(f"Object analysis failed: {e}")
            return f"⚠️ An error occurred during analysis: {str(e)}", None

    async def analyze_sp(
        self,
        source_code: str,
        object_name: str,
        object_type: str = "",
        database_name: str = "",
        object_resolution: Dict[str, Any] = None,
        stats: Dict[str, Any] = None,
        missing_indexes: list = None,
        dependencies: list = None,
        query_store: Dict[str, Any] = None,
        plan_xml: str = None,
        plan_meta: Dict[str, Any] = None,
        plan_insights: Dict[str, Any] = None,
        existing_indexes: list = None,
        parameter_sniffing: Dict[str, Any] = None,
        historical_trend: Dict[str, Any] = None,
        memory_grants: Dict[str, Any] = None,
        completeness: Dict[str, Any] = None,
        context_warning: str = None,
        deep_analysis: bool = False,
        skip_cache: bool = False,
        streaming: bool = False,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, Optional[AnalysisConfidence]]:
        """
        Backward-compatible wrapper. Use analyze_object() for new call sites.
        """
        return await self.analyze_object(
            source_code=source_code,
            object_name=object_name,
            object_type=object_type,
            database_name=database_name,
            object_resolution=object_resolution,
            stats=stats,
            missing_indexes=missing_indexes,
            dependencies=dependencies,
            query_store=query_store,
            plan_xml=plan_xml,
            plan_meta=plan_meta,
            plan_insights=plan_insights,
            existing_indexes=existing_indexes,
            parameter_sniffing=parameter_sniffing,
            historical_trend=historical_trend,
            memory_grants=memory_grants,
            completeness=completeness,
            context_warning=context_warning,
            deep_analysis=deep_analysis,
            skip_cache=skip_cache,
            streaming=streaming,
            on_chunk=on_chunk,
        )
    
    def _build_context_dict(
        self,
        source_code: str,
        object_name: str,
        stats: Dict[str, Any],
        missing_indexes: list,
        dependencies: list,
        query_store: Dict[str, Any],
        plan_xml: str,
        plan_meta: Dict[str, Any],
        plan_insights: Dict[str, Any],
        existing_indexes: list,
        parameter_sniffing: Dict[str, Any],
        historical_trend: Dict[str, Any],
        memory_grants: Dict[str, Any],
        completeness: Dict[str, Any],
        object_resolution: Dict[str, Any],
        plan_signal_summary: Dict[str, Any],
        environment_policy: Dict[str, Any],
        object_type: str = "OBJECT",
    ) -> Dict[str, Any]:
        """Build context dictionary for self-reflection"""
        return {
            "source_code": source_code,
            "object_name": object_name,
            "object_type": object_type,
            "stats": stats or {},
            "missing_indexes": missing_indexes or [],
            "depends_on": dependencies or [],
            "query_store": query_store or {},
            "plan_xml": plan_xml or "",
            "plan_meta": plan_meta or {},
            "plan_insights": plan_insights or {},
            "existing_indexes": existing_indexes or [],
            "parameter_sniffing": parameter_sniffing or {},
            "historical_trend": historical_trend or {},
            "memory_grants": memory_grants or {},
            "completeness": completeness or {},
            "object_resolution": object_resolution or {},
            "plan_signal_summary": plan_signal_summary or {},
            "environment_policy": environment_policy or {},
        }

    @staticmethod
    def _truncate_text(value: Any, max_len: int = 6000) -> str:
        """Convert to string and truncate long text fields for JSON prompt payloads."""
        if value is None:
            return ""
        text = str(value)
        if len(text) <= max_len:
            return text
        return text[:max_len] + "\n... [truncated]"

    @staticmethod
    def _compact_existing_indexes(
        existing_indexes: Any,
        max_tables: int = 5,
        max_indexes_per_table: int = 8,
    ) -> list:
        if not isinstance(existing_indexes, list):
            return []
        compact = []
        for table_info in existing_indexes[:max_tables]:
            if not isinstance(table_info, dict):
                continue
            item = {
                "table": table_info.get("table", table_info.get("table_hash", "")),
                "indexes": [],
            }
            indexes = table_info.get("indexes", [])
            if isinstance(indexes, list):
                item["indexes"] = indexes[:max_indexes_per_table]
            compact.append(item)
        return compact

    @staticmethod
    def _anonymize_existing_indexes(existing_indexes: Any) -> list:
        if not isinstance(existing_indexes, list):
            return []
        anonymized: list = []
        for table_info in existing_indexes:
            if not isinstance(table_info, dict):
                continue
            table_name = str(table_info.get("table", "") or "")
            item = {
                "table_hash": anonymize_identifier(table_name),
                "indexes": [],
            }
            indexes = table_info.get("indexes", [])
            if isinstance(indexes, list):
                for idx in indexes:
                    if not isinstance(idx, dict):
                        continue
                    item["indexes"].append(
                        {
                            "index_hash": anonymize_identifier(str(idx.get("name", "") or idx.get("index_name", ""))),
                            "type": idx.get("type", idx.get("index_type", "")),
                            "is_unique": bool(idx.get("is_unique", False)),
                            "is_pk": bool(idx.get("is_pk", idx.get("is_primary_key", False))),
                            "is_unique_constraint": bool(idx.get("is_unique_constraint", False)),
                            "is_disabled": bool(idx.get("is_disabled", False)),
                            "has_filter": bool(idx.get("has_filter", False)),
                            "fill_factor": idx.get("fill_factor", 0),
                            "is_padded": bool(idx.get("is_padded", False)),
                            "allow_row_locks": bool(idx.get("allow_row_locks", True)),
                            "allow_page_locks": bool(idx.get("allow_page_locks", True)),
                            "data_compression_desc": idx.get("data_compression_desc", "UNKNOWN"),
                            "is_duplicate": bool(idx.get("is_duplicate", False)),
                            "duplicate_type": idx.get("duplicate_type", ""),
                            "overlap_group_id": idx.get("overlap_group_id", ""),
                            "covered_by": idx.get("covered_by", {}),
                            "redundant_with_include": bool(idx.get("redundant_with_include", False)),
                            "covered_by_index_hash": anonymize_identifier(str(idx.get("covered_by_index", ""))),
                            "key_type_signature": idx.get("key_type_signature", ""),
                            "left_prefix_signature": idx.get("left_prefix_signature", ""),
                            "include_type_signature": idx.get("include_type_signature", ""),
                            "include_signature": idx.get("include_signature", ""),
                            "filter_signature": idx.get("filter_signature", ""),
                            "key_column_count": idx.get("key_column_count", 0),
                            "include_column_count": idx.get("include_column_count", 0),
                            "key_column_total_bytes": idx.get("key_column_total_bytes", 0),
                            "key_width_limit_bytes": idx.get("key_width_limit_bytes", 900),
                            "key_width_over_limit": bool(idx.get("key_width_over_limit", False)),
                            "all_columns_not_null": bool(idx.get("all_columns_not_null", False)),
                            "all_columns_fixed_length": bool(idx.get("all_columns_fixed_length", False)),
                            "has_lob_in_include": bool(idx.get("has_lob_in_include", False)),
                            "is_used": bool(idx.get("is_used", False)),
                            "access_pattern": idx.get("access_pattern", "NO_READS"),
                            "total_reads": idx.get("total_reads", 0),
                            "total_writes": idx.get("total_writes", 0),
                            "seeks": idx.get("seeks", idx.get("user_seeks", 0)),
                            "scans": idx.get("scans", idx.get("user_scans", 0)),
                            "lookups": idx.get("lookups", idx.get("user_lookups", 0)),
                            "updates": idx.get("updates", idx.get("user_updates", 0)),
                            "user_seeks": idx.get("user_seeks", idx.get("seeks", 0)),
                            "user_scans": idx.get("user_scans", idx.get("scans", 0)),
                            "user_lookups": idx.get("user_lookups", idx.get("lookups", 0)),
                            "user_updates": idx.get("user_updates", idx.get("updates", 0)),
                            "last_user_seek": idx.get("last_user_seek"),
                            "last_user_scan": idx.get("last_user_scan"),
                            "last_user_lookup": idx.get("last_user_lookup"),
                            "last_user_update": idx.get("last_user_update"),
                            "usage_window": idx.get("usage_window", {}),
                            "reads": idx.get("reads", {}),
                            "writes": idx.get("writes", {}),
                            "derived_metrics": idx.get("derived_metrics", {}),
                            "table_rows": idx.get("table_rows", 0),
                            "reserved_mb": idx.get("reserved_mb", 0),
                            "used_mb": idx.get("used_mb", 0),
                            "data_mb": idx.get("data_mb", 0),
                            "index_mb": idx.get("index_mb", 0),
                            "unused_mb": idx.get("unused_mb", 0),
                            "partition_count": idx.get("partition_count", 0),
                            "partition_scheme_name": idx.get("partition_scheme_name", ""),
                            "avg_fragmentation_in_percent": idx.get("avg_fragmentation_in_percent", 0),
                            "fragment_count": idx.get("fragment_count", 0),
                            "avg_fragment_size_in_pages": idx.get("avg_fragment_size_in_pages", 0),
                            "avg_page_space_used_in_percent": idx.get("avg_page_space_used_in_percent", 0),
                            "page_count": idx.get("page_count", 0),
                            "ghost_record_count": idx.get("ghost_record_count", 0),
                            "version_ghost_record_count": idx.get("version_ghost_record_count", 0),
                            "forwarded_record_count": idx.get("forwarded_record_count", 0),
                            "index_depth": idx.get("index_depth", 0),
                            "index_level": idx.get("index_level", 0),
                            "alloc_unit_type_desc": idx.get("alloc_unit_type_desc", ""),
                            "physical_scan_mode": idx.get("physical_scan_mode", "LIMITED"),
                            "last_stats_update": idx.get("last_stats_update"),
                            "stats_rows": idx.get("stats_rows", 0),
                            "rows_sampled": idx.get("rows_sampled", 0),
                            "modification_counter": idx.get("modification_counter", 0),
                            "modification_ratio": idx.get("modification_ratio", 0),
                            "days_since_last_stats_update": idx.get("days_since_last_stats_update", 0),
                            "stats_auto_created": bool(idx.get("stats_auto_created", False)),
                            "stats_user_created": bool(idx.get("stats_user_created", False)),
                            "stats_no_recompute": bool(idx.get("stats_no_recompute", False)),
                            "stats_is_incremental": bool(idx.get("stats_is_incremental", False)),
                            "stats_needs_update": bool(idx.get("stats_needs_update", False)),
                            "leaf_insert_count": idx.get("leaf_insert_count", 0),
                            "leaf_update_count": idx.get("leaf_update_count", 0),
                            "leaf_delete_count": idx.get("leaf_delete_count", 0),
                            "range_scan_count": idx.get("range_scan_count", 0),
                            "singleton_lookup_count": idx.get("singleton_lookup_count", 0),
                            "row_lock_count": idx.get("row_lock_count", 0),
                            "row_lock_wait_count": idx.get("row_lock_wait_count", 0),
                            "row_lock_wait_in_ms": idx.get("row_lock_wait_in_ms", 0),
                            "page_lock_count": idx.get("page_lock_count", 0),
                            "page_lock_wait_count": idx.get("page_lock_wait_count", 0),
                            "page_lock_wait_in_ms": idx.get("page_lock_wait_in_ms", 0),
                            "page_io_latch_wait_count": idx.get("page_io_latch_wait_count", 0),
                            "page_io_latch_wait_in_ms": idx.get("page_io_latch_wait_in_ms", 0),
                            "page_latch_wait_count": idx.get("page_latch_wait_count", 0),
                            "page_latch_wait_in_ms": idx.get("page_latch_wait_in_ms", 0),
                            "contention_score": idx.get("contention_score", 0),
                            "supports_fk": bool(idx.get("supports_fk", False)),
                            "final_class": idx.get("final_class", ""),
                            "rule_id": idx.get("rule_id", ""),
                            "explanation_code": idx.get("explanation_code", ""),
                        }
                    )
            anonymized.append(item)
        return anonymized

    @staticmethod
    def _anonymize_missing_indexes(missing_indexes: Any) -> list:
        if not isinstance(missing_indexes, list):
            return []
        anonymized: list = []
        for row in missing_indexes:
            if not isinstance(row, dict):
                continue
            signature_key = "|".join(
                [
                    str(row.get("equality_columns", "")),
                    str(row.get("inequality_columns", "")),
                    str(row.get("included_columns", "")),
                ]
            )
            anonymized.append(
                {
                    "mi_hash": anonymize_identifier(signature_key),
                    "avg_user_impact": row.get("avg_user_impact", 0),
                    "avg_total_user_cost": row.get("avg_total_user_cost", 0),
                    "user_seeks": row.get("user_seeks", 0),
                    "user_scans": row.get("user_scans", 0),
                    "impact_score": row.get("impact_score", 0),
                    "equality_signature": row.get("equality_signature", ""),
                    "inequality_signature": row.get("inequality_signature", ""),
                    "include_signature": row.get("include_signature", ""),
                    "mi_columns_signature": row.get("mi_columns_signature", ""),
                    "equality_columns": row.get("equality_columns_profile", {}),
                    "inequality_columns": row.get("inequality_columns_profile", {}),
                    "include_columns": row.get("include_columns_profile", {}),
                    "key_columns": row.get("key_columns_profile", {}),
                }
            )
        return anonymized

    def _compact_query_store(self, query_store: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(query_store, dict):
            return {}

        compact = {
            "days": query_store.get("days", 7),
            "status": query_store.get("status", {}),
            "summary": query_store.get("summary", {}),
            "waits": [],
            "top_queries": [],
            "query_patterns": [],
        }

        waits = query_store.get("waits", [])
        if isinstance(waits, list):
            compact["waits"] = waits[:10]

        top_queries = query_store.get("top_queries", [])
        if isinstance(top_queries, list):
            normalized = []
            for q in top_queries[:5]:
                if not isinstance(q, dict):
                    continue
                # Explicit privacy rule: do not include raw SQL text in LLM payload.
                item = {k: v for k, v in q.items() if k != "query_text"}
                normalized.append(item)
            compact["top_queries"] = normalized

        query_patterns = query_store.get("query_patterns", [])
        if isinstance(query_patterns, list):
            compact["query_patterns"] = [q for q in query_patterns[:10] if isinstance(q, dict)]

        return compact

    @staticmethod
    def _engine_edition_name(code: Any) -> str:
        mapping = {
            2: "Standard",
            3: "Enterprise",
            4: "Express",
            5: "Azure SQL Database",
            6: "Azure Synapse",
            8: "Managed Instance",
            9: "Azure SQL Edge",
            11: "Serverless",
        }
        try:
            return mapping.get(int(code), f"Unknown({code})")
        except Exception:
            return "Unknown"

    def _collect_environment_policy_context(self, database_name: Optional[str]) -> Dict[str, Any]:
        settings = get_settings()
        maintenance_minutes = 60
        env: Dict[str, Any] = {
            "engine_edition": "Unknown",
            "engine_edition_code": None,
            "compat_level": None,
            "maintenance_window_minutes": maintenance_minutes,
        }
        try:
            conn_mgr = get_connection_manager()
            active_conn = conn_mgr.active_connection
            if not active_conn or not active_conn.is_connected:
                return env
            query = """
            SELECT
                CAST(SERVERPROPERTY('EngineEdition') AS INT) AS engine_edition_code,
                CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(64)) AS product_version,
                (SELECT compatibility_level FROM sys.databases WHERE name = :db_name) AS compat_level
            """
            rows = active_conn.execute_query(query, {"db_name": database_name or ""})
            if rows:
                row = rows[0]
                code = row.get("engine_edition_code")
                env["engine_edition_code"] = code
                env["engine_edition"] = self._engine_edition_name(code)
                env["compat_level"] = row.get("compat_level")
                env["product_version"] = row.get("product_version")
        except Exception:
            pass
        return env

    @staticmethod
    def _extract_plan_missing_index_signatures(plan_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(plan_insights, dict):
            return []
        result: List[Dict[str, Any]] = []
        for item in (plan_insights.get("missing_indexes") or [])[:10]:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    "table_hash": anonymize_identifier(str(item.get("table", ""))),
                    "equality_signature": str(
                        (item.get("equality_columns_profile") or {}).get("signature", item.get("equality_columns", ""))
                    ),
                    "inequality_signature": str(
                        (item.get("inequality_columns_profile") or {}).get("signature", item.get("inequality_columns", ""))
                    ),
                    "include_signature": str(
                        (item.get("include_columns_profile") or {}).get("signature", item.get("include_columns", ""))
                    ),
                    "key_columns": item.get("key_columns_profile", {}),
                    "impact_pct": item.get("impact", item.get("avg_user_impact", 0)),
                }
            )
        return result

    @staticmethod
    def _detect_sargability_flags(
        source_code: str,
        plan_insights: Dict[str, Any],
        query_store: Dict[str, Any],
    ) -> List[str]:
        flags: List[str] = []
        text = str(source_code or "")
        lower = text.lower()
        if re.search(r"\blike\s+N?'%[^']*", lower):
            flags.append("leading_wildcard")
        if re.search(r"\bwhere\b[\s\S]{0,120}\b[a-z_][a-z0-9_]*\s*\(", lower):
            flags.append("function_on_column")
        if "cursor" in lower or re.search(r"\bwhile\b", lower):
            flags.append("RBAR")

        if isinstance(plan_insights, dict):
            if bool(plan_insights.get("has_implicit_conversion")):
                flags.append("implicit_convert")
            warnings = plan_insights.get("warnings", [])
            if isinstance(warnings, list):
                warn_text = " ".join(str(w) for w in warnings).lower()
                if "implicit" in warn_text and "convert" in warn_text:
                    flags.append("implicit_convert")

        if isinstance(query_store, dict):
            patterns = query_store.get("query_patterns", query_store.get("top_queries", []))
            if isinstance(patterns, list) and patterns:
                total_exec = 0.0
                range_exec = 0.0
                for p in patterns[:10]:
                    if not isinstance(p, dict):
                        continue
                    freq = float(p.get("total_executions", p.get("frequency", 0)) or 0)
                    total_exec += freq
                    if str(p.get("pattern_type", "")).upper() == "RANGE_SCAN":
                        range_exec += freq
                if total_exec > 0 and (range_exec / total_exec) >= 0.5:
                    flags.append("range_scan_heavy")

        uniq: List[str] = []
        for f in flags:
            if f not in uniq:
                uniq.append(f)
        return uniq

    def _build_plan_signal_summary(
        self,
        source_code: str,
        plan_insights: Dict[str, Any],
        query_store: Dict[str, Any],
    ) -> Dict[str, Any]:
        flags = self._detect_sargability_flags(source_code, plan_insights, query_store)
        key_lookup_seen = bool((plan_insights or {}).get("has_key_lookup", False))
        range_scan_heavy = "range_scan_heavy" in flags
        seekable = not any(
            f in flags for f in ("leading_wildcard", "function_on_column", "implicit_convert", "RBAR")
        )
        return {
            "sargability_flags": flags,
            "seekable": seekable,
            "range_scan_heavy": range_scan_heavy,
            "key_lookup_seen": key_lookup_seen,
            "mi_columns_signature": self._extract_plan_missing_index_signatures(plan_insights or {}),
        }

    @staticmethod
    def _build_json_user_prompt(
        request_type: str,
        metadata: Dict[str, Any],
        instruction_prompt: str,
        input_data: Dict[str, Any],
        output_contract: Dict[str, Any],
    ) -> str:
        """Build JSON payload text to send as LLM user prompt."""
        payload = {
            "request_type": request_type,
            "metadata": metadata or {},
            "instruction_prompt": instruction_prompt,
            "input_data": input_data or {},
            "output_contract": output_contract or {},
        }
        return json.dumps(payload, ensure_ascii=False, default=str, separators=(",", ":"))

    @staticmethod
    def _parse_json_user_prompt(user_prompt: str) -> Dict[str, Any]:
        """Parse JSON user prompt; fallback to text envelope if parsing fails."""
        try:
            parsed = json.loads(user_prompt or "")
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        return {
            "request_type": "text_prompt",
            "metadata": {},
            "instruction_prompt": user_prompt or "",
            "input_data": {},
            "output_contract": {},
        }

    def _resolve_provider_snapshot(self) -> Dict[str, Any]:
        """Resolve current provider/model information for payload metadata."""
        resolved_id = self.provider_id or getattr(self.llm_client, "active_provider_id", "")
        provider = self.llm_client.get_provider(self.provider_id) if self.provider_id else self.llm_client.active_provider

        provider_name = getattr(provider, "name", "") if provider else ""
        model = getattr(provider, "model", "") if provider else ""
        provider_type = ""
        if provider and getattr(provider, "config", None) is not None:
            try:
                provider_type = provider.config.provider_type.value
            except Exception:
                provider_type = ""

        return {
            "provider": resolved_id or provider_name or "unknown",
            "provider_id": resolved_id or "",
            "provider_name": provider_name,
            "provider_type": provider_type,
            "model": model,
        }

    def _build_export_request_payload(
        self,
        query_id: Optional[int],
        query_name: str,
        system_prompt: str,
        user_prompt: str,
        context_data: Dict[str, Any],
        cache_hit: bool = False,
        llm_request_performed: bool = True,
    ) -> Dict[str, Any]:
        """Build standardized export payload for UI save and audit logs."""
        prompt_payload = self._parse_json_user_prompt(user_prompt)
        provider = self._resolve_provider_snapshot()

        metadata = prompt_payload.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        metadata = dict(metadata)
        metadata["cache_hit"] = cache_hit
        metadata["llm_request_performed"] = llm_request_performed

        return {
            "schema_version": "1.0",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "query_id": query_id,
            "query_name": query_name,
            # Required top-level fields for downstream analysis.
            "provider": provider.get("provider", ""),
            "model": provider.get("model", ""),
            "cache_hit": cache_hit,
            # Additional provider diagnostics.
            "provider_id": provider.get("provider_id", ""),
            "provider_name": provider.get("provider_name", ""),
            "provider_type": provider.get("provider_type", ""),
            "llm_request_performed": llm_request_performed,
            # LLM request body (normalized envelope).
            "request_type": prompt_payload.get("request_type", "unknown"),
            "metadata": metadata,
            "instruction_prompt": prompt_payload.get("instruction_prompt", ""),
            "input_data": prompt_payload.get("input_data", {}),
            "output_contract": prompt_payload.get("output_contract", {}),
            # Full trace for reproducibility.
            "system_prompt": system_prompt,
            "raw_user_prompt": user_prompt,
            "context": context_data or {},
        }

    def _build_sp_analysis_json_input(
        self,
        source_code: str,
        object_name: str,
        object_type: str,
        stats: Dict[str, Any],
        missing_indexes: list,
        dependencies: list,
        query_store: Dict[str, Any],
        plan_xml: str,
        plan_meta: Dict[str, Any],
        plan_insights: Dict[str, Any],
        existing_indexes: list,
        parameter_sniffing: Dict[str, Any],
        historical_trend: Dict[str, Any],
        memory_grants: Dict[str, Any],
        completeness: Dict[str, Any],
        context_warning: str,
        index_recommendation_gate: Dict[str, Any],
        object_resolution: Dict[str, Any],
        plan_signal_summary: Dict[str, Any],
        environment_policy: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare structured SP analysis input with safe truncation limits."""
        compact_query_store = self._compact_query_store(query_store or {})
        compact_existing_indexes = self._compact_existing_indexes(existing_indexes or [])
        index_dataset_v2 = build_index_analysis_dataset_v2(
            object_name=object_name,
            existing_indexes=compact_existing_indexes,
            missing_indexes=(missing_indexes or [])[:10],
            plan_missing_indexes=(plan_signal_summary or {}).get("mi_columns_signature", [])[:10],
            query_store=compact_query_store,
            sql_version=self._get_sql_version_string(),
            policy_gate=index_recommendation_gate or {},
        )
        return {
            "object_name": object_name,
            "object_type": object_type,
            "source_code": self._truncate_text(source_code, 6000),
            "execution_stats": stats or {},
            "missing_indexes": (missing_indexes or [])[:5],
            "dependencies": (dependencies or [])[:20],
            "query_store": compact_query_store,
            "plan_meta": plan_meta or {},
            "plan_insights": plan_insights or {},
            "existing_indexes": compact_existing_indexes,
            "index_analysis_dataset_v2": index_dataset_v2,
            "index_pre_analysis": index_dataset_v2.get("pre_analysis", {}),
            "parameter_sniffing": parameter_sniffing or {},
            "historical_trend": historical_trend or {},
            "memory_grants": memory_grants or {},
            "plan_xml": self._truncate_text(plan_xml, 6000),
            "completeness": completeness or {},
            "object_resolution": object_resolution or {},
            "plan_signal_summary": plan_signal_summary or {},
            "environment_policy": environment_policy or {},
            "context_warning": context_warning or "",
            "index_recommendation_gate": index_recommendation_gate or {},
            "missing_data_hints": (index_recommendation_gate or {}).get("missing_data_hints", []),
        }

    @staticmethod
    def _calculate_read_write_ratio(reads: float, writes: float) -> float:
        return float(reads) if writes == 0 else float(reads) / float(writes)

    def _evaluate_index_coverage_and_usage(
        self,
        existing_indexes: Any,
        object_resolution: Optional[Dict[str, Any]] = None,
        sargability_flags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Mandatory gate for index recommendations:
        requires existing index coverage + dm_db_index_usage_stats usage metrics.
        """
        normalized: list = []

        if isinstance(existing_indexes, list):
            for entry in existing_indexes:
                if not isinstance(entry, dict):
                    continue

                # Collector format: {table, indexes:[{seeks, scans, lookups, ...}]}
                indexes = entry.get("indexes")
                if isinstance(indexes, list):
                    table_name = str(entry.get("table", "") or "")
                    for idx in indexes:
                        if isinstance(idx, dict):
                            row = dict(idx)
                            row["_table"] = table_name
                            normalized.append(row)
                    continue

                # Deterministic format from index analyzer output.
                metrics = entry.get("Metrics")
                if isinstance(metrics, dict):
                    row = {
                        "_table": str(entry.get("TableName", "") or ""),
                        "name": entry.get("IndexName", ""),
                        "seeks": metrics.get("UserSeeks", 0),
                        "scans": metrics.get("UserScans", 0),
                        "lookups": entry.get("Internal", {}).get("UserLookups", 0) if isinstance(entry.get("Internal"), dict) else 0,
                        "user_updates": metrics.get("UserUpdates", 0),
                    }
                    normalized.append(row)
                    continue

                # Flat fallback format.
                normalized.append(entry)

        total_indexes = len(normalized)
        tables = {str(i.get("_table", "") or "") for i in normalized if i.get("_table")}
        usage_covered = 0
        ratio_values = []
        reads_positive = 0
        physical_covered = 0
        stats_covered = 0
        has_window_delta = 0
        baseline_14d_covered = 0
        reliable_window_count = 0
        low_reliability_count = 0
        usage_window_warning_count = 0

        for idx in normalized:
            seeks = float(idx.get("seeks", idx.get("user_seeks", 0)) or 0)
            scans = float(idx.get("scans", idx.get("user_scans", 0)) or 0)
            lookups = float(idx.get("lookups", idx.get("user_lookups", 0)) or 0)
            updates = float(idx.get("user_updates", idx.get("updates", 0)) or 0)
            reads = seeks + scans + lookups
            ratio = self._calculate_read_write_ratio(reads, updates)
            has_usage = any(k in idx for k in ("seeks", "scans", "lookups", "user_seeks", "user_scans", "user_lookups"))

            if has_usage:
                usage_covered += 1
                ratio_values.append(ratio)
            if reads > 0:
                reads_positive += 1
            if any(k in idx for k in ("avg_fragmentation_in_percent", "page_count", "fragment_count")):
                physical_covered += 1
            if any(k in idx for k in ("modification_counter", "days_since_last_stats_update", "modification_ratio")):
                stats_covered += 1
            if isinstance(idx.get("usage_window"), dict) and idx.get("reads") is not None and idx.get("writes") is not None:
                has_window_delta += 1
                usage_window = idx.get("usage_window", {})
                days_tracked = float(usage_window.get("days_tracked", 0) or 0)
                baseline_ok = bool(usage_window.get("baseline_14d_ok", days_tracked >= 14.0))
                if baseline_ok:
                    baseline_14d_covered += 1
                reliability_check = usage_window.get("reliability_check", {})
                if isinstance(reliability_check, dict):
                    reliability_status = str(reliability_check.get("status", "UNKNOWN") or "UNKNOWN").upper()
                    warning_codes = reliability_check.get("warning_codes", [])
                else:
                    reliability_status = "UNKNOWN"
                    warning_codes = usage_window.get("warnings", [])
                if reliability_status in {"HIGH", "MEDIUM"}:
                    reliable_window_count += 1
                if reliability_status == "LOW":
                    low_reliability_count += 1
                if isinstance(warning_codes, list):
                    usage_window_warning_count += len(warning_codes)

        avg_ratio = (sum(ratio_values) / len(ratio_values)) if ratio_values else 0.0
        missing_hints: List[str] = []
        reason = ""
        object_ok = bool((object_resolution or {}).get("object_resolved", True))
        risky_flags = {
            "leading_wildcard",
            "function_on_column",
            "implicit_convert",
            "RBAR",
        }
        detected_flags = [f for f in (sargability_flags or []) if str(f) in risky_flags]

        allowed = True
        if not object_ok:
            allowed = False
            reason = "object_not_resolved"
            missing_hints.append("object_resolution(object_resolved=true, object_id)")
        if total_indexes == 0:
            allowed = False
            reason = reason or "existing_index_coverage_missing"
            missing_hints.append("existing_indexes(PK/UK/CI/NCI + key/include/filter)")
        elif usage_covered == 0:
            allowed = False
            reason = reason or "dm_db_index_usage_stats_missing"
            missing_hints.append("dm_db_index_usage_stats(14d delta)")
        if has_window_delta == 0:
            allowed = False
            reason = reason or "usage_window_delta_missing"
            missing_hints.append("usage_window(daily_read_rate,daily_write_rate,utilization_rate)")
        elif baseline_14d_covered == 0:
            allowed = False
            reason = reason or "usage_window_baseline_14d_missing"
            missing_hints.append("usage_window(14d baseline mandatory)")
        elif baseline_14d_covered < has_window_delta:
            allowed = False
            reason = reason or "usage_window_baseline_14d_incomplete"
            missing_hints.append("usage_window(14d baseline for all tracked indexes)")
        if has_window_delta > 0 and reliable_window_count == 0:
            allowed = False
            reason = reason or "usage_window_reliability_low"
            missing_hints.append("usage_window_reliability(reliability_check.status>=MEDIUM)")
        if physical_covered == 0:
            allowed = False
            reason = reason or "physical_stats_missing"
            missing_hints.append("physical_stats(LIMITED: frag_percent,page_count,page_density_percent)")
        if stats_covered == 0:
            allowed = False
            reason = reason or "stats_properties_missing"
            missing_hints.append("stats_properties(last_updated_age,modification_ratio)")
        if detected_flags:
            allowed = False
            reason = reason or "sargability_block"
            missing_hints.append("fix_sargability(leading_wildcard/function_on_column/implicit_convert/RBAR)")
            missing_hints.append("plan_signal_normalization(mi_columns_signature)")

        # Keep order while removing duplicates.
        seen_hints = set()
        dedup_hints: List[str] = []
        for h in missing_hints:
            if h in seen_hints:
                continue
            seen_hints.add(h)
            dedup_hints.append(h)

        return {
            "allowed": allowed,
            "reason": reason,
            "validation_source": "sys.dm_db_index_usage_stats",
            "table_count": len(tables),
            "index_count": total_indexes,
            "usage_covered_index_count": usage_covered,
            "active_read_index_count": reads_positive,
            "physical_covered_index_count": physical_covered,
            "stats_covered_index_count": stats_covered,
            "window_delta_index_count": has_window_delta,
            "baseline_14d_covered_index_count": baseline_14d_covered,
            "reliable_window_index_count": reliable_window_count,
            "low_reliability_index_count": low_reliability_count,
            "usage_window_warning_count": usage_window_warning_count,
            "missing_data_hints": dedup_hints,
            "sargability_flags": sargability_flags or [],
            "average_read_write_ratio": round(avg_ratio, 3),
        }

    @staticmethod
    def _enforce_no_index_recommendations(response: str, gate: Dict[str, Any]) -> str:
        """Hard-enforce index recommendation block when validation gate is not satisfied."""
        if not response:
            return response

        blocked_terms = (
            "create index",
            "drop index",
            "alter index",
            "missing index",
            "index suggestion",
            "index recommendation",
        )
        removed = 0
        filtered_lines = []
        for line in response.splitlines():
            low = line.lower()
            if any(term in low for term in blocked_terms):
                removed += 1
                continue
            filtered_lines.append(line)

        filtered_lines.append("")
        filtered_lines.append("---")
        filtered_lines.append(
            "⚠️ **Index Recommendation Gate:** Existing index coverage + usage validation "
            "(dm_db_index_usage_stats) is incomplete, so index recommendations were suppressed."
        )
        filtered_lines.append(f"- Validation status: {gate.get('reason', 'blocked')}")
        filtered_lines.append(f"- Covered indexes: {gate.get('usage_covered_index_count', 0)}/{gate.get('index_count', 0)}")
        hints = gate.get("missing_data_hints", [])
        if isinstance(hints, list) and hints:
            filtered_lines.append("- Missing data hints:")
            for hint in hints:
                filtered_lines.append(f"  - {hint}")
        if removed > 0:
            filtered_lines.append(f"- Suppressed lines: {removed}")
        return "\n".join(filtered_lines)
    
    def _run_self_reflection(
        self, 
        ai_response: str, 
        context: Dict[str, Any]
    ) -> AnalysisConfidence:
        """Run self-reflection engine on AI response"""
        try:
            engine = SelfReflectionEngine(context)
            confidence = engine.analyze(ai_response)
            logger.info(
                f"Self-reflection complete: {confidence.percentage}% confidence, "
                f"level={confidence.level.value}, deep_recommended={confidence.deep_analysis_recommended}"
            )
            return confidence
        except Exception as e:
            logger.warning(f"Self-reflection failed: {e}")
            # Return neutral confidence on failure
            return AnalysisConfidence(
                overall_score=0.5,
                level=ConfidenceLevel.MEDIUM,
                summary="Confidence calculation unavailable",
            )

    def _should_run_self_reflection_refinement(
        self,
        confidence: Optional[AnalysisConfidence],
        deep_analysis: bool,
    ) -> bool:
        """Decide whether a second LLM refinement pass should run."""
        if deep_analysis:
            return False
        if not self.SELF_REFLECTION_RETRY_ENABLED:
            return False
        if confidence is None:
            return False
        return (
            float(confidence.overall_score) < float(self.SELF_REFLECTION_RETRY_MIN_SCORE)
            or int(confidence.failed_validations) >= int(self.SELF_REFLECTION_RETRY_MIN_FAILED_VALIDATIONS)
        )

    def _is_refinement_improved(
        self,
        base_confidence: AnalysisConfidence,
        refined_confidence: AnalysisConfidence,
    ) -> bool:
        """Accept refinement only when confidence meaningfully improves."""
        if refined_confidence.overall_score >= (
            base_confidence.overall_score + self.SELF_REFLECTION_RETRY_MIN_IMPROVEMENT
        ):
            return True
        if refined_confidence.failed_validations < base_confidence.failed_validations:
            return True
        return False

    async def _run_self_reflection_refinement_pass(
        self,
        previous_response: str,
        confidence: AnalysisConfidence,
        system_prompt: str,
        object_name: str,
        object_type: str,
        analyzer_profile: Any,
    ) -> str:
        """
        Run a second-pass refinement focused on self-reflection findings.
        Returns empty string if refinement fails.
        """
        try:
            warnings = confidence.warnings[:5] if isinstance(confidence.warnings, list) else []
            warning_text = "\n".join(f"- {w}" for w in warnings) if warnings else "- No explicit warning text was produced."
            instruction_prompt = (
                "Refine the previous report to improve reliability.\n"
                "Address validation warnings directly, remove speculative claims, and keep evidence-grounded statements only.\n"
                "Preserve the requested structure and output in English.\n"
            )
            refinement_payload = self._build_json_user_prompt(
                request_type=f"{getattr(analyzer_profile, 'request_type', 'object_performance_analysis')}_self_reflection_refinement",
                metadata={
                    "object_name": object_name,
                    "object_type": object_type,
                    "phase": "self_reflection_refinement",
                    "base_confidence_pct": confidence.percentage,
                },
                instruction_prompt=instruction_prompt,
                input_data={
                    "object_name": object_name,
                    "object_type": object_type,
                    "base_confidence": confidence.to_display_dict(),
                    "validation_warnings": warnings,
                    "previous_response": previous_response,
                    "self_reflection_findings": warning_text,
                },
                output_contract={
                    "format": "markdown",
                    "sections": list(getattr(analyzer_profile, "sections", []) or []),
                    "section_requirements": dict(getattr(analyzer_profile, "section_requirements", {}) or {}),
                },
            )
            return await self.llm_client.generate(
                prompt=refinement_payload,
                system_prompt=system_prompt,
                provider_id=self.provider_id,
                temperature=0.05,
            )
        except Exception as e:
            logger.warning(f"Self-reflection refinement pass failed: {e}")
            return ""
    
    def get_last_confidence(self) -> Optional[AnalysisConfidence]:
        """Get the confidence from the last analysis"""
        return self._last_confidence

    def get_last_request_payload(self) -> Optional[Dict[str, Any]]:
        """Get the latest request payload sent to LLM."""
        return self._last_request_payload

    def get_last_request_file_path(self) -> Optional[str]:
        """Get the latest persisted request file path."""
        return self._last_request_file_path

    async def optimize_object(
        self,
        source_code: str,
        object_name: str,
        object_type: str = "",
        database_name: str = "",
        object_resolution: Dict[str, Any] = None,
        stats: Dict[str, Any] = None,
        missing_indexes: list = None,
        dependencies: list = None,
        query_store: Dict[str, Any] = None,
        plan_xml: str = None,
        plan_meta: Dict[str, Any] = None,
        plan_insights: Dict[str, Any] = None,           # NEW
        existing_indexes: list = None,                  # NEW
        parameter_sniffing: Dict[str, Any] = None,      # NEW
        historical_trend: Dict[str, Any] = None,        # NEW
        memory_grants: Dict[str, Any] = None,           # NEW
        streaming: bool = False,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Generate optimized SQL code for a database object (SQL output only)."""
        try:
            self._last_request_payload = None
            self._last_request_file_path = None
            normalized_object_type = self._resolve_object_type_for_analysis(
                object_type=object_type,
                object_resolution=object_resolution,
            )
            analyzer = create_object_analyzer_for_type(normalized_object_type)
            requires_index_policy = bool(getattr(analyzer, "requires_index_policy", False))
            logger.info(f"Starting object optimization for {object_name} (type: {normalized_object_type})")

            missing_indexes_anon = self._anonymize_missing_indexes(missing_indexes)
            existing_indexes_anon = self._anonymize_existing_indexes(existing_indexes)
            plan_signal_summary = self._build_plan_signal_summary(
                source_code=source_code,
                plan_insights=plan_insights or {},
                query_store=query_store or {},
            )
            index_gate: Dict[str, Any] = {
                "allowed": True,
                "coverage_ratio": 0.0,
                "usage_coverage_ratio": 0.0,
                "usage_window_days": 14,
                "missing_data_hints": [],
                "policy_reason": "index_policy_not_required_for_object_type",
            }
            if requires_index_policy:
                index_gate = self._evaluate_index_coverage_and_usage(
                    existing_indexes=existing_indexes_anon,
                    object_resolution=object_resolution,
                    sargability_flags=plan_signal_summary.get("sargability_flags", []),
                )
            environment_policy = self._collect_environment_policy_context(database_name)
            if not isinstance(object_resolution, dict):
                object_resolution = {"object_resolved": True, "object_id": None}
            object_resolution = dict(object_resolution)
            if "object_type" not in object_resolution:
                object_resolution["object_type"] = normalized_object_type

            system_prompt, user_prompt = AdvancedPromptBuilder.build_sp_code_prompt(
                source_code=source_code,
                object_name=object_name,
                stats=stats,
                missing_indexes=missing_indexes_anon,
                dependencies=dependencies,
                query_store=query_store,
                plan_xml=plan_xml,
                plan_meta=plan_meta,
                plan_insights=plan_insights,
                existing_indexes=existing_indexes_anon,
                parameter_sniffing=parameter_sniffing,
                historical_trend=historical_trend,
                memory_grants=memory_grants,
                context=PromptContext(sql_version=self._get_sql_version_string())
            )
            analyzer_profile = analyzer.build_profile(
                index_gate=index_gate,
                environment_policy=environment_policy,
            )
            for block in analyzer_profile.prompt_blocks:
                block_text = str(block or "").strip()
                if block_text:
                    user_prompt += f"\n\n{block_text}"

            optimize_index_dataset = build_index_analysis_dataset_v2(
                object_name=object_name,
                existing_indexes=self._compact_existing_indexes(existing_indexes_anon or []),
                missing_indexes=(missing_indexes_anon or [])[:10],
                plan_missing_indexes=(plan_signal_summary or {}).get("mi_columns_signature", [])[:10],
                query_store=self._compact_query_store(query_store or {}),
                sql_version=self._get_sql_version_string(),
                policy_gate=index_gate,
            )

            optimize_context = {
                "object_name": object_name,
                "object_type": normalized_object_type,
                "stats": stats,
                "missing_indexes": (missing_indexes_anon or [])[:5],
                "dependencies": (dependencies or [])[:20],
                "query_store": self._compact_query_store(query_store or {}),
                "plan_meta": plan_meta or {},
                "plan_insights": plan_insights or {},
                "existing_indexes": self._compact_existing_indexes(existing_indexes_anon or []),
                "index_analysis_dataset_v2": optimize_index_dataset,
                "index_pre_analysis": optimize_index_dataset.get("pre_analysis", {}),
                "parameter_sniffing": parameter_sniffing or {},
                "historical_trend": historical_trend or {},
                "memory_grants": memory_grants or {},
                "object_resolution": object_resolution or {},
                "plan_signal_summary": plan_signal_summary or {},
                "environment_policy": environment_policy or {},
                "source_code": self._truncate_text(source_code, 6000),
                "plan_xml": self._truncate_text(plan_xml, 6000),
            }

            llm_json_prompt = self._build_json_user_prompt(
                request_type=str(analyzer_profile.request_type).replace("_performance_analysis", "_code_optimization"),
                metadata={
                    "object_name": object_name,
                    "object_type": normalized_object_type,
                    "sql_version": self._get_sql_version_string(),
                },
                instruction_prompt=(
                    user_prompt
                    + "\n\n### RESPONSE LANGUAGE\n"
                    + "- Return SQL only.\n"
                    + "- If comments are included, comments must be in English.\n"
                ),
                input_data=optimize_context,
                output_contract={
                    "format": "sql",
                    "rules": [
                        "Return only SQL",
                        "Do not use markdown code fences",
                        "Keep full, executable procedure script",
                    ],
                },
            )

            self._log_analysis_request(
                query_id=None,
                query_name=f"{object_name}_code_only",
                system_prompt=system_prompt,
                user_prompt=llm_json_prompt,
                context_data=optimize_context,
            )

            if streaming:
                response = await self.llm_client.generate_streaming(
                    prompt=llm_json_prompt,
                    system_prompt=system_prompt,
                    provider_id=self.provider_id,
                    temperature=0.1,
                    on_chunk=on_chunk,
                )
            else:
                response = await self.llm_client.generate(
                    prompt=llm_json_prompt,
                    system_prompt=system_prompt,
                    provider_id=self.provider_id,
                    temperature=0.1,
                )

            response = self._strip_code_fences(response)
            response = await self._continue_sql_if_truncated(
                sql=response,
                system_prompt=system_prompt,
            )
            self._log_analysis_result(
                query_id=None,
                query_name=f"{object_name}_code_only",
                response=response,
            )
            return response

        except Exception as e:
            logger.error(f"Object optimization failed: {e}")
            return f"⚠️ An error occurred during analysis: {str(e)}"

    async def optimize_sp(
        self,
        source_code: str,
        object_name: str,
        object_type: str = "",
        database_name: str = "",
        object_resolution: Dict[str, Any] = None,
        stats: Dict[str, Any] = None,
        missing_indexes: list = None,
        dependencies: list = None,
        query_store: Dict[str, Any] = None,
        plan_xml: str = None,
        plan_meta: Dict[str, Any] = None,
        plan_insights: Dict[str, Any] = None,
        existing_indexes: list = None,
        parameter_sniffing: Dict[str, Any] = None,
        historical_trend: Dict[str, Any] = None,
        memory_grants: Dict[str, Any] = None,
        streaming: bool = False,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Backward-compatible wrapper. Use optimize_object() for new call sites.
        """
        return await self.optimize_object(
            source_code=source_code,
            object_name=object_name,
            object_type=object_type,
            database_name=database_name,
            object_resolution=object_resolution,
            stats=stats,
            missing_indexes=missing_indexes,
            dependencies=dependencies,
            query_store=query_store,
            plan_xml=plan_xml,
            plan_meta=plan_meta,
            plan_insights=plan_insights,
            existing_indexes=existing_indexes,
            parameter_sniffing=parameter_sniffing,
            historical_trend=historical_trend,
            memory_grants=memory_grants,
            streaming=streaming,
            on_chunk=on_chunk,
        )
    
    async def get_index_recommendations(
        self,
        query_text: str,
        table_info: Dict[str, Any],
        missing_index_dmv: Dict[str, Any] = None,
        existing_indexes: list = None
    ) -> str:
        """
        Index önerisi al
        """
        try:
            index_gate = self._evaluate_index_coverage_and_usage(existing_indexes)
            if not index_gate.get("allowed", False):
                hints = index_gate.get("missing_data_hints", [])
                hints_text = ""
                if isinstance(hints, list) and hints:
                    hints_text = "\n- Missing data hints: " + ", ".join(str(h) for h in hints)
                return (
                    "⚠️ Index recommendation generation blocked.\n\n"
                    "No recommendation was generated because existing index coverage + usage validation "
                    "(sys.dm_db_index_usage_stats) is mandatory and currently incomplete.\n\n"
                    f"- Reason: {index_gate.get('reason', 'blocked')}\n"
                    f"- Covered indexes: {index_gate.get('usage_covered_index_count', 0)}/"
                    f"{index_gate.get('index_count', 0)}"
                    f"{hints_text}"
                )

            system_prompt, user_prompt = AdvancedPromptBuilder.build_index_recommendation_prompt(
                query_text=query_text,
                table_info=table_info,
                missing_index_dmv=missing_index_dmv,
                existing_indexes=existing_indexes,
                context=PromptContext(sql_version=self._get_sql_version_string())
            )
            user_prompt += (
                "\n\n### MANDATORY VALIDATION RULE\n"
                "- Generate index recommendation only after validating existing index coverage and usage "
                "from dm_db_index_usage_stats.\n"
                "- Include this validation result in rationale.\n"
            )

            llm_json_prompt = self._build_json_user_prompt(
                request_type="index_recommendation",
                metadata={
                    "sql_version": self._get_sql_version_string(),
                    "index_recommendation_gate": index_gate,
                },
                instruction_prompt=user_prompt,
                input_data={
                    "query_text": self._truncate_text(query_text, 6000),
                    "table_info": table_info or {},
                    "missing_index_dmv": missing_index_dmv or {},
                    "existing_indexes": self._compact_existing_indexes(existing_indexes or []),
                    "index_recommendation_gate": index_gate,
                },
                output_contract={
                    "format": "markdown_or_sql",
                    "goal": "index_recommendations",
                },
            )
            
            response = await self.llm_client.generate(
                prompt=llm_json_prompt,
                system_prompt=system_prompt,
                provider_id=self.provider_id,
                temperature=0.1,
            )
            
            # Validate index syntax
            validation = self.response_validator.validate(response)
            return validation.sanitized_response
            
        except Exception as e:
            logger.error(f"Index recommendation failed: {e}")
            return f"⚠️ Failed to get index recommendations: {str(e)}"
    
    def analyze_plan_only(self, plan_xml: str) -> PlanInsights:
        """
        Sadece execution plan analizi (AI olmadan)
        """
        return self.plan_analyzer.analyze(plan_xml)

    def _get_sql_version_string(self) -> str:
        conn = get_connection_manager().active_connection
        if not conn or not conn.info:
            return ""
        info = conn.info
        friendly = SQL_SERVER_VERSIONS.get(info.major_version, f"SQL Server (v{info.major_version})")
        parts = []
        if info.product_version:
            parts.append(info.product_version)
        if info.edition:
            parts.append(info.edition)
        if info.is_azure:
            parts.append("Azure")
        if parts:
            return f"{friendly} ({', '.join(parts)})"
        return friendly

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove markdown code fences from a response."""
        if not text:
            return text
        cleaned = text.strip()
        if cleaned.startswith("```sql"):
            cleaned = cleaned[6:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    def _is_sql_complete(self, sql: str) -> bool:
        """Heuristic check for complete SQL procedure output."""
        if not sql:
            return True
        for line in reversed(sql.splitlines()):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("--"):
                continue
            upper = stripped.upper()
            if upper == "GO" or upper.endswith("GO"):
                return True
            if upper.endswith("END") or upper.endswith("END;"):
                return True
            return False
        return False

    def _has_unclosed_code_fence(self, text: str) -> bool:
        return text.count("```") % 2 == 1

    def _extract_tail_sql(self, text: str) -> str:
        upper = text.upper()
        idx = max(upper.rfind("ALTER PROCEDURE"), upper.rfind("CREATE PROCEDURE"))
        if idx == -1:
            return ""
        return text[idx:]

    async def _continue_sql_if_truncated(
        self,
        sql: str,
        system_prompt: str,
        max_rounds: int = 2,
    ) -> str:
        if self._is_sql_complete(sql):
            return sql
        assembled = sql.strip()
        for round_idx in range(max_rounds):
            tail = assembled[-800:] if len(assembled) > 800 else assembled
            continuation_prompt = self._build_json_user_prompt(
                request_type="sql_continuation",
                metadata={
                    "round": round_idx + 1,
                    "max_rounds": max_rounds,
                },
                instruction_prompt=(
                    "The SQL was truncated. Continue from the exact point it stopped. "
                    "Do not repeat any previous lines."
                ),
                input_data={
                    "last_part": tail,
                },
                output_contract={
                    "format": "sql",
                    "rules": [
                        "Return only SQL",
                        "Do not use markdown code fences",
                    ],
                },
            )
            cont = await self.llm_client.generate(
                prompt=continuation_prompt,
                system_prompt=system_prompt,
                provider_id=self.provider_id,
                temperature=0.1,
            )
            cont = self._strip_code_fences(cont).strip()
            if not cont:
                break
            assembled = assembled.rstrip() + "\n" + cont.lstrip()
            if self._is_sql_complete(assembled):
                break
        return assembled

    async def _continue_report_if_truncated(
        self,
        response: str,
        system_prompt: str,
        max_rounds: int = 2,
    ) -> str:
        if not response:
            return response
        tail_sql = self._extract_tail_sql(response)
        needs_continuation = self._has_unclosed_code_fence(response)
        if tail_sql and not self._is_sql_complete(tail_sql):
            needs_continuation = True
        if not needs_continuation:
            return response
        assembled = response.strip()
        for round_idx in range(max_rounds):
            tail = assembled[-800:] if len(assembled) > 800 else assembled
            continuation_prompt = self._build_json_user_prompt(
                request_type="report_continuation",
                metadata={
                    "round": round_idx + 1,
                    "max_rounds": max_rounds,
                },
                instruction_prompt=(
                    "The report was truncated. Continue from the exact point it stopped. "
                    "Do not repeat any previous lines. Preserve the same language and markdown."
                ),
                input_data={
                    "last_part": tail,
                },
                output_contract={
                    "format": "markdown",
                    "rules": [
                        "Continue from exact stop point",
                        "Preserve language and structure",
                    ],
                },
            )
            cont = await self.llm_client.generate(
                prompt=continuation_prompt,
                system_prompt=system_prompt,
                provider_id=self.provider_id,
                temperature=0.1,
            )
            cont = cont.strip()
            if not cont:
                break
            assembled = assembled.rstrip() + "\n" + cont.lstrip()
            tail_sql = self._extract_tail_sql(assembled)
            if not self._has_unclosed_code_fence(assembled) and (
                not tail_sql or self._is_sql_complete(tail_sql)
            ):
                break
        return assembled

    def _log_analysis_request(
        self,
        query_id: Optional[int],
        query_name: str,
        system_prompt: str,
        user_prompt: str,
        context_data: Dict[str, Any],
    ) -> None:
        """Persist analysis request payload for audit/debug."""
        try:
            ensure_app_dirs()
            settings = get_settings()
            logs_dir = Path(settings.logs_dir) / "ai_reports"
            logs_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in query_name)[:60]
            file_path = logs_dir / f"ai_request_{safe_name}_{query_id}_{timestamp}.json"

            payload = self._build_export_request_payload(
                query_id=query_id,
                query_name=query_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context_data=context_data,
                cache_hit=False,
                llm_request_performed=True,
            )
            self._last_request_payload = payload
            self._last_request_file_path = str(file_path)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to log AI request: {e}")

    def _log_analysis_result(
        self,
        query_id: Optional[int],
        query_name: str,
        response: str,
    ) -> None:
        """Persist analysis response for audit/debug."""
        try:
            ensure_app_dirs()
            settings = get_settings()
            logs_dir = Path(settings.logs_dir) / "ai_reports"
            logs_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in query_name)[:60]
            file_path = logs_dir / f"ai_response_{safe_name}_{query_id}_{timestamp}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(response)
        except Exception as e:
            logger.warning(f"Failed to log AI response: {e}")

    @staticmethod
    def _to_num(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _fmt_float(value: Any, decimals: int = 1) -> str:
        try:
            return f"{float(value):.{decimals}f}"
        except Exception:
            return f"{0.0:.{decimals}f}"

    @staticmethod
    def _fmt_int(value: Any) -> str:
        try:
            return f"{int(float(value)):,}"
        except Exception:
            return "0"

    @staticmethod
    def _estimate_expected_improvement_range(
        *,
        combined_class: str,
        trend_direction: str,
        gate_allowed: bool,
        critical_query_count: int,
        poor_query_count: int,
        high_risk_index_count: int,
    ) -> tuple[int, int]:
        base = {
            "CRITICAL_QUERY_ISSUE": (35, 60),
            "POOR_QUERY_DESIGN": (22, 42),
            "INDEX_CENTRIC_RISK": (15, 30),
            "BALANCED_QUERY_AND_INDEX": (8, 18),
        }
        low, high = base.get(str(combined_class or "").upper(), (10, 25))

        trend = str(trend_direction or "").strip().lower()
        if trend == "degrading":
            low += 5
            high += 8
        elif trend == "improving":
            low = max(5, low - 3)
            high = max(10, high - 5)

        if critical_query_count > 0:
            low += 5
            high += 5
        elif poor_query_count > 0:
            low += 2
            high += 3

        if high_risk_index_count >= 3:
            low += 2
            high += 4

        if not gate_allowed:
            low = max(5, low - 5)
            high = max(low + 2, high - 8)

        low = max(5, min(low, 70))
        high = max(low + 2, min(high, 80))
        return int(low), int(high)

    def _build_auto_executive_summary_markdown(
        self,
        *,
        object_name: str,
        stats: Dict[str, Any],
        historical_trend: Dict[str, Any],
        index_pre_analysis: Dict[str, Any],
        plan_signal_summary: Dict[str, Any],
        index_recommendation_gate: Dict[str, Any],
    ) -> str:
        pre = index_pre_analysis if isinstance(index_pre_analysis, dict) else {}
        combined = pre.get("query_index_combined_classification", {})
        if not isinstance(combined, dict):
            combined = {}
        cls = pre.get("classification_system", {})
        if not isinstance(cls, dict):
            cls = {}
        cls_counts = cls.get("counts", {}) if isinstance(cls.get("counts", {}), dict) else {}

        baseline_duration = self._to_num(stats.get("avg_duration_ms"), 0.0)
        baseline_cpu = self._to_num(stats.get("avg_cpu_ms"), 0.0)
        baseline_reads = self._to_num(stats.get("avg_logical_reads"), 0.0)
        execution_count = self._fmt_int(stats.get("execution_count", 0))

        trend = historical_trend if isinstance(historical_trend, dict) else {}
        trend_dir = str(trend.get("trend_direction", "stable") or "stable")
        dur_delta = trend.get("duration_change_percent")
        cpu_delta = trend.get("cpu_change_percent")
        reads_delta = trend.get("reads_change_percent")
        def _fmt_delta(value: Any) -> str:
            return "N/A" if value is None else f"{self._fmt_float(value)}"

        gate_allowed = bool((index_recommendation_gate or {}).get("allowed", False))
        combined_class = str(combined.get("overall_class", "BALANCED_QUERY_AND_INDEX") or "BALANCED_QUERY_AND_INDEX")
        critical_query_count = int(self._to_num(cls_counts.get("CRITICAL_QUERY_ISSUE"), 0))
        poor_query_count = int(self._to_num(cls_counts.get("POOR_QUERY_DESIGN"), 0))
        summary_counts = pre.get("summary", {}) if isinstance(pre.get("summary", {}), dict) else {}
        high_risk_index_count = int(self._to_num(summary_counts.get("high_risk_index_count"), 0))
        low_improve, high_improve = self._estimate_expected_improvement_range(
            combined_class=combined_class,
            trend_direction=trend_dir,
            gate_allowed=gate_allowed,
            critical_query_count=critical_query_count,
            poor_query_count=poor_query_count,
            high_risk_index_count=high_risk_index_count,
        )

        if baseline_duration > 0:
            target_fast = baseline_duration * (1.0 - (high_improve / 100.0))
            target_conservative = baseline_duration * (1.0 - (low_improve / 100.0))
            duration_target_text = (
                f"from {self._fmt_float(baseline_duration)} ms to ~"
                f"{self._fmt_float(target_fast)}-{self._fmt_float(target_conservative)} ms"
            )
        else:
            duration_target_text = "with no reliable numeric duration baseline available"

        flags = plan_signal_summary.get("sargability_flags", []) if isinstance(plan_signal_summary, dict) else []
        top_signal = ", ".join(str(f) for f in flags[:3]) if flags else "no critical sargability flags captured"

        sentence1 = (
            f"Baseline performance for `{object_name}` is {self._fmt_float(baseline_duration)} ms average duration, "
            f"{self._fmt_float(baseline_cpu)} ms CPU, and {self._fmt_int(baseline_reads)} logical reads "
            f"across {execution_count} executions, with combined class `{combined_class}`."
        )
        if dur_delta is not None or cpu_delta is not None or reads_delta is not None:
            sentence2 = (
                "Performance comparison vs baseline window shows "
                f"duration {_fmt_delta(dur_delta)}%, CPU {_fmt_delta(cpu_delta)}%, "
                f"and reads {_fmt_delta(reads_delta)}%, while key query/index signals are: {top_signal}."
            )
        else:
            sentence2 = (
                "Performance comparison vs baseline window is unavailable from historical trend data, "
                f"and current primary query/index signals are: {top_signal}."
            )
        sentence3 = (
            f"Expected improvement is explicitly estimated at {low_improve}-{high_improve}% faster average duration, "
            f"{duration_target_text}, subject to validation in the post-change test plan."
        )

        return (
            f"{self.AUTO_EXECUTIVE_SUMMARY_MARKER}\n\n"
            f"{sentence1}\n\n"
            f"{sentence2}\n\n"
            f"{sentence3}"
        )

    def _ensure_auto_executive_summary(self, response: str, summary_block: str) -> str:
        if not response:
            return summary_block or response
        if not summary_block:
            return response
        if self.AUTO_EXECUTIVE_SUMMARY_MARKER.lower() in response.lower():
            return response
        return f"{summary_block}\n\n{response}"
    
    def _format_waits(self, waits: Dict[str, float]) -> str:
        """Wait profili formatla"""
        if not waits:
            return "Veri yok"
        return "\n".join([
            f"- {k.replace('_percent', '').replace('_', ' ').title()}: %{v}" 
            for k, v in sorted(waits.items(), key=lambda x: x[1], reverse=True)
        ])
