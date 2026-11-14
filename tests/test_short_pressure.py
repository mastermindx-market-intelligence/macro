"""Short-pressure axes + IBKR borrow collector — trap pins.

Every test here pins a defect that was MEASURED on live data during the
2026-08-05 build, not a hypothetical. Each one fails if its guard is removed.
"""
from __future__ import annotations

import pandas as pd
import pytest

from collectors import ibkr_borrow
from engine import short_pressure as sp


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def isolated_data_root(monkeypatch, tmp_path):
    """Keep implicit native borrow reads inside each test's temporary store."""
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)


def _panel(rows):
    df = pd.DataFrame(rows)
    df["settlement_date"] = pd.to_datetime(df["settlement_date"])
    df["knowable_date"] = df["settlement_date"] + pd.Timedelta(days=10)
    if "is_listed" not in df:
        df["is_listed"] = True
    if "dtc_capped" not in df:
        df["dtc_capped"] = df["days_to_cover"] >= sp.DTC_SENTINEL
    return df


def _wide_panel(settlement="2026-07-15", n=400, listed=True, dtc_start=1.0, adv=5e5):
    """A cross-section wide enough to clear MIN_CROSS_SECTION."""
    return _panel([
        {"ticker": f"T{i:04d}", "days_to_cover": dtc_start + i * 0.01,
         "si_change_pct": 1.0, "short_shares": 1e6, "settlement_date": settlement,
         "is_listed": listed, "avg_daily_vol": adv}
        for i in range(n)
    ])


# --------------------------------------------------------------------------
# TRAP 1 — the 999.99 days-to-cover sentinel
# --------------------------------------------------------------------------
def test_sentinel_rows_are_excluded_from_the_percentile_basis():
    """FINRA caps days_to_cover at 999.99 when ADV rounds to 0 — 17.8% of all
    rows on the live feed, so the RAW column's p90 IS the sentinel. If capped
    rows enter the basis, every real name's percentile is crushed downward."""
    real = _wide_panel(n=300)
    capped = _panel([{"ticker": f"C{i:04d}", "days_to_cover": 999.99,
                      "si_change_pct": 0.0, "short_shares": 1e6,
                      "settlement_date": "2026-07-15"} for i in range(300)])
    panel = pd.concat([real, capped], ignore_index=True)

    xs = sp.cross_section(asof="2026-08-01", si_panel=panel, borrow=None)

    # the most-shorted REAL name must still rank at the top of the cross-section
    top = xs.loc["T0299", "dtc_pctile"]
    assert top >= 99.0, (
        f"top real name ranked {top} — sentinel rows leaked into the basis "
        "(they would occupy the entire top half)")
    # sentinel rows must carry no days_to_cover value at all
    assert pd.isna(xs.loc["C0000", "days_to_cover"])
    assert bool(xs.loc["C0000", "dtc_capped"])


def test_dtc_change_refuses_to_difference_against_a_sentinel():
    """A change measured from 999.99 to 3.0 is a data artifact, not a -997 day
    collapse in cover burden."""
    prev = _panel([{"ticker": "AAA", "days_to_cover": 999.99, "si_change_pct": 0,
                    "short_shares": 1e6, "settlement_date": "2026-06-30"}])
    cur = _panel([{"ticker": "AAA", "days_to_cover": 3.0, "si_change_pct": 0,
                   "short_shares": 1e6, "settlement_date": "2026-07-15"}])
    panel = pd.concat([prev, cur], ignore_index=True)

    xs = sp.cross_section(asof="2026-08-01", si_panel=panel, borrow=None)
    assert pd.isna(xs.loc["AAA", "dtc_change"]), \
        "differenced against the ADV-zero sentinel — that is a fiction, not a move"


