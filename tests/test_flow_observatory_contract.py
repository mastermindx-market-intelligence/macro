"""Flow Observatory V2 W1 — the trust strip, changed-today read, and absolute-vs-relative
truth on flow_velocity.html (research/flow_observatory/W1_SPEC.md).

Written FIRST and failing per the frozen spec's §0 gate. The pure-contract tests (1-3, 6-8,
10, 13-15) exercise ``engine/flow_observatory/{contract,changes}.py`` directly; the
template-integration tests (4, 5, 9, 11, 12) render ``templates/flow_velocity.html.j2``
against fixtures and would fail on the pre-W1 template (no trust strip / quadrant board /
changed-today section) even once the engine math is right — that gap is the whole point:
correct numbers behind an unconflated LABEL is the thing the live page was missing.

The motivating defect (mission brief): the live page showed Autos vel +2.58σ as an
inflow-colored +1.9% while raw 4-week flow was -0.9%, and Southbound "accelerating out"
beside a +¥7.1B absolute figure. The Autos/Southbound fixtures below are the real shapes
measured off the current build (`site/flowdata/desk.json`, 2026-09-02) — not invented
numbers — so the quadrant math is pinned against the actual defect, not a toy case.
"""
from __future__ import annotations

import html as html_lib
import json
import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader

from engine import i18n
from engine.cn_theme_tape import build_cn_theme_tape
from engine.flow_observatory import changes as fo_changes
from engine import flow_velocity as fv
from engine.flow_observatory.contract import (
    QUADRANT_LABELS,
    STATUS_WORD,
    UNKNOWN,
    VOCAB_V2,
    ContractError,
    build_sources,
    build_v2,
    direction_from_value,
    market_read,
    quadrant,
    rel_direction,
    sigma_meaning,
    validate,
)
from scripts.build_vector import C

ROOT = Path(__file__).resolve().parent.parent
TMPL = ROOT / "templates"

# banned-vocabulary list — masterplan §6 language law, exact
BANNED = ["big money", "institutions are buying", "institutional accumulation",
         "smart money", "大资金", "机构买入"]
OLD_VOCAB = ["accelerating in", "inflow cooling", "accelerating out", "outflow easing"]


# ── fixtures: the real Autos/Southbound shapes measured off the live desk ─────────────
def _autos_row(**over):
    row = {"id": "cn_autos", "name": "Autos & NEV Makers", "name_zh": "汽车整车",
          "category": "New Energy & Autos", "n_members": 16,
          "vel": 2.58, "accel": -0.009, "rate_now": 2.9, "rate_4wk": -0.9,
          "rate_norm": -2.8, "rate_rel": 1.9,
          "state": "above norm, cooling", "state_zh": "高于常态·降温",
          "spark": None, "members": [], "inst_attention": 0}
    row.update(over)
    return row


def _gold_row(**over):
    row = {"id": "cn_gold", "name": "Gold Miners", "name_zh": "黄金",
          "category": "Materials", "n_members": 6,
          "vel": 1.1, "accel": 0.02, "rate_now": 1.0, "rate_4wk": 1.2,
          "rate_norm": -0.5, "rate_rel": 1.7,
          "state": "above norm, rising", "state_zh": "高于常态·升温",
          "spark": None, "members": [], "inst_attention": 0}
    row.update(over)
    return row


def _member(**over):
    """A shared-kinetics-map member record (engine.flow_velocity._name_kinetics_map shape)
    — the same dict shape ``ashare_sector_velocity`` puts in a theme row's ``members[]``.
    Ships abs (rate_4wk) and rel (rate_rel) DIFFERENT on purpose (B2): a fixture where they
    happened to be equal could pass a broken template that swapped the two columns."""
    m = {"ticker": "600104.SS", "name": "SAIC Motor", "vel": 2.58, "accel": -0.009,
        "rate_now": 2.9, "rate_4wk": -0.9, "rate_norm": -2.8, "rate_rel": 1.9,
        "state": "above norm, cooling", "state_zh": "高于常态·降温"}
    m.update(over)
    return m


def _snap(**over):
    snap = {
        "as_of": "2026-09-01",
        "aggregate": [
            {"key": "southbound", "label": "Southbound — mainland money into HK",
             "label_zh": "南向 · 内地资金入港", "live": True, "as_of": "2026-09-01",
             "spark": None, "flow_1m_b": 7.1, "pos_days_20": 12,
             "vel": {"1w": -1.0, "1m": -1.52, "3m": -0.8}, "accel": -0.05,
             "vel_primary": -1.52, "primary": "1m",
             "state": "below norm, worsening", "state_zh": "低于常态·加剧"},
            {"key": "northbound", "label": "Northbound — foreign money into A-shares",
             "label_zh": "北向 · 外资入A股", "live": False, "as_of": None,
             "spark": None, "frozen_since": "2024-08-16",
             "note": "Aggregate northbound net disclosure ended 2024-08-16 (Stock Connect "
                     "home-market rule) — historical only, no live velocity.",
             "note_zh": "北向资金净额披露于2024-08-16停止（互联互通本地市场规则）——仅历史，无实时流速。"},
        ],
        "ashare_names": {
            "cadence": "daily", "as_of": "2026-09-01", "n": 10, "n_unscored": 3,
            "primary": "4wk", "note": "note", "note_zh": "note_zh",
            "market_read": market_read(
                [{"vel": 1.0, "rate_4wk": 0.5, "state": "above norm, rising"}] * 10, unscored=3),
            "inflow": [], "outflow": [],
        },
        "ashare_sectors": {
            "cadence": "daily", "as_of": "2026-09-01", "n": 2, "n_unscored": 0,
            "primary": "4wk", "note": "sector note", "note_zh": "板块说明",
            "rows": [_autos_row(), _gold_row()],
        },
        "hk_names": {
            "as_of": "2026-08-31", "n": 400, "n_sized": 380,
            "note": "hk note", "buying": [], "selling": [],
            "depth": 40, "vel_ready": True, "basis": "net-share flow velocity",
            "basis_zh": "净持股流速",
        },
        "seats_by_ticker": {"600104.SS": {"inst_net_yi": 1.2, "n_buy": 3, "n_sell": 1, "dir": "buy"}},
        "seats_as_of": "2026-08-30",
        "sb_vel_primary": -1.52,
        "confluence": None, "momentum": None,
        "pulse": {"breadth": {"names_in": 0, "names_out": 0, "n_names": 0,
                              "sectors_in": 1, "sectors_out": 1, "n_sectors": 2,
                              "tilt": 0, "state": "mixed", "state_zh": "分化"},
                 "dominant_in": None, "dominant_out": None,
                 "sb": {"vel": -1.52, "state": "below norm, worsening", "state_zh": "低于常态·加剧"},
                 "inst": {"agree": 0, "diverge": 0}},
        "note": "Display-only positioning lens — flow is never scored into an allocation signal.",
    }
    snap.update(over)
    return snap


def _v2(log_rows=None, market_session="2026-09-01", **over):
    return build_v2(_snap(**over), log_rows=log_rows or [], market_session=market_session,
                    generated_at="2026-09-01T12:00:00+00:00", seats_as_of="2026-08-30")


def _render(v2, built="test"):
    env = Environment(loader=FileSystemLoader(str(TMPL)), autoescape=True)
    env.globals.update(td=i18n.td, tr=i18n.tr, quadrant_labels=QUADRANT_LABELS,
                       status_word=STATUS_WORD, sigma_meaning=sigma_meaning)
    return env.get_template("flow_velocity.html.j2").render(C=C, snap=v2, built=built)


def _visible_only(html: str) -> str:
    """Strip data-tip-en/zh attribute VALUES so a figure that appears only inside a
    tooltip does not satisfy an "on screen at rest" assertion (spec §2.4/§0.4: abs and
    rel must be visible without hover, mutation check M2)."""
    return re.sub(r'data-tip-(?:en|zh)="[^"]*"', "", html)


# ── 1-3: quadrant axis logic (pure) ────────────────────────────────────────────────
def test_absolute_negative_relative_positive_is_improving_but_still_selling():
    """The Autos defect itself: abs -0.9% (still selling) + rel +2.58σ (pressure easing
    vs its own norm) must NOT collapse into a single inflow-colored number."""
    ad, rd = direction_from_value(-0.9, "pct_rate"), rel_direction(2.58)
    assert (ad, rd) == ("negative", "positive")
    assert quadrant(ad, rd) == "improving_but_still_selling"
    en, zh = QUADRANT_LABELS["improving_but_still_selling"]
    assert en == "still selling, pressure easing"
    assert zh == "仍净流出·压力改善"


def test_absolute_positive_relative_negative_is_weakening_but_still_buying():
    """The Southbound defect: abs +¥7.1B (still bought) + rel -1.52σ (below its own norm,
    fading) — never rendered as a bare "accelerating out"."""
    ad, rd = direction_from_value(7.1, "cny_b"), rel_direction(-1.52)
    assert (ad, rd) == ("positive", "negative")
    assert quadrant(ad, rd) == "weakening_but_still_buying"
    en, zh = QUADRANT_LABELS["weakening_but_still_buying"]
    assert en == "still buying, pace fading"
    assert zh == "仍净流入·动能转弱"


def test_quadrant_insufficient_or_unknown_is_neutral():
    # B1: missing/unknown is a DISTINCT key from the near-norm quiet band.
    assert quadrant("positive", "positive", sufficient=False) == "unknown"
    for bad_abs, bad_rel in [("unknown", "positive"), ("positive", "unknown")]:
        assert quadrant(bad_abs, bad_rel) == "unknown"
    for neu_abs, neu_rel in [("neutral", "positive"), ("positive", "neutral")]:
        assert quadrant(neu_abs, neu_rel) == "neutral_or_unknown"
    # de-minimis bands feed the near-norm quiet verdict, not "no data"
    assert direction_from_value(0.05, "pct_rate") == "neutral"
    assert direction_from_value(0.3, "cny_b") == "neutral"
    assert rel_direction(0.2) == "neutral"
    assert direction_from_value(None, "pct_rate") == "unknown"
    assert rel_direction(None) == "unknown"


