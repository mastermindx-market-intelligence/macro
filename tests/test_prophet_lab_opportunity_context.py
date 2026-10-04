from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json

import pytest

from engine.prophet_candidate_state import project_candidate_states
from engine.prophet_entry_availability import evaluate_entry_availability
from engine.prophet_lab.contracts import ALL_FALSE_AUTHORITY
from engine.prophet_lab.opportunity_context import (
    OpportunityContextContractError,
    compose_opportunity_context,
    project_terminal_portfolio_relation,
    resolve_display_alias_to_active_episode,
    select_unique_active_episode_id,
    validate_opportunity_context,
    validate_opportunity_identity_binding,
    validate_terminal_portfolio_relation,
)
from engine.prophet_strategy_definition import (
    build_early_leadership_sector_rotation_definition,
)
from lib.dataos.identity import VendorAliasTable


GEN = "peg:" + "a" * 64


def eid(label="1"):
    digest = label.encode("utf-8").hex().ljust(24, "0")[:24]
    return f"pe:SEC:US-XNAS-AAPL:epoch_0:sa:{digest}:1"


@dataclass(frozen=True)
class Gen:
    episodes: tuple


@dataclass(frozen=True)
class Snap:
    generation_id: str
    generation: Gen


def episode(state="ACTIVE", terminal_reason=None):
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": eid(),
        "security_id": "SEC:US-XNAS-AAPL",
        "company_id": "ISS:US-XNAS-AAPL",
        "identity_epoch": "epoch_0",
        "episode_state": state,
        "terminal_reason": terminal_reason,
        "superseded_by": None,
        "opened_at": "2026-09-17T20:00:00Z",
        "opened_session": "2026-09-17",
        "correction_state": "current",
    }


def projection(*, generated_at="2026-09-18T19:30:00Z", state="ACTIVE"):
    return project_candidate_states(
        Snap(GEN, Gen((episode(state, "expired" if state == "EXPIRED" else None),))),
        market_session="2026-09-18",
        generated_at=generated_at,
        emergence_by_episode={
            eid(): {
                "state": "TRIGGERED",
                "reason": None,
                "source_system": "turn_watch",
                "source_token": "B1_OBSERVED",
                "source_ref": "pee:" + "b" * 64,
            }
        },
    )


def facts():
    return {
        "decision_at": "2026-09-18T19:30:08Z",
        "market_session": "2026-09-18",
        "quote": {
            "price": 42.70,
            "asof": "2026-09-18T19:30:00Z",
            "freshness": "FRESH",
            "basis_version": "adjusted:v7",
            "source_receipt": "sha256:" + "1" * 64,
        },
        "geometry": {
            "owner_status": "buy_now",
            "zone_low": 41.80,
            "zone_high": 43.25,
            "chase_above": 43.60,
            "invalidation_price": 40.95,
            "basis_version": "adjusted:v7",
            "source_receipt": "sha256:" + "2" * 64,
        },
        "deterministic_gates": {
            "owner_confluence": "PASS",
            "risk_ceiling": "PASS",
            "liquidity_fillability": "PASS",
            "gap_velocity": "PASS",
            "source_health": "PASS",
            "corporate_action_basis": "RESOLVED",
            "session_eligibility": "PASS",
            "event_status": "ACTIVE",
            "structural_invalidation": "CLEAR",
        },
        "metric_inputs": {
            "first_trigger_price": 41.72,
            "anchor_price": 42.10,
            "atr": 1.15,
        },
        "source_receipts": ["b3:source-owner-v1"],
    }


def availability(p=None):
    p = p or projection()
    return evaluate_entry_availability(
        p,
        episode_id=eid(),
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        facts=facts(),
    )


def test_missing_b4_stays_unknown_and_mints_no_permission():
    out = compose_opportunity_context(projection(), episode_id=eid())
    assert out["fresh_entry"]["state"] == "UNAVAILABLE_DATA"
    assert out["fresh_entry"]["entry_open"] is None
    assert out["fresh_entry"]["availability_id"] is None
    assert out["fresh_entry"]["blockers"] == ["B4_NOT_AVAILABLE"]
    assert out["user_state"]["plan"]["state"] == "NOT_JOINED"
    assert out["user_state"]["watchlist"]["state"] == "NOT_JOINED"
    assert out["user_state"]["portfolio"]["state"] == "NOT_JOINED"
    assert out["forecast"]["qualified"] is False
    assert out["forecast"]["heads"] is None
    assert out["authority"] == ALL_FALSE_AUTHORITY
    validate_opportunity_context(out)


