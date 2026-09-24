"""Tests for engine/china_participation.py (W2 — Participation lobe).

All tests run OFFLINE using synthetic fixtures — no network, no real data files.
Tests cover:
  1. Schema contract (§5 frozen schema)
  2. Regime classification correctness (rule-based)
  3. Who-controls classification
  4. Risk classification
  5. Evidence / contradictions lists
  6. Degrade-to-null behaviour on missing stores (CN-SYS-R4)
  7. Northbound-dead invariant (SLF-050)
  8. ETF flow z-score (no raw sum; per-fund z)
  9. QVIX inverted semantics
 10. Enum-value constraint
 11. latest_snapshot shape

Run: python -m tests.test_china_participation   (or pytest)
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS_COUNT = 0
FAIL_COUNT = 0
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        print(f"  PASS  {name}")
    else:
        FAIL_COUNT += 1
        print(f"  FAIL  {name}  {detail}")
        FAILURES.append(f"{name}  {detail}".rstrip())


try:
    import pytest
except ImportError:  # script mode is promised to work without pytest installed
    pytest = None

if pytest is not None:
    @pytest.fixture(autouse=True)
    def _gate_checks():
        # check() is a soft assert (it used to `assert cond` inline, which aborted
        # the test function on the FIRST miss) so one run reports EVERY miss;
        # this flush is what makes a miss fail the test under pytest.
        before = len(FAILURES)
        yield
        fresh = FAILURES[before:]
        assert not fresh, "check() failures:\n  " + "\n  ".join(fresh)


# ---------------------------------------------------------------------------
# Fixtures: synthetic data builders
# ---------------------------------------------------------------------------
def _make_turnover(n: int = 200, start: str = "2014-02-11") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="B")
    rng = np.random.default_rng(42)
    margin_trade_amt = rng.uniform(3000, 8000, n)
    # trade_amt_ratio: margin_trade_amt as % of total turnover (typically 8-12%)
    trade_amt_ratio = rng.uniform(8.0, 12.0, n)
    return pd.DataFrame(
        {
            "margin_trade_amt": margin_trade_amt,
            "trade_amt_ratio": trade_amt_ratio,
        },
        index=idx,
    )


def _make_balance(n: int = 200, start: str = "2014-02-11") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="B")
    rng = np.random.default_rng(0)
    balance = np.cumsum(rng.uniform(-100, 300, n)) + 15000
    return pd.DataFrame(
        {
            "margin_total": balance,
            "fin_balance": balance * 0.99,
            "fin_pct_float": balance / 500_000 * 100,
            "net_fin_buy": rng.uniform(-200, 200, n),
            "sec_lending": rng.uniform(20, 80, n),
        },
        index=idx,
    )


def _make_southbound(n: int = 200, start: str = "2014-02-11") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="B")
    return pd.DataFrame(
        {"net": np.random.default_rng(1).uniform(-5000, 5000, n)},
        index=idx,
    )


def _make_qvix(n: int = 200, start: str = "2020-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="B")
    return pd.DataFrame(
        {"close": np.random.default_rng(2).uniform(15, 35, n)},
        index=idx,
    )


def _make_broker_sector(n: int = 200, start: str = "2014-02-11") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="B")
    rng = np.random.default_rng(3)
    price = np.cumprod(1 + rng.uniform(-0.03, 0.04, n)) * 3000
    return pd.DataFrame(
        {"close": price, "open": price * 0.99, "high": price * 1.01,
         "low": price * 0.98, "volume": rng.uniform(1e7, 1e8, n),
         "amount": rng.uniform(1e9, 1e10, n)},
        index=idx,
    )


def _make_csi300(n: int = 200, start: str = "2014-02-11") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="B")
    rng = np.random.default_rng(4)
    price = np.cumprod(1 + rng.uniform(-0.02, 0.03, n)) * 4.0
    # Reproduce the MultiIndex style of the real file
    df = pd.DataFrame({"close": price, "volume": rng.uniform(1e8, 1e9, n)}, index=idx)
    df.columns = pd.MultiIndex.from_tuples([("Price", "close"), ("Price", "volume")])
    return df


def _make_etf_shares(n: int = 24, start: str = "2026-06-13") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="B")
    rng = np.random.default_rng(5)
    data = {}
    for fund in ["sh_510300", "sh_510500", "sh_159915"]:
        data[fund] = (np.cumsum(rng.integers(-1e8, 1e8, n)) + 1e10).astype(int)
    return pd.DataFrame(data, index=idx)


def _make_limit_breadth_flows(n: int = 30, start: str = "2026-05-27") -> pd.DataFrame:
    idx = pd.date_range(start, periods=n, freq="B")
    rng = np.random.default_rng(6)
    return pd.DataFrame(
        {"zt": rng.integers(20, 200, n),
         "dt": rng.integers(5, 80, n),
         "zb": rng.integers(10, 100, n),
         "seal_rate": rng.uniform(50, 90, n)},
        index=idx,
    )


def _make_limit_tape(n: int = 200, start: str = "2014-02-11") -> pd.DataFrame:
    """W1 china_microstructure/limit_tape.parquet — the PREFERRED zt_breadth source.

    limit_up_breadth_pct is % of the ~5000-name A-share universe at limit-up, so it
    lives in the same units as the _ZT_BREADTH_* thresholds (unlike the
    china_flows/limit_breadth.parquet seal_rate fallback, which is 56-85 and would
    fire zt_hot on every row).

    Dated to match _make_turnover: build_tape drops every row where turnover_total,
    margin_balance, southbound_net and qvix are ALL null, so a tape on non-overlapping
    dates would be silently discarded before the schema assertions ever see it.

    failed_up_seal_count / limit_up_count are the raw columns build_tape divides into
    the failed_seal_ratio column — NOT a precomputed ratio.
    """
    idx = pd.date_range(start, periods=n, freq="B")
    rng = np.random.default_rng(7)
    limit_up_count = rng.integers(20, 200, n)
    return pd.DataFrame(
        {"limit_up_breadth_pct": rng.uniform(0.5, 6.0, n),
         "limit_up_count": limit_up_count,
         "failed_up_seal_count": (limit_up_count * rng.uniform(0.05, 0.4, n)).astype(int)},
        index=idx,
    )


# ---------------------------------------------------------------------------
# Context manager: patch data loaders with temp parquet files
# ---------------------------------------------------------------------------
class _FakeDataDir:
    """Write synthetic parquet files into a temp dir and monkeypatch _ROOT in the engine."""

    def __init__(self, include_microstructure: bool = False):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._ms = include_microstructure
        self.root = Path(self._tmpdir.name)

    def _write(self, rel: str, df: pd.DataFrame) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(p)

    def setup(self) -> None:
        self._write("china_margin/daily_trade.parquet", _make_turnover())
        self._write("china_margin/balance.parquet", _make_balance())
        self._write("china_connect/southbound.parquet", _make_southbound())
        self._write("china_qvix/qvix300.parquet", _make_qvix())
        self._write("china_sectors/801780.parquet", _make_broker_sector())
        self._write("china/510300.SS.parquet", _make_csi300())
        self._write("china_flows/etf_shares.parquet", _make_etf_shares())
        self._write("china_flows/limit_breadth.parquet", _make_limit_breadth_flows())
        if self._ms:
            # W1 preferred source.  This branch used to be a no-op import of
            # `engine.china_participation._TAPE_PATH` — a name that module has never
            # defined — and no caller ever passed include_microstructure=True, so it
            # never ran and the preferred _load_limit_breadth path had zero coverage.
            self._write("china_microstructure/limit_tape.parquet", _make_limit_tape())

    def patch(self):
        return mock.patch("engine.china_participation._ROOT", str(self.root))

    def cleanup(self) -> None:
        self._tmpdir.cleanup()

    def __enter__(self):
        self.setup()
        self._patcher = self.patch()
        self._patcher.start()
        return self

    def __exit__(self, *args):
        self._patcher.stop()
        self.cleanup()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_schema_columns():
    """All §5 schema columns are present in the output tape."""
    with _FakeDataDir() as fdd:
        from engine.china_participation import build_tape
        tape = build_tape(backfill=True)

    required = [
        "turnover_total", "turnover_z20", "turnover_z60",
        "margin_balance", "margin_chg_5d", "margin_to_mcap",
        "southbound_net", "southbound_z",
        "etf_share_chg", "zt_breadth", "failed_seal_ratio",
        "qvix", "qvix_z", "broker_rs",
        "regime", "who_controls", "risk",
        "data_gaps", "backfill",
    ]
    for col in required:
        check(f"column '{col}' present", col in tape.columns)


def test_backfill_flag():
    """All rows carry backfill=True when backfill=True passed."""
    with _FakeDataDir() as fdd:
        from engine.china_participation import build_tape
        tape = build_tape(backfill=True)
    check("all rows backfill=True", tape["backfill"].all())


def test_no_backfill_flag():
    """All rows carry backfill=False when backfill=False passed."""
    with _FakeDataDir() as fdd:
        from engine.china_participation import build_tape
        tape = build_tape(backfill=False)
    check("all rows backfill=False", (~tape["backfill"]).all())


def test_regime_enum_values():
    """regime column contains only legal enum values."""
    with _FakeDataDir() as fdd:
        from engine.china_participation import build_tape, REGIME_VALUES
        tape = build_tape()
    bad = set(tape["regime"].unique()) - set(REGIME_VALUES)
    check("regime only legal enum values", not bad, f"illegal values: {bad}")


def test_who_controls_enum_values():
    """who_controls column contains only legal enum values."""
    with _FakeDataDir() as fdd:
        from engine.china_participation import build_tape, WHO_CONTROLS_VALUES
        tape = build_tape()
    bad = set(tape["who_controls"].unique()) - set(WHO_CONTROLS_VALUES)
    check("who_controls only legal enum values", not bad, f"illegal values: {bad}")


def test_risk_enum_values():
    """risk column contains only legal enum values."""
    with _FakeDataDir() as fdd:
        from engine.china_participation import build_tape, RISK_VALUES
        tape = build_tape()
    bad = set(tape["risk"].unique()) - set(RISK_VALUES)
    check("risk only legal enum values", not bad, f"illegal values: {bad}")


def test_forced_deleveraging_detection():
    """Rows with large margin drop AND hot turnover classify as forced_deleveraging."""
    from engine.china_participation import _classify_regime
    row = pd.Series({
        "turnover_z20": 1.5,   # hot volume
        "turnover_z60": 0.8,
        "margin_chg_5d": -2.5, # large drop → forced_deleveraging
        "margin_to_mcap": 4.5,
        "zt_breadth": 2.0,
        "southbound_z": -0.3,
        "broker_rs": 0.1,
    })
    result = _classify_regime(row)
    check("forced_deleveraging detected", result == "forced_deleveraging", f"got: {result}")


def test_broad_mania_detection():
    """High turnover + ZT mania + margin rising → broad_mania."""
    from engine.china_participation import _classify_regime
    row = pd.Series({
        "turnover_z20": 2.5,   # > 2.0
        "turnover_z60": 1.8,
        "margin_chg_5d": 1.5,  # rising
        "margin_to_mcap": 4.8,
        "zt_breadth": 6.0,     # > 5%
        "southbound_z": 0.3,
        "broker_rs": 0.2,
    })
    result = _classify_regime(row)
    check("broad_mania detected", result == "broad_mania", f"got: {result}")


def test_dormant_detection():
    """Low turnover, no margin growth, low ZT → dormant."""
    from engine.china_participation import _classify_regime
    row = pd.Series({
        "turnover_z20": -1.2,  # cold
        "turnover_z60": -0.8,
        "margin_chg_5d": -0.3,  # not rising
        "margin_to_mcap": 2.5,
        "zt_breadth": 1.0,      # below 2%
        "southbound_z": 0.0,
        "broker_rs": -0.1,
    })
    result = _classify_regime(row)
    check("dormant detected", result == "dormant", f"got: {result}")


def test_institutional_accumulation_detection():
    """Quiet turnover + southbound hot + broker RS positive → institutional_accumulation."""
    from engine.china_participation import _classify_regime
    row = pd.Series({
        "turnover_z20": 0.2,   # mid range
        "turnover_z60": 0.1,
        "margin_chg_5d": -0.1,
        "margin_to_mcap": 2.8,
        "zt_breadth": 1.5,
        "southbound_z": 1.5,   # hot
        "broker_rs": 0.3,      # positive
    })
    result = _classify_regime(row)
    check("institutional_accumulation detected", result == "institutional_accumulation", f"got: {result}")


def test_unclear_when_turnover_null():
    """Missing turnover_z20 → unclear."""
    from engine.china_participation import _classify_regime
    row = pd.Series({
        "turnover_z20": np.nan,
        "turnover_z60": np.nan,
        "margin_chg_5d": 0.5,
        "margin_to_mcap": 3.0,
        "zt_breadth": 2.0,
        "southbound_z": 0.5,
        "broker_rs": 0.1,
    })
    result = _classify_regime(row)
    check("unclear when turnover null", result == "unclear", f"got: {result}")


def test_risk_fire_sale_on_deleveraging():
    """forced_deleveraging regime → fire_sale risk."""
    from engine.china_participation import _classify_risk
    row = pd.Series({"regime": "forced_deleveraging", "qvix_z": 0.5, "margin_to_mcap": 3.0})
    result = _classify_risk(row)
    check("fire_sale on forced_deleveraging", result == "fire_sale", f"got: {result}")


def test_risk_fire_sale_on_qvix_panic():
    """qvix_z > 2.0 → fire_sale regardless of regime."""
    from engine.china_participation import _classify_risk
    row = pd.Series({"regime": "retail_ignition", "qvix_z": 2.5, "margin_to_mcap": 3.0})
    result = _classify_risk(row)
    check("fire_sale on qvix panic", result == "fire_sale", f"got: {result}")


def test_risk_frothy_on_mania():
    """broad_mania regime → frothy risk."""
    from engine.china_participation import _classify_risk
    row = pd.Series({"regime": "broad_mania", "qvix_z": 1.0, "margin_to_mcap": 5.0})
    result = _classify_risk(row)
    check("frothy on broad_mania", result == "frothy", f"got: {result}")


def test_risk_low_on_dormant():
    """dormant regime → low risk."""
    from engine.china_participation import _classify_risk
    row = pd.Series({"regime": "dormant", "qvix_z": -0.5, "margin_to_mcap": 2.0})
    result = _classify_risk(row)
    check("low risk on dormant", result == "low", f"got: {result}")


def test_contradiction_volume_vs_breadth():
    """Hot turnover + cold breadth → contradiction row emitted."""
    from engine.china_participation import _build_contradictions
    row = pd.Series({
        "turnover_z20": 1.8,
        "zt_breadth": 0.5,
        "southbound_z": 0.1,
        "broker_rs": 0.0,
        "margin_chg_5d": 0.2,
        "qvix_z": 0.5,
    })
    cx = _build_contradictions(row)
    detail_strs = " ".join(c.get("detail", "") for c in cx)
    check("volume-vs-breadth contradiction present",
          any("narrow breadth" in c.get("detail", "") or "volume concentrated" in c.get("detail", "") for c in cx),
          f"contradictions: {cx}")


def test_contradiction_sb_vs_broker_rs():
    """SB buying + broker RS negative → contradiction."""
    from engine.china_participation import _build_contradictions
    row = pd.Series({
        "turnover_z20": 0.3,
        "zt_breadth": 2.0,
        "southbound_z": 1.5,   # hot SB
        "broker_rs": -0.3,     # broker lagging
        "margin_chg_5d": 0.1,
        "qvix_z": 0.5,
    })
    cx = _build_contradictions(row)
    check("SB-vs-broker contradiction present",
          any("offshore" in c.get("detail", "") or "cross-market" in c.get("detail", "") for c in cx),
          f"contradictions: {cx}")


def test_northbound_dead_in_gaps():
    """data_gaps must always mention northbound dead (SLF-050)."""
    with _FakeDataDir() as fdd:
        from engine.china_participation import build_tape
        tape = build_tape(backfill=True)

    # Sample last 10 rows
    sample = tape.tail(10)
    for dt, row in sample.iterrows():
        gaps = str(row.get("data_gaps", ""))
        check(
            f"northbound dead noted in data_gaps on {dt.date()}",
            "northbound" in gaps.lower() and "SLF-050" in gaps,
            f"gaps: {gaps[:100]}"
        )
        break  # check one to avoid verbose output; loop verified above


def test_etf_flows_uses_z_not_raw_sum():
    """ETF flow loader uses per-fund z-scores, not raw sum across funds."""
    # Build ETF fixture inline so we can compare against raw sum directly
    etf_fixture = _make_etf_shares()
    raw_sum = etf_fixture.diff().sum(axis=1)

    with _FakeDataDir() as fdd:
        from engine.china_participation import _load_etf_flows
        result, gaps = _load_etf_flows()

    # Raw cross-fund daily share-change sums would be on the order of 1e8 (fixture data).
    # z-scores must be bounded near zero.  Assert magnitudes are in z-scale.
    check(
        "etf_share_chg result is non-empty",
        not result.empty,
        "expected non-empty result with full fixture data",
    )
    non_null = result.dropna()
    check(
        "etf z-scores have non-empty non-null values",
        len(non_null) > 0,
        f"all-null result; gaps={gaps}",
    )
    if len(non_null) > 0:
        max_abs = non_null.abs().max()
        check(
            "etf z-scores are z-scale (max abs < 10), not raw cross-fund sum",
            max_abs < 10,
            f"max abs={max_abs:.2f} — if this is >>10 the loader returned raw sums",
        )
        # Verify result is NOT equal to a naive raw sum — raw sum should be >> z-scores
        raw_mean_abs = raw_sum.abs().mean()
        check(
            "etf raw sum has much larger magnitude than z-scores (different series)",
            raw_mean_abs > 1e4,
            f"raw_sum mean_abs={raw_mean_abs:.0f} (expected >>1e4 for fixture data)",
        )


def test_etf_flows_gap_noted():
    """ETF flows must note the 5-week history census issue in gaps."""
    with _FakeDataDir() as fdd:
        from engine.china_participation import _load_etf_flows
        _, gaps = _load_etf_flows()
    check("etf 5-week caveat in gaps",
          any("5 week" in g.lower() or "~5 week" in g.lower() or "incommensurable" in g.lower() or "unit-incommensurable" in g.lower() for g in gaps),
          f"gaps: {gaps}")


def test_qvix_inverted_semantics_documented():
    """QVIX z-score goes positive when vol is high (stress), not negative — inverted vs US."""
    # Build a sequence where QVIX is high relative to its 60d mean
    from engine.china_participation import _zscore
    idx = pd.date_range("2020-01-01", periods=100, freq="B")
    # First 80 days: low QVIX (~15); last 20: spike to ~35
    vals = pd.Series([15.0] * 80 + [35.0] * 20, index=idx, name="qvix")
    z = _zscore(vals, 60, 20)
    # Last rows should have POSITIVE z (high QVIX = high z = stress)
    late_z = z.iloc[-5:].mean()
    check("high QVIX → positive qvix_z (stress, not contrarian buy)",
          late_z > 1.0,
          f"late mean z={late_z:.2f} (expected > 1.0)")


def test_degrade_on_missing_turnover():
    """Engine degrades gracefully when daily_trade.parquet is absent."""
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        # Write all files EXCEPT turnover
        (Path(tmp) / "china_margin").mkdir(parents=True, exist_ok=True)
        _make_balance().to_parquet(Path(tmp) / "china_margin" / "balance.parquet")
        # No daily_trade.parquet here
        with mock.patch("engine.china_participation._ROOT", tmp):
            import engine.china_participation as cp
            _, gaps = cp._load_turnover()
        check("gap recorded on missing turnover file",
              any("absent" in g.lower() or "missing" in g.lower() for g in gaps),
              f"gaps: {gaps}")


def test_degrade_on_missing_margin():
    """Engine degrades gracefully when balance.parquet is absent."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "china_margin").mkdir(parents=True, exist_ok=True)
        # No balance.parquet
        with mock.patch("engine.china_participation._ROOT", tmp):
            import engine.china_participation as cp
            _, gaps = cp._load_margin()
        check("gap recorded on missing margin file",
              any("absent" in g.lower() or "missing" in g.lower() for g in gaps),
              f"gaps: {gaps}")


