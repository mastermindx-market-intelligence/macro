from __future__ import annotations

from copy import deepcopy

import pytest

from engine.prophet_cycle_equity import (
    CycleEquityError,
    build_cycle_equity_case,
    build_funding_path,
    inventory_sales_diagnostic,
    recovery_scenario,
)


ISSUER = "issuer:0000099999"
SECURITY = "SEC:US-XNAS-FIX"
DECISION = "2026-10-01T20:00:00Z"
RECOVERY = "2027-06-30T20:00:00Z"


def capital_need(*, cash=100.0, debt=400.0, status="complete", ladder_complete=True, reasons=None):
    return {
        "schema": "capital_need.v1",
        "version": 1,
        "status": status,
        "issuer": {
            "issuer_id": ISSUER,
            "security_id": SECURITY,
            "cik": "0000099999",
            "scope": "issuer",
        },
        "as_of": "2026-10-01",
        "coverage": {"state": status, "reasons": list(reasons or [])},
        "reported": {
            "debt_due": {
                "state": "observed",
                "unit": "USD",
                "currency": "USD",
                "issuer_debt_outstanding_only": True,
                "total_reported_usd": debt,
                "ladder_complete": ladder_complete,
                "buckets": [],
            },
            "cash": {
                "state": "observed",
                "value": cash,
                "unit": "USD",
                "currency": "USD",
                "basis": "instant",
            },
            "operating_cash_flow": None,
            "capex": None,
        },
        "derived": {
            "free_cash_flow": None,
            "scenario_runway": None,
            "near_term_cash_cover": None,
            "near_term_cash_gap_usd": None,
        },
        "authority": {"class": "context_only", "display_only": True},
        "source_clock": {
            "evaluation_as_of": "2026-10-01",
            "debt_evaluation_as_of": "2026-10-01",
            "cash_evaluation_as_of": "2026-10-01",
        },
    }


def share_count(*, shares=100.0, available="2026-10-01T18:00:00Z"):
    return {
        "schema": "capital_structure.share_count_observation.v1",
        "observation_id": "share-count:fixture",
        "issuer_id": ISSUER,
        "metric": {"kind": "common_shares_outstanding", "scope": "direct_sec_companyfacts_fact"},
        "state": {"disposition": "observed", "reason": "direct_sec_companyfacts_fact"},
        "normalized": {"value": str(shares), "unit": "shares", "scale": "1", "state": "observed"},
        "point_in_time": {
            "available_at": available,
            "system_available_at": available,
            "source_retrieved_at": available,
        },
        "authority": {
            "is_context_only": True,
            "rank_authority": False,
            "sizing_authority": False,
            "entry_authority": False,
            "trade_authority": False,
            "prophet_authority": False,
        },
    }


def event(kind, event_id, when, **kwargs):
    return {
        "event_id": event_id,
        "kind": kind,
        "status": kwargs.pop("status", "scenario_assumption"),
        "available_at": kwargs.pop("available_at", DECISION),
        "effective_at": when,
        "source_ref": kwargs.pop("source_ref", f"scenario:{event_id}"),
        **kwargs,
    }


def full_kwargs(**overrides):
    base = {
        "capital_need": capital_need(),
        "share_count_observation": share_count(),
        "issuer_id": ISSUER,
        "security_id": SECURITY,
        "decision_at": DECISION,
        "recovery_at": RECOVERY,
        "funding_events": [],
        "original_cohort_shares": 100.0,
        "minimum_operating_cash": 20.0,
        "restricted_cash": {
            "state": "not_applicable",
            "amount": 0.0,
            "included_in_reported_cash": False,
            "source_ref": "issuer:cash-note",
            "available_at": DECISION,
        },
        "schedule_complete_through": RECOVERY,
    }
    base.update(overrides)
    return base


