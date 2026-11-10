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
    assert sent["query"] == a._QUERY_PRELUDE + "select 1"


def test_timeout_cap_narrows_the_reported_budget(patched):
    """A capped best-effort probe must report ITS cap, not the surface's 9s."""

    def time_out(*args, **kwargs):
        raise a.requests.exceptions.Timeout("Read timed out. (read timeout=0.8)")

    patched.setattr(a.requests, "post", time_out)

    with pytest.raises(TimeoutError, match=r"within 0\.8s"):
        a._query("select 1", timeout_cap_s=0.75)
