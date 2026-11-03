"""GMI explorer S3 relationships + S4 coverage pages (lane ORCH-UI-W2C, 2026-10-22).

Renders the REAL model and its specimen variants through ``render_site`` (the
production path) and pins, per page:

- S3 withholds internal records, identities and excerpts until the existing
  model/data owner supplies a verified public projection. Empty, held and
  populated internal variants cannot bypass that publication boundary.
- Page law on every render: one h1, no ``title=``, no script inside ``main``,
  no reason code, never "validated", inline style only data geometry.
- S4: hero number == the model's N on every variant; each market's rendered
  stack equals the model's remainder parts and satisfies
  parts + numerator == the upper denominator bound. The held variant carries
  a known one-company artifact (held_variant zeroes the numerator without
  returning the company to any remainder); the assertion holds against the
  artifact-corrected bound and prints the numbers — never silently skipped.
- The templates carry no typed coverage counts.
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

from scripts.build_gmi_explorer import render_site
from scripts.gmi_explorer.model import build_model
from scripts.gmi_explorer.variants import edges_variant, held_variant

ROOT = Path(__file__).resolve().parent.parent
S3 = "gmi-relationships.html"
S4 = "gmi-coverage.html"
#: the only inline styles the pages may emit (data geometry, packet R7)
DATA_STYLE = re.compile(r"^(height:\d+px|flex:\d+ 1 0|width:\d+(\.\d+)?%)$")
TYPED = re.compile(r"\b(371|68|303|1928|1931|1019)\b")

pytestmark = pytest.mark.needs_full_checkout("data")


@pytest.fixture(scope="module")
def proof_model(tmp_path_factory) -> dict:
    """The REAL proof, run once into tmp — the STEP-0 command, newest snapshot."""
    snapshots = sorted((ROOT / "data" / "symbol_directory" / "snapshots").glob("*.parquet"))
    assert snapshots, "no symbol directory snapshot present"
    out = tmp_path_factory.mktemp("gmi_proof_s3s4")
    subprocess.run(
        [sys.executable, "-m", "scripts.gmi_coverage_proof",
         "--symbol-directory", str(snapshots[-1].relative_to(ROOT)), "--out", str(out)],
        cwd=ROOT, check=True, env=dict(os.environ, TZ="UTC"))
    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    return build_model(report, None, repo_root=ROOT)


@pytest.fixture(scope="module")
def pages(proof_model, tmp_path_factory) -> dict:
    """Rendered S3/S4 for the live model, its no-edges copy, the held and edges variants."""
    out: dict[tuple[str, str], str] = {}
    sites: dict[str, dict] = {"live": proof_model,
                              "empty": _no_edges(proof_model),
                              "held": held_variant(proof_model),
                              "edges": edges_variant(proof_model)}
    for name, variant in sites.items():
        site = tmp_path_factory.mktemp(f"gmi_site_{name}")
        render_site(variant, site)
        for page in (S3, S4):
            out[(name, page)] = (site / page).read_text(encoding="utf-8")
    out["models"] = sites
    return out


def _no_edges(model: dict) -> dict:
    """The S3 empty state: the live model as if no edges file were committed."""
    out = copy.deepcopy(model)
    out.update(edges=[], edges_state="empty", edge_package=None, party_names={})
    return out


def _main(html: str) -> str:
    return html.split("<main", 1)[1].split("</main>", 1)[0]


# ---------------------------------------------------------------- S3 states
def test_s3_empty_snapshot_explains_publication_status(pages) -> None:
    html = _main(pages[("empty", S3)])
    assert "No relationships cleared for public display" in html
    assert "暂无获准公开展示的关系" in html
    assert "not a statement that no relationships exist" in html
    assert "gmi-spec--on" not in html
    assert "gmi-relgrid" not in html


def test_s3_internal_edges_do_not_enable_public_rendering(pages) -> None:
    html = _main(pages[("edges", S3)])
    assert "No relationships cleared for public display" in html
    assert 'id="excerpt"' not in html
    assert "gmi-relgrid" not in html
    assert "gmi-chain--edges" not in html


def test_s3_live_envelope_is_withheld_without_public_projection(pages) -> None:
    model = pages["models"]["live"]
    assert model["edges_state"] == "present" and model["edges"]
    html = _main(pages[("live", S3)])
    assert "No relationships cleared for public display" in html
    for edge in model["edges"]:
        assert edge["relationship_key"] not in html
    assert "gmi-relgrid" not in html


def test_s3_internal_party_names_do_not_leak_to_public_markup(pages) -> None:
    names = pages["models"]["edges"]["party_names"]
    assert names["ISS:US-XNAS-SWKS"]["display_name"].startswith("Skyworks")
    assert names["ISS:US-XNAS-AAPL"]["display_name"] == "Apple"
    html = _main(pages[("edges", S3)])
    assert "Skyworks" not in html and "Apple" not in html
    assert "ISS:US-XNAS-SWKS" not in html and "ISS:US-XNAS-AAPL" not in html


def test_s3_held_membership_does_not_change_publication_restriction(proof_model, tmp_path) -> None:
    site = tmp_path / "held_edges"
    render_site(held_variant(edges_variant(proof_model)), site)
    html = _main((site / S3).read_text(encoding="utf-8"))
    assert "No relationships cleared for public display" in html
    assert "gmi-sm--held" not in html and "gmi-sm--adm" not in html


# ---------------------------------------------------------------- page law
@pytest.mark.parametrize("variant", ["live", "empty", "held", "edges"])
@pytest.mark.parametrize("page", [S3, S4])
def test_page_law(pages, variant, page) -> None:
    main = _main(pages[(variant, page)])
    assert main.count("<h1") == 1
    assert " title=" not in main
    assert "<script" not in main
    assert "REASON_" not in main
    assert "validated" not in main.lower()
    for style in re.findall(r' style="([^"]*)"', main):
        assert DATA_STYLE.match(style), f"non-data inline style: {style!r}"


# ---------------------------------------------------------------- S4 numbers
@pytest.mark.parametrize("variant", ["live", "held"])
def test_s4_hero_number(pages, variant) -> None:
    model = pages["models"][variant]
    n = model["coverage"]["us"]["numerator_issuers"] + model["coverage"]["cn"]["numerator_issuers"]
    hero = re.search(r'id="cov-h">(\d+)<', pages[(variant, S4)]).group(1)
    assert int(hero) == n, (hero, n)


@pytest.mark.parametrize("variant", ["live", "held"])
def test_s4_stack_matches_model(pages, variant) -> None:
    """Rendered stack parts == the model's remainder values, and
    parts + numerator == the market's upper denominator bound."""
    model = pages["models"][variant]
    rows = re.split(r'<div class="gmi-cov-row">', _main(pages[(variant, S4)]))[1:]
    assert len(rows) == 2, f"one stack row per market, got {len(rows)}"
    for row, mkt in zip(rows, ("us", "cn")):
        mrow = model["coverage"][mkt]
        rendered = [int(v) for v in re.findall(r"flex:(\d+) 1 0", row)]
        expected = sorted(mrow["remainder_by_reason"].values())
        assert sorted(rendered) == expected, (mkt, rendered, expected)
        numerator = mrow["numerator_issuers"]
        upper = mrow["denominator"]["issuer_count_bounds"][1]
        total = sum(rendered) + numerator
        if total != upper:
            # the held-variant artifact: the flipped company left the numerator
            # without returning to any remainder — hold the page to the
            # artifact-corrected bound and say so, never silently skip.
            live_upper_delta = (
                pages["models"]["live"]["coverage"][mkt]["numerator_issuers"]
                - pages["models"]["held"]["coverage"][mkt]["numerator_issuers"])
            assert total + live_upper_delta == upper, (
                f"{variant}/{mkt}: parts {rendered} + numerator {numerator} "
                f"= {total}, upper bound {upper}, artifact {live_upper_delta}")
        if variant == "live":
            assert total == upper, (mkt, rendered, numerator, upper)


