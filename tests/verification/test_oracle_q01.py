"""Q01 independent exact-rational oracle for Data OS price views (lane Q01-1).

Every expected value below is produced by the Section A oracle functions,
which are derived ONLY from the frozen D00.D3 semantic text and the design
vector JSON embedded below (programme DATA-OS-COMPLETION). No SUT output was
copied into any expectation. Synthetic inputs only; no files, no network,
no clock, no entropy sources. Verification only — nothing here fixes lib/.
"""

import ast
import pathlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction

import pytest

# ==== ORACLE (D00.D3 text only — imports nothing from lib/ or engine/) ====


def oracle_split(raw_price, raw_quantity, ratios):
    """Adjusted price/quantity/wealth under chained exact split ratios."""
    # D00.D3: "P_sadj(t) = P_raw(t) / S(t; v)" with "S(t; v) = prod r_e over
    # qualified split events e with ex_date > t"; r_e is an exact rational.
    s = Fraction(1)
    for r in ratios:
        s *= Fraction(r)
    adjusted_price = Fraction(raw_price) / s
    # D00.D3: "A split changes the price/share unit, not holding wealth
    # (V01/V02)" — quantity therefore moves BY the same S, and
    # "vol_adj = vol_raw x r_e" (V03) composes to vol_raw x S.
    adjusted_quantity = Fraction(raw_quantity) * s
    wealth = adjusted_price * adjusted_quantity
    return (adjusted_price, adjusted_quantity, wealth)


def oracle_return(p0, p1, k0, k1):
    """Return with and without rebasing the two endpoints by k0/k1."""
    # D00.D3 V04: "A common scalar on both return endpoints cancels."
    # (V05: different endpoint factors do not cancel.)
    original = Fraction(p1) / Fraction(p0) - 1
    rebased = (Fraction(p1) * Fraction(k1)) / (Fraction(p0) * Fraction(k0)) - 1
    return {"original": original, "rebased": rebased, "equal": original == rebased}


def oracle_cash(cash_per_new_share, p0, p1, q0, split_ratio):
    """Holding-plus-cash answer: one ex-date between the closes, split-first
    cash declared per POST-split share, reinvest NONE, withholding 0."""
    # D00.D3: total-return share basis is the "post-event share count".
    q1 = Fraction(q0) * Fraction(split_ratio)
    # D00.D3 V07: "split-first cash on new shares differs from cash on the old
    # share count" — the declared per-share amount applies to q1.
    cash = Fraction(cash_per_new_share) * q1
    wealth0 = Fraction(p0) * Fraction(q0)
    # D00.D3: reinvest=NONE "(cash held)": ending wealth "counts the shares
    # held at close p1 plus the cash".
    wealth1 = Fraction(p1) * q1 + cash
    return {
        "cash": cash,
        "holding_return": wealth1 / wealth0 - 1,
        "q1": q1,
        "raw_price_return": Fraction(p1) / Fraction(p0) - 1,
        "wealth": wealth1,
    }


def oracle_alias(rows, at):
    """Symbols whose [from, to) validity window covers `at` (half-open)."""
    # D00.D3 V12: half-open alias validity "[from, to)"; "to = None" is
    # open-ended, so the boundary date belongs to the NEXT row, not this one.
    return [
        r["symbol"]
        for r in rows
        if (r["from"] is None or r["from"] <= at) and (r["to"] is None or at < r["to"])
    ]


# Design vectors (verbatim from the programme's frozen vector JSON; rationals
# are strings, converted with Fraction(s)).
VECTORS = [
    {"id": "V01", "kind": "split",
     "input": {"raw_price": "100", "raw_quantity": "3", "ratios": ["2"]},
     "expected": {"adjusted_price": "50", "adjusted_quantity": "6", "wealth": "300"}},
    {"id": "V02", "kind": "split",
     "input": {"raw_price": "10", "raw_quantity": "5", "ratios": ["1/5"]},
     "expected": {"adjusted_price": "50", "adjusted_quantity": "1", "wealth": "50"}},
    {"id": "V03", "kind": "split",
     "input": {"raw_price": "90", "raw_quantity": "1200", "ratios": ["2", "3/2"]},
     "expected": {"adjusted_price": "30", "adjusted_quantity": "3600", "wealth": "108000"}},
    {"id": "V04", "kind": "return",
     "input": {"p0": "100", "p1": "110", "k0": "1/10", "k1": "1/10"},
     "expected": {"equal": True, "original": "1/10", "rebased": "1/10"}},
    {"id": "V05", "kind": "return",
     "input": {"p0": "100", "p1": "110", "k0": "1", "k1": "1/2"},
     "expected": {"equal": False, "original": "1/10", "rebased": "-9/20"}},
    {"id": "V06", "kind": "cash",
     "input": {"cash_per_new_share": "2", "p0": "100", "p1": "98", "q0": "1", "split_ratio": "1"},
     "expected": {"cash": "2", "holding_return": "0", "q1": "1",
                  "raw_price_return": "-1/50", "wealth": "100"}},
    {"id": "V07", "kind": "cash",
     "input": {"cash_per_new_share": "1", "p0": "100", "p1": "49", "q0": "1", "split_ratio": "2"},
     "expected": {"cash": "2", "holding_return": "0", "q1": "2",
                  "raw_price_return": "-51/100", "wealth": "100"}},
    {"id": "V12", "kind": "alias",
     "input": {"at": "2026-01-06T00:00:00Z",
               "rows": [{"from": "2026-01-01T00:00:00Z", "symbol": "OLD", "to": "2026-01-06T00:00:00Z"},
                        {"from": "2026-01-06T00:00:00Z", "symbol": "NEW", "to": None}]},
     "expected": {"symbols": ["NEW"]}},
]


