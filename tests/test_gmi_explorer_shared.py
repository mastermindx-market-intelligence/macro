"""GMI explorer shared layer — variants, projections, macros, render path, gmi.js contract.

Pins the W1.5 pieces every surface lane builds on: the held/edges variants used for the
specimen states, the exchange/source-label projections, the shared Jinja macros
(tip_adm/tip_held branching, search_box structure), render_site/--model-in, and the
tree/search contract gmi.js consumes (orchestrator rulings G-UI-9/11/12).
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import build_gmi_explorer
from scripts.gmi_explorer import model as model_module
from scripts.gmi_explorer.model import build_model
from scripts.gmi_explorer.present import make_env
from scripts.gmi_explorer.variants import edges_variant, held_variant

ROOT = Path(__file__).resolve().parent.parent
MACROS = ('{% from "_gmi_macros.html.j2" import t, tip, search_box, key, kind_tag, '
          'tip_core, tip_ext, tip_adm, tip_held with context %}')
PAGES = ("gmi.html", "gmi-index.html", "gmi-issuer-mu.html", "gmi-relationships.html",
         "gmi-coverage.html", "gmi-states.html")

pytestmark = pytest.mark.needs_full_checkout("data")


@pytest.fixture(scope="module")
def model(tmp_path_factory) -> dict:
    snapshots = sorted((ROOT / "data" / "symbol_directory" / "snapshots").glob("*.parquet"))
    assert snapshots, "no symbol directory snapshot present"
    out = tmp_path_factory.mktemp("gmi_proof_shared")
    subprocess.run(
        [sys.executable, "-m", "scripts.gmi_coverage_proof",
         "--symbol-directory", str(snapshots[-1].relative_to(ROOT)), "--out", str(out)],
        cwd=ROOT, check=True, env=dict(os.environ, TZ="UTC"))
    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    return build_model(report, None, repo_root=ROOT)


def _render(model: dict, body: str) -> str:
    env = make_env(model, ROOT / "templates")
    return env.from_string(MACROS + body).render(model=model)


# ---------------------------------------------------------------- projections
@pytest.mark.parametrize("issuer_id,expected", [
    ("ISS:US-XNAS-MU", "XNAS"), ("ISS:US-XNYS-IBM", "XNYS"), (None, None), ("", None),
    ("co:us:MU", None), ("ISS:US", None)])
def test_exchange_projection(issuer_id, expected):
    got = model_module._exchange_of(issuer_id)
    if expected is None:
        assert got is None
    else:
        assert got == model_module.EXCHANGE_WORDS.get(expected)


@pytest.mark.parametrize("key", ["sec:0000723125-24-000001", "manual:abc", None, "", "zzz:1"])
def test_source_label_projection(key):
    en, zh = model_module._source_label(key)
    assert en and zh
    prefix = (key or "").split(":", 1)[0]
    assert (en, zh) == model_module.SOURCE_LABELS.get(prefix, model_module.DEFAULT_SOURCE_LABEL)


def test_theme_links_shape(model):
    for link in model["theme_links"]:
        assert link["kind"] in {"held", "adm"}
        assert link["micro_id"] in model["micros"]
        assert link["name"], "display name = resolver name, filing-name fallback (GAP 21)"
        assert model["micros"][link["micro_id"]]["kind"] == link["kind"]


# ---------------------------------------------------------------- variants
def test_held_variant_is_the_specimen_state(model):
    before = copy.deepcopy(model)
    held = held_variant(model)
    assert model == before, "held_variant must not mutate its input"
    assert held["totals"]["admitted_micros"] == 0
    assert held["totals"]["held"] == len({lk["micro_id"] for lk in held["theme_links"]})
    assert all(lk["kind"] == "held" for lk in held["theme_links"])
    for market in ("us", "cn"):
        assert held["coverage"][market]["numerator_issuers"] == 0
    for mid, micro in held["micros"].items():
        assert micro["kind"] != "adm", mid
    cards = {c["id"]: c for c in held["card_payloads"]}
    for lk in held["theme_links"]:
        assert cards[lk["micro_id"]]["kind"] == "held"
    assert sum(held["disposition_counts"].values()) == sum(model["disposition_counts"].values())


def test_edges_variant_present(model):
    before = copy.deepcopy(model)
    ev = edges_variant(model, ROOT)
    assert model == before
    assert ev["edges_state"] == "present" and len(ev["edges"]) == 1
    assert ev["deck"] is not None and ev["edge_package"] is not None


# ---------------------------------------------------------------- macros
def test_t_falls_back_to_english():
    out = _render({"micros": {}}, '{{ t("Core", "") }}|{{ t("Core", "核心") }}')
    assert out == ('<span class="l-en">Core</span><span class="l-zh">Core</span>|'
                   '<span class="l-en">Core</span><span class="l-zh">核心</span>')


def test_search_box_structure(model):
    out = _render(model, '{{ search_box("Search 9 things", "搜索 9 项", "tree") }}')
    assert 'class="gmi-search" role="search"' in out
    assert re.search(r'<input class="gmi-search-in" type="search" data-gmi-filter="tree"', out)
    for attr in ('data-ph-en="Search 9 things"', 'data-ph-zh="搜索 9 项"',
                 'data-aria-en="Search 9 things"', 'data-aria-zh="搜索 9 项"'):
        assert attr in out
    assert re.search(r'<p class="mx-empty gmi-empty-inline" data-gmi-nomatch="tree" hidden>', out)
    assert " title=" not in out and " style=" not in out


def test_tips_never_use_title_and_carry_both_languages(model):
    out = _render(model, "{{ tip_core() }}{{ tip_ext() }}{{ tip_adm() }}{{ tip_held() }}")
    assert " title=" not in out
    assert out.count("data-tip-en=") == 4 and out.count("data-tip-zh=") == 4
    for words in re.findall(r'data-tip-(?:en|zh)="([^"]*)"', out):
        assert len(words.split()) <= 80


def test_tip_adm_branches_on_admitted_count(model):
    zero = copy.deepcopy(model)
    zero["totals"]["admitted_micros"] = 0
    some = copy.deepcopy(model)
    some["totals"]["admitted_micros"] = 1
    assert "None has been admitted yet." in _render(zero, "{{ tip_adm() }}")
    assert "None has been admitted yet." not in _render(some, "{{ tip_adm() }}")
    assert "目前尚无公司获准纳入。" in _render(zero, "{{ tip_adm() }}")


def test_tip_held_receipt_only_for_a_held_link(model):
    held = held_variant(model)
    if not held["theme_links"]:
        pytest.skip("no theme link in the live model")
    with_link = _render(held, "{{ tip_held() }}")
    assert "data-tip-rc-en=" in with_link and "data-tip-rc-zh=" in with_link
    none = copy.deepcopy(held)
    none["theme_links"] = []
    assert "data-tip-rc-en=" not in _render(none, "{{ tip_held() }}")


def test_core_and_extended_tips_read_the_model(model):
    out = _render(model, "{{ tip_core() }}{{ tip_ext() }}")
    assert f"The original {model['totals']['core']} micro-themes." in out
    assert f"{model['totals']['extended']} micro-themes added on" in out


# ---------------------------------------------------------------- render path
def test_render_site_writes_every_page_and_paired_asset(model, tmp_path):
    written = {p.name for p in build_gmi_explorer.render_site(model, tmp_path)}
    for page in PAGES:
        assert page in written, page
    for asset in ("gmi.css", "gmi.js"):
        assert (tmp_path / asset).read_bytes() == (ROOT / "templates" / asset).read_bytes()


def test_model_in_round_trip(model, tmp_path):
    saved = tmp_path / "model.json"
    saved.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    site = tmp_path / "site"
    assert build_gmi_explorer.main(["--model-in", str(saved), "--site-dir", str(site)]) == 0
    direct = tmp_path / "direct"
    build_gmi_explorer.render_site(model, direct)
    for page in PAGES:
        assert (site / page).read_bytes() == (direct / page).read_bytes(), page


def test_templates_type_no_coverage_number():
    for path in sorted((ROOT / "templates").glob("*gmi*.j2")):
        text = path.read_text(encoding="utf-8")
        hits = re.findall(r"\b(?:371|68|303|1928|1931|1019)\b", text)
        assert not hits, f"{path.name} hand-types a coverage number: {hits}"


# ---------------------------------------------------------------- gmi.js contract
def test_gmi_js_tree_and_search_contract():
    js = (ROOT / "templates" / "gmi.js").read_text(encoding="utf-8")
    for hook in ("data-gmi-tree-id", "data-gmi-tree-parent", "data-gmi-q", "input[data-gmi-filter]",
                 "data-gmi-nomatch", "gmi-trow--open", "aria-expanded", "[data-gmi-index]",
                 "open')==='all'"):
        assert hook in js, hook
    assert not re.search(r"setAttribute\(\s*['\"]title['\"]", js), "gmi.js must never write title="
    assert "innerHTML" not in js
