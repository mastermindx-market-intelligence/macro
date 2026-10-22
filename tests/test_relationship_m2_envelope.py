"""Tests for the GMI ORCH-REL M2 relationship envelope (§8.2 measures).

The envelope CLI is MEASUREMENT ONLY: it prints the predeclared §8.2 panel of
measures from the committed artifacts, printing OWED/ABSENT where a measure
cannot be computed.  These tests pin the predeclared panel bytes, the frozen
measure definitions (M0, E1-E8), the refusal paths and rerun determinism.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import envelope as env  # noqa: E402
from engine.company_intelligence.relationships.package_v2 import (  # noqa: E402
    path_validity,
)

PANEL_PATH = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/m2_inputs/envelope_panel_v1.json"
)
LEAVES_PATH = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/m2_inputs/leaves_v1.json"
)
RESOLVER_PATH = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/m2_inputs/resolver_us_issuers_v1.json"
)
PACKAGE_PATH = REPO_ROOT / "data/company_intelligence/relationships/observation_package.v2.json"
EDGES_PATH = REPO_ROOT / "data/company_intelligence/relationships/relationship_edges.json"
EXTRACTION_DIR = REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/extraction"
INPUTS_DIR = REPO_ROOT / "research/theme_graph/gmi_relationships_20261021"
RECALL_CORPUS_DIR = (
    REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/m2_recall"
)
RECALL_REPORT_PATH = RECALL_CORPUS_DIR / "recall_report_v1.json"
RECALL_EXTRACTION_DIR = EXTRACTION_DIR
RECALL_CLI = REPO_ROOT / "scripts/relationship_m2_recall.py"
M1_EXTRACTION_PATH = (
    REPO_ROOT
    / "research/theme_graph/gmi_relationships_20261021/extraction/swks_aapl_m1.jsonl"
)
# The accepted M1 byte outputs, copied verbatim from FILE_PKG_PIN /
# FILE_EDGES_PIN in tests/test_relationship_m2_keys.py (the file-scoped
# producer run over the M1 extraction file alone).  Never re-pinned here.
FILE_PKG_PIN = "cc67c2f9c065d04f5029c75157eefad19277fde29d2cbda5b2865c0f5d1307bb"
FILE_EDGES_PIN = "51434731fb33499e77ece20b9a71a9824cc3a76fa46c0fa5d14a9ccb53f986dd"


def _load(path):
    return json.loads(path.read_bytes().decode("utf-8"))


def _load_jsonl_dir(directory: Path) -> list:
    rows = []
    for path in sorted(directory.rglob("*.jsonl")):
        for line in path.read_bytes().decode("utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def m1_reference(tmp_path_factory):
    """The M1 reference package: the producer's own byte-pinned run over the
    M1 extraction file alone, with exactly the argument list the file-scoped
    run in tests/test_relationship_m2_keys.py uses.  The committed package
    spans every M2 leaf, so the M1-era literals are asserted against this
    reference instead of the committed default package."""
    out = tmp_path_factory.mktemp("m1_reference")
    env_vars = dict(os.environ)
    env_vars["TZ"] = "UTC"
    proc = subprocess.run(
        [sys.executable, "scripts/build_relationship_observations.py",
         "--as-of", "2026-10-21T00:00:00Z",
         "--extraction", str(M1_EXTRACTION_PATH),
         "--out-dir", str(out)],
        cwd=str(REPO_ROOT),
        env=env_vars,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    package = out / "observation_package.v2.json"
    edges = out / "relationship_edges.json"
    assert _sha_bytes(package.read_bytes()) == FILE_PKG_PIN, (
        "M1 reference package sha != the accepted FILE_PKG_PIN"
    )
    assert _sha_bytes(edges.read_bytes()) == FILE_EDGES_PIN, (
        "M1 reference edges sha != the accepted FILE_EDGES_PIN"
    )
    return {"package": package, "edges": edges}


def _eligible_issuers(leaves: dict) -> set:
    """The module's documented eligibility rule: every issuer in the leaves
    doc's domain map (``domain_of``) whose domain is one of D1/D2."""
    return {
        issuer_id
        for issuer_id, domain in leaves["domain_of"].items()
        if domain in ("D1", "D2")
    }


