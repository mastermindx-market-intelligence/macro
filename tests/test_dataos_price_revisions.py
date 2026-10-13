"""Action revision semantics — ``ActionRevisionSet`` as-of resolution (D00.D1/D00.D5, lane O2-P02).

A later correction can never rewrite what an earlier as-of view saw (P02.01,
P02.02); a correction that re-typings an event flips a view from answering to
refusing without ever touching the recorded originals (P02.03); unsupported
families and unconfirmed qualifications are typed refusals, never silent skips
or coercions (P02.04).  Expected values are hand-computed literal Fractions.

Run: .venv/bin/python -m pytest tests/test_dataos_price_revisions.py -q
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from fractions import Fraction

import pytest

from lib.dataos.price_views import (
    UNSUPPORTED_FAMILIES,
    ActionEvent,
    ActionFamily,
    ActionRevisionSet,
    RefusalReason,
    ReinvestPolicy,
    TotalReturnPolicy,
    ViewRefusal,
    sadj_view,
    split_factor,
    total_return_view,
)

UTC = timezone.utc
# Timeline every test below shares: the split is ANNOUNCED 2026-03-01 (known_at),
# trades ex 2026-03-10, and any correction/cancellation is recorded AFTER the
# ex-date — so an as_at of 2026-03-15 sees the event effective but the correction
# invisible, which is the discriminating as-of scenario (D00.D1).
EX_DAY = date(2026, 3, 10)
ROW_DAY = date(2026, 3, 9)  # ex_date - 1 day: inside every window below
AS_AT = datetime(2026, 6, 20, tzinfo=UTC)  # after every ex_date and known_at
ANNOUNCED = datetime(2026, 3, 1, tzinfo=UTC)
PRE_CORRECTION = datetime(2026, 3, 15, tzinfo=UTC)  # effective event, corrections invisible
POST_CORRECTION = datetime(2026, 5, 1, tzinfo=UTC)


def known(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def event(event_id: str, *, family=ActionFamily.FORWARD_SPLIT, ratio=Fraction(2),
          ex_date: date = EX_DAY, known_at: datetime, qualification: str = "CONFIRMED",
          supersedes: str | None = None, cancelled: bool = False,
          sequence: int | None = None, cash_per_share=None) -> ActionEvent:
    return ActionEvent(
        event_id=event_id,
        family=family,
        ex_date=ex_date,
        known_at=known_at,
        source_receipt=f"rcpt:{event_id}",
        qualification=qualification,
        ratio=ratio,
        cash_per_share=cash_per_share,
        supersedes=supersedes,
        cancelled=cancelled,
        sequence=sequence,
    )


# ── P02.01 — a correction is invisible until it is known ─────────────────────

def test_P02_01_as_at_before_the_correction_uses_the_original_ratio() -> None:
    original = event("A", ratio=Fraction(2), known_at=ANNOUNCED)
    correction = event("B", ratio=Fraction(3), known_at=known(2026, 4, 1), supersedes="A")
    revisions = ActionRevisionSet("corr", (original, correction))
    before = split_factor(ROW_DAY, revisions, PRE_CORRECTION)
    assert before == Fraction(2)  # the original ratio
    # ... and the view is identical to a set that never carried the correction
    assert before == split_factor(
        ROW_DAY, ActionRevisionSet("noB", (original,)), PRE_CORRECTION
    )


def test_P02_01_as_at_after_the_correction_uses_the_corrected_ratio() -> None:
    original = event("A", ratio=Fraction(2), known_at=ANNOUNCED)
    correction = event("B", ratio=Fraction(3), known_at=known(2026, 4, 1), supersedes="A")
    revisions = ActionRevisionSet("corr", (original, correction))
    assert split_factor(ROW_DAY, revisions, POST_CORRECTION) == Fraction(3)


def test_P02_01_history_keeps_both_originals_untouched() -> None:
    original = event("A", ratio=Fraction(2), known_at=ANNOUNCED)
    correction = event("B", ratio=Fraction(3), known_at=known(2026, 4, 1), supersedes="A")
    revisions = ActionRevisionSet("corr", (original, correction))
    chain = revisions.history("A")
    assert len(chain) == 2
    assert {record.event_id for record in chain} == {"A", "B"}
    assert {record.ratio for record in chain} == {Fraction(2), Fraction(3)}
    # earliest-known first, and the recorded objects are untouched
    assert chain[0].known_at <= chain[1].known_at
    assert chain[0] is original and chain[1] is correction


# ── P02.02 — a cancellation known later cannot change the earlier view ───────

def test_P02_02_cancellation_known_after_as_at_changes_nothing() -> None:
    original = event("A", ratio=Fraction(2), known_at=ANNOUNCED)
    cancellation = event(
        "C", ratio=Fraction(2), known_at=known(2026, 4, 1), supersedes="A", cancelled=True
    )
    with_cancel = ActionRevisionSet("cancel", (original, cancellation))
    without_cancel = ActionRevisionSet("noCancel", (original,))
    # the cancellation is recorded but not yet known at PRE_CORRECTION
    assert split_factor(ROW_DAY, with_cancel, PRE_CORRECTION) == Fraction(2)
    assert split_factor(ROW_DAY, with_cancel, PRE_CORRECTION) == split_factor(
        ROW_DAY, without_cancel, PRE_CORRECTION
    )


def test_P02_02_cancellation_known_before_as_at_removes_the_event() -> None:
    original = event("A", ratio=Fraction(2), known_at=ANNOUNCED)
    cancellation = event(
        "C", ratio=Fraction(2), known_at=known(2026, 4, 1), supersedes="A", cancelled=True
    )
    revisions = ActionRevisionSet("cancel", (original, cancellation))
    assert split_factor(ROW_DAY, revisions, POST_CORRECTION) == Fraction(1)  # no longer applies
    view = sadj_view([{"date": ROW_DAY, "close_raw": 100, "volume_raw": 4}], revisions, POST_CORRECTION)
    (row,) = view.rows
    assert row["close_sadj"] == Fraction(100)
    assert row["volume_sadj"] == Fraction(4)
    # the original stays recorded even after the cancellation is known
    assert {record.event_id for record in revisions.history("A")} == {"A", "C"}


# ── P02.03 — a correction may re-type an event; the originals survive ────────

def test_P02_03_family_correction_forward_split_to_spin_off_flips_the_view() -> None:
    original = event("A", family=ActionFamily.FORWARD_SPLIT, ratio=Fraction(2),
                     known_at=ANNOUNCED)
    retyped = event("B", family=ActionFamily.SPIN_OFF, ratio=None,
                    known_at=known(2026, 4, 1), supersedes="A")
    revisions = ActionRevisionSet("retype", (original, retyped))
    # pre-correction view still answers with the original split
    assert split_factor(ROW_DAY, revisions, PRE_CORRECTION) == Fraction(2)
    # post-correction view refuses — a spin-off is never coerced into a split
    with pytest.raises(ViewRefusal) as raised:
        split_factor(ROW_DAY, revisions, POST_CORRECTION)
    assert raised.value.reason is RefusalReason.UNSUPPORTED_ACTION
    assert raised.value.event_id == "B"
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": ROW_DAY, "close_raw": 100}], revisions, POST_CORRECTION)
    assert raised.value.reason is RefusalReason.UNSUPPORTED_ACTION


def test_P02_03_same_day_split_and_cash_keep_both_in_resolve_order() -> None:
    split_ev = event("S", ratio=Fraction(2), known_at=ANNOUNCED, sequence=1)
    cash_ev = event(
        "D",
        family=ActionFamily.CASH_DIVIDEND,
        ratio=None,
        cash_per_share=Fraction(1, 4),
        known_at=ANNOUNCED,
        sequence=2,
    )
    revisions = ActionRevisionSet("sameday", (cash_ev, split_ev))  # stored out of order
    resolved = revisions.resolve(AS_AT)
    assert [e.event_id for e in resolved] == ["S", "D"]  # (ex_date, sequence) order
    assert len(resolved) == 2  # both kept — never merged/normalized away
    # only the split enters the factor
    assert split_factor(ROW_DAY, revisions, AS_AT) == Fraction(2)
    # and the order tracks the sequences, not the storage order
    swapped = ActionRevisionSet(
        "sameday2",
        (
            event("S2", ratio=Fraction(2), known_at=ANNOUNCED, sequence=7),
            event("D2", family=ActionFamily.CASH_DIVIDEND, ratio=None,
                  cash_per_share=Fraction(1, 4), known_at=ANNOUNCED, sequence=3),
        ),
    )
    assert [e.event_id for e in swapped.resolve(AS_AT)] == ["D2", "S2"]


# ── P02.04 — unsupported and unconfirmed are refusals, never coercions ───────

@pytest.mark.parametrize("family", sorted(UNSUPPORTED_FAMILIES, key=lambda f: f.value))
def test_P02_04_each_known_unsupported_family_in_the_window_refuses(family) -> None:
    unsupported = event("U1", family=family, ratio=Fraction(2), known_at=ANNOUNCED)
    revisions = ActionRevisionSet("unsup", (unsupported,))
    with pytest.raises(ViewRefusal) as raised:
        split_factor(ROW_DAY, revisions, AS_AT)
    assert raised.value.reason is RefusalReason.UNSUPPORTED_ACTION
    assert raised.value.event_id == "U1"


def test_P02_04_unknown_family_string_ValueErrors_at_construction() -> None:
    with pytest.raises(ValueError):
        ActionFamily("warrant_swap")
    with pytest.raises(ValueError):
        event("U2", family="warrant_swap", known_at=ANNOUNCED)


def test_P02_04_rights_issue_carrying_a_ratio_is_still_refused_never_a_split() -> None:
    revisions = ActionRevisionSet(
        "rights",
        (event("R1", family=ActionFamily.RIGHTS_ISSUE, ratio=Fraction(2),
               known_at=ANNOUNCED),),
    )
    with pytest.raises(ViewRefusal) as raised:
        split_factor(ROW_DAY, revisions, AS_AT)
    assert raised.value.reason is RefusalReason.UNSUPPORTED_ACTION  # not factor 2


def test_P02_04_unconfirmed_split_in_the_window_refuses_NOT_CONFIRMED() -> None:
    suspected = event("S1", ratio=Fraction(2), known_at=ANNOUNCED,
                      qualification="SUSPECTED")
    revisions = ActionRevisionSet("suspect", (suspected,))
    with pytest.raises(ViewRefusal) as raised:
        split_factor(ROW_DAY, revisions, AS_AT)
    assert raised.value.reason is RefusalReason.NOT_CONFIRMED
    assert raised.value.event_id == "S1"
    # ... but the same event OUTSIDE the window never blocks the view
    assert split_factor(EX_DAY, revisions, AS_AT) == Fraction(1)


def test_P02_04_two_eligible_records_superseding_the_same_id_is_AMBIGUOUS_REVISION() -> None:
    original = event("A", ratio=Fraction(2), known_at=ANNOUNCED)
    first = event("B1", ratio=Fraction(3), known_at=known(2026, 4, 1), supersedes="A")
    second = event("B2", ratio=Fraction(5), known_at=known(2026, 4, 5), supersedes="A")
    revisions = ActionRevisionSet("ambig", (original, first, second))
    with pytest.raises(ViewRefusal) as raised:
        revisions.resolve(POST_CORRECTION)
    assert raised.value.reason is RefusalReason.AMBIGUOUS_REVISION
    assert raised.value.event_id == "A"
    # before either correction is known the view still answers
    assert split_factor(ROW_DAY, revisions, PRE_CORRECTION) == Fraction(2)


def test_P02_04_supersedes_naming_an_absent_id_is_NO_ELIGIBLE_REVISION() -> None:
    dangling = event("B", ratio=Fraction(3), known_at=known(2026, 4, 1), supersedes="ghost")
    revisions = ActionRevisionSet("dangling", (dangling,))
    with pytest.raises(ViewRefusal) as raised:
        revisions.resolve(POST_CORRECTION)
    assert raised.value.reason is RefusalReason.NO_ELIGIBLE_REVISION
    assert raised.value.event_id == "B"


# ═════════════════════════════════════════════════════════════════════════════
# Lane O2-P04 — the house TOTAL_RETURN view honours the same as-of law: a cash
# correction or cancellation known after `as_at` leaves the earlier view's cash
# untouched; known before, it moves it; the original observation stays recorded
# in history() either way (P02.01/P02.02 applied to cash).  Literals by hand:
# t0 2026-03-09 close 100, cash ex 2026-03-10, t1 2026-03-11 close 98.
# ═════════════════════════════════════════════════════════════════════════════

TR_ROWS = [
    {"date": date(2026, 3, 9), "close_raw": 100},   # ROW_DAY == t0
    {"date": date(2026, 3, 11), "close_raw": 98},   # t1
]
TR_POLICY = TotalReturnPolicy(ReinvestPolicy.NONE, Fraction(0), "USD")


def cash_event(
    event_id: str,
    per_share,
    *,
    known_at: datetime,
    ex_date: date = EX_DAY,
    supersedes: str | None = None,
    cancelled: bool = False,
) -> ActionEvent:
    """A CONFIRMED as-declared USD cash dividend (the local `event()` helper
    fixes family=split, so the cash tests build their own records)."""
    return ActionEvent(
        event_id=event_id,
        family=ActionFamily.CASH_DIVIDEND,
        ex_date=ex_date,
        known_at=known_at,
        source_receipt=f"rcpt:{event_id}",
        qualification="CONFIRMED",
        ratio=None,
        cash_per_share=per_share,
        cash_basis="as_declared",
        currency="USD",
        supersedes=supersedes,
        cancelled=cancelled,
    )


def test_O2_P04_cash_correction_known_after_as_at_leaves_cash_at_2() -> None:
    original = cash_event("D", Fraction(2), known_at=ANNOUNCED)
    correction = cash_event("D2", Fraction(3), known_at=known(2026, 4, 1), supersedes="D")
    revisions = ActionRevisionSet("trcorr", (original, correction))
    # at PRE_CORRECTION (2026-03-15) the correction is invisible: cash stays 2
    before = total_return_view(TR_ROWS, revisions, PRE_CORRECTION, TR_POLICY)
    assert before.cash == Fraction(2)
    assert before.wealth1 == Fraction(100)  # 1*98 + 2
    assert before.holding_return == Fraction(0)
    assert before.events_applied == (("D", ActionFamily.CASH_DIVIDEND, Fraction(1)),)
    # once known (POST_CORRECTION, 2026-05-01) the corrected amount 3 applies
    after = total_return_view(TR_ROWS, revisions, POST_CORRECTION, TR_POLICY)
    assert after.cash == Fraction(3)
    assert after.wealth1 == Fraction(101)  # 1*98 + 3
    assert after.holding_return == Fraction(1, 100)
    assert after.events_applied == (("D2", ActionFamily.CASH_DIVIDEND, Fraction(1)),)


def test_O2_P04_cash_cancellation_known_before_as_at_removes_the_cash() -> None:
    original = cash_event("D", Fraction(2), known_at=ANNOUNCED)
    cancellation = cash_event(
        "D3", Fraction(2), known_at=known(2026, 4, 1), supersedes="D", cancelled=True
    )
    revisions = ActionRevisionSet("trcancel", (original, cancellation))
    # before the cancellation is known, the cash is still there
    before = total_return_view(TR_ROWS, revisions, PRE_CORRECTION, TR_POLICY)
    assert before.cash == Fraction(2)
    assert before.holding_return == Fraction(0)
    # known before POST_CORRECTION: the event is gone, the view is pure price
    after = total_return_view(TR_ROWS, revisions, POST_CORRECTION, TR_POLICY)
    assert after.cash == Fraction(0)
    assert after.q1 == Fraction(1)
    assert after.wealth1 == Fraction(98)
    assert after.holding_return == Fraction(-1, 50)  # == raw_price_return
    assert after.events_applied == ()
    # the original observation remains recorded, untouched, in history()
    assert {record.event_id for record in revisions.history("D")} == {"D", "D3"}
    assert revisions.history("D")[0] is original


# ── R02 heal (M1) — one event id names exactly one record ──────────────────
def test_R02_M1_duplicate_event_id_refuses_in_split_factor() -> None:
    revisions = ActionRevisionSet(
        "dup", (event("s1", known_at=ANNOUNCED), event("s1", known_at=ANNOUNCED))
    )
    with pytest.raises(ViewRefusal) as raised:
        split_factor(ROW_DAY, revisions, AS_AT)
    assert raised.value.reason is RefusalReason.DUPLICATE_EVENT_ID
    assert raised.value.event_id == "s1"


def test_R02_M1_a_correction_under_a_new_id_still_resolves() -> None:
    original = event("s1", ratio=Fraction(2), known_at=ANNOUNCED)
    correction = event("s1-c1", ratio=Fraction(3), known_at=known(2026, 4, 1), supersedes="s1")
    revisions = ActionRevisionSet("corr-new-id", (original, correction))
    assert split_factor(ROW_DAY, revisions, PRE_CORRECTION) == Fraction(2)
    assert split_factor(ROW_DAY, revisions, POST_CORRECTION) == Fraction(3)
    assert split_factor(ROW_DAY, revisions, AS_AT) == Fraction(3)


# ── P05 — correction-aware retained views (O3-P05) ────────────────────────────
#
# Witness timeline (synthetic, local to this suite).  BARS: five sessions
# 2026-03-02..03-06 published as generation G1 on 2026-03-07, then corrected as
# G2 on 2026-03-25 (supersedes G1) with ONLY the 2026-03-02 close_raw moved
# 100 -> 101.  ACTIONS (EVENT profile): S1, a 2:1 forward split ex 2026-03-10
# published 2026-03-01, corrected by S2, a 3:1 split ex the same day, published
# 2026-04-01.  So a cutoff of 2026-03-20 sees (G1, S1); 2026-03-30 sees
# (G2, S1); 2026-04-15 sees (G2, S1+S2 resolved to S2).
from dataclasses import replace

from lib.dataos.price_views import (
    AdjustmentReference,
    PriceView,
    ViewVintage,
    admit_action_input,
    admit_revision_set,
    reconstruct_price_view,
    reopen_view,
    retain_view,
    return_vector,
    simple_returns,
)
from lib.dataos.read_contract import (Dependency, GenerationRef, ReadMode, ReadRefusal, ReadRequest, RefusalCode, ViewContract)
from lib.dataos.registry import DatasetContract, Registry
from lib.dataos.temporal import TemporalProfile

CODE = "c0dec0de" * 5
IDGEN = "IDGEN-1"


def _p05_contract() -> ViewContract:
    return ViewContract(purpose="P05 retained-view witness", identity={"security_id": "SEC-P05", "listing_id": "LST-P05"},
                        field_units={"close_sadj": "USD/share"}, adjustment_reference={"basis": "sadj"},
                        coverage="synthetic rows local to this suite")


def _p05_registry() -> Registry:
    return Registry([DatasetContract.from_mapping({"dataset_id": "equity.actions.splits.testfix", "layer": "L1", "status": "PRODUCED",
        "owner": "macro-dashboard", "producer": "collectors/example.py", "storage": "data/example/{ticker}.parquet", "format": "parquet",
        "grain": ["ticker", "ex_date"], "temporal_profile": "EVENT", "version": "1.0.0"})])


def _obs(receipt: str, origin: str = "source_record") -> dict:
    return {"dataset_id": "equity.actions.splits.testfix", "endpoint": "daily/TEST/splits", "field_convention": "as_observed_split_ratio",
            "receipt": receipt, "origin": origin, "response": "events", "rights_limited": False}


_P05_REGISTRY = _p05_registry()
_P05_DAYS = ("2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06")
_P05_CLOSES = {"G1": (100, 102, 101, 104, 105), "G2": (101, 102, 101, 104, 105)}
_P05_VOLUMES = (1000, 1010, 1020, 1030, 1040)
_P05_G1_PUB = "2026-03-07T00:00:00+00:00"
_P05_G2_PUB = "2026-03-25T00:00:00+00:00"


def _p05_bar_rows(generation_id: str, published_at: str) -> tuple[dict, ...]:
    return tuple(
        {"date": day,
         "period_start": f"{day}T00:00:00+00:00",
         "period_end": f"{day}T23:59:59+00:00",
         "published_at": published_at,
         "ingested_at": published_at,
         "generation_id": generation_id,
         "close_raw": close,
         "volume_raw": volume}
        for day, close, volume in zip(_P05_DAYS, _P05_CLOSES[generation_id], _P05_VOLUMES)
    )


_P05_BARS_G1 = _p05_bar_rows("G1", _P05_G1_PUB)
_P05_BARS_G2 = _p05_bar_rows("G2", _P05_G2_PUB)
_P05_G1_REF = GenerationRef("G1", published_at=_P05_G1_PUB, ingested_at=_P05_G1_PUB)
_P05_G2_REF = GenerationRef("G2", published_at=_P05_G2_PUB, ingested_at=_P05_G2_PUB, supersedes="G1")
_P05_BARS = Dependency("bars", TemporalProfile.BARS, rows=_P05_BARS_G1 + _P05_BARS_G2,
                       generations=(_P05_G1_REF, _P05_G2_REF))


def _p05_action(event_id: str, *, ratio: str, published_at: str, supersedes: str | None = None) -> dict:
    row = {"event_id": event_id, "family": "forward_split", "ex_date": "2026-03-10",
           "event_at": "2026-03-01T00:00:00+00:00", "published_at": published_at,
           "ingested_at": published_at, "ratio": ratio, "source_receipt": f"rcpt:{event_id}"}
    if supersedes is not None:
        row["supersedes"] = supersedes
    return row


_S1_ROW = _p05_action("S1", ratio="2/1", published_at="2026-03-01T00:00:00+00:00")
_S2_ROW = _p05_action("S2", ratio="3/1", published_at="2026-04-01T00:00:00+00:00", supersedes="S1")


def _p05_compose(cutoff, action_rows, observations=None, *, bars=None, basis="SADJ",
                 identity_generation_id=IDGEN):
    """reconstruct_price_view over the shared witness, qualified by default."""
    return reconstruct_price_view(
        ReadRequest(ReadMode.RECONSTRUCT, _p05_contract(), cutoff=cutoff, clock="published_at"),
        bars=bars if bars is not None else _P05_BARS,
        actions=Dependency("actions", TemporalProfile.EVENT, rows=tuple(action_rows)),
        observations=observations if observations is not None
        else {row["event_id"]: _obs(row["source_receipt"]) for row in action_rows},
        registry=_P05_REGISTRY, code_version=CODE,
        identity_generation_id=identity_generation_id, basis=basis)


def _p05_close(view, day: str) -> Fraction:
    (row,) = [row for row in view.rows if row["date"] == date.fromisoformat(day)]
    return row["close_sadj"]


def _p05_replay(output_id: str) -> ReadRequest:
    return ReadRequest(ReadMode.REPLAY, _p05_contract(), output_id=output_id)


# ── P05.01 — a corrected old bar is a NEW vintage, never a rewrite ────────────

def test_P05_01_corrected_old_bar_is_a_new_vintage_not_a_rewrite() -> None:
    a = _p05_compose(known(2026, 3, 20), (_S1_ROW,))  # G1 bars, S1
    b = _p05_compose(known(2026, 3, 30), (_S1_ROW,))  # G2 bars (03-02: 100 -> 101), S1
    retained_a = retain_view(a.view, a.vintage, output_id="out-A")
    retained_b = retain_view(b.view, b.vintage, output_id="out-B")
    assert retained_b.view_digest != retained_a.view_digest
    assert b.label != a.label
    assert retained_b.key != retained_a.key
    assert retained_a.vintage.source_generation_id == "G1"
    assert retained_b.vintage.source_generation_id == "G2"
    # the correction moves the 2026-03-02 SADJ level from 100/2 to 101/2
    assert _p05_close(b.view, "2026-03-02") == Fraction(101, 2)
    assert _p05_close(a.view, "2026-03-02") == Fraction(50)


def test_P05_01_retained_view_reopens_byte_exactly() -> None:
    a = _p05_compose(known(2026, 3, 20), (_S1_ROW,))
    retained_a = retain_view(a.view, a.vintage, output_id="out-A")
    reopened = reopen_view(retained_a, _p05_replay("out-A"))
    assert reopened.view == a.view
    assert reopened.label == retained_a.label == a.label
    assert reopened.vintage.source_generation_id == "G1"
    assert reopened.result.payload == retained_a.payload
    assert reopened.result.evidence["sha256"] == retained_a.view_digest


def test_P05_01b_tampered_payload_refuses_RETAINED_DIGEST_MISMATCH() -> None:
    retained_a = retain_view(_p05_compose(known(2026, 3, 20), (_S1_ROW,)).view,
                             _p05_compose(known(2026, 3, 20), (_S1_ROW,)).vintage, output_id="out-A")
    payload = retained_a.payload
    tampered = payload[:-1] + bytes([payload[-1] ^ 0x01])
    with pytest.raises(ReadRefusal) as raised:
        reopen_view(replace(retained_a, payload=tampered), _p05_replay("out-A"))
    assert raised.value.code is RefusalCode.RETAINED_DIGEST_MISMATCH


def test_P05_01b_missing_material_or_wrong_output_id_refuses_NO_RETAINED_OUTPUT() -> None:
    a = _p05_compose(known(2026, 3, 20), (_S1_ROW,))
    retained_a = retain_view(a.view, a.vintage, output_id="out-A")
    with pytest.raises(ReadRefusal) as raised:
        reopen_view(replace(retained_a, payload=None), _p05_replay("out-A"))
    assert raised.value.code is RefusalCode.NO_RETAINED_OUTPUT
    with pytest.raises(ReadRefusal) as raised:
        reopen_view(retained_a, _p05_replay("out-OTHER"))
    assert raised.value.code is RefusalCode.NO_RETAINED_OUTPUT


# ── P05.02 — a split correction is invisible until its clock passes the cutoff ─

def test_P05_02_correction_known_after_the_cutoff_is_invisible() -> None:
    only_s1 = _p05_compose(known(2026, 3, 20), (_S1_ROW,))
    with_correction = _p05_compose(known(2026, 3, 20), (_S1_ROW, _S2_ROW))
    assert with_correction.view.rows == only_s1.view.rows
    assert with_correction.vintage.revision_set_id == only_s1.vintage.revision_set_id
    assert retain_view(with_correction.view, with_correction.vintage,
                       output_id="out-w").view_digest == retain_view(
        only_s1.view, only_s1.vintage, output_id="out-o").view_digest
    assert with_correction.label == only_s1.label
    for row, raw in zip(only_s1.view.rows, _P05_CLOSES["G1"]):
        assert row["close_sadj"] == Fraction(raw, 2)  # every SADJ close == raw / 2


def test_P05_02_correction_known_before_the_cutoff_moves_view_and_vintage() -> None:
    late = _p05_compose(known(2026, 4, 15), (_S1_ROW, _S2_ROW))
    for row, raw in zip(late.view.rows, _P05_CLOSES["G2"]):
        assert row["close_sadj"] == Fraction(raw, 3)  # the CURRENT result is /3
    early = _p05_compose(known(2026, 3, 20), (_S1_ROW,))
    assert late.vintage.revision_set_id != early.vintage.revision_set_id
    assert retain_view(late.view, late.vintage, output_id="out-late").view_digest != retain_view(
        early.view, early.vintage, output_id="out-early").view_digest


def test_P05_02_the_retained_older_view_still_returns_the_old_rows() -> None:
    early = _p05_compose(known(2026, 3, 20), (_S1_ROW, _S2_ROW))
    retained_early = retain_view(early.view, early.vintage, output_id="out-early")
    _p05_compose(known(2026, 4, 15), (_S1_ROW, _S2_ROW))  # the correction is current now
    reopened = reopen_view(retained_early, _p05_replay("out-early"))
    for row, raw in zip(reopened.view.rows, _P05_CLOSES["G1"]):
        assert row["close_sadj"] == Fraction(raw, 2)  # still the /2 rows, exactly


# ── P05.03 — one generation, one receipt ──────────────────────────────────────

def test_P05_03_an_old_receipt_cannot_publish_a_new_generation() -> None:
    a = _p05_compose(known(2026, 3, 20), (_S1_ROW,))
    b = _p05_compose(known(2026, 3, 30), (_S1_ROW,))
    retained_a = retain_view(a.view, a.vintage, output_id="out-A")
    with pytest.raises(ViewRefusal) as raised:
        retain_view(b.view, b.vintage, output_id="out-A",
                    publishing_receipt_sha256=retained_a.publishing_receipt_sha256)
    assert raised.value.reason is RefusalReason.MIXED_GENERATION


def test_P05_03_reopen_refuses_bytes_retained_under_another_identity_generation() -> None:
    a = _p05_compose(known(2026, 3, 20), (_S1_ROW,))
    retained_a = retain_view(a.view, a.vintage, output_id="out-A")
    with pytest.raises(ViewRefusal) as raised:
        reopen_view(
            replace(retained_a, vintage=replace(retained_a.vintage, identity_generation_id="IDGEN-2")),
            _p05_replay("out-A"))
    assert raised.value.reason is RefusalReason.MIXED_GENERATION


def test_P05_03_a_vintage_must_name_the_revision_set_the_view_was_computed_against() -> None:
    a = _p05_compose(known(2026, 3, 20), (_S1_ROW,))
    with pytest.raises(ViewRefusal) as raised:
        retain_view(a.view, replace(a.vintage, revision_set_id="actions:" + "0" * 64), output_id="out-X")
    assert raised.value.reason is RefusalReason.MIXED_GENERATION


# ── P05.04 — a common scalar cancels; a single-bar correction does not ────────

def test_P05_04_return_vector_equal_is_true_for_three_common_scalars() -> None:
    p0, p1 = Fraction(101, 2), Fraction(52)  # literal endpoints of the witness
    for c in (Fraction(1, 3), Fraction(7), Fraction(2, 5)):
        vector = return_vector(p0, p1, c, c)
        assert vector["equal"] is True
        assert vector["original"] == vector["rebased"] == Fraction(3, 101)


def test_P05_04_a_constant_rescale_cancels_in_simple_returns_a_correction_does_not() -> None:
    # DEVIATION (recorded in the return packet): the invariance pair holds the
    # bars GENERATION fixed (G2) and varies only the split factor — the /2 view
    # over G2 is the cutoff 2026-03-30 composition, since the packet's own
    # counter-control requires the G1 -> G2 correction to move the first return
    # and would therefore make a /2-over-G1 comparison unequal by construction.
    b = _p05_compose(known(2026, 3, 30), (_S1_ROW,))          # /2 over G2
    z = _p05_compose(known(2026, 4, 15), (_S1_ROW, _S2_ROW))  # /3 over G2
    expected = (Fraction(1, 101), Fraction(-1, 102), Fraction(3, 101), Fraction(1, 104))
    assert simple_returns(b.view) == expected
    assert simple_returns(z.view) == expected  # the rescale cancels ...
    assert [row["close_sadj"] for row in b.view.rows] != [row["close_sadj"] for row in z.view.rows]
    a = _p05_compose(known(2026, 3, 20), (_S1_ROW,))          # /2 over G1
    # COUNTER-CONTROL: the single-bar correction DOES change the first return
    assert simple_returns(a.view)[0] == Fraction(1, 50) != simple_returns(b.view)[0]


# ── P05.05 — the qualify-first gate ───────────────────────────────────────────

def test_P05_05_the_gate_discards_the_caller_qualification_and_stamps_the_verdict() -> None:
    s1 = event("S1", known_at=ANNOUNCED)  # the CALLER says CONFIRMED
    admitted = admit_action_input(
        s1, _obs(s1.source_receipt, origin="price_discontinuity"), registry=_P05_REGISTRY)
    assert admitted.qualification == "SUSPECTED"  # the caller's CONFIRMED is discarded
    assert admitted is not s1 and s1.qualification == "CONFIRMED"  # the original is untouched
    stamped = ActionRevisionSet("gate", (admitted,))
    with pytest.raises(ViewRefusal) as raised:
        split_factor(ROW_DAY, stamped, AS_AT)
    assert raised.value.reason is RefusalReason.NOT_CONFIRMED
    assert raised.value.event_id == "S1"
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": ROW_DAY, "close_raw": 100}], stamped, AS_AT)
    assert raised.value.reason is RefusalReason.NOT_CONFIRMED
    assert raised.value.event_id == "S1"
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(TR_ROWS, stamped, AS_AT, TR_POLICY)
    assert raised.value.reason is RefusalReason.NOT_CONFIRMED
    assert raised.value.event_id == "S1"
    # outside every window the stamped event is inert
    assert split_factor(EX_DAY, stamped, AS_AT) == Fraction(1)


def test_P05_05_composed_path_refuses_a_discontinuity_observation() -> None:
    with pytest.raises(ViewRefusal) as raised:
        _p05_compose(known(2026, 3, 20), (_S1_ROW,),
                     observations={"S1": _obs("rcpt:S1", origin="price_discontinuity")})
    assert raised.value.reason is RefusalReason.NOT_CONFIRMED
    assert raised.value.event_id == "S1"


def test_P05_05_an_event_without_an_observation_refuses_NOT_CONFIRMED() -> None:
    with pytest.raises(ViewRefusal) as raised:
        _p05_compose(known(2026, 3, 20), (_S1_ROW,), observations={})
    assert raised.value.reason is RefusalReason.NOT_CONFIRMED
    assert raised.value.event_id == "S1"


def test_P05_05_a_qualified_empty_response_is_not_an_event() -> None:
    with pytest.raises(ViewRefusal) as raised:
        _p05_compose(known(2026, 3, 20), (_S1_ROW,),
                     observations={"S1": dict(_obs("rcpt:S1"), response="empty")})
    assert raised.value.reason is RefusalReason.NOT_CONFIRMED
    assert raised.value.event_id == "S1"


def test_P05_05_a_receipt_from_another_observation_refuses_RECEIPT_MISMATCH() -> None:
    with pytest.raises(ViewRefusal) as raised:
        _p05_compose(known(2026, 3, 20), (_S1_ROW,), observations={"S1": _obs("rcpt:OTHER")})
    assert raised.value.reason is RefusalReason.RECEIPT_MISMATCH
    assert raised.value.event_id == "S1"
    with pytest.raises(ViewRefusal) as raised:  # and through the single-event gate
        admit_action_input(event("S1", known_at=ANNOUNCED), _obs("rcpt:OTHER"), registry=_P05_REGISTRY)
    assert raised.value.reason is RefusalReason.RECEIPT_MISMATCH


def test_P05_05_positive_control_a_source_record_observation_admits_confirmed() -> None:
    s1 = event("S1", known_at=ANNOUNCED)
    admitted = admit_action_input(s1, _obs(s1.source_receipt), registry=_P05_REGISTRY)
    assert admitted.qualification == "CONFIRMED"
    revisions = admit_revision_set("gate-ok", ((s1, _obs(s1.source_receipt)),), registry=_P05_REGISTRY)
    (row,) = sadj_view([{"date": ROW_DAY, "close_raw": 100, "volume_raw": 4}], revisions, AS_AT).rows
    assert row["close_sadj"] == Fraction(50)  # the exact projected Fractions
    assert row["volume_sadj"] == Fraction(8)
    composed = _p05_compose(known(2026, 3, 20), (_S1_ROW,))
    assert composed.view.rows[0]["close_sadj"] == Fraction(50)


# ── UNBOUND_GENERATION / NON_EXACT_INPUT ──────────────────────────────────────

def test_P05_unbound_generation_a_bars_dependency_without_generations_refuses() -> None:
    bars = Dependency("bars", TemporalProfile.BARS, rows=_P05_BARS_G1)
    with pytest.raises(ViewRefusal) as raised:
        _p05_compose(known(2026, 3, 20), (_S1_ROW,), bars=bars)
    assert raised.value.reason is RefusalReason.UNBOUND_GENERATION


def test_P05_non_exact_input_a_float_pass_through_value_cannot_be_retained() -> None:
    view = PriceView(
        "RAW",
        ({"date": date(2026, 3, 2), "close_raw": Fraction(100), "note_weight": 0.5},),
        AdjustmentReference("RAW", None, None),
        True,
    )
    with pytest.raises(ViewRefusal) as raised:
        retain_view(view, ViewVintage("G1", None, IDGEN, CODE), output_id="out-float")
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT
