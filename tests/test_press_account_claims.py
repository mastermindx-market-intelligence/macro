"""Deterministic native Press measurement controls, isolated from the authoring planner."""
import json
from pathlib import Path
from admin import press_audience as A

def _seed(root):
    p=root/'data/press/published.jsonl';p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'id':'press-brief-1','ts':'2026-07-26T13:20:00Z','desk':'brief','slug':'a-published-note','urls':['https://www.mastermind-x.com/blog/a-published-note.html']})+'\n')
    return root

def _read(root, query):
    rows,digest,complete=A.ledger_snapshot(root/'data/press/published.jsonl')
    return {'ok':True,'signup_claims':A.signup_claims(rows,digest,complete,query,publication_limit=20)}

def _claim_response(identity="press-brief-1", count=0):
    return {"publication_id": identity, "published_at": "2026-07-26T13:20:00+00:00",
            "observed_at": "2026-11-05T12:00:00Z", "active_accounts_claiming_content": count,
            "earliest_signup_at": "2026-07-26T13:20:00Z" if count else None,
            "latest_signup_at": "2026-11-04T20:00:00Z" if count else None}


def test_signup_claims_zero_is_only_a_successful_known_input_read(tmp_path):
    root = _seed(tmp_path)
    good = _read(root, lambda sql: [_claim_response()])["signup_claims"]
    assert good["status"] == "available" and good["rows"][0]["active_accounts_claiming_content"] == 0
    for response in (None, [], {}, [_claim_response("unknown")], [_claim_response(), _claim_response()]):
        bad = _read(root, lambda sql: response)["signup_claims"]
        assert bad["status"] == "unavailable" and bad["rows"] == []


def test_signup_claims_reject_partial_malformed_counts_and_windows(tmp_path):
    root = _seed(tmp_path)
    cases = [
        {"active_accounts_claiming_content": -1}, {"active_accounts_claiming_content": True},
        {"active_accounts_claiming_content": "0"}, {"active_accounts_claiming_content": 0.0},
        {"active_accounts_claiming_content": 1}, {"published_at": "2026-07-25T13:20:00Z"},
        {"observed_at": "2026-07-25T13:20:00Z"}, {"observed_at": "2026-11-05"},
        {"earliest_signup_at": "2026-07-26T13:20:00Z"}, {"email": "must-not-escape@example.test"},
        {"publication_id": ["press-brief-1"]},
    ]
    positive = _claim_response(count=2)
    cases.extend([{**positive, "earliest_signup_at": "2026-07-26T13:19:59Z"},
                  {**positive, "latest_signup_at": "2026-11-05T12:00:00Z"},
                  {**positive, "latest_signup_at": "2026-07-26T13:19:59Z"},
                  {**positive, "active_accounts_claiming_content": 1}])
    for changes in cases:
        row = {**_claim_response(), **changes}
        result = _read(root, lambda sql: [row])["signup_claims"]
        assert result["status"] == "unavailable" and result["rows"] == [], changes
        assert "must-not-escape" not in json.dumps(result)


def test_signup_claims_backend_failure_does_not_break_press_or_leak_error(tmp_path):
    calls = []
    def fail(sql):
        calls.append(sql)
        raise TimeoutError("PRIVATE_BACKEND_PAYLOAD")
    out = _read(_seed(tmp_path), fail)
    assert out["ok"] is True and len(calls) == 1
    assert out["signup_claims"]["status"] == "unavailable"
    assert "PRIVATE_BACKEND_PAYLOAD" not in json.dumps(out)


def test_signup_claims_invalid_publication_custody_never_queries(tmp_path):
    root = _seed(tmp_path); path = root / Path("data/press/published.jsonl"); original = path.read_text()
    row = json.loads(original.strip().splitlines()[0])
    cases = [original + '{"torn":', original + original, '[]\n',
             json.dumps({**row, "id": "a');DROP TABLE x;--"}),
             json.dumps({**row, "ts": "2026-07-26"})]
    for content in cases:
        path.write_text(content)
        calls = []
        out = _read(root, lambda sql: calls.append(sql))
        assert out["ok"] is True and out["signup_claims"]["status"] == "unavailable"
        assert not calls
    path.unlink()
    assert _read(root, lambda sql: 1)["signup_claims"]["status"] == "unavailable"
    path.write_text("")
    assert _read(root, lambda sql: 1)["signup_claims"]["status"] == "no_publications"


def test_signup_claims_duplicate_identity_and_disagreeing_snapshot_are_unknown(tmp_path):
    root = _seed(tmp_path);path = root / Path("data/press/published.jsonl")
    first=json.loads(path.read_text().strip().splitlines()[0]);second={**first,"id":"press-brief-2"}
    path.write_text(json.dumps(first)+'\n'+json.dumps(second)+'\n')
    for rows in ([_claim_response(),_claim_response()],
                 [_claim_response(),{**_claim_response('press-brief-2'),'observed_at':'2026-11-05T12:00:01Z'}]):
        out=_read(root, lambda sql: rows)
        assert out['signup_claims']['status']=='unavailable'


def test_signup_claims_reads_only_existing_recent_ledger_bound_and_never_writes(tmp_path):
    root=_seed(tmp_path);path=root/Path("data/press/published.jsonl");first=json.loads(path.read_text().strip().splitlines()[0])
    rows=[{**first,'id':f'press-brief-{i}'} for i in range(20+2)]
    path.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()};calls=[]
    def query(sql):
        calls.append(sql)
        return [_claim_response(r['id']) for r in rows[-20:]]
    out=_read(root, query)['signup_claims']
    assert out['status']=='available' and len(out['rows'])==20 and out['total_publications']==22
    assert out['rows'][0]['publication_id']=='press-brief-21'
    assert "('press-brief-0'," not in calls[0]
    assert {p:p.read_bytes() for p in root.rglob('*') if p.is_file()}==before
