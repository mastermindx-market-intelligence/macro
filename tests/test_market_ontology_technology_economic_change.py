"""Tests for engine.market_ontology.technology_economic_change (F04 Task 5).

Every provider here is EXPLICITLY SYNTHETIC: no real issuer, product, filing or
vendor text appears anywhere; source ids, dates and digests are fabricated. The
management_outlook_comparison.v1 unit is built concurrently, so only its SEALED
OUTPUT SHAPE is fixture-built here — its internals are never mocked. The shared
``theme_graph.curation_assertion.v1`` contract (macro#7870) is present;
``SYNTHETIC_CURATION_CONTRACT`` is a test-only stand-in that lets the
composer's downstream logic run over Technology-shaped payloads, while
``test_shared_assertion_roundtrip_through_pinned_contract`` exercises the REAL
contract on a conformant fixture. Tests of the absent-contract refusal block
the module in ``sys.modules``.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import json
import re
import sys
import types
from pathlib import Path

import pytest

import engine.market_ontology.technology_economic_change as tech
from engine.market_ontology.technology_economic_change import (
    EconomicChangeDossierError,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "engine" / "market_ontology" / "technology_economic_change.py"
CONFORMANT_ASSERTION_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "technology_economic_change" / "conformant_assertion.json"
)

# --- synthetic identifiers (no real-world data) ------------------------------------

THEME = "theme:technology-ex-semis"
COMPANY = "co:us:synth-alpha"
COMPANY_SIMILAR = "co:us:synth-alpha-holdings"
BUYER = "co:us:synth-buyer"
PRODUCT_CHIP = "prod:synth-alpha-chip"
PRODUCT_SYSTEM = "prod:synth-alpha-system"
AS_OF = "2026-09-23"
CUTOFF = "2026-06-30"
GENERATION = "gen-synth-20260923"
COMPARISON_ID = "gmrmca_" + "1a2b3c4d" * 4
OWNER = {"owner_program": "gmi-technology-ex-semis", "owner_operation": None, "owner_lane": None}


def _sha(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _src(object_id: str, *, owner: str = "synthetic-owner-a", generation: str = "g1",
         selector: str | None = None, published_at: str = "2026-05-15",
         observed_at: str = "2026-05-16T08:00:00Z",
         retained_at: str = "2026-05-16T08:05:00Z") -> dict:
    # The six closed reference fields plus the source clocks the cutoff gate
    # reads (published_at, observed_at, retained_at). A source with no
    # publication clock is withheld as undatable.
    return {
        "owner": owner,
        "object_id": object_id,
        "schema": "synthetic.source/doc.v1",
        "generation": generation,
        "sha256": _sha(object_id),
        "selector": selector or f"synthetic/{object_id}#p1",
        "published_at": published_at,
        "observed_at": observed_at,
        "retained_at": retained_at,
    }


#: Technology's OWN authority vocabulary: the six bare names every object the
#: dossier composer EMITS carries (rows, cards, relationships, the root
#: ceiling) and the sealed comparison packet it checks (ECD-48). This is NOT
#: the shared curation assertion's vocabulary — see ASSERTION_FALSE_AUTHORITY
#: below; the two sets are disjoint and must never be merged or substituted.
_FALSE_AUTHORITY = {
    "rank": False, "gate": False, "size": False,
    "veto": False, "originate": False, "open_entry": False,
}

#: The shared curation assertion contract's OWN authority vocabulary: the FIVE
#: `can_*` flags, closed (additionalProperties:false), all required — as
#: inspected at 382c0b399d5c on macro#7870 (identical at 45eb37bb and
#: e2f4d4909156), and enforced by the owner's `authority_not_all_false` code
#: rule, which runs on every render BEFORE anything can be cited. The
#: intersection with the six-name block above is EMPTY: merging the two is how
#: the T8A-X1 wrong pin shipped (a six-name block inside the assertion neither
#: contract knows), so they are defined separately and never interchanged.
ASSERTION_FALSE_AUTHORITY = {
    "can_rank": False, "can_gate": False, "can_size": False,
    "can_originate": False, "can_open_entry": False,
}


def _assertion(
    *,
    predicate: str,
    statement_mode: str = "attributed",
    subject: tuple[str, str | None] = (COMPANY, "Synthetic Alpha Inc (SYNTHETIC)"),
    object_: tuple[str, str | None, str | None] = (PRODUCT_CHIP, "AI training accelerator (SYNTHETIC)", None),
    text: str = "Synthetic attributed statement (SYNTHETIC fixture text).",
    observed_on: str = "2026-05-15",
    source: dict | None = None,
    seed: str | None = None,
    vertical: str = "technology_ex_semis",
    authority: dict | None = None,
    drop: tuple[str, ...] = (),
    family_label: str | None = None,
) -> dict:
    seed = seed or f"{predicate}:{subject[0]}:{object_[0]}"
    payload = {
        "schema": "theme_graph.curation_assertion.v1",
        "curation_revision": "gmirca_" + _sha(seed)[:32],
        "review": {
            "reviewed_by": "synthetic-reviewer", "reviewed_on": "2026-06-01",
            "disposition": "accepted",
        },
        "source": source or _src("synthetic-doc-role-1"),
        "subject": {"entity_id": subject[0], "display_name": subject[1]},
        "object": {"entity_id": object_[0], "display_name": object_[1], "paid_unit": object_[2]},
        "predicate": predicate,
        "statement_mode": statement_mode,
        "scope": {"vertical": vertical},
        "observation": {"text": text},
        "temporal": {"observed_on": observed_on, "effective_from": None, "effective_to": None},
        "limitations": [{"text": "synthetic limitation"}],
        "correction": {"superseded_by": None},
        # the assertion fixture speaks the ASSERTION contract's five-flag
        # can_* vocabulary (owner-enforced all-false), NOT Technology's own
        # six-name row/dossier vocabulary
        "authority": dict(authority if authority is not None else ASSERTION_FALSE_AUTHORITY),
    }
    if family_label is not None:
        payload["industrial_context"] = {"family_label": family_label}
    for key in drop:
        payload.pop(key, None)
    return payload


ROLE = _assertion(
    predicate="product_workload_role",
    text="Synthetic role statement: attributed product workload role for compute acceleration.",
    seed="role-chip",
)
ROLE_SYSTEM = _assertion(
    predicate="product_workload_role",
    object_=(PRODUCT_SYSTEM, "Modular compute system (SYNTHETIC)", None),
    text="Synthetic role statement: attributed product workload role for systems.",
    seed="role-system",
    source=_src("synthetic-doc-role-2"),
)
BUYER_A = _assertion(
    predicate="buyer_paid_unit",
    subject=(BUYER, "Synthetic Buyer One (SYNTHETIC)"),
    object_=(PRODUCT_CHIP, "AI training accelerator (SYNTHETIC)", "per-host-month"),
    text="Synthetic buyer statement: buys the paid unit monthly per host.",
    seed="buyer-1",
    source=_src("synthetic-doc-buyer-1"),
)
COUNTER = _assertion(
    predicate="workload_usage_direction",
    statement_mode="contrary_observation",
    text="Synthetic counter-observation: some tenants report lower usage in recent months.",
    observed_on="2026-05-20",
    seed="counter-1",
    source=_src("synthetic-doc-counter-1"),
)


def _comparison(*, admitted: bool = True, limitations: list | None = None,
                authority: dict | None = None, extra: dict | None = None,
                drop: tuple[str, ...] = ()) -> dict:
    payload: dict = {
        "schema": "management_outlook_comparison.v1",
        "comparison_id": COMPARISON_ID,
        "kind": "MANAGEMENT_REVENUE_REMAINING_YEAR",
        "subject": {"entity_id": COMPANY, "product_id": PRODUCT_CHIP},
        "fiscal_partition": {"fiscal_year": 2026, "remaining_start": "2026-07-01", "remaining_end": "2026-12-31"},
        "input_roles": {"new_period": "guide", "prior_actual": "reported"},
        "input_vector": {"new_period_source": "synthetic-guide@g3", "prior_actual_source": "synthetic-actual@g2"},
        "eligibility": (
            {"eligible": True, "explanation": ""}
            if admitted
            else {"eligible": False, "explanation": "synthetic: remaining-year window not open yet"}
        ),
        "result": (
            {
                "annual_midpoint_change": "+120.5",
                "new_period_deviation": "+2.1",
                "prior_actual_revision": "-3.0",
                "earlier_remaining": "310.4",
                "later_remaining": "430.9",
                "remaining_change": "+120.5",
                "currency": "USD",
                "scale": "millions",
                "formula_revision": "rev-synth-1",
            }
            if admitted
            else None
        ),
        "limitations": limitations if limitations is not None else [
            {"text": "synthetic: single-product comparison; remaining-year window only"}
        ],
        "correction": {"open_issues": 0},
        "authority": dict(authority if authority is not None else _FALSE_AUTHORITY),
    }
    if extra:
        payload.update(extra)
    for key in drop:
        payload.pop(key, None)
    return payload


def _receipt(*, entity_id: str = COMPANY, ticker: str | None = "synth.a",
             object_id: str = "synthetic-identity-1", owner: str = "synthetic-owner-a") -> dict:
    return {
        "entity_id": entity_id,
        "binding_kind": "security",
        "display_ticker": ticker,
        "owner": owner,
        "object_id": object_id,
        "schema": "synthetic.identity/native-ref.v1",
        "generation": "g1",
        "sha256": _sha(object_id),
        "selector": f"synthetic/{object_id}#binding",
    }


def _native(*, mode: str = "first_unit_synthetic_fixture", cutoff: str = CUTOFF) -> dict:
    return {"mode": mode, "as_of": AS_OF, "cutoff": cutoff, "generation": GENERATION, **OWNER}


def _coverage(*, population_mode: str = "known_population", total: int | None = 12,
              complete: bool = True, baskets: bool = False) -> dict:
    return {
        "population_mode": population_mode,
        "known_population_total": total,
        "counts": {"included": 12, "missing": 0, "stale": 0, "rights_blocked": 0, "unresolved": 0},
        "complete_attested": complete,
        "family_labels_treated_as_baskets": baskets,
    }


def _scope(*, mode: str = "theme_first", offset: int | None = None,
           cursor: str | None = None, company_ref: str = COMPANY) -> dict:
    return {
        "scope_mode": mode,
        "theme_ref": THEME,
        "company_ref": company_ref,
        "offset": offset,
        "cursor": cursor,
    }


def _input_vector(receipts, *, comparison_id: str = COMPARISON_ID,
                  generation: str = GENERATION) -> dict:
    return {
        "engine_version": tech.ENGINE_VERSION,
        "native_context_generation": generation,
        "identity_receipts_digest": tech.identity_receipts_digest(receipts),
        "comparison_id": comparison_id,
    }


def _providers(**over) -> dict:
    receipts = over.pop("receipts", [_receipt()])
    assertions = over.pop("business_assertions", [ROLE, BUYER_A, COUNTER])
    kwargs = dict(
        scope=over.pop("scope", _scope()),
        business_assertions=assertions,
        comparison=over.pop("comparison", _comparison()),
        native_context=over.pop("native_context", _native()),
        identity_receipts=receipts,
        input_vector=over.pop("input_vector", _input_vector(receipts)),
        coverage=over.pop("coverage", _coverage()),
    )
    assert not over, f"unknown provider override keys: {sorted(over)}"
    return kwargs


def _compose(**over) -> dict:
    return tech.compose_technology_economic_change(**_providers(**over))


def _compose_happy(monkeypatch, **over) -> dict:
    monkeypatch.setattr(
        tech, "_load_shared_curation_contract", lambda: SYNTHETIC_CURATION_CONTRACT
    )
    return _compose(**over)


# --- the test-only stand-in for macro#7870's shared contract ------------------------

class _SyntheticCurationError(ValueError):
    pass


_SYNTHETIC_REQUIRED = (
    "schema", "curation_revision", "review", "source", "subject", "object",
    "predicate", "statement_mode", "scope", "observation", "temporal",
    "limitations", "correction", "authority",
)


def _synthetic_validate(payload):
    if not isinstance(payload, dict):
        raise _SyntheticCurationError("synthetic_validation_failed: payload is not a mapping")
    missing = [key for key in _SYNTHETIC_REQUIRED if key not in payload]
    if missing:
        raise _SyntheticCurationError(f"synthetic_validation_failed: missing {sorted(missing)}")
    if payload["schema"] != "theme_graph.curation_assertion.v1":
        raise _SyntheticCurationError("synthetic_validation_failed: schema mismatch")
    if not re.fullmatch(r"gmirca_[0-9a-f]{32}", str(payload["curation_revision"])):
        raise _SyntheticCurationError("synthetic_validation_failed: curation_revision grammar")
    # The REAL contract's authority vocabulary: the five can_* flags, CLOSED,
    # all literally false (as inspected at 382c0b399d5c, identical at
    # 45eb37bb/e2f4d4909156). Exact key-set equality makes the block closed, so
    # Technology's six bare names — or any other vocabulary — are REFUSED here
    # exactly as the owner's closed additionalProperties:false block refuses
    # them; checking the six names here is the oracle bug that let T8A-X1's
    # wrong pin ship unnoticed.
    assertion_authority = payload.get("authority")
    if (
        not isinstance(assertion_authority, dict)
        or set(assertion_authority) != set(ASSERTION_FALSE_AUTHORITY)
        or any(assertion_authority[flag] is not False for flag in ASSERTION_FALSE_AUTHORITY)
    ):
        raise _SyntheticCurationError(
            "synthetic_validation_failed: authority is the closed five can_* flags, all false"
        )
    for side in ("subject", "object"):
        entity_id = payload[side].get("entity_id") if isinstance(payload[side], dict) else False
        # Mirror the emitted contract: subject.entity_id is a string; object.entity_id may be null.
        if not isinstance(payload[side], dict) or "entity_id" not in payload[side] or not (
            isinstance(entity_id, str) or (side == "object" and entity_id is None)
        ):
            raise _SyntheticCurationError(f"synthetic_validation_failed: {side} shape")
    return dict(payload)


def _synthetic_curation_revision(payload):
    if not isinstance(payload, dict) or "curation_revision" not in payload:
        raise _SyntheticCurationError("synthetic_validation_failed: no curation_revision")
    return payload["curation_revision"]


SYNTHETIC_CURATION_CONTRACT = types.SimpleNamespace(
    CurationAssertionError=_SyntheticCurationError,
    validate_assertion=_synthetic_validate,
    curation_revision=_synthetic_curation_revision,
    decode_assertion=lambda value: dict(value) if isinstance(value, dict) else None,
    source_ref_for=lambda payload: f"{payload['source']['owner']}/{payload['source']['object_id']}",
)
# The synthetic stand-in is not the real contract: _assertion() builds a
# Technology-shaped payload that the real validate_assertion refuses. The
# real-contract roundtrip uses tests/fixtures/technology_economic_change/
# conformant_assertion.json (test_shared_assertion_roundtrip_through_pinned_contract).


def test_synthetic_stand_in_speaks_the_real_five_flag_can_star_vocabulary():
    # T8A-X1 oracle pin: the stand-in checks the ASSERTION contract's five
    # can_* flags (closed, all false) and refuses any other vocabulary —
    # checking Technology's six bare names here is exactly the oracle bug that
    # let the wrong six-name schema pin pass review unnoticed.
    real = _assertion(predicate="product_workload_role", seed="can-vocab-1")
    assert real["authority"] == ASSERTION_FALSE_AUTHORITY
    assert SYNTHETIC_CURATION_CONTRACT.validate_assertion(real) == real
    six_bare_names = dict(real, authority=dict(_FALSE_AUTHORITY))
    with pytest.raises(_SyntheticCurationError, match="authority"):
        SYNTHETIC_CURATION_CONTRACT.validate_assertion(six_bare_names)


# --- TR3: the shared contract --------------------------------------------------------


def test_shared_module_import_is_lazy_only():
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    top_level: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            top_level.append(node.module or "")
    assert not any("theme_graph" in name for name in top_level)


def _assigned_string_constant(tree: ast.AST, name: str) -> str:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
                break
    raise AssertionError(f"{name} is not a module-level string constant")


def _import_module_string_literals(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        label = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if label != "import_module":
            continue
        arg = node.args[0]
        # A Name is an opaque dynamic import (scripts/ci_scope_dependencies.py)
        # and smears CI scope. The target stays a literal bound to the constant.
        assert isinstance(arg, ast.Constant) and isinstance(arg.value, str), (
            "import_module target must stay a string literal equal to SHARED_CONTRACT_MODULE"
        )
        found.append(arg.value)
    return found


def _shared_contract_module_path_literals(tree: ast.AST) -> list[str]:
    """Whole-value module-path literals, not docstring mentions of the path."""
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        value = node.value
        if value.startswith("engine.") and " " not in value and "curation_assertion" in value:
            found.append(value)
    return found


def test_lazy_import_literal_equals_shared_contract_module():
    """Bind the lazy import literal to ``SHARED_CONTRACT_MODULE`` (audit N1).

    The loader keeps a string literal so CI scope can resolve the target. Nothing
    else may carry a divergent copy of that path: if the constant moves and the
    literal does not, the loader keeps importing the old name and stays
    ``shared_contract_unavailable``. ``_real_curation_module`` hardcodes the same
    literal, so it is included here and would not catch that drift on its own.
    """
    module_tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    assigned = _assigned_string_constant(module_tree, "SHARED_CONTRACT_MODULE")
    assert assigned == tech.SHARED_CONTRACT_MODULE
    helpers = _assigned_string_constant(module_tree, "SHARED_TIME_HELPERS_MODULE")
    assert helpers == tech.SHARED_TIME_HELPERS_MODULE
    assert sorted(_import_module_string_literals(module_tree)) == sorted([assigned, helpers])
    assert set(_shared_contract_module_path_literals(module_tree)) == {assigned}
    test_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    assert _import_module_string_literals(test_tree) == [assigned]
    assert set(_shared_contract_module_path_literals(test_tree)) == {assigned}


def _block_shared_contract(monkeypatch) -> None:
    """The pre-#7870 carrier state: the shared module does not import."""
    monkeypatch.setitem(sys.modules, tech.SHARED_CONTRACT_MODULE, None)


