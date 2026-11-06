#!/usr/bin/env python3
"""Read-only native CN metadata census from immutable Git blobs.

Prints a JSON evidence bundle. No repository checkout, collector, gate, cache,
latch, vendor call or file writer is invoked. I/O adapters read pinned blobs.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from copy import deepcopy
import hashlib
import io
import json
import logging
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

sys.dont_write_bytecode = True
import pandas as pd
import yaml

DEFAULT_SHA = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha1": hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}


class GitRead:
    def __init__(self, repo, sha):
        self.repo, self.sha = repo, sha
        wanted = ["data/china_search", "data/china_breadth", "data/china_stocks", "data/china",
                  "data/tushare/moneyflow.parquet", "data/tushare/valuation.parquet", "data/china_a_val/pe.parquet"]
        raw = self.cmd("ls-tree", "-r", "-l", sha, "--", *wanted)
        self.entries = {}
        for line in raw.decode().splitlines():
            head, path = line.split("\t", 1)
            mode, kind, blob, size = head.split()
            if kind == "blob": self.entries[path] = {"git_blob_sha1": blob, "bytes": int(size)}
        self.batch = subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.read_receipts = {}

    def cmd(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args])

    def source(self, path):
        return self.cmd("show", self.sha + ":" + path)

    def read(self, path):
        if path not in self.entries: raise FileNotFoundError(path)
        self.batch.stdin.write((self.sha + ":" + path + "\n").encode()); self.batch.stdin.flush()
        header = self.batch.stdout.readline().decode().strip().split()
        if len(header) != 3 or header[1] != "blob": raise RuntimeError(header)
        payload = self.batch.stdout.read(int(header[2]))
        if self.batch.stdout.read(1) != b"\n": raise RuntimeError("git batch boundary")
        ident = identity(payload)
        if ident["git_blob_sha1"] != header[0]: raise RuntimeError("git blob identity mismatch")
        self.read_receipts[path] = ident
        return payload

    def close(self):
        self.batch.stdin.close(); self.batch.stdout.close()
        self.batch.wait(timeout=20)


def json_scalar(value):
    if value is None: return None
    if isinstance(value, (pd.Timestamp,)): return value.isoformat()
    if hasattr(value, "item"): value = value.item()
    if isinstance(value, float) and pd.isna(value): return None
    return value


def compile_nodes(nodes, filename, scope):
    exec(compile(ast.Module(body=deepcopy(nodes), type_ignores=[]), filename, "exec"), scope)


def selected_nodes(text, names):
    out = []
    for n in ast.parse(text).body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names: out.append(n)
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            if any(isinstance(t, ast.Name) and t.id in names for t in targets): out.append(n)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="/Users/chriswong/Documents/Cluade/macro-main")
    parser.add_argument("--sha", default=DEFAULT_SHA)
    args = parser.parse_args()
    if args.sha != DEFAULT_SHA: raise ValueError("This research design pins one source/data commit")
    git = GitRead(Path(args.repo), args.sha)
    source_paths = ["scripts/build_china_library.py", "scripts/build_cn_live_pack.py", "engine/prophet_live/cn_pack.py",
                    "engine/prophet_live/armed_pack.py", "engine/china_liquidity.py", "engine/china_reversal.py",
                    "engine/china_board_rank.py", "engine/tushare_freshness.py", "lib/market_session.py",
                    "lib/cn_calendar.py", "lib/exchange_holidays.py"]
    originals = {p: git.source(p) for p in source_paths}
    code = {p: b.decode() for p, b in originals.items()}
    native_bundle = {}
    partial_names = {
        "scripts/build_china_library.py": {"MCAP_FLOOR_YI", "STALE_DAYS", "stock_tradability_ok", "universe", "_add_cache", "_overlay_deep_ohlc", "_last_session"},
        "engine/china_reversal.py": {"is_st", "_ST_PREFIXES"},
        "engine/china_board_rank.py": {"stock_panel_asof"},
        "engine/prophet_live/armed_pack.py": {"_DEFAULTS", "pack_cfg", "clean_closes", "as_of_date", "session_lag"},
    }
    for path, raw in originals.items():
        item = identity(raw)
        if path in partial_names:
            nodes = selected_nodes(code[path], partial_names[path])
            item["excerpts"] = [{"line_start": n.lineno, "line_end": n.end_lineno, "code": ast.get_source_segment(code[path], n)} for n in nodes]
        else: item["code"] = code[path]
        native_bundle[path] = item
    builder_tree = ast.parse(code["scripts/build_china_library.py"])
    owner = min((n for n in ast.walk(builder_tree) if isinstance(n, ast.FunctionDef) and n.lineno <= 2203 and n.end_lineno >= 2694), key=lambda n:n.end_lineno-n.lineno)
    metadata_nodes = [n for n in owner.body if 2203 <= n.lineno <= 2272]
    st_nodes = [n for n in metadata_nodes if n.lineno >= 2253]
    wrapper_nodes = [n for n in owner.body if 2525 <= n.lineno <= 2542]
    screening_node = next(n for n in ast.walk(owner) if isinstance(n, ast.If) and n.lineno == 2685)
    blocks = {}
    for name, nodes in [("metadata", metadata_nodes), ("st_metadata", st_nodes), ("tradability_wrapper", wrapper_nodes), ("nightly_screen", [screening_node])]:
        blocks[name] = [{"line_start": n.lineno, "line_end": n.end_lineno, "code": ast.get_source_segment(code["scripts/build_china_library.py"],n)} for n in nodes]
    native_bundle["scripts/build_china_library.py"]["owner_blocks"] = blocks
    native_bundle["scripts/build_china_library.py"]["owner_function"] = owner.name

    config_bytes = git.source("config.yml")
    config_full = yaml.safe_load(config_bytes)
    projected_config = {"china": {"yahoo": config_full["china"]["yahoo"]}, "prophet_live": config_full.get("prophet_live"), "cn_prophet_live": config_full.get("cn_prophet_live")}
    frames = {}
    class VPath:
        def __init__(self, path): self.path = path
        def __truediv__(self, child): return VPath(self.path + "/" + str(child))
        def exists(self): return self.path in git.entries
        @property
        def name(self): return self.path.rsplit("/",1)[-1]
        def __str__(self): return self.path
    parquet_native = pd.read_parquet
    def parquet(path, *args, **kwargs):
        if not isinstance(path,VPath): return parquet_native(path,*args,**kwargs)
        if path.path not in frames: frames[path.path] = parquet_native(io.BytesIO(git.read(path.path)))
        frame = frames[path.path]
        columns = kwargs.get("columns")
        if columns is not None: return frame[list(columns)].copy()
        return frame.copy()
    class PandasIO:
        read_parquet = staticmethod(parquet)
        def __getattr__(self,name): return getattr(pd,name)
    pd_io = PandasIO()
    config = SimpleNamespace(data_dir=lambda:VPath("data"), load=lambda:projected_config)
    def store_read(group,ticker):
        path = VPath("data") / group / (str(ticker)+".parquet")
        return parquet(path) if path.exists() else None
    store = SimpleNamespace(read=store_read)
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    logger = logging.getLogger("tradability_native");logger.setLevel(logging.INFO);logger.addHandler(handler)
    lib = ModuleType("lib");lib.__path__=[];lib.config=config;lib.store=store;sys.modules["lib"]=lib
    engine = ModuleType("engine");engine.__path__=[];sys.modules["engine"]=engine
    def load_full(path,name,inject=None):
        mod=ModuleType(name);mod.__file__=path+"@"+args.sha;sys.modules[name]=mod
        if inject:mod.__dict__.update(inject)
        exec(compile(code[path],mod.__file__,"exec"),mod.__dict__)
        parent,short=name.rsplit(".",1);setattr(sys.modules[parent],short,mod)
        return mod
    holidays=load_full("lib/exchange_holidays.py","lib.exchange_holidays")
    calendar=load_full("lib/cn_calendar.py","lib.cn_calendar")
    # Only CN calendar paths are evaluated. Other imported venue modules are
    # inert module placeholders, not substitutes for CN calendar arithmetic.
    for venue in ["hk_calendar","tsx_calendar","us_cash_calendar"]:
        mod=ModuleType("lib."+venue);sys.modules[mod.__name__]=mod;setattr(lib,venue,mod)
    market=load_full("lib/market_session.py","lib.market_session")
    freshness=load_full("engine/tushare_freshness.py","engine.tushare_freshness")
    liquidity=load_full("engine/china_liquidity.py","engine.china_liquidity")
    liquidity.pd=pd_io;liquidity.log=logger
    reverse={};compile_nodes(selected_nodes(code["engine/china_reversal.py"],{"_ST_PREFIXES","is_st"}),"china_reversal.py@"+args.sha,reverse)
    ns={"pd":pd_io,"config":config,"store":store,"log":logger,"china_liquidity":liquidity,"is_st":reverse["is_st"]}
    compile_nodes(selected_nodes(code["scripts/build_china_library.py"],partial_names["scripts/build_china_library.py"]),"build_china_library.py@"+args.sha,ns)
    cp={};compile_nodes(selected_nodes(code["engine/prophet_live/cn_pack.py"],{"_ETF_OR_INDEX","is_cn_stock","filter_universe"}),"cn_pack.py@"+args.sha,cp)
    ap={"pd":pd,"log":logger};compile_nodes(selected_nodes(code["engine/prophet_live/armed_pack.py"],partial_names["engine/prophet_live/armed_pack.py"]),"armed_pack.py@"+args.sha,ap)
    cp["AP"]=SimpleNamespace(**ap);compile_nodes(selected_nodes(code["engine/prophet_live/cn_pack.py"],{"pack_cfg"}),"cn_pack.py@"+args.sha,cp)
    board={};compile_nodes(selected_nodes(code["engine/china_board_rank.py"],{"stock_panel_asof"}),"china_board_rank.py@"+args.sha,board)
    uni=ns["universe"]()
    stocks=cp["filter_universe"](uni)
    stock_set={r[0] for r in stocks}
    panel=board["stock_panel_asof"](uni,stock_set)
    compile_nodes(metadata_nodes,"native_nightly_metadata@"+args.sha,ns)
    liq=liquidity.liquidity_map([r[0] for r in uni])
    ns["liq_by"]=liq
    compile_nodes(wrapper_nodes,"native_nightly_wrapper@"+args.sha,ns)
    captured={}
    predicate=ns["stock_tradability_ok"]
    def capture(ticker,**kwargs):
        captured[ticker]={k:json_scalar(v) for k,v in kwargs.items()}
        return predicate(ticker,**kwargs)
    ns["stock_tradability_ok"]=capture
    for ticker,*_ in stocks:ns["_tradability_ok"](ticker)
    ns["screen_drop"]={k:0 for k in ["st","mcap","adv","stale","non_stock"]}
    ns.update(_panel_asof=panel,_stock_universe_tickers=stock_set,prophet_cand=[],cand=[],sc=None)
    screening=compile(ast.Module(body=[deepcopy(screening_node)],type_ignores=[]),"native_nightly_screen@"+args.sha,"exec")
    nightly_reason={}
    for ticker,close,*_ in uni:
        before=dict(ns["screen_drop"]);ns.update(ticker=ticker,close=close,_last=close.last_valid_index(),_prophet_row={"ticker":ticker})
        exec(screening,ns)
        nightly_reason[ticker]=next((k for k in before if ns["screen_drop"][k]!=before[k]),None)
    cfg=cp["pack_cfg"](projected_config)
    rows=[]
    money=frames.get("data/tushare/moneyflow.parquet")
    last_money={}
    if money is not None:
        m=money.sort_values("trade_date").drop_duplicates("ticker",keep="last") if "trade_date" in money else money
        last_money={str(r["ticker"]):r for _,r in m.iterrows()}
    for ticker,close,high,name,sector in stocks:
        attrs=captured[ticker]
        pred=predicate(ticker,**attrs)
        s=ap["clean_closes"](close);last=s.index[-1] if s is not None else None
        path="data/china_stocks/"+ticker+".parquet";deep=frames.get(path)
        source_last=deep["close"].last_valid_index() if deep is not None and "close" in deep else None
        mf=last_money.get(ticker)
        rows.append({"ticker":ticker,"name":name,"sector":sector,"close_n":int(len(s)) if s is not None else 0,
                     "last_close":str(pd.Timestamp(last).date()) if last is not None else None,
                     "last_deep_close":str(pd.Timestamp(source_last).date()) if source_last is not None else None,
                     "native_predicate_arguments":attrs,"predicate_reason":pred,"nightly_quality_reason":nightly_reason[ticker],
                     "pack_session_lag":ap["session_lag"](str(pd.Timestamp(last).date()),str(panel.date()),calendar=calendar) if last is not None else None,
                     "has_st_flag_map_entry":ticker in ns["st_flag_by"],"st_source_name":str(mf.get("name")) if mf is not None else None,
                     "st_source_date":str(mf.get("trade_date")) if mf is not None else None,
                     "has_name_zh":ticker in ns["name_zh_by"],"has_real_mktcap":ticker in ns["mktcap_by"],
                     "has_adv":ticker in liq,"turn_ratio":liq.get(ticker,{}).get("turn_ratio")})
    rows.sort(key=lambda r:r["ticker"])
    chosen={"002460.SZ","603799.SS","300750.SZ"}
    categories={}
    for label,fun in [("st",lambda r:r["predicate_reason"]=="st"),("mcap",lambda r:r["predicate_reason"]=="mcap"),
                      ("adv",lambda r:r["predicate_reason"]=="adv"),("nightly_stale",lambda r:r["nightly_quality_reason"]=="stale"),
                      ("pack_stale",lambda r:r["pack_session_lag"]>int(cfg.get("max_lag_sessions") or 2)),
                      ("missing_st",lambda r:not r["has_st_flag_map_entry"]),("missing_mcap",lambda r:not r["has_real_mktcap"]),
                      ("missing_adv",lambda r:not r["has_adv"])]:
        found=next((r["ticker"] for r in rows if fun(r)),None);categories[label]=found
        if found:chosen.add(found)
    fixture=[]
    by_t={r[0]:r for r in stocks}
    for ticker in sorted(chosen):
        if ticker not in by_t:continue
        _,close,_,name,sector=by_t[ticker]
        tail=close.dropna().tail(70)
        deep=frames.get("data/china_stocks/"+ticker+".parquet")
        fixture.append({"ticker":ticker,"name":name,"sector":sector,"close_tail":[[str(pd.Timestamp(d).date()),float(v)] for d,v in tail.items()],
                        "deep_liquidity_tail":None if deep is None else [[str(pd.Timestamp(d).date()),json_scalar(r.get("close")),json_scalar(r.get("volume"))] for d,r in deep.tail(70).iterrows()],
                        "census":next(r for r in rows if r["ticker"]==ticker)})
    metadata_frames={}
    for path in ["data/china_search/members.parquet","data/tushare/valuation.parquet","data/tushare/moneyflow.parquet","data/china_a_val/pe.parquet"]:
        df=frames.get(path)
        if df is not None:metadata_frames[path]={"rows":len(df),"columns":[str(c) for c in df.columns],"index_name":df.index.name,
                                                "frame_asof":json_scalar(freshness.frame_asof(df)),"nulls":{str(c):int(df[c].isna().sum()) for c in df}}
    summary={"universe_n":len(uni),"stock_n":len(stocks),"nonstock_n":len(uni)-len(stocks),"panel_asof":str(panel.date()),
             "predicate_reason_counts":dict(Counter(r["predicate_reason"] or "pass" for r in rows)),
             "nightly_quality_reason_counts":dict(Counter(r["nightly_quality_reason"] or "pass" for r in rows)),
             "full_native_screen_counters":ns["screen_drop"],
             "st_source_missing_n":sum(not r["has_st_flag_map_entry"] for r in rows),"name_zh_missing_n":sum(not r["has_name_zh"] for r in rows),
             "real_mktcap_missing_n":sum(not r["has_real_mktcap"] for r in rows),"adv_missing_n":sum(not r["has_adv"] for r in rows),
             "pack_max_lag_sessions":int(cfg.get("max_lag_sessions") or 2),
             "pack_native_stale_n":sum(r["pack_session_lag"]>int(cfg.get("max_lag_sessions") or 2) for r in rows),
             "fixture_categories":categories,"fixture_n":len(fixture)}
    result={"schema":"cn_tradability_pinned_input_census_v1","source_sha":args.sha,"native_source":native_bundle,
            "config_identity":identity(config_bytes),"config_projection":projected_config,"summary":summary,"stock_rows":rows,
            "small_real_fixture":fixture,"metadata_frames":metadata_frames,"data_read_receipts":git.read_receipts,
            "missing_versioned_inputs":[p for p in ["data/china_breadth/_closes_cache.parquet"] if p not in git.entries],
            "native_loader_log":log_capture.getvalue(),"runtime":{"python":sys.version,"pandas":pd.__version__},
            "limits":["Quality census is conditional on versioned source/data and precedes signal/gate/analysis; it is not a recount of published board eligibility.",
                      "Metadata inputs have source dates but no fabricated first-seen availability or historical snapshot completeness.",
                      "An unversioned breadth cache cannot be supplied by the immutable Git pin and is explicitly absent from this replay.",
                      "Only CN calendar paths are exercised; other market imports are inert module placeholders.",
                      "No full gate/probe grid, natural pack publication, official suspension feed or execution outcome is established."],
            "safety":{"source_files_modified":0,"data_files_modified":0,"host_files_written":0,"latch_calls":0,"collector_calls":0,"vendor_calls":0}}
    git.close()
    print(json.dumps(result,ensure_ascii=False,separators=(",",":"),allow_nan=False))


if __name__=="__main__":main()
