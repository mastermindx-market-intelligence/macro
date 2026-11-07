"""Synthetic calculation witnesses only. No feed, native producer or publisher.

Run from the Macro root: python -m research.factor_atlas.session3.reproduce_native_scenarios
"""
from datetime import datetime, timedelta, timezone
from dataclasses import replace
import hashlib
import json

import numpy as np
from engine.options_basket_aggregation import Definition, Member, Correlation, aggregate


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()


def main():
    asof=datetime(2026,10,8,22,tzinfo=timezone.utc)
    roots=["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA"]
    ivs=[.30,.25,.55,.35,.29,.36,.68]
    definition=Definition("synthetic:mag7_example","fixture:definition",digest(roots),asof-timedelta(days=1))
    rows=[Member(root=r,weight=1/7,iv=v,observed_at=asof-timedelta(hours=2),
                 known_at=asof-timedelta(hours=1),qualified=True,source_ref=f"fixture:{r}",
                 source_sha256=digest({"root":r,"iv":v}),valid_until=asof+timedelta(hours=2),
                 method="iv30_total_variance_act365f",premium=900 if i==0 else 100/6)
          for i,(r,v) in enumerate(zip(roots,ivs))]
    matrix=.4*np.ones((7,7))+.6*np.eye(7)
    correlation=Correlation(tuple(roots),matrix,"fixture:correlation",digest(matrix.tolist()),
                            asof-timedelta(days=1),asof-timedelta(hours=1),
                            asof+timedelta(hours=2),"scenario_assumption")
    full=aggregate(rows,definition=definition,asof=asof,correlation=correlation)
    sparse={}
    for missing in (3,4,5):
        ten=[replace(rows[i%7],root=f"SYN{i:02}",weight=.1,iv=.2+i*.01 if i<10-missing else None,
                     source_ref=f"fixture:SYN{i:02}",
                     source_sha256=digest({"root":f"SYN{i:02}","iv":.2+i*.01 if i<10-missing else None}),
                     premium=None) for i in range(10)]
        cr=replace(correlation,roots=tuple(r.root for r in ten),values=np.eye(10),
                   source_sha256=digest(np.eye(10).tolist()))
        ten_definition=replace(definition,factor_ref="synthetic:ten_names",
                               source_ref="fixture:ten_name_definition",
                               source_sha256=digest([r.root for r in ten]))
        result=aggregate(ten,definition=ten_definition,asof=asof,correlation=cr)
        sparse[f"missing_{missing*10}_percent"]={
            k:result[k] for k in ("coverage","headline_mean_iv","hybrid_expected_move","reasons")}
    output={"schema":"factor_atlas.s3.synthetic_witness/v1","synthetic":True,
            "actual_market_data":False,"producer_integration":False,
            "full":full,"sparse":sparse,
            "mean_iv_as_move_for_comparison_only":full["covered"]["mean_iv"]*(30/365)**.5}
    print(json.dumps(output,sort_keys=True,indent=2,allow_nan=False))


if __name__=="__main__": main()