def _real_curation_module():
    return importlib.import_module("engine.theme_graph.curation_assertion")


def test_shared_contract_unavailable_on_carrier_base(monkeypatch):
    # #7870 is on this tree: the loader returns the real module.
    assert tech._load_shared_curation_contract() is _real_curation_module()
    # Without it (the pre-#7870 carrier base) the loader is typed unavailable.
    _block_shared_contract(monkeypatch)
    assert tech._load_shared_curation_contract() is None


def test_business_refused_when_shared_contract_unavailable(monkeypatch):
    # Present contract: the synthetic stand-in assertions are not valid
    # #7870 assertions, so all three are counted invalid and none renders.
    present = _compose()
    assert "rows" in present["business"]
    assert present["business"]["rows"] == []
    assert present["counter_observations"] == []
    assert present["coverage"]["assertion_counts_available"] is True
    assert present["coverage"]["counts"]["invalid_assertions"] == 3
    # Absent contract: the typed refusal, with every assertion count unknown.
    _block_shared_contract(monkeypatch)
    dossier = _compose()
    business = dossier["business"]
    assert business["refused"] is True
    assert business["reason_code"] == "shared_contract_unavailable"
    assert business["explanation"]
    assert dossier["counter_observations"] == []
    assert dossier["coverage"]["assertion_counts_available"] is False
    for key in ("unsupported_assertions", "invalid_assertions", "after_cutoff", "source_unavailable"):
        assert dossier["coverage"]["counts"][key] is None


