"""Tests for the skew methodology-parity audit.

Every path is under tmp_path. The real ThetaData store and the live skew
ledger are never opened. Pure helpers are exercised on synthetic frames.
The CLI test builds a tiny ledger and a fake store, then runs the module.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "audit_options_skew_parity.py"
PIN_LINE = "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))"


def _load_audit():
    spec = importlib.util.spec_from_file_location(
        "audit_options_skew_parity_under_test", AUDIT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def audit():
    return _load_audit()


def _row(**overrides) -> dict:
    base = {
        "date": "2026-06-22",
        "underlying": "AMD",
        "legacy_skew": 0.10,
        "new_skew": 0.10,
        "legacy_put": 0.40,
        "new_put": 0.40,
        "legacy_call": 0.30,
        "new_call": 0.30,
        "legacy_tenor": 30.0,
        "new_tenor": 30.0,
        "legacy_spot": 100.0,
        "new_spot": 100.0,
        "legacy_n_strikes": 10.0,
        "new_n_strikes": 4.0,
        "store_oi": 100.0,
        "store_volume": 40.0,
    }
    base.update(overrides)
    return base


# ── classification ───────────────────────────────────────────────────────────


def test_weekend_wins_even_when_the_store_has_the_key(audit):
    """Saturday and Sunday are weekend_date before any store check."""
    for day in ("2026-06-20", "2026-06-21"):
        assert audit.classify_key(
            day, "SPY", root_in_store=True, date_in_store=True, price_status="compared",
        ) == "weekend_date"


def test_absence_order_is_root_then_date_then_price(audit):
    assert audit.classify_key(
        "2026-06-22", "ZZZZ", root_in_store=False, date_in_store=False, price_status=None,
    ) == "root_not_in_store"
    assert audit.classify_key(
        "2026-06-22", "SPY", root_in_store=True, date_in_store=False, price_status=None,
    ) == "date_not_in_store_for_root"
    assert audit.classify_key(
        "2026-06-22", "SPY", root_in_store=True, date_in_store=True, price_status="no_usable_tenor",
    ) == "no_usable_tenor"
    assert audit.classify_key(
        "2026-06-22", "DIA", root_in_store=True, date_in_store=True, price_status="other",
    ) == "other"
    assert audit.classify_key(
        "2026-06-22", "SPY", root_in_store=True, date_in_store=True, price_status="compared",
    ) == "compared"


def test_present_key_requires_a_price_status(audit):
    with pytest.raises(ValueError):
        audit.classify_key(
            "2026-06-22", "SPY", root_in_store=True, date_in_store=True, price_status=None,
        )


def test_tenor_and_spot_flags_use_the_stated_thresholds(audit):
    assert audit.tenor_mismatch(30.0, 35.0) is False
    assert audit.tenor_mismatch(30.0, 35.1) is True
    assert audit.spot_mismatch(100.0, 102.0) is False
    assert audit.spot_mismatch(100.0, 103.0) is True
    assert audit.spot_mismatch(0.0, 0.0) is False
    assert audit.spot_mismatch(0.0, 1.0) is True


def test_sign_buckets_cover_every_pair(audit):
    assert audit.sign_bucket(0.1, 0.2) == "match"
    assert audit.sign_bucket(-0.1, -0.2) == "match"
    assert audit.sign_bucket(0.1, -0.2) == "flip"
    assert audit.sign_bucket(0.0, 0.0) == "zero"
    assert audit.sign_bucket(0.0, 0.2) == "zero"
    assert audit.sign_bucket(-0.2, 0.0) == "zero"


def test_legacy_source_treats_blank_as_polygon_and_drops_thetadata(audit):
    assert audit.is_legacy_source(None) is True
    assert audit.is_legacy_source("polygon_gex") is True
    assert audit.is_legacy_source("") is True
    assert audit.is_legacy_source(float("nan")) is True
    assert audit.is_legacy_source("thetadata") is False


def test_tenor_unusable_only_when_nothing_is_still_alive(audit):
    alive = pd.DataFrame({"T": [0.0, 30 / 365.0]})
    dead = pd.DataFrame({"T": [0.0, 0.0]})
    assert audit.tenor_is_unusable(alive) is False
    assert audit.tenor_is_unusable(dead) is True
    assert audit.tenor_is_unusable(pd.DataFrame()) is False
    assert audit.tenor_is_unusable(None) is False


# ── decomposition and stratification ─────────────────────────────────────────


def _hand_compared() -> list[dict]:
    """Five compared keys with a known gap split. Absolute gaps sum to 0.57."""
    return [
        _row(underlying="SPY", legacy_skew=0.10, new_skew=0.25,
             legacy_put=0.40, new_put=0.55, legacy_call=0.30, new_call=0.30,
             legacy_n_strikes=10),
        _row(underlying="QQQ", legacy_skew=-0.05, new_skew=0.10,
             legacy_put=0.20, new_put=0.40, legacy_call=0.25, new_call=0.30,
             legacy_n_strikes=20),
        _row(underlying="AMD", legacy_skew=0.10, new_skew=-0.10,
             legacy_put=0.30, new_put=0.30, legacy_call=0.20, new_call=0.40,
             legacy_spot=50.0, new_spot=50.0, legacy_n_strikes=30),
        _row(underlying="NVDA", legacy_skew=0.10, new_skew=0.12,
             legacy_put=0.40, new_put=0.42, legacy_call=0.30, new_call=0.30,
             legacy_spot=100.0, new_spot=110.0, legacy_n_strikes=40),
        _row(underlying="TSLA", legacy_skew=0.10, new_skew=0.15,
             legacy_put=0.40, new_put=0.45, legacy_call=0.30, new_call=0.30,
             legacy_tenor=30.0, new_tenor=10.0, legacy_spot=200.0, new_spot=200.0,
             legacy_n_strikes=50),
    ]


def test_decompose_assigns_each_absolute_gap_once(audit):
    out = audit.decompose_compared(_hand_compared())
    assert out["n"] == 5
    assert out["explained_share_put_leg"] == pytest.approx(0.30 / 0.57, abs=1e-6)
    assert out["explained_share_call_leg"] == pytest.approx(0.20 / 0.57, abs=1e-6)
    assert out["explained_share_spot"] == pytest.approx(0.02 / 0.57, abs=1e-6)
    assert out["explained_share_tenor"] == pytest.approx(0.05 / 0.57, abs=1e-6)
    shares = [
        out["explained_share_put_leg"], out["explained_share_call_leg"],
        out["explained_share_tenor"], out["explained_share_spot"],
    ]
    assert sum(shares) == pytest.approx(1.0)
    assert out["n_assigned_put"] == 2
    assert out["n_assigned_call"] == 1
    assert out["n_assigned_spot"] == 1
    assert out["n_assigned_tenor"] == 1
    assert out["n_tenor_mismatch"] == 1
    assert out["n_spot_mismatch"] == 1
    assert out["n_both_mismatch"] == 0
    assert out["p50"] == pytest.approx(0.15)
    assert out["max"] == pytest.approx(0.20)
    # The two IV contributions add back to the stored gap when rounding is exact.
    assert out["sum_put_contribution"] + out["sum_call_contribution"] == pytest.approx(out["sum_delta"])
    assert out["max_identity_residual"] == pytest.approx(0.0)


def test_both_flags_count_as_tenor_not_twice(audit):
    rows = [_row(
        legacy_skew=0.20, new_skew=0.00,
        legacy_put=0.50, new_put=0.30, legacy_call=0.30, new_call=0.30,
        legacy_tenor=30.0, new_tenor=10.0, legacy_spot=100.0, new_spot=120.0,
    )]
    out = audit.decompose_compared(rows)
    assert out["n_tenor_mismatch"] == 1
    assert out["n_spot_mismatch"] == 1
    assert out["n_both_mismatch"] == 1
    assert out["explained_share_tenor"] == pytest.approx(1.0)
    assert out["explained_share_spot"] == pytest.approx(0.0)
    assert out["n_assigned_tenor"] == 1
    assert out["n_assigned_spot"] == 0


def test_decompose_empty_is_defined_and_does_not_divide_by_zero(audit):
    out = audit.decompose_compared([])
    assert out["n"] == 0
    assert out["explained_share_put_leg"] is None
    assert out["abs_put_movement_share"] is None
    assert out["p50"] is None


def test_stratify_reports_honest_n_for_class_and_liquidity(audit):
    rows = _hand_compared()
    # One compared key has no stored open interest and no volume.
    rows.append(_row(
        underlying="MSFT", date="2026-06-23", legacy_n_strikes=60,
        legacy_skew=0.05, new_skew=-0.05, store_oi=None, store_volume=None,
        legacy_put=0.20, new_put=0.20, legacy_call=0.15, new_call=0.25,
    ))
    out = audit.stratify_compared(rows)
    assert sum(row["n"] for row in out["by_class"]) == 6
    classes = {row["stratum"]: row for row in out["by_class"]}
    assert classes["index_etf"]["n"] == 2
    assert classes["single_name"]["n"] == 4
    for row in out["by_class"]:
        assert row["n_sign_match"] + row["n_sign_flip"] + row["n_zero"] == row["n"]
    assert sum(row["n"] for row in out["by_n_strikes_quartile"]) == 6
    assert sum(row["n"] for row in out["by_store_oi_quartile"]) == 6
    assert sum(row["n"] for row in out["by_store_volume_quartile"]) == 6
    oi_names = [row["stratum"] for row in out["by_store_oi_quartile"]]
    assert "oi_unavailable" in oi_names
    unavailable = next(row for row in out["by_store_oi_quartile"] if row["stratum"] == "oi_unavailable")
    assert unavailable["n"] == 1


def test_stratified_sample_keeps_each_stratum_and_is_stable(audit):
    weekdays = []
    day = date(2026, 6, 22)
    while len(weekdays) < 10:
        if day.weekday() < 5:
            weekdays.append(day.isoformat())
        day += timedelta(days=1)
    keys = []
    for index, day_iso in enumerate(weekdays):
        keys.append({"date": day_iso, "underlying": "SPY"})
        keys.append({"date": day_iso, "underlying": f"N{index:02d}"})
        keys.append({"date": "2026-06-20", "underlying": f"W{index:02d}"})
    first = audit.stratified_sample(keys, 6, seed=20260923)
    second = audit.stratified_sample(keys, 6, seed=20260923)
    assert first == second
    assert len(first) == 6
    kinds = []
    for key in first:
        klass = "index" if key["underlying"] == "SPY" else "single"
        when = "weekend" if key["date"] == "2026-06-20" else "weekday"
        kinds.append((klass, when))
    assert kinds.count(("index", "weekday")) == 2
    assert kinds.count(("single", "weekday")) == 2
    assert kinds.count(("single", "weekend")) == 2
    assert audit.stratified_sample(keys, 1000) == list(keys)


# ── CLI on a fake store ──────────────────────────────────────────────────────


def _contract_rows(root, on, expiry, spot, put_iv, call_iv, oi=50.0, volume=10.0):
    strikes = [round(spot * factor, 4) for factor in (0.90, 0.95, 1.0, 1.05)]
    rights = ["P", "P", "C", "C"]
    deltas = [-0.10, -0.25, 0.50, 0.25]
    ivs = [put_iv + 0.05, put_iv, call_iv, call_iv - 0.02]
    eod, oi_rows, greeks = [], [], []
    for strike, right, delta, iv in zip(strikes, rights, deltas, ivs):
        eod.append(dict(
            root=root, expiration=expiry, strike=strike, right=right, date=on,
            open=1.0, high=1.0, low=1.0, close=1.0, volume=volume, count=1,
            bid=0.9, ask=1.1,
        ))
        oi_rows.append(dict(
            root=root, expiration=expiry, strike=strike, right=right, date=on,
            open_interest=oi,
        ))
        greeks.append(dict(
            root=root, expiration=expiry, strike=strike, right=right, date=on,
            bid=0.9, ask=1.1, underlying_price=spot, delta=delta,
            theta=0.0, vega=0.0, rho=0.0, implied_vol=iv, iv_error=0.0,
        ))
    return eod, oi_rows, greeks


def _write_store(store: Path, specs: list[dict]) -> None:
    buckets: dict[tuple[str, str], list[dict]] = {}
    for spec in specs:
        eod, oi_rows, greeks = _contract_rows(
            spec["root"], spec["date"], spec["expiry"], spec["spot"],
            spec["put_iv"], spec["call_iv"],
        )
        year = spec["date"][:4]
        buckets.setdefault(("eod", spec["root"], year), []).extend(eod)
        if spec.get("oi", True):
            buckets.setdefault(("oi", spec["root"], year), []).extend(oi_rows)
        if spec.get("greeks", True):
            buckets.setdefault(("greeks", spec["root"], year), []).extend(greeks)
    for (tier, root, year), rows in buckets.items():
        path = store / tier / root / f"{year}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_parquet(path, index=False)


def _ledger_row(on, underlying, *, source="polygon_gex", skew=0.10, put=0.40, call=0.30,
                tenor=30.0, spot=100.0, n_strikes=10) -> dict:
    return {
        "date": on, "underlying": underlying, "asof": on, "spot": spot,
        "tenor_days": tenor, "otm_put_iv": put, "atm_call_iv": call,
        "skew": skew, "n_strikes": n_strikes, "source": source,
    }


def _synthetic(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Ledger + store covering every class, with the five compared shapes above."""
    store = tmp_path / "store"
    _write_store(store, [
        # Sunday is in the store and would price, but the ledger date is a weekend.
        dict(root="SPY", date="2026-06-21", expiry="2026-07-21", spot=100.0, put_iv=0.55, call_iv=0.30),
        dict(root="SPY", date="2026-06-22", expiry="2026-07-22", spot=100.0, put_iv=0.55, call_iv=0.30),
        dict(root="QQQ", date="2026-06-22", expiry="2026-07-22", spot=100.0, put_iv=0.40, call_iv=0.30),
        dict(root="AMD", date="2026-06-22", expiry="2026-07-22", spot=50.0, put_iv=0.30, call_iv=0.40),
        dict(root="NVDA", date="2026-06-22", expiry="2026-07-22", spot=110.0, put_iv=0.42, call_iv=0.30),
        dict(root="TSLA", date="2026-06-22", expiry="2026-07-02", spot=200.0, put_iv=0.45, call_iv=0.30),
        dict(root="IWM", date="2026-06-22", expiry="2026-06-22", spot=100.0, put_iv=0.40, call_iv=0.30),
        dict(root="DIA", date="2026-06-22", expiry="2026-07-22", spot=100.0, put_iv=0.40, call_iv=0.30,
             greeks=False, oi=False),
    ])
    ledger = tmp_path / "ledger" / "snapshots.parquet"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        _ledger_row("2026-06-20", "SPY"),  # Saturday, and the store has no such day
        _ledger_row("2026-06-21", "SPY"),  # Sunday, store could price it
        _ledger_row("2026-06-22", "SPY", skew=0.10, put=0.40, call=0.30, n_strikes=10),
        _ledger_row("2026-08-03", "SPY"),  # root exists, this Monday is absent
        _ledger_row("2026-06-22", "QQQ", skew=-0.05, put=0.20, call=0.25, n_strikes=20),
        _ledger_row("2026-06-22", "AMD", skew=0.10, put=0.30, call=0.20, spot=50.0, n_strikes=30),
        _ledger_row("2026-06-22", "NVDA", skew=0.10, put=0.40, call=0.30, n_strikes=40),
        _ledger_row("2026-06-22", "TSLA", skew=0.10, put=0.40, call=0.30, spot=200.0, n_strikes=50),
        _ledger_row("2026-06-22", "ZZZZ"),
        _ledger_row("2026-06-22", "IWM"),
        _ledger_row("2026-06-22", "DIA"),
        _ledger_row("2026-06-22", "AAPL", source="thetadata"),
    ]
    pd.DataFrame(rows).to_parquet(ledger, index=False)
    out = tmp_path / "out" / "receipt.md"
    return ledger, store, out


