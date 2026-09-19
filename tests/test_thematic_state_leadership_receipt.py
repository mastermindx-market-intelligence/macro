"""The existing ThemeState reader preserves Lane C descriptive observations."""
from __future__ import annotations

import json

from engine.neuralweb import thematic_state as ts


def test_subsector_reader_and_theme_composer_preserve_leadership_observation(tmp_path):
    observation = {
        "schema": "subsector_rotation.closed_session_leadership.v1",
        "status": "PARTIAL",
        "asof": "2026-09-18",
        "parent": {"key": "Semiconductors", "windows": {"5": {"return_pct": 1.2}}},
        "subthemes": [{"key": "semiscompute", "name": "Compute",
                       "windows": {"5": {"return_pct": 4.7}}}],
        "reason_codes": ["DESCRIPTIVE_SHADOW_ONLY"],
        "measurement_receipt": {
            "benchmark": "SPY",
            "basis": {"membership_is_point_in_time": False},
            "permissions": {"may_rank": False, "may_gate": False},
            "clocks": {
                "observation_session": "2026-09-18",
                "input_snapshot_asof": "2026-09-18",
                "computation_utc": "2026-09-19 16:00",
            },
            "source_records": ["data/themes_heatmap/themes_tree.json", "SPY"],
        },
    }
    path = tmp_path / "site" / "marketdata" / "subsector_rotation.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "asof": "2026-09-18",
        "themes": [{
            "theme": "Semiconductors", "quadrant": "leading", "rs": {},
            "z_accel": 0.4, "emerging_score": 0.7,
            "leadership_observation": observation,
        }],
    }))

    by_name, stale = ts._read_subsector(tmp_path)
    assert not stale
    assert by_name["Semiconductors"]["leadership_observation"] == observation

    block = ts._compose_theme(
        {"id": "ai_semiconductors", "name_en": "AI Semiconductors",
         "name_zh": "AI半导体", "subsector_keys": ["Semiconductors"]},
        foresight_by_id={}, baskets_by_id={}, radar_flags={}, radar_hyps={},
        narrative_tickers={}, subsector_by_name=by_name, divergence_log={},
        membership_by_basket={},
    )
    receipt = block["subsector_rotation"]["subsectors"][0]
    assert receipt["key"] == "Semiconductors"
    assert receipt["leadership_observation"] == observation
