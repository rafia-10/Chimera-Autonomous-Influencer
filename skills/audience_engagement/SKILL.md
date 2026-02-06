# Skill: Audience Engagement

A reusable pattern for processing mentions and generating contextually aware social media responses.

## Purpose

Manages the interaction loop between social media platforms and the agent, ensuring that responses are timely, helpful, and strictly adhere to the persona definition.

## Interface

### Function: `process_engagement`

```python
async def process_engagement(
    mention: MentionData,
    conversation_history: list[dict],
    mcp_client: MCPClient,
) -> EngagementResponse
```

**Parameters**:
- `mention`: Data object containing the user's post, ID, and metadata.
- `conversation_history`: Recent turns from Short-Term Memory (Redis).
- `mcp_client`: Initialized MCP client.

**Returns**: `EngagementResponse` containing the reply text and validation metadata.

## Pattern

```
1. Context Retrieval
   ├─ Load Short-Term Memory (Episodic)
   └─ Identify user relationship/sentiment

2. Content Analysis
   ├─ Classify intent (Question, Praise, Criticism, Spam)
   └─ Extract technical entities

3. Response Generation (LLM)
   ├─ Inject Persona constraints (SOUL.md)
   ├─ Inject Technical Context (API Docs, etc.)
   └─ Draft reply (Platform-appropriate)

4. Validation
   ├─ Safety check (Banned keywords)
   └─ Fact check (Consistency with history)

5. Action
   └─ Queue for publishing or reject if junk
```

## Implementation

See: `src/skills/audience_engagement.py`

## Usage Example

```python
from src.skills.audience_engagement import process_engagement
from src.memory import ShortTermMemory

memory = ShortTermMemory()
history = await memory.get_history(mention.author_id)
response = await process_engagement(mention, history, mcp)

if response.should_reply:
    print(f"Replying to {mention.author_id}: {response.text}")
```

## Test Criteria

- Correctly identifies technical questions vs. general chatter.
- Maintains continuity over a 3-turn test conversation.
- Rejects toxic or spammy mentions (Safety score < 0.5).
- Response reflects the "expert but accessible" tone of Nova Intellect.
