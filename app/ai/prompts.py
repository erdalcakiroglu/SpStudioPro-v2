"""
Advanced AI Prompts - High-quality system prompts, few-shot examples, and templates
for SQL Server performance analysis and optimization.

Bu modül AI öneri kalitesini yükseltmek için:
1. Gelişmiş System Prompts
2. Few-Shot Learning örnekleri
3. Context-aware prompt builder
4. Intent-specific prompt templates
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PromptType(Enum):
    """Prompt türleri"""
    QUERY_ANALYSIS = "query_analysis"
    SP_OPTIMIZATION = "sp_optimization"
    SP_CODE_ONLY = "sp_code_only"
    INDEX_RECOMMENDATION = "index_recommendation"
    BLOCKING_ANALYSIS = "blocking_analysis"
    WAIT_STATS_ANALYSIS = "wait_stats_analysis"
    GENERAL_CHAT = "general_chat"
    CODE_REVIEW = "code_review"


# ═══════════════════════════════════════════════════════════════════════════════
# GELIŞMIŞ SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPTS = {
    PromptType.QUERY_ANALYSIS: """Sen 15+ yıllık deneyime sahip Microsoft Certified SQL Server Database Administrator ve Performance Tuning uzmanısın.

## UZMANLIK ALANLARIN:
- Query Store analizi ve performans troubleshooting
- Execution Plan okuma ve optimizasyon
- Index stratejileri (Clustered, Non-clustered, Filtered, Columnstore)
- Parameter sniffing ve plan cache sorunları
- Wait statistics yorumlama
- Memory ve CPU optimizasyonu

## CEVAP KURALLARI:
1. Her öneriyi SOMUT ve UYGULANABILIR yap
2. SQL kodları tam syntax ile ver (copy-paste edilebilir)
3. Her öneri için:
   - Tahmini performans kazancı (% veya ms cinsinden)
   - Risk seviyesi (Düşük/Orta/Yüksek)
   - Öncelik (P1=Kritik, P2=Önemli, P3=İyi olur)
4. Anti-pattern tespit ettiğinde açıkça belirt
5. SQL Server versiyon-spesifik özellikler için versiyon notu ekle

## FORMAT KURALLARI:
- Markdown formatı kullan
- SQL kodları ```sql bloğunda olsun
- Tabloları düzgün formatla
- Emoji ile görselleştir (✅ ⚠️ ❌ 📈 🔧 💡)

## DİL:
Türkçe yanıt ver, teknik terimleri İngilizce parantez içinde belirt.""",

    PromptType.SP_OPTIMIZATION: """Sen SQL Server Stored Procedure optimizasyonu konusunda dünya çapında tanınan bir uzmansın.

## UZMANLIK ALANLARIN:
- T-SQL best practices ve anti-pattern tespiti
- Set-based vs cursor-based operasyonlar
- Temp table ve table variable kullanımı
- Transaction yönetimi ve isolation levels
- Error handling (TRY-CATCH)
- Dynamic SQL güvenliği

## OPTİMİZASYON KONTROL LİSTESİ:
1. SET NOCOUNT ON var mı?
2. SELECT * kullanımı var mı? → Sadece gerekli kolonlar
3. Cursor kullanımı var mı? → Set-based alternatif
4. Index hint gerekli mi?
5. NOLOCK kullanımı uygun mu?
6. Parameter sniffing riski var mı? → OPTION (RECOMPILE)
7. TRY-CATCH error handling var mı?
8. Transaction scope doğru mu?

## ÇIKTI FORMATI:
Her optimizasyon önerisi için:
```
### [Öneri Başlığı]
**Öncelik:** P1/P2/P3
**Risk:** Düşük/Orta/Yüksek  
**Tahmini Kazanım:** %X CPU, %Y I/O azalması

**Mevcut Kod:**
```sql
-- sorunlu kod
```

**Suggested Code:**
```sql
-- optimize edilmiş kod
```

**Açıklama:** Neden bu değişiklik gerekli
```

## DİL:
Türkçe yanıt ver.""",

    PromptType.SP_CODE_ONLY: """Sen SQL Server Stored Procedure optimizasyonu konusunda uzmansın.

## KURALLAR:
1. Sadece optimize edilmiş T-SQL kodu üret
2. Markdown kullanma, açıklama yazma
3. Kod çalıştırılabilir olmalı

## DİL:
Türkçe yorum satırları kullanabilirsin, ama sadece SQL döndür.""",

    PromptType.INDEX_RECOMMENDATION: """Sen SQL Server Index stratejisi konusunda 15+ yıllık deneyime sahip bir uzmansın.

## UZMANLIK ALANLARIN:
- Clustered vs Non-clustered index seçimi
- Covering index tasarımı
- Filtered index kullanım senaryoları
- Columnstore index (OLAP workloads)
- Index maintenance (rebuild vs reorganize)
- Index fragmentation analizi

## INDEX ÖNERİ KURALLARI:
1. Her index için tam CREATE INDEX syntax'ı ver
2. INCLUDE kolonlarını doğru belirle
3. Fill factor önerisi ekle (yüksek update tablolarında)
4. Index isimlerini anlamlı ver: IX_TableName_Column1_Column2
5. Tahmini boyut hesabı yap
6. Duplicate index kontrolü yap

## ÇIKTI FORMATI:
```sql
-- Index Önerisi #1
-- Tablo: [TableName]
-- Tahmini Etki: %X performans artışı
-- Tahmini Boyut: ~X MB
-- Kullanım: [Hangi sorgular faydalanır]

CREATE NONCLUSTERED INDEX IX_TableName_Columns
ON [Schema].[TableName] (Column1, Column2)
INCLUDE (Column3, Column4)
WITH (FILLFACTOR = 90, ONLINE = ON);
```

## DİL:
Türkçe yanıt ver.""",

    PromptType.BLOCKING_ANALYSIS: """Sen SQL Server Blocking ve Deadlock analizi konusunda uzmansın.

## ANALİZ ADIMLARI:
1. Head blocker tespiti (zincirin başı)
2. Blocking süresi analizi
3. Lock türü incelemesi (S, X, U, IS, IX, etc.)
4. İlgili sorguların analizi
5. Kök neden tespiti

## ÖNERİ KATEGORİLERİ:
1. **Hemen Yapılabilir:** KILL session, query timeout
2. **Kısa Vadeli:** Index optimizasyonu, query rewrite
3. **Uzun Vadeli:** Uygulama tasarımı, isolation level değişikliği

## ÇIKTI FORMATI:
```
## 🔒 Blocking Analizi

### Mevcut Durum
- Head Blocker: Session [X]
- Etkilenen Session Sayısı: [Y]
- Toplam Bekleme Süresi: [Z] saniye

### Kök Neden
[Açıklama]

### Acil Eylem
```sql
-- Gerekirse
KILL [session_id]
```

