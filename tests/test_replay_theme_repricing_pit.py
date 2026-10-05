"""Executable PIT replay harness: source vintages + Massive split repair."""
import json
from datetime import date, timedelta

import pandas as pd

from lib import nyse_calendar
from scripts import replay_theme_repricing_pit as replay


def _tree(members=("A", "B", "C", "D")):
    return [{
        "theme": "Semiconductors",
        "key": "Semiconductors",
        "subsectors": [{
            "key": "semiscompute",
            "name": "Compute",
            "description": "Compute",
            "members": list(members),
        }],
    }]


def _sessions(end: date, n=100):
    rows = nyse_calendar.sessions_between(end - timedelta(days=180), end)
    return rows[-n:]


def _raw_close(end: date, daily: float, split_day: date | None = None):
    sessions = _sessions(end)
    adjusted = pd.Series(
        [100.0 * ((1 + daily) ** i) for i in range(len(sessions))],
        index=pd.DatetimeIndex(sessions),
        dtype=float,
    )
    raw = adjusted.copy()
    if split_day is not None:
        raw.loc[raw.index < pd.Timestamp(split_day)] *= 10.0
    return raw


def _write_world(root, store):
    (root / "finviz_themes").mkdir(parents=True)
    (root / "data/themes_heatmap").mkdir(parents=True)
    store.mkdir(parents=True)

    (root / "finviz_themes/finviz_themes_map.json").write_text(
        json.dumps({"asof": "2026-01-02", "themes": _tree(("A", "B", "C", "D"))}),
        encoding="utf-8",
    )
    (root / "data/themes_heatmap/tree_history.jsonl").write_text(
        json.dumps({
            "asof": "2026-01-15",
            "tree": _tree(("B", "C", "D", "E")),
        }) + "\n",
        encoding="utf-8",
    )
    (root / "data/themes_heatmap/subsector_perf_history.jsonl").write_text(
        json.dumps({
            "asof": "2026-01-16",
            "subsectors": {
                "semiscompute": {"1W": 4.0, "1M": 8.0, "3M": 12.0},
            },
        }) + "\n",
        encoding="utf-8",
    )

    rates = {"A": 0.002, "B": 0.008, "C": 0.006, "D": 0.004, "E": 0.003}
    for ticker, rate in rates.items():
        raw = _raw_close(
            date(2026, 1, 16),
            rate,
            split_day=date(2026, 1, 12) if ticker == "B" else None,
        )
        pd.DataFrame({"close": raw}).to_parquet(store / f"{ticker}.parquet")


def test_real_harness_uses_split_repair_and_pit_sources(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    store = tmp_path / "massive"
    _write_world(root, store)
    monkeypatch.setattr(replay, "check_local_mirror_freshness", lambda *a, **k: 0)

    out = replay.replay(
        root=root,
        store=store,
        asof="2026-01-16",
        tail=1,
        full=True,
    )

    assert out["schema"] == "theme_repricing_pit_replay.v1"
    assert out["source"]["split_repair"].endswith("split_adjust")
    assert out["authority"]["may_trade"] is False

    result = out["results"][0]
    assert result["membership"]["vintage_asof"] == "2026-01-15"
    assert result["prices"]["basis"] == "raw_close_split_adjusted_price_return"
    assert result["coverage"]["horizons"]["1W"]["coverage"] == 1.0

    row = result["repricing"]["subthemes"][0]
    assert row["shape"] == "broad_price_repricing"
    assert row["price_leader"]["ticker"] == "B"
    assert row["horizons"]["1W"]["leader"]["return"] < 10.0
    assert row["horizons"]["1W"]["leader"]["return"] > 0.0


def test_harness_refuses_when_massive_store_is_missing(tmp_path):
    root = tmp_path / "repo"
    store = tmp_path / "missing"
    (root / "data/themes_heatmap").mkdir(parents=True)
    (root / "data/themes_heatmap/subsector_perf_history.jsonl").write_text(
        json.dumps({"asof": "2026-01-16", "subsectors": {}}) + "\n",
        encoding="utf-8",
    )

    try:
        replay.replay(root=root, store=store, asof="2026-01-16")
    except Exception as exc:
        assert "Massive price store unavailable" in str(exc)
    else:
        raise AssertionError("missing heavy store must refuse")
