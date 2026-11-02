"""Policy Monitor display normalizer — discriminating unit coverage.

lib/policy_monitor_view.py is the PURE projection the Policy Monitor card and
dialog render from. These tests pin the behaviours the redesign had to fix in
the OLD template logic, and the robustness contract from the frozen packet
(research/policy_monitor/POLICY_MONITOR_UPGRADE_2026-11-01.md):

  * Unknown is never zero; a bool is never a numeric reading; NaN / infinity
    are never readings.
  * A missing arming block is "not observed", never "Quiet".
  * A missing state is UNKNOWN, never a silent QUIET.
  * A valid zero (n_7d = 0, n_30d = 0, days_to_midterm = 0) stays a zero.
  * The Fed-vs-market comparison appears only when the producer's own rule
    admits it (the legacy gap block is NOT basis-qualified by itself).
  * Fed dots are placed by their ACTUAL year-end date — never at a hardcoded
    m6 slot, never across a year rollover.
  * One bad section degrades on its own; the raw payload is never mutated.
"""
from __future__ import annotations

import copy
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import policy_monitor_view as pmv  # noqa: E402


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

def _policy_lever(**over) -> dict:
    base = {
        "schema": "policy_lever.v1",
        "as_of": "2026-10-30",
        "favored_complex": {
            "basket": ["SMH", "SOXX"],
            "basket_incomplete": False,
            "drawdown_pct": -24.95,
            "drawdown_z": -2.6,
            "as_of": "2026-10-30",
            "note": "Semis complex is -24.9% from the trailing-120-day peak.",
            "note_zh": "半导体组合距过去120日高点-24.9%。",
        },
        "jawboning": {
            "n_7d": 0,
            "n_30d": 12,
            "last_alert_ts": "2026-10-17T00:34:24+00:00",
            "last_alert_summary": "Trump signs Russia sanctions law then waives it.",
            "last_alert_summary_zh": "特朗普签署对俄制裁法案后几乎全部豁免。",
        },
        "calendar": {
            "days_to_midterm": 2,
            "context_note": "US midterm elections: 2 days (2026-11-03). Context only.",
            "context_note_zh": "美国中期选举：2天（2026年11月3日）。仅作背景参考。",
        },
        "levers": [
            {
                "name": "Iran / oil", "name_zh": "伊朗/石油", "asset": "CL=F",
                "arming": {"stoch_k": 88.47, "armed": False, "as_of": "2026-10-30"},
                "watch": "Middle East escalation is the transmission channel.",
                "watch_zh": "中东局势升级是传导通道。",
                "copy_as_of": "2026-07-18", "copy_age_days": 106, "copy_stale": True,
            },
            {
                "name": "China / tariffs", "name_zh": "中国/关税", "asset": None,
                "arming": None,
                "watch": "US-China trade friction is the policy channel.",
                "watch_zh": "中美贸易摩擦是政策渠道。",
                "copy_as_of": "2026-07-18", "copy_age_days": 106, "copy_stale": True,
            },
        ],
        "state": "ELEVATED",
        "framing": "Conditions, not intent, not timing.",
        "framing_zh": "条件，不是意图，也不是时点。",
    }
    base.update(over)
    return base


def _fed_path(**over) -> dict:
    base = {
        "asof": "2026-10-30",
        "policy_rate": 3.88,
        "target_low": 3.75,
        "target_high": 4.0,
        "target_mid": 3.88,
        "implied": {"now": 3.88, "m1": 3.88, "m3": 4.04, "m6": 4.23, "m12": 4.44},
        "implied_source_en": "ZQ fed-funds futures",
        "implied_source_zh": "ZQ 联邦基金期货",
        "implied_bp_12m": 56,
        "implied_cuts_12m": -2,
        "dots": [{"year": 2026, "median": 4.1}, {"year": 2027, "median": 4.1}],
        "gap": {
            "horizon_label": "end-2026", "horizon_months": 2,
            "fed_dot": 4.1, "market": 3.96, "gap_bp": -14,
            "lean_en": "market more dovish than the Fed",
            "lean_zh": "市场比美联储更鸽派",
        },
        "headline_en": "Market prices ~2 hikes over the next 12m",
        "read_en": "At end-2026 the market implies 3.96% vs the Fed's 4.10% median dot.",
        "implied_source_meta": {
            "schema": "fed_path_source_meta.v1",
            "selected_strip": "zq",
            "selected_is_effr": True,
            "strips": {
                "zq": {
                    "source": "rate_futures:ZQ", "rate_index": "EFFR",
                    "observation_time": "2026-10-30", "value_state": "present",
                    "limitations": ["vendor_close_not_exchange_settlement"],
                },
            },
            "dots": {
                "source": "fred:FEDTARMD",
                "target": "sep_fed_funds_year_end_median",
                "target_epoch": "2026-12-31",
                "vintage": "2026-03-18", "value_state": "present",
                "limitations": [],
            },
            "gap": {
                "rule_id": "sep_vs_market_year_end.v1",
                "status": "comparable_after_transformation",
                "reason": None, "transform": "year_end_interval_match",
                "market_horizon_months": 2,
                "market_reference_start": "2026-11-01",
                "market_reference_end": "2026-12-31",
                "limitations": [],
            },
        },
    }
    base.update(over)
    base["implied_source_meta"]["strips"]["zq"]["observation_time"] = base["asof"]
    return base


