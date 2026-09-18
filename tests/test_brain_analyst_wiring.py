"""Gateway wiring for the Market Analyst doctrine (Analyst OS P0).

What this suite pins (mirrors tests/test_brain_doctrine.py's wiring half):
  1. _analyst_block_for rides on EVERY page (message-routed, page-free) — the
     protocol reaches dashboard chat, not just the Terminal.
  2. The lane dial: fast → tight-sequence paragraph, pro/research → deeper-pass
     paragraph, unknown → block without a dial. The dial never replaces the block.
  3. Leak screen: the analyst banner + module openers are in _LEAK_SENTINELS.
  4. Source order in BOTH loops: technician doctrine → analyst block → language
     directive (the LANGUAGE line must stay last; recency is load-bearing).
  5. Never raises: a broken analyst library degrades to "" — the turn survives.
"""
from __future__ import annotations

import inspect

from engine.neuralweb import analyst_doctrine
from engine.neuralweb import brain_gateway as gw


# ── 1. Every page: block is message-routed, not page-gated ──────────────────

def test_analyst_block_rides_off_terminal():
    block = gw._analyst_block_for("why is TLT down while yields rise today", "fast")
    assert "MARKET ANALYST DOCTRINE" in block
    assert "THE ANALYST PROTOCOL" in block


def test_analyst_block_present_even_for_stable_questions():
    # The protocol is always-on (its freshness law TELLS the model educational
    # questions need no live retrieval — that guidance must be present to act).
    block = gw._analyst_block_for("what is duration?", "fast")
    assert "THE ANALYST PROTOCOL" in block
    # ...but a calm question must not drag in the stress-day playbook.
    assert "STRESS-DAY PLAYBOOK" not in block


# ── 2. Lane dial ─────────────────────────────────────────────────────────────

def test_fast_lane_gets_the_discipline_dial():
    block = gw._analyst_block_for("why is the market down today", "fast")
    assert "DISCIPLINE FOR THIS TURN" in block
    assert "DEPTH FOR THIS TURN" not in block


def test_pro_lane_gets_the_depth_dial():
    block = gw._analyst_block_for("why is the market down today", "pro")
    assert "DEPTH FOR THIS TURN" in block
    assert "DISCIPLINE FOR THIS TURN" not in block


def test_unknown_lane_keeps_the_block_drops_the_dial():
    block = gw._analyst_block_for("why is the market down today", "")
    assert "THE ANALYST PROTOCOL" in block
    assert "FOR THIS TURN" not in block


# ── 3. Leak screen carries the analyst sentinels ─────────────────────────────

def test_leak_sentinels_include_analyst_doctrine():
    for s in analyst_doctrine.LEAK_SENTINELS:
        assert s in gw._LEAK_SENTINELS, f"analyst sentinel missing from leak screen: {s!r}"


# ── 4. Source order in both loops: doctrine → analyst → language ────────────

def _assert_order(src: str) -> None:
    i_doc = src.index("_doctrine_block_for(safe_page, message)")
    i_ana = src.index("_analyst_block_for(message, lane)")
    i_lang = src.index("_language_directive(turn_lang)")
    assert i_doc < i_ana < i_lang


def test_loop_order_nonstream():
    _assert_order(inspect.getsource(gw._run_brain_loop))


def test_loop_order_stream():
    _assert_order(inspect.getsource(gw._run_brain_loop_stream))


# ── 5. Never raises ──────────────────────────────────────────────────────────

def test_analyst_block_degrades_to_empty_on_library_error(monkeypatch):
    def _boom(_msg):
        raise RuntimeError("library on fire")

    monkeypatch.setattr(analyst_doctrine, "route", _boom)
    assert gw._analyst_block_for("why is the market down", "fast") == ""


# ── 6. Market-intel tools: allowlist, schemas, dispatch, tier gate ───────────

def _dispatch(tool_name, params, tmp_path, user_id=""):
    return gw._dispatch_brain_tool(
        tool_name, params, tmp_path, tmp_path, "", user_id=user_id)


def test_intel_tools_in_allowlist_and_schemas(tmp_path):
    assert "get_market_events" in gw._BRAIN_TOOLS
    assert "search_research" in gw._BRAIN_TOOLS
    names = {s["name"] for s in gw._all_brain_tool_schemas(tmp_path)}
    assert {"get_market_events", "search_research"} <= names


def test_get_market_events_dispatches_for_everyone(tmp_path):
    # No user_id (guest turn): events are open — an empty world degrades honestly.
    out = _dispatch("get_market_events", {"window_h": 6, "limit": 3}, tmp_path)
    assert isinstance(out, dict) and "events" in out


