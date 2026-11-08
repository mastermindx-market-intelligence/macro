"""Synthetic causal-vintage guards using the real unchanged owner and Canon math.

The calendar/decisions are declared fixtures, never real exchange/source proof.
"""
from datetime import date
from pathlib import Path
import copy
import sys
import math
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.entry_radar.replay.oscillator_mtf_research import (
    aggregate_owner_windows, oscillator_events,
)
from engine.entry_radar.replay.rs_pullback_launch_data import _aggregate, _metadata_errors

# Freeze the whole synthetic population before deleting or revising observations.
SYNTHETIC_DAYS = tuple(pd.bdate_range("2026-01-05", periods=40).date)
SYNTHETIC_PREDECESSORS = dict(zip(SYNTHETIC_DAYS, (date(2026, 1, 2),) + SYNTHETIC_DAYS[:-1]))
SYNTHETIC_CALENDAR = {
    day: (pd.Timestamp(day.isoformat() + " 09:30", tz="America/New_York").tz_convert("UTC"),
          pd.Timestamp(day.isoformat() + " 16:00", tz="America/New_York").tz_convert("UTC"))
    for day in SYNTHETIC_DAYS
}
CASES = [
    ("CANON_RSI_MACD", "2026-02-25T20:30:00+00:00", "2026-02-25T20:30:02Z"),
    ("PRICE_MACD_RSI_PROXY", "2026-02-19T20:30:00+00:00", "2026-02-19T20:30:02Z"),
]
LATE_KNOWN = "2026-02-28T21:00:00+00:00"
REPLAY_CUTOFF = "2026-02-28T23:00:00Z"


def synthetic_long_prefix(late_revision=False):
    rows, eligibility = [], {}
    for day in SYNTHETIC_DAYS:
        session = day.isoformat()
        opening, closing = SYNTHETIC_CALENDAR[day]
        prior = SYNTHETIC_PREDECESSORS[day].isoformat()
        for ordinal in range(3):
            start = opening + pd.Timedelta(minutes=ordinal * 120)
            end = start + pd.Timedelta(minutes=120)
            known = end + pd.Timedelta(seconds=2)
            i = len(rows)
            price = 100. + .15 * i + 3. * math.sin(i / 4.)
            row = dict(schema="macro.rs_oscillator_mtf_bars.v1", symbol="A",
                       session_date=session, grain_minutes=120,
                       bar_start_utc=start.isoformat(), bar_end_utc=end.isoformat(),
                       known_at_utc=known.isoformat(), source_sha256="a" * 64,
                       ohlcv=dict(open=price, high=price+1., low=price-1.,
                                  close=price, volume=100_000.),
                       status="FULL_KNOWN", refusals=[], source_admitted=False)
            rows.append(row)
            eligibility[("A", end.isoformat())] = dict(
                is_leader=True, known_at_utc=(opening-pd.Timedelta(days=1)).isoformat(),
                asof_session=prior, expected_prior_session=prior, receipt_sha256="b"*64)
        rows.append(dict(schema="macro.rs_oscillator_mtf_bars.v1", symbol="A",
            session_date=session, grain_minutes=120,
            bar_start_utc=(opening+pd.Timedelta(minutes=360)).isoformat(),
            bar_end_utc=closing.isoformat(), known_at_utc=None, source_sha256=None,
            ohlcv=None, status="STUB_EXCLUDED", refusals=["NONFULL_SESSION_STUB"],
            source_admitted=False, stub_minutes=30))
    late = pd.Timestamp(rows[-1]["bar_end_utc"]) + pd.Timedelta(days=1)
    if late_revision:
        rows[1]["known_at_utc"] = late.isoformat()
    return rows, eligibility, late


def owner_predecessors(_rows=None):
    # Never infer adjacency from the surviving observed rows.
    return dict(SYNTHETIC_PREDECESSORS)


def case_rows(indicator):
    rows, eligibility, _ = synthetic_long_prefix()
    if indicator == "PRICE_MACD_RSI_PROXY":
        for j, row in enumerate(r for r in rows if r["status"] == "FULL_KNOWN"):
            price = 100 - .2 * min(j, 100) + .05 * max(0, j-100)
            row["ohlcv"].update(open=price, high=price+1., low=price-1., close=price)
    return rows, eligibility


def corrected(row, known=LATE_KNOWN):
    result = copy.deepcopy(row)
    result["known_at_utc"] = known
    result["source_sha256"] = "c" * 64
    result["ohlcv"]["close"] -= 20.
    result["ohlcv"]["low"] = min(result["ohlcv"]["low"], result["ohlcv"]["close"]-1.)
    return result


