"""
Authentication Manager - Orchestrates authentication across providers
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import time

from app.core.constants import AuthMethod
from app.core.logger import get_logger
from app.auth.ldap_provider import LDAPProvider, LDAPConfig, LDAPUser, LDAPAuthResult

logger = get_logger('auth.manager')


@dataclass
class AuthSession:
    """User authentication session"""
    username: str
    auth_method: AuthMethod
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    
    # User details
    display_name: str = ""
    email: str = ""
    groups: list = field(default_factory=list)
    
    # LDAP specific
    ldap_user: Optional[LDAPUser] = None
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    @property
    def session_id(self) -> str:
        """Generate session identifier"""
        data = f"{self.username}:{self.auth_method.value}:{self.created_at}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def is_admin(self) -> bool:
        """Check if user has admin privileges"""
        admin_groups = ['Domain Admins', 'Administrators', 'DBA', 'DBAdmins', 'sysadmin']
        return any(g.lower() in [ag.lower() for ag in admin_groups] for g in self.groups)


class AuthResult:
    """Result of authentication attempt"""
    
    def __init__(self, success: bool, session: Optional[AuthSession] = None,
                 error: str = "", error_code: str = ""):
        self.success = success
        self.session = session
        self.error = error
        self.error_code = error_code
    
    @property
    def error_message(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.error}"
        return self.error


class AuthManager:
    """
    Central authentication manager supporting multiple providers
    
    Usage:
        auth_mgr = AuthManager()
        
        # Configure LDAP
        auth_mgr.configure_ldap(LDAPConfig(...))
        
        # Authenticate
        result = auth_mgr.authenticate("jdoe", "password", AuthMethod.LDAP)
        if result.success:
            print(f"Welcome {result.session.display_name}")
    """
    
    _instance: Optional['AuthManager'] = None
    
    def __new__(cls) -> 'AuthManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._ldap_provider: Optional[LDAPProvider] = None
        self._ldap_config: Optional[LDAPConfig] = None
        self._current_session: Optional[AuthSession] = None
        self._session_timeout: int = 3600 * 8  # 8 hours default
        self._initialized = True
    
    @property
    def current_session(self) -> Optional[AuthSession]:
        """Get current authentication session"""
        if self._current_session and self._current_session.is_expired:
            logger.info("Session expired, clearing")
            self._current_session = None
        return self._current_session
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return self.current_session is not None
    
    def configure_ldap(self, config: LDAPConfig) -> None:
        """Configure LDAP provider"""
        self._ldap_config = config
        self._ldap_provider = LDAPProvider(config)
        logger.info(f"LDAP configured: {config.server}")
    
    def get_ldap_config(self) -> Optional[LDAPConfig]:
        """Get current LDAP configuration"""
        return self._ldap_config
    
    def test_ldap_connection(self) -> tuple[bool, str]:
        """Test LDAP server connectivity"""
        if not self._ldap_provider:
            return False, "LDAP not configured"
        return self._ldap_provider.test_connection()
    
    def authenticate(self, username: str, password: str, 
                    auth_method: AuthMethod = AuthMethod.SQL_SERVER,
                    **kwargs) -> AuthResult:
        """
        Authenticate user with specified method
        
        Args:
            username: Username or email
            password: Password
            auth_method: Authentication method to use
            **kwargs: Additional provider-specific options
            
        Returns:
            AuthResult with session if successful
        """
        logger.info(f"Authentication attempt: {username} via {auth_method.value}")
        
        if auth_method == AuthMethod.LDAP:
            return self._authenticate_ldap(username, password)
        elif auth_method == AuthMethod.WINDOWS:
            return self._authenticate_windows(username, password)
        else:
            # SQL Server auth is handled by the database connection
            return self._authenticate_sql(username, password)
    
    def _authenticate_ldap(self, username: str, password: str) -> AuthResult:
        """Authenticate via LDAP"""
        if not self._ldap_provider:
            return AuthResult(
                success=False,
                error="LDAP not configured",
                error_code="LDAP_NOT_CONFIGURED"
            )
        
        result = self._ldap_provider.authenticate(username, password)
        
        if result.success and result.user:
            # Create session
            session = AuthSession(
                username=result.user.username,
                auth_method=AuthMethod.LDAP,
                display_name=result.user.display_name or result.user.username,
                email=result.user.email,
                groups=result.user.groups,
                ldap_user=result.user,
                expires_at=time.time() + self._session_timeout
            )
            
            self._current_session = session
            logger.info(f"LDAP authentication successful: {username}")
            
            return AuthResult(success=True, session=session)
        else:
            return AuthResult(
                success=False,
                error=result.error,
                error_code=result.error_code
            )
    
    def _authenticate_windows(self, username: str, password: str) -> AuthResult:
        """
        Authenticate via Windows/NTLM
        Note: This typically uses the current Windows session
        """
        try:
            import ctypes
            
            # Try to logon using Windows API
            LOGON32_LOGON_NETWORK = 3
            LOGON32_PROVIDER_DEFAULT = 0
            
            token = ctypes.c_void_p()
            
            # Parse domain\username if provided
            domain = None
            if '\\' in username:
                domain, username = username.split('\\', 1)
            elif '@' in username:
                username, domain = username.split('@', 1)
            
            result = ctypes.windll.advapi32.LogonUserW(
                username,
                domain,
                password,
                LOGON32_LOGON_NETWORK,
                LOGON32_PROVIDER_DEFAULT,
                ctypes.byref(token)
            )
            
            if result:
                # Close the token
                ctypes.windll.kernel32.CloseHandle(token)
                
                session = AuthSession(
                    username=username,
                    auth_method=AuthMethod.WINDOWS,
                    display_name=username,
                    expires_at=time.time() + self._session_timeout
                )
                
                self._current_session = session
                logger.info(f"Windows authentication successful: {username}")
                
                return AuthResult(success=True, session=session)
            else:
                error_code = ctypes.windll.kernel32.GetLastError()
                return AuthResult(
                    success=False,
                    error="Invalid credentials",
                    error_code=f"WIN_ERROR_{error_code}"
                )
                
        except Exception as e:
            logger.error(f"Windows authentication error: {e}")
            return AuthResult(
                success=False,
                error=str(e),
                error_code="WINDOWS_AUTH_ERROR"
            )
    
    def _authenticate_sql(self, username: str, password: str) -> AuthResult:
        """
        SQL Server authentication
        Note: Actual validation happens during database connection
        """
        # Create a simple session - actual validation is done by DB connection
        session = AuthSession(
            username=username,
            auth_method=AuthMethod.SQL_SERVER,
            display_name=username,
            expires_at=time.time() + self._session_timeout
        )
        
        self._current_session = session
        logger.info(f"SQL auth session created for: {username}")
        
        return AuthResult(success=True, session=session)
    
    def logout(self) -> None:
        """End current session"""
        if self._current_session:
            logger.info(f"Logout: {self._current_session.username}")
            self._current_session = None
    
    def refresh_session(self) -> bool:
        """Refresh current session expiry"""
        if self._current_session:
            self._current_session.expires_at = time.time() + self._session_timeout
            return True
        return False
    
    def set_session_timeout(self, seconds: int) -> None:
        """Set session timeout in seconds"""
        self._session_timeout = max(300, min(seconds, 86400))  # 5 min to 24 hours


# Singleton accessor
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """Get the authentication manager singleton"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager
