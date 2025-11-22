from __future__ import annotations

import os

from agents import HostedMCPTool

EXA_API_KEY = os.getenv("EXA_API_KEY")

if not EXA_API_KEY:
    raise RuntimeError(f"{EXA_API_KEY} is not set in environment/.env")


def create_exa_web_search_tool(
    *,
    require_approval: str = "never",
) -> HostedMCPTool:
    """
    Configure Exa's hosted MCP server as a HostedMCPTool.

    The EXA_API_KEY must be set in environment/.env and will be
    forwarded to the MCP server via env mapping.
    """
    api_key = os.getenv(EXA_API_KEY)
    if not api_key:
        raise RuntimeError(f"{EXA_API_KEY} is not set in environment/.env")

    return HostedMCPTool(
        tool_config={
            "type": "mcp",
            "server_label": "exa",
            "server_url": "https://mcp.exa.ai/mcp?tools=web_search_exa",
            "require_approval": require_approval,
            "env": {
                "EXA_API_KEY": api_key,
            },
        }
    )