def _run(audit, ledger: Path, store: Path, out: Path, limit: int | None = None,
         store_flag: bool = True, env_store: Path | None = None) -> tuple[int, dict, str]:
    argv = ["--ledger", str(ledger), "--out", str(out)]
    if store_flag:
        argv.extend(["--store", str(store)])
    if limit is not None:
        argv.extend(["--limit", str(limit)])
    previous = os.environ.get("THETADATA_STORE")
    if env_store is not None:
        os.environ["THETADATA_STORE"] = str(env_store)
    elif "THETADATA_STORE" in os.environ:
        # Do not let the host store become the default during an in-process run.
        os.environ["THETADATA_STORE"] = str(store)
    try:
        code = audit.main(argv)
    finally:
        if previous is None:
            os.environ.pop("THETADATA_STORE", None)
        else:
            os.environ["THETADATA_STORE"] = previous
    text = out.read_text(encoding="utf-8") if out.exists() else ""
    payload = json.loads(text.strip().splitlines()[-1]) if text.strip() else {}
    return code, payload, text


def test_cli_classifies_and_decomposes_a_fake_store(audit, tmp_path):
    ledger, store, out = _synthetic(tmp_path)
    # The environment points at an empty directory. --store must win.
    code, payload, text = _run(
        audit, ledger, store, out, env_store=tmp_path / "empty-env-store",
    )
    assert code == 0
    assert payload["reconciles"] is True
    assert payload["legacy_keys"] == 11
    assert payload["weekend_date"] == 2
    assert payload["root_not_in_store"] == 1
    assert payload["date_not_in_store_for_root"] == 1
    assert payload["no_usable_tenor"] == 1
    assert payload["other"] == 1
    assert payload["compared"] == 5
    assert payload["n_sign_match"] == 3
    assert payload["n_sign_flip"] == 2
    assert payload["n_zero"] == 0
    assert payload["n_sign_match"] + payload["n_sign_flip"] + payload["n_zero"] == 5
    assert payload["explained_share_put_leg"] == pytest.approx(0.30 / 0.57, abs=1e-6)
    assert payload["explained_share_call_leg"] == pytest.approx(0.20 / 0.57, abs=1e-6)
    assert payload["explained_share_tenor"] == pytest.approx(0.05 / 0.57, abs=1e-6)
    assert payload["explained_share_spot"] == pytest.approx(0.02 / 0.57, abs=1e-6)
    assert payload["chosen_k_exposed"] is False
    assert payload["sign_agreement_rate"] == pytest.approx(0.6)
    classes = {row["stratum"]: row["n"] for row in payload["by_class"]}
    assert classes == {"index_etf": 2, "single_name": 3}
    assert sum(row["n"] for row in payload["by_n_strikes_quartile"]) == 5
    assert sum(row["n"] for row in payload["by_store_oi_quartile"]) == 5
    assert "oi_unavailable" not in {row["stratum"] for row in payload["by_store_oi_quartile"]}
    assert str(store) in text
    assert "0.250000" in text
    assert "does not return the strike it picked" in text
    # The only file written under the output directory is the receipt.
    assert sorted(path.name for path in out.parent.iterdir()) == ["receipt.md"]


