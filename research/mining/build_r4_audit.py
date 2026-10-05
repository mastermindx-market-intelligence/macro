"""Curated historical AUDIT, not a collector, complete universe or blinded sample."""
from pathlib import Path
import json
from resources_catalyst_r4_cohort import screen_observation, audit_summary, milestone_at_horizon, settlement_value
ROOT=Path(__file__).resolve().parent
SOURCES=[]
def source(key,day,title,url,note,read='indexed_primary_text'):
    SOURCES.append(dict(id=key,publication_date=day,title=title,url=url,
                        inspection=read,note=note,observed_on='2026-09-27',
                        raw_archive_sha256=None,global_first_publication_proven=False,
                        product_source_admission=False))
source('PG_BUILD','2019-08-07','Pure Gold construction finance and board decision','https://www.globenewswire.com/news-release/2019/08/07/1898192/0/en/pure-gold-secures-us-90-million-construction-finance-package-and-announces-construction-decision-for-madsen-red-lake-mine.html','Board approved construction; target first gold by end2020. Named mine used existing infrastructure; not a new greenfield-only observation.')
source('PG_COMMERCIAL','2021-08-03','PureGold commercial declaration','https://www.globenewswire.com/news-release/2021/08/03/2273468/0/en/PureGold-Declares-Commercial-Production.html','Issuer declared commercial production effective1Aug2021. This is not a cash-flow or return result.','parsed_primary_text')
source('PG_SUSPEND','2022-10-24','PureGold financial and operations update','https://www.globenewswire.com/news-release/2022/10/24/2539775/0/en/PureGold-Provides-Financial-and-Operations-Update.html','Immediate suspension; C$2m cash, C$13m net working-capital deficit excluding current Sprott debt; expected warrant exercises absent; no consistent positive site cash flow.','parsed_primary_text')
source('PG_CCAA','2022-10-31','PureGold obtains CCAA protection','https://www.globenewswire.com/news-release/2022/10/31/2545028/0/en/PureGold-Obtains-CCAA-Protection.html','Court-protection order is a distinct milestone, not proof of equity extinguishment or recovery amount.')
source('COTE_BUILD','2020-07-21','IAMGOLD proceeds with Cote construction','https://www.iamgold.com/English/investors/news-releases/news-releases-details/2020/IAMGOLD-to-Proceed-with-Construction-of-the-Ct-Gold-Project-in-Ontario-Canada/default.aspx','70/30 joint venture; expected commercial production H2 2023. Whole company already had operating assets.')
source('COTE_DECLARE','2024-08-02','IAMGOLD commercial declaration','https://www.iamgold.com/English/investors/news-releases/news-releases-details/2024/IAMGOLD-Announces-Commercial-Production-at-Ct-Gold/default.aspx','Declaration2Aug; threshold30consecutive days averaging60% of36,000tpd. Reaching commercial threshold does not establish sustained nameplate.')
source('COTE_Q2','2024-08-08','IAMGOLD Q2 results','https://www.iamgold.com/English/investors/news-releases/news-releases-details/2024/IAMGOLD-Reports-Second-Quarter-2024-Results/default.aspx','Reports operating commercial2Aug and JV-contract effective1Sep; 70% assets/liabilities versus60.3% revenues/costs before repurchase. Do not use one ownership percentage everywhere.')
source('COTE_Q3','2024-11-07','IAMGOLD Q3 results','https://www.iamgold.com/English/investors/news-releases/news-releases-details/2024/IAMGOLD-Reports-Third-Quarter-2024-Results/default.aspx','Later report calls operating commercial1Aug while retaining2Aug announcement and1Sep contractual trigger. Date assertions require adjudication, not latest-wins.','parsed_primary_text')
source('GOOSE_FINANCE','2022-02-08','Sabina financing package','https://www.globenewswire.com/fr/news-release/2022/02/08/2380519/0/en/Sabina-Gold-Silver-Announces-Comprehensive-US-520-Million-Financing-Package-for-Goose-Mine-at-Back-River.html','US$520m package; additional third-party equity and bridge repayment were conditions before funding. Financing proposal is a landmark, not proof of cash available.')
source('GOOSE_BUILD','2022-09-07','Sabina formal Goose construction decision','https://www.globenewswire.com/news-release/2022/09/07/2511381/0/en/sabina-gold-silver-makes-formal-construction-decision-for-the-goose-gold-mine.html','Formal build decision after early logistics; first production Q1 2025. Keep this native target wording, not commercial production.')
source('SABINA_EXCHANGE','2023-04-19','B2Gold completes Sabina acquisition','https://www.globenewswire.com/news-release/2023/04/19/2649875/0/en/B2Gold-Completes-Acquisition-of-Sabina-Gold-Silver-Corp.html','Completed0.3867 B2Gold common shares per Sabina share. Expected delisting date is not an observed exchange delisting receipt.','parsed_primary_text')
source('GOOSE_FIRST','2025-06-30','B2Gold first gold at Goose','https://www.b2gold.com/news-media/news-releases/news-details/2025/B2Gold-Pours-First-Gold-at-the-Goose-Mine/default.aspx','First gold30Jun2025 after first ore24Jun. Current corporate page boilerplate is not historical portfolio evidence.')
source('VAL_BUILD','2022-09-01','Marathon Valentine construction decision','https://www.globenewswire.com/news-release/2022/09/01/2508380/0/en/Marathon-Makes-Construction-Decision-for-the-Valentine-Gold-Project-and-Provides-Project-Development-Update.html','StartQ42022/majorwork2023; first gold early2025. Early2025 is deliberately not coerced to Q1.','parsed_primary_text')
source('PREMIER_FINANCE','2020-12-10','Ascot Premier construction finance','https://www.globenewswire.com/news-release/2020/12/10/2143158/0/en/Ascot-Secures-US-105-Million-Construction-Finance-Package-for-Premier-Gold-Project.html','Closed finance package has staged funding; part refinances notes. Brownfield restart, not a greenfield-only project.')
source('PREMIER_REFINANCE','2022-12-12','Ascot proposed replacement construction financing','https://www.globenewswire.com/news-release/2022/12/12/2571628/0/en/Ascot-Arranges-C-200-Million-Financing-Package-for-Construction-of-the-Premier-Gold-Project.html','Non-binding financing proposal. Same project as2020; do not count two independent investments.')
source('PREMIER_FIRST','2024-04-22','Ascot first gold during commissioning','https://www.globenewswire.com/news-release/2024/04/22/2866729/0/en/Ascot-Pours-First-Gold-During-Commissioning-at-the-Premier-Gold-Project.html','First pour20Apr2024; commissioning continues; commercial targetQ3 remains a forecast.')
source('PREMIER_SUSPEND','2024-09-06','Ascot suspension for mine development','https://www.globenewswire.com/news-release/2024/09/06/2942028/0/en/Ascot-Announces-Care-Maintenance-of-Operations-in-Order-to-Focus-on-Mine-Development-Activities.html','Near/design mill rates did not supply enough developed stopes and ore feed. C$15m cash supports suspension/compliance, not a confirmed restart budget.')
source('EAGLE_FINANCE','2018-03-08','Victoria Gold financing and continuation','https://www.globenewswire.com/news-release/2018/03/08/1418183/0/en/victoria-gold-announces-comprehensive-c-500-million-financing-package-for-eagle-and-continuation-of-construction-activities.html','Explicit continuation of construction. Financing belongs in a separate landmark; first construction within2018 is not established.')
source('GREENSTONE_BUILD','2021-10-27','Equinox groundbreaking full-scale construction','https://www.prnewswire.com/news-releases/equinox-gold-announces-groundbreaking-for-full-scale-construction-of-greenstone-mine-in-ontario-canada-301409519.html','60/40 JV announcement; separate quarterly footnote retains formal-decision conditions.')
source('GREENSTONE_CONDITION','2021-11-03','Equinox Q3 conditional decision qualification','https://www.newswire.ca/news-releases/equinox-gold-reports-third-quarter-2021-financial-and-operating-results-855547952.html','Formal construction decision subject to lender consent and Orion financing. This later qualification is not silently backdated to27Oct.','parsed_primary_text')
source('MAGINO_BUILD','2020-10-14','Argonaut approves Magino build','https://www.globenewswire.com/news-release/2020/10/14/2108722/0/en/Argonaut-Gold-Approves-Magino-Project-Construction-Receives-Fixed-Bid-Pricing-Proposal-Announces-US-50-Million-Bought-Deal-Financing-of-Senior-Unsecured-Convertible-Debentures-and-.html','Board approval; target first goldH12023. Funding includes assumed operating-mine cash generation and conditional asset sale, not cash alone.')
source('BLACKWATER_FINANCE','2022-02-24','Artemis credit-approved commitment letter','https://www.artemisgoldinc.com/news/artemis-gold-executes-credit-approved-commitment-letter-for-385-million-project-debt-financing-to-develop-blackwater','Credit-approved letter is financing progress, not an observed loan draw.')
source('BLACKWATER_EARLY','2022-09-29','Artemis site earthworks','https://www.artemisgoldinc.com/news/media-releases/2022/artemis-announces-commencement-of-blackwater-plant-site-earthworks','Site preparation can commence while major construction still requires Mines Act permits. Dated body says TSXV; current page header says TSX. Use the dated source span.','parsed_primary_text')
source('YAQUI_BUILD','2020-07-28','Alamos La Yaqui Grande construction decision','https://alamosgold.com/news-and-events/news/news-details/2020/Alamos-Gold-Announces-Construction-Decision-on-High-Return-La-Yaqui-Grande-Project-with-After-Tax-IRR-of-41/default.aspx','Satellite/replacement operation within Mulatos. Listed issuer is already producing; retain a different financial perimeter.')
source('SUGAR_PRIOR','2019-04-02','Harte Gold year-end2018 results','https://www.globenewswire.com/news-release/2019/04/02/1794802/0/en/Harte-Gold-Reports-Year-End-2018-Results.html','Earthworks beganSep2017 and mill erectionDec2017. This prior-works control does not exclude separate2018 financing landmarks or prove the date of formal FID.','parsed_primary_text')
source('TZ_FINANCE','2022-07-18','G Mining Tocantinzinho funding','https://www.accesswire.com/708863/G-Mining-Ventures-Announces-US481-million-Financing-Package-for-Tocantinzinho-Gold-Project','Reuses R1/R2 financing source and R3 capital uncertainty; not a newly qualified technical report.')

