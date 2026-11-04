"""Public product rendering checks against a freshly built GMI source model.

These exercise publication boundaries and navigation, not a frozen screenshot's
markup. Model-owner tests remain separate from the product view.
"""
from copy import deepcopy
import json
import re

import pytest
from bs4 import BeautifulSoup

from scripts.build_gmi_explorer import build_live_model, render_site


@pytest.fixture(scope="module")
def current_model():
    return build_live_model()


@pytest.fixture(scope="module")
def pages(current_model, tmp_path_factory):
    out = tmp_path_factory.mktemp("gmi_public_product")
    return {p.name: p.read_text() for p in render_site(current_model, out)}


def test_all_topics_remain_addressable(current_model, pages):
    soup = BeautifulSoup(pages["gmi.html"], "html.parser")
    payload = json.loads(soup.select_one("#gmi-topic-data").string)
    ids = {t["id"] for t in payload["topics"]}
    assert ids == set(current_model["micros"])
    assert len(ids) == len(payload["topics"])
    assert all(t["paths"] for t in payload["topics"])
    index = BeautifulSoup(pages["gmi-index.html"], "html.parser")
    assert len(index.select("a.gmi-irow-name[href*='#theme=']")) == len(ids)


def test_public_pages_do_not_emit_internal_relationships(current_model, pages):
    combined = "\n".join(pages.values())
    for edge in current_model["edges"]:
        assert edge["relationship_key"] not in combined
    payload = json.loads(BeautifulSoup(pages["gmi.html"], "html.parser").select_one("#gmi-topic-data").string)
    assert set(payload) == {"topics", "categories", "asof"}
    assert "No relationships cleared for public display" in pages["gmi-relationships.html"]


def test_restricted_correction_history_cannot_leak(current_model, tmp_path):
    model = deepcopy(current_model)
    secret = "RESTRICTED-CORRECTION-SENTINEL"
    model["edges"][0]["correction_lineage"] = [{"known_at": "2026-11-03T00:00:00Z", "reason": "part_iii_only_amendment", "accession": secret, "amends_accession": secret}]
    rendered = "\n".join(p.read_text() for p in render_site(model, tmp_path))
    assert secret not in rendered


def test_rejected_product_is_not_presented_as_evidence(current_model, tmp_path):
    model = deepcopy(current_model)
    secret = "REJECTED-PRODUCT-SENTINEL"
    model["issuers"][0]["links"][0]["curation"]["decision"] = "REJECT"
    model["issuers"][0]["links"][0]["scope"]["product"] = secret
    rendered = "\n".join(p.read_text() for p in render_site(model, tmp_path))
    assert secret not in rendered


def test_dates_and_stage_are_together_and_no_stale_graph_permission(pages):
    soup = BeautifulSoup(pages["gmi.html"], "html.parser")
    card = soup.select_one(".gmi-evidence-card")
    assert card
    top = card.select_one(".gmi-evidence-date").get_text(" ", strip=True)
    assert "26 Feb 2024" in top and "Planned" in top
    assert "graph_membership_use" not in pages["gmi-issuer-mu.html"]
    assert "NOT_GRANTED" not in pages["gmi-issuer-mu.html"]


def test_company_route_and_shared_shell_remain_integrated(pages):
    assert "gmi-companies.html" in pages
    for name, html in pages.items():
        soup = BeautifulSoup(html, "html.parser")
        assert len(soup.select("h1")) == 1, name
        assert soup.select_one(".gmi-product-nav a[href='gmi-companies.html']"), name
        assert soup.select_one("script[src='theme.js']"), name
        assert soup.select_one("link[href='theme.css']"), name
        assert soup.select_one(".gmi-skip[href='#main']"), name
    company = BeautifulSoup(pages["gmi-companies.html"], "html.parser")
    assert company.select_one("link[rel='canonical']")["href"].endswith("gmi-companies.html")


def test_payload_escapes_source_text(current_model):
    from scripts import build_gmi_explorer as product_builder
    from scripts.gmi_explorer.present import make_env

    # Qualify template escaping after projection. A changed raw issuer name
    # cannot authorize a production fact; that is tested separately below.
    model = product_builder._public_render_model(current_model)
    model["issuers"][0]["display_name"] = "</script><img src=x onerror=alert(1)>"
    html = make_env(model, product_builder.ROOT / "templates").get_template(
        "gmi_map.html.j2").render(model=model, nav_prefix="", page_key="map")
    soup = BeautifulSoup(html, "html.parser")
    assert not soup.select("img[onerror]")
    payload = json.loads(soup.select_one("#gmi-topic-data").string)
    assert any("</script>" in (c["company"] or "") for t in payload["topics"] for c in t["connections"])


