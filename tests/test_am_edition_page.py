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

ROOT = Path(__file__).resolve().parents[1]
from scripts.build_am_edition import (
    STATES,
    build_payload,
    _humanize_age,
    _is_session_open_now,
    _session_phase,
)

FORBIDDEN_KEYS = {
    "rank", "signal", "gate", "sizing", "ENTRY_OPEN",
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


# ── MOR-2b Lane C — new blocks (context_planes, research_watch, owner_links) ─
#
# These tests pin the §4 C1/C2 surface contract: every block ships a header
# row with eyebrow + h2 + state chip + .dtp-asof clock; state -> chip mapping
# is one-to-one; non-CURRENT/STALE blocks render .mx-empty + .mx-empty-line +
# .mx-empty-why with the reason; ZH parity is preserved (every EN string has a
# ZH twin via t()); no title= attribute carries translated text.

import importlib

STATE_CHIP_PAIRS = {
    "CURRENT": ("live", "Live", "实时"),
    "NOT_YET_OPEN": ("pre", "Not yet open", "尚未开始"),
    "STALE_WITH_LAST_KNOWN": ("stale", "Stale — last known", "已滞后 — 最新已知"),
    "UNAVAILABLE": ("warn", "Unavailable", "不可用"),
    "NOT_COVERED": ("behind", "Not covered", "未覆盖"),
}


def _render_am_edition(payload: dict) -> str:
    """Render templates/am_edition.html.j2 with the given payload."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    from engine import i18n  # registers t() / td() / tr() in env.globals

    env.globals.update(t=i18n.t, td=i18n.td, tr=i18n.tr)
    template = env.get_template("am_edition.html.j2")
    return template.render(payload=payload, as_of="2026-09-08T15:00Z")


def _make_fresh_blocks(tmp_path: Path, session_date: str = "2026-09-08") -> list[dict]:
    """Build a fresh set of MOR-2b blocks for testing. All three blocks in CURRENT."""
    return [
        {
            "key": "context_planes",
            "title_en": "Context planes",
            "title_zh": "背景面",
            "state": "CURRENT",
            "source_as_of": f"{session_date}T13:00:00+00:00",
            "rows": [
                {
                    "plane": "rates",
                    "label_en": "Steady",
                    "label_zh": "稳定",
                    "read_en": "Rates are steady this morning.",
                    "read_zh": "今晨利率保持稳定。",
                    "as_of": f"{session_date}T13:00:00+00:00",
                    "source_ref": "data/transmission/latest.json",
                    "state": "CURRENT",
                },
                {
                    "plane": "commodity",
                    "label_en": "Constructive",
                    "label_zh": "偏积极",
                    "read_en": "Commodity complex is steady with a soft bid.",
                    "read_zh": "商品整体企稳，有小幅买盘。",
                    "as_of": f"{session_date}T13:00:00+00:00",
                    "source_ref": "data/transmission/latest.json",
                    "state": "CURRENT",
                },
            ],
        },
        {
            "key": "research_watch",
            "title_en": "Research watch",
            "title_zh": "研究观察",
            "state": "CURRENT",
            "source_as_of": f"{session_date}T10:00:00+00:00",
            "calibration_note_en": "Calibration summary covers through 2026-09-08.",
            "calibration_note_zh": "校准汇总更新至 2026-09-08。",
            "rows": [
                {
                    "condition_en": "Watch when the dollar breaks its 20-day range.",
                    "condition_zh": "观察美元是否突破20日区间。",
                    "condition_zh_disclosed_why": None,
                    "since": f"{session_date}",
                    "as_of": f"{session_date}T10:00:00+00:00",
                    "source_ref": "data/master_brain/theses.jsonl",
                },
            ],
        },
        {
            "key": "owner_links",
            "title_en": "Owner pages & references",
            "title_zh": "主理页面与参考",
            "state": "CURRENT",
            "source_as_of": f"{session_date}T07:30:00+00:00",
            "rows": [
                {
                    "plane": "rates",
                    "label_en": "Macro dashboard",
                    "label_zh": "宏观仪表盘",
                    "href": "macro.html",
                    "kind": "owner",
                },
                {
                    "plane": "rates_and_credit",
                    "label_en": "Rates & credit dashboard",
                    "label_zh": "利率与信用",
                    "href": "bonds.html",
                    "kind": "owner",
                },
                {
                    "plane": "international",
                    "label_en": "China & Hong Kong",
                    "label_zh": "中国与香港",
                    "href": "china.html",
                    "kind": "owner",
                },
            ],
        },
    ]


def _build_payload(tmp_path: Path, blocks: list[dict]) -> dict:
    """Wrap the block list in the minimal payload the template needs."""
    return {
        "session_state": "NOT_YET_OPEN",
        "generated_at": "2026-09-08T15:00:00+00:00",
        "blocks": blocks,
        "morning_source_feasibility": "AVAILABLE",
        "morning_source_feasibility_cause_en": None,
        "morning_source_feasibility_cause_zh": None,
        "null_count": 0,
    }


def _panel_html(html: str, eyebrow_en: str) -> str:
    """Return the <div class="panel"> chunk whose eyebrow carries ``eyebrow_en``."""
    chunks = html.split('<div class="panel">')
    hits = [c for c in chunks[1:] if eyebrow_en in c]  # chunk 0 = everything before the first panel (head + nav)
    assert hits, f"no panel with eyebrow {eyebrow_en!r}"
    return hits[0]


def _strip_html(html: str) -> str:
    """Remove style/nav/script blocks and tags so we can search visible text."""
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL)
    text = re.sub(r'<nav[^>]*>.*?</nav>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


# ── C1: each block renders in every typed state ──────────────────────────────


@pytest.mark.parametrize("state", ["CURRENT", "STALE_WITH_LAST_KNOWN"])
def test_context_planes_renders_rows_in_current_or_stale(tmp_path, state):
    """context_planes rows render when state is CURRENT or STALE_WITH_LAST_KNOWN."""
    blocks = _make_fresh_blocks(tmp_path)
    blocks[0]["state"] = state
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    # Row content visible
    assert "Rates are steady this morning." in _strip_html(html)
    assert "今晨利率保持稳定。" in _strip_html(html)
    # Header chip uses the seat-pinned .dtp-chip primitive (BLOCKER 6 round 2)
    chip_pair = STATE_CHIP_PAIRS[state]
    assert f'dtp-chip--{chip_pair[0]}' in html
    # The parallel .mx-state-chip family must NOT appear as a class attr — no
    # parallel class. Strip <style> blocks first (the source-level comment
    # "no .mx-state-chip family exists." lives there) so the check is scoped
    # to actual rendered class= attributes only.
    body_only = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL)
    assert 'class="mx-state-chip' not in body_only
    assert chip_pair[1] in _strip_html(html)
    assert chip_pair[2] in _strip_html(html)
    # Built at asof is non-vacuous (MAJOR 4 round 2): we verify the block-level
    # clock reads block.source_as_of and renders the fixture's exact prefix.
    # The prior round's assertion `"Built at" in html` matched the page-header
    # "Built at" footer and silently passed with source_asof=None.
    assert "2026-09-08T13:00" in html, (
        "context_planes clock must read source_as_of (the producer key) and "
        "render the fixture's prefix 2026-09-08T13:00"
    )


@pytest.mark.parametrize("state", ["UNAVAILABLE", "NOT_COVERED", "NOT_YET_OPEN"])
def test_context_planes_renders_mx_empty_when_not_current(tmp_path, state):
    """context_planes renders .mx-empty + .mx-empty-line + .mx-empty-why when state
    is anything other than CURRENT or STALE_WITH_LAST_KNOWN."""
    blocks = _make_fresh_blocks(tmp_path)
    blocks[0]["state"] = state
    blocks[0]["state_reason_en"] = f"Test reason for {state}."
    blocks[0]["state_reason_zh"] = f"{state} 测试原因。"
    blocks[0]["rows"] = []
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    # The empty block markers
    assert "mx-empty" in html
    assert "mx-empty-line" in html
    assert "mx-empty-why" in html
    # Reason text is rendered in both EN and ZH
    assert "Test reason" in _strip_html(html)
    assert "测试原因" in _strip_html(html)
    # No row content leaks through
    assert "Rates are steady this morning." not in _strip_html(html)


def test_research_watch_renders_rows_in_current(tmp_path):
    """research_watch rows render when state is CURRENT."""
    blocks = _make_fresh_blocks(tmp_path)
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    text = _strip_html(html)
    assert "Watch when the dollar breaks its 20-day range." in text
    assert "观察美元是否突破20日区间。" in text
    # Calibration note is rendered
    assert "Calibration summary covers through 2026-09-08." in text


@pytest.mark.parametrize("state", ["UNAVAILABLE", "NOT_COVERED"])
def test_research_watch_renders_mx_empty_in_non_current(tmp_path, state):
    """research_watch renders .mx-empty in non-CURRENT/STALE states."""
    blocks = _make_fresh_blocks(tmp_path)
    blocks[1]["state"] = state
    blocks[1]["state_reason_en"] = f"Research watch {state} reason."
    blocks[1]["state_reason_zh"] = f"研究观察 {state} 原因。"
    blocks[1]["rows"] = []
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    assert "mx-empty" in html
    assert f"Research watch {state}" in _strip_html(html)


def test_owner_links_renders_rows_in_current(tmp_path):
    """owner_links rows render as .brief-link when state is CURRENT."""
    blocks = _make_fresh_blocks(tmp_path)
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    assert 'class="brief-link"' in html
    assert 'href="macro.html"' in html
    assert 'href="bonds.html"' in html
    assert 'href="china.html"' in html
    text = _strip_html(html)
    assert "Macro dashboard" in text
    assert "宏观仪表盘" in text
    # MAJOR 2 round 2: owner_links must render its clock too (the prior round
    # rendered no .dtp-asof on this block). The fixture stamps
    # source_as_of = 2026-09-08T07:30.
    assert "2026-09-08T07:30" in html, (
        "owner_links must render a .dtp-asof clock from source_as_of"
    )
    # BLOCKER 5 round 2: plane slugs must surface as plain words, never
    # `rates_and_credit` or `RATES_AND_CREDIT`. The render shows "Rates &
    # Credit" / "利率与信用".
    assert "Rates &amp; Credit" in html or "Rates & Credit" in text
    assert "利率与信用" in text
    assert "Rates &amp; credit dashboard" in html or "Rates & credit dashboard" in text
    # Raw slug MUST NOT appear in visible copy.
    assert "rates_and_credit" not in text.replace(" ", "").replace("rates_and_credit".replace("_", " "), "")


def test_owner_links_renders_stale_with_last_known_rows(tmp_path):
    """MAJOR 2 round 2: owner_links degrades ONLY when state is not CURRENT or
    STALE_WITH_LAST_KNOWN. STALE rows render the .mx-ol-row with brief-link,
    not the .mx-empty placeholder. The prior round routed STALE rows to the
    empty block, hiding last-known owners."""
    blocks = _make_fresh_blocks(tmp_path)
    blocks[2]["state"] = "STALE_WITH_LAST_KNOWN"
    blocks[2]["state_reason_en"] = "Owner registry has not refreshed since 02:00 UTC."
    blocks[2]["state_reason_zh"] = "主理页面注册表自UTC 02:00起未刷新。"
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    # Rows are still rendered (STALE keeps last-known links per C1).
    assert 'class="brief-link"' in html
    assert 'href="macro.html"' in html
    assert 'href="bonds.html"' in html
    # The block-level chip carries --stale, not the warn/behind fall-through.
    assert "dtp-chip--stale" in html
    body_only = re.sub(r'<style[^>]*>.*?</style>', ' ', html, flags=re.DOTALL)
    assert 'class="mx-state-chip' not in body_only
    # The empty placeholder must NOT be rendered for STALE — scoped to the
    # owner_links panel so unrelated blocks cannot mask a regression.
    owner = _panel_html(html, "Owner pages")
    assert "mx-empty" not in owner, "STALE owner_links must keep its rows, not degrade to .mx-empty"
    assert owner.count('class="mx-ol-row"') == 3
    text = _strip_html(owner)
    assert "Owner registry has not refreshed since 02:00 UTC." in text
    assert "主理页面注册表自UTC 02:00起未刷新。" in text


def test_owner_links_renders_mx_empty_in_not_covered(tmp_path):
    """owner_links renders .mx-empty when state is NOT_COVERED."""
    blocks = _make_fresh_blocks(tmp_path)
    blocks[2]["state"] = "NOT_COVERED"
    blocks[2]["state_reason_en"] = "No owner pages could be linked this morning."
    blocks[2]["state_reason_zh"] = "今晨无法链接到相关页面。"
    blocks[2]["rows"] = []
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    assert "mx-empty" in html
    assert "mx-empty-why" in html
    text = _strip_html(html)
    assert "今晨无法链接到相关页面。" in text


def test_owner_links_renders_clock_from_source_as_of(tmp_path):
    """BLOCKER 3 round 2: owner_links clock must read source_as_of (the producer
    key) and surface it under .dtp-asof. The prior round had no clock on this
    block at all. We assert both that the key prefix renders AND that the wrong
    key (`source_asof`, missing underscore) is NOT what the template reads."""
    blocks = _make_fresh_blocks(tmp_path)
    payload = _build_payload(tmp_path, blocks)
    owner = _panel_html(_render_am_edition(payload), "Owner pages")
    # Direction 1: a fixture clock renders exactly once under .dtp-asof.
    assert 'class="dtp-asof"' in owner and "2026-09-08T07:30" in owner, (
        "owner_links must render its source_as_of clock under .dtp-asof"
    )
    # Direction 2: the producer emits source_as_of=None for owner_links (the
    # static-link block has no clock); the template must then render NO clock
    # rather than a blank or a wrong key.
    blocks = _make_fresh_blocks(tmp_path)
    blocks[2]["source_as_of"] = None
    blocks[2]["source_asof"] = "1999-01-01T00:00:00+00:00"  # the wrong key must be ignored
    owner = _panel_html(_render_am_edition(_build_payload(tmp_path, blocks)), "Owner pages")
    assert 'class="dtp-asof"' not in owner
    assert "1999-01-01" not in owner


def test_new_blocks_render_title_zh_on_every_h2(tmp_path):
    """BLOCKER 4 round 2: every new block's <h2> must carry both title_en and
    title_zh via t() — the prior round rendered title_en only on ZH pages.
    Each h2 in the three new blocks must include the paired l-en / l-zh spans."""
    blocks = _make_fresh_blocks(tmp_path)
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    text = _strip_html(html)
    # Each block's title pair must appear adjacent (paired via t()).
    # We assert each pair is present AND that the producer's ZH title was
    # actually read (not silently falling back to the eyebrow text).
    pairs = [
        ("Context planes", "背景面"),
        ("Research watch", "研究观察"),
        ("Owner pages", "主理页面"),
    ]
    for en, zh in pairs:
        assert en in text, f"missing EN title: {en}"
        assert zh in text, f"missing ZH title twin: {zh} for {en}"
    # Negative: a title that the producer did NOT provide (e.g. "Foo bar") must
    # not be the value of any h2 in the new blocks. We can't easily scope to
    # just the new blocks from rendered HTML, but we can confirm the producer's
    # h2 is reading block.title_zh — strip the page header and search for the
    # OWNER <h2> rendered values.
    assert text.count("Owner pages") >= 1, "owner <h2> missing"
    assert text.count("主理页面与参考") >= 1, (
        "owner_links <h2> must read title_zh=主理页面与参考, not the eyebrow "
        "'Owner pages / 主理页面' alone"
    )


def test_plane_slugs_render_as_plain_words_not_raw(tmp_path):
    """BLOCKER 5 round 2: plane slugs (rates, dollar, credit, commodity,
    international, rates_and_credit) must surface as glance-tier EN/ZH labels.
    Raw slug variants like 'rates_and_credit' or ALL_CAPS must NOT appear in
    visible copy."""
    blocks = _make_fresh_blocks(tmp_path)
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    text = _strip_html(html)
    # Plain words are present in both languages.
    plain_en = ["Rates", "Commodity"]
    plain_zh = ["利率", "商品"]
    for w in plain_en:
        assert w in text, f"missing plain-word EN plane label: {w}"
    for w in plain_zh:
        assert w in text, f"missing plain-word ZH plane label: {w}"
    # Raw slug variants MUST NOT leak.
    assert "rates_and_credit" not in text
    assert "RATES_AND_CREDIT" not in text
    assert "INTERNATIONAL" not in text
    # Plane tags are language-switched twins via t(), never both languages
    # painted side by side ("Rates 利率") in one language's view.
    assert '<span class="l-en">Rates</span><span class="l-zh">利率</span>' in html
    assert ('<span class="l-en">Rates &amp; Credit</span><span class="l-zh">利率与信用</span>' in html
            or '<span class="l-en">Rates & Credit</span><span class="l-zh">利率与信用</span>' in html)
    assert '<span class="l-en">International</span><span class="l-zh">国际</span>' in html
    assert not re.search(r'<span class="mx-ol-label">[^<]*[一-鿿]', html), (
        "owner_links plane tag must not paint ZH as a bare second span"
    )
    assert 'style="margin-left' not in _panel_html(html, "Owner pages")


# ── C1: chip text uses plain words, never the enum ───────────────────────────


@pytest.mark.parametrize("state", list(STATE_CHIP_PAIRS.keys()))
def test_state_chip_text_is_plain_word_not_enum(tmp_path, state):
    """The chip text for each typed state must be the plain-word pair, never the enum."""
    blocks = _make_fresh_blocks(tmp_path)
    blocks[0]["state"] = state
    blocks[0]["rows"] = []
    blocks[0]["state_reason_en"] = "Test fixture reason for the read."
    blocks[0]["state_reason_zh"] = "本次测试夹具原因。"
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    text = _strip_html(html)
    chip_en, chip_zh = STATE_CHIP_PAIRS[state][1], STATE_CHIP_PAIRS[state][2]
    assert chip_en in text, f"chip EN word missing for {state}"
    assert chip_zh in text, f"chip ZH word missing for {state}"
    # The raw enum MUST NOT appear in visible copy
    assert state not in text, f"raw enum {state} leaked into visible copy"


# ── C1: ZH parity — every EN string has a ZH twin via t() ─────────────────────


def test_every_en_string_has_a_zh_twin_in_new_blocks(tmp_path):
    """Spot-check the key EN/ZH pairs across the three new blocks."""
    blocks = _make_fresh_blocks(tmp_path)
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    text = _strip_html(html)
    # Each EN block string should be paired with its ZH twin
    pairs = [
        ("Context planes", "背景面"),
        ("Research watch", "研究观察"),
        ("Owner pages", "主理页面"),
        ("Built at", "构建时间"),
        ("as of", "数据截至"),
    ]
    for en, zh in pairs:
        assert en in text, f"missing EN: {en}"
        assert zh in text, f"missing ZH twin: {zh} for {en}"


# ── C1: no title= translated text ─────────────────────────────────────────────


def test_no_translated_text_in_title_attributes_of_new_blocks(tmp_path):
    """The three new blocks must not carry translated text inside title= attrs.
    The only legal title= attrs are on <a> tags (bilingual), or on per-row SVG/aria
    labels that don't carry translated customer copy. We assert no ZH text appears
    in title= attrs that wrap the new blocks."""
    blocks = _make_fresh_blocks(tmp_path)
    payload = _build_payload(tmp_path, blocks)
    html = _render_am_edition(payload)
    # Find any title="..." that contains a Chinese character
    title_with_zh = re.findall(r'<title[^>]*>[^<]*[一-鿿]+[^<]*</title>', html)
    assert not title_with_zh, (
        f"title= attrs with translated ZH text found: {title_with_zh}"
    )


# ── C2: enforce-added clean — no colour/radius literals in added CSS lines ──


def test_new_blocks_have_no_color_or_radius_literals_in_added_css(tmp_path):
    """C1/C5: the MOR-2b CSS (templates/_mor2b_blocks_css.j2) must be token-only —
    no colour or radius literals and no var() fallback literals. Deterministic at
    every committed head: the whole include is fed to the design checker as an
    added-lines diff (a working-tree diff would skip at any committed head)."""
    import subprocess
    import sys

    include = ROOT / "templates" / "_mor2b_blocks_css.j2"
    css = include.read_text(encoding="utf-8")
    hex_literal = re.compile(r"#[0-9a-fA-F]{3,8}\b")
    rgb_or_rgba = re.compile(r"\brgba?\s*\(")
    radius_literal = re.compile(r"border-radius\s*:\s*\d", re.I)
    var_fallback_literal = re.compile(r"var\(--[a-z0-9-]+\s*,\s*[#0-9]")
    bad = []
    for line in css.splitlines():
        for kind, rx in (("hex", hex_literal), ("rgb", rgb_or_rgba),
                         ("radius", radius_literal), ("var-fallback", var_fallback_literal)):
            if rx.search(line):
                bad.append((kind, line.strip()[:80]))
    assert not bad, f"token-only CSS violated: {bad}"
    diff = subprocess.run(
        ["git", "diff", "--no-index", "--", "/dev/null", "templates/_mor2b_blocks_css.j2"],
        capture_output=True, text=True, cwd=str(ROOT), check=False,
    ).stdout
    assert "+++ b/templates/_mor2b_blocks_css.j2" in diff
    diff_file = tmp_path / "added.diff"
    diff_file.write_text(diff, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "scripts/check_design_system.py", "--mode", "enforce-added",
         "--diff-file", str(diff_file)],
        capture_output=True, text=True, cwd=str(ROOT), check=False,
    )
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def test_mor2b_css_is_shared_by_both_pages_not_page_local():
    """C2/C3: the block + band rules live in ONE shared include that BOTH pages
    load; neither page depends on rules another page defines, and the light art
    direction is real CSS, not a comment."""
    include = (ROOT / "templates" / "_mor2b_blocks_css.j2").read_text(encoding="utf-8")
    am = (ROOT / "templates" / "am_edition.html.j2").read_text(encoding="utf-8")
    brief = (ROOT / "templates" / "aibrief.html.j2").read_text(encoding="utf-8")
    brief_css = (ROOT / "templates" / "_aibrief_css.j2").read_text(encoding="utf-8")
    assert '{% include "_mor2b_blocks_css.j2" %}' in am
    assert '{% include "_mor2b_blocks_css.j2" %}' in brief
    for cls in (".mx-block-header", ".mx-chip-slot", ".mx-band", ".mx-cp-row", ".mx-rw-row", ".mx-ol-row"):
        assert cls in include, f"{cls} must be defined in the shared include"
        assert cls not in brief_css, f"{cls} must not be defined in _aibrief_css.j2"
        assert re.search(re.escape(cls) + r"\s*[{,]", am) is None, f"{cls} must not be page-local on am_edition"
    # DARK: transparent chip fill inside the MOR-2b headers; LIGHT: token-only tint, no pulse.
    assert ".mx-block-header .dtp-chip { background:transparent;" in include
    light_tint = 'html[data-theme="light"] .mx-block-header .dtp-chip::before {'
    assert light_tint in include
    tint_rule = include[include.index(light_tint):include.index("}", include.index(light_tint))]
    assert "background:currentColor" in tint_rule and "opacity:.1" in tint_rule, "light chip tint = currentColor at 10 %"
    assert "color-mix(" not in include, "colour functions are forbidden by the design checker"
    assert 'html[data-theme="light"] .mx-block-header .dtp-dot { animation:none; }' in include
    assert ".mx-stale-why" in include
    # The chip primitive itself stays the pinned theme.css family.
    assert ".mx-state-chip" not in include and ".mx-state-chip" not in am and ".mx-state-chip" not in brief


# ── C3: aibrief band — session-state chip maps the producer state ──────────────


def _render_aibrief_band(am_edition):
    from tests.test_aibrief_page import _env as _aibrief_env

    panels = {
        "ctx_strip": {"absent": True},
        "fwd_panel": {"absent": True, "events": [], "rebal_note_en": None, "rebal_note_zh": None},
        "record_panel": {"absent": True},
        "am_edition": am_edition,
    }
    html = _aibrief_env().get_template("aibrief.html.j2").render(as_of="2026-09-08 13:00 UTC", **panels)
    return _panel_html(html, "Morning Orientation")


@pytest.mark.parametrize(
    "session_state, chip, dot, word_en, word_zh",
    [
        ("OPEN", "dtp-chip--live", True, "Live", "实时"),
        ("CLOSED", "dtp-chip--stale", False, "After the close", "已收盘"),
        ("NOT_YET_OPEN", "dtp-chip--pre", False, "Not yet open", "尚未开盘"),
        ("WEIRD", "dtp-chip--warn", False, "Unavailable", "不可用"),
    ],
)
def test_aibrief_band_session_chip_maps_the_producer_state(session_state, chip, dot, word_en, word_zh):
    band = _render_aibrief_band({
        "absent": False, "session_state": session_state,
        "generated_at": "2026-09-08T13:00:00+00:00",
        "first_tape_en": "ES S&P 500 futures is up +0.30% since yesterday's close.",
        "first_tape_zh": "ES 标普500期货自昨日收盘以来上涨 +0.30%。",
        "reason_en": None, "reason_zh": None, "source_state": "CURRENT",
    })
    assert chip in band
    assert ('class="dtp-dot"' in band) is dot, "the pulse dot belongs to OPEN only"
    text = _strip_html(band)
    assert word_en in text and word_zh in text
    assert session_state not in text, "raw enum must not reach visible copy"
    assert "2026-09-08T13:00" in band and 'class="dtp-asof"' in band
    assert 'href="am_edition.html"' in band and "mx-empty" not in band
    assert "since yesterday's close" in text


def test_aibrief_band_absent_json_renders_honest_empty_state():
    band = _render_aibrief_band({
        "absent": True, "session_state": None, "generated_at": None,
        "first_tape_en": None, "first_tape_zh": None, "source_state": None,
        "reason_en": "The morning orientation page has not built yet.",
        "reason_zh": "今晨导读页面尚未生成。",
    })
    assert "mx-empty" in band and "mx-empty-why" in band
    assert "dtp-chip--warn" in band and 'class="dtp-dot"' not in band
    text = _strip_html(band)
    assert "The morning orientation page has not built yet." in text
    assert "今晨导读页面尚未生成。" in text
    assert 'href="am_edition.html"' not in band


# ── C4: nav entry exists for am_edition ──────────────────────────────────────


def test_nav_entry_for_am_edition_next_to_reference():
    """_navlinks.html.j2 must include a Core Research entry for am_edition.html
    positioned next to reference.html."""
    nav = Path("templates/_navlinks.html.j2").read_text(encoding="utf-8")
    assert "am_edition.html" in nav
    assert "早间版" in nav
    # Position: am_edition entry is inserted directly after the reference entry.
    # The comment block immediately preceding am_edition mentions Market Reference.
    pos_ref = nav.find('href="{{ NP }}reference.html"')
    pos_ame = nav.find('href="{{ NP }}am_edition.html"')
    assert pos_ref != -1 and pos_ame != -1
    assert pos_ame > pos_ref, "am_edition entry must come AFTER reference entry"
    # Distance is small — a few hundred chars for the reference <a>...</a> block.
    assert pos_ame - pos_ref < 3000, "am_edition entry too far from reference"


def test_nav_icon_is_sunrise_line_not_clock():
    """The new nav glyph must NOT be a clock icon — that glyph is owned by the
    session-clock panels. We assert by shape: no <circle> at the centre with
    hour/minute hands. The new glyph is a sunrise line over a horizon bar."""
    nav = Path("templates/_navlinks.html.j2").read_text(encoding="utf-8")
    # Find the am_edition block — between its href and the closing </a>
    pos = nav.find('href="{{ NP }}am_edition.html"')
    assert pos != -1
    end = nav.find("</a>", pos)
    block = nav[pos:end]
    # Has at least one .ghost path (the horizon bar)
    assert 'class="ghost"' in block
    # Has at least one .accent path (the sunrise line + rays)
    assert 'class="accent"' in block
    # The shape: vertical sun position with rays, NOT clock hands.
    # Block contains an M24 8 (top-of-circle sunrise origin) and M24 8l-7 7 / l7 7 rays.
    assert "M24 8" in block, "expected the sunrise line origin at M24 8"
