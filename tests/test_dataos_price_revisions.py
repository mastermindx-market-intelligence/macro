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
