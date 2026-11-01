import ast
import copy
import hashlib
import json
import sys
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.theme_graph import selection_cohort_publication as publication_module
from engine.theme_graph import selection_cohort_reads
from engine.theme_graph.selection_cohort_publication import (
    consume_us_source,
    validate_selection_cohort,
)
from engine.theme_graph.selection_cohort_reads import publication_reads


ROOT = Path(__file__).resolve().parents[1]
FINALIZED_AT = "2026-10-04T09:00:00.123456Z"
AVAILABLE_AT = "2026-10-04T08:00:00Z"


def raw(rows=None, generation="native-process-1"):
    if rows is None:
        rows = [
            dict(ticker="ROK", featured=True, conviction={"verdict": "owner-late"},
                 entry_signal={"label": "blocked"}, risk_sizing={"units": None}),
            dict(ticker="OTHER", featured=False),
        ]
    return json.dumps(
        dict(buy=rows, as_of="2026-10-03", emit={"pair_id": generation, "at_utc": AVAILABLE_AT},
             w3c_source={"schema": "mastermind.selection_cohort_library_source.v1",
                         "generation_id": generation, "availability": "VALID",
                         "available_at": AVAILABLE_AT}),
        separators=(",", ":"), allow_nan=False,
    ).encode()


def controlled_authority(request):
    assert request["purpose"] == "selection_cohort_internal_capture"
    assert request["source_sha256"] and request["generation_id"]
    return True


def publish(tmp_path, data=None):
    return publication_module.publish_us_source(
        data or raw(), data_dir=tmp_path, finalized_at=FINALIZED_AT,
        authorize_capture=controlled_authority,
    )


SENTINEL_READS = {
    "identity_reads": object(),
    "membership_reads": object(),
    "state_reads": object(),
}


def six_reads(selection, *, data_dir=None, rights_path=None):
    assert selection["rows"][0]["selection_id"]
    return {
        "identity_reads": SENTINEL_READS["identity_reads"],
        "membership_reads": SENTINEL_READS["membership_reads"],
        "state_reads": SENTINEL_READS["state_reads"],
        "unqualified": ["not-for-compose"],
        "selection_clock": ["not-for-compose"],
        "owners": ["not-for-compose"],
    }


def test_publication_reads_returns_only_compose_keys_with_identical_objects(monkeypatch):
    selection = {"rows": [{"selection_id": "row-1"}]}
    monkeypatch.setattr(selection_cohort_reads, "qualified_reads", six_reads)

    reads = publication_reads(selection, data_dir="data-dir", rights_path="rights-path")
    expected = dict(SENTINEL_READS)

    assert reads["identity_reads"] is expected["identity_reads"]
    assert reads["membership_reads"] is expected["membership_reads"]
    assert reads["state_reads"] is expected["state_reads"]
    assert set(reads) == set(selection_cohort_reads.COMPOSE_KEYS)


@pytest.mark.parametrize("exception", [ValueError, OSError])
def test_publication_reads_passes_publication_failures_through(monkeypatch, tmp_path, exception):
    def fail(*args, **kwargs):
        raise exception("controlled publication failure")

    monkeypatch.setattr(selection_cohort_reads, "qualified_reads", fail)
    with pytest.raises(exception, match="controlled publication failure"):
        publication_reads({"rows": []}, data_dir=tmp_path)


def test_publication_reads_wraps_unexpected_owner_failure(monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        raise RuntimeError("controlled owner failure")

    monkeypatch.setattr(selection_cohort_reads, "qualified_reads", fail)
    with pytest.raises(ValueError, match="^QUALIFIED_READS_OWNER_FAILURE:RuntimeError$") as caught:
        publication_reads({"rows": []}, data_dir=tmp_path)
    assert isinstance(caught.value.__cause__, RuntimeError)


def test_direct_six_key_owner_is_refused_but_three_key_adapter_is_available(tmp_path, monkeypatch):
    receipt = publish(tmp_path)
    assert receipt["status"] == "AVAILABLE"
    real_owner = selection_cohort_reads.qualified_reads

    monkeypatch.setattr(
        selection_cohort_reads, "qualified_reads",
        lambda selection, **kwargs: {
            "identity_reads": {}, "membership_reads": {}, "state_reads": {},
            "unqualified": [], "selection_clock": {}, "owners": {},
        },
    )
    defective = consume_us_source(
        raw(), data_dir=tmp_path,
        authorize_capture=controlled_authority,
        qualified_reads=partial(selection_cohort_reads.qualified_reads, data_dir=tmp_path),
    )
    assert defective["status"] == "UNAVAILABLE"
    assert defective["reason_codes"] == ["PUBLICATION_IO_OR_VALIDATION_FAILURE"]

    adapted = consume_us_source(
        raw(), data_dir=tmp_path,
        authorize_capture=controlled_authority,
        qualified_reads=partial(publication_reads, data_dir=tmp_path),
    )
    assert adapted["status"] == "AVAILABLE"
    assert adapted["explanation"] is not None
    assert adapted["receipt"] == receipt["receipt"]
    validate_selection_cohort(adapted["explanation"])


def find_seams():
    module = ast.parse((ROOT / "scripts/build_site.py").read_text())
    first = None
    fresh = None
    for node in ast.walk(module):
        if isinstance(node, ast.If) and ast.unparse(node.test) == "_us.exists()":
            first = node
        if (isinstance(node, ast.Try) and node.body and isinstance(node.body[0], ast.Assign)
                and ast.unparse(node.body[0]).startswith("_us_path =")):
            fresh = node
    assert first is not None and fresh is not None
    return module, first, fresh


def execute_first(module, namespace):
    first = find_seams()[1]
    target = first.body[0].body[2]
    exec(compile(ast.Module(body=[target], type_ignores=[]), "<first seam>", "exec"), namespace)


def execute_fresh(module, namespace):
    fresh = find_seams()[2]
    prefix = []
    for node in fresh.body:
        prefix.append(node)
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "_fresh_su"
                for target in node.targets):
            break
    exec(compile(ast.Module(body=prefix, type_ignores=[]), "<fresh seam>", "exec"), namespace)


