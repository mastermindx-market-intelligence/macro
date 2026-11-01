"""SPEC_U2 §2 gates 1-7: the typed change desk over two published generations.

The fixture family is the U1a producer lane's own, reused BY IMPORT and never
re-implemented: bundles are built by ``tests.test_capital_structure_state_bundle._built``
over the registration suites' event factories, so every diff below runs against
bundles the real builder produced and ``validate_state_bundle`` already accepted.
Before/after differences the compiler cannot publish through a rebuild (a
correction version increment on a published record, a second moved horizon) are
made by mutating the resulting DICT, exactly as the spec's building-inputs law
allows — never by hand-writing a bundle.

No digest, id or generation is hard-coded: every expectation is derived from the
fixture bundles, the contract helpers or the frozen vocabulary. No float
literal anywhere.
"""
from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path
from typing import Any, Mapping, NamedTuple

import pytest

from engine.capital_structure.issuer_state_contracts import (
    ContractViolation,
    sha256_of,
)
from engine.capital_structure.scenario_inputs import (
    CAPACITY_INPUTS_FILENAME,
    CapacityInputsBundle,
    FamilyEntry,
    RulesEntry,
)
from engine.capital_structure.state_changes import (
    CHANGE_KINDS,
    EVIDENCE_KEYS,
    StateChangeSet,
    changes_for_issuer,
    diff_state_generations,
)
from engine.capital_structure.rule_applicability import (
    build_rule_pack,
    load_rule_applicability_pack,
)
from scripts.build_capital_structure_state_changes import (
    build_from_disk,
)
import tests.test_capital_structure_scenario_inputs as inputs_suite
import tests.test_capital_structure_state_api as state_api_suite
from tests.test_capital_structure_registration_integration import (
    AS_OF,
    _s1_filed_amended_effective_withdrawn,
)
from tests.test_capital_structure_registration_lifecycle import _event
from tests.test_capital_structure_state_bundle import (
    ISSUER_ONE,
    ISSUER_TWO,
    _built,
)

ISSUER_ABSENT = ISSUER_TWO
#: The change set's own stamp — fixed, never a wall clock.
CHANGES_GENERATED_AT = "2026-10-19T06:00:00Z"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "capital_structure_state_changes.v1.schema.json"
)
SECOND_LIFETIME_FILE = "333-555"
NEW_LIFETIME_FILE = "333-888"


@pytest.fixture(scope="module")
def pack():
    return load_rule_applicability_pack()


@pytest.fixture(scope="module")
def pack_previous_edition(pack):
    """The same reviewed pack under a previous file edition, so only the
    bundle's rule-pack digest differs between the two generations."""
    return dataclasses.replace(pack, file_sha256=sha256_of({"edition": "u2-previous"}))


def _base_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Issuer ONE's S-1 lifecycle plus a second, independent shelf lifecycle."""
    events, edges = _s1_filed_amended_effective_withdrawn()
    second = _event(
        81,
        "S-3",
        accepted_at="2026-08-02T10:00:00Z",
        seen_at="2026-08-02T18:00:00Z",
        file_number=SECOND_LIFETIME_FILE,
    )
    events.append(second)
    return events, edges


def _s1_rows_only() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events, edges = _s1_filed_amended_effective_withdrawn()
    return events, edges


def _current_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The S-1 lifecycle, the second one gone, and a brand-new shelf whose only
    event arrives after the previous generation's newest house-knowledge clock
    (so the source observation horizon genuinely moves)."""
    events, edges = _s1_filed_amended_effective_withdrawn()
    fresh = _event(
        91,
        "S-3",
        accepted_at="2026-08-03T10:00:00Z",
        seen_at="2026-08-08T18:00:00Z",
        file_number=NEW_LIFETIME_FILE,
    )
    events.append(fresh)
    return events, edges


class _Generations(NamedTuple):
    previous: dict[str, Any]
    current: dict[str, Any]
    steady_previous: dict[str, Any]
    steady_current: dict[str, Any]


@pytest.fixture(scope="module")
def generations(pack, pack_previous_edition) -> _Generations:
    """Two real generation pairs built by the U1a fixture.

    ``previous``/``current`` differ in observations and in the source
    observation horizon.  ``steady_previous``/``steady_current`` are the SAME
    events under two rule-pack editions, so their only bundle-level difference
    is the rule-pack digest.
    """
    _, _, previous = _built(*_base_rows(), [ISSUER_ONE], rule_pack=pack)
    _, _, current = _built(*_current_rows(), [ISSUER_ONE], rule_pack=pack)
    _, _, steady_previous = _built(*_s1_rows_only(), [ISSUER_ONE], rule_pack=pack_previous_edition)
    _, _, steady_current = _built(*_s1_rows_only(), [ISSUER_ONE], rule_pack=pack)
    return _Generations(previous, current, steady_previous, steady_current)


def _inputs_record(
    *,
    bundle: dict[str, Any],
    entries: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One serialized capacity inputs bundle bound to a fixture generation.

    Imported fixture objects and the U1B suites' own entry helpers only; the
    financials family is flipped unavailable by replacing the WHOLE entry with
    an unavailable one, the way the U1b suite does.
    """
    rules_built, unknowns, _conditions, _excluded = build_rule_pack(
        load_rule_applicability_pack(), AS_OF[:10]
    )
    assert rules_built is not None
    families = entries if entries is not None else state_api_suite._fixture_entries(AS_OF)
    inputs = CapacityInputsBundle(
        as_of=AS_OF,
        generated_at=f"{AS_OF[:10]}T12:00:00Z",
        state_generation_id=bundle["generation_id"],
        source_generation_id=state_api_suite.stable_id_of_projection(),
        rules=RulesEntry(support="supported", unknowns=tuple(unknowns), record=rules_built),
        issuers={ISSUER_ONE: families},
    )
    return json.loads(json.dumps(inputs.as_record(), sort_keys=True))