class TestFundingPath:
    def test_plain_complete_path_is_funded(self):
        out = build_funding_path(**full_kwargs())
        assert out["path_state"] == "FUNDED_TO_RECOVERY"
        assert out["starting"]["accessible_cash"] == 100
        assert out["ending"]["accessible_cash"] == 100
        assert out["ending"]["reported_debt_model"] == 400
        assert out["ending"]["common_shares"] == 100
        assert not out["limitations"]
        assert all(out[key] is False for key in (
            "rank_authority", "entry_authority", "sizing_authority", "trade_authority", "policy_authority"
        ))

    def test_maturity_before_recovery_breaches_cash_floor(self):
        out = build_funding_path(**full_kwargs(funding_events=[
            event("debt_repayment", "maturity", "2026-12-01T00:00:00Z", principal=90.0),
        ]))
        assert out["path_state"] == "BREACHED_BEFORE_RECOVERY"
        assert out["breaches"][0]["event_id"] == "maturity"
        assert out["breaches"][0]["shortfall_to_operating_cash_floor"] == pytest.approx(10)

    def test_later_raise_does_not_erase_earlier_breach(self):
        out = build_funding_path(**full_kwargs(funding_events=[
            event("cash_obligation", "payment", "2026-11-01T00:00:00Z", amount=120.0),
            event(
                "equity_raise", "later_raise", "2027-01-01T00:00:00Z",
                gross_proceeds=100.0, fees=0.0, issue_price=1.0, shares_issued=100.0,
            ),
        ]))
        assert out["path_state"] == "BREACHED_BEFORE_RECOVERY"
        assert out["ending"]["accessible_cash"] == pytest.approx(80)
        assert out["breaches"][0]["event_id"] == "payment"

    def test_equity_raise_adds_cash_and_shares(self):
        out = build_funding_path(**full_kwargs(funding_events=[
            event(
                "equity_raise", "raise", "2026-12-01T00:00:00Z",
                gross_proceeds=200.0, fees=10.0, issue_price=1.0, shares_issued=200.0,
            ),
        ]))
        assert out["ending"]["accessible_cash"] == 290
        assert out["ending"]["common_shares"] == 300

    def test_equity_raise_requires_price_share_reconciliation(self):
        with pytest.raises(CycleEquityError, match="terms_do_not_reconcile"):
            build_funding_path(**full_kwargs(funding_events=[
                event(
                    "equity_raise", "raise", "2026-12-01T00:00:00Z",
                    gross_proceeds=200.0, fees=0.0, issue_price=2.0, shares_issued=200.0,
                ),
            ]))

    def test_original_cohort_subscription_tracks_new_money(self):
        out = build_funding_path(**full_kwargs(funding_events=[
            event(
                "equity_raise", "rights", "2026-12-01T00:00:00Z",
                gross_proceeds=200.0, fees=0.0, issue_price=1.0, shares_issued=200.0,
                original_cohort_subscribed_shares=100.0,
                original_cohort_cash_contribution=100.0,
            ),
        ]))
        assert out["ending"]["original_cohort_shares"] == 200
        assert out["ending"]["original_cohort_additional_contributions"] == 100

    def test_free_participation_is_refused(self):
        with pytest.raises(CycleEquityError, match="subscription_cash_mismatch"):
            build_funding_path(**full_kwargs(funding_events=[
                event(
                    "equity_raise", "rights", "2026-12-01T00:00:00Z",
                    gross_proceeds=200.0, fees=0.0, issue_price=1.0, shares_issued=200.0,
                    original_cohort_subscribed_shares=100.0,
                    original_cohort_cash_contribution=0.0,
                ),
            ]))

    def test_debt_draw_adds_equal_principal_claim_and_cash_before_fees(self):
        out = build_funding_path(**full_kwargs(funding_events=[
            event("debt_draw", "draw", "2026-12-01T00:00:00Z", principal=100.0, fees=5.0),
        ]))
        assert out["ending"]["accessible_cash"] == 195
        assert out["ending"]["reported_debt_model"] == 500

    def test_debt_conversion_adds_shares_but_no_cash(self):
        out = build_funding_path(**full_kwargs(funding_events=[
            event(
                "debt_conversion", "convert", "2026-12-01T00:00:00Z",
                principal=100.0, shares_issued=50.0, conversion_price=2.0,
            ),
        ]))
        assert out["ending"]["accessible_cash"] == 100
        assert out["ending"]["reported_debt_model"] == 300
        assert out["ending"]["common_shares"] == 150

    def test_restricted_cash_inside_reported_cash_is_not_initially_spendable(self):
        out = build_funding_path(**full_kwargs(restricted_cash={
            "state": "observed",
            "amount": 40.0,
            "included_in_reported_cash": True,
            "source_ref": "issuer:restricted",
            "available_at": DECISION,
        }))
        assert out["starting"]["accessible_cash"] == 60
        assert out["ending"]["restricted_cash"] == 40

    def test_restricted_cash_release_becomes_spendable_only_at_release(self):
        out = build_funding_path(**full_kwargs(
            restricted_cash={
                "state": "observed", "amount": 40.0, "included_in_reported_cash": True,
                "source_ref": "issuer:restricted", "available_at": DECISION,
            },
            funding_events=[
                event("restricted_cash_release", "release", "2027-01-01T00:00:00Z", amount=30.0),
            ],
        ))
        assert out["starting"]["accessible_cash"] == 60
        assert out["ending"]["accessible_cash"] == 90
        assert out["ending"]["restricted_cash"] == 10

    def test_unknown_restricted_cash_withholds_funded_claim(self):
        out = build_funding_path(**full_kwargs(restricted_cash={"state": "unknown", "amount": None}))
        assert out["path_state"] == "UNAVAILABLE"
        assert "restricted_cash_unknown" in out["limitations"]

    def test_incomplete_schedule_withholds_funded_claim(self):
        out = build_funding_path(**full_kwargs(schedule_complete_through="2027-01-01T00:00:00Z"))
        assert out["path_state"] == "UNAVAILABLE"
        assert "funding_schedule_does_not_cover_recovery" in out["limitations"]

    def test_missing_schedule_completeness_withholds_funded_claim(self):
        out = build_funding_path(**full_kwargs(schedule_complete_through=None))
        assert out["path_state"] == "UNAVAILABLE"

    def test_incomplete_debt_ladder_withholds_funded_claim(self):
        out = build_funding_path(**full_kwargs(capital_need=capital_need(ladder_complete=False, status="partial")))
        assert out["path_state"] == "UNAVAILABLE"
        assert "debt_ladder_incomplete" in out["limitations"]

    def test_future_share_count_is_refused(self):
        with pytest.raises(CycleEquityError, match="future_at_decision"):
            build_funding_path(**full_kwargs(share_count_observation=share_count(available="2026-10-02T00:00:00Z")))

    def test_future_knowledge_event_is_refused(self):
        with pytest.raises(CycleEquityError, match="future_knowledge"):
            build_funding_path(**full_kwargs(funding_events=[
                event(
                    "cash_obligation", "future", "2026-12-01T00:00:00Z",
                    available_at="2026-10-02T00:00:00Z", amount=1.0,
                )
            ]))

    def test_event_after_recovery_does_not_backfill_terminal_path(self):
        out = build_funding_path(**full_kwargs(funding_events=[
            event(
                "equity_raise", "too_late", "2027-12-01T00:00:00Z",
                gross_proceeds=100.0, fees=0.0, issue_price=1.0, shares_issued=100.0,
            )
        ]))
        assert out["ending"]["accessible_cash"] == 100
        assert out["ending"]["common_shares"] == 100
        assert out["timeline"] == []

    def test_negative_operating_cash_change_can_create_breach(self):
        out = build_funding_path(**full_kwargs(funding_events=[
            event("operating_cash_change", "burn", "2026-12-01T00:00:00Z", amount=-90.0),
        ]))
        assert out["path_state"] == "BREACHED_BEFORE_RECOVERY"
        assert out["ending"]["accessible_cash"] == 10