# --------------------------------------------------------------------------
# TRAP 2 — OTC contamination of the cross-section
# --------------------------------------------------------------------------
def test_otc_rows_do_not_enter_the_percentile_basis():
    """The live feed is ~42% OTC by row count and OTC carries nearly all the
    sentinels. Percentiles must be taken over exchange-listed names only."""
    listed = _wide_panel(n=250, listed=True, dtc_start=1.0)
    otc = _panel([{"ticker": f"O{i:04d}", "days_to_cover": 500.0 + i,
                   "si_change_pct": 0.0, "short_shares": 1e6,
                   "settlement_date": "2026-07-15", "is_listed": False}
                  for i in range(250)])
    panel = pd.concat([listed, otc], ignore_index=True)

    xs = sp.cross_section(asof="2026-08-01", si_panel=panel, borrow=None)
    top_listed = xs.loc["T0249", "dtc_pctile"]
    assert top_listed >= 99.0, (
        f"most-shorted listed name ranked {top_listed} — OTC names leaked into "
        "the basis and pushed every listed name down")


# --------------------------------------------------------------------------
# PIT LAW — knowable_date, never settlement_date
# --------------------------------------------------------------------------
def test_asof_uses_knowable_date_not_settlement_date():
    """FINRA disseminates ~7 days after the settlement date. A backtest that
    joins on settlement_date reads positions roughly a week before anyone could
    have seen them."""
    panel = _panel([{"ticker": "AAA", "days_to_cover": 5.0, "si_change_pct": 0,
                     "short_shares": 1e6, "settlement_date": "2026-07-15"}])
    # settlement has passed, publication has NOT
    assert sp.asof_slice(panel, asof="2026-07-20").empty, \
        "row surfaced before its knowable_date — that is look-ahead"
    assert not sp.asof_slice(panel, asof="2026-07-26").empty


def test_panel_without_knowable_date_raises_rather_than_silently_degrading():
    """A legacy panel lacking the PIT column must fail loudly. Falling back to
    settlement_date would make every downstream backtest quietly optimistic."""
    stale = _panel([{"ticker": "AAA", "days_to_cover": 5.0, "si_change_pct": 0,
                     "short_shares": 1e6, "settlement_date": "2026-07-15"}])
    stale = stale.drop(columns=["knowable_date"])
    with pytest.raises(KeyError, match="knowable_date"):
        sp.asof_slice(stale, asof="2026-08-01")


# --------------------------------------------------------------------------
# TRAP 3b — thin-ADV days-to-cover is a division artifact, not short pressure
# --------------------------------------------------------------------------
def test_thin_volume_names_cannot_top_the_cross_section():
    """Measured on the live 2026-07-15 listed cross-section: of the 75 names with
    DTC >= 50, ALL 75 have ADV under 100k and their MEDIAN ADV is 36 shares a day.
    Unlike the 999.99 sentinel these are plausible-looking numbers, so without a
    liquidity floor a 'most heavily shorted' ranking is 100% artifact."""
    liquid = _wide_panel(n=300, dtc_start=1.0, adv=5e5)      # tops out ~4 days
    thin = _panel([{"ticker": f"Z{i:03d}", "days_to_cover": 500.0 + i,
                    "si_change_pct": 0.0, "short_shares": 1e6,
                    "settlement_date": "2026-07-15", "avg_daily_vol": 36.0}
                   for i in range(50)])
    xs = sp.cross_section(asof="2026-08-01",
                          si_panel=pd.concat([liquid, thin], ignore_index=True),
                          borrow=None)
    # thin names must not be ranked at all...
    assert xs.loc["Z000", "dtc_pctile"] is pd.NA or pd.isna(xs.loc["Z000", "dtc_pctile"]), \
        "a 36-shares-a-day name received a days-to-cover percentile"
    # ...and the real cross-section must be undisturbed by them
    assert xs.loc["T0299", "dtc_pctile"] >= 99.0

    out = sp.axes("Z000", asof="2026-08-01", xs=xs)
    leg = [x for x in out["legs"] if x["axis"] == "days_to_cover"][0]
    assert leg["elevated"] is None, "a division artifact was reported as elevated short pressure"
    assert "too thin" in leg["reading"]


def test_percentile_reading_never_claims_one_hundred_percent():
    xs = sp.cross_section(asof="2026-08-01", si_panel=_wide_panel(n=300), borrow=None)
    out = sp.axes("T0299", asof="2026-08-01", xs=xs)
    leg = [x for x in out["legs"] if x["axis"] == "days_to_cover"][0]
    assert "100% of" not in leg["reading"], leg["reading"]