def test_shared_assertion_roundtrip_through_pinned_contract():
    module = _real_curation_module()
    payload = json.loads(CONFORMANT_ASSERTION_PATH.read_text(encoding="utf-8"))
    validated = module.validate_assertion(payload)
    revision = module.curation_revision(validated)
    assert re.fullmatch(r"gmirca_[0-9a-f]{32}", revision)
    assert validated["curation_revision"] == revision
    encoded = module.encode_assertion(validated)
    decoded = module.decode_assertion(encoded)
    assert decoded is not None
    assert decoded["curation_revision"] == revision
    assert isinstance(module.source_ref_for(validated), str)


def test_conformant_fixture_renders_one_product_workload_role_row():
    """One schema-valid assertion becomes one product_workload_role row.

    The shared schema's predicate enum does not include the Technology
    allowlist token, so the fixture's schema predicate is the shell's
    PRODUCT_CAPABILITY and its statement_mode is ATTRIBUTED_INTERPRETATION.
    The rendered row uses the allowlist pair.
    """
    module = _real_curation_module()
    payload = json.loads(CONFORMANT_ASSERTION_PATH.read_text(encoding="utf-8"))
    validated = module.validate_assertion(payload)
    revision = module.curation_revision(validated)
    assert re.fullmatch(r"gmirca_[0-9a-f]{32}", revision)
    dossier = _compose(business_assertions=[validated])
    rows = dossier["business"]["rows"]
    assert len(rows) == 1
    assert rows[0]["predicate"] == "product_workload_role"
    assert rows[0]["statement_mode"] == "attributed"
    assert re.fullmatch(r"gmirca_[0-9a-f]{32}", rows[0]["curation_revision"])
    assert rows[0]["curation_revision"] == revision


def test_invalid_assertion_is_counted_never_rendered(monkeypatch):
    broken = _assertion(predicate="product_workload_role", seed="broken", drop=("temporal",))
    dossier = _compose_happy(monkeypatch, business_assertions=[ROLE, broken])
    assert dossier["coverage"]["counts"]["invalid_assertions"] == 1
    assert [row["predicate"] for row in dossier["business"]["rows"]] == ["product_workload_role"]


# --- real #7870 contract: admission, rendering and the cutoff clocks -----------------

_DROP = object()
_WITHHOLDING_COUNTS = (
    "invalid_assertions",
    "unsupported_assertions",
    "after_cutoff",
    "undatable_withheld",
    "source_unavailable",
)


def _conformant(source: dict | None = None, temporal: dict | None = None, *,
                scope: dict | None = None, top: dict | None = None) -> dict:
    """The conformant fixture with fields replaced (``_DROP`` removes a source
    field), restamped so the real contract still validates it."""
    payload = json.loads(CONFORMANT_ASSERTION_PATH.read_text(encoding="utf-8"))
    for key, value in (source or {}).items():
        if value is _DROP:
            payload["source"].pop(key, None)
        else:
            payload["source"][key] = value
    for section, changes in (("temporal", temporal), ("scope", scope)):
        payload[section].update(changes or {})
    payload.update(top or {})
    module = _real_curation_module()
    payload["curation_revision"] = module.curation_revision(payload)
    module.validate_assertion(payload)  # each control is a #7870-valid assertion
    return payload


def _real_compose(*payloads) -> dict:
    return _compose(business_assertions=list(payloads))


def _withheld(dossier: dict) -> dict:
    counts = dossier["coverage"]["counts"]
    return {key: counts[key] for key in _WITHHOLDING_COUNTS if counts[key]}


def _assert_rendered(dossier: dict, payload: dict) -> dict:
    """Exactly one rendered row, for this payload, and nothing withheld."""
    rows = dossier["business"]["rows"]
    assert [row["curation_revision"] for row in rows] == [payload["curation_revision"]]
    assert _withheld(dossier) == {}
    return rows[0]


def _assert_withheld(dossier: dict, count_key: str) -> None:
    assert dossier["business"]["rows"] == []
    assert dossier["counter_observations"] == []
    assert _withheld(dossier) == {count_key: 1}


def test_conformant_assertion_is_admitted_and_rendered():
    # G1: a #7870-valid assertion renders as a Technology row. Without the
    # shared-contract source projection it is counted source_unavailable.
    payload = _conformant()
    dossier = _real_compose(payload)
    row = _assert_rendered(dossier, payload)
    source = payload["source"]
    assert row["predicate"] == "product_workload_role"
    assert row["statement_mode"] == "attributed"
    assert row["subject"] == {"entity_id": COMPANY, "display_name": "Synthetic Alpha Inc (SYNTHETIC)"}
    assert row["object"]["display_name"] == "AI training accelerator (SYNTHETIC)"
    assert row["statement"] == payload["limitations"]["establishes"][0]
    assert row["source_ref"] == {
        "owner": "synthetic-owner-a",
        "object_id": "synthetic-doc-role-conformant",
        "schema": "theme_graph.curation_assertion.v1",
        "generation": "2026-05-16",
        "sha256": source["native_digest"],
        "selector": "synthetic/conformant-role#p1",
    }
    assert row["observed_on"] == "2026-05-16"
    assert dossier["source_version_vector"]["curation_revisions"] == [payload["curation_revision"]]


def test_shared_contract_source_without_a_reference_is_source_unavailable():
    # #7870 allows a null retention_ref or native_digest and a free-form
    # publisher; none of those yields the closed six-field reference.
    for change in (
        {"retention_ref": None},
        {"native_digest": None},
        {"native_digest": "not-a-sha256"},
        {"publisher": "Synthetic Owner A"},
    ):
        _assert_withheld(_real_compose(_conformant(change)), "source_unavailable")


def test_c1_c2_published_after_cutoff_withheld_whatever_the_business_window():
    late = {
        "published_at": "2026-08-01",
        "observed_at": "2026-08-02T08:00:00Z",
        "retained_at": "2026-08-02T08:05:00Z",
    }
    # C1: business_valid_from before the cutoff does not make it knowable.
    _assert_withheld(_real_compose(_conformant(late, {"business_valid_from": "2026-05-01"})), "after_cutoff")
    # C2: nor does an open business window.
    _assert_withheld(_real_compose(_conformant(late, {"business_valid_from": None})), "after_cutoff")


def test_c3_retained_after_cutoff_withheld():
    _assert_withheld(_real_compose(_conformant({"retained_at": "2026-07-01T08:05:00Z"})), "after_cutoff")


