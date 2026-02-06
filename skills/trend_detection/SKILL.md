# Skill: Trend Detection

A reusable pattern for monitoring news sources and identifying high-value trending topics.

## Purpose

Automates the process of gathering technical news, clustering information, and determining which topics are most relevant for Nova Intellect's persona and audience.

## Interface

### Function: `detect_trends`

```python
async def detect_trends(
    news_sources: list[str],
    mcp_client: MCPClient,
    relevance_threshold: float = 0.75,
) -> list[TrendTopic]
```

**Parameters**:
- `news_sources`: List of resource URIs or source names to poll.
- `mcp_client`: Initialized MCP client.
- `relevance_threshold`: Minimum relevance score to flag as a trend.

**Returns**: `list[TrendTopic]` containing topic name, summary, source links, and impact score.

## Pattern

```
1. Information Gathering
   ├─ Poll MCP News Server (TechCrunch, AI News, etc.)
   └─ Clean and deduplicate articles

2. Topic Extraction
   ├─ Semantic clustering of headlines
   └─ Keyword/Entity extraction (LLM-assisted)

3. Scoring & Filtering
   ├─ Match against Persona Values (SOUL.md)
   ├─ Check "Freshness" (Time since discovery)
   └─ Filter by relevance_threshold

4. Reasoning
   ├─ Why is this relevant?
   └─ What unique angle can Nova take?

5. Output
   └─ Return structured TrendTopic objects
```

## Implementation

See: `src/skills/trend_detection.py`

## Usage Example

```python
from src.skills.trend_detection import detect_trends
from src.mcp import get_mcp_client

mcp = get_mcp_client()
trends = await detect_trends(
    news_sources=["news://techcrunch", "news://openai-blog"],
    mcp_client=mcp
)

for trend in trends:
    print(f"Detected: {trend.topic} (Score: {trend.score})")
```

## Test Criteria

- Successfully fetches data from MCP news resources.
- Correctly deduplicates similar articles.
- High-relevance topics (e.g., major AI releases) score > 0.8.
- Irrelevant topics (e.g., generic retail news) score < 0.3.
- Output contains actionable context for the Planner.
