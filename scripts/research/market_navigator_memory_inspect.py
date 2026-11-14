"""Inspect one existing Market Memory capture through Navigator, without writing.

This operator/research CLI is not a public endpoint. The incumbent reader validates
its store and original capture. Output contains the closed display projection only.
No current-time fallback, nearest query, initialization, source fetch or history copy.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(_ROOT))
from engine.market_navigator import HORIZONS,ContractError
from engine.market_navigator_memory import read_evidence,compare_evidence
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_trusted as trusted


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store-root',required=True,type=Path)
    parser.add_argument('--subject-id',required=True)
    parser.add_argument('--instrument-id',required=True)
    parser.add_argument('--event-time',required=True)
    parser.add_argument('--as-known-at',required=True)
    parser.add_argument('--horizon',choices=sorted(HORIZONS),required=True)
    parser.add_argument('--previous-context-id')
    args=parser.parse_args(argv)
    try:
        reader=trusted.TrustedFileAsKnownAtReader(args.store_root)
        result=read_evidence(reader,subject={'subject_id':args.subject_id,'instrument_id':args.instrument_id},
            event_time=args.event_time,as_known_at=args.as_known_at,horizon=args.horizon)
        output={'schema':'market_navigator.inspection/v1','source_status':result['source_status'],
                'evidence':result['view'],'changes':None}
        if args.previous_context_id and result['source_context'] is not None:
            with pit.bounded_owner_reads(maximum_bytes=8*1024*1024):
                previous=reader.read_stored_context_id(args.previous_context_id)
            output['changes']=compare_evidence(previous.packet,result['source_context'],horizon=args.horizon)
    except pit.MarketMemoryContextNotFound:
        output={'schema':'market_navigator.inspection/v1','source_status':'previous_context_absent'}
    except PermissionError:
        output={'schema':'market_navigator.inspection/v1','source_status':'source_access_denied'}
    except (pit.MarketMemoryPITError,OSError):
        output={'schema':'market_navigator.inspection/v1','source_status':'source_unavailable'}
    except (ContractError,ValueError,TypeError):
        output={'schema':'market_navigator.inspection/v1','source_status':'invalid_request_or_evidence'}
    print(json.dumps(output,sort_keys=True,ensure_ascii=False,allow_nan=False))
    return 0 if output['source_status']=='exact_owner_read' else 2


if __name__=='__main__':
    raise SystemExit(main())
