"""The panel's upstream budget fails LOUDLY and LEGIBLY — never with urllib3's transport wording.

WHY THIS EXISTS
---------------
admin.mastermind-x.com/#/page/analytics showed the operator, verbatim:

    Couldn't load this panel

    HTTPSConnectionPool(host='api.supabase.com', port=443): Read timed out. (read timeout=9.0)

That is urllib3 describing a socket. It sent the reader to the network, which was fine, while
the actual cause sat in the database. Measured on production 2026-11-09 (302,456 rows / 192 MB),
through this exact endpoint:

    select 1 ....................... 1.38s     (the transport is healthy)
    count(*) over the whole store .. 30.9s cold, 9.6s warm
    ident CTE (full-history) ....... 13.5s     <- 81% of the 16.7s Visitors fold

So a read timeout here is the STATEMENT outrunning the budget. `_query` now says that, and names
the budget it exceeded, instead of re-raising the pool message. This test pins that mapping:
a timeout must never surface the library's text, and a non-2xx must keep failing as it did.
"""
import pytest

from admin import analytics_first_party as a


class _Timeout(Exception):
    """Stand-in for requests.exceptions.Timeout (caught by the class, not by message)."""


@pytest.fixture
def patched(monkeypatch):
    """Configured module, no real HTTP, no surface deadline."""
    monkeypatch.setattr(a.settings, "supabase_pat", lambda: "sbp_test")
    monkeypatch.setattr(a.settings, "supabase_project_ref", lambda: "testref")
    monkeypatch.setattr(a, "_DEADLINE", a.contextvars.ContextVar("t_deadline", default=None))
    return monkeypatch


def test_read_timeout_is_reported_as_a_statement_budget_not_a_socket(patched):
    assert a.requests is not None, "requests is a hard dependency of this module"

    def time_out(*args, **kwargs):
        raise a.requests.exceptions.Timeout(
            "HTTPSConnectionPool(host='api.supabase.com', port=443): "
            "Read timed out. (read timeout=9.0)")

    patched.setattr(a.requests, "post", time_out)

    with pytest.raises(TimeoutError) as excinfo:
        a._query("select 1")

    message = str(excinfo.value)
    # The library's transport wording must not reach the operator.
    assert "HTTPSConnectionPool" not in message
    assert "Read timed out" not in message
    # It must name the budget it blew and say where the cost actually is.
    assert "9.0s" in message
    assert "Supabase Management API" in message
    assert "full-store scan" in message


def test_http_error_status_still_fails_truthfully(patched):
    class _Response:
        status_code = 400
        text = "invalid query"

    patched.setattr(a.requests, "post", lambda *args, **kwargs: _Response())

    with pytest.raises(RuntimeError, match=r"HTTP 400: invalid query"):
        a._query("select 1")


def test_every_statement_carries_the_sort_memory_prelude(patched):
    """The visit fold sorts ~19k wide rows per statement against a 2MB work_mem.

    That is a spill, not a bad plan, so no index reaches it — measured on production
    2026-11-09, Visitors (24h) took 13,848ms at the instance default and 4,329ms once the
    sort could fit in memory. The prelude must ride on EVERY statement, or the panel is
    back over its 9s budget.
    """
    sent = {}

    class _Response:
        status_code = 201
        text = ""

        @staticmethod
        def json():
            return [{"n": 1}]

    def capture(url, headers=None, json=None, timeout=None):
        sent.update(json)
        return _Response()

    patched.setattr(a.requests, "post", capture)

    assert a._query("select 1") == [{"n": 1}]
    assert "16MB" in a._QUERY_PRELUDE
    assert sent["query"] == a._statement_timeout_sql(a._QUERY_TIMEOUT_S) + a._QUERY_PRELUDE + "select 1"


def test_timeout_cap_narrows_the_reported_budget(patched):
    """A capped best-effort probe must report ITS cap, not the surface's 9s."""

    def time_out(*args, **kwargs):
        raise a.requests.exceptions.Timeout("Read timed out. (read timeout=0.8)")

    patched.setattr(a.requests, "post", time_out)

    with pytest.raises(TimeoutError, match=r"within 0\.8s"):
        a._query("select 1", timeout_cap_s=0.75)


