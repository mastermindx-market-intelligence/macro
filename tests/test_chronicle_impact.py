"""Tests for engine.chronicle.impact — MO-PAID-017 event-to-asset projection.

Acceptance (MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv row
MO-PAID-017): a consequence surface per event family reads spine output;
calibrated fields absent. Event identity stays spine.py's own (no second
event database); event-time vs known-at are both printed (known_at only
when the source data genuinely supports a distinct clock -- otherwise a
typed null reason, never fabricated); direct vs second-order materiality is
labelled; causal labels never exceed uncalibrated association; weak
second-order (corpus-dominant themes / ambiguous caps) fails closed rather
than ranking; no nightly git-tracked impact.jsonl dump.

Events are built via schema.new_event (the real assembly path every adapter
uses) rather than hand-rolled dicts, so a spine field rename here fails these
tests instead of leaving them silently green.
"""
from __future__ import annotations

import time

from engine.chronicle import impact, schema


def _ev(source_ref, date, ts=None, source="research_vault", kind="report",
        tickers=None, themes=None):
    ts = ts if ts is not None else f"{date}T00:00:00Z"
    return schema.new_event(
        id=schema.make_id(source, source_ref, date),
        ts=ts,
        date=date,
        source=source,
        source_ref=source_ref,
        kind=kind,
        title="t",
        facts=["a fact"],
        tickers=tickers or [],
        themes=themes or [],
        weight_hint=1,
        links=schema.make_links(site="/x.html"),
    )


def test_event_identity_is_spine_own_no_second_database():
    ev = _ev("abc123", "2026-09-01", tickers=["NVDA"])
    proj = impact.project_event_impact(ev)
    assert proj["event_id"] == ev["id"]


def test_event_time_vs_known_at_are_distinct_and_printed():
    # Alias of the genuine-distinct-clock case — PR acceptance evidence name.
    ev = _ev("x-1", date="2026-08-30", ts="2026-08-30T14:22:00Z", tickers=["AAPL"])
    proj = impact.project_event_impact(ev)
    assert proj["event_time"] == "2026-08-30"
    assert proj["known_at"] == "2026-08-30T14:22:00Z"
    assert proj["known_at_reason"] is None
    assert proj["event_time"] != proj["known_at"]


def test_known_at_printed_when_source_gives_a_genuine_distinct_clock():
    ev = _ev("x-1b", date="2026-08-30", ts="2026-08-30T14:22:00Z", tickers=["AAPL"])
    proj = impact.project_event_impact(ev)
    assert proj["event_time"] == "2026-08-30"
    assert proj["known_at"] == "2026-08-30T14:22:00Z"
    assert proj["known_at_reason"] is None


def test_known_at_is_null_with_typed_reason_when_ts_is_synthetic_midnight():
    ev = _ev("x-2", date="2026-09-01", ts="2026-09-01T00:00:00Z", tickers=["MSFT"])
    proj = impact.project_event_impact(ev)
    assert proj["event_time"] == "2026-09-01"
    assert proj["known_at"] is None
    assert proj["known_at_reason"] == impact.NO_DISTINCT_SOURCE_CLOCK


def test_clockless_event_projects_null_time_fields_with_typed_reason_not_none_silently():
    ev = {"id": "cev-x-clockless", "ts": None, "date": None, "source": "earnings",
          "source_ref": "r", "kind": "earnings", "title": "t", "facts": [],
          "tickers": ["TSLA"], "themes": [], "horizon_hint": "short",
          "weight_hint": 1, "links": {"site": None, "source": None, "receipt": None}}
    proj = impact.project_event_impact(ev)
    assert proj["event_time"] is None
    assert proj["known_at"] is None
    assert proj["known_at_reason"] == impact.NO_SOURCE_CLOCK


def test_ts_without_date_recovers_event_time_not_known_at_alone():
    # MINOR: date absent + ts present must not print known_at beside a null
    # event_time — recover the calendar date from the timestamp.
    ev = {"id": "cev-x-ts-only", "ts": "2026-09-01T14:00:00Z", "date": None,
          "source": "research_vault", "source_ref": "r", "kind": "report",
          "title": "t", "facts": [], "tickers": ["AAPL"], "themes": [],
          "horizon_hint": "medium", "weight_hint": 1,
          "links": {"site": None, "source": None, "receipt": None}}
    proj = impact.project_event_impact(ev)
    assert proj["event_time"] == "2026-09-01"
    assert proj["known_at"] == "2026-09-01T14:00:00Z"
    assert proj["known_at_reason"] is None


def test_direct_materiality_for_named_ticker():
    ev = _ev("x-3", "2026-09-01", tickers=["MSFT"])
    proj = impact.project_event_impact(ev)
    assert {"ticker": "MSFT", "materiality": "direct"} in proj["exposures"]


def test_second_order_materiality_via_co_theme_never_promoted_to_direct():
    # Narrow theme + MIN_SUPPORT met: second_order labelled, never upgraded.
    earn1 = _ev("e1", "2026-08-30", source="earnings", kind="earnings",
                tickers=["NVDA"], themes=["ai_capex"])
    earn2 = _ev("e2", "2026-08-31", source="earnings", kind="earnings",
                tickers=["NVDA"], themes=["ai_capex"])
    report = _ev("r1", "2026-09-02", source="research_vault", tickers=[],
                  themes=["ai_capex"])
    projections = {p["event_id"]: p for p in impact.project_events_impact(
        [earn1, earn2, report])}
    report_proj = projections[report["id"]]
    nvda_exp = next(e for e in report_proj["exposures"] if e["ticker"] == "NVDA")
    assert nvda_exp["materiality"] == "second_order"
    assert sorted(nvda_exp["source_event_ids"]) == sorted([earn1["id"], earn2["id"]])
    assert not any(e["ticker"] == "NVDA" and e["materiality"] == "direct"
                   for e in report_proj["exposures"])