def test_c4_every_clock_on_the_cutoff_day_is_rendered():
    payload = _conformant({
        "available_at": CUTOFF + "T23:59:59Z",
        "published_at": CUTOFF,
        "observed_at": CUTOFF + "T00:00:00Z",
        "retained_at": CUTOFF + "T10:00:00+08:00",
    })
    row = _assert_rendered(_real_compose(payload), payload)
    assert row["observed_on"] == CUTOFF


def test_c5_either_day_reading_after_the_cutoff_withholds():
    # UTC day D+1, own-offset day D.
    _assert_withheld(_real_compose(_conformant({"retained_at": CUTOFF + "T23:00:00-05:00"})), "after_cutoff")
    # Own-offset day D+1, UTC day D.
    _assert_withheld(_real_compose(_conformant({"retained_at": "2026-07-01T01:00:00+08:00"})), "after_cutoff")


def test_c6_unreadable_clock_is_undatable():
    _assert_withheld(_real_compose(_conformant({"published_at": "2026-02-30"})), "undatable_withheld")
    _assert_withheld(_real_compose(_conformant({"observed_at": "2026-13-45T00:00:00Z"})), "undatable_withheld")


def test_c7_unknown_availability_is_undatable():
    _assert_withheld(_real_compose(_conformant({"available_at": "unknown"})), "undatable_withheld")


def test_c8_available_after_cutoff_withheld_though_published_before():
    _assert_withheld(_real_compose(_conformant({"available_at": "2026-07-02T00:00:00Z"})), "after_cutoff")


def test_c9_unknown_publication_without_availability_is_undatable():
    payload = _conformant({"published_at": None, "published_at_grain": "unknown"})
    _assert_withheld(_real_compose(payload), "undatable_withheld")
    # The same assertion with an availability clock before the cutoff renders.
    dated = _conformant({
        "published_at": None,
        "published_at_grain": "unknown",
        "available_at": "2026-05-15T12:00:00Z",
    })
    _assert_rendered(_real_compose(dated), dated)


def test_c10_published_before_cutoff_without_availability_is_rendered():
    payload = _conformant()
    assert "available_at" not in payload["source"]
    _assert_rendered(_real_compose(payload), payload)


def test_c11_business_window_after_cutoff_is_not_a_knowability_clock():
    payload = _conformant(temporal={"business_valid_from": "2026-08-01"})
    _assert_rendered(_real_compose(payload), payload)


def test_c12_available_before_cutoff_does_not_excuse_late_publication():
    payload = _conformant({"available_at": "2026-06-01T00:00:00Z", "published_at": "2026-07-01"})
    _assert_withheld(_real_compose(payload), "after_cutoff")


def test_c13_observed_after_cutoff_alone_withholds():
    payload = _conformant({"observed_at": "2026-07-01T00:00:00Z"})
    _assert_withheld(_real_compose(payload), "after_cutoff")


def test_cutoff_moves_admission_without_changing_the_rendered_row():
    payload = _conformant({"retained_at": "2026-07-01T08:05:00Z"})
    _assert_withheld(_real_compose(payload), "after_cutoff")
    later = _compose(business_assertions=[payload], native_context=_native(cutoff="2026-07-01"))
    row = _assert_rendered(later, payload)
    assert row["source_ref"]["generation"] == "2026-07-01"
    # observed_on is the observation day, not the retention day.
    assert row["observed_on"] == "2026-05-16"


def test_shared_contract_assertion_outside_the_technology_form_is_unsupported():
    for change in (
        {"scope": {"technology_facet": "workload_usage_direction"}},
        {"scope": {"technology_facet": None}},
        {"scope": {"canonical_theme_id": "theme:semiconductors"}},
        {"top": {"statement_mode": "CATALOG_DESCRIPTION"}},
        {"top": {"predicate": "DEPLOYMENT_TARGET"}},
    ):
        _assert_withheld(_real_compose(_conformant(**change)), "unsupported_assertions")
    # The bare vertical id is the same technology theme.
    payload = _conformant(scope={"canonical_theme_id": "technology_ex_semis"})
    _assert_rendered(_real_compose(payload), payload)


# --- review disposition (#9111 F2: only accepted dispositions render or publish) ---


def _with_disposition(disposition: str, **change) -> dict:
    review = json.loads(CONFORMANT_ASSERTION_PATH.read_text(encoding="utf-8"))["review"]
    return _conformant(top={"review": {**review, "disposition": disposition}}, **change)


def _assert_excluded_by_disposition(dossier: dict, limitation: str) -> None:
    assert dossier["business"]["rows"] == []
    assert dossier["counter_observations"] == []
    assert _withheld(dossier) == {}
    assert dossier["coverage"]["counts"]["invalid_assertions"] == 0
    assert dossier["coverage"]["limitations"] == [limitation]
    tech.validate_dossier(dossier)


def test_f2_held_disposition_is_excluded_with_held_present():
    _assert_excluded_by_disposition(_real_compose(_with_disposition("held")), "held_present")


def test_f2_rejected_disposition_is_excluded_with_rejected_present():
    _assert_excluded_by_disposition(
        _real_compose(_with_disposition("rejected")), "rejected_present"
    )


def test_f2_accepted_control_renders_with_no_limitation():
    payload = _with_disposition("accepted")
    dossier = _real_compose(payload)
    _assert_rendered(dossier, payload)
    assert dossier["coverage"]["limitations"] == []
    tech.validate_dossier(dossier)


def test_f2_only_the_accepted_row_of_a_mixed_bundle_renders():
    accepted = _with_disposition("accepted")
    held = _with_disposition("held")
    rejected = _with_disposition("rejected")
    dossier = _real_compose(rejected, accepted, held)
    _assert_rendered(dossier, accepted)
    assert dossier["coverage"]["limitations"] == ["held_present", "rejected_present"]
    entity_ids = {entity["entity_id"] for entity in dossier["identity"]["entities"]}
    assert dossier["identity"]["entities"] == _real_compose(accepted)["identity"]["entities"]
    assert COMPANY in entity_ids


def test_f2_excluded_revisions_do_not_enter_the_dossier_identity():
    accepted = _with_disposition("accepted")
    alone = _real_compose(accepted)
    mixed = _real_compose(accepted, _with_disposition("held"), _with_disposition("rejected"))
    assert mixed["dossier_id"] == alone["dossier_id"]


def test_f2_held_counter_observation_is_not_rendered(monkeypatch):
    held = copy.deepcopy(COUNTER)
    held["review"] = {**held["review"], "disposition": "held"}
    dossier = _compose_happy(monkeypatch, business_assertions=[held])
    assert dossier["counter_observations"] == []
    assert dossier["coverage"]["limitations"] == ["held_present"]
    accepted = _compose_happy(monkeypatch, business_assertions=[COUNTER])
    assert len(accepted["counter_observations"]) == 1
    assert accepted["coverage"]["limitations"] == []


def test_f2_missing_or_unknown_disposition_is_invalid_not_rendered(monkeypatch):
    # The real contract refuses both at validation; the composer still fails
    # closed if a contract hands one through.
    rows = []
    for review in (
        {"reviewed_by": "synthetic-reviewer"},
        {"reviewed_by": "synthetic-reviewer", "disposition": "pending"},
        {"reviewed_by": "synthetic-reviewer", "disposition": ["accepted"]},
        "accepted",
    ):
        payload = _assertion(predicate="product_workload_role", seed=f"disp:{review!r}")
        payload["review"] = review
        rows.append(payload)
    dossier = _compose_happy(monkeypatch, business_assertions=rows)
    assert dossier["business"]["rows"] == []
    assert dossier["coverage"]["counts"]["invalid_assertions"] == 4
    assert dossier["coverage"]["limitations"] == []


def test_f2_coverage_limitations_is_a_closed_required_contract_field():
    dossier = _real_compose(_with_disposition("held"))
    for bad in (_DROP, ["accepted_present"], ["held_present", "held_present"], "held_present"):
        broken = copy.deepcopy(dossier)
        if bad is _DROP:
            del broken["coverage"]["limitations"]
        else:
            broken["coverage"]["limitations"] = bad
        with pytest.raises(EconomicChangeDossierError, match=r"^dossier_schema_violation: coverage"):
            tech.validate_dossier(broken)


def test_shared_time_helpers_unavailable_refuses_business(monkeypatch):
    # G5: the clock helpers are imported inside the contract loader's try; a
    # missing binding module is the typed shared_contract_unavailable refusal.
    monkeypatch.setitem(sys.modules, tech.SHARED_TIME_HELPERS_MODULE, None)
    assert tech._load_shared_time_helpers() is None
    assert tech._load_shared_curation_contract() is None
    dossier = _real_compose(_conformant())
    assert dossier["business"]["refused"] is True
    assert dossier["business"]["reason_code"] == "shared_contract_unavailable"
    assert dossier["coverage"]["counts"]["undatable_withheld"] is None
    assert dossier["coverage"]["limitations"] is None


