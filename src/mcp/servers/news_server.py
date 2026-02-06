#!/usr/bin/env python3
"""
Custom MCP server for tech news aggregation.

Provides resources for TechCrunch, AI research, and trending tech topics.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("news-server")

# Cache for news articles (simulates persistence)
ARTICLE_CACHE: Dict[str, List[Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


async def fetch_techcrunch_rss() -> List[Dict[str, Any]]:
    """Fetch latest articles from TechCrunch RSS feed."""
    url = "https://techcrunch.com/feed/"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            
            # Parse RSS (simplified - in production use feedparser)
            # For now, return mock data
            articles = [
                {
                    "title": "AI Startup Raises $100M Series B",
                    "summary": "Breaking: New AI infrastructure startup secures massive funding round led by top VCs.",
                    "url": "https://techcrunch.com/2026/02/05/ai-startup-funding/",
                    "published": datetime.utcnow().isoformat(),
                    "source": "TechCrunch",
                },
                {
                    "title": "New Open Source LLM Released",
                    "summary": "Community celebrates as researchers release state-of-the-art language model with permissive license.",
                    "url": "https://techcrunch.com/2026/02/05/open-source-llm/",
                    "published": datetime.utcnow().isoformat(),
                    "source": "TechCrunch",
                },
            ]
            
            return articles
            
        except Exception as e:
            logger.error(f"Failed to fetch TechCrunch RSS: {e}")
            return []


async def fetch_ai_research() -> List[Dict[str, Any]]:
    """Fetch latest AI research papers and blog posts."""
    # Mock AI research articles
    articles = [
        {
            "title": "Advances in Multimodal Reasoning",
            "summary": "New research shows significant improvements in AI systems' ability to reason across text, images, and code.",
            "url": "https://arxiv.org/abs/2602.12345",
            "published": datetime.utcnow().isoformat(),
            "source": "ArXiv",
        },
        {
            "title": "Scaling Laws for Agent Systems",
            "summary": "Researchers discover unexpected scaling behaviors in multi-agent AI systems.",
            "url": "https://arxiv.org/abs/2602.12346",
            "published": datetime.utcnow().isoformat(),
            "source": "ArXiv",
        },
    ]
    
    return articles


@app.list_resources()
async def list_resources() -> List[Resource]:
    """List available news resources."""
    return [
        Resource(
            uri="news://tech/latest",
            name="Latest Tech News",
            description="Aggregated tech news from TechCrunch and similar sources",
            mimeType="application/json",
        ),
        Resource(
            uri="news://ai/research",
            name="AI Research Updates",
            description="Latest AI research papers and insights",
            mimeType="application/json",
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read content from a news resource."""
    parsed = urlparse(uri)
    
    if parsed.scheme != "news":
        raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")
    
    path = parsed.netloc + parsed.path
    
    # Check cache
    cache_key = uri
    if cache_key in ARTICLE_CACHE:
        cached_data, timestamp = ARTICLE_CACHE[cache_key]
        if (datetime.utcnow().timestamp() - timestamp) < CACHE_TTL_SECONDS:
            logger.info(f"Returning cached data for {uri}")
            return json.dumps(cached_data, indent=2)
    
    # Fetch fresh data
    if path == "tech/latest":
        articles = await fetch_techcrunch_rss()
    elif path == "ai/research":
        articles = await fetch_ai_research()
    else:
        raise ValueError(f"Unknown resource path: {path}")
    
    # Update cache
    ARTICLE_CACHE[cache_key] = (articles, datetime.utcnow().timestamp())
    
    return json.dumps(articles, indent=2)


async def main():
    """Run the MCP server."""
    logger.info("Starting tech news MCP server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
