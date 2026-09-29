"""Opt-in daily expansion of the existing options universe; no vendor calls."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from engine import options_universe as universe

DAY = date(2026, 9, 28)


def membership(*symbols, group="sp500", first="2026-09-01", last="2026-09-28"):
    return pd.DataFrame([
        {"ticker": s, "group": group, "name": s, "sector": "test",
         "first_seen": first, "last_seen": last, "active": True}
        for s in symbols
    ], columns=["ticker", "group", "name", "sector", "first_seen", "last_seen", "active"])


def settings(target=3, budget=12, priorities=()):
    return {"target_stocks": target, "max_total_roots": budget,
            "priority_symbols": list(priorities)}


def plan(cfg=None, *, legacy=("SPY", "AAPL"), anchors=("SPY", "AAPL"), ledger=None, day=DAY):
    assert hasattr(universe, "plan_daily_expansion"), "shared daily expansion selector is missing"
    return universe.plan_daily_expansion(
        cfg or settings(), legacy_symbols=list(legacy), anchor_symbols=list(anchors),
        ledger=membership("AAPL", "AAA", "BBB", "CCC") if ledger is None else ledger,
        as_of=day,
    )


def test_disabled_path_keeps_legacy_order_and_never_reads_membership(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("disabled expansion accessed the membership planner")
    monkeypatch.setattr(universe.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(universe, "plan_daily_expansion", forbidden, raising=False)
    cfg = {"symbols": ["SPY", "AAPL", "SPY"], "include_baskets": False,
           "max_underlyings": 1, "daily_expansion": {"enabled": False}}
    assert universe.gex_symbols(cfg) == ["SPY", "AAPL"]
    assert list(tmp_path.iterdir()) == []


def test_priorities_win_new_slots_without_evicting_existing_roots():
    result = plan(settings(priorities=["CCC"]), legacy=["SPY", "AAPL", "LEGACY"])
    assert result["symbols"] == ["SPY", "AAPL", "CCC", "LEGACY", "AAA"]
    assert result["selected_stock_count"] == 3
    assert result["retained_legacy_count"] == 3
    assert result["roots_not_classified_as_stocks"] == ["SPY", "LEGACY"]
    assert result["uncovered_priority_symbols"] == []
    assert result["collection_started"] is False
    assert result["optionability_verified"] is False
    assert result["qualified_stock_count"] is None


def test_etf_and_unclassified_roots_do_not_satisfy_stock_target():
    result = plan(legacy=["SPY", "QQQ", "IWM"], anchors=["SPY", "QQQ", "IWM"])
    assert result["selected_stock_count"] == 3
    assert len(result["symbols"]) == 6
    assert set(result["roots_not_classified_as_stocks"]) == {"SPY", "QQQ", "IWM"}


def test_unknown_priority_is_retained_but_not_called_optionable_or_a_stock():
    result = plan(settings(priorities=["NEWIPO"]))
    assert "NEWIPO" in result["symbols"]
    assert "NEWIPO" in result["roots_not_classified_as_stocks"]
    assert result["selected_stock_count"] == 3
    assert result["qualified_stock_count"] is None


@pytest.mark.parametrize("target", [1000, 1500])
def test_large_targets_count_stocks_separately(target):
    ledger = membership(*(f"S{i:04d}" for i in range(1600)))
    result = plan(settings(target=target, budget=target + 5),
                  legacy=["SPY", "QQQ"], anchors=["SPY", "QQQ"], ledger=ledger)
    assert result["selected_stock_count"] == target
    assert len(result["symbols"]) == target + 2
    assert len(set(result["symbols"])) == target + 2
    assert result["collection_started"] is False


def test_existing_stock_population_is_never_shrunk_to_hit_a_smaller_target():
    result = plan(settings(target=1), legacy=["SPY", "AAPL", "AAA", "BBB"])
    assert set(result["symbols"]) == {"SPY", "AAPL", "AAA", "BBB"}
    assert result["selected_stock_count"] == 3
    assert result["target_exceeded_by_retention"] is True


def test_total_root_ceiling_refuses_instead_of_dropping_incumbents():
    with pytest.raises(ValueError, match="total_root_budget_exceeded"):
        plan(settings(target=3, budget=3))


def test_priority_overflow_is_explicit_and_never_silently_truncated():
    with pytest.raises(ValueError, match="total_root_budget_exceeded"):
        plan(settings(target=1, budget=3, priorities=["NEW1", "NEW2", "NEW3"]))


def test_insufficient_membership_does_not_invent_qualified_stocks():
    with pytest.raises(ValueError, match="stock_target_unreachable"):
        plan(settings(target=10))


def test_empty_or_missing_membership_fails_closed(monkeypatch, tmp_path):
    with pytest.raises(ValueError, match="stock_target_unreachable"):
        plan(ledger=membership())
    assert hasattr(universe, "plan_daily_expansion"), "shared daily expansion selector is missing"
    monkeypatch.setattr(universe.config, "data_dir", lambda: tmp_path)
    with pytest.raises(ValueError, match="membership_unavailable"):
        universe.plan_daily_expansion(settings(), legacy_symbols=["SPY"],
                                      anchor_symbols=["SPY"], as_of=DAY)
    assert list(tmp_path.iterdir()) == []


def test_existing_membership_owner_controls_date_and_group_selection():
    ledger = pd.concat([
        membership("AAPL"), membership("MID", group="sp400"),
        membership("SMALL", group="sp600"), membership("RUS", group="r2000"),
        membership("FUTURE", first="2026-09-29", last="2026-09-30"),
        membership("DROPPED", last="2026-09-25"),
        membership("NOT_EQUITY", group="unclassified"),
    ], ignore_index=True)
    result = plan(settings(target=4), ledger=ledger)
    assert result["symbols"] == ["SPY", "AAPL", "MID", "SMALL", "RUS"]
    assert result["source_session"] == "2026-09-28"
    assert "cold-start" in result["membership_caveat"]


def test_stale_membership_is_not_refreshed_by_planning_time():
    with pytest.raises(ValueError, match="stock_target_unreachable"):
        plan(ledger=membership("AAPL", "AAA", "BBB", last="2026-09-23"))


def test_class_share_punctuation_is_not_silently_rewritten():
    result = plan(settings(target=2, priorities=["brk.b"]),
                  ledger=membership("AAPL", "BRK.B"))
    assert result["symbols"] == ["SPY", "AAPL", "BRK.B"]
    assert "BRK-B" not in result["symbols"]


def test_deduplication_preserves_anchor_priority_and_stock_count():
    result = plan(settings(priorities=["aaa", "AAA", "AAPL"]),
                  ledger=pd.concat([membership("AAPL", "AAA", "BBB"), membership("AAA", group="r2000")]))
    assert result["symbols"] == ["SPY", "AAPL", "AAA", "BBB"]
    assert result["priority_symbols"] == ["AAA", "AAPL"]
    assert result["selected_stock_count"] == 3


@pytest.mark.parametrize("key,value", [
    ("target_stocks", True), ("target_stocks", 0), ("target_stocks", 1501),
    ("target_stocks", 3.5), ("target_stocks", "1000"),
    ("max_total_roots", False), ("max_total_roots", 0), ("max_total_roots", 2001),
])
def test_invalid_budgets_are_rejected(key, value):
    cfg = settings(); cfg[key] = value
    with pytest.raises(ValueError, match="invalid_config"):
        plan(cfg)


@pytest.mark.parametrize("value", ["AAPL", ["../secret"], ["AAPL\nMSFT"], [True], [None]])
def test_malformed_priorities_are_rejected(value):
    cfg = settings(); cfg["priority_symbols"] = value
    with pytest.raises(ValueError, match="invalid_symbol|invalid_config"):
        plan(cfg)


def test_unknown_expansion_keys_are_not_silently_accepted():
    cfg = settings(); cfg["skip_quality_gates"] = True
    with pytest.raises(ValueError, match="invalid_config"):
        plan(cfg)


def test_missing_membership_columns_fail_with_named_source_error():
    with pytest.raises(ValueError, match="membership_invalid"):
        plan(ledger=pd.DataFrame({"ticker": ["AAPL"]}))


@pytest.mark.parametrize("day", ["2026-09-27", "20260928", "yesterday", True])
def test_invalid_or_non_session_dates_are_rejected(day):
    with pytest.raises(ValueError, match="invalid_session"):
        plan(day=day)


def test_enabled_shared_resolver_reads_the_real_existing_ledger(monkeypatch, tmp_path):
    (tmp_path / "universe").mkdir()
    path = tmp_path / "universe" / "membership.parquet"
    membership("AAPL", "AAA", "BBB", "CCC").to_parquet(path, index=False)
    original = path.read_bytes()
    monkeypatch.setattr(universe.config, "data_dir", lambda: tmp_path)
    cfg = {"symbols": ["SPY", "AAPL"], "include_baskets": False, "max_underlyings": 2,
           "daily_expansion": {"enabled": True, "as_of": DAY.isoformat(),
                               **settings(priorities=["CCC"])}}
    assert universe.gex_symbols(cfg) == ["SPY", "AAPL", "CCC", "AAA"]
    assert path.read_bytes() == original
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")) == [
        "universe", "universe/membership.parquet"]


@pytest.mark.parametrize("enabled", ["false", "true", 1, None])
def test_activation_requires_an_actual_boolean(enabled):
    cfg = {"symbols": ["SPY"], "daily_expansion": {"enabled": enabled}}
    with pytest.raises(ValueError, match="invalid_config"):
        universe.gex_symbols(cfg)


def cli():
    import importlib
    assert importlib.util.find_spec("scripts.plan_options_coverage") is not None, "coverage preflight CLI is missing"
    return importlib.import_module("scripts.plan_options_coverage")


def test_cli_reads_existing_inputs_and_emits_selection_not_live_coverage(monkeypatch, tmp_path, capsys):
    import hashlib
    import json
    module = cli()
    (tmp_path / "universe").mkdir()
    source = tmp_path / "universe" / "membership.parquet"
    membership("AAPL", "AAA", "BBB", "CCC").to_parquet(source, index=False)
    raw = source.read_bytes()
    cfg = {"polygon": {"gex": {"symbols": ["SPY", "AAPL"], "include_baskets": False,
                                "max_underlyings": 2}}, "storage": {"data_dir": "data"}}
    monkeypatch.setattr(universe.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(universe.config, "load", lambda: cfg)
    assert module.main(["--as-of", "2026-09-28", "--target-stocks", "3",
                        "--max-total-roots", "8", "--priority", "CCC"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["symbols"] == ["SPY", "AAPL", "CCC", "AAA"]
    assert result["source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["source"]["mode"] == "file_snapshot"
    assert result["qualified_stock_count"] is None
    assert result["collection_started"] is False
    assert result["configuration_changed"] is False
    assert source.read_bytes() == raw
    assert "daily_expansion" not in cfg["polygon"]["gex"]
    assert sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*")) == [
        "universe", "universe/membership.parquet"]


def test_cli_missing_source_returns_named_refusal_and_does_not_create_data(monkeypatch, tmp_path, capsys):
    import json
    module = cli()
    monkeypatch.setattr(universe.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(universe.config, "load", lambda: {"polygon": {"gex": {"symbols": ["SPY"]}}})
    assert module.main(["--as-of", "2026-09-28", "--target-stocks", "1000",
                        "--max-total-roots", "1500"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "refused"
    assert result["reason"] == "membership_unavailable"
    assert result["collection_started"] is False
    assert list(tmp_path.iterdir()) == []


def test_cli_previews_without_executing_already_enabled_configuration(monkeypatch, tmp_path, capsys):
    import json
    module = cli()
    (tmp_path / "universe").mkdir()
    membership("AAPL", "AAA", "BBB").to_parquet(tmp_path / "universe" / "membership.parquet", index=False)
    cfg = {"polygon": {"gex": {"symbols": ["SPY", "AAPL"], "daily_expansion": {
        "enabled": True, "target_stocks": 1500, "max_total_roots": 2000}}}}
    monkeypatch.setattr(universe.config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(universe.config, "load", lambda: cfg)
    assert module.main(["--as-of", "2026-09-28", "--target-stocks", "3",
                        "--max-total-roots", "8"]) == 0
    assert json.loads(capsys.readouterr().out)["selected_stock_count"] == 3
    assert cfg["polygon"]["gex"]["daily_expansion"]["target_stocks"] == 1500


def test_legacy_basket_cap_and_order_are_unchanged_when_expansion_is_absent(monkeypatch):
    monkeypatch.setattr(universe, "baskets_universe", lambda: ["AAA", "AAPL", "BBB"])
    assert universe.gex_symbols({"symbols": ["SPY", "AAPL"], "include_baskets": True,
                                 "max_underlyings": 3}) == ["SPY", "AAPL", "AAA"]


def test_plan_does_not_mutate_injected_membership():
    ledger = membership("aapl", "AAA", "BBB")
    before = ledger.copy(deep=True)
    plan(ledger=ledger)
    pd.testing.assert_frame_equal(ledger, before)


@pytest.mark.parametrize("first,last", [(None, "2026-09-28"), ("2026-09-01", None),
                                          ("2026-09-29", "2026-09-25")])
def test_invalid_membership_intervals_cannot_be_silently_dropped(first, last):
    ledger = pd.concat([membership("AAPL", "AAA", "BBB"),
                        membership("BROKEN", first=first, last=last)], ignore_index=True)
    with pytest.raises(ValueError, match="membership_invalid"):
        plan(settings(target=1), ledger=ledger)


def test_duplicate_membership_columns_have_a_named_source_refusal():
    ledger = membership("AAPL", "AAA", "BBB")
    ledger = pd.concat([ledger, ledger[["ticker"]]], axis=1)
    with pytest.raises(ValueError, match="membership_invalid"):
        plan(ledger=ledger)


def test_conflicting_explicit_sessions_are_refused():
    cfg = settings(); cfg["as_of"] = "2026-09-25"
    with pytest.raises(ValueError, match="invalid_session"):
        plan(cfg)
