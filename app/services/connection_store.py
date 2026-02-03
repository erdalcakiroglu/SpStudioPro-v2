"""
Connection profile storage and management
"""

import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from app.models.connection_profile import ConnectionProfile, AuthMethod
from app.core.config import get_settings
from app.core.logger import get_logger
from app.core.exceptions import ConnectionProfileError

logger = get_logger('services.connection_store')


class ConnectionStore:
    """
    Manages connection profiles storage
    
    Features:
    - CRUD operations for connection profiles
    - JSON file persistence
    - Folder organization
    - Import/Export
    """
    
    _instance: Optional['ConnectionStore'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._profiles: Dict[str, ConnectionProfile] = {}
        self._file_path: Path = get_settings().connections_file
        self._initialized = True
        
        self._load()
    
    def _load(self) -> None:
        """Load profiles from JSON file"""
        if not self._file_path.exists():
            logger.info("No connections file found, starting fresh")
            return
        
        try:
            with open(self._file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for profile_data in data.get('profiles', []):
                try:
                    profile = ConnectionProfile.from_dict(profile_data)
                    self._profiles[profile.id] = profile
                except Exception as e:
                    logger.warning(f"Failed to load profile: {e}")
            
            logger.info(f"Loaded {len(self._profiles)} connection profiles")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in connections file: {e}")
        except Exception as e:
            logger.error(f"Failed to load connections: {e}")
    
    def _save(self) -> None:
        """Save profiles to JSON file"""
        try:
            # Ensure directory exists
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'version': '1.0',
                'profiles': [p.to_dict() for p in self._profiles.values()]
            }
            
            with open(self._file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Saved {len(self._profiles)} connection profiles")
            
        except Exception as e:
            logger.error(f"Failed to save connections: {e}")
            raise ConnectionProfileError(f"Failed to save connections: {e}")
    
    # === CRUD Operations ===
    
    def add(self, profile: ConnectionProfile) -> ConnectionProfile:
        """Add a new connection profile"""
        if profile.id in self._profiles:
            raise ConnectionProfileError(f"Profile with ID {profile.id} already exists")
        
        self._profiles[profile.id] = profile
        self._save()
        
        logger.info(f"Added connection profile: {profile.name}")
        return profile
    
    def update(self, profile: ConnectionProfile) -> ConnectionProfile:
        """Update an existing profile"""
        if profile.id not in self._profiles:
            raise ConnectionProfileError(f"Profile with ID {profile.id} not found")
        
        self._profiles[profile.id] = profile
        self._save()
        
        logger.info(f"Updated connection profile: {profile.name}")
        return profile
    
    def delete(self, profile_id: str) -> bool:
        """Delete a profile by ID"""
        if profile_id not in self._profiles:
            return False
        
        profile = self._profiles.pop(profile_id)
        self._save()
        
        logger.info(f"Deleted connection profile: {profile.name}")
        return True
    
    def get(self, profile_id: str) -> Optional[ConnectionProfile]:
        """Get a profile by ID"""
        return self._profiles.get(profile_id)
    
    def get_by_name(self, name: str) -> Optional[ConnectionProfile]:
        """Get a profile by name"""
        for profile in self._profiles.values():
            if profile.name == name:
                return profile
        return None
    
    def get_all(self) -> List[ConnectionProfile]:
        """Get all profiles"""
        return list(self._profiles.values())
    
    def get_by_folder(self, folder: str) -> List[ConnectionProfile]:
        """Get profiles in a specific folder"""
        return [p for p in self._profiles.values() if p.folder == folder]
    
    def get_folders(self) -> List[str]:
        """Get list of unique folders"""
        folders = set()
        for profile in self._profiles.values():
            if profile.folder:
                folders.add(profile.folder)
        return sorted(folders)
    
    # === Utility Methods ===
    
    def mark_connected(self, profile_id: str) -> None:
        """Update last connected timestamp"""
        if profile_id in self._profiles:
            self._profiles[profile_id].last_connected = datetime.now()
            self._save()
    
    def duplicate(self, profile_id: str) -> Optional[ConnectionProfile]:
        """Create a copy of a profile"""
        original = self.get(profile_id)
        if not original:
            return None
        
        copy = original.copy()
        return self.add(copy)
    
    def export_profiles(self, profile_ids: List[str], file_path: Path) -> int:
        """Export selected profiles to JSON file"""
        profiles_to_export = [
            p.to_dict() for p in self._profiles.values()
            if p.id in profile_ids
        ]
        
        if not profiles_to_export:
            return 0
        
        data = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'profiles': profiles_to_export
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Exported {len(profiles_to_export)} profiles to {file_path}")
        return len(profiles_to_export)
    
    def import_profiles(self, file_path: Path, overwrite: bool = False) -> int:
        """Import profiles from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        imported = 0
        for profile_data in data.get('profiles', []):
            try:
                profile = ConnectionProfile.from_dict(profile_data)
                
                # Generate new ID to avoid conflicts
                if not overwrite:
                    profile.id = str(__import__('uuid').uuid4())
                
                # Check for name conflict
                existing = self.get_by_name(profile.name)
                if existing and not overwrite:
                    profile.name = f"{profile.name} (imported)"
                
                if profile.id in self._profiles and overwrite:
                    self._profiles[profile.id] = profile
                else:
                    self._profiles[profile.id] = profile
                
                imported += 1
                
            except Exception as e:
                logger.warning(f"Failed to import profile: {e}")
        
        if imported > 0:
            self._save()
            logger.info(f"Imported {imported} profiles from {file_path}")
        
        return imported
    
    def search(self, query: str) -> List[ConnectionProfile]:
        """Search profiles by name, server, or tags"""
        query = query.lower()
        results = []
        
        for profile in self._profiles.values():
            if (query in profile.name.lower() or
                query in profile.server.lower() or
                query in profile.database.lower() or
                any(query in tag.lower() for tag in profile.tags)):
                results.append(profile)
        
        return results


def get_connection_store() -> ConnectionStore:
    """Get the global ConnectionStore instance"""
    return ConnectionStore()
