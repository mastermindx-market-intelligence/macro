"""FIF X2-s saved-store schema guards (gate 7 + T1).

Walks every committed saved-view fixture and refuses any number outside the
explicit allow-list (``peers.peer_n``, ``peers.peer_tol``,
``evidence_refs[].source_span``) and any metric-value field; re-admits every
embedded ``request`` through :func:`admit_financial_request` with canonical
bytes unchanged; and pins the JS store constants (``request_contract`` equals
the engine's ``_REQUEST_SCHEMA``) so a future contract change fails here
instead of silently loading old blobs. The behavioural refusal tests live in
the Node roundtrip suite, which this module also runs (the CI enrolment rides
this file, mirroring ``tests/test_fundamental_forensics_ui.py``'s node spawns).
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from engine.fundamental_forensics.api_client import encode_query_request
from engine.fundamental_forensics.query_service import (
    _REQUEST_SCHEMA,
    admit_financial_request,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "fundamental_forensics" / "fif_saved_research"
BRIEFCASE_JS = ROOT / "templates" / "fif_saved_briefcase.js"

SAVED_SCHEMA = "fundamental_forensics.saved_research.v1"
STORAGE_KEY = "mastermind.filing_forensics.saved_research.v1"

# Numbers may appear ONLY on these stored paths (explicit allow-list).
_ALLOWED_NUMERIC_PATHS = {
    ("peers", "peer_n"),
    ("peers", "peer_tol"),
}
# A stored field whose key names a value/metric shape is a copied value, no
# matter where it sits — refused outright.
_VALUE_KEY_NAMES = frozenset(
    {"value", "current", "prior", "delta", "magnitude", "amount", "score", "rank"}
)

_T1_REFUSAL_REASONS = (
    "schema",
    "request_contract",
    "request_schema",
    "request_root",
    "request_canonical",
    "pinned_type",
    "peers",
    "view",
    "pinned_cutoffs",
    "id",
    "unavailable",
    "storage",
)


def _fixtures() -> list[Path]:
    paths = sorted(FIXTURE_DIR.glob("saved_*.json"))
    assert paths, f"no saved-view fixtures under {FIXTURE_DIR}"
    return paths


def _walk(value, path, visit):
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        visit(path, value)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk(item, f"{path}[{index}]", visit)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            assert key not in _VALUE_KEY_NAMES, f"metric-value key stored at {path}.{key}"
            _walk(item, f"{path}.{key}", visit)


def _violations(view: object, base: str) -> list[str]:
    """Run the allow-list walk over ONE saved view; list every violation.

    The walk is the load-bearing half: a helper that never calls ``_walk``
    would vacuously report ``[]`` for every fixture (the r1 review finding).
    """
    violations: list[str] = []

    def visit(node_path: str, value: object) -> None:
        assert not isinstance(value, float), f"float stored at {base}{node_path}"
        relative = node_path.split(".", 1)[1] if "." in node_path else node_path
        parts = tuple(re.sub(r"\[\d+\]", "", relative).split("."))
        # r1: the span elements land at parts ("evidence_refs", "source_span")
        # once their [index] segments are stripped — the pre-r1 matcher demanded
        # parts[2] and never matched anything, because it never ran. This is
        # the documented allow-list (module docstring), not a new allowance.
        in_span = (
            len(parts) >= 2
            and parts[0] == "evidence_refs"
            and parts[-1] == "source_span"
        )
        if parts not in _ALLOWED_NUMERIC_PATHS and not in_span:
            violations.append(f"{base}{node_path}={value}")

    _walk(view, "", visit)
    return violations


def test_every_fixture_walk_refuses_numbers_outside_the_allow_list() -> None:
    for path in _fixtures():
        container = json.loads(path.read_text(encoding="utf-8"))
        for index, view in enumerate(container["saved_views"]):
            base = f"{path.name}#saved_views[{index}]"
            assert _violations(view, base) == [], path.name


def test_the_walk_reports_an_unaudited_number_at_exactly_its_path() -> None:
    # Permanent mutation check (X2-s r1): an unaudited number planted deep
    # inside a committed view must surface at exactly its path — proving the
    # fixture test above can fail.
    container = json.loads((FIXTURE_DIR / "saved_pinned.json").read_text(encoding="utf-8"))
    view = copy.deepcopy(container["saved_views"][0])
    view["view"]["zoom"] = 3
    base = "saved_pinned.json#saved_views[0]"
    assert _violations(view, base) == [f"{base}.view.zoom=3"]


def test_fixture_containers_carry_the_contract_and_no_inbox_key() -> None:
    for path in _fixtures():
        container = json.loads(path.read_text(encoding="utf-8"))
        assert container["contract"] == SAVED_SCHEMA, path.name
        assert set(container) == {"contract", "saved_views"}, path.name


def test_every_embedded_request_re_admits_with_canonical_bytes_unchanged() -> None:
    for path in _fixtures():
        container = json.loads(path.read_text(encoding="utf-8"))
        for view in container["saved_views"]:
            request = view["request"]
            assert view["request_contract"] == request["schema"] == _REQUEST_SCHEMA, path.name
            canonical = encode_query_request(request)
            admitted = admit_financial_request(canonical)
            assert admitted.entity_id == request["entity_id"], path.name
            # Canonical bytes are a stable function of the stored object.
            assert encode_query_request(json.loads(canonical.decode("utf-8"))) == canonical, path.name
            assert json.loads(canonical.decode("utf-8")) == request, path.name
            assert len(canonical) <= 65536, path.name


def test_pinned_views_carry_both_explicit_cutoffs_and_watch_is_a_stored_boolean() -> None:
    for path in _fixtures():
        container = json.loads(path.read_text(encoding="utf-8"))
        for view in container["saved_views"]:
            policy = view["request"]["policy"]
            if view["pinned"] is True:
                assert policy["source_snapshot_at"], path.name
                assert policy["recorded_at"], path.name
            assert isinstance(view["watch"]["issuer"], bool), path.name


def test_js_store_constants_equal_the_engine_contract() -> None:
    source = BRIEFCASE_JS.read_text(encoding="utf-8")

    def constant(name: str) -> str:
        match = re.search(rf"var {name} = '([^']+)'", source)
        assert match, f"{name} not found in fif_saved_briefcase.js"
        return match.group(1)

    assert constant("REQUEST_CONTRACT") == _REQUEST_SCHEMA
    assert constant("SAVED_SCHEMA") == SAVED_SCHEMA
    assert constant("STORAGE_KEY") == STORAGE_KEY


def _declared_refusal_reasons() -> tuple[str, ...]:
    source = BRIEFCASE_JS.read_text(encoding="utf-8")
    match = re.search(r"var REFUSAL_REASONS = \[(.*?)\];", source, re.DOTALL)
    assert match, "REFUSAL_REASONS not declared in fif_saved_briefcase.js"
    return tuple(re.findall(r"'([^']+)'", match.group(1)))


def test_module_declares_every_t1_refusal_reason_and_the_suite_pins_each() -> None:
    # The pinned list and the module's declared set must match EXACTLY, both
    # directions: a reason the module refuses with but no test pins, or a test
    # pinning a reason the module never returns, both fail here.
    declared = _declared_refusal_reasons()
    assert len(declared) == len(set(declared)), "a refusal reason is declared twice"
    assert set(declared) == set(_T1_REFUSAL_REASONS), (
        f"declared {sorted(declared)} != pinned {sorted(_T1_REFUSAL_REASONS)}"
    )
    source = BRIEFCASE_JS.read_text(encoding="utf-8")
    for reason in _T1_REFUSAL_REASONS:
        assert f"'{reason}'" in source, f"refusal reason {reason} missing from the store"
    roundtrip = (
        ROOT / "tests" / "fundamental_forensics_saved_research_roundtrip.test.mjs"
    ).read_text(encoding="utf-8")
    for reason in _T1_REFUSAL_REASONS:
        assert f"'{reason}'" in roundtrip, f"no behavioural test pins refusal {reason}"


def test_recorded_response_fixture_is_a_lawful_envelope() -> None:
    envelope = json.loads(
        (FIXTURE_DIR / "recorded_query_response.json").read_text(encoding="utf-8")
    )
    assert envelope["schema"] == "fundamental_forensics.financial_query_response/v1"
    assert envelope["authority"] == {"class": "context_only", "display_only": True}
    assert isinstance(envelope["receipt"]["nodes"], list) and envelope["receipt"]["nodes"]
    for node in envelope["receipt"]["nodes"]:
        assert isinstance(node["value"], str), "a fixture value must be decimal text"


def test_node_roundtrip_and_url_state_suites() -> None:
    node = shutil.which("node")
    if node is None:  # pragma: no cover - a missing binary is a SKIP, never a silent pass
        pytest.skip(f"node binary not found: which(node)={node!r} PATH={os.environ.get('PATH', '')!r}")
    for suite in (
        "fundamental_forensics_saved_research_roundtrip.test.mjs",
        "fundamental_forensics_saved_url_state.test.mjs",
        "fundamental_forensics_investigation_manifest_mapping.test.mjs",
        "fundamental_forensics_investigation_manifest_emitter.test.mjs",
    ):
        result = subprocess.run(
            [node, "--test", str(ROOT / "tests" / suite)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
