# H1 execution binding R2 — reproducible isolated specimens

Review exhibits only. Not production implementations, H1 smoke, independent review or an experiment. See EXECUTION_BINDING_R2.md for source and claim boundaries. All fixture inputs are fictional; no real data-store or outcome access. The complete executed scripts and their receipts follow.

## reader_visibility_probe.py

SHA256 `9f63921d3576847e1ee52ba53f8dc8ad74b6c1fd7d7930d68bd8756a5edc245f`

```python
"""Outcome-blind isolated reader specimens; NOT native-module or H1 smoke tests.

Source: engine/us_context_vector.py at c72d5d7e5defc9582e032f72fa23a8fc90737aac,
blob 861dad4fdc7108157eda9ca7ecbbd38fc13abb75. Executable body below is copied
from the native GitHub read of load_candidates, with docstring omitted. All I/O
is fictional; no real source store, grade, price, output label, fit or bootstrap.
The complete native module was not downloaded/imported.
"""
from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch
from pathlib import Path
import hashlib
import json
import logging
import sys
import pandas as pd

log = logging.getLogger('isolated_native_candidate_reader')
log.setLevel(logging.WARNING)
log.propagate = False


def _store_dir(root: Any = None):
    raise AssertionError('Real/default data-root access is prohibited in this specimen')


def load_candidates(root: Any = None, *, months: Iterable[str] | None = None,
                    columns: Iterable[str] | None = None):
    store = _store_dir(root)
    if not store.exists():
        return pd.DataFrame()
    wanted = {str(m) for m in months} if months is not None else None
    wanted_cols = [str(c) for c in columns] if columns is not None else None
    frames: list[pd.DataFrame] = []
    for part in sorted(store.glob("*.parquet")):
        if wanted is not None and part.stem not in wanted:
            continue
        try:
            if wanted_cols is None:
                frames.append(pd.read_parquet(part))
            else:
                try:
                    frame = pd.read_parquet(part, columns=wanted_cols)
                except Exception:
                    frame = pd.read_parquet(part)
                frames.append(frame.reindex(columns=wanted_cols))
        except Exception as exc:
            log.warning("us_context_vector: part %s unreadable (%s)", part.name, exc)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


@dataclass(frozen=True, order=True)
class Part:
    stem: str
    @property
    def name(self):
        return self.stem + '.parquet'

@dataclass
class Store:
    present: bool
    parts: tuple[Part, ...]
    def exists(self):
        return self.present
    def glob(self, pattern):
        assert pattern == '*.parquet'
        return iter(self.parts)

class Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.items = []
    def emit(self, record):
        self.items.append(record.getMessage())

A, B = Part('2000-01'), Part('2000-02')
frame_a = pd.DataFrame([{'stamp_date':'2000-01-03','ticker':'FIXTURE_A','board_definition':'fixture_only'}])
frame_b = pd.DataFrame([{'stamp_date':'2000-02-01','ticker':'FIXTURE_B','board_definition':'fixture_only'}])


def invoke(store, values, *, months=None, columns=None):
    reads = []
    def fake_read(part, columns=None):
        reads.append({'part':part.name,'columns':columns})
        if part not in values:
            raise AssertionError('undeclared fictional I/O')
        value = values[part]
        if isinstance(value, Exception):
            raise value
        if columns is not None:
            if any(c not in value.columns for c in columns):
                raise KeyError('fictional old schema has no requested field')
            return value[columns].copy()
        return value.copy()
    capture = Capture()
    log.addHandler(capture)
    try:
        with patch.dict(globals(), {'_store_dir':lambda root=None:store}), patch.object(pd, 'read_parquet', fake_read):
            result = load_candidates(months=months, columns=columns)
    finally:
        log.removeHandler(capture)
    return result, capture.items, reads


def run():
    results = []
    def record(case, **evidence):
        results.append({'case':case,'pass':True,**evidence})

    complete, warnings, reads = invoke(Store(True,(A,B)), {A:frame_a,B:frame_b}, months=['2000-01','2000-02'])
    assert len(complete)==2 and not warnings and len(reads)==2
    record('R01_complete_positive_control',returned_rows=2,warnings=0)

    corrupt, warnings, reads = invoke(Store(True,(A,B)), {A:frame_a,B:OSError('fixture unreadable')}, months=['2000-01','2000-02'])
    assert corrupt.equals(frame_a) and len(warnings)==1 and len(reads)==2
    record('R02_unreadable_requested_part_is_omitted',returned_rows=1,warnings=1,returned_integrity_metadata=False)

    absent, warnings, reads = invoke(Store(True,(A,)), {A:frame_a}, months=['2000-01','2000-02'])
    assert absent.equals(corrupt) and not warnings and len(reads)==1
    record('R03_absent_requested_part_same_frame_no_warning',same_dataframe_as_R02=True,warnings=0)

    narrow, warnings, reads = invoke(Store(True,(A,B)), {A:frame_a,B:frame_b}, months=['2000-01'])
    assert narrow.equals(absent) and not warnings and len(reads)==1
    record('R04_intentional_narrow_request_same_frame',same_dataframe_as_R03=True,request_scope_needed=True)

    missing_store, warnings, reads = invoke(Store(False,()), {})
    assert missing_store.empty and not warnings and not reads
    record('R05_missing_store_empty_untyped_return',warnings=0)
    empty_store, warnings, reads = invoke(Store(True,()), {})
    assert empty_store.equals(missing_store) and not warnings and not reads
    record('R06_existing_empty_store_indistinguishable',same_dataframe_as_R05=True)

    projected, warnings, reads = invoke(Store(True,(A,)), {A:frame_a}, months=['2000-01'], columns=['stamp_date','ticker','canonical_security_id'])
    assert len(projected)==1 and projected['canonical_security_id'].isna().all()
    assert len(reads)==2 and reads[0]['columns'] is not None and reads[1]['columns'] is None and not warnings
    record('R07_projection_fallback_yields_null_new_field',read_calls=2,identity_qualified=False,warnings=0)

    # This is denominator arithmetic on declared fictional rows, never an
    # estimate of real missing row counts. In real missing parts totals can be UNKNOWN.
    numerator = len(corrupt)
    declared_original_rows = len(frame_a)+len(frame_b)
    assert numerator/len(corrupt)==1.0 and numerator/declared_original_rows==0.5
    record('R08_returned_frame_is_not_original_denominator',naive_coverage=1.0,fixture_original_coverage=0.5,real_missing_count_inference=False)
    return results

if __name__ == '__main__':
    cases=run()
    payload={
        'scope':'isolated native function specimen with mocked I/O; not full native module, independent review, H1 smoke or experiment',
        'source':{'repo':'mastermindx-market-intelligence/macro','commit':'c72d5d7e5defc9582e032f72fa23a8fc90737aac','path':'engine/us_context_vector.py','blob':'861dad4fdc7108157eda9ca7ecbbd38fc13abb75','function':'load_candidates','copy':'executable body copied from native GitHub source; docstring omitted; globals/I/O mocked'},
        'environment':{'python':sys.version.split()[0],'pandas':pd.__version__},
        'results':cases,'passed':len(cases),'failed':0,
        'source_module_imported':False,'real_data_or_outcome_read':False,'fit_executed':False,'new_registry_or_evaluator':False,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    }
    path=Path(__file__).parent/'evidence'/'reader_visibility_receipt.json'
    path.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({'passed':len(cases),'failed':0,'receipt_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'script_sha256':payload['script_sha256']},indent=2))
```

