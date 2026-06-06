"""Cache directory management (configurable via environment variables)."""
from __future__ import annotations

import os
from pathlib import Path


def default_cache_dir() -> Path:
    base = os.environ.get("TOOLS_CACHE_DIR")
    if base:
        return Path(base).expanduser().resolve()
    return Path("/data/cache")


def ensure_cache_dir() -> Path:
    d = default_cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d
