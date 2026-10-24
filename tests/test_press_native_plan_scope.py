"""Pure stdlib tests for engine/press/native_plan_scope.py.

Fictional asset TEST and explicit dates only; no project data dependencies,
no generation/provider/network work.  Runs under pytest or
``python3 test_press_native_plan_scope.py``.
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.press import native_plan_scope as nps  # noqa: E402

ASSET = "TEST"
PRIMARY_REF = "chronicle:abc123"
PLAN_REF = "prophet_plan:abc123"
OTHER_REF = "chronicle:other999"
CANON = "https://www.mastermind-x.com/stocks/TEST.html"
OTHER_DOSSIER = "https://www.mastermind-x.com/stocks/OTHER.html"

BASE_SCOPE = {
    "source_ref": PRIMARY_REF,
    "asset": ASSET,
    "recorded_at": "2026-03-10",
    "price_basis_date": "2026-03-10",
    "close_date": "2026-03-12",
    "authority_tier": "display_only",
    "entry_status": "bounce_wait",
    "confirmed_date": None,
}

EXPECTED_FRAGMENTS = [
    "simulated paper plan",
    "plan recorded 2026-03-10",
    "price basis 2026-03-10",
    "display-only",
    "entry status bounce_wait",
    "signal tier not recorded",
    "signal provisional status not recorded",
    "T1 marker confirmation date not recorded",
    "simulated close 2026-03-12",
    "not an executed trade or investor return",
]

LINK_MARKUP = '<a href="' + CANON + '">TEST plan dossier</a>'
GOOD_BODY = (
    "<h2>TEST simulated paper plan</h2>"
    "<p>plan recorded 2026-03-10, price basis 2026-03-10, simulated close 2026-03-12.</p>"
    "<p>display-only; entry status bounce_wait; signal tier not recorded; signal provisional status not recorded; T1 marker confirmation date not recorded.</p>"
    "<p>simulated paper plan; not an executed trade or investor return.</p>"
    "<p>Continuation: " + LINK_MARKUP + "</p>"
)


def fact(ref, value=7, issuer="TEST"):
    return {"ref": ref, "issuer": issuer, "value": value, "kind": "fact"}


def context_facts():
    return [fact("context:%03d" % i, value=100 + i, issuer="HOUSE%d" % i) for i in range(21)]


def default_facts():
    return (
        [fact(PRIMARY_REF, value=42)]
        + [fact(PLAN_REF, value=43)]
        + context_facts()
        + [
            fact("context:numeric-echo", value=42, issuer="HOUSEX"),
            fact(OTHER_REF, issuer="OTHERCO"),
        ]
    )


def make_slot(**overrides):
    slot = SimpleNamespace(
        desk="brief",
        facts=default_facts(),
        sources=[PRIMARY_REF, OTHER_REF],
        primary_source=SimpleNamespace(ref=PRIMARY_REF, name="Prophet ledger close"),
        story=SimpleNamespace(tickers=["TEST", "OTHER"]),
        allowed_links=[CANON, OTHER_DOSSIER],
        as_of="2026-03-15",
        native_plan_scope=copy.deepcopy(BASE_SCOPE),
    )
    for key, value in overrides.items():
        setattr(slot, key, value)
    return slot


def slot_missing_metadata(**overrides):
    """Typed key present but None: native recognised, validation fails closed."""
    overrides["native_plan_scope"] = None
    return make_slot(**overrides)


def slot_no_metadata_key(**overrides):
    """No typed key at all, but the bound prophet_plan fact still binds."""
    slot = make_slot(**overrides)
    del slot.native_plan_scope
    return slot


def legacy_slot(**overrides):
    """Ordinary brief/research: no scope key, no bound plan fact."""
    overrides.setdefault("facts", [fact(PRIMARY_REF, value=42)] + context_facts())
    slot = make_slot(**overrides)
    del slot.native_plan_scope
    return slot


class RecognitionTests(unittest.TestCase):
    def test_typed_key_present_recognises_native_even_when_none(self):
        slot = slot_missing_metadata()
        self.assertTrue(nps.is_native_plan_brief(slot))
        with self.assertRaises(ValueError):
            nps.scope_fragments(slot)
        self.assertTrue(nps.scope_problems(GOOD_BODY, slot))
        with self.assertRaises(ValueError):
            nps.required_dossier(slot)

    def test_bound_plan_fact_recognises_native_without_metadata(self):
        self.assertTrue(nps.is_native_plan_brief(slot_no_metadata_key()))
        with self.assertRaises(ValueError):
            nps.scope_fragments(slot_no_metadata_key())

    def test_producer_identity_alone_is_not_native(self):
        slot = legacy_slot()
        slot.primary_source = SimpleNamespace(ref=PRIMARY_REF, name="Prophet ledger close")
        self.assertFalse(nps.is_native_plan_brief(slot))
        self.assertEqual(nps.scope_fragments(slot), [])
        self.assertEqual(nps.scope_problems("<p>plain note</p>", slot), [])
        self.assertIsNone(nps.required_dossier(slot))

    def test_unbound_plan_ref_for_other_identity_is_not_native(self):
        slot = legacy_slot(
            facts=[fact(PRIMARY_REF, value=42), fact("prophet_plan:zzz777", issuer="OTHERCO")]
        )
        self.assertFalse(nps.is_native_plan_brief(slot))
        self.assertEqual(nps.scope_fragments(slot), [])
        self.assertEqual(nps.scope_problems("<p>plain note</p>", slot), [])
        self.assertEqual(nps.receipt_facts(slot), slot.facts)

    def test_non_brief_desks_stay_false(self):
        for desk in ("research", "news", "briefing", None):
            with self.subTest(desk=desk):
                slot = make_slot(desk=desk)
                self.assertFalse(nps.is_native_plan_brief(slot))
                self.assertEqual(nps.scope_fragments(slot), [])
                self.assertEqual(nps.scope_problems(GOOD_BODY, slot), [])
                self.assertIsNone(nps.required_dossier(slot))
                self.assertEqual(nps.receipt_facts(slot), slot.facts)


class ReceiptFactTests(unittest.TestCase):
    def test_only_primary_lead_and_matching_plan_returned(self):
        refs = [item["ref"] for item in nps.receipt_facts(make_slot())]
        self.assertEqual(refs, [PRIMARY_REF, PLAN_REF])

    def test_unrelated_context_and_other_issuer_excluded(self):
        refs = {item["ref"] for item in nps.receipt_facts(make_slot())}
        self.assertNotIn(OTHER_REF, refs)
        self.assertEqual([r for r in refs if r.startswith("context:")], [])
        self.assertEqual(len(nps.receipt_facts(make_slot())), 2)

    def test_same_numeric_value_in_context_not_eligible(self):
        refs = {item["ref"] for item in nps.receipt_facts(make_slot())}
        self.assertNotIn("context:numeric-echo", refs)

    def test_primary_ref_not_in_sources_fails_closed(self):
        self.assertEqual(nps.receipt_facts(make_slot(sources=[OTHER_REF])), [])

    def test_inputs_are_never_modified(self):
        slot = make_slot()
        before_facts = copy.deepcopy(slot.facts)
        before_scope = copy.deepcopy(slot.native_plan_scope)
        identities = [id(item) for item in slot.facts]
        nps.receipt_facts(slot)
        nps.scope_fragments(slot)
        nps.scope_problems(GOOD_BODY, slot)
        nps.required_dossier(slot)
        self.assertEqual(slot.facts, before_facts)
        self.assertEqual(slot.native_plan_scope, before_scope)
        self.assertEqual([id(item) for item in slot.facts], identities)

    def test_legacy_brief_and_research_facts_unchanged(self):
        for slot in (legacy_slot(), legacy_slot(desk="research")):
            receipts = nps.receipt_facts(slot)
            self.assertEqual(receipts, slot.facts)
            for got, want in zip(receipts, slot.facts):
                self.assertIs(got, want)


class ScopeFragmentTests(unittest.TestCase):
    def test_non_native_returns_empty(self):
        self.assertEqual(nps.scope_fragments(legacy_slot()), [])

    def test_fragments_for_valid_scope(self):
        self.assertEqual(nps.scope_fragments(make_slot()), EXPECTED_FRAGMENTS)

    def test_missing_or_malformed_scope_raises(self):
        for slot in (slot_missing_metadata(), slot_no_metadata_key(),
                     make_slot(native_plan_scope="display-only")):
            with self.assertRaises(ValueError):
                nps.scope_fragments(slot)

    def test_missing_required_field_raises(self):
        for field in ("source_ref", "asset", "recorded_at", "price_basis_date",
                      "close_date", "authority_tier", "entry_status", "confirmed_date"):
            scope = copy.deepcopy(BASE_SCOPE)
            scope.pop(field)
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    nps.scope_fragments(make_slot(native_plan_scope=scope))

    def test_wrong_source_ref_raises(self):
        scope = dict(BASE_SCOPE, source_ref=OTHER_REF)
        with self.assertRaises(ValueError):
            nps.scope_fragments(make_slot(native_plan_scope=scope))

    def test_source_ref_not_in_slot_sources_raises(self):
        scope = dict(BASE_SCOPE, source_ref="chronicle:ghost")
        with self.assertRaises(ValueError):
            nps.scope_fragments(make_slot(native_plan_scope=scope))

    def test_asset_not_in_tickers_raises(self):
        for asset in ("NOPE", "OTHERX", "test lower"):
            scope = dict(BASE_SCOPE, asset=asset)
            with self.subTest(asset=asset):
                with self.assertRaises(ValueError):
                    nps.scope_fragments(make_slot(native_plan_scope=scope))

    def test_non_calendar_or_wrong_type_dates_raise(self):
        bad_values = ("not-a-date", "2026-13-01", "2026-03-41", "2026-3-10",
                      "20260310", "March 10, 2026", 20260310, True)
        for field in ("recorded_at", "price_basis_date", "close_date", "confirmed_date"):
            for bad in bad_values:
                scope = dict(BASE_SCOPE, **{field: bad})
                with self.subTest(field=field, bad=bad):
                    with self.assertRaises(ValueError):
                        nps.scope_fragments(make_slot(native_plan_scope=scope))

    def test_date_roles_ordered_with_equality_allowed(self):
        ok = dict(BASE_SCOPE, recorded_at="2026-03-12", price_basis_date="2026-03-12",
                  close_date="2026-03-12", confirmed_date="2026-03-12")
        frags = nps.scope_fragments(make_slot(native_plan_scope=ok))
        self.assertIn("plan recorded 2026-03-12", frags)
        self.assertIn("T1 marker confirmation date 2026-03-12", frags)
        bad = [
            dict(BASE_SCOPE, recorded_at="2026-03-13"),
            dict(BASE_SCOPE, price_basis_date="2026-03-13"),
            dict(BASE_SCOPE, confirmed_date="2026-03-13"),
            dict(BASE_SCOPE, close_date="2026-03-16"),
        ]
        for scope in bad:
            with self.subTest(scope=scope):
                with self.assertRaises(ValueError):
                    nps.scope_fragments(make_slot(native_plan_scope=scope))

    def test_as_of_required_and_parseable(self):
        slot = make_slot()
        del slot.as_of
        with self.assertRaises(ValueError):
            nps.scope_fragments(slot)
        with self.assertRaises(ValueError):
            nps.scope_fragments(make_slot(as_of="not-a-date"))

    def test_identity_tokens_lowercase_underscore_bounded(self):
        for field in ("authority_tier", "entry_status"):
            for bad in ("Display", "DISPLAY_ONLY", "has space", "dash-y", "", "x" * 41, None):
                scope = dict(BASE_SCOPE, **{field: bad})
                with self.subTest(field=field, bad=bad):
                    with self.assertRaises(ValueError):
                        nps.scope_fragments(make_slot(native_plan_scope=scope))

    def test_display_authority_requires_display_only_fragment(self):
        frags = nps.scope_fragments(make_slot())
        self.assertIn("display-only", frags)
        self.assertNotIn("plan authority display_only", frags)

    def test_non_display_authority_requires_plan_authority_value(self):
        scope = dict(BASE_SCOPE, authority_tier="proposed")
        frags = nps.scope_fragments(make_slot(native_plan_scope=scope))
        self.assertIn("plan authority proposed", frags)
        self.assertNotIn("display-only", frags)

    def test_confirmed_date_requires_confirmation_disclosure(self):
        scope = dict(BASE_SCOPE, confirmed_date="2026-03-11")
        frags = nps.scope_fragments(make_slot(native_plan_scope=scope))
        self.assertIn("T1 marker confirmation date 2026-03-11", frags)
        self.assertNotIn("T1 marker confirmation date not recorded", frags)


class RequiredDossierTests(unittest.TestCase):
    def test_returns_allowlisted_canonical_url(self):
        self.assertEqual(nps.required_dossier(make_slot()), CANON)

    def test_non_native_returns_none(self):
        self.assertIsNone(nps.required_dossier(legacy_slot()))

    def test_raises_when_canonical_not_allowlisted(self):
        slot = make_slot(
            allowed_links=["https://mastermind-x.com/stocks/TEST.html", OTHER_DOSSIER]
        )
        with self.assertRaises(ValueError):
            nps.required_dossier(slot)

    def test_raises_for_lookalike_wrong_issuer_or_empty_links(self):
        for links in (
            ["http://www.mastermind-x.com/stocks/TEST.html"],
            ["https://evil-mastermind-x.com/stocks/TEST.html"],
            ["https://www.mastermind-x.com/stocks/TESTX.html"],
            [OTHER_DOSSIER],
            ["https://www.mastermind-x.com/stocks/TEST.html?x=1"],
            [],
        ):
            with self.subTest(links=links):
                with self.assertRaises(ValueError):
                    nps.required_dossier(make_slot(allowed_links=links))

    def test_missing_metadata_raises(self):
        with self.assertRaises(ValueError):
            nps.required_dossier(slot_missing_metadata())


class ScopeProblemTests(unittest.TestCase):
    def test_pass_with_all_fragments_and_absolute_link(self):
        self.assertEqual(nps.scope_problems(GOOD_BODY, make_slot()), [])

    def test_pass_with_exact_relative_link_when_canonical_allowlisted(self):
        for href in ("/stocks/TEST.html",):
            with self.subTest(href=href):
                self.assertEqual(nps.scope_problems(GOOD_BODY.replace(CANON, href), make_slot()), [])

    def test_article_relative_stock_paths_are_not_the_canonical_dossier(self):
        for href in ("stocks/TEST.html", "./stocks/TEST.html"):
            with self.subTest(href=href):
                self.assertTrue(nps.scope_problems(GOOD_BODY.replace(CANON, href), make_slot()))

    def test_missing_scope_fails_closed(self):
        problems = nps.scope_problems(GOOD_BODY, slot_missing_metadata())
        self.assertTrue(problems)
        self.assertTrue(any("invalid native plan scope" in p for p in problems))

    def test_wrong_metadata_fails_closed(self):
        slot = make_slot(native_plan_scope=dict(BASE_SCOPE, asset="NOPE"))
        problems = nps.scope_problems(GOOD_BODY, slot)
        self.assertTrue(any("invalid native plan scope" in p for p in problems))

    def test_empty_body_reports_every_missing_piece(self):
        problems = nps.scope_problems("", make_slot())
        self.assertEqual(len(problems), len(EXPECTED_FRAGMENTS) + 1)
        for fragment in EXPECTED_FRAGMENTS:
            self.assertTrue(any(fragment in p for p in problems), fragment)
        self.assertTrue(any("continuation" in p for p in problems))

    def test_swapped_recorded_and_price_dates_fail(self):
        scope = dict(BASE_SCOPE, recorded_at="2026-03-10", price_basis_date="2026-03-11")
        body = (
            "<p>plan recorded 2026-03-11, price basis 2026-03-10, simulated close 2026-03-12.</p>"
            "<p>display-only; entry status bounce_wait; signal tier not recorded; signal provisional status not recorded; T1 marker confirmation date not recorded.</p>"
            "<p>simulated paper plan; not an executed trade or investor return.</p>"
            "<p>" + LINK_MARKUP + "</p>"
        )
        problems = nps.scope_problems(body, make_slot(native_plan_scope=scope))
        self.assertTrue(any("plan recorded 2026-03-10" in p for p in problems))
        self.assertTrue(any("price basis 2026-03-11" in p for p in problems))
        self.assertFalse(any("plan recorded 2026-03-11" in p for p in problems))

    def test_missing_display_disclosure_fails(self):
        problems = nps.scope_problems(GOOD_BODY.replace("display-only; ", ""), make_slot())
        self.assertTrue(any("display-only" in p for p in problems))

    def test_missing_entry_status_disclosure_fails(self):
        body = GOOD_BODY.replace("entry status bounce_wait", "entry status bounce-wait")
        problems = nps.scope_problems(body, make_slot())
        self.assertTrue(any("entry status bounce_wait" in p for p in problems))

    def test_missing_null_confirmation_disclosure_fails(self):
        body = GOOD_BODY.replace("T1 marker confirmation date not recorded", "T1 marker confirmation date 2026-03-12")
        problems = nps.scope_problems(body, make_slot())
        self.assertTrue(any("T1 marker confirmation date not recorded" in p for p in problems))

    def test_missing_mandatory_paper_plan_disclosures_fail(self):
        head = (
            "<p>plan recorded 2026-03-10, price basis 2026-03-10, simulated close 2026-03-12.</p>"
            "<p>display-only; entry status bounce_wait; signal tier not recorded; signal provisional status not recorded; T1 marker confirmation date not recorded.</p>"
        )
        body_no_paper_plan = head + "<p>not an executed trade or investor return.</p>" + LINK_MARKUP
        self.assertEqual(
            nps.scope_problems(body_no_paper_plan, make_slot()),
            ["missing required native plan disclosure: simulated paper plan"],
        )
        body_no_notrade = head + "<p>simulated paper plan.</p>" + LINK_MARKUP
        self.assertEqual(
            nps.scope_problems(body_no_notrade, make_slot()),
            ["missing required native plan disclosure: not an executed trade or investor return"],
        )

    def test_bare_url_text_is_not_a_continuation(self):
        body = GOOD_BODY.replace(LINK_MARKUP, CANON)
        problems = nps.scope_problems(body, make_slot())
        self.assertTrue(any("continuation" in p for p in problems))

    def test_escaped_anchor_markup_is_not_a_continuation(self):
        escaped = "&lt;a href=&quot;" + CANON + "&quot;&gt;TEST plan dossier&lt;/a&gt;"
        problems = nps.scope_problems(GOOD_BODY.replace(LINK_MARKUP, escaped), make_slot())
        self.assertTrue(any("continuation" in p for p in problems))

    def test_href_on_non_anchor_tag_is_not_a_continuation(self):
        body = GOOD_BODY.replace(
            LINK_MARKUP, '<span href="' + CANON + '">TEST plan dossier</span>'
        )
        problems = nps.scope_problems(body, make_slot())
        self.assertTrue(any("continuation" in p for p in problems))

    def test_lookalike_other_issuer_or_off_allowlist_links_fail(self):
        for href in (
            "https://www.mastermind-x.com/stocks/TESTX.html",
            "https://www.mastermind-x.com/stocks/OTHER.html",
            "http://www.mastermind-x.com/stocks/TEST.html",
            "https://evil-mastermind-x.com/stocks/TEST.html",
            "https://www.mastermind-x.com/stocks/TEST.html.extra",
            "https://www.mastermind-x.com/stocks/TEST.html#plan",
            "https://www.mastermind-x.com/stocks/test.html",
        ):
            with self.subTest(href=href):
                problems = nps.scope_problems(GOOD_BODY.replace(CANON, href), make_slot())
                self.assertTrue(any("continuation" in p for p in problems))

    def test_continuation_requires_allowlisted_dossier(self):
        slot = make_slot(allowed_links=["https://mastermind-x.com/stocks/TEST.html"])
        problems = nps.scope_problems(GOOD_BODY, slot)
        self.assertTrue(any("not present in slot.allowed_links" in p for p in problems))

    def test_fragment_matching_is_case_and_whitespace_normalized(self):
        body = GOOD_BODY.replace("plan recorded 2026-03-10", "PLAN RECORDED   2026-03-10")
        self.assertEqual(nps.scope_problems(body, make_slot()), [])

    def test_hidden_script_and_comment_text_do_not_count(self):
        stripped = GOOD_BODY.replace("simulated paper plan", "")
        wraps = (
            lambda frag: "<!-- " + frag + " -->",
            lambda frag: "<script>" + frag + "</script>",
            lambda frag: "<style>" + frag + "</style>",
            lambda frag: '<div hidden>' + frag + "</div>",
            lambda frag: '<div aria-hidden="true">' + frag + "</div>",
        )
        for wrap in wraps:
            body = stripped + wrap("simulated paper plan")
            with self.subTest(wrap=wrap("simulated paper plan")):
                self.assertEqual(
                    nps.scope_problems(body, make_slot()),
                    ["missing required native plan disclosure: simulated paper plan"],
                )

    def test_non_native_body_needs_nothing(self):
        self.assertEqual(nps.scope_problems("<p>plain research note</p>", legacy_slot()), [])

    def test_body_and_slot_inputs_unmodified_by_scope_problems(self):
        slot = make_slot()
        snapshot = copy.deepcopy(slot.native_plan_scope)
        body_before = GOOD_BODY
        nps.scope_problems(GOOD_BODY, slot)
        self.assertEqual(slot.native_plan_scope, snapshot)
        self.assertEqual(GOOD_BODY, body_before)

    def test_dict_shaped_slot_is_supported(self):
        slot = {
            "desk": "brief",
            "facts": default_facts(),
            "sources": [PRIMARY_REF, OTHER_REF],
            "primary_source": {"ref": PRIMARY_REF, "name": "Prophet ledger close"},
            "story": {"tickers": ["TEST", "OTHER"]},
            "allowed_links": [CANON],
            "as_of": "2026-03-15",
            "native_plan_scope": copy.deepcopy(BASE_SCOPE),
        }
        self.assertTrue(nps.is_native_plan_brief(slot))
        self.assertEqual([f["ref"] for f in nps.receipt_facts(slot)], [PRIMARY_REF, PLAN_REF])
        self.assertEqual(nps.scope_fragments(slot), EXPECTED_FRAGMENTS)
        self.assertEqual(nps.scope_problems(GOOD_BODY, slot), [])
        self.assertEqual(nps.required_dossier(slot), CANON)


if __name__ == "__main__":
    unittest.main(verbosity=2)