# --------------------------------------------------------------------------
# STALENESS — an 8.5-year panel resurrects delisted tickers
# --------------------------------------------------------------------------
def test_tickers_that_stopped_reporting_are_absent_not_stale():
    """Measured on the real panel: 'newest settlement per ticker' returned 48,539
    names at asof 2026-08-01 when the newest settlement carries only ~22k. The
    excess is delisted/renamed symbols surfacing with years-old readings dressed
    as current."""
    live = _wide_panel(settlement="2026-07-15", n=300)
    dead = _panel([{"ticker": "GONE", "days_to_cover": 40.0, "si_change_pct": 0,
                    "short_shares": 1e6, "settlement_date": "2019-05-15"}])
    panel = pd.concat([live, dead], ignore_index=True)

    s = sp.asof_slice(panel, asof="2026-08-01")
    assert "GONE" not in s.index, \
        "a ticker last reported in 2019 surfaced as a current reading"
    assert "T0000" in s.index


def test_a_name_missing_one_settlement_still_survives():
    """The staleness cut must not be so tight it drops a name that merely skipped
    a single bi-monthly report."""
    live = _wide_panel(settlement="2026-07-15", n=300)
    skipped = _panel([{"ticker": "SKIP", "days_to_cover": 6.0, "si_change_pct": 0,
                       "short_shares": 1e6, "settlement_date": "2026-06-30"}])
    s = sp.asof_slice(pd.concat([live, skipped], ignore_index=True), asof="2026-08-01")
    assert "SKIP" in s.index


# --------------------------------------------------------------------------
# schema stability — absent data reads as null, never as a missing column
# --------------------------------------------------------------------------
def test_borrow_columns_exist_even_when_no_capture_covers_the_date():
    """The borrow accrual starts 2026-08-05, so every historical asof has no
    capture. Dropping the columns would AttributeError every consumer on exactly
    the dates the 2018-> panel exists to support."""
    panel = _wide_panel(settlement="2019-12-13", n=300)
    xs = sp.cross_section(asof="2020-01-01", si_panel=panel, borrow=None)
    assert not xs.empty
    for col in ("borrow_fee_pct", "borrow_htb", "borrow_severe",
                "avail_shares", "avail_unlimited"):
        assert col in xs.columns, f"{col} vanished instead of reading null"
    assert not xs["borrow_htb"].any()

    out = sp.axes("T0299", asof="2020-01-01", xs=xs)
    assert out is not None
    fee_leg = [x for x in out["legs"] if x["axis"] == "borrow_fee"][0]
    assert fee_leg["value"] is None and fee_leg["elevated"] is None


# --------------------------------------------------------------------------
# TRAP 3 — borrow fee is near-constant in our universe
# --------------------------------------------------------------------------
def test_borrow_fee_uses_absolute_thresholds_not_a_percentile():
    """Measured 2026-08-05: in-universe fee median 0.35%, p99 1.25%, ZERO names
    above 20%. A percentile would label the 0.42% name 'expensive' purely by
    rank. Only an absolute threshold can say 'this is ordinary'."""
    panel = _wide_panel(n=300)
    borrow = pd.DataFrame({
        "ticker": [f"T{i:04d}" for i in range(300)],
        # a realistic flat general-collateral distribution
        "fee_pct": [0.25 + i * 0.0005 for i in range(300)],
        "avail_shares": [1e6] * 300, "avail_unlimited": [False] * 300,
        "date": pd.to_datetime(["2026-07-30"] * 300),
    })
    xs = sp.cross_section(asof="2026-08-01", si_panel=panel, borrow=borrow)
    # the single most expensive name is still only ~0.40% — ordinary, not HTB
    assert not xs["borrow_htb"].any(), \
        "flagged a general-collateral name as hard-to-borrow — fee was ranked, not measured"

    borrow.loc[0, "fee_pct"] = 7.5
    xs2 = sp.cross_section(asof="2026-08-01", si_panel=panel, borrow=borrow)
    assert bool(xs2.loc["T0000", "borrow_htb"])
    assert bool(xs2.loc["T0000", "borrow_severe"])


