#!/usr/bin/env python3
"""PREPARED ONLY: retained Micron/NVIDIA review-set CLI verification.

The principal must first freeze source, bind all code/input bytes, materialize
the new proof inputs, and authorize execution. This script performs no capture,
Git, registry creation, source/store edits, credential factory, or provider call.
Guarded children execute the real module CLI with runpy in fresh Python -B
processes. Separately labelled literal -m calls prove advertised-command behavior
without claiming that those ordinary calls carry the pre-import guard/loader.

The parent may write one explicitly requested, exclusive private evidence file
after its read-only child runs. No private source/candidate/result body is sent
to the parent's public stdout. Original source inputs are never written.
"""

import argparse
import contextlib
import copy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.machinery
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import runpy
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
CODE_ROOT = Path('/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-network-native-reader-20261009-pro-002')
CACHE = Path('/Users/chriswong/Library/Caches/Mastermind/economic-network-20261009')
CODE_EVIDENCE_ROOT = Path('/Users/chriswong/Library/Caches/Mastermind/economic-network-native-reader-20261009')
PROOF_ROOT = CODE_EVIDENCE_ROOT / 'pro-002-review-set-real'
INPUT_ROOT = PROOF_ROOT / 'inputs'
TASK = CACHE / 'nvda-sec-local-native-20261009'
STORE_ROOT = TASK / 'source-store'
MODULE = 'engine.company_intelligence.relationship_candidates'
OPERATION_ID = 'gmi-economic-network-native-reader-20261009-pro-002'
SNAPSHOT_ID = 'ffsecsrc_520d816415a2d1dbde1fcf348abef2cbfdd8b28b88b4bf847a549613002d02ee'
DESCRIPTOR = STORE_ROOT / f'fundamental_forensics/sec-source/v1/manifests/{SNAPSHOT_ID}.json'
NVDA_SHA = '94f539316ae2a9ff625357cf01008cb77b930d1a6a228326f04a3ce5f5a56d2e'
MICRON_SHA = 'a7efabf9cec581ba684688368118e3e13df6a3043aff56667927e24df97e8b2e'
NVDA_BYTES = 1967931
MICRON_BYTES = 504119
MICRON_SOURCE = CACHE / f'micron-hbm3e-{MICRON_SHA}.html'
MICRON_CANDIDATE = CACHE / 'micron-manual-candidate.json'
MICRON_WITNESS = CACHE / 'micron-complete-witness.json'
CASE_PATH = CODE_ROOT / 'research/theme_graph/economic_network_execution_20261009/MICRON_SOURCE_CASE.json'
LEGACY_HARNESS = CASE_PATH.with_name('replay_micron_witness.py')
NVDA_CANDIDATE = TASK / 'private-candidate.json'
NVDA_SOURCE = INPUT_ROOT / f'nvda-retained-{NVDA_SHA}.html'
INVALID_CANDIDATE = INPUT_ROOT / 'invalid-candidate.json'
MISSING_SOURCE = INPUT_ROOT / 'deliberately-missing-source.html'
CURRENT_MANIFEST = INPUT_ROOT / 'review-current.json'
REORDERED_MANIFEST = INPUT_ROOT / 'review-reordered.json'
MISSING_MANIFEST = INPUT_ROOT / 'review-missing-single.json'
HISTORICAL_AS_OF = '2024-02-26T12:00:00Z'
REVIEW_SET_ID = 'retained-micron-nvda-mixed-v1'
INVALID_BYTES = b'{"schema":"invalid"}\n'
PREMERGE_SCHEMA = 'economic_network.frozen_source_candidate.v1'
POSTMERGE_SCHEMA = 'economic_network.accepted_source_delivery.v1'
INPUT_RECEIPT_SCHEMA = 'economic_network.retained_review_set_inputs.v1'
MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_CODE_BYTES = 8 * 1024 * 1024
MAX_OBJECT_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024
FORBIDDEN_IMPORTS = ('collectors', 'requests', 'urllib3', 'httpx', 'aiohttp',
                     'boto3', 'botocore', 'urllib.request', 'http.client')
FIRST_PARTY_PREFIXES = frozenset({'engine', 'collectors', 'lib', 'scripts', 'tests'})
OBSERVATION = {'blocked_imports': [], 'blocked_events': [], 'phase': 'preflight'}
PRIVATE_RUNS = {}

EXPECTED_CURRENT_CODE = {
    'engine/company_intelligence/relationship_candidates.py': 'a558922c0586a5532f3912524b48f3cf592c3c6c9c21f689e3d416976e9cae55',
    'engine/fundamental_forensics/sec_document_spine.py': 'ee240863943823e598083f45164c6a288e9098292a47a454cc70898c2bdf8366',
    'collectors/sec_document_spine.py': '1c6fec647373372858f4ad5fc0b6a88d9da84d605f5d14e8e148ac2ee7e8a3e5',
    'engine/fundamental_forensics/filing_attestation.py': '1b2693a9bbff66761a573a8c1bd5d32b352a2d43719407e2864fda6e725d0a47',
    'engine/company_intelligence/pinned_relationship_candidates.py': 'afafacb978face2775c769844a2773e04a5cb5b755aacd6c9724d7e51eb07cb7',
    'tests/test_sec_document_spine.py': '050022e3e0d39ec644763d4b9377a3386bde7a81e33dbcf4495f5cc4cbd8f4bb',
    'tests/test_company_pinned_relationship_candidates.py': '08fa9e22f7c35681b2fd97ccd97796a01a98988b05b8d047c8368ff24f6eb669',
    'tests/test_company_relationship_review_set.py': '67636cc6eca4f9be84b383bb44b4835a3dc8447f6b288e2e99073f61182ce212',
}

