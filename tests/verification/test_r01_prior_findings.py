"""R01-1 — executable fix proof for every prior Data OS wave-1/2 finding.

One hermetic test per row of the R01-1 commission table (prior findings of the
#9143 / #9147 / #9152 / #9156 reviews).  Each test asserts the CORRECT behaviour
named by the seat ruling: if main conforms it is a plain PASS pinning the healed
behaviour; if main did not conform it would be a ``pytest.mark.xfail(strict=True,
reason="FINDING R01-Fn: ...")`` plus a characterization twin.  As written, all
rows are plain PASS pins — the record carries the per-row status.

Rules obeyed here:
* every name is imported from its defining module (``lib.dataos.read_contract``,
  ``lib.dataos.price_views``, ``lib.dataos.registry``, ``lib.dataos.temporal``),
  never from ``lib.dataos``;
* hermetic: in-memory rows and constructed objects only — no repository files
  are read, no wall clock, no network, no environment.

Run: PYTHONDONTWRITEBYTECODE=1 python -m pytest tests/verification/test_r01_prior_findings.py -q -p no:cacheprovider -rxs
"""

from __future__ import annotations

import itertools
from datetime import date, datetime, timezone
from fractions import Fraction

import pytest

from lib.dataos.price_views import (
    CONFIRMED,
    ActionEvent,
    ActionFamily,
    ActionRevisionSet,
    RefusalReason,
    ReinvestPolicy,
    TotalReturnPolicy,
    ViewRefusal,
    raw_view,
    sadj_view,
    split_factor,
    total_return_view,
)
from lib.dataos.read_contract import (
    CurrentEvidence,
    Dependency,
    GenerationRef,
    ReadMode,
    ReadRefusal,
    ReadRequest,
    RefusalCode,
    ViewContract,
    current,
    eligible_rows,
    reconstruct,
    resolve_revisions,
    select_generation,
    selected_input_sha256s,
)
from lib.dataos.registry import (
    ActionInputStatus,
    Registry,
    qualify_action_input,
)
from lib.dataos.temporal import TemporalProfile

#: A 40-char lowercase-hex code version, the only form the contract accepts.
CODE_VERSION = "0" * 40

#: 2026-03-06T02:00Z == 2026-03-05T21:00-05:00 (EST): 21:00 ET is still
#: exchange day 2026-03-05 for a US venue, though the UTC date is 03-06.
AS_AT_21ET = datetime(2026, 3, 6, 2, 0, tzinfo=timezone.utc)


def _contract() -> ViewContract:
    return ViewContract(
        purpose="R01-1 prior-finding fix proof",
        identity={"security_id": "S1", "listing_id": "L1"},
        field_units={"close": "USD/share"},
        adjustment_reference={"close": "raw"},
        coverage="synthetic in-memory rows only",
    )


def _reconstruct_request(cutoff: str, clock: str = "published_at") -> ReadRequest:
    return ReadRequest(ReadMode.RECONSTRUCT, _contract(), cutoff=cutoff, clock=clock)


def _current_request() -> ReadRequest:
    return ReadRequest(ReadMode.CURRENT, _contract())


def _evidence(identity_generation_id: str) -> CurrentEvidence:
    return CurrentEvidence(
        receipt_sha256s=("a" * 64,),
        identity_generation_id=identity_generation_id,
        action_revision_set_id="rs-1",
        code_version=CODE_VERSION,
    )


_G1 = GenerationRef("g1", published_at="2026-01-02T00:00:00Z",
                    ingested_at="2026-01-02T00:00:00Z")
_G2 = GenerationRef("g2", published_at="2026-01-09T00:00:00Z",
                    ingested_at="2026-01-09T00:00:00Z")


# ── T-M1: revision resolution is order-independent ───────────────────────────

