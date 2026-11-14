"""Source-truth, calculation, and existing Events-dialog integration contracts.

No live source fetch, no simulated street-surprise history and no trading claims.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import json

import pandas as pd
import pytest

from engine import release_visual_history as visual

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-11-13T15:00:00Z"


def _frame(*, duplicate: bool = False, gap: bool = False):
    first = date(2025, 1, 1)
    rows = []
    for i in range(19):
        year = first.year + (first.month - 1 + i) // 12
        month = (first.month - 1 + i) % 12 + 1
        period = f"{year:04d}-{month:02d}-01"
        if gap and i == 14:
            continue
        rows.append({"period": pd.Timestamp(period), "realtime_start": pd.Timestamp("2026-10-01"),
                     "realtime_end": date(9999,12,31), "value": 100.0 + i})
    # The expired historical revision is not selected for the chart.
    rows.append({"period": pd.Timestamp("2026-01-01"), "realtime_start": pd.Timestamp("2026-09-01"),
                 "realtime_end": date(2026,9,30), "value": 999.0})
    # The future revision cannot leak backwards to the collector's source clock.
    rows.append({"period": pd.Timestamp("2026-01-01"), "realtime_start": pd.Timestamp("2026-11-01"),
                 "realtime_end": date(9999,12,31), "value": 888.0})
    if duplicate:
        rows.append(dict(rows[12], realtime_start=pd.Timestamp("2026-09-30"), value=150.0))
    return pd.DataFrame(rows)


def _manifest(root, *, collected="2026-11-13T14:00:00Z", content=b"fake-parquet"):
    path=root/"data/fred_vintage/release_targets/PPIFIS_all_vintages.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    manifest={"schema":"release_target_vintage_collection.v1", "source_output_type":2,
              "status":"ok", "completed_at":collected,
              "series":{"PPIFIS":{"path":"data/fred_vintage/release_targets/PPIFIS_all_vintages.parquet",
                                "status":"written", "artifact_bytes":len(content),
                                "artifact_sha256":sha256(content).hexdigest()}}}
    (path.parent/"manifest.json").write_text(json.dumps(manifest))
    return path


def test_monthly_and_annual_rates_are_distinct_and_not_bps():
    levels={f"2025-{i:02d}":100.0 for i in range(1,13)}
    levels.update({"2026-01":110.0,"2026-02":110.5,"2026-03":111.0})
    yoy=visual._change(levels,12)
    mom=visual._change(levels,1)
    assert yoy == [{"period":"2026-01","value":10.0},
                   {"period":"2026-02","value":10.5},
                   {"period":"2026-03","value":11.0}]
    assert mom[-1]["value"] == round(100*(111.0/110.5-1),3)
    # A prior-month acceleration is 0.5 percentage point, not a 0.5% release surprise.
    assert round(yoy[-1]["value"]-yoy[-2]["value"],2) == 0.5


def test_source_asof_vintage_never_reads_future_or_expired_revisions():
    curve=visual._frame_points(_frame(),date(2026,10,16))
    assert curve["yoy"][0]["period"] == "2026-01"
    assert curve["yoy"][0]["value"] == 12.0
    assert curve["yoy"][-1]["period"] == "2026-07"
    assert curve["yoy"][-1]["value"] == round(100*(118/106-1),3)
    assert curve["mom"][-1]["period"] == "2026-07"
    assert all(x["value"] < 100 for x in curve["yoy"])


def test_overlapping_active_vintages_refused():
    with pytest.raises(ValueError,match="overlapping_active_vintages"):
        visual._frame_points(_frame(duplicate=True), date(2026,10,16))


def test_missing_months_not_interpolated():
    curve=visual._frame_points(_frame(gap=True),date(2026,10,16))
    yoy={p["period"] for p in curve["yoy"]}
    assert "2026-03" not in yoy
    assert "2026-04" in yoy


def test_missing_manifest_is_explicit_unavailable(tmp_path):
    result=visual.build_release_visual_history(tmp_path,asof=NOW)
    assert result["status"]=="unavailable"
    assert result["series"]==[]
    assert result["reason_codes"]
    assert result["display_only"] is True and not any(result["authority"].values())


def test_real_manifest_fence_partial_coverage_and_staleness(tmp_path,monkeypatch):
    _manifest(tmp_path,collected="2026-10-16T18:00:00Z")
    monkeypatch.setattr(visual,"load_full_vintage_parquets",lambda *a, **k:_frame())
    result=visual.build_release_visual_history(tmp_path,asof=NOW)
    assert result["status"]=="partial"
    assert result["source_status"]=="stale"
    assert "source_history_collection_stale" in result["reason_codes"]
    ppi=next(s for s in result["series"] if s["release"]=="ppi_finaldemand")
    assert ppi["status"]=="available" and len(ppi["yoy"])==7
    assert ppi["first_prints"]==[]  # no fabricated official receipts
    assert all(x["status"]=="unavailable" for x in result["series"][1:])


def test_wrong_digest_refuses_even_if_parquet_can_load(tmp_path,monkeypatch):
    path=_manifest(tmp_path)
    path.write_bytes(b"new-bytes-without-updating-manifest")
    called=[]
    monkeypatch.setattr(visual,"load_full_vintage_parquets",lambda *a, **k:called.append(1))
    result=visual.build_release_visual_history(tmp_path,asof=NOW)
    assert result["status"]=="unavailable"
    assert "ppi_finaldemand:vintage_manifest_integrity_mismatch" in result["reason_codes"]
    assert not called


def test_future_manifest_refused(tmp_path):
    _manifest(tmp_path,collected="2026-11-14T15:00:00Z")
    result=visual.build_release_visual_history(tmp_path,asof=NOW)
    assert result["status"]=="unavailable"
    assert "future_collection_clock" in result["reason_codes"]


def test_component_uses_original_radar_fetch_and_visible_dialog():
    template=(ROOT/"templates/dashboard.html.j2").read_text()
    script=(ROOT/"templates/release_visual_history.js").read_text()
    partial=(ROOT/"templates/_release_visual_history.html.j2").read_text()
    producer=(ROOT/"scripts/build_release_forecast.py").read_text()
    assert template.count('include "_release_visual_history.html.j2"')==1
    assert template.count('include "_release_surprise_confirmation.html.j2"')<=1
    assert template.index('id="rr-inline"') < template.index('include "_release_visual_history.html.j2"')
    assert 'window.MMXReleaseVisualHistory.render(' in template
    assert 'd && d.release_visual_history' in template
    assert "fetch('macrodata/release_forecast.json'" in template
    assert '"release_visual_history": release_visual_history' in producer
    assert '"release_forecast.v2"' in producer
    for forbidden in ("fetch(", "setInterval(", "localStorage", "sessionStorage", ".innerHTML", "eval("):
        assert forbidden not in script
    assert 'display_raw_allowed===true' in script
    assert "No verified pre-release economist poll" in script
    assert '<svg data-rrh-chart' in partial
    assert '<details class="mx-disc">' in partial
    assert 'class="l-en"' in partial and 'class="l-zh"' in partial


def test_native_jinja_partial_compiles():
    from jinja2 import Environment, FileSystemLoader
    env=Environment(loader=FileSystemLoader(str(ROOT/"templates")))
    markup=env.get_template("_release_visual_history.html.j2").render()
    assert "MMXReleaseVisualHistory" in markup
    assert 'data-rrh-chart' in markup
    assert 'role="status"' in markup
