"""Parity between news-universe build failures and read-only diagnosis."""
from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone

import pytest

from engine import qbus_news_universe_snapshot as m


UTC = timezone.utc
NOW = datetime(2026, 10, 5, 22, 0, tzinfo=UTC)

# Every NewsUniverseSnapshotError code raised inside the builder's ticker loop.
PER_TICKER_CODES = (
    "duplicate_security_resolution",
    "market_alias_invalid",
    "market_alias_unresolved",
    "membership_alias_unresolved",
    "security_master_superseded",
    "security_master_unresolved",
)


def _current(*symbols):
    return [{"symbol": symbol} for symbol in symbols]


def _pit(*rows):
    return [
        {"ticker": ticker, "start_date": start, "end_date": end, "src": "sp500"}
        for ticker, start, end in rows
    ]


def _aliases(*rows):
    out = []
    for membership, market, sid in rows:
        out.extend(
            [
                {
                    "vendor": "membership",
                    "vendor_symbol": membership,
                    "security_id": sid,
                    "valid_from": None,
                    "valid_to": None,
                },
                {
                    "vendor": "yahoo_fetch",
                    "vendor_symbol": market,
                    "security_id": sid,
                    "valid_from": None,
                    "valid_to": None,
                },
            ]
        )
    return out


def _master(*sids):
    return [
        {
            "security_id": sid,
            "issuer_id": "ISS:" + sid.removeprefix("SEC:"),
            "issuer_state": "RESOLVED",
            "listing_key": sid.removeprefix("SEC:"),
            "security_state": None,
            "superseded_by": None,
            "issuer_cik": None,
        }
        for sid in sids
    ]


def _nvda(**overrides):
    sid = "SEC:US-XNAS-NVDA"
    base = dict(
        current_rows=_current("NVDA"),
        pit_rows=_pit(("NVDA", "2001-01-01", None)),
        alias_rows=_aliases(("NVDA", "NVDA", sid)),
        security_rows=_master(sid),
        ticker="NVDA",
    )
    base.update(overrides)
    return base


