"""tests/test_portfolio_brief_context.py — the Portfolio brief snapshot producer.

The producer half of the accepted Portfolio brief snapshot contract
(docs/verification/portfolio-brief-snapshot-20261102/PLAN.md). The Terminal is
the sole canonical normalizer and book-key owner; this suite proves that the
producer emits a witness it can actually stand behind, and that it refuses
every one it cannot.

What is proved here
-------------------
1.  The projection gate. The shared fixture
    (tests/fixtures/portfolio_brief_context/projection_cases.json) carries the
    Terminal's REAL rowToPosition output and the frozen composer's own reading
    for the same synthetic rows. The producer must reproduce BOTH and accept
    exactly the rows the two independent authorities agree about.
2.  The completeness proof. A count/range that does not describe the rows in
    the SAME response is not a snapshot: truncation, a missing count, a
    non-zero start range, an invalid range, duplicates and an over-limit book
    all fail unavailable.
3.  One read, one witness. The rows the composer is called with and the rows
    the witness describes come from the SAME capture, and a bound request never
    reads or writes the legacy cache.
4.  The gates that must come first: authentication and Pro entitlement both
    precede every private read.
5.  The watchlist fallback stays distinct: it follows a PROVEN zero-open
    result, never re-reads positions, and can never qualify as a positions
    book.
6.  Ordinary requests are untouched, and the witness never reaches a log or a
    URL.

Every fixture is synthetic. No live account, no real holding and no database
mutation is involved.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import portfolio_brief_context as pbc  # noqa: E402
from app.portfolio_brief_context import (  # noqa: E402
    MAX_SNAPSHOT_ROWS,
    REASON_COUNT_MISMATCH,
    REASON_DROPPED_BY_TERMINAL,
    REASON_DUPLICATE_IDS,
    REASON_ENTRY_PRICE_MISMATCH,
    REASON_INVALID_RANGE,
    REASON_MISSING_COUNT,
    REASON_NONZERO_START,
    REASON_NOT_JSON_SAFE,
    REASON_OVER_LIMIT,
    REASON_SHARES_MISMATCH,
    REASON_TICKER_MISMATCH,
    REASON_TRANSPORT,
    REASON_WATCHLIST_PREFIX,
    SnapshotUnavailable,
    build_witness,
    capture_snapshot,
    check_row_compatible,
    composer_numeric,
    composer_row,
    snapshot_header_unsupported,
    snapshot_requested,
    terminal_position,
)

FIXTURE_DIR = ROOT / "tests" / "fixtures" / "portfolio_brief_context"
CASES_PATH = FIXTURE_DIR / "projection_cases.json"
SNAPSHOT_HEADER = {"X-Mastermind-Portfolio-Context": "snapshot-v1"}


# ── synthetic inputs ──────────────────────────────────────────────────────────

def _row(**kw) -> dict:
    """One synthetic portfolio_positions row (the ten selected fields)."""
    row = {
        "id": "11111111-1111-4111-8111-111111111111",
        "ticker": "NVDA",
        "shares": 10,
        "entry_price": 100.0,
        "entry_currency": None,
        "entry_currency_basis": None,
        "entry_date": "2026-01-15",
        "notes": None,
        "status": "open",
        "created_at": "2026-01-15T09:30:00+00:00",
    }
    row.update(kw)
    return row


def _ctx(asof: str = "2026-11-02") -> dict:
    """A minimal synthetic portfolio_ctx.v1 — enough for the composer to run."""
    return {
        "schema": "portfolio_ctx.v1",
        "asof": asof,
        "gate_go": False,
        "sectors": {},
        "coverage": {"tickers": 0},
        "tickers": {},
    }


_UNSET = object()


def _ok(rows: list[dict], *, count=_UNSET, first=_UNSET, last=_UNSET) -> dict:
    """A count-aware read that ANSWERED, with the stated completeness facts.

    The defaults describe a complete read: the count equals the rows returned
    and the range is 0..n-1 (the empty form ``*/0`` carries no range at all).
    ``count=None`` deliberately means "the response stated no count".
    """
    n = len(rows)
    return {
        "ok": True,
        "rows": rows,
        "count": n if count is _UNSET else count,
        "range_first": (0 if n else None) if first is _UNSET else first,
        "range_last": ((n - 1) if n else None) if last is _UNSET else last,
        "returned_count": n,
        "error": None,
    }


def _fail(error: str = "request_failed") -> dict:
    """A count-aware read that did NOT answer."""
    return {"ok": False, "rows": None, "count": None, "range_first": None,
            "range_last": None, "returned_count": None, "error": error}


class _Reader:
    """A count-aware reader stand-in that records every path it is asked for."""

    def __init__(self, positions=None, watchlists=None, symbols=None):
        self._positions = positions
        self._watchlists = watchlists
        self._symbols = symbols
        self.calls: list[dict] = []

    def __call__(self, path: str, *, limit: int) -> dict:
        self.calls.append({"path": path, "limit": limit})
        if path.startswith("portfolio_positions"):
            return self._positions() if callable(self._positions) else self._positions
        if path.startswith("watchlists"):
            return self._watchlists() if callable(self._watchlists) else self._watchlists
        if path.startswith("watchlist_symbols"):
            return self._symbols() if callable(self._symbols) else self._symbols
        raise AssertionError(f"unexpected read path: {path}")

    @property
    def positions_calls(self) -> list[dict]:
        return [c for c in self.calls if c["path"].startswith("portfolio_positions")]


# ── 1. the shared fixture is the contract ────────────────────────────────────

@pytest.fixture(scope="module")
def cases() -> list[dict]:
    raw = CASES_PATH.read_text(encoding="utf-8")

    def _reject(constant):  # pragma: no cover - only fires on a broken fixture
        raise AssertionError(f"the shared fixture must be strict JSON, found {constant!r}")

    doc = json.loads(raw, parse_constant=_reject)
    assert doc["schema"] == "portfolio_brief_context.projection_cases.v1"
    return doc["cases"]


def test_shared_fixture_covers_the_adversarial_surface(cases):
    """The fixture must actually cover the surface it claims to pin."""
    names = {c["name"] for c in cases}
    for required in ("decimal_string_shares", "negative_zero", "small_exponent",
                     "null_shares", "boolean_true_shares", "underscore_numeric_string",
                     "hex_numeric_string", "unicode_ticker", "bom_prefixed_ticker",
                     "status_closed_upper", "status_null", "missing_id",
                     "currency_receipt_valid", "currency_receipt_price_mismatch"):
        assert required in names, f"the shared fixture lost the {required!r} case"
    assert any(not c["compatible"] for c in cases), "no incompatible case: the gate is untested"
    assert any(c["compatible"] for c in cases), "no compatible case: nothing can be witnessed"


@pytest.mark.parametrize("case", json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"],
                         ids=lambda c: c["name"])
def test_terminal_mirror_reproduces_the_terminal_contract(case):
    """The producer's Terminal projection must equal the Terminal's own output.

    This is the anti-drift check: the Terminal's real rowToPosition produced the
    expectation, so a producer that reads a row differently from the Terminal
    fails here rather than in production.
    """
    expected = case["terminal"]
    got = terminal_position(case["row"])
    if expected is None:
        assert got is None, f"{case['name']}: Terminal drops this row, the producer kept {got!r}"
        return
    assert got is not None, f"{case['name']}: the producer dropped a row Terminal keeps"
    for field in ("id", "ticker", "shares", "entryPrice", "entryDate", "notes",
                  "status", "createdAt"):
        assert got[field] == expected[field], f"{case['name']}: {field}"


@pytest.mark.parametrize("case", json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"],
                         ids=lambda c: c["name"])
def test_composer_mirror_reproduces_the_frozen_composer(case):
    """The producer's composer reading must equal the frozen composer's own."""
    expected = case["composer"]
    got = composer_row(case["row"])
    assert got["ticker"] == expected["ticker"], case["name"]
    non_finite = expected.get("non_finite") or []
    for field in ("shares", "entry_price"):
        if field in non_finite:
            value = got[field]
            assert value is not None and value != value or value in (float("inf"), float("-inf")), (
                f"{case['name']}: {field} should read non-finite, got {value!r}")
            continue
        assert got[field] == expected[field], f"{case['name']}: {field}"


@pytest.mark.parametrize("case", json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"],
                         ids=lambda c: c["name"])
def test_gate_accepts_exactly_what_the_two_authorities_agree_on(case):
    """Accept exactly the compatible rows; refuse the rest, with a reason."""
    row = case["row"]
    try:
        check_row_compatible(row)
        accepted, reason = True, None
    except SnapshotUnavailable as exc:
        accepted, reason = False, exc.reason
    assert accepted is case["compatible"], (
        f"{case['name']}: expected accepted={case['compatible']}, got {accepted} ({reason})")
    if not accepted:
        assert reason == case["reject_reason"], f"{case['name']}: {reason}"
        assert reason  # a refusal always names its reason


def test_the_fixture_covers_every_reason_the_gate_can_raise(cases):
    """Every refusal reason in the fixture is a reason the gate actually raises."""
    raised = set()
    for case in cases:
        try:
            check_row_compatible(case["row"])
        except SnapshotUnavailable as exc:
            raised.add(exc.reason)
    expected = {c["reject_reason"] for c in cases if not c["compatible"]}
    assert expected <= raised


# ── 2. the completeness proof ────────────────────────────────────────────────

def test_a_complete_read_is_witnessed():
    rows = [_row(), _row(id="22222222-2222-4222-8222-222222222222", ticker="AMD")]
    reader = _Reader(positions=_ok(rows))
    snapshot = capture_snapshot("u-test", reader=reader)
    assert snapshot.population == "positions"
    assert len(snapshot.rows) == 2
    assert snapshot.completeness["exact_count"] == 2
    assert snapshot.completeness["complete"] is True
    assert snapshot.completeness["positions_reads"] == 1
    assert len(reader.positions_calls) == 1


def test_an_empty_book_is_complete_and_not_a_failure():
    """Zero rows with a stated count of zero is a COMPLETE empty book."""
    reader = _Reader(positions=_ok([]), watchlists=_ok([]))
    snapshot = capture_snapshot("u-test", reader=reader)
    assert snapshot.rows == ()
    assert snapshot.completeness["exact_count"] == 0
    # No open positions -> the watchlist union is the population, and it is
    # explicitly NOT a positions book.
    assert snapshot.population == "watchlist_union"
    assert snapshot.selected_position_ids == ()


@pytest.mark.parametrize("read, reason", [
    (_ok([_row()], count=2), REASON_COUNT_MISMATCH),
    (_ok([_row()], count=None), REASON_MISSING_COUNT),
    (_ok([_row()], first=1), REASON_NONZERO_START),
    (_ok([_row()], last=5), REASON_INVALID_RANGE),
    (_ok([_row()], count=MAX_SNAPSHOT_ROWS + 1), REASON_OVER_LIMIT),
    (_fail(), REASON_TRANSPORT),
])
def test_an_unprovable_read_is_unavailable(read, reason):
    reader = _Reader(positions=read)
    with pytest.raises(SnapshotUnavailable) as excinfo:
        capture_snapshot("u-test", reader=reader)
    assert excinfo.value.reason == reason


def test_a_truncated_read_is_unavailable_even_when_the_count_is_present():
    """The server says 5 rows exist and returned 3: the snapshot is NOT complete."""
    rows = [_row(id=f"{i:08d}-2222-4222-8222-222222222222") for i in range(3)]
    reader = _Reader(positions=_ok(rows, count=5, last=2))
    with pytest.raises(SnapshotUnavailable) as excinfo:
        capture_snapshot("u-test", reader=reader)
    assert excinfo.value.reason == REASON_COUNT_MISMATCH


def test_a_duplicate_id_is_unavailable():
    rows = [_row(), _row(ticker="AMD")]
    reader = _Reader(positions=_ok(rows))
    with pytest.raises(SnapshotUnavailable) as excinfo:
        capture_snapshot("u-test", reader=reader)
    assert excinfo.value.reason == REASON_DUPLICATE_IDS


def test_a_row_that_is_not_json_safe_is_unavailable():
    """A non-finite number cannot be carried in a witness: JSON has no literal."""
    rows = [_row(shares=float("inf"))]
    reader = _Reader(positions=_ok(rows))
    with pytest.raises(SnapshotUnavailable) as excinfo:
        capture_snapshot("u-test", reader=reader)
    assert excinfo.value.reason == REASON_NOT_JSON_SAFE


def test_a_thousand_rows_are_witnessed_and_a_thousand_and_one_are_not():
    rows = [_row(id=f"{i:08d}-2222-4222-8222-222222222222") for i in range(MAX_SNAPSHOT_ROWS)]
    snapshot = capture_snapshot("u-test", reader=_Reader(positions=_ok(rows)))
    assert len(snapshot.rows) == MAX_SNAPSHOT_ROWS
    assert snapshot.completeness["exact_count"] == MAX_SNAPSHOT_ROWS

    over = rows + [_row(id="ffffffff-2222-4222-8222-222222222222")]
    with pytest.raises(SnapshotUnavailable) as excinfo:
        capture_snapshot("u-test", reader=_Reader(positions=_ok(over)))
    assert excinfo.value.reason == REASON_OVER_LIMIT


def test_a_read_is_never_assembled_from_two_queries():
    """The capture makes exactly ONE positions read, whatever it finds."""
    rows = [_row()]
    reader = _Reader(positions=_ok(rows))
    capture_snapshot("u-test", reader=reader)
    assert len(reader.positions_calls) == 1


def test_the_read_is_owner_scoped():
    reader = _Reader(positions=_ok([_row()]))
    capture_snapshot("u-42", reader=reader)
    path = reader.positions_calls[0]["path"]
    assert "user_id=eq.u-42" in path, path
    assert "portfolio_positions?" in path


# ── 3. the transport helper ──────────────────────────────────────────────────

class _Resp:
    def __init__(self, payload, content_range=None):
        self._body = json.dumps(payload).encode()
        self.headers = {} if content_range is None else {"Content-Range": content_range}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body


def test_count_aware_read_carries_the_count_and_the_range(monkeypatch):
    from unittest.mock import patch
    from engine.neuralweb import brain_gateway as gw

    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    seen = {}

    def _open(req, *a, **kw):
        seen["url"] = req.full_url
        seen["headers"] = dict(req.header_items())
        return _Resp([{"id": "a"}], content_range="0-0/1")

    with patch("urllib.request.urlopen", side_effect=_open):
        result = gw._sb_get_count_aware("portfolio_positions?user_id=eq.u-1", limit=1000)

    assert result["ok"] is True
    assert result["count"] == 1
    assert result["range_first"] == 0
    assert result["range_last"] == 0
    assert result["returned_count"] == 1
    assert seen["headers"].get("Prefer") == "count=exact"
    assert seen["headers"].get("Range") == "0-999"
    assert "user_id=eq.u-1" in seen["url"]


def test_count_aware_read_without_a_content_range_reports_no_count(monkeypatch):
    from unittest.mock import patch
    from engine.neuralweb import brain_gateway as gw

    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    with patch("urllib.request.urlopen", return_value=_Resp([{"id": "a"}])):
        result = gw._sb_get_count_aware("portfolio_positions", limit=10)
    assert result["ok"] is True
    assert result["count"] is None, "an absent count must never be read as zero"
    assert result["range_first"] is None


def test_count_aware_read_failure_is_not_a_success(monkeypatch):
    from unittest.mock import patch
    from engine.neuralweb import brain_gateway as gw

    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
        result = gw._sb_get_count_aware("portfolio_positions", limit=10)
    assert result["ok"] is False
    assert result["rows"] is None
    assert result["count"] is None


def test_count_aware_read_without_a_store_is_not_configured(monkeypatch):
    from engine.neuralweb import brain_gateway as gw

    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "")
    result = gw._sb_get_count_aware("portfolio_positions", limit=10)
    assert result["ok"] is False
    assert result["error"] == "store_not_configured"


def test_the_legacy_get_is_untouched():
    """_sb_get is frozen: the count-aware helper is ADDITIVE."""
    from engine.neuralweb import brain_gateway as gw
    import inspect
    source = inspect.getsource(gw._sb_get)
    assert "return json.loads(resp.read())" in source
    assert "count=exact" not in source
    assert "Content-Range" not in source


def test_the_read_path_is_redacted_before_it_reaches_a_log(monkeypatch, caplog):
    from unittest.mock import patch
    from engine.neuralweb import brain_gateway as gw

    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    with caplog.at_level(logging.DEBUG):
        with patch("urllib.request.urlopen", side_effect=Exception("boom")):
            gw._sb_get_count_aware("portfolio_positions?user_id=eq.secret-owner", limit=10)
    assert "secret-owner" not in caplog.text
    assert "user_id=eq.***" in caplog.text


def test_content_range_parsing():
    from engine.neuralweb.brain_gateway import _parse_content_range
    assert _parse_content_range("0-24/26") == (0, 24, 26)
    assert _parse_content_range("*/0") == (None, None, 0)
    assert _parse_content_range("0-24/*") == (0, 24, None)
    assert _parse_content_range(None) == (None, None, None)
    assert _parse_content_range("nonsense") == (None, None, None)


# ── 4. the endpoint ──────────────────────────────────────────────────────────

def _client(monkeypatch, tmp_path, *, tier="pro", status="active", reader=None,
            ctx=None, holdings=None, population="positions", user=None):
    """Import app.main with a monkeypatched auth/tier/holdings/ctx + reader."""
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient  # noqa: PLC0415

    repo = tmp_path
    (repo / "site" / "data").mkdir(parents=True, exist_ok=True)
    if ctx is not None:
        (repo / "site" / "data" / "portfolio_ctx.json").write_text(
            json.dumps(ctx, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setenv("MACRO_REPO", str(repo))
    for mod in list(sys.modules):
        if mod == "app.main" or mod.startswith("app.main."):
            del sys.modules[mod]
    import app.main as m  # noqa: PLC0415

    if user is not None:
        m.app.dependency_overrides[m.require_user] = lambda: user
    monkeypatch.setattr(m, "_portfolio_resolve_tier",
                        lambda uid: {"tier": tier, "status": status})
    monkeypatch.setattr(m, "_portfolio_load_holdings",
                        lambda uid: ((holdings or []), population))
    if reader is not None:
        monkeypatch.setattr(pbc, "_default_reader", reader)
    return m, TestClient(m.app)


def _spy_on_compose(monkeypatch) -> list[dict]:
    """Record what the UNCHANGED composer was actually called with."""
    import engine.portfolio_brief as pb
    real = pb.compose_brief
    calls: list[dict] = []

    def _spy(ctx, holdings, today, generated_at, **kw):
        calls.append({"holdings": holdings, "population": kw.get("population")})
        return real(ctx, holdings, today, generated_at, **kw)

    monkeypatch.setattr(pb, "compose_brief", _spy)
    return calls


def test_an_ordinary_request_is_unchanged(monkeypatch, tmp_path):
    """No header -> the exact legacy loader, cache and response. No witness."""
    reader = _Reader(positions=_ok([_row()]))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        holdings=[{"ticker": "NVDA", "shares": 10, "entry_price": 100.0}],
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "portfolio_context" not in body
    assert body["schema"] == "portfolio_brief.v2"
    assert body["book"]["n"] == 1
    assert reader.positions_calls == [], "an ordinary request must not take the bound read"
    m.app.dependency_overrides.clear()


def test_an_opted_in_request_carries_the_witness(monkeypatch, tmp_path):
    rows = [_row(),
            _row(id="22222222-2222-4222-8222-222222222222", ticker="AMD", shares=5,
                 entry_price=50.0)]
    reader = _Reader(positions=_ok(rows))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 200, r.text
    body = r.json()
    witness = body["portfolio_context"]
    assert witness["schema"] == "portfolio_snapshot_witness.v1"
    assert witness["owner_id"] == "u-test"
    assert witness["population"] == "positions"
    assert witness["selected_position_ids"] == [
        "11111111-1111-4111-8111-111111111111",
        "22222222-2222-4222-8222-222222222222",
    ]
    assert len(witness["rows"]) == 2
    completeness = witness["completeness"]
    assert completeness["exact_count"] == 2
    assert completeness["range_first"] == 0
    assert completeness["range_last"] == 1
    assert completeness["returned_count"] == 2
    assert completeness["open_count"] == 2
    assert completeness["selected_count"] == 2
    assert completeness["positions_reads"] == 1
    assert completeness["complete"] is True
    assert r.headers.get("Cache-Control") == "private, no-store"
    m.app.dependency_overrides.clear()


def test_one_read_supplies_both_the_composer_rows_and_the_witness(monkeypatch, tmp_path):
    """The composer is called with the SELECTED source rows, from ONE read."""
    rows = [_row(),
            _row(id="22222222-2222-4222-8222-222222222222", ticker="AMD", shares=5,
                 entry_price=50.0)]
    reader = _Reader(positions=_ok(rows))
    calls = _spy_on_compose(monkeypatch)
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 200, r.text
    body = r.json()
    witness = body["portfolio_context"]

    assert len(calls) == 1
    holdings = calls[0]["holdings"]
    assert calls[0]["population"] == "positions"
    # The composer saw EXACTLY the selected source rows, verbatim.
    assert holdings == [{"ticker": "NVDA", "shares": 10, "entry_price": 100.0},
                        {"ticker": "AMD", "shares": 5, "entry_price": 50.0}]
    assert holdings == witness["composer_inputs"]
    # ...and those rows are the selected rows of the captured set.
    selected = {row["id"] for row in rows
                if row["id"] in witness["selected_position_ids"]}
    assert selected == set(witness["selected_position_ids"])
    assert len(reader.positions_calls) == 1
    m.app.dependency_overrides.clear()


def test_closed_rows_stay_in_the_witness(monkeypatch, tmp_path):
    rows = [_row(),
            _row(id="22222222-2222-4222-8222-222222222222", ticker="AMD",
                 status="closed", shares=5, entry_price=50.0)]
    reader = _Reader(positions=_ok(rows))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 200, r.text
    witness = r.json()["portfolio_context"]
    assert len(witness["rows"]) == 2, "a closed row is still part of the captured book"
    assert witness["selected_position_ids"] == [
        "11111111-1111-4111-8111-111111111111"]
    assert witness["completeness"]["open_count"] == 1
    closed = [row for row in witness["rows"] if row["ticker"] == "AMD"][0]
    assert closed["status"] == "closed"
    assert closed["shares"] == 5, "the closed row keeps its original values"
    m.app.dependency_overrides.clear()


def test_a_closed_status_variant_is_not_selected(monkeypatch, tmp_path):
    """Terminal's canonical rule: only a trimmed+lowercased 'closed' is closed."""
    rows = [_row(status="CLOSED"),
            _row(id="22222222-2222-4222-8222-222222222222", ticker="AMD", status=" open ")]
    reader = _Reader(positions=_ok(rows))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    witness = r.json()["portfolio_context"]
    assert witness["selected_position_ids"] == [
        "22222222-2222-4222-8222-222222222222"]
    m.app.dependency_overrides.clear()


