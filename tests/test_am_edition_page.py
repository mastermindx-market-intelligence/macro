"""RED-first contract tests for the AM Edition HTML page (packet MO-B F01-1).

These tests drive the page template and producer against tmp_path fixture
trees with a frozen `now` — none touch the network, none require the real
data/ or site/ trees, so this file is safe in a sparse worktree and needs
no needs_full_checkout marker.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from lib import nyse_calendar
from scripts.build_am_edition import (
    STATES,
    build_payload,
    _humanize_age,
    _is_session_open_now,
    _session_phase,
)

FORBIDDEN_KEYS = {
    "score", "rank", "signal", "gate", "size", "sizing", "ENTRY_OPEN",
    "prophet", "conviction", "buy", "sell", "target",
    "projection", "confidence", "surprise_skew", "surprise_distribution",
    "reaction_sensitivity", "market_implied", "inputs_hash", "model_epoch",
}


def _write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


def _fresh_tree(tmp_path: Path, *, tape_asof: str, session_date: str) -> tuple[Path, Path]:
    site = tmp_path / "site"
    data = tmp_path / "data"
    _write(site / "live" / "quotes.json", {
        "ts": 1, "asof": tape_asof, "source": "yahoo",
        "quotes": {
            "SPY": {"price": 740.0, "prevClose": 739.0, "changePct": 0.14, "basis": "regular"},
        },
        "meta": {},
    })
    _write(data / "market_state" / "latest.json", {
        "asof": session_date, "label_en": "Risk-on", "label_zh": "风险偏好",
        "posture_en": "Constructive", "posture_zh": "积极", "headline_en": "x", "headline_zh": "x",
    })
    _write(data / "regime" / "latest.json", {
        "asof": session_date, "quad_name": "Reflation", "label": "Q2",
    })
    _write(data / "neuralweb" / "market_plane.json", {
        "asof": session_date,
        "verdict": {
            "verdict": "RISK_ON", "score": 75, "label_en": "Risk-on", "label_zh": "风险偏好",
        },
        "contradiction_count": 0,
        "stale": False,
        "gaps": ["options_structure: no usable options_hub/gex payload for SPX/SPY/QQQ"],
    })
    _write(data / "release_forecast" / "latest.json", {
        "asof": f"{session_date}T10:00:00Z",
        "upcoming": [{
            "release": "cpi",
            "release_type": "cpi_headline",
            "release_date": session_date,
            "target": "mom_sa_pct",
            "projection": {
                "point": 0.2018, "p10": -0.5103, "p25": -0.0278,
                "p50": 0.2994, "p75": 0.6296, "p90": 0.8925,
            },
            "confidence": 0.42,
            "confidence_v2": 0.41,
            "surprise_skew": {"sigma": 0.4895, "tag": "hotter"},
            "surprise_distribution": {"p10": -0.5, "p90": 0.9},
            "reaction_sensitivity": {"spy": 0.3},
            "revision_risk": 0.1,
            "market_implied": {"source": "polymarket", "implied": "0.2%"},
            "model_epoch": "v3",
            "inputs_hash": "deadbeef",
            "code_receipt": "engine/release_forecast.py:1",
        }],
    })
    _write(site / "master_brief.json", {
        "generated_at": f"{session_date}T10:00:00Z", "state_asof": session_date, "lens": "macro",
    })
    return site, data


def _empty_tree(tmp_path: Path) -> tuple[Path, Path]:
    site = tmp_path / "site"
    data = tmp_path / "data"
    site.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    return site, data


# ── Template existence ────────────────────────────────────────────────────────

def test_template_exists():
    """The template must exist before this test file can even be written."""
    assert Path("templates/am_edition.html.j2").exists(), \
        "templates/am_edition.html.j2 is missing — RED on 9a4a389c confirmed"


# ── Template rendering ────────────────────────────────────────────────────────

def test_page_renders_with_heading_and_bilingual(tmp_path):
    """The rendered page must contain the Morning Edition heading in both EN and ZH."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    # Provide a minimal payload for rendering.
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)

    template = env.get_template("am_edition.html.j2")
    html = template.render(payload=payload, as_of="2026-09-08T15:00Z")

    # EN heading
    assert "Morning Edition" in html
    # ZH heading
    assert "早间版" in html
    # Both language spans present
    assert 'class="l-en"' in html
    assert 'class="l-zh"' in html
    # Session-state display (state shown as a CSS badge class, not raw string)
    # OPEN/CLOSED/NOT_YET_OPEN is rendered as a state badge with label text.
    assert ("US markets open" in html or "美股正在交易" in html or
            "US markets closed" in html or "美股已收盘" in html or
            "US markets not yet open" in html or "美股尚未开盘" in html)


def test_page_contains_no_english_only_payload_values_in_zh_mode(tmp_path):
    """Payload values must render as paired EN/ZH spans, not ZH-only fallbacks."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    def render_without_english_spans(payload: dict) -> str:
        html = env.get_template("am_edition.html.j2").render(
            payload=payload, as_of="2026-09-08T15:00Z"
        )
        for pattern in (
            r"<script\b.*?</script>",
            r"<title\b.*?</title>",
            r"<nav\b.*?</nav>",
            r'<span\b[^>]*\bclass="[^"]*\bl-en\b[^"]*"[^>]*>.*?</span>.*?</span>?',
        ):
            html = re.sub(pattern, " ", html, flags=re.DOTALL | re.I)
        return " ".join(re.sub(r"<[^>]+>", " ", html).split())

    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    for drop_zh_fields in (False, True):
        site, data = _fresh_tree(
            tmp_path / ("with-zh" if drop_zh_fields is False else "without-zh"),
            tape_asof="2026-09-08T13:00:00Z",
            session_date="2026-09-08",
        )
        if drop_zh_fields:
            market_state = json.loads(
                (data / "market_state" / "latest.json").read_text(encoding="utf-8")
            )
            market_state.update({
                "label_zh": None,
                "posture_zh": None,
                "headline_zh": None,
            })
            (data / "market_state" / "latest.json").write_text(
                json.dumps(market_state), encoding="utf-8"
            )
            market_plane = json.loads(
                (data / "neuralweb" / "market_plane.json").read_text(encoding="utf-8")
            )
            market_plane["verdict"].update({
                "label_en": "Risk-off",
                "label_zh": None,
            })
            (data / "neuralweb" / "market_plane.json").write_text(
                json.dumps(market_plane), encoding="utf-8"
            )

        payload = build_payload(site, data, now=now)
        payload["morning_source_feasibility"] = "DEGRADED"
        payload["morning_source_feasibility_cause_en"] = "Morning source is degraded."
        payload["morning_source_feasibility_cause_zh"] = "晨间数据源已降级。"
        visible_text = render_without_english_spans(payload)
        for token in ("Risk-on", "Constructive", "Risk-off", "CPI"):
            assert token not in visible_text, (
                f"English-only payload token {token!r} leaks in ZH mode "
                f"(fixture with Zh fields: {not drop_zh_fields})"
            )


def test_page_contains_aibrief_link(tmp_path):
    """The prior-close brief block must render as a link to /aibrief.html."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)

    template = env.get_template("am_edition.html.j2")
    html = template.render(payload=payload, as_of="2026-09-08T15:00Z")

    assert 'href="/aibrief.html"' in html


def test_page_contains_no_forbidden_authority_fields(tmp_path):
    """FORBIDDEN_KEYS must not appear as visible authority copy in the HTML."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    import re

    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    now = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")
    payload = build_payload(site, data, now=now)

    template = env.get_template("am_edition.html.j2")
    html = template.render(payload=payload, as_of="2026-09-08T15:00Z")

    # Strip HTML tags and inline CSS (box-sizing etc.) to get only visible copy.
    # Also strip the shared site nav AND its embedded <style> block since the nav
    # contains third-party labels (e.g. "signal lab", "Prophet") that are not
    # AM-edition copy.
    text_only = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL)
    text_only = re.sub(r'<nav[^>]*>.*?</nav>', ' ', text_only, flags=re.DOTALL)
    text_only = re.sub(r'<[^>]+>', ' ', text_only)
    text_lower = text_only.lower()
    for key in FORBIDDEN_KEYS:
        # Use word-boundary regex to avoid false positives from substrings like
        # "aggregate" containing "gate" or "sign" containing "signal".
        assert not re.search(r'\b' + re.escape(key) + r'\b', text_lower), \
            f"Forbidden authority field '{key}' found in visible HTML text"


# ── Producer integration ─────────────────────────────────────────────────────

def test_main_writes_both_json_and_html(tmp_path):
    """main() must write both am_edition.json and am_edition.html."""
    from scripts import build_am_edition as mod
    from lib import pages as pages_mod

    site = tmp_path / "site"
    data = tmp_path / "data"
    site.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)

    # Minimal fixtures so build_payload does not immediately return null blocks.
    _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")

    class _FakeCfg(dict):
        pass

    orig_load = mod.config.load
    orig_root = mod.config.ROOT
    orig_pages_root = pages_mod.config.ROOT
    try:
        mod.config.load = lambda: {"storage": {"site_dir": str(site)}}
        mod.config.ROOT = str(tmp_path)
        # pages.config.ROOT must be a Path (not str) for the / operator.
        import pathlib
        pages_mod.config.ROOT = pathlib.Path(str(tmp_path))
        rc = mod.main()
        assert rc == 0
        json_path = site / "am_edition.json"
        html_path = site / "am_edition.html"
        assert json_path.exists(), "am_edition.json was not written"
        assert html_path.exists(), "am_edition.html was not written"
        # Both must be non-empty.
        assert json_path.stat().st_size > 100
        assert html_path.stat().st_size > 200
    finally:
        mod.config.load = orig_load
        mod.config.ROOT = orig_root
        pages_mod.config.ROOT = orig_pages_root


def test_html_written_via_write_page_contains_dbase_shim(tmp_path):
    """am_edition.html must be written through lib.pages.write_page (has dbase shim)."""
    from scripts import build_am_edition as mod
    from lib import pages as pages_mod

    site = tmp_path / "site"
    data = tmp_path / "data"
    site.mkdir(parents=True, exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)

    _fresh_tree(tmp_path, tape_asof="2026-09-08T13:00:00Z", session_date="2026-09-08")

    class _FakeCfg(dict):
        pass

    orig_load = mod.config.load
    orig_root = mod.config.ROOT
    orig_pages_root = pages_mod.config.ROOT
    try:
        mod.config.load = lambda: {"storage": {"site_dir": str(site)}}
        mod.config.ROOT = str(tmp_path)
        # pages.config.ROOT must be a Path (not str) for the / operator.
        import pathlib
        pages_mod.config.ROOT = pathlib.Path(str(tmp_path))
        mod.main()
        html_path = site / "am_edition.html"
        content = html_path.read_text(encoding="utf-8")
        marker_pattern = re.compile(r"<script[^>]+\bdata-dbase\b[^>]*>")
        assert marker_pattern.search(content), (
            "am_edition.html is missing lib.pages.write_page's data-dbase shim marker"
        )
    finally:
        mod.config.load = orig_load
        mod.config.ROOT = orig_root
        pages_mod.config.ROOT = orig_pages_root
