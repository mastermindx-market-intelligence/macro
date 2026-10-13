#!/usr/bin/env python3
"""Independent fixed-artifact rational C1 replay; standard library, no source import.

The independently fetched full-board projection and W3 session checks are recorded
in GEX_RUN_REVIEW.md. This portable checker repeats arithmetic over hash-pinned
extracts; it does not fetch source artifacts or attest a parquet decode.
"""
import argparse, json, math, hashlib
from pathlib import Path
from collections import Counter, defaultdict
from fractions import Fraction as Q

base=Path(__file__).resolve().parent
PINNED_SHA256={
    'gex-published-board-extract.json':'af00367aeb4ba9fa64569eacfcac98926e5dcf46f863e1e99348d5d81938972e',
    'gex-w3-archived-coverage.json':'efc0e6965759a1f1c85061c9983f224cc5e8abac4cf8d2255a88c79ba4f67c32',
    'gex-published-run-audit.json':'130e2f352889815047bf392cacec4ecfbc5e813e08dc627dcf4a404cc71122a3',
}
for name,digest in PINNED_SHA256.items():
    if hashlib.sha256((base/name).read_bytes()).hexdigest()!=digest:
        raise ValueError('Pinned evidence identity mismatch: '+name)
b=json.loads((base/'gex-published-board-extract.json').read_text())
rows=b['buy']; n=len(rows)
assert n==69 and len({r['ticker'] for r in rows})==n
assert b['ranking']['stage_order']==['live','setting_up','ran','basing','blocked']
family={'alpha':'F2_MOMENTUM_EXTENSION','off_high':'F2_MOMENTUM_EXTENSION','tier_cascade':'F1_TECHNICAL_CONFLUENCE','sue_fresh':'F4_CATALYST_EVENT','smartmoney_add':'F5_FLOW_POSITIONING','insider_cluster':'F5_FLOW_POSITIONING','gex_confirm_verdict':'F5_FLOW_POSITIONING','news_burst':'F8_ATTENTION_CROWDING'}
tier={'T2':4,'T1':3,'T3':1,'T4':0}; gex={'confirm':1,'neutral':0,'caution':-1}
def finite(x):
    if x is None or isinstance(x,bool): return None
    try: v=float(x)
    except (ValueError,TypeError): return None
    return v if math.isfinite(v) else None
vals={k:[] for k in family}
for r in rows:
    d={'alpha':finite(r.get('alpha')),'off_high':finite(r.get('off_high')),'tier_cascade':tier.get(str((r.get('signal') or {}).get('tier_cascade')).strip()),'sue_fresh':int(bool(r.get('sue_z') and (r.get('sue_fresh_days') or 999)<=60)),'smartmoney_add':int(bool(r.get('smartmoney_chip'))),'insider_cluster':int((r.get('insider_buyers') or 0)>=2),'gex_confirm_verdict':gex.get(str((r.get('gex_confirm') or {}).get('verdict')).strip()),'news_burst':int(((r.get('news_burst') or {}).get('n_recent') or 0)>=3)}
    for k,v in d.items(): vals[k].append(v)
stats={k:{'nonnull':sum(v is not None for v in vv),'distinct':len({v for v in vv if v is not None})} for k,vv in vals.items()}
admitted=sorted(k for k,s in stats.items() if 2*s['nonnull']>=n and s['distinct']>=2)
assert admitted==b['ranking']['fusion']['w3_structural']['admitted_frozen']
def calculate(vectors,keep):
    pct={}
    for k in keep:
        vv=vectors[k]; present=[v for v in vv if v is not None]
        pct[k]=[None if v is None else Q(2*sum(x<v for x in present)+sum(x==v for x in present)+1,2*len(present)) for v in vv]
    duplicates=[(k,l) for k in keep for l in keep if k<l and family[k]==family[l] and pct[k]==pct[l]]
    assert not duplicates
    fs=[]; scores=[]
    for i in range(n):
        groups=defaultdict(list)
        for k in keep:
            if pct[k][i] is not None: groups[family[k]].append(pct[k][i])
        ff={k:sum(v)/len(v) for k,v in groups.items()}
        fs.append(ff); scores.append(sum(ff.values())/len(ff)*100)
    return pct,fs,scores
pct,fs,scores=calculate(vals,admitted)
assert [round(float(s),1) for s in scores]==[r['prophet']['score'] for r in rows]
for i,r in enumerate(rows):
    display=r['prophet']['fusion']
    assert {k:round(float(v[i]),6) for k,v in pct.items() if v[i] is not None}==display['member_percentiles']
    assert {k:round(float(v)*100,2) for k,v in fs[i].items()}==display['family_contribution']
    assert len(fs[i])==display['n_families']
