"""Deterministic synthetic fire rows for the aggregate tests (no market data, no RNG)."""
from datetime import date, timedelta

TICKERS = ("AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG")


def weekdays(n, start=date(2025, 6, 16)):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def synth_rows(n_dates=140, *, selector="EXHAUSTION_RECLAIM", horizon="60m", cost_bps=25, shift=0.0):
    rows = []
    for di, day in enumerate(weekdays(n_dates)):
        for ti, ticker in enumerate(TICKERS):
            if (di + ti) % 3 == 0:
                continue
            selected = ((di * 7 + ti * 3) % 11 - 4) / 1000.0 + shift
            controls_a = [((di + k * (ti + 1) + k) % 9 - 4) / 1000.0 for k in range(10 + (di % 3))]
            controls_b = controls_a[: len(controls_a) - (ti % 4)]
            row = {
                "selector": selector, "horizon": horizon, "cost_bps": cost_bps,
                "symbol": ticker, "date": day.isoformat(), "anchor_id": f"{ticker}:{day.isoformat()}",
                "candidate_bin": 19 + (di + ti) % 5, "decision_bin": 19 + (di + 2 * ti) % 6,
                "selected_return": selected,
                "selected_touch": "same_bar_ambiguous" if (di * 5 + ti) % 17 == 0 else "neither",
                "pool_availability": "AVAILABLE", "pool_reason": None,
                "matched_count": len(controls_a),
                "control_returns_a": controls_a, "control_returns_b": controls_b,
            }
            if (di * 3 + ti) % 23 == 0:
                row.update(pool_availability="NO_CONTROL", pool_reason="matched_control_floor_not_met",
                           matched_count=4, control_returns_a=[], control_returns_b=[])
            if (di + ti * 5) % 29 == 0:
                row.update(pool_availability="NO_CONTROL", pool_reason="qqq_sign_unavailable",
                           matched_count=0, control_returns_a=[], control_returns_b=[])
            if (di * 2 + ti) % 31 == 0:
                row["selected_return"] = None
                row["selected_touch"] = None
            if (di + ti) % 37 == 0 and row["pool_availability"] == "AVAILABLE":
                row["control_returns_a"] = []
                row["control_returns_b"] = []
            rows.append(row)
    return rows

CFG = {
    "matched_control_min_rows": 10, "early_partition_end": "2025-10-10", "late_partition_start": "2025-10-13",
    "primary_selector": "EXHAUSTION_RECLAIM", "primary_horizon": "60m", "primary_cost_bps": 25,
    "selectors": ["BASE_FRESH_LOW", "EXHAUSTION_FORMING", "RECLAIM_ONLY", "EXHAUSTION_RECLAIM", "CONTINUATION_RISK"],
    "horizons": ["30m", "60m", "120m", "close"], "round_trip_cost_bps": [10, 25, 50],
    "prospective_candidate_gate": {"min_fires": 300, "min_distinct_dates": 100, "min_tickers": 6, "max_single_ticker_fire_share": 0.35},
}

import pytest

from scripts.research import terminal_tactical_r1b_aggregate as agg


def test_base_rows_reference_numbers():
    rows = synth_rows()
    ref = {
        "L-A": dict(
            fires_raw=653, fires_delta=574, dates_delta=140, tickers_delta=7,
            statistic=0.001160516774891775,
            interval=(0.0009849662472943724, 0.0013498170995670997),
            early_statistic=0.001162549019607843, late_statistic=0.0011573760330578513,
            control_evidence_unavailable=14, ticker_share_delta_max=0.14634146341463414,
        ),
        "L-B": dict(
            fires_raw=653, fires_delta=574, dates_delta=140, tickers_delta=7,
            statistic=0.0011332337662337663,
            interval=(0.0009596157399891775, 0.0013164094967532468),
            early_statistic=0.0011320730837789661, late_statistic=0.0011350275482093664,
            control_evidence_unavailable=14, ticker_share_delta_max=0.14634146341463414,
        ),
        "S-A": dict(
            fires_raw=653, fires_delta=574, dates_delta=140, tickers_delta=7,
            statistic=0.001160516774891775,
            interval=(0.0009849662472943724, 0.0013498170995670997),
            early_statistic=0.001162549019607843, late_statistic=0.0011573760330578513,
            control_evidence_unavailable=14, ticker_share_delta_max=0.14634146341463414,
        ),
        "S-B": dict(
            fires_raw=653, fires_delta=328, dates_delta=135, tickers_delta=6,
            statistic=0.001354253647586981,
            interval=(0.0008784750833873494, 0.0018168552662203253),
            early_statistic=0.001402790096082779, late_statistic=0.0012791595197255575,
            control_evidence_unavailable=260, ticker_share_delta_max=0.25609756097560976,
        ),
    }
    for reading, exp in ref.items():
        s = agg.cell_summary(rows, reading, cfg=CFG, with_interval=True)
        for k, v in exp.items():
            if k == "interval":
                assert s["interval"][0] == pytest.approx(v[0], abs=1e-15)
                assert s["interval"][1] == pytest.approx(v[1], abs=1e-15)
            else:
                assert s[k] == pytest.approx(v, abs=1e-15) if isinstance(v, float) else s[k] == v
        assert s["no_control"] == 50
        assert s["selected_censored"] == 21
        assert s["no_control_and_censored"] == 6
        assert s["ambiguous_touch"] == 37
        assert s["ticker_share_raw_max"] == pytest.approx(0.1439509954058193, abs=1e-15)


