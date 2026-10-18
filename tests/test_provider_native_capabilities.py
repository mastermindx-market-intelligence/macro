"""Tests for the Provider Control native registration source.

Pure stdlib only; registry and transition fixtures are built in memory.
The checked-in source contract is also validated without provider access.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
from pathlib import Path
import unittest

from engine import provider_native_capabilities as pnc

D64 = "a" * 32 + "b" * 32  # valid lowercase 64-hex material source digest
D64_ALT = "0123456789abcdef" * 4


def make_row(
    cid="cap.fixture-a",
    gen=1,
    provider="minimax",
    billing="subscription",
    cred="api_key",
    surface="native_cli",
    state="registered",
):
    return {
        "capacity_capability_id": cid,
        "capability_generation": gen,
        "provider": provider,
        "billing_mode": billing,
        "credential_kind": cred,
        "execution_surface": surface,
        "registration_state": state,
    }


def make_claude_row(cid="cap.fixture-b", gen=1, state="registered"):
    return make_row(
        cid=cid,
        gen=gen,
        provider="claude",
        cred="attached_login",
        state=state,
    )


def make_registry(rows, schema=pnc.REGISTRY_SCHEMA, owner=pnc.OWNER_PROGRAM):
    return {"schema": schema, "owner_program": owner, "capabilities": list(rows)}


def empty_registry():
    return make_registry([])


def expected_receipt(export):
    payload = {
        key: value
        for key, value in export.items()
        if key != "registration_receipt_digest"
    }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class NativeCapabilityTestCase(unittest.TestCase):
    def assertCode(self, callable_obj, code):
        with self.assertRaises(pnc.NativeCapabilityError) as ctx:
            callable_obj()
        self.assertEqual(ctx.exception.code, code)
        self.assertEqual(str(ctx.exception), code)
        self.assertIn(code, pnc.ERROR_CODES)
        self.assertIsInstance(ctx.exception, ValueError)


class TestRegistryShape(NativeCapabilityTestCase):
    def test_checked_in_registry_obeys_closed_contract(self):
        source = Path(__file__).resolve().parent.parent / "config/provider_native_capabilities.v1.json"
        document = json.loads(source.read_text(encoding="utf-8"))
        self.assertEqual(pnc.validate_registry(document), document)

    def test_minimal_valid_registry(self):
        out = pnc.validate_registry(make_registry([make_row()]))
        self.assertEqual(out["schema"], pnc.REGISTRY_SCHEMA)
        self.assertEqual(out["owner_program"], pnc.OWNER_PROGRAM)
        self.assertEqual(out["capabilities"], [make_row()])

    def test_empty_registry_valid(self):
        out = pnc.validate_registry(empty_registry())
        self.assertEqual(out["capabilities"], [])

    def test_canonical_sort_by_capability_id(self):
        doc = make_registry(
            [
                make_row(cid="cap.c"),
                make_row(cid="cap.a"),
                make_row(cid="cap.b"),
            ]
        )
        out = pnc.validate_registry(doc)
        self.assertEqual(
            [row["capacity_capability_id"] for row in out["capabilities"]],
            ["cap.a", "cap.b", "cap.c"],
        )

    def test_document_not_a_dict(self):
        for bad in (None, [], "registry", 7, True, [make_row()]):
            self.assertCode(
                lambda bad=bad: pnc.validate_registry(bad),
                "invalid_registry_document",
            )

    def test_wrong_schema(self):
        self.assertCode(
            lambda: pnc.validate_registry(
                make_registry([], schema="mastermind.provider_capacity/v1")
            ),
            "invalid_registry_schema",
        )

    def test_schema_wrong_type(self):
        self.assertCode(
            lambda: pnc.validate_registry(make_registry([], schema=7)),
            "invalid_registry_schema",
        )

    def test_wrong_owner_program(self):
        self.assertCode(
            lambda: pnc.validate_registry(make_registry([], owner="other")),
            "invalid_owner_program",
        )

    def test_extra_top_level_key_refused(self):
        doc = make_registry([])
        doc["host"] = "example.internal"
        self.assertCode(
            lambda: pnc.validate_registry(doc), "unexpected_registry_field"
        )

    def test_extra_nested_row_keys_refused(self):
        for extra in (
            {"host": "h"},
            {"principal": "p"},
            {"worker": "w"},
            {"path": "/x"},
            {"quota": 3},
            {"api_key": "raw-secret"},
            {"account_id": "a"},
            {"email": "e@x"},
        ):
            row = make_row()
            row.update(extra)
            self.assertCode(
                lambda row=row: pnc.validate_registry(make_registry([row])),
                "unexpected_capability_field",
            )

    def test_missing_top_level_key_refused(self):
        for key in ("schema", "owner_program", "capabilities"):
            doc = make_registry([])
            del doc[key]
            self.assertCode(
                lambda doc=doc: pnc.validate_registry(doc),
                "missing_registry_field",
            )

    def test_missing_row_key_refused(self):
        for key in (
            "capacity_capability_id",
            "capability_generation",
            "provider",
            "billing_mode",
            "credential_kind",
            "execution_surface",
            "registration_state",
        ):
            row = make_row()
            del row[key]
            self.assertCode(
                lambda row=row: pnc.validate_registry(make_registry([row])),
                "missing_capability_field",
            )

    def test_capabilities_not_a_list(self):
        for bad in ({"cap": make_row()}, "caps", (), 5, True, None):
            doc = {
                "schema": pnc.REGISTRY_SCHEMA,
                "owner_program": pnc.OWNER_PROGRAM,
                "capabilities": bad,
            }
            self.assertCode(
                lambda doc=doc: pnc.validate_registry(doc),
                "invalid_capabilities",
            )

    def test_row_not_a_dict(self):
        for bad in ("row", 3, [], None, True):
            self.assertCode(
                lambda bad=bad: pnc.validate_registry(make_registry([bad])),
                "invalid_capability_row",
            )

    def test_duplicate_capability_id_refused(self):
        doc = make_registry([make_row(cid="cap.x", gen=1), make_row(cid="cap.x", gen=2)])
        self.assertCode(
            lambda: pnc.validate_registry(doc), "duplicate_capability_id"
        )

    def test_capability_bound_32_accepted_33_refused(self):
        rows = [make_row(cid="cap.slot.%02d" % index) for index in range(32)]
        out = pnc.validate_registry(make_registry(rows))
        self.assertEqual(len(out["capabilities"]), 32)
        rows.append(make_row(cid="cap.slot.32"))
        self.assertCode(
            lambda: pnc.validate_registry(make_registry(rows)),
            "capability_bound_exceeded",
        )


class TestRowFields(NativeCapabilityTestCase):
    def test_valid_ids_accepted_including_max_length(self):
        long_id = "a" + "b.-_" * 31 + "xyz"  # exactly 128 chars
        self.assertEqual(len(long_id), 128)
        row = make_row(cid=long_id)
        out = pnc.validate_registry(make_registry([row]))
        self.assertEqual(out["capabilities"][0]["capacity_capability_id"], long_id)

    def test_invalid_capability_ids(self):
        bad_ids = [
            "",
            "-leading",
            ".leading",
            "_leading",
            "has space",
            "has/slash",
            "has:colon",
            "has@at",
            "uni-code-é",
            "tab\there",
            "new\nline",
            "x" * 129,
            7,
            None,
            True,
            ["cap.x"],
        ]
        for bad in bad_ids:
            row = make_row(cid=bad)
            self.assertCode(
                lambda row=row: pnc.validate_registry(make_registry([row])),
                "invalid_capability_id",
            )

    def test_legacy_oauth_codex_deepseek_slot_names_refused(self):
        for bad in (
            "oauth",
            "OAuth",
            "codex",
            "deepseek",
            "oauth-v1",
            "oauth_slot",
            "codex.cli",
            "codex-session",
            "deepseek_api",
            "deepseek.chat",
        ):
            row = make_row(cid=bad)
            self.assertCode(
                lambda row=row: pnc.validate_registry(make_registry([row])),
                "forbidden_capability_id",
            )

    def test_non_legacy_ids_containing_stem_subset_allowed(self):
        # Opaque ids that merely contain a stem as a non-prefix fragment are
        # not legacy slot names.
        out = pnc.validate_registry(make_registry([make_row(cid="cap.researcher")]))
        self.assertEqual(len(out["capabilities"]), 1)

    def test_generation_boundaries(self):
        row = make_row(gen=1)
        pnc.validate_registry(make_registry([row]))
        row = make_row(gen=pnc.MAX_GENERATION)
        pnc.validate_registry(make_registry([row]))

    def test_invalid_generations_fail_closed(self):
        bad_generations = [
            0,
            -1,
            pnc.MAX_GENERATION + 1,
            2**64,
            True,  # bool-as-int must fail closed
            False,
            "1",
            1.0,
            1.5,
            None,
            [1],
            {"g": 1},
        ]
        for bad in bad_generations:
            row = make_row(gen=bad)
            self.assertCode(
                lambda row=row: pnc.validate_registry(make_registry([row])),
                "invalid_capability_generation",
            )

    def test_provider_allowlist(self):
        for bad in ("openai", "grok", "deepseek", "Claude", "MiniMax", "", 7, None, True):
            row = make_row(provider=bad)
            self.assertCode(
                lambda row=row: pnc.validate_registry(make_registry([row])),
                "invalid_provider",
            )

    def test_billing_mode_closed(self):
        for bad in ("paygo", "api", "usage", "subscription ", 7, None, True):
            row = make_row(billing=bad)
            self.assertCode(
                lambda row=row: pnc.validate_registry(make_registry([row])),
                "invalid_billing_mode",
            )

    def test_execution_surface_closed(self):
        for bad in ("api", "sdk", "native_cli ", "Native_Cli", 7, None, True):
            row = make_row(surface=bad)
            self.assertCode(
                lambda row=row: pnc.validate_registry(make_registry([row])),
                "invalid_execution_surface",
            )

    def test_provider_credential_kind_pairs(self):
        row = make_row(provider="claude", cred="api_key")
        self.assertCode(
            lambda: pnc.validate_registry(make_registry([row])),
            "provider_credential_mismatch",
        )
        row = make_row(provider="minimax", cred="attached_login")
        self.assertCode(
            lambda: pnc.validate_registry(make_registry([row])),
            "provider_credential_mismatch",
        )
        row = make_row(provider="minimax", cred="oauth")
        self.assertCode(
            lambda: pnc.validate_registry(make_registry([row])),
            "provider_credential_mismatch",
        )

    def test_credential_kind_must_be_string(self):
        for bad in (7, None, True, ["api_key"]):
            row = make_row(cred=bad)
            self.assertCode(
                lambda row=row: pnc.validate_registry(make_registry([row])),
                "invalid_credential_kind",
            )

    def test_registration_state_closed(self):
        for bad in ("pending", "ready", "registered ", "Registered", 7, None, True):
            row = make_row(state=bad)
            self.assertCode(
                lambda row=row: pnc.validate_registry(make_registry([row])),
                "invalid_registration_state",
            )

    def test_valid_rows_for_both_providers(self):
        out = pnc.validate_registry(make_registry([make_claude_row(), make_row()]))
        self.assertEqual(len(out["capabilities"]), 2)


class TestPurityAndFreshness(NativeCapabilityTestCase):
    def test_validation_does_not_mutate_input(self):
        doc = make_registry([make_row(), make_claude_row()])
        snapshot = copy.deepcopy(doc)
        out = pnc.validate_registry(doc)
        out["capabilities"][0]["capability_generation"] = 999
        out["capabilities"][0]["registration_state"] = "revoked"
        out["capabilities"].append(make_row(cid="cap.injected"))
        out["schema"] = "tampered"
        self.assertEqual(doc, snapshot)

    def test_validation_returns_fresh_rows_not_aliases(self):
        doc = make_registry([make_row()])
        out = pnc.validate_registry(doc)
        self.assertIsNot(out, doc)
        self.assertIsNot(out["capabilities"], doc["capabilities"])
        self.assertIsNot(out["capabilities"][0], doc["capabilities"][0])

    def test_repeated_validation_results_are_independent(self):
        doc = make_registry([make_row()])
        first = pnc.validate_registry(doc)
        second = pnc.validate_registry(doc)
        self.assertEqual(first, second)
        first["capabilities"][0]["registration_state"] = "revoked"
        first["capabilities"].append(make_row(cid="cap.extra"))
        self.assertEqual(second, pnc.validate_registry(doc))

    def test_transition_does_not_mutate_inputs(self):
        previous = make_registry([make_row(gen=2)])
        current = make_registry([make_row(gen=2, state="revoked")])
        previous_snapshot = copy.deepcopy(previous)
        current_snapshot = copy.deepcopy(current)
        out = pnc.validate_registry_transition(previous, current)
        out["capabilities"][0]["registration_state"] = "registered"
        self.assertEqual(previous, previous_snapshot)
        self.assertEqual(current, current_snapshot)

    def test_export_does_not_mutate_registry_and_is_fresh(self):
        doc = make_registry([make_row()])
        snapshot = copy.deepcopy(doc)
        first = pnc.registration_export(doc, "cap.fixture-a", material_source_digest=D64)
        second = pnc.registration_export(doc, "cap.fixture-a", material_source_digest=D64)
        self.assertEqual(doc, snapshot)
        self.assertIsNot(first, second)
        first["registration_state"] = "registered"
        first["capability_generation"] = 42
        self.assertEqual(doc, snapshot)
        self.assertEqual(
            second["registration_state"], "registered"
        )
        self.assertEqual(second["capability_generation"], 1)

    def test_module_imports_no_io_surface(self):
        # stdlib-only, pure: no os/socket/subprocess network-or-process
        # surface may be bound in the module namespace.
        for forbidden in ("os", "socket", "subprocess", "requests", "urllib", "pathlib"):
            self.assertNotIn(forbidden, vars(pnc))


class TestTransitions(NativeCapabilityTestCase):
    def test_first_registration_requires_registered(self):
        out = pnc.validate_registry_transition(
            empty_registry(), make_registry([make_row(), make_claude_row()])
        )
        self.assertEqual(len(out["capabilities"]), 2)

    def test_first_registration_refuses_revoked(self):
        self.assertCode(
            lambda: pnc.validate_registry_transition(
                empty_registry(), make_registry([make_row(state="revoked")])
            ),
            "transition_first_registration_not_registered",
        )

    def test_missing_previous_must_be_supplied_explicitly(self):
        self.assertCode(
            lambda: pnc.validate_registry_transition(None, make_registry([make_row()])),
            "missing_previous_registry",
        )

    def test_missing_current_refused(self):
        self.assertCode(
            lambda: pnc.validate_registry_transition(empty_registry(), None),
            "missing_current_registry",
        )

    def test_identity_unchanged_transition_valid(self):
        previous = make_registry([make_row(gen=3, state="revoked")])
        current = make_registry([make_row(gen=5)])
        out = pnc.validate_registry_transition(previous, current)
        self.assertEqual(out["capabilities"][0]["capability_generation"], 5)

    def test_capability_removal_refused(self):
        previous = make_registry([make_row(), make_claude_row()])
        current = make_registry([make_row()])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_capability_removed",
        )

    def test_whole_domain_removal_refused(self):
        previous = make_registry([make_row()])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, empty_registry()),
            "transition_capability_removed",
        )

    def test_identity_mutation_refused_for_each_identity_field(self):
        # A provider change is only expressible as a valid document when its
        # credential_kind moves to the matching kind, so the constructible
        # identity mutation is the provider+kind pair (two identity fields).
        previous = make_registry([make_row(gen=1)])
        current = make_registry(
            [make_row(gen=1, provider="claude", cred="attached_login")]
        )
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_identity_changed",
        )

    def test_lone_credential_kind_flip_fails_closed_earlier(self):
        # Flipping credential_kind alone yields an invalid provider/kind pair
        # and is refused at validation, before the transition gate.
        previous = make_registry([make_row(gen=1)])
        self.assertCode(
            lambda: pnc.validate_registry_transition(
                previous, make_registry([make_row(gen=1, cred="attached_login")])
            ),
            "provider_credential_mismatch",
        )

    def test_billing_and_surface_identity_mutations_fail_closed_earlier(self):
        # billing_mode and execution_surface have a single-value closed
        # vocabulary, so any mutation produces an invalid document and is
        # refused at validation, before the transition gate can see it.
        previous = make_registry([make_row(gen=1)])
        self.assertCode(
            lambda: pnc.validate_registry_transition(
                previous, make_registry([make_row(gen=1, billing="api")])
            ),
            "invalid_billing_mode",
        )
        self.assertCode(
            lambda: pnc.validate_registry_transition(
                previous, make_registry([make_row(gen=1, surface="sdk")])
            ),
            "invalid_execution_surface",
        )

    def test_registered_to_registered_same_generation_valid(self):
        previous = make_registry([make_row(gen=4)])
        current = make_registry([make_row(gen=4)])
        out = pnc.validate_registry_transition(previous, current)
        self.assertEqual(out["capabilities"][0]["registration_state"], "registered")

    def test_registered_generation_bump_refused(self):
        previous = make_registry([make_row(gen=4)])
        current = make_registry([make_row(gen=5)])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_registered_generation_changed",
        )

    def test_registered_generation_rollback_refused(self):
        previous = make_registry([make_row(gen=4)])
        current = make_registry([make_row(gen=3)])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_generation_rollback",
        )

    def test_registered_to_revoked_same_generation_valid(self):
        previous = make_registry([make_row(gen=4)])
        current = make_registry([make_row(gen=4, state="revoked")])
        out = pnc.validate_registry_transition(previous, current)
        self.assertEqual(out["capabilities"][0]["registration_state"], "revoked")
        self.assertEqual(out["capabilities"][0]["capability_generation"], 4)

    def test_registered_to_revoked_generation_bump_refused(self):
        previous = make_registry([make_row(gen=4)])
        current = make_registry([make_row(gen=5, state="revoked")])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_revocation_generation_changed",
        )

    def test_registered_to_revoked_generation_rollback_refused(self):
        previous = make_registry([make_row(gen=4)])
        current = make_registry([make_row(gen=2, state="revoked")])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_generation_rollback",
        )

    def test_revoked_tombstone_persists(self):
        previous = make_registry([make_row(gen=4, state="revoked")])
        current = make_registry([make_row(gen=4, state="revoked")])
        out = pnc.validate_registry_transition(previous, current)
        self.assertEqual(out["capabilities"][0]["registration_state"], "revoked")

    def test_incrementing_tombstone_refused(self):
        previous = make_registry([make_row(gen=4, state="revoked")])
        current = make_registry([make_row(gen=5, state="revoked")])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_tombstone_generation_changed",
        )

    def test_tombstone_decrement_refused(self):
        previous = make_registry([make_row(gen=4, state="revoked")])
        current = make_registry([make_row(gen=3, state="revoked")])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_tombstone_generation_changed",
        )

    def test_same_generation_resurrection_refused(self):
        previous = make_registry([make_row(gen=4, state="revoked")])
        current = make_registry([make_row(gen=4)])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_capability_resurrection",
        )

    def test_revival_below_tombstone_rollback_refused(self):
        previous = make_registry([make_row(gen=4, state="revoked")])
        current = make_registry([make_row(gen=2)])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_generation_rollback",
        )

    def test_revival_above_tombstone_valid(self):
        previous = make_registry([make_row(gen=4, state="revoked")])
        current = make_registry([make_row(gen=5)])
        out = pnc.validate_registry_transition(previous, current)
        self.assertEqual(out["capabilities"][0]["capability_generation"], 5)
        self.assertEqual(out["capabilities"][0]["registration_state"], "registered")

    def test_new_capability_enrollment_must_be_registered(self):
        previous = make_registry([make_row()])
        current = make_registry([make_row(), make_claude_row()])
        out = pnc.validate_registry_transition(previous, current)
        self.assertEqual(len(out["capabilities"]), 2)
        previous = make_registry([make_row()])
        current = make_registry([make_row(), make_claude_row(state="revoked")])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, current),
            "transition_new_capability_not_registered",
        )

    def test_transition_validates_both_documents(self):
        bad_previous = make_registry([make_row()], schema="nope")
        current = make_registry([make_row()])
        self.assertCode(
            lambda: pnc.validate_registry_transition(bad_previous, current),
            "invalid_registry_schema",
        )
        previous = make_registry([make_row()])
        bad_current = make_registry([make_row(gen=0)])
        self.assertCode(
            lambda: pnc.validate_registry_transition(previous, bad_current),
            "invalid_capability_generation",
        )

    def test_transition_returns_normalized_current(self):
        current = make_registry([make_claude_row(), make_row(cid="cap.a")])
        out = pnc.validate_registry_transition(empty_registry(), current)
        self.assertEqual(
            [row["capacity_capability_id"] for row in out["capabilities"]],
            ["cap.a", "cap.fixture-b"],
        )


class TestRegistrationExport(NativeCapabilityTestCase):
    def test_export_shape_and_receipt(self):
        doc = make_registry([make_row(gen=7)])
        export = pnc.registration_export(
            doc, "cap.fixture-a", material_source_digest=D64
        )
        self.assertEqual(export["schema"], pnc.REGISTRATION_EXPORT_SCHEMA)
        self.assertEqual(
            set(export),
            {
                "schema",
                "capacity_capability_id",
                "capability_generation",
                "provider",
                "billing_mode",
                "credential_kind",
                "execution_surface",
                "registration_state",
                "material_source_digest",
                "registration_receipt_digest",
            },
        )
        self.assertEqual(export["capability_generation"], 7)
        self.assertEqual(export["registration_state"], "registered")
        self.assertEqual(export["material_source_digest"], D64)
        self.assertEqual(export["registration_receipt_digest"], expected_receipt(export))

    def test_export_deterministic(self):
        doc = make_registry([make_row(gen=7)])
        first = pnc.registration_export(doc, "cap.fixture-a", material_source_digest=D64)
        second = pnc.registration_export(doc, "cap.fixture-a", material_source_digest=D64)
        self.assertEqual(first, second)
        self.assertEqual(
            json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True)
        )

    def test_revoked_export_remains_revoked(self):
        doc = make_registry([make_row(gen=3, state="revoked")])
        export = pnc.registration_export(doc, "cap.fixture-a", material_source_digest=D64)
        self.assertEqual(export["registration_state"], "revoked")
        self.assertEqual(export["capability_generation"], 3)
        self.assertEqual(export["registration_receipt_digest"], expected_receipt(export))

    def test_row_tamper_changes_receipt(self):
        doc_a = make_registry([make_row(gen=7)])
        doc_b = make_registry([make_row(gen=8)])
        export_a = pnc.registration_export(doc_a, "cap.fixture-a", material_source_digest=D64)
        export_b = pnc.registration_export(doc_b, "cap.fixture-a", material_source_digest=D64)
        self.assertNotEqual(
            export_a["registration_receipt_digest"],
            export_b["registration_receipt_digest"],
        )
        self.assertEqual(export_b["registration_receipt_digest"], expected_receipt(export_b))

    def test_material_digest_tamper_changes_receipt(self):
        doc = make_registry([make_row()])
        export_a = pnc.registration_export(doc, "cap.fixture-a", material_source_digest=D64)
        export_b = pnc.registration_export(
            doc, "cap.fixture-a", material_source_digest=D64_ALT
        )
        self.assertNotEqual(
            export_a["registration_receipt_digest"],
            export_b["registration_receipt_digest"],
        )
        self.assertEqual(export_b["material_source_digest"], D64_ALT)

    def test_invalid_material_source_digest(self):
        doc = make_registry([make_row()])
        bad_digests = [
            D64.upper(),
            "g" * 64,
            "a" * 63,
            "a" * 65,
            "",
            7,
            None,
            True,
            D64 + "\n",
        ]
        for bad in bad_digests:
            self.assertCode(
                lambda bad=bad: pnc.registration_export(
                    doc, "cap.fixture-a", material_source_digest=bad
                ),
                "invalid_material_source_digest",
            )

    def test_unknown_selection_refused(self):
        doc = make_registry([make_row()])
        self.assertCode(
            lambda: pnc.registration_export(
                doc, "cap.does.not.exist", material_source_digest=D64
            ),
            "unknown_capability_selection",
        )

    def test_invalid_selection_token_refused(self):
        doc = make_registry([make_row()])
        for bad in ("", "-lead", "has space", "x" * 129, 7, None, True):
            self.assertCode(
                lambda bad=bad: pnc.registration_export(
                    doc, bad, material_source_digest=D64
                ),
                "invalid_capability_id",
            )

    def test_selection_cannot_choose_state_or_generation(self):
        signature = inspect.signature(pnc.registration_export)
        names = list(signature.parameters)
        self.assertEqual(
            names, ["registry", "capacity_capability_id", "material_source_digest"]
        )
        self.assertEqual(
            signature.parameters["material_source_digest"].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )
        for name in names:
            self.assertNotIn("state", name)
            self.assertNotIn("generation", name)

    def test_export_of_invalid_registry_refused(self):
        doc = make_registry([make_row()])
        doc["quota"] = 10
        self.assertCode(
            lambda: pnc.registration_export(
                doc, "cap.fixture-a", material_source_digest=D64
            ),
            "unexpected_registry_field",
        )

    def test_export_values_come_from_the_row(self):
        doc = make_registry([make_claude_row(gen=9)])
        export = pnc.registration_export(
            doc, "cap.fixture-b", material_source_digest=D64
        )
        self.assertEqual(export["provider"], "claude")
        self.assertEqual(export["credential_kind"], "attached_login")
        self.assertEqual(export["billing_mode"], "subscription")
        self.assertEqual(export["execution_surface"], "native_cli")
        self.assertEqual(export["registration_receipt_digest"], expected_receipt(export))


class TestErrorDiscipline(NativeCapabilityTestCase):
    def test_error_is_value_error_with_bounded_code(self):
        error = pnc.NativeCapabilityError("unknown_capability_selection")
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.code, "unknown_capability_selection")
        self.assertEqual(str(error), "unknown_capability_selection")

    def test_no_input_repr_leaks_into_error_text(self):
        sticky = "SECRET-VALUE-should-never-appear"
        doc = make_registry([make_row(cid=sticky + "-x")])
        doc["owner_program"] = sticky
        try:
            pnc.validate_registry(doc)
        except pnc.NativeCapabilityError as error:
            self.assertEqual(str(error), "invalid_owner_program")
            self.assertNotIn(sticky, str(error))
            self.assertNotIn(sticky, repr(error.code))
        else:
            self.fail("expected NativeCapabilityError")

    def test_all_error_codes_are_distinct_strings(self):
        self.assertEqual(len(pnc.ERROR_CODES), len(set(pnc.ERROR_CODES)))
        for code in pnc.ERROR_CODES:
            self.assertIsInstance(code, str)
            self.assertTrue(code)


if __name__ == "__main__":
    unittest.main()