def _latest(**over) -> dict:
    base = {
        "date": "2026-10-30",
        "fed_path": _fed_path(),
        "fed_stance": {
            "stance": "hawkish", "label_en": "Hawkish", "label_zh": "鹰派",
            "guidance": "unknown",
            "market_vs_fed_en": "market more dovish than the Fed",
            "market_vs_fed_bp": -14,
            "drivers_en": ["market prices ~2.0 hike(s) over 12m"],
            "drivers_zh": ["市场计入未来12个月约2.0次加息"],
        },
    }
    base.update(over)
    return base


# --------------------------------------------------------------------------- #
# state + conditions
# --------------------------------------------------------------------------- #

class TestState:
    def test_missing_state_is_unknown_not_quiet(self):
        """The old face defaulted a missing state to QUIET. It must be UNKNOWN."""
        v = pmv.build_view(_policy_lever(state=None), _latest())
        assert v["state"]["value"] == "UNKNOWN"
        assert v["state"]["known"] is False

    def test_absent_state_key_is_unknown_not_quiet(self):
        pl = _policy_lever()
        pl.pop("state")
        v = pmv.build_view(pl, _latest())
        assert v["state"]["value"] == "UNKNOWN"
        assert v["state"]["known"] is False

    def test_unrecognised_state_is_unknown(self):
        v = pmv.build_view(_policy_lever(state="BOOM"), _latest())
        assert v["state"]["value"] == "UNKNOWN"

    def test_reported_states_need_matching_dated_predicates(self):
        for s, dd, armed in (("ARMED", -25, True), ("ELEVATED", -25, False), ("QUIET", -5, False)):
            pl = _policy_lever(state=s)
            pl["favored_complex"]["drawdown_pct"] = dd
            pl["levers"][0]["arming"]["armed"] = armed
            v = pmv.build_view(pl, _latest())
            assert v["state"]["value"] == s
            assert v["state"]["known"] is True

    def test_state_never_claims_observed_market_repricing(self):
        """ARMED is a condition state; it must not be renamed as repricing."""
        v = pmv.build_view(_policy_lever(state="ARMED"), _latest())
        blob = (v["state"]["summary_en"] + v["state"]["summary_zh"]
                + v["state"]["stance_en"] + v["state"]["stance_zh"]).lower()
        assert "repric" not in blob
        assert "重定价" not in v["state"]["summary_zh"] + v["state"]["stance_zh"]

    def test_conditions_are_reported_individually(self):
        v = pmv.build_view(_policy_lever(), _latest())
        legs = {c["key"]: c for c in v["conditions"]}
        assert legs["drawdown"]["met"] is True      # -24.95% is past the -15% leg
        assert legs["arming"]["met"] is False       # one observed lever, not armed
        assert legs["arming"]["known"] is True

    def test_condition_met_is_unknown_when_the_drawdown_is_missing(self):
        pl = _policy_lever()
        pl["favored_complex"]["drawdown_pct"] = None
        v = pmv.build_view(pl, _latest())
        legs = {c["key"]: c for c in v["conditions"]}
        assert legs["drawdown"]["known"] is False
        assert legs["drawdown"]["met"] is None


# --------------------------------------------------------------------------- #
# recorded policy alerts — a valid zero stays a zero
# --------------------------------------------------------------------------- #

class TestRecordedActivity:
    def test_zero_7d_count_is_preserved(self):
        """The old face used truthiness, so n_7d = 0 hid the chip entirely."""
        v = pmv.build_view(_policy_lever(), _latest())
        assert v["activity"]["known_7d"] is True
        assert v["activity"]["n_7d"] == 0

    def test_zero_30d_count_is_preserved(self):
        """The old dialog used `n_30d or '—'`, so a valid 0 became an em dash."""
        pl = _policy_lever()
        pl["jawboning"]["n_30d"] = 0
        v = pmv.build_view(pl, _latest())
        assert v["activity"]["known_30d"] is True
        assert v["activity"]["n_30d"] == 0

    def test_absent_counts_are_unknown_not_zero(self):
        pl = _policy_lever()
        pl["jawboning"] = {"_note": "whitehouse/alerts.jsonl absent"}
        v = pmv.build_view(pl, _latest())
        assert v["activity"]["known_7d"] is False
        assert v["activity"]["n_7d"] is None
        assert v["activity"]["known_30d"] is False
        assert v["activity"]["n_30d"] is None

    def test_bool_count_is_not_a_number(self):
        pl = _policy_lever()
        pl["jawboning"]["n_7d"] = True
        v = pmv.build_view(pl, _latest())
        assert v["activity"]["known_7d"] is False
        assert v["activity"]["n_7d"] is None

    def test_counts_are_never_labelled_fed_speeches(self):
        """The producer counts recorded whitehouse alerts, not Fed speeches."""
        v = pmv.build_view(_policy_lever(), _latest())
        blob = (v["activity"]["count_label_en"] + v["activity"]["count_label_zh"]
                + v["activity"]["last_alert_label_en"]
                + v["activity"]["last_alert_label_zh"]).lower()
        assert "speech" not in blob
        assert "演讲" not in blob and "讲话" not in blob

    def test_fed_communication_is_called_out_separately(self):
        v = pmv.build_view(_policy_lever(), _latest())
        assert "fed communication" in v["activity"]["fed_communication_label_en"].lower()

    def test_last_alert_is_dated(self):
        v = pmv.build_view(_policy_lever(), _latest())
        assert v["activity"]["last_alert"]["date"] == "2026-10-17"