# Frozen historical files. Their acquisition-code fields remain historical.
# The byte lengths are checked against the principal's input inventory as well.
ORIGINAL_FILES = {
    'micron_source': (MICRON_SOURCE, MICRON_SHA),
    'micron_candidate': (MICRON_CANDIDATE, '5e2a2c789599e5e146b6e2969ccc243ee5c85b7d74c67af76b7c437857c4383c'),
    'micron_fetch_receipt': (CACHE / 'micron-source-receipt.json', '8cc69451d1c13ee29031c2dae38a14aaaefbfc92347255d92fde3c3243ab6066'),
    'micron_complete_witness': (MICRON_WITNESS, 'c513033323e52705a007545f826a2fa2d938d08d7151eeb14bb4aca3e78c4747'),
    'micron_postmerge_witness': (CACHE / 'postmerge-micron-replay.json', 'c513033323e52705a007545f826a2fa2d938d08d7151eeb14bb4aca3e78c4747'),
    'micron_initial_current': (CACHE / 'micron-current-inspection.json', 'a4539e94a3978b941930c36734061214cebe5480e946be91edcb0fb9ef775d4f'),
    'micron_initial_historical': (CACHE / 'micron-historical-inspection.json', 'ef83ca39a5a97d952f1ac7996a6f74eaa91e6c7250a5ce0088a62104fb42873b'),
    'micron_source_case': (CASE_PATH, 'dd72d31afce12ca727a171e6f635d7085c8c2d6bff6bea2750f9c29a04fe101b'),
    'micron_legacy_harness': (LEGACY_HARNESS, '69da2f393711923be68f05b1da563dbbcb736761fa60a8bf5ea4aa6cbf9f1830'),
    'nvda_capture': (CACHE / 'nvda-sec-local-native-capture.json', '3671954fc8d02dc2b58e68e705e249c6919ddaacfd8fad1a5e5af7a6620901b1'),
    'nvda_witness': (CACHE / 'nvda-sec-local-native-relationship-witness.json', 'bd3edbbe0c4fef9b85657b8aaf07b3f65cf271828ec8982eb8393ed29dc3a5cd'),
    'nvda_candidate': (NVDA_CANDIDATE, '9c84a90ebdd09e55fc3ffe9892609c77561eef9d8d0789951c6e289a3a5567be'),
    'nvda_initial_candidate': (TASK / 'private-candidate-initial-unanchored.json', '7e43671653aae7cba93346547a5f9ac827de0aa4bd32752bf3a70b98952f8cbc'),
    'nvda_descriptor': (DESCRIPTOR, 'd9fd6566dfbecfc1b9de60c604fcb71c2f52f48ddaf3543c5279c89c698414b4'),
}

CURRENT_COUNTS = {
    'requested_cases': 4, 'supplied_source_cases': 3,
    'unique_supplied_source_byte_digests': 2, 'inspectable_cases': 2,
    'refused_cases': 1, 'unavailable_cases': 1, 'not_known_as_of_cases': 0,
}
HISTORICAL_COUNTS = {**CURRENT_COUNTS, 'inspectable_cases': 0, 'refused_cases': 3}
PROCESSING = {'requested_cases': 4, 'prepared_cases': 4, 'processed_cases': 4,
              'inspector_calls': 3, 'retained_case_results': 4}

# Shared source-verification schema and verified import loader follow. These
# definitions are copied unchanged from the separately prepared strict NVIDIA
# verifier; this script does not execute that verifier or its pinned API calls.


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


REQUIRED_PATHS = REQUIRED_PATHS | frozenset({'tests/test_company_relationship_review_set.py'})


def absolute_path(value, *, within=None):
    require(type(value) is str and value and '\x00' not in value,
            'invalid absolute verification path')
    path = Path(value)
    require(path.is_absolute() and str(path) == value
            and all(part not in {'.', '..'} for part in path.parts),
            'verification path is not physical absolute syntax')
    require('reader_builder_evidence' not in path.parts,
            'reserved evidence path is excluded')
    if within is not None:
        require(path.is_relative_to(within), 'verification path outside assigned proof root')
    return path


def checked_bytes(path, maximum):
    """Descriptor-relative regular-file read through nonsymlink components."""
    path = absolute_path(str(path))
    directory_fd = file_fd = None
    try:
        directory_fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for part in path.parts[1:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                              dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(path.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                          dir_fd=directory_fd)
        before = os.fstat(file_fd)
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum,
                'verification input is not bounded regular bytes')
        with os.fdopen(file_fd, 'rb') as stream:
            file_fd = None
            content = stream.read(maximum + 1)
            after = os.fstat(stream.fileno())
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(identity(before) == identity(after) and len(content) == before.st_size,
                'verification input changed while reading')
        require(identity(path.lstat()) == identity(after), 'verification path identity changed')
        real_directory_chain(path.parent)
        return content, (*identity(after), sha(content))
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def file_state(path, maximum=MAX_OBJECT_BYTES):
    return checked_bytes(path, maximum)[1]


def tree_state(root):
    real_directory_chain(root)
    state, total = {}, 0
    for directory, names, files in os.walk(root, followlinks=False):
        names.sort()
        files.sort()
        parent = Path(directory)
        for path in [parent, *(parent / name for name in names)]:
            s = path.lstat()
            require(stat.S_ISDIR(s.st_mode), 'protected tree contains a non-directory link')
            state[str(path)] = ('directory', s.st_dev, s.st_ino, s.st_mtime_ns, s.st_ctime_ns)
        for name in files:
            path = parent / name
            key = file_state(path)
            total += key[2]
            state[str(path)] = ('file', *key)
        require(len(state) <= 256 and total <= 128 * 1024 * 1024,
                'protected verification tree exceeds bounded inventory')
    return state


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def cohort_cases():
    return [
        {'case_id': '01-micron-positive', 'candidate_file': str(MICRON_CANDIDATE),
         'source_file': str(MICRON_SOURCE)},
        {'case_id': '02-nvda-positive', 'candidate_file': str(NVDA_CANDIDATE),
         'source_file': str(NVDA_SOURCE)},
        {'case_id': '03-missing-source', 'candidate_file': str(MICRON_CANDIDATE),
         'source_file': str(MISSING_SOURCE)},
        {'case_id': '04-invalid-candidate', 'candidate_file': str(INVALID_CANDIDATE),
         'source_file': str(MICRON_SOURCE)},
    ]


