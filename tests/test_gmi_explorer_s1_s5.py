"""GMI explorer S1 issuer + S5 data-states page gates (lane gmi-ui-w2b-s1s5-20261022-r2).

Every owned page must render from the live model AND the held variant (the
specimen parity state), carry exactly one h1, no title=/style= attributes, no
<script> inside <main>, no REASON_ codes, and never the word "validated".
S1 shows reviewed dated product evidence and withholds unreviewed links.
S5 is a generic noindex feedback reference, preserving prior state keys.
Internal relationship packages do not authorize publication.
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
              "path_template", "success"]
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


def test_s1_live_shows_reviewed_dated_product_evidence(live):
    model, site = live
    for issuer in model["issuers"]:
        main = _main(site / f"gmi-issuer-{issuer['ticker'].lower()}.html")
        accepted = [link for link in issuer["links"]
                    if link["curation"]["decision"] == "ACCEPT" and link["status"] == "RATIFIED"]
        assert main.count('<article class="gmi-evidence-card">') == len(accepted)
        for link in accepted:
            assert link["proposal_id"] in main
        assert "Current delivery, deal size and revenue exposure are not established" in main


def test_s1_unreviewed_connections_do_not_become_product_evidence(held):
    model, site = held
    for issuer in model["issuers"]:
        main = _main(site / f"gmi-issuer-{issuer['ticker'].lower()}.html")
        assert "No reviewed product evidence" in main
        assert '<article class="gmi-evidence-card">' not in main
        assert "gmi-evidence-receipt" not in main


def test_s1_receipt_is_closed_details(live, held):
    for _, site in (live, held):
        for page in site.glob("gmi-issuer-*.html"):
            main = _main(page)
            tags = re.findall(r'<details[^>]*class="gmi-evidence-receipt"[^>]*>', main)
            assert len(tags) == main.count('<article class="gmi-evidence-card">')
            assert all(not re.search(r'\bopen(?:\s|=|>)', tag) for tag in tags)


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


def test_s1_missing_product_values_are_plain_words(live, tmp_path):
    import copy
    model = copy.deepcopy(live[0])
    link = model["issuers"][0]["links"][0]
    link["scope"].update(product=None, platform=None)
    link["lifecycle"] = None
    render_site(model, tmp_path)
    main = _main(tmp_path / f"gmi-issuer-{model['issuers'][0]['ticker'].lower()}.html")
    assert "Not recorded" in main and "未记录" in main
    assert "Stage not recorded" in main and "阶段未记录" in main
    assert "What remains unknown" in main


# --------------------------------------------------------------- S5 states
def test_s5_hygiene_all_renders(live, held, edges):
    for _, site in (live, held, edges):
        _assert_hygiene(site / "gmi-states.html")


@pytest.mark.parametrize("fixture_name", ["live", "held", "edges"])
def test_s5_reference_covers_preserved_and_new_feedback_states(request, fixture_name):
    _, site = request.getfixturevalue(fixture_name)
    html = (site / "gmi-states.html").read_text(encoding="utf-8")
    keys = re.findall(r'<article data-gmi-state="([a-z_]+)"', html)
    assert len(keys) == len(set(keys)) == len(STATE_KEYS)
    assert set(keys) == set(STATE_KEYS)
    assert "Design reference only" in html
    assert "do not report live incidents" in html


def test_s5_noindex(live, held):
    for _, site in (live, held):
        html = (site / "gmi-states.html").read_text(encoding="utf-8")
        assert '<meta name="robots" content="noindex">' in html


def test_s5_generic_reference_does_not_require_provider_data(live, held, tmp_path):
    for name, (model, _) in (("live", live), ("held", held)):
        site = tmp_path / name
        render_site(dict(model, deck=None, edges=[], edges_state="empty",
                         edge_package=None, party_names={}), site)
        html = (site / "gmi-states.html").read_text(encoding="utf-8")
        assert "A taxonomy path describes research structure" in html
        assert "the filing says:" not in html


def test_s5_provider_examples_are_not_published(edges, tmp_path):
    model, _ = edges
    import copy
    model = copy.deepcopy(model)
    model["deck"] = {"private_example": "PRIVATE-DECK-SENTINEL"}
    render_site(model, tmp_path)
    html = (tmp_path / "gmi-states.html").read_text(encoding="utf-8")
    assert "PRIVATE-DECK-SENTINEL" not in html
    assert "If Apple reduces or stops its purchases" not in html
    assert "the filing says:" not in html


# ------------------------------------------------ S3 envelope receipt (DEC:GMI-RELATIONSHIP-ENVELOPE-CONTRACT)
RECEIPT_EN = ("Proposed — read from filings, not reviewed yet",
              "Display only — never a rank, size or gate input")
RECEIPT_ZH = ("拟议 · 来自披露文件，尚未审核", "仅供展示 — 绝不作为排序、仓位或准入依据")


def _receipts(main: str) -> list[str]:
    """The page-level envelope receipt rows (the gmi-ident row naming the package)."""
    rows = re.findall(r'<div class="gmi-ident">.*?</div>', main, re.S)
    return [r for r in rows if "数据包" in r]


@pytest.mark.parametrize("fixture_name", ["live", "edges"])
def test_s3_internal_package_is_not_a_publication_receipt(request, fixture_name):
    model, site = request.getfixturevalue(fixture_name)
    assert model["edges_state"] == "present" and model["edge_package"]
    main = _main(site / "gmi-relationships.html")
    assert "No relationships cleared for public display" in main
    assert "暂无获准公开展示的关系" in main
    assert _receipts(main) == []
    assert model["edge_package"]["package_id"] not in main


def test_s3_public_page_omits_internal_record_identifiers(live):
    model, site = live
    main = _main(site / "gmi-relationships.html")
    for edge in model["edges"]:
        assert edge["relationship_key"] not in main
    assert "How publication works" in main


def test_s3_rank_authority_does_not_grant_public_display(live, tmp_path):
    model, _ = live
    package = dict(model["edge_package"], authority=dict(model["edge_package"]["authority"], rank=True))
    render_site(dict(model, edge_package=package), tmp_path)
    main = _main(tmp_path / "gmi-relationships.html")
    assert "No relationships cleared for public display" in main
    assert _receipts(main) == []


def test_s3_no_receipt_without_a_package(live, tmp_path):
    model, _ = live
    for name, variant in (("bare", dict(model, edge_package=None)),
                          ("empty", dict(model, edges=[], edges_state="empty",
                                         edge_package=None, party_names={}))):
        site = tmp_path / name
        render_site(variant, site)
        assert _receipts(_main(site / "gmi-relationships.html")) == []


def test_s3_internal_coverage_does_not_imply_public_company_coverage(live, edges):
    for model, site in (live, edges):
        main = _main(site / "gmi-relationships.html")
        assert "not a statement that no relationships exist" in main
        assert "Company names, relationship details and financial figures are withheld here" in main
        for issuer_id in model["party_names"]:
            assert issuer_id not in main
        assert "Filings from " not in main


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
