import pytest
import inspect
from src.skills.social_posting import post_to_platform
from src.skills.trend_detection import detect_trends
from src.skills.audience_engagement import process_engagement

def test_social_posting_interface():
    """Validates social_posting signature matches SKILL.md contract."""
    # Contract: post_to_platform(content: str, platform: str, mcp_client: MCPClient, confidence_threshold: float = 0.90)
    sig = inspect.signature(post_to_platform)
    params = sig.parameters
    
    assert "content" in params
    assert "platform" in params
    assert "mcp_client" in params
    assert "confidence_threshold" in params
    assert params["confidence_threshold"].default == 0.90

def test_trend_detection_interface():
    """Validates trend_detection signature matches SKILL.md contract."""
    # Contract: detect_trends(news_sources: list[str], mcp_client: MCPClient, relevance_threshold: float = 0.75)
    sig = inspect.signature(detect_trends)
    params = sig.parameters
    
    assert "news_sources" in params
    assert "mcp_client" in params
    assert "relevance_threshold" in params
    assert params["relevance_threshold"].default == 0.75

def test_audience_engagement_interface():
    """Validates audience_engagement signature matches SKILL.md contract."""
    # Contract: process_engagement(mention: MentionData, conversation_history: list[dict], mcp_client: MCPClient)
    sig = inspect.signature(process_engagement)
    params = sig.parameters
    
    assert "mention" in params
    assert "conversation_history" in params
    assert "mcp_client" in params
