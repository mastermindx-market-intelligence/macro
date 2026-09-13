"""tests/test_options_command_aib.py — A-F03-W2-2 AD-1 glance-tier lede.

Contract (BINDING): packet A-F03-W2-2 (frozen design spec, ledger row
MO-PAID-010) — the AD-1 Daily Brief panel gets a glance-tier "lede" block
(headline, stance, freshness) promoted above the existing evidence tier.

House rule this suite exists to prove: `build_aib()` stays a PASS-THROUGH
adapter — every lede/freshness string is a closed-vocabulary lookup keyed on
the payload's OWN `board_state` and `len(cards)`, never a score, rank or
generated sentence. Each test builds the REAL context from a fixture payload
and renders the REAL `options.html.j2` template, then asserts on the
rendered HTML — asserting on the dict alone would prove the adapter, not the
surface this packet ships.

Run: python3 -m pytest tests/test_options_command_aib.py -q
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.build_options_command import build_aib, render  # noqa: E402

from tests.test_build_options_command import EMPTY_STORES  # noqa: E402

# Fixed render clock — Friday 2026-09-04, 22:00 UTC (18:00 ET, after the
# close+settle cutoff) -> nyse_calendar.expected_last_session(NOW) ==
# 2026-09-04, so an as_of of that same Friday close is genuinely CURRENT
# (0 sessions behind). A brief carrying the PRIOR session (Thursday
# 2026-09-03) is then correctly "1 trading day behind" — trading-session
# math, not calendar-day math (Major finding, review of PR #6932:
# calendar-day math mislabelled the freshest possible close as "behind",
# and the chip used to say "day" for a session count). No wall-clock read
# anywhere in this file.
NOW = datetime(2026, 9, 4, 22, 0, tzinfo=timezone.utc)


def _brief(*, board_state="OK", board_reason=None, opportunities=None,
           eligible=10, present=20, as_of="2026-09-03", oi_counted="2026-09-03",
           receipt_id="e5bd3f474eabff7904574b8c8abccd1d45f1bb57210eac2d4073e61915ad51",
           built_at_utc="2026-09-06T05:12:44Z") -> dict:
    return {
        "schema": "options.intel_brief/v1", "model_version": "intel_brief_heuristic/v1.2",
        "as_of_session": as_of, "oi_counted_date": oi_counted,
        "pending_session": None,
        "eligibility": {"present": present, "eligible": eligible,
                        "insufficient_history": 0, "insufficient_coverage": 0},
        "board_state": board_state, "board_reason": board_reason,
        "receipt_id": receipt_id,
        "built_at_utc": built_at_utc,
        "opportunities": opportunities or [],
        "opportunities_overflow": 0,
        "event_board": [], "risk_warnings": [], "no_signal_exemplar": None,
    }


def _card(symbol: str, *, direction: str = "LONG", r: int = 1) -> dict:
    return {
        "signal_id": f"adib:v1.2:2026-09-05:{symbol}",
        "symbol": symbol, "canonical_instrument_id": f"US:{symbol}",
        "direction": direction,
        "display_state_en": "Upside evidence", "display_state_zh": "上行证据",
        "horizon": "next_5_sessions",
        "evidence_strength": 0.7, "evidence_confidence": 0.5, "evidence_confidence_band": "moderate",
        "research_priority_score": r,
        "why_now": [{"en": f"why-now for {symbol}", "zh": f"{symbol} 事实"}],
        "evidence": [
            {"name": "Q_oi", "value": 0.7, "history_n": 45, "observed_or_inferred": "inferred"},
            {"name": "Q_skew", "value": 0.5, "history_n": 18, "observed_or_inferred": "inferred"},
        ],
        "contradictions": [],
        "mechanics_context": {"gex_confirm_verdict": None, "gamma_regime": None, "flip_proximity": None},
        "crowding": None,
        "event": None,
        "market_implied_move_pct": 0.03,
        "trigger_watch": {"en": f"trigger {symbol}", "zh": f"{symbol} 触发"},
        "invalidation_watch": {"en": f"invalidation {symbol}", "zh": f"{symbol} 失效"},
        "fresh_until": "2026-09-08",
        "source_state": "ok",
        "prophet_state": "READY",
        "prophet_asof": "2026-09-05",
        "asymmetry_score": None, "asymmetry_state": "UNCALIBRATED",
        "probability_up": None, "probability_down": None, "expected_edge_bps": None,
        "board_rank": r,
    }


def _aib_panel(page: str) -> str:
    start = page.index('<div class="oew-panel oew-aib" id="aib"')
    # The next sibling top-level panel opens with '<div class="oew-panel">'
    end = page.index('<div class="oew-panel">', start)
    return page[start:end]


def _esc(s: str) -> str:
    """The template renders through an autoescape=True Jinja env — a literal
    apostrophe comes back as the numeric entity, exactly like every other
    apostrophe-bearing string already shipped on this page (e.g. the footer's
    "don't chase"). Assertions compare against the escaped form."""
    return s.replace("'", "&#39;")


def _strip_attrs(html: str) -> str:
    """Strip tag attributes so 'user-visible text' assertions never match a
    data-* attribute value (data-aib-state legitimately carries the slug)."""
    return re.sub(r"<([a-zA-Z0-9]+)\s[^>]*>", r"<\1>", html)


# ─────────────────────────────────────────────────────────────────────────────
def test_populated_lede_renders_headline_stance_and_freshness():
    brief = _brief(board_state="OK", as_of="2026-09-03",
                    opportunities=[_card("AAA", r=1), _card("BBB", r=2), _card("CCC", r=3)])
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _aib_panel(page)
    assert _esc("3 names are worth a look after today's close.") in panel
    assert "今日收盘后有 3 个名称值得关注。" in panel
    assert "1 trading day behind" in panel
    assert "落后 1 个交易日" in panel
    lede_start = panel.index('class="oew-aib-lede')
    lede_end = panel.index("</div>", panel.index('class="oew-aib-fresh"'))
    lede = panel[lede_start:lede_end]
    assert 'class="oew-stance st-watch"' in lede


def test_populated_carries_readback_markers():
    brief = _brief(board_state="OK", as_of="2026-09-03",
                    opportunities=[_card("AAA", r=1)])
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _aib_panel(page)
    assert 'data-aib-state="OK"' in panel
    assert 'data-aib-asof="2026-09-03"' in panel
    m = re.search(r'data-aib-receipt="([0-9a-f]{12})"', panel)
    assert m is not None, panel
    assert 'data-aib-fresh="lagging"' in panel


def test_quiet_is_not_degraded():
    brief = _brief(board_state="NO_SIGNAL", opportunities=[])
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _aib_panel(page)
    assert "The options tape is quiet — nothing meets the bar today." in panel
    assert "oew-aib-degraded" not in panel
    assert "oew-aib-elig" in panel


def test_degraded_prints_plain_null_and_hides_eligibility():
    brief = _brief(board_state="STALE_SOURCE", opportunities=[])
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _aib_panel(page)
    assert _esc("Today's brief isn't ready yet.") in panel
    assert "oew-aib-elig" not in panel
    assert "oew-aib-degraded-why" in panel
    stamps_start = panel.index('class="oew-aib-stamps"')
    stamps_end = panel.index("</div>", stamps_start)
    assert "0/" not in panel[stamps_start:stamps_end]


def test_degraded_why_is_true_for_each_board_reason_not_one_hardcoded_line():
    """Major finding, review of PR #6932: templates/options.html.j2 used to
    render ONE hardcoded 'not counted yet' why-sentence under every degraded
    state, contradicting the state-specific headline directly above it on
    ELIGIBILITY_COLLAPSE / MIXED_VINTAGE / NO_SETTLED_OI_PAIR. The why line
    must vary with board_state/board_reason exactly like the headline does,
    and must never assert a counting delay when the true cause differs."""
    cases = [
        ("STALE_SOURCE", None, "the source has not caught up yet"),
        ("DEGRADED", "ELIGIBILITY_COLLAPSE", "too few names cleared today's coverage bar"),
        ("DEGRADED", "MIXED_VINTAGE", "evidence dates on file disagree"),
        ("DEGRADED", "NO_SETTLED_OI_PAIR", "next position count has not settled"),
    ]
    seen = set()
    for board_state, board_reason, must_contain in cases:
        brief = _brief(board_state=board_state, board_reason=board_reason, opportunities=[])
        page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
        panel = _aib_panel(page)
        assert _esc(must_contain) in panel, (board_state, board_reason, panel)
        assert "This is a data gap, not a quiet market" in panel
        why_start = panel.index('class="oew-aib-degraded-why"')
        why_end = panel.index("</p>", why_start)
        why = panel[why_start:why_end]
        seen.add(why)
        if board_state == "STALE_SOURCE":
            # MINOR 3: the why must not repeat the headline's
            # "holding the last good session" clause.
            assert "holding the last good session" not in why
            assert "the source has not caught up yet" in why
    assert len(seen) == len(cases), "each board_reason must render a DISTINCT why sentence"


def test_missing_artifact_why_never_claims_a_counting_delay():
    """The None-artifact path cannot have counted anything — its why must
    not assert 'not counted yet' the way the old hardcoded line did."""
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=None, now=NOW)
    panel = _aib_panel(page)
    assert "This is a data gap, not a quiet market" in panel
    assert "not been counted yet" not in panel
    assert "hasn&#39;t arrived yet" in panel or "hasn't arrived yet" in panel


def test_missing_artifact_renders_unavailable_not_empty():
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=None, now=NOW)
    panel = _aib_panel(page)
    assert _esc("Today's brief isn't ready yet.") in panel
    assert 'data-aib-state="unavailable"' in panel
    assert "oew-aib-grid" not in panel


def test_friday_close_read_on_sunday_is_current_not_behind():
    """Major finding, review of PR #6932: calendar-day math labelled the
    freshest possible board 'behind'. Friday 2026-09-04's close, read on
    Sunday 2026-09-06, must be CURRENT — 0 completed sessions are missing."""
    brief = _brief(board_state="OK", as_of="2026-09-04", opportunities=[_card("AAA")])
    sunday = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)
    out = build_aib(brief, now=sunday)
    assert out["freshness"]["days_behind"] == 0
    assert out["freshness"]["level"] == "current"
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=sunday)
    panel = _aib_panel(page)
    assert "Current" in panel
    assert "最新" in panel
    assert "behind" not in panel


def test_post_labor_day_tuesday_reads_the_newest_close_as_lagging_not_stale():
    """Major finding, review of PR #6932: after Labor Day (Mon 2026-09-07),
    reading Friday 2026-09-04's close on Tuesday 2026-09-08 evening is 4
    CALENDAR days but only 1 completed SESSION behind — 'lagging', never the
    warn-tinted 'stale' level calendar-day math produced on a holiday week."""
    brief = _brief(board_state="OK", as_of="2026-09-04", opportunities=[_card("AAA")])
    tuesday_eve = datetime(2026, 9, 8, 22, 0, tzinfo=timezone.utc)
    out = build_aib(brief, now=tuesday_eve)
    assert out["freshness"]["days_behind"] == 1
    assert out["freshness"]["level"] == "lagging"
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=tuesday_eve)
    panel = _aib_panel(page)
    assert "1 trading day behind" in panel
    assert "1 day behind" not in panel
    assert "lvl-stale" not in panel


def test_unknown_asof_is_not_zero_days():
    brief = _brief(board_state="OK", as_of=None, opportunities=[_card("AAA")])
    out = build_aib(brief, now=NOW)
    assert out["freshness"]["days_behind"] is None
    assert out["freshness"]["level"] == "unknown"
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _aib_panel(page)
    assert "As-of date not recorded" in panel
    assert "Current" not in panel
    assert "最新" not in panel


def test_unparseable_built_at_renders_not_recorded():
    brief = _brief(board_state="OK", opportunities=[_card("AAA")], built_at_utc="garbage")
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)  # must not raise
    panel = _aib_panel(page)
    assert "Update time not recorded" in panel
    assert "未记录更新时间" in panel


def test_no_forbidden_vocabulary_in_brief_section():
    brief = _brief(board_state="STALE_SOURCE", opportunities=[])
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _strip_attrs(_aib_panel(page))
    for banned in ("falsifier", "refuted", "invalidated", "证伪",
                   "board_state", "NO_SIGNAL", "intel_brief_heuristic"):
        assert banned not in panel, banned


def test_every_new_string_is_bilingual_and_no_title_attribute():
    brief = _brief(board_state="OK", as_of="2026-09-03",
                    opportunities=[_card("AAA", r=1), _card("BBB", r=2)])
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _aib_panel(page)
    pairs = [
        (_esc("2 names are worth a look after today's close."), "今日收盘后有 2 个名称值得关注。"),
        ("What to do", "该怎么做"),
        ("Read these first — none is a trade on its own.", "建议优先阅读——均非独立交易信号。"),
        ("As of", "数据截至"),
        ("1 trading day behind", "落后 1 个交易日"),
    ]
    for en, zh in pairs:
        assert en in panel, en
        assert zh in panel, zh
    assert "title=" not in panel


def test_degraded_receipt_prints_plain_word_built_and_truncated_id():
    """MINOR 2: the details receipt must not dump a raw ISO stamp or the
    full hex id — the lede already carries built_en/built_zh, and the
    panel attribute already truncates receipt_id to 12."""
    receipt = "e5bd3f474eabff7904574b8c8abccd1d45f1bb57210eac2d4073e61915ad51"
    brief = _brief(board_state="STALE_SOURCE", opportunities=[], receipt_id=receipt,
                   built_at_utc="2026-09-06T05:12:44Z")
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _aib_panel(page)
    rcp_start = panel.index('class="oew-aib-degraded-rcp"')
    rcp = panel[rcp_start:]
    assert "Updated 6 Sep, 05:12 UTC" in rcp
    assert "更新于 9月6日 05:12 UTC" in rcp
    assert "2026-09-06T05:12:44Z" not in rcp
    assert "e5bd3f474eab" in rcp
    assert receipt not in rcp


def test_unhealthy_board_with_cards_still_prints_degraded_lead():
    """MINOR 4: degraded_en used to be set only when cards were empty, so an
    unhealthy board that still carried cards rendered a blank lead. The
    producer can emit STALE_SOURCE with leftover cards; the lead must still
    be the STALE_SOURCE sentence, not None."""
    brief = _brief(board_state="STALE_SOURCE", opportunities=[_card("AAA")])
    out = build_aib(brief, now=NOW)
    assert out["healthy"] is False
    assert out["cards"], "fixture must carry a card so this is the leftover-card path"
    assert out["degraded_en"] == "Source data is stale — holding the last good session."
    assert out["degraded_zh"] == "数据源过期——保留最近有效交易日。"
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _aib_panel(page)
    lead_start = panel.index('class="oew-aib-degraded-lead"')
    lead_end = panel.index("</p>", lead_start)
    lead = panel[lead_start:lead_end]
    assert "Source data is stale" in lead
    assert "None" not in lead


def test_built_at_non_utc_offset_is_printed_as_utc():
    """MINOR 5: a +08:00 stamp must convert to UTC before the chip says UTC.
    2026-09-06T13:12:44+08:00 is 05:12 UTC, not 13:12 UTC."""
    brief = _brief(board_state="OK", opportunities=[_card("AAA")],
                   built_at_utc="2026-09-06T13:12:44+08:00")
    out = build_aib(brief, now=NOW)
    assert out["freshness"]["built_en"] == "Updated 6 Sep, 05:12 UTC"
    assert out["freshness"]["built_zh"] == "更新于 9月6日 05:12 UTC"
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _aib_panel(page)
    assert "05:12 UTC" in panel
    assert "13:12 UTC" not in panel


def test_built_at_is_the_payload_stamp_not_a_guarded_none():
    """MINOR 7: built_at sits inside the dict-only branch; it is the
    payload's own built_at_utc, never a dead ternary that could yield None
    on a dict that already passed the isinstance gate."""
    brief = _brief(board_state="OK", opportunities=[_card("AAA")],
                   built_at_utc="2026-09-06T05:12:44Z")
    out = build_aib(brief, now=NOW)
    assert out["built_at"] == "2026-09-06T05:12:44Z"


def test_two_sessions_behind_uses_plural_trading_days():
    """MAJOR 1 n-form: two completed sessions is '{d} trading days behind',
    never the calendar-day '2 days behind'."""
    brief = _brief(board_state="OK", as_of="2026-09-02", opportunities=[_card("AAA")])
    # NOW is Friday 2026-09-04 22:00 UTC → expected last session 2026-09-04;
    # as_of Wed 2026-09-02 is two completed sessions behind (Thu + Fri).
    out = build_aib(brief, now=NOW)
    assert out["freshness"]["days_behind"] == 2
    assert out["freshness"]["age_en"] == "2 trading days behind"
    assert out["freshness"]["age_zh"] == "落后 2 个交易日"
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    panel = _aib_panel(page)
    assert "2 trading days behind" in panel
    assert "落后 2 个交易日" in panel
    assert "2 days behind" not in panel


_LEDE_STATES = (
    ("many", _brief(board_state="OK", opportunities=[_card("AAA", r=1), _card("BBB", r=2), _card("CCC", r=3)])),
    ("one", _brief(board_state="OK", opportunities=[_card("AAA", r=1)])),
    ("quiet", _brief(board_state="NO_SIGNAL", opportunities=[])),
    ("degraded", _brief(board_state="STALE_SOURCE", opportunities=[])),
)

_POSTURE_WORDS = (
    "Stand aside", "暂时观望", "Watch — don't chase", "观察—勿追高",
    "Act", "Get ready", "Protect gains", "Ignore",
    "行动", "准备", "保护收益", "忽略",
)


def _lede_block(panel: str) -> str:
    lede_start = panel.index('class="oew-aib-lede')
    lede_end = panel.index("</div>", panel.index('class="oew-aib-fresh"'))
    return panel[lede_start:lede_end]


def _span_lang(block: str, cls: str, lang: str) -> str:
    # Class may carry extras (`oew-stance st-watch`); match the token prefix.
    start = block.index(f'class="{cls}')
    marker = f'class="l-{lang}"'
    inner_start = block.index(marker, start)
    inner = block[inner_start:]
    open_end = inner.index(">") + 1
    close = inner.index("</span>")
    return inner[open_end:close]


def _lede_chip_and_said(panel: str) -> tuple[str, str, str, str]:
    lede = _lede_block(panel)
    chip_cls = "oew-aib-lede-chip" if 'class="oew-aib-lede-chip"' in lede else "oew-stance"
    return (
        _span_lang(lede, chip_cls, "en"),
        _span_lang(lede, "oew-aib-lede-said", "en"),
        _span_lang(lede, chip_cls, "zh"),
        _span_lang(lede, "oew-aib-lede-said", "zh"),
    )


def test_lede_chip_word_is_not_the_stance_sentence():
    """Round-2 MAJOR 1: the quiet lede used to print the doctrine phrase as
    both the chip and the stance sentence. Every lede state must keep those
    two spans distinct."""
    for name, brief in _LEDE_STATES:
        page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
        chip_en, said_en, chip_zh, said_zh = _lede_chip_and_said(_aib_panel(page))
        assert chip_en != said_en, (name, "en", chip_en, said_en)
        assert chip_zh != said_zh, (name, "zh", chip_zh, said_zh)


def test_degraded_emits_no_posture_word():
    """Round-2 MINOR 1 / pinned fix (b): a data outage is not a market
    posture. The degraded chip is a freshness word, never Stand aside."""
    brief = _brief(board_state="STALE_SOURCE", opportunities=[])
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    lede = _lede_block(_aib_panel(page))
    for word in _POSTURE_WORDS:
        assert word not in lede, word
    chip_en, said_en, chip_zh, said_zh = _lede_chip_and_said(_aib_panel(page))
    assert chip_en == "Data behind"
    assert chip_zh == "数据滞后"
    assert said_en == "Not enough fresh data to give a stance."
    assert said_zh == "数据不足，暂不给出立场。"
    assert 'class="oew-aib-lede-chip"' in lede
    assert "oew-stance" not in lede


def test_quiet_chip_is_the_one_word_doctrine():
    brief = _brief(board_state="NO_SIGNAL", opportunities=[])
    page = render(REPO, stores=dict(EMPTY_STORES), intel_brief=brief, now=NOW)
    chip_en, said_en, chip_zh, said_zh = _lede_chip_and_said(_aib_panel(page))
    assert chip_en == "Watch"
    assert chip_zh == "观察"
    assert said_en == _esc("Watch — don't chase.")
    assert said_zh == "观察—勿追高。"


def test_visual_evidence_receipt_covers_four_lede_states_and_stale():
    """Round-2 MAJOR 1/2: the committed receipt must own the template and
    carry many + one + quiet + degraded + the plural is-stale path, each
    × desktop/mobile × en/zh × dark/light. Forty rest cells, no tautology."""
    receipt_path = REPO / "mockups/evidence/pr6932-aib-lede/EVIDENCE.yml"
    if not receipt_path.is_file():
        import pytest
        pytest.skip("sparse checkout omitted mockups")
    receipt = yaml.safe_load(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "mastermind.page_evidence_receipt.v1"
    assert receipt["changed_paths"] == ["templates/options.html.j2"]
    manifest_path = REPO / receipt["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "mastermind.p0_evidence.v2"
    page_ids = {page["page_id"] for page in manifest["pages"]}
    assert page_ids == {
        "pr6932_aib_many.html",
        "pr6932_aib_one.html",
        "pr6932_aib_quiet.html",
        "pr6932_aib_degraded.html",
        "pr6932_aib_stale.html",
    }
    fixtures = REPO / "mockups/evidence/pr6932-aib-lede/fixtures"
    for page_id in page_ids:
        assert (fixtures / page_id).is_file(), page_id
    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert "/Users/" not in manifest_text
    required = {
        (viewport, locale, theme)
        for viewport in ("desktop", "mobile")
        for locale in ("en", "zh")
        for theme in ("dark", "light")
    }
    expected_width = {"desktop": 1440, "mobile": 390}
    for page in manifest["pages"]:
        got = set()
        for state in page["states"]:
            if state.get("force_state") is not None:
                continue
            key = (state["viewport"], state["locale"], state["theme"])
            assert state["captured"] is True, (page["page_id"], key)
            assert state["applied_theme"] == state["theme"], (page["page_id"], key)
            assert state["applied_locale"] == state["locale"], (page["page_id"], key)
            assert state["viewport_width"] == expected_width[state["viewport"]], (
                page["page_id"], key, state.get("viewport_width"),
            )
            png = manifest_path.parent / state["file"]
            assert png.is_file(), (page["page_id"], key, state["file"])
            assert png.stat().st_size > 10_000, (page["page_id"], key, png.stat().st_size)
            got.add(key)
        assert got == required, (page["page_id"], required - got)
    assert sum(len(page["states"]) for page in manifest["pages"]) == 40