def seam_namespace(tmp_path, spy, monkeypatch):
    # The seams re-import consume_us_source from the publication module at exec time, so the spy must
    # replace the module attribute (same technique as the incumbent publication seam test).
    monkeypatch.setattr(publication_module, "consume_us_source", spy)
    source = raw()
    board_path = tmp_path / "factordata/us_standouts.json"
    board_path.parent.mkdir(exist_ok=True)
    board_path.write_bytes(source)
    return dict(
        ast=ast, json=json, site=tmp_path,
        _us=board_path, _us_path=board_path, _us_source_bytes=source,
        us_standouts=None, _us_w3c=None, _us_w3c_binding=None,
        _fresh_source_bytes=None, _fresh_w3c=None, _fresh_w3c_binding=None,
        consume_us_source=spy, log=SimpleNamespace(warning=lambda *args: None),
        config=SimpleNamespace(data_dir=lambda: tmp_path),
        _attach_board_display_chips=lambda site, doc: doc,
    )


def test_seams_fall_back_to_receipt_only_when_owner_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(
        publication_module, "default_capture_capability",
        lambda: controlled_authority)
    publish(tmp_path)
    calls = []
    receipt_only = consume_us_source(
        raw(), data_dir=tmp_path, authorize_capture=controlled_authority)

    def spy(source_bytes, *, data_dir, authorize_capture, qualified_reads=None):
        calls.append(qualified_reads)
        return consume_us_source(
            source_bytes, data_dir=data_dir,
            authorize_capture=controlled_authority, qualified_reads=qualified_reads)

    def fail(*args, **kwargs):
        raise RuntimeError("controlled reads owner failure")

    monkeypatch.setattr(selection_cohort_reads, "qualified_reads", fail)
    module, _, _ = find_seams()
    namespace = seam_namespace(tmp_path, spy, monkeypatch)
    execute_first(module, namespace)
    execute_fresh(module, namespace)

    assert namespace["_us_w3c"] == receipt_only
    assert namespace["_fresh_w3c"] == receipt_only
    assert namespace["_us_w3c"]["explanation"] is None
    assert namespace["_fresh_w3c"]["explanation"] is None
    assert calls == [calls[0], None, calls[2], None]
    assert all(call is not None for call in (calls[0], calls[2]))


def test_working_reads_produce_identical_first_and_fresh_explanations(tmp_path, monkeypatch):
    original_capability = publication_module.default_capture_capability
    try:
        publication_module.default_capture_capability = lambda: controlled_authority
        publish(tmp_path)
    finally:
        publication_module.default_capture_capability = original_capability

    def spy(source_bytes, *, data_dir, authorize_capture, qualified_reads=None):
        return consume_us_source(
            source_bytes, data_dir=data_dir,
            authorize_capture=controlled_authority, qualified_reads=qualified_reads)

    module, _, _ = find_seams()
    namespace = seam_namespace(tmp_path, spy, monkeypatch)
    execute_first(module, namespace)
    execute_fresh(module, namespace)

    assert namespace["_us_w3c"]["status"] == "AVAILABLE"
    assert namespace["_fresh_w3c"] == namespace["_us_w3c"]
    assert namespace["_fresh_w3c"]["explanation"] is not None


def test_missing_reads_module_still_preserves_both_receipt_only_boards(tmp_path, monkeypatch):
    monkeypatch.setattr(
        publication_module, "default_capture_capability",
        lambda: controlled_authority)
    publish(tmp_path)
    calls = []

    def spy(source_bytes, *, data_dir, authorize_capture, qualified_reads=None):
        calls.append(qualified_reads)
        return consume_us_source(
            source_bytes, data_dir=data_dir,
            authorize_capture=controlled_authority, qualified_reads=qualified_reads)

    monkeypatch.setitem(sys.modules, "engine.theme_graph.selection_cohort_reads", None)
    module, _, _ = find_seams()
    namespace = seam_namespace(tmp_path, spy, monkeypatch)
    execute_first(module, namespace)
    execute_fresh(module, namespace)

    assert namespace["_us_w3c"]["status"] == "AVAILABLE"
    assert namespace["_fresh_w3c"] == namespace["_us_w3c"]
    assert calls == [None, None]
