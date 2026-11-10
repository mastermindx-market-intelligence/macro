"""Optional typed blocks (lane 8 R1/R2, lane 7 depth) read `unavailable` unless produced.

REAL    The committed `site/` member bytes (session 2026-11-06) carry none of the
        seven blocks, so every block reads `unavailable/not_produced`: that is what
        the real producers emit today and nothing is invented.
FIXTURE Synthetic documents (labelled per test) prove the `available` path, shape
        refusal (`invalid_shape`), NaN refusal, the 64 KiB cap, the entitled-only
        gate and that a bad block never changes another part of the projection.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from engine.sector_native_view import project_sector_view, typed_blocks_of
from lib import sector_generation_contract as contract
from tests.test_sector_population import PUBLISHED, SESSION, _real_bundle

NAMES = ("r1_rising_priced_share", "r2_display_order", "r2_hazard_qualification",
         "etf_flows", "confluence", "bottoming_watch", "theme_table")
CONFLUENCE = {"us": {"n": 1}, "hk": {"n": 2}, "cn": {"n": 3}, "ca": {"n": 4}}


def _inputs(tmp_path, *, carried=False):
    raw, identity = _real_bundle(tmp=tmp_path, carried=carried)
    return contract._capture_view(
        member_bytes=raw, input_identity=identity, generation_id="typed-blocks",
        published_at=PUBLISHED.isoformat(), now=PUBLISHED)


def _project(inputs, receipt, audience="entitled"):
    return project_sector_view(inputs, receipt, audience=audience)


def test_real_bytes_carry_no_typed_block_so_all_read_not_produced(tmp_path):
    """REAL: the committed `sector_central.json` predates the carry step (no `carried`)."""
    inputs, receipt = _inputs(tmp_path)
    for audience in ("entitled", "preview"):
        data = _project(inputs, receipt, audience)["data"]
        # Incumbent byte parity: nothing produced => the key is absent and the
        # hash is untouched; the accessor supplies the explicit unavailable state.
        assert "typed_blocks" not in data
        blocks = typed_blocks_of(data)
        assert tuple(blocks) == NAMES
        for name in NAMES:
            expected_reason = ("audience_not_entitled"
                               if audience == "preview" and name in NAMES[3:] else "not_produced")
            assert blocks[name] == {"status": "unavailable", "reason": expected_reason,
                                    "value": None}


def test_fixture_produced_blocks_are_available_and_preserved(tmp_path):
    """FIXTURE: documents that carry each block under its closed key."""
    inputs, receipt = _inputs(tmp_path)
    inputs.central["hazard_qualification"] = {"status": "withheld"}
    inputs.central["carried"] = {
        "sector_central_r1": {"rising_share": 0.42, "priced_share": 0.9, "missing_members": 2},
        "display_order": {"order": ["xlk", "xlf"]},
        "etf_flows": {"rows": [1]}, "confluence": deepcopy(CONFLUENCE),
        "bottoming_watch": {"rows": []}, "theme_table": {"rows": [2]}}
    blocks = _project(inputs, receipt)["data"]["typed_blocks"]
    assert all(blocks[n]["status"] == "available" and blocks[n]["reason"] is None for n in NAMES)
    assert blocks["confluence"]["value"] == CONFLUENCE
    assert blocks["r1_rising_priced_share"]["value"]["missing_members"] == 2
    preview = _project(inputs, receipt, "preview")["data"]["typed_blocks"]
    assert preview["r1_rising_priced_share"]["status"] == "available"
    assert all(preview[n] == {"status": "unavailable", "reason": "audience_not_entitled",
                              "value": None} for n in NAMES[3:])


@pytest.mark.parametrize("name,owner,key,bad", [
    ("r1_rising_priced_share", "carried", "sector_central_r1", [1, 2]),
    ("r2_display_order", "carried", "display_order", {"order": [float("nan")]}),
    ("r2_hazard_qualification", "central", "hazard_qualification", "text"),
    ("etf_flows", "carried", "etf_flows", "text"),
    ("confluence", "carried", "confluence", {"us": {}}),
    ("theme_table", "carried", "theme_table", {"blob": "x" * (64 * 1024 + 1)}),
])
def test_fixture_malformed_block_is_invalid_shape_and_changes_nothing_else(
        tmp_path, name, owner, key, bad):
    """FIXTURE."""
    inputs, receipt = _inputs(tmp_path)
    baseline = _project(inputs, receipt)["data"]
    target = inputs.central if owner == "central" else inputs.central.setdefault("carried", {})
    target[key] = bad
    data = _project(inputs, receipt)["data"]
    assert data["typed_blocks"][name] == {"status": "unavailable", "reason": "invalid_shape",
                                          "value": None}
    for part in ("core", "history", "brief", "action_board"):
        assert data[part] == baseline[part]


def test_projection_hash_moves_only_when_a_block_moves_and_stays_under_4mib(tmp_path):
    """FIXTURE over real bytes."""
    inputs, receipt = _inputs(tmp_path)
    first = _project(inputs, receipt)
    again = _project(inputs, receipt)
    assert first["receipt"]["content_sha256"] == again["receipt"]["content_sha256"]
    inputs.central["carried"] = {"display_order": {"order": ["xlk"]}}
    changed = _project(inputs, receipt)
    assert changed["receipt"]["content_sha256"] != first["receipt"]["content_sha256"]
    assert len(json.dumps(changed, allow_nan=False).encode()) < 4 * 1024 * 1024
