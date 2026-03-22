"""
Economic Dashboard MCP Server
==============================
Exposes the Economic Dashboard API as a Model Context Protocol (MCP) server
so any MCP-compatible LLM assistant (Claude, GitHub Copilot, etc.) can call
live economic data tools.

Implemented tools
-----------------
  fred_series          — Fetch a FRED economic time series by ID
  fred_series_list     — List available FRED series with metadata
  stock_ohlcv          — Fetch stock OHLCV data from Yahoo Finance
  recession_probability — Current US recession probability with signals
  technical_indicators — Technical analysis features for a ticker
  sector_rotation      — Current sector rotation signals
  margin_risk          — Margin call risk score for a stock
  watermark_status     — Show incremental ingestion watermarks

Run
---
    python -m mcp_server.server
  or
    mcp_server/server.py

The server speaks stdio MCP by default (compatible with Codeespaces, Continue,
Claude Desktop, etc.).  Set ``MCP_TRANSPORT=sse`` for HTTP/SSE mode.

Configuration
-------------
  DASHBOARD_API_URL  — Base URL of the running FastAPI service (default: http://localhost:8000)
  MCP_TRANSPORT      — 'stdio' (default) or 'sse'
  MCP_SSE_HOST       — Host for SSE mode (default: 127.0.0.1)
  MCP_SSE_PORT       — Port for SSE mode (default: 8001)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DASHBOARD_API_URL = os.getenv("DASHBOARD_API_URL", "http://localhost:8000")
_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _api_get(path: str, params: dict | None = None, timeout: float = 15.0) -> Any:
    """
    Call the Economic Dashboard FastAPI and return the parsed JSON body.
    Raises ``httpx.HTTPStatusError`` on non-2xx responses.
    """
    url = f"{DASHBOARD_API_URL}{path}"
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, params=params or {})
        resp.raise_for_status()
        return resp.json()


def _safe_api_get(path: str, params: dict | None = None) -> str:
    """Call the API and return a formatted JSON string, or an error message."""
    try:
        data = _api_get(path, params)
        return json.dumps(data, indent=2, default=str)
    except httpx.ConnectError:
        return json.dumps({
            "error": "Cannot reach the Economic Dashboard API",
            "hint": f"Start the API first: uvicorn app:app --port 8000 (DASHBOARD_API_URL={DASHBOARD_API_URL})"
        })
    except httpx.HTTPStatusError as exc:
        return json.dumps({"error": f"API error {exc.response.status_code}", "detail": exc.response.text})
    except Exception as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server("economic-dashboard")


# ── Tool catalogue ──────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="fred_series",
            description=(
                "Fetch an economic time series from the Federal Reserve FRED database. "
                "Returns date/value pairs for the requested series ID (e.g. UNRATE, GDP, CPIAUCSL, DGS10)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "series_id": {
                        "type": "string",
                        "description": "FRED series identifier, e.g. 'UNRATE', 'GDP', 'CPIAUCSL', 'DGS10', 'T10Y2Y'",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Optional start date in YYYY-MM-DD format",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional end date in YYYY-MM-DD format",
                    },
                },
                "required": ["series_id"],
            },
        ),
        types.Tool(
            name="fred_series_list",
            description="List all available FRED economic series tracked by this dashboard, grouped by update frequency.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="stock_ohlcv",
            description=(
                "Fetch OHLCV (Open, High, Low, Close, Volume) stock price data from Yahoo Finance. "
                "Supports equities, ETFs, indices, and futures."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Yahoo Finance ticker symbol, e.g. 'AAPL', '^GSPC', 'SPY', 'GC=F'",
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["1d", "1wk", "1mo"],
                        "description": "Data interval (default: 1d)",
                    },
                },
                "required": ["ticker"],
            },
        ),
        types.Tool(
            name="recession_probability",
            description=(
                "Get the current US recession probability calculated using a multi-factor model. "
                "Combines yield curve, labor market, financial stress, economic activity, "
                "consumer confidence, housing, and stock market signals."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="technical_indicators",
            description=(
                "Compute technical analysis indicators for a stock ticker including RSI, MACD, "
                "Bollinger Bands, moving averages (SMA/EMA), ATR, OBV, and more."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol, e.g. 'AAPL', 'TSLA'",
                    },
                },
                "required": ["ticker"],
            },
        ),
        types.Tool(
            name="sector_rotation",
            description=(
                "Get current sector rotation signals for the 11 S&P 500 sectors. "
                "Shows relative strength, momentum, and whether we're in a risk-on or risk-off regime."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="margin_risk",
            description=(
                "Calculate margin call risk score for a single stock or the top-N highest-risk stocks. "
                "Combines leverage, volatility, options flow, and liquidity metrics."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Ticker symbol. Omit to get the top-N highest-risk stocks.",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Return top N stocks by risk score (used when ticker is omitted, default: 10)",
                    },
                },
            },
        ),
        types.Tool(
            name="watermark_status",
            description=(
                "Show the incremental ingestion watermarks — the last successfully fetched date for "
                "each data series. Useful for understanding data freshness."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


# ── Tool execution ──────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Dispatch an MCP tool call to the Economic Dashboard API."""

    result_text: str

    if name == "fred_series":
        series_id = arguments.get("series_id", "")
        if not series_id:
            result_text = json.dumps({"error": "series_id is required"})
        else:
            params = {
                k: arguments[k]
                for k in ("start_date", "end_date")
                if k in arguments
            }
            result_text = _safe_api_get(f"/v1/data/fred/{series_id.upper()}", params)

    elif name == "fred_series_list":
        # Enrich with local config — no API call needed
        try:
            from modules.data_series_config import FRED_SERIES_CONFIG
            summary = {
                freq: {
                    "description": cfg.get("description", ""),
                    "series": list(cfg["series"].keys()),
                    "series_ids": list(cfg["series"].values()),
                }
                for freq, cfg in FRED_SERIES_CONFIG.items()
            }
            result_text = json.dumps(summary, indent=2)
        except ImportError:
            result_text = _safe_api_get("/v1/data/fred")

    elif name == "stock_ohlcv":
        ticker = arguments.get("ticker", "")
        if not ticker:
            result_text = json.dumps({"error": "ticker is required"})
        else:
            params = {"interval": arguments.get("interval", "1d")}
            result_text = _safe_api_get(f"/v1/data/stocks/{ticker.upper()}", params)

    elif name == "recession_probability":
        result_text = _safe_api_get("/v1/predictions/recession")

    elif name == "technical_indicators":
        ticker = arguments.get("ticker", "")
        if not ticker:
            result_text = json.dumps({"error": "ticker is required"})
        else:
            result_text = _safe_api_get(f"/v1/features/technical/{ticker.upper()}")

    elif name == "sector_rotation":
        result_text = _safe_api_get("/v1/signals/sector-rotation")

    elif name == "margin_risk":
        ticker = arguments.get("ticker")
        if ticker:
            result_text = _safe_api_get(f"/v1/signals/margin-risk/{ticker.upper()}")
        else:
            top_n = arguments.get("top_n", 10)
            result_text = _safe_api_get("/v1/signals/margin-risk", {"top_n": top_n})

    elif name == "watermark_status":
        try:
            from modules.ingestion import get_incremental_fetcher
            fetcher = get_incremental_fetcher()
            wm_df = fetcher.get_all_watermarks()
            if wm_df.empty:
                result_text = json.dumps({"message": "No watermarks recorded yet. Run a data refresh first."})
            else:
                result_text = wm_df.to_json(orient="records", date_format="iso", indent=2)
        except Exception as exc:
            result_text = json.dumps({"error": str(exc)})

    else:
        result_text = json.dumps({"error": f"Unknown tool: {name}"})

    return [types.TextContent(type="text", text=result_text)]


