"""Publication integrity and revision round-trip failures must not look green."""
import copy
import hashlib
import json

import pandas as pd
import pytest

from engine.cot_positioning import build_snapshot, validate_snapshot
from scripts.build_cot import build
from tests.test_cot_positioning import history


def blank():
    return build_snapshot(now='2026-10-09T20:00:00Z', reader=lambda *_:None)


def rehash(snapshot):
    payload={k:v for k,v in snapshot.items() if k!='content_sha256'}
    snapshot['content_sha256']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def test_complete_unavailable_snapshot_is_valid_and_deterministic():
    a=blank();b=blank()
    assert a==b
    validate_snapshot(a)


@pytest.mark.parametrize('digest',['../../escape','bad','A'*64,None])
def test_digest_is_not_a_path_and_rejected_before_any_output(digest,tmp_path):
    p=blank();p['content_sha256']=digest
    with pytest.raises(ValueError):build(site=tmp_path/'output',snapshot=p)
    assert not (tmp_path/'output').exists()


def test_corrupt_payload_refused_before_publication(tmp_path):
    p=blank();p['markets'][0]['name']='not the original payload'
    with pytest.raises(ValueError,match='digest mismatch'):build(site=tmp_path/'output',snapshot=p)
    assert not (tmp_path/'output').exists()


def test_granting_trade_authority_is_rejected_even_with_matching_digest():
    p=blank();p['authority']['can_trade']=True;rehash(p)
    with pytest.raises(ValueError,match='trading authority'):validate_snapshot(p)


def test_duplicate_market_identity_is_not_complete_coverage():
    p=blank();p['markets'][1]=copy.deepcopy(p['markets'][0]);rehash(p)
    with pytest.raises(ValueError,match='identities'):validate_snapshot(p)


def test_revised_older_row_parquet_roundtrip_serializes_missing_revision_as_null(tmp_path):
    f=history(64)
    f.loc[f.index[-2],'revised_at']='2026-10-12T20:00:00Z'
    f.loc[f.index[-2],'version_observed_at']='2026-10-12T20:00:00Z'
    path=tmp_path/'revised.parquet';f.to_parquet(path);loaded=pd.read_parquet(path)
    p=build_snapshot(now='2026-10-13T20:00:00Z',reader=lambda g,n:loaded if n=='cot_legacy_209742' else None)
    validate_snapshot(p)
    market=next(m for m in p['markets'] if m['market_id']=='nasdaq')
    assert market['families']['legacy']['revised_at'] is None