def test_get_market_events_survives_junk_model_arguments(tmp_path):
    # The model sometimes emits junk argument types; the module's clamps must see
    # them (dispatch passes raw values through instead of raising on float()).
    out = _dispatch("get_market_events",
                    {"window_h": "soon", "limit": "a few"}, tmp_path)
    assert isinstance(out, dict) and "events" in out
    assert "error" not in out


def test_search_research_gate_guest(tmp_path):
    out = _dispatch("search_research", {"query": "oil shock"}, tmp_path, user_id="")
    assert out.get("error") == "essential_required"


def test_search_research_gate_free_tier(tmp_path, monkeypatch):
    monkeypatch.setattr(gw, "_resolve_tier",
                        lambda uid, root=None: {"tier": "free", "status": "active"})
    out = _dispatch("search_research", {"query": "oil shock"}, tmp_path, user_id="u1")
    assert out.get("error") == "essential_required"
    assert out.get("tier") == "free"


def test_search_research_serves_essential_and_pro(tmp_path, monkeypatch):
    import json
    cat_dir = tmp_path / "data" / "research_vault"
    cat_dir.mkdir(parents=True)
    (cat_dir / "catalog.json").write_text(json.dumps({
        "schema": "research_vault.catalog.v1", "count": 1,
        "items": [{"id": "x1", "title": "Oil shock playbook", "institution": "GS",
                   "side": "sell", "published_at": "2026-07-29T00:00:00Z",
                   "summary_points": ["Supply risk repricing"], "tags": [],
                   "tickers": [], "top_pick": False, "pages": 3, "language": "en"}],
    }))
    # 'insider' is the PRE-RENAME spelling a grandfathered entitlement row still carries;
    # the gate normalises it, so both must open the door.
    for tier in ("essential", "insider", "pro"):
        monkeypatch.setattr(gw, "_resolve_tier",
                            lambda uid, root=None, _t=tier: {"tier": _t, "status": "active"})
        out = _dispatch("search_research", {"query": "oil shock"}, tmp_path, user_id="u1")
        assert out.get("results"), f"tier {tier} should get results"
        assert out["results"][0]["title"] == "Oil shock playbook"


# ── 7. Grounding digest threads the turn language into the packet ───────────

def test_grounding_digest_threads_lang(tmp_path, monkeypatch):
    from engine.neuralweb import market_packet as mp
    seen = {}

    def _capture(root, char_budget=4200, lang="en"):
        seen["lang"] = lang
        return "[CURRENT DASHBOARD STATE] stub"

    monkeypatch.setattr(mp, "digest", _capture)
    out = gw._grounding_digest(tmp_path, lang="zh")
    assert seen["lang"] == "zh"
    assert out.startswith("[CURRENT DASHBOARD STATE]")


# ── 8. Analyst OS W2 — depth tools: analogues (gated) + curve detail (open) ──

def test_w2_tools_in_allowlists():
    assert "get_historical_analogues" in gw._BRAIN_TOOLS
    assert "get_curve_detail" in gw._BRAIN_TOOLS
    assert "get_historical_analogues" in gw._BRAIN_ONLY_TOOLS
    assert "get_curve_detail" in gw._BRAIN_ONLY_TOOLS


def test_w2_tools_in_schemas(tmp_path):
    names = {s["name"] for s in gw._all_brain_tool_schemas(tmp_path)}
    assert {"get_historical_analogues", "get_curve_detail"} <= names


def test_w2_tool_labels_bilingual():
    for name in ("get_historical_analogues", "get_curve_detail"):
        en, zh = gw._TOOL_LABELS[name]
        assert en and zh and en != zh


def test_analogues_gate_guest(tmp_path):
    out = _dispatch("get_historical_analogues", {}, tmp_path, user_id="")
    assert out.get("error") == "essential_required"


def test_analogues_gate_free_tier(tmp_path, monkeypatch):
    monkeypatch.setattr(gw, "_resolve_tier",
                        lambda uid, root=None: {"tier": "free", "status": "active"})
    out = _dispatch("get_historical_analogues", {}, tmp_path, user_id="u1")
    assert out.get("error") == "essential_required"
    assert out.get("tier") == "free"


def test_analogues_essential_reaches_module_and_degrades_honestly(tmp_path, monkeypatch):
    # tmp_path has no parquet estate: the gate passes, the module answers with its
    # own honest unavailable error instead of raising or fabricating episodes.
    monkeypatch.setattr(gw, "_resolve_tier",
                        lambda uid, root=None: {"tier": "insider", "status": "active"})
    out = _dispatch("get_historical_analogues", {"limit": 3}, tmp_path, user_id="u1")
    assert isinstance(out, dict)
    assert out.get("error") == "analogues_unavailable"


def test_curve_detail_open_to_guests_and_degrades_honestly(tmp_path):
    out = _dispatch("get_curve_detail", {}, tmp_path, user_id="")
    assert isinstance(out, dict)
    assert out.get("error") == "curve_detail_unavailable"


