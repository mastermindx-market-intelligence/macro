"""Wholly synthetic native custody fixtures; no retained production-source proof."""
from copy import deepcopy
from hashlib import sha256
import gzip
from pathlib import Path
from types import SimpleNamespace

import pytest

from collectors.sec_document_spine import (
    manifest_storage_key, persist_archive_document, persist_filing_manifest, receipt_storage_key,
)
from engine.company_intelligence.pinned_relationship_candidates import inspect_pinned_candidate
from engine.company_intelligence.relationship_candidates import MAX_SOURCE_BYTES, SCHEMA
from engine.earnings_release.receipts import receipt_for_char_span, sha256_text
from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority
from engine.fundamental_forensics.models import canonical_json
from engine.fundamental_forensics.sec_document_spine import (
    build_filing_manifests, documents_from_archive_index, with_archive_documents,
    with_document_retrievals,
)
from engine.fundamental_forensics.source_sync import sync_source_roots
from engine.research_vault.r2_store import LocalStore

SPAN = "<p>Aurora plans Widget integration in Boreal systems next year.</p>"
BODY = ("SYNTHETIC — café.\r\n" + SPAN + "\r\nSYNTHETIC footer.").encode("utf-8")
RECORDED = "2024-03-01T12:00:00Z"
SNAPSHOT_AT = "2024-03-02T12:00:00Z"


class SyntheticReadOnlySpy:
    """A test-only native strict reader; denied surfaces prove adapter read scope."""

    def __init__(self, backing):
        self.backing = backing
        self.reads = []
        self.failure = None
        self.missing_key = None

    def get_bytes_strict_bounded(self, key, maximum_bytes):
        self.reads.append((key, maximum_bytes))
        if self.failure is not None:
            raise self.failure
        if key == self.missing_key:
            return None
        return self.backing.get_bytes_strict_bounded(key, maximum_bytes)

    def _denied(self, *args, **kwargs):
        raise AssertionError("adapter attempted a write, discovery, or unbounded read")

    get_bytes = get_bytes_strict = put_bytes = list_prefix = exists = upload_time = _denied


def fixture(tmp_path, *, body=BODY, stored=True, form="10-K", recorded=RECORDED,
            retrieved=RECORDED, snapshot_at=SNAPSHOT_AT, prepare=None, alias=False,
            store_other=False):
    # Native owner capture is used only to construct temporary synthetic fixtures.
    raw_root = tmp_path / "synthetic-raw"
    archive_root = tmp_path / "synthetic-archive"
    raw_root.mkdir(parents=True)
    archive_root.mkdir(parents=True)
    manifest = build_filing_manifests({
        "cik": "1", "name": "SYNTHETIC Aurora",
        "filings": {"recent": {
            "accessionNumber": ["0000000001-24-000001"], "form": [form],
            "filingDate": ["2024-02-26"], "reportDate": ["2023-12-31"],
            "acceptanceDateTime": ["2024-02-26T16:00:00Z"],
            "primaryDocument": ["annual.htm"],
        }},
    }, recorded_at=recorded)[0]
    inventory = documents_from_archive_index(
        manifest, {"directory": {"item": [{"name": "annual.htm"}, {"name": "other.htm"}]}},
    )
    manifest = with_archive_documents(manifest, inventory)
    primary = next(d for d in manifest["documents"] if d["document_name"] == "annual.htm")
    if stored:
        receipt = persist_archive_document(archive_root, primary, body, retrieved_at=retrieved)
        receipts = {primary["document_id"]: receipt.to_dict()}
        if store_other:
            other = next(d for d in manifest["documents"] if d["document_name"] == "other.htm")
            other_receipt = persist_archive_document(archive_root, other, body, retrieved_at=retrieved)
            receipts[other["document_id"]] = other_receipt.to_dict()
        manifest = with_document_retrievals(manifest, receipts)
    manifest_key = persist_filing_manifest(archive_root, manifest)
    primary = next(d for d in manifest["documents"] if d["document_name"] == "annual.htm")
    if prepare:
        prepare(archive_root, manifest, primary)
    alias_key = "manifests/0000000001/0000000001-24-000002/" + manifest["manifest_id"] + ".json"
    if alias:
        target = archive_root / alias_key
        target.parent.mkdir(parents=True)
        target.write_bytes((archive_root / manifest_key).read_bytes())
    backing = LocalStore(tmp_path / "synthetic-store")
    snapshot = sync_source_roots(raw_root=raw_root, archive_root=archive_root, store=backing,
                                 snapshot_at=snapshot_at, publish_latest=False)
    reader = SyntheticReadOnlySpy(backing)
    authority = PinnedSourceAuthority(store=reader, snapshot_id=snapshot.snapshot_id)
    source = BODY.decode("utf-8")
    start = source.index(SPAN)
    span_receipt = receipt_for_char_span(
        source=source, source_sha256=sha256_text(source),
        char_start=start, char_end=start + len(SPAN),
    ).to_dict()
    digest = sha256(body).hexdigest()
    candidate = {
        "schema": SCHEMA, "candidate_id": "synthetic:relation:1",
        "document": {
            "document_id": primary["document_id"], "version": "sha256:" + digest,
            "source_ref": primary["archive_url"], "published_date": None,
        },
        "dataset_id": None, "temporal_row": None, "receipt": span_receipt,
        "assertion": {
            "kind": "product_integration", "subject_label": "Aurora", "object_label": "Boreal",
            "product_scope": "Widget", "lifecycle": "planned", "magnitude": None,
        },
        "revision": {"supersedes_candidate_id": None, "relation": "original"},
        "identity_annotations": None,
    }
    return SimpleNamespace(
        authority=authority, snapshot=snapshot, reader=reader, backing=backing,
        archive_root=archive_root, manifest=manifest, manifest_key=manifest_key,
        document=primary, candidate=candidate, alias_key=alias_key,
    )


