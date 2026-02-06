"""
Core Worker service implementation.

Implements the spec in specs/core/worker.spec.md
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional

from redis.asyncio import Redis
import google.generativeai as genai

from src.memory.persona import ContextManager
from src.memory.short_term import ShortTermMemoryManager
from src.memory.long_term import LongTermMemoryManager
from src.mcp.client import MCPClient
from src.models import AgentTask, TaskResult, TaskType
from src.generation.content_engine import ContentEngine

logger = logging.getLogger(__name__)


class WorkerService:
    """
    Stateless task executor in the FastRender swarm.
    
    Workers pull tasks, execute them, and return results for validation.
    """
    
    def __init__(
        self,
        agent_id: str,
        worker_id: str,
        redis_url: str,
        mcp_client: MCPClient,
        persona_manager: ContextManager,
        short_term_memory: ShortTermMemoryManager,
        long_term_memory: LongTermMemoryManager,
        gemini_api_key: str,
    ):
        """Initialize the Worker service."""
        self.agent_id = agent_id
        self.worker_id = worker_id
        self.redis_url = redis_url
        self.mcp_client = mcp_client
        self.persona = persona_manager
        self.short_term = short_term_memory
        self.long_term = long_term_memory
        
        # Initialize Gemini
        genai.configure(api_key=gemini_api_key)
        self.llm = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        # Initialize content engine
        self.content_engine = ContentEngine(
            persona_manager=persona_manager,
            llm=self.llm,
        )
        
        self.redis: Optional[Redis] = None
        self.running = False
        
        # Task timeout
        self.task_timeout_seconds = 60
    
    async def connect(self):
        """Connect to Redis."""
        if self.redis is None:
            self.redis = Redis.from_url(self.redis_url, decode_responses=True)
            logger.info(f"Worker {self.worker_id} connected to Redis")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            logger.info(f"Worker {self.worker_id} disconnected from Redis")
    
    async def start(self):
        """Start the main worker loop."""
        await self.connect()
        self.running = True
        
        logger.info(f"Worker {self.worker_id} starting for agent {self.agent_id}")
        
        try:
            while self.running:
                await self._work_cycle()
        except Exception as e:
            logger.error(f"Worker loop error: {e}", exc_info=True)
        finally:
            await self.disconnect()
    
    async def stop(self):
        """Stop the worker loop."""
        logger.info(f"Stopping Worker {self.worker_id}...")
        self.running = False
    
    async def _work_cycle(self):
        """Execute one work cycle: pop task, execute, queue result."""
        try:
            # Blocking pop from task queue (timeout 5 seconds)
            task_queue_key = f"agent:{self.agent_id}:task_queue"
            result = await self.redis.blpop(task_queue_key, timeout=5)
            
            if result is None:
                return  # Timeout, try again
            
            _, task_json = result
            task = AgentTask.model_validate_json(task_json)
            
            logger.info(f"Worker {self.worker_id} executing task {task.task_id}")
            
            # Execute with timeout
            task_result = await asyncio.wait_for(
                self.execute_task(task),
                timeout=self.task_timeout_seconds
            )
            
            # Queue result for Judge
            await self._queue_result(task_result)
            
            logger.info(f"Task {task.task_id} completed")
            
        except asyncio.TimeoutError:
            logger.error(f"Task {task.task_id} timed out")
            # Queue error result
            error_result = TaskResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                output="",
                error="Task execution timeout",
                state_version=task.state_version,
            )
            await self._queue_result(error_result)
            
        except Exception as e:
            logger.error(f"Work cycle error: {e}", exc_info=True)
    
    async def execute_task(self, task: AgentTask) -> TaskResult:
        """
        Execute a single task.
        
        Routes to specialized handlers based on task_type.
        """
        try:
            # Route to handler
            if task.task_type == TaskType.GENERATE_POST:
                output = await self._handle_generate_post(task)
            elif task.task_type == TaskType.GENERATE_REPLY:
                output = await self._handle_generate_reply(task)
            elif task.task_type == TaskType.ANALYZE_TREND:
                output = await self._handle_analyze_trend(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            return TaskResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                output=output,
                state_version=task.state_version,
                metadata=task.data,
            )
            
        except Exception as e:
            logger.error(f"Task execution error: {e}", exc_info=True)
            return TaskResult(
                task_id=task.task_id,
                worker_id=self.worker_id,
                output="",
                error=str(e),
                state_version=task.state_version,
            )
    
    async def _handle_generate_post(self, task: AgentTask) -> str:
        """
        Generate a social media post.
        
        Platform-specific tone adaptation applied.
        """
        topic = task.data.get("topic", "tech innovation")
        platform = task.platform
        
        # Assemble context
        context = await self.persona.assemble_context(
            input_query=f"Create a post about: {topic}",
            short_term_manager=self.short_term,
            long_term_manager=self.long_term,
        )
        
        # Generate content using content engine
        content = await self.content_engine.generate_post(
            topic=topic,
            platform=platform,
            context=context,
        )
        
        return content
    
    async def _handle_generate_reply(self, task: AgentTask) -> str:
        """Generate a reply to a mention/comment."""
        mention_text = task.data.get("mention_text", "")
        mention_author = task.data.get("mention_author", "user")
        
        # Assemble context
        context = await self.persona.assemble_context(
            input_query=f"Reply to @{mention_author}: {mention_text}",
            short_term_manager=self.short_term,
            long_term_manager=self.long_term,
        )
        
        # Generate reply
        reply = await self.content_engine.generate_reply(
            mention_text=mention_text,
            mention_author=mention_author,
            platform=task.platform,
            context=context,
        )
        
        return reply
    
    async def _handle_analyze_trend(self, task: AgentTask) -> str:
        """Analyze a cluster of articles for trending topics."""
        articles = task.data.get("articles", [])
        
        if not articles:
            return "No articles to analyze"
        
        # Build analysis prompt
        articles_text = "\n\n".join([
            f"Title: {a.get('title', 'Untitled')}\nSummary: {a.get('summary', '')}"
            for a in articles
        ])
        
        prompt = f"""Analyze these related tech articles and provide:
1. Main theme/topic
2. Key insights
3. Content opportunity (angle for a post)

Articles:
{articles_text}

Provide concise analysis."""
        
        response = await self.llm.generate_content_async(prompt)
        return response.text
    
    async def _queue_result(self, result: TaskResult):
        """Push result to review queue for Judge."""
        result_json = result.model_dump_json()
        review_queue_key = f"agent:{self.agent_id}:review_queue"
        await self.redis.rpush(review_queue_key, result_json)
        logger.debug(f"Queued result for task {result.task_id}")