def test_r01_t_m1_resolution_outcome_is_identical_for_every_permutation() -> None:
    """Key K: A(seq1,v=1) B(seq1,v=2) C(seq2,v=3) — all 6 supply orders agree.

    Prior defect (#9143): order [A,B,C] refused AMBIGUOUS_REVISION while order
    [C,A,B] returned C.  Correct: the answer depends on the SET of rows, never
    the supply order — every permutation serves the max-revision row C.
    """
    rows = [
        {"k": "K", "revision_seq": 1, "v": 1},
        {"k": "K", "revision_seq": 1, "v": 2},
        {"k": "K", "revision_seq": 2, "v": 3},
    ]
    outcomes = set()
    for perm in itertools.permutations(rows):
        try:
            served = resolve_revisions(list(perm), key_fields=("k",))
            outcomes.add(("served", tuple(r["v"] for r in served)))
        except ReadRefusal as exc:
            outcomes.add(("refused", exc.code.value))
    assert outcomes == {("served", (3,))}


# ── T-M2: one instant is one key however it is spelled ───────────────────────

def test_r01_t_m2_z_and_offset_spell_one_key_and_mixed_kinds_refuse_typed() -> None:
    """Prior defect (#9143): rev1 `...T00:00:00Z` + rev2 `...T00:00:00+00:00`
    were two keys, so both values were served.  Correct: both spellings are the
    same instant, so only rev2 (the max revision) is served; a datetime key
    mixed with a non-instant string key refuses KEY_TYPE_MISMATCH, never a raw
    TypeError.
    """
    rev1 = {"period_end": "2026-01-05T00:00:00Z", "revision_seq": 1, "v": "old"}
    rev2 = {"period_end": "2026-01-05T00:00:00+00:00", "revision_seq": 2, "v": "new"}
    served = resolve_revisions([rev1, rev2], key_fields=("period_end",))
    assert [row["v"] for row in served] == ["new"]

    mixed = [
        {"period_end": datetime(2026, 1, 5, tzinfo=timezone.utc),
         "revision_seq": 1, "v": "a"},
        {"period_end": "not-an-instant", "revision_seq": 2, "v": "b"},
    ]
    with pytest.raises(ReadRefusal) as excinfo:
        resolve_revisions(mixed, key_fields=("period_end",))
    assert excinfo.value.code is RefusalCode.KEY_TYPE_MISMATCH
    assert not isinstance(excinfo.value, TypeError)


# ── T-M3: a key with two different rows and no revision ordering refuses ─────

def test_r01_t_m3_snapshot_series_duplicate_ratios_never_both_served() -> None:
    """Prior defect (#9143): SNAPSHOT_SERIES action A1 rev1 ratio 2.0 + rev2
    ratio 0.5 were both served with `revision_resolution: "none"`.  Correct:
    never both — a typed DUPLICATE_KEY refusal.
    """
    dep = Dependency(
        name="actions",
        profile=TemporalProfile.SNAPSHOT_SERIES,
        key_fields=("action_id",),
        rows=(
            {"action_id": "A1", "ratio": 2.0, "published_at": "2026-01-05T00:00:00Z",
             "ingested_at": "2026-01-05T00:00:00Z"},
            {"action_id": "A1", "ratio": 0.5, "published_at": "2026-01-05T00:00:00Z",
             "ingested_at": "2026-01-05T00:00:00Z"},
        ),
    )
    with pytest.raises(ReadRefusal) as excinfo:
        reconstruct(_reconstruct_request("2026-01-08T00:00:00Z"), {"actions": dep},
                    required=["actions"], code_version=CODE_VERSION)
    assert excinfo.value.code is RefusalCode.DUPLICATE_KEY


# ── T-M4: a row of a non-selected generation is not served (EXCLUDE) ─────────

def test_r01_t_m4_row_of_a_non_selected_generation_is_not_served() -> None:
    """Prior defect (#9143): g1/g2 published 01-02/01-09, a g2-tagged row
    published 01-05, cutoff 01-08T13:00Z — evidence said `g1` while the g2 row
    was served.  Correct: the g2-tagged row is excluded, not served.
    """
    row = {"row_id": "r1", "generation_id": "g2", "v": 7,
           "published_at": "2026-01-05T00:00:00Z",
           "ingested_at": "2026-01-05T00:00:00Z"}
    dep = Dependency(
        name="master",
        profile=TemporalProfile.SNAPSHOT_SERIES,
        key_fields=("row_id",),
        rows=(row,),
        generations=(_G1, _G2),
    )
    result = reconstruct(_reconstruct_request("2026-01-08T13:00:00Z"),
                         {"master": dep}, required=["master"],
                         code_version=CODE_VERSION)
    assert result.evidence["dependency_generation_ids"]["master"] == "g1"
    assert result.values["master"] == ()