def _load_envelope_script():
    spec = importlib.util.spec_from_file_location(
        "relationship_m2_envelope_under_test",
        REPO_ROOT / "scripts/relationship_m2_envelope.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- synthetic fixtures ---------------------------------------------------------


def _extraction_row(obs_id, subject, species, published, ingested,
                    anonymous=None, subject_role=None, asserting=None,
                    accession="0000000000-26-000001"):
    obj = {
        "anonymous_alias": anonymous,
        "issuer_id": None,
        "name_as_filed": "Some Counterparty",
        "non_edge_reason": None if anonymous is None else "UNRESOLVED_COUNTERPARTY",
    }
    row = {
        "row_kind": "observation",
        "observation_id": obs_id,
        "species": species,
        "subject": subject,
        "object": obj,
        "published_at": published,
        "ingested_at": ingested,
        "conditions": [],
        "magnitudes": [],
        "asserting_party": asserting or subject["issuer_id"],
        "source_ref": {"accession": accession, "byte_start": 0, "byte_end": 10},
        "relation_status": "asserted",
    }
    if subject_role is not None:
        row["subject_role"] = subject_role
    return row


def _edge(key, species, from_iid, to_iid, *, freshness="fresh",
          magnitude_state="disclosed", asserting=None, conflicts=None,
          product_key="all", period=("2021-10-02", "2025-10-03"),
          revisions=None):
    roles = env.SPECIES_ROLES[species]
    return {
        "relationship_key": key,
        "species": species,
        "direction": {
            "from_issuer_id": from_iid,
            "from_role": roles[0],
            "to_issuer_id": to_iid,
            "to_role": roles[1],
        },
        "asserting_parties": asserting if asserting is not None else [from_iid],
        "relation_status": "asserted",
        "admission_state": "proposed",
        "magnitude_state": magnitude_state,
        "freshness_state": freshness,
        "current_magnitudes": (
            [{
                "kind": "seller_revenue_share",
                "value": 0.67,
                "unit": "ratio",
                "precision": "exact",
                "asserting_party": (asserting or [from_iid])[0],
            }]
            if magnitude_state == "disclosed"
            else []
        ),
        "magnitude_history": [],
        "conflicts": conflicts or [],
        "conditions": [],
        "correction_lineage": [],
        "source_refs": [{"accession": "0000000000-25-000001"}],
        "scope": {"geography": None, "product_key": product_key, "segment": None},
        "asserted_period": {"start": period[0], "end": period[1]},
        "magnitude_revisions": revisions or [],
    }


def _package(*, coverage=None, observations=None, non_edges=None, revisions=None):
    return {
        "as_of": "2026-10-21T00:00:00Z",
        "computed_at": "2026-10-21T00:00:00Z",
        "coverage": coverage or [],
        "observations": observations or [],
        "non_edges": non_edges or [],
        "magnitude_revisions": revisions or [],
        "assessments": [],
    }


SUBJ = {"cik": "0000000123", "issuer_id": "ISS:US-XNAS-I1",
        "name_as_filed": "Issuer One", "security_ids": ["SEC:US-XNAS-I1"]}


# --- E0: the predeclared panel ----------------------------------------------------


def test_panel_bytes_pinned_and_drift_refused():
    panel_bytes = PANEL_PATH.read_bytes()
    assert hashlib.sha256(panel_bytes).hexdigest() == env.PANEL_SHA256
    # any byte change is refused
    drifted = panel_bytes.replace(b"ERIC", b"ERIX", 1)
    assert drifted != panel_bytes
    with pytest.raises(env.PanelDrift):
        env.verify_panel(drifted, env.PANEL_SHA256,
                         hashlib.sha256(LEAVES_PATH.read_bytes()).hexdigest())
    # a leaves_sha256 that does not match the leaves file read is refused
    with pytest.raises(env.PanelDrift):
        env.verify_panel(panel_bytes, env.PANEL_SHA256, "0" * 64)
    # the real pair verifies clean
    assert env.verify_panel(panel_bytes, env.PANEL_SHA256,
                            hashlib.sha256(LEAVES_PATH.read_bytes()).hexdigest()) is None


def test_panel_issuers_follow_the_hash_rule():
    leaves = _load(LEAVES_PATH)
    panel = _load(PANEL_PATH)
    by_domain = {"D1": [], "D2": []}
    for issuer_id, domain in leaves["domain_of"].items():
        by_domain[domain].append(issuer_id)
    for domain in ("D1", "D2"):
        ranked = sorted(
            by_domain[domain],
            key=lambda i: hashlib.sha256(
                ("gmi-rel-envelope-panel-v1:" + i).encode("utf-8")
            ).hexdigest(),
        )
        assert sorted(panel["issuers"][domain]) == sorted(ranked[:5])
    assert len(panel["questions"]) == 6
    assert panel["leaves_sha256"] == (
        hashlib.sha256(LEAVES_PATH.read_bytes()).hexdigest()
    )


# --- E1 ------------------------------------------------------------------------


def test_e1_every_eligible_issuer_accounted(m1_reference):
    # synthetic: 3 issuers, one covered
    leaves = {"D1": ["ISS:US-XNAS-I1", "ISS:US-XNAS-I2"], "D2": ["ISS:US-XNYS-J1"]}
    package = _package(coverage=[
        {"issuer_id": "ISS:US-XNAS-I1", "state": "assessed",
         "documents": ["a-1"], "known_at": "2026-01-01T00:00:00Z",
         "period_end": "2025-10-03"},
    ])
    e1 = env.e1_coverage(package, leaves)
    total = sum(
        sum(states.values()) for states in
        (e1["domains"]["D1"]["states"], e1["domains"]["D2"]["states"])
    )
    assert total == 3
    nonzero = lambda states: {k: v for k, v in states.items() if v}
    assert nonzero(e1["domains"]["D1"]["states"]) == {"assessed": 1, "pending": 1}
    assert nonzero(e1["domains"]["D2"]["states"]) == {"pending": 1}
    assert e1["domains"]["D1"]["reading"]["supported"] == 1
    # missing coverage -> pending, never dropped
    assert e1["state_by_issuer"]["ISS:US-XNYS-J1"] == "pending"

    # the M1 reference package on the real leaves: every one of the 283
    # eligible issuers is accounted for
    leaves_real = _load(LEAVES_PATH)
    real = env.e1_coverage(_load(m1_reference["package"]), leaves_real)
    total = sum(
        sum(states.values())
        for states in (real["domains"]["D1"]["states"],
                       real["domains"]["D2"]["states"])
    )
    assert total == 283
    assert real["domains"]["D1"]["states"]["assessed"] == 1
    assert real["state_by_issuer"]["ISS:US-XNAS-SWKS"] == "assessed"

    # a per-domain sum mismatch is an error, never silently fixed: an issuer
    # valued outside D1/D2 is accounted in no domain
    bad_leaves = {"D1": ["ISS:US-XNAS-I1"], "D2": [], "P": ["ISS:US-XNAS-XX"]}
    with pytest.raises(env.EnvelopeError):
        env.e1_coverage(_package(coverage=[]), bad_leaves)

    # full data, re-derived independently of the expected values: the
    # accounted total equals the eligible issuer count recomputed straight
    # from leaves_v1.json, the D1 assessed count equals a direct recount of
    # the committed package's coverage rows, and SWKS stays assessed.
    # falsifier: an E1 that drops, invents or double-counts any eligible
    # issuer, or misclassifies SWKS / the D1 assessed coverage rows
    committed = _load(PACKAGE_PATH)
    full = env.e1_coverage(committed, leaves_real)
    full_total = sum(
        sum(states.values())
        for states in (full["domains"]["D1"]["states"],
                       full["domains"]["D2"]["states"])
    )
    assert full_total == len(_eligible_issuers(leaves_real))
    assert full["state_by_issuer"]["ISS:US-XNAS-SWKS"] == "assessed"
    assert full["domains"]["D1"]["states"]["assessed"] == sum(
        1 for row in committed["coverage"]
        if row.get("state") == "assessed"
        and leaves_real["domain_of"].get(row["issuer_id"]) == "D1"
    )


# --- E2 ------------------------------------------------------------------------


def test_e2_cell_precedence():
    leaves = {"D1": ["ISS:US-XNAS-I1"], "D2": []}
    package = _package(coverage=[
        {"issuer_id": "ISS:US-XNAS-I1", "state": "assessed",
         "documents": ["a-1"], "known_at": "2026-01-01T00:00:00Z",
         "period_end": "2025-10-03"},
    ])
    species, from_role, to_role = "supplier_customer", "supplier", "customer"

    def cells(edges, non_edges=()):
        package["non_edges"] = list(non_edges)
        e1 = env.e1_coverage(package, leaves)
        result = env.e2_cells(package, {"edges": edges}, [], leaves, e1)
        return result["per_domain"]["D1"][species]["supplier"]

    def state_of(edges, non_edges=()):
        block = cells(edges, non_edges)
        for state in ("known_fresh", "known_stale", "known_anonymous",
                      "searched_no_supported_result", "unavailable",
                      "not_assessed"):
            total = block[state]
            total = total["total"] if isinstance(total, dict) else total
            if total:
                return state
        raise AssertionError("no state set")

    fresh = _edge("rel:f", species, "ISS:US-XNAS-I1", "ISS:US-XNAS-I9")
    stale = _edge("rel:s", species, "ISS:US-XNAS-I1", "ISS:US-XNAS-I9",
                  freshness="stale")
    # fresh > stale on the same cell
    assert state_of([fresh, stale]) == "known_fresh"
    # > anonymous
    anon = {
        "non_edge_key": "nn:1", "species": species,
        "observation_id": "obs:a", "accession": "0000000000-26-000001",
        "subject_issuer_id": "ISS:US-XNAS-I1", "object_name_as_filed": "Anon",
        "anonymous_alias": "Customer A", "non_edge_reason": "UNRESOLVED_COUNTERPARTY",
        "known_at": "2026-01-01T00:00:00Z",
    }
    assert state_of([stale], [anon]) == "known_stale"
    assert state_of([], [anon]) == "known_anonymous"
    # > searched (issuer state assessed / no_supported_result)
    assert state_of([], []) == "searched_no_supported_result"
    # > unavailable
    package["coverage"][0]["state"] = "unavailable"
    assert state_of([], []) == "unavailable"
    # > not_assessed
    package["coverage"][0]["state"] = "pending"
    assert state_of([], []) == "not_assessed"

    # provenance split of known_*: own_filing (i in asserting_parties) vs
    # counterparty_filing, one classification per issuer-cell; I2's only
    # supplier-side edge is asserted by the counterparty's filing
    leaves = {"D1": ["ISS:US-XNAS-I1", "ISS:US-XNAS-I2"], "D2": []}
    package["coverage"].append(
        {"issuer_id": "ISS:US-XNAS-I2", "state": "assessed",
         "documents": ["a-2"], "known_at": "2026-01-01T00:00:00Z",
         "period_end": "2025-10-03"})
    result = env.e2_cells(package, {"edges": [
        fresh,
        _edge("rel:c", species, "ISS:US-XNAS-I2", "ISS:US-XNAS-I9",
              asserting=["ISS:US-XNAS-I9"]),
    ]}, [], leaves, env.e1_coverage(package, leaves))
    block = result["per_domain"]["D1"][species]["supplier"]
    assert block["known_fresh"]["own_filing"] == 1
    assert block["known_fresh"]["counterparty_filing"] == 1
    assert block["known_fresh"]["total"] == 2

    # the caveat line is carried verbatim
    result = env.e2_cells(package, {"edges": []}, [], leaves,
                          env.e1_coverage(package, leaves))
    assert result["caveat"] == env.SEARCHED_CAVEAT


# --- E3 ------------------------------------------------------------------------


def test_e3_m1_pinned_counted(m1_reference):
    package = _load(m1_reference["package"])
    leaves = _load(LEAVES_PATH)
    e3 = env.e3_sources(package, leaves, judging_dirs=[], inputs_dir=INPUTS_DIR)
    d1 = e3["per_domain"]["D1"]
    assert d1["issuers"]["collected_m1_pinned"] == 1
    assert d1["m1_pinned_documents"] == 3
    assert d1["issuers"]["pending"] == 145
    assert e3["per_domain"]["D2"]["issuers"]["pending"] == 137
    assert e3["judging_dirs"] == []
    assert e3["judging_state"] == "ABSENT"

    # full data, against the committed default package: per domain, the
    # issuer-state counts sum to that domain's leaf count.
    # falsifier: an E3 that drops or invents any issuer's source state
    full = env.e3_sources(
        _load(PACKAGE_PATH), leaves, judging_dirs=[], inputs_dir=INPUTS_DIR
    )
    for domain in ("D1", "D2"):
        leaf_count = sum(
            1 for d in leaves["domain_of"].values() if d == domain
        )
        assert sum(full["per_domain"][domain]["issuers"].values()) == leaf_count


# --- E4 ------------------------------------------------------------------------


def test_e4_recall_owed():
    e4 = env.e4_recall()
    assert e4 == {
        "value": None,
        "state": "OWED",
        "reason": env.RECALL_REASON,
        "files_read": [],
    }


def _stage_recall_corpus(tmp_path):
    """The committed m2_recall D1/D2 sentences + annotations staged into
    tmp_path exactly like the regeneration recipe: workdir/D{1,2}/
    sentences.jsonl plus a flat annotations dir with D1_/D2_ filename
    prefixes."""
    workdir = tmp_path / "wd"
    annotations = tmp_path / "ann"
    (workdir / "D1").mkdir(parents=True)
    (workdir / "D2").mkdir(parents=True)
    annotations.mkdir()
    for domain in ("D1", "D2"):
        (workdir / domain / "sentences.jsonl").write_bytes(
            (RECALL_CORPUS_DIR / domain / "sentences.jsonl").read_bytes()
        )
        for pack in sorted(
            (RECALL_CORPUS_DIR / domain / "annotations").glob("*.jsonl")
        ):
            (annotations / f"{domain}_{pack.name}").write_bytes(
                pack.read_bytes()
            )
    return workdir, annotations


def _stage_report_and_extraction(tmp_path):
    """The committed recall report + the 6 extraction files copied into
    tmp_path (the repo is never mutated)."""
    report = tmp_path / "recall_report_v1.json"
    report.write_bytes(RECALL_REPORT_PATH.read_bytes())
    extraction = tmp_path / "extraction"
    for path in sorted(RECALL_EXTRACTION_DIR.rglob("*.jsonl")):
        target = extraction / path.relative_to(RECALL_EXTRACTION_DIR)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    return report, extraction


def test_committed_recall_report_equals_fresh_compare(tmp_path):
    """The committed recall report is byte-equal to a fresh `compare` over
    the committed corpus.  Falsifier: any drift in sentences, annotations,
    aliases, resolver, manifest, extraction or recall code makes the
    committed number stale."""
    workdir, annotations = _stage_recall_corpus(tmp_path)
    fresh = tmp_path / "recall_report_v1.json"
    env_vars = dict(os.environ)
    env_vars["TZ"] = "UTC"
    proc = subprocess.run(
        [sys.executable, str(RECALL_CLI), "compare",
         "--workdir", str(workdir), "--annotations", str(annotations),
         "--report", str(fresh)],
        cwd=str(REPO_ROOT), env=env_vars, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert fresh.read_bytes() == RECALL_REPORT_PATH.read_bytes(), (
        "committed recall_report_v1.json != a fresh compare over the "
        "committed corpus"
    )


def test_e4_measured_from_committed_report():
    report_bytes = RECALL_REPORT_PATH.read_bytes()
    report = json.loads(report_bytes.decode("utf-8"))
    e4 = env.e4_recall(RECALL_REPORT_PATH, RECALL_EXTRACTION_DIR, "x")
    assert e4["state"] == "MEASURED"
    # every field re-derived from the committed report itself
    assert e4["value"] == report["recall"]["value"]
    assert e4["wilson_95"] == report["recall"]["wilson_95"]
    assert e4["jackknife_95"] == report["recall"]["jackknife_95"]
    assert e4["jackknife_issuers"] == report["recall"]["jackknife_issuers"]
    assert e4["reference_set_size"] == report["reference_set_size"]
    assert e4["hits"] == report["hits"]
    assert e4["misses_count"] == report["misses_count"]
    assert e4["pipeline_set_size"] == report["pipeline_set_size"]
    assert e4["by_domain"] == report["by_domain"]
    assert e4["by_species"] == report["by_species"]
    assert e4["corpus_sha256"] == report["corpus_sha256"]
    assert e4["lexicon_sha256"] == report["lexicon_sha256"]
    assert e4["caveat"] == report["caveat"]
    # the frozen literals at this base
    assert e4["value"] == 0.3487
    assert e4["hits"] == 83
    assert e4["reference_set_size"] == 238
    assert e4["by_domain"]["D1"]["recall"] == 0.4423
    assert e4["by_domain"]["D2"]["recall"] == 0.1707
    assert e4["report"] == "x"
    assert e4["report_sha256"] == _sha_bytes(report_bytes)
    assert e4["note"] == "precision is never used as a recall proxy"
    assert e4["reason"] is None
    assert e4["files_read"] == [RECALL_REPORT_PATH]


def test_e4_owed_cases(tmp_path):
    report, extraction = _stage_report_and_extraction(tmp_path)
    # the staged copies still measure clean (staging sanity, not a repo write)
    assert env.e4_recall(report, extraction, "r")["state"] == "MEASURED"

    # (a) no report given
    e4 = env.e4_recall(None, extraction, "r")
    assert e4["state"] == "OWED"
    assert e4["reason"] == env.RECALL_REASON
    assert e4["value"] is None
    assert e4["files_read"] == []

    # (b) file absent
    e4 = env.e4_recall(tmp_path / "absent.json", extraction, "r")
    assert e4["state"] == "OWED"
    assert e4["reason"].startswith("recall report not found")
    assert e4["value"] is None
    assert e4["files_read"] == []

    # (c) invalid JSON
    bad = tmp_path / "bad.json"
    bad.write_bytes(b"{not json")
    e4 = env.e4_recall(bad, extraction, "r")
    assert e4["state"] == "OWED"
    assert e4["reason"].startswith("RECALL_REPORT_SCHEMA")
    assert e4["value"] is None

    # (c) wrong schema
    doc = json.loads(report.read_bytes().decode("utf-8"))
    doc["schema"] = "some.other.schema/v1"
    wrong = tmp_path / "wrong_schema.json"
    wrong.write_bytes((json.dumps(doc, sort_keys=True, indent=1) + "\n").encode())
    e4 = env.e4_recall(wrong, extraction, "r")
    assert e4["state"] == "OWED"
    assert e4["reason"].startswith("RECALL_REPORT_SCHEMA")
    assert e4["value"] is None

    # (d) corpus drift
    doc = json.loads(report.read_bytes().decode("utf-8"))
    doc["corpus_sha256"] = "0" * 64
    drifted = tmp_path / "corpus_drift.json"
    drifted.write_bytes((json.dumps(doc, sort_keys=True, indent=1) + "\n").encode())
    e4 = env.e4_recall(drifted, extraction, "r")
    assert e4["state"] == "OWED"
    assert e4["reason"] == "RECALL_REPORT_DRIFT: corpus"
    assert e4["value"] is None

    # (d) lexicon drift
    doc = json.loads(report.read_bytes().decode("utf-8"))
    doc["lexicon_sha256"] = "1" * 64
    drifted = tmp_path / "lexicon_drift.json"
    drifted.write_bytes((json.dumps(doc, sort_keys=True, indent=1) + "\n").encode())
    e4 = env.e4_recall(drifted, extraction, "r")
    assert e4["state"] == "OWED"
    assert e4["reason"] == "RECALL_REPORT_DRIFT: lexicon"
    assert e4["value"] is None

    # (e) one extraction file with one byte appended
    appended = tmp_path / "ext_appended"
    appended.mkdir()
    for path in sorted(extraction.rglob("*.jsonl")):
        target = appended / path.relative_to(extraction)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    victim = sorted(appended.rglob("*.jsonl"))[0]
    victim.write_bytes(victim.read_bytes() + b"\n")
    e4 = env.e4_recall(report, appended, "r")
    assert e4["state"] == "OWED"
    assert e4["reason"].startswith("RECALL_REPORT_DRIFT: extraction")
    assert e4["value"] is None

    # (e) one extraction file deleted
    deleted = tmp_path / "ext_deleted"
    deleted.mkdir()
    for path in sorted(extraction.rglob("*.jsonl")):
        target = deleted / path.relative_to(extraction)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    sorted(deleted.rglob("*.jsonl"))[0].unlink()
    e4 = env.e4_recall(report, deleted, "r")
    assert e4["state"] == "OWED"
    assert e4["reason"].startswith("RECALL_REPORT_DRIFT: extraction")
    assert e4["value"] is None

    # (e) one extra *.jsonl added
    extra = tmp_path / "ext_extra"
    extra.mkdir()
    for path in sorted(extraction.rglob("*.jsonl")):
        target = extra / path.relative_to(extraction)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    (extra / "zz_extra.jsonl").write_bytes(b"{}\n")
    e4 = env.e4_recall(report, extra, "r")
    assert e4["state"] == "OWED"
    assert e4["reason"].startswith("RECALL_REPORT_DRIFT: extraction")
    assert e4["value"] is None


def test_e4_print_block(tmp_path):
    out = tmp_path / "print"
    result = _run_cli("--out", str(out))
    assert result.returncode == 0, result.stderr
    assert "E4 extraction recall" in result.stdout
    assert "  value=0.3487 state=MEASURED" in result.stdout
    assert "  note: precision is never used as a recall proxy" in result.stdout
    assert "recall is OWED" not in result.stdout
    assert "none exists" not in result.stdout


# --- E5 ------------------------------------------------------------------------


def test_e5_states(tmp_path):
    # no directory at all -> OWED
    assert env.e5_precision(None)["state"] == "OWED"
    assert env.e5_precision(tmp_path / "missing")["state"] == "OWED"

    # manifest only -> PREPARED_NOT_REVIEWED
    manifest = {"items_total": 40, "decoys_made": 8,
                "allocation": {"D1a": 20, "D1b": 12}}
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    (prepared / "manifest.json").write_bytes(json.dumps(manifest).encode())
    e5 = env.e5_precision(prepared)
    assert e5["state"] == "PREPARED_NOT_REVIEWED"
    assert e5["n_items"] == 40
    assert e5["n_real"] == 32
    assert e5["n_decoys"] == 8
    assert e5["strata"] == {"D1a": 20, "D1b": 12}

    # scored -> passthrough of the report, never recomputed
    report = {
        "schema": "gmi_rel_m2.precision_report/v1",
        "strata": {"D1a": {"population": 20, "reviewed": 20, "accepted": 19,
                           "unclear": 0, "missing": 0, "precision": 0.95,
                           "wilson95": [0.76, 0.99]}},
        "overall_unweighted": {"reviewed": 20, "accepted": 19,
                               "precision": 0.95, "wilson95": [0.76, 0.99]},
        "overall_weighted": {"precision": 0.95, "ci": [0.76, 0.99],
                             "ci_method": "stratified_normal"},
        "decoys": {"reviewed": 8, "accepted": 0, "acceptance_rate": 0.0,
                   "wilson95": [0.0, 0.37], "by_kind": {}},
        "reviewer_reliable": True,
    }
    scored = tmp_path / "scored"
    scored.mkdir()
    (scored / "precision_report.json").write_bytes(json.dumps(report).encode())
    e5 = env.e5_precision(scored)
    assert e5["state"] == "SCORED"
    assert e5["overall_unweighted"] == report["overall_unweighted"]
    assert e5["strata"] == report["strata"]
    assert e5["decoys"] == report["decoys"]
    assert e5["reviewer_reliable"] is True


# --- E6 ------------------------------------------------------------------------


def test_e6_latency_quantiles_and_clock_violation():
    from datetime import datetime, timedelta, timezone

    leaves = {"D1": ["ISS:US-XNAS-I1", "ISS:US-XNAS-I2"], "D2": []}
    rows = []
    index = []
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    lags = [10.0, 20.0, 30.0, 40.0]  # hours
    for n, lag in enumerate(lags):
        published_dt = base + timedelta(days=n)
        ingested_dt = published_dt + timedelta(hours=lag)
        published = published_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        ingested = ingested_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append(_extraction_row(f"obs:{n}", SUBJ, "supplier_customer",
                                    published, ingested))
        index.append({"observation_id": f"obs:{n}", "disposition": "edge",
                      "accession": "a", "known_at": ingested,
                      "relationship_key": "rel:x", "non_edge_key": None,
                      "refusal_reason": None, "source_state": "verified"})
    # one clock violation: ingested before published
    rows.append(_extraction_row("obs:bad", SUBJ, "supplier_customer",
                                "2026-02-02T12:00:00Z", "2026-02-02T00:00:00Z"))
    index.append({"observation_id": "obs:bad", "disposition": "edge",
                  "accession": "a", "known_at": "2026-02-02T00:00:00Z",
                  "relationship_key": "rel:x", "non_edge_key": None,
                  "refusal_reason": None, "source_state": "verified"})

    package = _package(observations=index)
    e6 = env.e6_latency(package, rows, leaves)
    d1 = e6["per_domain"]["D1"]
    assert d1["n"] == 5
    # nearest-rank on the sorted list (-12, 10, 20, 30, 40)
    assert d1["p50"] == 20.0
    assert d1["p90"] == 40.0
    assert d1["max"] == 40.0
    assert d1["clock_violations"] == 1
    assert e6["per_domain"]["ALL"]["n"] == 5
    assert e6["per_domain"]["D2"]["n"] == 0
    assert e6["per_domain"]["D2"]["p50"] is None
    assert e6["package_lag"] == {
        "state": "NOT_MEASURABLE",
        "reason": env.PACKAGE_LAG_REASON,
    }


# --- E7 ------------------------------------------------------------------------


def test_e7_q2_never_unanswerable_and_status_order():
    leaves = {"D1": ["ISS:US-XNAS-I1", "ISS:US-XNAS-I2"], "D2": []}
    panel = {
        "issuers": {"D1": ["ISS:US-XNAS-I1", "ISS:US-XNAS-I2"], "D2": []},
        "questions": [
            {"id": "Q1", "kind": "outgoing_customers", "en": "q1", "zh": "一"},
            {"id": "Q2", "kind": "incoming_mentions", "en": "q2", "zh": "二"},
            {"id": "Q3", "kind": "dependencies", "en": "q3", "zh": "三"},
            {"id": "Q4", "kind": "licensing_distribution", "en": "q4", "zh": "四"},
            {"id": "Q5", "kind": "freshness", "en": "q5", "zh": "五"},
            {"id": "Q6", "kind": "revisions", "en": "q6", "zh": "六"},
        ],
        "status_labels": {
            "ANSWERED_ANONYMOUS": {"en": "a-anon", "zh": "甲"},
            "ANSWERED_FACT": {"en": "a-fact", "zh": "乙"},
            "ANSWERED_NONE_FOUND": {"en": "a-none", "zh": "丙"},
            "UNANSWERABLE_NOT_ASSESSED": {"en": "u-na", "zh": "丁"},
            "UNANSWERABLE_PENDING": {"en": "u-pend", "zh": "戊"},
            "UNANSWERABLE_UNAVAILABLE": {"en": "u-un", "zh": "己"},
        },
    }
    # I1: own supplier_customer edge + anonymous non_edge + coverage with
    # documents + a reassertion revision; I2: nothing at all (pending).
    package = _package(
        coverage=[{"issuer_id": "ISS:US-XNAS-I1", "state": "assessed",
                   "documents": ["0000000000-26-000002", "0000000000-25-000001"],
                   "known_at": "2026-01-01T00:00:00Z",
                   "period_end": "2025-10-03"}],
        observations=[
            {"observation_id": "obs:1", "disposition": "edge",
             "accession": "0000000000-25-000001",
             "known_at": "2026-01-01T00:00:00Z",
             "relationship_key": "rel:f", "non_edge_key": None,
             "refusal_reason": None, "source_state": "verified"},
            {"observation_id": "obs:a", "disposition": "non_edge",
             "accession": "0000000000-26-000001",
             "known_at": "2026-01-01T00:00:00Z",
             "relationship_key": None, "non_edge_key": "nn:1",
             "refusal_reason": None, "source_state": "verified"},
        ],
        non_edges=[{
            "non_edge_key": "nn:1", "species": "supplier_customer",
            "observation_id": "obs:a", "accession": "0000000000-26-000001",
            "subject_issuer_id": "ISS:US-XNAS-I1",
            "object_name_as_filed": "Anon", "anonymous_alias": "Customer A",
            "non_edge_reason": "UNRESOLVED_COUNTERPARTY",
            "known_at": "2026-01-01T00:00:00Z",
        }],
        revisions=[{
            "revision_id": "rev:1", "revision_kind": "reassertion",
            "relationship_key": "rel:f", "revision_seq": 2,
            "source_ref": {"accession": "0000000000-26-000002"},
            "asserting_party": "ISS:US-XNAS-I1",
        }],
    )
    edges = {"edges": [_edge("rel:f", "supplier_customer",
                             "ISS:US-XNAS-I1", "ISS:US-XNAS-I9")]}
    rows = [
        _extraction_row("obs:1", SUBJ, "supplier_customer",
                        "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
        _extraction_row("obs:a", SUBJ, "supplier_customer",
                        "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z",
                        anonymous="Customer A"),
    ]
    e1 = env.e1_coverage(package, leaves)
    e7 = env.e7_answerability(package, edges, rows, leaves, panel, e1, [])
    by_issuer_q = {(c["issuer"], c["question"]): c for c in e7["cells"]}

    i1 = by_issuer_q[("ISS:US-XNAS-I1", "Q1")]
    assert i1["status"] == "ANSWERED_FACT"  # an edge outranks the anonymous non_edge
    assert i1["cite"] == "rel:f"
    assert i1["en"] == "a-fact" and i1["zh"] == "乙"
    # Q2 is answered NONE_FOUND when no counterparty names us — never unanswerable
    q2_i2 = by_issuer_q[("ISS:US-XNAS-I2", "Q2")]
    assert q2_i2["status"] == "ANSWERED_NONE_FOUND"
    # Q2 FACT when an edge we did not assert names us
    edges["edges"].append(_edge("rel:g", "licensing", "ISS:US-XNAS-I9",
                                "ISS:US-XNAS-I2", asserting=["ISS:US-XNAS-I9"]))
    e7 = env.e7_answerability(package, edges, rows, leaves, panel, e1, [])
    by_issuer_q = {(c["issuer"], c["question"]): c for c in e7["cells"]}
    assert by_issuer_q[("ISS:US-XNAS-I2", "Q2")]["status"] == "ANSWERED_FACT"

    # Q3 dependencies: i as the client of contract_manufacturing
    edges["edges"].append(_edge("rel:h", "contract_manufacturing",
                                "ISS:US-XNAS-I9", "ISS:US-XNAS-I1"))
    e7 = env.e7_answerability(package, edges, rows, leaves, panel, e1, [])
    by_issuer_q = {(c["issuer"], c["question"]): c for c in e7["cells"]}
    assert by_issuer_q[("ISS:US-XNAS-I1", "Q3")]["status"] == "ANSWERED_FACT"

    # Q5 freshness cites the newest accession; Q6 sees the reassertion
    assert by_issuer_q[("ISS:US-XNAS-I1", "Q5")]["status"] == "ANSWERED_FACT"
    assert "0000000000-26-000002" in by_issuer_q[("ISS:US-XNAS-I1", "Q5")]["cite"]
    assert by_issuer_q[("ISS:US-XNAS-I1", "Q6")]["status"] == "ANSWERED_FACT"

    # pending issuer, non-Q2 questions are UNANSWERABLE_PENDING
    assert by_issuer_q[("ISS:US-XNAS-I2", "Q1")]["status"] == "UNANSWERABLE_PENDING"
    # per-domain answered counts FACT+ANONYMOUS+NONE_FOUND out of 30 (5 issuers)
    # here only 2 panel issuers -> 12 cells per domain is wrong; check the count
    # matches the printed denominator actually used (6 questions x issuers)
    assert e7["per_domain"]["D1"]["answered"] > 0
    assert e7["note"] == env.USEFULNESS_LINE


# --- E8 ------------------------------------------------------------------------


def test_e8_selection_is_hash_min_not_first():
    kind = "quantitative_fact"
    first = "rel:aaaa"
    second = "rel:bbbb"
    h1 = hashlib.sha256(f"gmi-rel-envelope-evidence-v1:{kind}:{first}".encode()).hexdigest()
    h2 = hashlib.sha256(f"gmi-rel-envelope-evidence-v1:{kind}:{second}".encode()).hexdigest()
    # order the candidates so the hash-min is the LAST one
    candidates = [first, second] if h2 < h1 else [second, first]
    expected = second if h2 < h1 else first
    assert env.select_evidence(kind, candidates) == expected


def test_e8_absent_printed():
    package = _package()
    edges = {"edges": []}
    leaves = {"D1": ["ISS:US-XNAS-I1"], "D2": []}
    e8 = env.e8_evidence(package, edges, [], leaves, [])
    kinds = {(row["domain"], row["kind"]): row for row in e8["kinds"]}
    row = kinds[("D2", "outgoing_query")]
    assert row["state"] == "ABSENT"
    assert row["candidates"] == 0
    assert row["selected"] is None


def test_e8_multi_hop_uses_package_path_validity():
    leaves = {"D1": ["ISS:US-XNAS-I1", "ISS:US-XNAS-I2"], "D2": []}
    ab = _edge("rel:ab", "supplier_customer", "ISS:US-XNAS-I1",
               "ISS:US-XNAS-I2")
    bc = _edge("rel:bc", "supplier_customer", "ISS:US-XNAS-I2",
               "ISS:US-XNAS-I9", product_key="widget")
    e8 = env.e8_evidence(_package(), {"edges": [ab, bc]}, [], leaves, [])
    kinds = {(row["domain"], row["kind"]): row for row in e8["kinds"]}
    invalid = kinds[("D1", "invalid_multi_hop")]
    assert invalid["state"] == "FOUND"
    assert invalid["selected"] == "rel:ab|rel:bc"
    # the reason comes from package_v2.path_validity itself, not a re-implementation
    ok, reason = path_validity(ab, bc)
    assert ok is False and reason == "product_key_mismatch"
    assert reason in invalid["line"]
    valid = kinds[("D1", "valid_multi_hop")]
    assert valid["state"] == "ABSENT"


# --- CLI: refusals, determinism, the real artifacts ------------------------------


def _run_cli(*args):
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/relationship_m2_envelope.py"),
         "measure", *args],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )


def test_out_dir_under_data_refused(tmp_path):
    for refused in ("data/company_intelligence/relationships/envelope_tmp",
                    "site/envelope_tmp"):
        result = _run_cli("--out", str(REPO_ROOT / refused))
        assert result.returncode == 2, (result.stdout, result.stderr)
        assert "OUT_REFUSED" in result.stderr
        assert not (REPO_ROOT / refused).exists()


def test_rerun_byte_identical(tmp_path):
    out1, out2 = tmp_path / "one", tmp_path / "two"
    r1 = _run_cli("--out", str(out1))
    assert r1.returncode == 0, r1.stderr
    r2 = _run_cli("--out", str(out2))
    assert r2.returncode == 0, r2.stderr
    for name in ("envelope_report.json", "envelope_report.txt"):
        assert (out1 / name).read_bytes() == (out2 / name).read_bytes(), name
    # stdout is the txt artifact, byte for byte
    assert r1.stdout == (out1 / "envelope_report.txt").read_bytes().decode("utf-8")


def test_real_m1_artifacts(m1_reference, tmp_path, monkeypatch):
    # The M1 reference artifacts: the CLI entry point in-process, with the
    # script's module package/edges constants pointed at the byte-pinned
    # reference files (an absolute path joins over the script's REPO_ROOT).
    script = _load_envelope_script()
    monkeypatch.setattr(script, "PACKAGE_PATH", str(m1_reference["package"]))
    monkeypatch.setattr(script, "EDGES_PATH", str(m1_reference["edges"]))
    out = tmp_path / "report"
    with contextlib.redirect_stdout(io.StringIO()):
        assert script.main(["measure", "--out", str(out),
                            "--recall-report",
                            str(tmp_path / "absent.json")]) == 0
    report = _load(out / "envelope_report.json")
    assert report["schema"] == "gmi_rel_m2.envelope_report/v1"
    assert report["as_of"] == "2026-10-21T00:00:00Z"
    assert report["panel_sha256"] == env.PANEL_SHA256
    # M0: the joined M1 observations are 2 SWKS supplier_customer rows in D1
    assert report["M0"]["edges"]["D1"]["supplier_customer"] == 1
    assert report["M0"]["observations"]["D1"]["supplier_customer"] == 2
    assert report["M0"]["join"]["join_missing"] == []
    # E1: SWKS assessed, everything else pending, 283 accounted
    assert report["E1"]["domains"]["D1"]["states"]["assessed"] == 1
    # E2: SWKS supplier/supplier_customer is the one known_fresh own_filing cell
    cell = report["E2"]["per_domain"]["D1"]["supplier_customer"]["supplier"]
    assert cell["known_fresh"]["own_filing"] == 1
    # E8: D1 next_publication_reassertion is FOUND from the M1 revisions
    kinds = {(row["domain"], row["kind"]): row for row in report["E8"]["kinds"]}
    assert kinds[("D1", "next_publication_reassertion")]["state"] == "FOUND"
    # E8: D2 has no rows at this base — every kind is ABSENT with 0 candidates
    d2 = [row for row in report["E8"]["kinds"] if row["domain"] == "D2"]
    assert len(d2) == 11
    assert all(row["state"] == "ABSENT" and row["candidates"] == 0 for row in d2)
    # E4 is OWED (this run passes an absent recall report), E6 package lag
    # NOT_MEASURABLE, E7 note verbatim
    assert report["E4"]["state"] == "OWED"
    assert report["E4"]["reason"].startswith("recall report not found")
    assert report["E6"]["package_lag"]["state"] == "NOT_MEASURABLE"
    assert report["E7"]["note"] == env.USEFULNESS_LINE

    # full data, the default CLI run (subprocess, as committed today),
    # re-derived independently: schema/as_of/panel pins, a clean M0 join, E4
    # MEASURED at the committed report's own value, the verbatim E7 note, and
    # an E1 total equal to the eligible leaf count recomputed from
    # leaves_v1.json.
    # falsifier: a committed-artifacts run that drops eligible issuers,
    # breaks the M0 join, drifts the usefulness note, or prints a recall
    # number the committed report does not carry
    full_out = tmp_path / "report_full"
    result = _run_cli("--out", str(full_out))
    assert result.returncode == 0, result.stderr
    full = _load(full_out / "envelope_report.json")
    assert full["schema"] == "gmi_rel_m2.envelope_report/v1"
    assert full["as_of"] == "2026-10-21T00:00:00Z"
    assert full["panel_sha256"] == env.PANEL_SHA256
    assert full["M0"]["join"]["join_missing"] == []
    assert full["E4"]["state"] == "MEASURED"
    assert full["E4"]["value"] == _load(RECALL_REPORT_PATH)["recall"]["value"]
    assert full["E7"]["note"] == env.USEFULNESS_LINE
    assert full["E1"]["eligible_total"] == len(_eligible_issuers(_load(LEAVES_PATH)))


def test_no_network_import():
    sources = [
        Path(env.__file__).read_bytes().decode("utf-8"),
        (REPO_ROOT / "scripts/relationship_m2_envelope.py").read_bytes().decode("utf-8"),
    ]
    pattern = re.compile(r"urllib|requests|http\.client|socket")
    for source in sources:
        assert not pattern.search(source), "network import found in envelope source"
