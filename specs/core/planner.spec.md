---
component: core.planner
version: 1.0.0
status: draft
dependencies:
  - redis>=5.0
  - google-generativeai || anthropic
  - src.memory.persona
  - src.memory.short_term
  - src.memory.long_term
  - src.mcp.client
---

# Planner Service Specification

## Purpose

The Planner is the "strategic brain" of the swarm. It continuously monitors the global state (news, trends, campaign goals) and decomposes high-level objectives into concrete, executable tasks for Worker agents.

## Interface

### Class: `PlannerService`

#### Constructor
```python
def __init__(
    self,
    agent_id: str,
    redis_url: str,
    mcp_client: MCPClient,
    persona_manager: ContextManager,
)
```

#### Methods

**start()**
```python
async def start() -> None
```
Starts the Planner's main loop. Runs until `stop()` is called.

**stop()**
```python
async def stop() -> None
```
Gracefully stops the Planner loop.

**plan_daily_content()**
```python
async def plan_daily_content() -> List[AgentTask]
```
Generates daily posting schedule based on agent's goals and time of day.

**detect_trending_topics()**
```python
async def detect_trending_topics() -> List[TrendAlert]
```
Analyzes news resources for emerging trends worthy of content creation.

**create_reply_tasks()**
```python
async def create_reply_tasks(mentions: List[Dict]) -> List[AgentTask]
```
Creates tasks for replying to mentions/comments.

**update_global_state()**
```python
async def update_global_state(updates: Dict[str, Any]) -> int
```
Updates global state with OCC versioning. Returns new state version.

## Behavior

### Main Loop

```
loop:
  1. Poll MCP resources (news, mentions) via resource_monitor
  2. Analyze incoming data for opportunities
  3. Check time-based triggers (e.g., "post at 9am")
  4. Generate tasks based on opportunities + schedule
  5. Push tasks to Redis queue
  6. Sleep for interval (default: 30 seconds)
```

### Task Generation Logic

#### Daily Content Planning
- **Trigger**: Clock-based (e.g., 6am daily)
- **Process**:
  1. Query long-term memory for successful topics
  2. Check news resources for recent developments
  3. Generate 3-5 content ideas
  4. Create tasks with type `generate_post`

#### Trending Topic Detection
- **Trigger**: News resource updates
- **Process**:
  1. Aggregate articles over 4-hour window
  2. Use LLM to cluster related topics
  3. If cluster exceeds threshold (e.g., 3+ articles), create `TrendAlert`
  4. Generate task to create timely content

#### Reply Task Creation
- **Trigger**: New mentions detected in `x://mentions/recent`
- **Process**:
  1. For each mention:
     - Pass through semantic filter (relevance > 0.70)
     - If relevant, create `generate_reply` task
     - Include mention context in task data

### OCC State Management

The Planner maintains `GlobalState` with OCC versioning:

```python
GlobalState = {
    "state_version": 142,  # Increments with each update
    "current_goals": ["Promote AI safety awareness", "Build thought leadership"],
    "active_campaigns": [...],
    "budget_remaining": 8.50,  # USD
    "last_post_timestamp": "2026-02-06T07:30:00Z",
    "trending_topics": [...]
}
```

When updating state:
1. Read current `state_version`
2. Make changes
3. Increment `state_version`
4. Write atomically to Redis

If multiple Planners run concurrently (future scaling), they use Redis transactions to ensure consistency.

## Test Criteria

### Unit Tests

1. **Task Generation**
   - `plan_daily_content()` returns 3-5 tasks
   - Tasks have valid structure (`AgentTask` model)
   - Tasks include context from persona + memory

2. **Trend Detection**
   - `detect_trending_topics()` clusters related articles
   - Returns empty list when no trends
   - Clusters have meaningful topics

3. **Reply Task Creation**
   - Creates task for each relevant mention
   - Filters out low-relevance mentions
   - Includes mention context

4. **State Management**
   - `update_global_state()` increments version
   - Concurrent updates handled correctly (use Redis WATCH/MULTI)

### Integration Tests

1. **Full Planning Cycle**
   - Start Planner service
   - Inject test news articles via mock MCP
   - Verify tasks appear in Redis queue
   - Verify tasks have correct context

2. **Time-Based Planning**
   - Mock system clock to trigger daily planning
   - Verify scheduled tasks are created at right time

3. **Resource Polling Integration**
   - Connect to real MCP news server
   - Verify Planner reacts to new articles
   - Verify semantic filtering applied

## Examples

### Basic Usage

```python
from src.core.planner import PlannerService
from src.mcp import get_mcp_client
from src.memory import ContextManager

# Initialize
mcp = get_mcp_client()
persona = ContextManager(soul_path="./SOUL.md")
planner = PlannerService(
    agent_id="nova",
    redis_url="redis://localhost:6379",
    mcp_client=mcp,
    persona_manager=persona,
)

# Start planning loop
await planner.start()  # Runs until stop() called
```

### Manual Task Creation (for testing)

```python
# Manually trigger content planning
tasks = await planner.plan_daily_content()
print(f"Generated {len(tasks)} tasks")

# Manually detect trends
trends = await planner.detect_trending_topics()
for trend in trends:
    print(f"Trend: {trend.topic} ({trend.article_count} articles)")
```

## Performance Requirements

- **Planning cycle**: Complete within 10 seconds
- **Memory usage**: < 100MB per Planner instance
- **Task generation latency**: < 5 seconds per task
- **Handles 100+ news articles/day efficiently**

## Error Handling

- **Redis connection loss**: Retry with exponential backoff, escalate after 3 failures
- **LLM API errors**: Retry with different model (Gemini → Claude fallback)
- **MCP resource unavailable**: Log warning, continue with other resources
- **Invalid task generated**: Log error, discard task, continue loop