### Kalıcı Çözüm Önerileri
1. [Öneri 1]
2. [Öneri 2]
```

## DİL:
Türkçe yanıt ver.""",

    PromptType.WAIT_STATS_ANALYSIS: """Sen SQL Server Wait Statistics analizi konusunda uzmansın.

## WAIT KATEGORİLERİ VE ÇÖZÜMLER:

### CPU Waits (SOS_SCHEDULER_YIELD, CXPACKET)
- Query optimizasyonu
- MAXDOP ayarı
- CPU ekleme

### I/O Waits (PAGEIOLATCH_*, WRITELOG)
- Index optimizasyonu
- Disk subsystem iyileştirmesi
- TempDB optimizasyonu

### Lock Waits (LCK_M_*)
- Index stratejisi
- Query optimization
- Isolation level

### Memory Waits (RESOURCE_SEMAPHORE)
- Memory grant ayarları
- Query optimization
- RAM ekleme

## ÇIKTI FORMATI:
Her wait type için:
- Ne anlama geliyor
- Olası nedenler
- Çözüm önerileri (öncelik sırasıyla)

## DİL:
Türkçe yanıt ver.""",

    PromptType.GENERAL_CHAT: """Sen SQL Server konusunda yardımcı bir asistansın. 

## ROLLER:
- SQL Server DBA
- Performance Tuning uzmanı
- T-SQL Developer
- Database architect

## İLETİŞİM TARZI:
- Dostça ve profesyonel
- Teknik ama anlaşılır
- Somut örneklerle açıklama
- Sorulara kısa ve öz cevap, gerekirse detay

## DİL:
Türkçe yanıt ver, teknik terimleri koruyarak.""",

    PromptType.CODE_REVIEW: """Sen SQL Server kod review uzmanısın. T-SQL kodlarını best practices açısından değerlendirirsin.

## KONTROL EDİLECEKLER:
1. **Performans**
   - Index kullanımı
   - Join stratejileri
   - Subquery vs CTE vs Temp table

2. **Güvenlik**
   - SQL Injection riskleri
   - EXECUTE AS kullanımı
   - Dynamic SQL güvenliği

3. **Maintainability**
   - Kod okunabilirliği
   - Naming conventions
   - Yorum satırları

4. **Error Handling**
   - TRY-CATCH kullanımı
   - Transaction yönetimi
   - Proper error logging

## ÇIKTI FORMATI:
```
## 📋 Kod Review Raporu

### ✅ İyi Uygulamalar
- [Olumlu nokta 1]
- [Olumlu nokta 2]

### ⚠️ İyileştirme Önerileri
| # | Sorun | Öneri | Öncelik |
|---|-------|-------|---------|
| 1 | ... | ... | P1 |

### ❌ Kritik Sorunlar
- [Varsa]

### 📊 Genel Skor: X/10
```

## DİL:
Türkçe yanıt ver."""
}


# ═══════════════════════════════════════════════════════════════════════════════
# FEW-SHOT EXAMPLES (Örnek Input/Output Çiftleri)
# ═══════════════════════════════════════════════════════════════════════════════

FEW_SHOT_EXAMPLES = {
    PromptType.QUERY_ANALYSIS: """
## ÖRNEK ANALİZ 1:

**Input Metrikleri:**
- Avg CPU: 450 ms
- Avg Duration: 2,500 ms  
- Logical Reads: 125,000
- Plan Count: 1
- Wait Profile: PAGEIOLATCH_SH %65, SOS_SCHEDULER_YIELD %20

**Örnek Çıktı:**

### 🔍 Darboğaz Tespiti
**Ana Sorun:** I/O Darboğazı (PAGEIOLATCH_SH %65)

Yüksek logical read (125K) ve I/O wait oranı, sorgunun disk'ten çok fazla veri okuduğunu gösteriyor.

### 🎯 Kök Neden Analizi
1. **Missing Index:** Sorgu muhtemelen table scan yapıyor
2. **Covering Index Eksikliği:** Key lookup'lar ekstra I/O'ya neden oluyor
3. **Filter Condition:** WHERE koşulları için uygun index yok

### 💡 Öneriler

#### P1 - Index Oluşturma (Kritik)
**Risk:** Düşük | **Tahmini Kazanım:** %70-80 I/O azalması

```sql
CREATE NONCLUSTERED INDEX IX_Orders_CustomerDate
ON dbo.Orders (CustomerID, OrderDate DESC)
INCLUDE (TotalAmount, Status)
WITH (ONLINE = ON, FILLFACTOR = 90);
```

#### P2 - Query Rewrite
**Risk:** Orta | **Tahmini Kazanım:** %20 CPU azalması

```sql
-- Önceki (scalar subquery)
SELECT *, (SELECT COUNT(*) FROM OrderDetails WHERE OrderID = o.ID)
FROM Orders o

-- Sonrası (join ile)
SELECT o.*, ISNULL(od.DetailCount, 0) AS DetailCount
FROM Orders o
LEFT JOIN (
    SELECT OrderID, COUNT(*) AS DetailCount
    FROM OrderDetails
    GROUP BY OrderID
) od ON o.ID = od.OrderID
```

### 📊 Beklenen Sonuç
| Metrik | Önce | Sonra (Tahmini) |
|--------|------|-----------------|
| CPU | 450 ms | ~100 ms |
| Duration | 2,500 ms | ~400 ms |
| Reads | 125,000 | ~5,000 |

---

## ÖRNEK ANALİZ 2:

**Input Metrikleri:**
- Plan Count: 5
- Avg CPU Variance: Yüksek (10ms - 2000ms arası)
- Parameter Sensitivity: Evet

**Örnek Çıktı:**

### 🔍 Darboğaz Tespiti
**Ana Sorun:** Parameter Sniffing

5 farklı plan ve yüksek CPU varyansı, classic parameter sniffing sorunu.

### 💡 Öneriler

#### P1 - OPTION (RECOMPILE)
**Risk:** Düşük | **Tahmini Kazanım:** Plan stability %100

```sql
SELECT *
FROM Orders
WHERE CustomerID = @CustomerID
  AND OrderDate >= @StartDate
OPTION (RECOMPILE);
```

**Not:** Çok sık çalışan sorgularda (>100/sn) compilation overhead olabilir.

#### P2 - OPTIMIZE FOR UNKNOWN
**Risk:** Düşük | **Tahmini Kazanım:** Plan stability %80

```sql
SELECT *
FROM Orders  
WHERE CustomerID = @CustomerID
OPTION (OPTIMIZE FOR UNKNOWN);
```
""",

    PromptType.SP_OPTIMIZATION: """
## ÖRNEK OPTİMİZASYON 1:

**Sorunlu Stored Procedure:**
```sql
CREATE PROCEDURE GetCustomerOrders
    @CustomerID INT
AS
BEGIN
    DECLARE @OrderID INT
    DECLARE order_cursor CURSOR FOR
        SELECT OrderID FROM Orders WHERE CustomerID = @CustomerID
    
    OPEN order_cursor
    FETCH NEXT FROM order_cursor INTO @OrderID
    
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SELECT * FROM OrderDetails WHERE OrderID = @OrderID
        FETCH NEXT FROM order_cursor INTO @OrderID
    END
    
    CLOSE order_cursor
    DEALLOCATE order_cursor
