"""Offline tests for collectors/sp1500_pit_sectors.py (Trend Persistence Wave C-0).

Every test builds fixtures under tmp_path and passes ``data_dir=tmp_path``.
No network: ``_get_submissions`` is monkeypatched wherever network=True is used.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collectors import sp1500_pit_sectors as mod

TODAY = date(2026, 10, 3)
VALID_SECTORS = {
    "Communication Services", "Consumer Discretionary", "Consumer Staples", "Energy",
    "Financials", "Health Care", "Industrials", "Information Technology", "Materials",
    "Real Estate", "Utilities",
}


def _membership(rows):
    df = pd.DataFrame(rows, columns=["ticker", "start_date", "end_date", "src"])
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    return df


def _write(tmp_path, *, membership, ticker_sectors=None, dead=None, cik_sic=None,
           profiles=None, cache=None):
    b = tmp_path / "breadth"
    b.mkdir(parents=True, exist_ok=True)
    _membership(membership).to_parquet(b / "sp1500_pit_membership.parquet", index=False)
    if ticker_sectors is not None:
        pd.DataFrame(ticker_sectors, columns=["ticker", "sector", "source"]).to_parquet(
            b / "ticker_sectors.parquet", index=False)
    e = tmp_path / "edgar"
    if dead is not None:
        e.mkdir(parents=True, exist_ok=True)
        (e / "dead_name_cik.json").write_text(json.dumps(dead))
    if cik_sic is not None:
        e.mkdir(parents=True, exist_ok=True)
        (e / "cik_sic.json").write_text(json.dumps(cik_sic))
    if profiles is not None:
        p = tmp_path / "profile"
        p.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"sic_description": list(profiles.values())},
                     index=pd.Index(list(profiles), name="ticker")).to_parquet(
            p / "profiles.parquet")
    if cache is not None:
        (b / "_sp1500_pit_sic_cache.json").write_text(json.dumps(cache))


def _run(tmp_path, **kw):
    kw.setdefault("network", False)
    kw.setdefault("today", TODAY)
    return mod.build(tmp_path, **kw)


def _row(frame, t):
    return frame[frame["ticker"] == t].iloc[0]


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(mod.time, "sleep", lambda s: None)


def _no_network(monkeypatch):
    def boom(cik):
        raise AssertionError("network call attempted")
    monkeypatch.setattr(mod, "_get_submissions", boom)


# 1
def test_leaver_derivation(tmp_path):
    _write(tmp_path, membership=[
        ["CUR", "2010-01-01", None, "x"],
        ["REJOIN", "2005-01-01", "2008-01-01", "x"],
        ["REJOIN", "2012-01-01", None, "x"],
        ["GONE", "2001-01-01", "2003-05-05", "x"],
        ["GONE", "2004-01-01", "2009-09-09", "x"],
    ])
    f, _ = _run(tmp_path)
    assert bool(_row(f, "CUR").is_leaver) is False
    assert bool(_row(f, "REJOIN").is_leaver) is False
    assert pd.isna(_row(f, "REJOIN").membership_end)
    assert _row(f, "REJOIN").membership_start == pd.Timestamp("2005-01-01")
    g = _row(f, "GONE")
    assert bool(g.is_leaver) is True
    assert g.membership_start == pd.Timestamp("2001-01-01")
    assert g.membership_end == pd.Timestamp("2009-09-09")


# 2
def test_channel_priority_gics_beats_cik_bridge(tmp_path, monkeypatch):
    _no_network(monkeypatch)
    _write(tmp_path,
           membership=[["AAA", "2001-01-01", None, "x"]],   # CURRENT member keeps channel 1
           ticker_sectors=[["AAA", "Health Care", "gics_sp500"]],
           dead={"AAA": {"cik": 1, "method": "seed"}},
           cik_sic={"0000000001": {"sic": "1311", "sic_desc": "Crude Petroleum & Natural Gas"}})
    f, _ = _run(tmp_path, network=True)
    r = _row(f, "AAA")
    assert r.basis == "gics_current" and r.sector == "Health Care"


# 3
def test_sic_current_from_sic_mapped(tmp_path):
    _write(tmp_path, membership=[["BBB", "2001-01-01", None, "x"]],
           ticker_sectors=[["BBB", "Financials", "sic_mapped"]])
    f, _ = _run(tmp_path)
    r = _row(f, "BBB")
    assert r.basis == "sic_current" and r.sector == "Financials"


# 4  (R1: text map FIRST, numeric range FALLBACK)
def test_numeric_sic_via_cik_sic_and_text_first_order(tmp_path):
    _write(tmp_path,
           membership=[["EN", "2001-01-01", "2005-01-01", "x"],
                       ["TXT", "2001-01-01", "2005-01-01", "x"],
                       ["DIS", "2001-01-01", "2005-01-01", "x"],
                       ["RNG", "2001-01-01", "2005-01-01", "x"]],
           dead={"EN": {"cik": 1311, "method": "edgar_fts"},
                 "TXT": {"cik": 77, "method": "seed"},
                 "DIS": {"cik": 3651, "method": "seed"},
                 "RNG": {"cik": 88, "method": "seed"}},
           cik_sic={"0000001311": {"sic": "1311", "sic_desc": "Crude Petroleum & Natural Gas"},
                    # SIC 9999999 has no numeric range hit -> text map on sic_desc
                    "0000000077": {"sic": "9999999", "sic_desc": "National Commercial Banks"},
                    # the two maps DISAGREE: text = Consumer Discretionary, range = IT
                    "0000003651": {"sic": "3651", "sic_desc": "Household Audio & Video Equipment"},
                    # desc absent from the text map -> numeric range fallback (1311 = Energy)
                    "0000000088": {"sic": "1311", "sic_desc": "Not A Real SIC Description"}})
    assert mod._sic_range_to_sector(3651) == "Information Technology"   # premise of the pair
    assert mod._SIC_TEXT_MAP["Household Audio & Video Equipment"] == "Consumer Discretionary"
    f, rc = _run(tmp_path)
    en, txt = _row(f, "EN"), _row(f, "TXT")
    assert (en.basis, en.sector, int(en.sic), en.cik) == ("sic_derived", "Energy", 1311, "0000001311")
    assert en.cik_method == "edgar_fts"
    assert (txt.basis, txt.sector) == ("sic_derived", "Financials")
    dis = _row(f, "DIS")
    assert (dis.basis, dis.sector) == ("sic_derived", "Consumer Discretionary")   # text wins
    rng = _row(f, "RNG")
    assert (rng.basis, rng.sector) == ("sic_derived", "Energy")                   # range fallback
    assert rc["leavers_sic_on_disk_before_run"] == 4


# 5
def test_own_cache_hit_makes_no_network_call(tmp_path, monkeypatch):
    _no_network(monkeypatch)
    _write(tmp_path, membership=[["CCC", "2001-01-01", "2005-01-01", "x"]],
           dead={"CCC": {"cik": 5, "method": "seed"}},
           cache={"0000000005": {"sic": "6022", "sic_desc": "State Commercial Banks",
                                 "name": "C", "fetched_at": "2026-01-01"}})
    f, rc = _run(tmp_path, network=True)
    assert _row(f, "CCC").sector == "Financials"
    assert rc["network_lookups_performed"] == 0


# 6
def test_network_lookup_caches_and_counts(tmp_path, monkeypatch):
    calls = []

    def fake(cik):
        calls.append(cik)
        if cik == 10:
            return {"sic": "1311", "sicDescription": "Crude Petroleum & Natural Gas", "name": "X"}
        return {"sic": "", "sicDescription": "", "name": "Y"}

    monkeypatch.setattr(mod, "_get_submissions", fake)
    _write(tmp_path, membership=[["OIL", "2001-01-01", "2005-01-01", "x"],
                                 ["BLK", "2001-01-01", "2005-01-01", "x"]],
           dead={"OIL": {"cik": 10, "method": "seed"}, "BLK": {"cik": 11, "method": "seed"}})
    f, rc = _run(tmp_path, network=True)
    assert _row(f, "OIL").sector == "Energy" and _row(f, "OIL").basis == "sic_derived"
    assert _row(f, "BLK").basis == "unlabeled"
    assert rc["network_lookups_performed"] == 2 and rc["sic_blank_after_fetch"] == 1
    cache = json.loads((tmp_path / "breadth" / "_sp1500_pit_sic_cache.json").read_text())
    assert set(cache) == {"0000000010", "0000000011"}
    assert cache["0000000011"]["sic"] is None  # blank cached
    # re-run: no refetch, including the blank one
    monkeypatch.setattr(mod, "_get_submissions",
                        lambda c: (_ for _ in ()).throw(AssertionError("refetch")))
    _, rc2 = _run(tmp_path, network=True)
    assert rc2["network_lookups_performed"] == 0


# 7
def test_max_lookups_cap(tmp_path, monkeypatch):
    calls = []

    def fake(cik):
        calls.append(cik)
        return {"sic": "1311", "sicDescription": "Crude Petroleum & Natural Gas", "name": "X"}

    monkeypatch.setattr(mod, "_get_submissions", fake)
    tick = ["T1", "T2", "T3"]
    _write(tmp_path, membership=[[t, "2001-01-01", "2005-01-01", "x"] for t in tick],
           dead={t: {"cik": i + 1, "method": "seed"} for i, t in enumerate(tick)})
    f, rc = _run(tmp_path, network=True, max_lookups=2)
    assert len(calls) == 2
    assert rc["network_lookups_performed"] == 2 and rc["network_lookups_skipped_cap"] == 1
    assert (f["basis"] == "unlabeled").sum() == 1


# 8
def test_network_disabled_leaves_unlabeled(tmp_path, monkeypatch):
    _no_network(monkeypatch)
    _write(tmp_path, membership=[["DDD", "2001-01-01", "2005-01-01", "x"]],
           dead={"DDD": {"cik": 9, "method": "seed"}})
    f, rc = _run(tmp_path, network=False)
    assert _row(f, "DDD").basis == "unlabeled"
    assert rc["network_disabled"] is True and rc["network_lookups_performed"] == 0


# 9
def test_profiles_sic_description_fallback(tmp_path):
    _write(tmp_path, membership=[["EEE", "2001-01-01", None, "x"]],   # current member
           profiles={"EEE": "National Commercial Banks"})
    f, _ = _run(tmp_path)
    r = _row(f, "EEE")
    assert (r.basis, r.sector, r.sic_desc) == ("sic_derived", "Financials", "National Commercial Banks")


# 10
def test_invariants_and_receipt_sums(tmp_path):
    _write(tmp_path,
           membership=[["G", "2001-01-01", None, "x"], ["S", "2001-01-01", None, "x"],
                       ["D", "2001-01-01", "2004-01-01", "x"], ["U", "2001-01-01", "2004-01-01", "x"]],
           ticker_sectors=[["G", "Energy", "gics_sp400"], ["S", "Utilities", "sic_mapped"]],
           dead={"D": {"cik": 3, "method": "seed"}},
           cik_sic={"0000000003": {"sic": "6022", "sic_desc": "State Commercial Banks"}})
    f, rc = _run(tmp_path)
    assert list(f.columns) == mod.COLUMNS
    assert f["ticker"].tolist() == sorted(f["ticker"])
    assert not f["era_correct"].any() and rc["era_correct_count"] == 0
    assert set(f["basis"]) <= set(mod.BASES)
    assert f.loc[f["basis"] == "unlabeled", "sector"].isna().all()
    assert f.loc[f["basis"] != "unlabeled", "sector"].isin(VALID_SECTORS).all()
    assert sum(rc["basis_counts_all"].values()) == rc["denominator_all"] == 4
    assert sum(rc["basis_counts_leavers"].values()) == rc["denominator_leavers"] == 2
    assert set(rc["basis_counts_all"]) == set(mod.BASES)
    assert rc["unlabeled_leavers"] == 1 and rc["leavers_with_cik"] == 1
    assert "as-of-now" in rc["note"]
    on_disk = pd.read_parquet(tmp_path / "breadth" / "sp1500_pit_sectors.parquet")
    assert str(on_disk["sic"].dtype) == "Int64"
    assert on_disk["label_asof"].eq(pd.Timestamp(TODAY)).all()
    on_rc = json.loads((tmp_path / "breadth" / "_sp1500_pit_sectors_coverage.json").read_text())
    assert on_rc["label_asof"] == "2026-10-03"


# 10b  (R2: leavers are CIK-only; current members keep ticker channels)
def test_leavers_never_take_ticker_string_channels(tmp_path):
    # ECHO: leaver whose ticker string is in BOTH ticker_sectors and profiles (recycled ticker)
    # and has no CIK -> must stay unlabeled.
    _write(tmp_path,
           membership=[["ECHO", "2019-12-17", "2021-11-24", "x"],
                       ["ECHB", "2019-12-17", "2021-11-24", "x"],
                       ["BRG", "2001-01-01", "2005-01-01", "x"],
                       ["PRF", "2001-01-01", "2005-01-01", "x"],
                       ["CURR", "2001-01-01", None, "x"],
                       ["CPRF", "2001-01-01", None, "x"],
                       ["NONE", "2001-01-01", "2005-01-01", "x"]],
           ticker_sectors=[["ECHO", "Communication Services", "gics_sp500"],
                           ["ECHB", "Communication Services", "gics_sp500"],
                           ["BRG", "Energy", "gics_sp500"],
                           ["PRF", "Utilities", "sic_mapped"],
                           ["CURR", "Energy", "sic_mapped"]],
           dead={"ECHO": {"cik": None, "method": "unresolved"},
                 "ECHB": {"cik": 9, "method": "seed"},
                 "BRG": {"cik": 3, "method": "seed"}},
           cik_sic={"0000000003": {"sic": "6022", "sic_desc": "State Commercial Banks"},
                    "0000000009": {"sic": "1311", "sic_desc": "Crude Petroleum & Natural Gas"}},
           profiles={"ECHO": "National Commercial Banks", "PRF": "National Commercial Banks",
                     "CPRF": "National Commercial Banks"})
    f, rc = _run(tmp_path)
    echo = _row(f, "ECHO")
    assert (echo.is_leaver, echo.basis) == (True, "unlabeled")
    assert pd.isna(echo.sector) and pd.isna(echo.label_join)
    # a leaver in ticker_sectors whose CIK resolves is labeled by the CIK bridge, not the ticker map
    echb = _row(f, "ECHB")
    assert (echb.basis, echb.sector, echb.label_join) == ("sic_derived", "Energy", "cik")
    brg = _row(f, "BRG")
    assert (brg.basis, brg.sector, brg.label_join) == ("sic_derived", "Financials", "cik")
    prf = _row(f, "PRF")                      # leaver in ticker_sectors AND profiles, no CIK
    assert prf.basis == "unlabeled" and pd.isna(prf.label_join)
    assert _row(f, "CURR").label_join == "ticker" and _row(f, "CURR").basis == "sic_current"
    cprf = _row(f, "CPRF")                    # current member keeps the profiles channel
    assert (cprf.label_join, cprf.sector) == ("ticker", "Financials")
    assert pd.isna(_row(f, "NONE").label_join) and _row(f, "NONE").basis == "unlabeled"
    assert set(f["label_join"].dropna()) <= set(mod.LABEL_JOINS)
    assert set(f.loc[f["is_leaver"], "label_join"].dropna()) <= {"cik"}
    # receipt invariant: no leaver is ever labeled by ticker string
    assert rc["leavers_labeled_by_ticker_string"] == 0
    assert rc["leavers_labeled_by_cik"] == 2
    assert rc["labeled_by_ticker_string_all"] == 2 and rc["labeled_by_cik_all"] == 2
    assert (rc["leavers_labeled_by_cik"] + rc["unlabeled_leavers"] == rc["denominator_leavers"])
    assert "CIK" in rc["note"] and "ticker reuse" in rc["note"]
    on_disk = pd.read_parquet(tmp_path / "breadth" / "sp1500_pit_sectors.parquet")
    assert list(on_disk.columns) == mod.COLUMNS


# 11
def test_vocabulary_guard_raises_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_sic_range_to_sector", lambda sic: "Tech")
    _write(tmp_path, membership=[["FFF", "2001-01-01", "2005-01-01", "x"]],
           dead={"FFF": {"cik": 4, "method": "seed"}},
           # desc absent from the text map -> falls through to the (patched) range mapper
           cik_sic={"0000000004": {"sic": "3674", "sic_desc": "Not A Real SIC Description"}})
    with pytest.raises(ValueError):
        _run(tmp_path)
    assert not (tmp_path / "breadth" / "sp1500_pit_sectors.parquet").exists()
    assert not (tmp_path / "breadth" / "_sp1500_pit_sectors_coverage.json").exists()


# 12
def test_notice_line_is_bare_annotation(tmp_path, capsys):
    _write(tmp_path, membership=[["HHH", "2001-01-01", "2005-01-01", "x"]])
    _run(tmp_path)
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert len(lines) == 1
    assert lines[0].startswith("::notice title=sp1500-pit-sectors::")
    assert lines[0].endswith("era_correct=0")


# 13
def test_atomic_no_tmp_sibling(tmp_path):
    _write(tmp_path, membership=[["III", "2001-01-01", "2005-01-01", "x"]])
    _run(tmp_path)
    assert not list(tmp_path.rglob("*.tmp"))


# 14
def test_missing_optional_inputs(tmp_path):
    _write(tmp_path, membership=[["JJJ", "2001-01-01", "2005-01-01", "x"],
                                 ["KKK", "2001-01-01", None, "x"]])
    f, rc = _run(tmp_path)
    assert (f["basis"] == "unlabeled").all() and f["sector"].isna().all()
    assert rc["unlabeled_leavers"] == 1 and rc["denominator_all"] == 2


def test_missing_membership_raises_and_cli_is_clean(tmp_path, capsys):
    with pytest.raises(FileNotFoundError):
        mod.build(tmp_path, network=False)
    assert mod.main(["--no-network", "--data-dir", str(tmp_path)]) == 2
    assert "sp1500_pit_membership.parquet" in capsys.readouterr().err


# R3
def test_empty_membership_raises_before_any_write(tmp_path):
    _write(tmp_path, membership=[])
    with pytest.raises(mod.MissingInputError):
        _run(tmp_path)
    assert not (tmp_path / "breadth" / "sp1500_pit_sectors.parquet").exists()
    assert not (tmp_path / "breadth" / "_sp1500_pit_sectors_coverage.json").exists()


# R3 (second half): rows that exist but carry no ticker must never produce a 0-row write
def test_all_null_ticker_membership_raises_before_any_write(tmp_path):
    _write(tmp_path, membership=[[None, "2001-01-01", None, "x"]])
    with pytest.raises(mod.MissingInputError):
        _run(tmp_path)
    assert not (tmp_path / "breadth" / "sp1500_pit_sectors.parquet").exists()
    assert not (tmp_path / "breadth" / "_sp1500_pit_sectors_coverage.json").exists()
    assert not (tmp_path / "breadth" / "_sp1500_pit_sic_cache.json").exists()


def test_null_ticker_rows_are_dropped_and_counted(tmp_path):
    _write(tmp_path, membership=[["KEEP", "2001-01-01", "2005-01-01", "x"],
                                 [None, "2001-01-01", None, "x"]])
    frame, receipt = _run(tmp_path)
    assert list(frame["ticker"]) == ["KEEP"]
    assert receipt["denominator_all"] == 1
    assert receipt["membership_rows_null_ticker_dropped"] == 1


# R5(a)
def test_cik_sic_json_wins_over_own_cache(tmp_path, monkeypatch):
    _no_network(monkeypatch)
    _write(tmp_path, membership=[["WIN", "2001-01-01", "2005-01-01", "x"]],
           dead={"WIN": {"cik": 6, "method": "seed"}},
           cik_sic={"0000000006": {"sic": "1311", "sic_desc": "Crude Petroleum & Natural Gas"}},
           cache={"0000000006": {"sic": "6022", "sic_desc": "State Commercial Banks",
                                 "name": "W", "fetched_at": "2026-01-01"}})
    f, _ = _run(tmp_path, network=True)
    r = _row(f, "WIN")
    assert (r.sector, int(r.sic)) == ("Energy", 1311)     # cik_sic.json, not the cache's Financials


# R5(b)
def test_cik_sic_json_is_never_written(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_get_submissions", lambda c: {
        "sic": "1311", "sicDescription": "Crude Petroleum & Natural Gas", "name": "X"})
    _write(tmp_path, membership=[["RO", "2001-01-01", "2005-01-01", "x"],
                                 ["NET", "2001-01-01", "2005-01-01", "x"]],
           dead={"RO": {"cik": 6, "method": "seed"}, "NET": {"cik": 7, "method": "seed"}},
           cik_sic={"0000000006": {"sic": "6022", "sic_desc": "State Commercial Banks"}})
    path = tmp_path / "edgar" / "cik_sic.json"
    before = path.read_bytes()
    _run(tmp_path, network=True)
    assert path.read_bytes() == before


# R5(c)
def test_clean_sic_accepts_float_strings():
    assert mod._clean_sic("1311.0") == 1311
    assert mod._clean_sic("1311") == 1311
    assert mod._clean_sic(1311.0) == 1311
    assert mod._clean_sic("") is None and mod._clean_sic(None) is None
    assert mod._clean_sic("nan") is None and mod._clean_sic("abc") is None


# R6
def test_known_but_unmappable_sic_is_still_recorded(tmp_path):
    _write(tmp_path, membership=[["UNM", "2001-01-01", "2005-01-01", "x"]],
           dead={"UNM": {"cik": 8, "method": "seed"}},
           cik_sic={"0000000008": {"sic": "9999999", "sic_desc": "Not A Real SIC Description"}})
    f, rc = _run(tmp_path)
    r = _row(f, "UNM")
    assert r.basis == "unlabeled" and pd.isna(r.sector) and pd.isna(r.label_join)
    assert int(r.sic) == 9999999 and r.sic_desc == "Not A Real SIC Description"
    assert r.cik == "0000000008"
    assert rc["unlabeled_leavers"] == 1


# verifier finding 1: current-map CIK methods must never label a leaver
def test_leaver_cik_from_current_map_methods_is_never_bridged(tmp_path, monkeypatch):
    _no_network(monkeypatch)
    _write(tmp_path,
           membership=[["ECHO", "2019-12-17", "2021-11-24", "x"],
                       ["PLY", "2001-01-01", "2005-01-01", "x"],
                       ["GOOD", "2001-01-01", "2005-01-01", "x"],
                       ["CURM", "2001-01-01", None, "x"]],
           dead={"ECHO": {"cik": 2, "method": "company_tickers"},
                 "PLY": {"cik": 3, "method": "polygon"},
                 "GOOD": {"cik": 4, "method": "edgar_fts"},
                 "CURM": {"cik": 5, "method": "company_tickers"}},
           cik_sic={"0000000002": {"sic": "4899", "sic_desc": "Communications Services, NEC"},
                    "0000000003": {"sic": "1311", "sic_desc": "Crude Petroleum & Natural Gas"},
                    "0000000004": {"sic": "6022", "sic_desc": "State Commercial Banks"},
                    "0000000005": {"sic": "6022", "sic_desc": "State Commercial Banks"}})
    f, rc = _run(tmp_path, network=True)
    for t in ("ECHO", "PLY"):
        r = _row(f, t)
        assert r.basis == "unlabeled" and pd.isna(r.sector) and pd.isna(r.label_join)
        assert pd.isna(r.cik_method) and pd.isna(r.sic)
    assert _row(f, "GOOD").label_join == "cik" and _row(f, "GOOD").sector == "Financials"
    # a CURRENT member may still use a current-map CIK
    assert (_row(f, "CURM").label_join, _row(f, "CURM").sector) == ("cik", "Financials")
    assert rc["leavers_labeled_by_cik"] == 1
    assert rc["leavers_labeled_by_ticker_string"] == 0
    assert rc["leavers_cik_untrusted_method"] == 2
    assert rc["leavers_sic_on_disk_before_run"] == 1
    assert rc["network_lookups_performed"] == 0