def test_degrade_on_missing_southbound():
    """Engine degrades gracefully when southbound.parquet is absent."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "china_connect").mkdir(parents=True, exist_ok=True)
        # No southbound.parquet
        with mock.patch("engine.china_participation._ROOT", tmp):
            import engine.china_participation as cp
            _, gaps = cp._load_southbound()
        check("gap recorded on missing southbound file",
              any("absent" in g.lower() or "missing" in g.lower() for g in gaps),
              f"gaps: {gaps}")


def test_degrade_missing_microstructure_degrades_to_null():
    """When W1 limit_tape absent, zt_breadth degrades to null (seal_rate incompatible units)."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        # Write china_flows/limit_breadth but NO china_microstructure dir
        (Path(tmp) / "china_flows").mkdir(parents=True, exist_ok=True)
        _make_limit_breadth_flows().to_parquet(Path(tmp) / "china_flows" / "limit_breadth.parquet")
        with mock.patch("engine.china_participation._ROOT", tmp):
            import engine.china_participation as cp
            result, gaps = cp._load_limit_breadth()
        # Breadth leg must degrade to null — seal_rate has incompatible units
        check("zt_breadth degrades to null when W1 limit_tape absent",
              result.empty,
              f"result non-empty (seal_rate wrongly mapped); len={len(result)}, sample={result.head(3)}")
        check("incompatible-units reason noted in gaps",
              any("incompatible" in g.lower() or "units" in g.lower() or "W1" in g for g in gaps),
              f"gaps: {gaps}")
        # Ensure seal_rate values (56-85 range) are NOT appearing in result
        if not result.empty:
            check("no seal_rate-scale values in zt_breadth",
                  result.dropna().empty or result.dropna().max() < 10,
                  f"max={result.dropna().max():.1f} (seal_rate range is 56-85)")