def test_gate_passes_only_when_every_reading_passes():
    g = agg.gate(synth_rows(), cfg=CFG)
    for r in agg.READINGS:
        assert g["readings"][r]["mechanical_pass"] is True
        assert g["readings"][r]["bullet_5_admission_artifact"] == "REQUIRES_ADJUDICATION"
    assert g["mechanical_pass_all_readings"] is True
    assert g["disposition"] == "PROSPECTIVE_CANDIDATE_PENDING_ARTIFACT_ADJUDICATION"

    g2 = agg.gate(synth_rows(n_dates=120), cfg=CFG)
    for r in ("L-A", "L-B", "S-A"):
        assert g2["readings"][r]["mechanical_pass"] is True
    assert g2["readings"]["S-B"]["mechanical_pass"] is False
    assert g2["readings"]["S-B"]["bullet_1_counts"] is False
    assert g2["readings"]["S-B"]["summary"]["fires_delta"] == 282
    assert g2["readings"]["S-B"]["summary"]["dates_delta"] == 116
    assert g2["mechanical_pass_all_readings"] is False
    assert g2["disposition"] == "NO_PROMOTION"


def test_negative_effect_fails_the_interval_bullet():
    g = agg.gate(synth_rows(shift=-0.0015), cfg=CFG)
    for r in agg.READINGS:
        assert g["readings"][r]["bullet_2_interval"] is False
    la = g["readings"]["L-A"]["summary"]["interval"]
    assert la[0] == pytest.approx(-0.0005150337527056277, abs=1e-15)
    assert la[1] == pytest.approx(-0.00015018290043290034, abs=1e-15)
    sb = g["readings"]["S-B"]["summary"]["interval"]
    assert sb[0] == pytest.approx(-0.0006215249166126505, abs=1e-15)
    assert sb[1] == pytest.approx(0.00031685526622032514, abs=1e-15)
    assert g["disposition"] == "NO_PROMOTION"


def test_partition_signs_must_agree():
    g = agg.gate(synth_rows(shift=-0.00116), cfg=CFG)
    la = g["readings"]["L-A"]
    assert la["summary"]["early_statistic"] == pytest.approx(2.549019607843235e-06, abs=1e-15)
    assert la["summary"]["late_statistic"] == pytest.approx(-2.6239669421486885e-06, abs=1e-15)
    assert la["bullet_3_partition_sign"] is False
    assert g["readings"]["S-B"]["bullet_3_partition_sign"] is True


def test_single_ticker_concentration_fails_bullet_4():
    rows = synth_rows()
    for row in rows:
        if row["symbol"] in ("BBB", "CCC", "DDD"):
            row["symbol"] = "AAA"
    la = agg.gate(rows, cfg=CFG)["readings"]["L-A"]
    s = la["summary"]
    assert s["ticker_share_raw_max"] == pytest.approx(0.5712098009188361, abs=1e-15)
    assert s["ticker_share_delta_max"] == pytest.approx(0.5679442508710801, abs=1e-15)
    assert s["tickers_delta"] == 4
    assert la["bullet_4_concentration"] is False
    assert la["bullet_1_counts"] is False


def test_bootstrap_uses_a_fresh_generator_each_call():
    rows = synth_rows()
    pairs = []
    for r in rows:
        d = agg.event_delta(r, "L-A", floor=CFG["matched_control_min_rows"])
        if d is not None:
            pairs.append((r["date"], d))
    means = agg.date_means(pairs)
    a = agg.bootstrap_interval(means)
    b = agg.bootstrap_interval(means)
    assert a == b
    t1 = agg.cell_summary(rows, "L-A", cfg=CFG, with_interval=True)["interval"]
    assert a == t1


