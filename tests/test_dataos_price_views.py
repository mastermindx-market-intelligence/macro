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
    ViewRefusal,
    adjust_quantity,
    qualified_return,
    raw_view,
    return_vector,
    sadj_view,
    split_factor,
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
    )
    (row,) = view.rows
    assert row["close_sadj"] == Fraction(30)
    assert row["volume_sadj"] == Fraction(3600)
    assert row["close_sadj"] * row["volume_sadj"] == Fraction(108000)

    # composition property: the chain equals ONE event of ratio 3
    single = ActionRevisionSet("v03-single", (split("s3", Fraction(3)),))
    assert split_factor(date(2026, 6, 9), chained, AS_AT) == Fraction(3)
    assert split_factor(date(2026, 6, 9), chained, AS_AT) == split_factor(
        date(2026, 6, 9), single, AS_AT
    )


def test_V03_inverse_forward_2_then_reverse_1_2_is_factor_1() -> None:
    inverse = ActionRevisionSet(
        "v03-inv",
        (
            split("s1", Fraction(2), ex_date=date(2026, 6, 10)),
            split("s2", Fraction(1, 2), ex_date=date(2026, 6, 12), family=ActionFamily.REVERSE_SPLIT),
        ),
    )
    assert split_factor(date(2026, 6, 9), inverse, AS_AT) == Fraction(1)


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
    view = sadj_view(rows, revisions, AS_AT)
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
    assert split_factor(EX_DAY - timedelta(days=1), revisions, AS_AT) == Fraction(2)
    # ... a row dated ex_date itself gets 1
    assert split_factor(EX_DAY, revisions, AS_AT) == Fraction(1)
    view = sadj_view(
        [
            {"date": date(2026, 6, 9), "close_raw": 100},
            {"date": date(2026, 6, 10), "close_raw": 100},
        ],
        revisions,
        AS_AT,
    )
    by_day = {row["date"]: row["close_sadj"] for row in view.rows}
    assert by_day[date(2026, 6, 9)] == Fraction(50)
    assert by_day[date(2026, 6, 10)] == Fraction(100)


def test_half_open_ex_date_boundary_event_after_as_at_is_not_yet_effective() -> None:
    """ex_date > as_at: the share basis at as_at is the pre-split one (D00.D3)."""
    revisions = ActionRevisionSet("future", (split("s1", Fraction(2)),))
    before = datetime(2026, 6, 5, tzinfo=UTC)
    assert split_factor(date(2026, 6, 1), revisions, before) == Fraction(1)
    view = sadj_view(
        [{"date": date(2026, 6, 1), "close_raw": 100, "volume_raw": 7}],
        revisions,
        before,
    )
    (row,) = view.rows
    assert row["close_sadj"] == Fraction(100)
    assert row["volume_sadj"] == Fraction(7)


# ── P03.02 — never adjust twice, never accept a proxy ────────────────────────

def test_P03_02_close_sadj_input_refuses_DOUBLE_ADJUST_RISK() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_sadj": Fraction(100)}], EMPTY, AS_AT)
    assert raised.value.reason is RefusalReason.DOUBLE_ADJUST_RISK
    assert raised.value.column == "close_sadj"


def test_P03_02_close_tradj_input_refuses_NON_RAW_INPUT() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_tradj": Fraction(100)}], EMPTY, AS_AT)
    assert raised.value.reason is RefusalReason.NON_RAW_INPUT
    assert raised.value.column == "close_tradj"


def test_P03_02_bare_close_refuses_AMBIGUOUS_BASIS() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close": 100}], EMPTY, AS_AT)
    assert raised.value.reason is RefusalReason.AMBIGUOUS_BASIS
    assert raised.value.column == "close"


# ── P03.03 — cash dividends never touch SADJ prices or volume ────────────────