# --------------------------------------------------------------------------- #
# transmission rows — observed state vs hypothesis
# --------------------------------------------------------------------------- #

class TestTransmission:
    def test_missing_arming_is_unavailable_not_quiet(self):
        """The old dialog rendered a missing arming block as 'Quiet'."""
        v = pmv.build_view(_policy_lever(), _latest())
        china = v["transmission"][1]
        assert china["observed"]["known"] is False
        assert china["observed"]["state"] == "unavailable"
        assert china["observed"]["label_en"] != "Quiet"

    def test_explicit_false_arming_is_quiet(self):
        v = pmv.build_view(_policy_lever(), _latest())
        oil = v["transmission"][0]
        assert oil["observed"]["known"] is True
        assert oil["observed"]["state"] == "quiet"

    def test_arming_true_is_armed(self):
        pl = _policy_lever()
        pl["levers"][0]["arming"]["armed"] = True
        v = pmv.build_view(pl, _latest())
        assert v["transmission"][0]["observed"]["state"] == "armed"

    def test_arming_flag_missing_is_unavailable(self):
        pl = _policy_lever()
        pl["levers"][0]["arming"] = {"stoch_k": 40.0}
        v = pmv.build_view(pl, _latest())
        assert v["transmission"][0]["observed"]["known"] is False
        assert v["transmission"][0]["observed"]["state"] == "unavailable"

    def test_non_bool_arming_flag_is_refused(self):
        pl = _policy_lever()
        pl["levers"][0]["arming"]["armed"] = "yes"
        v = pmv.build_view(pl, _latest())
        assert v["transmission"][0]["observed"]["known"] is False
        assert v["transmission"][0]["observed"]["state"] == "unavailable"

    def test_gauge_geometry_is_clamped(self):
        pl = _policy_lever()
        pl["levers"][0]["arming"]["stoch_k"] = 150.0
        v = pmv.build_view(pl, _latest())
        g = v["transmission"][0]["observed"]["gauge"]
        assert g["known"] is True
        assert g["value"] == 100.0
        assert g["clamped"] is True

    def test_negative_gauge_is_clamped_to_zero(self):
        pl = _policy_lever()
        pl["levers"][0]["arming"]["stoch_k"] = -20.0
        v = pmv.build_view(pl, _latest())
        g = v["transmission"][0]["observed"]["gauge"]
        assert g["value"] == 0.0
        assert g["clamped"] is True

    def test_bool_gauge_is_not_a_number(self):
        pl = _policy_lever()
        pl["levers"][0]["arming"]["stoch_k"] = True
        v = pmv.build_view(pl, _latest())
        assert v["transmission"][0]["observed"]["gauge"]["known"] is False

    def test_hypothesis_is_kept_apart_from_the_observed_state(self):
        v = pmv.build_view(_policy_lever(), _latest())
        row = v["transmission"][0]
        assert row["hypothesis_en"]
        assert row["observed"]["label_en"]
        assert row["hypothesis_en"] != row["observed"]["label_en"]

    def test_stale_copy_is_flagged_with_its_date(self):
        v = pmv.build_view(_policy_lever(), _latest())
        assert v["transmission"][0]["copy_stale"] is True
        assert v["transmission"][0]["copy_as_of"] == "2026-07-18"

    def test_stale_copy_surfaces_in_the_evidence_notes(self):
        v = pmv.build_view(_policy_lever(), _latest())
        blob = " ".join(n["en"] for n in v["evidence"]["notes"])
        assert "2026-07-18" in blob


# --------------------------------------------------------------------------- #
# rates panel
# --------------------------------------------------------------------------- #