# ── T-M5: CURRENT serves one revision and never a superseded generation ──────

def test_r01_t_m5_current_never_serves_two_revisions_nor_a_superseded_generation() -> None:
    """Prior defect (#9143): CURRENT over A1 rev1+rev2 served both, and CURRENT
    accepted g1 although g3 supersedes g1.  Correct: CURRENT resolves rows with
    the same law as RECONSTRUCT (max revision per key) and binds only the newest
    non-superseded generation — evidence naming a superseded id refuses
    STALE_GENERATION.
    """
    dep = Dependency(
        name="actions",
        profile=TemporalProfile.REVISABLE_RELEASE,
        key_fields=("action_id",),
        rows=(
            {"action_id": "A1", "revision_seq": 1, "ratio": "2",
             "published_at": "2026-01-05T00:00:00Z",
             "ingested_at": "2026-01-05T00:00:00Z"},
            {"action_id": "A1", "revision_seq": 2, "ratio": "3",
             "published_at": "2026-01-05T00:00:00Z",
             "ingested_at": "2026-01-05T00:00:00Z"},
        ),
    )
    result = current(_current_request(), {"actions": dep},
                     evidence=_evidence("no-ledger"))
    served = result.values["actions"]
    assert len(served) == 1
    assert served[0]["revision_seq"] == 2

    g1 = GenerationRef("g1", published_at="2026-01-02T00:00:00Z",
                       ingested_at="2026-01-02T00:00:00Z")
    g3 = GenerationRef("g3", published_at="2026-01-09T00:00:00Z",
                       ingested_at="2026-01-09T00:00:00Z", supersedes="g1")
    dep_gen = Dependency(
        name="master",
        profile=TemporalProfile.SNAPSHOT_SERIES,
        key_fields=("m",),
        rows=({"m": "x", "generation_id": "g3", "v": 1,
               "published_at": "2026-01-05T00:00:00Z",
               "ingested_at": "2026-01-05T00:00:00Z"},),
        generations=(g1, g3),
    )
    fresh = current(_current_request(), {"master": dep_gen},
                    evidence=_evidence("g3"))
    assert fresh.evidence["dependency_generation_ids"]["master"] == "g3"
    with pytest.raises(ReadRefusal) as excinfo:
        current(_current_request(), {"master": dep_gen}, evidence=_evidence("g1"))
    assert excinfo.value.code is RefusalCode.STALE_GENERATION


# ── T-M6: the input fingerprint binds the selected generation ────────────────

def test_r01_t_m6_fingerprint_differs_when_the_selected_generation_differs() -> None:
    """Prior defect (#9143): two RECONSTRUCT reads selecting g1 vs g2 had the
    same `selected_input_sha256s`.  Correct: the selected generation is bound
    into the digest, so the digests differ — even for identical (empty) rows.
    """
    def _dep() -> Dependency:
        return Dependency(
            name="master",
            profile=TemporalProfile.SNAPSHOT_SERIES,
            key_fields=("m",),
            rows=(),
            generations=(_G1, _G2),
        )

    at_g1 = reconstruct(_reconstruct_request("2026-01-05T00:00:00Z"),
                        {"master": _dep()}, required=["master"],
                        code_version=CODE_VERSION)
    at_g2 = reconstruct(_reconstruct_request("2026-01-10T00:00:00Z"),
                        {"master": _dep()}, required=["master"],
                        code_version=CODE_VERSION)
    assert at_g1.evidence["dependency_generation_ids"]["master"] == "g1"
    assert at_g2.evidence["dependency_generation_ids"]["master"] == "g2"
    digests_g1 = selected_input_sha256s(at_g1)
    digests_g2 = selected_input_sha256s(at_g2)
    assert digests_g1["master"] != digests_g2["master"]