# ── 4-5: template integration — the anti-conflation device on screen ──────────────
def test_autos_fixture_cannot_render_unqualified_inflow():
    v2 = _v2()
    autos = next(r for r in v2["ashare_sectors"]["rows"] if r["id"] == "cn_autos")
    assert autos["quadrant"] == "improving_but_still_selling"
    html = _render(v2)
    assert "still selling, pressure easing" in html
    assert "仍净流出·压力改善" in html
    for bad in OLD_VOCAB:
        assert bad not in html, f"old vocabulary {bad!r} leaked into the rendered page"
    for bad in BANNED:
        assert bad not in html, f"banned unqualified vocabulary {bad!r} in the rendered page"
    # gate #2 (§0.2): abs -0.9% AND rel +2.58σ must both be figures at rest, not
    # tooltip-only — the exact "single inflow-colored number" defect the mission cites.
    visible = _visible_only(html)
    assert "0.9" in visible, "the raw abs 4wk figure must be visible at rest"
    # M-c option (i): the vbar σ numeral moved to the tip; the relative rate (%)
    # stays at rest so abs and rel cannot collapse into one inflow-colored number.
    assert "1.9" in visible, "the relative (vs-norm) rate must be visible at rest"


def test_southbound_fixture_keeps_absolute_and_relative_visible():
    v2 = _v2()
    sb = next(c for c in v2["aggregate"] if c["key"] == "southbound")
    assert sb["quadrant"] == "weakening_but_still_buying"
    visible = _visible_only(_render(v2))
    assert "7.1" in visible, "the absolute ¥B figure must be visible at rest, not tooltip-only"
    # scope to the Southbound card itself — the quadrant board's own section header for this
    # SAME enum string is always present, so a whole-page substring search would pass even
    # if the card's own abs×rel chip were dropped (that is the exact M2 failure mode to catch).
    idx = visible.find("Southbound — mainland money into HK")
    assert idx != -1, "southbound card not found"
    card_window = visible[idx:idx + 800]
    assert "still buying, pace fading" in card_window, (
        "the abs×rel quadrant label must be visible at rest ON THE CARD, not tooltip-only — "
        "this is the exact anti-conflation device (spec §2.6/mutation M2)")


# ── 6: market_read denominators / neutral / unscored ───────────────────────────────
def test_market_read_counts_include_neutral_and_unscored():
    rows = [
        {"vel": 1.2, "rate_4wk": 2.0, "state": "above norm, rising"},
        {"vel": -1.2, "rate_4wk": -2.0, "state": "below norm, worsening"},
        {"vel": 0.1, "rate_4wk": 0.02, "state": "near its norm"},   # neutral both axes
        {"vel": None, "rate_4wk": None, "state": "no data"},         # unknown both axes
    ]
    mr = market_read(rows, unscored=5)
    assert mr["absolute_breadth"]["denominator"] == 9
    assert mr["relative_breadth"]["denominator"] == 9
    assert mr["acceleration_breadth"]["denominator"] == 9
    assert mr["absolute_breadth"]["positive"] == 1
    assert mr["absolute_breadth"]["negative"] == 1
    assert mr["absolute_breadth"]["neutral"] == 1
    assert mr["absolute_breadth"]["missing"] == 5 + 1        # unscored + the unknown row
    assert mr["relative_breadth"]["missing"] == 5 + 1
    assert mr["acceleration_breadth"]["strengthening"] == 1
    assert mr["acceleration_breadth"]["worsening"] == 1
    assert mr["acceleration_breadth"]["neutral_or_unknown"] == 5 + 2   # unscored + near-norm + no-data


# ── 7-8: rank/state history vs the previous VALID snapshot only ───────────────────
def test_rank_and_state_changes_compare_previous_valid_snapshot_only():
    """A lane that skipped a session (no line logged for it) must not manufacture a
    transition across the gap it never observed — comparison walks back to the NEWEST
    logged session strictly before today, whatever the calendar gap."""
    log_rows = [
        {"session": "2026-08-28", "written_at": "x", "aggregate": {}, "market_read": {},
         "themes": {"cn_autos": {"quadrant": "true_distribution", "state": "s", "vel": -2.0,
                                 "rank": 5, "abs": -3.0}}},
        # 2026-08-29/30/31 deliberately absent (skipped sessions)
    ]
    v2 = _v2(log_rows=log_rows, market_session="2026-09-01")
    autos = next(r for r in v2["ashare_sectors"]["rows"] if r["id"] == "cn_autos")
    assert autos["prior_state"] == "true_distribution"
    assert autos["state_started"] == "2026-09-01"       # quadrant changed vs 08-28 -> fresh state
    assert autos["state_age_sessions"] == 1
    assert autos["rank_change"] == autos["rank"] - 5


def test_missing_previous_snapshot_yields_null_not_zero():
    """Empty log -> NULL/"first tracked session", never a manufactured zero-change claim
    (missing != zero, §4 law)."""
    v2 = _v2(log_rows=[])
    autos = next(r for r in v2["ashare_sectors"]["rows"] if r["id"] == "cn_autos")
    assert autos["state_started"] is None
    assert autos["state_age_sessions"] is None
    assert autos["prior_state"] is None
    assert autos["state_note"] == "first tracked session"
    assert autos["rank_change"] is None

    cs = fo_changes.compute_changes({"session": "2026-09-01", "themes": {}}, [])
    assert cs["material_change"] is None
    assert cs["previous_valid_session"] is None
    assert cs["reason"] == "no_previous_snapshot"


# ── 9: the quiet "what changed today" state, rendered ───────────────────────────────
def test_no_material_transition_yields_quiet_message():
    log_rows = [
        {"session": "2026-08-31", "written_at": "x", "aggregate": {}, "market_read": {},
         "themes": {"cn_autos": {"quadrant": "improving_but_still_selling", "state": "s",
                                 "vel": 2.5, "rank": 1, "abs": -0.8},
                    "cn_gold": {"quadrant": "true_accumulation", "state": "s",
                               "vel": 1.0, "rank": 2, "abs": 1.0}}},
    ]
    v2 = _v2(log_rows=log_rows, market_session="2026-09-01")
    current_themes = {r["id"]: {"quadrant": r["quadrant"], "state": r.get("state"),
                                "vel": r.get("vel"), "rank": r.get("rank"),
                                "abs": (r.get("abs") or {}).get("value")}
                      for r in v2["ashare_sectors"]["rows"]}
    v2["change_summary"] = fo_changes.compute_changes(
        {"session": "2026-09-01", "themes": current_themes}, log_rows)
    assert v2["change_summary"]["material_change"] is False
    out = _render(v2)
    assert ("No material flow-state transition since the previous valid market session "
            "(2026-08-31)." in out)
    assert "自上一有效交易日（2026-08-31）以来，资金状态无重大变化。" in out


# ── 10: source legs keep distinct dates ────────────────────────────────────────────
def test_source_leg_dates_stay_distinct():
    v2 = _v2()
    sources = build_sources(v2, newest_session="2026-09-01", seats_as_of="2026-08-30")
    by_id = {s["source_id"]: s for s in sources}
    assert by_id["hk_sb_holdings"]["effective_date"] == "2026-08-31"
    assert by_id["cn_large_order_proxy"]["effective_date"] == "2026-09-01"
    assert by_id["lhb_inst_seats"]["effective_date"] == "2026-08-30"
    dates = {s["effective_date"] for s in sources if s["effective_date"]}
    assert len(dates) > 1, "every leg collapsed onto one shared date"
    assert by_id["nb_aggregate"]["status"] == "HISTORICAL_ONLY"
    assert by_id["nb_aggregate"]["effective_date"] != by_id["cn_large_order_proxy"]["effective_date"]


# ── W3: sources[].first_known_at comes from the observations ledger ───────────────
def test_source_first_known_at_bootstrap_null_then_real_from_ledger():
    """W1 shipped ``first_known_at`` permanently ``None`` (no ledger existed yet).
    W3 closes that: omitted/empty ``ledger_rows`` keeps the exact bootstrap null
    (backward-compat — every pre-W3 caller), and a ledger holding the leg's
    ``revision_id==0`` row for its own effective_date surfaces the REAL first-known
    instant (research/flow_observatory/W3_SPEC.md §2)."""
    v2 = _v2()
    bootstrap_sources = build_sources(v2, newest_session="2026-09-01", seats_as_of="2026-08-30")
    by_id = {s["source_id"]: s for s in bootstrap_sources}
    assert by_id["cn_large_order_proxy"]["first_known_at"] is None

    ledger_rows = [{
        "entity_kind": "market", "entity_id": "cn_large_order_proxy",
        "effective_session": "2026-09-01", "revision_id": 0,
        "first_known_at": "2026-09-01T09:00:00+00:00", "revised_at": None,
        "vel": None, "abs_value": None, "quadrant": None, "state": None,
        "rank": None, "coverage_n": 100, "status": "HEALTHY",
    }]
    fed_sources = build_sources(v2, newest_session="2026-09-01", seats_as_of="2026-08-30",
                                ledger_rows=ledger_rows)
    by_id2 = {s["source_id"]: s for s in fed_sources}
    assert by_id2["cn_large_order_proxy"]["first_known_at"] == "2026-09-01T09:00:00+00:00"
    # a DIFFERENT leg (no matching ledger row) stays honestly null, never borrowing
    # cn_large_order_proxy's instant.
    assert by_id2["sb_aggregate"]["first_known_at"] is None


