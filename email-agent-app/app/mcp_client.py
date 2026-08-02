# app/mcp_client.py
import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.tools import StructuredTool
from urllib.parse import urlparse
import socket
import logging

logger = logging.getLogger("uvicorn.error")

# Config for the MCP server you want to run
# web fetch example to fetch web pages linked in emails and extract content
server_params = StdioServerParameters(
    command="uvx",
    args=["mcp-server-fetch"]
)

# # Internet search example, using Brave Search API (requires an API key)
# server_params = StdioServerParameters(
#     command="npx",
#     args=["-y", "@modelcontextprotocol/server-brave-search"],
#     env={"BRAVE_API_KEY": "your_brave_api_key_here"}
# )

# # Github example, requires a personal access token with repo permissions
# server_params = StdioServerParameters(
#     command="docker",
#     args=["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server"],
#     env={"GITHUB_PERSONAL_ACCESS_TOKEN": "your_github_token_here"}
# )

# # email example
# server_params = StdioServerParameters(
#     command="npx",
#     args=["-y", "@lobehub/mcp-gmail"],  # Dynamically downloads and runs the server
#     env={
#         "EMAIL_ADDRESS": "your_email@gmail.com",
#         "EMAIL_PASSWORD": "your_16_char_app_password",  # app password - generated in google account settings
#         "IMAP_HOST": "imap.gmail.com",
#         "IMAP_PORT": "993",
#         "SMTP_HOST": "smtp.gmail.com",
#         "SMTP_PORT": "587"
#     }
# )

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

def apply_fetch_guardrails(raw_mcp_fetch_tool):
    """
    Intercepts the raw MCP fetch tool and wraps it with safety checks
    to prevent SSRF attacks and enforce domain whitelisting.
    """
    async def guarded_fetch(url: str, **kwargs):
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return "Error: Invalid URL."

            # Block Localhost / Private IP Subnets (SSRF Protection)
            # Resolve the domain to an IP address to prevent DNS-rebinding bypasses
            ip_address = socket.gethostbyname(hostname)
            
            private_ranges = [
                "127.",         # Localhost
                "10.",          # Private Class A
                "172.16.",      # Private Class B
                "192.168.",     # Private Class C
                "169.254."      # Cloud metadata service (AWS/GCP/Azure)
            ]
            
            if any(ip_address.startswith(prefix) for prefix in private_ranges):
                return (
                    "Security Block: Access to local or internal cloud network resources is prohibited."
                )

            # Strict Domain Whitelisting (Optional but highly recommended)
            # Example, if we only want our email agent researching our own docs, GitHub, or Wikipedia
            ALLOWED_DOMAINS = ["docs.mycompany.com", "github.com", "wikipedia.org"]
            
            # Allow users to pass subdomains (e.g., api.github.com)
            is_allowed = any(hostname == domain or hostname.endswith("." + domain) for domain in ALLOWED_DOMAINS)
            
            if not is_allowed:
                return (
                    f"Security Block: The domain '{hostname}' is not on the company whitelist. "
                    f"You may only search these trusted domains: {ALLOWED_DOMAINS}"
                )

            # ✅ Passed all checks! Execute the real, underlying MCP Fetch tool
            return await raw_mcp_fetch_tool.ainvoke({"url": url, **kwargs})
            
        except Exception as e:
            return f"Error executing fetch: {str(e)}"

    # Re-package the guardrailed function as a LangChain-compatible tool
    # keeping the original description and schema intact so the LLM still understands it
    return StructuredTool.from_function(
        coroutine=guarded_fetch,
        name=raw_mcp_fetch_tool.name,
        description=raw_mcp_fetch_tool.description,
        args_schema=raw_mcp_fetch_tool.args_schema
    )