class TestRates:
    def test_points_carry_elapsed_months(self):
        v = pmv.build_view(_policy_lever(), _latest())
        months = [p["months"] for p in v["rates"]["points"]]
        assert months == [1.0, 3.0, 6.0, 12.0]

    def test_x_axis_is_elapsed_time_not_evenly_spaced(self):
        """0/1/3/6/12 must sit to scale — the old chart spaced them evenly."""
        v = pmv.build_view(_policy_lever(), _latest())
        ticks = {t["months"]: t["x"] for t in v["rates"]["chart"]["x_ticks"]}
        origin = v["rates"]["chart"]["x_min"]
        span = ticks[12.0] - origin
        assert ticks[1.0] - origin == pytest.approx(span / 12, rel=1e-3)
        assert ticks[3.0] - origin == pytest.approx(span / 4, rel=1e-3)
        assert ticks[6.0] - origin == pytest.approx(span / 2, rel=1e-3)
        # an even spacing would have put m3 at 1/4 of the way and m6 at 1/2 —
        # the distinguishing case is m1, which is at 1/12 and not 1/4
        assert ticks[1.0] != pytest.approx(ticks[3.0])

    def test_missing_horizon_is_a_gap_not_a_zero(self):
        fp = _fed_path()
        fp["implied"]["m3"] = None
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        row = {r["key"]: r for r in v["rates"]["table"]}
        assert row["m3"]["known"] is False
        assert row["m3"]["value"] == "not available"
        # m1 remains a standalone observation; only m6→m12 is joined.
        assert len(v["rates"]["chart"]["segments"]) == 1
        assert v["rates"]["chart"]["markers"][0]["months"] == 1
        assert [g["months"] for g in v["rates"]["chart"]["gaps"]] == [3.0]

    def test_non_finite_value_is_refused_as_a_reading(self):
        fp = _fed_path()
        fp["implied"]["m6"] = float("nan")
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        row = {r["key"]: r for r in v["rates"]["table"]}
        assert row["m6"]["known"] is False

    def test_infinite_value_is_refused_as_a_reading(self):
        fp = _fed_path()
        fp["implied"]["m6"] = float("inf")
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        row = {r["key"]: r for r in v["rates"]["table"]}
        assert row["m6"]["known"] is False

    def test_bool_rate_is_not_a_reading(self):
        fp = _fed_path()
        fp["implied"]["m6"] = True
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        row = {r["key"]: r for r in v["rates"]["table"]}
        assert row["m6"]["known"] is False

    def test_no_hike_count_is_asserted(self):
        """A rate-change equivalent must never be rendered as a number of hikes."""
        v = pmv.build_view(_policy_lever(), _latest())
        blob = (v["move_en"] + v["move_zh"]).lower()
        assert "hike" not in blob and "cut" not in blob
        assert "加息" not in blob and "降息" not in blob
        assert "bp" in v["move_en"].lower() or "基点" in v["move_zh"]

    def test_no_rate_path_is_not_reported_as_a_flat_path(self):
        fp = _fed_path()
        fp["implied"] = {}
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        assert v["rates"]["available"] is False
        assert v["rates"]["chart"]["segments"] == []


class TestFedDotPlacement:
    """Fed dots are year-end projections: place them by their ACTUAL date."""

    def _dot_x(self, months: float) -> float:
        ch = pmv._CHART
        x0, x1 = ch["pl"], ch["width"] - ch["pr"]
        return x0 + (months / 12.0) * (x1 - x0)

    def test_november_snapshot_does_not_use_the_m6_slot(self):
        """The old chart put every current-year dot at m6. In November 2026 the
        year-end dot is ~2 months out."""
        v = pmv.build_view(_policy_lever(), _latest())
        dot = v["rates"]["dots"][0]
        assert dot["on_axis"] is True
        assert dot["months"] == pytest.approx(2.03, abs=0.05)
        assert dot["x"] == pytest.approx(self._dot_x(dot["months"]), abs=0.5)
        assert dot["x"] != pytest.approx(self._dot_x(6.0), abs=2.0)

    def test_midyear_snapshot_places_the_dot_at_about_six_months(self):
        pl = _policy_lever(as_of="2026-06-30")
        lt = _latest(date="2026-06-30")
        lt["fed_path"] = _fed_path(asof="2026-06-30")
        v = pmv.build_view(pl, lt)
        dot = v["rates"]["dots"][0]
        assert dot["on_axis"] is True
        assert dot["months"] == pytest.approx(6.03, abs=0.05)

    def test_year_rollover_uses_the_new_years_target(self):
        pl = _policy_lever(as_of="2027-01-15")
        lt = _latest(date="2027-01-15")
        fp = _fed_path(asof="2027-01-15")
        fp["dots"] = [{"year": 2027, "median": 3.9}, {"year": 2028, "median": 3.6}]
        fp["implied_source_meta"]["dots"]["target_epoch"] = "2027-12-31"
        lt["fed_path"] = fp
        v = pmv.build_view(pl, lt)
        dot = v["rates"]["dots"][0]
        assert dot["year"] == 2027
        assert dot["on_axis"] is True
        assert dot["months"] == pytest.approx(11.5, abs=0.2)

    def test_dot_beyond_the_chart_horizon_is_tabulated_not_plotted(self):
        fp = _fed_path()
        fp["dots"] = [{"year": 2027, "median": 4.1}]
        fp["implied_source_meta"]["dots"]["target_epoch"] = "2027-12-31"
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        dot = v["rates"]["dots"][0]
        assert dot["on_axis"] is False
        assert v["rates"]["dots_on_axis"] == []

    def test_past_dot_is_never_plotted(self):
        fp = _fed_path()
        fp["dots"] = [{"year": 2025, "median": 4.4}]
        fp["implied_source_meta"]["dots"]["target_epoch"] = "2025-12-31"
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        assert v["rates"]["dots"][0]["on_axis"] is False

    def test_dot_without_a_recorded_target_epoch_is_tabulated(self):
        fp = _fed_path()
        fp["implied_source_meta"]["dots"].pop("target_epoch")
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        assert v["rates"]["dots"][0]["on_axis"] is False

    def test_non_effr_strip_keeps_the_dot_off_the_axis(self):
        """A SOFR-compounded strip is not a fed-funds path: no dot on the axis."""
        fp = _fed_path()
        fp["implied_source_meta"]["selected_is_effr"] = False
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        assert v["rates"]["dots"][0]["on_axis"] is False


