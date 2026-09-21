"""build_meta must never emit a dateless paper when the date is recoverable.

MarketDesk's item `t` (unix publish time) is the primary date, but if it is ever
absent we recover a DAY-precision date from the browse breadcrumb (the library
tree is organized by publish date). This keeps a backfilled/mopped-up paper on its
REAL day so it sorts into historical position — never stamped with our own clock.
When even the breadcrumb has no date, published_at stays None and the downstream
vault sorts the paper LAST (the dashboard ingest never substitutes its ingest
time). Pure-function + integration coverage.
"""
from __future__ import annotations

from datetime import datetime, timezone

from marketdesk_extractor.config import Config
from marketdesk_extractor.marketdesk import _date_from_breadcrumb, build_meta


def _utc(y, m, d, hh=0, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


# --- _date_from_breadcrumb (pure) ------------------------------------------
def test_date_from_breadcrumb_year_month_day():
    assert _date_from_breadcrumb(["2026", "July", "Jul 7", "Goldman", "S&T"]) == _utc(2026, 7, 7)


def test_date_from_breadcrumb_skips_non_date_crumbs():
    # "Top 5" must not be mistaken for a Mon-Day; the real "Jul 7" wins.
    assert _date_from_breadcrumb(["2026", "Top 5", "Jul 7", "Barclays"]) == _utc(2026, 7, 7)


def test_date_from_breadcrumb_two_digit_day():
    assert _date_from_breadcrumb(["2026", "February", "Feb 28", "GS"]) == _utc(2026, 2, 28)


def test_date_from_breadcrumb_none_when_no_year():
    assert _date_from_breadcrumb(["Jul 7", "Goldman"]) is None


def test_date_from_breadcrumb_none_when_no_month_day():
    # A bare month name ("July") is not a "Mon D" leaf — no day, so no date.
    assert _date_from_breadcrumb(["2026", "July", "Goldman"]) is None


def test_date_from_breadcrumb_rejects_impossible_day():
    assert _date_from_breadcrumb(["2026", "Feb 30", "GS"]) is None


def test_date_from_breadcrumb_empty_or_none():
    assert _date_from_breadcrumb([]) is None
    assert _date_from_breadcrumb(None) is None


# --- build_meta integration -------------------------------------------------
def test_build_meta_prefers_t_over_breadcrumb():
    cfg = Config.from_env()
    t = int(_utc(2026, 7, 7, 13, 0).timestamp())
    meta = build_meta(cfg, {"pathId": "abc", "name": "Rep", "t": t},
                      breadcrumb=["2026", "July", "Jul 6", "GS"])  # breadcrumb says the 6th
    assert meta.published_at == _utc(2026, 7, 7, 13, 0)           # `t` (the 7th) wins
    assert meta.published_unix == t


def test_build_meta_recovers_date_from_breadcrumb_when_t_missing():
    cfg = Config.from_env()
    meta = build_meta(cfg, {"pathId": "abc", "name": "Rep"},      # no `t`
                      breadcrumb=["2026", "July", "Jul 7", "GS"])
    assert meta.published_at == _utc(2026, 7, 7)
    assert meta.published_unix == int(_utc(2026, 7, 7).timestamp())
    # age text is derived from the recovered date, not left dangling
    assert meta.marketdesk_age_text


def test_build_meta_leaves_date_none_when_t_and_breadcrumb_dateless():
    cfg = Config.from_env()
    meta = build_meta(cfg, {"pathId": "abc", "name": "Rep"},      # no `t`
                      breadcrumb=["Goldman", "S&T"])              # no date crumbs
    # Never invented: the vault then leaves the sidecar blank and sorts it last.
    assert meta.published_at is None
    assert meta.published_unix is None
    assert meta.marketdesk_age_text is None