# ── 11: proxy disclosure copy, rendered ────────────────────────────────────────────
def test_order_size_copy_carries_proxy_disclosure():
    out = _render(_v2())
    assert "order-size classification" in out or "order-size proxy" in out
    assert "not identified investors" in out or "非机构身份识别" in out
    for bad in BANNED:
        assert bad not in out, f"banned unqualified vocabulary {bad!r} in the rendered page"


@pytest.mark.needs_full_checkout("data")
def test_real_build_output_carries_v2_vocabulary_and_no_old_vocab_or_banned_terms():
    """Integration proof through the REAL engine (not a synthetic fixture): builds off
    committed `data/`, so this is the test that actually EXERCISES `flow_velocity._classify`
    end to end — the fixture-based tests above pin the CONTRACT logic but hardcode their own
    state strings and would not notice `_classify` itself reverting to the old vocabulary.
    Mutation check M1 (PR body): reverting `_classify` to the pre-W1 strings must fail this
    test (and test_flow_velocity.py's demeaning test) via the real data path.
    """
    from engine.flow_velocity import snapshot as real_snapshot
    snap = real_snapshot()
    if not snap or not (snap.get("ashare_sectors") or {}).get("rows"):
        pytest.skip("committed China flow data unavailable in this checkout")
    v2 = build_v2(snap, log_rows=[], market_session=snap.get("as_of"),
                 generated_at="2026-09-01T12:00:00+00:00", seats_as_of=snap.get("seats_as_of"))
    out = _render(v2)
    for bad in OLD_VOCAB:
        assert bad not in out, (
            f"old vocabulary {bad!r} reached the REAL rendered page — _classify has reverted "
            "or a consumer is bypassing the v2 vocabulary")
    for bad in BANNED:
        assert bad not in out, f"banned unqualified vocabulary {bad!r} in the real rendered page"


# ── 12: EN/ZH parity for every new label ───────────────────────────────────────────
def test_en_zh_parity_for_new_labels():
    out = _render(_v2())
    pairs = [
        ("still selling, pressure easing", "仍净流出·压力改善"),
        ("still buying, pace fading", "仍净流入·动能转弱"),
        ("real inflow, above norm", "真实流入·高于常态"),
        ("real outflow, below norm", "真实流出·低于常态"),
    ]
    for en, zh in pairs:
        assert en in out, f"EN label {en!r} missing"
        assert zh in out, f"ZH twin {zh!r} missing for EN label {en!r}"


# ── 13: state_log idempotence ──────────────────────────────────────────────────────
def test_state_log_append_is_idempotent_per_session(tmp_path):
    data_root = tmp_path
    e1 = {"themes": {"cn_autos": {"quadrant": "true_accumulation", "state": "s", "vel": 1.0,
                                  "rank": 1, "abs": 1.0}}, "aggregate": {}, "market_read": {}}
    r1 = fo_changes.append_state_log("2026-09-01", e1, data_root, require_lane=False)
    assert r1["written"] and r1["rows"] == 1

    other_day = {"themes": {"cn_autos": {"quadrant": "true_accumulation", "state": "s",
                                         "vel": 0.9, "rank": 2, "abs": 0.8}},
                "aggregate": {}, "market_read": {}}
    fo_changes.append_state_log("2026-08-31", other_day, data_root, require_lane=False)
    before = fo_changes.state_log_path(data_root).read_text()

    e1b = {"themes": {"cn_autos": {"quadrant": "true_distribution", "state": "s2", "vel": -2.0,
                                   "rank": 5, "abs": -3.0}}, "aggregate": {}, "market_read": {}}
    r2 = fo_changes.append_state_log("2026-09-01", e1b, data_root, require_lane=False)
    assert r2["written"] and r2["rows"] == 2, "re-running the SAME session must replace, not duplicate"

    rows = fo_changes.read_state_log(data_root)
    assert len(rows) == 2
    sept1 = next(r for r in rows if r["session"] == "2026-09-01")
    assert sept1["themes"]["cn_autos"]["quadrant"] == "true_distribution"
    aug31 = next(r for r in rows if r["session"] == "2026-08-31")
    assert aug31["themes"]["cn_autos"]["rank"] == 2, "an untouched session's line must stay byte-stable"
    after_text = fo_changes.state_log_path(data_root).read_text()
    before_line = next(l for l in before.splitlines() if '"2026-08-31"' in l)
    assert before_line in after_text.splitlines()


def test_state_log_advance_is_lane_gated(tmp_path, monkeypatch):
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)
    monkeypatch.delenv("CN_LANE", raising=False)
    e1 = {"themes": {}, "aggregate": {}, "market_read": {}}
    r = fo_changes.append_state_log("2026-09-01", e1, tmp_path)   # require_lane defaults True
    assert r["written"] is False and r["reason"] == "off_ledger_lane"
    assert not fo_changes.state_log_path(tmp_path).exists()


# ── 14: additive keys don't break the known consumer (cn_theme_tape) ──────────────
def test_added_top_level_keys_do_not_break_known_consumers():
    v2 = _v2()
    membership = {"baskets": {"cn_autos": {
        "name": "Autos & NEV Makers", "name_zh": "汽车整车", "etf_proxy": None,
        "members": [{"ticker": "600104.SS", "name_zh": "上汽集团"}],
    }}}
    import pandas as pd
    cycles = pd.DataFrame([{"date": "2026-09-01", "id": "b-cn_autos", "kind": "basket",
                           "phase": "Recovery", "osc_slope": 4.0, "pos": 10.0}])
    candidates = pd.DataFrame([{"stamp_date": "2026-09-01", "ticker": "600104.SS",
                               "lane": "featured", "entry_status": "partial",
                               "gate_reason": None}])
    import datetime as _dt
    tape = build_cn_theme_tape(membership=membership, cycles=cycles, candidates=candidates,
                               flow=v2, today=_dt.date(2026, 9, 1))
    assert tape is not None
    row = next(r for r in tape["rows"] if r["key"] == "cn_autos")
    assert row["flow_en"] == "above norm, cooling"
    assert row["flow_zh"] == "高于常态·降温"


# ── 15: validate() catches a quadrant/axis mismatch ────────────────────────────────
def test_validate_rejects_quadrant_axis_mismatch():
    v2 = _v2()
    v2["ashare_sectors"]["rows"][0]["quadrant"] = "true_distribution"   # was improving_but_still_selling
    with pytest.raises(ContractError):
        validate(v2)


def test_validate_passes_a_consistent_payload():
    validate(_v2())   # must not raise


# ── M1/W4 repair: validate() extended to cover official_sectors rows (quadrant/axis
#    consistency + the coverage_state enum) — previously entirely unchecked, since
#    contract.py was not touched in the W4 landing. ─────────────────────────────────
def _official_row(**over):
    from engine.flow_observatory.contract import enrich_group
    row = dict(enrich_group(1.0, 1.1), id="801780", name="Banks", name_zh="银行",
              group_kind="official_sector", overlap_allowed=False,
              membership_as_of="current", n_members=42, n_covered=38, coverage_pct=90.5,
              coverage_state="ok", excluded=[], vel=1.1, accel=0.02, rate_now=1.0,
              rate_4wk=1.0, rate_norm=0.0, rate_rel=1.1, state="above norm, rising",
              state_zh="高于常态·升温", spark=None, concentration=None, members=[],
              rank=1, rank_change=None)
    row.update(over)
    return row


def test_validate_passes_a_consistent_official_sectors_payload():
    v2 = _v2()
    v2["official_sectors"] = {"available": True, "seed_date": "2026-09-03", "n": 1,
                              "rows": [_official_row()]}
    validate(v2)   # must not raise


def test_validate_rejects_an_official_sectors_quadrant_axis_mismatch():
    v2 = _v2()
    bad = _official_row(quadrant="true_distribution")   # abs/rel both positive -> mismatch
    v2["official_sectors"] = {"available": True, "seed_date": "2026-09-03", "n": 1, "rows": [bad]}
    with pytest.raises(ContractError):
        validate(v2)


def test_validate_rejects_an_unknown_coverage_state():
    v2 = _v2()
    bad = _official_row(coverage_state="mostly_ok")   # not in the enum
    v2["official_sectors"] = {"available": True, "seed_date": "2026-09-03", "n": 1, "rows": [bad]}
    with pytest.raises(ContractError):
        validate(v2)


def test_validate_rejects_an_unknown_coverage_state_on_a_curated_theme_row_too():
    """The coverage_state enum check is shared by BOTH lenses (M1 — minimal, but not
    official_sectors-only where the field is equally real on ashare_sectors rows)."""
    v2 = _v2()
    v2["ashare_sectors"]["rows"][0]["coverage_state"] = "mostly_ok"
    with pytest.raises(ContractError):
        validate(v2)


def test_validate_ignores_an_unavailable_official_sectors_lens():
    v2 = _v2()
    v2["official_sectors"] = {"available": False, "reason": "no_membership_data"}
    validate(v2)   # must not raise — an unavailable lens carries no rows to check


def test_validate_rejects_a_missing_denominator():
    v2 = _v2()
    del v2["market_read"]["themes"]["absolute_breadth"]["denominator"]
    with pytest.raises(ContractError):
        validate(v2)


# ══════════════════════════════════════════════════════════════════════════════════════
# W1 repair round — independent-review findings (research/flow_observatory/W1_SPEC.md
# repair commission). B1/B2/B3 = FAIL findings; S4-S9/NIT12 = should-fix findings.
# ══════════════════════════════════════════════════════════════════════════════════════

