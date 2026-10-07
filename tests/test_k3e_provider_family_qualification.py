"""E1 qualification: provider family, identity alias cutoff, coverage, clocks, rights."""
from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from collectors import equity_revisions as er
from engine.k3e_expectation_surface import (
    ATTEMPTS_PATH,
    OBSERVATIONS_PATH,
    inspect_expectation_surface,
)

BASE_PIN = "13910854fbd652dcdf975301bdc8c6728c2e4767"

ALIAS_KNOWN_AT = "2026-06-01T00:00:00Z"
# A lawful post-alias as_of: on/after ALIAS_KNOWN_AT AND on/after the
# 2026-06-02T10:00:00Z capture it queries
# (DEC:ITP-K3E-BASIS-CHANGE-IS-NONCOMPARABLE-2026-10-07).
POST_ALIAS_AS_OF = "2026-06-02T12:00:00Z"
CUT = "2026-10-02T12:00:00Z"
PROVENANCE = {
    "source_revision": "a" * 40,
    "inputs": {
        OBSERVATIONS_PATH: {"sha256": "1" * 64, "git_blob_id": "1" * 40},
        ATTEMPTS_PATH: {"sha256": "2" * 64, "git_blob_id": "2" * 40},
    },
}


def _attempt(
    label: str,
    *,
    time: str = "2026-10-02T10:00:00Z",
    provider: str = "yfinance",
    ticker: str = "P",
    status: str = "success",
) -> dict:
    return {
        "attempt_id": label,
        "collection_session_id": label,
        "provider": provider,
        "ticker_compat": ticker,
        "attempted_at": time,
        "completed_at": time,
        "status": status,
        "response_payload_hash": label,
        "observation_count": 2,
    }


def _observation(
    label: str,
    *,
    time: str = "2026-10-02T10:00:00Z",
    provider: str = "yfinance",
    ticker: str = "P",
    value: float | None = 2.5,
    count: int = 10,
    security_ref: str | None = None,
    issuer_ref: str | None = None,
    missingness_reason: str | None = None,
    observation_id: str | None = None,
    source_published_at: str | None = None,
    source_effective_at: str | None = None,
    rights_class: str = "UNKNOWN",
    contributor_id: str | None = "contrib-1",
) -> dict:
    oid = observation_id or f"{label}-average"
    miss = missingness_reason
    if value is None and miss is None:
        miss = "UNESTIMABLE"
    return {
        "observation_id": oid,
        "collection_session_id": label,
        "attempt_id": label,
        "provider": provider,
        "provider_record_class": "earnings_estimate",
        "provider_payload_hash": label,
        "ticker_compat": ticker,
        "issuer_ref": issuer_ref,
        "security_ref": security_ref,
        "metric": "EPS",
        "horizon_label_raw": "+1q",
        "period_end": "2026-12-31",
        "fiscal_period": None,
        "fiscal_year": None,
        "observation_type": "average",
        "value": value,
        "unit": "USD/sh",
        "currency": "USD",
        "basis": "GAAP",
        "aggregation_level": "single_contributor",
        "contributor_id": contributor_id,
        "source_effective_at": source_effective_at,
        "source_published_at": source_published_at,
        "provider_observed_at": time,
        "system_observed_at": time,
        "market_session": "2026-10-02",
        "missingness_reason": miss,
        "correction_state": "original",
        "supersedes_observation_id": None,
        "rights_class": rights_class,
        "provenance_note": "qualification-fixture",
    }


def _count_row(label: str, **kwargs) -> dict:
    count = kwargs.pop("count", 10)
    row = _observation(label, **kwargs)
    row["observation_type"] = "covering_analyst_count"
    row["observation_id"] = f"{label}-count"
    row["value"] = count
    row["missingness_reason"] = None
    return row


def _pair(label: str, **kwargs) -> tuple[list[dict], list[dict]]:
    avg = _observation(label, **kwargs)
    cnt = _count_row(label, **{k: v for k, v in kwargs.items() if k != "value"})
    return [avg, cnt], [_attempt(label, time=kwargs.get("time", "2026-10-02T10:00:00Z"),
                                provider=kwargs.get("provider", "yfinance"),
                                ticker=kwargs.get("ticker", "P"))]


def _payload(rows, attempts, **kwargs):
    params = dict(
        source_provenance=PROVENANCE,
        ticker=kwargs.pop("ticker", "P"),
        metric="EPS",
        horizon="+1q",
        as_of=kwargs.pop("as_of", CUT),
        composed_at="2026-10-03T12:00:00Z",
    )
    params.update(kwargs)
    return inspect_expectation_surface(rows, attempts, **params)["semantic_payload"]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP-E-ALIAS: pending Data OS owner-issued as-of identity crosswalk "
        "(DEC:ITP-K3E-BASIS-CHANGE-IS-NONCOMPARABLE-2026-10-07); query uses ticker_compat "
        f"equality only at engine/k3e_expectation_surface.py:206-207 ({BASE_PIN})"
    ),
)
def test_e_a_alias_p_unresolved_before_alias_known_date():
    """E-A before D: pre-alias observation must stay unresolved, not mis-attributed."""
    rows, attempts = _pair(
        "pre-alias",
        time="2026-05-15T10:00:00Z",
        security_ref=None,
        issuer_ref=None,
    )
    result = _payload(rows, attempts, as_of="2026-05-20T12:00:00Z", ticker="P")
    snap = result["last_structurally_supported_snapshot"]["snapshot"]
    assert snap is None
    assert result["normalized_baseline"]["status"] in {"UNAVAILABLE", "UNESTIMABLE"}
    assert result["denominators"]["capture_clock_bounded_relevant_records"] >= 1


