"""Investigate actual duplicate analyst rows without calling a collector or network."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import io
import json
import logging
import math
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import pandas as pd

PIN="3d90aad6d83152dfeeaf8345bc995826ac9d3139"

def main():
    p=argparse.ArgumentParser();p.add_argument("--repo",required=True);p.add_argument("--out",required=True);p.add_argument("--input",required=True);a=p.parse_args()
    hashes={}
    def raw(path):
        b=subprocess.check_output(["git","-C",a.repo,"show",PIN+":"+path]);hashes[path]={"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)};return b
    b=raw("data/china_analyst/forecast.parquet");df=pd.read_parquet(io.BytesIO(b))
    inp=json.loads(Path(a.input).read_text());q={r["ticker"] for r in inp["qualified_rows"]};featured=set(inp["published_featured"])
    scope={"json":json,"math":math,"log":logging.getLogger("analyst_duplicate_probe"),
           "pd":SimpleNamespace(read_parquet=pd.read_parquet,Timestamp=SimpleNamespace(now=lambda:pd.Timestamp("2026-10-09")))}
    locations={}
    for path,names,constants in [("engine/china_extras.py",{"_num","_read_payload","_rating","analyst_consensus"},{"_RATINGS"}),
                                  ("engine/china_altdata.py",{"_clip","_analyst_score","_rank_pct"},set())]:
        source=raw(path).decode();nodes=[]
        for node in ast.parse(source).body:
            if isinstance(node,ast.FunctionDef) and node.name in names:
                nodes.append(node);locations[node.name]={"path":path,"line":node.lineno}
            elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in node.targets):nodes.append(node)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),path+"@"+PIN,"exec"),scope)
    # Actual source parser and feature functions; only storage root and wall-clock year are injected.
    with tempfile.TemporaryDirectory(prefix="analyst-order-",dir=str(Path(a.out).parent)) as td:
        root=Path(td);variants={}
        for label,data in [("forward",df),("reverse",df.iloc[::-1])]:
            folder=root/label/"china_analyst";folder.mkdir(parents=True)
            if label=="forward":(folder/"forecast.parquet").write_bytes(b)
            else:data.to_parquet(folder/"forecast.parquet",index=False)
            scope["config"]=SimpleNamespace(data_dir=lambda base=root/label:base)
            blocks=scope["analyst_consensus"]()
            scores={t:scope["_analyst_score"](v) for t,v in blocks.items()}
            ranks=scope["_rank_pct"](scores)
            variants[label]={"blocks":blocks,"scores":scores,"ranks":ranks}
    def canonical(x):
        try:return json.dumps(json.loads(x),sort_keys=True,ensure_ascii=False)
        except Exception:return "INVALID:"+str(x)
    duplicates=[]
    for t,g in df.groupby("ticker",sort=True):
        if len(g)<2:continue
        payloads=[json.loads(x) for x in g["payload"]]
        duplicates.append({"ticker":t,"rows":len(g),"distinct_payloads":len({canonical(x) for x in g["payload"]}),
                           "asof":sorted(set(g["asof"].astype(str))),"qualified":t in q,"featured":t in featured,
                           "payloads":payloads})
    first=variants["forward"];second=variants["reverse"]
    changes=[]
    for t in sorted(set(first["blocks"])|set(second["blocks"])):
        fields={k:{"forward":first["blocks"].get(t,{}).get(k),"reverse":second["blocks"].get(t,{}).get(k)}
                for k in set(first["blocks"].get(t,{}))|set(second["blocks"].get(t,{}))
                if first["blocks"].get(t,{}).get(k)!=second["blocks"].get(t,{}).get(k)}
        sr1,sr2=first["scores"].get(t),second["scores"].get(t);r1,r2=first["ranks"].get(t),second["ranks"].get(t)
        if fields or sr1!=sr2 or r1!=r2:changes.append({"ticker":t,"qualified":t in q,"featured":t in featured,"fields":fields,
                                                    "raw_rating_forward":sr1,"raw_rating_reverse":sr2,"rank_forward":r1,"rank_reverse":r2})
    out={"source_sha":PIN,"input_hashes":hashes,"source_locations":locations,"injected_year":2026,
         "source_input_bytes":len(Path(a.input).read_bytes()),"source_input_sha256":hashlib.sha256(Path(a.input).read_bytes()).hexdigest(),
         "rows":len(df),"unique_tickers":int(df.ticker.nunique()),"duplicate_groups":len(duplicates),
         "duplicate_rows":sum(r["rows"] for r in duplicates),"conflicting_payload_groups":sum(r["distinct_payloads"]>1 for r in duplicates),
         "group_sizes":{str(k):int(v) for k,v in df.groupby("ticker").size().value_counts().sort_index().items()},
         "changed_consensus_blocks":sum(bool(r["fields"]) for r in changes),
         "changed_raw_rating_scores":sum(r["raw_rating_forward"]!=r["raw_rating_reverse"] for r in changes),
         "changed_rank_percentiles":sum(r["rank_forward"]!=r["rank_reverse"] for r in changes),
         "qualified_changed_rank_percentiles":sum(r["qualified"] and r["rank_forward"]!=r["rank_reverse"] for r in changes),
         "featured_changed_rank_percentiles":sum(r["featured"] and r["rank_forward"]!=r["rank_reverse"] for r in changes),
         "duplicates":duplicates,"changes":changes,
         "limits":["Physical row reversal only; no source publication chronology is supplied by the same-day asof.",
                   "Rating feature and its own cross-sectional percentiles are compared. No full intelligence recomputation or board/performance effect is claimed.",
                   "No vendor/network call, production mutation, or fact reconciliation by choosing first/last/average."]}
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k not in {"duplicates","changes","input_hashes","source_locations","limits"}},ensure_ascii=False))

if __name__=="__main__":main()
