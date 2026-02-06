# Project Chimera - Autonomous AI Influencer

**An autonomous AI influencer system powered by GitHub Spec Kit and FastRender Swarm Architecture**

## Overview

Project Chimera is an AI-powered social media influencer ("Nova Intellect") that autonomously creates and publishes content to X (Twitter) and LinkedIn using a Spec-Driven Development approach.

### Key Features

- 🤖 **Autonomous Content Creation** - Generates platform-optimized posts
- 🎯 **Trending Topic Detection** - Monitors tech news and identifies opportunities
- 💬 **Audience Engagement** - Responds to mentions and comments
- 🧠 **Hierarchical Memory** - Short-term (Redis) + Long-term (Weaviate) memory systems
- 🔌 **MCP Integration** - All external services via Model Context Protocol
- 🛡️ **Safety First** - HITL review, confidence scoring, ethical disclosure
- 📊 **Swarm Architecture** - Planner-Worker-Judge pattern for scalability

## Tech Stack

- **Language**: Python 3.11+
- **LLM**: Google Gemini 2.0 Flash
- **Memory**: Redis (short-term), Weaviate (long-term)
- **Integration**: MCP (Model Context Protocol)
- **Platforms**: X (Twitter), LinkedIn
- **Development**: GitHub Spec Kit (Spec-Driven Development)

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- `uv` package manager
- GitHub Spec Kit CLI

### Installation

```bash
# Clone repository
git clone <repository-url>
cd Chimera-Autonomous-Influencer

# Install dependencies
make install-dev

# Start infrastructure (Redis + Weaviate)
make docker-up

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### GitHub Spec Kit Setup

```bash
# Install Spec Kit CLI
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git

# Already initialized! Use slash commands:
# /speckit.constitution - Define project principles
# /speckit.specify - Create specifications
# /speckit.plan - Generate implementation plan
# /speckit.tasks - Break down into tasks
# /speckit.implement - Execute implementation
```

### Running the System

```bash
# Development mode (dry-run, no actual posting)
make run-dev

# Run tests
make test

# Check code quality
make lint

# Format code
make format
```

## Project Structure

```
Chimera-Autonomous-Influencer/
├── .claude/           # GitHub Spec Kit slash commands
├── .specify/          # Spec Kit configuration & templates
├── src/               # Source code
│   ├── core/         # Planner, Worker, Judge services
│   ├── memory/       # Memory systems (short-term, long-term)
│   ├── mcp/          # MCP client & custom servers
│   ├── generation/   # Content generation engine
│   └── models.py     # Pydantic data models
├── tests/            # Test suite
│   ├── unit/         # Unit tests
│   ├── integration/  # Integration tests
│   └── e2e/          # End-to-end tests
├── skills/           # Reusable agent capabilities
├── config/           # Configuration files
│   ├── safety_policies.json
│   └── mcp_config.json
├── .github/          # CI/CD workflows
├── Dockerfile        # Container image
├── Makefile          # Build automation
└── SOUL.md           # Agent persona definition
```

## Architecture

### FastRender Swarm Pattern

```
Planner → Task Queue → Workers (pool) → Review Queue → Judge → Publish
   ↑                                                        ↓
   └────────────── HITL Queue (human review) ─────────────┘
```

**Planner**: Strategic task generation (trend detection, scheduling)  
**Workers**: Stateless task executors (content generation, replies)  
**Judge**: Quality validation (safety, persona alignment, confidence scoring)

### Memory System

- **Short-Term (Redis)**: Recent interactions, 2-hour TTL
- **Long-Term (Weaviate)**: High-performing content, semantic search

### MCP Servers

- **News Server**: Tech news aggregation (TechCrunch, AI research)
- **X Server**: Twitter posting, mentions, timeline
- **LinkedIn Server**: LinkedIn posting, comments

## Development Workflow

Following **Spec-Driven Development (SDD)** via GitHub Spec Kit:

1. **Constitution** (`/speckit.constitution`) - Define principles
2. **Specify** (`/speckit.specify`) - Create specifications
3. **Plan** (`/speckit.plan`) - Technical implementation plan
4. **Tasks** (`/speckit.tasks`) - Actionable task breakdown
5. **Implement** (`/speckit.implement`) - Code execution
6. **Test** - Validate against specs

## Safety & Ethics

- ✅ **Transparent AI Disclosure** - Bio states "AI-powered"
- ✅ **HITL Review** - Medium-confidence content requires human approval
- ✅ **Safety Filters** - Banned keywords, sensitive topics
- ✅ **Rate Limiting** - Platform API limits enforced
- ✅ **Dry-Run Default** - All tests run in simulation mode

## Current Status

**Phase 4: Core Swarm Implementation** ✅
- Planner service complete
- Worker service complete
- Judge service complete
- ContentEngine complete

**Next**: Integration testing & end-to-end validation

## Contributing

1. Follow GitHub Spec Kit workflow
2. All changes must align with specifications
3. Maintain >80% test coverage
4. Use `make ci` before committing

## License

[Your License Here]

## Contact

- **Project**: Project Chimera by AiQEM
- **Agent**: Nova Intellect
- **Methodology**: GitHub Spec Kit + Spec-Driven Development

---

**Built with GitHub Spec Kit** | **Powered by FastRender Swarm Architecture**