def test_a_same_count_mutation_is_witnessed_fresh(monkeypatch, tmp_path):
    """A changed value with an UNCHANGED count must not be served from a cache."""
    state = {"shares": 10}

    def _positions():
        return _ok([_row(shares=state["shares"])])

    reader = _Reader(positions=_positions)
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    first = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER).json()
    state["shares"] = 25
    second = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER).json()

    assert first["portfolio_context"]["composer_inputs"][0]["shares"] == 10
    assert second["portfolio_context"]["composer_inputs"][0]["shares"] == 25
    assert first["portfolio_context"]["completeness"]["exact_count"] == \
        second["portfolio_context"]["completeness"]["exact_count"] == 1
    # The FIRST response object is untouched: a fresh witness is never stamped
    # onto an earlier brief.
    assert first["portfolio_context"]["composer_inputs"][0]["shares"] == 10
    assert len(reader.positions_calls) == 2
    m.app.dependency_overrides.clear()


def test_a_primed_legacy_cache_cannot_affect_a_bound_request(monkeypatch, tmp_path):
    reader = _Reader(positions=_ok([_row()]))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        holdings=[{"ticker": "NVDA", "shares": 10, "entry_price": 100.0}],
                        user={"id": "u-test"})
    # Prime the legacy cache with a brief that is obviously not the live one.
    primed = {"schema": "portfolio_brief.v2", "book": {"n": 99}, "marker": "primed"}
    m._PORTFOLIO_CACHE[("u-test", 0.0, "primed")] = (primed, 9e18)

    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("marker") != "primed", "the bound request served the cached brief"
    assert "portfolio_context" in body
    assert body["portfolio_context"]["rows"][0]["ticker"] == "NVDA"

    # ...and the cached object was NOT mutated.
    cached = m._PORTFOLIO_CACHE[("u-test", 0.0, "primed")][0]
    assert cached is primed
    assert cached == {"schema": "portfolio_brief.v2", "book": {"n": 99}, "marker": "primed"}
    m.app.dependency_overrides.clear()