# Snapshot evidence, not a successful historical roster download.
source('FRAME_NRCAN',None,'NRCan major projects inventory methodology','https://natural-resources.canada.ca/science-data/data-analysis/major-energy-natural-resources-projects-inventory','Indexed description: Canadian-located projects over stated cost thresholds; not a global Toronto-listed population. Direct page403 was not bypassed.','indexed_description_direct_open_403')
source('FRAME_NRCAN_HISTORY',None,'NRCan historical project inventory changes','https://natural-resources.canada.ca/science-data/data-analysis/natural-resources-major-projects-planned-under-construction-2024-2034','Indexed descriptions distinguish additions, completed and inactive removals across annual snapshots. A current inventory omits relevant old entrants. Direct inventory403 not rerouted.','indexed_primary_description')
source('FRAME_TMX',None,'TMX current statistics and archive navigation','https://www.tsx.com/en/listings/current-market-statistics','Historical issuer rosters are a required input, not obtained by reading a latest statistics page. Direct page403 stopped; no complete listing census.','indexed_description_direct_open_403')

OBS=[]
def obs(key,p,issuer,day,kind,source,venue='TSX',prior=None,lo=None,hi=None):
    OBS.append(dict(observation_key=key,project_key=p,issuer_key=issuer,claim_key=issuer+'_entry_common',
                    source_ref=source,known_on=day,effective_lower=lo or day,effective_upper=hi or day,
                    listing_venue=venue,primary_product='gold',stage_kind=kind,prior_stage_entry=prior))
