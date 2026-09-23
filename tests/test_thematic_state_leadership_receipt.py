"""The existing ThemeState reader preserves one deduplicated Lane C observation."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from engine.neuralweb import thematic_state as ts


def _observation() -> dict:
    return {
        "schema": "subsector_rotation.closed_session_leadership.v1",
        "status": "PARTIAL",
        "asof": "2026-09-18",
        "parent": {"key": "Semiconductors", "windows": {"5": {"return_pct": 1.2}}},
        "subthemes": [
            {
                "key": "semiscompute",
                "name": "Compute",
                "windows": {"5": {"return_pct": 4.7}},
                "detail": "bounded-proof-" * 200,
            }
        ],
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


def _write_rotation(root: Path, observation: dict) -> None:
    path = root / "site" / "marketdata" / "subsector_rotation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "asof": "2026-09-18",
                "themes": [
                    {
                        "theme": "Semiconductors",
                        "quadrant": "leading",
                        "rs": {},
                        "z_accel": 0.4,
                        "emerging_score": 0.7,
                        "leadership_observation": observation,
                    }
                ],
            }
        )
    )


def _count_equal(value: object, target: dict) -> int:
    count = 1 if isinstance(value, dict) and value == target else 0
    if isinstance(value, dict):
        count += sum(_count_equal(child, target) for child in value.values())
    elif isinstance(value, list):
        count += sum(_count_equal(child, target) for child in value)
    return count


def test_subsector_reader_exposes_private_payload_and_public_reference(tmp_path, monkeypatch):
    # Payload/reference shape is independent of freshness; stale behavior has its own test below.
    monkeypatch.setattr(ts, "_is_stale", lambda _asof: False)
    observation = _observation()
    _write_rotation(tmp_path, observation)

    by_name, stale = ts._read_subsector(tmp_path)

    assert not stale
    row = by_name["Semiconductors"]
    assert row["_leadership_observation_payload"] == observation
    assert row["leadership_observation_ref"] == {
        "observation_key": "Semiconductors",
        "evidence_family_id": (
            "subsector_rotation.closed_session_leadership.v1:Semiconductors"
        ),
        "observation_id": (
            "subsector_rotation.closed_session_leadership.v1:Semiconductors:2026-09-18"
        ),
        "json_pointer": "/subsector_leadership_observations/Semiconductors",
        "schema": observation["schema"],
        "status": "PARTIAL",
        "asof": "2026-09-18",
        "measurement_receipt": observation["measurement_receipt"],
    }
    assert row["leadership_observation"] == observation


def test_theme_composer_emits_reference_not_full_payload(tmp_path):
    observation = _observation()
    _write_rotation(tmp_path, observation)
    by_name, _ = ts._read_subsector(tmp_path)

    block = ts._compose_theme(
        {
            "id": "ai_semiconductors",
            "name_en": "AI Semiconductors",
            "name_zh": "AI半导体",
            "subsector_keys": ["Semiconductors"],
        },
        foresight_by_id={},
        baskets_by_id={},
        radar_flags={},
        radar_hyps={},
        narrative_tickers={},
        subsector_by_name=by_name,
        divergence_log={},
        membership_by_basket={},
    )

    receipt = block["subsector_rotation"]["subsectors"][0]
    assert receipt["key"] == "Semiconductors"
    assert receipt["leadership_observation_ref"]["observation_key"] == "Semiconductors"
    assert receipt["leadership_observation_ref"]["measurement_receipt"] == observation[
        "measurement_receipt"
    ]
    assert "leadership_observation" not in receipt
    assert "_leadership_observation_payload" not in receipt


def test_full_composer_stores_one_observation_for_three_canonical_consumers(tmp_path):
    observation = _observation()
    _write_rotation(tmp_path, observation)
    config = tmp_path / "config" / "theme_crosswalk.yml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        yaml.safe_dump(
            {
                "themes": [
                    {
                        "id": theme_id,
                        "name_en": theme_id,
                        "name_zh": theme_id,
                        "subsector_keys": ["Semiconductors"],
                    }
                    for theme_id in (
                        "ai_semiconductors",
                        "memory_storage",
                        "semicap_equipment",
                    )
                ]
            },
            sort_keys=False,
        )
    )

    artifact = ts.compose(root=tmp_path)

    assert artifact["subsector_leadership_observations"] == {
        "Semiconductors": observation
    }
    assert _count_equal(artifact, observation) == 1
    for block in artifact["themes"]:
        receipt = block["subsector_rotation"]["subsectors"][0]
        ref = receipt["leadership_observation_ref"]
        assert ref["observation_key"] == "Semiconductors"
        assert ref["json_pointer"] == "/subsector_leadership_observations/Semiconductors"
        assert ref["status"] == "PARTIAL"
        assert ref["measurement_receipt"]["permissions"]["may_rank"] is False
        assert "leadership_observation" not in receipt

    compact = len(json.dumps(artifact, separators=(",", ":"), sort_keys=True))
    duplicated = json.loads(json.dumps(artifact))
    duplicated.pop("subsector_leadership_observations")
    for block in duplicated["themes"]:
        row = block["subsector_rotation"]["subsectors"][0]
        row["leadership_observation"] = observation
    duplicated_size = len(json.dumps(duplicated, separators=(",", ":"), sort_keys=True))
    assert compact < duplicated_size * 0.6


def test_stale_embedded_leadership_is_propagated_to_health(tmp_path):
    observation = _observation()
    observation["asof"] = "2000-01-03"
    observation["measurement_receipt"]["clocks"]["observation_session"] = "2000-01-03"
    _write_rotation(tmp_path, observation)

    by_name, stale = ts._read_subsector(tmp_path)

    row = by_name["Semiconductors"]
    assert row["leadership_observation"]["status"] == "PARTIAL"
    assert row["leadership_observation_ref"]["asof"] == "2000-01-03"
    assert any(
        "leadership[Semiconductors]" in item and "stale" in item.lower()
        for item in stale
    )


def test_unavailable_producer_receipt_and_reason_reach_consumer_health(tmp_path):
    today = ts._asof_today()
    path = tmp_path / "site" / "marketdata" / "subsector_rotation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "asof": today,
        "closed_session_leadership": {
            "schema": "subsector_rotation.closed_session_leadership.v1",
            "status": "UNAVAILABLE",
            "requested_themes": ["Semiconductors"],
            "reason_codes": ["OWNER_INPUT_LOAD_FAILED"],
            "clocks": {
                "observation_session": None,
                "input_snapshot_asof": today,
                "computation_utc": f"{today} 23:00",
            },
        },
        "themes": [{"theme": "Semiconductors", "quadrant": "leading"}],
    }))

    by_name, stale = ts._read_subsector(tmp_path)

    row = by_name["Semiconductors"]
    assert row["leadership_observation"]["status"] == "UNAVAILABLE"
    assert row["leadership_observation_ref"]["status"] == "UNAVAILABLE"
    assert "OWNER_INPUT_LOAD_FAILED" in row["leadership_observation"]["reason_codes"]
    assert any("OWNER_INPUT_LOAD_FAILED" in item for item in stale)


def test_observation_reference_has_stable_family_and_observation_identity(tmp_path):
    observation = _observation()
    _write_rotation(tmp_path, observation)

    by_name, _ = ts._read_subsector(tmp_path)
    ref = by_name["Semiconductors"]["leadership_observation_ref"]

    assert ref["evidence_family_id"] == (
        "subsector_rotation.closed_session_leadership.v1:Semiconductors"
    )
    assert ref["observation_id"] == (
        "subsector_rotation.closed_session_leadership.v1:Semiconductors:2026-09-18"
    )


def test_observation_identity_changes_only_when_observation_clock_changes():
    first = _observation()
    same = json.loads(json.dumps(first))
    later = json.loads(json.dumps(first))
    later["asof"] = "2026-09-19"
    later["measurement_receipt"]["clocks"]["observation_session"] = "2026-09-19"

    ref_first = ts._leadership_observation_ref("Semiconductors", first)
    ref_same = ts._leadership_observation_ref("Semiconductors", same)
    ref_later = ts._leadership_observation_ref("Semiconductors", later)

    assert ref_same["evidence_family_id"] == ref_first["evidence_family_id"]
    assert ref_same["observation_id"] == ref_first["observation_id"]
    assert ref_later["evidence_family_id"] == ref_first["evidence_family_id"]
    assert ref_later["observation_id"] != ref_first["observation_id"]
