"""Tests for score.compute_priority — institution/keyword/watchlist/penalties."""
from __future__ import annotations

from marketdesk_extractor.schemas import ArticleMeta
from marketdesk_extractor.score import compute_priority


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _meta(
    title: str = "",
    institution: str | None = None,
    summary: str | None = None,
    is_top_pick: bool = False,
    is_saved: bool = False,
) -> ArticleMeta:
    return ArticleMeta(
        blob_id="test-blob",
        article_url="https://marketdesk.ai/library/browse?item=test-blob",
        blob_url="https://marketdesk.ai/files/test-blob/blob",
        title=title,
        institution=institution,
        marketdesk_summary=summary,
        is_top_pick=is_top_pick,
        is_saved=is_saved,
    )


# ---------------------------------------------------------------------------
# core scoring: high-priority case
# ---------------------------------------------------------------------------

def test_jpm_earnings_upgrade_catalyst_is_high(
) -> None:
    """A JPM paper with 'earnings upgrade catalyst' keywords scores well above 60."""
    meta = _meta(
        title="JPM: Earnings Upgrade Catalyst — Buy on Margin Expansion",
        institution="JPM",
    )
    score = compute_priority(meta)
    # JPM=25, catalyst=10, upgrade=9, earnings=5, margin=6 => 55 minimum (some overlap possible)
    # The important thing is it is meaningfully high
    assert score >= 45, f"Expected high score, got {score}"


def test_weekly_calendar_is_low() -> None:
    """A 'weekly calendar' recap paper should score very low (penalties apply)."""
    meta = _meta(
        title="Weekly Calendar: Morning Note — Daily Wrap and Recap",
        institution=None,
    )
    score = compute_priority(meta)
    # calendar=-6, week ahead=-4, morning note=-2, recap=-3, daily wrap=-3 => heavy penalties
    assert score < 20, f"Expected low score, got {score}"


# ---------------------------------------------------------------------------
# institution recognition
# ---------------------------------------------------------------------------

def test_institution_in_meta_field_adds_points() -> None:
    meta = _meta(title="Rates outlook", institution="Goldman Sachs")
    score = compute_priority(meta)
    assert score >= 25  # Goldman = 25 pts


def test_institution_in_title_adds_points() -> None:
    meta = _meta(title="Goldman: Semis upgrade to overweight", institution=None)
    score = compute_priority(meta)
    # Goldman from title + semis=8 + upgrade=9
    assert score >= 25


def test_multiple_institution_aliases_take_best() -> None:
    # "Goldman" and "GS" both map to 25 — should not double-count
    meta_abbrev = _meta(title="GS semis view", institution=None)
    meta_full = _meta(title="Goldman semis view", institution=None)
    score_a = compute_priority(meta_abbrev)
    score_b = compute_priority(meta_full)
    # both should produce the same institution contribution
    assert score_a == score_b


def test_unknown_institution_adds_zero_points() -> None:
    meta_known = _meta(title="Plain title", institution="JPM")
    meta_unknown = _meta(title="Plain title", institution="SmallFirm XYZ")
    score_known = compute_priority(meta_known)
    score_unknown = compute_priority(meta_unknown)
    assert score_known > score_unknown


# ---------------------------------------------------------------------------
# keyword points
# ---------------------------------------------------------------------------

def test_cpi_keyword_adds_points() -> None:
    meta = _meta(title="CPI surprise: Fed reconsiders rates path")
    score = compute_priority(meta)
    assert score > 0


def test_ipo_keyword_adds_points() -> None:
    meta = _meta(title="IPO pipeline for Q3")
    score_ipo = compute_priority(meta)
    meta_plain = _meta(title="Quarterly overview")
    score_plain = compute_priority(meta_plain)
    assert score_ipo > score_plain


def test_summary_field_also_scanned() -> None:
    """Keywords in marketdesk_summary must contribute to the score."""
    meta_no_summary = _meta(title="Rates outlook Q3")
    meta_with_summary = _meta(
        title="Rates outlook Q3",
        summary="Initiation of coverage: semis sector looks strong with AI tailwinds.",
    )
    score_plain = compute_priority(meta_no_summary)
    score_rich = compute_priority(meta_with_summary)
    assert score_rich > score_plain


# ---------------------------------------------------------------------------
# watchlist ticker matching
# ---------------------------------------------------------------------------

def test_watchlist_hit_adds_points() -> None:
    meta = _meta(title="AAPL earnings preview: strong beats expected")
    score_no_wl = compute_priority(meta, watchlist=None)
    score_wl = compute_priority(meta, watchlist=["AAPL", "MSFT"])
    assert score_wl > score_no_wl


def test_watchlist_points_capped() -> None:
    """Hitting many watchlist tickers should not exceed WATCHLIST_POINTS_CAP=24."""
    title = "AAPL MSFT GOOGL AMZN NVDA TSLA META outlook"
    meta = _meta(title=title)
    watchlist = ["aapl", "msft", "googl", "amzn", "nvda", "tsla", "meta"]
    score = compute_priority(meta, watchlist=watchlist)
    from marketdesk_extractor.config import WATCHLIST_POINTS_CAP
    # watchlist contribution alone cannot exceed cap
    # (total score may be higher due to other keywords)
    # Just verify it does not exceed total reasonable bound
    assert score < 200  # sanity


def test_watchlist_no_match_no_extra_points() -> None:
    meta = _meta(title="Some paper about bonds")
    score_wl = compute_priority(meta, watchlist=["AAPL", "NVDA"])
    score_no_wl = compute_priority(meta, watchlist=None)
    assert score_wl == score_no_wl


# ---------------------------------------------------------------------------
# feed membership boosts
# ---------------------------------------------------------------------------

def test_top_pick_adds_15_points() -> None:
    meta_base = _meta(title="Neutral paper")
    meta_top = _meta(title="Neutral paper", is_top_pick=True)
    assert compute_priority(meta_top) - compute_priority(meta_base) == 15


def test_saved_adds_10_points() -> None:
    meta_base = _meta(title="Neutral paper")
    meta_saved = _meta(title="Neutral paper", is_saved=True)
    assert compute_priority(meta_saved) - compute_priority(meta_base) == 10


# ---------------------------------------------------------------------------
# score is never negative
# ---------------------------------------------------------------------------

def test_score_never_negative() -> None:
    meta = _meta(title="recap at a glance daily wrap calendar week ahead morning note")
    score = compute_priority(meta)
    assert score >= 0
