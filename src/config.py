"""Configuration models and utilities."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server."""
    command: str
    args: List[str] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = None
    description: str = ""


class ResourcePollingConfig(BaseModel):
    """Configuration for resource polling."""
    interval_seconds: int
    relevance_threshold: float = Field(ge=0.0, le=1.0)


class AgentConfig(BaseModel):
    """Main agent configuration."""
    agent_id: str
    agent_name: str
    soul_file: Path


class ChimeraConfig(BaseModel):
    """Complete system configuration."""
    agent_config: AgentConfig
    mcp_servers: Dict[str, MCPServerConfig]
    resource_polling: Dict[str, ResourcePollingConfig]
    
    @classmethod
    def from_file(cls, config_path: Path) -> "ChimeraConfig":
        """Load configuration from JSON file."""
        with open(config_path) as f:
            data = json.load(f)
        return cls(**data)


def load_safety_policies(config_path: Path) -> Dict:
    """Load safety policies from JSON file."""
    with open(config_path) as f:
        return json.load(f)
