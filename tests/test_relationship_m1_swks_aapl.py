"""M1 materialized record: one real supplier->customer edge (SWKS->AAPL, 10-K).

Pins the committed SWKS->AAPL record end to end: recomputed identity formulas,
offline excerpt verification, the exact edge, its revisions and correction
lineage, the 2025-06-30 point-in-time replay, producer behavior (determinism,
naive as-of refusal, fail-open on missing input), and byte equality between the
committed data files and a fresh producer run.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import package_v2 as pv2  # noqa: E402
from engine.company_intelligence.relationships import replay  # noqa: E402

EXTRACTION_REL = (
    "research/theme_graph/gmi_relationships_20261021/extraction/swks_aapl_m1.jsonl"
)
SOURCES_REL = "research/theme_graph/gmi_relationships_20261021/sources"
MANIFEST_REL = "research/theme_graph/coverage_20261019/UNIVERSE_MANIFEST.json"
EXTRACTION_PATH = REPO_ROOT / EXTRACTION_REL
SOURCES_DIR = REPO_ROOT / SOURCES_REL
MANIFEST_PATH = REPO_ROOT / MANIFEST_REL
ACC_24 = "0000004127-24-000131"
ACC_25 = "0000004127-25-000085"
ACC_26 = "0000004127-26-000003"
SWKS = "ISS:US-XNAS-SWKS"
AAPL = "ISS:US-XNAS-AAPL"
AS_OF = "2026-10-21T00:00:00Z"

pytestmark = pytest.mark.data_gate


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run_producer(*args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["TZ"] = "UTC"
    return subprocess.run(
        [sys.executable, "scripts/build_relationship_observations.py", *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module")
def m1_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("m1_out")
    proc = _run_producer("--as-of", AS_OF, "--out-dir", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    package = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    edges = json.loads((out / "relationship_edges.json").read_text("utf-8"))
    return {
        "out": out,
        "stdout": proc.stdout,
        "package": package,
        "edges": edges,
        "package_bytes": (out / "observation_package.v2.json").read_bytes(),
        "edges_bytes": (out / "relationship_edges.json").read_bytes(),
    }


@pytest.fixture(scope="module")
def pit_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("pit_out")
    proc = _run_producer("--as-of", "2025-06-30T00:00:00Z", "--out-dir", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    edges = json.loads((out / "relationship_edges.json").read_text("utf-8"))
    package = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    return {"out": out, "stdout": proc.stdout, "edges": edges, "package": package}


def _load_rows() -> list[dict]:
    return [
        json.loads(line)
        for line in EXTRACTION_PATH.read_text("utf-8").splitlines()
        if line.strip()
    ]


def _m1_edge(m1_run) -> dict:
    edges = m1_run["edges"]["edges"]
    assert len(edges) == 1
    return edges[0]


def _unknown_rights() -> dict:
    """The A7 default: a ruling binds nothing, so nothing is granted."""
    return {
        "source_class": "SEC_PUBLIC_ACCESS",
        "purpose_permitted": ["private_api", "research"],
        "public_display": "unknown",
        "excerpt_display": "unknown",
        "magnitude_display": "unknown",
        "ruling_ref": None,
    }


def _valid_ruling() -> dict:
    """A synthetic Chairman rights ruling with the exact binding shape (A7).

    Built in tmp_path only — a ruling is a Chairman artifact and is never
    committed under research/ or data/.
    """
    return {
        "schema": "company_intelligence.source_purpose_ruling/v1",
        "ruling_id": "GMI-REL-TEST-0001",
        "decision_owner": "Chairman Chris",
        "evidence_kind": "direct_chairman_source_rights_confirmation",
        "source": {"source_class": "SEC_PUBLIC_ACCESS"},
        "permitted_use": {
            "citation_required": True,
            "derived_fact_public_display": True,
            "magnitude_display": False,
            "verbatim_excerpt_display": "entitled_only",
            "excerpt_max_raw_bytes": 2048,
        },
    }


def _write_ruling(path: Path, ruling: dict) -> bytes:
    raw = json.dumps(ruling, indent=1, sort_keys=True).encode("utf-8")
    path.write_bytes(raw)
    return raw


def _has_warning(stdout: str, title: str) -> bool:
    return any(line.startswith(f"::warning title={title}") for line in stdout.splitlines())


def test_recomputed_ids_equal_committed():
    rows = _load_rows()
    assert len(rows) == 4
    for row in rows:
        source = row.get("source_ref") or {}
        if row["row_kind"] == "observation":
            expect = "obs:" + _sha_text(
                pv2.canon(
                    [
                        source["accession"],
                        source["byte_start"],
                        source["byte_end"],
                        row["species"],
                        row["subject"]["issuer_id"],
                        row["object"]["issuer_id"],
                    ]
                )
            )[:20]
            assert expect == row["observation_id"]
        elif row["row_kind"] == "document_assessment":
            expect = "asm:" + _sha_text(
                pv2.canon(
                    [
                        source["accession"],
                        source["byte_start"],
                        source["byte_end"],
                        row["assessment"],
                    ]
                )
            )[:20]
            assert expect == row["assessment_id"]
    rel_key = "rel:" + _sha_text(
        pv2.canon(["supplier_customer", SWKS, AAPL, "all"])
    )[:20]
    assert rel_key == _m1_edge_from_producer()["relationship_key"]


def _m1_edge_from_producer() -> dict:
    out = REPO_ROOT / "data/company_intelligence/relationships"
    committed = out / "relationship_edges.json"
    if committed.exists():
        edges = json.loads(committed.read_text("utf-8"))["edges"]
        if len(edges) == 1:
            return edges[0]
    # Fall back to an in-process build when the committed record is absent.
    excerpts = {
        acc: json.loads((SOURCES_DIR / f"{acc}.json").read_text("utf-8"))
        for acc in (ACC_24, ACC_25, ACC_26)
    }
    manifest_version, issuers = pv2.load_manifest_issuers(MANIFEST_PATH)
    inputs = [
        {"path": EXTRACTION_REL, "sha256": _sha_bytes(EXTRACTION_PATH.read_bytes())},
        {"path": MANIFEST_REL, "sha256": _sha_bytes(MANIFEST_PATH.read_bytes())},
    ]
    package, edges_doc = pv2.build_package(
        _load_rows(), excerpts, issuers, AS_OF, manifest_version, inputs
    )
    assert len(edges_doc["edges"]) == 1
    return edges_doc["edges"][0]


def test_excerpts_verify_offline():
    for acc in (ACC_24, ACC_25, ACC_26):
        excerpt = json.loads((SOURCES_DIR / f"{acc}.json").read_text("utf-8"))
        assert replay.verify_excerpt(excerpt) == [], acc


def test_m1_edge_exact(m1_run):
    edge = _m1_edge(m1_run)
    assert edge["species"] == "supplier_customer"
    assert edge["direction"] == {
        "from_issuer_id": SWKS,
        "to_issuer_id": AAPL,
        "from_role": "supplier",
        "to_role": "customer",
    }
    assert edge["from"] == {
        "issuer_id": SWKS,
        "security_ids": ["SEC:US-XNAS-SWKS"],
    }
    assert edge["to"] == {"issuer_id": AAPL, "security_ids": ["SEC:US-XNAS-AAPL"]}
    assert edge["scope"] == {"product_key": "all", "segment": None, "geography": None}
    assert edge["theme_graph_mapping"] == "SUPPLIES"
    assert edge["relation_status"] == "asserted"
    assert edge["admission_state"] == "proposed"
    assert edge["asserting_parties"] == [SWKS]
    assert edge["first_known_at"] == "2024-11-15T21:37:43Z"
    assert edge["last_asserted_at"] == "2025-11-07T21:08:12Z"
    assert edge["last_assessed_at"] == "2026-01-30T21:06:48Z"
    assert edge["freshness_state"] == "fresh"
    assert edge["magnitude_state"] == "disclosed"
    assert edge["asserted_period"] == {"start": "2021-10-02", "end": "2025-10-03"}
    assert edge["rights"] == _unknown_rights()
    assert edge["conditions"] == []
    assert edge["source_refs"] == [
        {
            "observation_id": "obs:aafd6fdeb1ee9043d452",
            "accession": ACC_24,
            "form": "10-K",
            "url": (
                "https://www.sec.gov/Archives/edgar/data/4127/"
                "000000412724000131/swks-20240927.htm"
            ),
            "byte_start": 1396889,
            "byte_end": 1397687,
            "span_sha256": (
                "396a24d2ca9c4f82699f7b30d61289d45d9e3301c5ad313bb90a82d5b6c193fa"
            ),
            "excerpt_path": f"{SOURCES_REL}/{ACC_24}.json",
        },
        {
            "observation_id": "obs:ac5a91d2e47760c66b4b",
            "accession": ACC_25,
            "form": "10-K",
            "url": (
                "https://www.sec.gov/Archives/edgar/data/4127/"
                "000000412725000085/swks-20251003.htm"
            ),
            "byte_start": 1500407,
            "byte_end": 1501205,
            "span_sha256": (
                "c8fedadd764727f63dc239ad99530ffa5b2f1cf1f0a6a7dada29854c88fb7aeb"
            ),
            "excerpt_path": f"{SOURCES_REL}/{ACC_25}.json",
        },
    ]
    assert edge["conflicts"] == []
    assert m1_run["edges"]["non_edges"] == []
    assert m1_run["edges"]["as_of"] == AS_OF
    assert m1_run["edges"]["adoption_state"] == "proposed"
    assert m1_run["edges"]["package_id"] == m1_run["package"]["package_id"]
    package_sha = _sha_bytes(m1_run["package_bytes"])
    assert m1_run["edges"]["package_sha256"] == package_sha


def test_m1_revisions_and_current(m1_run):
    edge = _m1_edge(m1_run)
    history = edge["magnitude_history"]
    assert len(history) == 6
    seen = [
        (rev["period"]["label"], rev["value"], rev["revision_seq"], rev["revision_kind"])
        for rev in history
    ]
    assert seen == [
        ("FY2022", 0.58, 1, "new_period"),
        ("FY2023", 0.66, 1, "new_period"),
        ("FY2023", 0.66, 2, "reassertion"),
        ("FY2024", 0.69, 1, "new_period"),
        ("FY2024", 0.69, 2, "reassertion"),
        ("FY2025", 0.67, 1, "new_period"),
    ]
    for rev in history:
        assert rev["kind"] == "seller_revenue_share"
        assert rev["unit"] == "ratio"
        assert rev["relationship_key"] == edge["relationship_key"]
        assert rev["asserting_party"] == SWKS
    seq2_revs = [rev for rev in history if rev["revision_seq"] == 2]
    for rev in seq2_revs:
        prev = next(r for r in history if r["revision_id"] == rev["supersedes"])
        assert prev["revision_seq"] == 1
        assert prev["period"] == rev["period"]
        assert prev["value"] == rev["value"]
    # The revision id formula is bound to the relationship key and sequence.
    rev = history[0]
    expect = "rev:" + _sha_text(
        pv2.canon(
            [
                edge["relationship_key"],
                rev["kind"],
                rev["period"]["start"],
                rev["period"]["end"],
                rev["asserting_party"],
                rev["revision_seq"],
            ]
        )
    )[:20]
    assert expect == rev["revision_id"]
    current = edge["current_magnitudes"]
    assert len(current) == 1
    assert current[0]["period"]["label"] == "FY2025"
    assert current[0]["value"] == 0.67
    assert current[0]["period"] == {
        "start": "2024-09-28",
        "end": "2025-10-03",
        "label": "FY2025",
    }
    assert [rev["revision_id"] for rev in current] == [
        rev["revision_id"]
        for rev in history
        if rev["period"]["label"] == "FY2025"
    ]


def test_m1_correction_lineage_not_restated(m1_run):
    edge = _m1_edge(m1_run)
    assert edge["correction_lineage"] == [
        {
            "assessment_id": "asm:e45f8c5527e4f3586ca7",
            "accession": ACC_26,
            "amends_accession": ACC_25,
            "assessment": "not_restated",
            "reason": "part_iii_only_amendment",
            "known_at": "2026-01-30T21:06:48Z",
            "effect": "none",
        }
    ]
    assert edge["relation_status"] == "asserted"


def test_m1_pit_2025_06_30(pit_run):
    edges = pit_run["edges"]["edges"]
    assert len(edges) == 1
    edge = edges[0]
    seen = [
        (rev["period"]["label"], rev["value"], rev["revision_seq"])
        for rev in edge["magnitude_history"]
    ]
    assert seen == [("FY2022", 0.58, 1), ("FY2023", 0.66, 1), ("FY2024", 0.69, 1)]
    current = edge["current_magnitudes"]
    assert len(current) == 1 and current[0]["value"] == 0.69
    assert current[0]["period"]["label"] == "FY2024"
    assert edge["correction_lineage"] == []
    assert edge["last_assessed_at"] == "2024-11-15T21:37:43Z"
    assert edge["last_asserted_at"] == "2024-11-15T21:37:43Z"
    assert edge["freshness_state"] == "fresh"
    coverage = pit_run["edges"]["coverage"]
    assert len(coverage) == 1
    assert coverage[0]["issuer_id"] == SWKS
    assert coverage[0]["state"] == "not_assessed"
    assert coverage[0]["known_at"] is None
    assert pit_run["package"]["counts"]["assessments"] == 0
    # Rows published after the as_of leave no trace anywhere.
    blob = json.dumps(pit_run["edges"]) + json.dumps(pit_run["package"])
    assert "2025-11-07" not in blob
    assert "obs:ac5a91d2e47760c66b4b" not in blob
    assert "asm:e45f8c5527e4f3586ca7" not in blob


def test_outputs_conform_to_contracts(m1_run):
    import jsonschema

    package_schema = json.loads(
        (
            REPO_ROOT
            / "contracts/company_intelligence/relationship_observation_package.v2.schema.json"
        ).read_text("utf-8")
    )
    edges_schema = json.loads(
        (
            REPO_ROOT
            / "contracts/company_intelligence/relationship_edges.v1.schema.json"
        ).read_text("utf-8")
    )
    jsonschema.validate(m1_run["package"], package_schema)
    jsonschema.validate(m1_run["edges"], edges_schema)


def test_producer_deterministic(tmp_path):
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    proc_a = _run_producer("--as-of", AS_OF, "--out-dir", str(out_a))
    proc_b = _run_producer("--as-of", AS_OF, "--out-dir", str(out_b))
    assert proc_a.returncode == 0 and proc_b.returncode == 0
    assert proc_a.stdout == proc_b.stdout
    for name in ("observation_package.v2.json", "relationship_edges.json"):
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes(), name


def test_producer_rejects_naive_as_of():
    proc = _run_producer("--as-of", "2026-10-21", "--out-dir", "/tmp/rel_naive_reject")
    assert proc.returncode == 2
    assert "as-of" in (proc.stdout + proc.stderr).lower()


def test_missing_extraction_fails_open(tmp_path):
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of",
        AS_OF,
        "--extraction",
        str(tmp_path / "missing.jsonl"),
        "--out-dir",
        str(out),
    )
    assert proc.returncode == 0
    assert proc.stdout.startswith("::warning ")
    assert "relationship-input-missing" in proc.stdout.splitlines()[0]
    assert not out.exists() or not any(out.iterdir())


def test_replay_fetch_synthetic():
    excerpt = json.loads((SOURCES_DIR / f"{ACC_26}.json").read_text("utf-8"))
    span = excerpt["span"]
    doc = (
        b"<html>head-pad"
        + span["raw"].encode("utf-8")
        + b"tail-pad</html>"
    )
    start = 14
    end = start + len(span["raw"].encode("utf-8"))
    good = dict(excerpt)
    good["doc_byte_length"] = len(doc)
    good["doc_sha256"] = _sha_bytes(doc)
    good["span"] = dict(span, byte_start=start, byte_end=end)
    assert replay.replay_fetch(good, "test-agent", fetch=lambda url, headers: doc) == []

    tampered = bytearray(doc)
    tampered[start] = tampered[start] ^ 0x01
    tampered_doc = bytes(tampered)
    assert replay.replay_fetch(good, "test-agent", fetch=lambda url, headers: tampered_doc) != []


@pytest.mark.needs_full_checkout("data")
def test_committed_data_equals_fresh_run(tmp_path):
    out = tmp_path / "fresh"
    proc = _run_producer("--as-of", AS_OF, "--out-dir", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for name in ("observation_package.v2.json", "relationship_edges.json"):
        committed = REPO_ROOT / "data/company_intelligence/relationships" / name
        assert committed.exists(), name
        assert committed.read_bytes() == (out / name).read_bytes(), name


def test_producer_quarantines_clock_mismatch(tmp_path):
    rows = []
    shifted = False
    for line in EXTRACTION_PATH.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("row_kind") == "observation" and not shifted:
            moment = datetime.strptime(
                row["published_at"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            row["published_at"] = (moment + timedelta(hours=1)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            shifted = True
        rows.append(json.dumps(row))
    assert shifted
    extraction = tmp_path / "shifted.jsonl"
    extraction.write_text("\n".join(rows) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of", AS_OF, "--extraction", str(extraction), "--out-dir", str(out)
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _has_warning(proc.stdout, "CLOCK_MISMATCH")
    package = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    mismatched = [
        o for o in package["observations"] if o["refusal_reason"] == "clock_mismatch"
    ]
    assert len(mismatched) == 1
    assert mismatched[0]["disposition"] == "quarantined"
    assert package["counts"]["edges"] == 1  # the untouched observation still binds
    strict = _run_producer(
        "--as-of",
        AS_OF,
        "--extraction",
        str(extraction),
        "--out-dir",
        str(tmp_path / "out_strict"),
        "--strict",
    )
    assert strict.returncode == 2


def test_rights_ruling_absent_keeps_unknown(m1_run):
    for edge in m1_run["edges"]["edges"]:
        assert edge["rights"] == _unknown_rights()
    assert m1_run["package"]["rights_ruling_ref"] is None


def test_rights_ruling_synthetic_binds_and_cites(tmp_path):
    import jsonschema

    path = tmp_path / "ruling.json"
    raw = _write_ruling(path, _valid_ruling())
    ref = "GMI-REL-TEST-0001@sha256:" + hashlib.sha256(raw).hexdigest()
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of", AS_OF, "--rights-ruling", str(path), "--out-dir", str(out)
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert not _has_warning(proc.stdout, "RIGHTS_RULING_INVALID")
    edges = json.loads((out / "relationship_edges.json").read_text("utf-8"))
    package = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    assert edges["edges"]
    for edge in edges["edges"]:
        assert edge["rights"] == {
            "source_class": "SEC_PUBLIC_ACCESS",
            "purpose_permitted": ["private_api", "research"],
            "public_display": "derived_facts_permitted",
            "excerpt_display": "entitled_only",
            "magnitude_display": "entitled_only",
            "ruling_ref": ref,
        }
    assert package["rights_ruling_ref"] == ref
    assert {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(raw).hexdigest(),
    } in package["inputs"]
    for name, schema_path in (
        ("observation_package.v2.json", "relationship_observation_package.v2.schema.json"),
        ("relationship_edges.json", "relationship_edges.v1.schema.json"),
    ):
        schema = json.loads(
            (REPO_ROOT / "contracts/company_intelligence" / schema_path).read_text(
                "utf-8"
            )
        )
        jsonschema.validate(json.loads((out / name).read_text("utf-8")), schema)


def _ruling_mutations() -> dict:
    def _mutate(mutator):
        def apply(ruling: dict) -> None:
            mutator(ruling)

        return apply

    return {
        "wrong_owner": _mutate(lambda r: r.update(decision_owner="Sol")),
        "wrong_evidence_kind": _mutate(
            lambda r: r.update(evidence_kind="derived_opinion")
        ),
        "excerpt_bytes_over_limit": _mutate(
            lambda r: r["permitted_use"].update(excerpt_max_raw_bytes=4096)
        ),
        "missing_citation_required": _mutate(
            lambda r: r["permitted_use"].pop("citation_required")
        ),
    }


@pytest.mark.parametrize("mutation", sorted(_ruling_mutations()))
def test_rights_ruling_malformed_fails_open_unknown(tmp_path, mutation):
    ruling = _valid_ruling()
    _ruling_mutations()[mutation](ruling)
    path = tmp_path / "ruling.json"
    _write_ruling(path, ruling)
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of", AS_OF, "--rights-ruling", str(path), "--out-dir", str(out)
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _has_warning(proc.stdout, "RIGHTS_RULING_INVALID")
    edges = json.loads((out / "relationship_edges.json").read_text("utf-8"))
    package = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    assert edges["edges"]
    for edge in edges["edges"]:
        assert edge["rights"] == _unknown_rights()  # never a partial grant
    assert package["rights_ruling_ref"] is None
    strict = _run_producer(
        "--as-of",
        AS_OF,
        "--rights-ruling",
        str(path),
        "--out-dir",
        str(tmp_path / "out_strict"),
        "--strict",
    )
    assert strict.returncode == 2


def test_extraction_directory_input_equals_file_input(tmp_path):
    nested = tmp_path / "d" / "a"
    nested.mkdir(parents=True)
    (nested / "swks.jsonl").write_bytes(EXTRACTION_PATH.read_bytes())
    out_file = tmp_path / "out_file"
    out_dir = tmp_path / "out_dir"
    proc_file = _run_producer("--as-of", AS_OF, "--out-dir", str(out_file))
    proc_dir = _run_producer(
        "--as-of", AS_OF, "--extraction", str(tmp_path / "d"), "--out-dir", str(out_dir)
    )
    assert proc_file.returncode == 0, proc_file.stdout + proc_file.stderr
    assert proc_dir.returncode == 0, proc_dir.stdout + proc_dir.stderr
    edges_file = json.loads((out_file / "relationship_edges.json").read_text("utf-8"))
    edges_dir = json.loads((out_dir / "relationship_edges.json").read_text("utf-8"))
    assert edges_dir["edges"] == edges_file["edges"]
    assert edges_dir["non_edges"] == edges_file["non_edges"]
    assert edges_dir["coverage"] == edges_file["coverage"]
    assert edges_dir["counts"] == edges_file["counts"]
    package_file = json.loads(
        (out_file / "observation_package.v2.json").read_text("utf-8")
    )
    package_dir = json.loads(
        (out_dir / "observation_package.v2.json").read_text("utf-8")
    )
    assert package_dir["package_id"] == package_file["package_id"]
    assert package_dir["counts"] == package_file["counts"]


def test_sources_duplicate_conflict_is_source_corrupt(tmp_path):
    original = (SOURCES_DIR / f"{ACC_24}.json").read_bytes()
    # Same parsed JSON, different bytes: only the byte-conflict path can explain
    # a source_corrupt verdict here.
    tampered = original.replace(b"{", b"{ ", 1)
    assert tampered != original
    sources = tmp_path / "sources"
    (sources / "nested" / "deep").mkdir(parents=True)
    (sources / f"{ACC_24}.json").write_bytes(original)
    (sources / "nested" / "deep" / f"{ACC_24}.json").write_bytes(tampered)
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of",
        AS_OF,
        "--sources",
        str(sources),
        "--out-dir",
        str(out),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _has_warning(proc.stdout, "SOURCE_DUPLICATE_CONFLICT")
    package = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    citing = [o for o in package["observations"] if o["accession"] == ACC_24]
    assert citing
    assert all(o["source_state"] == "source_corrupt" for o in citing)
    assert all(o["disposition"] == "quarantined" for o in citing)