def project_at(rows, decision, corrections=(), calls=None):
    """Synthetic raw slots; revision selection belongs to the incumbent owner.

    Each callback receives only this fixture's exact requested window versions.
    Metadata refusal and minute selection are the real unchanged owner functions.
    """
    receipt = {"source_ref": "SYNTHETIC_CONFORMANCE:oscillator-vintage", "receipt_sha256": "b"*64}
    metadata = {
        "security_id": "A", "availability_basis": "observed_first_seen",
        "identity": dict(receipt, security_id="A", known_at="2026-01-01T00:00:00Z",
                         valid_from="2026-01-01"),
        "basis": dict(receipt, known_at="2026-01-01T00:00:00Z", basis_id="synthetic-unadjusted",
                      price_adjustment="unadjusted", volume_adjustment="unadjusted",
                      corporate_actions_sha256="a"*64),
    }
    versions = {}
    for revision, row in enumerate([*rows, *corrections]):
        if row["status"] != "FULL_KNOWN":
            continue
        versions.setdefault((row["bar_start_utc"], row["bar_end_utc"]), []).append((revision, row))

    def reader(symbol, start, end, cutoff):
        assert symbol == "A"
        if calls is not None:
            calls.append(cutoff)
        session = pd.Timestamp(start).tz_convert("America/New_York").date().isoformat()
        stamp = pd.Timestamp(cutoff).to_pydatetime()
        errors = _metadata_errors(metadata, stamp, session)
        if errors:
            return {"availability": "unavailable", "refusals": errors}
        minutes = []
        for revision, row in versions.get((start, end), []):
            for minute in range(120):
                opened = pd.Timestamp(start) + pd.Timedelta(minutes=minute)
                prices = row["ohlcv"]
                minutes.append(dict(receipt, stream="stock", security_id="A",
                    basis_id="synthetic-unadjusted", revision_id=f"fixture-{revision}-{minute}",
                    start=opened.isoformat(), end=(opened+pd.Timedelta(minutes=1)).isoformat(),
                    known_at=row["known_at_utc"], open=prices["open"], high=prices["high"],
                    low=prices["low"], close=prices["close"], volume=prices["volume"]/120.))
        return _aggregate(minutes, "stock", metadata,
                          pd.Timestamp(start).to_pydatetime(), pd.Timestamp(end).to_pydatetime(), stamp)

    return aggregate_owner_windows(symbol="A", calendar=SYNTHETIC_CALENDAR,
        decision_utc=decision, minutes=120, read_aggregate=reader)


def declared_events(bars, eligibility, indicator, target, decision, candidate_id="frozen-opportunity"):
    return oscillator_events(bars=bars, indicator=indicator, eligibility=eligibility,
        prior_session_by_day=SYNTHETIC_PREDECESSORS, decision_cutoff_utc=REPLAY_CUTOFF,
        original_decisions={("A", target): {"candidate_id": candidate_id, "decision_at": decision}})


def target_event(events, target):
    return next(x for x in events if x["bar_end_utc"] == target)


@pytest.mark.parametrize("indicator,target,decision", CASES)
def test_current_candle_revision_cannot_reclassify_original_opportunity(indicator, target, decision):
    rows, eligibility = case_rows(indicator)
    current = next(r for r in rows if r["bar_end_utc"] == target)
    expected = 121.90660360109061 if indicator == "CANON_RSI_MACD" else 80.05
    assert current["ohlcv"]["close"] == pytest.approx(expected)
    calls = []
    original = project_at(rows, decision, calls=calls)
    before = declared_events(original, eligibility, indicator, target, decision)
    assert target_event(before, target)["state"] == "CROSS_OBSERVED"
    assert set(calls) == {pd.Timestamp(decision).isoformat()}
    correction = corrected(current)
    after = project_at(rows, decision, corrections=[correction])
    assert after == original
    assert declared_events(after, eligibility, indicator, target, decision) == before

    # The same later snapshot that reproduced CROSS -> NO_CROSS before repair
    # cannot impersonate the original, even with its original candidate identity.
    late = project_at(rows, REPLAY_CUTOFF, corrections=[correction])
    refused = target_event(declared_events(late, eligibility, indicator, target, decision), target)
    assert refused["state"] == "SOURCE_HISTORICAL_REVISION_UNAVAILABLE"
    assert refused["candidate_id"] == "frozen-opportunity"
    assert refused["decision_at_utc"] == pd.Timestamp(decision).isoformat()
    assert refused["signal"] is None and refused["issued_at_utc"] is None


