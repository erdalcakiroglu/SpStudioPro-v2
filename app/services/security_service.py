"""
Security Audit Service - SQL Server security analysis
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

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
        
        # Check 6: Trustworthy databases
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
        
        # Check 7: Cross-database chaining
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
        
        # Check 8: Guest access
        try:
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
        
        # Check 9: Public role permissions
        try:
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
        
        # Check 10: Locked accounts
        locked = [l.name for l in summary.logins if l.is_locked]
        if locked:
            issues.append(SecurityIssue(
                title="Locked Login Accounts",
                description=f"Found {len(locked)} locked login account(s).",
                risk=SecurityRisk.INFO,
                category="Authentication",
                details=locked,
                recommendation="Investigate why accounts are locked."
            ))
        
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
