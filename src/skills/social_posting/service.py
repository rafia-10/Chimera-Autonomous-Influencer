"""Social posting skill service."""

def post_to_platform(content: str, platform: str, mcp_client=None, confidence_threshold: float = 0.90):
    """
    Publishes content to the specified platform.
    
    Args:
        content: The text/media to post.
        platform: 'x' or 'linkedin'.
        mcp_client: The MCP client to use for publishing.
        confidence_threshold: Minimum confidence required (default 0.90).
    """
    pass