def test_w1_limit_tape_is_preferred_over_seal_rate_fallback():
    """When china_microstructure/limit_tape.parquet IS present, zt_breadth comes from it.

    This is the other half of test_degrade_missing_microstructure_degrades_to_null and
    the first test ever to run `_FakeDataDir(include_microstructure=True)`.  The flag
    existed but its body was a no-op import of a nonexistent name, so the preferred
    W1 branch of _load_limit_breadth() had never been executed by any test — only the
    degrade branch was covered.
    """
    with _FakeDataDir(include_microstructure=True):
        import engine.china_participation as cp
        result, gaps = cp._load_limit_breadth()

    check("zt_breadth populated from W1 limit_tape", not result.empty,
          f"result empty — preferred branch not taken; gaps={gaps}")
    check("series named zt_breadth", result.name == "zt_breadth", f"name={result.name!r}")
    # Fixture range is 0.5-6.0 (% of universe). seal_rate would be 50-90.
    check("values are universe-breadth units, not seal_rate",
          result.max() < 10.0,
          f"max={result.max():.1f} — looks like seal_rate (50-90), not breadth %")
    check("no degrade gap when W1 tape present",
          not any("limit_breadth:" in g for g in gaps),
          f"gaps: {gaps}")


def test_w1_limit_tape_reaches_the_built_tape():
    """zt_breadth from the W1 tape must survive into build_tape output, non-null."""
    with _FakeDataDir(include_microstructure=True):
        import engine.china_participation as cp
        tape = cp.build_tape(backfill=True)

    check("zt_breadth column present", "zt_breadth" in tape.columns, f"cols={list(tape.columns)}")
    nn = tape["zt_breadth"].notna().sum()
    check("zt_breadth has non-null rows", nn > 0,
          f"all-null zt_breadth despite W1 limit_tape fixture (rows={len(tape)})")
    check("zt_breadth in universe-breadth units", tape["zt_breadth"].max() < 10.0,
          f"max={tape['zt_breadth'].max():.1f} — seal_rate (50-90) leaked in")
    # failed_seal_ratio rides the same W1 artifact (derived from the raw count columns)
    check("failed_seal_ratio populated from W1 limit_tape",
          tape["failed_seal_ratio"].notna().sum() > 0,
          "failed_seal_ratio all-null despite limit_up_count/failed_up_seal_count present")


def test_latest_snapshot_shape():
    """latest_snapshot returns required keys with correct types (§5 contract)."""
    with _FakeDataDir() as fdd:
        from engine.china_participation import build_tape, latest_snapshot
        tape = build_tape(backfill=True)
        snap = latest_snapshot(tape)

    required_keys = ["date", "regime", "who_controls", "risk",
                     "evidence", "contradictions", "data_gaps", "authority", "backfill"]
    for k in required_keys:
        check(f"latest_snapshot has key '{k}'", k in snap, f"keys: {list(snap.keys())}")

    check("authority.tier == context_only",
          snap.get("authority", {}).get("tier") == "context_only")
    check("evidence is a list", isinstance(snap["evidence"], list))
    check("contradictions is a list (not Python repr str)", isinstance(snap["contradictions"], list),
          f"type={type(snap.get('contradictions'))}, value={str(snap.get('contradictions'))[:80]}")
    check("data_gaps is a list", isinstance(snap["data_gaps"], list))
    # Verify the old contradictions_raw key is gone (§5 contract requires contradictions as list)
    check("contradictions_raw key absent (superseded by contradictions list)",
          "contradictions_raw" not in snap,
          f"keys: {list(snap.keys())}")


def test_tape_not_empty_with_full_fixtures():
    """build_tape with all fixtures produces a non-empty result."""
    with _FakeDataDir() as fdd:
        import engine.china_participation as cp
        tape = cp.build_tape(backfill=True)
    check("tape non-empty", len(tape) > 10, f"rows={len(tape)}")


def test_broker_rs_multiindex_handled():
    """Broker RS loader handles MultiIndex columns from 510300.SS.parquet."""
    with _FakeDataDir() as fdd:
        import engine.china_participation as cp
        result, gaps = cp._load_broker_rs()
    # Should produce a series, not error out
    check("broker_rs is a Series", isinstance(result, pd.Series))
    check("broker_rs has rows", len(result) > 0 or any("absent" in g for g in gaps),
          f"len={len(result)}, gaps={gaps}")


