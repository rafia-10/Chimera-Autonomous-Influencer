# Project Chimera - Directory Structure

## Root Directory

```
Chimera-Autonomous-Influencer/
├── .claude/              # GitHub Spec Kit agent commands
├── .specify/             # Spec Kit configuration & templates
├── .github/              # CI/CD workflows
├── .vscode/              # VSCode/MCP configuration
├── config/               # System configuration
├── research/             # Research & strategy docs
├── scripts/              # Utility scripts
├── skills/               # Reusable agent capabilities
├── src/                  # Source code (implementation)
├── tests/                # Test suite
├── deployment/           # Deployment configs
├── SOUL.md               # Agent persona
├── README.md             # Project overview
├── Makefile              # Build automation
├── Dockerfile            # Container image
├── docker-compose.yml    # Infrastructure services
├── requirements.txt      # Python dependencies
├── requirements-dev.txt  # Dev dependencies
├── .env.example          # Environment template
└── .gitignore            # Git exclusions
```

## Key Directories

### `.claude/` - GitHub Spec Kit Commands
Slash commands for the Spec-Driven Development workflow:
- `/speckit.constitution` - Project principles
- `/speckit.specify` - Create specifications
- `/speckit.plan` - Implementation plan
- `/speckit.tasks` - Task breakdown
- `/speckit.implement` - Execute implementation
- `/speckit.analyze` - Consistency checks
- `/speckit.clarify` - Ask questions
- `/speckit.checklist` - Quality validation

### `src/` - Source Code
```
src/
├── core/              # Swarm services
│   ├── planner/      # Strategic task generation
│   ├── worker/       # Task execution
│   └── judge/        # Quality validation
├── memory/            # Memory systems
│   ├── persona.py    # Persona management
│   ├── short_term.py # Redis episodic memory
│   └── long_term.py  # Weaviate semantic memory
├── mcp/               # MCP integration
│   ├── client.py     # MCP client wrapper
│   └── servers/      # Custom MCP servers
│       ├── news_server.py
│       ├── x_server.py
│       └── linkedin_server.py
├── generation/        # Content generation
│   └── content_engine.py
├── models.py          # Pydantic schemas
└── config.py          # Configuration loader
```

### `tests/` - Test Suite
```
tests/
├── unit/              # Unit tests
│   └── test_short_term_memory.py
├── integration/       # Integration tests
└── e2e/               # End-to-end tests
```

### `skills/` - Agent Capabilities
Reusable skill patterns documented as SKILL.md files:
- `social_posting/` - Platform posting pattern
- Future: `trend_detection/`, `content_optimization/`, etc.

### `config/` - Configuration
- `safety_policies.json` - Safety rules, banned keywords
- `mcp_config.json` - MCP server configurations

### `.specify/` - Spec Kit Framework
Templates and configuration for GitHub Spec Kit:
- `templates/` - Spec, plan, task templates
- `scripts/` - Automation scripts
- `memory/` - Spec Kit memory/context

## File Naming Conventions

- **Python modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Documents**: `SCREAMING_SNAKE_CASE.md` for important docs
- **Configs**: `snake_case.json`
- **Tests**: `test_*.py`

## Important Files

- `SOUL.md` - Agent persona (Nova Intellect's backstory, values, style)
- `Makefile` - Development commands (`make test`, `make lint`, etc.)
- `docker-compose.yml` - Redis + Weaviate infrastructure
- `.env.example` - Template for environment variables
- `README.md` - Project overview and quick start

---

**Last Updated**: 2026-02-06  
**Methodology**: GitHub Spec Kit + Spec-Driven Development
