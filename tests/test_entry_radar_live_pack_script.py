"""scripts/entry_radar_live_pack.py — substrate_sink and --stream-substrate (P-SCALE-2 lane C)."""
from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

_SCRIPT = _ROOT / "scripts" / "entry_radar_live_pack.py"
_spec = importlib.util.spec_from_file_location("entry_radar_live_pack", _SCRIPT)
assert _spec and _spec.loader
_erp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_erp)

from engine.entry_radar import live_pack as lp  # noqa: E402
from engine.entry_radar.pack_spool import ParquetSpoolSink  # noqa: E402
from tests.test_entry_radar_w4_pack import build  # noqa: E402


def test_SC1_substrate_sink_false_no_op(tmp_path):
    sink, cleanup = _erp.substrate_sink(False, tmp_path)
    assert sink is None
    cleanup()
    assert list(tmp_path.iterdir()) == []


def test_SC2_substrate_sink_true_under_state_pack(tmp_path):
    sink, cleanup = _erp.substrate_sink(True, tmp_path)
    assert isinstance(sink, ParquetSpoolSink)
    pack_dir = tmp_path / "pack"
    assert pack_dir.is_dir()
    spool_dirs = [p for p in pack_dir.iterdir() if p.name.startswith(".spool-")]
    assert len(spool_dirs) == 1
    assert spool_dirs[0] in sink.path.parents
    assert str(sink.path).startswith(str(spool_dirs[0]))
    cleanup()
    assert not spool_dirs[0].exists()
    assert pack_dir.is_dir()
    assert list(pack_dir.iterdir()) == []


def test_SC3_substrate_sink_true_no_state_dir():
    sink, cleanup = _erp.substrate_sink(True, None)
    assert isinstance(sink, ParquetSpoolSink)
    spool_parent = sink.path.parent
    assert spool_parent.name.startswith(".spool-")
    assert spool_parent.is_dir()
    cleanup()
    assert not spool_parent.exists()


def test_SC4_save_pack_survives_spool_cleanup(tmp_path):
    sink, cleanup = _erp.substrate_sink(True, tmp_path / "state")
    pack = build(sink=sink)
    state = tmp_path / "state"
    lp.save_pack(pack, state)
    expected_hash = pack.pack_hash
    spool_dir = sink.path.parent
    cleanup()
    assert not spool_dir.exists()
    loaded = lp.load_pack(state)
    assert loaded.pack_hash == expected_hash
    session_dirs = list((state / "pack").glob("*/substrate.parquet"))
    assert session_dirs
    sidecar = Path(f"{session_dirs[0]}.sidecar.json")
    assert sidecar.is_file()


def test_SC5_stream_substrate_in_help(capsys):
    with pytest.raises(SystemExit) as exc:
        _erp.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--stream-substrate" in out


def _state_tree_listing(state: Path) -> list[str]:
    return sorted(str(p.relative_to(state)) for p in state.rglob("*"))


def test_SC6_dry_run_stream_substrate_leaves_state_dir_untouched(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    before = _state_tree_listing(state)
    sink, cleanup = _erp.substrate_sink(True, state, dry_run=True)
    assert isinstance(sink, ParquetSpoolSink)
    spool_parent = sink.path.parent
    assert spool_parent.name.startswith(".spool-")
    assert not (state / "pack").exists()
    cleanup()
    assert not spool_parent.exists()
    assert _state_tree_listing(state) == before


def test_SC7_reap_spool_orphans(tmp_path):
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    old_spool = pack_dir / ".spool-old"
    old_spool.mkdir()
    new_spool = pack_dir / ".spool-new"
    new_spool.mkdir()
    session_dir = pack_dir / "2026-08-13"
    session_dir.mkdir()
    aged = time.time() - 7 * 3600
    os.utime(old_spool, (aged, aged))
    removed = _erp.reap_spool_orphans(pack_dir)
    assert removed == 1
    assert not old_spool.exists()
    assert new_spool.is_dir()
    assert session_dir.is_dir()
