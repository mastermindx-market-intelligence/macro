"""Cheap idempotency: current pack identity from pointer + manifest only."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from engine.entry_radar import live_pack as lp
from scripts import entry_radar_live_pack as pack_mod

_MANIFEST_OMIT = object()


def _layout(
    state: Path,
    *,
    as_of: str = "2026-10-02",
    pack_hash: str = "abc123",
    manifest: dict | list | str | None | object = None,
    pointer: dict | list | str | None = None,
    substrate: bool = True,
) -> None:
    root = lp.pack_root(state)
    root.mkdir(parents=True, exist_ok=True)
    if pointer is None:
        pointer = {"as_of": as_of, "pack_hash": pack_hash}
    if isinstance(pointer, str):
        (root / lp._POINTER_NAME).write_text(pointer, encoding="utf-8")
    else:
        (root / lp._POINTER_NAME).write_text(json.dumps(pointer), encoding="utf-8")
    session_dir = root / as_of
    session_dir.mkdir(parents=True, exist_ok=True)
    if manifest is _MANIFEST_OMIT:
        pass
    else:
        if manifest is None:
            manifest = {"as_of": as_of, "pack_hash": pack_hash}
        if isinstance(manifest, str):
            (session_dir / lp._MANIFEST_NAME).write_text(manifest, encoding="utf-8")
        else:
            (session_dir / lp._MANIFEST_NAME).write_text(
                json.dumps(manifest), encoding="utf-8"
            )
    if substrate:
        (session_dir / lp._SUBSTRATE_NAME).write_bytes(b"")


def test_consistent_layout_returns_identity_without_reading_substrate(tmp_path):
    _layout(tmp_path)
    assert lp.current_pack_identity(tmp_path) == {
        "as_of": "2026-10-02",
        "pack_hash": "abc123",
    }


@pytest.mark.parametrize(
    "setup",
    [
        lambda s: None,
        lambda s: _layout(s, pointer="{"),
        lambda s: _layout(s, pointer=[]),
        lambda s: _layout(s, pointer={"as_of": "2026-10-02"}),
        lambda s: _layout(s, pointer={"as_of": "2026-10-02", "pack_hash": ""}),
        lambda s: _layout(s, pointer={"as_of": 20261002, "pack_hash": "abc123"}),
        lambda s: _layout(s, pointer={"as_of": "2026-10-2", "pack_hash": "abc123"}),
        lambda s: _layout(s, manifest=_MANIFEST_OMIT),
        lambda s: _layout(s, manifest="{"),
        lambda s: _layout(s, manifest=[]),
        lambda s: _layout(
            s, manifest={"as_of": "2026-10-02", "pack_hash": "other"}
        ),
        lambda s: _layout(
            s, manifest={"as_of": "2026-10-01", "pack_hash": "abc123"}
        ),
        lambda s: _layout(s, substrate=False),
    ],
    ids=[
        "no_pack_directory",
        "pointer_not_json",
        "pointer_json_list",
        "pointer_no_pack_hash",
        "pointer_empty_pack_hash",
        "pointer_as_of_integer",
        "pointer_as_of_non_canonical_date",
        "manifest_missing",
        "manifest_not_json",
        "manifest_json_list",
        "manifest_pack_hash_differs",
        "manifest_as_of_differs",
        "substrate_missing",
    ],
)
def test_invalid_layout_returns_none(tmp_path, setup):
    setup(tmp_path)
    assert lp.current_pack_identity(tmp_path) is None


def test_path_traversal_pointer_returns_none(tmp_path):
    as_of = "../x"
    _layout(
        tmp_path,
        as_of=as_of,
        manifest={"as_of": as_of, "pack_hash": "abc123"},
        pointer={"as_of": as_of, "pack_hash": "abc123"},
    )
    assert lp.current_pack_identity(tmp_path) is None


def test_main_skip_without_load_pack(tmp_path, monkeypatch, capsys):
    _layout(tmp_path)
    monkeypatch.setattr(pack_mod.lp, "assert_published_spec_hashes", lambda: None)
    monkeypatch.setattr(
        pack_mod.lp,
        "load_pack",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("load_pack must not be called")
        ),
    )
    rc = pack_mod.main(["--as-of", "2026-10-02", "--state-dir", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "already current for 2026-10-02" in out
    assert "pack_hash abc123" in out


class _Proceeded(Exception):
    pass


@pytest.mark.parametrize(
    "argv",
    [
        ["--as-of", "2026-10-02", "--state-dir", "{state}"],
        ["--as-of", "2026-10-02", "--state-dir", "{state}"],
        ["--as-of", "2026-10-02", "--state-dir", "{state}"],
        ["--as-of", "2026-10-02", "--force", "--state-dir", "{state}"],
    ],
    ids=[
        "corrupt_pointer",
        "pointer_manifest_hash_mismatch",
        "wrong_as_of_date",
        "force_flag",
    ],
)
def test_main_rebuild_paths(tmp_path, monkeypatch, argv, request):
    monkeypatch.setattr(
        pack_mod, "load_config", lambda *_a, **_k: (_ for _ in ()).throw(_Proceeded())
    )
    monkeypatch.setattr(pack_mod.lp, "assert_published_spec_hashes", lambda: None)
    monkeypatch.setattr(
        pack_mod.lp,
        "load_pack",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("load_pack must not be called")
        ),
    )
    case = request.node.callspec.id
    if case == "corrupt_pointer":
        _layout(tmp_path, pointer="{")
    elif case == "pointer_manifest_hash_mismatch":
        _layout(tmp_path, manifest={"as_of": "2026-10-02", "pack_hash": "mismatch"})
    elif case == "wrong_as_of_date":
        _layout(tmp_path, as_of="2026-10-01")
    else:
        _layout(tmp_path)
    resolved = [a.replace("{state}", str(tmp_path)) for a in argv]
    with pytest.raises(_Proceeded):
        pack_mod.main(resolved)


def test_main_source_uses_current_pack_identity_not_load_pack():
    src = inspect.getsource(pack_mod.main)
    before_collect = src.split('_stage("collect")')[0]
    assert "lp.current_pack_identity(" in before_collect
    assert "load_pack(" not in before_collect
