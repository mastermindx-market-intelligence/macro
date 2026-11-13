"""Read-only research probe of an exact source snapshot; synthetic temporary registry."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, tempfile
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path)
args=parser.parse_args()
p=args.source
b=p.read_bytes()
blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
assert blob=='63ba2b60e9be6615208fab5b53b1fbcb44f4f433'
spec=importlib.util.spec_from_file_location('r9_native_rights',p)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
rows=[]
def record(name, observed, expected, kind='BEHAVIOR_CHECK'):
    rows.append({'id':name,'kind':kind,'observed':observed,'expected':expected,'matches':observed==expected})
with tempfile.TemporaryDirectory(prefix='r9-rights-') as td:
    reg=Path(td)/'sources.yml'
    reg.write_text('families:\n  vendor:\n    rights_class: derived_display_ok\n    auth_class: vendor\n  house:\n    rights_class: direct_display_ok\n    auth_class: house\n  pending:\n    rights_class: unresolved\n    auth_class: vendor\n  bad:\n    rights_class: not_a_rights_class\n')
    try:m.rights_class('absent',path=reg); refused=False
    except m.RightsRefusal:refused=True
    record('RIGHTS-01',refused,True)
    record('RIGHTS-02',m.emission_allowed('absent',path=reg),False)
    record('RIGHTS-03',m.emission_allowed('pending',path=reg),False)
    record('RIGHTS-04',m.emission_allowed('bad',path=reg),False)
    record('RIGHTS-05',list(m.licensing_for_family('vendor',path=reg)),[True,True,False])
    record('RIGHTS-06',list(m.licensing_for_family('house',path=reg)),[True,True,True])
    record('RIGHTS-07',m.family_for_source_ref('https://issuer.example/report'),None)
    record('RIGHTS-08',m.family_for_source_ref('curation:gmirca_0123456789abcdef0123456789abcdef#observation'),None)
    record('RIGHTS-09',list(m.licensing_for_family('absent',path=reg)),[True,False,False])
    # Baseline is known to allow; change only this temporary on-disk policy.
    record('RIGHTS-10',m.emission_allowed('vendor',path=reg),True)
    reg.write_text('families:\n  vendor:\n    rights_class: internal_only\n    auth_class: vendor\n')
    record('RIGHTS-11',m.emission_allowed('vendor',path=reg),False,'V0_REVOCATION_REQUIREMENT')
    m._load.cache_clear()  # Test-only diagnostic control, not a proposed production patch.
    record('RIGHTS-12',m.emission_allowed('vendor',path=reg),False,'CACHE_INVALIDATION_CONTROL')
assert all(r['matches'] for r in rows if r['id']!='RIGHTS-11')
assert rows[10]['observed'] is True and rows[10]['matches'] is False
out={'scope':'Native-source local probe using only a synthetic temporary registry. No production reads/writes, no leak allegation, no product implementation.',
     'interface_commit':'8183f865e8705e4cd854ed2f696415ece2c3e920','source_path':'engine/theme_graph/rights.py','source_git_blob':blob,
     'checks':rows,'expected_behavior_checks_matching':11,'unmet_v0_requirement_probes':1,
     'finding':'Path-cached native registry returns the earlier allowed class after an in-place policy change in the same process; explicit cache invalidation observes the denial. Production caller reload discipline remains uninspected.',
     'native_admission':False,'production_proven':False}
if args.output is not None:
    args.output.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