def test_a_bound_request_never_writes_the_legacy_cache(monkeypatch, tmp_path):
    reader = _Reader(positions=_ok([_row()]))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 200, r.text
    assert m._PORTFOLIO_CACHE == {}, "bound mode must not write the legacy cache"
    m.app.dependency_overrides.clear()


def test_an_ordinary_request_still_uses_the_legacy_cache(monkeypatch, tmp_path):
    """The ordinary path keeps its cache: the bound path did not break it."""
    reader = _Reader(positions=_ok([_row()]))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        holdings=[{"ticker": "NVDA", "shares": 10, "entry_price": 100.0}],
                        user={"id": "u-test"})
    assert client.get("/api/portfolio/brief").status_code == 200
    assert len(m._PORTFOLIO_CACHE) == 1
    before = dict(m._PORTFOLIO_CACHE)
    assert client.get("/api/portfolio/brief").status_code == 200
    assert m._PORTFOLIO_CACHE == before, "the legacy cache must still serve its own hit"
    m.app.dependency_overrides.clear()


def test_authentication_precedes_every_private_read(monkeypatch, tmp_path):
    reader = _Reader(positions=_ok([_row()]))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(), user=None)
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code in (401, 403)
    assert reader.positions_calls == [], "an unauthenticated request must not read positions"
    m.app.dependency_overrides.clear()