def test_company_catalogue_keeps_dated_evidence(current_model, pages):
    soup = BeautifulSoup(pages["gmi-companies.html"], "html.parser")
    issuer = next(row for row in current_model["issuers"] if row["ticker"] == "MU")
    cleared = next(link for link in issuer["links"]
                   if link["proposal_id"] == "actprop:287edbf7e04b8aba873b7493")
    records = soup.select(".gmi-company-record")
    # Raw ACCEPT/RATIFIED membership is not the public-fact boundary.
    assert len(records) == 1
    assert soup.select_one("[data-company-count]").get_text(strip=True)
    assert soup.select_one("[data-company-guide]")
    for record, link in zip(records, [cleared]):
        assert link["scope"]["product"] in record.get_text(" ", strip=True)
        assert record.select_one(".gmi-evidence-date .gmi-stage")
        source = record.select_one(".gmi-source-link a")
        assert source["href"] == link["source"]["url_if_public"]
        assert set(source["rel"]) >= {"noopener", "noreferrer"}


def test_company_catalogue_preserves_all_links_and_rejects_unsafe_source(current_model, tmp_path, monkeypatch):
    model = deepcopy(current_model)
    extra = deepcopy(model["issuers"][0]["links"][0])
    extra["scope"]["product"] = "TEST-ONLY-SECOND-PRODUCT"
    extra["source"]["url_if_public"] = "javascript:alert(1)"
    model["issuers"][0]["links"].append(extra)
    # Isolate downstream multi-record rendering from the separately owned grant.
    # This synthetic test-only qualification is NOT a production publication grant.
    from scripts import build_gmi_explorer as product_builder
    monkeypatch.setattr(product_builder, "_current_public_product",
                        lambda issuer, lk: lk["curation"]["decision"] == "ACCEPT" and lk["status"] == "RATIFIED")
    html = next(p for p in render_site(model, tmp_path) if p.name == "gmi-companies.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.select(".gmi-company-record")) == 2
    assert "TEST-ONLY-SECOND-PRODUCT" in soup.get_text()
    assert not soup.select(".gmi-company-record a[href^='javascript:']")
    assert "Public source link unavailable" in soup.select(".gmi-company-record")[1].get_text()


def test_company_catalogue_empty_state_is_server_rendered(current_model, tmp_path):
    model = deepcopy(current_model)
    for issuer in model["issuers"]:
        for link in issuer["links"]:
            link["curation"]["decision"] = "REJECT"
    html = next(p for p in render_site(model, tmp_path) if p.name == "gmi-companies.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    assert not soup.select("[data-company-card]")
    assert not soup.select_one("[data-company-empty]").has_attr("hidden")
    assert "No company evidence yet" in soup.select_one("[data-company-empty]").get_text()
    assert soup.select_one("[data-company-count]").get_text(strip=True)


def test_unqualified_future_company_does_not_enter_public_files(current_model, tmp_path):
    """ACCEPT/RATIFIED alone cannot serialize another issuer or product."""
    model = deepcopy(current_model)
    other = deepcopy(model["issuers"][0])
    other["node_id"] = "co:us:ZZ"
    other["ticker"] = "ZZ"
    other["display_name"] = "PRIVATE-UNQUALIFIED-COMPANY-SENTINEL"
    other["links"][0]["scope"]["product"] = "PRIVATE-UNQUALIFIED-PRODUCT-SENTINEL"
    model["issuers"].append(other)
    pages = {p.name: p.read_text() for p in render_site(model, tmp_path)}
    assert "gmi-issuer-zz.html" not in pages
    rendered = "\n".join(pages.values())
    assert "PRIVATE-UNQUALIFIED-COMPANY-SENTINEL" not in rendered
    assert "PRIVATE-UNQUALIFIED-PRODUCT-SENTINEL" not in rendered
    assert "gmi-issuer-mu.html" in pages


def test_unqualified_future_link_is_withheld_even_with_accepted_review(current_model, tmp_path):
    model = deepcopy(current_model)
    extra = deepcopy(model["issuers"][0]["links"][0])
    extra["proposal_id"] = "uncleared:future-proposal"
    extra["scope"]["product"] = "PRIVATE-UNQUALIFIED-LINK-SENTINEL"
    model["issuers"][0]["links"].append(extra)
    pages = {p.name: p.read_text() for p in render_site(model, tmp_path)}
    assert "PRIVATE-UNQUALIFIED-LINK-SENTINEL" not in "\n".join(pages.values())
    company = BeautifulSoup(pages["gmi-companies.html"], "html.parser")
    assert len(company.select(".gmi-company-record")) == 1


@pytest.mark.parametrize("field,value", [
    ("proposal_id", "uncleared:future-proposal"),
    ("scope.product", "PRIVATE-UNCLEARED-FACT-SENTINEL"),
    ("source.text_sha256", "0" * 64),
    ("emission_state", "DENIED"),
])
def test_current_fact_changes_fail_closed_and_remove_stale_issuer(current_model, tmp_path, field, value):
    """A source identity/rights change must retire the old generated issuer page."""
    assert (tmp_path / "gmi-issuer-mu.html") in render_site(current_model, tmp_path)
    model = deepcopy(current_model)
    target = model["issuers"][0]["links"][0]
    parts = field.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value
    pages = {p.name: p.read_text() for p in render_site(model, tmp_path)}
    assert "gmi-issuer-mu.html" not in pages
    assert not (tmp_path / "gmi-issuer-mu.html").exists()
    combined = "\n".join(pages.values())
    assert "24GB 8H HBM3E" not in combined
    assert "PRIVATE-UNCLEARED-FACT-SENTINEL" not in combined
    assert not BeautifulSoup(pages["gmi-companies.html"], "html.parser").select("[data-company-card]")


@pytest.mark.parametrize("name", ["gmi-issuer-zz.html", "gmi-issuer-mu.html"])
def test_issuer_output_refuses_symlink(current_model, tmp_path, name):
    """No generated-page pruning may follow a symlink into unrelated output."""
    target = tmp_path / "unrelated-original.html"
    target.write_text("SENTINEL-UNTOUCHED")
    (tmp_path / name).symlink_to(target)
    with pytest.raises(RuntimeError, match="nonregular GMI issuer output"):
        render_site(current_model, tmp_path)
    assert target.read_text() == "SENTINEL-UNTOUCHED"


def test_public_template_model_is_strictly_allowlisted(current_model):
    """Jinja cannot read private payloads through an unused model field."""
    from scripts.build_gmi_explorer import _public_render_model
    model = deepcopy(current_model)
    model["deck"] = {"secret": "PRIVATE-DECK-SENTINEL"}
    model["edges"] = [{"secret": "PRIVATE-EDGE-SENTINEL"}]
    model["party_names"] = {"secret": "PRIVATE-PARTY-SENTINEL"}
    model["theme_links"].append({"ticker": "SECRET-TICKER-SENTINEL",
                                  "micro_id": "theme:hbm_packaging"})
    public = _public_render_model(model)
    assert set(public) == {
        "cats", "micros", "totals", "disposition_counts", "coverage",
        "reason_words", "extended_on", "asof", "provenance",
        "issuers", "theme_links",
    }
    assert set(public["provenance"]) == {"built_at_utc"}
    assert "SECRET-TICKER-SENTINEL" not in json.dumps(public["theme_links"])
    assert len(public["issuers"]) == 1
    assert set(public["issuers"][0]) == {
        "ticker", "exchange", "display_name", "links",
    }
    assert set(public["issuers"][0]["links"][0]) == {
        "proposal_id", "status", "micro_id", "micro_en", "micro_zh",
        "lifecycle", "curation", "scope", "source",
    }
    assert set(public["issuers"][0]["links"][0]["scope"]) == {"product", "platform"}
    for forbidden in ("PRIVATE-DECK-SENTINEL", "PRIVATE-EDGE-SENTINEL",
                      "PRIVATE-PARTY-SENTINEL", "SECRET-TICKER-SENTINEL",
                      "graph_membership_use", "correction_lineage", "counterparty_issuer_id"):
        assert forbidden not in json.dumps(public)


@pytest.mark.parametrize("field", [
    "display_name",
    "exchange",
    "links.0.micro_en",
    "links.0.micro_zh",
    "links.0.source.label_en",
    "links.0.source.label_zh",
])
def test_current_fact_attribution_changes_fail_closed(current_model, tmp_path, field):
    """The same receipt cannot publish an altered company, theme or source label."""
    assert (tmp_path / "gmi-issuer-mu.html") in render_site(current_model, tmp_path)
    model = deepcopy(current_model)
    target = model["issuers"][0]
    parts = field.split(".")
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target[part]
    target[parts[-1]] = "ALTERED-PUBLIC-ATTRIBUTION-SENTINEL"
    pages = {p.name: p.read_text() for p in render_site(model, tmp_path)}
    assert len(pages) == 6
    assert "gmi-issuer-mu.html" not in pages
    assert not (tmp_path / "gmi-issuer-mu.html").exists()
    combined = "\n".join(pages.values())
    for withheld in ("ALTERED-PUBLIC-ATTRIBUTION-SENTINEL", "24GB 8H HBM3E",
                     "actprop:287edbf7e04b8aba873b7493", "gmi-issuer-mu.html"):
        assert withheld not in combined
    soup = BeautifulSoup(pages["gmi-companies.html"], "html.parser")
    assert not soup.select(".gmi-company-record")
    assert "No company evidence yet" in soup.select_one("[data-company-empty]").get_text()
    payload = json.loads(BeautifulSoup(pages["gmi.html"], "html.parser")
                         .select_one("#gmi-topic-data").string)
    assert all(not topic["connections"] for topic in payload["topics"])
