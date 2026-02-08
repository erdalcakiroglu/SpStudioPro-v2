"""
Security Audit Queries - SQL Server security analysis
"""

from enum import Enum
from typing import Dict


class SecurityRisk(Enum):
    """Security risk levels"""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"


# Risk level colors
RISK_COLORS: Dict[SecurityRisk, str] = {
    SecurityRisk.CRITICAL: "#DC2626",  # Red-600
    SecurityRisk.HIGH: "#EF4444",      # Red-500
    SecurityRisk.MEDIUM: "#D97706",    # Amber-600
    SecurityRisk.LOW: "#2563EB",       # Blue-600
    SecurityRisk.INFO: "#64748B",      # Slate-500
}


class SecurityQueries:
    """SQL queries for Security Audit"""
    
    # ══════════════════════════════════════════════════════════════════════
    # SERVER-LEVEL SECURITY
    # ══════════════════════════════════════════════════════════════════════
    
    # All SQL Logins
    SERVER_LOGINS = """
    SELECT 
        p.name AS login_name,
        p.type_desc AS login_type,
        p.is_disabled,
        p.create_date,
        p.modify_date,
        p.default_database_name,
        CONVERT(datetime, LOGINPROPERTY(p.name, 'PasswordLastSetTime')) AS password_last_set,
        CONVERT(int, LOGINPROPERTY(p.name, 'DaysUntilExpiration')) AS days_until_expiration,
        CONVERT(int, LOGINPROPERTY(p.name, 'IsExpired')) AS is_expired,
        CONVERT(int, LOGINPROPERTY(p.name, 'IsLocked')) AS is_locked,
        CONVERT(int, LOGINPROPERTY(p.name, 'IsMustChange')) AS must_change_password,
        CONVERT(int, LOGINPROPERTY(p.name, 'BadPasswordCount')) AS bad_password_count,
        CONVERT(datetime, LOGINPROPERTY(p.name, 'BadPasswordTime')) AS bad_password_time
    FROM sys.server_principals p
    WHERE p.type IN ('S', 'U', 'G')  -- SQL Login, Windows User, Windows Group
      AND p.name NOT LIKE '##%'
      AND p.name NOT LIKE 'NT %'
    ORDER BY p.name
    """
    
    # Server Role Members
    SERVER_ROLE_MEMBERS = """
    SELECT 
        r.name AS role_name,
        m.name AS member_name,
        m.type_desc AS member_type,
        m.is_disabled
    FROM sys.server_role_members rm
    JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
    JOIN sys.server_principals m ON rm.member_principal_id = m.principal_id
    WHERE r.type = 'R'
    ORDER BY r.name, m.name
    """
    
    # Sysadmin Members (Critical)
    SYSADMIN_MEMBERS = """
    SELECT 
        m.name AS login_name,
        m.type_desc AS login_type,
        m.is_disabled,
        m.create_date
    FROM sys.server_role_members rm
    JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
    JOIN sys.server_principals m ON rm.member_principal_id = m.principal_id
    WHERE r.name = 'sysadmin'
      AND m.name NOT IN ('sa', 'NT AUTHORITY\\SYSTEM', 'NT SERVICE\\MSSQLSERVER')
    ORDER BY m.name
    """
    
    # SA Account Status
    SA_ACCOUNT_CHECK = """
    SELECT 
        name,
        is_disabled,
        LOGINPROPERTY(name, 'IsLocked') AS is_locked,
        LOGINPROPERTY(name, 'PasswordLastSetTime') AS password_last_set
    FROM sys.server_principals
    WHERE name = 'sa'
    """
    
    # Server-level Permissions
    SERVER_PERMISSIONS = """
    SELECT 
        pr.name AS principal_name,
        pr.type_desc AS principal_type,
        pe.permission_name,
        pe.state_desc AS permission_state
    FROM sys.server_permissions pe
    JOIN sys.server_principals pr ON pe.grantee_principal_id = pr.principal_id
    WHERE pe.state IN ('G', 'W')  -- Grant or Grant with Grant
      AND pr.name NOT LIKE '##%'
      AND pr.name NOT LIKE 'NT %'
    ORDER BY pr.name, pe.permission_name
    """

    # Critical Server-Level Permissions (half-sysadmin)
    CRITICAL_SERVER_PERMISSIONS = """
    SELECT
        pr.name AS principal_name,
        pr.type_desc AS principal_type,
        pe.permission_name,
        pe.state_desc AS permission_state,
        CASE WHEN sr.name = 'sysadmin' THEN 1 ELSE 0 END AS is_sysadmin_member
    FROM sys.server_permissions pe
    JOIN sys.server_principals pr ON pe.grantee_principal_id = pr.principal_id
    LEFT JOIN sys.server_role_members srm
        ON srm.member_principal_id = pr.principal_id
    LEFT JOIN sys.server_principals sr
        ON srm.role_principal_id = sr.principal_id
       AND sr.name = 'sysadmin'
    WHERE pe.state IN ('G', 'W')
      AND pe.permission_name IN (
        'CONTROL SERVER',
        'ALTER ANY LOGIN',
        'ALTER ANY DATABASE',
        'ALTER ANY CREDENTIAL',
        'ALTER ANY LINKED SERVER'
      )
      AND pr.name NOT LIKE '##%'
      AND pr.name NOT LIKE 'NT %'
      AND pr.name <> 'sa'
    ORDER BY pe.permission_name, pr.name
    """

    # Surface Area / Risky Server Configuration
    SURFACE_AREA_CONFIG = """
    SELECT
        name AS config_name,
        CAST(value_in_use AS int) AS value_in_use
    FROM sys.configurations
    WHERE name IN (
        'xp_cmdshell',
        'Ad Hoc Distributed Queries',
        'Ole Automation Procedures',
        'SQL Mail XPs',
        'Database Mail XPs',
        'clr enabled',
        'clr strict security',
        'external scripts enabled'
    )
    ORDER BY name
    """

    # Recon / Wide-Read Server Permissions (P2/P3 hardening)
    RECON_SERVER_PERMISSIONS = """
    SELECT
        pr.name AS principal_name,
        pr.type_desc AS principal_type,
        pe.permission_name,
        pe.state_desc AS permission_state,
        CASE WHEN sr.name = 'sysadmin' THEN 1 ELSE 0 END AS is_sysadmin_member
    FROM sys.server_permissions pe
    JOIN sys.server_principals pr ON pe.grantee_principal_id = pr.principal_id
    LEFT JOIN sys.server_role_members srm
        ON srm.member_principal_id = pr.principal_id
    LEFT JOIN sys.server_principals sr
        ON srm.role_principal_id = sr.principal_id
       AND sr.name = 'sysadmin'
    WHERE pe.state IN ('G', 'W')
      AND pe.permission_name IN (
        'VIEW SERVER STATE',
        'VIEW ANY DATABASE',
        'CONNECT ANY DATABASE',
        'IMPERSONATE ANY LOGIN'
      )
      AND pr.name NOT LIKE '##%'
      AND pr.name NOT LIKE 'NT %'
      AND pr.name <> 'sa'
    ORDER BY pe.permission_name, pr.name
    """

    # Object-level permission volume per principal (current DB)
    OBJECT_PERMISSION_COUNTS = """
    SELECT
        dp.name AS principal_name,
        dp.type_desc AS principal_type,
        COUNT(*) AS perm_count
    FROM sys.database_permissions p
    JOIN sys.database_principals dp
        ON p.grantee_principal_id = dp.principal_id
    WHERE p.state IN ('G', 'W')
      AND p.class_desc IN ('OBJECT_OR_COLUMN', 'SCHEMA')
      AND dp.name NOT IN ('dbo', 'INFORMATION_SCHEMA', 'sys')
    GROUP BY dp.name, dp.type_desc
    ORDER BY perm_count DESC
    """

    # Object-level permissions granted to public (current DB)
    PUBLIC_OBJECT_PERMISSIONS = """
    SELECT
        p.class_desc AS object_class,
        s.name AS schema_name,
        o.name AS object_name,
        p.permission_name,
        p.state_desc AS permission_state
    FROM sys.database_permissions p
    LEFT JOIN sys.objects o
        ON p.major_id = o.object_id
       AND p.class_desc = 'OBJECT_OR_COLUMN'
    LEFT JOIN sys.schemas s
        ON o.schema_id = s.schema_id
    WHERE p.grantee_principal_id = DATABASE_PRINCIPAL_ID('public')
      AND p.state IN ('G', 'W')
      AND (
        p.class_desc = 'SCHEMA'
        OR (p.class_desc = 'OBJECT_OR_COLUMN' AND o.type IN ('P', 'V', 'U', 'FN', 'IF', 'TF'))
      )
    ORDER BY p.class_desc, schema_name, object_name, p.permission_name
    """

    # Schema CONTROL/ALTER grants to non-dbo principals (current DB)
    SCHEMA_CONTROL_GRANTS = """
    SELECT
        s.name AS schema_name,
        dp.name AS principal_name,
        dp.type_desc AS principal_type,
        p.permission_name,
        p.state_desc AS permission_state
    FROM sys.database_permissions p
    JOIN sys.schemas s
        ON p.major_id = s.schema_id
       AND p.class_desc = 'SCHEMA'
    JOIN sys.database_principals dp
        ON p.grantee_principal_id = dp.principal_id
    WHERE p.state IN ('G', 'W')
      AND p.permission_name IN ('CONTROL', 'ALTER', 'TAKE OWNERSHIP')
      AND dp.name NOT IN ('dbo')
    ORDER BY s.name, dp.name
    """

    # Server-level impersonate grants (IMPERSONATE on LOGIN)
    IMPERSONATE_LOGIN_GRANTS = """
    SELECT
        grantee.name AS grantee_name,
        grantee.type_desc AS grantee_type,
        target.name AS target_login,
        pe.state_desc AS permission_state
    FROM sys.server_permissions pe
    JOIN sys.server_principals grantee
        ON pe.grantee_principal_id = grantee.principal_id
    JOIN sys.server_principals target
        ON pe.major_id = target.principal_id
    WHERE pe.permission_name = 'IMPERSONATE'
      AND pe.class_desc = 'LOGIN'
      AND pe.state IN ('G', 'W')
      AND grantee.name NOT LIKE '##%'
      AND grantee.name NOT LIKE 'NT %'
      AND grantee.name <> 'sa'
    ORDER BY grantee.name, target.name
    """

    # Database-level impersonate grants (IMPERSONATE on USER) - current DB
    IMPERSONATE_USER_GRANTS = """
    SELECT
        grantee.name AS grantee_name,
        grantee.type_desc AS grantee_type,
        target.name AS target_user,
        pe.state_desc AS permission_state
    FROM sys.database_permissions pe
    JOIN sys.database_principals grantee
        ON pe.grantee_principal_id = grantee.principal_id
    JOIN sys.database_principals target
        ON pe.major_id = target.principal_id
    WHERE pe.permission_name = 'IMPERSONATE'
      AND pe.class_desc IN ('USER', 'DATABASE_PRINCIPAL')
      AND pe.state IN ('G', 'W')
      AND grantee.name NOT IN ('dbo', 'guest', 'public')
    ORDER BY grantee.name, target.name
    """

    # Modules using EXECUTE AS (stored procedures/functions) - current DB
    EXECUTE_AS_MODULES = """
    SELECT
        s.name AS schema_name,
        o.name AS object_name,
        o.type_desc,
        dp.name AS execute_as_principal
    FROM sys.sql_modules m
    JOIN sys.objects o
        ON m.object_id = o.object_id
    JOIN sys.schemas s
        ON o.schema_id = s.schema_id
    LEFT JOIN sys.database_principals dp
        ON m.execute_as_principal_id = dp.principal_id
    WHERE m.execute_as_principal_id IS NOT NULL
      AND o.type IN ('P', 'FN', 'IF', 'TF')
    ORDER BY s.name, o.name
    """

    # Public EXECUTE on EXECUTE AS modules (current DB)
    PUBLIC_EXECUTE_ON_EXECUTE_AS = """
    SELECT
        s.name AS schema_name,
        o.name AS object_name,
        dp.name AS execute_as_principal,
        p.state_desc AS permission_state
    FROM sys.database_permissions p
    JOIN sys.objects o
        ON p.major_id = o.object_id
       AND p.class_desc = 'OBJECT_OR_COLUMN'
    JOIN sys.schemas s
        ON o.schema_id = s.schema_id
    JOIN sys.sql_modules m
        ON m.object_id = o.object_id
       AND m.execute_as_principal_id IS NOT NULL
    LEFT JOIN sys.database_principals dp
        ON m.execute_as_principal_id = dp.principal_id
    WHERE p.grantee_principal_id = DATABASE_PRINCIPAL_ID('public')
      AND p.permission_name = 'EXECUTE'
      AND p.state IN ('G', 'W')
    ORDER BY s.name, o.name
    """

    # Current database TRUSTWORTHY + chaining flags
    CURRENT_DB_FLAGS = """
    SELECT
        d.name AS database_name,
        d.is_trustworthy_on,
        d.is_db_chaining_on,
        SUSER_SNAME(d.owner_sid) AS owner_name
    FROM sys.databases d
    WHERE d.name = DB_NAME()
    """

    # Server audit specifications (overview)
    SERVER_AUDIT_SPECS = """
    SELECT
        sas.name AS spec_name,
        sas.is_state_enabled,
        sa.name AS audit_name
    FROM sys.server_audit_specifications sas
    LEFT JOIN sys.server_audits sa
        ON sas.audit_guid = sa.audit_guid
    ORDER BY sas.name
    """

    # Server audit actions (what is being audited)
    SERVER_AUDIT_ACTIONS = """
    SELECT
        sas.name AS spec_name,
        sad.audit_action_name,
        sad.audit_action_id,
        sad.class_desc
    FROM sys.server_audit_specification_details sad
    JOIN sys.server_audit_specifications sas
        ON sad.server_specification_id = sas.server_specification_id
    WHERE sas.is_state_enabled = 1
    ORDER BY sas.name, sad.audit_action_name
    """

    # Database audit specifications (current DB)
    DB_AUDIT_SPECS = """
    SELECT
        das.name AS spec_name,
        das.is_state_enabled
    FROM sys.database_audit_specifications das
    ORDER BY das.name
    """

    # Database audit actions (current DB)
    DB_AUDIT_ACTIONS = """
    SELECT
        das.name AS spec_name,
        dad.audit_action_name,
        dad.class_desc
    FROM sys.database_audit_specification_details dad
    JOIN sys.database_audit_specifications das
        ON dad.database_specification_id = das.database_specification_id
    WHERE das.is_state_enabled = 1
    ORDER BY das.name, dad.audit_action_name
    """

    # Login auditing level (best-effort via registry)
    LOGIN_AUDIT_LEVEL = """
    DECLARE @audit_level INT;
    EXEC master..xp_instance_regread
        N'HKEY_LOCAL_MACHINE',
        N'SOFTWARE\\Microsoft\\Microsoft SQL Server\\MSSQLServer\\MSSQLServer',
        N'AuditLevel',
        @audit_level OUTPUT;
    SELECT @audit_level AS audit_level;
    """

    # Default trace status
    DEFAULT_TRACE_ENABLED = """
    SELECT
        CAST(value_in_use AS int) AS default_trace_enabled
    FROM sys.configurations
    WHERE name = 'default trace enabled'
    """

    # Default trace settings (if enabled)
    DEFAULT_TRACE_INFO = """
    SELECT
        path,
        max_size,
        is_rollover
    FROM sys.traces
    WHERE is_default = 1
    """

    # TDE status for all databases (requires access to dm_database_encryption_keys)
    TDE_STATUS = """
    SELECT
        d.name AS database_name,
        CASE WHEN dek.database_id IS NULL THEN 0 ELSE 1 END AS has_tde_metadata,
        dek.encryption_state,
        dek.encryptor_type
    FROM sys.databases d
    LEFT JOIN sys.dm_database_encryption_keys dek
        ON d.database_id = dek.database_id
    WHERE d.name NOT IN ('tempdb')
    ORDER BY d.name
    """

    # Always Encrypted usage (current DB)
    ALWAYS_ENCRYPTED_KEYS = """
    SELECT
        (SELECT COUNT(*) FROM sys.column_master_keys) AS cmk_count,
        (SELECT COUNT(*) FROM sys.column_encryption_keys) AS cek_count
    """

    # Backup encryption summary for last 30 days (best-effort; returns empty if columns missing)
    BACKUP_ENCRYPTION_SUMMARY = """
    IF COL_LENGTH('msdb..backupset', 'encryptor_type') IS NULL
    BEGIN
        SELECT CAST(NULL AS sysname) AS database_name, CAST(NULL AS int) AS total_backups, CAST(NULL AS int) AS encrypted_backups
        WHERE 1 = 0;
        RETURN;
    END

    SELECT
        database_name,
        COUNT(*) AS total_backups,
        SUM(CASE WHEN encryptor_type IS NULL THEN 0 ELSE 1 END) AS encrypted_backups
    FROM msdb.dbo.backupset
    WHERE backup_start_date >= DATEADD(day, -30, GETDATE())
      AND type IN ('D', 'I', 'L')
    GROUP BY database_name
    ORDER BY database_name
    """

    # Who can execute external scripts (R/ML Services)
    EXTERNAL_SCRIPT_PERMISSIONS = """
    SELECT
        pr.name AS principal_name,
        pr.type_desc AS principal_type,
        pe.permission_name,
        pe.state_desc AS permission_state
    FROM sys.server_permissions pe
    JOIN sys.server_principals pr ON pe.grantee_principal_id = pr.principal_id
    WHERE pe.state IN ('G', 'W')
      AND pe.permission_name = 'EXECUTE ANY EXTERNAL SCRIPT'
      AND pr.name NOT LIKE '##%'
      AND pr.name NOT LIKE 'NT %'
    ORDER BY pr.name
    """

    # Potentially unsafe CLR assemblies (current database)
    CLR_UNSAFE_ASSEMBLIES = """
    SELECT
        name AS assembly_name,
        permission_set_desc
    FROM sys.assemblies
    WHERE is_user_defined = 1
      AND permission_set_desc IN ('UNSAFE', 'EXTERNAL_ACCESS')
    ORDER BY name
    """

    # Endpoints (overview)
    ENDPOINTS = """
    SELECT
        e.endpoint_id,
        e.name AS endpoint_name,
        e.type_desc,
        e.state_desc,
        e.is_admin_endpoint
    FROM sys.endpoints e
    ORDER BY e.type_desc, e.name
    """

    # Endpoint CONNECT permissions (who can connect)
    ENDPOINT_CONNECT_PERMISSIONS = """
    SELECT
        e.name AS endpoint_name,
        e.type_desc,
        pr.name AS principal_name,
        pr.type_desc AS principal_type,
        pe.state_desc AS permission_state
    FROM sys.server_permissions pe
    JOIN sys.endpoints e
        ON pe.major_id = e.endpoint_id
       AND pe.class_desc = 'ENDPOINT'
       AND pe.permission_name = 'CONNECT'
    JOIN sys.server_principals pr
        ON pe.grantee_principal_id = pr.principal_id
    WHERE pe.state IN ('G', 'W')
    ORDER BY e.name, pr.name
    """

    # Force Encryption (best-effort; reads registry via xp_instance_regread)
    FORCE_ENCRYPTION = """
    DECLARE @force_encryption INT;
    EXEC master..xp_instance_regread
        N'HKEY_LOCAL_MACHINE',
        N'SOFTWARE\\Microsoft\\Microsoft SQL Server\\MSSQLServer\\SuperSocketNetLib',
        N'ForceEncryption',
        @force_encryption OUTPUT;
    SELECT @force_encryption AS force_encryption;
    """

    # Linked Servers (overview)
    LINKED_SERVERS = """
    SELECT
        name AS linked_server,
        product,
        provider,
        data_source,
        is_data_access_enabled,
        is_rpc_enabled,
        is_rpc_out_enabled
    FROM sys.servers
    WHERE is_linked = 1
      AND name NOT LIKE '##%'
    ORDER BY name
    """

    # Linked Server login mappings
    LINKED_SERVER_LOGINS = """
    SELECT
        s.name AS linked_server,
        COALESCE(sp.name, '<All Logins>') AS local_principal,
        ll.uses_self_credential,
        ll.remote_name
    FROM sys.linked_logins ll
    JOIN sys.servers s
        ON ll.server_id = s.server_id
    LEFT JOIN sys.server_principals sp
        ON ll.local_principal_id = sp.principal_id
    WHERE s.is_linked = 1
    ORDER BY s.name, local_principal
    """

    # SQL Agent job steps (CmdExec/PowerShell + proxy)
    AGENT_RISKY_JOB_STEPS = """
    SELECT
        j.name AS job_name,
        SUSER_SNAME(j.owner_sid) AS owner_name,
        CASE WHEN sa.principal_id IS NOT NULL THEN 1 ELSE 0 END AS owner_is_sysadmin,
        js.step_id,
        js.step_name,
        js.subsystem,
        js.proxy_id,
        CASE WHEN js.proxy_id = 0 THEN 'SQL Agent Service Account' ELSE p.name END AS run_as
    FROM msdb.dbo.sysjobs j
    JOIN msdb.dbo.sysjobsteps js
        ON j.job_id = js.job_id
    LEFT JOIN msdb.dbo.sysproxies p
        ON js.proxy_id = p.proxy_id
    LEFT JOIN sys.server_principals sp
        ON j.owner_sid = sp.sid
    LEFT JOIN sys.server_role_members srm
        ON srm.member_principal_id = sp.principal_id
    LEFT JOIN sys.server_principals sa
        ON srm.role_principal_id = sa.principal_id
       AND sa.name = 'sysadmin'
    WHERE js.subsystem IN ('CmdExec', 'PowerShell')
    ORDER BY j.name, js.step_id
    """
    
    # ══════════════════════════════════════════════════════════════════════
    # DATABASE-LEVEL SECURITY
    # ══════════════════════════════════════════════════════════════════════
    
    # Database Users
    DATABASE_USERS = """
    SELECT 
        dp.name AS user_name,
        dp.type_desc AS user_type,
        dp.authentication_type_desc,
        dp.default_schema_name,
        dp.create_date,
        dp.modify_date,
        sp.name AS login_name,
        sp.is_disabled AS login_disabled
    FROM sys.database_principals dp
    LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid
    WHERE dp.type IN ('S', 'U', 'G', 'E', 'X')
      AND dp.name NOT IN ('dbo', 'guest', 'INFORMATION_SCHEMA', 'sys')
      AND dp.name NOT LIKE '##%'
    ORDER BY dp.name
    """
    
    # Database Role Members
    DATABASE_ROLE_MEMBERS = """
    SELECT 
        r.name AS role_name,
        m.name AS member_name,
        m.type_desc AS member_type
    FROM sys.database_role_members rm
    JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
    JOIN sys.database_principals m ON rm.member_principal_id = m.principal_id
    WHERE r.type = 'R'
      AND r.name NOT IN ('public')
    ORDER BY r.name, m.name
    """
    
    # db_owner Members (High Risk)
    DB_OWNER_MEMBERS = """
    SELECT 
        DB_NAME() AS database_name,
        m.name AS user_name,
        m.type_desc AS user_type
    FROM sys.database_role_members rm
    JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
    JOIN sys.database_principals m ON rm.member_principal_id = m.principal_id
    WHERE r.name = 'db_owner'
      AND m.name NOT IN ('dbo')
    ORDER BY m.name
    """
    
    # Orphaned Users
    ORPHANED_USERS = """
    SELECT 
        dp.name AS user_name,
        dp.type_desc AS user_type,
        dp.create_date
    FROM sys.database_principals dp
    LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid
    WHERE dp.type IN ('S', 'U')
      AND sp.sid IS NULL
      AND dp.name NOT IN ('dbo', 'guest', 'INFORMATION_SCHEMA', 'sys')
      AND dp.authentication_type_desc = 'INSTANCE'
    ORDER BY dp.name
    """
    
    # Explicit Permissions
    DATABASE_PERMISSIONS = """
    SELECT 
        pr.name AS principal_name,
        pr.type_desc AS principal_type,
        pe.class_desc AS object_class,
        OBJECT_NAME(pe.major_id) AS object_name,
        pe.permission_name,
        pe.state_desc AS permission_state
    FROM sys.database_permissions pe
    JOIN sys.database_principals pr ON pe.grantee_principal_id = pr.principal_id
    WHERE pe.state IN ('G', 'W')
      AND pr.name NOT IN ('dbo', 'guest', 'public')
      AND pr.name NOT LIKE '##%'
    ORDER BY pr.name, pe.permission_name
    """
    
    # ══════════════════════════════════════════════════════════════════════
    # SECURITY ISSUES
    # ══════════════════════════════════════════════════════════════════════
    
    # Guest Access Enabled
    GUEST_ACCESS = """
    SELECT 
        DB_NAME() AS database_name,
        CASE WHEN EXISTS (
            SELECT 1 FROM sys.database_permissions
            WHERE grantee_principal_id = DATABASE_PRINCIPAL_ID('guest')
            AND permission_name = 'CONNECT'
            AND state = 'G'
        ) THEN 1 ELSE 0 END AS guest_has_connect
    """
    
    # Public Role Permissions (should be minimal)
    PUBLIC_PERMISSIONS = """
    SELECT 
        pe.class_desc AS object_class,
        OBJECT_NAME(pe.major_id) AS object_name,
        pe.permission_name,
        pe.state_desc
    FROM sys.database_permissions pe
    WHERE pe.grantee_principal_id = DATABASE_PRINCIPAL_ID('public')
      AND pe.permission_name NOT IN ('CONNECT')
      AND pe.class_desc <> 'DATABASE'
    ORDER BY pe.permission_name
    """
    
    # SQL Logins with Empty Password
    EMPTY_PASSWORDS = """
    SELECT 
        name AS login_name,
        type_desc,
        create_date,
        is_disabled
    FROM sys.sql_logins
    WHERE PWDCOMPARE('', password_hash) = 1
      AND is_disabled = 0
    """
    
    # SQL Logins with Weak Passwords (common passwords)
    WEAK_PASSWORDS = """
    SELECT name AS login_name
    FROM sys.sql_logins
    WHERE is_disabled = 0
      AND (
        PWDCOMPARE(name, password_hash) = 1 OR
        PWDCOMPARE(REVERSE(name), password_hash) = 1 OR
        PWDCOMPARE('password', password_hash) = 1 OR
        PWDCOMPARE('Password1', password_hash) = 1 OR
        PWDCOMPARE('123456', password_hash) = 1 OR
        PWDCOMPARE('admin', password_hash) = 1 OR
        PWDCOMPARE('sa', password_hash) = 1
      )
    """

    # SQL Logins with Weak Password Policy Settings
    PASSWORD_POLICY = """
    SELECT
        name AS login_name,
        is_policy_checked,
        is_expiration_checked
    FROM sys.sql_logins
    WHERE is_disabled = 0
      AND (is_policy_checked = 0 OR is_expiration_checked = 0)
    """
    
    # Cross-Database Ownership Chaining
    CROSS_DB_CHAINING = """
    SELECT 
        name AS database_name,
        is_db_chaining_on
    FROM sys.databases
    WHERE is_db_chaining_on = 1
      AND name NOT IN ('master', 'tempdb', 'model', 'msdb')
    """
    
    # Trustworthy Databases
    TRUSTWORTHY_DBS = """
    SELECT 
        name AS database_name,
        is_trustworthy_on,
        SUSER_SNAME(owner_sid) AS owner
    FROM sys.databases
    WHERE is_trustworthy_on = 1
      AND name NOT IN ('msdb')
    """

    # Databases with Non-Standard Owners
    NON_DBO_OWNERS = """
    SELECT
        name AS database_name,
        SUSER_SNAME(owner_sid) AS owner_name
    FROM sys.databases
    WHERE name NOT IN ('master', 'model', 'msdb', 'tempdb')
      AND ISNULL(SUSER_SNAME(owner_sid), '') NOT IN ('sa', 'dbo')
    """

    # Risky Extended Stored Procedure Permissions
    RISKY_XP_PERMISSIONS = """
    SELECT
        o.name AS proc_name,
        dp.name AS grantee_name,
        dp.type_desc AS grantee_type,
        perm.state_desc
    FROM master.sys.objects o
    JOIN master.sys.database_permissions perm
        ON perm.major_id = o.object_id
       AND perm.class = 1
       AND perm.permission_name = 'EXECUTE'
       AND perm.state IN ('G', 'W')
    JOIN master.sys.database_principals dp
        ON perm.grantee_principal_id = dp.principal_id
    LEFT JOIN sys.server_principals sp
        ON dp.sid = sp.sid
    LEFT JOIN sys.server_role_members srm
        ON srm.member_principal_id = sp.principal_id
    LEFT JOIN sys.server_principals sr
        ON srm.role_principal_id = sr.principal_id
       AND sr.name = 'sysadmin'
    WHERE o.name IN ('xp_cmdshell', 'xp_regread', 'xp_regwrite', 'xp_dirtree', 'xp_fileexist')
      AND dp.name NOT IN ('dbo')
      AND sr.name IS NULL
    """

    # SQL Server Agent Jobs (owners and execution context)
    AGENT_JOBS = """
    SELECT
        j.name AS job_name,
        SUSER_SNAME(j.owner_sid) AS owner_name,
        CASE WHEN sa.principal_id IS NOT NULL THEN 1 ELSE 0 END AS owner_is_sysadmin,
        CASE WHEN js.proxy_id = 0 THEN 'SQL Agent Service Account' ELSE p.name END AS run_as
    FROM msdb.dbo.sysjobs j
    LEFT JOIN msdb.dbo.sysjobsteps js
        ON j.job_id = js.job_id
       AND js.step_id = 1
    LEFT JOIN msdb.dbo.sysproxies p
        ON js.proxy_id = p.proxy_id
    LEFT JOIN sys.server_principals sp
        ON j.owner_sid = sp.sid
    LEFT JOIN sys.server_role_members srm
        ON srm.member_principal_id = sp.principal_id
    LEFT JOIN sys.server_principals sa
        ON srm.role_principal_id = sa.principal_id
       AND sa.name = 'sysadmin'
    ORDER BY j.name
    """

    # SQL Server Version / Patch Level
    SERVER_VERSION = """
    SELECT
        CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(128)) AS product_version,
        CAST(SERVERPROPERTY('ProductLevel') AS nvarchar(128)) AS product_level,
        CAST(SERVERPROPERTY('ProductUpdateLevel') AS nvarchar(128)) AS update_level,
        CAST(SERVERPROPERTY('ProductUpdateReference') AS nvarchar(128)) AS update_reference,
        CAST(SERVERPROPERTY('Edition') AS nvarchar(128)) AS edition
    """

    # Unused/Inactive Logins (last login older than 90 days or never)
    UNUSED_LOGINS = """
    SELECT
        sp.name AS login_name,
        sp.type_desc AS login_type,
        sl.lastlogin AS last_login
    FROM sys.server_principals sp
    LEFT JOIN sys.syslogins sl
        ON sp.sid = sl.sid
    WHERE sp.type IN ('S', 'U', 'G')
      AND sp.name NOT LIKE '##%'
      AND sp.name NOT LIKE 'NT %'
      AND sp.is_disabled = 0
      AND (sl.lastlogin IS NULL OR sl.lastlogin < DATEADD(day, -90, GETDATE()))
    ORDER BY sl.lastlogin
    """

    # Unused/Inactive Logins (template; format with an integer days threshold)
    UNUSED_LOGINS_WITH_THRESHOLD = """
    SELECT
        sp.name AS login_name,
        sp.type_desc AS login_type,
        sl.lastlogin AS last_login
    FROM sys.server_principals sp
    LEFT JOIN sys.syslogins sl
        ON sp.sid = sl.sid
    WHERE sp.type IN ('S', 'U', 'G')
      AND sp.name NOT LIKE '##%'
      AND sp.name NOT LIKE 'NT %'
      AND sp.is_disabled = 0
      AND (sl.lastlogin IS NULL OR sl.lastlogin < DATEADD(day, -{days}, GETDATE()))
    ORDER BY sl.lastlogin
    """

    # Login -> DB user mapping counts across user databases (best-effort)
    LOGIN_DB_USER_MAP_COUNTS = """
    CREATE TABLE #login_map (
        login_name sysname NOT NULL,
        database_name sysname NOT NULL,
        user_name sysname NOT NULL
    );

    DECLARE @db sysname;
    DECLARE cur CURSOR FAST_FORWARD FOR
        SELECT name
        FROM sys.databases
        WHERE name NOT IN ('master', 'model', 'msdb', 'tempdb')
          AND state_desc = 'ONLINE';

    OPEN cur;
    FETCH NEXT FROM cur INTO @db;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        DECLARE @sql nvarchar(max) =
            N'INSERT INTO #login_map(login_name, database_name, user_name)
              SELECT
                  sp.name AS login_name,
                  ' + QUOTENAME(@db, '''') + N' AS database_name,
                  dp.name AS user_name
              FROM ' + QUOTENAME(@db) + N'.sys.database_principals dp
              JOIN sys.server_principals sp
                  ON dp.sid = sp.sid
              WHERE dp.type IN (''S'',''U'',''G'')
                AND dp.name NOT IN (''dbo'',''guest'',''INFORMATION_SCHEMA'',''sys'')
                AND sp.type IN (''S'',''U'',''G'')
                AND sp.is_disabled = 0
                AND sp.name NOT LIKE ''##%''
                AND sp.name NOT LIKE ''NT %'';';
        BEGIN TRY
            EXEC sys.sp_executesql @sql;
        END TRY
        BEGIN CATCH
            -- ignore databases we cannot access
        END CATCH;

        FETCH NEXT FROM cur INTO @db;
    END
    CLOSE cur;
    DEALLOCATE cur;

    SELECT
        login_name,
        COUNT(DISTINCT database_name) AS mapped_db_count,
        COUNT(*) AS mapped_user_count,
        MIN(database_name) AS sample_db
    FROM #login_map
    GROUP BY login_name
    ORDER BY mapped_db_count DESC, mapped_user_count DESC, login_name;

    DROP TABLE #login_map;
    """

    # Public role object/schema permission summary across user databases (best-effort)
    PUBLIC_PERMISSIONS_DB_SUMMARY = """
    CREATE TABLE #pub_perm (
        database_name sysname NOT NULL,
        perm_count int NOT NULL,
        select_count int NOT NULL,
        execute_count int NOT NULL,
        control_count int NOT NULL,
        other_count int NOT NULL
    );

    DECLARE @db sysname;
    DECLARE cur CURSOR FAST_FORWARD FOR
        SELECT name
        FROM sys.databases
        WHERE name NOT IN ('master', 'model', 'msdb', 'tempdb')
          AND state_desc = 'ONLINE';

    OPEN cur;
    FETCH NEXT FROM cur INTO @db;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        DECLARE @sql nvarchar(max) =
            N'INSERT INTO #pub_perm(database_name, perm_count, select_count, execute_count, control_count, other_count)
              SELECT
                  ' + QUOTENAME(@db, '''') + N' AS database_name,
                  COUNT(*) AS perm_count,
                  SUM(CASE WHEN p.permission_name IN (''SELECT'',''INSERT'',''UPDATE'',''DELETE'') THEN 1 ELSE 0 END) AS select_count,
                  SUM(CASE WHEN p.permission_name = ''EXECUTE'' THEN 1 ELSE 0 END) AS execute_count,
                  SUM(CASE WHEN p.permission_name IN (''CONTROL'',''ALTER'',''TAKE OWNERSHIP'') THEN 1 ELSE 0 END) AS control_count,
                  SUM(CASE WHEN p.permission_name NOT IN (''SELECT'',''INSERT'',''UPDATE'',''DELETE'',''EXECUTE'',''CONTROL'',''ALTER'',''TAKE OWNERSHIP'') THEN 1 ELSE 0 END) AS other_count
              FROM ' + QUOTENAME(@db) + N'.sys.database_permissions p
              WHERE p.grantee_principal_id = (
                    SELECT principal_id FROM ' + QUOTENAME(@db) + N'.sys.database_principals WHERE name = ''public''
                )
                AND p.state IN (''G'',''W'')
                AND p.class_desc IN (''OBJECT_OR_COLUMN'',''SCHEMA'');';
        BEGIN TRY
            EXEC sys.sp_executesql @sql;
        END TRY
        BEGIN CATCH
        END CATCH;

        FETCH NEXT FROM cur INTO @db;
    END
    CLOSE cur;
    DEALLOCATE cur;

    SELECT *
    FROM #pub_perm
    WHERE perm_count > 0
    ORDER BY perm_count DESC, database_name;

    DROP TABLE #pub_perm;
    """

    # Guest CONNECT summary across user databases + mapped login/user count (best-effort)
    GUEST_CONNECT_DB_SUMMARY = """
    CREATE TABLE #guest_db (
        database_name sysname NOT NULL,
        guest_has_connect bit NOT NULL,
        mapped_login_count int NOT NULL
    );

    DECLARE @db sysname;
    DECLARE cur CURSOR FAST_FORWARD FOR
        SELECT name
        FROM sys.databases
        WHERE name NOT IN ('master', 'model', 'msdb', 'tempdb')
          AND state_desc = 'ONLINE';

    OPEN cur;
    FETCH NEXT FROM cur INTO @db;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        DECLARE @sql nvarchar(max) =
            N'DECLARE @guest_connect bit = 0;
              SELECT @guest_connect =
                  CASE WHEN EXISTS (
                      SELECT 1
                      FROM ' + QUOTENAME(@db) + N'.sys.database_permissions
                      WHERE grantee_principal_id = (
                            SELECT principal_id FROM ' + QUOTENAME(@db) + N'.sys.database_principals WHERE name = ''guest''
                        )
                        AND permission_name = ''CONNECT''
                        AND state = ''G''
                  ) THEN 1 ELSE 0 END;

              DECLARE @mapped int = 0;
              SELECT @mapped = COUNT(*)
              FROM ' + QUOTENAME(@db) + N'.sys.database_principals dp
              JOIN sys.server_principals sp
                  ON dp.sid = sp.sid
              WHERE dp.type IN (''S'',''U'',''G'')
                AND dp.name NOT IN (''dbo'',''guest'',''INFORMATION_SCHEMA'',''sys'')
                AND sp.type IN (''S'',''U'',''G'')
                AND sp.is_disabled = 0;

              INSERT INTO #guest_db(database_name, guest_has_connect, mapped_login_count)
              VALUES (' + QUOTENAME(@db, '''') + N', @guest_connect, @mapped);';

        BEGIN TRY
            EXEC sys.sp_executesql @sql;
        END TRY
        BEGIN CATCH
        END CATCH;

        FETCH NEXT FROM cur INTO @db;
    END
    CLOSE cur;
    DEALLOCATE cur;

    SELECT *
    FROM #guest_db
    WHERE guest_has_connect = 1
    ORDER BY mapped_login_count DESC, database_name;

    DROP TABLE #guest_db;
    """

    # Custom Database Roles with High Privileges
    CUSTOM_ROLE_PRIVS = """
    SELECT
        r.name AS role_name,
        CASE WHEN ro.name = 'db_owner' THEN 1 ELSE 0 END AS is_db_owner_member,
        perm.permission_name
    FROM sys.database_principals r
    LEFT JOIN sys.database_role_members rm
        ON rm.member_principal_id = r.principal_id
    LEFT JOIN sys.database_principals ro
        ON rm.role_principal_id = ro.principal_id
       AND ro.name = 'db_owner'
    LEFT JOIN sys.database_permissions perm
        ON perm.grantee_principal_id = r.principal_id
       AND perm.class_desc = 'DATABASE'
       AND perm.permission_name IN (
            'CONTROL',
            'ALTER ANY DATABASE',
            'ALTER ANY ROLE',
            'ALTER ANY USER',
            'ALTER ANY SCHEMA',
            'ALTER ANY APPLICATION ROLE',
            'ALTER ANY ASSEMBLY',
            'IMPERSONATE'
        )
    WHERE r.type = 'R'
      AND r.is_fixed_role = 0
      AND (ro.name = 'db_owner' OR perm.permission_name IS NOT NULL)
    """
    
    # ══════════════════════════════════════════════════════════════════════
    # AUDIT & COMPLIANCE
    # ══════════════════════════════════════════════════════════════════════
    
    # Server Audit Status
    SERVER_AUDITS = """
    SELECT 
        name AS audit_name,
        status_desc,
        audit_file_path,
        max_file_size,
        max_rollover_files,
        is_state_enabled
    FROM sys.server_audits
    """
    
    # Failed Login Attempts (from error log)
    FAILED_LOGINS = """
    EXEC xp_readerrorlog 0, 1, N'Login failed'
    """
    
    # Security Summary
    SECURITY_SUMMARY = """
    SELECT 
        (SELECT COUNT(*) FROM sys.server_principals WHERE type = 'S' AND name NOT LIKE '##%') AS sql_logins,
        (SELECT COUNT(*) FROM sys.server_principals WHERE type IN ('U', 'G')) AS windows_logins,
        (SELECT COUNT(*) FROM sys.server_role_members rm
         JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
         WHERE r.name = 'sysadmin') AS sysadmin_count,
        (SELECT COUNT(*) FROM sys.server_principals WHERE is_disabled = 1) AS disabled_logins,
        (SELECT CASE WHEN is_disabled = 1 THEN 1 ELSE 0 END FROM sys.server_principals WHERE name = 'sa') AS sa_disabled
    """
    
    # Database Security Summary
    DB_SECURITY_SUMMARY = """
    SELECT
        DB_NAME() AS database_name,
        (SELECT COUNT(*) FROM sys.database_principals WHERE type IN ('S', 'U', 'G', 'E', 'X')
         AND name NOT IN ('dbo', 'guest', 'INFORMATION_SCHEMA', 'sys')) AS user_count,
        (SELECT COUNT(*) FROM sys.database_role_members rm
         JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
         WHERE r.name = 'db_owner' AND r.principal_id <> 1) AS db_owner_count,
        (SELECT COUNT(*) FROM sys.database_principals dp
         LEFT JOIN sys.server_principals sp ON dp.sid = sp.sid
         WHERE dp.type IN ('S', 'U') AND sp.sid IS NULL
         AND dp.authentication_type_desc = 'INSTANCE') AS orphaned_users
    """


def get_risk_color(risk: SecurityRisk) -> str:
    """Get color for risk level"""
    return RISK_COLORS.get(risk, RISK_COLORS[SecurityRisk.INFO])
