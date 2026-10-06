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
        "GAP-E-ALIAS: no ticker-P alias-as-of cutoff resolver; query uses ticker_compat "
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP-E-ALIAS: no ticker-P alias-as-of cutoff resolver; query uses ticker_compat "
        f"equality only at engine/k3e_expectation_surface.py:206-207 ({BASE_PIN})"
    ),
)
def test_e_a_alias_p_resolves_on_or_after_alias_known_date():
    """E-A on/after D: alias-known observations resolve for as_of >= D."""
    rows, attempts = _pair(
        "post-alias",
        time="2026-06-02T10:00:00Z",
        security_ref="SEC:PALO-P",
        issuer_ref="ISS:PALO",
    )
    result = _payload(rows, attempts, as_of=ALIAS_KNOWN_AT, ticker="P")
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP-E-FAMILY-SEAM: no explicit yfinance↔yahoo family seam refusal; rows are "
        f"silently filtered at engine/k3e_expectation_surface.py:206-207 ({BASE_PIN})"
    ),
)
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP-E-CLOCK: inclusion boundary uses provider_observed_at/system_observed_at only "
        f"at engine/k3e_expectation_surface.py:215-218 ({BASE_PIN}), not source publication"
    ),
)
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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP-E-RIGHTS: no rank-purpose rights field on observation seam; only rights_class "
        f"labels at engine/k3e_expectation_surface.py:365-371 ({BASE_PIN})"
    ),
)
def test_e_e_display_only_purpose_refused_for_rank_authority():
    """E-E: display-only purpose rights must refuse rank/authority consumption."""
    rows, attempts = _pair("display-only", rights_class="DISPLAY_ONLY")
    result = _payload(rows, attempts)
    baseline = result["normalized_baseline"]
    assert baseline["value"] is None
    assert baseline["status"] == "RIGHTS_BLOCKED"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "GAP-E-RIGHTS: contributor_id present on schema but not enforced at "
        f"engine/k3e_expectation_surface.py:205-252 ({BASE_PIN})"
    ),
)
def test_e_e_missing_contributor_identity_refused_or_flagged():
    """E-E: observations without contributor identity must be refused or flagged."""
    rows, attempts = _pair("no-contrib", contributor_id=None)
    result = _payload(rows, attempts)
    reasons = result["denominators"]["reason_counts"]
    assert any("CONTRIBUTOR" in key for key in reasons)
    assert result["last_structurally_supported_snapshot"]["snapshot"] is None