def test_shared_time_helpers_incomplete_refuses_business(monkeypatch):
    assert tech._load_shared_time_helpers() is not None
    binding = sys.modules[tech.SHARED_TIME_HELPERS_MODULE]
    for name in tech._SHARED_TIME_HELPER_NAMES:
        with monkeypatch.context() as patch:
            patch.delattr(binding, name)
            assert tech._load_shared_time_helpers() is None, name
            dossier = _real_compose(_conformant())
            assert dossier["business"]["reason_code"] == "shared_contract_unavailable", name
    assert tech._load_shared_time_helpers() is not None


# --- minimum content ------------------------------------------------------------------


def test_minimum_content_happy_path(monkeypatch):
    dossier = _compose_happy(monkeypatch)
    rows = dossier["business"]["rows"]
    predicates = {row["predicate"] for row in rows}
    # attributed product/workload role
    assert "product_workload_role" in predicates
    role_row = next(row for row in rows if row["predicate"] == "product_workload_role")
    assert role_row["statement_mode"] == "attributed"
    assert role_row["source_ref"]["sha256"] == _sha("synthetic-doc-role-1")
    # buyer / paid-unit explanation
    assert "buyer_paid_unit" in predicates
    buyer_row = next(row for row in rows if row["predicate"] == "buyer_paid_unit")
    assert buyer_row["object"]["paid_unit"] == "per-host-month"
    assert buyer_row["statement"]
    # admitted comparison
    assert dossier["comparison"]["admission"] == "admitted"
    assert dossier["comparison"]["result"]["annual_midpoint_change"] == "+120.5"
    # primary limitation
    assert dossier["comparison"]["primary_limitation"]["text"].startswith("synthetic:")
    # contrary observation, attributed
    counters = dossier["counter_observations"]
    assert len(counters) == 1
    assert counters[0]["attributed_to"]["entity_id"] == COMPANY
    assert counters[0]["source_ref"]["object_id"] == "synthetic-doc-counter-1"
    # source versions
    svv = dossier["source_version_vector"]
    assert svv["comparison_input_vector"] == _comparison()["input_vector"]
    assert len(svv["curation_revisions"]) == 3
    # validated return navigation
    assert dossier["navigation"]["theme_first"].endswith("/index.html")
    assert dossier["navigation"]["company_first"].endswith(".html")
    tech.validate_dossier(dossier)  # already ran inside compose; holds standalone too


def test_minimum_content_refusal_state_names_typed_refusals(monkeypatch):
    _block_shared_contract(monkeypatch)
    dossier = _compose()
    assert dossier["comparison"]["admission"] == "admitted"
    assert dossier["comparison"]["primary_limitation"]["text"]
    assert dossier["business"]["reason_code"] == "shared_contract_unavailable"
    assert dossier["source_version_vector"]["comparison_input_vector"] == _comparison()["input_vector"]
    assert dossier["bounds"]["pagination_supported"] is False


# --- routes and distinctness ------------------------------------------------------------


def test_theme_first_and_company_first_same_selected_vector(monkeypatch):
    theme_first = _compose_happy(monkeypatch, scope=_scope(mode="theme_first"))
    company_first = _compose_happy(monkeypatch, scope=_scope(mode="company_first"))
    assert theme_first["selected"] == company_first["selected"]
    assert theme_first["source_version_vector"] == company_first["source_version_vector"]
    assert theme_first["dossier_id"] != company_first["dossier_id"]
    assert theme_first["scope"]["scope_mode"] == "theme_first"
    assert company_first["scope"]["scope_mode"] == "company_first"
    assert theme_first["navigation"] == company_first["navigation"]


def test_multiple_products_stay_distinct(monkeypatch):
    dossier = _compose_happy(
        monkeypatch, business_assertions=[ROLE, ROLE_SYSTEM, BUYER_A]
    )
    rows = dossier["business"]["rows"]
    assert len(rows) == 3
    assert len({row["row_id"] for row in rows}) == 3
    assert dossier["selected"]["product_ids"] == [PRODUCT_CHIP, PRODUCT_SYSTEM]
    assert dossier["classification"]["issuer_pure_play_claimed"] is False


def test_whole_issuer_never_declared_pure_play(monkeypatch):
    pure_play = _assertion(predicate="issuer_pure_play", seed="pure-play")
    dossier = _compose_happy(monkeypatch, business_assertions=[ROLE, pure_play])
    assert dossier["coverage"]["counts"]["unsupported_assertions"] == 1
    assert all(row["predicate"] != "issuer_pure_play" for row in dossier["business"]["rows"])
    assert dossier["classification"]["issuer_pure_play_claimed"] is False


def test_similar_names_do_not_collapse(monkeypatch):
    similar_role = _assertion(
        predicate="product_workload_role",
        subject=(COMPANY_SIMILAR, "Synthetic Alpha Inc (SYNTHETIC)"),
        object_=(PRODUCT_CHIP, "AI training accelerator (SYNTHETIC)", None),
        seed="similar-1",
        source=_src("synthetic-doc-role-similar"),
    )
    dossier = _compose_happy(
        monkeypatch,
        business_assertions=[ROLE, similar_role],
        receipts=[_receipt()],  # binding exists only for COMPANY
    )
    entities = {e["entity_id"]: e for e in dossier["identity"]["entities"]}
    assert set(entities) == {COMPANY, COMPANY_SIMILAR}
    assert entities[COMPANY]["binding_state"] == "bound"
    # The similar-named issuer never acquires the other's binding: no fuzzy join.
    assert entities[COMPANY_SIMILAR]["security_binding"] is None
    assert entities[COMPANY_SIMILAR]["binding_state"] == "unbound"
    assert dossier["selected"]["business_entity_ids"] == [COMPANY, COMPANY_SIMILAR]


def test_source_local_configurations_stay_distinct(monkeypatch):
    local_a = _assertion(predicate="product_workload_role", seed="src-a",
                         source=_src("synthetic-doc-role-1", owner="synthetic-owner-a"))
    local_b = _assertion(predicate="product_workload_role", seed="src-b",
                         source=_src("synthetic-doc-role-1b", owner="synthetic-owner-b"))
    dossier = _compose_happy(monkeypatch, business_assertions=[local_a, local_b])
    rows = dossier["business"]["rows"]
    assert len(rows) == 2
    assert {row["source_ref"]["owner"] for row in rows} == {"synthetic-owner-a", "synthetic-owner-b"}


# --- closed allowlist --------------------------------------------------------------------


def test_narrative_mention_and_out_of_allowlist_predicates_counted(monkeypatch):
    unsupported = [
        _assertion(predicate="theme_membership", seed="m1"),
        _assertion(predicate="theme_membership", statement_mode="narrative_mention", seed="m2"),
        _assertion(predicate="procurement_volume", seed="m3"),
        _assertion(predicate="materiality_claim", seed="m4"),
        _assertion(predicate="capacity_conclusion", seed="m5"),
        _assertion(predicate="exposure_percentage", seed="m6"),
        _assertion(predicate="product_workload_role", vertical="healthcare_ex_semis", seed="m7"),
    ]
    dossier = _compose_happy(monkeypatch, business_assertions=[ROLE, *unsupported])
    assert dossier["coverage"]["counts"]["unsupported_assertions"] == 7
    assert [row["predicate"] for row in dossier["business"]["rows"]] == ["product_workload_role"]
    rendered = json.dumps(dossier)
    for predicate in ("theme_membership", "procurement_volume", "materiality_claim",
                      "capacity_conclusion", "exposure_percentage"):
        assert predicate not in rendered


def test_ecd27_to_39_positive_claims_rejected_by_first_contract(monkeypatch):
    later_capabilities = [
        _assertion(predicate="financial_ratio", seed="e27"),
        _assertion(predicate="capacity_conclusion", seed="e31"),
        _assertion(predicate="ai_exposure_percentage", seed="e33"),
        _assertion(predicate="regional_materiality", seed="e35"),
        _assertion(predicate="valuation_multiple", seed="e37"),
        _assertion(predicate="capital_allocation", seed="e39"),
    ]
    dossier = _compose_happy(monkeypatch, business_assertions=later_capabilities)
    assert dossier["business"]["rows"] == []
    assert dossier["coverage"]["counts"]["unsupported_assertions"] == 6
    # Rejection is absence: the contract carries no capability classification at
    # all, so these tests never read as "implemented and rejected".
    assert "capabilities" not in dossier
    assert "implemented_capabilities" not in dossier


def test_unnamed_counterparty_remains_unnamed(monkeypatch):
    unnamed_buyer = _assertion(
        predicate="buyer_paid_unit",
        subject=("counterparty:unnamed-buyer", None),
        text="Synthetic buyer statement: an unnamed counterparty buys the paid unit.",
        seed="unnamed-1",
    )
    dossier = _compose_happy(monkeypatch, business_assertions=[unnamed_buyer])
    row = dossier["business"]["rows"][0]
    assert row["subject"]["entity_id"] == "counterparty:unnamed-buyer"
    assert row["subject"]["display_name"] is None
    entity_ids = {e["entity_id"] for e in dossier["identity"]["entities"]}
    assert "counterparty:unnamed-buyer" not in entity_ids


