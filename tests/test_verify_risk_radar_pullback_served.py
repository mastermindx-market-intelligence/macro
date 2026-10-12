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
    assert "whole_page_count=" in next(c["detail"] for c in receipt["checks"] if c["id"] == "C6")
    rc_active, receipt_active, _page = _run(tmp_path, html, "us", "--require-active")
    assert rc_active == 0 and receipt_active["pass"] is True


def test_active_cn_passes_with_and_without_require_active(tmp_path):
    html = _active_cn()
    rc, receipt, page = _run(tmp_path, html, "cn", "--require-active")
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


def test_unavailable_fails_when_require_active(tmp_path):
    rc, receipt, _page = _run(tmp_path, _unavailable_cn(), "cn", "--require-active")
    assert rc == 1
    assert receipt["pass"] is False
    assert _failed(receipt) == ["C7"]


def test_digit_in_forecast_row_fails_only_c5(tmp_path):
    html = _active_cn()
    needle = f"<strong>{EM}</strong>"
    assert needle in html
    html = html.replace(needle, f"<strong>{EM}1</strong>", 1)
    rc, receipt, _page = _run(tmp_path, html, "cn")
    assert rc == 1
    assert _failed(receipt) == ["C5"]


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