def test_entitlement_precedes_every_private_read(monkeypatch, tmp_path):
    reader = _Reader(positions=_ok([_row()]))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(), tier="free",
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 403
    assert r.json()["detail"]["error"] == "pro_required"
    assert reader.positions_calls == [], "a non-Pro request must not read positions"
    m.app.dependency_overrides.clear()


def test_an_unsupported_contract_version_is_told(monkeypatch, tmp_path):
    reader = _Reader(positions=_ok([_row()]))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief",
                   headers={"X-Mastermind-Portfolio-Context": "snapshot-v2"})
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "unsupported_portfolio_context"
    assert reader.positions_calls == []
    m.app.dependency_overrides.clear()


@pytest.mark.parametrize("read, reason", [
    (_ok([_row()], count=2), REASON_COUNT_MISMATCH),
    (_ok([_row()], count=None), REASON_MISSING_COUNT),
    (_ok([_row()], first=1), REASON_NONZERO_START),
    (_ok([_row()], last=5), REASON_INVALID_RANGE),
    (_ok([_row()], count=MAX_SNAPSHOT_ROWS + 1), REASON_OVER_LIMIT),
    (_fail(), REASON_TRANSPORT),
])
def test_an_unprovable_capture_is_unavailable_at_the_endpoint(monkeypatch, tmp_path,
                                                              read, reason):
    reader = _Reader(positions=read)
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 503, r.text
    detail = r.json()["detail"]
    assert detail["error"] == "portfolio_snapshot_unavailable"
    assert detail["reason"] == reason
    assert "portfolio_context" not in r.json()
    m.app.dependency_overrides.clear()


