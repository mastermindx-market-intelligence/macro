"""P-MP1-SHELL §10/Amendment 1 V-B4 — the ladder's ERROR state.

Distinct from LOADING (book is None, artifact not yet published — normal,
wordless skeleton) by CAUSE: `us_prophet_book_error` is set only when
site/prophet/index.json EXISTS but fails to parse (scripts/build_site.py) —
a real read failure, never the "hasn't published yet" case. The Chairman-approved September 16 record-only direction supersedes the old
unconditional assurance that unrelated sources are current. A failed plan read
cannot certify freshness of Candidates, Groups or the outcome record.
"""
from __future__ import annotations

from pathlib import Path

import jinja2

ROOT = Path(__file__).resolve().parent.parent


def _env() -> jinja2.Environment:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    return env


def test_error_state_renders_tracking_failure_without_certifying_other_sources():
    t = _env().get_template("_prophet_card.html.j2")
    html = str(t.module.mx_ladder(None, error=True))
    assert 'class="mx-error"' in html
    assert "Tracking unavailable. Check the dates on Candidates and the record below." in html
    assert "跟踪暂不可用。请核对候选与下方记录各自的日期。" in html
    assert "Retry" in html and "重试" in html
    # ≥40px touch floor (MPDS §14), on both axes
    assert "min-height:40px" in html and "min-width:40px" in html
    # error state never renders the loading skeleton markup
    assert "skel" not in html


def test_loading_state_unaffected_by_the_error_param_default():
    t = _env().get_template("_prophet_card.html.j2")
    html = str(t.module.mx_ladder(None))
    assert 'aria-busy="true"' in html
    assert 'class="mx-error"' not in html


def test_build_site_distinguishes_missing_from_unreadable():
    src = (ROOT / "scripts" / "build_site.py").read_text()
    idx_read = src.index("def _read_us_prophet_book")
    idx_absent = src.index("if not path.exists():", idx_read)
    idx_except = src.index("except Exception as exc:", idx_read)
    # Missing retains loading; the unreadable flag belongs to the exception
    # branch, before main consumes both halves of the reader result.
    assert src.index("return None, False", idx_absent) < idx_except
    assert src.index("return None, True", idx_except) > idx_except
    assert "us_prophet_book, us_prophet_book_error = _read_us_prophet_book(" in src


def test_build_site_wires_the_error_flag_through_both_render_call_sites():
    src = (ROOT / "scripts" / "build_site.py").read_text()
    assert src.count('"us_prophet_book_error": us_prophet_book_error') == 2


def test_dashboard_consumes_the_error_flag():
    dash = (ROOT / "templates" / "dashboard.html.j2").read_text()
    assert "pv.mx_ladder(_upb, error=_upb_err)" in dash
    # the grid/tier-wall must not attempt to render while erroring (book is
    # always None alongside the error flag, but the template guards belt-
    # and-braces on the flag too)
    assert "{%- if _upb and not _upb_err %}" in dash
