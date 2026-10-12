"""Early rotation context: exact-session evidence, no new decision authority."""
from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import rotation_events as RE
from engine.oracle import ratio_lens as RL
from lib import nyse_calendar as cal

ASOF = "2026-10-06"


def levels(end=ASOF, n=45, start_value=100.0, daily=0.001, source=None):
    dates = cal.sessions_between(
        pd.Timestamp(end).date() - pd.Timedelta(days=n * 3),
        pd.Timestamp(end).date(),
    )[-n:]
    s = pd.Series(start_value * (1 + daily) ** np.arange(len(dates)),
                  index=pd.DatetimeIndex(dates))
    if source:
        s.attrs["source_root"] = source
    return s


def pair(num="XLP", den="XLK", group="defensive_sector", pid=None):
    return {
        "id": pid or f"{num.lower()}_vs_{den.lower()}",
        "num": num, "den": den, "kind": "etf",
        "name_en": f"{num} vs {den}", "name_zh": f"{num} / {den}",
        "reads_as_en": "Relative price context", "reads_as_zh": "相对价格",
        "context_group": group,
    }


def receipt(group="defensive_sector", num_daily=.003, den_daily=.001,
            num="XLP", den="XLK", as_of=ASOF):
    return RL.short_horizon_receipt(
        pair(num, den, group), levels(daily=num_daily), levels(daily=den_daily),
        as_of=as_of,
    )


def batch(*rows):
    return {"schema": "ratio_lens.short_horizons/v1", "as_of": ASOF,
            "definition_id": "ratio_lens.short_horizons/1",
            "pairs": list(rows), "reason_codes": []}


def context(*rows):
    return RE.early_rotation_context(batch(*rows), as_of=ASOF)


def test_simple_return_and_exact_session_endpoints():
    rec = receipt()
    w = rec["horizons"]["2s"]
    assert w["eligible"] is True
    assert w["start"] == "2026-10-02"
    assert w["end"] == ASOF
    assert w["numerator_return_pct"] == pytest.approx(((1.003)**2 - 1)*100)
    assert w["denominator_return_pct"] == pytest.approx(((1.001)**2 - 1)*100)
    assert w["ratio_return_pct"] == pytest.approx(((1.003/1.001)**2 - 1)*100)
    assert w["shape"] == "BOTH_UP"
    assert set(rec["horizons"]) == {"1s", "2s", "5s", "20s"}


def test_post_cutoff_price_shock_cannot_change_short_or_long_math(tmp_path, monkeypatch):
    p = pair()
    num, den = levels(n=300), levels(n=300, daily=.0007)
    path = tmp_path / "oracle"
    path.mkdir()
    (path / "ratio_pairs.json").write_text(json.dumps({"version": "test", "taxonomy": {}, "pairs": [p]}))
    full = {"XLP": num, "XLK": den}
    monkeypatch.setattr(RL, "_etf_close", lambda sym, root: full[sym])
    before = RL.compute(tmp_path, as_of=ASOF)
    full["XLP"] = pd.concat([num, pd.Series([100000.], index=[pd.Timestamp("2026-10-07")])])
    after = RL.compute(tmp_path, as_of=ASOF)
    assert before == after
    assert after["pairs"][0]["value_as_of"] == ASOF


def test_older_all_long_math_cutoff_is_applied_to_baskets(tmp_path, monkeypatch):
    p = pair("basket_a", "basket_b")
    p["kind"] = "basket"
    (tmp_path / "oracle").mkdir()
    (tmp_path / "oracle" / "ratio_pairs.json").write_text(json.dumps({"version": "test", "taxonomy": {}, "pairs": [p]}))
    observed = []
    monkeypatch.setattr(RL, "_basket_ew_level",
                        lambda *args: levels(end="2026-10-08", n=45))
    original = RL._compute_pair_record
    def capture(p, num, den, kind, **kwargs):
        observed.extend([num.index.max(), den.index.max()])
        return original(p, num, den, kind, **kwargs)
    monkeypatch.setattr(RL, "_compute_pair_record", capture)
    RL.compute(tmp_path, as_of=ASOF)
    assert observed == [pd.Timestamp(ASOF), pd.Timestamp(ASOF)]


