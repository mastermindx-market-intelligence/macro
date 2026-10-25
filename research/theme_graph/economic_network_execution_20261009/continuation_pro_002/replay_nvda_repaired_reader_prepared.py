#!/usr/bin/env python3
"""Prepared independent retained-source replay; principal freeze gate required.

Run only in a fresh native Python -B process after the principal has verified this
script's digest and supplied a separately digest-pinned source-verification
receipt. Designed for stdin execution; it writes no file and invokes no Git,
capture, credential factory, provider, network client, or child process.

Historical capture/witness code hashes remain capture provenance. Current replay
code is bound separately. A phase label is a principal-receipt claim, not this
read-only harness independently proving a GitHub merge or production admission.
"""

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.machinery
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

sys.dont_write_bytecode = True

CODE_ROOT = Path("/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-native-reader-20261009-pro-002")
CACHE = Path("/Users/chriswong/Library/Caches/Mastermind/economic-network-20261009")
CODE_EVIDENCE_ROOT = Path("/Users/chriswong/Library/Caches/Mastermind/economic-network-native-reader-20261009")
TASK = CACHE / "nvda-sec-local-native-20261009"
STORE_ROOT = TASK / "source-store"
CAPTURE = CACHE / "nvda-sec-local-native-capture.json"
WITNESS = CACHE / "nvda-sec-local-native-relationship-witness.json"
CANDIDATE = TASK / "private-candidate.json"
INITIAL = TASK / "private-candidate-initial-unanchored.json"
SNAPSHOT_ID = "ffsecsrc_520d816415a2d1dbde1fcf348abef2cbfdd8b28b88b4bf847a549613002d02ee"
DESCRIPTOR = STORE_ROOT / f"fundamental_forensics/sec-source/v1/manifests/{SNAPSHOT_ID}.json"
EXPECTED = {
    CAPTURE: "3671954fc8d02dc2b58e68e705e249c6919ddaacfd8fad1a5e5af7a6620901b1",
    WITNESS: "bd3edbbe0c4fef9b85657b8aaf07b3f65cf271828ec8982eb8393ed29dc3a5cd",
    CANDIDATE: "9c84a90ebdd09e55fc3ffe9892609c77561eef9d8d0789951c6e289a3a5567be",
    INITIAL: "7e43671653aae7cba93346547a5f9ac827de0aa4bd32752bf3a70b98952f8cbc",
    DESCRIPTOR: "d9fd6566dfbecfc1b9de60c604fcb71c2f52f48ddaf3543c5279c89c698414b4",
}

