"""Bounded retained International Library reader — receipt shape and byte binding.

The tree built here is a SYNTHETIC local stand-in for a retained publisher
output: it exists so the reader's binding rules can be exercised without the
expensive analysis.  It is not a publisher fixture and it is not a substitute
for the normal publisher path — only the byte manifest that the trusted native
builder captures over the real retained tree is modelled here.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.intl_library_retained import (  # noqa: E402
    RetainedLibraryError,
    load_retained_library,
)


_SETUPS_BYTES = b'{"buy":[{"ticker":"AAA","price":12.5}],"sell":[]}'
_SOURCE_HEAD = "0123456789abcdef" * 2 + "01234567"
_MAX_FILE_BYTES = 32 * 1024 * 1024


# ── synthetic retained tree ────────────────────────────────────────────────
def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def _build_tree(tmp_path: Path, *, setups: bytes = _SETUPS_BYTES) -> tuple[Path, Path]:
    """Return the (data_root, site_root) of a synthetic retained tree."""
    data_root = tmp_path / "data"
    site_root = tmp_path / "site"
    _write(data_root / "intl_search" / "closes.parquet", b"PAR1-closes")
    _write(data_root / "intl_search" / "members.parquet", b"PAR1-members")
    _write(data_root / "intl_search" / "coverage.parquet", b'{"covered":988}')
    _write(site_root / "intlstockdata" / "index.json", b'{"index":[]}')
    _write(site_root / "intlstockdata" / "AAA.json", b'{"ticker":"AAA"}')
    _write(site_root / "intlohlc" / "AAA.json", b'{"ohlc":[]}')
    _write(site_root / "factordata" / "intl_setups.json", setups)
    return data_root, site_root


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _capture(root: Path, *, prefix: str = "") -> dict[str, str]:
    """Mirror the builder's capture step: every regular file under ``root``."""
    manifest: dict[str, str] = {}
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            full = Path(base) / name
            manifest[prefix + full.relative_to(root).as_posix()] = _sha256(full)
    return manifest


def _receipt(data_root: Path, site_root: Path) -> dict[str, object]:
    site_files = _capture(site_root / "intlstockdata", prefix="intlstockdata/")
    site_files.update(_capture(site_root / "intlohlc", prefix="intlohlc/"))
    site_files["factordata/intl_setups.json"] = _sha256(
        site_root / "factordata" / "intl_setups.json"
    )
    return {
        "schema": "intl.library_retained.v1",
        "producer": "scripts.build_intl_library.main",
        "source_head": _SOURCE_HEAD,
        "data_files": _capture(data_root),
        "site_files": site_files,
    }


def _snapshot(root: Path) -> dict[str, tuple[int, int, str]]:
    """Return the writable state of every file under ``root``."""
    state: dict[str, tuple[int, int, str]] = {}
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            full = Path(base) / name
            info = full.stat()
            state[full.relative_to(root).as_posix()] = (
                info.st_size,
                info.st_mtime_ns,
                _sha256(full),
            )
    return state


def _load(data_root: Path, site_root: Path, receipt: dict[str, object]) -> dict:
    return load_retained_library(
        data_root=data_root, site_root=site_root, receipt=receipt
    )


