"""Verify all 10 tools are registered on the MCP server."""
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
from tools.app import mcp

EXPECTED_TOOLS = {
    "fetch_ohlcv",
    "fetch_indicators",
    "fetch_vwap",
    "fetch_fundamentals",
    "fetch_statement",
    "fetch_avgpe",
    "fetch_insider",
    "fetch_news",
    "fetch_global_news",
    "fetch_macro_data",
}


def _registered() -> set[str]:
    return {t.name for t in mcp._tool_manager._tools.values()}  # noqa: SLF001


def test_all_tools_registered():
    registered = _registered()
    assert EXPECTED_TOOLS == registered, (
        f"Missing: {EXPECTED_TOOLS - registered}, Extra: {registered - EXPECTED_TOOLS}"
    )


def test_tool_count():
    assert len(_registered()) == 10
