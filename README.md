# Project Chimera: Autonomous Tech Influencer

**Status**: 🚧 In Development  
**Agent**: Nova Intellect  
**Platforms**: X (Twitter), LinkedIn  
**Focus**: AI, Startups, Emerging Technology

## Overview

This is an implementation of the **Project Chimera 2026 SRS** autonomous influencer network, configured to operate a single tech-focused AI influencer named **Nova Intellect**.

The system uses:
- **FastRender Swarm Architecture**: Planner-Worker-Judge pattern for robust task execution
- **Model Context Protocol (MCP)**: Universal interface for external data and tools
- **Hierarchical Memory**: Redis (short-term) + Weaviate (long-term semantic memory)
- **Human-in-the-Loop**: Confidence-based escalation for safety and quality control

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Planner Service                     │   │
│  │  - Monitors trends and goals                     │   │
│  │  - Decomposes into tasks                         │   │
│  │  - Manages task queue                            │   │
│  └──────────────────┬───────────────────────────────┘   │
│                     │                                    │
│         ┌───────────┴────────────┐                      │
│         ▼                        ▼                       │
│  ┌─────────────┐          ┌─────────────┐              │
│  │   Worker    │          │    Judge    │              │
│  │   Pool      │──────────▶   Service   │              │
│  │             │          │             │              │
│  │ - Execute   │          │ - Validate  │              │
│  │   tasks     │          │ - Score     │              │
│  │ - Generate  │          │ - Escalate  │              │
│  │   content   │          │   (HITL)    │              │
│  └─────────────┘          └─────────────┘              │
└──────────────┬──────────────────┬───────────────────────┘
               │                  │
       ┌───────┴────────┐  ┌──────┴─────────┐
       │  MCP Servers   │  │  Memory Layer  │
       │                │  │                │
       │ - Tech News    │  │ - Weaviate     │
       │ - X/Twitter    │  │ - Redis        │
       │ - LinkedIn     │  │ - PostgreSQL   │
       └────────────────┘  └────────────────┘
```

## Project Structure

```
Chimera-Autonomous-Influencer/
├── SOUL.md                    # Persona definition (immutable DNA)
├── src/
│   ├── core/
│   │   ├── planner/          # Planning service
│   │   ├── worker/           # Worker execution pool
│   │   └── judge/            # Quality assurance & governance
│   ├── memory/
│   │   ├── context.py        # Context assembly (SOUL + memories)
│   │   ├── short_term.py     # Redis episodic memory
│   │   └── long_term.py      # Weaviate semantic memory
│   ├── perception/
│   │   ├── resource_monitor.py  # MCP resource polling
│   │   ├── semantic_filter.py   # Relevance scoring
│   │   └── trend_detector.py    # Pattern detection
│   ├── generation/
│   │   ├── content_engine.py    # Multimodal generation
│   │   └── platform_adapter.py  # X vs LinkedIn tone
│   ├── action/
│   │   └── publisher.py         # MCP tool execution
│   └── mcp/
│       ├── client.py            # MCP client wrapper
│       └── servers/             # Custom MCP servers
├── config/
│   ├── agents.json           # Fleet configuration
│   ├── mcp_config.json       # MCP server definitions
│   └── safety_policies.json  # Governance rules
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── deployment/
    ├── docker-compose.yml
    └── k8s/
```

## Persona: Nova Intellect

**Voice**: Witty, sharp, playful, insightful, confident  
**Platforms**: X (Twitter) and LinkedIn  
**Niche**: AI, startups, emerging technology  

Nova is designed to:
- Monitor TechCrunch and reputable tech news sources continuously
- Generate platform-appropriate content (punchy for X, professional for LinkedIn)
- Engage authentically with the tech community
- Never hallucinate facts or give financial/legal advice
- Disclose AI identity when asked directly

Full persona definition: [SOUL.md](./SOUL.md)

## Getting Started

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Redis
- Weaviate (or Weaviate Cloud)
- API Keys:
  - Gemini API (or Claude API)
  - X (Twitter) API
  - LinkedIn API
  - TechCrunch/News APIs

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd Chimera-Autonomous-Influencer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start infrastructure services
docker-compose up -d

# Run the orchestrator
python src/main.py
```

### Configuration

Edit `config/agents.json` to customize Nova's behavior:
- Posting frequency
- Platform distribution (X vs LinkedIn ratio)
- Budget limits
- HITL thresholds

## Safety & Governance

The system implements multiple safety layers:

1. **Confidence Scoring**: Every output gets scored 0.0–1.0
   - \>0.90: Auto-approve
   - 0.70–0.90: Async human review
   - <0.70: Auto-reject and retry

2. **Sensitive Topic Filters**: Automatic escalation for:
   - Political content
   - Financial/legal advice
   - Unverifiable claims

3. **Fact-Checking**: All factual claims validated against sources

4. **Disclosure**: Automatic AI identity disclosure when asked

## Development Roadmap

- [x] Phase 1: Foundation & Persona
- [ ] Phase 2: Memory & Context System
- [ ] Phase 3: MCP Integration Layer
- [ ] Phase 4: Planner-Worker-Judge Core
- [ ] Phase 5: Perception System
- [ ] Phase 6: Content Generation Engine
- [ ] Phase 7: Action & Publishing System
- [ ] Phase 8: Safety & Governance
- [ ] Phase 9: Testing & Validation
- [ ] Phase 10: Deployment & Monitoring

## License

Proprietary - AiQEM.tech

## Contact

For questions about Project Chimera, contact the development team.

---

*Built with the FastRender Swarm Architecture and Model Context Protocol*