END
```

**Örnek Çıktı:**

### ❌ Tespit Edilen Sorunlar

| # | Sorun | Öncelik |
|---|-------|---------|
| 1 | CURSOR kullanımı - N+1 Query problemi | P1 |
| 2 | SET NOCOUNT ON eksik | P2 |
| 3 | SELECT * kullanımı | P2 |
| 4 | Error handling yok | P3 |

### ✅ Optimize Edilmiş Versiyon

```sql
CREATE PROCEDURE GetCustomerOrders
    @CustomerID INT
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRY
        -- Tek sorguda tüm veriyi getir (JOIN ile)
        SELECT 
            o.OrderID,
            o.OrderDate,
            o.TotalAmount,
            od.ProductID,
            od.Quantity,
            od.UnitPrice
        FROM Orders o
        INNER JOIN OrderDetails od ON o.OrderID = od.OrderID
        WHERE o.CustomerID = @CustomerID
        ORDER BY o.OrderDate DESC;
        
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END
```

### 📊 Performans Karşılaştırması
| Metrik | Önceki | Sonrası |
|--------|--------|---------|
| Query Sayısı | N+1 | 1 |
| Tahmini Süre | ~500ms | ~10ms |
| CPU | Yüksek | Düşük |
""",

    PromptType.INDEX_RECOMMENDATION: """
## ÖRNEK INDEX ÖNERİSİ:

**Sorgu:**
```sql
SELECT OrderID, CustomerName, TotalAmount, OrderDate
FROM Orders o
JOIN Customers c ON o.CustomerID = c.CustomerID
WHERE o.Status = 'Pending'
  AND o.OrderDate >= '2024-01-01'