# ── B1: the t() macro must never be called inside an HTML attribute value ─────────────
def test_no_attribute_breakout_leak_from_the_t_macro():
    """The committed site previously shipped `aria-label="<span class="l-en">Data
    sources</span>..."` — the t() macro's span markup broke out of the attribute value
    and leaked the literal text `Data sources">` onto the page. Every attribute value in
    the rendered page must be free of the t() macro's own markup."""
    html = _render(_v2())
    assert 'Data sources">' not in html, "the aria-label attribute-breakout leak reproduced"
    # a fully general guard: no attribute value anywhere may contain the t() macro's own
    # inner markup — that would mean a t() call landed inside an attribute again.
    assert re.search(r'="[^"]*<span class="l-en"', html) is None, (
        "a t() call landed inside an HTML attribute value (breaks out of the quote)")


# ── B2: member drill-down rows must align column-for-column with the sectortbl header ──
_TD_RE = re.compile(r"<td([^>]*)>(.*?)</td>", re.S)
_TH_RE = re.compile(r"<th([^>]*)>(.*?)</th>", re.S)
_TR_RE = re.compile(r'<tr\b[^>]*>.*?</tr>', re.S)
_COLSPAN_RE = re.compile(r'colspan="(\d+)"')


def _sectortbl_html(html: str) -> str:
    m = re.search(r'<table class="board" id="sectortbl">.*?</table>', html, re.S)
    assert m, "sectortbl not found in rendered page"
    return m.group(0)


def _row_colspan_total(row_html: str, cell_re) -> int:
    total = 0
    for attrs, _inner in cell_re.findall(row_html):
        cs = _COLSPAN_RE.search(attrs)
        total += int(cs.group(1)) if cs else 1
    return total


def test_sectortbl_row_td_counts_match_the_header_th_count():
    """Every body row's <td> colspans must sum to the same total as the header's <th>
    colspans — the structural check for B2's defect (memberrow shipped 5 <td> against an
    8-column header, so a member's numbers silently shifted under the wrong headers)."""
    member = _member()
    v2 = _v2()
    v2["ashare_sectors"]["rows"][0] = dict(v2["ashare_sectors"]["rows"][0], members=[member])
    table_html = _sectortbl_html(_render(v2))
    rows = _TR_RE.findall(table_html)
    assert rows, "no <tr> parsed from sectortbl"
    header_total = _row_colspan_total(rows[0], _TH_RE)
    assert header_total == 8, f"header itself unexpectedly has {header_total} columns"
    body_rows = rows[1:]
    assert body_rows, "no body rows parsed"
    mismatches = [(i, _row_colspan_total(r, _TD_RE)) for i, r in enumerate(body_rows)
                 if _row_colspan_total(r, _TD_RE) != header_total]
    assert not mismatches, (
        f"{len(mismatches)} row(s) have a <td> colspan total != the header's {header_total}: "
        f"{mismatches}")


def test_member_row_shows_raw_abs_under_abs_header_never_the_relative_figure():
    """The Autos defect, relocated: a member's RELATIVE rate_rel used to land under the
    'abs 4wk' header. abs 4wk must show the member's own RAW rate_4wk; 'vs norm' must show
    rate_rel; the two must never collide (they differ in this fixture on purpose)."""
    member = _member(rate_4wk=-0.9, rate_rel=1.9)
    v2 = _v2()
    v2["ashare_sectors"]["rows"][0] = dict(v2["ashare_sectors"]["rows"][0], members=[member])
    table_html = _sectortbl_html(_render(v2))
    row_html = next(r for r in _TR_RE.findall(table_html) if member["ticker"] in r)
    cells = [(int(m.group(1)) if (m := _COLSPAN_RE.search(attrs)) else 1, inner)
            for attrs, inner in _TD_RE.findall(row_html)]
    assert sum(c for c, _ in cells) == 8
    assert len(cells) == 6, f"expected 6 <td> elements (name, seat, abs, rel, vel, dash-3), got {len(cells)}"
    name_cell, seat_cell, abs_cell, rel_cell, vel_cell, tail_cell = cells
    assert name_cell[0] == 1 and seat_cell[0] == 1
    assert "SAIC Motor" in name_cell[1]
    assert "🏛" in seat_cell[1], "seat badge must render in its own cell"
    assert abs_cell[0] == 1 and rel_cell[0] == 1 and vel_cell[0] == 1
    # scope to the VISIBLE figure in each cell — the rel cell's own LENS tooltip legitimately
    # quotes the raw rate_4wk as its receipt ("...ran -0.9% of turnover...") without that
    # being the abs/rel conflation this test guards against (spec §2.4: tooltip receipts are
    # allowed to name both numbers; only the AT-REST figure must not collide).
    abs_visible, rel_visible = _visible_only(abs_cell[1]), _visible_only(rel_cell[1])
    assert "-0.9%" in abs_visible, "abs 4wk cell must show the member's raw rate_4wk at rest"
    assert "+1.9%" not in abs_visible, "the relative figure must never appear in the abs cell at rest"
    assert "+1.9%" in rel_visible, "vs norm cell must show rate_rel at rest"
    assert "-0.9%" not in rel_visible, "the raw abs figure must never appear in the vs-norm cell at rest"
    assert "above norm, cooling" in vel_cell[1], "velocity cell must carry the state word"
    assert tail_cell[0] == 3, "the Quadrant/rank-Δ/trend columns collapse to one colspan-3 dash"


def test_member_row_abs_cell_is_an_em_dash_when_the_member_has_no_scored_rate():
    """A member too short-lived to score gets an em-dash in the abs cell, never a bare
    relative figure and never a fabricated zero. Mirrors the real _rate_read() shape: when
    a series is too short/empty ALL four rate fields come back None together (never just
    rate_4wk alone), so that is the realistic fixture."""
    member = _member(rate_4wk=None, rate_norm=None, rate_rel=None, rate_now=None)
    v2 = _v2()
    v2["ashare_sectors"]["rows"][0] = dict(v2["ashare_sectors"]["rows"][0], members=[member])
    table_html = _sectortbl_html(_render(v2))
    row_html = next(r for r in _TR_RE.findall(table_html) if member["ticker"] in r)
    cells = [(int(m.group(1)) if (m := _COLSPAN_RE.search(attrs)) else 1, inner)
            for attrs, inner in _TD_RE.findall(row_html)]
    abs_cell = cells[2][1]   # name(0), seat(1), abs 4wk(2)
    assert "—" in abs_cell, "a missing member rate must render an em-dash"


# ── B3: market_read.themes must count the REAL unscored themes, not a hardcoded 0 ─────
def test_market_read_themes_denominator_includes_real_unscored_themes():
    """contract.build_v2 used to hardcode unscored=0 for the theme lens while
    flow_velocity.ashare_sector_velocity already computed the real drop count in
    ashare_sectors.n_unscored (themes with <3 members or an unscoreable kinetics read) —
    silently dropping them from the denominator, the exact missing-!=-zero gap the
    contract law exists to close."""
    snap = _snap()
    snap["ashare_sectors"] = {**snap["ashare_sectors"], "n_unscored": 4}
    v2 = build_v2(snap, log_rows=[], market_session="2026-09-01",
                 generated_at="2026-09-01T12:00:00+00:00", seats_as_of="2026-08-30")
    themes_mr = v2["market_read"]["themes"]
    n_scored = len(v2["ashare_sectors"]["rows"])
    assert themes_mr["absolute_breadth"]["missing"] >= 4
    assert themes_mr["absolute_breadth"]["denominator"] == n_scored + 4
    assert themes_mr["relative_breadth"]["denominator"] == n_scored + 4
    assert themes_mr["relative_breadth"]["missing"] >= 4


# ── S4(a): hero thesis pinned all-net-seller sentence when absolute-positive is zero ───
def test_hero_thesis_uses_the_pinned_all_net_seller_sentence_when_absolute_positive_is_zero():
    snap = _snap()
    rows = [_autos_row(rate_4wk=-0.9, vel=1.9, rate_rel=1.9),
           _gold_row(rate_4wk=-1.2, vel=1.7, rate_rel=1.7)]   # both abs negative -> abspos=0
    snap["ashare_sectors"] = {**snap["ashare_sectors"], "rows": rows}
    v2 = build_v2(snap, log_rows=[], market_session="2026-09-01",
                 generated_at="2026-09-01T12:00:00+00:00", seats_as_of="2026-08-30")
    mrt = v2["market_read"]["themes"]
    assert mrt["absolute_breadth"]["positive"] == 0
    n = mrt["relative_breadth"]["denominator"]
    html = _render(v2)
    assert (f"Main-force flow was a net seller in all {n} themes — normal for this "
            "order-size proxy; the signal is pressure vs norm.") in html
    assert f"主力资金在全部{n}个主题均为净卖出——该口径的常态；关键信号是相对常态的压力。" in html
    # the >0 sentence must NOT also be present
    assert "saw positive absolute 4-week flow" not in html.split('id="sources"')[0]


def test_hero_thesis_keeps_the_original_sentence_when_absolute_positive_is_nonzero():
    v2 = _v2()   # default fixture: Autos abs<0, Gold abs>0 -> abspos == 1
    mrt = v2["market_read"]["themes"]
    assert mrt["absolute_breadth"]["positive"] > 0
    html = _render(v2)
    assert "saw positive absolute 4-week flow" in html
    assert "Main-force flow was a net seller in all" not in html