class TestComparisonBasis:
    """The legacy gap block is NOT basis-qualified by itself."""

    def test_qualified_comparison_is_shown(self):
        v = pmv.build_view(_policy_lever(), _latest())
        assert v["rates"]["gap"]["available"] is True
        assert v["rates"]["gap"]["gap_bp"] == -14
        assert v["relative"]["known"] is True
        assert v["relative"]["label_en"] == "-14 bp at end-2026"

    def test_comparison_is_suppressed_without_source_metadata(self):
        fp = _fed_path()
        fp.pop("implied_source_meta")
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        assert v["rates"]["gap"]["available"] is False
        assert v["relative"]["known"] is False
        assert v["rates"]["gap"]["gap_bp"] is None
        assert "publication date" in v["relative"]["sub_en"]

    def test_comparison_is_suppressed_when_the_rule_says_not_comparable(self):
        fp = _fed_path()
        fp["implied_source_meta"]["gap"]["status"] = "not_comparable"
        fp["implied_source_meta"]["gap"]["reason"] = "basis_mismatch:rate_index"
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        assert v["rates"]["gap"]["available"] is False
        assert v["relative"]["known"] is False
        assert "matched measure" in v["relative"]["sub_en"]

    def test_relative_read_is_labelled_relative_not_a_policy_stance(self):
        v = pmv.build_view(_policy_lever(), _latest())
        assert "relative" in v["relative"]["sub_en"].lower()
        assert "not a policy stance" in v["relative"]["sub_en"].lower()
        assert "不是政策立场" in v["relative"]["sub_zh"]

    def test_legacy_engine_read_and_hike_headline_are_not_echoed(self):
        """The engine's own read_en/headline_en are not basis-qualified and
        assert a literal number of hikes — the panel must not echo them."""
        v = pmv.build_view(_policy_lever(), _latest())
        blob = json.dumps(v, ensure_ascii=False)
        assert "hikes" not in blob
        assert "2.0 hike" not in blob


# --------------------------------------------------------------------------- #
# context
# --------------------------------------------------------------------------- #

class TestContext:
    def test_zero_day_countdown_is_preserved(self):
        pl = _policy_lever()
        pl["calendar"]["days_to_midterm"] = 0
        v = pmv.build_view(pl, _latest())
        assert v["context"]["calendar"]["known"] is True
        assert v["context"]["calendar"]["days"] == 0

    def test_legacy_countdown_does_not_borrow_the_semis_date(self):
        v = pmv.build_view(_policy_lever(), _latest())
        txt = v["context"]["calendar"]["countdown_en"].lower()
        assert "calculation date unavailable" in txt
        assert "2026-10-30" not in txt

    def test_absent_repricing_field_is_unknown_not_empty(self):
        """The old dialog said 'No repricing channels active today' when the
        field was simply ABSENT. Absent is not empty."""
        v = pmv.build_view(_policy_lever(), _latest())
        assert v["context"]["repricing"]["known"] is False
        assert v["context"]["repricing"]["channels"] == []
        assert "absent field" in v["context"]["repricing"]["unknown_en"]

    def test_empty_repricing_list_is_a_known_empty(self):
        pl = _policy_lever(repricing_components=[])
        v = pmv.build_view(pl, _latest())
        assert v["context"]["repricing"]["known"] is True
        assert v["context"]["repricing"]["channels"] == []
        assert "No active repricing channels" in v["context"]["repricing"]["empty_en"]

    def test_repricing_channels_are_listed_when_present(self):
        pl = _policy_lever(repricing_components=[{"name": "rates", "label_en": "Rates",
                                                  "label_zh": "利率"}])
        v = pmv.build_view(pl, _latest())
        assert v["context"]["repricing"]["known"] is True
        assert v["context"]["repricing"]["channels"][0]["label_en"] == "Rates"

    def test_malformed_repricing_payload_degrades_without_crashing(self):
        pl = _policy_lever(repricing_components="not-a-list")
        v = pmv.build_view(pl, _latest())
        assert v["context"]["repricing"]["known"] is False

    def test_flip_context_is_carried(self):
        v = pmv.build_view(_policy_lever(), _latest(),
                           flip_confirmation={"last_event": {"event_date": "2026-10-02",
                                                             "description": "Oil setup flipped."}})
        assert v["context"]["flip"]["known"] is True
        assert v["context"]["flip"]["date"] == "2026-10-02"


# --------------------------------------------------------------------------- #
# robustness contract
# --------------------------------------------------------------------------- #

