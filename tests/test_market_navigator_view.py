"""Render integration through the incumbent response wire; no live network or Paper."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts.research.market_navigator_view_browser_check import synthetic_wire

ROOT = Path(__file__).resolve().parents[1]


def test_browserless_js_view_with_actual_python_wire():
    source = synthetic_wire()
    result = subprocess.run(["node", "tests/market_navigator_view_harness.js"],
                            cwd=ROOT, text=True, input=json.dumps(source),
                            capture_output=True, timeout=20, check=True)
    assert "PASS" in result.stdout


def test_ui_scripts_are_syntax_valid():
    for entry in ("templates/market_navigator_view.js", "templates/market_navigator_client.js",
                  "tests/market_navigator_view_harness.js"):
        subprocess.run(["node", "--check", entry], cwd=ROOT,
                       check=True, capture_output=True, timeout=10)


def test_view_has_closed_surface_without_io_or_implicit_trade_action():
    view = (ROOT/"templates/market_navigator_view.js").read_text()
    style = (ROOT/"templates/market_navigator_view.css").read_text()
    assert "textContent" in view and "createView" in view
    for forbidden in ("fetch(", "localStorage", "sessionStorage", "XMLHttpRequest",
                      ".innerHTML", "document.cookie", "WebSocket(",
                      "addEventListener('message'", "setInterval("):
        assert forbidden not in view
    assert ".mnv" in style
    assert "prefers-reduced-motion" in style