def _entries_with_unavailable_financials() -> dict[str, Any]:
    entries = state_api_suite._fixture_entries(AS_OF)
    entries[inputs_suite.FINANCIALS_FAMILY] = FamilyEntry(
        family=inputs_suite.FINANCIALS_FAMILY,
        support="unavailable",
        reason_codes=("companyfacts_snapshot_unavailable",),
    )
    return entries


def _check_changeset(record: Mapping[str, Any]) -> None:
    """The ONE shared helper every change set in this file asserts through.

    Validates the record against the frozen JSON schema, requires the changes
    sorted by change_id with unique identities, and every evidence block to
    carry all five keys.
    """
    from jsonschema import Draft202012Validator, FormatChecker  # noqa: PLC0415 — lazy

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(dict(record)))
    assert not errors, [error.message for error in errors[:10]]
    changes = record["changes"]
    ids = [change["change_id"] for change in changes]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)
    for change in changes:
        assert sorted(change["evidence"]) == sorted(EVIDENCE_KEYS)
        assert change["to_generation_id"] == record["to_generation_id"]
        assert change["from_generation_id"] == record["from_generation_id"]
    assert record["baseline"] == (record["from_generation_id"] is None)
    counted = {kind: 0 for kind in CHANGE_KINDS}
    for change in changes:
        counted[change["kind"]] += 1
    assert record["counts"] == counted


# ---------------------------------------------------------------------------
# Gate 1 — baseline
# ---------------------------------------------------------------------------


def test_u2_changes_baseline_when_previous_absent(generations: _Generations) -> None:
    changeset = diff_state_generations(
        None, generations.current, generated_at=CHANGES_GENERATED_AT
    )
    assert isinstance(changeset, StateChangeSet)
    assert changeset.baseline is True
    assert changeset.changes == ()
    assert changeset.from_generation_id is None
    assert changeset.from_as_of is None
    assert changeset.to_generation_id == generations.current["generation_id"]
    assert changeset.to_as_of == generations.current["as_of"]
    _check_changeset(changeset.as_record())


# ---------------------------------------------------------------------------
# Gate 2 — new / corrected / withdrawn are three distinct kinds
# ---------------------------------------------------------------------------


