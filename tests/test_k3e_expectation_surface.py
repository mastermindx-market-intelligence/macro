"""Discriminators for EXP-1 cutoff/coverage/refusal boundaries."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import subprocess
import sys

import pytest
from lib.dataos.identity import VendorAliasTable
from engine.k3e_expectation_surface import (
    ALIASES_PATH, ATTEMPTS_PATH, OBSERVATIONS_PATH, QueryRefusal,
    inspect_expectation_surface,
)

CUT = "2026-10-02T12:00:00Z"
PROVENANCE = {"source_revision": "a" * 40, "inputs": {
    OBSERVATIONS_PATH: {"sha256": "1" * 64, "git_blob_id": "1" * 40},
    ATTEMPTS_PATH: {"sha256": "2" * 64, "git_blob_id": "2" * 40},
}}
ALIAS_PROVENANCE = deepcopy(PROVENANCE)
ALIAS_PROVENANCE["inputs"][ALIASES_PATH] = {
    "sha256": "3" * 64,
    "git_blob_id": "3" * 40,
}


def alias(symbol="V", security="SEC:V", ingested="2026-10-01T00:00:00Z",
          valid_from=None, valid_to=None):
    return dict(
        vendor="yahoo", vendor_symbol=symbol, security_id=security,
        valid_from=valid_from, valid_to=valid_to, ingested_at=ingested,
    )


def capture(label="one", time="2026-10-02T10:00:00Z", value=2.5,
            count=10, status="success", period="2026-12-31", provider="yfinance"):
    attempt = dict(attempt_id=label, collection_session_id=label, provider=provider,
                   ticker_compat="V", attempted_at=time, completed_at=time,
                   status=status, response_payload_hash=label, observation_count=2)
    common = dict(collection_session_id=label, attempt_id=label, provider=provider,
                  provider_record_class="earnings_estimate", provider_payload_hash=label,
                  ticker_compat="V", metric="EPS", horizon_label_raw="+1q",
                  period_end=period, provider_observed_at=time, system_observed_at=time,
                  rights_class="UNKNOWN", correction_state="original",
                  supersedes_observation_id=None, source_effective_at=None,
                  source_published_at=None)
    rows = [dict(common, observation_id=label + "-average", observation_type="average",
                 value=value, missingness_reason=None if value is not None else "UNESTIMABLE"),
            dict(common, observation_id=label + "-count", observation_type="covering_analyst_count",
                 value=count, missingness_reason=None if count is not None else "UNAVAILABLE")]
    return rows, [attempt]


def inspect(rows, attempts, **kwargs):
    parameters = dict(source_provenance=PROVENANCE, ticker="V", metric="EPS",
                      horizon="+1q", as_of=CUT, composed_at="2026-10-03T12:00:00Z")
    parameters.update(kwargs)
    return inspect_expectation_surface(rows, attempts, **parameters)


def payload(rows, attempts, **kwargs):
    return inspect(rows, attempts, **kwargs)["semantic_payload"]


def selected(result, key="last_structurally_supported_snapshot"):
    snap = result[key]["snapshot"]
    return snap["selected_observation"] if snap else None


def test_future_rows_attempts_and_duplicates_do_not_leak():
    rows, attempts = capture()
    original = inspect(rows, attempts)
    future_rows, future_attempts = capture("future", "2026-10-02T13:00:00Z", 999)
    # Future duplicate attempt ID cannot invalidate a prior receipt.
    future_attempts[0]["attempt_id"] = "one"
    future_rows[0]["rights_class"] = "RIGHTS_BLOCKED"
    changed = inspect(rows + future_rows, attempts + future_attempts)
    assert changed["semantic_payload"] == original["semantic_payload"]
    assert changed["semantic_digest"] == original["semantic_digest"]
    assert changed["input_provenance"] != original["input_provenance"]
    assert "future" not in json.dumps(changed["semantic_payload"])


def test_later_attempt_completion_and_outcome_are_redacted():
    rows, attempts = capture()
    attempts[0].update(completed_at="2026-10-02T13:00:00Z", latency_ms=99,
                       http_status=200, safe_error_class=None)
    first = payload(rows, attempts)
    assert selected(first) is None
    latest = first["latest_attempt"]["snapshot"]
    assert latest["derived_query_state"] == "INCOMPLETE_AT_CUTOFF"
    assert latest["status"] is None and latest["completed_at"] is None
    assert "response_payload_hash" not in latest
    attempts[0].update(status="http_429", http_status=429, latency_ms=999,
                       safe_error_class="rate_limit", observation_count=0,
                       response_payload_hash="later-result")
    assert payload(rows, attempts) == first


@pytest.mark.parametrize("cutoff", ["2026-10-02T12:00:00", "bad",
                                   "2026-10-02T12:00:00+01:00"])
def test_malformed_naive_nonutc_query_refused(cutoff):
    with pytest.raises(QueryRefusal, match="INVALID_UTC_CLOCK"):
        inspect([], [], as_of=cutoff)


@pytest.mark.parametrize("field", ["system_observed_at", "provider_observed_at"])
@pytest.mark.parametrize("clock", [None, "bad", "2026-10-02T10:00:00"])
def test_malformed_source_clock_excluded(field, clock):
    rows, attempts = capture()
    rows[0][field] = clock
    result = payload(rows, attempts)
    assert selected(result) is None
    assert result["denominators"]["invalid_or_inconsistent_excluded_records"] == 2


def test_publication_after_capture_invalid_but_future_economic_date_valid():
    rows, attempts = capture()
    rows[0]["source_effective_at"] = "2027-01-01T00:00:00Z"
    assert selected(payload(rows, attempts))["value"] == 2.5
    rows[0]["source_published_at"] = "2026-10-02T11:00:00Z"
    result = payload(rows, attempts)
    assert selected(result) is None
    assert result["denominators"]["reason_counts"]["PUBLICATION_AFTER_CAPTURE"] == 1


@pytest.mark.parametrize("change", ["missing", "duplicate", "session", "payload", "order"])
def test_receipt_integrity(change):
    rows, attempts = capture()
    if change == "missing":
        attempts = []
    elif change == "duplicate":
        attempts *= 2
    elif change == "session":
        attempts[0]["collection_session_id"] = "wrong"
    elif change == "payload":
        attempts[0]["response_payload_hash"] = "wrong"
    else:
        attempts[0]["completed_at"] = "2026-10-02T09:00:00Z"
    assert selected(payload(rows, attempts)) is None


def test_cross_session_count_cannot_support_other_estimate():
    rows, attempts = capture(count=None)
    newer, receipts = capture("two", "2026-10-02T11:00:00Z", value=None, count=20)
    result = payload(rows + newer, attempts + receipts)
    assert selected(result) is None
    assert selected(result, "latest_captured_snapshot")["value"] is None


@pytest.mark.parametrize("value,count,supported", [
    (0, 10, True), (None, 10, False), (2, 0, False),
    (2, None, False), (2, -1, False), (2, 1.5, False), (2, True, False),
])
def test_zero_null_and_integral_count_law(value, count, supported):
    rows, attempts = capture(value=value, count=count)
    result = payload(rows, attempts)
    assert (selected(result) is not None) is supported
    latest = result["latest_captured_snapshot"]["snapshot"]
    if count == 0:
        assert latest["provider_reported_covering_analyst_count"] == 0
    assert result["normalized_baseline"]["value"] is None


@pytest.mark.parametrize("status,value", [("partial", 3.5), ("null", None), ("error", None)])
def test_failed_partial_null_never_erase_prior_supported(status, value):
    rows, attempts = capture()
    newer, receipts = capture("two", "2026-10-02T11:00:00Z", value=value, status=status)
    newer[0]["correction_state"] = "superseding"
    newer[0]["supersedes_observation_id"] = "one-average"
    result = payload(rows + newer, attempts + receipts)
    assert selected(result)["value"] == 2.5
    assert result["last_structurally_supported_snapshot"]["snapshot"]["age_seconds"] == 7200
    assert result["latest_captured_snapshot"]["snapshot"]["attempt_status"] == status
    assert selected(result, "latest_captured_snapshot")["supersedes_observation_id"] == "one-average"


@pytest.mark.parametrize("period,continuity", [
    ("2027-03-31", "NATIVE_PERIOD_CHANGED_NO_REVISION_INFERENCE"),
    (None, "ANCHOR_UNAVAILABLE"),
])
def test_native_rollover_and_missing_anchor(period, continuity):
    rows, attempts = capture()
    newer, receipts = capture("two", "2026-10-02T11:00:00Z", status="partial", period=period)
    result = payload(rows + newer, attempts + receipts)
    assert result["period_continuity"] == continuity
    assert selected(result)["period_end"] == "2026-12-31"


def test_equal_clock_conflicting_snapshots_no_lexicographic_pick():
    rows, attempts = capture()
    other, receipts = capture("two", value=999)
    result = payload(rows + other, attempts + receipts)
    assert selected(result) is None
    assert result["latest_captured_snapshot"]["status"] == "UNESTIMABLE"
    assert len(result["latest_captured_snapshot"]["candidates"]) == 2


def test_incoherent_period_fields_and_duplicate_values_excluded():
    rows, attempts = capture()
    rows[1]["period_end"] = "2027-03-31"
    assert selected(payload(rows, attempts)) is None
    rows, attempts = capture()
    duplicate = dict(rows[0], observation_id="other-average", value=999)
    result = payload(rows + [duplicate], attempts)
    assert selected(result) is None
    assert result["denominators"]["invalid_or_inconsistent_excluded_records"] == 3


def test_missingness_is_not_correction_state_and_numeric_with_reason_invalid():
    rows, attempts = capture()
    rows[0]["correction_state"] = "UNESTIMABLE"
    assert selected(payload(rows, attempts))["value"] == 2.5
    rows[0]["missingness_reason"] = "UNESTIMABLE"
    result = payload(rows, attempts)
    assert selected(result) is None
    assert result["denominators"]["true_missing_records"] == 0


def test_unknown_or_caller_labels_ids_cannot_enable_normalized_value():
    rows, attempts = capture()
    for right in ("UNKNOWN", "PERMITTED", "LICENSED"):
        for row in rows:
            row.update(rights_class=right, issuer_ref="caller-issuer",
                       security_ref="caller-security", unit="USD", currency="USD", basis="GAAP")
        result = payload(rows, attempts)
        assert result["normalized_baseline"]["value"] is None
        assert "NORMALIZED_CONSUMER_ADMISSION_NOT_GRANTED" in result["normalized_baseline"]["reasons"]
        assert result["normalized_baseline"]["rights_state"] == "UNKNOWN"
        assert "SOURCE_USE_RIGHTS_UNKNOWN" in result["normalized_baseline"]["reasons"]
    rows[0]["rights_class"] = "RIGHTS_BLOCKED"
    assert payload(rows, attempts)["normalized_baseline"]["status"] == "RIGHTS_BLOCKED"


def test_absent_ticker_is_successful_typed_absence():
    rows, attempts = capture()
    result = payload(rows, attempts, ticker="ABSENT")
    assert result["latest_captured_snapshot"]["status"] == "UNAVAILABLE"
    assert result["normalized_baseline"]["status"] == "UNAVAILABLE"
    assert result["denominators"]["capture_clock_bounded_relevant_records"] == 0


def test_vintage_bytes_dimensions_identity_composition_and_nonmutation():
    rows, attempts = capture()
    original = deepcopy((rows, attempts, PROVENANCE))
    first = inspect(rows, attempts)
    repeated = inspect(rows, attempts, composed_at="2026-10-04T00:00:00Z")
    assert first["semantic_payload"] == repeated["semantic_payload"]
    assert first["semantic_digest"] == repeated["semantic_digest"]
    assert first["composition_time"] != repeated["composition_time"]
    for mutate in ("revision", "bytes", "blob"):
        vintage = deepcopy(PROVENANCE)
        if mutate == "revision":
            vintage["source_revision"] = "b" * 40
        else:
            vintage["inputs"][ATTEMPTS_PATH]["sha256" if mutate == "bytes" else "git_blob_id"] = "3" * (64 if mutate == "bytes" else 40)
        assert payload(rows, attempts, source_provenance=vintage)["query_identity"] != first["semantic_payload"]["query_identity"]
    assert (rows, attempts, PROVENANCE) == original


def test_cli_fixture_reads_only_explicit_commit_and_refuses_moving_ref(tmp_path):
    pd = pytest.importorskip("pandas")
    repository = tmp_path / "fixture"
    repository.mkdir()
    rows, attempts = capture()
    alias_records = [dict(
        vendor="yahoo", vendor_symbol="V", security_id="SEC:V",
        valid_from=None, valid_to=None,
        ingested_at=pd.Timestamp("2026-10-01 00:00:00"),
    )]
    for path, records in (
        (OBSERVATIONS_PATH, rows),
        (ATTEMPTS_PATH, attempts),
        (ALIASES_PATH, alias_records),
    ):
        destination = repository / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(records).to_parquet(destination)
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repository), *args], text=True).strip()
    git("init", "-q")
    git("add", "data")
    git("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "synthetic fixture")
    revision = git("rev-parse", "HEAD")
    script = Path(__file__).resolve().parents[1] / "scripts/query_k3e_expectation_surface.py"
    args = [sys.executable, "-B", str(script), "--repository", str(repository),
            "--source-revision", revision, "--ticker", "V", "--metric", "EPS",
            "--horizon", "+1q", "--as-of", CUT]
    run = subprocess.run(args, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    semantic = result["semantic_payload"]
    assert selected(semantic)["value"] == 2.5
    assert semantic["source"]["source_revision"] == revision
    assert semantic["identity_gate"]["status"] == "CHECKED"
    assert semantic["denominators"]["identity_resolved_records"] >= 1
    expected_blob = git("rev-parse", f"{revision}:{ALIASES_PATH}")
    assert semantic["source"]["inputs"][ALIASES_PATH]["git_blob_id"] == expected_blob
    assert git("status", "--porcelain") == ""
    args[args.index(revision)] = "HEAD"
    refusal = subprocess.run(args, capture_output=True, text=True)
    assert refusal.returncode == 2
    assert json.loads(refusal.stderr)["reason"] == "FULL_IMMUTABLE_SOURCE_REVISION_REQUIRED"


def test_latest_duplicate_or_invalid_attempt_does_not_hide_degradation():
    rows, attempts = capture()
    _, later = capture("later", "2026-10-02T11:00:00Z")
    result = payload(rows, attempts + later * 2)
    assert result["latest_attempt"]["status"] == "UNESTIMABLE"
    assert selected(result)["value"] == 2.5
    later[0]["completed_at"] = None
    result = payload(rows, attempts + later)
    assert result["latest_attempt"]["snapshot"]["derived_query_state"] == "INCOMPLETE_AT_CUTOFF"
    later[0]["completed_at"] = "malformed-clock"
    result = payload(rows, attempts + later)
    assert result["latest_attempt"]["snapshot"]["derived_query_state"] == "INVALID_ATTEMPT_RECEIPT"


def test_average_is_explicit_not_synthesized_from_median_or_range():
    rows, attempts = capture()
    rows[0]["observation_type"] = "median"
    result = payload(rows, attempts)
    assert selected(result) is None
    latest = result["latest_captured_snapshot"]["snapshot"]
    assert latest["selected_raw_field"] == "average"
    assert latest["selected_observation"] is None


def test_composition_and_input_order_do_not_change_semantics():
    rows, attempts = capture()
    newer, receipts = capture("two", "2026-10-02T11:00:00Z")
    first = inspect(rows + newer, attempts + receipts)
    second = inspect(list(reversed(rows + newer)), list(reversed(attempts + receipts)))
    assert first == second


def test_invalid_full_revision_and_unpaired_provenance_refused():
    for key, value in (("source_revision", "main"), ("inputs", {})):
        malformed = deepcopy(PROVENANCE)
        malformed[key] = value
        with pytest.raises(QueryRefusal):
            inspect([], [], source_provenance=malformed)


@pytest.mark.parametrize("mutation", ["value", "missingness", "rights", "identity", "payload", "all"])
def test_not_yet_available_observations_cannot_affect_any_historical_adjudication(mutation):
    good, completed = capture("good", "2026-10-02T09:00:00Z")
    pending, unfinished = capture("pending", "2026-10-02T10:00:00Z")
    unfinished[0]["completed_at"] = "2026-10-02T13:00:00Z"
    original = inspect(good + pending, completed + unfinished)
    changed = deepcopy(pending)
    if mutation in ("value", "all"):
        changed[0]["value"] = None
        changed[0]["missingness_reason"] = "UNESTIMABLE"
    if mutation in ("missingness", "all"):
        changed[1]["value"] = None
        changed[1]["missingness_reason"] = "UNAVAILABLE"
    if mutation in ("rights", "all"):
        for row in changed:
            row["rights_class"] = "RIGHTS_BLOCKED"
    if mutation in ("identity", "all"):
        changed[0]["observation_id"] = good[0]["observation_id"]
    if mutation in ("payload", "all"):
        changed[0]["provider_payload_hash"] = "changed-future-payload"
    revised = inspect(good + changed, completed + unfinished)
    assert revised["semantic_payload"] == original["semantic_payload"]
    assert revised["semantic_digest"] == original["semantic_digest"]
    result = revised["semantic_payload"]
    assert selected(result)["observation_id"] == "good-average"
    assert result["denominators"]["capture_clock_bounded_relevant_records"] == 2
    assert result["denominators"]["true_missing_records"] == 0
    assert result["denominators"]["started_attempt_records_by_cutoff"] == 2
    assert result["denominators"]["unique_completed_valid_attempts_by_cutoff"] == 1


@pytest.mark.parametrize("completion", [None, "2026-10-02T13:00:00Z"])
@pytest.mark.parametrize("status", ["success", "future_unknown_status", None])
def test_pending_attempt_does_not_consume_final_outcome_even_invalid_labels(completion, status):
    rows, attempts = capture()
    attempts[0]["completed_at"] = completion
    original = inspect(rows, attempts)
    changed = deepcopy(attempts)
    changed[0].update(status=status, http_status=429, latency_ms="bad",
                      safe_error_class="future-error", observation_count=-1,
                      response_payload_hash="different-future-payload")
    revised = inspect(rows, changed)
    assert revised["semantic_payload"] == original["semantic_payload"]
    assert revised["semantic_digest"] == original["semantic_digest"]
    result = revised["semantic_payload"]
    assert result["latest_attempt"]["snapshot"]["derived_query_state"] == "INCOMPLETE_AT_CUTOFF"
    assert result["denominators"]["capture_clock_bounded_relevant_records"] == 0
    assert result["normalized_baseline"]["status"] == "UNAVAILABLE"
    assert result["denominators"]["reason_counts"] == {}


@pytest.mark.parametrize("completion", ["bad-clock", "2026-10-02T09:00:00Z"])
def test_malformed_or_backwards_completion_is_not_unfinished(completion):
    rows, attempts = capture()
    attempts[0]["completed_at"] = completion
    result = payload(rows, attempts)
    assert result["latest_attempt"]["snapshot"]["derived_query_state"] == "INVALID_ATTEMPT_RECEIPT"
    assert result["denominators"]["capture_clock_bounded_relevant_records"] == 2
    assert result["denominators"]["invalid_or_inconsistent_excluded_records"] == 2
    assert result["denominators"]["reason_counts"]["INVALID_LINKED_ATTEMPT"] == 2
    assert selected(result) is None


@pytest.mark.parametrize("field", ["average", "covering_analyst_count"])
@pytest.mark.parametrize("value,missingness", [
    ("bad", None), (None, None), (9, "UNESTIMABLE"),
])
def test_invalid_duplicate_fields_cannot_disappear_and_manufacture_support(field, value, missingness):
    rows, attempts = capture()
    source = next(row for row in rows if row["observation_type"] == field)
    duplicate = dict(source, observation_id="distinct-invalid-" + field,
                     value=value, missingness_reason=missingness)
    result = payload(rows + [duplicate], attempts)
    assert selected(result) is None
    assert result["latest_captured_snapshot"]["snapshot"] is None
    populations = result["denominators"]
    assert populations["capture_clock_bounded_relevant_records"] == 3
    assert populations["invalid_or_inconsistent_excluded_records"] == 3
    assert populations["valid_captured_records"] == 0
    assert populations["reason_counts"]["DUPLICATE_SNAPSHOT_FIELD"] == 1


@pytest.mark.parametrize("contradiction", ["period_end", "system_observed_at"])
def test_invalid_member_cannot_hide_group_period_or_capture_contradiction(contradiction):
    rows, attempts = capture()
    bad = dict(rows[0], observation_id="distinct-invalid-high",
               observation_type="high", value="bad")
    bad[contradiction] = ("2027-03-31" if contradiction == "period_end"
                          else "2026-10-02T10:01:00Z")
    result = payload(rows + [bad], attempts)
    assert selected(result) is None
    assert result["denominators"]["invalid_or_inconsistent_excluded_records"] == 3
    assert result["denominators"]["valid_captured_records"] == 0
    assert result["denominators"]["reason_counts"]["INCONSISTENT_SNAPSHOT_" + contradiction.upper()] == 1


def test_locatable_missing_receipt_remains_an_honest_exclusion_population():
    rows, _ = capture()
    result = payload(rows, [])
    assert result["denominators"]["capture_clock_bounded_relevant_records"] == 2
    assert result["denominators"]["invalid_or_inconsistent_excluded_records"] == 2
    assert result["denominators"]["reason_counts"]["MISSING_LINKED_ATTEMPT"] == 2


@pytest.mark.parametrize("mutation", ["append", "status", "completion", "payload", "identity"])
def test_future_start_receipt_cannot_change_missing_receipt_observation_population(mutation):
    rows, attempts = capture()
    original = inspect(rows, [])
    attempts[0].update(attempted_at="2026-10-02T13:00:00Z",
                       completed_at="2026-10-02T13:01:00Z")
    if mutation == "status":
        attempts[0].update(status=None, http_status=429, observation_count=-1)
    elif mutation == "completion":
        attempts[0]["completed_at"] = None
    elif mutation == "payload":
        attempts[0]["response_payload_hash"] = "future-payload"
    elif mutation == "identity":
        attempts[0]["attempt_id"] = "different-future-id"
    revised = inspect(rows, attempts)
    assert revised["semantic_payload"] == original["semantic_payload"]
    assert revised["semantic_digest"] == original["semantic_digest"]
    assert revised["input_provenance"]["full_input_attempt_records"] == 1
    assert original["input_provenance"]["full_input_attempt_records"] == 0
    result = revised["semantic_payload"]
    assert result["denominators"]["capture_clock_bounded_relevant_records"] == 2
    assert result["denominators"]["reason_counts"]["MISSING_LINKED_ATTEMPT"] == 2
    assert result["latest_attempt"]["status"] == "UNAVAILABLE"
    removed = inspect(rows, [])
    assert removed["semantic_payload"] == revised["semantic_payload"]
    assert removed["semantic_digest"] == revised["semantic_digest"]


@pytest.mark.parametrize("mutation", ["value", "missingness", "rights", "identity", "payload", "all"])
def test_mixed_completed_pending_attempt_id_withholds_all_observation_facts(mutation):
    completed_rows, completed_attempts = capture()
    pending_rows, pending_attempts = capture("pending", "2026-10-02T11:00:00Z")
    pending_attempts[0].update(attempt_id="one", completed_at="2026-10-02T13:00:00Z")
    for row in pending_rows:
        row["attempt_id"] = "one"
    original = inspect(completed_rows + pending_rows, completed_attempts + pending_attempts)
    changed = deepcopy(pending_rows)
    if mutation in ("value", "all"):
        changed[0].update(value=None, missingness_reason="UNESTIMABLE")
    if mutation in ("missingness", "all"):
        changed[1].update(value=None, missingness_reason="UNAVAILABLE")
    if mutation in ("rights", "all"):
        for row in changed:
            row["rights_class"] = "RIGHTS_BLOCKED"
    if mutation in ("identity", "all"):
        changed[0]["observation_id"] = completed_rows[0]["observation_id"]
    if mutation in ("payload", "all"):
        changed[0]["provider_payload_hash"] = "future-mutated-payload"
    revised = inspect(completed_rows + changed, completed_attempts + pending_attempts)
    assert revised["semantic_payload"] == original["semantic_payload"]
    assert revised["semantic_digest"] == original["semantic_digest"]
    result = revised["semantic_payload"]
    assert selected(result) is None
    assert result["latest_captured_snapshot"]["snapshot"] is None
    assert result["normalized_baseline"]["status"] == "UNAVAILABLE"
    assert result["normalized_baseline"]["rights_state"] == "UNKNOWN"
    populations = result["denominators"]
    assert populations["capture_clock_bounded_relevant_records"] == 0
    assert populations["true_missing_records"] == 0
    assert populations["invalid_or_inconsistent_excluded_records"] == 0
    assert populations["started_attempt_records_by_cutoff"] == 2
    assert populations["unique_completed_valid_attempts_by_cutoff"] == 0
    assert populations["reason_counts"] == {"DUPLICATE_ATTEMPT_ID": 2}
    assert result["latest_attempt"]["snapshot"]["derived_query_state"] == "INCOMPLETE_AT_CUTOFF"


def test_identity_gate_undated_alias_ingested_before_capture_supported():
    rows, attempts = capture()
    records = [alias(ingested="2026-10-01T00:00:00Z")]
    result = payload(rows, attempts, identity_aliases=records, source_provenance=ALIAS_PROVENANCE)
    assert result["identity_gate"]["status"] == "CHECKED"
    assert selected(result) is not None
    assert result["denominators"]["identity_resolved_records"] == (
        result["denominators"]["capture_clock_bounded_relevant_records"])


def test_identity_gate_undated_alias_ingested_after_capture_unresolved():
    rows, attempts = capture()
    records = [alias(ingested="2026-10-02T11:00:00Z")]
    result = payload(rows, attempts, identity_aliases=records, source_provenance=ALIAS_PROVENANCE)
    assert selected(result) is None
    assert result["denominators"]["identity_unresolved_records"] >= 1
    assert result["denominators"]["reason_counts"]["SECURITY_IDENTITY_UNRESOLVED_AT_CUTOFF"] >= 1


def test_identity_gate_undated_alias_ingested_after_cutoff_unresolved():
    rows, attempts = capture()
    records = [alias(ingested="2026-10-02T13:00:00Z")]
    result = payload(rows, attempts, identity_aliases=records, source_provenance=ALIAS_PROVENANCE)
    assert result["denominators"]["identity_unresolved_records"] >= 1
    assert result["identity_gate"]["query_security_id_at_cutoff"] is None


def test_identity_gate_dated_window_boundaries():
    rows, attempts = capture()
    future_from = payload(
        rows, attempts,
        identity_aliases=[alias(valid_from="2026-10-03")],
        source_provenance=ALIAS_PROVENANCE,
    )
    assert selected(future_from) is None
    exclusive_to = payload(
        rows, attempts,
        identity_aliases=[alias(valid_to="2026-10-02")],
        source_provenance=ALIAS_PROVENANCE,
    )
    assert selected(exclusive_to) is None
    assert VendorAliasTable.from_records([{
        "vendor": "yahoo", "vendor_symbol": "V", "security_id": "SEC:V",
        "valid_from": "2026-10-02", "valid_to": "2026-10-02",
    }]).resolve("yahoo", "V", date(2026, 10, 2)) is None
    resolved = payload(
        rows, attempts,
        identity_aliases=[alias(valid_from="2026-10-01", valid_to="2026-10-03")],
        source_provenance=ALIAS_PROVENANCE,
    )
    assert selected(resolved) is not None
    from datetime import datetime as dt
    resolved_dates = payload(
        rows, attempts,
        identity_aliases=[alias(
            valid_from=date(2026, 10, 1), valid_to=date(2026, 10, 3),
            ingested=dt(2026, 9, 1))],
        source_provenance=ALIAS_PROVENANCE,
    )
    assert selected(resolved_dates) is not None


def test_identity_gate_ticker_reassignment_unresolved_at_cutoff():
    rows, attempts = capture(time="2026-09-30T10:00:00Z")
    records = [
        alias(security="SEC:OLD", valid_to="2026-10-01", ingested="2026-09-01T00:00:00Z"),
        alias(security="SEC:NEW", valid_from="2026-10-01", ingested="2026-09-01T00:00:00Z"),
    ]
    result = payload(rows, attempts, identity_aliases=records, source_provenance=ALIAS_PROVENANCE)
    assert result["identity_gate"]["query_security_id_at_cutoff"] == "SEC:NEW"
    assert selected(result) is None
    control = payload(rows, attempts)
    assert selected(control) is not None


def test_identity_gate_unmapped_provider_unresolved():
    rows, attempts = capture(provider="other_vendor")
    records = [alias()]
    result = payload(
        rows, attempts, provider="other_vendor",
        identity_aliases=records, source_provenance=ALIAS_PROVENANCE,
    )
    assert result["identity_gate"]["vendor_space"] is None
    assert result["denominators"]["identity_unresolved_records"] >= 1


def test_identity_gate_none_discloses_not_checked():
    rows, attempts = capture()
    baseline = payload(rows, attempts)
    assert baseline["identity_gate"]["status"] == "NOT_CHECKED"
    assert baseline["identity_gate"]["alias_input"] is None
    assert baseline["denominators"]["identity_resolved_records"] is None
    assert baseline["denominators"]["identity_unresolved_records"] is None
    assert selected(baseline) is not None
    extra = deepcopy(PROVENANCE)
    extra["inputs"][ALIASES_PATH] = {"sha256": "9" * 64, "git_blob_id": "9" * 40}
    with_extra = payload(rows, attempts, source_provenance=extra)
    assert with_extra["query_identity"] == baseline["query_identity"]


def test_identity_gate_empty_aliases_with_pin_all_unresolved():
    rows, attempts = capture()
    result = payload(rows, attempts, identity_aliases=[], source_provenance=ALIAS_PROVENANCE)
    assert result["identity_gate"]["status"] == "CHECKED"
    assert result["denominators"]["identity_unresolved_records"] == (
        result["denominators"]["capture_clock_bounded_relevant_records"])


def test_identity_gate_provenance_refusals():
    rows, attempts = capture()
    with pytest.raises(QueryRefusal, match="ALIAS_PROVENANCE_REQUIRED"):
        payload(rows, attempts, identity_aliases=[alias()])
    bad = deepcopy(ALIAS_PROVENANCE)
    bad["inputs"][ALIASES_PATH] = dict(absent_at_revision=True)
    with pytest.raises(QueryRefusal, match="ALIAS_PROVENANCE_REQUIRED"):
        payload(rows, attempts, identity_aliases=[alias()], source_provenance=bad)
    with pytest.raises(QueryRefusal, match="RECORD_MAPPINGS_REQUIRED"):
        payload(rows, attempts, identity_aliases="not-a-list", source_provenance=ALIAS_PROVENANCE)


def test_identity_gate_ambiguous_table_invalid():
    rows, attempts = capture()
    records = [
        alias(security="SEC:A", valid_from="2026-10-01", valid_to="2026-10-05"),
        alias(security="SEC:B", valid_from="2026-10-02", valid_to="2026-10-06"),
    ]
    result = payload(rows, attempts, identity_aliases=records, source_provenance=ALIAS_PROVENANCE)
    assert result["identity_gate"]["status"] == "ALIAS_TABLE_INVALID"
    assert result["denominators"]["identity_unresolved_records"] == (
        result["denominators"]["capture_clock_bounded_relevant_records"])


def test_identity_gate_query_identity_depends_on_alias_pin():
    rows, attempts = capture()
    first = payload(rows, attempts, identity_aliases=[alias()], source_provenance=ALIAS_PROVENANCE)
    second_prov = deepcopy(ALIAS_PROVENANCE)
    second_prov["inputs"][ALIASES_PATH]["sha256"] = "4" * 64
    second = payload(rows, attempts, identity_aliases=[alias()], source_provenance=second_prov)
    assert first["query_identity"] != second["query_identity"]


def test_cli_fixture_alias_path_absent(tmp_path):
    pd = pytest.importorskip("pandas")
    repository = tmp_path / "fixture"
    repository.mkdir()
    rows, attempts = capture()
    for path, records in ((OBSERVATIONS_PATH, rows), (ATTEMPTS_PATH, attempts)):
        destination = repository / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(records).to_parquet(destination)

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repository), *args], text=True).strip()

    git("init", "-q")
    git("add", "data/revisions")
    git("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "synthetic fixture")
    revision = git("rev-parse", "HEAD")
    script = Path(__file__).resolve().parents[1] / "scripts/query_k3e_expectation_surface.py"
    args = [sys.executable, "-B", str(script), "--repository", str(repository),
            "--source-revision", revision, "--ticker", "V", "--metric", "EPS",
            "--horizon", "+1q", "--as-of", CUT]
    run = subprocess.run(args, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    semantic = json.loads(run.stdout)["semantic_payload"]
    assert semantic["identity_gate"]["status"] == "ALIAS_PATH_ABSENT_AT_REVISION"
    assert semantic["source"]["inputs"][ALIASES_PATH] == dict(absent_at_revision=True)
    assert selected(semantic) is None
    assert semantic["denominators"]["identity_unresolved_records"] == (
        semantic["denominators"]["capture_clock_bounded_relevant_records"])


def test_cli_fixture_missing_alias_blob_refuses(tmp_path):
    pd = pytest.importorskip("pandas")
    repository = tmp_path / "fixture"
    repository.mkdir()
    rows, attempts = capture()
    alias_records = [alias()]
    for path, records in (
        (OBSERVATIONS_PATH, rows),
        (ATTEMPTS_PATH, attempts),
        (ALIASES_PATH, alias_records),
    ):
        destination = repository / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(records).to_parquet(destination)

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repository), *args], text=True).strip()

    git("init", "-q")
    git("add", "data")
    git("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "synthetic fixture")
    revision = git("rev-parse", "HEAD")
    blob = git("rev-parse", f"{revision}:{ALIASES_PATH}")
    loose = repository / ".git" / "objects" / blob[:2] / blob[2:]
    loose.unlink()
    script = Path(__file__).resolve().parents[1] / "scripts/query_k3e_expectation_surface.py"
    args = [sys.executable, "-B", str(script), "--repository", str(repository),
            "--source-revision", revision, "--ticker", "V", "--metric", "EPS",
            "--horizon", "+1q", "--as-of", CUT]
    run = subprocess.run(args, capture_output=True, text=True)
    assert run.returncode == 2
    assert json.loads(run.stderr)["reason"] == "SOURCE_OBJECT_UNAVAILABLE_WITHOUT_FETCH"
