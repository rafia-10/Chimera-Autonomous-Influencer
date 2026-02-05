"""
Core data models for Project Chimera.

Defines the schema for tasks, results, agent state, and other critical data structures
used throughout the Planner-Worker-Judge architecture.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Types of tasks that can be executed by Workers."""
    GENERATE_CONTENT = "generate_content"
    REPLY_COMMENT = "reply_comment"
    PUBLISH_POST = "publish_post"
    ANALYZE_TREND = "analyze_trend"
    FETCH_NEWS = "fetch_news"
    EXECUTE_TRANSACTION = "execute_transaction"


class TaskPriority(str, Enum):
    """Priority levels for task execution."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Current status of a task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETE = "complete"
    FAILED = "failed"
    REJECTED = "rejected"


class Platform(str, Enum):
    """Supported social media platforms."""
    TWITTER = "twitter"  # X
    LINKEDIN = "linkedin"


class ContentType(str, Enum):
    """Types of content that can be generated."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    MULTIMODAL = "multimodal"


class TaskContext(BaseModel):
    """Context information for task execution."""
    goal_description: str = Field(..., description="High-level goal this task contributes to")
    persona_constraints: List[str] = Field(default_factory=list, description="Voice and behavior constraints from SOUL.md")
    required_resources: List[str] = Field(default_factory=list, description="MCP resources needed (e.g., 'mcp://twitter/mentions/123')")
    platform: Optional[Platform] = Field(None, description="Target platform if applicable")
    content_type: Optional[ContentType] = Field(None, description="Type of content to generate")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")


class AgentTask(BaseModel):
    """
    Represents a single atomic task to be executed by a Worker.
    
    This is the core data structure passed from Planner to Worker via the task queue.
    """
    task_id: UUID = Field(default_factory=uuid4, description="Unique task identifier")
    task_type: TaskType = Field(..., description="Type of task to execute")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Execution priority")
    context: TaskContext = Field(..., description="Execution context and requirements")
    assigned_worker_id: Optional[str] = Field(None, description="ID of worker currently executing this task")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Task creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current task status")
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts before failure")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class ValidationResult(BaseModel):
    """Result of Judge validation."""
    is_valid: bool = Field(..., description="Whether the output passes validation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in output quality (0.0-1.0)")
    validation_notes: str = Field(default="", description="Detailed validation reasoning")
    escalate_to_hitl: bool = Field(default=False, description="Whether to escalate to human review")
    failed_constraints: List[str] = Field(default_factory=list, description="List of failed validation constraints")


class TaskResult(BaseModel):
    """
    Result of a Worker's task execution.
    
    This is passed from Worker to Judge via the review queue.
    """
    task_id: UUID = Field(..., description="ID of the associated task")
    worker_id: str = Field(..., description="ID of the worker that executed the task")
    status: TaskStatus = Field(..., description="Execution status")
    output: Dict[str, Any] = Field(default_factory=dict, description="Generated output/artifacts")
    validation: Optional[ValidationResult] = Field(None, description="Judge validation result")
    execution_time_ms: Optional[int] = Field(None, description="Execution duration in milliseconds")
    error_message: Optional[str] = Field(None, description="Error details if execution failed")
    state_version: str = Field(..., description="Version/hash of GlobalState when task started (for OCC)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Result creation timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class AgentGoal(BaseModel):
    """High-level goal defined by the Network Operator."""
    goal_id: UUID = Field(default_factory=uuid4, description="Unique goal identifier")
    description: str = Field(..., description="Natural language goal description")
    target_platform: Optional[Platform] = Field(None, description="Primary platform for this goal")
    active: bool = Field(default=True, description="Whether this goal is currently active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Goal creation timestamp")
    deadline: Optional[datetime] = Field(None, description="Optional completion deadline")
    success_metrics: Dict[str, Any] = Field(default_factory=dict, description="Success criteria")


class GlobalState(BaseModel):
    """
    Central state shared across the swarm.
    
    Managed by the Planner, read by Workers, validated by Judges.
    Uses versioning for Optimistic Concurrency Control.
    """
    state_version: str = Field(..., description="State version hash for OCC")
    active_goals: List[AgentGoal] = Field(default_factory=list, description="Current active goals")
    pending_tasks: int = Field(default=0, description="Number of tasks in queue")
    budget_remaining_usd: float = Field(default=0.0, description="Remaining operational budget")
    last_post_timestamp: Optional[datetime] = Field(None, description="Timestamp of last published post")
    campaign_metadata: Dict[str, Any] = Field(default_factory=dict, description="Campaign-specific data")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last state update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class MCPResource(BaseModel):
    """Represents an MCP Resource identifier."""
    uri: str = Field(..., description="MCP resource URI (e.g., 'news://ethiopia/latest')")
    name: str = Field(..., description="Human-readable resource name")
    description: str = Field(default="", description="Resource description")
    mime_type: Optional[str] = Field(None, description="Resource MIME type")


class MCPTool(BaseModel):
    """Represents an MCP Tool definition."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for tool inputs")


class ContentOutput(BaseModel):
    """Generated content ready for publishing."""
    content_id: UUID = Field(default_factory=uuid4, description="Unique content identifier")
    platform: Platform = Field(..., description="Target platform")
    text: Optional[str] = Field(None, description="Text content")
    media_urls: List[str] = Field(default_factory=list, description="Attached media URLs")
    tags: List[str] = Field(default_factory=list, description="Content tags/hashtags")
    is_reply: bool = Field(default=False, description="Whether this is a reply to another post")
    parent_post_id: Optional[str] = Field(None, description="ID of parent post if reply")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Generation confidence")
    requires_review: bool = Field(default=False, description="Whether HITL review is required")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")


# Type aliases for clarity
TaskQueue = List[AgentTask]
ReviewQueue = List[TaskResult]