@pytest.mark.parametrize("indicator,target,decision", CASES)
def test_batch_warmup_and_current_revisions_cannot_move_original_clock(indicator, target, decision):
    rows, eligibility = case_rows(indicator)
    originals = project_at(rows, decision)
    before = declared_events(originals, eligibility, indicator, target, decision)
    assert target_event(before, target)["signal"] is True
    corrections = [corrected(r) for r in rows if r["status"] == "FULL_KNOWN"]
    assert project_at(rows, decision, corrections) == originals
    later = project_at(rows, REPLAY_CUTOFF, corrections)
    event = target_event(declared_events(later, eligibility, indicator, target, decision), target)
    assert event["state"] == "SOURCE_HISTORICAL_REVISION_UNAVAILABLE"
    assert event["issued_at_utc"] is None


@pytest.mark.parametrize("indicator,target,decision", CASES)
def test_future_early_bar_revision_cannot_backdate_canonical_oscillator(indicator, target, decision):
    rows, eligibility = case_rows(indicator)
    correction = corrected(rows[1])
    originals = project_at(rows, decision)
    assert project_at(rows, decision, [correction]) == originals
    assert target_event(declared_events(originals, eligibility, indicator, target, decision), target)["signal"] is True
    later = project_at(rows, REPLAY_CUTOFF, [correction])
    event = target_event(declared_events(later, eligibility, indicator, target, decision), target)
    assert event["state"] == "SOURCE_HISTORICAL_REVISION_UNAVAILABLE"
    assert event["signal"] is None and event["issued_at_utc"] is None


@pytest.mark.parametrize("indicator", ["CANON_RSI_MACD", "PRICE_MACD_RSI_PROXY"])
def test_later_genuine_post_revision_session_can_be_classified_again(indicator):
    rows, eligibility = case_rows(indicator)
    target, decision = "2026-02-27T20:30:00+00:00", "2026-02-27T20:30:02Z"
    correction = corrected(rows[1], known="2026-02-10T21:00:00Z")
    projection = project_at(rows, decision, [correction])
    event = target_event(declared_events(projection, eligibility, indicator, target, decision,
                                         candidate_id="distinct-later-opportunity"), target)
    assert event["signal"] is not None
    assert event["candidate_id"] == "distinct-later-opportunity"
    assert event["issued_at_utc"] == pd.Timestamp(decision).isoformat()
    assert pd.Timestamp(event["inputs_known_at_utc"]) <= pd.Timestamp(decision)


@pytest.mark.parametrize("indicator,target,decision", CASES)
def test_unretained_original_current_vintage_retains_unavailable_opportunity(indicator, target, decision):
    rows, eligibility = case_rows(indicator)
    rows = [corrected(r) if r["bar_end_utc"] == target else r for r in rows]
    projection = project_at(rows, decision)
    event = target_event(declared_events(projection, eligibility, indicator, target, decision), target)
    assert event["state"] == "SOURCE_UNAVAILABLE"
    assert event["candidate_id"] == "frozen-opportunity"
    assert event["signal"] is None and event["issued_at_utc"] is None


@pytest.mark.parametrize("indicator,target,decision", CASES)
def test_every_consumed_warmup_bar_requires_the_original_projection_cutoff(indicator, target, decision):
    rows, eligibility = case_rows(indicator)
    projection = project_at(rows, decision)
    projection[1]["projection_cutoff_utc"] = REPLAY_CUTOFF
    event = target_event(declared_events(projection, eligibility, indicator, target, decision), target)
    assert event["state"] == "SOURCE_ORIGINAL_VINTAGE_UNAVAILABLE"
    assert event["signal"] is None


@pytest.mark.parametrize("indicator,target,decision", CASES)
def test_undeclared_warmup_opportunities_do_not_shorten_valid_indicator_prefix(indicator, target, decision):
    rows, eligibility = case_rows(indicator)
    projection = project_at(rows, decision)
    events = declared_events(projection, eligibility, indicator, target, decision)
    event = target_event(events, target)
    assert event["state"] == "CROSS_OBSERVED"
    assert len(events) == len(projection)
    assert all(e["state"] == "ORIGINAL_DECISION_UNAVAILABLE" and e["signal"] is None
               for e, bar in zip(events, projection)
               if bar["status"] == "FULL_KNOWN" and bar["bar_end_utc"] != target)
    assert projection[-1]["status"] == "STUB_EXCLUDED"


def test_synthetic_owner_mapping_is_not_reconstructed_after_session_deletion():
    rows, eligibility = case_rows("CANON_RSI_MACD")
    projection = project_at(rows, "2026-02-25T20:30:02Z")
    shortened = [r for r in projection if r["session_date"] != "2026-02-17"]
    assert owner_predecessors(shortened)[date(2026, 2, 18)] == date(2026, 2, 17)
    with pytest.raises(ValueError, match="missing owner predecessor session"):
        declared_events(shortened, eligibility, "CANON_RSI_MACD",
                        "2026-02-25T20:30:00+00:00", "2026-02-25T20:30:02Z")