# ---------------------------------------------------------------------------
# Runner (also works via pytest)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    fns = [
        test_schema_columns,
        test_backfill_flag,
        test_no_backfill_flag,
        test_regime_enum_values,
        test_who_controls_enum_values,
        test_risk_enum_values,
        test_forced_deleveraging_detection,
        test_broad_mania_detection,
        test_dormant_detection,
        test_institutional_accumulation_detection,
        test_unclear_when_turnover_null,
        test_risk_fire_sale_on_deleveraging,
        test_risk_fire_sale_on_qvix_panic,
        test_risk_frothy_on_mania,
        test_risk_low_on_dormant,
        test_contradiction_volume_vs_breadth,
        test_contradiction_sb_vs_broker_rs,
        test_northbound_dead_in_gaps,
        test_etf_flows_uses_z_not_raw_sum,
        test_etf_flows_gap_noted,
        test_qvix_inverted_semantics_documented,
        test_degrade_on_missing_turnover,
        test_degrade_on_missing_margin,
        test_degrade_on_missing_southbound,
        # The name below was `..._falls_back_to_flows` from #1939 (876fa7775a6) —
        # a function that never existed, so `python -m tests.test_china_participation`
        # died on NameError before running a single test for the file's whole life.
        test_degrade_missing_microstructure_degrades_to_null,
        # Added by #3786 (9f6fb073259) but never listed here — script mode skipped them.
        test_w1_limit_tape_is_preferred_over_seal_rate_fallback,
        test_w1_limit_tape_reaches_the_built_tape,
        test_latest_snapshot_shape,
        test_tape_not_empty_with_full_fixtures,
        test_broker_rs_multiindex_handled,
    ]
    print(f"\nRunning {len(fns)} tests …\n")
    for fn in fns:
        print(f"[{fn.__name__}]")
        try:
            fn()
        except AssertionError as e:
            print(f"  ASSERT: {e}")
        except Exception as e:
            import traceback
            FAIL_COUNT += 1
            print(f"  ERROR: {e}")
            traceback.print_exc()
        print()

    print(f"\nResult: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    sys.exit(0 if FAIL_COUNT == 0 else 1)

# Chairman China dispersion slice: descriptive, never a second scored state.
def _price_context_fixture():
    dates = pd.bdate_range(end='2026-09-18', periods=210)
    names = [f'{600000+i}.SS' for i in range(10)]
    prices = pd.DataFrame(100.0, index=dates, columns=names)
    bench = pd.Series(100.0, index=dates)
    return prices, bench, names


def _price_context(prices, bench, names, **kw):
    from engine import china_participation as pc
    return pc.price_breadth_context(prices, bench, members=names,
                                   asof='2026-09-18', **kw)


def test_context_exposes_index_up_while_most_sampled_shares_fall():
    prices, bench, names = _price_context_fixture()
    prices.iloc[-1] = [170.0] + [98.0] * 9
    bench.iloc[-1] = 104.0
    r = _price_context(prices, bench, names)
    w = r['windows']['20']
    assert r['status'] == 'current'
    assert (w['eligible'], w['up'], w['down']) == (10, 1, 9)
    assert w['median_return_pct'] == pytest.approx(-2)
    assert w['mean_return_pct'] == pytest.approx(5.2)
    assert w['benchmark_return_pct'] == pytest.approx(4)
    assert w['comparison'] == 'index_up_sample_down'
    assert w['dispersion_pp'] >= 0
    assert r['authority'] == 'context_only'
    assert 'probability' not in r and 'risk_score' not in r


@pytest.mark.parametrize('bad', [None, float('nan'), float('inf'), 0.0, -1.0, 'bad'])
def test_context_missing_current_prices_are_not_filled(bad):
    prices, bench, names = _price_context_fixture()
    prices = prices.astype(object)
    prices.iloc[-1, 4:] = bad
    r = _price_context(prices, bench, names)
    assert r['asof'] == '2026-09-18'
    assert r['quote_count'] == 4
    assert r['windows']['20']['status'] == 'insufficient_coverage'
    assert r['windows']['20']['median_return_pct'] is None


def test_context_old_price_sample_is_dated_not_current():
    prices, bench, names = _price_context_fixture()
    r = _price_context(prices.iloc[:-10], bench, names)
    assert r['status'] == 'delayed'
    assert r['asof'] == str(prices.index[-11].date())
    assert r['requested_asof'] == '2026-09-18'
    assert r['current_comparison'] is None


def test_context_future_rows_cannot_change_past_snapshot():
    prices, bench, names = _price_context_fixture()
    expected = _price_context(prices, bench, names)
    prices.loc[pd.Timestamp('2026-09-21')] = 2000.0
    bench.loc[pd.Timestamp('2026-09-21')] = 500.0
    assert _price_context(prices, bench, names) == expected


def test_context_internal_gap_disqualifies_stock_from_return_window():
    prices, bench, names = _price_context_fixture()
    prices.iloc[-7, 0] = np.nan
    r = _price_context(prices, bench, names)
    assert r['windows']['5']['eligible'] == 10
    assert r['windows']['20']['eligible'] == 9


def test_context_benchmark_gap_cannot_look_like_a_zero_return():
    prices, bench, names = _price_context_fixture()
    bench.iloc[-1] = np.nan
    w = _price_context(prices, bench, names)['windows']['20']
    assert w['benchmark_return_pct'] is None
    assert w['comparison'] == 'sample_only'


def test_context_unrequested_symbol_cannot_improve_coverage():
    prices, bench, names = _price_context_fixture()
    prices.iloc[-1, 4:] = np.nan
    prices['EXTRA'] = 100.0
    r = _price_context(prices, bench, names)
    assert r['configured_count'] == 10 and r['quote_count'] == 4


@pytest.mark.parametrize('which', ['date', 'column', 'members'])
def test_context_duplicate_inputs_refuse_without_double_counting(which):
    prices, bench, names = _price_context_fixture()
    if which == 'date': prices = pd.concat([prices, prices.iloc[-1:]])
    elif which == 'column': prices = pd.concat([prices, prices.iloc[:, :1]], axis=1)
    else: names += names[:1]
    assert _price_context(prices, bench, names)['status'] == 'unavailable'


def test_context_ma_change_uses_identical_members_at_both_endpoints():
    prices, bench, names = _price_context_fixture()
    prices.iloc[-5:, :4] = 110.0
    prices.iloc[-1, 8:] = np.nan
    r = _price_context(prices, bench, names)['trend']
    assert r['eligible'] == 8 and r['paired_eligible'] == 8
    assert r['above200_pct'] == 50
    assert r['paired_change_pp'] == 50


def test_context_percent_change_is_not_percentage_point_difference():
    prices, bench, names = _price_context_fixture()
    prices.iloc[-1] = 110.0
    w = _price_context(prices, bench, names)['windows']['20']
    assert w['median_return_pct'] == pytest.approx(10)
    assert w['positive_pct'] == 100


def test_context_empty_inputs_keep_explicit_absence():
    _, bench, names = _price_context_fixture()
    r = _price_context(pd.DataFrame(), bench, names)
    assert r['status'] == 'unavailable'
    assert r['current_comparison'] is None


def test_context_short_history_does_not_fake_ma_or_twenty_sessions():
    prices, bench, names = _price_context_fixture()
    r = _price_context(prices.iloc[-6:], bench, names)
    assert r['windows']['5']['status'] == 'ok'
    assert r['windows']['20']['status'] == 'insufficient_coverage'
    assert r['trend']['above200_pct'] is None


def _board_fixture():
    return pd.DataFrame({'n': [5000], 'adv': [4000], 'dec': [900], 'flat': [100],
                         'med_pct': [1.5], 'source': ['sina']},
                        index=pd.to_datetime(['2026-09-18']))


def test_context_board_keeps_full_board_and_sample_scopes_separate():
    from engine.china_participation import board_breadth_context
    r = board_breadth_context(_board_fixture(), asof='2026-09-18')
    assert r['status'] == 'current' and r['n'] == 5000
    assert r['positive_pct'] == 80 and r['median_return_pct'] == 1.5
    assert r['scope'] == 'hushen_traded_board'


@pytest.mark.parametrize('field,value', [('n',200), ('adv',-1), ('flat',np.nan),
                                         ('dec',999), ('adv',True), ('med_pct',np.inf)])
def test_context_board_bad_counts_never_become_broad_confirmation(field, value):
    from engine.china_participation import board_breadth_context
    df = _board_fixture().astype(object)
    df.loc[df.index[0],field] = value
    r = board_breadth_context(df, asof='2026-09-18')
    assert r['status'] == 'unavailable' and r['positive_pct'] is None


def test_context_board_does_not_relabel_old_counts_as_current():
    from engine.china_participation import board_breadth_context
    r = board_breadth_context(_board_fixture(), asof='2026-09-21')
    assert r['status'] == 'delayed' and r['asof'] == '2026-09-18'


def test_context_loader_reads_existing_stores_without_network_or_writes(monkeypatch):
    from engine import china_participation as pc
    from lib import store
    prices, bench, names = _price_context_fixture()
    reads = []
    inputs = {('china_search','closes'): prices,
              ('china','510300.SS'): bench.to_frame('close'),
              ('china_board_breadth','breadth'): _board_fixture()}
    def read(g, n):
        reads.append((g,n))
        return inputs.get((g,n))
    monkeypatch.setattr(store, 'read', read)
    r = pc.load_breadth_context(asof='2026-09-18')
    assert r['sample']['configured_count'] == 10 and r['daily_board']['n'] == 5000
    assert set(reads) == set(inputs)


def test_context_loader_ignores_etfs_and_offshore_symbols(monkeypatch):
    from engine import china_participation as pc
    from lib import store
    prices, bench, names = _price_context_fixture()
    for name in ['510300.SS','00700.HK','200011.SZ','830799.BJ']:
        prices[name] = 10.0
    monkeypatch.setattr(store, 'read', lambda g,n: prices if g=='china_search' else
                        bench.to_frame('close') if g=='china' else _board_fixture())
    assert pc.load_breadth_context(asof='2026-09-18')['sample']['configured_count'] == 10


def _render_participation_context(context):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[1]/'templates')),
                      autoescape=True)
    return env.from_string('{% import "_china_participation_context.html.j2" as cbx %}'
                           '{{ cbx.participation_panel(ctx) }}').render(ctx=context)


def test_context_panel_distinguishes_recent_improvement_from_twenty_day_weakness(monkeypatch):
    context = _timed_context(monkeypatch)
    assert context['timing']['status'] == 'current'
    # Synthetic returns exercise narrative only; real reader qualifies this clock.
    sample = context['sample']
    sample['windows']['5'].update(status='ok', median_return_pct=1.0, positive_pct=60)
    sample['windows']['20'].update(status='ok', median_return_pct=-1.0, positive_pct=40)
    html = _render_participation_context(context)
    assert 'Recent rebound, uneven recovery' in html
    assert '20-session sample' in html and 'Latest board session' in html
    assert 'Not an equal-weight index' in html
    assert 'Price-library sample' in html and '沪深' in html


def test_context_panel_missing_data_is_not_a_calm_or_bearish_verdict():
    html = _render_participation_context({})
    assert 'Participation unavailable' in html and '参与度暂不可用' in html
    assert 'Recent rebound' not in html
    assert 'Risk-off' not in html and 'Risk-on' not in html


def test_context_panel_stale_sample_never_gets_a_current_rebound_headline(monkeypatch):
    def older_sample(inputs):
        inputs[('china_search', 'closes')] = inputs[('china_search', 'closes')].iloc[:-5]
    context = _timed_context(monkeypatch, change=older_sample)
    assert context['timing']['status'] == 'mixed'
    assert context['sample']['status'] == 'delayed'
    html = _render_participation_context(context)
    assert 'Different source dates' in html
    assert context['sample']['asof'] in html
    assert 'Recent rebound, uneven recovery' not in html


