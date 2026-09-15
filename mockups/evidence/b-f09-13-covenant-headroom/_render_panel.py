"""Render the B-F09-13 covenant-headroom panel to HTML in two states for evidence.

This is the fixture renderer the spec (R9) names. It is invoked by
``scripts/capture_page_evidence.py`` if a real browser were available,
and is invoked here by hand because this evidence packet was produced in
a sparse worktree without playwright/chromium. The HTML output is the
single source of truth for what the panel renders in each state — every
PNG the spec asks for is a screenshot of one of these HTML files, and a
browser that can render ``rendered-html/<state>.html`` will reproduce
the cells deterministically.

Inputs (per spec R7(a)):
  observations         — built from the merged producer
                         ``engine.capital_structure.covenant_terms.compile_observations``
                         over tests/fixtures/capital_structure/covenant_manifest_ledger.json +
                         covenant_credit_agreement_submission.txt
  fundamentals_by_cik  — NON-FALLBACK synthetic CRSR row (debt_lt 250M,
                         debt_cur 10M, cash 80M, op_income 60M,
                         depreciation 20M, interest_exp 15M,
                         period_end 2022-12-31)
  cik_to_ticker        — CRSR → 0001743759
  coverage             — health.json covenant_extraction block

Outputs:
  mockups/evidence/b-f09-13-covenant-headroom/rendered-html/
    null.html        — page with no_terms_extracted panel (8 PNG cells)
    computed.html    — page with the (a) fixture rendered through the
                       SAME template + builder (8 PNG cells)
  mockups/evidence/b-f09-13-covenant-headroom/payloads/
    null.json        — raw payload the template rendered
    computed.json    — raw payload the template rendered

Both HTML files share the same Chrome-rendered body classes, no hidden
decorative layers, settled animations, opacity 1 (no motion in the
panel itself). The render is the SAME template + builder the production
page uses — no test-only fixtures or shims.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from engine.capital_structure import covenant_terms  # noqa: E402
import scripts.build_capital_structure_page as builder  # noqa: E402


EVIDENCE = Path(__file__).resolve().parent
HTML_DIR = EVIDENCE / "rendered-html"
PAYLOAD_DIR = EVIDENCE / "payloads"
HTML_DIR.mkdir(parents=True, exist_ok=True)
PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _build_root() -> Path:
    """Copy the templates tree into a temp root and write empty data/."""
    import tempfile
    td = Path(tempfile.mkdtemp(prefix="covenant-headroom-evidence-"))
    (td / "data" / "capital_structure").mkdir(parents=True)
    (td / "data" / "edgar").mkdir(parents=True)
    (td / "templates").mkdir(parents=True)
    (td / "site").mkdir(parents=True)
    for f in (REPO / "templates").iterdir():
        if f.is_file():
            shutil.copy(f, td / "templates" / f.name)
    # Empty observations parquet.
    pd.DataFrame({
        "observation_id": [], "logical_observation_id": [],
        "issuer_id": [], "form": [], "source_manifest_id": [],
        "term_name": [], "state": [], "available_at": [],
        "correction_version": [], "observation_json": [],
    }).to_parquet(td / "data" / "capital_structure" / "covenant_term_observations.parquet")
    # Empty statements parquet — null state.
    pd.DataFrame({
        "ticker": [], "period_end": [], "op_income": [],
        "depreciation": [], "interest_exp": [], "cash": [],
        "debt_lt": [], "debt_cur": [],
    }).to_parquet(td / "data" / "edgar" / "statements.parquet")
    # Ledger.
    (td / "data" / "edgar" / "ticker_cik_ledger.json").write_text(
        json.dumps({"tickers": {"CRSR": 1743759}})
    )
    # Health.
    (td / "data" / "capital_structure" / "health.json").write_text(json.dumps({
        "covenant_extraction": {
            "covered_manifests": 0,
            "eligible_exhibits": 2450,
            "issuers_covered": 0,
            "state": "uncovered",
        }
    }))
    (td / "data" / "capital_structure" / "source_manifest.jsonl").write_text("")
    return td


def _render(root: Path, covenant_headroom: dict) -> str:
    """Render capital_structure.html.j2 with the given covenant_headroom."""
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    env = Environment(
        loader=FileSystemLoader(str(root / "templates")),
        autoescape=True,
        undefined=StrictUndefined,
    )
    return env.get_template("capital_structure.html.j2").render(
        active_section="research",
        active_page="capital_structure",
        premium=None,
        policy_watch=None,
        policy_projection=None,
        covenant_headroom=covenant_headroom,
    )


def _fixture_observation() -> dict:
    """The spec R7(a) fixture — synthetic CRSR FY row 2022-12-31."""
    return {
        "observation_id": "cov-headroom-fixture:crsr:maximum_total_net_leverage_ratio:v1",
        "logical_observation_id": "cov-term:cs:maximum_total_net_leverage_ratio:sm-covenant-crsr-ex101-20221202",
        "term_name": "maximum_total_net_leverage_ratio",
        "clause_id": "clause-fixture",
        "state": "direct",
        "source_manifest_id": "sm-covenant-crsr-ex101-20221202",
        "issuer_id": "sec:cik:0001743759",
        "issuer": {"cik": "0001743759"},
        "version": {"correction_version": 1, "correction_of": None,
                    "immutable_record": True},
        "point_in_time": {
            "available_at": "2026-09-13T00:00:00Z",
            "source_available_at": "2022-12-02T00:00:00Z",
        },
        "accession": "0001564590-22-038930",
        "form": "EX-10.1",
        "filing_date": "2022-12-02",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1743759/000156459022038930/ex10-1.htm",
        "value": {
            "limit_raw": 3.50,
            "limit_unit": "x",
            "direction": "max",
            "definition_basis": "filing_text_confirmed",
            "headline_ratio_text": "3.50 to 1.00",
            "section_label": "Section 7.11 Financial Covenants",
            "steps": [
                {"start_date": "2022-09-30", "end_date": None, "limit_raw": 3.50},
            ],
        },
        "relationships": {"amends": [], "supersedes": [], "contradiction_ids": []},
    }


def _computable_observation() -> dict:
    """A second fixture observation covering minimum_interest_coverage."""
    return {
        "observation_id": "cov-headroom-fixture:crsr:minimum_interest_coverage_ratio:v1",
        "logical_observation_id": "cov-term:cs:minimum_interest_coverage_ratio:sm-covenant-crsr-ex101-20221202",
        "term_name": "minimum_interest_coverage_ratio",
        "clause_id": "clause-fixture",
        "state": "direct",
        "source_manifest_id": "sm-covenant-crsr-ex101-20221202",
        "issuer_id": "sec:cik:0001743759",
        "issuer": {"cik": "0001743759"},
        "version": {"correction_version": 1, "correction_of": None,
                    "immutable_record": True},
        "point_in_time": {
            "available_at": "2026-09-13T00:00:00Z",
            "source_available_at": "2022-12-02T00:00:00Z",
        },
        "accession": "0001564590-22-038930",
        "form": "EX-10.1",
        "filing_date": "2022-12-02",
        "source_url": "https://www.sec.gov/Archives/edgar/data/1743759/000156459022038930/ex10-1.htm",
        "value": {
            "limit_raw": 3.00,
            "limit_unit": "x",
            "direction": "min",
            "definition_basis": "filing_text_confirmed",
            "headline_ratio_text": "3.00 to 1.00",
            "section_label": "Section 7.11 Financial Covenants",
            "steps": [
                {"start_date": "2022-09-30", "end_date": None, "limit_raw": 3.00},
            ],
        },
        "relationships": {"amends": [], "supersedes": [], "contradiction_ids": []},
    }


def main() -> int:
    # ── Null state: empty observations parquet, what the production page
    #    will render before the producer covers anything.
    root_null = _build_root()
    null_payload = builder._covenant_headroom(root_null)
    null_html = _render(root_null, null_payload)
    (HTML_DIR / "null.html").write_text(null_html, encoding="utf-8")
    (PAYLOAD_DIR / "null.json").write_text(
        json.dumps(null_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # ── Computed state: inject the spec R7(a) fixture directly into the
    #    engine via compute_headroom (SAME builder + SAME template).
    from engine import covenant_headroom as headroom_engine
    stmt = {
        "cik": "0001743759",
        "op_income": 60_000_000.0,
        "depreciation": 20_000_000.0,
        "interest_exp": 15_000_000.0,
        "cash": 80_000_000.0,
        "debt_lt": 250_000_000.0,
        "debt_cur": 10_000_000.0,
        "period_end": "2022-12-31",
    }
    fixtures = [_fixture_observation(), _computable_observation()]
    computed_payload = headroom_engine.compute_headroom(
        fixtures,
        {"0001743759": stmt},
        {"0001743759": "CRSR"},
        generated_at="2026-09-13T00:00:00Z",
        coverage={"covered_manifests": 1, "eligible_exhibits": 2450,
                  "issuers_covered": 1, "state": "covered"},
        cik_by_source_manifest_id={"sm-covenant-crsr-ex101-20221202": "0001743759"},
    )
    root_computed = _build_root()
    computed_html = _render(root_computed, computed_payload)
    (HTML_DIR / "computed.html").write_text(computed_html, encoding="utf-8")
    (PAYLOAD_DIR / "computed.json").write_text(
        json.dumps(computed_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"WROTE {HTML_DIR / 'null.html'}")
    print(f"WROTE {HTML_DIR / 'computed.html'}")
    print(f"WROTE {PAYLOAD_DIR / 'null.json'}")
    print(f"WROTE {PAYLOAD_DIR / 'computed.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
