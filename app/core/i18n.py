"""
Internationalization (i18n) System - Multi-language support for SQL Perf AI
Runtime language is driven by Settings.ui.language.
"""

import json
import os
from typing import Dict, Optional, Any
from pathlib import Path
from functools import lru_cache

from app.core.constants import Language
from app.core.logger import get_logger

logger = get_logger('core.i18n')


class TranslationManager:
    """
    Manages translations for the application.
    
    Usage:
        from app.core.i18n import tr, set_language
        
        set_language(Language.ENGLISH)
        print(tr("dashboard.title"))  # "Dashboard"
        print(tr("common.save"))      # "Save"
    """
    
    _instance: Optional['TranslationManager'] = None
    
    def __new__(cls) -> 'TranslationManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._current_language: Language = Language.ENGLISH
        self._fallback_language: Language = Language.ENGLISH
        self._locales_path = self._get_locales_path()
        
        # Load all translations
        self._load_all_translations()
        self._initialized = True
    
    def _get_locales_path(self) -> Path:
        """Get the path to locales directory"""
        # Try different paths
        possible_paths = [
            Path(__file__).parent.parent / "locales",  # app/locales
            Path(__file__).parent.parent.parent / "locales",  # project/locales
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        # Create default path
        default_path = Path(__file__).parent.parent / "locales"
        default_path.mkdir(parents=True, exist_ok=True)
        return default_path
    
    def _load_all_translations(self) -> None:
        """Load all translation files"""
        for lang in Language:
            self._load_translation(lang)
    
    def _load_translation(self, language: Language) -> None:
        """Load translation file for a specific language"""
        file_path = self._locales_path / f"{language.value}.json"
        
        if not file_path.exists():
            logger.warning(f"Translation file not found: {file_path}")
            self._translations[language.value] = {}
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self._translations[language.value] = json.load(f)
            logger.info(f"Loaded translations for {language.value}")
        except Exception as e:
            logger.error(f"Failed to load translation {file_path}: {e}")
            self._translations[language.value] = {}
    
    def set_language(self, language: Language) -> None:
        """Set the current language"""
        self._current_language = language
        logger.info(f"Language set to: {language.value}")
        # Clear cache
        self.translate.cache_clear()
    
    def get_language(self) -> Language:
        """Get the current language"""
        return self._current_language
    
    @lru_cache(maxsize=1000)
    def translate(self, key: str, **kwargs) -> str:
        """
        Translate a key to the current language.
        
        Args:
            key: Dot-notation key (e.g., "dashboard.title", "common.save")
            **kwargs: Values for placeholders in the translation
            
        Returns:
            Translated string, or the key itself if not found
        """
        # Try current language
        value = self._get_nested_value(
            self._translations.get(self._current_language.value, {}),
            key
        )
        
        # Fallback to English if not found
        if value is None and self._current_language != self._fallback_language:
            value = self._get_nested_value(
                self._translations.get(self._fallback_language.value, {}),
                key
            )
        
        # Return key if still not found
        if value is None:
            logger.debug(f"Translation not found: {key}")
            return key
        
        # Apply format arguments if any
        if kwargs:
            try:
                return value.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing placeholder in translation {key}: {e}")
                return value
        
        return value
    
    def _get_nested_value(self, data: Dict, key: str) -> Optional[str]:
        """Get value from nested dictionary using dot notation"""
        keys = key.split('.')
        value = data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return None
        
        return value if isinstance(value, str) else None
    
    def reload(self) -> None:
        """Reload all translations from files"""
        self._translations.clear()
        self._load_all_translations()
        self.translate.cache_clear()
        logger.info("Translations reloaded")
    
    def get_available_languages(self) -> list:
        """Get list of available languages"""
        return [lang for lang in Language if self._translations.get(lang.value)]


# Singleton instance
_manager: Optional[TranslationManager] = None


def get_translation_manager() -> TranslationManager:
    """Get the translation manager singleton"""
    global _manager
    if _manager is None:
        _manager = TranslationManager()
    return _manager


def tr(key: str, **kwargs) -> str:
    """
    Shortcut function for translation.
    
    Usage:
        from app.core.i18n import tr
        
        label = tr("common.save")  # "Save" or "Kaydet" etc.
        msg = tr("errors.connection_failed", server="localhost")
    """
    return get_translation_manager().translate(key, **kwargs)


def set_language(language: Language) -> None:
    """Set the current language"""
    get_translation_manager().set_language(language)


def get_language() -> Language:
    """Get the current language"""
    return get_translation_manager().get_language()


def reload_translations() -> None:
    """Reload all translation files"""
    get_translation_manager().reload()


# Language display names
LANGUAGE_NAMES = {
    Language.ENGLISH: "English",
    Language.TURKISH: "Türkçe",
    Language.GERMAN: "Deutsch",
}


def get_language_name(language: Language) -> str:
    """Get display name for a language"""
    return LANGUAGE_NAMES.get(language, language.value)