# ── T-m1: the cutoff boundary instant is inclusive ───────────────────────────

def test_r01_t_m1_row_and_generation_stamped_exactly_at_the_cutoff_are_included() -> None:
    """Prior defect (#9143): no test at exactly the cutoff.  Correct (pin):
    `known_at <= cutoff`, so a row and a generation stamped exactly AT the
    cutoff are included.
    """
    boundary = "2026-01-05T21:30:00Z"
    rows = [{"v": 1, "published_at": boundary, "ingested_at": boundary}]
    assert len(eligible_rows(rows, TemporalProfile.BARS, cutoff=boundary,
                             clock="published_at")) == 1
    gen = GenerationRef("gen-exact", published_at=boundary, ingested_at=boundary)
    assert select_generation((gen,), cutoff=boundary,
                             clock="published_at").generation_id == "gen-exact"


# ── T-m7: served rows cannot be mutated ──────────────────────────────────────

def test_r01_t_m7_served_rows_cannot_be_mutated() -> None:
    """Prior defect (#9143): `values["actions"][0]["ratio"] = 999` succeeded and
    changed a later fingerprint.  Correct (first alternative holds): returned
    rows are read-only mappings, so the mutation raises TypeError and no later
    `selected_input_sha256s` can change.
    """
    dep = Dependency(
        name="actions",
        profile=TemporalProfile.SNAPSHOT_SERIES,
        key_fields=("action_id",),
        rows=({"action_id": "A1", "ratio": 2, "published_at": "2026-01-05T00:00:00Z",
               "ingested_at": "2026-01-05T00:00:00Z"},),
    )
    result = reconstruct(_reconstruct_request("2026-01-08T00:00:00Z"),
                         {"actions": dep}, required=["actions"],
                         code_version=CODE_VERSION)
    before = selected_input_sha256s(result)
    with pytest.raises(TypeError):
        result.values["actions"][0]["ratio"] = 999
    assert selected_input_sha256s(result) == before


# ── P-M1: a duplicate event id refuses, it never multiplies ──────────────────

def test_r01_p_m1_duplicate_event_id_is_a_typed_refusal() -> None:
    """Prior defect (#9147 P02): duplicate `event_id` with no `supersedes` gave
    `split_factor` 4 instead of 2 (SADJ 100 -> 25).  Correct: DUPLICATE_EVENT_ID.
    """
    revisions = ActionRevisionSet(
        revision_set_id="rs-dup",
        events=(
            ActionEvent(event_id="E1", family=ActionFamily.FORWARD_SPLIT,
                        ex_date=date(2026, 3, 2),
                        known_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
                        source_receipt="rcpt:e1", qualification=CONFIRMED,
                        ratio=Fraction(2)),
            ActionEvent(event_id="E1", family=ActionFamily.FORWARD_SPLIT,
                        ex_date=date(2026, 3, 2),
                        known_at=datetime(2026, 3, 1, 1, tzinfo=timezone.utc),
                        source_receipt="rcpt:e1b", qualification=CONFIRMED,
                        ratio=Fraction(2)),
        ),
    )
    as_at = datetime(2026, 3, 5, tzinfo=timezone.utc)
    with pytest.raises(ViewRefusal) as excinfo:
        revisions.resolve(as_at)
    assert excinfo.value.reason is RefusalReason.DUPLICATE_EVENT_ID
    with pytest.raises(ViewRefusal) as excinfo2:
        split_factor(date(2026, 3, 1), revisions, as_at, mic="XNYS")
    assert excinfo2.value.reason is RefusalReason.DUPLICATE_EVENT_ID


# ── P-M2: same-ex-date dividend then split, EX_DATE_CLOSE -> holding return 0 ─