# ==== SUT ADAPTERS ====

from lib.dataos.identity import AliasRow, VendorAliasTable  # noqa: E402
from lib.dataos.price_views import (  # noqa: E402
    ActionEvent,
    ActionFamily,
    ActionRevisionSet,
    RefusalReason,
    ReinvestPolicy,
    TotalReturnPolicy,
    ViewRefusal,
    ViewVintage,
    adjust_quantity,
    qualified_return,
    reopen_view,
    retain_view,
    return_vector,
    sadj_view,
    simple_returns,
    split_factor,
    total_return_view,
    view_label,
)
from lib.dataos.read_contract import ReadMode, ReadRequest, ViewContract  # noqa: E402

UTC = timezone.utc
MIC = "XNYS"
EX_DAY = date(2026, 6, 10)
ROW_DATE = date(2026, 6, 9)  # one row dated before every ex-date used below
AS_AT = datetime(2026, 6, 20, tzinfo=UTC)
KNOWN_EARLY = datetime(2026, 1, 1, tzinfo=UTC)
HEX40 = "0123456789abcdef0123456789abcdef01234567"  # synthetic code version
VENDOR = "q01v"
SEC = "SEC-Q01"


def split_event(event_id, ratio, *, ex_date=EX_DAY, family=ActionFamily.FORWARD_SPLIT,
                known_at=KNOWN_EARLY, qualification="CONFIRMED", **kw):
    return ActionEvent(event_id=event_id, family=family, ex_date=ex_date, known_at=known_at,
                       source_receipt=f"rcpt:{event_id}", qualification=qualification,
                       ratio=ratio, **kw)


def cash_event(event_id, per_share, *, ex_date=EX_DAY, known_at=KNOWN_EARLY, **kw):
    return ActionEvent(event_id=event_id, family=ActionFamily.CASH_DIVIDEND, ex_date=ex_date,
                       known_at=known_at, source_receipt=f"rcpt:{event_id}",
                       qualification="CONFIRMED", ratio=None, cash_per_share=per_share,
                       cash_basis="as_declared", currency="USD", **kw)


POLICY = TotalReturnPolicy(ReinvestPolicy.NONE, Fraction(0), "USD")


def close_rows(p0, p1):
    return [{"date": date(2026, 6, 9), "close_raw": Fraction(p0)},
            {"date": date(2026, 6, 11), "close_raw": Fraction(p1)}]


def sut_split_view(ratios, raw_price, raw_quantity):
    """SADJ view + revision set for a split vector: one row dated before every
    ex-date, split-first sequence order declared explicitly (insertion order
    in the tuple deliberately differs where >1 event shares the ex-date)."""
    events = []
    for i, r in enumerate(ratios):
        r = Fraction(r)
        family = ActionFamily.FORWARD_SPLIT if r > 1 else ActionFamily.REVERSE_SPLIT
        events.append(split_event(f"q01-s{i}", r, family=family, sequence=i))
    # insertion order reversed vs sequence order: ordering must come from
    # `sequence`, never from tuple position (D00.D3 same-day ordering).
    revs = ActionRevisionSet("q01-split-rev", tuple(reversed(events)))
    rows = [{"date": ROW_DATE, "close_raw": Fraction(raw_price),
             "volume_raw": Fraction(raw_quantity)}]
    return sadj_view(rows, revs, AS_AT, mic=MIC), revs


def sut_cash_view(cash_per_new_share, p0, p1, q0, split_ratio):
    """House TOTAL_RETURN over two closes straddling one ex-date; when a split
    shares the ex-date it is declared FIRST via sequence=0 (cash sequence=1),
    and the cash event is inserted first in the tuple so ordering must come
    from `sequence` alone."""
    events = [cash_event("q01-c", Fraction(cash_per_new_share), sequence=1)]
    if Fraction(split_ratio) != 1:
        events.append(split_event("q01-s", Fraction(split_ratio), sequence=0))
    revs = ActionRevisionSet("q01-cash-rev", tuple(events))
    return total_return_view(close_rows(p0, p1), revs, AS_AT, POLICY, mic=MIC, q0=Fraction(q0))