def inspect(f, **kwargs):
    return inspect_pinned_candidate(
        kwargs.pop("candidate", f.candidate),
        authority=kwargs.pop("authority", f.authority),
        snapshot_id=kwargs.pop("snapshot_id", f.snapshot.snapshot_id),
        manifest_key=kwargs.pop("manifest_key", f.manifest_key),
        document_id=kwargs.pop("document_id", f.document["document_id"]),
        **kwargs,
    )


def assert_refusal(result, code=None):
    assert result["inspection_status"] == "REFUSED"
    assert result["native_source_binding"] is None
    assert result["admission"] == "NOT_ADMITTED"
    assert result["graph1_projection"] is None
    assert not any(result["authority"].values())
    assert result["content_boundary"]["public_safe_payload"] == "NOT_CERTIFIED"
    if result["candidate_inspection"]:
        assert result["candidate_inspection"]["current_candidate_view"] is None
        assert result["candidate_inspection"]["source_provenance"] is None
    if code:
        assert result["refusal"]["code"] == code


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_positive_actual_native_reader_replay_is_separate_from_semantics(tmp_path):
    f = fixture(tmp_path)
    before = files(tmp_path)
    candidate = deepcopy(f.candidate)
    result = inspect(f)
    assert result == inspect(f)
    assert f.candidate == candidate and files(tmp_path) == before
    assert result["inspection_status"] == "INSPECTABLE"
    binding = result["native_source_binding"]
    assert binding["source_custody"] == "verified_relative_to_supplied_native_reader"
    assert binding["reader_owner_authenticity"] == "not_independently_established"
    assert binding["sec_authorship"] == "not_cryptographically_authenticated"
    assert binding["raw_sha256"] == sha256(BODY).hexdigest()
    assert binding["raw_byte_length"] == len(BODY)
    assert binding["archive_url"] == f.document["archive_url"]
    assert binding["receipt_sidecar_verified"] is True
    assert binding["retrieval_receipt"] == f.document["retrieval"]
    for key in ("manifest_witness", "receipt_sidecar_witness", "gzip_object_witness"):
        assert binding[key]["snapshot_id"] == f.snapshot.snapshot_id
    assert binding["source_local_clocks"]["filed_on"] == "2024-02-26"
    assert binding["source_local_filing"]["report_date"] == "2023-12-31"
    inspected = result["candidate_inspection"]
    assert inspected["source_provenance"]["metadata_authenticity"] == "caller_supplied_not_authenticated"
    assert inspected["source_provenance"]["published_date"] is None
    assert "replayed_value_text" not in inspected["support"]
    assert inspected["current_candidate_view"]["assertion"]["lifecycle"] == "planned"
    assert inspected["current_candidate_view"]["economic_weight"] is None
    assert inspected["current_candidate_view"]["canonical_subject_id"] is None
    assert result["gaps"]["rights"] and result["gaps"]["reader_owner"]
    assert not any(result["authority"].values())
    assert all(type(limit) is int and limit >= 0 for _, limit in f.reader.reads)
    assert all("latest" not in key for key, _ in f.reader.reads)


