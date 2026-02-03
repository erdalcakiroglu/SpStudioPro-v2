"""
Authentication module - MSSQL, Windows, and LDAP/AD auth providers

Supported authentication methods:
- SQL Server Authentication (username/password)
- Windows Authentication (NTLM/Kerberos)
- LDAP/Active Directory Authentication

Usage:
    from app.auth import get_auth_manager, LDAPConfig, create_ad_config
    
    # Configure LDAP/AD
    config = create_ad_config(
        server="dc.company.local",
        domain="company.local"
    )
    
    auth_mgr = get_auth_manager()
    auth_mgr.configure_ldap(config)
    
    # Authenticate
    from app.core.constants import AuthMethod
    result = auth_mgr.authenticate("jdoe", "password", AuthMethod.LDAP)
    
    if result.success:
        session = result.session
        print(f"Welcome {session.display_name}!")
        print(f"Groups: {session.groups}")
"""

from app.auth.auth_manager import (
    AuthManager,
    AuthSession,
    AuthResult,
    get_auth_manager,
)

from app.auth.ldap_provider import (
    LDAPProvider,
    LDAPConfig,
    LDAPUser,
    LDAPAuthResult,
    LDAPConnectionMode,
    LDAPEncryption,
    create_ad_config,
    create_openldap_config,
)

__all__ = [
    # Auth Manager
    'AuthManager',
    'AuthSession',
    'AuthResult',
    'get_auth_manager',
    
    # LDAP Provider
    'LDAPProvider',
    'LDAPConfig',
    'LDAPUser',
    'LDAPAuthResult',
    'LDAPConnectionMode',
    'LDAPEncryption',
    'create_ad_config',
    'create_openldap_config',
]
