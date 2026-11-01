"""Tests for the sector holdings coverage emitter — Options R1 W2B, section L-W2B-MACRO.

The Terminal reads sector_holdings_coverage.json through a strict validator
(SPEC §C): any violation drops the whole file, so this suite re-checks every
rule of that contract, not just the happy path. Three denominators stay
separate everywhere: rows listed, the fund's total weight, the top of the
list. The store keeps only the top 20 by weight, so the fund's total holding
count is unknown — it must surface as null, never 0 and never the listed
count. Synthetic frames only; the one test that needs the committed parquet
skips cleanly when it is absent.
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.build_sector_holdings_coverage as shc  # noqa: E402
from scripts.build_sector_holdings_coverage import (  # noqa: E402
    FUNDS,
    SCHEMA,
    build_holdings_coverage,
    coverage_for_fund,
    emit_holdings_coverage_additive,
    load_snapshots,
    main,
)

STORE_DIR = ROOT / "data" / "sector_holdings"
TICKER_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)?$")


def _frame(rows, day="2026-10-19", ranks=None):
    """A store-shaped frame: index = as_of datetime (unnamed), columns ticker/name/weight_pct/rank."""
    n = len(rows)
    return pd.DataFrame(
        {
            "ticker": [t for t, _ in rows],
            "name": [f"{t or 'CASH'} holdings row" for t, _ in rows],
            "weight_pct": [w for _, w in rows],
            "rank": ranks if ranks is not None else list(range(1, n + 1)),
        },
        index=pd.to_datetime([day] * n),
    )


def _assert_contract(feed):
    """Every rule the Terminal reader enforces (SPEC §C) — the file is rejected
    whole on any violation, so each one is pinned here independently."""
    assert set(feed) == {"meta", "funds"}
    meta = feed["meta"]
    assert list(meta) == ["schema", "asOf", "source"]
    assert meta["schema"] == SCHEMA
    assert isinstance(meta["source"], str) and 0 < len(meta["source"]) <= 64
    meta_day = date.fromisoformat(meta["asOf"])
    funds = feed["funds"]
    assert len(funds) <= 40
    ids = [f["fund"] for f in funds]
    assert len(ids) == len(set(ids))
    for f in funds:
        assert re.fullmatch(r"^[A-Z][A-Z0-9.]{0,11}$", f["fund"])
        assert list(f) == ["fund", "as_of", "n_holdings_total", "total_unknown",
                           "listed", "coverage"]
        assert date.fromisoformat(f["as_of"]) <= meta_day
        listed = f["listed"]
        if f["total_unknown"]:
            assert f["n_holdings_total"] is None
        else:
            assert isinstance(f["n_holdings_total"], int)
            assert f["n_holdings_total"] >= 1
            assert f["n_holdings_total"] >= len(listed)
        assert len(listed) <= 60
        tickers: set[str] = set()
        prev = None
        for i, row in enumerate(listed):
            assert list(row) == ["ticker", "weight_pct", "rank"]
            assert TICKER_RE.fullmatch(row["ticker"])
            assert row["ticker"] not in tickers
            tickers.add(row["ticker"])
            w = row["weight_pct"]
            assert isinstance(w, (int, float)) and not isinstance(w, bool)
            assert math.isfinite(w) and 0 <= w <= 100
            assert row["rank"] == i + 1
            if prev is not None:
                assert w <= prev  # weights non-increasing down the list
            prev = w
        c = f["coverage"]
        assert list(c) == ["count", "weight_pct", "concentration"]
        assert list(c["count"]) == ["listed", "total"]
        assert c["count"]["listed"] == len(listed)
        assert c["count"]["total"] == f["n_holdings_total"]
        assert isinstance(c["weight_pct"], (int, float))
        assert not isinstance(c["weight_pct"], bool)
        assert math.isfinite(c["weight_pct"])
        assert c["weight_pct"] <= 100.0001
        if listed:
            assert abs(c["weight_pct"] - round(sum(r["weight_pct"] for r in listed), 2)) <= 0.01
        else:
            assert c["weight_pct"] == 0.0
        conc = c["concentration"]
        assert list(conc) == ["top3_of_fund_pct", "top3_of_sample_pct"]
        if len(listed) < 3:
            assert conc["top3_of_fund_pct"] is None
            assert conc["top3_of_sample_pct"] is None
        else:
            top3 = round(sum(r["weight_pct"] for r in listed[:3]), 2)
            assert abs(conc["top3_of_fund_pct"] - top3) <= 0.01
            if c["weight_pct"] == 0:
                assert conc["top3_of_sample_pct"] is None
            else:
                assert conc["top3_of_sample_pct"] is not None
                expected = round(top3 / c["weight_pct"] * 100, 2)
                assert abs(conc["top3_of_sample_pct"] - expected) <= 0.01
    assert json.loads(json.dumps(feed)) == feed


def test_latest_snapshot_is_listed_in_rank_order_with_separate_denominators():
    latest = [("NVDA", 14.21), ("AAPL", 12.05), ("MSFT", 6.33), ("UNH", 5.10), ("JPM", 4.20)]
    snap = pd.concat([_frame([("OLD", 1.0)], day="2026-10-16"),
                      _frame(latest, day="2026-10-19")])
    cov = coverage_for_fund("XLK", snap, asof=date(2026, 10, 20))
    assert cov["as_of"] == "2026-10-19"  # only the latest index date is used
    listed = cov["listed"]
    assert [r["ticker"] for r in listed] == ["NVDA", "AAPL", "MSFT", "UNH", "JPM"]
    assert [r["rank"] for r in listed] == [1, 2, 3, 4, 5]  # contiguous, not the stored rank
    weight = cov["coverage"]["weight_pct"]
    assert weight == round(sum(r["weight_pct"] for r in listed), 2) == 41.89
    top3 = cov["coverage"]["concentration"]["top3_of_fund_pct"]
    assert top3 == round(sum(r["weight_pct"] for r in listed[:3]), 2) == 32.59
    share = cov["coverage"]["concentration"]["top3_of_sample_pct"]
    assert share == round(top3 / weight * 100, 2) == 77.8
    # the store holds only the top 20: the total is unknown, never 0 or 5
    assert cov["coverage"]["count"]["total"] is None
    assert cov["n_holdings_total"] is None and cov["total_unknown"] is True


def test_unknown_total_is_null_never_zero_or_the_listed_count():
    snap = _frame([("NVDA", 14.21), ("AAPL", 12.05), ("MSFT", 6.33)])
    cov = coverage_for_fund("XLK", snap, asof=date(2026, 10, 20))
    assert cov["n_holdings_total"] is None
    assert cov["coverage"]["count"]["total"] is None
    assert cov["total_unknown"] is True
    feed = build_holdings_coverage({"XLK": snap}, funds=["XLK"])
    text = json.dumps(feed, separators=(",", ":"), ensure_ascii=False)
    assert '"n_holdings_total":null' in text
    assert '"n_holdings_total":0' not in text
    assert '"n_holdings_total":20' not in text
    big = _frame([(f"T{i:02d}", round(5.0 - i * 0.2, 2)) for i in range(20)])
    cov25 = coverage_for_fund("XLK", big, asof=date(2026, 10, 20), total=25)
    assert cov25["total_unknown"] is False
    assert cov25["n_holdings_total"] == 25
    assert cov25["coverage"]["count"]["total"] == 25
    cov5 = coverage_for_fund("XLK", big, asof=date(2026, 10, 20), total=5)
    assert cov5["total_unknown"] is True and cov5["n_holdings_total"] is None


def test_fewer_than_three_listed_leaves_concentration_null():
    snap = _frame([("NVDA", 14.21), ("AAPL", 12.05)])
    conc = coverage_for_fund("XLK", snap, asof=date(2026, 10, 20))["coverage"]["concentration"]
    assert conc["top3_of_fund_pct"] is None
    assert conc["top3_of_sample_pct"] is None
    one = coverage_for_fund("XLK", _frame([("NVDA", 14.21)]), asof=date(2026, 10, 20))
    assert one["coverage"]["concentration"]["top3_of_fund_pct"] is None


def test_missing_fund_snapshot_is_an_empty_fund_not_an_error():
    asof = date(2026, 10, 19)
    for snap in (None, pd.DataFrame()):
        cov = coverage_for_fund("XLF", snap, asof=asof)
        assert cov["listed"] == []
        assert cov["coverage"]["count"]["listed"] == 0
        assert cov["coverage"]["weight_pct"] == 0.0
        assert cov["coverage"]["count"]["total"] is None
        assert cov["n_holdings_total"] is None and cov["total_unknown"] is True
        assert cov["coverage"]["concentration"] == {
            "top3_of_fund_pct": None, "top3_of_sample_pct": None}
    snap = _frame([("NVDA", 14.21), ("AAPL", 12.05), ("MSFT", 6.33)], day="2026-10-16")
    feed = build_holdings_coverage({"XLK": snap})
    assert [f["fund"] for f in feed["funds"]] == list(FUNDS)
    meta_asof = feed["meta"]["asOf"]
    assert meta_asof == "2026-10-16"
    for f in feed["funds"]:
        if f["fund"] == "XLK":
            assert f["as_of"] == "2026-10-16"
        else:  # every other fund emitted as an empty fund at meta.asOf
            assert f["as_of"] == meta_asof
            assert f["listed"] == []


def test_non_ticker_rows_are_dropped_and_ranks_renumbered():
    snap = _frame(
        [
            ("CASH_USD", 3.00),
            ("NVDA", 14.21),
            ("", 2.00),
            ("GOOG", float("nan")),
            ("AAPL", 12.05),
            ("BRK.B", 1.20),
            ("BF-B", 0.90),
        ],
        day="2026-10-19",
        ranks=[1, 2, 3, 4, 5, 9, 12],  # stored ranks carry gaps after the drops
    )
    cov = coverage_for_fund("XLK", snap, asof=date(2026, 10, 20))
    listed = cov["listed"]
    assert [r["ticker"] for r in listed] == ["NVDA", "AAPL", "BRK.B", "BF-B"]
    assert [r["rank"] for r in listed] == [1, 2, 3, 4]  # renumbered 1..n, no gap
    assert cov["coverage"]["weight_pct"] == 28.36  # the dropped rows' weights are excluded
    assert cov["coverage"]["count"]["listed"] == 4
    assert all(r["ticker"] not in {"CASH_USD", "", "GOOG"} for r in listed)


def test_feed_contract_matches_the_terminal_reader():
    big_tickers = ["NVDA", "AAPL", "MSFT", "AVGO", "ORCL", "PLTR", "CSCO", "IBM",
                   "AMD", "CRM", "ACN", "INTC", "QCOM", "TXN", "INTU", "NOW",
                   "ADBE", "MU", "LRCX", "PANW"]
    big = _frame([(t, round(6.0 - i * 0.25, 2)) for i, t in enumerate(big_tickers)])
    two = _frame([("NVDA", 14.21), ("AAPL", 12.05)], day="2026-10-17")
    feed = build_holdings_coverage({"XLK": big, "XLF": two, "XLE": None},
                                   funds=["XLK", "XLF", "XLE"])
    _assert_contract(feed)
    by_fund = {f["fund"]: f for f in feed["funds"]}
    assert len(by_fund["XLK"]["listed"]) == 20
    assert by_fund["XLK"]["coverage"]["count"]["listed"] == 20
    assert by_fund["XLE"]["coverage"]["weight_pct"] == 0.0


def test_real_store_snapshot_round_trips_when_present():
    if not (STORE_DIR / "XLK.parquet").exists():
        pytest.skip("data/sector_holdings/XLK.parquet not present in this checkout")
    snap = load_snapshots(["XLK"])["XLK"]
    assert isinstance(snap, pd.DataFrame) and not snap.empty
    latest_iso = pd.to_datetime(snap.index).max().date().isoformat()
    cov = coverage_for_fund("XLK", snap, asof=date.today())
    assert cov["as_of"] == latest_iso
    assert 1 <= cov["coverage"]["count"]["listed"] <= 20
    assert cov["coverage"]["weight_pct"] > 0
    assert cov["n_holdings_total"] is None and cov["total_unknown"] is True


def test_emitter_is_additive_and_never_fatal(tmp_path):
    def _boom():
        raise RuntimeError("store exploded")

    assert emit_holdings_coverage_additive(tmp_path, snapshots_loader=_boom) is None
    assert list(tmp_path.iterdir()) == []  # nothing written on failure

    snap = _frame([("NVDA", 14.21), ("AAPL", 12.05), ("MSFT", 6.33)])
    out = emit_holdings_coverage_additive(tmp_path, snapshots_loader=lambda: {"XLK": snap})
    assert out == tmp_path / "sector_holdings_coverage.json"
    feed = json.loads(out.read_text(encoding="utf-8"))
    assert feed["meta"]["schema"] == SCHEMA
    assert [f["fund"] for f in feed["funds"]] == list(FUNDS)  # default FUNDS order
    assert len(next(f for f in feed["funds"] if f["fund"] == "XLK")["listed"]) == 3
    _assert_contract(feed)

    src = (ROOT / "scripts" / "build_sector_central.py").read_text(encoding="utf-8")
    hook = src.index("emit_holdings_coverage_additive(")
    pre = src[max(0, hook - 400):hook]
    assert "try:" in pre  # the call sits inside a try block
    assert "# Options R1 W2B" in pre
    assert 'log.warning("sector_central: holdings coverage feed skipped' in src[hook:]
    assert src.rindex("    return 0") > hook  # before main()'s FINAL return 0
    try:
        import jinja2  # noqa: F401
    except ImportError:
        return  # read-as-text above still ran; the module import needs jinja2
    import scripts.build_sector_central as sc
    assert callable(sc.main)
    assert callable(shc.emit_holdings_coverage_additive)


@pytest.mark.parametrize(
    ("weights", "emitted"),
    [
        ([101], 101.0),
        ([60, 50, 1], 111.0),
        ([33.335, 33.335, 33.33], 100.01),
    ],
    ids=["individual-overflow", "aggregate-overflow", "row-rounding-overflow"],
)
def test_invalid_weight_contract_preserves_existing_output(tmp_path, weights, emitted):
    snap = _frame([(f"T{i}", pct) for i, pct in enumerate(weights)])
    feed = build_holdings_coverage({"XLK": snap}, funds=["XLK"])
    assert feed["funds"][0]["coverage"]["weight_pct"] == emitted
    with pytest.raises(AssertionError):
        _assert_contract(feed)  # native reader contract rejects the produced feed

    out = tmp_path / "sector_holdings_coverage.json"
    sentinel = b"trusted-previous-feed\x00\xff"
    out.write_bytes(sentinel)
    with pytest.raises(ValueError, match="holdings coverage: XLK invalid"):
        shc.write_holdings_coverage(out, feed)
    assert out.read_bytes() == sentinel


@pytest.mark.parametrize("field", ["listed", "aggregate"])
def test_boolean_weight_contract_rejects_before_touching_output(tmp_path, field):
    feed = build_holdings_coverage(
        {"XLK": _frame([("NVDA", 1.0)])}, funds=["XLK"])
    fund = feed["funds"][0]
    if field == "listed":
        fund["listed"][0]["weight_pct"] = True
    else:
        fund["coverage"]["weight_pct"] = True
    with pytest.raises(AssertionError):
        _assert_contract(feed)  # Terminal rejects JSON true, not a number

    out = tmp_path / "sector_holdings_coverage.json"
    sentinel = b"trusted-previous-feed\x00\xff"
    out.write_bytes(sentinel)
    with pytest.raises(ValueError, match="holdings coverage: XLK invalid"):
        shc.write_holdings_coverage(out, feed)
    assert out.read_bytes() == sentinel

    absent = tmp_path / "absent-dir" / "sector_holdings_coverage.json"
    with pytest.raises(ValueError, match="holdings coverage: XLK invalid"):
        shc.write_holdings_coverage(absent, feed)
    assert not absent.exists()
    assert not absent.parent.exists()


def test_valid_exact_100_weight_feed_is_published(tmp_path):
    snap = _frame([("NVDA", 60), ("AAPL", 39), ("MSFT", 1)])
    feed = build_holdings_coverage({"XLK": snap}, funds=["XLK"])
    _assert_contract(feed)
    assert feed["funds"][0]["coverage"]["weight_pct"] == 100.0
    out = tmp_path / "exact-100.json"
    shc.write_holdings_coverage(out, feed)
    assert json.loads(out.read_text(encoding="utf-8")) == feed


@pytest.mark.parametrize("entry", ["additive-hook", "cli"])
def test_entry_paths_reject_invalid_feed_without_overwrite_and_recover(
        tmp_path, monkeypatch, caplog, entry):
    bad = _frame([("NVDA", 60), ("AAPL", 50), ("MSFT", 1)])
    good = _frame([("NVDA", 60), ("AAPL", 39), ("MSFT", 1)])
    out = (tmp_path / "sector_holdings_coverage.json" if entry == "additive-hook"
           else tmp_path / "explicit-cli-out.json")
    sentinel = b"trusted-original-\x00\xff"
    out.write_bytes(sentinel)
    caplog.set_level("WARNING")
    if entry == "additive-hook":
        assert emit_holdings_coverage_additive(
            tmp_path, snapshots_loader=lambda: {"XLK": bad}) is None
        assert "holdings coverage: feed skipped" in caplog.text
    else:
        monkeypatch.setattr(
            shc, "load_snapshots",
            lambda funds: {fund: (bad if fund == "XLK" else None) for fund in funds})
        assert main(["--out", str(out)]) == 1
        assert "holdings coverage: emit failed" in caplog.text
    assert out.read_bytes() == sentinel

    if entry == "additive-hook":
        assert emit_holdings_coverage_additive(
            tmp_path, snapshots_loader=lambda: {"XLK": good}) == out
    else:
        monkeypatch.setattr(
            shc, "load_snapshots",
            lambda funds: {fund: (good if fund == "XLK" else None) for fund in funds})
        assert main(["--out", str(out)]) == 0
    feed = json.loads(out.read_text(encoding="utf-8"))
    _assert_contract(feed)
    assert next(f for f in feed["funds"] if f["fund"] == "XLK")[
        "coverage"]["weight_pct"] == 100.0


def test_ci_manifest_declares_the_job():
    import yaml

    doc = yaml.safe_load(
        (ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8"))
    jobs = doc["jobs"]
    # This job requires its stable identity and declared gate/path/step,
    # not the first registry position.
    job = jobs["options-r1-sector-holdings-coverage"]
    assert job["gate"] == "code"
    paths = job["paths"]
    assert "scripts/build_sector_holdings_coverage.py" in paths
    assert "scripts/build_sector_central.py" in paths
    assert "tests/test_sector_holdings_coverage.py" in paths
    runs = [s.get("run", "") for s in job["steps"]]
    assert any("tests/test_sector_holdings_coverage.py" in r for r in runs)


def test_main_dry_run_writes_only_the_out_path(tmp_path, capsys, monkeypatch):
    out = tmp_path / "x.json"
    snap = _frame([("NVDA", 14.21), ("AAPL", 12.05), ("MSFT", 6.33)], day="2026-10-19")
    monkeypatch.setattr(shc, "load_snapshots",
                        lambda funds: {f: (snap if f == "XLK" else None) for f in funds})
    rc = main(["--out", str(out)])
    assert rc == 0
    assert out.exists()
    assert [p.name for p in tmp_path.iterdir()] == ["x.json"]  # only the --out path
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == len(FUNDS)  # one line per fund
    assert lines[FUNDS.index("XLK")] == ("XLK as_of=2026-10-19 listed=3 "
                                         "weight=32.59% top3=32.59% total=unknown")
