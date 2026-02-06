"""
Weaviate-based long-term (semantic) memory manager.

Stores agent memories with vector embeddings for semantic retrieval.
Enables the agent to recall relevant past experiences based on context.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery
from pydantic import BaseModel, Field


class SemanticMemory(BaseModel):
    """Represents a long-term semantic memory."""
    memory_id: UUID = Field(default_factory=uuid4, description="Unique memory identifier")
    content: str = Field(..., description="Memory content text")
    memory_type: str = Field(..., description="Type of memory (post, interaction, insight, etc.)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When memory was created")
    platform: Optional[str] = Field(None, description="Platform associated with this memory")
    engagement_score: float = Field(default=0.0, description="How well this memory performed (for posts)")
    tags: List[str] = Field(default_factory=list, description="Categorical tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class LongTermMemoryManager:
    """
    Manages long-term semantic memory using Weaviate vector database.
    
    Enables semantic search to retrieve contextually relevant past memories.
    """
    
    COLLECTION_NAME = "AgentMemory"
    
    def __init__(
        self,
        weaviate_url: str = "http://localhost:8080",
        weaviate_api_key: Optional[str] = None,
        agent_id: str = "nova",
    ):
        """
        Initialize the long-term memory manager.
        
        Args:
            weaviate_url: Weaviate instance URL
            weaviate_api_key: API key for Weaviate Cloud (optional for local)
            agent_id: Unique identifier for this agent
        """
        self.weaviate_url = weaviate_url
        self.weaviate_api_key = weaviate_api_key
        self.agent_id = agent_id
        self.client: Optional[weaviate.WeaviateClient] = None
    
    def connect(self):
        """Establish connection to Weaviate and ensure schema exists."""
        if self.client is not None:
            return  # Already connected
        
        # Connect to Weaviate
        if self.weaviate_api_key:
            self.client = weaviate.connect_to_weaviate_cloud(
                cluster_url=self.weaviate_url,
                auth_credentials=weaviate.auth.AuthApiKey(self.weaviate_api_key),
            )
        else:
            self.client = weaviate.connect_to_local(
                host=self.weaviate_url.replace("http://", "").replace("https://", "")
            )
        
        # Ensure collection exists
        self._ensure_schema()
    
    def disconnect(self):
        """Close Weaviate connection."""
        if self.client:
            self.client.close()
            self.client = None
    
    def _ensure_schema(self):
        """Create the AgentMemory collection if it doesn't exist."""
        if self.client.collections.exists(self.COLLECTION_NAME):
            return
        
        # Create collection with vectorizer
        self.client.collections.create(
            name=self.COLLECTION_NAME,
            description="Long-term semantic memories for AI agents",
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(),
            properties=[
                Property(name="agent_id", data_type=DataType.TEXT, description="Agent identifier"),
                Property(name="content", data_type=DataType.TEXT, description="Memory content"),
                Property(name="memory_type", data_type=DataType.TEXT, description="Type of memory"),
                Property(name="timestamp", data_type=DataType.DATE, description="Creation timestamp"),
                Property(name="platform", data_type=DataType.TEXT, description="Associated platform"),
                Property(name="engagement_score", data_type=DataType.NUMBER, description="Performance metric"),
                Property(name="tags", data_type=DataType.TEXT_ARRAY, description="Category tags"),
            ]
        )
    
    def store_memory(
        self,
        content: str,
        memory_type: str,
        platform: Optional[str] = None,
        engagement_score: float = 0.0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """
        Store a new memory in the vector database.
        
        Args:
            content: The memory content/text
            memory_type: Type of memory (e.g., "successful_post", "high_engagement_reply")
            platform: Platform where this occurred
            engagement_score: Normalized engagement metric (0.0-1.0)
            tags: Categorical tags for filtering
            metadata: Additional context (stored but not vectorized)
            
        Returns:
            UUID of the created memory
        """
        self.connect()
        
        memory = SemanticMemory(
            content=content,
            memory_type=memory_type,
            platform=platform,
            engagement_score=engagement_score,
            tags=tags or [],
            metadata=metadata or {},
        )
        
        collection = self.client.collections.get(self.COLLECTION_NAME)
        
        # Insert into Weaviate
        uuid = collection.data.insert(
            properties={
                "agent_id": self.agent_id,
                "content": memory.content,
                "memory_type": memory.memory_type,
                "timestamp": memory.timestamp.isoformat(),
                "platform": memory.platform,
                "engagement_score": memory.engagement_score,
                "tags": memory.tags,
            }
        )
        
        return UUID(uuid)
    
    def search_memories(
        self,
        query: str,
        limit: int = 5,
        memory_type_filter: Optional[str] = None,
        platform_filter: Optional[str] = None,
        min_engagement: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search for relevant memories.
        
        This is the primary method for memory retrieval during context assembly.
        
        Args:
            query: Natural language query (e.g., current task description)
            limit: Maximum number of memories to return
            memory_type_filter: Optional filter by memory type
            platform_filter: Optional filter by platform
            min_engagement: Optional minimum engagement score threshold
            
        Returns:
            List of memory dictionaries with content and metadata
        """
        self.connect()
        
        collection = self.client.collections.get(self.COLLECTION_NAME)
        
        # Build filters
        filters = weaviate.classes.query.Filter.by_property("agent_id").equal(self.agent_id)
        
        if memory_type_filter:
            filters = filters & weaviate.classes.query.Filter.by_property("memory_type").equal(memory_type_filter)
        
        if platform_filter:
            filters = filters & weaviate.classes.query.Filter.by_property("platform").equal(platform_filter)
        
        if min_engagement is not None:
            filters = filters & weaviate.classes.query.Filter.by_property("engagement_score").greater_or_equal(min_engagement)
        
        # Execute semantic search
        response = collection.query.near_text(
            query=query,
            limit=limit,
            filters=filters,
            return_metadata=MetadataQuery(distance=True)
        )
        
        # Format results
        memories = []
        for obj in response.objects:
            memories.append({
                "content": obj.properties.get("content"),
                "memory_type": obj.properties.get("memory_type"),
                "timestamp": obj.properties.get("timestamp"),
                "platform": obj.properties.get("platform"),
                "engagement_score": obj.properties.get("engagement_score"),
                "tags": obj.properties.get("tags", []),
                "distance": obj.metadata.distance,  # Semantic similarity (lower = more similar)
            })
        
        return memories
    
    def get_memory_summaries(
        self,
        query: str,
        limit: int = 5,
        **kwargs
    ) -> List[str]:
        """
        Get memory summaries formatted for prompt injection.
        
        Args:
            query: Search query
            limit: Maximum memories to retrieve
            **kwargs: Additional filters (memory_type_filter, platform_filter, etc.)
            
        Returns:
            List of formatted memory strings
        """
        memories = self.search_memories(query, limit=limit, **kwargs)
        
        summaries = []
        for mem in memories:
            timestamp = mem.get("timestamp", "unknown time")
            content = mem.get("content", "")
            mem_type = mem.get("memory_type", "memory")
            platform = mem.get("platform")
            
            platform_str = f" on {platform}" if platform else ""
            summary = f"[{mem_type}{platform_str}] {content}"
            summaries.append(summary)
        
        return summaries
    
    def get_high_performing_memories(
        self,
        limit: int = 10,
        min_engagement: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve high-performing past content for learning.
        
        Useful for understanding what content resonates with the audience.
        
        Args:
            limit: Maximum memories to return
            min_engagement: Minimum engagement score threshold
            
        Returns:
            List of high-performing memories
        """
        self.connect()
        
        collection = self.client.collections.get(self.COLLECTION_NAME)
        
        filters = (
            weaviate.classes.query.Filter.by_property("agent_id").equal(self.agent_id) &
            weaviate.classes.query.Filter.by_property("engagement_score").greater_or_equal(min_engagement)
        )
        
        response = collection.query.fetch_objects(
            filters=filters,
            limit=limit,
        )
        
        memories = []
        for obj in response.objects:
            memories.append({
                "content": obj.properties.get("content"),
                "memory_type": obj.properties.get("memory_type"),
                "engagement_score": obj.properties.get("engagement_score"),
                "platform": obj.properties.get("platform"),
                "tags": obj.properties.get("tags", []),
            })
        
        # Sort by engagement score
        memories.sort(key=lambda m: m.get("engagement_score", 0), reverse=True)
        
        return memories
    
    def consolidate_memories(self, similarity_threshold: float = 0.1):
        """
        Merge very similar memories to prevent redundancy.
        
        This is a maintenance operation that should run periodically.
        
        Args:
            similarity_threshold: Distance threshold for considering memories duplicates
        """
        # TODO: Implement memory consolidation logic
        # This would involve:
        # 1. Query all memories
        # 2. Find clusters of similar memories
        # 3. Merge clusters into representative memories
        # 4. Delete redundant entries
        pass


# Singleton instance
_instance: Optional[LongTermMemoryManager] = None


def get_long_term_memory(
    weaviate_url: str = "http://localhost:8080",
    weaviate_api_key: Optional[str] = None,
    agent_id: str = "nova",
) -> LongTermMemoryManager:
    """Get or create the singleton LongTermMemoryManager instance."""
    global _instance
    if _instance is None:
        _instance = LongTermMemoryManager(
            weaviate_url=weaviate_url,
            weaviate_api_key=weaviate_api_key,
            agent_id=agent_id,
        )
    return _instance
