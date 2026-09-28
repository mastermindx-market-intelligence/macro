"""Finance Intelligence — hydration-state classification tests.

Runs the shipped IIFE against the §B section skeletons and a scripted fetch
table. The goal is to keep the seven §E.3 status mappings (200/401/402/403/
503/network/contract_mismatch) from collapsing into a single generic
"unavailable" surface, and to keep the evidence drawer's focus + inert
contract safe at every state.
"""
from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
HARNESS = Path(__file__).with_name("finance_intelligence_hydration_harness.js")
HAS_NODE = shutil.which("node") is not None
needs_node = pytest.mark.skipif(not HAS_NODE, reason="node not on PATH")

CONTRACT = "finance_intelligence_read_model.v1"
AS_OF = "2026-09-24T12:00:00Z"

# A PARTIAL harness document: the fields the painters read, not the whole T1
# contract (validate_contract rejects it). Contract conformance is painted from
# the T2 composer's own output in
# test_a_contract_valid_read_model_paints_without_leaking_machine_values.
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
                    "locator": "Item 7, net interest income table",
                    "observed_at": "2026-09-15",
                    "published_at": "2026-09-15",
                    "published_at_grain": "DAY"},
         "business_scope": "10-K Annual report",
         "excerpt": "Net interest income up 6.4% YoY.",
         "metric": {"value": 6.4, "unit": "USD"},
         "statement_mode": "REPORTED_FACT",
         "rights_state": "DIRECT_DISPLAY_OK",
         # T1 schema: an OBJECT of five required strings ($defs/source_record).
         # The old `[]` was schema-invalid and hid a drawer that always painted blank.
         "limitations": {"establishes": "Reported net interest income for the year.",
                         "does_not_establish": "Any forward margin path.",
                         "coverage": "One issuer, one fiscal year.",
                         "source_dependence": "The issuer's own filing.",
                         "expiry_trigger": "The next annual filing."},
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
    # One scenario file per call: a fixed /tmp path is shared by every
    # parallel worker and every checkout on the host.
    with tempfile.TemporaryDirectory() as tmp:
        scene_path = Path(tmp) / "scenario.json"
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
    """Keyboard gate, driven not read (T11 r3 replaced a source-string check).
    Pressing an evidence button opens the drawer, makes the page and nav
    behind it inert and moves focus inside; Tab and Shift+Tab stay inside;
    Escape closes it, lifts the inert state and returns focus to the button."""
    trigger = '[data-fi-mount="what-changed-list"] .fi-evidence-trigger'
    # One tick for the hashchange task the trigger queues, one for the drawer's
    # requestAnimationFrame focus move.
    press = [{"do": "press", "selector": trigger}, {"do": "tick"}, {"do": "tick"}]
    out = _run({"routes": _route(VALID_DOC),
                "actions": press + [{"do": "key", "key": "Tab"},
                                    {"do": "key", "key": "Tab", "shiftKey": True}]})
    root = _dom(out["second"])
    drawer = root.one("aside", id="evidence-drawer")
    assert not drawer.hidden and "is-open" in drawer.classes
    for behind in (root.one("main"), root.one("nav")):
        assert "inert" in behind.attrs and behind.attrs.get("aria-hidden") == "true", behind.tag
    assert out["second"]["active"]["id"] == "fi-close-evidence", out["second"]["active"]

    out = _run({"routes": _route(VALID_DOC), "actions": press + [{"do": "key", "key": "Escape"}]})
    root = _dom(out["second"])
    assert root.one("aside", id="evidence-drawer").hidden
    for behind in (root.one("main"), root.one("nav")):
        assert "inert" not in behind.attrs and "aria-hidden" not in behind.attrs, behind.tag
    active = out["second"]["active"]
    assert active["isPressed"] and active["connected"], active


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


# ──────────────────────────────────────────────────────────────────────────
# T11 round 3 (Opus review MAJOR-1): behaviour, not source spelling. The
# harness serialises its live tree ("dom") and records every painter
# innerHTML write ("htmlWrites"); the tests below parse both, so each one
# fails on what a reader would see or hear, whatever the JS happens to say.
# ──────────────────────────────────────────────────────────────────────────

_VOID_TAGS = frozenset({"area", "base", "br", "col", "embed", "hr", "img",
                        "input", "link", "meta", "source", "track", "wbr"})


class _El:
    """A parsed element: tag, attrs, parent and children (elements or text)."""

    def __init__(self, tag: str, attrs: dict, parent: "_El | None") -> None:
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.children: list = []

    @property
    def classes(self) -> set:
        return set((self.attrs.get("class") or "").split())

    @property
    def hidden(self) -> bool:
        return "hidden" in self.attrs

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def spoken(self) -> str:
        """Text a screen reader reads: aria-hidden subtrees are skipped."""
        return "".join(c if isinstance(c, str) else
                       ("" if c.attrs.get("aria-hidden") == "true" else c.spoken())
                       for c in self.children)

    def elements(self) -> list:
        return [c for c in self.children if isinstance(c, _El)]

    def walk(self):
        for child in self.elements():
            yield child
            yield from child.walk()

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def find(self, tag: str | None = None, cls: str | None = None, **attrs: str) -> list:
        """Descendants by tag, class and exact attrs (data_view -> data-view)."""
        wanted = {k.replace("_", "-"): v for k, v in attrs.items()}
        return [el for el in self.walk()
                if (tag is None or el.tag == tag)
                and (cls is None or cls in el.classes)
                and all(el.attrs.get(k) == v for k, v in wanted.items())]

    def one(self, tag: str | None = None, cls: str | None = None, **attrs: str) -> "_El":
        hits = self.find(tag, cls, **attrs)
        assert len(hits) == 1, (tag, cls, attrs, len(hits))
        return hits[0]

    def previous_element(self) -> "_El | None":
        siblings = self.parent.elements() if self.parent is not None else []
        idx = siblings.index(self)
        return siblings[idx - 1] if idx > 0 else None


