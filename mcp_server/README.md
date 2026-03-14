# Jerome7 MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that exposes Jerome7's core functionality as tools any MCP-compatible agent can call.

## Tools

| Tool | Description |
|------|-------------|
| `jerome7_daily` | Get today's personalised 7-minute session |
| `jerome7_pledge` | Register a new user |
| `jerome7_log` | Log a completed session (updates streak) |
| `jerome7_streak` | Get streak and consistency data |
| `jerome7_nudge` | Check if user needs a nudge today |
| `jerome7_pod_match` | Find/create an accountability pod |

## Setup

### 1. Install dependencies

```bash
pip install mcp httpx
```

Or add to your existing environment:

```bash
pip install -r requirements.txt
```

### 2. Configure the API URL

Set the `JEROME7_API_URL` environment variable. Defaults to `https://jerome7.com`.

```bash
export JEROME7_API_URL=http://localhost:8000   # for local dev
```

### 3. Run the server

```bash
# stdio transport (default — used by Claude Desktop, Claude Code, etc.)
python -m mcp_server.server

# or with the mcp CLI
mcp run mcp_server/server.py
```

## Claude Desktop configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "jerome7": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/Jerome 7 - github",
      "env": {
        "JEROME7_API_URL": "https://jerome7.com"
      }
    }
  }
}
```

## Claude Code configuration

Add to `.claude/settings.json` or run:

```bash
claude mcp add jerome7 -- python -m mcp_server.server
```
