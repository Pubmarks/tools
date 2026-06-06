"""MCP server entrypoint — Streamable HTTP transport with /healthz."""
from __future__ import annotations

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from tools.app import mcp
from tools.config import cfg

# Import tool modules so their @mcp.tool() decorators register with the mcp instance.
import tools.tools.avgpe  # noqa: F401
import tools.tools.fundamentals  # noqa: F401
import tools.tools.global_news  # noqa: F401
import tools.tools.indicators  # noqa: F401
import tools.tools.insider  # noqa: F401
import tools.tools.macro  # noqa: F401
import tools.tools.news  # noqa: F401
import tools.tools.ohlcv  # noqa: F401
import tools.tools.statement  # noqa: F401
import tools.tools.vwap  # noqa: F401


@mcp.custom_route("/healthz", methods=["GET"])
async def _healthz(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


def create_app() -> Starlette:
    return mcp.streamable_http_app()


if __name__ == "__main__":
    uvicorn.run(
        "tools.server:create_app",
        factory=True,
        host=cfg.host,
        port=cfg.port,
        log_level=cfg.log_level.lower(),
    )
