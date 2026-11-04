from pathlib import Path
import json,yaml
root=Path.cwd()
rig=root/'research/reference_integrity/intl-country-intelligence-20261020'
sha='46f02fa355abbfaa4387203c0e3190db6747bed9'
b=yaml.safe_load((rig/'baseline.yml').read_text())
n=yaml.safe_load((rig/'first_pass_capability_tasks.yml').read_text())
browser=json.loads((rig/'complete_browser_receipt.json').read_text())
capmap={c['id']:c for c in n['capabilities']}
dispositions=[]
for cap in b['capabilities']:
    cid=cap['id']; dest=capmap[cid]['proposal_destination']
    row={'id':cid}
    if cid.startswith(('navigation.','stocks.')):
        row.update(disposition='RETAIN',target=dest)
    elif cid in ['macro.growth-inflation','macro.policy-observations']:
        row.update(disposition='IMPROVE',target='Primary country assessment observations and policy section; '+dest,
            rationale='Country assessments now carry dated growth/inflation observations and a separately sourced national policy decision. The original tool remains available with its own qualification boundary.')
    else:
        row.update(disposition='RELOCATE',destination=dest,
            reachability='Data & tools in the page navigation opens #intl-analysis-tools. Existing ?view= contexts open that disclosure, and existing section fragments open their containing disclosures. '+capmap[cid]['proposal_source']+'; complete_browser_receipt.json records view and legacy-fragment navigation. Source-only or currently unavailable data states remain described in baseline.yml.')
    dispositions.append(row)
tasks=[]
for task in n['primary_country_tasks']:
    tasks.append({'id':'task.'+task['id'],'task':task['task'],'critical':True,
        'production':'Source destinations: '+ '; '.join(task['production_locations'])+'. Actual anonymous baseline has failed workspace resources and its data qualifications remain as captured.',
        'proposal':'Source destinations: '+'; '.join(task['proposal_locations'])+'. '+task['proposal_source'],
        'verdict':'BETTER' if task['id'] not in ['country.evidence-state','country.navigation-context'] else 'BETTER',
        'notes':'Comparative assessment based on direct artifacts and source. No timed user study or investment performance claim. Existing unavailable qualified FX and legacy observations are not converted to current evidence.'})