class TestRecoveryScenario:
    def test_business_can_recover_while_original_share_loses(self):
        funding = build_funding_path(**full_kwargs(funding_events=[
            event(
                "equity_raise", "raise", "2026-12-01T00:00:00Z",
                gross_proceeds=200.0, fees=10.0, issue_price=1.0, shares_issued=200.0,
            ),
            event("cash_obligation", "investment", "2027-01-01T00:00:00Z", amount=190.0),
        ]))
        out = recovery_scenario(
            funding,
            enterprise_value=900.0,
            original_purchase_price_per_share=2.0,
        )
        assert funding["ending"]["accessible_cash"] == 100
        assert funding["ending"]["common_shares"] == 300
        assert out["common_equity_value"] == 600
        assert out["ending_value_per_continuing_common_share"] == 2
        assert out["original_cohort_terminal_value"] == 200
        assert out["scenario_return_on_total_contributed"] == pytest.approx(0)

    def test_business_value_growth_can_still_leave_original_cohort_below_cost(self):
        funding = build_funding_path(**full_kwargs(
            capital_need=capital_need(cash=0.0, debt=400.0),
            minimum_operating_cash=0.0,
            funding_events=[
                event(
                    "equity_raise", "raise", "2026-12-01T00:00:00Z",
                    gross_proceeds=200.0, fees=10.0, issue_price=1.0, shares_issued=200.0,
                ),
                event("cash_obligation", "investment", "2027-01-01T00:00:00Z", amount=190.0),
            ],
        ))
        out = recovery_scenario(
            funding,
            enterprise_value=900.0,
            original_purchase_price_per_share=2.0,
        )
        assert out["common_equity_value"] == 500
        assert out["ending_value_per_continuing_common_share"] == pytest.approx(5 / 3)
        assert out["scenario_return_on_total_contributed"] == pytest.approx(-1 / 6)
        assert out["enterprise_value_required_to_recover_original_purchase"] == pytest.approx(1000)

    @pytest.mark.parametrize(
        "issue_price, expected_required_ev",
        [(0.5, 1400.0), (1.0, 1000.0), (2.0, 800.0)],
    )
    def test_cheaper_equity_financing_raises_recovery_hurdle(self, issue_price, expected_required_ev):
        shares_issued = 200.0 / issue_price
        funding = build_funding_path(**full_kwargs(
            capital_need=capital_need(cash=0.0, debt=400.0),
            minimum_operating_cash=0.0,
            funding_events=[
                event(
                    "equity_raise", "raise", "2026-12-01T00:00:00Z",
                    gross_proceeds=200.0, fees=0.0,
                    issue_price=issue_price, shares_issued=shares_issued,
                ),
                event("cash_obligation", "investment", "2027-01-01T00:00:00Z", amount=200.0),
            ],
        ))
        out = recovery_scenario(
            funding, enterprise_value=900.0, original_purchase_price_per_share=2.0
        )
        assert out["enterprise_value_required_to_recover_original_purchase"] == pytest.approx(expected_required_ev)

    def test_breached_path_withholds_terminal_equity_value(self):
        funding = build_funding_path(**full_kwargs(funding_events=[
            event("cash_obligation", "payment", "2026-11-01T00:00:00Z", amount=120.0),
        ]))
        out = recovery_scenario(funding, enterprise_value=2_000.0, original_purchase_price_per_share=2)
        assert funding["path_state"] == "BREACHED_BEFORE_RECOVERY"
        assert out["common_equity_value"] is None
        assert out["original_cohort_terminal_value"] is None

    def test_incomplete_path_withholds_terminal_equity_value(self):
        funding = build_funding_path(**full_kwargs(schedule_complete_through=None))
        out = recovery_scenario(funding, enterprise_value=2_000.0, original_purchase_price_per_share=2)
        assert out["common_equity_value"] is None

    def test_debt_draw_is_not_free_equity_value(self):
        base = build_funding_path(**full_kwargs())
        levered = build_funding_path(**full_kwargs(funding_events=[
            event("debt_draw", "draw", "2026-12-01T00:00:00Z", principal=100.0, fees=0.0),
        ]))
        a = recovery_scenario(base, enterprise_value=900)
        b = recovery_scenario(levered, enterprise_value=900)
        assert a["common_equity_value"] == b["common_equity_value"]

    def test_cohort_participation_requires_new_money_in_return_denominator(self):
        funding = build_funding_path(**full_kwargs(funding_events=[
            event(
                "equity_raise", "rights", "2026-12-01T00:00:00Z",
                gross_proceeds=200.0, fees=0.0, issue_price=1.0, shares_issued=200.0,
                original_cohort_subscribed_shares=100.0,
                original_cohort_cash_contribution=100.0,
            ),
        ]))
        out = recovery_scenario(funding, enterprise_value=1_300.0, original_purchase_price_per_share=2.0)
        assert out["original_cohort_total_contributed"] == 300
        assert out["original_cohort_terminal_value"] == 800
        assert out["scenario_return_on_total_contributed"] == pytest.approx(5 / 3)

    def test_cancelled_security_without_distribution_is_unavailable_not_zero(self):
        funding = build_funding_path(**full_kwargs())
        out = recovery_scenario(
            funding, enterprise_value=2_000, original_purchase_price_per_share=2,
            security_state="canceled",
        )
        assert out["original_cohort_terminal_value"] is None
        assert "original_security_canceled_distribution_unestablished" in out["limitations"]

    def test_cancelled_security_uses_explicit_distribution_without_splicing(self):
        funding = build_funding_path(**full_kwargs())
        out = recovery_scenario(
            funding,
            enterprise_value=2_000,
            original_purchase_price_per_share=2,
            security_state="canceled",
            replacement_distribution={
                "source_ref": "court:plan",
                "cash_per_old_share": 0.1,
                "new_shares_per_old_share": 0.02,
                "new_share_value": 5.0,
            },
        )
        assert out["original_cohort_terminal_value"] == pytest.approx(20.0)
        assert out["scenario_return_on_total_contributed"] == pytest.approx(-0.9)

    def test_cancelled_security_with_unknown_new_share_value_is_unavailable(self):
        funding = build_funding_path(**full_kwargs())
        out = recovery_scenario(
            funding,
            enterprise_value=2_000,
            security_state="canceled",
            replacement_distribution={
                "source_ref": "court:plan",
                "cash_per_old_share": 0,
                "new_shares_per_old_share": 0.02,
                "new_share_value": None,
            },
        )
        assert out["original_cohort_terminal_value"] is None
        assert "replacement_new_share_value_unestablished" in out["limitations"]