@pytest.mark.parametrize("bad", ["duplicate", "gap", "zero", "negative", "nan", "infinite"])
def test_invalid_window_abstains_instead_of_skipping_rows(bad):
    n, d = levels(), levels()
    if bad == "duplicate":
        n = pd.concat([n, n.iloc[-2:-1]])
    elif bad == "gap":
        n = n.drop(n.index[-2])
    else:
        n.iloc[-2] = {"zero": 0., "negative": -1., "nan": np.nan, "infinite": np.inf}[bad]
    rec = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    assert rec["horizons"]["2s"]["eligible"] is False
    assert rec["horizons"]["2s"]["ratio_return_pct"] is None
    assert rec["horizons"]["2s"]["reason_codes"]


def test_weekend_row_does_not_satisfy_missing_friday():
    n, d = levels(), levels()
    n = n.drop(pd.Timestamp("2026-10-02"))
    n.loc[pd.Timestamp("2026-10-03")] = 101.
    rec = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    assert rec["horizons"]["2s"]["eligible"] is False
    assert "2026-10-02" in rec["horizons"]["2s"]["missing_num_sessions"]


def test_stale_asof_and_trailing_null_cannot_refresh_price_value():
    n, d = levels(), levels()
    n.iloc[-1] = np.nan
    rec = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    assert rec["value_as_of"] == "2026-10-05"
    assert rec["horizons"]["2s"]["eligible"] is False
    rec = RL.short_horizon_receipt(pair(), levels(end="2026-10-05"), d, as_of=ASOF)
    assert rec["horizons"]["2s"]["eligible"] is False
    assert "STALE_NUMERATOR" in rec["reason_codes"]


def test_future_only_source_is_missing_at_cutoff():
    future = pd.Series([100.], index=[pd.Timestamp("2026-10-07")])
    rec = RL.short_horizon_receipt(pair(), future, future, as_of=ASOF)
    assert rec["value_as_of"] is None
    assert context(rec)["state"] is None


def test_price_loader_honors_explicit_root_without_creating_missing_store(tmp_path, monkeypatch):
    from lib import store
    monkeypatch.setattr(store, "read", lambda *args: pytest.fail("global data root read"))
    assert RL._etf_close("XLP", tmp_path) is None
    assert not (tmp_path / "yahoo").exists()
    (tmp_path / "yahoo").mkdir()
    pd.DataFrame({"close": levels()}).to_parquet(tmp_path / "yahoo" / "XLP.parquet")
    got = RL._etf_close("XLP", tmp_path)
    assert got.attrs["source_root"] == "yahoo/XLP.parquet#close"


def test_no_false_lineage_completeness_and_revisions_separate_from_roots():
    n, d = levels(), levels()
    unknown = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    assert unknown["lineage"]["status"] == "UNKNOWN"
    assert unknown["lineage"]["roots"] == []
    n.attrs["source_root"] = "yahoo/XLP.parquet#close"
    d.attrs["source_root"] = "yahoo/XLK.parquet#close"
    one = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    n.iloc[-1] *= 1.01
    two = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    assert one["lineage"]["status"] == "COMPLETE"
    assert one["lineage"]["roots"] == two["lineage"]["roots"]
    assert one["lineage"]["revisions"] != two["lineage"]["revisions"]
    assert one["lineage"]["dependency_groups"] == ["equity_price"]


def test_pure_context_can_watch_defensives_while_donor_still_rises():
    out = context(receipt(), receipt("broadening_proxy", -.001, .001, "IWM", "QQQ"))
    assert out["state"] == "DEFENSIVE_RELATIVE_STRENGTH"
    assert out["pairs"][0]["horizons"]["2s"]["shape"] == "BOTH_UP"
    assert out["display_only"] is True
    assert "macro_context" not in inspect.signature(RE.early_rotation_context).parameters


def test_both_down_is_resilience_not_distribution():
    out = context(receipt(num_daily=-.001, den_daily=-.003))
    assert out["state"] == "DEFENSIVE_RELATIVE_STRENGTH"
    assert out["pairs"][0]["interpretation"] == "RELATIVE_RESILIENCE"
    assert "distribution" not in json.dumps(out).lower()


def test_healthy_broadening_never_becomes_defensive_risk_off():
    out = context(receipt(num_daily=.001, den_daily=.003),
                  receipt("broadening_proxy", .003, .001, "IWM", "QQQ"))
    assert out["state"] == "BROADENING"
    assert "RISK_OFF" not in json.dumps(out)
    assert out["coverage"]["groups"]["broadening_proxy"]["positive_2s"] == 1