class _Tree(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _El("#root", {}, None)
        self._node = self.root
        self.duplicate_attrs: list = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        names = [name for name, _ in attrs]
        if len(names) != len(set(names)):
            self.duplicate_attrs.append((tag, names))
        el = _El(tag, dict(attrs), self._node)
        self._node.children.append(el)
        if tag not in _VOID_TAGS:
            self._node = el

    def handle_endtag(self, tag: str) -> None:
        for node in (self._node, *self._node.ancestors()):
            if node.tag == tag and node.parent is not None:
                self._node = node.parent
                return

    def handle_data(self, data: str) -> None:
        self._node.children.append(data)


def _parse(markup: str) -> _Tree:
    tree = _Tree()
    tree.feed(markup)
    tree.close()
    return tree


def _dom(snap: dict) -> _El:
    return _parse(snap["dom"]).root


def _route(doc: dict) -> dict:
    return {"__default__": {"status": 200, "body": _json(doc),
                            "contentType": "application/json"}}


def _node(node_id: str, en: str, zh: str) -> dict:
    return {"node_id": node_id, "label_en": en, "label_zh": zh,
            "node_type": "INSTITUTION", "slice_ids": ["s.banks.americas"],
            "expandable": False, "children_ids": []}


def _two_view_doc() -> dict:
    doc = copy.deepcopy(VALID_DOC)
    doc["system_views"].append({
        "view_id": "public_equity_economics", "name_en": "Equity economics",
        "name_zh": "股权经济",
        "nodes": [_node("n.issuer", "Issuer", "发行人"),
                  _node("n.holder", "Holder", "持有人")],
        "edges": [{"from": "n.holder", "to": "n.issuer",
                   "relationship": "EARNS_FEE_FROM", "evidence_state": "INFERRED"}]})
    return doc


def _wide_doc(n: int) -> dict:
    """n first-vertical slices, n company rows, n macro rows and n system nodes."""
    doc = copy.deepcopy(VALID_DOC)
    base = doc["slices"][0]
    ids = [base["slice_id"]] + [f"s.banks.r{i:02d}" for i in range(1, n)]
    doc["slices"] = [dict(copy.deepcopy(base), slice_id=sid,
                          name_en=f"Banks {i}", name_zh=f"银行 {i}")
                     for i, sid in enumerate(ids)]
    doc["domains"][0]["slice_ids"] = ids
    doc["coverage"].update(slices_total=n, slices_populated=n)
    doc["coverage"]["first_vertical"]["slice_ids"] = ids
    doc["macro_matrix"] = [dict(doc["macro_matrix"][0], slice_id=sid) for sid in ids]
    cell = doc["company_exposures"][0]["cells"][0]
    doc["company_exposures"] = [
        {"row_id": f"r.{i}", "issuer_label": f"Issuer {i}",
         "identity": {"state": "IDENTITY_VALIDATED"},
         "cells": [dict(cell, slice_id=sid)]} for i, sid in enumerate(ids)]
    doc["system_views"][0]["nodes"] = [_node(f"n.{i}", f"Node {i}", f"节点 {i}")
                                       for i in range(n)]
    return doc


@needs_node
def test_painted_markup_never_repeats_an_attribute() -> None:
    """Item 1: a repeated class= keeps only the first, so the state chip lost
    `fi-step-chip` and every rule keyed on it."""
    snap = _run({"routes": _route(_wide_doc(11))})["first"]
    assert snap["htmlWrites"], "the harness recorded no painter writes"
    for markup in snap["htmlWrites"]:
        tree = _parse(markup)
        assert not tree.duplicate_attrs, (tree.duplicate_attrs, markup[:160])
    chips = _dom(snap).find("span", "fi-step-chip")
    assert len(chips) == 4 and all("fi-chip" in chip.classes for chip in chips)


@needs_node
def test_painters_write_no_inline_style() -> None:
    """Design law: material decisions live in governed CSS. The atlas and macro
    chip rows were the last style= writers (T11 r3). Genuinely data-dependent
    geometry would need an explicit exemption here, not a quiet style=."""
    snap = _run({"routes": _route(_wide_doc(11))})["first"]
    for markup in snap["htmlWrites"]:
        for el in _parse(markup).root.walk():
            assert "style" not in el.attrs, (el.tag, el.attrs)


@needs_node
def test_state_chips_carry_the_state_their_rules_select() -> None:
    """Item 2: the step chip's data-state is its plane's state, and the atlas
    slice chip carries data-state-slice; those are the attributes the CSS
    state rules select."""
    root = _dom(_run({"routes": _route(VALID_DOC)})["first"])
    steps = root.find("li", "fi-rerating-step")
    assert [step.attrs.get("data-state-marker") for step in steps] == [
        "OBSERVED", "OBSERVED", "VALUATION_ANCHOR_UNAVAILABLE", "PRICE_BASIS_UNQUALIFIED"]
    for step in steps:
        assert step.one("span", "fi-step-chip").attrs.get("data-state") == \
            step.attrs["data-state-marker"]
    chip = root.one("span", "fi-slice-chip")
    assert chip.attrs.get("data-state-slice") == "PRICE_SURFACE_AVAILABLE"
    css = (TEMPLATES / "finance_intelligence.css").read_text(encoding="utf-8")
    assert '.fi-step-chip[data-state="OBSERVED"]' in css


@needs_node
@pytest.mark.parametrize("lang,prefix,words", [
    ("en", "Open evidence: ", ["Operating", "Expectations", "Valuation", "Price"]),
    ("zh", "打开证据：", ["经营", "市场预期", "估值", "价格"]),
])
def test_rerating_evidence_buttons_are_named_by_their_whole_plane_word(
        lang: str, prefix: str, words: list) -> None:
    """T11 r3: labelFor() already returns ONE string, so indexing it named the
    four buttons "O", "E", "V", "P" (ZH: 打开证据：营). The name is the whole word."""
    root = _dom(_run({"lang": lang, "routes": _route(VALID_DOC)})["first"])
    buttons = root.one(data_fi_mount="rerating-steps").find("button")
    assert [b.attrs.get("aria-label") for b in buttons] == [prefix + w for w in words]


@needs_node
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_system_edges_name_their_nodes_never_their_ids(lang: str) -> None:
    """Item 3: an edge reads as words; an id missing from the view's nodes
    reads "Unlabelled node", and no raw node id reaches the reader."""
    root = _dom(_run({"lang": lang, "routes": _route(VALID_DOC)})["first"])
    section = root.one("section", id="system-map")
    statement = section.one("span", "fi-system-edge-statement").text()
    if lang == "en":
        assert statement == "Bank — lends → Unlabelled node"
    else:
        assert statement.startswith("银行 — ") and statement.endswith(" → 未标注节点"), statement
    assert "n.bank" not in section.text() and "n.borrower" not in section.text()


@needs_node
def test_system_nodes_past_eight_fold_into_one_counted_disclosure() -> None:
    """Item 3 (§C.10): 11 nodes paint 8 in the panel list and 3 behind one
    "Show 3 more nodes" disclosure; 8 nodes paint no disclosure at all."""
    panel = _dom(_run({"routes": _route(_wide_doc(11))})["first"]).one("div", "fi-view-panel")
    first = [el for el in panel.elements() if el.tag == "ul"]
    assert len(first) == 1 and len(first[0].find("li")) == 8
    disc = panel.one("details", "fi-disc")
    assert disc.one("summary").one("span", "l-en").text() == "Show 3 more nodes"
    assert [li.attrs["data-node-id"] for li in disc.find("li")] == ["n.8", "n.9", "n.10"]
    eight = _wide_doc(11)
    eight["system_views"][0]["nodes"] = eight["system_views"][0]["nodes"][:8]
    panel8 = _dom(_run({"routes": _route(eight)})["first"]).one("div", "fi-view-panel")
    assert not panel8.find("details", "fi-disc")
    first8 = [el for el in panel8.elements() if el.tag == "ul"]
    assert len(first8) == 1 and len(first8[0].find("li")) == 8


_UNNAMEABLE_TAGS = frozenset({"span", "div", "p", "strong", "em", "b", "i", "code",
                              "sub", "sup", "del", "ins", "small"})
_UNNAMEABLE_ROLES = frozenset({"generic", "presentation", "none", "paragraph", "caption",
                               "code", "deletion", "emphasis", "insertion", "strong",
                               "subscript", "superscript"})


@needs_node
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_every_named_element_has_a_role_that_can_carry_a_name(lang: str) -> None:
    """Item 6: ARIA 1.2 prohibits naming generic and paragraph roles; a name on
    a bare <span> or <div> is dropped by assistive tech. Every painted button
    also speaks words, not just an arrow glyph."""
    root = _dom(_run({"lang": lang, "routes": _route(_two_view_doc())})["first"])
    named = [el for el in root.walk()
             if "aria-label" in el.attrs or "aria-labelledby" in el.attrs]
    assert named, "nothing on the hydrated page carries a name"
    for el in named:
        role = el.attrs.get("role")
        if role:
            assert role not in _UNNAMEABLE_ROLES, (el.tag, el.attrs)
        else:
            assert el.tag not in _UNNAMEABLE_TAGS, (el.tag, el.attrs)
    buttons = root.one("main").find("button")
    assert buttons
    for button in buttons:
        name = button.attrs.get("aria-label") or button.spoken()
        assert re.search(r"[A-Za-z一-鿿]", name), button.attrs


_LIVE_ROLES = frozenset({"status", "alert", "log", "marquee", "timer"})


@needs_node
def test_hydration_paints_no_live_region_and_the_page_owns_exactly_one() -> None:
    """Item 7: a live region painted into rows would announce the dossier on
    every repaint; the page's single polite region is the notice."""
    out = _run({"routes": _route(_wide_doc(11)), "actions": [{"do": "lang", "lang": "zh"}]})
    writes = out["second"]["htmlWrites"]
    assert len(writes) > len(out["first"]["htmlWrites"]), "langchange repainted nothing"
    for markup in writes:
        for el in _parse(markup).root.walk():
            assert "aria-live" not in el.attrs and el.attrs.get("role") not in _LIVE_ROLES, \
                (el.tag, el.attrs)
    page = _parse((TEMPLATES / "finance_intelligence.html.j2").read_text(encoding="utf-8")).root
    live = [el for el in page.walk()
            if "aria-live" in el.attrs or el.attrs.get("role") in _LIVE_ROLES]
    assert len(live) == 1 and "fi-notice-live" in live[0].classes, \
        [(el.tag, el.attrs) for el in live]


@needs_node
def test_langchange_returns_focus_to_the_same_view_tab_on_the_new_dom() -> None:
    """Item 8: the repaint rebuilds the tabs, so focus must land on the NEW tab
    for the reader's view (connected, selected, in the tab order), not stay
    on the detached node and not reset to view 1."""
    out = _run({"lang": "en", "routes": _route(_two_view_doc()),
                "actions": [{"do": "clickTab", "index": 1}, {"do": "lang", "lang": "zh"}]})
    active = out["second"]["active"]
    assert active["tag"] == "button" and "fi-view-tab" in active["className"], active
    assert active["dataView"] == "public_equity_economics", active
    assert (active["tabindex"], active["ariaSelected"]) == ("0", "true"), active
    assert active["connected"] and not active["isPriorFocus"], active
    root = _dom(out["second"])
    assert not root.one("div", "fi-view-panel", data_view="public_equity_economics").hidden
    assert root.one("div", "fi-view-panel", data_view="contractual_flow").hidden


@needs_node
def test_langchange_leaves_focus_outside_the_tabs_where_it_was() -> None:
    """Item 8: focus on the slice picker stays there across the repaint, and
    the reader's chosen view stays selected."""
    out = _run({"lang": "en", "routes": _route(_two_view_doc()),
                "actions": [{"do": "clickTab", "index": 1},
                            {"do": "focus", "selector": "#fi-slice-select"},
                            {"do": "lang", "lang": "zh"}]})
    active = out["second"]["active"]
    assert active["tag"] == "select" and active["isPriorFocus"] and active["connected"], active
    tab = _dom(out["second"]).one("button", "fi-view-tab", data_view="public_equity_economics")
    assert tab.attrs.get("aria-selected") == "true"


@needs_node
def test_phone_cards_past_eight_fold_into_a_counted_disclosure() -> None:
    """Item 9: 11 rows paint 8 phone cards plus a "See all 11" disclosure that
    holds the other 3, with none dropped and none painted twice; 8 rows keep
    the disclosure hidden."""
    root = _dom(_run({"routes": _route(_wide_doc(11))})["first"])
    for first, more, rest, card, words in (
            ("exposure-cards", "exposure-cards-more", "exposure-cards-list",
             "fi-exposure-card", "See all 11 companies"),
            ("macro-cards", "macro-cards-more", "macro-cards-list",
             "fi-macro-card", "See all 11 slices")):
        shown = root.one(data_fi_mount=first).find("li", card)
        folded = root.one(data_fi_mount=rest).find("li", card)
        assert (len(shown), len(folded)) == (8, 3), first
        names = [li.one("p", "fi-cell-role").text() for li in shown + folded]
        assert len(set(names)) == 11, names
        disc = root.one("details", data_fi_mount=more)
        assert not disc.hidden and "fi-disc" in disc.classes
        assert disc.one("summary").one("span", "l-en").text() == words
    root8 = _dom(_run({"routes": _route(_wide_doc(8))})["first"])
    for more in ("exposure-cards-more", "macro-cards-more"):
        assert root8.one("details", data_fi_mount=more).hidden, more


_PROSE = ("Earnings up, multiple down — visible on the chips above.",
          "Re-rating reverses if net interest margin compresses.",
          "Earnings up.", "Multiple down.",
          "Capital ratio steady; net interest income up.",
          "Higher policy rates lift net interest income.",
          "Higher capital requirements reduce ROE.")


def _in_english(el: _El) -> bool:
    return any(node.attrs.get("lang") == "en" for node in (el, *el.ancestors()))


def _assert_one_note_per_prose_section(root: _El) -> int:
    notes_total = 0
    for section in root.find("section", "fi-section"):
        notes = section.find("p", "fi-srclang-note")
        has_prose = any(el.attrs.get("lang") == "en" for el in section.walk())
        assert len(notes) == (1 if has_prose else 0), (section.attrs.get("id"), len(notes))
        for note in notes:
            assert note.parent is section and note.classes == {"fi-srclang-note", "l-zh"}
            assert "lang" not in note.attrs
            head = note.previous_element()
            assert head is not None and "fi-section-head" in head.classes, section.attrs.get("id")
        notes_total += len(notes)
    return notes_total


@needs_node
def test_zh_marks_payload_prose_english_and_notes_each_prose_section_once() -> None:
    """Item 10: payload prose is English inside lang="en"; each section holding
    it gets ONE page-language note right under its head, and two more
    langchange repaints neither stack nor lose it."""
    out = _run({"lang": "zh", "routes": _route(VALID_DOC),
                "actions": [{"do": "langchange"}, {"do": "langchange"}]})
    for snap in (out["first"], out["second"]):
        root = _dom(snap)
        for prose in _PROSE:
            hosts = [el for el in root.walk()
                     if any(isinstance(c, str) and prose in c for c in el.children)]
            assert hosts and all(_in_english(h) for h in hosts), prose
        assert _assert_one_note_per_prose_section(root) == 4


@needs_node
def test_a_placeholder_only_section_gets_no_note_and_en_gets_none() -> None:
    """Item 10: page-language placeholders carry no lang, so a section whose
    payload prose is empty holds no note; the EN page never shows the line."""
    doc = copy.deepcopy(VALID_DOC)
    doc["constraints"][0]["economic_effect"] = ""
    doc["macro_matrix"][0]["mechanism"] = ""
    root = _dom(_run({"lang": "zh", "routes": _route(doc)})["first"])
    for sid in ("constraint-map", "macro-matrix"):
        section = root.one("section", id=sid)
        assert not [el for el in section.walk() if el.attrs.get("lang") == "en"], sid
        assert not section.find("p", "fi-srclang-note"), sid
    assert _assert_one_note_per_prose_section(root) == 2
    en = _dom(_run({"lang": "en", "routes": _route(VALID_DOC)})["first"])
    assert not en.find("p", "fi-srclang-note")


_LIMITS = ("establishes", "does_not_establish", "coverage", "source_dependence",
           "expiry_trigger")


def _drawer(lang: str, record_patch: dict | None = None) -> _El:
    doc = copy.deepcopy(VALID_DOC)
    doc["source_records"][0].update(record_patch or {})
    snap = _run({"lang": lang, "routes": _route(doc), "hash": "#evidence=src.a"})["first"]
    drawer = _dom(snap).one("aside", id="evidence-drawer")
    assert not drawer.hidden, "the #evidence= hash did not open the drawer"
    return drawer


def _drawer_field(drawer: _El, label: str) -> _El:
    for pair in drawer.one("dl").elements():
        dt, dd = pair.elements()
        if dt.text() == label:
            return dd
    raise AssertionError(f"no drawer row {label!r}")


def _limitation_items(drawer: _El) -> list:
    return [el for el in drawer.walk() if "data-limitation" in el.attrs]


@needs_node
def test_drawer_paints_the_five_limitations_in_schema_order() -> None:
    """MAJOR-2: `limitations` is an object of five strings (T1 schema); the
    drawer paints each under its plain-word label, payload marked English,
    plus the source locator."""
    drawer = _drawer("en")
    items = _limitation_items(drawer)
    assert [li.attrs["data-limitation"] for li in items] == list(_LIMITS)
    expected = VALID_DOC["source_records"][0]["limitations"]
    labels = ("Establishes", "Does not establish", "Coverage", "Depends on",
              "Stops holding when")
    for li, key, label in zip(items, _LIMITS, labels):
        assert li.one("span", "fi-limitation-label").text() == label
        text = li.one("span", "fi-limitation-text")
        assert text.text() == expected[key] and text.attrs.get("lang") == "en", key
    locator = _drawer_field(drawer, "Locator")
    assert locator.text() == "Item 7, net interest income table"
    assert locator.attrs.get("lang") == "en"


@needs_node
@pytest.mark.parametrize("lang,label,words", [
    ("en", "Coverage", "Not stated"),
    ("zh", "覆盖范围", "未说明"),
])
def test_a_limitation_the_record_omits_says_so_in_page_words(
        lang: str, label: str, words: str) -> None:
    """A field the record leaves out says so in the reader's language, with no
    lang="en" on the page's own words."""
    limitations = dict(VALID_DOC["source_records"][0]["limitations"])
    del limitations["coverage"]
    items = _limitation_items(_drawer(lang, {"limitations": limitations}))
    assert len(items) == 5
    li = items[_LIMITS.index("coverage")]
    assert li.one("span", "fi-limitation-label").text() == label
    text = li.one("span", "fi-limitation-text")
    assert text.text() == words and "lang" not in text.attrs
    assert "fi-limitation-missing" in text.classes


@needs_node
@pytest.mark.parametrize("value,shown", [(0, "0 USD"), (6.4, "6.4 USD"), (None, "Not stated")])
def test_a_stated_zero_is_a_value_and_only_null_is_not_stated(value, shown) -> None:
    """With no excerpt the Value row reads the metric: a stated 0 must print
    as 0, never as the page's "Not stated" word; only a null value is absent.
    The receipt prints the stated number exactly (the stepper rounds 6.4 to 6)
    and names its unit — a bare number said nothing about what it counted."""
    drawer = _drawer("en", {"excerpt": None, "metric": {"value": value, "unit": "USD"}})
    assert _drawer_field(drawer, "Value").text() == shown


@needs_node
@pytest.mark.parametrize("metric,shown", [
    ({"value": 3.5, "unit": "x", "measurement_class": "QUALITATIVE"}, "3.5 x"),
    ({"value": 0, "unit": "x", "measurement_class": "QUALITATIVE"}, "0 x"),
    ({"value": 1e21, "unit": "USD"}, "1000000000000000000000 USD"),
    ({"value": -2.5e22, "unit": "USD"}, "-25000000000000000000000 USD"),
    ({"value": 1e-7, "unit": "USD"}, "0.0000001 USD"),
    ({"value": 1.5e-7, "unit": "USD"}, "0.00000015 USD"),
    ({"value": 123456789012.5, "unit": "USD"}, "123456789012.5 USD"),
])
def test_the_receipt_prints_every_stated_number_in_plain_digits(metric, shown) -> None:
    """Round-3c review F1/F2: the receipt printed "No metric on file" for a
    QUALITATIVE-class record that states a number (the T2 composer gives a
    classless observation QUALITATIVE), and String() put very large and very
    small numbers in exponent form. The receipt prints the stated number,
    whatever its class, in plain digits and with none of them rounded."""
    drawer = _drawer("en", {"excerpt": None, "metric": metric})
    assert _drawer_field(drawer, "Value").text() == shown


@needs_node
def test_a_unit_that_is_the_currency_is_not_repeated() -> None:
    """Round 3: unit "USD" with currency "USD" printed "6.40 USD USD"; a unit
    that is not the currency still carries it."""
    period = " (2025-09-30 \u2013 2026-09-24)"
    root = _dom(_run({"routes": _route(VALID_DOC)})["first"])
    metrics = [m.text() for m in root.find("span", "fi-step-metric")]
    assert "6.40 USD" + period in metrics, metrics
    doc = copy.deepcopy(VALID_DOC)
    doc["slices"][0]["rerating"]["operating"]["primary_metric"]["unit"] = "per share"
    root = _dom(_run({"routes": _route(doc)})["first"])
    metrics = [m.text() for m in root.find("span", "fi-step-metric")]
    assert "6.40 per share USD" + period in metrics, metrics


@needs_node
@pytest.mark.parametrize("lang,ids,words", [
    ("en", ["B.1"], "1 reference basket"),
    ("en", ["B.1", "B.2"], "2 reference baskets"),
    ("zh", ["B.1"], "1 个参考篮子"),
])
def test_the_atlas_counts_reference_baskets_in_words(lang, ids, words) -> None:
    """Round 3: the count is muted metadata (it opens nothing), and one basket
    is singular."""
    doc = copy.deepcopy(VALID_DOC)
    doc["slices"][0]["basket_state"]["incumbent_basket_ids"] = ids
    root = _dom(_run({"lang": lang, "routes": _route(doc)})["first"])
    counts = root.one("section", id="subtheme-atlas").find("span", "fi-slice-baskets")
    assert [c.text() for c in counts] == [words]
    assert not [c for c in counts if c.tag == "button" or "role" in c.attrs]


@needs_node
def test_system_views_paint_no_empty_svg_until_t12_draws_the_graph() -> None:
    """Round 3: an <svg> holding only <title> painted an empty 280px panel.
    Until T12 draws nodes into it, each view is its node and edge lists."""
    system = _dom(_run({"routes": _route(_two_view_doc())})["first"]).one("section", id="system-map")
    assert not [el for el in system.walk() if el.tag in ("svg", "title")]
    panels = system.find("div", "fi-view-panel")
    assert len(panels) == 2
    for panel in panels:
        assert panel.find("ul", "fi-slice-list") and panel.find("ol", "fi-system-edge-list")


@needs_node
def test_held_rights_hide_the_excerpt_but_keep_locator_and_limitations() -> None:
    """Spec §A.8: publisher, family, locator and the five limitations show at
    every rights state; only the value, excerpt and digest hide."""
    drawer = _drawer("en", {"rights_state": "SOURCE_RIGHTS_HELD"})
    assert "Net interest income up 6.4% YoY." not in drawer.text()
    assert "Value" not in [dt.text() for dt in drawer.find("dt")]
    assert _drawer_field(drawer, "Locator").text() == "Item 7, net interest income table"
    assert len(_limitation_items(drawer)) == 5
    assert not drawer.one(data_fi_mount="evidence-private-notice").hidden


# ──────────────────────────────────────────────────────────────────────────
# Contract conformance — a document the T1 contract ACCEPTS, not VALID_DOC.
# ──────────────────────────────────────────────────────────────────────────

_LEAK = re.compile(r"\[object \w+\]|\bundefined\b|\bNaN\b|\bnull\b|Invalid Date")


@needs_node
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_a_contract_valid_read_model_paints_without_leaking_machine_values(lang) -> None:
    """VALID_DOC is partial, so it never showed a painter reading a field of the
    wrong shape: the drawer printed `correction`, a required object, as
    "[object Object]". This paints what the real T2 composer emits from the
    projection suite's synthetic inputs, once the contract validator accepts it,
    with the drawer open on its first record."""
    from engine.sector_intelligence.contracts import validate_contract
    from engine.sector_intelligence.finance_projection import compose_finance_projection
    from tests.test_finance_intelligence_projection import (
        _default_8slice_inputs, _knowledge_cutoff, _today,
    )

    doc = compose_finance_projection(_default_8slice_inputs(), generated_at=_today(),
                                     knowledge_cutoff=_knowledge_cutoff())
    validate_contract(CONTRACT, doc)
    record = doc["source_records"][0]
    snap = _run({"lang": lang, "routes": _route(doc), "hash": "#evidence=" + record["record_id"]})["first"]
    assert snap["noticeEn"] == "" and snap["noticeZh"] == ""
    root = _dom(snap)
    drawer = root.one("aside", id="evidence-drawer")
    assert not drawer.hidden
    assert not _LEAK.findall(root.text()), _LEAK.findall(root.text())
    assert _drawer_field(drawer, "修正" if lang == "zh" else "Correction").text() == (
        "无修正记录" if lang == "zh" else "No correction on file")


@needs_node
@pytest.mark.parametrize("lang,correction,words,english", [
    ("en", {"predecessor_record_id": None, "reason": None}, "No correction on file", []),
    ("zh", {"predecessor_record_id": None, "reason": None}, "无修正记录", []),
    ("en", {"predecessor_record_id": "src.prev", "reason": "Restated after audit."},
     "Replaces record src.prev — Restated after audit.", ["Restated after audit."]),
    ("zh", {"predecessor_record_id": "src.prev", "reason": None}, "取代记录 src.prev", []),
    ("zh", {"predecessor_record_id": None, "reason": "Restated after audit."},
     "Restated after audit.", ["Restated after audit."]),
])
def test_a_correction_is_read_as_words_never_as_the_raw_object(lang, correction, words, english) -> None:
    """Schema: `correction` is {predecessor_record_id, reason}, both nullable.
    Only the reason is payload prose, so only it is marked English."""
    dd = _drawer_field(_drawer(lang, {"correction": correction}), "修正" if lang == "zh" else "Correction")
    assert dd.text() == words
    assert [el.text() for el in dd.walk() if el.attrs.get("lang") == "en"] == english


@needs_node
def test_methodology_reads_how_the_value_was_obtained_not_the_statement_mode() -> None:
    """Methodology printed the statement mode, the same words as the Statement
    mode row; it reads metric.reported_derived_estimated."""
    drawer = _drawer("en", {"metric": {"value": 6.4, "unit": "USD", "reported_derived_estimated": "DERIVED"},
                            "statement_mode": "FORWARD_TARGET"})
    assert _drawer_field(drawer, "Methodology").text() == "derived"
    assert _drawer_field(drawer, "Statement mode").text() == "Forward target"


# Every enum path in the T1 schema -> the FI_LABELS map that words it, or None
# with the reason it is never painted as a word. A new enum path is red here
# until someone decides which.
_ENUM_WORDS = {
    "outer_dossier_ref/state": "outer_dossier_state",
    "coverage/first_vertical/state": "first_vertical_state",
    "material_changes/freshness_state": "freshness",
    "macro_matrix/driver": "driver",
    "macro_matrix/lag": "lag",
    "macro_matrix/state": "macro_state",
    "constraints/constraint": "constraint",
    "conflicts/label": "conflict_label",
    "conflicts/left/plane": "plane_word",
    "conflicts/right/plane": "plane_word",
    "freshness/state": "freshness",
    "input_receipts/owner": "receipt_owner",
    "input_receipts/state": "receipt_state",
    "degraded_sections/section": None,  # selects the section element; never printed
    "degraded_sections/state": "degraded_section_state",
    "$defs/domain_id": None,  # ids; the words are domains[].name_en/name_zh
    "$defs/slice_id": None,  # ids; the words are slices[].name_en/name_zh
    "$defs/view_id": None,  # ids; the words are system_views[].name_en/name_zh
    "$defs/freshness_state": "freshness",
    "$defs/clock/published_at_grain": "published_at_grain",
    "$defs/metric/measurement_class": "measurement_class",
    "$defs/metric/gross_net_basis": "gross_net_basis",
    "$defs/metric/average_end": None,  # not painted
    "$defs/metric/reported_derived_estimated": "reported_derived_estimated",
    "$defs/plane_state": "plane_state",
    "$defs/plane/state": "plane_state",
    "$defs/plane/comparability_state": "comparability_state",
    "$defs/expectations_plane/state": "plane_state",
    "$defs/expectations_plane/comparability_state": "comparability_state",
    "$defs/expectations_plane/history/state": "history_state",
    "$defs/basket_state/posture": "posture",
    "$defs/basket_state/incumbent_basket_ids": None,  # counted, never named
    "$defs/basket_state/membership_state": "membership",
    "$defs/basket_state/weighting_family": "weighting_family",
    "$defs/basket_state/price_basis_state": "price_basis_state",
    "$defs/indicator/direction": "indicator_direction",
    "$defs/indicator/state": "indicator_state",
    "$defs/valuation_anchor/primary_per_share_anchor": "per_share_anchor",
    "$defs/valuation_anchor/primary_valuation_anchor": "valuation_multiple",
    "$defs/valuation_anchor/horizon": "horizon",
    "$defs/valuation_anchor/state": "valuation_anchor_state",
    "$defs/falsifier/state": "falsifier_state",
    "$defs/slice/slice_state": "slice_state",
    "$defs/source/published_at_grain": "published_at_grain",
    "$defs/source_record/observation/reported_derived_estimated": "reported_derived_estimated",
    "$defs/source_record/identity_state": "identity_state",
    "$defs/source_record/rights_state": "rights_state",
    "$defs/source_record/statement_mode": "statement_mode",
    "$defs/exposure/basis": "basis",
    "$defs/exposure/state": "exposure_state",
    "$defs/exposure_cell/role": "role",
    "$defs/exposure_cell/materiality": "materiality",
    "$defs/company_exposure/identity/state": "identity_state",
    "$defs/company_exposure/company_route/state": "company_route_state",
    "$defs/system_view/edges/evidence_state": "evidence_state",
    "$defs/system_view/edges/relationship": "edge_relationship",
    # Const-only fields (round-3c review F4): fixed values the page checks or
    # selects by, and never prints.
    "contract_id": None,  # checked on load; never printed
    "outer_dossier_ref/contract_id": None,  # the outer dossier's id; never printed
    "sector_ref": None,  # an id; never printed
    "coverage/first_vertical/name": None,  # not painted; the slice names are the words
    "conflicts/resolution": None,  # UNRESOLVED_BY_DESIGN on every conflict; both sides are shown, no resolution is
    "$defs/system_view/view_id": None,  # ids; the words are system_views[].name_en/name_zh
}


def _schema_enums() -> dict:
    schema = json.loads((ROOT / "contracts/sector_intelligence"
                         / f"{CONTRACT}.schema.json").read_text(encoding="utf-8"))
    found: dict = {}

    def walk(node, path):
        if isinstance(node, dict):
            if path and any(isinstance(v, str) for v in node.get("enum", [])):
                found.setdefault("/".join(path), set()).update(
                    v for v in node["enum"] if isinstance(v, str))
            # A const admits one value exactly as an enum does (round-3c
            # review F4): a const-only field needs a word too.
            if path and isinstance(node.get("const"), str):
                found.setdefault("/".join(path), set()).add(node["const"])
            for key, value in node.items():
                if key == "properties":
                    for name, sub in value.items():
                        walk(sub, path + [name])
                elif key == "$defs":
                    for name, sub in value.items():
                        walk(sub, ["$defs", name])
                elif isinstance(value, (dict, list)):
                    walk(value, path)
        elif isinstance(node, list):
            for item in node:
                walk(item, path)

    walk(schema, [])
    return found


def _fi_labels() -> dict:
    src = (TEMPLATES / "finance_intelligence.js").read_text(encoding="utf-8")
    start = src.index("  var FI_LABELS = {")
    end = src.index("\n  };\n", start)
    literal = src[src.index("{", start):end + len("\n  }")]
    result = subprocess.run(
        ["node", "-e", "let s='';process.stdin.on('data',d=>s+=d).on('end',()=>"
                       "process.stdout.write(JSON.stringify(eval('('+s+')'))))"],
        input=literal, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@needs_node
def test_every_value_the_contract_admits_has_a_page_word_in_both_languages() -> None:
    """Missing and machine states are rendered as words: no value a valid
    document can carry may fall through to a fallback or print its token."""
    enums = _schema_enums()
    assert set(enums) == set(_ENUM_WORDS), sorted(set(enums) ^ set(_ENUM_WORDS))
    labels = _fi_labels()
    gaps = []
    for path, values in enums.items():
        words = _ENUM_WORDS[path]
        if words is None:
            continue
        for value in sorted(values):
            pair = labels.get(words, {}).get(value)
            if not (isinstance(pair, list) and len(pair) == 2 and all(isinstance(w, str) and w.strip() for w in pair)):
                gaps.append(f"{path}={value} ({words})")
    assert not gaps, gaps
    # Positive control: the walk reached the enums the drawer words.
    assert {"REPORTED_FACT", "FORWARD_TARGET"} <= enums["$defs/source_record/statement_mode"]


# Spec §D.8 and the identity-state words, as the page must paint them.
_EXPOSURE_WORDS = {
    "en": {"MEASURED": "Measured",
           "EXPOSURE_NOT_SEPARATELY_DISCLOSED": "Exposure not separately disclosed",
           "DIRECT_DIVERSIFIED": "Direct, diversified", "QUALITATIVE_ONLY": "Qualitative only"},
    "zh": {"MEASURED": "已量化", "EXPOSURE_NOT_SEPARATELY_DISCLOSED": "敞口未单独披露",
           "DIRECT_DIVERSIFIED": "直接，多元化", "QUALITATIVE_ONLY": "仅作定性"},
}
_IDENTITY_WORDS = {
    "en": {"IDENTITY_VALIDATED": "Identity confirmed", "IDENTITY_UNRESOLVED": "Identity unresolved",
           "RESEARCH_HINT_UNVALIDATED": "Research hint, not validated"},
    "zh": {"IDENTITY_VALIDATED": "身份已确认", "IDENTITY_UNRESOLVED": "身份尚未确认",
           "RESEARCH_HINT_UNVALIDATED": "研究线索，尚未确认"},
}


def _exposure_states_doc() -> dict:
    """The T2 composer's document plus three synthetic rows, re-validated by the
    contract: SYNP holds one cell in each of the eight first-vertical slices,
    cycling all four exposure states; SYNQ's identity is unresolved and SYNR's
    is an unvalidated research hint."""
    from engine.sector_intelligence.contracts import validate_contract
    from engine.sector_intelligence.finance_projection import compose_finance_projection
    from tests.test_finance_intelligence_projection import (
        _default_8slice_inputs, _knowledge_cutoff, _today,
    )

    doc = compose_finance_projection(_default_8slice_inputs(), generated_at=_today(),
                                     knowledge_cutoff=_knowledge_cutoff())
    base = next(r for r in doc["company_exposures"] if r["row_id"] == "row-SYN1")
    exposures = {
        "MEASURED": {"basis": "SEGMENT_REVENUE", "numerator": "Synthetic segment revenue",
                     "denominator": "Synthetic total company revenue", "value": 0.5,
                     "unit": "ratio of revenues"},
        "EXPOSURE_NOT_SEPARATELY_DISCLOSED": {"basis": "NOT_SEPARATELY_DISCLOSED", "numerator": None,
                                              "denominator": None, "value": None, "unit": None},
        "DIRECT_DIVERSIFIED": {"basis": "AUC_A", "numerator": "Synthetic assets under custody",
                               "denominator": "Synthetic total client assets", "value": 0.3,
                               "unit": "ratio of assets"},
        "QUALITATIVE_ONLY": {"basis": "QUALITATIVE", "numerator": None, "denominator": None,
                             "value": None, "unit": None},
    }

    def cell(slice_id: str, state: str) -> dict:
        out = copy.deepcopy(base["cells"][0])
        out.update(slice_id=slice_id, evidence_refs=[f"src-{slice_id}-synthetic_research"],
                   exposure=dict(exposures[state], state=state))
        return out

    def row(tag: str, identity: str, cells: list) -> dict:
        out = copy.deepcopy(base)
        out.update(row_id=f"row-{tag}", issuer_label=tag, ticker_hint=tag, cells=cells)
        if identity == "IDENTITY_UNRESOLVED":
            out["identity"] = {"state": identity, "company_node_id": None,
                               "security_ref": None, "listing_note": None}
            out["company_route"] = {"href": None, "state": "IDENTITY_UNRESOLVED"}
        else:
            out["identity"] = dict(out["identity"], state=identity,
                                   company_node_id=f"company:synthetic-{tag.lower()}",
                                   security_ref=f"security:{tag.lower()}")
        return out

    states = list(exposures)
    first_vertical = doc["coverage"]["first_vertical"]["slice_ids"]
    doc["company_exposures"] += [
        row("SYNP", "IDENTITY_VALIDATED",
            [cell(sid, states[i % 4]) for i, sid in enumerate(first_vertical)]),
        row("SYNQ", "IDENTITY_UNRESOLVED", [cell("card_networks", "EXPOSURE_NOT_SEPARATELY_DISCLOSED")]),
        row("SYNR", "RESEARCH_HINT_UNVALIDATED", [cell("market_reference_data", "QUALITATIVE_ONLY")]),
    ]
    doc["coverage"]["companies_with_records"] = len(doc["company_exposures"])
    validate_contract(CONTRACT, doc)
    return doc


@needs_node
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_every_exposure_cell_names_its_exposure_state_in_words(lang) -> None:
    """Spec §B.5/§D.8: each exposure cell carries a chip naming its exposure
    state. The page kept the state only in data-state-exposure, so a cell
    whose exposure is not separately disclosed read like a measured one."""
    section = _dom(_run({"lang": lang, "routes": _route(_exposure_states_doc())})["first"]).one(
        "section", id="company-exposure")
    words = _EXPOSURE_WORDS[lang]
    painted = []
    for td in section.find("td", "fi-cell"):
        state = td.attrs.get("data-state-exposure")
        chips = td.find("span", "fi-exposure-chip")
        if not state:  # an absent slice column: "No role recorded", no state to name
            assert not chips, td.text()
            continue
        assert len(chips) == 1, td.text()
        assert chips[0].attrs.get("data-state-exposure") == state
        assert "fi-chip" in chips[0].classes and chips[0].text() == words[state]
        painted.append(state)
    assert set(painted) == set(words), painted
    card_chips = [chip for li in section.find("li", "fi-exposure-card")
                  for chip in li.find("span", "fi-exposure-chip")]
    assert sorted(chip.attrs["data-state-exposure"] for chip in card_chips) == sorted(painted)
    assert all(chip.text() == words[chip.attrs["data-state-exposure"]] for chip in card_chips)


@needs_node
@pytest.mark.parametrize("lang", ["en", "zh"])
def test_a_phone_card_names_its_identity_state(lang) -> None:
    """At 390 px the card is the only exposure surface. It carried no identity
    chip, so an unresolved identity or an unvalidated research hint read like
    a confirmed company on a phone."""
    section = _dom(_run({"lang": lang, "routes": _route(_exposure_states_doc())})["first"]).one(
        "section", id="company-exposure")
    words = _IDENTITY_WORDS[lang]
    seen = set()
    for li in section.find("li", "fi-exposure-card"):
        identity = li.attrs.get("data-state-identity")
        chip = li.one("span", "fi-identity-chip")
        assert chip.attrs.get("data-identity") == identity and chip.text() == words[identity]
        assert chip.tag == "span" and "fi-evidence-trigger" not in chip.classes
        seen.add(identity)
    assert seen == set(words), seen


@needs_node
def test_a_phone_card_lists_its_table_rows_cells_in_column_order() -> None:
    """The card took the first six cells of any vertical: a company with a cell
    in all eight first-vertical slices lost two on a phone, silently. It now
    lists the row's populated cells in the table's column order; this row
    populates all eight."""
    section = _dom(_run({"routes": _route(_exposure_states_doc())})["first"]).one(
        "section", id="company-exposure")
    heads = [th.text() for th in section.find("th", "fi-col-slice")]
    heads = heads[:len(heads) // 2] if len(heads) > 8 else heads  # the fold repeats <thead>
    tr = section.one("tr", data_row_id="row-SYNP")
    card = section.one("li", "fi-exposure-card", data_row_id="row-SYNP")
    lines = [p.one("strong").text().rstrip(":") for p in card.find("p") if p.find("strong")]
    assert len(tr.find("span", "fi-exposure-chip")) == len(heads) == 8
    assert lines == heads
