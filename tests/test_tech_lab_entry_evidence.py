"""The UI must preserve the registered result and refuse invented/uncoupled evidence."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil

from bs4 import BeautifulSoup
import pytest

from scripts import tech_lab_entry_evidence as evidence

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def sources(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, "TRUSTED_SHA256", dict(evidence.TRUSTED_SHA256))
    paths = [evidence.SPEC_PATH, *[evidence.STUDY_DIR / name for name in
             ("report.json", "verification.json", "timing_attribution.json")]]
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / relative, target)
    return tmp_path


def edit(root, filename, mutation, *, rebind=False, trust=False):
    relative = evidence.SPEC_PATH if filename == "spec" else evidence.STUDY_DIR / filename
    path = root / relative
    data = json.loads(path.read_text())
    mutation(data)
    path.write_text(json.dumps(data, allow_nan=True) + "\n")
    if rebind:
        report_path = root / evidence.STUDY_DIR / "report.json"
        report = json.loads(report_path.read_text())
        spec_sha = hashlib.sha256((root / evidence.SPEC_PATH).read_bytes()).hexdigest()
        report["spec_sha256"] = spec_sha
        report_path.write_text(json.dumps(report, allow_nan=True) + "\n")
        receipt_path = root / evidence.STUDY_DIR / "verification.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["spec_sha256"] = spec_sha
        receipt["report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
        receipt_path.write_text(json.dumps(receipt) + "\n")
    if rebind or trust:
        trust_synthetic_fixture(root)


def trust_synthetic_fixture(root):
    # Tests of semantic validation deliberately use a new synthetic trust anchor.
    # Production constants remain bound to the accepted historical artifacts.
    for relative in evidence.TRUSTED_SHA256:
        path = root / relative
        if path.exists():
            evidence.TRUSTED_SHA256[relative] = hashlib.sha256(path.read_bytes()).hexdigest()



def test_real_registered_artifacts_project_complete_negative_result(sources):
    result = evidence.load_entry_evidence(sources)
    assert result["available"] is True
    assert result["promotion_eligible"] is False
    assert result["universe_count"] == 11
    assert result["unique_events"] == 2851
    assert result["verified_rows"] == 5702
    assert result["comparison_count"] == 11
    assert result["adjusted_intervals_excluding_zero"] == 0
    assert len(result["rows_by_horizon"][21]) == len(result["rows_by_horizon"][63]) == 12
    assert result["t12_provisional_events"] == 368
    assert result["t12_events"] == 480
    assert result["auxiliary_available"] is True
    assert len(result["auxiliary_rows"]) == 4
    assert all(r["timing_residual"] < 0 for r in result["auxiliary_rows"])


def test_report_values_are_not_handwritten_display_estimates(sources):
    result = evidence.load_entry_evidence(sources)
    source = json.loads((sources / evidence.STUDY_DIR / "report.json").read_text())
    for horizon, rows in result["rows_by_horizon"].items():
        for row in rows:
            original = next(r for r in source["arm_summaries"] if r["arm"] == row["id"] and r["horizon"] == horizon)
            assert row["net_return"] == original["net_return"]
            assert row["net_excess"] == original["net_excess"]
            assert row["positive_net_rate"] == original["net_positive_rate_date_weighted"]
            assert row["retention"] == original["signal_retention"]


@pytest.mark.parametrize("filename", ["report.json", "verification.json"])
def test_missing_primary_artifact_is_not_sample_data(sources, filename):
    (sources / evidence.STUDY_DIR / filename).unlink()
    result = evidence.load_entry_evidence(sources)
    assert result["available"] is False
    assert result["reason_code"] == "FileNotFoundError"
    assert "rows_by_horizon" not in result
    assert result["promotion_eligible"] is False


def test_missing_spec_is_not_optional(sources):
    (sources / evidence.SPEC_PATH).unlink()
    assert evidence.load_entry_evidence(sources)["available"] is False


def test_missing_optional_control_does_not_hide_primary_null(sources):
    (sources / evidence.STUDY_DIR / "timing_attribution.json").unlink()
    result = evidence.load_entry_evidence(sources)
    assert result["available"] is True
    assert result["auxiliary_available"] is False
    assert result["auxiliary_rows"] == []
    assert result["adjusted_intervals_excluding_zero"] == 0


def test_edited_financial_result_without_receipt_is_refused(sources):
    edit(sources, "report.json", lambda d: d["arm_summaries"][0].update(net_return=.99))
    result = evidence.load_entry_evidence(sources)
    assert result["reason_code"] == "UNPINNED_EVIDENCE"
    assert result["available"] is False


def test_edited_protocol_without_matching_source_is_refused(sources):
    edit(sources, "spec", lambda d: d.update(primary_round_trip_cost_bps=0))
    assert evidence.load_entry_evidence(sources)["reason_code"] == "UNPINNED_EVIDENCE"


@pytest.mark.parametrize("filename,mutation,code", [
    ("report.json", lambda d: d.update(promotion_eligible=True), "RESEARCH_AUTHORITY_CONTRACT"),
    ("report.json", lambda d: d.update(survivorship_biased=False), "POPULATION_LIMITATION_REQUIRED"),
    ("spec", lambda d: d.update(primary_horizon=63), "HORIZON_CONTRACT"),
    ("report.json", lambda d: d.update(fill_basis="signal_close"), "FILL_BASIS"),
    ("report.json", lambda d: d.update(primary_metric="highest_win_rate"), "PRIMARY_METRIC"),
    ("report.json", lambda d: d.update(primary_round_trip_cost_bps=0), "COST_BASIS"),
    ("report.json", lambda d: d.update(integer_primary_comparison_count=1), "REPORT_COMPARISON_BUDGET"),
    ("spec", lambda d: d["universe"].append("<script>"), "UNIVERSE_CONTRACT"),
    ("report.json", lambda d: d["arm_summaries"][0].update(promotion_eligible=True), "SUMMARY_AUTHORITY"),
    ("report.json", lambda d: d["arm_summaries"][0].update(net_positive_rate_date_weighted=1.2), "NET_POSITIVE_RATE"),
    ("report.json", lambda d: d["arm_summaries"][0].update(net_return="0.99"), "NET_RETURN"),
    ("report.json", lambda d: d["arm_summaries"][0].update(events=-1), "EVENT_COUNT"),
    ("report.json", lambda d: d["arm_summaries"][0].update(events=True), "EVENT_COUNT"),
    ("report.json", lambda d: d["arm_summaries"][0].update(signal_retention=.5), "RETENTION_CENSUS"),
    ("report.json", lambda d: d["arm_summaries"][0].update(net_return=None), "OBSERVED_ARM_METRIC_MISSING"),
    ("report.json", lambda d: d["arm_summaries"].pop(), "SUMMARY_CENSUS"),
    ("report.json", lambda d: d["arm_summaries"].__setitem__(1, copy.deepcopy(d["arm_summaries"][0])), "DUPLICATE_SUMMARY"),
    ("report.json", lambda d: d["primary_comparisons"][0].update(delta=.99), "CONTRAST_ARITHMETIC"),
    ("report.json", lambda d: d["primary_comparisons"][0].update(familywise_ci=[1, -1]), "ADJUSTED_INTERVAL"),
    ("report.json", lambda d: d["primary_comparisons"][0].update(honest_n_floor_met="yes"), "SAMPLE_FLOOR_TYPE"),
    ("report.json", lambda d: d["primary_comparisons"].__setitem__(0, None), "CONTRAST_OBJECT"),
    ("report.json", lambda d: d["technical_core_strata_descriptive"].pop(), "PROVISIONAL_CENSUS"),
    ("verification.json", lambda d: d.update(status="STARTED"), "RECEIPT_STATUS"),
    ("verification.json", lambda d: d.update(native_source=[]), "NATIVE_RECEIPT_OBJECT"),
    ("verification.json", lambda d: d["row_verification"].update(all_price_fill_cost_and_context_checks=False), "VERIFICATION_SCOPE"),
])
def test_semantic_contract_survives_a_rehashed_fixture(sources, filename, mutation, code):
    # Synthetic adversarial fixture only. A fresh digest cannot grant a new meaning.
    edit(sources, filename, mutation, rebind=filename != "verification.json", trust=True)
    result = evidence.load_entry_evidence(sources)
    assert result["available"] is False
    assert result["reason_code"] == code
    assert result["promotion_eligible"] is False


def test_nonstandard_numeric_json_is_rejected_before_projection(sources):
    edit(sources, "report.json", lambda d: d["arm_summaries"][0].update(net_return=float("nan")), rebind=True)
    assert evidence.load_entry_evidence(sources)["reason_code"] == "NONFINITE_JSON"


def test_duplicate_json_keys_are_not_last_value_wins(sources):
    path = sources / evidence.STUDY_DIR / "report.json"
    path.write_text('{"promotion_eligible": true, "promotion_eligible": false}')
    trust_synthetic_fixture(sources)
    assert evidence.load_entry_evidence(sources)["reason_code"] == "DUPLICATE_JSON_KEY"


def test_bad_auxiliary_binding_is_local_to_auxiliary(sources):
    edit(sources, "timing_attribution.json", lambda d: d.update(primary_report_sha256="0" * 64), trust=True)
    result = evidence.load_entry_evidence(sources)
    assert result["available"] is True
    assert result["auxiliary_available"] is False
    assert result["auxiliary_reason_code"] == "AUXILIARY_BINDING"


def test_auxiliary_cannot_acquire_significance_or_live_authority(sources):
    edit(sources, "timing_attribution.json", lambda d: d.update(statistical_inference={"p": .001}), trust=True)
    result = evidence.load_entry_evidence(sources)
    assert result["available"] is True
    assert result["auxiliary_reason_code"] == "AUXILIARY_AUTHORITY"


def test_source_symlink_must_stay_in_qualified_root(sources, tmp_path):
    path = sources / evidence.STUDY_DIR / "report.json"
    outside = tmp_path.parent / (tmp_path.name + "-outside-secret.json")
    outside.write_text(path.read_text())
    path.unlink(); path.symlink_to(outside)
    result = evidence.load_entry_evidence(sources)
    assert result["reason_code"] == "SOURCE_PATH_ESCAPE"
    assert str(outside) not in json.dumps(result)


def test_oversize_source_does_not_become_a_new_report(sources):
    (sources / evidence.STUDY_DIR / "report.json").write_bytes(b"x" * (evidence.MAX_FILE_BYTES + 1))
    assert evidence.load_entry_evidence(sources)["reason_code"] == "SOURCE_SIZE_CONTRACT"


def test_allowlisted_projection_omits_raw_prices_and_private_runtime_paths(sources):
    result = evidence.load_entry_evidence(sources)
    rendered = json.dumps(result)
    for forbidden in ["/Volumes/", "input_manifest", "cache_name", "source_path", "git_blob_sha", "checked_worktree_head", "environment"]:
        assert forbidden not in rendered


def render_partial(payload):
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from markupsafe import Markup, escape
    env = Environment(loader=FileSystemLoader(REPO / "templates"), autoescape=select_autoescape(default=True))
    def translate(en, zh):
        return Markup('<span class="l-en">{}</span><span class="l-zh">{}</span>').format(escape(en), escape(zh))
    return env.get_template("partials/entry_regime_evidence.html.j2").render(entry_evidence=payload, t=translate)


def test_real_render_contains_all_arms_and_never_labels_a_row_a_live_buy(sources):
    html = render_partial(evidence.load_entry_evidence(sources))
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.select('[data-er-results="21"] tbody tr')) == 12
    assert len(soup.select('[data-er-results="63"] tbody tr')) == 12
    assert len(soup.select('.er-contrasts tbody tr')) == 11
    assert soup.select_one('[data-er-view="63"]').has_attr("hidden")
    assert not soup.select_one('[data-er-view="21"]').has_attr("hidden")
    assert soup.select_one('[data-er-horizon="21"]')["aria-pressed"] == "true"
    assert "56.16%" in soup.get_text()
    assert "54.69%" in soup.get_text()
    assert "368 / 480" in soup.get_text()
    assert "RESEARCH ONLY" in soup.get_text()
    assert "does not establish an improvement" in soup.get_text()
    assert "not a compounded or capital-constrained portfolio" in soup.get_text()
    assert "same stock and calendar month" in soup.get_text()
    assert "No significance or promotion" in soup.get_text()
    assert "\u672a\u664b\u5347\u5b9e\u76d8" in soup.get_text()
    assert "\\u672a" not in soup.get_text()
    assert not soup.select('a[href*="trade"],button[data-action="buy"]')


def test_unavailable_render_has_no_statistics_or_synthetic_success():
    html = render_partial({"available": False, "reason_code": "REPORT_RECEIPT_DIGEST"})
    soup = BeautifulSoup(html, "html.parser")
    assert soup.select_one('[data-er-state="unavailable"]')
    assert not soup.select("table,.er-metrics")
    assert "No statistics, sample results" in soup.get_text()


def test_unavailable_reason_is_escaped_not_executed():
    html = render_partial({"available": False, "reason_code": '<img src=x onerror="alert(1)">'})
    soup = BeautifulSoup(html, "html.parser")
    assert not soup.select("img,script")
    assert "<img src=x" in soup.get_text()



def test_actual_builder_escapes_unavailable_reason_and_retains_existing_views(tmp_path, monkeypatch):
    from scripts import build_tech_lab as builder
    (tmp_path / "templates").symlink_to(REPO / "templates", target_is_directory=True)
    monkeypatch.setattr(builder.config, "ROOT", tmp_path)
    payload = {"available": False, "reason_code": '<img src=x onerror="alert(1)">'}
    monkeypatch.setattr(builder, "load_entry_evidence", lambda root: payload)
    assert builder.main() == 0
    page = tmp_path / "site/tech_lab.html"
    assert page.exists()
    soup = BeautifulSoup(page.read_text(), "html.parser")
    panel = soup.select_one("#tab-entry-evidence")
    assert panel and panel.select_one('[data-er-state="unavailable"]')
    assert not panel.select("img,script,table,.er-metrics")
    assert "<img src=x" in panel.get_text()
    assert {x["data-tab"] for x in soup.select("#tab-bar [data-tab]")} == {
        "screener", "combos", "entry-evidence", "siglab", "stock", "test"}


def test_mutually_rehashed_files_cannot_replace_the_accepted_pilot(sources):
    accepted = dict(evidence.TRUSTED_SHA256)
    edit(sources, "report.json",
         lambda d: d["arm_summaries"][0].update(net_positive_rate_date_weighted=.99),
         rebind=True)
    evidence.TRUSTED_SHA256.update(accepted)
    assert evidence.load_entry_evidence(sources)["reason_code"] == "UNPINNED_EVIDENCE"


def test_huge_integer_is_a_panel_local_refusal(sources):
    edit(sources, "report.json", lambda d: d["arm_summaries"][0].update(net_return=10**400),
         rebind=True)
    result = evidence.load_entry_evidence(sources)
    assert result["available"] is False and result["reason_code"] == "OverflowError"


@pytest.mark.parametrize("filename,primary_available", [
    ("report.json", False), ("timing_attribution.json", True)])
def test_deep_json_is_local_to_its_evidence_panel(sources, filename, primary_available):
    path = sources / evidence.STUDY_DIR / filename
    path.write_text('{"x":' + '[' * 2000 + '0' + ']' * 2000 + '}')
    trust_synthetic_fixture(sources)
    result = evidence.load_entry_evidence(sources)
    assert result["available"] is primary_available
    key = "auxiliary_reason_code" if primary_available else "reason_code"
    # Some Python JSON implementations decode this depth iteratively; either
    # parser refusal or typed schema refusal must stay local to this panel.
    expected_schema = "AUXILIARY_SCHEMA" if primary_available else "REPORT_SCHEMA"
    assert result[key] in {"RecursionError", expected_schema}


def copy_cohort(root):
    for name in ["context_report.json", "metadata_receipt.json"]:
        relative = evidence.COHORT_DIR / name
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / relative, root / relative)


def test_recovered_cohort_projection_preserves_the_original_denominators(sources):
    copy_cohort(sources)
    value = evidence.load_entry_evidence(sources)["cohort"]
    assert value["available"] is True and value["promotion_eligible"] is False
    assert value["screen_retained"] == 23065
    assert (value["joined"], value["unavailable"]) == (22860, 205)
    assert (value["primary_any"], value["primary_none"]) == (14441, 7332)
    assert value["outside_primary_analytic"] == 1292
    assert sum(row["any"] for row in value["directions"]) == 14441
    assert sum(row["none"] for row in value["directions"]) == 7332
    assert value["survivor_biased_events"] + value["usable_source_events"] == 23065


def test_missing_cohort_report_does_not_hide_the_frozen_pilot(sources):
    value = evidence.load_entry_evidence(sources)
    assert value["available"] is True and value["cohort"]["available"] is False


def test_cohort_missing_context_cannot_disappear_from_counting(sources):
    copy_cohort(sources)
    path = sources / evidence.COHORT_DIR / "context_report.json"
    value = json.loads(path.read_text())
    value["join_status_counts"].pop("CONTEXT_WINDOW_INCOMPLETE")
    path.write_text(json.dumps(value))
    trust_synthetic_fixture(sources)
    result = evidence.load_entry_evidence(sources)
    assert result["available"] is True
    assert result["cohort"]["available"] is False
    assert result["cohort"]["reason_code"] == "COHORT_JOIN_CENSUS"


def test_real_cohort_render_shows_coverage_without_inventing_success_rates(sources):
    copy_cohort(sources)
    soup = BeautifulSoup(render_partial(evidence.load_entry_evidence(sources)), "html.parser")
    cohort = soup.select_one('[data-er-cohort="available"]')
    text = cohort.get_text(" ", strip=True)
    assert all(number in text for number in ["23,065", "22,860", "205", "14,441", "7,332", "1,292"])
    assert "event counts, not success rates" in text
    assert "does not test a predictive improvement" in text
    assert "SCREEN80" in text and "first live observation" in text
