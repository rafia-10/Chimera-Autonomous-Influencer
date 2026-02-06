# Chimera Autonomous Influencer - Makefile

.PHONY: help install test lint format clean docker-up docker-down run-dev

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install all dependencies"
	@echo "  test         - Run all tests"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-int     - Run integration tests only"
	@echo "  lint         - Run linters (ruff, mypy)"
	@echo "  format       - Format code with black"
	@echo "  clean        - Clean build artifacts"
	@echo "  docker-up    - Start infrastructure (Redis, Weaviate)"
	@echo "  docker-down  - Stop infrastructure"
	@echo "  run-dev      - Run in development mode (dry-run)"
	@echo "  run-prod     - Run in production mode"
	@echo "  spec-check   - Verify code aligns with specs"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

setup: install-dev docker-up
	@echo "Setup complete! Run 'make test' to verify."

# Testing
test:
	pytest tests/ -v --cov=src --cov-report=html

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v --asyncio-mode=auto

test-e2e:
	pytest tests/e2e/ -v --asyncio-mode=auto

test-watch:
	pytest-watch tests/ -v

# Code quality
lint:
	ruff check src/ tests/
	mypy src/

format:
	black src/ tests/
	ruff check --fix src/ tests/

check: lint test

# Spec alignment verification
spec-check:
	@echo "Checking spec alignment..."
	@python scripts/spec_check.py

# Infrastructure
docker-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@docker-compose ps

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# Running the application
run-dev:
	DRY_RUN_MODE=true python -m src.main

run-prod:
	python -m src.main

run-planner:
	python -m src.core.planner.service

run-worker:
	python -m src.core.worker.service

run-judge:
	python -m src.core.judge.service

# MCP servers
mcp-news:
	python src/mcp/servers/news_server.py

mcp-x:
	python src/mcp/servers/x_server.py

mcp-linkedin:
	python src/mcp/servers/linkedin_server.py

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info

# Database management
db-reset:
	docker-compose down -v
	docker-compose up -d
	@echo "Databases reset"

# Development utilities
shell:
	python -i -c "from src.memory import *; from src.mcp import *; from src.models import *"

# CI/CD simulation
ci: lint test spec-check
	@echo "CI checks passed!"
