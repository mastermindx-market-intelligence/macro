from pathlib import Path
from hashlib import sha256
from copy import deepcopy
import json, sys

C = Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/pr-9066-e4ea65fadb39fb56')
D = Path(__file__).resolve().parent
sys.path.insert(0, str(C))
from engine.earnings_release.binding import bind_release_document
from engine.company_intelligence.events import FiscalPeriod
from engine.company_intelligence.defense_profiles import defense_issuer
from engine.company_intelligence.noc_adverse_profile import noc_adverse_profile
from engine.government_revenue.defense_economics_producer import _project_fact

a = json.loads(Path('/Volumes/Mastermind/evidence/defense-investor-01a13303/owner_reads/release_acquisitions/NOC.fixed-acquisition.json').read_bytes())
body = a['exhibit_body']
digest = sha256(body.encode()).hexdigest()
assert digest == '5f8488263feeed78515180fa7ac0d48ca370e4692ac592ddc9371ae62389a038'
b = bind_release_document(body=body, **{k:a[k] for k in ('cik','accession','form','filing_date','acceptance_datetime','report_date','exhibit_url')})
event = 'evt_cik0001133421_2026Q2_source_validation'
facts = noc_adverse_profile().extract_release_facts(bound=b, document_id=b.revision.document_id, event_id=event, fiscal_period=FiscalPeriod(year=2026, quarter=2))
metric = 'issuer_space_gem63xl_unfavorable_eac'
selected = [f for f in facts if f['metric'] == metric]
assert len(selected) == 1
f = selected[0]
assert (f['value'],f['unit'],f['period'],f['basis']) == (91,'USD_million','2026Q2','issuer_reported_program_cost_estimate:GEM63XL:unfavorable_EAC')
old = [f for f in facts if not f['metric'].startswith('issuer_space_')]
oldsha = sha256(json.dumps(old,sort_keys=True,separators=(',',':')).encode()).hexdigest()
prior = json.loads((Path('/Volumes/Mastermind/evidence/defense-e2e-20261012-01a13300/space-profile-implementation/RED_SOURCE.json')).read_bytes())
assert len(old) == 20 and oldsha == prior['actual_noc_profile_incumbent_sha256']
space = [f for f in facts if f['metric'].startswith('issuer_space_segment_')]
assert len(space) == 6 and [f['value'] for f in space] == [2753,2646,236,280,8.6,10.6]
assert len(facts) == 27 and len({f['fact_id'] for f in facts}) == 27
receipt = f['source_span']['receipt']
literal = body.encode()[receipt['span_start_byte']:receipt['span_end_byte']].decode()
assert literal == '91' == f['source_span']['display_excerpt']
workspace = {'event_id':event,'issuer':{'company_id':defense_issuer('NOC').company_id},'fiscal_period':{'year':2026,'quarter':2}}
source = {'kind':'issuer_release','document_id':b.revision.document_id,'source_sha256':digest,'url':a['exhibit_url']}
projected = _project_fact(f,workspace,source,owner_ref='isolated-source-validation-only')
assert projected['fact_class'] == 'reported_eac' and projected['value'] == 91
negative = []
for key,value in [('value',92),('unit','USD_billion'),('period','2026H1'),('basis','issuer_reported_cash_flow:GEM63XL:cash_loss')]:
    mutated = deepcopy(f);mutated[key] = value
    try: _project_fact(mutated,workspace,source,owner_ref='isolated-source-validation-only')
    except ValueError: negative.append(key)
    else: raise AssertionError('Accepted altered ' + key)
for key,value in [('company_id',defense_issuer('LMT').company_id),('year',2025),('quarter',3)]:
    mutated = deepcopy(workspace)
    (mutated['issuer'] if key=='company_id' else mutated['fiscal_period'])[key] = value
    try: _project_fact(f,mutated,source,owner_ref='isolated-source-validation-only')
    except ValueError: negative.append(key)
    else: raise AssertionError('Accepted altered ' + key)
result = {'state':'ONE_REAL_SOURCE_ADVERSE_FACT_AND_PROJECTION_VERIFIED','source_sha256':digest,'incumbent_noc_facts':20,'incumbent_noc_facts_sha256':oldsha,'existing_space_figures_unchanged':6,'total_source_facts':27,'negative_projection_controls':negative,'new_fact':f,'projected_fact':projected,'canonical_writes':0,'publication':False}
(D/'GREEN_SOURCE.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('new_fact','projected_fact')},indent=2))
