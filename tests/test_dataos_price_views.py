"""SADJ price views — ``lib/dataos/price_views.py`` (Data OS §D4, D00.D3, lane O2-P02).

Discriminating tests with hand-computed literal Fractions: every expected
number below was computed by hand from D00.D3, never by calling the function
under test.  Vectors V01–V05 and the half-open ``ex_date`` boundary are the
D00 witness vectors for ``S(t) = prod r_e`` over CONFIRMED splits with
``ex_date > t``; P03.02–P03.04 pin the fail-closed column/value law.

Run: .venv/bin/python -m pytest tests/test_dataos_price_views.py -q
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction

import pytest

from lib.dataos.price_views import (
    ActionEvent,
    ActionFamily,
    ActionRevisionSet,
    AdjustmentReference,
    PriceView,
    RefusalReason,
    ReinvestPolicy,
    TotalReturnPolicy,
    TotalReturnView,
    ViewRefusal,
    adjust_quantity,
    qualified_return,
    raw_view,
    return_vector,
    sadj_view,
    split_factor,
    total_return_view,
)

UTC = timezone.utc
EX_DAY = date(2026, 6, 10)  # the split's ex_date used throughout
AS_AT = datetime(2026, 6, 20, tzinfo=UTC)  # after every ex_date here


def known(*args, **kw) -> datetime:
    return datetime(*args, tzinfo=UTC)


def split(event_id: str, ratio, *, ex_date: date = EX_DAY, family=ActionFamily.FORWARD_SPLIT,
          known_at: datetime = known(2026, 1, 1), qualification: str = "CONFIRMED", **kw) -> ActionEvent:
    return ActionEvent(
        event_id=event_id,
        family=family,
        ex_date=ex_date,
        known_at=known_at,
        source_receipt=f"rcpt:{event_id}",
        qualification=qualification,
        ratio=ratio,
        **kw,
    )


def cash(event_id: str, per_share, *, ex_date: date = EX_DAY,
         known_at: datetime = known(2026, 1, 1), **kw) -> ActionEvent:
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
        **kw,
    )


EMPTY = ActionRevisionSet("empty", ())


# ── V01/V02/V03 — wealth is invariant, only the unit changes ─────────────────

def test_V01_forward_2_price_50_qty_6_wealth_300() -> None:
    """raw 100, qty 3, forward 2:1 -> price 50, qty 6, wealth 300."""
    revisions = ActionRevisionSet("v01", (split("s1", Fraction(2)),))
    view = sadj_view(
        [{"date": date(2026, 6, 9), "close_raw": 100, "volume_raw": 3}],
        revisions,
        AS_AT,
        mic="XNYS",
    )
    (row,) = view.rows
    assert set(row) == {"date", "close_sadj", "volume_sadj"}
    assert row["close_sadj"] == Fraction(50)
    assert row["volume_sadj"] == Fraction(6)
    assert row["close_sadj"] * row["volume_sadj"] == Fraction(300)  # == 100 * 3
    assert isinstance(row["close_sadj"], Fraction) and isinstance(row["volume_sadj"], Fraction)


def test_V02_reverse_1_5_price_50_qty_1_wealth_50() -> None:
    """raw 10, qty 5, reverse 1:5 (r = 1/5) -> price 50, qty 1, wealth 50."""
    revisions = ActionRevisionSet(
        "v02", (split("s1", Fraction(1, 5), family=ActionFamily.REVERSE_SPLIT),)
    )
    view = sadj_view(
        [{"date": date(2026, 6, 9), "close_raw": 10, "volume_raw": 5}],
        revisions,
        AS_AT,
        mic="XNYS",
    )
    (row,) = view.rows
    assert row["close_sadj"] == Fraction(50)
    assert row["volume_sadj"] == Fraction(1)
    assert row["close_sadj"] * row["volume_sadj"] == Fraction(50)  # == 10 * 5


def test_V03_chained_2_and_3_2_is_one_event_of_ratio_3() -> None:
    """raw 90, qty 1200, [2, 3/2] -> price 30, qty 3600, wealth 108000."""
    chained = ActionRevisionSet(
        "v03",
        (
            split("s1", Fraction(2), ex_date=date(2026, 6, 10)),
            split("s2", Fraction(3, 2), ex_date=date(2026, 6, 12)),
        ),
    )
    view = sadj_view(
        [{"date": date(2026, 6, 9), "close_raw": 90, "volume_raw": 1200}],
        chained,
        AS_AT,
        mic="XNYS",
    )
    (row,) = view.rows
    assert row["close_sadj"] == Fraction(30)
    assert row["volume_sadj"] == Fraction(3600)
    assert row["close_sadj"] * row["volume_sadj"] == Fraction(108000)

    # composition property: the chain equals ONE event of ratio 3
    single = ActionRevisionSet("v03-single", (split("s3", Fraction(3)),))
    assert split_factor(date(2026, 6, 9), chained, AS_AT, mic="XNYS") == Fraction(3)
    assert split_factor(date(2026, 6, 9), chained, AS_AT, mic="XNYS") == split_factor(
        date(2026, 6, 9), single, AS_AT,
        mic="XNYS",
    )


def test_V03_inverse_forward_2_then_reverse_1_2_is_factor_1() -> None:
    inverse = ActionRevisionSet(
        "v03-inv",
        (
            split("s1", Fraction(2), ex_date=date(2026, 6, 10)),
            split("s2", Fraction(1, 2), ex_date=date(2026, 6, 12), family=ActionFamily.REVERSE_SPLIT),
        ),
    )
    assert split_factor(date(2026, 6, 9), inverse, AS_AT, mic="XNYS") == Fraction(1)


def test_V03_wealth_preserved_on_every_row_of_a_multi_event_window() -> None:
    """price_sadj * q_sadj == price_raw * q_raw on every row, all boundaries."""
    revisions = ActionRevisionSet(
        "v03-wealth",
        (
            split("s1", Fraction(2), ex_date=date(2026, 6, 10)),
            split("s2", Fraction(3, 2), ex_date=date(2026, 6, 12)),
        ),
    )
    rows = [
        {"date": date(2026, 6, 9), "close_raw": 90, "volume_raw": 1200},   # S = 3
        {"date": date(2026, 6, 10), "close_raw": 90, "volume_raw": 1200},  # S = 3/2
        {"date": date(2026, 6, 11), "close_raw": 90, "volume_raw": 1200},  # S = 3/2
        {"date": date(2026, 6, 12), "close_raw": 90, "volume_raw": 1200},  # S = 1
    ]
    view = sadj_view(rows, revisions, AS_AT, mic="XNYS")
    by_day = {row["date"]: row for row in view.rows}
    assert by_day[date(2026, 6, 9)]["close_sadj"] == Fraction(30)
    assert by_day[date(2026, 6, 10)]["close_sadj"] == Fraction(60)
    assert by_day[date(2026, 6, 11)]["close_sadj"] == Fraction(60)
    assert by_day[date(2026, 6, 12)]["close_sadj"] == Fraction(90)
    for row in view.rows:
        assert row["close_sadj"] * row["volume_sadj"] == Fraction(108000)


# ── V04/V05 — returns across (non-)split boundaries ──────────────────────────

def test_V04_common_scalar_cancels_original_equals_rebased() -> None:
    """p0 100, p1 110, k0 = k1 = 1/10 -> both returns 1/10, equal."""
    vector = return_vector(Fraction(100), Fraction(110), Fraction(1, 10), Fraction(1, 10))
    assert vector["original"] == Fraction(1, 10)
    assert vector["rebased"] == Fraction(1, 10)
    assert vector["equal"] is True
    assert isinstance(vector["original"], Fraction) and isinstance(vector["rebased"], Fraction)


def test_V05_scalar_on_one_endpoint_breaks_equality_and_qualifies_a_refusal() -> None:
    """p0 100, p1 110, k0 1, k1 1/2 -> original 1/10, rebased -9/20, not equal."""
    vector = return_vector(Fraction(100), Fraction(110), Fraction(1), Fraction(1, 2))
    assert vector["original"] == Fraction(1, 10)
    assert vector["rebased"] == Fraction(-9, 20)
    assert vector["equal"] is False
    with pytest.raises(ViewRefusal) as raised:
        qualified_return(Fraction(100), Fraction(110), Fraction(1), Fraction(1, 2))
    assert raised.value.reason is RefusalReason.RETURN_ACROSS_UNADJUSTED_SPLIT


def test_qualified_return_answers_only_when_no_split_crosses_the_interval() -> None:
    assert qualified_return(Fraction(100), Fraction(110), Fraction(1), Fraction(1)) == Fraction(1, 10)
    assert (
        qualified_return(Fraction(100), Fraction(110), Fraction(1, 10), Fraction(1, 10))
        == Fraction(1, 10)
    )


def test_adjust_quantity_multiplies_and_refuses_other_conventions() -> None:
    assert adjust_quantity(Fraction(1200), Fraction(3, 2)) == Fraction(1800)
    assert adjust_quantity(5, Fraction(1, 5)) == Fraction(1)
    with pytest.raises(ViewRefusal) as raised:
        adjust_quantity(Fraction(1200), Fraction(3, 2), "lots")
    assert raised.value.reason is RefusalReason.UNSUPPORTED_QUANTITY_CONVENTION


# ── the half-open ex_date boundary (D00.D3; the V12 alias vector is ORCH-1's) ─

def test_half_open_ex_date_boundary_row_before_ex_date_divided_row_on_ex_date_untouched() -> None:
    revisions = ActionRevisionSet("boundary", (split("s1", Fraction(2)),))
    # a row dated ex_date - 1 day gets factor r ...
    assert split_factor(EX_DAY - timedelta(days=1), revisions, AS_AT, mic="XNYS") == Fraction(2)
    # ... a row dated ex_date itself gets 1
    assert split_factor(EX_DAY, revisions, AS_AT, mic="XNYS") == Fraction(1)
    view = sadj_view(
        [
            {"date": date(2026, 6, 9), "close_raw": 100},
            {"date": date(2026, 6, 10), "close_raw": 100},
        ],
        revisions,
        AS_AT,
        mic="XNYS",
    )
    by_day = {row["date"]: row["close_sadj"] for row in view.rows}
    assert by_day[date(2026, 6, 9)] == Fraction(50)
    assert by_day[date(2026, 6, 10)] == Fraction(100)


def test_half_open_ex_date_boundary_event_after_as_at_is_not_yet_effective() -> None:
    """ex_date > as_at: the share basis at as_at is the pre-split one (D00.D3)."""
    revisions = ActionRevisionSet("future", (split("s1", Fraction(2)),))
    before = datetime(2026, 6, 5, tzinfo=UTC)
    assert split_factor(date(2026, 6, 1), revisions, before, mic="XNYS") == Fraction(1)
    view = sadj_view(
        [{"date": date(2026, 6, 1), "close_raw": 100, "volume_raw": 7}],
        revisions,
        before,
        mic="XNYS",
    )
    (row,) = view.rows
    assert row["close_sadj"] == Fraction(100)
    assert row["volume_sadj"] == Fraction(7)


# ── P03.02 — never adjust twice, never accept a proxy ────────────────────────

def test_P03_02_close_sadj_input_refuses_DOUBLE_ADJUST_RISK() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_sadj": Fraction(100)}], EMPTY, AS_AT, mic="XNYS")
    assert raised.value.reason is RefusalReason.DOUBLE_ADJUST_RISK
    assert raised.value.column == "close_sadj"


def test_P03_02_close_tradj_input_refuses_NON_RAW_INPUT() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_tradj": Fraction(100)}], EMPTY, AS_AT, mic="XNYS")
    assert raised.value.reason is RefusalReason.NON_RAW_INPUT
    assert raised.value.column == "close_tradj"


def test_P03_02_bare_close_refuses_AMBIGUOUS_BASIS() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close": 100}], EMPTY, AS_AT, mic="XNYS")
    assert raised.value.reason is RefusalReason.AMBIGUOUS_BASIS
    assert raised.value.column == "close"


# ── P03.03 — cash dividends never touch SADJ prices or volume ────────────────

def test_P03_03_confirmed_cash_dividend_in_window_changes_nothing() -> None:
    rows = [{"date": date(2026, 6, 9), "close_raw": 100, "volume_raw": 1000}]
    without = sadj_view(rows, EMPTY, AS_AT, mic="XNYS")
    with_cash = sadj_view(
        rows, ActionRevisionSet("cash", (cash("d1", Fraction(1, 4)),)), AS_AT,
        mic="XNYS",
    )
    assert with_cash.rows == without.rows  # prices AND volume_sadj identical
    (row,) = with_cash.rows
    assert row["close_sadj"] == Fraction(100)
    assert row["volume_sadj"] == Fraction(1000)


# ── P03.04 — each bad value its own typed refusal ────────────────────────────

def _window_factor(event: ActionEvent):
    revisions = ActionRevisionSet("p0304", (event,))
    return split_factor(date(2026, 6, 9), revisions, AS_AT, mic="XNYS")


def test_P03_04_zero_ratio_refuses_INVALID_RATIO() -> None:
    with pytest.raises(ViewRefusal) as raised:
        _window_factor(split("s1", Fraction(0)))
    assert raised.value.reason is RefusalReason.INVALID_RATIO
    assert raised.value.event_id == "s1"


def test_P03_04_negative_ratio_refuses_INVALID_RATIO() -> None:
    with pytest.raises(ViewRefusal) as raised:
        _window_factor(split("s1", Fraction(-2)))
    assert raised.value.reason is RefusalReason.INVALID_RATIO


def test_P03_04_missing_ratio_refuses_UNKNOWN_RATIO() -> None:
    with pytest.raises(ViewRefusal) as raised:
        _window_factor(split("s1", None))
    assert raised.value.reason is RefusalReason.UNKNOWN_RATIO


def test_P03_04_forward_split_with_ratio_below_one_refuses_INVALID_RATIO() -> None:
    with pytest.raises(ViewRefusal) as raised:
        _window_factor(split("s1", Fraction(1, 2)))
    assert raised.value.reason is RefusalReason.INVALID_RATIO


def test_P03_04_reverse_split_with_ratio_above_one_refuses_INVALID_RATIO() -> None:
    with pytest.raises(ViewRefusal) as raised:
        _window_factor(split("s1", Fraction(3, 2), family=ActionFamily.REVERSE_SPLIT))
    assert raised.value.reason is RefusalReason.INVALID_RATIO


def test_P03_04_split_carrying_cash_refuses_CASH_BASIS_MISMATCH() -> None:
    event = split("s1", Fraction(2), cash_per_share=Fraction(1, 4))
    with pytest.raises(ViewRefusal) as raised:
        _window_factor(event)
    assert raised.value.reason is RefusalReason.CASH_BASIS_MISMATCH


def test_P03_04_cash_carrying_ratio_refuses_CASH_BASIS_MISMATCH() -> None:
    mismatched = ActionEvent(
        event_id="d1x",
        family=ActionFamily.CASH_DIVIDEND,
        ex_date=EX_DAY,
        known_at=known(2026, 1, 1),
        source_receipt="rcpt:d1x",
        qualification="CONFIRMED",
        ratio=Fraction(2),
        cash_per_share=Fraction(1, 4),
        cash_basis="as_declared",
    )
    with pytest.raises(ViewRefusal) as raised:
        _window_factor(mismatched)
    assert raised.value.reason is RefusalReason.CASH_BASIS_MISMATCH


def test_P03_04_open_raw_plus_close_sadj_in_one_row_refuses_MIXED_OHLC_BASIS() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view(
            [{"date": date(2026, 6, 9), "open_raw": 100, "close_sadj": Fraction(100)}],
            EMPTY,
            AS_AT,
            mic="XNYS",
        )
    assert raised.value.reason is RefusalReason.MIXED_OHLC_BASIS


def test_P03_04_mixed_bases_across_rows_also_refuse_MIXED_OHLC_BASIS() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view(
            [
                {"date": date(2026, 6, 9), "close_raw": 100},
                {"date": date(2026, 6, 10), "close_tradj": Fraction(100)},
            ],
            EMPTY,
            AS_AT,
            mic="XNYS",
        )
    assert raised.value.reason is RefusalReason.MIXED_OHLC_BASIS


def test_P03_04_lots_convention_refuses_UNSUPPORTED_QUANTITY_CONVENTION() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view(
            [{"date": date(2026, 6, 9), "close_raw": 100, "volume_raw": 3}],
            EMPTY,
            AS_AT,
            quantity_convention="lots",
            mic="XNYS",
        )
    assert raised.value.reason is RefusalReason.UNSUPPORTED_QUANTITY_CONVENTION


def test_P03_04_float_price_refuses_NON_EXACT_INPUT() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_raw": 100.0}], EMPTY, AS_AT, mic="XNYS")
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT


def test_P03_04_bool_and_bogus_string_prices_refuse_NON_EXACT_INPUT() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_raw": True}], EMPTY, AS_AT, mic="XNYS")
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_raw": "cheap"}], EMPTY, AS_AT, mic="XNYS")
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT


def test_exact_inputs_int_decimal_and_rational_string_are_accepted_exactly() -> None:
    revisions = ActionRevisionSet("exact", (split("s1", Fraction(3, 2)),))
    view = sadj_view(
        [
            {"date": date(2026, 6, 9), "close_raw": 201},                 # int
            {"date": date(2026, 6, 10), "close_raw": Decimal("201")},     # Decimal
            {"date": date(2026, 6, 11), "close_raw": "402/2"},            # rational str
        ],
        revisions,
        AS_AT,
        mic="XNYS",
    )
    by_day = {row["date"]: row for row in view.rows}
    assert by_day[date(2026, 6, 9)]["close_sadj"] == Fraction(134)   # 201 / (3/2)
    assert by_day[date(2026, 6, 10)]["close_sadj"] == Fraction(201)  # post-ex rows: 201 / 1
    assert by_day[date(2026, 6, 11)]["close_sadj"] == Fraction(201)
    assert adjust_quantity("402/2", "3/2") == Fraction(603, 2)  # 201 * 3/2


# ── executability and view shape ─────────────────────────────────────────────

def test_non_RAW_PriceView_executable_True_refuses() -> None:
    reference = AdjustmentReference("SADJ", None, None)
    with pytest.raises(ViewRefusal):
        PriceView(basis="SADJ", rows=(), reference=reference, executable=True)
    with pytest.raises(ViewRefusal):
        PriceView(basis="TRADJ", rows=(), reference=AdjustmentReference("TRADJ", None, None), executable=True)


def test_raw_view_is_executable_sadj_view_never_is() -> None:
    rows = [{"date": date(2026, 6, 9), "close_raw": 100, "volume_raw": 3}]
    raw = raw_view(rows)
    assert raw.basis == "RAW"
    assert raw.executable is True
    assert raw.reference == AdjustmentReference("RAW", None, None)
    adjusted = sadj_view(rows, ActionRevisionSet("v", (split("s1", Fraction(2)),)), AS_AT, mic="XNYS")
    assert adjusted.basis == "SADJ"
    assert adjusted.executable is False
    assert adjusted.reference.action_revision_set_id == "v"
    assert adjusted.reference.as_at == AS_AT


def test_raw_view_still_applies_the_column_law() -> None:
    """A vendor-adjusted series can never be labelled RAW (the DNR kill case)."""
    with pytest.raises(ViewRefusal):
        raw_view([{"date": date(2026, 6, 9), "close": 100}])
    with pytest.raises(ViewRefusal):
        raw_view([{"date": date(2026, 6, 9), "close_tradj": Fraction(100)}])


def test_every_numeric_output_is_a_Fraction() -> None:
    revisions = ActionRevisionSet(
        "frac",
        (
            split("s1", Fraction(2), ex_date=date(2026, 6, 10)),
            cash("d1", Fraction(1, 4), ex_date=date(2026, 6, 11)),
        ),
    )
    view = sadj_view(
        [
            {"date": date(2026, 6, 9), "open_raw": 99, "high_raw": 101, "low_raw": 98, "close_raw": 100, "volume_raw": 3},
            {"date": date(2026, 6, 10), "open_raw": 49, "high_raw": 51, "low_raw": 48, "close_raw": 50, "volume_raw": 6},
        ],
        revisions,
        AS_AT,
        mic="XNYS",
    )
    for row in view.rows:
        assert set(row) == {"date", "open_sadj", "high_sadj", "low_sadj", "close_sadj", "volume_sadj"}
        for key, value in row.items():
            if key != "date":
                assert isinstance(value, Fraction), (key, value)
    assert split_factor(date(2026, 6, 9), revisions, AS_AT, mic="XNYS") == Fraction(2)  # cash adds nothing
    (day1, day2) = view.rows
    assert day1["open_sadj"] == Fraction(99, 2)
    assert day1["high_sadj"] == Fraction(101, 2)
    assert day1["low_sadj"] == Fraction(49)
    assert day1["close_sadj"] == Fraction(50)
    assert day2["close_sadj"] == Fraction(50)


def test_naive_timestamps_refuse_NAIVE_TIMESTAMP() -> None:
    with pytest.raises(ViewRefusal) as raised:
        split("s1", Fraction(2), known_at=datetime(2026, 1, 1))  # naive known_at
    assert raised.value.reason is RefusalReason.NAIVE_TIMESTAMP
    revisions = ActionRevisionSet("naive", (split("s1", Fraction(2)),))
    with pytest.raises(ViewRefusal) as raised:
        split_factor(date(2026, 6, 9), revisions, datetime(2026, 6, 20), mic="XNYS")
    assert raised.value.reason is RefusalReason.NAIVE_TIMESTAMP
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_raw": 100}], revisions, datetime(2026, 6, 20), mic="XNYS")
    assert raised.value.reason is RefusalReason.NAIVE_TIMESTAMP


# ── source immutability ──────────────────────────────────────────────────────

def test_inputs_are_never_mutated() -> None:
    rows = [
        {"date": date(2026, 6, 9), "open_raw": 99, "close_raw": 100, "volume_raw": 3},
        {"date": date(2026, 6, 10), "close_raw": 50},
    ]
    revisions = ActionRevisionSet(
        "immutable",
        (split("s1", Fraction(2)), cash("d1", Fraction(1, 4), ex_date=date(2026, 6, 12))),
    )
    rows_before = copy.deepcopy(rows)
    events_before = copy.deepcopy(revisions.events)
    sadj_view(rows, revisions, AS_AT, mic="XNYS")
    raw_view(rows)
    assert rows == rows_before
    assert revisions.events == events_before
    # the recorded originals are the very same objects — nothing was rewritten
    assert revisions.resolve(AS_AT)[0] is revisions.events[0]
    assert revisions.resolve(AS_AT)[1] is revisions.events[1]


# ═════════════════════════════════════════════════════════════════════════════
# Lane O2-P04 — house TOTAL_RETURN: holding plus cash under a declared policy
# (D00.D3).  Every expected number below was computed by hand from the D00.D3
# house-TOTAL_RETURN row, never by calling the function under test; each vector
# is pinned against BOTH the literal AND the independent oracle below, which
# lives in this file only and is never imported from lib.
# ═════════════════════════════════════════════════════════════════════════════


def holding_oracle(p0, p1, q0, split, cps):
    """TEST-ONLY independent oracle: first principles, nothing from lib.

    ``split`` is the cumulative split factor over the window and ``cps`` the
    cash per POST-SPLIT share actually received, so ``q1 = q0*split`` and
    ``cash = q1*cps`` — the split-first convention V07 pins.  Returns
    ``(q1, cash, wealth0, wealth1, holding_return, raw_return)`` with
    ``wealth0 = q0*p0`` and ``wealth1 = q1*p1 + cash``.
    """
    q1 = q0 * split
    cash = q1 * cps
    wealth0 = q0 * p0
    wealth1 = q1 * p1 + cash
    return q1, cash, wealth0, wealth1, wealth1 / wealth0 - 1, p1 / p0 - 1


#: The declared default policy of the vectors below: USD, no withholding
#: (DECLARED as Fraction(0), never assumed), cash held as cash.
POLICY = TotalReturnPolicy(ReinvestPolicy.NONE, Fraction(0), "USD")

#: t0 2026-06-09 (close 100), ex_date 2026-06-10, t1 2026-06-11 (close 98).
V_ROWS = [
    {"date": date(2026, 6, 9), "close_raw": 100},
    {"date": date(2026, 6, 11), "close_raw": 98},
]


def p04_cash(
    event_id: str,
    per_share,
    *,
    ex_date: date = EX_DAY,
    known_at: datetime = known(2026, 1, 1),
    qualification: str = "CONFIRMED",
    cash_basis: str | None = "as_declared",
    currency: str | None = "USD",
    sequence: int | None = None,
) -> ActionEvent:
    """A CONFIRMED cash dividend with overridable basis/currency (P02's
    ``cash()`` helper fixes them, so the P04 refusals need their own)."""
    return ActionEvent(
        event_id=event_id,
        family=ActionFamily.CASH_DIVIDEND,
        ex_date=ex_date,
        known_at=known_at,
        source_receipt=f"rcpt:{event_id}",
        qualification=qualification,
        ratio=None,
        cash_per_share=per_share,
        cash_basis=cash_basis,
        currency=currency,
        sequence=sequence,
    )


def _vector(view, oracle_tuple) -> None:
    """Assert the view's six numbers against BOTH themselves and the oracle."""
    produced = (
        view.q1,
        view.cash,
        view.wealth0,
        view.wealth1,
        view.holding_return,
        view.raw_price_return,
    )
    assert produced == oracle_tuple
    for value in produced:
        assert isinstance(value, Fraction), (value, type(value))