def sut_alias_table(oracle_rows):
    rows = [AliasRow(vendor=VENDOR, vendor_symbol=r["symbol"], security_id=SEC,
                     valid_from=r["from"], valid_to=r["to"]) for r in oracle_rows]
    return VendorAliasTable(rows)


def q01_contract():
    return ViewContract(purpose="q01-verification",
                        identity={"mic": MIC, "security_id": SEC, "listing_id": "LST-Q01"},
                        field_units={"close": "currency", "volume": "shares"},
                        adjustment_reference={"basis": "SADJ"},
                        coverage="2026-06-09..2026-06-11")


def frac(x):
    return Fraction(x)


# ==== TESTS ====


def test_Q01_00_oracle_section_imports_nothing_from_the_sut():
    source = pathlib.Path(__file__).read_text()  # self-check reads only this file
    tree = ast.parse(source)
    sut_bound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in ("lib", "engine"):
            sut_bound.update(a.asname or a.name for a in node.names)
        elif isinstance(node, ast.Import):
            for a in node.names:
                root = (a.asname or a.name).split(".")[0]
                if root in ("lib", "engine"):
                    sut_bound.add(a.asname or root)
    oracles = [n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name.startswith("oracle_")]
    assert oracles, "no oracle_ functions found"
    offenders = sorted({(fn.name, n.id) for fn in oracles
                        for n in ast.walk(fn)
                        if isinstance(n, ast.Name) and n.id in sut_bound})
    assert offenders == [], f"oracle section references SUT names: {offenders}"


@pytest.mark.parametrize("vec", VECTORS, ids=[v["id"] for v in VECTORS])
def test_Q01_01_vector_three_way(vec):
    vid, inp, exp = vec["id"], vec["input"], vec["expected"]
    if vec["kind"] == "split":
        ratios = [Fraction(r) for r in inp["ratios"]]
        o_price, o_qty, o_wealth = oracle_split(Fraction(inp["raw_price"]),
                                                Fraction(inp["raw_quantity"]), ratios)
        # oracle == JSON (every key)
        assert o_price == Fraction(exp["adjusted_price"])
        assert o_qty == Fraction(exp["adjusted_quantity"])
        assert o_wealth == Fraction(exp["wealth"])
        # SUT == JSON, read through sadj_view / split_factor / adjust_quantity
        view, revs = sut_split_view(ratios, inp["raw_price"], inp["raw_quantity"])
        row = view.rows[0]
        assert frac(row["close_sadj"]) == Fraction(exp["adjusted_price"])
        assert frac(row["volume_sadj"]) == Fraction(exp["adjusted_quantity"])
        assert frac(row["close_sadj"]) * frac(row["volume_sadj"]) == Fraction(exp["wealth"])
        factor = split_factor(ROW_DATE, revs, AS_AT, mic=MIC)
        chain = Fraction(1)
        for r in ratios:
            chain *= r
        assert factor == chain
        assert adjust_quantity(Fraction(inp["raw_quantity"]), factor) == Fraction(exp["adjusted_quantity"])
        assert Fraction(inp["raw_price"]) / factor == Fraction(exp["adjusted_price"])
    elif vec["kind"] == "return":
        o = oracle_return(Fraction(inp["p0"]), Fraction(inp["p1"]),
                          Fraction(inp["k0"]), Fraction(inp["k1"]))
        assert o["original"] == Fraction(exp["original"])
        assert o["rebased"] == Fraction(exp["rebased"])
        assert o["equal"] == exp["equal"]
        s = return_vector(Fraction(inp["p0"]), Fraction(inp["p1"]),
                          Fraction(inp["k0"]), Fraction(inp["k1"]))
        assert frac(s["original"]) == Fraction(exp["original"])
        assert frac(s["rebased"]) == Fraction(exp["rebased"])
        assert bool(s["equal"]) is exp["equal"]
    elif vec["kind"] == "cash":
        o = oracle_cash(Fraction(inp["cash_per_new_share"]), Fraction(inp["p0"]),
                        Fraction(inp["p1"]), Fraction(inp["q0"]), Fraction(inp["split_ratio"]))
        assert o["cash"] == Fraction(exp["cash"])
        assert o["holding_return"] == Fraction(exp["holding_return"])
        assert o["q1"] == Fraction(exp["q1"])
        assert o["raw_price_return"] == Fraction(exp["raw_price_return"])
        assert o["wealth"] == Fraction(exp["wealth"])
        tr = sut_cash_view(inp["cash_per_new_share"], inp["p0"], inp["p1"],
                           inp["q0"], inp["split_ratio"])
        assert frac(tr.q1) == Fraction(exp["q1"])
        assert frac(tr.cash) == Fraction(exp["cash"])
        assert frac(tr.wealth1) == Fraction(exp["wealth"])
        assert frac(tr.holding_return) == Fraction(exp["holding_return"])
        assert frac(tr.raw_price_return) == Fraction(exp["raw_price_return"])
        families = [fam for (_eid, fam, _r) in tr.events_applied]
        # D00.D3: "the view states which it used" — events_applied must state it.
        assert ActionFamily.CASH_DIVIDEND in families
        if Fraction(inp["split_ratio"]) != 1:
            assert families[0] == ActionFamily.FORWARD_SPLIT, "split-first order (sequence) must be stated"
    else:  # alias
        at = date.fromisoformat(inp["at"][:10])
        oracle_rows = [{"symbol": r["symbol"],
                        "from": date.fromisoformat(r["from"][:10]) if r["from"] else None,
                        "to": date.fromisoformat(r["to"][:10]) if r["to"] else None}
                       for r in inp["rows"]]
        assert oracle_alias(oracle_rows, at) == exp["symbols"]
        table = sut_alias_table(oracle_rows)
        assert table.vendor_symbol_for(VENDOR, SEC, at) == exp["symbols"][0]
        # half-open boundary: the day before the switch is the OLD spelling...
        prev = at - timedelta(days=1)
        assert oracle_alias(oracle_rows, prev) == ["OLD"]
        assert table.vendor_symbol_for(VENDOR, SEC, prev) == "OLD"
        # ...and OLD no longer maps ON the boundary day ([from, to) excludes to)
        assert table.resolve(VENDOR, "OLD", at) is None


