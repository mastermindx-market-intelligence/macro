"""Free SIC label fill: only unambiguous chains are filled; the overlay never
overrides an existing label; every fill label is as-of-now and not era-correct."""
from __future__ import annotations

import gzip
import json

import numpy as np
import pandas as pd

import scripts.build_sp1500_sic_fill as fill
from scripts.build_group_breadth_history import membership_dated


def _sectors():
    return pd.DataFrame({
        "ticker": ["KEEP", "OK", "TWO", "LATE", "AMB", "NOSIC"],
        "basis": ["gics_current"] + ["unlabeled"] * 5,
        "sector": ["Energy"] + [None] * 5,
        "membership_start": pd.to_datetime(["2000-01-03"] * 6),
        "membership_end": pd.to_datetime([None] + ["2010-01-04"] * 5),
    })


def test_norm_name_strips_suffixes_and_punctuation():
    assert fill.norm_name("PRA Health Sciences, Inc.") == fill.norm_name("PRA HEALTH SCIENCES INC")
    assert fill.norm_name("Carrizo Oil & Gas Inc") == "CARRIZO OIL GAS"


def test_candidates_keep_only_unambiguous_chains():
    idx = pd.bdate_range("1999-06-01", "2010-01-04")
    closes = pd.DataFrame(1.0, index=idx, columns=["OK", "TWO", "AMB", "NOSIC"])
    closes["LATE"] = np.where(idx >= pd.Timestamp("2005-01-03"), 1.0, np.nan)   # reused ticker
    meta = pd.DataFrame({"ticker": ["OK", "TWO", "TWO", "LATE", "AMB", "NOSIC"],
                         "name": ["Okay Corp", "Two A Inc", "Two B Inc", "Late Co", "Amb Inc", "Nosic Inc"]})
    lookup = {"OKAY": {1}, "TWO A": {2}, "LATE": {3}, "AMB": {4, 5}, "NOSIC": {6}}
    cand, funnel = fill.candidates(_sectors(), meta, closes, lookup)
    assert sorted(cand["ticker"]) == ["NOSIC", "OK"]
    assert funnel == {"unlabeled": 5, "one_tiingo_company": 4, "series_covers_window_no_handover": 3, "one_sec_cik": 2}


def test_handover_inside_one_index_is_excluded():
    mem = pd.DataFrame({"ticker": ["GAS", "GAS", "FL", "FL", "OK"],
                        "src": ["sp500", "sp500", "sp500", "sp500", "sp500"],
                        "start_date": pd.to_datetime(["1996-01-02", "2011-12-13", "1996-01-02", "2016-04-04",
                                                      "2000-01-03"]),
                        "end_date": pd.to_datetime(["2011-12-12", "2016-07-01", "1999-01-04", "2019-08-09",
                                                    "2010-01-04"])})
    assert fill.handover_tickers(mem) == {"GAS"}     # FL re-entry years later is not a handover
    idx = pd.bdate_range("1990-01-01", "2016-07-01")
    closes = pd.DataFrame(1.0, index=idx, columns=["GAS", "OK"])
    sec = pd.DataFrame({"ticker": ["GAS", "OK"], "basis": "unlabeled", "sector": None,
                        "membership_start": pd.to_datetime(["1996-01-02", "2000-01-03"])})
    meta = pd.DataFrame({"ticker": ["GAS", "OK"], "name": ["Agl Resources Inc", "Okay Corp"]})
    cand, _ = fill.candidates(sec, meta, closes, {"AGL RESOURCES": {1}, "OKAY": {2}}, mem)
    assert list(cand["ticker"]) == ["OK"]


def test_build_writes_as_of_now_labels_only_when_sic_maps(tmp_path, monkeypatch):
    bd = tmp_path / "breadth"
    bd.mkdir()
    _sectors().to_parquet(bd / "sp1500_pit_sectors.parquet")
    pd.DataFrame({"ticker": ["OK", "NOSIC"], "src": "sp500", "start_date": pd.to_datetime(["2000-01-03"] * 2),
                  "end_date": pd.to_datetime(["2010-01-04"] * 2)}).to_parquet(bd / "sp1500_pit_membership.parquet")
    idx = pd.bdate_range("1999-06-01", "2010-01-04")
    pd.DataFrame(1.0, index=idx, columns=["OK", "NOSIC"]).to_parquet(tmp_path / "c.parquet")
    with gzip.open(tmp_path / "meta.raw.gz", "wt") as f:
        json.dump([{"ticker": "ok", "name": "Okay Corp"}, {"ticker": "nosic", "name": "Nosic Inc"}], f)
    (tmp_path / "lookup.txt").write_text("OKAY CORP:0000000001:\nNOSIC INC:0000000006:\n")
    subs = {1: {"sic": "1311", "sicDescription": "Crude Petroleum & Natural Gas", "name": "OKAY CORP"},
            6: {"sic": "", "sicDescription": "", "name": "NOSIC INC"}}
    monkeypatch.setattr(fill, "_get_submissions", lambda cik: subs.get(cik))
    out = tmp_path / "fill.parquet"
    funnel = fill.build(bd, tmp_path / "meta.raw.gz", tmp_path / "c.parquet", tmp_path / "lookup.txt",
                        tmp_path / "cache.json", out)
    f = pd.read_parquet(out)
    assert funnel["filled"] == 1 and list(f["ticker"]) == ["OK"]
    assert f.loc[0, "sector"] == "Energy" and f.loc[0, "basis"] == "sic_derived_fill"
    assert not f["era_correct"].any() and "name" not in f.columns   # Tiingo names not written


def test_membership_dated_overlay_never_overrides(tmp_path):
    bd = tmp_path
    pd.DataFrame({"ticker": ["KEEP", "OK"], "src": "sp500",
                  "start_date": pd.to_datetime(["2000-01-03"] * 2),
                  "end_date": pd.to_datetime([None, "2010-01-04"])}).to_parquet(bd / "sp1500_pit_membership.parquet")
    pd.DataFrame({"ticker": ["KEEP", "OK"], "sector": ["Energy", None]}).to_parquet(bd / "sp1500_pit_sectors.parquet")
    without = membership_dated(bd, "sp500").set_index("ticker")["group"]
    assert pd.isna(without["OK"])
    pd.DataFrame({"ticker": ["KEEP", "OK"], "sector": ["Utilities", "Materials"]}).to_parquet(
        bd / "sp1500_pit_sectors_sic_fill.parquet")
    g = membership_dated(bd, "sp500").set_index("ticker")["group"]
    assert g["KEEP"] == "Energy" and g["OK"] == "Materials"
