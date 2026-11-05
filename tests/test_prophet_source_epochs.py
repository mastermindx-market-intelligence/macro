"""Focused tests for :mod:`engine.prophet_source_epochs`.

All fixtures are synthetic and self-contained: no network, no repository
data, no private datasets, and no writes outside pytest's ``tmp_path``.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import engine.prophet_source_epochs as pse  # noqa: E402

# ---------------------------------------------------------------------------
# Synthetic fixtures: board A / index I / frozen board A, then board B, which
# keeps the same market date but changes one member.
# ---------------------------------------------------------------------------

A_OBJ = {
    "as_of": "2026-10-28",
    "market_date": "2026-10-28",
    "members": [{"ticker": "AAA", "weight": 0.5}, {"ticker": "BBB", "weight": 0.5}],
}
B_OBJ = {
    "as_of": "2026-10-28",
    "market_date": "2026-10-28",
    "members": [{"ticker": "AAA", "weight": 0.5}, {"ticker": "CCC", "weight": 0.5}],
}


def _dumps(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


BOARD_A = _dumps(A_OBJ)
BOARD_B = _dumps(B_OBJ)
A_SHA = _sha(BOARD_A)
B_SHA = _sha(BOARD_B)
GZ_NAME = "%s.json.gz" % A_SHA
SNAPSHOT_PATH = "data/prophet/origination_sources/%s" % GZ_NAME


def _index_bytes(**overrides) -> bytes:
    payload = {
        "asof": "2026-10-28",
        "source_asof": "2026-10-28",
        "source_board_asof": "2026-10-28",
        "source_board_sha256": A_SHA,
        "source_board_snapshot_path": SNAPSHOT_PATH,
        "source_board_snapshot_encoding": "gzip",
    }
    payload.update(overrides)
    return _dumps(payload)


# Index I and frozen board A are byte-stable across every scenario.
INDEX_I = _index_bytes()


def _project(board=BOARD_A, index=INDEX_I, snapshot=BOARD_A):
    return pse.project_source_epochs(
        board_bytes=board, index_bytes=index, snapshot_bytes=snapshot
    )


def _read(root, board=BOARD_A, index=INDEX_I):
    return pse.read_source_epochs(board_bytes=board, index_bytes=index, data_dir=root)


def _write_snapshot(root: pathlib.Path, sha: str, payload: bytes) -> pathlib.Path:
    directory = root / "prophet" / "origination_sources"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / ("%s.json.gz" % sha)
    target.write_bytes(gzip.compress(payload))
    return target


def _tree(root: pathlib.Path):
    """Files *and* directories, so a stray mkdir would show up."""
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(dirnames):
            full = pathlib.Path(dirpath) / name
            entries.append((str(full.relative_to(root)) + "/", None, full.is_symlink()))
        for name in sorted(filenames):
            full = pathlib.Path(dirpath) / name
            entries.append((str(full.relative_to(root)), full.stat().st_size,
                            full.is_symlink()))
    return entries


TOP_LEVEL_KEYS = {"schema", "relation", "settlement_status", "reason_codes",
                  "current_board", "index", "origination_board"}
CURRENT_BOARD_KEYS = {"sha256", "source_asof"}
INDEX_KEYS = {"sha256", "asof", "source_asof"}
ORIGINATION_BOARD_KEYS = {"sha256", "source_asof", "snapshot_verified"}


# ---------------------------------------------------------------------------
# Pure projection: relation
# ---------------------------------------------------------------------------


def test_same_source_when_live_board_matches_frozen_snapshot():
    result = _project()
    assert result["relation"] == "SAME_SOURCE"
    assert result["settlement_status"] == "PENDING"
    assert result["reason_codes"] == ["FOUR_FAMILY_RECEIPT_NOT_EVALUATED"]
    assert result["current_board"]["sha256"] == A_SHA
    assert result["origination_board"]["sha256"] == A_SHA
    assert result["origination_board"]["snapshot_verified"] is True
    assert result["current_board"]["source_asof"] == "2026-10-28"
    assert result["origination_board"]["source_asof"] == "2026-10-28"
    assert result["index"]["asof"] == "2026-10-28"
    assert result["index"]["source_asof"] == "2026-10-28"


def test_separate_epochs_when_live_board_membership_changes_on_same_market_date():
    result = _project(board=BOARD_B)
    assert result["relation"] == "SEPARATE_EPOCHS"
    # Index I and frozen A are unchanged; only the live board moved.
    assert result["current_board"]["sha256"] == B_SHA
    assert result["origination_board"]["sha256"] == A_SHA
    assert result["index"]["sha256"] == _sha(INDEX_I)
    assert result["origination_board"]["snapshot_verified"] is True
    assert (result["current_board"]["source_asof"]
            == result["origination_board"]["source_asof"] == "2026-10-28")


def test_formatting_only_difference_is_separate_epochs():
    reformatted = json.dumps(A_OBJ, sort_keys=True, indent=2).encode("utf-8")
    assert reformatted != BOARD_A
    result = _project(board=reformatted)
    assert result["relation"] == "SEPARATE_EPOCHS"
    assert result["current_board"]["sha256"] == _sha(reformatted)
    assert result["origination_board"]["sha256"] == A_SHA
    assert result["current_board"]["source_asof"] == "2026-10-28"


def test_projection_is_deterministic():
    assert _project() == _project()


def test_identical_hashes_are_never_settled():
    result = _project()
    assert result["settlement_status"] == "PENDING"
    assert "SETTLED" not in json.dumps(result)


# ---------------------------------------------------------------------------
# Pure projection: absent / invalid inputs
# ---------------------------------------------------------------------------


def test_projection_without_any_input_is_unavailable():
    result = _project(board=None, index=None, snapshot=None)
    assert result["relation"] == "UNAVAILABLE"
    assert "CURRENT_BOARD_MISSING" in result["reason_codes"]
    assert "INDEX_MISSING" in result["reason_codes"]
    assert "SNAPSHOT_MISSING" in result["reason_codes"]
    assert result["current_board"] == {"sha256": None, "source_asof": None}
    assert result["index"] == {"sha256": None, "asof": None, "source_asof": None}
    assert result["origination_board"] == {"sha256": None, "source_asof": None,
                                           "snapshot_verified": False}


@pytest.mark.parametrize(
    "overrides,expected_code",
    [
        ({"source_board_sha256": A_SHA.upper()}, "INDEX_SOURCE_BOARD_SHA256_INVALID"),
        ({"source_board_sha256": "abc"}, "INDEX_SOURCE_BOARD_SHA256_INVALID"),
        ({"source_board_sha256": A_SHA + "0"}, "INDEX_SOURCE_BOARD_SHA256_INVALID"),
        ({"source_board_sha256": 12345}, "INDEX_SOURCE_BOARD_SHA256_INVALID"),
        ({"source_board_sha256": None}, "INDEX_SOURCE_BOARD_SHA256_INVALID"),
        ({"source_board_snapshot_path": "data/prophet/origination_sources/x.json.gz"},
         "INDEX_SNAPSHOT_PATH_INVALID"),
        ({"source_board_snapshot_path": "/etc/passwd"}, "INDEX_SNAPSHOT_PATH_INVALID"),
        ({"source_board_snapshot_path": "data/prophet/origination_sources/../origination_sources/%s" % GZ_NAME},
         "INDEX_SNAPSHOT_PATH_INVALID"),
        ({"source_board_snapshot_path": "data/prophet/origination_sources/%s.json.gz" % B_SHA},
         "INDEX_SNAPSHOT_PATH_INVALID"),
        ({"source_board_snapshot_encoding": "GZIP"}, "INDEX_SNAPSHOT_ENCODING_INVALID"),
        ({"source_board_snapshot_encoding": "json"}, "INDEX_SNAPSHOT_ENCODING_INVALID"),
        ({"source_board_snapshot_encoding": None}, "INDEX_SNAPSHOT_ENCODING_INVALID"),
        ({"asof": "not-a-date"}, "INDEX_ASOF_INVALID"),
        ({"asof": "2026-13-01"}, "INDEX_ASOF_INVALID"),
        ({"asof": "2026-10-28T00:00:00Z"}, "INDEX_ASOF_INVALID"),
        ({"source_asof": "nope"}, "INDEX_SOURCE_ASOF_INVALID"),
        ({"source_board_asof": None}, "INDEX_SOURCE_BOARD_ASOF_INVALID"),
    ],
)
def test_projection_rejects_invalid_index_metadata(overrides, expected_code):
    result = _project(index=_index_bytes(**overrides))
    assert result["relation"] == "UNAVAILABLE"
    assert expected_code in result["reason_codes"]
    # A broken index binding blocks the relation, but the raw byte identity
    # of each artifact is still reported.
    assert result["origination_board"]["sha256"] == A_SHA
    assert result["current_board"]["sha256"] == A_SHA


def test_projection_rejects_index_missing_required_metadata():
    payload = json.loads(INDEX_I.decode("utf-8"))
    del payload["source_board_snapshot_path"]
    result = _project(index=_dumps(payload))
    assert result["relation"] == "UNAVAILABLE"
    assert "INDEX_SNAPSHOT_PATH_INVALID" in result["reason_codes"]


def test_projection_rejects_snapshot_whose_bytes_do_not_match_declared_sha():
    result = _project(snapshot=BOARD_B)
    assert result["relation"] == "UNAVAILABLE"
    assert "SNAPSHOT_SHA_MISMATCH" in result["reason_codes"]
    assert result["origination_board"]["snapshot_verified"] is False
    assert result["origination_board"]["sha256"] == B_SHA


@pytest.mark.parametrize(
    "raw",
    [
        b"not json at all", b"{", b"[1, 2, 3]", b'"a bare string"', b"123",
        b'{"a": 1, "a": 2}',
        b'{"as_of": "2026-10-28", "as_of": "2026-10-27"}',
        b'{"as_of": "2026-10-28", "x": NaN}',
    ],
)
def test_projection_rejects_invalid_current_board_json(raw):
    result = _project(board=raw)
    assert result["relation"] == "UNAVAILABLE"
    assert "CURRENT_BOARD_JSON_INVALID" in result["reason_codes"]
    # The raw byte identity is still reported even though the JSON is invalid.
    assert result["current_board"]["sha256"] == _sha(raw)
    assert result["current_board"]["source_asof"] is None


@pytest.mark.parametrize(
    "raw",
    [b"not json", b"[1,2]", b'{"a": 1, "a": 2}',
     b'{"asof": "2026-10-28", "asof": "2026-10-27"}'],
)
def test_projection_rejects_invalid_index_json(raw):
    result = _project(index=raw)
    assert result["relation"] == "UNAVAILABLE"
    assert "INDEX_JSON_INVALID" in result["reason_codes"]
    assert result["index"]["sha256"] == _sha(raw)
    assert result["index"]["asof"] is None


@pytest.mark.parametrize("raw", [b"not json", b"[1,2]", b'{"a": 1, "a": 2}'])
def test_projection_rejects_invalid_snapshot_json(raw):
    result = _project(snapshot=raw)
    assert result["relation"] == "UNAVAILABLE"
    assert "SNAPSHOT_JSON_INVALID" in result["reason_codes"]
    assert result["origination_board"]["snapshot_verified"] is False


def test_projection_requires_board_as_of():
    payload = dict(A_OBJ)
    del payload["as_of"]
    result = _project(board=_dumps(payload))
    assert result["relation"] == "UNAVAILABLE"
    assert "CURRENT_BOARD_ASOF_INVALID" in result["reason_codes"]


def test_projection_requires_source_board_asof_to_agree_with_frozen_snapshot():
    result = _project(index=_index_bytes(source_board_asof="2026-10-27"))
    assert result["relation"] == "UNAVAILABLE"
    assert "SOURCE_BOARD_ASOF_MISMATCH" in result["reason_codes"]
    # Byte identity still holds; the binding metadata disagrees with it.
    assert result["origination_board"]["snapshot_verified"] is True
    assert result["origination_board"]["source_asof"] == "2026-10-28"


def test_projection_requires_snapshot_as_of():
    payload = dict(A_OBJ)
    payload["as_of"] = "not-a-date"
    result = _project(snapshot=_dumps(payload))
    assert result["relation"] == "UNAVAILABLE"
    assert "SNAPSHOT_ASOF_INVALID" in result["reason_codes"]
    assert result["origination_board"]["source_asof"] is None


def test_index_source_asof_may_differ_from_source_board_asof():
    result = _project(index=_index_bytes(source_asof="2026-10-29"))
    assert result["relation"] == "SAME_SOURCE"
    assert result["index"]["source_asof"] == "2026-10-29"
    assert result["index"]["asof"] == "2026-10-28"
    assert result["origination_board"]["source_asof"] == "2026-10-28"


def test_snapshot_verified_reports_byte_identity_only():
    """``snapshot_verified`` states that the snapshot bytes are exactly the
    declared digest and parse as an object.  It is not a settlement and it
    does not repair a broken index binding."""
    result = _project(index=_index_bytes(source_board_snapshot_encoding="json"))
    assert result["origination_board"]["snapshot_verified"] is True
    assert result["relation"] == "UNAVAILABLE"
    assert "INDEX_SNAPSHOT_ENCODING_INVALID" in result["reason_codes"]


# ---------------------------------------------------------------------------
# File-bound reader
# ---------------------------------------------------------------------------


def test_reader_reports_same_source_from_canonical_gzip(tmp_path):
    _write_snapshot(tmp_path, A_SHA, BOARD_A)
    result = _read(tmp_path)
    assert result["relation"] == "SAME_SOURCE"
    assert result["origination_board"]["snapshot_verified"] is True
    assert result["origination_board"]["sha256"] == A_SHA
    assert result["current_board"]["sha256"] == A_SHA


def test_reader_reports_separate_epochs_when_live_board_changed(tmp_path):
    _write_snapshot(tmp_path, A_SHA, BOARD_A)
    result = _read(tmp_path, board=BOARD_B)
    assert result["relation"] == "SEPARATE_EPOCHS"
    assert result["current_board"]["sha256"] == B_SHA
    assert result["origination_board"]["sha256"] == A_SHA


def test_reader_fails_closed_when_snapshot_file_is_missing(tmp_path):
    result = _read(tmp_path)
    assert result["relation"] == "UNAVAILABLE"
    assert "SNAPSHOT_FILE_MISSING" in result["reason_codes"]
    assert result["origination_board"]["snapshot_verified"] is False


def test_reader_fails_closed_when_data_dir_is_missing(tmp_path):
    result = _read(tmp_path / "absent")
    assert result["relation"] == "UNAVAILABLE"
    assert "DATA_DIR_UNAVAILABLE" in result["reason_codes"]


def test_reader_fails_closed_when_data_dir_is_a_file(tmp_path):
    target = tmp_path / "not-a-directory"
    target.write_bytes(b"x")
    result = _read(target)
    assert result["relation"] == "UNAVAILABLE"
    assert "DATA_DIR_UNAVAILABLE" in result["reason_codes"]


@pytest.mark.parametrize("corrupt", [b"not a gzip stream", b"", b"\x1f\x8b\x08\x00garbage"])
def test_reader_fails_closed_on_corrupt_gzip(tmp_path, corrupt):
    directory = tmp_path / "prophet" / "origination_sources"
    directory.mkdir(parents=True)
    (directory / GZ_NAME).write_bytes(corrupt)
    result = _read(tmp_path)
    assert result["relation"] == "UNAVAILABLE"
    assert "SNAPSHOT_DECOMPRESS_FAILED" in result["reason_codes"]


def test_reader_fails_closed_on_truncated_gzip(tmp_path):
    directory = tmp_path / "prophet" / "origination_sources"
    directory.mkdir(parents=True)
    (directory / GZ_NAME).write_bytes(gzip.compress(BOARD_A)[:6])
    result = _read(tmp_path)
    assert result["relation"] == "UNAVAILABLE"
    assert "SNAPSHOT_DECOMPRESS_FAILED" in result["reason_codes"]


def test_reader_fails_closed_when_canonical_path_is_a_directory(tmp_path):
    (tmp_path / "prophet" / "origination_sources" / GZ_NAME).mkdir(parents=True)
    result = _read(tmp_path)
    assert result["relation"] == "UNAVAILABLE"
    assert "SNAPSHOT_FILE_UNREADABLE" in result["reason_codes"]


def test_reader_rejects_snapshot_bytes_that_do_not_match_declared_sha(tmp_path):
    _write_snapshot(tmp_path, A_SHA, BOARD_B)
    result = _read(tmp_path)
    assert result["relation"] == "UNAVAILABLE"
    assert "SNAPSHOT_SHA_MISMATCH" in result["reason_codes"]
    assert result["origination_board"]["snapshot_verified"] is False


def test_reader_rejects_symlinked_snapshot_that_escapes_data_dir(tmp_path):
    outside = pathlib.Path(tempfile.mkdtemp(prefix="prophet-outside-"))
    try:
        outside_file = outside / GZ_NAME
        outside_file.write_bytes(gzip.compress(BOARD_A))
        directory = tmp_path / "prophet" / "origination_sources"
        directory.mkdir(parents=True)
        (directory / GZ_NAME).symlink_to(outside_file)
        result = _read(tmp_path)
        assert result["relation"] == "UNAVAILABLE"
        assert "SNAPSHOT_PATH_ESCAPE" in result["reason_codes"]
        assert result["origination_board"]["snapshot_verified"] is False
    finally:
        shutil.rmtree(outside, ignore_errors=True)


def test_reader_rejects_redirected_directory_that_escapes_data_dir(tmp_path):
    outside = pathlib.Path(tempfile.mkdtemp(prefix="prophet-outside-"))
    try:
        storage = outside / "origination_sources"
        storage.mkdir(parents=True)
        (storage / GZ_NAME).write_bytes(gzip.compress(BOARD_A))
        (tmp_path / "prophet").symlink_to(outside, target_is_directory=True)
        result = _read(tmp_path)
        assert result["relation"] == "UNAVAILABLE"
        assert "SNAPSHOT_PATH_ESCAPE" in result["reason_codes"]
    finally:
        shutil.rmtree(outside, ignore_errors=True)


def test_reader_rejects_even_an_in_tree_symlink(tmp_path):
    directory = tmp_path / "prophet" / "origination_sources"
    directory.mkdir(parents=True)
    real = tmp_path / "prophet" / "stored-elsewhere.bin"
    real.write_bytes(gzip.compress(BOARD_A))
    (directory / GZ_NAME).symlink_to(real)
    result = _read(tmp_path)
    assert result["relation"] == "UNAVAILABLE"
    assert "SNAPSHOT_PATH_ESCAPE" in result["reason_codes"]


def test_reader_does_not_read_any_file_when_the_binding_is_invalid(tmp_path):
    _write_snapshot(tmp_path, A_SHA, BOARD_A)
    index = _index_bytes(
        source_board_snapshot_path="data/prophet/origination_sources/other.json.gz"
    )
    result = _read(tmp_path, index=index)
    assert result["relation"] == "UNAVAILABLE"
    assert "INDEX_SNAPSHOT_PATH_INVALID" in result["reason_codes"]
    assert "SNAPSHOT_NOT_READ" in result["reason_codes"]


def test_reader_rejects_oversized_snapshot(tmp_path, monkeypatch):
    _write_snapshot(tmp_path, A_SHA, BOARD_A)
    monkeypatch.setattr(pse, "MAX_SNAPSHOT_BYTES", 16)
    result = _read(tmp_path)
    assert result["relation"] == "UNAVAILABLE"
    assert "SNAPSHOT_TOO_LARGE" in result["reason_codes"]


def test_reader_never_writes_to_the_data_dir(tmp_path):
    _write_snapshot(tmp_path, A_SHA, BOARD_A)
    before = _tree(tmp_path)
    _read(tmp_path)
    _read(tmp_path, index=_index_bytes(source_board_snapshot_encoding="json"))
    _read(tmp_path / "absent")
    assert _tree(tmp_path) == before


# ---------------------------------------------------------------------------
# Contract: strict allow-list, no private fields, never settled
# ---------------------------------------------------------------------------


def _all_scenarios():
    yield _project()
    yield _project(board=BOARD_B)
    yield _project(board=None, index=None, snapshot=None)
    yield _project(board=b"{}", index=b"{}", snapshot=b"{}")
    yield _project(index=_index_bytes(source_board_asof="1999-01-01"))


def test_result_shape_is_strictly_allowlisted():
    for result in _all_scenarios():
        assert set(result) == TOP_LEVEL_KEYS
        assert set(result["current_board"]) == CURRENT_BOARD_KEYS
        assert set(result["index"]) == INDEX_KEYS
        assert set(result["origination_board"]) == ORIGINATION_BOARD_KEYS
        assert result["schema"] == "prophet_source_epochs.v1"
        assert result["settlement_status"] == "PENDING"
        assert result["relation"] in {"SAME_SOURCE", "SEPARATE_EPOCHS", "UNAVAILABLE"}
        assert isinstance(result["reason_codes"], list)


def test_result_copies_no_private_or_free_form_source_material():
    for result in _all_scenarios():
        blob = json.dumps(result, sort_keys=True)
        for leak in ("AAA", "BBB", "CCC", "origination_sources",
                     "source_board_snapshot_path", "source_board_sha256",
                     "market_date", "bundle", "plan"):
            assert leak not in blob


def test_result_dates_and_digests_are_well_formed():
    for result in _all_scenarios():
        for digest in (result["current_board"]["sha256"], result["index"]["sha256"],
                       result["origination_board"]["sha256"]):
            assert digest is None or (
                len(digest) == 64
                and all(character in "0123456789abcdef" for character in digest)
            )
        for value in (result["current_board"]["source_asof"], result["index"]["asof"],
                      result["index"]["source_asof"],
                      result["origination_board"]["source_asof"]):
            assert value is None or (
                len(value) == 10 and value[4] == "-" and value[7] == "-"
                and value.replace("-", "").isdigit()
            )
        assert isinstance(result["origination_board"]["snapshot_verified"], bool)


def test_reason_codes_come_from_the_fixed_vocabulary():
    observed = set()
    for result in _all_scenarios():
        observed.update(result["reason_codes"])
    assert observed <= set(pse.REASON_CODES)
    assert "FOUR_FAMILY_RECEIPT_NOT_EVALUATED" in observed


def test_every_outcome_carries_the_four_family_receipt_marker():
    for result in _all_scenarios():
        assert "FOUR_FAMILY_RECEIPT_NOT_EVALUATED" in result["reason_codes"]
        assert result["reason_codes"][0] == "FOUR_FAMILY_RECEIPT_NOT_EVALUATED"
        assert result["settlement_status"] == "PENDING"
        assert "SETTLED" not in json.dumps(result)


def test_non_bytes_input_is_rejected():
    with pytest.raises(TypeError):
        pse.project_source_epochs(
            board_bytes="not bytes", index_bytes=INDEX_I, snapshot_bytes=BOARD_A
        )

def test_snapshot_path_replacement_cannot_change_the_open_source(tmp_path, monkeypatch):
    _write_snapshot(tmp_path, A_SHA, BOARD_A)
    target = tmp_path / "prophet" / "origination_sources" / GZ_NAME
    replacement = tmp_path / "other.json.gz"
    replacement.write_bytes(gzip.compress(BOARD_B))
    original = gzip.GzipFile
    calls = []
    def replace_after_probe(*args, **kwargs):
        calls.append(kwargs["fileobj"])
        target.unlink()
        target.symlink_to(replacement)
        return original(*args, **kwargs)
    monkeypatch.setattr(gzip, "GzipFile", replace_after_probe)
    result = _read(tmp_path)
    assert len(calls) == 1
    assert result["relation"] == "SAME_SOURCE"
    assert result["origination_board"]["sha256"] == A_SHA


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32", "utf-8-sig"])
def test_non_utf8_or_bom_index_is_unavailable(encoding):
    encoded = INDEX_I.decode("utf-8").encode(encoding)
    result = _project(index=encoded)
    assert result["relation"] == "UNAVAILABLE"
    assert "INDEX_JSON_INVALID" in result["reason_codes"]