# --------------------------------------------------------------------------
# abstention
# --------------------------------------------------------------------------
def test_thin_cross_section_abstains_rather_than_printing_a_percentile():
    panel = _wide_panel(n=10)
    xs = sp.cross_section(asof="2026-08-01", si_panel=panel, borrow=None)
    assert xs["dtc_pctile"].isna().all(), \
        "printed a percentile off a 10-name cross-section"


# --------------------------------------------------------------------------
# THE FUSION BAN — SM2-R3 / "positioning fusion is ILLEGAL"
# --------------------------------------------------------------------------
def test_axes_emits_printed_legs_and_no_fused_score():
    """SM2-R3: no function may combine short-derived axes into a single number.
    The output must expose legs; any float summary key would be a fused score."""
    panel = _wide_panel(n=300)
    out = sp.axes("T0299", asof="2026-08-01", xs=sp.cross_section(
        asof="2026-08-01", si_panel=panel, borrow=None))
    assert out is not None
    assert isinstance(out["legs"], list) and len(out["legs"]) >= 4
    banned = {"score", "composite", "rank", "weight", "alpha", "signal", "conviction"}
    assert not banned & set(out), f"fused-score key present: {banned & set(out)}"
    # agree_count must be an integer COUNT of printed legs, never a weighted sum
    assert isinstance(out["agree_count"], int)
    assert out["agree_count"] <= out["measured_count"]


def test_authority_contract_is_display_only():
    assert sp.AUTHORITY["tier"] == "display"
    assert not any(sp.AUTHORITY[k] for k in ("may_rank", "may_size", "may_gate"))
    panel = _wide_panel(n=300)
    out = sp.axes("T0000", asof="2026-08-01",
                  xs=sp.cross_section(asof="2026-08-01", si_panel=panel, borrow=None))
    assert out["authority"]["tier"] == "display"


def test_state_carries_no_directional_verb_and_no_squeeze_vocabulary():
    """The axes are ungraded, so a buy/sell verb would be an uncomputed stance;
    'squeeze' is banned outright (DO_NOT_REBUILD line 139 forbids shortening a
    flow reading to 'short squeeze')."""
    banned = ("squeeze", "buy", "sell", "short the", "long the",
              "bullish", "bearish", "avoid", "trim")
    for n_elev in range(6):
        for n_meas in range(6):
            s = sp._state(n_elev, n_meas).lower()
            for w in banned:
                assert w not in s, f"state {s!r} contains banned word {w!r}"


def test_every_reading_ships_the_ungraded_disclosure():
    panel = _wide_panel(n=300)
    out = sp.axes("T0299", asof="2026-08-01", xs=sp.cross_section(
        asof="2026-08-01", si_panel=panel, borrow=None))
    assert "not been answered" in out["grading_note"]


# --------------------------------------------------------------------------
# IBKR collector parse contract
# --------------------------------------------------------------------------
_HEAD = "#BOF|2026.08.05|07:17:12\n#SYM|CUR|NAME|CON|ISIN|REBATERATE|FEERATE|AVAILABLE|FIGI|\n"


def test_unlimited_availability_is_a_flag_not_a_number():
    """IBKR writes '>10000000' for names with abundant supply. Coercing it to
    10_000_000 invents a precise tightness reading for exactly the names that
    are NOT tight; coercing to 0 inverts the meaning entirely."""
    txt = _HEAD + "AAPL|USD|Apple Inc|1|US0378331005|3.4|0.41|>10000000|BBG1|\n"
    df, _ = ibkr_borrow._parse(txt)
    row = df.iloc[0]
    assert bool(row["avail_unlimited"])
    assert pd.isna(row["avail_shares"]), \
        "'>10000000' was coerced to a number — that is an invented quantity"


