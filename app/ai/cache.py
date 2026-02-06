"""
AI Analysis Cache - Intelligent caching for AI responses and collection data

Provides:
- Multi-level caching (memory + disk)
- TTL-based expiration
- Hash-based cache keys
- Invalidation strategies
"""

import hashlib
import json
import time
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from collections import OrderedDict
from enum import Enum

from app.core.logger import get_logger

logger = get_logger('ai.cache')

T = TypeVar('T')


class CacheLevel(Enum):
    """Cache storage levels"""
    MEMORY = "memory"     # In-memory (fastest, volatile)
    DISK = "disk"         # File-based (persistent, slower)
    BOTH = "both"         # Memory with disk backup


class CacheStrategy(Enum):
    """Cache invalidation strategies"""
    TTL = "ttl"                    # Time-to-live based
    LRU = "lru"                    # Least recently used
    SIZE_BASED = "size_based"      # Max size limit
    HASH_BASED = "hash_based"      # Content hash mismatch


@dataclass
class CacheEntry(Generic[T]):
    """Individual cache entry with metadata"""
    key: str
    value: T
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.now)
    content_hash: Optional[str] = None
    size_bytes: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self) -> None:
        """Update access metadata"""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class CacheConfig:
    """Cache configuration"""
    # Memory cache settings
    memory_enabled: bool = True
    memory_max_entries: int = 100
    memory_max_size_mb: int = 50
    
    # Disk cache settings
    disk_enabled: bool = True
    disk_cache_dir: Optional[str] = None  # Default: user cache dir
    disk_max_size_mb: int = 200
    
    # TTL settings (seconds)
    default_ttl: int = 3600  # 1 hour
    analysis_ttl: int = 7200  # 2 hours for AI analysis
    collection_ttl: int = 600  # 10 minutes for collection data
    
    # Strategies
    eviction_strategy: CacheStrategy = CacheStrategy.LRU
    
    def get_disk_cache_path(self) -> Path:
        """Get the disk cache directory path"""
        if self.disk_cache_dir:
            return Path(self.disk_cache_dir)
        
        # Default to user cache directory
        import os
        cache_base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.cache'))
        return cache_base / 'SQLPerfAI' / 'ai_cache'


class CacheKeyBuilder:
    """Builds cache keys from various inputs"""
    
    @staticmethod
    def for_analysis(
        object_name: str,
        source_code_hash: str,
        analysis_type: str = "optimization"
    ) -> str:
        """Build cache key for AI analysis"""
        parts = [
            "analysis",
            analysis_type,
            object_name,
            source_code_hash[:16]
        ]
        return ":".join(parts)
    
    @staticmethod
    def for_collection(
        db_name: str,
        object_name: str,
        collector_name: str
    ) -> str:
        """Build cache key for collection data"""
        parts = [
            "collection",
            db_name,
            object_name,
            collector_name
        ]
        return ":".join(parts)
    
    @staticmethod
    def hash_content(content: Any) -> str:
        """Generate hash from content"""
        if isinstance(content, str):
            data = content.encode('utf-8')
        elif isinstance(content, bytes):
            data = content
        else:
            data = json.dumps(content, sort_keys=True, default=str).encode('utf-8')
        
        return hashlib.sha256(data).hexdigest()


