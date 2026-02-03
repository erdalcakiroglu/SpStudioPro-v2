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
    SecurityRisk.HIGH: "#EA580C",      # Orange-600
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
        LOGINPROPERTY(p.name, 'PasswordLastSetTime') AS password_last_set,
        LOGINPROPERTY(p.name, 'DaysUntilExpiration') AS days_until_expiration,
        LOGINPROPERTY(p.name, 'IsExpired') AS is_expired,
        LOGINPROPERTY(p.name, 'IsLocked') AS is_locked,
        LOGINPROPERTY(p.name, 'IsMustChange') AS must_change_password,
        LOGINPROPERTY(p.name, 'BadPasswordCount') AS bad_password_count,
        LOGINPROPERTY(p.name, 'BadPasswordTime') AS bad_password_time
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
