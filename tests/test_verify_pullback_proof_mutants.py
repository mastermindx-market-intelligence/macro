"""Killers for pullback-proof mutants the existing suites left alive.

Each test feeds a small synthetic page, or a synthetic measurement, to a
public verifier function. Prices and timestamps are round fixtures. No market
feed is read.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.verify_risk_radar_pullback_matrix as matrix
from scripts.verify_risk_radar_pullback_served import (
    EM_DASH,
    FORECAST_LINES,
    forecast_lines_ok,
    verify_html,
)

EM = EM_DASH
NOW = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)
SOURCE = {"file": "synthetic.html"}


def _build(
    *,
    phase="underway",
    role="dialog",
    modal="true",
    labelledby="pbx-ttl",
    emit_label=True,
    asof="2026-09-30",
    valid_until="2026-10-01T09:00:00+00:00",
    times=None,
    current="10.0%",
    worst="-12.0%",
    rebound="+2.0%",
    note="Reference high 2026-09-01",
    extra="",
    strongs=None,
    second_forecast=False,
    copies=1,
):
    if times is None:
        times = (asof, valid_until)
    if strongs is None:
        strongs = (EM, EM)
    labels = (
        ("Further decline from the latest close", "自最新收盘价起的进一步跌幅"),
        ("Total pullback depth", "回撤总深度"),
    )
    rows = []
    for (en, zh), value in zip(labels, strongs):
        rows.append(
            '<div class="rrp-forecast-row">'
            f'<span class="l-en">{en}</span><span class="l-zh">{zh}</span>'
            f"<strong>{value}</strong></div>"
        )
    forecast = (
        '<div class="rrp-forecast" data-forecast-status="unavailable">'
        '<h3><span class="l-en">Estimate unavailable</span>'
        '<span class="l-zh">估计暂不可用</span></h3>'
        + "".join(rows)
        + "</div>"
    )
    if second_forecast:
        forecast += forecast
    stamp = "".join(f'<time datetime="{item}">t</time>' for item in times)
    modal_attr = "" if modal is None else f' aria-modal="{modal}"'
    label_attr = "" if labelledby is None else f' aria-labelledby="{labelledby}"'
    section = (
        f'<section class="rrp pbx" data-pb-phase="{phase}" data-pb-asof="{asof}" '
        f'data-pb-valid-until="{valid_until}">'
        f'<div class="rrp-stamp">{stamp}</div>'
        f'<span data-metric="current">{current}</span>'
        f'<span data-metric="worst">{worst}</span>'
        f'<span data-metric="rebound">{rebound}</span>'
        f'<p class="rrp-note">{note}</p>'
        f"{extra}{forecast}</section>"
    )
    dialog = (
        f'<div id="cnx-dlg-risk" role="{role}"{modal_attr}{label_attr}>{section}</div>'
    )
    label = f'<h2 id="{labelledby}">Risk</h2>' if emit_label and labelledby else ""
    return "<!DOCTYPE html><html><body>" + label + (dialog * copies) + "</body></html>"


def _run(html, **kwargs):
    receipt = verify_html(
        html.encode("utf-8"),
        SOURCE,
        kwargs.get("market", "cn"),
        kwargs.get("require_active", False),
        kwargs.get("now", NOW),
    )
    bad = [item["id"] for item in receipt["checks"] if not item["pass"]]
    detail = {item["id"]: item["detail"] for item in receipt["checks"]}
    return bad, detail, receipt["pass"]


def _cell(**overrides):
    cell = {
        "page": "us",
        "file": "macro.html",
        "lang": "en",
        "theme": "dark",
        "viewport": "desktop",
        "width": 1440,
        "height": 900,
        "motion": "no-preference",
        "javascript": True,
    }
    cell.update(overrides)
    return cell


def _measured(**overrides):
    measured = {
        "dialog_visible": True,
        "pbx_present": True,
        "phase": "underway",
        "forecast_heading_text": "Estimate unavailable",
        "forecast_row_text": f"Further decline from the latest close {EM}",
        "forecast_row_count": 2,
        "forecast_values": [EM, EM],
        "forecast_block_text": "Estimate unavailable\n" + EM,
        "data_lang": "en",
        "data_theme": "dark",
        "page_scroll_width": 1440,
        "page_inner_width": 1440,
        "dialog_scroll_width": 400,
        "dialog_client_width": 400,
        "tab_escapes": 0,
        "escape_closes": True,
        "focus_returns_to_opener": True,
        "time_datetime": "2026-01-02T00:00:00Z",
    }
    measured.update(overrides)
    return measured


def test_kill_A01_monitoring_phase_passes_c2():
    """A phase removed from PHASES must not make a monitoring page fail C2."""
    bad, _detail, ok = _run(_build(phase="monitoring"))
    assert ok is True
    assert bad == []


def test_kill_A04_planted_allow_sentence_fails_c5():
    bad, detail, _ok = _run(_build(extra="<p>This outcome is likely.</p>"))
    assert "C5" in bad
    assert "This outcome is likely." in detail["C5"]


def test_kill_A05_likely_alone_fails_c5():
    bad, detail, _ok = _run(_build(extra="<p>This is likely.</p>"))
    assert "C5" in bad
    assert "likely" in detail["C5"]


def test_kill_A06_minute_60_offset_fails_c3():
    bad, detail, _ok = _run(_build(valid_until="2026-10-01T09:00:00+00:60"))
    assert "C3" in bad
    assert "offset" in detail["C3"]


def test_kill_A07_valid_until_equal_to_asof_fails_c3():
    bad, detail, _ok = _run(_build(valid_until="2026-09-30T00:00:00+00:00"))
    assert "C3" in bad
    assert "not after asof" in detail["C3"]


def test_kill_A08_three_stamp_times_fail_c3():
    bad, detail, _ok = _run(_build(times=(
        "2026-09-30",
        "2026-10-01T09:00:00+00:00",
        "2026-10-01T09:00:00+00:00",
    )))
    assert "C3" in bad
    assert "found 3" in detail["C3"]


def test_kill_A09_bad_current_text_fails_c4():
    bad, detail, _ok = _run(_build(current="nope"))
    assert "C4" in bad
    assert "nope" in detail["C4"]


def test_kill_A10_smaller_worst_fails_c4():
    bad, detail, _ok = _run(_build(worst="-4.0%"))
    assert "C4" in bad
    assert "worst magnitude" in detail["C4"]


def test_kill_A11_stabilizing_bad_current_fails_c4():
    bad, _detail, _ok = _run(_build(phase="stabilizing", current="nope"))
    assert "C4" in bad


def test_kill_A12_two_forecast_blocks_fail_c5():
    bad, detail, _ok = _run(_build(second_forecast=True))
    assert "C5" in bad
    assert "found 2" in detail["C5"]


def test_kill_A13_nondigit_nondash_value_fails_c5():
    bad, detail, _ok = _run(_build(strongs=("Total pullback depth", "Total pullback depth")))
    assert "C5" in bad
    assert "em dash" in detail["C5"]


def test_kill_A14_non_string_forecast_text_is_rejected():
    assert forecast_lines_ok(None, FORECAST_LINES["en"]) is False


def test_kill_A15_aria_modal_false_fails_c1():
    bad, detail, _ok = _run(_build(modal="false"))
    assert "C1" in bad
    assert "aria-modal" in detail["C1"]


def test_kill_A16_dangling_labelledby_fails_c1():
    bad, detail, _ok = _run(_build(labelledby="missing-id", emit_label=False))
    assert "C1" in bad
    assert "does not resolve" in detail["C1"]


def test_kill_A17_unknown_phase_fails_c2():
    bad, detail, _ok = _run(_build(phase="nope"))
    assert "C2" in bad
    assert "nope" in detail["C2"]


def test_kill_A18_monitoring_require_active_fails_c7():
    bad, detail, _ok = _run(_build(phase="monitoring"), require_active=True)
    assert bad == ["C7"]
    assert "monitoring" in detail["C7"]


def test_kill_A19_duplicate_dialog_is_counted():
    _bad, detail, _ok = _run(_build(copies=2))
    assert "expected 1" in detail["C1"]


def test_kill_A20_duplicate_dialog_fails_c1():
    bad, _detail, ok = _run(_build(copies=2))
    assert ok is False
    assert "C1" in bad


def test_kill_A23_twenty_minutes_of_life_stays_current():
    now = datetime(2026, 10, 1, 8, 40, tzinfo=timezone.utc)
    bad, _detail, ok = _run(_build(), require_active=True, now=now)
    assert ok is True
    assert "C7" not in bad


def test_kill_A24_alertdialog_role_fails_c1():
    bad, detail, _ok = _run(_build(role="alertdialog"))
    assert "C1" in bad
    assert "role" in detail["C1"]


def test_kill_B03_zero_forecast_rows_fail():
    result = matrix.evaluate_cell(_cell(), _measured(forecast_row_count=0, forecast_row_text=""))
    assert result["checks"]["forecast_rows_have_no_digit"] is False
    assert "forecast_rows_have_no_digit" in result["failures"]


def test_kill_B04_three_forecast_values_fail():
    result = matrix.evaluate_cell(_cell(), _measured(forecast_values=[EM, EM, EM]))
    assert result["checks"]["forecast_values_ok"] is False
    assert "forecast_values_ok" in result["failures"]


def test_kill_B07_one_failed_cell_fails_the_receipt():
    receipt = matrix.assemble_receipt(
        "http://example.test",
        "2026-01-01T00:00:00Z",
        "chromium 0",
        [{"pass": True}, {"pass": False}],
    )
    assert receipt["pass"] is False


def test_kill_B08_empty_cell_list_fails_the_receipt():
    receipt = matrix.assemble_receipt(
        "http://example.test",
        "2026-01-01T00:00:00Z",
        "chromium 0",
        [],
    )
    assert receipt["pass"] is False


def test_kill_B09_extra_pbx_class_still_counts():
    html = (
        '<section class="rrp pbx extra" data-pb-phase="underway">'
        '<time datetime="2026-01-02T00:00:00Z">x</time></section>'
    )
    present, receipt, phase = matrix._pbx_from_html(html)
    assert present is True
    assert receipt == "2026-01-02T00:00:00Z"
    assert phase == "underway"


def test_kill_B10_missing_dialog_id_is_closed():
    assert matrix._dialog_is_open("<html></html>", "dlg-risk") is False


def test_kill_B11_slash_in_filename_is_rejected():
    with pytest.raises(ValueError):
        matrix.parse_pages("us=sub/macro.html")


def test_kill_B12_heading_suffix_fails():
    result = matrix.evaluate_cell(
        _cell(),
        _measured(forecast_heading_text="Estimate unavailable now"),
    )
    assert result["checks"]["forecast_heading_ok"] is False
    assert "forecast_heading_ok" in result["failures"]


def test_kill_B13_missing_tab_escape_count_fails():
    result = matrix.evaluate_cell(_cell(), _measured(tab_escapes=None))
    assert "tab_escapes" in result["failures"]


def test_kill_B14_unknown_language_rejects_english_copy():
    result = matrix.evaluate_cell(
        _cell(lang="fr"),
        _measured(data_lang="fr", forecast_heading_text=""),
    )
    assert result["checks"]["forecast_block_text_ok"] is False
    assert "forecast_block_text_ok" in result["failures"]


def test_kill_B16_non_numeric_width_fails_overflow():
    result = matrix.evaluate_cell(_cell(), _measured(page_scroll_width="wide"))
    assert result["checks"]["no_page_overflow"] is False
    assert "no_page_overflow" in result["failures"]
