#!/usr/bin/env python3
"""
CodeGuard AI - Redis Client Configuration

This module handles Redis connections and caching operations for the CodeGuard AI application.
Used for caching analysis results, session management, and rate limiting.
"""

import json
import pickle
from typing import Any, Optional, Union
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from .config import get_settings

settings = get_settings()

# Global Redis client
redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client
    
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False,  # We'll handle encoding manually
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Test connection
        await redis_client.ping()
        print("✅ Redis connection established")
        
    except Exception as e:
        print(f"❌ Redis initialization failed: {e}")
        redis_client = None
        raise


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


def get_redis() -> Optional[Redis]:
    """Get Redis client instance."""
    return redis_client


class CacheManager:
    """Redis cache manager for CodeGuard AI."""
    
    def __init__(self):
        self.client = redis_client
        self.default_expire = settings.REDIS_EXPIRE_SECONDS
    
    def _get_key(self, prefix: str, key: str) -> str:
        """Generate cache key with prefix."""
        return f"codeguard:{prefix}:{key}"
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None, prefix: str = "cache") -> bool:
        """Set a value in cache."""
        if not self.client:
            return False
        
        try:
            cache_key = self._get_key(prefix, key)
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            elif isinstance(value, str):
                serialized_value = value
            else:
                serialized_value = pickle.dumps(value)
            
            # Set with expiration
            expire_time = expire or self.default_expire
            await self.client.setex(cache_key, expire_time, serialized_value)
            return True
            
        except Exception as e:
            print(f"❌ Cache set error: {e}")
            return False
    
    async def get(self, key: str, prefix: str = "cache") -> Optional[Any]:
        """Get a value from cache."""
        if not self.client:
            return None
        
        try:
            cache_key = self._get_key(prefix, key)
            value = await self.client.get(cache_key)
            
            if value is None:
                return None
            
            # Try to deserialize as JSON first
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # If JSON fails, try pickle
                try:
                    return pickle.loads(value)
                except (pickle.PickleError, TypeError):
                    # Return as string if both fail
                    return value.decode('utf-8') if isinstance(value, bytes) else value
                    
        except Exception as e:
            print(f"❌ Cache get error: {e}")
            return None
    
    async def delete(self, key: str, prefix: str = "cache") -> bool:
        """Delete a value from cache."""
        if not self.client:
            return False
        
        try:
            cache_key = self._get_key(prefix, key)
            result = await self.client.delete(cache_key)
            return result > 0
        except Exception as e:
            print(f"❌ Cache delete error: {e}")
            return False
    
    async def exists(self, key: str, prefix: str = "cache") -> bool:
        """Check if key exists in cache."""
        if not self.client:
            return False
        
        try:
            cache_key = self._get_key(prefix, key)
            result = await self.client.exists(cache_key)
            return result > 0
        except Exception as e:
            print(f"❌ Cache exists error: {e}")
            return False
    
    async def expire(self, key: str, seconds: int, prefix: str = "cache") -> bool:
        """Set expiration time for a key."""
        if not self.client:
            return False
        
        try:
            cache_key = self._get_key(prefix, key)
            result = await self.client.expire(cache_key, seconds)
            return result
        except Exception as e:
            print(f"❌ Cache expire error: {e}")
            return False
    
    async def clear_prefix(self, prefix: str) -> int:
        """Clear all keys with given prefix."""
        if not self.client:
            return 0
        
        try:
            pattern = self._get_key(prefix, "*")
            keys = await self.client.keys(pattern)
            if keys:
                return await self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"❌ Cache clear prefix error: {e}")
            return 0
    
    async def get_stats(self) -> dict:
        """Get cache statistics."""
        if not self.client:
            return {"status": "disconnected"}
        
        try:
            info = await self.client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class RateLimiter:
    """Redis-based rate limiter."""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager
    
    async def is_allowed(self, key: str, limit: int, window_seconds: int = 3600) -> tuple[bool, dict]:
        """Check if request is allowed based on rate limit."""
        try:
            current_count = await self.cache.get(key, prefix="ratelimit") or 0
            current_count = int(current_count)
            
            if current_count >= limit:
                return False, {
                    "allowed": False,
                    "current": current_count,
                    "limit": limit,
                    "window_seconds": window_seconds
                }
            
            # Increment counter
            new_count = current_count + 1
            await self.cache.set(key, new_count, expire=window_seconds, prefix="ratelimit")
            
            return True, {
                "allowed": True,
                "current": new_count,
                "limit": limit,
                "remaining": limit - new_count,
                "window_seconds": window_seconds
            }
            
        except Exception as e:
            print(f"❌ Rate limiter error: {e}")
            # Allow request on error to avoid blocking legitimate traffic
            return True, {"allowed": True, "error": str(e)}


# Global cache manager instance
cache_manager = CacheManager()
rate_limiter = RateLimiter(cache_manager)


# Cache decorators
def cache_result(key_prefix: str, expire: int = None):
    """Decorator to cache function results."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key, prefix=key_prefix)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, expire=expire, prefix=key_prefix)
            return result
        
        return wrapper
    return decorator