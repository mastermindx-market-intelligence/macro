import unittest

from research.special_situations_horizontal_reference import (
    map_transaction_relationships,
    transaction_lifecycle,
    merge_discovery_enrichment,
    invalidate_dependent_cases,
    route_registrant_event,
)


class HorizontalReferenceTests(unittest.TestCase):
    def test_parent_take_private_keeps_fund_indirect(self):
        rows = [
            {"security": "MGLD", "event_ref": "tmc-mdp", "source_origin": "tmc-mdp-announcement", "role": "target"},
            {"security": "USO", "event_ref": "tmc-mdp", "source_origin": "tmc-mdp-announcement", "role": "affected_through_general_partner_control"},
            {"security": "UNG", "event_ref": "tmc-mdp", "source_origin": "tmc-mdp-announcement", "role": "affected_through_general_partner_control"},
        ]
        out = map_transaction_relationships(rows)
        self.assertEqual(out["direct_targets"], ["MGLD"])
        self.assertEqual(out["affected_securities"], ["UNG", "USO"])
        self.assertEqual(out["independent_source_origins"], 1)

    def test_repeated_registrant_filings_do_not_multiply_confirmation(self):
        rows = [
            {"security": t, "event_ref": "tmc-mdp", "source_origin": "tmc-mdp-announcement", "role": "affected_through_general_partner_control"}
            for t in ["USO", "USL", "UNG", "UGA", "BNO", "CPER", "UNL"]
        ]
        out = map_transaction_relationships(rows)
        self.assertEqual(out["independent_source_origins"], 1)
        self.assertEqual(len(out["affected_securities"]), 7)

    def test_unrelated_close_does_not_close_other_transaction(self):
        events = [
            {"transaction_id": "deal-a", "stage": "announced", "known_at": "2026-01-01T10:00:00Z"},
            {"transaction_id": "deal-b", "stage": "announced", "known_at": "2026-01-02T10:00:00Z"},
            {"transaction_id": "deal-b", "stage": "closed", "known_at": "2026-02-01T10:00:00Z"},
        ]
        states = transaction_lifecycle(events)
        self.assertEqual(states["deal-a"]["current_stage"], "announced")
        self.assertEqual(states["deal-b"]["current_stage"], "closed")

    def test_partial_enrichment_preserves_unknown_discovery(self):
        discovered = [
            {"accession": "a", "form_type": "8-K"},
            {"accession": "b", "form_type": "8-K"},
        ]
        enrichment = {"a": {"items": ["1.01"]}}
        out = merge_discovery_enrichment(discovered, enrichment, special_items={"1.01"})
        self.assertEqual([r["accession"] for r in out], ["a", "b"])
        self.assertEqual(out[1]["enrichment_status"], "unknown")
        self.assertTrue(out[1]["items_unknown"])

    def test_observed_nonqualifying_enrichment_is_dropped(self):
        discovered = [{"accession": "a", "form_type": "8-K"}]
        enrichment = {"a": {"items": ["2.02"]}}
        out = merge_discovery_enrichment(discovered, enrichment, special_items={"1.01"})
        self.assertEqual(out, [])

    def test_revision_invalidates_only_dependent_cases(self):
        cases = [
            {"case_id": "fund-economics", "dependencies": {"tmc-mdp", "uscf-control"}},
            {"case_id": "unrelated-biotech", "dependencies": {"trial-abc"}},
        ]
        out = invalidate_dependent_cases(cases, changed_dependencies={"uscf-control"})
        self.assertEqual(out["invalidated"], ["fund-economics"])
        self.assertEqual(out["preserved"], ["unrelated-biotech"])


if __name__ == "__main__":
    unittest.main()

class RegistrantRoleRoutingTests(unittest.TestCase):
    def test_direct_family_with_incompatible_role_is_withheld(self):
        out = route_registrant_event(
            category="Going-Private",
            registrant_role="none",
            direct_roles={"target"},
        )
        self.assertEqual(out["projection"], "withheld")
        self.assertEqual(out["reason"], "relationship_unresolved")
        self.assertFalse(out["direct_target"])

    def test_bound_indirect_relation_preserves_context_without_target_semantics(self):
        out = route_registrant_event(
            category="Going-Private",
            registrant_role="none",
            direct_roles={"target"},
            affected_relation="affected_through_general_partner_control",
        )
        self.assertEqual(out["projection"], "affected")
        self.assertEqual(out["security_role"], "affected_through_general_partner_control")
        self.assertFalse(out["direct_target"])

    def test_compatible_direct_role_remains_direct(self):
        out = route_registrant_event(
            category="Going-Private",
            registrant_role="target",
            direct_roles={"target"},
        )
        self.assertEqual(out["projection"], "direct")
        self.assertTrue(out["direct_target"])