class TestInventorySalesDiagnostic:
    def test_inventory_down_but_sales_down_faster_is_not_demand_confirmation(self):
        out = inventory_sales_diagnostic(
            prior_inventory=100, current_inventory=90,
            prior_sales=100, current_sales=80,
        )
        assert out["state"] == "INVENTORY_DOWN_SALES_DOWN_FASTER"
        assert out["inventory_change"] == pytest.approx(-0.10)
        assert out["sales_change"] == pytest.approx(-0.20)
        assert out["inventory_to_sales_change"] > 0

    def test_destocking_with_sales_strength_improves_ratio(self):
        out = inventory_sales_diagnostic(
            prior_inventory=100, current_inventory=90,
            prior_sales=100, current_sales=110,
        )
        assert out["state"] == "DESTOCKING_WITH_IMPROVING_INVENTORY_SALES_RATIO"
        assert out["inventory_to_sales_change"] < 0

    def test_no_authority_is_created(self):
        out = inventory_sales_diagnostic(
            prior_inventory=100, current_inventory=100,
            prior_sales=100, current_sales=100,
        )
        assert all(out[key] is False for key in (
            "rank_authority", "entry_authority", "sizing_authority", "trade_authority", "policy_authority"
        ))


class TestComposedCase:
    def test_complete_case_preserves_all_boundaries(self):
        out = build_cycle_equity_case(
            **full_kwargs(),
            enterprise_value=900.0,
            original_purchase_price_per_share=2.0,
        )
        assert out["schema"] == "prophet.cycle_equity_case/v1"
        assert out["funding"]["path_state"] == "FUNDED_TO_RECOVERY"
        assert out["recovery"]["ending_value_per_continuing_common_share"] == 6.0
        assert "current_market_permission" in out["not_established"]
        assert "automatic_average_down_permission" in out["not_established"]
        assert all(out[key] is False for key in (
            "rank_authority", "entry_authority", "sizing_authority", "trade_authority", "policy_authority"
        ))

    def test_input_objects_are_not_mutated(self):
        need = capital_need()
        shares = share_count()
        events = [
            event(
                "equity_raise", "raise", "2026-12-01T00:00:00Z",
                gross_proceeds=100.0, fees=0.0, issue_price=1.0, shares_issued=100.0,
            )
        ]
        before = (deepcopy(need), deepcopy(shares), deepcopy(events))
        build_cycle_equity_case(
            **full_kwargs(
                capital_need=need, share_count_observation=shares, funding_events=events
            ),
            enterprise_value=900,
        )
        assert (need, shares, events) == before

    def test_authoritative_child_input_is_refused(self):
        need = capital_need()
        need["authority"]["rank_authority"] = True
        with pytest.raises(CycleEquityError, match="authority_escalation"):
            build_funding_path(**full_kwargs(capital_need=need))


