"""E3A — carry regime_outlook verbatim in rates_command lobe.

The reader surfaces the projection itself (deep copy), preserves every
existing key, and adds no key when the projection is absent or malformed.
Gate-3 (no build date promoted to a reading date) and Gate-4 (no
derived/ranked/normalised numbers) are enforced directly.
"""

import copy
import json

import pytest

from engine.neuralweb._law import assert_no_authority
from engine.neuralweb.world_state import _compose_rates_command


@pytest.fixture
def latest() -> dict:
    return {
        "asof": "2026-09-30",
        "expectations_pressure": {
            "net_state": "balanced",
            "state_label": {"en": "Balanced", "zh": "平衡"},
            "hawk_score": 1,
            "ease_score": 1,
        },
        "market_check": {
            "futures": {"m12": 3.6, "plain_read_en": "x", "plain_read_zh": "y"}
        },
        "stance": {"en": "hold", "zh": "观望"},
        "board": {
            "rate_path_row": {
                "policy_rate": 3.88,
                "path_plain": {"en": "p", "zh": "q"},
            }
        },
    }


@pytest.fixture
def projection() -> dict:
    return {
        "schema_version": "regime_outlook.v1",
        "scope": "US",
        "analysis_cutoff": "2026-09-30T09:43:58.059037+00:00",
        "built_at": "2026-10-01T02:00:00+00:00",
        "mapping_version": "VERDICT_MAPPING_V2",
        "mapping_sha256": "deadbeef" * 8,
        "evidence_clock_range": {
            "oldest": "2026-09-25",
            "newest": "2026-09-30",
            "by_clock_semantics": {"owner_snapshot_date": 2},
        },
        "conditional_paths": [
            {
                "path_id": "orderly_disinflation",
                "family": "rates",
                "conditions": {},
                "family_readings": [
                    {"evidence_family_id": "core_pce", "reading": "fits"},
                    {
                        "evidence_family_id": "treasury_curve",
                        "reading": "does_not_fit",
                    },
                    {"evidence_family_id": "labour", "reading": "fits"},
                    {
                        "evidence_family_id": "credit_and_funding",
                        "reading": "mixed",
                    },
                ],
                "watch": [],
            },
            {
                "path_id": "growth_deterioration",
                "family": "rates",
                "conditions": {},
                "family_readings": [
                    {
                        "evidence_family_id": "treasury_curve",
                        "reading": "does_not_fit",
                    },
                    {"evidence_family_id": "labour", "reading": "unknown"},
                ],
                "watch": [],
            },
        ],
        "authority": {
            "may_rank": False,
            "may_gate": False,
            "may_size": False,
            "may_trade": False,
            "may_forecast": False,
            "may_escalate": False,
        },
        "tier": "display_research",
        "notes": [],
    }


def _write_root(tmp_path, payload, name="rates"):
    data_dir = tmp_path / name / "data" / "rates_command"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "latest.json").write_text(json.dumps(payload))
    return tmp_path / name


def test_projection_carried_verbatim(tmp_path, latest, projection):
    payload = {**latest, "regime_outlook": projection}
    out = _compose_rates_command(root=_write_root(tmp_path, payload))
    assert out["regime_outlook"] == projection
    assert json.dumps(out["regime_outlook"], sort_keys=True) == json.dumps(
        projection, sort_keys=True
    )


def test_deep_copy_independence(tmp_path, latest, projection):
    payload = {**latest, "regime_outlook": projection}
    root = _write_root(tmp_path, payload)
    out1 = _compose_rates_command(root=root)
    out1["regime_outlook"]["conditional_paths"][0]["path_id"] = "MUTATED"
    out2 = _compose_rates_command(root=root)
    assert out2["regime_outlook"] == projection
    assert out1["regime_outlook"] is not out2["regime_outlook"]


def test_existing_keys_unchanged_with_and_without_projection(tmp_path, latest, projection):
    root_without = _write_root(tmp_path, latest, name="without")
    root_with = _write_root(tmp_path, {**latest, "regime_outlook": projection}, name="with")
    a = _compose_rates_command(root=root_without)
    b = _compose_rates_command(root=root_with)
    assert {k: b[k] for k in a} == a
    assert set(b) - set(a) == {"regime_outlook"}


def test_absent_projection_adds_no_key(tmp_path, latest):
    a = _compose_rates_command(root=_write_root(tmp_path, latest))
    assert "regime_outlook" not in a


def test_malformed_projection_adds_no_key(tmp_path, latest):
    a = _compose_rates_command(root=_write_root(tmp_path, latest))
    for ro in (None, [], "x", {}, {"schema_version": "regime_outlook.v0"}, {"scope": "US"}):
        payload = copy.deepcopy(latest)
        payload["regime_outlook"] = ro
        out = _compose_rates_command(root=_write_root(tmp_path, payload))
        assert out == a


def test_file_absent_returns_todays_null_shape(tmp_path):
    out = _compose_rates_command(root=tmp_path)
    assert list(out) == [
        "asof",
        "net_state",
        "state_label",
        "hawk_score",
        "ease_score",
        "stance_en",
        "stance_zh",
        "implied_m12",
        "policy_rate",
        "display_only",
        "authority",
    ]
    for k in ("asof", "net_state", "state_label", "hawk_score", "ease_score",
              "stance_en", "stance_zh", "implied_m12", "policy_rate"):
        assert out[k] is None
    assert out["display_only"] is True
    assert out["authority"] is False


def test_authority_law_holds(tmp_path, latest, projection):
    payload = {**latest, "regime_outlook": projection}
    b = _compose_rates_command(root=_write_root(tmp_path, payload))
    assert assert_no_authority(b) == []
    assert b["display_only"] is True
    assert b["authority"] is False
    assert all(v is False for v in b["regime_outlook"]["authority"].values())


def test_analysis_cutoff_verbatim_and_built_at_not_promoted(tmp_path, latest, projection):
    payload = {**latest, "regime_outlook": projection}
    b = _compose_rates_command(root=_write_root(tmp_path, payload))
    assert b["regime_outlook"]["analysis_cutoff"] == "2026-09-30T09:43:58.059037+00:00"
    assert b["regime_outlook"]["built_at"] == "2026-10-01T02:00:00+00:00"
    assert set(b["regime_outlook"]) == set(projection)
    assert b.get("asof") == "2026-09-30"


def test_no_derived_numbers(tmp_path, latest, projection):
    payload = {**latest, "regime_outlook": projection}
    b = _compose_rates_command(root=_write_root(tmp_path, payload))
    assert set(b["regime_outlook"]) == set(projection)