def test_Q01_01_ex_date_boundary_row_is_not_adjusted():
    # D00.D3: S(t; v) = prod r_e over qualified split events e with
    # "ex_date > t" — STRICTLY greater, so a row dated ON the ex-date is not
    # divided by that split (it already trades in the new unit).
    rows = [{"date": date(2026, 6, 8), "close_raw": Fraction(100), "volume_raw": Fraction(5)},
            {"date": EX_DAY, "close_raw": Fraction(50), "volume_raw": Fraction(10)},
            {"date": date(2026, 6, 11), "close_raw": Fraction(48), "volume_raw": Fraction(9)}]
    revs = ActionRevisionSet("q01-boundary", (split_event("q01-b1", Fraction(2)),))
    assert split_factor(date(2026, 6, 8), revs, AS_AT, mic=MIC) == Fraction(2)
    assert split_factor(EX_DAY, revs, AS_AT, mic=MIC) == Fraction(1)
    assert split_factor(date(2026, 6, 11), revs, AS_AT, mic=MIC) == Fraction(1)
    view = sadj_view(rows, revs, AS_AT, mic=MIC)
    expected_sadj = [Fraction(100) / 2, Fraction(50), Fraction(48)]  # P_raw/S(t)
    assert [frac(r["close_sadj"]) for r in view.rows] == expected_sadj
    expected_vol = [Fraction(5) * 2, Fraction(10), Fraction(9)]  # vol_raw x S(t)
    assert [frac(r["volume_sadj"]) for r in view.rows] == expected_vol


SCALARS = (Fraction(1), Fraction(2), Fraction(1, 3), Fraction(100, 7))
SCALE_PAIRS = ((Fraction(100), Fraction(110)), (Fraction(7), Fraction(13)),
               (Fraction(9, 4), Fraction(27, 8)))


@pytest.mark.parametrize("p0,p1", SCALE_PAIRS, ids=["100-110", "7-13", "9_4-27_8"])
@pytest.mark.parametrize("s", SCALARS, ids=["s1", "s2", "s1_3", "s100_7"])
def test_Q01_02_uniform_scaling_is_not_a_return_error(p0, p1, s):
    # D00.D3 V04: "A common scalar on both return endpoints cancels."
    one = Fraction(1)
    o = oracle_return(p0, p1, s, s)
    o0 = oracle_return(p0, p1, one, one)
    assert o["original"] == o0["original"] and o["rebased"] == o0["rebased"]
    assert o["equal"] is True
    s1 = return_vector(p0, p1, s, s)
    s0 = return_vector(p0, p1, one, one)
    assert frac(s1["original"]) == frac(s0["original"]) == o0["original"]
    assert bool(s1["equal"]) is True
    if s != one:  # non-vacuity: the endpoints really moved
        assert p0 * s != p0 and p1 * s != p1