class TestNativeCapitalNeedIntegration:
    def test_actual_capital_need_v1_output_is_consumed_without_rederiving_cash_or_debt(self):
        import json
        from datetime import date
        from pathlib import Path

        from engine.capital_need import assemble_capital_need
        from engine.cash_runway import extract_cash_runway

        fixture = Path(__file__).parent / "fixtures" / "cash_runway" / "synthetic_burn.json"
        cash = extract_cash_runway(
            json.loads(fixture.read_text()),
            cik="0000099999",
            as_of=date(2025, 6, 1),
        )
        period = dict(cash["period"])
        debt = {
            "schema": "debt_maturity.v1",
            "status": "reported",
            "cik": "0000099999",
            "unit": "USD",
            "period": dict(period),
            "buckets": [
                {"key": "y1", "usd": 10_000_000, "reported": True, "drop_reason": None, "tag": "y1"},
                *[
                    {"key": key, "usd": 0, "reported": True, "drop_reason": None, "tag": key}
                    for key in ("y2", "y3", "y4", "y5", "after5")
                ],
            ],
            "total_reported_usd": 10_000_000,
            "as_of": period["filed"],
        }
        need = assemble_capital_need(
            debt,
            cash,
            issuer_id=ISSUER,
            security_id=SECURITY,
            as_of=date(2025, 6, 1),
        )
        assert need["status"] == "complete"

        out = build_funding_path(
            capital_need=need,
            share_count_observation=share_count(available="2025-05-31T20:00:00Z"),
            issuer_id=ISSUER,
            security_id=SECURITY,
            decision_at="2025-06-01T20:00:00Z",
            recovery_at="2025-12-31T20:00:00Z",
            funding_events=[],
            original_cohort_shares=100.0,
            minimum_operating_cash=0.0,
            restricted_cash={
                "state": "not_applicable",
                "amount": 0.0,
                "included_in_reported_cash": False,
                "source_ref": "fixture:no-restricted-cash",
                "available_at": "2025-05-31T20:00:00Z",
            },
            schedule_complete_through="2025-12-31T20:00:00Z",
        )
        assert out["path_state"] == "FUNDED_TO_RECOVERY"
        assert out["starting"]["reported_cash"] == need["reported"]["cash"]["value"]
        assert out["starting"]["reported_debt"] == need["reported"]["debt_due"]["total_reported_usd"]


