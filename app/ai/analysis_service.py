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

from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import json
from pathlib import Path
from app.ai.llm_client import get_llm_client, UnifiedLLMClient
from app.ai.prompts import AdvancedPromptBuilder, PromptType, PromptContext
from app.ai.plan_analyzer import ExecutionPlanAnalyzer, PlanInsights
from app.ai.response_validator import AIResponseValidator, ValidationResult
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
                user_prompt=user_prompt,
                context_data=context,
            )
            
            # AI'dan yanıt al (aktif veya belirtilen provider ile)
            response = await self.llm_client.generate(
                prompt=user_prompt,
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
                user_prompt=user_prompt,
                context_data=context,
            )

            response = await self.llm_client.generate(
                prompt=user_prompt,
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
    
    async def analyze_sp(
        self,
        source_code: str,
        object_name: str,
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
        skip_cache: bool = False                          # NEW: Skip cache
    ) -> Tuple[str, Optional[AnalysisConfidence]]:
        """
        Stored Procedure analizi - Advanced Performance Analysis
        
        Features:
        - Intelligent caching
        - Self-reflection with confidence scoring
        - Deep analysis mode for complex procedures
        - Graceful degradation when data is incomplete
        
        Args:
            source_code: SP kaynak kodu
            object_name: SP adı
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
            quality_level = "unknown"
            if completeness:
                quality_level = completeness.get('quality_level', 'unknown')
            logger.info(f"Starting SP analysis for {object_name} (data quality: {quality_level}, deep: {deep_analysis})")
            
            # Check cache first (unless skip_cache or deep_analysis)
            if self._cache and not skip_cache and not deep_analysis:
                cached = self._cache.get_analysis(object_name, source_code, "optimization")
                if cached:
                    logger.info(f"Cache hit for {object_name}")
                    # Re-run self-reflection on cached result
                    context = self._build_context_dict(
                        source_code, object_name, stats, missing_indexes, dependencies,
                        query_store, plan_xml, plan_meta, plan_insights, existing_indexes,
                        parameter_sniffing, historical_trend, memory_grants, completeness
                    )
                    confidence = self._run_self_reflection(cached, context)
                    return cached, confidence
            
            # Build context dict for self-reflection
            context = self._build_context_dict(
                source_code, object_name, stats, missing_indexes, dependencies,
                query_store, plan_xml, plan_meta, plan_insights, existing_indexes,
                parameter_sniffing, historical_trend, memory_grants, completeness
            )
            
            # Build prompt
            system_prompt, user_prompt = AdvancedPromptBuilder.build_sp_optimization_prompt(
                source_code=source_code,
                object_name=object_name,
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
                context=PromptContext(sql_version=self._get_sql_version_string())
            )
            
            # Add deep analysis enhancement if requested
            if deep_analysis:
                reflection_engine = SelfReflectionEngine(context)
                enhancement = reflection_engine.get_deep_analysis_prompt_enhancement()
                user_prompt = enhancement + "\n\n" + user_prompt

            self._log_analysis_request(
                query_id=None,
                query_name=object_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context_data=context,
            )
            
            response = await self.llm_client.generate(
                prompt=user_prompt,
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
            
            # Run self-reflection
            confidence = self._run_self_reflection(response, context)
            self._last_confidence = confidence
            
            # Add confidence info to response
            response += f"\n\n---\n📊 **Recommendation Quality Score:** {validation.quality_score:.0f}/100"
            response += f"\n{confidence.emoji} **Analysis Confidence:** {confidence.percentage}% ({confidence.level.value})"
            
            if confidence.warnings:
                response += "\n\n**⚠️ Doğrulama Uyarıları:**"
                for warning in confidence.warnings[:3]:
                    response += f"\n- {warning}"
            
            if confidence.deep_analysis_recommended and not deep_analysis:
                response += "\n\n💡 *Daha kapsamlı analiz için 'Deep Analysis' modu önerilir.*"
            
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
            logger.error(f"SP analysis failed: {e}")
            return f"⚠️ An error occurred during analysis: {str(e)}", None
    
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
    ) -> Dict[str, Any]:
        """Build context dictionary for self-reflection"""
        return {
            "source_code": source_code,
            "object_name": object_name,
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
        }
    
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
    
    def get_last_confidence(self) -> Optional[AnalysisConfidence]:
        """Get the confidence from the last analysis"""
        return self._last_confidence

    async def optimize_sp(
        self,
        source_code: str,
        object_name: str,
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
        memory_grants: Dict[str, Any] = None            # NEW
    ) -> str:
        """
        Stored Procedure optimize edilmiş SQL kodu üretir (sadece SQL döndürür).
        """
        try:
            logger.info(f"Starting SP optimization for {object_name}")

            system_prompt, user_prompt = AdvancedPromptBuilder.build_sp_code_prompt(
                source_code=source_code,
                object_name=object_name,
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
                context=PromptContext(sql_version=self._get_sql_version_string())
            )

            self._log_analysis_request(
                query_id=None,
                query_name=f"{object_name}_code_only",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                context_data={
                    "object_name": object_name,
                    "stats": stats,
                    "missing_indexes": missing_indexes,
                    "dependencies": dependencies,
                    "query_store": query_store,
                    "plan_meta": plan_meta,
                    "plan_insights": plan_insights,
                    "existing_indexes": existing_indexes,
                    "parameter_sniffing": parameter_sniffing,
                    "historical_trend": historical_trend,
                    "memory_grants": memory_grants,
                },
            )

            response = await self.llm_client.generate(
                prompt=user_prompt,
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
            logger.error(f"SP optimization failed: {e}")
            return f"⚠️ An error occurred during analysis: {str(e)}"
    
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
            system_prompt, user_prompt = AdvancedPromptBuilder.build_index_recommendation_prompt(
                query_text=query_text,
                table_info=table_info,
                missing_index_dmv=missing_index_dmv,
                existing_indexes=existing_indexes,
                context=PromptContext(sql_version=self._get_sql_version_string())
            )
            
            response = await self.llm_client.generate(
                prompt=user_prompt,
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
        for _ in range(max_rounds):
            tail = assembled[-800:] if len(assembled) > 800 else assembled
            continuation_prompt = (
                "The SQL was truncated. Continue from the exact point it stopped. "
                "Do not repeat any previous lines. Return only SQL.\n\n"
                f"Last part:\n{tail}"
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
        for _ in range(max_rounds):
            tail = assembled[-800:] if len(assembled) > 800 else assembled
            continuation_prompt = (
                "The report was truncated. Continue from the exact point it stopped. "
                "Do not repeat any previous lines. Preserve the same language and markdown.\n\n"
                f"Last part:\n{tail}"
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

            payload = {
                "timestamp": timestamp,
                "query_id": query_id,
                "query_name": query_name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "context": context_data,
            }
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
    
    def _format_waits(self, waits: Dict[str, float]) -> str:
        """Wait profili formatla"""
        if not waits:
            return "Veri yok"
        return "\n".join([
            f"- {k.replace('_percent', '').replace('_', ' ').title()}: %{v}" 
            for k, v in sorted(waits.items(), key=lambda x: x[1], reverse=True)
        ])
