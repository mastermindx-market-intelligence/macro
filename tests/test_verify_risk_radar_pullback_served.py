"""Served-page contract for the Risk Radar pullback popup.

Renders the real US and China dialog templates with the synthetic observation
the integration tests already use, then runs the verifier's main() in process.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import types
from pathlib import Path

import pytest


def _allow_dashboard_render_without_plotly() -> None:
    """scripts/build_site.py imports plotly at module load. The dashboard
    template render does not call it; this venv does not install it."""
    try:
        import plotly.graph_objects  # noqa: F401
        import plotly.subplots  # noqa: F401
    except ModuleNotFoundError:
        plotly = types.ModuleType("plotly")
        graph_objects = types.ModuleType("plotly.graph_objects")
        subplots = types.ModuleType("plotly.subplots")

        def _unused(*_args, **_kwargs):
            raise RuntimeError("plotly is not used by the pullback dialog render")

        graph_objects.Figure = _unused
        subplots.make_subplots = _unused
        plotly.graph_objects = graph_objects
        plotly.subplots = subplots
        sys.modules["plotly"] = plotly
        sys.modules["plotly.graph_objects"] = graph_objects
        sys.modules["plotly.subplots"] = subplots


_allow_dashboard_render_without_plotly()

from scripts.verify_risk_radar_pullback_served import main
from tests.test_cn_pullback_dialog_integration import _render as render_cn
from tests.test_macro_risk_dialog import _render as render_us
from tests.test_macro_risk_dialog import _vm
from tests.test_risk_radar_pullback_depth_template import native_view
from tests.test_risk_radar_pullback_depth_template import render as render_pullback

EM = "\u2014"
MINUS = "\u2212"
CHECK_IDS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
# The synthetic observation's valid_until is 2026-10-01T09:00:00+00:00.
STILL_CURRENT = "2026-10-01T08:00:00+00:00"


def _active_us() -> str:
    vm = _vm()
    vm["us_pullback_view"] = native_view("us")
    return render_us(vm=vm, mode="macro")


def _active_cn() -> str:
    return render_cn(native_view("cn"))


def _unavailable_cn() -> str:
    """The page gate omits an unqualified view, so splice the real fragment in."""
    shell = render_cn(None)
    section = render_pullback(None, "cn")
    marker = '<div class="cnx-dlg-body rrd">'
    assert marker in shell
    assert 'data-pb-phase="unavailable"' in section
    return shell.replace(marker, marker + section, 1)


def _run(tmp_path: Path, html: str, market: str, *extra: str):
    page = tmp_path / "page.html"
    page.write_bytes(html.encode("utf-8"))
    out = tmp_path / "receipt.json"
    rc = main(["--html", str(page), "--market", market, "--out", str(out), *extra])
    receipt = json.loads(out.read_text(encoding="utf-8"))
    return rc, receipt, page


def _failed(receipt: dict) -> list[str]:
    return [item["id"] for item in receipt["checks"] if not item["pass"]]


def _assert_shape(receipt: dict, page: Path, market: str) -> None:
    assert receipt["schema"] == "risk_radar_pullback_served.v1"
    assert receipt["source"] == {"file": str(page)}
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", receipt["fetched_at_utc"])
    raw = page.read_bytes()
    assert receipt["bytes"] == len(raw)
    assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["market"] == market
    assert [item["id"] for item in receipt["checks"]] == CHECK_IDS
    assert set(receipt["metrics"]) == {"current", "worst", "rebound", "age"}


def test_active_us_passes_with_and_without_require_active(tmp_path):
    html = _active_us()
    rc, receipt, page = _run(tmp_path, html, "us")
    assert rc == 0, [(c["id"], c["detail"]) for c in receipt["checks"] if not c["pass"]]
    assert receipt["pass"] is True
    _assert_shape(receipt, page, "us")
    assert receipt["phase"] == "underway"
    assert receipt["asof"] == "2026-09-30"
    assert receipt["valid_until"] == "2026-10-01T09:00:00+00:00"
    assert receipt["source_digest"] == "a" * 64
    assert receipt["metrics"]["current"] == f"{MINUS}6.8%"
    assert receipt["metrics"]["worst"] == f"{MINUS}7.4%"
    assert receipt["metrics"]["rebound"] == "+0.6%"
    assert "12" in receipt["metrics"]["age"]
    c6 = next(c["detail"] for c in receipt["checks"] if c["id"] == "C6")
    assert "whole_page_count=0" in c6
    rc_active, receipt_active, _page = _run(
        tmp_path, html, "us", "--require-active", "--now", STILL_CURRENT,
    )
    assert rc_active == 0 and receipt_active["pass"] is True


def test_active_cn_passes_with_and_without_require_active(tmp_path):
    html = _active_cn()
    rc, receipt, page = _run(tmp_path, html, "cn", "--require-active", "--now", STILL_CURRENT)
    assert rc == 0, [(c["id"], c["detail"]) for c in receipt["checks"] if not c["pass"]]
    assert receipt["pass"] is True
    _assert_shape(receipt, page, "cn")
    assert receipt["phase"] == "underway"
    assert receipt["metrics"]["current"] == f"{MINUS}6.8%"
    rc_open, receipt_open, _page = _run(tmp_path, html, "cn")
    assert rc_open == 0 and receipt_open["pass"] is True
    assert _failed(receipt_open) == []


def test_unavailable_passes_without_require_active(tmp_path):
    rc, receipt, _page = _run(tmp_path, _unavailable_cn(), "cn")
    assert rc == 0, [(c["id"], c["detail"]) for c in receipt["checks"] if not c["pass"]]
    assert receipt["pass"] is True
    assert receipt["phase"] == "unavailable"
    assert _failed(receipt) == []


def test_expired_page_fails_c7_when_require_active(tmp_path):
    """G7: a still-underway page whose valid_until is already past fails closed."""
    html = _active_cn()
    rc, receipt, _page = _run(
        tmp_path, html, "cn", "--require-active", "--now", "2026-10-01T09:00:00+00:00",
    )
    assert rc == 1
    assert _failed(receipt) == ["C7"]
    detail = next(item["detail"] for item in receipt["checks"] if item["id"] == "C7")
    assert detail == "expired: valid_until <= now"
    later = _run(tmp_path, html, "cn", "--now", "2026-12-01T00:00:00Z")
    assert later[0] == 0 and later[1]["pass"] is True


def test_valid_until_beyond_the_page_cap_fails_c7_when_require_active(tmp_path):
    """The page script expires a stamp more than 400 days ahead; C7 agrees at the boundary."""
    html = _active_cn()
    # valid_until 2026-10-01T09:00:00+00:00 is exactly 400 days after this clock.
    rc, receipt, _page = _run(
        tmp_path, html, "cn", "--require-active", "--now", "2025-08-27T09:00:00+00:00",
    )
    assert rc == 0, [(c["id"], c["detail"]) for c in receipt["checks"] if not c["pass"]]
    rc, receipt, _page = _run(
        tmp_path, html, "cn", "--require-active", "--now", "2025-08-27T08:59:59+00:00",
    )
    assert rc == 1
    assert _failed(receipt) == ["C7"]
    detail = next(item["detail"] for item in receipt["checks"] if item["id"] == "C7")
    assert detail == "valid_until is more than 400 days ahead; the page script expires it"


def test_c7_cap_equals_the_page_script_cap():
    from datetime import timedelta

    from scripts.verify_risk_radar_pullback_served import MAX_AHEAD

    js = (Path(__file__).resolve().parents[1]
          / "templates/_risk_radar_pullback_depth.js.j2").read_text(encoding="utf-8")
    match = re.search(r"var MAX_AHEAD_MS = (\d+) \* 24 \* 60 \* 60 \* 1000;", js)
    assert match, "page script cap moved"
    assert MAX_AHEAD == timedelta(days=int(match.group(1)))


def test_missing_valid_until_fails_c7_when_require_active(tmp_path):
    html = _active_cn()
    old = 'data-pb-valid-until="2026-10-01T09:00:00+00:00"'
    assert html.count(old) == 1
    html = html.replace(old, 'data-pb-valid-until="not-a-time"', 1)
    rc, receipt, _page = _run(tmp_path, html, "cn", "--require-active", "--now", STILL_CURRENT)
    assert rc == 1
    assert "C7" in _failed(receipt)
    detail = next(item["detail"] for item in receipt["checks"] if item["id"] == "C7")
    assert detail == "valid_until missing or unparseable"


def test_bad_now_is_an_input_error(tmp_path):
    page = tmp_path / "page.html"
    page.write_text("<html></html>", encoding="utf-8")
    rc = main(["--html", str(page), "--market", "cn", "--now", "yesterday"])
    assert rc == 2
    assert not (tmp_path / "receipt.json").exists()


def test_unavailable_fails_when_require_active(tmp_path):
    rc, receipt, _page = _run(tmp_path, _unavailable_cn(), "cn", "--require-active")
    assert rc == 1
    assert receipt["pass"] is False
    assert _failed(receipt) == ["C7"]


def test_worded_forecast_paragraph_fails_only_c5(tmp_path):
    """G4: a forecast sentence with no digit and no percent still fails C5."""
    html = _active_cn()
    needle = 'data-forecast-status="unavailable">'
    assert needle in html
    html = html.replace(needle, needle + "<p>A deep further drop is likely.</p>", 1)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C5"]
    detail = next(item["detail"] for item in receipt["checks"] if item["id"] == "C5")
    assert "allow-list" in detail


def test_forecast_allow_list_equals_rendered_text_nodes():
    """A copy change in the partial without a verifier change fails here."""
    from scripts.verify_risk_radar_pullback_served import FORECAST_TEXT_ALLOW, forecast_text_set

    current = forecast_text_set(render_pullback(native_view("us"), "us"))
    current_cn = forecast_text_set(render_pullback(native_view("cn"), "cn"))
    unavailable = forecast_text_set(render_pullback(None, "cn"))
    assert current == FORECAST_TEXT_ALLOW
    assert current_cn == FORECAST_TEXT_ALLOW
    assert unavailable == FORECAST_TEXT_ALLOW
    assert EM in FORECAST_TEXT_ALLOW
    assert "Estimate unavailable" in FORECAST_TEXT_ALLOW
    assert "估计暂不可用" in FORECAST_TEXT_ALLOW


def test_digit_in_forecast_row_fails_only_c5(tmp_path):
    html = _active_cn()
    needle = f"<strong>{EM}</strong>"
    assert needle in html
    html = html.replace(needle, f"<strong>{EM}1</strong>", 1)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C5"]


def test_vendor_token_outside_the_dialog_fails_c6(tmp_path):
    """G5: a banned token anywhere on the page fails, even with dialog_hits=0."""
    html = _active_cn() + "<!-- Massive -->"
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C6"]
    detail = next(item["detail"] for item in receipt["checks"] if item["id"] == "C6")
    assert detail == "dialog_hits=0; whole_page_count=1"


def test_css_polygon_function_is_not_a_vendor_token(tmp_path):
    """G6: clip-path:polygon(...) is a CSS function, not a banned token."""
    html = _active_cn() + '<style>.mark{clip-path:polygon(50% 0,100% 100%,0 100%)}</style>'
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 0, [(c["id"], c["detail"]) for c in receipt["checks"] if not c["pass"]]
    detail = next(item["detail"] for item in receipt["checks"] if item["id"] == "C6")
    assert "whole_page_count=0" in detail


def test_polygon_word_in_body_fails_c6(tmp_path):
    """G6: the word Polygon in body text still fails C6, in any case."""
    html = _active_cn() + "<p>Polygon</p>"
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C6"]
    detail = next(item["detail"] for item in receipt["checks"] if item["id"] == "C6")
    assert "dialog_hits=0" in detail
    assert "whole_page_count=1" in detail
    html_lower = _active_cn() + "<p>polygon</p>"
    rc_lower, receipt_lower, _page = _run(tmp_path, html_lower, "cn")
    assert rc_lower == 1
    assert _failed(receipt_lower) == ["C6"]


def test_vendor_name_in_dialog_fails_only_c6(tmp_path):
    html = _active_cn()
    marker = 'id="cnx-dlg-risk"'
    end = html.index(">", html.index(marker))
    html = html[: end + 1] + "<p>Yahoo</p>" + html[end + 1:]
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C6"]
    detail = next(item["detail"] for item in receipt["checks"] if item["id"] == "C6")
    assert "whole_page_count=" in detail
    assert "dialog_hits=0" not in detail


def test_valid_until_without_offset_fails_only_c3(tmp_path):
    html = _active_cn()
    old = 'data-pb-valid-until="2026-10-01T09:00:00+00:00"'
    new = 'data-pb-valid-until="2026-10-01T09:00:00"'
    assert old in html
    html = html.replace(old, new, 1)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C3"]


def test_current_until_time_that_disagrees_fails_only_c3(tmp_path):
    html = _active_cn()
    old = '<time datetime="2026-10-01T09:00:00+00:00">'
    assert html.count(old) == 1
    html = html.replace(old, '<time datetime="2026-10-09T09:00:00+00:00">', 1)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C3"]


def test_aria_modal_removed_fails_only_c1(tmp_path):
    html = _active_cn()
    old = '<div class="cnx-dlg" id="cnx-dlg-risk" role="dialog" aria-modal="true" aria-labelledby="cnx-dlg-risk-ttl">'
    new = '<div class="cnx-dlg" id="cnx-dlg-risk" role="dialog" aria-labelledby="cnx-dlg-risk-ttl">'
    assert old in html
    html = html.replace(old, new, 1)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C1"]


def test_duplicate_section_fails_only_c1(tmp_path):
    html = _active_cn()
    start = html.index('<section class="rrp pbx"')
    end = html.index("</section>", start) + len("</section>")
    html = html[:end] + html[start:end] + html[end:]
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C1"]


def test_non_http_url_is_an_input_error(tmp_path):
    rc = main(["--url", "file:///tmp/pullback.html", "--market", "us", "--out", str(tmp_path / "receipt.json")])
    assert rc == 2
    assert not (tmp_path / "receipt.json").exists()


def test_missing_html_file_is_an_input_error(tmp_path):
    rc = main(["--html", str(tmp_path / "missing.html"), "--market", "cn"])
    assert rc == 2


_LEAK = "Further decline of 8% is likely"
_FORECAST_OPEN = '<div class="rrp-forecast"'
_FORECAST_STATUS = 'data-forecast-status="unavailable">'
_HIDDEN_STYLE = "position:absolute;left:-9999px;clip:rect(0,0,0,0)"


def _insert(html: str, anchor: str, snippet: str, *, after: bool) -> str:
    assert html.count(anchor) == 1, anchor
    planted = anchor + snippet if after else snippet + anchor
    return html.replace(anchor, planted, 1)


def _assert_c5(rc: int, receipt: dict) -> str:
    assert rc == 1
    assert _failed(receipt) == ["C5"], [
        (item["id"], item["detail"]) for item in receipt["checks"] if not item["pass"]
    ]
    return next(item["detail"] for item in receipt["checks"] if item["id"] == "C5")


def _phase_page(market: str, phase: str) -> str:
    view = native_view(market)
    view["phase"] = phase
    view["observation"]["phase"] = phase
    view["observation"]["active"] = phase in {"underway", "stabilizing", "recovering"}
    if market == "us":
        vm = _vm()
        vm["us_pullback_view"] = view
        return render_us(vm=vm, mode="macro")
    return render_cn(view)


def test_stabilizing_us_and_cn_still_pass(tmp_path):
    """Current, expired, and unavailable already pass above. Stabilizing does too."""
    for market in ("us", "cn"):
        rc, receipt, _page = _run(tmp_path, _phase_page(market, "stabilizing"), market)
        assert rc == 0, [(c["id"], c["detail"]) for c in receipt["checks"] if not c["pass"]]
        assert receipt["phase"] == "stabilizing"
        assert _failed(receipt) == []


def test_hidden_forecast_outside_block_fails_c5(tmp_path):
    """P1: a clipped span outside .rrp-forecast is still forecast copy."""
    snippet = f'<span style="{_HIDDEN_STYLE}">{_LEAK}</span>'
    html = _insert(_active_cn(), _FORECAST_OPEN, snippet, after=False)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "forecast language" in detail


def test_template_forecast_outside_block_fails_c5(tmp_path):
    """P2: template text outside .rrp-forecast is still forecast copy."""
    snippet = f"<template>{_LEAK}</template>"
    html = _insert(_active_cn(), _FORECAST_OPEN, snippet, after=False)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "forecast language" in detail


def test_noscript_forecast_outside_block_fails_c5(tmp_path):
    """P3: noscript text outside .rrp-forecast is still forecast copy."""
    snippet = f"<noscript>{_LEAK}</noscript>"
    html = _insert(_active_cn(), _FORECAST_OPEN, snippet, after=False)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "forecast language" in detail


def test_forecast_aria_label_without_percent_fails_c5(tmp_path):
    """P4: an aria-label with no percent is still forecast copy."""
    old = '<h3><span class="l-en">Estimate unavailable</span>'
    new = '<h3 aria-label="expected remaining drop is severe"><span class="l-en">Estimate unavailable</span>'
    html = _active_cn()
    assert html.count(old) == 1
    html = html.replace(old, new, 1)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "forecast language" in detail
    assert "percent" not in detail


def test_dialog_aria_label_forecast_fails_c5(tmp_path):
    """P5: forecast wording on the dialog element itself fails C5."""
    marker = 'id="cnx-dlg-risk"'
    html = _active_cn()
    assert html.count(marker) == 1
    html = html.replace(marker, marker + ' aria-label="further decline 8%"', 1)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "forecast language" in detail


def test_style_forecast_content_anywhere_fails_c5(tmp_path):
    """P6: a scoped content: value outside .rrp-forecast fails C5."""
    html = _active_cn() + '<style>.rrp-forecast h3::after{content:" further decline 8%"}</style>'
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "disclosure marker" in detail


def test_hidden_forecast_inside_block_still_fails_c5(tmp_path):
    snippet = f'<span style="{_HIDDEN_STYLE}">{_LEAK}</span>'
    html = _insert(_active_cn(), _FORECAST_STATUS, snippet, after=True)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "allow-list" in detail


def test_template_forecast_inside_block_still_fails_c5(tmp_path):
    snippet = f"<template>{_LEAK}</template>"
    html = _insert(_active_cn(), _FORECAST_STATUS, snippet, after=True)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "allow-list" in detail


def test_noscript_forecast_inside_block_still_fails_c5(tmp_path):
    snippet = f"<noscript>{_LEAK}</noscript>"
    html = _insert(_active_cn(), _FORECAST_STATUS, snippet, after=True)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "allow-list" in detail


def test_style_forecast_inside_block_still_fails_c5(tmp_path):
    snippet = '<style>.rrp-forecast h3::after{content:" further decline 8%"}</style>'
    html = _insert(_active_cn(), _FORECAST_STATUS, snippet, after=True)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "allow-list" in detail or "disclosure marker" in detail


def test_forecast_aria_percent_inside_block_still_fails_c5(tmp_path):
    old = '<h3><span class="l-en">Estimate unavailable</span>'
    new = '<h3 aria-label="8%"><span class="l-en">Estimate unavailable</span>'
    html = _active_cn()
    assert html.count(old) == 1
    html = html.replace(old, new, 1)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "percent" in detail


def test_altered_allow_listed_sentence_fails_c5(tmp_path):
    """An allow-listed sentence with one word changed is not exempt."""
    html = _active_cn()
    old = "Not recovery odds"
    assert html.count(old) == 1
    html = html.replace(old, "Recovery odds 60%", 1)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    detail = _assert_c5(rc, receipt)
    assert "forecast language" in detail


# The page script decides what a viewer sees as current. C3 and C7 have to read
# every data-pb-valid-until the way it does, or --require-active can pass bytes
# the page has already expired. Stamps the script reads:
STAMPS_READ = [
    "2026-10-01T09:00:00Z",
    "2026-10-01T09:00:00+00:00",
    "2026-10-01T09:00:00-00:00",
    "2026-10-01T17:00:00+08:00",
    "2026-10-01T05:00:00-04:00",
    "2026-10-01T23:00:00+14:00",
    "2026-09-30T19:00:00-14:00",
    "2026-10-01T23:59:00+14:59",
    "2026-10-01T09:00:00.0Z",
    "2026-10-01T09:00:00.000000+00:00",
    "2028-02-29T00:00:00Z",
    "0100-03-01T00:00:00Z",
]
# Stamps it expires at once, each with a clock at which a looser reading
# (rolled-over fields, years mapped onto the 1900s) would still be current.
STAMPS_REFUSED = [
    ("2026-10-01T09:00:00.001Z", "2026-09-30T09:00:00Z"),
    ("2026-10-01T09:00:00.0000000Z", "2026-09-30T09:00:00Z"),
    ("2026-10-01T17:00:00+0800", "2026-09-30T09:00:00Z"),
    ("2026-10-01T09:00:00+15:00", "2026-09-30T09:00:00Z"),
    ("2026-10-01T09:00:00+08:60", "2026-09-30T09:00:00Z"),
    ("2026-10-01T09:00:00z", "2026-09-30T09:00:00Z"),
    (" 2026-10-01T09:00:00Z", "2026-09-30T09:00:00Z"),
    ("2026-10-01T09:00:00Z ", "2026-09-30T09:00:00Z"),
    ("2026-10-01T09:00:00Z\n", "2026-09-30T09:00:00Z"),
    ("２026-10-01T09:00:00Z", "2026-09-30T09:00:00Z"),
    ("2026-10-01 09:00:00Z", "2026-09-30T09:00:00Z"),
    ("2026-10-01T09:00Z", "2026-09-30T09:00:00Z"),
    ("2026-10-01T09:00:00", "2026-09-30T09:00:00Z"),
    ("2026-13-01T09:00:00Z", "2026-09-30T09:00:00Z"),
    ("2026-02-29T09:00:00Z", "2026-02-27T00:00:00Z"),
    ("2026-10-01T24:00:00Z", "2026-09-30T09:00:00Z"),
    ("2026-10-01T09:60:00Z", "2026-09-30T09:00:00Z"),
    ("2026-10-01T09:00:60Z", "2026-09-30T09:00:00Z"),
    ("0099-10-01T09:00:00Z", "1999-09-30T09:00:00Z"),
    ("0099-10-01T09:00:00Z", "0099-09-30T09:00:00Z"),
]


def _stamp_cases():
    from datetime import datetime, timedelta

    from scripts.verify_risk_radar_pullback_served import MAX_AHEAD, _parse_valid_until

    second = timedelta(seconds=1)
    cases = []
    for stamp in STAMPS_READ:
        instant = _parse_valid_until(stamp)
        assert instant is not None, stamp
        for now in (instant - second, instant, instant - MAX_AHEAD, instant - MAX_AHEAD - second):
            cases.append((stamp, now))
    for stamp, clock in STAMPS_REFUSED:
        cases.append((stamp, datetime.fromisoformat(clock)))
    return cases


def test_c7_reads_every_stamp_as_the_shipped_page_script_does():
    """Run the shipped expiry owner in Node on each stamp and clock; C7 agrees."""
    from datetime import datetime, timedelta, timezone

    from scripts.verify_risk_radar_pullback_served import _check_c7
    from tests.test_pullback_expiry_owner_js_edge import _run_json

    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    cases = _stamp_cases()
    wire = [[stamp, (now - epoch) // timedelta(milliseconds=1)] for stamp, now in cases]
    body = (
        "const cases = " + json.dumps(wire) + ";\n"
        "const out = cases.map(([stamp, ms]) => {\n"
        "  now = ms; const sec = section(stamp); boot([sec]);\n"
        "  return !sec.classes.has('pb-expired');\n"
        "});\n"
        "console.log(JSON.stringify({current: out}));\n"
    )
    page = _run_json(body, "UTC")["current"]
    verifier = [_check_c7("underway", stamp, True, now)[0] for stamp, now in cases]
    disagree = [
        (stamp, now.isoformat(), page_current, ours)
        for (stamp, now), page_current, ours in zip(cases, page, verifier)
        if page_current != ours
    ]
    assert disagree == []
    # Both directions are exercised: the four clocks per read stamp give two
    # current and two expired verdicts, and every refused stamp is expired.
    assert sum(verifier) == 2 * len(STAMPS_READ)


def _with_stamp(html: str, stamp: str) -> str:
    old = "2026-10-01T09:00:00+00:00"
    attr = f'data-pb-valid-until="{old}"'
    time = f'<time datetime="{old}">'
    assert html.count(attr) == 1 and html.count(time) == 1
    html = html.replace(attr, f'data-pb-valid-until="{stamp}"', 1)
    return html.replace(time, f'<time datetime="{stamp}">', 1)



@pytest.mark.parametrize("stamp", [
    "2026-10-01T09:00:00.001+00:00",
    "2026-10-01T09:00:00+0000",
    "2026-10-01T09:00:00+15:00",
])
def test_stamp_the_page_expires_fails_c3_and_c7(tmp_path, stamp):
    """A fraction, a colonless offset or an offset past +14:00 expires the
    panel in the page, so the served bytes are neither a receipt nor current."""
    html = _with_stamp(_active_cn(), stamp)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C3"]
    detail = next(item["detail"] for item in receipt["checks"] if item["id"] == "C3")
    assert "not a stamp the page script reads" in detail
    rc, receipt, _page = _run(tmp_path, html, "cn", "--require-active", "--now", STILL_CURRENT)
    assert rc == 1
    assert _failed(receipt) == ["C3", "C7"]
    detail = next(item["detail"] for item in receipt["checks"] if item["id"] == "C7")
    assert detail == "valid_until missing or unparseable"


def test_zero_fraction_stamp_stays_current(tmp_path):
    """The page reads a zero fraction as the same second; so does the verifier."""
    html = _with_stamp(_active_cn(), "2026-10-01T09:00:00.000+00:00")
    rc, receipt, _page = _run(tmp_path, html, "cn", "--require-active", "--now", STILL_CURRENT)
    assert rc == 0, [(c["id"], c["detail"]) for c in receipt["checks"] if not c["pass"]]


_OWNER_RE = re.compile(r"<script>/\* Observation expiry owner.*?</script>", re.DOTALL)


def _c7_detail(receipt: dict) -> str:
    return next(item["detail"] for item in receipt["checks"] if item["id"] == "C7")


@pytest.mark.parametrize("market", ["us", "cn"])
def test_require_active_needs_the_served_expiry_script(tmp_path, market):
    """Without the page script nothing hides the figures after valid_until."""
    html = _active_us() if market == "us" else _active_cn()
    assert len(_OWNER_RE.findall(html)) == 1
    stripped = _OWNER_RE.sub("", html)
    rc, receipt, _page = _run(tmp_path, stripped, market)
    assert rc == 0, [(c["id"], c["detail"]) for c in receipt["checks"] if not c["pass"]]
    rc, receipt, _page = _run(tmp_path, stripped, market, "--require-active", "--now", STILL_CURRENT)
    assert rc == 1
    assert _failed(receipt) == ["C7"]
    assert _c7_detail(receipt) == "the page expiry script is not served"


def test_require_active_needs_the_section_the_script_selects(tmp_path):
    html = _active_cn()
    old = '<section class="rrp pbx"'
    assert html.count(old) == 1
    html = html.replace(old, '<section class="pbx"', 1)
    rc, receipt, _page = _run(tmp_path, html, "cn", "--require-active", "--now", STILL_CURRENT)
    assert rc == 1
    assert "C7" in _failed(receipt)
    assert _c7_detail(receipt) == (
        "section does not match .rrp.pbx[data-pb-valid-until]; the page script never expires it"
    )


@pytest.mark.parametrize("old,new,detail", [
    (r"(\.0{1,6})?", r"(\.\d{1,6})?",
     "the served expiry script reads valid_until with a different pattern"),
    ("var MAX_AHEAD_MS = 400 *", "var MAX_AHEAD_MS = 401 *",
     "the served expiry script caps valid_until at a different horizon"),
])
def test_require_active_needs_the_served_script_to_read_stamps_as_c7_does(tmp_path, old, new, detail):
    html = _active_cn()
    script = _OWNER_RE.search(html).group(0)
    assert script.count(old) == 1
    html = html.replace(script, script.replace(old, new, 1), 1)
    rc, receipt, _page = _run(tmp_path, html, "cn", "--require-active", "--now", STILL_CURRENT)
    assert rc == 1
    assert _failed(receipt) == ["C7"]
    assert _c7_detail(receipt) == detail


def test_c7_stamp_pattern_is_the_page_script_pattern():
    from scripts.verify_risk_radar_pullback_served import PAGE_STAMP

    js = (Path(__file__).resolve().parents[1]
          / "templates/_risk_radar_pullback_depth.js.j2").read_text(encoding="utf-8")
    assert f"var STAMP = /{PAGE_STAMP}/;" in js
