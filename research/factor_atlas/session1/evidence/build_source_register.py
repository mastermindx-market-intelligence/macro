"""Retain compact citations and inspection bounds; no source store or runtime registry."""
import json
from pathlib import Path
R=Path(__file__).resolve().parent
macro='cdbcd143dcfa419ab0637bc11dd4c80368143e2e'
terminal='bacda5dcc30682f9327e037a2d4425bd9714ac3a'
mastermind='732cf7be88e7159b4995a8885fbd381cd1484e3e'
rows=[
('M01','engine/baskets.py','53981a43bc134ecb12cda8e05218f08166c38260','lines 1–200; _ew_level and _ret; targeted source read'),
('M02','engine/group_flow.py','af0d5f671edded697c03a827976d207bb2b7e7a3','lines 1–170; targeted source read'),
('M03','engine/subsector_rotation.py','adb9a8077d94868ad8758a03cbfbbe95f4705169','lines 1–180; targeted source read'),
('M04','engine/factor_series.py','03eb5aae0f1fe3c5fcb1f5984a01165bbfd6943b','lines 1–180; targeted source read'),
('M05','engine/equity_factors.py','74a5dbb280b7060d86c9e8ed6cd58e0df950e4a2','lines 1–200 plus selected function/asof/shares matches; not whole-module execution'),
('M06','engine/factor_seasonality.py','972329b31fc6745acdd205c4a851b26f7b52801d','lines 1–210; targeted source read'),
('M07','engine/price_ladder.py','12b4d54e071fd2ca288e5ea4837851d6bdf71e34','lines 1–252 via overlapping reads; basis and same-read receipt code'),
('M08','engine/basket_membership_pit.py','5c7ba201d505648365ba40ff88c6901b47aef713','lines 1–190, 404–448, 974–1102 and function/clock matches; not complete module review'),
('M09','lib/dataos/identity.py','ea8485596e57fd1e686bfdb9d75708a3a3845fda','selected identity/alias/known_at/resolve API matches; no durable identity-store census'),
('M10','lib/dataos/price.py','be127fa853a6aafbf0bcb33b58783316ac972faa','first 125 lines and basis vocabulary'),
('M11','lib/closes_panel.py','f36b47e9d10590c3d750cbce7f5646f504794b64','subtree metadata and incumbent reference; not full source read or native test'),
('M12','data/baskets/membership.json','c5b838d59fad8115d40cd369410846e9aaf5ec11','selected-field JSON read and direct basket/slot/ticker-string counts'),
('M13','data/baskets/snapshots/_cadence.json',None,'complete small JSON read; blob not retained; not live collector verification'),
('M14','config/theme_crosswalk.yml','5796e3e5cf16839c7dbca2bf6d74737b35b547fc','lines 1–155; counts in header are owner declarations, not a full row recount'),
('M15','research/theme_graph/THEME_FABRIC_COMPLETION_RESEARCH_2026-10-07.md',None,'lines 1–145; historical research/owner observations, not live graph proof'),
('M16','research/theme_graph/theme_fabric_gap_matrix.json',None,'selected top-level fields and bounded census excerpt; not current graph census'),
('M17','research/FACTOR_INTELLIGENCE_MASTERPLAN_BY_FABLE.md',None,'lines 1–180; existing separate programme charter/frozen interpretation'),
('M18','agentos/handoffs/GMI-THEME-GRAPH-2026-10-08-finviz-discover.md','0a63f4c20e4bfe2037f945e0b2b42f553dbddda8','complete returned handoff range 1–160; recorded PR/tests are historical claims'),
('M19','tests/test_factor_series.py','297dc6afb3effc972e20d9e69ef2ad0b3823c4fb','complete file read; NOT executed in native repository'),
('M20','tests/test_us_basket_membership_pit.py','30e6c0408ae395e9f8460f221d6a8661a6366ac3','lines 1–140; fixture/owner contract evidence, NOT executed'),
('M21','config/theme_sources.yml','20e20cb9f40ba838821aabba371f4498724943f2','bounded complete registry text read; GMI scope and specific grandfathered paths')]
entries=[dict(key=k,repository='mastermindx-market-intelligence/macro',commit=macro,path=p,blob_sha=b,inspection=i,
              url=f'https://github.com/mastermindx-market-intelligence/macro/blob/{macro}/{p}') for k,p,b,i in rows]
