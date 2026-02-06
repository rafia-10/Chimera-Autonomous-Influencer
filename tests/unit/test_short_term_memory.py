"""
Unit tests for short-term memory (Redis) functionality.

Tests the ShortTermMemoryManager against the spec in specs/memory/short_term.spec.md
"""

import asyncio
from datetime import datetime, timedelta
from typing import List

import pytest
from redis.asyncio import Redis

from src.memory.short_term import ShortTermMemoryManager, EpisodicMemory


@pytest.fixture
async def redis_client():
    """Fixture to provide test Redis client."""
    client = Redis.from_url("redis://localhost:6379/15", decode_responses=True)
    
    # Clear test database before each test
    await client.flushdb()
    
    yield client
    
    # Cleanup after test
    await client.flushdb()
    await client.aclose()


@pytest.fixture
async def memory_manager(redis_client):
    """Fixture to provide ShortTermMemoryManager instance."""
    manager = ShortTermMemoryManager(
        redis_url="redis://localhost:6379/15",
        agent_id="test_agent"
    )
    await manager.connect()
    
    yield manager
    
    await manager.disconnect()


@pytest.mark.asyncio
class TestConnectionManagement:
    """Test connection lifecycle."""
    
    async def test_connect_establishes_connection(self, memory_manager):
        """Test that connect() establishes Redis connection."""
        # Connection established in fixture
        assert memory_manager.redis is not None
        
        # Verify connection works
        result = await memory_manager.redis.ping()
        assert result is True
    
    async def test_multiple_connects_are_idempotent(self, memory_manager):
        """Test that calling connect() multiple times is safe."""
        await memory_manager.connect()
        await memory_manager.connect()
        
        # Should still work
        result = await memory_manager.redis.ping()
        assert result is True
    
    async def test_disconnect_closes_connection(self, memory_manager):
        """Test that disconnect() closes Redis connection."""
        await memory_manager.disconnect()
        
        # Further operations should fail
        with pytest.raises(Exception):
            await memory_manager.redis.ping()


@pytest.mark.asyncio
class TestMemoryStorage:
    """Test memory storage operations."""
    
    async def test_add_interaction_stores_memory(self, memory_manager):
        """Test that add_interaction() stores memory successfully."""
        memory = await memory_manager.add_interaction(
            interaction_type="posted_tweet",
            content="Test tweet about AI",
            platform="x"
        )
        
        assert memory.interaction_type == "posted_tweet"
        assert memory.content == "Test tweet about AI"
        assert memory.platform == "x"
        assert memory.timestamp is not None
    
    async def test_memory_has_correct_ttl(self, memory_manager, redis_client):
        """Test that stored memory has correct TTL."""
        memory = await memory_manager.add_interaction(
            interaction_type="posted_tweet",
            content="Test content",
            ttl_hours=1
        )
        
        # Check TTL on the Redis key
        key = f"agent:test_agent:episodic:{memory.timestamp.isoformat()}"
        ttl_seconds = await redis_client.ttl(key)
        
        # Should be approximately 1 hour (3600 seconds), with some tolerance
        assert 3500 < ttl_seconds <= 3600
    
    async def test_memory_appears_in_sorted_set_index(self, memory_manager, redis_client):
        """Test that memory is indexed in sorted set."""
        memory = await memory_manager.add_interaction(
            interaction_type="posted_tweet",
            content="Test content"
        )
        
        # Check sorted set index
        index_key = "agent:test_agent:episodic:index"
        members = await redis_client.zrange(index_key, 0, -1)
        
        expected_member = f"agent:test_agent:episodic:{memory.timestamp.isoformat()}"
        assert expected_member in members


