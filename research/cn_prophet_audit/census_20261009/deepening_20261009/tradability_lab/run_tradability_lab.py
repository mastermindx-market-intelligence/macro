#!/usr/bin/env python3
"""Offline native-caller, metadata-owner and bounded weight challenges.

All writes are inside this research directory. Native functions/statements are
compiled without source rewrites. Only input I/O, the main() build callee and
the pre-gate trace boundary are research adapters. No collector or gate runs.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
import logging
import numbers
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import time
from types import ModuleType, SimpleNamespace
import pandas as pd

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"
INPUT_SHA = "8106d35c0caccfdc000f50652cf5a673605cd2d6e11882ccb28741e85490f7a3"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def compile_native(code, names, scope, filename):
    tree = ast.parse(code)
    nodes = [n for n in tree.body if
             isinstance(n, ast.ImportFrom) and n.module == "__future__" or
             isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names or
             isinstance(n, (ast.Assign, ast.AnnAssign)) and any(
                 isinstance(t, ast.Name) and t.id in names for t in
                 (n.targets if isinstance(n, ast.Assign) else [n.target]))]
    if not any(isinstance(n, ast.ImportFrom) and n.module == "__future__" for n in nodes):
        nodes = ast.parse("from __future__ import annotations").body + nodes
    exec(compile(ast.Module(body=copy.deepcopy(nodes), type_ignores=[]), filename, "exec"), scope)
    return nodes


def block_nodes(rows, original_indent):
    """Restore the original owner indentation before dedenting exact excerpts."""
    out = []
    for item in rows:
        lines = item["code"].splitlines()
        lines[0] = " " * original_indent + lines[0]
        out.extend(ast.parse(textwrap.dedent("\n".join(lines))).body)
    return out


def exec_block(nodes, scope, filename):
    header = ast.parse("from __future__ import annotations").body
    exec(compile(ast.Module(body=header + copy.deepcopy(nodes), type_ignores=[]), filename, "exec"), scope)


def main():
    inp_raw = (HERE / "TRADABILITY_INPUT.json").read_bytes()
    inp = json.loads(inp_raw)
    checks = []
    observations = {}

    def check(name, condition, details=None, kind="native_boundary"):
        checks.append({"name": name, "passed": bool(condition), "kind": kind, "details": details})
        if not condition:
            raise AssertionError(name)

    check("exact_corrected_input", sha(inp_raw) == INPUT_SHA, {"sha256": sha(inp_raw)}, "identity")
    check("source_pin", inp["source_sha"] == PIN, PIN, "identity")
    check("corrected_date_helper_and_stock_set_preflight",
          inp["summary"]["native_last_session_preflight"] == "2026-10-09" and
          inp["summary"]["nightly_pack_stock_set_equal_on_current_input"], kind="identity")
    receipt = json.loads((HERE / "extraction_receipt.json").read_text())
    check("corrected_host_census_exit_zero", receipt["terminal_exit_0"], receipt["terminal_tail"], "identity")
    native = inp["native_source"]
    for name, source in native.items():
        if "code" in source:
            raw = source["code"].encode()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            check("full_source_bytes_" + name,
                  sha(raw) == source["sha256"] and blob == source["git_blob_sha1"], source["sha256"], "identity")

    def code(name):
        row = native[name]
        return row.get("code") or "\n\n".join(x["code"] for x in row["excerpts"])

    log = logging.getLogger("tradability_offline")
    log.addHandler(logging.NullHandler())
    touched_modules = ["lib", "lib.exchange_holidays", "lib.cn_calendar", "lib.hk_calendar", "lib.tsx_calendar",
                       "lib.us_cash_calendar", "lib.market_session", "engine", "engine.tushare_freshness",
                       "scripts", "scripts.build_china_library"]
    previous = {k: sys.modules.get(k) for k in touched_modules}
    io_frames = {}
    reads = []

    class VPath:
        def __init__(self, value): self.value = value
        def __truediv__(self, part): return VPath(self.value + "/" + str(part))
        def exists(self): return self.value in io_frames
        def __str__(self): return self.value

    class PandasIO:
        def read_parquet(self, path, *args, **kwargs):
            key = str(path); reads.append(key)
            value = io_frames[key]
            if isinstance(value, Exception): raise value
            cols = kwargs.get("columns")
            return value[list(cols)].copy() if cols is not None else value.copy()
        def __getattr__(self, name): return getattr(pd, name)

    config = SimpleNamespace(data_dir=lambda: VPath("data"), load=lambda: copy.deepcopy(inp["config_projection"]))
    lib = ModuleType("lib"); lib.__path__ = []; lib.config = config; sys.modules["lib"] = lib
    engine = ModuleType("engine"); engine.__path__ = []; sys.modules["engine"] = engine

    def load_full(path, module_name):
        m = ModuleType(module_name); m.__file__ = path + "@" + PIN
        sys.modules[module_name] = m
        exec(compile(code(path), m.__file__, "exec"), m.__dict__)
        owner, short = module_name.rsplit(".", 1); setattr(sys.modules[owner], short, m)
        return m

    try:
        load_full("lib/exchange_holidays.py", "lib.exchange_holidays")
        calendar = load_full("lib/cn_calendar.py", "lib.cn_calendar")
        for venue in ["hk_calendar", "tsx_calendar", "us_cash_calendar"]:
            m = ModuleType("lib." + venue); sys.modules[m.__name__] = m; setattr(lib, venue, m)
        load_full("lib/market_session.py", "lib.market_session")
        freshness = load_full("engine/tushare_freshness.py", "engine.tushare_freshness")
        rev = {}; compile_native(code("engine/china_reversal.py"), {"_ST_PREFIXES", "is_st"}, rev, "native_reversal")
        base = {"pd": PandasIO(), "numbers": numbers, "config": config, "log": log, "is_st": rev["is_st"]}
        liq = {"__name__": "native_liquidity"}
        exec(compile(code("engine/china_liquidity.py"), "china_liquidity.py@" + PIN, "exec"), liq)
        liq["pd"] = base["pd"]
        base["china_liquidity"] = SimpleNamespace(**liq)
        compile_native(code("scripts/build_china_library.py"),
                       {"MCAP_FLOOR_YI", "STALE_DAYS", "stock_tradability_ok", "_last_session"}, base, "native_library")
        predicate = base["stock_tradability_ok"]
        check("native_last_session_local_dependency_preflight",
              str(base["_last_session"](pd.Series([1.0], index=pd.to_datetime(["2026-10-09"])))) == "2026-10-09")

        current = inp["stock_rows"]
        mismatches = []
        for row in current:
            found = predicate(row["ticker"], **row["native_predicate_arguments"])
            if found != row["predicate_reason"]: mismatches.append(row["ticker"])
        check("all_1716_native_predicate_argument_replays", len(current) == 1716 and not mismatches,
              {"n": len(current), "mismatches": mismatches, "counts": inp["summary"]["predicate_reason_counts"]}, "actual")
        unknown_cap = [r for r in current if not r["has_real_mktcap"]]
        check("actual_unknown_cap_passes_incumbent_rule", len(unknown_cap) == 1 and unknown_cap[0]["ticker"] == "300773.SZ"
              and unknown_cap[0]["predicate_reason"] is None, [{k:r[k] for k in ("ticker", "native_predicate_arguments")} for r in unknown_cap], "actual")
        age_differences = [{k:r[k] for k in ("ticker", "last_close", "last_deep_close", "pack_session_lag", "native_predicate_arguments")}
                           for r in current if r["last_close"] != r["last_deep_close"]]
        observations["actual_close_vs_adv_source_dates"] = age_differences
        check("actual_older_adv_sources_are_visible", [r["ticker"] for r in age_differences] == ["300773.SZ", "601059.SS", "601198.SS"], age_differences, "actual")
        check("actual_no_price_stale_or_mcap_rejection_witness",
              inp["summary"]["full_native_screen_counters"]["stale"] == 0 and
              inp["summary"]["full_native_screen_counters"]["mcap"] == 0 and inp["summary"]["pack_native_stale_n"] == 0,
              "Synthetic boundaries below are not current suspension/cap failures.", "actual")

        good = {"st_flag": False, "name_zh": "普通公司", "mktcap": 60.0, "adv_yi": 1.0}
        predicate_cases = [
            ("known_st_flag", {"st_flag": True}, "st"), ("st_name_fallback", {"name_zh": "ST公司"}, "st"),
            ("star_st_name", {"name_zh": "*ST公司"}, "st"), ("retired_name", {"name_zh": "公司退"}, "st"),
            ("cap_below_30_yi", {"mktcap": 29.999}, "mcap"), ("cap_placeholder_30_passes", {"mktcap": 30.0}, None),
            ("unknown_cap_passes", {"mktcap": None}, None), ("adv_below_half_yi", {"adv_yi": 0.4999}, "adv"),
            ("adv_at_half_yi_passes", {"adv_yi": 0.5}, None), ("unknown_adv_passes", {"adv_yi": None}, None),
            ("all_unknown_metadata_passes", {"st_flag": False, "name_zh": None, "mktcap": None, "adv_yi": None}, None),
            ("reason_precedence_st_before_cap_adv", {"st_flag": True, "mktcap": 10, "adv_yi": 0.1}, "st")]
        for label, changes, expected in predicate_cases:
            args = {**good, **changes}; got = predicate("600000.SS", **args)
            check("predicate_" + label, got == expected, {"synthetic": True, "arguments": args, "reason": got})

        ap = {"pd": pd, "log": log}
        compile_native(code("engine/prophet_live/armed_pack.py"),
                       {"_DEFAULTS", "pack_cfg", "clean_closes", "as_of_date", "session_lag"}, ap, "native_armed_pack")
        cp = {"AP": SimpleNamespace(**ap)}
        compile_native(code("engine/prophet_live/cn_pack.py"),
                       {"_ETF_OR_INDEX", "pack_cfg", "is_cn_stock", "filter_universe"}, cp, "native_cn_pack")
        forbidden_calls = []
        def forbidden_gate():
            forbidden_calls.append("gate")
            raise AssertionError("Native gate must not be reached by this frontier study")
        cp["make_cn_gate"] = forbidden_gate
        caller = {"argparse": argparse, "json": json, "logging": logging, "sys": sys, "time": time,
                  "datetime": datetime, "timezone": timezone, "Path": Path, "_CODE_ROOT": str(HERE),
                  "CP": SimpleNamespace(**cp), "AP": SimpleNamespace(**ap), "log": log}
        caller_code = code("scripts/build_cn_live_pack.py")
        compile_native(caller_code, {"_now", "build", "main"}, caller, "build_cn_live_pack.py@" + PIN)
        native_build = caller["build"]
        calls = []
        def capture_build(**kwargs):
            calls.append(kwargs); return {"research": "argument capture only"}
        caller["build"] = capture_build
        exit_code = caller["main"](["--now", "2026-10-09T16:20:00Z", "--limit", "6", "--root", str(HERE)])
        check("actual_native_main_omits_tradable_argument", exit_code == 0 and len(calls) == 1 and "tradable" not in calls[0],
              {"captured_keyword_names": sorted(calls[0]), "series_argument_supplied": "series" in calls[0],
               "publish": False, "out": None}, "actual")
        caller["build"] = native_build
        originals = {}
        tuples = []
        for row in inp["small_real_fixture"]:
            s = pd.Series([v for _,v in row["close_tail"]], index=pd.to_datetime([d for d,_ in row["close_tail"]]))
            originals[row["ticker"]] = s
            tuples.append((row["ticker"], s, None, row["name"], row["sector"]))
        scripts = ModuleType("scripts"); scripts.__path__ = []; sys.modules["scripts"] = scripts
        library_mod = ModuleType("scripts.build_china_library"); library_mod.universe = lambda: list(tuples)
        sys.modules[library_mod.__name__] = library_mod; scripts.build_china_library = library_mod
        build_node = next(n for n in ast.parse(caller_code).body if isinstance(n, ast.FunctionDef) and n.name == "build")
        stop_line = next(n.lineno for n in build_node.body if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id == "g" for t in n.targets))
        class FrontierReached(BaseException): pass
        def frontier(**kwargs):
            captured = {}
            def trace(frame, event, arg):
                if event == "line" and frame.f_code is native_build.__code__ and frame.f_lineno == stop_line:
                    captured.update({"tickers": list(frame.f_locals["series"]), "tip": frame.f_locals["tip"],
                                     "skipped": dict(frame.f_locals["skipped"]), "line": frame.f_lineno})
                    raise FrontierReached()
                return trace
            prior_trace = sys.gettrace()
            try:
                sys.settrace(trace)
                native_build(root=HERE, cfg=inp["config_projection"], **kwargs)
            except FrontierReached: pass
            finally: sys.settrace(prior_trace)
            if not captured: raise AssertionError("Did not reach exact native frontier")
            return captured
        by_t = {r["ticker"]: r for r in current}
        complete_map = {t: predicate(t, **by_t[t]["native_predicate_arguments"]) is None for t in originals}
        raw_reason_map = {t: predicate(t, **by_t[t]["native_predicate_arguments"]) for t in originals}
        f_none = frontier(); f_bool = frontier(tradable=complete_map); f_raw = frontier(tradable=raw_reason_map)
        f_empty = frontier(tradable={}); f_partial = frontier(tradable={"600079.SS": False})
        check("actual_six_name_frontier_unfiltered", len(f_none["tickers"]) == 6 and {"600079.SS", "000028.SZ"} <= set(f_none["tickers"]), f_none, "actual")
        expected = [t for t in originals if t not in {"600079.SS", "000028.SZ"}]
        check("complete_boolean_map_reuses_native_screen", f_bool["tickers"] == expected, f_bool, "proposed_caller_argument")
        check("raw_reason_map_inverts_filter", set(f_raw["tickers"]) == {"600079.SS", "000028.SZ"}, f_raw)
        check("empty_map_is_unfiltered", f_empty["tickers"] == f_none["tickers"], f_empty)
        check("partial_map_missing_keys_pass", len(f_partial["tickers"]) == 5 and "000028.SZ" in f_partial["tickers"], f_partial)
        check("series_injection_bypasses_tradable", frontier(series=originals, tradable=complete_map)["tickers"] == list(originals),
              "The explicit test-universe branch bypasses the map; production main supplies no series.")
        context = [
            ("000300.SS", originals["300750.SZ"], None, "index fixture", "Index"),
            ("510300.SS", originals["300750.SZ"], None, "ETF fixture", "Sector ETF"),
            ("430001.BJ", originals["300750.SZ"], None, "BJ fixture", "Other")]
        check("native_stock_filter_context_boundaries", cp["filter_universe"](tuples + context) == tuples,
              {"synthetic_context_tickers": [r[0] for r in context], "stock_fixture_n": len(tuples)})
        check("series_injection_bypasses_universe_filter", "000300.SS" in frontier(series={**originals, "000300.SS": originals["300750.SZ"]})["tickers"])
        saved_tuples = list(tuples)
        tuples.extend([("600998.SS", pd.Series([float("nan"), float("nan")]), None, "no price", "Other"),
                       ("600999.SS", pd.Series([1.0], index=pd.to_datetime(["2026-10-09"])), None, "one price", "Other")])
        f_bad_close = frontier()
        check("native_price_cleaning_excludes_unusable_series", f_bad_close["tickers"] == f_none["tickers"] and f_bad_close["skipped"] == {"no_series": 2}, f_bad_close)
        tuples[:] = saved_tuples
        check("no_gate_latch_or_probe_called", forbidden_calls == [], {"gate_calls": 0, "frontier_line": stop_line}, "safety")
        observations["native_frontiers"] = {"no_map": f_none, "complete_boolean_map": f_bool, "raw_reason_map": f_raw, "partial_map": f_partial}

        owner_blocks = native["scripts/build_china_library.py"]["owner_blocks"]
        metadata_nodes = block_nodes(owner_blocks["metadata"], 4)
        st_nodes = block_nodes(owner_blocks["st_metadata"], 4)
        wrapper_nodes = block_nodes(owner_blocks["tradability_wrapper"], 4)
        screen_nodes = block_nodes(owner_blocks["nightly_screen"], 8)
        def owner_metadata(frames, st_only=False):
            io_frames.clear(); io_frames.update(frames)
            scope = dict(base)
            exec_block(st_nodes if st_only else metadata_nodes, scope, "exact_native_metadata_owner")
            return scope
        money_path = "data/tushare/moneyflow.parquet"
        def mf(rows): return pd.DataFrame(rows, columns=["ticker", "name", "trade_date"])
        stale_scope = owner_metadata({money_path: mf([("600000.SS", "ST测试", "20250102")])}, True)
        check("st_loader_accepts_old_name_row_without_age_guard", stale_scope["st_flag_by"] == {"600000.SS": True},
              {"synthetic": True, "source_date": "2025-01-02", "observed_map": stale_scope["st_flag_by"]})
        future_scope = owner_metadata({money_path: mf([("600000.SS", "ST测试", "20261009"), ("600000.SS", "普通测试", "20261012")])}, True)
        check("st_loader_future_row_can_replace_current_flag", future_scope["st_flag_by"] == {"600000.SS": False},
              {"synthetic": True, "reference_for_test": "2026-10-09", "native_api_cutoff": None, "observed_map": future_scope["st_flag_by"]})
        missing_scope = owner_metadata({}, True)
        check("missing_st_source_is_empty_map", missing_scope["st_flag_by"] == {})
        corrupt_scope = owner_metadata({money_path: ValueError("labeled synthetic unreadable table")}, True)
        check("unreadable_st_source_is_empty_map", corrupt_scope["st_flag_by"] == {})
        check("missing_st_source_keeps_name_fallback", predicate("600000.SS", st_flag=False, name_zh="ST测试", mktcap=60, adv_yi=1) == "st")
        names = pd.DataFrame({"ticker": ["600000.SS", "600001.SS"], "mktcap_yi": [30.0, 60.0],
                              "name_zh": ["普通零", "普通一"], "name_en": ["Zero", "One"]}).set_index("ticker")
        valuation = pd.DataFrame({"ticker": ["600000.SS", "600001.SS"], "total_mv_yi": [47.0, 80.0], "trade_date": ["20261009", "20261009"]})
        free = pd.DataFrame({"median_pe_ttm": [10.0]}, index=pd.to_datetime(["2026-10-09"]))
        frames = {"data/china_search/members.parquet": names, "data/tushare/valuation.parquet": valuation, "data/china_a_val/pe.parquet": free}
        cap_scope = owner_metadata(frames)
        check("owner_cap_overlay_fills_placeholder_and_preserves_real_member", cap_scope["mktcap_by"] == {"600000.SS": 47.0, "600001.SS": 60.0}, cap_scope["mktcap_by"])
        cap_no_overlay = owner_metadata({"data/china_search/members.parquet": names})
        check("owner_placeholder_drops_to_unknown_without_overlay", cap_no_overlay["mktcap_by"] == {"600001.SS": 60.0}, cap_no_overlay["mktcap_by"])

        def tframe(date): return pd.DataFrame({"trade_date": [date], "total_mv_yi": [60.0]})
        preference_cases = [
            ("one_session_lag", tframe("20261008"), free, "tushare"),
            ("two_session_holiday_lag", tframe("20260930"), free, "free"),
            ("ancient_source_without_free", tframe("20250102"), None, "tushare"),
            ("undatable_source_without_free", pd.DataFrame({"value": [1]}), None, "tushare"),
            ("undatable_source_with_free", pd.DataFrame({"value": [1]}), free, "free"),
            ("future_source_with_free", tframe("20261012"), free, "tushare"),
            ("missing_source_with_free", None, free, "free")]
        preferences = []
        for label, ts, f, wanted in preference_cases:
            _, got = freshness.prefer_tushare(ts, f)
            check("relative_freshness_" + label, got == wanted, {"synthetic": True, "chosen": got})
            preferences.append({"case": label, "chosen": got})
        observations["relative_freshness"] = preferences

        io_frames.clear()
        for row in inp["small_real_fixture"]:
            rows = row["deep_liquidity_tail"]
            io_frames["data/china_stocks/" + row["ticker"] + ".parquet"] = pd.DataFrame(
                {"close": [r[1] for r in rows], "volume": [r[2] for r in rows]}, index=pd.to_datetime([r[0] for r in rows]))
            profile = liq["profile"](row["ticker"])
            expected_profile = {"adv_yi": row["census"]["native_predicate_arguments"]["adv_yi"], "turn_ratio": row["census"]["turn_ratio"]}
            check("actual_native_liquidity_tail_" + row["ticker"], profile == expected_profile,
                  {"profile": profile, "tail_rows": len(rows), "source_through": row["census"]["last_deep_close"]}, "actual")
        old_frame = pd.DataFrame({"close": [10.0] * 70, "volume": [10_000_000] * 70}, index=pd.date_range("2024-01-01", periods=70))
        io_frames["data/china_stocks/600000.SS.parquet"] = old_frame
        check("native_adv_accepts_old_source_without_absolute_age_check", liq["profile"]("600000.SS") == {"adv_yi": 1.0, "turn_ratio": 1.0},
              {"synthetic": True, "source_last": str(old_frame.index[-1].date()), "decision_cutoff_argument": None})
        io_frames["data/china_stocks/600000.SS.parquet"] = old_frame.tail(1)
        check("native_adv_uses_available_nonempty_tail_without_min_20", liq["profile"]("600000.SS") == {"adv_yi": 1.0, "turn_ratio": None})
        io_frames.pop("data/china_stocks/600000.SS.parquet")
        check("missing_liquidity_omits_map_key", liq["profile"]("600000.SS") is None and liq["liquidity_map"](["600000.SS"]) == {})
        io_frames["data/china_stocks/600000.SS.parquet"] = pd.DataFrame({"close": [10.0]}, index=pd.to_datetime(["2026-10-09"]))
        check("missing_volume_omits_liquidity", liq["profile"]("600000.SS") is None)

        resolved = cp["pack_cfg"](inp["config_projection"])
        check("native_pack_resolves_three_session_guard", int(resolved["max_lag_sessions"]) == 3, resolved["max_lag_sessions"])
        temporal = []
        for last, wanted_reason, wanted_lag in [("2026-09-23", "stale", 6), ("2026-09-24", None, 5),
                                                ("2026-09-30", None, 2), ("2026-10-08", None, 1), ("2026-10-09", None, 0)]:
            scope = {**base, "st_flag_by": {}, "name_zh_by": {"600000.SS": "普通公司"}, "mktcap_by": {"600000.SS": 60.0}, "liq_by": {"600000.SS": {"adv_yi": 1.0}}}
            exec_block(wrapper_nodes, scope, "native_nightly_tradability_wrapper")
            scope.update(_panel_asof=pd.Timestamp("2026-10-09"), _last=pd.Timestamp(last), ticker="600000.SS",
                         _stock_universe_tickers={"600000.SS"}, prophet_cand=[], cand=[], sc=None, _prophet_row={"ticker": "600000.SS"}, copy=copy)
            exec_block(screen_nodes, scope, "native_nightly_price_stale_screen")
            reason = next((k for k,v in scope["screen_drop"].items() if v), None)
            lag = ap["session_lag"](last, "2026-10-09", calendar=calendar)
            result = {"last": last, "panel": "2026-10-09", "calendar_days": (pd.Timestamp("2026-10-09")-pd.Timestamp(last)).days,
                      "nightly_reason": reason, "pack_session_lag": lag, "pack_stale": lag > resolved["max_lag_sessions"], "synthetic": True}
            temporal.append(result)
            check("separate_native_stale_rules_" + last, reason == wanted_reason and lag == wanted_lag, result)
        observations["nightly_calendar_days_vs_pack_sessions"] = temporal
        observations["current_metadata_summary"] = inp["summary"]
        observations["breadth_limit"] = inp["breadth_assessment"]
        observations["actual_st_source_dates"] = dict(Counter(r["st_source_date"] for r in current))
        check("current_breadth_absent_pin_and_host", not inp["breadth_assessment"]["host_unversioned_cache_exists"] and
              "data/china_breadth/_closes_cache.parquet" in inp["missing_versioned_inputs"], inp["breadth_assessment"], "actual")
    finally:
        for key, value in previous.items():
            if value is None: sys.modules.pop(key, None)
            else: sys.modules[key] = value

    # Reproduce the producer's exact weight script in an owned directory. Source
    # and reviewed results stay immutable; __file__ hash remains the exact script.
    freeze = HERE / "weight_reviewed_source"
    replay = HERE / "weight_replay"; replay.mkdir(exist_ok=True)
    for name in ["weight_contract_audit.py", "weight_input.json"]: shutil.copyfile(freeze/name, replay/name)
    weight_run = subprocess.run([sys.executable, "-B", str(replay/"weight_contract_audit.py")], capture_output=True, text=True)
    check("weight_original_terminal_exit_zero", weight_run.returncode == 0,
          {"exit_code": weight_run.returncode, "stdout": weight_run.stdout.strip(), "stderr": weight_run.stderr.strip()}, "weight")
    wr_raw = (replay/"weight_results.json").read_bytes()
    check("weight_original_receipt_byte_identical", wr_raw == (freeze/"weight_results.json").read_bytes(), {"sha256": sha(wr_raw)}, "weight")
    wi = json.loads((freeze/"weight_input.json").read_bytes()); wr = json.loads(wr_raw)
    ns = {}
    compile_native(wi["signal_lab_source"], {"_PRIORS", "_VAL_FAMILY", "load_validation", "leg_weights_for"}, ns, "independent_native_weight")
    weight_card = json.loads(wi["scorecard_raw"])
    mapped = ns["_VAL_FAMILY"]
    normalized = {k: round(v/sum(ns["_PRIORS"]["altdata"].values()), 4) for k,v in ns["_PRIORS"]["altdata"].items()}
    check("weight_current_baseline_independently_normalized", wr["scenarios"][0]["weights"] == normalized,
          {"raw_sum": sum(ns["_PRIORS"]["altdata"].values()), "signed_coefficients": normalized}, "weight")
    check("weight_actual_card_all_three_mapped_families_unproven",
          all(weight_card["families"][mapped[k]]["proven"] is False for k in ["value", "margin", "flow"]), kind="weight")
    check("weight_actual_and_synthetic_cases_labeled",
          [s["synthetic"] for s in wr["scenarios"]] == [False, True, True, True, True, True, True], kind="weight")
    # A date-only control distinguishes accepting future evidence from claiming
    # that a future timestamp itself causes the numeric weight change.
    module_keys = ["engine", "engine.china_validation"]
    previous_weight = {k: sys.modules.get(k) for k in module_keys}
    val = ModuleType("engine.china_validation")
    line = next(l for l in wi["validation_source_excerpt"].splitlines() if l.startswith("_MIN_PROVEN_N_TS ="))
    exec(line, val.__dict__)
    en = ModuleType("engine"); en.china_validation = val
    sys.modules["engine"] = en; sys.modules["engine.china_validation"] = val
    try:
        qualified = copy.deepcopy(weight_card)
        qualified["families"]["valuation"].update(proven=True, sign_ok=True, mean_ic=0.1, t_hac=3.0, n_obs=400, n_weeks=80, n_indep=20)
        qualified["generated_utc"] = "2026-10-08T08:00:00Z"
        val.load_scorecard = lambda: qualified
        before = ns["leg_weights_for"]("altdata")
        qualified["generated_utc"] = "2026-10-20T08:00:00Z"
        after = ns["leg_weights_for"]("altdata")
        check("weight_date_only_change_is_ignored", before == after and after["value"] > normalized["value"],
              {"synthetic": True, "before": before, "after": after,
               "meaning": "The native reader accepts both dates. This does not show that the timestamp causes the weight change."}, "weight")
    finally:
        for key, value in previous_weight.items():
            if value is None: sys.modules.pop(key, None)
            else: sys.modules[key] = value
    alt_tree = ast.parse(wi["altdata_source"])
    margin_fn = next(n for n in alt_tree.body if isinstance(n, ast.FunctionDef) and n.name == "_margin_score")
    margin_code = ast.get_source_segment(wi["altdata_source"], margin_fn)
    check("weight_margin_consumer_uses_per_issuer_chg_pct", 'block.get("chg_pct")' in margin_code and mapped["margin"] == "margin",
          {"consumer_function": margin_code, "qualification": "The 20.0 denominator is scaling, not proof of a 20-session measurement window."}, "weight")
    observations["weight_assessment"] = {
        "producer_check_count": wr["check_count"], "producer_scenarios": len(wr["scenarios"]),
        "reviewed_result_sha256": sha(wr_raw), "actual_generated_utc": weight_card["generated_utc"],
        "actual_current_weight_action": "none: normalized signed priors retained", "current_coefficients": normalized,
        "synthetic_only": [s["label"] for s in wr["scenarios"] if s["synthetic"]],
        "acceptance": "Accept the bounded reader witnesses and unchanged-current-prior conclusion. No actual board or return effect is demonstrated.",
        "feature_target_limit": "A whole-market margin/CSI300 timer verdict is not empirical qualification of the per-issuer chg_pct consumer. Feature horizon authenticity must come from its existing source owner, not division by 20.0."}

    result = {
        "schema": "cn_tradability_native_seam_lab_v1", "source_sha": PIN, "input_sha256": sha(inp_raw),
        "script_sha256": sha(Path(__file__).read_bytes()), "check_count": len(checks),
        "all_passed": all(c["passed"] for c in checks), "checks": checks, "observations": observations,
        "interpretation": "Successful checks reproduce current behavior, including gaps; they do not certify the unmodified caller as repaired.",
        "minimum_compatible_change": [
            "Expose/reuse a read-only metadata loader at the existing nightly owner; preserve its source precedence, fields, units and unknown-value behavior.",
            "For the complete native stock universe, derive strict Boolean values using stock_tradability_ok(ticker, st_flag=..., name_zh=..., mktcap=..., adv_yi=...) is None.",
            "Pass that complete map at the existing CN pack caller; validate exact key coverage before invoking the native build. Do not use only published-board membership.",
            "Preserve the pack's native three-session stale guard and the nightly owner's separate 15-calendar-day screen. These are not official suspension status.",
            "Track source receipts/dates and resolve cutoff/absolute freshness with the existing source/vintage owner; do not invent expiry or a new screen in this caller fix."],
        "limits": [
            "Current census uses frozen versioned data. The breadth cache is absent in both the Git pin and observed host, so seven additional configured constituents have no cache-backed rows in this replay.",
            "No current official suspension source/status, historical first-seen availability or natural full-universe gate/probe/publication is established.",
            "Synthetic old/future/missing metadata tests describe native acceptance behavior, not detected current board corruption.",
            "The actual six-name frontier is stopped before gate construction. No latch, signal gate or probe executes.",
            "Local boundary replay uses pandas " + pd.__version__ + "; the full native metadata census used pandas " + inp["runtime"]["pandas"] + ".",
            "The weight scenarios do not measure actual rank, board, return or execution effects."],
        "runtime": {"python": sys.version, "pandas": pd.__version__},
        "safety": {"production_edits": 0, "collector_calls": 0, "vendor_calls": 0, "cache_writes": 0, "latch_calls": 0, "gate_calls": 0, "publication_calls": 0}}
    (HERE/"results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"checks": len(checks), "all_passed": result["all_passed"], "current_stocks": 1716,
                      "native_predicate_pass": 1638, "current_exclusions": {"st": 1, "adv": 77},
                      "weight_original_checks": wr["check_count"], "weight_receipt_identical": True}))


if __name__ == "__main__":
    main()
