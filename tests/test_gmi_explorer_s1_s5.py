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


def test_s5_deck_none_branch(live, held, tmp_path):
    for name, (model, _) in (("live", live), ("held", held)):
        site = tmp_path / name
        # S5's no-deck branch, rendered without edges: the S3 present branch reads
        # its sentences from the deck (as the edges variant's own fixture deck does),
        # and the live model now carries the committed envelope's edges.
        render_site(dict(model, deck=None, edges=[], edges_state="empty",
                         edge_package=None, party_names={}), site)
        html = (site / "gmi-states.html").read_text(encoding="utf-8")
        assert "Condition as stated in the filing" in html
        assert "the filing says:" not in html  # G-UI-14: lead-in foot omitted without a deck


def test_s5_deck_present_branch(edges):
    model, site = edges
    assert model["deck"] is not None
    html = (site / "gmi-states.html").read_text(encoding="utf-8")
    assert "If Apple reduces or stops its purchases" in html
    assert "the filing says:" in html


# ------------------------------------------------ S3 envelope receipt (DEC:GMI-RELATIONSHIP-ENVELOPE-CONTRACT)
RECEIPT_EN = ("Proposed — read from filings, not reviewed yet",
              "Display only — never a rank, size or gate input")
RECEIPT_ZH = ("拟议 · 来自披露文件，尚未审核", "仅供展示 — 绝不作为排序、仓位或准入依据")


def _receipts(main: str) -> list[str]:
    """The page-level envelope receipt rows (the gmi-ident row naming the package)."""
    rows = re.findall(r'<div class="gmi-ident">.*?</div>', main, re.S)
    return [r for r in rows if "数据包" in r]


@pytest.mark.parametrize("fixture_name", ["live", "edges"])
def test_s3_envelope_receipt(request, fixture_name):
    model, site = request.getfixturevalue(fixture_name)
    package = model["edge_package"]
    assert model["edges_state"] == "present" and package is not None
    assert not any(package["authority"].values())
    main = _main(site / "gmi-relationships.html")
    receipts = _receipts(main)
    assert len(receipts) == 1, "exactly one page-level envelope receipt"
    receipt = receipts[0]
    for words in RECEIPT_EN + RECEIPT_ZH:
        assert words in receipt
    assert package["package_id"][:12] in receipt
    counts = package["counts"]
    assert f"{counts['edges']:,} documented" in receipt
    assert f"已记录 {counts['edges']:,} 条" in receipt
    assert f"{counts['non_edges']:,} other mentions checked" in receipt
    assert f"另核对 {counts['non_edges']:,} 处提及" in receipt
    assert "As of " in receipt and "截至 " in receipt
    assert " title=" not in receipt


def test_s3_live_receipt_names_the_committed_package(live):
    model, site = live
    receipt = _receipts(_main(site / "gmi-relationships.html"))[0]
    assert model["edge_package"]["package_id"].startswith("pkg:")
    assert model["edge_package"]["counts"]["edges"] == len(model["edges"])
    assert f"{len(model['edges']):,} documented" in receipt


def test_s3_receipt_drops_the_display_only_claim_if_any_authority_is_true(live, tmp_path):
    model, _ = live
    package = dict(model["edge_package"], authority=dict(model["edge_package"]["authority"], rank=True))
    render_site(dict(model, edge_package=package), tmp_path)
    receipt = _receipts(_main(tmp_path / "gmi-relationships.html"))[0]
    assert RECEIPT_EN[1] not in receipt and RECEIPT_ZH[1] not in receipt


def test_s3_no_receipt_without_a_package(live, tmp_path):
    model, _ = live
    for name, variant in (("bare", dict(model, edge_package=None)),
                          ("empty", dict(model, edges=[], edges_state="empty",
                                         edge_package=None, party_names={}))):
        site = tmp_path / name
        render_site(variant, site)
        assert _receipts(_main(site / "gmi-relationships.html")) == []


def test_s3_coverage_panel_counts_the_searched_companies(live, edges):
    model, site = live
    searched = {c["issuer_id"] for c in model["edge_package"]["coverage"]
                if c["state"] in ("assessed", "no_supported_result")}
    main = _main(site / "gmi-relationships.html")
    assert f"Filings from {len(searched):,} companies have been read so far." in main
    assert f"目前已读取 {len(searched):,} 家公司的披露文件。" in main
    assert "Filings from one company" not in main
    # the one-company fixture package keeps the one-company sentence
    assert "Filings from one company have been read so far." in _main(edges[1] / "gmi-relationships.html")


def test_s3_hero_possessive(live, edges):
    for _, site in (live, edges):
        main = _main(site / "gmi-relationships.html")
        assert not re.search(r"[^s]’ revenue came from", main), "possessive of a name not ending in s"


# --------------------------------------------------------------- templates
def test_templates_carry_no_typed_coverage_counts():
    for name in ("gmi_issuer.html.j2", "gmi_states.html.j2"):
        src = (ROOT / "templates" / name).read_text(encoding="utf-8")
        assert not re.search(r"\b(371|68|303|1928|1931|1019)\b", src), \
            f"{name}: typed coverage count"