@pytest.mark.asyncio
class TestMemoryRetrieval:
    """Test memory retrieval operations."""
    
    async def test_get_recent_returns_memories_within_time_window(self, memory_manager):
        """Test that get_recent() returns only memories within time window."""
        # Add memories at different times
        now = datetime.utcnow()
        
        # Recent memory (30 minutes ago)
        recent_memory = EpisodicMemory(
            timestamp=now - timedelta(minutes=30),
            interaction_type="posted_tweet",
            content="Recent tweet",
        )
        await memory_manager._store_memory(recent_memory)
        
        # Old memory (3 hours ago) - outside 2-hour window
        old_memory = EpisodicMemory(
            timestamp=now - timedelta(hours=3),
            interaction_type="posted_tweet",
            content="Old tweet",
        )
        await memory_manager._store_memory(old_memory)
        
        # Retrieve recent (last 2 hours)
        memories = await memory_manager.get_recent(hours=2.0)
        
        # Should only get the recent one
        assert len(memories) == 1
        assert memories[0].content == "Recent tweet"
    
    async def test_memories_sorted_newest_first(self, memory_manager):
        """Test that get_recent() returns memories sorted newest first."""
        # Add multiple memories
        await memory_manager.add_interaction("posted_tweet", "First")
        await asyncio.sleep(0.1)  # Small delay to ensure different timestamps
        await memory_manager.add_interaction("posted_tweet", "Second")
        await asyncio.sleep(0.1)
        await memory_manager.add_interaction("posted_tweet", "Third")
        
        memories = await memory_manager.get_recent()
        
        assert len(memories) == 3
        assert memories[0].content == "Third"  # Newest first
        assert memories[1].content == "Second"
        assert memories[2].content == "First"
    
    async def test_respects_limit_parameter(self, memory_manager):
        """Test that get_recent() respects limit parameter."""
        # Add 10 memories
        for i in range(10):
            await memory_manager.add_interaction("posted_tweet", f"Tweet {i}")
            await asyncio.sleep(0.01)
        
        # Retrieve with limit=5
        memories = await memory_manager.get_recent(limit=5)
        
        assert len(memories) == 5
    
    async def test_returns_empty_list_when_no_memories(self, memory_manager):
        """Test that get_recent() returns empty list when no memories exist."""
        memories = await memory_manager.get_recent()
        
        assert memories == []


@pytest.mark.asyncio
class TestSummaryFormatting:
    """Test summary formatting for LLM context."""
    
    async def test_get_recent_summaries_formats_correctly(self, memory_manager):
        """Test that summaries are formatted correctly."""
        await memory_manager.add_interaction(
            interaction_type="posted_tweet",
            content="AI just did something wild",
            platform="x"
        )
        
        summaries = await memory_manager.get_recent_summaries()
        
        assert len(summaries) == 1
        summary = summaries[0]
        
        # Should include time, type, platform, and content
        assert "posted_tweet" in summary
        assert "x" in summary
        assert "AI just did something wild" in summary
    
    async def test_summaries_include_metadata(self, memory_manager):
        """Test that summaries include metadata when present."""
        await memory_manager.add_interaction(
            interaction_type="received_mention",
            content="Great post!",
            platform="x",
            metadata={"author": "@test_user", "engagement": "high"}
        )
        
        summaries = await memory_manager.get_recent_summaries()
        
        assert len(summaries) == 1
        # Metadata should be represented in summary
        assert "test_user" in summaries[0] or "@test_user" in summaries[0]


@pytest.mark.asyncio
class TestTTLExpiration:
    """Test TTL expiration behavior."""
    
    async def test_memories_expire_after_ttl(self, memory_manager, redis_client):
        """Test that memories auto-expire after TTL."""
        # Add memory with very short TTL (1 second)
        memory = await memory_manager.add_interaction(
            interaction_type="test",
            content="Short-lived",
            ttl_hours=1/3600  # 1 second
        )
        
        # Memory should exist immediately
        key = f"agent:test_agent:episodic:{memory.timestamp.isoformat()}"
        exists = await redis_client.exists(key)
        assert exists == 1
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Memory should be gone
        exists = await redis_client.exists(key)
        assert exists == 0
    
    async def test_expired_memories_not_returned_by_get_recent(self, memory_manager):
        """Test that expired memories are not returned by get_recent()."""
        # Add memory with short TTL
        await memory_manager.add_interaction(
            interaction_type="test",
            content="Will expire",
            ttl_hours=1/3600  # 1 second
        )
        
        # Should be retrievable immediately
        memories = await memory_manager.get_recent()
        assert len(memories) == 1
        
        # Wait for expiration
        await asyncio.sleep(2)
        
        # Should not be returned anymore
        memories = await memory_manager.get_recent()
        assert len(memories) == 0