def test_a_duplicate_id_is_unavailable_at_the_endpoint(monkeypatch, tmp_path):
    reader = _Reader(positions=_ok([_row(), _row(ticker="AMD")]))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 503
    assert r.json()["detail"]["reason"] == REASON_DUPLICATE_IDS
    m.app.dependency_overrides.clear()


def test_a_row_the_two_readers_disagree_about_is_unavailable(monkeypatch, tmp_path):
    """A boolean share: Python reads 1, the Terminal reads null."""
    reader = _Reader(positions=_ok([_row(shares=True)]))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 503
    assert r.json()["detail"]["reason"] == REASON_SHARES_MISMATCH
    m.app.dependency_overrides.clear()


def test_the_watchlist_union_is_explicit_and_never_a_positions_book(monkeypatch, tmp_path):
    """A PROVEN zero-open result may be followed by the watchlist union."""
    reader = _Reader(
        positions=_ok([_row(status="closed")]),
        watchlists=_ok([{"id": "wl-1"}]),
        symbols=_ok([{"symbol": "AMD"}, {"symbol": "NVDA"}]),
    )
    calls = _spy_on_compose(monkeypatch)
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 200, r.text
    witness = r.json()["portfolio_context"]
    assert witness["population"] == "watchlist_union"
    assert witness["composer_input_source"] == "watchlist_union"
    assert witness["selected_position_ids"] == [], "a union can never qualify as positions"
    assert witness["completeness"]["open_count"] == 0
    assert witness["completeness"]["positions_reads"] == 1
    assert witness["completeness"]["watchlist"]["reads"] == 2
    assert calls[0]["population"] == "watchlist_union"
    assert calls[0]["holdings"] == [
        {"ticker": "AMD", "shares": None, "entry_price": None},
        {"ticker": "NVDA", "shares": None, "entry_price": None},
    ]
    # No SECOND positions query: the zero-open fact came from the one capture.
    assert len(reader.positions_calls) == 1
    m.app.dependency_overrides.clear()