def test_every_statement_is_bounded_server_side_by_its_own_budget(patched):
    """An abandoned HTTP request must not leave its statement running.

    The role's statement_timeout is 2min, so before this every panel the client gave up on
    kept scanning server-side for up to 1m53s (production 2026-11-12) and the stacked
    orphans starved the next attempt. `set local statement_timeout` bounds the statement
    to the same budget the client waits for.
    """
    sent = {}

    class _Response:
        status_code = 201
        text = ""

        @staticmethod
        def json():
            return []

    def capture(url, headers=None, json=None, timeout=None):
        sent.update(json, http_timeout=timeout)
        return _Response()

    patched.setattr(a.requests, "post", capture)
    a._query("select 1", timeout_cap_s=3)
    assert sent["query"].startswith("set local statement_timeout = '3000ms'; ")
    assert sent["http_timeout"] > 3   # the server, not the socket, fires first
    assert a._statement_timeout_sql(0.1) == "set local statement_timeout = '500ms'; "


def test_server_side_statement_timeout_reads_as_the_panel_budget(patched):
    class _Response:
        status_code = 400
        text = '{"message":"ERROR:  57014: canceling statement due to statement timeout"}'

    patched.setattr(a.requests, "post", lambda *args, **kwargs: _Response())
    with pytest.raises(TimeoutError, match=r"did not finish within 9\.0s"):
        a._query("select 1")


def test_other_upstream_errors_are_not_disguised_as_timeouts(patched):
    class _Response:
        status_code = 400
        text = '{"message":"ERROR:  42P01: relation does not exist"}'

    patched.setattr(a.requests, "post", lambda *args, **kwargs: _Response())
    with pytest.raises(RuntimeError, match="HTTP 400"):
        a._query("select 1")


# ---- warmer-held classifier sets (farm fingerprints, excluded cookies) ------------
# A fresh entry for the exact live SQL replaces the full-store CTE with a literal; a miss,
# a stale entry, a config change or an unexpected value shape falls back to the live CTE.
_CACHE_CFG = {"emails": [], "locations": [], "ips": [], "visitor_ids": [],
        "bots": {}, "geo_overrides": []}


@pytest.fixture
def cache(monkeypatch):
    monkeypatch.setattr(a, "_load_exclusions", lambda: dict(_CACHE_CFG))
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
    monkeypatch.setattr(a, "_load_exclusions", lambda: dict(_CACHE_CFG, ips=["9.9.9.9"]))
    assert "array['v1','v2']" not in a._excluded_cte()
    monkeypatch.setattr(a, "_load_exclusions", lambda: dict(_CACHE_CFG, bots={"fp_fanout": 30}))
    assert "array['fp1']" not in a._bot_cte()


def test_unexpected_value_shape_is_never_cached(monkeypatch, cache):
    _refresh(monkeypatch)
    _refresh(monkeypatch, excluded=("v1", "it's odd"))
    assert "excluded" not in cache               # old entry dropped, not served
    assert "farm" in cache
    assert "excl_link" in a._excluded_cte().split("excluded as (", 1)[1]


@pytest.mark.parametrize("rows", [
    {}, "v1", [None], [{}], [{"visitor_id": None}],
    [{"visitor_id": False}], [{"visitor_id": 42}], [{"visitor_id": "v1\n"}],
    [{"visitor_id": "v1"}, {"wrong_column": "v2"}],
])
def test_malformed_refresh_discards_only_the_affected_set(monkeypatch, cache, rows):
    _refresh(monkeypatch)
    peer = cache["farm"]
    key = cache["excluded"]["key"]
    monkeypatch.setattr(a, "_query", lambda sql: rows)
    a._refresh_set("excluded", key, "query", "visitor_id")
    assert "excluded" not in cache
    assert cache["farm"] is peer
    assert "excl_link" in a._excluded_cte().split("excluded as (", 1)[1]


def test_malformed_old_refresh_keeps_a_newer_configuration(monkeypatch, cache):
    _refresh(monkeypatch)
    current = cache["excluded"]
    monkeypatch.setattr(a, "_query", lambda sql: [{"visitor_id": None}])
    a._refresh_set("excluded", "previous-config", "query", "visitor_id")
    assert cache["excluded"] is current


def test_refresh_caps_distinct_values_and_accepts_an_empty_result(monkeypatch, cache):
    monkeypatch.setattr(a, "_CLASSIFIER_MAX_VALUES", 1)
    _refresh(monkeypatch, excluded=("v1", "v1"))
    assert cache["excluded"]["values"] == ("v1",)
    _refresh(monkeypatch, excluded=("v1", "v2"))
    assert "excluded" not in cache
    _refresh(monkeypatch, excluded=())
    assert cache["excluded"]["values"] == ()


def test_one_failing_refresh_leaves_the_other(monkeypatch, cache):
    def fake_query(sql, *args, **kwargs):
        if sql.startswith("with "):
            raise TimeoutError("slow")
        return [{"fp": "fp1"}]
    monkeypatch.setattr(a, "_query", fake_query)
    a.refresh_classifier_cache()
    assert set(cache) == {"farm"}
