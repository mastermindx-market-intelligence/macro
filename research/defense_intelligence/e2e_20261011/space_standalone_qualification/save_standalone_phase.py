from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import gzip,json,subprocess,shutil

D=Path(__file__).parent;N=D/'standalone-runtime'
Q=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/pr-9066-e4ea65fadb39fb56')
W=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main')
O=Q/'research/defense_intelligence/e2e_20261011/space_standalone_qualification';O.mkdir(exist_ok=False)
delta=json.loads((D/'standalone-delta-v2/RESULT.json').read_text());assert delta['all_apply']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=Q,text=True).strip()==delta['base']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=W,text=True).strip()==delta['base']
files={}
for name in delta['changed_paths']:
    actual=(Q/name).read_bytes();expected=subprocess.check_output(['git','show',delta['result_tree']+':'+name],cwd=Q)
    assert actual==expected,name
    files[name]=sha256(actual).hexdigest()
assert '166 passed' in (D/'standalone-tests.log').read_text()
ci=json.loads((D/'STANDALONE_CI_CLOSURE.json').read_text());assert len(ci['jobs'])==16 and ci['no_uncovered_paths']
compare=json.loads((N/'PUBLIC_DISCLOSURE_COMPARISON.json').read_text())
assert {x[0] for x in compare['differences']}=={'/as_of','/content_id','/theme_content_id'}
theme=json.loads((N/'SPACE_THEME_STAGE_RECEIPT.json').read_text())
assert set(theme['all_six_theme_research_states'].values())=={'EVIDENCE_INSUFFICIENT'}
for name in ['GREEN_SOURCE.json','FULL_ECONOMICS_STAGE_RECEIPT.json','SPACE_THEME_STAGE_RECEIPT.json','PUBLIC_DISCLOSURE_COMPARISON.json','verify_real_source.py','build_full_economics_stage.py','qualify_theme_stage.py']:
    shutil.copy2(N/name,O/name)
for name in ['source-replay.log','full-consumer.log','theme-stage.log']:
    (O/(name+'.gz')).write_bytes(gzip.compress((N/name).read_bytes(),mtime=0))
for name in ['FULL_ECONOMICS_STAGE.json','theme-stage/theme-public-disclosure.json','theme-stage/theme-reference-snapshot.json','theme-stage/config/government_revenue/program_theme_assignments.v1.json']:
    (O/(Path(name).name+'.gz')).write_bytes(gzip.compress((N/name).read_bytes(),mtime=0))
for name in ['STANDALONE_CI_CLOSURE.json','STANDALONE_WORKTREE_MINT.json','check_standalone_ci_closure.py','save_standalone_phase.py']:
    shutil.copy2(D/name,O/name)
for name in ['standalone-tests.log','standalone-ci-closure.log']:
    (O/(name+'.gz')).write_bytes(gzip.compress((D/name).read_bytes(),mtime=0))
shutil.copy2(D/'standalone-delta-v2/RESULT.json',O/'DELTA_PROVENANCE.json')
shutil.copy2(D/'standalone-review/COMMISSION.json',O/'PENDING_REVIEW_COMMISSION.json')
phase={'state':'STANDALONE_SPACE_SOURCE_AND_CONSUMER_VERIFIED_REVIEW_PENDING','verified_at':datetime.now(timezone.utc).isoformat(),'base':delta['base'],'source_tree':delta['result_tree'],'source_files':files,'tests_passed':166,'ci_import_scopes_closed':16,'actual_full_source_replay':True,'existing_quartet_financial_facts_preserved':True,'source_to_theme':'Seven exact NOC Space references only; other theme references retained, six market leaves remain stale','bounded_visual_reuse':{'source_evidence_commit':'c682d5295db250e8419e4589a00c3f4ef801c313','component_cells':8,'basis':'All public disclosure bytes are semantically identical except three top-level current projection identity/time fields. UI source is untouched by the ten-path delta.','limit':'Explicit component fixture, parent visual inspection; not full-page or installed/authenticated acceptance.'},'capacity_changes_in_delta':False,'canonical_financial_or_theme_owner_written':False,'release_branch_modified':False,'publication':False,'independent_review':'defense-space-standalone-review-01a13300-a pending retained result; no acceptance yet','next':'Consume and adjudicate the exact retained independent integration review. This contribution remains outside PR9066 until its existing release settles; preserve all source/effect/release gates.'}
(O/'VERIFIED_PHASE.json').write_text(json.dumps(phase,indent=2)+'\n')
index={str(p.relative_to(O)):{'sha256':sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(O.rglob('*')) if p.is_file()}
(O/'INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
h=Q/'agentos/handoffs/DEFENSE-PROCUREMENT-V3-2026-10-13-e2e-recovery.md'
with h.open('a') as f:f.write('\n\n## 2026-10-14 — Isolated Space integration qualified against exact release head\n\nAn external SSD helper-created checkout of PR9066 head `5bbaaa712145fd147bb86ff7559f7c41071e37de` applies only the ten-path Space financial source/interpretation delta. It passes 166 affected tests and sixteen complete import closures. Real NOC source replay preserves all twenty old facts and six previously qualified Space values while qualifying the GEM63XL adjustment. Full consumer staging preserves every existing quartet financial fact; the seven new Space references reach the theme and all six themes remain EVIDENCE_INSUFFICIENT. Comparison with the previously captured component differs only in three top-level projection identity/time fields; bounded component evidence is reused with its original limits. No capacity contribution or canonical owner/config was applied. Independent integration review `defense-space-standalone-review-01a13300-a` is pending; review is not acceptance until consumed and adjudicated. PR9066 and its current hosted failure remain unchanged. See `research/defense_intelligence/e2e_20261011/space_standalone_qualification/`.\n')
print(json.dumps({'saved':str(O),'files':len(index),'verified_source_files':len(files)}))
