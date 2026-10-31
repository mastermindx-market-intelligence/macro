"""Synthetic battery for the relationship package v2 derivation rules.

Every case clones the committed SWKS->AAPL observation row as a template,
adjusts the facts under test, recomputes the identity formulas, and asserts the
derived package/edges behavior: direction and manifest security resolution,
magnitude kinds never summed, PIT hygiene, conflict preservation, path
validity, verbatim conditions, refusals, source-state quarantine, document
scoping, and the undisclosed/null rule.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import package_v2 as pv2  # noqa: E402

EXTRACTION_PATH = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/extraction/swks_aapl_m1.jsonl"
)
SOURCES_DIR = REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/sources"
MANIFEST_PATH = REPO_ROOT / "research/theme_graph/coverage_20261019/UNIVERSE_MANIFEST.json"
ACC_24 = "0000004127-24-000131"
ACC_25 = "0000004127-25-000085"
ACC_26 = "0000004127-26-000003"
ACC_FAKE = "0000004127-99-000001"
SWKS = "ISS:US-XNAS-SWKS"
AAPL = "ISS:US-XNAS-AAPL"
GOOG = "ISS:US-XNAS-GOOG"
AS_OF = "2026-10-21T00:00:00Z"

pytestmark = pytest.mark.data_gate

_MANIFEST_VERSION, _ISSUERS = pv2.load_manifest_issuers(MANIFEST_PATH)
_INPUTS = [{"path": "battery-synthetic-inputs", "sha256": "0" * 64}]


def _template_row() -> dict:
    rows = [
        json.loads(line)
        for line in EXTRACTION_PATH.read_text("utf-8").splitlines()
        if line.strip()
    ]
    return copy.deepcopy(next(r for r in rows if r.get("row_kind") == "observation"))


def _source_ref(accession: str) -> dict:
    rows = [
        json.loads(line)
        for line in EXTRACTION_PATH.read_text("utf-8").splitlines()
        if line.strip()
    ]
    for row in rows:
        if row.get("row_kind") in ("observation", "document_assessment") and (
            row["source_ref"]["accession"] == accession
        ):
            return copy.deepcopy(row["source_ref"])
    raise AssertionError(f"no committed source_ref for {accession}")


def _reid(row: dict) -> dict:
    """Recompute the observation id after synthetic mutation."""
    source = row["source_ref"]
    row["observation_id"] = (
        "obs:"
        + hashlib.sha256(
            pv2.canon(
                [
                    source["accession"],
                    source["byte_start"],
                    source["byte_end"],
                    row["species"],
                    row["subject"]["issuer_id"],
                    row["object"]["issuer_id"],
                ]
            ).encode("utf-8")
        ).hexdigest()[:20]
    )
    return row


def _real_excerpts(*accessions: str) -> dict:
    out = {}
    for acc in accessions:
        out[acc] = json.loads((SOURCES_DIR / f"{acc}.json").read_text("utf-8"))
    return out


def _build(rows, excerpts, as_of: str = AS_OF):
    return pv2.build_package(
        [copy.deepcopy(r) for r in rows], excerpts, _ISSUERS, as_of, _MANIFEST_VERSION, _INPUTS
    )


def _single_edge(edges_doc: dict) -> dict:
    assert len(edges_doc["edges"]) == 1, edges_doc["edges"]
    return edges_doc["edges"][0]


def _find_warning(package: dict, title: str) -> dict:
    matches = [w for w in package["warnings"] if w["title"] == title]
    assert matches, f"missing warning {title}: {package['warnings']}"
    return matches[0]


# --- case01 -----------------------------------------------------------------


def test_case01_share_classes_one_issuer_edge():
    row = _template_row()
    row["object"] = {
        "issuer_id": GOOG,
        "name_as_filed": "Google",
        "anonymous_alias": None,
        "non_edge_reason": None,
    }
    _reid(row)
    package, edges_doc = _build([row], _real_excerpts(ACC_24))
    edge = _single_edge(edges_doc)
    assert edge["direction"] == {
        "from_issuer_id": SWKS,
        "to_issuer_id": GOOG,
        "from_role": "supplier",
        "to_role": "customer",
    }
    # Both GOOG share classes are carried on the same issuer edge.
    assert edge["to"]["security_ids"] == ["SEC:US-XNAS-GOOG", "SEC:US-XNAS-GOOGL"]
    assert edge["from"]["security_ids"] == ["SEC:US-XNAS-SWKS"]
    assert edge["relationship_key"] != _m1_relationship_key()


def _m1_relationship_key() -> str:
    return "rel:" + hashlib.sha256(
        pv2.canon(["supplier_customer", SWKS, AAPL, "all"]).encode("utf-8")
    ).hexdigest()[:20]


# --- case02 -----------------------------------------------------------------


def test_case02_magnitude_kinds_never_summed():
    row = _template_row()
    fy2024 = copy.deepcopy(row["magnitudes"][0])
    procurement = copy.deepcopy(fy2024)
    procurement["kind"] = "buyer_procurement_share"
    procurement["value"] = 1000000.0
    procurement["unit"] = "usd"
    procurement["xbrl_fact_id"] = None
    row["magnitudes"] = [fy2024, procurement]
    _reid(row)
    package, edges_doc = _build([row], _real_excerpts(ACC_24))
    edge = _single_edge(edges_doc)
    current = edge["current_magnitudes"]
    assert sorted(entry["kind"] for entry in current) == [
        "buyer_procurement_share",
        "seller_revenue_share",
    ]
    by_kind = {entry["kind"]: entry for entry in current}
    assert by_kind["seller_revenue_share"]["value"] == 0.69
    assert by_kind["buyer_procurement_share"]["value"] == 1000000.0
    assert edge["magnitude_state"] == "disclosed"
    assert edge["conflicts"] == []
    assert package["counts"]["revisions"] == 2


# --- case03 -----------------------------------------------------------------


def test_case03_pit_future_row_leaves_no_trace():
    row = _template_row()
    row["published_at"] = "2030-01-01T00:00:00Z"
    _reid(row)
    package, edges_doc = _build([row], _real_excerpts(ACC_24))
    assert package["counts"]["observations_in"] == 1
    assert package["counts"]["observations_pit_visible"] == 0
    assert edges_doc["edges"] == []
    assert package["observations"] == []
    blob = json.dumps(package) + json.dumps(edges_doc)
    assert "2030-01-01" not in blob
    assert row["observation_id"] not in blob


# --- case04 -----------------------------------------------------------------


def test_case04_conflicting_parties_kept_never_averaged():
    row_a = _template_row()
    row_a["magnitudes"] = [copy.deepcopy(row_a["magnitudes"][0])]  # FY2024 0.69
    _reid(row_a)
    row_b = _template_row()
    row_b["source_ref"] = _source_ref(ACC_25)
    row_b["asserting_party"] = AAPL
    row_b["published_at"] = "2025-11-07T21:08:12Z"
    row_b["magnitudes"] = [copy.deepcopy(row_a["magnitudes"][0])]
    row_b["magnitudes"][0]["value"] = 0.70
    row_b["magnitudes"][0]["xbrl_fact_id"] = None
    _reid(row_b)
    assert row_a["observation_id"] != row_b["observation_id"]
    package, edges_doc = _build(
        [row_a, row_b], _real_excerpts(ACC_24, ACC_25)
    )
    edge = _single_edge(edges_doc)
    assert edge["magnitude_state"] == "conflicted"
    assert edge["asserting_parties"] == [AAPL, SWKS]
    conflicts = edge["conflicts"]
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict["kind"] == "seller_revenue_share"
    assert conflict["period"]["label"] == "FY2024"
    values = conflict["values"]
    assert [v["asserting_party"] for v in values] == [AAPL, SWKS]
    assert sorted(v["value"] for v in values) == [0.69, 0.70]
    current = edge["current_magnitudes"]
    assert len(current) == 1
    assert current[0]["value"] is None
    blob = json.dumps(package) + json.dumps(edges_doc)
    assert "0.695" not in blob  # never averaged, summed or netted
    assert package["counts"]["revisions"] == 2


# --- case05 -----------------------------------------------------------------


def _path_edge(
    from_iid: str,
    to_iid: str,
    product_key: str = "all",
    status: str = "asserted",
    start=None,
    end: str = "2024-09-27",
) -> dict:
    return {
        "relationship_key": f"rel:{from_iid}->{to_iid}",
        "species": "supplier_customer",
        "direction": {
            "from_issuer_id": from_iid,
            "to_issuer_id": to_iid,
            "from_role": "supplier",
            "to_role": "customer",
        },
        "relation_status": status,
        "scope": {"product_key": product_key, "segment": None, "geography": None},
        "asserted_period": {"start": start, "end": end},
    }


def test_case05_path_validity_refusals():
    ab = _path_edge(SWKS, AAPL)
    bc = _path_edge(AAPL, GOOG, start="2024-01-01", end="2025-10-03")
    assert pv2.path_validity(ab, bc) == (True, "ok")
    other_head = _path_edge(GOOG, SWKS)
    assert pv2.path_validity(other_head, bc) == (False, "not_chained")
    terminated = _path_edge(SWKS, AAPL, status="terminated")
    assert pv2.path_validity(terminated, bc) == (False, "not_asserted")
    assert pv2.path_validity(ab, _path_edge(AAPL, GOOG, status="denied")) == (
        False,
        "not_asserted",
    )
    assert pv2.path_validity(ab, _path_edge(AAPL, GOOG, product_key="SoC")) == (
        False,
        "product_key_mismatch",
    )
    # "all" matches only "all" — no wildcard semantics.
    assert pv2.path_validity(
        _path_edge(SWKS, AAPL, product_key="all"),
        _path_edge(AAPL, GOOG, product_key="SoC"),
    ) == (False, "product_key_mismatch")
    disjoint = _path_edge(AAPL, GOOG, start="2025-01-01", end="2025-12-31")
    assert pv2.path_validity(ab, disjoint) == (False, "period_disjoint")
    # null start collapses to the interval end; touching intervals overlap.
    touching = _path_edge(SWKS, AAPL, start=None, end="2024-09-27")
    same_day = _path_edge(AAPL, GOOG, start="2024-09-27", end="2025-10-03")
    assert pv2.path_validity(touching, same_day) == (True, "ok")


# --- case06 -----------------------------------------------------------------


def test_case06_conditions_verbatim_no_score_fields(tmp_path):
    row = _template_row()
    row["conditions"] = [
        {
            "kind": "concentration_risk",
            "text": "Apple is accounted for in aggregate through distributors.",
            "byte_start": row["source_ref"]["byte_start"],
            "byte_end": row["source_ref"]["byte_end"],
            "span_sha256": row["source_ref"]["span_sha256"],
        },
        {
            "kind": "pricing",
            "text": "Pricing is negotiated annually.",
            "byte_start": row["source_ref"]["byte_start"],
            "byte_end": row["source_ref"]["byte_end"],
            "span_sha256": row["source_ref"]["span_sha256"],
        },
    ]
    _reid(row)
    extraction = tmp_path / "rows.jsonl"
    extraction.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    env = dict(os.environ)
    env["TZ"] = "UTC"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_relationship_observations.py",
            "--as-of",
            AS_OF,
            "--extraction",
            str(extraction),
            "--sources",
            str(SOURCES_DIR),
            "--out-dir",
            str(out),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    package = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    edges_doc = json.loads((out / "relationship_edges.json").read_text("utf-8"))
    edge = _single_edge(edges_doc)
    assert edge["conditions"] == [
        {
            "kind": c["kind"],
            "text": c["text"],
            "byte_start": c["byte_start"],
            "byte_end": c["byte_end"],
            "span_sha256": c["span_sha256"],
            "accession": row["source_ref"]["accession"],
        }
        for c in row["conditions"]
    ]
    forbidden = ("sign", "score", "weight", "polarity", "strength")

    def _scan(node):
        if isinstance(node, dict):
            for key, value in node.items():
                lowered = key.lower()
                for word in forbidden:
                    assert word not in lowered, f"forbidden key {key!r}"
                _scan(value)
        elif isinstance(node, list):
            for value in node:
                _scan(value)

    _scan(package)
    _scan(edges_doc)


# --- case07 -----------------------------------------------------------------


def test_case07_self_edge_refused_channel_no_intermediary_edge_and_reverse_direction_distinct():
    self_row = _template_row()
    self_row["object"] = {
        "issuer_id": SWKS,
        "name_as_filed": "Skyworks Solutions, Inc.",
        "anonymous_alias": None,
        "non_edge_reason": None,
    }
    _reid(self_row)
    package, edges_doc = _build([self_row], _real_excerpts(ACC_24))
    assert edges_doc["edges"] == []
    assert package["counts"]["edges"] == 0
    assert package["counts"]["observations_refused"] == 1
    obs = package["observations"][0]
    assert obs["disposition"] == "refused"
    assert obs["refusal_reason"] == "self_edge"
    _find_warning(package, "relationship-self-edge")

    # The channel list describes how revenue flows; it never mints an edge to
    # the intermediary — the single edge is keyed to the named counterparty.
    channel_row = _template_row()
    _reid(channel_row)
    package_c, edges_doc_c = _build([channel_row], _real_excerpts(ACC_24))
    assert channel_row["channel"] == ["distributor", "contract_manufacturer", "direct"]
    assert len(edges_doc_c["edges"]) == 1
    assert edges_doc_c["edges"][0]["to"]["issuer_id"] == AAPL

    # The reverse-direction assertion (AAPL as supplier of SWKS) is a distinct
    # edge with its own key, never merged into the SWKS->AAPL edge.
    reversed_row = _template_row()
    reversed_row["source_ref"] = _source_ref(ACC_25)
    reversed_row["subject"] = {
        "cik": "0000320193",
        "issuer_id": AAPL,
        "name_as_filed": "Apple Inc.",
        "security_ids": ["SEC:US-XNAS-AAPL"],
    }
    reversed_row["object"] = {
        "issuer_id": SWKS,
        "name_as_filed": "Skyworks Solutions, Inc.",
        "anonymous_alias": None,
        "non_edge_reason": None,
    }
    reversed_row["subject_role"] = "supplier"
    reversed_row["asserting_party"] = AAPL
    _reid(reversed_row)
    package_r, edges_doc_r = _build(
        [channel_row, reversed_row], _real_excerpts(ACC_24, ACC_25)
    )
    assert len(edges_doc_r["edges"]) == 2
    directions = sorted(
        (
            edge["direction"]["from_issuer_id"],
            edge["direction"]["to_issuer_id"],
        )
        for edge in edges_doc_r["edges"]
    )
    assert directions == [(AAPL, SWKS), (SWKS, AAPL)]
    keys = {edge["relationship_key"] for edge in edges_doc_r["edges"]}
    assert len(keys) == 2


# --- case08 -----------------------------------------------------------------


def test_case08_refused_species_and_unnamed_provider(tmp_path):
    species_row = _template_row()
    species_row["species"] = "theme"
    _reid(species_row)
    provider_row = _template_row()
    provider_row["species"] = "component_dependency"
    provider_row["subject_role"] = "dependent"
    provider_row["object"] = {
        "issuer_id": None,
        "name_as_filed": "an unnamed packaging provider",
        "anonymous_alias": None,
        "non_edge_reason": "ANONYMOUS_ALIAS",
    }
    _reid(provider_row)
    extraction = tmp_path / "rows.jsonl"
    extraction.write_text(
        json.dumps(species_row, sort_keys=True)
        + "\n"
        + json.dumps(provider_row, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    env = dict(os.environ)
    env["TZ"] = "UTC"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_relationship_observations.py",
            "--as-of",
            AS_OF,
            "--extraction",
            str(extraction),
            "--sources",
            str(SOURCES_DIR),
            "--out-dir",
            str(out),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "::warning title=relationship-species-refused::" in proc.stdout
    assert "::warning title=relationship-provider-unnamed::" in proc.stdout
    package = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    edges_doc = json.loads((out / "relationship_edges.json").read_text("utf-8"))
    assert edges_doc["edges"] == []
    assert package["counts"]["observations_refused"] == 2
    assert package["counts"]["edges"] == 0
    dispositions = {obs["disposition"] for obs in package["observations"]}
    assert dispositions == {"refused"}
    reasons = {obs["refusal_reason"] for obs in package["observations"]}
    assert reasons == {"species_refused", "provider_unnamed"}


# --- case09 -----------------------------------------------------------------


def test_case09_source_unavailable_corrupt_unavailable_coverage_null_not_zero_stale_kept_not_restated_keeps_asserted():
    # (a) excerpt missing -> quarantined, not an edge.
    unavailable_row = _template_row()
    unavailable_row["source_ref"] = _source_ref(ACC_24)
    unavailable_row["source_ref"]["accession"] = ACC_FAKE
    unavailable_row["source_ref"]["url"] = (
        "https://www.sec.gov/Archives/edgar/data/4127/000000412799000001/x.htm"
    )
    _reid(unavailable_row)
    package_a, edges_doc_a = _build([unavailable_row], {})
    assert edges_doc_a["edges"] == []
    obs = package_a["observations"][0]
    assert obs["disposition"] == "quarantined"
    assert obs["source_state"] == "source_unavailable"
    _find_warning(package_a, "relationship-source-unavailable")

    # (b) excerpt failing offline verification -> quarantined as corrupt.
    corrupt_excerpt = _real_excerpts(ACC_24)[ACC_24]
    corrupt_excerpt = copy.deepcopy(corrupt_excerpt)
    corrupt_excerpt["span"]["raw_sha256"] = "0" * 64
    package_b, edges_doc_b = _build([_template_row()], {ACC_24: corrupt_excerpt})
    assert edges_doc_b["edges"] == []
    obs = package_b["observations"][0]
    assert obs["disposition"] == "quarantined"
    assert obs["source_state"] == "source_corrupt"
    _find_warning(package_b, "relationship-source-corrupt")

    # (c) a coverage row in state unavailable stays unavailable.
    coverage_row = {
        "schema": "company_intelligence.relationship_extraction/v1",
        "row_kind": "coverage",
        "temporal_eligibility": "acceptance_time",
        "published_at": "2026-01-30T21:06:48Z",
        "ingested_at": "2026-10-21T10:55:11Z",
        "period_end": "2025-10-03",
        "issuer_id": SWKS,
        "documents": [ACC_24],
        "state": "unavailable",
        "reason": "filing_body_unreadable",
    }
    package_c, _ = _build([coverage_row], {})
    assert package_c["coverage"] == [
        {
            "issuer_id": SWKS,
            "state": "unavailable",
            "period_end": "2025-10-03",
            "documents": [ACC_24],
            "known_at": "2026-01-30T21:06:48Z",
        }
    ]

    # (d) a disclosed magnitude with no number stays null and is never 0.
    null_row = _template_row()
    null_row["magnitudes"] = [
        {
            "kind": "seller_revenue_share",
            "value": None,
            "unit": "ratio",
            "precision": "lower_bound",
            "period": {
                "start": "2023-09-30",
                "end": "2024-09-27",
                "label": "FY2024",
            },
            "numerator_scope": "net revenue from Apple",
            "denominator_scope": "Skyworks consolidated net revenue",
            "xbrl_fact_id": None,
        }
    ]
    _reid(null_row)
    package_d, edges_doc_d = _build([null_row], _real_excerpts(ACC_24))
    edge = _single_edge(edges_doc_d)
    assert edge["magnitude_state"] == "disclosed"
    rev = edge["magnitude_history"][0]
    assert rev["value"] is None
    assert rev["value"] != 0
    assert edge["current_magnitudes"][0]["value"] is None

    # (e) a stale edge is kept, marked stale, never dropped.
    stale_row = _template_row()
    stale_row["published_at"] = "2020-06-01T00:00:00Z"
    _reid(stale_row)
    package_e, edges_doc_e = _build([stale_row], _real_excerpts(ACC_24))
    edge = _single_edge(edges_doc_e)
    assert edge["freshness_state"] == "stale"
    assert edge["last_asserted_at"] == "2020-06-01T00:00:00Z"
    assert package_e["counts"]["edges"] == 1

    # (f) a not_restated correction never changes relation_status.
    assessment = {
        "schema": "company_intelligence.relationship_extraction/v1",
        "row_kind": "document_assessment",
        "temporal_eligibility": "acceptance_time",
        "published_at": "2026-01-30T21:06:48Z",
        "ingested_at": "2026-10-21T10:55:11Z",
        "period_end": "2025-10-03",
        "sec_index_header_acceptance_et": "20260130160648",
        "sec_submissions_acceptance_raw": "2026-01-31T02:06:48.000Z",
        "assessment_id": "asm:" + "1" * 20,
        "issuer_id": SWKS,
        "amends_accession": ACC_24,
        "assessment": "not_restated",
        "reason": "part_iii_only_amendment",
        "extracted_by": {
            "agent": "battery",
            "lane_run_id": None,
            "method": "narrative_span",
        },
        "source_ref": _source_ref(ACC_26),
    }
    package_f, edges_doc_f = _build(
        [_template_row(), assessment], _real_excerpts(ACC_24, ACC_26)
    )
    edge = _single_edge(edges_doc_f)
    assert edge["relation_status"] == "asserted"
    assert edge["correction_lineage"] == [
        {
            "assessment_id": assessment["assessment_id"],
            "accession": ACC_26,
            "amends_accession": ACC_24,
            "assessment": "not_restated",
            "reason": "part_iii_only_amendment",
            "known_at": "2026-01-30T21:06:48Z",
            "effect": "none",
        }
    ]


# --- case11 -----------------------------------------------------------------


def test_case11_anonymous_aliases_document_scoped_never_merged():
    def _alias_row(accession: str) -> dict:
        row = _template_row()
        row["source_ref"] = _source_ref(accession)
        row["object"] = {
            "issuer_id": None,
            "name_as_filed": None,
            "anonymous_alias": "Customer A",
            "non_edge_reason": "ANONYMOUS_ALIAS",
        }
        _reid(row)
        return row

    row_a = _alias_row(ACC_24)
    row_b = _alias_row(ACC_25)
    assert row_a["observation_id"] != row_b["observation_id"]
    package, edges_doc = _build([row_a, row_b], _real_excerpts(ACC_24, ACC_25))
    assert edges_doc["edges"] == []
    non_edges = edges_doc["non_edges"]
    assert len(non_edges) == 2
    keys = {entry["non_edge_key"] for entry in non_edges}
    assert len(keys) == 2  # document-scoped: never merged across documents
    for entry in non_edges:
        assert entry["anonymous_alias"] == "Customer A"
        assert entry["non_edge_reason"] == "ANONYMOUS_ALIAS"
        assert entry["object_name_as_filed"] is None
    assert package["counts"]["non_edges"] == 2


# --- case12 -----------------------------------------------------------------


def test_case12_no_magnitudes_undisclosed_null():
    row = _template_row()
    row["magnitudes"] = []
    _reid(row)
    package, edges_doc = _build([row], _real_excerpts(ACC_24))
    edge = _single_edge(edges_doc)
    assert edge["magnitude_state"] == "undisclosed"
    assert edge["current_magnitudes"] == []
    assert edge["magnitude_history"] == []
    assert edge["asserted_period"] == {"start": None, "end": "2024-09-27"}
    assert package["counts"]["revisions"] == 0
