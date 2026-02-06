"""
MCP (Model Context Protocol) client wrapper.

Provides centralized interface for interacting with MCP servers.
Handles connection management, resource polling, and tool invocation.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Centralized MCP client for the agent runtime.
    
    Manages connections to multiple MCP servers and provides
    unified interface for resources and tools.
    """
    
    def __init__(self):
        """Initialize the MCP client."""
        self.sessions: Dict[str, ClientSession] = {}
        self.server_configs: Dict[str, StdioServerParameters] = {}
    
    def register_server(
        self,
        server_name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        """
        Register an MCP server configuration.
        
        Args:
            server_name: Unique name for this server
            command: Command to start the server
            args: Command-line arguments
            env: Environment variables
        """
        self.server_configs[server_name] = StdioServerParameters(
            command=command,
            args=args or [],
            env=env,
        )
        logger.info(f"Registered MCP server: {server_name}")
    
    async def connect(self, server_name: str) -> ClientSession:
        """
        Connect to a registered MCP server.
        
        Args:
            server_name: Name of the server to connect to
            
        Returns:
            Connected ClientSession
            
        Raises:
            ValueError: If server not registered
        """
        if server_name not in self.server_configs:
            raise ValueError(f"Server '{server_name}' not registered")
        
        if server_name in self.sessions:
            return self.sessions[server_name]  # Already connected
        
        server_params = self.server_configs[server_name]
        
        # Start stdio client
        read, write = await stdio_client(server_params)
        session = ClientSession(read, write)
        
        await session.initialize()
        
        self.sessions[server_name] = session
        logger.info(f"Connected to MCP server: {server_name}")
        
        return session
    
    async def disconnect(self, server_name: str):
        """
        Disconnect from an MCP server.
        
        Args:
            server_name: Name of the server to disconnect from
        """
        if server_name in self.sessions:
            session = self.sessions[server_name]
            # MCP sessions don't have explicit close, but we remove from cache
            del self.sessions[server_name]
            logger.info(f"Disconnected from MCP server: {server_name}")
    
    async def disconnect_all(self):
        """Disconnect from all MCP servers."""
        server_names = list(self.sessions.keys())
        for server_name in server_names:
            await self.disconnect(server_name)
    
    async def list_resources(self, server_name: str) -> List[Dict[str, Any]]:
        """
        List all resources available on a server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            List of resource definitions
        """
        session = await self.connect(server_name)
        response = await session.list_resources()
        
        resources = []
        for resource in response.resources:
            resources.append({
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mime_type": getattr(resource, "mimeType", None),
            })
        
        return resources
    
    async def read_resource(self, server_name: str, uri: str) -> Dict[str, Any]:
        """
        Read content from an MCP resource.
        
        Args:
            server_name: Name of the server hosting the resource
            uri: Resource URI (e.g., "news://tech/latest")
            
        Returns:
            Resource content and metadata
        """
        session = await self.connect(server_name)
        response = await session.read_resource(uri)
        
        # Extract contents
        contents = []
        for content in response.contents:
            contents.append({
                "uri": content.uri,
                "mime_type": getattr(content, "mimeType", None),
                "text": getattr(content, "text", None),
                "blob": getattr(content, "blob", None),
            })
        
        return {
            "uri": uri,
            "contents": contents,
        }
    
    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """
        List all tools available on a server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            List of tool definitions
        """
        session = await self.connect(server_name)
        response = await session.list_tools()
        
        tools = []
        for tool in response.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            })
        
        return tools
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Invoke an MCP tool.
        
        Args:
            server_name: Name of the server hosting the tool
            tool_name: Name of the tool to call
            arguments: Tool arguments as a dictionary
            
        Returns:
            List of tool execution results
        """
        session = await self.connect(server_name)
        
        logger.info(f"Calling tool {tool_name} on {server_name} with args: {arguments}")
        
        response = await session.call_tool(tool_name, arguments)
        
        # Extract results
        results = []
        for content in response.content:
            results.append({
                "type": content.type,
                "text": getattr(content, "text", None),
                "data": getattr(content, "data", None),
            })
        
        return results
    
    async def get_all_available_resources(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all resources from all connected servers.
        
        Returns:
            Dictionary mapping server names to their available resources
        """
        all_resources = {}
        
        for server_name in self.server_configs.keys():
            try:
                resources = await self.list_resources(server_name)
                all_resources[server_name] = resources
            except Exception as e:
                logger.error(f"Failed to list resources from {server_name}: {e}")
                all_resources[server_name] = []
        
        return all_resources
    
    async def get_all_available_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all tools from all connected servers.
        
        Returns:
            Dictionary mapping server names to their available tools
        """
        all_tools = {}
        
        for server_name in self.server_configs.keys():
            try:
                tools = await self.list_tools(server_name)
                all_tools[server_name] = tools
            except Exception as e:
                logger.error(f"Failed to list tools from {server_name}: {e}")
                all_tools[server_name] = []
        
        return all_tools


# Singleton instance
_instance: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get or create the singleton MCPClient instance."""
    global _instance
    if _instance is None:
        _instance = MCPClient()
    return _instance
