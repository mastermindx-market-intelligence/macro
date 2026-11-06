"""Backfill the covered skew ledger from a fake ThetaData chain, and keep weekend rows out of emit.

The chain frame uses the same two-leg shape as tests/test_options_skew.py. The
ledger is a tmp parquet, never the production file.
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from engine import options_skew as S  # noqa: E402

# Monday / Tuesday / Saturday in the legacy window. Saturday is the newest
# stamp so a broken weekend filter would publish it.
_WEEKDAY = "2026-06-22"
_UNCOVERED = "2026-06-23"
_WEEKEND = "2026-06-27"
_DATES = [_WEEKDAY, _UNCOVERED, _WEEKEND]


def _priced_chain(underlying, asof, put_iv=0.55, call_iv=0.20, spot=100.0):
    """One ~30-day expiry with a 25-delta put and a 50-delta call. Same columns
    the ThetaData chain provider emits."""
    tenor = 30 / 365.0
    far = tenor * 6
    rows = []
    for exp, t in (("2026-07-22", tenor), ("2027-01-22", far)):
        rows += [
            dict(underlying=underlying, expiry=exp, K=spot * 0.95, T=t, is_call=False,
                 iv=put_iv, delta=-0.25, oi=100, volume=10, spot=spot, asof=asof),
            dict(underlying=underlying, expiry=exp, K=spot, T=t, is_call=True,
                 iv=call_iv, delta=0.50, oi=100, volume=10, spot=spot, asof=asof),
        ]
    return pd.DataFrame(rows)


def _polygon_row(underlying, day, skew):
    return {
        "date": day,
        "underlying": underlying,
        "asof": day,
        "spot": 100.0,
        "tenor_days": 30.0,
        "otm_put_iv": round(0.30 + skew, 4),
        "atm_call_iv": 0.30,
        "skew": skew,
        "n_strikes": 8,
        "source": "polygon_gex",
    }


def _seed(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        _polygon_row("XYZ", _WEEKDAY, 0.10),
        _polygon_row("QQQ", _UNCOVERED, 0.20),
        _polygon_row("BBB", _WEEKEND, 0.05),
    ]).to_parquet(path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pin(monkeypatch, path: Path) -> None:
    def _snap():
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    monkeypatch.setattr(S, "_snap_path", _snap)


def _install_chain(monkeypatch, seen: list):
    def fake_load_chain(asof=None, store=None, roots=None):
        seen.append({"asof": asof, "store": store, "roots": roots})
        if asof == _WEEKDAY:
            return _priced_chain("XYZ", asof), "ok"
        if asof and S._is_weekend_iso(asof):
            raise AssertionError(f"weekend {asof} was sent to the store")
        return None, "no_chain_for_date"

    monkeypatch.setattr(S, "load_chain", fake_load_chain)


def _row(path: Path, underlying: str) -> pd.Series:
    frame = pd.read_parquet(path)
    hit = frame[frame["underlying"].astype(str) == underlying]
    assert len(hit) == 1
    return hit.iloc[0]


def test_backfill_replaces_the_weekday_and_leaves_weekend_and_uncovered(tmp_path, monkeypatch):
    ledger = tmp_path / "snapshots.parquet"
    _seed(ledger)
    _pin(monkeypatch, ledger)
    seen: list = []
    _install_chain(monkeypatch, seen)
    calls = []
    real_snapshot = S.snapshot

    def spy_snapshot(today=None, chain=None, source=None):
        calls.append({
            "today": today,
            "source": source,
            "asof": None if chain is None else str(chain["asof"].iloc[0])[:10],
        })
        return real_snapshot(today=today, chain=chain, source=source)

    monkeypatch.setattr(S, "snapshot", spy_snapshot)

    receipt = S.backfill_from_store(_DATES, store="sentinel-store", roots=["XYZ"])

    assert receipt["dates_requested"] == 3
    assert receipt["dates_weekend_skipped"] == 1
    assert receipt["dates_not_in_store"] == 1
    assert receipt["dates_backfilled"] == 1
    assert receipt["rows_replaced"] == 1
    assert receipt["rows_added"] == 0
    assert [item["asof"] for item in seen] == [_WEEKDAY, _UNCOVERED]
    assert seen[0]["store"] == "sentinel-store"
    assert seen[0]["roots"] == ["XYZ"]
    assert _WEEKEND not in [item["asof"] for item in seen]
    assert calls == [{
        "today": date.fromisoformat(_WEEKDAY),
        "source": "thetadata",
        "asof": _WEEKDAY,
    }]

    monday = _row(ledger, "XYZ")
    assert monday["source"] == "thetadata"
    assert float(monday["skew"]) == pytest.approx(0.35, abs=1e-6)
    assert float(monday["skew"]) != pytest.approx(0.10, abs=1e-6)
    assert _row(ledger, "QQQ")["source"] == "polygon_gex"
    assert float(_row(ledger, "QQQ")["skew"]) == pytest.approx(0.20, abs=1e-9)
    assert _row(ledger, "BBB")["source"] == "polygon_gex"
    assert str(_row(ledger, "BBB")["date"])[:10] == _WEEKEND

    again = S.backfill_from_store(_DATES, store="sentinel-store", roots=["XYZ"])
    assert again["rows_replaced"] == 0
    assert again["rows_added"] == 0

    payload = S.emit_from_ledger(today=date(2026, 6, 24))
    assert payload["n_weekend_rows_excluded"] == 1
    assert payload["history_sources"] == ["polygon_gex", "thetadata"]
    assert payload["ledger_asof"] == _UNCOVERED
    assert set(payload["names"]) == {"QQQ"}
    assert "BBB" not in payload["names"]
    for key in ("schema", "names", "ranked", "n", "source", "source_state",
                "source_detail", "ledger_asof", "accrual_state"):
        assert key in payload


def test_dry_run_counts_the_change_and_does_not_write(tmp_path, monkeypatch):
    ledger = tmp_path / "snapshots.parquet"
    _seed(ledger)
    pinned = _sha(ledger)
    _pin(monkeypatch, ledger)
    seen: list = []
    _install_chain(monkeypatch, seen)

    def _boom(*_args, **_kwargs):
        raise AssertionError("dry_run wrote through snapshot")

    monkeypatch.setattr(S, "snapshot", _boom)
    receipt = S.backfill_from_store(_DATES, dry_run=True)
    assert receipt["rows_replaced"] == 1
    assert receipt["rows_added"] == 0
    assert receipt["dates_weekend_skipped"] == 1
    assert receipt["dates_not_in_store"] == 1
    assert _sha(ledger) == pinned
    assert _row(ledger, "XYZ")["source"] == "polygon_gex"


def test_cli_backfill_prints_one_json_line_and_skips_emit(tmp_path, monkeypatch, capsys):
    ledger = tmp_path / "snapshots.parquet"
    site = tmp_path / "site"
    _seed(ledger)
    pinned = _sha(ledger)
    seen: list = []
    _install_chain(monkeypatch, seen)
    monkeypatch.setattr("lib.config.site_dir", lambda: site)
    from scripts.build_options_skew import main

    args = ["--backfill", _WEEKDAY, _WEEKEND, "--ledger", str(ledger), "--roots", "XYZ,QQQ"]
    assert main([*args, "--dry-run"]) == 0
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) == 1
    dry = json.loads(lines[0])
    assert dry["rows_replaced"] == 1
    assert dry["dates_weekend_skipped"] == 1
    assert _sha(ledger) == pinned
    assert seen[0]["roots"] == ["XYZ", "QQQ"]
    assert not (site / "options_skew" / "latest.json").exists()

    seen.clear()
    assert main(args) == 0
    written = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert written["rows_replaced"] == 1
    assert _row(ledger, "XYZ")["source"] == "thetadata"
    assert not (site / "options_skew" / "latest.json").exists()

    assert main(args) == 0
    second = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert second["rows_replaced"] == 0
    assert second["rows_added"] == 0


def test_weekend_only_ledger_does_not_claim_rows_were_excluded(tmp_path, monkeypatch):
    """A ledger with no weekday row still emits its latest weekend row.

    The older emit fixture stamps Saturday 2026-06-20 and Sunday 2026-06-21
    and expects that Sunday row to stay. Those rows were not removed, so the
    exclusion count is zero. A ledger that also has a weekday drops the
    weekend rows and counts only the rows it removed.
    """
    ledger = tmp_path / "snapshots.parquet"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        _polygon_row("OLD", "2026-06-20", 0.01),
        _polygon_row("XYZ", "2026-06-21", 0.10),
    ]).to_parquet(ledger)
    _pin(monkeypatch, ledger)

    payload = S.emit_from_ledger(today=date(2026, 6, 24))
    assert payload["ledger_asof"] == "2026-06-21"
    assert set(payload["names"]) == {"XYZ"}
    assert payload["n_weekend_rows_excluded"] == 0
    assert payload["history_sources"] == ["polygon_gex"]


def test_unresolved_store_exits_zero_with_the_warning_line(tmp_path, monkeypatch, capsys):
    ledger = tmp_path / "snapshots.parquet"
    _seed(ledger)
    pinned = _sha(ledger)
    monkeypatch.delenv("THETADATA_STORE", raising=False)
    monkeypatch.setattr(
        "engine.thetadata_store.resolve_thetadata_store", lambda **_kw: None,
    )
    from scripts.build_options_skew import main

    assert main(["--backfill", _WEEKDAY, _WEEKDAY, "--ledger", str(ledger)]) == 0
    out = capsys.readouterr().out
    assert any(line.startswith("::warning") for line in out.splitlines())
    assert out.splitlines()[0].startswith("::warning title=options-skew-source::")
    assert _sha(ledger) == pinned