obs('pg_build','madsen','puregold','2019-08-07','BUILD_APPROVED','PG_BUILD','TSXV')
obs('cote_build','cote','iamgold','2020-07-21','BUILD_APPROVED','COTE_BUILD')
obs('goose_finance','goose','sabina','2022-02-08','FINANCING_ATTEMPT','GOOSE_FINANCE')
obs('goose_build','goose','sabina','2022-09-07','BUILD_APPROVED','GOOSE_BUILD')
obs('val_build','valentine','marathon','2022-09-01','BUILD_APPROVED','VAL_BUILD')
obs('premier_finance','premier','ascot','2020-12-10','FINANCING_ATTEMPT','PREMIER_FINANCE')
obs('premier_refinance','premier','ascot','2022-12-12','FINANCING_ATTEMPT','PREMIER_REFINANCE',prior=True)
obs('eagle_finance','eagle','victoria','2018-03-08','FINANCING_ATTEMPT','EAGLE_FINANCE','TSXV',True)
# Use the later condition-bearing disclosure date; do not backdate its information.
obs('greenstone_condition','greenstone','equinox','2021-11-03','BUILD_CONDITIONAL','GREENSTONE_CONDITION',lo='2021-10-27',hi='2021-10-27')
obs('magino_build','magino','argonaut','2020-10-14','BUILD_APPROVED','MAGINO_BUILD')
obs('blackwater_finance','blackwater','artemis','2022-02-24','FINANCING_ATTEMPT','BLACKWATER_FINANCE','TSXV')
obs('blackwater_early','blackwater','artemis','2022-09-29','EARLY_WORKS','BLACKWATER_EARLY','TSXV')
obs('yaqui_build','la_yaqui_grande','alamos','2020-07-28','BUILD_APPROVED','YAQUI_BUILD')
obs('sugar_prior','sugar_zone','harte','2019-04-02','CONTINUED_CONSTRUCTION','SUGAR_PRIOR',prior=True,lo='2017-09-01',hi='2017-09-30')
obs('tz_finance','tocantinzinho','gmining','2022-07-18','FINANCING_ATTEMPT','TZ_FINANCE','TSXV')
LABELS=[]
def ev(key,p,target,lo,known,src,hi=None):
    LABELS.append(dict(id=key,project_key=p,target=target,kind='attained_first',lower=lo,upper=hi or lo,
                       known_on=known,recorded_on='2026-09-27',source_ref=src))
