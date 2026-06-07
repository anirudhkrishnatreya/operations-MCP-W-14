import sys
from pathlib import Path

import yaml
from crewai import Agent
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

from llm_core import get_llama_instant, get_llama_versatile

# Primary MCP server — connects via SSE (must be running before the crew starts)
# Start it with: uv run python server/mcp_server.py
SERVER_PARAMS = {"url": "http://127.0.0.1:8000/sse"}

# Secondary fetch server — still uses Stdio (spawned inline by MCPServerAdapter)
FETCH_SERVER_PARAMS = StdioServerParameters(
    command=sys.executable,
    args=["server/mcp_fetch_server.py"],
)


def get_agents_config():
    config_path = Path(__file__).parent.parent / "config" / "agents.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_agents(mcp_tools: list, fetch_tools: list) -> tuple[Agent, Agent, Agent]:
    config = get_agents_config()

    # Operations Researcher gets search & read tools from the main server PLUS the fetch tool
    researcher_tools = [t for t in mcp_tools if t.name != "save_report"] + fetch_tools

    # Report Writer does NOT get the save_report tool anymore
    writer_tools = []

    # Fact checker gets no agent-level tools (tool is passed at task-level to prevent saving before approval)
    checker_tools = []

    researcher = Agent(
        config=config["researcher"],
        tools=researcher_tools,
        llm=get_llama_instant(),
        max_iter=5,  # prevent infinite loops
        verbose=True,
    )

    writer = Agent(
        config=config["writer"],
        tools=writer_tools,
        llm=get_llama_versatile(),
        max_iter=3,
        verbose=True,
    )

    fact_checker = Agent(
        config=config["fact_checker"],
        tools=checker_tools,
        llm=get_llama_instant(),
        max_iter=3,
        verbose=True,
    )

    return researcher, writer, fact_checker