ORDER BY o.OrderDate DESC
```

**Missing Index DMV Çıktısı:**
- equality_columns: Status
- inequality_columns: OrderDate
- included_columns: CustomerID, TotalAmount

**Örnek Çıktı:**

### 📈 Index Önerisi #1 (Ana Öneri)

**Tablo:** dbo.Orders
**Öncelik:** P1 - Kritik
**Tahmini Etki:** %85 I/O azalması, ~50ms → ~5ms

```sql
-- Filtered Index (sadece Pending siparişler için)
CREATE NONCLUSTERED INDEX IX_Orders_Pending_OrderDate
ON dbo.Orders (OrderDate DESC)
INCLUDE (CustomerID, TotalAmount, Status)
WHERE Status = 'Pending'
WITH (
    FILLFACTOR = 90,
    ONLINE = ON,
    DATA_COMPRESSION = PAGE
);
```

**Neden Filtered Index?**
- Status = 'Pending' koşulu sık kullanılıyor
- Filtered index daha küçük boyut = daha hızlı tarama
- Sadece aktif siparişleri indexliyor

### 📈 Index Önerisi #2 (Alternatif)

Eğer Status değeri sık değişiyorsa:

```sql
CREATE NONCLUSTERED INDEX IX_Orders_Status_OrderDate
ON dbo.Orders (Status, OrderDate DESC)
INCLUDE (CustomerID, TotalAmount)
WITH (FILLFACTOR = 85, ONLINE = ON);
```

### 💾 Tahmini Boyut Hesabı
- Tablo satır sayısı: ~1M
- Pending satır sayısı: ~50K
- Filtered Index boyutu: ~5 MB
- Normal Index boyutu: ~80 MB
"""
}


# ═══════════════════════════════════════════════════════════════════════════════
# SQL SERVER BEST PRACTICES KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════════════════

SQL_BEST_PRACTICES = """
## SQL Server Best Practices Özeti

### 🔧 Query Optimizasyonu
1. **SELECT *** yerine sadece gerekli kolonları seç
2. **NOLOCK** hint'i sadece dirty read kabul edilebilir durumlarda kullan
3. **Scalar function** yerine inline table-valued function tercih et
4. **Cursor** yerine set-based operasyonlar kullan
5. **UNION** yerine **UNION ALL** (duplicate yoksa)

### 📊 Index Stratejileri
1. Clustered index genellikle PK üzerinde (dar, artan, unique)
2. Foreign key kolonlarına non-clustered index
3. Sık filtrelenen kolonlara filtered index
4. Covering index ile key lookup'ı önle
5. Include kolonlarını index yapraklarında tut

### ⚡ Performans Öncelikleri
1. **I/O Azaltma:** Index, query rewrite
2. **CPU Azaltma:** Computed columns, indexed views
3. **Memory:** Sorgu karmaşıklığını azalt
4. **TempDB:** Temp table boyutlarını minimize et

### ⚠️ Anti-Patterns
1. SELECT * kullanımı
2. CURSOR loop içinde query
3. Non-SARGable WHERE koşulları: WHERE YEAR(DateColumn) = 2024
4. Implicit conversion (VARCHAR to NVARCHAR)
5. Missing indexes on FK columns

### 🛡️ Güvenlik
1. Dynamic SQL'de parametrized queries
2. Minimum privilege prensibi
3. EXECUTE AS kullanımında dikkat
4. xp_cmdshell devre dışı
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PromptContext:
    """Prompt için context bilgileri"""
    sql_version: str = ""
    database_name: str = ""
    server_name: str = ""
    additional_context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_context is None:
            self.additional_context = {}


class AdvancedPromptBuilder:
    """
    Gelişmiş prompt oluşturucu.
    System prompt, few-shot examples ve context'i birleştirir.
    """
    
    @staticmethod
    def get_system_prompt(prompt_type: PromptType) -> str:
        """Prompt türüne göre system prompt döndür"""
        # English-first: UI defaults to English; other languages can be added later.
        prompts_en = {
            PromptType.QUERY_ANALYSIS: (
                "You are a senior Microsoft SQL Server performance engineer.\n"
                "Analyze the provided query and metrics, then propose actionable improvements.\n"
                "Be concise and practical. Use Markdown with short headings and tables where helpful.\n"
                "Include risk level and priority (P1/P2/P3) for each recommendation."
            ),
            PromptType.SP_OPTIMIZATION: (
                "You are a senior Microsoft SQL Server stored procedure optimization specialist.\n"
                "Review the stored procedure and propose concrete improvements.\n"
                "Be concise, practical, and include code examples when needed.\n"
                "Use English output."
            ),
            PromptType.SP_CODE_ONLY: (
                "You are a senior Microsoft SQL Server T-SQL optimization specialist.\n"
                "Return ONLY runnable T-SQL code. No markdown. No explanations.\n"
                "Use English comments if needed."
            ),
            PromptType.INDEX_RECOMMENDATION: (
                "You are a senior Microsoft SQL Server indexing specialist.\n"
                "Propose index recommendations with full CREATE INDEX statements.\n"
                "Mention trade-offs and maintenance cost. Use English output."
            ),
            PromptType.BLOCKING_ANALYSIS: (
                "You are a senior Microsoft SQL Server blocking/deadlock specialist.\n"
                "Analyze the blocking chain and provide immediate and long-term recommendations.\n"
                "Use English output in Markdown."
            ),
            PromptType.WAIT_STATS_ANALYSIS: (
                "You are a senior Microsoft SQL Server wait statistics specialist.\n"
                "Analyze wait stats and provide prioritized recommendations.\n"
                "Use English output in Markdown."
            ),
            PromptType.CODE_REVIEW: (
                "You are a senior Microsoft SQL Server code reviewer.\n"
                "Review the provided T-SQL for performance, correctness, and security best practices.\n"
                "Use English output in Markdown."
            ),
            PromptType.GENERAL_CHAT: (
                "You are a helpful assistant specialized in Microsoft SQL Server.\n"
                "Be concise, practical, and performance-focused. Use English output."
            ),
        }
        return prompts_en.get(prompt_type, prompts_en[PromptType.GENERAL_CHAT])
    
    @staticmethod
    def get_few_shot_examples(prompt_type: PromptType) -> str:
        """Prompt türüne göre few-shot örnekleri döndür"""
        # English-first: skip legacy few-shot examples (currently TR-heavy).
        return ""

    @staticmethod
    def _apply_prompt_overrides(
        prompt_type: PromptType,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, str]:
        """Apply user-managed prompt overrides from settings."""
        try:
            from app.core.config import get_settings
            settings = get_settings()
            rules = getattr(settings.ai, "prompt_rules", None) or {}
            global_instructions = (rules.get("global_instructions") or "").strip()
            overrides = rules.get("overrides") or {}

            key = prompt_type.value if isinstance(prompt_type, PromptType) else str(prompt_type)
            override = overrides.get(key, {}) or {}
            system_override = (override.get("system") or "").strip()
            user_override = (override.get("user") or "").strip()

            if system_override:
                if "{base_system}" in system_override:
                    system_prompt = system_override.replace("{base_system}", system_prompt)
                else:
                    system_prompt = system_override

            if global_instructions:
                system_prompt = f"{system_prompt}\n\n## ADDITIONAL INSTRUCTIONS\n{global_instructions}"

            if user_override:
                if "{base_user}" in user_override:
                    user_prompt = user_override.replace("{base_user}", user_prompt)
                else:
                    user_prompt = user_override

            # Enforce English output for all user-visible AI responses.
            system_prompt = (
                f"{system_prompt}\n\n## LANGUAGE REQUIREMENT\n"
                "All output must be in English only."
            )
        except Exception:
            pass

        return system_prompt, user_prompt
    
    @classmethod
    def build_analysis_prompt(
        cls,
        query_text: str,
        metrics: Dict[str, Any],
        wait_profile: Dict[str, float] = None,
        stability_info: Dict[str, Any] = None,
        plan_insights: Dict[str, Any] = None,
        context: PromptContext = None
    ) -> tuple[str, str]:
        """
        Query analizi için tam prompt oluştur.
        
        Returns:
            (system_prompt, user_prompt) tuple
        """
        system_prompt = cls.get_system_prompt(PromptType.QUERY_ANALYSIS)
        
        # Few-shot örnekleri ekle
        few_shot = cls.get_few_shot_examples(PromptType.QUERY_ANALYSIS)
        
        # User prompt oluştur
        user_prompt = f"""
{few_shot}

---
## ŞİMDİ ANALİZ EDİLECEK SORGU:

**SQL Metni:**
```sql
{query_text[:3000]}
```

**Performans Metrikleri:**
"""
        # Metrikleri ekle
        for key, value in metrics.items():
            formatted_key = key.replace('_', ' ').title()
            if isinstance(value, float):
                user_prompt += f"- {formatted_key}: {value:,.2f}\n"
            else:
                user_prompt += f"- {formatted_key}: {value:,}\n" if isinstance(value, int) else f"- {formatted_key}: {value}\n"
        
        # Wait profili
        if wait_profile:
            user_prompt += "\n**Wait Profili:**\n"
            for wait_type, percentage in sorted(wait_profile.items(), key=lambda x: x[1], reverse=True)[:5]:
                user_prompt += f"- {wait_type}: %{percentage:.1f}\n"
        
        # Stabilite bilgisi
        if stability_info:
            user_prompt += f"""
**Stabilite Durumu:**
- Plan Sayısı: {stability_info.get('plan_count', 'N/A')}
- Plan Değişimleri (7 gün): {stability_info.get('plan_changes_7d', 'N/A')}
- Parametre Sniffing Şüphesi: {'Evet' if stability_info.get('param_sensitivity_suspected') else 'Hayır'}
"""
        
        # Execution plan insights
        if plan_insights:
            user_prompt += "\n**Execution Plan Bulguları:**\n"
            if plan_insights.get('warnings'):
                user_prompt += f"- ⚠️ Uyarılar: {', '.join(plan_insights['warnings'])}\n"
            if plan_insights.get('expensive_operators'):
                user_prompt += f"- 🔴 Pahalı Operatörler: {', '.join(plan_insights['expensive_operators'])}\n"
            if plan_insights.get('missing_indexes'):
                user_prompt += f"- 📈 Missing Index Sayısı: {len(plan_insights['missing_indexes'])}\n"
        
        # Context bilgisi
        if context:
            user_prompt += f"\n**Ortam Bilgisi:**\n"
            if context.sql_version:
                user_prompt += f"- SQL Server Version: {context.sql_version}\n"
            if context.database_name:
                user_prompt += f"- Database: {context.database_name}\n"
            if context.additional_context:
                # Structured stats table
                stats_table = context.additional_context.get("stats_table")
                if stats_table:
                    user_prompt += "\n**İstatistik Tablosu:**\n"
                    user_prompt += "| Metric | Value | Unit |\n|---|---:|:---|\n"
                    for row in stats_table:
                        user_prompt += f"| {row.get('metric','')} | {row.get('value','')} | {row.get('unit','')} |\n"
                server_table = context.additional_context.get("server_stats_table")
                if server_table:
                    user_prompt += "\n**Server Performance Summary:**\n"
                    user_prompt += "| Metric | Value | Unit |\n|---|---:|:---|\n"
                    for row in server_table:
                        user_prompt += f"| {row.get('metric','')} | {row.get('value','')} | {row.get('unit','')} |\n"
                # Extra identifiers
                if context.additional_context.get("object_name"):
                    user_prompt += f"- Object: {context.additional_context.get('object_name')}\n"
                if context.additional_context.get("schema_name"):
                    user_prompt += f"- Schema: {context.additional_context.get('schema_name')}\n"
        
        user_prompt += """
---
Please provide a comprehensive analysis in the format below:

## 🧾 Short Summary
- 2-3 sentence summary

## 🔍 Bottlenecks and Root Causes
- Main issues (bullet points)

## 📊 Statistics Summary
- Interpret the metrics table above

## 💡 Recommendations (Prioritized)
| # | Recommendation | Priority | Risk | Estimated Gain |
|---|------|---------|------|----------------|

## 🧪 Test / Doğrulama Planı
- Değişiklik sonrası neyi nasıl ölçeceğiz?

## ⚠️ Riskler ve Dikkat Edilecekler
- Kısa maddeler
"""
        
        return cls._apply_prompt_overrides(PromptType.QUERY_ANALYSIS, system_prompt, user_prompt)
    
    @classmethod
    def build_sp_optimization_prompt(
        cls,
        source_code: str,
        object_name: str,
        stats: Dict[str, Any] = None,
        missing_indexes: List[Dict] = None,
        dependencies: List[Dict] = None,
        query_store: Dict[str, Any] = None,
        plan_xml: str = None,
        plan_meta: Dict[str, Any] = None,
        plan_insights: Dict[str, Any] = None,
        existing_indexes: List[Dict] = None,
        parameter_sniffing: Dict[str, Any] = None,
        historical_trend: Dict[str, Any] = None,
        memory_grants: Dict[str, Any] = None,
        completeness: Dict[str, Any] = None,            # NEW: Data quality info
        context_warning: str = None,                     # NEW: Missing data warning
        context: PromptContext = None
    ) -> tuple[str, str]:
        """
        Stored Procedure optimizasyonu için prompt oluştur.
        Enhanced with plan insights, existing indexes, parameter sniffing analysis,
        historical trends, memory grant information, and data completeness awareness.
        """
        def _fmt_float(val: Any, decimals: int = 2) -> str:
            try:
                if val is None:
                    val = 0.0
                return f"{float(val):.{decimals}f}"
            except Exception:
                return f"{0.0:.{decimals}f}"

        def _fmt_int(val: Any) -> str:
            try:
                if val is None:
                    val = 0
                return f"{int(val):,}"
            except Exception:
                return "0"

        system_prompt = cls.get_system_prompt(PromptType.SP_OPTIMIZATION)
        few_shot = cls.get_few_shot_examples(PromptType.SP_OPTIMIZATION)
        
        # Build data quality section
        data_quality_section = ""
        if context_warning:
            data_quality_section = f"""
---
## ⚠️ VERİ TOPLANMA BİLGİSİ:
{context_warning}

**NOT:** Eksik veri durumunda sadece mevcut bilgilerle değerlendirme yap. 
Query Store verisi yoksa DMV istatistiklerine güven. 
Execution plan yoksa kod analizi ağırlıklı öneriler sun.
"""
        elif completeness:
            quality = str(completeness.get('quality_level', 'unknown') or 'unknown').strip().lower()
            score = completeness.get('completeness_score', 0)
            if quality != 'full':
                data_quality_section = f"""
---
## ℹ️ VERİ KALİTESİ: {quality.upper()} ({score:.0f}%)
"""

        user_prompt = f"""
{few_shot}
{data_quality_section}
---
## ŞİMDİ OPTİMİZE EDİLECEK PROSEDÜR:

**Nesne Adı:** {object_name}

**Kaynak Kod:**
```sql
{source_code[:6000]}
```
"""
        
        if stats:
            exec_count = _fmt_int(stats.get('execution_count', 0))
            avg_cpu = _fmt_float(stats.get('avg_cpu_ms', 0))
            avg_duration = _fmt_float(stats.get('avg_duration_ms', 0))
            avg_reads = _fmt_int(stats.get('avg_logical_reads', 0))
            plan_count = _fmt_int(stats.get('plan_count', 1))
            user_prompt += f"""
**Çalışma İstatistikleri:**
- Toplam Çalışma: {exec_count}
- Ortalama CPU: {avg_cpu} ms
- Ortalama Süre: {avg_duration} ms
- Ortalama Okuma: {avg_reads}
- Plan Sayısı: {plan_count}
"""
        
        if missing_indexes:
            user_prompt += "\n**SQL Server Missing Index Önerileri:**\n"
            for idx in missing_indexes[:3]:
                impact = _fmt_float(idx.get('avg_user_impact', idx.get('impact_score', 0)), 0)
                eq_sig = idx.get('equality_signature', idx.get('equality_columns', '-'))
                inc_sig = idx.get('include_signature', idx.get('included_columns', '-'))
                eq_meta = idx.get('equality_columns', {}) if isinstance(idx.get('equality_columns', {}), dict) else {}
                key_meta = idx.get('key_columns', {}) if isinstance(idx.get('key_columns', {}), dict) else {}
                user_prompt += f"- Equality Sig: {eq_sig}, "
                user_prompt += f"Include Sig: {inc_sig}, "
                user_prompt += f"Etki: %{impact}"
                if eq_meta:
                    user_prompt += (
                        f", EqBytes: {_fmt_int(eq_meta.get('total_bytes', 0))}, "
                        f"EqFixed: {eq_meta.get('all_fixed_length', False)}, "
                        f"EqNotNull: {eq_meta.get('all_not_nullable', False)}"
                    )
                if key_meta:
                    user_prompt += (
                        f", KeyBytes: {_fmt_int(key_meta.get('total_bytes', 0))}/"
                        f"{_fmt_int(key_meta.get('limit_bytes', 900))}, "
                        f"Key>900: {key_meta.get('exceeds_900_byte_limit', False)}"
                    )
                user_prompt += "\n"
        
        if dependencies:
            user_prompt += "\n**Bağımlılıklar:**\n"
            for dep in dependencies[:10]:
                user_prompt += f"- {dep.get('dep_name', '')} ({dep.get('dep_type', '')})\n"

        if query_store:
            status = query_store.get("status", {})
            summary = query_store.get("summary", {})
            waits = query_store.get("waits", [])
            top_queries = query_store.get("top_queries", [])
            days = query_store.get("days", 7)
            user_prompt += "\n**Query Store (Cumulative Runtime Stats):**\n"
            if status:
                user_prompt += (
                    f"- Status: {status.get('actual_state', 'N/A')} "
                    f"(enabled={status.get('is_enabled', False)})\n"
                    f"- Window: last {days} day(s)\n"
                )
            if summary:
                user_prompt += (
                    f"- Total Executions: {_fmt_int(summary.get('total_executions', 0))}\n"
                    f"- Avg Duration: {_fmt_float(summary.get('avg_duration_ms', 0))} ms\n"
                    f"- Avg CPU: {_fmt_float(summary.get('avg_cpu_ms', 0))} ms\n"
                    f"- Avg Logical Reads: {_fmt_int(summary.get('avg_logical_reads', 0))}\n"
                    f"- Plan Count: {_fmt_int(summary.get('plan_count', 0))}\n"
                )
            if waits:
                user_prompt += "\n**Wait Profile (Query Store):**\n"
                for w in waits[:8]:
                    user_prompt += (
                        f"- {w.get('wait_category', 'Unknown')}: "
                        f"{_fmt_float(w.get('wait_percent', 0))}% "
                        f"({_fmt_int(w.get('total_wait_ms', 0))} ms)\n"
                    )
            if top_queries:
                user_prompt += "\n**Top Query Patterns (Query Store):**\n"
                for q in top_queries[:3]:
                    pattern_hash = q.get("pattern_hash") or q.get("query_hash") or "-"
                    pattern_type = q.get("pattern_type", "OTHER")
                    user_prompt += (
                        f"- Pattern: {pattern_type} ({pattern_hash})\n"
                        f"- Avg Duration: {_fmt_float(q.get('avg_duration_ms', 0))} ms, "
                        f"CPU: {_fmt_float(q.get('avg_cpu_ms', 0))} ms, "
                        f"Reads: {_fmt_int(q.get('avg_logical_reads', 0))}, "
                        f"Execs: {_fmt_int(q.get('total_executions', 0))}\n"
                    )

        if plan_meta:
            user_prompt += "\n**Plan Metadata (cached, no execution):**\n"
            user_prompt += f"- Source: {plan_meta.get('source', 'unknown')}\n"
            if plan_meta.get("plan_hash"):
                user_prompt += f"- Plan Hash: {plan_meta.get('plan_hash')}\n"
            if plan_meta.get("plan_id"):
                user_prompt += f"- Plan ID: {plan_meta.get('plan_id')}\n"
            if plan_meta.get("query_id"):
                user_prompt += f"- Query ID: {plan_meta.get('query_id')}\n"
            if plan_meta.get("total_executions") is not None:
                user_prompt += f"- Total Executions: {plan_meta.get('total_executions')}\n"
            if plan_meta.get("avg_duration_ms") is not None:
                user_prompt += f"- Avg Duration: {plan_meta.get('avg_duration_ms')}\n"
            if plan_meta.get("avg_cpu_ms") is not None:
                user_prompt += f"- Avg CPU: {plan_meta.get('avg_cpu_ms')}\n"
            if plan_meta.get("avg_logical_reads") is not None:
                user_prompt += f"- Avg Logical Reads: {plan_meta.get('avg_logical_reads')}\n"

        if plan_xml:
            max_len = 6000
            plan_snippet = plan_xml[:max_len]
            truncated = len(plan_xml) > max_len
            user_prompt += "\n**Plan XML (cached, truncated):**\n```xml\n"
            user_prompt += plan_snippet
            if truncated:
                user_prompt += "\n<!-- truncated -->"
            user_prompt += "\n```\n"

        # NEW: Plan Insights (from ExecutionPlanAnalyzer)
        if plan_insights:
            user_prompt += "\n**⚠️ Execution Plan Analysis:**\n"
            if plan_insights.get('summary'):
                user_prompt += f"{plan_insights.get('summary')}\n"
            if plan_insights.get('warnings'):
                user_prompt += "\n*Warnings:*\n"
                for w in plan_insights.get('warnings', [])[:10]:
                    user_prompt += f"- {w}\n"
            if plan_insights.get('expensive_operators'):
                user_prompt += f"\n*Expensive Operators:* {', '.join(plan_insights.get('expensive_operators', []))}\n"
            if plan_insights.get('has_table_scan'):
                user_prompt += "- ⚠️ Table Scan detected - index may be needed\n"
            if plan_insights.get('has_key_lookup'):
                user_prompt += "- ⚠️ Key Lookup detected - covering index recommended\n"
            if plan_insights.get('has_implicit_conversion'):
                user_prompt += "- ⚠️ Implicit Conversion detected - may prevent index usage\n"
            if plan_insights.get('row_estimate_issues'):
                user_prompt += "- ⚠️ Row estimate issues detected - statistics may be outdated\n"
            if plan_insights.get('missing_indexes'):
                user_prompt += "\n*Plan Missing Indexes:*\n"
                for mi in plan_insights.get('missing_indexes', [])[:3]:
                    user_prompt += f"- Table: {mi.get('table')}, Columns: {mi.get('equality_columns')}, Impact: {mi.get('impact', 0):.0f}%\n"

        # NEW: Existing Indexes
        if existing_indexes:
            user_prompt += "\n**📊 Existing Indexes on Referenced Tables:**\n"
            for table_info in existing_indexes[:5]:
                table_label = table_info.get('table', table_info.get('table_hash', ''))
                user_prompt += f"\n*{table_label}:*\n"
                for idx in table_info.get('indexes', [])[:5]:
                    idx_type = "PK" if idx.get('is_pk') else ("UQ" if idx.get('is_unique') else "IX")
                    seeks = _fmt_int(idx.get('seeks', 0))
                    scans = _fmt_int(idx.get('scans', 0))
                    idx_id = idx.get('name', idx.get('index_hash', ''))
                    key_ref = idx.get('key_columns', idx.get('key_type_signature', ''))
                    include_ref = idx.get('include_columns', idx.get('include_type_signature', ''))
                    reads = idx.get('reads', {}) if isinstance(idx.get('reads', {}), dict) else {}
                    derived = idx.get('derived_metrics', {}) if isinstance(idx.get('derived_metrics', {}), dict) else {}
                    read_write_ratio = derived.get('read_write_ratio')
                    access_pattern = reads.get('access_pattern', idx.get('access_pattern', 'NO_READS'))
                    is_used = reads.get('is_used', idx.get('is_used', False))
                    last_read_age = reads.get('last_user_read_age_days')
                    key_bytes = idx.get('key_column_total_bytes', 0)
                    key_limit = idx.get('key_width_limit_bytes', 900)
                    key_over = idx.get('key_width_over_limit', False)
                    user_prompt += f"- [{idx_type}] {idx_id} ({key_ref})"
                    if include_ref:
                        user_prompt += f" INCLUDE({include_ref})"
                    user_prompt += f" - Seeks: {seeks}, Scans: {scans}"
                    user_prompt += f", Used: {is_used}, Access: {access_pattern}"
                    if read_write_ratio is not None:
                        user_prompt += f", R/W: {_fmt_float(read_write_ratio)}"
                    if last_read_age is not None:
                        user_prompt += f", LastReadAge: {_fmt_float(last_read_age)}d"
                    user_prompt += (
                        f", KeyBytes: {_fmt_int(key_bytes)}/{_fmt_int(key_limit)}, "
                        f"Key>900: {key_over}"
                    )
                    user_prompt += "\n"

        # NEW: Parameter Sniffing Analysis
        if parameter_sniffing:
            risk = str(parameter_sniffing.get('risk_level', 'unknown') or 'unknown').strip().lower()
            risk_emoji = "🟢" if risk == "low" else ("🟡" if risk == "medium" else "🔴")
            user_prompt += f"\n**{risk_emoji} Parameter Sniffing Analysis:**\n"
            user_prompt += f"- Risk Level: {risk.upper()}\n"
            user_prompt += f"- Plan Count: {parameter_sniffing.get('plan_count', 0)}\n"
            if parameter_sniffing.get('duration_variance'):
                user_prompt += f"- Duration Variance (CV): {parameter_sniffing.get('duration_variance')}%\n"
            if parameter_sniffing.get('cpu_variance'):
                user_prompt += f"- CPU Variance (CV): {parameter_sniffing.get('cpu_variance')}%\n"
            if parameter_sniffing.get('indicators'):
                user_prompt += "*Indicators:*\n"
                for ind in parameter_sniffing.get('indicators', []):
                    user_prompt += f"- {ind}\n"

        # NEW: Historical Trend
        if historical_trend:
            direction = str(historical_trend.get('trend_direction', 'stable') or 'stable').strip().lower()
            direction_emoji = "📈" if direction == "degrading" else ("📉" if direction == "improving" else "➡️")
            user_prompt += f"\n**{direction_emoji} Historical Trend ({historical_trend.get('recent_period', 'Last 14 days')} vs {historical_trend.get('previous_period', 'Previous 14 days')}):**\n"
            user_prompt += f"- Trend: {direction.upper()}\n"
            if historical_trend.get('duration_change_percent') is not None:
                user_prompt += f"- Duration Change: {historical_trend.get('duration_change_percent'):+.1f}%\n"
            if historical_trend.get('cpu_change_percent') is not None:
                user_prompt += f"- CPU Change: {historical_trend.get('cpu_change_percent'):+.1f}%\n"
            if historical_trend.get('reads_change_percent') is not None:
                user_prompt += f"- Reads Change: {historical_trend.get('reads_change_percent'):+.1f}%\n"
            if historical_trend.get('changes'):
                for change in historical_trend.get('changes', []):
                    user_prompt += f"- {change}\n"

        # NEW: Memory Grants
        if memory_grants:
            user_prompt += "\n**💾 Memory Grant Analysis:**\n"
            user_prompt += f"- Source: {memory_grants.get('source', 'unknown')}\n"
            if memory_grants.get('granted_memory_kb'):
                user_prompt += f"- Granted Memory: {_fmt_int(memory_grants.get('granted_memory_kb'))} KB\n"
            if memory_grants.get('used_memory_kb'):
                user_prompt += f"- Used Memory: {_fmt_int(memory_grants.get('used_memory_kb'))} KB\n"
            if memory_grants.get('utilization_pct') is not None:
                user_prompt += f"- Utilization: {memory_grants.get('utilization_pct')}%\n"
            if memory_grants.get('avg_memory_kb'):
                user_prompt += f"- Avg Memory (QS): {_fmt_int(memory_grants.get('avg_memory_kb'))} KB\n"
            if memory_grants.get('max_memory_kb'):
                user_prompt += f"- Max Memory (QS): {_fmt_int(memory_grants.get('max_memory_kb'))} KB\n"
            if memory_grants.get('warnings'):
                for warn in memory_grants.get('warnings', []):
                    user_prompt += f"- ⚠️ {warn}\n"

        if context and context.sql_version:
            user_prompt += f"\n**SQL Server Version:** {context.sql_version}\n"
        
        user_prompt += """
---
## ANALYSIS REQUEST

Please provide a comprehensive analysis including:

### 1. Executive Summary (Enhanced)
- 3-5 sentence overview with overall risk level, estimated impact, and top 3 findings
- Include "Immediate 24-hour actions" and "Strategic follow-up actions"

### 2. Classification System
- Use a clear taxonomy and classify findings into:
  - Effective
  - Needs Maintenance
  - Unnecessary
  - High Write Cost
  - CRITICAL_QUERY_ISSUE
  - POOR_QUERY_DESIGN
  - Uncertain / Requires More Evidence
- Explain why each class was assigned and provide class counts.
- Provide a single Query+Index combined class with rationale.

### 3. Identified Issues (Prioritized)
| # | Issue | Priority | Risk | Impact |
|---|-------|----------|------|--------|
| ... | ... | P1/P2/P3 | Low/Med/High | ... |

### 4. Optimization Recommendations
For each recommendation:
- Current code (problematic)
- Optimized code
- Expected improvement

### 5. Missing Index Comparison
- Compare missing-index signals with existing indexes before proposing new indexes.
- For each candidate, state:
  - Coverage status: Covered / Partially Covered / Not Covered / Not Feasible
  - Source comparison: Plan Missing Index vs Existing Index (and DMV Missing Index vs Existing Index when available)
  - Leftmost prefix detection result
  - Include-column coverage analysis (matched/missing include columns)
  - Best existing index match
  - Recommended action: Reuse, Refine existing, or Create new
  - Key width feasibility (900-byte limit)

### 6. Deep Existing Index Analysis
- Include deep analysis of current indexes:
  - Seek vs scan behavior
  - Read/write pressure and write overhead
  - 14-day usage window baseline coverage and reliability status
  - Usage-window warning signals (baseline gaps, low reliability)
  - Fragmentation, page density, stale stats
  - Duplicate/overlap and left-prefix coverage risks

### 7. Parameter Sniffing Mitigation (if applicable)
- Specific recommendations (RECOMPILE, OPTIMIZE FOR, etc.)

### 8. Testing & Validation Plan
- How to measure improvement
- Before/after comparison approach

### 9. Risks & Considerations
- Deployment risks
- Potential side effects
"""
        return cls._apply_prompt_overrides(PromptType.SP_OPTIMIZATION, system_prompt, user_prompt)

    @classmethod
    def build_sp_code_prompt(
        cls,
        source_code: str,
        object_name: str,
        stats: Dict[str, Any] = None,
        missing_indexes: List[Dict] = None,
        dependencies: List[Dict] = None,
        query_store: Dict[str, Any] = None,
        plan_xml: str = None,
        plan_meta: Dict[str, Any] = None,
        plan_insights: Dict[str, Any] = None,           # NEW
        existing_indexes: List[Dict] = None,            # NEW
        parameter_sniffing: Dict[str, Any] = None,      # NEW
        historical_trend: Dict[str, Any] = None,        # NEW
        memory_grants: Dict[str, Any] = None,           # NEW
        context: PromptContext = None
    ) -> tuple[str, str]:
        """Stored Procedure optimize edilmiş kodu (sadece SQL) için prompt oluştur."""
        def _fmt_float(val: Any, decimals: int = 2) -> str:
            try:
                if val is None:
                    val = 0.0
                return f"{float(val):.{decimals}f}"
            except Exception:
                return f"{0.0:.{decimals}f}"

        def _fmt_int(val: Any) -> str:
            try:
                if val is None:
                    val = 0
                return f"{int(val):,}"
            except Exception:
                return "0"

        system_prompt = cls.get_system_prompt(PromptType.SP_CODE_ONLY)
        few_shot = cls.get_few_shot_examples(PromptType.SP_OPTIMIZATION)

        user_prompt = f"""
{few_shot}

---
## OPTİMİZE EDİLECEK PROSEDÜR:

**Nesne Adı:** {object_name}

**Kaynak Kod:**
```sql
{source_code[:6000]}
```
"""

        if stats:
            exec_count = _fmt_int(stats.get('execution_count', 0))
            avg_cpu = _fmt_float(stats.get('avg_cpu_ms', 0))
            avg_duration = _fmt_float(stats.get('avg_duration_ms', 0))
            avg_reads = _fmt_int(stats.get('avg_logical_reads', 0))
            plan_count = _fmt_int(stats.get('plan_count', 1))
            user_prompt += f"""
**Çalışma İstatistikleri:**
- Toplam Çalışma: {exec_count}
- Ortalama CPU: {avg_cpu} ms
- Ortalama Süre: {avg_duration} ms
- Ortalama Okuma: {avg_reads}
- Plan Sayısı: {plan_count}
"""

        if missing_indexes:
            user_prompt += "\n**SQL Server Missing Index Önerileri:**\n"
            for idx in missing_indexes[:3]:
                impact = _fmt_float(idx.get('avg_user_impact', idx.get('impact_score', 0)), 0)
                eq_sig = idx.get('equality_signature', idx.get('equality_columns', '-'))
                inc_sig = idx.get('include_signature', idx.get('included_columns', '-'))
                eq_meta = idx.get('equality_columns', {}) if isinstance(idx.get('equality_columns', {}), dict) else {}
                key_meta = idx.get('key_columns', {}) if isinstance(idx.get('key_columns', {}), dict) else {}
                user_prompt += f"- Equality Sig: {eq_sig}, "
                user_prompt += f"Include Sig: {inc_sig}, "
                user_prompt += f"Etki: %{impact}"
                if eq_meta:
                    user_prompt += (
                        f", EqBytes: {_fmt_int(eq_meta.get('total_bytes', 0))}, "
                        f"EqFixed: {eq_meta.get('all_fixed_length', False)}, "
                        f"EqNotNull: {eq_meta.get('all_not_nullable', False)}"
                    )
                if key_meta:
                    user_prompt += (
                        f", KeyBytes: {_fmt_int(key_meta.get('total_bytes', 0))}/"
                        f"{_fmt_int(key_meta.get('limit_bytes', 900))}, "
                        f"Key>900: {key_meta.get('exceeds_900_byte_limit', False)}"
                    )
                user_prompt += "\n"

        if dependencies:
            user_prompt += "\n**Bağımlılıklar:**\n"
            for dep in dependencies[:10]:
                user_prompt += f"- {dep.get('dep_name', '')} ({dep.get('dep_type', '')})\n"

        if query_store:
            status = query_store.get("status", {})
            summary = query_store.get("summary", {})
            waits = query_store.get("waits", [])
            days = query_store.get("days", 7)
            user_prompt += "\n**Query Store (Runtime Context):**\n"
            if status:
                user_prompt += (
                    f"- Status: {status.get('actual_state', 'N/A')} "
                    f"(enabled={status.get('is_enabled', False)})\n"
                    f"- Window: last {days} day(s)\n"
                )
            if summary:
                user_prompt += (
                    f"- Total Executions: {_fmt_int(summary.get('total_executions', 0))}\n"
                    f"- Avg Duration: {_fmt_float(summary.get('avg_duration_ms', 0))} ms\n"
                    f"- Avg CPU: {_fmt_float(summary.get('avg_cpu_ms', 0))} ms\n"
                    f"- Avg Logical Reads: {_fmt_int(summary.get('avg_logical_reads', 0))}\n"
                    f"- Plan Count: {_fmt_int(summary.get('plan_count', 0))}\n"
                )
            if waits:
                user_prompt += "\n**Wait Profile (Query Store):**\n"
                for w in waits[:5]:
                    user_prompt += (
                        f"- {w.get('wait_category', 'Unknown')}: "
                        f"{_fmt_float(w.get('wait_percent', 0))}%\n"
                    )

        if plan_meta:
            user_prompt += "\n**Plan Metadata (cached, no execution):**\n"
            user_prompt += f"- Source: {plan_meta.get('source', 'unknown')}\n"
            if plan_meta.get("plan_hash"):
                user_prompt += f"- Plan Hash: {plan_meta.get('plan_hash')}\n"
            if plan_meta.get("plan_id"):
                user_prompt += f"- Plan ID: {plan_meta.get('plan_id')}\n"

        # NEW: Plan Insights (compact format for code-only output)
        if plan_insights:
            issues = []
            if plan_insights.get('has_table_scan'):
                issues.append("Table Scan")
            if plan_insights.get('has_key_lookup'):
                issues.append("Key Lookup")
            if plan_insights.get('has_implicit_conversion'):
                issues.append("Implicit Conversion")
            if plan_insights.get('expensive_operators'):
                issues.extend(plan_insights.get('expensive_operators', []))
            if issues:
                user_prompt += f"\n**Plan Issues:** {', '.join(set(issues))}\n"

        # NEW: Parameter Sniffing (compact)
        risk_level = str((parameter_sniffing or {}).get('risk_level', '') or '').strip().lower()
        if risk_level in ('medium', 'high'):
            user_prompt += f"\n**Parameter Sniffing Risk:** {risk_level.upper()}\n"

        if context and context.sql_version:
            user_prompt += f"\n**SQL Server Version:** {context.sql_version}\n"

        user_prompt += """
---
Return ONLY optimized SQL code. No explanations. No markdown.
Apply these optimizations:
1. Add SET NOCOUNT ON
2. Replace SELECT * with specific columns
3. Add OPTION (RECOMPILE) if parameter sniffing risk is high
4. Add proper error handling (TRY/CATCH)
5. Optimize joins and remove cursors if possible
"""

        return cls._apply_prompt_overrides(PromptType.SP_CODE_ONLY, system_prompt, user_prompt)
    
    @classmethod
    def build_index_recommendation_prompt(
        cls,
        query_text: str,
        table_info: Dict[str, Any],
        missing_index_dmv: Dict[str, Any] = None,
        existing_indexes: List[str] = None,
        context: PromptContext = None
    ) -> tuple[str, str]:
        """
        Index önerisi için prompt oluştur.
        """
        system_prompt = cls.get_system_prompt(PromptType.INDEX_RECOMMENDATION)
        few_shot = cls.get_few_shot_examples(PromptType.INDEX_RECOMMENDATION)

        def _format_int(value: Any, default: str = "N/A") -> str:
            try:
                if value is None:
                    return default
                return f"{int(value):,}"
            except (TypeError, ValueError):
                return default

        def _format_float(value: Any, default: str = "N/A") -> str:
            try:
                if value is None:
                    return default
                return f"{float(value):.0f}"
            except (TypeError, ValueError):
                return default
        
        user_prompt = f"""
{few_shot}

---
## INDEX ÖNERİSİ İSTENEN SORGU:

**SQL:**
```sql
{query_text[:2000]}
```

**Tablo Bilgileri:**
- Tablo: {table_info.get('table_name', 'N/A')}
- Satır Sayısı: {_format_int(table_info.get('row_count', None))}
- Tablo Boyutu: {_format_float(table_info.get('size_mb', None))} MB
"""
        
        if missing_index_dmv:
            user_prompt += f"""
**Missing Index DMV Çıktısı:**
- Equality Columns: {missing_index_dmv.get('equality_columns', '-')}
- Inequality Columns: {missing_index_dmv.get('inequality_columns', '-')}
- Include Columns: {missing_index_dmv.get('included_columns', '-')}
- User Seeks: {_format_int(missing_index_dmv.get('user_seeks', None), default='0')}
- Avg User Impact: %{_format_float(missing_index_dmv.get('avg_user_impact', None), default='0')}
"""
        
        if existing_indexes:
            user_prompt += "\n**Existing Indexes:**\n"
            for idx in existing_indexes[:5]:
                user_prompt += f"- {idx}\n"

        if context and context.sql_version:
            user_prompt += f"\n**SQL Server Version:** {context.sql_version}\n"
        
        user_prompt += """
---
Please recommend the most suitable index strategy.
Provide both CREATE INDEX syntax and rationale for why the index is needed.
Also evaluate a filtered index alternative when applicable.
"""
        return cls._apply_prompt_overrides(PromptType.INDEX_RECOMMENDATION, system_prompt, user_prompt)
    
    @classmethod
    def build_blocking_analysis_prompt(
        cls,
        blocking_data: List[Dict],
        head_blockers: List[Dict],
        lock_details: Dict[int, List] = None,
        context: PromptContext = None
    ) -> tuple[str, str]:
        """
        Blocking analizi için prompt oluştur.
        """
        system_prompt = cls.get_system_prompt(PromptType.BLOCKING_ANALYSIS)
        
        user_prompt = """## BLOCKING ANALYSIS

**Active Blocking Chains:**
"""
        
        if not blocking_data:
            user_prompt += "✅ There is no active blocking at the moment.\n"
        else:
            user_prompt += "| Blocked | Blocker | Wait Type | Duration (s) | Database |\n"
            user_prompt += "|---------|---------|-----------|----------|----------|\n"
            for b in blocking_data[:10]:
                user_prompt += f"| {b.session_id} | {b.blocking_session_id} | {b.wait_type} | {b.wait_seconds:.0f} | {b.database_name} |\n"
        
        if head_blockers:
            user_prompt += "\n**Head Blockers (Chain Root):**\n"
            for hb in head_blockers:
                user_prompt += f"\n### Session {hb.get('head_blocker_session')}\n"
                user_prompt += f"- Login: {hb.get('login_name')}\n"
                user_prompt += f"- Host: {hb.get('host_name')}\n"
                user_prompt += f"- Program: {hb.get('program_name')}\n"
                user_prompt += f"- Blocked Count: {hb.get('blocked_count')}\n"
                user_prompt += f"- Query:\n```sql\n{(hb.get('blocker_query') or 'N/A')[:500]}\n```\n"

        if context and context.sql_version:
            user_prompt += f"\n**SQL Server Version:** {context.sql_version}\n"
        
        user_prompt += """
---
Please analyze this blocking situation:
1. What is the likely root cause?
2. What are the immediate mitigation steps?
3. What should be done for a permanent fix?
"""
        
        return cls._apply_prompt_overrides(PromptType.BLOCKING_ANALYSIS, system_prompt, user_prompt)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_system_prompt(prompt_type: PromptType) -> str:
    """Shortcut function for getting system prompt"""
    return AdvancedPromptBuilder.get_system_prompt(prompt_type)


def get_best_practices() -> str:
    """Get SQL Server best practices text"""
    return SQL_BEST_PRACTICES
