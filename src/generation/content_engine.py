"""
Content generation engine.

Handles platform-specific content generation with persona alignment.
"""

import logging
from typing import Optional

import google.generativeai as genai

from src.memory.persona import ContextManager

logger = logging.getLogger(__name__)


class ContentEngine:
    """
    Core content generation with LLM.
    
    Handles platform adaptation and persona-aligned prompting.
    """
    
    def __init__(
        self,
        persona_manager: ContextManager,
        llm: genai.GenerativeModel,
    ):
        """Initialize content engine."""
        self.persona = persona_manager
        self.llm = llm
        
        # Platform constraints
        self.platform_limits = {
            "x": 280,
            "linkedin": 3000,
        }
    
    async def generate_post(
        self,
        topic: str,
        platform: str,
        context: str,
    ) -> str:
        """
        Generate a platform-specific post.
        
        Args:
            topic: What to post about
            platform: Target platform ("x" or "linkedin")
            context: Full context (persona + memories)
            
        Returns:
            Generated post text
        """
        char_limit = self.platform_limits.get(platform, 280)
        
        # Platform-specific instructions
        if platform == "x":
            platform_guide = """
Style for X (Twitter):
- Short and punchy (max 280 characters)
- Witty, engaging, scroll-stopping
- Use emojis strategically (1-2 max)
- Hashtags optional but minimal (#AI, #Tech)
- Hook readers in first 5 words
"""
        else:  # LinkedIn
            platform_guide = """
Style for LinkedIn:
- Professional yet conversational (max 3000 characters)
- Insightful, thought-provoking
- Minimal or no emojis
- No hashtags or very subtle
- Start with a strong statement or question
- Provide value/insights
"""
        
        prompt = f"""{context}

{platform_guide}

Topic: {topic}

Create a {platform} post that matches your persona perfectly. Be authentic, engaging, and provide value."""
        
        response = await self.llm.generate_content_async(prompt)
        content = response.text.strip()
        
        # Enforce character limit
        if len(content) > char_limit:
            content = content[:char_limit-3] + "..."
            logger.warning(f"Content truncated to {char_limit} chars")
        
        return content
    
    async def generate_reply(
        self,
        mention_text: str,
        mention_author: str,
        platform: str,
        context: str,
    ) -> str:
        """
        Generate a reply to a mention/comment.
        
        Args:
            mention_text: The original mention text
            mention_author: Author of the mention
            platform: Target platform
            context: Full context (persona + memories)
            
        Returns:
            Generated reply text
        """
        char_limit = self.platform_limits.get(platform, 280)
        
        prompt = f"""{context}

Someone mentioned you on {platform}:
@{mention_author}: "{mention_text}"

Reply guidelines:
- Be friendly and engaging
- Acknowledge their point
- Add value to the conversation
- Stay true to your persona
- Keep it under {char_limit} characters

Your reply:"""
        
        response = await self.llm.generate_content_async(prompt)
        reply = response.text.strip()
        
        # Enforce character limit
        if len(reply) > char_limit:
            reply = reply[:char_limit-3] + "..."
        
        return reply
    
    async def calculate_confidence(
        self,
        content: str,
        persona_description: str,
    ) -> float:
        """
        Self-assess content quality and persona alignment.
        
        Args:
            content: Generated content to assess
            persona_description: Description of persona to match
            
        Returns:
            Confidence score (0.0-1.0)
        """
        prompt = f"""Rate how well this content matches the persona (0.0-1.0):

Persona:
{persona_description}

Content:
"{content}"

Provide ONLY a number between 0.0 and 1.0, nothing else."""
        
        try:
            response = await self.llm.generate_content_async(prompt)
            score_text = response.text.strip()
            score = float(score_text)
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
        except Exception as e:
            logger.error(f"Confidence calculation error: {e}")
            return 0.5  # Default to medium confidence on error
