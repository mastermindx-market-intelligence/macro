"""Hermetic arrival only. No SSH, native source, provider, bucket or app effect."""
from dataclasses import replace
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import stat

import pytest

from engine import options_scenario_source_arrival as arrival
from engine import options_hub_retention as retention
from engine import options_scenario_capture as capture
from tests.test_options_scenario_capture import world

TODAY = date(2026, 10, 23)


def tree(tmp_path):
    (tmp_path / "gex").mkdir()
    return tmp_path


def run(h, out_dir, **kwargs):
    return arrival.arrive_gex_source(h.descriptor_owner, h.gex_bytes,
                                    producer_out_dir=out_dir, today=TODAY, **kwargs)


def test_original_whitespace_and_unknown_fields_survive_arrival_then_existing_capture(tmp_path):
    h = world(with_moves=False)
    payload = json.loads(h.gex_bytes)
    payload["source_extra"] = {"unicode": "保留原始字节", "unknown": None}
    # This serialized sequence is the fixture producer's original, not output
    # reconstructed by the arrival helper.
    h.gex_bytes = ("\n " + json.dumps(payload, ensure_ascii=False, indent=3) + "\n").encode()
    h.gex_ref = retention.reference_for_bytes("SPY", "gex", h.gex_bytes, today=TODAY)
    h.descriptor_owner = replace(h.descriptor_owner, gex=h.gex_ref)
    root = tree(tmp_path)
    assert run(h, root) == h.gex_ref
    target = root / "gex/SPY.json"
    assert target.read_bytes() == h.gex_bytes
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert sorted(p.name for p in target.parent.iterdir()) == ["SPY.json"]
    assert not h.reads and not h.s3.log and not h.saves
    args = {k: v for k, v in h.params.items() if k != "producer_read"}
    result = capture.capture_built_scenario_sources(h.descriptor_owner, h.viewer, out_dir=root, **args)
    assert h.s3.objects[h.gex_ref.key] == h.gex_bytes
    assert result.boundary()["moves"] is None
    assert result.boundary()["canonical_save_performed"] is False


def test_explicit_source_observation_clock_is_preserved_verbatim(tmp_path):
    h = world(with_moves=False)
    p = json.loads(h.gex_bytes)
    clock = "2026-10-22T20:15:00Z"
    p["exposure_projection"] = {"clocks": {"option_observed_at": clock}}
    h.gex_bytes = json.dumps(p).encode()
    h.descriptor_owner = replace(h.descriptor_owner, source_as_of=clock,
        gex=retention.reference_for_bytes("SPY", "gex", h.gex_bytes, today=TODAY))
    run(h, tree(tmp_path))
    assert h.descriptor_owner.source_as_of == clock
    assert (tmp_path / "gex/SPY.json").read_bytes() == h.gex_bytes


@pytest.mark.parametrize("same", [True, False])
def test_existing_file_is_never_overwritten_even_when_bytes_match(tmp_path, same):
    h = world(with_moves=False); root = tree(tmp_path)
    existing = h.gex_bytes if same else b"previous source must survive"
    target = root / "gex/SPY.json"; target.write_bytes(existing)
    inode = target.stat().st_ino
    with pytest.raises(arrival.SourceArrivalRefused, match="target_exists"):
        run(h, root)
    assert target.read_bytes() == existing and target.stat().st_ino == inode
    assert sorted(p.name for p in target.parent.iterdir()) == ["SPY.json"]


def test_moves_request_refuses_intact_before_filesystem_or_retention(monkeypatch, tmp_path):
    h = world(with_moves=True)
    with monkeypatch.context() as m:
        m.setattr(arrival.os, "open", lambda *a, **kw: pytest.fail("must refuse before filesystem IO"))
        with pytest.raises(arrival.SourceArrivalRefused, match="moves_requested"):
            run(h, tmp_path)
    assert h.descriptor_owner.moves is not None
    assert not h.s3.log and not h.reads and not h.saves