# This is the already verified 68-path candidate dependency inventory plus the
# two additional scoped native test paths. These are names, not old code hashes.
# The new principal receipt must bind every current byte. No changing builder
# source was sampled to prepare this inventory.
REQUIRED_PATHS = frozenset("""
collectors/__init__.py
collectors/edgar_forensics.py
collectors/fundamental_forensics_acquisition.py
collectors/fundamental_forensics_companyfacts.py
collectors/sec_document_spine.py
collectors/sec_filing_parser.py
config/dataset_registry.yml
config/fundamental_forensics_disclosure_diff.v1.json
engine/__init__.py
engine/basket_breadth_divergence.py
engine/catalyst_tone.py
engine/company_intelligence/__init__.py
engine/company_intelligence/contracts.py
engine/company_intelligence/health.py
engine/company_intelligence/pinned_relationship_candidates.py
engine/company_intelligence/relationship_candidates.py
engine/company_intelligence/views.py
engine/desk_ledger.py
engine/earnings_release/__init__.py
engine/earnings_release/receipts.py
engine/fundamental_forensics/__init__.py
engine/fundamental_forensics/detectors.py
engine/fundamental_forensics/disclosure_diff.py
engine/fundamental_forensics/filing_attestation.py
engine/fundamental_forensics/filing_package.py
engine/fundamental_forensics/ixbrl_extraction.py
engine/fundamental_forensics/models.py
engine/fundamental_forensics/normalize.py
engine/fundamental_forensics/pipeline.py
engine/fundamental_forensics/sec_companyfacts.py
engine/fundamental_forensics/sec_document_spine.py
engine/fundamental_forensics/source_sync.py
engine/gdelt_client.py
engine/marketing/__init__.py
engine/marketing/accounts.py
engine/marketing/authority.py
engine/marketing/chart_render.py
engine/marketing/charter.py
engine/marketing/claims.py
engine/marketing/cmo.py
engine/marketing/departments.py
engine/marketing/economics.py
engine/marketing/events.py
engine/marketing/ledgers.py
engine/marketing/logo_cache.py
engine/marketing/opportunity_bus.py
engine/marketing/publication.py
engine/marketing/state.py
engine/master_brain.py
engine/research_vault/__init__.py
engine/research_vault/r2_store.py
lib/__init__.py
lib/config.py
lib/dataos/__init__.py
lib/dataos/identity.py
lib/dataos/nulls.py
lib/dataos/price.py
lib/dataos/quality.py
lib/dataos/registry.py
lib/dataos/temporal.py
research/theme_graph/economic_network_execution_20261009/MICRON_SOURCE_CASE.json
research/theme_graph/economic_network_execution_20261009/replay_micron_witness.py
scripts/__init__.py
scripts/worktree_sparse.py
tests/__init__.py
tests/conftest.py
tests/test_company_pinned_relationship_candidates.py
tests/test_company_relationship_candidates.py
tests/test_sec_document_spine.py
tests/test_fundamental_forensics_attestation.py
""".split())

FORBIDDEN_IMPORTS = ("collectors.sec_document_spine", "requests", "urllib3")
FIRST_PARTY_PREFIXES = frozenset({"engine", "collectors", "lib", "scripts", "tests"})
MAX_INPUT_BYTES = 1024 * 1024
MAX_CODE_BYTES = 8 * 1024 * 1024
MAX_OBJECT_BYTES = 64 * 1024 * 1024
PREMERGE_SCHEMA = "economic_network.frozen_source_candidate.v1"
POSTMERGE_SCHEMA = "economic_network.accepted_source_delivery.v1"
OBSERVATION = {
    "phase": "preflight",
    "source_phase": None,
    "code_receipt_sha256": None,
    "five_complete_outputs_equal": False,
    "tracked_files_unchanged": None,
    "task_store_directories_unchanged": None,
    "latest_pointer_absent": None,
    "blocked_events": [],
    "blocked_imports": [],
}


class ReplayVerificationError(RuntimeError):
    """Sanitized harness finding; messages never include source/candidate text."""


def require(condition, label):
    if not condition:
        raise ReplayVerificationError(label)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest_text(value, length):
    return (type(value) is str and bool(re.fullmatch(r"[0-9a-f]{%d}" % length, value))
            and value != "0" * length)


def safe_relative(value):
    require(type(value) is str and value and "\\" not in value and "\x00" not in value,
            "invalid relative path")
    parts = value.split("/")
    require(not value.startswith("/") and all(part not in {"", ".", ".."} for part in parts),
            "unsafe relative path")
    require(str(PurePosixPath(value)) == value, "noncanonical relative path")
    return parts


def real_directory_chain(path):
    for item in [*reversed(path.parents), path]:
        s = item.lstat()
        require(stat.S_ISDIR(s.st_mode), "non-directory or symlink in existing chain")


def checked_bytes(path, maximum):
    real_directory_chain(path.parent)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode), "tracked input is not a regular nonsymlink file")
    require(0 <= before.st_size <= maximum, "tracked input exceeds verification byte bound")
    with path.open("rb") as handle:
        content = handle.read(maximum + 1)
    after = path.lstat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    require(identity(before) == identity(after), "tracked input changed while reading")
    require(len(content) == before.st_size <= maximum, "tracked input size changed while reading")
    return content, (*identity(after), sha(content))