# ── the happy path ─────────────────────────────────────────────────────────
def test_load_returns_the_retained_setup_document(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    document = _load(data_root, site_root, _receipt(data_root, site_root))
    assert document == json.loads(_SETUPS_BYTES.decode("utf-8"))


def test_successful_reuse_writes_nothing(tmp_path):
    """The reuse path is read-only: the retained tree is byte-identical after."""
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    before = (_snapshot(data_root), _snapshot(site_root))
    document = _load(data_root, site_root, receipt)
    after = (_snapshot(data_root), _snapshot(site_root))
    assert document == json.loads(_SETUPS_BYTES.decode("utf-8"))
    assert before == after


def test_returned_document_comes_from_the_verified_bytes(tmp_path):
    """The parsed document is bound to the bytes the receipt hashed."""
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    document = _load(data_root, site_root, receipt)
    on_disk = json.loads(
        (site_root / "factordata" / "intl_setups.json").read_text(encoding="utf-8")
    )
    assert document == on_disk


def test_empty_setup_document_is_returned_as_is(tmp_path):
    data_root, site_root = _build_tree(tmp_path, setups=b"{}")
    document = _load(data_root, site_root, _receipt(data_root, site_root))
    assert document == {}


# ── changed / missing / extra content ──────────────────────────────────────
def test_changed_data_file_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    (data_root / "intl_search" / "closes.parquet").write_bytes(b"PAR1-closes-v2")
    with pytest.raises(RetainedLibraryError, match="sha256 mismatch"):
        _load(data_root, site_root, receipt)


def test_changed_site_output_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    (site_root / "intlstockdata" / "index.json").write_bytes(b'{"index":["AAA"]}')
    with pytest.raises(RetainedLibraryError, match="sha256 mismatch"):
        _load(data_root, site_root, receipt)


def test_changed_setup_document_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    (site_root / "factordata" / "intl_setups.json").write_bytes(b'{"buy":[]}')
    with pytest.raises(RetainedLibraryError, match="sha256 mismatch"):
        _load(data_root, site_root, receipt)


def test_missing_site_output_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    (site_root / "intlohlc" / "AAA.json").unlink()
    with pytest.raises(RetainedLibraryError, match="not present"):
        _load(data_root, site_root, receipt)


def test_missing_data_file_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    (data_root / "intl_search" / "members.parquet").unlink()
    with pytest.raises(RetainedLibraryError, match="not present"):
        _load(data_root, site_root, receipt)


def test_extra_site_output_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    _write(site_root / "intlstockdata" / "BBB.json", b'{"ticker":"BBB"}')
    with pytest.raises(RetainedLibraryError, match="not listed in the receipt"):
        _load(data_root, site_root, receipt)


def test_extra_data_file_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    _write(data_root / "intl_search" / "extra.json", b"{}")
    with pytest.raises(RetainedLibraryError, match="not listed in the receipt"):
        _load(data_root, site_root, receipt)


def test_site_files_outside_the_canonical_outputs_are_not_inventoried(tmp_path):
    """The site inventory is scoped to the library outputs, not the whole root."""
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    _write(site_root / "factordata" / "other.json", b"{}")
    _write(site_root / "pages" / "intl.html", b"<html></html>")
    document = _load(data_root, site_root, receipt)
    assert document == json.loads(_SETUPS_BYTES.decode("utf-8"))


# ── unsafe receipt paths ───────────────────────────────────────────────────
@pytest.mark.parametrize(
    ("unsafe_path", "reason"),
    [
        ("../escape.json", "'..' component"),
        ("intl_search/../../escape.json", "'..' component"),
        ("/etc/passwd", "must be relative"),
        ("C:/escape.json", "must be relative"),
        ("intl_search\\closes.parquet", "contains a backslash"),
        ("intl_search/clo\nses.parquet", "control character"),
        ("intl_search/clo\x00ses.parquet", "control character"),
        ("./intl_search/closes.parquet", "'.' component"),
        ("intl_search/./closes.parquet", "'.' component"),
        ("intl_search//closes.parquet", "empty component"),
        ("intl_search/closes.parquet/", "empty component"),
        ("", "must not be empty"),
    ],
)
def test_unsafe_receipt_path_is_rejected(tmp_path, unsafe_path, reason):
    """An unsafe path is refused on its shape, not merely found missing."""
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["data_files"][unsafe_path] = "0" * 64
    with pytest.raises(RetainedLibraryError, match=reason):
        _load(data_root, site_root, receipt)


def test_unsafe_site_receipt_path_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["site_files"]["../../escape.json"] = "0" * 64
    with pytest.raises(RetainedLibraryError, match="'..' component"):
        _load(data_root, site_root, receipt)


def test_a_file_outside_the_data_root_is_never_reachable(tmp_path):
    """A traversal must not reach a real file that sits outside the root."""
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    outside = tmp_path / "escape.json"
    outside.write_bytes(b"{}")
    receipt["data_files"]["../escape.json"] = _sha256(outside)
    with pytest.raises(RetainedLibraryError, match="'..' component"):
        _load(data_root, site_root, receipt)


def test_duplicate_normalized_path_is_rejected(tmp_path):
    """Two keys that normalize to one path may not shadow each other."""
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["data_files"]["intl_search/café.json"] = "0" * 64
    receipt["data_files"]["intl_search/cafe\u0301.json"] = "0" * 64
    with pytest.raises(RetainedLibraryError, match="duplicate normalized path"):
        _load(data_root, site_root, receipt)


def test_non_canonical_site_path_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["site_files"]["elsewhere/file.json"] = "0" * 64
    with pytest.raises(RetainedLibraryError, match="canonical library paths"):
        _load(data_root, site_root, receipt)


# ── symlinks ───────────────────────────────────────────────────────────────
def test_symlinked_data_file_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"not-a-library-file")
    os.symlink(outside, data_root / "intl_search" / "link.parquet")
    with pytest.raises(RetainedLibraryError, match="symlink"):
        _load(data_root, site_root, receipt)