def test_the_watchlist_union_is_not_produced_from_an_unknown_positions_read(monkeypatch,
                                                                           tmp_path):
    """An incomplete positions read must NOT fall through to the union."""
    reader = _Reader(
        positions=_ok([_row()], count=2),
        watchlists=_ok([{"id": "wl-1"}]),
        symbols=_ok([{"symbol": "AMD"}]),
    )
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 503
    assert r.json()["detail"]["reason"] == REASON_COUNT_MISMATCH
    assert [c for c in reader.calls if c["path"].startswith("watchlists")] == []
    m.app.dependency_overrides.clear()


def test_a_failed_watchlist_read_is_unavailable_not_an_empty_union(monkeypatch, tmp_path):
    reader = _Reader(positions=_ok([]), watchlists=_fail())
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-test"})
    r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 503
    reason = r.json()["detail"]["reason"]
    assert reason.startswith(REASON_WATCHLIST_PREFIX), reason
    m.app.dependency_overrides.clear()


def test_the_witness_never_reaches_a_log_or_a_url(monkeypatch, tmp_path, caplog):
    rows = [_row(ticker="SECRETTICKER", shares=10, entry_price=100.0)]
    reader = _Reader(positions=_ok(rows))
    with caplog.at_level(logging.DEBUG):
        m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                            user={"id": "u-test"})
        r = client.get("/api/portfolio/brief", headers=SNAPSHOT_HEADER)
    assert r.status_code == 200, r.text
    assert "SECRETTICKER" not in caplog.text
    for call in reader.calls:
        assert "SECRETTICKER" not in call["path"]
    m.app.dependency_overrides.clear()


