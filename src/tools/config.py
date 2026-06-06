from __future__ import annotations

import os


class _Config:
    @property
    def cache_dir(self) -> str:
        return os.environ.get("TOOLS_CACHE_DIR", "/data/cache")

    @property
    def ohlcv_cache_years(self) -> int:
        raw = os.environ.get("TOOLS_OHLCV_CACHE_YEARS", "5")
        try:
            return max(1, min(int(raw), 30))
        except ValueError:
            return 5

    @property
    def fred_api_key(self) -> str:
        return os.environ.get("FRED_API_KEY", "")

    @property
    def avgpe_base_url(self) -> str:
        return os.environ.get(
            "AVGPE_BASE_URL",
            "https://pubmarks.github.io/datasets/stocks/{ticker}",
        )

    @property
    def host(self) -> str:
        return os.environ.get("MCP_HOST", "0.0.0.0")

    @property
    def port(self) -> int:
        return int(os.environ.get("MCP_PORT", "8080"))

    @property
    def log_level(self) -> str:
        return os.environ.get("LOG_LEVEL", "INFO")


cfg = _Config()