def test_seed_plan_curve_and_analogue_nudges():
    plan = gw._seed_tool_plan("why is the yield curve steepening today")
    assert "get_curve_detail" in plan
    plan = gw._seed_tool_plan("when did something similar to this happen before")
    assert "get_historical_analogues" in plan
    # zh triggers ride the same tuples
    plan = gw._seed_tool_plan("历史上有类似的情况吗")
    assert "get_historical_analogues" in plan


# ── 9. Analyst OS W3 — per-user memory tools + preference setter ─────────────

def test_w3_tools_in_allowlists():
    for name in ("recall_sessions", "get_trade_episodes", "set_chat_preference"):
        assert name in gw._BRAIN_TOOLS, name
        assert name in gw._BRAIN_ONLY_TOOLS, name
        en, zh = gw._TOOL_LABELS[name]
        assert en and zh and en != zh


def test_w3_tools_in_schemas(tmp_path):
    names = {s["name"] for s in gw._all_brain_tool_schemas(tmp_path)}
    assert {"recall_sessions", "get_trade_episodes", "set_chat_preference"} <= names


def test_recall_sessions_guest_gets_signin_note(tmp_path):
    out = _dispatch("recall_sessions", {}, tmp_path, user_id="")
    assert out.get("available") is False
    assert "sign in" in (out.get("note") or "")


def test_trade_episodes_guest_gets_signin_note(tmp_path):
    out = _dispatch("get_trade_episodes", {}, tmp_path, user_id="")
    assert out.get("available") is False


def test_set_chat_preference_guest_refused(tmp_path):
    out = _dispatch("set_chat_preference", {"depth": "concise"}, tmp_path, user_id="")
    assert out.get("error") == "signin_required"


def test_recall_sessions_signed_in_reaches_module(tmp_path, monkeypatch):
    from engine.neuralweb import brain_user_memory as bum
    monkeypatch.setattr(bum, "_sb_get", lambda path: [])
    bum.clear_cache()
    out = _dispatch("recall_sessions", {"days": 7, "limit": 3}, tmp_path, user_id="u1")
    assert out.get("schema") == "brain.session_recall.v1"
    bum.clear_cache()


# ── 10. Analyst OS W4 — vault full-report escalation gate (operator ruling) ──

def test_report_mode_essential_gets_pro_required(tmp_path, monkeypatch):
    """Operator ruling 2026-07-31: full reports are PRO-only; Essential keeps summaries.

    The resolver is mocked with the PRE-RENAME spelling on purpose — the reported tier
    must come back canonical, proving the gate normalises rather than echoing a raw row.
    """
    monkeypatch.setattr(gw, "_resolve_tier",
                        lambda uid, root=None: {"tier": "insider", "status": "active"})
    out = _dispatch("search_research",
                    {"mode": "report", "report_id": "x1"}, tmp_path, user_id="u1")
    assert out.get("error") == "pro_required"
    assert out.get("tier") == "essential"


def test_report_mode_pro_reaches_module_with_user_ctx(tmp_path, monkeypatch):
    from engine.neuralweb import brain_market_intel as bmi
    seen = {}

    def _capture(root, query="", limit=5, *, mode="search", report_id="",
                 user_ctx=None, now=None):
        seen.update(mode=mode, report_id=report_id, user_ctx=user_ctx)
        return {"schema": "brain.research_report.v1"}

    monkeypatch.setattr(gw, "_resolve_tier",
                        lambda uid, root=None: {"tier": "pro", "status": "active"})
    monkeypatch.setattr(bmi, "search_research", _capture)
    out = _dispatch("search_research",
                    {"mode": "report", "report_id": "gs-1"}, tmp_path, user_id="u7")
    assert out.get("schema") == "brain.research_report.v1"
    assert seen["mode"] == "report" and seen["report_id"] == "gs-1"
    assert seen["user_ctx"] == {"user_id": "u7"}


def test_search_mode_still_serves_essential_with_no_user_ctx(tmp_path, monkeypatch):
    from engine.neuralweb import brain_market_intel as bmi
    seen = {}

    def _capture(root, query="", limit=5, *, mode="search", report_id="",
                 user_ctx=None, now=None):
        seen.update(mode=mode, user_ctx=user_ctx)
        return {"results": []}

    monkeypatch.setattr(gw, "_resolve_tier",
                        lambda uid, root=None: {"tier": "insider", "status": "active"})
    monkeypatch.setattr(bmi, "search_research", _capture)
    out = _dispatch("search_research", {"query": "oil"}, tmp_path, user_id="u1")
    assert "results" in out
    assert seen["mode"] == "search" and seen["user_ctx"] is None


# Event Intelligence: published calendar to the existing Brain packet.
from datetime import datetime, timezone
from pathlib import Path
import json
import pytest