def test_P03_03_confirmed_cash_dividend_in_window_changes_nothing() -> None:
    rows = [{"date": date(2026, 6, 9), "close_raw": 100, "volume_raw": 1000}]
    without = sadj_view(rows, EMPTY, AS_AT)
    with_cash = sadj_view(
        rows, ActionRevisionSet("cash", (cash("d1", Fraction(1, 4)),)), AS_AT
    )
    assert with_cash.rows == without.rows  # prices AND volume_sadj identical
    (row,) = with_cash.rows
    assert row["close_sadj"] == Fraction(100)
    assert row["volume_sadj"] == Fraction(1000)


# ── P03.04 — each bad value its own typed refusal ────────────────────────────

def _window_factor(event: ActionEvent):
    revisions = ActionRevisionSet("p0304", (event,))
    return split_factor(date(2026, 6, 9), revisions, AS_AT)


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
        )
    assert raised.value.reason is RefusalReason.MIXED_OHLC_BASIS


def test_P03_04_lots_convention_refuses_UNSUPPORTED_QUANTITY_CONVENTION() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view(
            [{"date": date(2026, 6, 9), "close_raw": 100, "volume_raw": 3}],
            EMPTY,
            AS_AT,
            quantity_convention="lots",
        )
    assert raised.value.reason is RefusalReason.UNSUPPORTED_QUANTITY_CONVENTION


def test_P03_04_float_price_refuses_NON_EXACT_INPUT() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_raw": 100.0}], EMPTY, AS_AT)
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT


def test_P03_04_bool_and_bogus_string_prices_refuse_NON_EXACT_INPUT() -> None:
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_raw": True}], EMPTY, AS_AT)
    assert raised.value.reason is RefusalReason.NON_EXACT_INPUT
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_raw": "cheap"}], EMPTY, AS_AT)
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
    adjusted = sadj_view(rows, ActionRevisionSet("v", (split("s1", Fraction(2)),)), AS_AT)
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
    )
    for row in view.rows:
        assert set(row) == {"date", "open_sadj", "high_sadj", "low_sadj", "close_sadj", "volume_sadj"}
        for key, value in row.items():
            if key != "date":
                assert isinstance(value, Fraction), (key, value)
    assert split_factor(date(2026, 6, 9), revisions, AS_AT) == Fraction(2)  # cash adds nothing
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
        split_factor(date(2026, 6, 9), revisions, datetime(2026, 6, 20))
    assert raised.value.reason is RefusalReason.NAIVE_TIMESTAMP
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_raw": 100}], revisions, datetime(2026, 6, 20))
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
    sadj_view(rows, revisions, AS_AT)
    raw_view(rows)
    assert rows == rows_before
    assert revisions.events == events_before
    # the recorded originals are the very same objects — nothing was rewritten
    assert revisions.resolve(AS_AT)[0] is revisions.events[0]
    assert revisions.resolve(AS_AT)[1] is revisions.events[1]


# ── R02 heal (M1 m1 m2 m4) — refusals the first review found missing ──────
def test_R02_M1_duplicate_event_id_refuses_in_sadj_view() -> None:
    revisions = ActionRevisionSet("dup", (split("s1", Fraction(2)), split("s1", Fraction(2))))
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 9), "close_raw": 100}], revisions, AS_AT)
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
    sadj_view([row], ActionRevisionSet("guard", (split("s1", Fraction(2)),)), AS_AT)


def test_R02_m2_sadj_view_refuses_a_row_after_as_at() -> None:
    revisions = ActionRevisionSet("late", (split("s1", Fraction(2)),))
    with pytest.raises(ViewRefusal) as raised:
        sadj_view([{"date": date(2026, 6, 21), "close_raw": 100}], revisions, AS_AT)
    assert raised.value.reason is RefusalReason.ROW_AFTER_AS_AT
    assert raised.value.column == "date"
    view = sadj_view([{"date": date(2026, 6, 20), "close_raw": 100}], revisions, AS_AT)
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