def test_symlinked_data_directory_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "planted.json").write_bytes(b"{}")
    os.symlink(outside, data_root / "intl_search" / "planted")
    with pytest.raises(RetainedLibraryError, match="symlink"):
        _load(data_root, site_root, receipt)


def test_symlinked_setup_document_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    setups = site_root / "factordata" / "intl_setups.json"
    real = tmp_path / "real_setups.json"
    real.write_bytes(_SETUPS_BYTES)
    setups.unlink()
    os.symlink(real, setups)
    with pytest.raises(RetainedLibraryError, match="symlink"):
        _load(data_root, site_root, receipt)


def test_symlinked_site_output_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    outside = tmp_path / "outside_index.json"
    outside.write_bytes(b'{"index":[]}')
    target = site_root / "intlstockdata" / "index.json"
    target.unlink()
    os.symlink(outside, target)
    with pytest.raises(RetainedLibraryError, match="symlink"):
        _load(data_root, site_root, receipt)


# ── receipt shape ──────────────────────────────────────────────────────────
def test_wrong_schema_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["schema"] = "intl.library_retained.v2"
    with pytest.raises(RetainedLibraryError, match="schema must be"):
        _load(data_root, site_root, receipt)


def test_wrong_producer_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["producer"] = "scripts.build_intl_library.other"
    with pytest.raises(RetainedLibraryError, match="producer must be"):
        _load(data_root, site_root, receipt)


def test_unbound_extra_receipt_key_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["generated_at"] = "2026-11-04T00:00:00Z"
    with pytest.raises(RetainedLibraryError, match="unbound extra keys"):
        _load(data_root, site_root, receipt)


def test_missing_receipt_key_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    del receipt["source_head"]
    with pytest.raises(RetainedLibraryError, match="missing required keys"):
        _load(data_root, site_root, receipt)


def test_non_mapping_receipt_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    with pytest.raises(RetainedLibraryError, match="must be a mapping"):
        _load(data_root, site_root, ["not", "a", "receipt"])


def test_url_shaped_root_is_rejected(tmp_path):
    """The roots are local paths from the builder, never a URL parameter."""
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    with pytest.raises(RetainedLibraryError, match="never a URL"):
        load_retained_library(
            data_root="https://example.invalid/data",
            site_root=site_root,
            receipt=receipt,
        )


def test_missing_root_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    with pytest.raises(RetainedLibraryError):
        load_retained_library(
            data_root=tmp_path / "absent", site_root=site_root, receipt=receipt
        )


