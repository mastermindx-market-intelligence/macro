"""Intelligence Hub keeps machine receipts off the primary reading path."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
TEMPLATE = TEMPLATES / "intelligence_hub.html.j2"
SITE = ROOT / "site" / "intelligence_hub.html"


def _macro(name: str, markup: str) -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    start = text.index("{% macro " + name)
    end_marker = "{%- endmacro %}"
    end = text.index(end_marker, start) + len(end_marker)
    macro_src = text[start:end]
    prelude = ""
    if name == "qlword":
        for var in ("QL_EN", "QL_ZH"):
            vm = re.search(r"{% set " + var + r" = .*? %}", text)
            assert vm, f"{var} missing"
            prelude += vm.group(0)
    env = Environment(autoescape=True)
    return env.from_string(prelude + macro_src + markup).render()


def test_entry_badge_is_review_language_not_machine_buy_jargon() -> None:
    html = _macro("entrybadge", "{{ entrybadge({'buyable': true, 'tier': 'T2'}) }}")
    assert "ready to review" in html.lower()
    assert "可复核" in html
    assert "Technical tier: T2" in html
    assert "Validated confluence buy" not in html
    assert "entry T2" not in html
    assert "⚡" not in html


def test_qledger_states_render_as_human_status_words() -> None:
    cases = [
        ("UNGRADED", "ql-ungraded", "no history", "暂无记录"),
        ("ACCRUING", "ql-accruing", "building record", "记录积累中"),
        ("GRADED", "ql-graded-pos", "measured", "已有记录"),
    ]
    for state, css, en, zh in cases:
        html = _macro("qlword", "{{ qlword({'state': '" + state + "', 'css_class': '" + css + "'}) }}")
        assert en in html
        assert zh in html
        assert f">{state.lower()}<" not in html


def test_ranking_explainer_is_short_plain_tier_two_copy() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r'aria-label="How this page ranks names"\s+data-tip-en="([^"]+)"', text)
    assert m, "ranking help tooltip missing"
    tip = m.group(1)
    assert len(tip.split()) <= 80
    for banned in ("genuine signal ×", "Deliberately NOT ranked", "crowd favourite"):
        assert banned not in tip
    assert "room for the move" in tip.lower()
    assert "Policy intent is shown as context" in tip


def test_track_record_uses_evidence_wording_not_proof_language() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "pre-registered significance bar" not in text
    assert "{{ t('proven', '已验证') }}" not in text
    assert "preset evidence threshold" in text
    assert "{{ t('supported', '有证据') }}" in text


def test_desk_rail_does_not_expose_raw_qledger_labels() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    rail = text[text.index('{# ── desk rail.'):text.index('{# ── EMERGING EDGE')]
    assert "qc.label" not in rail
    assert "UNGRADED · n=0" not in rail
    assert "qlreceipt(qc" in rail


def test_committed_page_matches_plain_language_contract() -> None:
    """Conditional labels are exercised by explicit full-template states below."""
    html = SITE.read_text(encoding="utf-8")
    for banned in ("Validated confluence buy", "UNGRADED · n=0", "pre-registered significance bar", ">proven<", "⚡"):
        assert banned not in html


def test_structured_watch_condition_renders_human_text_only() -> None:
    html = _macro("watchcopy", "{{ watchcopy({'text': 'Revenue falls below expectations.', 'text_zh': '营收低于预期。', 'check': {'kind': 'rel_return', 'threshold': -0.05}}) }}")
    assert 'Revenue falls below expectations.' in html
    assert '营收低于预期。' in html
    assert 'rel_return' not in html and 'threshold' not in html


def test_watch_condition_keeps_legacy_text_and_escapes_markup() -> None:
    html = _macro("watchcopy", "{{ watchcopy('A legacy condition') }}")
    assert 'A legacy condition' in html
    html = _macro("watchcopy", "{{ watchcopy({'text': '<img src=x onerror=alert(1)>'}) }}")
    assert '<img ' not in html
    assert '&lt;img' in html


def test_watch_condition_never_stringifies_invalid_shapes() -> None:
    for value in ("none", "42", "[]", "{'check': {'kind': 'rel_return'}}", "{'text': {'unexpected': 1}}"):
        html = _macro("watchcopy", "{{ watchcopy(" + value + ") }}")
        assert 'Review condition unavailable' in html
        assert '复核条件暂缺' in html
        assert 'rel_return' not in html and 'unexpected' not in html


def test_mobile_command_rows_have_a_full_width_explanation() -> None:
    src = TEMPLATE.read_text(encoding="utf-8")
    assert 'class="led-metrics"' in src and 'class="led-analysis"' in src
    assert '.led-row > .led-analysis{grid-column:2 / -1;grid-row:2;' in src
    assert '{{ watchcopy(d.falsifier) }}' in src
    assert '{{ d.falsifier|e }}' not in src


def test_rendered_watch_conditions_have_no_serialized_check() -> None:
    """The full template path stays safe even when today's page has zero watches."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.globals["region_for"] = lambda _ticker: "us"
    falsifier = {
        "text": "Revenue falls below expectations.",
        "text_zh": "营收低于预期。",
        "check": {"subject_ticker": "TEST", "horizon_d": 20},
    }
    row = {
        "ticker": "TEST",
        "opportunity_score": 80,
        "composite_conviction": 80,
        "directions": {},
        "stage": "emerging",
        "entry_gate": None,
        "trajectory": None,
        "flags": [],
        "leading_gap": 0,
        "edge_drivers": [],
        "falsifier": falsifier,
        "price": None,
        "edge_remaining": 0.5,
        "n_confirm": 0,
        "source_mix": [],
        "sectors": [],
    }
    hub = {
        "command": [row],
        "emerging": [],
        "discovery": [],
        "exhausted": [],
        "catalysts": [],
        "track_record": None,
        "desk_grader": {},
        "sector_heat": [],
        "disclaimer": "",
        "n_universe": 1,
        "n_actionable": 1,
        "macro_context": {},
        "desks": {},
        "as_of": "2026-09-27",
        "counts": {},
    }
    html = env.get_template("intelligence_hub.html.j2").render(
        hub=hub,
        built="2026-09-27T00:00:00+00:00",
        mode="intel_hub",
        qledger_chips={},
        china=None,
        market_pulse_roster=["TEST"],
        research_implications={"cards": []},
    )
    watches = re.findall(r'<div class="watch">(.*?)</div>', html, re.S)
    assert len(watches) == 1
    watch = watches[0]
    assert "Revenue falls below expectations." in watch
    assert "营收低于预期。" in watch
    assert "subject_ticker" not in watch and "horizon_d" not in watch
    assert "&#39;text&#39;" not in watch and "&#39;check&#39;" not in watch


