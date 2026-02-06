"""
Core Judge service implementation.

Implements the spec in specs/core/judge.spec.md
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from redis.asyncio import Redis
import google.generativeai as genai

from src.memory.persona import ContextManager
from src.mcp.client import MCPClient
from src.models import TaskResult, ValidationResult, ValidationDecision
from src.config import load_safety_policies

logger = logging.getLogger(__name__)


class SafetyCheckResult:
    """Result of safety filter check."""
    SAFE = "safe"
    UNSAFE = "unsafe"
    NEEDS_REVIEW = "needs_review"


class JudgeService:
    """
    Quality assurance and governance layer in the FastRender swarm.
    
    Validates Worker outputs and makes Approve/Reject/Escalate decisions.
    """
    
    def __init__(
        self,
        agent_id: str,
        redis_url: str,
        mcp_client: MCPClient,
        persona_manager: ContextManager,
        safety_policies: Dict,
        gemini_api_key: str,
    ):
        """Initialize the Judge service."""
        self.agent_id = agent_id
        self.redis_url = redis_url
        self.mcp_client = mcp_client
        self.persona = persona_manager
        self.safety_policies = safety_policies
        
        # Initialize Gemini
        genai.configure(api_key=gemini_api_key)
        self.llm = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        self.redis: Optional[Redis] = None
        self.running = False
        
        # Thresholds from safety policies
        self.auto_approve_threshold = safety_policies["confidence_thresholds"]["auto_approve"]
        self.hitl_threshold = safety_policies["confidence_thresholds"]["hitl_review"]
        
        # Dry-run mode
        self.dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
    
    async def connect(self):
        """Connect to Redis."""
        if self.redis is None:
            self.redis = Redis.from_url(self.redis_url, decode_responses=True)
            logger.info("Judge connected to Redis")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            logger.info("Judge disconnected from Redis")
    
    async def start(self):
        """Start the main judge loop."""
        await self.connect()
        self.running = True
        
        logger.info(f"Judge starting for agent {self.agent_id} (dry_run={self.dry_run})")
        
        try:
            while self.running:
                await self._judge_cycle()
        except Exception as e:
            logger.error(f"Judge loop error: {e}", exc_info=True)
        finally:
            await self.disconnect()
    
    async def stop(self):
        """Stop the judge loop."""
        logger.info("Stopping Judge...")
        self.running = False
    
    async def _judge_cycle(self):
        """Execute one judge cycle: pop result, validate, decide."""
        try:
            # Blocking pop from review queue (timeout 5 seconds)
            review_queue_key = f"agent:{self.agent_id}:review_queue"
            result_data = await self.redis.blpop(review_queue_key, timeout=5)
            
            if result_data is None:
                return  # Timeout, try again
            
            _, result_json = result_data
            result = TaskResult.model_validate_json(result_json)
            
            logger.info(f"Judge validating result from task {result.task_id}")
            
            # Validate
            validation = await self.validate_result(result)
            
            # Execute decision
            await self._execute_decision(result, validation)
            
            logger.info(f"Validation complete: {validation.decision} (confidence: {validation.confidence:.2f})")
            
        except Exception as e:
            logger.error(f"Judge cycle error: {e}", exc_info=True)
    
    async def validate_result(self, result: TaskResult) -> ValidationResult:
        """
        Run validation pipeline on a task result.
        
        Returns:
            ValidationResult with decision and confidence
        """
        # Skip validation if task already has an error
        if result.error:
            return ValidationResult(
                decision=ValidationDecision.REJECT,
                confidence=0.0,
                reason=f"Task error: {result.error}",
            )
        
        # 1. OCC conflict check
        if await self.check_occ_conflict(result.state_version):
            return ValidationResult(
                decision=ValidationDecision.REJECT,
                confidence=0.0,
                reason="State version conflict (OCC)",
            )
        
        # 2. Persona alignment
        persona_score = await self._check_persona_alignment(result.output)
        
        # 3. Safety filter
        safety_result = await self._check_safety(result.output)
        
        # 4. Platform compliance  
        platform_ok = await self._check_platform_compliance(result)
        
        # 5. Calculate overall confidence
        confidence = await self._calculate_confidence(
            persona_score=persona_score,
            safety_result=safety_result,
            platform_ok=platform_ok,
        )
        
        # Determine decision
        if safety_result == SafetyCheckResult.UNSAFE:
            decision = ValidationDecision.REJECT
            reason = "Failed safety filter"
        elif not platform_ok:
            decision = ValidationDecision.REJECT
            reason = "Platform compliance violation"
        elif confidence >= self.auto_approve_threshold:
            decision = ValidationDecision.APPROVE
            reason = "High confidence"
        elif confidence >= self.hitl_threshold:
            decision = ValidationDecision.ESCALATE
            reason = "Medium confidence - needs human review"
        else:
            decision = ValidationDecision.REJECT
            reason = "Low confidence"
        
        return ValidationResult(
            decision=decision,
            confidence=confidence,
            reason=reason,
            checks={
                "persona_alignment": persona_score,
                "safety": safety_result,
                "platform_compliant": platform_ok,
            }
        )
    
    async def _check_persona_alignment(self, content: str) -> float:
        """
        Check if content aligns with persona.
        
        Returns:
            Alignment score (0.0-1.0)
        """
        persona_desc = self.persona.persona.to_system_prompt_section()
        
        prompt = f"""{persona_desc}

