# Agent Skills Library

This directory contains the "blueprint" patterns for core agent capabilities. Each skill follows a strictly defined I/O contract and operational pattern, enabling predictable and testable behavior in the Chimera Swarm.

## Core Skills

| Skill | Folder | Description | Status |
|-------|--------|-------------|--------|
| **Social Media Posting** | [`social_posting/`](./social_posting/SKILL.md) | Multi-platform publishing with safety checks. | ✅ Defined |
| **Trend Detection** | [`trend_detection/`](./trend_detection/SKILL.md) | Autonomous news polling and topic analysis. | ✅ Defined |
| **Audience Engagement** | [`audience_engagement/`](./audience_engagement/SKILL.md) | Context-aware replies and conversation management. | ✅ Defined |

## Structure of a Skill

Each skill directory follows this structure:

- `SKILL.md`: The "Source of Truth" specification.
  - **Purpose**: Why this skill exists.
  - **Interface**: The technical I/O contract (function signatures, parameters).
  - **Pattern**: The step-by-step logic/workflow the agent follows.
  - **Test Criteria**: Success and failure definitions for validation.
- `__init__.py`: Package entry point.
- `logic.py`: (Optional) The actual implementation code.

## How to Use

Skills are invoked by **Workers** in the swarm for specific task types:

1. **Planner** creates a task (e.g., `type: generate_post`).
2. **Worker** picks up the task and identifies the required skill.
3. **Worker** follows the **Pattern** defined in the `SKILL.md`.
4. **Judge** validates the output against the **Test Criteria**.

## Adding New Skills

To add a new skill to the library:
1. Create a new directory under `skills/`.
2. Draft the `SKILL.md` following the template of existing skills.
3. Update this `README.md` index.
4. (Optional) Implement the logic once the contract is approved.

---
**Methodology**: GitHub Spec Kit | **Context**: Project Chimera