def test_the_header_selects_a_contract_and_grants_no_authority(monkeypatch, tmp_path):
    """The header carries no owner: the owner comes from the session alone."""
    reader = _Reader(positions=_ok([_row()]))
    m, client = _client(monkeypatch, tmp_path, reader=reader, ctx=_ctx(),
                        user={"id": "u-session-owner"})
    r = client.get("/api/portfolio/brief", headers={
        "X-Mastermind-Portfolio-Context": "snapshot-v1",
        "X-Owner-Id": "someone-else",
    })
    assert r.status_code == 200, r.text
    witness = r.json()["portfolio_context"]
    assert witness["owner_id"] == "u-session-owner"
    assert "user_id=eq.u-session-owner" in reader.positions_calls[0]["path"]
    m.app.dependency_overrides.clear()


# ── 5. header handling ───────────────────────────────────────────────────────

def test_the_header_helpers():
    assert snapshot_requested("snapshot-v1") is True
    assert snapshot_requested(" snapshot-v1 ") is True
    assert snapshot_requested(None) is False
    assert snapshot_requested("") is False
    assert snapshot_requested("snapshot-v2") is False
    assert snapshot_header_unsupported("snapshot-v2") is True
    assert snapshot_header_unsupported("") is False
    assert snapshot_header_unsupported(None) is False