## input_binding_counterexamples.py

SHA256 `246a9182746c7e9d9274c9222b557ca1640da532dbab40b0fd30706db10e560d`

```python
"""Four source-binding counterexamples on fictional data, no empirical experiment.

The three native function bodies are copied from engine/us_context_vector.py
(c72d5d7e5defc9582e032f72fa23a8fc90737aac, blob861dad4fdc7108157eda9ca7ecbbd38fc13abb75).
Docstrings/comments are omitted; helpers and data are isolated fixtures.
No native module import, I/O, model fitting, protected labels or H1 smoke.
"""
from __future__ import annotations
from collections.abc import Mapping
from pathlib import Path
from typing import Any
import hashlib, json, math, sys
import pandas as pd

def _mapping(value):
    return value if isinstance(value, Mapping) else {}
def _finite(value):
    try:
        x=float(value)
    except (TypeError,ValueError):
        return None
    return x if math.isfinite(x) else None
def _text(value):
    return None if value is None else (str(value).strip() or None)
def _bool(value):
    return value if isinstance(value,bool) else None
def _date(value):
    text=_text(value)
    return text[:10] if text else None
TURNOVER_WINDOW_20D=20

def turnover_percentiles(volumes: pd.DataFrame | None, asof: str, *, window: int = TURNOVER_WINDOW_20D) -> dict[str,dict[str,Any]]:
    out: dict[str, dict[str, Any]] = {}
    if volumes is None or volumes.empty:
        return out
    try:
        cutoff = pd.Timestamp(_date(asof))
    except Exception:
        return out
    frame = volumes.sort_index()
    for ticker in frame.columns:
        series = frame[ticker].dropna()
        series = series.loc[series.index <= cutoff]
        if len(series) < window + 1:
            continue
        win = series.iloc[-window:]
        out[str(ticker)] = {
            "turnover_pctile_20d": round(float(win.rank(pct=True).iloc[-1]), 4),
            "turnover_window_20d": int(len(win)),
        }
    return out

def theme_pulse_by_ticker(membership: Mapping[str,list[str]], states: Mapping[str,Mapping[str,Any]]) -> dict[str,dict[str,Any]]:
    best: dict[str, dict[str, Any]] = {}
    for basket_id, members in membership.items():
        state = _mapping(states.get(basket_id))
        rank = _finite(state.get("rank"))
        if rank is None:
            continue
        for ticker in members:
            prior = best.get(ticker)
            if prior is None or rank < prior["rank"]:
                best[ticker] = {
                    "rank": rank,
                    "id": basket_id,
                    "name": _text(state.get("name")),
                    "label": _text(state.get("label")),
                    "reco": _text(state.get("reco")),
                    "score": _finite(state.get("score")),
                    "bull_days": _finite(state.get("bull_days")),
                    "clean_entry": _bool(state.get("clean_entry")),
                }
    return best

def relay_features(closes: pd.DataFrame | None, membership: Mapping[str,list[str]], *, high_lookback: int, recent_sessions: int, position_window: int, min_members: int) -> dict[str,dict[str,Any]]:
    out: dict[str, dict[str, Any]] = {}
    if closes is None or closes.empty or not membership:
        return out
    need = high_lookback + position_window + 1
    frame = closes.sort_index()
    tail = frame.iloc[-need:] if len(frame) >= need else frame
    if len(tail) < high_lookback + 2:
        return out
    prior_max = tail.rolling(high_lookback).max().shift(1)
    breakouts = (tail > prior_max) & tail.notna() & prior_max.notna()
    window = breakouts.iloc[-position_window:]
    for basket_id, members in membership.items():
        covered = [t for t in members if t in window.columns]
        covered = [t for t in covered if bool(tail[t].notna().all())]
        if len(covered) < min_members:
            continue
        sub = window[covered]
        recent_any = sub.tail(recent_sessions).any(axis=0)
        earlier_any = sub.iloc[:-1].any(axis=0)
        for ticker in covered:
            others = [t for t in covered if t != ticker]
            count_3d = int(recent_any[others].sum()) if others else 0
            earlier = int(earlier_any[others].sum()) if others else 0
            position = round(earlier / len(covered), 4)
            prior = out.get(ticker)
            if prior is None or count_3d > prior["relay_count_3d"]:
                out[ticker] = {
                    "relay_count_3d": count_3d,
                    "relay_position": position,
                    "relay_members_covered": len(covered),
                    "relay_basket_id": basket_id,
                }
    return out

def run():
    evidence=[]
    # These are FICTIONAL session labels, not a certified exchange calendar.
    dates=pd.date_range('2000-01-03',periods=31,freq='B')
    vol=pd.DataFrame({'FIX_A':range(100,131),'FIX_B':range(100,131)},index=dates)
    native=turnover_percentiles(vol,str(dates[-1].date()))
    liquidity_a=math.log1p(float((vol['FIX_A'].iloc[-20:]*2).median()))
    liquidity_b=math.log1p(float((vol['FIX_B'].iloc[-20:]*200).median()))
    assert native['FIX_A']['turnover_pctile_20d']==native['FIX_B']['turnover_pctile_20d']==1.0
    assert liquidity_a != liquidity_b
    evidence.append({'case':'B01_share_volume_percentile_is_not_dollar_liquidity','pass':True,'same_native_value':1.0,'accepted_feature_fixture_values':[liquidity_a,liquidity_b]})

    gapped=vol[['FIX_A']].astype(float).copy()
    gapped.iloc[[12,17,23],0]=float('nan')
    gapped_native=turnover_percentiles(gapped,str(dates[-1].date()))
    assert 'FIX_A' in gapped_native and not bool(gapped.iloc[-20:,0].notna().all())
    evidence.append({'case':'B02_last_non_null_is_not_contiguous_expected_window','pass':True,'native_window':gapped_native['FIX_A']['turnover_window_20d'],'required_recent_20_non_null':int(gapped.iloc[-20:,0].notna().sum()),'H1_feature_disposition':'INPUT_SUPPORT_UNQUALIFIED'})

    membership={'FIX_GROUP_A':['FIX_A'],'FIX_GROUP_B':['FIX_A']}
    first=theme_pulse_by_ticker(membership,{'FIX_GROUP_A':{'rank':2},'FIX_GROUP_B':{'rank':1}})
    second=theme_pulse_by_ticker(membership,{'FIX_GROUP_A':{'rank':1},'FIX_GROUP_B':{'rank':2}})
    assert first['FIX_A']['id']=='FIX_GROUP_B' and second['FIX_A']['id']=='FIX_GROUP_A'
    evidence.append({'case':'B03_strongest_theme_is_not_eligible_primary_roster','pass':True,'native_groups':[first['FIX_A']['id'],second['FIX_A']['id']],'H1_without_owner_primary':'AMBIGUOUS_OVERLAP_q0'})

    closes=pd.DataFrame({'FIX_A':[10]*6,'FIX_A_ALT':[10,10,10,10,10,12],'FIX_B':[10]*6,'FIX_C':[10]*6},index=dates[:6])
    member={'FIX_GROUP':['FIX_A','FIX_A_ALT','FIX_B','FIX_C']}
    native_relay=relay_features(closes,member,high_lookback=2,recent_sessions=1,position_window=2,min_members=2)
    assert native_relay['FIX_A']['relay_count_3d']==1
    # Owner fixture states A and A_ALT are one issuer. Other issuers B and C
    # are flat against a flat fictional benchmark -> strict outperformance=0.
    issuer_qualified_breadth=0.0
    assert issuer_qualified_breadth != native_relay['FIX_A']['relay_count_3d']
    evidence.append({'case':'B04_ticker_exclusion_is_not_issuer_exclusion','pass':True,'native_relay_count':1,'H1_other_issuer_breadth_fixture':issuer_qualified_breadth,'native_function_is_not_H1_or_a_bug_claim':True})
    return evidence

if __name__=='__main__':
    cases=run()
    payload={'scope':'source-binding non-equivalence witnesses on fictional data, not an H1 experiment or full-native test','source_commit':'c72d5d7e5defc9582e032f72fa23a8fc90737aac','source_blob':'861dad4fdc7108157eda9ca7ecbbd38fc13abb75','functions':['turnover_percentiles','theme_pulse_by_ticker','relay_features'],'function_copy':'executable bodies copied from native GitHub read; docstrings/comments omitted; isolated helpers','environment':{'python':sys.version.split()[0],'pandas':pd.__version__},'passed':len(cases),'failed':0,'results':cases,'real_data_read':False,'fit_executed':False,'native_module_imported':False,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    p=Path(__file__).parent/'evidence'/'input_binding_counterexamples_receipt.json'
    p.write_text(json.dumps(payload,indent=2)+'\n')
    print(json.dumps({'passed':len(cases),'failed':0,'receipt_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'script_sha256':payload['script_sha256']},indent=2))
```