class TestRobustness:
    def test_raw_payload_is_never_mutated(self):
        pl = _policy_lever()
        lt = _latest()
        before_pl = copy.deepcopy(pl)
        before_lt = copy.deepcopy(lt)
        pmv.build_view(pl, lt)
        assert pl == before_pl
        assert lt == before_lt

    def test_a_broken_rates_section_does_not_break_the_rest(self):
        lt = _latest()
        lt["fed_path"] = {"implied": "not-a-mapping", "dots": 42}
        v = pmv.build_view(_policy_lever(), lt)
        assert v["rates"]["available"] is False
        assert v["state"]["value"] == "ELEVATED"
        assert v["activity"]["n_30d"] == 12
        assert len(v["transmission"]) == 2

    def test_a_broken_policy_lever_does_not_crash(self):
        v = pmv.build_view(None, None)
        assert v["state"]["value"] == "UNKNOWN"
        assert v["snapshot"]["known"] is False
        assert v["rates"]["available"] is False

    def test_a_broken_lever_row_does_not_break_the_other_rows(self):
        pl = _policy_lever()
        pl["levers"].insert(0, "not-a-mapping")
        v = pmv.build_view(pl, _latest())
        assert len(v["transmission"]) == 3
        assert v["transmission"][0]["observed"]["known"] is False

    def test_bool_drawdown_is_not_a_reading(self):
        pl = _policy_lever()
        pl["favored_complex"]["drawdown_pct"] = True
        v = pmv.build_view(pl, _latest())
        assert v["structure"]["drawdown_pct"] is None
        legs = {c["key"]: c for c in v["conditions"]}
        assert legs["drawdown"]["known"] is False

    def test_nan_drawdown_is_not_a_reading(self):
        pl = _policy_lever()
        pl["favored_complex"]["drawdown_pct"] = float("nan")
        v = pmv.build_view(pl, _latest())
        assert v["structure"]["drawdown_pct"] is None

    def test_unsafe_urls_are_refused(self):
        assert pmv._safe_url("javascript:alert(1)") is None
        assert pmv._safe_url("data:text/html,<script>") is None
        assert pmv._safe_url("vbscript:msgbox") is None
        assert pmv._safe_url("https://example.com/x") == "https://example.com/x"

    def test_url_without_a_host_is_refused(self):
        assert pmv._safe_url("https:///nohost") is None
        assert pmv._safe_url("not a url") is None

    def test_no_source_link_is_invented(self):
        """The payload carries no URL, so the sources table carries no link."""
        v = pmv.build_view(_policy_lever(), _latest())
        for row in v["sources"]:
            assert not row["value_en"].startswith("http")

    def test_text_is_bounded_at_the_display_boundary(self):
        pl = _policy_lever()
        pl["levers"][0]["watch"] = "x" * 5000
        v = pmv.build_view(pl, _latest())
        assert len(v["transmission"][0]["hypothesis_en"]) <= pmv.MAX_TEXT

    def test_arrays_are_bounded_at_the_display_boundary(self):
        pl = _policy_lever()
        pl["levers"] = [dict(pl["levers"][0], name=f"L{i}") for i in range(50)]
        v = pmv.build_view(pl, _latest())
        assert len(v["transmission"]) <= pmv.MAX_LEVERS

    def test_malformed_dates_are_refused(self):
        pl = _policy_lever()
        pl["as_of"] = "not-a-date"
        v = pmv.build_view(pl, _latest())
        assert v["snapshot"]["known"] is False

    def test_a_non_mapping_payload_yields_a_usable_model(self):
        v = pmv.build_view("nope", 42)
        assert v["schema"] == pmv.VIEW_SCHEMA
        assert v["state"]["value"] == "UNKNOWN"
        assert v["transmission"] == []
        assert v["sources"]


class TestSources:
    def test_each_input_carries_source_date_and_basis(self):
        v = pmv.build_view(_policy_lever(), _latest())
        labels = {s["label_en"] for s in v["sources"]}
        assert "Semiconductor drawdown" in labels
        assert "Market-implied rate path" in labels
        assert "Fed projection (dot plot)" in labels
        assert "Fed-vs-market comparison rule" in labels
        for row in v["sources"]:
            assert row["basis_en"]
            assert row["value_en"]

    def test_the_comparison_rule_is_disclosed(self):
        v = pmv.build_view(_policy_lever(), _latest())
        rule = [s for s in v["sources"] if s["label_en"] == "Fed-vs-market comparison rule"][0]
        assert rule["value_en"] == "sep_vs_market_year_end.v1"
        assert "comparable_after_transformation" in rule["basis_en"]

    def test_the_methodology_states_the_basis_rule(self):
        v = pmv.build_view(_policy_lever(), _latest())
        assert "matched measure" in v["methodology_en"]
        assert "缺口" in v["methodology_zh"]

    def test_the_boundary_is_explicit(self):
        v = pmv.build_view(_policy_lever(), _latest())
        assert "no administration intent" in v["boundary_en"]
        assert "不含政策意图" in v["boundary_zh"]


class TestEvidenceLevel:
    def test_partial_coverage_is_reported_as_partial(self):
        pl = _policy_lever()
        pl["jawboning"] = {}
        lt = _latest()
        lt["fed_path"] = {"implied": {}}
        v = pmv.build_view(pl, lt)
        assert v["evidence"]["level"] == "partial"

    def test_no_evidence_is_reported_as_missing(self):
        pl = _policy_lever()
        pl["jawboning"] = {}
        pl["levers"] = []
        pl["favored_complex"] = {"basket": []}
        lt = _latest()
        lt["fed_path"] = {"implied": {}}
        v = pmv.build_view(pl, lt)
        assert v["evidence"]["level"] == "missing"

    def test_evidence_is_reported_apart_from_the_condition_state(self):
        """A met condition and a good evidence level are separate facts."""
        v = pmv.build_view(_policy_lever(), _latest())
        assert v["state"]["value"] == "ELEVATED"
        assert v["evidence"]["level"] in ("partial", "complete")
        assert "not proof that markets have repriced" not in v["state"]["summary_en"]