def test_cli_store_flag_beats_the_environment(audit, tmp_path):
    ledger, store, out = _synthetic(tmp_path)
    code, payload, _text = _run(
        audit, ledger, store, out, env_store=tmp_path / "wrong-store",
    )
    assert code == 0
    assert payload["compared"] == 5


def test_cli_defaults_store_to_the_environment_when_the_flag_is_omitted(audit, tmp_path):
    ledger, store, out = _synthetic(tmp_path)
    code, payload, text = _run(
        audit, ledger, store, out, store_flag=False, env_store=store,
    )
    assert code == 0
    assert payload["compared"] == 5
    assert str(store) in text


def test_cli_limit_is_a_stable_stratified_sample(audit, tmp_path):
    ledger, store, first_out = _synthetic(tmp_path)
    second_out = tmp_path / "out" / "receipt-2.md"
    code_a, payload_a, _ = _run(audit, ledger, store, first_out, limit=4)
    code_b, payload_b, _ = _run(audit, ledger, store, second_out, limit=4)
    assert code_a == 0 and code_b == 0
    assert payload_a["legacy_keys"] == 4
    assert payload_a["population_keys"] == 11
    assert payload_a["limit"] == 4
    assert payload_a["sample_seed"] == 20260923
    assert payload_a["reconciles"] is True
    assert payload_a == payload_b
    assert "not the full ledger" in first_out.read_text(encoding="utf-8")