_EIC_NOW = datetime(2026, 9, 18, 12, tzinfo=timezone.utc)


def _eic_row(**changes):
    value = {
        'schema': 'calendar_event_context.v1',
        'method_version': 'reference-playbooks-2026-09-17.1',
        'event_type': 'AUCTION', 'event_date': '2026-09-23',
        'title': {'en': '2-Year FRN auction (reopening)', 'zh': '2年期浮息国债拍卖'},
        'coverage': 'official_terms', 'known_at': None,
        'source_url': 'https://www.treasurydirect.gov/auctions/announcements-data-results/',
        'can_rank': False, 'can_size': False, 'can_trade': False,
        'summary': {'en': 'Do not carry this editorial text as an observed fact'},
        'facts': [
            {'key': 'cusip', 'value': '91282CRD5', 'state': 'source_supplied'},
            {'key': 'offering_amount_usd', 'value': '28000000000', 'state': 'source_supplied'},
            {'key': 'competitive_close_et', 'value': '11:30', 'state': 'source_supplied'},
            {'key': 'announcement_date', 'value': '2026-09-17', 'state': 'source_supplied'},
            {'key': 'issue_date', 'value': '2026-09-25', 'state': 'source_supplied'},
            {'key': 'maturity_date', 'value': '2028-07-31', 'state': 'source_supplied'},
        ],
    }
    value.update(changes)
    return value


def _eic_publish(root, rows, stamp='2026-09-18T10:00:00+00:00', extra=''):
    p = root / 'site/macro.html'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('<!doctype html><meta charset="utf-8"><script id="calendar-event-context-data" '
                 'type="application/json" data-generated-at="' + stamp + '">'
                 + json.dumps(rows, ensure_ascii=False) + '</script>' + extra, encoding='utf-8')
    return p


def _eic_read(root, **kw):
    from engine.neuralweb.calendar_grounding import read_calendar
    return read_calendar(root, now=kw.pop('now', _EIC_NOW), **kw)


def test_eic_missing_projection_is_an_explicit_gap(tmp_path):
    got = _eic_read(tmp_path)
    assert got['state'] == 'unavailable' and got['events'] == []
    assert got['reason'] == 'published_calendar_unavailable'


def test_eic_published_same_day_events_and_terms_reach_machine_context(tmp_path):
    a, b = _eic_row(), _eic_row(title={'en':'5-Year Note auction', 'zh':'5年期国债拍卖'})
    b['facts'][0]['value'] = '91282CRN3'
    _eic_publish(tmp_path, [a, b])
    got = _eic_read(tmp_path)
    assert len(got['events']) == 2
    assert got['events'][0]['facts']['offering_amount_usd'] == '28000000000'
    assert got['events'][0]['facts']['competitive_close_et'] == '11:30'
    assert got['source_observed_at'] is None
    assert got['state'] == 'published_snapshot' and len(got['snapshot_sha256']) == 64
    assert got['may_originate_signal'] is False


@pytest.mark.parametrize('stamp', ['', '2026-09-18', 'nonsense', '2026-09-18T10:00:00'])
def test_eic_unknown_publication_clock_is_not_current(tmp_path, stamp):
    _eic_publish(tmp_path, [_eic_row()], stamp=stamp)
    got = _eic_read(tmp_path)
    assert got['state'] == 'clock_unknown' and got['page_generated_at'] is None
    assert got['events'] and got['source_observed_at'] is None


def test_eic_future_stamp_refuses_even_with_valid_facts(tmp_path):
    _eic_publish(tmp_path, [_eic_row()], stamp='2026-09-19T10:00:00Z')
    got = _eic_read(tmp_path)
    assert got['state'] == 'unavailable' and got['events'] == []
    assert got['reason'] == 'future_publication'


def test_eic_old_snapshot_retains_honest_last_known_terms(tmp_path):
    _eic_publish(tmp_path, [_eic_row()], stamp='2026-09-15T10:00:00Z')
    got = _eic_read(tmp_path)
    assert got['state'] == 'stale_snapshot' and got['events']


def test_eic_reference_and_conflict_never_pass_numeric_terms(tmp_path):
    _eic_publish(tmp_path, [_eic_row(coverage='conflicting_terms'), _eic_row(coverage='reference_only')])
    got = _eic_read(tmp_path)
    assert len(got['events']) == 2
    assert all(x['facts'] == {} for x in got['events'])


@pytest.mark.parametrize('bad', [True, '1e100', '-1', '0', 'NaN', '<b>42</b>', '10,000'])
def test_eic_bad_amount_cannot_become_a_number(tmp_path, bad):
    r = _eic_row(); r['facts'][1]['value'] = bad
    _eic_publish(tmp_path, [r])
    assert 'offering_amount_usd' not in _eic_read(tmp_path)['events'][0]['facts']