class TestCycleEquityBrief:
    def test_business_recovery_loss_is_explicit_counterevidence(self):
        from engine.prophet_cycle_equity import cycle_equity_brief

        case = build_cycle_equity_case(
            **full_kwargs(
                capital_need=capital_need(cash=0.0, debt=400.0),
                minimum_operating_cash=0.0,
                funding_events=[
                    event(
                        "equity_raise", "raise", "2026-12-01T00:00:00Z",
                        gross_proceeds=200.0, fees=10.0, issue_price=1.0, shares_issued=200.0,
                    ),
                    event("cash_obligation", "investment", "2027-01-01T00:00:00Z", amount=190.0),
                ],
            ),
            enterprise_value=900.0,
            original_purchase_price_per_share=2.0,
        )
        brief = cycle_equity_brief(case)
        assert brief["summary_state"] == "RECOVERY_WITH_MATERIAL_EQUITY_RISK"
        codes = {row["code"] for row in brief["counterevidence"]}
        assert "BUSINESS_RECOVERY_DOES_NOT_RECOVER_ORIGINAL_CAPITAL" in codes
        assert "COMMON_SHARE_COUNT_INCREASED" in codes
        assert brief["rank_authority"] is False
        assert brief["entry_authority"] is False

    def test_early_funding_gap_is_first_class(self):
        from engine.prophet_cycle_equity import cycle_equity_brief

        case = build_cycle_equity_case(
            **full_kwargs(
                funding_events=[
                    event("cash_obligation", "payment", "2026-11-01T00:00:00Z", amount=120.0),
                    event(
                        "equity_raise", "later", "2027-01-01T00:00:00Z",
                        gross_proceeds=100.0, fees=0.0, issue_price=1.0, shares_issued=100.0,
                    ),
                ]
            ),
            enterprise_value=2_000,
            original_purchase_price_per_share=2,
        )
        brief = cycle_equity_brief(case)
        assert brief["summary_state"] == "FUNDING_GAP"
        row = next(x for x in brief["counterevidence"] if x["code"] == "FUNDING_GAP_BEFORE_RECOVERY")
        assert row["values"]["event_id"] == "payment"

    def test_unknown_restricted_cash_stays_incomplete(self):
        from engine.prophet_cycle_equity import cycle_equity_brief

        case = build_cycle_equity_case(
            **full_kwargs(restricted_cash={"state": "unknown", "amount": None}),
            enterprise_value=2_000,
        )
        brief = cycle_equity_brief(case)
        assert brief["summary_state"] == "EVIDENCE_INCOMPLETE"
        assert "restricted_cash_unknown" in brief["not_established"]
        assert "QUALIFIED_FUNDING_PATH_TO_RECOVERY" in brief["not_established"]

    def test_cancelled_security_never_splices_replacement_performance(self):
        from engine.prophet_cycle_equity import cycle_equity_brief

        case = build_cycle_equity_case(
            **full_kwargs(),
            enterprise_value=2_000,
            original_purchase_price_per_share=2,
            security_state="canceled",
            replacement_distribution={
                "source_ref": "court:plan",
                "cash_per_old_share": 0.1,
                "new_shares_per_old_share": 0.02,
                "new_share_value": 5.0,
            },
        )
        brief = cycle_equity_brief(case)
        row = next(x for x in brief["counterevidence"] if x["code"] == "ORIGINAL_SECURITY_CANCELED_AND_MAPPED")
        assert "not from splicing replacement-security performance" in row["text"]
        assert brief["trade_authority"] is False

    def test_hurdle_is_visible(self):
        from engine.prophet_cycle_equity import cycle_equity_brief

        case = build_cycle_equity_case(
            **full_kwargs(
                capital_need=capital_need(cash=0.0, debt=400.0),
                minimum_operating_cash=0.0,
                funding_events=[
                    event(
                        "equity_raise", "raise", "2026-12-01T00:00:00Z",
                        gross_proceeds=200.0, fees=0.0, issue_price=1.0, shares_issued=200.0,
                    ),
                    event("cash_obligation", "investment", "2027-01-01T00:00:00Z", amount=200.0),
                ],
            ),
            enterprise_value=900,
            original_purchase_price_per_share=2,
        )
        brief = cycle_equity_brief(case)
        row = next(x for x in brief["counterevidence"] if x["code"] == "ENTERPRISE_VALUE_RECOVERY_HURDLE")
        assert row["values"]["required_enterprise_value"] == pytest.approx(1000)

    def test_positive_scenario_still_disclaims_permission(self):
        from engine.prophet_cycle_equity import cycle_equity_brief

        case = build_cycle_equity_case(
            **full_kwargs(),
            enterprise_value=2_000,
            original_purchase_price_per_share=2,
        )
        brief = cycle_equity_brief(case)
        assert brief["summary_state"] == "SCENARIO_REACHES_ORIGINAL_COMMON"
        assert "current_market_permission" in brief["not_established"]
        assert "buy permission" in brief["interpretation"]

    def test_authoritative_case_is_refused(self):
        from engine.prophet_cycle_equity import cycle_equity_brief

        case = build_cycle_equity_case(
            **full_kwargs(),
            enterprise_value=2_000,
        )
        case["rank_authority"] = True
        with pytest.raises(CycleEquityError, match="authority_escalation"):
            cycle_equity_brief(case)