def test_mixed_rotation_and_no_shift_are_observations():
    defensive = receipt()
    broad = receipt("broadening_proxy", .003, .001, "IWM", "QQQ")
    assert context(defensive, broad)["state"] == "MIXED_ROTATION"
    assert context(receipt(num_daily=.001, den_daily=.003),
                   receipt("broadening_proxy", .001, .003, "IWM", "QQQ"))["state"] == "NO_EARLY_SHIFT"


def test_retailers_alone_are_not_sector_or_prior_loser_confirmation():
    retail = receipt("retailer_context", .005, .001, "WMT", "XLK")
    out = context(retail)
    assert out["state"] is None
    assert out["coverage"]["groups"]["retailer_context"]["positive_2s"] == 1
    assert out["prior_loser_constituent_claim"] is False


def test_two_day_shift_does_not_require_five_or_twenty_day_agreement():
    n, d = levels(daily=-.004), levels(daily=.001)
    n.iloc[-2:] = [n.iloc[-3]*1.01, n.iloc[-3]*1.02]
    rec = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    out = context(rec)
    assert out["state"] == "DEFENSIVE_RELATIVE_STRENGTH"
    assert "2S_VS_20S_SIGN_CONFLICT" in out["pairs"][0]["reason_codes"]


def test_duplicate_and_permutation_do_not_amplify_observations():
    a, b = receipt(), receipt("broadening_proxy", .003, .001, "IWM", "QQQ")
    before = context(a, b)
    after = context(b, copy.deepcopy(a), a)
    assert after == before
    alias = copy.deepcopy(a)
    alias["pair_id"] = "alias"
    after_alias = context(a, alias, b)
    assert after_alias["state"] == before["state"]
    assert after_alias["coverage"] == before["coverage"]


def test_conflicting_duplicate_pair_abstains():
    a = receipt()
    b = copy.deepcopy(a)
    b["horizons"]["2s"]["ratio_return_pct"] *= -1
    out = context(a, b)
    assert out["state"] is None
    assert "CONFLICTING_PAIR_OBSERVATIONS" in out["reason_codes"]


def test_context_never_writes_files_or_mutates_receipts(tmp_path, monkeypatch):
    a = receipt()
    original = copy.deepcopy(a)
    monkeypatch.chdir(tmp_path)
    out = context(a)
    assert a == original
    assert list(tmp_path.iterdir()) == []
    assert not any(k in out for k in ("score", "confidence", "may_gate", "active", "severity"))


def test_registry_contains_separate_explicit_context_groups():
    registry = RL._load_registry(Path(__file__).resolve().parents[1] / "data")
    groups = {}
    for p in registry["pairs"]:
        if p.get("context_group"):
            groups.setdefault(p["context_group"], set()).add((p["num"], p["den"]))
    assert groups == {
        "defensive_sector": {("XLP", "XLK"), ("XLU", "XLK"), ("XLV", "XLK"), ("XLP", "SMH")},
        "retailer_context": {("WMT", "XLK"), ("COST", "XLK")},
        "broadening_proxy": {("DIA", "QQQ"), ("IWM", "QQQ"), ("RSP", "QQQ")},
    }


def test_nonfinite_or_malformed_receipt_returns_unknown_without_crashing():
    a = receipt()
    a["horizons"]["2s"]["ratio_return_pct"] = float("nan")
    out = context(a)
    assert out["state"] is None
    assert "INVALID_PAIR_OBSERVATION" in out["reason_codes"]
    assert out["lineage"]["status"] == "UNKNOWN"


def test_registered_reader_loads_each_leg_once_and_discloses_missing(tmp_path, monkeypatch):
    configs = [pair(), pair("WMT", "XLK", "retailer_context")]
    (tmp_path / "oracle").mkdir()
    (tmp_path / "oracle" / "ratio_pairs.json").write_text(json.dumps(
        {"version": "test", "taxonomy": {}, "pairs": configs}))
    calls = []
    def load(sym, root):
        calls.append(sym)
        assert root == tmp_path
        return None if sym == "WMT" else levels()
    monkeypatch.setattr(RL, "_etf_close", load)
    result = RL.registered_short_horizon_context(tmp_path, as_of=ASOF)
    assert calls.count("XLK") == 1
    assert set(calls) == {"XLP", "XLK", "WMT"}
    out = RE.early_rotation_context(result, as_of=ASOF)
    assert out["coverage"]["registered_pairs"] == 2
    assert out["coverage"]["missing_pair_ids"] == ["wmt_vs_xlk"]
    assert out["state"] is None