def test_qualitative_only_role_renders_without_numbers(monkeypatch):
    qualitative = _assertion(
        predicate="product_workload_role",
        text="Synthetic qualitative role: described in words only, with no figures.",
        seed="qual-1",
    )
    dossier = _compose_happy(monkeypatch, business_assertions=[qualitative])
    row = dossier["business"]["rows"][0]
    assert row["statement"].startswith("Synthetic qualitative role")
    numeric_keys = {key for key in row if key.endswith(("_pct", "_share", "_value", "_amount"))}
    assert numeric_keys == set()


# --- sealed comparison ----------------------------------------------------------------------


def test_comparison_decimal_strings_verbatim(monkeypatch):
    dossier = _compose_happy(monkeypatch)
    result = dossier["comparison"]["result"]
    fixture_result = _comparison()["result"]
    for key in ("annual_midpoint_change", "new_period_deviation", "prior_actual_revision",
                "earlier_remaining", "later_remaining", "remaining_change"):
        assert result[key] == fixture_result[key]
        assert isinstance(result[key], str)
    assert re.fullmatch(r"[0-9a-f]{64}", dossier["comparison"]["correction_digest"] or "")


def test_comparison_refusal_passthrough(monkeypatch):
    dossier = _compose_happy(monkeypatch, comparison=_comparison(admitted=False))
    section = dossier["comparison"]
    assert section["admission"] == "refused"
    assert section["result"] is None
    assert section["eligibility_explanation"].startswith("synthetic:")


def test_comparison_schema_mismatch_raises():
    with pytest.raises(EconomicChangeDossierError, match=r"^comparison_schema_mismatch:"):
        _compose(comparison=_comparison(extra={"schema": "management_outlook_comparison.v2"}))


def test_comparison_kind_unsupported_raises():
    with pytest.raises(EconomicChangeDossierError, match=r"^comparison_kind_unsupported:"):
        _compose(comparison=_comparison(extra={"kind": "MANAGEMENT_REVENUE_NEXT_YEAR"}))


def test_comparison_authority_violation_raises():
    with pytest.raises(EconomicChangeDossierError, match=r"^comparison_authority_violation:"):
        _compose(comparison=_comparison(authority={**_FALSE_AUTHORITY, "gate": True}))


def test_comparison_inconsistent_refusal_without_explanation_raises():
    bad = _comparison(admitted=False)
    bad["eligibility"] = {"eligible": False, "explanation": ""}
    with pytest.raises(EconomicChangeDossierError, match=r"^comparison_inconsistent:"):
        _compose(comparison=bad)


def test_comparison_section_mismatch_raises():
    with pytest.raises(EconomicChangeDossierError, match=r"^comparison_section_mismatch:"):
        _compose(comparison=_comparison(extra={"unexpected_section": 1}))


def test_comparison_limitations_absent_refuses_section(monkeypatch):
    dossier = _compose_happy(monkeypatch, comparison=_comparison(limitations=[]))
    assert dossier["comparison"]["refused"] is True
    assert dossier["comparison"]["reason_code"] == "comparison_limitations_absent"
    # The rest of the minimum content still renders.
    assert dossier["business"]["rows"]
    assert dossier["navigation"]["theme_first"]


# --- identity / enrichment views ----------------------------------------------------------------


def test_missing_security_binding_removes_enrichment(monkeypatch):
    dossier = _compose_happy(monkeypatch, receipts=[])
    focus = next(
        e for e in dossier["identity"]["entities"] if e["entity_id"] == COMPANY
    )
    assert focus["security_binding"] is None
    assert focus["binding_state"] == "unbound"
    assert focus["display_ticker"] is None
    # Typed missingness: no enrichment-shaped key anywhere in the entity subtree.
    def _keys(value):
        if isinstance(value, dict):
            for key, inner in value.items():
                yield key
                yield from _keys(inner)
        elif isinstance(value, list):
            for item in value:
                yield from _keys(item)
    forbidden = ("price", "portfolio", "stock", "enrichment", "market")
    assert not [key for key in _keys(focus) if any(word in key for word in forbidden)]
    view = dossier["identity"]["views"]["security_enrichment_view"]
    assert view["refused"] is True
    assert view["reason_code"] == "security_binding_missing"


def test_no_fuzzy_join_on_similar_names(monkeypatch):
    # A receipt for the similarly-named issuer must not bind the focus company.
    dossier = _compose_happy(
        monkeypatch,
        scope=_scope(company_ref=COMPANY_SIMILAR),
        receipts=[_receipt(entity_id=COMPANY)],
    )
    focus = next(
        e for e in dossier["identity"]["entities"] if e["entity_id"] == COMPANY_SIMILAR
    )
    assert focus["security_binding"] is None
    assert dossier["identity"]["views"]["security_enrichment_view"]["reason_code"] == "security_binding_missing"


def test_bound_entity_still_refuses_enrichment_out_of_first_unit(monkeypatch):
    dossier = _compose_happy(monkeypatch)
    focus = next(e for e in dossier["identity"]["entities"] if e["entity_id"] == COMPANY)
    assert focus["binding_state"] == "bound"
    assert set(focus["security_binding"]) == {
        "owner", "object_id", "schema", "generation", "sha256", "selector"
    }
    view = dossier["identity"]["views"]["security_enrichment_view"]
    assert view["reason_code"] == "enrichment_out_of_first_unit_scope"


def test_identity_proof_separate_from_ticker_formatting(monkeypatch):
    good = _receipt(ticker="synth.a", object_id="synthetic-identity-1")
    ugly = _receipt(entity_id=COMPANY_SIMILAR, ticker="sy nth!", object_id="synthetic-identity-2")
    dossier = _compose_happy(
        monkeypatch,
        business_assertions=[ROLE],
        receipts=[good, ugly],
    )
    entities = {e["entity_id"]: e for e in dossier["identity"]["entities"]}
    assert entities[COMPANY]["display_ticker"] == "SYNTH.A"
    # A malformed display ticker removes the FORMATTING only; the proof (the
    # receipt itself) is a separate concern and stays bound.
    assert entities[COMPANY_SIMILAR]["display_ticker"] is None
    assert entities[COMPANY_SIMILAR]["binding_state"] == "bound"
    assert entities[COMPANY_SIMILAR]["security_binding"]["object_id"] == "synthetic-identity-2"


def test_unresolved_view_refuses_while_source_facts_visible(monkeypatch):
    dossier = _compose_happy(monkeypatch, receipts=[])
    assert dossier["identity"]["views"]["security_enrichment_view"]["refused"] is True
    assert dossier["business"]["rows"]
    assert dossier["comparison"]["admission"] == "admitted"
    assert dossier["business"]["cards"]


# --- freshness and counter-observations -----------------------------------------------------------


def test_counter_observation_requires_available_source(monkeypatch):
    sourceless = _assertion(
        predicate="workload_usage_direction",
        statement_mode="contrary_observation",
        text="Synthetic counter-observation without a usable source reference.",
        seed="counter-srcless",
        # Datable (the cutoff gate admits it) but no reference fields.
        source={
            "note": "synthetic: source fields absent",
            "published_at": "2026-05-15",
            "observed_at": "2026-05-16T08:00:00Z",
            "retained_at": "2026-05-16T08:05:00Z",
        },
    )
    dossier = _compose_happy(monkeypatch, business_assertions=[COUNTER, sourceless])
    assert dossier["coverage"]["counts"]["source_unavailable"] == 1
    assert dossier["coverage"]["counts"]["undatable_withheld"] == 0
    counters = dossier["counter_observations"]
    assert len(counters) == 1
    assert counters[0]["source_ref"]["object_id"] == "synthetic-doc-counter-1"


def test_later_filing_excluded_from_earlier_cutoff(monkeypatch):
    later = _assertion(
        predicate="workload_usage_direction",
        statement_mode="contrary_observation",
        text="Synthetic supplementary filing: dated after the selected cutoff.",
        observed_on="2026-08-01",
        seed="counter-later",
        source=_src(
            "synthetic-doc-supplementary-1",
            published_at="2026-08-01",
            observed_at="2026-08-01T09:00:00Z",
            retained_at="2026-08-01T09:05:00Z",
        ),
    )
    earlier = _compose_happy(monkeypatch, business_assertions=[later])
    assert earlier["counter_observations"] == []
    assert earlier["coverage"]["counts"]["after_cutoff"] == 1

    later_cutoff = _compose_happy(
        monkeypatch,
        business_assertions=[later],
        native_context=_native(cutoff="2026-09-01"),
    )
    assert len(later_cutoff["counter_observations"]) == 1
    assert later_cutoff["coverage"]["counts"]["after_cutoff"] == 0