# ── S4(b): designed quiet empty states in the quadrant board + LENS tip on its h2 ─────
def test_quadrant_empty_cells_use_designed_quiet_copy_not_bare_none():
    snap = _snap()
    rows = [_autos_row(rate_4wk=-0.9, vel=1.9, rate_rel=1.9),      # -> improving_but_still_selling
           _gold_row(rate_4wk=-1.2, vel=-1.7, rate_rel=-1.7)]      # -> true_distribution
    snap["ashare_sectors"] = {**snap["ashare_sectors"], "rows": rows}
    v2 = build_v2(snap, log_rows=[], market_session="2026-09-01",
                 generated_at="2026-09-01T12:00:00+00:00", seats_as_of="2026-08-30")
    html = _render(v2)
    # true_accumulation and weakening_but_still_buying are both empty in this fixture
    assert "none — rare for this proxy; exceptional when a theme appears here" in html
    assert "无——该口径下罕见，出现即为异常信号" in html
    assert "none today" not in html
    assert "今日无" not in html
    assert "structurally a net seller" in html, "quadrant h2 must carry a LENS tip explaining emptiness"


# ── S5: the relative-breadth line must reach its own stated denominator on screen ─────
def test_relative_breadth_line_shows_its_missing_term_and_reaches_the_denominator():
    snap = _snap()
    snap["ashare_sectors"] = {**snap["ashare_sectors"], "n_unscored": 3}
    v2 = build_v2(snap, log_rows=[], market_session="2026-09-01",
                 generated_at="2026-09-01T12:00:00+00:00", seats_as_of="2026-08-30")
    rb = v2["market_read"]["themes"]["relative_breadth"]
    assert rb["missing"] >= 3
    assert rb["positive"] + rb["neutral"] + rb["negative"] + rb["missing"] == rb["denominator"]
    html = _render(v2)
    assert f"— {rb['missing']} unscored" in html
    assert f"— {rb['missing']}个未评分" in html


# ── S6: validate() must reject a build instant substituted for a leg's effective_date ──
def test_validate_rejects_a_build_instant_substituted_for_a_leg_date():
    """The OLD check compared generated_at (always a full ISO instant, e.g.
    "2026-09-01T12:00:00+00:00") byte-for-byte against effective_date (always a plain
    10-char YYYY-MM-DD panel date) — two values that can never be equal by construction,
    so the check was dead code no mutation could ever reach. This mutation (a leg's
    effective_date literally replaced by the build instant) must be caught."""
    v2 = _v2()
    v2["sources"][0]["effective_date"] = v2["generated_at"]
    with pytest.raises(ContractError):
        validate(v2)


def test_validate_still_passes_a_legitimate_same_day_t0_leg():
    """Guard against over-correcting S6: a T+0 leg whose panel date legitimately equals
    today's calendar date (a real, common case — asia-close runs shortly after CN close)
    must NOT be rejected. Only a build-INSTANT shape (has a time component) is rejected."""
    v2 = _v2()
    v2["generated_at"] = "2026-09-01T07:30:00+00:00"    # same UTC calendar day as the legs
    validate(v2)   # must not raise


# ── S7: sources[] always emits all five W1 legs, even with a panel outage ─────────────
def test_sources_always_emit_all_five_legs_even_when_a_panel_is_absent():
    v2 = _v2()
    v2["aggregate"] = [c for c in v2["aggregate"] if c.get("key") != "southbound"]   # sb=None
    sources = build_sources(v2, newest_session="2026-09-01", seats_as_of="2026-08-30")
    assert len(sources) == 5
    by_id = {s["source_id"]: s for s in sources}
    assert set(by_id) == {"cn_large_order_proxy", "sb_aggregate", "hk_sb_holdings",
                          "nb_aggregate", "lhb_inst_seats"}
    sb = by_id["sb_aggregate"]
    assert sb["effective_date"] is None
    assert sb["ui_state"] == "unavailable"
    assert sb["state_word_en"] == "unavailable" and sb["state_word_zh"] == "不可用"
    assert sb["coverage"]["n_observed"] is None
    # the page still renders cleanly with a panel outage, chip date shows an em-dash
    v2["sources"] = sources
    html = _render(v2)
    assert "unavailable" in html or "不可用" in html


def test_hero_vital_shows_a_true_denominator_of_current_legs_out_of_five():
    v2 = _v2()
    present = sum(1 for s in v2["sources"] if s["ui_state"] == "current")
    html = _render(v2)
    assert re.search(rf'<span class="tnum">{present}</span> of 5 legs current', html)
    assert re.search(rf'5条数据源·<span class="tnum">{present}</span>条最新', html)


# ── S9: bare "institutions"/bare "机构" must never appear in at-rest copy ─────────────
def test_at_rest_copy_never_uses_bare_institutions_or_bare_jigou():
    """S9: 'N inst'/'N机构' at rest is qualified to 'N inst seats'/'N机构席位' — extend the
    BANNED at-rest list with a bare word-boundary check. data-tip attribute contents stay
    exempt (LENS receipts are allowed more latitude than glance-tier copy). Scoped to the
    flow_velocity page's OWN content — the shared `_site_nav` include is a separate,
    out-of-scope governed component (nav bar copy is not this program's vocabulary law)."""
    v2 = _v2()
    v2["ashare_sectors"]["rows"][0] = dict(v2["ashare_sectors"]["rows"][0], inst_attention=3)
    html = _render(v2)
    page_html = html.split('<div class="wrap">', 1)[1]
    visible = _visible_only(page_html)
    assert not re.search(r"\binstitutions\b", visible, re.I), (
        "bare word-boundary 'institutions' leaked into at-rest copy")
    bad = [m.group(0) for m in re.finditer(r"机构(?!席位|专用)", visible)]
    assert not bad, f"bare '机构' (not qualified by 席位/专用) at rest: {bad}"
    assert "3 inst seats" in visible or "机构席位" in visible


# ── NIT12: board abs column colors by direction (neutral -> muted), not raw sign ──────
def test_theme_abs_column_colors_by_direction_not_raw_sign():
    """A value like -0.04% sits inside the 0.1pp de-minimis neutral band (direction=
    'neutral') but rounds for display to '-0.0%' — the raw-sign coloring used to print
    that in outflow-red ink, contradicting the quadrant's own neutral read of the same
    figure. Must be muted ('neu'), not 'neg'."""
    snap = _snap()
    rows = [_autos_row(rate_4wk=-0.04, vel=0.2, rate_rel=0.1),   # abs+rel both neutral
           _gold_row()]
    snap["ashare_sectors"] = {**snap["ashare_sectors"], "rows": rows}
    v2 = build_v2(snap, log_rows=[], market_session="2026-09-01",
                 generated_at="2026-09-01T12:00:00+00:00", seats_as_of="2026-08-30")
    autos = next(r for r in v2["ashare_sectors"]["rows"] if r["id"] == "cn_autos")
    assert autos["abs"]["direction"] == "neutral"
    table_html = _sectortbl_html(_render(v2))
    row_html = next(r for r in _TR_RE.findall(table_html) if "cn_autos" in r or "Autos" in r)
    assert 'class="chg neu"' in row_html, "a neutral-direction abs value must use the muted 'neu' class"
    assert 'class="chg neg"' not in row_html, "a neutral-direction abs value must never render as 'neg'"


# ── B1 structural kill (W6 review round) ───────────────────────────────────────────────
# This program has now shipped FOUR waves (W2, W3, W4, W5 — see the "Wired ..." comments
# stacked in .github/ci/legacy-jobs.yml immediately above its flow lane run: line) that
# each landed a brand-new tests/test_flow_observatory_*.py suite with no job naming it
# anywhere in CI, so the suite's own tests never actually ran despite being present and
# green-looking in the PR's own local run. W6 (tests/test_flow_observatory_workflow.py)
# was the FIFTH instance, caught only by independent review after merge. Every prior fix
# was a one-off edit to the run: line; none of them closed the CLASS. This test does: it
# reads the run: line directly off disk and fails the NEXT time a suite ships unwired,
# in the same PR, before merge — the fourth-plus recurrence a mere code-review comment
# evidently cannot prevent.
def test_all_flow_observatory_suites_are_wired_into_the_ci_lane():
    legacy_src = (ROOT / ".github" / "ci" / "legacy-jobs.yml").read_text(encoding="utf-8")
    # Matched structurally (the pytest invocation naming test_flow_velocity.py, the
    # oldest suite this lane has always carried) rather than by line number — line
    # numbers drift on every unrelated ci edit, exactly the kind of edit this lane sees
    # constantly.
    m = re.search(r"run:\s*python -m pytest ([^\n]*\btests/test_flow_velocity\.py\b[^\n]*)\n", legacy_src)
    assert m, ('the flow-velocity measure guards run: line (naming tests/test_flow_velocity.py) '
              'was not found in .github/ci/legacy-jobs.yml — this test can no longer locate the '
              'lane it is supposed to guard; update the regex above if the lane was legitimately '
              'restructured, but do not simply delete this test')
    run_line = m.group(1)
    wired = set(re.findall(r"tests/test_flow_observatory_\w+\.py", run_line))
    on_disk = {f"tests/{p.name}" for p in (ROOT / "tests").glob("test_flow_observatory_*.py")}
    missing = on_disk - wired
    assert not missing, (
        f"{sorted(missing)} exist under tests/ but are NOT named on the flow-velocity "
        "measure guards' run: line in .github/ci/legacy-jobs.yml — a new "
        "tests/test_flow_observatory_*.py suite ships DARK (present, looks green locally, "
        "NEVER actually executed by CI) until it is added to that run: line. This is the "
        "SAME defect that shipped unwired in W2, W3, W4, W5, and W6 (5 waves in a row) — "
        "add the new file to the run: command in .github/ci/legacy-jobs.yml (and its "
        "matching path-gate entry in .github/workflows/ci.yml) in this SAME commit before "
        "this test will pass.")


# ── W13 heal (B1, B2, M-b, M-c option i, M-d, M-e, M-f, M-i, M-j) ─────────────────────
_THEME_CATEGORIES = [
    "Financials & Value",
    "Cyclicals & Resources",
    "Technology & AI",
    "New Energy & Autos",
    "Consumer & Brands",
    "Advanced Manufacturing",
]
_LATIN3_NO_CJK = re.compile(r"[A-Za-z]{3,}")
_CJK = re.compile(r"[\u4e00-\u9fff]")


