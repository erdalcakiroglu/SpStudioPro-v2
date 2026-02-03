# SQL Performance AI Platform
## Proje Tasarım Dökümanı

**Versiyon:** 1.0  
**Tarih:** Ocak 2025  
**Yazar:** Erdal & Claude  

---

## İÇindekiler

1. [Proje Vizyonu ve Hedefler](#1-proje-vizyonu-ve-hedefler)
2. [Teknoloji Stack](#2-teknoloji-stack)
3. [Mimari Tasarım](#3-mimari-tasarım)
4. [Veri Erişim Modeli](#4-veri-erişim-modeli)
5. [AI Workflow ve Intent Sistemi](#5-ai-workflow-ve-intent-sistemi)
6. [Query Template Kütüphanesi](#6-query-template-kütüphanesi)
7. [Kod Optimizasyonu ve Karşılaştırma](#7-kod-optimizasyonu-ve-karşılaştırma)
8. [Kullanıcı Arayüzü Tasarımı](#8-kullanıcı-arayüzü-tasarımı)
9. [Modül Yapısı ve Sorumlulukları](#9-modül-yapısı-ve-sorumlulukları)
10. [SP Studio'dan Migration Planı](#10-sp-studiodan-migration-planı)
11. [MVP Yol Haritası](#11-mvp-yol-haritası)
12. [Prompt Åžablonları](#12-prompt-şablonları)
13. [Güvenlik ve Authentication](#13-güvenlik-ve-authentication)
14. [Ã‡oklu Dil Desteği](#14-Çoklu-dil-desteği)
15. [SQL Server Version Yönetimi](#15-sql-server-version-yönetimi)
16. [Connection Manager Sistemi](#16-connection-manager-sistemi)
17. [Kapsamlı Performans Analiz Framework'ü](#17-kapsamlı-performans-analiz-frameworkü)
18. [SQL Kod Güvenlik Analizi](#18-sql-kod-güvenlik-analizi)
19. [Caching Strategy](#19-caching-strategy)
20. [Async Architecture](#20-async-architecture)
21. [Output Validation Pipeline](#21-output-validation-pipeline)
22. [Development Planı](#22-development-planı)
23. [Deployment & Packaging](#23-deployment--packaging)
24. [Query Stats Modülü](#24-query-stats-modülü)
25. [Performans Analiz Modülleri Arası İlişki](#25-performans-analiz-modülleri-arası-ilişki)

---

## 1. Proje Vizyonu ve Hedefler

### 1.1 Vizyon

**"AI-Powered SQL Performance Intelligence Platform"** - Global pazara hitap eden, kurumsal ve bireysel kullanıcılar iÇin tasarlanmış, yapay zeka destekli SQL Server performans analiz ve optimizasyon platformu.

### 1.2 Temel Hedefler

| Hedef | AÇıklama |
|-------|----------|
| **AI-Native Analiz** | Doğal dil ile soru sorma, AI destekli performans analizi |
| **Kod Optimizasyonu** | SP, Trigger, View iÇin otomatik optimizasyon önerileri ve düzeltilmiş kod üretimi |
| **Güvenli Erişim** | Sadece metadata ve system database erişimi - müşteri verisine dokunmama |
| **Karşılaştırma** | Eski vs yeni kod performans karşılaştırması |
| **Kurumsal Hazırlık** | LDAP/MSSQL Auth, Çoklu dil, subscription lisanslama |

### 1.3 Hedef Kullanıcılar

**DBA'ler (Database Administrators):**
- Sunucu sağlığı izleme
- Performans sorunları tespiti
- Index ve istatistik yönetimi
- Wait stats analizi
- Job ve backup monitoring

**Developers:**
- SP/Trigger/View kodu analizi
- Kod optimizasyonu önerileri
- Execution plan inceleme
- Query performans iyileştirme

### 1.4 Pazar ve Lisanslama

- **Pazar:** Global (Tüm dünya)
- **Lisans Modeli:** Subscription (aylık/yıllık)
- **Dağıtım:** Desktop-first, ileride Web versiyonu

---

## 2. Teknoloji Stack

### 2.1 Temel Teknolojiler

| Kategori | Teknoloji | Versiyon | GerekÇe |
|----------|-----------|----------|---------|
| **Dil** | Python | 3.11+ | Tip güvenliği, performans |
| **UI Framework** | PyQt6 | 6.6+ | Native performans, profesyonel UI, mature ecosystem |
| **Stil** | QSS (Qt Style Sheets) | - | CSS-like styling, tema desteği |
| **Kod Editör** | QScintilla | 2.14+ | Profesyonel syntax highlighting |
| **DB Bağlantı** | SQLAlchemy | 2.0+ | Async support, ORM |
| **SQL Server Driver** | pyodbc | 5.0+ | Native ODBC |
| **AI/LLM** | Ollama | Latest | Local LLM, gizlilik |
| **HTTP Client** | aiohttp | 3.9+ | Async API calls |
| **Config** | Pydantic | 2.0+ | Settings validation |
| **Password Store** | keyring | 24+ | OS-native credential storage |

### 2.2 PyQt6 Avantajları

```
#------------------------------------------------------------------------------
#                      NEDEN PyQt6?                                           #
#------------------------------------------------------------------------------¤
#                                                                             #
#  âš¡ PERFORMANS              ðŸŽ¨ UI KALİTESİ           ðŸ”§ Ã–ZELLİKLER          #
#  -------------              -------------           -------------          #
#  â€¢ Native C++ Qt            â€¢ Modern görünüm        â€¢ QScintilla editör    #
#  â€¢ Hızlı startup (~0.5s)    â€¢ Smooth animasyonlar   â€¢ QTableView (virtual) #
#  â€¢ Düşük memory (~50MB)     â€¢ Custom themes         â€¢ QSplitter layouts    #
#  â€¢ Large list support       â€¢ Rounded corners       â€¢ Drag & drop          #
#  â€¢ Virtual scrolling        â€¢ Blur/shadow efekt     â€¢ Docking widgets      #
#                             â€¢ Dark/Light theme      â€¢ MDI support          #
#                                                                             #
#  ðŸ“¦ ECOSYSTEM               ðŸŒ CROSS-PLATFORM       ðŸ“š MATURITY            #
#  -------------              -----------------       ----------             #
#  â€¢ 20+ yıllık geÇmiş        â€¢ Windows               â€¢ Production-ready     #
#  â€¢ Geniş community          â€¢ macOS                 â€¢ Enterprise kullanım  #
#  â€¢ Zengin dokümantasyon     â€¢ Linux                 â€¢ Stabil API           #
#  â€¢ Qt Designer              â€¢ (Web ayrı proje)      â€¢ Long-term support    #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 2.3 PyQt6 vs pyqt6 Karşılaştırması

| Kriter | PyQt6 | pyqt6 | SeÇim |
|--------|-------|------|-------|
| Startup time | ~0.5s | ~2-3s | PyQt6 âœ… |
| Memory usage | ~50MB | ~150MB | PyQt6 âœ… |
| Large data lists | Smooth (virtual scroll) | Laggy | PyQt6 âœ… |
| Styling flexibility | QSS (CSS-like) | Limited | PyQt6 âœ… |
| Native feel | Excellent | Web-like | PyQt6 âœ… |
| Animations | QPropertyAnimation | Basic | PyQt6 âœ… |
| Learning curve | Orta | Kolay | pyqt6 |
| Web support | âŒ Yok | âœ… Var | pyqt6 |

### 2.4 AI Layer

| Teknoloji | Kullanım Amacı | Neden SeÇildi |
|-----------|----------------|---------------|
| **Ollama** | Local LLM Runtime | Veri gizliliği, offline Çalışma |
| **CodeLlama / SQLCoder / Mistral** | LLM Modelleri | SQL ve kod odaklı |
| **OpenAI-compatible API** | Alternatif provider desteği | Esneklik |

### 2.5 Geliştirme AraÇları

| AraÇ | AmaÇ |
|------|------|
| **Qt Designer** | Visual UI tasarımı (.ui dosyaları) |
| **pyuic6** | .ui â†’ Python dönüşümü |
| **Poetry** | Dependency management |
| **Black** | Code formatting |
| **Ruff** | Linting |
| **pytest-qt** | PyQt6 test framework |
| **PyInstaller** | Executable packaging |

### 2.6 Paket Yapısı (Stabil Versiyonlar)

```toml
# pyproject.toml - Sabit, test edilmiş versiyonlar

[tool.poetry.dependencies]
python = "^3.11"

# UI Framework - Qt 6.6 LTS
PyQt6 = "6.6.1"
PyQt6-Qt6 = "6.6.1"
PyQt6-QScintilla = "2.14.1"
PyQt6-sip = "13.6.0"

# Database
SQLAlchemy = "2.0.25"
pyodbc = "5.1.0"

# Async & HTTP
aiohttp = "3.9.1"
asyncio = "3.4.3"

# Config & Validation
pydantic = "2.5.3"
pydantic-settings = "2.1.0"

# Security
keyring = "24.3.0"
cryptography = "41.0.7"

# Utilities
pyyaml = "6.0.1"
python-dateutil = "2.8.2"

[tool.poetry.group.dev.dependencies]
pytest = "7.4.4"
pytest-qt = "4.3.1"
pytest-asyncio = "0.23.3"
pytest-cov = "4.1.0"
black = "23.12.1"
ruff = "0.1.11"
mypy = "1.8.0"
pyinstaller = "6.3.0"

[tool.poetry.group.docs.dependencies]
mkdocs = "1.5.3"
mkdocs-material = "9.5.4"
```

### 2.7 Versiyon Sabitleme Nedenleri

| Paket | Versiyon | Neden |
|-------|----------|-------|
| PyQt6 | 6.6.1 | LTS, stabil, Qt 6.6 uyumlu |
| SQLAlchemy | 2.0.25 | 2.x async API, stabil |
| pydantic | 2.5.3 | V2 stabil, performanslı |
| aiohttp | 3.9.1 | Python 3.11+ uyumlu |
| keyring | 24.3.0 | Windows/macOS/Linux stabil |

**Versiyon Güncelleme Politikası:**
- Patch versiyonlar (x.x.X) â†’ Otomatik güncelleme OK
- Minor versiyonlar (x.X.x) â†’ Test sonrası güncelleme
- Major versiyonlar (X.x.x) â†’ Tam regression test gerekli

### 2.7 Local AI (Ollama) Avantajları

- **Veri Gizliliği:** Kurumsal müşteriler iÇin veri gizliliği
- **GDPR/KVKK Uyumluluğu:** Veri dışarı Çıkmaz
- **Offline Ã‡alışma:** Internet bağımlılığı yok
- **Maliyet Kontrolü:** API maliyeti yok

---

## 3. Mimari Tasarım

### 3.1 Genel Mimari

```
#------------------------------------------------------------------------------
#                        SQL PERFORMANCE AI PLATFORM                          #
#------------------------------------------------------------------------------¤
#                                                                             #
#  #----------------------------------------------------------------------   #
#  #                         PyQt6 UI LAYER                              #   #
#  #  #----------- #----------- #----------- #----------- #-----------  #   #
#  #  #  Login   # #Dashboard # # Query    # #  Object  # # Settings #  #   #
#  #  #  View    # #  View    # # Analyzer # # Explorer # #   View   #  #   #
#  #  -”-----------˜ -”-----------˜ -”-----------˜ -”-----------˜ -”-----------˜  #   #
#  #                                                                     #   #
#  #  #---------------------------------------------------------------  #   #
#  #  #                    AI CHAT INTERFACE                         #  #   #
#  #  #  "Son 10 günde en yavaş SP'ler hangileri?"                   #  #   #
#  #  -”---------------------------------------------------------------˜  #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  #----------------------------------------------------------------------   #
#  #                      AI ORCHESTRATION LAYER                         #   #
#  #                                                                     #   #
#  #  #--------------  #--------------  #--------------                 #   #
#  #  #   Intent    #  #   Query     #  #  Response   #                 #   #
#  #  #  Detector   #â†’ #  Selector   #â†’ #  Generator  #                 #   #
#  #  #  (AI)       #  #  (Hybrid)   #  #  (AI)       #                 #   #
#  #  -”--------------˜  -”--------------˜  -”--------------˜                 #   #
#  #                                                                     #   #
#  #  #--------------------------------------------------------------   #   #
#  #  #              CODE GENERATION & COMPARISON                    #   #   #
#  #  #  â€¢ Optimized SP/Trigger/View code generation                #   #   #
#  #  #  â€¢ Before/After comparison                                   #   #   #
#  #  #  â€¢ Performance prediction                                    #   #   #
#  #  -”--------------------------------------------------------------˜   #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  #----------------------------------------------------------------------   #
#  #                       ANALYSIS ENGINE                               #   #
#  #                   (SP Studio Core - Refactored)                     #   #
#  #                                                                     #   #
#  #  #------------ #------------ #------------ #------------          #   #
#  #  #   SQL     # # Enhanced  # #  Summary  # # Execution #          #   #
#  #  #  Parser   # #Statistics # #  Builder  # #   Plan    #          #   #
#  #  #           # #           # #           # # Analyzer  #          #   #
#  #  -”------------˜ -”------------˜ -”------------˜ -”------------˜          #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  #----------------------------------------------------------------------   #
#  #                         DATA LAYER                                  #   #
#  #                                                                     #   #
#  #  #--------------  #--------------  #--------------                 #   #
#  #  #    LLM      #  #  Database   #  #   Query     #                 #   #
#  #  #   Client    #  # Connection  #  #  Library    #                 #   #
#  #  #             #  #             #  # (Templates) #                 #   #
#  #  -”--------------˜  -”--------------˜  -”--------------˜                 #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  #----------------------------------------------------------------------   #
#  #                     TARGET DATABASES                                #   #
#  #         MSSQL (metadata + system views only)                        #   #
#  #         msdb (jobs, backup history)                                 #   #
#  -”----------------------------------------------------------------------˜   #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 3.2 Katman Sorumlulukları

| Katman | Sorumluluk |
|--------|------------|
| **UI Layer** | Kullanıcı etkileşimi, view'lar, tema |
| **AI Orchestration** | Intent detection, query seÇimi, yanıt üretimi |
| **Analysis Engine** | SQL parsing, statistics, execution plan analizi |
| **Data Layer** | DB bağlantı, LLM client, query template'ler |

---

## 4. Veri Erişim Modeli

### 4.1 Kritik Kısıtlama: Sadece Metadata

**Bu platform müşteri verisine ASLA erişmez.** Sadece metadata ve system database'lerinden bilgi Çeker.

### 4.2 Erişilebilir ve Erişilemez Alanlar

```
#------------------------------------------------------------------------------
#                         VERİ ERİÅžİM SINIRI                                  #
#------------------------------------------------------------------------------¤
#                                                                             #
#   âœ… ERİÅžEBİLECEÄžİMİZ                    âŒ ERİÅžMEYECEÄžİMİZ                #
#   ------------------                     --------------------               #
#                                                                             #
#   System DMVs:                           User Tables:                       #
#   â€¢ sys.dm_exec_query_stats              â€¢ SELECT * FROM Orders             #
#   â€¢ sys.dm_exec_requests                 â€¢ SELECT * FROM Customers          #
#   â€¢ sys.dm_os_wait_stats                 â€¢ Herhangi bir user data           #
#   â€¢ sys.dm_db_index_usage_stats                                             #
#   â€¢ sys.dm_db_missing_index_*            User Data:                         #
#   â€¢ sys.dm_tran_locks                    â€¢ Tablo iÇerikleri                 #
#   â€¢ sys.dm_exec_sessions                 â€¢ Row-level veriler                #
#   â€¢ sys.dm_exec_procedure_stats                                             #
#                                                                             #
#   System Catalogs:                                                          #
#   â€¢ sys.tables / sys.columns                                                #
#   â€¢ sys.indexes / sys.index_columns                                         #
#   â€¢ sys.procedures / sys.triggers                                           #
#   â€¢ sys.views / sys.sql_modules                                             #
#   â€¢ sys.schemas / sys.types                                                 #
#   â€¢ sys.stats / sys.stats_columns                                           #
#                                                                             #
#   System Databases:                                                         #
#   â€¢ master (server-level info)                                              #
#   â€¢ msdb (jobs, backup history)                                             #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 4.3 Ã–nerilen SQL Kullanıcı Yetkileri

```sql
-- Uygulama iÇin önerilen SQL kullanıcı yetkisi
CREATE LOGIN AppReadOnly WITH PASSWORD = '***';
CREATE USER AppReadOnly FOR LOGIN AppReadOnly;

-- Sadece VIEW SERVER STATE ve metadata erişimi
GRANT VIEW SERVER STATE TO AppReadOnly;
GRANT VIEW DATABASE STATE TO AppReadOnly;
GRANT VIEW DEFINITION TO AppReadOnly;

-- msdb erişimi (jobs, backup history)
USE msdb;
GRANT SELECT ON dbo.sysjobs TO AppReadOnly;
GRANT SELECT ON dbo.sysjobhistory TO AppReadOnly;
GRANT SELECT ON dbo.backupset TO AppReadOnly;
GRANT SELECT ON dbo.backupmediafamily TO AppReadOnly;

-- Kesinlikle VERİLMEYECEK yetkiler:
-- âŒ db_datareader (user table'lara erişim)
-- âŒ db_datawriter
-- âŒ db_owner
-- âŒ EXECUTE (SP Çalıştırma)
```

---

## 5. AI Workflow ve Intent Sistemi

### 5.1 Hibrit Query Sistemi

Kullanıcı soruları iki şekilde işlenir:

1. **Template Match:** Ã–nceden tanımlı sorgularla hızlı eşleşme
2. **Dynamic Generation:** Template yoksa AI metadata SQL üretir

```
#------------------------------------------------------------------------------
#                        HİBRİT QUERY SİSTEMİ                                 #
#------------------------------------------------------------------------------¤
#                                                                             #
#                      KULLANICI SORUSU                                       #
#                            #                                                #
#                            â–¼                                                #
#  #----------------------------------------------------------------------   #
#  #                    AI INTENT ANALYZER                               #   #
#  #                                                                     #   #
#  #  Soru: "Son 10 gün iÇinde en Çok Çalışan sorgular nelerdir?"       #   #
#  #                                                                     #   #
#  #  Analiz:                                                            #   #
#  #  â€¢ Kategori: QUERY_STATISTICS                                       #   #
#  #  â€¢ Zaman filtresi: 10 gün                                           #   #
#  #  â€¢ Metrik: execution_count (en Çok Çalışan)                         #   #
#  #  â€¢ Eşleşen template: top_executed_queries                           #   #
#  -”----------------------------------------------------------------------˜   #
#                            #                                                #
#                            â–¼                                                #
#         #-------------------´-------------------                            #
#         #                                     #                            #
#         â–¼                                     â–¼                            #
#  #------------------                 #------------------                   #
#  # TEMPLATE MATCH  #                 #  DYNAMIC SQL    #                   #
#  #                 #                 #   GENERATION    #                   #
#  # Ã–nceden tanımlı #                 #                 #                   #
#  # sorgu + parametre#                # Template yoksa  #                   #
#  # (Hızlı, Güvenli)#                 # AI metadata SQL #                   #
#  #                 #                 # üretir          #                   #
#  -”---------¬---------˜                 -”---------¬---------˜                   #
#           #                                   #                            #
#           -”---------------¬---------------------˜                            #
#                          â–¼                                                  #
#  #----------------------------------------------------------------------   #
#  #                    SQL VALIDATOR                                    #   #
#  #                                                                     #   #
#  #  âœ“ Sadece sys.* ve DMV erişimi?                                     #   #
#  #  âœ“ User table'a SELECT yok?                                         #   #
#  #  âœ“ Tehlikeli komut yok?                                             #   #
#  -”----------------------------------------------------------------------˜   #
#                          #                                                  #
#                          â–¼                                                  #
#  #----------------------------------------------------------------------   #
#  #                 EXECUTE & ANALYZE                                   #   #
#  -”----------------------------------------------------------------------˜   #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 5.2 Intent â†’ Template Eşleştirme

```python
INTENT_TO_TEMPLATES = {
    # Query Performance
    "slow_queries": ["top_slow_queries"],
    "most_executed": ["top_executed_queries"],
    "high_io_queries": ["top_io_queries"],
    
    # Objects
    "analyze_sp": ["sp_code", "sp_statistics", "sp_dependencies"],
    "analyze_trigger": ["trigger_code", "trigger_list"],
    "analyze_view": ["view_code", "view_dependencies"],
    "list_sp": ["sp_list"],
    "list_triggers": ["trigger_list"],
    "list_views": ["view_list"],
    
    # Indexes
    "missing_indexes": ["missing_indexes"],
    "unused_indexes": ["unused_indexes"],
    "index_fragmentation": ["index_fragmentation"],
    
    # Waits & Blocking
    "wait_stats": ["wait_stats"],
    "blocking": ["blocking_chains", "active_sessions"],
    "active_sessions": ["active_sessions"],
    
    # Jobs & Backup
    "job_status": ["job_list", "job_history"],
    "backup_status": ["backup_history"],
    
    # Table Analysis
    "table_info": ["table_info", "table_columns", "missing_indexes"]
}
```

### 5.3 AI'ın Rolü

AI artık user table'lardan SQL üretmek yerine şunları yapar:

1. **Intent Detection** - Kullanıcı ne istiyor?
2. **Query Selection** - Hangi önceden tanımlı sorguları Çalıştırmalı?
3. **Parameter Extraction** - Sorgular iÇin parametreleri Çıkar
4. **Result Analysis** - Dönen metadata'yı analiz et ve yorumla
5. **Code Generation** - Optimize edilmiş SP/Trigger/View kodu üret
6. **Recommendation** - Optimizasyon önerileri sun

---

## 6. Query Template Kütüphanesi

### 6.1 Server Level Configuration

```python
"server_version": {
    "description": "Sunucu versiyonu ve detayları",
    "parameters": [],
    "sql": """
        SELECT 
            @@VERSION AS FullVersion,
            SERVERPROPERTY('ProductVersion') AS ProductVersion,
            SERVERPROPERTY('ProductMajorVersion') AS MajorVersion,
            SERVERPROPERTY('ProductLevel') AS ProductLevel,
            SERVERPROPERTY('Edition') AS Edition,
            SERVERPROPERTY('EngineEdition') AS EngineEdition,
            SERVERPROPERTY('MachineName') AS MachineName,
            SERVERPROPERTY('ServerName') AS ServerName,
            SERVERPROPERTY('IsClustered') AS IsClustered,
            SERVERPROPERTY('IsHadrEnabled') AS IsHadrEnabled
    """
},

"server_memory_config": {
    "description": "Sunucu bellek ayarları",
    "parameters": [],
    "sql": """
        SELECT 
            name,
            value AS configured_value,
            value_in_use AS running_value,
            minimum,
            maximum,
            description
        FROM sys.configurations
        WHERE name IN (
            'max server memory (MB)',
            'min server memory (MB)',
            'max worker threads',
            'query wait (s)'
        )
        ORDER BY name
    """
},

"server_cpu_config": {
    "description": "CPU ve parallelism ayarları",
    "parameters": [],
    "sql": """
        SELECT 
            name,
            value AS configured_value,
            value_in_use AS running_value,
            description
        FROM sys.configurations
        WHERE name IN (
            'max degree of parallelism',
            'cost threshold for parallelism',
            'affinity mask',
            'affinity64 mask'
        )
        
        UNION ALL
        
        SELECT 
            'CPU Count' AS name,
            cpu_count AS configured_value,
            cpu_count AS running_value,
            'Number of logical CPUs' AS description
        FROM sys.dm_os_sys_info
        
        UNION ALL
        
        SELECT 
            'Hyperthread Ratio' AS name,
            hyperthread_ratio AS configured_value,
            hyperthread_ratio AS running_value,
            'Logical to physical CPU ratio' AS description
        FROM sys.dm_os_sys_info
    """
},

"server_memory_usage": {
    "description": "Anlık bellek kullanımı",
    "parameters": [],
    "sql": """
        SELECT 
            physical_memory_kb / 1024 AS physical_memory_mb,
            committed_kb / 1024 AS committed_mb,
            committed_target_kb / 1024 AS committed_target_mb,
            visible_target_kb / 1024 AS visible_target_mb,
            stack_size_in_bytes / 1024 / 1024 AS stack_size_mb,
            virtual_machine_type_desc
        FROM sys.dm_os_sys_info
        
        UNION ALL
        
        SELECT TOP 1
            (SELECT cntr_value / 1024 FROM sys.dm_os_performance_counters 
             WHERE counter_name = 'Total Server Memory (KB)') AS total_server_memory_mb,
            (SELECT cntr_value / 1024 FROM sys.dm_os_performance_counters 
             WHERE counter_name = 'Target Server Memory (KB)') AS target_server_memory_mb,
            NULL, NULL, NULL, NULL
        FROM sys.dm_os_performance_counters
    """
},

"server_os_info": {
    "description": "İşletim sistemi bilgileri",
    "min_version": 14,  # SQL 2017+
    "parameters": [],
    "sql": """
        SELECT 
            host_platform,
            host_distribution,
            host_release,
            host_service_pack_level,
            host_sku,
            os_language_version
        FROM sys.dm_os_host_info
    """
},

### 6.2 Database Level Configuration

"database_config": {
    "description": "Veritabanı konfigürasyonu",
    "parameters": [],
    "sql": """
        SELECT 
            d.name AS database_name,
            d.compatibility_level,
            d.collation_name,
            d.is_auto_create_stats_on,
            d.is_auto_update_stats_on,
            d.is_auto_update_stats_async_on,
            d.is_parameterization_forced,
            d.snapshot_isolation_state_desc,
            d.is_read_committed_snapshot_on,
            d.recovery_model_desc,
            d.page_verify_option_desc,
            d.is_query_store_on,
            d.is_memory_optimized_elevate_to_snapshot_on
        FROM sys.databases d
        WHERE d.database_id = DB_ID()
    """
},

"database_files": {
    "description": "Veritabanı dosya bilgileri",
    "parameters": [],
    "sql": """
        SELECT 
            df.name AS logical_name,
            df.type_desc AS file_type,
            df.physical_name,
            df.size * 8 / 1024 AS size_mb,
            df.max_size,
            CASE df.is_percent_growth
                WHEN 1 THEN CAST(df.growth AS VARCHAR) + '%'
                ELSE CAST(df.growth * 8 / 1024 AS VARCHAR) + ' MB'
            END AS growth_setting,
            df.is_percent_growth,
            FILEPROPERTY(df.name, 'SpaceUsed') * 8 / 1024 AS used_mb,
            (df.size - FILEPROPERTY(df.name, 'SpaceUsed')) * 8 / 1024 AS free_mb,
            fg.name AS filegroup_name
        FROM sys.database_files df
        LEFT JOIN sys.filegroups fg ON df.data_space_id = fg.data_space_id
        ORDER BY df.type, df.file_id
    """
},

"database_io_stats": {
    "description": "Veritabanı I/O istatistikleri",
    "parameters": [],
    "sql": """
        SELECT 
            DB_NAME(vfs.database_id) AS database_name,
            mf.name AS logical_name,
            mf.type_desc AS file_type,
            mf.physical_name,
            vfs.num_of_reads,
            vfs.num_of_writes,
            vfs.num_of_bytes_read / 1024 / 1024 AS mb_read,
            vfs.num_of_bytes_written / 1024 / 1024 AS mb_written,
            vfs.io_stall_read_ms,
            vfs.io_stall_write_ms,
            vfs.io_stall_read_ms / NULLIF(vfs.num_of_reads, 0) AS avg_read_latency_ms,
            vfs.io_stall_write_ms / NULLIF(vfs.num_of_writes, 0) AS avg_write_latency_ms,
            vfs.size_on_disk_bytes / 1024 / 1024 AS size_on_disk_mb
        FROM sys.dm_io_virtual_file_stats(DB_ID(), NULL) vfs
        JOIN sys.master_files mf ON vfs.database_id = mf.database_id 
            AND vfs.file_id = mf.file_id
        ORDER BY vfs.io_stall DESC
    """
},

"database_statistics_health": {
    "description": "İstatistik sağlığı ve güncellik durumu",
    "parameters": ["min_rows_changed_percent"],
    "sql": """
        SELECT 
            OBJECT_SCHEMA_NAME(s.object_id) AS schema_name,
            OBJECT_NAME(s.object_id) AS table_name,
            s.name AS statistics_name,
            s.auto_created,
            s.user_created,
            s.no_recompute,
            sp.last_updated,
            sp.rows,
            sp.rows_sampled,
            sp.modification_counter,
            ROUND(sp.modification_counter * 100.0 / NULLIF(sp.rows, 0), 2) AS modification_percent,
            sp.steps,
            DATEDIFF(day, sp.last_updated, GETDATE()) AS days_since_update
        FROM sys.stats s
        CROSS APPLY sys.dm_db_stats_properties(s.object_id, s.stats_id) sp
        WHERE OBJECTPROPERTY(s.object_id, 'IsUserTable') = 1
          AND sp.modification_counter * 100.0 / NULLIF(sp.rows, 0) > @min_rows_changed_percent
        ORDER BY modification_percent DESC
    """
},

### 6.3 Query Statistics

```python
"top_slow_queries": {
    "description": "En yavaş sorgular",
    "parameters": ["top_n", "days"],
    "sql": """
        SELECT TOP (@top_n)
            qs.total_elapsed_time / qs.execution_count AS avg_elapsed_time_ms,
            qs.execution_count,
            qs.total_logical_reads / qs.execution_count AS avg_logical_reads,
            qs.creation_time,
            SUBSTRING(st.text, 1, 1000) AS query_text
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        WHERE qs.creation_time > DATEADD(day, -@days, GETDATE())
        ORDER BY avg_elapsed_time_ms DESC
    """
},

"top_executed_queries": {
    "description": "En Çok Çalışan sorgular",
    "parameters": ["top_n", "days"],
    "sql": """
        SELECT TOP (@top_n)
            qs.execution_count,
            qs.total_elapsed_time / qs.execution_count AS avg_elapsed_time_ms,
            qs.total_logical_reads,
            qs.creation_time,
            SUBSTRING(st.text, 1, 1000) AS query_text
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        WHERE qs.creation_time > DATEADD(day, -@days, GETDATE())
        ORDER BY qs.execution_count DESC
    """
},

"top_io_queries": {
    "description": "En Çok IO yapan sorgular",
    "parameters": ["top_n", "days"],
    "sql": """
        SELECT TOP (@top_n)
            qs.total_logical_reads + qs.total_logical_writes AS total_io,
            qs.execution_count,
            qs.total_logical_reads / qs.execution_count AS avg_reads,
            SUBSTRING(st.text, 1, 1000) AS query_text
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        WHERE qs.creation_time > DATEADD(day, -@days, GETDATE())
        ORDER BY total_io DESC
    """
}
```

### 6.2 Stored Procedures

```python
"sp_list": {
    "description": "Stored procedure listesi",
    "parameters": ["schema_filter"],
    "sql": """
        SELECT 
            s.name AS schema_name,
            p.name AS sp_name,
            p.create_date,
            p.modify_date,
            LEN(m.definition) AS code_length
        FROM sys.procedures p
        JOIN sys.schemas s ON p.schema_id = s.schema_id
        JOIN sys.sql_modules m ON p.object_id = m.object_id
        WHERE (@schema_filter IS NULL OR s.name = @schema_filter)
        ORDER BY s.name, p.name
    """
},

"sp_code": {
    "description": "Stored procedure kaynak kodu",
    "parameters": ["sp_name"],
    "sql": """
        SELECT 
            OBJECT_SCHEMA_NAME(object_id) AS schema_name,
            OBJECT_NAME(object_id) AS sp_name,
            definition
        FROM sys.sql_modules
        WHERE object_id = OBJECT_ID(@sp_name)
    """
},

"sp_statistics": {
    "description": "Stored procedure Çalışma istatistikleri",
    "parameters": ["top_n"],
    "sql": """
        SELECT TOP (@top_n)
            OBJECT_SCHEMA_NAME(ps.object_id) AS schema_name,
            OBJECT_NAME(ps.object_id) AS sp_name,
            ps.execution_count,
            ps.total_elapsed_time / NULLIF(ps.execution_count, 0) / 1000 AS avg_elapsed_ms,
            ps.total_logical_reads / NULLIF(ps.execution_count, 0) AS avg_logical_reads,
            ps.total_physical_reads / NULLIF(ps.execution_count, 0) AS avg_physical_reads,
            ps.cached_time,
            ps.last_execution_time
        FROM sys.dm_exec_procedure_stats ps
        WHERE ps.database_id = DB_ID()
        ORDER BY avg_elapsed_ms DESC
    """
},

"sp_dependencies": {
    "description": "SP bağımlılıkları (hangi tabloları kullanıyor)",
    "parameters": ["sp_name"],
    "sql": """
        SELECT DISTINCT
            OBJECT_NAME(referencing_id) AS sp_name,
            referenced_schema_name,
            referenced_entity_name,
            referenced_minor_name AS column_name
        FROM sys.sql_expression_dependencies
        WHERE referencing_id = OBJECT_ID(@sp_name)
    """
}
```

### 6.3 Triggers

```python
"trigger_list": {
    "description": "Trigger listesi",
    "parameters": [],
    "sql": """
        SELECT 
            OBJECT_SCHEMA_NAME(t.parent_id) AS schema_name,
            OBJECT_NAME(t.parent_id) AS table_name,
            t.name AS trigger_name,
            t.is_disabled,
            t.is_instead_of_trigger,
            te.type_desc AS trigger_event,
            t.create_date,
            t.modify_date
        FROM sys.triggers t
        JOIN sys.trigger_events te ON t.object_id = te.object_id
        WHERE t.parent_class = 1
        ORDER BY schema_name, table_name, trigger_name
    """
},

"trigger_code": {
    "description": "Trigger kaynak kodu",
    "parameters": ["trigger_name"],
    "sql": """
        SELECT 
            OBJECT_NAME(t.parent_id) AS table_name,
            t.name AS trigger_name,
            m.definition
        FROM sys.triggers t
        JOIN sys.sql_modules m ON t.object_id = m.object_id
        WHERE t.name = @trigger_name
    """
}
```

### 6.4 Views

```python
"view_list": {
    "description": "View listesi",
    "parameters": ["schema_filter"],
    "sql": """
        SELECT 
            s.name AS schema_name,
            v.name AS view_name,
            v.create_date,
            v.modify_date,
            OBJECTPROPERTYEX(v.object_id, 'IsIndexed') AS is_indexed,
            LEN(m.definition) AS code_length
        FROM sys.views v
        JOIN sys.schemas s ON v.schema_id = s.schema_id
        JOIN sys.sql_modules m ON v.object_id = m.object_id
        WHERE (@schema_filter IS NULL OR s.name = @schema_filter)
        ORDER BY s.name, v.name
    """
},

"view_code": {
    "description": "View kaynak kodu",
    "parameters": ["view_name"],
    "sql": """
        SELECT 
            OBJECT_SCHEMA_NAME(object_id) AS schema_name,
            OBJECT_NAME(object_id) AS view_name,
            definition
        FROM sys.sql_modules
        WHERE object_id = OBJECT_ID(@view_name)
    """
}
```

### 6.5 Indexes

```python
"missing_indexes": {
    "description": "Eksik index önerileri",
    "parameters": ["top_n"],
    "sql": """
        SELECT TOP (@top_n)
            OBJECT_SCHEMA_NAME(mid.object_id) AS schema_name,
            OBJECT_NAME(mid.object_id) AS table_name,
            mid.equality_columns,
            mid.inequality_columns,
            mid.included_columns,
            ROUND(migs.avg_user_impact, 2) AS avg_impact_percent,
            migs.user_seeks + migs.user_scans AS potential_usage,
            'CREATE INDEX IX_' + OBJECT_NAME(mid.object_id) + '_' 
                + REPLACE(REPLACE(COALESCE(mid.equality_columns, ''), ', ', '_'), '[', '') 
                + ' ON ' + mid.statement 
                + ' (' + COALESCE(mid.equality_columns, '') 
                + CASE WHEN mid.inequality_columns IS NOT NULL 
                       THEN ', ' + mid.inequality_columns ELSE '' END + ')'
                + CASE WHEN mid.included_columns IS NOT NULL 
                       THEN ' INCLUDE (' + mid.included_columns + ')' ELSE '' END 
            AS suggested_index_script
        FROM sys.dm_db_missing_index_details mid
        JOIN sys.dm_db_missing_index_groups mig ON mid.index_handle = mig.index_handle
        JOIN sys.dm_db_missing_index_group_stats migs ON mig.index_group_handle = migs.group_handle
        WHERE mid.database_id = DB_ID()
        ORDER BY migs.avg_user_impact * (migs.user_seeks + migs.user_scans) DESC
    """
},

"unused_indexes": {
    "description": "Kullanılmayan indexler",
    "parameters": ["min_days_old"],
    "sql": """
        SELECT 
            OBJECT_SCHEMA_NAME(i.object_id) AS schema_name,
            OBJECT_NAME(i.object_id) AS table_name,
            i.name AS index_name,
            i.type_desc,
            ius.user_seeks,
            ius.user_scans,
            ius.user_lookups,
            ius.user_updates,
            (SELECT SUM(ps.used_page_count) * 8 / 1024 
             FROM sys.dm_db_partition_stats ps 
             WHERE ps.object_id = i.object_id AND ps.index_id = i.index_id) AS size_mb
        FROM sys.indexes i
        LEFT JOIN sys.dm_db_index_usage_stats ius 
            ON i.object_id = ius.object_id AND i.index_id = ius.index_id
        WHERE OBJECTPROPERTY(i.object_id, 'IsUserTable') = 1
          AND i.type_desc <> 'HEAP'
          AND i.is_primary_key = 0
          AND i.is_unique_constraint = 0
          AND (ius.user_seeks + ius.user_scans + ius.user_lookups) = 0
          AND ius.last_user_update < DATEADD(day, -@min_days_old, GETDATE())
        ORDER BY size_mb DESC
    """
},

"index_fragmentation": {
    "description": "Index fragmentation durumu",
    "parameters": ["min_fragmentation"],
    "sql": """
        SELECT 
            OBJECT_SCHEMA_NAME(ips.object_id) AS schema_name,
            OBJECT_NAME(ips.object_id) AS table_name,
            i.name AS index_name,
            ips.index_type_desc,
            ROUND(ips.avg_fragmentation_in_percent, 2) AS fragmentation_percent,
            ips.page_count,
            CASE 
                WHEN ips.avg_fragmentation_in_percent > 30 THEN 'REBUILD'
                WHEN ips.avg_fragmentation_in_percent > 10 THEN 'REORGANIZE'
                ELSE 'OK'
            END AS recommended_action
        FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
        JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
        WHERE ips.avg_fragmentation_in_percent > @min_fragmentation
          AND ips.page_count > 1000
        ORDER BY fragmentation_percent DESC
    """
}
```

### 6.6 Wait Statistics & Blocking

```python
"wait_stats": {
    "description": "Wait istatistikleri",
    "parameters": ["top_n"],
    "sql": """
        SELECT TOP (@top_n)
            wait_type,
            waiting_tasks_count,
            wait_time_ms,
            wait_time_ms / NULLIF(waiting_tasks_count, 0) AS avg_wait_ms,
            signal_wait_time_ms,
            ROUND(100.0 * wait_time_ms / SUM(wait_time_ms) OVER(), 2) AS wait_percent
        FROM sys.dm_os_wait_stats
        WHERE wait_type NOT IN (
            'SLEEP_TASK', 'BROKER_TASK_STOP', 'BROKER_EVENTHANDLER',
            'CLR_AUTO_EVENT', 'CLR_MANUAL_EVENT', 'REQUEST_FOR_DEADLOCK_SEARCH',
            'LAZYWRITER_SLEEP', 'CHECKPOINT_QUEUE', 'XE_DISPATCHER_WAIT',
            'FT_IFTS_SCHEDULER_IDLE_WAIT', 'LOGMGR_QUEUE', 'DIRTY_PAGE_POLL',
            'HADR_FILESTREAM_IOMGR_IOCOMPLETION', 'SP_SERVER_DIAGNOSTICS_SLEEP'
        )
        ORDER BY wait_time_ms DESC
    """
},

"active_sessions": {
    "description": "Aktif session'lar",
    "parameters": [],
    "sql": """
        SELECT 
            r.session_id,
            s.login_name,
            s.host_name,
            DB_NAME(r.database_id) AS database_name,
            r.status,
            r.command,
            r.wait_type,
            r.wait_time,
            r.blocking_session_id,
            r.cpu_time,
            r.logical_reads,
            SUBSTRING(t.text, 1, 500) AS current_query
        FROM sys.dm_exec_requests r
        JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
        CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
        WHERE r.session_id > 50
        ORDER BY r.cpu_time DESC
    """
},

"blocking_chains": {
    "description": "Blocking zincirleri",
    "parameters": [],
    "sql": """
        WITH BlockingChain AS (
            SELECT 
                session_id,
                blocking_session_id,
                wait_type,
                wait_time,
                0 AS level
            FROM sys.dm_exec_requests
            WHERE blocking_session_id = 0 AND session_id IN (
                SELECT DISTINCT blocking_session_id 
                FROM sys.dm_exec_requests 
                WHERE blocking_session_id > 0
            )
            
            UNION ALL
            
            SELECT 
                r.session_id,
                r.blocking_session_id,
                r.wait_type,
                r.wait_time,
                bc.level + 1
            FROM sys.dm_exec_requests r
            JOIN BlockingChain bc ON r.blocking_session_id = bc.session_id
        )
        SELECT 
            bc.*,
            t.text AS query_text
        FROM BlockingChain bc
        CROSS APPLY sys.dm_exec_sql_text(
            (SELECT sql_handle FROM sys.dm_exec_requests WHERE session_id = bc.session_id)
        ) t
        ORDER BY level, session_id
    """
}
```

### 6.7 Jobs & Backup (msdb)

```python
"job_list": {
    "description": "SQL Agent job listesi",
    "parameters": [],
    "sql": """
        SELECT 
            j.name AS job_name,
            j.enabled,
            CASE j.notify_level_eventlog
                WHEN 0 THEN 'Never'
                WHEN 1 THEN 'On Success'
                WHEN 2 THEN 'On Failure'
                WHEN 3 THEN 'Always'
            END AS notify_level,
            c.name AS category_name,
            j.date_created,
            j.date_modified,
            (SELECT MAX(run_date) FROM msdb.dbo.sysjobhistory h WHERE h.job_id = j.job_id) AS last_run_date
        FROM msdb.dbo.sysjobs j
        JOIN msdb.dbo.syscategories c ON j.category_id = c.category_id
        ORDER BY j.name
    """
},

"job_history": {
    "description": "Job Çalışma geÇmişi",
    "parameters": ["job_name", "days"],
    "sql": """
        SELECT TOP 50
            j.name AS job_name,
            h.step_name,
            CASE h.run_status
                WHEN 0 THEN 'Failed'
                WHEN 1 THEN 'Succeeded'
                WHEN 2 THEN 'Retry'
                WHEN 3 THEN 'Canceled'
                WHEN 4 THEN 'In Progress'
            END AS status,
            h.run_date,
            h.run_time,
            h.run_duration,
            h.message
        FROM msdb.dbo.sysjobhistory h
        JOIN msdb.dbo.sysjobs j ON h.job_id = j.job_id
        WHERE j.name = @job_name
          AND h.run_date > CONVERT(int, CONVERT(varchar(8), DATEADD(day, -@days, GETDATE()), 112))
        ORDER BY h.run_date DESC, h.run_time DESC
    """
},

"backup_history": {
    "description": "Backup geÇmişi",
    "parameters": ["database_name", "days"],
    "sql": """
        SELECT 
            bs.database_name,
            bs.backup_start_date,
            bs.backup_finish_date,
            DATEDIFF(minute, bs.backup_start_date, bs.backup_finish_date) AS duration_minutes,
            CASE bs.type
                WHEN 'D' THEN 'Full'
                WHEN 'I' THEN 'Differential'
                WHEN 'L' THEN 'Log'
            END AS backup_type,
            ROUND(bs.backup_size / 1024 / 1024, 2) AS backup_size_mb,
            ROUND(bs.compressed_backup_size / 1024 / 1024, 2) AS compressed_size_mb,
            bmf.physical_device_name
        FROM msdb.dbo.backupset bs
        JOIN msdb.dbo.backupmediafamily bmf ON bs.media_set_id = bmf.media_set_id
        WHERE bs.database_name = @database_name
          AND bs.backup_start_date > DATEADD(day, -@days, GETDATE())
        ORDER BY bs.backup_start_date DESC
    """
}
```

### 6.8 Execution Plan Capture

```python
"get_cached_plan": {
    "description": "Plan cache'den execution plan al",
    "parameters": ["sp_name"],
    "sql": """
        SELECT 
            qp.query_plan,
            qs.execution_count,
            qs.total_elapsed_time / qs.execution_count as avg_elapsed_time,
            qs.total_logical_reads / qs.execution_count as avg_logical_reads,
            qs.total_worker_time / qs.execution_count as avg_cpu_time
        FROM sys.dm_exec_procedure_stats ps
        CROSS APPLY sys.dm_exec_query_plan(ps.plan_handle) qp
        WHERE ps.object_id = OBJECT_ID(@sp_name)
          AND ps.database_id = DB_ID()
    """
},

"get_query_plan_by_hash": {
    "description": "Query hash ile execution plan al",
    "parameters": ["query_hash"],
    "sql": """
        SELECT 
            qs.query_hash,
            qs.query_plan_hash,
            qs.execution_count,
            qs.total_elapsed_time / qs.execution_count AS avg_duration_us,
            qs.total_worker_time / qs.execution_count AS avg_cpu_us,
            qs.total_logical_reads / qs.execution_count AS avg_logical_reads,
            qs.total_physical_reads / qs.execution_count AS avg_physical_reads,
            qp.query_plan,
            SUBSTRING(st.text, 1, 500) AS query_text
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_query_plan(qs.plan_handle) qp
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        WHERE qs.query_hash = @query_hash
    """
}
```

### 6.9 Lock & Deadlock Statistics

```python
"current_locks": {
    "description": "Anlık lock durumu",
    "parameters": [],
    "sql": """
        SELECT 
            tl.request_session_id AS session_id,
            tl.resource_type,
            tl.resource_subtype,
            tl.resource_database_id,
            DB_NAME(tl.resource_database_id) AS database_name,
            tl.resource_associated_entity_id,
            CASE tl.resource_type
                WHEN 'OBJECT' THEN OBJECT_NAME(tl.resource_associated_entity_id, tl.resource_database_id)
                ELSE NULL
            END AS object_name,
            tl.request_mode,
            tl.request_type,
            tl.request_status,
            tl.request_owner_type,
            es.login_name,
            es.host_name,
            es.program_name,
            SUBSTRING(st.text, 1, 500) AS query_text
        FROM sys.dm_tran_locks tl
        JOIN sys.dm_exec_sessions es ON tl.request_session_id = es.session_id
        LEFT JOIN sys.dm_exec_requests er ON tl.request_session_id = er.session_id
        OUTER APPLY sys.dm_exec_sql_text(er.sql_handle) st
        WHERE tl.request_session_id > 50
        ORDER BY tl.request_session_id, tl.resource_type
    """
},

"lock_wait_stats": {
    "description": "Lock bekleme istatistikleri",
    "parameters": [],
    "sql": """
        SELECT 
            wait_type,
            waiting_tasks_count,
            wait_time_ms,
            max_wait_time_ms,
            signal_wait_time_ms
        FROM sys.dm_os_wait_stats
        WHERE wait_type LIKE 'LCK_%'
          AND waiting_tasks_count > 0
        ORDER BY wait_time_ms DESC
    """
},

"deadlock_graph": {
    "description": "Son deadlock bilgisi (Extended Events / System Health)",
    "min_version": 13,
    "parameters": [],
    "sql": """
        ;WITH XEventData AS (
            SELECT 
                CAST(target_data AS XML) AS target_data
            FROM sys.dm_xe_session_targets st
            JOIN sys.dm_xe_sessions s ON s.address = st.event_session_address
            WHERE s.name = 'system_health'
              AND st.target_name = 'ring_buffer'
        )
        SELECT TOP 10
            xed.value('@timestamp', 'datetime2') AS deadlock_time,
            xed.query('.') AS deadlock_graph
        FROM XEventData
        CROSS APPLY target_data.nodes('RingBufferTarget/event[@name="xml_deadlock_report"]') AS xn(xed)
        ORDER BY deadlock_time DESC
    """
}
```

### 6.10 Parameter Sniffing Detection

```python
"parameter_sniffing_check": {
    "description": "Parametre sniffing tespiti - aynı SP iÇin farklı planlar",
    "parameters": ["sp_name"],
    "sql": """
        SELECT 
            OBJECT_NAME(ps.object_id) AS sp_name,
            ps.plan_handle,
            ps.execution_count,
            ps.total_elapsed_time / NULLIF(ps.execution_count, 0) / 1000 AS avg_duration_ms,
            ps.total_logical_reads / NULLIF(ps.execution_count, 0) AS avg_logical_reads,
            ps.total_worker_time / NULLIF(ps.execution_count, 0) / 1000 AS avg_cpu_ms,
            ps.cached_time,
            ps.last_execution_time,
            qp.query_plan
        FROM sys.dm_exec_procedure_stats ps
        CROSS APPLY sys.dm_exec_query_plan(ps.plan_handle) qp
        WHERE ps.object_id = OBJECT_ID(@sp_name)
          AND ps.database_id = DB_ID()
        ORDER BY avg_duration_ms DESC
    """
},

"query_multiple_plans": {
    "description": "Aynı sorgu iÇin birden fazla plan (parameter sniffing göstergesi)",
    "parameters": ["top_n"],
    "sql": """
        SELECT TOP (@top_n)
            query_hash,
            COUNT(DISTINCT query_plan_hash) AS plan_count,
            SUM(execution_count) AS total_executions,
            MIN(total_elapsed_time / NULLIF(execution_count, 0)) / 1000 AS min_avg_duration_ms,
            MAX(total_elapsed_time / NULLIF(execution_count, 0)) / 1000 AS max_avg_duration_ms,
            AVG(total_elapsed_time / NULLIF(execution_count, 0)) / 1000 AS avg_duration_ms,
            MAX(total_elapsed_time / NULLIF(execution_count, 0)) / 
                NULLIF(MIN(total_elapsed_time / NULLIF(execution_count, 0)), 1) AS variance_ratio
        FROM sys.dm_exec_query_stats
        GROUP BY query_hash
        HAVING COUNT(DISTINCT query_plan_hash) > 1
        ORDER BY variance_ratio DESC
    """
}
```

### 6.11 Workload Analysis

```python
"sp_execution_history": {
    "description": "SP Çağrılma sıklığı ve performans trendi",
    "parameters": ["sp_name", "days"],
    "sql": """
        -- Plan cache'den anlık bilgi
        SELECT 
            OBJECT_NAME(ps.object_id) AS sp_name,
            ps.execution_count,
            ps.total_elapsed_time / 1000 AS total_duration_ms,
            ps.total_elapsed_time / NULLIF(ps.execution_count, 0) / 1000 AS avg_duration_ms,
            ps.total_logical_reads,
            ps.total_logical_reads / NULLIF(ps.execution_count, 0) AS avg_logical_reads,
            ps.total_physical_reads,
            ps.total_physical_reads / NULLIF(ps.execution_count, 0) AS avg_physical_reads,
            ps.total_worker_time / 1000 AS total_cpu_ms,
            ps.total_worker_time / NULLIF(ps.execution_count, 0) / 1000 AS avg_cpu_ms,
            ps.cached_time,
            ps.last_execution_time,
            DATEDIFF(minute, ps.cached_time, GETDATE()) AS minutes_in_cache,
            ps.execution_count * 1.0 / NULLIF(DATEDIFF(minute, ps.cached_time, GETDATE()), 0) AS exec_per_minute
        FROM sys.dm_exec_procedure_stats ps
        WHERE ps.object_id = OBJECT_ID(@sp_name)
          AND ps.database_id = DB_ID()
    """
},

"query_store_sp_history": {
    "description": "Query Store'dan SP performans geÇmişi",
    "min_version": 13,
    "requires_feature": "QUERY_STORE",
    "parameters": ["sp_name", "days"],
    "sql": """
        SELECT 
            OBJECT_NAME(q.object_id) AS sp_name,
            p.plan_id,
            rs.runtime_stats_interval_id,
            rsi.start_time,
            rsi.end_time,
            rs.count_executions,
            rs.avg_duration / 1000 AS avg_duration_ms,
            rs.avg_cpu_time / 1000 AS avg_cpu_ms,
            rs.avg_logical_io_reads,
            rs.avg_physical_io_reads,
            rs.avg_rowcount
        FROM sys.query_store_query q
        JOIN sys.query_store_plan p ON q.query_id = p.query_id
        JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
        JOIN sys.query_store_runtime_stats_interval rsi ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
        WHERE q.object_id = OBJECT_ID(@sp_name)
          AND rsi.start_time > DATEADD(day, -@days, GETDATE())
        ORDER BY rsi.start_time DESC
    """
},

"concurrent_sp_impact": {
    "description": "SP Çalışırken diğer sorguların etkilenme durumu",
    "parameters": [],
    "sql": """
        SELECT 
            r.session_id,
            r.blocking_session_id,
            r.wait_type,
            r.wait_time,
            r.wait_resource,
            DB_NAME(r.database_id) AS database_name,
            s.login_name,
            s.host_name,
            SUBSTRING(st.text, 1, 500) AS query_text,
            r.cpu_time,
            r.logical_reads,
            r.status,
            r.command
        FROM sys.dm_exec_requests r
        JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
        CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) st
        WHERE r.session_id > 50
          AND r.session_id != @@SPID
        ORDER BY r.wait_time DESC
    """
}
```

### 6.12 Trigger Analysis

```python
"trigger_performance": {
    "description": "Trigger performans analizi",
    "parameters": [],
    "sql": """
        SELECT 
            OBJECT_SCHEMA_NAME(t.parent_id) AS schema_name,
            OBJECT_NAME(t.parent_id) AS table_name,
            t.name AS trigger_name,
            t.is_disabled,
            t.is_instead_of_trigger,
            te.type_desc AS trigger_event,
            ts.execution_count,
            ts.total_elapsed_time / NULLIF(ts.execution_count, 0) / 1000 AS avg_duration_ms,
            ts.total_worker_time / NULLIF(ts.execution_count, 0) / 1000 AS avg_cpu_ms,
            ts.total_logical_reads / NULLIF(ts.execution_count, 0) AS avg_logical_reads,
            ts.total_logical_writes / NULLIF(ts.execution_count, 0) AS avg_logical_writes,
            ts.cached_time,
            ts.last_execution_time
        FROM sys.triggers t
        JOIN sys.trigger_events te ON t.object_id = te.object_id
        LEFT JOIN sys.dm_exec_trigger_stats ts ON t.object_id = ts.object_id
        WHERE t.parent_class = 1  -- Object triggers
        ORDER BY ts.total_elapsed_time DESC
    """
},

"trigger_impact_on_table": {
    "description": "Belirli tablodaki trigger'ların toplam etkisi",
    "parameters": ["table_name"],
    "sql": """
        SELECT 
            OBJECT_NAME(t.parent_id) AS table_name,
            COUNT(*) AS trigger_count,
            SUM(CASE WHEN t.is_disabled = 0 THEN 1 ELSE 0 END) AS active_triggers,
            SUM(ts.execution_count) AS total_trigger_executions,
            SUM(ts.total_elapsed_time) / 1000 AS total_trigger_time_ms,
            AVG(ts.total_elapsed_time / NULLIF(ts.execution_count, 0)) / 1000 AS avg_trigger_time_ms
        FROM sys.triggers t
        LEFT JOIN sys.dm_exec_trigger_stats ts ON t.object_id = ts.object_id
        WHERE t.parent_id = OBJECT_ID(@table_name)
        GROUP BY t.parent_id
    """
}
```

---

## 7. Kod Optimizasyonu ve Karşılaştırma

### 7.1 Optimizasyon Workflow

```
#------------------------------------------------------------------------------
#                    SP OPTIMIZATION WORKFLOW                                 #
#------------------------------------------------------------------------------¤
#                                                                             #
#  ADIM 1: MEVCUT SP ANALİZİ                                                  #
#  #----------------------------------------------------------------------   #
#  # â€¢ SP kodunu al (sys.sql_modules)                                    #   #
#  # â€¢ Execution stats al (sys.dm_exec_procedure_stats)                  #   #
#  # â€¢ Bağımlılıkları bul (sys.sql_expression_dependencies)              #   #
#  # â€¢ Index bilgilerini topla                                           #   #
#  # â€¢ Plan cache'den execution plan al                                  #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  ADIM 2: AI ANALİZ & Ã–NERİ                                                  #
#  #----------------------------------------------------------------------   #
#  # AI tüm verileri analiz eder ve şunları üretir:                      #   #
#  #                                                                     #   #
#  # â€¢ SORUN TESPİTİ:                                                    #   #
#  #   - "Cursor kullanımı var, satır satır işleniyor"                   #   #
#  #   - "SELECT * kullanılmış, gereksiz kolonlar Çekiliyor"             #   #
#  #   - "Missing index: Orders(CustomerID, OrderDate)"                  #   #
#  #                                                                     #   #
#  # â€¢ OPTİMİZE EDİLMİÅž KOD:                                             #   #
#  #   - Cursor â†’ Set-based dönüşüm                                      #   #
#  #   - SELECT * â†’ Explicit column list                                 #   #
#  #   - Index creation script                                           #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  ADIM 3: KARÅžILAÅžTIRMA GÃ–RÃœNÃœMÃœ                                             #
#  #-----------------------------¬-----------------------------------------   #
#  #      MEVCUT KOD            #         OPTİMİZE EDİLMİÅž KOD           #   #
#  #-----------------------------¼-----------------------------------------¤   #
#  # CREATE PROCEDURE dbo.GetX  # CREATE PROCEDURE dbo.GetX              #   #
#  # AS                         # AS                                     #   #
#  # BEGIN                      # BEGIN                                  #   #
#  #   DECLARE @id INT          #   -- Set-based approach                #   #
#  #   DECLARE cur CURSOR FOR   #   SELECT                               #   #
#  #   ...                      #     o.OrderID,                         #   #
#  #                            #     SUM(od.Quantity) as TotalQty       #   #
#  #                            #   FROM Orders o                        #   #
#  #                            #   JOIN OrderDetails od ON ...          #   #
#  #                            #   GROUP BY o.OrderID                   #   #
#  # END                        # END                                    #   #
#  #-----------------------------¼-----------------------------------------¤   #
#  # â±ï¸ Avg: 4,500ms            # â±ï¸ Tahmini: ~150ms                     #   #
#  # ðŸ“– Logical Reads: 125,000  # ðŸ“– Tahmini: ~2,000                     #   #
#  -”-----------------------------´-----------------------------------------˜   #
#                                                                             #
#  #--------------- #--------------- #---------------                        #
#  # ðŸ“‹ Kodu      # # ðŸ“Š Plan      # # âœ… Kopyala   #                        #
#  #    Kopyala   # #    Karşıla.  # #              #                        #
#  -”---------------˜ -”---------------˜ -”---------------˜                        #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 7.2 Test Stratejisi

Optimize edilmiş kod iÇin test yaklaşımı:

| Yöntem | AÇıklama |
|--------|----------|
| **Execution Plan Only (B)** | Sadece execution plan al, gerÇek Çalıştırma yapma |
| **Kullanıcıya Uyar (C)** | Kullanıcıya kodu kopyalayıp kendi test etmesini öner |

**NOT:** Version history tutulmayacak.

---

## 8. Kullanıcı Arayüzü Tasarımı

### 8.1 Genel Tasarım İlkeleri

- **Perplexity Benzeri:** Minimalist, modern, koyu tema
- **Merkezi Arama:** Ana odak noktası doğal dil soru kutusu
- **İkon Tabanlı Sidebar:** Navigation with icons and labels
- **Responsive:** QSplitter ile pencere boyutuna uyum
- **Native Feel:** PyQt6 ile platform-native görünüm

### 8.2 PyQt6 UI Bileşenleri

| Bileşen | PyQt6 Widget | Kullanım |
|---------|--------------|----------|
| **Main Window** | QMainWindow | Ana pencere, menu bar, status bar |
| **Sidebar** | QWidget + QVBoxLayout | Navigation menu |
| **Stacked Views** | QStackedWidget | Sayfa geÇişleri |
| **Chat Area** | QScrollArea + custom widgets | Chat mesajları |
| **Code Editor** | QScintilla | SQL syntax highlighting |
| **Data Tables** | QTableView + QAbstractTableModel | Virtual scrolling |
| **Splitters** | QSplitter | Resizable panels |
| **Dialogs** | QDialog | Modal forms |
| **Progress** | QProgressDialog | Long operations |

### 8.3 Ana Ekran Yapısı

```
#------------------------------------------------------------------------------
#  ðŸš€ SQL Perf AI                                              [-] [â–¡] [Ã—]   #
#---------------¬---------------------------------------------------------------¤
#              #                                                              #
#  ðŸ’¬ Chat  â—„--#         Welcome to SQL Performance AI                        #
#              #      Ask me anything about SQL Server performance            #
#  ðŸ“Š Dashboard#                                                              #
#              #      #---------------------------------------------------   #
#  ðŸ” SP Explor#      # ðŸ” Analyze stored procedure usp_GetOrderDetails  #   #
#              #      -”---------------------------------------------------˜   #
#  ðŸ“ˆ Query St #      #---------------------------------------------------   #
#              #      # ðŸ“Š Show me the slowest queries in the last hour  #   #
#  ðŸ”§ Index Adv#      -”---------------------------------------------------˜   #
#              #      #---------------------------------------------------   #
#  ðŸ›¡ï¸ Security #      # ðŸ”§ Check index fragmentation on Orders table     #   #
#              #      -”---------------------------------------------------˜   #
#  ðŸ“‹ Jobs     #                                                              #
#              #      #---------------------------------------------------   #
# â— Production #      # ðŸ” Ask about SQL performance...          [Send]  #   #
#              #      -”---------------------------------------------------˜   #
#  âš™ï¸ Settings #                                                              #
#              #      [Pro Mode]  [Sources]  [Related]                        #
#---------------´---------------------------------------------------------------¤
#  Connected: SQLSERVER01 # Model: Ollama/codellama # ðŸŸ¢ Ready               #
-”------------------------------------------------------------------------------˜
```

### 8.4 Theme System (QSS)

```css
/* Dark Theme - QSS Ã–rneği */
QMainWindow {
    background-color: #1a1a1a;
}

#sidebar {
    background-color: #0d0d0d;
    border-right: 1px solid #2a2a2a;
}

#sidebar QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 12px 16px;
    color: #888888;
}

#sidebar QPushButton:hover {
    background-color: #1a1a1a;
    color: #ffffff;
}

#chatInput {
    background-color: #242424;
    border: 1px solid #3a3a3a;
    border-radius: 24px;
    padding: 12px 20px;
    color: #ffffff;
}

#userMessage {
    background-color: #0066ff;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 16px;
    color: white;
}

#codeBlock {
    background-color: #1e1e1e;
    border: 1px solid #333333;
    border-radius: 8px;
    font-family: 'Consolas', monospace;
}
```

### 8.5 View Listesi

| View | AÇıklama | Ana Widget'lar |
|------|----------|----------------|
| **ChatView** | AI chat arayüzü | QScrollArea, QLineEdit, custom bubbles |
| **DashboardView** | Server overview | Charts, cards, QGridLayout |
| **SPExplorerView** | SP listesi ve kod | QTreeView, QScintilla |
| **QueryStatsView** | Query istatistikleri | QTableView, filters |
| **IndexAdvisorView** | Index önerileri | QTableView, action buttons |
| **SecurityView** | Güvenlik analizi | Risk cards, recommendations |
| **JobsView** | SQL Agent jobs | QTableView, status icons |
| **SettingsView** | Ayarlar | QTabWidget, forms |
| **ConnectionDialog** | Bağlantı ekleme | QDialog, QFormLayout |

### 8.6 Object Explorer (SSMS Benzeri)

Object Explorer, veritabanı objelerini hiyerarşik yapıda gösteren ana navigasyon bileşenidir.

```
#------------------------------------------------------------------------------
#  OBJECT EXPLORER                                                            #
#------------------------------------------------------------------------------¤
#                                                                             #
#  ðŸ“ Production Server (SQLSERVER01)                                         #
#  -”-- ðŸ“ Databases                                                           #
#      -”-- ðŸ“ SalesDB                                                         #
#          #-- ðŸ“ Programmability                                             #
#          #   #-- ðŸ“ Stored Procedures (147)           [Loading... 45%]     #
#          #   #   #-- ðŸ”§ usp_GetOrderDetails          âš¡ 12.5ms avg         #
#          #   #   #-- ðŸ”§ usp_ProcessPayment           âš ï¸ 245ms avg          #
#          #   #   #-- ðŸ”§ usp_UpdateInventory          âš¡ 8.2ms avg          #
#          #   #   -”-- ... (144 more)                                        #
#          #   #                                                              #
#          #   #-- ðŸ“ Triggers (23)                                          #
#          #   #   #-- âš¡ trg_Orders_Insert             âœ… Enabled           #
#          #   #   #-- âš¡ trg_Audit_Update              âš ï¸ Disabled          #
#          #   #   -”-- ... (21 more)                                         #
#          #   #                                                              #
#          #   -”-- ðŸ“ Views (34)                                             #
#          #       #-- ðŸ‘ï¸ vw_ActiveCustomers            ðŸ“Š Indexed          #
#          #       #-- ðŸ‘ï¸ vw_SalesReport                                     #
#          #       -”-- ... (32 more)                                         #
#          #                                                                  #
#          -”-- ðŸ“ Performance                                                 #
#              #-- ðŸ“Š Missing Indexes (12)              âš ï¸ High Impact       #
#              #-- ðŸ“Š Unused Indexes (8)                ðŸ’¾ Wasting Space     #
#              #-- ðŸ“Š Fragmented Indexes (15)           ðŸ”§ Needs Maint.      #
#              #-- ðŸ“Š Wait Statistics                   ðŸ”´ PAGEIOLATCH       #
#              -”-- ðŸ“Š Active Sessions (24)              ðŸŸ¢ Normal            #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

#### Object Explorer Tree Yapısı

```python
# app/ui/components/object_explorer.py

from PyQt6.QtWidgets import QTreeView, QHeaderView
from PyQt6.QtCore import Qt, QAbstractItemModel, QModelIndex
from PyQt6.QtGui import QIcon, QColor
from dataclasses import dataclass
from typing import List, Optional, Any
from enum import Enum

class ObjectType(Enum):
    SERVER = "server"
    DATABASE = "database"
    FOLDER = "folder"
    STORED_PROCEDURE = "sp"
    TRIGGER = "trigger"
    VIEW = "view"
    INDEX = "index"
    PERFORMANCE = "performance"

@dataclass
class TreeNode:
    """Object Explorer tree node"""
    name: str
    object_type: ObjectType
    data: Optional[Any] = None  # SP stats, trigger info, etc.
    children: List['TreeNode'] = None
    parent: Optional['TreeNode'] = None
    is_loaded: bool = False
    icon: str = ""
    badge: str = ""  # "âš¡", "âš ï¸", "ðŸ”´" etc.
    
    def __post_init__(self):
        if self.children is None:
            self.children = []

class ObjectExplorerModel(QAbstractItemModel):
    """Tree model for Object Explorer"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root = TreeNode("Root", ObjectType.FOLDER)
        self._icons = self._load_icons()
    
    def _load_icons(self) -> dict:
        return {
            ObjectType.SERVER: QIcon(":/icons/server.png"),
            ObjectType.DATABASE: QIcon(":/icons/database.png"),
            ObjectType.FOLDER: QIcon(":/icons/folder.png"),
            ObjectType.STORED_PROCEDURE: QIcon(":/icons/sp.png"),
            ObjectType.TRIGGER: QIcon(":/icons/trigger.png"),
            ObjectType.VIEW: QIcon(":/icons/view.png"),
            ObjectType.INDEX: QIcon(":/icons/index.png"),
            ObjectType.PERFORMANCE: QIcon(":/icons/chart.png"),
        }
    
    def add_server(self, server_name: str, databases: List[str]):
        """Add server node with databases"""
        server_node = TreeNode(
            name=server_name,
            object_type=ObjectType.SERVER,
            icon="ðŸ–¥ï¸"
        )
        
        db_folder = TreeNode("Databases", ObjectType.FOLDER, icon="ðŸ“")
        
        for db_name in databases:
            db_node = self._create_database_node(db_name)
            db_folder.children.append(db_node)
            db_node.parent = db_folder
        
        server_node.children.append(db_folder)
        self.root.children.append(server_node)
        
    def _create_database_node(self, db_name: str) -> TreeNode:
        """Create database node with standard structure"""
        db_node = TreeNode(db_name, ObjectType.DATABASE, icon="ðŸ“")
        
        # Programmability folder
        prog_folder = TreeNode("Programmability", ObjectType.FOLDER, icon="ðŸ“")
        prog_folder.children = [
            TreeNode("Stored Procedures", ObjectType.FOLDER, icon="ðŸ“"),
            TreeNode("Triggers", ObjectType.FOLDER, icon="ðŸ“"),
            TreeNode("Views", ObjectType.FOLDER, icon="ðŸ“"),
        ]
        
        # Performance folder
        perf_folder = TreeNode("Performance", ObjectType.FOLDER, icon="ðŸ“")
        perf_folder.children = [
            TreeNode("Missing Indexes", ObjectType.PERFORMANCE, icon="ðŸ“Š"),
            TreeNode("Unused Indexes", ObjectType.PERFORMANCE, icon="ðŸ“Š"),
            TreeNode("Index Fragmentation", ObjectType.PERFORMANCE, icon="ðŸ“Š"),
            TreeNode("Wait Statistics", ObjectType.PERFORMANCE, icon="ðŸ“Š"),
            TreeNode("Active Sessions", ObjectType.PERFORMANCE, icon="ðŸ“Š"),
        ]
        
        db_node.children = [prog_folder, perf_folder]
        return db_node

class ObjectExplorer(QTreeView):
    """SSMS-style Object Explorer widget"""
    
    object_selected = pyqtSignal(TreeNode)
    object_double_clicked = pyqtSignal(TreeNode)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("objectExplorer")
        self.model = ObjectExplorerModel(self)
        self.setModel(self.model)
        self.setup_ui()
    
    def setup_ui(self):
        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setIndentation(20)
        self.setExpandsOnDoubleClick(False)
        
        # Selection
        self.clicked.connect(self._on_item_clicked)
        self.doubleClicked.connect(self._on_item_double_clicked)
        
        # Style
        self.setStyleSheet("""
            QTreeView {
                background-color: #1e1e1e;
                border: none;
                color: #cccccc;
                font-size: 13px;
            }
            QTreeView::item {
                padding: 4px 8px;
                border-radius: 4px;
            }
            QTreeView::item:hover {
                background-color: #2a2a2a;
            }
            QTreeView::item:selected {
                background-color: #094771;
                color: white;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                image: url(:/icons/branch-closed.png);
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                image: url(:/icons/branch-open.png);
            }
        """)
```

### 8.7 Pre-Loading System (Progress Bar ile Metadata Yükleme)

Tüm metadata bağlantı kurulduğunda yüklenir, sonraki gezintiler Çok hızlı olur.

```
#------------------------------------------------------------------------------
#                                                                             #
#                    ðŸš€ SQL Performance AI                                    #
#                                                                             #
#                    Loading Database Metadata...                             #
#                                                                             #
#     â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘â–‘  45%             #
#                                                                             #
#     âœ… Server info loaded                                                   #
#     âœ… Stored Procedures (147/147)                                         #
#     âœ… SP Statistics loaded                                                 #
#     ðŸ”„ Loading Triggers (12/23)...                                         #
#     â³ Views                                                                #
#     â³ Index information                                                    #
#     â³ Performance metrics                                                  #
#                                                                             #
#     Elapsed: 3.2s | Estimated: 4.1s remaining                              #
#                                                                             #
#                         [Cancel]                                            #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

#### Pre-Loader Implementation

```python
# app/services/metadata_preloader.py

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

class LoadingStage(Enum):
    SERVER_INFO = "Server Info"
    STORED_PROCEDURES = "Stored Procedures"
    SP_STATISTICS = "SP Statistics"
    SP_DEPENDENCIES = "SP Dependencies"
    TRIGGERS = "Triggers"
    TRIGGER_STATISTICS = "Trigger Statistics"
    VIEWS = "Views"
    VIEW_DEPENDENCIES = "View Dependencies"
    INDEXES = "Indexes"
    MISSING_INDEXES = "Missing Indexes"
    UNUSED_INDEXES = "Unused Indexes"
    INDEX_FRAGMENTATION = "Index Fragmentation"
    WAIT_STATISTICS = "Wait Statistics"
    ACTIVE_SESSIONS = "Active Sessions"

@dataclass
class LoadingProgress:
    stage: LoadingStage
    current: int = 0
    total: int = 0
    message: str = ""
    
    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 0
        return (self.current / self.total) * 100

@dataclass
class PreloadedMetadata:
    """Container for all preloaded metadata"""
    
    # Server
    server_info: dict = field(default_factory=dict)
    
    # Stored Procedures
    stored_procedures: List[dict] = field(default_factory=list)
    sp_statistics: Dict[str, dict] = field(default_factory=dict)
    sp_dependencies: Dict[str, List[dict]] = field(default_factory=dict)
    sp_execution_plans: Dict[str, str] = field(default_factory=dict)
    
    # Triggers
    triggers: List[dict] = field(default_factory=list)
    trigger_statistics: Dict[str, dict] = field(default_factory=dict)
    
    # Views
    views: List[dict] = field(default_factory=list)
    view_dependencies: Dict[str, List[dict]] = field(default_factory=dict)
    indexed_views: List[dict] = field(default_factory=list)
    
    # Indexes
    missing_indexes: List[dict] = field(default_factory=list)
    unused_indexes: List[dict] = field(default_factory=list)
    index_fragmentation: List[dict] = field(default_factory=list)
    
    # Performance
    wait_statistics: List[dict] = field(default_factory=list)
    active_sessions: List[dict] = field(default_factory=list)
    blocking_chains: List[dict] = field(default_factory=list)
    
    # Metadata
    load_time: float = 0.0
    loaded_at: str = ""

class MetadataPreloader(QObject):
    """
    Pre-loads all database metadata at connection time.
    Enables fast navigation without additional queries.
    """
    
    # Signals
    progress_updated = pyqtSignal(LoadingProgress)
    stage_completed = pyqtSignal(LoadingStage)
    loading_completed = pyqtSignal(PreloadedMetadata)
    loading_failed = pyqtSignal(str)
    loading_cancelled = pyqtSignal()
    
    # Loading stages with weights (for progress calculation)
    STAGES = [
        (LoadingStage.SERVER_INFO, 2),
        (LoadingStage.STORED_PROCEDURES, 10),
        (LoadingStage.SP_STATISTICS, 15),
        (LoadingStage.SP_DEPENDENCIES, 10),
        (LoadingStage.TRIGGERS, 5),
        (LoadingStage.TRIGGER_STATISTICS, 5),
        (LoadingStage.VIEWS, 5),
        (LoadingStage.VIEW_DEPENDENCIES, 5),
        (LoadingStage.INDEXES, 8),
        (LoadingStage.MISSING_INDEXES, 10),
        (LoadingStage.UNUSED_INDEXES, 8),
        (LoadingStage.INDEX_FRAGMENTATION, 7),
        (LoadingStage.WAIT_STATISTICS, 5),
        (LoadingStage.ACTIVE_SESSIONS, 5),
    ]
    
    def __init__(self, db_connection, query_executor):
        super().__init__()
        self.db = db_connection
        self.executor = query_executor
        self.metadata = PreloadedMetadata()
        self._cancelled = False
        self._start_time = 0
    
    async def preload_all(self) -> PreloadedMetadata:
        """Load all metadata with progress updates"""
        import time
        self._start_time = time.time()
        self._cancelled = False
        
        total_weight = sum(w for _, w in self.STAGES)
        completed_weight = 0
        
        try:
            for stage, weight in self.STAGES:
                if self._cancelled:
                    self.loading_cancelled.emit()
                    return None
                
                # Update progress
                progress = LoadingProgress(
                    stage=stage,
                    current=completed_weight,
                    total=total_weight,
                    message=f"Loading {stage.value}..."
                )
                self.progress_updated.emit(progress)
                
                # Execute stage loader
                await self._load_stage(stage)
                
                completed_weight += weight
                self.stage_completed.emit(stage)
            
            # Finalize
            self.metadata.load_time = time.time() - self._start_time
            self.metadata.loaded_at = time.strftime("%Y-%m-%d %H:%M:%S")
            
            self.loading_completed.emit(self.metadata)
            return self.metadata
            
        except Exception as e:
            self.loading_failed.emit(str(e))
            raise
    
    async def _load_stage(self, stage: LoadingStage):
        """Load specific metadata stage"""
        
        if stage == LoadingStage.SERVER_INFO:
            self.metadata.server_info = await self._load_server_info()
            
        elif stage == LoadingStage.STORED_PROCEDURES:
            self.metadata.stored_procedures = await self._load_stored_procedures()
            
        elif stage == LoadingStage.SP_STATISTICS:
            self.metadata.sp_statistics = await self._load_sp_statistics()
            
        elif stage == LoadingStage.SP_DEPENDENCIES:
            self.metadata.sp_dependencies = await self._load_sp_dependencies()
            
        elif stage == LoadingStage.TRIGGERS:
            self.metadata.triggers = await self._load_triggers()
            
        elif stage == LoadingStage.TRIGGER_STATISTICS:
            self.metadata.trigger_statistics = await self._load_trigger_statistics()
            
        elif stage == LoadingStage.VIEWS:
            self.metadata.views = await self._load_views()
            
        elif stage == LoadingStage.VIEW_DEPENDENCIES:
            self.metadata.view_dependencies = await self._load_view_dependencies()
            
        elif stage == LoadingStage.MISSING_INDEXES:
            self.metadata.missing_indexes = await self._load_missing_indexes()
            
        elif stage == LoadingStage.UNUSED_INDEXES:
            self.metadata.unused_indexes = await self._load_unused_indexes()
            
        elif stage == LoadingStage.INDEX_FRAGMENTATION:
            self.metadata.index_fragmentation = await self._load_index_fragmentation()
            
        elif stage == LoadingStage.WAIT_STATISTICS:
            self.metadata.wait_statistics = await self._load_wait_statistics()
            
        elif stage == LoadingStage.ACTIVE_SESSIONS:
            self.metadata.active_sessions = await self._load_active_sessions()
            self.metadata.blocking_chains = await self._load_blocking_chains()
    
    def cancel(self):
        """Cancel loading"""
        self._cancelled = True
    
    # === Stage Loaders ===
    
    async def _load_stored_procedures(self) -> List[dict]:
        """Load all stored procedures with code"""
        query = """
        SELECT 
            p.object_id,
            SCHEMA_NAME(p.schema_id) AS schema_name,
            p.name AS sp_name,
            p.create_date,
            p.modify_date,
            m.definition AS sp_code,
            LEN(m.definition) AS code_length
        FROM sys.procedures p
        INNER JOIN sys.sql_modules m ON p.object_id = m.object_id
        WHERE p.is_ms_shipped = 0
        ORDER BY p.name
        """
        return await self.executor.execute_query(query)
    
    async def _load_sp_statistics(self) -> Dict[str, dict]:
        """Load SP execution statistics"""
        query = """
        SELECT 
            OBJECT_SCHEMA_NAME(ps.object_id) AS schema_name,
            OBJECT_NAME(ps.object_id) AS sp_name,
            ps.execution_count,
            ps.total_elapsed_time / 1000.0 AS total_elapsed_ms,
            ps.total_elapsed_time / NULLIF(ps.execution_count, 0) / 1000.0 AS avg_elapsed_ms,
            ps.total_logical_reads,
            ps.total_logical_reads / NULLIF(ps.execution_count, 0) AS avg_logical_reads,
            ps.total_physical_reads,
            ps.total_physical_reads / NULLIF(ps.execution_count, 0) AS avg_physical_reads,
            ps.total_worker_time / 1000.0 AS total_cpu_ms,
            ps.total_worker_time / NULLIF(ps.execution_count, 0) / 1000.0 AS avg_cpu_ms,
            ps.cached_time,
            ps.last_execution_time,
            ps.last_elapsed_time / 1000.0 AS last_elapsed_ms
        FROM sys.dm_exec_procedure_stats ps
        WHERE OBJECT_NAME(ps.object_id) IS NOT NULL
          AND ps.database_id = DB_ID()
        ORDER BY ps.total_elapsed_time DESC
        """
        rows = await self.executor.execute_query(query)
        return {f"{r['schema_name']}.{r['sp_name']}": r for r in rows}
    
    async def _load_sp_dependencies(self) -> Dict[str, List[dict]]:
        """Load SP dependencies (tables, views used)"""
        query = """
        SELECT 
            OBJECT_SCHEMA_NAME(d.referencing_id) AS sp_schema,
            OBJECT_NAME(d.referencing_id) AS sp_name,
            d.referenced_schema_name,
            d.referenced_entity_name,
            o.type_desc AS referenced_type
        FROM sys.sql_expression_dependencies d
        LEFT JOIN sys.objects o ON d.referenced_id = o.object_id
        WHERE OBJECTPROPERTY(d.referencing_id, 'IsProcedure') = 1
        ORDER BY sp_name, referenced_entity_name
        """
        rows = await self.executor.execute_query(query)
        
        # Group by SP
        deps = {}
        for r in rows:
            key = f"{r['sp_schema']}.{r['sp_name']}"
            if key not in deps:
                deps[key] = []
            deps[key].append(r)
        return deps
    
    async def _load_triggers(self) -> List[dict]:
        """Load all triggers with code and status"""
        query = """
        SELECT 
            t.object_id,
            SCHEMA_NAME(t.schema_id) AS schema_name,
            t.name AS trigger_name,
            OBJECT_NAME(t.parent_id) AS parent_table,
            t.is_disabled,
            t.is_instead_of_trigger,
            t.create_date,
            t.modify_date,
            m.definition AS trigger_code,
            te.type_desc AS trigger_event
        FROM sys.triggers t
        INNER JOIN sys.sql_modules m ON t.object_id = m.object_id
        LEFT JOIN sys.trigger_events te ON t.object_id = te.object_id
        WHERE t.is_ms_shipped = 0
        ORDER BY t.name
        """
        return await self.executor.execute_query(query)
    
    async def _load_trigger_statistics(self) -> Dict[str, dict]:
        """Load trigger execution statistics"""
        query = """
        SELECT 
            OBJECT_SCHEMA_NAME(ts.object_id) AS schema_name,
            OBJECT_NAME(ts.object_id) AS trigger_name,
            ts.execution_count,
            ts.total_elapsed_time / 1000.0 AS total_elapsed_ms,
            ts.total_elapsed_time / NULLIF(ts.execution_count, 0) / 1000.0 AS avg_elapsed_ms,
            ts.total_logical_reads,
            ts.total_logical_reads / NULLIF(ts.execution_count, 0) AS avg_logical_reads,
            ts.total_worker_time / 1000.0 AS total_cpu_ms,
            ts.total_worker_time / NULLIF(ts.execution_count, 0) / 1000.0 AS avg_cpu_ms,
            ts.cached_time,
            ts.last_execution_time
        FROM sys.dm_exec_trigger_stats ts
        WHERE OBJECT_NAME(ts.object_id) IS NOT NULL
          AND ts.database_id = DB_ID()
        """
        rows = await self.executor.execute_query(query)
        return {f"{r['schema_name']}.{r['trigger_name']}": r for r in rows}
    
    async def _load_views(self) -> List[dict]:
        """Load all views with code"""
        query = """
        SELECT 
            v.object_id,
            SCHEMA_NAME(v.schema_id) AS schema_name,
            v.name AS view_name,
            v.create_date,
            v.modify_date,
            m.definition AS view_code,
            CASE WHEN EXISTS (
                SELECT 1 FROM sys.indexes i 
                WHERE i.object_id = v.object_id AND i.type > 0
            ) THEN 1 ELSE 0 END AS is_indexed
        FROM sys.views v
        INNER JOIN sys.sql_modules m ON v.object_id = m.object_id
        WHERE v.is_ms_shipped = 0
        ORDER BY v.name
        """
        return await self.executor.execute_query(query)
    
    async def _load_view_dependencies(self) -> Dict[str, List[dict]]:
        """Load view dependencies"""
        query = """
        SELECT 
            OBJECT_SCHEMA_NAME(d.referencing_id) AS view_schema,
            OBJECT_NAME(d.referencing_id) AS view_name,
            d.referenced_schema_name,
            d.referenced_entity_name,
            o.type_desc AS referenced_type
        FROM sys.sql_expression_dependencies d
        LEFT JOIN sys.objects o ON d.referenced_id = o.object_id
        WHERE OBJECTPROPERTY(d.referencing_id, 'IsView') = 1
        ORDER BY view_name, referenced_entity_name
        """
        rows = await self.executor.execute_query(query)
        
        deps = {}
        for r in rows:
            key = f"{r['view_schema']}.{r['view_name']}"
            if key not in deps:
                deps[key] = []
            deps[key].append(r)
        return deps
    
    async def _load_missing_indexes(self) -> List[dict]:
        """Load missing index recommendations"""
        query = """
        SELECT TOP 50
            OBJECT_SCHEMA_NAME(d.object_id) AS schema_name,
            OBJECT_NAME(d.object_id) AS table_name,
            d.equality_columns,
            d.inequality_columns,
            d.included_columns,
            gs.user_seeks,
            gs.user_scans,
            gs.avg_total_user_cost,
            gs.avg_user_impact,
            gs.user_seeks * gs.avg_total_user_cost * gs.avg_user_impact AS improvement_measure,
            'CREATE INDEX [IX_' + OBJECT_NAME(d.object_id) + '_' 
                + REPLACE(REPLACE(REPLACE(ISNULL(d.equality_columns,''), ', ', '_'), '[', ''), ']', '') 
                + '] ON ' + d.statement 
                + ' (' + ISNULL(d.equality_columns, '') 
                + CASE WHEN d.equality_columns IS NOT NULL AND d.inequality_columns IS NOT NULL THEN ', ' ELSE '' END 
                + ISNULL(d.inequality_columns, '') + ')'
                + ISNULL(' INCLUDE (' + d.included_columns + ')', '') AS create_statement
        FROM sys.dm_db_missing_index_details d
        INNER JOIN sys.dm_db_missing_index_groups g ON d.index_handle = g.index_handle
        INNER JOIN sys.dm_db_missing_index_group_stats gs ON g.index_group_handle = gs.group_handle
        WHERE d.database_id = DB_ID()
        ORDER BY improvement_measure DESC
        """
        return await self.executor.execute_query(query)
    
    async def _load_unused_indexes(self) -> List[dict]:
        """Load unused indexes"""
        query = """
        SELECT 
            OBJECT_SCHEMA_NAME(i.object_id) AS schema_name,
            OBJECT_NAME(i.object_id) AS table_name,
            i.name AS index_name,
            i.type_desc AS index_type,
            ius.user_seeks,
            ius.user_scans,
            ius.user_lookups,
            ius.user_updates,
            (SELECT SUM(ps.reserved_page_count) * 8 / 1024.0
             FROM sys.dm_db_partition_stats ps
             WHERE ps.object_id = i.object_id AND ps.index_id = i.index_id) AS size_mb,
            'DROP INDEX [' + i.name + '] ON [' + SCHEMA_NAME(o.schema_id) + '].[' + OBJECT_NAME(i.object_id) + ']' AS drop_statement
        FROM sys.indexes i
        INNER JOIN sys.objects o ON i.object_id = o.object_id
        LEFT JOIN sys.dm_db_index_usage_stats ius ON i.object_id = ius.object_id 
            AND i.index_id = ius.index_id AND ius.database_id = DB_ID()
        WHERE o.type = 'U'
          AND i.type > 0
          AND i.is_primary_key = 0
          AND i.is_unique_constraint = 0
          AND ISNULL(ius.user_seeks, 0) = 0
          AND ISNULL(ius.user_scans, 0) = 0
          AND ISNULL(ius.user_lookups, 0) = 0
        ORDER BY size_mb DESC
        """
        return await self.executor.execute_query(query)
    
    async def _load_index_fragmentation(self) -> List[dict]:
        """Load index fragmentation (sampled mode for performance)"""
        query = """
        SELECT 
            OBJECT_SCHEMA_NAME(ips.object_id) AS schema_name,
            OBJECT_NAME(ips.object_id) AS table_name,
            i.name AS index_name,
            i.type_desc AS index_type,
            ips.avg_fragmentation_in_percent AS fragmentation_pct,
            ips.page_count,
            ips.page_count * 8 / 1024.0 AS size_mb,
            CASE 
                WHEN ips.avg_fragmentation_in_percent > 30 THEN 'REBUILD'
                WHEN ips.avg_fragmentation_in_percent > 10 THEN 'REORGANIZE'
                ELSE 'OK'
            END AS recommendation
        FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'SAMPLED') ips
        INNER JOIN sys.indexes i ON ips.object_id = i.object_id AND ips.index_id = i.index_id
        WHERE ips.avg_fragmentation_in_percent > 10
          AND ips.page_count > 1000
        ORDER BY ips.avg_fragmentation_in_percent DESC
        """
        return await self.executor.execute_query(query)
    
    async def _load_wait_statistics(self) -> List[dict]:
        """Load wait statistics"""
        query = """
        SELECT TOP 20
            wait_type,
            waiting_tasks_count,
            wait_time_ms,
            wait_time_ms / NULLIF(waiting_tasks_count, 0) AS avg_wait_ms,
            max_wait_time_ms,
            signal_wait_time_ms,
            wait_time_ms - signal_wait_time_ms AS resource_wait_ms,
            100.0 * wait_time_ms / SUM(wait_time_ms) OVER() AS pct
        FROM sys.dm_os_wait_stats
        WHERE wait_type NOT IN (
            'CLR_SEMAPHORE', 'LAZYWRITER_SLEEP', 'RESOURCE_QUEUE',
            'SLEEP_TASK', 'SLEEP_SYSTEMTASK', 'SQLTRACE_BUFFER_FLUSH',
            'WAITFOR', 'LOGMGR_QUEUE', 'CHECKPOINT_QUEUE',
            'REQUEST_FOR_DEADLOCK_SEARCH', 'XE_TIMER_EVENT',
            'BROKER_TO_FLUSH', 'BROKER_TASK_STOP', 'CLR_MANUAL_EVENT',
            'CLR_AUTO_EVENT', 'DISPATCHER_QUEUE_SEMAPHORE',
            'FT_IFTS_SCHEDULER_IDLE_WAIT', 'XE_DISPATCHER_WAIT',
            'XE_DISPATCHER_JOIN', 'SQLTRACE_INCREMENTAL_FLUSH_SLEEP',
            'ONDEMAND_TASK_QUEUE', 'BROKER_EVENTHANDLER',
            'SLEEP_BPOOL_FLUSH', 'DIRTY_PAGE_POLL', 'HADR_FILESTREAM_IOMGR_IOCOMPLETION'
        )
        AND waiting_tasks_count > 0
        ORDER BY wait_time_ms DESC
        """
        return await self.executor.execute_query(query)
    
    async def _load_active_sessions(self) -> List[dict]:
        """Load active sessions and queries"""
        query = """
        SELECT 
            r.session_id,
            r.status,
            r.command,
            r.wait_type,
            r.wait_time,
            r.blocking_session_id,
            r.cpu_time,
            r.total_elapsed_time / 1000.0 AS elapsed_sec,
            r.logical_reads,
            r.writes,
            DB_NAME(r.database_id) AS database_name,
            s.login_name,
            s.host_name,
            s.program_name,
            t.text AS query_text,
            SUBSTRING(t.text, r.statement_start_offset/2 + 1,
                (CASE WHEN r.statement_end_offset = -1 
                    THEN LEN(CONVERT(nvarchar(max), t.text)) * 2
                    ELSE r.statement_end_offset 
                END - r.statement_start_offset) / 2 + 1) AS current_statement
        FROM sys.dm_exec_requests r
        INNER JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
        CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) t
        WHERE r.session_id <> @@SPID
          AND s.is_user_process = 1
        ORDER BY r.total_elapsed_time DESC
        """
        return await self.executor.execute_query(query)
    
    async def _load_blocking_chains(self) -> List[dict]:
        """Load blocking chains"""
        query = """
        SELECT 
            r.session_id AS blocked_session,
            r.blocking_session_id AS blocking_session,
            r.wait_type,
            r.wait_time / 1000.0 AS wait_sec,
            blocked_text.text AS blocked_query,
            blocking_text.text AS blocking_query,
            DB_NAME(r.database_id) AS database_name
        FROM sys.dm_exec_requests r
        INNER JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
        CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) blocked_text
        OUTER APPLY (
            SELECT t.text
            FROM sys.dm_exec_requests r2
            CROSS APPLY sys.dm_exec_sql_text(r2.sql_handle) t
            WHERE r2.session_id = r.blocking_session_id
        ) blocking_text
        WHERE r.blocking_session_id > 0
        ORDER BY r.wait_time DESC
        """
        return await self.executor.execute_query(query)
```

### 8.8 Loading Progress Dialog

```python
# app/ui/dialogs/loading_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, 
    QPushButton, QHBoxLayout, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

class MetadataLoadingDialog(QDialog):
    """Progress dialog for metadata pre-loading"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading Database Metadata")
        self.setModal(True)
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self._cancelled = False
        self._start_time = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel("ðŸš€ Loading Database Metadata")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        self.subtitle = QLabel("Preparing Object Explorer...")
        self.subtitle.setStyleSheet("color: #888888; font-size: 14px;")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle)
        
        layout.addSpacing(8)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                background-color: #242424;
                height: 24px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0066ff, stop:1 #00aa66);
                border-radius: 7px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Stage list
        self.stage_list = QListWidget()
        self.stage_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 4px 8px;
            }
        """)
        layout.addWidget(self.stage_list)
        
        # Time info
        self.time_label = QLabel("Elapsed: 0.0s")
        self.time_label.setStyleSheet("color: #888888; font-size: 12px;")
        layout.addWidget(self.time_label)
        
        # Cancel button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                color: white;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # Timer for elapsed time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_time)
    
    def start(self):
        """Start loading timer"""
        import time
        self._start_time = time.time()
        self.timer.start(100)
        self.show()
    
    def update_progress(self, progress):
        """Update progress bar and current stage"""
        self.progress_bar.setValue(int(progress.percentage))
        self.subtitle.setText(progress.message)
    
    def mark_stage_complete(self, stage):
        """Mark a stage as completed"""
        item = QListWidgetItem(f"âœ… {stage.value}")
        item.setForeground(QColor("#4ade80"))
        self.stage_list.addItem(item)
        self.stage_list.scrollToBottom()
    
    def mark_stage_loading(self, stage):
        """Show currently loading stage"""
        item = QListWidgetItem(f"ðŸ”„ {stage.value}...")
        item.setForeground(QColor("#60a5fa"))
        self.stage_list.addItem(item)
        self.stage_list.scrollToBottom()
    
    def _update_time(self):
        """Update elapsed time display"""
        import time
        if self._start_time:
            elapsed = time.time() - self._start_time
            self.time_label.setText(f"Elapsed: {elapsed:.1f}s")
    
    def _on_cancel(self):
        self._cancelled = True
        self.reject()
    
    @property
    def cancelled(self):
        return self._cancelled
```

### 8.9 Animations (QPropertyAnimation)

```python
# Sidebar collapse animation örneği
self.animation = QPropertyAnimation(self.sidebar, b"minimumWidth")
self.animation.setDuration(200)
self.animation.setStartValue(220)
self.animation.setEndValue(60)
self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
self.animation.start()
```

---

## 9. Modül Yapısı ve Sorumlulukları

### 9.1 Proje Dizin Yapısı

```
sql-perf-ai/
#
#-- app/
#   #-- __init__.py
#   #-- main.py                      # PyQt6 entry point
#   #
#   #-- core/
#   #   #-- __init__.py
#   #   #-- config.py                # Ayar yönetimi
#   #   #-- constants.py             # Sabitler
#   #   #-- exceptions.py            # Ã–zel exception'lar
#   #   #-- language_manager.py      # Ã‡oklu dil yönetimi
#   #   #-- cache_manager.py         # Multi-level caching
#   #   -”-- task_manager.py          # Async task orchestration
#   #
#   #-- models/
#   #   #-- __init__.py
#   #   -”-- connection_profile.py    # Connection profil dataclass
#   #
#   #-- auth/
#   #   #-- __init__.py
#   #   #-- auth_manager.py          # Ana auth orchestrator
#   #   #-- ldap_provider.py         # LDAP authentication
#   #   -”-- mssql_provider.py        # MSSQL authentication
#   #
#   #-- database/
#   #   #-- __init__.py
#   #   #-- connection.py            # DB bağlantı yönetimi
#   #   #-- version_detector.py      # SQL Server version tespiti
#   #   #-- query_library.py         # Version-aware template sorgular
#   #   #-- query_executor.py        # Güvenli query Çalıştırma
#   #   #-- cached_executor.py       # Cache destekli executor
#   #   -”-- collectors/
#   #       #-- __init__.py
#   #       #-- sp_collector.py      # SP bilgileri
#   #       #-- trigger_collector.py # Trigger bilgileri
#   #       #-- view_collector.py    # View bilgileri
#   #       #-- index_collector.py   # Index bilgileri
#   #       -”-- stats_collector.py   # Statistics bilgileri
#   #
#   #-- analysis/
#   #   #-- __init__.py
#   #   #-- sql_parser.py            # SQL parsing
#   #   #-- execution_plan.py        # Plan analizi
#   #   #-- code_comparator.py       # Kod karşılaştırma
#   #   -”-- summary_builder.py       # LLM context hazırlama
#   #
#   #-- ai/
#   #   #-- __init__.py
#   #   #-- llm_client.py            # LLM bağlantı client
#   #   #-- intent/
#   #   #   #-- __init__.py
#   #   #   #-- detector.py          # Intent detection
#   #   #   #-- mapper.py            # Intent â†’ template
#   #   #   -”-- parameter_extractor.py
#   #   #-- code_generator/
#   #   #   #-- __init__.py
#   #   #   #-- sp_optimizer.py      # SP optimizasyonu
#   #   #   #-- trigger_optimizer.py # Trigger optimizasyonu
#   #   #   -”-- view_optimizer.py    # View optimizasyonu
#   #   -”-- prompts/
#   #       #-- __init__.py
#   #       #-- intent_prompts.py
#   #       #-- analysis_prompts.py
#   #       -”-- optimization_prompts.py
#   #
#   #-- ui/
#   #   #-- __init__.py
#   #   #-- main_window.py           # QMainWindow - Ana pencere
#   #   #-- theme.py                 # QSS tema yönetimi (Dark/Light)
#   #   #-- resources.py             # İkonlar, assets yönetimi
#   #   #-- components/
#   #   #   #-- __init__.py
#   #   #   #-- sidebar.py           # QWidget - Navigation sidebar
#   #   #   #-- header.py            # QWidget - App header
#   #   #   #-- chat_input.py        # QFrame - Chat input with send button
#   #   #   #-- chat_message.py      # QFrame - Chat bubble widget
#   #   #   #-- suggestion_button.py # QPushButton - Ã–neri kartları
#   #   #   #-- code_editor.py       # QScintilla - SQL syntax highlighting
#   #   #   #-- code_diff_viewer.py  # QSplitter - Side-by-side diff
#   #   #   #-- result_table.py      # QTableView - Virtual scrolling data
#   #   #   #-- connection_card.py   # QFrame - Bağlantı kartı widget
#   #   #   #-- connection_tree.py   # QTreeView - Klasör/connection ağacı
#   #   #   #-- plan_viewer.py       # Execution plan görüntüleme
#   #   #   #-- progress_dialog.py   # QProgressDialog - Async operations
#   #   #   -”-- validation_dialog.py # QDialog - AI output validation
#   #   #-- views/
#   #   #   #-- __init__.py
#   #   #   #-- chat_view.py         # Ana chat arayüzü (Perplexity-style)
#   #   #   #-- dashboard_view.py    # Server overview, quick stats
#   #   #   #-- sp_explorer_view.py  # QTreeView + QScintilla
#   #   #   #-- query_stats_view.py  # Top queries, filters
#   #   #   #-- index_advisor_view.py# Missing/unused index
#   #   #   #-- security_view.py     # Security analysis results
#   #   #   #-- wait_stats_view.py   # Wait statistics
#   #   #   #-- jobs_view.py         # SQL Agent jobs
#   #   #   #-- comparison_view.py   # Before/after comparison
#   #   #   #-- connection_manager_view.py  # Bağlantı yönetimi
#   #   #   #-- connection_dialog.py # QDialog - Add/Edit connection
#   #   #   -”-- settings_view.py     # QTabWidget - Ayarlar
#   #   -”-- styles/
#   #       #-- __init__.py
#   #       #-- dark_theme.qss       # Koyu tema QSS
#   #       -”-- light_theme.qss      # AÇık tema QSS
#   #
#   -”-- services/
#       #-- __init__.py
#       #-- connection_store.py      # Bağlantı CRUD, import/export
#       #-- credential_store.py      # OS keyring ile şifre saklama
#       #-- optimization_service.py  # SP optimize workflow
#       #-- comparison_service.py    # Before/after karşılaştırma
#       #-- security_analyzer.py     # SQL güvenlik analizi
#       #-- comprehensive_analyzer.py # Kapsamlı performans analizi
#       #-- output_validator.py      # AI Çıktı doğrulama (3 katman)
#       -”-- validated_ai_service.py  # Doğrulamalı AI servisi
#
#-- prompts/
#   -”-- prompts.yaml                 # LLM prompt şablonları
#
#-- locales/
#   #-- languages.json               # Dil meta bilgisi
#   #-- en.json
#   #-- tr.json
#   -”-- custom/                      # Kullanıcı eklediği diller
#
#-- assets/
#   #-- icons/
#   #-- fonts/
#   -”-- images/
#
#-- tests/
#   #-- __init__.py
#   #-- test_auth/
#   #-- test_database/
#   #-- test_analysis/
#   -”-- test_ai/
#
#-- scripts/
#   #-- build_windows.py
#   -”-- create_installer.py
#
#-- pyproject.toml
#-- README.md
-”-- .env.example
```

### 9.2 Modül Sorumlulukları

| Modül | Sorumluluk | Tahmini Satır |
|-------|------------|---------------|
| `core/` | Config, sabitler, exceptions, language, cache, task manager | ~800 |
| `models/` | Data classes (ConnectionProfile vb.) | ~200 |
| `auth/` | LDAP, MSSQL auth, session | ~500 |
| `database/` | Bağlantı, version detection, query library, cached executor, collectors | ~1200 |
| `analysis/` | SQL parsing, plan, karşılaştırma | ~600 |
| `ai/` | LLM client, intent, code gen | ~700 |
| `ui/components/` | Tekrar kullanılabilir UI, connection widgets, dialogs | ~1400 |
| `ui/views/` | Ekranlar, connection manager | ~1800 |
| `services/` | Connection store, security analyzer, output validator, workflows | ~1200 |

---

## 10. SP Studio'dan Migration Planı

### 10.1 Taşınabilir Modüller

| Mevcut Modül | Yeni Projede | Değişiklik |
|--------------|--------------|------------|
| `llm_client.py` | `app/ai/llm_client.py` | Minimal refactor |
| `db_connection.py` | `app/database/connection.py` | pyqt6 uyumlu |
| `enhanced_statistics.py` | `app/database/collectors/stats_collector.py` | Genişlet |
| `sql_parser.py` | `app/analysis/sql_parser.py` | Aynen kullan |
| `summary_builder.py` | `app/analysis/summary_builder.py` | Genişlet |
| `config_manager.py` | `app/core/config.py` | pyqt6 settings'e adapte |
| `prompts.yaml` | `prompts/prompts.yaml` | Genişlet |

### 10.2 Yeniden Yazılacak Modüller

| Modül | Neden |
|-------|-------|
| `ui_components.py` | Tkinter â†’ pyqt6 dönüşümü |
| `main.py` | Tamamen yeni pyqt6 yapısı |

### 10.3 Migration Adımları

1. **Faz 1:** Core modülleri taşı (config, exceptions)
2. **Faz 2:** Database layer'ı taşı ve adapte et
3. **Faz 3:** AI modüllerini taşı
4. **Faz 4:** pyqt6 UI'ı sıfırdan yaz
5. **Faz 5:** Entegrasyon ve test

---

## 11. MVP Yol Haritası

### 11.1 Faz 1: Temel Altyapı (Hafta 1-3)

| Ã–zellik | AÇıklama | Ã–ncelik |
|---------|----------|---------|
| pyqt6 Kurulum | Proje yapısı, tema, temel layout | P0 |
| Config Manager | Ayarlar, dil seÇimi, tema | P0 |
| MSSQL Bağlantı | Connection manager, test bağlantı | P0 |
| Login Ekranı | MSSQL Auth ile giriş | P0 |

### 11.2 Faz 2: AI Entegrasyonu (Hafta 4-6)

| Ã–zellik | AÇıklama | Ã–ncelik |
|---------|----------|---------|
| Ollama Bağlantı | Provider, model listesi | P0 |
| Intent Detection | Doğal dil â†’ intent | P0 |
| Query Selector | Intent â†’ template eşleştirme | P0 |
| Response Generator | AI yanıt üretimi | P0 |

### 11.3 Faz 3: DBA Dashboard (Hafta 7-9)

| Ã–zellik | AÇıklama | Ã–ncelik |
|---------|----------|---------|
| Ana Dashboard | Server overview, quick stats | P0 |
| Doğal Dil Arama | Soru sor, cevap al | P0 |
| Query SonuÇ Grid | SonuÇları tabloda göster | P0 |
| AI Analiz Paneli | Performans önerileri | P0 |

### 11.4 Faz 4: Analiz Ã–zellikleri (Hafta 10-12)

| Ã–zellik | AÇıklama | Ã–ncelik |
|---------|----------|---------|
| SP Explorer | Liste, kod görüntüleme | P1 |
| Kod Optimizasyonu | AI-powered SP/Trigger/View tune | P1 |
| Karşılaştırma View | Eski vs yeni kod | P1 |
| Execution Plan Ã–zet | Metin tabanlı plan analizi | P1 |

### 11.5 Faz 5: Enterprise Features (Hafta 13-16)

| Ã–zellik | AÇıklama | Ã–ncelik |
|---------|----------|---------|
| LDAP Auth | Active Directory entegrasyonu | P2 |
| Ã‡oklu Dil | TR/EN/DE desteği | P2 |
| Lisanslama | Subscription sistemi | P2 |
| Installer | Windows MSI paketi | P2 |

---

## 12. Prompt Åžablonları

### 12.1 Mevcut Promptlar (prompts.yaml'dan)

SP Studio'da kullanılan promptlar iki ana kategoride:

**1. analyze_performance:** Performans analizi prompt'u
- SP kodunu ve JSON context'i alır
- Performans bulgularını analiz eder
- Ã–ncelikli aksiyon planı oluşturur
- Güvenlik ve data quality riskleri değerlendirir

**2. optimize_sql:** SP yeniden yazma prompt'u
- Mevcut SP'yi analiz eder
- Optimize edilmiş versiyon üretir
- İş mantığını korur
- Güvenlik iyileştirmeleri ekler

### 12.2 Prompt Ã–zellikleri

- **Ã‡oklu dil desteği:** TürkÇe ve İngilizce
- **Sıkı kısıtlamalar:** Veri eksikliğinde tahmin yapma, server config değiştirme yasak
- **Güvenlik odaklı:** Data conversion, locking, transaction safety analizi
- **Markdown Çıktı:** Yapılandırılmış, okunabilir format

---

## 13. Güvenlik ve Authentication

### 13.1 Desteklenen Auth Yöntemleri

| Yöntem | Hedef Kullanıcı | AÇıklama |
|--------|-----------------|----------|
| **MSSQL Auth** | Bireysel, küÇük ekipler | SQL Server kullanıcı/şifre |
| **LDAP/AD** | Kurumsal müşteriler | Active Directory entegrasyonu |

### 13.2 Session Yönetimi

- Token-based session
- Secure credential storage (keyring)
- Session timeout
- Audit logging (ileride)

---

## 14. Ã‡oklu Dil Desteği

### 14.1 Desteklenen Diller

Sistem esnek ve genişletilebilir bir dil yapısına sahiptir:

- TürkÇe (tr) - Tam destek
- English (en) - Tam destek
- Deutsch (de) - Planlanıyor
- æ—¥æœ¬èªž (ja) - Planlanıyor
- ä¸­æ–‡ (zh) - Planlanıyor
- Custom diller eklenebilir

### 14.2 Dil Dosya Yapısı

```
locales/
#-- languages.json    # Desteklenen diller meta bilgisi
#-- tr.json           # TürkÇe Çeviriler
#-- en.json           # İngilizce Çeviriler
#-- de.json           # Almanca Çeviriler
-”-- custom/           # Kullanıcı eklediği diller
    -”-- xx.json
```

### 14.3 languages.json (Meta Dosyası)

```json
{
  "version": "1.0",
  "default_language": "en",
  "supported_languages": [
    {
      "code": "en",
      "name": "English",
      "native_name": "English",
      "direction": "ltr",
      "flag": "ðŸ‡¬ðŸ‡§",
      "ai_instruction": "Respond in English.",
      "complete": true
    },
    {
      "code": "tr",
      "name": "Turkish",
      "native_name": "TürkÇe",
      "direction": "ltr",
      "flag": "ðŸ‡¹ðŸ‡·",
      "ai_instruction": "Tüm yanıtlarını TürkÇe olarak ver.",
      "complete": true
    }
  ]
}
```

### 14.4 Language Manager

```python
class LanguageManager:
    """Flexible Çoklu dil yönetim sistemi"""
    
    def set_language(self, lang_code: str) -> bool:
        """Aktif dili değiştir"""
    
    def get_text(self, key: str, **kwargs) -> str:
        """Ã‡eviri metnini al (örn: 'dashboard.title')"""
    
    def get_ai_instruction(self) -> str:
        """AI iÇin dil talimatını al"""
    
    def detect_system_locale(self) -> str:
        """Sistem dilini tespit et"""
    
    def add_custom_language(self, lang_code, translations, meta) -> bool:
        """Yeni dil ekle"""

# Kullanım
from app.core.language_manager import t
label = t("dashboard.title")  # "Dashboard" veya "Gösterge Paneli"
```

### 14.5 AI Yanıt Dili

- Kullanıcı ayarlarından seÇilen dile göre yanıt
- Prompt'a dil talimatı otomatik eklenir
- UI strings ve AI yanıtları senkronize

---

## 15. SQL Server Version Yönetimi

### 15.1 Neden Gerekli?

Farklı SQL Server versiyonlarında DMV'ler ve özellikler değişiyor:

| Ã–zellik | SQL 2016 | SQL 2017 | SQL 2019 | SQL 2022 |
|---------|----------|----------|----------|----------|
| `sys.dm_exec_query_stats.total_rows` | âŒ | âœ… | âœ… | âœ… |
| `sys.dm_db_page_info` | âŒ | âŒ | âœ… | âœ… |
| Query Store DMVs | âœ… | âœ…+ | âœ…++ | âœ…+++ |
| `OPTIMIZE_FOR_SEQUENTIAL_KEY` | âŒ | âŒ | âœ… | âœ… |
| Intelligent Query Processing | âŒ | Kısmi | âœ… | âœ…+ |

### 15.2 Version Detection

```python
class VersionDetector:
    """SQL Server version ve feature tespiti"""
    
    VERSION_MAP = {
        16: "2022",
        15: "2019", 
        14: "2017",
        13: "2016",
        12: "2014",
        11: "2012"
    }
    
    @staticmethod
    def detect(connection) -> dict:
        """Bağlantıdan version bilgisi Çek"""
        sql = """
        SELECT 
            SERVERPROPERTY('ProductMajorVersion') AS MajorVersion,
            SERVERPROPERTY('ProductMinorVersion') AS MinorVersion,
            SERVERPROPERTY('ProductLevel') AS ProductLevel,
            SERVERPROPERTY('Edition') AS Edition,
            @@VERSION AS FullVersion
        """
        # Returns: {major, minor, edition, friendly_name, features}
```

### 15.3 Version-Aware Query System

```
#------------------------------------------------------------------------------
#                    VERSION-AWARE QUERY SYSTEM                               #
#------------------------------------------------------------------------------¤
#                                                                             #
#  ADIM 1: Bağlantı sonrası versiyon tespiti                                  #
#  #----------------------------------------------------------------------   #
#  #  SonuÇ: MajorVersion=15 â†’ SQL Server 2019                           #   #
#  #  Features: [QUERY_STORE, AUTO_TUNING, ADR]                          #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  ADIM 2: Query Library'den uygun sorguyu seÇ                                #
#  #----------------------------------------------------------------------   #
#  #  query_library.get("top_slow_queries", version="2019")              #   #
#  #                                                                     #   #
#  #  Eğer 2019+ â†’ total_rows, last_rows dahil sorgu                     #   #
#  #  Eğer 2016  â†’ total_rows olmadan basit sorgu                        #   #
#  -”----------------------------------------------------------------------˜   #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 15.4 Query Library Yapısı

```python
class QueryLibrary:
    """Version-aware query template kütüphanesi"""
    
    QUERIES = {
        "top_slow_queries": {
            "description": "En yavaş sorgular",
            "min_version": 13,  # SQL 2016
            "versions": {
                "default": "SELECT ... (basic query)",
                "2017+": "SELECT ... WITH total_rows, last_rows",
                "2019+": "SELECT ... WITH additional metrics"
            }
        },
        
        "query_store_stats": {
            "description": "Query Store istatistikleri",
            "min_version": 13,
            "requires_feature": "QUERY_STORE",
            "versions": { ... }
        },
        
        "intelligent_qp_feedback": {
            "description": "Intelligent Query Processing feedback",
            "min_version": 15,  # SQL 2019+ only
            "versions": { ... }
        }
    }
    
    def get_query(self, query_name: str) -> str | None:
        """Version'a uygun sorguyu döndür"""
    
    def get_available_queries(self) -> list:
        """Bu version iÇin kullanılabilir sorguları listele"""
```

### 15.5 Feature Detection

Bağlantı sonrası aktif özellikler otomatik tespit edilir:

| Feature | Kontrol Yöntemi |
|---------|-----------------|
| Query Store | `sys.databases.is_query_store_on` |
| Auto Tuning | `sys.database_automatic_tuning_options` |
| ADR | `sys.databases.is_accelerated_database_recovery_on` |

---

## 16. Connection Manager Sistemi

### 16.1 Genel Bakış

Kurumsal DBA'ler genellikle onlarca sunucu ve veritabanı yönetir. Connection Manager bu ihtiyacı karşılar.

```
#------------------------------------------------------------------------------
#                      CONNECTION MANAGEMENT SYSTEM                           #
#------------------------------------------------------------------------------¤
#                                                                             #
#  KAYDEDILEN BİLGİLER              KAYDEDILMEYEN BİLGİLER                   #
#  --------------------             ----------------------                   #
#  âœ… Connection Name               âŒ Password                              #
#  âœ… Host / Server                 âŒ API Keys                              #
#  âœ… Instance / Port               âŒ Credentials                           #
#  âœ… Database                                                               #
#  âœ… Username                      ðŸ” Åžifreler her bağlantıda               #
#  âœ… Auth Type                        kullanıcıdan istenir veya             #
#  âœ… Driver Settings                  OS keyring'de saklanır (opsiyonel)    #
#  âœ… Color Tag / Folder                                                     #
#  âœ… Notes                                                                  #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 16.2 Connection Profile

```python
@dataclass
class ConnectionProfile:
    """Bağlantı profili - şifre hariÇ tüm bilgiler"""
    
    # Benzersiz tanımlayıcı
    id: str
    
    # Görünen bilgiler
    name: str                    # "Production - AdventureWorks"
    description: str             # Opsiyonel aÇıklama
    
    # Sunucu bilgileri
    host: str                    # IP veya hostname
    instance: str                # Named instance (opsiyonel)
    port: str                    # Port (opsiyonel)
    database: str                # Varsayılan veritabanı
    
    # Kimlik doğrulama
    auth_type: AuthType          # SQL_AUTH, WINDOWS_AUTH, LDAP_AUTH
    username: str                # SQL Auth iÇin kullanıcı adı
    domain: str                  # LDAP/Windows iÇin domain
    
    # Driver ayarları
    driver: str
    trust_server_certificate: bool
    encrypt: bool
    connection_timeout: int
    command_timeout: int
    
    # Organizasyon
    folder: str                  # Grup/klasör adı
    color: ConnectionColor       # RED, GREEN, BLUE, etc.
    tags: List[str]
    is_favorite: bool
    
    # Meta bilgiler
    created_at: datetime
    last_connected_at: datetime
    connection_count: int
    
    # Tespit edilen bilgiler
    detected_version: str        # "SQL Server 2019"
    detected_edition: str        # "Enterprise Edition"
    
    # Notlar
    notes: str
```

### 16.3 Connection Colors (Ortam Tanıma)

| Renk | Kullanım |
|------|----------|
| ðŸ”´ Red | Production |
| ðŸŸ  Orange | Staging |
| ðŸŸ¡ Yellow | UAT |
| ðŸŸ¢ Green | Development |
| ðŸ”µ Blue | Test |
| ðŸŸ£ Purple | Other |
| âš« Gray | Default |

### 16.4 Connection Store

```python
class ConnectionStore:
    """Bağlantı profillerini dosyada saklar"""
    
    def add(self, profile: ConnectionProfile) -> ConnectionProfile
    def update(self, profile: ConnectionProfile) -> ConnectionProfile
    def delete(self, connection_id: str) -> bool
    def get(self, connection_id: str) -> ConnectionProfile
    def get_all(self) -> List[ConnectionProfile]
    def get_by_folder(self, folder: str) -> List[ConnectionProfile]
    def get_favorites(self) -> List[ConnectionProfile]
    def get_recent(self, limit: int = 5) -> List[ConnectionProfile]
    def search(self, query: str) -> List[ConnectionProfile]
    def export_to_file(self, file_path: str) -> None
    def import_from_file(self, file_path: str) -> int
    def duplicate(self, connection_id: str) -> ConnectionProfile
```

### 16.5 Secure Credential Storage (Opsiyonel)

```python
class CredentialStore:
    """
    OS keyring kullanarak güvenli şifre saklama.
    Kullanıcı "Åžifremi Hatırla" seÇerse kullanılır.
    
    Windows: Windows Credential Manager
    macOS: Keychain
    Linux: Secret Service (GNOME Keyring, KWallet)
    """
    
    @classmethod
    def save_password(cls, connection_id: str, password: str) -> bool
    
    @classmethod
    def get_password(cls, connection_id: str) -> Optional[str]
    
    @classmethod
    def delete_password(cls, connection_id: str) -> bool
    
    @classmethod
    def save_api_key(cls, provider: str, api_key: str) -> bool
    
    @classmethod
    def get_api_key(cls, provider: str) -> Optional[str]
```

### 16.6 UI: Connection Manager

```
#--------------------------------------------------------------------------
#  Connection Manager                                    [+ Yeni] [Import]#
#--------------------------------------------------------------------------¤
#  ðŸ” Ara...                                                              #
#-------------------¬-------------------------------------------------------¤
#                  #                                                      #
#  ðŸ“ Favorites    #   #----------------------------------------------   #
#    â­ PROD-SQL   #   #  PROD-SQL01                                 #   #
#                  #   #  -----------------------------------------  #   #
#  ðŸ“ Production   #   #  Host: 192.168.1.10                         #   #
#    ðŸ”´ PROD-SQL01 #   #  Database: AdventureWorks                   #   #
#    ðŸ”´ PROD-SQL02 #   #  Auth: SQL Authentication                   #   #
#                  #   #  User: sa                                    #   #
#  ðŸ“ Development  #   #  Version: SQL Server 2019 Enterprise        #   #
#    ðŸŸ¢ DEV-SQL01  #   #                                             #   #
#    ðŸŸ¢ DEV-SQL02  #   #  Last connected: 2 hours ago                #   #
#                  #   #  Total connections: 147                      #   #
#  ðŸ“ Test         #   #                                             #   #
#    ðŸ”µ TEST-SQL01 #   #  Notes: Ana production sunucusu.            #   #
#                  #   #                                             #   #
#                  #   #  [Connect] [Edit] [Copy] [Delete]           #   #
#                  #   -”----------------------------------------------˜   #
#                  #                                                      #
-”-------------------´-------------------------------------------------------˜
```

### 16.7 Connection Dialog

```
#--------------------------------------------------------------------------
#  New Connection                                                    [X]  #
#--------------------------------------------------------------------------¤
#                                                                         #
#  Connection Name: [Production - AdventureWorks________________]         #
#                                                                         #
#  -- Server ----------------------------------------------------------   #
#  Host:        [192.168.1.10_______________________________]             #
#  Instance:    [_______________] (or)  Port: [1433__]                    #
#  Database:    [AdventureWorks________________________] [â–¼]              #
#                                                                         #
#  -- Authentication --------------------------------------------------   #
#  Type:        (â€¢) SQL Server  ( ) Windows  ( ) LDAP                     #
#  Username:    [sa_____________________________________]                 #
#  Password:    [â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢â€¢_____________________________]                 #
#               [ ] Remember password (stored securely)                   #
#                                                                         #
#  -- Organization ----------------------------------------------------   #
#  Folder:      [Production________________________] [â–¼]                  #
#  Color:       ðŸ”´ ðŸŸ  ðŸŸ¡ ðŸŸ¢ ðŸ”µ ðŸŸ£ âš«                                        #
#  Tags:        [prod, critical_____________________]                     #
#  [ ] Mark as Favorite                                                   #
#                                                                         #
#              [Test Connection]        [Cancel]  [Save]                  #
-”--------------------------------------------------------------------------˜
```

### 16.8 connections.json Ã–rnek

```json
{
  "version": "1.0",
  "updated_at": "2025-01-21T14:30:00",
  "connections": {
    "uuid-1": {
      "id": "uuid-1",
      "name": "Production - AdventureWorks",
      "host": "192.168.1.10",
      "port": "1433",
      "database": "AdventureWorks",
      "auth_type": "sql_auth",
      "username": "app_user",
      "folder": "Production",
      "color": "red",
      "tags": ["prod", "critical"],
      "is_favorite": true,
      "last_connected_at": "2025-01-21T12:30:00",
      "connection_count": 147,
      "detected_version": "SQL Server 2019",
      "notes": "Ana production sunucusu."
    }
  }
}
```

### 16.9 Ã–zellik Ã–zeti

| Ã–zellik | AÇıklama |
|---------|----------|
| **Ã‡oklu Bağlantı** | Sınırsız sayıda sunucu/veritabanı profili |
| **Güvenli Saklama** | Åžifreler ve API key'ler ASLA dosyada saklanmaz |
| **Opsiyonel Keyring** | "Åžifremi Hatırla" iÇin OS güvenli depolama |
| **Organizasyon** | Klasörler, renkler, tag'ler, favoriler |
| **Import/Export** | Bağlantıları paylaşma (şifresiz) |
| **Son Kullanılanlar** | Hızlı erişim iÇin son bağlantılar |
| **Otomatik Tespit** | Bağlantı sonrası version/edition kaydı |

---

## 17. Kapsamlı Performans Analiz Framework'ü

### 17.1 Analiz Katmanları

Kapsamlı bir performance tuning iÇin bilgiler 5 katmanda toplanır:

```
#------------------------------------------------------------------------------
#                    PERFORMANS ANALİZ KATMANLARI                             #
#------------------------------------------------------------------------------¤
#                                                                             #
#  #----------------------------------------------------------------------   #
#  #  KATMAN 1: SUNUCU KONFİGÃœRASYONU                                    #   #
#  #  â€¢ Versiyon, SP, Edition                                            #   #
#  #  â€¢ Bellek ayarları (min/max server memory)                          #   #
#  #  â€¢ CPU sayısı ve kullanımı                                          #   #
#  #  â€¢ MAXDOP, Cost Threshold for Parallelism                           #   #
#  #  â€¢ İşletim sistemi bilgileri                                        #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  #----------------------------------------------------------------------   #
#  #  KATMAN 2: VERİTABANI KONFİGÃœRASYONU                                #   #
#  #  â€¢ Compatibility level                                              #   #
#  #  â€¢ Dosya boyutları ve büyüme ayarları (mdf, ldf, ndf)               #   #
#  #  â€¢ Dosyaların fiziksel yerleşimi                                    #   #
#  #  â€¢ Auto statistics ayarları                                         #   #
#  #  â€¢ Index maintenance ve fragmentasyon                               #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  #----------------------------------------------------------------------   #
#  #  KATMAN 3: STORED PROCEDURE ANALİZİ                                 #   #
#  #  â€¢ Execution plan (gerÇek ve tahmini)                               #   #
#  #  â€¢ Kullanılan tablo/view istatistikleri                             #   #
#  #  â€¢ Index yapıları (clustered, nonclustered, columnstore)            #   #
#  #  â€¢ View tanımları ve indexed view kontrolü                          #   #
#  #  â€¢ Trigger tanımları ve tetiklenme sıklığı                          #   #
#  #  â€¢ Ã‡alışma süresi, okunan/yazılan satır, CPU kullanımı              #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  #----------------------------------------------------------------------   #
#  #  KATMAN 4: İÅž YÃœKÃœ ANALİZİ                                          #   #
#  #  â€¢ SP Çağrılma sıklığı                                              #   #
#  #  â€¢ Parametre dağılımı (parameter sniffing kontrolü)                 #   #
#  #  â€¢ Concurrent Çalışma durumu                                        #   #
#  #  â€¢ Diğer sorguların etkilenme durumu                                #   #
#  -”----------------------------------------------------------------------˜   #
#                                    #                                        #
#                                    â–¼                                        #
#  #----------------------------------------------------------------------   #
#  #  KATMAN 5: PERFORMANS İSTATİSTİKLERİ                                #   #
#  #  â€¢ Wait statistics                                                  #   #
#  #  â€¢ Disk I/O (read/write latency, throughput)                        #   #
#  #  â€¢ Lock ve deadlock istatistikleri                                  #   #
#  #  â€¢ Memory pressure göstergeleri                                     #   #
#  -”----------------------------------------------------------------------˜   #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 17.2 Veri Toplama Matrisi

| Katman | Veri Kaynağı | Template Query |
|--------|--------------|----------------|
| **Sunucu** | `@@VERSION` | `server_version` |
| **Sunucu** | `sys.configurations` | `server_memory_config`, `server_cpu_config` |
| **Sunucu** | `sys.dm_os_sys_info` | `server_memory_usage` |
| **Sunucu** | `sys.dm_os_host_info` | `server_os_info` |
| **Veritabanı** | `sys.databases` | `database_config` |
| **Veritabanı** | `sys.database_files` | `database_files` |
| **Veritabanı** | `sys.dm_io_virtual_file_stats` | `database_io_stats` |
| **Veritabanı** | `sys.stats`, `sys.dm_db_stats_properties` | `database_statistics_health` |
| **SP** | `sys.sql_modules` | `sp_code` |
| **SP** | `sys.dm_exec_procedure_stats` | `sp_statistics` |
| **SP** | `sys.dm_exec_query_plan` | `get_cached_plan` |
| **SP** | `sys.sql_expression_dependencies` | `sp_dependencies` |
| **İş Yükü** | `sys.dm_exec_procedure_stats` | `sp_execution_history` |
| **İş Yükü** | Query Store | `query_store_sp_history` |
| **İş Yükü** | `sys.dm_exec_query_stats` | `query_multiple_plans` |
| **Performans** | `sys.dm_os_wait_stats` | `wait_stats` |
| **Performans** | `sys.dm_tran_locks` | `current_locks` |
| **Performans** | `sys.dm_db_index_physical_stats` | `index_fragmentation` |

### 17.3 AI Ã–neri Kategorileri

Toplanan veriler ışığında AI şu kategorilerde öneriler üretir:

#### 17.3.1 Execution Plan Analizi

| Tespit | Ã–neri |
|--------|-------|
| Table Scan (büyük tabloda) | Uygun index öner |
| Key Lookup yüksek maliyetli | Covering index öner |
| Sort operasyonu maliyetli | Index ile sort'u ortadan kaldır |
| Hash Match (büyük veri) | Join sırası veya index öner |
| Missing Index Hint | Index script'i üret |
| Outdated Statistics | `UPDATE STATISTICS` öner |

#### 17.3.2 Index Optimizasyonu

| Tespit | Ã–neri |
|--------|-------|
| Fragmentation > 30% | `ALTER INDEX ... REBUILD` |
| Fragmentation 10-30% | `ALTER INDEX ... REORGANIZE` |
| Unused Index | Index drop değerlendir |
| Missing Index | Create script öner |
| Duplicate Index | Gereksiz index'i kaldır |
| Over-indexed Table | Index konsolidasyonu öner |

#### 17.3.3 Query Rewrite

| Tespit | Ã–neri |
|--------|-------|
| Cursor kullanımı | Set-based operasyona Çevir |
| `SELECT *` | Explicit column list |
| Non-SARGable predicate | SARGable forma Çevir |
| Correlated subquery | JOIN'e Çevir |
| `DISTINCT` gereksiz | Kaldır veya EXISTS kullan |
| Temp table gereksiz | CTE veya table variable |
| `COUNT(*)` existence iÇin | `EXISTS` kullan |
| RBAR (Row-By-Agonizing-Row) | Set-based Çözüm öner |

#### 17.3.4 Konfigürasyon Ã–nerileri

| Tespit | Ã–neri |
|--------|-------|
| Max memory Çok düşük | Artır (available RAM'in %80'i) |
| MAXDOP = 0 | CPU sayısına göre ayarla |
| Cost threshold = 5 | İş yüküne göre artır |
| Auto stats off | Aktifleştir |
| Compatibility level eski | Upgrade değerlendir |

#### 17.3.5 Trigger Optimizasyonu

| Tespit | Ã–neri |
|--------|-------|
| Trigger iÇinde cursor | Set-based Çevir |
| Recursive trigger | Derinlik kontrolü |
| Yavaş trigger | İÇeriği optimize et |
| Gereksiz trigger | Kaldır veya disable et |
| INSTEAD OF gereksiz | AFTER trigger değerlendir |

#### 17.3.6 Parameter Sniffing Ã‡özümleri

| Tespit | Ã–neri |
|--------|-------|
| Aynı SP farklı plan süreleri | Lokal değişken kullan |
| Plan variance ratio yüksek | `OPTION(RECOMPILE)` ekle |
| İlk Çalışma atypical parametre | `OPTION(OPTIMIZE FOR)` |
| Query Store'da plan regression | Force good plan |

### 17.4 Analiz Workflow

```
#------------------------------------------------------------------------------
#                      KAPSAMLI ANALİZ WORKFLOW                               #
#------------------------------------------------------------------------------¤
#                                                                             #
#  #------------------                                                        #
#  # BAÅžLAT: Kullanıcı#                                                       #
#  # SP analiz ister #                                                        #
#  -”---------¬---------˜                                                        #
#           #                                                                  #
#           â–¼                                                                  #
#  #----------------------------------------------------------------------   #
#  #  ADIM 1: SUNUCU BİLGİLERİNİ TOPLA (Paralel)                         #   #
#  #  â€¢ server_version           â€¢ server_memory_config                  #   #
#  #  â€¢ server_cpu_config        â€¢ server_memory_usage                   #   #
#  -”----------------------------------------------------------------------˜   #
#           #                                                                  #
#           â–¼                                                                  #
#  #----------------------------------------------------------------------   #
#  #  ADIM 2: VERİTABANI BİLGİLERİNİ TOPLA (Paralel)                     #   #
#  #  â€¢ database_config          â€¢ database_files                        #   #
#  #  â€¢ database_io_stats        â€¢ database_statistics_health            #   #
#  -”----------------------------------------------------------------------˜   #
#           #                                                                  #
#           â–¼                                                                  #
#  #----------------------------------------------------------------------   #
#  #  ADIM 3: SP DETAYLARINI TOPLA                                       #   #
#  #  â€¢ sp_code                  â€¢ sp_statistics                         #   #
#  #  â€¢ sp_dependencies          â€¢ get_cached_plan                       #   #
#  #  â€¢ İlgili tablo index'leri  â€¢ İlgili trigger'lar                    #   #
#  -”----------------------------------------------------------------------˜   #
#           #                                                                  #
#           â–¼                                                                  #
#  #----------------------------------------------------------------------   #
#  #  ADIM 4: İÅž YÃœKÃœ ANALİZİ                                            #   #
#  #  â€¢ sp_execution_history     â€¢ query_multiple_plans                  #   #
#  #  â€¢ parameter_sniffing_check â€¢ Query Store (varsa)                   #   #
#  -”----------------------------------------------------------------------˜   #
#           #                                                                  #
#           â–¼                                                                  #
#  #----------------------------------------------------------------------   #
#  #  ADIM 5: PERFORMANS METRİKLERİ                                      #   #
#  #  â€¢ wait_stats               â€¢ current_locks                         #   #
#  #  â€¢ index_fragmentation      â€¢ trigger_performance                   #   #
#  -”----------------------------------------------------------------------˜   #
#           #                                                                  #
#           â–¼                                                                  #
#  #----------------------------------------------------------------------   #
#  #  ADIM 6: AI ANALİZ & Ã–NERİ ÃœRETİMİ                                  #   #
#  #                                                                     #   #
#  #  Tüm toplanan veriler + SP kodu â†’ AI'a gönder                       #   #
#  #                                                                     #   #
#  #  AI üretir:                                                         #   #
#  #  â€¢ Sorun tespitleri (öncelikli)                                     #   #
#  #  â€¢ Execution plan analizi                                           #   #
#  #  â€¢ Index önerileri (script ile)                                     #   #
#  #  â€¢ Query rewrite önerileri                                          #   #
#  #  â€¢ Konfigürasyon önerileri                                          #   #
#  #  â€¢ Optimize edilmiş SP kodu                                         #   #
#  -”----------------------------------------------------------------------˜   #
#           #                                                                  #
#           â–¼                                                                  #
#  #----------------------------------------------------------------------   #
#  #  ADIM 7: KULLANICIYA SUNUÅž                                          #   #
#  #                                                                     #   #
#  #  â€¢ Ã–zet (kritik bulgular)                                           #   #
#  #  â€¢ Detaylı analiz raporu                                            #   #
#  #  â€¢ Ã–nceliklendirilmiş aksiyon listesi                               #   #
#  #  â€¢ Side-by-side kod karşılaştırma                                   #   #
#  #  â€¢ Ã‡alıştırılabilir script'ler (index, stats, SP)                   #   #
#  -”----------------------------------------------------------------------˜   #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 17.5 Ã–ncelik Matrisi

Ã–neriler şu kriterlere göre önceliklendirilir:

| Ã–ncelik | Kriter | Ã–rnekler |
|---------|--------|----------|
| **ðŸ”´ Kritik** | Immediate business impact | Missing critical index, blocking, deadlock |
| **ðŸŸ  Yüksek** | Significant performance gain | Query rewrite, major index change |
| **ðŸŸ¡ Orta** | Moderate improvement | Statistics update, minor index |
| **ðŸŸ¢ Düşük** | Nice-to-have | Code cleanup, minor config |
| **âšª Bilgi** | Awareness only | Best practice notes |

### 17.6 JSON Context Format

AI'a gönderilen analiz context'i:

```json
{
  "analysis_metadata": {
    "timestamp": "2025-01-21T14:30:00Z",
    "target_object": "dbo.usp_GetOrderDetails",
    "object_type": "STORED_PROCEDURE"
  },
  
  "server_context": {
    "version": "SQL Server 2019 (15.0.4153.1)",
    "edition": "Enterprise Edition (64-bit)",
    "cpu_count": 16,
    "memory_mb": 65536,
    "maxdop": 4,
    "cost_threshold": 50
  },
  
  "database_context": {
    "name": "SalesDB",
    "compatibility_level": 150,
    "auto_create_stats": true,
    "auto_update_stats": true,
    "recovery_model": "FULL",
    "file_io_latency": {
      "data_read_ms": 2.5,
      "data_write_ms": 1.8,
      "log_write_ms": 0.9
    }
  },
  
  "sp_context": {
    "definition": "CREATE PROCEDURE dbo.usp_GetOrderDetails...",
    "execution_count": 15420,
    "avg_duration_ms": 450,
    "avg_logical_reads": 12500,
    "avg_cpu_ms": 180,
    "last_execution": "2025-01-21T14:25:00Z",
    "cached_time": "2025-01-20T08:00:00Z"
  },
  
  "dependencies": {
    "tables": [
      {
        "name": "dbo.Orders",
        "row_count": 5000000,
        "indexes": [
          {"name": "PK_Orders", "type": "CLUSTERED", "columns": ["OrderID"]},
          {"name": "IX_Orders_CustomerID", "type": "NONCLUSTERED", "columns": ["CustomerID"]}
        ],
        "statistics_age_days": 3,
        "fragmentation_percent": 15
      }
    ],
    "views": [],
    "triggers": [
      {
        "name": "tr_Orders_Audit",
        "event": "AFTER INSERT, UPDATE",
        "avg_duration_ms": 5
      }
    ]
  },
  
  "execution_plan_summary": {
    "estimated_cost": 125.5,
    "warnings": ["Missing Index", "Implicit Conversion"],
    "expensive_operators": [
      {"operator": "Clustered Index Scan", "table": "Orders", "cost_percent": 45},
      {"operator": "Hash Match", "cost_percent": 25}
    ],
    "missing_index_hint": {
      "table": "Orders",
      "equality_columns": ["CustomerID", "OrderDate"],
      "include_columns": ["TotalAmount"],
      "impact_percent": 85
    }
  },
  
  "workload_analysis": {
    "executions_per_hour": 642,
    "peak_hours": ["09:00-12:00", "14:00-17:00"],
    "parameter_variance": {
      "detected": true,
      "plan_count": 3,
      "min_duration_ms": 50,
      "max_duration_ms": 2500,
      "variance_ratio": 50
    }
  },
  
  "performance_stats": {
    "top_waits": [
      {"wait_type": "PAGEIOLATCH_SH", "wait_ms": 15000, "percent": 35},
      {"wait_type": "CXPACKET", "wait_ms": 8000, "percent": 18}
    ],
    "lock_issues": {
      "blocked_sessions": 0,
      "deadlocks_last_24h": 0
    }
  }
}
```

### 17.7 Collector Service

```python
# app/services/comprehensive_analyzer.py

class ComprehensiveAnalyzer:
    """Kapsamlı performans analizi servisi"""
    
    async def analyze_sp(self, sp_name: str) -> AnalysisResult:
        """SP iÇin tam kapsamlı analiz"""
        
        # Paralel veri toplama
        server_data, db_data = await asyncio.gather(
            self._collect_server_context(),
            self._collect_database_context()
        )
        
        # SP-specific veri toplama
        sp_data = await self._collect_sp_context(sp_name)
        dependencies = await self._collect_dependencies(sp_name)
        workload = await self._collect_workload_analysis(sp_name)
        perf_stats = await self._collect_performance_stats()
        
        # Context oluştur
        context = self._build_analysis_context(
            server_data, db_data, sp_data, 
            dependencies, workload, perf_stats
        )
        
        # AI analizi
        ai_result = await self.ai_client.analyze(
            sp_code=sp_data.definition,
            context=context,
            prompt_type="comprehensive_analysis"
        )
        
        return AnalysisResult(
            summary=ai_result.summary,
            issues=ai_result.issues,
            recommendations=ai_result.recommendations,
            optimized_code=ai_result.optimized_code,
            scripts=ai_result.scripts,
            context=context
        )
```

---

## 18. SQL Kod Güvenlik Analizi

### 18.1 Güvenlik Analiz Kategorileri

```
#------------------------------------------------------------------------------
#                    SQL KOD GÃœVENLİK ANALİZİ                                 #
#------------------------------------------------------------------------------¤
#                                                                             #
#  ðŸ”´ KRİTİK GÃœVENLİK         ðŸŸ  VERİ BÃœTÃœNLÃœÄžÃœ                              #
#  â€¢ SQL Injection            â€¢ Transaction yönetimi                         #
#  â€¢ Dynamic SQL riskleri     â€¢ Error handling                               #
#  â€¢ Privilege escalation     â€¢ Data conversion                              #
#  â€¢ Hassas veri ifşası       â€¢ Constraint bypass                            #
#                                                                             #
#  ðŸŸ¡ CONCURRENCY & LOCKING   ðŸŸ¢ EN İYİ UYGULAMALAR                          #
#  â€¢ Deadlock riskleri        â€¢ Parametre doğrulama                          #
#  â€¢ Dirty read (NOLOCK)      â€¢ Ownership chaining                           #
#  â€¢ Lost update              â€¢ Least privilege                              #
#  â€¢ Phantom read             â€¢ Audit logging                                #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 18.2 SQL Injection Analizi

#### 18.2.1 Tehlikeli Pattern'ler

| Pattern | Risk | AÇıklama |
|---------|------|----------|
| `EXEC(@sql)` | ðŸ”´ Kritik | Parametresiz dynamic SQL |
| `EXEC('SELECT * FROM ' + @table)` | ðŸ”´ Kritik | String concatenation |
| `sp_executesql` without parameters | ðŸ”´ Kritik | Parametresiz kullanım |
| `QUOTENAME()` eksikliği | ðŸŸ  Yüksek | Object name injection |
| `xp_cmdshell` | ðŸ”´ Kritik | OS command execution |
| `OPENROWSET` / `OPENDATASOURCE` | ðŸŸ  Yüksek | External data access |

#### 18.2.2 Tespit Sorguları

```python
"detect_dynamic_sql": {
    "description": "Dynamic SQL kullanımı tespit et",
    "parameters": ["sp_name"],
    "sql": """
        SELECT 
            OBJECT_NAME(object_id) AS object_name,
            CASE 
                WHEN definition LIKE '%EXEC(%@%+%' THEN 'CRITICAL: String concatenation in EXEC'
                WHEN definition LIKE '%EXEC(@%' THEN 'HIGH: Dynamic SQL with variable'
                WHEN definition LIKE '%sp_executesql%' AND definition NOT LIKE '%@%param%' 
                    THEN 'HIGH: sp_executesql without parameters'
                ELSE 'MEDIUM: Review recommended'
            END AS risk_assessment
        FROM sys.sql_modules
        WHERE object_id = OBJECT_ID(@sp_name)
          AND (definition LIKE '%EXEC(%' OR definition LIKE '%sp_executesql%')
    """
},

"detect_dangerous_commands": {
    "description": "Tehlikeli komutları tespit et",
    "parameters": [],
    "sql": """
        SELECT 
            OBJECT_SCHEMA_NAME(m.object_id) AS schema_name,
            OBJECT_NAME(m.object_id) AS object_name,
            CASE 
                WHEN m.definition LIKE '%xp_cmdshell%' THEN 'CRITICAL: xp_cmdshell'
                WHEN m.definition LIKE '%OPENROWSET%' THEN 'HIGH: OPENROWSET'
                WHEN m.definition LIKE '%OPENDATASOURCE%' THEN 'HIGH: OPENDATASOURCE'
                WHEN m.definition LIKE '%xp_reg%' THEN 'HIGH: Registry access'
                WHEN m.definition LIKE '%BULK INSERT%' THEN 'MEDIUM: BULK INSERT'
            END AS security_concern
        FROM sys.sql_modules m
        WHERE m.definition LIKE '%xp_cmdshell%'
           OR m.definition LIKE '%OPENROWSET%'
           OR m.definition LIKE '%xp_reg%'
    """
}
```

#### 18.2.3 Güvenli vs Güvensiz Ã–rnekler

```sql
-- âŒ GÃœVENSİZ: String concatenation
DECLARE @sql NVARCHAR(MAX)
SET @sql = 'SELECT * FROM Users WHERE Name = ''' + @UserName + ''''
EXEC(@sql)  -- SQL INJECTION AÃ‡IÄžI!

-- âœ… GÃœVENLİ: Parametreli sorgu
DECLARE @sql NVARCHAR(MAX) = N'SELECT * FROM Users WHERE Name = @pName'
EXEC sp_executesql @sql, N'@pName VARCHAR(100)', @pName = @UserName

-- âœ… GÃœVENLİ: Dynamic table with QUOTENAME + whitelist
IF @TableName NOT IN ('Orders', 'Customers', 'Products')
    RAISERROR('Invalid table', 16, 1);
DECLARE @sql NVARCHAR(MAX) = N'SELECT * FROM ' + QUOTENAME(@TableName)
EXEC sp_executesql @sql
```

### 18.3 Transaction & Error Handling

#### 18.3.1 Tespit Edilecek Sorunlar

| Sorun | Risk | AÇıklama |
|-------|------|----------|
| `BEGIN TRAN` without `COMMIT/ROLLBACK` | ðŸ”´ Kritik | Orphan transaction |
| No `TRY...CATCH` block | ðŸŸ  Yüksek | Unhandled errors |
| `@@ERROR` after multiple statements | ðŸŸ  Yüksek | Error değeri kaybolur |
| `XACT_ABORT OFF` with transactions | ðŸŸ¡ Orta | Partial commit riski |

#### 18.3.2 Ã–nerilen Güvenli Pattern

```sql
CREATE PROCEDURE usp_SafeOperation @Param1 INT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    
    -- Parametre doğrulama
    IF @Param1 IS NULL OR @Param1 <= 0
    BEGIN
        RAISERROR('Invalid parameter', 16, 1);
        RETURN -1;
    END
    
    BEGIN TRY
        BEGIN TRANSACTION;
        
        -- İş mantığı
        UPDATE Table1 SET Col1 = 'X' WHERE ID = @Param1;
        
        COMMIT TRANSACTION;
        RETURN 0;
        
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        
        DECLARE @Msg NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR(@Msg, ERROR_SEVERITY(), ERROR_STATE());
        RETURN -1;
    END CATCH
END
```

### 18.4 Data Conversion & Validation

| Pattern | Risk | Ã–neri |
|---------|------|-------|
| `CONVERT()` without error handling | ðŸŸ  Yüksek | `TRY_CONVERT()` kullan |
| `CAST()` without validation | ðŸŸ  Yüksek | `TRY_CAST()` kullan |
| Date string parsing | ðŸŸ¡ Orta | `TRY_PARSE()` veya format belirt |

```sql
-- âŒ GÃœVENSİZ
DECLARE @Amount MONEY = CONVERT(MONEY, @Input)

-- âœ… GÃœVENLİ
DECLARE @Amount MONEY = TRY_CONVERT(MONEY, @Input)
IF @Amount IS NULL AND @Input IS NOT NULL
    RAISERROR('Invalid amount format', 16, 1);
```

### 18.5 Locking & Concurrency

#### 18.5.1 Risk Analizi

| Pattern | Risk | AÇıklama |
|---------|------|----------|
| `WITH (NOLOCK)` her yerde | ðŸ”´ Kritik | Dirty reads, skipped/duplicate rows |
| `WITH (TABLOCKX)` | ðŸŸ  Yüksek | Excessive blocking |
| `HOLDLOCK` without need | ðŸŸ  Yüksek | Deadlock riski |

#### 18.5.2 NOLOCK Sorunları

```sql
-- âŒ NOLOCK SORUNLARI:
-- 1. Dirty reads (uncommitted data)
-- 2. Skipped rows (page splits)
-- 3. Duplicate rows (page splits)

-- NOLOCK kullanılabilir:
-- âœ… Reporting (yaklaşık rakamlar OK)
-- âœ… Historical data (değişmiyor)

-- NOLOCK kullanılmamalı:
-- âŒ Financial calculations
-- âŒ Inventory/balance checks
-- âŒ Business-critical queries

-- âœ… Ã–NERİ: SNAPSHOT ISOLATION
ALTER DATABASE MyDB SET READ_COMMITTED_SNAPSHOT ON;
```

### 18.6 Privilege & Permission

```python
"detect_permission_issues": {
    "description": "Yetki sorunlarını tespit et",
    "parameters": ["sp_name"],
    "sql": """
        SELECT 
            dp.name AS grantee,
            p.permission_name,
            CASE 
                WHEN dp.name = 'public' THEN 'CRITICAL: public permission'
                WHEN dp.name = 'guest' THEN 'HIGH: guest permission'
                ELSE 'Review'
            END AS security_concern
        FROM sys.database_permissions p
        JOIN sys.database_principals dp ON p.grantee_principal_id = dp.principal_id
        WHERE p.major_id = OBJECT_ID(@sp_name)
    """
}
```

### 18.7 Sensitive Data Exposure

| Pattern | AÇıklama | Ã–neri |
|---------|----------|-------|
| `SELECT *` on sensitive tables | Gereksiz veri ifşası | Explicit column list |
| Password in error message | Stack trace'de veri | Generic error |
| SSN/Credit card columns | PII/PCI data | Data masking |

```python
"detect_sensitive_data": {
    "description": "Hassas veri tespit et",
    "parameters": ["sp_name"],
    "sql": """
        SELECT 
            CASE 
                WHEN definition LIKE '%password%SELECT%' THEN 'HIGH: Password in SELECT'
                WHEN definition LIKE '%ssn%' OR definition LIKE '%credit_card%' 
                THEN 'CRITICAL: PII/PCI data'
                WHEN definition LIKE '%SELECT%*%FROM%' THEN 'MEDIUM: SELECT *'
                ELSE 'OK'
            END AS concern
        FROM sys.sql_modules
        WHERE object_id = OBJECT_ID(@sp_name)
    """
}
```

### 18.8 Güvenlik Ã–neri Matrisi

| Kategori | Tespit | AI Ã–nerisi |
|----------|--------|------------|
| **SQL Injection** | Dynamic SQL + concat | Parametreli `sp_executesql` |
| **SQL Injection** | `EXEC(@var)` | Whitelist + `QUOTENAME()` |
| **Transaction** | No `TRY...CATCH` | Full error handling |
| **Conversion** | `CONVERT()` | `TRY_CONVERT()` |
| **Locking** | Excessive `NOLOCK` | Snapshot isolation |
| **Permission** | `public` access | Specific role |
| **Data** | `SELECT *` sensitive | Explicit columns |

### 18.9 Security Analyzer Service

```python
class SecurityAnalyzer:
    """SQL kod güvenlik analizi servisi"""
    
    CHECKS = [
        "detect_dynamic_sql",
        "detect_dangerous_commands", 
        "detect_transaction_issues",
        "detect_locking_issues",
        "detect_permission_issues",
        "detect_sensitive_data"
    ]
    
    async def analyze(self, sp_name: str) -> SecurityReport:
        findings = []
        for check in self.CHECKS:
            result = await self.executor.run(check, {"sp_name": sp_name})
            findings.extend(result)
        
        ai_analysis = await self.ai.analyze_security(sp_name, findings)
        
        return SecurityReport(
            risk_level=self._calc_risk(findings),
            findings=findings,
            recommendations=ai_analysis.recommendations,
            secure_code=ai_analysis.secure_version
        )
```

### 18.10 Güvenlik Rapor Ã–rneği

```json
{
  "security_report": {
    "sp_name": "dbo.usp_GetUserData",
    "overall_risk": "HIGH",
    "findings": [
      {
        "category": "SQL_INJECTION",
        "severity": "CRITICAL",
        "line": 15,
        "code": "EXEC('SELECT * FROM Users WHERE Name = ''' + @Name + '''')",
        "fix": "Use sp_executesql with parameters"
      },
      {
        "category": "TRANSACTION",
        "severity": "HIGH", 
        "description": "Transaction without TRY...CATCH"
      }
    ],
    "statistics": {
      "critical": 1,
      "high": 1,
      "medium": 0
    }
  }
}
```

---

## 19. Caching Strategy

### 19.1 Cache Mimarisi

```
#------------------------------------------------------------------------------
#                         CACHING STRATEGY                                    #
#------------------------------------------------------------------------------¤
#                                                                             #
#  #------------------  #------------------  #------------------             #
#  # SESSION CACHE   #  # CONNECTION CACHE#  #  NO CACHE       #             #
#  # (App lifetime)  #  # (Per connection)#  #  (Always fresh) #             #
#  #------------------¤  #------------------¤  #------------------¤             #
#  # â€¢ Server version#  # â€¢ Database files#  # â€¢ Wait stats    #             #
#  # â€¢ CPU count     #  # â€¢ SP list       #  # â€¢ Active locks  #             #
#  # â€¢ Memory config #  # â€¢ Index list    #  # â€¢ Blocking      #             #
#  # â€¢ MAXDOP        #  # â€¢ Table list    #  # â€¢ Current procs #             #
#  # â€¢ OS info       #  # â€¢ Stats age     #  # â€¢ Live metrics  #             #
#  #                 #  # â€¢ SP code       #  # â€¢ Query stats   #             #
#  # TTL: Session    #  # TTL: 5-15 min   #  # TTL: 0          #             #
#  -”------------------˜  -”------------------˜  -”------------------˜             #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 19.2 Cache Kategorileri

| Kategori | Veri Türü | TTL | Invalidation |
|----------|-----------|-----|--------------|
| **Session** | Server config, version, CPU | App lifetime | App restart |
| **Connection** | DB metadata, SP list, indexes | 5-15 dakika | Manual refresh, connection change |
| **Short-term** | Statistics age, fragmentation | 1-5 dakika | Manual refresh |
| **No Cache** | Wait stats, locks, active sessions | 0 | Her zaman fresh |

### 19.3 Cache Implementation

```python
# app/core/cache_manager.py

from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import hashlib

class CacheLevel(Enum):
    SESSION = "session"         # App lifetime
    CONNECTION = "connection"   # Per connection, 5-15 min
    SHORT_TERM = "short_term"   # 1-5 min
    NO_CACHE = "no_cache"       # Always fresh

@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    ttl_seconds: int = 300
    level: CacheLevel = CacheLevel.CONNECTION
    
    def is_expired(self) -> bool:
        if self.level == CacheLevel.SESSION:
            return False
        if self.level == CacheLevel.NO_CACHE:
            return True
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)

class CacheManager:
    """Multi-level cache manager for database metadata"""
    
    # TTL defaults (seconds)
    TTL_CONFIG = {
        CacheLevel.SESSION: 0,        # Never expires
        CacheLevel.CONNECTION: 600,   # 10 minutes
        CacheLevel.SHORT_TERM: 120,   # 2 minutes
        CacheLevel.NO_CACHE: 0        # Always fetch
    }
    
    # Query to cache level mapping
    QUERY_CACHE_LEVELS = {
        # Session level - rarely changes
        "server_version": CacheLevel.SESSION,
        "server_memory_config": CacheLevel.SESSION,
        "server_cpu_config": CacheLevel.SESSION,
        "server_os_info": CacheLevel.SESSION,
        
        # Connection level - changes occasionally
        "database_config": CacheLevel.CONNECTION,
        "database_files": CacheLevel.CONNECTION,
        "sp_list": CacheLevel.CONNECTION,
        "sp_code": CacheLevel.CONNECTION,
        "trigger_list": CacheLevel.CONNECTION,
        "view_list": CacheLevel.CONNECTION,
        "index_list": CacheLevel.CONNECTION,
        "table_list": CacheLevel.CONNECTION,
        
        # Short-term - changes more frequently
        "database_statistics_health": CacheLevel.SHORT_TERM,
        "index_fragmentation": CacheLevel.SHORT_TERM,
        "sp_statistics": CacheLevel.SHORT_TERM,
        
        # No cache - real-time data
        "wait_stats": CacheLevel.NO_CACHE,
        "current_locks": CacheLevel.NO_CACHE,
        "blocking_chains": CacheLevel.NO_CACHE,
        "active_sessions": CacheLevel.NO_CACHE,
        "top_slow_queries": CacheLevel.NO_CACHE,
    }
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._connection_id: Optional[str] = None
        self._lock = asyncio.Lock()
    
    def _make_key(self, query_name: str, params: Dict = None) -> str:
        """Generate unique cache key"""
        base = f"{self._connection_id}:{query_name}"
        if params:
            param_str = str(sorted(params.items()))
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            base = f"{base}:{param_hash}"
        return base
    
    async def get(self, query_name: str, params: Dict = None) -> Optional[Any]:
        """Get cached value if valid"""
        level = self.QUERY_CACHE_LEVELS.get(query_name, CacheLevel.CONNECTION)
        
        if level == CacheLevel.NO_CACHE:
            return None
        
        key = self._make_key(query_name, params)
        
        async with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                return entry.value
            elif entry:
                del self._cache[key]
        
        return None
    
    async def set(self, query_name: str, value: Any, params: Dict = None):
        """Cache a value"""
        level = self.QUERY_CACHE_LEVELS.get(query_name, CacheLevel.CONNECTION)
        
        if level == CacheLevel.NO_CACHE:
            return
        
        key = self._make_key(query_name, params)
        ttl = self.TTL_CONFIG[level]
        
        async with self._lock:
            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                level=level,
                ttl_seconds=ttl
            )
    
    async def invalidate(self, query_name: str = None, level: CacheLevel = None):
        """Invalidate cache entries"""
        async with self._lock:
            if query_name:
                # Invalidate specific query
                keys_to_remove = [k for k in self._cache if query_name in k]
            elif level:
                # Invalidate all at a level
                keys_to_remove = [
                    k for k, v in self._cache.items() 
                    if v.level == level
                ]
            else:
                # Invalidate all
                keys_to_remove = list(self._cache.keys())
            
            for key in keys_to_remove:
                del self._cache[key]
    
    def set_connection(self, connection_id: str):
        """Set current connection and invalidate connection-level cache"""
        if self._connection_id != connection_id:
            self._connection_id = connection_id
            # Clear connection and short-term cache
            asyncio.create_task(self.invalidate(level=CacheLevel.CONNECTION))
            asyncio.create_task(self.invalidate(level=CacheLevel.SHORT_TERM))
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = len(self._cache)
        expired = sum(1 for e in self._cache.values() if e.is_expired())
        by_level = {}
        for entry in self._cache.values():
            by_level[entry.level.value] = by_level.get(entry.level.value, 0) + 1
        
        return {
            "total_entries": total,
            "expired_entries": expired,
            "by_level": by_level
        }
```

### 19.4 Cached Query Executor

```python
# app/database/cached_executor.py

class CachedQueryExecutor:
    """Query executor with caching support"""
    
    def __init__(self, executor: QueryExecutor, cache: CacheManager):
        self.executor = executor
        self.cache = cache
    
    async def execute(self, query_name: str, params: Dict = None) -> Any:
        """Execute query with caching"""
        
        # Check cache first
        cached = await self.cache.get(query_name, params)
        if cached is not None:
            return cached
        
        # Execute query
        result = await self.executor.execute(query_name, params)
        
        # Cache result
        await self.cache.set(query_name, result, params)
        
        return result
    
    async def execute_fresh(self, query_name: str, params: Dict = None) -> Any:
        """Execute query bypassing cache"""
        result = await self.executor.execute(query_name, params)
        await self.cache.set(query_name, result, params)
        return result
```

### 19.5 Cache Invalidation Triggers

| Trigger | Action |
|---------|--------|
| Manual refresh button | Invalidate CONNECTION level |
| Connection change | Invalidate CONNECTION + SHORT_TERM |
| SP modification detected | Invalidate specific SP cache |
| App restart | All cache cleared |
| TTL expiry | Automatic removal on next access |

---

## 20. Async Architecture

### 20.1 Async Workflow

```
#------------------------------------------------------------------------------
#                         ASYNC ARCHITECTURE                                  #
#------------------------------------------------------------------------------¤
#                                                                             #
#  UI THREAD              BACKGROUND TASKS           DATABASE                 #
#  ---------              ----------------           --------                 #
#      #                                                                      #
#      #  --"Analyze SP"--â–º  #---------------                                #
#      #                     # Task Manager #                                #
#      #  â—„--"Started"----   -”-------¬--------˜                                #
#      #                            #                                         #
#      #  â—„-"Progress 20%"-   #------´------                                  #
#      #                      #  Parallel #                                  #
#      #  â—„-"Progress 40%"-   #  Queries  #------â–º  Server Info              #
#      #                      #           #------â–º  DB Config                #
#      #  â—„-"Progress 60%"-   #           #------â–º  SP Stats                 #
#      #                      -”------¬------˜                                  #
#      #                            #                                         #
#      #  â—„-"Progress 80%"-   #------´------                                  #
#      #                      # AI Analyze#                                  #
#      #                      -”------¬------˜                                  #
#      #                            #                                         #
#      #  â—„---"Complete"---   #------´------                                  #
#      #                      #  Result   #                                  #
#      â–¼                      -”------------˜                                  #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 20.2 Task Manager

```python
# app/core/task_manager.py

from dataclasses import dataclass, field
from typing import Callable, Any, Optional, List
from enum import Enum
import asyncio
import uuid
from datetime import datetime

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskProgress:
    current_step: int = 0
    total_steps: int = 100
    message: str = ""
    percentage: float = 0.0
    
    def update(self, step: int, message: str = ""):
        self.current_step = step
        self.message = message
        self.percentage = (step / self.total_steps) * 100

@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    status: TaskStatus = TaskStatus.PENDING
    progress: TaskProgress = field(default_factory=TaskProgress)
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    _cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()
    
    def cancel(self):
        self._cancel_event.set()
        self.status = TaskStatus.CANCELLED

class TaskManager:
    """Manages async background tasks with progress tracking"""
    
    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._listeners: dict[str, List[Callable]] = {}
    
    def create_task(self, name: str, total_steps: int = 100) -> Task:
        """Create a new task"""
        task = Task(
            name=name,
            progress=TaskProgress(total_steps=total_steps)
        )
        self._tasks[task.id] = task
        return task
    
    async def run_task(self, task: Task, coro: Callable) -> Any:
        """Run a coroutine as a managed task"""
        try:
            task.status = TaskStatus.RUNNING
            self._notify(task.id, "started", task)
            
            result = await coro(task)
            
            if task.is_cancelled():
                return None
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            self._notify(task.id, "completed", task)
            
            return result
            
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            self._notify(task.id, "cancelled", task)
            raise
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            self._notify(task.id, "failed", task)
            raise
    
    def update_progress(self, task_id: str, step: int, message: str = ""):
        """Update task progress"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            task.progress.update(step, message)
            self._notify(task_id, "progress", task)
    
    def cancel_task(self, task_id: str):
        """Cancel a running task"""
        if task_id in self._tasks:
            self._tasks[task_id].cancel()
    
    def add_listener(self, task_id: str, callback: Callable):
        """Add progress listener"""
        if task_id not in self._listeners:
            self._listeners[task_id] = []
        self._listeners[task_id].append(callback)
    
    def _notify(self, task_id: str, event: str, task: Task):
        """Notify listeners of task events"""
        for callback in self._listeners.get(task_id, []):
            try:
                callback(event, task)
            except:
                pass
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)
    
    def cleanup_completed(self, max_age_seconds: int = 3600):
        """Remove old completed tasks"""
        now = datetime.now()
        to_remove = []
        for task_id, task in self._tasks.items():
            if task.completed_at:
                age = (now - task.completed_at).total_seconds()
                if age > max_age_seconds:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._tasks[task_id]
            self._listeners.pop(task_id, None)
```

### 20.3 Async Analysis Service

```python
# app/services/async_analyzer.py

class AsyncAnalyzer:
    """Async SP analysis with progress tracking"""
    
    ANALYSIS_STEPS = [
        (10, "Collecting server information..."),
        (20, "Collecting database configuration..."),
        (35, "Analyzing stored procedure..."),
        (50, "Gathering dependencies..."),
        (65, "Collecting performance statistics..."),
        (80, "Running AI analysis..."),
        (95, "Validating output..."),
        (100, "Complete")
    ]
    
    def __init__(self, task_manager: TaskManager, cache: CacheManager):
        self.task_manager = task_manager
        self.cache = cache
    
    async def analyze_sp(self, sp_name: str, on_progress: Callable = None) -> AnalysisResult:
        """Analyze SP with progress tracking"""
        
        task = self.task_manager.create_task(
            name=f"Analyze {sp_name}",
            total_steps=100
        )
        
        if on_progress:
            self.task_manager.add_listener(task.id, on_progress)
        
        async def _analyze(task: Task):
            # Step 1: Server info (parallel with DB config)
            self._update(task, 10, "Collecting server information...")
            
            if task.is_cancelled():
                return None
            
            # Parallel data collection
            server_task = asyncio.create_task(self._collect_server_info())
            db_task = asyncio.create_task(self._collect_db_config())
            
            self._update(task, 20, "Collecting database configuration...")
            
            server_info, db_config = await asyncio.gather(server_task, db_task)
            
            if task.is_cancelled():
                return None
            
            # Step 2: SP Analysis
            self._update(task, 35, "Analyzing stored procedure...")
            sp_data = await self._collect_sp_data(sp_name)
            
            if task.is_cancelled():
                return None
            
            # Step 3: Dependencies
            self._update(task, 50, "Gathering dependencies...")
            dependencies = await self._collect_dependencies(sp_name)
            
            if task.is_cancelled():
                return None
            
            # Step 4: Performance stats
            self._update(task, 65, "Collecting performance statistics...")
            perf_stats = await self._collect_perf_stats(sp_name)
            
            if task.is_cancelled():
                return None
            
            # Step 5: AI Analysis
            self._update(task, 80, "Running AI analysis...")
            ai_result = await self._run_ai_analysis(
                sp_data, server_info, db_config, dependencies, perf_stats
            )
            
            if task.is_cancelled():
                return None
            
            # Step 6: Validation
            self._update(task, 95, "Validating output...")
            validated = await self._validate_output(ai_result)
            
            self._update(task, 100, "Complete")
            
            return validated
        
        return await self.task_manager.run_task(task, _analyze)
    
    def _update(self, task: Task, step: int, message: str):
        self.task_manager.update_progress(task.id, step, message)
    
    def cancel_analysis(self, task_id: str):
        """Cancel ongoing analysis"""
        self.task_manager.cancel_task(task_id)
```

### 20.4 PyQt6 UI Integration

```python
# app/ui/components/progress_dialog.py

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, 
    QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt

class AnalysisProgressDialog(QDialog):
    """Progress dialog for async analysis"""
    
    def __init__(self, title: str = "Analyzing...", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(450, 150)
        self._cancel_callback = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Status text
        self.status_label = QLabel("Starting...")
        self.status_label.setStyleSheet("font-size: 14px; color: #ffffff;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                background-color: #242424;
                height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0066ff;
                border-radius: 7px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Cancel button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
    
    def update_progress(self, event: str, task):
        """Called by task manager"""
        if event == "progress":
            self.progress_bar.setValue(int(task.progress.percentage))
            self.status_label.setText(task.progress.message)
        elif event == "completed":
            self.accept()
        elif event == "failed":
            self.status_label.setText(f"Error: {task.error}")
            self.cancel_btn.setText("Close")
    
    def set_cancel_callback(self, callback):
        self._cancel_callback = callback
    
    def _on_cancel(self):
        if self._cancel_callback:
            self._cancel_callback()
        self.reject()
```

### 20.5 Async Patterns

| Pattern | Kullanım | Ã–rnek |
|---------|----------|-------|
| **Fire-and-forget** | Logging, cache update | `asyncio.create_task(log_event())` |
| **Parallel gather** | Multiple independent queries | `await asyncio.gather(q1, q2, q3)` |
| **Sequential with progress** | Step-by-step analysis | `for step in steps: await step()` |
| **Cancellable** | Long-running operations | `task.is_cancelled()` check |
| **Timeout** | External API calls | `asyncio.wait_for(coro, timeout=30)` |

---

## 21. Output Validation Pipeline

### 21.1 Validation Architecture

```
#------------------------------------------------------------------------------
#                    OUTPUT VALIDATION PIPELINE                               #
#------------------------------------------------------------------------------¤
#                                                                             #
#  AI OUTPUT                                                                  #
#      #                                                                      #
#      â–¼                                                                      #
#  #----------------------------------------------------------------------   #
#  #  LAYER 1: SYNTAX VALIDATION                                         #   #
#  #  â€¢ SQL Parser ile syntax kontrolü                                   #   #
#  #  â€¢ Bracket/parenthesis matching                                     #   #
#  #  â€¢ Keyword validation                                               #   #
#  #  â€¢ SET PARSEONLY ON ile SQL Server validation                       #   #
#  -”----------------------------------------------------------------------˜   #
#      # âœ… Pass / âŒ Fail                                                    #
#      â–¼                                                                      #
#  #----------------------------------------------------------------------   #
#  #  LAYER 2: SECURITY VALIDATION                                       #   #
#  #  â€¢ SQL Injection pattern detection                                  #   #
#  #  â€¢ Dangerous command check                                          #   #
#  #  â€¢ Dynamic SQL analysis                                             #   #
#  #  â€¢ Permission escalation check                                      #   #
#  -”----------------------------------------------------------------------˜   #
#      # âœ… Pass / âš ï¸ Warning / âŒ Fail                                       #
#      â–¼                                                                      #
#  #----------------------------------------------------------------------   #
#  #  LAYER 3: SEMANTIC VALIDATION                                       #   #
#  #  â€¢ Object existence (tables, views, columns)                        #   #
#  #  â€¢ Parameter type compatibility                                     #   #
#  #  â€¢ Schema validation                                                #   #
#  #  â€¢ Data type compatibility                                          #   #
#  -”----------------------------------------------------------------------˜   #
#      # âœ… Pass / âš ï¸ Warning / âŒ Fail                                       #
#      â–¼                                                                      #
#  #----------------------------------------------------------------------   #
#  #  VALIDATION RESULT                                                  #   #
#  #                                                                     #   #
#  #  âœ… PASSED          âš ï¸ WARNINGS           âŒ FAILED                 #   #
#  #  Kullanıcıya sun    Uyarı ile sun         AI'dan yeniden iste       #   #
#  #                     (onay iste)           veya hata göster          #   #
#  -”----------------------------------------------------------------------˜   #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 21.2 Validation Implementation

```python
# app/services/output_validator.py

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
import re
import sqlparse

class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationIssue:
    severity: ValidationSeverity
    category: str
    message: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    validated_code: Optional[str] = None
    
    @property
    def has_errors(self) -> bool:
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)
    
    @property
    def has_warnings(self) -> bool:
        return any(i.severity == ValidationSeverity.WARNING for i in self.issues)

class OutputValidator:
    """3-layer validation pipeline for AI-generated SQL"""
    
    # Dangerous patterns
    DANGEROUS_PATTERNS = [
        (r'xp_cmdshell', 'CRITICAL: xp_cmdshell usage detected'),
        (r'OPENROWSET', 'HIGH: OPENROWSET usage detected'),
        (r'OPENDATASOURCE', 'HIGH: OPENDATASOURCE usage detected'),
        (r'xp_reg\w+', 'HIGH: Registry access detected'),
        (r'sp_OACreate', 'CRITICAL: OLE Automation detected'),
        (r'EXEC\s*\(\s*@', 'HIGH: Dynamic SQL with variable execution'),
        (r"EXEC\s*\([^)]*\+[^)]*\)", 'CRITICAL: String concatenation in EXEC'),
    ]
    
    # Required patterns for safe code
    RECOMMENDED_PATTERNS = [
        (r'SET\s+NOCOUNT\s+ON', 'Missing SET NOCOUNT ON'),
        (r'BEGIN\s+TRY', 'Missing TRY...CATCH block'),
        (r'SET\s+XACT_ABORT\s+ON', 'Consider SET XACT_ABORT ON for transactions'),
    ]
    
    def __init__(self, db_connection=None):
        self.db = db_connection
    
    async def validate(self, sql_code: str) -> ValidationResult:
        """Run full validation pipeline"""
        issues = []
        
        # Layer 1: Syntax
        syntax_issues = await self._validate_syntax(sql_code)
        issues.extend(syntax_issues)
        
        # Stop if syntax errors (can't proceed)
        if any(i.severity == ValidationSeverity.ERROR and i.category == "SYNTAX" 
               for i in issues):
            return ValidationResult(is_valid=False, issues=issues)
        
        # Layer 2: Security
        security_issues = self._validate_security(sql_code)
        issues.extend(security_issues)
        
        # Layer 3: Semantic (if DB connection available)
        if self.db:
            semantic_issues = await self._validate_semantic(sql_code)
            issues.extend(semantic_issues)
        
        # Determine overall validity
        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            validated_code=sql_code if is_valid else None
        )
    
    async def _validate_syntax(self, sql_code: str) -> List[ValidationIssue]:
        """Layer 1: Syntax validation"""
        issues = []
        
        # Basic Python parsing
        try:
            parsed = sqlparse.parse(sql_code)
            if not parsed:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="SYNTAX",
                    message="Failed to parse SQL code"
                ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="SYNTAX",
                message=f"Parse error: {str(e)}"
            ))
        
        # Bracket matching
        if not self._check_brackets(sql_code):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="SYNTAX",
                message="Unmatched brackets or parentheses"
            ))
        
        # SQL Server validation (if DB available)
        if self.db:
            try:
                # Use SET PARSEONLY to validate without executing
                await self.db.execute("SET PARSEONLY ON")
                await self.db.execute(sql_code)
                await self.db.execute("SET PARSEONLY OFF")
            except Exception as e:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="SYNTAX",
                    message=f"SQL Server syntax error: {str(e)}"
                ))
            finally:
                await self.db.execute("SET PARSEONLY OFF")
        
        return issues
    
    def _validate_security(self, sql_code: str) -> List[ValidationIssue]:
        """Layer 2: Security validation"""
        issues = []
        
        # Check dangerous patterns
        for pattern, message in self.DANGEROUS_PATTERNS:
            if re.search(pattern, sql_code, re.IGNORECASE):
                severity = ValidationSeverity.ERROR if 'CRITICAL' in message else ValidationSeverity.WARNING
                issues.append(ValidationIssue(
                    severity=severity,
                    category="SECURITY",
                    message=message,
                    suggestion="Remove or replace with safer alternative"
                ))
        
        # Check for missing recommended patterns (warnings)
        if 'BEGIN TRAN' in sql_code.upper():
            for pattern, message in self.RECOMMENDED_PATTERNS:
                if not re.search(pattern, sql_code, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="BEST_PRACTICE",
                        message=message
                    ))
        
        # Check NOLOCK overuse
        nolock_count = len(re.findall(r'NOLOCK', sql_code, re.IGNORECASE))
        if nolock_count > 5:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="SECURITY",
                message=f"Excessive NOLOCK usage ({nolock_count} occurrences)",
                suggestion="Consider using READ_COMMITTED_SNAPSHOT isolation"
            ))
        
        # Check for SELECT *
        if re.search(r'SELECT\s+\*\s+FROM', sql_code, re.IGNORECASE):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="BEST_PRACTICE",
                message="SELECT * usage detected",
                suggestion="Use explicit column list"
            ))
        
        return issues
    
    async def _validate_semantic(self, sql_code: str) -> List[ValidationIssue]:
        """Layer 3: Semantic validation against database"""
        issues = []
        
        # Extract table references
        tables = self._extract_table_names(sql_code)
        
        for table in tables:
            # Check if table exists
            exists = await self._check_object_exists(table)
            if not exists:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="SEMANTIC",
                    message=f"Table or view '{table}' does not exist"
                ))
        
        # Extract column references and validate
        # (simplified - full implementation would parse SQL properly)
        
        return issues
    
    def _check_brackets(self, sql_code: str) -> bool:
        """Check for balanced brackets"""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        
        in_string = False
        string_char = None
        
        for char in sql_code:
            # Handle string literals
            if char in ("'", '"') and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None
            elif not in_string:
                if char in pairs:
                    stack.append(char)
                elif char in pairs.values():
                    if not stack:
                        return False
                    if pairs[stack.pop()] != char:
                        return False
        
        return len(stack) == 0
    
    def _extract_table_names(self, sql_code: str) -> List[str]:
        """Extract table names from SQL (simplified)"""
        # This is a simplified version - real implementation would use proper parsing
        pattern = r'(?:FROM|JOIN|INTO|UPDATE)\s+(\[?\w+\]?\.?\[?\w+\]?)'
        matches = re.findall(pattern, sql_code, re.IGNORECASE)
        return list(set(matches))
    
    async def _check_object_exists(self, object_name: str) -> bool:
        """Check if object exists in database"""
        try:
            result = await self.db.execute(
                "SELECT OBJECT_ID(@name)",
                {"name": object_name}
            )
            return result is not None
        except:
            return True  # Assume exists if check fails
```

### 21.3 Validation Rules Matrix

| Category | Rule | Severity | Action |
|----------|------|----------|--------|
| **Syntax** | Parse failure | ERROR | Block, request regeneration |
| **Syntax** | Unmatched brackets | ERROR | Block, show error |
| **Syntax** | SQL Server parse error | ERROR | Block, show error |
| **Security** | `xp_cmdshell` | ERROR | Block, never allow |
| **Security** | String concat in EXEC | ERROR | Block, show secure alternative |
| **Security** | Dynamic SQL variable | WARNING | Allow with warning |
| **Security** | Excessive NOLOCK | WARNING | Allow with warning |
| **Best Practice** | Missing TRY...CATCH | WARNING | Allow with suggestion |
| **Best Practice** | SELECT * | WARNING | Allow with suggestion |
| **Semantic** | Table not found | ERROR | Block, show error |
| **Semantic** | Column not found | ERROR | Block, show error |

### 21.4 Integration with AI Service

```python
# app/services/ai_with_validation.py

class ValidatedAIService:
    """AI service with automatic output validation"""
    
    MAX_RETRY_ATTEMPTS = 3
    
    def __init__(self, ai_client, validator: OutputValidator):
        self.ai = ai_client
        self.validator = validator
    
    async def generate_optimized_sp(self, original_sp: str, context: dict) -> ValidatedOutput:
        """Generate and validate optimized SP"""
        
        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            # Generate code
            ai_output = await self.ai.optimize_sp(original_sp, context)
            
            # Validate
            validation = await self.validator.validate(ai_output.code)
            
            if validation.is_valid:
                return ValidatedOutput(
                    code=validation.validated_code,
                    validation=validation,
                    attempts=attempt + 1
                )
            
            # If only warnings, return with warnings
            if not validation.has_errors:
                return ValidatedOutput(
                    code=ai_output.code,
                    validation=validation,
                    has_warnings=True,
                    attempts=attempt + 1
                )
            
            # If errors, retry with error feedback
            context['previous_errors'] = [
                i.message for i in validation.issues 
                if i.severity == ValidationSeverity.ERROR
            ]
        
        # All retries failed
        return ValidatedOutput(
            code=None,
            validation=validation,
            failed=True,
            attempts=self.MAX_RETRY_ATTEMPTS
        )
```

### 21.5 UI Integration

```python
# Validation result display in UI (PyQt6)

from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

def show_validation_result(result: ValidationResult, parent=None):
    """Show validation result to user"""
    
    if result.is_valid and not result.has_warnings:
        # Clean pass - show code
        show_code_dialog(result.validated_code, parent)
        
    elif result.is_valid and result.has_warnings:
        # Pass with warnings - show warnings and ask confirmation
        warnings = [i for i in result.issues if i.severity == ValidationSeverity.WARNING]
        
        dialog = QDialog(parent)
        dialog.setWindowTitle("âš ï¸ Validation Warnings")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("The generated code has some warnings:"))
        
        for w in warnings:
            label = QLabel(f"â€¢ {w.message}")
            label.setStyleSheet("color: #f59e0b;")  # Orange
            layout.addWidget(label)
        
        layout.addWidget(QLabel("\nDo you want to proceed?"))
        
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        proceed_btn = QPushButton("Proceed Anyway")
        proceed_btn.setStyleSheet("background-color: #0066ff; color: white;")
        proceed_btn.clicked.connect(lambda: (dialog.accept(), show_code(result.validated_code)))
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(proceed_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()
        
    else:
        # Failed - show errors
        errors = [i for i in result.issues if i.severity == ValidationSeverity.ERROR]
        
        dialog = QDialog(parent)
        dialog.setWindowTitle("âŒ Validation Failed")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("The generated code has errors:"))
        
        for e in errors:
            label = QLabel(f"â€¢ {e.message}")
            label.setStyleSheet("color: #ef4444;")  # Red
            layout.addWidget(label)
        
        layout.addWidget(QLabel("\nPlease try again or modify manually."))
        
        btn_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.reject)
        retry_btn = QPushButton("Retry")
        retry_btn.setStyleSheet("background-color: #0066ff; color: white;")
        retry_btn.clicked.connect(lambda: (dialog.accept(), retry_generation()))
        
        btn_layout.addWidget(close_btn)
        btn_layout.addWidget(retry_btn)
        layout.addLayout(btn_layout)
        
        dialog.exec()
```

---

## 22. Development Planı

### 22.1 Genel Bakış

```
#------------------------------------------------------------------------------
#                    DEVELOPMENT TIMELINE (20 Hafta)                          #
#------------------------------------------------------------------------------¤
#                                                                             #
#  PHASE 1          PHASE 2          PHASE 3          PHASE 4                #
#  Foundation       Core Features    Advanced         Polish & Release        #
#  (Hafta 1-5)      (Hafta 6-11)     (Hafta 12-16)    (Hafta 17-20)          #
#                                                                             #
#  #----------      #----------      #----------      #----------            #
#  # Setup   #      # DB Conn #      # AI Opt  #      # Testing #            #
#  # Core    # --â–º  # Query   # --â–º  # Security# --â–º  # Docs    #            #
#  # UI Base #      # Analysis#      # Cache   #      # Package #            #
#  -”----------˜      -”----------˜      -”----------˜      -”----------˜            #
#                                                                             #
#  Milestone:       Milestone:       Milestone:       Milestone:             #
#  Working Shell    Basic Analysis   Full Features    Production Ready       #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 22.2 Phase 1: Foundation (Hafta 1-5)

#### Hafta 1: Proje Kurulumu & Temel Yapı

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Proje yapısı oluştur | Poetry, folder structure, git |
| 2-3 | Core modülleri kur | `config.py`, `constants.py`, `exceptions.py` |
| 3-4 | PyQt6 kurulumu ve test | Boş pencere aÇılıyor |
| 4-5 | CI/CD pipeline | GitHub Actions, linting, tests |

```bash
# Proje oluşturma
poetry new sql-perf-ai
cd sql-perf-ai

# Temel bağımlılıklar
poetry add pyqt6 sqlalchemy pyodbc pydantic aiohttp
poetry add --group dev pytest pytest-asyncio black ruff mypy

# Folder structure
mkdir -p app/{core,models,auth,database,analysis,ai,ui/{components,views},services}
mkdir -p locales tests/{unit,integration} docs
```

**Deliverables:**
- [ ] Poetry project configured
- [ ] Folder structure created
- [ ] Git repository initialized
- [ ] Basic CI/CD pipeline
- [ ] README.md with setup instructions

---

#### Hafta 2: Configuration & Language System

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Config manager | JSON config load/save |
| 2-3 | Language manager | TR/EN/DE JSON files |
| 3-4 | Constants & Exceptions | Tüm sabitler tanımlı |
| 5 | Unit tests | %80 coverage for core |

```python
# Hafta 2 sonunda Çalışan örnek:
from app.core import Config, LanguageManager

config = Config.load()
lang = LanguageManager()
lang.set_language("tr")
print(lang.get_text("common.welcome"))  # "Hoş geldiniz"
```

**Deliverables:**
- [ ] `app/core/config.py` - Configuration management
- [ ] `app/core/language_manager.py` - Multi-language support
- [ ] `locales/tr.json`, `locales/en.json`, `locales/de.json`
- [ ] `locales/languages.json` - Language registry
- [ ] Unit tests for config and language

---

#### Hafta 3: UI Foundation

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Main window & routing | Temel sayfa geÇişleri |
| 2-3 | Sidebar component | Navigation menu |
| 3-4 | Header component | Title, user info |
| 4-5 | Theme system | Light/Dark theme |

```python
# Hafta 3 sonunda Çalışan örnek:
import sys
from PyQt6.QtWidgets import QApplication
from app.ui import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
# Sidebar ile boş sayfalar arası geÇiş Çalışıyor
```

**Deliverables:**
- [ ] `app/ui/main_window.py` - Main application window
- [ ] `app/ui/components/sidebar.py` - Navigation sidebar
- [ ] `app/ui/components/header.py` - App header
- [ ] `app/ui/theme.py` - Theme configuration
- [ ] Basic routing between empty views

---

#### Hafta 4: Connection Manager UI

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | ConnectionProfile model | Dataclass tanımı |
| 2-3 | Connection dialog | Add/Edit form |
| 3-4 | Connection list view | Tree view, cards |
| 5 | Connection store (mock) | JSON save/load |

```python
# Hafta 4 sonunda Çalışan örnek:
# UI'dan yeni connection eklenebiliyor (henüz bağlanmıyor)
# Connection listesi görüntülenebiliyor
# Edit/Delete işlemleri Çalışıyor
```

**Deliverables:**
- [ ] `app/models/connection_profile.py` - Connection data model
- [ ] `app/ui/views/connection_manager_view.py` - Connection list
- [ ] `app/ui/views/connection_dialog.py` - Add/Edit dialog
- [ ] `app/ui/components/connection_card.py` - Connection card
- [ ] `app/services/connection_store.py` - JSON persistence

---

#### Hafta 5: Database Connection

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | SQLAlchemy connection | Async connection pool |
| 2-3 | Version detector | SQL Server version tespiti |
| 3-4 | Credential store | Keyring integration |
| 5 | Connection test | UI'dan bağlantı test |

```python
# Hafta 5 sonunda Çalışan örnek:
from app.database import DatabaseConnection, VersionDetector

async with DatabaseConnection(profile) as conn:
    version = await VersionDetector(conn).detect()
    print(f"Connected to {version.friendly_name}")
    # "Connected to SQL Server 2019"
```

**Deliverables:**
- [ ] `app/database/connection.py` - Async DB connection
- [ ] `app/database/version_detector.py` - Version detection
- [ ] `app/services/credential_store.py` - Keyring integration
- [ ] Test Connection button working
- [ ] Connection status indicator in UI

---

### 22.3 Phase 2: Core Features (Hafta 6-11)

#### Hafta 6: Query Library & Executor

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Query library | 20+ template query |
| 2-3 | Version-aware queries | Version-specific SQL |
| 3-4 | Query executor | Parameterized execution |
| 5 | Cache manager | Basic caching |

**Deliverables:**
- [ ] `app/database/query_library.py` - 20+ query templates
- [ ] `app/database/query_executor.py` - Safe query execution
- [ ] `app/core/cache_manager.py` - Multi-level caching
- [ ] Version-aware query selection

---

#### Hafta 7: SP Explorer View

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | SP list collector | SP'leri listele |
| 2-3 | SP Explorer UI | Tree view, search |
| 3-4 | SP Code viewer | Syntax highlighting |
| 5 | SP Dependencies | Bağımlılık görüntüleme |

```python
# Hafta 7 sonunda:
# - Sol panelde SP listesi (schema bazlı)
# - Arama ve filtreleme
# - SP seÇince kod görüntüleme
# - Bağımlılık listesi
```

**Deliverables:**
- [ ] `app/database/collectors/sp_collector.py`
- [ ] `app/ui/views/sp_explorer_view.py`
- [ ] `app/ui/components/code_editor.py` - Syntax highlighting
- [ ] SP search and filter functionality

---

#### Hafta 8: Query Statistics & Analysis

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Stats collectors | Wait stats, IO stats |
| 2-3 | Query stats view | Top queries dashboard |
| 3-4 | SP stats | Execution stats |
| 5 | Result table component | Sortable, filterable |

**Deliverables:**
- [ ] `app/database/collectors/stats_collector.py`
- [ ] `app/ui/views/query_stats_view.py`
- [ ] `app/ui/components/result_table.py`
- [ ] Dashboard with top slow queries

---

#### Hafta 9: Index Analysis

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Index collector | Index listesi, usage |
| 2-3 | Fragmentation analysis | dm_db_index_physical_stats |
| 3-4 | Index advisor UI | Missing index önerileri |
| 5 | Index script generator | Rebuild/Reorganize scripts |

**Deliverables:**
- [ ] `app/database/collectors/index_collector.py`
- [ ] `app/ui/views/index_advisor_view.py`
- [ ] Index fragmentation analysis
- [ ] Script generation for maintenance

---

#### Hafta 10: Task Manager & Async

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Task manager | Background task handling |
| 2-3 | Progress tracking | Progress events |
| 3-4 | UI integration | Progress dialogs |
| 5 | Cancellation | Task iptal mekanizması |

**Deliverables:**
- [ ] `app/core/task_manager.py` - Async task orchestration
- [ ] `app/ui/components/progress_dialog.py`
- [ ] Cancellable long-running operations
- [ ] Progress indicators in UI

---

#### Hafta 11: AI Integration (Basic)

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Ollama client | HTTP API client |
| 2-3 | Prompt templates | YAML prompt config |
| 3-4 | Chat UI | Basic chat interface |
| 5 | Context builder | SP + metadata to prompt |

```python
# Hafta 11 sonunda:
# - Chat UI'dan soru sorulabiliyor
# - Ollama'ya bağlanıyor
# - Basit SP analizi yapılabiliyor
```

**Deliverables:**
- [ ] `app/ai/ollama_client.py` - Ollama HTTP client
- [ ] `app/ai/prompt_templates.py` - YAML-based prompts
- [ ] `app/ui/views/chat_view.py` - Chat interface
- [ ] Basic SP analysis working

---

### 22.4 Phase 3: Advanced Features (Hafta 12-16)

#### Hafta 12: AI Optimization Engine

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Intent classifier | Kullanıcı niyeti anlama |
| 2-3 | Analysis workflow | Multi-step analysis |
| 3-4 | Code generation | Optimized SP üretimi |
| 5 | Response formatting | Structured AI responses |

**Deliverables:**
- [ ] `app/ai/intent_classifier.py`
- [ ] `app/ai/analysis_workflow.py`
- [ ] `app/ai/code_generator.py`
- [ ] Structured optimization output

---

#### Hafta 13: Output Validation

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Syntax validator | sqlparse + PARSEONLY |
| 2-3 | Security validator | Injection detection |
| 3-4 | Semantic validator | Object existence |
| 5 | Validation UI | Warning/Error display |

**Deliverables:**
- [ ] `app/services/output_validator.py` - 3-layer validation
- [ ] `app/ui/components/validation_dialog.py`
- [ ] Automatic retry on validation failure
- [ ] User confirmation for warnings

---

#### Hafta 14: Security Analysis

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Security scanner | Pattern detection |
| 2-3 | Risk assessment | Severity scoring |
| 3-4 | Security report | Detailed findings |
| 5 | Security UI | Risk dashboard |

**Deliverables:**
- [ ] `app/services/security_analyzer.py`
- [ ] `app/ui/views/security_view.py`
- [ ] SQL injection detection
- [ ] Security recommendations

---

#### Hafta 15: Code Comparison

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Diff algorithm | Side-by-side diff |
| 2-3 | Diff viewer UI | Highlighted changes |
| 3-4 | Metrics comparison | Before/After stats |
| 5 | Export functionality | PDF/HTML export |

**Deliverables:**
- [ ] `app/ui/components/code_diff_viewer.py`
- [ ] Side-by-side comparison
- [ ] Performance metrics comparison
- [ ] Export to file

---

#### Hafta 16: Comprehensive Analysis

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Full analysis workflow | 5-layer analysis |
| 2-3 | Report generation | JSON/HTML report |
| 3-4 | Analysis UI | Dashboard view |
| 5 | Export & sharing | Report export |

**Deliverables:**
- [ ] `app/services/comprehensive_analyzer.py`
- [ ] Full analysis workflow (server â†’ DB â†’ SP â†’ workload â†’ perf)
- [ ] Comprehensive analysis report
- [ ] Report export functionality

---

### 22.5 Phase 4: Polish & Release (Hafta 17-20)

#### Hafta 17: Testing & Bug Fixes

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Unit test completion | %80+ coverage |
| 2-3 | Integration tests | End-to-end scenarios |
| 3-4 | Bug fixing | Known issues resolved |
| 5 | Performance testing | Load testing |

**Deliverables:**
- [ ] Unit tests for all modules
- [ ] Integration test suite
- [ ] Performance benchmarks
- [ ] Bug fixes documented

---

#### Hafta 18: Documentation

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | User documentation | Kullanım kılavuzu |
| 2-3 | API documentation | Code docs |
| 3-4 | Installation guide | Setup instructions |
| 5 | Video tutorials | Demo videos |

**Deliverables:**
- [ ] User manual (TR/EN)
- [ ] API documentation
- [ ] Installation guide
- [ ] Video tutorials

---

#### Hafta 19: Packaging & Distribution

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Windows packaging | EXE installer |
| 2-3 | macOS packaging | DMG/App bundle |
| 3-4 | Linux packaging | AppImage/deb |
| 5 | Auto-update system | Update mechanism |

```bash
# Packaging commands (PyInstaller)

# Windows
pyinstaller --name "SQL Perf AI" \
    --icon assets/icon.ico \
    --windowed \
    --onefile \
    --add-data "assets;assets" \
    --add-data "locales;locales" \
    app/main.py

# macOS
pyinstaller --name "SQL Perf AI" \
    --icon assets/icon.icns \
    --windowed \
    --onefile \
    --osx-bundle-identifier "com.sqlperfai.app" \
    --add-data "assets:assets" \
    --add-data "locales:locales" \
    app/main.py

# Linux
pyinstaller --name "sql-perf-ai" \
    --windowed \
    --onefile \
    --add-data "assets:assets" \
    --add-data "locales:locales" \
    app/main.py
```

**Deliverables:**
- [ ] Windows installer (EXE)
- [ ] macOS app bundle (DMG)
- [ ] Linux AppImage
- [ ] Auto-update mechanism

---

#### Hafta 20: Release & Launch

| Gün | Task | Ã‡ıktı |
|-----|------|-------|
| 1-2 | Final testing | Release candidate |
| 2-3 | Release notes | Changelog |
| 3-4 | Launch preparation | Marketing materials |
| 5 | Release | v1.0.0 ðŸŽ‰ |

**Deliverables:**
- [ ] Release v1.0.0
- [ ] Release notes
- [ ] Landing page
- [ ] Announcement

---

### 22.6 Sprint Planning Template

Her hafta iÇin sprint template:

```markdown
## Sprint [N] - [Tarih]

### Goals
- [ ] Goal 1
- [ ] Goal 2

### Tasks
| Task | Assignee | Est. Hours | Status |
|------|----------|------------|--------|
| Task 1 | - | 4h | â¬œ |
| Task 2 | - | 8h | â¬œ |

### Blockers
- None

### Notes
- 

### Retrospective
- What went well:
- What could improve:
- Action items:
```

### 22.7 Definition of Done

Her task iÇin "Done" kriterleri:

| Kategori | Kriter |
|----------|--------|
| **Code** | Code complete, follows style guide |
| **Tests** | Unit tests written, passing |
| **Docs** | Docstrings added, README updated if needed |
| **Review** | Code reviewed (self or peer) |
| **UI** | Works in Light/Dark theme |
| **i18n** | All strings in language files |

### 22.8 Risk Mitigation

| Risk | Olasılık | Etki | Mitigation |
|------|----------|------|------------|
| Ollama performance | Orta | Yüksek | Cache aggressively, async calls |
| SQL Server version differences | Yüksek | Orta | Extensive testing, version detection |
| pyqt6 limitations | Düşük | Orta | Fallback to custom components |
| AI hallucination | Yüksek | Yüksek | 3-layer validation, retry logic |
| Cross-platform issues | Orta | Orta | CI/CD on all platforms |

### 22.9 Technology Decisions Log

| Karar | Tarih | GerekÇe | Alternatifler |
|-------|-------|---------|---------------|
| pyqt6 for UI | - | Cross-platform, Python-native | PyQt, Tkinter, Electron |
| SQLAlchemy | - | Mature, async support | pyodbc direct |
| Ollama | - | Local, privacy | OpenAI API, Claude API |
| Poetry | - | Modern dependency mgmt | pip, pipenv |
| Pydantic | - | Data validation | dataclasses |

### 22.10 Milestone Checklist

#### ðŸ Milestone 1: Working Shell (Hafta 5)
- [ ] App launches without errors
- [ ] Navigation between views works
- [ ] Connection manager functional
- [ ] Can connect to SQL Server
- [ ] Theme switching works

#### ðŸ Milestone 2: Basic Analysis (Hafta 11)
- [ ] SP list displayed
- [ ] SP code viewable
- [ ] Query statistics visible
- [ ] Basic AI chat works
- [ ] Cache system operational

#### ðŸ Milestone 3: Full Features (Hafta 16)
- [ ] AI optimization generates code
- [ ] Output validation works
- [ ] Security analysis complete
- [ ] Code comparison functional
- [ ] Comprehensive reports

#### ðŸ Milestone 4: Production Ready (Hafta 20)
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Installers ready
- [ ] Performance acceptable
- [ ] v1.0.0 released

---

## 23. Deployment & Packaging

### 23.1 Hedef Paket Boyutları

```
#------------------------------------------------------------------------------
#                    PAKET BOYUTU KARÅžILAÅžTIRMASI                             #
#------------------------------------------------------------------------------¤
#                                                                             #
#  FLET (Eski)                     PyQt6 (Yeni)                               #
#  ------------                    -------------                              #
#  ðŸ“¦ 150-200 MB                   ðŸ“¦ 35-50 MB                                #
#  #-- Flutter Engine: 80 MB       #-- Qt Core: 15 MB                         #
#  #-- Dart Runtime: 40 MB         #-- Qt Widgets: 10 MB                      #
#  #-- Python: 30 MB               #-- Python: 15 MB                          #
#  -”-- Dependencies: 50 MB         -”-- Dependencies: 10 MB                    #
#                                                                             #
#  â±ï¸ Startup: 2-3 saniye          â±ï¸ Startup: 0.5 saniye                     #
#  ðŸ’¾ RAM: 150+ MB                 ðŸ’¾ RAM: 50-80 MB                           #
#                                                                             #
#  KAZANÃ‡: %70-75 DAHA KÃœÃ‡ÃœK, 5X DAHA HIZLI BAÅžLANGIÃ‡                        #
#                                                                             #
-”------------------------------------------------------------------------------˜
```

### 23.2 Minimal Dependency Stratejisi

#### Sadece Gerekli PyQt6 Modülleri

```python
# âŒ YANLIÅž - Tüm PyQt6'yı import etme
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# âœ… DOÄžRU - Sadece kullanılanları import et
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableView, QTreeView, QStackedWidget, QSplitter,
    QDialog, QProgressDialog, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette
```

#### Minimal Requirements

```txt
# requirements-minimal.txt (Production)
PyQt6-Qt6==6.6.0          # Sadece gerekli Qt modülleri
PyQt6==6.6.0
PyQt6-QScintilla==2.14.0  # Kod editör
SQLAlchemy==2.0.23
pyodbc==5.0.1
aiohttp==3.9.1
pydantic==2.5.0
keyring==24.3.0
pyyaml==6.0.1

# âŒ EKLEME - Bunlar paket boyutunu artırır
# PyQt6-WebEngine  (+50MB)
# PyQt6-3D         (+30MB)
# PyQt6-Charts     (+20MB)
```

### 23.3 PyInstaller Optimizasyonu

#### Minimal Spec Dosyası

```python
# sql_perf_ai.spec
# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Sadece gerekli dosyaları dahil et
added_files = [
    ('locales/*.json', 'locales'),
    ('assets/icons/*.png', 'assets/icons'),
    ('app/ui/styles/*.qss', 'app/ui/styles'),
    ('prompts/*.yaml', 'prompts'),
]

# EXCLUDE - Gereksiz modüller
excluded_modules = [
    'PyQt6.QtWebEngine',
    'PyQt6.QtWebEngineCore', 
    'PyQt6.QtWebEngineWidgets',
    'PyQt6.Qt3DCore',
    'PyQt6.Qt3DRender',
    'PyQt6.QtCharts',
    'PyQt6.QtDataVisualization',
    'PyQt6.QtMultimedia',
    'PyQt6.QtBluetooth',
    'PyQt6.QtNfc',
    'PyQt6.QtPositioning',
    'PyQt6.QtRemoteObjects',
    'PyQt6.QtSensors',
    'PyQt6.QtSerialPort',
    'PyQt6.QtTest',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'PIL',
    'cv2',
    'tkinter',
    '_tkinter',
]

a = Analysis(
    ['app/main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=['keyring.backends.Windows'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Gereksiz binary'leri Çıkar
a.binaries = [b for b in a.binaries if not any(
    x in b[0].lower() for x in [
        'qt6webengine', 'qt6quick', 'qt63d', 'qt6multimedia',
        'opengl32sw', 'libcrypto', 'libssl'
    ]
)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SQL Perf AI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,           # Strip debug symbols
    upx=True,             # UPX compression
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # Windowed app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)
```

### 23.4 Build Scripts

#### Windows Build

```batch
@echo off
REM build_windows.bat

echo === SQL Perf AI - Windows Build ===

REM Clean previous builds
rmdir /s /q dist build 2>nul

REM Create virtual environment
python -m venv .venv
call .venv\Scripts\activate

REM Install minimal dependencies
pip install -r requirements-minimal.txt
pip install pyinstaller

REM Build with spec file
pyinstaller sql_perf_ai.spec --clean

REM UPX compression (optional, extra 30% smaller)
REM upx --best dist\SQL_Perf_AI.exe

echo === Build complete: dist\SQL Perf AI.exe ===
dir dist\*.exe

pause
```

#### Linux/macOS Build

```bash
#!/bin/bash
# build_unix.sh

echo "=== SQL Perf AI - Unix Build ==="

# Clean
rm -rf dist build

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install
pip install -r requirements-minimal.txt
pip install pyinstaller

# Build
pyinstaller sql_perf_ai.spec --clean

# Make executable
chmod +x dist/sql-perf-ai

echo "=== Build complete: dist/sql-perf-ai ==="
ls -lh dist/
```

### 23.5 Portable Deployment

#### Folder Yapısı (Portable)

```
SQL-Perf-AI-Portable/
#
#-- SQL Perf AI.exe          # ~35-40 MB (tek dosya)
#
#-- config/
#   -”-- settings.json        # Kullanıcı ayarları
#
#-- data/
#   -”-- connections.json     # Bağlantı profilleri (şifresiz)
#
-”-- logs/
    -”-- app.log              # Uygulama logları
```

#### Portable Config Detection

```python
# app/core/portable.py

import sys
import os
from pathlib import Path

def get_app_dir() -> Path:
    """
    Portable vs Installed mode detection
    Portable: exe ile aynı klasör
    Installed: AppData/Local/SQL Perf AI
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller executable
        exe_dir = Path(sys.executable).parent
        
        # Portable mode: config klasörü exe yanında mı?
        if (exe_dir / 'config').exists():
            return exe_dir
    
    # Installed mode: user data folder
    if sys.platform == 'win32':
        return Path(os.environ['LOCALAPPDATA']) / 'SQL Perf AI'
    elif sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'SQL Perf AI'
    else:
        return Path.home() / '.config' / 'sql-perf-ai'

def ensure_dirs():
    """Gerekli klasörleri oluştur"""
    app_dir = get_app_dir()
    (app_dir / 'config').mkdir(parents=True, exist_ok=True)
    (app_dir / 'data').mkdir(parents=True, exist_ok=True)
    (app_dir / 'logs').mkdir(parents=True, exist_ok=True)
    return app_dir
```

### 23.6 ODBC Driver Yönetimi

SQL Server'a bağlanmak iÇin ODBC driver gerekli. Bunu kullanıcıya aÇıkÇa bildirmemiz gerekiyor.

```python
# app/core/odbc_check.py

import pyodbc
from typing import Optional, List

def get_available_drivers() -> List[str]:
    """Sistemdeki SQL Server ODBC driver'ları"""
    drivers = pyodbc.drivers()
    sql_drivers = [d for d in drivers if 'SQL Server' in d]
    return sql_drivers

def get_best_driver() -> Optional[str]:
    """En iyi ODBC driver'ı seÇ"""
    drivers = get_available_drivers()
    
    # Tercih sırası (yeniden eskiye)
    preferred = [
        'ODBC Driver 18 for SQL Server',
        'ODBC Driver 17 for SQL Server',
        'ODBC Driver 13 for SQL Server',
        'SQL Server Native Client 11.0',
        'SQL Server',
    ]
    
    for pref in preferred:
        if pref in drivers:
            return pref
    
    return drivers[0] if drivers else None

def check_odbc_installed() -> tuple[bool, str]:
    """ODBC kurulum kontrolü"""
    driver = get_best_driver()
    
    if driver:
        return True, f"âœ… {driver}"
    else:
        return False, """
âŒ SQL Server ODBC Driver bulunamadı!

Lütfen aşağıdaki linkten indirip kurun:
https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

Ã–nerilen: ODBC Driver 18 for SQL Server
"""
```

#### İlk Ã‡alıştırmada Kontrol

```python
# app/main.py

def main():
    from app.core.odbc_check import check_odbc_installed
    
    # ODBC kontrolü
    odbc_ok, message = check_odbc_installed()
    
    if not odbc_ok:
        # Basit dialog göster
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("ODBC Driver Required")
        msg.setText("SQL Server ODBC Driver bulunamadı")
        msg.setInformativeText(message)
        msg.exec()
        
        sys.exit(1)
    
    # Normal başlatma
    run_app()
```

### 23.7 Tahmini Final Boyutlar

| Platform | Boyut | İÇerik |
|----------|-------|--------|
| **Windows (exe)** | ~40 MB | Tek dosya, UPX sıkıştırılmış |
| **Windows (folder)** | ~60 MB | Klasör yapısı, DLL'ler ayrı |
| **macOS (app)** | ~50 MB | .app bundle |
| **Linux (AppImage)** | ~55 MB | Tek dosya, portable |

### 23.8 Flet vs PyQt6 Karşılaştırma Ã–zeti

| Kriter | Flet | PyQt6 | Winner |
|--------|------|-------|--------|
| Paket boyutu | 150-200 MB | 35-50 MB | PyQt6 âœ… |
| Startup süresi | 2-3 sn | 0.5 sn | PyQt6 âœ… |
| RAM kullanımı | 150+ MB | 50-80 MB | PyQt6 âœ… |
| Portable deployment | Zor | Kolay | PyQt6 âœ… |
| ODBC dependency | Aynı | Aynı | Berabere |
| Web desteği | âœ… Var | âŒ Yok | Flet |
| Build complexity | Kolay | Orta | Flet |

---

## 24. Query Stats Modülü

### 24.1 Modül Kimliği

| Alan | Değer |
|------|-------|
| **Modül Adı** | Query Stats |
| **Hedef Kullanıcı** | DBA, Senior Developer |
| **Amaç** | Sorgu performansını analiz et, AI destekli tune önerileri sun |
| **Veri Kaynağı** | Query Store (birincil), DMV (anlık tamamlayıcı) |
| **Minimum Versiyon** | SQL Server 2017+ |

### 24.2 Modülün Kapsamı ve Sınırları

**Ne YAPAR:**
- Query Store'dan performans metriklerini çeker ve görselleştirir
- Sorgu bazlı wait istatistiklerini analiz eder
- Plan stabilitesini değerlendirir
- Regresyon ve anomali tespiti yapar
- AI'a zengin context sağlayarak aksiyon odaklı öneriler üretir

**Ne YAPMAZ:**
- Sürekli veri toplamaz (bu Query Store'un işi)
- Kendi history veritabanı tutmaz
- Müşteri verisine erişmez (sadece metadata)
- Otomatik değişiklik uygulamaz (sadece öneri)

### 24.3 Veri Toplama Stratejisi

Kullanıcı "Analyze" tetiklediğinde tek seferde paralel çekim (on-demand):

| Sorgu | Kaynak | Amaç |
|-------|--------|------|
| Runtime Stats | `sys.query_store_runtime_stats` | CPU, duration, reads, writes |
| Wait Stats | `sys.query_store_wait_stats` | Sorgu bazlı bekleme profili |
| Plan Info | `sys.query_store_plan` | Plan sayısı, değişim tarihleri |
| Query Text | `sys.query_store_query_text` | Normalize edilmiş SQL |
| Anlık Plan | `sys.dm_exec_query_plan` | Güncel execution plan XML |

**Zaman Aralığı Seçenekleri:**
- Son 24 saat (hızlı analiz)
- Son 7 gün (varsayılan)
- Son 30 gün (trend analizi)
- Custom range

### 24.4 Metrik Tanımları

#### 24.4.1 Temel Metrikler

| Metrik | Hesaplama | Birim |
|--------|-----------|-------|
| Avg Duration | `avg_duration_us / 1000` | ms |
| P95 Duration | `percentile_disc(0.95)` | ms |
| Avg CPU | `avg_cpu_time_us / 1000` | ms |
| Avg Logical Reads | `avg_logical_io_reads` | page |
| Avg Physical Reads | `avg_physical_io_reads` | page |
| Execution Count | `count_executions` | adet |
| Plan Count | `COUNT(DISTINCT plan_id)` | adet |

#### 24.4.2 Türetilmiş Skorlar

**Impact Score:**
```
Impact Score = (P95 Duration) × (Execution Count) × (Trend Katsayısı)
```
- Trend Katsayısı: Son 7 gün / önceki 7 gün oranı
- Yüksek skor = öncelikli tune hedefi

**Stability Score:**
```
Stability Score = 1 / (Plan Değişim Sayısı + Latency Varyansı)
```
- Düşük skor = parametre sniffing veya plan instability şüphesi

**IO-Bound Ratio:**
```
IO-Bound Ratio = (PAGEIOLATCH waits) / (Total Wait Time)
```
- Yüksek oran = disk/index problemi
- Düşük oran = CPU veya lock problemi

### 24.5 Wait Kategorileri

DBA'ların hızlı karar vermesi için gruplandırılmış wait'ler:

| Kategori | Wait Types | Olası Neden |
|----------|------------|-------------|
| **IO** | PAGEIOLATCH_SH/EX, WRITELOG | Disk yavaş, index eksik, buffer pool yetersiz |
| **CPU** | SOS_SCHEDULER_YIELD | CPU baskısı, paralellik sorunu |
| **Lock** | LCK_M_X/S/U/IX/IS | Blocking, isolation level |
| **Parallelism** | CXPACKET, CXCONSUMER | MAXDOP ayarı, skewed distribution |
| **Memory** | RESOURCE_SEMAPHORE | Memory grant yetersiz |
| **Network** | ASYNC_NETWORK_IO | Client yavaş tüketiyor |

### 24.6 Plan Stability Eşikleri

| Plan Sayısı | Durum | Gösterge |
|-------------|-------|----------|
| 1 plan | Stabil | 🟢 |
| 2-3 plan | Dikkat | 🟡 |
| 4+ plan | Problem | 🔴 |

### 24.7 UI Yapısı

#### 24.7.1 Ana Görünüm (Liste)

```
┌─────────────────────────────────────────────────────────────────┐
│ Query Stats                                    [Son 7 gün ▼]   │
├─────────────────────────────────────────────────────────────────┤
│ Sıralama: [Impact Score ▼]  Filtre: [Tümü ▼]  [🔍 Ara...]      │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 🔴 usp_GetOrderDetails          Impact: 94.2    ▁▃▅▇█▇▅    │ │
│ │    Avg: 450ms  P95: 1.2s  Exec: 15K  Plans: 3   ↑ 45%      │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ 🟡 usp_SearchProducts           Impact: 67.8    ▂▂▃▃▄▄▅    │ │
│ │    Avg: 320ms  P95: 890ms Exec: 8K   Plans: 1   ↑ 12%      │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ 🟢 usp_GetCustomerInfo          Impact: 23.1    ▃▃▃▃▃▃▃    │ │
│ │    Avg: 45ms   P95: 120ms Exec: 50K  Plans: 1   → 0%       │ │
│ └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Liste Özellikleri:**
- Sparkline: Günlük trend (detayda saatlik opsiyonel)
- Renk kodlu durum göstergesi
- Tek tıkla detay sayfasına geçiş

#### 24.7.2 Detay Görünümü

```
┌─────────────────────────────────────────────────────────────────┐
│ usp_GetOrderDetails                              [Analyze AI]   │
├──────────────────────────┬──────────────────────────────────────┤
│ PERFORMANCE METRICS      │  TREND (Son 7 gün)                   │
│ ─────────────────────    │  ┌────────────────────────────────┐  │
│ Avg Duration:    450 ms  │  │    ▁                           │  │
│ P95 Duration:    1.2 s   │  │   ▃█▇                          │  │
│ Avg CPU:         180 ms  │  │  ▅███▆▄                        │  │
│ Avg Reads:       12.5K   │  │ ▂██████▅▃                      │  │
│ Executions:      15,420  │  └────────────────────────────────┘  │
│ Plan Count:      3 ⚠️    │                                      │
├──────────────────────────┼──────────────────────────────────────┤
│ WAIT PROFILE             │  AI ÖNERİLERİ                        │
│ ─────────────────────    │  ─────────────────────               │
│ ████████░░ IO      62%   │  🔴 Missing Index                    │
│ ███░░░░░░░ CPU     24%   │     OrderDate + CustomerID           │
│ █░░░░░░░░░ Lock     8%   │     Tahmini kazanç: %40 duration     │
│ ░░░░░░░░░░ Other    6%   │                                      │
│                          │  🟡 Statistics Outdated              │
│                          │     Orders tablosu - 15 gün önce     │
│                          │                                      │
│                          │  🟢 Plan Stability                   │
│                          │     3 farklı plan tespit edildi      │
│                          │     Parametre sniffing olası         │
└──────────────────────────┴──────────────────────────────────────┘
```

### 24.8 AI Context Entegrasyonu

Query Stats modülü, Section 17.6'daki JSON Context Format'ına uygun veri hazırlar:

```json
{
  "query_stats_context": {
    "query_id": 12345,
    "query_hash": "0x7A3B2C1D...",
    
    "metrics": {
      "avg_duration_ms": 450,
      "p95_duration_ms": 1200,
      "avg_cpu_ms": 180,
      "avg_logical_reads": 12500,
      "execution_count": 15420,
      "plan_count": 3
    },
    
    "trend": {
      "duration_change_percent": 45,
      "direction": "increasing",
      "regression_detected": true
    },
    
    "wait_profile": {
      "io_percent": 62,
      "cpu_percent": 24,
      "lock_percent": 8,
      "dominant_wait": "PAGEIOLATCH_SH"
    },
    
    "stability": {
      "plan_changes_7d": 3,
      "latency_variance": 0.85,
      "param_sensitivity_suspected": true
    }
  }
}
```

### 24.9 Query Store Sorguları

```python
# Query Stats için temel sorgular

"query_stats_top_by_duration": {
    "description": "En yavaş sorgular (Query Store)",
    "min_version": 14,  # SQL Server 2017+
    "parameters": ["top_n", "days"],
    "sql": """
        SELECT TOP (@top_n)
            q.query_id,
            q.query_hash,
            qt.query_sql_text,
            COUNT(DISTINCT p.plan_id) AS plan_count,
            SUM(rs.count_executions) AS total_executions,
            AVG(rs.avg_duration) / 1000.0 AS avg_duration_ms,
            AVG(rs.avg_cpu_time) / 1000.0 AS avg_cpu_ms,
            AVG(rs.avg_logical_io_reads) AS avg_logical_reads,
            MAX(rs.last_execution_time) AS last_execution
        FROM sys.query_store_query q
        JOIN sys.query_store_query_text qt ON q.query_text_id = qt.query_text_id
        JOIN sys.query_store_plan p ON q.query_id = p.query_id
        JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
        JOIN sys.query_store_runtime_stats_interval rsi ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
        WHERE rsi.start_time > DATEADD(day, -@days, GETDATE())
        GROUP BY q.query_id, q.query_hash, qt.query_sql_text
        ORDER BY AVG(rs.avg_duration) DESC
    """
},

"query_wait_stats": {
    "description": "Sorgu bazlı wait istatistikleri",
    "min_version": 14,
    "parameters": ["query_id", "days"],
    "sql": """
        SELECT 
            ws.wait_category_desc,
            SUM(ws.total_query_wait_time_ms) AS total_wait_ms,
            SUM(ws.total_query_wait_time_ms) * 100.0 / 
                SUM(SUM(ws.total_query_wait_time_ms)) OVER() AS wait_percent
        FROM sys.query_store_wait_stats ws
        JOIN sys.query_store_runtime_stats_interval rsi 
            ON ws.runtime_stats_interval_id = rsi.runtime_stats_interval_id
        JOIN sys.query_store_plan p ON ws.plan_id = p.plan_id
        WHERE p.query_id = @query_id
          AND rsi.start_time > DATEADD(day, -@days, GETDATE())
        GROUP BY ws.wait_category_desc
        ORDER BY total_wait_ms DESC
    """
},

"query_plan_stability": {
    "description": "Plan stability analizi",
    "min_version": 14,
    "parameters": ["query_id", "days"],
    "sql": """
        SELECT 
            p.plan_id,
            p.query_plan_hash,
            p.is_forced_plan,
            p.force_failure_count,
            MIN(rs.first_execution_time) AS first_seen,
            MAX(rs.last_execution_time) AS last_seen,
            SUM(rs.count_executions) AS execution_count,
            AVG(rs.avg_duration) / 1000.0 AS avg_duration_ms,
            STDEV(rs.avg_duration) / 1000.0 AS stdev_duration_ms
        FROM sys.query_store_plan p
        JOIN sys.query_store_runtime_stats rs ON p.plan_id = rs.plan_id
        JOIN sys.query_store_runtime_stats_interval rsi 
            ON rs.runtime_stats_interval_id = rsi.runtime_stats_interval_id
        WHERE p.query_id = @query_id
          AND rsi.start_time > DATEADD(day, -@days, GETDATE())
        GROUP BY p.plan_id, p.query_plan_hash, p.is_forced_plan, p.force_failure_count
        ORDER BY execution_count DESC
    """
}
```

---

## 25. Performans Analiz Modülleri Arası İlişki

### 25.1 Modül Sorumluluk Dağılımı

```
┌─────────────────────────────────────────────────────────────┐
│                PERFORMANS ANALİZ MODÜLLERİ                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐      ┌──────────────┐                    │
│   │ Query Stats  │─────▶│ Plan Analyzer│                    │
│   │              │      │              │                    │
│   │ • Metrikler  │      │ • Operatörler│                    │
│   │ • Trendler   │      │ • Tahminler  │                    │
│   │ • Wait'ler   │      │ • Spill/Grant│                    │
│   └──────┬───────┘      └──────────────┘                    │
│          │                     ▲                            │
│          │                     │                            │
│          ▼                     │                            │
│   ┌──────────────┐      ┌──────┴───────┐                    │
│   │Index Analyzer│◀────▶│  AI Engine   │                    │
│   │              │      │              │                    │
│   │ • Kullanım   │      │ • Context    │                    │
│   │ • Missing    │      │ • Öneriler   │                    │
│   │ • Overlap    │      │ • Öncelik    │                    │
│   └──────────────┘      └──────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 25.2 Sorumluluk Matrisi

| Modül | Tek Sorumluluk | Çıktı |
|-------|----------------|-------|
| **Query Stats** | Sorgu performans metriklerini topla ve göster | NE olduğunu söyler |
| **Plan Analyzer** | Execution plan'ı görselleştir ve operatör analizi yap | NEDEN olduğunu gösterir |
| **Index Analyzer** | Index kullanımını değerlendir ve öneriler sun | ÇÖZÜMÜ önerir |
| **AI Engine** | Tüm sinyalleri birleştir, önceliklendirilmiş öneriler üret | PRİORİTİZE eder |

### 25.3 Veri Akışı

```
┌─────────────────────────────────────────────────────────────────┐
│                        VERİ AKIŞI                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Object Explorer                                                │
│       │                                                         │
│       ▼ (Nesne seçimi)                                         │
│  ┌─────────────┐                                               │
│  │ Query Stats │─────────────────────────────────┐             │
│  │             │                                 │             │
│  │ query_id    │                                 │             │
│  │ metrics     │                                 ▼             │
│  │ wait_profile│──────────────────────▶  ┌─────────────┐       │
│  │ trend_data  │                         │  AI Engine  │       │
│  └─────────────┘                         │             │       │
│       │                                  │ ┌─────────┐ │       │
│       ▼ (plan_id)                        │ │ Context │ │       │
│  ┌─────────────┐                         │ │ Builder │ │       │
│  │Plan Analyzer│────────────────────────▶│ └─────────┘ │       │
│  │             │                         │      │      │       │
│  │ operators   │                         │      ▼      │       │
│  │ estimates   │                         │ ┌─────────┐ │       │
│  │ warnings    │                         │ │ LLM API │ │       │
│  └─────────────┘                         │ └─────────┘ │       │
│       │                                  │      │      │       │
│       ▼ (table_names)                    │      ▼      │       │
│  ┌─────────────┐                         │ ┌─────────┐ │       │
│  │Index Analyzer──────────────────────▶│ │Priority │ │       │
│  │             │                         │ │ Matrix  │ │       │
│  │ usage_stats │                         │ └─────────┘ │       │
│  │ missing     │                         └──────┬──────┘       │
│  │ fragmentation                                │              │
│  └─────────────┘                                ▼              │
│                                          ┌─────────────┐       │
│                                          │  Öneriler   │       │
│                                          │ (öncelikli) │       │
│                                          └─────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 25.4 Modüller Arası Veri Paylaşımı

| Kaynak Modül | Hedef Modül | Paylaşılan Veri |
|--------------|-------------|-----------------|
| Object Explorer | Query Stats | Seçilen nesne (SP/Query) bilgisi |
| Query Stats | Plan Analyzer | query_id, plan_id |
| Query Stats | Index Analyzer | Sorgu tarafından erişilen tablolar |
| Query Stats | AI Engine | Metrikler, wait profili, trend |
| Plan Analyzer | AI Engine | Operatör maliyetleri, uyarılar |
| Plan Analyzer | Index Analyzer | Scan/Seek oranları, key lookup |
| Index Analyzer | AI Engine | Missing index, kullanım istatistikleri |
| AI Engine | UI | Önceliklendirilmiş öneri listesi |

### 25.5 Section 17 ile Entegrasyon

Query Stats modülü, **Section 17: Kapsamlı Performans Analiz Framework'ü** ile şu noktalarda entegre olur:

| Framework Adımı | Query Stats Katkısı |
|-----------------|---------------------|
| Adım 4: İş Yükü Analizi | Execution count, trend, plan stability |
| Adım 5: Performans Metrikleri | Wait stats, duration, CPU, IO |
| Adım 6: AI Analiz | query_stats_context JSON |
| Adım 7: Kullanıcıya Sunum | Önceliklendirilmiş liste, detay sayfası |

### 25.6 Öncelik Matrisi Entegrasyonu

Section 17.5'teki öncelik matrisi Query Stats modülünde şu şekilde uygulanır:

| Öncelik | Query Stats Sinyali | Örnek |
|---------|---------------------|-------|
| 🔴 Kritik | Impact Score > 90, Plan Count > 4 | Regresyon + instability |
| 🟠 Yüksek | Impact Score 70-90, Trend > %30 | Hızlı kötüleşme |
| 🟡 Orta | Impact Score 40-70, Plan Count 2-3 | Dikkat gerektiren |
| 🟢 Düşük | Impact Score < 40, Stabil trend | İzleme modunda |
| ⚪ Bilgi | Yeni sorgu, yetersiz veri | Baseline oluşturuluyor |

---

## SonuÇ

Bu döküman, SQL Performance AI Platform projesinin kapsamlı tasarım rehberidir. SP Studio'nun güÇlü temelini koruyarak, modern PyQt6 UI, local AI entegrasyonu ve kurumsal özelliklerle genişletilmiş yeni bir platform oluşturulacaktır.

**Temel Prensipler:**
1. Müşteri verisine asla dokunma - sadece metadata
2. Local AI ile veri gizliliği
3. Hem öneri hem düzeltilmiş kod üret
4. Desktop-first, native performans (PyQt6)
5. Global pazar, Çoklu dil
6. SQL Server version-aware sorgular
7. Ã‡oklu bağlantı yönetimi, güvenli credential storage
8. 5 katmanlı kapsamlı performans analizi
9. SQL kod güvenlik analizi ve önerileri
10. Akıllı caching ile performans optimizasyonu
11. Async mimari ile responsive UI
12. 3 katmanlı AI output doğrulama
13. Minimal paket boyutu (~40 MB), portable deployment
14. **Object Explorer ile SSMS benzeri navigasyon**
15. **Pre-loading ile hızlı metadata erişimi**
16. **Query Stats modülü ile on-demand performans analizi**

**Teknoloji SeÇimleri (Stabil Versiyonlar):**
- **UI Framework:** PyQt6 6.6.1 (LTS, native performans)
- **Kod Editör:** QScintilla 2.14.1
- **DB:** SQLAlchemy 2.0.25 + pyodbc 5.1.0
- **AI:** Ollama (Local LLM)
- **Packaging:** PyInstaller 6.3.0 + UPX

**Metadata Pre-Loading:**
| Obje Tipi | Toplanan Bilgi |
|-----------|----------------|
| **SP** | Kod, istatistikler, bağımlılıklar, execution plan |
| **Trigger** | Kod, istatistikler, event type, durum |
| **View** | Kod, bağımlılıklar, index bilgisi |
| **Index** | Missing, unused, fragmentation |
| **Performance** | Wait stats, active sessions, blocking |

**Paket Boyutu:** ~40 MB (Flet: 150-200 MB â†’ %75 küÇülme)

**Toplam: 48+ metadata sorgusu, 25 bölüm dokümantasyon**

---

*Döküman Versiyonu: 1.9*  
*Son Güncelleme: Ocak 2025*  
*UI Framework: PyQt6 6.6.1 (Stabil)*  
*Özellikler: Object Explorer, Pre-Loading, SSMS-style UI, Query Stats*  
*Toplam: 25 Bölüm*