# ── V06 — cash held as cash exactly offsets the price drop ───────────────────

def test_V06_no_split_cash_2_holding_return_zero_raw_minus_1_50() -> None:
    """p0 100, p1 98, q0 1, cps 2 held as cash: wealth 100 both ends, hr 0."""
    revisions = ActionRevisionSet("v06", (p04_cash("d1", Fraction(2)),))
    view = total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert view.q1 == Fraction(1)
    assert view.cash == Fraction(2)
    assert view.wealth0 == Fraction(100)
    assert view.wealth1 == Fraction(100)  # 1*98 + 2
    assert view.holding_return == Fraction(0)
    assert view.raw_price_return == Fraction(-1, 50)  # 98/100 - 1
    _vector(view, holding_oracle(Fraction(100), Fraction(98), Fraction(1), Fraction(1), Fraction(2)))
    # shape: never executable, reference names basis/revision-set/as_at, and
    # the cash event states the share basis it acted on (1, no split)
    assert view.executable is False
    assert view.policy == POLICY
    assert view.reference == AdjustmentReference("total_return", "v06", AS_AT)
    assert view.events_applied == (("d1", ActionFamily.CASH_DIVIDEND, Fraction(1)),)


# ── V07 — same-ex-date split first, then cash on the NEW shares ───────────────