def test_e_a_alias_p_resolves_on_or_after_alias_known_date():
    """E-A on/after D: alias-known observations resolve for as_of >= D."""
    rows, attempts = _pair(
        "post-alias",
        time="2026-06-02T10:00:00Z",
        security_ref="SEC:PALO-P",
        issuer_ref="ISS:PALO",
    )
    assert POST_ALIAS_AS_OF >= ALIAS_KNOWN_AT
    result = _payload(rows, attempts, as_of=POST_ALIAS_AS_OF, ticker="P")
    snap = result["last_structurally_supported_snapshot"]["snapshot"]
    assert snap is not None
    assert snap["selected_observation"]["security_ref"] == "SEC:PALO-P"


def test_e_b_provider_family_literal_emitted_by_collector():
    """E-B: pin the provider-family literal the collector emits."""
    assert er._EXPECTATION_PROVIDER == "yfinance"  # collectors/equity_revisions.py:86


def test_e_b_family_mismatch_not_silently_merged():
    """E-B: yahoo-labelled rows do not satisfy a yfinance-scoped consumer query."""
    rows, attempts = _pair("yahoo-row", provider="yahoo")
    result = _payload(rows, attempts, provider="yfinance")
    assert result["denominators"]["capture_clock_bounded_relevant_records"] == 0
    assert result["latest_captured_snapshot"]["status"] == "UNAVAILABLE"
    assert result["query"]["provider"] == "yfinance"


def test_e_b_family_mismatch_surfaces_explicit_refusal():
    """E-B: family mismatch should surface a refusal reason, not only empty population."""
    rows, attempts = _pair("yahoo-row", provider="yahoo")
    result = _payload(rows, attempts, provider="yfinance")
    reasons = result["denominators"]["reason_counts"]
    assert any("FAMILY" in key or "PROVIDER" in key for key in reasons)


def test_e_c_coverage_denominator_includes_unresolved_and_null():
    """E-C: resolved / attempted = 2/4 with one unresolved identity and one null."""
    specs = [
        ("good-a", 2.0, "good-a", None),
        ("good-b", 3.0, "good-b", None),
        ("null-row", None, "null-row", "UNESTIMABLE"),
        ("bad-id", 4.0, "bad-id-average", None),
    ]
    rows = []
    attempts = []
    for label, value, obs_id, miss in specs:
        row = _observation(
            label,
            value=value,
            missingness_reason=miss,
            observation_id=obs_id,
        )
        if label == "bad-id":
            row["provider_payload_hash"] = ""
        attempts.append(_attempt(label))
        rows.append(row)
    result = _payload(rows, attempts, ticker="P")
    d = result["denominators"]
    attempted = d["capture_clock_bounded_relevant_records"]
    resolved = d["valid_captured_records"] - d["true_missing_records"]
    assert attempted == 4
    assert resolved == 2
    assert resolved / attempted == 0.5


def test_e_d_source_publication_after_cutoff_excluded_even_when_system_clock_before():
    """E-D: source clock after cutoff C excludes observation at C (system clock before C)."""
    rows, attempts = _pair(
        "late-source",
        time="2026-10-02T10:00:00Z",
        source_published_at="2026-10-02T13:00:00Z",
        source_effective_at="2026-10-02T13:00:00Z",
    )
    result = _payload(rows, attempts, as_of=CUT)
    assert result["denominators"]["capture_clock_bounded_relevant_records"] == 0


def test_e_d_source_publication_before_cutoff_included_when_capture_clocks_before():
    """E-D mirror: lawful source publication before cutoff remains visible at C."""
    rows, attempts = _pair(
        "timely-source",
        time="2026-10-02T10:00:00Z",
        source_published_at="2026-10-02T09:00:00Z",
        source_effective_at="2026-10-02T09:00:00Z",
    )
    result = _payload(rows, attempts, as_of=CUT)
    assert result["denominators"]["capture_clock_bounded_relevant_records"] == 2
    snap = result["last_structurally_supported_snapshot"]["snapshot"]
    assert snap is not None


def test_e_e_display_only_purpose_refused_for_rank_authority():
    """E-E: display-only purpose rights must refuse rank/authority consumption."""
    rows, attempts = _pair("display-only", rights_class="DISPLAY_ONLY")
    result = _payload(rows, attempts)
    baseline = result["normalized_baseline"]
    assert baseline["value"] is None
    assert baseline["status"] == "RIGHTS_BLOCKED"


