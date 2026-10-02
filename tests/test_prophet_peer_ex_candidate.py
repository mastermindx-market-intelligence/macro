from __future__ import annotations

import copy

import pytest

from engine import prophet_peer_ex_candidate as adapter


def _inputs():
    returns = {
        "AAA": 0.12,
        "AAA.B": 0.99,
        "B": 0.05,
        "C": 0.03,
        "D": -0.02,
    }
    issuers = {
        "AAA": "ISS:A",
        "AAA.B": "ISS:A",
        "B": "ISS:B",
        "C": "ISS:C",
        "D": "ISS:D",
    }
    securities = {
        "AAA": "SEC:XNAS:AAA",
        "AAA.B": "SEC:XNYS:AAAB",
        "B": "SEC:XNAS:B",
        "C": "SEC:XNAS:C",
        "D": "SEC:XNAS:D",
    }
    kwargs = {
        "member_returns": returns,
        "focal_ticker": "AAA",
        "issuer_by_ticker": issuers,
        "security_by_ticker": securities,
        "candidate_issuer_id": "ISS:A",
        "candidate_security_id": "SEC:XNAS:AAA",
        "theme_id": "theme:semis:cpu",
        "asof": "2026-10-01T20:00:00Z",
        "known_at": "2026-10-01T20:01:00Z",
        "membership_vintage": "2026-10-01",
        "return_window_sessions": 10,
        "return_basis": "split_adjusted_close_to_close",
        "source_ref": "gmi:peer:semis-cpu:2026-10-01",
    }
    return kwargs


def test_adapter_projects_owner_exclusion_and_complete_metrics():
    out = adapter.build_peer_ex_candidate(**_inputs())
    assert out == {
        "schema": "prophet.peer_ex_candidate/v1",
        "candidate_issuer_id": "ISS:A",
        "candidate_security_id": "SEC:XNAS:AAA",
        "theme_id": "theme:semis:cpu",
        "asof": "2026-10-01T20:00:00Z",
        "known_at": "2026-10-01T20:01:00Z",
        "membership_vintage": "2026-10-01",
        "return_window_sessions": 10,
        "return_basis": "split_adjusted_close_to_close",
        "candidate_excluded": True,
        "issuer_aliases_excluded": True,
        "peer_member_count": 3,
        "priced_peer_count": 3,
        "coverage": 1.0,
        "equal_weight_return": pytest.approx(0.02),
        "median_return": pytest.approx(0.03),
        "positive_share": pytest.approx(2 / 3),
        "source_ref": "gmi:peer:semis-cpu:2026-10-01",
    }


def test_adapter_keeps_missing_price_in_denominator_without_renormalizing_coverage():
    kwargs = _inputs()
    kwargs["member_returns"]["D"] = None
    out = adapter.build_peer_ex_candidate(**kwargs)
    assert out["peer_member_count"] == 3
    assert out["priced_peer_count"] == 2
    assert out["coverage"] == pytest.approx(2 / 3)
    assert out["equal_weight_return"] == pytest.approx(0.04)
    assert out["median_return"] == pytest.approx(0.04)
    assert out["positive_share"] == 1.0


def test_adapter_singleton_peer_metrics_are_explicitly_unavailable():
    kwargs = _inputs()
    kwargs["member_returns"] = {"AAA": 0.12, "B": 0.05, "C": None}
    kwargs["issuer_by_ticker"] = {
        "AAA": "ISS:A",
        "B": "ISS:B",
        "C": "ISS:C",
    }
    kwargs["security_by_ticker"] = {
        "AAA": "SEC:XNAS:AAA",
        "B": "SEC:XNAS:B",
        "C": "SEC:XNAS:C",
    }
    out = adapter.build_peer_ex_candidate(**kwargs)
    assert out["peer_member_count"] == 2
    assert out["priced_peer_count"] == 1
    assert out["coverage"] == 0.5
    assert out["equal_weight_return"] is None
    assert out["median_return"] is None
    assert out["positive_share"] is None


def test_same_issuer_alias_can_never_enter_peer_numerics():
    kwargs = _inputs()
    kwargs["member_returns"]["AAA.B"] = 10_000.0
    out = adapter.build_peer_ex_candidate(**kwargs)
    assert out["peer_member_count"] == 3
    assert out["equal_weight_return"] == pytest.approx(0.02)
    assert out["median_return"] == pytest.approx(0.03)


def test_unresolved_peer_identity_refuses_alias_exclusion_claim():
    kwargs = _inputs()
    kwargs["issuer_by_ticker"].pop("C")
    with pytest.raises(adapter.PeerExCandidateAdapterError, match="peer_identity_unavailable"):
        adapter.build_peer_ex_candidate(**kwargs)


def test_focal_issuer_must_match_canonical_candidate_identity():
    kwargs = _inputs()
    kwargs["candidate_issuer_id"] = "ISS:OTHER"
    with pytest.raises(adapter.PeerExCandidateAdapterError, match="candidate_issuer_mismatch"):
        adapter.build_peer_ex_candidate(**kwargs)