def test_private_support_opt_in_never_grants_rights_or_authorship(tmp_path):
    f = fixture(tmp_path)
    result = inspect(f, include_support_text=True)
    assert "next year" in result["candidate_inspection"]["support"]["replayed_value_text"]
    assert result["admission"] == "NOT_ADMITTED" and result["gaps"]["rights"]
    assert result["native_source_binding"]["sec_authorship"] == "not_cryptographically_authenticated"


@pytest.mark.parametrize("field,value", [
    ("document_id", "invented:document"), ("version", "latest"),
    ("source_ref", "https://www.sec.gov/Archives/fabricated.htm"),
    ("published_date", "2024-02-26"),
])
def test_caller_source_metadata_cannot_be_laundered(field, value, tmp_path):
    f = fixture(tmp_path)
    f.candidate["document"][field] = value
    assert_refusal(inspect(f), "CANDIDATE_SOURCE_METADATA_MISMATCH")


def test_snapshot_document_and_manifest_selection_are_exact(tmp_path):
    f = fixture(tmp_path, alias=True)
    other = fixture(tmp_path / "other-snapshot", snapshot_at="2024-03-03T12:00:00Z")
    assert_refusal(inspect(f, snapshot_id=other.snapshot.snapshot_id), "SNAPSHOT_SELECTOR_MISMATCH")
    assert_refusal(inspect(f, manifest_key=f.alias_key), "MANIFEST_SELECTOR_MISMATCH")
    assert_refusal(inspect(f, document_id="sec_document_unknown"), "DOCUMENT_NOT_UNIQUELY_SELECTED")
    other_document = next(d for d in f.manifest["documents"] if d["document_name"] == "other.htm")
    assert_refusal(inspect(f, document_id=other_document["document_id"]), "DOCUMENT_NOT_STORED")


def test_other_retained_document_cannot_substitute_for_candidate_locator(tmp_path):
    f = fixture(tmp_path, store_other=True)
    other = next(d for d in f.manifest["documents"] if d["document_name"] == "other.htm")
    assert other["availability"] == "stored"
    assert_refusal(inspect(f, document_id=other["document_id"]), "CANDIDATE_SOURCE_METADATA_MISMATCH")


def test_exact_authority_required_and_cached_mapping_cannot_redirect(tmp_path):
    f = fixture(tmp_path)
    assert_refusal(inspect(f, authority=SimpleNamespace(snapshot_id=f.snapshot.snapshot_id)),
                   "EXACT_NATIVE_AUTHORITY_REQUIRED")
    original_snapshot = f.authority._snapshot
    f.authority._snapshot = SimpleNamespace(snapshot_id="ffsecsrc_" + "0" * 64)
    f.authority.read_archive_document = lambda **kwargs: pytest.fail("session override used")
    result = inspect(f)
    assert result["inspection_status"] == "INSPECTABLE"
    assert result["native_source_binding"]["snapshot_id"] == original_snapshot.snapshot_id


def test_declared_body_is_explicitly_unavailable(tmp_path):
    assert_refusal(inspect(fixture(tmp_path, stored=False)), "DOCUMENT_NOT_STORED")