def _raises_in_ticker_loop(fn) -> set[str]:
    tree = ast.parse(inspect.getsource(fn))
    found: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.in_ticker = False

        def visit_For(self, node: ast.For) -> None:
            is_ticker = isinstance(node.target, ast.Name) and node.target.id == "ticker"
            previous = self.in_ticker
            if is_ticker:
                self.in_ticker = True
            self.generic_visit(node)
            self.in_ticker = previous

        def visit_Raise(self, node: ast.Raise) -> None:
            if self.in_ticker and isinstance(node.exc, ast.Call) and node.exc.args:
                arg = node.exc.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.add(arg.value)
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            # market_alias_invalid is raised inside _symbol, not at the call.
            if (
                self.in_ticker
                and isinstance(node.func, ast.Name)
                and node.func.id == "_symbol"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                found.add(node.args[1].value)
            self.generic_visit(node)

    Visitor().visit(tree)
    return found


def _assert_parity(*, code, ticker, current_rows, pit_rows, alias_rows, security_rows):
    common = dict(
        current_rows=current_rows,
        pit_rows=pit_rows,
        alias_rows=alias_rows,
        security_rows=security_rows,
        observed_at=NOW,
    )
    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(**common, min_count=1)
    assert exc.value.code == code

    diagnosis = m.diagnose_news_universe(**common)
    assert diagnosis["schema"] == "qbus.news_universe_diagnosis.v1"
    assert diagnosis["observed_at"] == NOW.isoformat()
    assert diagnosis["table_errors"] == []
    assert diagnosis["unresolved"][0] == {"ticker": ticker, "reason": code}
    assert diagnosis["reason_counts"][code] >= 1
    assert (
        diagnosis["resolved_count"] + len(diagnosis["unresolved"])
        == diagnosis["current_count"]
    )
    return diagnosis


def _case_membership(_monkeypatch):
    spec = _nvda()
    for row in spec["alias_rows"]:
        if row["vendor"] == "membership":
            row["valid_to"] = "2026-10-05"
    return spec


def _case_market(_monkeypatch):
    spec = _nvda()
    for row in spec["alias_rows"]:
        if row["vendor"] == "yahoo_fetch":
            row["valid_to"] = "2026-10-05"
    return spec


def _case_master_missing(_monkeypatch):
    return _nvda(security_rows=[])


def _case_superseded(_monkeypatch):
    sid = "SEC:US-XNAS-NVDA"
    master = _master(sid)
    master[0]["security_state"] = "SUPERSEDED_DUPLICATE_MINT"
    master[0]["superseded_by"] = "SEC:US-XNAS-NVDA2"
    return _nvda(security_rows=master)


def _case_duplicate(monkeypatch):
    from lib.dataos.identity import VendorAliasTable

    # Overlapping membership rows for one security are refused while the alias
    # table is built. This stub is what lets the ticker walk reach the duplicate.
    monkeypatch.setattr(VendorAliasTable, "_assert_unambiguous", lambda self: None)
    sid = "SEC:US-XNYS-SAME"
    return dict(
        current_rows=_current("AAA", "BBB"),
        pit_rows=_pit(("AAA", "2020-01-01", None), ("BBB", "2020-01-01", None)),
        alias_rows=_aliases(("AAA", "AAA", sid), ("BBB", "BBB", sid)),
        security_rows=_master(sid),
        ticker="BBB",
    )


def _case_market_invalid(monkeypatch):
    from lib.dataos.identity import VendorAliasTable

    real = VendorAliasTable.vendor_symbol_for

    def fake(self, vendor, security_id_, on, *, decision_at=None):
        if vendor == "yahoo_fetch":
            return "\x00"
        return real(self, vendor, security_id_, on, decision_at=decision_at)

    # The historical-symbol scan would have rejected this symbol as a table
    # error. Returning it only from the lookup is what reaches market_alias_invalid.
    monkeypatch.setattr(VendorAliasTable, "vendor_symbol_for", fake)
    return _nvda()


_CASES = {
    "membership_alias_unresolved": _case_membership,
    "market_alias_unresolved": _case_market,
    "security_master_unresolved": _case_master_missing,
    "security_master_superseded": _case_superseded,
    "duplicate_security_resolution": _case_duplicate,
    "market_alias_invalid": _case_market_invalid,
}


def test_parity_suite_names_every_per_ticker_raise_in_the_builder():
    assert _raises_in_ticker_loop(m.build_news_universe_snapshot) == set(PER_TICKER_CODES)
    assert set(_CASES) == set(PER_TICKER_CODES)


@pytest.mark.parametrize("code", PER_TICKER_CODES)
def test_diagnose_matches_builder_per_ticker_reason(code, monkeypatch):
    spec = _CASES[code](monkeypatch)
    ticker = spec.pop("ticker")
    _assert_parity(code=code, ticker=ticker, **spec)


def test_diagnose_lists_later_tickers_after_the_builder_stops():
    rows = _aliases(
        ("AAA", "AAA", "SEC:US-XNAS-AAA"),
        ("CCC", "CCC", "SEC:US-XNAS-CCC"),
        ("DDD", "DDD", "SEC:US-XNAS-DDD"),
    )
    rows = [
        row
        for row in rows
        if not (row["vendor"] == "yahoo_fetch" and row["security_id"] == "SEC:US-XNAS-DDD")
    ]
    master = _master("SEC:US-XNAS-AAA", "SEC:US-XNAS-CCC", "SEC:US-XNAS-DDD")
    for row in master:
        if row["security_id"] == "SEC:US-XNAS-CCC":
            row["security_state"] = "SUPERSEDED_DUPLICATE_MINT"
            row["superseded_by"] = "SEC:US-XNAS-CCC2"
    common = dict(
        current_rows=_current("AAA", "BBB", "CCC", "DDD"),
        pit_rows=[],
        alias_rows=rows,
        security_rows=master,
        observed_at=NOW,
    )

    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(**common, min_count=1)
    diagnosis = m.diagnose_news_universe(**common)

    assert exc.value.code == "membership_alias_unresolved"
    assert diagnosis["table_errors"] == []
    assert diagnosis["current_count"] == 4
    assert diagnosis["resolved_count"] == 1
    assert diagnosis["unresolved"] == [
        {"ticker": "BBB", "reason": "membership_alias_unresolved"},
        {"ticker": "CCC", "reason": "security_master_superseded"},
        {"ticker": "DDD", "reason": "market_alias_unresolved"},
    ]
    assert diagnosis["unresolved"][0]["reason"] == exc.value.code
    assert diagnosis["reason_counts"] == {
        "market_alias_unresolved": 1,
        "membership_alias_unresolved": 1,
        "security_master_superseded": 1,
    }
    assert [row["ticker"] for row in diagnosis["unresolved"]] == ["BBB", "CCC", "DDD"]


def test_clean_diagnosis_means_the_builder_raises_no_per_ticker_code():
    common = dict(
        current_rows=_current("NVDA"),
        pit_rows=_pit(("NVDA", "2001-01-01", None)),
        alias_rows=_aliases(("NVDA", "NVDA", "SEC:US-XNAS-NVDA")),
        security_rows=_master("SEC:US-XNAS-NVDA"),
        observed_at=NOW,
    )
    diagnosis = m.diagnose_news_universe(**common)
    assert diagnosis["unresolved"] == []
    assert diagnosis["table_errors"] == []
    assert diagnosis["resolved_count"] == diagnosis["current_count"] == 1
    assert set(diagnosis) == {
        "current_count",
        "observed_at",
        "reason_counts",
        "resolved_count",
        "schema",
        "table_errors",
        "unresolved",
    }

    built = m.build_news_universe_snapshot(**common, min_count=1)
    assert len(built["securities"]) == 1

    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(**common, min_count=400)
    assert exc.value.code == "current_roster_suspicious"
    assert exc.value.code not in PER_TICKER_CODES


def test_collapsed_membership_rows_stay_a_table_error():
    sid = "SEC:US-XNYS-SAME"
    common = dict(
        current_rows=_current("AAA", "BBB"),
        pit_rows=_pit(("AAA", "2020-01-01", None), ("BBB", "2020-01-01", None)),
        alias_rows=_aliases(("AAA", "AAA", sid), ("BBB", "BBB", sid)),
        security_rows=_master(sid),
        observed_at=NOW,
    )
    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(**common, min_count=1)
    diagnosis = m.diagnose_news_universe(**common)

    assert exc.value.code == "alias_table_invalid"
    assert diagnosis["table_errors"] == ["alias_table_invalid"]
    assert diagnosis["unresolved"] == []
    assert diagnosis["resolved_count"] == 0
    assert diagnosis["reason_counts"] == {}
    assert diagnosis["current_count"] == 2


def test_alias_date_errors_keep_their_own_table_code():
    spec = _nvda()
    spec["alias_rows"][0]["valid_from"] = "not-a-date"
    spec.pop("ticker")
    common = {**spec, "observed_at": NOW}
    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(**common, min_count=1)
    diagnosis = m.diagnose_news_universe(**common)

    assert exc.value.code == "alias_valid_from_invalid"
    assert diagnosis["table_errors"] == ["alias_valid_from_invalid"]
    assert diagnosis["unresolved"] == []


def test_security_master_load_failure_is_a_table_error():
    spec = _nvda(security_rows=[{"issuer_cik": "NOT-A-CIK"}])
    spec.pop("ticker")
    common = {**spec, "observed_at": NOW}
    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(**common, min_count=1)
    diagnosis = m.diagnose_news_universe(**common)

    assert exc.value.code == "security_master_invalid"
    assert diagnosis["table_errors"] == ["security_master_invalid"]
    assert diagnosis["unresolved"] == []


def test_pit_interval_error_stops_before_a_missing_ticker():
    common = dict(
        current_rows=_current("GHOST", "NVDA"),
        pit_rows=_pit(("NVDA", "2020-01-01", "2020-01-01")),
        alias_rows=_aliases(("NVDA", "NVDA", "SEC:US-XNAS-NVDA")),
        security_rows=_master("SEC:US-XNAS-NVDA"),
        observed_at=NOW,
    )
    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(**common, min_count=1)
    diagnosis = m.diagnose_news_universe(**common)

    assert exc.value.code == "pit_interval_invalid"
    assert diagnosis["table_errors"] == ["pit_interval_invalid"]
    assert diagnosis["unresolved"] == []
    assert diagnosis["current_count"] == 2
    assert diagnosis["resolved_count"] == 0


def test_unlawful_historical_symbol_is_not_reported_as_market_alias_invalid():
    spec = _nvda(alias_rows=_aliases(("NVDA", "N" * 65, "SEC:US-XNAS-NVDA")))
    spec.pop("ticker")
    common = {**spec, "observed_at": NOW}
    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(**common, min_count=1)
    diagnosis = m.diagnose_news_universe(**common)

    assert exc.value.code == "historical_alias_invalid"
    assert diagnosis["table_errors"] == ["historical_alias_invalid"]
    assert diagnosis["unresolved"] == []
    assert "market_alias_invalid" not in diagnosis["reason_counts"]


def test_duplicate_current_symbol_is_a_table_error_with_no_roster_count():
    common = dict(
        current_rows=_current("NVDA", "NVDA"),
        pit_rows=_pit(("NVDA", "2001-01-01", None)),
        alias_rows=_aliases(("NVDA", "NVDA", "SEC:US-XNAS-NVDA")),
        security_rows=_master("SEC:US-XNAS-NVDA"),
        observed_at=NOW,
    )
    with pytest.raises(m.NewsUniverseSnapshotError) as exc:
        m.build_news_universe_snapshot(**common, min_count=1)
    diagnosis = m.diagnose_news_universe(**common)

    assert exc.value.code == "current_roster_duplicate"
    assert diagnosis["table_errors"] == ["current_roster_duplicate"]
    assert diagnosis["current_count"] == 0
    assert diagnosis["unresolved"] == []


def test_naive_observed_at_raises_the_builder_code():
    common = dict(
        current_rows=_current("NVDA"),
        pit_rows=[],
        alias_rows=[],
        security_rows=[],
        observed_at=datetime(2026, 10, 5, 22, 0),
    )
    with pytest.raises(m.NewsUniverseSnapshotError) as built:
        m.build_news_universe_snapshot(**common, min_count=1)
    with pytest.raises(m.NewsUniverseSnapshotError) as diagnosed:
        m.diagnose_news_universe(**common)
    assert built.value.code == diagnosed.value.code == "observed_at_invalid"


def test_diagnose_rejects_positional_arguments():
    with pytest.raises(TypeError):
        m.diagnose_news_universe([], [], [], [], NOW)
