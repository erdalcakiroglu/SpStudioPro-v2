"""
AI Response Validator - Validate and sanitize AI-generated SQL recommendations

Bu modül AI çıktısını doğrular ve güvenli hale getirir:
1. SQL syntax doğrulama
2. Tehlikeli komut tespiti ve filtreleme
3. Best practice uyumluluk kontrolü
4. Object varlık doğrulama (opsiyonel)
5. Öneri kalite skoru
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.core.logger import get_logger

logger = get_logger('ai.validator')


class ValidationSeverity(Enum):
    """Doğrulama sonuç seviyeleri"""
    CRITICAL = "critical"   # Kesinlikle engelle
    WARNING = "warning"     # Uyar ama izin ver
    INFO = "info"          # Bilgilendirme
    OK = "ok"              # Sorun yok


class DangerLevel(Enum):
    """Tehlike seviyeleri"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Doğrulama sorunu"""
    severity: ValidationSeverity
    category: str
    message: str
    line_number: Optional[int] = None
    suggestion: str = ""
    blocked: bool = False


@dataclass
class ValidationResult:
    """Doğrulama sonucu"""
    is_valid: bool
    danger_level: DangerLevel
    issues: List[ValidationIssue] = field(default_factory=list)
    sanitized_response: str = ""
    quality_score: float = 0.0  # 0-100
    blocked_commands: List[str] = field(default_factory=list)
    
    @property
    def has_critical_issues(self) -> bool:
        return any(i.severity == ValidationSeverity.CRITICAL for i in self.issues)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == ValidationSeverity.WARNING)
    
    def get_summary(self) -> str:
        """Özet döndür"""
        if self.is_valid and not self.issues:
            return "✅ Doğrulama başarılı"
        
        lines = []
        if not self.is_valid:
            lines.append(f"❌ Doğrulama başarısız (Tehlike: {self.danger_level.value})")
        
        if self.blocked_commands:
            lines.append(f"🚫 Engellenen komutlar: {', '.join(self.blocked_commands)}")
        
        critical = [i for i in self.issues if i.severity == ValidationSeverity.CRITICAL]
        if critical:
            lines.append(f"🔴 {len(critical)} kritik sorun")
        
        warnings = [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
        if warnings:
            lines.append(f"⚠️ {len(warnings)} uyarı")
        
        lines.append(f"📊 Kalite skoru: {self.quality_score:.0f}/100")
        
        return "\n".join(lines)


class AIResponseValidator:
    """
    AI response validator ve sanitizer
    
    Usage:
        validator = AIResponseValidator()
        result = validator.validate(ai_response)
        
        if result.is_valid:
            safe_response = result.sanitized_response
        else:
            print(result.get_summary())
    """
    
    # Kesinlikle engellenmesi gereken komutlar
    CRITICAL_BLOCKED_COMMANDS = [
        r'\bDROP\s+DATABASE\b',
        r'\bDROP\s+TABLE\b(?!\s+IF\s+EXISTS\s+#)',  # Temp table hariç
        r'\bTRUNCATE\s+TABLE\b(?!\s+#)',  # Temp table hariç
        r'\bDELETE\s+FROM\s+(?!#)\w+\s*(?:;|$)',  # WHERE olmayan DELETE (temp hariç)
        r'\bxp_cmdshell\b',
        r'\bsp_configure\b',
        r'\bsp_addlogin\b',
        r'\bsp_addsrvrolemember\b',
        r'\bsp_addrolemember\b.*sysadmin',
        r'\bOPENROWSET\b',
        r'\bOPENDATASOURCE\b',
        r'\bBULK\s+INSERT\b',
        r'\bRESTORE\s+DATABASE\b',
        r'\bALTER\s+LOGIN\b.*PASSWORD',
        r'\bCREATE\s+LOGIN\b',
        r'\bGRANT\b.*\bCONTROL\b',
        r'\bSHUTDOWN\b',
        r'\bRECONFIGURE\b',
    ]
    
    # Uyarı gerektiren komutlar
    WARNING_COMMANDS = [
        (r'\bDROP\s+INDEX\b', "DROP INDEX komutu - dikkatli kullanın"),
        (r'\bDROP\s+PROCEDURE\b', "DROP PROCEDURE komutu"),
        (r'\bDROP\s+VIEW\b', "DROP VIEW komutu"),
        (r'\bALTER\s+TABLE\b.*\bDROP\b', "ALTER TABLE DROP komutu"),
        (r'\bUPDATE\s+STATISTICS\b.*\bWITH\s+FULLSCAN\b', "FULLSCAN uzun sürebilir"),
        (r'\bDBCC\s+', "DBCC komutu - production'da dikkatli kullanın"),
        (r'\bWITH\s*\(\s*NOLOCK\s*\)', "NOLOCK hint - dirty read riski"),
        (r'\bOPTION\s*\(\s*RECOMPILE\s*\)', "RECOMPILE - sık çağrılırsa CPU artışı"),
        (r'\bWITH\s*\(\s*ONLINE\s*=\s*OFF\s*\)', "ONLINE=OFF - tablo kilitlenecek"),
    ]
    
    # İyi pratikler (olması gereken)
    BEST_PRACTICES = [
        (r'\bSET\s+NOCOUNT\s+ON\b', "SET NOCOUNT ON kullanımı", 5),
        (r'\bBEGIN\s+TRY\b', "Error handling (TRY-CATCH)", 10),
        (r'\bBEGIN\s+TRANSACTION\b', "Transaction kullanımı", 5),
        (r'--.*comment|/\*.*\*/', "Yorum satırları", 3),
        (r'\bCREATE\s+(NONCLUSTERED\s+)?INDEX\b', "Index önerisi içeriyor", 10),
    ]
    
    # Kötü pratikler (olmaması gereken)
    ANTI_PATTERNS = [
        (r'\bSELECT\s+\*\s+FROM\b', "SELECT * kullanımı", -5),
        (r'\bCURSOR\b', "CURSOR kullanımı", -8),
        (r'\bWHILE\s+@@FETCH_STATUS', "CURSOR loop", -10),
        (r'\bsp_executesql\b.*\+.*@', "Potansiyel SQL injection", -15),
        (r'\bEXEC\s*\(\s*@', "Dynamic SQL (dikkatli kullanın)", -5),
        (r"N?'[^']*'\s*\+\s*@", "String concatenation with variable", -8),
    ]
    
    def __init__(self, strict_mode: bool = False):
        """
        Args:
            strict_mode: True ise uyarılar da engellenir
        """
        self.strict_mode = strict_mode
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Regex pattern'ları derle"""
        self._critical_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self.CRITICAL_BLOCKED_COMMANDS
        ]
        
        self._warning_patterns = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE), msg)
            for p, msg in self.WARNING_COMMANDS
        ]
        
        self._best_practice_patterns = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE), msg, score)
            for p, msg, score in self.BEST_PRACTICES
        ]
        
        self._anti_pattern_patterns = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE), msg, score)
            for p, msg, score in self.ANTI_PATTERNS
        ]
    
    def validate(self, response: str) -> ValidationResult:
        """
        AI response'u doğrula ve sanitize et
        
        Args:
            response: AI tarafından üretilen yanıt
            
        Returns:
            ValidationResult with issues and sanitized response
        """
        result = ValidationResult(
            is_valid=True,
            danger_level=DangerLevel.SAFE,
            sanitized_response=response
        )
        
        if not response or not response.strip():
            result.is_valid = False
            result.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="Empty",
                message="Boş yanıt"
            ))
            return result
        
        # 1. Kritik komut kontrolü
        self._check_critical_commands(response, result)
        
        # 2. Uyarı gerektiren komutlar
        self._check_warning_commands(response, result)
        
        # 3. Best practice kontrolü
        self._check_best_practices(response, result)
        
        # 4. Anti-pattern kontrolü
        self._check_anti_patterns(response, result)
        
        # 5. SQL syntax temel kontrolü
        self._check_sql_syntax(response, result)
        
        # 6. Kalite skoru hesapla
        result.quality_score = self._calculate_quality_score(response, result)
        
        # 7. Sanitize (tehlikeli kısımları işaretle/kaldır)
        result.sanitized_response = self._sanitize_response(response, result)
        
        # Sonuç değerlendirmesi
        if result.has_critical_issues:
            result.is_valid = False
            result.danger_level = DangerLevel.CRITICAL
        elif result.warning_count > 3:
            result.danger_level = DangerLevel.MEDIUM
        elif result.warning_count > 0:
            result.danger_level = DangerLevel.LOW
        
        if self.strict_mode and result.warning_count > 0:
            result.is_valid = False
        
        return result
    
    def _check_critical_commands(self, response: str, result: ValidationResult) -> None:
        """Kritik tehlikeli komutları kontrol et"""
        for pattern in self._critical_patterns:
            matches = pattern.findall(response)
            if matches:
                for match in matches:
                    cmd = match if isinstance(match, str) else match[0]
                    result.blocked_commands.append(cmd.strip())
                    result.issues.append(ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        category="DangerousCommand",
                        message=f"Tehlikeli komut tespit edildi: {cmd}",
                        blocked=True
                    ))
    
    def _check_warning_commands(self, response: str, result: ValidationResult) -> None:
        """Uyarı gerektiren komutları kontrol et"""
        for pattern, message in self._warning_patterns:
            if pattern.search(response):
                result.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="PotentialRisk",
                    message=message,
                    suggestion="Production ortamında dikkatli kullanın"
                ))
    
    def _check_best_practices(self, response: str, result: ValidationResult) -> None:
        """Best practice kontrolü"""
        # SQL kod blokları içinde kontrol et
        sql_blocks = re.findall(r'```sql(.*?)```', response, re.DOTALL | re.IGNORECASE)
        sql_content = '\n'.join(sql_blocks) if sql_blocks else response
        
        for pattern, message, _ in self._best_practice_patterns:
            if pattern.search(sql_content):
                result.issues.append(ValidationIssue(
                    severity=ValidationSeverity.INFO,
                    category="BestPractice",
                    message=f"✅ {message}"
                ))
    
    def _check_anti_patterns(self, response: str, result: ValidationResult) -> None:
        """Anti-pattern kontrolü"""
        sql_blocks = re.findall(r'```sql(.*?)```', response, re.DOTALL | re.IGNORECASE)
        sql_content = '\n'.join(sql_blocks) if sql_blocks else response
        
        for pattern, message, _ in self._anti_pattern_patterns:
            if pattern.search(sql_content):
                result.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="AntiPattern",
                    message=f"⚠️ Anti-pattern: {message}",
                    suggestion="Daha iyi bir alternatif kullanmayı düşünün"
                ))
    
    def _check_sql_syntax(self, response: str, result: ValidationResult) -> None:
        """Temel SQL syntax kontrolü"""
        sql_blocks = re.findall(r'```sql(.*?)```', response, re.DOTALL | re.IGNORECASE)
        
        for sql in sql_blocks:
            # Açılmamış parantez kontrolü
            open_parens = sql.count('(')
            close_parens = sql.count(')')
            if open_parens != close_parens:
                result.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="SyntaxWarning",
                    message=f"Parantez dengesi bozuk: {open_parens} açık, {close_parens} kapalı"
                ))
            
            # Tek tırnak kontrolü (string'ler için)
            # Basit kontrol - '' escape'leri göz ardı ediliyor
            quotes = re.findall(r"'(?:[^']|'')*'", sql)
            remaining = re.sub(r"'(?:[^']|'')*'", '', sql)
            if remaining.count("'") > 0:
                result.issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="SyntaxWarning",
                    message="Kapatılmamış string literal olabilir"
                ))
    
    def _calculate_quality_score(self, response: str, result: ValidationResult) -> float:
        """Kalite skoru hesapla (0-100)"""
        score = 50.0  # Başlangıç
        
        # Best practices bonus
        sql_blocks = re.findall(r'```sql(.*?)```', response, re.DOTALL | re.IGNORECASE)
        sql_content = '\n'.join(sql_blocks) if sql_blocks else response
        
        for pattern, _, bonus in self._best_practice_patterns:
            if pattern.search(sql_content):
                score += bonus
        
        # Anti-patterns penalty
        for pattern, _, penalty in self._anti_pattern_patterns:
            if pattern.search(sql_content):
                score += penalty  # penalty zaten negatif
        
        # Issue-based adjustments
        for issue in result.issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                score -= 30
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 5
        
        # İçerik kalitesi
        if len(response) > 500:
            score += 5  # Detaylı yanıt
        if '```sql' in response:
            score += 10  # Kod bloğu içeriyor
        if '| ' in response and ' |' in response:
            score += 5  # Tablo formatı
        if re.search(r'(P1|P2|P3|Öncelik|Priority)', response, re.IGNORECASE):
            score += 5  # Önceliklendirme içeriyor
        if re.search(r'(\d+%|\d+\s*ms)', response):
            score += 5  # Metrikler içeriyor
        
        # Sınırla
        return max(0.0, min(100.0, score))
    
    def _sanitize_response(self, response: str, result: ValidationResult) -> str:
        """Tehlikeli kısımları işaretle veya kaldır"""
        sanitized = response
        
        for cmd in result.blocked_commands:
            # Tehlikeli komutu işaretle
            pattern = re.compile(re.escape(cmd), re.IGNORECASE)
            sanitized = pattern.sub(f"[⚠️ BLOCKED: {cmd}]", sanitized)
        
        return sanitized
    
    def validate_index_syntax(self, sql: str) -> Tuple[bool, str]:
        """CREATE INDEX syntax doğrulaması"""
        pattern = r'''
            CREATE\s+
            (UNIQUE\s+)?
            (CLUSTERED\s+|NONCLUSTERED\s+)?
            INDEX\s+
            \[?\w+\]?\s+
            ON\s+
            \[?\w+\]?\.\[?\w+\]?\s*
            \([^)]+\)
        '''
        
        if re.search(pattern, sql, re.IGNORECASE | re.VERBOSE):
            return True, "Geçerli CREATE INDEX syntax"
        return False, "Geçersiz veya eksik CREATE INDEX syntax"
    
    def validate_sp_syntax(self, sql: str) -> Tuple[bool, str]:
        """CREATE/ALTER PROCEDURE syntax doğrulaması"""
        pattern = r'''
            (CREATE|ALTER)\s+
            (PROC|PROCEDURE)\s+
            \[?\w+\]?(\.\[?\w+\])?\s*
            (
                \(@?\w+\s+\w+.*\)\s*
            )?
            AS\s+
            BEGIN
        '''
        
        if re.search(pattern, sql, re.IGNORECASE | re.VERBOSE | re.DOTALL):
            return True, "Geçerli PROCEDURE syntax"
        return False, "Geçersiz veya eksik PROCEDURE syntax"


class ResponseQualityChecker:
    """
    AI yanıt kalitesini ölçen yardımcı sınıf
    """
    
    @staticmethod
    def check_completeness(response: str) -> Dict[str, bool]:
        """Yanıtın tamlık kontrolü"""
        checks = {
            "has_analysis": bool(re.search(r'(analiz|analysis|tespit|darboğaz)', response, re.IGNORECASE)),
            "has_recommendation": bool(re.search(r'(öneri|recommendation|tavsiye|yapılmalı)', response, re.IGNORECASE)),
            "has_sql_code": '```sql' in response.lower(),
            "has_metrics": bool(re.search(r'\d+\s*(ms|%|MB|KB|saniye)', response)),
            "has_priority": bool(re.search(r'(P1|P2|P3|öncelik|priority)', response, re.IGNORECASE)),
            "has_impact": bool(re.search(r'(kazanım|impact|etkisi|iyileşme)', response, re.IGNORECASE)),
        }
        return checks
    
    @staticmethod
    def calculate_readability(response: str) -> float:
        """Okunabilirlik skoru (0-100)"""
        score = 50.0
        
        # Markdown formatlaması
        if '##' in response:
            score += 10
        if '```' in response:
            score += 10
        if '|' in response:  # Tablo
            score += 10
        if '- ' in response or '* ' in response:  # Liste
            score += 5
        
        # Emoji kullanımı (görsellik)
        if re.search(r'[✅⚠️❌📈🔧💡🔍📊]', response):
            score += 5
        
        # Paragraf yapısı
        paragraphs = response.split('\n\n')
        if len(paragraphs) >= 3:
            score += 5
        
        return min(100.0, score)


# Shortcut functions
def validate_response(response: str, strict: bool = False) -> ValidationResult:
    """Shortcut for validation"""
    validator = AIResponseValidator(strict_mode=strict)
    return validator.validate(response)


def sanitize_response(response: str) -> str:
    """Shortcut for sanitization only"""
    result = validate_response(response)
    return result.sanitized_response


def get_quality_score(response: str) -> float:
    """Shortcut for quality score"""
    result = validate_response(response)
    return result.quality_score