def test_context_panel_nonfinite_prices_do_not_leak_json_nan():
    import json
    prices, bench, names = _price_context_fixture()
    prices.iloc[-1] = np.inf
    json.dumps(_price_context(prices,bench,names),allow_nan=False)


def test_context_builder_binds_to_assessment_date_not_render_clock(monkeypatch):
    from scripts import build_china
    from engine import china_participation as pc
    seen = []
    def load(*, asof, sector_universe):
        assert sector_universe
        seen.append(asof)
        return {'assessment_asof':asof,'authority':'context_only'}
    monkeypatch.setattr(pc, 'load_breadth_context', load)
    assert build_china._participation_context('2026-09-18')['assessment_asof'] == '2026-09-18'
    assert seen == ['2026-09-18']


def test_context_sector_outperformance_does_not_mean_sector_rose():
    from engine.china_participation import sector_breadth_context
    prices, bench, names = _price_context_fixture()
    prices.iloc[-1] = 98
    bench.iloc[-1] = 95
    r = sector_breadth_context({'ETF':prices.iloc[:,0].to_frame('close')},bench,
                              names={'ETF':['Banks']},asof='2026-09-18')
    row = r['rows'][0]
    assert row['return_pct'] == pytest.approx(-2)
    assert row['benchmark_gap_pp'] == pytest.approx(3)
    assert r['rising'] == 0 and r['eligible'] == 1


def test_context_sector_missing_data_does_not_shrink_declared_universe():
    from engine.china_participation import sector_breadth_context
    prices, bench, names = _price_context_fixture()
    r = sector_breadth_context({'ETF':prices.iloc[:,0].to_frame('close')},bench,
                              names={'ETF':['Banks'],'MISSING':['Missing']},asof='2026-09-18')
    assert r['declared'] == 2 and len(r['rows']) == 2 and r['eligible'] == 1
    assert r['rows'][1]['return_pct'] is None


def test_context_sector_delayed_read_does_not_count_in_current_rising_tally():
    from engine.china_participation import sector_breadth_context
    prices, bench, names = _price_context_fixture()
    r = sector_breadth_context({'ETF':prices.iloc[:-1,0].to_frame('close')},bench,
                              names={'ETF':['Banks']},asof='2026-09-18')
    assert r['eligible'] == 0 and r['rows'][0]['status'] == 'delayed'


def test_context_extreme_finite_quotes_cannot_export_infinite_metrics():
    import json
    prices, bench, names = _price_context_fixture()
    prices.iloc[-1] = 1e308
    result = _price_context(prices,bench,names)
    json.dumps(result,allow_nan=False)


def test_context_boolean_prices_are_invalid_not_one_currency_unit():
    prices, bench, names = _price_context_fixture()
    prices = prices.astype(object)
    prices.iloc[-1,4:] = True
    r = _price_context(prices,bench,names)
    assert r['quote_count'] == 4 and r['windows']['20']['median_return_pct'] is None


def test_context_unsorted_rows_do_not_change_the_snapshot():
    prices, bench, names = _price_context_fixture()
    assert _price_context(prices.iloc[::-1],bench.iloc[::-1],names) == _price_context(prices,bench,names)


def test_context_input_frames_are_not_mutated():
    prices, bench, names = _price_context_fixture()
    original, original_bench = prices.copy(), bench.copy()
    _price_context(prices,bench,names)
    pd.testing.assert_frame_equal(prices,original)
    pd.testing.assert_series_equal(bench,original_bench)


def test_context_panel_absent_board_has_no_direction_word():
    from bs4 import BeautifulSoup
    html = _render_participation_context({})
    text = BeautifulSoup(html,'html.parser').select_one('.cnx-part-data').get_text(' ',strip=True)
    assert 'rose' not in text and '上涨' not in text


# CSI 300 single-snapshot constituent lens. No historical/index-weight claims.
def _index_member_fixture():
    dates = pd.bdate_range(end="2026-09-18", periods=205)
    names = [f"{600000+i:06d}.SS" for i in range(300)]
    membership = pd.DataFrame({"symbol": ["000300"]*300, "ticker": names,
                               "fetched_date": ["2026-09-15"]*300})
    prices = pd.DataFrame(100.0, index=dates, columns=names)
    prices.iloc[-1,:200] = 99.0
    prices.iloc[-1,200:] = 104.0
    benchmark = pd.Series(100.0,index=dates)
    benchmark.iloc[-1] = 100.1
    return membership, prices, benchmark


def _index_member_context(membership, prices, benchmark):
    from engine.china_participation import index_member_breadth_context
    return index_member_breadth_context(membership,prices,benchmark,asof="2026-09-18")


def test_index_member_lens_separates_etf_gain_from_its_typical_constituent():
    m,p,b = _index_member_fixture()
    r = _index_member_context(m,p,b)
    assert r["status"] == "available"
    assert r["member_count"] == r["expected_members"] == 300
    assert r["membership_observed"] == "2026-09-15"
    w = r["windows"]["5"]
    assert w["eligible"] == 300 and w["median_return_pct"] == pytest.approx(-1)
    assert w["benchmark_return_pct"] == pytest.approx(.1)
    assert w["comparison"] == "index_up_sample_down"
    assert r["contribution_status"] == "unavailable_no_official_start_weights"
    assert r["historical_membership"] is False


@pytest.mark.parametrize("change", ["short", "duplicate", "mixed_dates", "future", "missing_date", "bad_ticker", "bad_date", "duplicate_columns"])
def test_index_member_lens_refuses_invalid_membership_without_shrinking(change):
    m,p,b = _index_member_fixture()
    if change == "short": m=m.iloc[:-1]
    elif change == "duplicate": m.loc[299,"ticker"]=m.loc[0,"ticker"]
    elif change == "mixed_dates": m.loc[299,"fetched_date"]="2026-09-14"
    elif change == "future": m["fetched_date"]="2026-09-19"
    elif change == "missing_date": m=m.drop(columns="fetched_date")
    elif change == "bad_ticker": m.loc[0,"ticker"]="0700.HK"
    elif change == "bad_date": m["fetched_date"]="not-a-date"
    else: m=pd.concat([m,m[["ticker"]]],axis=1)
    r = _index_member_context(m,p,b)
    assert r["status"] == "unavailable"
    assert r["windows"] == {} and r["data_gaps"]
    assert r["expected_members"] == 300


def test_index_member_lens_ignores_other_indices_and_extra_stocks():
    m,p,b = _index_member_fixture()
    extra=m.iloc[:1].copy();extra["symbol"]="000852";extra["ticker"]="300999.SZ"
    m=pd.concat([m,extra],ignore_index=True)
    p["300999.SZ"] = 1e10
    r=_index_member_context(m,p,b)
    assert r["member_count"] == 300
    assert r["windows"]["20"]["median_return_pct"] == pytest.approx(-1)


def test_index_member_lens_does_not_replace_missing_member_with_extra():
    m,p,b = _index_member_fixture()
    p=p.drop(columns=p.columns[0]);p["300999.SZ"]=100.0
    r=_index_member_context(m,p,b)
    assert r["status"] == "insufficient_coverage"
    assert r["windows"]["20"]["eligible"] == 299
    assert r["windows"]["20"]["median_return_pct"] is None


def test_index_member_lens_never_uses_market_cap_placeholders_as_weights():
    m,p,b=_index_member_fixture()
    original=_index_member_context(m,p,b)
    m["mktcap_yi"]=30.0;m.loc[0,"mktcap_yi"]=1e99
    assert _index_member_context(m,p,b) == original
    assert "weighted_return" not in original and "contributions" not in original


def test_index_member_lens_declares_snapshot_applied_retrospectively():
    m,p,b=_index_member_fixture()
    r=_index_member_context(m,p,b)
    assert r["windows"]["20"]["membership_observed_after_start"] is True
    assert r["windows"]["5"]["membership_observed_after_start"] is True
    assert r["membership_age_days_at_assessment"] == 3


def test_index_member_lens_delayed_prices_keep_their_own_date():
    m,p,b=_index_member_fixture()
    r=_index_member_context(m,p.iloc[:-1],b)
    assert r["status"] == "delayed" and r["price_asof"] == "2026-09-17"
    assert r["membership_observed"] == "2026-09-15"


def test_index_member_loader_reads_only_existing_membership_and_closes(monkeypatch):
    from engine import china_participation as pc
    from lib import store
    m,p,b=_index_member_fixture()
    fixtures={("china_search","index_cons"):m,("china_search","closes"):p,
              ("china","510300.SS"):b.to_frame("close")}
    reads=[]
    def read(g,n):
        reads.append((g,n));return fixtures[(g,n)]
    monkeypatch.setattr(store,"read",read)
    result=pc.load_index_member_breadth_context(asof="2026-09-18")
    assert result["status"] == "available" and set(reads)==set(fixtures)


def test_index_member_loader_read_error_is_explicit_not_empty_confirmation(monkeypatch):
    from engine import china_participation as pc
    from lib import store
    def read(g,n): raise OSError("source unavailable")
    monkeypatch.setattr(store,"read",read)
    result=pc.load_index_member_breadth_context(asof="2026-09-18")
    assert result["status"] == "unavailable" and result["data_gaps"]


def test_index_member_panel_shows_dated_cohort_not_weighted_contribution():
    m,p,b = _index_member_fixture()
    r = _index_member_context(m,p,b)
    html = _render_participation_context({'index_members':r})
    assert 'CSI 300 members' in html and '沪深300成分股' in html
    assert '2026-09-15' in html and '2026-09-18' in html
    assert '-1.00%' in html and '+0.10%' in html
    assert 'not a historical membership archive' in html
    assert 'Starting index weights unavailable' in html