tasks.extend([
    {'id':'task.supporting-tools','task':'Open a supporting research view, preserve its context and follow an old section link.','critical':True,
     'production':'Workspace view controls are initially prominent, but captured public JS/CSS failures prevent their normal operation.',
     'proposal':'One Data & tools entry precedes the same view controls; ?view= and existing fragment links reveal the requested content.',
     'verdict':'BETTER','notes':'Actual complete_browser_receipt.json covers six query views, six activated views and four legacy fragments on desktop and mobile. Compared with a functioning source design, general browsing adds one disclosure action; direct links retain immediate access.'},
    {'id':'task.scan-legacy-world','task':'Scan existing global-regime, market-turn and full reference-table observations.','critical':True,
     'production':'These source sections appear below the original workspace in an initially open legacy disclosure.',
     'proposal':'The same source sections are inside Data & tools, with the legacy disclosure initially open within it.',
     'verdict':'WORSE','notes':'Discoverability of the old aggregate boards is reduced by one outer disclosure and their lower placement. Root design authority must explicitly adjudicate this primary-hierarchy tradeoff; source and deep links remain available.'},
    {'id':'task.language-theme-mobile','task':'Read the main assessment and supporting controls in English/Chinese, light/dark, desktop/mobile.','critical':True,
     'production':'Shared controls exist, with actual public resource failures recorded separately.',
     'proposal':'Both languages and themes at1440/390/320; mobile supporting views use the existing compact selector.',
     'verdict':'BETTER','notes':'Actual complete browser receipt:46/46 cases, no page exceptions or document overflow. No authenticated-tier claim.'},
    {'id':'task.separate-stock-research','task':'Open the existing country and International stock research destinations.','critical':False,
     'production':'Shared navigation and separate route links.',
     'proposal':'The shared navigation and separate route links remain, with additional country research links in primary cards.',
     'verdict':'EQUIVALENT','notes':'Source identity is retained. Separate destination-page bodies are outside this reference capture.'}
])
proposal={
 'schema':'mastermind.rig_proposal.v1','reference_id':b['reference_id'],
 'proposed_artifact':{'frozen_sha':sha,'paths':[str((rig/'proposed/intl.html').relative_to(root)),str((rig/'proposed').relative_to(root)),
   'templates/intl.html.j2','templates/intl_country_cockpit.html.j2','templates/intl_country_cockpit.css','templates/intl_country_cockpit.js'],
   'screenshots':[{'path':r['path'],'viewport':r['viewport'],'theme':r['theme'],'locale':r['locale']} for r in browser['states'] if 'viewport' in r]},
 'dispositions':dispositions,
 'additions':[
  {'id':'country.analysis','description':'Seven country assessments join current observations, policy decisions, fiscal/external context and market interpretation.'},
  {'id':'country.official-projections','description':'Published historical points and official growth/inflation projections have distinct chart treatments, period conventions and source dates.'},
  {'id':'country.conditional-paths','description':'Stronger/weaker paths describe conditions to examine; they are not predicted asset-return scenarios.'},
  {'id':'country.global-connections','description':'Demand, energy-price and financing channels link to relevant country assessments; no measured causal coefficient is claimed.'}
 ],
 'user_tasks':tasks,
 'authority_delta':[
  {'id':'auth.official-outlook','production_claim':'Mostly current/recomputed macro and market observations.','proposal_claim':'An official provider projects country and world growth/inflation over stated periods.','direction':'stronger','warranted':True,'evidence':'config/intl_country_baseline.json archived release records; lib/intl_country_inputs.py admission and custody; templates/intl_country_cockpit.html.j2 period labels and history/projection separation.'},
  {'id':'auth.country-thesis','production_claim':'Fragmented regime labels and observations.','proposal_claim':'A short interpretation joins a national primary-source assessment with separately dated market observations.','direction':'stronger','warranted':True,'evidence':'Country thesis source and date are visible; country policy narrative retains national decision and independent monthly policy cross-check. Source/interpretation disclosures are in the frozen rendered artifact.'},
  {'id':'auth.conditional-watch','production_claim':'Risk/regime observations and manually entered scenario arithmetic.','proposal_claim':'Named conditions could strengthen or weaken the economic path; channels are not causal estimates.','direction':'stronger','warranted':True,'evidence':'What changes the view uses conditional language; Global connections says Channels to examine, not causal estimates. No probability, expected return or recommendation is produced.'},
  {'id':'auth.market-freshness','production_claim':'Qualified workspace observations or unavailable states.','proposal_claim':'Market-state description uses dated equity windows; FX requires source-qualified observations and otherwise shows unavailable.','direction':'equal','warranted':True,'evidence':'Actual production-input render has Observation unavailable for unqualified copied FX. Copy receipts explicitly do not acquire source evidence; producer acquisition and served acceptance remain release obligations.'},
  {'id':'auth.legacy','production_claim':'Existing tools and composites retain their own source qualifications.','proposal_claim':'The same tool claims behind a disclosure.','direction':'equal','warranted':True,'evidence':'Retained workspace template/controller source identities; complete build and task receipt, with unavailable macro/history/chart states kept explicit.'}
 ],
 'information_economics':{
   'words_per_card':{'production':'No comparable primary country-assessment card exists in captured production. The actual broken-resource desktop page exposes13,888 whitespace-separated visible tokens over many panels; this is not a normal functioning before-card measure.',
    'proposal':'Default desktop page exposes782 English whitespace-separated visible tokens including shared chrome, one expanded country, six collapsed country rows and connection cards. Chinese whitespace counts are not comparable word measures. Complete browser receipt supplies exact states.'},
   'findings':['One expanded country provides a consistent sequence from thesis to path, policy, balances, market conditions and evidence.',
     'Older aggregate boards and research panels require the Data & tools disclosure; this raises browsing effort for a user starting with those panels.',
     'The default is still a substantive long assessment on mobile. Collapsed country rows and charts compress navigation and published paths; no claim of universally faster task completion is made.',
     'The production before image has failed resource delivery. Do not advertise a percentage compression gain as an apples-to-apples comparison with a functioning old workspace.'],
   'preserved':['Existing charts, source tables, calculators and evidence ledgers remain in their source hierarchy under the outer disclosure.','Published history and projection use distinct line treatments and a visible legend.','Country summaries expose thesis, growth path and market state before expansion.']}
}
manifest=yaml.safe_load((rig/'manifest.yml').read_text())
manifest['status']='in_review'
manifest['reference_files']=[{'path':str((rig/'proposed/intl.html').relative_to(root)),'frozen_sha':sha}]
(rig/'manifest.yml').write_text(yaml.safe_dump(manifest,sort_keys=False,allow_unicode=True))
(rig/'proposal.yml').write_text(yaml.safe_dump(proposal,sort_keys=False,allow_unicode=True,width=110))
print(json.dumps({'reference_id':b['reference_id'],'frozen_sha':sha,'dispositions':len(dispositions),'user_tasks':len(tasks),'status':'in_review'}))
