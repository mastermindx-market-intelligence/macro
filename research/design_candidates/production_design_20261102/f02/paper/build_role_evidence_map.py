#!/usr/bin/env python3
"""Bind F02 contract roles to exact prepared input keys, never invented Paper IDs."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib, json, re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
FILE='01M312VSDSZFVT45674GDVJVZN'
PACKETS=['foundation-inputs/boards.json','consumer-inputs/consumer-boards.json','mobile-inputs/mobile-state-boards.json','mobile-inputs/supplemental-boards.json','core-supplement-inputs.json','fault-composition-inputs.json']
registry={}; packets=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for filename in PACKETS:
 data=json.loads((HERE/filename).read_text())
 packets.append({'path':'paper/'+filename,'sha256':sha(HERE/filename),'boards':len(data.get('boards',[])),'append_targets':len(data.get('append_to_existing',[]))})
 for b in data.get('boards',[]):
  assert b['key'] not in registry
  registry[b['key']]={'page_id':b['pageId'],'steps':{s['key']:{'packet':filename,'html_sha256':hashlib.sha256(s['html'].encode()).hexdigest()} for s in b['steps']}}
 for g in data.get('append_to_existing',[]):
  b=registry[g['target_board_key']]
  for s in g['steps']:
   assert s['key'] not in b['steps'],(g['target_board_key'],s['key'])
   b['steps'][s['key']]={'packet':filename,'html_sha256':hashlib.sha256(s['html'].encode()).hexdigest()}

def e(board,*keys):
 if len(keys)==1 and isinstance(keys[0],list):keys=keys[0]
 assert board in registry,board
 assert all(k in registry[board]['steps'] for k in keys),(board,keys)
 return {'board_key':board,'source_page_id':registry[board]['page_id'],'step_keys':list(keys),'input_packets':list(dict.fromkeys(registry[board]['steps'][k]['packet'] for k in keys)),'native_board_id':None,'native_step_ids':{k:None for k in keys},'binding_status':'UNBOUND_BY_THIS_MAP'}
def ep(board,prefix):return e(board,[k for k in registry[board]['steps'] if k.startswith(prefix)])
def both(base,*keys):return [e(base+'-dark',*keys),e(base+'-light',*keys)]
def v(name,refs,shows,limits='',status='INPUT_SPECIMEN_PRESENT'):
 return {'variant':name,'status':status,'evidence':refs,'native_can_show_after_binding_and_review':shows,'still_unverified':limits or 'Actual source integration, semantic HTML/ARIA, keyboard/touch behavior and browser rendering are not proved by native design.'}
def missing(name,reason,refs=None):return v(name,refs or [],'No complete editable example asserted.',reason,'CONTRACT_ONLY_OR_INCOMPLETE_VARIANT')

contract=(ROOT/'SYSTEM_CONTRACT.md').read_text()
rows={}
for line in contract.splitlines():
 if line.startswith('| ') and len(line.split('|'))==6:
  cells=[x.strip() for x in line.split('|')[1:-1]]
  if cells[0] in ['SectionHeader','MetricValue','ChangeValue','FreshnessReceipt','DataRow','TableFrame','VirtualizedDataInspector','ChartFrame','Tabs','EvidenceTrigger','EvidenceInspector','StatePanel','Callout','DetailDisclosure','Action','SaveFeedback','TierGate','Icon','CountLadder','LifecycleRail','DecisionRow / VerdictHero']:rows[cells[0]]=cells[1:]
assert len(rows)==21,len(rows)
links=dict(re.findall(r'^\[([^]]+)\]: (https://\S+)',(ROOT/'SOURCE_AND_DATA_CONTRACT.md').read_text(),re.M))
terminal='https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/b79b1e136290978ff7675087de979bb1b42b3713/terminal/'
links.update({'TA1':terminal+'components/OptionsPaywall.tsx','TA2':terminal+'components/OptionsServiceUnavailable.tsx','TA3':terminal+'lib/entitlement.ts','TA4':terminal+'lib/optionsAccess.ts','TA5':terminal+'lib/i18n.tsx'})
ledger=json.loads((ROOT/'paper-retention-ledger.json').read_text())['rows']
pred={x['board_id']:x for x in ledger}
roles=[]
def role(name,source_keys,sections,predecessors,variants,qualifiers=None,retained=False):
 anatomy,example,exception=rows[name]
 refs=[{'path':'SYSTEM_CONTRACT.md','section':'4. Component anatomy, variants and failure treatment','row':name}]
 refs += [{'path':p,'section':s}for p,s in sections]
 r={'role':name,'role_status':'RETAINED_UNQUALIFIED' if retained else 'EDITABLE_INPUTS_PREPARED_NATIVE_PROOF_PENDING','required_anatomy':anatomy,'contract_meaningful_example':example,'required_exception_treatment':exception,'contract_references':refs,'source_owner_references':[{'key':k,'url':links[k]} for k in source_keys],'predecessors':[{'file_id':FILE,'page_id':pred[n]['page_id'],'board_id':n,'name':pred[n]['name'],'original_disposition':pred[n]['disposition'],'historical_inspection':pred[n]['inspection'],'qualification':'Retained source/reference identity; no current design or domain approval inferred.'}for n in predecessors],'variants':variants,'required_qualifiers':qualifiers or [],'runtime_and_integration_status':'UNVERIFIED_BY_THIS_MAP'}
 roles.append(r)

S='SOURCE_AND_DATA_CONTRACT.md';I='INTERACTION_STATES.md';C='SYSTEM_CONTRACT.md'
role('SectionHeader',['M1','T3','T6','E3'],[(S,'5. Component integration and preservation contract'),(C,'2. Visual hierarchy and archetypes')],['25V-0'],[
 v('analytical heading, period/source and local action',both('macro','question')+both('company','question')+both('options','question'),'Editable heading, source scope/date and separate local action.'),
 v('reading section and publication',both('editorial','article-title','publication','calculation-heading','averages-heading','limits-heading'),'Public reading hierarchy and publication/update distinction.'),
 v('narrow English and Chinese title wrapping',[e('macro-dark-en-390','title'),e('macro-light-zh-390','title')],'390px localized title and question hierarchy.','CJK glyph quality, long-label stress and real browser reflow remain unverified.'),
 v('missing observation period header',[e('fault-compositions','missing-period-headers')],'Complete EXM header in both themes retains the question, currency, explicit missing source period, separate retrieval and source action.','Illustrative missing-period input, not a change to normal Company fixture dates; real host source mapping remains unverified.')])

role('MetricValue',['M1','T11'],[(S,'4.1 Numeric and unit rules'),(I,'Copy and recovery matrix')],['25Z-0'],[
 v('finite percent, typed absence and reported zero',[e('metrics','metric-trio','metric-units')],'66.70%, EPS unknown and dividend 0.00 USD remain visibly different.'),
 v('company field-specific absence and zero',both('company','statement-row-7','statement-row-8','statement-caveat')+[e('company-eps-overlay-320','value','period-2026','comparison','limitation'),e('company-dividend-overlay-320','value','comparison','limitation')],'Five-period EPS absence and reported-zero dividend with an absolute zero change and undefined percentage growth.'),
 v('dated value retained through stale/partial/write status',[e('states-matrix','combined-dark-value','combined-dark-status','combined-dark-action','combined-light-value','combined-light-status','combined-light-action'),e('fault-compositions','combined-confirmed-saved')],'A concrete 66.7% observation remains present beside distinct read and write states, including the matched owner-confirmed saved fixture.','Real request-generation identity, account context and state transitions remain owner integration requirements.')])

role('ChangeValue',['M1','T11'],[(S,'4.1 Numeric and unit rules'),(C,'4.2 Chart grammar')],[],[
 v('signed pp with declared prior-session baseline',[e('metrics','metric-trio','metric-units','data-0','data-1')]+both('macro','metrics','sector-4'),'Positive and negative signed percentage-point changes and explicit comparator.'),
 v('relative percent and absolute currency zero',both('company','statement-row-1','statement-row-8','statement-caveat')+both('editorial','calculation-row-1','calculation-row-2','equations'),'Relative percentage changes and currency-per-share zero are labeled independently.'),
 v('basis points',[e('metrics','core-metric-bps')],'65.57% → 66.70% is +1.13 pp or +113 bps, in both themes.','A unit-conversion fixture, not a new published statistic or production formatter.'),
 v('unavailable comparison from missing/zero baseline',[e('company-eps-overlay-320','comparison','limitation'),e('company-dividend-overlay-320','comparison','limitation')],'Unknown EPS comparison and undefined percentage growth from zero.'),
 v('non-comparable definition and mixed-currency baseline',[e('fault-compositions','withheld-comparisons')],'Two concrete comparisons retain original values/periods/units but withhold the change: different definitions without restatement, and USD/EUR without authorized FX.','These are explicitly counterfactual portable input states. The actual changed-filing definition or currency-mismatch source witness remains a consumer integration requirement.')])

role('FreshnessReceipt',['T7','T12','M4'],[(S,'4.2 Time and freshness rules'),(I,'Independent state axes')],['272-0'],[
 v('observation, publication and retrieval separately',[e('metrics','source-receipt'),e('options-full-row-evidence-320','clocks')]+both('macro','evidence-field-1','evidence-field-2','evidence-field-3'),'Three individually labeled clocks, including ET print observation versus UTC publication/retrieval.'),
 v('transport, market session and snapshot separately',both('options','transport-receipt','question','expiry-heading'),'Connected transport, closed market session and original snapshot/window do not collapse into a live label.'),
 v('stale while useful observations remain',[e('states-matrix','state-3','combined-dark-value','combined-dark-status','combined-light-value','combined-light-status')],'Original observation date remains beside retained value and stale/partial copy.'),
 v('unknown source age with known retrieval',[e('metrics','core-metric-unknown-age')],'Source observation/publication absence is explicit; a retrieval timestamp does not assert freshness.','Separate missing-clock state fixture; it does not replace dates on existing Macro consumer rows.')])

role('DataRow',['T6','T11','M1'],[(S,'5.1 Table, chart and overlay behavior'),(C,'4.1 Density and truncation'),(I,'Control/action contracts')],['26J-0','27I-0'],[
 v('sector rows and selection',both('macro',*[f'sector-{i}' for i in range(1,11)]),'All ten sector identities, aligned values, typed absence, coverage and row evidence.'),
 v('five-period Company metrics',both('company',*[f'statement-row-{i}' for i in range(1,10)]),'All nine financial metrics and five annual columns, including missing EPS and zero dividends.'),
 v('complete Options print fields',both('options',*[f'print-{i:02}' for i in range(1,13)]),'Twelve prints with twelve explicit fields.','No real data, sorting, filtering, producer schema or export scope is qualified.'),
 v('narrow complete-row evidence and stable identity',[e('options-full-row-evidence-320','entity','contract-fields','print-fields','context-fields','source-identity','clocks','return-action'),e('macro-zh-evidence-return-390','entity','source-identity','returned-selected-row')],'Full first Options row at 320px and matched Chinese Macro evidence/return row.','Source-row identity is specified; actual trigger restoration after filtering/reordering remains a browser requirement.')])

role('TableFrame',['T6','T13','T15'],[(S,'5.1 Table, chart and overlay behavior'),(S,'11.3 Closed-form criteria for the open consumer integration gap'),(C,'4.1 Density and truncation')],['2O6-0'],[
 v('caption, headers, local controls, scope and evidence',both('macro','table-caption','table-header','table-behavior')+both('company','statement-caption','statement-header','statement-caveat')+both('options','filters','tape-caption','tape-header','cohort-caption'),'Dense comparison geometry and declared field/count/coverage scope; numeric alignment and source column.'),
 v('narrow comparison with overflow cue and adjacent evidence',[e('macro-dark-en-390','section-toolbar','scroll-cue','table','sector-3','post-table'),e('macro-light-zh-390','section-toolbar','scroll-cue','table','sector-3','post-table')],'Local-width frame, visible overflow instruction and first-column row evidence target.','Paper does not demonstrate scrolling, sticky behavior, semantic headers, aria-sort, or whole-page reflow.'),
 v('reading calculation table',both('editorial','calculation-caption','calculation-header','calculation-row-0','calculation-row-1','calculation-row-2','calculation-evidence'),'Readable calculation rows and explicit evidence path inside article measure.'),
 v('composed empty / unavailable / retained-error table',[e('fault-compositions','empty-table-context','empty-table-state','unavailable-table-context','unavailable-table-state','retained-table-context','retained-operating-income','retained-pretax-income','retained-net-income','retained-table-error')],'Three complete table-frame compositions retain EXM identity, requested periods, filters, scoped count/absence, headers, source clock and recovery. The error frame preserves three exact Company fixture rows.','Illustrative response states only; actual semantic headers, filtering, source availability, retry effects and retained-row rendering remain unverified.')])

role('VirtualizedDataInspector',['T13','T15'],[(S,'5. Component integration and preservation contract'),(S,'5.1 Table, chart and overlay behavior'),(S,'11.3 Closed-form criteria for the open consumer integration gap'),(I,'Control/action contracts')],[],[
 v('existing virtualized inspector retained',[e('grammar','virtualization')],'Annotation records retention requirements only; no new editable virtualized inspector is asserted.','Actual incumbent grid, time keys, selection, mounted active descendant and row-limit behavior remain unqualified.','RETAINED_UNQUALIFIED')],qualifiers=[
 'Bind an exact existing Terminal DataInspector revision and an actual canonical item/time-key dataset; no index-as-identity substitute.',
 'Exercise sort, prepend, filter and replay while preserving selected record identity, mounted active descendant, row count/index and generation reset.',
 'Exercise Arrow/Page/Home/End/Shift/Space/Enter/Escape semantics and accurate CSV/replay record scope.',
 'Qualify the 50,000-row range/export refusal and screen-reader behavior on the actual owner; do not create a second virtualizer.'
 ],retained=True)

role('ChartFrame',['M5','M6','T13','T15','T8'],[(S,'5. Component integration and preservation contract'),(S,'11.1 Exact Company fixture scope'),(C,'4.2 Chart grammar')],['2PH-0'],[
 v('axis/range/gap anatomy with exact values',[e('grammar','chart-title','chart','exact-values','chart-source')],'Eight categorical sessions, numeric 50–80% range and a missing 26 Oct point; native labels remain editable.','This is a separate anatomy fixture. It is not the 40–80% Macro consumer series with 23 Oct missing (AC-06).'),
 v('Macro gap in the consumer context',both('macro','history-title','history-unit','history-chart')+[e('macro-dark-en-390','chart-heading','chart','chart-footer')],'Seven of eight observations, 23 Oct gap, declared 40–80% range and categorical session axis.'),
 v('Company dense five-series 17-year history',both('company','history-heading','history-legend','history-chart','statement-caption'),'85 bar marks across 17 fiscal years with five-series numbered legend, USD bn and zero baseline.','The complete 17×5 exact-values view is implemented in the supporting HTML fixture; native board shows its entry action and last-five-period statement table, not an opened 85-value inspector.'),
 v('Options expiry cohort bars',both('options','expiry-heading','expiry-summary','cohort-caption'),'Two expiry groups totaling the fixture cohort and separate print observation window; side semantics stay independent.'),
 v('unavailable chart series in its full frame',[e('fault-compositions','unavailable-chart-context','unavailable-chart-state')],'Complete unavailable Revenue-history frame retains EXM, requested FY 2010–2026, USD bn, honest unknown scale/source clock, disabled exact values and coverage recovery. No zero or fabricated data marks are drawn.','Fault-state fixture; actual chart data owner, recovery callback and existing engine behavior remain unverified.')])

role('Tabs',['M1','T3','T6'],[(I,'Control/action contracts'),(I,'Focus, overlays and input details')],['26C-0'],[
 v('default, hover, selected and keyboard focus',[e('controls','tabs','supplement-hover-row')],'Four concrete 44px tab states; neutral selection and independent focus outline.'),
 v('consumer panel naming and preserved domain entry points',both('macro','tabs')+both('company','statement-tabs'),'Comparison/chart/source entry and existing statement families/period modes remain visible.','Roving focus, manual activation, panel IDs and the actual owner parser remain unverified.'),
 v('busy versus empty active panel',[e('fault-compositions','tabs-comparison','tabs-loading-panel','tabs-empty-panel')],'The same EXM/FY 2025–2026/ZZZ context and selected Table tab have concrete active panels. Loading has no count; completed empty reports zero and offers Clear filter.','The named panel, selection and state geometry are prepared; actual roving focus, aria-busy, semantic panel identity and activation remain unverified.')])

role('EvidenceTrigger',['M4','T14','T6'],[(S,'5. Component integration and preservation contract'),(I,'Control/action contracts')],['2BK-0'],[
 v('visible row-specific evidence actions',both('macro','sector-4')+both('company','statement-row-7','statement-row-8')+both('options','print-01'),'Visible evidence text stays associated with the exact row/field.'),
 v('icon plus visible action and 44px target',[e('foundations','core-icon-evidence','core-icon-sizes'),e('macro-dark-en-390','sector-3'),e('macro-light-zh-390','sector-3')],'Reused icon anatomy and important phone target geometry; text remains present.','Context-specific accessible names, citation precision and touch activation still need browser/source wiring.'),
 v('return matches the originating row',[e('macro-zh-evidence-return-390','return-action','returned-selected-row'),e('options-full-row-evidence-320','return-action')],'Return names match the selected Macro row or exact Options print identity.')])

role('EvidenceInspector',['M4','T14','T13'],[(S,'5.1 Table, chart and overlay behavior'),(S,'11.2 Independent state and evidence admission'),(I,'Focus, overlays and input details')],['2BK-0'],[
 v('wide dock with values, three clocks, limitation and close',both('macro','evidence-head','evidence-entity','evidence-value-0','evidence-value-1','evidence-value-2','evidence-field-0','evidence-field-1','evidence-field-2','evidence-field-3','evidence-field-4','evidence-caveat','evidence-return')+[e('macro-docked-1280','dock-heading','dock-entity','dock-value','dock-source-0','dock-source-1','dock-source-2','dock-source-3','dock-source-4','dock-footer')],'Complete contextual Macro dock and a narrow-desktop dock composition.','The dock is specified not to trap focus; actual opening/closing, source fetch and focus return remain unverified.'),
 v('320px missing and zero Company field inspectors',[e('company-eps-overlay-320','header','title','value','period-2022','period-2023','period-2024','period-2025','period-2026','comparison','source-0','source-1','source-2','source-3','source-4','source-5','limitation','return'),e('company-dividend-overlay-320','header','title','value','period-2022','period-2023','period-2024','period-2025','period-2026','comparison','source-0','source-1','source-2','source-3','source-4','source-5','limitation','return')],'Complete five-period field evidence at 320px with missing/zero distinction and close/return.'),
 v('complete 12-field Options row at 320px',[e('options-full-row-evidence-320','dialog-header','entity','contract-fields','print-fields','context-fields','source-identity','clocks','limitation','return-action')],'All twelve exact print-01 fields, source identity, separate observation/expiry/cohort/publication/retrieval, interpretation limits and 44px close/return.','Illustrative fixture, not a real producer receipt or consumer integration proof.'),
 v('Chinese comparison → evidence → return',[e('macro-light-zh-390','metric','sector-3'),e('macro-zh-evidence-return-390','dialog-header','entity','values','value-0','value-1','value-2','baseline','source-identity','source-clocks','units','coverage-limit','return-action','return-state','returned-selected-row')],'Matched Chinese values, source key, critical limits and same-row return state at 390px.','Actual modal trap, backdrop inertness, CJK rendering, scroll return and dock/overlay transitions need browser qualification.'),
 v('768/1024 overlay and 1600 dock content classes',[e('width-768-overlay','overlay-header','overlay-entity','overlay-values','overlay-source','overlay-clocks','overlay-limit','overlay-return'),e('width-1024-overlay','overlay-header','overlay-entity','overlay-values','overlay-source','overlay-clocks','overlay-limit','overlay-return'),e('width-1600-docked','dock-heading','dock-entity','dock-value','dock-source-0','dock-source-1','dock-source-2','dock-source-3','dock-source-4','dock-footer')],'Prepared content-width classes with concrete comparison and contextual evidence.','F01 joint geometry freeze and actual viewport/zoom behavior remain separate gates.'),
 v('source-unavailable inspector with retained entity summary',[e('fault-compositions','unavailable-inspector-context','unavailable-inspector-summary','unavailable-inspector-source-error','unavailable-inspector-return')],'A complete Communication-services inspector retains 66.70%, +1.13 pp, 21/21, baseline, exact source key and original three clocks while unavailable supporting citation detail has typed recovery and close/return.','The failed supporting-source read is illustrative. Cached-summary admission, actual source recovery, modal behavior and identity-based return remain consumer/browser requirements.')])

role('StatePanel',['M1','T12','T4'],[(S,'4.3 State axes and required copy'),(I,'Copy and recovery matrix'),(I,'Component state applicability and specimen coverage')],['2A7-0','2M3-0'],[
 v('loading, empty, partial, stale, read error and unsupported',[e('states-matrix',*[f'state-{i}' for i in range(6)])],'Six distinct dark/light outcomes with scope, absence/count language and appropriate read recovery.'),
 v('guest, denied, expired, first use, corrected and loaded',[e('states-matrix','state-6','state-7','state-8','state-9','state-14','state-15')],'Named access/availability/provenance states; routine loaded data lacks a permanent success banner.','Valid starting choices, actual corrected-source lineage and host access return destinations are source integration requirements.'),
 v('source unavailable versus entitlement service unavailable',[e('states-matrix','supplement-source-unavailable','supplement-access-service-unavailable'),e('controls-variants','core-tier-unavailable-dark','core-tier-unavailable-dark-actions','core-tier-unavailable-light','core-tier-unavailable-light-actions')],'No conflation of publisher absence, subscription denial and provider outage.'),
 v('orthogonal combined states with useful values',[e('states-matrix','combined-dark-value','combined-dark-status','combined-dark-action','combined-light-value','combined-light-status','combined-light-action')],'Stale+partial+pending and stale+partial+expired-after-send/uncertain are concretely composed.'),
 v('unknown age',[e('metrics','core-metric-unknown-age')],'Explicit missing observation/publication clock and known retrieval remain distinct.'),
 v('no publication yet / coverage not quantified',[e('fault-compositions','not-yet-published-state','unquantified-coverage-state')],'Concrete source/calendar context and last-observation recovery accompany not-published input. A separate coverage fixture retains seven available records, an explicitly unknown eligible total and no computed fraction.','Publication status is a declared input, not inferred from a missing network response. Real producer publication/coverage semantics remain unverified.')])

role('Callout',['M1','E3'],[(C,'2. Visual hierarchy and archetypes'),(I,'Copy and recovery matrix'),(S,'4.1 Numeric and unit rules')],['29H-0','2NG-0'],[
 v('critical analytical caveat remains visible',both('company','statement-caveat')+both('options','question','cohort-caption')+[e('options-full-row-evidence-320','limitation')],'Missing-field, undefined-growth and estimated-side limitations remain readable beside their affected answer.'),
 v('editorial assumption and limitation',both('editorial','limits-heading','limits-copy','equations'),'Concise assumption/consequence text within the article, without a status-colored edge.'),
 v('narrow source limitation',[e('company-eps-overlay-320','limitation'),e('company-dividend-overlay-320','limitation'),e('macro-zh-evidence-return-390','coverage-limit')],'Critical caveat remains outside optional disclosure and available at narrow widths.')])

role('DetailDisclosure',['M4','M1'],[(I,'Control/action contracts'),(I,'Focus, overlays and input details'),(S,'5. Component integration and preservation contract')],['2GG-0','2LX-0'],[
 v('collapsed desktop',[e('controls-variants','core-disclosure-collapsed')],'Explicit, stable summary and visible Show method affordance.'),
 v('expanded desktop',[e('controls-variants','core-disclosure-expanded-summary','core-disclosure-expanded-body')],'Same summary and readable method body; the answer is outside the optional region.'),
 v('failed detail read retains summary/context',[e('controls-variants','core-disclosure-error-summary','core-disclosure-error-copy','core-disclosure-error-action')],'Error is inside the expanded region with a specific read-only recovery action.'),
 v('collapsed, expanded and error at 320px',[e('controls-variants','core-disclosure-mobile-label','core-disclosure-mobile-collapsed','core-disclosure-mobile-expanded-summary','core-disclosure-mobile-expanded-body','core-disclosure-mobile-error-summary','core-disclosure-mobile-error-copy','core-disclosure-mobile-error-action')],'Long summary wraps; important summary/retry controls meet the proposed 44px geometry.','Touch/keyboard toggling, aria-expanded, panel identity, focus, request-cache behavior and actual mobile reflow remain unverified.')])

role('Action',['M4','T14','T4'],[(I,'Control/action contracts'),(S,'11.3 Closed-form criteria for the open consumer integration gap')],['28D-0'],[
 v('primary, secondary and quiet hierarchy in both themes',[e('controls-variants','core-action-hierarchy-dark','core-action-hierarchy-light')],'Calm filled primary, neutral outlined secondary and text-led quiet action with 44px targets.'),
 v('pending primary disables repeat action, reading remains available',[e('controls-variants','core-action-disabled'),e('states-matrix','state-10')],'Saving label and disabled treatment coexist with an available evidence action.','Only the existing write owner may enforce deduplication or confirm result.'),
 v('read recovery and uncertain-write reconciliation',[e('states-matrix','state-4','state-12','state-13'),e('controls-variants','core-tier-unavailable-dark-actions','core-tier-unavailable-light-actions')],'Read retry, confirmed save failure and unknown save outcome use different named actions.'),
 v('44px labeled close and return',[e('options-full-row-evidence-320','dialog-header','return-action'),e('macro-zh-evidence-return-390','dialog-header','return-action')],'Visible target geometry and contextual return labels at 320/390px.')])

role('SaveFeedback',[],[(I,'Independent state axes'),(I,'Copy and recovery matrix'),(S,'11.3 Closed-form criteria for the open consumer integration gap')],[],[
 v('pending, saved, confirmed failure and uncertain',[e('states-matrix','state-10','state-11','state-12','state-13')],'Four separate dark/light states with appropriate action language and retained local-edit intent.','The saved object name is a fixture. There is no actual request/object receipt, commit, readback or write.'),
 v('confirmed save preserves the same stale and partial read snapshot',[e('states-matrix','combined-dark-heading','combined-dark-value','combined-dark-status'),e('fault-compositions','combined-confirmed-saved')],'Matched before/after design retains 66.7%, +1.13 pp, 7/8, 30 Oct 20:00 source and both read caveats after an owner-confirmed illustrative saved result.','Saved object, request fixture-save-01 and owner readback are explicitly illustrative. No actual write, source update or executed transition is asserted.'),
 v('expiry after dispatch retains data and becomes uncertain',[e('states-matrix','combined-light-value','combined-light-status','combined-light-action')],'No assertion that nothing was sent; reconciliation follows sign-in while useful dated observations remain.'),
 v('existing-owner contract annotation',[e('controls','saves')],'Annotation identifies D23/current owner; it is not a mutation demonstration.','Bind real endpoint/callback, immutable account subject, request identity, reconciliation and idempotency policy.','ANNOTATION_ONLY')],qualifiers=['D23/current mutation owner must bind immutable subject, object/request identity, confirmed noncommit versus ambiguity, dedupe/reconciliation and actual readback.','Verify context preservation on valid sign-in/plan/session recovery; navigation/theme/language remain read-only.'])

role('TierGate',['M8','T4','TA1','TA2','TA3','TA4','TA5'],[(S,'5. Component integration and preservation contract'),(S,'2.3 Exact public editorial boundary — newly resolved'),(I,'Copy and recovery matrix')],['2RE-0'],[
 v('resource-specific Options denied in both themes',[e('controls-variants','core-tier-denied-dark-copy','core-tier-denied-dark-action','core-tier-denied-light-copy','core-tier-denied-light-action')],'Live Options resource, existing access requirement copy, feature description and existing onboarding entry. No paid tape is shown behind the gate.','Pinned-source offer copy must be checked by the billing owner before release. Real access is not granted by plan wording.'),
 v('resource-specific Options provider unavailable',[e('controls-variants','core-tier-unavailable-dark','core-tier-unavailable-dark-actions','core-tier-unavailable-light','core-tier-unavailable-light-actions')],'Unavailability is distinct from denial; existing reload and /terminal actions remain available without a billing flow.','The actual route is gated before OptionsWorkspaceMount; no entitlement or protected-payload test has been run.'),
 v('guest and expired recovery where the host permits public reading',[e('states-matrix','state-6','state-8','combined-light-status','combined-light-action')],'Host-dependent guest/expiry messages do not override Options route policy.','Existing return URL, authentication and payload omission must be bound and exercised by F01/D25/domain owners.')],qualifiers=['getLiveOptionsAccess is tri-state; denied returns OptionsPaywall, unavailable returns OptionsServiceUnavailable, allowed mounts the workspace.','optionsReadAccess uses terminal_live_options feature or the exact existing unlimited exception; paid-tier label alone is insufficient.','The copied paywall CTA calls onboarding.open(signup,{plan:essential}); unavailable retry reloads and its existing chart link is /terminal. No new plan, URL or entitlement owner is introduced.','Do not serve paid Options data on denial/uncertainty or revoke unrelated public evidence by transplanting this resource policy.'])

role('Icon',['M7'],[(S,'3.2 Type, space, radius, motion and icon collisions'),(S,'5. Component integration and preservation contract'),(C,'4.3 Icon and effect reconciliation')],[],[
 v('evidence, direction and recovery anatomy',[e('foundations','core-icon-evidence','core-icon-direction','core-icon-recovery')],'Native SVG reuses exact existing search, arrow_up and swirl paths; 24 viewBox, 1.8 stroke, currentColor and dark/light labeled anatomy.'),
 v('optical sizes and labeled targets',[e('foundations','core-icon-sizes')],'16/20/24px rendered sizes retain the 24-unit path; important controls show 44px target geometry.','Optical balance after Paper import, currentColor inheritance in the browser, decorative aria-hidden and forced colors require separate verification.'),
 v('unknown direction suppresses invented mark',[e('foundations','core-icon-direction')],'Unknown comparison uses text and a reserved blank slot rather than an inferred arrow.'),
 v('source owner and accessible-name contract',[e('foundations','core-icon-reuse-contract')],'The source/reuse note is an annotation, not proof of browser accessibility.','No new React import, icon package or brand asset is established.','ANNOTATION_ONLY')])

role('CountLadder',[],[(S,'11.3 Closed-form criteria for the open consumer integration gap'),(I,'Component state applicability and specimen coverage')],['2CM-0','2HH-0'],[
 v('retained desktop/mobile domain ladder',[],'Existing canonical reference identity only; no new concrete F02 ladder is asserted.','No actual source-bound stage/count dataset or new independent design review.','RETAINED_UNQUALIFIED')],qualifiers=[
 'Domain owner supplies stage labels, count denominators, inclusion criteria and the actual active stage for one representative source-bound example.',
 'Prove partitions are disjoint/exhaustive where the domain claims them, reconcile available/missing counts, and do not synthesize a global total across overlapping stages.',
 'Preserve existing desktop/mobile source lineage and meaningful count drill-down/return.',
 'Admit independent review of the exact updated native/implementation revision; generic accepted/complete badges do not qualify the ladder.'
 ],retained=True)

role('LifecycleRail',[],[(S,'11.3 Closed-form criteria for the open consumer integration gap'),(I,'Component state applicability and specimen coverage')],['2E3-0','2IY-0'],[
 v('retained desktop/mobile lifecycle',[],'Existing canonical reference identity only; no new concrete F02 lifecycle is asserted.','No authorized domain transition, history or pending/uncertain state is newly evidenced.','RETAINED_UNQUALIFIED')],qualifiers=[
 'Domain owner supplies real transition names, current state, permitted next actions and a meaningful actual transition/return witness.',
 'Retain loops, terminal states, pending and uncertain transitions; do not remap lifecycle to a generic up/down scale.',
 'Bind source history and authority; a presentation choice cannot issue or complete a transition.',
 'Qualify exact desktop/mobile compositions and integration with independent review.'
 ],retained=True)

role('DecisionRow / VerdictHero',[],[(S,'11.3 Closed-form criteria for the open consumer integration gap'),(I,'Component state applicability and specimen coverage')],['28Y-0','2BR-0','2GM-0','2LB-0'],[
 v('retained decision/verdict desktop/mobile',[],'Existing canonical reference identities only; no new verdict example or approval is asserted.','No domain verdict, probability, confidence, trading command or authoritative action may be inferred from F02 styling.','RETAINED_UNQUALIFIED')],qualifiers=[
 'Domain owner supplies a real current verdict, its evidence/source lineage and exactly permitted next steps.',
 'Preserve distinction between evidence, domain judgment and authorized action; F02 does not create confidence/probability or trading commands.',
 'Retain compact/mobile order and the source/evidence/return path without hiding critical caveats.',
 'Review exact updated composition and exercised consumer path independently; preserved reference ID is not qualification.'
 ],retained=True)

assert len(roles)==21 and {x['role']for x in roles}==set(rows)
incomplete=[{'role':r['role'],'variant':v['variant'],'reason':v['still_unverified'],'evidence':v['evidence']} for r in roles for v in r['variants'] if v['status']=='CONTRACT_ONLY_OR_INCOMPLETE_VARIANT']
retained=[r['role'] for r in roles if r['role_status']=='RETAINED_UNQUALIFIED']
source_files=['SYSTEM_CONTRACT.md','SOURCE_AND_DATA_CONTRACT.md','INTERACTION_STATES.md','paper/ASSIGNMENT_COMPLETENESS_20261103.md','paper-retention-ledger.json','pattern-lab.html','fixtures/company-history.json','paper/role-evidence-source-receipts.json']
result={
 'schema':'f02.paper.role-evidence-input-map.v1','created_utc':datetime.now(timezone.utc).isoformat(),'system_version':'F02-SYSTEM/1.0.0-candidate.2','file_id':FILE,
 'scope':'Operational author-informed contract-to-input map. Local preparation and source consistency only; no Paper/browser writes or native admission by this map.',
 'evidence_boundary':'Prepared HTML/SVG inputs can become editable native evidence only after actual IDs, screenshots and exports are read back and reviewed. No runtime, F01 release, production implementation or formal RIG pass is inferred.',
 'source_files':[{'path':p,'sha256':sha(ROOT/p)}for p in source_files], 'input_packets':packets,
 'status_vocabulary':{'INPUT_SPECIMEN_PRESENT':'Concrete editable HTML/SVG construction input exists at the exact keys; native application/review is not asserted.','ANNOTATION_ONLY':'Behavior/source note exists; does not qualify a component variant.','CONTRACT_ONLY_OR_INCOMPLETE_VARIANT':'Specified behavior has no complete matching editable composition in this input set.','RETAINED_UNQUALIFIED':'Existing domain/source reference is intentionally retained; no new concrete F02 example or qualification claimed.'},
 'native_binding_contract':{'native_board_id':None,'native_step_ids':None,'instructions':['Parent binds actual returned IDs; never derive IDs from names or keys.','Read back final subtree/JSX, screenshots and measured geometry at the exact native checkpoint.','If a clone or corrective patch changes markup/geometry/data, retain its provenance and map the actual affected node IDs.','Prepared page IDs are source routing intent; readme may have moved. Bind actual native page membership from the final readback.','A screenshot, an HTML input, an annotation and executable integration are separate evidence classes.']},
 'summary':{'contract_roles':21,'roles_with_prepared_editable_examples':17,'retained_unqualified_roles':retained,'retained_role_count':len(retained),'important_contract_only_or_incomplete_variants':len(incomplete),'mandatory_roles_without_new_complete_editable_example':retained,'all_roles_native_qualified':False},
 'fault_composition_summary':{'requested_portable_variant_gaps_prepared':7,'board_key':'fault-compositions','groups':25,'extra_acceptance':'Matched stale + partial + owner-confirmed saved fixture preserves the same read snapshot and caveats.','original_core_packet_unchanged':True,'scope':'Prepared concrete design variants only; no new native, source-authority or runtime qualification.'},
 'roles':roles,'remaining_variant_limits':incomplete,
 'cross_cutting_evidence':[
 {'topic':'Four consumer density','refs':[e('macro-dark',*[f'sector-{i}' for i in range(1,11)]),e('company-dark','history-chart',*[f'statement-row-{i}' for i in range(1,10)]),e('options-dark',*[f'print-{i:02}' for i in range(1,13)]),e('editorial-dark','article-title','publication','calculation-caption','calculation-header','calculation-row-0','calculation-row-1','calculation-row-2','equations','limits-copy')],'limit':'Density and visible data values only, until native visual readback. Full consumer engines and other capabilities remain with their owners.'},
 {'topic':'Theme parity','refs':[e('foundations','semantic-0','semantic-1','semantic-2','semantic-3'),e('controls-variants','core-action-hierarchy-dark','core-action-hierarchy-light'),e('states-matrix',*[f'state-{i}'for i in range(16)])],'limit':'Clone/theme application, optical review, actual contrast measurements and forced colors require final native/browser evidence.'},
 {'topic':'Independent semantics','refs':[e('states-matrix','meaning-0','meaning-1','meaning-2'),e('options-full-row-evidence-320','limitation')],'limit':'Direction, estimated side, exposure and judgment are distinct. Language preference cannot establish market meaning.'},
 {'topic':'Width classes','refs':[e('options-full-row-evidence-320','dialog-header','entity','return-action'),e('macro-light-zh-390','title','metric','sector-3'),e('width-768-overlay','scene','overlay'),e('width-1024-overlay','scene','overlay'),e('macro-docked-1280','workspace','split','dock'),e('macro-dark','body','comparison-layout'),e('width-1600-docked','workspace','split','dock')],'limit':'320/390/768/1024/1280/1440/1600 construction inputs are not measured viewport, 400%-zoom, touch or keyboard tests; F01 joint freeze remains open.'},
 {'topic':'AC-06 chart fixture identity','refs':[e('grammar','chart-title','chart','exact-values'),e('macro-dark','history-unit','history-chart')],'limit':'Anatomy chart: gap 26 Oct, 50–80%. Macro consumer: gap 23 Oct, 40–80%. Keep separate names/source identities or explicitly align through a reviewed data change.'}
 ],
 'not_proved_by_native_design':['Live source correctness or schema/producer completeness','Real entitlement, protected-payload omission, account identity or billing offer validity','Mutation callback effects, idempotency, request reconciliation and confirmed readback','Semantic table/grid/dialog/ARIA behavior and assistive-technology support','Keyboard activation, focus trap/return after sort/filter, touch or horizontal scroll','400% zoom, viewport reflow, font/CJK loading or forced-color/reduced-motion behavior','Existing chart/DataInspector performance, virtualization, replay and export scope','F01 joint foundation release, complete consumer integration, admitted independent RIG review or production deployment'],
 'audit_references':{'map_gap':'paper/ASSIGNMENT_COMPLETENESS_20261103.md AC-02','other_open_gates':'AC-01 and AC-03 through AC-08 must be reconciled against final native checkpoint; this map closes no review gate by itself.'}
}
(HERE/'role-evidence-input-map.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')

def short_ref(ref):return '`'+ref['board_key']+'` / '+', '.join('`'+k+'`'for k in ref['step_keys'])
md=['# F02 role and variant evidence input map','',
 'This is an operational, author-informed map of **all 21 SYSTEM_CONTRACT roles** to exact prepared HTML/SVG board and step keys. It is not a native completion receipt. Actual Paper IDs are intentionally `null`; the parent writer must bind returned IDs, screenshots and exports at the final checkpoint. The JSON contains full anatomy, source links, predecessor IDs, variant references and qualifiers.','',
 '## Coverage and remaining limits','',
 '**17 roles have concrete editable input examples. Four remain retained and unqualified:** VirtualizedDataInspector, CountLadder, LifecycleRail, and DecisionRow / VerdictHero. No stage counts, lifecycle transitions or verdicts were fabricated. All 21 roles still need their applicable native, integration and review gates.','',
 'The portable supplement adds action hierarchy and pending treatment; collapsed/expanded/error disclosure examples at desktop and 320px; existing SVG icon anatomy; basis points and unknown source age; a resource-specific Options gate in both themes; and the complete first Options print inspector at 320px. A separate 25-group fault-compositions board closes all seven remaining portable design variants and adds the matched stale/partial/confirmed-saved case. These are concrete prepared inputs, not applied or reviewed native evidence.','',
 '| Role | Main prepared evidence | Important qualifications |','| --- | --- | --- |']
brief={
 'SectionHeader':('consumer question/title groups; fault-compositions/missing-period-headers','Missing-period header is explicit in both themes; retrieval cannot substitute for observation period.'),
 'MetricValue':('metrics/metric-trio; company-eps-overlay-320/value; company-dividend-overlay-320/value','Reported zero, absence and retained dated values are distinct.'),
 'ChangeValue':('metrics/metric-units + core-metric-bps; fault-compositions/withheld-comparisons','Definition/currency mismatches are concrete counterfactual inputs; the actual domain witness remains unqualified.'),
 'FreshnessReceipt':('metrics/source-receipt + core-metric-unknown-age; options-full-row-evidence-320/clocks','Retrieval does not replace source time; unknown-age example is a separate state fixture.'),
 'DataRow':('macro-{dark,light}/sector-1…10; company-{dark,light}/statement-row-1…9; options-{dark,light}/print-01…12','The JSON expands every key; row identity/focus behavior remains unverified.'),
 'TableFrame':('consumer frames; fault-compositions/empty-table-*, unavailable-table-* and retained-*','Three complete fault frames retain entity, filter, headers, source, count meaning and recovery; retained values match the Company fixture.'),
 'VirtualizedDataInspector':('grammar/virtualization — annotation only','Retained/unqualified; no new editable replacement.'),
 'ChartFrame':('consumer/grammar charts; fault-compositions/unavailable-chart-context + unavailable-chart-state','Unavailable series has an honest unknown scale/clock and no invented marks. Company full 85-value view remains a supporting HTML path.'),
 'Tabs':('controls/tabs + supplement-hover-row; fault-compositions/tabs-loading-panel + tabs-empty-panel','Matched context and selected Table panel distinguish pending/no count from completed/zero count.'),
 'EvidenceTrigger':('consumer row evidence; foundations/core-icon-evidence + core-icon-sizes','Accessible contextual names and real activation remain unverified.'),
 'EvidenceInspector':('Macro/Company/Options inspectors; fault-compositions/unavailable-inspector-*','Unavailable supporting citation detail preserves the exact Communication-services summary, identity, clocks and return target.'),
 'StatePanel':('states-matrix; metrics/core-metric-unknown-age; fault-compositions/not-yet-published-state + unquantified-coverage-state','Publication status and unknown denominator are now explicit context-bearing fixtures; neither is inferred from a failed request.'),
 'Callout':('company-*/statement-caveat; editorial-*/limits-*; options-full-row-evidence-320/limitation','Critical limitations remain visible outside disclosure.'),
 'DetailDisclosure':('controls-variants/core-disclosure-*','Desktop and 320px collapsed/expanded/error complete as inputs; no interaction test.'),
 'Action':('controls-variants/core-action-*; states-matrix/state-4,10,12,13','44px primary/secondary/quiet hierarchy and pending are concrete; owner effects unverified.'),
 'SaveFeedback':('states-matrix/state-10…13 + combined-*; fault-compositions/combined-confirmed-saved','Owner-confirmed fixture retains the same 66.7%, +1.13 pp, 7/8, source clock and read caveats; real readback remains unverified.'),
 'TierGate':('controls-variants/core-tier-denied-{dark,light}-*; core-tier-unavailable-{dark,light}*','Actual pinned Options tri-state policy; paid data is withheld on denied/unavailable. Offer validity is a later owner check.'),
 'Icon':('foundations/core-icon-*','Exact existing search/arrow_up/swirl paths; 24 viewBox, 1.8 stroke, currentColor; runtime accessibility unverified.'),
 'CountLadder':('Existing 2CM-0 / 2HH-0','Retained/unqualified; require source-bound stages, denominators and partition reconciliation.'),
 'LifecycleRail':('Existing 2E3-0 / 2IY-0','Retained/unqualified; require actual domain transition and return witness.'),
 'DecisionRow / VerdictHero':('Existing 28Y-0 / 2BR-0 / 2GM-0 / 2LB-0','Retained/unqualified; require actual verdict/evidence/allowed-next-step source lineage.')}
for r in roles:
 a,b=brief[r['role']];md.append('| '+r['role']+' | '+a+' | '+b+' |')
md+=['','## Exact supplement packet','',
 '`core-supplement-inputs.json` contains **9 append groups**: 6 for `foundations` and 3 for `metrics`; a separate **39-group `controls-variants` board** on `p-4-0` (compact header plus 38 variant groups); and the **12-group `options-full-row-evidence-320` board** on `p-5-0`. The original controls board receives only its separately prepared hover comparison. Existing source keys were preserved. Source and integration notes remain separate from product examples.','',
 'The Options inspector matches `optionRows[0]` / `evidenceRecord("options-0")` and the consumer `print-01` step. It contains EXM, 15:58:42 ET, 2026-11-20 expiry, Call, USD 120.00 strike, estimated Buy, USD 825,000 premium, 1,500 contracts, 21 calendar DTE, ITM, Sweep and the expanded fixture source identity. Observation date/window, publication and retrieval are separately labeled. Expiry is not used as the observation clock.','',
 'The resource-specific gate follows the pinned actual `/options` owner: `allowed` mounts the workspace; `denied` renders OptionsPaywall; `unavailable` renders OptionsServiceUnavailable. The source predicate checks `terminal_live_options` or the exact existing `unlimited` exception. The copied plan/trial wording is a pinned-source reference, not a current offer verification. The real existing onboarding callback and outage reload/chart actions are recorded; no new route or billing authority is introduced.','',
 '## Portable fault variants now prepared','',
 '`fault-composition-inputs.json` adds one 1440px, fit-content board on `p-4-0` in 25 meaningful groups. The original 60-group core packet remains byte-for-byte unchanged.','',
 '| Variant | Exact fault-compositions steps |','| --- | --- |',
 '| Missing-period header | `missing-period-headers` |',
 '| Withheld definition/currency comparisons | `withheld-comparisons` |',
 '| Empty / unavailable / retained-error tables | `empty-table-context`, `empty-table-state`, `unavailable-table-context`, `unavailable-table-state`, `retained-table-context`, `retained-operating-income`, `retained-pretax-income`, `retained-net-income`, `retained-table-error` |',
 '| Unavailable chart frame | `unavailable-chart-context`, `unavailable-chart-state` |',
 '| Busy versus empty active Table panel | `tabs-comparison`, `tabs-loading-panel`, `tabs-empty-panel` |',
 '| Unavailable entity-bound inspector | `unavailable-inspector-context`, `unavailable-inspector-summary`, `unavailable-inspector-source-error`, `unavailable-inspector-return` |',
 '| No publication / unquantified coverage | `not-yet-published-state`, `unquantified-coverage-state` |',
 '| Matched stale + partial + confirmed saved | `combined-confirmed-saved` |','',
 'All seven previously listed portable design gaps now have concrete prepared compositions. Definition/currency flags and publication/availability responses are explicitly counterfactual state inputs; the normal consumer fixture is unchanged. The retained financial rows and Macro summary use their exact existing values and identities. Real source authority, native review and runtime outcomes remain unqualified.','']
for x in incomplete:md.append('- **'+x['role']+' — '+x['variant']+':** '+x['reason'])
md+=['','## Qualification required for retained roles','']
for r in roles:
 if r['role_status']=='RETAINED_UNQUALIFIED':
  md += ['### '+r['role'],'']
  md += ['- '+q for q in r['required_qualifiers']]
  md.append('')
md+=['## Native binding and review','',
 'Bind each exact board/step key to the actual returned Paper node ID, including clone remaps and corrective patches. Read back the final subtree/JSX, capture the actual board and inspect editable text, data/mark correspondence, target geometry, overflow and light/dark consistency. Source input hashes are recorded so a later mismatch is explicit. Do not convert an annotation or a preserved predecessor ID into a passing native variant.','',
 'Keep the anatomy chart (26 Oct missing, 50–80%) distinct from the Macro consumer chart (23 Oct missing, 40–80%) unless a deliberate reviewed data change aligns them. The map records this AC-06 difference; it does not silently change either fixture.','',
 'Paper appearance cannot prove keyboard activation, semantic ARIA, focus trap/return, actual scroll, touch, zoom, CJK/browser rendering, real data, entitlement, save confirmation, existing virtualization, export/replay scope, F01 joint release or formal RIG. Those remain separate source-owner and review receipts.','',
 'Source basis: SYSTEM_CONTRACT §4; SOURCE_AND_DATA_CONTRACT §§4–5 and §11; INTERACTION_STATES; ASSIGNMENT_COMPLETENESS_20261103 AC-02/AC-06; pinned source links and input hashes in the JSON.','']
(HERE/'ROLE_EVIDENCE_INPUT_MAP.md').write_text('\n'.join(md))
print(json.dumps({'roles':len(roles),'prepared_role_examples':17,'retained_unqualified':retained,'contract_only_or_incomplete_variants':len(incomplete),'input_boards':len(registry),'files':['role-evidence-input-map.json','ROLE_EVIDENCE_INPUT_MAP.md']},indent=2))