# ── Entry point ─────────────────────────────────────────────────────────────

async def run_stdio():
    """Run the MCP server over stdio (default)."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="economic-dashboard",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )


def main():
    import asyncio

    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()

    if transport == "sse":
        # HTTP Server-Sent Events mode
        try:
            import uvicorn
            from mcp.server.sse import SseServerTransport
            from starlette.applications import Starlette
            from starlette.routing import Mount, Route

            sse = SseServerTransport("/messages/")

            async def handle_sse(request):
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    await server.run(
                        streams[0],
                        streams[1],
                        InitializationOptions(
                            server_name="economic-dashboard",
                            server_version="1.0.0",
                            capabilities=server.get_capabilities(
                                notification_options=None,
                                experimental_capabilities={},
                            ),
                        ),
                    )

            starlette_app = Starlette(
                routes=[
                    Route("/sse", endpoint=handle_sse),
                    Mount("/messages/", app=sse.handle_post_message),
                ]
            )
            host = os.getenv("MCP_SSE_HOST", "127.0.0.1")
            port = int(os.getenv("MCP_SSE_PORT", "8001"))
            print(f"Economic Dashboard MCP server (SSE) listening on {host}:{port}")
            uvicorn.run(starlette_app, host=host, port=port)
        except ImportError as exc:
            print(f"SSE transport unavailable: {exc}. Install uvicorn and starlette.")
            sys.exit(1)
    else:
        # Default: stdio
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