ev('pg_commercial','madsen','issuer_commercial','2021-08-01','2021-08-03','PG_COMMERCIAL')
ev('pg_suspension','madsen','operating_suspension','2022-10-24','2022-10-24','PG_SUSPEND')
ev('pg_ccaa','madsen','court_protection','2022-10-31','2022-10-31','PG_CCAA')
ev('goose_first','goose','first_gold','2025-06-30','2025-06-30','GOOSE_FIRST')
ev('premier_first','premier','first_gold','2024-04-20','2024-04-22','PREMIER_FIRST')
ev('premier_suspend','premier','operating_suspension','2024-09-06','2024-09-06','PREMIER_SUSPEND')
ev('cote_announcement','cote','public_commercial_declaration','2024-08-02','2024-08-02','COTE_DECLARE')
ev('cote_operating_q2','cote','operating_commercial','2024-08-02','2024-08-08','COTE_Q2')
ev('cote_operating_q3','cote','operating_commercial','2024-08-01','2024-11-07','COTE_Q3')
# The August Q2 report specifies a future contractual effective date; not an attained-first fact then.
# Its later Q3 repetition can support retrospective effective-date labeling without future-fact leakage.
ev('cote_contract','cote','joint_venture_commercial','2024-09-01','2024-11-07','COTE_Q3')

def label(p,target,start,months=24,cut='2026-09-27',mode='public_reconstruction'):
    return milestone_at_horizon([r for r in LABELS if r['project_key']==p],target,start,months,cut,project_key=p,mode=mode)