def _theme(i, **over):
    row = _autos_row(id=f"cn_t{i:02d}", name=f"Theme {i:02d}", name_zh=f"主题{i:02d}",
                     category=_THEME_CATEGORIES[i % 6],
                     vel=0.1, rate_4wk=0.02, rate_rel=0.0, accel=0.0,
                     state="near its norm", state_zh="接近常态")
    row.update(over)
    return row


def _official(i, **over):
    row = {
        "id": f"sw_{i:03d}", "name": f"Sector {i:02d}", "name_zh": f"行业{i:02d}",
        "n_members": 10, "n_covered": 10, "coverage_pct": 100.0,
        "coverage_state": "ok", "vel": 0.2, "rate_4wk": -0.5, "members": [],
        "state": "near its norm", "state_zh": "接近常态",
        "quadrant": "neutral_or_unknown",
        "quadrant_en": "quiet — near its norm", "quadrant_zh": "平静·接近常态",
    }
    row.update(over)
    return row


def _table(html, table_id):
    m = re.search(rf'<table class="board" id="{table_id}">(.*?)</table>', html, re.S)
    assert m, f"#{table_id} missing"
    return m.group(1)


def _sector_row_classes(block):
    return re.findall(r'<tr class="(sector-row[^"]*)"', block)


def test_w13_b1_near_norm_and_unknown_are_unfusable_both_lanes():
    """B1: quiet-near-norm and genuinely-unknown use distinct keys AND distinct copy;
    'insufficient coverage' never shares a label with near-norm; no chip/row/summary
    says 'insufficient data' while its tip says near-norm. Both lanes."""
    assert QUADRANT_LABELS["neutral_or_unknown"] == ("quiet — near its norm", "平静·接近常态")
    assert QUADRANT_LABELS["unknown"] == ("no data", "无数据")
    assert QUADRANT_LABELS["neutral_or_unknown"] != QUADRANT_LABELS["unknown"]
    assert quadrant("neutral", "neutral") == "neutral_or_unknown"
    assert quadrant("unknown", "positive") == UNKNOWN
    assert quadrant("positive", "positive", sufficient=False) == UNKNOWN

    near = _theme(0, vel=0.1, rate_4wk=0.02)
    missing = _theme(1, vel=None, rate_4wk=None, rate_rel=None, state="no data",
                     state_zh="无数据")
    insuff = _official(1, coverage_state="insufficient_coverage", n_covered=1,
                       n_members=20, coverage_pct=5.0, vel=None, rate_4wk=None,
                       state="insufficient coverage", state_zh="覆盖不足")
    v2 = _v2(ashare_sectors={"cadence": "daily", "as_of": "2026-09-01", "n": 2,
                             "n_unscored": 0, "primary": "4wk",
                             "note": "n", "note_zh": "n",
                             "rows": [near, missing]},
             official_sectors={"available": True, "rows": [insuff],
                               "seed_date": "2026-01-01", "n": 1})
    rows = {r["id"]: r for r in v2["ashare_sectors"]["rows"]}
    assert rows["cn_t00"]["quadrant"] == "neutral_or_unknown"
    assert rows["cn_t00"]["quadrant_en"] == "quiet — near its norm"
    assert rows["cn_t00"]["quadrant_zh"] == "平静·接近常态"
    assert rows["cn_t01"]["quadrant"] == "unknown"
    assert rows["cn_t01"]["quadrant_en"] == "no data"
    assert rows["cn_t01"]["quadrant_zh"] == "无数据"

    html = _render(v2)
    assert "quiet / insufficient data" not in html
    assert "平静 / 数据不足" not in html
    assert "quiet — near its norm" in html
    assert "平静·接近常态" in html
    assert ">no data<" in html.replace(" ", "") or "no data" in html
    assert "无数据" in html
    assert "insufficient coverage" in html
    assert "覆盖不足" in html
    # no rendered host says "insufficient data" while its own tip says near-norm
    for m in re.finditer(r"<[^>]+data-tip-en=\"([^\"]*)\"[^>]*>([^<]*)<", html):
        tip, text = m.group(1), m.group(2)
        if "near its norm" in tip.lower() or "near-norm" in tip.lower():
            assert "insufficient data" not in text.lower(), (
                f"B1 fuse: visible {text!r} with near-norm tip {tip!r}")
    for m in re.finditer(r'class="qchip[^"]*"[^>]*>.*?</span>', html, re.S):
        chip = m.group(0)
        if "insufficient coverage" in chip or "覆盖不足" in chip:
            assert "quiet — near its norm" not in chip
            assert "平静·接近常态" not in chip


def test_w13_b2_hero_summary_rowcount_agree_with_quality_and_revision():
    """B2: hero integer == summary integer == li.fv-chg-row count when the render
    contains ≥1 quality transition and ≥1 source revision."""
    transitions = [{"id": f"cn_t{i:02d}", "from_quadrant": "true_distribution",
                    "to_quadrant": "improving_but_still_selling"} for i in range(3)]
    rank_movers = [{"id": f"cn_t{i:02d}", "from_rank": 10, "to_rank": 4} for i in range(3, 6)]
    quality = [{"kind": "quality", "id": "cn_large_order_proxy",
                "from_status": "HEALTHY", "to_status": "STALE"}]
    revisions = [{"kind": "revision", "id": "southbound", "entity_kind": "market",
                  "effective_session": "2026-09-01",
                  "from": {"quadrant": "weakening_but_still_buying"},
                  "to": {"quadrant": "weakening_but_still_buying", "vel": -1.5}}]
    extra = [{"id": f"cn_t{i:02d}", "from_quadrant": "true_accumulation",
              "to_quadrant": "weakening_but_still_buying"} for i in range(6, 8)]
    all_n = len(transitions) + len(rank_movers) + len(quality) + len(revisions) + len(extra)
    assert all_n > 8
    v2 = _v2(ashare_sectors={"cadence": "daily", "as_of": "2026-09-01", "n": 8,
                             "n_unscored": 0, "primary": "4wk", "note": "n", "note_zh": "n",
                             "rows": [_theme(i) for i in range(8)]})
    v2["change_summary"] = {
        "material_change": True, "previous_valid_session": "2026-08-31",
        "transitions": transitions + extra, "rank_movers": rank_movers,
        "quality_transitions": quality, "source_revisions": revisions,
    }
    html = _render(v2)
    hero = re.search(
        r'data-goto-sec="changed"[\s\S]*?<span class="tnum">(\d+)</span>', html)
    assert hero, "hero changed-today count missing"
    summary = re.search(r"all (\d+) changes", html)
    assert summary, "collapsed 'all N changes' summary missing (need N>8)"
    rows = len(re.findall(r'class="fv-chg-row', html))
    assert int(hero.group(1)) == int(summary.group(1)) == rows == all_n
    assert "kind" in str(quality[0]) and "cn_large_order_proxy" in html
    assert "data revised" in html or "数据已修正" in html


def test_w13_mb_theme_categories_render_cjk_in_zh_lane():
    """M-b: all six theme categories render CJK in the l-zh lane; the
    ≥3-Latin-letters-no-CJK scan over .cat l-zh spans is 0."""
    rows = [_theme(i, category=_THEME_CATEGORIES[i]) for i in range(6)]
    v2 = _v2(ashare_sectors={"cadence": "daily", "as_of": "2026-09-01", "n": 6,
                             "n_unscored": 0, "primary": "4wk", "note": "n", "note_zh": "n",
                             "rows": rows})
    html = _render(v2)
    cats = re.findall(r'<span class="cat">(.*?)</span>', html, re.S)
    assert len(cats) >= 6, f"expected 6 category chips, got {len(cats)}"
    bad = []
    for block in cats:
        for zh in re.findall(r'<span class="l-zh">(.*?)</span>', block, re.S):
            text = re.sub(r"<[^>]+>", "", zh)
            if _LATIN3_NO_CJK.search(text) and not _CJK.search(text):
                bad.append(text)
    assert bad == [], f"l-zh category spans with ≥3 Latin letters and no CJK: {bad}"
    for en in _THEME_CATEGORIES:
        assert en.replace("&", "&amp;") in html or en in html


def test_w13_mc_sigma_demoted_to_tipped_meaning_sentence_both_lanes():
    """M-c option (i): no vbar-sig at rest; every valued vbar tip carries σ WITH
    a meaning sentence in both lanes; never a bare σ beside a .vstate word.
    Tips live on the dedicated .lens-q host (not the vbar itself)."""
    v2 = _v2()
    html = _render(v2)
    assert 'class="vbar-sig"' not in html
    vis = _visible_only(html)
    assert re.search(r"class=\"vbar[^\"]*\"[^>]*>[^<]*σ", vis) is None
    tips_en = re.findall(r'class="lens-q"[^>]*data-tip-en="([^"]+)"', html)
    tips_zh = re.findall(r'class="lens-q"[^>]*data-tip-zh="([^"]+)"', html)
    pace_en = [t for t in tips_en if "σ" in t and "normal pace" in t]
    pace_zh = [t for t in tips_zh if "σ" in t and ("自身常态" in t or "罕见" in t)]
    assert pace_en, "valued vbars must carry an EN meaning-sentence tip on .lens-q"
    assert pace_zh, "valued vbars must carry a ZH meaning-sentence tip on .lens-q"
    for tip in pace_en:
        assert "—" in tip or "-" in tip
    # no .vstate host whose own text contains σ
    for block in re.findall(r'<span class="vstate[^"]*">.*?</span>', html, re.S):
        visible = re.sub(r"<[^>]+>", "", block)
        assert "σ" not in visible