def test_Q01_02_sadj_simple_returns_invariant_to_series_scaling():
    # Uniform scaling of the WHOLE raw series leaves SADJ simple returns
    # unchanged: S(t) does not depend on prices (D00.D3 SADJ definition).
    base_rows = [{"date": date(2026, 6, 9), "close_raw": Fraction(120), "volume_raw": Fraction(10)},
                 {"date": date(2026, 6, 11), "close_raw": Fraction(50), "volume_raw": Fraction(20)}]
    revs = ActionRevisionSet("q01-scale", (split_event("q01-sc1", Fraction(2)),))
    v0 = sadj_view(base_rows, revs, AS_AT, mic=MIC)
    r0 = simple_returns(v0, "close")
    # oracle: S(6/9)=2, S(6/11)=1 -> sadj closes 60, 50 -> 50/60 - 1 == -1/6
    assert r0 == (Fraction(50) / Fraction(60) - 1,)
    assert r0 == (Fraction(-1, 6),)
    for c in SCALARS:
        scaled = [{"date": r["date"], "close_raw": r["close_raw"] * c,
                   "volume_raw": r["volume_raw"]} for r in base_rows]
        vc = sadj_view(scaled, revs, AS_AT, mic=MIC)
        assert simple_returns(vc, "close") == r0
        assert frac(vc.rows[0]["close_sadj"]) == frac(v0.rows[0]["close_sadj"]) * c


@pytest.mark.parametrize("k0,k1", [(Fraction(1), Fraction(1, 2)), (Fraction(2), Fraction(1))],
                         ids=["k1-half", "k2-down"])
def test_Q01_02_different_endpoint_factors_change_return_and_are_refused(k0, k1):
    # D00.D3 V05: "Different endpoint factors can create a false return", and
    # the executable claim only holds when no split crosses the interval.
    p0, p1 = Fraction(100), Fraction(110)
    o = oracle_return(p0, p1, k0, k1)
    assert o["equal"] is False and o["rebased"] != o["original"]
    s = return_vector(p0, p1, k0, k1)
    assert bool(s["equal"]) is False
    assert frac(s["rebased"]) == o["rebased"] != o["original"]
    with pytest.raises(ViewRefusal) as ei:
        qualified_return(p0, p1, k0, k1)
    assert ei.value.reason == RefusalReason.RETURN_ACROSS_UNADJUSTED_SPLIT
    # with no split crossing, the executable claim answers exactly
    assert qualified_return(p0, p1, Fraction(1), Fraction(1)) == o["original"]


def test_Q01_02_cash_event_never_transforms_volume():
    # D00.D3: "Volume transforms only under a split ... ; cash dividends never
    # apply an inverse split-volume transform (P03.03)" — with no split event
    # in the set, S(t) is the empty product 1: close and volume pass through.
    rows = [{"date": ROW_DATE, "close_raw": Fraction(100), "volume_raw": Fraction(7)}]
    revs = ActionRevisionSet("q01-cashonly", (cash_event("q01-co1", Fraction(2)),))
    view = sadj_view(rows, revs, AS_AT, mic=MIC)
    assert frac(view.rows[0]["close_sadj"]) == Fraction(100)
    assert frac(view.rows[0]["volume_sadj"]) == Fraction(7)


# ---- Q01.03 future-mutation immunity fixtures (all additions known AFTER T1)

T1 = datetime(2026, 6, 20, tzinfo=UTC)
T2 = datetime(2026, 7, 1, tzinfo=UTC)
KNOWN_LATER = datetime(2026, 6, 25, tzinfo=UTC)  # > T1, < T2

IMM_ROWS = [{"date": date(2026, 6, 9), "close_raw": Fraction(100), "volume_raw": Fraction(10)},
            {"date": date(2026, 6, 11), "close_raw": Fraction(50), "volume_raw": Fraction(20)}]
IMM_E1 = split_event("q01-i-e1", Fraction(2), ex_date=date(2026, 6, 10),
                     known_at=datetime(2026, 1, 1, tzinfo=UTC), sequence=0)
IMM_E4 = split_event("q01-i-e4", Fraction(3), ex_date=date(2026, 6, 12),
                     known_at=datetime(2026, 1, 15, tzinfo=UTC))
IMM_C1 = cash_event("q01-i-c1", Fraction(1), ex_date=date(2026, 6, 10),
                    known_at=datetime(2026, 1, 1, tzinfo=UTC), sequence=1)
IMM_BASE = (IMM_C1, IMM_E1, IMM_E4)  # cash first in tuple; order comes from sequence
IMM_A_NEW = split_event("q01-i-e2", Fraction(5), ex_date=date(2026, 6, 16), known_at=KNOWN_LATER)
IMM_A_SUPERSEDE = split_event("q01-i-e1b", Fraction(5, 2), ex_date=date(2026, 6, 10),
                              known_at=KNOWN_LATER, supersedes="q01-i-e1", sequence=0)
IMM_A_CANCEL = split_event("q01-i-e4c", Fraction(3), ex_date=date(2026, 6, 12),
                           known_at=KNOWN_LATER, supersedes="q01-i-e4", cancelled=True)


def _tr_economic(tr):
    return (tr.wealth0, tr.q1, tr.cash, tr.wealth1, tr.holding_return,
            tr.raw_price_return, tr.events_applied, tr.executable, tr.policy)