class MemoryCache:
    """In-memory LRU cache with size limits"""
    
    def __init__(self, max_entries: int = 100, max_size_mb: int = 50):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_entries = max_entries
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._current_size = 0
        self._lock = Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if entry.is_expired:
                self._remove_entry(key)
                self._stats["misses"] += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            self._stats["hits"] += 1
            
            return entry.value
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None,
        content_hash: Optional[str] = None
    ) -> None:
        """Set value in cache"""
        with self._lock:
            # Calculate size
            try:
                size = len(pickle.dumps(value))
            except Exception:
                size = 1024  # Default estimate
            
            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(seconds=ttl_seconds) if ttl_seconds else None,
                content_hash=content_hash,
                size_bytes=size,
            )
            
            # Remove old entry if exists
            if key in self._cache:
                self._remove_entry(key)
            
            # Evict if necessary
            while (len(self._cache) >= self._max_entries or 
                   self._current_size + size > self._max_size_bytes):
                if not self._cache:
                    break
                self._evict_oldest()
            
            # Add entry
            self._cache[key] = entry
            self._current_size += size
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a specific key"""
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate keys matching pattern (simple prefix match)"""
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(pattern)]
            for key in keys_to_remove:
                self._remove_entry(key)
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Clear all entries"""
        with self._lock:
            self._cache.clear()
            self._current_size = 0
    
    def _remove_entry(self, key: str) -> None:
        """Remove entry and update size"""
        if key in self._cache:
            self._current_size -= self._cache[key].size_bytes
            del self._cache[key]
    
    def _evict_oldest(self) -> None:
        """Evict least recently used entry"""
        if self._cache:
            oldest_key = next(iter(self._cache))
            self._remove_entry(oldest_key)
            self._stats["evictions"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
            
            return {
                "entries": len(self._cache),
                "max_entries": self._max_entries,
                "size_bytes": self._current_size,
                "max_size_bytes": self._max_size_bytes,
                "utilization_pct": (self._current_size / self._max_size_bytes * 100) if self._max_size_bytes > 0 else 0,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate_pct": round(hit_rate, 2),
                "evictions": self._stats["evictions"],
            }


class DiskCache:
    """Disk-based cache with persistence"""
    
    def __init__(self, cache_dir: Path, max_size_mb: int = 200):
        self._cache_dir = cache_dir
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._index_file = cache_dir / "index.json"
        self._index: Dict[str, Dict] = {}
        self._lock = Lock()
        
        # Ensure directory exists
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_index()
    
    def _load_index(self) -> None:
        """Load cache index from disk"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r') as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
                self._index = {}
    
    def _save_index(self) -> None:
        """Save cache index to disk"""
        try:
            with open(self._index_file, 'w') as f:
                json.dump(self._index, f)
        except Exception as e:
            logger.warning(f"Failed to save cache index: {e}")
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for a cache key"""
        # Hash the key to create a valid filename
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self._cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache"""
        with self._lock:
            if key not in self._index:
                return None
            
            meta = self._index[key]
            
            # Check expiration
            if meta.get("expires_at"):
                if datetime.fromisoformat(meta["expires_at"]) < datetime.now():
                    self.invalidate(key)
                    return None
            
            # Read from disk
            file_path = self._get_file_path(key)
            if not file_path.exists():
                del self._index[key]
                self._save_index()
                return None
            
            try:
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to read cache file: {e}")
                return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Set value in disk cache"""
        with self._lock:
            file_path = self._get_file_path(key)
            
            try:
                # Serialize
                data = pickle.dumps(value)
                size = len(data)
                
                # Evict if necessary
                self._enforce_size_limit(size)
                
                # Write to disk
                with open(file_path, 'wb') as f:
                    f.write(data)
                
                # Update index
                self._index[key] = {
                    "file": str(file_path.name),
                    "size": size,
                    "created_at": datetime.now().isoformat(),
                    "expires_at": (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat() if ttl_seconds else None,
                }
                self._save_index()
                
            except Exception as e:
                logger.warning(f"Failed to write cache file: {e}")
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a specific key"""
        with self._lock:
            if key not in self._index:
                return False
            
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
            
            del self._index[key]
            self._save_index()
            return True
    
    def clear(self) -> None:
        """Clear all cache files"""
        with self._lock:
            for file in self._cache_dir.glob("*.cache"):
                file.unlink()
            self._index = {}
            self._save_index()
    
    def _enforce_size_limit(self, new_size: int) -> None:
        """Evict old entries to stay within size limit"""
        current_size = sum(m.get("size", 0) for m in self._index.values())
        
        while current_size + new_size > self._max_size_bytes and self._index:
            # Remove oldest entry
            oldest_key = min(
                self._index.keys(),
                key=lambda k: self._index[k].get("created_at", "")
            )
            current_size -= self._index[oldest_key].get("size", 0)
            
            file_path = self._get_file_path(oldest_key)
            if file_path.exists():
                file_path.unlink()
            del self._index[oldest_key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_size = sum(m.get("size", 0) for m in self._index.values())
            return {
                "entries": len(self._index),
                "size_bytes": total_size,
                "max_size_bytes": self._max_size_bytes,
                "utilization_pct": (total_size / self._max_size_bytes * 100) if self._max_size_bytes > 0 else 0,
                "cache_dir": str(self._cache_dir),
            }


class AIAnalysisCache:
    """
    High-level cache manager for AI analysis results.
    
    Provides intelligent caching with:
    - Multi-level storage (memory + disk)
    - Content-aware invalidation
    - TTL management
    - Statistics tracking
    
    Usage:
        cache = AIAnalysisCache()
        
        # Cache analysis result
        cache.set_analysis("dbo.MyProc", source_code, analysis_result)
        
        # Get cached result (None if not found/expired)
        result = cache.get_analysis("dbo.MyProc", source_code)
        
        # Invalidate when source changes
        cache.invalidate_object("dbo.MyProc")
    """
    
    _instance: Optional["AIAnalysisCache"] = None
    
    def __new__(cls, config: Optional[CacheConfig] = None):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[CacheConfig] = None):
        if self._initialized:
            return
            
        self._config = config or CacheConfig()
        
        # Initialize caches
        if self._config.memory_enabled:
            self._memory = MemoryCache(
                max_entries=self._config.memory_max_entries,
                max_size_mb=self._config.memory_max_size_mb
            )
        else:
            self._memory = None
        
        if self._config.disk_enabled:
            self._disk = DiskCache(
                cache_dir=self._config.get_disk_cache_path(),
                max_size_mb=self._config.disk_max_size_mb
            )
        else:
            self._disk = None
        
        self._initialized = True
        logger.info("AIAnalysisCache initialized")
    
    def get_analysis(
        self, 
        object_name: str, 
        source_code: str,
        analysis_type: str = "optimization"
    ) -> Optional[str]:
        """
        Get cached analysis result.
        
        Args:
            object_name: Object identifier
            source_code: Current source code (for hash comparison)
            analysis_type: Type of analysis
            
        Returns:
            Cached analysis or None
        """
        content_hash = CacheKeyBuilder.hash_content(source_code)
        key = CacheKeyBuilder.for_analysis(object_name, content_hash, analysis_type)
        
        # Try memory first
        if self._memory:
            result = self._memory.get(key)
            if result is not None:
                logger.debug(f"Cache hit (memory): {key}")
                return result
        
        # Try disk
        if self._disk:
            result = self._disk.get(key)
            if result is not None:
                logger.debug(f"Cache hit (disk): {key}")
                # Promote to memory cache
                if self._memory:
                    self._memory.set(key, result, self._config.analysis_ttl, content_hash)
                return result
        
        logger.debug(f"Cache miss: {key}")
        return None
    
    def set_analysis(
        self,
        object_name: str,
        source_code: str,
        analysis_result: str,
        analysis_type: str = "optimization"
    ) -> None:
        """
        Cache analysis result.
        
        Args:
            object_name: Object identifier
            source_code: Source code (for hash)
            analysis_result: AI analysis result
            analysis_type: Type of analysis
        """
        content_hash = CacheKeyBuilder.hash_content(source_code)
        key = CacheKeyBuilder.for_analysis(object_name, content_hash, analysis_type)
        ttl = self._config.analysis_ttl
        
        # Store in both levels
        if self._memory:
            self._memory.set(key, analysis_result, ttl, content_hash)
        
        if self._disk:
            self._disk.set(key, analysis_result, ttl)
        
        logger.debug(f"Cached analysis: {key}")
    
    def get_collection(
        self,
        db_name: str,
        object_name: str,
        collector_name: str
    ) -> Optional[Any]:
        """Get cached collection data"""
        key = CacheKeyBuilder.for_collection(db_name, object_name, collector_name)
        
        if self._memory:
            result = self._memory.get(key)
            if result is not None:
                return result
        
        return None
    
    def set_collection(
        self,
        db_name: str,
        object_name: str,
        collector_name: str,
        data: Any
    ) -> None:
        """Cache collection data"""
        key = CacheKeyBuilder.for_collection(db_name, object_name, collector_name)
        
        if self._memory:
            self._memory.set(key, data, self._config.collection_ttl)
    
    def invalidate_object(self, object_name: str) -> int:
        """
        Invalidate all cache entries for an object.
        
        Returns:
            Number of invalidated entries
        """
        count = 0
        
        # Invalidate by pattern (prefix match)
        patterns = [
            f"analysis:optimization:{object_name}:",
            f"analysis:code_only:{object_name}:",
            f"collection:*:{object_name}:",
        ]
        
        for pattern in patterns:
            if self._memory:
                count += self._memory.invalidate_pattern(pattern.replace("*", ""))
        
        logger.info(f"Invalidated {count} cache entries for {object_name}")
        return count
    
    def clear_all(self) -> None:
        """Clear all caches"""
        if self._memory:
            self._memory.clear()
        if self._disk:
            self._disk.clear()
        logger.info("All caches cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = {
            "enabled": True,
            "memory": self._memory.get_stats() if self._memory else {"enabled": False},
            "disk": self._disk.get_stats() if self._disk else {"enabled": False},
        }
        
        # Combined stats
        if self._memory:
            stats["total_hit_rate_pct"] = stats["memory"].get("hit_rate_pct", 0)
        
        return stats


def get_ai_cache() -> AIAnalysisCache:
    """Get the singleton cache instance"""
    return AIAnalysisCache()


def cached_analysis(
    ttl_seconds: Optional[int] = None,
    analysis_type: str = "optimization"
) -> Callable:
    """
    Decorator for caching analysis results.
    
    Usage:
        @cached_analysis(ttl_seconds=3600)
        async def analyze_sp(self, object_name: str, source_code: str, ...) -> str:
            # AI analysis logic
            return result
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            cache = get_ai_cache()
            
            # Extract key parameters
            object_name = kwargs.get('object_name') or (args[1] if len(args) > 1 else None)
            source_code = kwargs.get('source_code') or (args[2] if len(args) > 2 else None)
            
            if object_name and source_code:
                # Check cache
                cached = cache.get_analysis(object_name, source_code, analysis_type)
                if cached is not None:
                    logger.info(f"Using cached analysis for {object_name}")
                    return cached
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            if object_name and source_code and result:
                cache.set_analysis(object_name, source_code, result, analysis_type)
            
            return result
        
        return wrapper
    return decorator