for k,p,b,i in [
('T01','terminal/app/api/sector-intelligence/route.ts','2607c8407a18308a018ff4a3168f15f292f52031','complete returned file; no served browser proof'),
('T02','terminal/lib/sectorIntelligence.ts','b62b2999cb1377da9a88b29971ed8788aa8175df','lines 1–200; shape/receipt/membership/concentration/URL state'),
('T03','tests/test_factordata_source.py','c40b49961f3fb7b8ba65687afda31c23ae9d6a3e','lines 1–170; NOT executed in native repository')]:
 entries.append(dict(key=k,repository='mastermindx-market-intelligence/mastermind-terminal',commit=terminal,path=p,blob_sha=b,inspection=i,
                     url=f'https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/{terminal}/{p}'))
public=[
('P01','https://www.spglobal.com/spdji/en/documents/methodologies/methodology-index-math.pdf','S&P DJI Index Mathematics, April 2026; parsed methodology and successful screenshots of cover and pages 11/21 (zero-index); page-16 screenshot failed and is not claimed as visual evidence.'),
('P02','https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html','First-party factor-library construction/vintage/revision and FIZ→CIZ notes.'),
('P03','https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html','First-party five-factor construction; academic/house distinction.'),
('P04','https://syndication.finra.org/content/short-interest-what-it-what-it-not','FINRA short positions versus short-sale volume.'),
('P05','https://developer.finra.org/docs','FINRA API publication documentation; not proof of historical release clocks for every observation.'),
('P06','https://www.spglobal.com/spdji/en/landing/topic/gics/','First-party classification hierarchy and scope; no redistribution rights inferred.'),
('P07','https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-alerts/sec','Official leveraged/inverse ETF investor bulletin; daily objectives versus longer-period compounding.'),
('P08','https://github.com/ranaroussi/yfinance/blob/main/README.md','Primary software project points to data terms; software license is not a market-data entitlement.'),
('P09','https://liqn.ai/landing','Live public landing/sign-in/metadata only; no authenticated history or methodology evidence.')]
register={
 'schema':'factor_atlas_research_source_register.v0',
 'role':'citation_and_inspection_evidence_not_a_source_or_owner_registry',
 'observation_date_local':'2026-10-08', 'timezone':'America/New_York',
 'pins':{'Mastermind':mastermind,'macro':macro,'mastermind-terminal':terminal},
 'source_files':entries,
 'public_sources':[{'key':k,'url':u,'observed_scope':s,'access_date_local':'2026-10-08'} for k,u,s in public],
 'direct_measurements':{'house_baskets':49,'member_slots':1038,'unique_ticker_strings':708,
                        'mag7_members':7,'ai_infra_members':24,'ai_software_members':17},
 'owner_declarations_not_independent_recounts':{'backprojected_baskets':35,'canonical_crosswalk_themes':18,'primary_basket_maps':13,'null_primary_maps':5},
 'unresolved': ['full affected-PR exact-head/custody reconciliation','membership parquet interval/record-kind/completeness census',
                'actual price-purpose entitlement and adjustment-vintage coverage','full historical identity/alias store census',
                'exact chart consumer binding and authenticated served proof','LIQN exact historical and spread methods'],
 'refused_read_batches':{'count':2,'remote_modifying_effects':[],'replayed_or_alternate_carrier_for_same_effect':False},
 'liqn_receipt':{'source_url':'https://liqn.ai/landing','http_status':200,'returned_links':[],
                 'firecrawl_scrape_id':'01a11e82-4797-7011-8612-7eb8aae3d98c','max_age':0,
                 'metadata_scope_claim':{'thematic_factors_lower_bound':150,'us_equities_lower_bound':3000},
                 'claim_type':'first_party_marketing_metadata_not_independent_population_census'}
}
(R/'source_register.json').write_text(json.dumps(register,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
print(f'Registered {len(entries)} source-file references and {len(public)} public sources.')