def test_e_e_missing_contributor_identity_refused_or_flagged():
    """E-E: observations without contributor identity must be refused or flagged."""
    rows, attempts = _pair("no-contrib", contributor_id=None)
    result = _payload(rows, attempts)
    reasons = result["denominators"]["reason_counts"]
    assert any("CONTRIBUTOR" in key for key in reasons)
    assert result["last_structurally_supported_snapshot"]["snapshot"] is None


def test_provider_mismatch_excludes_value_and_names_family_reason():
    """E2-A: matching economics with a different provider stay ineligible but reasoned."""
    rows, attempts = _pair("yahoo-row", provider="yahoo")
    result = _payload(rows, attempts, provider="yfinance")
    assert result["denominators"]["capture_clock_bounded_relevant_records"] == 0
    # One mismatched attempt row plus both mismatched observation rows.
    assert result["denominators"]["reason_counts"]["PROVIDER_FAMILY_UNRESOLVED"] == 3
    assert result["latest_captured_snapshot"]["snapshot"] is None
    assert result["last_structurally_supported_snapshot"]["snapshot"] is None


def test_observation_only_provider_mismatch_is_counted_and_never_selected():
    """E2-A: mismatched observation rows are reasoned even with no mismatched attempt."""
    rows, attempts = _pair("yf-row")
    other = [_observation("yahoo-row", provider="yahoo", value=9.75),
             _count_row("yahoo-row", provider="yahoo")]
    result = _payload(rows + other, attempts, provider="yfinance")
    assert result["denominators"]["reason_counts"]["PROVIDER_FAMILY_UNRESOLVED"] == 2
    for key in ("latest_captured_snapshot", "last_structurally_supported_snapshot"):
        snap = result[key]["snapshot"]
        assert snap is not None
        assert snap["identity"]["provider"] == "yfinance"
        assert snap["selected_observation"]["value"] == 2.5
    assert "yahoo-row" not in repr(result)
    assert "9.75" not in repr(result)


def test_source_publication_visibility_is_bounded_by_query_cutoff():
    """E2-B: late source publication is invisible; the same pre-cutoff mirror is visible."""
    rows, attempts = _pair(
        "late-source",
        time="2026-10-02T10:00:00Z",
        source_published_at="2026-10-02T13:00:00Z",
        source_effective_at="2026-10-02T13:00:00Z",
    )
    late = _payload(rows, attempts, as_of=CUT)
    assert late["denominators"]["capture_clock_bounded_relevant_records"] == 0
    assert late["denominators"]["reason_counts"]["SOURCE_PUBLISHED_AFTER_CUTOFF"] == 2
    assert late["last_structurally_supported_snapshot"]["snapshot"] is None

    rows, attempts = _pair(
        "timely-source",
        time="2026-10-02T10:00:00Z",
        source_published_at="2026-10-02T09:00:00Z",
        source_effective_at="2026-10-02T09:00:00Z",
    )
    timely = _payload(rows, attempts, as_of=CUT)
    assert timely["denominators"]["capture_clock_bounded_relevant_records"] == 2
    assert timely["last_structurally_supported_snapshot"]["snapshot"] is not None


def test_malformed_source_publication_clock_fails_closed():
    """E2-B: a malformed publication clock cannot become earlier knowledge."""
    rows, attempts = _pair("bad-clock", source_published_at="not-a-clock")
    result = _payload(rows, attempts)
    assert result["denominators"]["reason_counts"]["MALFORMED_SOURCE_PUBLISHED_AT"] == 2
    assert result["latest_captured_snapshot"]["snapshot"] is None
    assert result["last_structurally_supported_snapshot"]["snapshot"] is None


def test_display_only_is_explicitly_refused_as_normalized_baseline():
    """E2-C: display-only raw evidence cannot become rank/normalized authority."""
    rows, attempts = _pair("display-only", rights_class="DISPLAY_ONLY")
    result = _payload(rows, attempts)
    baseline = result["normalized_baseline"]
    assert baseline["value"] is None
    assert baseline["status"] == "RIGHTS_BLOCKED"
    assert baseline["rights_state"] == "RIGHTS_BLOCKED"
    assert "SOURCE_USE_RIGHTS_BLOCKED" in baseline["reasons"]
    assert result["last_structurally_supported_snapshot"]["snapshot"] is not None


def test_missing_contributor_identity_is_refused_and_reasoned():
    """E2-C: estimate identity is required even when a covering count is present."""
    rows, attempts = _pair("no-contrib")
    for row in rows:
        if row["observation_type"] != "covering_analyst_count":
            row["contributor_id"] = None
    result = _payload(rows, attempts)
    assert result["denominators"]["reason_counts"]["CONTRIBUTOR_IDENTITY_UNAVAILABLE"] == 1
    assert result["last_structurally_supported_snapshot"]["snapshot"] is None
    assert result["normalized_baseline"]["value"] is None
    support = result["latest_captured_snapshot"]["snapshot"]["support_reasons"]
    assert "CONTRIBUTOR_IDENTITY_UNAVAILABLE" in support
    assert "INVALID_EXPECTATION_STATE_ENVELOPE" not in support