def test_V07_split_2_then_cash_1_per_new_share_on_the_same_ex_date() -> None:
    """p0 100, p1 49, split 2 (seq 1) then cps 1 per NEW share (seq 2)."""
    revisions = ActionRevisionSet(
        "v07",
        (split("s1", Fraction(2), sequence=1), p04_cash("d1", Fraction(1), sequence=2)),
    )
    view = total_return_view(
        V_ROWS[:1] + [{"date": date(2026, 6, 11), "close_raw": 49}],
        revisions,
        AS_AT,
        POLICY,
        mic="XNYS",
    )
    assert view.q1 == Fraction(2)
    assert view.cash == Fraction(2)  # 2 new shares x 1 per new share
    assert view.wealth0 == Fraction(100)
    assert view.wealth1 == Fraction(100)  # 2*49 + 2
    assert view.holding_return == Fraction(0)
    assert view.raw_price_return == Fraction(-51, 100)  # 49/100 - 1
    _vector(view, holding_oracle(Fraction(100), Fraction(49), Fraction(1), Fraction(2), Fraction(1)))
    # the view states the cash used the POST-split share basis 2 (D00.D3 V07)
    assert view.events_applied == (
        ("s1", ActionFamily.FORWARD_SPLIT, Fraction(1)),
        ("d1", ActionFamily.CASH_DIVIDEND, Fraction(2)),
    )