@pytest.mark.parametrize('bad', ['25:00', '', None, '11:30<script>', '13:0'])
def test_eic_invalid_time_stays_unavailable(tmp_path, bad):
    r = _eic_row(); r['facts'][2]['value'] = bad
    _eic_publish(tmp_path, [r])
    assert 'competitive_close_et' not in _eic_read(tmp_path)['events'][0]['facts']


def test_eic_whitelist_drops_instructions_private_data_and_effect_claims(tmp_path):
    r = _eic_row(beneficiaries=['NVDA'], confidence=.99, private_portfolio={'secret':1})
    r['facts'].append({'key':'trade_size','value':'500','state':'source_supplied'})
    _eic_publish(tmp_path, [r])
    text = json.dumps(_eic_read(tmp_path))
    for bad in ['NVDA','confidence','private_portfolio','trade_size','editorial text']:
        assert bad not in text


@pytest.mark.parametrize('bad', ['https://www.treasurydirect.gov.evil.test/x',
                                 'https://user@www.treasurydirect.gov/x',
                                 'javascript:alert(1)', 'http://www.bls.gov/x'])
def test_eic_bad_source_urls_cannot_cross_bridge(tmp_path, bad):
    _eic_publish(tmp_path, [_eic_row(source_url=bad)])
    assert _eic_read(tmp_path)['events'][0]['source_url'] is None


def test_eic_invalid_rows_do_not_erase_neighbors(tmp_path):
    _eic_publish(tmp_path, [None, 7, _eic_row(event_date='2026-02-30'), _eic_row(can_trade=True), _eic_row()])
    got = _eic_read(tmp_path)
    assert len(got['events']) == 1 and got['rejected_rows'] == 4


def test_eic_duplicate_payload_fails_closed(tmp_path):
    _eic_publish(tmp_path, [_eic_row()], extra='<script type="application/json" id="calendar-event-context-data">[]</script>')
    assert _eic_read(tmp_path)['reason'] == 'ambiguous_calendar_payload'


def test_eic_no_stale_source_reuse_after_file_disappears(tmp_path):
    p = _eic_publish(tmp_path, [_eic_row()]); assert _eic_read(tmp_path)['events']
    p.unlink(); assert _eic_read(tmp_path)['state'] == 'unavailable'


def test_eic_correction_changes_snapshot_identity(tmp_path):
    r = _eic_row(); _eic_publish(tmp_path, [r]); before = _eic_read(tmp_path)
    r['facts'][1]['value'] = '27000000000'
    _eic_publish(tmp_path, [r]); after = _eic_read(tmp_path)
    assert after['snapshot_sha256'] != before['snapshot_sha256']
    assert after['events'][0]['facts']['offering_amount_usd'] == '27000000000'


def test_eic_no_publication_field_is_relabelled_source_known_at(tmp_path):
    r = _eic_row(known_at='2026-09-18T10:00:00Z')
    _eic_publish(tmp_path, [r]); got = _eic_read(tmp_path)
    assert got['source_observed_at'] is None
    assert all('known_at' not in x for x in got['events'])


def test_eic_selection_is_bounded_and_omissions_are_disclosed(tmp_path):
    _eic_publish(tmp_path, [_eic_row() for _ in range(10)])
    got = _eic_read(tmp_path, limit=4)
    assert len(got['events']) == 4 and got['omitted_rows'] == 6


def test_eic_naive_now_is_explicitly_unsupported(tmp_path):
    _eic_publish(tmp_path, [_eic_row()])
    assert _eic_read(tmp_path, now=_EIC_NOW.replace(tzinfo=None))['reason'] == 'invalid_now'


def test_eic_expired_schedule_is_not_reported_as_upcoming(tmp_path):
    _eic_publish(tmp_path, [_eic_row(event_date='2026-09-17'), _eic_row()])
    got = _eic_read(tmp_path)
    assert len(got['events']) == 1 and got['outside_window_rows'] == 1


def test_eic_page_and_payload_size_are_bounded(tmp_path):
    from engine.neuralweb.calendar_grounding import MAX_PAGE_BYTES, MAX_PAYLOAD_BYTES
    p = _eic_publish(tmp_path, [])
    p.write_bytes(b'x' * (MAX_PAGE_BYTES + 1))
    assert _eic_read(tmp_path)['reason'] == 'page_too_large'
    p.write_text('<script id="calendar-event-context-data" type="application/json">' + ' '* (MAX_PAYLOAD_BYTES+1) + '</script>')
    assert _eic_read(tmp_path)['reason'] == 'payload_too_large'


