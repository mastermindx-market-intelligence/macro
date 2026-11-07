"""GMI explorer S2 — theme map (gmi.html) and index (gmi-index.html).

Lane gmi-ui-w2a-s2-20261022-r3: the ported specimen bodies must render the live
model with one h1 per page, all 371 index rows carrying their card-payload
names, gate-4 mark separation (hatched Core vs dashed Extended), the tree
accordion contract gmi.js consumes, the data-branched side panels, and none of
the banned attributes/strings (title=, style=, <script> in main, REASON_*,
typed coverage literals).
"""
from __future__ import annotations

import copy
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from scripts.build_gmi_explorer import build_live_model, render_site
from scripts.gmi_explorer.variants import held_variant

ROOT = Path(__file__).resolve().parent.parent
S2_PAGES = ("gmi.html", "gmi-index.html")

pytestmark = pytest.mark.needs_full_checkout("data")

#: HTML void elements — opened, never closed, so the parser must pop them itself
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input",
                  "link", "meta", "param", "source", "track", "wbr"})


class _Dom(HTMLParser):
    """Flat element list with a depth stack and per-node text."""

    def __init__(self) -> None:
        super().__init__()
        self.nodes: list[dict] = []
        self.stack: list[dict] = []
        self.in_main = False

    def _node(self, tag, attrs) -> dict:
        return {"tag": tag, "attrs": dict(attrs),
                "classes": set((attrs.get("class") or "").split()),
                "parent": self.stack[-1] if self.stack else None,
                "text": [], "in_main": self.in_main}

    def handle_starttag(self, tag, attrs):
        node = self._node(tag, dict(attrs))
        if tag == "main":
            self.in_main = True
        self.nodes.append(node)
        self.stack.append(node)
        if tag in VOID:
            self.stack.pop()  # void elements never receive an endtag event

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.stack.pop()

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1]["tag"] == tag:
            self.stack.pop()
        if tag == "main":
            self.in_main = False

    def handle_data(self, data):
        for node in self.stack:
            node["text"].append(data)

    def all(self, cls: str) -> list[dict]:
        return [n for n in self.nodes if cls in n["classes"]]

    def subtree(self, node: dict) -> list[dict]:
        out, seen = [], False
        for n in self.nodes:
            if n is node:
                seen = True
                continue
            if seen:
                p = n["parent"]
                while p is not None:
                    if p is node:
                        out.append(n)
                        break
                    p = p["parent"]
        return out

    def text_of(self, node: dict) -> str:
        return "".join("".join(n["text"]) for n in [node] + self.subtree(node))


def _dom(html: str) -> _Dom:
    d = _Dom()
    d.feed(html)
    return d


def _render(model: dict, site_dir: Path) -> dict[str, str]:
    render_site(model, site_dir)
    return {name: (site_dir / name).read_text(encoding="utf-8") for name in S2_PAGES}


@pytest.fixture(scope="module")
def fixture_model() -> dict:
    return build_live_model()


@pytest.fixture(scope="module")
def pages(tmp_path_factory, fixture_model) -> dict:
    out = {"model": fixture_model}
    out["live"] = _render(fixture_model, tmp_path_factory.mktemp("s2_live"))
    out["held"] = _render(held_variant(fixture_model), tmp_path_factory.mktemp("s2_held"))
    bare = copy.deepcopy(fixture_model)
    bare["theme_links"] = []
    for mv in bare["micros"].values():
        mv["admitted"] = 0
        mv["kind"] = "acc" if mv["tier"] == "acceptance" else "disp"
        mv["counts"] = dict(mv["counts"], admitted=0)
    bare["totals"]["admitted_micros"] = 0
    bare["totals"]["held"] = 0
    out["nolink"] = _render(bare, tmp_path_factory.mktemp("s2_nolink"))
    return out


# ---------------------------------------------------------------- Tier 1 / structure
def test_exactly_one_h1_per_page(pages):
    for variant in ("live", "held"):
        for name in S2_PAGES:
            assert pages[variant][name].count("<h1") == 1, (variant, name)


def test_key_legend_on_both_pages(pages):
    for variant in ("live", "held"):
        for name in S2_PAGES:
            assert _dom(pages[variant][name]).all("gmi-key"), (variant, name)


def test_no_title_or_style_attribute(pages):
    for variant in ("live", "held", "nolink"):
        for name in S2_PAGES:
            assert ' title="' not in pages[variant][name], (variant, name)
            assert ' style="' not in pages[variant][name], (variant, name)


def test_no_script_inside_main(pages):
    for variant in ("live", "held"):
        for name in S2_PAGES:
            scripts = [n for n in _dom(pages[variant][name]).nodes
                       if n["tag"] == "script" and n["in_main"]]
            assert scripts == [], (variant, name)


def test_no_reason_codes(pages):
    for variant in ("live", "held"):
        for name in S2_PAGES:
            assert "REASON_" not in pages[variant][name], (variant, name)


def test_no_typed_coverage_literals():
    for name in ("gmi_map.html.j2", "gmi_index.html.j2"):
        text = (ROOT / "templates" / name).read_text(encoding="utf-8")
        assert not re.search(r"\b(371|68|303|1928|1931|1019)\b", text), name