def test_V07_contrast_cash_on_the_OLD_count_differs_and_the_view_says_so() -> None:
    """Sequences swapped (cash seq 1, split seq 2): cash 1 on the OLD count —
    a different economic fact, not a rounding of the same one (P04.02)."""
    revisions = ActionRevisionSet(
        "v07-old",
        (p04_cash("d1", Fraction(1), sequence=1), split("s1", Fraction(2), sequence=2)),
    )
    view = total_return_view(
        V_ROWS[:1] + [{"date": date(2026, 6, 11), "close_raw": 49}],
        revisions,
        AS_AT,
        POLICY,
        mic="XNYS",
    )
    assert view.q1 == Fraction(2)
    assert view.cash == Fraction(1)  # 1 old share x 1 per old share
    assert view.wealth1 == Fraction(99)  # 2*49 + 1
    assert view.holding_return == Fraction(-1, 100)
    _vector(view, holding_oracle(Fraction(100), Fraction(49), Fraction(1), Fraction(2), Fraction(1, 2)))
    # events_applied records the OLD basis on the cash event
    assert view.events_applied == (
        ("d1", ActionFamily.CASH_DIVIDEND, Fraction(1)),
        ("s1", ActionFamily.FORWARD_SPLIT, Fraction(1)),
    )


# ── the EX_DATE_CLOSE and withholding controls ───────────────────────────────

def test_EX_DATE_CLOSE_control_reinvests_at_the_printed_ex_date_close() -> None:
    """p0 100, cash 2/share, ex-date close 98 == p1 -> q1 = 50/49, cash 0,
    wealth 100, hr 0.  Wealth matches the carry-cash oracle exactly because
    the reinvestment price IS p1 here: (2/98)*98 == 2."""
    rows = [
        {"date": date(2026, 6, 9), "close_raw": 100},
        {"date": EX_DAY, "close_raw": 98},  # ex_date row, also t1
    ]
    revisions = ActionRevisionSet("exclose", (p04_cash("d1", Fraction(2)),))
    policy = TotalReturnPolicy(ReinvestPolicy.EX_DATE_CLOSE, Fraction(0), "USD")
    view = total_return_view(rows, revisions, AS_AT, policy, mic="XNYS")
    assert view.q1 == Fraction(50, 49)  # 1 + 2/98
    assert view.cash == Fraction(0)
    assert view.wealth0 == Fraction(100)
    assert view.wealth1 == Fraction(100)  # (50/49)*98
    assert view.holding_return == Fraction(0)
    assert view.raw_price_return == Fraction(-1, 50)
    oracle = holding_oracle(Fraction(100), Fraction(98), Fraction(1), Fraction(1), Fraction(2))
    assert (view.wealth0, view.wealth1, view.holding_return, view.raw_price_return) == oracle[2:]


