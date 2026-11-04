#!/usr/bin/env python3
"""Read-only validation of composed source; writes only this folder's receipt.

Uses independent HTML/Decimal checks rather than calling the composition or
clone generator. This is author source verification, not independent design
review, native visual acceptance or browser proof.
"""
from __future__ import annotations

import copy
from decimal import Decimal, ROUND_HALF_UP, getcontext
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
getcontext().prec = 60
HERE = Path(__file__).resolve().parent
PAPER = HERE.parents[1]
EFFECTIVE = HERE / "effective"
CSS = {"display": "flex", "flex-direction": "column", "align-items": "end", "justify-content": "center", "text-align": "right"}
TABLE_ORDER = [0, 1, 2, 3, 4, 5, 6, 8, 9, 7]
# Independently specified raw values from the accepted v3 fixture contract.
DATA = [(286, 207, 201), (267, 189, 185), (500, 346, 343), (177, 118, 116),
        (375, 238, 241), (54, 33, 33), (333, 194, 198), (0, None, None),
        (250, 139, 138), (500, 261, 264)]
EXACT_KEY = "f02.fixture.v3/macro/sector/communication_services/share_above_50d/2026-10-30"


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def load(path):
    return json.loads(path.read_bytes())


class Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.roots = [], []

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "children": [], "chunks": []}
        (self.stack[-1]["children"] if self.stack else self.roots).append(node)
        self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "children": [], "chunks": []}
        (self.stack[-1]["children"] if self.stack else self.roots).append(node)

    def handle_endtag(self, tag):
        assert self.stack.pop()["tag"] == tag

    def handle_data(self, value):
        if self.stack:
            self.stack[-1]["chunks"].append(value)


def parse(value):
    p = Parser()
    p.feed(value)
    assert not p.stack and len(p.roots) == 1
    return p.roots[0]


def css(node):
    return {k.strip(): v.strip() for decl in node["attrs"].get("style", "").split(";") if ":" in decl for k, v in [decl.split(":", 1)]}


def walk(node, path=(0,)):
    yield path, node
    for i, child in enumerate(node["children"]):
        yield from walk(child, path + (i,))


def describe_walk(node, path=None):
    path = path or node["tag"] + "[0]"
    yield path, node
    for i, child in enumerate(node["children"]):
        yield from describe_walk(child, path + "/" + child["tag"] + f"[{i}]")


def direct(node):
    return "".join(node["chunks"]).strip()


def text(node):
    return " ".join(direct(n) for _, n in walk(node) if direct(n))


def rounded(value, places):
    return f"{value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP):.{places}f}"


def step_map(board):
    return {s["key"]: s for s in board["steps"]}


def subtree_steps(board, key):
    included, output = {key}, []
    for step in board["steps"]:
        if step["key"] == key or step["parent"] in included:
            output.append({k: step[k] for k in ("key", "parent", "html")})
            included.add(step["key"])
    return output


