"""
Redis Graph Cache for CAP Caselaw Plugin
High-speed caching layer for frequently accessed queries and results
"""

import logging
import json
import pickle
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import asyncio

import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError

from ..models.caselaw_node import CaselawNode
from ..models.case_relationship import CaseRelationship

logger = logging.getLogger(__name__)


class RedisGraphCache:
    """
    Redis-based caching layer for the CAP caselaw plugin.
    Provides high-speed access to frequently queried nodes, relationships, and query results.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.redis_url = config.get("url", "redis://localhost:6379")
        self.db = config.get("db", 0)
        self.max_connections = config.get("max_connections", 10)
        
        # Cache configuration
        self.default_ttl = config.get("default_ttl", 3600)  # 1 hour
        self.node_ttl = config.get("node_ttl", 7200)  # 2 hours
        self.relationship_ttl = config.get("relationship_ttl", 3600)  # 1 hour
        self.query_ttl = config.get("query_ttl", 1800)  # 30 minutes
        
        # Key prefixes
        self.node_prefix = "caselaw:node:"
        self.relationship_prefix = "caselaw:rel:"
        self.query_prefix = "caselaw:query:"
        self.stats_prefix = "caselaw:stats:"
        
        self._redis_pool: Optional[redis.ConnectionPool] = None
        self._redis: Optional[redis.Redis] = None
        self._initialized = False
        
        # Performance tracking
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            # Create connection pool
            self._redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                db=self.db,
                max_connections=self.max_connections,
                decode_responses=False  # We'll handle encoding/decoding
            )
            
            self._redis = redis.Redis(connection_pool=self._redis_pool)
            
            # Test connection
            await self._redis.ping()
            
            # Initialize cache statistics
            await self._init_cache_stats()
            
            self._initialized = True
            self.logger.info(f"Redis cache initialized: {self.redis_url}")
            
        except ConnectionError as e:
            self.logger.error(f"Redis connection failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis cache: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
        
        if self._redis_pool:
            await self._redis_pool.disconnect()
        
        self._initialized = False
        self.logger.info("Redis cache closed")
    
    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy"""
        return self._initialized and self._redis is not None
    
    async def _init_cache_stats(self):
        """Initialize cache statistics in Redis"""
        stats_key = f"{self.stats_prefix}performance"
        if not await self._redis.exists(stats_key):
            await self._redis.hset(stats_key, mapping=self._cache_stats)
    
    # Node caching
    async def cache_node(self, node: CaselawNode, ttl: Optional[int] = None) -> bool:
        """Cache a node"""
        try:
            key = f"{self.node_prefix}{node.id}"
            
            # Serialize node data
            node_data = {
                "id": node.id,
                "node_type": node.node_type,
                "canonical_id": str(node.canonical_id),
                "properties": node.properties,
                "created_at": node.created_at.isoformat(),
                "updated_at": node.updated_at.isoformat(),
                "provenance_id": node.provenance_id,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            # Use pickle for complex data structures
            serialized_data = pickle.dumps(node_data)
            
            # Set with TTL
            await self._redis.setex(
                key, 
                ttl or self.node_ttl, 
                serialized_data
            )
            
            self._cache_stats["sets"] += 1
            await self._update_cache_stats()
            
            return True
            
        except RedisError as e:
            self.logger.error(f"Failed to cache node {node.id}: {e}")
            self._cache_stats["errors"] += 1
            return False
    
    async def get_node(self, node_id: str) -> Optional[CaselawNode]:
        """Get a cached node"""
        try:
            key = f"{self.node_prefix}{node_id}"
            cached_data = await self._redis.get(key)
            
            if cached_data:
                # Deserialize
                node_data = pickle.loads(cached_data)
                
                # Rebuild node (simplified version)
                self._cache_stats["hits"] += 1
                await self._update_cache_stats()
                
                # Note: In production, you'd reconstruct the full node with provenance
                # For now, returning None to indicate cache miss and fetch from Neo4j
                return None
            
            self._cache_stats["misses"] += 1
            await self._update_cache_stats()
            return None
            
        except (RedisError, pickle.PickleError) as e:
            self.logger.error(f"Failed to get cached node {node_id}: {e}")
            self._cache_stats["errors"] += 1
            return None
    
    async def invalidate_node(self, node_id: str) -> bool:
        """Invalidate a cached node"""
        try:
            key = f"{self.node_prefix}{node_id}"
            deleted = await self._redis.delete(key)
            
            # Also invalidate related relationship caches
            await self.invalidate_node_relationships(node_id)
            
            self._cache_stats["deletes"] += 1
            await self._update_cache_stats()
            
            return deleted > 0
            
        except RedisError as e:
            self.logger.error(f"Failed to invalidate node {node_id}: {e}")
            return False
    
    # Relationship caching
    async def cache_relationships(self, 
                                cache_key: str, 
                                relationships: List[CaseRelationship],
                                ttl: Optional[int] = None) -> bool:
        """Cache relationships for a query"""
        try:
            key = f"{self.relationship_prefix}{cache_key}"
            
            # Serialize relationships
            rel_data = []
            for rel in relationships:
                rel_data.append({
                    "id": rel.id,
                    "source_case_id": rel.source_case_id,
                    "target_case_id": rel.target_case_id,
                    "relationship_type": rel.relationship_type.value,
                    "confidence": rel.confidence,
                    "precedential_strength": rel.precedential_strength,
                    "created_at": rel.created_at.isoformat()
                })
            
            cached_data = {
                "relationships": rel_data,
                "cached_at": datetime.utcnow().isoformat(),
                "count": len(relationships)
            }
            
            serialized_data = pickle.dumps(cached_data)
            
            await self._redis.setex(
                key,
                ttl or self.relationship_ttl,
                serialized_data
            )
            
            self._cache_stats["sets"] += 1
            await self._update_cache_stats()
            
            return True
            
        except RedisError as e:
            self.logger.error(f"Failed to cache relationships {cache_key}: {e}")
            return False
    
    async def get_relationships(self, cache_key: str) -> Optional[List[CaseRelationship]]:
        """Get cached relationships"""
        try:
            key = f"{self.relationship_prefix}{cache_key}"
            cached_data = await self._redis.get(key)
            
            if cached_data:
                data = pickle.loads(cached_data)
                
                self._cache_stats["hits"] += 1
                await self._update_cache_stats()
                
                # Note: In production, you'd reconstruct full CaseRelationship objects
                # For now, return None to indicate cache miss
                return None
            
            self._cache_stats["misses"] += 1
            await self._update_cache_stats()
            return None
            
        except (RedisError, pickle.PickleError) as e:
            self.logger.error(f"Failed to get cached relationships {cache_key}: {e}")
            return None
    
    async def invalidate_node_relationships(self, node_id: str) -> bool:
        """Invalidate all relationship caches involving a node"""
        try:
            # Find all relationship cache keys that involve this node
            pattern = f"{self.relationship_prefix}*{node_id}*"
            
            # Use scan to avoid blocking
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                
                if keys:
                    deleted = await self._redis.delete(*keys)
                    deleted_count += deleted
                
                if cursor == 0:
                    break
            
            return deleted_count > 0
            
        except RedisError as e:
            self.logger.error(f"Failed to invalidate relationships for {node_id}: {e}")
            return False
    
    # Query result caching
    async def cache_query_results(self,
                                cache_key: str,
                                results: Any,
                                ttl: Optional[int] = None) -> bool:
        """Cache query results"""
        try:
            key = f"{self.query_prefix}{cache_key}"
            
            cached_data = {
                "results": results,
                "cached_at": datetime.utcnow().isoformat(),
                "result_type": type(results).__name__
            }
            
            serialized_data = pickle.dumps(cached_data)
            
            await self._redis.setex(
                key,
                ttl or self.query_ttl,
                serialized_data
            )
            
            self._cache_stats["sets"] += 1
            await self._update_cache_stats()
            
            return True
            
        except RedisError as e:
            self.logger.error(f"Failed to cache query results {cache_key}: {e}")
            return False
    
    async def get_query_results(self, cache_key: str) -> Optional[Any]:
        """Get cached query results"""
        try:
            key = f"{self.query_prefix}{cache_key}"
            cached_data = await self._redis.get(key)
            
            if cached_data:
                data = pickle.loads(cached_data)
                
                self._cache_stats["hits"] += 1
                await self._update_cache_stats()
                
                return data["results"]
            
            self._cache_stats["misses"] += 1
            await self._update_cache_stats()
            return None
            
        except (RedisError, pickle.PickleError) as e:
            self.logger.error(f"Failed to get cached query results {cache_key}: {e}")
            return None
    
    # Cache management
    async def _update_cache_stats(self):
        """Update cache statistics"""
        try:
            stats_key = f"{self.stats_prefix}performance"
            await self._redis.hset(stats_key, mapping=self._cache_stats)
        except RedisError:
            pass  # Don't fail operations due to stats updates
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        try:
            stats_key = f"{self.stats_prefix}performance"
            raw_stats = await self._redis.hgetall(stats_key)
            
            # Convert bytes to proper types
            stats = {}
            for key, value in raw_stats.items():
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                if isinstance(value, bytes):
                    value = int(value.decode('utf-8'))
                stats[key] = value
            
            # Calculate derived metrics
            total_requests = stats.get("hits", 0) + stats.get("misses", 0)
            hit_rate = (stats.get("hits", 0) / total_requests * 100) if total_requests > 0 else 0
            
            stats.update({
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
                "last_updated": datetime.utcnow().isoformat()
            })
            
            return stats
            
        except RedisError as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return self._cache_stats
    
    async def cleanup_expired_entries(self) -> Dict[str, int]:
        """Clean up expired cache entries"""
        try:
            cleanup_stats = {
                "nodes_cleaned": 0,
                "relationships_cleaned": 0,
                "queries_cleaned": 0
            }
            
            # Clean up expired nodes
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=f"{self.node_prefix}*", count=100)
                
                for key in keys:
                    ttl = await self._redis.ttl(key)
                    if ttl == -2:  # Key doesn't exist
                        cleanup_stats["nodes_cleaned"] += 1
                
                if cursor == 0:
                    break
            
            # Clean up expired relationships
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=f"{self.relationship_prefix}*", count=100)
                
                for key in keys:
                    ttl = await self._redis.ttl(key)
                    if ttl == -2:  # Key doesn't exist
                        cleanup_stats["relationships_cleaned"] += 1
                
                if cursor == 0:
                    break
            
            # Clean up expired queries
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match=f"{self.query_prefix}*", count=100)
                
                for key in keys:
                    ttl = await self._redis.ttl(key)
                    if ttl == -2:  # Key doesn't exist
                        cleanup_stats["queries_cleaned"] += 1
                
                if cursor == 0:
                    break
            
            self.logger.info(f"Cache cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except RedisError as e:
            self.logger.error(f"Failed to cleanup expired entries: {e}")
            return {"error": str(e)}
    
    async def flush_cache(self, pattern: Optional[str] = None) -> bool:
        """Flush cache entries matching pattern or all caselaw entries"""
        try:
            if pattern:
                # Delete entries matching pattern
                cursor = 0
                deleted_count = 0
                
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                    
                    if keys:
                        deleted = await self._redis.delete(*keys)
                        deleted_count += deleted
                    
                    if cursor == 0:
                        break
                
                self.logger.info(f"Flushed {deleted_count} cache entries matching pattern: {pattern}")
                
            else:
                # Flush all caselaw cache entries
                patterns = [
                    f"{self.node_prefix}*",
                    f"{self.relationship_prefix}*", 
                    f"{self.query_prefix}*"
                ]
                
                total_deleted = 0
                for pattern in patterns:
                    cursor = 0
                    while True:
                        cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                        
                        if keys:
                            deleted = await self._redis.delete(*keys)
                            total_deleted += deleted
                        
                        if cursor == 0:
                            break
                
                self.logger.info(f"Flushed {total_deleted} total cache entries")
            
            return True
            
        except RedisError as e:
            self.logger.error(f"Failed to flush cache: {e}")
            return False
    
    # Advanced caching strategies
    async def cache_precedent_hierarchy(self, 
                                      jurisdiction: str,
                                      hierarchy_data: Dict[str, Any],
                                      ttl: int = 86400) -> bool:  # 24 hours
        """Cache precedent hierarchy for a jurisdiction"""
        try:
            key = f"{self.query_prefix}hierarchy:{jurisdiction}"
            
            cached_data = {
                "jurisdiction": jurisdiction,
                "hierarchy": hierarchy_data,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            serialized_data = pickle.dumps(cached_data)
            await self._redis.setex(key, ttl, serialized_data)
            
            return True
            
        except RedisError as e:
            self.logger.error(f"Failed to cache precedent hierarchy: {e}")
            return False
    
    async def cache_citation_network(self,
                                   network_id: str,
                                   network_data: Dict[str, Any],
                                   ttl: int = 7200) -> bool:  # 2 hours
        """Cache citation network analysis"""
        try:
            key = f"{self.query_prefix}network:{network_id}"
            
            cached_data = {
                "network_id": network_id,
                "network_data": network_data,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            serialized_data = pickle.dumps(cached_data)
            await self._redis.setex(key, ttl, serialized_data)
            
            return True
            
        except RedisError as e:
            self.logger.error(f"Failed to cache citation network: {e}")
            return False
    
    # Monitoring and debugging
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get comprehensive cache information"""
        try:
            info = await self._redis.info()
            stats = await self.get_cache_stats()
            
            # Count cached items by type
            node_count = 0
            rel_count = 0
            query_count = 0
            
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(cursor, match="caselaw:*", count=1000)
                
                for key in keys:
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    
                    if key.startswith(self.node_prefix):
                        node_count += 1
                    elif key.startswith(self.relationship_prefix):
                        rel_count += 1
                    elif key.startswith(self.query_prefix):
                        query_count += 1
                
                if cursor == 0:
                    break
            
            return {
                "redis_info": {
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0)
                },
                "cache_counts": {
                    "nodes": node_count,
                    "relationships": rel_count,
                    "queries": query_count,
                    "total": node_count + rel_count + query_count
                },
                "performance_stats": stats,
                "configuration": {
                    "node_ttl": self.node_ttl,
                    "relationship_ttl": self.relationship_ttl,
                    "query_ttl": self.query_ttl,
                    "max_connections": self.max_connections
                }
            }
            
        except RedisError as e:
            self.logger.error(f"Failed to get cache info: {e}")
            return {"error": str(e)}