def test_withholding_control_three_tenths_leaves_seven_tenths_of_the_cash() -> None:
    """V06 with withholding 3/10 declared: cash 7/5, wealth1 497/5, hr -3/500.
    The oracle sees the net-of-withholding cash per share 2*(1-3/10)=7/5."""
    revisions = ActionRevisionSet("v06w", (p04_cash("d1", Fraction(2)),))
    policy = TotalReturnPolicy(ReinvestPolicy.NONE, Fraction(3, 10), "USD")
    view = total_return_view(V_ROWS, revisions, AS_AT, policy, mic="XNYS")
    assert view.q1 == Fraction(1)
    assert view.cash == Fraction(7, 5)  # 1 * 2 * (1 - 3/10)
    assert view.wealth0 == Fraction(100)
    assert view.wealth1 == Fraction(497, 5)  # 98 + 7/5
    assert view.holding_return == Fraction(-3, 500)
    assert view.raw_price_return == Fraction(-1, 50)
    _vector(view, holding_oracle(Fraction(100), Fraction(98), Fraction(1), Fraction(1), Fraction(7, 5)))


# ── P04.01 — a total-return question declares its policy or refuses ──────────

def test_P04_01_missing_reinvest_refuses_UNKNOWN_REINVESTMENT() -> None:
    with pytest.raises(ViewRefusal) as raised:
        TotalReturnPolicy(None, Fraction(0), "USD")
    assert raised.value.reason is RefusalReason.UNKNOWN_REINVESTMENT
    with pytest.raises(ViewRefusal) as raised:
        TotalReturnPolicy("monthly", Fraction(0), "USD")  # no such policy
    assert raised.value.reason is RefusalReason.UNKNOWN_REINVESTMENT
    with pytest.raises(TypeError):
        total_return_view(V_ROWS, EMPTY, AS_AT, None, mic="XNYS")  # not a policy at all


def test_P04_01_missing_withholding_refuses_UNKNOWN_WITHHOLDING() -> None:
    with pytest.raises(ViewRefusal) as raised:
        TotalReturnPolicy(ReinvestPolicy.NONE, None, "USD")
    assert raised.value.reason is RefusalReason.UNKNOWN_WITHHOLDING
    # declared zero — the lawful "none" — is exactly what POLICY carries, and
    # V06 above answered on it


def test_P04_01_missing_or_empty_currency_refuses_UNKNOWN_FX() -> None:
    with pytest.raises(ViewRefusal) as raised:
        TotalReturnPolicy(ReinvestPolicy.NONE, Fraction(0), None)
    assert raised.value.reason is RefusalReason.UNKNOWN_FX
    with pytest.raises(ViewRefusal) as raised:
        TotalReturnPolicy(ReinvestPolicy.NONE, Fraction(0), "")
    assert raised.value.reason is RefusalReason.UNKNOWN_FX


def test_P04_01_withholding_rate_outside_the_unit_interval_refuses_UNKNOWN_WITHHOLDING() -> None:
    for bad in (Fraction(1), Fraction(3, 2), Fraction(-1, 10)):
        with pytest.raises(ViewRefusal) as raised:
            TotalReturnPolicy(ReinvestPolicy.NONE, bad, "USD")
        assert raised.value.reason is RefusalReason.UNKNOWN_WITHHOLDING


def test_P04_01_float_withholding_refuses_NON_EXACT_INPUT() -> None:
    with pytest.raises(ViewRefusal) as raised:
        TotalReturnPolicy(ReinvestPolicy.NONE, 0.15, "USD")
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT
    with pytest.raises(ViewRefusal) as raised:
        TotalReturnPolicy(ReinvestPolicy.NONE, True, "USD")  # bool is not exact
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT


# ── P04.02 — original cash, adjusted cash and a price factor are three facts ─

def test_P04_02_cash_in_another_currency_refuses_UNKNOWN_FX() -> None:
    revisions = ActionRevisionSet("fx", (p04_cash("d1", Fraction(2), currency="EUR"),))
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.CURRENCY_MISMATCH
    assert raised.value.event_id == "d1"


def test_P04_02_cash_without_a_currency_refuses_UNKNOWN_FX() -> None:
    revisions = ActionRevisionSet("fxnone", (p04_cash("d1", Fraction(2), currency=None),))
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.UNKNOWN_FX


def test_P04_02_current_share_adjusted_cash_refuses_CASH_BASIS_MISMATCH() -> None:
    revisions = ActionRevisionSet(
        "csa", (p04_cash("d1", Fraction(2), cash_basis="current_share_adjusted"),)
    )
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.CASH_BASIS_MISMATCH
    assert raised.value.event_id == "d1"


def test_P04_02_cash_without_an_amount_refuses_UNKNOWN_RATIO() -> None:
    revisions = ActionRevisionSet("noamount", (p04_cash("d1", None),))
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.UNKNOWN_RATIO


def test_P04_02_cash_price_factor_distinction_no_cash_ever_enters_the_price() -> None:
    """The same window through SADJ shows the price unchanged by cash; the
    total-return view carries the cash separately.  Neither mimics the other."""
    revisions = ActionRevisionSet("twoviews", (p04_cash("d1", Fraction(2)),))
    price = sadj_view(V_ROWS, revisions, AS_AT, mic="XNYS")
    holding = total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert [row["close_sadj"] for row in price.rows] == [Fraction(100), Fraction(98)]
    assert holding.cash == Fraction(2)  # carried, not folded into any price


# ── P04.03 — unknown ordering / unsupported events / missing prices ──────────

def test_P04_03_same_day_split_and_cash_without_sequences_refuses_UNKNOWN_ORDERING() -> None:
    revisions = ActionRevisionSet(
        "noorder", (split("s1", Fraction(2)), p04_cash("d1", Fraction(1)))
    )
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.UNKNOWN_ORDERING
    # equal sequences are equally unordered — never a guess
    equal = ActionRevisionSet(
        "eqorder",
        (split("s1", Fraction(2), sequence=1), p04_cash("d1", Fraction(1), sequence=1)),
    )
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, equal, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.UNKNOWN_ORDERING


def test_P04_03_unsupported_family_in_window_refuses_UNSUPPORTED_ACTION() -> None:
    spin_off = ActionEvent(
        event_id="u1",
        family=ActionFamily.SPIN_OFF,
        ex_date=EX_DAY,
        known_at=known(2026, 1, 1),
        source_receipt="rcpt:u1",
        qualification="CONFIRMED",
        ratio=None,
    )
    revisions = ActionRevisionSet("unsup", (spin_off,))
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.UNSUPPORTED_ACTION
    assert raised.value.event_id == "u1"


def test_P04_03_EX_DATE_CLOSE_without_a_row_on_ex_date_refuses_MISSING_PRICE() -> None:
    revisions = ActionRevisionSet("missing", (p04_cash("d1", Fraction(2)),))
    policy = TotalReturnPolicy(ReinvestPolicy.EX_DATE_CLOSE, Fraction(0), "USD")
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, policy, mic="XNYS")  # no 2026-06-10 row
    assert raised.value.reason is RefusalReason.MISSING_PRICE
    assert raised.value.event_id == "d1"
    # holding cash needs no price: the SAME data answers under NONE
    view = total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert view.cash == Fraction(2)


def test_P04_03_unconfirmed_cash_in_window_refuses_NOT_CONFIRMED() -> None:
    revisions = ActionRevisionSet(
        "suspect", (p04_cash("d1", Fraction(2), qualification="SUSPECTED"),)
    )
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.NOT_CONFIRMED


# ── P04.04 — never executable, in either house ───────────────────────────────

def test_P04_04_TotalReturnView_executable_True_and_TRADJ_PriceView_refuse() -> None:
    with pytest.raises(ViewRefusal) as raised:
        TotalReturnView(
            wealth0=Fraction(100),
            q1=Fraction(1),
            cash=Fraction(0),
            wealth1=Fraction(98),
            holding_return=Fraction(-1, 50),
            raw_price_return=Fraction(-1, 50),
            policy=POLICY,
            reference=AdjustmentReference("total_return", None, None),
            executable=True,
        )
    assert raised.value.reason is RefusalReason.NOT_EXECUTABLE_BASIS
    # a TRADJ-basis PriceView (the vendor proxy this view exists to not be)
    # is equally never executable — no executable total-return anything
    with pytest.raises(ViewRefusal) as raised:
        PriceView(
            basis="TRADJ",
            rows=(),
            reference=AdjustmentReference("TRADJ", None, None),
            executable=True,
        )
    assert raised.value.reason is RefusalReason.NOT_EXECUTABLE_BASIS