def main():
    record = load(HERE / "composition.v2.json")
    for path, expected in record["input_sha256"].items():
        assert sha((PAPER / path).read_bytes()) == expected, ("input drift", path)
    for path, expected in record["outputs"].items():
        assert sha((HERE / path).read_bytes()) == expected, ("output drift", path)
    before_packets = {name: load(PAPER / "repairs/fixture-coherence-v1/effective-spaced" / name) for name in ["mobile-state-boards.json", "supplemental-boards.json"]}
    after_packets = {name: load(EFFECTIVE / name) for name in before_packets}
    before = {b["key"]: b for packet in before_packets.values() for b in packet["boards"]}
    after = {b["key"]: b for packet in after_packets.values() for b in packet["boards"]}
    assert before.keys() == after.keys() and len(after) == 10
    changes = {(c["board_key"], c["step_key"]): c for c in record["changed_steps"]}
    assert len(changes) == 67
    expected_metadata_changes = {}
    for move in record["capture_marker_relocations"]:
        expected_metadata_changes[(move["board_key"], move["from_step"])] = None
        expected_metadata_changes[(move["board_key"], move["to_step"])] = move["capture_state_unchanged"]

    numeric_cells, unchanged_steps, html_steps, elements = 0, 0, 0, 0
    parent_checks = []
    for key in before:
        a, b = before[key], after[key]
        assert {k: v for k, v in a.items() if k != "steps"} == {k: v for k, v in b.items() if k != "steps"}, (key, "board metadata changed")
        assert [s["key"] for s in a["steps"]] == [s["key"] for s in b["steps"]]
        seen = {"board"}
        for old, new in zip(a["steps"], b["steps"]):
            identity = (key, old["key"])
            assert new["key"] not in seen and new["parent"] in seen, (identity, "bad parent order")
            seen.add(new["key"])
            old_meta = {k: v for k, v in old.items() if k != "html"}
            if identity in expected_metadata_changes:
                value = expected_metadata_changes[identity]
                if value is None:
                    old_meta.pop("capture_state")
                else:
                    old_meta["capture_state"] = value
            assert old_meta == {k: v for k, v in new.items() if k != "html"}, (identity, "unaccounted step metadata")
            old_root, new_root = parse(old["html"]), parse(new["html"])
            old_nodes, new_nodes = dict(walk(old_root)), dict(walk(new_root))
            assert old_nodes.keys() == new_nodes.keys(), (identity, "topology changed")
            elements += len(new_nodes)
            assert all(n["tag"] not in {"script", "iframe", "img", "table", "style"} for n in new_nodes.values())
            if identity not in changes:
                assert old["html"] == new["html"], (identity, "unexpected HTML edit")
                unchanged_steps += 1
                continue
            change = changes[identity]
            assert sha(old["html"]) == change["before_html_sha256"]
            assert sha(new["html"]) == change["after_html_sha256"]
            assert re.sub(r'\bstyle="[^"]*"', 'style=""', old["html"]) == re.sub(r'\bstyle="[^"]*"', 'style=""', new["html"]), (identity, "non-style bytes changed")
            allowed = {tuple(map(int, c["input_element_path"].split("."))): c for c in change["cells"]}
            assert len(allowed) == 3
            for path, old_node in old_nodes.items():
                new_node = new_nodes[path]
                assert old_node["tag"] == new_node["tag"] and old_node["chunks"] == new_node["chunks"]
                assert len(old_node["children"]) == len(new_node["children"])
                if path not in allowed:
                    assert old_node["attrs"] == new_node["attrs"], (identity, path, "nonnumeric node changed")
                    continue
                cell = allowed[path]
                assert {k: v for k, v in old_node["attrs"].items() if k != "style"} == {k: v for k, v in new_node["attrs"].items() if k != "style"}
                assert css(old_node) == cell["expected_current_style"]
                assert css(new_node) == {**css(old_node), **CSS}
                assert text(old_node) == text(new_node) == cell["expected_visible_text"]
                assert not old_node["children"] and not new_node["children"]
                numeric_cells += 1
            html_steps += 1
        parent_checks.append({"board_key": key, "steps": len(b["steps"]), "single_roots_and_prior_parent_bindings": True})
    assert (html_steps, numeric_cells, unchanged_steps) == (67, 201, 230)
    assert before_packets["supplemental-boards.json"]["append_to_existing"] == after_packets["supplemental-boards.json"]["append_to_existing"]
    assert all(before[k] == after[k] for k in ["states-matrix", "company-eps-overlay-320", "company-dividend-overlay-320"])

    # Verify complete rows, exact arithmetic and numeric alignment independently.
    table_reports, geometry_reports, chart_reports = [], [], []
    for key, board in after.items():
        steps = step_map(board)
        row_steps = [s for s in board["steps"] if re.fullmatch(r"sector-\d+", s["key"])]
        if row_steps:
            assert [int(s["key"].split("-")[1]) for s in row_steps] == TABLE_ORDER
            assert "↓" in text(parse(steps["table"]["html"]))
            phone = key.endswith("-390")
            for step in row_steps:
                row = parse(step["html"])
                columns = [2, 3, 4] if phone else [1, 2, 3]
                actual = [text(row["children"][i]) for i in columns]
                denom, current, prior = DATA[int(step["key"].split("-")[1])]
                if denom:
                    rate = Decimal(current) * 100 / denom
                    delta = Decimal(current - prior) * 100 / denom
                    expected = [rounded(rate, 1) + "%", ("+" if delta > 0 else "") + rounded(delta, 2), f"{denom} / {denom}"]
                else:
                    expected = ["—", "—", "0 / 82"]
                assert actual == expected, (key, step["key"], actual, expected)
                assert all(all(css(row["children"][i]).get(k) == v for k, v in CSS.items()) for i in columns)
            head = parse(steps["table"]["html"])["children"][0]
            assert all(all(css(head["children"][i]).get(k) == v for k, v in CSS.items()) for i in [1, 2, 3])
            g = board["expected_geometry"]
            widths = [int(css(n)["width"][:-2]) for n in head["children"]]
            if phone:
                assert sum(widths) + 12 == 650
                assert css(parse(steps["table"]["html"]))["width"] == "358px"
                assert all(css(parse(s["html"]))["height"] == "56px" for s in row_steps)
                geometry_reports.append({"board_key": key, "comparison_viewport": 358, "row_intrinsic": 650, "row_height": 56})
            elif key in ["width-768-overlay", "width-1024-overlay"]:
                content = g["viewport"] - g["rail"] - 2 * g["side_padding"]
                assert content == g["primary_without_inspector"] == sum(widths) + 24
                assert content - 320 - 24 == g["hypothetical_docked_primary"] < 640
                assert g["overlay_left"] == g["viewport"] - 440
                assert css(parse(steps["overlay"]["html"]))["width"] == "440px"
                marker_steps = [s for s in board["steps"] if s.get("capture_state", "").startswith("CLOSED_BEFORE_OVERLAY")]
                assert marker_steps == [row_steps[-1]] and row_steps[-1]["key"] == "sector-7"
                ordered_keys = [s["key"] for s in board["steps"]]
                assert ordered_keys.index("sector-7") < ordered_keys.index("backdrop") < ordered_keys.index("overlay")
                assert steps["overlay-contract"]["capture_state"].startswith("OPEN_OVERLAY")
                geometry_reports.append({"board_key": key, "content": content, "hypothetical_docked_primary": content - 344, "overlay": 440, "closed_capture_after_tenth_row": "sector-7"})
            else:
                assert g["viewport_width"] - g["rail"] - 2 * g["main_padding"] == g["main_usable"]
                assert g["main_usable"] - g["dock"] - g["gap"] == g["primary"] == sum(widths) + 24
                assert g["dock"] == 320 and g["gap"] == 24 and g["primary"] >= 640
                assert css(parse(steps["dock"]["html"]))["width"] == "320px"
                geometry_reports.append({"board_key": key, "content": g["main_usable"], "primary": g["primary"], "dock": 320, "gap": 24})
            table_reports.append({"board_key": key, "rows": 10, "raw_count_values_and_delta_pp": True, "descending_rate_energy_last": True, "unknown_not_zero_and_health_zero_retained": True, "numeric_cells": 33})
        if "chart" in steps and (key.startswith("macro-") or key.startswith("width-")):
            svg = re.search(r"<svg\b.*?</svg>", steps["chart"]["html"], re.S).group(0)
            points = [(Decimal(x), Decimal(y)) for x, y in re.findall(r'<circle\b[^>]*cx="([0-9.]+)"[^>]*cy="([0-9.]+)"', svg)]
            width = Decimal(re.search(r'<svg[^>]*width="([0-9.]+)"', svg).group(1))
            expected = [(Decimal(44) + Decimal(i) * (width - 64) / 7, Decimal(20) + (Decimal(80) - Decimal(n) * 100 / 1063) / 40 * 140) for i, n in enumerate([657, 663, None, 679, 673, 687, 697, 709]) if n is not None]
            assert len(points) == len(expected) == 7
            assert all(abs(x - a) < Decimal("0.000002") and abs(y - b) < Decimal("0.000002") for (x, y), (a, b) in zip(points, expected))
            data_lines = re.findall(r'<line\b[^>]*stroke-width="(?:2(?:\.5)?|3)"[^>]*/>', svg)
            assert len(data_lines) == 5
            missing_x = 44 + 2 * (width - 64) / 7
            for line in data_lines:
                a = Decimal(re.search(r'x1="([0-9.]+)"', line).group(1))
                b = Decimal(re.search(r'x2="([0-9.]+)"', line).group(1))
                assert not min(a, b) < missing_x < max(a, b)
            chart_reports.append({"board_key": key, "points": 7, "data_segments": 5, "missing_session": "23 Oct", "raw_count_coordinates_and_no_interpolation": True})
    assert len(table_reports) == 6 and len(chart_reports) == 4

    identity_reports = []
    for key in ["macro-docked-1280", "width-1600-docked", "width-768-overlay", "width-1024-overlay", "macro-zh-evidence-return-390"]:
        steps = step_map(after[key])
        if key in ["macro-docked-1280", "width-1600-docked"]:
            identity = text(parse(steps["dock-source-0"]["html"]))
            clocks = " ".join(text(parse(steps[f"dock-source-{i}"]["html"])) for i in [1, 2, 3])
            baseline = text(parse(steps["dock-footer"]["html"]))
            labels = ["Observation", "Publication", "Retrieved"]
        elif key.startswith("width-"):
            identity = text(parse(steps["overlay-source"]["html"]))
            clocks = text(parse(steps["overlay-clocks"]["html"]))
            baseline = text(parse(steps["overlay-limit"]["html"]))
            labels = ["Observed", "Published", "Retrieved"]
        else:
            identity = text(parse(steps["source-identity"]["html"]))
            clocks = text(parse(steps["source-clocks"]["html"]))
            baseline = text(parse(steps["baseline"]["html"]))
            labels = ["观测", "发布", "获取"]
        assert EXACT_KEY in identity
        assert all(v in clocks for v in labels + ["20:00 UTC", "20:02 UTC", "20:03 UTC"])
        assert all(v in baseline for v in ["118/177", "116/177", "66.67%", "65.54%", "+1.13", "7/8"])
        assert "f02.fixture.v2/macro/" not in json.dumps(after[key], ensure_ascii=False)
        identity_reports.append({"board_key": key, "exact_observation_key": EXACT_KEY, "distinct_observation_publication_retrieval": True, "communication_and_universe_cohorts_distinct": True})
    identity_overlay = load(PAPER / "repairs/observation-identity-clocks-v1/source-overrides.v1.json")
    assert not {(o["board_key"], o["step_key"]) for o in identity_overlay["overrides"]} & {(b["key"], s["key"]) for b in after.values() for s in b["steps"]}

    # Check every clone delta against the composed source and target, independently
    # of compare_clones.py. No undeclared semantic or presentation delta is allowed.
    clone = load(EFFECTIVE / "supplemental-wide-clone.json")
    assert clone["source_input_sha256"] == sha((EFFECTIVE / "mobile-state-boards.json").read_bytes())
    assert clone["supplement_sha256"] == sha((EFFECTIVE / "supplemental-boards.json").read_bytes())
    a, b = after["macro-docked-1280"], after["width-1600-docked"]
    assert clone["pair"]["board_dimension_changes"] == {"width": {"before": 1280, "after": 1600}}
    assert a["artboardStyles"] == b["artboardStyles"] and a["height"] == b["height"]
    totals = {"text_changes": 0, "style_targets": 0, "style_properties": 0, "svg_attribute_targets": 0, "svg_attribute_changes": 0, "vector_subtrees": 0}
    for old, new, planned in zip(a["steps"], b["steps"], clone["pair"]["steps"]):
        assert old["key"] == new["key"] == planned["key"] and old["parent"] == new["parent"] == planned["parent"]
        assert sha(old["html"]) == planned["source_html_sha256"] and sha(new["html"]) == planned["target_html_sha256"]
        old_nodes = dict(describe_walk(parse(old["html"])))
        new_nodes = dict(describe_walk(parse(new["html"])))
        assert old_nodes.keys() == new_nodes.keys()
        delta_by_path = {e["path"]: e for e in planned["element_changes"]}
        seen_deltas = set()
        for path, left in old_nodes.items():
            right = new_nodes[path]
            assert left["tag"] == right["tag"] and len(left["children"]) == len(right["children"])
            actual_delta = {}
            if direct(left) != direct(right):
                actual_delta["text"] = {"before": direct(left), "after": direct(right)}
                totals["text_changes"] += 1
            left_css, right_css = css(left), css(right)
            style_diff = {k: {"before": left_css.get(k), "after": right_css.get(k)} for k in left_css.keys() | right_css.keys() if left_css.get(k) != right_css.get(k)}
            if style_diff:
                actual_delta["css_changes"] = style_diff
                totals["style_targets"] += 1
                totals["style_properties"] += len(style_diff)
            if left["attrs"].get("layer-name") != right["attrs"].get("layer-name"):
                actual_delta["rename"] = {"before": left["attrs"].get("layer-name"), "after": right["attrs"].get("layer-name")}
            attributes = {k: {"before": left["attrs"].get(k), "after": right["attrs"].get(k)} for k in left["attrs"].keys() | right["attrs"].keys() if k not in ["style", "layer-name"] and left["attrs"].get(k) != right["attrs"].get(k)}
            if attributes:
                actual_delta["attribute_changes"] = attributes
                totals["svg_attribute_targets"] += 1
                totals["svg_attribute_changes"] += len(attributes)
            if actual_delta:
                assert path in delta_by_path
                declared = {k: v for k, v in delta_by_path[path].items() if k in ["text", "css_changes", "rename", "attribute_changes"]}
                assert declared == actual_delta, (old["key"], path, "clone delta differs")
                seen_deltas.add(path)
            else:
                assert path not in delta_by_path
        assert seen_deltas == delta_by_path.keys()
        for vector in planned["vector_subtrees"]:
            assert vector["source_svg_html"] in old["html"] and vector["target_svg_html"] in new["html"]
            assert sha(vector["source_svg_html"]) == vector["source_svg_sha256"]
            assert sha(vector["target_svg_html"]) == vector["target_svg_sha256"]
            totals["vector_subtrees"] += 1
    assert len(clone["pair"]["steps"]) == len(a["steps"]) == len(b["steps"]) == 43
    assert all(totals[k] == clone["pair"]["summary"][k] for k in totals)
    historical = load(PAPER / "repairs/fixture-coherence-v1/effective-spaced/supplemental-wide-clone.json")
    invalidated = [(s["key"], side) for old, s in zip(historical["pair"]["steps"], clone["pair"]["steps"]) for side in ["source_html_sha256", "target_html_sha256"] if old[side] != s[side]]
    assert len(invalidated) == 22

    reuse = load(HERE / "subtree-reuse.v2.json")
    zh_source = step_map(after["macro-light-zh-390"])["sector-3"]["html"]
    zh_target = step_map(after["macro-zh-evidence-return-390"])["returned-selected-row"]["html"]
    assert zh_source == zh_target
    assert reuse["candidates"][0]["source_html_sha256"] == reuse["candidates"][0]["target_html_sha256"] == sha(zh_source)
    overlay_768 = subtree_steps(after["width-768-overlay"], "overlay")
    overlay_1024 = subtree_steps(after["width-1024-overlay"], "overlay")
    assert overlay_768 == overlay_1024
    assert reuse["candidates"][1]["source_subtree_sha256"] == reuse["candidates"][1]["target_subtree_sha256"] == sha(encoded(overlay_768))
    pending = load(HERE / "pending-responsive-boards.v2.json")
    assert len(pending["boards"]) == 5 and sum(len(b["steps"]) for b in pending["boards"]) == 169
    assert all(b == after[b["key"]] for b in pending["boards"])
    assert "board_id" not in pending and "node_id" not in pending
    assert after_packets["supplemental-boards.json"]["base_packet_sha256"] == sha((EFFECTIVE / "mobile-state-boards.json").read_bytes())
    for packet in after_packets.values():
        for block, path_key, hash_key in [("fixture_override", "contract", "contract_sha256"), ("fixture_override", "original_packet", "original_packet_sha256"), ("copy_spacing_override", "base_packet", "base_packet_sha256"), ("responsive_alignment_composition", "source_packet", "source_packet_sha256")]:
            entry = packet[block]
            assert sha((EFFECTIVE / entry[path_key]).read_bytes()) == entry[hash_key], (block, path_key)

    report = {
        "schema": "f02.paper.responsive-effective-validation.v2",
        "status": "SOURCE_CHECKS_PASS_NOT_NATIVE_OR_INDEPENDENT_REVIEW",
        "method": "Separate HTML traversal, strict non-style byte comparison, Decimal arithmetic, parent/capture ordering and complete actual-delta/clone-hash comparison; no generator imported.",
        "composition_sha256": sha((HERE / "composition.v2.json").read_bytes()),
        "outputs": record["outputs"],
        "checks": {
            "all_pinned_inputs_unchanged": True,
            "297_step_keys_parents_and_board_geometry_preserved": True,
            "67_HTML_deltas_only_201_numeric_cell_style_attributes": True,
            "all_rendered_text_data_controls_charts_source_ids_and_clocks_byte_preserved": True,
            "230_other_step_HTML_strings_unchanged": True,
            "states_and_both_Company320_boards_unchanged": True,
            "five_existing_append_steps_unchanged": True,
            "both_closed_capture_markers_follow_actual_tenth_Energy_row": True,
            "all_43_clone_step_pairs_match_composed_HTML_hashes_and_exact_deltas": True,
            "22_historical_clone_step_side_hashes_correctly_invalidated": True,
            "three_return_row_numeric_cells_match_aligned_Chinese_source": True,
            "440px_overlay_subtrees_remain_identical": True,
            "responsive_exact_identity_and_market_clocks_verified_no_Company_clock_overlay_misapplied": True,
            "all_local_provenance_paths_resolve_to_expected_bytes": True,
        },
        "counts": {"boards": 10, "steps": 297, "parsed_elements": elements, "HTML_changed_steps": html_steps, "numeric_cells": numeric_cells, "unchanged_HTML_steps": unchanged_steps, "pending_boards": 5, "pending_steps": 169, "capture_marker_relocations": 2},
        "parent_checks": parent_checks, "tables": table_reports, "geometry": geometry_reports,
        "charts": chart_reports, "identity_and_clocks": identity_reports,
        "clone": {"step_pairs": 43, "totals": totals, "historical_step_side_hashes_invalidated": 22, "artboard_width_delta": 320},
        "capture_marker_relocations": record["capture_marker_relocations"],
        "paper_calls": 0, "browser_calls": 0, "native_mutations": 0,
        "native_mapping_or_visual_acceptance": False, "independent_reviewer_verdict": False,
        "unresolved_native_effect_unchanged": record["unresolved_native_effect"],
    }
    path = HERE / "validation.v2.json"
    path.write_bytes(encoded(report))
    print(json.dumps({"status": report["status"], "counts": report["counts"], "validation_sha256": sha(path.read_bytes()), "clone": report["clone"], "mismatches": []}, indent=2))


if __name__ == "__main__":
    main()
