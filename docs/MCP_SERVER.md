# MCP Server — Economic Dashboard

## Overview

The Economic Dashboard exposes a fully-featured **MCP server** (`mcp_server/server.py`)
that LLM assistants (Claude, GitHub Copilot, etc.) can use to query live economic data.

## Quick Start

```bash
# Run in stdio mode (default — for Claude Desktop / VS Code Copilot)
python -m mcp_server

# Run in SSE mode (HTTP, for browser-based tools)
MCP_TRANSPORT=sse python -m mcp_server
```

### VS Code / GitHub Copilot
The server is pre-configured in `.vscode/mcp.json`.  
Copilot will automatically discover it when the workspace is opened.

### Claude Desktop
Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "economic-dashboard": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "/path/to/Economic-Dashboard-API",
      "env": { "DASHBOARD_API_URL": "http://localhost:8000" }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `fred_series` | Fetch a FRED time series by series ID (e.g. UNRATE, GDP, DGS10) |
| `fred_series_list` | List all tracked FRED series grouped by update frequency |
| `stock_ohlcv` | Fetch OHLCV data for any Yahoo Finance ticker |
| `recession_probability` | Current US recession probability with signal breakdown |
| `technical_indicators` | RSI, MACD, Bollinger Bands, SMA/EMA, ATR, OBV for any ticker |
| `sector_rotation` | S&P 500 sector rotation signals and risk-on/off regime |
| `margin_risk` | Margin call risk score — single ticker or top-N ranking |
| `watermark_status` | Show incremental ingestion watermarks / data freshness |

## Example Prompts

Once the MCP server is active in your assistant:

- _"What is the current US recession probability?"_
- _"Show me the last 2 years of the 10Y-2Y Treasury spread"_
- _"What are the technical indicators for NVDA right now?"_
- _"Which sectors are leading in the current rotation cycle?"_
- _"What stocks have the highest margin call risk?"_

## Architecture

```
User / LLM assistant
        │
        ▼ MCP protocol (stdio or SSE)
mcp_server/server.py   ← tool definitions + dispatch
        │
        ▼ HTTP REST
FastAPI (api/main.py)  ← existing endpoints at /v1/...
        │
        ▼
modules/ + DuckDB/PostgreSQL   ← data + ML models
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHBOARD_API_URL` | `http://localhost:8000` | Base URL of the running FastAPI service |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `sse` |
| `MCP_SSE_HOST` | `127.0.0.1` | Host for SSE mode |
| `MCP_SSE_PORT` | `8001` | Port for SSE mode |