def _render_glance_page(*, entry_gate=None, qledger_chips=None, **hub_overrides) -> str:
    """Render conditional copy through the shipped template with synthetic inputs."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=True)
    env.globals["region_for"] = lambda _ticker: "us"
    row = {
        "ticker": "TEST",
        "opportunity_score": 80,
        "composite_conviction": 80,
        "directions": {},
        "stage": "emerging",
        "entry_gate": entry_gate,
        "trajectory": None,
        "flags": [],
        "leading_gap": 0,
        "edge_drivers": [],
        "falsifier": None,
        "price": None,
        "edge_remaining": 0.5,
        "n_confirm": 0,
        "source_mix": [],
        "sectors": [],
    }
    hub = {
        "command": [row],
        "emerging": [],
        "discovery": [],
        "exhausted": [],
        "catalysts": [],
        "track_record": None,
        "desk_grader": {},
        "sector_heat": [],
        "disclaimer": "",
        "n_universe": 1,
        "n_actionable": 1,
        "macro_context": {},
        "desks": {},
        "as_of": "2026-09-27",
        "counts": {},
    }
    hub.update(hub_overrides)
    return env.get_template("intelligence_hub.html.j2").render(
        hub=hub,
        built="2026-09-27T00:00:00+00:00",
        mode="intel_hub",
        qledger_chips=qledger_chips or {},
        china=None,
        market_pulse_roster=["TEST"],
        research_implications={"cards": []},
    )


def test_full_template_renders_populated_plain_language_states() -> None:
    html = _render_glance_page(
        entry_gate={"buyable": True, "tier": "T2"},
        qledger_chips={
            "news": {"state": "UNGRADED", "css_class": "ql-ungraded"},
            "alt_data": {"state": "ACCRUING", "css_class": "ql-accruing"},
            "radar": {"state": "GRADED", "css_class": "ql-graded-pos"},
        },
    )
    assert 'class="chip en-buy"' in html
    assert '<span class="l-en">ready to review</span>' in html
    assert '<span class="l-zh">可复核</span>' in html
    for css, en, zh in (
        ("ql-ungraded", "no history", "暂无记录"),
        ("ql-accruing", "building record", "记录积累中"),
        ("ql-graded-pos", "measured", "已有记录"),
    ):
        assert (
            f'<span class="gw {css}"><span class="l-en">{en}</span>'
            f'<span class="l-zh">{zh}</span></span>'
        ) in html


@pytest.mark.parametrize(
    "entry_gate",
    [None, {}, {"buyable": False, "tier": "T2"}],
    ids=["absent", "empty", "not-buyable"],
)
def test_full_template_does_not_invent_conditional_states(entry_gate) -> None:
    html = _render_glance_page(entry_gate=entry_gate, qledger_chips={})
    assert 'class="chip en-buy"' not in html
    assert '<span class="l-en">ready to review</span>' not in html
    assert '<span class="l-zh">可复核</span>' not in html
    states = re.findall(
        r'<span class="gw ([^"]+)"><span class="l-en">([^<]+)</span>'
        r'<span class="l-zh">([^<]+)</span></span>',
        html,
    )
    assert states
    assert set(states) == {("ql-ungraded", "no history", "暂无记录")}


@pytest.mark.parametrize(
    "banned",
    ["Validated confluence buy", "UNGRADED · n=0", "pre-registered significance bar", ">proven<", "⚡"],
)
def test_committed_page_contract_rejects_forbidden_copy(tmp_path, monkeypatch, banned) -> None:
    html = _render_glance_page(entry_gate=None)
    synthetic_site = tmp_path / "intelligence_hub.html"
    synthetic_site.write_text(html.replace("</body>", f"<div>{banned}</div></body>"), encoding="utf-8")
    monkeypatch.setitem(globals(), "SITE", synthetic_site)
    with pytest.raises(AssertionError):
        test_committed_page_matches_plain_language_contract()


# ── W18-A: the Hub prints the evidence it already publishes ──


def _w18a1_track_record(*, with_coverage=True, n_missing=10) -> dict:
    """Synthetic track_record shaped like the committed hub.json values."""
    tr = {
        "n_snapshots": 120,
        "any_matured": True,
        "proven": {},
        "horizons": {
            "5": {"n_matured": 187762, "opportunity_ic": -0.0168,
                  "by_stage": {}},
        },
        "accrual_gaps": {
            "approximate": True,
            "window_days": 30,
            "n_expected": 21,
            "n_present": 11,
            "n_missing": n_missing,
            "missing_dates": ["2026-09-21", "2026-09-22", "2026-09-23",
                              "2026-09-24", "2026-09-25", "2026-10-15"],
            "first_snapshot": "2026-06-21",
            "last_snapshot": "2026-10-19",
            "note": "Expected dates are pandas business days — NYSE market "
                    "holidays inside the window are counted as gaps, so this "
                    "over-reports rather than under-reports.",
        },
    }
    if with_coverage:
        tr["coverage_pct"] = {
            "5": {"n_eligible": 266959, "n_matured": 187762,
                  "coverage_pct": 70.33, "below_floor": False},
        }
    return tr


def _w18a1_trh_block(html: str) -> str:
    """Slice the rendered track-record card block (the trh grid)."""
    m = re.search(r'<div class="trh">.*?\n  </div>', html, re.S)
    assert m, "trh block missing from rendered page"
    return m.group(0)


def _w18a1_gap_note(html: str) -> str:
    """Slice the accrual-gap card note body, or '' when it is not rendered."""
    for m in re.finditer(r'<div class="card note">(.*?)</div>', html, re.S):
        if "snapshot dates" in m.group(1) or "没有快照" in m.group(1):
            return m.group(1)
    return ""


def test_w18a1_track_record_prints_committed_coverage() -> None:
    html = _render_glance_page(track_record=_w18a1_track_record())
    card = _w18a1_trh_block(html)
    assert "187,762" in card
    assert "70% of 266,959 eligible" in card
    assert "占可评分 266,959 条的 70%" in card


def test_w18a1_gap_note_quotes_count_and_holiday_caveat() -> None:
    html = _render_glance_page(track_record=_w18a1_track_record())
    note = _w18a1_gap_note(html)
    assert note, "accrual-gap note missing"
    assert "10 of 21 expected snapshot dates in the last 30 days " \
        "have no snapshot." in note
    assert "Approximate: market holidays count as missing, so this " \
        "over-reports." in note
    assert "近 30 天预期的 21 个快照日中，有 10 个没有快照。" in note
    assert "为近似值：市场假日也计为缺失，因此偏高。" in note
    assert "skipped" not in note.lower()
    assert "nightly" not in note.lower()


def test_w18a1_no_gap_note_or_coverage_when_absent() -> None:
    html_zero = _render_glance_page(
        track_record=_w18a1_track_record(n_missing=0))
    assert _w18a1_gap_note(html_zero) == ""
    html_nocov = _render_glance_page(
        track_record=_w18a1_track_record(with_coverage=False))
    card = _w18a1_trh_block(html_nocov)
    assert "eligible" not in card
    assert "占可评分" not in card
    assert "None" not in card
    assert "0%" not in card


def _w18a2_glance_row(**changes) -> dict:
    base = {
        "ticker": "IBM", "opportunity_score": 21.3, "composite_conviction": 21,
        "directions": {}, "stage": "early", "entry_gate": None, "trajectory": None,
        "flags": [], "leading_gap": 0, "edge_drivers": [], "falsifier": None,
        "price": None, "edge_remaining": 0.5, "n_confirm": 0, "lean": 0,
        "source_mix": [], "sectors": [],
    }
    base.update(changes)
    return base


def _w18a2_strip(html: str) -> str:
    start = html.index("萌芽优势")
    j = html.index('<div class="empty">', start)
    return html[j : html.index("</div>", j)]


def test_w18a2_empty_strip_names_the_barred_early_name() -> None:
    ibm = _w18a2_glance_row(entry_gate={"eligible": False, "buyable": False,
                                        "flat_sell": True},
                            trajectory={"rolling_over": False})
    html = _render_glance_page(counts={"early": 1, "emerging": 0}, command=[ibm])
    strip = _w18a2_strip(html)
    assert "already moved" not in strip
    assert "已经发动" not in strip
    assert "IBM" in strip
    assert "entry checks did not agree" in strip
    assert "入场条件不一致" in strip
    assert "flat_sell" not in html


def test_w18a2_zero_counts_has_no_false_cause() -> None:
    for counts in ({}, {"early": 0, "emerging": 0}):
        html = _render_glance_page(counts=counts)
        strip = _w18a2_strip(html)
        assert "Nothing emerging today." in strip
        assert "今日无萌芽机会。" in strip
        assert "already moved" not in html
        assert "已经发动" not in html


def test_w18a2_rolling_over_reason_outranks_gate() -> None:
    ibm = _w18a2_glance_row(entry_gate={"eligible": False, "buyable": False,
                                        "flat_sell": True},
                            trajectory={"rolling_over": True})
    html = _render_glance_page(counts={"early": 1, "emerging": 0}, command=[ibm])
    strip = _w18a2_strip(html)
    assert "price rolling over" in strip
    assert "价格转弱" in strip
    assert "entry checks did not agree" not in strip
    assert '<div class="card ecard' not in html


def _w18a3_q2_track_record(quad_ic: float | None = -0.0365, **q2) -> dict:
    """Synthetic horizon-5 entry shaped like the committed track_record slice."""
    q2_cell = {"n": 77077, "mean_fwd_rel": 0.0358, "hit_rate": 0.479,
               "opportunity_ic": quad_ic}
    q2_cell.update(q2)
    return {
        "n_snapshots": 120,
        "any_matured": True,
        "proven": {},
        "horizons": {"5": {
            "n_matured": 187762,
            "opportunity_ic": -0.0168,
            "by_stage": {},
            "by_regime": {
                "Q1": {"n": 10310, "mean_fwd_rel": 0.4884, "hit_rate": 0.478,
                       "opportunity_ic": 0.0274},
                "Q2": q2_cell,
                "Q3": {"n": 26297, "mean_fwd_rel": 0.0345, "hit_rate": 0.465,
                       "opportunity_ic": -0.0178},
            },
        }},
    }


def _w18a3_rank_skill_cell(html: str) -> str:
    """The rank-skill cell region of the single rendered 5d card."""
    start = html.index("rank skill")
    return html[start:html.index("scored", start)]


def test_w18a3_rank_skill_prints_q2_slice() -> None:
    html = _render_glance_page(macro_context={"quad": "Q2"},
                               track_record=_w18a3_q2_track_record())
    cell = _w18a3_rank_skill_cell(html)
    assert "%+.3f" % -0.0365 in cell
    assert "77,077" in cell
    assert "this regime (Q2)" in cell
    assert "本格局 Q2" in cell
    assert "%+.3f" % -0.0168 in cell


def test_w18a3_no_slice_when_quad_missing() -> None:
    for macro_context in ({"quad": "Q4"}, {}):
        html = _render_glance_page(macro_context=macro_context,
                                   track_record=_w18a3_q2_track_record())
        assert "this regime" not in html
        assert "本格局" not in html
        assert "+0.000" not in html


@pytest.mark.parametrize(
    "q2",
    [{"quad_ic": None}, {"n": None}],
    ids=["null-ic", "null-n"],
)
def test_w18a3_incomplete_slice_is_omitted(q2) -> None:
    html = _render_glance_page(macro_context={"quad": "Q2"},
                               track_record=_w18a3_q2_track_record(**q2))
    assert "this regime" not in html
    assert "本格局" not in html
    assert "+0.000" not in html
    assert "%+.3f" % -0.0168 in html


def _w18a4_sg(**patch) -> dict:
    """Synthetic hub.signal_governor shaped like the committed hub.json payload."""
    sg = {
        "schema": "signal_governor.v1",
        "generated_at": "2026-10-18T01:00:00+00:00",
        "region": "us",
        "gate": {"hub": 0.05, "radar": 0.05},
        "trust": {"radar": 1.0, "hub": 1.0},
        "signals": {
            "hub": {"n_matured": 160108, "horizon": "21", "demoted": False,
                    "reason": "IC=+0.012 t_hac=0.84 below gate"},
            "radar": {"n_matured": 16280, "horizon": "21", "demoted": False,
                      "reason": "IC=-0.004 t_hac=-0.21"},
        },
        "n_demoted": 0,
        "note": ("No signal has cleared the de-escalation gate yet — "
                 "all trust 1.0 (shadow/measuring)."),
        "inputs": ["a.json"],
        "stale_inputs": [],
    }
    sg.update(patch)
    return sg


def _w18a4_strip(html: str) -> str:
    """The governor card note body, or '' when it is not rendered."""
    for m in re.finditer(r'<div class="card note">(.*?)</div>', html, re.S):
        if "Desk-history check" in m.group(1):
            return m.group(1)
    return ""


def test_w18a4_governor_strip_prints_committed_counts() -> None:
    html = _render_glance_page(signal_governor=_w18a4_sg())
    strip = _w18a4_strip(html)
    assert "信号台历史检查" in strip
    assert "not currently pulling any names down" in strip
    assert "目前未下调任何标的" in strip
    assert "160,108" in strip
    assert "16,280" in strip
    assert "this page" in strip and "本页" in strip
    assert "radar" in strip and "雷达" in strip
    assert "scored" in strip and "已评分" in strip
    assert not re.search(r'<span class="chip">\s*hub\b', strip)
    note = _w18a4_sg()["note"]
    for leak in ("IC=", "t_hac", "HAC", "DEMOTED", "trust 1.0", note):
        assert leak not in html


def test_w18a4_governor_strip_omitted_when_empty() -> None:
    for overrides in ({"signal_governor": {}}, {"signal_governor": None}, {}):
        html = _render_glance_page(**overrides)
        assert "Desk-history check" not in html
        assert "信号台历史检查" not in html


def test_w18a4_demoted_branch_counts_without_raw_reason() -> None:
    sg = _w18a4_sg(n_demoted=1)
    sg["signals"]["hub"]["demoted"] = True
    html = _render_glance_page(signal_governor=sg)
    assert "signal(s) currently weighted down" in html
    assert "个信号因自身评分记录而被降权" in html
    assert "not currently pulling" not in html
    assert "目前未下调" not in html
    assert "IC=" not in html


def _w18a5_footer(html: str) -> str:
    m = re.search(r'<footer class="hf">.*?</footer>', html, re.S)
    assert m, "footer missing"
    return m.group(0)


def test_w18a5_footer_prints_committed_exclusion_count() -> None:
    """The US gate prints how many names were counted out, with the roster date."""
    html = _render_glance_page(
        n_universe=2247,
        universe_scope={
            "applied": True,
            "n_in": 2235,
            "n_excluded": 731,
            "roster_date": "2026-10-15",
            "excluded_sample": ["ZZQX", "QQZY"],
        },
    )
    footer = _w18a5_footer(html)
    assert "731" in footer
    assert "2,247" in footer
    assert "non-US names excluded" in footer
    assert "未纳入" in footer
    assert "(roster 2026-10-15)" in footer
    assert "（名册 2026-10-15）" in footer
    assert "ZZQX" not in html
    assert "QQZY" not in html


@pytest.mark.parametrize(
    "overrides",
    [
        {"universe_scope": {"applied": False, "n_excluded": 731,
                            "roster_date": "2026-10-15"}},
        {"universe_scope": {}},
        {},
    ],
    ids=["not-applied", "empty-scope", "scope-missing"],
)
def test_w18a5_footer_omits_exclusions_when_not_applied(overrides) -> None:
    footer = _w18a5_footer(_render_glance_page(n_universe=2247, **overrides))
    assert "731" not in footer
    assert "excluded" not in footer
    assert "未纳入" not in footer


def test_w18a5_missing_roster_date_keeps_count() -> None:
    html = _render_glance_page(
        n_universe=2247,
        universe_scope={"applied": True, "n_in": 2235, "n_excluded": 731},
    )
    footer = _w18a5_footer(html)
    assert "731" in footer
    assert "未纳入" in footer
    assert "(roster" not in footer
    assert "（名册" not in footer
    assert "None" not in footer


# ── W20-L2: the Discovery-feed card on the track-record band ──


def _w20l2_track_record() -> dict:
    """Synthetic track_record carrying per-feed by_source stats, as hub.json does.

    Key order is load-bearing: the other-horizons line joins in dict order,
    and the 21d by_source order (radar first) pins the alphabetical sort.
    """
    return {
        "n_snapshots": 120, "any_matured": True, "proven": {},
        "horizons": {
            "5": {"n_matured": 9000, "opportunity_ic": -0.01, "by_stage": {}, "by_source": {
                "insider_cluster": {"n": 2757, "mean_fwd_rel": -0.0072, "hit_rate": 0.423},
                "radar_quiet": {"n": 159, "mean_fwd_rel": 0.0109, "hit_rate": 0.528},
                "federal_velocity": {"n": 140, "mean_fwd_rel": -0.016, "hit_rate": None}}},
            "21": {"n_matured": 8000, "opportunity_ic": -0.02, "by_stage": {}, "by_source": {
                "radar_quiet": {"n": 132, "mean_fwd_rel": 0.0221, "hit_rate": 0.477},
                "insider_cluster": {"n": 2124, "mean_fwd_rel": -0.0398, "hit_rate": 0.302},
                "federal_velocity": {"n": 108, "mean_fwd_rel": -0.0573, "hit_rate": None},
                "stale_feed": {"n": 0, "mean_fwd_rel": 0.0, "hit_rate": None},
                "gap_feed": {"n": 5, "mean_fwd_rel": None, "hit_rate": None},
                "flat_feed": {"n": 3, "mean_fwd_rel": 0.0, "hit_rate": 0.0}}},
            "63": {"n_matured": 2000, "opportunity_ic": -0.03, "by_stage": {}, "by_source": {
                "insider_cluster": {"n": 557, "mean_fwd_rel": -0.0904, "hit_rate": 0.212},
                "radar_quiet": {"n": 0, "mean_fwd_rel": 0.0, "hit_rate": None},
                "federal_velocity": {"n": 45, "mean_fwd_rel": -0.1551, "hit_rate": 0.222}}},
        },
    }


def _w20l2_card(html: str) -> str:
    """Slice the rendered Discovery-leads feed card, or '' when it is absent."""
    m = re.search(r'<div class="card trc trsrc">.*?\n  </div>', html, re.S)
    return m.group(0) if m else ""


def _w20l2_cell(card: str, label: str) -> str:
    """The ONE trcell whose first trlab text equals label; asserts exactly one."""
    hits = []
    for piece in card.split('<div class="trcell"')[1:]:
        m = re.search(r'<span class="trlab">(.*?)</span>', piece, re.S)
        if m and m.group(1) == label:
            hits.append(piece)
    assert len(hits) == 1, f"expected exactly one cell for {label!r}, got {len(hits)}"
    return hits[0]


def test_w20l2_feed_card_prints_21d_values() -> None:
    html = _render_glance_page(track_record=_w20l2_track_record())
    card = _w20l2_card(html)
    assert card, "Discovery-feed card missing"
    assert "Discovery leads · 21d" in card
    assert "发掘线索 · 21天" in card
    ins = _w20l2_cell(card, "insider cluster")
    assert "-4.0%" in ins
    assert "n 2,124" in ins
    assert "30% of leads beat SPY" in ins
    assert "30% 的线索跑赢标普" in ins
    assert "lagged SPY" in ins
    assert "跑输标普" in ins
    rad = _w20l2_cell(card, "radar quiet")
    assert "+2.2%" in rad
    assert "n 132" in rad
    assert "48% of leads beat SPY" in rad
    assert "跑赢标普" in rad
    fed = _w20l2_cell(card, "federal velocity")
    assert "-5.7%" in fed
    assert "n 108" in fed
    assert "of leads beat SPY" not in fed
    assert "insider cluster" in card
    assert "insider_cluster" not in card
    assert "None" not in card


def test_w20l2_feed_card_other_horizons_line() -> None:
    html = _render_glance_page(track_record=_w20l2_track_record())
    card = _w20l2_card(html)
    ins = _w20l2_cell(card, "insider cluster")
    assert "5d -0.7% · 63d -9.0%" in ins
    assert "5天 -0.7% · 63天 -9.0%" in ins
    fed = _w20l2_cell(card, "federal velocity")
    assert "5d -1.6% · 63d -15.5%" in fed
    rad = _w20l2_cell(card, "radar quiet")
    assert "5d +1.1%" in rad
    assert "63d" not in rad
    assert "63天" not in rad
    for label in ("insider cluster", "radar quiet", "federal velocity", "flat feed"):
        cell = _w20l2_cell(card, label)
        assert "21d " not in cell
        assert "21天 " not in cell


@pytest.mark.parametrize("case", ["empty", "no_key", "no_horizon"])
def test_w20l2_feed_card_absent_without_21d_sources(case: str) -> None:
    tr = _w20l2_track_record()
    if case == "empty":
        tr["horizons"]["21"]["by_source"] = {}
    elif case == "no_key":
        del tr["horizons"]["21"]["by_source"]
    else:
        del tr["horizons"]["21"]
    html = _render_glance_page(track_record=tr)
    assert _w20l2_card(html) == ""
    assert "Discovery leads" not in html


def test_w20l2_incomplete_feeds_are_skipped() -> None:
    html = _render_glance_page(track_record=_w20l2_track_record())
    card = _w20l2_card(html)
    assert card
    assert "stale feed" not in card
    assert "gap feed" not in card


def test_w20l2_flat_feed_reads_matched() -> None:
    html = _render_glance_page(track_record=_w20l2_track_record())
    cell = _w20l2_cell(_w20l2_card(html), "flat feed")
    assert "+0.0%" in cell
    assert "matched SPY" in cell
    assert "持平标普" in cell
    assert re.search(r'<span class="trans ?">\s*<span class="l-en">matched SPY', cell)
    assert 'class="trval "' in cell
    assert 'class="trval pos"' not in cell
    assert 'class="trval neg"' not in cell
    assert "0% of leads beat SPY" in cell


def test_w20l2_cells_carry_direction_classes() -> None:
    html = _render_glance_page(track_record=_w20l2_track_record())
    card = _w20l2_card(html)
    ins = _w20l2_cell(card, "insider cluster")
    assert 'class="trval neg"' in ins
    assert 'class="trans bad"' in ins
    rad = _w20l2_cell(card, "radar quiet")
    assert 'class="trval pos"' in rad
    assert 'class="trans ok"' in rad


def test_w20l2_feeds_sorted_by_name() -> None:
    html = _render_glance_page(track_record=_w20l2_track_record())
    card = _w20l2_card(html)
    i_fed = card.index("federal velocity")
    i_ins = card.index("insider cluster")
    i_rad = card.index("radar quiet")
    assert i_fed < i_ins < i_rad


def test_w20l2_card_sits_between_grid_and_gap_note() -> None:
    tr = _w20l2_track_record()
    tr["accrual_gaps"] = _w18a1_track_record()["accrual_gaps"]
    html = _render_glance_page(track_record=tr)
    assert "Discovery leads" not in _w18a1_trh_block(html)
    assert html.index('class="card trc trsrc"') > html.index('<div class="trh">')
    assert html.index('class="card trc trsrc"') < html.index("snapshot dates")


def test_w20l2_feed_name_escaped_in_production_env(monkeypatch) -> None:
    import jinja2

    assert jinja2.select_autoescape(["html", "xml"])("intelligence_hub.html.j2") is False

    def _w20l2_env(**kw):
        kw["autoescape"] = jinja2.select_autoescape(["html", "xml"])
        return jinja2.Environment(**kw)

    monkeypatch.setitem(globals(), "Environment", _w20l2_env)
    tr = _w20l2_track_record()
    tr["horizons"]["21"]["by_source"] = {
        "<b>x</b>": {"n": 3, "mean_fwd_rel": 0.01, "hit_rate": 0.5},
    }
    card = _w20l2_card(_render_glance_page(track_record=tr))
    assert card
    assert "&lt;b&gt;x&lt;/b&gt;" in card
    assert "<b>x</b>" not in card


def test_w20l2_seat_edge_cells() -> None:
    """A 0.0 hit rate prints; a horizon with n but no mean is skipped; no empty line."""
    tr = _w20l2_track_record()
    tr["horizons"]["5"]["by_source"]["flat_feed"] = {
        "n": 4, "mean_fwd_rel": None, "hit_rate": None}
    card = _w20l2_card(_render_glance_page(track_record=tr))
    flat = _w20l2_cell(card, "flat feed")
    assert "0% of leads beat SPY" in flat
    assert "5d" not in flat
    assert flat.count('class="trlab"') == 2