# ── 6. the witness itself ────────────────────────────────────────────────────

def test_the_witness_preserves_the_original_row_values():
    rows = [_row(entry_currency="USD",
                 entry_currency_basis={"ticker": "NVDA", "price": 100.0},
                 notes="core\nposition", created_at="2026-01-15T09:30:00.123456+00:00")]
    snapshot = capture_snapshot("u-test", reader=_Reader(positions=_ok(rows)))
    witness = build_witness(snapshot)
    assert witness["rows"] == rows, "the witness must carry the captured rows verbatim"
    assert witness["rows"][0]["entry_currency_basis"] == {"ticker": "NVDA", "price": 100.0}
    assert witness["rows"][0]["notes"] == "core\nposition"


def test_the_witness_is_serialisable_as_strict_json():
    rows = [_row()]
    snapshot = capture_snapshot("u-test", reader=_Reader(positions=_ok(rows)))
    witness = build_witness(snapshot)

    def _reject(constant):  # pragma: no cover
        raise AssertionError(f"the witness is not strict JSON: {constant!r}")

    # allow_nan=False refuses Infinity/NaN on the way out; parse_constant
    # refuses them on the way back in (a strict-JSON reader's behaviour).
    text = json.dumps(witness, allow_nan=False)
    assert json.loads(text, parse_constant=_reject) == witness


def test_the_witness_carries_the_composer_inputs_it_describes():
    rows = [_row(), _row(id="22222222-2222-4222-8222-222222222222", ticker="AMD",
                         status="closed")]
    snapshot = capture_snapshot("u-test", reader=_Reader(positions=_ok(rows)))
    witness = build_witness(snapshot)
    assert witness["composer_inputs"] == [
        {"ticker": "NVDA", "shares": 10, "entry_price": 100.0}]
    assert witness["composer_input_source"] == "positions"
    assert witness["selected_position_ids"] == [
        "11111111-1111-4111-8111-111111111111"]


def test_the_captured_rows_are_frozen_against_later_mutation():
    """Mutating the captured rows cannot reach the witness."""
    rows = [_row()]
    reader = _Reader(positions=_ok(rows))
    snapshot = capture_snapshot("u-test", reader=reader)
    rows[0]["shares"] = 999999
    rows[0]["ticker"] = "MUTATED"
    witness = build_witness(snapshot)
    assert witness["rows"][0]["shares"] == 10
    assert witness["rows"][0]["ticker"] == "NVDA"