def test_parse_survives_a_pipe_inside_the_issuer_name():
    """Fields are read from the right precisely so a pipe in free-text NAME
    cannot shift every column after it."""
    txt = _HEAD + "XYZ|USD|Acme | Holdings Inc|9|US9|2.1|1.75|450000|BBG9|\n"
    df, _ = ibkr_borrow._parse(txt)
    row = df.iloc[0]
    assert row["ticker"] == "XYZ"
    assert row["fee_pct"] == pytest.approx(1.75)
    assert row["avail_shares"] == pytest.approx(450000)


def test_bond_and_non_usd_lines_are_dropped():
    """The live file carries CUSIP-shaped bond rows (049323AB4) and a handful of
    EUR/CAD lines that would otherwise pollute an equity panel."""
    txt = (_HEAD
           + "049323AB4|USD|CB ATLAS BOND|1|X|3.3|0.25|300000|BBG0|\n"
           + "SAP|EUR|SAP SE|2|X|1.0|0.30|100000|BBG2|\n"
           + "MSFT|USD|Microsoft|3|X|3.3|0.25|>10000000|BBG3|\n")
    df, _ = ibkr_borrow._parse(txt)
    assert set(df["ticker"]) == {"MSFT"}


def test_snapshot_date_and_clock_are_captured():
    """The feed mutates intraday (observed 07:01:33 -> 07:17:12 in 16 minutes),
    so a row is only comparable with its capture clock attached."""
    txt = _HEAD + "MSFT|USD|Microsoft|3|X|3.3|0.25|500000|BBG3|\n"
    df, stamp = ibkr_borrow._parse(txt)
    assert stamp == "07:17:12"
    assert df.iloc[0]["date"] == pd.Timestamp("2026-08-05")
    assert df.iloc[0]["snapshot_et"] == "07:17:12"


# Missing comparative evidence must abstain, not vote negative.
def _missing_measurement_axes(**updates):
    row=dict(days_to_cover=None,dtc_pctile=None,dtc_change=None,si_change_pct=None,
             borrow_fee_pct=None,avail_shares=None,avail_unlimited=False,
             thin_adv=False,dtc_capped=False,settlement_date='2026-10-30')
    row.update(updates)
    return sp.axes('SYN',xs=pd.DataFrame([row],index=['SYN']))

@pytest.mark.parametrize('missing',[None,float('nan'),pd.NA])
def test_missing_changes_do_not_establish_coverage(missing):
    r=_missing_measurement_axes(dtc_change=missing,si_change_pct=missing)
    assert r['measured_count']==0
    assert not r['coverage_ok']
    assert r['state']=='not enough short-side data to describe'

@pytest.mark.parametrize('key',['dtc_change','si_change_pct'])
@pytest.mark.parametrize('value',[-1.0,0.0,1.0])
def test_one_observation_is_not_two_measurements(key,value):
    r=_missing_measurement_axes(**{key:value})
    assert r['measured_count']==1
    assert not r['coverage_ok']
    assert r['agree_count']==int(value>0)

@pytest.mark.parametrize('value',[-1.0,0.0,1.0])
def test_observed_zero_and_negative_changes_remain_measured(value):
    r=_missing_measurement_axes(dtc_change=value,si_change_pct=value)
    assert r['measured_count']==2
    assert r['coverage_ok']
    assert r['agree_count']==2*int(value>0)

@pytest.mark.parametrize('missing',[None,float('nan'),pd.NA])
def test_raw_cover_burden_without_comparator_is_not_negative_evidence(missing):
    r=_missing_measurement_axes(days_to_cover=3.0,dtc_pctile=missing)
    leg=next(x for x in r['legs'] if x['axis']=='days_to_cover')
    assert leg['value']==3.0
    assert leg['reading']=='3.0 days of average volume to buy back'
    assert leg['elevated'] is None
    assert r['measured_count']==0

@pytest.mark.parametrize('pct',[0.0,30.0,79.9,80.0,100.0])
def test_observed_comparator_is_measured_without_invented_change_axes(pct):
    r=_missing_measurement_axes(days_to_cover=3.0,dtc_pctile=pct)
    assert r['measured_count']==1
    assert r['agree_count']==int(pct>=80)