## evidence/reader_visibility_receipt.json

SHA256 `682705f67a555438be328c87f1386b3717cd42035bfb42b5cc37170d793196c8`

```json
{
  "scope": "isolated native function specimen with mocked I/O; not full native module, independent review, H1 smoke or experiment",
  "source": {
    "repo": "mastermindx-market-intelligence/macro",
    "commit": "c72d5d7e5defc9582e032f72fa23a8fc90737aac",
    "path": "engine/us_context_vector.py",
    "blob": "861dad4fdc7108157eda9ca7ecbbd38fc13abb75",
    "function": "load_candidates",
    "copy": "executable body copied from native GitHub source; docstring omitted; globals/I/O mocked"
  },
  "environment": {
    "python": "3.13.5",
    "pandas": "2.2.3"
  },
  "results": [
    {
      "case": "R01_complete_positive_control",
      "pass": true,
      "returned_rows": 2,
      "warnings": 0
    },
    {
      "case": "R02_unreadable_requested_part_is_omitted",
      "pass": true,
      "returned_rows": 1,
      "warnings": 1,
      "returned_integrity_metadata": false
    },
    {
      "case": "R03_absent_requested_part_same_frame_no_warning",
      "pass": true,
      "same_dataframe_as_R02": true,
      "warnings": 0
    },
    {
      "case": "R04_intentional_narrow_request_same_frame",
      "pass": true,
      "same_dataframe_as_R03": true,
      "request_scope_needed": true
    },
    {
      "case": "R05_missing_store_empty_untyped_return",
      "pass": true,
      "warnings": 0
    },
    {
      "case": "R06_existing_empty_store_indistinguishable",
      "pass": true,
      "same_dataframe_as_R05": true
    },
    {
      "case": "R07_projection_fallback_yields_null_new_field",
      "pass": true,
      "read_calls": 2,
      "identity_qualified": false,
      "warnings": 0
    },
    {
      "case": "R08_returned_frame_is_not_original_denominator",
      "pass": true,
      "naive_coverage": 1.0,
      "fixture_original_coverage": 0.5,
      "real_missing_count_inference": false
    }
  ],
  "passed": 8,
  "failed": 0,
  "source_module_imported": false,
  "real_data_or_outcome_read": false,
  "fit_executed": false,
  "new_registry_or_evaluator": false,
  "script_sha256": "9f63921d3576847e1ee52ba53f8dc8ad74b6c1fd7d7930d68bd8756a5edc245f"
}
```