def file_state(path, maximum=MAX_OBJECT_BYTES):
    return checked_bytes(path, maximum)[1]


def directory_state(path):
    s = path.lstat()
    require(stat.S_ISDIR(s.st_mode), "existing directory changed type")
    return (s.st_dev, s.st_ino, s.st_mtime_ns)


def canonical_digest(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def read_json(content):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "duplicate JSON key in verification input")
            out[key] = value
        return out
    def constant(_value):
        raise ReplayVerificationError("nonfinite JSON verification input")
    value = json.loads(content.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    require(type(value) is dict, "verification input is not a JSON object")
    return value


def aware_clock(value):
    require(type(value) is str, "verification clock must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None,
            "verification clock is not an offset instant")
    return parsed


def source_binding(receipt, expected_phase):
    require(receipt.get("status") == "PASS" and receipt.get("working_tree_clean") is True,
            "principal source verification is not a clean PASS")
    require(receipt.get("code_root") == str(CODE_ROOT), "principal verification code root mismatch")
    require(receipt.get("repository") == "mastermindx-market-intelligence/macro",
            "principal verification repository mismatch")
    require(receipt.get("operation_id") == "gmi-economic-network-native-reader-20261009-pro-002",
            "principal verification operation mismatch")
    require(receipt.get("phase") == expected_phase, "source-verification phase mismatch")
    require(aware_clock(receipt.get("verified_at")) <= datetime.now(timezone.utc),
            "principal verification clock is in the future")
    for key in ("reviewed_head", "execution_workspace_head"):
        require(digest_text(receipt.get(key), 40), "invalid principal source commit")
    require(receipt["execution_workspace_head"] == receipt["reviewed_head"],
            "workspace is not the exact frozen reviewed commit")
    for key in ("native_fact_admission", "production_reader_custody", "historical_system_replay",
                "rights_admission", "served_product_proof", "predictive_authority"):
        require(receipt.get(key) is False, "source receipt makes an unauthorized production claim")
    if expected_phase == "PREMERGE_FROZEN_CANDIDATE":
        require(receipt.get("schema") == PREMERGE_SCHEMA, "wrong frozen-candidate receipt schema")
        for key in ("accepted_merge_sha", "fresh_upstream_sha", "merged_at"):
            require(key in receipt and receipt[key] is None, "premerge receipt claims merge evidence")
        require(receipt.get("upstream_contains_merge") is False, "premerge receipt claims accepted upstream")
        owned_equality = "reviewed_workspace_equal"
    else:
        require(expected_phase == "POSTMERGE_ACCEPTED_SOURCE", "unknown source phase")
        require(receipt.get("schema") == POSTMERGE_SCHEMA, "wrong accepted-source receipt schema")
        for key in ("accepted_merge_sha", "fresh_upstream_sha"):
            require(digest_text(receipt.get(key), 40), "missing accepted-source commit evidence")
        require(receipt.get("upstream_contains_merge") is True, "principal did not verify upstream containment")
        require(aware_clock(receipt.get("merged_at")) <= aware_clock(receipt["verified_at"]),
                "accepted-source verification predates claimed merge")
        require(type(receipt.get("pr")) is str and re.fullmatch(
            r"https://github[.]com/mastermindx-market-intelligence/macro/pull/[1-9][0-9]*",
            receipt["pr"]) is not None, "missing accepted-source carrier")
        owned_equality = "all_four_locations_equal"

    hashes = {}
    for key, count_key, equality_key in (
        ("owned_files", "owned_file_count", owned_equality),
        ("dependencies", "dependency_count", "all_locations_equal"),
    ):
        rows = receipt.get(key)
        require(type(rows) is list and rows and type(receipt.get(count_key)) is int
                and receipt[count_key] == len(rows), "source-verification inventory count mismatch")
        seen = set()
        for row in rows:
            require(type(row) is dict and row.get(equality_key) is True,
                    "source-verification row lacks required location equality")
            relative, digest = row.get("path"), row.get("sha256")
            safe_relative(relative)
            require(relative not in seen and digest_text(digest, 64), "invalid or duplicate source row")
            seen.add(relative)
            require(relative not in hashes or hashes[relative] == digest,
                    "owned/dependency source digest conflict")
            hashes[relative] = digest
    require(REQUIRED_PATHS <= hashes.keys(), "source receipt omits a required code or dependency path")
    return hashes


def boundary_leaf_counts(value):
    counts = {"null": 0, "false": 0}
    def visit(v):
        if isinstance(v, dict):
            for child in v.values():
                visit(child)
        elif isinstance(v, list):
            for child in v:
                visit(child)
        elif v is None:
            counts["null"] += 1
        elif v is False:
            counts["false"] += 1
    visit(value)
    return counts


def is_forbidden_import(name):
    return any(name == prefix or name.startswith(prefix + ".") for prefix in FORBIDDEN_IMPORTS)


def install_import_boundary(code_hashes):
    # A fresh interpreter is mandatory. Do not hide a dependency by inheriting its
    # initialized module or loading the pytest producer/fixture module here.
    require(not any(is_forbidden_import(name) for name in sys.modules),
            "forbidden acquisition module already initialized")
    require(not any(name.split(".")[0] in FIRST_PARTY_PREFIXES for name in sys.modules),
            "first-party modules already initialized; fresh process required")
    loaded = set()

    class VerifiedSourceLoader(importlib.machinery.SourceFileLoader):
        def get_code(self, fullname):
            path = Path(self.path)
            relative = path.relative_to(CODE_ROOT).as_posix()
            require(relative in code_hashes, "imported first-party source missing from binding")
            raw, state = checked_bytes(path, MAX_CODE_BYTES)
            require(state[-1] == code_hashes[relative], "first-party source changed before compilation")
            # Compile the exact checked .py bytes. -B alone prevents cache writes,
            # but does not prove that an existing .pyc was not read. This loader
            # preserves module semantics and exposes every import to the guard;
            # it never warms, substitutes, suppresses or stubs application code.
            loaded.add(relative)
            return self.source_to_code(raw, self.path)

    class ImportBoundary:
        def find_spec(self, fullname, path=None, target=None):
            if is_forbidden_import(fullname):
                OBSERVATION["blocked_imports"].append(fullname)
                raise ImportError("retained reader denied acquisition import")
            if fullname.split(".")[0] not in FIRST_PARTY_PREFIXES:
                return None
            spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
            require(spec is not None and type(spec.origin) is str,
                    "first-party import lacks an exact source origin")
            origin = Path(spec.origin)
            require(origin.is_relative_to(CODE_ROOT) and origin.suffix == ".py",
                    "first-party import resolves outside verified source")
            relative = origin.relative_to(CODE_ROOT).as_posix()
            require(relative in code_hashes, "first-party import is outside verified code inventory")
            require(type(spec.loader) is importlib.machinery.SourceFileLoader,
                    "first-party import has an unsupported source loader")
            spec.loader = VerifiedSourceLoader(fullname, str(origin))
            return spec

    boundary = ImportBoundary()
    sys.meta_path.insert(0, boundary)
    return boundary, loaded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-receipt", required=True)
    parser.add_argument("--source-receipt-sha256", required=True)
    parser.add_argument("--phase", required=True,
                        choices=("PREMERGE_FROZEN_CANDIDATE", "POSTMERGE_ACCEPTED_SOURCE"))
    args = parser.parse_args()
    require(digest_text(args.source_receipt_sha256, 64), "invalid pinned source-receipt digest")
    source_receipt_path = Path(args.source_receipt)
    require(source_receipt_path.is_absolute() and ".." not in source_receipt_path.parts
            and source_receipt_path.is_relative_to(CODE_EVIDENCE_ROOT),
            "source-verification receipt must be an existing native cache artifact")
    require(source_receipt_path not in EXPECTED, "source receipt cannot replace historical input")
    real_directory_chain(CODE_ROOT)
    real_directory_chain(STORE_ROOT)
    receipt_bytes, receipt_state = checked_bytes(source_receipt_path, MAX_INPUT_BYTES)
    require(receipt_state[-1] == args.source_receipt_sha256, "pinned source-receipt digest mismatch")
    receipt = read_json(receipt_bytes)
    code_hashes = source_binding(receipt, args.phase)
    OBSERVATION["source_phase"] = args.phase
    OBSERVATION["code_receipt_sha256"] = args.source_receipt_sha256

    inputs = {}
    tracked = {source_receipt_path}
    verified_states = {str(source_receipt_path): receipt_state}
    for path, expected in EXPECTED.items():
        content, state = checked_bytes(path, MAX_INPUT_BYTES)
        require(state[-1] == expected, "fixed historical input digest mismatch")
        inputs[path] = read_json(content)
        tracked.add(path)
        verified_states[str(path)] = state
    capture, witness, candidate = inputs[CAPTURE], inputs[WITNESS], inputs[CANDIDATE]
    descriptor = inputs[DESCRIPTOR]
    require(capture["task_root"] == str(TASK), "task-root mismatch")
    require(capture["snapshot_id"] == SNAPSHOT_ID == descriptor["snapshot_id"], "snapshot mismatch")
    require(witness["capture_receipt_sha256"] == EXPECTED[CAPTURE], "capture linkage mismatch")
    require(witness["evidence_class"] == "LOCAL_NATIVE_REPLAY", "historical evidence-class mismatch")

    # Descriptor bytes are pinned above. Its five entries bind the exact existing
    # retained objects, independently of any updated replay-code receipt.
    entries = [entry for tree in descriptor["trees"] for entry in tree["entries"]]
    require(len(entries) == 5, "retained object inventory changed")
    object_keys = set()
    for entry in entries:
        parts = safe_relative(entry["object_key"])
        require(entry["object_key"] not in object_keys, "duplicate retained object key")
        object_keys.add(entry["object_key"])
        path = STORE_ROOT.joinpath(*parts)
        require(type(entry["byte_length"]) is int and 0 <= entry["byte_length"] <= MAX_OBJECT_BYTES
                and digest_text(entry["sha256"], 64), "invalid retained object identity")
        fp = file_state(path)
        require(fp[2] == entry["byte_length"] and fp[-1] == entry["sha256"], "retained object mismatch")
        tracked.add(path)
        verified_states[str(path)] = fp

    # Historical code_sha256 is deliberately not a current-code requirement.
    # The root's independently verified receipt binds the current source instead.
    for relative, digest in code_hashes.items():
        path = CODE_ROOT.joinpath(*safe_relative(relative))
        state = file_state(path, MAX_CODE_BYTES)
        require(state[-1] == digest, "frozen replay-code digest mismatch")
        tracked.add(path)
        verified_states[str(path)] = state

    latest = STORE_ROOT / "fundamental_forensics/sec-source/v1/latest.json"
    require(not latest.exists() and not latest.is_symlink(), "unexpected native latest pointer")
    before = verified_states
    require(before == {str(p): file_state(p) for p in tracked}, "verified files changed before imports")
    directories = [TASK, STORE_ROOT]
    before_dirs = {str(p): directory_state(p) for p in directories}

    # These network/process and post-constructor filesystem denial predicates are
    # unchanged from the original failed strict replay. No event is cleared.
    guard = {"filesystem": False, "blocked_events": OBSERVATION["blocked_events"]}
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    mutation_events = {
        "os.mkdir", "os.rmdir", "os.remove", "os.rename", "os.link", "os.symlink",
        "os.chmod", "os.chown", "os.utime", "os.truncate", "os.setxattr", "os.removexattr",
        "shutil.copyfile", "shutil.copymode", "shutil.copystat", "shutil.rmtree",
    }
    def audit(event, values):
        deny = event.startswith(("socket.", "subprocess.", "os.exec", "os.spawn")) or event in {"os.system", "os.fork", "os.forkpty", "os.posix_spawn"}
        if guard["filesystem"]:
            deny = deny or event in mutation_events
            if event == "open":
                mode, flags = values[1], values[2]
                deny = deny or (isinstance(mode, str) and any(x in mode for x in "wax+")) or (isinstance(flags, int) and bool(flags & write_flags))
        if deny:
            guard["blocked_events"].append(event)
            raise PermissionError("read-only replay denied " + event)
    sys.addaudithook(audit)
    boundary, loaded_sources = install_import_boundary(code_hashes)
    sys.path.insert(0, str(CODE_ROOT))
    OBSERVATION["phase"] = "fresh first-party imports"
    from engine.research_vault.r2_store import LocalStore
    from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority
    from engine.company_intelligence.pinned_relationship_candidates import inspect_pinned_candidate
    from engine.company_intelligence.relationship_candidates import MAX_SOURCE_BYTES

    # LocalStore calls mkdir(exist_ok=True). Supply only the prechecked existing
    # directory, preserve the original boundary and immediately check its identity.
    OBSERVATION["phase"] = "existing LocalStore constructor"
    store = LocalStore(STORE_ROOT)
    require(before_dirs == {str(p): directory_state(p) for p in directories}, "constructor changed existing directories")
    guard["filesystem"] = True
    OBSERVATION["phase"] = "retained candidate replay"
    authority = PinnedSourceAuthority(store=store, snapshot_id=SNAPSHOT_ID)
    kwargs = dict(authority=authority, snapshot_id=SNAPSHOT_ID,
                  manifest_key=capture["manifest_key"], document_id=capture["document"]["document_id"],
                  maximum_bytes=MAX_SOURCE_BYTES, include_support_text=False)

    bad = copy.deepcopy(candidate)
    bad["document"]["version"] = "sha256:" + "0" * 64
    unanchored = copy.deepcopy(candidate)
    unanchored["candidate_id"] = "manual:nvda:2026-10k:foundry-roster:unanchored-probe"
    unanchored["assertion"].update(subject_label="NVIDIA", object_label="TSMC; Samsung", product_scope="semiconductor wafer manufacturing")
    actual = {
        "current": inspect_pinned_candidate(candidate, **kwargs),
        "historical": inspect_pinned_candidate(candidate, **kwargs, as_of="2026-02-26T00:00:00Z"),
        "candidate_metadata_mismatch": inspect_pinned_candidate(bad, **kwargs),
        "missing_document_selector": inspect_pinned_candidate(candidate, **{**kwargs, "document_id": kwargs["document_id"] + "-missing-probe"}),
        "unsupported_source_labels": inspect_pinned_candidate(unanchored, **kwargs),
    }
    OBSERVATION["phase"] = "post-replay verification"
    require(set(actual) == set(witness["outcomes"]), "five-outcome inventory mismatch")
    for name, result in actual.items():
        require(result == witness["outcomes"][name], "complete output mismatch: " + name)
        require(result["admission"] == "NOT_ADMITTED" and result["graph1_projection"] is None, "admission boundary changed")
        require(all(v is False for v in result["authority"].values()), "authority boundary changed")
        if name != "current":
            require(result["native_source_binding"] is None, "refusal exposed native binding")
    for field in ("current_candidate_view", "source_provenance", "support"):
        require(actual["historical"]["candidate_inspection"][field] is None, "historical disclosure boundary changed")
    OBSERVATION["five_complete_outputs_equal"] = True
    require(before == {str(p): file_state(p) for p in tracked}, "tracked source or input changed")
    OBSERVATION["tracked_files_unchanged"] = len(tracked)
    require(before_dirs == {str(p): directory_state(p) for p in directories}, "task/store directory changed")
    OBSERVATION["task_store_directories_unchanged"] = True
    require(not latest.exists() and not latest.is_symlink(), "latest pointer appeared")
    OBSERVATION["latest_pointer_absent"] = True
    require(not guard["blocked_events"], "replay attempted a forbidden side effect")
    require(not OBSERVATION["blocked_imports"], "replay attempted a forbidden acquisition import")
    require(not any(is_forbidden_import(name) for name in sys.modules), "forbidden acquisition module became initialized")
    require(sys.meta_path[0] is boundary, "reader changed the installed import boundary")

    print(json.dumps({
        "schema": "economic_network.repaired_reader_local_native_replay.v1",
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "evidence_class": "LOCAL_NATIVE_REPLAY",
        "source_phase": args.phase,
        "replay_code_binding": {
            "principal_verification_receipt_sha256": args.source_receipt_sha256,
            "principal_receipt_schema": receipt["schema"],
            "reviewed_head_from_principal_receipt": receipt["reviewed_head"],
            "accepted_merge_sha_from_principal_receipt": receipt["accepted_merge_sha"],
            "fresh_upstream_sha_from_principal_receipt": receipt["fresh_upstream_sha"],
            "verified_at_from_principal_receipt": receipt["verified_at"],
            "github_merge_independently_verified_by_this_harness": False,
            "code_root": str(CODE_ROOT),
            "locally_verified_code_paths": len(code_hashes),
            "current_code_sha256_manifest_digest": canonical_digest(code_hashes),
            "first_party_sources_compiled_from_verified_bytes": sorted(loaded_sources),
            "first_party_bytecode_cache_used": False,
            "third_party_runtime_fully_pinned": False,
        },
        "historical_capture_provenance": {
            "capture_sha256": EXPECTED[CAPTURE],
            "saved_witness_sha256": EXPECTED[WITNESS],
            "capture_code_head": capture["code_head"],
            "capture_code_sha256": capture["code_sha256"],
            "witness_code_head": witness["code_head"],
            "witness_candidate_module_sha256": witness["candidate_module_sha256"],
            "witness_pinned_adapter_sha256": witness["pinned_adapter_sha256"],
            "historical_code_hashes_reclassified_as_current": False,
        },
        "snapshot_id": SNAPSHOT_ID,
        "five_complete_outputs_equal": True,
        "outcomes": {name: {"inspection_status": result["inspection_status"],
            "refusal_code": (result["refusal"] or {}).get("code"),
            "complete_output_sha256": canonical_digest(result),
            "preserved_boundary_leaf_counts": boundary_leaf_counts(result)} for name, result in actual.items()},
        "tracked_files_unchanged": len(tracked),
        "task_store_directories_unchanged": True,
        "forbidden_acquisition_imports": list(FORBIDDEN_IMPORTS),
        "blocked_import_attempts": OBSERVATION["blocked_imports"],
        "network_and_process_creation_blocked": True,
        "filesystem_mutations_blocked_after_existing_LocalStore_constructor": True,
        "blocked_side_effect_attempts": OBSERVATION["blocked_events"],
        "latest_pointer_absent": True,
        "prior_strict_failure_reclassified": False,
        "production_owner_custody": False,
        "native_fact_admission": False,
        "historical_system_replay": False,
        "rights_admission": False,
        "served_product_proof": False,
        "predictive_authority": False,
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # A sanitized failure receipt preserves denied events and partial proof.
        # No source/candidate body, audit argument, or arbitrary SDK message leaks.
        print(json.dumps({
            "schema": "economic_network.repaired_reader_local_native_replay.v1",
            "status": "FAIL",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "failure": str(exc) if type(exc) is ReplayVerificationError else type(exc).__name__,
            "observation": OBSERVATION,
            "production_owner_custody": False,
            "native_fact_admission": False,
            "historical_system_replay": False,
            "rights_admission": False,
            "served_product_proof": False,
            "predictive_authority": False,
        }, sort_keys=True, indent=2))
        raise SystemExit(1)
