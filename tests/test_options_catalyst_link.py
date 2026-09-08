"""Tests for engine.options_catalyst_link — F03 catalyst-linkage read-model.

Synthetic live_flow event fixtures only. No data/ I/O. No network. No clock.
``ts`` / ``observed_at`` use the producer's UTC ``...Z`` shape
(``live_flow._event_ts_utc``).
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
from datetime import date, timedelta

import pytest

from engine.earnings_catalyst import STALE_AGE_TD as CANONICAL_STALE_AGE_TD
from engine.options_catalyst_link import (
    AMBIGUOUS_MULTIPLE,
    BINDING_STATES,
    BOUND,
    DEFAULT_HORIZON_DAYS,
    EXPIRY_BEFORE_ASOF,
    EXPIRY_MISMATCH,
    IDENTITY_UNRESOLVED,
    SAME_DAY_UNORDERED,
    STALE_AGE_TD,
    STALE_CATALYST,
    UNBOUND_NO_CATALYST,
    CalendarContext,
    CatalystCandidate,
    ContractKeyError,
    bind_event,
    bind_events,
    write_links,
)
from engine.stock_identity.authority import authority_block, is_zero_authority

EXPECTED_KEYS = frozenset(
    {
        "schema",
        "spec_version",
        "session_date",
        "asof",
        "asof_vs_session",
        "horizon_days",
        "event_id",
        "contract",
        "binding_state",
        "identity",
        "catalyst",
        "catalyst_state",
        "catalyst_reason",
        "candidates",
        "expiry",
        "evidence",
        "source_rights",
        "authority",
        "is_context_only",
    }
)

ASOF = date(2026, 9, 4)
# 2026-10-16 is a third Friday (monthly OPEX)
EXP_OK = "2026-10-16"
KNOWN = frozenset({"AAPL", "SPY", "QQQ", "BRKB"})
KNOWN_AS_OF = date(2026, 9, 1)


def _event(**overrides):
    """Synthetic live_flow event dict using the emitted field names and UTC Z."""
    base = {
        "id": "a1b2c3d4e5f60718",
        "ts": "2026-09-04T18:30:00Z",
        "observed_at": "2026-09-04T18:30:05Z",
        "root": "AAPL",
        "group": "tech",
        "group_zh": "科技",
        "right": "C",
        "exp": EXP_OK,
        "strike": 240.0,
        "dte": 42,
        "dte_bucket": "30_60",
        "mny_bucket": "atm",
        "side": "ask",
        "n_prints": 3,
        "size": 150,
        "avg_price": 2.5,
        "premium": 37500.0,
        "premium_z": 2.1,
        "baseline_source": "session",
        "selection_rule": "floor",
        "selection_floor_usd": 25000.0,
        "selection_root_class": "single_name",
        "vol_gt_oi": False,
        "vol_gt_oi_ratio": None,
        "oi_vintage": None,
        "repeated": False,
        "zerodte": False,
        "signing_source": "tape",
        "swept": False,
        "microstructure": {"spread_bps": 10},
    }
    base.update(overrides)
    return base


def _empty_calendar(macros=()):
    return CalendarContext(
        is_third_friday=None,
        is_quad_witching=None,
        macro_catalysts=tuple(macros),
    )


def _earnings(
    d: date,
    *,
    stale=False,
    source="engine.earnings_catalyst",
    artifact="earnings_store",
    label="Q3 results",
    known_as_of=KNOWN_AS_OF,
    as_of_age_td=2,
    locator="earnings_blackout.assess",
):
    if stale is True or stale is None:
        as_of_age_td = None
    return CatalystCandidate(
        kind="earnings",
        date=d,
        source=source,
        artifact=artifact,
        stale=stale,
        known_as_of=known_as_of,
        as_of_age_td=as_of_age_td,
        label=label,
        locator=locator,
    )


def _macro(
    kind: str,
    d: date,
    *,
    source="engine.event_calendar",
    artifact="event_calendar.static",
    stale=False,
    known_as_of=KNOWN_AS_OF,
    as_of_age_td=1,
    label=None,
    locator="event_calendar:static",
):
    return CatalystCandidate(
        kind=kind,
        date=d,
        source=source,
        artifact=artifact,
        stale=stale,
        known_as_of=known_as_of,
        as_of_age_td=as_of_age_td,
        label=label,
        locator=locator,
    )


def _bind(ev=None, *, catalysts=None, calendar=None, known=None, **kwargs):
    return bind_event(
        ev if ev is not None else _event(),
        asof=kwargs.pop("asof", ASOF),
        catalysts=catalysts if catalysts is not None else {},
        calendar=calendar if calendar is not None else _empty_calendar(),
        known_symbols=known if known is not None else KNOWN,
        **kwargs,
    )


# ── 1. positive bind ──────────────────────────────────────────────────────────


def test_positive_bind_single_in_window_catalyst():
    cat = _earnings(date(2026, 10, 10), label="Q3 results")
    rec = _bind(catalysts={"AAPL": [cat]}).record
    assert rec["binding_state"] == BOUND
    assert rec["catalyst"]["date"] == "2026-10-10"
    assert rec["catalyst"]["days_expiry_minus_catalyst"] == 6
    assert rec["catalyst"]["source"] == "engine.earnings_catalyst"
    assert rec["catalyst"]["artifact"] == "earnings_store"
    assert rec["horizon_days"] == DEFAULT_HORIZON_DAYS
    assert [e["leg"] for e in rec["evidence"]] == ["event", "catalyst", "expiry"]
    assert rec["evidence"][1]["source"] == "engine.earnings_catalyst"
    assert rec["evidence"][1]["artifact"] == "earnings_store"


# ── 2. ambiguous — never nearest ──────────────────────────────────────────────


def test_ambiguous_multiple_is_typed_not_nearest():
    near = _earnings(date(2026, 9, 15), label="near", source="engine.earnings_catalyst")
    far = _macro("cpi", date(2026, 10, 8), label="far")
    rec = _bind(catalysts={"AAPL": [near, far]}).record
    assert rec["binding_state"] == AMBIGUOUS_MULTIPLE
    assert rec["catalyst"] is None
    assert {c["date"] for c in rec["candidates"]} == {"2026-09-15", "2026-10-08"}


# ── 3. stale True ─────────────────────────────────────────────────────────────


def test_stale_catalyst_is_typed():
    rec = _bind(catalysts={"AAPL": [_earnings(date(2026, 10, 10), stale=True)]}).record
    assert rec["binding_state"] == STALE_CATALYST
    assert rec["candidates"][0]["stale"] is True
    assert rec["candidates"][0]["trusted"] is False


# ── 4. stale None is never fresh ──────────────────────────────────────────────


def test_stale_none_is_not_read_as_fresh():
    cat = CatalystCandidate(
        kind="earnings",
        date=date(2026, 10, 10),
        source="engine.earnings_catalyst",
        artifact="earnings_store",
        stale=None,
        known_as_of=KNOWN_AS_OF,
        as_of_age_td=None,
        label="unchecked",
    )
    rec = _bind(catalysts={"AAPL": [cat]}).record
    assert rec["binding_state"] == STALE_CATALYST
    assert rec["candidates"][0]["stale"] is None
    assert rec["candidates"][0]["stale_reason"] == "never_checked"


# ── 5. identity unresolved — expiry still runs ────────────────────────────────


def test_identity_unresolved_is_typed():
    rec = _bind(_event(root="ZZZZ")).record
    assert rec["binding_state"] == IDENTITY_UNRESOLVED
    assert rec["identity"]["resolved_symbol"] is None
    assert rec["identity"]["match"] == "exact_root_upper"
    assert rec["catalyst_state"] == "NOT_ATTEMPTED"
    assert rec["expiry"]["state"] == "OK"
    assert rec["expiry"]["is_third_friday"] is True
    assert rec["expiry"]["dte_calendar_days"] == 42


# ── 6. expiry mismatch does not blank the event ───────────────────────────────


def test_expiry_mismatch_does_not_blank_the_event():
    rec = _bind(
        _event(exp="not-a-date"),
        catalysts={"AAPL": [_earnings(date(2026, 9, 20))]},
    ).record
    assert rec["binding_state"] == EXPIRY_MISMATCH
    assert rec["expiry"]["state"] == EXPIRY_MISMATCH
    assert rec["expiry"]["reason"] == "expiry_unparseable"
    assert rec["expiry"]["is_third_friday"] is None
    assert rec["expiry"]["is_quad_witching"] is None
    assert rec["event_id"] == "a1b2c3d4e5f60718"
    assert rec["contract"]["root"] == "AAPL"
    assert rec["identity"]["state"] == "RESOLVED"


# ── 7. catalyst after expiry (B1) ─────────────────────────────────────────────


def test_catalyst_after_expiry_does_not_corrupt_expiry_class():
    rec = _bind(catalysts={"AAPL": [_earnings(date(2026, 11, 15))]}).record
    assert rec["binding_state"] == UNBOUND_NO_CATALYST
    assert rec["expiry"]["state"] == "OK"
    assert rec["expiry"]["reason"] is None
    assert rec["expiry"]["is_third_friday"] is True
    assert rec["expiry"]["is_quad_witching"] is False
    assert rec["expiry"]["dte_calendar_days"] == 42
    assert rec["catalyst_reason"] == "all_candidates_after_expiry"
    assert rec["catalyst_state"] == UNBOUND_NO_CATALYST


def test_catalyst_after_expiry_state_stable_when_stale_past_macro_present():
    past = _macro("fomc", date(2026, 8, 1), label="stale-past")
    rec = _bind(
        catalysts={"AAPL": [_earnings(date(2026, 11, 15))]},
        calendar=_empty_calendar(macros=(past,)),
    ).record
    assert rec["binding_state"] == UNBOUND_NO_CATALYST
    assert rec["expiry"]["state"] == "OK"
    assert rec["catalyst_reason"] == "no_candidate_in_window"
    assert rec["expiry"]["dte_calendar_days"] == 42


# ── 8. no catalyst — never invented ───────────────────────────────────────────


def test_no_catalyst_is_unbound_never_invented():
    rec = _bind().record
    assert rec["binding_state"] == UNBOUND_NO_CATALYST
    assert rec["catalyst"] is None
    assert rec["candidates"] == []
    assert rec["session_date"] is None
    blob = json.dumps(rec, sort_keys=True)
    assert '"catalyst": null' in blob
    for key, val in rec.items():
        if key in {"asof", "session_date"}:
            continue
        if key in {"contract", "expiry"}:
            continue
        if isinstance(val, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", val):
            pytest.fail(f"invented date at top-level key {key}: {val}")


# ── 9. contract key miss raises ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "overrides",
    [
        {"strike": None},
        {"root": ""},
        {"right": "X"},
        {"id": None},
    ],
)
def test_contract_key_miss_raises(overrides, tmp_path):
    ev = _event(**overrides)
    if "strike" in overrides and overrides["strike"] is None:
        ev.pop("strike", None)
    if "id" in overrides and overrides["id"] is None:
        ev.pop("id", None)
    with pytest.raises(ContractKeyError):
        _bind(ev)
    out = tmp_path / "x.jsonl"
    assert not out.exists()


# ── 10. determinism (M3) ──────────────────────────────────────────────────────


def test_determinism_byte_identical_under_shuffled_inputs():
    cats = [
        _macro("cpi", date(2026, 10, 8), label="cpi"),
        _earnings(date(2026, 9, 15), label="earn"),
    ]
    macros = (
        _macro("fomc", date(2026, 9, 20), label="fomc"),
    )
    events = [
        _event(id="id00000000000001", root="AAPL"),
        _event(id="id00000000000002", root="SPY", selection_root_class="etf_anchor"),
    ]
    a = bind_events(
        events,
        asof=ASOF,
        catalysts={"AAPL": list(cats), "SPY": []},
        calendar=_empty_calendar(macros=macros),
        known_symbols=KNOWN,
    )
    b = bind_events(
        events,
        asof=ASOF,
        catalysts={"AAPL": list(reversed(cats)), "SPY": []},
        calendar=_empty_calendar(macros=tuple(reversed(macros))),
        known_symbols=KNOWN,
    )
    assert [la.record["event_id"] for la in a] == [
        "id00000000000001",
        "id00000000000002",
    ]
    for la, lb in zip(a, b):
        assert json.dumps(la.record, sort_keys=True) == json.dumps(
            lb.record, sort_keys=True
        )
        assert [c["date"] for c in la.record["candidates"]] == [
            c["date"] for c in lb.record["candidates"]
        ]


def test_bind_events_preserves_input_order():
    events = [
        _event(id="id00000000000002", root="SPY"),
        _event(id="id00000000000001", root="AAPL"),
    ]
    links = bind_events(
        events,
        asof=ASOF,
        catalysts={},
        calendar=_empty_calendar(),
        known_symbols=KNOWN,
    )
    assert [lk.record["event_id"] for lk in links] == [
        "id00000000000002",
        "id00000000000001",
    ]
    assert [lk.record["contract"]["root"] for lk in links] == ["SPY", "AAPL"]


# ── 11. nulls printed ─────────────────────────────────────────────────────────


def test_nulls_are_printed_not_absent():
    fixtures = {
        BOUND: (
            _event(),
            {"AAPL": [_earnings(date(2026, 10, 10))]},
            _empty_calendar(),
            KNOWN,
        ),
        AMBIGUOUS_MULTIPLE: (
            _event(),
            {
                "AAPL": [
                    _earnings(date(2026, 9, 15)),
                    _macro("cpi", date(2026, 10, 8)),
                ]
            },
            _empty_calendar(),
            KNOWN,
        ),
        STALE_CATALYST: (
            _event(),
            {"AAPL": [_earnings(date(2026, 10, 10), stale=True)]},
            _empty_calendar(),
            KNOWN,
        ),
        UNBOUND_NO_CATALYST: (
            _event(),
            {},
            _empty_calendar(),
            KNOWN,
        ),
        IDENTITY_UNRESOLVED: (
            _event(root="NOPE"),
            {},
            _empty_calendar(),
            KNOWN,
        ),
        EXPIRY_MISMATCH: (
            _event(exp="bogus"),
            {"AAPL": [_earnings(date(2026, 9, 20))]},
            _empty_calendar(),
            KNOWN,
        ),
        EXPIRY_BEFORE_ASOF: (
            _event(exp="2026-09-03"),
            {"AAPL": [_earnings(date(2026, 9, 20))]},
            _empty_calendar(),
            KNOWN,
        ),
        SAME_DAY_UNORDERED: (
            _event(),
            {"AAPL": [_earnings(date(2026, 9, 4), label="same-day")]},
            _empty_calendar(),
            KNOWN,
        ),
    }
    assert set(fixtures) == set(BINDING_STATES)
    for state, (ev, cats, cal, known) in fixtures.items():
        rec = _bind(ev, catalysts=cats, calendar=cal, known=known).record
        assert set(rec) == EXPECTED_KEYS, state
        assert rec["binding_state"] == state
        assert rec["horizon_days"] == 63
        assert rec["identity"]["state"] in {IDENTITY_UNRESOLVED, "RESOLVED"}
        assert rec["expiry"]["state"] in {
            "OK",
            EXPIRY_MISMATCH,
            EXPIRY_BEFORE_ASOF,
        }


# ── 12. zero authority ────────────────────────────────────────────────────────


def test_zero_authority():
    rec = _bind(catalysts={"AAPL": [_earnings(date(2026, 10, 10))]}).record
    assert rec["authority"] == authority_block()
    assert all(v is False for v in rec["authority"].values())
    assert rec["source_rights"] == "research_expression_only"
    assert rec["is_context_only"] is True
    assert is_zero_authority(rec) is True


# ── 13. no scoring / prophet import ───────────────────────────────────────────


def test_no_scoring_or_prophet_import():
    src_path = pathlib.Path("engine/options_catalyst_link.py")
    src = src_path.read_text(encoding="utf-8")
    assert (
        re.search(
            r"^(from|import) +(engine\.(prophet|conditions|regime|run|inputs|"
            r"equity_alloc|calibrate|scoring)|scripts|lib\.prophet)",
            src,
            re.M,
        )
        is None
    )

    allowed_engine = {
        "engine.event_calendar",
        "engine.stock_identity.authority",
        "engine.earnings_catalyst",
    }
    forbidden_prefixes = (
        "engine.prophet",
        "engine.conditions",
        "engine.regime",
        "engine.run",
        "engine.inputs",
        "engine.equity_alloc",
        "engine.calibrate",
        "engine.live_flow",
        "scripts",
        "pandas",
        "requests",
        "urllib",
    )
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                for prefix in forbidden_prefixes:
                    assert not (
                        name == prefix or name.startswith(prefix + ".")
                    ), f"forbidden import {name}"
                assert (
                    not name.startswith("engine.")
                    or name in allowed_engine
                    or name.startswith("engine.stock_identity")
                )
                if name.startswith("engine.") and "signal" in name:
                    pytest.fail(f"forbidden signal import {name}")
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for prefix in forbidden_prefixes:
                assert not (
                    mod == prefix or mod.startswith(prefix + ".")
                ), f"forbidden from-import {mod}"
            if mod.startswith("engine.") and mod.endswith("_signals"):
                pytest.fail(f"forbidden signals import {mod}")
            assert (
                mod in allowed_engine
                or mod in {"__future__"}
                or mod.split(".")[0]
                in (
                    "dataclasses",
                    "datetime",
                    "json",
                    "typing",
                    "os",
                )
                or mod.startswith("engine.stock_identity")
            )


def test_stale_age_td_is_earnings_catalyst_constant():
    assert STALE_AGE_TD is CANONICAL_STALE_AGE_TD
    assert STALE_AGE_TD == 10


# ── 14. write_links path discipline ───────────────────────────────────────────


def test_write_links_only_touches_given_path(tmp_path):
    data_sentinel = pathlib.Path("data/options/catalyst_links")
    pre_existed = data_sentinel.exists()
    rec_link = _bind(catalysts={"AAPL": [_earnings(date(2026, 10, 10))]})
    out = tmp_path / "x.jsonl"
    n = write_links(out, [rec_link, rec_link])
    assert n == 2
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert obj["schema"] == "options.catalyst_link/v1"
    n2 = write_links(out, [rec_link, rec_link])
    assert n2 == 2
    assert len(out.read_text(encoding="utf-8").strip().splitlines()) == 2
    if not pre_existed:
        assert not data_sentinel.exists()


def test_write_links_refuses_repo_data_path():
    with pytest.raises(ValueError, match="data/"):
        write_links("data/options/catalyst_links.jsonl", [])
    assert not pathlib.Path("data/options/catalyst_links.jsonl").exists()


# ── B2 look-ahead ─────────────────────────────────────────────────────────────


def test_lookahead_candidate_never_binds():
    late = _earnings(
        date(2026, 10, 10),
        known_as_of=date(2026, 9, 5),
        label="announced-after-event",
    )
    rec = _bind(catalysts={"AAPL": [late]}).record
    assert rec["binding_state"] == STALE_CATALYST
    assert rec["catalyst_reason"] == "LOOKAHEAD_EXCLUDED"
    assert rec["catalyst"] is None
    row = rec["candidates"][0]
    assert row["known_as_of"] == "2026-09-05"
    assert row["exclusion_reason"] == "LOOKAHEAD_EXCLUDED"
    assert row["trusted"] is False
    assert row["in_window"] is True


def test_known_as_of_none_is_lookahead_excluded():
    cat = CatalystCandidate(
        kind="earnings",
        date=date(2026, 10, 10),
        source="engine.earnings_catalyst",
        artifact="earnings_store",
        stale=False,
        known_as_of=None,
        as_of_age_td=2,
        label="unknowable",
    )
    rec = _bind(catalysts={"AAPL": [cat]}).record
    assert rec["binding_state"] == STALE_CATALYST
    assert rec["catalyst_reason"] == "LOOKAHEAD_EXCLUDED"
    assert rec["candidates"][0]["known_as_of"] is None
    assert rec["candidates"][0]["exclusion_reason"] == "LOOKAHEAD_EXCLUDED"


def test_asof_before_session_is_typed():
    rec = _bind(
        _event(session_date="2026-09-04"),
        asof=date(2026, 9, 3),
        catalysts={"AAPL": [_earnings(date(2026, 10, 10))]},
    ).record
    assert rec["session_date"] == "2026-09-04"
    assert rec["asof"] == "2026-09-03"
    assert rec["asof_vs_session"] == "asof_before_session"
    assert rec["evidence"][0]["asof_vs_event"] == "asof_before_event"


# ── M1 session_date ───────────────────────────────────────────────────────────


def test_session_date_never_fabricated_from_asof_or_observed_at():
    rec = _bind(
        _event(observed_at="2026-09-05T02:00:00Z", ts="2026-09-04T18:30:00Z"),
        asof=date(2026, 9, 6),
    ).record
    assert rec["session_date"] is None
    assert rec["asof"] == "2026-09-06"
    assert rec["asof_vs_session"] == "session_date_null"
    ev_ref = rec["evidence"][0]
    assert ev_ref["locator"] is None
    assert ev_ref["locator_state"] == "session_date_untyped"
    assert ev_ref["event_ts_date"] == "2026-09-04"


def test_session_date_uses_caller_not_poller_clock():
    rec = _bind(
        _event(
            session_date="2026-09-04",
            observed_at="2026-09-05T02:15:00Z",
            ts="2026-09-04T20:05:00Z",
        ),
        catalysts={"AAPL": [_earnings(date(2026, 10, 10))]},
    ).record
    assert rec["session_date"] == "2026-09-04"
    assert rec["asof_vs_session"] == "ok"
    ev_ref = rec["evidence"][0]
    assert ev_ref["locator"] == (
        "data/live_flow_state/events/2026-09-04.jsonl#a1b2c3d4e5f60718"
    )
    assert ev_ref["locator_state"] == "ok"
    assert ev_ref["observed_at"] == "2026-09-05T02:15:00Z"


def test_session_date_kwarg_overrides_missing_event_field():
    rec = _bind(session_date=date(2026, 9, 4)).record
    assert rec["session_date"] == "2026-09-04"
    assert rec["asof_vs_session"] == "ok"


# ── M2 provenance ─────────────────────────────────────────────────────────────


def test_evidence_source_is_carried_not_guessed():
    fred = _macro(
        "cpi",
        date(2026, 10, 8),
        source="engine.event_calendar",
        artifact="event_calendar.fred",
        locator="fred:CPIAUCSL",
        label="cpi",
    )
    rec = _bind(catalysts={"AAPL": [fred]}).record
    assert rec["binding_state"] == BOUND
    assert rec["catalyst"]["source"] == "engine.event_calendar"
    assert rec["catalyst"]["artifact"] == "event_calendar.fred"
    cat_ref = rec["evidence"][1]
    assert cat_ref["source"] == "engine.event_calendar"
    assert cat_ref["artifact"] == "event_calendar.fred"
    assert cat_ref["locator"] == "fred:CPIAUCSL"
    assert rec["candidates"][0]["artifact"] == "event_calendar.fred"


def test_unbound_catalyst_evidence_does_not_claim_earnings_module():
    rec = _bind().record
    cat_ref = rec["evidence"][1]
    assert cat_ref["source"] is None
    assert cat_ref["artifact"] is None
    assert cat_ref["locator"] is None
    assert cat_ref["state"] == UNBOUND_NO_CATALYST


# ── M4 alias / co-dated / boundaries ──────────────────────────────────────────


def test_share_class_alias_is_unresolved_not_remapped():
    rec = _bind(_event(root="BRK.B"), known=frozenset({"BRKB", "AAPL"})).record
    assert rec["binding_state"] == IDENTITY_UNRESOLVED
    assert rec["identity"]["resolved_symbol"] is None
    assert rec["contract"]["root"] == "BRK.B"
    assert rec["identity"]["match"] == "exact_root_upper"


def test_adjusted_root_is_not_the_underlying_symbol():
    rec = _bind(_event(root="AAPL1"), known=frozenset({"AAPL"})).record
    assert rec["binding_state"] == IDENTITY_UNRESOLVED
    assert rec["contract"]["root"] == "AAPL1"


def test_exact_root_still_binds():
    rec = _bind(
        _event(root="BRKB"),
        catalysts={"BRKB": [_earnings(date(2026, 10, 10))]},
        known=frozenset({"BRKB"}),
    ).record
    assert rec["binding_state"] == BOUND
    assert rec["identity"]["resolved_symbol"] == "BRKB"


def test_co_dated_kind_tiebreak_discloses_losers():
    earn = _earnings(date(2026, 10, 10), label="earn")
    cpi = _macro("cpi", date(2026, 10, 10), label="cpi")
    rec = _bind(catalysts={"AAPL": [cpi, earn]}).record
    assert rec["binding_state"] == BOUND
    assert rec["catalyst"]["kind"] == "earnings"
    assert rec["catalyst"]["date"] == "2026-10-10"
    assert rec["catalyst"]["co_dated"] == [
        {
            "kind": "cpi",
            "date": "2026-10-10",
            "source": "engine.event_calendar",
            "artifact": "event_calendar.static",
            "label": "cpi",
        }
    ]
    assert len(rec["candidates"]) == 2


def test_window_includes_asof_and_expiry_dates():
    on_asof = _earnings(date(2026, 9, 4), label="on-asof")
    on_exp = _macro("cpi", date(2026, 10, 16), label="on-exp")
    rec_asof = _bind(catalysts={"AAPL": [on_asof]}).record
    assert rec_asof["binding_state"] == SAME_DAY_UNORDERED
    assert rec_asof["candidates"][0]["in_window"] is True
    assert rec_asof["candidates"][0]["date"] == "2026-09-04"
    rec_exp = _bind(catalysts={"AAPL": [on_exp]}).record
    assert rec_exp["binding_state"] == BOUND
    assert rec_exp["catalyst"]["date"] == "2026-10-16"
    assert rec_exp["catalyst"]["days_expiry_minus_catalyst"] == 0
    assert rec_exp["candidates"][0]["in_window"] is True


def test_zero_dte_expiry_equals_asof_is_ok():
    rec = _bind(_event(exp="2026-09-04")).record
    assert rec["expiry"]["state"] == "OK"
    assert rec["expiry"]["dte_calendar_days"] == 0
    assert rec["expiry"]["reason"] is None
    assert rec["binding_state"] == UNBOUND_NO_CATALYST
    assert rec["catalyst_reason"] == "no_candidates_for_root"


def test_horizon_edge_is_inclusive_then_closed():
    late_exp = "2026-12-18"
    on_edge = _macro("fomc", ASOF + timedelta(days=63), label="edge")
    past_edge = _macro("fomc", ASOF + timedelta(days=64), label="past")
    rec_in = _bind(
        _event(exp=late_exp),
        catalysts={"AAPL": [on_edge]},
        horizon_days=63,
    ).record
    assert rec_in["horizon_days"] == 63
    assert rec_in["binding_state"] == BOUND
    assert rec_in["catalyst"]["date"] == "2026-11-06"
    rec_out = _bind(
        _event(exp=late_exp),
        catalysts={"AAPL": [past_edge]},
        horizon_days=63,
    ).record
    assert rec_out["binding_state"] == UNBOUND_NO_CATALYST
    assert rec_out["catalyst_reason"] == "no_candidate_in_window"
    assert rec_out["candidates"][0]["in_window"] is False
    assert rec_out["candidates"][0]["date"] == "2026-11-07"


def test_stale_false_without_age_is_untrustworthy():
    cat = CatalystCandidate(
        kind="earnings",
        date=date(2026, 10, 10),
        source="engine.earnings_catalyst",
        artifact="earnings_store",
        stale=False,
        known_as_of=KNOWN_AS_OF,
        as_of_age_td=None,
        label="false-without-age",
    )
    rec = _bind(catalysts={"AAPL": [cat]}).record
    assert rec["binding_state"] == STALE_CATALYST
    assert rec["candidates"][0]["trusted"] is False
    assert rec["candidates"][0]["stale"] is False


# ── M5 same-day ───────────────────────────────────────────────────────────────


def test_same_day_catalyst_is_unordered_not_bound():
    rec = _bind(
        catalysts={"AAPL": [_earnings(date(2026, 9, 4), label="cpi-day")]},
    ).record
    assert rec["binding_state"] == SAME_DAY_UNORDERED
    assert rec["catalyst_state"] == SAME_DAY_UNORDERED
    assert rec["catalyst_reason"] == "same_day_unordered"
    assert rec["catalyst"]["date"] == "2026-09-04"
    assert rec["catalyst"]["days_expiry_minus_catalyst"] == 42


# ── minors ────────────────────────────────────────────────────────────────────


def test_dedupe_keeps_distinct_source_on_same_kind_date():
    a = _macro(
        "cpi",
        date(2026, 10, 8),
        source="engine.event_calendar",
        artifact="event_calendar.fred",
        locator="fred:CPIAUCSL",
        label="cpi-fred",
    )
    b = _macro(
        "cpi",
        date(2026, 10, 8),
        source="engine.event_calendar",
        artifact="event_calendar.static",
        locator="static:cpi",
        label="cpi-static",
    )
    rec = _bind(catalysts={"AAPL": [a, b]}).record
    assert rec["binding_state"] == BOUND
    assert len(rec["candidates"]) == 2
    artifacts = {c["artifact"] for c in rec["candidates"]}
    assert artifacts == {"event_calendar.fred", "event_calendar.static"}
    assert rec["catalyst"]["co_dated"][0]["artifact"] in artifacts
    assert rec["catalyst"]["artifact"] in artifacts
    assert rec["catalyst"]["artifact"] != rec["catalyst"]["co_dated"][0]["artifact"]


def test_expiry_before_asof_keeps_calendar_facts():
    rec = _bind(_event(exp="2026-09-03")).record
    assert rec["binding_state"] == EXPIRY_BEFORE_ASOF
    assert rec["expiry"]["state"] == EXPIRY_BEFORE_ASOF
    assert rec["expiry"]["reason"] == "expiry_before_asof"
    assert rec["expiry"]["dte_calendar_days"] == -1
    assert rec["expiry"]["is_third_friday"] is False
    assert rec["expiry"]["is_quad_witching"] is False
