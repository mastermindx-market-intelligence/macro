"""GMI explorer S3 relationships + S4 coverage pages (lane ORCH-UI-W2C, 2026-10-22).

Renders the REAL model and its specimen variants through ``render_site`` (the
production path) and pins, per page:

- S3 withholds internal records, identities and excerpts until the existing
  model/data owner supplies a verified public projection. Empty, held and
  populated internal variants cannot bypass that publication boundary.
- Page law on every render: one h1, no ``title=``, no script inside ``main``,
  no reason code, never "validated", inline style only data geometry.
- S4: each market keeps the source numerator and denominator bounds. Resolved
  company reasons and unresolved listings retain their own units. Together
  with admitted companies they account for the upper bound. The existing held
  display fixture's missing-company artifact stays explicit.
- Core-theme activity totals exclude extended themes and distinguish admitted
  activity from proposed-only status. Snapshot and model-generation clocks
  retain their source meanings.
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
from bs4 import BeautifulSoup

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
    assert "Public relationship view unavailable" in html
    assert "暂无公开关系视图" in html
    assert "not a statement that no relationships exist" in html
    assert "gmi-spec--on" not in html
    assert "gmi-relgrid" not in html


def test_s3_internal_edges_do_not_enable_public_rendering(pages) -> None:
    html = _main(pages[("edges", S3)])
    assert "Public relationship view unavailable" in html
    assert 'id="excerpt"' not in html
    assert "gmi-relgrid" not in html
    assert "gmi-chain--edges" not in html


def test_s3_live_envelope_is_withheld_without_public_projection(pages) -> None:
    model = pages["models"]["live"]
    assert model["edges_state"] == "present" and model["edges"]
    html = _main(pages[("live", S3)])
    assert "Public relationship view unavailable" in html
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
    assert "Public relationship view unavailable" in html
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
def test_s4_market_counts_keep_source_bounds(pages, variant) -> None:
    model = pages["models"][variant]
    soup = BeautifulSoup(_main(pages[(variant, S4)]), "html.parser")
    assert soup.select_one("#cov-h .l-en").get_text() == "Core-theme company coverage"
    assert not soup.select(".gmi-big0, .gmi-track, .gmi-stack")
    rows = soup.select("[data-gmi-coverage-market]")
    assert [r["data-gmi-coverage-market"] for r in rows] == ["us", "cn"]
    for row in rows:
        mrow = model["coverage"][row["data-gmi-coverage-market"]]
        denominator = mrow["denominator"]
        low, high = denominator["issuer_count_bounds"]
        expected = f"{low:,}" if low == high else f"{low:,}–{high:,}"
        assert row.select_one(".gmi-coverage-bound dt .l-en").get_text() == "Company count range"
        assert row.select_one(".gmi-coverage-bound dt .l-zh").get_text() == "公司数量范围"
        assert row.select_one(".gmi-coverage-bound dd").get_text() == expected
        assert int(row.select_one(".gmi-coverage-admitted strong").get_text().replace(",", "")) == mrow["numerator_issuers"]
        assert int(row.select_one(".gmi-coverage-matched dd").get_text().replace(",", "")) == denominator["eligible_issuers_resolved"]
        unmatched = row.select_one(".gmi-coverage-unmatched dd")
        unresolved = denominator["eligible_securities_unresolved_issuer"]
        assert (unmatched is not None) == (unresolved > 0)
        if unmatched:
            assert int(unmatched.get_text().replace(",", "")) == unresolved


@pytest.mark.parametrize("variant", ["live", "held"])
def test_s4_company_reasons_account_for_separate_listings(pages, variant) -> None:
    model = pages["models"][variant]
    soup = BeautifulSoup(_main(pages[(variant, S4)]), "html.parser")
    for market in ("us", "cn"):
        row = soup.select_one(f'[data-gmi-coverage-market="{market}"]')
        mrow = model["coverage"][market]
        unresolved = mrow["denominator"]["eligible_securities_unresolved_issuer"]
        remainder = mrow["remainder_by_reason"]
        assert set(remainder) <= set(model["reason_words"]), "no source reason may disappear"
        expected = []
        for code, words in model["reason_words"].items():
            if code not in remainder:
                continue
            count = remainder[code] - (unresolved if code == "IDENTITY_NOT_QUALIFIED" else 0)
            assert count >= 0, (market, code, count)
            if count:
                expected.append((words["en"], words["zh"], count))
        rendered = [(part.select_one("dt .l-en").get_text(),
                     part.select_one("dt .l-zh").get_text(),
                     int(part.select_one("dd b").get_text().replace(",", "")))
                    for part in row.select(".gmi-coverage-reason-list > div")]
        assert rendered == expected, (market, rendered, expected)
        assert bool(row.select(".gmi-coverage-reasons")) == bool(expected)
        count = sum(part[2] for part in rendered)
        total = count + unresolved + mrow["numerator_issuers"]
        upper = mrow["denominator"]["issuer_count_bounds"][1]
        artifact = 0
        if variant == "held":
            # Existing held_variant removes the admitted company without
            # returning it to a reason. Do not conceal or repair its data here.
            artifact = (pages["models"]["live"]["coverage"][market]["numerator_issuers"]
                        - mrow["numerator_issuers"])
        assert total + artifact == upper, (variant, market, total, upper, artifact)
        assert count + artifact == (
            mrow["denominator"]["eligible_issuers_resolved"] - mrow["numerator_issuers"])
        for part in row.select(".gmi-coverage-reason-list > div"):
            assert part.select_one("dd .l-en").get_text() in ("company", "companies")
            assert part.select_one("dd .l-zh").get_text() == "家公司"


def test_s4_core_activity_counts_use_one_scope(pages) -> None:
    model = pages["models"]["live"]
    soup = BeautifulSoup(_main(pages[("live", S4)]), "html.parser")
    core = [m for m in model["micros"].values() if m["tier"] == "acceptance"]
    admitted = sum(m["admitted"] > 0 for m in core)
    counts = [int(n.get_text().replace(",", "")) for n in soup.select(".gmi-coverage-theme-totals b")]
    assert counts == [admitted, len(core) - admitted]
    assert all("core theme" in n.get_text() for n in soup.select(".gmi-coverage-theme-totals .l-en"))
    assert all("核心主题" in n.get_text() for n in soup.select(".gmi-coverage-theme-totals .l-zh"))
    assert len(soup.select(".gmi-strip68 > .gmi-sm--adm")) == admitted
    assert len(soup.select(".gmi-strip68 > .gmi-sm--acc")) == len(core) - admitted


def test_s4_clocks_describe_the_saved_model(pages) -> None:
    model = pages["models"]["live"]
    soup = BeautifulSoup(_main(pages[("live", S4)]), "html.parser")
    rows = soup.select(".gmi-coverage-sources .gmi-dl > div")
    assert len(rows) == 3
    assert rows[0].select_one("dt .l-en").get_text() == "Snapshot as of"
    assert rows[0].select_one("dd time")["datetime"] == model["asof"]
    assert rows[1].select_one("dt .l-en").get_text() == "Coverage model generated"
    assert rows[1].select_one("dd time")["datetime"] == model["provenance"]["built_at_utc"]
    assert rows[2].select_one("dt .l-en").get_text() == "Sources"
    assert rows[2].select_one("dd time") is None
    assert "Review records" in rows[2].select_one("dd .l-en").get_text()
    assert "review ledger," not in str(soup)


@pytest.mark.parametrize("matched,unresolved,numerator,identity,vendor", [
    (4, 3, 1, 5, 1),
    (3, 2, 3, 2, 0),
    (3, 0, 3, 0, 0),
    (0, 0, 0, 0, 0),
    (0, 7, 0, 7, 0),
])
def test_s4_population_boundaries(proof_model, tmp_path, matched, unresolved, numerator, identity, vendor) -> None:
    model = copy.deepcopy(proof_model)
    row = model["coverage"]["us"]
    row["numerator_issuers"] = numerator
    row["denominator"] = {
        "eligible_issuers_resolved": matched,
        "eligible_securities_unresolved_issuer": unresolved,
        "issuer_count_bounds": [matched + (1 if unresolved else 0), matched + unresolved],
    }
    row["remainder_by_reason"] = {}
    if identity:
        row["remainder_by_reason"]["IDENTITY_NOT_QUALIFIED"] = identity
    if vendor:
        row["remainder_by_reason"]["VENDOR_MEMBERSHIP_ONLY"] = vendor
    assert identity - unresolved + vendor == matched - numerator
    render_site(model, tmp_path)
    html = (tmp_path / S4).read_text(encoding="utf-8")
    bound = {("live", S4): html, "models": {"live": model}}
    test_s4_market_counts_keep_source_bounds(bound, "live")
    test_s4_company_reasons_account_for_separate_listings(bound, "live")
    main = _main(html)
    assert "100%" not in main and "complete coverage" not in main.lower()


def test_s4_extended_activity_cannot_change_core_summary(proof_model, tmp_path) -> None:
    model = copy.deepcopy(proof_model)
    core = [m for m in model["micros"].values() if m["tier"] == "acceptance"]
    extended = [m for m in model["micros"].values() if m["tier"] != "acceptance"]
    assert len(core) >= 5 and extended
    for micro in core:
        micro.update(admitted=0, disposition="EMPTY", kind="acc")
        micro["counts"] = {"admitted": 0, "proposed": 0, "rejected": 0,
                           "research_records": {}, "vendor_expressing_routes": 0, "vendor_member_companies": 0}
    cases = [("NATIVE_POPULATED", "adm", 2, 1), ("PROPOSED_ONLY", "held", 0, 2),
             ("RESEARCH_UNADMITTED", "acc", 0, 0), ("VENDOR_ONLY", "acc", 0, 0)]
    for micro, (disposition, kind, admitted, proposed) in zip(core, cases):
        micro.update(disposition=disposition, kind=kind, admitted=admitted)
        micro["counts"].update(admitted=admitted, proposed=proposed)
    core[2]["counts"]["research_records"] = {"fixture": 1}
    core[3]["counts"].update(vendor_expressing_routes=1, vendor_member_companies=2)
    extended[0].update(admitted=3, disposition=None, kind="adm")
    extended[0]["counts"]["admitted"] = 3
    model["totals"]["admitted_micros"] = sum(m["admitted"] > 0 for m in model["micros"].values())
    model["totals"]["held"] = sum(m["kind"] == "held" for m in model["micros"].values())
    model["disposition_counts"] = {key: sum(m["disposition"] == key for m in core)
                                   for key in ("NATIVE_POPULATED", "PROPOSED_ONLY", "RESEARCH_UNADMITTED", "VENDOR_ONLY", "EMPTY")}
    before_markets = copy.deepcopy(model["coverage"])
    render_site(model, tmp_path)
    html = (tmp_path / S4).read_text(encoding="utf-8")
    bound = {("live", S4): html, "models": {"live": model}}
    test_s4_core_activity_counts_use_one_scope(bound)
    soup = BeautifulSoup(_main(html), "html.parser")
    assert [n.get_text() for n in soup.select(".gmi-coverage-theme-totals b")] == ["1", str(len(core) - 1)]
    assert "1 has proposals only." in soup.select_one(".gmi-coverage-proposed .l-en").get_text()
    assert model["coverage"] == before_markets
    core[4].update(admitted=1, disposition="NATIVE_POPULATED", kind="adm")
    core[4]["counts"]["admitted"] = 1
    model["totals"]["admitted_micros"] += 1
    model["disposition_counts"]["NATIVE_POPULATED"] += 1
    model["disposition_counts"]["EMPTY"] -= 1
    render_site(model, tmp_path)
    changed = (tmp_path / S4).read_text(encoding="utf-8")
    test_s4_core_activity_counts_use_one_scope({("live", S4): changed, "models": {"live": model}})
    assert model["coverage"] == before_markets


def test_s4_distinct_clock_fixture_survives_rendering(proof_model, tmp_path) -> None:
    model = copy.deepcopy(proof_model)
    model["asof"] = "2024-03-09"
    model["provenance"]["built_at_utc"] = "2025-08-17T06:42:19Z"
    render_site(model, tmp_path)
    first = (tmp_path / S4).read_text(encoding="utf-8")
    test_s4_clocks_describe_the_saved_model({("live", S4): first, "models": {"live": model}})
    render_site(model, tmp_path)
    assert (tmp_path / S4).read_text(encoding="utf-8") == first


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