Does this content match the persona's voice, values, and style?
Content: "{content}"

Rate alignment from 0.0 (completely off-brand) to 1.0 (perfect match).
Respond with ONLY a number."""
        
        try:
            response = await self.llm.generate_content_async(prompt)
            score = float(response.text.strip())
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.error(f"Persona alignment check error: {e}")
            return 0.5  # Default to medium on error
    
    async def _check_safety(self, content: str) -> str:
        """
        Run safety filters on content.
        
        Returns:
            SafetyCheckResult status
        """
        content_lower = content.lower()
        
        # Check banned keywords
        for keyword in self.safety_policies.get("banned_keywords", []):
            if keyword.lower() in content_lower:
                logger.warning(f"Banned keyword detected: {keyword}")
                return SafetyCheckResult.UNSAFE
        
        # Check auto-escalate patterns
        for pattern in self.safety_policies.get("auto_escalate_patterns", []):
            if pattern.lower() in content_lower:
                logger.warning(f"Auto-escalate pattern detected: {pattern}")
                return SafetyCheckResult.NEEDS_REVIEW
        
        # Check sensitive topics (basic keyword matching)
        sensitive_topics = self.safety_policies.get("sensitive_topics", [])
        for topic in sensitive_topics:
            if topic.lower() in content_lower:
                logger.info(f"Sensitive topic detected: {topic}")
                return SafetyCheckResult.NEEDS_REVIEW
        
        return SafetyCheckResult.SAFE
    
    async def _check_platform_compliance(self, result: TaskResult) -> bool:
        """
        Check platform-specific constraints.
        
        Returns:
            True if compliant
        """
        platform = result.metadata.get("platform", "x")
        content = result.output
        
        # Character limits
        limits = self.safety_policies.get("platform_constraints", {}).get(platform, {})
        char_limit = limits.get("character_limit", 280)
        
        if len(content) > char_limit:
            logger.warning(f"Content exceeds {platform} character limit: {len(content)} > {char_limit}")
            return False
        
        return True
    
    async def _calculate_confidence(
        self,
        persona_score: float,
        safety_result: str,
        platform_ok: bool,
    ) -> float:
        """
        Calculate overall confidence score.
        
        Returns:
            Confidence (0.0-1.0)
        """
        # Safety score
        if safety_result == SafetyCheckResult.SAFE:
            safety_score = 1.0
        elif safety_result == SafetyCheckResult.NEEDS_REVIEW:
            safety_score = 0.6
        else:  # UNSAFE
            safety_score = 0.0
        
        # Platform compliance score
        compliance_score = 1.0 if platform_ok else 0.0
        
        # Weighted combination
        confidence = (
            persona_score * 0.3 +
            safety_score * 0.4 +
            compliance_score * 0.3
        )
        
        return confidence
    
    async def check_occ_conflict(self, task_state_version: int) -> bool:
        """
        Check for Optimistic Concurrency Control conflicts.
        
        Returns:
            True if conflict detected
        """
        current_version = await self.redis.get(f"agent:{self.agent_id}:state_version")
        current_version = int(current_version) if current_version else 0
        
        if task_state_version != current_version:
            logger.warning(f"OCC conflict: task version {task_state_version} != current {current_version}")
            return True
        
        return False
    
    async def escalate_to_hitl(self, result: TaskResult, reason: str):
        """Queue result for human review."""
        hitl_item = {
            "result": result.model_dump(),
            "reason": reason,
            "escalated_at": datetime.utcnow().isoformat(),
        }
        
        await self.redis.rpush(
            f"agent:{self.agent_id}:hitl_queue",
            json.dumps(hitl_item)
        )
        
        logger.info(f"Escalated task {result.task_id} to HITL: {reason}")
    
    async def _execute_decision(self, result: TaskResult, validation: ValidationResult):
        """Execute the validation decision."""
        if validation.decision == ValidationDecision.APPROVE:
            await self._approve_and_publish(result)
        elif validation.decision == ValidationDecision.ESCALATE:
            await self.escalate_to_hitl(result, validation.reason)
        else:  # REJECT
            logger.info(f"Rejected task {result.task_id}: {validation.reason}")
            # Could signal Planner to retry, but for now just log
    
    async def _approve_and_publish(self, result: TaskResult):
        """Approve result and execute the action."""
        platform = result.metadata.get("platform", "x")
        content = result.output
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would publish to {platform}: {content}")
            return
        
        # Execute via MCP
        try:
            if platform == "x":
                await self.mcp_client.call_tool(
                    server_name="x",
                    tool_name="post_tweet",
                    arguments={"text": content}
                )
            elif platform == "linkedin":
                await self.mcp_client.call_tool(
                    server_name="linkedin",
                    tool_name="create_post",
                    arguments={"text": content}
                )
            
            logger.info(f"Published to {platform}: {content[:50]}...")
            
        except Exception as e:
            logger.error(f"Publishing error: {e}", exc_info=True)
