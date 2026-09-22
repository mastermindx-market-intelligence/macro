"""Pure-function tests for engine/options_skew.py — single-name IV skew (display-only)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json  # noqa: E402
from datetime import date  # noqa: E402

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from engine import options_skew as S  # noqa: E402


def _chain(underlying="XYZ", spot=100.0, put_iv=0.40, call_iv=0.30, days=30):
    """A minimal two-expiry chain: a near-target ~30d expiry + a far one to exercise
    expiry selection. Puts carry put_iv, calls call_iv → skew = put_iv - call_iv."""
    T = days / 365.0
    rows = []
    for exp, t in [("2026-07-21", T), ("2027-01-21", T * 6)]:
        # OTM put at delta ~-0.25 (K below spot) and ATM call at delta ~0.5 (K≈spot)
        rows += [
            dict(underlying=underlying, expiry=exp, K=spot * 0.95, T=t, is_call=False,
                 iv=put_iv, delta=-0.25, oi=100, gamma=0.01, volume=10, spot=spot, asof="2026-06-21"),
            dict(underlying=underlying, expiry=exp, K=spot * 0.90, T=t, is_call=False,
                 iv=put_iv + 0.05, delta=-0.10, oi=50, gamma=0.01, volume=5, spot=spot, asof="2026-06-21"),
            dict(underlying=underlying, expiry=exp, K=spot, T=t, is_call=True,
                 iv=call_iv, delta=0.50, oi=100, gamma=0.01, volume=10, spot=spot, asof="2026-06-21"),
            dict(underlying=underlying, expiry=exp, K=spot * 1.05, T=t, is_call=True,
                 iv=call_iv - 0.02, delta=0.25, oi=50, gamma=0.01, volume=5, spot=spot, asof="2026-06-21"),
        ]
    return pd.DataFrame(rows)


def test_compute_skew_put_over_call():
    m = S.compute_skew(_chain(put_iv=0.40, call_iv=0.30))
    assert m is not None
    assert abs(m["otm_put_iv"] - 0.40) < 1e-9 and abs(m["atm_call_iv"] - 0.30) < 1e-9
    assert abs(m["skew"] - 0.10) < 1e-9                 # +0.10 put-over-call skew
    assert 25 <= m["tenor_days"] <= 35                  # picked the ~30d expiry, not the far one


def test_compute_skew_negative_when_call_rich():
    m = S.compute_skew(_chain(put_iv=0.28, call_iv=0.34))
    assert m["skew"] < 0                                 # call IV > put IV → negative skew


def test_skew_map_multi_underlying():
    chain = pd.concat([_chain("AAA", put_iv=0.5, call_iv=0.3),
                       _chain("BBB", put_iv=0.3, call_iv=0.35)], ignore_index=True)
    mp = S.skew_map(chain)
    assert set(mp) == {"AAA", "BBB"}
    assert mp["AAA"]["skew"] > 0 and mp["BBB"]["skew"] < 0


def test_compute_skew_degrades_empty():
    assert S.compute_skew(pd.DataFrame()) is None
    assert S.compute_skew(None) is None
    assert S.skew_map(None) == {}


def test_build_snapshot_is_context_only(monkeypatch, tmp_path):
    # no gate file, no store → dormant 'measuring' state, never scored
    monkeypatch.delenv("THETADATA_STORE", raising=False)
    monkeypatch.setattr("engine.thetadata_store.resolve_thetadata_store",
                        lambda **kw: None)
    pay = S.build_snapshot()
    assert pay["is_context_only"] is True
    assert pay["scored"] is False
    assert pay["schema"] == S.SCHEMA


# --------------------------------------------------------------------------- #
# ThetaData chain store migration (A-F03-W2-1)
# --------------------------------------------------------------------------- #

def _write_theta_store(tmp_path, root="XYZ", date="2026-06-21", expiry="2026-07-21",
                        spot=100.0, put_iv=0.40, call_iv=0.30):
    """Synthetic ThetaData store: eod + oi + greeks tiers for one root/year,
    documented columns per engine/thetadata_store.py:8-12."""
    pa = pytest.importorskip("pyarrow")  # noqa: F841
    year = date[:4]
    strikes = [90.0, 95.0, 100.0, 105.0]
    rights = ["P", "P", "C", "C"]
    deltas = [-0.10, -0.25, 0.50, 0.25]
    ivs = [put_iv + 0.05, put_iv, call_iv, call_iv - 0.02]

    eod_rows, oi_rows, greeks_rows = [], [], []
    for k, r, d, iv in zip(strikes, rights, deltas, ivs):
        eod_rows.append(dict(root=root, expiration=expiry, strike=k, right=r, date=date,
                              open=1.0, high=1.0, low=1.0, close=1.0, volume=10, count=1,
                              bid=0.9, ask=1.1))
        oi_rows.append(dict(root=root, expiration=expiry, strike=k, right=r, date=date,
                             open_interest=50))
        greeks_rows.append(dict(root=root, expiration=expiry, strike=k, right=r, date=date,
                                 bid=0.9, ask=1.1, underlying_price=spot, delta=d,
                                 theta=0.0, vega=0.0, rho=0.0, epsilon=0.0, lambda_=0.0,
                                 implied_vol=iv, iv_error=0.0))

    for tier, rows in (("eod", eod_rows), ("oi", oi_rows), ("greeks", greeks_rows)):
        d = tmp_path / tier / root
        d.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_parquet(d / f"{year}.parquet")
    return tmp_path


def test_thetadata_chain_positive(tmp_path):
    store = _write_theta_store(tmp_path, root="XYZ", put_iv=0.40, call_iv=0.30)
    frame, state = S.load_chain(asof="2026-06-21", store=store, roots=["XYZ"])
    assert state == "ok"
    assert frame is not None
    for col in ["underlying", "expiry", "K", "T", "iv", "delta", "is_call",
                "spot", "oi", "volume", "asof"]:
        assert col in frame.columns
    m = S.skew_map(frame)
    assert m["XYZ"]["skew"] == pytest.approx(0.10, abs=1e-6)
    assert 25 <= m["XYZ"]["tenor_days"] <= 35


def test_missing_chain_is_typed_null(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("THETADATA_STORE", raising=False)
    # Empty store dir → unresolved (no eod/oi/greeks subdirs at all).
    monkeypatch.setattr("engine.thetadata_store.resolve_thetadata_store",
                        lambda **kw: None)
    pay = S.build_snapshot()
    assert pay["names"] == {} and pay["n"] == 0 and pay["source"] is None
    assert pay["source_state"] == "thetadata_store_unresolved"
    out = capsys.readouterr().out
    assert any(line.startswith("::warning") for line in out.splitlines())

    # store with eod/ but no greeks/ → no_iv_tier
    store = tmp_path / "eodonly"
    (store / "eod" / "XYZ").mkdir(parents=True)
    frame, state = S.load_chain(store=store)
    assert frame is None and state == "no_iv_tier"

    assert all(v is not None for v in [pay["source_state"], pay["names"], pay["ranked"]])
    assert pay["source_state"] != "ok"


def test_stale_chain_is_typed_null(tmp_path, capsys, monkeypatch):
    from datetime import date as _date
    store = _write_theta_store(tmp_path, root="XYZ", date="2026-06-21")
    monkeypatch.setattr("engine.thetadata_store.resolve_thetadata_store",
                        lambda **kw: store)
    pay = S.build_snapshot(today=_date(2026, 7, 21))  # 30 days after the chain's asof
    assert pay["source_state"] == "stale_chain"
    assert pay["source_detail"]["stale_days"] >= 25
    out = capsys.readouterr().out
    assert any(line.startswith("::warning") for line in out.splitlines())


def test_legacy_path_not_globbed_by_default(monkeypatch):
    import glob as glob_mod
    monkeypatch.delenv(S._LEGACY_CHAIN_ENV, raising=False)
    monkeypatch.setattr("engine.thetadata_store.resolve_thetadata_store",
                        lambda **kw: None)

    def _boom(*a, **kw):
        raise AssertionError("legacy path reached")
    monkeypatch.setattr(glob_mod, "glob", _boom)

    # must not raise: the legacy glob is never reached when the flag is unset
    S.build_snapshot()

    monkeypatch.setenv(S._LEGACY_CHAIN_ENV, "1")
    with pytest.raises(AssertionError, match="legacy path reached"):
        S._legacy_chain()


def test_thetadata_and_legacy_overlap(tmp_path, monkeypatch):
    """Cross-source equivalence: the same underlying facts fed through the legacy
    polygon_gex schema and the ThetaData schema must drive the identical formula
    to the same sign and comparable magnitude."""
    spot, put_iv, call_iv = 100.0, 0.40, 0.30

    legacy_rows = [
        dict(underlying="XYZ", strike_ticker="O:XYZ", expiry="2026-07-21", K=95.0,
             T=30 / 365.0, is_call=False, oi=100, iv=put_iv, gamma=0.01, delta=-0.25,
             volume=10, spot=spot, asof="2026-06-21"),
        dict(underlying="XYZ", strike_ticker="O:XYZ", expiry="2026-07-21", K=90.0,
             T=30 / 365.0, is_call=False, oi=50, iv=put_iv + 0.05, gamma=0.01,
             delta=-0.10, volume=5, spot=spot, asof="2026-06-21"),
        dict(underlying="XYZ", strike_ticker="O:XYZ", expiry="2026-07-21", K=100.0,
             T=30 / 365.0, is_call=True, oi=100, iv=call_iv, gamma=0.01, delta=0.50,
             volume=10, spot=spot, asof="2026-06-21"),
        dict(underlying="XYZ", strike_ticker="O:XYZ", expiry="2026-07-21", K=105.0,
             T=30 / 365.0, is_call=True, oi=50, iv=call_iv - 0.02, gamma=0.01,
             delta=0.25, volume=5, spot=spot, asof="2026-06-21"),
    ]
    legacy_chain = pd.DataFrame(legacy_rows)
    skew_legacy = S.compute_skew(legacy_chain)["skew"]

    store = _write_theta_store(tmp_path, root="XYZ", put_iv=put_iv, call_iv=call_iv)
    frame, state = S.load_chain(asof="2026-06-21", store=store, roots=["XYZ"])
    assert state == "ok"
    skew_theta = S.skew_map(frame)["XYZ"]["skew"]

    import math
    assert math.copysign(1, skew_legacy) == math.copysign(1, skew_theta)
    assert abs(skew_legacy - skew_theta) < 0.01


def test_null_is_never_zero(tmp_path, monkeypatch):
    for resolver in (lambda **kw: None,):
        monkeypatch.setattr("engine.thetadata_store.resolve_thetadata_store", resolver)
        pay = S.build_snapshot()
        assert pay["source_state"] != "ok"
        assert "skew" not in json.dumps(pay["names"])
        assert pay["ranked"] == []


# --------------------------------------------------------------------------- #
# Regression: _fwd_ic must emit a finite, non-NaN HAC t-stat                  #
# --------------------------------------------------------------------------- #

def test_fwd_ic_hac_t_is_finite_not_nan():
    """Regression guard for the t_hac key bug.

    Before the fix, _fwd_ic used summ.get("t", summ.get("hac_t", ...)) which
    always produces NaN because ic_summary() returns the key 't_hac', not 't'
    or 'hac_t'.  This test creates a synthetic panel large enough to pass the
    6-IC floor in ic_summary and asserts the returned 'hac_t' is a finite float.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    import numpy as np
    import pandas as pd

    # Build a synthetic panel with a strong positive monotone signal so that
    # rank-IC is reliably non-NaN and the HAC t-stat is large.
    dates = [f"2020-01-{i+2:02d}" for i in range(25)]
    underlyings = [f"SYM{j:02d}" for j in range(15)]

    rows = []
    spot_base = 100.0
    for i, d in enumerate(dates):
        for j, u in enumerate(underlyings):
            # Monotone drift so spots increase — gives clean forward returns
            rows.append({"date": d, "underlying": u,
                         "skew": float(j) / 14.0,  # cross-sectional rank matches j
                         "spot": spot_base + i * 0.5 + j * 0.1})
    panel = pd.DataFrame(rows)

    from scripts.validate_options_skew import _fwd_ic
    result = _fwd_ic(panel, h=5)

    assert result["n_dates"] > 0, "Expected non-zero IC dates from synthetic panel"
    hac_t = result.get("hac_t")
    assert hac_t is not None, "_fwd_ic did not return 'hac_t' key"
    assert np.isfinite(float(hac_t)), (
        f"hac_t is {hac_t!r} — expected a finite float. "
        "This indicates the t_hac key is still wrong (ic_summary returns 't_hac', "
        "not 't' or 'hac_t')."
    )


