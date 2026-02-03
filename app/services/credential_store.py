"""
Secure credential storage using OS keyring
"""

from typing import Optional
import keyring
from keyring.errors import KeyringError

from app.core.constants import APP_NAME
from app.core.logger import get_logger
from app.core.exceptions import CredentialStoreError

logger = get_logger('services.credential_store')


class CredentialStore:
    """
    Secure credential storage using OS keyring
    
    Uses the operating system's secure credential storage:
    - Windows: Windows Credential Manager
    - macOS: Keychain
    - Linux: Secret Service (GNOME Keyring, KWallet)
    """
    
    SERVICE_NAME = APP_NAME.replace(' ', '')  # "SQLPerfAI"
    
    _instance: Optional['CredentialStore'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._test_keyring()
    
    def _test_keyring(self) -> None:
        """Test if keyring is available"""
        try:
            # Try a simple operation
            keyring.get_keyring()
            logger.info(f"Keyring backend: {keyring.get_keyring().__class__.__name__}")
        except Exception as e:
            logger.warning(f"Keyring may not be available: {e}")
    
    def _get_key(self, profile_id: str) -> str:
        """Generate keyring key for a profile"""
        return f"{self.SERVICE_NAME}_{profile_id}"
    
    def set_password(self, profile_id: str, password: str) -> bool:
        """
        Store password for a connection profile
        
        Args:
            profile_id: Connection profile ID
            password: Password to store
        
        Returns:
            True if successful
        """
        try:
            key = self._get_key(profile_id)
            keyring.set_password(self.SERVICE_NAME, key, password)
            logger.debug(f"Password stored for profile: {profile_id}")
            return True
        except KeyringError as e:
            logger.error(f"Failed to store password: {e}")
            raise CredentialStoreError(f"Failed to store password: {e}")
        except Exception as e:
            logger.error(f"Unexpected error storing password: {e}")
            raise CredentialStoreError(f"Unexpected error: {e}")
    
    def get_password(self, profile_id: str) -> Optional[str]:
        """
        Retrieve password for a connection profile
        
        Args:
            profile_id: Connection profile ID
        
        Returns:
            Password string or None if not found
        """
        try:
            key = self._get_key(profile_id)
            password = keyring.get_password(self.SERVICE_NAME, key)
            return password
        except KeyringError as e:
            logger.error(f"Failed to retrieve password: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error retrieving password: {e}")
            return None
    
    def delete_password(self, profile_id: str) -> bool:
        """
        Delete password for a connection profile
        
        Args:
            profile_id: Connection profile ID
        
        Returns:
            True if successful or password didn't exist
        """
        try:
            key = self._get_key(profile_id)
            keyring.delete_password(self.SERVICE_NAME, key)
            logger.debug(f"Password deleted for profile: {profile_id}")
            return True
        except keyring.errors.PasswordDeleteError:
            # Password doesn't exist, that's OK
            return True
        except KeyringError as e:
            logger.error(f"Failed to delete password: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting password: {e}")
            return False
    
    def has_password(self, profile_id: str) -> bool:
        """Check if password exists for a profile"""
        return self.get_password(profile_id) is not None
    
    def update_password(self, profile_id: str, password: str) -> bool:
        """Update (or create) password for a profile"""
        return self.set_password(profile_id, password)
    
    def clear_all(self) -> int:
        """
        Clear all stored passwords (use with caution!)
        
        Returns:
            Number of passwords cleared
        """
        # Note: This is a destructive operation
        # We can't easily enumerate all stored passwords
        # This would need to work with ConnectionStore to get all profile IDs
        logger.warning("clear_all() is not fully implemented")
        return 0


def get_credential_store() -> CredentialStore:
    """Get the global CredentialStore instance"""
    return CredentialStore()
