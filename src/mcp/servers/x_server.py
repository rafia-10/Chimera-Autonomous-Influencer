#!/usr/bin/env python3
"""
Custom MCP server for X (formerly Twitter) integration.

Provides resources for mentions/timeline and tools for posting/replying.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import tweepy
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
app = Server("x-server")

# Twitter API client
twitter_client: tweepy.Client = None


def init_twitter_client():
    """Initialize Twitter API v2 client."""
    global twitter_client
    
    if twitter_client is not None:
        return
    
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_SECRET")
    
    if not all([bearer_token, api_key, api_secret, access_token, access_secret]):
        raise ValueError("Missing Twitter API credentials in environment variables")
    
    twitter_client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
        wait_on_rate_limit=True,
    )
    
    logger.info("Twitter API client initialized")


@app.list_resources()
async def list_resources() -> List[Resource]:
    """List available X/Twitter resources."""
    return [
        Resource(
            uri="x://mentions/recent",
            name="Recent Mentions",
            description="Latest mentions of the agent account",
            mimeType="application/json",
        ),
        Resource(
            uri="x://timeline/own",
            name="Own Timeline",
            description="Agent's own posted tweets",
            mimeType="application/json",
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read content from an X/Twitter resource."""
    init_twitter_client()
    
    import json
    from urllib.parse import urlparse
    
    parsed = urlparse(uri)
    
    if parsed.scheme != "x":
        raise ValueError(f"Unsupported URI scheme: {parsed.scheme}")
    
    path = parsed.netloc + parsed.path
    
    try:
        if path == "mentions/recent":
            # Get my user ID first
            me = twitter_client.get_me()
            user_id = me.data.id
            
            # Fetch mentions
            mentions = twitter_client.get_users_mentions(
                user_id,
                max_results=10,
                tweet_fields=["created_at", "author_id", "text"],
            )
            
            results = []
            if mentions.data:
                for tweet in mentions.data:
                    results.append({
                        "id": tweet.id,
                        "text": tweet.text,
                        "author_id": tweet.author_id,
                        "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    })
            
            return json.dumps(results, indent=2)
        
        elif path == "timeline/own":
            # Get my user ID
            me = twitter_client.get_me()
            user_id = me.data.id
            
            # Fetch own tweets
            tweets = twitter_client.get_users_tweets(
                user_id,
                max_results=10,
                tweet_fields=["created_at", "public_metrics"],
            )
            
            results = []
            if tweets.data:
                for tweet in tweets.data:
                    results.append({
                        "id": tweet.id,
                        "text": tweet.text,
                        "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                        "metrics": tweet.public_metrics if hasattr(tweet, "public_metrics") else {},
                    })
            
            return json.dumps(results, indent=2)
        
        else:
            raise ValueError(f"Unknown resource path: {path}")
    
    except Exception as e:
        logger.error(f"Error reading X resource {uri}: {e}")
        return json.dumps({"error": str(e)})


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available X/Twitter tools."""
    return [
        Tool(
            name="post_tweet",
            description="Post a new tweet to X (formerly Twitter)",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Tweet text content (max 280 characters)",
                        "maxLength": 280,
                    },
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="reply_tweet",
            description="Reply to a tweet",
            inputSchema={
                "type": "object",
                "properties": {
                    "tweet_id": {
                        "type": "string",
                        "description": "ID of the tweet to reply to",
                    },
                    "text": {
                        "type": "string",
                        "description": "Reply text content",
                        "maxLength": 280,
                    },
                },
                "required": ["tweet_id", "text"],
            },
        ),
        Tool(
            name="like_tweet",
            description="Like a tweet",
            inputSchema={
                "type": "object",
                "properties": {
                    "tweet_id": {
                        "type": "string",
                        "description": "ID of the tweet to like",
                    },
                },
                "required": ["tweet_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Execute an X/Twitter tool."""
    init_twitter_client()
    
    # Check dry-run mode
    dry_run = os.getenv("DRY_RUN_MODE", "true").lower() == "true"
    
    try:
        if name == "post_tweet":
            text = arguments["text"]
            
            if dry_run:
                logger.info(f"[DRY RUN] Would post tweet: {text}")
                return [TextContent(
                    type="text",
                    text=f"[DRY RUN] Tweet posted successfully: {text}"
                )]
            
            response = twitter_client.create_tweet(text=text)
            tweet_id = response.data["id"]
            
            return [TextContent(
                type="text",
                text=f"Tweet posted successfully. ID: {tweet_id}"
            )]
        
        elif name == "reply_tweet":
            tweet_id = arguments["tweet_id"]
            text = arguments["text"]
            
            if dry_run:
                logger.info(f"[DRY RUN] Would reply to {tweet_id}: {text}")
                return [TextContent(
                    type="text",
                    text=f"[DRY RUN] Reply posted to {tweet_id}"
                )]
            
            response = twitter_client.create_tweet(
                text=text,
                in_reply_to_tweet_id=tweet_id
            )
            reply_id = response.data["id"]
            
            return [TextContent(
                type="text",
                text=f"Reply posted successfully. ID: {reply_id}"
            )]
        
        elif name == "like_tweet":
            tweet_id = arguments["tweet_id"]
            
            if dry_run:
                logger.info(f"[DRY RUN] Would like tweet: {tweet_id}")
                return [TextContent(
                    type="text",
                    text=f"[DRY RUN] Liked tweet {tweet_id}"
                )]
            
            me = twitter_client.get_me()
            user_id = me.data.id
            
            twitter_client.like(user_id, tweet_id)
            
            return [TextContent(
                type="text",
                text=f"Liked tweet {tweet_id}"
            )]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Run the MCP server."""
    logger.info("Starting X (Twitter) MCP server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