def test_r01_p_m2_ex_date_close_settles_after_every_same_day_event() -> None:
    """Prior defect (#9152 P04): dividend (seq 1, cps 2) then 2:1 split
    (seq 2) on one ex-date, p0=100, close 49, EX_DATE_CLOSE reinvest gave
    holding_return 1/50 (cash reinvested pre-split at the post-split close on
    the pre-split count).  Correct: purchases settle after every event of the
    ex-date, so wealth1 == wealth0 and holding_return is exactly Fraction(0).
    """
    revisions = ActionRevisionSet(
        revision_set_id="rs-m2",
        events=(
            ActionEvent(event_id="D1", family=ActionFamily.CASH_DIVIDEND,
                        ex_date=date(2026, 3, 2),
                        known_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
                        source_receipt="rcpt:d1", qualification=CONFIRMED,
                        cash_per_share=Fraction(2), cash_basis="as_declared",
                        currency="USD", sequence=1),
            ActionEvent(event_id="S1", family=ActionFamily.FORWARD_SPLIT,
                        ex_date=date(2026, 3, 2),
                        known_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
                        source_receipt="rcpt:s1", qualification=CONFIRMED,
                        ratio=Fraction(2), sequence=2),
        ),
    )
    rows = (
        {"date": date(2026, 3, 1), "close_raw": Fraction(100)},
        {"date": date(2026, 3, 2), "close_raw": Fraction(49)},
    )
    policy = TotalReturnPolicy(reinvest=ReinvestPolicy.EX_DATE_CLOSE,
                               withholding_rate=Fraction(0), currency="USD")
    view = total_return_view(rows, revisions, datetime(2026, 3, 3, tzinfo=timezone.utc),
                             policy, mic="XNYS")
    assert isinstance(view.holding_return, Fraction)
    assert view.holding_return == Fraction(0)
    assert view.wealth0 == view.wealth1 == Fraction(100)


# ── P-M3: qualify_action_input without a registry is never CONFIRMED ─────────

def test_r01_p_m3_registry_is_required_and_an_unregistered_source_is_unqualified() -> None:
    """Prior defect (#9156 P01): `qualify_action_input(...)` with no registry
    returned CONFIRMED/AS_OBSERVED for an unregistered dataset id.  Correct:
    `registry` is a REQUIRED keyword-only argument (a call without it raises
    TypeError) and an unregistered dataset id is UNQUALIFIED — never CONFIRMED.
    """
    observation = {
        "dataset_id": "not.registered.anywhere",
        "endpoint": "/corporate-actions",
        "field_convention": "as_observed_split_ratio",
        "receipt": "rcpt:abc",
        "origin": "source_record",
        "response": "events",
        "rights_limited": False,
    }
    with pytest.raises(TypeError):
        qualify_action_input(observation)
    verdict = qualify_action_input(observation, registry=Registry(()))
    assert verdict.status is ActionInputStatus.UNQUALIFIED
    assert verdict.reason == "UNREGISTERED_SOURCE"


# ── P-m1: a float price is a non-exact input, refused ────────────────────────

def test_r01_p_m1_raw_view_refuses_a_float_close() -> None:
    """Prior defect (#9147): `raw_view` with float `close_raw=100.1` produced
    an executable view.  Correct: typed NON_EXACT_INPUT refusal.
    """
    rows = [{"date": date(2026, 3, 2), "close_raw": 100.1}]
    with pytest.raises(ViewRefusal) as excinfo:
        raw_view(rows)
    assert excinfo.value.reason is RefusalReason.NON_EXACT_INPUT


# ── P-m2: a row dated after the venue-local as_at day refuses ────────────────

def test_r01_p_m2_row_after_the_as_at_day_refuses() -> None:
    """Prior defect (#9147): a row dated after `as_at` silently mixed share
    bases.  Correct: typed ROW_AFTER_AS_AT refusal against the venue-local
    as_at day.
    """
    revisions = ActionRevisionSet(revision_set_id="rs-empty", events=())
    rows = [{"date": date(2026, 3, 6), "close_raw": Fraction(101)}]
    as_at = datetime(2026, 3, 5, 23, 0, tzinfo=timezone.utc)  # 18:00 ET, day 03-05
    with pytest.raises(ViewRefusal) as excinfo:
        sadj_view(rows, revisions, as_at, mic="XNYS")
    assert excinfo.value.reason is RefusalReason.ROW_AFTER_AS_AT