def test_focal_security_must_match_canonical_candidate_identity():
    kwargs = _inputs()
    kwargs["security_by_ticker"]["AAA"] = "SEC:XNAS:OTHER"
    with pytest.raises(adapter.PeerExCandidateAdapterError, match="candidate_security_mismatch"):
        adapter.build_peer_ex_candidate(**kwargs)


def test_missing_focal_security_binding_is_not_inferred():
    kwargs = _inputs()
    kwargs["security_by_ticker"].pop("AAA")
    with pytest.raises(adapter.PeerExCandidateAdapterError, match="candidate_security_mismatch"):
        adapter.build_peer_ex_candidate(**kwargs)


def test_focal_ticker_must_be_part_of_the_dated_roster():
    kwargs = _inputs()
    kwargs["member_returns"].pop("AAA")
    with pytest.raises(adapter.PeerExCandidateAdapterError, match="focal_ticker_missing"):
        adapter.build_peer_ex_candidate(**kwargs)


@pytest.mark.parametrize("bad", [" AAA", "AAA ", "", 7])
def test_member_ticker_identity_is_not_silently_normalized(bad):
    kwargs = _inputs()
    kwargs["member_returns"][bad] = 0.1
    with pytest.raises(adapter.PeerExCandidateAdapterError, match="member_ticker_invalid"):
        adapter.build_peer_ex_candidate(**kwargs)


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("asof", "2026-10-01", "asof_invalid"),
        ("known_at", "2026-10-01T20:01:00+00:00", "known_at_invalid"),
        ("membership_vintage", "2026-02-30", "membership_vintage_invalid"),
        ("membership_vintage", "2026-10-02", "membership_vintage_after_measurement"),
        ("return_window_sessions", True, "return_window_sessions_invalid"),
        ("return_window_sessions", 0, "return_window_sessions_invalid"),
        ("source_ref", " ", "source_ref_invalid"),
    ],
)
def test_closed_metadata_fails_before_owner_projection(field, value, match):
    kwargs = _inputs()
    kwargs[field] = value
    with pytest.raises(adapter.PeerExCandidateAdapterError, match=match):
        adapter.build_peer_ex_candidate(**kwargs)


def test_measurement_cannot_be_known_before_it_exists():
    kwargs = _inputs()
    kwargs["asof"] = "2026-10-01T20:02:00Z"
    with pytest.raises(adapter.PeerExCandidateAdapterError, match="peer_clock_invalid"):
        adapter.build_peer_ex_candidate(**kwargs)


def test_bool_and_nonfinite_peer_returns_remain_missing_not_zero_or_positive():
    kwargs = _inputs()
    kwargs["member_returns"] = {
        "AAA": 0.12,
        "B": True,
        "C": float("inf"),
        "D": 0.03,
    }
    kwargs["issuer_by_ticker"] = {
        "AAA": "ISS:A",
        "B": "ISS:B",
        "C": "ISS:C",
        "D": "ISS:D",
    }
    kwargs["security_by_ticker"] = {
        "AAA": "SEC:XNAS:AAA",
        "B": "SEC:XNAS:B",
        "C": "SEC:XNAS:C",
        "D": "SEC:XNAS:D",
    }
    out = adapter.build_peer_ex_candidate(**kwargs)
    assert out["peer_member_count"] == 3
    assert out["priced_peer_count"] == 1
    assert out["coverage"] == pytest.approx(1 / 3)
    assert out["equal_weight_return"] is None
    assert out["median_return"] is None
    assert out["positive_share"] is None


def test_adapter_does_not_mutate_owner_inputs_or_emit_financial_authority():
    kwargs = _inputs()
    before = copy.deepcopy(kwargs)
    out = adapter.build_peer_ex_candidate(**kwargs)
    assert kwargs == before
    assert set(out) == {
        "schema",
        "candidate_issuer_id",
        "candidate_security_id",
        "theme_id",
        "asof",
        "known_at",
        "membership_vintage",
        "return_window_sessions",
        "return_basis",
        "candidate_excluded",
        "issuer_aliases_excluded",
        "peer_member_count",
        "priced_peer_count",
        "coverage",
        "equal_weight_return",
        "median_return",
        "positive_share",
        "source_ref",
    }
    assert not any("authority" in key or "rank" in key or "score" in key for key in out)


def test_adapter_fails_closed_if_owner_priced_count_drifts(monkeypatch):
    def impossible_owner(*args, **kwargs):
        return {
            "independence_status": "AVAILABLE",
            "focal_issuer": "ISS:A",
            "peer_denominator": 3,
            "observed_independent_peers": 3,
            "excluded_same_issuer": ["AAA", "AAA.B"],
            "unknown_peer_identity": [],
            "missing_market_observation": ["D"],
            "peer_median": 0.03,
            "n_positive": 2,
        }

    monkeypatch.setattr(adapter, "independent_peer_observation", impossible_owner)
    with pytest.raises(adapter.PeerExCandidateAdapterError, match="priced_count_mismatch"):
        adapter.build_peer_ex_candidate(**_inputs())
