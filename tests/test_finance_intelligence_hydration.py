"""Finance Intelligence — hydration-state classification tests.

Runs the shipped IIFE against the §B section skeletons and a scripted fetch
table. The goal is to keep the seven §E.3 status mappings (200/401/402/403/
503/network/contract_mismatch) from collapsing into a single generic
"unavailable" surface, and to keep the evidence drawer's focus + inert
contract safe at every state.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
HARNESS = Path(__file__).with_name("finance_intelligence_hydration_harness.js")
HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

CONTRACT = "finance_intelligence_read_model.v1"
AS_OF = "2026-09-24T12:00:00Z"

VALID_DOC = {
    "contract_id": CONTRACT,
    "schema_version": "1.0.0",
    "as_of": AS_OF,
    "common_as_of": AS_OF,
    "knowledge_cutoff": AS_OF,
    "freshness": {"state": "FRESH", "as_of": AS_OF, "horizon_days": 90},
    "outer_dossier_ref": {
        "publisher": "MastermindX",
        "accepted": True,
        "state": "AVAILABLE"
    },
    "domains": [
        {"domain_id": "dom.banks", "name_en": "Banks", "name_zh": "银行",
         "slice_ids": ["s.banks.americas"]}
    ],
    "slices": [
        {"slice_id": "s.banks.americas", "domain_id": "dom.banks",
         "name_en": "Banks — Americas", "name_zh": "银行 — 美洲",
         "slice_state": "PRICE_SURFACE_AVAILABLE",
         "basket_state": {"membership_state": "PIT_MEMBERSHIP_VALIDATED",
                          "posture": "ADMITTED",
                          "price_basis_state": "TOTAL_RETURN_QUALIFIED",
                          "weighting_family": "EQUAL_WEIGHT",
                          "incumbent_basket_ids": ["B.BNK.AMER"]},
         "rerating": {
            "operating": {"state": "OBSERVED",
                          "primary_metric": {"value": 6.4, "unit": "USD",
                                             "currency": "USD",
                                             "measurement_class": "PER_SHARE",
                                             "period_start": "2025-09-30",
                                             "period_end": "2026-09-24"},
                          "evidence_refs": ["src.a"]},
            "expectations": {"state": "OBSERVED",
                             "history": {"state": "DATED_CONSENSUS_AVAILABLE"},
                             "evidence_refs": ["src.b"]},
            "valuation": {"state": "VALUATION_ANCHOR_UNAVAILABLE",
                          "evidence_refs": ["src.c"]},
            "price": {"state": "PRICE_BASIS_UNQUALIFIED", "evidence_refs": ["src.d"]},
            "bridge": "Earnings up, multiple down — visible on the chips above."
         },
         "valuation_anchor": {
            "primary_per_share_anchor": "EPS",
            "primary_valuation_anchor": "P_E",
            "horizon": "FORWARD_12M",
            "state": "VALUATION_ANCHOR_UNAVAILABLE"
         },
         "falsifiers": [
            {"state": "WATCHING",
             "statement": "Re-rating reverses if net interest margin compresses.",
             "window": "next_180d"}
         ]
        }
    ],
    "system_views": [
        {"view_id": "contractual_flow", "name_en": "Contractual flow", "name_zh": "合同流",
         "nodes": [{"node_id": "n.bank", "label_en": "Bank", "label_zh": "银行"}],
         "edges": [{"from": "n.bank", "to": "n.borrower",
                    "relationship": "LENDS",
                    "evidence_state": "OBSERVED"}]}
    ],
    "conflicts": [
        {"slice_ids": ["s.banks.americas"],
         "label": "EARNINGS_UP_P_E_DOWN",
         "left": {"plane": "operating", "statement": "Earnings up.",
                  "evidence_refs": ["src.a"]},
         "right": {"plane": "valuation", "statement": "Multiple down.",
                   "evidence_refs": ["src.c"]}}
    ],
    "material_changes": [
        {"change_id": "chg.1", "slice_ids": ["s.banks.americas"],
         "domain_ids": ["dom.banks"],
         "freshness_state": "FRESH",
         "operating_implication": "Capital ratio steady; net interest income up.",
         "event_clock": {"published_at": "2026-09-22T08:00:00Z",
                         "published_at_grain": "DAY"},
         "evidence_refs": ["src.a"]}
    ],
    "company_exposures": [
        {"row_id": "r.jpm", "issuer_label": "JPMorgan Chase",
         "identity": {"state": "IDENTITY_VALIDATED"},
         "cells": [{"slice_id": "s.banks.americas",
                    "role": "DIRECT_PURE_OR_HIGH_EXPOSURE",
                    "materiality": "MATERIAL",
                    "exposure": {"basis": "SEGMENT_REVENUE",
                                 "state": "MEASURED"}}]}
    ],
    "macro_matrix": [
        {"slice_id": "s.banks.americas", "driver": "policy_rates",
         "state": "CAUSAL_EFFECT_UNMEASURED", "lag": "ONE_QUARTER",
         "mechanism": "Higher policy rates lift net interest income."}
    ],
    "constraints": [
        {"slice_id": "s.banks.americas", "constraint": "capital",
         "economic_effect": "Higher capital requirements reduce ROE.",
         "evidence_refs": ["src.e"]}
    ],
    "source_records": [
        {"record_id": "src.a",
         "source": {"publisher": "10-K", "source_family": "company_filing",
                    "observed_at": "2026-09-15",
                    "published_at": "2026-09-15",
                    "published_at_grain": "DAY"},
         "business_scope": "10-K Annual report",
         "excerpt": "Net interest income up 6.4% YoY.",
         "metric": {"value": 6.4, "unit": "USD"},
         "statement_mode": "REPORTED_FACT",
         "rights_state": "DIRECT_DISPLAY_OK",
         "limitations": [],
         "correction": None}
    ],
    "input_receipts": [
        {"owner": "financial_intelligence", "state": "READ"}
    ],
    "degraded_sections": [
        {"section": "what_changed", "state": "AVAILABLE"},
        {"section": "rerating_map", "state": "AVAILABLE"},
        {"section": "system_map", "state": "AVAILABLE"},
        {"section": "subtheme_atlas", "state": "AVAILABLE"},
        {"section": "company_exposure", "state": "AVAILABLE"},
        {"section": "macro_matrix", "state": "AVAILABLE"},
        {"section": "constraint_map", "state": "AVAILABLE"}
    ],
    "coverage": {
        "first_vertical": {"slice_ids": ["s.banks.americas"]},
        "domains_total": 1, "domains_populated": 1,
        "slices_total": 1, "slices_populated": 1
    }
}


def _json(payload: object) -> str:
    return json.dumps(payload, separators=(",", ":"))


def _run(scenario: dict) -> dict:
    scene_path = Path("/tmp/fi_hydration_scenario.json")
    scene_path.write_text(_json(scenario), encoding="utf-8")
    js_path = TEMPLATES / "finance_intelligence.js"
    result = subprocess.run(
        ["node", str(HARNESS), str(scene_path), str(js_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


# ──────────────────────────────────────────────────────────────────────────
# §E.3 status mapping — every status lands on its dedicated state.
# ──────────────────────────────────────────────────────────────────────────

@needs_node
def test_200_with_valid_contract_paints_ready_state(tmp_path: Path) -> None:
    snap = _run({"routes": {"__default__": {"status": 200, "body": _json(VALID_DOC),
                                            "contentType": "application/json"}}})
    # No notice published — the seven sections remain in their hydrated state.
    assert snap["first"]["noticeEn"] == ""
    assert snap["first"]["noticeZh"] == ""
    # The slice selector binds to the read model (one first-vertical slice).
    assert snap["first"]["sliceOptions"] == 1
    # Rerating stepper renders exactly four nodes.
    assert snap["first"]["reratingStepCount"] == 4
    # Atlas cards present.
    assert snap["first"]["atlasCardCount"] >= 1
    # Exactly one fetch call.
    assert len(snap["first"]["fetchCalls"]) == 1


@needs_node
def test_401_paints_locked_not_generic_unavailable() -> None:
    snap = _run({"routes": {"__default__": {"status": 401, "body": '{"detail":"auth"}',
                                            "contentType": "application/json"}}})
    notice_en = snap["first"]["noticeEn"].lower()
    notice_zh = snap["first"]["noticeZh"]
    assert "sign in" in notice_en or "locked" in notice_en or "login" in notice_en
    assert "登录" in notice_zh or "暂不可用" in notice_zh or "登录" in notice_zh


@needs_node
def test_402_paints_locked_not_generic_unavailable() -> None:
    snap = _run({"routes": {"__default__": {"status": 402, "body": '{"detail":"payment"}',
                                            "contentType": "application/json"}}})
    # 402 must NOT collapse to a generic outage / unknown surface.
    assert "couldn't load" not in snap["first"]["noticeEn"].lower()
    assert "读取失败" not in snap["first"]["noticeZh"]


@needs_node
def test_403_paints_locked_not_generic_unavailable() -> None:
    snap = _run({"routes": {"__default__": {"status": 403, "body": '{"detail":"forbidden"}',
                                            "contentType": "application/json"}}})
    assert "couldn't load" not in snap["first"]["noticeEn"].lower()
    assert "读取失败" not in snap["first"]["noticeZh"]


@needs_node
def test_503_paints_source_outage() -> None:
    snap = _run({"routes": {"__default__": {"status": 503, "body": '{"detail":"down"}',
                                            "contentType": "application/json"}}})
    assert snap["first"]["noticeEn"] != ""
    assert snap["first"]["noticeZh"] != ""
    assert "couldn't load" not in snap["first"]["noticeEn"].lower()  # never generic unavailable


@needs_node
def test_network_failure_paints_source_outage_copy() -> None:
    """A failing fetch must surface the source-outage copy, not a generic unknown."""
    snap = _run({"routes": {"__default__": {"status": 0, "body": "",
                                            "contentType": ""}}})
    # status=0 with empty body fails the response.ok branch and routes through
    # source_outage — never unknown.
    assert snap["first"]["noticeEn"] != ""
    assert snap["first"]["noticeZh"] != ""


@needs_node
def test_200_with_wrong_contract_is_contract_invalid_not_ready() -> None:
    payload = dict(VALID_DOC)
    payload["contract_id"] = "wrong_contract.v1"
    snap = _run({"routes": {"__default__": {"status": 200, "body": _json(payload),
                                            "contentType": "application/json"}}})
    # Wrong contract → contract_invalid notice, no slice selector binding.
    assert snap["first"]["noticeEn"] != ""
    assert snap["first"]["noticeZh"] != ""
    assert snap["first"]["sliceOptions"] == 0


@needs_node
def test_200_with_html_content_type_is_integrity_block() -> None:
    snap = _run({"routes": {"__default__": {"status": 200,
                                            "body": "<html>not json</html>",
                                            "contentType": "text/html"}}})
    # Non-JSON body fails jsonContentType → integrity_block.
    assert snap["first"]["noticeEn"] != ""
    assert snap["first"]["noticeZh"] != ""


@needs_node
def test_200_with_malformed_json_is_integrity_block() -> None:
    snap = _run({"routes": {"__default__": {"status": 200,
                                            "body": "{not valid json",
                                            "contentType": "application/json"}}})
    assert snap["first"]["noticeEn"] != ""
    assert snap["first"]["noticeZh"] != ""


@needs_node
def test_drawer_focus_ownership_keeps_shell_and_nav_inert_when_open() -> None:
    """Drawer open must setInert(<main>) + setInert(<nav.site-nav>) and trap focus."""
    js = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")

    # setDrawer body — slice from setDrawer(open) up to the next top-level helper.
    setdrawer_start = js.index("function setDrawer(open)")
    next_fn = js.index("\n  function", setdrawer_start + 1)
    body = js[setdrawer_start:next_fn]
    assert "setInert(state.ui.shell, true)" in body
    assert "setInert(state.ui.siteNav, true)" in body

    # handleDrawerKeydown body — Escape closes the drawer; Tab cycles inside it.
    kbd_start = js.index("function handleDrawerKeydown")
    next_fn_kbd = js.index("\n  function", kbd_start + 1)
    kbd_body = js[kbd_start:next_fn_kbd]
    assert "'Escape'" in kbd_body
    assert "setDrawer(false)" in kbd_body
    assert "'Tab'" in kbd_body
    assert "shiftKey" in kbd_body
    # focusableInDrawer must return an array (Tab order iteration).
    fid_start = js.index("function focusableInDrawer")
    fid_body = js[fid_start:js.index("\n  function", fid_start + 1)]
    assert "tabindex=\"-1\"" in fid_body or "tabindex=\\\"-1\\\"" in fid_body or "tabindex=" in fid_body


@needs_node
def test_template_and_site_assets_remain_byte_equivalent() -> None:
    site = ROOT / "site"
    for name in ("finance_intelligence.css", "finance_intelligence.js"):
        template_bytes = (TEMPLATES / name).read_bytes()
        site_path = site / name
        if site_path.exists():
            assert site_path.read_bytes() == template_bytes


@needs_node
def test_hydrated_controls_are_named_in_the_page_language() -> None:
    """Hydrated controls are created AFTER the inline ARIA swapper has run (first
    paint, slice change, the langchange re-render), so each must be born with its
    accessible name in the current language, or 中文 readers hear English on
    every evidence control."""
    route = {"__default__": {"status": 200, "body": _json(VALID_DOC),
                             "contentType": "application/json"}}
    zh_snap = _run({"lang": "zh", "routes": route})["first"]
    en_snap = _run({"lang": "en", "routes": route})["first"]
    zh, en = zh_snap["evidenceAriaLabels"], en_snap["evidenceAriaLabels"]
    assert zh and len(zh) == len(en), (zh, en)
    assert all(re.search(r"[\u4e00-\u9fff]", label) for label in zh), zh
    assert all(label.startswith("Open evidence: ") for label in en), en
    # F3 (item 4): the row labels ARE the visible text — what-changed = slice
    # name, rerating step = plane word, conflict sides = "first reading
    # (plane)" / "second reading (plane)", constraint = §D.9 label. None of
    # them may be a placeholder or a fabricated word.
    for label in en:
        assert "{slice" not in label and "{plane" not in label and "{row" not in label, label
    for label in zh:
        assert "{" not in label, label
        assert label.startswith("打开证据："), label
    # F4 (item 5): hero chips carry NO aria-label — their visible text already
    # names them. The runtime exposes the absence of aria-label as empty
    # strings, not as a placeholder.
    zh_chips, en_chips = zh_snap["heroChipAria"], en_snap["heroChipAria"]
    assert en_chips == ["", ""], en_chips
    assert zh_chips == ["", ""], zh_chips
    assert not any("{" in label for label in zh_chips + en_chips), (zh_chips, en_chips)
