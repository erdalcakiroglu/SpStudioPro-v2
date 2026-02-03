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

**Önerilen Kod:**
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
        return SYSTEM_PROMPTS.get(prompt_type, SYSTEM_PROMPTS[PromptType.GENERAL_CHAT])
    
    @staticmethod
    def get_few_shot_examples(prompt_type: PromptType) -> str:
        """Prompt türüne göre few-shot örnekleri döndür"""
        return FEW_SHOT_EXAMPLES.get(prompt_type, "")

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
                system_prompt = f"{system_prompt}\n\n## EK TALIMATLAR\n{global_instructions}"

            if user_override:
                if "{base_user}" in user_override:
                    user_prompt = user_override.replace("{base_user}", user_prompt)
                else:
                    user_prompt = user_override
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
                    user_prompt += "\n**Sunucu Performans Özeti:**\n"
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
Lütfen aşağıdaki formatta kapsamlı bir analiz yap:

## 🧾 Kısa Özet
- 2-3 cümlelik özet

## 🔍 Darboğazlar ve Kök Nedenler
- Ana sorunlar (madde madde)

## 📊 İstatistik Özeti
- Yukarıdaki metrik tablosunu yorumla

## 💡 Öneriler (Önceliklendirilmiş)
| # | Öneri | Öncelik | Risk | Tahmini Kazanç |
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
        context: PromptContext = None
    ) -> tuple[str, str]:
        """
        Stored Procedure optimizasyonu için prompt oluştur.
        """
        system_prompt = cls.get_system_prompt(PromptType.SP_OPTIMIZATION)
        few_shot = cls.get_few_shot_examples(PromptType.SP_OPTIMIZATION)
        
        user_prompt = f"""
{few_shot}

---
## ŞİMDİ OPTİMİZE EDİLECEK PROSEDÜR:

**Nesne Adı:** {object_name}

**Kaynak Kod:**
```sql
{source_code[:6000]}
```
"""
        
        if stats:
            user_prompt += f"""
**Çalışma İstatistikleri:**
- Toplam Çalışma: {stats.get('execution_count', 0):,}
- Ortalama CPU: {stats.get('avg_cpu_ms', 0):.2f} ms
- Ortalama Süre: {stats.get('avg_duration_ms', 0):.2f} ms
- Ortalama Okuma: {stats.get('avg_logical_reads', 0):,.0f}
- Plan Sayısı: {stats.get('plan_count', 1)}
"""
        
        if missing_indexes:
            user_prompt += "\n**SQL Server Missing Index Önerileri:**\n"
            for idx in missing_indexes[:3]:
                user_prompt += f"- Equality: {idx.get('equality_columns', '-')}, "
                user_prompt += f"Include: {idx.get('included_columns', '-')}, "
                user_prompt += f"Etki: %{idx.get('avg_user_impact', 0):.0f}\n"
        
        if dependencies:
            user_prompt += "\n**Bağımlılıklar:**\n"
            for dep in dependencies[:10]:
                user_prompt += f"- {dep.get('dep_name', '')} ({dep.get('dep_type', '')})\n"

        if context and context.sql_version:
            user_prompt += f"\n**SQL Server Version:** {context.sql_version}\n"
        
        user_prompt += """
---
Lütfen bu prosedürü kapsamlı olarak analiz et ve optimize edilmiş versiyonu öner.
Ayrıca CREATE INDEX ifadelerini de ekle.
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
        context: PromptContext = None
    ) -> tuple[str, str]:
        """Stored Procedure optimize edilmiş kodu (sadece SQL) için prompt oluştur."""
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
            user_prompt += f"""
**Çalışma İstatistikleri:**
- Toplam Çalışma: {stats.get('execution_count', 0):,}
- Ortalama CPU: {stats.get('avg_cpu_ms', 0):.2f} ms
- Ortalama Süre: {stats.get('avg_duration_ms', 0):.2f} ms
- Ortalama Okuma: {stats.get('avg_logical_reads', 0):,.0f}
- Plan Sayısı: {stats.get('plan_count', 1)}
"""

        if missing_indexes:
            user_prompt += "\n**SQL Server Missing Index Önerileri:**\n"
            for idx in missing_indexes[:3]:
                user_prompt += f"- Equality: {idx.get('equality_columns', '-')}, "
                user_prompt += f"Include: {idx.get('included_columns', '-')}, "
                user_prompt += f"Etki: %{idx.get('avg_user_impact', 0):.0f}\n"

        if dependencies:
            user_prompt += "\n**Bağımlılıklar:**\n"
            for dep in dependencies[:10]:
                user_prompt += f"- {dep.get('dep_name', '')} ({dep.get('dep_type', '')})\n"

        if context and context.sql_version:
            user_prompt += f"\n**SQL Server Version:** {context.sql_version}\n"

        user_prompt += """
---
SADECE optimize edilmiş SQL kodunu döndür.
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
            user_prompt += "\n**Mevcut Indexler:**\n"
            for idx in existing_indexes[:5]:
                user_prompt += f"- {idx}\n"

        if context and context.sql_version:
            user_prompt += f"\n**SQL Server Version:** {context.sql_version}\n"
        
        user_prompt += """
---
Lütfen en uygun index stratejisini öner. 
Hem CREATE INDEX syntax'ı hem de neden bu index'in gerekli olduğunu açıkla.
Varsa filtered index alternatifi de değerlendir.
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
        
        user_prompt = """## BLOCKING DURUMU ANALİZİ

**Aktif Blocking Zincirleri:**
"""
        
        if not blocking_data:
            user_prompt += "✅ Şu anda aktif blocking yok.\n"
        else:
            user_prompt += "| Blocked | Blocker | Wait Type | Süre (s) | Database |\n"
            user_prompt += "|---------|---------|-----------|----------|----------|\n"
            for b in blocking_data[:10]:
                user_prompt += f"| {b.session_id} | {b.blocking_session_id} | {b.wait_type} | {b.wait_seconds:.0f} | {b.database_name} |\n"
        
        if head_blockers:
            user_prompt += "\n**Head Blockers (Zincirin Başı):**\n"
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
Lütfen bu blocking durumunu analiz et:
1. Kök neden ne olabilir?
2. Acil çözüm önerileri
3. Kalıcı çözüm için ne yapılmalı?
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