def test_empty_series_has_no_interval_and_fails():
    assert agg.bootstrap_interval([]) is None
    g = agg.gate([], cfg=CFG)
    for r in agg.READINGS:
        assert g["readings"][r]["mechanical_pass"] is False
    assert g["disposition"] == "NO_PROMOTION"
    s = agg.cell_summary([], "L-A", cfg=CFG, with_interval=True)
    assert s["statistic"] is None
    assert s["no_control_fraction"] is None
    assert s["ticker_share_raw_max"] is None


def test_week_blocks_are_iso_weeks_in_order():
    assert agg.week_blocks([("2025-12-29", 1.0), ("2026-01-02", 2.0), ("2026-01-05", 3.0)]) == [
        [1.0, 2.0],
        [3.0],
    ]


def test_event_delta_rules():
    base = synth_rows(n_dates=1)[0].copy()
    base["pool_availability"] = "NO_CONTROL"
    assert agg.event_delta(base, "L-A", floor=10) is None
    base2 = base.copy()
    base2["pool_availability"] = "AVAILABLE"
    base2["selected_return"] = None
    assert agg.event_delta(base2, "L-A", floor=10) is None
    row = {
        "pool_availability": "AVAILABLE", "selected_return": 0.01,
        "control_returns_a": [0.0], "control_returns_b": [0.0],
    }
    assert agg.event_delta(row, "L-A", floor=10) == pytest.approx(0.01, abs=1e-15)
    assert agg.event_delta(row, "S-A", floor=10) is None
    row2 = {
        "pool_availability": "AVAILABLE", "selected_return": 0.05,
        "control_returns_a": [0.0] * 10, "control_returns_b": [0.0] * 9,
    }
    assert agg.event_delta(row2, "S-A", floor=10) == pytest.approx(0.05, abs=1e-15)
    assert agg.event_delta(row2, "S-B", floor=10) is None
    mean_a = 0.0
    assert agg.event_delta(row2, "S-A", floor=10) == pytest.approx(0.05 - mean_a, abs=1e-15)


def test_zero_statistic_fails_the_sign_bullet():
    early_days = weekdays(60, start=date(2025, 6, 16))
    late_days = weekdays(60, start=date(2025, 10, 13))
    rows = []
    for day in early_days + late_days:
        rows.append({
            "selector": "EXHAUSTION_RECLAIM", "horizon": "60m", "cost_bps": 25,
            "symbol": "AAA", "date": day.isoformat(), "anchor_id": f"AAA:{day.isoformat()}",
            "candidate_bin": 19, "decision_bin": 19,
            "selected_return": 0.0, "selected_touch": "neither",
            "pool_availability": "AVAILABLE", "pool_reason": None, "matched_count": 10,
            "control_returns_a": [0.0] * 10, "control_returns_b": [0.0] * 10,
        })
    g = agg.gate(rows, cfg=CFG)
    for r in agg.READINGS:
        assert g["readings"][r]["bullet_3_partition_sign"] is False


def test_summarize_reports_all_sixty_cells():
    rows = synth_rows() + synth_rows(cost_bps=10) + synth_rows(cost_bps=50)
    out = agg.summarize(rows, cfg=CFG)
    assert len(out["cells"]) == 60
    assert out["cells"]["BASE_FRESH_LOW|30m|10"]["L-A"]["fires_raw"] == 0
    assert out["cells"]["EXHAUSTION_RECLAIM|60m|25"]["L-A"]["interval"] is not None
    assert out["cells"]["EXHAUSTION_RECLAIM|60m|10"]["L-A"]["interval"] is None
    assert out["cost_invariance"]["EXHAUSTION_RECLAIM|60m"]["L-A"] is True
    assert out["gates"]["EXHAUSTION_RECLAIM"]["gate_role"] == "prospective_candidate_gate"
    assert out["gates"]["RECLAIM_ONLY"]["gate_role"] == "comparator_only"
    assert out["gates"]["RECLAIM_ONLY"]["disposition"] is None
    assert out["may_rank"] is False and out["may_alert"] is False
    assert out["may_size"] is False and out["may_trade"] is False


