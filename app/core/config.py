"""
Application configuration management using Pydantic Settings
"""

import sys
import os
from pathlib import Path
from typing import Optional, Any
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    APP_NAME,
    Theme,
    Language,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_QUERY_TIMEOUT,
    DEFAULT_CONNECTION_TIMEOUT,
    AI_RESPONSE_TIMEOUT,
)


def get_app_dir() -> Path:
    """
    Get application data directory.
    Portable mode: config folder next to exe
    Installed mode: OS-specific user data folder
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller executable
        exe_dir = Path(sys.executable).parent
        
        # Portable mode: config folder exists next to exe
        if (exe_dir / 'config').exists():
            return exe_dir
    
    # Installed mode: user data folder
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path.home() / '.config'
    
    return base / APP_NAME.replace(' ', '')


def ensure_app_dirs() -> Path:
    """Create necessary application directories"""
    app_dir = get_app_dir()
    
    (app_dir / 'config').mkdir(parents=True, exist_ok=True)
    (app_dir / 'data').mkdir(parents=True, exist_ok=True)
    (app_dir / 'logs').mkdir(parents=True, exist_ok=True)
    (app_dir / 'cache').mkdir(parents=True, exist_ok=True)
    
    return app_dir


class DatabaseSettings(BaseSettings):
    """Database connection settings"""
    
    query_timeout: int = Field(default=DEFAULT_QUERY_TIMEOUT, ge=1, le=600)
    connection_timeout: int = Field(default=DEFAULT_CONNECTION_TIMEOUT, ge=1, le=120)
    max_pool_size: int = Field(default=5, ge=1, le=20)
    pool_recycle: int = Field(default=3600, ge=60)
    echo_sql: bool = Field(default=False)


class AISettings(BaseSettings):
    """AI/LLM settings"""
    
    # The ID of the currently active/default provider
    active_provider_id: str = Field(default="default_ollama")
    
    ollama_host: str = Field(default=DEFAULT_OLLAMA_HOST)
    model: str = Field(default=DEFAULT_MODEL)
    temperature: float = Field(default=DEFAULT_TEMPERATURE, ge=0.0, le=2.0)
    max_tokens: int = Field(default=DEFAULT_MAX_TOKENS, ge=100, le=32000)
    timeout: int = Field(default=AI_RESPONSE_TIMEOUT, ge=10, le=600)
    
    # Dictionary of configured providers: {provider_id: {config_dict}}
    providers: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Prompt rules are stored in YAML under the repository `prompts/` folder.
    # (Settings.json should not contain prompt content.)
    prompt_rules: dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('ollama_host')
    @classmethod
    def validate_ollama_host(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            v = f"http://{v}"
        return v.rstrip('/')


class UISettings(BaseSettings):
    """UI settings"""
    
    theme: Theme = Field(default=Theme.DARK)
    language: Language = Field(default=Language.ENGLISH)
    sidebar_collapsed: bool = Field(default=False)
    window_width: int = Field(default=1400, ge=800, le=4096)
    window_height: int = Field(default=900, ge=600, le=2160)
    window_maximized: bool = Field(default=False)
    font_size: int = Field(default=13, ge=10, le=24)
    code_font_size: int = Field(default=12, ge=10, le=24)
    show_line_numbers: bool = Field(default=True)
    license_accepted: bool = Field(default=False)
    navigation_visibility: dict[str, bool] = Field(default_factory=lambda: {
        "chat": True,
        "dashboard": True,
        "sp_explorer": True,
        "query_stats": True,
        "index_advisor": True,
        "blocking": True,
        "security": True,
        "jobs": True,
        "wait_stats": True,
    })
    # Per-database Query Statistics filter memory.
    # Key format: connection/database hash, value: serialized filter params.
    query_stats_filter_memory: dict[str, dict[str, Any]] = Field(default_factory=dict)


class CacheSettings(BaseSettings):
    """Cache settings"""
    
    enabled: bool = Field(default=True)
    memory_cache_mb: int = Field(default=100, ge=10, le=1024)
    disk_cache_mb: int = Field(default=500, ge=50, le=5120)
    default_ttl: int = Field(default=300, ge=60, le=86400)


class LoggingSettings(BaseSettings):
    """Logging settings"""
    
    level: str = Field(default="INFO")
    file_enabled: bool = Field(default=True)
    max_file_size_mb: int = Field(default=10, ge=1, le=100)
    backup_count: int = Field(default=5, ge=1, le=20)
    retention_days: int = Field(default=7, ge=1, le=30)
    
    @field_validator('level')
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v = v.upper()
        if v not in valid_levels:
            v = 'INFO'
        return v


class LicenseSettings(BaseSettings):
    """License/trial settings (online validation)."""

    server_url: str = Field(default="")
    email: str = Field(default="")
    token: str = Field(default="")
    device_id: str = Field(default="")
    status: str = Field(default="unknown")
    trial_expires_at: Optional[str] = Field(default=None)
    license_count: int = Field(default=0, ge=0)
    allowed_devices: int = Field(default=0, ge=0)
    last_validated_at: Optional[str] = Field(default=None)


class Settings(BaseSettings):
    """Main application settings"""
    
    model_config = SettingsConfigDict(
        env_prefix='SQLPERFAI_',
        env_nested_delimiter='__',
        extra='ignore',
    )
    
    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    ai: AISettings = Field(default_factory=AISettings)
    ui: UISettings = Field(default_factory=UISettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    license: LicenseSettings = Field(default_factory=LicenseSettings)
    
    # App paths
    app_dir: Path = Field(default_factory=get_app_dir)
    
    # Feature flags
    enable_telemetry: bool = Field(default=False)
    enable_auto_connect: bool = Field(default=False)
    enable_auto_update: bool = Field(default=True)
    
    # Recent connections (stored separately but quick access here)
    last_connection_id: Optional[str] = Field(default=None)
    
    @property
    def config_dir(self) -> Path:
        return self.app_dir / 'config'
    
    @property
    def data_dir(self) -> Path:
        return self.app_dir / 'data'
    
    @property
    def logs_dir(self) -> Path:
        return self.app_dir / 'logs'
    
    @property
    def cache_dir(self) -> Path:
        return self.app_dir / 'cache'
    
    @property
    def settings_file(self) -> Path:
        return self.config_dir / 'settings.json'
    
    @property
    def connections_file(self) -> Path:
        return self.data_dir / 'connections.json'
    
    def save(self) -> None:
        """Save settings to JSON file"""
        ensure_app_dirs()
        
        # Convert to dict, excluding computed properties
        data = self.model_dump(
            exclude={'app_dir'},
            mode='json'
        )
        
        import json
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    
    @classmethod
    def load(cls) -> 'Settings':
        """Load settings from JSON file"""
        app_dir = ensure_app_dirs()
        settings_file = app_dir / 'config' / 'settings.json'
        
        if settings_file.exists():
            import json
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Lightweight migration: bump old default AI timeout (120s) to 300s.
                # This primarily affects AI Tune (Object Explorer) where 120s can be too short.
                try:
                    if isinstance(data, dict):
                        ai = data.get("ai")
                        if isinstance(ai, dict) and ai.get("timeout") == 120:
                            ai["timeout"] = 300
                            data["ai"] = ai
                except Exception:
                    pass
                return cls(**data)
            except Exception:
                # If loading fails, return defaults
                pass
         
        return cls()


# Global settings instance (cached)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings.load()
        # Interface language is locked to English for now.
        _settings.ui.language = Language.ENGLISH
        _init_i18n(Language.ENGLISH)
    return _settings


def _init_i18n(language: Language) -> None:
    """Initialize i18n system with the specified language"""
    try:
        from app.core.i18n import set_language
        set_language(language)
    except Exception:
        pass  # i18n not critical, fail silently


def reset_settings() -> Settings:
    """Reset settings to defaults"""
    global _settings
    _settings = Settings()
    _settings.save()
    return _settings


def update_settings(**kwargs) -> Settings:
    """Update settings with new values"""
    global _settings
    settings = get_settings()
    
    old_language = settings.ui.language
    
    # Update nested settings
    for key, value in kwargs.items():
        if hasattr(settings, key):
            if isinstance(value, dict) and hasattr(getattr(settings, key), 'model_copy'):
                # Update nested settings object
                nested = getattr(settings, key)
                updated_nested = nested.model_copy(update=value)
                setattr(settings, key, updated_nested)
            else:
                setattr(settings, key, value)
    
    # Interface language is locked to English for now.
    settings.ui.language = Language.ENGLISH

    settings.save()
    _settings = settings
    
    # Keep i18n in sync
    if settings.ui.language != old_language:
        _init_i18n(Language.ENGLISH)
    
    return settings