def test_eic_digest_keeps_limits_and_source_identity(tmp_path):
    from engine.neuralweb.calendar_grounding import render_calendar
    _eic_publish(tmp_path, [_eic_row()])
    got = _eic_read(tmp_path)
    text = render_calendar(got, lang='en')
    assert '11:30' in text and '28,000,000,000' in text
    assert 'not release results' in text and 'observation time unknown' in text
    assert 'treasurydirect.gov' in text and len(text) <= 1800
    assert '浮息' in render_calendar(got, lang='zh')


def test_eic_denied_fact_state_is_not_resurrected(tmp_path):
    r = _eic_row(); r['facts'][1]['state'] = 'conflicting'
    _eic_publish(tmp_path, [r])
    assert 'offering_amount_usd' not in _eic_read(tmp_path)['events'][0]['facts']


def test_eic_duplicate_fact_keys_withhold_that_field(tmp_path):
    r = _eic_row(); r['facts'].append({'key':'offering_amount_usd','value':'100','state':'source_supplied'})
    _eic_publish(tmp_path, [r])
    assert 'offering_amount_usd' not in _eic_read(tmp_path)['events'][0]['facts']


def test_eic_duplicate_script_attributes_cannot_select_a_different_browser_payload(tmp_path):
    p = _eic_publish(tmp_path, [_eic_row()])
    p.write_text(p.read_text().replace('id="calendar-event-context-data"', 'id="other" id="calendar-event-context-data"'))
    assert _eic_read(tmp_path)['state'] == 'unavailable'


def test_eic_oversized_fact_list_cannot_hide_a_late_conflict(tmp_path):
    r = _eic_row(); r['facts'] += [{'key':'unused'+str(i),'value':'x','state':'source_supplied'} for i in range(12)]
    r['facts'].append({'key':'offering_amount_usd','value':'1','state':'source_supplied'})
    _eic_publish(tmp_path, [r])
    assert _eic_read(tmp_path)['events'][0]['facts'] == {}


def test_eic_render_missing_time_is_explicit(tmp_path):
    from engine.neuralweb.calendar_grounding import render_calendar
    r = _eic_row(); r['facts'][2]['value'] = None
    _eic_publish(tmp_path, [r])
    assert 'deadline unavailable' in render_calendar(_eic_read(tmp_path))


def test_eic_too_many_rejected_rows_cannot_look_like_full_coverage(tmp_path):
    from engine.neuralweb.calendar_grounding import render_calendar
    _eic_publish(tmp_path, [None, _eic_row()])
    assert 'Rejected rows: 1' in render_calendar(_eic_read(tmp_path))


def test_eic_calendar_enters_actual_market_packet_and_digest(tmp_path, monkeypatch):
    from engine.neuralweb import market_packet as mp
    monkeypatch.setattr(mp, '_live_dir', lambda root: root / 'site/live')
    _eic_publish(tmp_path, [_eic_row()])
    packet = mp.build_packet(tmp_path, now=_EIC_NOW)
    assert packet['calendar']['events'][0]['facts']['cusip'] == '91282CRD5'
    text = mp.render_digest(packet)
    assert 'CALENDAR REFERENCE' in text and '11:30' in text
    assert 'not release results' in text
    assert 'editorial text' not in text
    assert '浮息' in mp.render_digest(packet, lang='zh')


def test_eic_absent_or_corrupt_calendar_cannot_break_live_tape(tmp_path, monkeypatch):
    from engine.neuralweb import market_packet as mp
    live = tmp_path / 'site/live'; live.mkdir(parents=True)
    monkeypatch.setattr(mp, '_live_dir', lambda _: live)
    (live / 'quotes.json').write_text(json.dumps({'asof': _EIC_NOW.isoformat(), 'quotes': {'SPY': {'price': 500, 'changePct': 1}}}))
    packet = mp.build_packet(tmp_path, now=_EIC_NOW)
    assert 'calendar' not in packet
    assert any(g.startswith('calendar:') for g in packet['gaps'])
    assert 'SPY +1%' in mp.render_digest(packet)
    p = _eic_publish(tmp_path, [_eic_row()]); p.write_text('not a page')
    packet = mp.build_packet(tmp_path, now=_EIC_NOW)
    assert 'calendar' not in packet and 'SPY +1%' in mp.render_digest(packet)


def test_eic_existing_digest_cache_tracks_calendar_appearance_correction_removal(tmp_path, monkeypatch):
    from engine.neuralweb import market_packet as mp
    import os
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return _EIC_NOW if tz else _EIC_NOW.replace(tzinfo=None)
    monkeypatch.setattr(mp, 'datetime', FixedDatetime)
    monkeypatch.setattr(mp, '_live_dir', lambda root: root / 'site/live')
    monkeypatch.setattr(mp, '_clock', lambda: 100.0)
    mp._CACHE.clear()
    try:
        assert 'CALENDAR REFERENCE' not in mp.digest(tmp_path)
        r = _eic_row(); p = _eic_publish(tmp_path, [r]); before = mp.digest(tmp_path)
        assert '28,000,000,000' in before
        r['facts'][1]['value'] = '27000000000'
        old = p.stat().st_mtime
        _eic_publish(tmp_path, [r]); os.utime(p, (old+2, old+2))
        assert '27,000,000,000' in mp.digest(tmp_path)
        assert '28,000,000,000' not in mp.digest(tmp_path)
        p.unlink(); assert 'CALENDAR REFERENCE' not in mp.digest(tmp_path)
    finally:
        mp._CACHE.clear()