stage={s:i for i,s in enumerate(b['ranking']['stage_order'])}
def rank(ss,rounded=True):
    ordering=sorted(range(n),key=lambda i:(stage[rows[i]['stage']],-round(float(ss[i]),1) if rounded else -ss[i],rows[i]['ticker']))
    out=[0]*n
    for j,i in enumerate(ordering,1): out[i]=j
    return out
full=rank(scores)
assert full==[r['score_rank'] for r in rows]
def compare(other):
    rr=rank(other); ds=[abs(a-c) for a,c in zip(full,rr)]
    before={rows[i]['ticker'] for i,r in enumerate(full) if r<=30}; after={rows[i]['ticker'] for i,r in enumerate(rr) if r<=30}
    return {'rows_with_changed_rational_score':sum(s!=t for s,t in zip(scores,other)), 'rows_moved':sum(d>0 for d in ds),'max_abs_rank_displacement':max(ds),'mean_abs_rank_displacement':sum(ds)/n,'rows_with_changed_published_score':sum(round(float(s),1)!=round(float(t),1) for s,t in zip(scores,other)),'top30_names_replaced':len(before-after),'top30_symmetric_difference':len(before^after)}
no_gex=calculate(vals,[k for k in admitted if k!='gex_confirm_verdict'])[2]
assert no_gex==scores
no_f5=calculate(vals,[k for k in admitted if family[k]!='F5_FLOW_POSITIONING'])[2]
bad={k:list(v) for k,v in vals.items()}; bad['gex_confirm_verdict']=[0 if v is None else v for v in bad['gex_confirm_verdict']]
mutation=calculate(bad,sorted(admitted+['gex_confirm_verdict']))[2]
expected=json.loads((base/'gex-published-run-audit.json').read_text())
for target,ss in [('remove_gex_member_fixed_pool',no_gex),('remove_entire_f5_family_fixed_pool',no_f5),('forbidden_missing_to_neutral_mutation',mutation)]:
    for k,v in compare(ss).items():
        if k!='rows_with_changed_rational_score': assert v==expected[target][k],(target,k,v)
archive=json.loads((base/'gex-w3-archived-coverage.json').read_text())
assert archive['session']['board_as_of']==b['as_of']
assert archive['session']['n_v3_buy_rows']==62 != n
archived_gex=next(r for r in archive['rows'] if r['member']=='gex_confirm_verdict')
assert archived_gex['coverage']==0.370968 and archived_gex['status']=='below_presence'
assert stats['gex_confirm_verdict']=={'nonnull':21,'distinct':3}
assert compare(no_f5)['rows_with_changed_rational_score']==68
assert compare(mutation)['rows_with_changed_rational_score']==69
assert 'gex_confirm_verdict' not in admitted
assert sum(a!=c for a,c in zip(full,rank(scores,False)))==4
result={
    'schema':'options.research.gex_independent_replay.v1',
    'verdict':'PASS',
    'independent_arithmetic':'rational pairwise counts; no pinned module import',
    'evidence_sha256':PINNED_SHA256,
    'rows':n, 'member_stats':stats, 'admitted':admitted,
    'raw_instead_of_published_rounding_rank_changes':4,
    'no_gex':compare(no_gex), 'no_f5':compare(no_f5),
    'synthetic_missing_neutral':compare(mutation),
    'stage_counts':dict(Counter(r['stage'] for r in rows)),
    'archived_extract_rows':62,
    'archived_extract_gex_coverage':archived_gex['coverage'],
    'archived_observation_fingerprint':archive['session']['observation_fingerprint'],
    'claim_limits':[
        'Fixed published population and stages; no upstream cohort reconstruction.',
        'Full-board projection and source-session fetch are review evidence, not rerun here.',
        'Archived parquet is not independently decoded by this checker.',
        'Exact rational score changes can differ from literal incumbent float inequality counts.',
        'No execution attestation, consumer availability, causality, or predictive value.',
        'Synthetic missing-to-neutral mutation is not observed input or a policy proposal.',
    ],
}
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
if args.output.resolve() in {(base/name).resolve() for name in PINNED_SHA256}:
    raise ValueError('Output must not overwrite pinned evidence')
args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
print(json.dumps({'verdict':'PASS','rows':n,'output_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}))
