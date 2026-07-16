"""Market-data tools — MCP server and importable library."""
from __future__ import annotations

import sys

import tools.tools.avgpe as avgpe
import tools.tools.fundamentals as fundamentals
import tools.tools.global_news as global_news
import tools.tools.indicators as indicators
import tools.tools.insider as insider
import tools.tools.macro as macro
import tools.tools.news as news
import tools.tools.ohlcv as ohlcv
import tools.tools.statement as statement
import tools.tools.vwap as vwap

for _name, _mod in {
    "avgpe": avgpe,
    "fundamentals": fundamentals,
    "global_news": global_news,
    "indicators": indicators,
    "insider": insider,
    "macro": macro,
    "news": news,
    "ohlcv": ohlcv,
    "statement": statement,
    "vwap": vwap,
}.items():
    sys.modules[f"{__name__}.{_name}"] = _mod

__all__ = [
    "avgpe",
    "fundamentals",
    "global_news",
    "indicators",
    "insider",
    "macro",
    "news",
    "ohlcv",
    "statement",
    "vwap",
]
