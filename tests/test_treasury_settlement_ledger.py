"""Adversarial H3 source inventory, non-overlap and release-vintage gates."""
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
import json
from pathlib import Path
import unittest

from engine import treasury_settlement_ledger as ledger
from engine.treasury_auction_primitives import CashComponent, CashKind, InputRole, Observation, SecurityClass

AT = datetime(2026, 10, 5, 20, tzinfo=timezone.utc)
S = date(2026, 10, 6)
BEFORE = datetime(2026, 10, 5, 19, tzinfo=timezone.utc)
SHA = 'a' * 64


def claims():
    result = []
    for security, prefix, amounts in ((SecurityClass.BILL, 'bill', (100, 70, 5)),
            (SecurityClass.NOTE, 'coupon', (40, 60, 0))):
        for kind, amount in zip(CashKind, amounts):
            identity = prefix + ':' + kind.value
            a = Observation(Decimal(amount), 'USD', 'USD', BEFORE, BEFORE,
                'fixture:source', 'source-qualified-cash', InputRole.QUALIFIED)
            result.append(ledger.SettlementClaim(CashComponent(identity, kind, 'S6', S, a),
                security, SHA, 'fixture:row:' + identity, () if amount == 0 else (identity,),
                sourced_category_zero=amount == 0))
    return result


def inventory(values):
    return ledger.CohortInventory('S6', S, tuple(c.component.component_id for c in values),
        ledger.inventory_digest(values), BEFORE, 'fixture:inventory', 'fixture:independent-acceptance', True, True)


def qualify(values, certificate=True):
    return ledger.qualify_settlement_cohort(cohort_id='S6', settlement_date=S,
        decision_at=AT, claims=values, inventory=inventory(values) if certificate else None)


def vintage(series='TGCR', value='4.5', released=BEFORE, known=BEFORE, identity='first', **kwargs):
    a = Observation(Decimal(value), 'PERCENT', None, known, BEFORE,
        'fixture:rate', 'literal-release-vintage', InputRole.QUALIFIED)
    return ledger.FinancingVintage(series, date(2026, 10, 2), a, released, known, SHA, identity, **kwargs)


class SettlementLedgerTests(unittest.TestCase):
    def test_exact_channels_have_opposing_signs_without_prediction(self):
        with localcontext() as ctx:
            ctx.prec = 2
            out = qualify(claims())
        self.assertEqual(out['input_contract_status'], 'SOURCE_CONTRACT_SATISFIED')
        self.assertEqual(out['channels']['BILL_CMB']['net_private_cash_usd'], Decimal('25'))
        self.assertEqual(out['channels']['COUPON']['net_private_cash_usd'], Decimal('-20'))
        self.assertIsNone(out['net_private_cash_usd'])
        self.assertIsNone(out['reserve_pressure'])
        self.assertIsNone(out['probabilities'])
        self.assertEqual(out['research_admission'], 'REQUIRES_INDEPENDENT_SOURCE_PIT_REVIEW_AND_DATASET_FREEZE')

    def test_missing_inventory_never_self_certifies_from_ids(self):
        out = qualify(claims(), certificate=False)
        self.assertEqual(out['input_contract_status'], 'INSUFFICIENT_PIT')
        self.assertIn('missing_accepted_inventory', out['null_reasons'])
        self.assertTrue(all(v is None for v in out['channels'].values()))

    def test_certificate_cannot_precede_claims_or_inherit_unverified_acceptance(self):
        values = claims()
        for bad, reason in ((replace(inventory(values), known_at=BEFORE.replace(hour=18)),
                'inventory_precedes_claim_availability'),
                (replace(inventory(values), independent_acceptance_ref=None),
                'missing_independent_source_acceptance'),
                (replace(inventory(values), complete_private_universe=False),
                'inventory_completeness_or_nonoverlap_unaccepted')):
            out = ledger.qualify_settlement_cohort(cohort_id='S6', settlement_date=S,
                decision_at=AT, claims=values, inventory=bad)
            self.assertIn(reason, out['null_reasons'])
            self.assertTrue(all(v is None for v in out['channels'].values()))

    def test_truthy_certification_strings_cannot_grant_completeness(self):
        values = claims()
        bad = replace(inventory(values), complete_private_universe="false")
        with self.assertRaises(ValueError):
            ledger.qualify_settlement_cohort(cohort_id='S6', settlement_date=S,
                decision_at=AT, claims=values, inventory=bad)

    def test_two_ids_cannot_double_subtract_the_same_payment(self):
        values = claims()
        values[2] = replace(values[2], economic_claim_keys=values[1].economic_claim_keys)
        out = qualify(values)
        self.assertIn('overlapping_economic_payment', out['null_reasons'])
        self.assertIsNone(out['channels']['BILL_CMB'])

    def test_inventory_digest_binds_amount_basis_clock_and_scope(self):
        original = claims(); certificate = inventory(original)
        for mutation in (replace(original[0], cash_basis='FACE_VALUE'),
                replace(original[0], holder_scope='ALL_HOLDERS'),
                replace(original[0], component=replace(original[0].component,
                    amount=replace(original[0].component.amount, value=Decimal('101'))))):
            with self.subTest(mutation=mutation):
                values = [mutation] + original[1:]
                out = ledger.qualify_settlement_cohort(cohort_id='S6', settlement_date=S,
                    decision_at=AT, claims=values, inventory=certificate)
                self.assertIn('inventory_does_not_bind_exact_claims', out['null_reasons'])
                self.assertIsNone(out['channels']['BILL_CMB'])

    def test_missing_zero_cannot_be_inferred_from_an_empty_category(self):
        values = claims()[:-1]
        out = qualify(values)
        self.assertTrue(any(r.startswith('missing_inventory:COUPON:') for r in out['null_reasons']))

    def test_category_zero_cannot_hide_other_detail(self):
        values = claims()
        values.append(replace(values[-1], component=replace(values[-1].component, component_id='different-row')))
        self.assertIn('category_zero_conflicts_with_detail', qualify(values)['null_reasons'])

    def test_final_result_synthetic_and_future_cash_cannot_be_forecast_inputs(self):
        original = claims()
        for amount in (replace(original[0].component.amount, role=InputRole.RESULT),
                replace(original[0].component.amount, role=InputRole.SYNTHETIC),
                replace(original[0].component.amount, known_at=AT.replace(hour=21))):
            values = [replace(original[0], component=replace(original[0].component, amount=amount))] + original[1:]
            self.assertEqual(qualify(values)['input_contract_status'], 'INSUFFICIENT_PIT')

    def test_gross_face_soma_adjustment_and_wrong_cohort_are_not_private_cash(self):
        original = claims()
        for mutation in (replace(original[0], cash_basis='PAR_USD'),
                replace(original[0], soma_treatment='SUBTRACT_SOMA_AGAIN'),
                replace(original[0], component=replace(original[0].component, cohort_id='other'))):
            self.assertEqual(qualify([mutation] + original[1:])['input_contract_status'], 'INSUFFICIENT_PIT')

    def test_retrospective_source_receipts_cannot_qualify_october5_cutoff(self):
        root = Path(__file__).parents[1] / 'research/sovereign_auction_pressure/funding_audit'
        receipts = json.loads((root / 'SOURCE_RECEIPTS.json').read_text())
        self.assertEqual(len(receipts), 12)
        for r in receipts:
            # Hash and metadata verification belongs to the original audit. This
            # test specifically discriminates historical dates from local clocks.
            known = datetime.fromisoformat(r['verified_present_at'])
            self.assertGreater(known, AT)
        self.assertEqual(qualify([], certificate=False)['input_contract_status'], 'INSUFFICIENT_PIT')


