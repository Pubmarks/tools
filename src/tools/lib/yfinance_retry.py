"""Retry yfinance calls on Yahoo Finance HTTP 429 rate limits."""
from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

from yfinance.exceptions import YFRateLimitError

logger = logging.getLogger(__name__)
T = TypeVar("T")


def yf_retry(func: Callable[[], T], max_retries: int = 3, base_delay: float = 2.0) -> T:
    for attempt in range(max_retries + 1):
        try:
            return func()
        except YFRateLimitError:
            if attempt < max_retries:
                delay = base_delay * (2**attempt)
                logger.warning(
                    "Yahoo Finance rate limited, retrying in %.0fs (attempt %s/%s)",
                    delay,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(delay)
            else:
                raise