def test_owner_issued_b4_is_projected_without_recomputing_it():
    p = projection()
    b4 = availability(p)
    out = compose_opportunity_context(p, episode_id=eid(), entry_availability=b4)
    assert out["fresh_entry"]["state"] == "ENTRY_OPEN"
    assert out["fresh_entry"]["entry_open"] is True
    assert out["fresh_entry"]["availability_id"] == b4["availability_id"]
    assert out["fresh_entry"]["strategy"]["strategy_definition_id"] == b4["strategy_definition_id"]
    assert out["fresh_entry"]["current_price"] == {
        "value": 42.7,
        "basis": "adjusted:v7",
        "asof": "2026-09-18T19:30:00Z",
        "age_seconds": 8,
    }
    assert out["fresh_entry"]["zone"] == b4["zone"]
    assert out["fresh_entry"]["source_receipts"] == b4["source_receipts"]


def test_b4_from_another_candidate_projection_is_refused():
    old = projection(generated_at="2026-09-18T19:29:00Z")
    b4 = availability(old)
    with pytest.raises(
        OpportunityContextContractError,
        match="candidate_state_projection_id",
    ):
        compose_opportunity_context(
            projection(),
            episode_id=eid(),
            entry_availability=b4,
        )


def test_terminal_episode_does_not_infer_a_fresh_entry_verdict():
    out = compose_opportunity_context(
        projection(state="EXPIRED"),
        episode_id=eid(),
    )
    assert out["native_phase"]["episode_lifecycle"]["state"] == "CLOSED"
    assert out["fresh_entry"]["state"] == "UNAVAILABLE_DATA"
    assert out["fresh_entry"]["entry_open"] is None


def test_unknown_episode_is_refused_not_joined_by_ticker():
    with pytest.raises(
        OpportunityContextContractError,
        match="exactly one canonical B3 row",
    ):
        compose_opportunity_context(projection(), episode_id=eid("other"))


def test_context_does_not_accept_or_infer_private_plan_or_forecast_state():
    p = projection()
    out = compose_opportunity_context(
        p,
        episode_id=eid(),
        entry_availability=availability(p),
    )
    assert out["user_state"] == {
        "plan": {
            "state": "NOT_JOINED",
            "plan_ref": None,
            "reason": "PRIVATE_PLAN_OWNER_NOT_READ",
        },
        "watchlist": {
            "state": "NOT_JOINED",
            "saved": None,
            "reason": "WATCHLIST_READ_CONTRACT_NOT_ADMITTED",
        },
        "portfolio": {
            "state": "NOT_JOINED",
            "relation": None,
            "reason": "PORTFOLIO_OWNER_NOT_READ",
        },
    }
    assert out["evidence_summary"]["support"] is None
    assert out["evidence_summary"]["contradiction"] is None
    assert out["evidence_summary"]["next_observable"] is None
    assert out["forecast"] == {
        "qualified": False,
        "heads": None,
        "reason": "NO_QUALIFIED_OLI_FORECAST",
    }


def test_closed_contract_rejects_authority_or_user_state_laundering():
    out = compose_opportunity_context(projection(), episode_id=eid())
    bad = deepcopy(out)
    bad["authority"]["ranking"] = True
    with pytest.raises(OpportunityContextContractError, match="authority"):
        validate_opportunity_context(bad)

    bad = deepcopy(out)
    bad["user_state"]["plan"]["state"] = "entered"
    with pytest.raises(OpportunityContextContractError, match="private Plan state"):
        validate_opportunity_context(bad)


def test_missing_b4_cannot_be_relabelled_as_false_entry_permission():
    out = compose_opportunity_context(projection(), episode_id=eid())
    bad = deepcopy(out)
    bad["fresh_entry"]["entry_open"] = False
    with pytest.raises(
        OpportunityContextContractError,
        match="unknown rather than a false verdict",
    ):
        validate_opportunity_context(bad)