## evidence/input_binding_counterexamples_receipt.json

SHA256 `ed77b38a9e59f2a0e0c5e5707be663a04bc5078e2d6b47a5f2399d29db6b5e6e`

```json
{
  "scope": "source-binding non-equivalence witnesses on fictional data, not an H1 experiment or full-native test",
  "source_commit": "c72d5d7e5defc9582e032f72fa23a8fc90737aac",
  "source_blob": "861dad4fdc7108157eda9ca7ecbbd38fc13abb75",
  "functions": [
    "turnover_percentiles",
    "theme_pulse_by_ticker",
    "relay_features"
  ],
  "function_copy": "executable bodies copied from native GitHub read; docstrings/comments omitted; isolated helpers",
  "environment": {
    "python": "3.13.5",
    "pandas": "2.2.3"
  },
  "passed": 4,
  "failed": 0,
  "results": [
    {
      "case": "B01_share_volume_percentile_is_not_dollar_liquidity",
      "pass": true,
      "same_native_value": 1.0,
      "accepted_feature_fixture_values": [
        5.488937726156687,
        10.090008612393838
      ]
    },
    {
      "case": "B02_last_non_null_is_not_contiguous_expected_window",
      "pass": true,
      "native_window": 20,
      "required_recent_20_non_null": 17,
      "H1_feature_disposition": "INPUT_SUPPORT_UNQUALIFIED"
    },
    {
      "case": "B03_strongest_theme_is_not_eligible_primary_roster",
      "pass": true,
      "native_groups": [
        "FIX_GROUP_B",
        "FIX_GROUP_A"
      ],
      "H1_without_owner_primary": "AMBIGUOUS_OVERLAP_q0"
    },
    {
      "case": "B04_ticker_exclusion_is_not_issuer_exclusion",
      "pass": true,
      "native_relay_count": 1,
      "H1_other_issuer_breadth_fixture": 0.0,
      "native_function_is_not_H1_or_a_bug_claim": true
    }
  ],
  "real_data_read": false,
  "fit_executed": false,
  "native_module_imported": false,
  "script_sha256": "246a9182746c7e9d9274c9222b557ca1640da532dbab40b0fd30706db10e560d"
}
```