@pytest.mark.parametrize("change", ["hash", "length", "root", "schema", "session", "clock", "oversize", "body_type", "grant", "descriptor"])
def test_invalid_source_refuses_before_target_io(monkeypatch, tmp_path, change):
    h = world(with_moves=False)
    if change == "hash": h.gex_bytes = h.gex_bytes.replace(b"600.25", b"601.25")
    elif change == "length": h.gex_bytes += b" "
    elif change in {"root", "schema", "session", "clock"}:
        p = json.loads(h.gex_bytes)
        if change == "root": p["root"] = "QQQ"
        elif change == "schema": p["schema"] = "options_hub.moves/v1"
        elif change == "session": p["asof"] = "2026-10-21"
        else: p["exposure_projection"] = {"clocks": {"option_observed_at": "2026-10-22T20:16:00Z"}}
        h.gex_bytes = json.dumps(p).encode()
        h.descriptor_owner = replace(h.descriptor_owner, gex=replace(h.gex_ref,
            sha256=hashlib.sha256(h.gex_bytes).hexdigest(), byte_length=len(h.gex_bytes)))
    elif change == "oversize": h.gex_bytes = b"x" * (retention.MAX_GEX_BYTES + 1)
    elif change == "body_type": h.gex_bytes = bytearray(h.gex_bytes)
    elif change == "grant": h.descriptor_owner = replace(h.descriptor_owner, grant_id="10000000-0000-4000-8000-000000000001")
    else: h.descriptor_owner = replace(h.descriptor_owner, root="../SPY")
    with monkeypatch.context() as m:
        m.setattr(arrival.os, "open", lambda *a, **kw: pytest.fail("must reject before target IO"))
        with pytest.raises(arrival.SourceArrivalRefused): run(h, tmp_path)
    assert not h.s3.log and not h.saves


@pytest.mark.parametrize("kind", ["relative", "escape", "missing", "missing_gex", "ancestor_link", "root_link", "kind_link", "leaf_link"])
def test_unavailable_or_unsafe_paths_do_not_create_or_follow(tmp_path, kind):
    h = world(with_moves=False)
    outside = tmp_path / "outside"; outside.mkdir(); (outside / "gex").mkdir()
    root = tmp_path / "private"; root.mkdir(); (root / "gex").mkdir()
    marker = outside / "original"; marker.write_bytes(b"preserve")
    if kind == "relative": root = Path("private")
    elif kind == "escape": root = tmp_path / "private/../outside"
    elif kind == "missing": root = tmp_path / "absent"
    elif kind == "missing_gex": (root / "gex").rmdir()
    elif kind == "ancestor_link":
        alias = tmp_path / "alias"; alias.symlink_to(tmp_path, target_is_directory=True); root = alias / "private"
    elif kind == "root_link":
        alias = tmp_path / "alias"; alias.symlink_to(root, target_is_directory=True); root = alias
    elif kind == "kind_link":
        (root / "gex").rmdir(); (root / "gex").symlink_to(outside / "gex", target_is_directory=True)
    else: (root / "gex/SPY.json").symlink_to(marker)
    with pytest.raises(arrival.SourceArrivalRefused): run(h, root)
    assert marker.read_bytes() == b"preserve"
    assert not (outside / "gex/SPY.json").exists()
    assert not (tmp_path / "absent").exists()


