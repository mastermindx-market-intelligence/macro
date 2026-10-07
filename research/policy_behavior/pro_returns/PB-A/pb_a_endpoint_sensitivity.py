#!/usr/bin/env python3
"""POST_SCORE_EXPLORATORY: fixed forecast, fixed anchor, endpoint-only +/-7 days.
Not preregistered. Not additional validation. Excludes adversarial challenge.
Writes only sibling PB_A_ENDPOINT_SENSITIVITY.json. Does not import/run scorer.
"""
import calendar
import csv
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
TARGET = "fed_target_midpoint_net_direction"
MODELS = ("M0", "M1", "M2", "C0")
PAIRS = (("M0", "M2"), ("M0", "M1"), ("M2", "C0"))
HORIZONS = (1, 3, 6)
NY = ZoneInfo("America/New_York")

def read_json(name):
    return json.loads((ROOT / name).read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))

def classify(delta):
    return "UP" if delta > 1e-10 else "DOWN" if delta < -1e-10 else "HOLD"

def month_end(cut, months):
    civil = utc(cut).astimezone(NY).date()
    total = civil.year * 12 + civil.month - 1 + months
    year, month = divmod(total, 12)
    month += 1
    return date(year, month, min(civil.day, calendar.monthrange(year, month)[1]))

def read_series(name):
    result = {}
    with (ROOT / "outcome_inputs" / (name + ".csv")).open() as handle:
        for row in csv.DictReader(handle):
            if row[name] not in ("", "."):
                result[date.fromisoformat(row["observation_date"])] = float(row[name])
    return result

def own_stats(rows, model):
    subset = [r for r in rows if r["predictions"][model] != "ABSTAIN"]
    good = sum(r["predictions"][model] == r["truth"] for r in subset)
    return {
        "count": len(subset), "correct_count": good,
        "accuracy": good / len(subset) if subset else None,
        "observed_denominator": len(rows), "abstention_count": len(rows)-len(subset),
        "episode_ids": [r["episode_id"] for r in subset],
    }

def pair_stats(rows, left, right):
    subset = [r for r in rows if r["predictions"][left] != "ABSTAIN" and r["predictions"][right] != "ABSTAIN"]
    lc = sum(r["predictions"][left] == r["truth"] for r in subset)
    rc = sum(r["predictions"][right] == r["truth"] for r in subset)
    both = sum(r["predictions"][left] == r["truth"] and r["predictions"][right] == r["truth"] for r in subset)
    left_only = lc-both
    right_only = rc-both
    return {
        "left": left, "right": right, "matched_count": len(subset),
        "left_correct_count": lc, "right_correct_count": rc,
        "both_correct_count": both, "left_only_correct_count": left_only,
        "right_only_correct_count": right_only, "neither_correct_count": len(subset)-both-left_only-right_only,
        "left_accuracy": lc/len(subset) if subset else None,
        "right_accuracy": rc/len(subset) if subset else None,
        "left_minus_right_accuracy": (lc-rc)/len(subset) if subset else None,
        "exact_matched_episode_ids": [r["episode_id"] for r in subset],
    }

