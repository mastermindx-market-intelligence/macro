"""Durable-state safety for the Watchlist Sentinel runner (scripts/run_watchlist_sentinel.py).

The runner's Supabase read used to collapse two different facts into one empty list:

    "the operator watches nothing"      -> [] -- authoritative; safe to advance state
    "we could not find out tonight"     -> [] -- missing creds, missing operator id, a non-200,
                                                a timeout, a payload of the wrong shape

main() read `not watched` as authoritative empty either way and then WROTE:

    _save_cooldown(today_str, {}, dry_run)      # every live cooldown erased
    _save_states(today_str, today_states, ...)  # enter-detection baseline stepped forward

so ONE bad night silently destroyed a 5-session cooldown and moved the yesterday-snapshot past a
transition that was never evaluated and therefore could never fire.

These tests exercise main() end to end against a tmp_path state directory. The fetch is failed at
each of its real failure points (not by stubbing the typed result), so what is proved is that the
FETCH classifies honestly AND that main() branches on that classification.

Run:
    python -m pytest tests/test_watchlist_sentinel_source_truth.py -v
"""
from __future__ import annotations

import json
import sys

import pytest
import requests

from scripts import run_watchlist_sentinel as M

D1, D2, D3 = "2026-09-16", "2026-09-17", "2026-09-18"

# A cooldown the operator has really earned: AAPL alerted on D1 and is 0 sessions into its
# 5-session suppression. This is the state a bad night used to wipe.
LIVE_COOLDOWN = {"AAPL": {"last_alert": D1, "last_in_window": True, "sessions_since": 0}}
# Yesterday's per-ticker snapshot -- the baseline enter-detection diffs against.
PREV_STATES = {"AAPL": {"entry_status": "outside", "gate_eligible": True,
                        "gate_tier": "A", "in_blackout": False, "extension_grade": "ok"}}
TODAY_STATES = {"AAPL": {"entry_status": "outside", "gate_eligible": True,
                         "gate_tier": "A", "in_blackout": False, "extension_grade": "ok"}}


@pytest.fixture()
def sentinel(tmp_path, monkeypatch):
    """Point the runner's durable state at tmp_path and neutralise its outbound edges."""
    alerts = tmp_path / "alerts"
    alerts.mkdir(parents=True)
    monkeypatch.setattr(M, "_ALERTS_DIR", alerts)
    monkeypatch.setattr(M, "_STATES_PATH", alerts / "watchlist_sentinel_states.json")
    monkeypatch.setattr(M, "_COOLDOWN_PATH", alerts / "watchlist_sentinel_cooldown.json")
    monkeypatch.setattr(M, "_ALERTS_JSONL", alerts / "watchlist_alerts.jsonl")
    # Today's per-ticker states come from committed engine artifacts, which are not what is
    # under test here (and are not checked out in a sparse worktree).
    monkeypatch.setattr(M, "_load_per_ticker_states", lambda today: dict(TODAY_STATES))
    monkeypatch.setattr(M, "_send_discord_watchlist", lambda msg, dry: False)
    monkeypatch.setattr(sys, "argv", ["run_watchlist_sentinel"])
    return M


def _seed(prev_states=None, cooldown=None, as_of=D2):
    """Write the state a previous AUTHORITATIVE night would have left behind."""
    M._STATES_PATH.write_text(json.dumps(
        {"as_of": as_of, "states": prev_states if prev_states is not None else PREV_STATES}))
    M._COOLDOWN_PATH.write_text(json.dumps(
        {"as_of": as_of, "cooldown": cooldown if cooldown is not None else LIVE_COOLDOWN}))


def _states_file() -> dict:
    return json.loads(M._STATES_PATH.read_text())


def _cooldown_file() -> dict:
    return json.loads(M._COOLDOWN_PATH.read_text())


def _run(date=D3) -> int:
    sys.argv[:] = ["run_watchlist_sentinel", "--date", date]
    return M.main()


# --------------------------------------------------------------------------- #
# fetch-failure injectors -- each fails the read at a DIFFERENT real point
# --------------------------------------------------------------------------- #
def _wire_supabase(monkeypatch, *, url="https://abc.supabase.co", key="sk_test",
                   uid="uid-123", response=None, raises=None):
    monkeypatch.setattr(M.config, "load", lambda: {"watchlist": {"supabase": {"url": url}}})
    monkeypatch.setattr(M.config, "secret", lambda k: {
        "SUPABASE_SERVICE_KEY": key,
        "SUPABASE_SERVICE_ROLE_KEY": None,
        "SUPABASE_OPERATOR_USER_ID": uid,
    }.get(k))

    def _get(*a, **kw):
        if raises is not None:
            raise raises
        return response

    monkeypatch.setattr(M.requests, "get", _get)