# --------------------------------------------------------------------------- #
# A-F03-W2-1b — ledger upsert, accrue/emit split, legacy pin on render hosts
# --------------------------------------------------------------------------- #

def _patch_dirs(monkeypatch, tmp_path):
    data = tmp_path / "data"
    site = tmp_path / "site"
    data.mkdir()
    site.mkdir()
    monkeypatch.setattr("lib.config.data_dir", lambda: data)
    monkeypatch.setattr("lib.config.site_dir", lambda: site)
    monkeypatch.delenv(S._LEGACY_CHAIN_ENV, raising=False)
    return data, site


def _ledger_row(underlying, date, skew, source=None):
    row = {
        "date": date,
        "underlying": underlying,
        "asof": date,
        "spot": 100.0,
        "tenor_days": 30.0,
        "otm_put_iv": round(0.30 + skew, 4),
        "atm_call_iv": 0.30,
        "skew": skew,
        "n_strikes": 8,
    }
    if source is not None:
        row["source"] = source
    return row


def _sha256(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_snapshot_upsert_canonical_wins_and_atomic_write(tmp_path, monkeypatch):
    """Missing source reads as polygon_gex; theta replaces it; polygon never replaces theta.

    The write goes through os.replace in the ledger's own directory. A failed
    temp write leaves the previous bytes in place.
    """
    import os

    data, _site = _patch_dirs(monkeypatch, tmp_path)
    ledger = data / "options_skew" / "snapshots.parquet"
    ledger.parent.mkdir(parents=True)
    pd.DataFrame([_ledger_row("XYZ", "2026-06-21", 0.10)]).to_parquet(ledger)

    # No source column → treated as polygon_gex, so a polygon upsert replaces it.
    replaced = S.snapshot(
        today=date(2026, 6, 21),
        chain=_chain("XYZ", put_iv=0.55, call_iv=0.30),
        source="polygon_gex",
    )
    assert replaced == 1
    after_polygon = pd.read_parquet(ledger)
    assert list(after_polygon["source"]) == ["polygon_gex"]
    assert after_polygon.iloc[0]["skew"] == pytest.approx(0.25, abs=1e-9)

    # Theta replaces polygon for the same (date, underlying).
    theta_n = S.snapshot(
        today=date(2026, 6, 21),
        chain=_chain("XYZ", put_iv=0.50, call_iv=0.30),
        source="thetadata",
    )
    assert theta_n == 1
    after_theta = pd.read_parquet(ledger)
    assert after_theta.iloc[0]["source"] == "thetadata"
    assert after_theta.iloc[0]["skew"] == pytest.approx(0.20, abs=1e-9)
    pinned = _sha256(ledger)

    calls = {}
    real_replace = os.replace

    def _spy(src, dst):
        calls["src"] = str(src)
        calls["dst"] = str(dst)
        assert Path(src).parent == Path(dst).parent
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", _spy)
    inserted = S.snapshot(
        today=date(2026, 6, 21),
        chain=_chain("AAA", put_iv=0.42, call_iv=0.30),
        source="polygon_gex",
    )
    assert inserted == 1
    assert calls["dst"] == str(ledger)
    assert Path(calls["src"]).name.startswith(".snapshots.parquet.")
    assert not Path(calls["src"]).exists()
    both = pd.read_parquet(ledger)
    by_name = {str(r.underlying): r for r in both.itertuples(index=False)}
    assert by_name["XYZ"].source == "thetadata"
    assert by_name["XYZ"].skew == pytest.approx(0.20, abs=1e-9)
    assert by_name["AAA"].source == "polygon_gex"

    # A polygon row must not replace the thetadata row, and must not rewrite the file.
    pinned = _sha256(ledger)
    blocked = S.snapshot(
        today=date(2026, 6, 21),
        chain=_chain("XYZ", put_iv=0.90, call_iv=0.30),
        source="polygon_gex",
    )
    assert blocked == 0
    assert _sha256(ledger) == pinned
    still = pd.read_parquet(ledger)
    xyz = still[still["underlying"].astype(str) == "XYZ"].iloc[0]
    assert xyz["source"] == "thetadata"
    assert xyz["skew"] == pytest.approx(0.20, abs=1e-9)

    # A failed temp write must not replace the ledger.
    pinned = _sha256(ledger)
    real_to_parquet = pd.DataFrame.to_parquet

    def _boom(self, path, *args, **kwargs):
        if ".tmp" in Path(path).name:
            raise OSError("temp write failed")
        return real_to_parquet(self, path, *args, **kwargs)

    monkeypatch.setattr(pd.DataFrame, "to_parquet", _boom)
    with pytest.raises(OSError, match="temp write failed"):
        S.snapshot(
            today=date(2026, 6, 22),
            chain=_chain("BBB", put_iv=0.45, call_iv=0.30),
            source="thetadata",
        )
    assert _sha256(ledger) == pinned
    assert not any(p.name.endswith(".tmp") for p in ledger.parent.iterdir())


def test_accrue_skips_unresolved_store_without_rewriting_ledger(tmp_path, monkeypatch, capsys):
    data, _site = _patch_dirs(monkeypatch, tmp_path)
    ledger = data / "options_skew" / "snapshots.parquet"
    ledger.parent.mkdir(parents=True)
    pd.DataFrame([_ledger_row("XYZ", "2026-06-21", 0.10)]).to_parquet(ledger)
    pinned = _sha256(ledger)
    monkeypatch.setattr(
        "engine.thetadata_store.resolve_thetadata_store", lambda **kw: None
    )
    from scripts.build_options_skew import main

    assert main(["--accrue"]) == 0
    assert _sha256(ledger) == pinned
    out = capsys.readouterr().out
    assert any(
        line.startswith("::warning title=options-skew-source::")
        for line in out.splitlines()
    )
    # --emit of that same untouched ledger still renders the stored row.
    assert main(["--emit"]) == 0
    assert _sha256(ledger) == pinned


def test_emit_renders_fixture_ledger_without_touching_the_chain(tmp_path, monkeypatch):
    data, site = _patch_dirs(monkeypatch, tmp_path)
    ledger = data / "options_skew" / "snapshots.parquet"
    ledger.parent.mkdir(parents=True)
    pd.DataFrame([
        _ledger_row("OLD", "2026-06-20", 0.01, source="polygon_gex"),
        _ledger_row("XYZ", "2026-06-21", 0.10, source="polygon_gex"),
    ]).to_parquet(ledger)
    pinned = _sha256(ledger)

    def _boom(*args, **kwargs):
        raise AssertionError("emit constructed a chain provider")

    monkeypatch.setattr("engine.thetadata_store.make_chain_provider", _boom)
    monkeypatch.setattr(S, "_legacy_chain", _boom)
    from scripts.build_options_skew import main

    assert main(["--emit"]) == 0
    assert _sha256(ledger) == pinned
    payload = json.loads((site / "options_skew" / "latest.json").read_text())
    assert payload["schema"] == "options_skew.v1"
    assert payload["accrual_state"] == "ledger_only"
    assert payload["ledger_asof"] == "2026-06-21"
    assert set(payload["names"]) == {"XYZ"}
    assert payload["names"]["XYZ"]["skew"] == pytest.approx(0.10, abs=1e-9)
    assert payload["n"] == 1
    for key in ("source", "source_state", "source_detail"):
        assert key in payload


def test_legacy_flag_reaches_legacy_path(tmp_path, monkeypatch):
    _patch_dirs(monkeypatch, tmp_path)
    monkeypatch.setenv(S._LEGACY_CHAIN_ENV, "1")
    seen = {}

    def _legacy():
        seen["legacy"] = True
        return _chain("XYZ", put_iv=0.40, call_iv=0.30)

    def _boom(*args, **kwargs):
        raise AssertionError("legacy flag still reached ThetaData")

    monkeypatch.setattr(S, "_legacy_chain", _legacy)
    monkeypatch.setattr("engine.thetadata_store.make_chain_provider", _boom)
    from scripts.build_options_skew import main

    assert main(["--accrue"]) == 0
    assert seen.get("legacy") is True


def _two_strike_chain(underlying="THIN", spot=100.0, put_iv=0.40, call_iv=0.30):
    """One put and one call on the ~30d expiry. The pre-packet builder published this."""
    t = 30 / 365.0
    return pd.DataFrame([
        dict(underlying=underlying, expiry="2026-07-21", K=spot * 0.95, T=t,
             is_call=False, iv=put_iv, delta=-0.25, oi=100, gamma=0.01,
             volume=10, spot=spot, asof="2026-06-21"),
        dict(underlying=underlying, expiry="2026-07-21", K=spot, T=t,
             is_call=True, iv=call_iv, delta=0.50, oi=100, gamma=0.01,
             volume=10, spot=spot, asof="2026-06-21"),
    ])


def test_two_strike_expiry_keeps_the_pre_packet_skew():
    """A chosen expiry with fewer than four rows still publishes skew.

    The polygon builder at 98df3cf31eb7 returned a name as soon as that expiry
    had a put and a call. A four-row floor dropped THIN (skew 0.1, n_strikes 2)
    from latest.json and from the ledger. That is a live-surface change, not
    an additive key.
    """
    m = S.compute_skew(_two_strike_chain())
    assert m is not None
    assert m["underlying"] == "THIN"
    assert m["n_strikes"] == 2
    assert m["skew"] == pytest.approx(0.10, abs=1e-9)
    assert m["otm_put_iv"] == pytest.approx(0.40, abs=1e-9)
    assert m["atm_call_iv"] == pytest.approx(0.30, abs=1e-9)


def test_legacy_builder_publishes_a_two_strike_name(tmp_path, monkeypatch):
    """OPTIONS_SKEW_LEGACY_CHAIN=1 must keep the thin name the polygon builder kept."""
    data, site = _patch_dirs(monkeypatch, tmp_path)
    chains = data / "polygon_gex" / "chains"
    chains.mkdir(parents=True)
    pd.concat([
        _chain("AAA", put_iv=0.50, call_iv=0.30),
        _two_strike_chain("THIN"),
    ], ignore_index=True).to_parquet(chains / "2026-06-21.parquet")
    monkeypatch.setenv(S._LEGACY_CHAIN_ENV, "1")
    from scripts.build_options_skew import main

    assert main([]) == 0
    payload = json.loads((site / "options_skew" / "latest.json").read_text())
    assert set(payload["names"]) == {"AAA", "THIN"}
    assert payload["names"]["THIN"]["n_strikes"] == 2
    assert payload["names"]["THIN"]["skew"] == pytest.approx(0.10, abs=1e-9)
    assert payload["n"] == 2
    ledger = pd.read_parquet(data / "options_skew" / "snapshots.parquet")
    assert set(ledger["underlying"].astype(str)) == {"AAA", "THIN"}
    thin = ledger[ledger["underlying"].astype(str) == "THIN"].iloc[0]
    assert int(thin["n_strikes"]) == 2
    assert thin["source"] == "polygon_gex"


def _live_skew_invocations(text: str) -> list[int]:
    """Shell lines that actually launch scripts.build_options_skew."""
    hits = []
    for i, line in enumerate(text.splitlines()):
        if "scripts.build_options_skew" not in line:
            continue
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "brun " in line or "run_py " in line or "python -m " in line:
            hits.append(i)
    return hits


def _job_level_pin(path: Path) -> set[str]:
    """Jobs in a workflow file that pin the legacy source through job-level env."""
    if path.suffix not in {".yml", ".yaml"}:
        return set()
    import yaml

    doc = yaml.safe_load(path.read_text()) or {}
    pinned = set()
    for name, job in (doc.get("jobs") or {}).items():
        env = (job or {}).get("env") or {}
        if str(env.get("OPTIONS_SKEW_LEGACY_CHAIN", "")) == "1":
            pinned.add(name)
    return pinned


def _jobs_launching_skew(path: Path) -> set[str]:
    import yaml

    doc = yaml.safe_load(path.read_text()) or {}
    hits = set()
    for name, job in (doc.get("jobs") or {}).items():
        text = "\n".join(str(s.get("run") or "") for s in ((job or {}).get("steps") or []))
        if _live_skew_invocations(text):
            hits.add(name)
    return hits


def test_every_live_skew_caller_exports_the_legacy_flag():
    """Every process that publishes skew today must set the legacy source.

    engine-render.yml and closing-bell.yml were pinned in W2-1b. The nightly
    engine job runs scripts/ci/daily_engine_regional_desk_builders.sh, and
    render.yml (default runner render-linux, scope all and scope gex) also
    launches the builder. A pin that only matches `brun options_skew` leaves
    the run_py lines, and those two files, free to emit the old ledger.

    Two pin shapes are lawful: (a) `export OPTIONS_SKEW_LEGACY_CHAIN=1` on the
    line before the launch and `unset` on the line after; (b) a job-level
    `env: OPTIONS_SKEW_LEGACY_CHAIN: "1"` on every job that launches the
    builder — render.yml uses (b) because its re-render step's run expression
    sits 76 chars under the 20,500-char guard in test_public_render_fastlane.
    """
    root = Path(__file__).resolve().parents[1]
    required = {
        ".github/workflows/engine-render.yml",
        ".github/workflows/closing-bell.yml",
        ".github/workflows/render.yml",
        "scripts/ci/daily_engine_regional_desk_builders.sh",
    }
    found: dict[str, int] = {}
    for base in (root / ".github" / "workflows", root / "scripts" / "ci"):
        for path in sorted(base.rglob("*")):
            if path.suffix not in {".yml", ".yaml", ".sh"} or not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            lines = path.read_text().splitlines()
            hits = _live_skew_invocations("\n".join(lines))
            if not hits:
                continue
            found[rel] = len(hits)
            if path.suffix in {".yml", ".yaml"}:
                launching = _jobs_launching_skew(path)
                pinned = _job_level_pin(path)
                if launching and launching <= pinned:
                    # shape (b): every launching job carries the env pin; the
                    # dated cutover comment must sit on the pin itself.
                    assert "A-F03-W2-1b (2026-09-22)" in "\n".join(lines), rel
                    continue
            for i in hits:
                assert lines[i - 1].strip() == "export OPTIONS_SKEW_LEGACY_CHAIN=1", (
                    rel, i + 1, lines[max(0, i - 3): i + 2]
                )
                assert lines[i + 1].strip() == "unset OPTIONS_SKEW_LEGACY_CHAIN", (
                    rel, i + 1, lines[i: i + 2]
                )
                comment = "\n".join(lines[max(0, i - 4): i])
                assert "A-F03-W2-1b (2026-09-22)" in comment, (rel, comment)
    assert required <= set(found), sorted(required - set(found))
    # The narrow gex scope is a second launch in each render workflow.
    assert found[".github/workflows/engine-render.yml"] >= 2
    assert found[".github/workflows/render.yml"] >= 2
    assert found["scripts/ci/daily_engine_regional_desk_builders.sh"] == 1
    assert found[".github/workflows/closing-bell.yml"] == 1
