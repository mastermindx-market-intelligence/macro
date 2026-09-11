#!/usr/bin/env python3
"""Replay existing canonical vintages into one create-only research report.

No data collection, canonical data/site write, scheduler, model fitting, or trade
permission. A missing repository-approved Parquet dependency is a typed failure,
not permission to select another data source or silently use a laboratory parser.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from engine.macro_turnaround import TurnaroundConfig
from engine.macro_turnaround_replay import SeriesBinding, load_panel, replay
from scripts.build_macro_turnaround_research import _unique_object, _reject_constant, _publish_immutable


def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        output=args.output.resolve();root=args.root.resolve()
        if output==args.input.resolve():raise ValueError('input and output paths must be distinct')
        if any(output.is_relative_to(root/p) for p in ('data','site')):
            raise ValueError('research replay cannot write source data or generated product paths')
        request=json.loads(args.input.read_text(encoding='utf-8'),object_pairs_hook=_unique_object,parse_constant=_reject_constant)
        fields={'schema','manifest_sha256','bindings','cutoffs','domain','config'}
        if not isinstance(request,dict) or set(request)!=fields or request['schema']!='macro.turnaround_replay_request.v1':
            raise ValueError('request must have the exact macro.turnaround_replay_request.v1 fields')
        if not isinstance(request['bindings'],list) or not all(isinstance(x,dict) for x in request['bindings']):
            raise ValueError('bindings must be an array of objects')
        if not isinstance(request['cutoffs'],list):raise ValueError('cutoffs must be an array')
        bindings=[SeriesBinding(**x) for x in request['bindings']]
        config=TurnaroundConfig.from_dict(request['config'])
        panel=load_panel(root,bindings,request['manifest_sha256'])
        report=replay(panel,bindings,request['cutoffs'],domain=request['domain'],config=config)
        content=(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
        _publish_immutable(args.output,content)
    except (OSError,TypeError,ValueError) as exc:
        print(f'replay_macro_turnaround: ERROR — {exc}',file=sys.stderr)
        return 2
    print(f'replay_macro_turnaround: OK — {len(report["rows"])} research cutoffs; no forecast authority')
    return 0

if __name__=='__main__':raise SystemExit(main())
