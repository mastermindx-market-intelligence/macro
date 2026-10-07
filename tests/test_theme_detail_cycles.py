"""All-region theme-detail cycle records built from the equal-weight level matrix."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from scripts.build_theme_detail import _cycle_from_chart


def test_cycle_from_chart_builds_compact_record():
    idx = pd.bdate_range("2023-01-02", periods=750)
    x = np.arange(len(idx), dtype=float)
    values = 100.0 * np.exp(0.0004 * x + 0.12 * np.sin(x / 45.0))
    chart = {
        "dates": [d.strftime("%Y-%m-%d") for d in idx],
        "baskets": {"gold_miners": values.tolist()},
    }
    rec = _cycle_from_chart(
        chart,
        "gold_miners",
        {"name": "Gold Miners", "name_zh": "黄金矿业"},
    )
    assert rec is not None
    assert len(rec["price"]) > 50
    assert rec["basis"] == "equal_weight_close"
    assert rec["now"]["phase"] in rec["phases"]
    assert rec["xDomain"][1] > rec["today"]


def test_theme_cycle_chart_preserves_geometry_on_wide_detail_pages():
    template = (Path(__file__).parents[1] / "templates" / "basket_detail.html.j2").read_text()
    assert 'const W=1080,H=240' in template
    assert 'preserveAspectRatio="xMidYMid meet"' in template
    assert 'aspect-ratio:${W}/${H}' in template
    assert 'preserveAspectRatio="none" style="display:block;height:168px"' not in template