def test_Q01_03_future_mutations_cannot_alter_an_earlier_view():
    # A view at T1 is computed from the revision set AS KNOWN AT T1: events
    # known only after T1 (new split / supersede / cancellation) must not
    # move it (row tuples, split_factor, TotalReturnView fields).
    base = ActionRevisionSet("q01-i-base", IMM_BASE)
    ext = ActionRevisionSet("q01-i-ext", IMM_BASE + (IMM_A_NEW, IMM_A_SUPERSEDE, IMM_A_CANCEL))
    v1 = sadj_view(IMM_ROWS, base, T1, mic=MIC)
    v1x = sadj_view(IMM_ROWS, ext, T1, mic=MIC)
    assert tuple(v1x.rows) == tuple(v1.rows)
    assert split_factor(date(2026, 6, 9), ext, T1, mic=MIC) == \
        split_factor(date(2026, 6, 9), base, T1, mic=MIC) == Fraction(6)
    tr1 = total_return_view(IMM_ROWS, base, T1, POLICY, mic=MIC, q0=Fraction(1))
    tr1x = total_return_view(IMM_ROWS, ext, T1, POLICY, mic=MIC, q0=Fraction(1))
    assert _tr_economic(tr1x) == _tr_economic(tr1)


@pytest.mark.parametrize("addition", ["new_split", "supersede", "cancel", "all"],
                         ids=["a-new", "b-supersede", "c-cancel", "all"])
def test_Q01_03_additions_are_real_they_change_the_T2_view(addition):
    # Non-vacuity: the same additions DO change the view at T2 > known_at of
    # every addition — proving the T1 immunity above is not vacuous.
    base = ActionRevisionSet("q01-i-base", IMM_BASE)
    picks = {"new_split": (IMM_A_NEW,), "supersede": (IMM_A_SUPERSEDE,),
             "cancel": (IMM_A_CANCEL,),
             "all": (IMM_A_NEW, IMM_A_SUPERSEDE, IMM_A_CANCEL)}[addition]
    mutated = ActionRevisionSet(f"q01-i-{addition}", IMM_BASE + picks)
    v_base = sadj_view(IMM_ROWS, base, T2, mic=MIC)
    v_mut = sadj_view(IMM_ROWS, mutated, T2, mic=MIC)
    assert tuple(v_mut.rows) != tuple(v_base.rows)
    assert split_factor(date(2026, 6, 9), mutated, T2, mic=MIC) != \
        split_factor(date(2026, 6, 9), base, T2, mic=MIC)
    if addition == "all":
        tr_base = total_return_view(IMM_ROWS, base, T2, POLICY, mic=MIC, q0=Fraction(1))
        tr_mut = total_return_view(IMM_ROWS, mutated, T2, POLICY, mic=MIC, q0=Fraction(1))
        assert _tr_economic(tr_mut) != _tr_economic(tr_base)


def test_Q01_03_retained_view_reopens_byte_identically():
    # A retained view is "frozen as it answered": after a LATER view has been
    # computed, reopening returns byte-identical rows and label.
    base = ActionRevisionSet("q01-i-base", IMM_BASE)
    ext = ActionRevisionSet("q01-i-ext", IMM_BASE + (IMM_A_NEW, IMM_A_SUPERSEDE, IMM_A_CANCEL))
    v1 = sadj_view(IMM_ROWS, base, T1, mic=MIC)
    vintage = ViewVintage(source_generation_id="gen:q01", revision_set_id="q01-i-base",
                          identity_generation_id="idgen:q01", code_version=HEX40)
    retained = retain_view(v1, vintage, output_id="out:q01:1")
    assert retained.payload, "a retained view carries its payload bytes"
    later = sadj_view(IMM_ROWS, ext, T2, mic=MIC)  # a later view, computed after retention
    request = ReadRequest(mode=ReadMode.REPLAY, contract=q01_contract(), output_id="out:q01:1")
    ro = reopen_view(retained, request)
    assert ro.label == retained.label == view_label(v1, vintage)
    assert tuple(ro.view.rows) == tuple(v1.rows)
    assert tuple(ro.view.rows) != tuple(later.rows)  # non-vacuous freeze


def test_Q01_04_every_numeric_output_is_exact():
    rows = [{"date": ROW_DATE, "close_raw": Fraction(100), "volume_raw": Fraction(3)},
            {"date": date(2026, 6, 11), "close_raw": Fraction(50), "volume_raw": Fraction(6)}]
    revs = ActionRevisionSet("q01-exact", (split_event("q01-x1", Fraction(2)),))
    view = sadj_view(rows, revs, AS_AT, mic=MIC)
    tr = total_return_view(close_rows(100, 50), revs, AS_AT, POLICY, mic=MIC, q0=Fraction(1))
    rv = return_vector(Fraction(100), Fraction(110), Fraction(1), Fraction(1))
    values = [
        view.rows[0]["close_sadj"], view.rows[0]["volume_sadj"],
        split_factor(ROW_DATE, revs, AS_AT, mic=MIC),
        adjust_quantity(Fraction(3), Fraction(2)),
        rv["original"], rv["rebased"],
        *simple_returns(view, "close"),
        tr.wealth0, tr.q1, tr.cash, tr.wealth1, tr.holding_return, tr.raw_price_return,
        *[_r for (_eid, _fam, _r) in tr.events_applied],
    ]
    for x in values:
        assert isinstance(x, (Fraction, int)), f"non-exact type {type(x)} for {x!r}"
        assert not isinstance(x, (float, Decimal)), f"lossy type {type(x)} for {x!r}"