# ---------------------------------------------------------------- index (gate 3 + payloads)
def test_index_row_count_matches_totals_and_payloads(pages):
    model = pages["model"]
    rows = _dom(pages["live"]["gmi-index.html"]).all("gmi-irow-name")
    assert len(rows) == model["totals"]["micros"] == len(model["card_payloads"])


def test_index_rows_carry_every_card_payload(pages):
    model = pages["model"]
    d = _dom(pages["live"]["gmi-index.html"])
    by_id = {n["attrs"]["data-gmi-id"]: n for n in d.all("gmi-irow")
             if n["attrs"].get("data-gmi-id")}
    payloads = {p["id"]: p for p in model["card_payloads"]}
    assert set(by_id) == set(payloads)
    assert len(by_id) == model["totals"]["micros"]
    for mid, p in payloads.items():
        text = d.text_of(by_id[mid])
        assert p["en"] in text, mid
        assert p["zh"] in text, mid


def test_index_marks_separate_core_and_extended(pages):
    """Gate 4: hatched (acc) + solid/ring (held/adm) rows == Core; dashed rows == Extended."""
    for variant in ("live", "held"):
        model_v = pages["model"] if variant == "live" else held_variant(pages["model"])
        d = _dom(pages[variant]["gmi-index.html"])
        counts = {"acc": 0, "disp": 0, "held": 0, "adm": 0}
        for row in d.all("gmi-irow"):
            for n in d.subtree(row):
                if n["tag"] == "span" and "gmi-sm" in n["classes"]:
                    for k in counts:
                        if ("gmi-sm--" + k) in n["classes"]:
                            counts[k] += 1
        core = sum(1 for mv in model_v["micros"].values() if mv["kind"] != "disp")
        ext = sum(1 for mv in model_v["micros"].values() if mv["kind"] == "disp")
        assert counts["acc"] + counts["held"] + counts["adm"] == core, variant
        assert counts["disp"] == ext == model_v["totals"]["extended"], variant


# ---------------------------------------------------------------- tree contract
def test_tree_parents_resolve_to_ids(pages):
    for variant in ("live", "held"):
        d = _dom(pages[variant]["gmi.html"])
        ids = {n["attrs"]["data-gmi-tree-id"] for n in d.nodes
               if n["attrs"].get("data-gmi-tree-id")}
        parents = {n["attrs"]["data-gmi-tree-parent"] for n in d.nodes
                   if n["attrs"].get("data-gmi-tree-parent")}
        assert ids and parents, variant
        assert sorted(parents - ids) == [], (variant, sorted(parents - ids))


def test_tree_rows_carry_search_keys_and_open_state(pages):
    d = _dom(pages["held"]["gmi.html"])
    rows = [n for n in d.nodes if n["attrs"].get("data-gmi-tree-id")
            or n["attrs"].get("data-gmi-tree-parent")]
    assert rows
    assert all(n["attrs"].get("data-gmi-q") for n in rows)
    expanded = [n for n in rows if "aria-expanded" in n["attrs"]]
    assert expanded, "expandable rows must carry aria-expanded"
    for n in expanded:
        assert (n["attrs"]["aria-expanded"] == "true") == ("gmi-trow--open" in n["classes"])


def test_empty_categories_render_empty_bands_and_rows(pages):
    model = pages["model"]
    empties = [c["id"] for c in model["cats"] if not c["micros"]]
    assert empties, "the live model is expected to have empty categories"
    assert len(_dom(pages["live"]["gmi.html"]).all("gmi-cband--empty")) == len(empties)
    assert pages["live"]["gmi.html"].count("No micro-themes mapped yet") == len(empties)
    assert pages["live"]["gmi-index.html"].count("No micro-themes mapped yet") == len(empties)


# ---------------------------------------------------------------- side panels
def test_live_shows_admitted_panel(pages):
    page = pages["live"]["gmi.html"]
    assert "Admitted after review. Counted in coverage." in page
    assert "经审核已纳入，计入覆盖率。" in page


def test_held_variant_shows_held_panel(pages):
    page = pages["held"]["gmi.html"]
    assert "Proposed, not a member. Not counted until reviewed." in page
    assert "拟议关联，尚非成员。审核前不计入统计。" in page


def test_nolink_model_shows_empty_review_panel(pages):
    page = pages["nolink"]["gmi.html"]
    assert "Nothing is waiting for review." in page
    assert "目前没有待审核的关联。" in page


def test_empty_subs_summary_row_names_them(tmp_path, fixture_model):
    """SPECS §8: empty sub-themes collapse into one summary row that names them.

    The live focus theme has no empty subs, so point the focus at one that does
    (theme:semicap_equipment, via one of its direct micros) and re-render.
    """
    from scripts.build_gmi_explorer import render_site

    m = copy.deepcopy(fixture_model)
    m["theme_links"][0]["micro_id"] = "theme:etch_deposition_equipment"
    out = tmp_path / "s2_emptysubs"
    render_site(m, out)
    page = (out / "gmi.html").read_text(encoding="utf-8")
    assert "sub-themes have no micro-themes yet" in page
    assert "Not mapped yet: " in page
    summary = [n for n in _dom(page).nodes
               if "gmi-trow--empty" in n["classes"] and "gmi-trow--l3" in n["classes"]]
    assert summary