# ── the column law and exactness, carried from P02 into P04 ─────────────────

def test_P04_column_law_tradj_input_refuses_NON_RAW_INPUT() -> None:
    rows = [
        {"date": date(2026, 6, 9), "close_tradj": Fraction(100)},
        {"date": date(2026, 6, 11), "close_tradj": Fraction(98)},
    ]
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(rows, EMPTY, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.NON_RAW_INPUT
    assert raised.value.column == "close_tradj"


def test_P04_column_law_sadj_input_refuses_DOUBLE_ADJUST_RISK() -> None:
    rows = [
        {"date": date(2026, 6, 9), "close_sadj": Fraction(100)},
        {"date": date(2026, 6, 11), "close_sadj": Fraction(98)},
    ]
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(rows, EMPTY, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.DOUBLE_ADJUST_RISK


def test_P04_float_close_refuses_NON_EXACT_INPUT() -> None:
    rows = [
        {"date": date(2026, 6, 9), "close_raw": 100.0},
        {"date": date(2026, 6, 11), "close_raw": 98},
    ]
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(rows, EMPTY, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT


# ── holding scale and window boundaries ──────────────────────────────────────

def test_q0_scales_the_holding_and_float_q0_refuses() -> None:
    """V06 with q0 = 10: every wealth x10, every return unchanged."""
    revisions = ActionRevisionSet("q0", (p04_cash("d1", Fraction(2)),))
    view = total_return_view(V_ROWS, revisions, AS_AT, POLICY, q0=10, mic="XNYS")
    _vector(
        view,
        holding_oracle(Fraction(100), Fraction(98), Fraction(10), Fraction(1), Fraction(2)),
    )
    assert view.cash == Fraction(20)
    assert view.holding_return == Fraction(0)
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, POLICY, q0=1.5, mic="XNYS")
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT


def test_events_outside_the_window_never_touch_the_holding() -> None:
    revisions = ActionRevisionSet(
        "outside",
        (
            p04_cash("d0", Fraction(5), ex_date=date(2026, 6, 9)),   # == t0: outside (t0 < ex_date)
            p04_cash("d2", Fraction(7), ex_date=date(2026, 6, 12)),  # > t1: outside
            split("s2", Fraction(2), ex_date=date(2026, 6, 12)),     # > t1: outside
        ),
    )
    view = total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert view.events_applied == ()
    assert view.q1 == Fraction(1)
    assert view.cash == Fraction(0)
    assert view.holding_return == view.raw_price_return == Fraction(-1, 50)
    # even an UNSUPPORTED family outside the window never blocks the view
    spin_off = ActionEvent(
        event_id="u2",
        family=ActionFamily.MERGER,
        ex_date=date(2026, 6, 12),
        known_at=known(2026, 1, 1),
        source_receipt="rcpt:u2",
        qualification="CONFIRMED",
        ratio=None,
    )
    beyond = ActionRevisionSet("beyond", revisions.events + (spin_off,))
    assert total_return_view(V_ROWS, beyond, AS_AT, POLICY, mic="XNYS").cash == Fraction(0)


# ── R02 heal (M1 m1 m2 m4) — refusals the first review found missing ──────
def test_R02_M1_duplicate_event_id_refuses_in_sadj_view() -> None:
    revisions = ActionRevisionSet("dup", (split("s1", Fraction(2)), split("s1", Fraction(2))))
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_raw": 100}], revisions, AS_AT, mic="XNYS")
    assert raised.value.reason is RefusalReason.DUPLICATE_EVENT_ID
    assert raised.value.event_id == "s1"


def test_R02_m1_raw_view_refuses_a_float_price() -> None:
    with pytest.raises(ViewRefusal) as raised:
        raw_view([{"date": date(2026, 6, 9), "close_raw": 100.25}])
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT
    assert raised.value.column == "close_raw"


@pytest.mark.parametrize("name", ["adjusted_close", "Adj Close"])
def test_R02_m1_raw_view_refuses_a_price_like_unknown_column(name: str) -> None:
    with pytest.raises(ViewRefusal) as raised:
        raw_view([{"date": date(2026, 6, 9), "close_raw": 100, name: 99}])
    assert raised.value.reason is RefusalReason.AMBIGUOUS_BASIS
    assert raised.value.column == name


def test_R02_m1_raw_view_values_are_exact_fractions_and_inputs_untouched() -> None:
    rows = [
        {
            "date": date(2026, 6, 9),
            "close_raw": Decimal("100.25"),
            "open_raw": "99.5",
            "volume_raw": 3,
            "note": "x",
        }
    ]
    before = copy.deepcopy(rows)
    out = raw_view(rows).rows[0]
    assert out["close_raw"] == Fraction(401, 4)
    assert out["open_raw"] == Fraction(199, 2)
    assert out["volume_raw"] == Fraction(3)
    assert all(type(out[key]) is Fraction for key in ("close_raw", "open_raw", "volume_raw"))
    assert out["note"] == "x"
    assert out["date"] == date(2026, 6, 9)
    assert rows == before
    assert type(rows[0]["close_raw"]) is Decimal and rows[0]["open_raw"] == "99.5"


def test_R02_m1_non_price_columns_pass_through_unchanged() -> None:
    row = {
        "date": date(2026, 6, 9),
        "close_raw": 100,
        "close_time": "16:00",
        "last_updated": "2026-06-09T20:00:00Z",
        "open_interest": 12,
        "volume_raw": 5,
    }
    out = raw_view([row]).rows[0]
    for key in ("close_time", "last_updated", "open_interest"):
        assert out[key] == row[key]
    sadj_view([row], ActionRevisionSet("guard", (split("s1", Fraction(2)),)), AS_AT, mic="XNYS")


def test_R02_m2_sadj_view_refuses_a_row_after_as_at() -> None:
    revisions = ActionRevisionSet("late", (split("s1", Fraction(2)),))
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 21), "close_raw": 100}], revisions, AS_AT, mic="XNYS")
    assert raised.value.reason is RefusalReason.ROW_AFTER_AS_AT
    assert raised.value.column == "date"
    view = sadj_view([{"date": date(2026, 6, 19), "close_raw": 100}], revisions, AS_AT, mic="XNYS")
    assert view.rows[0]["close_sadj"] == Fraction(100)


def test_R02_m4_non_positive_inputs_refuse_typed() -> None:
    cases = [
        (qualified_return, (0, 10, 1, 1)),
        (qualified_return, (-5, 10, 1, 1)),
        (qualified_return, (100, 90, 0, 0)),
        (return_vector, (0, 10, 1, 1)),
        (return_vector, (100, 90, 0, 1)),
    ]
    for fn, args in cases:
        with pytest.raises(ViewRefusal) as raised:
            fn(*args)
        assert raised.value.reason is RefusalReason.NON_POSITIVE_VALUE, (fn.__name__, args)


def test_R02_m4_a_zero_end_price_is_a_total_loss_not_a_refusal() -> None:
    assert qualified_return(100, 0, 1, 1) == Fraction(-1)
    assert return_vector(100, 0, 1, 1)["original"] == Fraction(-1)


# ── R02 heal of the total-return view (M2 m2 m4 m5) ──────────────────────────