def test_no_control_fraction_and_reasons():
    rows = synth_rows()
    s = agg.cell_summary(rows, "L-A", cfg=CFG, with_interval=True)
    assert s["no_control_fraction"] == pytest.approx(50 / 653, abs=1e-15)
    n1 = sum(1 for r in rows if r["pool_availability"] != "AVAILABLE" and r["pool_reason"] == "matched_control_floor_not_met")
    n2 = sum(1 for r in rows if r["pool_availability"] != "AVAILABLE" and r["pool_reason"] == "qqq_sign_unavailable")
    assert n1 + n2 == 50
    assert s["no_control_reasons"] == {
        "matched_control_floor_not_met": n1,
        "qqq_sign_unavailable": n2,
    }


def test_same_week_number_in_two_years_is_two_blocks():
    assert agg.week_blocks([("2025-06-16", 1.0), ("2026-06-15", 3.0)]) == [[1.0], [3.0]]


def test_interval_lower_bound_of_exactly_zero_fails():
    early_days = weekdays(60, start=date(2025, 6, 16))
    late_days = weekdays(60, start=date(2025, 10, 13))
    rows = []
    for day in early_days + late_days:
        rows.append({
            "selector": "EXHAUSTION_RECLAIM", "horizon": "60m", "cost_bps": 25,
            "symbol": "AAA", "date": day.isoformat(), "anchor_id": f"AAA:{day.isoformat()}",
            "candidate_bin": 19, "decision_bin": 19,
            "selected_return": 0.0, "selected_touch": "neither",
            "pool_availability": "AVAILABLE", "pool_reason": None, "matched_count": 10,
            "control_returns_a": [0.0] * 10, "control_returns_b": [0.0] * 10,
        })
    g = agg.gate(rows, cfg=CFG)
    for r in agg.READINGS:
        assert g["readings"][r]["summary"]["interval"] == (0.0, 0.0)
        assert g["readings"][r]["bullet_2_interval"] is False


def test_duplicate_event_cell_rows_are_refused():
    rows = synth_rows()
    with pytest.raises(ValueError, match="duplicate_event_cell_row"):
        agg.cell_summary(rows + [rows[0]], "L-A", cfg=CFG, with_interval=False)
    with pytest.raises(ValueError, match="duplicate_event_cell_row"):
        agg.summarize(rows + [rows[0]], cfg=CFG)


def test_ticker_share_is_gated_on_the_delta_set_too():
    def mk(t, i, avail=True):
        d = weekdays(40)[i]
        r = {
            "selector": "EXHAUSTION_RECLAIM", "horizon": "60m", "cost_bps": 25,
            "symbol": t, "date": d.isoformat(), "anchor_id": f"{t}:{d.isoformat()}",
            "candidate_bin": 19, "decision_bin": 19, "selected_return": 0.01,
            "selected_touch": "neither", "pool_availability": "AVAILABLE", "pool_reason": None,
            "matched_count": 10, "control_returns_a": [0.0] * 10, "control_returns_b": [0.0] * 10,
        }
        if not avail:
            r.update(
                pool_availability="NO_CONTROL", pool_reason="matched_control_floor_not_met",
                matched_count=4, control_returns_a=[], control_returns_b=[],
            )
        return r

    even = [mk("AAA", i) for i in range(7)] + [mk("BBB", i) for i in range(7)] + [mk("CCC", i) for i in range(6)]
    skew = (
        [mk("AAA", i) for i in range(7)]
        + [mk("BBB", i) for i in range(7)]
        + [mk("CCC", i, avail=(i >= 2)) for i in range(6)]
    )
    for rs in (even, skew):
        g = agg.gate(rs, cfg=CFG)
        for r in agg.READINGS:
            s = g["readings"][r]["summary"]
            assert s["ticker_share_raw_max"] == 0.35
    for r in agg.READINGS:
        s = agg.gate(even, cfg=CFG)["readings"][r]["summary"]
        assert s["ticker_share_delta_max"] == 0.35
        assert agg.gate(even, cfg=CFG)["readings"][r]["bullet_4_concentration"] is True
    for r in agg.READINGS:
        s = agg.gate(skew, cfg=CFG)["readings"][r]["summary"]
        assert s["ticker_share_delta_max"] == pytest.approx(7 / 18)
        assert agg.gate(skew, cfg=CFG)["readings"][r]["bullet_4_concentration"] is False


def test_cost_invariance_is_null_when_no_cell_has_a_statistic():
    assert agg.summarize([], cfg=CFG)["cost_invariance"]["EXHAUSTION_RECLAIM|60m"] == {
        "L-A": None, "L-B": None, "S-A": None, "S-B": None,
    }