def test_cli_missing_ledger_and_empty_legacy_are_distinct(audit, tmp_path, capsys):
    missing = tmp_path / "no-such.parquet"
    assert audit.main(["--ledger", str(missing), "--store", str(tmp_path), "--out", str(tmp_path / "a.md")]) == 3
    ledger = tmp_path / "only-new.parquet"
    pd.DataFrame([_ledger_row("2026-06-22", "AAPL", source="thetadata")]).to_parquet(ledger, index=False)
    assert audit.main([
        "--ledger", str(ledger), "--store", str(tmp_path), "--out", str(tmp_path / "b.md"),
    ]) == 2
    assert not (tmp_path / "a.md").exists()
    assert not (tmp_path / "b.md").exists()


def test_module_entrypoint_writes_only_the_requested_receipt(tmp_path):
    ledger, store, out = _synthetic(tmp_path)
    env = os.environ.copy()
    env["THETADATA_STORE"] = str(tmp_path / "wrong-store")
    completed = subprocess.run(
        [sys.executable, "-m", "scripts.audit_options_skew_parity",
         "--ledger", str(ledger), "--store", str(store), "--out", str(out)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload["legacy_keys"] == 11
    assert payload["compared"] == 5
    assert payload["reconciles"] is True
    assert out.is_file()
    assert sorted(path.name for path in out.parent.iterdir()) == ["receipt.md"]


def test_script_pins_the_repo_root_and_does_not_name_live_lane_dirs():
    source = AUDIT.read_text(encoding="utf-8")
    assert source.count(PIN_LINE) == 1
    assert "skew-ops-wt" not in source
    assert "skew-ops-state" not in source
    assert "publish_r2" not in source
    assert "open(" not in source
    # The pin is the only sys.path edit, and it is the one the spec requires.
    assert source.count("sys.path.insert") == 1