def test_eic_actual_fragment_preserves_same_json_and_exposes_only_page_clock(tmp_path):
    from jinja2 import DictLoader, Environment
    from engine.neuralweb.calendar_grounding import read_calendar
    root = Path(__file__).resolve().parents[1]
    source = (root / 'templates/_calendar_event_context.html.j2').read_text()
    env = Environment(loader=DictLoader({'fragment': source, 'calendar_event_context.js': ''}), autoescape=True)
    event = _eic_row()
    html = env.get_template('fragment').render(macro_catalysts=[{'intelligence':event}], generated_utc='2026-09-18 10:00', generated_at_utc='2026-09-18T10:00:00+00:00')
    target = tmp_path / 'site/macro.html'; target.parent.mkdir(parents=True)
    target.write_text(html)
    block = read_calendar(tmp_path, now=_EIC_NOW)
    assert block['state'] == 'published_snapshot'
    assert block['page_generated_at'] == '2026-09-18T10:00:00+00:00'
    assert block['source_observed_at'] is None
    assert block['events'][0]['facts']['cusip'] == event['facts'][0]['value']


def test_eic_crowded_packet_keeps_event_limits_inside_unchanged_budget(tmp_path, monkeypatch):
    from engine.neuralweb import market_packet as mp
    monkeypatch.setattr(mp, '_live_dir', lambda root: root / 'site/live')
    _eic_publish(tmp_path, [_eic_row() for _ in range(8)])
    packet = mp.build_packet(tmp_path, now=_EIC_NOW)
    packet.update({'desk': {'asof': _EIC_NOW.isoformat(), 'reads':[('Read','x'*350)]*4},
                   'watch': {'asof':_EIC_NOW.isoformat(),'lines':[('Watch','y'*300)]*4},
                   'drivers': {'asof':_EIC_NOW.isoformat(),'primary_label':'test input','direction':'up'}})
    text = mp.render_digest(packet)
    assert mp.DEFAULT_CHAR_BUDGET == 4200
    assert len(text) <= 4200
    assert 'CALENDAR REFERENCE' in text and 'Not complete event coverage' in text
    assert 'Events omitted' in text


@pytest.mark.parametrize('wrapper', ['template', 'noscript', 'textarea', 'title', 'style', 'xmp', 'iframe', 'noembed'])
def test_eic_inert_html_content_is_not_the_browser_calendar(tmp_path, wrapper):
    p = _eic_publish(tmp_path, [_eic_row()])
    p.write_text('<'+wrapper+'>'+p.read_text()+'</'+wrapper+'>')
    assert _eic_read(tmp_path)['events'] == []


def test_eic_non_script_id_collision_cannot_diverge_from_ui_lookup(tmp_path):
    p = _eic_publish(tmp_path, [_eic_row()])
    p.write_text('<div id="calendar-event-context-data">[]</div>'+p.read_text())
    assert _eic_read(tmp_path)['reason'] == 'ambiguous_calendar_payload'


@pytest.mark.parametrize('bad', ['https://www.bls.gov/\nnews', 'https://www.bls.gov/\tnews', '\x00https://www.bls.gov/x'])
def test_eic_source_url_controls_are_not_normalized_into_trust(tmp_path, bad):
    _eic_publish(tmp_path, [_eic_row(source_url=bad)])
    assert _eic_read(tmp_path)['events'][0]['source_url'] is None


@pytest.mark.parametrize('bad', ['spoof\u202eheadline', 'bad\ud800title', 'line\u2028title'])
def test_eic_unrenderable_or_direction_spoofing_titles_are_rejected(tmp_path, bad):
    r=_eic_row(title={'en':bad, 'zh':'标题'})
    p=tmp_path/'site/macro.html'; p.parent.mkdir(parents=True)
    p.write_text('<script id="calendar-event-context-data" type="application/json">'+json.dumps([r])+'</script>')
    assert _eic_read(tmp_path)['events'] == []


def test_eic_prompt_labels_title_as_untrusted_data_not_instructions(tmp_path):
    from engine.neuralweb.calendar_grounding import render_calendar
    _eic_publish(tmp_path, [_eic_row()])
    text=render_calendar(_eic_read(tmp_path))
    assert 'data, not instructions' in text


