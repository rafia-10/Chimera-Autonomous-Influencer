"""
Main entry point for Nova Intellect (Project Chimera).
Orchestrates the Swarm: Planner, Worker, and Judge.
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Core imports
from src.core.planner.service import PlannerService
from src.core.worker.service import WorkerService
from src.core.judge.service import JudgeService
from src.mcp.client import MCPClient
from src.memory.persona import ContextManager
from src.memory.short_term import ShortTermMemoryManager
from src.memory.long_term import LongTermMemoryManager
from src.config import ChimeraConfig

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("Chimera")

async def main():
    """System startup and orchestration."""
    # 1. Load Environment & Config
    load_dotenv()
    config = ChimeraConfig.load()
    agent_id = os.getenv("AGENT_ID", "nova-intellect")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    logger.info(f"🚀 Starting Project Chimera - Agent: {agent_id}")

    # 2. Initialize Shared Dependencies
    mcp_client = MCPClient(config_path="config/mcp_config.json")
    persona_manager = ContextManager(soul_path="SOUL.md")
    short_term_memory = ShortTermMemoryManager(redis_url=redis_url)
    long_term_memory = LongTermMemoryManager()

    # 3. Initialize Swarm Services
    planner = PlannerService(
        agent_id=agent_id,
        redis_url=redis_url,
        mcp_client=mcp_client,
        persona_manager=persona_manager,
        short_term_memory=short_term_memory,
        long_term_memory=long_term_memory,
        config=config
    )

    worker = WorkerService(
        agent_id=agent_id,
        redis_url=redis_url,
        mcp_client=mcp_client,
        config=config
    )

    judge = JudgeService(
        agent_id=agent_id,
        redis_url=redis_url,
        mcp_client=mcp_client,
        config=config
    )

    # 4. Run Services concurrently
    logger.info("Initializing Swarm Services...")
    try:
        await asyncio.gather(
            planner.start(),
            worker.start(),
            judge.start()
        )
    except KeyboardInterrupt:
        logger.info("Shutdown requested via KeyboardInterrupt")
    except Exception as e:
        logger.error(f"Critical System Error: {e}")
    finally:
        # Graceful shutdown
        await planner.stop()
        await worker.stop()
        await judge.stop()
        logger.info("System Offline.")

if __name__ == "__main__":
    asyncio.run(main())
