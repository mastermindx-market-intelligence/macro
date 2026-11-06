"""Normal International EOD publication -> same-owner chart renderer input."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json

import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader

from engine import i18n
from lib.intl_library_mount import render_international_pages
from scripts import build_intl
from tests.test_intl_eod_publication import EVALUATED, _setup


def test_production_workspace_captures_only_its_qualified_source_pair(tmp_path, monkeypatch):
    from lib import intl_eod_publication as source_owner

    frame, _ = _setup(tmp_path)
    calls = []
    build = source_owner.build_eod_inputs

    def counted(*args, **kwargs):
        calls.append((args, kwargs))
        return build(*args, **kwargs)

    monkeypatch.setattr(source_owner, "build_eod_inputs", counted)
    sink = {}
    workspace = build_intl._publication_workspace(
        frame, data_root=tmp_path, evaluated_at=EVALUATED, chart_source_sink=sink)
    assert workspace is not None
    assert len(calls) == 1
    assert workspace["eod_snapshot"]["as_of"] == "2026-10-07"
    assert set(sink) == {"sources"}
    closes, packet = sink["sources"]
    assert isinstance(closes, pd.DataFrame)
    assert packet["policy_id"] == "intl-observed-endpoints-completed-session-v1"
    assert closes.index[-1] == pd.Timestamp("2026-10-07")
    assert packet["source_evidence"][0]["source_reference"] == next(
        p["overview"]["context"]["source_reference"]
        for p in workspace["panels"]
        if p["overview"]["context"]["currency_basis"] == "usd_unhedged")
    assert not any("chart_sources" in p for p in workspace["panels"])
    assert "sources" not in workspace


def test_failed_or_missing_source_cannot_leak_a_previous_packet(tmp_path):
    frame, _ = _setup(tmp_path, late=False)
    sink = {}
    workspace = build_intl._publication_workspace(
        frame, data_root=tmp_path, evaluated_at=EVALUATED, chart_source_sink=sink)
    assert workspace is not None
    assert sink == {}
    assert "eod_snapshot" not in workspace
    # A nonempty / reused capture object must be rejected before any reads.
    with pytest.raises(ValueError, match="invalid_international_chart_sink"):
        build_intl._publication_workspace(
            frame, data_root=tmp_path, evaluated_at=EVALUATED,
            chart_source_sink={"sources": "previous"})
    with pytest.raises(ValueError, match="invalid_international_chart_sink"):
        build_intl._publication_workspace(
            frame, data_root=tmp_path, evaluated_at=EVALUATED,
            chart_source_sink=[])


def test_normal_jinja_page_consumes_the_private_chart_sidecar(tmp_path):
    import importlib.util

    frame, _ = _setup(tmp_path)
    sink = {}
    workspace = build_intl._publication_workspace(
        frame, data_root=tmp_path, evaluated_at=EVALUATED, chart_source_sink=sink)
    original = deepcopy(workspace)
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("intl_page_vm_fixture", root / "tests/test_intl_build.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    vm = module._vm()
    vm["intl_workspace"] = workspace
    env = Environment(loader=FileSystemLoader(str(root / "templates")), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    catalogue = json.loads((root / "config/intl_library_catalogue.json").read_text())
    html, stocks = render_international_pages(
        env.get_template("intl.html.j2"), vm, catalogue=catalogue,
        chart_sources=sink["sources"])
    assert html.count('data-im-chart-model="intl-chart-geometry.v1"') == 10
    assert html.count("data-im-compare-panel") == 10
    assert html.count("data-im-eod-disclosure") == 1
    assert 'data-im-chart-selection-unavailable' in html
    assert 'data-im-chart-benchmark-unavailable' in html
    assert 'intl-legacy-research' in html
    assert 'data-im-chart-table-market="JP"' in html
    assert 'saved-parquet:sha256:' not in html
    assert '"adjustment_bases"' not in html
    assert workspace == original
    assert stocks