def test_R02_P04_M2_cash_before_a_same_day_split_buys_post_split_shares() -> None:
    """p0 100; cash 2 per OLD share (seq 1), then split 2 (seq 2); ex-date close
    49.  The close prints after the split: 2/49 post-split shares, wealth 100."""
    rows = [{"date": date(2026, 6, 9), "close_raw": 100}, {"date": EX_DAY, "close_raw": 49}]
    revisions = ActionRevisionSet(
        "r02m2", (p04_cash("d1", Fraction(2), sequence=1), split("s1", Fraction(2), sequence=2))
    )
    policy = TotalReturnPolicy(ReinvestPolicy.EX_DATE_CLOSE, Fraction(0), "USD")
    view = total_return_view(rows, revisions, AS_AT, policy, mic="XNYS")
    assert view.q1 == Fraction(100, 49)  # 1 -> split -> 2, + 2/49 bought at the close
    assert view.cash == Fraction(0)
    assert view.wealth0 == Fraction(100)
    assert view.wealth1 == Fraction(100)
    assert view.holding_return == Fraction(0)
    assert view.raw_price_return == Fraction(-51, 100)
    assert view.events_applied == (
        ("d1", ActionFamily.CASH_DIVIDEND, Fraction(1)),
        ("s1", ActionFamily.FORWARD_SPLIT, Fraction(1)),
    )


def test_R02_P04_M2_shares_bought_at_the_close_carry_no_later_same_day_cash() -> None:
    """cash 2 per old share (seq 1), split 2 (seq 2), cash 1 per new share
    (seq 3); ex-date close 48: (2 + 2*1)/48 bought at the close, wealth 100."""
    rows = [{"date": date(2026, 6, 9), "close_raw": 100}, {"date": EX_DAY, "close_raw": 48}]
    revisions = ActionRevisionSet(
        "r02m2b",
        (
            p04_cash("d1", Fraction(2), sequence=1),
            split("s1", Fraction(2), sequence=2),
            p04_cash("d3", Fraction(1), sequence=3),
        ),
    )
    policy = TotalReturnPolicy(ReinvestPolicy.EX_DATE_CLOSE, Fraction(0), "USD")
    view = total_return_view(rows, revisions, AS_AT, policy, mic="XNYS")
    assert view.q1 == Fraction(25, 12)  # 2 + 4/48
    assert view.cash == Fraction(0)
    assert view.wealth1 == Fraction(100)
    assert view.holding_return == Fraction(0)
    assert view.raw_price_return == Fraction(-13, 25)
    assert view.events_applied == (
        ("d1", ActionFamily.CASH_DIVIDEND, Fraction(1)),
        ("s1", ActionFamily.FORWARD_SPLIT, Fraction(1)),
        ("d3", ActionFamily.CASH_DIVIDEND, Fraction(2)),
    )


def test_R02_P04_M2_guard_split_first_then_cash_is_unchanged() -> None:
    """split 2 (seq 1), then cash 1 per NEW share (seq 2), ex-date close 49."""
    rows = [{"date": date(2026, 6, 9), "close_raw": 100}, {"date": EX_DAY, "close_raw": 49}]
    revisions = ActionRevisionSet(
        "r02m2g", (split("s1", Fraction(2), sequence=1), p04_cash("d1", Fraction(1), sequence=2))
    )
    policy = TotalReturnPolicy(ReinvestPolicy.EX_DATE_CLOSE, Fraction(0), "USD")
    view = total_return_view(rows, revisions, AS_AT, policy, mic="XNYS")
    assert view.q1 == Fraction(100, 49)
    assert view.wealth1 == Fraction(100)
    assert view.holding_return == Fraction(0)
    assert view.events_applied == (
        ("s1", ActionFamily.FORWARD_SPLIT, Fraction(1)),
        ("d1", ActionFamily.CASH_DIVIDEND, Fraction(2)),
    )


def test_R02_P04_m5_two_rows_on_one_date_refuse() -> None:
    rows = [
        {"date": date(2026, 6, 9), "close_raw": 100},
        {"date": date(2026, 6, 11), "close_raw": 98},
        {"date": date(2026, 6, 11), "close_raw": 97},
    ]
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(rows, EMPTY, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.DUPLICATE_ROW_DATE
    assert raised.value.column == "date"


def test_R02_P04_m2_a_row_after_as_at_refuses() -> None:
    rows = [{"date": date(2026, 6, 9), "close_raw": 100}, {"date": date(2026, 6, 21), "close_raw": 98}]
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(rows, EMPTY, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.ROW_AFTER_AS_AT
    assert raised.value.column == "date"


def test_R02_P04_m2_guard_a_row_on_the_as_at_date_is_lawful() -> None:
    rows = [{"date": date(2026, 6, 9), "close_raw": 100}, {"date": date(2026, 6, 19), "close_raw": 98}]
    view = total_return_view(rows, EMPTY, AS_AT, POLICY, mic="XNYS")
    assert view.holding_return == Fraction(-1, 50)


def test_R02_P04_m4_non_positive_q0_or_p0_refuse_typed() -> None:
    for q0 in (0, -1):
        with pytest.raises(ViewRefusal) as raised:
            total_return_view(V_ROWS, EMPTY, AS_AT, POLICY, q0=q0, mic="XNYS")
        assert raised.value.reason is RefusalReason.NON_POSITIVE_VALUE, q0
        assert raised.value.column is None
    for p0 in (0, -5):
        rows = [{"date": date(2026, 6, 9), "close_raw": p0}, {"date": date(2026, 6, 11), "close_raw": 98}]
        with pytest.raises(ViewRefusal) as raised:
            total_return_view(rows, EMPTY, AS_AT, POLICY, mic="XNYS")
        assert raised.value.reason is RefusalReason.NON_POSITIVE_VALUE, p0
        assert raised.value.column == "close_raw"


# ── P06 — venue-local as_at day + declared currency (D00.A1) ──

from lib.dataos.identity import IdentityError
from lib.dataos.price_views import ViewVintage, view_label

#: A lawful 40-char lowercase-hex code version for the P06 vintage witness.
P06_CODE = "c0dec0de" * 5


def test_P06_falsifier_us_split_not_effective_before_the_ny_session() -> None:
    """D00.A1.1 falsifier: a 2:1 split ex 2026-06-10 with as_at 2026-06-10T02:00Z
    (22:00 ET on 06-09) — the NY venue day is 06-09, so S(06-09) = 1: the tape
    has not split yet.  The UTC-date rule would answer 2."""
    revisions = ActionRevisionSet(
        "p06-falsifier", (split("f1", Fraction(2), known_at=known(2026, 6, 1)),)
    )
    as_at = datetime(2026, 6, 10, 2, 0, tzinfo=UTC)
    assert split_factor(date(2026, 6, 9), revisions, as_at, mic="XNYS") == Fraction(1)


def test_P06_falsifier_total_return_row_on_the_utc_day_is_after_the_venue_day() -> None:
    """At that same as_at a row dated 06-10 (the UTC day) is AFTER the NY venue
    day 06-09 — an as-of view cannot carry a price printed later."""
    revisions = ActionRevisionSet(
        "p06-falsifier-tr", (split("f1", Fraction(2), known_at=known(2026, 6, 1)),)
    )
    as_at = datetime(2026, 6, 10, 2, 0, tzinfo=UTC)
    rows = [
        {"date": date(2026, 6, 9), "close_raw": 100},
        {"date": date(2026, 6, 10), "close_raw": 98},
    ]
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(rows, revisions, as_at, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.ROW_AFTER_AS_AT
    assert raised.value.column == "date"


def test_P06_mic_is_required_keyword_only() -> None:
    revisions = ActionRevisionSet("p06-kw", (split("s1", Fraction(2)),))
    with pytest.raises(TypeError):
        split_factor(date(2026, 6, 9), revisions, AS_AT)
    with pytest.raises(TypeError):
        sadj_view([{"date": date(2026, 6, 9), "close_raw": 100}], revisions, AS_AT)
    with pytest.raises(TypeError):
        total_return_view(V_ROWS, EMPTY, AS_AT, POLICY)


def test_P06_unknown_or_none_mic_refuses_VENUE_CLOCK_UNKNOWN() -> None:
    revisions = ActionRevisionSet("p06-mic", (split("s1", Fraction(2)),))
    rows = [{"date": date(2026, 6, 9), "close_raw": 100}]
    for bad in (None, "XXXX"):
        checks = (
            lambda: split_factor(date(2026, 6, 9), revisions, AS_AT, mic=bad),
            lambda: sadj_view(rows, revisions, AS_AT, mic=bad),
            lambda: total_return_view(V_ROWS, EMPTY, AS_AT, POLICY, mic=bad),
        )
        for check in checks:
            with pytest.raises(ViewRefusal) as raised:
                check()
            assert raised.value.reason is RefusalReason.VENUE_CLOCK_UNKNOWN
            assert not isinstance(raised.value, IdentityError)
    with pytest.raises(ViewRefusal) as raised:
        raw_view(rows, mic="XXXX")
    assert raised.value.reason is RefusalReason.VENUE_CLOCK_UNKNOWN
    assert not isinstance(raised.value, IdentityError)


@pytest.mark.parametrize(
    "mic, ex_date, t, as_at, expected, known_at",
    [
        # summer rows (known_at a week before ex 2026-06-10)
        ("XHKG", date(2026, 6, 10), date(2026, 6, 9), datetime(2026, 6, 9, 16, 30, tzinfo=UTC), Fraction(2), known(2026, 6, 3)),
        ("XHKG", date(2026, 6, 10), date(2026, 6, 9), datetime(2026, 6, 9, 15, 30, tzinfo=UTC), Fraction(1), known(2026, 6, 3)),
        ("XTSE", date(2026, 6, 10), date(2026, 6, 9), datetime(2026, 6, 10, 3, 59, tzinfo=UTC), Fraction(1), known(2026, 6, 3)),
        ("XTSE", date(2026, 6, 10), date(2026, 6, 9), datetime(2026, 6, 10, 4, 0, tzinfo=UTC), Fraction(2), known(2026, 6, 3)),
        ("XSHG", date(2026, 6, 10), date(2026, 6, 9), datetime(2026, 6, 9, 16, 0, tzinfo=UTC), Fraction(2), known(2026, 6, 3)),
        ("XSHG", date(2026, 6, 10), date(2026, 6, 9), datetime(2026, 6, 9, 15, 59, 59, tzinfo=UTC), Fraction(1), known(2026, 6, 3)),
        # winter rows (EST, known_at 2025-12-01)
        ("XNYS", date(2026, 1, 15), date(2026, 1, 14), datetime(2026, 1, 15, 4, 59, tzinfo=UTC), Fraction(1), known(2025, 12, 1)),
        ("XNYS", date(2026, 1, 15), date(2026, 1, 14), datetime(2026, 1, 15, 5, 0, tzinfo=UTC), Fraction(2), known(2025, 12, 1)),
    ],
)
def test_P06_venue_day_boundary_table(mic, ex_date, t, as_at, expected, known_at) -> None:
    """S(t) flips exactly at the venue-local midnight of the ex_date, never at
    the UTC date (D00.A1.1): each pair straddles the venue's midnight."""
    revisions = ActionRevisionSet(
        "p06-table", (split("s1", Fraction(2), ex_date=ex_date, known_at=known_at),)
    )
    assert split_factor(t, revisions, as_at, mic=mic) == expected


def test_P06_row_on_the_utc_as_at_date_is_after_the_ny_venue_day() -> None:
    """AS_AT 2026-06-20T00:00Z is 20:00 ET on 06-19: the NY venue day is 06-19,
    so a row dated 06-20 (the UTC day) refuses ROW_AFTER_AS_AT in BOTH views —
    the twins of the two re-expressed R02 guards (§8.7)."""
    revisions = ActionRevisionSet("p06-twins", (split("s1", Fraction(2)),))
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 20), "close_raw": 100}], revisions, AS_AT, mic="XNYS")
    assert raised.value.reason is RefusalReason.ROW_AFTER_AS_AT
    rows = [{"date": date(2026, 6, 9), "close_raw": 100}, {"date": date(2026, 6, 20), "close_raw": 98}]
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(rows, EMPTY, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.ROW_AFTER_AS_AT


def test_P06_policy_currency_mismatch() -> None:
    cad = TotalReturnPolicy(ReinvestPolicy.NONE, Fraction(0), "CAD")
    revisions = ActionRevisionSet("p06-pcy", (split("s1", Fraction(2)),))
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, cad, mic="XNYS")
    assert raised.value.reason is RefusalReason.CURRENCY_MISMATCH


