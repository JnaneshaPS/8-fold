from __future__ import annotations

import os

from agents import HostedMCPTool

EXA_API_KEY_NAME = "EXA_API_KEY"


def create_exa_web_search_tool(
    *,
    require_approval: str = "never",
) -> HostedMCPTool:
    api_key = os.getenv(EXA_API_KEY_NAME)
    if not api_key:
        raise RuntimeError(f"{EXA_API_KEY_NAME} is not set in environment/.env")

    return HostedMCPTool(
        tool_config={
            "type": "mcp",
            "server_label": "exa",
            "server_url": "https://mcp.exa.ai/mcp?tools=web_search_exa",
            "authorization": f"Bearer {api_key}",
            "require_approval": require_approval,
        }
    )
