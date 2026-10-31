"""M2 source re-key + identity: (accession, span) excerpt keys, A35 object-label
identity, producer row dedupe, recursive replay.

Pins the accepted M1 byte outputs through the re-key (the two SHA-256 pins), the
two recognized ``--sources`` layouts and their poison/conflict rules, the
two-kind excerpt lookup order, the A35 observation-identity extension for
unresolved objects, producer row dedupe, and replay's recursive excerpt load.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.company_intelligence.relationships import package_v2 as pv2  # noqa: E402
from engine.company_intelligence.relationships import replay  # noqa: E402

EXTRACTION_REL = (
    "research/theme_graph/gmi_relationships_20261021/extraction/swks_aapl_m1.jsonl"
)
EXTRACTION_PATH = REPO_ROOT / EXTRACTION_REL
SOURCES_DIR = REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/sources"
ACC_24 = "0000004127-24-000131"
ACC_25 = "0000004127-25-000085"
ACC_26 = "0000004127-26-000003"
SWKS = "ISS:US-XNAS-SWKS"
AAPL = "ISS:US-XNAS-AAPL"
AS_OF = "2026-10-21T00:00:00Z"
M1_ROW_25 = "obs:ac5a91d2e47760c66b4b"
M1_ASM = "asm:e45f8c5527e4f3586ca7"
EXCERPT_PATH_TEMPLATE = (
    "research/theme_graph/gmi_relationships_20261021/sources/{accession}.json"
)

# The accepted M1 bytes (STEP 0 of the lane packet): the byte-identity oracle
# for the re-key.  A sources root outside the repo records absolute input
# paths, so the file pins bind only to runs over the committed inputs; the
# package identity (hashed from input sha256s only) binds everywhere.
PKG_PIN = "cc67c2f9c065d04f5029c75157eefad19277fde29d2cbda5b2865c0f5d1307bb"
EDGES_PIN = "51434731fb33499e77ece20b9a71a9824cc3a76fa46c0fa5d14a9ccb53f986dd"
PACKAGE_ID_PIN = "pkg:56502f8b52805a61749a"

#: J2 b, verbatim: the extraction contract's x-gmi-identity-rule annotation.
IDENTITY_RULE = {
    "rule_id": "A35",
    "canon": (
        "json.dumps(value, sort_keys=True, separators=(',', ':'), "
        "ensure_ascii=False); sha = sha256 hex of its utf-8 bytes"
    ),
    "observation_id": (
        "'obs:' + sha(canon([accession, byte_start, byte_end, species, "
        "subject_issuer_id, object_issuer_id]))[:20]; when object_issuer_id is "
        "null and object_label is a non-empty string, object_label is appended "
        "as a 7th element"
    ),
    "object_label": "object.anonymous_alias when non-null, else object.name_as_filed",
    "assessment_id": "'asm:' + sha(canon([accession, byte_start, byte_end, assessment]))[:20]",
    "note": (
        "Two unresolved counterparties in one span (e.g. 'Customer A' and "
        "'Customer B') would collide on the 6-element form; the label separates "
        "them. Ids of resolved-object observations are unchanged."
    ),
}

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


def _has_warning(stdout: str, title: str) -> bool:
    return any(
        line.startswith(f"::warning title={title}") for line in stdout.splitlines()
    )


def _excerpt_bytes(acc: str) -> bytes:
    return (SOURCES_DIR / f"{acc}.json").read_bytes()


def _excerpt(acc: str) -> dict:
    return json.loads(_excerpt_bytes(acc).decode("utf-8"))


def _write_json(path: Path, doc: dict) -> None:
    path.write_bytes(
        json.dumps(doc, sort_keys=True, indent=1, ensure_ascii=False).encode("utf-8")
        + b"\n"
    )


def _flat_sources(tmp_path: Path, accs=(ACC_24, ACC_25, ACC_26), name="sources") -> Path:
    """The committed M1 excerpts in the FLAT layout under tmp_path."""
    sources = tmp_path / name
    sources.mkdir()
    for acc in accs:
        (sources / f"{acc}.json").write_bytes(_excerpt_bytes(acc))
    return sources


def _nested_sources(tmp_path: Path, accs=(ACC_24, ACC_25, ACC_26), name="sources") -> Path:
    """The committed M1 excerpts in the NESTED layout under tmp_path."""
    sources = tmp_path / name
    for acc in accs:
        target = sources / acc
        target.mkdir(parents=True)
        (target / f"{_excerpt(acc)['span']['raw_sha256'][:20]}.json").write_bytes(
            _excerpt_bytes(acc)
        )
    return sources


def _sub_span_excerpt(acc: str = ACC_25, start: int = 100, end: int = 500) -> dict:
    """A strict sub-span of the committed span as its own valid excerpt (J1)."""
    doc = _excerpt(acc)
    raw = doc["span"]["raw"].encode("utf-8")
    sub = raw[start:end]
    normalized = pv2.normalize_span(sub)
    new = dict(doc)
    new["span"] = {
        "raw": sub.decode("utf-8"),
        "byte_start": doc["span"]["byte_start"] + start,
        "byte_end": doc["span"]["byte_start"] + end,
        "raw_sha256": _sha_bytes(sub),
        "normalized": normalized,
        "normalized_sha256": _sha_text(normalized),
    }
    new["xbrl_contexts"] = []
    return new


def _m1_row(observation_id: str) -> dict:
    return next(
        json.loads(line)
        for line in EXTRACTION_PATH.read_text("utf-8").splitlines()
        if line.strip()
        and json.loads(line).get("observation_id") == observation_id
    )


def _repointed_observation(excerpt: dict, observation_id: str = M1_ROW_25) -> dict:
    """A copy of an M1 observation row re-pointed at `excerpt` (ids recomputed)."""
    row = _m1_row(observation_id)
    span = excerpt["span"]
    source = dict(row["source_ref"])
    source["byte_start"] = span["byte_start"]
    source["byte_end"] = span["byte_end"]
    source["span_sha256"] = span["raw_sha256"]
    source["normalized_span_sha256"] = span["normalized_sha256"]
    row = dict(row, source_ref=source)
    row["observation_id"] = pv2.observation_identity(
        source["accession"],
        source["byte_start"],
        source["byte_end"],
        row["species"],
        row["subject"]["issuer_id"],
        row["object"]["issuer_id"],
    )
    return row


def test_m1_outputs_byte_identical_after_rekey(tmp_path):
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of", AS_OF, "--extraction", str(EXTRACTION_PATH), "--out-dir", str(out)
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _sha_bytes((out / "observation_package.v2.json").read_bytes()) == PKG_PIN
    assert _sha_bytes((out / "relationship_edges.json").read_bytes()) == EDGES_PIN


def _load_producer_module():
    spec = importlib.util.spec_from_file_location(
        "m2_build_relationship_observations",
        REPO_ROOT / "scripts" / "build_relationship_observations.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_default_extraction_is_the_directory(tmp_path):
    module = _load_producer_module()
    assert module.DEFAULT_EXTRACTION.name == "extraction"
    assert module.DEFAULT_EXTRACTION.is_dir()
    out = tmp_path / "out"
    proc = _run_producer("--as-of", AS_OF, "--out-dir", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _sha_bytes((out / "observation_package.v2.json").read_bytes()) == PKG_PIN
    assert _sha_bytes((out / "relationship_edges.json").read_bytes()) == EDGES_PIN


def test_nested_layout_resolves_and_records_excerpt_path(tmp_path):
    sources = _nested_sources(tmp_path)
    base_out = tmp_path / "base"
    nested_out = tmp_path / "nested"
    base_proc = _run_producer(
        "--as-of", AS_OF, "--extraction", str(EXTRACTION_PATH), "--out-dir", str(base_out)
    )
    nested_proc = _run_producer(
        "--as-of",
        AS_OF,
        "--extraction",
        str(EXTRACTION_PATH),
        "--sources",
        str(sources),
        "--out-dir",
        str(nested_out),
    )
    assert base_proc.returncode == 0 and nested_proc.returncode == 0
    base_pkg = json.loads((base_out / "observation_package.v2.json").read_text("utf-8"))
    pkg = json.loads((nested_out / "observation_package.v2.json").read_text("utf-8"))
    edges = json.loads((nested_out / "relationship_edges.json").read_text("utf-8"))
    # Same source states and dispositions as the flat M1 run.
    assert pkg["observations"] == base_pkg["observations"]
    assert pkg["assessments"] == base_pkg["assessments"]
    assert all(o["source_state"] == "verified" for o in pkg["observations"])
    # Every emitted excerpt_path names the nested file, not the template.
    refs = list(edges["edges"][0]["source_refs"])
    refs += [rev["source_ref"] for rev in edges["edges"][0]["magnitude_history"]]
    assert refs
    for ref in refs:
        assert ref["excerpt_path"].endswith(
            f"{ref['accession']}/{ref['span_sha256'][:20]}.json"
        ), ref


def test_two_excerpts_one_accession_resolve_by_span(tmp_path):
    sources = _nested_sources(tmp_path)
    sub = _sub_span_excerpt()
    assert replay.verify_excerpt(sub) == []
    _write_json(sources / ACC_25 / f"{sub['span']['raw_sha256'][:20]}.json", sub)
    extraction = tmp_path / "extraction"
    extraction.mkdir()
    (extraction / "m1.jsonl").write_bytes(EXTRACTION_PATH.read_bytes())
    row = _repointed_observation(sub)
    (extraction / "repointed.jsonl").write_text(
        json.dumps(row) + "\n", encoding="utf-8"
    )
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of",
        AS_OF,
        "--extraction",
        str(extraction),
        "--sources",
        str(sources),
        "--out-dir",
        str(out),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    pkg = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    edges = json.loads((out / "relationship_edges.json").read_text("utf-8"))
    by_id = {o["observation_id"]: o for o in pkg["observations"]}
    assert by_id[M1_ROW_25]["source_state"] == "verified"
    assert by_id[M1_ROW_25]["disposition"] == "edge"
    assert by_id[row["observation_id"]]["source_state"] == "verified"
    assert by_id[row["observation_id"]]["disposition"] == "edge"
    # Each observation resolves to its own excerpt of the shared accession.
    acc25_refs = [
        ref for ref in edges["edges"][0]["source_refs"] if ref["accession"] == ACC_25
    ]
    assert len(acc25_refs) == 2
    assert {ref["span_sha256"] for ref in acc25_refs} == {
        _excerpt(ACC_25)["span"]["raw_sha256"],
        sub["span"]["raw_sha256"],
    }
    for ref in acc25_refs:
        assert ref["excerpt_path"].endswith(
            f"{ACC_25}/{ref['span_sha256'][:20]}.json"
        )
    # The package inputs list both ACC_25 files.
    input_names = [
        entry["path"] for entry in pkg["inputs"] if entry["path"].endswith(".json")
    ]
    acc25_inputs = [p for p in input_names if f"/{ACC_25}/" in p]
    assert sorted(p.rsplit("/", 1)[-1] for p in acc25_inputs) == sorted(
        {
            f"{_excerpt(ACC_25)['span']['raw_sha256'][:20]}.json",
            f"{sub['span']['raw_sha256'][:20]}.json",
        }
    )


@pytest.mark.parametrize(
    "mutation",
    ["accession_field_mismatch", "unparseable_bytes", "missing_raw_sha256"],
)
def test_poisoned_accession_is_source_corrupt(tmp_path, mutation):
    sources = _flat_sources(tmp_path)
    doc = _excerpt(ACC_24)
    if mutation == "accession_field_mismatch":
        doc["accession"] = ACC_25
        _write_json(sources / f"{ACC_24}.json", doc)
    elif mutation == "unparseable_bytes":
        (sources / f"{ACC_24}.json").write_bytes(b"{ definitely not json")
    else:
        del doc["span"]["raw_sha256"]
        _write_json(sources / f"{ACC_24}.json", doc)
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of",
        AS_OF,
        "--extraction",
        str(EXTRACTION_PATH),
        "--sources",
        str(sources),
        "--out-dir",
        str(out),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _has_warning(proc.stdout, "SOURCE_FILE_POISONED")
    pkg = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    citing = [o for o in pkg["observations"] if o["accession"] == ACC_24]
    assert citing
    assert all(o["source_state"] == "source_corrupt" for o in citing)
    assert all(o["disposition"] == "quarantined" for o in citing)
    # The poison is per accession, not global.
    others = [o for o in pkg["observations"] if o["accession"] != ACC_24]
    assert others
    assert all(o["source_state"] == "verified" for o in others)


def test_nested_stem_must_match_raw_sha_prefix(tmp_path):
    sources = _flat_sources(tmp_path, accs=(ACC_25, ACC_26))
    nested = sources / ACC_24
    nested.mkdir()
    (nested / "0123456789abcdef0123.json").write_bytes(_excerpt_bytes(ACC_24))
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of",
        AS_OF,
        "--extraction",
        str(EXTRACTION_PATH),
        "--sources",
        str(sources),
        "--out-dir",
        str(out),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _has_warning(proc.stdout, "SOURCE_PATH_MISMATCH")
    pkg = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    citing = [o for o in pkg["observations"] if o["accession"] == ACC_24]
    assert citing
    assert all(o["source_state"] == "source_corrupt" for o in citing)
    assert all(o["disposition"] == "quarantined" for o in citing)


def test_unreferenced_span_with_multiple_excerpts_is_unavailable(tmp_path):
    sources = _nested_sources(tmp_path)
    sub = _sub_span_excerpt()
    _write_json(sources / ACC_25 / f"{sub['span']['raw_sha256'][:20]}.json", sub)
    # A row citing a THIRD span hash that no file under --sources pins.
    row = _repointed_observation(sub)
    source = dict(row["source_ref"])
    source["byte_start"] = sub["span"]["byte_start"] + 10
    source["byte_end"] = sub["span"]["byte_end"]
    source["span_sha256"] = "e" * 64
    source["normalized_span_sha256"] = "f" * 64
    row = dict(row, source_ref=source)
    row["observation_id"] = pv2.observation_identity(
        source["accession"],
        source["byte_start"],
        source["byte_end"],
        row["species"],
        row["subject"]["issuer_id"],
        row["object"]["issuer_id"],
    )
    extraction = tmp_path / "third.jsonl"
    extraction.write_text(json.dumps(row) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of",
        AS_OF,
        "--extraction",
        str(extraction),
        "--sources",
        str(sources),
        "--out-dir",
        str(out),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    pkg = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    obs = {o["observation_id"]: o for o in pkg["observations"]}
    assert obs[row["observation_id"]]["source_state"] == "source_unavailable"
    assert obs[row["observation_id"]]["disposition"] == "quarantined"


def test_nested_duplicate_conflict_is_source_corrupt(tmp_path):
    sources = _nested_sources(tmp_path, accs=(ACC_25, ACC_26))
    original = _excerpt_bytes(ACC_24)
    tampered = original.replace(b"{", b"{ ", 1)
    assert tampered != original
    sha20 = _excerpt(ACC_24)["span"]["raw_sha256"][:20]
    (sources / ACC_24).mkdir()
    (sources / ACC_24 / f"{sha20}.json").write_bytes(original)
    deep = sources / "deep" / ACC_24
    deep.mkdir(parents=True)
    (deep / f"{sha20}.json").write_bytes(tampered)
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of",
        AS_OF,
        "--extraction",
        str(EXTRACTION_PATH),
        "--sources",
        str(sources),
        "--out-dir",
        str(out),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _has_warning(proc.stdout, "SOURCE_DUPLICATE_CONFLICT")
    pkg = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    citing = [o for o in pkg["observations"] if o["accession"] == ACC_24]
    assert citing
    assert all(o["source_state"] == "source_corrupt" for o in citing)
    assert all(o["disposition"] == "quarantined" for o in citing)
    conflicted = [
        entry["path"]
        for entry in pkg["inputs"]
        if entry["path"].endswith(f"{ACC_24}/{sha20}.json")
    ]
    assert len(conflicted) == 2


def test_flat_and_nested_identical_bytes_use_flat_path(tmp_path):
    sources = _nested_sources(tmp_path, accs=(ACC_25, ACC_26))
    (sources / f"{ACC_24}.json").write_bytes(_excerpt_bytes(ACC_24))
    sha20 = _excerpt(ACC_24)["span"]["raw_sha256"][:20]
    nested = sources / ACC_24
    nested.mkdir()
    nested_file = nested / f"{sha20}.json"
    nested_file.write_bytes(_excerpt_bytes(ACC_24))

    def _run(out_dir: Path):
        proc = _run_producer(
            "--as-of",
            AS_OF,
            "--extraction",
            str(EXTRACTION_PATH),
            "--sources",
            str(sources),
            "--out-dir",
            str(out_dir),
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        return proc

    both_out = tmp_path / "flat_and_nested"
    both_proc = _run(both_out)
    # Remove the nested twin and rerun over the same directory: the flat run.
    nested_file.unlink()
    nested.rmdir()
    flat_out = tmp_path / "flat_only"
    flat_proc = _run(flat_out)
    assert flat_proc.stdout == both_proc.stdout
    # The nested twin is fully absorbed: byte-identical outputs to the flat run.
    for name in ("observation_package.v2.json", "relationship_edges.json"):
        assert (flat_out / name).read_bytes() == (both_out / name).read_bytes(), name
    pkg = json.loads((both_out / "observation_package.v2.json").read_text("utf-8"))
    edges = json.loads((both_out / "relationship_edges.json").read_text("utf-8"))
    # The flat file is the input; the nested twin is not recorded.
    acc24_inputs = [
        entry["path"] for entry in pkg["inputs"] if ACC_24 in entry["path"]
    ]
    assert [p.rsplit("/", 1)[-1] for p in acc24_inputs] == [f"{ACC_24}.json"]
    # The excerpt_path falls back to the flat template.
    edge = edges["edges"][0]
    for ref in edge["source_refs"]:
        if ref["accession"] == ACC_24:
            assert ref["excerpt_path"] == EXCERPT_PATH_TEMPLATE.format(accession=ACC_24)
    for rev in edge["magnitude_history"]:
        if rev["source_ref"]["accession"] == ACC_24:
            assert rev["source_ref"]["excerpt_path"].endswith(f"/{ACC_24}.json")
    # Identical source content gives the committed M1 package identity.
    assert pkg["package_id"] == PACKAGE_ID_PIN


def test_lookup_order_unit():
    poison = pv2.CORRUPT
    keyed = {"span": "keyed"}
    plain = {"span": "plain"}
    source = {"accession": "ACC", "span_sha256": "ab"}
    # A poison sentinel wins over a keyed dict.
    assert (
        pv2._lookup_excerpt({"ACC": poison, ("ACC", "ab"): keyed}, source) is poison
    )
    # A keyed dict beats the plain single-excerpt entry.
    assert pv2._lookup_excerpt({"ACC": plain, ("ACC", "ab"): keyed}, source) is keyed
    # The plain entry is returned when no keyed entry exists.
    assert pv2._lookup_excerpt({"ACC": plain}, source) is plain
    # Neither -> None -> source_unavailable.
    assert pv2._lookup_excerpt({}, source) is None
    # A source_ref with no span hash reads the plain-by-accession entry.
    assert pv2._lookup_excerpt({"ACC": plain}, {"accession": "ACC"}) is plain


def test_observation_identity_object_label():
    # The two M1 ids recompute unchanged with or without a label (object resolved).
    assert (
        pv2.observation_identity(ACC_24, 1396889, 1397687, "supplier_customer", SWKS, AAPL)
        == "obs:aafd6fdeb1ee9043d452"
    )
    assert (
        pv2.observation_identity(
            ACC_24, 1396889, 1397687, "supplier_customer", SWKS, AAPL, "ignored"
        )
        == "obs:aafd6fdeb1ee9043d452"
    )
    assert (
        pv2.observation_identity(ACC_25, 1500407, 1501205, "supplier_customer", SWKS, AAPL)
        == M1_ROW_25
    )
    assert (
        pv2.observation_identity(
            ACC_25, 1500407, 1501205, "supplier_customer", SWKS, AAPL, "ignored"
        )
        == M1_ROW_25
    )
    # Unresolved object: the label separates two counterparties of one span.
    base = pv2.observation_identity(
        "0000004127-99-000001", 0, 10, "supplier_customer", SWKS, None
    )
    cust_a = pv2.observation_identity(
        "0000004127-99-000001", 0, 10, "supplier_customer", SWKS, None, "Customer A"
    )
    cust_b = pv2.observation_identity(
        "0000004127-99-000001", 0, 10, "supplier_customer", SWKS, None, "Customer B"
    )
    assert cust_a != cust_b
    assert base not in (cust_a, cust_b)
    # None and "" labels keep the exact 6-element id.
    assert (
        pv2.observation_identity(
            "0000004127-99-000001", 0, 10, "supplier_customer", SWKS, None, None
        )
        == base
    )
    assert (
        pv2.observation_identity(
            "0000004127-99-000001", 0, 10, "supplier_customer", SWKS, None, ""
        )
        == base
    )
    # The 7-element formula, checked against an inline canon/sha recomputation.
    assert cust_a == (
        "obs:"
        + _sha_text(
            pv2.canon(
                [
                    "0000004127-99-000001",
                    0,
                    10,
                    "supplier_customer",
                    SWKS,
                    None,
                    "Customer A",
                ]
            )
        )[:20]
    )


def test_identity_rule_declared_in_extraction_contract():
    schema = json.loads(
        (
            REPO_ROOT
            / "contracts/company_intelligence/relationship_extraction.v1.schema.json"
        ).read_text("utf-8")
    )
    assert schema["x-gmi-identity-rule"] == IDENTITY_RULE
    clock = schema.get("x-gmi-clock-rule")
    assert isinstance(clock, dict)
    assert clock["rule_id"] == "A24"
    assert clock["not_a_clock"] == ["sec_submissions_acceptance_raw"]
    jsonschema.validators.Draft202012Validator.check_schema(schema)


def test_committed_rows_ids_recompute():
    files = sorted(
        (
            REPO_ROOT / "research/theme_graph/gmi_relationships_20261021/extraction"
        ).rglob("*.jsonl")
    )
    assert files
    checked = 0
    for path in files:
        for line in path.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            source = row.get("source_ref") or {}
            if row["row_kind"] == "observation":
                obj = row["object"]
                label = obj.get("anonymous_alias") or obj.get("name_as_filed")
                assert pv2.observation_identity(
                    source["accession"],
                    source["byte_start"],
                    source["byte_end"],
                    row["species"],
                    row["subject"]["issuer_id"],
                    obj["issuer_id"],
                    object_label=label,
                ) == row["observation_id"]
                checked += 1
            elif row["row_kind"] == "document_assessment":
                assert pv2.assessment_identity(
                    source["accession"],
                    source["byte_start"],
                    source["byte_end"],
                    row["assessment"],
                ) == row["assessment_id"]
                checked += 1
    assert checked >= 3


def test_duplicate_observation_identical_collapses(tmp_path):
    extraction = tmp_path / "extraction"
    extraction.mkdir()
    (extraction / "a.jsonl").write_bytes(EXTRACTION_PATH.read_bytes())
    (extraction / "b.jsonl").write_bytes(EXTRACTION_PATH.read_bytes())
    single_out = tmp_path / "single"
    dup_out = tmp_path / "dup"
    single_proc = _run_producer(
        "--as-of", AS_OF, "--extraction", str(EXTRACTION_PATH), "--out-dir", str(single_out)
    )
    dup_proc = _run_producer(
        "--as-of", AS_OF, "--extraction", str(extraction), "--out-dir", str(dup_out)
    )
    assert single_proc.returncode == 0 and dup_proc.returncode == 0
    single_pkg = json.loads(
        (single_out / "observation_package.v2.json").read_text("utf-8")
    )
    dup_pkg = json.loads((dup_out / "observation_package.v2.json").read_text("utf-8"))
    single_edges = json.loads(
        (single_out / "relationship_edges.json").read_text("utf-8")
    )
    dup_edges = json.loads((dup_out / "relationship_edges.json").read_text("utf-8"))
    # Identical rows collapse to one: everything but the input list (and the
    # ids derived from it) matches the single-file package.
    for key, value in dup_pkg.items():
        if key in ("inputs", "package_id"):
            continue
        assert value == single_pkg[key], key
    for key, value in dup_edges.items():
        if key in ("package_id", "package_sha256"):
            continue
        assert value == single_edges[key], key
    names = [
        entry["path"].rsplit("/", 1)[-1]
        for entry in dup_pkg["inputs"]
        if entry["path"].endswith(".jsonl")
    ]
    assert sorted(names) == ["a.jsonl", "b.jsonl"]


def test_duplicate_observation_conflict_skips_all(tmp_path):
    extraction = tmp_path / "extraction"
    extraction.mkdir()
    (extraction / "a.jsonl").write_bytes(EXTRACTION_PATH.read_bytes())
    rows = []
    for line in EXTRACTION_PATH.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("observation_id") == M1_ROW_25:
            row["magnitudes"][0]["value"] = 0.99
        rows.append(json.dumps(row))
    (extraction / "b.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of", AS_OF, "--extraction", str(extraction), "--out-dir", str(out)
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _has_warning(proc.stdout, "OBSERVATION_DUPLICATE_CONFLICT")
    warning = next(
        line
        for line in proc.stdout.splitlines()
        if line.startswith("::warning title=OBSERVATION_DUPLICATE_CONFLICT")
    )
    assert M1_ROW_25 in warning and " 2 " in warning
    pkg = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    edges = json.loads((out / "relationship_edges.json").read_text("utf-8"))
    assert [o["observation_id"] for o in pkg["observations"]] == [
        "obs:aafd6fdeb1ee9043d452"
    ]
    assert pkg["observations"][0]["source_state"] == "verified"
    assert M1_ROW_25 not in json.dumps(pkg) + json.dumps(edges)
    # The other rows are unaffected: the edge survives on its remaining leg.
    assert len(edges["edges"]) == 1
    assert [ref["accession"] for ref in edges["edges"][0]["source_refs"]] == [ACC_24]
    assert pkg["counts"]["edges"] == 1


def test_duplicate_assessment_conflict_skips_all(tmp_path):
    extraction = tmp_path / "extraction"
    extraction.mkdir()
    (extraction / "a.jsonl").write_bytes(EXTRACTION_PATH.read_bytes())
    rows = []
    for line in EXTRACTION_PATH.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("assessment_id") == M1_ASM:
            row["reason"] = "tampered_reason"
        rows.append(json.dumps(row))
    (extraction / "b.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    out = tmp_path / "out"
    proc = _run_producer(
        "--as-of", AS_OF, "--extraction", str(extraction), "--out-dir", str(out)
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _has_warning(proc.stdout, "ASSESSMENT_DUPLICATE_CONFLICT")
    pkg = json.loads((out / "observation_package.v2.json").read_text("utf-8"))
    edges = json.loads((out / "relationship_edges.json").read_text("utf-8"))
    assert pkg["assessments"] == []
    assert M1_ASM not in json.dumps(pkg) + json.dumps(edges)
    # Observations are unaffected.
    assert len(pkg["observations"]) == 2
    assert all(o["disposition"] == "edge" for o in pkg["observations"])
    assert len(edges["edges"]) == 1
    assert edges["edges"][0]["correction_lineage"] == []


def test_replay_loads_nested_excerpts(tmp_path, capsys):
    sources = _nested_sources(tmp_path)
    rc = replay.main(["--sources", str(sources)])
    out = capsys.readouterr().out
    for acc in (ACC_24, ACC_25, ACC_26):
        assert f"{acc}: ok" in out
    assert "sources=3 failures=0" in out
    assert rc == 0

    broken = sources / "nested" / "deeper"
    broken.mkdir(parents=True)
    (broken / "broken.json").write_bytes(b"{oops")
    rc = replay.main(["--sources", str(sources)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "nested/deeper/broken.json" in out
    assert "failures=1" in out
