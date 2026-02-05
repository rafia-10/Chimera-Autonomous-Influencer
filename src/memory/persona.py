"""
Persona management and context assembly.

This module handles loading the SOUL.md persona file and assembling
the complete context (persona + memories) for LLM interactions.
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class AgentPersona(BaseModel):
    """
    Parsed SOUL.md persona definition.
    
    This represents the immutable "DNA" of the agent.
    """
    name: str = Field(..., description="Agent's display name")
    id: str = Field(..., description="Unique agent identifier (UUID)")
    niche: str = Field(..., description="Content niche/focus area")
    platforms: List[str] = Field(..., description="Supported platforms")
    voice_traits: List[str] = Field(..., description="Personality and voice characteristics")
    humor_style: str = Field(..., description="Humor and wit style")
    audience: Dict[str, str] = Field(..., description="Target audience per platform")
    hard_rules: List[str] = Field(..., description="Absolute behavioral constraints")
    disclosure_policy: str = Field(..., description="AI identity disclosure policy")
    backstory: str = Field(..., description="Agent's narrative history and purpose")
    
    @classmethod
    def from_soul_file(cls, soul_path: Path) -> "AgentPersona":
        """
        Load and parse a SOUL.md file.
        
        Args:
            soul_path: Path to the SOUL.md file
            
        Returns:
            Parsed AgentPersona instance
            
        Raises:
            FileNotFoundError: If SOUL.md doesn't exist
            ValueError: If SOUL.md is malformed
        """
        if not soul_path.exists():
            raise FileNotFoundError(f"SOUL.md not found at {soul_path}")
        
        content = soul_path.read_text(encoding="utf-8")
        
        # Split frontmatter and backstory
        if not content.startswith("---"):
            raise ValueError("SOUL.md must start with YAML frontmatter (---)")
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("SOUL.md must have valid YAML frontmatter")
        
        frontmatter_text = parts[1]
        backstory_text = parts[2].strip()
        
        # Parse YAML frontmatter
        frontmatter = yaml.safe_load(frontmatter_text)
        
        # Combine frontmatter with backstory
        persona_data = {**frontmatter, "backstory": backstory_text}
        
        return cls(**persona_data)
    
    def to_system_prompt_section(self) -> str:
        """
        Convert persona to a system prompt section.
        
        Returns:
            Formatted prompt text defining the agent's identity
        """
        prompt = f"""# WHO YOU ARE

You are **{self.name}**, an AI influencer focused on {self.niche}.

## Your Voice
{', '.join(self.voice_traits)}

Your humor style: {self.humor_style}

## Your Backstory
{self.backstory}

## Platform Adaptation
"""
        for platform, audience in self.audience.items():
            prompt += f"- **{platform}**: Target audience is {audience}\n"
        
        prompt += f"""
## Hard Rules (NEVER VIOLATE)
"""
        for rule in self.hard_rules:
            prompt += f"- {rule}\n"
        
        prompt += f"""
## Disclosure Policy
{self.disclosure_policy}

---
"""
        return prompt


class ContextManager:
    """
    Manages context assembly for LLM interactions.
    
    Combines SOUL.md persona with retrieved memories to create
    the complete system prompt for each generation.
    """
    
    def __init__(self, soul_path: Path):
        """
        Initialize the context manager.
        
        Args:
            soul_path: Path to the SOUL.md file
        """
        self.soul_path = soul_path
        self.persona = AgentPersona.from_soul_file(soul_path)
        self._persona_hash = self._compute_persona_hash()
    
    def _compute_persona_hash(self) -> str:
        """Compute a hash of the persona for cache invalidation."""
        content = self.soul_path.read_text(encoding="utf-8")
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def reload_if_changed(self) -> bool:
        """
        Check if SOUL.md has been modified and reload if necessary.
        
        Returns:
            True if persona was reloaded, False otherwise
        """
        current_hash = self._compute_persona_hash()
        if current_hash != self._persona_hash:
            self.persona = AgentPersona.from_soul_file(self.soul_path)
            self._persona_hash = current_hash
            return True
        return False
    
    async def assemble_context(
        self,
        input_query: str,
        short_term_memories: Optional[List[str]] = None,
        long_term_memories: Optional[List[str]] = None,
    ) -> str:
        """
        Assemble complete context for LLM generation.
        
        Combines:
        1. SOUL.md persona definition
        2. Short-term episodic memories (recent interactions)
        3. Long-term semantic memories (retrieved from Weaviate)
        
        Args:
            input_query: The current input/task
            short_term_memories: Recent interaction history
            long_term_memories: Semantically relevant past memories
            
        Returns:
            Complete system prompt string
        """
        context_parts = []
        
        # 1. Core persona
        context_parts.append(self.persona.to_system_prompt_section())
        
        # 2. Short-term memory (episodic)
        if short_term_memories:
            context_parts.append("# RECENT CONTEXT (Last 1-2 hours)\n")
            for memory in short_term_memories:
                context_parts.append(f"- {memory}\n")
            context_parts.append("\n")
        
        # 3. Long-term memory (semantic)
        if long_term_memories:
            context_parts.append("# WHAT YOU REMEMBER (Relevant past experiences)\n")
            for memory in long_term_memories:
                context_parts.append(f"- {memory}\n")
            context_parts.append("\n")
        
        # 4. Current task
        context_parts.append(f"# CURRENT TASK\n{input_query}\n")
        
        return "".join(context_parts)
    
    def get_persona_constraints(self) -> List[str]:
        """
        Extract persona constraints for task validation.
        
        Returns:
            List of hard rules and voice traits
        """
        return self.persona.hard_rules + [
            f"Voice must be: {', '.join(self.persona.voice_traits)}",
            f"Humor style: {self.persona.humor_style}",
        ]
