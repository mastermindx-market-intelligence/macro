#!/usr/bin/env python3
"""Compose F02 responsive authoring inputs locally; never call Paper or GitHub.

All writes are contained in this new repair directory. Historical inputs,
applied receipts, native exports and shared indexes are read-only inputs.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PAPER = HERE.parents[1]
EFFECTIVE = HERE / "effective"

SOURCE_HASHES = {
    "repairs/fixture-coherence-v1/effective-spaced/mobile-state-boards.json": "276572f02660d9b6be25473bdf039b28aea10ad31a1d0813bec6812caf804399",
    "repairs/fixture-coherence-v1/effective-spaced/supplemental-boards.json": "e65ecfcec783c752651634541d6f9917857e2da42e4686bdae0535cd089aaa2e",
    "repairs/numeric-alignment-390-v1/source-overrides.v1.json": "dc1c1c7a3b7bc148642a74908c0791ace9b8482b228ab96718481de96872ff67",
    "repairs/numeric-alignment-390-v1/pending-width-source-overrides.v1.json": "abf8f62551f6c08f48cca930fda67a81f9760e047cac7fba4efc059932cff824",
    "repairs/observation-identity-clocks-v1/source-overrides.v1.json": "b94b7db39f4735b2eb749475e4aba1f513792b1c6fe6365b0c15954f994b8512",
    "repairs/fixture-coherence-v1/fixture-contract.json": "d3329c2608fe14fb4fd592f971c945b6ac5a860d8c9836ee485cfa0151b58433",
    "repairs/fixture-coherence-v1/effective-spaced/supplemental-wide-clone.json": "522dba06859cb98e349528d8cb197a8e63ba128e60e8ca070f3bd4d5448422d9",
    "mobile-inputs/compare_clones.py": "4dc007913843fd1aac76830261b71a0941439bc497fb728a4f1d9c83a984bc87",
}
MOBILE_SOURCE = "repairs/fixture-coherence-v1/effective-spaced/mobile-state-boards.json"
SUPPLEMENT_SOURCE = "repairs/fixture-coherence-v1/effective-spaced/supplemental-boards.json"
PHONE_OVERLAY = "repairs/numeric-alignment-390-v1/source-overrides.v1.json"
WIDTH_OVERLAY = "repairs/numeric-alignment-390-v1/pending-width-source-overrides.v1.json"
IDENTITY_OVERLAY = "repairs/observation-identity-clocks-v1/source-overrides.v1.json"
PENDING_KEYS = [
    "macro-docked-1280", "macro-zh-evidence-return-390",
    "width-768-overlay", "width-1024-overlay", "width-1600-docked",
]
FILE_ID = "01M312VSDSZFVT45674GDVJVZN"


def sha(value: str | bytes) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def dump(path: Path, value) -> str:
    assert path.resolve().is_relative_to(HERE)
    raw = encoded(value)
    path.write_bytes(raw)
    return sha(raw)


def steps_of(board):
    result = {step["key"]: step for step in board["steps"]}
    assert len(result) == len(board["steps"])
    return result


def subtree_steps(board, key):
    admitted, result = {key}, []
    for step in board["steps"]:
        if step["key"] == key or step["parent"] in admitted:
            result.append({k: step[k] for k in ("key", "parent", "html")})
            admitted.add(step["key"])
    return result


def main():
    inputs = {}
    for relative, expected in SOURCE_HASHES.items():
        raw = (PAPER / relative).read_bytes()
        assert sha(raw) == expected, (relative, "source changed; reconcile before composing")
        if relative.endswith(".json"):
            inputs[relative] = json.loads(raw)

    mobile = copy.deepcopy(inputs[MOBILE_SOURCE])
    supplement = copy.deepcopy(inputs[SUPPLEMENT_SOURCE])
    boards = {b["key"]: b for b in mobile["boards"] + supplement["boards"]}
    assert len(boards) == 10
    board_sources = {b["key"]: MOBILE_SOURCE for b in mobile["boards"]}
    board_sources.update({b["key"]: SUPPLEMENT_SOURCE for b in supplement["boards"]})
    before_html = {
        (b["key"], s["key"]): s["html"]
        for b in mobile["boards"] + supplement["boards"] for s in b["steps"]
    }
    changed = []
    for overlay_path in [PHONE_OVERLAY, WIDTH_OVERLAY]:
        for override in inputs[overlay_path]["overrides"]:
            board_key, step_key = override["board_key"], override["step_key"]
            source_path = board_sources[board_key]
            step = steps_of(boards[board_key])[step_key]
            assert override["source_packet_sha256"] == SOURCE_HASHES[source_path]
            assert sha(step["html"]) == override["source_step_html_sha256"]
            assert sha(step["html"]) in override["accepted_before_overlay_html_sha256"]
            assert sha(override["replacement_html"]) == override["replacement_html_sha256"]
            assert len(override["cell_overrides"]) == 3
            step["html"] = override["replacement_html"]
            changed.append({
                "board_key": board_key, "step_key": step_key,
                "source_packet": source_path, "source_packet_sha256": SOURCE_HASHES[source_path],
                "overlay": overlay_path, "overlay_sha256": SOURCE_HASHES[overlay_path],
                "before_html_sha256": override["source_step_html_sha256"],
                "after_html_sha256": override["replacement_html_sha256"],
                "cells": [
                    {k: cell[k] for k in ("input_element_path", "column_role", "expected_visible_text", "expected_current_style", "style_delta")}
                    for cell in override["cell_overrides"]
                ],
            })
    assert len(changed) == 66

    # The prior packet deliberately flagged, but did not repair, the returned row.
    # Reuse the exact aligned Chinese source HTML, rather than reconstructing it.
    flag = inputs[WIDTH_OVERLAY]["related_pending_return_row_flag"]
    source_pair = ("macro-light-zh-390", "sector-3")
    return_pair = (flag["board_key"], flag["step_key"])
    assert return_pair == ("macro-zh-evidence-return-390", "returned-selected-row")
    returned = steps_of(boards[return_pair[0]])[return_pair[1]]
    source = steps_of(boards[source_pair[0]])[source_pair[1]]
    assert sha(returned["html"]) == flag["source_step_html_sha256"]
    assert returned["html"] == before_html[source_pair]
    source_change = next(c for c in changed if (c["board_key"], c["step_key"]) == source_pair)
    returned["html"] = source["html"]
    return_change = {
        "board_key": return_pair[0], "step_key": return_pair[1],
        "source_packet": SUPPLEMENT_SOURCE, "source_packet_sha256": SOURCE_HASHES[SUPPLEMENT_SOURCE],
        "overlay": "derived from exact source-equal Chinese sector-3 overlay",
        "overlay_sha256": SOURCE_HASHES[PHONE_OVERLAY],
        "before_html_sha256": flag["source_step_html_sha256"],
        "after_html_sha256": sha(returned["html"]),
        "cells": copy.deepcopy(source_change["cells"]),
        "source_board_key": source_pair[0], "source_step_key": source_pair[1],
        "native_ids": "NOT_ASSIGNED; source paths are HTML anchors only",
    }
    changed.append(return_change)
    assert len(changed) == 67

    # The v3 sort moved Energy last, but the historical closed-state marker
    # remained on Materials. The source-only capture instruction must follow
    # the actual final row; no rendered data or interaction copy is changed.
    capture_relocations = []
    for key in ("width-768-overlay", "width-1024-overlay"):
        board = boards[key]
        row_steps = [s for s in board["steps"] if s["key"].startswith("sector-")]
        marked = [s for s in board["steps"] if s.get("capture_state", "").startswith("CLOSED_BEFORE_OVERLAY")]
        assert len(row_steps) == 10 and len(marked) == 1
        assert marked[0]["key"] == "sector-9" and row_steps[-1]["key"] == "sector-7"
        marker = marked[0].pop("capture_state")
        assert "capture_state" not in row_steps[-1]
        row_steps[-1]["capture_state"] = marker
        capture_relocations.append({
            "board_key": key, "from_step": "sector-9", "to_step": "sector-7",
            "capture_state_unchanged": marker,
            "reason": "Energy sorts after Materials in v3; capture the closed state only after all ten rows exist.",
            "rendered_html_changed_by_this_relocation": False,
        })

    # The observation/clock correction owns six desktop/fault steps. It has
    # no responsive target to apply; do not silently replay it into these files.
    identity_targets = {(o["board_key"], o["step_key"]) for o in inputs[IDENTITY_OVERLAY]["overrides"]}
    responsive_targets = {(b["key"], s["key"]) for b in boards.values() for s in b["steps"]}
    assert not identity_targets & responsive_targets

    EFFECTIVE.mkdir(exist_ok=True)
    for name, packet, source_path in [
        ("mobile-state-boards.json", mobile, MOBILE_SOURCE),
        ("supplemental-boards.json", supplement, SUPPLEMENT_SOURCE),
    ]:
        packet["fixture_override"]["contract"] = "../../fixture-coherence-v1/fixture-contract.json"
        packet["fixture_override"]["original_packet"] = "../../../mobile-inputs/" + name
        packet["copy_spacing_override"]["base_packet"] = "../../fixture-coherence-v1/effective/" + name
        packet["responsive_alignment_composition"] = {
            "revision": 2,
            "status": "PREPARED_NOT_APPLIED",
            "source_packet": "../../fixture-coherence-v1/effective-spaced/" + name,
            "source_packet_sha256": SOURCE_HASHES[source_path],
            "phone_overlay": "../../numeric-alignment-390-v1/source-overrides.v1.json",
            "phone_overlay_sha256": SOURCE_HASHES[PHONE_OVERLAY],
            "pending_width_overlay": "../../numeric-alignment-390-v1/pending-width-source-overrides.v1.json",
            "pending_width_overlay_sha256": SOURCE_HASHES[WIDTH_OVERLAY],
            "composition_record": "../composition.v2.json",
            "rendered_text_data_geometry_parent_order_preserved": True,
            "native_application": "Not established by this source packet. Reconcile current targets; do not replay existing construction steps.",
        }
    mobile_sha = dump(EFFECTIVE / "mobile-state-boards.json", mobile)
    supplement["base_packet_sha256"] = mobile_sha
    supplement_sha = dump(EFFECTIVE / "supplemental-boards.json", supplement)

    spec = importlib.util.spec_from_file_location("f02_responsive_clone_comparison", PAPER / "mobile-inputs/compare_clones.py")
    comparator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = comparator
    spec.loader.exec_module(comparator)
    narrow, wide = boards["macro-docked-1280"], boards["width-1600-docked"]
    pair = comparator.compare(narrow, wide)
    pair["board_dimension_changes"] = {
        k: {"before": narrow[k], "after": wide[k]} for k in ("width", "height") if narrow[k] != wide[k]
    }
    assert pair["input_structure_equivalent"] and not pair["structural_exceptions"]
    assert pair["summary"] == inputs["repairs/fixture-coherence-v1/effective-spaced/supplemental-wide-clone.json"]["pair"]["summary"]
    pair["layout_exceptions"] = [
        "Only a freshly read native 1280 source matching the effective v3/alignment inputs can be a clone source. The local plan establishes no native mapping or edit permission.",
        "Primary grows from 664px to 984px; the 320px dock and 24px gap stay fixed. Apply the declared 320px artboard-width increase and all 71 native width/style targets.",
        "The chart has 20 SVG geometry-attribute changes across one subtree. Resolve actual editable vector nodes or replace only that observed mapped chart subtree with its exact target SVG.",
        "Preserve numeric end alignment in both widths. A later native source repair requires a bounded new comparison, not reuse of stale source HTML hashes.",
        "Actual descendantIdMap, source readback, final content fit and screenshot/JSX evidence remain required. F01 joint release and browser interaction proof remain separate.",
    ]
    clone = {
        "schema": "f02.paper.clone-preparation.v1",
        "status": "LOCAL_PREPARATION_NOT_APPLIED",
        "fixture_version": "f02.fixture.v3", "copy_spacing_revision": 1,
        "responsive_alignment_revision": 2,
        "source_input": "mobile-state-boards.json", "source_input_sha256": mobile_sha,
        "supplement": "supplemental-boards.json", "supplement_sha256": supplement_sha,
        "historical_clone": "../../fixture-coherence-v1/effective-spaced/supplemental-wide-clone.json",
        "historical_clone_sha256": SOURCE_HASHES["repairs/fixture-coherence-v1/effective-spaced/supplemental-wide-clone.json"],
        "pair": pair, "paper_calls": 0, "browser_calls": 0,
        "native_id_binding": "UNOBSERVED_IN_THIS_PREPARATION",
    }
    clone_sha = dump(EFFECTIVE / "supplemental-wide-clone.json", clone)

    overlay_768 = subtree_steps(boards["width-768-overlay"], "overlay")
    overlay_1024 = subtree_steps(boards["width-1024-overlay"], "overlay")
    assert overlay_768 == overlay_1024
    return_override = {
        "schema": "f02.paper.return-row-source-alignment.v2",
        "status": "PREPARED_NOT_APPLIED",
        "correction": return_change, "replacement_html": returned["html"],
        "paper_calls": 0, "browser_calls": 0,
        "execution_boundary": "Independent source authoring only. This does not clear the existing Chinese-board footer effect or grant any native clone/replay authority.",
    }
    return_sha = dump(HERE / "return-row-alignment.v2.json", return_override)
    reuse = {
        "schema": "f02.paper.responsive-subtree-reuse.v2",
        "status": "SOURCE_EQUALITY_ONLY_NOT_NATIVE_QUALIFICATION",
        "source_packets": {"effective/mobile-state-boards.json": mobile_sha, "effective/supplemental-boards.json": supplement_sha},
        "candidates": [
            {
                "source_board_key": source_pair[0], "source_step_key": source_pair[1],
                "target_board_key": return_pair[0], "target_step_key": return_pair[1],
                "source_html_sha256": sha(source["html"]), "target_html_sha256": sha(returned["html"]),
                "byte_equal": True,
                "dependency": "Source row alignment is prepared only. Direct construction from the new target HTML does not require native cloning. A clone requires same-carrier current source inspection and actual descendant mapping; preserve any unresolved source-target fence.",
            },
            {
                "source_board_key": "width-768-overlay", "source_step_key": "overlay",
                "target_board_key": "width-1024-overlay", "target_step_key": "overlay",
                "include_descendants": True, "subtree_steps": len(overlay_768),
                "source_subtree_sha256": sha(encoded(overlay_768)), "target_subtree_sha256": sha(encoded(overlay_1024)),
                "byte_equal": True,
                "dependency": "Only the 440px sheet and descendants match. Viewport, backdrop, rail and primary widths differ. Native mapping and current target parents remain unobserved here.",
            },
        ],
        "paper_calls": 0, "browser_calls": 0,
    }
    reuse_sha = dump(HERE / "subtree-reuse.v2.json", reuse)
    pending = {
        "schema": "f02.paper.native-construction.v1",
        "status": "PREPARED_NOT_APPLIED",
        "system_version": mobile["system_version"], "file_id": FILE_ID,
        "scope": "The five responsive boards absent from the retained f7c25c4b9870cff260c2a4b998be18d6c04d36d0 checkpoint; current native state must be checked before construction.",
        "source_packets": {"effective/mobile-state-boards.json": mobile_sha, "effective/supplemental-boards.json": supplement_sha},
        "boards": [copy.deepcopy(boards[key]) for key in PENDING_KEYS],
        "optional_clone_plan": "effective/supplemental-wide-clone.json", "optional_clone_plan_sha256": clone_sha,
        "subtree_reuse_plan": "subtree-reuse.v2.json", "subtree_reuse_plan_sha256": reuse_sha,
        "construction_requirement": "Do not replay already-applied steps. Resolve exact file/page/current board identities, keep original effect fences, and capture the complete closed table after sector-7 before adding an overlay.",
        "paper_calls": 0, "browser_calls": 0,
    }
    pending_sha = dump(HERE / "pending-responsive-boards.v2.json", pending)

    composition = {
        "schema": "f02.paper.responsive-effective-composition.v2",
        "status": "PREPARED_SOURCE_COMPOSITION_NOT_APPLIED",
        "assignment_sha": "6e1862867193ec6486a22001a0e4fb515da20448",
        "retained_f02_head": "f7c25c4b9870cff260c2a4b998be18d6c04d36d0",
        "procedure_pin": "910803421beca53ca25145392725ab2d84c7a8e9",
        "input_paths_relative_to": "f02/paper", "input_sha256": SOURCE_HASHES,
        "precedence": [
            "fixture-coherence-v1/effective-spaced: complete v3 count-first, spacing and Energy-last source",
            "observation-identity-clocks-v1: checked; its six consumer/fault targets are disjoint from these packets",
            "numeric-alignment-390-v1: 22 phone plus 44 pending-width exact guarded step overlays",
            "responsive-effective-v2: 3-cell Chinese returned-row alignment and two closed-capture marker relocations",
            "Recomputed clone plan binds both newly composed packet hashes and all 43 step-pair HTML hashes",
        ],
        "changed_steps": changed,
        "capture_marker_relocations": capture_relocations,
        "metadata_only_changes": [
            "Resolve inherited fixture/original/copy-spacing provenance paths relative to this new effective directory.",
            "Supplement base_packet_sha256 now binds the composed mobile packet.",
            "Add composition provenance and rebuild wide-clone packet/step hashes; no native IDs are assigned.",
        ],
        "identity_clock_overlay": {
            "input": IDENTITY_OVERLAY, "sha256": SOURCE_HASHES[IDENTITY_OVERLAY],
            "targeted_steps": len(identity_targets), "responsive_target_intersections": 0,
            "disposition": "No applicability. Preserve the already correct responsive exact identity and market clocks; Company fiscal-clock repair remains owned by its separate packet.",
        },
        "counts": {
            "complete_input_boards": 10, "complete_input_board_steps": sum(len(b["steps"]) for b in boards.values()),
            "html_style_only_changed_steps": len(changed), "numeric_cells": sum(len(c["cells"]) for c in changed),
            "phone_existing_source_steps": 22, "phone_numeric_cells": 66,
            "pending_width_source_steps": 44, "pending_width_numeric_cells": 132,
            "return_row_source_steps": 1, "return_row_numeric_cells": 3,
            "capture_marker_relocations": len(capture_relocations),
            "pending_responsive_boards": len(pending["boards"]), "pending_responsive_steps": sum(len(b["steps"]) for b in pending["boards"]),
            "untouched_existing_append_steps": sum(len(g["steps"]) for g in supplement["append_to_existing"]),
        },
        "outputs": {
            "effective/mobile-state-boards.json": mobile_sha,
            "effective/supplemental-boards.json": supplement_sha,
            "effective/supplemental-wide-clone.json": clone_sha,
            "return-row-alignment.v2.json": return_sha,
            "subtree-reuse.v2.json": reuse_sha,
            "pending-responsive-boards.v2.json": pending_sha,
        },
        "native_effects": 0, "paper_calls": 0, "browser_calls": 0,
        "no_original_inputs_or_exports_changed": True,
        "unresolved_native_effect": {
            "operation_id": "f02-c2-macro-light-zh-390-chart-footer-20261103-01",
            "file_id": FILE_ID, "target_node_id": "7J4-0",
            "disposition": "Not reconciled by this source work. Root retains same-carrier target-scoped recovery and all current source-law gates.",
        },
    }
    assert composition["counts"]["complete_input_board_steps"] == 297
    assert composition["counts"]["numeric_cells"] == 201
    assert composition["counts"]["pending_responsive_steps"] == 169
    for relative, expected in SOURCE_HASHES.items():
        assert sha((PAPER / relative).read_bytes()) == expected, (relative, "input changed during composition")
    composition_sha = dump(HERE / "composition.v2.json", composition)
    print(json.dumps({"status": composition["status"], "counts": composition["counts"], "composition_sha256": composition_sha, "outputs": composition["outputs"], "clone_summary": pair["summary"]}, indent=2))


if __name__ == "__main__":
    main()
