"""
Security Audit Service - SQL Server security analysis
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import os

from app.database.connection import get_connection_manager
from app.database.queries.security_queries import (
    SecurityQueries,
    SecurityRisk,
    get_risk_color,
)
from app.core.logger import get_logger

logger = get_logger('services.security')


@dataclass
class SecurityIssue:
    """Security issue/finding"""
    title: str
    description: str
    risk: SecurityRisk
    category: str
    details: List[str] = field(default_factory=list)
    recommendation: str = ""
    
    @property
    def risk_color(self) -> str:
        return get_risk_color(self.risk)


@dataclass
class Login:
    """SQL Server login"""
    name: str
    login_type: str
    is_disabled: bool = False
    create_date: Optional[datetime] = None
    default_database: str = ""
    is_expired: bool = False
    is_locked: bool = False
    password_last_set: Optional[datetime] = None
    bad_password_count: int = 0
    bad_password_time: Optional[datetime] = None


@dataclass
class DatabaseUser:
    """Database user"""
    name: str
    user_type: str
    login_name: str = ""
    default_schema: str = ""
    is_orphaned: bool = False


@dataclass
class RoleMember:
    """Role membership"""
    role_name: str
    member_name: str
    member_type: str


@dataclass
class SecuritySummary:
    """Security audit summary"""
    # Counts
    sql_logins: int = 0
    windows_logins: int = 0
    sysadmin_count: int = 0
    disabled_logins: int = 0
    sa_disabled: bool = False
    
    # Database level
    db_users: int = 0
    db_owner_count: int = 0
    orphaned_users: int = 0
    
    # Issues
    issues: List[SecurityIssue] = field(default_factory=list)
    
    # Lists
    logins: List[Login] = field(default_factory=list)
    sysadmins: List[str] = field(default_factory=list)
    db_owners: List[str] = field(default_factory=list)
    orphaned_user_list: List[str] = field(default_factory=list)
    
    # Timestamp
    collected_at: datetime = field(default_factory=datetime.now)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.risk == SecurityRisk.CRITICAL)
    
    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.risk == SecurityRisk.HIGH)
    
    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.risk == SecurityRisk.MEDIUM)
    
    @property
    def low_count(self) -> int:
        return sum(1 for i in self.issues if i.risk == SecurityRisk.LOW)


class SecurityService:
    """
    Service for Security Audit
    """
    
    _instance: Optional['SecurityService'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def connection(self):
        """Get active database connection"""
        conn_mgr = get_connection_manager()
        return conn_mgr.active_connection
    
    @property
    def is_connected(self) -> bool:
        """Check if connected"""
        conn = self.connection
        return conn is not None and conn.is_connected
    
    def run_security_audit(self) -> SecuritySummary:
        """Run comprehensive security audit"""
        summary = SecuritySummary()
        
        if not self.is_connected:
            logger.warning("No active connection for security audit")
            return summary
        
        conn = self.connection
        
        try:
            # Get server summary
            result = conn.execute_query(SecurityQueries.SECURITY_SUMMARY)
            if result:
                row = result[0]
                summary.sql_logins = row.get('sql_logins', 0) or 0
                summary.windows_logins = row.get('windows_logins', 0) or 0
                summary.sysadmin_count = row.get('sysadmin_count', 0) or 0
                summary.disabled_logins = row.get('disabled_logins', 0) or 0
                summary.sa_disabled = bool(row.get('sa_disabled', 0))
            
            # Get database summary
            db_result = conn.execute_query(SecurityQueries.DB_SECURITY_SUMMARY)
            if db_result:
                row = db_result[0]
                summary.db_users = row.get('user_count', 0) or 0
                summary.db_owner_count = row.get('db_owner_count', 0) or 0
                summary.orphaned_users = row.get('orphaned_users', 0) or 0
            
            # Get logins
            summary.logins = self._get_logins(conn)
            
            # Get sysadmins
            summary.sysadmins = self._get_sysadmins(conn)
            
            # Get db_owners
            summary.db_owners = self._get_db_owners(conn)
            
            # Get orphaned users
            summary.orphaned_user_list = self._get_orphaned_users(conn)
            
            # Run security checks
            summary.issues = self._run_security_checks(conn, summary)
            
            summary.collected_at = datetime.now()
            
        except Exception as e:
            logger.error(f"Error running security audit: {e}")
        
        return summary
    
    def _get_logins(self, conn) -> List[Login]:
        """Get all server logins"""
        logins = []
        try:
            result = conn.execute_query(SecurityQueries.SERVER_LOGINS)
            for row in result or []:
                logins.append(Login(
                    name=row.get('login_name', '') or '',
                    login_type=row.get('login_type', '') or '',
                    is_disabled=bool(row.get('is_disabled', 0)),
                    create_date=row.get('create_date'),
                    default_database=row.get('default_database_name', '') or '',
                    is_expired=bool(row.get('is_expired', 0)),
                    is_locked=bool(row.get('is_locked', 0)),
                    password_last_set=row.get('password_last_set'),
                    bad_password_count=row.get('bad_password_count', 0) or 0,
                    bad_password_time=row.get('bad_password_time'),
                ))
        except Exception as e:
            logger.warning(f"Error getting logins: {e}")
        return logins
    
    def _get_sysadmins(self, conn) -> List[str]:
        """Get sysadmin members"""
        sysadmins = []
        try:
            result = conn.execute_query(SecurityQueries.SYSADMIN_MEMBERS)
            for row in result or []:
                sysadmins.append(row.get('login_name', ''))
        except Exception as e:
            logger.warning(f"Error getting sysadmins: {e}")
        return sysadmins
    
    def _get_db_owners(self, conn) -> List[str]:
        """Get db_owner members"""
        owners = []
        try:
            result = conn.execute_query(SecurityQueries.DB_OWNER_MEMBERS)
            for row in result or []:
                owners.append(row.get('user_name', ''))
        except Exception as e:
            logger.warning(f"Error getting db_owners: {e}")
        return owners
    
    def _get_orphaned_users(self, conn) -> List[str]:
        """Get orphaned users"""
        users = []
        try:
            result = conn.execute_query(SecurityQueries.ORPHANED_USERS)
            for row in result or []:
                users.append(row.get('user_name', ''))
        except Exception as e:
            logger.warning(f"Error getting orphaned users: {e}")
        return users
    
    def _run_security_checks(self, conn, summary: SecuritySummary) -> List[SecurityIssue]:
        """Run all security checks"""
        issues = []
        
        # Check 1: SA account enabled
        if not summary.sa_disabled:
            issues.append(SecurityIssue(
                title="SA Account Enabled",
                description="The 'sa' account is enabled. This is a well-known account and a prime target for attacks.",
                risk=SecurityRisk.HIGH,
                category="Authentication",
                recommendation="Disable the 'sa' account and use named accounts instead."
            ))

        # Check 1.1: Critical server-level permissions granted (CONTROL SERVER / ALTER ANY*)
        try:
            result = conn.execute_query(SecurityQueries.CRITICAL_SERVER_PERMISSIONS)
            if result:
                rows = [
                    r for r in result
                    if (r.get("principal_name") or "").lower() != "sysadmin"
                    and not r.get("is_sysadmin_member", 0)
                ]
                if rows:
                    control = [r for r in rows if r.get("permission_name") == "CONTROL SERVER"]
                    alter_any = [r for r in rows if r.get("permission_name") != "CONTROL SERVER"]

                    if control:
                        details = [
                            f"{r.get('principal_name', '')} ({r.get('principal_type', '')}) [{r.get('permission_state', '')}]"
                            for r in control[:10]
                        ]
                        if len(control) > 10:
                            details.append(f"... (+{len(control) - 10} more)")
                        issues.append(SecurityIssue(
                            title="CONTROL SERVER Granted to Non-Sysadmin",
                            description=f"Found {len(control)} principal(s) with CONTROL SERVER outside sysadmin membership.",
                            risk=SecurityRisk.CRITICAL,
                            category="Server Permissions",
                            details=details,
                            recommendation="Remove CONTROL SERVER grants from non-admin principals and review server permissions."
                        ))

                    if alter_any:
                        details = [
                            f"{r.get('principal_name', '')}: {r.get('permission_name', '')} [{r.get('permission_state', '')}]"
                            for r in alter_any[:12]
                        ]
                        if len(alter_any) > 12:
                            details.append(f"... (+{len(alter_any) - 12} more)")
                        issues.append(SecurityIssue(
                            title="High-Risk Server Permissions Granted",
                            description=f"Found {len(alter_any)} ALTER ANY* permission grant(s) outside sysadmin membership.",
                            risk=SecurityRisk.HIGH,
                            category="Server Permissions",
                            details=details,
                            recommendation="Review and remove unnecessary ALTER ANY* server permissions."
                        ))
        except Exception as e:
            logger.debug(f"Critical server permission check failed: {e}")

        # Check 1.2 (P2/P3): Recon/wide-read server permissions
        try:
            result = conn.execute_query(SecurityQueries.RECON_SERVER_PERMISSIONS) or []
            rows = [r for r in result if not r.get("is_sysadmin_member", 0)]
            if rows:
                details = [
                    f"{r.get('principal_name', '')}: {r.get('permission_name', '')} [{r.get('permission_state', '')}]"
                    for r in rows[:12]
                ]
                if len(rows) > 12:
                    details.append(f"... (+{len(rows) - 12} more)")
                issues.append(SecurityIssue(
                    title="Wide-Read / Recon Server Permissions Granted",
                    description=f"Found {len(rows)} server permission grant(s) that enable broad recon (VIEW SERVER STATE / VIEW ANY DB / CONNECT ANY DB / IMPERSONATE ANY LOGIN).",
                    risk=SecurityRisk.MEDIUM,
                    category="Server Permissions",
                    details=details,
                    recommendation="Limit recon-style server permissions to administrators and monitoring accounts only."
                ))
        except Exception as e:
            logger.debug(f"Recon server permission check failed: {e}")
        
        # Check 2: Too many sysadmins
        if summary.sysadmin_count > 5:
            issues.append(SecurityIssue(
                title="Excessive Sysadmin Members",
                description=f"There are {summary.sysadmin_count} members in the sysadmin role.",
                risk=SecurityRisk.MEDIUM,
                category="Authorization",
                details=summary.sysadmins[:10],
                recommendation="Review and minimize sysadmin membership. Use role-based access."
            ))
        
        # Check 3: Orphaned users
        if summary.orphaned_users > 0:
            issues.append(SecurityIssue(
                title="Orphaned Database Users",
                description=f"Found {summary.orphaned_users} orphaned user(s) without a corresponding server login.",
                risk=SecurityRisk.MEDIUM,
                category="User Management",
                details=summary.orphaned_user_list[:10],
                recommendation="Remove orphaned users or map them to valid logins."
            ))
        
        # Check 4: Empty passwords
        try:
            result = conn.execute_query(SecurityQueries.EMPTY_PASSWORDS)
            if result:
                empty_pw_logins = [r.get('login_name', '') for r in result]
                issues.append(SecurityIssue(
                    title="Logins with Empty Passwords",
                    description=f"Found {len(result)} login(s) with empty passwords.",
                    risk=SecurityRisk.CRITICAL,
                    category="Authentication",
                    details=empty_pw_logins,
                    recommendation="Set strong passwords for all SQL logins."
                ))
        except Exception as e:
            logger.debug(f"Empty password check failed: {e}")
        
        # Check 5: Weak passwords
        try:
            result = conn.execute_query(SecurityQueries.WEAK_PASSWORDS)
            if result:
                weak_pw_logins = [r.get('login_name', '') for r in result]
                issues.append(SecurityIssue(
                    title="Logins with Weak Passwords",
                    description=f"Found {len(result)} login(s) with weak/common passwords.",
                    risk=SecurityRisk.CRITICAL,
                    category="Authentication",
                    details=weak_pw_logins,
                    recommendation="Enforce strong password policy."
                ))
        except Exception as e:
            logger.debug(f"Weak password check failed: {e}")

        # Check 6: Weak password policy settings
        try:
            result = conn.execute_query(SecurityQueries.PASSWORD_POLICY)
            if result:
                policy_off = [r.get('login_name', '') for r in result if not r.get('is_policy_checked', 0)]
                expiry_off = [r.get('login_name', '') for r in result if not r.get('is_expiration_checked', 0)]
                details = []
                if policy_off:
                    details.append("Policy OFF: " + ", ".join(policy_off[:5]) + (" ..." if len(policy_off) > 5 else ""))
                if expiry_off:
                    details.append("Expiration OFF: " + ", ".join(expiry_off[:5]) + (" ..." if len(expiry_off) > 5 else ""))
                issues.append(SecurityIssue(
                    title="Weak Password Policies",
                    description=f"Found {len(result)} SQL login(s) without password policy or expiration enforcement.",
                    risk=SecurityRisk.MEDIUM,
                    category="Authentication",
                    details=details,
                    recommendation="Enable CHECK_POLICY and CHECK_EXPIRATION for SQL logins."
                ))
        except Exception as e:
            logger.debug(f"Password policy check failed: {e}")

        # Check 6.1: Surface area / risky server configuration
        try:
            result = conn.execute_query(SecurityQueries.SURFACE_AREA_CONFIG)
            cfg = {r.get("config_name"): int(r.get("value_in_use", 0) or 0) for r in (result or [])}
            enabled = [k for k, v in cfg.items() if v == 1]
            if enabled:
                details = enabled[:12]
                if len(enabled) > 12:
                    details.append(f"... (+{len(enabled) - 12} more)")
                issues.append(SecurityIssue(
                    title="Risky Server Features Enabled",
                    description=f"Found {len(enabled)} surface area feature(s) enabled.",
                    risk=SecurityRisk.HIGH,
                    category="Surface Area",
                    details=details,
                    recommendation="Disable unused surface area features (xp_cmdshell, Ad Hoc Distributed Queries, Ole Automation, CLR, external scripts, mail) unless required."
                ))

            # CLR strict security and unsafe assemblies (current DB)
            if cfg.get("clr enabled", 0) == 1:
                if cfg.get("clr strict security", 1) == 0:
                    issues.append(SecurityIssue(
                        title="CLR Enabled Without Strict Security",
                        description="CLR is enabled and 'clr strict security' is OFF. This can allow unsafe assemblies or reduce safeguards.",
                        risk=SecurityRisk.HIGH,
                        category="Surface Area",
                        recommendation="Enable 'clr strict security' and review CLR usage."
                    ))
                try:
                    assemblies = conn.execute_query(SecurityQueries.CLR_UNSAFE_ASSEMBLIES) or []
                    if assemblies:
                        details = [
                            f"{r.get('assembly_name', '')} ({r.get('permission_set_desc', '')})"
                            for r in assemblies[:10]
                        ]
                        if len(assemblies) > 10:
                            details.append(f"... (+{len(assemblies) - 10} more)")
                        issues.append(SecurityIssue(
                            title="Potentially Unsafe CLR Assemblies",
                            description=f"Found {len(assemblies)} user-defined assembly(ies) with UNSAFE/EXTERNAL_ACCESS permission set in the current database.",
                            risk=SecurityRisk.HIGH,
                            category="Surface Area",
                            details=details,
                            recommendation="Review and remove unsafe/external-access assemblies unless strictly required."
                        ))
                except Exception as e:
                    logger.debug(f"CLR assembly check failed: {e}")

            # external scripts enabled -> who can execute
            if cfg.get("external scripts enabled", 0) == 1:
                try:
                    perms = conn.execute_query(SecurityQueries.EXTERNAL_SCRIPT_PERMISSIONS) or []
                    details = [
                        f"{r.get('principal_name', '')} ({r.get('principal_type', '')}) [{r.get('permission_state', '')}]"
                        for r in perms[:12]
                    ]
                    if len(perms) > 12:
                        details.append(f"... (+{len(perms) - 12} more)")
                    issues.append(SecurityIssue(
                        title="External Scripts Enabled",
                        description="R/ML external scripts are enabled. This increases attack surface and data exfiltration risk.",
                        risk=SecurityRisk.MEDIUM,
                        category="Surface Area",
                        details=details,
                        recommendation="Disable external scripts if not required; otherwise restrict 'EXECUTE ANY EXTERNAL SCRIPT' grants."
                    ))
                except Exception as e:
                    logger.debug(f"External script permissions check failed: {e}")
        except Exception as e:
            logger.debug(f"Surface area configuration check failed: {e}")

        # Check 7: Risky extended stored procedure permissions
        try:
            result = conn.execute_query(SecurityQueries.RISKY_XP_PERMISSIONS)
            if result:
                details = [
                    f"{r.get('proc_name', '')} → {r.get('grantee_name', '')}"
                    for r in result[:10]
                ]
                if len(result) > 10:
                    details.append(f"... (+{len(result) - 10} more)")
                issues.append(SecurityIssue(
                    title="Risky Extended Procedures Accessible",
                    description=f"Found {len(result)} EXECUTE grant(s) on risky extended procedures to non-sysadmin principals.",
                    risk=SecurityRisk.HIGH,
                    category="Execution",
                    details=details,
                    recommendation="Remove EXECUTE grants on xp_cmdshell/xp_regread/xp_regwrite for non-admins."
                ))
        except Exception as e:
            logger.debug(f"Risky procedure permission check failed: {e}")

        # Check 7.05 (P2/P3): Object & schema-level permission sprawl
        try:
            # Public object-level permissions
            pub = conn.execute_query(SecurityQueries.PUBLIC_OBJECT_PERMISSIONS) or []
            if pub:
                details = [
                    f"{r.get('permission_name', '')} on {r.get('schema_name', 'dbo')}.{r.get('object_name', '')} [{r.get('permission_state', '')}]"
                    for r in pub[:12]
                ]
                if len(pub) > 12:
                    details.append(f"... (+{len(pub) - 12} more)")
                issues.append(SecurityIssue(
                    title="Public Has Object/Schema Permissions",
                    description=f"Found {len(pub)} object/schema permission grant(s) to public in the current database.",
                    risk=SecurityRisk.MEDIUM,
                    category="Authorization",
                    details=details,
                    recommendation="Avoid granting object/schema permissions to public; grant to least-privilege roles instead."
                ))

            # Schema CONTROL/ALTER grants
            schema_grants = conn.execute_query(SecurityQueries.SCHEMA_CONTROL_GRANTS) or []
            if schema_grants:
                details = [
                    f"{r.get('schema_name', '')}: {r.get('principal_name', '')} → {r.get('permission_name', '')} [{r.get('permission_state', '')}]"
                    for r in schema_grants[:12]
                ]
                if len(schema_grants) > 12:
                    details.append(f"... (+{len(schema_grants) - 12} more)")
                issues.append(SecurityIssue(
                    title="Schema Control Granted",
                    description=f"Found {len(schema_grants)} schema-level CONTROL/ALTER/TAKE OWNERSHIP grant(s) to non-dbo principals.",
                    risk=SecurityRisk.HIGH,
                    category="Authorization",
                    details=details,
                    recommendation="Review schema-level grants and restrict CONTROL/ALTER to trusted deployment/admin roles."
                ))

            # Permission volume score (signals over-granting)
            counts = conn.execute_query(SecurityQueries.OBJECT_PERMISSION_COUNTS) or []
            noisy = [r for r in counts if int(r.get("perm_count", 0) or 0) >= 1000]
            if noisy:
                details = [
                    f"{r.get('principal_name', '')} ({r.get('principal_type', '')}): {r.get('perm_count', 0)} grants"
                    for r in noisy[:10]
                ]
                if len(noisy) > 10:
                    details.append(f"... (+{len(noisy) - 10} more)")
                issues.append(SecurityIssue(
                    title="High Object/Schema Permission Volume",
                    description=f"Found {len(noisy)} principal(s) with 1000+ object/schema permission grants in the current database (possible permission sprawl).",
                    risk=SecurityRisk.LOW,
                    category="Authorization",
                    details=details,
                    recommendation="Review broad roles and excessive grants; prefer role-based access and group grants."
                ))
        except Exception as e:
            logger.debug(f"Object-level permission sprawl check failed: {e}")

        # Check 7.06 (P2/P3): Impersonation & EXECUTE AS patterns
        try:
            imp_login = conn.execute_query(SecurityQueries.IMPERSONATE_LOGIN_GRANTS) or []
            if imp_login:
                details = [
                    f"{r.get('grantee_name', '')} → {r.get('target_login', '')} [{r.get('permission_state', '')}]"
                    for r in imp_login[:12]
                ]
                if len(imp_login) > 12:
                    details.append(f"... (+{len(imp_login) - 12} more)")
                issues.append(SecurityIssue(
                    title="IMPERSONATE LOGIN Grants",
                    description=f"Found {len(imp_login)} IMPERSONATE grant(s) on server logins. This can enable privilege escalation via EXECUTE AS LOGIN.",
                    risk=SecurityRisk.HIGH,
                    category="Authentication",
                    details=details,
                    recommendation="Remove unnecessary IMPERSONATE grants; restrict to tightly-controlled admin workflows."
                ))

            imp_user = conn.execute_query(SecurityQueries.IMPERSONATE_USER_GRANTS) or []
            if imp_user:
                details = [
                    f"{r.get('grantee_name', '')} → {r.get('target_user', '')} [{r.get('permission_state', '')}]"
                    for r in imp_user[:12]
                ]
                if len(imp_user) > 12:
                    details.append(f"... (+{len(imp_user) - 12} more)")
                issues.append(SecurityIssue(
                    title="IMPERSONATE USER Grants (DB)",
                    description=f"Found {len(imp_user)} IMPERSONATE grant(s) in the current database.",
                    risk=SecurityRisk.MEDIUM,
                    category="Authorization",
                    details=details,
                    recommendation="Review and remove unnecessary IMPERSONATE grants within the database."
                ))

            exec_as = conn.execute_query(SecurityQueries.EXECUTE_AS_MODULES) or []
            if exec_as:
                details = [
                    f"{r.get('schema_name', '')}.{r.get('object_name', '')} EXECUTE AS {r.get('execute_as_principal', '')}"
                    for r in exec_as[:10]
                ]
                if len(exec_as) > 10:
                    details.append(f"... (+{len(exec_as) - 10} more)")
                issues.append(SecurityIssue(
                    title="Modules Using EXECUTE AS",
                    description=f"Found {len(exec_as)} stored procedures/functions using EXECUTE AS (review for privilege escalation paths).",
                    risk=SecurityRisk.LOW,
                    category="Authorization",
                    details=details,
                    recommendation="Ensure EXECUTE AS modules are least-privilege and only trusted principals can EXECUTE them."
                ))

            pub_exec = conn.execute_query(SecurityQueries.PUBLIC_EXECUTE_ON_EXECUTE_AS) or []
            if pub_exec:
                details = [
                    f"{r.get('schema_name', '')}.{r.get('object_name', '')} EXECUTE AS {r.get('execute_as_principal', '')}"
                    for r in pub_exec[:12]
                ]
                if len(pub_exec) > 12:
                    details.append(f"... (+{len(pub_exec) - 12} more)")
                issues.append(SecurityIssue(
                    title="Public EXECUTE on EXECUTE AS Modules",
                    description=f"Found {len(pub_exec)} EXECUTE grant(s) to public on modules that use EXECUTE AS (high risk privilege-escalation pattern).",
                    risk=SecurityRisk.HIGH,
                    category="Authorization",
                    details=details,
                    recommendation="Revoke public EXECUTE on EXECUTE AS modules and restrict execution to trusted roles."
                ))
        except Exception as e:
            logger.debug(f"Impersonation/EXECUTE AS checks failed: {e}")

        # Check 7.1: Endpoint security (extra endpoints + CONNECT to public)
        try:
            endpoints = conn.execute_query(SecurityQueries.ENDPOINTS) or []
            extra = [
                e for e in endpoints
                if not e.get("is_admin_endpoint", 0)
                and (e.get("type_desc") or "").upper() not in ("TSQL",)
                and (e.get("state_desc") or "").upper() == "STARTED"
            ]
            if extra:
                details = [
                    f"{e.get('endpoint_name', '')} ({e.get('type_desc', '')}) [{e.get('state_desc', '')}]"
                    for e in extra[:10]
                ]
                if len(extra) > 10:
                    details.append(f"... (+{len(extra) - 10} more)")
                issues.append(SecurityIssue(
                    title="Extra Endpoints Enabled",
                    description=f"Found {len(extra)} non-TDS endpoint(s) started (e.g. Service Broker/Mirroring/HTTP).",
                    risk=SecurityRisk.MEDIUM,
                    category="Network/Endpoints",
                    details=details,
                    recommendation="Disable unused endpoints and restrict CONNECT permissions."
                ))

            perms = conn.execute_query(SecurityQueries.ENDPOINT_CONNECT_PERMISSIONS) or []
            public_connect = [
                p for p in perms
                if (p.get("principal_name") or "").lower() == "public"
                and (p.get("permission_state") or "").upper() in ("GRANT", "GRANT_WITH_GRANT_OPTION")
            ]
            if public_connect:
                details = [
                    f"{p.get('endpoint_name', '')} ({p.get('type_desc', '')})"
                    for p in public_connect[:12]
                ]
                if len(public_connect) > 12:
                    details.append(f"... (+{len(public_connect) - 12} more)")
                issues.append(SecurityIssue(
                    title="Public CONNECT on Endpoints",
                    description=f"Found {len(public_connect)} endpoint CONNECT grant(s) to public.",
                    risk=SecurityRisk.HIGH,
                    category="Network/Endpoints",
                    details=details,
                    recommendation="Revoke CONNECT on endpoints from public and grant only to required principals."
                ))

            # Best-effort: Force Encryption registry flag
            try:
                fe = conn.execute_query(SecurityQueries.FORCE_ENCRYPTION) or []
                if fe and int(fe[0].get("force_encryption", 0) or 0) == 0:
                    issues.append(SecurityIssue(
                        title="Force Encryption Disabled",
                        description="Force Encryption appears to be disabled for SQL Server network connections.",
                        risk=SecurityRisk.MEDIUM,
                        category="Network/Endpoints",
                        recommendation="Enable Force Encryption if supported by your certificate/OS configuration and client requirements."
                    ))
            except Exception as e:
                logger.debug(f"Force encryption check failed: {e}")
        except Exception as e:
            logger.debug(f"Endpoint security check failed: {e}")

        # Check 7.2: Linked server risks
        try:
            linked = conn.execute_query(SecurityQueries.LINKED_SERVERS) or []
            if linked:
                details = [
                    f"{s.get('linked_server', '')} (RPC OUT: {s.get('is_rpc_out_enabled', 0)}, DataAccess: {s.get('is_data_access_enabled', 0)})"
                    for s in linked[:10]
                ]
                if len(linked) > 10:
                    details.append(f"... (+{len(linked) - 10} more)")
                issues.append(SecurityIssue(
                    title="Linked Servers Present",
                    description=f"Found {len(linked)} linked server(s). Linked servers are a common data-exfiltration and privilege-escalation path.",
                    risk=SecurityRisk.MEDIUM,
                    category="Linked Servers",
                    details=details,
                    recommendation="Remove unused linked servers; restrict access and disable RPC OUT unless required."
                ))

                rpc_out = [s for s in linked if s.get("is_rpc_out_enabled", 0)]
                if rpc_out:
                    details = [s.get("linked_server", "") for s in rpc_out[:12]]
                    if len(rpc_out) > 12:
                        details.append(f"... (+{len(rpc_out) - 12} more)")
                    issues.append(SecurityIssue(
                        title="Linked Servers with RPC OUT Enabled",
                        description=f"Found {len(rpc_out)} linked server(s) with RPC OUT enabled.",
                        risk=SecurityRisk.HIGH,
                        category="Linked Servers",
                        details=details,
                        recommendation="Disable RPC OUT unless explicitly required; review remote procedure execution paths."
                    ))

                mappings = conn.execute_query(SecurityQueries.LINKED_SERVER_LOGINS) or []
                fixed_ctx = [
                    m for m in mappings
                    if not m.get("uses_self_credential", 0)
                    and m.get("remote_name")
                    and (m.get("local_principal") or "") == "<All Logins>"
                ]
                if fixed_ctx:
                    details = [
                        f"{m.get('linked_server', '')}: fixed remote login '{m.get('remote_name', '')}'"
                        for m in fixed_ctx[:10]
                    ]
                    if len(fixed_ctx) > 10:
                        details.append(f"... (+{len(fixed_ctx) - 10} more)")
                    issues.append(SecurityIssue(
                        title="Linked Server Uses Fixed High-Value Credentials",
                        description=f"Found {len(fixed_ctx)} linked server mapping(s) using a fixed remote security context for all logins.",
                        risk=SecurityRisk.HIGH,
                        category="Linked Servers",
                        details=details,
                        recommendation="Avoid fixed high-privilege remote credentials; use least-privilege mappings per login/role."
                    ))

                impersonate_all = [
                    m for m in mappings
                    if m.get("uses_self_credential", 0)
                    and (m.get("local_principal") or "") == "<All Logins>"
                ]
                if impersonate_all:
                    details = [m.get("linked_server", "") for m in impersonate_all[:12]]
                    if len(impersonate_all) > 12:
                        details.append(f"... (+{len(impersonate_all) - 12} more)")
                    issues.append(SecurityIssue(
                        title="Linked Server Impersonation for All Logins",
                        description=f"Found {len(impersonate_all)} linked server mapping(s) using 'self credential' for all logins.",
                        risk=SecurityRisk.MEDIUM,
                        category="Linked Servers",
                        details=details,
                        recommendation="Review linked server authentication and limit impersonation mappings."
                    ))
        except Exception as e:
            logger.debug(f"Linked server check failed: {e}")

        # Check 8: Non-standard database owners
        try:
            result = conn.execute_query(SecurityQueries.NON_DBO_OWNERS)
            if result:
                owners = [f"{r.get('database_name', '')} (owner: {r.get('owner_name', '')})" for r in result]
                issues.append(SecurityIssue(
                    title="Non-Standard Database Owners",
                    description=f"Found {len(result)} database(s) owned by accounts other than 'sa' or 'dbo'.",
                    risk=SecurityRisk.MEDIUM,
                    category="Authorization",
                    details=owners[:10],
                    recommendation="Review database owners and set to a standard owner (e.g., 'sa') if appropriate."
                ))
        except Exception as e:
            logger.debug(f"Database owner check failed: {e}")

        # Check 9: Custom roles with high privileges
        try:
            result = conn.execute_query(SecurityQueries.CUSTOM_ROLE_PRIVS)
            if result:
                role_map: Dict[str, Dict[str, Any]] = {}
                for row in result:
                    role = row.get('role_name', '') or ''
                    if not role:
                        continue
                    entry = role_map.setdefault(role, {"db_owner": False, "perms": set()})
                    if row.get('is_db_owner_member', 0):
                        entry["db_owner"] = True
                    perm = row.get('permission_name')
                    if perm:
                        entry["perms"].add(perm)

                details = []
                for role_name, info in role_map.items():
                    parts = []
                    if info["db_owner"]:
                        parts.append("db_owner member")
                    if info["perms"]:
                        parts.append("perms: " + ", ".join(sorted(info["perms"])))
                    details.append(f"{role_name} ({'; '.join(parts)})" if parts else role_name)

                issues.append(SecurityIssue(
                    title="Custom Roles with Excessive Privileges",
                    description=f"Found {len(role_map)} custom role(s) with db_owner membership or high database privileges.",
                    risk=SecurityRisk.HIGH,
                    category="Authorization",
                    details=details[:10],
                    recommendation="Review custom roles and remove unnecessary high privileges."
                ))
        except Exception as e:
            logger.debug(f"Custom role privilege check failed: {e}")

        # Check 10: SQL Server Agent jobs owned by non-sysadmin accounts
        try:
            result = conn.execute_query(SecurityQueries.AGENT_JOBS)
            if result:
                non_admin_jobs = [
                    r for r in result if not r.get('owner_is_sysadmin', 0)
                ]
                if non_admin_jobs:
                    details = [
                        f"{r.get('job_name', '')} (Owner: {r.get('owner_name', '')}, RunAs: {r.get('run_as', '')})"
                        for r in non_admin_jobs[:10]
                    ]
                    if len(non_admin_jobs) > 10:
                        details.append(f"... (+{len(non_admin_jobs) - 10} more)")
                    issues.append(SecurityIssue(
                        title="Agent Jobs Owned by Non-Sysadmin",
                        description=f"Found {len(non_admin_jobs)} SQL Agent job(s) owned by non-sysadmin accounts.",
                        risk=SecurityRisk.LOW,
                        category="Authorization",
                        details=details,
                        recommendation="Review job owners and execution context for least privilege."
                    ))
        except Exception as e:
            logger.debug(f"Agent jobs check failed: {e}")

        # Check 10.1: SQL Agent CmdExec/PowerShell steps + proxy (high risk combo)
        try:
            result = conn.execute_query(SecurityQueries.AGENT_RISKY_JOB_STEPS)
            if result:
                risky = [r for r in result if not r.get("owner_is_sysadmin", 0)]
                if risky:
                    details = [
                        f"{r.get('job_name', '')} / Step {r.get('step_id', '')}: {r.get('subsystem', '')} (RunAs: {r.get('run_as', '')})"
                        for r in risky[:10]
                    ]
                    if len(risky) > 10:
                        details.append(f"... (+{len(risky) - 10} more)")
                    issues.append(SecurityIssue(
                        title="Non-Sysadmin Owned CmdExec/PowerShell Jobs",
                        description=f"Found {len(risky)} job step(s) using CmdExec/PowerShell with non-sysadmin job owners.",
                        risk=SecurityRisk.HIGH,
                        category="SQL Agent",
                        details=details,
                        recommendation="Review job owners, step types, and proxy usage. Avoid OS-level step types for non-admin owners."
                    ))
        except Exception as e:
            logger.debug(f"Agent job step check failed: {e}")

        # Check 11: SQL Server version / patch level
        try:
            result = conn.execute_query(SecurityQueries.SERVER_VERSION)
            if result:
                row = result[0]
                update_level = (row.get('update_level') or '').strip()
                if not update_level:
                    details = [
                        f"Version: {row.get('product_version', '')}",
                        f"Level: {row.get('product_level', '')}",
                        f"Edition: {row.get('edition', '')}",
                    ]
                    issues.append(SecurityIssue(
                        title="Missing Cumulative Update Level",
                        description="SQL Server update level (CU/GDR) information is missing; instance may be unpatched.",
                        risk=SecurityRisk.MEDIUM,
                        category="Patch Management",
                        details=details,
                        recommendation="Verify the latest security/CU update and apply if necessary."
                    ))
        except Exception as e:
            logger.debug(f"Server version check failed: {e}")

        # Check 12: Unused/Inactive logins (enriched + parametrized)
        try:
            inactive_days_threshold = int(os.getenv("SQLPERFAI_SECURITY_INACTIVE_DAYS", "90"))
            inactive_days_threshold = max(30, min(inactive_days_threshold, 3650))

            query = SecurityQueries.UNUSED_LOGINS_WITH_THRESHOLD.format(days=inactive_days_threshold)
            result = conn.execute_query(query) or []
            if result:
                # Best-effort: map logins to DB user mappings across databases
                login_map: Dict[str, Dict[str, Any]] = {}
                try:
                    maps = conn.execute_query(SecurityQueries.LOGIN_DB_USER_MAP_COUNTS) or []
                    for r in maps:
                        login_name = (r.get("login_name") or "").strip()
                        if not login_name:
                            continue
                        login_map[login_name] = {
                            "mapped_db_count": int(r.get("mapped_db_count", 0) or 0),
                            "mapped_user_count": int(r.get("mapped_user_count", 0) or 0),
                            "sample_db": r.get("sample_db"),
                        }
                except Exception as e:
                    logger.debug(f"Login DB user mapping check failed: {e}")

                now = datetime.now()
                removable: List[str] = []
                review: List[str] = []
                never_used_mapped: List[str] = []

                for r in result:
                    login = (r.get("login_name") or "").strip()
                    if not login:
                        continue
                    last_login = r.get("last_login")
                    mapped_db_count = int(login_map.get(login, {}).get("mapped_db_count", 0) or 0)

                    if last_login:
                        try:
                            inactive_days = (now - last_login).days
                        except Exception:
                            inactive_days = inactive_days_threshold
                    else:
                        inactive_days = 99999  # never/unknown

                    if last_login is None and mapped_db_count > 0:
                        never_used_mapped.append(login)

                    if inactive_days >= 365 and mapped_db_count == 0:
                        removable.append(login)
                    if inactive_days >= 180 and mapped_db_count >= 2:
                        review.append(login)

                def _sample(items: List[str], max_items: int = 5) -> str:
                    if not items:
                        return ""
                    head = ", ".join(items[:max_items])
                    tail = f" (+{len(items) - max_items} more)" if len(items) > max_items else ""
                    return head + tail

                details = [
                    f"Threshold: {inactive_days_threshold}+ days (override: SQLPERFAI_SECURITY_INACTIVE_DAYS)",
                    f"Remove candidates (>=365d/never + no DB user maps): {len(removable)} [{_sample(removable)}]".rstrip(" []"),
                    f"Manual review (>=180d/never + mapped to 2+ DBs): {len(review)} [{_sample(review)}]".rstrip(" []"),
                    f"Never used but mapped to DB users: {len(never_used_mapped)} [{_sample(never_used_mapped)}]".rstrip(" []"),
                ]

                issues.append(SecurityIssue(
                    title="Inactive Logins",
                    description=(
                        f"Found {len(result)} login(s) inactive for {inactive_days_threshold}+ days or never used. "
                        f"Enriched with DB user mapping signals."
                    ),
                    risk=SecurityRisk.LOW,
                    category="User Management",
                    details=details,
                    recommendation="Disable unused accounts first; remove only after confirming no dependencies (apps, jobs, linked servers, service accounts)."
                ))
        except Exception as e:
            logger.debug(f"Unused login check failed: {e}")

        # Check 13: Trustworthy databases
        try:
            result = conn.execute_query(SecurityQueries.TRUSTWORTHY_DBS)
            if result:
                trustworthy_dbs = [r.get('database_name', '') for r in result]
                issues.append(SecurityIssue(
                    title="Trustworthy Databases",
                    description=f"Found {len(result)} database(s) with TRUSTWORTHY enabled.",
                    risk=SecurityRisk.HIGH,
                    category="Database Configuration",
                    details=trustworthy_dbs,
                    recommendation="Disable TRUSTWORTHY unless specifically required."
                ))
        except Exception as e:
            logger.debug(f"Trustworthy check failed: {e}")

        # Check 13.1 (P2/P3): TRUSTWORTHY + CLR + db_owner combination (current DB)
        try:
            flags = conn.execute_query(SecurityQueries.CURRENT_DB_FLAGS) or []
            if flags:
                f = flags[0]
                is_trustworthy = int(f.get("is_trustworthy_on", 0) or 0) == 1
                owner_name = (f.get("owner_name") or "").strip()
                if is_trustworthy:
                    cfg = conn.execute_query(SecurityQueries.SURFACE_AREA_CONFIG) or []
                    cfg_map = {r.get("config_name"): int(r.get("value_in_use", 0) or 0) for r in cfg}
                    clr_enabled = cfg_map.get("clr enabled", 0) == 1

                    non_sa_db_owner = any((u or "").lower() not in ("sa", "dbo") for u in (summary.db_owners or []))
                    if clr_enabled and non_sa_db_owner and owner_name.lower() not in ("sa", "dbo", ""):
                        issues.append(SecurityIssue(
                            title="High-Risk PrivEsc Pattern (TRUSTWORTHY + CLR + db_owner)",
                            description="Current database has TRUSTWORTHY ON, CLR enabled at server, and non-sa db_owner members, with a non-standard DB owner. This combination can enable privilege escalation.",
                            risk=SecurityRisk.CRITICAL,
                            category="Database Configuration",
                            details=[
                                f"DB: {f.get('database_name', '')}",
                                f"Owner: {owner_name or 'Unknown'}",
                                f"db_owner members (sample): {', '.join((summary.db_owners or [])[:5])}",
                            ],
                            recommendation="Disable TRUSTWORTHY where possible, review DB owner/db_owner membership, and restrict CLR usage."
                        ))
        except Exception as e:
            logger.debug(f"Trustworthy+CLR+db_owner combo check failed: {e}")
        
        # Check 14: Cross-database chaining
        try:
            result = conn.execute_query(SecurityQueries.CROSS_DB_CHAINING)
            if result:
                chaining_dbs = [r.get('database_name', '') for r in result]
                issues.append(SecurityIssue(
                    title="Cross-Database Ownership Chaining",
                    description=f"Found {len(result)} database(s) with cross-database chaining enabled.",
                    risk=SecurityRisk.MEDIUM,
                    category="Database Configuration",
                    details=chaining_dbs,
                    recommendation="Disable cross-database chaining unless required."
                ))
        except Exception as e:
            logger.debug(f"Chaining check failed: {e}")
        
        # Check 15: Guest access (prefer instance-wide summary; fallback to current DB)
        try:
            result = conn.execute_query(SecurityQueries.GUEST_CONNECT_DB_SUMMARY)
            if result:
                total_dbs = len(result)
                worst = max(result, key=lambda r: int(r.get("mapped_login_count", 0) or 0))
                details = [
                    f"{r.get('database_name', '')}: guest CONNECT (mapped logins: {r.get('mapped_login_count', 0)})"
                    for r in result[:10]
                ]
                if len(result) > 10:
                    details.append(f"... (+{len(result) - 10} more)")
                issues.append(SecurityIssue(
                    title="Guest Access Enabled",
                    description=(
                        f"Guest CONNECT permission is enabled in {total_dbs} database(s). "
                        f"Most exposed: {worst.get('database_name', '')} (mapped logins: {worst.get('mapped_login_count', 0)})."
                    ),
                    risk=SecurityRisk.MEDIUM,
                    category="Authorization",
                    details=details,
                    recommendation="Revoke CONNECT permission from guest user in user databases unless explicitly required."
                ))
            else:
                # Fallback: current DB only
                result = conn.execute_query(SecurityQueries.GUEST_ACCESS)
                if result and result[0].get('guest_has_connect', 0):
                    issues.append(SecurityIssue(
                        title="Guest Access Enabled",
                        description="The guest user has CONNECT permission in this database.",
                        risk=SecurityRisk.MEDIUM,
                        category="Authorization",
                        recommendation="Revoke CONNECT permission from guest user."
                    ))
        except Exception as e:
            logger.debug(f"Guest access check failed: {e}")
        
        # Check 16: Public role permissions (prefer instance-wide summary; fallback to current DB)
        try:
            rows = conn.execute_query(SecurityQueries.PUBLIC_PERMISSIONS_DB_SUMMARY) or []
            if rows:
                db_count = len(rows)
                total = sum(int(r.get("perm_count", 0) or 0) for r in rows)
                total_select = sum(int(r.get("select_count", 0) or 0) for r in rows)
                total_exec = sum(int(r.get("execute_count", 0) or 0) for r in rows)
                total_control = sum(int(r.get("control_count", 0) or 0) for r in rows)

                worst = max(rows, key=lambda r: int(r.get("perm_count", 0) or 0))
                details = [
                    (
                        f"{r.get('database_name', '')}: {r.get('perm_count', 0)} perms "
                        f"(DML: {r.get('select_count', 0)}, EXEC: {r.get('execute_count', 0)}, CONTROL/ALTER: {r.get('control_count', 0)})"
                    )
                    for r in rows[:10]
                ]
                if len(rows) > 10:
                    details.append(f"... (+{len(rows) - 10} more)")

                risk = SecurityRisk.HIGH if total_control > 0 else SecurityRisk.MEDIUM if total_exec > 0 else SecurityRisk.LOW
                issues.append(SecurityIssue(
                    title="Public Role Has Extra Permissions",
                    description=(
                        f"Across the instance, public has {total} object/schema permission grant(s) in {db_count} database(s). "
                        f"Most risky DB: {worst.get('database_name', '')} ({worst.get('perm_count', 0)} perms). "
                        f"Breakdown: DML={total_select}, EXEC={total_exec}, CONTROL/ALTER={total_control}."
                    ),
                    risk=risk,
                    category="Authorization",
                    details=details,
                    recommendation="Remove object/schema grants from public; grant to least-privilege roles/groups."
                ))
            else:
                result = conn.execute_query(SecurityQueries.PUBLIC_PERMISSIONS)
                if result:
                    perms = [f"{r.get('permission_name', '')} on {r.get('object_name', 'N/A')}" for r in result[:5]]
                    issues.append(SecurityIssue(
                        title="Public Role Has Extra Permissions",
                        description=f"The public role has {len(result)} non-default permission(s).",
                        risk=SecurityRisk.LOW,
                        category="Authorization",
                        details=perms,
                        recommendation="Review and minimize public role permissions."
                    ))
        except Exception as e:
            logger.debug(f"Public permissions check failed: {e}")
        
        # Check 17: Locked accounts (enrich with rate and recent signals)
        locked_logins = [l for l in summary.logins if l.is_locked]
        if locked_logins:
            total = max(1, len(summary.logins))
            locked_count = len(locked_logins)
            ratio = locked_count / total

            now = datetime.now()
            recent_24h = [
                l for l in locked_logins
                if l.bad_password_time and (now - l.bad_password_time).total_seconds() <= 24 * 3600
            ]

            details = []
            for l in locked_logins[:10]:
                last_bad = l.bad_password_time.isoformat(sep=" ", timespec="seconds") if l.bad_password_time else "Unknown"
                details.append(f"{l.name} (bad_pw_count: {l.bad_password_count}, last_bad_pw: {last_bad})")
            if len(locked_logins) > 10:
                details.append(f"... (+{len(locked_logins) - 10} more)")

            risk = SecurityRisk.MEDIUM if recent_24h else SecurityRisk.INFO
            issues.append(SecurityIssue(
                title="Locked Login Accounts",
                description=(
                    f"Found {locked_count} locked login account(s) ({ratio:.1%} of visible logins). "
                    f"Locked in last 24h (signal): {len(recent_24h)}."
                ),
                risk=risk,
                category="Authentication",
                details=details,
                recommendation=(
                    "Investigate lockout causes: possible brute-force attempts, incorrect application connection strings, "
                    "scheduler/job misconfiguration, or stale credentials in services."
                )
            ))

        # Check 18 (P2/P3): Monitoring & audit posture
        try:
            audits = conn.execute_query(SecurityQueries.SERVER_AUDITS) or []
            enabled_audits = [a for a in audits if a.get("is_state_enabled", 0)]
            if not enabled_audits:
                issues.append(SecurityIssue(
                    title="SQL Server Audit Not Enabled",
                    description="No enabled SQL Server Audit was found. This reduces visibility into security-relevant activity.",
                    risk=SecurityRisk.MEDIUM,
                    category="Monitoring & Audit",
                    recommendation="Configure SQL Server Audit and enable server/database audit specifications for key security events."
                ))

            specs = conn.execute_query(SecurityQueries.SERVER_AUDIT_SPECS) or []
            enabled_specs = [s for s in specs if s.get("is_state_enabled", 0)]
            if not enabled_specs:
                issues.append(SecurityIssue(
                    title="Server Audit Specifications Not Enabled",
                    description="No enabled server audit specification was found.",
                    risk=SecurityRisk.MEDIUM,
                    category="Monitoring & Audit",
                    recommendation="Enable server audit specifications for login changes, permission changes, and schema changes as appropriate."
                ))

            db_specs = conn.execute_query(SecurityQueries.DB_AUDIT_SPECS) or []
            enabled_db_specs = [s for s in db_specs if s.get("is_state_enabled", 0)]
            if not enabled_db_specs:
                issues.append(SecurityIssue(
                    title="Database Audit Specifications Not Enabled (Current DB)",
                    description="No enabled database audit specification was found for the current database.",
                    risk=SecurityRisk.LOW,
                    category="Monitoring & Audit",
                    recommendation="Consider enabling DB audit specifications for schema/permission changes in sensitive databases."
                ))

            # Login auditing level (registry)
            try:
                level_rows = conn.execute_query(SecurityQueries.LOGIN_AUDIT_LEVEL) or []
                if level_rows:
                    level = int(level_rows[0].get("audit_level", 0) or 0)
                    # Common meanings: 0=None, 1=Success, 2=Failure, 3=Both
                    if level == 0:
                        issues.append(SecurityIssue(
                            title="Login Auditing Disabled",
                            description="Login auditing appears to be disabled (AuditLevel=0).",
                            risk=SecurityRisk.MEDIUM,
                            category="Monitoring & Audit",
                            recommendation="Enable at least failed login auditing; consider auditing both success and failure based on policy."
                        ))
                    elif level in (1, 2):
                        issues.append(SecurityIssue(
                            title="Login Auditing Not Comprehensive",
                            description=f"Login auditing is enabled but not set to audit both success and failure (AuditLevel={level}).",
                            risk=SecurityRisk.LOW,
                            category="Monitoring & Audit",
                            recommendation="Review login auditing policy; auditing both success and failure improves forensics (may increase volume)."
                        ))
            except Exception as e:
                logger.debug(f"Login audit level check failed: {e}")

            # Default trace (legacy signal; still useful in some environments)
            try:
                dt = conn.execute_query(SecurityQueries.DEFAULT_TRACE_ENABLED) or []
                if dt and int(dt[0].get("default_trace_enabled", 1) or 1) == 0:
                    issues.append(SecurityIssue(
                        title="Default Trace Disabled",
                        description="Default trace is disabled. This reduces lightweight change tracking on older setups.",
                        risk=SecurityRisk.INFO,
                        category="Monitoring & Audit",
                        recommendation="Prefer Extended Events for auditing; if relying on default trace, enable it."
                    ))
            except Exception as e:
                logger.debug(f"Default trace check failed: {e}")
        except Exception as e:
            logger.debug(f"Audit posture checks failed: {e}")

        # Check 19 (P2/P3): Encryption / data protection posture
        try:
            tde = conn.execute_query(SecurityQueries.TDE_STATUS) or []
            user_dbs = [r for r in tde if (r.get("database_name") or "").lower() not in ("master", "model", "msdb", "tempdb")]
            encrypted = [r for r in user_dbs if int(r.get("encryption_state", 0) or 0) == 3]
            if user_dbs and not encrypted:
                details = [r.get("database_name", "") for r in user_dbs[:12]]
                if len(user_dbs) > 12:
                    details.append(f"... (+{len(user_dbs) - 12} more)")
                issues.append(SecurityIssue(
                    title="No TDE-Encrypted User Databases Detected",
                    description="No user database appears to be in 'Encrypted' state (TDE). This may be fine depending on policy, but is worth reviewing for sensitive data.",
                    risk=SecurityRisk.LOW,
                    category="Encryption",
                    details=details,
                    recommendation="Enable TDE for sensitive databases where appropriate; ensure key management and backups are handled securely."
                ))

            # Backup encryption (best-effort)
            backups = conn.execute_query(SecurityQueries.BACKUP_ENCRYPTION_SUMMARY) or []
            if backups:
                not_encrypted = [
                    b for b in backups
                    if int(b.get("total_backups", 0) or 0) > 0
                    and int(b.get("encrypted_backups", 0) or 0) < int(b.get("total_backups", 0) or 0)
                ]
                if not_encrypted:
                    details = [
                        f"{b.get('database_name', '')}: {b.get('encrypted_backups', 0)}/{b.get('total_backups', 0)} encrypted (last 30d)"
                        for b in not_encrypted[:10]
                    ]
                    if len(not_encrypted) > 10:
                        details.append(f"... (+{len(not_encrypted) - 10} more)")
                    issues.append(SecurityIssue(
                        title="Backups Not Encrypted (Last 30 Days)",
                        description="Some recent backups appear to be unencrypted (best-effort detection).",
                        risk=SecurityRisk.MEDIUM,
                        category="Encryption",
                        details=details,
                        recommendation="Use `WITH ENCRYPTION` for backups and protect keys/certificates according to policy."
                    ))

            # Always Encrypted presence (informational)
            ae = conn.execute_query(SecurityQueries.ALWAYS_ENCRYPTED_KEYS) or []
            if ae:
                cmk = int(ae[0].get("cmk_count", 0) or 0)
                cek = int(ae[0].get("cek_count", 0) or 0)
                if cmk == 0 and cek == 0:
                    issues.append(SecurityIssue(
                        title="Always Encrypted Not Configured (Current DB)",
                        description="No Always Encrypted column master/encryption keys were found in the current database.",
                        risk=SecurityRisk.INFO,
                        category="Encryption",
                        recommendation="If you store highly sensitive columns, consider Always Encrypted or column-level encryption per policy."
                    ))
        except Exception as e:
            logger.debug(f"Encryption posture checks failed: {e}")
        
        # Sort by risk level
        risk_order = {
            SecurityRisk.CRITICAL: 0,
            SecurityRisk.HIGH: 1,
            SecurityRisk.MEDIUM: 2,
            SecurityRisk.LOW: 3,
            SecurityRisk.INFO: 4,
        }
        issues.sort(key=lambda x: risk_order.get(x.risk, 5))
        
        return issues
    
    def get_server_permissions(self) -> List[Dict[str, Any]]:
        """Get server-level permissions"""
        if not self.is_connected:
            return []
        
        try:
            result = self.connection.execute_query(SecurityQueries.SERVER_PERMISSIONS)
            return result or []
        except Exception as e:
            logger.warning(f"Error getting server permissions: {e}")
        return []
    
    def get_database_permissions(self) -> List[Dict[str, Any]]:
        """Get database-level permissions"""
        if not self.is_connected:
            return []
        
        try:
            result = self.connection.execute_query(SecurityQueries.DATABASE_PERMISSIONS)
            return result or []
        except Exception as e:
            logger.warning(f"Error getting database permissions: {e}")
        return []


def get_security_service() -> SecurityService:
    """Get singleton security service instance"""
    return SecurityService()