@pytest.mark.parametrize("maximum_bytes", [True, False, 0, -1, "100", MAX_SOURCE_BYTES + 1])
def test_invalid_limit_refuses_before_source_reads(maximum_bytes, tmp_path):
    f = fixture(tmp_path)
    before = list(f.reader.reads)
    assert_refusal(inspect(f, maximum_bytes=maximum_bytes), "SOURCE_LIMIT_INVALID")
    assert f.reader.reads == before


def test_receipted_raw_size_limit_is_applied_before_archive_read(tmp_path):
    f = fixture(tmp_path)
    assert_refusal(inspect(f, maximum_bytes=len(BODY) - 1), "SOURCE_RAW_SIZE_OUTSIDE_LIMIT")
    object_keys = {key for key, _ in f.reader.reads}
    assert not any(key.endswith(f.document["content_sha256"] + ".bin.gz") for key in object_keys)


def test_native_document_above_application_cap_refuses_without_inflation(tmp_path):
    f = fixture(tmp_path, body=BODY + b"x" * MAX_SOURCE_BYTES)
    assert_refusal(inspect(f), "SOURCE_RAW_SIZE_OUTSIDE_LIMIT")


def test_non_utf8_native_bytes_never_reach_text_inspector(tmp_path):
    f = fixture(tmp_path, body=b"\xff\xfe synthetic")
    assert_refusal(inspect(f), "SOURCE_UTF8_INVALID")


@pytest.mark.parametrize("which", ["manifest", "sidecar", "gzip"])
def test_pinned_outer_object_tamper_is_native_contract_failure(which, tmp_path):
    f = fixture(tmp_path)
    native = f.authority
    if which == "manifest":
        read = native.read_file(kind="archive", relative_path=f.manifest_key, maximum_bytes=1024 * 1024)
    else:
        path = (receipt_storage_key(f.document["retrieval"]["receipt_id"])
                if which == "sidecar" else f.document["storage_key"])
        read = native.read_file(kind="archive", relative_path=path, maximum_bytes=1024 * 1024)
    # Same-length tampering reaches native snapshot digest validation instead
    # of the backing reader's independently enforced length cap.
    tampered = bytes([read.content[0] ^ 1]) + read.content[1:]
    f.backing.put_bytes(read.witness.object_key, tampered)
    assert_refusal(inspect(f), "PINNED_SOURCE_CONTRACT_INVALID")


@pytest.mark.parametrize("which", ["manifest", "sidecar", "gzip"])
def test_native_localstore_length_overflow_is_bounded_and_never_missing(which, tmp_path):
    f = fixture(tmp_path)
    path = (f.manifest_key if which == "manifest" else
            receipt_storage_key(f.document["retrieval"]["receipt_id"]) if which == "sidecar" else
            f.document["storage_key"])
    read = f.authority.read_file(kind="archive", relative_path=path, maximum_bytes=1024 * 1024)
    f.backing.put_bytes(read.witness.object_key, read.content + b"synthetic-overflow")
    result = inspect(f)
    assert_refusal(result, "SOURCE_BOUNDED_READ_FAILED")
    assert result["refusal"]["code"] != "PINNED_SOURCE_MISSING"


@pytest.mark.parametrize("replacement", [
    b"not-a-gzip", gzip.compress(BODY.replace(b"Widget", b"Gadget"), mtime=0),
    gzip.compress(b"x" * 4096, mtime=0),
])
def test_self_consistent_snapshot_does_not_override_raw_receipt(replacement, tmp_path):
    def prepare(archive, manifest, document):
        (archive / document["storage_key"]).write_bytes(replacement)
    f = fixture(tmp_path, prepare=prepare)
    assert_refusal(inspect(f), "NATIVE_ARCHIVE_REPLAY_FAILED")


