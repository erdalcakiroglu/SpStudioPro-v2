"""
Intent Detection System - Natural language to intent mapping

Doğal dil sorgularını intent'lere dönüştürür ve entity extraction yapar.
Türkçe ve İngilizce destekler.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import re

from app.core.logger import get_logger

logger = get_logger('ai.intent')


class Intent(Enum):
    """Supported user intents - 40+ intent türü"""
    
    # ═══════════════════════════════════════════════════════════
    # QUERY ANALYSIS (Sorgu Analizi)
    # ═══════════════════════════════════════════════════════════
    ANALYZE_QUERY = "analyze_query"
    EXPLAIN_PLAN = "explain_plan"
    OPTIMIZE_QUERY = "optimize_query"
    FIND_QUERY = "find_query"
    QUERY_HISTORY = "query_history"
    
    # ═══════════════════════════════════════════════════════════
    # PERFORMANCE (Performans)
    # ═══════════════════════════════════════════════════════════
    TOP_QUERIES = "top_queries"
    SLOW_QUERIES = "slow_queries"
    CPU_INTENSIVE = "cpu_intensive"
    IO_INTENSIVE = "io_intensive"
    EXPENSIVE_QUERIES = "expensive_queries"
    FREQUENT_QUERIES = "frequent_queries"
    LONG_RUNNING = "long_running"
    
    # ═══════════════════════════════════════════════════════════
    # WAIT STATS (Bekleme İstatistikleri)
    # ═══════════════════════════════════════════════════════════
    TOP_WAITS = "top_waits"
    WAIT_ANALYSIS = "wait_analysis"
    WAIT_BY_TYPE = "wait_by_type"
    SIGNAL_WAITS = "signal_waits"
    RESOURCE_WAITS = "resource_waits"
    CLEAR_WAITS = "clear_waits"
    
    # ═══════════════════════════════════════════════════════════
    # BLOCKING & LOCKING (Kilitleme)
    # ═══════════════════════════════════════════════════════════
    BLOCKING_SESSIONS = "blocking_sessions"
    DEADLOCKS = "deadlocks"
    LOCK_ANALYSIS = "lock_analysis"
    KILL_SESSION = "kill_session"
    ACTIVE_SESSIONS = "active_sessions"
    
    # ═══════════════════════════════════════════════════════════
    # INDEX (İndeks)
    # ═══════════════════════════════════════════════════════════
    MISSING_INDEXES = "missing_indexes"
    UNUSED_INDEXES = "unused_indexes"
    INDEX_USAGE = "index_usage"
    INDEX_FRAGMENTATION = "index_fragmentation"
    DUPLICATE_INDEXES = "duplicate_indexes"
    INDEX_SIZE = "index_size"
    REBUILD_INDEX = "rebuild_index"
    
    # ═══════════════════════════════════════════════════════════
    # DATABASE OBJECTS (Veritabanı Nesneleri)
    # ═══════════════════════════════════════════════════════════
    SP_INFO = "sp_info"
    TABLE_INFO = "table_info"
    VIEW_INFO = "view_info"
    FUNCTION_INFO = "function_info"
    TRIGGER_INFO = "trigger_info"
    SCHEMA_INFO = "schema_info"
    OBJECT_SEARCH = "object_search"
    OBJECT_DEPENDENCIES = "object_dependencies"
    
    # ═══════════════════════════════════════════════════════════
    # SERVER HEALTH (Sunucu Sağlığı)
    # ═══════════════════════════════════════════════════════════
    SERVER_STATUS = "server_status"
    MEMORY_STATUS = "memory_status"
    CPU_STATUS = "cpu_status"
    DISK_STATUS = "disk_status"
    BUFFER_POOL = "buffer_pool"
    PAGE_LIFE = "page_life"
    CONNECTION_COUNT = "connection_count"
    
    # ═══════════════════════════════════════════════════════════
    # TEMPDB
    # ═══════════════════════════════════════════════════════════
    TEMPDB_USAGE = "tempdb_usage"
    TEMPDB_CONTENTION = "tempdb_contention"
    VERSION_STORE = "version_store"
    
    # ═══════════════════════════════════════════════════════════
    # JOBS (SQL Agent)
    # ═══════════════════════════════════════════════════════════
    FAILED_JOBS = "failed_jobs"
    RUNNING_JOBS = "running_jobs"
    JOB_HISTORY = "job_history"
    JOB_SCHEDULE = "job_schedule"
    LONG_RUNNING_JOBS = "long_running_jobs"
    
    # ═══════════════════════════════════════════════════════════
    # SECURITY (Güvenlik)
    # ═══════════════════════════════════════════════════════════
    SECURITY_AUDIT = "security_audit"
    LOGIN_INFO = "login_info"
    PERMISSIONS = "permissions"
    ROLE_MEMBERS = "role_members"
    ORPHANED_USERS = "orphaned_users"
    
    # ═══════════════════════════════════════════════════════════
    # BACKUP & RECOVERY
    # ═══════════════════════════════════════════════════════════
    BACKUP_STATUS = "backup_status"
    LAST_BACKUP = "last_backup"
    BACKUP_HISTORY = "backup_history"
    LOG_USAGE = "log_usage"
    
    # ═══════════════════════════════════════════════════════════
    # DATABASE INFO
    # ═══════════════════════════════════════════════════════════
    DATABASE_SIZE = "database_size"
    DATABASE_FILES = "database_files"
    DATABASE_GROWTH = "database_growth"
    DATABASE_OPTIONS = "database_options"
    
    # ═══════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════
    UPDATE_STATISTICS = "update_statistics"
    STATS_INFO = "stats_info"
    AUTO_STATS = "auto_stats"
    
    # ═══════════════════════════════════════════════════════════
    # GENERAL
    # ═══════════════════════════════════════════════════════════
    HELP = "help"
    RUN_QUERY = "run_query"
    GENERAL_QUESTION = "general_question"
    UNKNOWN = "unknown"


@dataclass
class Entity:
    """Extracted entity from user input"""
    type: str  # table, database, sp, number, time, etc.
    value: str
    start: int = 0
    end: int = 0


@dataclass
class IntentMatch:
    """Result of intent detection"""
    intent: Intent
    confidence: float  # 0.0 - 1.0
    entities: Dict[str, Any] = field(default_factory=dict)
    extracted_entities: List[Entity] = field(default_factory=list)
    original_text: str = ""
    suggested_template: Optional[str] = None
    
    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.6
    
    @property
    def has_entities(self) -> bool:
        return len(self.extracted_entities) > 0


# ═══════════════════════════════════════════════════════════════════════════
# INTENT PATTERNS - Türkçe ve İngilizce
# ═══════════════════════════════════════════════════════════════════════════

INTENT_PATTERNS: Dict[Intent, List[str]] = {
    # Query Analysis
    Intent.ANALYZE_QUERY: [
        r"analiz", r"analyze", r"sorgu.*analiz", r"query.*analyze",
        r"incele", r"examine", r"değerlendir", r"evaluate", r"check query"
    ],
    Intent.EXPLAIN_PLAN: [
        r"plan", r"execution plan", r"çalışma planı", r"explain",
        r"plan.*açıkla", r"plan.*nedir", r"show plan", r"query plan"
    ],
    Intent.OPTIMIZE_QUERY: [
        r"optimize", r"iyileştir", r"hızlandır", r"speed up",
        r"tune", r"performans.*artır", r"improve", r"daha hızlı"
    ],
    Intent.FIND_QUERY: [
        r"sorgu.*bul", r"find.*query", r"query.*search", r"hangi sorgu",
        r"sorgu.*ara", r"search query"
    ],
    
    # Performance
    Intent.TOP_QUERIES: [
        r"top.*sorgu", r"en çok.*sorgu", r"most.*queries",
        r"yoğun.*sorgu", r"top queries", r"en yoğun", r"top \d+"
    ],
    Intent.SLOW_QUERIES: [
        r"yavaş.*sorgu", r"slow.*query", r"uzun süren",
        r"long running", r"timeout", r"geç kalan", r"yavaş çalışan"
    ],
    Intent.CPU_INTENSIVE: [
        r"cpu.*yoğun", r"cpu.*intensive", r"cpu.*kullan",
        r"processor", r"işlemci", r"high cpu", r"cpu heavy"
    ],
    Intent.IO_INTENSIVE: [
        r"io.*yoğun", r"disk.*yoğun", r"read.*intensive",
        r"write.*intensive", r"okuma.*yazma", r"logical read"
    ],
    Intent.EXPENSIVE_QUERIES: [
        r"pahalı.*sorgu", r"expensive", r"costly", r"maliyetli",
        r"cost.*high", r"yüksek maliyet"
    ],
    Intent.FREQUENT_QUERIES: [
        r"sık çalışan", r"frequent", r"often", r"en çok çalışan",
        r"most executed", r"execution count"
    ],
    Intent.LONG_RUNNING: [
        r"uzun süren", r"long running", r"çalışan sorgu", r"running query",
        r"şu an çalışan", r"currently running"
    ],
    
    # Wait Stats
    Intent.TOP_WAITS: [
        r"top.*wait", r"en çok.*wait", r"bekleme.*istatistik",
        r"wait stats", r"wait.*analiz", r"wait type"
    ],
    Intent.WAIT_ANALYSIS: [
        r"wait.*neden", r"neden bekliyor", r"why waiting",
        r"bekleme.*sebep", r"wait.*cause"
    ],
    Intent.WAIT_BY_TYPE: [
        r"pageiolatch", r"lck_", r"async_network", r"cxpacket",
        r"writelog", r"sos_scheduler", r"resource_semaphore"
    ],
    Intent.SIGNAL_WAITS: [
        r"signal.*wait", r"cpu.*queue", r"sinyal bekleme"
    ],
    Intent.CLEAR_WAITS: [
        r"clear.*wait", r"reset.*wait", r"wait.*temizle", r"sıfırla"
    ],
    
    # Blocking & Locking
    Intent.BLOCKING_SESSIONS: [
        r"block", r"engelle", r"kilitlen", r"tıkan",
        r"blocking session", r"blocked", r"bekleyen", r"who is blocking"
    ],
    Intent.DEADLOCKS: [
        r"deadlock", r"kilitlenme", r"çıkmaz", r"ölü kilit"
    ],
    Intent.LOCK_ANALYSIS: [
        r"lock.*analiz", r"kilit.*analiz", r"locking",
        r"lock escalation", r"row lock", r"page lock", r"table lock"
    ],
    Intent.KILL_SESSION: [
        r"kill", r"session.*kapat", r"bağlantı.*kes", r"terminate"
    ],
    Intent.ACTIVE_SESSIONS: [
        r"aktif.*session", r"active.*session", r"bağlı kullanıcı",
        r"connected users", r"who is connected"
    ],
    
    # Index
    Intent.MISSING_INDEXES: [
        r"eksik.*index", r"missing.*index", r"index.*öner",
        r"index.*recommendation", r"hangi index", r"create index"
    ],
    Intent.UNUSED_INDEXES: [
        r"kullanılmayan.*index", r"unused.*index",
        r"gereksiz.*index", r"drop.*index", r"never used"
    ],
    Intent.INDEX_USAGE: [
        r"index.*kullanım", r"index.*usage", r"index.*stats",
        r"index.*istatistik", r"seek.*scan"
    ],
    Intent.INDEX_FRAGMENTATION: [
        r"fragment", r"parçalanma", r"rebuild", r"reorganize",
        r"index health", r"index maintenance"
    ],
    Intent.DUPLICATE_INDEXES: [
        r"duplicate.*index", r"overlapping", r"çakışan.*index",
        r"redundant.*index"
    ],
    Intent.INDEX_SIZE: [
        r"index.*boyut", r"index.*size", r"index.*space"
    ],
    
    # Database Objects
    Intent.SP_INFO: [
        r"stored procedure", r"sp\b", r"prosedür",
        r"procedure.*bilgi", r"sp.*ne yapar"
    ],
    Intent.TABLE_INFO: [
        r"tablo.*bilgi", r"table.*info", r"tablo.*boyut",
        r"table.*size", r"row count", r"satır sayısı", r"table structure"
    ],
    Intent.VIEW_INFO: [
        r"view.*bilgi", r"görünüm", r"view.*tanım"
    ],
    Intent.OBJECT_SEARCH: [
        r"nesne.*ara", r"object.*search", r"find.*object",
        r"where is", r"nerede", r"which table"
    ],
    Intent.OBJECT_DEPENDENCIES: [
        r"bağımlılık", r"dependency", r"depends on", r"used by",
        r"referans", r"reference"
    ],
    
    # Server Health
    Intent.SERVER_STATUS: [
        r"server.*durum", r"sunucu.*sağlık", r"server.*health",
        r"genel.*durum", r"overview", r"özet", r"dashboard"
    ],
    Intent.MEMORY_STATUS: [
        r"memory", r"bellek", r"ram", r"buffer pool",
        r"memory.*kullanım", r"ple", r"page life"
    ],
    Intent.CPU_STATUS: [
        r"cpu.*durum", r"cpu.*status", r"işlemci.*yük",
        r"cpu.*usage", r"processor.*load"
    ],
    Intent.DISK_STATUS: [
        r"disk.*durum", r"disk.*status", r"io.*durum",
        r"storage", r"depolama", r"latency", r"iops"
    ],
    Intent.PAGE_LIFE: [
        r"page life", r"ple", r"buffer.*life", r"memory pressure"
    ],
    Intent.CONNECTION_COUNT: [
        r"connection.*count", r"bağlantı.*sayısı", r"how many connections"
    ],
    
    # TempDB
    Intent.TEMPDB_USAGE: [
        r"tempdb", r"temp.*kullanım", r"temp.*usage"
    ],
    Intent.VERSION_STORE: [
        r"version store", r"snapshot", r"row versioning"
    ],
    
    # Jobs
    Intent.FAILED_JOBS: [
        r"başarısız.*job", r"failed.*job", r"hatalı.*job",
        r"job.*error", r"job.*fail"
    ],
    Intent.RUNNING_JOBS: [
        r"çalışan.*job", r"running.*job", r"aktif.*job",
        r"job.*running", r"job.*aktif"
    ],
    Intent.JOB_HISTORY: [
        r"job.*geçmiş", r"job.*history", r"job.*log"
    ],
    Intent.LONG_RUNNING_JOBS: [
        r"uzun süren.*job", r"long.*running.*job"
    ],
    
    # Security
    Intent.SECURITY_AUDIT: [
        r"güvenlik", r"security", r"audit", r"denetim",
        r"güvenlik.*kontrol", r"security.*check"
    ],
    Intent.LOGIN_INFO: [
        r"login", r"kullanıcı", r"user", r"oturum",
        r"hesap", r"account"
    ],
    Intent.PERMISSIONS: [
        r"yetki", r"permission", r"izin", r"erişim",
        r"access", r"grant", r"role"
    ],
    Intent.ORPHANED_USERS: [
        r"orphan", r"yetim.*kullanıcı", r"eşleşmeyen"
    ],
    
    # Backup
    Intent.BACKUP_STATUS: [
        r"backup.*durum", r"yedek.*durum", r"backup.*status"
    ],
    Intent.LAST_BACKUP: [
        r"son.*backup", r"last.*backup", r"en son.*yedek",
        r"ne zaman.*backup", r"backup.*ne zaman"
    ],
    Intent.LOG_USAGE: [
        r"log.*usage", r"transaction log", r"log.*kullanım",
        r"log.*boyut"
    ],
    
    # Database
    Intent.DATABASE_SIZE: [
        r"database.*size", r"veritabanı.*boyut", r"db.*size",
        r"ne kadar yer"
    ],
    Intent.DATABASE_FILES: [
        r"database.*file", r"mdf", r"ldf", r"ndf", r"data file"
    ],
    
    # Statistics
    Intent.UPDATE_STATISTICS: [
        r"update.*stat", r"istatistik.*güncelle", r"stat.*update"
    ],
    Intent.STATS_INFO: [
        r"statistics.*info", r"istatistik.*bilgi", r"stat.*detail"
    ],
    
    # General
    Intent.HELP: [
        r"yardım", r"help", r"ne yapabilirsin", r"what can you",
        r"nasıl.*kullan", r"how to use", r"komutlar", r"commands"
    ],
    Intent.RUN_QUERY: [
        r"^select\b", r"^exec\b", r"^sp_", r"çalıştır", r"execute",
        r"run query"
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# ENTITY PATTERNS - Entity extraction için
# ═══════════════════════════════════════════════════════════════════════════

ENTITY_PATTERNS = {
    'number': r'\b(\d+)\b',
    'table_name': r'\b([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)\b',
    'object_name': r'\b(dbo\.[A-Za-z_][A-Za-z0-9_]*)\b',
    'time_period': r'\b(son\s+\d+\s+(saat|dakika|gün|hafta)|last\s+\d+\s+(hour|minute|day|week)s?)\b',
    'top_n': r'\b(top\s*\d+|en\s+(iyi|kötü|yavaş|hızlı)\s*\d+)\b',
    'wait_type': r'\b(PAGEIOLATCH|LCK_|ASYNC_NETWORK|CXPACKET|WRITELOG|SOS_SCHEDULER)[A-Z_]*\b',
    'database_name': r'\b([A-Za-z_][A-Za-z0-9_]*DB|master|msdb|tempdb|model)\b',
}


class IntentDetector:
    """
    Detects user intent from natural language input
    
    Features:
    - Multi-language support (TR/EN)
    - Entity extraction
    - Confidence scoring
    - Template suggestion
    """
    
    def __init__(self):
        self._compiled_patterns: Dict[Intent, List[re.Pattern]] = {}
        self._entity_patterns: Dict[str, re.Pattern] = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for faster matching"""
        for intent, patterns in INTENT_PATTERNS.items():
            self._compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE | re.UNICODE)
                for p in patterns
            ]
        
        for entity_type, pattern in ENTITY_PATTERNS.items():
            self._entity_patterns[entity_type] = re.compile(pattern, re.IGNORECASE)
    
    def detect(self, text: str) -> IntentMatch:
        """
        Detect intent from user input
        
        Args:
            text: User's natural language input
            
        Returns:
            IntentMatch with detected intent, confidence, and entities
        """
        if not text or not text.strip():
            return IntentMatch(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                original_text=text
            )
        
        text_lower = text.lower().strip()
        
        # Extract entities first
        entities = self._extract_entities(text)
        
        # Score each intent
        scores: List[Tuple[Intent, float, Dict[str, str]]] = []
        
        for intent, patterns in self._compiled_patterns.items():
            score, matched = self._calculate_score(text_lower, patterns)
            if score > 0:
                scores.append((intent, score, matched))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        if scores:
            best_intent, best_score, matched = scores[0]
            # Normalize score to confidence (0-1)
            confidence = min(best_score / 3.0, 1.0)  # 3 matches = 100% confidence
            
            # Get suggested template
            from app.ai.query_templates import get_template_for_intent
            template = get_template_for_intent(best_intent)
            
            return IntentMatch(
                intent=best_intent,
                confidence=confidence,
                entities=matched,
                extracted_entities=entities,
                original_text=text,
                suggested_template=template
            )
        
        # No match - general question
        return IntentMatch(
            intent=Intent.GENERAL_QUESTION,
            confidence=0.5,
            extracted_entities=entities,
            original_text=text
        )
    
    def _calculate_score(
        self, 
        text: str, 
        patterns: List[re.Pattern]
    ) -> Tuple[float, Dict[str, str]]:
        """Calculate match score for patterns"""
        score = 0.0
        entities = {}
        
        for pattern in patterns:
            matches = pattern.findall(text)
            if matches:
                score += len(matches)
                if isinstance(matches[0], str):
                    entities[pattern.pattern] = matches[0]
        
        return score, entities
    
    def _extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text"""
        entities = []
        
        for entity_type, pattern in self._entity_patterns.items():
            for match in pattern.finditer(text):
                entities.append(Entity(
                    type=entity_type,
                    value=match.group(1) if match.groups() else match.group(0),
                    start=match.start(),
                    end=match.end()
                ))
        
        return entities
    
    def get_intent_description(self, intent: Intent) -> str:
        """Get human-readable description of intent"""
        descriptions = {
            Intent.ANALYZE_QUERY: "Query analysis",
            Intent.EXPLAIN_PLAN: "Execution plan explanation",
            Intent.OPTIMIZE_QUERY: "Query optimization recommendations",
            Intent.TOP_QUERIES: "List top queries",
            Intent.SLOW_QUERIES: "Show slow queries",
            Intent.CPU_INTENSIVE: "List CPU-intensive queries",
            Intent.IO_INTENSIVE: "List I/O-intensive queries",
            Intent.TOP_WAITS: "Show top wait statistics",
            Intent.WAIT_ANALYSIS: "Wait statistics analysis",
            Intent.BLOCKING_SESSIONS: "Check blocking status",
            Intent.DEADLOCKS: "Show deadlock information",
            Intent.MISSING_INDEXES: "Missing index recommendations",
            Intent.UNUSED_INDEXES: "Unused indexes",
            Intent.INDEX_FRAGMENTATION: "Check index fragmentation",
            Intent.SERVER_STATUS: "Server status summary",
            Intent.MEMORY_STATUS: "Memory status",
            Intent.CPU_STATUS: "CPU status",
            Intent.DISK_STATUS: "Disk status",
            Intent.FAILED_JOBS: "List failed jobs",
            Intent.RUNNING_JOBS: "List running jobs",
            Intent.SECURITY_AUDIT: "Security audit",
            Intent.BACKUP_STATUS: "Check backup status",
            Intent.LAST_BACKUP: "Last backup information",
            Intent.DATABASE_SIZE: "Database size",
            Intent.TEMPDB_USAGE: "TempDB usage",
            Intent.HELP: "Help",
            Intent.GENERAL_QUESTION: "General question",
        }
        return descriptions.get(intent, "Action will be performed")
    
    def get_all_intents(self) -> List[Dict[str, str]]:
        """Get list of all supported intents with descriptions"""
        return [
            {"intent": intent.value, "description": self.get_intent_description(intent)}
            for intent in Intent
            if intent not in [Intent.UNKNOWN, Intent.GENERAL_QUESTION]
        ]


# Singleton instance
_detector: Optional[IntentDetector] = None


def get_intent_detector() -> IntentDetector:
    """Get singleton intent detector instance"""
    global _detector
    if _detector is None:
        _detector = IntentDetector()
    return _detector