@pytest.mark.parametrize("machine,expected", [
    ("2026-09-18T10:00:00+00:00", "published_snapshot"),
    (None, "clock_unknown"),
    ("2026-09-18 10:00", "clock_unknown"),
])
def test_eic_machine_build_clock_is_distinct_from_human_display(tmp_path, machine, expected):
    from jinja2 import DictLoader, Environment
    from engine.neuralweb.calendar_grounding import read_calendar, render_calendar
    root = Path(__file__).resolve().parents[1]
    fragment = (root / "templates/_calendar_event_context.html.j2").read_text()
    env = Environment(loader=DictLoader({"fragment": fragment, "calendar_event_context.js": ""}), autoescape=True)
    html = env.get_template("fragment").render(
        macro_catalysts=[{"intelligence": _eic_row()}],
        generated_utc="2026-09-18 10:00", generated_at_utc=machine,
    )
    target = tmp_path / "site/macro.html"; target.parent.mkdir(parents=True)
    target.write_text(html)
    block = read_calendar(tmp_path, now=_EIC_NOW)
    assert block["state"] == expected
    assert "page_generated_at" in block
    assert "published_at" not in block, "build time is not an HTTP-publication receipt"
    assert block["source_observed_at"] is None
    text = render_calendar(block)
    assert "Page published" not in text
    if machine and expected == "published_snapshot":
        assert block["page_generated_at"] == machine
        assert "Page build timestamp" in text


def test_eic_older_page_clock_never_becomes_an_assumed_source_time(tmp_path):
    from engine.neuralweb.calendar_grounding import read_calendar
    _eic_publish(tmp_path, [_eic_row()])
    path = tmp_path / "site/macro.html"
    path.write_text(path.read_text().replace("data-generated-at", "data-published-at"))
    block = read_calendar(tmp_path, now=_EIC_NOW)
    assert block["state"] == "clock_unknown"
    assert block["page_generated_at"] is None
    assert block["source_observed_at"] is None
    assert block["events"], "mixed-version publication may retain honest reference facts"


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("lang", ["en", "zh"])
@pytest.mark.parametrize("scenario", ["available", "stale", "conflict", "missing"])
def test_eic_actual_provider_request_preserves_calendar_truth(tmp_path, monkeypatch, stream, lang, scenario):
    """Real gateway loops and packet; only the external model is replaced."""
    from engine.neuralweb import market_packet as mp
    from tests.test_brain_gateway import _MockBlock, _MockClient, _MockResponse, _FakeStreamCtx

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return _EIC_NOW

    monkeypatch.setattr(mp, "datetime", Clock)
    monkeypatch.setattr(mp, "_live_dir", lambda root: root / "site/live")
    monkeypatch.setattr("lib.ai_costs._write_ledger_path", lambda root=None: tmp_path / "costs.jsonl")
    if scenario != "missing":
        row = _eic_row(coverage="conflicting_terms") if scenario == "conflict" else _eic_row()
        stamp = "2026-09-15T10:00:00+00:00" if scenario == "stale" else "2026-09-18T10:00:00+00:00"
        _eic_publish(tmp_path, [row], stamp=stamp)
    answer = "This is a controlled test response, not a live model assessment."
    client = _MockClient([_MockResponse([_MockBlock("text", answer)])])
    if stream:
        def capture(**kwargs):
            client.calls.append(kwargs)
            return _FakeStreamCtx(answer)
        client.stream = capture
    message = "解释这次国债拍卖的现有公告信息。" if lang == "zh" else "Explain the auction announcement information."
    args = (message, "fast", [], {"page": "macro"}, tmp_path, tmp_path, "", client, "fixture-model", 500, 1)
    mp._CACHE.clear()
    try:
        if stream:
            events = list(gw._run_brain_loop_stream(*args, meta_event={}))
            assert events
        else:
            gw._run_brain_loop(*args)
        assert client.calls, "the actual provider request boundary was never reached"
        content = json.dumps(client.calls[0]["messages"][0]["content"], ensure_ascii=False)
        if scenario == "missing":
            assert "91282CRD5" not in content
            assert "CALENDAR REFERENCE" not in content and "日历参考" not in content
        else:
            assert ("日历参考" if lang == "zh" else "CALENDAR REFERENCE") in content
            assert ("来源观测时间未知" if lang == "zh" else "source observation time unknown") in content
            assert ("非发布结果" if lang == "zh" else "not release results") in content
            if scenario == "conflict":
                assert "91282CRD5" not in content and "28000000000" not in content
                assert ("来源冲突" if lang == "zh" else "conflicting source") in content
            else:
                assert "91282CRD5" in content and "11:30" in content
            if scenario == "stale":
                assert ("过期快照" if lang == "zh" else "STALE snapshot") in content
    finally:
        mp._CACHE.clear()
