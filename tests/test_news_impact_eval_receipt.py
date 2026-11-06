"""Tests for engine.news_impact.eval_receipt (A3 4.8-4.14).

Hermetic: no network; the frozen contracts under contracts/news_impact are the
only files read, and every reader fails closed when they are absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import jsonschema

from engine.news_impact import eval_receipt as er

REGISTRY_PATH = er.default_registry_path()
RECEIPT_SCHEMA_PATH = REGISTRY_PATH.parent / "eval_receipt.v1.schema.json"

if not REGISTRY_PATH.is_file():
    raise RuntimeError(f"frozen endpoints registry missing (fail closed, never skip): {REGISTRY_PATH}")


# ----------------------------------------------------------------- fixtures


def gi(case_id: str, fold: str, field: str, outcome: str, *, template: str = "t", notes: str = "", candidate_value=None, gold_value=None) -> er.GradedItem:
    return er.GradedItem(
        case_id=case_id, fold=fold, template=template, field=field,
        outcome=outcome, gold_value=gold_value, candidate_value=candidate_value,
        notes=notes,
    )


def make_reg(mode: str = "confirm") -> dict:
    return er.make_registration(
        tape_sha256="a" * 64,
        sampler_version="sampler-1",
        sampling_seed=7,
        t_prospective="2026-10-12T00:00:00Z",
        mode=mode,
    )


def receipt_for(items, *, cluster_map=None, issuer_map=None, accounting=None, **kw):
    cluster_map = cluster_map if cluster_map is not None else {}
    issuer_map = issuer_map if issuer_map is not None else {}
    accounting = accounting if accounting is not None else er.AccountingInput(manifest_n=0)
    return er.build_receipt(
        graded_by_construction={("cheap_extractor_no_frontier", "full"): items},
        cluster_map=cluster_map,
        issuer_map=issuer_map,
        accounting=accounting,
        registration=make_reg(kw.pop("mode", "confirm")),
        **kw,
    )


def row(receipt, metric_id, slice_label="all_historical", baseline="cheap_extractor_no_frontier"):
    matches = [
        m for m in receipt["metrics"]
        if m["metric_id"] == metric_id and m["fold_slice"] == slice_label and m["baseline_id"] == baseline
    ]
    assert len(matches) == 1, (metric_id, slice_label, len(matches))
    return matches[0]


def thresh_row(receipt, metric_id, slice_label="all_historical"):
    matches = [
        t for t in receipt["threshold_evaluations"]
        if t["metric_id"] == metric_id and t["fold_slice"] == slice_label
    ]
    assert len(matches) == 1
    return matches[0]


def case_id(i: int) -> str:
    return f"case_{i:024x}"


def cluster_of(i: int) -> str:
    return f"grp_{i % 10:04d}"


def maps_for(n: int):
    cm = {case_id(i): cluster_of(i) for i in range(n)}
    im = {case_id(i): f"cik:{i:010d}" for i in range(n)}
    return cm, im


# ------------------------------------------------------------- statistics


class TestStatistics:
    def test_clopper_pearson_hand_computed(self):
        # closed form check: lower solves x^3/3 - x^4/4 = 0.025/12 (Beta(3,2) CDF);
        # upper = 0.975 ** (1/4) via I_x(4,1) = x^4
        iv = er.clopper_pearson_interval(3, 4)
        assert iv["method"] == "clopper_pearson_diagnostic"
        assert abs(iv["low"] - 0.194120) < 2e-3
        assert abs(iv["high"] - 0.993691) < 2e-3
        x = iv["low"]
        assert abs((x ** 3 / 3 - x ** 4 / 4) * 12 - 0.025) < 1e-4  # CDF really is 0.025

    def test_clopper_pearson_zero_events_n600(self):
        iv = er.clopper_pearson_interval(0, 600)
        assert abs(iv["high"] - 0.0061293) < 1e-4  # rule-of-three neighbourhood

    def test_clopper_pearson_zero_denominator_none(self):
        assert er.clopper_pearson_interval(0, 0) is None

    def test_wilson_hand_computed(self):
        iv = er.wilson_interval(3, 4)
        assert iv["method"] == "wilson_diagnostic"
        assert abs(iv["low"] - 0.300642) < 1e-4
        assert abs(iv["high"] - 0.954413) < 1e-4

    def test_wilson_bad_coverage(self):
        with pytest.raises(er.EvalReceiptError) as e:
            er.wilson_interval(1, 2, coverage=0.5)
        assert er.EvalReceiptError("BAD_COVERAGE").code == "BAD_COVERAGE"
        assert e.value.code == "BAD_COVERAGE"

    def test_bootstrap_floor_below_30(self):
        iv = er.cluster_bootstrap_interval([1.0] * 20, [f"g{i}" for i in range(20)])
        assert iv["method"] == "not_estimable" and iv["low"] is None

    def test_bootstrap_floor_below_10_clusters(self):
        iv = er.cluster_bootstrap_interval([1.0] * 40, ["g"] * 40)
        assert iv["method"] == "not_estimable"

    def test_bootstrap_all_hits_is_degenerate_interval(self):
        vals = [1.0] * 30
        clusters = [f"g{i % 10}" for i in range(30)]
        iv = er.cluster_bootstrap_interval(vals, clusters)
        assert iv["method"] == "cluster_bootstrap_percentile"
        assert iv["low"] == 1.0 and iv["high"] == 1.0

    def test_bootstrap_deterministic_and_permutation_invariant(self):
        vals = [1.0] * 27 + [0.0] * 3
        clusters = [f"g{i % 10}" for i in range(30)]
        a = er.cluster_bootstrap_interval(vals, clusters)
        b = er.cluster_bootstrap_interval(list(reversed(vals)), list(reversed(clusters)))
        assert a == b
        rng_runs = [er.cluster_bootstrap_interval(vals, clusters) for _ in range(2)]
        assert rng_runs[0] == rng_runs[1]
        assert a["low"] < a["high"]

    def test_two_way_cgm_hand_computed(self):
        iv = er.two_way_cgm_interval(
            [1.0, 2.0, 3.0, 6.0], ["g1", "g1", "g2", "g2"], ["c1", "c2", "c1", "c2"]
        )
        assert iv["method"] == "two_way_cluster_cgm"
        assert abs(iv["low"] - 0.171036) < 1e-3
        assert abs(iv["high"] - 5.828964) < 1e-3

    def test_two_way_cgm_needs_two_of_each(self):
        assert er.two_way_cgm_interval([1.0, 2.0], ["g1", "g1"], ["c1", "c1"]) is None


# ------------------------------------------------------------- F1 fact_integrity


class TestFactIntegrity:
    def test_critical_numeric_auto_published_hand_computed(self):
        items = [
            gi(case_id(0), "f1", "incremental_amount", "correct"),
            gi(case_id(1), "f1", "remaining_authorization", "correct"),
            gi(case_id(2), "f2", "executed_amount", "correct"),
            gi(case_id(3), "f2", "incremental_amount", "wrong_value"),
        ]
        cm, im = maps_for(4)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        m = row(r, "critical_numeric_correctness_auto_published")
        assert m["value"] == pytest.approx(0.75)
        assert m["n"] == 4
        assert m["n_clusters"] == 4
        assert m["status"] == "not_estimable"  # below reporting floor
        assert m["interval"]["method"] == "not_estimable"
        assert m["interval_diagnostic_cp"] is not None
        assert m["predictive_weight"] == "qa_only" and m["qa_only"] is True

    def test_reviewed_published_excluded_from_98_denominator(self):
        items = [
            gi(case_id(0), "f1", "incremental_amount", "correct"),  # auto population
            gi(case_id(1), "f1", "incremental_amount", "correct",
               notes=er.POP_ALL_DISPOSITIONS),  # reviewed: separate population
        ]
        cm, im = maps_for(2)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        auto = row(r, "critical_numeric_correctness_auto_published")
        alld = row(r, "critical_numeric_correctness_all_dispositions")
        assert auto["n"] == 1 and auto["value"] == 1.0
        assert alld["n"] == 1 and alld["value"] == 1.0
        # the reviewed item never lands in the auto-published denominator
        items_auto_only = [items[0]]
        r2 = receipt_for(items_auto_only, cluster_map={case_id(0): "g0"}, issuer_map={case_id(0): "cik:0000000001"})
        assert row(r2, "critical_numeric_correctness_auto_published")["n"] == 1

    def test_absence_correctness_population(self):
        items = [
            gi(case_id(0), "f1", "remaining_authorization", "correct", notes=er.POP_GOLD_ABSENT),
            gi(case_id(1), "f1", "remaining_authorization", "wrong_absence", notes=er.POP_GOLD_ABSENT),
            gi(case_id(2), "f1", "remaining_authorization", "correct"),  # not in this population
        ]
        cm, im = maps_for(3)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        m = row(r, "absence_correctness")
        assert m["n"] == 2 and m["value"] == 0.5

    def test_span_replay_and_correction_replay(self):
        items = [
            gi(case_id(0), "f1", "span_replay", "pass"),
            gi(case_id(1), "f1", "span_replay", "pass"),
            gi(case_id(2), "f2", "correction_replay", "success"),
            gi(case_id(3), "f2", "correction_replay", "failure"),
        ]
        cm, im = maps_for(4)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        assert row(r, "span_replay_pass_rate")["value"] == 1.0
        assert row(r, "correction_replay_success")["value"] == 0.5

    def test_disposition_accounting_complete_true_and_false(self):
        cm, im = maps_for(1)
        ok = er.AccountingInput(
            manifest_n=2, auto_published=1, deferred=1,
            manifest_case_ids=(case_id(0), case_id(1)),
            output_case_ids=(case_id(1), case_id(0)),
        )
        r = receipt_for([], cluster_map=cm, issuer_map=im, accounting=ok)
        m = row(r, "disposition_accounting_complete")
        assert m["value"] == 1.0 and m["predictive_weight"] == "not_a_rate"
        t = thresh_row(r, "disposition_accounting_complete")
        assert t["observed"] is True and t["crossing"] == "meets"
        assert t["owner_status"] == "PROPOSED-OWNER-FREEZES"

        bad = er.AccountingInput(manifest_n=2, auto_published=1)  # sums to 1
        r2 = receipt_for([], cluster_map=cm, issuer_map=im, accounting=bad)
        assert row(r2, "disposition_accounting_complete")["value"] == 0.0
        assert thresh_row(r2, "disposition_accounting_complete")["crossing"] == "below"

    def test_duplicate_output_breaks_completeness(self):
        cm, im = maps_for(1)
        dup = er.AccountingInput(
            manifest_n=1, auto_published=1,
            manifest_case_ids=(case_id(0),), output_case_ids=(case_id(0), case_id(1)),
        )
        r = receipt_for([], cluster_map=cm, issuer_map=im, accounting=dup)
        assert row(r, "disposition_accounting_complete")["value"] == 0.0


# ------------------------------------------------------------- F2/F3/F4


class TestClusteringRoutingEconomics:
    def test_f2_metrics_hand_computed(self):
        items = [
            gi(case_id(0), "f1", "pair_joined", "same_gold_group"),
            gi(case_id(1), "f1", "pair_joined", "different_gold_group"),
            gi(case_id(2), "f1", "gold_pair", "system_joined"),
            gi(case_id(3), "f1", "system_cluster", "mixed"),
            gi(case_id(4), "f1", "system_cluster", "pure"),
            gi(case_id(5), "f1", "novelty_term", "missed"),
            gi(case_id(6), "f1", "group_independence", "hold"),
            gi(case_id(7), "f1", "group_independence", "violation"),
        ]
        cm, im = maps_for(8)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        assert row(r, "pair_precision")["value"] == 0.5
        assert row(r, "pair_recall")["value"] == 1.0
        assert row(r, "false_event_merge_rate")["value"] == 0.5
        assert row(r, "missed_novel_term_rate")["value"] == 1.0
        hold = row(r, "root_source_independence_hold")
        assert hold["value"] == 0.5

    def test_f3_routing_metrics(self):
        items = [
            gi(case_id(0), "f1", "material_routing", "hit"),
            gi(case_id(1), "f1", "material_routing", "miss"),
            gi(case_id(2), "f1", "material_routing", "miss"),
            gi(case_id(3), "f1", "strategic_nonnumeric", "published"),
            gi(case_id(4), "f1", "reject_audit", "auto_published"),
            gi(case_id(5), "f1", "defer_match", "matched"),
        ]
        cm, im = maps_for(6)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        assert row(r, "material_event_routing_recall")["value"] == pytest.approx(1 / 3)
        assert row(r, "strategic_nonnumeric_coverage")["value"] == 1.0
        assert row(r, "reject_audit_miss_rate")["value"] == 1.0
        assert row(r, "defer_disposition_match")["value"] == 1.0

    def test_f4_economic_reasoning(self):
        items = [
            gi(case_id(0), "f1", "mechanism_follows", "allowed"),
            gi(case_id(1), "f1", "mechanism_follows", "not_allowed"),
            gi(case_id(2), "f1", "negative_channel", "represented"),
            gi(case_id(3), "f1", "contrary_quote", "present"),
        ]
        cm, im = maps_for(4)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        assert row(r, "mechanism_follows_from_source")["value"] == 0.5
        assert row(r, "negative_channel_represented")["value"] == 1.0
        assert row(r, "contrary_quote_present_when_required")["value"] == 1.0


# ------------------------------------------------------------- F5/F6 outcomes


class TestProspectiveFamilies:
    def test_f5_revision_hit_missing_stays_missing(self):
        items = [
            gi(case_id(0), "f1", "revision_hit", "agree"),
            gi(case_id(1), "f1", "revision_hit", "disagree"),
            gi(case_id(2), "f1", "revision_hit", "unmatured"),
        ]
        cm, im = maps_for(3)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        m = row(r, "period_matched_revision_hit")
        assert m["value"] == 0.5 and m["n"] == 2 and m["n_missing"] == 1
        assert m["status"] == "qa_only"  # historical slice prints as qa_only
        assert m["predictive_weight"] == "prospective_primary"

    def test_f6_means_and_coverage_hand_computed(self):
        items = [
            gi(case_id(0), "f1", "net_return", "observed", candidate_value=0.01),
            gi(case_id(1), "f1", "net_return", "observed", candidate_value=0.02),
            gi(case_id(2), "f1", "net_return", "missing", candidate_value=None),
            gi(case_id(0), "f1", "group_relative_return", "observed", candidate_value=-0.005),
            gi(case_id(1), "f1", "drawdown", "observed", candidate_value=-0.10),
            gi(case_id(0), "f1", "return_coverage", "computed"),
            gi(case_id(1), "f1", "return_coverage", "not_computed"),
        ]
        cm, im = maps_for(3)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        assert row(r, "net_return_horizon")["value"] == pytest.approx(0.015)
        assert row(r, "net_return_horizon")["n_missing"] == 1
        assert row(r, "group_relative_return")["value"] == pytest.approx(-0.005)
        assert row(r, "drawdown_window")["value"] == pytest.approx(-0.10)
        assert row(r, "coverage_rate")["value"] == 0.5
        assert row(r, "net_return_horizon")["qa_only"] is True

    def test_mean_metric_requires_numeric_candidate(self):
        items = [gi(case_id(0), "f1", "net_return", "observed", candidate_value="oops")]
        cm, im = maps_for(1)
        with pytest.raises(er.EvalReceiptError) as e:
            receipt_for(items, cluster_map=cm, issuer_map=im)
        assert e.value.code == "BAD_METRIC_VALUE"


# ------------------------------------------------------------- zero bar / undecidable


class TestUndecidableZeroBar:
    def test_unsupported_count_undecidable_at_n(self):
        items = [
            gi(case_id(0), "f1", "unsupported_transfer", "yes"),
            gi(case_id(1), "f1", "unsupported_transfer", "no"),
            gi(case_id(2), "f1", "unsupported_transfer", "no"),
        ]
        cm, im = maps_for(3)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        m = row(r, "unsupported_ticker_to_supplier_count")
        assert m["value"] == 1.0 and m["n"] == 3
        assert "undecidable_at_n" in m["display_text"]
        assert "3000" in m["display_text"]  # required independent groups stated
        t = thresh_row(r, "unsupported_ticker_to_supplier_count")
        assert t["proposed_bar"] == 0
        assert t["crossing"] == "not_evaluable"  # never a pass
        assert t["owner_status"] == "PROPOSED-OWNER-FREEZES"

    def test_root_source_zero_bar_not_certified(self):
        items = [gi(case_id(0), "f1", "group_independence", "hold")]
        cm, im = maps_for(1)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        assert thresh_row(r, "root_source_independence_hold")["crossing"] == "not_evaluable"

    def test_no_promote_field_anywhere(self):
        items = [gi(case_id(0), "f1", "span_replay", "pass")]
        cm, im = maps_for(1)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        blob = er.canonical_json(r)
        for bad in ("promote", "pass_to_authority", "\"pass\""):
            assert bad not in blob


# ------------------------------------------------------------- thresholds / kills


class TestThresholdsAndKills:
    def _big_recall_fixture(self):
        items = [gi(case_id(i), f"f{i % 5 + 1}", "material_routing", "hit") for i in range(30)]
        cm, im = maps_for(30)
        return items, cm, im

    def test_dispute_when_governing_clears_and_naive_cp_does_not(self):
        items, cm, im = self._big_recall_fixture()
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        t = thresh_row(r, "material_event_routing_recall")
        # 30/30 hits in 10 clusters: bootstrap degenerate at 1.0 (meets),
        # CP low = 0.025**(1/30) = 0.884 < 0.95 -> dependence_dispute
        assert t["crossing"] == "meets"
        assert t["dependence_dispute"] is True

    def test_98_bar_not_evaluable_below_reporting_floor(self):
        items = [gi(case_id(0), "f1", "incremental_amount", "correct")]
        cm, im = maps_for(1)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        t = thresh_row(r, "critical_numeric_correctness_auto_published")
        assert t["proposed_bar"] == 0.98
        assert t["crossing"] == "not_evaluable"

    def test_span_replay_fail_closes_construction_only(self):
        items = [gi(case_id(0), "f1", "span_replay", "fail")]
        cm, im = maps_for(1)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        assert len(r["kills"]) == 1
        k = r["kills"][0]
        assert k["construction_id"] == "cheap_extractor_no_frontier+full+span_replay_pass_rate"
        assert k["search_space_still_open"] is True
        assert k["metric_id"] == "span_replay_pass_rate"

    def test_string_bar_not_representable_is_skipped(self):
        items = [gi(case_id(0), "f1", "correction_replay", "success")]
        cm, im = maps_for(1)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        assert all(t["metric_id"] != "correction_replay_success" for t in r["threshold_evaluations"])
        assert row(r, "correction_replay_success")["value"] == 1.0  # metric still printed


# ------------------------------------------------------------- leakage audit


class TestLeakageAudit:
    def test_prospective_fold_refused(self):
        items = [gi(case_id(0), "prospective", "span_replay", "pass")]
        cm, im = maps_for(1)
        with pytest.raises(er.EvalReceiptError) as e:
            receipt_for(items, cluster_map=cm, issuer_map=im)
        assert e.value.code == "PROSPECTIVE_FOLD_REFUSED"

    def test_sealed_fold_refused(self):
        items = [gi(case_id(0), "f6", "span_replay", "pass")]
        cm, im = maps_for(1)
        with pytest.raises(er.EvalReceiptError) as e:
            receipt_for(items, cluster_map=cm, issuer_map=im)
        assert e.value.code == "SEALED_FOLD_REFUSED"

    def test_prospective_slice_request_refused(self):
        with pytest.raises(er.EvalReceiptError) as e:
            receipt_for([], cluster_map={}, issuer_map={}, fold_slices=("prospective",))
        assert e.value.code == "PROSPECTIVE_FOLD_REFUSED"

    def test_endpoints_sha_mismatch(self):
        reg = make_reg()
        reg["endpoints_sha256"] = "b" * 64
        with pytest.raises(er.EvalReceiptError) as e:
            er.build_receipt(
                graded_by_construction={("cheap_extractor_no_frontier", "full"): []},
                cluster_map={}, issuer_map={},
                accounting=er.AccountingInput(manifest_n=0), registration=reg,
            )
        assert e.value.code == "ENDPOINTS_SHA_MISMATCH"

    def test_audit_flags_fail_the_audit(self):
        reg = make_reg(mode="tune")
        audit = er.audit_leakage(
            [], mode="tune", registration=reg,
            prospective_labels_loaded=True, prospective_outputs_in_tune=True,
            prompt_corpus_hit=True, outcome_conditioned_selection=True,
        )
        assert audit["passed"] is False
        assert audit["findings"] == [
            "outcome_conditioned_selection",
            "prompt_corpus_contains_prospective_identifier",
            "prospective_label_loaded_in_tune",
            "prospective_output_present",
        ]

    def test_audit_clean_pass(self):
        audit = er.audit_leakage([], mode="confirm", registration=make_reg("confirm"))
        assert audit["passed"] is True and audit["findings"] == []
        assert audit["endpoints_sha256"] == er.load_registry().sha256


# ------------------------------------------------------------- error codes


class TestErrorCodes:
    def test_cluster_id_missing(self):
        items = [gi(case_id(0), "f1", "span_replay", "pass")]
        with pytest.raises(er.EvalReceiptError) as e:
            receipt_for(items, cluster_map={}, issuer_map={})
        assert e.value.code == "CLUSTER_ID_MISSING"

    def test_unknown_fold_slice(self):
        with pytest.raises(er.EvalReceiptError) as e:
            receipt_for([], cluster_map={}, issuer_map={}, fold_slices=("f9",))
        assert e.value.code == "UNKNOWN_FOLD_SLICE"

    def test_unknown_baseline(self):
        with pytest.raises(er.EvalReceiptError) as e:
            receipt_for(
                [], cluster_map={}, issuer_map={},
                baselines_run=("not_a_baseline",),
            )
        assert e.value.code == "UNKNOWN_BASELINE"

    def test_duplicate_graded_item(self):
        items = [
            gi(case_id(0), "f1", "span_replay", "pass"),
            gi(case_id(0), "f1", "span_replay", "fail"),
        ]
        cm, im = maps_for(1)
        with pytest.raises(er.EvalReceiptError) as e:
            receipt_for(items, cluster_map=cm, issuer_map=im)
        assert e.value.code == "DUPLICATE_GRADED_ITEM"

    def test_bad_registry_missing_keys(self, tmp_path):
        p = tmp_path / "bad_registry.json"
        p.write_text(json.dumps({"baselines": []}), encoding="utf-8")
        with pytest.raises(er.EvalReceiptError) as e:
            er.load_registry(p)
        assert e.value.code == "BAD_REGISTRY"

    def test_bad_registry_missing_file(self, tmp_path):
        with pytest.raises(er.EvalReceiptError) as e:
            er.load_registry(tmp_path / "absent.json")
        assert e.value.code == "BAD_REGISTRY"

    def test_bad_registration(self):
        reg = make_reg()
        del reg["mode"]
        with pytest.raises(er.EvalReceiptError) as e:
            er.build_receipt(
                graded_by_construction={("cheap_extractor_no_frontier", "full"): []},
                cluster_map={}, issuer_map={},
                accounting=er.AccountingInput(manifest_n=0), registration=reg,
            )
        assert e.value.code == "BAD_REGISTRATION"

    def test_display_forbidden_word(self):
        with pytest.raises(er.EvalReceiptError) as e:
            er.lint_display_text("this proves the system works")
        assert e.value.code == "DISPLAY_FORBIDDEN_WORD"

    def test_every_code_asserted_and_listed(self):
        asserted = {
            "PROSPECTIVE_FOLD_REFUSED", "SEALED_FOLD_REFUSED", "ENDPOINTS_SHA_MISMATCH",
            "CLUSTER_ID_MISSING", "UNKNOWN_FOLD_SLICE", "UNKNOWN_BASELINE",
            "DUPLICATE_GRADED_ITEM", "BAD_REGISTRY", "BAD_REGISTRATION",
            "BAD_COVERAGE", "BAD_METRIC_VALUE", "DISPLAY_FORBIDDEN_WORD",
        }
        assert asserted == set(er.CODES)


# ------------------------------------------------------------- baselines / ablations


class TestBaselinesAblations:
    def test_ablation_id_rules(self):
        assert er.ablation_id_from_switches([]) == "full"
        assert er.ablation_id_from_switches(["group_transfer", "novelty"]) == "minus_group_transfer+minus_novelty"
        assert er.ablation_id_from_switches(["novelty", "group_transfer"]) == "minus_group_transfer+minus_novelty"

    def test_cost_at_fixed_recall(self):
        items_a = [gi(case_id(i), f"f{i % 5 + 1}", "material_routing", "hit") for i in range(4)]  # recall 1.0 on f1-f4
        items_b = [gi(case_id(i), f"f{i % 5 + 1}", "material_routing", "hit") for i in range(3)]
        items_b.append(gi(case_id(3), "f4", "material_routing", "miss"))  # recall 0.75
        cm, im = maps_for(4)
        r = er.build_receipt(
            graded_by_construction={
                ("cheap_extractor_no_frontier", "full"): items_a,
                ("proposed_cascade", "full"): items_b,
            },
            cluster_map=cm, issuer_map=im,
            accounting=er.AccountingInput(manifest_n=4),
            registration=make_reg(),
            costs=[
                er.CostRecord("cheap_extractor_no_frontier", "full", 600, 400),
                er.CostRecord("proposed_cascade", "full", 5000, 5000),
            ],
        )
        cheap = row(r, "cost_at_fixed_recall", "f5", baseline="cheap_extractor_no_frontier")
        cascade = row(r, "cost_at_fixed_recall", "f5", baseline="proposed_cascade")
        assert cheap["value"] == 1000.0 and cheap["status"] == "measured"
        assert cascade["value"] is None and "recall_below_0.95" in cascade["display_text"]
        hist = row(r, "cost_at_fixed_recall", "all_historical")
        assert hist["value"] is None and "f5_only_metric" in hist["display_text"]

    def test_frontier_audit_offsubset_null(self):
        r = er.build_receipt(
            graded_by_construction={("cheap_extractor_no_frontier", "full"): []},
            cluster_map={}, issuer_map={},
            accounting=er.AccountingInput(manifest_n=0), registration=make_reg(),
            baselines_run=("cheap_extractor_no_frontier", "frontier_only_audit"),
        )
        m = [x for x in r["metrics"] if x["baseline_id"] == "frontier_only_audit" and x["metric_id"] == "pair_precision"]
        assert m and m[0]["value"] is None
        assert "not_in_audit_subset" in m[0]["display_text"]
        assert set(r["baselines_run"]) == {"cheap_extractor_no_frontier", "frontier_only_audit"}


# ------------------------------------------------------------- receipt assembly


class TestReceiptAssembly:
    def test_endpoint_coverage_counts(self):
        reg = er.load_registry()
        registry_ids = {m.metric_id for m in reg.metrics} | {reg.undecidable_metric_id}
        r = receipt_for([gi(case_id(0), "f1", "span_replay", "pass")], cluster_map={case_id(0): "g0"}, issuer_map={case_id(0): "cik:0000000001"})
        emitted = {m["metric_id"] for m in r["metrics"]}
        print(f"registry endpoints={len(registry_ids)} receipt endpoints={len(emitted)}")
        assert emitted == registry_ids  # every endpoint present, none invented
        slices = {m["fold_slice"] for m in r["metrics"]}
        assert slices == {"all_historical", "f1", "f2", "f3", "f4", "f5"}
        per_combo = {(m["baseline_id"], m["ablation_id"], m["fold_slice"], m["metric_id"]) for m in r["metrics"]}
        assert len(per_combo) == len(registry_ids) * 6  # 28 x 6 grid complete

    def test_receipt_validates_against_schema(self):
        assert RECEIPT_SCHEMA_PATH.is_file(), f"receipt schema missing (fail closed): {RECEIPT_SCHEMA_PATH}"
        items = [
            gi(case_id(0), "f1", "incremental_amount", "correct", template="capital_allocation_event.v1"),
            gi(case_id(1), "f1", "material_routing", "hit", template="demand_guidance_contract_event.v1"),
            gi(case_id(2), "f1", "unsupported_transfer", "no", template="strategic_product_partnership_event.v1"),
            gi(case_id(3), "f1", "revision_hit", "unmatured", template="capital_allocation_event.v1"),
            gi(case_id(4), "f1", "net_return", "observed", candidate_value=0.011, template="capital_allocation_event.v1"),
        ]
        cm, im = maps_for(5)
        r = receipt_for(items, cluster_map=cm, issuer_map=im, notes="synthetic")
        schema = json.loads(RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(r)

    def test_determinism_permuted_input_byte_identical(self):
        n = 34
        items = [
            gi(case_id(i), f"f{i % 5 + 1}", "material_routing", "hit" if i % 8 else "miss")
            for i in range(n)
        ] + [
            gi(case_id(i), f"f{i % 5 + 1}", "incremental_amount", "correct" if i % 6 else "wrong_value")
            for i in range(n)
        ]
        cm, im = maps_for(n)
        r1 = receipt_for(items, cluster_map=cm, issuer_map=im)
        r2 = receipt_for(list(reversed(items)), cluster_map=cm, issuer_map=im)
        assert er.canonical_json(r1) == er.canonical_json(r2)
        r3 = receipt_for(items, cluster_map=cm, issuer_map=im)
        assert er.canonical_json(r1) == er.canonical_json(r3)
        assert r1["registration"]["bootstrap_seed"] == 20261012
        assert r1["registration"]["bootstrap_reps"] == 9999
        # the pooled sample clears the reporting floor -> governing interval present
        pooled = row(r1, "material_event_routing_recall")
        assert pooled["interval"]["method"] == "cluster_bootstrap_percentile"

    def test_forbidden_keys_stripped_and_recorded(self):
        reg = dict(make_reg())
        reg["confidence"] = "high"  # injected forbidden key
        items = [gi(case_id(0), "f1", "span_replay", "pass", gold_value={"score": 1})]
        r = er.build_receipt(
            graded_by_construction={("cheap_extractor_no_frontier", "full"): items},
            cluster_map={case_id(0): "g0"}, issuer_map={case_id(0): "cik:0000000001"},
            accounting=er.AccountingInput(manifest_n=1), registration=reg,
            injection_findings=[{"case_id": case_id(0), "quote": "ignore previous instructions", "action": "recorded_and_ignored"}],
        )
        blob = er.canonical_json(r)
        for bad in ("confidence", "score"):
            assert f'"{bad}"' not in blob
        assert "stripped_fields=registration.confidence" in (r["notes"] or "")
        assert r["injection_findings"][0]["action"] == "recorded_and_ignored"

    def test_prophet_flags_and_authority_frozen(self):
        r = receipt_for([], cluster_map={}, issuer_map={})
        assert r["authority"] == "context_only"
        assert r["prophet_flags"] == {
            "may_rank": False, "may_size": False, "may_gate": False, "prophet_authority": False,
        }
        assert r["registration"]["owner_status"] == "PROPOSED-OWNER-FREEZES"

    def test_zero_denominator_null_never_zero_never_exception(self):
        # graded items exist, but none lands in this metric's denominator
        items = [gi(case_id(0), "f1", "span_replay", "pass")]
        r = receipt_for(items, cluster_map={case_id(0): "g0"}, issuer_map={case_id(0): "cik:0000000001"})
        m = row(r, "critical_numeric_correctness_auto_published")
        assert m["value"] is None and m["n"] == 0
        assert m["status"] == "null_printed"
        assert "zero_denominator" in m["display_text"]


# ------------------------------------------------------------- worked cases 1-5 (receipt level)


class TestWorkedCases:
    """A3 section 5 cases 1-5 as receipt-level expectations."""

    def _base_maps(self, n):
        return maps_for(n)

    def test_case1_correction_supersedes(self):
        items = [
            gi(case_id(0), "f3", "incremental_amount", "correct", template="capital_allocation_event.v1"),
            gi(case_id(0), "f3", "remaining_authorization", "correct", template="capital_allocation_event.v1"),
            gi(case_id(0), "f3", "executed_amount", "correct", template="capital_allocation_event.v1"),
            gi(case_id(0), "f3", "correction_replay", "success"),
        ]
        cm, im = self._base_maps(1)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        m = row(r, "critical_numeric_correctness_auto_published", slice_label="f3")
        assert m["value"] == 1.0 and m["n"] == 3  # slot_contrib_to_98 = [True]*3
        assert row(r, "correction_replay_success", slice_label="f3")["value"] == 1.0

    def test_case2_invalid_published_packet_still_in_denom(self):
        # auto-published F3-violating packet: slot graded wrong, still in the 98% denom
        items = [gi(case_id(0), "f2", "stated_amount", "wrong_value", template="demand_guidance_contract_event.v1")]
        cm, im = self._base_maps(1)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        m = row(r, "critical_numeric_correctness_auto_published", slice_label="f2")
        assert m["value"] == 0.0 and m["n"] == 1  # claimed auto_published -> in denom
        t = thresh_row(r, "critical_numeric_correctness_auto_published")
        assert t["crossing"] == "not_evaluable"

    def test_case3_tam_routing_miss(self):
        items = [gi(case_id(0), "f1", "material_routing", "miss", template="demand_guidance_contract_event.v1")]
        cm, im = self._base_maps(1)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        m = row(r, "material_event_routing_recall", slice_label="f1")
        assert m["value"] == 0.0 and m["n"] == 1  # recall_denom=true, hit=false

    def test_case4_unsupported_supplier_assertion(self):
        items = [gi(case_id(0), "f4", "unsupported_transfer", "yes", template="strategic_product_partnership_event.v1")]
        cm, im = self._base_maps(1)
        r = receipt_for(items, cluster_map=cm, issuer_map=im)
        m = row(r, "unsupported_ticker_to_supplier_count", slice_label="f4")
        assert m["value"] == 1.0  # contributes_to_zero_bar = 1
        assert thresh_row(r, "unsupported_ticker_to_supplier_count", slice_label="f4")["crossing"] == "not_evaluable"

    def test_case5_defer_excluded_from_denom(self):
        items = [  # case_a slots auto-published; case_e deferred, emits no slot items
            gi(case_id(0), "f3", "incremental_amount", "correct", template="capital_allocation_event.v1"),
            gi(case_id(1), "f5", "defer_match", "matched", template="capital_allocation_event.v1"),
        ]
        cm, im = self._base_maps(2)
        acc = er.AccountingInput(
            manifest_n=2, auto_published=1, deferred=1,
            manifest_case_ids=(case_id(0), case_id(1)),
            output_case_ids=(case_id(0), case_id(1)),
        )
        r = receipt_for(items, cluster_map=cm, issuer_map=im, accounting=acc)
        f5 = row(r, "critical_numeric_correctness_auto_published", slice_label="f5")
        assert f5["n"] == 0 and f5["value"] is None  # deferred case out of the 98% denom
        assert row(r, "defer_disposition_match", slice_label="f5")["value"] == 1.0
        assert row(r, "disposition_accounting_complete")["value"] == 1.0  # deferred +1 counted