def test_native_sidecar_must_match_complete_selected_manifest_receipt(tmp_path):
    def prepare(archive, manifest, document):
        # Mint a different complete receipt using the native owner, then retain
        # it at the selected sidecar location in this intentionally bad fixture.
        alternate = persist_archive_document(tmp_path / "synthetic-alternate-cache", document,
                                             BODY, retrieved_at=RECORDED, http_etag="synthetic-other")
        (archive / receipt_storage_key(document["retrieval"]["receipt_id"])).write_bytes(
            canonical_json(alternate.to_dict()).encode("utf-8"))
    assert_refusal(inspect(fixture(tmp_path, prepare=prepare)), "NATIVE_ARCHIVE_REPLAY_FAILED")


def test_invalid_retained_manifest_is_distinct_from_object_absence(tmp_path):
    def prepare(archive, manifest, document):
        (archive / manifest_storage_key(manifest)).write_bytes(b"{}")
    assert_refusal(inspect(fixture(tmp_path, prepare=prepare)), "NATIVE_MANIFEST_INVALID")


def test_missing_object_is_distinct_from_auth_outage_and_integrity(tmp_path):
    f = fixture(tmp_path)
    f.reader.missing_key = f.snapshot.manifest_key
    assert_refusal(inspect(f), "PINNED_SOURCE_MISSING")
    f.reader.missing_key = None
    f.reader.failure = PermissionError("synthetic unauthorized secret must not echo")
    result = inspect(f)
    assert_refusal(result, "SOURCE_ACCESS_DENIED")
    assert "secret" not in str(result)
    f.reader.failure = OSError("synthetic network outage")
    assert_refusal(inspect(f), "SOURCE_READER_UNAVAILABLE")
    class SyntheticSDKError(Exception):
        pass
    f.reader.failure = SyntheticSDKError("synthetic SDK detail must not echo")
    assert_refusal(inspect(f), "SOURCE_READER_FAILED")


@pytest.mark.parametrize("field", ["recorded", "retrieved"])
def test_post_snapshot_source_capture_is_not_causally_admitted(field, tmp_path):
    f = fixture(tmp_path, **{field: "2024-03-03T12:00:00Z"})
    code = "MANIFEST_RECORDED_AFTER_SNAPSHOT" if field == "recorded" else "DOCUMENT_RETRIEVED_AFTER_SNAPSHOT"
    assert_refusal(inspect(f), code)


@pytest.mark.parametrize("as_of", ["2024-02-26", "2024-02-26T12:00:00", "2024-02-26T12:00:00Z"])
def test_historical_refusal_exposes_no_current_source_binding_or_provenance(as_of, tmp_path):
    f = fixture(tmp_path)
    result = inspect(f, as_of=as_of)
    assert_refusal(result)
    assert result["native_source_binding"] is None
    if result["candidate_inspection"]:
        assert result["candidate_inspection"]["source_provenance"] is None
        assert result["candidate_inspection"]["current_candidate_view"] is None


def test_native_future_known_row_excludes_all_current_source_witnesses(tmp_path):
    from lib.dataos.registry import DatasetContract, DatasetStatus, Layer, Registry
    from lib.dataos.temporal import TemporalProfile
    f = fixture(tmp_path)
    candidate = deepcopy(f.candidate)
    candidate["dataset_id"] = "synthetic_relationship_probe"
    candidate["temporal_row"] = {
        "candidate_id": candidate["candidate_id"],
        "document_id": candidate["document"]["document_id"],
        "document_version": candidate["document"]["version"],
        "source_sha256": candidate["receipt"]["source_sha256"],
        "event_at": RECORDED, "published_at": RECORDED, "ingested_at": RECORDED,
    }
    fields = ("candidate_id", "document_id", "document_version", "source_sha256")
    registry = Registry([DatasetContract(
        dataset_id="synthetic_relationship_probe", owner="synthetic-test", producer="synthetic-test",
        storage="synthetic", format="synthetic", layer=Layer.L0_SOURCE,
        grain=fields[:3], schema={name: {"type": "string"} for name in fields},
        temporal_profile=TemporalProfile.EVENT, version="synthetic-v1", status=DatasetStatus.PRODUCED,
    )])
    result = inspect(f, candidate=candidate, as_of="2024-02-25T00:00:00Z", registry=registry)
    assert result["inspection_status"] == "NOT_KNOWN_AS_OF"
    assert result["native_source_binding"] is None
    assert result["candidate_inspection"]["source_provenance"] is None
    assert result["candidate_inspection"]["current_candidate_view"] is None
    assert result["candidate_inspection"]["support"] is None
    assert not any(result["authority"].values())