def test_second_order_requires_minimum_support_and_carries_k1_evidence():
    earn1 = _ev("e1b", "2026-08-30", source="earnings", kind="earnings",
                tickers=["NVDA"], themes=["ai_capex"])
    earn2 = _ev("e2b", "2026-08-31", source="earnings", kind="earnings",
                tickers=["NVDA"], themes=["ai_capex"])
    report = _ev("r1b", "2026-09-02", source="research_vault", tickers=[],
                  themes=["ai_capex"])
    projections = {p["event_id"]: p for p in impact.project_events_impact(
        [earn1, earn2, report])}
    report_proj = projections[report["id"]]
    nvda_exp = next(e for e in report_proj["exposures"] if e["ticker"] == "NVDA")
    assert nvda_exp["materiality"] == "second_order"
    assert sorted(nvda_exp["source_event_ids"]) == sorted([earn1["id"], earn2["id"]])


def test_second_order_needs_minimum_support_single_co_theme_event_is_dropped():
    earn = _ev("e1c", "2026-08-30", source="earnings", tickers=["NVDA"], themes=["ai_capex"])
    report = _ev("r1c", "2026-09-01", source="research_vault", tickers=[], themes=["ai_capex"])
    projections = {p["event_id"]: p for p in impact.project_events_impact([earn, report])}
    assert projections[report["id"]]["exposures"] == []


def test_broad_theme_second_order_fails_closed_not_ranked():
    # BLOCKER 1: corpus-dominant theme ("earnings") must not propagate
    # second-order exposures via co-mention count / alphabetical top-N.
    supporters = []
    # 40 events under "earnings" + 1 under a narrow theme so earnings share
    # is well above SECOND_ORDER_THEME_MAX_SHARE (5%).
    for i in range(40):
        supporters.append(_ev(f"earn-{i}", "2026-08-01", source="earnings",
                              tickers=[f"T{i % 5}"], themes=["earnings"]))
    report = _ev("rv-broad", "2026-09-01", source="research_vault", tickers=[],
                  themes=["earnings"])
    projections = {p["event_id"]: p for p in impact.project_events_impact(
        supporters + [report])}
    proj = projections[report["id"]]
    assert proj["exposures"] == []
    assert "earnings" in proj["second_order_theme_refused"]
    assert proj["second_order_theme_refused_reason"] == (
        impact.SECOND_ORDER_THEME_TOO_BROAD_REASON)


def test_broad_theme_fails_closed_through_glance_surface_window():
    # MAJOR 1: eligibility must be computed over the FULL corpus, not the
    # bounded glance window -- 24 events can never reach the broad-theme
    # min count (40) on their own, so the corpus-dominant "earnings" theme
    # must still be refused when routed through glance_consequence_surface.
    # The ticker-less vault note is not a glance consequence (R1); the
    # fail-closed is asserted on the projection, and the glance row for a
    # named-ticker event in the same window carries no second-order leak.
    corpus = []
    for i in range(45):
        corpus.append(_ev(f"earn-g-{i}", "2026-08-01", source="earnings",
                           tickers=[f"G{i % 5}"], themes=["earnings"]))
    report = _ev("rv-glance-broad", "2026-09-01", source="research_vault",
                  tickers=[], themes=["earnings"])
    named = [
        _ev("named-g1", "2026-09-01", source="earnings",
            tickers=["NAMED"], themes=["earnings"]),
        _ev("named-g2", "2026-09-01", source="earnings",
            tickers=["NAME2"], themes=["earnings"]),
        _ev("named-g3", "2026-09-01", source="earnings",
            tickers=["NAME3"], themes=["earnings"]),
    ]
    corpus.extend([report, *named])
    surface = impact.glance_consequence_surface(corpus, limit=24)
    assert all(r["event_id"] != report["id"] for r in surface["rows"])
    projections = {p["event_id"]: p for p in impact.project_events_impact(
        corpus, eligible_themes=impact._eligible_themes(corpus))}
    assert "earnings" in projections[report["id"]]["second_order_theme_refused"]
    named_row = next(r for r in surface["rows"] if r["event_id"] == named[0]["id"])
    assert named_row["second_order_tickers"] == []


def test_second_order_ambiguous_cap_refuses_all_and_prints_dropped_count():
    # MAJOR 7 + no opaque ranker: when > MAX candidates remain on a narrow
    # theme, refuse ALL second-order and print candidate/dropped counts.
    supporters = []
    for i in range(12):
        for dup in range(2):
            supporters.append(_ev(f"s{i}-{dup}", "2026-08-01",
                                    source="earnings", tickers=[f"T{i}"],
                                    themes=["narrow_supply"]))
    ticker_less = _ev("tl-1", "2026-09-01", source="research_vault", tickers=[],
                       themes=["narrow_supply"])
    projections = {p["event_id"]: p for p in impact.project_events_impact(
        supporters + [ticker_less])}
    proj = projections[ticker_less["id"]]
    assert proj["exposures"] == []
    assert proj["second_order_truncated"] is True
    assert proj["second_order_truncated_reason"] == impact.SECOND_ORDER_AMBIGUOUS_REASON
    assert proj["second_order_candidate_count"] == 12
    assert proj["second_order_dropped_count"] == 12


