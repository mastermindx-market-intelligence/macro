"""GMI explorer S1 issuer + S5 data-states page gates (lane gmi-ui-w2b-s1s5-20261022-r2).

Every owned page must render from the live model AND the held variant (the
specimen parity state), carry exactly one h1, no title=/style= attributes, no
<script> inside <main>, no REASON_ codes, and never the word "validated".
S1 branches on the link state (admitted vs held); S5 is the ten-card state
enum reference sheet (noindex, keys in specimen order).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_gmi_explorer import build_live_model, render_site  # noqa: E402
from scripts.gmi_explorer.variants import edges_variant, held_variant  # noqa: E402

#: the single §10 state enum, in specimen card order
STATE_KEYS = ["fetch_failed", "stale", "rights_withheld", "purpose_denied",
              "source_paused", "unknown", "loading", "empty", "read_updated",
              "path_template"]
#: SPECS §10 plain words an unset S1 value may print (never 0 / — / blank)
UNSET_WORDS = {"Awaiting review", "Not in the source", "Size withheld",
               "Not set yet", "Not disclosed"}
SET_DATE = re.compile(r"\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}")
MAIN = re.compile(r"<main.*?</main>", re.S)


def _main(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    return MAIN.search(html).group(0)


def _assert_hygiene(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    assert html.count("<h1") == 1, f"{path.name}: exactly one h1"
    assert " title=" not in html, f"{path.name}: no title= attribute"
    assert ' style="' not in _main(path), f"{path.name}: no inline style in main"
    assert "<script" not in _main(path), f"{path.name}: no <script> in main"
    assert "REASON_" not in html, f"{path.name}: no reason codes"
    assert "validated" not in html.lower(), f"{path.name}: never 'validated'"


def _unknown_values(main: str) -> list[str]:
    """Trailing values of the side sheet's 'what we don't know yet' list."""
    aside = re.search(r'<aside class="gmi-sheet">.*?</aside>', main, re.S).group(0)
    ul = re.search(r'<ul class="gmi-list">(.*?)</ul>', aside, re.S).group(1)
    out = []
    for row in re.findall(r"<li>(.*?)</li>", ul, re.S):
        spans = re.findall(r"<span>(.*?)</span>", row, re.S)
        out.append(re.sub(r"<[^>]+>", "", spans[-1]).strip())
    return out


@pytest.fixture(scope="module")
def live(tmp_path_factory) -> tuple[dict, Path]:
    model = build_live_model()
    site = tmp_path_factory.mktemp("live")
    render_site(model, site)
    return model, site


@pytest.fixture(scope="module")
def held(tmp_path_factory) -> tuple[dict, Path]:
    model = held_variant(build_live_model())
    site = tmp_path_factory.mktemp("held")
    render_site(model, site)
    return model, site


@pytest.fixture(scope="module")
def edges(tmp_path_factory) -> tuple[dict, Path]:
    model = edges_variant(build_live_model())
    site = tmp_path_factory.mktemp("edges")
    render_site(model, site)
    return model, site


# --------------------------------------------------------------- S1 issuer
def test_issuer_page_per_issuer(live):
    model, site = live
    for issuer in model["issuers"]:
        assert (site / f"gmi-issuer-{issuer['ticker'].lower()}.html").exists()


def test_s1_hygiene_live_and_held(live, held):
    for _, site in (live, held):
        for page in site.glob("gmi-issuer-*.html"):
            _assert_hygiene(page)


def test_s1_live_is_admitted_branch(live):
    model, site = live
    for issuer in model["issuers"]:
        main = _main(site / f"gmi-issuer-{issuer['ticker'].lower()}.html")
        assert "Admitted after review." in main
        assert "Awaiting review" not in main  # the "Whether ... belongs here" row is held-only


def test_s1_held_is_held_branch(held):
    model, site = held
    for issuer in model["issuers"]:
        main = _main(site / f"gmi-issuer-{issuer['ticker'].lower()}.html")
        assert "gmi-pip--held" in main
        assert "Awaiting review" in main


def test_s1_receipt_is_closed_details(live, held):
    for _, site in (live, held):
        for page in site.glob("gmi-issuer-*.html"):
            tag = re.search(r'<details[^>]*id="receipt"[^>]*>', page.read_text(encoding="utf-8"))
            assert tag, f"{page.name}: receipt details present"
            assert "open" not in tag.group(0).split("class")[0], "receipt renders closed"


def test_s1_no_excerpt_text_when_not_granted(live, held):
    for model, site in (live, held):
        for issuer in model["issuers"]:
            for link in issuer["links"]:
                page = (site / f"gmi-issuer-{issuer['ticker'].lower()}.html"
                        ).read_text(encoding="utf-8")
                if link["graph_membership_use"] == "NOT_GRANTED":
                    assert "excerpt_text" not in page
                if link["excerpt_text"]:
                    assert link["excerpt_text"] not in page


def test_s1_unset_values_are_plain_words(live, held):
    for _, site in (live, held):
        for page in sorted(site.glob("gmi-issuer-*.html")):
            main = _main(page)
            values = _unknown_values(main)
            assert values, f"{page.name}: unknowns list present"
            for value in values:
                assert value in UNSET_WORDS or SET_DATE.search(value), \
                    f"{page.name}: unset value {value!r} is not a §10 plain word or a set date"


# --------------------------------------------------------------- S5 states
def test_s5_hygiene_all_renders(live, held, edges):
    for _, site in (live, held, edges):
        _assert_hygiene(site / "gmi-states.html")


@pytest.mark.parametrize("fixture_name", ["live", "held", "edges"])
def test_s5_ten_cards_in_specimen_order(request, fixture_name):
    model, site = request.getfixturevalue(fixture_name)
    html = (site / "gmi-states.html").read_text(encoding="utf-8")
    assert len(re.findall(r"<article class=\"gmi-state\"", html)) == 10
    keys = re.findall(r'<span class="gmi-state-k">([a-z_]+)</span>', html)
    assert keys == STATE_KEYS


def test_s5_noindex(live, held):
    for _, site in (live, held):
        html = (site / "gmi-states.html").read_text(encoding="utf-8")
        assert '<meta name="robots" content="noindex">' in html


def test_s5_deck_none_branch(live, held):
    for model, site in (live, held):
        assert model["deck"] is None
        html = (site / "gmi-states.html").read_text(encoding="utf-8")
        assert "Condition as stated in the filing" in html
        assert "the filing says:" not in html  # G-UI-14: lead-in foot omitted without a deck


def test_s5_deck_present_branch(edges):
    model, site = edges
    assert model["deck"] is not None
    html = (site / "gmi-states.html").read_text(encoding="utf-8")
    assert "If Apple reduces or stops its purchases" in html
    assert "the filing says:" in html


# --------------------------------------------------------------- templates
def test_templates_carry_no_typed_coverage_counts():
    for name in ("gmi_issuer.html.j2", "gmi_states.html.j2"):
        src = (ROOT / "templates" / name).read_text(encoding="utf-8")
        assert not re.search(r"\b(371|68|303|1928|1931|1019)\b", src), \
            f"{name}: typed coverage count"