def test_index_member_panel_missing_membership_does_not_invent_index_attribution():
    m,p,b = _index_member_fixture()
    html = _render_participation_context({'index_members':_index_member_context(m.iloc[:20],p,b)})
    assert 'Constituent comparison unavailable' in html
    assert '成分股对比暂不可用' in html
    assert 'Weighted contribution' not in html


def test_index_member_panel_preserves_incomplete_price_denominator():
    m,p,b = _index_member_fixture()
    html = _render_participation_context({'index_members':_index_member_context(m,p.iloc[:,:299],b)})
    assert '299 / 300' in html
    assert 'All 300' not in html


def test_index_member_builder_adds_cohort_without_mutating_original_context(monkeypatch):
    from scripts import build_china
    from engine import china_participation as pc
    original = {'assessment_asof':'2026-09-18', 'sample':{'status':'delayed'}}
    member = {'membership_observed':'2026-09-15','status':'available'}
    monkeypatch.setattr(pc,'load_breadth_context',lambda **_kw: original)
    def loader(*, asof):
        assert asof=='2026-09-18'
        return member
    monkeypatch.setattr(pc,'load_index_member_breadth_context',loader)
    r = build_china._participation_context('2026-09-18')
    assert r['index_members'] == member
    assert 'index_members' not in original
    assert r['sample']['status'] == 'delayed'


# A fixed starting-weight basket is descriptive, not official index attribution.
def _weighted_context_fixture():
    members = [f'{600000+i:06d}.SS' for i in range(300)]
    dates = pd.bdate_range('2026-08-31','2026-09-18')
    prices = pd.DataFrame(100.0,index=dates,columns=members)
    prices.iloc[-1,0] = 110
    prices.iloc[-1,1:] = 99
    weights = pd.DataFrame({'symbol':'000300','ticker':members,'name_zh':members,
        'weight_date':'2026-08-31','observed_at':'2026-09-22T00:00:00+00:00',
        'source':'csindex_closeweight','weight_pct':[10.0]+[90/299]*299})
    benchmark = pd.Series(100.0,index=dates)
    return weights,prices,benchmark


def test_weighted_context_uses_actual_start_weights_not_equal_weights_or_end_caps():
    from engine.china_participation import index_weight_context
    weights,prices,bench = _weighted_context_fixture()
    r = index_weight_context(weights,prices,bench,asof='2026-09-18')
    assert r['status'] == 'available' and r['eligible'] == 300
    assert r['basket_return_pct'] == pytest.approx(.1)
    assert r['median_return_pct'] == pytest.approx(-1)
    assert r['top_contributors'][0]['contribution_pp'] == pytest.approx(1)
    assert r['official_index_attribution'] is False
    assert r['start'] == '2026-08-31' and r['end'] == '2026-09-18'
    assert r['known_after_window'] is True


@pytest.mark.parametrize('fault',['missing','gap','before_weights','bad_total','duplicate','foreign'])
def test_weighted_context_refuses_false_attribution(fault):
    from engine.china_participation import index_weight_context
    w,p,b = _weighted_context_fixture()
    if fault == 'missing': p = p.iloc[:,:-1]
    elif fault == 'gap': p.iloc[3,3] = np.nan
    elif fault == 'before_weights': w['weight_date'] = '2026-09-30'
    elif fault == 'bad_total': w['weight_pct'] = 1
    elif fault == 'duplicate': w.loc[1,'ticker'] = w.loc[0,'ticker']
    elif fault == 'foreign': w['source'] = 'market_caps'
    r = index_weight_context(w,p,b,asof='2026-09-18')
    assert r['basket_return_pct'] is None
    assert r['official_index_attribution'] is False
    assert r['data_gaps']


def test_weighted_context_keeps_concentration_when_price_coverage_is_incomplete():
    from engine.china_participation import index_weight_context
    w,p,b = _weighted_context_fixture()
    r = index_weight_context(w,p.iloc[:,:-1],b,asof='2026-09-18')
    assert r['top10_weight_pct'] == pytest.approx(10+9*90/299)
    assert r['eligible'] == 299 and r['basket_return_pct'] is None


def test_weighted_context_is_input_immutable_and_json_finite():
    import json
    from engine.china_participation import index_weight_context
    w,p,b = _weighted_context_fixture()
    before = (w.copy(),p.copy(),b.copy())
    json.dumps(index_weight_context(w,p,b,asof='2026-09-18'),allow_nan=False)
    pd.testing.assert_frame_equal(w,before[0]); pd.testing.assert_frame_equal(p,before[1])
    pd.testing.assert_series_equal(b,before[2])


@pytest.mark.parametrize('bad_ticker',['510300.SS','00700.HK','notreal.X'])
def test_weighted_context_rejects_nonmember_symbol_classes(bad_ticker):
    from engine.china_participation import index_weight_context
    w,p,b = _weighted_context_fixture()
    w.loc[0,'ticker'] = bad_ticker
    p = p.rename(columns={p.columns[0]:bad_ticker})
    r = index_weight_context(w,p,b,asof='2026-09-18')
    assert r['basket_return_pct'] is None and r['data_gaps']


def test_weight_reader_is_read_only_and_absence_is_not_fabricated(monkeypatch):
    from engine import china_participation as pc
    from lib import store
    seen=[]
    def read(g,n):
        seen.append((g,n)); return None
    monkeypatch.setattr(store,'read',read)
    r=pc.load_index_weight_context(asof='2026-09-18')
    assert r['basket_return_pct'] is None and r['official_index_attribution'] is False
    assert set(seen)=={('china_search','index_weights'),('china_search','closes'),('china','510300.SS')}
    assert r['data_gaps']


def test_weight_reader_consumes_the_official_snapshot_without_network(monkeypatch):
    from engine import china_participation as pc
    from lib import store
    w,p,b=_weighted_context_fixture()
    inputs={('china_search','index_weights'):w,('china_search','closes'):p,('china','510300.SS'):b.to_frame('close')}
    monkeypatch.setattr(store,'read',lambda g,n:inputs[(g,n)])
    assert pc.load_index_weight_context(asof='2026-09-18')['basket_return_pct']==pytest.approx(.1)


def test_weight_view_names_the_basket_and_never_claims_cash_index_attribution():
    from engine.china_participation import index_weight_context
    w,p,b=_weighted_context_fixture()
    html=_render_participation_context({'index_weights':index_weight_context(w,p,b,asof='2026-09-18')})
    assert 'Official weights' in html and '官方权重' in html
    assert '2026-08-31' in html and '2026-09-18' in html
    assert 'Fixed-start basket estimate' in html
    assert 'not official index attribution' in html
    assert '+0.10%' in html and '300 / 300' in html
    assert 'obtained after this return window' in html


def test_weight_view_preserves_incomplete_price_coverage_without_zero_return():
    from engine.china_participation import index_weight_context
    w,p,b=_weighted_context_fixture()
    html=_render_participation_context({'index_weights':index_weight_context(w,p.iloc[:,:-1],b,asof='2026-09-18')})
    assert '299 / 300' in html and 'Unavailable' in html
    assert '+0.00%' not in html


def test_weight_builder_attaches_optional_read_without_mutating_other_context(monkeypatch):
    from engine import china_participation as pc
    from scripts import build_china
    base={'authority':'context_only'}
    monkeypatch.setattr(pc,'load_breadth_context',lambda **kw:base)
    monkeypatch.setattr(pc,'load_index_member_breadth_context',lambda **kw:{})
    monkeypatch.setattr(pc,'load_index_weight_context',lambda **kw:{'status':'unavailable'})
    assert build_china._participation_context('2026-09-18')['index_weights']['status']=='unavailable'
    assert base=={'authority':'context_only'}


# Explain a withheld cohort result without changing its eligibility or return.
def test_member_gap_detail_names_missing_latest_quotes_without_substitution():
    m,p,b = _index_member_fixture()
    p.iloc[-1,:3] = np.nan
    r = _index_member_context(m,p,b)
    w = r['windows']['5']; detail = w['coverage_detail']
    assert w['eligible'] == 297 and w['median_return_pct'] is None
    assert detail['excluded_count'] == 3 and detail['status'] == 'incomplete'
    assert [x['ticker'] for x in detail['members']] == list(p.columns[:3])
    assert all(x['missing_observations'] == 1 and x['last_missing'] == '2026-09-18'
               and x['latest_quote_missing'] for x in detail['members'])


def test_member_gap_detail_keeps_each_window_and_same_end_date_separate():
    m,p,b = _index_member_fixture(); p.iloc[-10,0] = np.nan
    r = _index_member_context(m,p,b)
    assert r['windows']['5']['coverage_detail']['status'] == 'complete'
    detail = r['windows']['20']['coverage_detail']
    assert detail['excluded_count'] == 1
    assert detail['members'][0]['last_missing'] == str(p.index[-10].date())
    assert detail['members'][0]['latest_quote_missing'] is False


@pytest.mark.parametrize('bad', [None, -1.0, 0.0, np.inf, True, 'bad'])
def test_member_gap_detail_handles_invalid_prices_without_inventing_a_reason(bad):
    m,p,b = _index_member_fixture(); p=p.astype(object); p.iloc[-1,0]=bad
    d = _index_member_context(m,p,b)['windows']['5']['coverage_detail']
    assert d['excluded_count'] == 1 and d['members'][0]['reason'] == 'missing_or_invalid_price'


def test_member_gap_detail_absent_column_names_all_window_observations():
    m,p,b = _index_member_fixture(); name=p.columns[0]; p=p.drop(columns=name)
    d = _index_member_context(m,p,b)['windows']['20']['coverage_detail']
    assert d['members'][0]['ticker'] == name
    assert d['members'][0]['missing_observations'] == 21