def test_direct_wins_when_ticker_is_both_direct_and_second_order():
    # Exercise project_event_impact's dedup branch directly (not only the
    # project_events_impact path that drops own tickers before the call).
    ev = _ev("x-4", "2026-09-01", tickers=["NVDA"], themes=["ai_capex"])
    proj = impact.project_event_impact(
        ev,
        second_order_tickers=["NVDA", "AMD"],
        second_order_sources={"NVDA": ["cev-other"], "AMD": ["cev-other2"]},
    )
    nvda = [e for e in proj["exposures"] if e["ticker"] == "NVDA"]
    assert nvda == [{"ticker": "NVDA", "materiality": "direct"}]
    assert {"ticker": "AMD", "materiality": "second_order",
            "source_event_ids": ["cev-other2"]} in proj["exposures"]


def test_second_order_never_leaks_from_a_future_event_point_in_time():
    future = _ev("fut", "2026-12-31", source="earnings", tickers=["NVDA"], themes=["ai_capex"])
    earlier1 = _ev("e1d", "2026-08-30", source="earnings", tickers=["AMD"], themes=["ai_capex"])
    earlier2 = _ev("e2d", "2026-08-31", source="research_vault", tickers=[], themes=["ai_capex"])
    # Need a second prior AMD naming so MIN_SUPPORT is the only reason NVDA
    # stays out -- future must not contribute.
    earlier3 = _ev("e3d", "2026-08-29", source="earnings", tickers=["AMD"], themes=["ai_capex"])
    projections = {p["event_id"]: p for p in impact.project_events_impact(
        [future, earlier1, earlier2, earlier3])}
    earlier_proj = projections[earlier2["id"]]
    assert not any(e["ticker"] == "NVDA" for e in earlier_proj["exposures"])


def test_evidence_fields_are_carried_not_dropped():
    ev = _ev("x-7", "2026-09-01", tickers=["AAPL"])
    proj = impact.project_event_impact(ev)
    assert proj["source_ref"] == ev["source_ref"]
    assert proj["links"] == ev["links"]
    assert proj["facts"] == ev["facts"]
    assert proj["title"] == ev["title"]


def test_retracted_event_reports_typed_state_and_empties_exposures():
    ev = _ev("x-8", "2026-09-01", tickers=["AAPL"])
    proj = impact.project_event_impact(ev, retracted=True, retraction_reason="quarantined")
    assert proj["state"] == "retracted"
    assert proj["retraction_reason"] == "quarantined"
    assert proj["exposures"] == []


def test_active_event_reports_active_state():
    ev = _ev("x-9", "2026-09-01", tickers=["AAPL"])
    proj = impact.project_event_impact(ev)
    assert proj["state"] == "active"
    assert proj["retraction_reason"] is None


def test_causal_label_never_exceeds_uncalibrated_association():
    ev = _ev("x-10", "2026-09-01", tickers=["TSLA"], kind="signal_close")
    proj = impact.project_event_impact(ev)
    assert proj["causal_label"] == "uncalibrated_association"
    assert "causal" != proj["causal_label"]


def test_calibrated_impact_absent_and_reason_given_k5_gated():
    ev = _ev("x-11", "2026-09-01", tickers=["AMZN"])
    proj = impact.project_event_impact(ev)
    assert proj["calibrated_impact"] is None
    assert proj["calibrated_impact_reason"] == "not_yet_knowable_k5_gated"


def test_family_grouping_reads_spine_source_field_per_event_family():
    ev1 = _ev("a-1", "2026-09-01", source="earnings", tickers=["A"])
    ev2 = _ev("b-1", "2026-09-01", source="research_vault", tickers=["B"])
    ev3 = _ev("a-2", "2026-09-02", source="earnings", tickers=["C"])
    families = impact.project_family_impact([ev1, ev2, ev3])
    assert set(families.keys()) == {"earnings", "research_vault"}
    assert len(families["earnings"]) == 2
    assert len(families["research_vault"]) == 1


def test_deterministic_byte_stable_across_repeated_projection():
    events = [
        _ev("a-1", "2026-09-01", tickers=["A"], themes=["x"]),
        _ev("b-1", "2026-09-02", tickers=[], themes=["x"]),
    ]
    first = impact.project_events_impact(list(events))
    second = impact.project_events_impact(list(events))
    assert first == second


def test_empty_event_list_yields_no_projections_no_crash():
    assert impact.project_events_impact([]) == []
    assert impact.project_family_impact([]) == {}


def test_glance_consequence_surface_explicitly_does_not_serve_market_feed():
    # BLOCKER 3 / MO-DELTA-001: real consumer surface + explicit non-Market-Feed.
    # Three named events so the glance clears the fail-closed floor.
    events = [
        _ev("a-1", "2026-09-01", source="earnings", tickers=["A"]),
        _ev("a-2", "2026-09-02", source="earnings", tickers=["B"]),
        _ev("a-3", "2026-09-03", source="earnings", tickers=["C"]),
    ]
    surface = impact.glance_consequence_surface(events)
    assert surface["served_as_market_feed"] is False
    assert surface["market_feed_disposition"] == "explicitly_does_not_serve_market_feed"
    assert surface["event_count"] == 3
    assert surface["empty_kind"] is None
    assert [r["direct_tickers"] for r in surface["rows"]] == [["C"], ["B"], ["A"]]
    assert surface["rows"][0]["calibrated_impact"] is None