class TestReviewedRegressions:
    """Cases independently reproduced against the first pushed candidate."""

    @pytest.mark.parametrize("raw,dd,armed,expected,qualification", [
        ("QUIET", None, None, "UNKNOWN", "unavailable"),
        ("ARMED", -25, None, "UNKNOWN", "unavailable"),
        ("ARMED", -5, None, "UNKNOWN", "inconsistent"),
        ("QUIET", -25, None, "UNKNOWN", "inconsistent"),
        ("ELEVATED", -25, None, "ELEVATED", "partial"),
        ("ELEVATED", -5, None, "UNKNOWN", "unavailable"),
        ("ARMED", -25, False, "UNKNOWN", "inconsistent"),
        ("QUIET", -5, False, "QUIET", "confirmed"),
        (" quiet ", -5, False, "QUIET", "confirmed"),
        ("ELEVATED", -25, False, "ELEVATED", "confirmed"),
        ("ARMED", -25, True, "ARMED", "confirmed"),
        ("ELEVATED", -25, True, "UNKNOWN", "inconsistent"),
    ])
    def test_headline_is_qualified_without_replacing_the_score(self, raw, dd, armed, expected, qualification):
        pl = _policy_lever(state=raw)
        pl["favored_complex"]["drawdown_pct"] = dd
        pl["levers"][0]["arming"] = None if armed is None else {"armed": armed, "as_of": "2026-10-30"}
        v = pmv.build_view(pl, _latest())
        assert v["state"]["value"] == expected
        assert v["state"]["qualification"] == qualification
        assert pl["state"] == raw

    def test_undated_or_future_technical_observation_cannot_confirm_quiet(self):
        for stamp in (None, "2026-11-03"):
            pl = _policy_lever(state="QUIET", computed_at="2026-11-01T01:00:00Z")
            pl["favored_complex"]["drawdown_pct"] = -5
            pl["levers"][0]["arming"]["as_of"] = stamp
            assert pmv.build_view(pl, _latest())["state"]["value"] == "UNKNOWN"

    def test_missing_eligible_lever_prevents_a_false_negative(self):
        pl = _policy_lever(state="QUIET")
        pl["favored_complex"]["drawdown_pct"] = -5
        pl["levers"].append({"asset": "XYZ", "arming": None})
        assert pmv.build_view(pl, _latest())["conditions"][1]["met"] is None

    @pytest.mark.parametrize("rates", [
        {"implied": {"m1": 4.0, 3: 4.1}},
        {"implied_source_meta": {"missing_source": [None, {}, 7]}},
        {"implied_source_meta": {"selected_strip": ["zq"]}},
        {"implied": {"m1": -1e308, "m12": 1e308}},
    ])
    def test_bad_rate_metadata_cannot_crash_independent_sections(self, rates):
        v = pmv.build_view(_policy_lever(), _latest(fed_path=rates))
        assert v["activity"]["n_30d"] == 12
        assert v["conditions"][0]["met"] is True
        json.dumps(v, allow_nan=False)

    @pytest.mark.parametrize("bad", ["2026-10-30junk", "2026-10-30<script>", "2026-02-30", "2026-10-30T25:00:00"])
    def test_date_parser_validates_the_entire_input(self, bad):
        assert pmv._date(bad) is None

    def test_source_rule_alone_does_not_qualify_undated_sep(self):
        fp = _fed_path()
        fp["implied_source_meta"]["dots"]["vintage"] = None
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        assert not v["relative"]["known"]
        assert not v["rates"]["dots_on_axis"]
        assert len(v["rates"]["dots"]) == 2
        assert v["rates"]["available"]

    @pytest.mark.parametrize("stamp", ["2026-10-30", "2026-11-01"])
    def test_sep_must_be_available_before_the_chart_observation(self, stamp):
        fp = _fed_path()
        fp["implied_source_meta"]["dots"]["vintage"] = stamp
        fp["implied_source_meta"]["cutoff"] = "2026-12-01"
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        assert not v["rates"]["dots_on_axis"]
        assert not v["relative"]["known"]

    def test_sofr_curve_has_no_connected_policy_observation_or_fed_gap(self):
        fp = _fed_path()
        meta = fp["implied_source_meta"]
        meta.update(selected_strip="sofr", selected_is_effr=False, selected_basis="sr3_compounded_sofr")
        meta["strips"]["sofr"] = {"rate_index": "SOFR", "value_state": "present", "observation_time": "2026-10-30"}
        meta["gap"]["status"] = "not_comparable"
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        assert all(p["months"] > 0 for p in v["rates"]["points"])
        assert v["rates"]["reference"] is None
        assert v["rates"]["bp_12m"] is None
        assert v["rates"]["available"]
        assert not v["relative"]["known"]

    def test_current_effective_rate_is_not_mislabelled_as_target_midpoint(self):
        fp = _fed_path(target_mid=None, policy_rate=3.91)
        v = pmv.build_view(_policy_lever(), _latest(fed_path=fp))
        assert v["rates"]["current_rate"]["value"] == 3.91
        assert "Effective" in v["rates"]["current_rate"]["label_en"]
        assert "today" not in v["rates"]["current_rate"]["label_en"].lower()

    def test_semis_date_cannot_move_the_rate_chart(self):
        v = pmv.build_view(_policy_lever(as_of="2026-06-30"), _latest())
        assert v["rates"]["dots"][0]["months"] == pytest.approx(2.03, abs=.05)
        assert v["rates"]["as_of"] == "2026-10-30"

    def test_mobile_geometry_preserves_values_and_readable_coordinates(self):
        r = pmv.build_view(_policy_lever(), _latest())["rates"]
        assert r["mobile_chart"]["width"] == 340
        assert [m["value"] for m in r["mobile_chart"]["markers"]] == [m["value"] for m in r["chart"]["markers"]]
        assert all(0 <= m["x"] <= 340 for m in r["mobile_chart"]["markers"])

    def test_out_of_horizon_points_are_not_clamped_to_twelve_months(self):
        fp = _fed_path()
        fp["implied"].update(m999=8.0, m0=9.0)
        r = pmv.build_view(_policy_lever(), _latest(fed_path=fp))["rates"]
        assert [p["months"] for p in r["points"]] == [1, 3, 6, 12]



