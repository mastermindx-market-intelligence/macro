"""GMI explorer S3 relationships + S4 coverage pages (lane ORCH-UI-W2C, 2026-10-22).

Renders the REAL model and its specimen variants through ``render_site`` (the
production path) and pins, per page:

- S3 empty state (live: no edges): five zero species chips, none on, the
  honest empty band, the link panel in the model's kind with both facts shown
  (admitted AND not permitted — G-UI-10), the coverage empty panel.
- S3 edges state: the relgrid hero and the ``#excerpt`` receipt.
- S3 held-link branch (G-UI-9): ``held_variant(edges_variant(m))`` is the
  specimen's exact state — the panel flips to the held mark and words.
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
    """Rendered S3/S4 for the live model, the held variant and the edges variant."""
    out: dict[tuple[str, str], str] = {}
    sites: dict[str, dict] = {"live": proof_model,
                              "held": held_variant(proof_model),
                              "edges": edges_variant(proof_model)}
    for name, variant in sites.items():
        site = tmp_path_factory.mktemp(f"gmi_site_{name}")
        render_site(variant, site)
        for page in (S3, S4):
            out[(name, page)] = (site / page).read_text(encoding="utf-8")
    out["models"] = sites
    return out


def _main(html: str) -> str:
    return html.split("<main", 1)[1].split("</main>", 1)[0]


# ---------------------------------------------------------------- S3 states
def test_s3_live_empty_state(pages) -> None:
    html = _main(pages[("live", S3)])
    assert html.count("gmi-spec gmi-spec--zero") == 5
    assert "gmi-spec--on" not in html
    assert 'aria-pressed="true"' not in html
    assert "No documented relationships yet" in html
    assert "尚无已记录的关系" in html
    # NOT_GRANTED renders both facts truthfully (G-UI-10): admitted AND not permitted
    assert "Not permitted yet" in html
    assert "暂不允许" in html
    assert "gmi-empty-inline" in html


def test_s3_edges_state(pages) -> None:
    html = _main(pages[("edges", S3)])
    assert '<details class="mx-disc" id="excerpt">' in html
    assert "gmi-relgrid" in html
    assert "gmi-thread" in html
    assert "gmi-chain gmi-chain--edges" in html
    assert "No documented relationships yet" not in html


def test_s3_held_link_branch(proof_model, tmp_path) -> None:
    """G-UI-9: kind held -> the held mark, held words, held tip (the specimen state)."""
    site = tmp_path / "held_edges"
    render_site(held_variant(edges_variant(proof_model)), site)
    html = _main((site / S3).read_text(encoding="utf-8"))
    assert "gmi-sm--held" in html
    assert "gmi-sm--adm" not in html
    assert "Held for review" in html
    assert "A proposed theme link, not a member. Not shown on the map." in html


# ---------------------------------------------------------------- page law
@pytest.mark.parametrize("variant", ["live", "held", "edges"])
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


def test_s4_live_corrections_only_theme_links(pages) -> None:
    """Live (no edges): the corrections log carries exactly the Theme links row."""
    main = _main(pages[("live", S4)])
    log = main.split("Corrections log", 1)[1].split("</section>", 1)[0]
    assert log.count("<dt>") == 1
    assert "Theme links" in log and "主题关联" in log
    assert "Changes are not tracked yet." in log
    assert "Skyworks" not in log


# ---------------------------------------------------------------- templates
def test_templates_carry_no_typed_counts() -> None:
    for name in ("gmi_relationships.html.j2", "gmi_coverage.html.j2"):
        text = (ROOT / "templates" / name).read_text(encoding="utf-8")
        assert not TYPED.search(text), f"{name} types a coverage count"
