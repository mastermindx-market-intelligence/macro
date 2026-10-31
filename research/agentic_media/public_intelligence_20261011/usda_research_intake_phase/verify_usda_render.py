"""Exercise the incumbent Research renderer against the retained USDA intake.

Usage: python -B verify_usda_render.py REPOSITORY RETAINED_LOCAL_STORE NEW_OUTPUT
This writes an isolated fixture only. It does not admit or publish a source.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

SOURCE_ID = "usda-2026-10-09-wasde-676"
PDF_SHA = "6cc97c08be7e683b6114ae8e16d49fce2f21dce3ed3f9933b0acbd2d37e6840b"
SIDECAR_SHA = "1a215b20c74538f8532757ce2ee043b5784a3e6573e857a8d51eeca8ffd2c80e"
SLUG = "world-agricultural-supply-and-demand-estimates-october-2026-wasde-676-sde676"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    repo, retained, output = [Path(p).resolve() for p in sys.argv[1:]]
    pdf = retained / "research_vault" / (SOURCE_ID + ".pdf")
    sidecar = Path(__file__).with_name("usda_sidecar.json")
    assert digest(pdf) == PDF_SHA, "retained PDF hash mismatch"
    assert digest(sidecar) == SIDECAR_SHA, "sidecar hash mismatch"
    assert not output.exists(), "existing output must not be overwritten"
    inputs = {str(p): digest(p) for p in retained.rglob("*") if p.is_file()}
    inputs[str(sidecar)] = digest(sidecar)
    output.mkdir(parents=True)
    sys.path.insert(0, str(repo))
    violations = []

    def audit(event, args):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
            violations.append(event)
            raise RuntimeError("network forbidden in render acceptance")
        if event == "open" and not isinstance(args[0], int):
            flags = args[2] or 0
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
                assert Path(args[0]).resolve().is_relative_to(output), "write escaped fixture"
        if event in {"os.remove", "os.mkdir", "os.rmdir"}:
            assert Path(args[0]).resolve().is_relative_to(output), "mutation escaped fixture"

    sys.addaudithook(audit)
    from bs4 import BeautifulSoup
    from jinja2 import FileSystemLoader
    from engine.research_vault.excerpt import derive, EXCERPT_MAX_CHARS
    from scripts import build_research_pages as builder
    from lib import pages

    used = {}
    original_get_source = FileSystemLoader.get_source

    def tracked_get_source(self, env, template):
        result = original_get_source(self, env, template)
        used[str(Path(result[1]).resolve().relative_to(repo))] = digest(result[1])
        return result

    FileSystemLoader.get_source = tracked_get_source
    for name in ("scripts/build_research_pages.py", "lib/pages.py", "lib/config.py",
                 "lib/seo.py", "engine/research_vault/sidecar.py",
                 "engine/research_vault/slugs.py", "engine/research_vault/excerpt.py",
                 "templates/data_base.js"):
        used[name] = digest(repo / name)
    catalog = json.loads((retained / "research_vault/catalog.json").read_text())
    assert len(catalog["items"]) == 1 and catalog["items"][0]["id"] == SOURCE_ID
    with sqlite3.connect(f"file:{retained / 'research_vault/corpus.sqlite'}?mode=ro", uri=True) as db:
        row = db.execute("SELECT published_at,body FROM documents WHERE doc_id=?", (SOURCE_ID,)).fetchone()
    assert row and row[0] == "2026-10-09T16:00:00Z"
    paras = derive(row[1])
    site = output / "site"
    site.mkdir()
    builder.SITE = site
    builder.RESEARCH_DIR = site / "research"
    builder.SITEMAP = site / "sitemap.xml"
    builder.EXCERPTS = output / "excerpts.json"
    pages._site_root = lambda: site
    pages._shim_checked = False
    builder.EXCERPTS.write_text(json.dumps({"excerpts": {SOURCE_ID: paras}}))
    keep_url = "https://www.mastermind-x.com/stocks/CVS.html"
    builder.SITEMAP.write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>' + keep_url + '</loc></url></urlset>')
    count = builder.build(catalog)
    page_path = site / "research" / (SLUG + ".html")
    html = page_path.read_text()
    soup = BeautifulSoup(html, "html.parser")
    structured = json.loads(soup.select_one('script[type="application/ld+json"]').string)
    checks = []

    def passed(name, condition):
        assert condition, name
        checks.append({"check": name, "passed": True})

    canonical = "https://www.mastermind-x.com/research/" + SLUG + ".html"
    passed("one_report_rendered", count == 1)
    passed("canonical_slug_and_link", soup.select_one('link[rel="canonical"]')["href"] == canonical)
    passed("actual_report_date_not_freshened", structured["datePublished"] == "2026-10-09T16:00:00Z" and "Oct 9, 2026" in soup.get_text())
    passed("original_agency_attribution", structured["author"]["name"] == "U.S. Department of Agriculture")
    passed("report_title_retained", "WASDE 676" in soup.h1.get_text())
    passed("no_invented_issuer", "about" not in structured and not soup.select(".rr-tks, .rr-tk"))
    passed("bounded_original_excerpt", bool(paras) and sum(map(len, paras)) <= EXCERPT_MAX_CHARS + 1)
    passed("excerpt_exactly_from_existing_derivation", [p.get_text() for p in soup.select(".rr-x-body > p")] == paras)
    passed("excerpt_outside_paywall", soup.select_one(".rr-x").find_parent(class_="rr-gate") is None)
    passed("paywall_metadata_matches_gate", structured["isAccessibleForFree"] is False and structured["hasPart"]["cssSelector"] == ".rr-gate" and len(soup.select(".rr-gate")) == 1)
    passed("existing_report_acquisition_route", soup.select_one(".rr-cta")["href"] == "../research_vault.html?doc=" + SOURCE_ID)
    passed("no_direct_pdf_or_private_store_link", not any(".pdf" in a.get("href", "").lower() or "research_inbox/" in a.get("href", "") for a in soup.select("a")))
    passed("full_summary_not_exposed_as_points", not soup.select(".rr-gate li") and "6 key points" in soup.select_one(".rr-gate").get_text())
    teaser = soup.select_one(".rr-teaser").get_text()
    passed("projection_qualifier_and_marketing_year_retained", catalog["items"][0]["summary_points"][0] in teaser
           and "USDA projects" in teaser and "2026/27" in teaser)
    hub = BeautifulSoup((site / "research/index.html").read_text(), "html.parser")
    passed("crawl_hub_links_report", bool(hub.select('a[href="' + SLUG + '.html"]')))
    sitemap = builder.SITEMAP.read_text()
    passed("sitemap_keeps_existing_stock_and_true_date", keep_url in sitemap and canonical in sitemap and "2026-10-09" in sitemap)
    shim = soup.select_one("script[data-dbase]")
    passed("inline_shim_and_isolated_asset_present", shim is not None and bool(shim.string)
           and not shim.has_attr("src") and (site / "data_base.js").is_file()
           and html.index('<script data-dbase>') > html.index('<meta charset="utf-8"'))
    passed("network_unused", not violations)
    passed("source_and_retained_inputs_unchanged", inputs == {p: digest(p) for p in inputs})
    passed("render_dependencies_unchanged", used == {p: digest(repo / p) for p in used})
    result = {"observed_at": datetime.now(timezone.utc).isoformat(), "source_id": SOURCE_ID,
              "source_pdf_sha256": PDF_SHA, "sidecar_sha256": SIDECAR_SHA,
              "checks": checks, "render_dependencies": used,
              "html_sha256": digest(page_path), "canonical_path": canonical,
              "input_hashes": inputs, "output": str(output),
              "production_writes": 0, "provider_calls": 0, "press_staging_writes": 0,
              "canonical_source_admission": False, "public_page_verified": False,
              "publication": False, "cutover": False, "d14_credit": "0/10"}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": len(checks), "result": str(output / "result.json")}))


if __name__ == "__main__":
    main()