def test_counter_observation_does_not_change_arithmetic(monkeypatch):
    with_counter = _compose_happy(monkeypatch, business_assertions=[ROLE, COUNTER])
    without_counter = _compose_happy(monkeypatch, business_assertions=[ROLE])
    assert with_counter["comparison"]["result"] == without_counter["comparison"]["result"]
    counter = with_counter["counter_observations"][0]
    assert counter["effect_on_comparison"] == "none_display_only"
    counter_words = json.dumps(counter).lower()
    for banned in ("forecast", "projection", "expectation", "outlook_revision"):
        assert banned not in counter_words


# --- coverage ----------------------------------------------------------------------------------------


def test_coverage_known_population(monkeypatch):
    dossier = _compose_happy(monkeypatch)
    cov = dossier["coverage"]
    assert cov["population_mode"] == "known_population"
    assert cov["known_population_total"] == 12
    assert cov["counts"]["included"] == 12
    assert cov["family_labels"] == {"are_baskets": False, "denominator": "known"}
    assert cov["completeness"]["complete_within_accepted_scope"] is True


def test_coverage_unknown_family_denominator(monkeypatch):
    dossier = _compose_happy(
        monkeypatch,
        coverage=_coverage(population_mode="unknown_scope", total=None),
    )
    cov = dossier["coverage"]
    assert cov["population_mode"] == "unknown_scope"
    assert cov["known_population_total"] is None
    assert cov["family_labels"]["denominator"] == "unknown"
    assert cov["family_labels"]["are_baskets"] is False
    # One company (or one family label) is never sector completeness.
    assert cov["completeness"]["sector_completeness_claimed"] is False


def test_family_labels_treated_as_baskets_is_refused():
    with pytest.raises(EconomicChangeDossierError, match=r"^coverage_basket_equivalence_forbidden:"):
        _compose(coverage=_coverage(baskets=True))


def test_no_partial_page_labeled_complete(monkeypatch):
    dossier = _compose_happy(monkeypatch, coverage=_coverage(complete=False))
    completeness = dossier["coverage"]["completeness"]
    assert completeness["complete_within_accepted_scope"] is False
    assert completeness["basis"] == "accepted_scope_only"
    assert completeness["sector_completeness_claimed"] is False


# --- bounds and pagination (ECD-44) -------------------------------------------------------------------


def test_pagination_supported_false_is_exposed(monkeypatch):
    dossier = _compose_happy(monkeypatch)
    assert dossier["bounds"]["pagination_supported"] is False
    assert dossier["bounds"]["truncation"] == "none_refuse_instead"
    assert dossier["bounds"]["max_cards"] == 25
    assert dossier["bounds"]["max_business_rows"] == 50
    assert dossier["bounds"]["max_relationships"] == 100


def test_offset_query_rejected():
    with pytest.raises(EconomicChangeDossierError, match=r"^pagination_not_supported:"):
        _compose(scope=_scope(offset=1))


def test_cursor_query_rejected():
    with pytest.raises(EconomicChangeDossierError, match=r"^pagination_not_supported:"):
        _compose(scope=_scope(cursor="synthetic-cursor"))


def test_business_rows_bound_refuses_without_truncation(monkeypatch):
    many = [
        _assertion(predicate="buyer_paid_unit", subject=(BUYER, "Synthetic Buyer One (SYNTHETIC)"),
                   object_=(f"prod:synth-p{i % 10}", "Synthetic product (SYNTHETIC)", "per-host-month"),
                   seed=f"rows-{i}")
        for i in range(51)
    ]
    with pytest.raises(EconomicChangeDossierError, match=r"first_unit_bounds_exceeded: business rows 51 > 50"):
        _compose_happy(monkeypatch, business_assertions=many)


def test_cards_bound_refuses_without_truncation(monkeypatch):
    many_products = [
        _assertion(predicate="product_workload_role",
                   object_=(f"prod:synth-wide-{i}", "Synthetic wide product (SYNTHETIC)", None),
                   seed=f"cards-{i}")
        for i in range(26)
    ]
    with pytest.raises(EconomicChangeDossierError, match=r"first_unit_bounds_exceeded: cards 28 > 25"):
        _compose_happy(monkeypatch, business_assertions=many_products)


def test_relationships_bound_refuses_without_truncation(monkeypatch):
    many_rels = []
    for product in range(17):
        for revision_index in range(2):
            many_rels.append(
                _assertion(predicate="product_workload_role",
                           object_=(f"prod:synth-rel-{product}", "Synthetic rel product (SYNTHETIC)", None),
                           seed=f"rels-{product}-{revision_index}")
            )
    with pytest.raises(EconomicChangeDossierError, match=r"first_unit_bounds_exceeded: relationships 102 > 100"):
        _compose_happy(monkeypatch, business_assertions=many_rels)


def test_free_text_bound_refuses(monkeypatch):
    verbose = _assertion(predicate="product_workload_role", text="x" * 2001, seed="verbose")
    with pytest.raises(EconomicChangeDossierError, match=r"^free_text_bounds_exceeded:"):
        _compose_happy(monkeypatch, business_assertions=[verbose])


def test_native_input_bytes_bound_refuses():
    # No single field may exceed its own limit; the BOUND is on the total native
    # input, so the fixture overflows it with many small, individually valid
    # receipts (~250 bytes each; 1500 of them >> 262144).
    many = [
        _receipt(object_id=f"synthetic-identity-{i:06d}", ticker=None)
        for i in range(1500)
    ]
    with pytest.raises(EconomicChangeDossierError, match=r"^native_input_bounds_exceeded:"):
        _compose(receipts=many)


def test_input_vector_binding_mismatch_on_comparison_id(monkeypatch):
    receipts = [_receipt()]
    with pytest.raises(EconomicChangeDossierError, match=r"^input_vector_binding_mismatch:"):
        _compose_happy(
            monkeypatch,
            input_vector=_input_vector(receipts, comparison_id="gmrmca_" + "ff" * 16),
        )


# --- noninterference (ECD-48) -------------------------------------------------------------------------


def _walk_authority_blocks(value):
    if isinstance(value, dict):
        if "rank" in value and "gate" in value:
            yield value
        for inner in value.values():
            yield from _walk_authority_blocks(inner)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_authority_blocks(item)


def test_every_authority_block_is_literally_false(monkeypatch):
    dossier = _compose_happy(monkeypatch)
    blocks = list(_walk_authority_blocks(dossier))
    assert len(blocks) >= 12  # root + every row/card/relationship/observation
    for block in blocks:
        assert block == _FALSE_AUTHORITY


def test_no_signal_language_anywhere_in_dossier(monkeypatch):
    dossier = _compose_happy(monkeypatch)
    rendered = json.dumps(dossier).lower()
    for banned in ("conviction", "forecast", "probab", "confidence", "signal",
                   "valuation", "price", "portfolio", "stock", "trade"):
        assert banned not in rendered, banned


def test_ordering_is_by_identifier_not_magnitude(monkeypatch):
    forward = _compose_happy(monkeypatch)
    reversed_inputs = _compose_happy(
        monkeypatch, business_assertions=[COUNTER, BUYER_A, ROLE]
    )
    assert forward["business"]["rows"] == reversed_inputs["business"]["rows"]
    assert forward["business"]["ordering"] == "identifier_lexicographic"
    rows = forward["business"]["rows"]
    assert [row["row_id"] for row in rows] == sorted(row["row_id"] for row in rows)
    cards = forward["business"]["cards"]
    assert [card["card_id"] for card in cards] == sorted(card["card_id"] for card in cards)
    rels = forward["business"]["relationships"]
    assert [rel["relationship_id"] for rel in rels] == sorted(rel["relationship_id"] for rel in rels)


def test_deterministic_dossier_id(monkeypatch):
    first = _compose_happy(monkeypatch)
    second = _compose_happy(monkeypatch)
    assert first["dossier_id"] == second["dossier_id"]
    other_cutoff = _compose_happy(monkeypatch, native_context=_native(cutoff="2026-06-29"))
    assert other_cutoff["dossier_id"] != first["dossier_id"]


def test_dataclasses_and_mappings_accepted_equivalently(monkeypatch):
    from engine.market_ontology.technology_economic_change import DossierScope

    with_mapping = _compose_happy(monkeypatch)
    with_dataclass = _compose_happy(
        monkeypatch,
        scope=DossierScope(scope_mode="theme_first", theme_ref=THEME, company_ref=COMPANY),
    )
    assert with_mapping["dossier_id"] == with_dataclass["dossier_id"]


def test_invalid_theme_ref_grammar_raises():
    with pytest.raises(EconomicChangeDossierError, match=r"^scope_shape_invalid:"):
        _compose(scope=_scope() | {"theme_ref": "not-a-theme-ref"})