def _rehash_projection(payload):
    material = {key: value for key, value in payload.items() if key != "projection_id"}
    encoded = json.dumps(
        material, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    payload["projection_id"] = "pcs:" + sha256(encoded).hexdigest()


def test_security_resolution_returns_the_one_active_canonical_episode():
    p = projection()
    assert select_unique_active_episode_id(
        p, security_id="SEC:US-XNAS-AAPL"
    ) == eid()


def test_security_resolution_refuses_zero_active_episode_instead_of_ticker_fallback():
    with pytest.raises(
        OpportunityContextContractError,
        match="no ACTIVE B3 episode",
    ):
        select_unique_active_episode_id(
            projection(), security_id="SEC:US-XNAS-MSFT"
        )


def test_security_resolution_refuses_multiple_active_episodes():
    p = projection()
    second = deepcopy(p["rows"][0])
    second["episode_id"] = eid("2")
    p["rows"].append(second)
    p["rows"].sort(key=lambda row: row["episode_id"])
    p["row_count"] = 2
    _rehash_projection(p)
    with pytest.raises(
        OpportunityContextContractError,
        match="multiple ACTIVE B3 episodes",
    ):
        select_unique_active_episode_id(
            p, security_id="SEC:US-XNAS-AAPL"
        )


def test_security_resolution_ignores_closed_rows_but_never_infers_from_them():
    p = projection(state="EXPIRED")
    with pytest.raises(
        OpportunityContextContractError,
        match="no ACTIVE B3 episode",
    ):
        select_unique_active_episode_id(
            p, security_id="SEC:US-XNAS-AAPL"
        )



def _identity_aliases():
    return VendorAliasTable.from_records([
        {
            "vendor": "store",
            "vendor_symbol": "AAPL",
            "security_id": "SEC:US-XNAS-AAPL",
            "valid_from": None,
            "valid_to": None,
        },
    ])


def _identity_receipts():
    return (
        {
            "source": "identity",
            "path": "data/reference/vendor_aliases.parquet",
            "sha256": "sha256:" + "a" * 64,
        },
        {
            "source": "identity",
            "path": "data/reference/security_master.parquet",
            "sha256": "sha256:" + "b" * 64,
        },
    )


def test_display_alias_resolves_through_data_os_and_reverse_proves_identity():
    p = projection()
    binding = resolve_display_alias_to_active_episode(
        p,
        aliases=_identity_aliases(),
        identity_source_receipts=_identity_receipts(),
        display_symbol=" aapl ",
        decision_date=date(2026, 9, 18),
    )
    assert binding["display_symbol"] == "AAPL"
    assert binding["security_id"] == "SEC:US-XNAS-AAPL"
    assert binding["episode_id"] == eid()
    assert binding["identity_epoch"] == "epoch_0"
    assert binding["candidate_generation_id"] == p["candidate_generation_id"]
    assert binding["candidate_state_projection_id"] == p["projection_id"]
    assert binding["authority"] == ALL_FALSE_AUTHORITY
    assert len(binding["identity_source_receipts"]) == 2
    validate_opportunity_identity_binding(binding)


def test_display_alias_refuses_unmapped_symbol_instead_of_ticker_identity():
    with pytest.raises(
        OpportunityContextContractError,
        match="unmapped in the Data OS store alias space",
    ):
        resolve_display_alias_to_active_episode(
            projection(),
            aliases=_identity_aliases(),
            identity_source_receipts=_identity_receipts(),
            display_symbol="MSFT",
            decision_date=date(2026, 9, 18),
        )


def test_display_alias_requires_canonical_identity_receipts():
    with pytest.raises(
        OpportunityContextContractError,
        match="identity source receipts are required",
    ):
        resolve_display_alias_to_active_episode(
            projection(),
            aliases=_identity_aliases(),
            identity_source_receipts=(),
            display_symbol="AAPL",
            decision_date=date(2026, 9, 18),
        )


def test_display_alias_refuses_historical_vendor_space_as_current_identity():
    aliases = VendorAliasTable.from_records([
        {
            "vendor": "yahoo_historical",
            "vendor_symbol": "AAPL",
            "security_id": "SEC:US-XNAS-AAPL",
            "valid_from": None,
            "valid_to": None,
        },
    ])
    with pytest.raises(
        OpportunityContextContractError,
        match="unmapped in the Data OS store alias space",
    ):
        resolve_display_alias_to_active_episode(
            projection(),
            aliases=aliases,
            identity_source_receipts=_identity_receipts(),
            display_symbol="AAPL",
            decision_date=date(2026, 9, 18),
        )


def test_display_alias_refuses_non_date_clock():
    with pytest.raises(
        OpportunityContextContractError,
        match="decision_date must be a calendar date",
    ):
        resolve_display_alias_to_active_episode(
            projection(),
            aliases=_identity_aliases(),
            identity_source_receipts=_identity_receipts(),
            display_symbol="AAPL",
            decision_date="2026-09-18",
        )



def _identity_binding():
    return resolve_display_alias_to_active_episode(
        projection(),
        aliases=_identity_aliases(),
        identity_source_receipts=_identity_receipts(),
        display_symbol="AAPL",
        decision_date=date(2026, 9, 18),
    )


def test_terminal_portfolio_relation_projects_only_current_open_owner_rows():
    relation = project_terminal_portfolio_relation(
        _identity_binding(),
        http_status=200,
        payload={
            "positions": [
                {"id": "p-open", "ticker": "AAPL", "status": "open", "notes": "private"},
                {"id": "p-closed", "ticker": "AAPL", "status": "closed"},
                {"id": "p-other", "ticker": "MSFT", "status": "open"},
            ],
            "risk": {"ignored": True},
        },
    )
    assert relation["state"] == "OPEN_POSITION"
    assert relation["join_basis"] == "CURRENT_STORE_ALIAS"
    assert relation["open_position_count"] == 1
    assert relation["position_refs"] == [{"position_id": "p-open"}]
    assert "notes" not in str(relation)
    assert "risk" not in relation
    assert relation["authority"] == ALL_FALSE_AUTHORITY
    validate_terminal_portfolio_relation(relation)


def test_terminal_portfolio_relation_preserves_multiple_open_lots():
    relation = project_terminal_portfolio_relation(
        _identity_binding(),
        http_status=200,
        payload={"positions": [
            {"id": "p-1", "ticker": "AAPL", "status": "open"},
            {"id": "p-2", "ticker": "AAPL", "status": "open"},
        ]},
    )
    assert relation["state"] == "OPEN_POSITION"
    assert relation["open_position_count"] == 2
    assert relation["position_refs"] == [
        {"position_id": "p-1"},
        {"position_id": "p-2"},
    ]


def test_terminal_portfolio_relation_200_empty_is_authoritative_no_open_position():
    relation = project_terminal_portfolio_relation(
        _identity_binding(),
        http_status=200,
        payload={"positions": [], "risk": None},
    )
    assert relation["state"] == "NO_OPEN_POSITION"
    assert relation["open_position_count"] == 0
    assert relation["position_refs"] == []
    assert relation["reason"] is None


def test_terminal_portfolio_relation_never_turns_owner_failure_into_zero():
    unavailable = project_terminal_portfolio_relation(
        _identity_binding(),
        http_status=503,
        payload={"error": "portfolio unavailable"},
    )
    assert unavailable["state"] == "UNAVAILABLE_DATA"
    assert unavailable["open_position_count"] is None
    assert unavailable["position_refs"] == []
    assert unavailable["reason"] == "PORTFOLIO_OWNER_HTTP_503"

    auth = project_terminal_portfolio_relation(
        _identity_binding(),
        http_status=401,
        payload={"error": "unauthenticated"},
    )
    assert auth["state"] == "AUTHENTICATION_REQUIRED"
    assert auth["open_position_count"] is None
    assert auth["reason"] == "PORTFOLIO_AUTHENTICATION_REQUIRED"


def test_terminal_portfolio_relation_refuses_malformed_owner_rows():
    with pytest.raises(
        OpportunityContextContractError,
        match="ticker is not normalized",
    ):
        project_terminal_portfolio_relation(
            _identity_binding(),
            http_status=200,
            payload={"positions": [{"id": "p-1", "ticker": "aapl", "status": "open"}]},
        )

    with pytest.raises(
        OpportunityContextContractError,
        match="duplicate position id",
    ):
        project_terminal_portfolio_relation(
            _identity_binding(),
            http_status=200,
            payload={"positions": [
                {"id": "p-1", "ticker": "AAPL", "status": "open"},
                {"id": "p-1", "ticker": "AAPL", "status": "closed"},
            ]},
        )


def test_context_joins_portfolio_without_laundering_plan_or_watchlist_state():
    p = projection()
    binding = resolve_display_alias_to_active_episode(
        p,
        aliases=_identity_aliases(),
        identity_source_receipts=_identity_receipts(),
        display_symbol="AAPL",
        decision_date=date(2026, 9, 18),
    )
    relation = project_terminal_portfolio_relation(
        binding,
        http_status=200,
        payload={"positions": [{"id": "p-1", "ticker": "AAPL", "status": "open"}]},
    )
    out = compose_opportunity_context(
        p,
        episode_id=eid(),
        portfolio_relation=relation,
    )
    assert out["user_state"]["portfolio"]["state"] == "JOINED"
    assert out["user_state"]["portfolio"]["relation"]["state"] == "OPEN_POSITION"
    assert out["user_state"]["plan"]["state"] == "NOT_JOINED"
    assert out["user_state"]["watchlist"] == {
        "state": "NOT_JOINED",
        "saved": None,
        "reason": "WATCHLIST_READ_CONTRACT_NOT_ADMITTED",
    }


def test_context_refuses_portfolio_relation_from_another_episode_identity():
    p = projection()
    binding = _identity_binding()
    relation = project_terminal_portfolio_relation(
        binding,
        http_status=200,
        payload={"positions": []},
    )
    relation["episode_id"] = eid("other")
    with pytest.raises(
        OpportunityContextContractError,
        match="portfolio relation episode_id does not match",
    ):
        compose_opportunity_context(
            p,
            episode_id=eid(),
            portfolio_relation=relation,
        )


def test_user_state_watchlist_negative_cannot_be_invented():
    out = compose_opportunity_context(projection(), episode_id=eid())
    bad = deepcopy(out)
    bad["user_state"]["watchlist"] = {
        "state": "JOINED",
        "saved": False,
        "reason": None,
    }
    with pytest.raises(
        OpportunityContextContractError,
        match="watchlist state must remain unjoined",
    ):
        validate_opportunity_context(bad)
