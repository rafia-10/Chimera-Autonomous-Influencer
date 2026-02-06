# Skill: Social Media Posting

A reusable pattern for posting content to social media platforms via MCP.

## Purpose

Encapsulates the complete flow of creating, validating, and publishing social media posts across multiple platforms (X/Twitter, LinkedIn) with safety checks and error handling.

## Interface

### Function: `post_to_platform`

```python
async def post_to_platform(
    content: str,
    platform: str,
    mcp_client: MCPClient,
    confidence_threshold: float = 0.90,
) -> PostResult
```

**Parameters**:
- `content`: Text content to post
- `platform`: Target platform ("x" or "linkedin")
- `mcp_client`: Initialized MCP client
- `confidence_threshold`: Minimum confidence to auto-post

**Returns**: `PostResult` with status, post_id (if successful), and any errors

## Pattern

```
1. Validate content
   ├─ Check character limits
   ├─ Check banned keywords
   └─ Check sensitive topics

2. Platform adaptation
   ├─ Adjust tone for platform
   ├─ Format hashtags
   └─ Add emojis (platform-appropriate)

3. Safety check
   ├─ Confidence scoring via LLM
   ├─ If < threshold → escalate to HITL
   └─ If >= threshold → proceed

4. Publish
   ├─ Call MCP tool (post_tweet or create_post)
   ├─ Handle rate limits
   └─ Log action

5. Store memory
   ├─ Add to short-term memory
   └─ If high engagement → long-term memory
```

## Implementation

See: `src/skills/social_posting.py`

## Usage Example

```python
from src.skills.social_posting import post_to_platform
from src.mcp import get_mcp_client

mcp = get_mcp_client()
result = await post_to_platform(
    content="AI agents are reshaping software development",
    platform="x",
    mcp_client=mcp
)

if result.success:
    print(f"Posted: {result.post_id}")
else:
    print(f"Failed: {result.error}")
```

## Test Criteria

- Character limit enforcement works
- Banned keywords trigger rejection
- Confidence scoring returns 0.0-1.0
- HITL escalation works when confidence < threshold
- Platform-specific formatting applied correctly
