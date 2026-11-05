"""Pinned native rendering refuses source drift without rewriting publication inputs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import build_site


def _pair(tmp_path: Path):
    site = tmp_path / "site"
    data = site / "factordata"
    data.mkdir(parents=True)
    emit = {"pair_id": "1" * 32, "at_utc": "2026-10-12T18:02:00+00:00",
            "writer": "build_stock_library"}
    board = {"as_of": "2026-10-12", "board_definition": "us_prophet_v3",
             "emit": dict(emit), "buy": [
                 {"ticker": "ALFA", "price": 42.0, "featured": True, "signal": {"ticks": 2}},
             ]}
    gate = {"as_of": "2026-10-12", "emit": dict(emit),
            "verdicts": {"ALFA": {"ticks": 2}}}
    paths = [data / "us_standouts.json", data / "signal_gate.json"]
    for path, document in zip(paths, (board, gate)):
        path.write_text(json.dumps(document))
    return site, paths


def _pins(paths):
    return [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]


def test_exact_native_pair_is_read_only_and_postcheck_detects_drift(tmp_path):
    site, paths = _pair(tmp_path)
    before = {path: path.read_bytes() for path in paths}
    frozen = build_site._capture_frozen_us_render_source(site, *_pins(paths))
    assert frozen == before
    assert {path: path.read_bytes() for path in paths} == before
    build_site._verify_frozen_us_render_source(frozen)
    paths[0].write_bytes(before[paths[0]] + b"\n")
    with pytest.raises(RuntimeError, match="REFUSED_FROZEN_US_SOURCE_DRIFT"):
        build_site._verify_frozen_us_render_source(frozen)


@pytest.mark.parametrize("missing", [0, 1])
def test_missing_artifact_refuses_even_with_matching_pin(tmp_path, missing):
    site, paths = _pair(tmp_path)
    pins = _pins(paths)
    paths[missing].unlink()
    with pytest.raises(ValueError, match="missing or indirect"):
        build_site._capture_frozen_us_render_source(site, *pins)


@pytest.mark.parametrize("wrong", [0, 1])
def test_changed_source_refuses_before_render(tmp_path, wrong):
    site, paths = _pair(tmp_path)
    pins = _pins(paths)
    pins[wrong] = "0" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        build_site._capture_frozen_us_render_source(site, *pins)


@pytest.mark.parametrize("field,value", [
    ("pair_id", "2" * 32), ("at_utc", "2026-10-12T19:02:00+00:00"),
    ("writer", "different_writer"), ("as_of", "2026-10-13"),
])
def test_pinned_but_mixed_generation_refuses(tmp_path, field, value):
    site, paths = _pair(tmp_path)
    gate = json.loads(paths[1].read_text())
    if field == "as_of":
        gate[field] = value
    else:
        gate["emit"][field] = value
    paths[1].write_text(json.dumps(gate))
    with pytest.raises(ValueError, match="REFUSED_FROZEN_US_SOURCE"):
        build_site._capture_frozen_us_render_source(site, *_pins(paths))


def test_same_pair_stamp_does_not_hide_gate_content_mismatch(tmp_path):
    site, paths = _pair(tmp_path)
    gate = json.loads(paths[1].read_text())
    gate["verdicts"]["ALFA"]["ticks"] = 3
    paths[1].write_text(json.dumps(gate))
    with pytest.raises(ValueError, match="content mismatch"):
        build_site._capture_frozen_us_render_source(site, *_pins(paths))


@pytest.mark.parametrize("bad", [[], "{broken"])
def test_invalid_json_or_object_refuses(tmp_path, bad):
    site, paths = _pair(tmp_path)
    paths[0].write_text(json.dumps(bad) if isinstance(bad, list) else bad)
    with pytest.raises(ValueError, match="invalid"):
        build_site._capture_frozen_us_render_source(site, *_pins(paths))


def test_unbound_roster_cannot_enter_frozen_render(tmp_path):
    site, paths = _pair(tmp_path)
    board = json.loads(paths[0].read_text())
    board["buy"] = "not-a-native-roster"
    paths[0].write_text(json.dumps(board))
    with pytest.raises(ValueError, match="native source binding unavailable"):
        build_site._capture_frozen_us_render_source(site, *_pins(paths))


def test_indirect_source_path_refuses(tmp_path):
    site, paths = _pair(tmp_path)
    pins = _pins(paths)
    target = paths[0].with_name("retained.json")
    paths[0].rename(target)
    paths[0].symlink_to(target)
    with pytest.raises(ValueError, match="missing or indirect"):
        build_site._capture_frozen_us_render_source(site, *pins)


def test_missing_pins_stop_main_before_any_site_write(monkeypatch, tmp_path):
    monkeypatch.setattr(build_site.config, "ROOT", tmp_path)
    monkeypatch.setattr(build_site.config, "load", lambda: {"storage": {"site_dir": "site"}})
    with pytest.raises(ValueError, match="both exact SHA256 pins are required"):
        build_site.main(refresh_stock_library=False)
    assert not (tmp_path / "site").exists()


def test_cli_keeps_normal_default_and_forwards_explicit_frozen_pins(monkeypatch):
    seen = []
    monkeypatch.setattr(build_site, "main", lambda **kwargs: seen.append(kwargs) or 0)
    assert build_site._cli([]) == 0
    assert seen[-1] == {"refresh_stock_library": True,
                        "frozen_us_board_sha256": None, "frozen_us_gate_sha256": None}
    assert build_site._cli(["--no-refresh-stock-library",
                            "--frozen-us-board-sha256", "a" * 64,
                            "--frozen-us-gate-sha256", "b" * 64]) == 0
    assert seen[-1] == {"refresh_stock_library": False,
                        "frozen_us_board_sha256": "a" * 64, "frozen_us_gate_sha256": "b" * 64}