def test_glance_consequence_surface_null_on_empty():
    surface = impact.glance_consequence_surface([])
    assert surface["rows"] == []
    assert surface["stance_en"] == "Not available yet"
    assert surface["served_as_market_feed"] is False


def test_plain_glance_titles_strip_ledger_enums():
    """Front-end clarity: glance titles never print T1_HIT / BULL / EXPIRED."""
    en, zh = impact.plain_glance_titles({
        "title": "Prophet close: FBRT BULL → T1_HIT (+10.8% in 25d)",
        "source": "prophet_ledger",
        "exposures": [{"ticker": "FBRT", "materiality": "direct"}],
    })
    assert "T1_HIT" not in en and "T1_HIT" not in zh
    assert "BULL" not in en and "BULL" not in zh
    assert "FBRT" in en and "FBRT" in zh
    assert "hit first target" in en
    assert "达到首个目标" in zh

    en2, zh2 = impact.plain_glance_titles({
        "title": "CANADA regime: Q3 Stagflation → Q2 Reflation",
        "source": "regime_flip",
        "exposures": [],
    })
    assert "Q3" not in en2 and "Q2" not in en2
    assert en2 == "Canada's macro backdrop turned from stagflation to reflation"
    assert zh2 == "加拿大宏观环境由滞胀转向再通胀"
    assert "regime" not in en2.lower()
    assert "体制切换" not in zh2

    extras = [
        _ev("p-2", "2026-09-01", source="earnings", tickers=["AAA"]),
        _ev("p-3", "2026-09-01", source="earnings", tickers=["BBB"]),
    ]
    prophet = {
        **_ev("p-1", "2026-09-01", source="prophet_ledger", tickers=["FBRT"]),
        "title": "Prophet close: FBRT BULL → EXPIRED (-2.1% in 45d)",
        "kind": "signal_close",
    }
    surface = impact.glance_consequence_surface([prophet, *extras])
    assert all(r["family"] != "prophet_ledger" for r in surface["rows"])
    assert {r["direct_tickers"][0] for r in surface["rows"]} == {"AAA", "BBB"}


def test_no_write_family_impact_helper_on_module():
    # BLOCKER 2: nightly writer removed — projection is read-time only.
    assert not hasattr(impact, "write_family_impact")


def test_project_events_impact_scale_stays_subsecond_on_2k_events():
    # MAJOR 5: bounded cost on a 2k-event fixture (dominant broad theme
    # refused; narrow theme stays small).
    events = []
    for i in range(1900):
        events.append(_ev(f"broad-{i}", f"2026-01-{(i % 28) + 1:02d}",
                          source="earnings", tickers=[f"B{i % 10}"],
                          themes=["earnings"]))
    for i in range(100):
        events.append(_ev(f"narrow-{i}", f"2026-02-{(i % 28) + 1:02d}",
                          source="research_vault", tickers=[f"N{i % 3}"],
                          themes=["narrow_supply"]))
    t0 = time.perf_counter()
    out = impact.project_events_impact(events)
    elapsed = time.perf_counter() - t0
    assert len(out) == 2000
    assert elapsed < 2.0, f"projection took {elapsed:.3f}s on 2k events"


def test_earnings_call_mapped_tone_and_unmapped_tone_omit_clause():
    """BLOCKER 2: ZH must not assert 中性 when EN says a different tone."""
    en, zh = impact.plain_glance_titles({
        "title": "Earnings call: STDN Q2 FY2026 \u2014 confident",
        "source": "earnings_call",
        "exposures": [{"ticker": "STDN", "materiality": "direct"}],
    })
    assert en == "STDN earnings call — confident tone"
    assert zh == "STDN业绩电话会——基调有信心"
    assert "中性" not in zh

    en2, zh2 = impact.plain_glance_titles({
        "title": "Earnings call: ZZQ Q1 FY2026 \u2014 unclassified",
        "source": "earnings_call",
        "exposures": [{"ticker": "ZZQ", "materiality": "direct"}],
    })
    assert en2 == "ZZQ earnings call"
    assert zh2 == "ZZQ业绩电话会"
    assert "tone" not in en2.lower()
    assert "基调" not in zh2
    assert "中性" not in zh2
    assert "unclassified" not in en2


def test_macro_release_plain_series_labels_and_unmapped_fallback():
    """MAJOR 1: no raw series slug; unit is printed; unknown series falls back."""
    en, zh = impact.plain_glance_titles({
        "title": "Macro print: claims = +203 (2026-09-04)",
        "source": "macro_release",
        "exposures": [],
    })
    assert en == "Weekly jobless claims came in at +203k"
    assert zh == "每周初请失业金人数公布为+203k"

    en_ppi, zh_ppi = impact.plain_glance_titles({
        "title": "Macro print: ppi_finaldemand = -0.3 (2026-09-04)",
        "source": "macro_release",
        "exposures": [],
    })
    assert en_ppi == "Producer prices (final demand) came in at -0.3%"
    assert zh_ppi == "PPI最终需求公布为-0.3%"
    assert "ppi_finaldemand" not in en_ppi
    assert "ppi_finaldemand" not in zh_ppi

    en_unk, zh_unk = impact.plain_glance_titles({
        "title": "Macro print: mystery_print = 1.2 (2026-09-04)",
        "source": "macro_release",
        "exposures": [],
    })
    assert en_unk == "Macro data release"
    assert zh_unk == "宏观数据发布"
    assert "mystery_print" not in en_unk
    assert "mystery_print" not in zh_unk