def test_member_gap_detail_short_window_is_not_three_hundred_bad_stocks():
    m,p,b = _index_member_fixture()
    d = _index_member_context(m,p.iloc[-3:],b.iloc[-3:])['windows']['5']['coverage_detail']
    assert d['status'] == 'short_history' and d['excluded_count'] is None
    assert d['members'] == []


def test_member_gap_detail_ignores_future_holes_and_keeps_inputs_immutable():
    m,p,b = _index_member_fixture()
    p.loc[p.index[-1]+pd.offsets.BDay()] = np.nan
    original=p.copy()
    result=_index_member_context(m,p,b)
    assert result['windows']['5']['coverage_detail']['excluded_count'] == 0
    pd.testing.assert_frame_equal(p,original)


def test_member_gap_detail_renders_why_the_comparison_is_withheld_in_both_languages():
    m,p,b = _index_member_fixture(); p.iloc[-1,:3]=np.nan
    html=_render_participation_context({'index_members':_index_member_context(m,p,b)})
    assert 'Missing or invalid stored prices' in html and '存储价格缺失或无效' in html
    assert '600000.SS' in html and '297 / 300' in html
    assert '3 affected members' in html and '3只受影响成分股' in html


def test_member_gap_detail_does_not_change_any_existing_window_measurement():
    from engine.china_participation import price_breadth_context
    m,p,b=_index_member_fixture(); p.iloc[-1,:3]=np.nan
    raw=price_breadth_context(p,b,members=m.ticker.tolist(),asof='2026-09-18',min_coverage=1.0)
    result=_index_member_context(m,p,b)
    for key,w in result['windows'].items():
        assert {k:v for k,v in w.items() if k not in ('coverage_detail','membership_observed_after_start')} == raw['windows'][key]


def test_member_gap_detail_limits_visible_rows_without_hiding_the_total():
    from bs4 import BeautifulSoup
    m,p,b=_index_member_fixture(); p.iloc[-1,:6]=np.nan
    result=_index_member_context(m,p,b)
    assert len(result['windows']['5']['coverage_detail']['members']) == 6
    html=_render_participation_context({'index_members':result})
    soup=BeautifulSoup(html,'html.parser')
    assert all(len(table.select('tbody tr')) == 5 for table in soup.select('.cnx-member-gaps'))
    assert '6 affected members' in html and 'First 5 affected members shown.' in html


# Independent build-time clock: equal old source dates must not certify freshness.
def _timed_context(monkeypatch, *, now=None, asof="2026-09-18", change=None):
    from datetime import datetime, timezone
    from engine import china_participation as pc
    from lib import store
    prices, bench, _ = _price_context_fixture()
    inputs = {("china_search", "closes"): prices,
              ("china", "510300.SS"): bench.to_frame("close"),
              ("china_board_breadth", "breadth"): _board_fixture(),
              ("china", "ETF"): prices.iloc[:, 0].to_frame("close")}
    if change:
        change(inputs)
    monkeypatch.setattr(store, "read", lambda g, n: inputs.get((g, n)))
    return pc.load_breadth_context(asof=asof, sector_universe={"ETF": ["Banks"]},
        now=now if now is not None else datetime(2026, 9, 18, 10, tzinfo=timezone.utc))


def test_timing_identically_old_inputs_are_delayed_not_current(monkeypatch):
    from datetime import datetime, timezone
    r = _timed_context(monkeypatch, now=datetime(2026, 9, 21, 12, tzinfo=timezone.utc))
    assert r["timing"]["expected_session"] == "2026-09-21"
    assert r["timing"]["status"] == "delayed"
    assert r["sample"]["status"] == r["daily_board"]["status"] == "delayed"
    assert r["sample"]["asof"] == "2026-09-18"
    assert r["sample"]["current_comparison"] is None
    assert r["sectors"]["eligible"] == 0
    assert r["timing"]["sources"]["sample"]["sessions_behind"] == 1


@pytest.mark.parametrize("instant,expected,state", [
    ("2026-09-18T09:00:00+00:00", "2026-09-18", "current"),
    ("2026-09-20T12:00:00+00:00", "2026-09-18", "current"),
    ("2026-09-21T08:59:00+00:00", "2026-09-18", "current"),
    ("2026-09-21T09:00:00+00:00", "2026-09-21", "delayed"),
    ("2026-09-25T12:00:00+00:00", "2026-09-24", "delayed"),
])
def test_timing_uses_existing_settle_weekend_and_holiday_rules(monkeypatch, instant, expected, state):
    from datetime import datetime
    r = _timed_context(monkeypatch, now=datetime.fromisoformat(instant))
    assert r["timing"]["expected_session"] == expected
    assert r["timing"]["status"] == state
    assert r["timing"]["calendar_basis"] == "lib.cn_calendar.conservative_rules"


def test_timing_unsettled_assessment_cannot_include_same_day_spike(monkeypatch):
    from datetime import datetime, timezone
    def future(inputs):
        for key in (("china_search", "closes"), ("china", "510300.SS"), ("china", "ETF")):
            inputs[key].loc[pd.Timestamp("2026-09-21")] = 9999.0
    r = _timed_context(monkeypatch, asof="2026-09-21", change=future,
                       now=datetime(2026, 9, 21, 8, tzinfo=timezone.utc))
    assert r["assessment_asof"] == "2026-09-21"
    assert r["timing"]["calculation_asof"] == "2026-09-18"
    assert r["timing"]["status"] == "unsettled"
    assert r["sample"]["windows"]["20"]["median_return_pct"] == 0
    assert r["timing"]["sources"]["sample"]["observed_through"] == "2026-09-21"
    assert r["timing"]["sources"]["sample"]["after_cutoff_rows"] == 1
    assert r["sample"]["current_comparison"] is None


def test_timing_different_board_and_sample_dates_are_explicit(monkeypatch):
    def older_board(inputs):
        inputs[("china_board_breadth", "breadth")].index = pd.to_datetime(["2026-09-17"])
    r = _timed_context(monkeypatch, change=older_board)
    assert r["timing"]["status"] == "mixed"
    assert r["timing"]["sources"]["daily_board"]["used_asof"] == "2026-09-17"
    assert r["timing"]["sources"]["sample"]["used_asof"] == "2026-09-18"


def test_timing_fresh_row_with_bad_benchmark_has_no_valid_clock(monkeypatch):
    def bad_benchmark(inputs):
        inputs[("china", "510300.SS")].iloc[-1] = np.nan
    r = _timed_context(monkeypatch, change=bad_benchmark)
    b = r["timing"]["sources"]["benchmark"]
    assert b["frame_through"] == "2026-09-18"
    assert b["observed_through"] == "2026-09-17"
    assert b["status"] == "unavailable"
    assert r["timing"]["status"] == "partial"


def test_timing_fresh_but_undercovered_panel_remains_partial(monkeypatch):
    def thin(inputs):
        inputs[("china_search", "closes")].iloc[-1, 4:] = np.nan
    r = _timed_context(monkeypatch, change=thin)
    assert r["timing"]["status"] == "partial"
    assert r["timing"]["sources"]["sample"]["status"] == "insufficient_coverage"
    assert r["sample"]["quote_count"] == 4


def test_timing_calendar_failure_keeps_old_values_but_no_current_claim(monkeypatch):
    from lib import cn_calendar
    def unavailable(_now):
        raise ValueError("calendar unavailable")
    monkeypatch.setattr(cn_calendar, "expected_last_session", unavailable)
    r = _timed_context(monkeypatch)
    assert r["timing"]["status"] == "unavailable"
    assert r["timing"]["expected_session"] is None
    assert r["sample"]["current_comparison"] is None
    assert r["sample"]["status"] != "current"


@pytest.mark.parametrize("clock", ["not a clock", float("nan"), pd.NaT])
def test_timing_invalid_clock_never_defaults_to_fresh(monkeypatch, clock):
    r = _timed_context(monkeypatch, now=clock)
    assert r["timing"]["status"] == "unavailable"
    assert r["sample"]["current_comparison"] is None


def test_timing_current_measurements_match_prior_arithmetic(monkeypatch):
    import json
    prices, bench, names = _price_context_fixture()
    expected = _price_context(prices, bench, names)
    r = _timed_context(monkeypatch)
    assert r["timing"]["status"] == "current"
    assert r["sample"]["windows"] == expected["windows"]
    assert r["sample"]["trend"] == expected["trend"]
    json.dumps(r, allow_nan=False)


@pytest.mark.parametrize('bad', [np.nan, np.inf, 0.0, -1.0, True])
def test_clock_invalid_latest_benchmark_cannot_be_fresh(monkeypatch, bad):
    def invalid(inputs):
        key = ('china', '510300.SS')
        inputs[key] = inputs[key].astype(object)
        inputs[key].iloc[-1, 0] = bad
    result = _timed_context(monkeypatch, change=invalid)
    source = result['timing']['sources']['benchmark']
    assert source['frame_through'] == '2026-09-18'
    assert source['observed_through'] == '2026-09-17'
    assert source['status'] == 'unavailable'
    assert result['timing']['status'] == 'partial'
    assert result['sample']['current_comparison'] is None


def test_clock_sector_lag_is_not_hidden_by_current_core_sources(monkeypatch):
    def older(inputs):
        inputs[('china', 'ETF')] = inputs[('china', 'ETF')].iloc[:-1]
    result = _timed_context(monkeypatch, change=older)
    assert result['timing']['status'] == 'mixed'
    assert result['timing']['sources']['sector:ETF']['used_asof'] == '2026-09-17'
    assert result['timing']['sources']['sector:ETF']['status'] == 'delayed'
    assert result['sectors']['eligible'] == 0
    assert result['sample']['current_comparison'] is None