def test_unlabelled_missing_registry_cannot_become_no_shift(tmp_path):
    result = RL.registered_short_horizon_context(tmp_path, as_of=ASOF)
    out = RE.early_rotation_context(result, as_of=ASOF)
    assert out["state"] is None
    assert "CONTEXT_REGISTRY_UNAVAILABLE" in out["reason_codes"]


def test_us_nightly_context_preserves_confirmed_payload_and_ledger(tmp_path, monkeypatch):
    from tests.test_rotation_events_v2 import _make_minimal_sectors
    sectors = _make_minimal_sectors()
    for spec in sectors.values():
        for s in [spec["etf_close"], *spec["legs"].values()]:
            s.index = levels(end="2026-10-05", n=len(s)).index
    universe = {"bench": {"key": "spy"}, "series": [], "pairs": [],
                "velocity_series": [], "contagion_pairs": []}
    closes = {"spy": levels(n=400)}
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.setattr(RL, "registered_short_horizon_context",
                        lambda root, *, as_of: batch(receipt()))
    with_context = RE.run_nightly(
        sectors, tmp_path / "with", generated_utc="2026-10-07T01:00:00Z",
        universe=universe, closes=closes,
    )
    assert with_context["early_context"]["as_of"] == ASOF
    assert with_context["as_of"] == "2026-10-05"
    assert with_context["early_context"]["state"] == "DEFENSIVE_RELATIVE_STRENGTH"
    monkeypatch.setattr(RL, "registered_short_horizon_context",
                        lambda root, *, as_of: batch())
    without = RE.run_nightly(
        sectors, tmp_path / "without", generated_utc="2026-10-07T01:00:00Z",
        universe=universe, closes=closes,
    )
    assert {k: v for k, v in with_context.items() if k != "early_context"} == {
        k: v for k, v in without.items() if k != "early_context"}
    def file_bytes(root):
        return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert file_bytes(tmp_path / "with") == file_bytes(tmp_path / "without")
    assert all("early_context" not in p.read_text()
               for p in (tmp_path / "with").rglob("*.jsonl"))


def test_no_universe_regional_path_never_loads_early_context(tmp_path, monkeypatch):
    from tests.test_rotation_events_v2 import _make_minimal_sectors
    monkeypatch.setattr(RL, "registered_short_horizon_context",
                        lambda *args, **kwargs: pytest.fail("US context reached regional v1 path"))
    result = RE.run_nightly(_make_minimal_sectors(), tmp_path)
    assert "early_context" not in result


def test_proportional_prices_are_not_a_floating_point_relative_shift():
    n = levels(daily=.003)
    d = n * 1.73
    rec = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    assert all(w["ratio_return_pct"] == 0.0 for w in rec["horizons"].values())
    assert context(rec)["coverage"]["positive_2s"] == 0


def test_finite_extreme_prices_cannot_emit_infinite_return():
    n, d = levels(), levels()
    n.iloc[-3] = 1e-308
    n.iloc[-1] = 1e308
    rec = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    assert rec["horizons"]["2s"]["eligible"] is False
    json.dumps(rec, allow_nan=False)


def test_future_intraday_label_cannot_poison_a_prior_daily_receipt():
    n, d = levels(), levels(daily=.001)
    before = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    n.loc[pd.Timestamp("2026-10-07T12:00:00")] = 1e9
    after = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    assert after == before


def test_retained_intraday_label_is_still_rejected():
    n, d = levels(), levels()
    n.loc[pd.Timestamp(ASOF + "T12:00:00")] = 1e9
    out = RL.short_horizon_receipt(pair(), n, d, as_of=ASOF)
    assert out["horizons"]["2s"]["eligible"] is False


@pytest.mark.parametrize("horizons", [[1], {"2s": [1]}, {"2s": {}, "5s": "bad"}])
def test_malformed_horizon_mapping_returns_explicit_unknown(horizons):
    a = receipt()
    a["horizons"] = horizons
    out = context(a)
    assert out["state"] is None
    assert "INVALID_PAIR_OBSERVATION" in out["reason_codes"]
    assert out["lineage"]["status"] == "UNKNOWN"


def test_malformed_reason_codes_are_rejected_without_crashing():
    a = receipt()
    a["reason_codes"] = [{"bad": True}]
    assert "INVALID_PAIR_OBSERVATION" in context(a)["reason_codes"]
    envelope = batch(receipt())
    envelope["reason_codes"] = [{"bad": True}]
    out = RE.early_rotation_context(envelope, as_of=ASOF)
    assert out["state"] is None
    assert out["reason_codes"] == ["INVALID_SHORT_HORIZON_ENVELOPE"]
