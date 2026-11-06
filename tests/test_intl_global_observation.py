"""IM12 contract checks: basis identity, four clocks, return identity, abstains."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from engine.intl_global_observation import (
    ABSTAIN_REASONS,
    CONTRACT_VERSION,
    CURRENCY_BASES,
    LEGACY_MARKET_TO_UNIVERSE_ID,
    ObservationError,
    assert_single_basis,
    build_observation,
    check_clocks,
    decompose,
    fx_return_from_closes,
    observation_id,
    return_identity_residual,
)

CLOCKED = {
    "observation": {"at": "2026-10-07T00:00:00", "precision": "session_date"},
    "source_publication": {"at": "2026-10-09T15:00:00+00:00", "precision": "upper_bound"},
    "ingestion": {"at": "2026-10-09T15:00:00+00:00", "precision": "exact"},
    "computation": {"at": "2026-10-09T20:30:00+00:00", "precision": "exact"},
}
RIGHTS = {"decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
          "scope": "intl-index-fx-eod-user-facing-v1"}
INCUMBENT = {"quality": "qualified", "reason": None,
             "decision_ref": "derived-evaluation:sha256:abc"}
EVIDENCE = "saved-parquet:sha256:one|saved-parquet:sha256:two"


def _identity(**overrides) -> dict:
    identity = {
        "universe_id": "JP", "market_id": "JP", "index_id": "^N225",
        "fx_id": "USDJPY=X", "horizon": "1m", "currency_basis": "usd_unhedged",
        "return_basis": "price", "window_start": "2026-09-08T00:00:00",
        "window_end": "2026-10-07T00:00:00", "source_content_sha256": "a" * 64,
    }
    identity.update(overrides)
    return identity


def _build(**overrides):
    """A fully evidenced usd_unhedged observation; overrides replace kwargs."""
    kwargs = {
        "identity": _identity(),
        "clocks": {name: dict(clock) for name, clock in CLOCKED.items()},
        "values": {"local_pct": 5.0, "usd_pct": -5.5, "fx_pct": -10.0},
        "rights": dict(RIGHTS),
        "incumbent": dict(INCUMBENT),
        "evidence_ref": EVIDENCE,
    }
    kwargs.update(overrides)
    return build_observation(**kwargs)


def test_identity_holds_and_fully_evidenced_usd_observation_qualifies():
    assert return_identity_residual(0.05, -0.10, -0.055) <= 1e-9
    observation = _build()
    assert observation["state"] == "qualified"
    assert observation["abstain_reasons"] == []
    assert observation["value"] == {"pct": -5.5, "unit": "percent"}
    assert observation["contract_version"] == CONTRACT_VERSION
    assert observation["identity_residual"] <= 1e-9
    parts = observation["decomposition"]
    assert parts["local_pct"] == 5.0
    assert parts["fx_pct"] == -10.0
    assert parts["usd_pct"] == -5.5
    assert parts["additive_fx_contribution_pp"] == pytest.approx(-10.5)
    assert parts["interaction_pp"] == pytest.approx(-0.5)
    assert parts["identity_residual"] <= 1e-9


def test_identity_violation_abstains_and_keeps_residual_diagnostic():
    observation = _build(values={"local_pct": 5.0, "usd_pct": -5.0, "fx_pct": -10.0})
    assert observation["state"] == "abstain"
    assert observation["abstain_reasons"] == ["return_identity_violation"]
    assert observation["value"] is None
    assert observation["decomposition"] is None
    assert observation["identity_residual"] == pytest.approx(0.005)


def test_fx_orientation_by_quote_convention():
    assert fx_return_from_closes(1.25, 1.30, "USD_per_local") == pytest.approx(0.04)
    assert fx_return_from_closes(150.0, 160.0, "local_per_USD") == pytest.approx(
        150.0 / 160.0 - 1.0)
    with pytest.raises(ObservationError):
        fx_return_from_closes(1.25, 1.30, "cross_rate")
    with pytest.raises(ObservationError):
        fx_return_from_closes(0.0, 1.30, "USD_per_local")
    with pytest.raises(ObservationError):
        fx_return_from_closes(1.25, float("nan"), "local_per_USD")


@pytest.mark.parametrize("mangle", [
    lambda clocks: clocks.pop("observation"),
    lambda clocks: clocks.update({"source_publication": None}),
    lambda clocks: clocks["ingestion"].update({"at": None}),
    lambda clocks: clocks["computation"].update({"precision": "iso8601"}),
    lambda clocks: clocks["observation"].update({"at": ""}),
])
def test_any_missing_or_imprecise_clock_abstains_clock_missing(mangle):
    clocks = {name: dict(clock) for name, clock in CLOCKED.items()}
    mangle(clocks)
    observation = _build(clocks=clocks)
    assert observation["state"] == "abstain"
    assert "clock_missing" in observation["abstain_reasons"]
    assert observation["value"] is None


def test_clock_ordering_violation_and_session_date_equality():
    reordered = {name: dict(clock) for name, clock in CLOCKED.items()}
    reordered["ingestion"]["at"] = "2026-10-09T14:00:00+00:00"
    observation = _build(clocks=reordered)
    assert "clock_order_violation" in observation["abstain_reasons"]
    assert observation["state"] == "abstain"
    # A session_date observation shares the publication calendar date: not a
    # violation even though the instants differ by fifteen hours.
    same_day = {name: dict(clock) for name, clock in CLOCKED.items()}
    same_day["observation"]["at"] = "2026-10-09T00:00:00"
    assert _build(clocks=same_day)["state"] == "qualified"
    # session_date compares calendar dates ONLY: an observation stamped later
    # the same day than every downstream instant still orders by date.
    later_same_date = {
        "observation": {"at": "2026-10-09T23:30:00", "precision": "session_date"},
        "source_publication": {"at": "2026-10-09T15:00:00+00:00",
                               "precision": "upper_bound"},
        "ingestion": {"at": "2026-10-09T15:00:00+00:00", "precision": "exact"},
        "computation": {"at": "2026-10-09T16:00:00+00:00", "precision": "exact"},
    }
    assert check_clocks(later_same_date) is None
    assert _build(clocks=later_same_date)["state"] == "qualified"


def test_observation_id_binds_identity_only_and_is_deterministic():
    stamped = _build(snapshot_published_at="2026-10-09T20:31:00+00:00")
    unstamped = _build(snapshot_published_at=None)
    assert stamped["observation_id"] == unstamped["observation_id"]
    assert stamped["clocks"] == unstamped["clocks"]
    assert stamped["clocks"] == CLOCKED
    assert observation_id(_identity()) == observation_id(_identity())
    moved = _build(identity=_identity(window_end="2026-10-08T00:00:00"))
    resourced = _build(identity=_identity(source_content_sha256="b" * 64))
    assert moved["observation_id"] != unstamped["observation_id"]
    assert resourced["observation_id"] != unstamped["observation_id"]
    assert unstamped["observation_id"].startswith("obs:sha256:")


def test_unsupported_bases_abstain_without_values():
    hedged = _build(identity=_identity(currency_basis="usd_hedged"))
    assert hedged["state"] == "abstain"
    assert "basis_unsupported" in hedged["abstain_reasons"]
    assert hedged["value"] is None
    assert hedged["decomposition"] is None
    total_return = _build(identity=_identity(return_basis="total_return_gross"))
    assert total_return["state"] == "abstain"
    assert "basis_unsupported" in total_return["abstain_reasons"]
    assert total_return["value"] is None


def test_assert_single_basis_rejects_mixed_bases_only():
    def observation(currency_basis, return_basis="price"):
        return {"identity": {"currency_basis": currency_basis, "return_basis": return_basis}}

    uniform = [observation("usd_unhedged"), observation("usd_unhedged")]
    assert assert_single_basis(uniform) is None
    mixed_currency = [observation("local"), observation("usd_unhedged")]
    with pytest.raises(ObservationError):
        assert_single_basis(mixed_currency)
    mixed_return = [observation("local", "price"), observation("local", "total_return_gross")]
    with pytest.raises(ObservationError):
        assert_single_basis(mixed_return)
    try:
        assert_single_basis(mixed_currency)
    except ObservationError as error:
        assert isinstance(error, ValueError)


def test_rights_incumbent_and_evidence_gates_collect_sorted_reasons():
    unconfirmed = _build(rights=None)
    assert "rights_unconfirmed" in unconfirmed["abstain_reasons"]
    blank = _build(rights={"decision_ref": "", "scope": "intl-index-fx-eod-user-facing-v1"})
    assert "rights_unconfirmed" in blank["abstain_reasons"]
    stale = _build(incumbent={"quality": "stale", "reason": "source_session_missed",
                              "decision_ref": "derived-evaluation:sha256:def"})
    assert "incumbent_qualification_withheld" in stale["abstain_reasons"]
    assert stale["incumbent"]["reason"] == "source_session_missed"
    assert stale["incumbent"]["quality"] == "stale"
    unevidenced = _build(evidence_ref=None)
    assert "source_evidence_missing" in unevidenced["abstain_reasons"]
    everything = _build(rights=None, incumbent=None, evidence_ref="")
    assert everything["state"] == "abstain"
    assert everything["abstain_reasons"] == sorted([
        "rights_unconfirmed", "incumbent_qualification_withheld", "source_evidence_missing"])


def test_vocabularies_are_closed_and_match_the_configured_universe():
    with pytest.raises(ObservationError):
        _build(identity=_identity(currency_basis="euro"))
    with pytest.raises(ObservationError):
        _build(identity=_identity(return_basis="dividend"))
    with pytest.raises(ObservationError):
        _build(identity=_identity(market_id="US"))
    with pytest.raises(ObservationError):
        _build(identity=_identity(universe_id="XX"))
    short = _identity()
    del short["source_content_sha256"]
    with pytest.raises(ObservationError):
        _build(identity=short)
    with pytest.raises(ObservationError):
        _build(identity=_identity(extra_field="unexpected"))
    config = yaml.safe_load((Path(__file__).resolve().parents[1] / "config.yml").read_text())
    assert set(LEGACY_MARKET_TO_UNIVERSE_ID) == set(config["intl"]["countries"])
    assert "usd_hedged" in CURRENCY_BASES
    assert ABSTAIN_REASONS == frozenset({
        "clock_missing", "clock_order_violation", "value_unavailable",
        "return_identity_violation", "identity_mismatch", "basis_unsupported",
        "rights_unconfirmed", "incumbent_qualification_withheld",
        "source_evidence_missing"})


def test_local_basis_uses_local_value_and_checks_identity_when_fully_supplied():
    local = _build(identity=_identity(currency_basis="local"))
    assert local["state"] == "qualified"
    assert local["value"] == {"pct": 5.0, "unit": "percent"}
    broken = _build(identity=_identity(currency_basis="local"),
                    values={"local_pct": 5.0, "usd_pct": -5.0, "fx_pct": -10.0})
    assert broken["state"] == "abstain"
    assert "return_identity_violation" in broken["abstain_reasons"]
    partial = _build(identity=_identity(currency_basis="local"),
                     values={"local_pct": 5.0, "usd_pct": None, "fx_pct": None})
    assert partial["state"] == "qualified"
    assert partial["value"] == {"pct": 5.0, "unit": "percent"}
    assert partial["decomposition"] is None
    unavailable = _build(identity=_identity(currency_basis="local"),
                         values={"local_pct": None, "usd_pct": None, "fx_pct": None})
    assert "value_unavailable" in unavailable["abstain_reasons"]
    assert unavailable["value"] is None


def test_usd_basis_requires_the_decomposition_legs():
    missing_fx = _build(values={"local_pct": 5.0, "usd_pct": -5.5, "fx_pct": None})
    assert "value_unavailable" in missing_fx["abstain_reasons"]
    assert missing_fx["value"] is None
    missing_usd = _build(values={"local_pct": 5.0, "usd_pct": None, "fx_pct": -10.0})
    assert "value_unavailable" in missing_usd["abstain_reasons"]
    nonfinite = _build(values={"local_pct": 5.0, "usd_pct": float("inf"), "fx_pct": -10.0})
    assert "value_unavailable" in nonfinite["abstain_reasons"]


def test_extra_reasons_must_be_closed_vocabulary():
    with pytest.raises(ObservationError):
        _build(extra_reasons=("invented_reason",))
    mismatched = _build(extra_reasons=("identity_mismatch",))
    assert mismatched["state"] == "abstain"
    assert "identity_mismatch" in mismatched["abstain_reasons"]


def test_decompose_reports_percentage_point_parts():
    parts = decompose(5.0, -5.5, -10.0)
    assert parts["additive_fx_contribution_pp"] == pytest.approx(-10.5)
    assert parts["interaction_pp"] == pytest.approx(-0.5)
    assert parts["identity_residual"] == pytest.approx(
        return_identity_residual(0.05, -0.10, -0.055))