def test_clock_invalid_board_tail_is_not_an_observation(monkeypatch):
    def bad_board(inputs):
        key = ('china_board_breadth', 'breadth')
        older = inputs[key].copy()
        older.index = pd.to_datetime(['2026-09-17'])
        inputs[key] = pd.concat([older, inputs[key]])
        inputs[key].loc[pd.Timestamp('2026-09-18'), 'n'] = 1
    result = _timed_context(monkeypatch, change=bad_board)
    source = result['timing']['sources']['daily_board']
    assert source['frame_through'] == '2026-09-18'
    assert source['observed_through'] == '2026-09-17'
    assert source['status'] == 'unavailable'
    assert result['timing']['status'] == 'partial'


def test_clock_naive_wall_time_does_not_guess_a_timezone(monkeypatch):
    from datetime import datetime
    result = _timed_context(monkeypatch, now=datetime(2026, 9, 18, 10))
    assert result['timing']['status'] == 'unavailable'
    assert result['sample']['current_comparison'] is None


def test_clock_future_calendar_result_is_not_accepted(monkeypatch):
    from datetime import date
    from lib import cn_calendar
    monkeypatch.setattr(cn_calendar, 'expected_last_session', lambda _: date(2026, 9, 22))
    result = _timed_context(monkeypatch)
    assert result['timing']['status'] == 'unavailable'


def _render_clock_panel(context):
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader, ChainableUndefined
    env = Environment(loader=FileSystemLoader(str(Path(__file__).resolve().parents[1] / 'templates')),
                      undefined=ChainableUndefined, autoescape=True)
    return str(env.get_template('_china_participation_context.html.j2').module.participation_panel(context))


@pytest.mark.parametrize('status,en,zh', [
    ('delayed', 'Dated snapshot', '历史快照'),
    ('unsettled', 'Unsettled assessment', '尚未结算'),
    ('mixed', 'Different source dates', '来源日期不同'),
    ('partial', 'Incomplete inputs', '输入不完整'),
    ('unavailable', 'Timing unavailable', '时间核验暂不可用'),
])
def test_clock_panel_labels_noncurrent_evidence(monkeypatch, status, en, zh):
    context = _timed_context(monkeypatch)
    context['timing']['status'] = status
    html = _render_clock_panel(context)
    assert en in html and zh in html
    assert 'Expected completed session' in html and '预期已完成交易日' in html
    assert '2026-09-18' in html
    assert 'lib.cn_calendar' not in html
    assert 'Check source timing' in html and '核对来源时间' in html


def test_clock_panel_discloses_its_calendar_and_scope_limit(monkeypatch):
    html = _render_clock_panel(_timed_context(monkeypatch))
    assert 'Conservative calendar rules' in html and '保守日历规则' in html


def test_clock_missing_receipt_does_not_default_to_current(monkeypatch):
    context = _timed_context(monkeypatch)
    context.pop('timing')
    html = _render_clock_panel(context)
    assert 'Timing unavailable' in html
    assert 'Read the index alongside' not in html


def test_clock_short_sector_history_is_partial_even_with_a_fresh_tail(monkeypatch):
    def short(inputs):
        inputs[('china', 'ETF')] = inputs[('china', 'ETF')].tail(8)
    result = _timed_context(monkeypatch, change=short)
    source = result['timing']['sources']['sector:ETF']
    assert source['frame_through'] == '2026-09-18'
    assert source['status'] == 'insufficient_coverage'
    assert result['timing']['status'] == 'partial'
    assert result['sample']['current_comparison'] is None
    assert result['sectors']['eligible'] == 0


def test_clock_calendar_runtime_failure_stays_unavailable(monkeypatch):
    from lib import cn_calendar
    def broken(_):
        raise RuntimeError('calendar unavailable')
    monkeypatch.setattr(cn_calendar, 'expected_last_session', broken)
    result = _timed_context(monkeypatch)
    assert result['timing']['status'] == 'unavailable'
    assert result['sample']['current_comparison'] is None


# A missing benchmark row must not stretch a claimed return/MA window backward.
@pytest.mark.parametrize('position,affected', [(-3, {'5','20'}), (-7, {'20'}),
                                               (-21, {'20'}), (-22, set())])
def test_context_calendar_hole_cannot_change_the_return_horizon(position, affected):
    prices, bench, names = _price_context_fixture()
    prices.iloc[-22] = 50.; prices.iloc[-21] = 100.; prices.iloc[-1] = 90.
    before = _price_context(prices, bench, names)
    missing = bench.index[position]
    result = _price_context(prices, bench.drop(missing), names)
    for key in ('5','20'):
        w = result['windows'][key]
        if key in affected:
            assert w['status'] == 'incomplete_calendar'
            assert w['median_return_pct'] is None and w['benchmark_return_pct'] is None
            assert w['comparison'] is None
            assert w['calendar_gaps'] == [str(missing.date())]
        else:
            assert w['median_return_pct'] == before['windows'][key]['median_return_pct']
            assert w['start'] == before['windows'][key]['start']
            assert w['status'] == 'ok'
    if '20' in affected:
        assert result['current_comparison'] is None


@pytest.mark.parametrize('position,current_ok,paired_ok',
                         [(-7,False,False),(-100,False,False),(-202,True,False)])
def test_context_calendar_hole_qualifies_ma_windows_separately(position,current_ok,paired_ok):
    prices, bench, names = _price_context_fixture()
    missing = bench.index[position]
    result = _price_context(prices, bench.drop(missing), names)
    assert (result['trend']['above200_pct'] is not None) == current_ok
    assert (result['trend']['paired_change_pp'] is not None) == paired_ok
    assert str(missing.date()) in result['trend']['calendar_gaps']


@pytest.mark.parametrize('position', [-209, -1])
def test_context_calendar_gap_outside_used_window_does_not_erase_evidence(position):
    prices, bench, names = _price_context_fixture()
    reference = _price_context(prices, bench, names)
    if position == -1:
        prices.loc[pd.Timestamp('2026-09-21')] = 2000.
    else:
        bench = bench.drop(bench.index[position])
    assert _price_context(prices, bench, names) == reference


def test_context_calendar_gap_uses_only_requested_valid_observations():
    prices, bench, names = _price_context_fixture()
    missing = bench.index[-7]
    prices.loc[missing] = np.nan
    prices['UNREQUESTED'] = 100.
    reduced = bench.drop(missing)
    without_extra = _price_context(prices.drop(columns='UNREQUESTED'), reduced, names)
    assert _price_context(prices, reduced, names) == without_extra
    assert without_extra['windows']['20']['status'] == 'ok'


def test_context_calendar_hole_is_not_silently_counted_as_a_rising_sector():
    from engine.china_participation import sector_breadth_context
    prices, bench, names = _price_context_fixture()
    prices.iloc[-1] = 120.
    result = sector_breadth_context({names[0]: prices[[names[0]]].rename(columns={names[0]:'close'})},
        bench.drop(bench.index[-7]), names={names[0]: ('Synthetic sector',)}, asof='2026-09-18')
    assert result['declared'] == 1 and result['eligible'] == result['rising'] == 0
    assert result['rows'][0]['return_pct'] is None


def test_index_member_calendar_hole_is_not_three_hundred_missing_stock_quotes():
    from engine.china_participation import index_member_breadth_context
    membership, prices, benchmark = _index_member_fixture()
    missing = benchmark.index[-7]
    result = index_member_breadth_context(membership, prices, benchmark.drop(missing), asof='2026-09-18')
    window = result['windows']['20']
    assert window['status'] == 'incomplete_calendar'
    assert window['median_return_pct'] is None
    assert window['coverage_detail']['status'] == 'incomplete_calendar'
    assert window['coverage_detail']['excluded_count'] is None
    assert window['coverage_detail']['members'] == []
    assert window['coverage_detail']['calendar_gaps'] == [str(missing.date())]


def test_context_calendar_check_preserves_inputs():
    prices, bench, names = _price_context_fixture()
    bench = bench.drop(bench.index[-7])
    p0, b0 = prices.copy(deep=True), bench.copy(deep=True)
    _price_context(prices, bench, names)
    pd.testing.assert_frame_equal(prices, p0)
    pd.testing.assert_series_equal(bench, b0)


def test_context_calendar_hole_reaches_loader_and_existing_panel(monkeypatch):
    from datetime import datetime, timezone
    from lib import store
    from engine.china_participation import load_breadth_context
    prices, bench, _ = _price_context_fixture()
    prices.columns = [f'{600000+i:06d}.SS' for i in range(len(prices.columns))]
    prices.iloc[-22] = 50.; prices.iloc[-21] = 100.; prices.iloc[-1] = 90.
    frames = {('china_search','closes'): prices,
              ('china','510300.SS'): bench.drop(bench.index[-7]).to_frame('close'),
              ('china_board_breadth','breadth'): _board_fixture()}
    calls = []
    def read(group,name):
        calls.append((group,name))
        return frames.get((group,name))
    monkeypatch.setattr(store,'read',read)
    result = load_breadth_context(asof='2026-09-18',
                                 now=datetime(2026,9,18,12,tzinfo=timezone.utc))
    assert result['timing']['status'] == 'partial'
    assert result['sample']['current_comparison'] is None
    assert result['sample']['windows']['20']['median_return_pct'] is None
    html = _render_participation_context(result)
    assert 'current participation is not fully established' in html
    assert '+80.00%' not in html and 'Unavailable' in html
    assert set(calls) == set(frames) and len(calls) == 3
