"""D03 T38: publication outcome and rerender-only recovery, not atomicity.

All snapshots, JSON, HTML and ledgers are temporary. The real caller, view model,
template and write_page execute; fault injection distinguishes pre-write failure
from an interrupted writer that may already have changed the page.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from jinja2 import TemplateSyntaxError

from engine.pick_lab import ledger, render, snapshot
from lib import config
from scripts import build_pick_lab as builder


ROOT = Path(__file__).resolve().parents[1]
AS_OF = "2026-11-02"
OLD_PAGE = b"<html>PRIOR PAGE 2026-11-01</html>"
PREFIX = "::warning title=pick_lab::HTML publication failed (non-fatal);"


@pytest.fixture
def isolated_site(tmp_path, monkeypatch):
    site = tmp_path / "site"
    (site / "labdata").mkdir(parents=True)
    (site / "us_stocks_lab.html").write_bytes(OLD_PAGE)
    # Read-only template access. No test writes through this symlink.
    (tmp_path / "templates").symlink_to(ROOT / "templates", target_is_directory=True)
    data = tmp_path / "data"
    book_data = data / "pick_lab"
    book_data.mkdir(parents=True)
    monkeypatch.setattr(config, "ROOT", tmp_path)
    monkeypatch.setattr(config, "data_dir", lambda: data)
    for key, name in (("FIRES_PATH", "fires.jsonl"), ("GRADES_PATH", "grades.jsonl"),
                      ("LH_FIRES_PATH", "lh_fires.jsonl"), ("LH_GRADES_PATH", "lh_grades.jsonl")):
        path = book_data / name
        path.write_bytes(b"")
        monkeypatch.setattr(ledger, key, path)
    # External price refresh/store are outside publication proof.
    monkeypatch.setattr(builder, "_build_etf_closes", lambda _panel: None)
    monkeypatch.setattr(builder, "_load_close_panel", lambda: None)
    return site


def _write_inputs(site):
    entry = {"schema": "pick_lab.v1", "as_of": AS_OF,
             "regime": {"calm": None, "stress": None, "liquidity": None},
             "scoreboard": [], "books": {}, "lanes": {},
             "method_note": "D03 temporary publication fixture"}
    other = {"as_of": AS_OF, "books": {}, "fires_by_book": {}}
    for name, payload in (("pick_lab.json", entry), ("pick_lab_longhold.json", other),
                          ("pick_lab_fires.json", other)):
        (site / "labdata" / name).write_text(json.dumps(payload))


def _snapshot(monkeypatch, site):
    row = {key: None for key in snapshot.SNAPSHOT_COLUMNS}
    row.update(ticker="AAA", asof=AS_OF, close=25.0, dollar_adv_20d=50e6,
               sector="Information Technology", d1_macd_xup_bars=1,
               d1_kd_xup_bars=3, d1_from_os=True, d1_k=30.0, d1_d=20.0, rsi14=55.0,
               composite_z=1.0, edge_alpha=0.1, axis_selection=0.1, axis_quality=0.1)
    frame = pd.DataFrame([row]).set_index("ticker")
    frame.attrs["asof"] = AS_OF
    monkeypatch.setattr(snapshot, "latest_snapshot", lambda **_kw: (frame, AS_OF))
    write = snapshot.write_snapshot
    monkeypatch.setattr(snapshot, "write_snapshot", lambda data, asof, **kw: write(
        data, asof, base_dir=str(site.parent / "data/pick_lab/snapshots"), **kw))


def _protected_bytes(site):
    paths = list((site / "labdata").glob("*.json"))
    paths += list((site.parent / "data/pick_lab").glob("*.jsonl"))
    paths += list((site.parent / "data/pick_lab/snapshots").rglob("*.parquet"))
    return {path: path.read_bytes() for path in paths}


def _inject_failure(monkeypatch, stage):
    def fail(*_a, **_kw):
        raise RuntimeError("synthetic view-model failure")

    def template_fail(*_a, **_kw):
        raise TemplateSyntaxError("synthetic template failure", 1)

    def partial_write(path, _html, *_a, **_kw):
        Path(path).write_text("INTERRUPTED PAGE WRITE")
        raise OSError("synthetic writer interruption")

    if stage == "view_model":
        monkeypatch.setattr(render, "build_vm", fail)
    elif stage == "template":
        monkeypatch.setattr(render.Environment, "get_template", template_fail)
    else:
        monkeypatch.setattr(render, "write_page", partial_write)


def _assert_warning(capsys, *, nightly):
    out = capsys.readouterr().out
    warnings = [line for line in out.splitlines() if line.startswith(PREFIX)]
    assert len(warnings) == 1, out
    assert "site/us_stocks_lab.html" in warnings[0]
    if nightly:
        assert "JSON artifacts were written" in warnings[0]
        assert "different vintages" in warnings[0]
    else:
        assert "not confirmed refreshed" in warnings[0]
        assert "JSON artifacts were written" not in warnings[0]


def _assert_recovery(site, before, capsys):
    assert render.build_and_render(site) is True
    html = (site / "us_stocks_lab.html").read_text()
    assert AS_OF in html
    assert "PRIOR PAGE" not in html and "INTERRUPTED PAGE WRITE" not in html
    assert "data-dbase" in html
    assert _protected_bytes(site) == before
    assert PREFIX not in capsys.readouterr().out


@pytest.mark.parametrize("stage", ["view_model", "template", "writer"])
def test_committed_rerender_failure_and_recovery(isolated_site, monkeypatch, capsys, stage):
    site = isolated_site
    _write_inputs(site)
    before = _protected_bytes(site)
    with monkeypatch.context() as fault:
        _inject_failure(fault, stage)
        assert render.build_and_render(site) is False
    _assert_warning(capsys, nightly=False)
    assert _protected_bytes(site) == before
    if stage == "writer":
        assert (site / "us_stocks_lab.html").read_text() == "INTERRUPTED PAGE WRITE"
    else:
        assert (site / "us_stocks_lab.html").read_bytes() == OLD_PAGE
    _assert_recovery(site, before, capsys)


@pytest.mark.parametrize("stage", ["view_model", "template", "writer"])
def test_nightly_json_then_failed_html_has_honest_outcome(isolated_site, monkeypatch, capsys, stage):
    site = isolated_site
    _snapshot(monkeypatch, site)
    with monkeypatch.context() as fault:
        _inject_failure(fault, stage)
        assert builder._build() is False
    _assert_warning(capsys, nightly=True)
    for name in ("pick_lab.json", "pick_lab_longhold.json", "pick_lab_fires.json"):
        assert json.loads((site / "labdata" / name).read_text())["as_of"] == AS_OF
    before = _protected_bytes(site)
    if stage == "writer":
        assert (site / "us_stocks_lab.html").read_text() == "INTERRUPTED PAGE WRITE"
    else:
        assert (site / "us_stocks_lab.html").read_bytes() == OLD_PAGE
    _assert_recovery(site, before, capsys)


def test_successful_nightly_reports_html_completion(isolated_site, monkeypatch, capsys):
    _snapshot(monkeypatch, isolated_site)
    assert builder._build() is True
    assert AS_OF in (isolated_site / "us_stocks_lab.html").read_text()
    assert PREFIX not in capsys.readouterr().out


def test_missing_committed_inputs_can_publish_existing_empty_state(isolated_site, capsys):
    assert render.build_and_render(isolated_site) is True
    assert "First accrual tonight" in (isolated_site / "us_stocks_lab.html").read_text()
    assert PREFIX not in capsys.readouterr().out


def test_no_snapshot_is_unpublished_without_breaking_cli(isolated_site, monkeypatch, capsys):
    monkeypatch.setattr(snapshot, "latest_snapshot", lambda **_kw: (None, None))
    assert builder._build() is False
    assert builder.main() == 0
    assert (isolated_site / "us_stocks_lab.html").read_bytes() == OLD_PAGE
    assert PREFIX not in capsys.readouterr().out


def test_unconfirmed_render_does_not_change_cli_zero_contract(isolated_site, monkeypatch):
    monkeypatch.setattr(builder, "_build", lambda: False)
    assert builder.main() == 0


@pytest.mark.parametrize("payload", ["not-an-object", {"scoreboard": [None]}])
def test_invalid_view_model_inputs_are_inside_fail_soft_boundary(isolated_site, capsys, payload):
    (isolated_site / "labdata/pick_lab.json").write_text(json.dumps(payload))
    before = _protected_bytes(isolated_site)
    assert render.build_and_render(isolated_site) is False
    _assert_warning(capsys, nightly=False)
    assert _protected_bytes(isolated_site) == before
    assert (isolated_site / "us_stocks_lab.html").read_bytes() == OLD_PAGE