class FinancingBaselineTests(unittest.TestCase):
    def test_future_iorb_release_never_uses_old_effective_date_to_enter_cutoff(self):
        later = vintage('IORB', released=AT.replace(hour=20, minute=30), known=AT.replace(hour=20, minute=31))
        out = ledger.financing_baseline_at([vintage(), later], AT)
        self.assertIn('TGCR', out['selected'])
        self.assertNotIn('IORB', out['selected'])
        self.assertEqual(out['status'], 'INSUFFICIENT_PIT')

    def test_revision_after_cutoff_preserves_first_released_vintage(self):
        first = vintage()
        revision = vintage(value='4.8', released=AT.replace(hour=21), known=AT.replace(hour=21), identity='revision', revision=True)
        before = ledger.financing_baseline_at([revision, first], AT)
        self.assertEqual(before['selected']['TGCR']['value'], '4.5')
        after = ledger.financing_baseline_at([first, revision], AT.replace(hour=22))
        self.assertEqual(after['selected']['TGCR']['value'], '4.8')
        self.assertTrue(after['selected']['TGCR']['revision'])

    def test_qualified_body_bound_leaves_exact_publication_unknown(self):
        bounded = replace(vintage(), release_at=None,
            release_clock_basis='QUALIFIED_OFFICIAL_BODY_AVAILABILITY_BOUND')
        out = ledger.financing_baseline_at([bounded], AT)
        selected = out['selected']['TGCR']
        self.assertIsNone(selected['release_at'])
        self.assertEqual(selected['release_available_by'], BEFORE.isoformat())
        future = replace(bounded, body_received_at=AT.replace(hour=21),
            observation=replace(bounded.observation, known_at=AT.replace(hour=21)))
        self.assertFalse(ledger.financing_baseline_at([future], AT)['selected'])

    def test_refetch_does_not_refresh_original_availability_or_override_revision(self):
        first = replace(vintage(), release_at=None,
            release_clock_basis='QUALIFIED_OFFICIAL_BODY_AVAILABILITY_BOUND')
        later = BEFORE.replace(minute=30)
        repeat = replace(first, body_received_at=AT,
            observation=replace(first.observation, known_at=AT))
        revision = replace(first, vintage_id='revision', source_digest='b' * 64,
            body_received_at=later, observation=replace(first.observation, value=Decimal('4.8'), known_at=later), revision=True)
        out = ledger.financing_baseline_at([repeat, revision, first], AT)
        self.assertEqual(out['selected']['TGCR']['value'], '4.8')

    def test_missing_release_and_interpolation_are_not_synthetic_knowledge(self):
        for v in (replace(vintage(), release_at=None), replace(vintage(), interpolated=True),
                replace(vintage(), observation=replace(vintage().observation, role=InputRole.RESULT))):
            out = ledger.financing_baseline_at([v], AT)
            self.assertFalse(out['selected'])

    def test_conflicting_same_release_versions_never_choose_digest_winner(self):
        first, contradiction = vintage(), vintage(value='9.9', identity='conflict')
        for values in ([first, contradiction], [contradiction, first]):
            out = ledger.financing_baseline_at(values, AT)
            self.assertNotIn('TGCR', out['selected'])
            self.assertTrue(out['conflicts'])

    def test_release_receipt_order_must_be_literal_and_causal(self):
        impossible = vintage(released=AT, known=BEFORE)
        self.assertFalse(ledger.financing_baseline_at([impossible], AT)['selected'])