analysis={
 'puregold_24m':label('madsen','issuer_commercial','2019-08-07'),
 'puregold_24m_as_known_then':label('madsen','issuer_commercial','2019-08-07',cut='2021-08-07'),
 'puregold_24m_system_possession':label('madsen','issuer_commercial','2019-08-07',cut='2021-08-07',mode='system_replay'),
 'goose_first_gold_24m_build':label('goose','first_gold','2022-09-07'),
 'premier_first_gold_24m_original_finance':label('premier','first_gold','2020-12-10'),
 'premier_first_gold_24m_refinance':label('premier','first_gold','2022-12-12'),
 'cote_operating_date_conflict':label('cote','operating_commercial','2020-07-21'),
 'cote_declared':label('cote','public_commercial_declaration','2020-07-21'),
 'cote_contract':label('cote','joint_venture_commercial','2020-07-21'),
}
metadata={
 'sampling_design':'RETROSPECTIVE_PURPOSEFUL_AUDIT',
 'scope':'Proposed TSX/TSXV gold-development disclosure window2018-2022; global project locations.',
 'identifiers':'All keys in this fixture are human research labels; NO canonical issuer/security/asset/event IDs have been minted or bound.',
 'first_incident_search_coverage':'UNQUALIFIED',
 'historical_listing_roster_complete':False,'researcher_outcome_blind':False,
 'population_success_rate':None,'fitted_probability':None,'expected_return':None,
 'raw_sources_archived':False,'production_admission':False,
 'native_Paper_applied':False,
 'date_basis':'Calendar disclosure dates. No exchange first-known timestamp or historical system-possession proof.',
 'primary_model_horizons_months':[12,24],
 'Cote_conflict':'Conflicting operating-date assertions remain CONFLICT even though both fall after the24month deadline. Public declaration and contractual trigger retain separate target identities.',
}
objects={
 'R4_SOURCE_MANIFEST.json':dict(metadata=metadata,sources=SOURCES),
 'R4_ENROLLMENT_AUDIT.json':dict(metadata=metadata,observations=OBS,
                               dispositions={r['observation_key']:screen_observation(r) for r in OBS},summary=audit_summary(OBS)),
 'R4_TARGET_AND_CLAIM_LABELS.json':dict(metadata=metadata,events=LABELS,worked_labels=analysis,
    original_windows=[dict(project='goose',source_ref='GOOSE_BUILD',wording='first production Q1 2025',
                           normalized_start='2025-01-01',normalized_end='2025-03-31',
                           target_alias_to_first_gold='REQUIRES_REVIEW_NOT_AUTOMATIC_COMMERCIAL_LABEL'),
                      dict(project='cote',source_ref='COTE_BUILD',wording='commercial production H2 2023',
                           normalized_start='2023-07-01',normalized_end='2023-12-31',
                           precise_operating_definition_match='UNQUALIFIED'),
                      dict(project='valentine',source_ref='VAL_BUILD',wording='first gold early2025',
                           normalized_start=None,normalized_end=None,reason='do_not_coerce_early_to_Q1')],
    claims=[dict(project='goose',original_claim='sabina_entry_common',status='SHARE_SETTLEMENT_REPORTED',
                 settlement_effective='2023-04-19',known_on='2023-04-19',recorded_on='2026-09-27',
                 source_ref='SABINA_EXCHANGE',successor_name='B2Gold common',shares_per_old_share='0.3867',
                 native_corporate_action_id=None,actual_wealth=None,
                 illustrative_successor_price='10',illustrative_currency='CAD',
                 illustrative_gross_value=settlement_value('0.3867','10','0','CAD','CAD'),
                 actual_market_observation=False,entry_price=None,return_value=None),
            dict(project='madsen',original_claim='puregold_entry_common',status='COURT_PROTECTION_REPORTED',
                 source_ref='PG_CCAA',legal_extinction=None,recovery_amount=None,return_value=None),
            dict(project='premier',original_claim='ascot_entry_common',status='OPERATIONAL_SUSPENSION_REPORTED',
                 source_ref='PREMIER_SUSPEND',legal_extinction=None,recovery_amount=None,return_value=None)]),
}
for path,payload in objects.items():
    (ROOT/path).write_text(json.dumps(payload,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
print(json.dumps(objects['R4_ENROLLMENT_AUDIT.json']['summary'],indent=2))
print({k:v['state'] for k,v in analysis.items()})
