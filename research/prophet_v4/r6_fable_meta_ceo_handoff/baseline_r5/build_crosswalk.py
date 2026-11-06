"""Compile design-only catalogs. No network, product imports, or runtime writes."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent

def dump(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')

# These are proposal/document IDs, not a new decision authority or runtime registry.
decisions = []
def d(i, title, owner, evidence, decision, shortcut, consumers):
    decisions.append(dict(id=i,title=title,status='OPEN_OWNER_DECISION',owner=owner,
                         required_evidence=evidence,required_output=decision,
                         forbidden_shortcut=shortcut,blocked_consumers=consumers,
                         creates_authority=False))
d('D01','Source-session validity and revocation','Incumbent confluence and B4 policy/adapter owners, #7581',
  'Current exact adapter and producer heads; actual emission/scheduling contract; accepted session and basis facts; next-session, late-emission, expiry, retraction and shortened-session cases.',
  'Accepted source/observed/valid-for/expiry/revocation semantics, or proof of genuine current-session qualified production. Return to existing #7581 finding5789777976 without duplicating review.',
  'Relabeling prior data as today, removing equality without a replacement validity rule, or translating compact UNKNOWN into FAIL.', ['B05','B12','B15','B19'])
d('D02','Independent expert anchors and episode admission','B1/Stock Identity/TOI and relevant existing expert owners',
  'Owner-native nomination and structural anchor; causal observation clock; exact identity and re-arm semantics; rejected-source/key examples; comparison with known killed species.',
  'Versioned accepted source adapter and anchor contract with immutable episode lineage, suppression reasons and no changed historical IDs.',
  'Ticker/date surrogate episodes, future extrema, silent retries of immutable source keys, or parallel lifecycle store.', ['B02','B10','B12','B14','B17'])
d('D03','Real source histories and rights','Existing Data OS, Earnings/FIF, GMI, quote and source licensing owners',
  'Exact usable dates, field semantics, vintage/correction lineage, coverage by original universe, delistings, publication/processing rights and source costs; data-independent domain criteria.',
  'Signed-off source-readiness matrix and branch-specific admissible data classes. Industrial capital goods is a Cycle readiness candidate, not a return-selected winning domain.',
  'Current membership/event set backdated, guessed statutory availability lags, broad industry series relabeled granular subthemes, or assumed licenses.', ['B04','B08','B09','B16','B18'])
d('D04','Distinct strategy, entry and holding versions','Existing Prophet strategy/B4/plan owners and program acceptance',
  'Frozen economic job, supported instruments, eligibility, horizons by role, exact owner facts, entry windows, invalidation and hold/review rules; unchanged legacy control.',
  'Accepted sleeve definitions and separate policy versions; new 1D/4H entry and ER/CC management cannot be inferred from the EL control.',
  'Changing labels under the singleton definition, horizon-as-hold inference, confluence waiver in an adapter or retroactive strategy relabeling.', ['B05','B12','B13','B15','B19'])
d('D05','Durable user decision/thesis mapping','Existing WatchStore, feedback, plan and Portfolio owners',
  'Actual supported write/read APIs and schema ownership; account/list/episode/security bindings; local/cloud distinction; retries, corrected generations, readback and independent portfolio checks.',
  'Owner-compatible versioned mappings for Watch, Pass/reason, thesis/milestone and held-position links. Unsupported actions visibly remain unavailable until their owner exists.',
  'A new Prophet personal store, turning a watch into a position, local-only notes advertised as cloud saved or unverified optimistic success.', ['B07','B13','B17','B19','B21','B24'])
d('D06','Economic margins, endpoints and formal-read law','Existing Evaluation/QLedger with strategy and risk acceptance owners',
  'User economic loss/coverage budget independent of held-out results; declared primary endpoint and cost assumptions; permitted pilot variability/dependence analysis; all comparisons/horizons/peeks counted.',
  'Finite registered analysis with numerical minimum worthwhile gain/non-inferiority/coverage margins, uncertainty method, effective-information floor and read schedule before outcomes. Existing7751 remains separately controlled.',
  'Nonsignificant harm presented as safety, 300rows treated as sufficient power, favorable horizon selection, duplicate cells credited as independent or unrestricted threshold search.', ['B06','B10','B11','B12','B15','B18','B19'])
d('D07','Source and model-vintage eligibility','Existing source and model/research owners',
  'Data release/observed/correction dates; model training and selection vintage where knowable; held-out partition and retrieval/extraction semantics.',
  'Observed-as-run, point-in-time replay or retrospective designation for each study, with a prospective remedy when historical model knowledge cannot be established.',
  'Date-filtered retrieval treated as proof modern model weights contain no future knowledge; masking alone treated as certification.', ['B04','B08','B10','B11','B15','B18'])
d('D08','Fill, costs, latency and capacity assumptions','Existing quote/basis/B4/Evaluation owners; Portfolio/Risk for capacity',
  'Executable side or approved cost floor, first usable decision time, session/bar anchoring, limit-order evidence, halt/delisting treatment and measured/floor/unknown status.',
  'Versioned fill/cost contract and sensitivity tests; no capacity claim until actual position/liquidity assumptions are evaluated.',
  'Same-bar known-close fill, touch-equals-fill, twice-charged spread, missing quote treated as zero cost or a stop assumed guaranteed.', ['B05','B06','B12','B15','B19','B24'])
d('D09','Visual architecture and user comprehension','Existing design-system/product owners and independent design reviewer',
  'Current shared components, design tokens and route inventory; dark/light EN/ZH1440/390 examples; empty/invalidated/degraded/uncertain states and user tasks.',
  'Accepted visual packet and task-based comprehension criteria, including experimental versus live authority and new-entry versus held-position distinctions.',
  'A third header/token family, CSS skin swap counted as both art directions, or attractive mocks treated as production proof.', ['B07','B14','B17','B20','B25'])
d('D10','Exact source custody, worker admission and independence','Existing Executive Capacity/Runtime, source writer, routing and review owners',
  'Current operation/Attempt state, writer leases and effect uncertainty; original review carrier; eligible capability and budget; exact immutable packet.',
  'One admitted source-authoritative operation per unit, least-scarce capable route, qualified independent reviewer and durable return path.',
  'A plan mistaken for dispatch, replacing a STARTed/unknown effect, Fable default placement or raw provider-spawn fallback.', ['B00','B01','B02','B03','B04','B05','B06','B20','B25','B26'])
d('D11','Release, telemetry and safe rollback','Existing release/publication/auth/monitoring owners',
  'Current production-path artifacts, entitlement and account matrix, actual ordinary refresh, version-compatible last-good state and user-action preservation.',
  'Accepted staged-release/rollback packet with declared freshness and field performance budgets; current quote-state reevaluation after any rollback.',
  'Serving a stale green entry card from last-good cache, destructive user-store resets, or CI green treated as acceptance.', ['B21','B22','B23','B25','B26','B28'])
d('D12','Final US capability and claim boundary','Chairman/program acceptance with product/research/risk owners',
  'All advertised US persona tasks, three initial sleeve dispositions, independent scientific/mechanical/product evidence, actual limitations and remaining scope.',
  'Explicit accepted launch claims and ongoing obligations. Failed research is rejected honestly; further sleeves/regions require their own accepted work and do not disappear silently.',
  'A research prototype called a complete flagship, fabricated positive evidence, copying US coefficients to other markets or hiding a promised missing capability.', ['B25','B27','B28'])
dump('DECISION_REGISTER.json', {'document_kind':'PROPOSED_OWNER_DECISION_CROSSWALK_NOT_AUTHORITY_REGISTRY','count':len(decisions),'decisions':decisions})

# Last-verified navigation. R5 did not re-read each PR; no current status claims.
carriers=[]
def c(n,role,round_,status,head,obligation,consumers,comments=None):
    carriers.append(dict(repository='mastermindx-market-intelligence/macro',number=n,role=role,
      status_basis=f'Last verified in {round_}; not re-censused in R5',last_verified_status=status,
      last_verified_head=head,current_head_and_runtime_state='NOT_RECHECKED_R5',
      remaining_obligation=obligation,build_consumers=consumers,existing_finding_comments=comments or [],
      action_law='Refresh exact head, custody, original reviewer and effects before acting. Preserve original carrier.'))
c(7180,'Completed-session and exact source-bound publication','R2','OPEN_DRAFT','a991d4d22a933ca8953a08260352cc4b30e2ee8d',
 'Body qualification cited an older head; new head needs exact review/composition/proof. Ordinary served-path refresh remains distinct.', ['B01','B03','B06','B23'])
c(7572,'Searchable lossless candidate field','R3','OPEN_DRAFT','5e43db462b5ffa4912874c0be32549f8e26baeda',
 'Retain private payload, source digest and honest unscored rows. Do not apply older-head test claims to newer head; do not equate board-pool identity with B1.', ['B03','B07','B20'])
c(7581,'Sole B4 runtime source adapter','R3','OPEN_DRAFT','39ef2cd48e091d90f12771aab142c2197022aa79',
 'Resolve source-session validity question, complete native owner facts and exact non-author review. No new review child or confluence waiver.', ['B05','B07','B12'],[5789777976])
c(7584,'Price-basis provenance','R2','OPEN_DRAFT','87f85e88f75bf037e4f917ee30313444f766bb62',
 'Accepted original review and downstream real-source proof required; numeric similarity alone is not provenance.', ['B05','B08','B23'])
c(7734,'NBBO/current-session-open measurement substrate','R2','OPEN_DRAFT','55e8671317af3219785e7a14e490028a9933daa4',
 'Measured facts only; no calibrated policy or capacity authority. Exact review and owner-compatible integration required.', ['B05','B06','B23'])
c(7738,'B4 fillability/gap initial policy facts','R1 source checkpoint','DRAFT_CONTROL_SHADOW','b143e7000b6afa003a15a7f934f4aaf099968d42',
 'Operation constants remain uncalibrated. Do not promote from configuration or source merge alone.', ['B05','B06','B12'])
c(7751,'Prospective B4 calibration preregistration','R1','MERGED_REGISTRATION_ONLY','01de8a7d36a8ce2e09242c167ca5869d1db34a20',
 'Merge ad48105910163e5709c75f28c0ae0edefa8eca57. Eight labels/six unique configurations finding remains; explicit alias or lawful amendment. No outcome read or capture-state claim.', ['B06','B12'],[5787579945])
c(7455,'Closed-session subtheme leadership','R3','OPEN_DRAFT','fdd731f18a7634c57cdc83fc80cbe13811ec745e',
 'Last described scope Semiconductors; current-membership/non-PIT and basis limits. No all-US historical predictive claim.', ['B09','B10','B20'])
c(7508,'Theme leadership/entry-context source','Phase2','EXISTING_CARRIER_STATUS_NOT_RECHECKED',None,
 'Preserve Theme Intelligence boundary and refresh actual payload/authority before consumption.', ['B04','B09','B20'])
c(7604,'Emerging-subtheme funnel measurement','Phase2','DRAFT_ZERO_AUTHORITY',None,
 'Consume source coverage/funnel diagnostics; not a live stock-rank or entry gate.', ['B09','B10','B22'])
c(7218,'Measurement/model-research correction dossier','Phase2','RESEARCH_HOLD',None,
 'PIT rank/sector and full-funnel research correction, no live-model approval.', ['B06','B10','B11','B15','B18'])
c(7294,'Stage earnings source restore','Phase2','MERGED_SOURCE_REPAIR',None,
 'Do not redo source fix. Natural run and historical correction/PIT limits must remain distinguished.', ['B04','B08'])
c(7295,'Bottom Ledger clock repair','Phase2','MERGED_SOURCE_REPAIR',None,
 'Do not redo source fix. Natural accrual/product governor proof remains a separate obligation unless later accepted.', ['B06','B22'])
dump('CARRIER_MAP.json',{'document_kind':'HISTORICAL_EVIDENCE_NAVIGATION_NOT_RUNTIME_STATE','r5_snapshot':'c9978765aa0085eba0213430284cb4b41065d4e2','count':len(carriers),'carriers':carriers})

# Requirements are the full deliverable map, not a second live backlog.
requirements=[]
def req(i,title,section,builds,qs,ds):
    requirements.append(dict(id=i,title=title,master_plan_sections=section,build_units=builds,
                             research_packets=qs,decision_dependencies=ds,status='PROPOSED_REQUIREMENT'))
req('R01','Complete early field including suppressions and displaced rows',['2','7'],['B02','B03','B07'],['Q02','Q03'],['D02'])
req('R02','Canonical identity, episode generation, correction and re-arm',['4','5','7'],['B02','B04','B06'],['Q01','Q03'],['D02'])
req('R03','Actual source/observed/decision/publication clocks',['5'],['B01','B05','B06','B23'],['Q01','Q15'],['D01','D07'])
req('R04','Coverage, rights and usable historical vintages',['6'],['B04','B08','B09','B16'],['Q01','Q06','Q07','Q14'],['D03','D07'])
req('R05','Clear qualitative intelligence and counterevidence',['6','9'],['B04','B08','B17'],['Q06','Q08','Q14','Q20'],['D03','D07'])
req('R06','Early Leadership, real independent peer support',['8.1'],['B09','B10','B11','B12'],['Q03','Q04','Q05'],['D02','D04'])
req('R07','Earnings issuer economics and matched expectation revisions',['8.2'],['B08','B14','B15'],['Q06'],['D03','D04'])
req('R08','Cycle economic turn, survival and original-share capture',['8.3'],['B16','B17','B18','B19'],['Q07','Q08','Q17'],['D03','D04'])
req('R09','Additional sleeves and instruments retained explicitly',['8.4','25'],['B27','B28'],['Q23'],['D12'])
req('R10','Origin and current-landmark predictions remain distinct',['9','10'],['B06','B11','B13','B15','B19'],['Q09','Q16','Q17'],['D06','D07'])
req('R11','Multi-head forecasts, strong transparent and ambitious challengers',['10'],['B10','B11','B15','B18'],['Q09','Q10','Q20'],['D06','D07'])
req('R12','Context conditioning and graph research without double-counting',['9','10'],['B04','B09','B11'],['Q05','Q12','Q13','Q14'],['D03','D06'])
req('R13','Calibration, missingness and selective prediction',['10','12'],['B11','B15','B18','B22'],['Q11','Q12'],['D06'])
req('R14','B4 deterministic current entry with no model waiver',['11'],['B05','B07','B12','B15','B19'],['Q04','Q15','Q18'],['D01','D04','D08'])
req('R15','Realistic fills, quote basis, sessions, latency and costs',['11','12'],['B05','B06','B12'],['Q15','Q18'],['D01','D08'])
req('R16','Explicit tactical, earnings and core/add holding laws',['11'],['B13','B15','B19'],['Q16','Q17'],['D04','D05'])
req('R17','Same-origin full-opportunity comparisons and original controls',['12'],['B06','B10','B12','B15','B18'],['Q02','Q04','Q15'],['D06','D08'])
req('R18','Failure-inclusive labels and honest path metrics',['12'],['B06','B18','B22'],['Q01','Q02','Q08','Q09'],['D03','D06'])
req('R19','Dependence, temporal leakage, multiplicity and power',['12'],['B06','B10','B11','B15','B18'],['Q01','Q09','Q10','Q11','Q20'],['D06','D07'])
req('R20','Action Desk and Early Radar user tasks',['14'],['B03','B07','B20'],['Q19','Q24'],['D09'])
req('R21','All Candidates and Theme/Propagation tasks',['14'],['B03','B04','B09','B20'],['Q03','Q05','Q13','Q24'],['D09'])
req('R22','Track Record and Health/Receipts tasks',['14'],['B22','B23','B20'],['Q02','Q22','Q24'],['D11'])
req('R23','Two art directions, EN/ZH, mobile/desktop and accessibility',['15'],['B07','B14','B17','B20','B25'],['Q24'],['D09'])
req('R24','Watch, thesis, plan and positions have truthful persistence',['16'],['B07','B13','B19','B21','B24'],['Q19'],['D05'])
req('R25','Meaningful alerts with current revalidation and correction',['16'],['B21','B23'],['Q19','Q22'],['D01','D05','D11'])
req('R26','Portfolio context, correlated exposure and no duplicate holdings',['16'],['B24'],['Q21'],['D05','D08'])
req('R27','Field performance, reliability, cost and latency budgets',['17'],['B23','B26'],['Q15','Q22','Q24'],['D11'])
req('R28','Post-launch drift, learning and safe versioned rollback',['18','23'],['B22','B23','B26'],['Q22'],['D11'])
req('R29','Onboarding, useful comprehension and truthful commercial claims',['19'],['B20','B25','B28'],['Q24'],['D09','D12'])
req('R30','Concrete 24-packet scientific program and rejected hypotheses',['3','13'],['B00','B06','B27'],['Q01','Q23'],['D06','D12'])
req('R31','Bounded build slices and exact existing carriers',['20'],['B00','B01','B02','B03','B04','B05'],[],['D10'])
req('R32','Astra principal research, justified Fable and least-scarce fabric',['21'],['B00','B25'],[],['D10'])
req('R33','Independent exact-head review and real entitled browser proof',['22'],['B25','B26'],['Q24'],['D09','D10','D11'])
req('R34','Legacy episodes, grades, strategies and positions preserved',['23'],['B06','B13','B19','B22','B26'],['Q01','Q02'],['D04','D05','D11'])
req('R35','Declared economic/statistical gates before outcome selection',['12','24'],['B06','B10','B11','B15','B18'],['Q09','Q10','Q11','Q18'],['D06'])
req('R36','Complete US first, market-native later adaptation',['2','25','26'],['B27','B28'],['Q23','Q24'],['D12'])
dump('REQUIREMENT_CROSSWALK.json',{'document_kind':'DESIGN_REQUIREMENT_TRACEABILITY','count':len(requirements),'requirements':requirements})

# Preserve all inherited case text. IDs are namespaced only to avoid collisions.
case_map3={'EL0':'B00','EL1':'B03','EL2':'B04','EL3':'B07','EL4':'B06','EL5':'B11','EL6':'B12','EL7':'B13','EL8':'B26'}
case_map4={'S0':'B00','S1':'B08','S2':'B04','ER1':'B08','ER2':'B14','ER3':'B15','ER4':'B15','CC1':'B16','CC2':'B17','CC3':'B18','CC4':'B19','JOIN':'B26'}
cases=[]
for prefix,mapping in [('R3',case_map3),('R4',case_map4)]:
    original=json.loads((ROOT/'inputs'/f'{prefix}_ACCEPTANCE_CASES.json').read_text())['cases']
    for x in original:
        cases.append(dict(id=prefix+':'+x['id'],origin=prefix,original_case=x,
             build_units=[mapping[x['slice']]],execution_status='NOT_EXECUTED',production_proven=False))

def a(i,title,setup,expected,units,reqs):
    cases.append(dict(id='R5:'+i,origin='R5',title=title,setup=setup,required_behavior=expected,
                      build_units=units,requirements=reqs,execution_status='NOT_EXECUTED',production_proven=False))
a('A01','No hidden candidate deletion','A source-qualified nomination is cap-displaced or lacks a B1 anchor.', 'Original source count, suppression and searchable observation remain; no surrogate episode or fabricated score.', ['B02','B03'],['R01','R02'])
a('A02','No surrogate identity','Two securities share an issuer or a ticker alias changes.', 'Resolve exact security/epoch and B1 generation, not string equality or a newly synthesized ticker-date key.', ['B02','B04'],['R02'])
a('A03','Corrected same-date source','Payload changes without a new market date.', 'Coherent generation changes reach preview/private hydration; prior decision is preserved.', ['B01','B03','B23'],['R03','R34'])
a('A04','Prior-session validity','Yesterday qualified technical source meets current RTH quote.', 'Accepted explicit validity/expiry law or honest refusal, never relabeled source date.', ['B05'],['R03','R14'])
a('A05','Expired or retracted validity','Previously valid entry facts expire or retract while UI remains open.', 'Current action becomes unavailable with clear reason; old decision is retained as history.', ['B05','B21','B23'],['R14','R25'])
a('A06','Historical event omissions','Current manifest lacks an old event previously in the universe.', 'Historical study refuses full-event-population claim until owner history is qualified.', ['B08','B06'],['R04','R07'])
a('A07','Model vintage leakage','Modern model is run on old documents with unknowable training chronology.', 'Extraction versus prediction class and retrospective status are explicit; no PIT forecasting certification from prompt dates.', ['B04','B11'],['R04','R19'])
a('A08','Optional intelligence missing','Options/estimates/transcript unavailable for a supported name.', 'Base research remains useful with named missingness; mandatory entry fact absence still blocks action.', ['B04','B11'],['R05','R13'])
a('A09','Source rights to prose','Unlicensed consensus present in a worker or server-side context.', 'No prohibited value leaks through anonymous JSON, generated narration or cached account responses.', ['B04','B08','B25'],['R04','R29'])
a('A10','Self-generated group strength','One member drives an otherwise flat group.', 'Peer-excluding-member control is distinct, with actual weights and no independent evidence double-credit.', ['B09','B10'],['R06','R12'])
a('A11','Historical member leakage','Today-known baskets omit failed historical constituents.', 'PIT membership or explicit non-PIT limitation; no promotional historical inference on biased frame.', ['B09','B18'],['R04','R08'])
a('A12','Source granularity mismatch','Electronics aggregate is presented as memory-subtheme observation.', 'Claim remains at real aggregate scope; unavailable granularity is disclosed.', ['B09','B16'],['R04','R08'])
a('A13','False consensus revision','Contributor exits while remaining estimates are unchanged.', 'Aggregate change and matched revision reported separately; matched absence is unknown.', ['B08','B15'],['R07'])
a('A14','Period and accounting mismatch','GAAP versus adjusted estimates or different fiscal dates are compared.', 'No beat/miss unless exact comparable owner semantics established.', ['B08','B15'],['R07'])
a('A15','Funding precedes recovery','Debt maturity falls before modeled recovery despite simple runway.', 'Dated obligations reveal funding limit; scenario assumptions cannot be described as committed facilities.', ['B17','B18'],['R08'])
a('A16','Old equity canceled','Business recovers after old shares canceled and new equity issued.', 'Old security terminal value is preserved; no performance splice into replacement equity.', ['B17','B18','B22'],['R08','R18'])
a('A17','Original and current predictions','Later favorable evidence appears on an existing episode.', 'New landmark observation; original ranking/forecast remains immutable and visible.', ['B06','B11','B22'],['R10','R34'])
a('A18','Rank is not probability','Rank relevance rises to a high value without calibration.', 'UI labels rank/priority only; no win probability or return target invented.', ['B11','B20'],['R11','R13'])
a('A19','Selected-cohort calibration','Pooled model calibrated but displayed top-K poorly calibrated.', 'Top-K/sleeve/horizon failure appears in qualification; no pooled-only confidence claim.', ['B11','B15','B22'],['R13'])
a('A20','Implicit confluence waiver','Earlier 1D/4H observation is used with unchanged EL control.', 'No entry bypass; separate accepted early-entry policy and study are required.', ['B05','B12'],['R14'])
a('A21','Missed confirmation denominator','Only eventual confirmers are retained in early-entry evaluation.', 'Evaluator rejects selected population and preserves all original opportunities.', ['B06','B10','B12'],['R17'])
a('A22','Price-row/session mismatch','Missing daily bars shift a positional horizon.', 'Expected session endpoint and actual coverage differ visibly; no silent H10-session label.', ['B06','B22'],['R15','R18'])
a('A23','Unknown path versus cash','Unpriced episode and known no-entry policy share a report.', 'Unpriced remains unknown; only valid no-entry follows declared cash accounting.', ['B06','B22'],['R17','R18'])
a('A24','Ambiguous barrier order','Same OHLC bar crosses both target and invalidation.', 'Order unresolved without actual finer evidence; conservative sensitivity is labeled assumption.', ['B06','B12'],['R15','R18'])
a('A25','Entry MAE versus giveback','Path rallies then falls sharply while above entry.', 'Entry adverse excursion, peak drawdown and realized capture remain distinct metrics.', ['B06','B13','B22'],['R16','R18'])
a('A26','Row-count leakage','Thousands of rows/date are split with a small sample gap.', 'Whole dates/episodes and outcome intervals define split; immature labels do not train.', ['B06','B11'],['R19'])
a('A27','Duplicate policies and repeated instants','Identical configurations and many ticks inflate apparent sample count.', 'Explicit semantic aliases and dependence; no new independent episode or test credit.', ['B06'],['R19','R35'])
a('A28','No-harm fallacy','Wide interval includes zero and material downside.', 'Declared non-inferiority bound fails or remains inconclusive; absence of significance does not pass.', ['B11','B15','B18'],['R35'])
a('A29','Mature stock new-entry refusal','Held position remains valid but a new entry would chase.', 'New-entry and held-position actions differ correctly; no automatic exit from RAN.', ['B13','B19','B20'],['R16','R20'])
a('A30','Retroactive strategy change','Losing tactical position is retitled Cycle Capture.', 'Original strategy persists; any new thesis is explicit and cannot rewrite its old outcome.', ['B13','B19','B24'],['R16','R34'])
a('A31','Focus-safe update','User reviews a row as rank generation updates.', 'Selection/focus preserved; update offered; material invalidation still visible without stale action.', ['B20','B21'],['R20','R23'])
a('A32','Art directions and language','1440/390 EN/ZH dark/light with long labels and degraded data.', 'Separate materials, readable contrast, keyboard use, no overflow, same semantic action/authority.', ['B20','B25'],['R23'])
a('A33','Truthful Watch save','Save to nondefault list with network ambiguity.', 'Owner readback/list scope; no invented success or retry on uncertain write; portfolio unchanged.', ['B07','B21','B24'],['R24'])
a('A34','Thesis persistence claim','Local notes exist but cloud episode action is unsupported.', 'UI states actual durability; unsupported cloud thesis not offered until owner extension accepted.', ['B13','B19','B21'],['R24'])
a('A35','Alert provenance and stale delivery','Duplicate trigger, revoked evidence or stale queued alert.', 'Existing dedupe/revocation/current validity prevents false fresh action; original delivery record preserved.', ['B21','B23'],['R25'])
a('A36','Correlated duplicate exposure','Three sleeves identify one security and overlapping groups.', 'One actual position lineage; opportunity views are not separate capital/independent trials.', ['B24'],['R26'])
a('A37','No feasible portfolio claim from averages','Candidate mean improves while liquidity/capital constraints untested.', 'Only appropriate episode/policy metrics claimed; portfolio/capacity remains unproven.', ['B24','B22'],['R26'])
a('A38','Performance and entitlement','Cold/warm loads, busy updates and account entitlement variants.', 'Measured mobile/desktop field budgets and actual private-path response behavior; no protected cross-account cache leak.', ['B23','B25'],['R27','R29'])
a('A39','Rollback stale green','New head withdrawn while old snapshot carried ENTRY_OPEN.', 'Current B4 reevaluation or unavailable action; no stale permission restored from cache.', ['B23','B26'],['R28','R34'])
a('A40','Source review independence','Old check belongs to another head or builder supplies own review.', 'Exact-head evidence and genuine independent gate; preserve existing review operation and custody.', ['B00','B25'],['R31','R32','R33'])
a('A41','Negative scientific result','Research packet fails or has inadequate power.', 'Record rejected/inconclusive result without threshold shopping; protect useful unaffected product work and honest claims.', ['B10','B15','B18','B27'],['R30','R35','R36'])
a('A42','Full US ordinary-path acceptance','Three initial advertised sleeves and later roadmap evaluated at release.', 'Every advertised persona task and ordinary refresh proved, unresolved claims visible, regions deferred until accepted US boundary.', ['B25','B26','B27','B28'],['R33','R36'])
dump('ACCEPTANCE_CATALOG.json', {'document_kind':'REQUIRED_ACCEPTANCE_CASE_CROSSWALK_NOT_TEST_REPORT',
 'counts':{'R3_inherited':36,'R4_inherited':48,'R5_added':42,'entries':len(cases)},
 'independence_note':'Entries may overlap semantically. This is not independent test N or a statistical sample.',
 'all_execution_status':'NOT_EXECUTED','cases':cases})

sources=[{'id':x['id'],'kind':'prior_dossier','locator':x['file'],'sha256':x['sha256'],
          'depth':'Exact local input hash verified; synthesis uses recorded source evidence and its original access limits.'}
         for x in json.loads((ROOT/'INPUT_MANIFEST.json').read_text())]
for i,loc,depth in [
 ('I01','https://github.com/mastermindx-market-intelligence/macro/issues/6805#issuecomment-5790671385','Final cumulative R4 checkpoint read fresh; navigation/evidence, not live action authority.'),
 ('I02','Mastermind@89582a372aa2a57ec500868ce6d79cd156219445/docs/sol_skills/','Protected branch and same-pin INDEX/ACTIVE_EXECUTION/WEB_CEO_DELEGATION/CLOSEOUT read.'),
 ('I03','macro@c9978765aa0085eba0213430284cb4b41065d4e2/AGENTS.md','Lines1–180 read; source reported blobba426238eb93faf478d05e66c5b4168fcc1a74d3. Not full local write boot.'),
 ('I04','Mastermind@89582a372aa2a57ec500868ce6d79cd156219445/docs/EXECUTIVE_WORKER_ROUTING_CHAIRMAN_ADDENDUM.md','Lines1–310 read. Planning roles and economic boundaries, no live activation.'),
 ('X01','https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html','Official docs; ranking grouping/relevance semantics, no model fitted.'),
 ('X02','https://proceedings.mlr.press/v70/guo17a.html','Primary publisher abstract, calibration motivation, no financial replication.'),
 ('X03','https://www.nber.org/papers/w20592','Primary abstract, multiplicity rationale, no new universal numerical promotion bar.'),
 ('X04','https://www.sec.gov/search-filings/edgar-application-programming-interfaces','Official API documentation, not a licensed consensus dataset.'),
 ('X05','https://fred.stlouisfed.org/docs/api/fred/realtime_period.html','Official vintage semantics, no data collection.'),
 ('X06','https://www.w3.org/WAI/WCAG21/Understanding/status-messages','Official explanation; no conformance test performed.'),
 ('X07','https://web.dev/articles/vitals','Official field/lab thresholds, not current Prophet measurements.'),
 ('X08','https://proceedings.mlr.press/v97/geifman19a.html','Primary publisher abstract risk/coverage; not financial validation.'),
 ('X09','https://www.census.gov/manufacturing/m3/historical/timeseries.html','Official source scope and revision notes; no granular corporate mapping assumed.')]:
    sources.append(dict(id=i,kind='public_primary' if i.startswith('X') else 'canonical_internal',locator=loc,depth=depth))
dump('SOURCE_REGISTER.json',{'sources':sources,'reading_limit':'R5 refreshed official references and prior source-bound dossiers. No market empirical study was replicated and no data subscription/entitlement is inferred.'})

# Matrix for executable branch-local gates. Do not serialize every scientific lane behind live B4.
dump('ACTIVATION_GATES.json', {'document_kind':'PROPOSED_BRANCH_GATES_NOT_RUNTIME_ADMISSION', 'gates':[
 {'id':'G01','unit':'B06','branch':'admissible historical analysis','requires_builds':['B00','B01','B02'],'requires_decisions':['D03','D06','D07','D08'], 'note':'Does not require live B4 to be complete; must satisfy source and scientific registration gates.'},
 {'id':'G02','unit':'B06','branch':'prospective B4 policy-cell capture','requires_builds':['B05'],'requires_decisions':['D01','D04','D06','D08'],'note':'All exact existing #7751 prerequisites remain; no historic backfill or duplicate outcome store.'},
 {'id':'G03','unit':'B11','branch':'live rank promotion','requires_builds':['B10'],'requires_decisions':['D06','D07','D11'],'note':'Research model existence is not live ranking authority.'},
 {'id':'G04','unit':'B12','branch':'new early-entry permission','requires_builds':['B05','B06'],'requires_decisions':['D02','D04','D06','D08'],'note':'Incumbent strategy confluence is not waived by adapter/UI.'},
 {'id':'G05','unit':'B15','branch':'earnings model/policy promotion','requires_builds':['B08','B14','B06'],'requires_decisions':['D03','D04','D06','D07','D08'],'note':'Absent estimates can hold revision branch without freezing qualified issuer-evidence research.'},
 {'id':'G06','unit':'B19','branch':'core/add recommendations','requires_builds':['B17','B18','B05'],'requires_decisions':['D03','D04','D05','D06','D08'],'note':'Scenario dossier is not proven survival/recovery probability or allocation authority.'},
 {'id':'G07','unit':'B26','branch':'flagship public claims/cutover','requires_builds':['B25'],'requires_decisions':['D09','D10','D11','D12'],'note':'Actual release and normal refresh proof; stale green is never fallback.'}
]})

# Mark every catalog as proposal; no accepted live authority exists in this packet.
dump('PROPOSAL_STATUS.json',{'schema':'research_document_status.v1','document':'Prophet US R5 integrated master plan',
 'status':'PROPOSED_FOR_REVIEW_AND_STAGED_ADOPTION','registered_trial':False,'source_committed':False,
 'source_changes':False,'workers_dispatched':False,'production_proven':False,'mission_complete':False,
 'authority':{k:False for k in ['can_rank','can_admit','can_set_entry_open','can_originate_plan','can_size','can_execute','can_trade','can_promote_model','can_promote_policy']},
 'parent':'macro#6805','working_checkpoint_comment':5791272310,
 'procedure_pin':'89582a372aa2a57ec500868ce6d79cd156219445',
 'macro_planning_snapshot':'c9978765aa0085eba0213430284cb4b41065d4e2',
 'next_action':'Source-publication/adversarial review of this packet under current custody; bind first ready existing-carrier unit, not another global audit.',
 'intended_resume':'Fresh Extra High interaction for review/publication/admission; hard research packets may use separately admitted Pro.',
 'note':'Mode is a task-fit recommendation. Comment writes are observed; source edit/merge/deployment/fabric action classes are not proven by that observation.'})
print(f'Wrote {len(decisions)} decisions, {len(carriers)} carriers, {len(requirements)} requirements and {len(cases)} required cases.')
