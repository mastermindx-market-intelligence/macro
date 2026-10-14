"""P01 action-input qualification — ``lib/dataos/registry.py::qualify_action_input``.

One pure function decides whether a corporate-action observation may enter a
split/dividend factor at all (D00.D3: "the only admitted source of events is a
qualified original observation with its own receipt"; P01.01–P01.04).  The
counterexamples below are the discriminating cases: a provider name, an
``adjusted=true`` flag, a price jump, a cumulative vendor factor and a
current-share cash amount must each be REFUSED — with its own reason code —
no matter how qualifying the rest of the observation looks.

Two halves, both load-bearing, mirroring ``tests/test_dataos_registry.py``:

* the SYNTHETIC half proves each rule fires on exactly its defect (a function
  that refused everything would pass a "the bad inputs fail" test perfectly,
  so the CONFIRMED control and the ordering pins are as important as the
  refusals);
* the REAL half proves the committed registry still refuses its PROPOSED
  action sources — the twenty PROPOSED Tiingo contracts stay PROPOSED
  (R00.04) until their original owner produces them.

No ``data/`` read, no I/O beyond the one real-registry load (a config file,
the same one every registry test already reads).

Run: PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dataos_action_projection.py -q -p no:cacheprovider
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from lib.dataos.registry import (
    ACTION_INPUT_FIELDS,
    ActionInputStatus,
    ActionInputVerdict,
    DatasetContract,
    Registry,
    load_registry,
    qualify_action_input,
)

ROOT = Path(__file__).resolve().parent.parent


def observation(**overrides) -> dict:
    """A fully QUALIFIED as-observed observation — the CONFIRMED control — so a
    test introduces exactly one defect at a time."""
    base = {
        "dataset_id": "equity.actions.splits.testfix",
        "endpoint": "daily/AAPL/splits",
        "field_convention": "as_observed_split_ratio",
        "receipt": "mastermind.tiingo.raw_receipt.v1:rq-abc123-rawdef456",
        "origin": "source_record",
        "response": "events",
        "rights_limited": False,
    }
    base.update(overrides)
    return base


def contract(dataset_id: str, status: str = "PRODUCED") -> DatasetContract:
    """A minimal valid row, so a test can vary exactly the registry fact."""
    return DatasetContract.from_mapping(
        {
            "dataset_id": dataset_id,
            "layer": "L1",
            "status": status,
            "owner": "macro-dashboard",
            "producer": "collectors/example.py",
            "storage": "data/example/{ticker}.parquet",
            "format": "parquet",
            "grain": ["ticker", "ex_date"],
            "temporal_profile": "EVENT",
            "version": "1.0.0",
        }
    )


#: The default registry every synthetic case runs against: the fixture source
#: is registered and PRODUCED, so each rule below is reached exactly as before.
TESTFIX_REGISTRY = Registry([contract("equity.actions.splits.testfix")])


def pair(observation_map: dict, registry: Registry = TESTFIX_REGISTRY) -> tuple:
    """The (status, reason) pair — what a refusal actually branches on."""
    verdict = qualify_action_input(observation_map, registry=registry)
    return (verdict.status, verdict.reason)


# ── rule 8: the positive control ─────────────────────────────────────────────
def test_confirmed_is_reachable_and_only_via_rule_8() -> None:
    """The fully qualified as-observed observation IS confirmed — and every
    one-field defect on it lands somewhere else, so rule 8 is the ONLY door."""
    verdict = qualify_action_input(observation(), registry=TESTFIX_REGISTRY)
    assert verdict.status is ActionInputStatus.CONFIRMED
    assert verdict.reason == "AS_OBSERVED"

    mutations = {
        # (kwargs, expected (status, reason)) — one mutation per rule 1–7
        "rule1 discontinuity": (
            {"origin": "price_discontinuity"},
            (ActionInputStatus.SUSPECTED, "DISCONTINUITY_INFERRED"),
        ),
        "rule2 rights_limited": (
            {"rights_limited": True},
            (ActionInputStatus.UNCAPTURED, "RIGHTS_LIMITED"),
        ),
        "rule3 no receipt": (
            {"receipt": None},
            (ActionInputStatus.UNCAPTURED, "NO_RECEIPT"),
        ),
        "rule4 no convention": (
            {"field_convention": None},
            (ActionInputStatus.UNQUALIFIED, "UNIDENTIFIED_CONVENTION"),
        ),
        "rule5 cumulative factor": (
            {"field_convention": "cumulative_adjustment_factor"},
            (ActionInputStatus.UNQUALIFIED, "CUMULATIVE_FACTOR_NOT_AS_OBSERVED"),
        ),
        "rule6 qualified empty": (
            {"response": "empty"},
            (ActionInputStatus.NO_ACTION_IN_QUALIFIED_RESPONSE, "QUALIFIED_EMPTY"),
        ),
        "rule7 no response": (
            {"response": None},
            (ActionInputStatus.UNCAPTURED, "NO_RESPONSE"),
        ),
    }
    for label, (kwargs, expected) in mutations.items():
        assert pair(observation(**kwargs)) == expected, label


def test_a_verified_verdict_is_frozen_and_self_identifying() -> None:
    verdict = qualify_action_input(observation(), registry=TESTFIX_REGISTRY)
    assert isinstance(verdict, ActionInputVerdict)
    with pytest.raises(dataclasses.FrozenInstanceError):
        verdict.reason = "SOMETHING_ELSE"  # type: ignore[misc]
    # the verdict echoes the observation's identity and receipt, so a coverage
    # report never has to re-read the input
    assert verdict.dataset_id == "equity.actions.splits.testfix"
    assert verdict.receipt == "mastermind.tiingo.raw_receipt.v1:rq-abc123-rawdef456"
    assert qualify_action_input(
        observation(receipt=None), registry=TESTFIX_REGISTRY
    ).receipt is None
    # StrEnum (the lib.dataos.price idiom): the member IS the loggable string
    assert verdict.status == "CONFIRMED"
    assert {s.value for s in ActionInputStatus} == {
        "CONFIRMED", "SUSPECTED", "UNQUALIFIED",
        "NO_ACTION_IN_QUALIFIED_RESPONSE", "UNCAPTURED",
    }


def test_the_required_field_vocabulary_is_exactly_the_frozen_seven() -> None:
    """The observation contract itself is part of the freeze: a key added here
    without a decision is an ignored key waiting to happen."""
    assert ACTION_INPUT_FIELDS == (
        "dataset_id", "endpoint", "field_convention", "receipt",
        "origin", "response", "rights_limited",
    )


# ── P01.01: a provider label is never an event ───────────────────────────────
def test_p0101_provider_label_with_adjusted_flag_is_never_confirmed() -> None:
    """THE discriminating counterexample: `provider="tiingo", adjusted_flag=True,
    receipt=None` is not an observation of anything — it is a vendor label."""
    verdict = qualify_action_input(
        observation(receipt=None, provider="tiingo", adjusted_flag=True),
        registry=TESTFIX_REGISTRY,
    )
    assert verdict.status is not ActionInputStatus.CONFIRMED
    assert (verdict.status, verdict.reason) == (
        ActionInputStatus.UNQUALIFIED, "PROVIDER_LABEL_ONLY"
    )


def test_p0101_label_alone_and_flag_alone_each_refuse_but_bare_no_receipt_differs() -> None:
    """Either half of the vendor label triggers P01.01; with NEITHER present the
    honest answer is the different status UNCAPTURED / NO_RECEIPT."""
    assert pair(observation(receipt=None, provider="tiingo")) == (
        ActionInputStatus.UNQUALIFIED, "PROVIDER_LABEL_ONLY"
    )
    assert pair(observation(receipt=None, adjusted_flag=True)) == (
        ActionInputStatus.UNQUALIFIED, "PROVIDER_LABEL_ONLY"
    )
    assert pair(observation(receipt=None)) == (
        ActionInputStatus.UNCAPTURED, "NO_RECEIPT"
    )


def test_p0101_an_adjusted_flag_set_to_false_is_still_a_label() -> None:
    """`adjusted_flag=False` is a label that said something — the observation is
    still label-only.  "Given" means non-None, never truthy."""
    assert pair(observation(receipt=None, adjusted_flag=False)) == (
        ActionInputStatus.UNQUALIFIED, "PROVIDER_LABEL_ONLY"
    )


# ── P01.02: a price discontinuity is never a confirmed event ─────────────────
def test_p0102_discontinuity_with_a_full_receipt_is_suspected() -> None:
    """THE discriminating counterexample: even a perfect receipt attached to a
    price-jump inference authenticates the INFERENCE, not an event (D00.D3)."""
    verdict = qualify_action_input(
        observation(origin="price_discontinuity"), registry=TESTFIX_REGISTRY
    )
    assert verdict.status is not ActionInputStatus.CONFIRMED
    assert (verdict.status, verdict.reason) == (
        ActionInputStatus.SUSPECTED, "DISCONTINUITY_INFERRED"
    )


# ── P01.03: qualified empty != rights-limited != never captured ──────────────
def test_p0103_qualified_empty_rights_limited_and_no_receipt_are_three_distinct_verdicts() -> None:
    """Three refusals a naive implementation collapses into one UNCAPTURED:
    an authoritative empty is an ANSWER, a rights-limited capture is an
    unsupported family (D00.D3), and a missing receipt is silence.  Pairwise
    unequal as (status, reason) — the exact counterexample the packet pins."""
    empty = pair(observation(response="empty"))
    rights = pair(observation(rights_limited=True))
    no_receipt = pair(observation(receipt=None))
    assert empty == (ActionInputStatus.NO_ACTION_IN_QUALIFIED_RESPONSE, "QUALIFIED_EMPTY")
    assert rights == (ActionInputStatus.UNCAPTURED, "RIGHTS_LIMITED")
    assert no_receipt == (ActionInputStatus.UNCAPTURED, "NO_RECEIPT")
    assert empty != rights
    assert empty != no_receipt
    assert rights != no_receipt


# ── P01.04: derived quantities are never events ──────────────────────────────
def test_p0104_cumulative_factor_with_a_perfect_receipt_is_unqualified() -> None:
    """THE discriminating counterexample: a cumulative vendor adjustment factor
    with a flawless receipt and endpoint is still not an as-observed ratio."""
    verdict = qualify_action_input(
        observation(field_convention="cumulative_adjustment_factor"),
        registry=TESTFIX_REGISTRY,
    )
    assert verdict.status is not ActionInputStatus.CONFIRMED
    assert (verdict.status, verdict.reason) == (
        ActionInputStatus.UNQUALIFIED, "CUMULATIVE_FACTOR_NOT_AS_OBSERVED"
    )


def test_p0104_current_share_cash_and_adjusted_series_each_get_their_own_code() -> None:
    """Original cash, current-share adjusted cash and a price factor are three
    distinct facts and never substitute for one another (D00.D3, P04.02) — so
    each refusal names WHICH derived quantity was offered (P01.04)."""
    assert pair(observation(field_convention="current_share_adjusted_cash")) == (
        ActionInputStatus.UNQUALIFIED, "CURRENT_SHARE_CASH_NOT_AS_DECLARED"
    )
    assert pair(observation(field_convention="adjusted_close_only")) == (
        ActionInputStatus.UNQUALIFIED, "ADJUSTED_SERIES_NOT_AN_EVENT"
    )


def test_p0104_the_admissible_conventions_are_the_only_other_members() -> None:
    """Closing the set both ways: the two admissible conventions reach rule 8
    (here via the control's sibling), and a fourth invented convention raises
    rather than inventing a verdict."""
    assert pair(observation(field_convention="as_declared_cash_amount")) == (
        ActionInputStatus.CONFIRMED, "AS_OBSERVED"
    )
    with pytest.raises(ValueError, match="field_convention"):
        qualify_action_input(
            observation(field_convention="vendor_dividend_flag"),
            registry=TESTFIX_REGISTRY,
        )


# ── decision order (first match wins) ────────────────────────────────────────
def test_discontinuity_outranks_the_rights_limit_and_the_registry() -> None:
    """Rule 1 wins even when a later rule would also fire: the inference is the
    first thing wrong with the observation, and a not-produced source (or a
    rights limitation) cannot upgrade it to a source problem."""
    registry = Registry([contract("equity.actions.splits.testfix", "PROPOSED")])
    assert pair(observation(origin="price_discontinuity", rights_limited=True)) == (
        ActionInputStatus.SUSPECTED, "DISCONTINUITY_INFERRED"
    )
    assert pair(
        observation(origin="price_discontinuity"), registry=registry
    ) == (ActionInputStatus.SUSPECTED, "DISCONTINUITY_INFERRED")


def test_rights_limit_outranks_the_provider_label_and_the_missing_receipt() -> None:
    """Rule 2 before rule 3: a rights-limited capture is UNCAPTURED no matter
    what vendor labels ride alongside it."""
    assert pair(
        observation(rights_limited=True, receipt=None, provider="tiingo")
    ) == (ActionInputStatus.UNCAPTURED, "RIGHTS_LIMITED")


def test_unidentified_convention_outranks_a_never_admissible_convention() -> None:
    """Rule 4 before rule 5: with the endpoint missing, the observation never
    gets far enough for its convention to be judged."""
    assert pair(
        observation(endpoint=None, field_convention="cumulative_adjustment_factor")
    ) == (ActionInputStatus.UNQUALIFIED, "UNIDENTIFIED_CONVENTION")


def test_a_never_admissible_convention_outranks_a_qualified_empty() -> None:
    """Rule 5 before rule 6: a cumulative factor wearing an empty response is
    refused as the derived quantity it is, not recorded as absence."""
    assert pair(
        observation(field_convention="adjusted_close_only", response="empty")
    ) == (ActionInputStatus.UNQUALIFIED, "ADJUSTED_SERIES_NOT_AN_EVENT")


# ── the registry step (after rule 1, before rule 2) ──────────────────────────
def test_unregistered_dataset_id_is_refused() -> None:
    registry = Registry([contract("equity.actions.splits.testfix")])
    assert pair(observation(dataset_id="equity.actions.splits.ghost"), registry=registry) == (
        ActionInputStatus.UNQUALIFIED, "UNREGISTERED_SOURCE"
    )


def test_a_proposed_source_is_refused_as_not_produced() -> None:
    """R00.04 in action: the PROPOSED action sources stay refused until their
    original owner produces them — in a synthetic registry AND in the real
    committed one, where every action-named Tiingo row is still PROPOSED."""
    registry = Registry([contract("equity.actions.splits.testfix", "PROPOSED")])
    assert pair(observation(), registry=registry) == (
        ActionInputStatus.UNQUALIFIED, "SOURCE_NOT_PRODUCED"
    )
    real = load_registry()
    assert real.get("vendor.tiingo.raw.splits").status.value == "PROPOSED"
    assert pair(
        observation(dataset_id="vendor.tiingo.raw.splits"), registry=real
    ) == (ActionInputStatus.UNQUALIFIED, "SOURCE_NOT_PRODUCED")


def test_a_retired_source_is_refused_under_the_same_not_produced_code() -> None:
    """A retired store no longer exists to witness new events; refusing it under
    SOURCE_NOT_PRODUCED keeps the consumer's repair path single ('bring a live
    produced source') instead of one code per tombstone state."""
    registry = Registry([contract("equity.actions.splits.testfix", "RETIRED")])
    assert pair(observation(), registry=registry) == (
        ActionInputStatus.UNQUALIFIED, "SOURCE_NOT_PRODUCED"
    )


def test_a_produced_source_passes_through_to_rule_8() -> None:
    """The registry gates ENTRY, never confirms: a produced source still has to
    qualify on its own receipt/convention/response facts."""
    registry = Registry([contract("equity.actions.splits.testfix")])
    assert pair(observation(), registry=registry) == (
        ActionInputStatus.CONFIRMED, "AS_OBSERVED"
    )
    assert pair(observation(receipt=None), registry=registry) == (
        ActionInputStatus.UNCAPTURED, "NO_RECEIPT"
    )


def test_the_registry_argument_must_be_a_registry() -> None:
    with pytest.raises(TypeError, match="Registry"):
        qualify_action_input(observation(), registry={"equity.actions.splits.testfix": ()})


# ── structural refusals: raise, never a verdict ──────────────────────────────
@pytest.mark.parametrize(
    "broken",
    [
        lambda o: dict(o, vendor_note="adjusted=true"),   # unknown key, never ignored
        lambda o: {k: v for k, v in o.items() if k != "origin"},
        lambda o: {k: v for k, v in o.items() if k != "dataset_id"},
        lambda o: dict(o, origin="chart_gap"),
        lambda o: dict(o, response="maybe"),
        lambda o: dict(o, rights_limited="no"),
        lambda o: dict(o, rights_limited=None),
        lambda o: dict(o, field_convention="magic"),
        lambda o: dict(o, receipt=""),
        lambda o: dict(o, receipt=42),
        lambda o: dict(o, dataset_id=""),
        lambda o: dict(o, provider=""),
    ],
)
def test_structurally_impossible_observations_raise_value_error(broken) -> None:
    with pytest.raises(ValueError):
        qualify_action_input(broken(observation()), registry=TESTFIX_REGISTRY)


def test_a_non_mapping_observation_raises_type_error() -> None:
    with pytest.raises(TypeError, match="Mapping"):
        qualify_action_input(
            "provider=tiingo, adjusted=true", registry=TESTFIX_REGISTRY
        )  # type: ignore[arg-type]


# ── R02 heal (M3) — the registry is a REQUIRED argument (seat ruling D00.D3/D00.D6) ──
def test_R02_M3_registry_is_required() -> None:
    with pytest.raises(TypeError, match="registry"):
        qualify_action_input(observation(dataset_id="nonexistent.dataset"))  # type: ignore[call-arg]


def test_R02_M3_registry_none_refuses() -> None:
    with pytest.raises(TypeError, match="Registry"):
        qualify_action_input(observation(), registry=None)  # type: ignore[arg-type]


def test_R02_M3_unregistered_dataset_with_the_real_registry_is_unqualified() -> None:
    assert pair(observation(dataset_id="nonexistent.dataset"), registry=load_registry()) == (
        ActionInputStatus.UNQUALIFIED,
        "UNREGISTERED_SOURCE",
    )