@pytest.mark.parametrize('fee',[0.0,0.5,1.0,5.0])
def test_borrow_only_does_not_inherit_two_phantom_measurements(fee):
    r=_missing_measurement_axes(borrow_fee_pct=fee)
    assert r['measured_count']==1
    assert not r['coverage_ok']
    assert r['agree_count']==int(fee>=1)

@pytest.mark.parametrize('av,unlimited',[(None,False),(0.0,False),(450000.0,False),(None,True)])
def test_availability_does_not_substitute_for_missing_directional_measures(av,unlimited):
    r=_missing_measurement_axes(avail_shares=av,avail_unlimited=unlimited)
    assert r['measured_count']==0
    assert not r['coverage_ok']

def test_complete_comparison_and_threshold_contract_unchanged():
    r=_missing_measurement_axes(days_to_cover=3.0,dtc_pctile=90.0,dtc_change=1.0,
           si_change_pct=0.0,borrow_fee_pct=0.5)
    assert (r['measured_count'],r['agree_count'],r['coverage_ok'])==(4,2,True)
    assert r['state']=='2 short-side readings stand out together'
    assert not any(r['authority'][k] for k in ['may_rank','may_size','may_gate'])




def test_absent_short_evidence_abstains_through_native_parquet_loaders(monkeypatch, tmp_path):
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    (tmp_path / "finra").mkdir()
    pd.DataFrame([{
        "ticker": "SYN", "settlement_date": pd.Timestamp("2026-10-30"),
        "knowable_date": pd.Timestamp("2026-11-11"), "days_to_cover": None,
        "dtc_capped": False, "is_listed": True, "avg_daily_vol": 500000,
        "si_change_pct": None, "short_shares": 1000000,
    }]).to_parquet(tmp_path / "finra/short_interest_panel.parquet", index=False)
    result = sp.axes("SYN", xs=sp.cross_section(asof="2026-11-12"))
    assert all(leg["value"] is None for leg in result["legs"])
    assert result["measured_count"] == result["agree_count"] == 0
    assert not result["coverage_ok"]
    assert result["state"] == "not enough short-side data to describe"
    assert not any(result["authority"][k] for k in ("may_rank", "may_size", "may_gate"))

@pytest.mark.parametrize('prior', [False, True])
@pytest.mark.parametrize('dtc', [0., .1, 3., 8., 20.])
@pytest.mark.parametrize('sic', [None, -2., 0., 2.])
def test_retained_ticker_cannot_compare_its_settlement_to_itself(prior, dtc, sic):
    rows = [dict(ticker='SYN',settlement_date='2026-10-15',days_to_cover=dtc,si_change_pct=sic),
            dict(ticker='LIVE',settlement_date='2026-10-30',days_to_cover=4.,si_change_pct=0.)]
    if prior:
        rows.append(dict(ticker='SYN',settlement_date='2026-09-30',days_to_cover=dtc+7.,si_change_pct=sic))
    xs=sp.cross_section(asof='2026-11-12', si_panel=_panel(rows), borrow=pd.DataFrame())
    result=sp.axes('SYN',xs=xs)
    leg=next(x for x in result['legs'] if x['axis']=='dtc_change')
    assert pd.isna(xs.loc['SYN','dtc_change'])
    assert leg['value'] is None and leg['elevated'] is None
    assert result['measured_count']==int(sic is not None)
    assert not result['coverage_ok']
    assert result['state']=='not enough short-side data to describe'