class _Resp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _rows(*symbols):
    return [{"id": "list-1", "user_id": "uid-123",
             "watchlist_symbols": [{"symbol": s} for s in symbols]}]


# --------------------------------------------------------------------------- #
# 1. honest empty -- MAY advance
# --------------------------------------------------------------------------- #
def test_genuinely_empty_account_advances_state_normally(sentinel, monkeypatch):
    """The operator has a Supabase row and watches nothing. That is a real answer, so the night
    advances exactly as before: today's snapshot, empty cooldown, both stamped today."""
    _seed()
    _wire_supabase(monkeypatch, response=_Resp(200, []))

    assert _run() == 0

    states, cooldown = _states_file(), _cooldown_file()
    assert states["as_of"] == D3
    assert states["states"] == TODAY_STATES
    assert cooldown == {"as_of": D3, "cooldown": {}}
    # ...and it is legible as an honest empty, not as a failure.
    assert states["source"]["status"] == "ok"
    assert states["source"]["state"] == "ok_zero_events"
    assert states["source"]["watched_count"] == 0
    assert states["source"]["checked"] == D3


# --------------------------------------------------------------------------- #
# 2-5. every unavailable read -- MUST preserve durable state exactly
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("wire,reason", [
    (dict(key=None), "no_service_key"),
    (dict(uid=None), "no_operator_id"),
    (dict(url=None), "no_config_url"),
    (dict(response=_Resp(401, text="unauthorized")), "http_401"),
    (dict(response=_Resp(500, text="upstream boom")), "http_500"),
    (dict(raises=requests.exceptions.Timeout("read timed out")), "request_failed"),
    (dict(raises=requests.exceptions.ConnectionError("dns")), "request_failed"),
    (dict(response=_Resp(200, payload={"code": "42703", "message": "no such column"})),
     "malformed_payload"),
    (dict(response=_Resp(200, payload=["not-a-row", 7])), "malformed_payload"),
    (dict(response=_Resp(200, payload=ValueError("not json"))), "request_failed"),
])
def test_unavailable_read_preserves_cooldown_and_previous_state_exactly(
        sentinel, monkeypatch, capsys, wire, reason):
    """Missing credentials, missing operator identity, 4xx, 5xx, timeout, connection failure and
    a payload of the wrong shape are all the SAME fact: we did not learn the watchlist. None of
    them may advance a single byte of durable state."""
    _seed()
    before_states = M._STATES_PATH.read_text()
    before_cooldown = M._COOLDOWN_PATH.read_text()
    _wire_supabase(monkeypatch, **wire)

    assert _run() == 0, "the nightly step must stay fail-soft"

    # The cooldown file is untouched -- not rewritten, not emptied.
    assert M._COOLDOWN_PATH.read_text() == before_cooldown
    assert _cooldown_file()["cooldown"] == LIVE_COOLDOWN

    # The states file keeps the last AUTHORITATIVE night's answer; only the health stamp moves.
    states = _states_file()
    assert states["as_of"] == D2, "the enter-detection baseline must not step over a blind night"
    assert states["states"] == PREV_STATES
    assert json.loads(before_states)["states"] == states["states"]

    # ...and the night is visible rather than silent.
    assert states["source"] == {"status": "unavailable", "state": "unavailable",
                                "reason": reason, "checked": D3, "watched_count": 0}
    out = capsys.readouterr().out
    assert "::warning title=watchlist-sentinel-source-unavailable::" in out
    assert reason in out


def test_the_annotation_starts_its_line(sentinel, monkeypatch, capsys):
    """House law: a GitHub annotation only registers when `::warning` is the first thing on the
    line, which is why this is a bare print() and not a log call (loggers prefix the level)."""
    _seed()
    _wire_supabase(monkeypatch, response=_Resp(503, text="unavailable"))
    _run()
    lines = [ln for ln in capsys.readouterr().out.splitlines() if "::warning" in ln]
    assert lines and all(ln.startswith("::warning ") for ln in lines), lines


def test_malformed_payload_does_not_crash_the_nightly(sentinel, monkeypatch):
    """PostgREST reports errors as a JSON OBJECT. The old loop walked that object's keys as if
    they were rows and raised AttributeError straight out of the nightly step."""
    _seed()
    _wire_supabase(monkeypatch,
                   response=_Resp(200, payload={"message": "permission denied for table"}))
    assert _run() == 0
    assert _cooldown_file()["cooldown"] == LIVE_COOLDOWN