def test_u2_changes_new_corrected_withdrawn_are_distinct_kinds(
    generations: _Generations,
) -> None:
    previous = generations.previous
    current = copy.deepcopy(generations.current)
    # This gate pins the three OBSERVATION kinds and nothing else, so the
    # pair's real horizon move is held back by mutation (the spec's own
    # building-inputs law); gate 4 pins the horizon record on the raw pair.
    current["horizons"]["source_observation_horizon"] = previous["horizons"][
        "source_observation_horizon"
    ]
    # The corrected observation: the retained S-1 lifecycle's published
    # amendment chain moves from correction version 1 to 2 — the one
    # before/after difference a rebuild cannot publish and the spec's own
    # building-inputs law mutates the dict for.
    family = None
    for issuer_record in current["issuers"]:
        if issuer_record["request"]["issuer_id"] != ISSUER_ONE:
            continue
        family = issuer_record["families"][0]
    assert family is not None
    corrected = next(
        record
        for record in family["records"]
        if record.get("amendment_chain")
    )
    corrected["amendment_chain"][0]["correction_version"] = 2
    retained_lifecycle_id = corrected["lifecycle_id"]

    changeset = diff_state_generations(
        previous, current, generated_at=CHANGES_GENERATED_AT
    )
    _check_changeset(changeset.as_record())
    assert changeset.from_generation_id == previous["generation_id"]
    by_kind = {}
    for change in changeset.changes:
        by_kind.setdefault(change.kind, []).append(change)
    assert sorted(by_kind) == ["corrected_observation", "new_event", "withdrawn_observation"]
    assert len(by_kind["new_event"]) == 1
    assert len(by_kind["corrected_observation"]) == 1
    assert len(by_kind["withdrawn_observation"]) == 1

    new_change = by_kind["new_event"][0]
    assert new_change.reason == "new_accession"
    assert new_change.issuer_id == ISSUER_ONE
    assert new_change.before is None
    assert new_change.after is not None
    assert NEW_LIFETIME_FILE == new_change.after["registration"]["file_number"]
    assert new_change.evidence["correction_version"] == 1

    corrected_change = by_kind["corrected_observation"][0]
    assert corrected_change.reason == "correction_version_incremented"
    assert corrected_change.before is not None and corrected_change.after is not None
    assert corrected_change.before["lifecycle_id"] == retained_lifecycle_id
    assert corrected_change.after["lifecycle_id"] == retained_lifecycle_id
    assert corrected_change.evidence["correction_version"] == 2
    assert corrected_change.before["amendment_chain"][0]["correction_version"] == 1
    assert corrected_change.after["amendment_chain"][0]["correction_version"] == 2

    withdrawn_change = by_kind["withdrawn_observation"][0]
    assert withdrawn_change.reason == "observation_absent_in_current"
    assert withdrawn_change.before is not None and withdrawn_change.after is None
    assert SECOND_LIFETIME_FILE == withdrawn_change.before["registration"]["file_number"]


# ---------------------------------------------------------------------------
# Gate 3 — support transition + rule-pack digest, and nothing else
# ---------------------------------------------------------------------------


def test_u2_changes_input_support_transition_and_rule_pack_digest(
    generations: _Generations,
) -> None:
    inputs_previous = _inputs_record(bundle=generations.steady_previous)
    inputs_current = _inputs_record(
        bundle=generations.steady_current,
        entries=_entries_with_unavailable_financials(),
    )
    changeset = diff_state_generations(
        generations.steady_previous,
        generations.steady_current,
        inputs_previous=inputs_previous,
        inputs_current=inputs_current,
        generated_at=CHANGES_GENERATED_AT,
    )
    _check_changeset(changeset.as_record())
    kinds = sorted(change.kind for change in changeset.changes)
    assert kinds == ["input_support_changed", "rule_pack_changed"], kinds

    support_change = next(
        change for change in changeset.changes if change.kind == "input_support_changed"
    )
    assert support_change.reason == "family_support_transition"
    assert support_change.issuer_id == ISSUER_ONE
    assert support_change.subject == {"family": inputs_suite.FINANCIALS_FAMILY}
    assert support_change.before == {"support": "partial"}
    assert support_change.after == {"support": "unavailable"}

    pack_change = next(
        change for change in changeset.changes if change.kind == "rule_pack_changed"
    )
    assert pack_change.reason == "rule_pack_digest_changed"
    assert pack_change.issuer_id is None
    assert pack_change.before["rule_pack_digest"] != pack_change.after["rule_pack_digest"]
    assert pack_change.after["rule_pack_digest"] == generations.steady_current["rule_pack"]["rule_pack_digest"]


# ---------------------------------------------------------------------------
# Gate 4 — one horizon_moved record per moved horizon
# ---------------------------------------------------------------------------


def test_u2_changes_horizon_moved_is_one_record_per_horizon(
    generations: _Generations,
) -> None:
    # The real pair: only the source observation horizon moved (the new shelf's
    # only event arrives later); the material filing horizon did not.
    changeset = diff_state_generations(
        generations.previous, generations.current, generated_at=CHANGES_GENERATED_AT
    )
    _check_changeset(changeset.as_record())
    moved = [change for change in changeset.changes if change.kind == "horizon_moved"]
    assert len(moved) == 1
    assert moved[0].reason == "source_observation_horizon_moved"
    assert moved[0].subject == {"horizon": "source_observation_horizon"}
    assert moved[0].issuer_id is None
    assert (
        generations.previous["horizons"]["source_observation_horizon"]
        != generations.current["horizons"]["source_observation_horizon"]
    )
    assert (
        generations.previous["horizons"]["material_filing_horizon"]
        == generations.current["horizons"]["material_filing_horizon"]
    )

    # When the second named horizon moves too, it is its own record.
    both = copy.deepcopy(generations.current)
    both["horizons"]["material_filing_horizon"] = "2026-08-02"
    changeset_both = diff_state_generations(
        generations.previous, both, generated_at=CHANGES_GENERATED_AT
    )
    _check_changeset(changeset_both.as_record())
    moved_both = [change for change in changeset_both.changes if change.kind == "horizon_moved"]
    assert [change.reason for change in moved_both] == [
        "source_observation_horizon_moved",
        "material_filing_horizon_moved",
    ] or [change.reason for change in moved_both] == [
        "material_filing_horizon_moved",
        "source_observation_horizon_moved",
    ]
    assert {change.subject["horizon"] for change in moved_both} == {
        "source_observation_horizon",
        "material_filing_horizon",
    }


