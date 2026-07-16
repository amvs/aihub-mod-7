# app/mcp_client.py
import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
import logging

logger = logging.getLogger("uvicorn.error")

# Config for the MCP server you want to run (e.g., SQLite DB inspector, filesystem, etc.)
server_params = StdioServerParameters(
    command="uv",
    args=["run", "mcp-server-sqlite", "--db-path", "company_database.db"]
)

# Global variables to hold our active session and active converted tools
_exit_stack = AsyncExitStack()
active_mcp_tools = []

async def init_mcp_client():
    """Initializes the connection to the MCP server and registers the tools."""
    global active_mcp_tools
    try:
        logger.info("Connecting to MCP Server...")
        # Start the background stdio client process
        stdio_transport = await _exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport
        
        # Open client-server session
        session = await _exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        
        # Automatically load and convert all tools exposed by the server to LangChain format
        active_mcp_tools = await load_mcp_tools(session)
        logger.info(f"MCP Connection established! Loaded {len(active_mcp_tools)} tools.")
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
        raise e

async def close_mcp_client():
    """Cleans up and gracefully shuts down sub-processes and sessions."""
    logger.info("Shutting down MCP connection...")
    await _exit_stack.aclose()

def get_tools():
    """Access function for graph.py to fetch active tools."""
    logger.info(f"Fetching {len(active_mcp_tools)} active MCP tools.")
    logger.info("Active MCP Tools: " + ", ".join([tool.name for tool in active_mcp_tools]))
    return active_mcp_tools