# --------------------------------------------------------------------------- #
# 6-7. the outage night must cost nothing
# --------------------------------------------------------------------------- #
def test_cooldown_survives_the_unavailable_night_and_resumes_on_the_next_good_one(
        sentinel, monkeypatch):
    """The whole point. AAPL is 0 sessions into a 5-session cooldown. One blind night, then a
    good one: the cooldown must be intact through the outage and must have consumed exactly ONE
    session by the end -- the blind night is not a session, because nothing was evaluated."""
    _seed(as_of=D1)

    # night 2 -- Supabase is down
    _wire_supabase(monkeypatch, response=_Resp(500, text="boom"))
    assert _run(D2) == 0
    assert _cooldown_file()["cooldown"]["AAPL"]["sessions_since"] == 0, "outage consumed a session"

    # night 3 -- Supabase is back
    _wire_supabase(monkeypatch, response=_Resp(200, _rows("AAPL")))
    assert _run(D3) == 0

    cooldown = _cooldown_file()
    assert cooldown["as_of"] == D3
    assert cooldown["cooldown"]["AAPL"]["sessions_since"] == 1
    assert cooldown["cooldown"]["AAPL"]["last_alert"] == D1, "the alert date must not drift"
    states = _states_file()
    assert states["as_of"] == D3 and states["source"]["status"] == "ok"
    assert states["source"]["state"] == "ok"
    assert states["source"]["watched_count"] == 1


def test_a_good_read_after_an_outage_diffs_against_the_pre_outage_baseline(sentinel, monkeypatch):
    """Because the blind night did not advance the snapshot, the next good night still compares
    against the last state the sentinel actually evaluated -- so a transition that happened
    across the outage is still detectable instead of being silently skipped over."""
    _seed(prev_states={"AAPL": {"entry_status": "outside"}}, cooldown={}, as_of=D1)
    seen: dict = {}
    monkeypatch.setattr(M, "run_sentinel",
                        lambda **kw: seen.update(kw) or [])

    _wire_supabase(monkeypatch, raises=requests.exceptions.Timeout("t"))
    _run(D2)
    assert seen == {}, "a blind night must not evaluate anything"

    _wire_supabase(monkeypatch, response=_Resp(200, _rows("AAPL")))
    _run(D3)
    assert seen["yesterday_states"] == {"AAPL": {"entry_status": "outside"}}
    assert seen["watched_tickers"] == ["AAPL"]


def test_an_unavailable_night_with_no_prior_state_writes_only_the_health_stamp(sentinel, monkeypatch):
    """First-ever run, and the source is down: there is nothing to preserve, and nothing may be
    invented. The cooldown file must not spring into existence as an authoritative empty."""
    _wire_supabase(monkeypatch, key=None)
    assert _run() == 0
    assert not M._COOLDOWN_PATH.exists()
    assert _states_file() == {"source": {"status": "unavailable", "state": "unavailable",
                                         "reason": "no_service_key", "checked": D3,
                                         "watched_count": 0}}


# --------------------------------------------------------------------------- #
# 8. same-day rerender
# --------------------------------------------------------------------------- #
def test_same_day_rerender_is_still_a_no_op(sentinel, monkeypatch):
    """Both stores already carry today -> the run short-circuits before the fetch, unchanged."""
    _seed(as_of=D3)
    before = (M._STATES_PATH.read_text(), M._COOLDOWN_PATH.read_text())
    called = {"n": 0}
    monkeypatch.setattr(M, "_fetch_operator_watchlist",
                        lambda: called.update(n=called["n"] + 1))

    assert _run(D3) == 0
    assert called["n"] == 0
    assert (M._STATES_PATH.read_text(), M._COOLDOWN_PATH.read_text()) == before


def test_an_unavailable_night_leaves_the_day_open_for_a_retry(sentinel, monkeypatch):
    """A blind night must NOT look like a completed one. Because `as_of` stays stale, a later run
    the same evening re-attempts the fetch instead of short-circuiting as already-done."""
    _seed(as_of=D2)
    _wire_supabase(monkeypatch, response=_Resp(500, text="boom"))
    assert _run(D3) == 0
    assert M._is_same_day_rerender(D3) is False

    _wire_supabase(monkeypatch, response=_Resp(200, _rows("AAPL")))
    assert _run(D3) == 0
    assert _states_file()["as_of"] == D3, "the retry must be allowed to land"


# --------------------------------------------------------------------------- #
# 9. dry-run writes nothing
# --------------------------------------------------------------------------- #
def test_dry_run_never_touches_the_state_files(sentinel, monkeypatch):
    _seed()
    before = (M._STATES_PATH.read_text(), M._COOLDOWN_PATH.read_text())
    _wire_supabase(monkeypatch, response=_Resp(500, text="boom"))
    sys.argv[:] = ["run_watchlist_sentinel", "--date", D3, "--dry-run"]
    assert M.main() == 0
    assert (M._STATES_PATH.read_text(), M._COOLDOWN_PATH.read_text()) == before