def test_w13_md_theme_and_official_boards_cap_at_eight_with_count_true_control():
    """M-d: 8 rows at rest + counted See all N (N == expanding population) + collapse
    copy + sort-reset; N==8 boundary renders a plain count and no control."""
    nine = [_theme(i, vel=1.0 + i * 0.1, rate_4wk=-0.9) for i in range(9)]
    nine_off = [_official(i) for i in range(9)]
    v2 = _v2(ashare_sectors={"cadence": "daily", "as_of": "2026-09-01", "n": 9,
                             "n_unscored": 0, "primary": "4wk", "note": "n", "note_zh": "n",
                             "rows": nine},
             official_sectors={"available": True, "rows": nine_off,
                               "seed_date": "2026-01-01", "n": 9})
    html = _render(v2)
    theme_rows = _sector_row_classes(_table(html, "sectortbl"))
    off_rows = _sector_row_classes(_table(html, "officialtbl"))
    assert len(theme_rows) == 9
    assert len(off_rows) == 9
    assert sum("fv-over" not in c for c in theme_rows) == 8
    assert sum("fv-over" in c for c in theme_rows) == 1
    assert sum("fv-over" not in c for c in off_rows) == 8
    assert sum("fv-over" in c for c in off_rows) == 1
    assert "See all 9 themes" in html
    assert "全部9个主题" in html
    assert "See all 9 sectors" in html
    assert "全部9个行业" in html
    assert "Show fewer" in html
    assert "收起" in html
    assert "fv-cap-toggle" in html
    assert "function resetBoardCap" in html
    assert "resetBoardCap(block)" in html
    assert "tog.checked=false" in html  # cap resets on sort via resetBoardCap

    eight = [_theme(i, vel=1.0 + i * 0.1, rate_4wk=-0.9) for i in range(8)]
    eight_off = [_official(i) for i in range(8)]
    v2_8 = _v2(ashare_sectors={"cadence": "daily", "as_of": "2026-09-01", "n": 8,
                               "n_unscored": 0, "primary": "4wk", "note": "n", "note_zh": "n",
                               "rows": eight},
               official_sectors={"available": True, "rows": eight_off,
                                 "seed_date": "2026-01-01", "n": 8})
    html8 = _render(v2_8)
    rows8 = _sector_row_classes(_table(html8, "sectortbl"))
    off8 = _sector_row_classes(_table(html8, "officialtbl"))
    assert len(rows8) == 8
    assert len(off8) == 8
    assert all("fv-over" not in c for c in rows8)
    assert all("fv-over" not in c for c in off8)
    assert "See all" not in html8
    assert "8 themes" in html8
    assert "8个主题" in html8
    assert "8 sectors" in html8
    assert "8个行业" in html8


def test_w13_me_board_label_and_chip_figures_carry_nouns_same_formatting():
    """M-e: board label is the scored population; board figure formatting matches
    the chip; chip figures carry nouns in both lanes."""
    v2 = _v2(ashare_names={
        "cadence": "daily", "as_of": "2026-09-01", "n": 1521, "n_unscored": 283,
        "primary": "4wk", "note": "note", "note_zh": "note_zh",
        "market_read": market_read(
            [{"vel": 1.0, "rate_4wk": 0.5, "state": "above norm, rising"}] * 10, unscored=283),
        "inflow": [_member()], "outflow": [],
    })
    html = _render(v2)
    assert "A-share names we could score" in html
    assert "已评分A股" in html
    assert "All A-share names" not in html
    assert "1,521" in html
    cn = next(s for s in v2["sources"] if s["source_id"] == "cn_large_order_proxy")
    assert "names" in cn["coverage_line_en"]
    assert "coverage" in cn["coverage_line_en"]
    assert "只已评分" in cn["coverage_line_zh"]
    assert "覆盖率" in cn["coverage_line_zh"]
    assert cn["coverage_line_en"] in html
    assert cn["coverage_line_zh"] in html


def test_w13_mf_exactly_one_h1():
    html = _render(_v2())
    assert html.count("<h1") == 1
    assert "Capital Flow Velocity" in html.split("<h1", 1)[1].split("</h1>", 1)[0]


def test_w13_mi_zero_untipped_bare_dash_rank_spans():
    v2 = _v2(ashare_names={
        "cadence": "daily", "as_of": "2026-09-01", "n": 10, "n_unscored": 3,
        "primary": "4wk", "note": "note", "note_zh": "note_zh",
        "market_read": market_read(
            [{"vel": 1.0, "rate_4wk": 0.5, "state": "above norm, rising"}] * 10, unscored=3),
        "inflow": [_member()], "outflow": [],
    })
    html = _render(v2)
    vis = _visible_only(html)
    assert re.search(r'<span class="rk na"[^>]*>—</span>', vis) is None
    assert "not ranked" in vis
    assert "不排名" in vis
    assert "first day" in vis
    assert "首日" in vis


def test_w13_mj_net_buyer_never_renders_selling_easing():
    """M-j: easing is bound to absolute direction — a net-buyer never renders
    'selling easing' / '卖出趋缓'."""
    assert fv._classify(-1.0, 0.1, abs_value=7.1)[0] == "buying slowing"
    assert fv._classify(-1.0, 0.1, abs_value=7.1)[1] == "买入放缓"
    assert fv._classify(-1.0, 0.1, abs_value=-2.0)[0] == "selling easing"
    assert fv._classify(-1.0, 0.1, abs_value=-2.0)[1] == "卖出趋缓"
    assert fv._classify(-1.0, 0.1, abs_value=None) == ("pace easing", "步伐放缓")
    assert fv._classify(-1.0, 0.1, abs_value=float("nan")) == ("pace easing", "步伐放缓")

    snap_over = _snap()
    for chan in snap_over["aggregate"]:
        if chan["key"] == "southbound":
            chan["vel_primary"] = -1.0
            chan["accel"] = 0.1
            chan["flow_1m_b"] = 7.1
            chan["state"] = "buying slowing"
            chan["state_zh"] = "买入放缓"
            chan["vel"] = {"1w": -0.8, "1m": -1.0, "3m": -0.5}
    v2 = build_v2(snap_over, log_rows=[], market_session="2026-09-01",
                  generated_at="2026-09-01T12:00:00+00:00", seats_as_of="2026-08-30")
    html = _render(v2)
    idx = html.find("Southbound — mainland money into HK")
    assert idx != -1
    card = html[idx:idx + 2500]
    assert "selling easing" not in card
    assert "卖出趋缓" not in card
    assert "still buying, pace fading" in card or "buying slowing" in card
    assert "仍净流入·动能转弱" in card or "买入放缓" in card


def test_w13_r2_sigma_bands_both_lanes_and_channel_noun():
    """B-1: band boundaries 0.9/1.0/1.9/2.0/2.9/3.0 both lanes; channel noun."""
    cases = [
        (0.9, "close to this name's normal pace", "该标的接近自身常态"),
        (1.0, "running above this name's normal pace", "该标的高于自身常态"),
        (1.9, "running above this name's normal pace", "该标的高于自身常态"),
        (2.0, "well above this name's normal pace", "该标的明显高于自身常态"),
        (2.9, "well above this name's normal pace", "该标的明显高于自身常态"),
        (3.0, "further above this name's own normal pace than on all but a handful of days this year",
         "该标的处于今年罕见的高位"),
        (-0.9, "close to this name's normal pace", "该标的接近自身常态"),
        (-1.0, "running below this name's normal pace", "该标的低于自身常态"),
        (-2.0, "well below this name's normal pace", "该标的明显低于自身常态"),
        (-3.0, "further below this name's own normal pace than on all but a handful of days this year",
         "该标的处于今年罕见的低位"),
    ]
    for v, en_clause, zh_clause in cases:
        en, zh = sigma_meaning(v, "name")
        assert f"{v:+.2f}σ" in en and f"{v:+.2f}σ" in zh
        assert en_clause in en, (v, en)
        assert zh_clause in zh, (v, zh)
        assert "this name's" in en
    ch_en, ch_zh = sigma_meaning(0.10, "channel")
    assert "this channel's" in ch_en
    assert "该通道" in ch_zh
    assert "this name's" not in ch_en
    assert "该标的" not in ch_zh
    ch_hi_en, ch_hi_zh = sigma_meaning(4.76, "channel")
    assert "this channel's" in ch_hi_en
    assert "该通道处于今年罕见的高位" in ch_hi_zh
    rendered = html_lib.unescape(_render(_v2()))
    assert "this channel's" in rendered
    assert "该通道" in rendered


def test_w13_r2_vocab_v2_and_masterplan_byte_exact():
    """MAJ-3: VOCAB_V2 tuples match the masterplan §6 table byte-for-byte;
    buying slowing and pace easing have their own keys."""
    assert VOCAB_V2["outflow easing"] == ("selling easing", "卖出趋缓")
    assert VOCAB_V2["buying slowing"] == ("buying slowing", "买入放缓")
    assert VOCAB_V2["pace easing"] == ("pace easing", "步伐放缓")
    mp = (ROOT / "research" / "FLOW_OBSERVATORY_V2_MASTERPLAN_BY_FABLE.md").read_text(
        encoding="utf-8")
    for key, (en, zh) in VOCAB_V2.items():
        assert f"| {key} | {en} | {zh} |" in mp, (key, en, zh)
    assert "selling easing / buying slowing" not in mp


