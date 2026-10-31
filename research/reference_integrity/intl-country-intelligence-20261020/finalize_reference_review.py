"""Record root adjudication after both actual critics clear the frozen repair artifact."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json,yaml
RIG=Path(__file__).resolve().parent
ARTIFACT='883a1e48efdf9c334c08665262efa0961b1997a0'
SOURCE='442042e591d255dd24b540ff240edb4c0410c297'
HTML='ad802caa6a04a7049d0adf8721354c88aa7dfec7378d5afc6bf161064f9767d0'
def read(name): return yaml.safe_load((RIG/name).read_text())
def write(name,data): (RIG/name).write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True,width=115))
freeze=json.loads((RIG/'first_pass_freeze.json').read_text())
assert freeze['artifact_sha']=='46f02fa355abbfaa4387203c0e3190db6747bed9' and not freeze['rationale_revealed']
raws={}
for short,role in [('product','product_regression'),('visual','visual_taste')]:
    raw=read('repair_pass_'+short+'.yml')
    assert raw['verdict']=='PASS', (role,raw.get('verdict'))
    assert raw['artifact']['commit']==ARTIFACT and raw['artifact']['source_commit']==SOURCE and raw['artifact']['html_sha256']==HTML
    original=read('first_pass_'+short+'.yml');second=read('second_pass_'+short+'.yml')
    binding=next(x for x in freeze['reviews'] if x['role']==role)
    assert sha256((RIG/('first_pass_'+short+'.yml')).read_bytes()).hexdigest()==binding['sha256']
    amendments=[]
    for row in second['amendments']:
        amendments.append({'finding':row.get('finding',row.get('id')),'action':row.get('action',row.get('disposition')),'note':row.get('note',row.get('reason'))})
    normalized={'schema':'mastermind.rig_review.v1','reference_id':'intl-country-intelligence-20261020','role':role,
      'reviewer':{'identity':binding['reviewer_identity'],'model':'GPT-6 Astra Pro','independent_of_author':True},
      'artifact_sha':ARTIFACT,'quarantine':{'rationale_received_after_first_pass':True},
      'first_pass':{'artifact_sha':freeze['artifact_sha'],'frozen_at':freeze['frozen_at'],'raw_path':'first_pass_'+short+'.yml','sha256':binding['sha256'],'verdict':original['verdict'],'findings':original['findings']},
      'second_pass':{'artifact_sha':freeze['artifact_sha'],'amended_at':second['amended_at'],'raw_path':'second_pass_'+short+'.yml','verdict':second.get('verdict',second.get('final_verdict')),'amendments':amendments},
      'repair_pass':{'artifact_sha':ARTIFACT,'raw_path':'repair_pass_'+short+'.yml','sha256':sha256((RIG/('repair_pass_'+short+'.yml')).read_bytes()).hexdigest(),'review':raw},
      'history_note':'Original blind and rationale passes concern their original artifact and remain unchanged. The separately authored repair pass reviews the final frozen bytes.'}
    (RIG/'reviews').mkdir(exist_ok=True);write('reviews/'+role+'.yml',normalized);raws[role]=normalized
now=datetime.now(timezone.utc).isoformat()
packet={
'materially_improved':'The first reading task now connects a named country thesis to published growth/inflation paths, national policy, fiscal/external conditions, dated market observations and conditions that could alter the view. The source repair makes five GDP calculations and seven equity states traceable to actual stored inputs. Visible mobile tools navigation, a reserved persistent assistant control, localized equity labels and corrected country/history navigation remove the independently observed regressions. All411 final browser checks pass with the actual production fonts and shared UI assets; independent product and visual critics inspected the final artifact.',
'materially_worsened':'task.scan-legacy-world remains WORSE: aggregate world boards and their detailed reference tables are placed behind the Data & tools disclosure, adding one action and lowering their default prominence. This cost is explicit and accepted under the user\'s direction that country understanding lead. The substantial expanded country page also remains long on narrow screens; detailed source inputs increase document weight.',
'disappeared':'No inventoried source capability is implicitly removed. Existing comparison, macro, risk, history, library, evidence, calculations and separate stock-research destinations retain their source contracts. Their access moves behind a visible tools entrance; query and legacy-fragment paths are exercised. Existing unavailable inputs and unlinked catalogue destinations remain qualified limitations, not newly functioning claims.',
'behavior_harder':'A user starting from the older aggregate boards opens Data & tools before scanning them. The main country navigation reduces the need to assemble an economic story across separate panels, but this is a product judgment, not a timed usability result. Long source disclosures require scrolling, while their raw inputs remain available for audit. The earlier clipped tools entry and floating assistant occlusion are repaired rather than accepted tradeoffs.',
'stronger_claims':'Country theses, official paths and conditional interpretation are stronger claims than a loose market dashboard. They are warranted only within their named providers, publication dates, information cutoffs, units and period conventions. Published history and forecasts are visually distinct. GDP calculations and equity windows now disclose actual inputs; EA19/EA21 geography and the broader-European equity proxy remain explicit. Unknown acquisition/revision custody is not upgraded by rendering, and unqualified FX plus missing TW/IN GDP remain unavailable.',
'intent_vs_convenience':'The user explicitly prioritized deep country economic and market interpretation over saved research, comparison and alerts as primary features. The chosen hierarchy implements that request while preserving the supporting tools and direct paths. It does not substitute implementation convenience for missing inputs: source validation, actual raw calculations, full-asset browser captures and independent re-review were completed after concrete failures.',
'production_preferable_for':'The incumbent source hierarchy is preferable for someone whose first task is scanning its aggregate boards or switching the old research views without an outer disclosure. The actually captured public baseline had failed workspace resources, so no claim is made that it operated normally or that its large text count is a valid functioning-product comparison. Authenticated behavior and separate destination pages remain outside this anonymous reference verdict.',
'strongest_argument_against':'The improved hierarchy could make incomplete evidence feel more comprehensive than it is. Seven qualified FX observations still require genuine production acquisition, Taiwan/India observed GDP coverage is incomplete, retained source vintages have explicit limits, and narrow expanded content remains long. The candidate addresses authority risk through visible dates, source/input disclosures, conditional language and refusal states; approval does not assert complete institutional coverage, investment accuracy, authenticated behavior, or production adoption.'}
findings=[]
for fid,note,evidence in [
('PRC-001','Canonical GDP and equity sources, stored observation dates and reproducible raw calculation inputs replace anonymous claims. Missing observations remain withheld.',['repair_pass_product.yml','source_principal/REVIEW.md','dock4_source_disclosure_browser.json']),
('PRC-002','The complete Data & tools entrance is visible and operable at320px and390px.',['repair_pass_product.yml','repair_dock4/review_counterexamples.json']),
('VTC-001','Responsive navigation exposes all four labels beside the reserved assistant slot.',['repair_pass_visual.yml','repair_dock4/review_counterexamples.json']),
('VTC-002','The existing assistant is available in persistent navigation and retains its original panel and focus owner.',['repair_pass_visual.yml','repair_dock4/review_counterexamples.json']),
('VTC-003','Every expanded and collapsed summary labels its state as Equity trend in both languages.',['repair_pass_visual.yml','repair_dock4/review_counterexamples.json']),
('VTC-004','The launcher occupies reserved opaque navigation space instead of covering country research; actual loaded-control post-close geometry is verified in all12 contexts.',['dock2_visual_provisional.yml','repair_pass_visual.yml','repair_dock4/review_counterexamples.json'])]:
    findings.append({'finding':fid,'resolution':'resolved_by_change','note':note,'evidence':evidence})
overrides=[{'finding':'task.scan-legacy-world','authority':'/root — project owner and reference design authority','justification':'Accept the explicitly WORSE initial aggregate-board scan: the user directs country interpretation to be the primary feature. Preserve the source content and direct fragments; expose the secondary entrance visibly at every supported width. This is a documented hierarchy tradeoff, not a waiver of the repaired mobile discoverability defect.'}]
conditions=[
{'id':'RELEASE-INTL-FX-CUSTODY','required_before':'claiming complete production acquisition and market acceptance','requirement':'Run the existing protected-main intl_prices backfill after normal source acceptance; inspect actual published canonical stores, genuine adapter capture receipts and their final renderer consumption. Retained copied stores and a green workflow alone are insufficient. Until then preserve unavailable qualified FX states.'},
{'id':'RELEASE-INTL-SERVED','required_before':'claiming the rebuild shipped and adopted','requirement':'Complete applicable exact-head hosted CI and normal merge, a covering International render, normal updater adoption, and actual served anonymous desktop/mobile language/theme/navigation/assistant checks with public assets and protected access boundaries. This reference approval does not establish those steps.'}]
verdict={'schema':'mastermind.rig_verdict.v1','reference_id':'intl-country-intelligence-20261020','authority':{'identity':'/root','role':'project owner and reference design authority'},'recorded_at':now,'artifact_sha':ARTIFACT,'source_commit':SOURCE,'html_sha256':HTML,'packet':packet,'blocking_findings':findings,'overrides':overrides,'conditions':conditions,'verdict':'APPROVE_WITH_CONDITIONS'}
write('verdict.yml',verdict)
approval={'schema':'mastermind.rig_approval.v1','reference_id':'intl-country-intelligence-20261020','approved_at':now,'artifact_sha':ARTIFACT,'verdict':'APPROVE_WITH_CONDITIONS','authority':'/root — project owner and reference design authority','author':'/root','reviewers':[x['reviewer']['identity'] for x in raws.values()],'overrides':overrides,'conditions':conditions,'scope':'Reference artifact approval only; production acceptance remains explicit.'}
write('approval.yml',approval)
manifest=read('manifest.yml');assert manifest['reference_files'][0]['frozen_sha']==ARTIFACT;manifest['status']='approved';manifest['files']['approval']='approval.yml';write('manifest.yml',manifest)
print(json.dumps({'artifact_sha':ARTIFACT,'approved_at':now,'verdict':verdict['verdict'],'reviewers':approval['reviewers'],'historical_findings_preserved':True,'production_release_claimed':False}))
