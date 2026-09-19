"""Cheap, deterministic, rule-based priority score computed *before* download.

Lets the pipeline optionally skip low-value papers (``DOWNLOAD_ONLY_ABOVE_PRIORITY``)
without any LLM. Fully configurable via ``config.py`` tables. Higher = more important.
"""
from __future__ import annotations

from .config import (
    IMPORTANT_INSTITUTIONS, KEYWORD_POINTS, LOW_ACTION_KEYWORDS,
    WATCHLIST_POINTS_CAP, WATCHLIST_POINTS_PER_HIT,
)
from .schemas import ArticleMeta


def compute_priority(meta: ArticleMeta, watchlist: list[str] | None = None) -> int:
    """Return an integer priority score for a discovered paper."""
    haystack = f"{meta.title or ''}\n{meta.marketdesk_summary or ''}".lower()
    inst = (meta.institution or "").lower()
    score = 0

    # institution points (case-insensitive substring match; take the best single hit)
    inst_best = 0
    for name, pts in IMPORTANT_INSTITUTIONS.items():
        if name.lower() in inst or name.lower() in haystack:
            inst_best = max(inst_best, pts)
    score += inst_best

    # keyword points (additive)
    for kw, pts in KEYWORD_POINTS.items():
        if kw in haystack:
            score += pts

    # watchlist tickers
    if watchlist:
        hits = 0
        for sym in watchlist:
            s = sym.strip().lower()
            if s and s in haystack:
                hits += 1
        score += min(hits * WATCHLIST_POINTS_PER_HIT, WATCHLIST_POINTS_CAP)

    # low-actionability penalties
    for kw, pts in LOW_ACTION_KEYWORDS.items():
        if kw in haystack:
            score += pts  # pts are negative

    # feed-membership boosts
    if meta.is_top_pick:
        score += 15
    if meta.is_saved:
        score += 10

    return max(0, score)
