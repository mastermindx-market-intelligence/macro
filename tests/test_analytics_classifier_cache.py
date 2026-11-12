"""The warmer-held classifier sets (farm fingerprints, excluded cookies).

A fresh entry for the exact live SQL replaces the full-store CTE with a literal; a miss, a
stale entry, a config change or an unexpected value shape falls back to the live CTE.
"""
import pytest

from admin import analytics_first_party as a

_CFG = {"emails": [], "locations": [], "ips": [], "visitor_ids": [],
        "bots": {}, "geo_overrides": []}


@pytest.fixture
def cache(monkeypatch):
    monkeypatch.setattr(a, "_load_exclusions", lambda: dict(_CFG))
    monkeypatch.setattr(a, "_CLASSIFIER_CACHE", {})
    return a._CLASSIFIER_CACHE


def _refresh(monkeypatch, farm=("fp1",), excluded=("v1", "v2")):
    def fake_query(sql, *args, **kwargs):
        if sql.startswith("with "):
            return [{"visitor_id": v} for v in excluded]
        return [{"fp": f} for f in farm]
    monkeypatch.setattr(a, "_query", fake_query)
    a.refresh_classifier_cache()


def test_cold_cache_uses_the_live_ctes(cache):
    assert "excl_link" in a._excluded_cte().split("excluded as (", 1)[1]
    assert "group by fp" in a._bot_cte()


def test_fresh_cache_inlines_the_sets(monkeypatch, cache):
    _refresh(monkeypatch)
    excl = a._excluded_cte()
    assert excl.split("excluded as (", 1)[1] == \
        "select unnest(array['v1','v2']::text[]) as visitor_id)"
    assert "excl_users" in excl          # siblings stay defined (other surfaces read them)
    bots = a._bot_cte()
    assert "group by fp" not in bots and "array['fp1']::text[]" in bots


def test_empty_sets_stay_valid_sql(monkeypatch, cache):
    _refresh(monkeypatch, farm=(), excluded=())
    assert "select null::text as visitor_id where false" in a._excluded_cte()
    assert "select null::text as fp where false" in a._bot_cte()


def test_stale_entry_falls_back(monkeypatch, cache):
    _refresh(monkeypatch)
    monkeypatch.setattr(a, "_CLASSIFIER_MAX_AGE_S", -1)
    assert "array['v1','v2']" not in a._excluded_cte()
    assert "group by fp" in a._bot_cte()


def test_config_change_misses_the_cache(monkeypatch, cache):
    _refresh(monkeypatch)
    monkeypatch.setattr(a, "_load_exclusions", lambda: dict(_CFG, ips=["9.9.9.9"]))
    assert "array['v1','v2']" not in a._excluded_cte()
    monkeypatch.setattr(a, "_load_exclusions", lambda: dict(_CFG, bots={"fp_fanout": 30}))
    assert "array['fp1']" not in a._bot_cte()


def test_unexpected_value_shape_is_never_cached(monkeypatch, cache):
    _refresh(monkeypatch)
    _refresh(monkeypatch, excluded=("v1", "it's odd"))
    assert "excluded" not in cache               # old entry dropped, not served
    assert "farm" in cache
    assert "excl_link" in a._excluded_cte().split("excluded as (", 1)[1]


def test_one_failing_refresh_leaves_the_other(monkeypatch, cache):
    def fake_query(sql, *args, **kwargs):
        if sql.startswith("with "):
            raise TimeoutError("slow")
        return [{"fp": "fp1"}]
    monkeypatch.setattr(a, "_query", fake_query)
    a.refresh_classifier_cache()
    assert set(cache) == {"farm"}