def main():
    tracked = [ROOT/x for x in (
        "PB_A_DECISION_INPUTS.json", "PB_A_FORECAST_FREEZE.json",
        "PB_A_OUTCOMES.json", "PB_A_BASELINE_PILOT.json",
        "PB_A_PROTOCOL_FREEZE.json", "PB_A_IMPLEMENTATION_CLARIFICATIONS.json",
        "pb_a_analyze.py",
        "outcome_inputs/DFEDTARL.csv", "outcome_inputs/DFEDTARU.csv",
        "outcome_inputs/policy_decision_changes.json",
    )]
    before = {str(p.relative_to(ROOT)): sha(p) for p in tracked}
    decisions = read_json("PB_A_DECISION_INPUTS.json")
    freeze = read_json("PB_A_FORECAST_FREEZE.json")
    outcomes = read_json("PB_A_OUTCOMES.json")
    pilot = read_json("PB_A_BASELINE_PILOT.json")
    ledger = read_json("outcome_inputs/policy_decision_changes.json")
    lower, upper = read_series("DFEDTARL"), read_series("DFEDTARU")
    assert set(lower) == set(upper)
    forecasts = freeze["forecast_payload"]["episodes"]
    unsigned = {k:freeze[k] for k in ("input_sha256","forecast_payload")}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()
    assert hashlib.sha256(canonical).hexdigest() == freeze["freeze_content_sha256"]
    assert outcomes["forecast_freeze_content_sha256"] == freeze["freeze_content_sha256"]
    assert outcomes["forecast_freeze_file_sha256"] == before["PB_A_FORECAST_FREEZE.json"]
    by_input = {x["episode_id"]: x for x in decisions["episodes"]}
    by_outcome = {x["episode_id"]: x for x in outcomes["episodes"]}
    primary = [x for x in forecasts if x["cohort"] == "PRIMARY"]
    excluded = [x["episode_id"] for x in forecasts if x["cohort"] != "PRIMARY"]
    assert len(primary) == 24
    anchors = []
    detail = []
    scenario_rows = {str(s): {str(h): [] for h in HORIZONS} for s in (-7,0,7)}
    for frozen in primary:
        identity = frozen["episode_id"]
        input_row, outcome = by_input[identity], by_outcome[identity]
        assert frozen["decision_cut_utc"] == input_row["decision_cut_utc"]
        cut = utc(frozen["decision_cut_utc"])
        prior = [r for r in ledger["changes"] if utc(r["decision_utc"]) <= cut]
        latest = max(prior, key=lambda r: utc(r["decision_utc"]))
        independent_range = [latest["lower"], latest["upper"]]
        declared = input_row["known_rate_decision"]
        if declared is not None:
            assert utc(declared["decision_utc"]) <= cut
            assert [declared["lower_pct"], declared["upper_pct"]] == independent_range
        anchor = outcome["horizons"]["1"]["policy"]["anchor"]
        assert [anchor["lower_pct"], anchor["upper_pct"]] == independent_range
        expected_mid = sum(independent_range)/2
        assert anchor["midpoint_pct"] == expected_mid
        anchors.append({
            "episode_id":identity, "cut_utc":frozen["decision_cut_utc"],
            "range_pct":independent_range, "midpoint_pct":expected_mid,
            "stored_anchor_provenance":anchor["provenance"],
            "latest_change_decision_utc":latest["decision_utc"],
            "latest_change_effective_date":latest["effective_date"],
            "independent_level_agrees":True,
            "known_latest_change_not_effective_at_cut":
                date.fromisoformat(latest["effective_date"]) > cut.astimezone(NY).date(),
        })
        for h in HORIZONS:
            horizon = str(h)
            original = outcome["horizons"][horizon]["policy"]
            end = month_end(frozen["decision_cut_utc"], h)
            assert end.isoformat() == original["horizon_date_ny"] == frozen["forecasts"][horizon]["horizon_date_ny"]
            assert original["anchor"] == anchor
            assert original["targets"][TARGET]["status"] == "OBSERVED"
            predictions = {
                m:frozen["forecasts"][horizon]["policy_targets"][TARGET][m]["direction"]
                for m in MODELS
            }
            base_truth = original["targets"][TARGET]["direction"]
            for shift in (-7,0,7):
                shifted = end + timedelta(days=shift)
                assert shifted in lower and shifted in upper
                endpoint_range = [lower[shifted], upper[shifted]]
                midpoint = sum(endpoint_range)/2
                truth = classify(midpoint-expected_mid)
                if shift == 0:
                    assert endpoint_range == original["endpoint_range_pct"]
                    assert midpoint == original["endpoint_midpoint_pct"]
                    assert truth == base_truth
                crossed = [
                    {"decision_utc":r["decision_utc"],"effective_date":r["effective_date"],
                     "lower":r["lower"],"upper":r["upper"]}
                    for r in ledger["changes"]
                    if min(end,shifted) < date.fromisoformat(r["effective_date"]) <= max(end,shifted)
                ]
                row = {
                    "episode_id":identity,"horizon_months":h,"endpoint_shift_days":shift,
                    "original_endpoint_date":end.isoformat(),"shifted_endpoint_date":shifted.isoformat(),
                    "anchor_midpoint_pct":expected_mid,"endpoint_range_pct":endpoint_range,
                    "endpoint_midpoint_pct":midpoint,"net_change_bps":(midpoint-expected_mid)*100,
                    "base_truth":base_truth,"truth":truth,"truth_label_flip":truth != base_truth,
                    "predictions":predictions,"crossed_effective_changes":crossed,
                }
                detail.append(row)
                scenario_rows[str(shift)][horizon].append(row)
    scenarios = {}
    for shift, horizon_rows in scenario_rows.items():
        scenarios[shift] = {}
        for h, rows in horizon_rows.items():
            scenarios[shift][h] = {
                "observed_count":len(rows),
                "truth_counts":{c:sum(r["truth"]==c for r in rows) for c in ("DOWN","HOLD","UP")},
                "truth_label_flip_count_vs_unshifted":sum(r["truth_label_flip"] for r in rows),
                "truth_label_flip_episode_ids":[r["episode_id"] for r in rows if r["truth_label_flip"]],
                "own":{m:own_stats(rows,m) for m in MODELS},
                "pairs":{a+"__"+b:pair_stats(rows,a,b) for a,b in PAIRS},
            }
    after = {str(p.relative_to(ROOT)):sha(p) for p in tracked}
    assert before == after
    # Exact baseline reproduction of primary ALL own counts and accuracy.
    pilot_primary = pilot["cohorts"]["PRIMARY"]["targets"][TARGET]
    for h in ("1","3","6"):
        original = pilot_primary[h]["ALL"]["own_coverage"]
        for model in MODELS:
            assert original[model]["count"] == scenarios["0"][h]["own"][model]["count"]
            assert original[model]["direction_accuracy"] == scenarios["0"][h]["own"][model]["accuracy"]
    report = {
        "schema":"pb_a_post_score_endpoint_sensitivity.v1",
        "status":"POST_SCORE_EXPLORATORY",
        "preregistered":False,"additional_validation":False,
        "authority":"RESEARCH_ONLY",
        "forecast_freeze_remote_commit_as_provided_by_root":"8799d065178b7637bc91a0e69696df8b9ef763f6",
        "forecast_freeze_content_sha256":freeze["freeze_content_sha256"],
        "scope":"Primary net-target only; fixed sample, cuts, anchors, forecast directions and probabilities. Endpoints shifted -7/0/+7 calendar days.",
        "challenge_excluded_ids":excluded,
        "primary_episode_count":len(primary),"horizons_calendar_months":[1,3,6],
        "endpoint_semantics":"End of shifted civil date America/New_York; exact daily effective target observations, no carry-forward.",
        "input_sha256":before,"frozen_inputs_unchanged_after_run":True,
        "independent_audit":{"anchor_checks":len(anchors),"anchor_mismatches":0,
            "original_endpoint_label_checks":len(primary)*len(HORIZONS),
            "original_endpoint_label_mismatches":0,
            "baseline_metrics_reproduced":True},
        "anchors":anchors,"scenarios":scenarios,
        "truth_flip_details":[r for r in detail if r["truth_label_flip"]],
        "all_endpoint_details":detail,
        "interpretation_limits":[
            "Post-score diagnostic chosen after inspecting primary metrics; cannot revise primary labels, forecasts, or metrics.",
            "Not preregistered and not additional or unseen validation.",
            "Exact counts are descriptive; purposive overlapping historical episodes remain dependent.",
            "No horizon pooling or comparison of model-own accuracy across unequal coverage denominators.",
            "A +/-7-day endpoint can change rate magnitude without flipping UP/HOLD/DOWN; such boundary changes are retained in detail.",
            "Endpoint-only perturbation does not examine alternate cut, anchor, statement coding, or meeting-aligned target definitions.",
        ],
        "source_spot_checks":[
            {"url":"https://www.federalreserve.gov/newsevents/pressreleases/monetary20190130a.htm",
             "ref":"turn45view0","fact":"Jan30 2019 14:00EST hold at2.25-2.50%; July31 cut effectiveAug1 is beyond originalJul30 six-month endpoint."},
            {"url":"https://www.federalreserve.gov/newsevents/pressreleases/monetary20211215a.htm",
             "ref":"turn45view1","fact":"Dec15 2021 14:00EST hold at0-0.25%; Mar16 2022 liftoff effectiveMar17 is beyond originalMar15 three-month endpoint."},
            {"url":"https://www.federalreserve.gov/newsevents/pressreleases/monetary20230503a.htm",
             "ref":"turn37view3","fact":"May3 2023 14:00EDT hike to5-5.25%; Treasury next-midnight cut uses known new range, not old daily effective range."},
        ],
    }
    destination = ROOT/"PB_A_ENDPOINT_SENSITIVITY.json"
    destination.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "status":report["status"],"path":str(destination),
        "sha256":sha(destination),"audit":report["independent_audit"],
        "flip_counts":{s:{h:r["truth_label_flip_count_vs_unshifted"] for h,r in hs.items()} for s,hs in scenarios.items()},
        "counts":{s:{h:{"own":{m:[v["correct_count"],v["count"]] for m,v in r["own"].items()},
                 "pairs":{p:[v["left_correct_count"],v["right_correct_count"],v["matched_count"]] for p,v in r["pairs"].items()}}
                 for h,r in hs.items()} for s,hs in scenarios.items()}
    },indent=2))

if __name__ == "__main__":
    main()
