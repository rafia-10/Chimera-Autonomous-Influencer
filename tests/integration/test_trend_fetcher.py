import pytest
from pathlib import Path
import json
from src.perception.trend_detector import TrendDetector
from src.mcp import MCPClient

@pytest.mark.asyncio
async def test_trend_data_structure_alignment():
    """
    Asserts that the trend data structure matches the API contract in technical.md.
    Note: This test is EXPECTED TO FAIL initially as the implementation is missing.
    """
    # 1. Setup mock client and detector
    client = MCPClient()
    detector = TrendDetector(mcp_client=client)
    
    # 2. Attempt to fetch trends
    # This should fail/raise because TrendDetector or fetch_trends isn't implemented or doesn't match
    trends = await detector.fetch_trends(source="news://tech-feed")
    
    # 3. Validate against Technical Spec Contract
    # Contract from specs/technical.md:
    # {
    #   "id": "article-123",
    #   "title": "...",
    #   "url": "...",
    #   "published_at": "...",
    #   "source": "...",
    #   "summary": "...",
    #   "keywords": ["..."],
    #   "relevance_score": 0.92
    # }
    
    assert isinstance(trends, list)
    assert len(trends) > 0
    
    first_trend = trends[0]
    required_keys = {
        "id", "title", "url", "published_at", 
        "source", "summary", "keywords", "relevance_score"
    }
    
    assert required_keys.issubset(first_trend.keys()), f"Missing keys in trend data: {required_keys - first_trend.keys()}"
    assert isinstance(first_trend["relevance_score"], float)
    assert isinstance(first_trend["keywords"], list)