def test_distinct_global_endpoints_preserve_real_zero_and_pit_transition(monkeypatch,tmp_path):
    from lib import config
    monkeypatch.setattr(config,'data_dir',lambda:tmp_path)
    (tmp_path/'finra').mkdir()
    panel=_panel([
        dict(ticker='SYN',settlement_date='2026-09-30',days_to_cover=8.,si_change_pct=0.),
        dict(ticker='SYN',settlement_date='2026-10-15',days_to_cover=8.,si_change_pct=0.),
        dict(ticker='LIVE',settlement_date='2026-10-30',days_to_cover=4.,si_change_pct=0.)])
    panel.loc[panel.ticker=='LIVE','knowable_date']=pd.Timestamp('2026-11-11')
    panel.to_parquet(tmp_path/'finra/short_interest_panel.parquet',index=False)
    early=sp.axes('SYN',xs=sp.cross_section(asof='2026-11-10'))
    late=sp.axes('SYN',xs=sp.cross_section(asof='2026-11-11'))
    leg=lambda x:next(y for y in x['legs'] if y['axis']=='dtc_change')
    assert leg(early)['value']==0. and leg(early)['elevated'] is False
    assert early['measured_count']==2 and early['coverage_ok']
    assert leg(late)['value'] is None and leg(late)['elevated'] is None
    assert late['measured_count']==1 and not late['coverage_ok']
    assert late['settlement_date']==early['settlement_date']

# Synthetic finite-admission regressions; these do not assert live incidence.
@pytest.mark.parametrize('bad', [float('inf'), -float('inf'), 'inf', '-Infinity'])
@pytest.mark.parametrize('field,axis', [('days_to_cover','days_to_cover'), ('dtc_change','dtc_change'), ('si_change_pct','si_change_pct'), ('borrow_fee_pct','borrow_fee'), ('avail_shares','availability')])
def test_nonfinite_axes_abstain_and_serialize(field, axis, bad):
    import json
    xs = pd.DataFrame([{field: bad}], index=['SYN'])
    payload = sp.axes('SYN', xs=xs)
    assert next(leg for leg in payload['legs'] if leg['axis'] == axis)['value'] is None
    assert payload['measured_count'] == 0
    assert not payload['coverage_ok']
    json.dumps(payload, allow_nan=False)

@pytest.mark.parametrize('n', [199, 200, 250])
@pytest.mark.parametrize('field', ['days_to_cover', 'avg_daily_vol'])
@pytest.mark.parametrize('bad', [float('inf'), -float('inf')])
def test_nonfinite_population_cannot_dilute_valid_peers(n, field, bad):
    good = _wide_panel(n=n)
    invalid = _wide_panel(n=200, dtc_start=500.)
    invalid['ticker'] = ['X'+str(i) for i in range(200)]
    invalid['dtc_capped'] = False
    invalid[field] = bad
    clean = sp.cross_section(asof='2026-08-01', si_panel=good, borrow=pd.DataFrame())
    mixed = sp.cross_section(asof='2026-08-01', si_panel=pd.concat([good, invalid]), borrow=pd.DataFrame())
    pd.testing.assert_series_equal(clean.dtc_pctile, mixed.loc[clean.index, 'dtc_pctile'])
    assert mixed.loc[invalid.ticker, 'dtc_pctile'].isna().all()
    if n < 200:
        assert mixed.dtc_pctile.isna().all()
    else:
        assert mixed.loc[f'T{n-1:04d}', 'dtc_pctile'] == 100.

@pytest.mark.parametrize('bad', [float('inf'), -float('inf')])
@pytest.mark.parametrize('endpoint', ['previous', 'current'])
def test_nonfinite_endpoint_cannot_be_a_change(endpoint, bad):
    old = _wide_panel(settlement='2026-07-01', n=1)
    new = _wide_panel(settlement='2026-07-15', n=1)
    (old if endpoint == 'previous' else new)['days_to_cover'] = bad
    (old if endpoint == 'previous' else new)['dtc_capped'] = False
    xs = sp.cross_section(asof='2026-08-01', si_panel=pd.concat([old,new]), borrow=pd.DataFrame())
    assert pd.isna(xs.loc['T0000','dtc_change'])

def test_finite_endpoint_subtraction_overflow_abstains():
    old = _wide_panel(settlement='2026-07-01', n=1)
    new = _wide_panel(settlement='2026-07-15', n=1)
    old['days_to_cover'], new['days_to_cover'] = -1e308, 1e308
    old['dtc_capped'] = new['dtc_capped'] = False
    xs = sp.cross_section(asof='2026-08-01', si_panel=pd.concat([old,new]), borrow=pd.DataFrame())
    assert pd.isna(xs.loc['T0000','dtc_change'])
