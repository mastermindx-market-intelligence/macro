"""Tests for scripts/c19_wp31_sources.py — the C19 WP31 SOURCES module.

Synthetic fixtures only (lane law R1): no network, no file under data/, no
real EPS / price / return / estimate / consensus / label value for AAPL, DHI,
PHM, KBH or TOL.  Every expected market cutoff is derived from the repo's own
calendar libs (``lib/exchange_holidays.early_close`` + ``lib/us_cash_calendar.
is_session``); where a literal date appears, the lib predicate for that date
is asserted in the same test so the lib, not the packet example, is the truth
(rerun rule R2).
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from scripts import c19_wp31_sources as sources
from engine.k3e_expectation_surface import ATTEMPTS_PATH, OBSERVATIONS_PATH
from lib.exchange_holidays import early_close
from lib.us_cash_calendar import is_session

_ET = ZoneInfo("America/New_York")
UTC = timezone.utc


def _close_utc(day: date) -> datetime:
    """Expected scheduled close of a session ``day``, derived from the libs."""
    close_local = early_close("US", day) or time(16)
    return datetime.combine(day, close_local, _ET).astimezone(UTC)


def _dt(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# cutoff_for
# ---------------------------------------------------------------------------


def test_cutoff_after_close_release_same_day() -> None:
    t_rel = datetime(2026, 10, 21, 20, 5, tzinfo=UTC)
    expected = _close_utc(date(2026, 10, 21))
    assert is_session(date(2026, 10, 21))
    assert early_close("US", date(2026, 10, 21)) is None  # regular 16:00 ET day
    assert sources.cutoff_for(t_rel) == expected
    assert expected == datetime(2026, 10, 21, 20, 0, tzinfo=UTC)  # EDT close


def test_cutoff_pre_open_release_uses_previous_session_close() -> None:
    t_rel = datetime(2026, 10, 21, 11, 0, tzinfo=UTC)
    assert is_session(date(2026, 10, 20))
    assert sources.cutoff_for(t_rel) == _close_utc(date(2026, 10, 20))
    assert sources.cutoff_for(t_rel) == datetime(2026, 10, 20, 20, 0, tzinfo=UTC)


def test_cutoff_release_exactly_at_close_belongs_to_previous_session() -> None:
    # "Strictly before t_rel": a release at exactly 16:00:00 ET (20:00Z EDT)
    # belongs to the PREVIOUS session's close.
    t_rel = datetime(2026, 10, 21, 20, 0, 0, tzinfo=UTC)
    cutoff = sources.cutoff_for(t_rel)
    assert cutoff == _close_utc(date(2026, 10, 20))
    assert cutoff < t_rel


def test_cutoff_monday_pre_open_skips_weekend() -> None:
    monday = date(2026, 10, 19)
    friday = date(2026, 10, 16)
    assert monday.weekday() == 0
    assert not is_session(date(2026, 10, 18)) and not is_session(date(2026, 10, 17))
    assert is_session(friday)
    t_rel = datetime(2026, 10, 19, 11, 30, tzinfo=UTC)
    assert sources.cutoff_for(t_rel) == _close_utc(friday)


def test_cutoff_morning_after_full_holiday_skips_it() -> None:
    thanksgiving = date(2026, 11, 26)
    assert not is_session(thanksgiving)  # full closure in the announced slate
    assert holiday_name_is_thanksgiving(thanksgiving)
    t_rel = datetime(2026, 11, 27, 12, 0, tzinfo=UTC)  # Friday morning
    expected = _close_utc(date(2026, 11, 25))
    assert is_session(date(2026, 11, 25))
    assert sources.cutoff_for(t_rel) == expected
    assert expected == datetime(2026, 11, 25, 21, 0, tzinfo=UTC)  # EST close


def holiday_name_is_thanksgiving(day: date) -> bool:
    from lib.exchange_holidays import holiday_name

    return holiday_name("US", day) == "Thanksgiving"


def test_cutoff_early_close_day_after_thanksgiving() -> None:
    friday = date(2026, 11, 27)
    assert is_session(friday)
    if early_close("US", friday) is not None:
        t_rel = datetime(2026, 11, 30, 12, 0, tzinfo=UTC)  # Monday pre-open
        expected = _close_utc(friday)
        assert sources.cutoff_for(t_rel) == expected
        assert expected == datetime(2026, 11, 27, 18, 0, tzinfo=UTC)  # 13:00 EST
    else:  # the lib wins: no early close -> regular 16:00 close
        t_rel = datetime(2026, 11, 30, 12, 0, tzinfo=UTC)
        assert sources.cutoff_for(t_rel) == _close_utc(friday)


def test_cutoff_dst_boundary_november_est_close() -> None:
    # After the DST fall-back, the 16:00 local close is 21:00Z, not 20:00Z.
    thursday = date(2026, 11, 19)
    assert is_session(thursday)
    t_rel = datetime(2026, 11, 20, 14, 0, tzinfo=UTC)  # Friday pre-open (EST now)
    cutoff = sources.cutoff_for(t_rel)
    assert cutoff == _close_utc(thursday)
    assert cutoff == datetime(2026, 11, 19, 21, 0, tzinfo=UTC)
    assert cutoff.astimezone(_ET).time() == time(16, 0)


def test_cutoff_christmas_eve_early_close_then_holiday() -> None:
    assert not is_session(date(2026, 12, 25))  # Christmas Day closure
    t_rel = datetime(2026, 12, 28, 12, 0, tzinfo=UTC)  # Monday pre-open
    assert sources.cutoff_for(t_rel) == _close_utc(date(2026, 12, 24))


def test_cutoff_naive_datetime_raises_value_error() -> None:
    with pytest.raises(ValueError):
        sources.cutoff_for(datetime(2026, 10, 21, 20, 5))


def test_cutoff_returns_aware_utc() -> None:
    cutoff = sources.cutoff_for(datetime(2026, 10, 21, 11, 0, tzinfo=UTC))
    assert cutoff.tzinfo == UTC
    assert cutoff.utcoffset() == timedelta_zero()


def timedelta_zero():
    from datetime import timedelta

    return timedelta(0)


# ---------------------------------------------------------------------------
# is_eligible
# ---------------------------------------------------------------------------


def test_is_eligible_prereg_commit_instant_itself_is_false() -> None:
    assert sources.is_eligible(sources.PREREG_COMMIT_TIME) is False


def test_is_eligible_one_second_after_prereg_commit_is_true() -> None:
    from datetime import timedelta

    later = sources.PREREG_COMMIT_TIME + timedelta(seconds=1)
    assert sources.is_eligible(later) is True
    assert sources.PREREG_COMMIT_TIME == datetime(2026, 10, 17, 12, 1, 44, tzinfo=UTC)


def test_is_eligible_naive_raises_value_error() -> None:
    with pytest.raises(ValueError):
        sources.is_eligible(datetime(2026, 11, 1, 12, 0))


# ---------------------------------------------------------------------------
# enumerate_episodes
# ---------------------------------------------------------------------------


def _eightk(ticker: str, acc: str, accepted: str, report_date: str,
            *, items: str = "2.02,9.01", form: str = "8-K",
            exhibits: tuple[str, ...] | None = ("EX-99.1",)) -> dict:
    row = {
        "ticker": ticker, "cik": 320193, "accession": acc, "form": form,
        "filing_date": report_date, "acceptance_datetime": accepted,
        "report_date": report_date, "items": items,
    }
    if exhibits is not None:
        row["exhibits"] = list(exhibits)
    return row


def test_enumerate_drops_non_universe_issuer() -> None:
    rows = [_eightk("XYZZ", "0000000000-26-000101",
                    "2026-10-29T20:05:00.000Z", "2026-10-29")]
    assert sources.enumerate_episodes(rows) == []


def test_enumerate_drops_missing_item_202() -> None:
    for items in ("9.01", "12.02,9.01", "2.020", ""):
        rows = [_eightk("AAPL", "0000000000-26-000102",
                        "2026-10-29T20:05:00.000Z", "2026-10-29", items=items)]
        assert sources.enumerate_episodes(rows) == [], items


def test_enumerate_drops_amended_and_other_forms() -> None:
    # prereg §2: the release is a Form 8-K; amendments and other forms never qualify.
    for form in ("8-K/A", "8-K12B", "6-K", "10-Q", " 8-k ", ""):
        rows = [_eightk("AAPL", "0000000000-26-000109",
                        "2026-10-29T20:05:00.000Z", "2026-10-29", form=form)]
        assert sources.enumerate_episodes(rows) == [], form
    rows = [_eightk("AAPL", "0000000000-26-000109",
                    "2026-10-29T20:05:00.000Z", "2026-10-29", form=" 8-K ")]
    assert len(sources.enumerate_episodes(rows)) == 1


def test_enumerate_drops_missing_exhibit_991() -> None:
    without_key = [_eightk("AAPL", "0000000000-26-000103",
                           "2026-10-29T20:05:00.000Z", "2026-10-29",
                           exhibits=None)]
    assert sources.enumerate_episodes(without_key) == []
    wrong_exhibit = [_eightk("AAPL", "0000000000-26-000104",
                             "2026-10-29T20:05:00.000Z", "2026-10-29",
                             exhibits=("EX-99.2", "10.1"))]
    assert sources.enumerate_episodes(wrong_exhibit) == []


def test_enumerate_two_filings_for_one_quarter_keeps_the_earlier() -> None:
    # Both anchors (2026-08-05 and 2026-08-12) map to AAPL FYE-9 quarter end
    # 2026-06-30 -> the same (issuer, q); the earlier acceptance must win.
    # Clocks follow the submissions-JSON convention (prereg §10 A2): the raw value
    # runs 4h ahead in EDT, so 00:10 "Z" on the 6th is 20:10Z on the 5th.
    early = _eightk("AAPL", "0000000000-26-000110",
                    "2026-08-06T00:10:00.000Z", "2026-08-05")
    late = _eightk("AAPL", "0000000000-26-000111",
                   "2026-08-13T00:10:00.000Z", "2026-08-12")
    episodes = sources.enumerate_episodes([late, early])
    assert len(episodes) == 1
    assert episodes[0]["t_rel"] == "2026-08-05T20:10:00Z"
    assert episodes[0]["q"] == "2026Q3"
    assert episodes[0]["period_end"] == "2026-06-30"


def test_enumerate_status_exposed_before_prereg_commit_time() -> None:
    rows = [_eightk("DHI", "0000000000-26-000120",
                    "2026-10-16T20:05:00.000Z", "2026-10-15")]
    episodes = sources.enumerate_episodes(rows)
    assert [ep["status"] for ep in episodes] == ["EXPOSED"]


def test_enumerate_status_eligible_after_prereg_commit_time() -> None:
    rows = [_eightk("DHI", "0000000000-26-000121",
                    "2026-10-29T20:05:00.000Z", "2026-10-29")]
    episodes = sources.enumerate_episodes(rows)
    assert [ep["status"] for ep in episodes] == ["ELIGIBLE"]


def test_enumerate_episode_shape_is_the_shared_dict() -> None:
    rows = [_eightk("PHM", "0000000000-26-000130",
                    "2026-10-29T20:05:00.000Z", "2026-10-29")]
    (episode,) = sources.enumerate_episodes(rows)
    assert set(episode) == {
        "issuer", "cluster", "q", "period_end", "t_rel", "cutoff", "status",
        "not_evaluable_reason", "label", "k", "s", "a0",
    }
    assert "returns" not in episode
    assert episode["issuer"] == "PHM"
    assert episode["cluster"] == "HOMEBUILDERS"
    t_rel = _dt(episode["t_rel"])
    assert _dt(episode["cutoff"]) == sources.cutoff_for(t_rel)
    assert episode["q"] == "2026Q3" and episode["period_end"] == "2026-09-30"  # PHM FYE Dec
    assert episode["label"] is None and episode["not_evaluable_reason"] is None
    assert episode["k"]["abstain_reason"] is None and episode["k"]["average"] is None
    assert episode["s"]["q_minus_1_resolved"] is False
    assert episode["a0"]["sign"] is None


def test_enumerate_empty_input_returns_empty_list() -> None:
    assert sources.enumerate_episodes([]) == []
    assert sources.enumerate_episodes([{"ticker": "AAPL"}]) == []


# prereg §10 A2: the submissions-JSON acceptanceDateTime carries a "Z" suffix but is
# Eastern wall-clock time read as UTC, so it runs |ET offset| ahead of true UTC.
# Pins from non-universe filings (MSFT); the header <ACCEPTANCE-DATETIME> agrees.


def test_edgar_json_clock_edt_and_est_pins() -> None:
    fix = sources._edgar_json_acceptance_utc
    assert fix("2026-07-30T00:04:53.000Z") == datetime(2026, 7, 29, 20, 4, 53, tzinfo=UTC)
    assert fix("2026-01-29T02:04:38.000Z") == datetime(2026, 1, 28, 21, 4, 38, tzinfo=UTC)


def test_edgar_json_clock_dst_transitions_are_unresolvable() -> None:
    fix = sources._edgar_json_acceptance_utc
    assert fix("2026-03-08T09:00:00Z") is None   # spring-forward hour
    assert fix("2026-11-01T08:00:00Z") is None   # fall-back hour


def test_edgar_json_clock_rejects_missing_and_garbage() -> None:
    fix = sources._edgar_json_acceptance_utc
    for value in (None, "", "garbage"):
        assert fix(value) is None, value


def test_enumerate_corrects_the_json_clock_to_true_utc() -> None:
    rows = [_eightk("DHI", "0000000000-26-000140",
                    "2026-10-29T20:05:00.000Z", "2026-10-29")]
    (episode,) = sources.enumerate_episodes(rows)
    assert episode["t_rel"] == "2026-10-29T16:05:00Z"  # EDT: 4h behind the raw value
    assert episode["status"] == "ELIGIBLE"


def test_enumerate_unresolvable_clock_alone_mints_no_episode() -> None:
    rows = [_eightk("DHI", "0000000000-26-000141",
                    "2026-11-01T08:00:00Z", "2026-11-01")]
    assert sources.enumerate_episodes(rows) == []


def test_enumerate_unresolvable_clock_blocks_a_later_eligible_filing() -> None:
    # prereg §10 A3: a same-quarter Item 2.02 row whose clock cannot be ordered may be
    # the true first release, so the kept filing is not evaluable — never shifted.
    unordered = _eightk("DHI", "0000000000-26-000142",
                        "2026-11-01T08:00:00Z", "2026-11-01")
    kept = _eightk("DHI", "0000000000-26-000143",
                   "2026-10-29T20:05:00.000Z", "2026-10-29")
    (episode,) = sources.enumerate_episodes([kept, unordered])
    assert episode["status"] == "NOT_EVALUABLE"
    assert episode["not_evaluable_reason"] == "earlier_release_filing_dropped"
    assert episode["t_rel"] == "2026-10-29T16:05:00Z"


def test_enumerate_earlier_filing_without_exhibit_blocks_the_kept_one() -> None:
    dropped = _eightk("PHM", "0000000000-26-000150",
                      "2026-10-28T20:05:00.000Z", "2026-10-28", exhibits=None)
    kept = _eightk("PHM", "0000000000-26-000151",
                   "2026-10-29T20:05:00.000Z", "2026-10-29")
    (episode,) = sources.enumerate_episodes([kept, dropped])
    assert episode["status"] == "NOT_EVALUABLE"
    assert episode["not_evaluable_reason"] == "earlier_release_filing_dropped"
    assert episode["t_rel"] == "2026-10-29T16:05:00Z"  # never shifted to another filing


def test_enumerate_later_dropped_filing_leaves_the_kept_one_eligible() -> None:
    kept = _eightk("PHM", "0000000000-26-000152",
                   "2026-10-29T20:05:00.000Z", "2026-10-29")
    later = _eightk("PHM", "0000000000-26-000153",
                    "2026-10-30T20:05:00.000Z", "2026-10-30", exhibits=None)
    (episode,) = sources.enumerate_episodes([later, kept])
    assert episode["status"] == "ELIGIBLE"
    assert episode["not_evaluable_reason"] is None


def test_enumerate_same_accession_shadow_is_the_kept_filing_itself() -> None:
    kept = _eightk("PHM", "0000000000-26-000154",
                   "2026-10-29T20:05:00.000Z", "2026-10-29")
    echo = _eightk("PHM", "0000000000-26-000154",
                   "2026-10-29T20:05:00.000Z", "2026-10-29", exhibits=None)
    (episode,) = sources.enumerate_episodes([echo, kept])
    assert episode["status"] == "ELIGIBLE"


def test_enumerate_exposed_episode_keeps_its_status_with_earlier_shadow() -> None:
    dropped = _eightk("DHI", "0000000000-26-000155",
                      "2026-10-15T20:05:00.000Z", "2026-10-15", exhibits=None)
    kept = _eightk("DHI", "0000000000-26-000156",
                   "2026-10-16T20:05:00.000Z", "2026-10-15")
    (episode,) = sources.enumerate_episodes([kept, dropped])
    assert episode["status"] == "EXPOSED"
    assert episode["not_evaluable_reason"] is None


def test_enumerate_shadow_only_quarter_mints_no_episode() -> None:
    rows = [_eightk("TOL", "0000000000-26-000157",
                    "2026-11-20T21:05:00.000Z", "2026-11-20", exhibits=None)]
    assert sources.enumerate_episodes(rows) == []


# ---------------------------------------------------------------------------
# k_from_surface (synthetic DataFrames / row mappings only)
# ---------------------------------------------------------------------------


def _prov() -> dict:
    return {
        "source_revision": "a" * 40,
        "inputs": {
            OBSERVATIONS_PATH: {"sha256": "b" * 64, "git_blob_id": "c" * 40},
            ATTEMPTS_PATH: {"sha256": "d" * 64, "git_blob_id": "e" * 40},
        },
    }


def _surface_rows(group_hash: str, attempt_id: str, clock: str,
                  average: float, year_ago: float,
                  period_end: str = "2026-06-30") -> tuple[list[dict], list[dict]]:
    common = {
        "collection_session_id": "sess-1", "attempt_id": attempt_id,
        "provider": "yfinance", "provider_record_class": "earnings_estimate",
        "provider_payload_hash": group_hash, "ticker_compat": "AAPL",
        "metric": "EPS", "horizon_label_raw": "0q", "missingness_reason": None,
        "provider_observed_at": clock, "system_observed_at": clock,
        "period_end": period_end, "rights_class": None,
    }
    observations = [
        {**common, "observation_id": f"{group_hash}-avg", "observation_type": "average",
         "value": average},
        {**common, "observation_id": f"{group_hash}-ya", "observation_type": "year_ago",
         "value": year_ago},
    ]
    attempts = [{
        "attempt_id": attempt_id, "collection_session_id": "sess-1",
        "provider": "yfinance", "ticker_compat": "AAPL",
        "attempted_at": "2026-10-19T17:00:00Z", "completed_at": "2026-10-19T17:00:30Z",
        "status": "success", "response_payload_hash": group_hash,
    }]
    return observations, attempts


_CUTOFF = datetime(2026, 10, 20, 20, 0, tzinfo=UTC)


def test_k_picks_newest_group_at_or_below_cutoff() -> None:
    older, older_att = _surface_rows("hash-OLD", "att-old", "2026-10-18T20:00:00Z",
                                    1.11, 1.00)
    newer, newer_att = _surface_rows("hash-NEW", "att-new", "2026-10-19T18:00:00Z",
                                     2.22, 2.05)
    k = sources.k_from_surface(older + newer, older_att + newer_att,
                               cutoff=_CUTOFF, period_end="2026-06-30",
                               source_provenance=_prov())
    assert k["average"] == 2.22 and k["year_ago"] == 2.05
    assert k["observed_at"] == "2026-10-19T18:00:00Z"
    assert k["abstain_reason"] is None
    assert k["record_ids"] == ["hash-NEW-avg", "hash-NEW-ya"]


def test_k_ignores_group_observed_after_cutoff() -> None:
    inside, inside_att = _surface_rows("hash-IN", "att-in", "2026-10-19T18:00:00Z",
                                       2.22, 2.05)
    after, after_att = _surface_rows("hash-AFTER", "att-after",
                                     "2026-10-21T05:00:00Z", 9.99, 9.90)
    k = sources.k_from_surface(inside + after, inside_att + after_att,
                               cutoff=_CUTOFF, period_end="2026-06-30",
                               source_provenance=_prov())
    assert k["average"] == 2.22  # the after-cutoff group is never read
    assert k["observed_at"] == "2026-10-19T18:00:00Z"


def test_k_only_after_cutoff_group_abstains_missing_without_reason() -> None:
    after, after_att = _surface_rows("hash-AFTER", "att-after",
                                     "2026-10-21T05:00:00Z", 9.99, 9.90)
    k = sources.k_from_surface(after, after_att, cutoff=_CUTOFF,
                               period_end="2026-06-30", source_provenance=_prov())
    assert k["average"] is None and k["year_ago"] is None
    assert k["observed_at"] is None and k["abstain_reason"] is None


def test_k_period_mismatch_abstains() -> None:
    rows, att = _surface_rows("hash-M", "att-m", "2026-10-19T18:00:00Z",
                              3.10, 3.00, period_end="2026-09-30")
    k = sources.k_from_surface(rows, att, cutoff=_CUTOFF,
                               period_end="2026-06-30", source_provenance=_prov())
    assert k["abstain_reason"] == "period_mismatch"
    assert k["average"] is None and k["year_ago"] is None


def test_k_null_period_end_abstains_period_mismatch() -> None:
    rows, att = _surface_rows("hash-N", "att-n", "2026-10-19T18:00:00Z",
                              3.10, 3.00)
    for row in rows:
        row["period_end"] = None
    k = sources.k_from_surface(rows, att, cutoff=_CUTOFF,
                               period_end=date(2026, 6, 30),
                               source_provenance=_prov())
    assert k["abstain_reason"] == "period_mismatch"


def test_k_period_within_seven_days_is_accepted() -> None:
    rows, att = _surface_rows("hash-P", "att-p", "2026-10-19T18:00:00Z",
                              3.10, 3.00, period_end="2026-06-24")  # 6 days off
    k = sources.k_from_surface(rows, att, cutoff=_CUTOFF,
                               period_end=date(2026, 6, 30),
                               source_provenance=_prov())
    assert k["abstain_reason"] is None
    assert k["average"] == 3.10


def test_k_query_refusal_maps_reason() -> None:
    rows, att = _surface_rows("hash-R", "att-r", "2026-10-19T18:00:00Z",
                              2.22, 2.05)
    k = sources.k_from_surface(rows, att, cutoff=_CUTOFF, period_end="2026-06-30",
                               source_provenance={"source_revision": "not-hex",
                                                  "inputs": {}})
    assert k["abstain_reason"] == "query_refusal:FULL_IMMUTABLE_SOURCE_REVISION_REQUIRED"
    assert k["average"] is None


def test_k_reads_lineage_fields() -> None:
    rows, att = _surface_rows("hash-L", "att-l", "2026-10-19T18:00:00Z",
                              2.22, 2.05)
    k = sources.k_from_surface(rows, att, cutoff=_CUTOFF, period_end="2026-06-30",
                               source_provenance=_prov())
    assert k["expectation_state"] == "CURRENT"
    assert k["identity_status"] == "NOT_CHECKED"
    assert k["attempt_status"] == "success"
    assert k["rights_class"] == "UNKNOWN"  # both consumed rows unlabeled (§10 A1)
    assert k["period_end"] == "2026-06-30"


def _k_with_rights(average_rights: object, year_ago_rights: object) -> dict:
    rows, att = _surface_rows("hash-RC", "att-rc", "2026-10-19T18:00:00Z", 2.22, 2.05)
    for row in rows:
        row["rights_class"] = (average_rights if row["observation_type"] == "average"
                               else year_ago_rights)
    return sources.k_from_surface(rows, att, cutoff=_CUTOFF, period_end="2026-06-30",
                                  source_provenance=_prov())


def test_k_rights_reads_both_consumed_rows() -> None:
    # prereg §10 A1: a label on either consumed row counts; disagreement is MIXED.
    assert _k_with_rights(None, "LICENSED")["rights_class"] == "MIXED:LICENSED,UNKNOWN"


def test_k_rights_absent_and_unknown_labels_read_as_unknown() -> None:
    assert _k_with_rights("unknown", None)["rights_class"] == "UNKNOWN"
    assert _k_with_rights("", None)["rights_class"] == "UNKNOWN"


def test_k_rights_agreeing_labels_are_normalized() -> None:
    assert _k_with_rights(" licensed ", "LICENSED")["rights_class"] == "LICENSED"


def test_k_accepts_synthetic_pandas_dataframes() -> None:
    rows, att = _surface_rows("hash-DF", "att-df", "2026-10-19T18:00:00Z",
                              2.22, 2.05)
    observations = pd.DataFrame(rows)
    attempts = pd.DataFrame(att)
    k = sources.k_from_surface(observations, attempts, cutoff=_CUTOFF,
                               period_end="2026-06-30", source_provenance=_prov())
    assert k["average"] == 2.22 and k["year_ago"] == 2.05
    assert k["attempt_status"] == "success"
    assert k["abstain_reason"] is None


# ---------------------------------------------------------------------------
# label_and_a0_from_companyfacts (synthetic companyfacts only)
# ---------------------------------------------------------------------------


def _facts(rows: list[dict]) -> dict:
    return {"facts": {"us-gaap": {"EarningsPerShareDiluted":
                                  {"units": {"USD/shares": rows}}}}}


def _fact(start: str, end: str, val: float, accn: str, form: str = "10-Q",
          **extra: object) -> dict:
    row = {"start": start, "end": end, "val": val, "accn": accn, "form": form,
           "filed": end}
    row.update(extra)
    return row


_Q_ACCESSION = "0000000000-26-000900"
_CUT = datetime(2026, 10, 20, 20, 0, tzinfo=UTC)


def _q_pair(current: float, prior: float) -> list[dict]:
    return [_fact("2026-04-01", "2026-06-30", current, _Q_ACCESSION),
            _fact("2025-04-01", "2025-06-30", prior, _Q_ACCESSION)]


def _read(rows: list[dict], *, cutoff=_CUT, prior_filings=()) -> dict:
    return sources.label_and_a0_from_companyfacts(
        _facts(rows), "2026-06-30", _Q_ACCESSION, cutoff, list(prior_filings))


def test_label_up() -> None:
    out = _read(_q_pair(2.50, 2.00))
    assert out["label"] == 1
    assert out["not_evaluable_reason"] is None


def test_label_down() -> None:
    out = _read(_q_pair(1.85, 2.00))
    assert out["label"] == -1
    assert out["not_evaluable_reason"] is None


def test_label_tie() -> None:
    out = _read(_q_pair(2.00, 2.00))
    assert out["label"] is None
    assert out["not_evaluable_reason"] == "label_tie"


def test_label_absent_comparative_is_none_without_reason() -> None:
    out = _read([_fact("2026-04-01", "2026-06-30", 2.50, _Q_ACCESSION)])
    assert out["label"] is None
    assert out["not_evaluable_reason"] is None  # caller decides label_unavailable


def test_label_amendment_form_ignored() -> None:
    rows = [_fact("2026-04-01", "2026-06-30", 2.50, _Q_ACCESSION, form="10-Q/A"),
            _fact("2025-04-01", "2025-06-30", 2.00, _Q_ACCESSION, form="10-Q/A")]
    out = _read(rows)
    assert out["label"] is None and out["not_evaluable_reason"] is None


def test_label_10_k_quarterly_contexts_accepted() -> None:
    k_rows = [_fact("2026-07-01", "2026-09-30", 1.35, _Q_ACCESSION, form="10-K"),
              _fact("2025-07-01", "2025-09-30", 1.20, _Q_ACCESSION, form="10-K")]
    out = sources.label_and_a0_from_companyfacts(
        _facts(k_rows), "2026-09-30", _Q_ACCESSION, _CUT, [])
    assert out["label"] == 1


def test_label_segment_context_ignored() -> None:
    rows = _q_pair(2.50, 2.00) + [
        _fact("2026-04-01", "2026-06-30", 9.99, _Q_ACCESSION,
              segment={"DataAxis": {"BusinessSegment": {"Dimension": "East"}}})]
    out = _read(rows)
    assert out["label"] == 1  # the segmented 9.99 never enters the comparison


def test_label_out_of_range_duration_ignored() -> None:
    ytd = [_fact("2026-01-01", "2026-06-30", 4.40, _Q_ACCESSION),   # 180 days
           _fact("2025-01-01", "2025-06-30", 4.00, _Q_ACCESSION)]
    out = _read(ytd)
    assert out["label"] is None and out["not_evaluable_reason"] is None
    off_by_one = [_fact("2026-03-23", "2026-06-30", 2.50, _Q_ACCESSION),  # 99 days
                  _fact("2025-04-01", "2025-06-30", 2.00, _Q_ACCESSION)]
    out = _read(off_by_one)
    assert out["label"] is None  # the 99-day context is not a three-month one


def test_a0_uses_q_minus_1_when_accepted_before_cutoff() -> None:
    q1 = "0000000000-26-000901"
    rows = _q_pair(2.50, 2.00) + [
        _fact("2026-01-01", "2026-03-31", 2.10, q1),
        _fact("2025-01-01", "2025-03-31", 2.05, q1)]
    out = _read(rows, prior_filings=[
        {"accession": q1, "accepted_at": "2026-04-30T20:30:00Z"}])
    assert out["a0"] == {"sign": 1, "period": "2026-03-31", "accession": q1,
                         "accepted_at": "2026-04-30T20:30:00Z"}


def test_a0_falls_back_from_late_q_minus_1_to_q_minus_2() -> None:
    q1 = "0000000000-26-000901"
    q2 = "0000000000-26-000902"
    rows = _q_pair(2.50, 2.00) + [
        _fact("2026-01-01", "2026-03-31", 2.10, q1),
        _fact("2025-01-01", "2025-03-31", 2.05, q1),
        _fact("2025-10-01", "2025-12-31", 1.90, q2),
        _fact("2024-10-01", "2024-12-31", 1.95, q2)]
    prior = [{"accession": q1, "accepted_at": "2026-11-02T20:30:00Z"},  # after _CUT
             {"accession": q2, "accepted_at": "2026-01-28T21:00:00Z"}]
    out = _read(rows, prior_filings=prior)
    assert out["a0"]["sign"] == -1
    assert out["a0"]["period"] == "2025-12-31"
    assert out["a0"]["accession"] == q2


def test_a0_none_when_no_prior_filing_accepted_before_cutoff() -> None:
    q1 = "0000000000-26-000901"
    rows = _q_pair(2.50, 2.00) + [
        _fact("2026-01-01", "2026-03-31", 2.10, q1),
        _fact("2025-01-01", "2025-03-31", 2.05, q1)]
    out = _read(rows, prior_filings=[
        {"accession": q1, "accepted_at": "2026-11-02T20:30:00Z"}])
    assert out["a0"]["sign"] is None
    out = _read(rows)  # no prior_filings at all -> unknowable acceptance, fail closed
    assert out["a0"]["sign"] is None


def test_a0_requires_both_contexts_in_the_original_filing() -> None:
    q1 = "0000000000-26-000901"
    rows = _q_pair(2.50, 2.00) + [
        _fact("2026-01-01", "2026-03-31", 2.10, q1)]  # comparative missing
    out = _read(rows, prior_filings=[
        {"accession": q1, "accepted_at": "2026-04-30T20:30:00Z"}])
    assert out["a0"]["sign"] is None


# ---------------------------------------------------------------------------
# apply_leak_rules
# ---------------------------------------------------------------------------


def _eligible_episode(**overrides: object) -> dict:
    rows = [_eightk("AAPL", "0000000000-26-000150",
                    "2026-10-29T20:05:00.000Z", "2026-10-29")]
    (episode,) = sources.enumerate_episodes(rows)
    episode.update(overrides)
    return episode


def test_leak_k_observed_after_cutoff_is_not_evaluable() -> None:
    episode = _eligible_episode()
    episode["k"]["observed_at"] = "2026-10-30T02:00:00Z"  # > cutoff 2026-10-29T20:00Z
    out = sources.apply_leak_rules(episode)
    assert out["status"] == "NOT_EVALUABLE"
    assert out["not_evaluable_reason"] == "pre_cutoff_leak"


def test_leak_a0_accepted_after_cutoff_is_not_evaluable() -> None:
    episode = _eligible_episode()
    episode["a0"]["accepted_at"] = "2026-10-29T20:00:01Z"  # one second after cutoff
    out = sources.apply_leak_rules(episode)
    assert out["status"] == "NOT_EVALUABLE"
    assert out["not_evaluable_reason"] == "pre_cutoff_leak"


def test_leak_pit_unrecoverable_flag_is_not_evaluable() -> None:
    episode = _eligible_episode(pit_unrecoverable=True)
    out = sources.apply_leak_rules(episode)
    assert out["status"] == "NOT_EVALUABLE"
    assert out["not_evaluable_reason"] == "pit_unrecoverable"


def test_leak_clean_episode_unchanged_and_non_eligible_preserved() -> None:
    episode = _eligible_episode()
    out = sources.apply_leak_rules(episode)
    assert out["status"] == "ELIGIBLE" and out["not_evaluable_reason"] is None
    exposed = _eligible_episode()
    exposed["status"] = "EXPOSED"
    exposed["k"]["observed_at"] = "2027-01-01T00:00:00Z"
    out = sources.apply_leak_rules(exposed)
    assert out["status"] == "EXPOSED"  # never upgraded, never silently cleared


# ---------------------------------------------------------------------------
# s_from_workspace stub
# ---------------------------------------------------------------------------


def test_s_from_workspace_raises_not_implemented_with_exact_message() -> None:
    with pytest.raises(NotImplementedError) as excinfo:
        sources.s_from_workspace("AAPL", cutoff=_CUT, anything=1)
    assert str(excinfo.value) == "S reader: owner-bound; seat wave 2"