def test_competing_create_at_atomic_commit_is_not_overwritten(monkeypatch, tmp_path):
    h = world(with_moves=False); root = tree(tmp_path)
    real_link = os.link
    def race(src, dst, **kwargs):
        (root / "gex/SPY.json").write_bytes(b"other delivery")
        return real_link(src, dst, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(arrival.os, "link", race)
        with pytest.raises(arrival.SourceArrivalRefused, match="target_exists"): run(h, root)
    assert (root / "gex/SPY.json").read_bytes() == b"other delivery"
    assert sorted(p.name for p in (root / "gex").iterdir()) == ["SPY.json"]


def test_failed_write_cleans_own_temporary_and_exposes_no_final(monkeypatch, tmp_path):
    h = world(with_moves=False); root = tree(tmp_path)
    marker = root / "gex/.other-copy.tmp"; marker.write_bytes(b"other")
    def fail(*a): raise OSError("controlled write failure")
    with monkeypatch.context() as m:
        m.setattr(arrival.os, "write", fail)
        with pytest.raises(arrival.SourceArrivalRefused, match="source_arrival_failed"): run(h, root)
    assert sorted(p.name for p in (root / "gex").iterdir()) == [marker.name]
    assert marker.read_bytes() == b"other"


def test_temporary_name_collision_does_not_delete_existing_leaf(monkeypatch, tmp_path):
    h = world(with_moves=False); root = tree(tmp_path)
    class FixedUuid:
        hex = "controlledcollision"
    marker = root / "gex/.p052-gex-controlledcollision.tmp"; marker.write_bytes(b"other source")
    with monkeypatch.context() as m:
        m.setattr(arrival.uuid, "uuid4", lambda: FixedUuid())
        with pytest.raises(arrival.SourceArrivalRefused, match="source_arrival_failed"): run(h, root)
    assert sorted(p.name for p in marker.parent.iterdir()) == [marker.name]
    assert marker.read_bytes() == b"other source"


def test_replaced_temporary_is_not_published_or_deleted(monkeypatch, tmp_path):
    h = world(with_moves=False); root = tree(tmp_path); real_fsync = os.fsync
    marker = root / "unrelated"; marker.write_bytes(b"must survive")
    def replace_temp(fd):
        real_fsync(fd)
        if stat.S_ISREG(os.fstat(fd).st_mode):
            temporary = next((root / "gex").iterdir())
            temporary.unlink()
            temporary.symlink_to(marker)
    with monkeypatch.context() as m:
        m.setattr(arrival.os, "fsync", replace_temp)
        with pytest.raises(arrival.SourceArrivalRefused, match="source_arrival_failed"): run(h, root)
    remaining = list((root / "gex").iterdir())
    assert len(remaining) == 1 and remaining[0].is_symlink()
    assert not (root / "gex/SPY.json").exists()
    assert marker.read_bytes() == b"must survive"


def test_short_writes_are_completed_before_publishing(monkeypatch, tmp_path):
    h = world(with_moves=False); root = tree(tmp_path); real_write = os.write
    def short(fd, data): return real_write(fd, data[:17])
    with monkeypatch.context() as m:
        m.setattr(arrival.os, "write", short)
        run(h, root)
    assert (root / "gex/SPY.json").read_bytes() == h.gex_bytes


@pytest.mark.parametrize("replacement", ["different_inode", "symlink"])
def test_link_name_replacement_is_uncertain_and_preserves_final(monkeypatch, tmp_path, replacement):
    h = world(with_moves=False); root = tree(tmp_path); real_link = os.link
    marker = root / "unrelated"; marker.write_bytes(b"must survive")
    def replace_inside_link(src, dst, **kwargs):
        # The original pre-link lstat has already returned at this boundary.
        os.unlink(src, dir_fd=kwargs["src_dir_fd"])
        if replacement == "symlink":
            os.symlink(marker, src, dir_fd=kwargs["src_dir_fd"])
        else:
            fd = os.open(src, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600,
                         dir_fd=kwargs["src_dir_fd"])
            try:
                os.write(fd, b"x" * len(h.gex_bytes))
            finally:
                os.close(fd)
        return real_link(src, dst, **kwargs)
    with monkeypatch.context() as m:
        m.setattr(arrival.os, "link", replace_inside_link)
        with pytest.raises(arrival.SourceArrivalUncertain, match="source_arrival_uncertain"):
            run(h, root)
    target = root / "gex/SPY.json"
    if replacement == "symlink":
        assert target.is_symlink()
    else:
        assert target.read_bytes() == b"x" * len(h.gex_bytes)
    assert marker.read_bytes() == b"must survive"
    assert not h.s3.log and not h.saves


@pytest.mark.parametrize("failure", ["link_reply_lost", "directory_fsync"])
def test_ambiguous_or_post_link_failure_leaves_final_and_never_claims_rollback(monkeypatch, tmp_path, failure):
    h = world(with_moves=False); root = tree(tmp_path)
    with monkeypatch.context() as m:
        if failure == "link_reply_lost":
            real_link = os.link
            def lost(*a, **kw): real_link(*a, **kw); raise OSError("controlled lost link return")
            m.setattr(arrival.os, "link", lost)
        else:
            real_fsync = os.fsync
            def fail_dir(fd):
                if stat.S_ISDIR(os.fstat(fd).st_mode): raise OSError("controlled directory fsync failure")
                return real_fsync(fd)
            m.setattr(arrival.os, "fsync", fail_dir)
        with pytest.raises(arrival.SourceArrivalUncertain, match="source_arrival_uncertain"): run(h, root)
    assert (root / "gex/SPY.json").read_bytes() == h.gex_bytes
    assert not h.s3.log and not h.saves