class TestProducerContractIntegration:
    @pytest.mark.parametrize('status', ['missing', 'unreadable', 'unusable', 'unexpected', None, []])
    def test_unusable_source_cannot_masquerade_as_zero(self, status):
        pl = _policy_lever(jawboning={'source_status': status, 'n_7d': 0, 'n_30d': 0})
        activity = pmv.build_view(pl, _latest())['activity']
        assert activity['known_7d'] is activity['known_30d'] is False

    @pytest.mark.parametrize('status', ['usable', 'partial', 'empty'])
    def test_qualified_zero_survives_without_claiming_feed_freshness(self, status):
        pl = _policy_lever(jawboning={
            'source_status': status, 'n_7d': 0, 'n_30d': 0,
            'evaluated_at': '2026-11-01T23:30:00-02:00',
            'evaluated_date': '2026-11-02', 'coverage': 'unknown',
        })
        activity = pmv.build_view(pl, _latest())['activity']
        assert activity['n_7d'] == activity['n_30d'] == 0
        assert activity['window_end'] == '2026-11-02'
        assert 'Feed coverage is not established' in activity['coverage_en']
        assert 'UTC' in activity['coverage_en']
        assert '2026-10-30' not in activity['coverage_en']

    def test_future_last_record_is_withheld_even_with_a_usable_source(self):
        pl = _policy_lever(jawboning={
            'source_status': 'usable', 'n_7d': 1, 'n_30d': 1,
            'evaluated_at': '2026-11-01T12:00:00Z',
            'last_alert_ts_utc': '2026-11-01T12:00:00.000001Z',
            'last_alert_summary': 'Future record',
        })
        assert pmv.build_view(pl)['activity']['last_alert']['known'] is False

    @pytest.mark.parametrize('day,state,days_to,days_since', [
        (1, 'upcoming', 2, None), (3, 'today', 0, 0), (4, 'past', None, 1),
    ])
    def test_actual_producer_calendar_remains_dated_in_the_view(self, day, state, days_to, days_since):
        from datetime import datetime, timezone
        from scripts.build_policy_lever import _compute_calendar
        calendar = _compute_calendar(now=datetime(2026, 11, day, 12, tzinfo=timezone.utc))
        view = pmv.build_view(_policy_lever(calendar=calendar))['context']['calendar']
        assert view['known'] is True and view['state'] == state
        assert view['days'] == days_to
        assert '2026-11-03' in view['countdown_en']
        assert f'evaluated 2026-11-{day:02d}' in view['countdown_en']
        if state == 'past':
            assert 'Scheduled date passed' in view['countdown_en']
            assert '0 days' not in view['countdown_en']

    @pytest.mark.parametrize('change', [
        {'event_state': 'upcoming'}, {'days_to_midterm': 0}, {'days_since_midterm': 99},
        {'evaluation_date': '2026-11-03'}, {'event_date': 'invalid'},
    ])
    def test_inconsistent_calendar_does_not_synthesize_a_countdown(self, change):
        from datetime import datetime, timezone
        from scripts.build_policy_lever import _compute_calendar
        calendar = _compute_calendar(now=datetime(2026, 11, 4, 12, tzinfo=timezone.utc))
        calendar.update(change)
        view = pmv.build_view(_policy_lever(calendar=calendar))['context']['calendar']
        assert view['known'] is False
        assert not view['countdown_en']

    @pytest.mark.parametrize('records,expected_status,expected_count', [
        ([], 'empty', 0),
        (['not JSON', 'null'], 'unusable', None),
        ([{'published': '2026-11-02T00:00:00Z'}], 'unusable', None),
        (['not JSON', {'published': '2026-10-31T12:00:00Z', 'summary': 'Observed'},
          {'published': '2026-11-02T00:00:00Z', 'summary': 'Future'}], 'partial', 1),
    ])
    def test_actual_record_reader_to_view_preserves_zero_unknown_and_partial(self, tmp_path, records, expected_status, expected_count):
        from datetime import datetime, timezone
        from scripts.build_policy_lever import _compute_jawboning
        path = tmp_path / 'alerts.jsonl'
        path.write_text('\n'.join(r if isinstance(r, str) else json.dumps(r) for r in records))
        activity = _compute_jawboning(path, now=datetime(2026, 11, 1, 12, tzinfo=timezone.utc))
        view = pmv.build_view(_policy_lever(jawboning=activity), _latest())
        assert view['activity']['source_status'] == expected_status
        assert view['activity']['n_7d'] == expected_count
        assert view['activity']['known_7d'] is (expected_count is not None)
        assert view['rates']['available'] is True
        if expected_status == 'partial':
            assert 'valid records only' in view['activity']['coverage_en']
            assert view['activity']['last_alert']['summary_en'] == 'Observed'