def test_regime_and_risk_glance_use_plain_word_states():
    """MAJOR 2: title-case region; no Goldilocks/体制切换/金发女孩 leak."""
    en_hk, zh_hk = impact.plain_glance_titles({
        "title": "HK regime: Goldilocks → Growth-scare",
        "source": "regime_flip",
        "exposures": [],
    })
    assert en_hk == (
        "Hong Kong's macro backdrop turned from mild growth with low inflation "
        "to a growth scare"
    )
    assert zh_hk == "香港宏观环境由温和增长、低通胀转向增长担忧"
    assert "Goldilocks" not in en_hk
    assert "金发女孩" not in zh_hk
    assert "体制切换" not in zh_hk

    en_r, zh_r = impact.plain_glance_titles({
        "title": "Risk radar: calm → watch",
        "source": "risk_band",
        "exposures": [],
    })
    assert en_r == "Risk radar moved from calm to watch — stay selective"
    assert zh_r == "风险雷达由平静转为关注——保持谨慎选择"


def test_research_vault_glance_carries_subject_or_is_dropped():
    """MAJOR 3 + R1: ticker-less vault notes are not glance consequences.

    A named-ticker vault note still carries the house subject. A subject-less
    ticker-less row is dropped by the title guard; a ticker-less row with a
    subject is excluded by the exposure rule (it remains in the vault).
    """
    named = _ev("rv-named", "2026-09-01", source="research_vault",
                tickers=["HSBC"], themes=["china_property"])
    named["title"] = "GS: housing note"
    peers = [
        _ev("rv-p2", "2026-09-01", source="research_vault", tickers=["AAA"]),
        _ev("rv-p3", "2026-09-01", source="research_vault", tickers=["BBB"]),
    ]
    surface = impact.glance_consequence_surface([named, *peers])
    row = next(r for r in surface["rows"] if r["direct_tickers"] == ["HSBC"])
    assert row["title_en"] == "Research note on HSBC"
    assert row["title_zh"] == "关于HSBC的研究纪要"

    ev = _ev("rv-subj", "2026-09-01", source="research_vault", tickers=[],
             themes=["china_property"])
    ev["title"] = "GS: housing note"
    surface_subj = impact.glance_consequence_surface([ev])
    assert surface_subj["rows"] == []
    assert surface_subj["empty_kind"] == "no_named_exposure"

    empty = _ev("rv-empty", "2026-09-01", source="research_vault", tickers=[],
                themes=[])
    empty["title"] = "untitled blob with no house prefix"
    surface2 = impact.glance_consequence_surface([empty])
    assert surface2["rows"] == []
    assert surface2["empty_kind"] == "no_named_exposure"


def test_project_family_impact_threads_corpus_eligible_themes():
    """MINOR 1: window-only eligibility must not silently keep a broad theme."""
    corpus = []
    for i in range(45):
        corpus.append(_ev(f"earn-fam-{i}", "2026-08-01", source="earnings",
                           tickers=[f"G{i % 5}"], themes=["earnings"]))
    report = _ev("rv-fam", "2026-09-01", source="research_vault", tickers=[],
                 themes=["earnings"])
    corpus.append(report)
    window = [report]
    eligible = impact._eligible_themes(corpus)
    window_only = impact.project_family_impact(window)["research_vault"][0]
    threaded = impact.project_family_impact(
        window, eligible_themes=eligible)["research_vault"][0]
    assert "earnings" not in window_only.get("second_order_theme_refused", [])
    assert "earnings" in threaded.get("second_order_theme_refused", [])


def test_idless_co_theme_source_is_skipped_not_crashed():
    """MINOR 2: a missing source id must not TypeError at render time."""
    a = _ev("a-id", "2026-08-01", source="earnings", tickers=["TTT"],
            themes=["ai_capex"])
    b = _ev("b-id", "2026-08-01", source="earnings", tickers=["TTT"],
            themes=["ai_capex"])
    b["id"] = None
    target = _ev("t-id", "2026-09-01", tickers=[], themes=["ai_capex"])
    out = impact.project_events_impact([a, b, target])
    tgt = next(p for p in out if p["event_id"] == target["id"])
    seconds = [e for e in tgt["exposures"] if e.get("materiality") == "second_order"]
    assert seconds == []
    assert all(None not in (e.get("source_event_ids") or []) for e in tgt["exposures"])


def test_theme_keys_are_casefolded_for_support_floor():
    """MINOR 3: McElligott / Mcelligott must count as one theme for support."""
    a = _ev("mc-a", "2026-08-01", source="earnings", tickers=["NVDA"],
            themes=["McElligott"])
    b = _ev("mc-b", "2026-08-02", source="earnings", tickers=["NVDA"],
            themes=["Mcelligott"])
    c = _ev("mc-c", "2026-09-01", tickers=[], themes=["mcelligott"])
    projs = impact.project_events_impact([a, b, c])
    tgt = next(p for p in projs if p["event_id"] == c["id"])
    seconds = [e["ticker"] for e in tgt["exposures"]
               if e.get("materiality") == "second_order"]
    assert seconds == ["NVDA"]


def _named(ref, day, ticker):
    return _ev(ref, f"2026-09-{day:02d}", source="earnings", tickers=[ticker])


