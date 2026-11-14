"""Real-data checks for the SI rotation read against the committed inputs.

Skipped on a sparse tree where data/ is not materialised. No ticker from the
real data is printed or asserted by value — roster checks compare sets behind
a boolean so a failure cannot dump the membership into the log.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine.us_basket_turn import active_members
from scripts import build_rotation_read as brr

ROOT = Path(__file__).resolve().parent.parent
HIST = ROOT / "data/breadth/history/basket_breadth_weekly_current.parquet"
MEMBERSHIP = ROOT / "data/baskets/membership.json"

NOW_PIN = datetime(2026, 11, 13, 22, 0, tzinfo=timezone.utc)

pytestmark = pytest.mark.skipif(
    not HIST.exists() or not MEMBERSHIP.exists(),
    reason="data/ not materialised (sparse tree)",
)

_MEASURES = ("pct_above_200", "chg_13w", "chg_26w", "direction", "run_weeks",
             "rank_13w", "n_ranked")


def _inputs() -> tuple[pd.DataFrame, dict]:
    hist = pd.read_parquet(HIST)
    membership = json.loads(MEMBERSHIP.read_text(encoding="utf-8"))
    return hist, membership


def test_real_build_shape_and_vintage():
    hist, membership = _inputs()
    payload = brr.build(hist, membership, NOW_PIN)
    assert payload is not None

    expected = brr.last_completed_weekly_close(hist["date"].unique())
    assert expected is not None
    assert payload["as_of"] == expected.isoformat()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", payload["as_of"])

    groups = payload["groups"]
    assert len(groups) == 49
    families = [g["family"] for g in groups]
    assert families.count("sector") == 11
    assert families.count("theme") == 38

    basket_ids = set(membership["baskets"])
    assert {g["group_id"] for g in groups} == basket_ids
    ordered = sorted(basket_ids, key=lambda gid: (0 if gid.startswith("us_sector_") else 1, gid))
    assert [g["group_id"] for g in groups] == ordered

    assert payload["status"] in {"ok", "stale"}
    for g in groups:
        assert g["status"] in {"ok", "unavailable"}
        if g["status"] == "unavailable":
            assert all(g[field] is None for field in _MEASURES)

    serialized = json.dumps(payload, ensure_ascii=False)
    assert "vendor" not in serialized
    assert "internal_only" not in serialized

    union: set[str] = set()
    for basket in membership["baskets"].values():
        union.update(m["ticker"] for m in active_members(basket))
    companies_match = set(payload["companies"]) == union
    assert companies_match, "companies tickers differ from the union of active rosters"


def test_real_check_rotation_read_coherent(tmp_path):
    from scripts import check_sector_intelligence_freshness as freshness

    hist, membership = _inputs()
    payload = brr.build(hist, membership, NOW_PIN)
    assert payload is not None

    root = tmp_path / "root"
    hist_dir = root / "data/breadth/history"
    hist_dir.mkdir(parents=True)
    shutil.copy(HIST, hist_dir / HIST.name)
    out = root / "site/sectordata/rotation_read.json"
    out.parent.mkdir(parents=True)
    out.write_text(
        json.dumps(payload, indent=1, sort_keys=False, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    assert freshness.check_rotation_read(root) == []