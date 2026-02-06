---
component: memory.short_term
version: 1.0.0
status: stable
dependencies:
  - redis>=5.0
  - pydantic>=2.0
---

# Short-Term Memory Specification

## Purpose

Provides episodic memory storage for recent agent interactions (1-2 hour rolling window). Enables the agent to maintain conversational context and recall recent activities without overloading the LLM context window.

## Interface

### Class: `ShortTermMemoryManager`

#### Constructor
```python
def __init__(self, redis_url: str = "redis://localhost:6379/0", agent_id: str = "nova")
```

#### Methods

**connect()**
```python
async def connect() -> None
```
Establishes connection to Redis. Idempotent (can be called multiple times safely).

**disconnect()**
```python
async def disconnect() -> None
```
Closes Redis connection and cleans up resources.

**add_interaction()**
```python
async def add_interaction(
    interaction_type: str,
    content: str,
    platform: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ttl_hours: Optional[int] = None,
) -> EpisodicMemory
```
Stores a new interaction with automatic TTL expiration.

**Returns**: Created `EpisodicMemory` object

**get_recent()**
```python
async def get_recent(
    hours: float = 2.0,
    limit: Optional[int] = None,
) -> List[EpisodicMemory]
```
Retrieves recent interactions within time window.

**Returns**: List of memories, sorted newest first

**get_recent_summaries()**
```python
async def get_recent_summaries(
    hours: float = 2.0,
    limit: Optional[int] = None,
) -> List[str]
```
Gets formatted string summaries for LLM context injection.

**Returns**: List of formatted strings like `"[HH:MM] posted_tweet on x: AI just did something wild"`

## Behavior

### TTL Management
- Default TTL: 2 hours
- Memories auto-expire via Redis TTL
- No manual cleanup required

### Key Structure
- Memory key: `agent:{agent_id}:episodic:{timestamp_iso}`
- Index key: `agent:{agent_id}:episodic:index` (sorted set)

### Concurrency
- Thread-safe via Redis atomic operations
- Multiple processes can write simultaneously
- Sorted set maintains chronological order

### Error Handling
- Connection failures: Raise `ConnectionError`
- Redis unavailable: Retry with exponential backoff (handled by redis-py)
- Invalid timestamps: Raise `ValueError`

## Test Criteria

### Unit Tests
1. **Connection Management**
   - Can connect to Redis
   - Can disconnect cleanly
   - Multiple connects are idempotent

2. **Memory Storage**
   - `add_interaction()` stores memory
   - Memory has correct TTL
   - Memory appears in sorted set index

3. **Memory Retrieval**
   - `get_recent()` returns memories within time window
   - Memories sorted newest first
   - Respects `limit` parameter
   - Returns empty list when no memories exist

4. **Summary Formatting**
   - `get_recent_summaries()` formats correctly
   - Includes timestamp, type, platform, content

5. **TTL Expiration**
   - Memories expire after TTL
   - Expired memories not returned by `get_recent()`

### Integration Tests
- Works with real Redis instance
- Handles network interruptions
- Multiple agents use same Redis without collision

## Examples

### Basic Usage
```python
from src.memory import get_short_term_memory

memory = get_short_term_memory()
await memory.connect()

# Store an interaction
await memory.add_interaction(
    interaction_type="posted_tweet",
    content="Just shipped a new AI feature!",
    platform="x"
)

# Retrieve recent summaries for LLM context
summaries = await memory.get_recent_summaries(hours=2.0, limit=10)
# Returns: ["[14:23] posted_tweet on x: Just shipped a new AI feature!"]
```

### Integration with Context Assembly
```python
from src.memory import ContextManager, get_short_term_memory

context_mgr = ContextManager(soul_path="./SOUL.md")
short_term = get_short_term_memory()

# Context assembly auto-fetches memories
context = await context_mgr.assemble_context(
    input_query="Generate a tweet about AI ethics",
    short_term_manager=short_term
)
```

## Performance Requirements

- **Write latency**: < 10ms per interaction
- **Read latency**: < 50ms for retrieving 10 memories
- **Memory footprint**: < 1KB per memory entry
- **Concurrent writes**: Support 100+ writes/sec

## Security Considerations

- No sensitive data stored in Redis (PII should be hashed)
- Redis auth required in production
- TLS encryption for Redis connections recommended