# --------------------------------------------------------------------------- #
# 10. the typed contract itself
# --------------------------------------------------------------------------- #
def test_read_state_slugs_match_the_house_vocabulary():
    """WatchlistRead mirrors engine/alert_triage.py's READ_* slugs rather than importing them
    (the nightly runner should not pull that module in for three strings). This pins the mirror
    so the two can never drift into two different words for the same fact."""
    from engine import alert_triage as at

    assert M.WatchlistRead.READ_OK == at.READ_OK
    assert M.WatchlistRead.READ_OK_ZERO == at.READ_OK_ZERO
    assert M.WatchlistRead.READ_UNAVAILABLE == at.READ_UNAVAILABLE


def test_the_three_states_are_distinguishable_from_the_value_alone():
    """An unavailable read must not be mistakable for an empty one by any caller, including a
    future one that only looks at `tickers`."""
    ok = M.WatchlistRead.ok(["AAPL"])
    empty = M.WatchlistRead.ok(())
    down = M.WatchlistRead.unavailable("http_500")

    assert [r.state for r in (ok, empty, down)] == ["ok", "ok_zero_events", "unavailable"]
    assert (ok.available, empty.available, down.available) == (True, True, False)
    # the trap the old contract set: empty and unavailable share a ticker list...
    assert empty.tickers == down.tickers == ()
    # ...and are still never equal, so `read == <empty read>` cannot silently accept an outage.
    assert empty != down


# --------------------------------------------------------------------------- #
# 11. schema drift is an unknown read, not an empty watchlist
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("payload,reason", [
    # the `symbol` column renamed out from under the embedded select
    ([{"id": "l1", "watchlist_symbols": [{"ticker": "AAPL"}, {"ticker": "NVDA"}]}],
     "no_usable_symbols"),
    # symbol rows present but every value blank
    ([{"id": "l1", "watchlist_symbols": [{"symbol": ""}, {"symbol": "  "}]}],
     "no_usable_symbols"),
    # the embedded select returned an object where a list was asked for
    ([{"id": "l1", "watchlist_symbols": {"symbol": "AAPL"}}], "malformed_payload"),
])
def test_symbol_rows_that_yield_nothing_are_unavailable_not_empty(
        sentinel, monkeypatch, payload, reason):
    """A 200 whose symbol rows produce no usable ticker is a read we no longer understand -- NOT
    an operator who watches nothing. Classifying it as empty would let a schema drift erase the
    cooldown, which is the original defect wearing a narrower disguise."""
    _seed()
    before_cooldown = M._COOLDOWN_PATH.read_text()
    _wire_supabase(monkeypatch, response=_Resp(200, payload))

    assert _run() == 0
    assert M._COOLDOWN_PATH.read_text() == before_cooldown
    assert _states_file()["as_of"] == D2
    assert _states_file()["source"]["reason"] == reason


def test_a_container_with_no_symbol_rows_is_still_honestly_empty(sentinel, monkeypatch):
    """The boundary the rule above must not cross: ZERO symbol rows is a real container the
    operator simply has not filled, and still advances normally."""
    _seed()
    _wire_supabase(monkeypatch, response=_Resp(200, [{"id": "l1", "watchlist_symbols": []}]))

    assert _run() == 0
    assert _states_file()["as_of"] == D3
    assert _states_file()["source"]["state"] == "ok_zero_events"
    assert _cooldown_file() == {"as_of": D3, "cooldown": {}}


# --------------------------------------------------------------------------- #
# 12. an unreadable states file is never overwritten
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("content", ["{not json", "", "[1,2]", "null"])
def test_an_unreadable_states_file_is_left_untouched(sentinel, monkeypatch, content):
    """The health stamp must never be the thing that destroys state. If the states file exists
    but cannot be read as an object, rewriting it with only a `source` key would turn a read
    problem into data loss -- and would destroy bytes a human might still recover."""
    M._STATES_PATH.write_text(content)
    M._COOLDOWN_PATH.write_text(json.dumps({"as_of": D2, "cooldown": LIVE_COOLDOWN}))
    _wire_supabase(monkeypatch, response=_Resp(500, text="boom"))

    assert _run() == 0
    assert M._STATES_PATH.read_text() == content, "the unreadable file was rewritten"
    assert _cooldown_file()["cooldown"] == LIVE_COOLDOWN


def test_a_readable_states_file_still_gets_its_stamp(sentinel, monkeypatch):
    """The boundary: a well-formed file keeps as_of + states AND gains the health stamp."""
    _seed()
    _wire_supabase(monkeypatch, response=_Resp(500, text="boom"))
    assert _run() == 0
    st = _states_file()
    assert st["as_of"] == D2 and st["states"] == PREV_STATES
    assert st["source"]["reason"] == "http_500"