# ---------------------------------------------------------------------------
# Gate 5 — a contract-version mismatch is a violation
# ---------------------------------------------------------------------------


def test_u2_changes_contract_version_mismatch_is_a_violation(
    generations: _Generations,
) -> None:
    other_version = copy.deepcopy(generations.current)
    other_version["contract_version"] = "capital-structure-state-contracts/9.9.9"
    with pytest.raises(ContractViolation) as raised:
        diff_state_generations(
            generations.previous, other_version, generated_at=CHANGES_GENERATED_AT
        )
    assert "state_changes:contract_version_mismatch" in str(raised.value)


# ---------------------------------------------------------------------------
# Gate 6 — the producer writes one artifact or nothing
# ---------------------------------------------------------------------------


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_u2_changes_producer_writes_one_artifact_or_nothing(
    generations: _Generations, tmp_path: Path
) -> None:
    root = tmp_path / "data"
    root.mkdir()
    _write_json(root / "state_bundle.json", generations.current)
    previous_path = tmp_path / "previous_state_bundle.json"
    _write_json(previous_path, generations.previous)

    summary = build_from_disk(root=root, previous=previous_path, generated_at=CHANGES_GENERATED_AT)
    assert summary["status"] == "diffed"
    ledger_path = root / "state_changes.json"
    assert ledger_path.exists()
    from jsonschema import Draft202012Validator, FormatChecker  # noqa: PLC0415 — lazy

    record = json.loads(ledger_path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(record))
    assert not errors, [error.message for error in errors[:10]]
    _check_changeset(record)
    assert record["to_generation_id"] == generations.current["generation_id"]

    # A current bundle that fails its schema: non-zero outcome, NOTHING written.
    refused_root = tmp_path / "refused"
    refused_root.mkdir()
    broken = copy.deepcopy(generations.current)
    broken["schema"] = "capital_structure.state_bundle.v9"
    _write_json(refused_root / "state_bundle.json", broken)
    with pytest.raises(ValueError) as raised:
        build_from_disk(root=refused_root, previous=previous_path, generated_at=CHANGES_GENERATED_AT)
    assert "current state bundle is invalid" in str(raised.value)
    assert not (refused_root / "state_changes.json").exists()

    # An absent current bundle is the same refusal.
    absent_root = tmp_path / "absent"
    absent_root.mkdir()
    with pytest.raises(ValueError) as absent_raised:
        build_from_disk(root=absent_root, previous=None, generated_at=CHANGES_GENERATED_AT)
    assert "current state bundle is required" in str(absent_raised.value)
    assert not (absent_root / "state_changes.json").exists()

    # An unreadable previous bundle is the stated baseline, exit-ok.
    baseline_root = tmp_path / "baseline"
    baseline_root.mkdir()
    _write_json(baseline_root / "state_bundle.json", generations.current)
    baseline_summary = build_from_disk(
        root=baseline_root,
        previous=tmp_path / "missing.json",
        generated_at=CHANGES_GENERATED_AT,
    )
    assert baseline_summary["status"] == "baseline"
    baseline_record = json.loads(
        (baseline_root / "state_changes.json").read_text(encoding="utf-8")
    )
    _check_changeset(baseline_record)
    assert baseline_record["baseline"] is True
    assert baseline_record["changes"] == []


# ---------------------------------------------------------------------------
# Gate 7 — changes_for_issuer includes the issuer-less changes
# ---------------------------------------------------------------------------


def test_u2_changes_for_issuer_includes_issuerless_changes(
    generations: _Generations,
) -> None:
    inputs_previous = _inputs_record(bundle=generations.steady_previous)
    inputs_current = _inputs_record(
        bundle=generations.steady_current,
        entries=_entries_with_unavailable_financials(),
    )
    changeset = diff_state_generations(
        generations.steady_previous,
        generations.steady_current,
        inputs_previous=inputs_previous,
        inputs_current=inputs_current,
        generated_at=CHANGES_GENERATED_AT,
    )
    own = changes_for_issuer(changeset, ISSUER_ONE)
    kinds = sorted(change.kind for change in own)
    assert kinds == ["input_support_changed", "rule_pack_changed"]
    other = changes_for_issuer(changeset, ISSUER_ABSENT)
    assert [change.kind for change in other] == ["rule_pack_changed"]
    assert changes_for_issuer(None, ISSUER_ONE) == ()