def test_w13_r2_quadrant_chips_demote_sigma_to_banded_tip():
    """MAJ-1: q-chips show a word + abs % at rest; σ lives in the banded tip."""
    acc = _theme(0, vel=2.2, rate_4wk=1.4, rate_rel=2.2,
                 quadrant="true_accumulation",
                 quadrant_en="real inflow, above norm",
                 quadrant_zh="真实流入·高于常态",
                 abs={"value": 1.4, "direction": "positive"},
                 rel={"value": 2.2})
    v2 = _v2(ashare_sectors={"cadence": "daily", "as_of": "2026-09-01", "n": 1,
                             "n_unscored": 0, "primary": "4wk", "note": "n", "note_zh": "n",
                             "rows": [acc]})
    # build_v2 recomputes quadrant from abs/rel; pin the chip by using the computed row
    html = _render(v2)
    # σ must not sit at rest in a q-chip
    for m in re.finditer(r'<span class="q-chip"[^>]*>.*?</span>', html, re.S):
        inner = re.sub(r'data-tip-(?:en|zh)="[^"]*"', "", m.group(0))
        visible = re.sub(r"<[^>]+>", "", inner)
        assert "σ" not in visible, visible
    assert "well above this name" in html
    assert "normal pace" in html
    assert "该标的明显高于自身常态" in html
    assert "q-chip" in html


def test_w13_r2_see_all_does_not_count_all_names_row_as_a_theme():
    """MIN-1: leaders present → N is the theme count, not the __all__ aggregate."""
    nine = [_theme(i, vel=1.0 + i * 0.1, rate_4wk=-0.9) for i in range(9)]
    v2 = _v2(ashare_sectors={"cadence": "daily", "as_of": "2026-09-01", "n": 9,
                             "n_unscored": 0, "primary": "4wk", "note": "n", "note_zh": "n",
                             "rows": nine},
             ashare_names={
                 "cadence": "daily", "as_of": "2026-09-01", "n": 10, "n_unscored": 0,
                 "primary": "4wk", "note": "n", "note_zh": "n",
                 "market_read": market_read(
                     [{"vel": 1.0, "rate_4wk": 0.5, "state": "above norm, rising"}] * 10),
                 "inflow": [_member()], "outflow": [],
             })
    html = _render(v2)
    assert "See all 9 themes" in html
    assert "全部9个主题" in html
    assert "See all 10 themes" not in html
    assert 'data-sector="__all__"' in html


def test_w13_r2_h1_is_a_real_heading_not_a_muted_eyebrow():
    """MAJ-5: the single h1 has a real heading treatment, not font:inherit 11px."""
    html = _render(_v2())
    assert ".fv-hero-eyebrow h1{margin:0;font-size:22px" in html
    assert "font:inherit" not in html.split(".fv-hero-eyebrow h1")[1][:200]


def test_w13_r2_row_hosted_tips_use_lens_q_not_tabindex_on_vbar():
    """MAJ-6: no tabindex host on the vbar itself; dedicated .lens-q button."""
    html = _render(_v2())
    vbars = re.findall(r'<span class="vbar [^"]*"[^>]*>', html)
    for tag in vbars:
        assert "tabindex" not in tag
        assert "data-tip-en" not in tag
    assert 'class="lens-q"' in html
    assert "role=\"button\" tabindex=\"0\"" not in re.findall(
        r'<span class="vbar [^"]*"[^>]*>', html)[0] if vbars else ""


def test_w13_r2_cap_toggle_not_focusable_label_is_button():
    """MIN-7: checkbox is clip-hidden AND unfocusable; label is the control."""
    nine = [_theme(i) for i in range(9)]
    html = _render(_v2(ashare_sectors={"cadence": "daily", "as_of": "2026-09-01", "n": 9,
                                       "n_unscored": 0, "primary": "4wk", "note": "n",
                                       "note_zh": "n", "rows": nine}))
    assert 'class="fv-cap-toggle" tabindex="-1" aria-hidden="true"' in html
    assert 'class="fv-see-all" role="button" tabindex="0" aria-expanded="false"' in html


def test_w13_r2_light_art_direction_named_and_page_scoped():
    """B-2: comment block names both treatments; light rules exist for r1 surfaces."""
    src = (TMPL / "flow_velocity.html.j2").read_text(encoding="utf-8")
    assert "DARK TREATMENT" in src
    assert "LIGHT TREATMENT" in src
    assert "post-stack: consolidate" in src
    html = _render(_v2())
    assert 'html[data-theme="light"] .fv-see-all' in html
    assert 'html[data-theme="light"] .fv-caption' in html
    assert 'html[data-theme="light"] .q-empty .empty-why' in html
    assert 'html[data-theme="light"] .foot' in html
    assert 'html[data-theme="light"] .fv-hero-eyebrow h1' in html
    # W13 r4 m4: light UNAVAILABLE chip figures sit at the muted floor, not the
    # inherited 0.68 opacity of the dark-lane instrument-fault idiom.
    assert 'html[data-theme="light"] .fv-src--unavailable{opacity:1;' in html


# ── W13 r5: no baked relative day-words (seat: dated as-of stamp carries WHEN) ────────
_DAY_WORD_RE = re.compile(r"today|tonight|yesterday|今日|今天|今晚|昨日|昨天", re.I)
_STALE_EN_ALLOWED = "Treat levels as history, not today's tape."
_STALE_ZH_ALLOWED = "而非今日盘面"


def _strip_scripts_styles(html: str) -> str:
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.I | re.S)
    return html


def _page_own_html(html: str) -> str:
    """Page body only. Shared `_site_nav` is a separate governed component
    (same scope as test_at_rest_copy_never_uses_bare_institutions_or_bare_jigou)."""
    if '<div class="wrap">' in html:
        html = html.split('<div class="wrap">', 1)[1]
    return html


def _day_word_hits_outside_stale(html: str) -> list[str]:
    """Banned-set matches in rendered output (tips kept; scripts/styles stripped).

    The seat-lawful stale sentence is the sole allowed match — both the EN
    'not today's tape' clause and the ZH '而非今日盘面' clause.
    """
    body = _strip_scripts_styles(_page_own_html(html))
    allowed = []
    for phrase in (_STALE_EN_ALLOWED, _STALE_ZH_ALLOWED):
        start = 0
        while True:
            i = body.find(phrase, start)
            if i < 0:
                break
            allowed.append((i, i + len(phrase)))
            start = i + len(phrase)
    hits = []
    for m in _DAY_WORD_RE.finditer(body):
        if any(lo <= m.start() < hi for lo, hi in allowed):
            continue
        ctx = body[max(0, m.start() - 24): m.end() + 24].replace("\n", " ")
        hits.append(f"{m.group(0)!r} @ {m.start()} …{ctx}…")
    return hits


def _stale_hero_v2():
    v2 = _v2()
    for s in v2.get("sources") or []:
        if s.get("source_id") == "cn_large_order_proxy":
            s["status"] = "STALE"
            s["ui_state"] = "stale"
            s["effective_date"] = s.get("effective_date") or "2026-08-17"
            break
    return v2


def _empty_confluence_v2():
    v2 = _v2()
    v2["confluence"] = {
        "n_agree": 0, "n_diverge": 0, "agree": [], "diverge": [],
    }
    return v2


def test_w13_r5_replacements_pin_the_seat_frozen_copy_both_lanes():
    html = _render(_v2())
    assert "What changed" in html and "本次变化" in html
    assert "What Changed" in html
    assert "Changed today" not in html
    assert "What Changed Today" not in html
    assert "今日变化" not in html
    assert "Change tracking begins with this build — no prior tracked session." in html
    assert "变化追踪自本次构建开始——暂无历史对比。" in html
    assert "Change tracking begins today" not in html
    assert "变化追踪自今日开始" not in html

    conf = _render(_empty_confluence_v2())
    assert "No overlap where they agree." in conf
    assert "无一致交集" in conf
    assert "No clashes." in conf
    assert "无背离" in conf
    assert "agree today" not in conf
    assert "clashes today" not in conf
    assert "今日无一致" not in conf
    assert "今日无背离" not in conf


def test_w13_r5_rendered_output_has_no_baked_day_words_except_stale_sentence():
    """Page-wide negative: both lanes, scripts/styles stripped, tips INCLUDED.

    Run on the r4 rig's fixture shape plus the contract fixtures that actually
    emit the other seven replacement sites (first-run change tracking, empty
    confluence, empty quadrants) and a STALE-hero shape so the sole-allowed
    stale sentence is asserted verbatim.
    """
    from scripts.capture_flow_velocity_w13_r3_evidence import _fixture_html

    r4_html = _fixture_html()
    default_html = _render(_v2())
    quad_html = _render(build_v2(
        _snap(ashare_sectors={
            **_snap()["ashare_sectors"],
            "rows": [_autos_row(rate_4wk=-0.9, vel=1.9, rate_rel=1.9),
                     _gold_row(rate_4wk=-1.2, vel=-1.7, rate_rel=-1.7)],
        }),
        log_rows=[], market_session="2026-09-01",
        generated_at="2026-09-01T12:00:00+00:00", seats_as_of="2026-08-30"))
    conf_html = _render(_empty_confluence_v2())
    stale_html = _render(_stale_hero_v2())

    for label, html in (("r4", r4_html), ("default", default_html),
                        ("quadrant-empty", quad_html), ("confluence-empty", conf_html)):
        hits = _day_word_hits_outside_stale(html)
        assert hits == [], f"{label} fixture leaked banned day-words: {hits}"

    stale_body = _strip_scripts_styles(_page_own_html(stale_html))
    assert _STALE_EN_ALLOWED in stale_body, "stale EN sentence missing — allowlist untestable"
    assert _STALE_ZH_ALLOWED in stale_body, "stale ZH sentence missing — allowlist untestable"
    stale_hits = _day_word_hits_outside_stale(stale_html)
    assert stale_hits == [], (
        "stale fixture must have the verbatim stale sentence as the sole allowed "
        f"banned-set match; extra hits: {stale_hits}")
    # Positive control: the instrument still fires on the banned word when present.
    assert _DAY_WORD_RE.search("Changed today") and _DAY_WORD_RE.search("今日变化")