@pytest.mark.parametrize("bad_head", ["abc", "A" * 40, "0" * 39, "0" * 41, "g" * 40, 7])
def test_malformed_source_head_is_rejected(tmp_path, bad_head):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["source_head"] = bad_head
    with pytest.raises(RetainedLibraryError, match="source_head"):
        _load(data_root, site_root, receipt)


def test_source_head_is_recorded_but_not_authenticated(tmp_path):
    """The head is provenance the caller asserts; the reader does not verify it."""
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["source_head"] = "f" * 40
    document = _load(data_root, site_root, receipt)
    assert document == json.loads(_SETUPS_BYTES.decode("utf-8"))


@pytest.mark.parametrize("bad_digest", ["z" * 64, "A" * 64, "0" * 63, "0" * 65, 1])
def test_non_hex_digest_is_rejected(tmp_path, bad_digest):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["data_files"]["intl_search/closes.parquet"] = bad_digest
    with pytest.raises(RetainedLibraryError, match="lowercase 64-hex sha256"):
        _load(data_root, site_root, receipt)


def test_empty_manifest_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["site_files"] = {}
    with pytest.raises(RetainedLibraryError, match="must not be empty"):
        _load(data_root, site_root, receipt)


def test_missing_required_data_path_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    del receipt["data_files"]["intl_search/coverage.parquet"]
    with pytest.raises(RetainedLibraryError, match="missing required path"):
        _load(data_root, site_root, receipt)


def test_missing_required_site_path_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    del receipt["site_files"]["intlstockdata/index.json"]
    with pytest.raises(RetainedLibraryError, match="missing required path"):
        _load(data_root, site_root, receipt)


# ── the setup document ─────────────────────────────────────────────────────
def test_malformed_setup_document_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path, setups=b'{"buy":')
    with pytest.raises(RetainedLibraryError, match="not valid JSON"):
        _load(data_root, site_root, _receipt(data_root, site_root))


def test_non_object_setup_document_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path, setups=b"[1,2,3]")
    with pytest.raises(RetainedLibraryError, match="must decode to an object"):
        _load(data_root, site_root, _receipt(data_root, site_root))


def test_duplicate_json_keys_are_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path, setups=b'{"buy":[],"buy":[]}')
    with pytest.raises(RetainedLibraryError, match="not valid JSON"):
        _load(data_root, site_root, _receipt(data_root, site_root))


# ── explicit caps ──────────────────────────────────────────────────────────
def test_manifest_entry_cap_is_enforced(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    receipt["data_files"] = {
        f"intl_search/filler-{index:05d}.bin": "0" * 64 for index in range(20001)
    }
    with pytest.raises(RetainedLibraryError, match="20000-entry cap"):
        _load(data_root, site_root, receipt)


def test_oversized_file_is_rejected(tmp_path):
    data_root, site_root = _build_tree(tmp_path)
    oversized = data_root / "intl_search" / "oversized.bin"
    _write(oversized, b"")
    with oversized.open("r+b") as handle:
        handle.truncate(_MAX_FILE_BYTES + 1)
    receipt = _receipt(data_root, site_root)
    with pytest.raises(RetainedLibraryError, match="byte limit"):
        _load(data_root, site_root, receipt)

@pytest.mark.parametrize('root_kind', ['data', 'site'])
def test_symlinked_root_is_rejected(tmp_path, root_kind):
    data_root, site_root = _build_tree(tmp_path)
    receipt = _receipt(data_root, site_root)
    alias = tmp_path / ('alias-' + root_kind)
    alias.symlink_to(data_root if root_kind == 'data' else site_root, target_is_directory=True)
    with pytest.raises(RetainedLibraryError, match='symlink'):
        _load(alias if root_kind == 'data' else data_root,
              alias if root_kind == 'site' else site_root, receipt)