def manifest_recipe():
    """Expected future principal-created bytes; this function writes nothing."""
    value = {'schema': 'company_intelligence.relationship_review_files/v1',
             'review_set_id': REVIEW_SET_ID, 'cases': cohort_cases()}
    reverse = {'cases': list(reversed(value['cases'])), 'review_set_id': REVIEW_SET_ID,
               'schema': value['schema']}
    missing = {**value, 'review_set_id': REVIEW_SET_ID + ':missing-only',
               'cases': [value['cases'][2]]}
    return {
        CURRENT_MANIFEST: canonical_bytes(value) + b'\n',
        REORDERED_MANIFEST: (json.dumps(reverse, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
        MISSING_MANIFEST: canonical_bytes(missing) + b'\n',
    }


def immutable_check(context):
    require(context['states'] == {path: file_state(Path(path)) for path in context['states']},
            'source code or original/proof input changed')
    require(context['trees'] == {str(root): tree_state(root) for root in (TASK, INPUT_ROOT)},
            'protected source/proof-input tree changed')
    require(not os.path.lexists(MISSING_SOURCE), 'negative missing-source path appeared')
    require(not os.path.lexists(STORE_ROOT / 'fundamental_forensics/sec-source/v1/latest.json'),
            'native latest pointer appeared')


def preflight(args):
    self_path = absolute_path(str(Path(__file__).absolute()), within=PROOF_ROOT)
    source_path = absolute_path(args.source_receipt, within=CODE_EVIDENCE_ROOT)
    input_path = absolute_path(args.input_receipt, within=PROOF_ROOT)
    for value in (args.harness_sha256, args.source_receipt_sha256, args.input_receipt_sha256):
        require(digest_text(value, 64), 'invalid principal-pinned artifact digest')
    if args.private_output is not None:
        target = absolute_path(args.private_output, within=PROOF_ROOT / 'results')
        real_directory_chain(target.parent)
        require(not os.path.lexists(target), 'private evidence target must be absent before any child launch')
    real_directory_chain(CODE_ROOT)
    real_directory_chain(INPUT_ROOT)
    states, raw_by_path = {}, {}

    def take(path, digest, maximum=MAX_INPUT_BYTES):
        raw, state = checked_bytes(path, maximum)
        require(state[-1] == digest, 'required file digest mismatch')
        if str(path) in states:
            require(states[str(path)] == state, 'repeated input changed during preflight')
        states[str(path)] = state
        raw_by_path[str(path)] = raw
        return raw

    take(self_path, args.harness_sha256, MAX_CODE_BYTES)
    source_receipt = read_json(take(source_path, args.source_receipt_sha256))
    code_hashes = source_binding(source_receipt, args.phase)
    for relative, expected in EXPECTED_CURRENT_CODE.items():
        require(code_hashes.get(relative) == expected, 'principal receipt does not bind reviewed consumer/repair')
    for relative, expected in code_hashes.items():
        take(CODE_ROOT.joinpath(*safe_relative(relative)), expected, MAX_CODE_BYTES)

    input_receipt = read_json(take(input_path, args.input_receipt_sha256))
    require(set(input_receipt) == {
        'schema', 'status', 'operation_id', 'proof_root', 'verified_at',
        'source_receipt_sha256', 'harness_sha256', 'files', 'absent_paths',
        'nvda_derivation', 'source_capture_performed', 'original_inputs_modified',
    }, 'input receipt is not the required closed verification envelope')
    require(input_receipt['schema'] == INPUT_RECEIPT_SCHEMA
            and input_receipt['status'] == 'VERIFIED_INPUT_BYTES'
            and input_receipt['operation_id'] == OPERATION_ID
            and input_receipt['proof_root'] == str(PROOF_ROOT), 'input receipt context mismatch')
    require(input_receipt['source_receipt_sha256'] == args.source_receipt_sha256
            and input_receipt['harness_sha256'] == args.harness_sha256,
            'input receipt does not bind this source receipt and harness')
    require(aware_clock(input_receipt['verified_at']) <= datetime.now(timezone.utc),
            'input verification timestamp is in the future')
    require(input_receipt['source_capture_performed'] is False
            and input_receipt['original_inputs_modified'] is False,
            'input preparation changed the retained-source contract')
    require(input_receipt['absent_paths'] == [str(MISSING_SOURCE)]
            and not os.path.lexists(MISSING_SOURCE), 'missing-source control must remain absent')

    expected_files = {role: (path, digest, 'retained_original')
                      for role, (path, digest) in ORIGINAL_FILES.items()}
    for path, digest in ORIGINAL_FILES.values():
        take(path, digest)
    descriptor = read_json(raw_by_path[str(DESCRIPTOR)])
    capture = read_json(raw_by_path[str(ORIGINAL_FILES['nvda_capture'][0])])
    require(descriptor['snapshot_id'] == capture['snapshot_id'] == SNAPSHOT_ID,
            'retained snapshot linkage changed')
    require(capture['task_root'] == str(TASK)
            and capture['document']['content_sha256'] == NVDA_SHA
            and capture['document']['byte_length'] == NVDA_BYTES, 'retained capture identity changed')
    entries = [entry for tree in descriptor['trees'] for entry in tree['entries']]
    require(len(entries) == 5, 'retained descriptor no longer binds exactly five objects')
    seen, compressed_entry = set(), None
    for index, entry in enumerate(entries, 1):
        key = entry['object_key']
        safe_relative(key)
        require(key not in seen and digest_text(entry['sha256'], 64), 'invalid retained object binding')
        seen.add(key)
        path = STORE_ROOT / key
        raw = take(path, entry['sha256'], MAX_OBJECT_BYTES)
        require(type(entry['byte_length']) is int and len(raw) == entry['byte_length'],
                'retained object length mismatch')
        expected_files[f'nvda_store_object_{index}'] = (path, entry['sha256'], 'retained_original')
        if entry['relative_path'] == f'objects/sha256/94/{NVDA_SHA}.bin.gz':
            require(compressed_entry is None, 'ambiguous retained NVIDIA archive object')
            compressed_entry = entry
    require(compressed_entry is not None, 'retained NVIDIA gzip object missing')
    compressed = raw_by_path[str(STORE_ROOT / compressed_entry['object_key'])]
    with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode='rb') as stream:
        nvda_raw = stream.read(MAX_INPUT_BYTES + 1)
    require(len(nvda_raw) == NVDA_BYTES and sha(nvda_raw) == NVDA_SHA,
            'bounded retained decompression differs from historical source')
    require(nvda_raw.decode('utf-8').encode('utf-8') == nvda_raw,
            'retained NVIDIA bytes are not an exact UTF-8 roundtrip')
    derivation = {
        'method': 'bounded_gzip_decompression_of_retained_pinned_object',
        'descriptor_sha256': ORIGINAL_FILES['nvda_descriptor'][1],
        'object_key': compressed_entry['object_key'],
        'compressed_sha256': compressed_entry['sha256'],
        'compressed_bytes': compressed_entry['byte_length'],
        'raw_sha256': NVDA_SHA, 'raw_bytes': NVDA_BYTES, 'utf8_roundtrip': True,
    }
    require(input_receipt['nvda_derivation'] == derivation, 'principal derivation binding mismatch')
    require(take(NVDA_SOURCE, NVDA_SHA) == nvda_raw, 'derived NVIDIA file is not the exact retained raw bytes')
    expected_files['nvda_derived_utf8_source'] = (NVDA_SOURCE, NVDA_SHA, 'derived_exact_retained_bytes')
    require(take(INVALID_CANDIDATE, sha(INVALID_BYTES)) == INVALID_BYTES,
            'invalid-candidate control bytes changed')
    expected_files['invalid_candidate_control'] = (INVALID_CANDIDATE, sha(INVALID_BYTES), 'negative_control')
    for role, path in (('current_manifest', CURRENT_MANIFEST), ('reordered_manifest', REORDERED_MANIFEST),
                       ('missing_single_manifest', MISSING_MANIFEST)):
        expected = manifest_recipe()[path]
        require(take(path, sha(expected)) == expected, 'explicit manifest recipe changed')
        expected_files[role] = (path, sha(expected), 'review_manifest')
    require(sha(raw_by_path[str(CURRENT_MANIFEST)]) != sha(raw_by_path[str(REORDERED_MANIFEST)]),
            'manifest permutation/formatting control is not distinct')

    rows = input_receipt['files']
    require(type(rows) is list and len(rows) == len(expected_files), 'input inventory count mismatch')
    roles = set()
    for row in rows:
        require(type(row) is dict and set(row) == {'role', 'path', 'sha256', 'bytes', 'origin'},
                'input inventory row shape mismatch')
        role = row['role']
        require(type(role) is str and role in expected_files and role not in roles,
                'input inventory role missing, duplicated or unexpected')
        roles.add(role)
        path, digest, origin = expected_files[role]
        require(row['path'] == str(path) and row['sha256'] == digest and row['origin'] == origin,
                'principal input row differs from fixed source or control')
        require(type(row['bytes']) is int and row['bytes'] == len(raw_by_path[str(path)]),
                'principal input byte length mismatch')
    require(roles == set(expected_files), 'principal input inventory incomplete')

    micron = raw_by_path[str(MICRON_SOURCE)]
    case = read_json(raw_by_path[str(CASE_PATH)])
    require(len(micron) == MICRON_BYTES and micron.decode('utf-8').encode('utf-8') == micron,
            'Micron source bytes or encoding changed')
    require((case['char_start'], case['char_end'], case['byte_start'], case['byte_end'])
            == (370876, 371258, 370936, 371320), 'authoritative Micron replay coordinates changed')
    require(case['raw_sha256'] == MICRON_SHA and case['source_bytes'] == MICRON_BYTES
            and case['historical_probe'] == HISTORICAL_AS_OF, 'Micron source-case identity changed')
    require(sha(micron[370936:371320]) == case['span_sha256']
            == 'f79bce81f656e826b3aa74380eb9a2b63bf74fc0e60376dc2b40c64600eb890a',
            'Micron byte-span identity changed')
    # The original fetch receipt's exploratory 1483/1618 coordinates are kept
    # intact. They are not the subsequent authoritative replay-span contract.
    context = {'self_path': self_path, 'source_receipt': source_receipt,
               'input_receipt': input_receipt, 'code_hashes': code_hashes,
               'states': states, 'raw': raw_by_path, 'case': case,
               'trees': {str(root): tree_state(root) for root in (TASK, INPUT_ROOT)}}
    immutable_check(context)
    return context


def install_guards(code_hashes):
    # Manual file CLI needs no LocalStore constructor. All filesystem mutation
    # denial is active before the first application import in every guarded child.
    guard = {'filesystem': True, 'blocked_events': OBSERVATION['blocked_events']}
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    mutation_events = {
        'os.mkdir', 'os.rmdir', 'os.remove', 'os.rename', 'os.link', 'os.symlink',
        'os.chmod', 'os.chown', 'os.utime', 'os.truncate', 'os.setxattr', 'os.removexattr',
        'shutil.copyfile', 'shutil.copymode', 'shutil.copystat', 'shutil.rmtree',
    }
    def audit(event, values):
        deny = event.startswith(('socket.', 'subprocess.', 'os.exec', 'os.spawn')) or event in {'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn'}
        if guard['filesystem']:
            deny = deny or event in mutation_events
            if event == 'open':
                mode, flags = values[1], values[2]
                deny = deny or (isinstance(mode, str) and any(x in mode for x in 'wax+')) or (isinstance(flags, int) and bool(flags & write_flags))
        if deny:
            guard['blocked_events'].append(event)
            raise PermissionError('read-only replay denied ' + event)
    sys.addaudithook(audit)
    boundary, loaded = install_import_boundary(code_hashes)
    sys.path.insert(0, str(CODE_ROOT))
    return boundary, loaded


def cli_jobs():
    micron = ['--candidate', str(MICRON_CANDIDATE), '--source', str(MICRON_SOURCE)]
    nvda = ['--candidate', str(NVDA_CANDIDATE), '--source', str(NVDA_SOURCE)]
    invalid = ['--candidate', str(INVALID_CANDIDATE), '--source', str(MICRON_SOURCE)]
    return {
        'micron_current': micron, 'nvda_current': nvda, 'invalid_current': invalid,
        'micron_historical': micron + ['--as-of', HISTORICAL_AS_OF],
        'nvda_historical': nvda + ['--as-of', HISTORICAL_AS_OF],
        'invalid_historical': invalid + ['--as-of', HISTORICAL_AS_OF],
        'missing_single': ['--review-set', str(MISSING_MANIFEST)],
        'review_current': ['--review-set', str(CURRENT_MANIFEST)],
        'review_reordered': ['--review-set', str(REORDERED_MANIFEST)],
        'review_historical': ['--review-set', str(CURRENT_MANIFEST), '--as-of', HISTORICAL_AS_OF],
    }


def regenerate_micron(context):
    # This is its own fresh guarded child; no CLI process is prewarmed by it.
    from engine.earnings_release.receipts import receipt_for_char_span
    case = context['case']
    source = context['raw'][str(MICRON_SOURCE)].decode('utf-8')
    receipt = receipt_for_char_span(source=source, source_sha256=case['raw_sha256'],
                                    char_start=case['char_start'], char_end=case['char_end'])
    require((receipt.span_sha256, receipt.byte_start, receipt.byte_end)
            == (case['span_sha256'], case['byte_start'], case['byte_end']),
            'native Micron receipt regeneration differs from original replay contract')
    candidate = {
        'schema': 'company_intelligence.relationship_candidate/v1',
        'candidate_id': case['candidate_id'],
        'document': {'document_id': case['document_id'], 'version': 'sha256:' + case['raw_sha256'],
                     'source_ref': case['source_url'], 'published_date': case['published_date']},
        'dataset_id': None, 'temporal_row': None, 'receipt': receipt.to_dict(),
        'assertion': case['assertion'],
        'revision': {'supersedes_candidate_id': None, 'relation': 'original'},
        'identity_annotations': None,
    }
    original = read_json(context['raw'][str(MICRON_CANDIDATE)])
    require(candidate == original, 'complete regenerated Micron candidate differs from retained candidate')
    return {'complete_candidate_equal': True, 'canonical_candidate_sha256': canonical_digest(candidate),
            'span_sha256': receipt.span_sha256, 'original_private_candidate_written': False,
            'regeneration_contract': 'unchanged_original_replay_micron_witness.py'}


def child_main(args):
    context = preflight(args)
    cwd_before = os.getcwd()
    boundary, loaded = install_guards(context['code_hashes'])
    output, errors = io.StringIO(), io.StringIO()
    OBSERVATION['phase'] = args.child
    if args.child == 'regenerate_micron':
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            regeneration = regenerate_micron(context)
        require(not output.getvalue() and not errors.getvalue(), 'unexpected regeneration output')
        result = {'regeneration': regeneration}
    else:
        require(args.child in cli_jobs(), 'unknown guarded CLI journey')
        previous_argv = sys.argv
        sys.argv = [MODULE, *cli_jobs()[args.child]]
        exit_code = None
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                try:
                    runpy.run_module(MODULE, run_name='__main__', alter_sys=True)
                except SystemExit as exc:
                    exit_code = exc.code
        finally:
            sys.argv = previous_argv
        raw = output.getvalue().encode('utf-8')
        PRIVATE_RUNS['cli_capture'] = {'exit_code': exit_code,
                                       'stdout': output.getvalue(), 'stderr': errors.getvalue()}
        require(type(exit_code) is int and len(raw) <= MAX_OUTPUT_BYTES,
                'actual CLI did not produce bounded JSON and an integer exit')
        require(errors.getvalue() == '', 'actual guarded CLI produced stderr')
        result = {'exit_code': exit_code, 'stdout_sha256': sha(raw), 'stdout_bytes': len(raw),
                  'stderr_empty': True, 'result': read_json(raw)}
    immutable_check(context)
    require(os.getcwd() == cwd_before, 'guarded consumer changed process working directory')
    require(sys.meta_path[0] is boundary and not OBSERVATION['blocked_imports']
            and not OBSERVATION['blocked_events'], 'guarded consumer attempted a forbidden effect or import')
    require(not any(is_forbidden_import(name) for name in sys.modules),
            'forbidden acquisition module initialized in guarded consumer')
    return {'schema': 'economic_network.guarded_review_cli_child.v1', 'status': 'PASS',
            'job': args.child, 'launch': 'fresh_python_-B_script_then_runpy_module_as___main__',
            'first_party_sources_compiled_from_verified_bytes': sorted(loaded),
            'first_party_bytecode_cache_used': False,
            'blocked_import_attempts': list(OBSERVATION['blocked_imports']),
            'blocked_side_effect_attempts': list(OBSERVATION['blocked_events']),
            'filesystem_guard_active_before_application_import': True,
            'third_party_runtime_fully_pinned': False, **result}


def assertion_boundaries(result, *, historical=False):
    require(result['admission'] == 'NOT_ADMITTED' and result['graph1_projection'] is None,
            'inspection admission/Graph1 boundary changed')
    authority = result['authority']
    require(type(authority) is dict and set(authority) == {'rank', 'gate', 'size', 'trade', 'prediction'}
            and all(value is False for value in authority.values()), 'inspection authority changed')
    require(result['temporal']['historical_system_replay'] is False,
            'inspection fabricates historical system replay')
    boundary = result['content_boundary']
    require(boundary['public_export'] == 'NOT_AUTHORIZED'
            and boundary['quote_free_payload'] == 'NOT_CERTIFIED'
            and boundary['public_safe_payload'] == 'NOT_CERTIFIED'
            and boundary['machine_replayed_support_text'] == 'OMITTED',
            'inspection export/support boundary changed')
    if historical or result['inspection_status'] != 'INSPECTABLE':
        require(all(result[key] is None for key in ('current_candidate_view', 'source_provenance', 'support')),
                'refused or historical inspection disclosed a semantic result')
    else:
        view = result['current_candidate_view']
        require(all(view[key] is None for key in ('canonical_subject_id', 'canonical_object_id',
                                                'shipments', 'revenue', 'economic_weight', 'theme_membership')),
                'inspection promotes an unsupported identity, magnitude or theme')
        require(result['support']['semantic_adjudication'] == 'NOT_PERFORMED'
                and 'replayed_value_text' not in result['support'],
                'inspection claimed semantic adjudication or exported replay support')


def expected_input_bindings(context, case):
    candidate_raw = context['raw'][case['candidate_file']]
    canonical = canonical_bytes(read_json(candidate_raw))
    source_raw = context['raw'].get(case['source_file'])
    return {
        'candidate': {'representation': 'original_file_bytes',
                      'raw_file_sha256': sha(candidate_raw), 'raw_file_bytes': len(candidate_raw),
                      'canonical_payload_sha256': sha(canonical), 'canonical_payload_bytes': len(canonical)},
        'source': {'representation': 'original_file_bytes',
                   'sha256': sha(source_raw) if source_raw is not None else None,
                   'bytes': len(source_raw) if source_raw is not None else None,
                   'utf8': True if source_raw is not None else None},
    }


def check_missing_single(context, run):
    require(run['exit_code'] == 2 and run['stderr_empty'], 'missing-file single-case CLI exit changed')
    result = run['result']
    require(result['review_status'] == 'INSPECTED' and result['refusal'] is None,
            'missing input erased its requested case')
    require(result['admission'] == 'NOT_ADMITTED' and result['graph1_projection'] is None
            and result['authority'] == {key: False for key in ('rank', 'gate', 'size', 'trade', 'prediction')},
            'single-case missing-file aggregate grants authority')
    require(result['denominators'] == {
        'requested_cases': 1, 'supplied_source_cases': 0, 'unique_supplied_source_byte_digests': 0,
        'inspectable_cases': 0, 'refused_cases': 0, 'unavailable_cases': 1, 'not_known_as_of_cases': 0,
    }, 'missing-file single-case denominator changed')
    require(result['processing'] == {'requested_cases': 1, 'prepared_cases': 1, 'processed_cases': 1,
                                    'inspector_calls': 0, 'retained_case_results': 1},
            'missing-file input was silently inspected or dropped')
    require(len(result['cases']) == 1, 'missing-file single-case output inventory changed')
    case = result['cases'][0]
    require(case['case_id'] == '03-missing-source' and case['status'] == 'UNAVAILABLE'
            and case['input_bindings'] == expected_input_bindings(context, cohort_cases()[2])
            and case['input_refusals'] == [{'input': 'source', 'code': 'REVIEW_FILE_UNAVAILABLE'}],
            'missing-source exact file refusal or binding changed')
    require(case['inspection']['inspection_status'] == 'REFUSED'
            and case['inspection']['refusal'] == {'code': 'REVIEW_FILE_UNAVAILABLE'},
            'missing-file nested inspection refusal changed')
    assertion_boundaries(case['inspection'])
    return case


def check_review(context, run, baselines, missing_case, *, historical=False, reordered=False):
    require(run['exit_code'] == 2 and run['stderr_empty'], 'mixed CLI must exit 2 with refused/unavailable cases')
    result = run['result']
    require(result['schema'] == 'company_intelligence.relationship_review/v1'
            and result['review_status'] == 'INSPECTED' and result['refusal'] is None
            and result['review_set_id'] == REVIEW_SET_ID, 'review envelope/status changed')
    require(result['admission'] == 'NOT_ADMITTED' and result['graph1_projection'] is None
            and result['authority'] == {key: False for key in ('rank', 'gate', 'size', 'trade', 'prediction')},
            'review aggregate authority/admission boundary changed')
    require(result['denominators'] == (HISTORICAL_COUNTS if historical else CURRENT_COUNTS)
            and result['processing'] == PROCESSING, 'mixed case counts or processing changed')
    require(result['options'] == {'as_of': aware_clock(HISTORICAL_AS_OF).isoformat() if historical else None,
                                  'include_support_text': False}, 'review options changed')
    require(result['registry_input'] == {
        'supplied': False, 'trust': 'caller_supplied_not_authenticated_native_registry_history',
    }, 'review invents a supplied registry')
    path = REORDERED_MANIFEST if reordered else CURRENT_MANIFEST
    raw = context['raw'][str(path)]
    require(result['input_manifest'] == {'raw_file_sha256': sha(raw), 'raw_file_bytes': len(raw)},
            'raw manifest identity was not retained separately')
    expected_cases = []
    for case, base_name in zip(cohort_cases(), ('micron', 'nvda', None, 'invalid')):
        if base_name is None:
            expected_cases.append(missing_case)
            continue
        inspection = baselines[base_name + ('_historical' if historical else '_current')]['result']
        expected_cases.append({'case_id': case['case_id'], 'status': inspection['inspection_status'],
                               'input_bindings': expected_input_bindings(context, case),
                               'input_refusals': [], 'inspection': inspection})
    require(result['cases'] == expected_cases, 'complete per-case output differs from actual single-case CLI')
    for case in result['cases']:
        assertion_boundaries(case['inspection'], historical=historical)
    require(result['reconciliation'] == {
        'scope': 'inspectable_cases_only', 'resolution': 'UNRESOLVED_NO_AUTOMATIC_SELECTION',
        'candidate_collisions': [], 'repeated_input_references': [], 'revision_links': [],
    }, 'refused/missing cases entered reconciliation or cohort silently changed')
    identity = {key: value for key, value in result.items() if key not in {'content_sha256', 'input_manifest'}}
    require(result['content_sha256'] == canonical_digest(identity), 'canonical review content digest mismatch')
    require(result['content_boundary']['public_export'] == 'NOT_AUTHORIZED'
            and result['content_boundary']['machine_replayed_support_text'] == 'OMITTED',
            'review content/export boundary changed')
    return result


def subprocess_environment():
    # No credential values are inspected or printed. No provider/runtime factory
    # is initialized. The selected native Python and installed third-party runtime
    # remain a separately scoped platform dependency.
    env = os.environ.copy()
    for key in ('PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONINSPECT'):
        env.pop(key, None)
    env['PYTHONPATH'] = str(CODE_ROOT)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    return env


def invoke(context, name, command, *, guarded):
    immutable_check(context)
    PRIVATE_RUNS[name] = {'command': command, 'guarded': guarded, 'completed': False}
    try:
        process = subprocess.run(command, cwd=str(INPUT_ROOT), env=subprocess_environment(),
                                 capture_output=True, timeout=45, check=False)
    except subprocess.TimeoutExpired as exc:
        PRIVATE_RUNS[name].update(timeout=True,
            stdout=(exc.stdout or b'').decode('utf-8', errors='replace'),
            stderr=(exc.stderr or b'').decode('utf-8', errors='replace'))
        raise ReplayVerificationError('declared CLI child exceeded bounded timeout') from None
    PRIVATE_RUNS[name].update(completed=True, process_exit=process.returncode,
                             stdout=process.stdout.decode('utf-8', errors='replace'),
                             stderr=process.stderr.decode('utf-8', errors='replace'))
    require(len(process.stdout) <= MAX_OUTPUT_BYTES and process.stderr == b'',
            'declared CLI child emitted stderr or exceeded output bound')
    value = read_json(process.stdout)
    if guarded:
        require(process.returncode == 0 and value.get('status') == 'PASS'
                and value.get('job') == name, 'fresh guarded child did not complete all checks')
        require(value['blocked_import_attempts'] == [] and value['blocked_side_effect_attempts'] == [],
                'guarded child recorded forbidden attempts')
        outcome = value
    else:
        outcome = {'exit_code': process.returncode, 'result': value,
                   'stdout_sha256': sha(process.stdout), 'stdout_bytes': len(process.stdout),
                   'stderr_empty': True, 'launch': 'literal_python_-B_-m',
                   'independent_preimport_guard_or_verified_loader': False}
    PRIVATE_RUNS[name]['outcome'] = outcome
    immutable_check(context)
    return outcome


def principal_arguments(args):
    return ['--source-receipt', args.source_receipt, '--source-receipt-sha256', args.source_receipt_sha256,
            '--input-receipt', args.input_receipt, '--input-receipt-sha256', args.input_receipt_sha256,
            '--harness-sha256', args.harness_sha256, '--phase', args.phase]


def parent_main(args):
    context = preflight(args)
    guarded = {}
    for job in ('regenerate_micron', *cli_jobs()):
        command = [sys.executable, '-B', str(context['self_path']), *principal_arguments(args), '--child', job]
        guarded[job] = invoke(context, job, command, guarded=True)
    baselines = {key: guarded[key] for key in ('micron_current', 'nvda_current', 'invalid_current',
                                             'micron_historical', 'nvda_historical', 'invalid_historical')}
    for name, run in baselines.items():
        historical = name.endswith('_historical')
        positive = name in {'micron_current', 'nvda_current'}
        require(run['exit_code'] == (0 if positive else 2), 'single-case CLI exit changed')
        require(run['result']['inspection_status'] == ('INSPECTABLE' if positive else 'REFUSED'),
                'single-case CLI status changed')
        if not positive:
            refusal = 'INPUT_INVALID' if name.startswith('invalid_') else 'AS_OF_REGISTRY_REQUIRED'
            require(run['result']['refusal'] == {'code': refusal}, 'single-case refusal changed')
        assertion_boundaries(run['result'], historical=historical)
    micron_witness = read_json(context['raw'][str(MICRON_WITNESS)])
    for phase in ('current', 'historical'):
        saved = micron_witness['outcomes'][phase]
        actual = baselines['micron_' + phase]
        require(actual['result'] == saved['result'] and actual['exit_code'] == saved['exit_code']
                and saved['stderr_empty'] is True, 'complete Micron legacy witness compatibility changed')
    nvda_witness = read_json(context['raw'][str(ORIGINAL_FILES['nvda_witness'][0])])
    require(baselines['nvda_current']['result'] == nvda_witness['outcomes']['current']['candidate_inspection'],
            'complete NVIDIA manual result differs from retained genuine inspection')
    missing_case = check_missing_single(context, guarded['missing_single'])
    current = check_review(context, guarded['review_current'], baselines, missing_case)
    reordered = check_review(context, guarded['review_reordered'], baselines, missing_case, reordered=True)
    historical = check_review(context, guarded['review_historical'], baselines, missing_case, historical=True)
    without_manifest = lambda result: {key: value for key, value in result.items() if key != 'input_manifest'}
    require(without_manifest(current) == without_manifest(reordered)
            and current['input_manifest'] != reordered['input_manifest'],
            'manifest permutation/formatting changed complete canonical review content')

    literal = {}
    for name, source_job in (('literal_review_current', 'review_current'),
                             ('literal_micron_current', 'micron_current'),
                             ('literal_micron_historical', 'micron_historical')):
        command = [sys.executable, '-B', '-m', MODULE, *cli_jobs()[source_job]]
        run = invoke(context, name, command, guarded=False)
        expected = guarded[source_job]
        require(run['exit_code'] == expected['exit_code'] and run['result'] == expected['result'],
                'ordinary literal -m command differs from complete guarded CLI output/exit')
        literal[name] = run
    immutable_check(context)
    receipt = context['source_receipt']
    return {
        'schema': 'economic_network.retained_review_set_cli_verification.v1', 'status': 'PASS',
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'proof_scope': 'retained_real_sources_to_manual_file_review_cli_not_pinned_custody',
        'source_phase': args.phase,
        'replay_code_binding': {
            'principal_source_receipt_sha256': args.source_receipt_sha256,
            'principal_input_receipt_sha256': args.input_receipt_sha256,
            'harness_sha256': args.harness_sha256,
            'reviewed_head_from_principal_receipt': receipt['reviewed_head'],
            'accepted_merge_sha_from_principal_receipt': receipt['accepted_merge_sha'],
            'github_merge_independently_verified_by_this_harness': False,
            'locally_verified_code_paths': len(context['code_hashes']),
            'current_code_manifest_sha256': canonical_digest(context['code_hashes']),
        },
        'source_digests': {'micron': MICRON_SHA, 'nvda': NVDA_SHA},
        'current_denominators': current['denominators'],
        'historical_denominators': historical['denominators'],
        'complete_cases_equal_to_actual_single_case_cli': True,
        'complete_micron_historical_witness_compatibility': True,
        'micron_native_regeneration_matches_retained_candidate': True,
        'micron_exploratory_fetch_coordinates_rewritten': False,
        'canonical_content_sha256': current['content_sha256'],
        'historical_content_sha256': historical['content_sha256'],
        'distinct_manifest_raw_sha256': [current['input_manifest']['raw_file_sha256'],
                                       reordered['input_manifest']['raw_file_sha256']],
        'permutation_and_formatting_preserve_complete_content': True,
        'literal_advertised_command_matches_guarded_output_and_exit': True,
        'literal_micron_single_case_compatibility': True,
        'guarded_fresh_processes': len(guarded), 'ordinary_literal_cli_processes': len(literal),
        'guarded_import_policy': list(FORBIDDEN_IMPORTS),
        'ordinary_literal_runs_independently_carry_preimport_guards': False,
        'third_party_runtime_fully_pinned': False,
        'runs': {name: {
            'launch': run['launch'], 'exit_code': run['exit_code'],
            'complete_output_sha256': canonical_digest(run['result']),
            'status': run['result'].get('review_status', run['result'].get('inspection_status')),
            'refusal_code': (run['result'].get('refusal') or {}).get('code'),
        } for name, run in {**{key: value for key, value in guarded.items() if key != 'regenerate_micron'},
                            **literal}.items()},
        'case_results': {case['case_id']: {
            'status': case['status'], 'refusal_code': (case['inspection']['refusal'] or {}).get('code'),
            'complete_inspection_sha256': canonical_digest(case['inspection']),
        } for case in current['cases']},
        'protected_original_and_input_tree_unchanged': True, 'latest_pointer_absent': True,
        'source_capture_performed': False, 'original_private_candidate_written': False,
        'strict_native_nvda_five_call_replay_performed_here': False,
        'prior_strict_failures_reclassified': False,
        'native_fact_admission': False, 'production_reader_custody': False,
        'historical_system_replay': False, 'rights_admission': False,
        'served_product_proof': False, 'predictive_authority': False,
    }


def private_output(args, public_receipt):
    """Optional principal-requested evidence write, outside guarded readers."""
    if args.private_output is None:
        return {'status': 'NOT_REQUESTED', 'complete_outputs_retained_in_parent_memory_only': True}
    path = absolute_path(args.private_output, within=PROOF_ROOT / 'results')
    real_directory_chain(path.parent)
    require(not os.path.lexists(path), 'private result target must be a new exclusive file')
    payload = canonical_bytes({'public_receipt': public_receipt, 'private_runs': PRIVATE_RUNS}) + b'\n'
    require(len(payload) <= 64 * 1024 * 1024, 'private evidence exceeds bounded output size')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(payload)
    raw, _state = checked_bytes(path, 64 * 1024 * 1024)
    require(raw == payload, 'private evidence readback differs')
    return {'status': 'SAVED_PRIVATE', 'path': str(path), 'sha256': sha(raw), 'bytes': len(raw)}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-receipt', required=True)
    parser.add_argument('--source-receipt-sha256', required=True)
    parser.add_argument('--input-receipt', required=True)
    parser.add_argument('--input-receipt-sha256', required=True)
    parser.add_argument('--harness-sha256', required=True)
    parser.add_argument('--phase', required=True,
                        choices=('PREMERGE_FROZEN_CANDIDATE', 'POSTMERGE_ACCEPTED_SOURCE'))
    parser.add_argument('--private-output', help='Optional new exclusive private JSON under proof_root/results')
    parser.add_argument('--child', choices=('regenerate_micron', *cli_jobs()), help=argparse.SUPPRESS)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    try:
        if args.child:
            require(args.private_output is None, 'guarded child cannot write evidence files')
            print(json.dumps(child_main(args), ensure_ascii=False, sort_keys=True, separators=(',', ':')))
        else:
            receipt = parent_main(args)
            receipt['private_evidence'] = private_output(args, receipt)
            print(json.dumps(receipt, sort_keys=True, indent=2))
    except Exception as exc:
        failure = {'schema': 'economic_network.retained_review_set_cli_verification.v1',
                   'status': 'FAIL', 'observed_at': datetime.now(timezone.utc).isoformat(),
                   'failure': str(exc) if type(exc) is ReplayVerificationError else type(exc).__name__,
                   'observation': OBSERVATION, 'source_phase': args.phase,
                   'native_fact_admission': False, 'production_reader_custody': False,
                   'historical_system_replay': False, 'rights_admission': False,
                   'served_product_proof': False, 'predictive_authority': False}
        if args.child:
            # Captured only by the private parent subprocess pipe, never published
            # as the principal's sanitized stdout receipt.
            failure['private_partial_output'] = PRIVATE_RUNS
        else:
            try:
                failure['private_evidence'] = private_output(args, failure)
            except Exception as save_exc:
                failure['private_evidence'] = {'status': 'UNAVAILABLE_OR_PARTIAL_DO_NOT_OVERWRITE',
                                               'error_type': type(save_exc).__name__}
        print(json.dumps(failure, ensure_ascii=False, sort_keys=True, indent=2))
        raise SystemExit(1)
