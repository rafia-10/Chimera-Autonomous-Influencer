"""
Redis-based short-term (episodic) memory manager.

Stores recent interactions with TTL for automatic expiration.
Used for maintaining conversational context over the last 1-2 hours.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from pydantic import BaseModel, Field


class EpisodicMemory(BaseModel):
    """Represents a single episodic memory entry."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When this interaction occurred")
    interaction_type: str = Field(..., description="Type of interaction (post, reply, mention, etc.)")
    content: str = Field(..., description="The actual content/text")
    platform: Optional[str] = Field(None, description="Platform where interaction occurred")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    def to_summary_string(self) -> str:
        """Convert to human-readable summary for context injection."""
        platform_str = f" on {self.platform}" if self.platform else ""
        time_str = self.timestamp.strftime("%H:%M")
        return f"[{time_str}] {self.interaction_type}{platform_str}: {self.content}"


class ShortTermMemoryManager:
    """
    Manages short-term episodic memory using Redis.
    
    Implements a rolling window of recent interactions with automatic TTL expiration.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0", agent_id: str = "nova"):
        """
        Initialize the short-term memory manager.
        
        Args:
            redis_url: Redis connection URL
            agent_id: Unique identifier for this agent
        """
        self.redis_url = redis_url
        self.agent_id = agent_id
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl_hours = 2  # Memories expire after 2 hours
    
    async def connect(self):
        """Establish connection to Redis."""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    def _make_key(self, timestamp: datetime) -> str:
        """Generate Redis key for a memory entry."""
        ts_str = timestamp.isoformat()
        return f"agent:{self.agent_id}:episodic:{ts_str}"
    
    def _list_key(self) -> str:
        """Generate Redis key for the sorted set of memory timestamps."""
        return f"agent:{self.agent_id}:episodic:index"
    
    async def add_interaction(
        self,
        interaction_type: str,
        content: str,
        platform: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_hours: Optional[int] = None,
    ) -> EpisodicMemory:
        """
        Store a new interaction in short-term memory.
        
        Args:
            interaction_type: Type of interaction (e.g., "posted_tweet", "replied_to_mention")
            content: The actual content text
            platform: Platform where interaction occurred (e.g., "x", "linkedin")
            metadata: Additional context data
            ttl_hours: Custom TTL in hours (defaults to 2 hours)
            
        Returns:
            The created EpisodicMemory object
        """
        await self.connect()
        
        memory = EpisodicMemory(
            interaction_type=interaction_type,
            content=content,
            platform=platform,
            metadata=metadata or {}
        )
        
        # Store the memory with TTL
        key = self._make_key(memory.timestamp)
        ttl_seconds = (ttl_hours or self.default_ttl_hours) * 3600
        
        await self.redis_client.setex(
            key,
            ttl_seconds,
            memory.model_dump_json()
        )
        
        # Add to sorted set index (score = timestamp)
        timestamp_score = memory.timestamp.timestamp()
        await self.redis_client.zadd(
            self._list_key(),
            {key: timestamp_score}
        )
        
        # Set TTL on the index as well
        await self.redis_client.expire(self._list_key(), ttl_seconds)
        
        return memory
    
    async def get_recent(
        self,
        hours: float = 2.0,
        limit: Optional[int] = None,
    ) -> List[EpisodicMemory]:
        """
        Retrieve recent interactions within the specified time window.
        
        Args:
            hours: How far back to retrieve (default: 2 hours)
            limit: Maximum number of memories to return (most recent first)
            
        Returns:
            List of EpisodicMemory objects, sorted by timestamp (newest first)
        """
        await self.connect()
        
        # Calculate cutoff timestamp
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        cutoff_score = cutoff.timestamp()
        
        # Get keys from sorted set within time range
        keys = await self.redis_client.zrangebyscore(
            self._list_key(),
            min=cutoff_score,
            max="+inf",
        )
        
        if not keys:
            return []
        
        # Fetch all memories
        memories = []
        for key in keys:
            data = await self.redis_client.get(key)
            if data:
                memory = EpisodicMemory.model_validate_json(data)
                memories.append(memory)
        
        # Sort by timestamp (newest first)
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        
        # Apply limit if specified
        if limit:
            memories = memories[:limit]
        
        return memories
    
    async def get_recent_summaries(
        self,
        hours: float = 2.0,
        limit: Optional[int] = None,
    ) -> List[str]:
        """
        Get recent interactions as human-readable summary strings.
        
        This is the primary method used for context injection into LLM prompts.
        
        Args:
            hours: How far back to retrieve
            limit: Maximum number of summaries
            
        Returns:
            List of summary strings, formatted for prompt injection
        """
        memories = await self.get_recent(hours=hours, limit=limit)
        return [mem.to_summary_string() for mem in memories]
    
    async def clear_old(self, hours: float = 24.0):
        """
        Manually clear memories older than specified hours.
        
        Note: Redis TTL should handle this automatically, but this provides
        explicit cleanup if needed.
        
        Args:
            hours: Age threshold for deletion
        """
        await self.connect()
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        cutoff_score = cutoff.timestamp()
        
        # Remove old entries from sorted set
        removed_count = await self.redis_client.zremrangebyscore(
            self._list_key(),
            min="-inf",
            max=cutoff_score
        )
        
        return removed_count
    
    async def clear_all(self):
        """Clear all episodic memories for this agent."""
        await self.connect()
        
        # Get all keys
        pattern = f"agent:{self.agent_id}:episodic:*"
        keys = []
        async for key in self.redis_client.scan_iter(match=pattern):
            keys.append(key)
        
        # Delete all
        if keys:
            await self.redis_client.delete(*keys)
        
        return len(keys)


# Singleton instance for easy import
_instance: Optional[ShortTermMemoryManager] = None


def get_short_term_memory(redis_url: str = "redis://localhost:6379/0", agent_id: str = "nova") -> ShortTermMemoryManager:
    """Get or create the singleton ShortTermMemoryManager instance."""
    global _instance
    if _instance is None:
        _instance = ShortTermMemoryManager(redis_url=redis_url, agent_id=agent_id)
    return _instance