def test_amendment_source_lineage_does_not_rewrite_candidate_revision(tmp_path):
    f = fixture(tmp_path, form="10-K/A")
    result = inspect(f)
    assert result["inspection_status"] == "INSPECTABLE"
    assert result["native_source_binding"]["source_local_lineage"] == f.manifest["lineage"]
    assert result["native_source_binding"]["source_local_lineage"]["relationship"] == "unresolved"
    assert result["candidate_inspection"]["current_candidate_view"]["revision"]["relation"] == "original"


def test_candidate_receipt_body_hash_and_authority_injection_still_refuse(tmp_path):
    f = fixture(tmp_path)
    f.candidate["receipt"]["source_sha256"] = "0" * 64
    assert_refusal(inspect(f), "SOURCE_REPLAY_FAILED")
    f = fixture(tmp_path / "authority-injection")
    f.candidate["authority"] = {"trade": True}
    assert_refusal(inspect(f), "INPUT_INVALID")


@pytest.mark.parametrize("candidate", [None, [], {}, "malformed"])
def test_malformed_candidate_is_bounded_refusal(candidate, tmp_path):
    f = fixture(tmp_path)
    assert_refusal(inspect(f, candidate=candidate), "CANDIDATE_DOCUMENT_INVALID")


def test_fresh_reader_replays_without_acquisition_imports_or_side_effects(tmp_path):
    """Native writers run only in the parent; the fresh child is a guarded reader."""
    import json
    import os
    import subprocess
    import sys
    import textwrap

    f = fixture(tmp_path)
    expected = inspect(f)
    assert expected["inspection_status"] == "INSPECTABLE"
    before = files(tmp_path)
    payload = {
        "code_root": str(Path(__file__).resolve().parents[1]),
        "fixture_root": str(tmp_path.resolve()),
        "store_root": str(f.backing.root.resolve()),
        "candidate": f.candidate,
        "snapshot_id": f.snapshot.snapshot_id,
        "manifest_key": f.manifest_key,
        "document_id": f.document["document_id"],
        "expected": expected,
    }
    child = textwrap.dedent(r"""
        from hashlib import sha256
        import json
        import os
        from pathlib import Path
        import stat
        import sys

        sys.dont_write_bytecode = True
        payload = json.load(sys.stdin)

        def require(condition, label):
            if not condition:
                raise AssertionError(label)

        forbidden = (
            "collectors", "requests", "urllib3", "httpx", "aiohttp",
            "boto3", "botocore", "urllib.request", "http.client",
        )
        def acquisition_module(name):
            return any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)

        blocked_imports = []
        class NoAcquisitionImports:
            def find_spec(self, fullname, path=None, target=None):
                if acquisition_module(fullname):
                    frame = sys._getframe(1)
                    callers = []
                    while frame is not None:
                        module = frame.f_globals.get("__name__", "")
                        if module.startswith("engine."):
                            callers.append((module, frame.f_code.co_name, frame.f_lineno))
                        frame = frame.f_back
                    blocked_imports.append({"module": fullname, "callers": callers})
                    raise ImportError("fresh reader denied acquisition import " + fullname)
                return None

        require(not any(acquisition_module(name) for name in sys.modules),
                "acquisition dependency was warmed before the reader guard")
        sys.meta_path.insert(0, NoAcquisitionImports())
        guard = {"filesystem": False, "blocked_events": []}
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        mutation_events = {
            "os.mkdir", "os.rmdir", "os.remove", "os.rename", "os.link", "os.symlink",
            "os.chmod", "os.chown", "os.utime", "os.truncate", "os.setxattr", "os.removexattr",
            "shutil.copyfile", "shutil.copymode", "shutil.copystat", "shutil.rmtree",
        }
        def audit(event, values):
            deny = event.startswith(("socket.", "subprocess.", "os.exec", "os.spawn")) or event in {
                "os.system", "os.fork", "os.forkpty", "os.posix_spawn",
            }
            if guard["filesystem"]:
                deny = deny or event in mutation_events
                if event == "open":
                    mode, flags = values[1], values[2]
                    deny = deny or (isinstance(mode, str) and any(x in mode for x in "wax+")) or (
                        isinstance(flags, int) and bool(flags & write_flags)
                    )
            if deny:
                guard["blocked_events"].append(event)
                raise PermissionError("read-only replay denied " + event)
        sys.addaudithook(audit)

        fixture_root = Path(payload["fixture_root"])
        store_root = Path(payload["store_root"])
        for directory in [*reversed(store_root.parents), store_root]:
            require(stat.S_ISDIR(directory.lstat().st_mode),
                    "existing store chain contains a non-directory or symlink")

        def tree_state():
            result = {}
            for path in [fixture_root, *sorted(fixture_root.rglob("*"))]:
                info = path.lstat()
                base = (info.st_dev, info.st_ino, info.st_mtime_ns)
                if stat.S_ISDIR(info.st_mode):
                    result[str(path)] = ("directory", *base)
                else:
                    require(stat.S_ISREG(info.st_mode), "fixture contains a non-regular file")
                    result[str(path)] = ("file", *base, info.st_size, sha256(path.read_bytes()).hexdigest())
            return result

        before = tree_state()
        latest = store_root / "fundamental_forensics/sec-source/v1/latest.json"
        require(not latest.exists() and not latest.is_symlink(), "unexpected latest pointer")
        sys.path.insert(0, payload["code_root"])
        from engine.research_vault.r2_store import LocalStore
        from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority
        from engine.company_intelligence.pinned_relationship_candidates import inspect_pinned_candidate

        # LocalStore calls mkdir(exist_ok=True). Supply only the checked existing
        # store, verify its identity, then enable the full mutation guard.
        store = LocalStore(store_root)
        require(tree_state() == before, "imports or constructor changed existing fixture state")
        guard["filesystem"] = True
        authority = PinnedSourceAuthority(store=store, snapshot_id=payload["snapshot_id"])
        result = inspect_pinned_candidate(
            payload["candidate"], authority=authority, snapshot_id=payload["snapshot_id"],
            manifest_key=payload["manifest_key"], document_id=payload["document_id"],
        )
        require(not blocked_imports, "acquisition imports attempted: " + repr(blocked_imports))
        require(not guard["blocked_events"], "forbidden side effects attempted: " + repr(guard["blocked_events"]))
        require(not any(acquisition_module(name) for name in sys.modules),
                "an acquisition module entered the fresh reader")
        require(result["inspection_status"] == "INSPECTABLE", "positive source replay did not complete")
        require(result == payload["expected"], "complete positive output differs")
        require(result["admission"] == "NOT_ADMITTED" and result["graph1_projection"] is None,
                "admission boundary changed")
        require(all(value is False for value in result["authority"].values()), "authority boundary changed")
        require(tree_state() == before, "reader changed retained fixture state")
        require(not latest.exists() and not latest.is_symlink(), "reader created a latest pointer")
        print(json.dumps({
            "result": result, "blocked_imports": blocked_imports,
            "blocked_events": guard["blocked_events"], "retained_state_unchanged": True,
        }, sort_keys=True))
    """)
    run = subprocess.run(
        [sys.executable, "-B", "-c", child], input=json.dumps(payload),
        text=True, capture_output=True, cwd=tmp_path,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=30,
    )
    assert run.returncode == 0, run.stderr
    assert run.stderr == ""
    actual = json.loads(run.stdout)
    assert actual == {
        "result": expected, "blocked_imports": [], "blocked_events": [],
        "retained_state_unchanged": True,
    }
    assert files(tmp_path) == before
