import copy
import hashlib
import json
import pytest
from engine.neuralweb.bottom_sensors_shadow import snapshot


def context():
    return {"schema":"bottom_pivot_context.v1","symbol":"ABC",
            "decision_at":"2026-11-05T22:00:00Z", "is_display_only":True,
            "action_authority":"none", "probability":None,
            "evidence":[{"field":"coiled_fire","value":True}]}


def record():
    return {"symbol":"ABC", "decline_geometry":"flush", "pivot_context":context()}


def lines(path):
    return [json.loads(x) for x in path.read_text().splitlines()]


def test_receipt_stored_in_incumbent_book_with_exact_digest(tmp_path):
    path=tmp_path/'book.jsonl';r=record();before=copy.deepcopy(r)
    assert snapshot('2026-11-05',[r],path=str(path),recorded_at='2026-11-05T22:01:00Z')==1
    saved=lines(path)[0]
    encoded=json.dumps(r['pivot_context'],ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    assert saved['pivot_context_sha256']==hashlib.sha256(encoded.encode()).hexdigest()
    assert saved['pivot_context']==r['pivot_context']
    assert saved['pivot_recorded_at']=='2026-11-05T22:01:00Z'
    assert r==before


def test_rebuild_cannot_rewrite_issued_context(tmp_path):
    path=tmp_path/'book.jsonl';r=record()
    snapshot('2026-11-05',[r],path=str(path),recorded_at='2026-11-05T22:01:00Z')
    original=path.read_bytes();r['pivot_context']['evidence'][0]['value']=False
    assert snapshot('2026-11-05',[r],path=str(path),recorded_at='2026-11-06T02:00:00Z')==0
    assert path.read_bytes()==original


def test_old_row_never_backfilled_with_new_first_seen(tmp_path):
    path=tmp_path/'book.jsonl'
    snapshot('2026-11-05',[{'symbol':'ABC'}],path=str(path))
    original=path.read_bytes()
    assert snapshot('2026-11-05',[record()],path=str(path),recorded_at='2026-11-06T02:00:00Z')==0
    assert path.read_bytes()==original and 'pivot_recorded_at' not in lines(path)[0]


@pytest.mark.parametrize('stamp',[None,'bad','2026-11-05','2026-11-05T21:59:00Z'])
def test_invalid_or_backdated_capture_not_fabricated(tmp_path,stamp):
    path=tmp_path/'book.jsonl';snapshot('2026-11-05',[record()],path=str(path),recorded_at=stamp)
    assert 'pivot_context' not in lines(path)[0]


@pytest.mark.parametrize('key,value',[('symbol','OTHER'),('schema','wrong'),('probability',.8),('action_authority','trade'),('is_display_only',False)])
def test_wrong_subject_or_promoted_claim_not_captured(tmp_path,key,value):
    path=tmp_path/'book.jsonl';r=record();r['pivot_context'][key]=value
    snapshot('2026-11-05',[r],path=str(path),recorded_at='2026-11-05T22:01:00Z')
    assert 'pivot_context' not in lines(path)[0]


def test_nonfinite_context_cannot_corrupt_book(tmp_path):
    path=tmp_path/'book.jsonl';r=record();r['pivot_context']['bad']=float('nan')
    snapshot('2026-11-05',[r],path=str(path),recorded_at='2026-11-05T22:01:00Z')
    assert 'pivot_context' not in lines(path)[0]
    json.dumps(lines(path),allow_nan=False)
