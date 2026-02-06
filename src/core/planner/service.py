"""
Core Planner service implementation.

Implements the spec in specs/core/planner.spec.md
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from redis.asyncio import Redis

from src.memory.persona import ContextManager
from src.memory.short_term import ShortTermMemoryManager
from src.memory.long_term import LongTermMemoryManager
from src.mcp.client import MCPClient
from src.models import AgentTask, TaskType, TrendAlert
from src.config import ChimeraConfig

logger = logging.getLogger(__name__)


class PlannerService:
    """
    Strategic planner that monitors global state and generates tasks.
    
    Part of the FastRender swarm architecture.
    """
    
    def __init__(
        self,
        agent_id: str,
        redis_url: str,
        mcp_client: MCPClient,
        persona_manager: ContextManager,
        short_term_memory: ShortTermMemoryManager,
        long_term_memory: LongTermMemoryManager,
        config: ChimeraConfig,
    ):
        """Initialize the Planner service."""
        self.agent_id = agent_id
        self.redis_url = redis_url
        self.mcp_client = mcp_client
        self.persona = persona_manager
        self.short_term = short_term_memory
        self.long_term = long_term_memory
        self.config = config
        
        self.redis: Optional[Redis] = None
        self.running = False
        
        # Planning interval
        self.planning_interval_seconds = 30
    
    async def connect(self):
        """Connect to Redis."""
        if self.redis is None:
            self.redis = Redis.from_url(self.redis_url, decode_responses=True)
            logger.info("Planner connected to Redis")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            logger.info("Planner disconnected from Redis")
    
    async def start(self):
        """Start the main planning loop."""
        await self.connect()
        self.running = True
        
        logger.info(f"Planner starting for agent {self.agent_id}")
        
        try:
            while self.running:
                await self._planning_cycle()
                await asyncio.sleep(self.planning_interval_seconds)
        except Exception as e:
            logger.error(f"Planner loop error: {e}", exc_info=True)
        finally:
            await self.disconnect()
    
    async def stop(self):
        """Stop the planning loop."""
        logger.info("Stopping Planner...")
        self.running = False
    
    async def _planning_cycle(self):
        """Execute one planning cycle."""
        try:
            # 1. Check for trending topics
            trends = await self.detect_trending_topics()
            if trends:
                logger.info(f"Detected {len(trends)} trends")
                await self._create_trend_tasks(trends)
            
            # 2. Check for mentions/comments to reply to
            await self._create_reply_tasks()
            
            # 3. Check time-based triggers (daily content, etc.)
            await self._check_scheduled_content()
            
            logger.debug("Planning cycle complete")
            
        except Exception as e:
            logger.error(f"Planning cycle error: {e}", exc_info=True)
    
    async def detect_trending_topics(self) -> List[TrendAlert]:
        """
        Analyze news resources for emerging trends.
        
        Returns:
            List of detected trends worthy of content creation
        """
        try:
            # Read news resources via MCP
            news_data = await self.mcp_client.read_resource("news", "news://tech/latest")
            
            # TODO: Implement trend clustering with LLM
            # For now, return empty (will implement after LLM integration)
            return []
            
        except Exception as e:
            logger.warning(f"Trend detection failed: {e}")
            return []
    
    async def _create_trend_tasks(self, trends: List[TrendAlert]):
        """Create tasks for trending topics."""
        for trend in trends:
            task = AgentTask(
                task_id=f"trend_{trend.topic}_{datetime.utcnow().timestamp()}",
                task_type=TaskType.GENERATE_POST,
                platform="x",  # Prioritize X for trending topics
                data={
                    "topic": trend.topic,
                    "articles": trend.related_articles,
                    "urgency": "high",
                },
                state_version=await self._get_state_version(),
            )
            
            await self._queue_task(task)
            logger.info(f"Queued trend task: {trend.topic}")
    
    async def _create_reply_tasks(self):
        """Create tasks for replying to mentions."""
        try:
            # Read mentions via MCP
            mentions_data = await self.mcp_client.read_resource("x", "x://mentions/recent")
            
            # TODO: Parse mentions and create reply tasks
            # For now, skip (will implement with full MCP integration)
            
        except Exception as e:
            logger.warning(f"Reply task creation failed: {e}")
    
    async def _check_scheduled_content(self):
        """Check for time-based content triggers."""
        current_hour = datetime.utcnow().hour
        
        # Example: Post daily insight at 9am UTC
        if current_hour == 9:
            last_post = await self._get_last_scheduled_post_time()
            if last_post is None or (datetime.utcnow() - last_post) > timedelta(hours=23):
                await self.plan_daily_content()
    
    async def plan_daily_content(self) -> List[AgentTask]:
        """
        Generate daily posting schedule.
        
        Returns:
            List of scheduled content tasks
        """
        logger.info("Planning daily content...")
        
        # TODO: Implement with LLM
        # For now, return empty
        return []
    
    async def _queue_task(self, task: AgentTask):
        """Push task to Redis queue for Workers."""
        task_json = task.model_dump_json()
        await self.redis.rpush(f"agent:{self.agent_id}:task_queue", task_json)
        logger.debug(f"Queued task {task.task_id}")
    
    async def _get_state_version(self) -> int:
        """Get current global state version (for OCC)."""
        version = await self.redis.get(f"agent:{self.agent_id}:state_version")
        return int(version) if version else 0
    
    async def update_global_state(self, updates: Dict[str, Any]) -> int:
        """
        Update global state with OCC versioning.
        
        Returns:
            New state version
        """
        async with self.redis.pipeline(transaction=True) as pipe:
            # Increment version
            await pipe.incr(f"agent:{self.agent_id}:state_version")
            
            # Apply updates
            for key, value in updates.items():
                await pipe.hset(
                    f"agent:{self.agent_id}:global_state",
                    key,
                    str(value)
                )
            
            results = await pipe.execute()
            new_version = results[0]  # First result is INCR
            
            logger.info(f"Global state updated to version {new_version}")
            return new_version
    
    async def _get_last_scheduled_post_time(self) -> Optional[datetime]:
        """Get timestamp of last scheduled post."""
        timestamp = await self.redis.get(f"agent:{self.agent_id}:last_scheduled_post")
        if timestamp:
            return datetime.fromisoformat(timestamp)
        return None