# --- schema teeth ----------------------------------------------------------------------------------------


def test_schema_rejects_mutations(monkeypatch):
    dossier = _compose_happy(monkeypatch)

    mutated = json.loads(json.dumps(dossier))
    mutated["business"]["rows"][0]["unexpected"] = 1
    with pytest.raises(EconomicChangeDossierError, match=r"^dossier_schema_violation:"):
        tech.validate_dossier(mutated)

    mutated = json.loads(json.dumps(dossier))
    mutated["authority"]["rank"] = True
    with pytest.raises(EconomicChangeDossierError, match=r"^dossier_schema_violation:"):
        tech.validate_dossier(mutated)

    mutated = json.loads(json.dumps(dossier))
    mutated["identity"]["entities"][0]["market_context"] = {}
    with pytest.raises(EconomicChangeDossierError, match=r"^dossier_schema_violation:"):
        tech.validate_dossier(mutated)

    mutated = json.loads(json.dumps(dossier))
    mutated["bounds"]["pagination_supported"] = True
    with pytest.raises(EconomicChangeDossierError, match=r"^dossier_schema_violation:"):
        tech.validate_dossier(mutated)

    mutated = json.loads(json.dumps(dossier))
    mutated["definition_version"] = "1999-01-01.9"  # well-formed but NOT this revision
    with pytest.raises(EconomicChangeDossierError, match=r"^dossier_schema_violation:"):
        tech.validate_dossier(mutated)


def test_source_version_vector_is_exact(monkeypatch):
    comparison = _comparison()
    dossier = _compose_happy(monkeypatch, comparison=comparison)
    svv = dossier["source_version_vector"]
    assert svv["comparison_input_vector"] == comparison["input_vector"]
    expected = sorted(
        [ROLE["curation_revision"], BUYER_A["curation_revision"], COUNTER["curation_revision"]]
    )
    assert svv["curation_revisions"] == expected


def test_navigation_targets_are_validated_relative_paths(monkeypatch):
    dossier = _compose_happy(monkeypatch)
    for key in ("theme_first", "company_first"):
        target = dossier["navigation"][key]
        assert re.fullmatch(r"[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)*\.html", target)
        assert not target.startswith("/")
        assert "://" not in target and "//" not in target
        assert "?" not in target and "#" not in target


def test_owner_mode_and_freshness_preserved(monkeypatch):
    dossier = _compose_happy(monkeypatch)
    assert dossier["owner"]["program"] == "gmi-technology-ex-semis"
    assert dossier["mode"] == "first_unit_synthetic_fixture"
    assert dossier["freshness"] == {"as_of": AS_OF, "cutoff": CUTOFF}


# --- review pins (T5 independent review, 2026-09-24) -------------------------------


def _rels(dossier):
    return dossier["business"]["relationships"]


def test_null_object_buyer_row_keeps_counterparty_unnamed_and_invents_no_edge(monkeypatch):
    unnamed_object = _assertion(
        predicate="buyer_paid_unit",
        object_=(None, None, "seat-month (SYNTHETIC)"),
        text="Synthetic buyer statement: the paid unit is bought by an unnamed counterparty.",
        seed="nullobj-buyer-1",
    )
    dossier = _compose_happy(monkeypatch, business_assertions=[unnamed_object])
    rows = dossier["business"]["rows"]
    assert len(rows) == 1 and rows[0]["object"]["entity_id"] is None
    assert not [r for r in _rels(dossier) if r["rel_type"] == "product_has_buyer"]
    assert not [r for r in _rels(dossier) if r["from_id"] == r["to_id"]]
    assert all(r["from_id"] and r["to_id"] for r in _rels(dossier))
    assert all(card["title"] for card in dossier["business"]["cards"])


def test_null_object_workload_role_emits_no_role_edge(monkeypatch):
    unnamed_object = _assertion(
        predicate="product_workload_role",
        object_=(None, None, None),
        text="Synthetic role statement with an unnamed product side.",
        seed="nullobj-role-1",
    )
    dossier = _compose_happy(monkeypatch, business_assertions=[unnamed_object])
    assert len(dossier["business"]["rows"]) == 1
    assert not [r for r in _rels(dossier) if r["rel_type"] == "product_has_workload_role"]
    assert all(r["to_id"] for r in _rels(dossier))


def test_unnamed_side_cards_are_labelled_per_kind_and_never_merge_with_a_real_entity(monkeypatch):
    unnamed_buyer = _assertion(
        predicate="buyer_paid_unit",
        object_=(None, None, "seat-month (SYNTHETIC)"),
        text="Synthetic buyer statement: the paid unit is bought by an unnamed counterparty.",
        seed="nullobj-buyer-2",
    )
    unnamed_product = _assertion(
        predicate="product_workload_role",
        object_=(None, None, None),
        text="Synthetic role statement with an unnamed product side.",
        seed="nullobj-role-2",
    )
    literal = _assertion(
        predicate="buyer_paid_unit",
        object_=("unnamed-counterparty", "Literal Sentinel Corp (SYNTHETIC)", "seat-month (SYNTHETIC)"),
        text="Synthetic buyer statement naming a real entity whose id spells the old sentinel.",
        seed="literal-sentinel-1",
    )
    dossier = _compose_happy(monkeypatch, business_assertions=[unnamed_buyer, unnamed_product, literal])
    titles = sorted(
        card["title"] for card in dossier["business"]["cards"]
        if card["card_kind"] in {"buyer_paid_unit", "product_workload_role"}
    )
    # The real entity keeps its own card under its own display name, the unnamed sides get
    # per-kind labels, and nothing merges however an id happens to spell.
    assert titles == [
        "Literal Sentinel Corp (SYNTHETIC) — buyer / paid unit (attributed)",
        "Unnamed counterparty — buyer / paid unit (attributed)",
        "Unnamed product — workload role (attributed)",
    ]
    assert len({card["card_id"] for card in dossier["business"]["cards"]}) == len(dossier["business"]["cards"])


def test_card_display_names_never_cross_kinds(monkeypatch):
    shared_id = "counterparty:dual-role (SYNTHETIC)"
    as_product = _assertion(
        predicate="product_workload_role",
        object_=(shared_id, "Dual Role As Product (SYNTHETIC)", None),
        text="Synthetic role statement where the object is a product.",
        seed="dual-product-1",
    )
    as_buyer = _assertion(
        predicate="buyer_paid_unit",
        object_=(shared_id, "Dual Role As Buyer (SYNTHETIC)", "seat-month (SYNTHETIC)"),
        text="Synthetic buyer statement where the same id is a buyer.",
        seed="dual-buyer-1",
    )
    dossier = _compose_happy(monkeypatch, business_assertions=[as_product, as_buyer])
    titles = {card["card_kind"]: card["title"] for card in dossier["business"]["cards"]}
    assert titles["product_workload_role"] == "Dual Role As Product (SYNTHETIC) — workload role (attributed)"
    assert titles["buyer_paid_unit"] == "Dual Role As Buyer (SYNTHETIC) — buyer / paid unit (attributed)"


def test_whitespace_only_statement_is_counted_not_rendered_on_both_paths(monkeypatch):
    blank_attributed = _assertion(predicate="buyer_paid_unit", text="   ", seed="ws-attr-1")
    blank_contrary = _assertion(
        predicate="workload_usage_direction", statement_mode="contrary_observation", text=" \t ",
        seed="ws-contrary-1",
    )
    dossier = _compose_happy(monkeypatch, business_assertions=[blank_attributed, blank_contrary])
    assert dossier["business"]["rows"] == []
    assert dossier["counter_observations"] == []
    dumped = json.dumps(dossier, sort_keys=True)
    assert '"invalid_assertions": 2' in dumped
    assert '"statement": "   "' not in dumped and '"statement": " \\t "' not in dumped


def test_partially_present_shared_contract_is_typed_unavailable(monkeypatch):
    partial = types.SimpleNamespace(
        CurationAssertionError=_SyntheticCurationError, validate_assertion=_synthetic_validate
    )  # no curation_revision symbol
    # Install through the import seam so the loader's own symbol gate is exercised.
    monkeypatch.setitem(sys.modules, "engine.theme_graph.curation_assertion", partial)
    dossier = _compose(business_assertions=[_assertion(predicate="buyer_paid_unit", seed="partial-1")])
    business = dossier["business"]
    assert business["refused"] is True and business["reason_code"] == "shared_contract_unavailable"


def test_attributed_assertion_without_statement_text_is_counted_not_rendered(monkeypatch):
    blank = _assertion(predicate="buyer_paid_unit", text=None, seed="blank-1")  # type: ignore[arg-type]
    dossier = _compose_happy(monkeypatch, business_assertions=[blank])
    assert dossier["business"]["rows"] == []
    assert '"invalid_assertions": 1' in json.dumps(dossier, sort_keys=True)
