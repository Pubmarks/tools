# tools

An MCP server that serves market and fundamentals data as a
set of tools. It fetches OHLCV bars, technical indicators, VWAP, company fundamentals, financial
statements, insider activity, company and global news (with article bodies), valuation stats, and
macroeconomic series — and returns them over a single Streamable-HTTP endpoint.

There is no model and no decision logic here. Every tool is a deterministic data fetcher: give it
a symbol and a date range, get the data back. Any MCP-capable client can connect to it.

## Highlights

- **One server, ten tools** — all market data behind a single `/mcp` endpoint.
- **Pure data, returned inline** — tools never write to your filesystem; they hand back the
  content and let you decide what to do with it.
- **Uniform results** — every tool returns the same `{ summary, artifacts[] }` shape.
- **Look-ahead-safe** — as-of date filtering on every time-sensitive tool, so historical queries
  never leak future data.
- **Self-sufficient** — tools that need price history fetch and cache it on demand; there is no
  required call order.
- **Runs anywhere** — a small container image, publicly pullable, no auth required for read-only
  market data.

## Quick start

Pull and run the published image:

```sh
podman pull ghcr.io/pubmarks/tools:latest
podman run -p 8080:8080 -e FRED_API_KEY=your_key ghcr.io/pubmarks/tools:latest
```

Or build it yourself:

```sh
podman build -t tools -f Containerfile .
podman run -p 8080:8080 -e FRED_API_KEY=your_key -v tools-cache:/data/cache tools
```

The MCP endpoint is then available at `http://localhost:8080/mcp`, with a health check at
`http://localhost:8080/healthz`.

## Connecting a client

Point any MCP client at the Streamable-HTTP endpoint and list the tools:

```jsonc
// example client config
{
  "mcpServers": {
    "tools": { "url": "http://localhost:8080/mcp" }
  }
}
```

Then call a tool, e.g. `fetch_ohlcv`:

```jsonc
{
  "name": "fetch_ohlcv",
  "arguments": { "symbol": "AAPL", "start": "2024-01-01", "end": "2025-01-01" }
}
```

## Tools

| Tool | What it returns | Key arguments |
|---|---|---|
| `fetch_ohlcv` | Daily OHLCV bars (CSV) | `symbol`, `start`, `end` |
| `fetch_indicators` | Technical indicators (text or CSV) | `symbol`, `indicators[]`, `curr_date`, *`lookback`, `mode`* |
| `fetch_vwap` | Volume-weighted average price (CSV) | `symbol`, *`bars`, `start`, `end`, `date`* |
| `fetch_fundamentals` | Company fundamentals summary (text) | `ticker` |
| `fetch_statement` | Balance sheet / cash flow / income (CSV) | `ticker`, `statement`, *`freq`, `curr_date`* |
| `fetch_avgpe` | Current vs. historical P/E valuation stats (text) | `ticker` |
| `fetch_insider` | Insider transactions (text) | `ticker` |
| `fetch_news` | Company headlines + article bodies | `ticker`, `start`, `end`, *`lookback`, `limit`, `include_pages`* |
| `fetch_global_news` | Broad market / macro headlines + bodies | *`curr_date`, `lookback`, `limit`, `include_pages`* |
| `fetch_macro_data` | Key macroeconomic series (text) | *`curr_date`* |

Supported indicators for `fetch_indicators`: `close_50_sma`, `close_200_sma`, `close_10_ema`,
`macd`, `macds`, `macdh`, `rsi`, `boll`, `boll_ub`, `boll_lb`, `atr`, `vwma`, `mfi`.

## Result format

Every tool returns the same envelope:

```jsonc
{
  "summary": "AAPL OHLCV 2024-01-01..2025-01-01 — 252 rows",
  "artifacts": [
    {
      "path_hint": "ohlcv.csv",             // a suggested filename
      "media_type": "text/csv",             // text/csv | text/plain | application/json | text/html
      "content": "Date,Open,High,...\n..."  // the data, inline
    }
  ]
}
```

Most tools return a single artifact. The news tools return several: a headline index plus one
artifact per fetched article body and a manifest.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `TOOLS_CACHE_DIR` | On-disk cache directory for price history | `/data/cache` |
| `TOOLS_OHLCV_CACHE_YEARS` | Rolling window of price history to cache | `5` |
| `FRED_API_KEY` | API key for macroeconomic series (required for `fetch_macro_data`) | — |
| `AVGPE_BASE_URL` | Base URL for the valuation-stats data source | — |
| `MCP_HOST` / `MCP_PORT` | Bind address for the server | `0.0.0.0` / `8080` |
| `LOG_LEVEL` | Log verbosity | `INFO` |

Copy `.env.example` to `.env` to set these locally.

## Development

```sh
uv sync
uv run pytest
uv run ruff check .
```

The server is built with the official MCP Python SDK (FastMCP) over Streamable HTTP. Data sources
are public market data providers; the price-history cache persists across runs on a mounted
volume.

## License

MIT
