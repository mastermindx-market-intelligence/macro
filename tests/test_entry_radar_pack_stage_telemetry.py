"""Stage telemetry for scripts/entry_radar_live_pack.py (IDR R1)."""
from __future__ import annotations

import inspect
import re
from datetime import date

import pytest

from scripts import entry_radar_live_pack as pack_mod


def test_stage_prints_begin_and_done_lines_that_start_the_line(capsys):
    with pack_mod._stage("x"):
        pass
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln.startswith("entry-radar-pack stage=x")]
    assert len(lines) == 2
    assert lines[0] == lines[0].lstrip() and re.match(
        r"^entry-radar-pack stage=x status=begin (?:peak_)?rss_mb=",
        lines[0],
    )
    done_re = re.compile(
        r"^entry-radar-pack stage=x status=done elapsed_s=\d+\.\d{3} (?:peak_)?rss_mb=(\d+\.\d|na)$"
    )
    assert done_re.match(lines[1])


def test_stage_reports_failed_and_reraises(capsys):
    with pytest.raises(ValueError, match="boom"):
        with pack_mod._stage("failme"):
            raise ValueError("boom")
    out = capsys.readouterr().out
    assert any(
        ln.startswith("entry-radar-pack stage=failme status=failed elapsed_s=")
        for ln in out.splitlines()
    )


def test_rss_mb_never_raises(monkeypatch, capsys):
    import builtins
    import resource

    def bad_open(*args, **kwargs):
        raise OSError("no proc")

    monkeypatch.setattr(builtins, "open", bad_open)
    monkeypatch.setattr(resource, "getrusage", lambda *_: (_ for _ in ()).throw(RuntimeError("nope")))
    assert pack_mod._rss_mb() is None
    with pack_mod._stage("na"):
        pass
    out = capsys.readouterr().out
    assert re.search(r"(?:peak_)?rss_mb=na", out)


def test_main_wraps_every_stage_in_order():
    src = inspect.getsource(pack_mod.main)
    names = [
        'collect',
        'probe_set',
        'slice_lanes',
        'build_pack',
        'proof',
        'ledger',
        'save',
        'spool',
    ]
    positions = []
    for name in names:
        needle = f'_stage("{name}")'
        count = src.count(needle)
        assert count == 1, f"{needle} count={count}"
        positions.append(src.index(needle))
    assert positions == sorted(positions)
    assert src.count("stage=total") >= 3


def test_slice_lanes_prints_progress_every_250_names(capsys, tmp_path):
    tickers = [f"T{i:04d}" for i in range(501)]
    lanes, runs = pack_mod.slice_lanes(
        tickers, as_of=date(2026, 10, 2), slice_dir=tmp_path
    )
    out = capsys.readouterr().out
    assert "progress=250/501" in out
    assert "progress=500/501" in out
    assert "progress=501/501" in out
    assert runs == []
    assert isinstance(lanes, dict)


def test_slice_lanes_unconfigured_prints_no_progress(capsys):
    pack_mod.slice_lanes(["AAA"], as_of=date(2026, 10, 2), slice_dir=None)
    out = capsys.readouterr().out
    assert "progress=" not in out


def test_rss_label_is_one_of_the_two_names():
    assert pack_mod._rss_label() in ("rss_mb", "peak_rss_mb")


def test_slice_lanes_progress_prints_exactly_at_250_500_and_the_end(capsys, tmp_path):
    tickers = [f"T{i:04d}" for i in range(501)]
    pack_mod.slice_lanes(tickers, as_of=date(2026, 10, 2), slice_dir=tmp_path)
    out = capsys.readouterr().out
    progress_lines = [
        ln for ln in out.splitlines() if "stage=slice_lanes progress=" in ln
    ]
    assert len(progress_lines) == 3
    assert "progress=250/501" in out
    assert "progress=500/501" in out
    assert "progress=501/501" in out
