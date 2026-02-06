# Project Chimera: Tooling & Skills Strategy

## Overview

This document defines the **two-tier tooling architecture** for Project Chimera:

1. **Developer Tools (MCP)**: Tools that help HUMANS develop the system
2. **Agent Skills (Runtime)**: Capabilities that AI AGENTS use to accomplish tasks

## Part 1: Developer Tools (MCP Servers)

### Purpose

MCP (Model Context Protocol) servers extend the IDE's AI assistant capabilities during development.

### Selected MCP Servers

#### 1. **filesystem-mcp** ✅

**Purpose**: File system operations

**Capabilities**:
- Read/write files
- List directories
- Search codebase

**Why**: Essential for code navigation and editing

**Status**: Standard with most AI IDEs

---

#### 2. **github-mcp-server** ✅

**Purpose**: GitHub integration

**Capabilities**:
- Create PRs
- Review code
- Manage issues
- Read repository contents

**Why**: Enables GitOps workflow and collaboration

**Status**: Integrated

---

#### 3. **brave-search** (Optional)

**Purpose**: Web search for latest documentation

**Capabilities**:
- Search technical docs
- Find API references
- Research best practices

**Why**: Useful when implementing new integrations

**Status**: Optional, add if needed

---

#### 4. **memory-mcp** (Custom - Future)

**Purpose**: Project knowledge persistence

**Capabilities**:
- Store design decisions
- Remember conversation context
- Retrieve historical context

**Why**: Long-term project memory across sessions

**Status**: Future enhancement

---

### Configuration

MCP servers are configured in `.vscode/mcp.json` (VS Code) or equivalent for other IDEs.

Example:
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}
```

## Part 2: Agent Skills (Runtime Capabilities)

### Definition

A **Skill** is a self-contained capability package that an AI Agent can use to accomplish specific tasks. Each skill has:

- **Clear interface** (inputs/outputs)
- **Defined purpose** (what it does)
- **Error handling** (what can go wrong)
- **Testing strategy** (how to validate)

### Skill Directory Structure

```
skills/
├── README.md              ← Index of all skills
├── social_posting/
│   └── SKILL.md          ← Posting pattern
├── trend_detection/
│   └── SKILL.md          ← Topic clustering
├── content_optimization/
│   └── SKILL.md          ← A/B testing
└── engagement_analysis/
    └── SKILL.md          ← Performance metrics
```

### Critical Skills (MVP)

#### Skill 1: Social Media Posting ✅

**File**: `skills/social_posting/SKILL.md`

**Purpose**: Publish content to social platforms via MCP

**Inputs**:
```json
{
  "content": "string",
  "platform": "enum(x, linkedin)",
  "mcp_client": "MCPClient instance",
  "confidence_threshold": "float (default 0.90)"
}
```

**Outputs**:
```json
{
  "success": "boolean",
  "post_id": "string (if success)",
  "error": "string (if failure)"
}
```

**Status**: Documented, implementation in `src/generation/content_engine.py`

---

#### Skill 2: Trend Detection

**File**: `skills/trend_detection/SKILL.md`

**Purpose**: Analyze news clusters to identify trending topics

**Inputs**:
```json
{
  "articles": [
    {
      "title": "string",
      "summary": "string",
      "url": "string",
      "published": "ISO8601"
    }
  ],
  "time_window": "hours (default 4)",
  "min_cluster_size": "integer (default 3)"
}
```

**Outputs**:
```json
{
  "trends": [
    {
      "topic": "string",
      "confidence": "float (0-1)",
      "related_articles": "array",
      "suggested_angle": "string"
    }
  ]
}
```

**Implementation**: Partially in `src/core/planner/service.py`, needs LLM clustering

**Status**: In progress

---

#### Skill 3: Content Optimization

**File**: `skills/content_optimization/SKILL.md`

**Purpose**: A/B test different content angles

**Inputs**:
```json
{
  "topic": "string",
  "platform": "string",
  "variants": "integer (default 2)",
  "max_chars": "integer"
}
```

**Outputs**:
```json
{
  "options": [
    {
      "content": "string",
      "predicted_engagement": "float",
      "style": "string (e.g., 'witty', 'informative')"
    }
  ]
}
```

**Implementation**: Not yet started

**Status**: Planned for Phase 5

---

### Skill Development Workflow

When creating a new skill:

1. **Define the need**
   - What problem does this solve?
   - Which agent role needs this? (Planner/Worker/Judge)

2. **Write SKILL.md**
   - Purpose and scope
   - Input/output contracts (JSON schemas)
   - Error cases and handling
   - Usage examples

3. **Design tests**
   - Unit tests for core logic
   - Integration tests with dependencies
   - E2E test in full workflow

4. **Implement**
   - Create module in `src/skills/` or relevant package
   - Follow input/output contract exactly
   - Add comprehensive error handling

5. **Document usage**
   - Update `skills/README.md` index
   - Add to agent training data (future)

## Tool Selection Criteria

### For Developer Tools (MCP)

Select based on:
- **Frequency of use**: Will this save daily time?
- **Unique capability**: Can't be done another way?
- **Maintenance cost**: Is it actively maintained?
- **Security**: Does it require sensitive credentials?

### For Agent Skills

Select based on:
- **Core to mission**: Essential for autonomous operation?
- **Reusability**: Used across multiple workflows?
- **Clear boundaries**: Well-defined inputs/outputs?
- **Testability**: Can we validate correctness?

## Security Considerations

### Developer Tools

- **Credentials**: Store in environment variables only
- **Scope**: Limit permissions to minimum required
- **Review**: Audit MCP server source code before use
- **Updates**: Keep MCP servers up to date

### Agent Skills

- **Validation**: All inputs validated before use
- **Rate limiting**: Respect platform API limits
- **Error handling**: Graceful degradation, no crashes
- **Logging**: All skill invocations logged for audit

## Future Enhancements

### Developer Tools

- **Spec validator MCP**: Check code against specs automatically
- **Test generator MCP**: Generate test cases from specs
- **Cost estimator MCP**: Predict LLM API costs

### Agent Skills

- **Video generation**: Create short-form video content
- **Multi-agent coordination**: Skills for swarm communication
- **Budget optimization**: Allocate resources across goals
- **Learning loop**: Consolidate high-performing patterns

## Skill Index (Quick Reference)

| Skill | Status | Purpose | Priority |
|-------|--------|---------|----------|
| Social Posting | ✅ Done | Publish content | Critical |
| Trend Detection | ⏳ In Progress | Find hot topics | Critical |
| Content Optimization | 📋 Planned | A/B testing | High |
| Engagement Analysis | 📋 Planned | Performance metrics | Medium |
| Reply Generation | 📋 Planned | Mention responses | High |
| Fact Checking | 📋 Planned | Verify claims | Critical |
| Sentiment Analysis | 📋 Planned | Audience feedback | Medium |

---

**Maintained by**: Super-Orchestrator  
**Last Updated**: 2026-02-06  
**Next Review**: After Phase 5