def test_P06_row_currency_column() -> None:
    revisions = ActionRevisionSet("p06-rowcur", (split("s1", Fraction(2)),))
    base = {"date": date(2026, 6, 9), "close_raw": 100}
    # a row currency equal (case-insensitively) to the declared one is accepted
    view = sadj_view([dict(base, currency="usd")], revisions, AS_AT, mic="XNYS")
    assert view.rows[0]["close_sadj"] == Fraction(50)
    for bad, reason in (
        ("EUR", RefusalReason.CURRENCY_MISMATCH),
        (None, RefusalReason.UNKNOWN_FX),
    ):
        with pytest.raises(ViewRefusal) as raised:
            sadj_view([dict(base, currency=bad)], revisions, AS_AT, mic="XNYS")
        assert raised.value.reason is reason
        assert raised.value.column == "currency"
    tr_rows = [
        {"date": date(2026, 6, 9), "close_raw": 100, "currency": "usd"},
        {"date": date(2026, 6, 11), "close_raw": 98, "currency": "usd"},
    ]
    assert total_return_view(tr_rows, EMPTY, AS_AT, POLICY, mic="XNYS").cash == Fraction(0)
    for bad, reason in (
        ("EUR", RefusalReason.CURRENCY_MISMATCH),
        (None, RefusalReason.UNKNOWN_FX),
    ):
        rows = [dict(tr_rows[0], currency=bad), tr_rows[1]]
        with pytest.raises(ViewRefusal) as raised:
            total_return_view(rows, EMPTY, AS_AT, POLICY, mic="XNYS")
        assert raised.value.reason is reason


def test_P06_cash_none_currency_stays_UNKNOWN_FX() -> None:
    """Positive pin of the seat ruling: a cash event whose currency is None (or
    blank) stays UNKNOWN_FX — only a known-and-different one is a mismatch."""
    revisions = ActionRevisionSet("p06-cashnone", (p04_cash("d1", Fraction(2), currency=None),))
    with pytest.raises(ViewRefusal) as raised:
        total_return_view(V_ROWS, revisions, AS_AT, POLICY, mic="XNYS")
    assert raised.value.reason is RefusalReason.UNKNOWN_FX
    assert raised.value.event_id == "d1"


def test_P06_view_currency() -> None:
    rows = [{"date": date(2026, 6, 9), "close_raw": 100}]
    revisions = ActionRevisionSet("p06-cur", (split("s1", Fraction(2)),))
    assert raw_view(rows).currency is None
    assert raw_view(rows, mic="XNYS").currency == "USD"
    assert sadj_view(rows, revisions, AS_AT, mic="XHKG").currency == "HKD"
    with pytest.raises(TypeError):
        PriceView(
            basis="RAW",
            rows=(),
            reference=AdjustmentReference("RAW", None, None),
            executable=True,
            currency=5,
        )


def test_P06_label_carries_currency() -> None:
    revisions = ActionRevisionSet("p06-label", (split("s1", Fraction(2)),))
    sadj = sadj_view([{"date": date(2026, 6, 9), "close_raw": 100}], revisions, AS_AT, mic="XNYS")
    vintage = ViewVintage("G1", "p06-label", "IDGEN-1", P06_CODE)
    assert "|currency=USD|" in view_label(sadj, vintage)
    raw = raw_view([{"date": date(2026, 6, 9), "close_raw": 100}])
    raw_vintage = ViewVintage("G1", None, "IDGEN-1", P06_CODE)
    assert "|currency=-|" in view_label(raw, raw_vintage)