@pytest.mark.parametrize("case", ["sadj_close", "sadj_volume", "total_return"],
                         ids=["sadj-close", "sadj-volume", "tr-close"])
def test_Q01_04_float_price_input_is_refused(case):
    # D00.D3 works in exact rationals end to end; row values are exact
    # int/Fraction. A float anywhere in a price row is refused, never rounded.
    revs = ActionRevisionSet("q01-float", (split_event("q01-f1", Fraction(2)),))
    if case == "sadj_close":
        rows = [{"date": ROW_DATE, "close_raw": 100.0, "volume_raw": Fraction(3)}]
        call = lambda: sadj_view(rows, revs, AS_AT, mic=MIC)  # noqa: E731
    elif case == "sadj_volume":
        rows = [{"date": ROW_DATE, "close_raw": Fraction(100), "volume_raw": 3.0}]
        call = lambda: sadj_view(rows, revs, AS_AT, mic=MIC)  # noqa: E731
    else:
        rows = [{"date": date(2026, 6, 9), "close_raw": 100.0},
                {"date": date(2026, 6, 11), "close_raw": Fraction(50)}]
        call = lambda: total_return_view(rows, revs, AS_AT, POLICY, mic=MIC, q0=Fraction(1))  # noqa: E731
    with pytest.raises(ViewRefusal) as ei:
        call()
    assert ei.value.reason == RefusalReason.NON_EXACT_INPUT


# ---- Q01.06 refusal oracle (every expectation derived from D00.D3 text)


REFUSAL_CASES = [
    # (case id, entry point, D00-derived reason)
    # D00.D3: unsupported families (spin-offs et al.) are a "typed refusal
    # UNSUPPORTED_ACTION, never coerced".
    ("spin_off", "sadj", RefusalReason.UNSUPPORTED_ACTION),
    # D00.D3: house TOTAL_RETURN refuses when "any event in the window is
    # unsupported" — the spin-off ex-date 2026-06-10 is inside 6/9..6/11.
    ("spin_off", "tr", RefusalReason.UNSUPPORTED_ACTION),
    # D00.D3: SADJ refuses when "a ratio is zero/negative/unknown".
    ("ratio_zero", "factor", RefusalReason.INVALID_RATIO),
    ("ratio_zero", "sadj", RefusalReason.INVALID_RATIO),
    ("ratio_negative", "factor", RefusalReason.INVALID_RATIO),
    ("ratio_unknown", "factor", RefusalReason.UNKNOWN_RATIO),
    ("ratio_unknown", "sadj", RefusalReason.UNKNOWN_RATIO),
]


@pytest.mark.parametrize("case,entry,expected_reason",
                         REFUSAL_CASES,
                         ids=[f"{c}-{e}" for c, e, _r in REFUSAL_CASES])
def test_Q01_06_typed_refusals(case, entry, expected_reason):
    if case == "spin_off":
        ev = split_event("q01-r-so", None, family=ActionFamily.SPIN_OFF)
    elif case == "ratio_zero":
        ev = split_event("q01-r-z", Fraction(0))
    elif case == "ratio_negative":
        ev = split_event("q01-r-n", Fraction(-2))
    else:
        ev = split_event("q01-r-u", None)
    revs = ActionRevisionSet(f"q01-rev-{case}", (ev,))
    if entry == "factor":
        with pytest.raises(ViewRefusal) as ei:
            split_factor(ROW_DATE, revs, AS_AT, mic=MIC)
    elif entry == "sadj":
        rows = [{"date": ROW_DATE, "close_raw": Fraction(100), "volume_raw": Fraction(3)}]
        with pytest.raises(ViewRefusal) as ei:
            sadj_view(rows, revs, AS_AT, mic=MIC)
    else:
        with pytest.raises(ViewRefusal) as ei:
            total_return_view(close_rows(100, 50), revs, AS_AT, POLICY, mic=MIC, q0=Fraction(1))
    assert ei.value.reason == expected_reason