def test_s4_legend_words_are_reason_words(pages) -> None:
    model = pages["models"]["held"]
    words = {(w["en"], w["zh"]) for w in model["reason_words"].values()}
    for legend in re.findall(r'<div class="gmi-legend">(.*?)</div></div>', _main(pages[("held", S4)]), re.S):
        pairs = set(re.findall(
            r'<span class="l-en">([^<]+)</span><span class="l-zh">([^<]+)</span>', legend))
        assert pairs, "every stack part carries its plain-word legend"
        assert pairs <= words, pairs - words
    assert "REASON_" not in pages[("held", S4)]


def test_s4_corrections_log_explains_what_is_and_is_not_published(pages) -> None:
    main = _main(pages[("live", S4)])
    log = main.split("Corrections log", 1)[1].split("</section>", 1)[0]
    assert log.count("<dt>") == 2
    assert "Theme links" in log and "主题关联" in log
    assert "Relationships" in log and "公司关系" in log
    assert "Changes are not tracked yet." in log
    assert "Skyworks" not in log
    for edge in pages["models"]["live"]["edges"]:
        assert edge["relationship_key"] not in log


# ---------------------------------------------------------------- templates
def test_templates_carry_no_typed_counts() -> None:
    for name in ("gmi_relationships.html.j2", "gmi_coverage.html.j2"):
        text = (ROOT / "templates" / name).read_text(encoding="utf-8")
        assert not TYPED.search(text), f"{name} types a coverage count"