# ── P-m4: zero prices / share counts refuse, never ZeroDivisionError ─────────

def test_r01_p_m4_non_positive_p0_or_q0_is_a_typed_refusal() -> None:
    """Prior defect (#9147/#9152): p0 = 0 raised ZeroDivisionError and
    q0<=0 / p0<=0 raised ValueError.  Correct: ViewRefusal NON_POSITIVE_VALUE.
    """
    revisions = ActionRevisionSet(revision_set_id="rs-empty", events=())
    policy = TotalReturnPolicy(reinvest=ReinvestPolicy.NONE,
                               withholding_rate=Fraction(0), currency="USD")
    as_at = datetime(2026, 3, 5, tzinfo=timezone.utc)
    zero_p0 = (
        {"date": date(2026, 3, 1), "close_raw": Fraction(0)},
        {"date": date(2026, 3, 2), "close_raw": Fraction(50)},
    )
    with pytest.raises(ViewRefusal) as excinfo:
        total_return_view(zero_p0, revisions, as_at, policy, mic="XNYS")
    assert excinfo.value.reason is RefusalReason.NON_POSITIVE_VALUE
    good_rows = (
        {"date": date(2026, 3, 1), "close_raw": Fraction(100)},
        {"date": date(2026, 3, 2), "close_raw": Fraction(50)},
    )
    with pytest.raises(ViewRefusal) as excinfo2:
        total_return_view(good_rows, revisions, as_at, policy, mic="XNYS", q0=0)
    assert excinfo2.value.reason is RefusalReason.NON_POSITIVE_VALUE


# ── P-m5: two rows on one date refuse, the last is not kept ──────────────────

def test_r01_p_m5_two_rows_on_one_date_refuse() -> None:
    """Prior defect (#9152): two rows on one date — the last was silently
    kept.  Correct: typed DUPLICATE_ROW_DATE refusal.
    """
    revisions = ActionRevisionSet(revision_set_id="rs-empty", events=())
    policy = TotalReturnPolicy(reinvest=ReinvestPolicy.NONE,
                               withholding_rate=Fraction(0), currency="USD")
    rows = (
        {"date": date(2026, 3, 2), "close_raw": Fraction(100)},
        {"date": date(2026, 3, 2), "close_raw": Fraction(99)},
    )
    with pytest.raises(ViewRefusal) as excinfo:
        total_return_view(rows, revisions, datetime(2026, 3, 5, tzinfo=timezone.utc),
                          policy, mic="XNYS")
    assert excinfo.value.reason is RefusalReason.DUPLICATE_ROW_DATE


# ── P-m3: the as_at day is the venue-local day, not the UTC date ─────────────

def test_r01_p_m3_2100_et_is_still_the_same_us_exchange_day() -> None:
    """Prior defect (#9147): the as_at day was the UTC date of `as_at`.
    Correct (D00.A1 / #9184 P06): the as_at day is the listing venue's
    calendar day — at 21:00 ET on 2026-03-05 (02:00Z on 03-06) the exchange day
    is still 03-05, so a 03-05 row is served and a 03-06 row (the UTC date)
    refuses ROW_AFTER_AS_AT.
    """
    revisions = ActionRevisionSet(revision_set_id="rs-empty", events=())
    view = sadj_view(
        ({"date": date(2026, 3, 5), "close_raw": Fraction(100)},),
        revisions, AS_AT_21ET, mic="XNYS")
    assert view.rows[0]["date"] == date(2026, 3, 5)
    with pytest.raises(ViewRefusal) as excinfo:
        sadj_view(({"date": date(2026, 3, 6), "close_raw": Fraction(100)},),
                  revisions, AS_AT_21ET, mic="XNYS")
    assert excinfo.value.reason is RefusalReason.ROW_AFTER_AS_AT