def test_glance_24_tickerless_research_notes_yield_typed_empty_and_zero_cards():
    """R1 (a): 24 ticker-less research notes are not consequences."""
    notes = []
    for i in range(24):
        ev = _ev(f"rv-empty-{i}", "2026-09-07", source="research_vault",
                 tickers=[], themes=[])
        ev["title"] = f"UBS: weekly note {i}"
        notes.append(ev)
    surface = impact.glance_consequence_surface(notes)
    assert surface["rows"] == []
    assert surface["empty_kind"] == "no_named_exposure"
    assert surface["reason_en"] == impact.EMPTY_NO_EXPOSURE_EN
    assert surface["reason_zh"] == impact.EMPTY_NO_EXPOSURE_ZH
    assert surface["stance_en"] is None
    assert surface["window_mode"] == impact.GLANCE_WINDOW_LAST_7


def test_glance_mixed_corpus_keeps_only_exposure_rows_newest_first_capped_at_8():
    """R1 (b): mixed corpus yields only exposure-bearing rows, newest first, cap 8."""
    notes = []
    for i in range(10):
        ev = _ev(f"rv-mix-{i}", "2026-09-07", source="research_vault", tickers=[])
        ev["title"] = f"MS: note {i}"
        notes.append(ev)
    named = [_named(f"earn-mix-{i}", 1 + i, f"T{i}") for i in range(10)]
    surface = impact.glance_consequence_surface(notes + named)
    assert surface["empty_kind"] is None
    assert len(surface["rows"]) == 8
    assert all(r["direct_tickers"] or r["second_order_tickers"] for r in surface["rows"])
    times = [r["event_time"] for r in surface["rows"]]
    assert times == sorted(times, reverse=True)
    assert all(r["family"] != "research_vault" for r in surface["rows"])
    assert surface["rows"][0]["direct_tickers"] == ["T9"]


def test_glance_7day_window_and_200_event_fallback_boundary():
    """R1 (c): 7-day as-of window excludes D-8; undated corpus falls back to 200."""
    recent = _named("win-recent", 7, "NEW")
    edge = _ev("win-edge", "2026-08-31", source="earnings", tickers=["EDGE"])
    too_old = _ev("win-old", "2026-08-30", source="earnings", tickers=["OLD"])
    filler = [_named("win-f1", 6, "F1"), _named("win-f2", 5, "F2")]
    surface = impact.glance_consequence_surface([recent, edge, too_old, *filler])
    ids = {r["event_id"] for r in surface["rows"]}
    assert recent["id"] in ids
    assert edge["id"] in ids
    assert too_old["id"] not in ids
    assert surface["window_mode"] == impact.GLANCE_WINDOW_LAST_7

    undated = []
    for i in range(210):
        ev = _ev(f"undated-{i:03d}", "2026-01-01",
                 source="earnings", tickers=[f"U{i}"])
        ev["date"] = "not-a-date"
        undated.append(ev)
    surface_fb = impact.glance_consequence_surface(undated)
    assert surface_fb["window_mode"] == impact.GLANCE_WINDOW_FALLBACK
    assert surface_fb["event_count"] == impact.GLANCE_FALLBACK_LIMIT
    assert len(surface_fb["rows"]) == 8
    assert all(r["direct_tickers"] for r in surface_fb["rows"])


def test_glance_plain_event_dates_never_raw_iso():
    """R3: card dates are '7 Sep 2026' / '2026年9月7日', never 2026-09-07."""
    events = [_named("d1", 7, "A"), _named("d2", 6, "B"), _named("d3", 5, "C")]
    surface = impact.glance_consequence_surface(events)
    row = next(r for r in surface["rows"] if r["event_time"] == "2026-09-07")
    assert row["event_time_en"] == "7 Sep 2026"
    assert row["event_time_zh"] == "2026年9月7日"
    assert impact._plain_event_date("2026-09-07") == ("7 Sep 2026", "2026年9月7日")
    assert impact._plain_event_date(None) == (None, None)
    assert impact._plain_event_date("bogus") == (None, None)


def test_unparsed_regime_risk_and_unknown_source_use_typed_pairs():
    """R4: unparsed regime/risk or unknown source → typed pair, never a placeholder."""
    en_r, zh_r = impact.plain_glance_titles({
        "title": "this line does not match the regime regex",
        "source": "regime_flip",
        "exposures": [],
    })
    assert en_r == "A regional macro backdrop changed"
    assert zh_r == "某一地区宏观环境发生变化"
    assert "prior state" not in zh_r
    assert "Market" not in zh_r
    assert "new state" not in zh_r

    en_k, zh_k = impact.plain_glance_titles({
        "title": "Risk desk moved sideways",
        "source": "risk_band",
        "exposures": [],
    })
    assert en_k == "Risk radar changed — stay selective"
    assert zh_k == "风险雷达已变化——保持谨慎选择"
    assert "prior" not in zh_k

    en_u, zh_u = impact.plain_glance_titles({
        "title": "BrandNewAdapter: raw ledger slug XYZ_FLIP",
        "source": "brand_new_adapter",
        "exposures": [{"ticker": "ZZZ", "materiality": "direct"}],
    })
    assert en_u == "Market event"
    assert zh_u == "市场事件"
    assert "BrandNewAdapter" not in en_u
    assert "XYZ_FLIP" not in en_u
    assert "XYZ_FLIP" not in zh_u

    unknown = {
        "id": "cev-brand_new_adapter-unk1",
        "ts": "2026-09-07T00:00:00Z",
        "date": "2026-09-07",
        "source": "brand_new_adapter",
        "source_ref": "unk-1",
        "kind": "report",
        "title": "BrandNewAdapter: raw ledger slug XYZ_FLIP",
        "facts": ["a fact"],
        "tickers": ["ZZZ"],
        "themes": [],
        "horizon_hint": "medium",
        "weight_hint": 1,
        "links": {"site": None, "source": None, "receipt": None},
    }
    peers = [_named("unk-2", 6, "AA"), _named("unk-3", 5, "BB")]
    surface = impact.glance_consequence_surface([unknown, *peers])
    assert all(r["family"] != "brand_new_adapter" for r in surface["rows"])
    assert {tuple(r["direct_tickers"]) for r in surface["rows"]} == {("AA",), ("BB",)}