# PRE-REGISTRATION (decided from the D00.D3 text BEFORE this test was first
# run against the SUT): D00.D3 defines S(t; v) as the product of r_e "over
# QUALIFIED split events e", and "an action inferred solely from a price
# discontinuity is never admitted as a confirmed event (P01.02)" — so an
# INFERRED-qualification event is not a qualified event and simply does not
# enter the product: split_factor stays 1. The refusal conditions enumerated
# for SADJ in D00.D3 (already-adjusted input, zero/negative/unknown ratio,
# mixed OHLC bases) do NOT include qualification, which the oracle reads as:
# no refusal. [Observed against the SUT during the pre-freeze shape probe and
# at first run: the SUT raises ViewRefusal(NOT_CONFIRMED) instead — recorded
# as FINDING F1 in Q01_ORACLE.md, never silently re-matched.]
# SEAT RULING 2026-10-17 (D00.D3 clarification "ABSENT vs UNRESOLVED", recorded in
# D00_SEMANTIC_DECISIONS.md and Q01_ORACLE.md): an INFERRED event that is PRESENT in
# the revision set is an UNRESOLVED observation, not an absent one. Leaving the factor
# at 1 would assert "no split happened" without a qualified receipt — exactly the
# false consensus C03 exists to prevent — so SADJ/TOTAL_RETURN refuse with the typed
# NOT_CONFIRMED (D00.D4: context may be shown, computation refuses); RAW is untouched.
# The pre-registered factor-1 reading remains correct for the ABSENT case (a revision
# set with no observation at all). FINDING F1 is CLOSED-BY-RULING; this test now pins
# the ruled behaviour instead of carrying a strict xfail.
def test_Q01_06_not_confirmed_is_a_typed_refusal_by_ruling():
    revs = ActionRevisionSet("q01-nc", (split_event("q01-nc1", Fraction(2), qualification="INFERRED"),))
    with pytest.raises(ViewRefusal) as ei:
        split_factor(ROW_DATE, revs, AS_AT, mic=MIC)
    assert ei.value.reason == RefusalReason.NOT_CONFIRMED


def test_Q01_06_not_confirmed_event_is_never_applied_as_confirmed():
    # D00.D3 (P01.02): an INFERRED event "is never admitted as a confirmed
    # event" — under EITHER reading (oracle: skipped; SUT per FINDING F1:
    # typed NOT_CONFIRMED refusal) the factor may never become the ratio and
    # the view may never adjust by it.
    revs = ActionRevisionSet("q01-nc2", (split_event("q01-nc2", Fraction(2), qualification="INFERRED"),))
    try:
        f = split_factor(ROW_DATE, revs, AS_AT, mic=MIC)
    except ViewRefusal as vr:
        assert vr.reason == RefusalReason.NOT_CONFIRMED  # observed path (F1)
    else:
        assert f == Fraction(1)  # oracle path
    rows = [{"date": ROW_DATE, "close_raw": Fraction(100), "volume_raw": Fraction(3)}]
    try:
        view = sadj_view(rows, revs, AS_AT, mic=MIC)
    except ViewRefusal as vr:
        assert vr.reason == RefusalReason.NOT_CONFIRMED  # observed path (F1)
    else:
        assert frac(view.rows[0]["close_sadj"]) == Fraction(100)  # ratio never applied


def test_Q01_06_non_raw_price_column_is_refused():
    # PRE-REGISTRATION: D00.D3 refuses SADJ when "an input already adjusted
    # (is_ambiguous or basis != RAW) would be adjusted twice" — a row
    # carrying a non-raw price column must be refused with one of the D00
    # basis reasons (NON_RAW_INPUT / DOUBLE_ADJUST_RISK / MIXED_OHLC_BASIS);
    # the observed reason is recorded in Q01_ORACLE.md (observed:
    # MIXED_OHLC_BASIS).
    revs = ActionRevisionSet("q01-nonraw", (split_event("q01-nr1", Fraction(2)),))
    rows = [{"date": ROW_DATE, "close_raw": Fraction(100), "volume_raw": Fraction(3),
             "close_sadj": Fraction(50)}]
    with pytest.raises(ViewRefusal) as ei:
        sadj_view(rows, revs, AS_AT, mic=MIC)
    assert ei.value.reason in (RefusalReason.NON_RAW_INPUT,
                               RefusalReason.DOUBLE_ADJUST_RISK,
                               RefusalReason.MIXED_OHLC_BASIS)


def test_Q01_06_mixed_ohlc_bases_are_refused():
    # PRE-REGISTRATION: D00.D3 refuses when "OHLC rows mix bases" ->
    # MIXED_OHLC_BASIS (one row on the raw basis, another on an adjusted one).
    revs = ActionRevisionSet("q01-mixed", (split_event("q01-mx1", Fraction(2)),))
    rows = [{"date": date(2026, 6, 9), "close_raw": Fraction(100), "volume_raw": Fraction(3)},
            {"date": date(2026, 6, 11), "close_sadj": Fraction(50), "volume_raw": Fraction(6)}]
    with pytest.raises(ViewRefusal) as ei:
        sadj_view(rows, revs, AS_AT, mic=MIC)
    assert ei.value.reason == RefusalReason.MIXED_OHLC_BASIS
