"""
AI Chat Service - Conversational database assistant
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime

from app.ai.intent_detector import get_intent_detector, Intent, IntentMatch
from app.ai.ollama_client import OllamaClient
from app.database.connection import get_connection_manager
from app.core.config import get_settings
from app.core.logger import get_logger
from app.core.constants import SQL_SERVER_VERSIONS

logger = get_logger('ai.chat')


@dataclass
class ChatContext:
    """Context for chat conversation"""
    server_name: str = ""
    database_name: str = ""
    sql_version: str = ""
    last_intent: Optional[Intent] = None
    last_query_result: Optional[List[Dict]] = None


class AIChatService:
    """
    AI-powered chat service for database assistance
    """
    
    _instance: Optional['AIChatService'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._intent_detector = get_intent_detector()
        self._ollama = OllamaClient()
        self._context = ChatContext()
        self._initialized = True
    
    @property
    def connection(self):
        """Get active database connection"""
        conn_mgr = get_connection_manager()
        return conn_mgr.active_connection
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to database"""
        conn = self.connection
        return conn is not None and conn.is_connected
    
    def update_context(self):
        """Update chat context with current connection info"""
        if self.is_connected:
            conn = self.connection
            self._context.server_name = conn.profile.server
            self._context.database_name = conn.profile.database
            self._context.sql_version = self._get_sql_version_string(conn)
    
    async def process_message(self, message: str) -> str:
        """
        Process user message and return AI response
        
        Args:
            message: User's natural language input
            
        Returns:
            AI response (Markdown formatted)
        """
        self.update_context()
        
        # Detect intent
        intent_match = self._intent_detector.detect(message)
        self._context.last_intent = intent_match.intent
        
        logger.info(f"Detected intent: {intent_match.intent.value} (confidence: {intent_match.confidence:.2f})")
        
        # Process based on intent
        try:
            if not self.is_connected:
                return self._no_connection_response()
            
            # Get data based on intent
            data = await self._execute_intent(intent_match)
            
            # Generate AI response
            response = await self._generate_response(message, intent_match, data)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"⚠️ İşlem sırasında bir hata oluştu: {str(e)}"
    
    async def _execute_intent(self, intent_match: IntentMatch) -> Dict[str, Any]:
        """Execute query based on intent"""
        intent = intent_match.intent
        conn = self.connection
        data = {"intent": intent.value}
        
        try:
            if intent == Intent.SERVER_STATUS:
                data["metrics"] = await self._get_server_status(conn)
                
            elif intent == Intent.TOP_QUERIES:
                data["queries"] = await self._get_top_queries(conn)
                
            elif intent == Intent.SLOW_QUERIES:
                data["queries"] = await self._get_slow_queries(conn)
                
            elif intent == Intent.TOP_WAITS:
                data["waits"] = await self._get_top_waits(conn)
                
            elif intent == Intent.BLOCKING_SESSIONS:
                data["blocking"] = await self._get_blocking_sessions(conn)
                
            elif intent == Intent.MISSING_INDEXES:
                data["indexes"] = await self._get_missing_indexes(conn)
                
            elif intent == Intent.FAILED_JOBS:
                data["jobs"] = await self._get_failed_jobs(conn)
                
            elif intent == Intent.MEMORY_STATUS:
                data["memory"] = await self._get_memory_status(conn)
                
            elif intent == Intent.CPU_STATUS:
                data["cpu"] = await self._get_cpu_status(conn)
                
            elif intent == Intent.BACKUP_STATUS:
                data["backups"] = await self._get_backup_status(conn)
                
            elif intent == Intent.SECURITY_AUDIT:
                data["security"] = await self._get_security_summary(conn)
                
            elif intent == Intent.HELP:
                data["help"] = self._get_help_info()
                
        except Exception as e:
            logger.error(f"Error executing intent {intent.value}: {e}")
            data["error"] = str(e)
        
        return data
    
    async def _get_server_status(self, conn) -> Dict:
        """Get server status metrics"""
        result = {}
        
        # CPU
        cpu = conn.execute_scalar("""
            SELECT TOP 1 
                100 - record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int')
            FROM (
                SELECT CAST(record AS xml) AS record 
                FROM sys.dm_os_ring_buffers 
                WHERE ring_buffer_type = 'RING_BUFFER_SCHEDULER_MONITOR'
            ) AS t
        """)
        result["cpu_percent"] = cpu or 0
        
        # Memory
        memory = conn.execute_query("""
            SELECT 
                physical_memory_in_use_kb / 1024 AS used_mb,
                memory_utilization_percentage AS usage_percent
            FROM sys.dm_os_process_memory
        """)
        if memory:
            result["memory_used_mb"] = memory[0].get("used_mb", 0)
            result["memory_percent"] = memory[0].get("usage_percent", 0)
        
        # Active sessions
        sessions = conn.execute_scalar("""
            SELECT COUNT(*) FROM sys.dm_exec_sessions 
            WHERE is_user_process = 1 AND status IN ('running', 'runnable')
        """)
        result["active_sessions"] = sessions or 0
        
        # Blocking
        blocking = conn.execute_scalar("""
            SELECT COUNT(DISTINCT blocking_session_id) 
            FROM sys.dm_exec_requests WHERE blocking_session_id > 0
        """)
        result["blocking_count"] = blocking or 0
        
        return result
    
    async def _get_top_queries(self, conn) -> List[Dict]:
        """Get top resource-consuming queries"""
        result = conn.execute_query("""
            SELECT TOP 10
                SUBSTRING(st.text, 1, 200) AS query_text,
                qs.total_elapsed_time / 1000 AS total_duration_ms,
                qs.execution_count,
                qs.total_logical_reads,
                qs.total_worker_time / 1000 AS total_cpu_ms
            FROM sys.dm_exec_query_stats qs
            CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
            ORDER BY qs.total_elapsed_time DESC
        """)
        return result or []
    
    async def _get_slow_queries(self, conn) -> List[Dict]:
        """Get slow running queries"""
        result = conn.execute_query("""
            SELECT TOP 10
                SUBSTRING(st.text, 1, 200) AS query_text,
                (qs.total_elapsed_time / qs.execution_count) / 1000 AS avg_duration_ms,
                qs.execution_count,
                qs.last_execution_time
            FROM sys.dm_exec_query_stats qs
            CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
            WHERE qs.execution_count > 0
            ORDER BY (qs.total_elapsed_time / qs.execution_count) DESC
        """)
        return result or []
    
    async def _get_top_waits(self, conn) -> List[Dict]:
        """Get top wait statistics"""
        result = conn.execute_query("""
            SELECT TOP 10
                wait_type,
                wait_time_ms,
                waiting_tasks_count,
                CAST(100.0 * wait_time_ms / SUM(wait_time_ms) OVER() AS DECIMAL(5,2)) AS wait_percent
            FROM sys.dm_os_wait_stats
            WHERE wait_type NOT IN (
                'SLEEP_TASK', 'BROKER_TASK_STOP', 'WAITFOR', 'LAZYWRITER_SLEEP',
                'XE_DISPATCHER_WAIT', 'REQUEST_FOR_DEADLOCK_SEARCH', 'SQLTRACE_BUFFER_FLUSH'
            )
            AND wait_time_ms > 0
            ORDER BY wait_time_ms DESC
        """)
        return result or []
    
    async def _get_blocking_sessions(self, conn) -> List[Dict]:
        """Get blocking session info"""
        result = conn.execute_query("""
            SELECT 
                r.session_id AS blocked_session,
                r.blocking_session_id AS blocking_session,
                r.wait_type,
                r.wait_time / 1000 AS wait_seconds,
                SUBSTRING(st.text, 1, 200) AS blocked_query
            FROM sys.dm_exec_requests r
            CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) st
            WHERE r.blocking_session_id > 0
            ORDER BY r.wait_time DESC
        """)
        return result or []
    
    async def _get_missing_indexes(self, conn) -> List[Dict]:
        """Get missing index recommendations"""
        result = conn.execute_query("""
            SELECT TOP 10
                OBJECT_NAME(mid.object_id) AS table_name,
                mid.equality_columns,
                mid.inequality_columns,
                mid.included_columns,
                migs.user_seeks,
                migs.avg_user_impact
            FROM sys.dm_db_missing_index_details mid
            JOIN sys.dm_db_missing_index_groups mig ON mid.index_handle = mig.index_handle
            JOIN sys.dm_db_missing_index_group_stats migs ON mig.index_group_handle = migs.group_handle
            WHERE mid.database_id = DB_ID()
            ORDER BY migs.avg_user_impact * migs.user_seeks DESC
        """)
        return result or []
    
    async def _get_failed_jobs(self, conn) -> List[Dict]:
        """Get failed jobs"""
        result = conn.execute_query("""
            SELECT TOP 10
                j.name AS job_name,
                h.step_name,
                msdb.dbo.agent_datetime(h.run_date, h.run_time) AS run_time,
                SUBSTRING(h.message, 1, 200) AS error_message
            FROM msdb.dbo.sysjobs j
            JOIN msdb.dbo.sysjobhistory h ON j.job_id = h.job_id
            WHERE h.run_status = 0 AND h.step_id > 0
            ORDER BY msdb.dbo.agent_datetime(h.run_date, h.run_time) DESC
        """)
        return result or []
    
    async def _get_memory_status(self, conn) -> Dict:
        """Get memory status"""
        result = {}
        
        # Process memory
        mem = conn.execute_query("""
            SELECT 
                physical_memory_in_use_kb / 1024 AS used_mb,
                locked_page_allocations_kb / 1024 AS locked_mb,
                memory_utilization_percentage AS percent
            FROM sys.dm_os_process_memory
        """)
        if mem:
            result.update(mem[0])
        
        # Buffer pool
        ple = conn.execute_scalar("""
            SELECT cntr_value FROM sys.dm_os_performance_counters
            WHERE counter_name = 'Page life expectancy' AND object_name LIKE '%Buffer Manager%'
        """)
        result["ple_seconds"] = ple or 0
        
        return result
    
    async def _get_cpu_status(self, conn) -> Dict:
        """Get CPU status"""
        result = {}
        
        cpu = conn.execute_scalar("""
            SELECT TOP 1 
                100 - record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int')
            FROM (
                SELECT CAST(record AS xml) AS record 
                FROM sys.dm_os_ring_buffers 
                WHERE ring_buffer_type = 'RING_BUFFER_SCHEDULER_MONITOR'
            ) AS t
        """)
        result["cpu_percent"] = cpu or 0
        
        # Batch requests
        batch = conn.execute_scalar("""
            SELECT cntr_value FROM sys.dm_os_performance_counters
            WHERE counter_name = 'Batch Requests/sec'
        """)
        result["batch_requests"] = batch or 0
        
        return result
    
    async def _get_backup_status(self, conn) -> List[Dict]:
        """Get backup status"""
        result = conn.execute_query("""
            SELECT 
                d.name AS database_name,
                MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END) AS last_full,
                MAX(CASE WHEN b.type = 'L' THEN b.backup_finish_date END) AS last_log,
                DATEDIFF(HOUR, MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END), GETDATE()) AS hours_since_full
            FROM sys.databases d
            LEFT JOIN msdb.dbo.backupset b ON d.name = b.database_name
            WHERE d.database_id > 4
            GROUP BY d.name
            ORDER BY hours_since_full DESC
        """)
        return result or []
    
    async def _get_security_summary(self, conn) -> Dict:
        """Get security summary"""
        result = {}
        
        # Sysadmin count
        sysadmins = conn.execute_scalar("""
            SELECT COUNT(*) FROM sys.server_role_members rm
            JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
            WHERE r.name = 'sysadmin'
        """)
        result["sysadmin_count"] = sysadmins or 0
        
        # SA status
        sa_disabled = conn.execute_scalar("""
            SELECT is_disabled FROM sys.server_principals WHERE name = 'sa'
        """)
        result["sa_disabled"] = bool(sa_disabled)
        
        # Total logins
        logins = conn.execute_scalar("""
            SELECT COUNT(*) FROM sys.server_principals WHERE type IN ('S', 'U', 'G')
        """)
        result["total_logins"] = logins or 0
        
        return result
    
    def _get_help_info(self) -> Dict:
        """Get help information"""
        return {
            "capabilities": [
                "🔍 Sorgu analizi ve optimizasyon önerileri",
                "📊 Performans metrikleri ve top queries",
                "⏱️ Wait statistics analizi",
                "🔒 Blocking session tespiti",
                "📈 Index önerileri (missing indexes)",
                "💾 Memory ve CPU durumu",
                "⚙️ SQL Agent job durumu",
                "🛡️ Güvenlik denetimi",
                "💿 Backup durumu kontrolü",
            ],
            "examples": [
                "En yavaş sorguları göster",
                "Wait istatistiklerini analiz et",
                "Blocking var mı kontrol et",
                "Eksik index önerilerini getir",
                "Sunucu durumunu özetle",
                "Son backup'lar ne zaman alındı?",
                "Güvenlik kontrolü yap",
            ]
        }
    
    async def _generate_response(
        self, 
        message: str, 
        intent_match: IntentMatch, 
        data: Dict[str, Any]
    ) -> str:
        """Generate AI response based on intent and data"""
        
        # Handle special cases
        if intent_match.intent == Intent.HELP:
            return self._format_help_response(data.get("help", {}))
        
        if "error" in data:
            return f"⚠️ Veri alınırken hata oluştu: {data['error']}"
        
        # Check if Ollama is available
        try:
            is_connected = await self._ollama.check_connection()
            if not is_connected:
                logger.warning("Ollama not available, using formatted response")
                return self._format_data_response(intent_match, data)
        except Exception:
            logger.warning("Ollama connection check failed, using formatted response")
            return self._format_data_response(intent_match, data)
        
        # Build context for AI
        system_prompt = """Sen SQL Server veritabanı uzmanı bir AI asistansın.
Kullanıcının sorularına Türkçe olarak yanıt ver.
Yanıtlarını Markdown formatında, okunabilir ve yapılandırılmış şekilde sun.
Teknik terimleri açıkla ve somut öneriler sun."""
        
        user_prompt = self._build_response_prompt(message, intent_match, data)
        
        try:
            response = await self._ollama.generate_response(user_prompt, system_prompt)
            return response
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            # Fallback to formatted data response
            return self._format_data_response(intent_match, data)
    
    def _build_response_prompt(
        self, 
        message: str, 
        intent_match: IntentMatch, 
        data: Dict[str, Any]
    ) -> str:
        """Build prompt for AI response generation"""
        prompt = f"""Kullanıcı Sorusu: {message}

Bağlam:
- Sunucu: {self._context.server_name}
- Veritabanı: {self._context.database_name}
- SQL Server Version: {self._context.sql_version}
- Tespit Edilen İstek: {intent_match.intent.value}

Toplanan Veriler:
{self._format_data_for_prompt(data)}

Lütfen bu verileri analiz ederek kullanıcının sorusuna kapsamlı bir yanıt ver.
Önemli bulguları vurgula ve varsa iyileştirme önerileri sun."""
        
        return prompt

    @staticmethod
    def _get_sql_version_string(conn) -> str:
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
    
    def _format_data_for_prompt(self, data: Dict[str, Any]) -> str:
        """Format data for AI prompt"""
        lines = []
        for key, value in data.items():
            if key == "intent":
                continue
            if isinstance(value, list):
                lines.append(f"\n{key.upper()}:")
                for i, item in enumerate(value[:5], 1):  # Limit to 5 items
                    if isinstance(item, dict):
                        lines.append(f"  {i}. {item}")
                    else:
                        lines.append(f"  {i}. {item}")
            elif isinstance(value, dict):
                lines.append(f"\n{key.upper()}: {value}")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)
    
    def _format_help_response(self, help_info: Dict) -> str:
        """Format help response"""
        response = """## 🤖 SQL Perf AI Asistan

Veritabanınız hakkında doğal dilde sorular sorabilirsiniz.

### Yapabileceklerim:
"""
        for cap in help_info.get("capabilities", []):
            response += f"\n- {cap}"
        
        response += "\n\n### Örnek Sorular:\n"
        for ex in help_info.get("examples", []):
            response += f"\n- *\"{ex}\"*"
        
        return response
    
    def _format_data_response(self, intent_match: IntentMatch, data: Dict[str, Any]) -> str:
        """Format a simple data response when AI is unavailable"""
        intent = intent_match.intent
        
        if intent == Intent.SERVER_STATUS:
            metrics = data.get("metrics", {})
            return f"""## 📊 Sunucu Durumu

| Metrik | Değer |
|--------|-------|
| CPU Kullanımı | {metrics.get('cpu_percent', 0)}% |
| Memory Kullanımı | {metrics.get('memory_percent', 0)}% |
| Aktif Oturumlar | {metrics.get('active_sessions', 0)} |
| Blocking | {metrics.get('blocking_count', 0)} |

*Bağlı sunucu: {self._context.server_name} / {self._context.database_name}*
"""
        
        elif intent == Intent.TOP_QUERIES:
            queries = data.get("queries", [])
            if not queries:
                return "📊 Sorgu istatistiği bulunamadı."
            
            response = "## 📊 En Yoğun Sorgular\n\n"
            response += "| # | Sorgu | Toplam Süre | Çalışma | Okuma |\n"
            response += "|---|-------|-------------|---------|-------|\n"
            for i, q in enumerate(queries[:10], 1):
                text = str(q.get('query_text', ''))[:50].replace('\n', ' ').replace('|', '/')
                response += f"| {i} | {text}... | {q.get('total_duration_ms', 0):,} ms | {q.get('execution_count', 0):,} | {q.get('total_logical_reads', 0):,} |\n"
            return response
        
        elif intent == Intent.SLOW_QUERIES:
            queries = data.get("queries", [])
            if not queries:
                return "⏱️ Yavaş sorgu bulunamadı."
            
            response = "## ⏱️ Yavaş Sorgular\n\n"
            response += "| # | Sorgu | Ort. Süre | Çalışma |\n"
            response += "|---|-------|-----------|----------|\n"
            for i, q in enumerate(queries[:10], 1):
                text = str(q.get('query_text', ''))[:50].replace('\n', ' ').replace('|', '/')
                response += f"| {i} | {text}... | {q.get('avg_duration_ms', 0):,} ms | {q.get('execution_count', 0):,} |\n"
            return response
        
        elif intent == Intent.TOP_WAITS:
            waits = data.get("waits", [])
            if not waits:
                return "✅ Önemli bir wait istatistiği bulunamadı."
            
            response = "## ⏱️ Top Wait Types\n\n"
            response += "| Wait Type | Süre | Oran |\n"
            response += "|-----------|------|------|\n"
            for w in waits[:10]:
                wait_ms = w.get('wait_time_ms', 0)
                response += f"| {w.get('wait_type', 'N/A')} | {wait_ms:,} ms | {w.get('wait_percent', 0)}% |\n"
            return response
        
        elif intent == Intent.BLOCKING_SESSIONS:
            blocking = data.get("blocking", [])
            if not blocking:
                return "✅ Şu anda blocking durumu yok."
            
            response = "## 🔒 Blocking Sessions\n\n"
            response += "| Blocked | Blocker | Wait Type | Süre |\n"
            response += "|---------|---------|-----------|------|\n"
            for b in blocking:
                response += f"| {b.get('blocked_session', '')} | {b.get('blocking_session', '')} | {b.get('wait_type', '')} | {b.get('wait_seconds', 0)}s |\n"
            
            response += "\n⚠️ **Öneri:** Blocking session'ları çözmek için KILL komutu veya uygulama tarafını kontrol edin."
            return response
        
        elif intent == Intent.MISSING_INDEXES:
            indexes = data.get("indexes", [])
            if not indexes:
                return "✅ Eksik index önerisi bulunamadı."
            
            response = "## 📈 Eksik Index Önerileri\n\n"
            for i, idx in enumerate(indexes[:5], 1):
                response += f"### {i}. {idx.get('table_name', 'N/A')}\n"
                response += f"- **Equality:** {idx.get('equality_columns', '-')}\n"
                response += f"- **Inequality:** {idx.get('inequality_columns', '-')}\n"
                response += f"- **Include:** {idx.get('included_columns', '-')}\n"
                response += f"- **Seek Sayısı:** {idx.get('user_seeks', 0):,}\n"
                response += f"- **Tahmini Etki:** %{idx.get('avg_user_impact', 0)}\n\n"
            return response
        
        elif intent == Intent.FAILED_JOBS:
            jobs = data.get("jobs", [])
            if not jobs:
                return "✅ Başarısız job bulunamadı."
            
            response = "## ❌ Başarısız Job'lar\n\n"
            for j in jobs[:5]:
                response += f"### {j.get('job_name', 'N/A')}\n"
                response += f"- **Step:** {j.get('step_name', '')}\n"
                response += f"- **Zaman:** {j.get('run_time', '')}\n"
                response += f"- **Hata:** {j.get('error_message', '')[:100]}...\n\n"
            return response
        
        elif intent == Intent.MEMORY_STATUS:
            memory = data.get("memory", {})
            return f"""## 💾 Memory Durumu

| Metrik | Değer |
|--------|-------|
| Kullanılan | {memory.get('used_mb', 0):,} MB |
| Memory % | {memory.get('percent', 0)}% |
| Locked Pages | {memory.get('locked_mb', 0):,} MB |
| Page Life Expectancy | {memory.get('ple_seconds', 0):,} saniye |

*PLE 300 saniyenin altındaysa memory baskısı var demektir.*
"""
        
        elif intent == Intent.CPU_STATUS:
            cpu = data.get("cpu", {})
            return f"""## ⚡ CPU Durumu

| Metrik | Değer |
|--------|-------|
| CPU Kullanımı | {cpu.get('cpu_percent', 0)}% |
| Batch Requests/sec | {cpu.get('batch_requests', 0):,} |

*CPU sürekli %80+ ise sorgu optimizasyonu veya donanım iyileştirmesi gerekebilir.*
"""
        
        elif intent == Intent.BACKUP_STATUS:
            backups = data.get("backups", [])
            if not backups:
                return "⚠️ Backup bilgisi bulunamadı."
            
            response = "## 💿 Backup Durumu\n\n"
            response += "| Database | Son Full | Son Log | Saat |\n"
            response += "|----------|----------|---------|------|\n"
            for b in backups[:10]:
                full = str(b.get('last_full', '-'))[:16] if b.get('last_full') else '-'
                log = str(b.get('last_log', '-'))[:16] if b.get('last_log') else '-'
                hours = b.get('hours_since_full', 0) or 0
                status = "⚠️" if hours > 24 else "✅"
                response += f"| {b.get('database_name', '')} | {full} | {log} | {hours}h {status} |\n"
            return response
        
        elif intent == Intent.SECURITY_AUDIT:
            security = data.get("security", {})
            sa_status = "✅ Devre Dışı" if security.get('sa_disabled') else "⚠️ Aktif"
            return f"""## 🛡️ Güvenlik Özeti

| Kontrol | Durum |
|---------|-------|
| Toplam Login | {security.get('total_logins', 0)} |
| Sysadmin Sayısı | {security.get('sysadmin_count', 0)} |
| SA Hesabı | {sa_status} |

*Sysadmin sayısını minimumda tutun ve SA hesabını devre dışı bırakın.*
"""
        
        elif intent == Intent.GENERAL_QUESTION:
            return f"""🤔 Sorunuzu anladım: *"{intent_match.original_text}"*

Bu konuda size yardımcı olabilmem için daha spesifik bir soru sorabilir misiniz?

**Örnek sorular:**
- "En yavaş sorguları göster"
- "Wait istatistiklerini analiz et"
- "Blocking var mı?"
- "Sunucu durumunu özetle"
"""
        
        # Generic response
        return f"✅ {self._intent_detector.get_intent_description(intent)}"
    
    def _no_connection_response(self) -> str:
        """Response when not connected to database"""
        return """⚠️ **Veritabanı Bağlantısı Yok**

Lütfen önce bir SQL Server'a bağlanın:

1. **Settings** → **Connections** bölümüne gidin
2. Yeni bir bağlantı ekleyin veya mevcut birini seçin
3. **Connect** butonuna tıklayın

Bağlandıktan sonra sorularınızı yanıtlayabilirim."""


# Singleton
_service: Optional[AIChatService] = None


def get_chat_service() -> AIChatService:
    """Get singleton chat service instance"""
    global _service
    if _service is None:
        _service = AIChatService()
    return _service
