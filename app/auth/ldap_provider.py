"""
LDAP/Active Directory Authentication Provider
Supports:
- LDAP (Lightweight Directory Access Protocol)
- Microsoft Active Directory
- Azure AD (via LDAP interface)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import ssl

from app.core.logger import get_logger

logger = get_logger('auth.ldap')


class LDAPConnectionMode(Enum):
    """LDAP connection modes"""
    SIMPLE = "simple"           # Simple bind (username/password)
    NTLM = "ntlm"              # NTLM authentication (Windows)
    KERBEROS = "kerberos"       # Kerberos authentication


class LDAPEncryption(Enum):
    """LDAP encryption modes"""
    NONE = "none"              # No encryption (port 389)
    START_TLS = "start_tls"    # STARTTLS upgrade
    LDAPS = "ldaps"            # LDAP over SSL (port 636)


@dataclass
class LDAPConfig:
    """LDAP server configuration"""
    server: str                                     # LDAP server hostname or IP
    port: int = 389                                 # Default LDAP port
    base_dn: str = ""                              # Base DN for searches
    bind_dn: str = ""                              # DN for binding (admin/service account)
    bind_password: str = ""                        # Bind password
    
    # Connection settings
    encryption: LDAPEncryption = LDAPEncryption.START_TLS
    connection_mode: LDAPConnectionMode = LDAPConnectionMode.SIMPLE
    timeout: int = 10                              # Connection timeout in seconds
    
    # Search settings
    user_search_filter: str = "(sAMAccountName={username})"  # AD default
    user_search_base: str = ""                     # Override base_dn for user search
    group_search_filter: str = "(member={user_dn})"
    group_search_base: str = ""                    # Override base_dn for group search
    
    # Attribute mappings
    username_attribute: str = "sAMAccountName"     # AD: sAMAccountName, LDAP: uid
    email_attribute: str = "mail"
    display_name_attribute: str = "displayName"
    group_attribute: str = "memberOf"
    
    # SSL settings
    validate_certs: bool = True
    ca_certs_file: str = ""                        # Path to CA certificates
    
    # Domain settings (for AD)
    domain: str = ""                               # e.g., "company.local"
    
    def get_port(self) -> int:
        """Get port based on encryption"""
        if self.port != 389:
            return self.port
        return 636 if self.encryption == LDAPEncryption.LDAPS else 389


@dataclass
class LDAPUser:
    """Authenticated LDAP user"""
    username: str
    dn: str                                        # Distinguished Name
    email: str = ""
    display_name: str = ""
    groups: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_admin(self) -> bool:
        """Check if user is in admin groups"""
        admin_groups = ['Domain Admins', 'Administrators', 'DBA', 'DBAdmins']
        return any(g in self.groups for g in admin_groups)


class LDAPAuthResult:
    """Result of LDAP authentication"""
    
    def __init__(self, success: bool, user: Optional[LDAPUser] = None, 
                 error: str = "", error_code: str = ""):
        self.success = success
        self.user = user
        self.error = error
        self.error_code = error_code
    
    @property
    def error_message(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.error}"
        return self.error


class LDAPProvider:
    """
    LDAP/Active Directory Authentication Provider
    
    Usage:
        config = LDAPConfig(
            server="ldap.company.com",
            base_dn="DC=company,DC=local",
            domain="company.local"
        )
        
        provider = LDAPProvider(config)
        result = provider.authenticate("jdoe", "password123")
        
        if result.success:
            print(f"Welcome {result.user.display_name}!")
        else:
            print(f"Login failed: {result.error}")
    """
    
    def __init__(self, config: LDAPConfig):
        self.config = config
        self._connection = None
        self._server = None
        
    def _get_server(self):
        """Get or create LDAP server connection"""
        try:
            from ldap3 import Server, Tls
            
            tls = None
            if self.config.encryption != LDAPEncryption.NONE:
                tls_config = {
                    'validate': ssl.CERT_REQUIRED if self.config.validate_certs else ssl.CERT_NONE,
                }
                if self.config.ca_certs_file:
                    tls_config['ca_certs_file'] = self.config.ca_certs_file
                tls = Tls(**tls_config)
            
            use_ssl = self.config.encryption == LDAPEncryption.LDAPS
            
            self._server = Server(
                self.config.server,
                port=self.config.get_port(),
                use_ssl=use_ssl,
                tls=tls,
                get_info='ALL',
                connect_timeout=self.config.timeout
            )
            
            return self._server
            
        except ImportError:
            logger.error("ldap3 package not installed. Run: pip install ldap3")
            raise
        except Exception as e:
            logger.error(f"Failed to create LDAP server: {e}")
            raise
    
    def _get_bind_dn(self, username: str) -> str:
        """Get the full DN or UPN for binding"""
        # If domain is set, use UPN format (username@domain)
        if self.config.domain:
            return f"{username}@{self.config.domain}"
        
        # If bind_dn template contains {username}, use it
        if self.config.bind_dn and "{username}" in self.config.bind_dn:
            return self.config.bind_dn.format(username=username)
        
        # Default: try username as-is (might be full DN)
        return username
    
    def authenticate(self, username: str, password: str) -> LDAPAuthResult:
        """
        Authenticate a user against LDAP/AD
        
        Args:
            username: Username (sAMAccountName, UPN, or email)
            password: User's password
            
        Returns:
            LDAPAuthResult with success status and user info
        """
        try:
            from ldap3 import Connection, NTLM, SIMPLE, AUTO_BIND_TLS_BEFORE_BIND, AUTO_BIND_NO_TLS
            
            server = self._get_server()
            bind_dn = self._get_bind_dn(username)
            
            # Determine authentication mode
            if self.config.connection_mode == LDAPConnectionMode.NTLM:
                authentication = NTLM
                # For NTLM, format: DOMAIN\username
                if self.config.domain and '\\' not in bind_dn and '@' not in bind_dn:
                    bind_dn = f"{self.config.domain}\\{username}"
            else:
                authentication = SIMPLE
            
            # Determine auto_bind based on encryption
            if self.config.encryption == LDAPEncryption.START_TLS:
                auto_bind = AUTO_BIND_TLS_BEFORE_BIND
            else:
                auto_bind = AUTO_BIND_NO_TLS
            
            logger.debug(f"Attempting LDAP bind: {bind_dn}")
            
            # Try to bind
            conn = Connection(
                server,
                user=bind_dn,
                password=password,
                authentication=authentication,
                auto_bind=auto_bind,
                read_only=True,
                receive_timeout=self.config.timeout
            )
            
            if not conn.bound:
                logger.warning(f"LDAP bind failed for {username}: {conn.result}")
                return LDAPAuthResult(
                    success=False,
                    error="Invalid username or password",
                    error_code="INVALID_CREDENTIALS"
                )
            
            # Search for user details
            user = self._get_user_details(conn, username)
            
            if user:
                logger.info(f"LDAP authentication successful for {username}")
                return LDAPAuthResult(success=True, user=user)
            else:
                # Authenticated but couldn't find user details
                user = LDAPUser(username=username, dn=bind_dn)
                return LDAPAuthResult(success=True, user=user)
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"LDAP authentication error for {username}: {error_msg}")
            
            # Parse common LDAP errors
            if "invalidCredentials" in error_msg or "52e" in error_msg:
                return LDAPAuthResult(
                    success=False,
                    error="Invalid username or password",
                    error_code="INVALID_CREDENTIALS"
                )
            elif "unwillingToPerform" in error_msg:
                return LDAPAuthResult(
                    success=False,
                    error="Account disabled or locked",
                    error_code="ACCOUNT_DISABLED"
                )
            elif "serverDown" in error_msg or "connection" in error_msg.lower():
                return LDAPAuthResult(
                    success=False,
                    error="Cannot connect to LDAP server",
                    error_code="SERVER_UNAVAILABLE"
                )
            else:
                return LDAPAuthResult(
                    success=False,
                    error=error_msg,
                    error_code="LDAP_ERROR"
                )
    
    def _get_user_details(self, conn, username: str) -> Optional[LDAPUser]:
        """Get detailed user information after successful bind"""
        try:
            search_base = self.config.user_search_base or self.config.base_dn
            search_filter = self.config.user_search_filter.format(username=username)
            
            attributes = [
                self.config.username_attribute,
                self.config.email_attribute,
                self.config.display_name_attribute,
                self.config.group_attribute,
                'distinguishedName'
            ]
            
            conn.search(
                search_base=search_base,
                search_filter=search_filter,
                attributes=attributes
            )
            
            if not conn.entries:
                logger.debug(f"No LDAP entries found for {username}")
                return None
            
            entry = conn.entries[0]
            
            # Extract attributes safely
            def get_attr(attr_name: str, default: str = "") -> str:
                if hasattr(entry, attr_name):
                    val = getattr(entry, attr_name)
                    return str(val.value) if val.value else default
                return default
            
            # Get groups
            groups = []
            if hasattr(entry, self.config.group_attribute):
                member_of = getattr(entry, self.config.group_attribute)
                if member_of.values:
                    for group_dn in member_of.values:
                        # Extract CN from DN
                        if isinstance(group_dn, str) and group_dn.startswith('CN='):
                            cn = group_dn.split(',')[0].replace('CN=', '')
                            groups.append(cn)
            
            return LDAPUser(
                username=get_attr(self.config.username_attribute, username),
                dn=get_attr('distinguishedName'),
                email=get_attr(self.config.email_attribute),
                display_name=get_attr(self.config.display_name_attribute),
                groups=groups,
                attributes=dict(entry.entry_attributes_as_dict)
            )
            
        except Exception as e:
            logger.warning(f"Failed to get user details: {e}")
            return None
    
    def test_connection(self) -> tuple[bool, str]:
        """
        Test LDAP server connection
        
        Returns:
            Tuple of (success, message)
        """
        try:
            from ldap3 import Connection, ANONYMOUS
            
            server = self._get_server()
            
            # Try anonymous bind to test connectivity
            conn = Connection(server, auto_bind=True, read_only=True)
            
            if conn.bound:
                server_info = f"Connected to {self.config.server}"
                if server.info:
                    server_info += f" ({server.info.vendor_name or 'Unknown vendor'})"
                conn.unbind()
                return True, server_info
            else:
                return False, f"Connection failed: {conn.result}"
                
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def search_users(self, search_term: str, limit: int = 10) -> List[LDAPUser]:
        """
        Search for users in LDAP directory
        
        Args:
            search_term: Search term (partial username, name, or email)
            limit: Maximum results to return
            
        Returns:
            List of matching LDAPUser objects
        """
        try:
            from ldap3 import Connection
            
            # Need a service account for searching
            if not self.config.bind_dn or not self.config.bind_password:
                logger.warning("Cannot search users without service account credentials")
                return []
            
            server = self._get_server()
            
            conn = Connection(
                server,
                user=self.config.bind_dn,
                password=self.config.bind_password,
                auto_bind=True,
                read_only=True
            )
            
            search_base = self.config.user_search_base or self.config.base_dn
            # Multi-attribute search
            search_filter = f"(|({self.config.username_attribute}=*{search_term}*)({self.config.display_name_attribute}=*{search_term}*)({self.config.email_attribute}=*{search_term}*))"
            
            attributes = [
                self.config.username_attribute,
                self.config.email_attribute,
                self.config.display_name_attribute,
                'distinguishedName'
            ]
            
            conn.search(
                search_base=search_base,
                search_filter=search_filter,
                attributes=attributes,
                size_limit=limit
            )
            
            users = []
            for entry in conn.entries:
                def get_attr(attr_name: str, default: str = "") -> str:
                    if hasattr(entry, attr_name):
                        val = getattr(entry, attr_name)
                        return str(val.value) if val.value else default
                    return default
                
                users.append(LDAPUser(
                    username=get_attr(self.config.username_attribute),
                    dn=get_attr('distinguishedName'),
                    email=get_attr(self.config.email_attribute),
                    display_name=get_attr(self.config.display_name_attribute)
                ))
            
            conn.unbind()
            return users
            
        except Exception as e:
            logger.error(f"User search failed: {e}")
            return []


def create_ad_config(server: str, domain: str, base_dn: str = "") -> LDAPConfig:
    """
    Create an Active Directory configuration with sensible defaults
    
    Args:
        server: AD domain controller hostname
        domain: AD domain (e.g., "company.local")
        base_dn: Base DN (auto-generated from domain if not provided)
        
    Returns:
        LDAPConfig configured for Active Directory
    """
    if not base_dn:
        # Generate base_dn from domain: company.local -> DC=company,DC=local
        parts = domain.split('.')
        base_dn = ','.join(f'DC={part}' for part in parts)
    
    return LDAPConfig(
        server=server,
        port=389,
        base_dn=base_dn,
        domain=domain,
        encryption=LDAPEncryption.START_TLS,
        connection_mode=LDAPConnectionMode.SIMPLE,
        user_search_filter="(sAMAccountName={username})",
        username_attribute="sAMAccountName",
        email_attribute="mail",
        display_name_attribute="displayName",
        group_attribute="memberOf"
    )


def create_openldap_config(server: str, base_dn: str) -> LDAPConfig:
    """
    Create an OpenLDAP configuration with sensible defaults
    
    Args:
        server: LDAP server hostname
        base_dn: Base DN for the directory
        
    Returns:
        LDAPConfig configured for OpenLDAP
    """
    return LDAPConfig(
        server=server,
        port=389,
        base_dn=base_dn,
        encryption=LDAPEncryption.START_TLS,
        connection_mode=LDAPConnectionMode.SIMPLE,
        user_search_filter="(uid={username})",
        username_attribute="uid",
        email_attribute="mail",
        display_name_attribute="cn",
        group_attribute="memberOf"
    )