def test_zh_glance_strings_have_no_internal_cjk_spaces():
    """R5: no ASCII space around the middot or inside ZH sentences on a card."""
    zh_earn = impact.plain_glance_titles({
        "title": "Earnings: AAPL actual vs est",
        "source": "earnings",
        "exposures": [{"ticker": "AAPL", "materiality": "direct"}],
    })[1]
    assert zh_earn == "AAPL公布业绩"
    assert " " not in zh_earn
    assert " ·" not in zh_earn and "· " not in zh_earn

    zh_macro = impact.plain_glance_titles({
        "title": "Macro print: claims = +215 (2026-07-09)",
        "source": "macro_release", "exposures": [],
    })[1]
    assert zh_macro == "每周初请失业金人数公布为+215k"
    assert " 公布" not in zh_macro
    assert " ·" not in zh_macro and "· " not in zh_macro

    ev = _ev("zh-earn-1", "2026-09-07", source="earnings", tickers=["AAPL"])
    surface = impact.glance_consequence_surface([ev])
    assert surface["rows"][0]["title_zh"] == "AAPL公布业绩"
    assert " " not in surface["rows"][0]["title_zh"]


def test_macro_regime_risk_without_exposure_yield_typed_empty():
    """NB-2: a corpus of only macro/regime/risk with no named exposure is empty."""
    macro = _ev("m-claims", "2026-09-04", source="macro_release", tickers=[])
    macro["title"] = "Macro print: claims = +206 (2026-09-03)"
    regime = _ev("r-ca", "2026-09-03", source="regime_flip", tickers=[])
    regime["title"] = "CANADA regime: Q1 Goldilocks → Q3 Stagflation"
    risk = _ev("k-watch", "2026-09-02", source="risk_band", tickers=[])
    risk["title"] = "Risk radar: calm → watch"
    vault = _ev("v-empty", "2026-09-07", source="research_vault", tickers=[])
    vault["title"] = "UBS: weekly note"
    surface = impact.glance_consequence_surface([macro, regime, risk, vault])
    assert surface["rows"] == []
    assert surface["empty_kind"] == "no_named_exposure"
    assert surface["reason_en"] == impact.EMPTY_NO_EXPOSURE_EN
    assert surface["reason_zh"] == impact.EMPTY_NO_EXPOSURE_ZH
    assert surface["stance_en"] is None
    assert not hasattr(impact, "GLANCE_NAMED_EXPOSURE_FAMILIES")


def test_prophet_ledger_is_typed_exclusion_from_glance():
    """NM-2: prophet_ledger is not a market event and never appears on the glance."""
    assert "prophet_ledger" in impact.GLANCE_EXCLUDED_FAMILIES
    assert "prophet_ledger" not in impact.GLANCE_ELIGIBLE_FAMILIES
    events = []
    for i, tk in enumerate(("FBRT", "DVA", "ROST")):
        ev = _ev(f"prop-{i}", "2026-09-04", source="prophet_ledger", tickers=[tk])
        ev["title"] = f"Prophet close: {tk} BULL → T1_HIT (+1.0% in 5d)"
        ev["kind"] = "signal_close"
        events.append(ev)
    events.append(_named("earn-keep", 7, "KEEP"))
    surface = impact.glance_consequence_surface(events)
    assert all(r["family"] != "prophet_ledger" for r in surface["rows"])
    assert [r["direct_tickers"] for r in surface["rows"]] == [["KEEP"]]
    assert surface["families"] == {"earnings": 1}


def test_glance_one_qualifying_row_renders():
    """NM-3: a single qualifying row is a card, not the empty state."""
    surface = impact.glance_consequence_surface([_named("solo", 7, "SOLO")])
    assert surface["empty_kind"] is None
    assert len(surface["rows"]) == 1
    assert surface["rows"][0]["direct_tickers"] == ["SOLO"]
    assert "size_en" not in surface["rows"][0]
    assert "size_zh" not in surface["rows"][0]
    assert surface["rows"][0]["note_en"] is None
    assert surface["window_label_en"] == "Events from 31 Aug to 7 Sep 2026"
    assert surface["window_label_zh"] == "2026年8月31日至9月7日的事件"


def test_glance_zero_qualifying_rows_typed_empty():
    """NM-3: the typed empty state appears only when ZERO rows qualify."""
    notes = []
    for i in range(4):
        ev = _ev(f"rv-zero-{i}", "2026-09-07", source="research_vault", tickers=[])
        ev["title"] = f"UBS: weekly note {i}"
        notes.append(ev)
    surface = impact.glance_consequence_surface(notes)
    assert surface["rows"] == []
    assert surface["empty_kind"] == "no_named_exposure"
    assert surface["reason_en"] == impact.EMPTY_NO_EXPOSURE_EN
    assert surface["reason_zh"] == impact.EMPTY_NO_EXPOSURE_ZH
    assert surface["window_label_en"] == "Events from 31 Aug to 7 Sep 2026"
    assert surface["window_label_zh"] == "2026年8月31日至9月7日的事件"


def test_glance_fallback_carries_latest_200_label():
    """NM-3: newest-200 fallback is labelled, never 'last 7 days'."""
    undated = []
    for i in range(210):
        ev = _ev(f"undated-fb-{i:03d}", "2026-01-01",
                 source="earnings", tickers=[f"U{i}"])
        ev["date"] = "not-a-date"
        undated.append(ev)
    surface = impact.glance_consequence_surface(undated)
    assert surface["window_mode"] == impact.GLANCE_WINDOW_FALLBACK
    assert surface["event_count"] == impact.GLANCE_FALLBACK_LIMIT
    assert surface["window_label_en"] == impact.WINDOW_FALLBACK_LABEL_EN
    assert surface["window_label_zh"] == impact.WINDOW_FALLBACK_LABEL_ZH
    assert surface["window_label_en"] == "Latest 200 recorded events"
    assert surface["window_label_zh"] == "最近记录的200个事件"
    assert len(surface["rows"]) == 8


def test_glance_earnings_row_with_ticker_has_no_size_slot():
    """NM-4: an earnings row with a ticker is one card and carries no size fields."""
    ev = _ev("earn-aapl", "2026-09-07", source="earnings", tickers=["AAPL"])
    ev["title"] = "Earnings: AAPL actual vs est"
    surface = impact.glance_consequence_surface([ev])
    assert surface["empty_kind"] is None
    assert len(surface["rows"]) == 1
    row = surface["rows"][0]
    assert row["direct_tickers"] == ["AAPL"]
    assert row["family"] == "earnings"
    assert "size_en" not in row
    assert "size_zh" not in row
    assert not hasattr(impact, "SIZE_UNAVAILABLE_EN")
    assert not hasattr(impact, "SIZE_UNAVAILABLE_ZH")
    assert surface["stance_en"] == impact.GLANCE_STANCE_EN
    assert surface["stance_zh"] == impact.GLANCE_STANCE_ZH


def test_glance_flip_series_collapses_to_latest_with_unstable_note():
    """NM-5: two flips of one series in the window collapse to the latest + note."""
    older = _ev("ca-old", "2026-08-31", source="regime_flip", tickers=["EWC"])
    older["title"] = "CANADA regime: Q1 Goldilocks → Q3 Stagflation"
    newer = _ev("ca-new", "2026-09-04", source="regime_flip", tickers=["EWC"])
    newer["title"] = "CANADA regime: Q3 Stagflation → Q2 Reflation"
    other = _ev("hk-one", "2026-09-03", source="regime_flip", tickers=["EWH"])
    other["title"] = "HK regime: Q2 Goldilocks → Q3 GrowthScare"
    surface = impact.glance_consequence_surface([older, newer, other])
    assert surface["empty_kind"] is None
    ca = [r for r in surface["rows"] if "Canada" in (r.get("title_en") or "")]
    hk = [r for r in surface["rows"] if "Hong Kong" in (r.get("title_en") or "")]
    assert len(ca) == 1
    assert len(hk) == 1
    assert ca[0]["event_time"] == "2026-09-04"
    assert ca[0]["note_en"] == impact.FLIP_UNSTABLE_EN
    assert ca[0]["note_zh"] == impact.FLIP_UNSTABLE_ZH
    assert ca[0]["note_en"] == "changed direction twice this week — unstable"
    assert ca[0]["note_zh"] == "本周两度转向——尚不稳定"
    assert hk[0]["note_en"] is None
    assert "size_en" not in ca[0]


def test_glance_flip_collapse_earlier_ticker_later_state():
    """NM-A (c1): two flips, only the earlier carries a ticker → later state + note."""
    older = _ev("ca-c1-old", "2026-09-02", source="regime_flip", tickers=["SPY"])
    older["title"] = "CANADA regime: Q1 Goldilocks → Q3 Stagflation"
    newer = _ev("ca-c1-new", "2026-09-05", source="regime_flip", tickers=[])
    newer["title"] = "CANADA regime: Q3 Stagflation → Q2 Reflation"
    surface = impact.glance_consequence_surface([older, newer])
    assert surface["empty_kind"] is None
    assert len(surface["rows"]) == 1
    row = surface["rows"][0]
    assert row["event_time"] == "2026-09-05"
    assert "reflation" in (row["title_en"] or "").lower()
    assert row["note_en"] == impact.FLIP_UNSTABLE_EN
    assert row["note_zh"] == impact.FLIP_UNSTABLE_ZH
    assert row["direct_tickers"] == ["SPY"]
    assert "size_en" not in row


def test_glance_flip_collapse_neither_ticker_yields_zero_rows():
    """NM-A (c2): two flips, neither carries a ticker → zero rows."""
    older = _ev("ca-c2-old", "2026-09-02", source="regime_flip", tickers=[])
    older["title"] = "CANADA regime: Q1 Goldilocks → Q3 Stagflation"
    newer = _ev("ca-c2-new", "2026-09-05", source="regime_flip", tickers=[])
    newer["title"] = "CANADA regime: Q3 Stagflation → Q2 Reflation"
    surface = impact.glance_consequence_surface([older, newer])
    assert surface["rows"] == []
    assert surface["empty_kind"] == "no_named_exposure"
    assert surface["reason_en"] == impact.EMPTY_NO_EXPOSURE_EN
    assert surface["reason_zh"] == impact.EMPTY_NO_EXPOSURE_ZH
