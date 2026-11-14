"""Optional typed blocks (lane 8 R1/R2, lane 7 depth, lane 1 v1.1 rows) read `unavailable` unless produced.

REAL    The committed `site/` member bytes (session 2026-11-06) carry none of the
        twelve blocks, so every block reads `unavailable/not_produced`: that is
        what the real producers emit today and nothing is invented. With the
        carry step run over the same committed artifacts (the builder the nightly
        pipeline uses), the five v1.1 row blocks are `available` with values
        equal to the carry, in the wire's order after the untouched seven.
FIXTURE Synthetic documents (labelled per test) prove the `available` path, shape
        refusal (`invalid_shape`), NaN refusal, the 64 KiB cap (516 KiB for the
        five row blocks), the `block_too_large` stub reason, the entitled-only
        gate and that a bad block never changes another part of the projection.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from engine.sector_native_view import (_TYPED_ROW_BLOCK_MAX_BYTES,
                                       project_sector_view, typed_blocks_of)
from lib import sector_generation_contract as contract
from lib.sector_generation_wire import encode_sector_generation
import tests.test_sector_population as population
from tests.test_sector_population import PUBLISHED, SESSION, _real_bundle

NAMES = ("r1_rising_priced_share", "r2_display_order", "r2_hazard_qualification",
         "etf_flows", "confluence", "bottoming_watch", "theme_table",
         "confluence_universe_sp500", "confluence_universe_nasdaq",
         "confluence_universe_russell", "confluence_universe_baskets", "theme_rows")
#: the five lane-1 v1.1 row blocks (wire §1) - the last five of the wire order
ROW_NAMES = NAMES[7:]
CONFLUENCE = {"us": {"n": 1}, "hk": {"n": 2}, "cn": {"n": 3}, "ca": {"n": 4}}


def _universe_block(owner_word, arrays, **override):
    """A minimal valid carried universe row block (wire §2 shape)."""
    block = {"source": "marketdata/x.json", "as_of": "2026-11-06", "as_of_field": "as_of",
             "group_arrays": list(arrays),
             "data": {"universe": owner_word, **{array: [] for array in arrays}}}
    block.update(override)
    return block


ROW_BLOCKS = {
    "confluence_universe_sp500": _universe_block("sp500_subsectors", ("subsectors", "sectors")),
    "confluence_universe_nasdaq": _universe_block("nasdaq_subsectors", ("subsectors", "sectors")),
    "confluence_universe_russell": _universe_block("russell_subsectors", ("subsectors", "sectors")),
    "confluence_universe_baskets": _universe_block("curated_baskets", ("baskets",)),
    "theme_rows": {"source": "basketdata/si_handoff.json#theme_context.themes",
                   "as_of": "2026-11-06", "rows": [{"id": "memory_storage"}]},
}


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
        "bottoming_watch": {"rows": []}, "theme_table": {"rows": [2]},
        **deepcopy(ROW_BLOCKS)}
    blocks = _project(inputs, receipt)["data"]["typed_blocks"]
    assert all(blocks[n]["status"] == "available" and blocks[n]["reason"] is None for n in NAMES)
    assert blocks["confluence"]["value"] == CONFLUENCE
    assert blocks["r1_rising_priced_share"]["value"]["missing_members"] == 2
    assert blocks["confluence_universe_baskets"]["value"]["data"]["universe"] == "curated_baskets"
    preview = _project(inputs, receipt, "preview")["data"]["typed_blocks"]
    assert preview["r1_rising_priced_share"]["status"] == "available"
    assert all(preview[n] == {"status": "unavailable", "reason": "audience_not_entitled",
                              "value": None} for n in NAMES[3:])


def test_fixture_row_block_stub_reads_by_its_reason(tmp_path):
    """FIXTURE (wire §4 rule 1): a carried ``block_too_large`` stub reads
    ``unavailable/block_too_large`` with a null value; a stub with any other
    reason is just another malformed value (``invalid_shape``)."""
    inputs, receipt = _inputs(tmp_path)
    inputs.central["carried"] = {
        "confluence_universe_sp500": {"source": "marketdata/subsector_confluence.json",
                                      "as_of": "2026-11-06", "as_of_field": "as_of",
                                      "status": "unavailable", "reason": "block_too_large"},
        "confluence_universe_nasdaq": {"source": "marketdata/subsector_confluence_nasdaq.json",
                                       "as_of": "2026-11-09 09:38 UTC",
                                       "as_of_field": "generated_utc",
                                       "status": "unavailable", "reason": "producer_refused"},
        "theme_rows": {"source": "basketdata/si_handoff.json#theme_context.themes",
                       "as_of": "2026-11-06", "status": "unavailable",
                       "reason": "block_too_large"},
    }
    blocks = _project(inputs, receipt)["data"]["typed_blocks"]
    assert blocks["confluence_universe_sp500"] == {"status": "unavailable",
                                                   "reason": "block_too_large", "value": None}
    assert blocks["theme_rows"] == {"status": "unavailable", "reason": "block_too_large",
                                    "value": None}
    assert blocks["confluence_universe_nasdaq"] == {"status": "unavailable",
                                                    "reason": "invalid_shape", "value": None}


def test_fixture_stub_to_preview_audience_still_reads_audience_not_entitled(tmp_path):
    """SF-3/M5 (review r1): the audience gate comes FIRST - a carried
    ``block_too_large`` stub served to the preview audience reads
    ``audience_not_entitled``, never ``block_too_large``."""
    inputs, receipt = _inputs(tmp_path)
    inputs.central["carried"] = {
        "confluence_universe_sp500": {"source": "x", "as_of": "2026-11-06",
                                      "status": "unavailable", "reason": "block_too_large"},
        "theme_rows": {"source": "x", "as_of": "2026-11-06",
                       "status": "unavailable", "reason": "block_too_large"},
    }
    preview = typed_blocks_of(_project(inputs, receipt, "preview")["data"])
    for name in ("confluence_universe_sp500", "theme_rows"):
        assert preview[name] == {"status": "unavailable", "reason": "audience_not_entitled",
                                 "value": None}, name
    # and the projection emits no typed_blocks key of its own: every reason is
    # audience_not_entitled or not_produced
    assert "typed_blocks" not in _project(inputs, receipt, "preview")["data"]


@pytest.mark.parametrize("name,owner,key,bad", [
    ("r1_rising_priced_share", "carried", "sector_central_r1", [1, 2]),
    ("r2_display_order", "carried", "display_order", {"order": [float("nan")]}),
    ("r2_hazard_qualification", "central", "hazard_qualification", "text"),
    ("etf_flows", "carried", "etf_flows", "text"),
    ("confluence", "carried", "confluence", {"us": {}}),
    ("theme_table", "carried", "theme_table", {"blob": "x" * (64 * 1024 + 1)}),
    # the five row blocks, wire §4 shape checks (each is otherwise a valid block)
    ("confluence_universe_sp500", "carried", "confluence_universe_sp500",
     _universe_block("sp500_subsectors", ("subsectors", "sectors"), as_of=None)),
    ("confluence_universe_nasdaq", "carried", "confluence_universe_nasdaq",
     _universe_block("sp500_subsectors", ("subsectors", "sectors"))),  # wrong owner word
    ("confluence_universe_russell", "carried", "confluence_universe_russell",
     _universe_block("russell_subsectors", ("sectors", "subsectors"))),  # array order
    ("confluence_universe_baskets", "carried", "confluence_universe_baskets",
     _universe_block("curated_baskets", ("baskets",), group_arrays=["subsectors"])),
    ("confluence_universe_sp500", "carried", "confluence_universe_sp500",
     _universe_block("sp500_subsectors", ("subsectors", "sectors"),
                     data={"universe": "sp500_subsectors", "subsectors": {}, "sectors": []})),
    ("theme_rows", "carried", "theme_rows", {"source": "x", "as_of": "2026-11-06",
                                             "rows": {"id": "x"}}),
    ("theme_rows", "carried", "theme_rows", {"blob": "x" * (_TYPED_ROW_BLOCK_MAX_BYTES + 1)}),
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


def test_fixture_row_block_cap_boundary_available_at_cap_invalid_one_byte_over(tmp_path):
    """FIXTURE: a row block encoded at exactly ``_TYPED_ROW_BLOCK_MAX_BYTES`` is
    available; one byte over is ``invalid_shape`` (never trimmed to fit)."""
    def with_pad(n):
        return {"source": "x", "as_of": "2026-11-06", "rows": [{"id": "a", "pad": "y" * n}]}
    base = len(json.dumps(with_pad(0), ensure_ascii=False, allow_nan=False,
                          sort_keys=True, separators=(",", ":")).encode("utf-8"))
    pad = _TYPED_ROW_BLOCK_MAX_BYTES - base  # every added ASCII byte is one encoded byte
    inputs, receipt = _inputs(tmp_path)
    inputs.central["carried"] = {"theme_rows": with_pad(pad)}
    at_cap = _project(inputs, receipt)["data"]["typed_blocks"]["theme_rows"]
    assert at_cap["status"] == "available" and len(at_cap["value"]["rows"][0]["pad"]) == pad
    inputs.central["carried"] = {"theme_rows": with_pad(pad + 1)}
    over = _project(inputs, receipt)["data"]["typed_blocks"]["theme_rows"]
    assert over == {"status": "unavailable", "reason": "invalid_shape", "value": None}


def test_real_carry_serves_twelve_blocks_in_wire_order_five_row_blocks_available(tmp_path):
    """REAL: with the carry step run over the committed artifacts (exactly what
    ``build_sector_central`` does nightly), the projection serves twelve typed
    blocks in the wire §4 order - the first seven unchanged, the five row blocks
    ``available`` with values equal to the carry - and a preview projection gates
    all nine entitled-only blocks."""
    inputs, receipt = _inputs(tmp_path, carried=True)
    data = _project(inputs, receipt)["data"]
    blocks = data["typed_blocks"]
    assert tuple(blocks) == NAMES
    carried = inputs.central["carried"]
    for name in ROW_NAMES:
        assert blocks[name] == {"status": "available", "reason": None,
                                "value": carried[name]}, name
    assert blocks["confluence"]["value"] == carried["confluence"]  # incumbent too
    preview = _project(inputs, receipt, "preview")["data"]["typed_blocks"]
    assert all(preview[n] == {"status": "unavailable", "reason": "audience_not_entitled",
                              "value": None} for n in NAMES[3:])


def test_real_generation_envelope_keeps_room_for_five_row_blocks(tmp_path):
    """REAL (wire §1): B - the entitled legacy projection of a real generation
    WITHOUT the five row blocks - plus five times the 512 KiB carry cap stays
    inside the 4 MiB encode budget minus 256 KiB of headroom; with the five the
    encoded generation is under the same budget and the capture hash moves."""
    def serve(tag, carried):
        (tmp_path / tag).mkdir(parents=True, exist_ok=True)
        raw, identity = _real_bundle(tmp=tmp_path / tag, carried=False)
        inputs, receipt = contract._capture_view(
            member_bytes=raw, input_identity=identity, generation_id=f"envelope-{tag}",
            published_at=PUBLISHED.isoformat(), now=PUBLISHED)
        inputs.central["carried"] = carried
        output = project_sector_view(inputs, receipt, audience="entitled")
        body = encode_sector_generation(
            audience="entitled", source_session=SESSION,
            published_at=PUBLISHED.isoformat(), qualification="accepted",
            projection=output)
        return output, body

    full = population._real_carry_blocks()
    legacy = {name: block for name, block in full.items() if name not in ROW_NAMES}
    out_b, body_b = serve("b", legacy)
    out_a, body_a = serve("a", full)
    B, A = len(body_b), len(body_a)
    assert B + 5 * (512 * 1024) <= 4 * 1024 * 1024 - 256 * 1024
    assert A < 4 * 1024 * 1024 and A > B
    assert out_a["receipt"]["content_sha256"] != out_b["receipt"]["content_sha256"]
    assert tuple(out_a["data"]["typed_blocks"]) == NAMES
    for name in ROW_NAMES:
        assert out_b["data"]["typed_blocks"][name]["reason"] == "not_produced", name


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
