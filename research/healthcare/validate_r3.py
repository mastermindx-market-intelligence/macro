"""Validate research-artifact consistency only; does not run product acceptance cases."""
import json, pathlib, hashlib, re
from decimal import Decimal as D
from datetime import date
ROOT=pathlib.Path(__file__).parent
P=ROOT/'HEALTHCARE_SUPPLIER_ECONOMICS_R3_EXAMPLES_2026-09-23.json'
M=ROOT/'HEALTHCARE_SUPPLIER_ECONOMICS_R3_2026-09-23.md'
x=json.loads(P.read_text())
sources=set(x['source_ids'])
arrays=['entity_examples','ownership_examples','measurement_examples','scenario_examples','adversarial_specifications']
records=[r for k in arrays for r in x[k]]
ids=[r['id'] for r in records]
assert len(ids)==len(set(ids))==81
assert sources==set(re.findall(r'^- \*\*(R3-S\d{2})',M.read_text(),re.M)) and len(sources)==35
assert all(set(r['sources'])<=sources and r['sources'] for r in records)
assert all(x[k] is False for k in ['production_validated','basket_membership_authorized','trading_authorized'])
assert x['application_case_execution']=='NOT_EXECUTED'
assert x['materiality_default']['value'] is None and x['materiality_default']['reason']
assert x['security_identity_default']['value'] is None and x['security_identity_default']['reason']
for r in records:
    for k in ['period_start','period_end','announcement_date','effective_date']:
        if r.get(k): assert date.fromisoformat(r[k])<=date.fromisoformat(x['as_of'])
    for k,v in r.items():
        if v is None:
            assert r.get(k+'_reason'),(r['id'],k)
assert json.loads(json.dumps(x,ensure_ascii=False))==x
v={r['id']:r for r in records}
d=lambda r,k:D(str(v[r][k]))
checks=[]
def check(name,condition,actual,expected):
    assert condition,name
    checks.append(dict(name=name,status='PASS',actual=str(actual),expected=str(expected)))
q=d('R3-M01','ebitda')/d('R3-M01','revenue')*100
check('Bachem margin rounds to reported figure',q.quantize(D('.1'))==D('25.4'),q.quantize(D('.1')),'25.4 percent')
q=d('R3-M02','operating_cash')-d('R3-M02','cash_ppe_purchases')-d('R3-M02','cash_intangible_purchases')
check('PolyPeptide cash bridge',q==D('-19102'),q,'-19102 EUR thousands')
naive=d('R3-M02','operating_cash')-d('R3-M02','headline_capital_expenditure')
check('PolyPeptide rejects accrual-capex substitution',naive!=q,naive,'not -19102')
r='R3-M03'
q=d(r,'operating_cash')+d(r,'interest_paid_addback')-d(r,'interest_received_deduction')-d(r,'cash_ppe_purchases')+d(r,'ppe_sale_proceeds')-d(r,'cash_intangible_purchases')
check('Stevanato issuer FCF definition reconciles',q==d(r,'reported_fcf'),q,'-32.0 EUR millions')
group=d('R3-M04','high_value_sales')/d('R3-M04','group_sales')*100
segment=d('R3-M04','high_value_sales')/d('R3-M04','bds_sales')*100
check('Stevanato two denominators preserved',round(group)==45 and round(segment)==51 and group!=segment,f'{round(group)}/{round(segment)}','45 group / 51 BDS percent')
r='R3-M05';q=sum(d(r,k) for k in ['core_revenue','milestone_revenue','royalty_revenue'])
check('MaxCyte components sum to total',q==d(r,'total_revenue'),q,'7271 USD thousands')
r='R3-M06';q=sum(d(r,k) for k in ['ebitda','trade_working_capital_change','capex','other_reconciling_items'])
check('Lonza operational FCF bridge',q==d(r,'operational_fcf'),q,'426 CHF millions')
r='R3-O02';lo=d(r,'cash_per_target_share_usd')+d(r,'buyer_shares_per_target_share')*100;hi=d(r,'cash_per_target_share_usd')+d(r,'buyer_shares_per_target_share')*200
check('Mixed consideration depends on buyer price',lo!=hi,f'{lo}/{hi}','different hypothetical values; 100 and 200 are invented inputs, not observed prices')
r='R3-O06';q=sum(d(r,k) for k in ['seller_equity_usd_m_approx','assumed_net_debt_usd_m_approx','other_components_usd_m_approx'])
check('Telix rounded components do not add debt twice',abs(q-d(r,'upfront_usd_m_approx'))<=2,q,'approximately 1650 USD millions; components rounded')
r='R3-O05';q=d(r,'current_percent')+d(r,'remaining_percent')
check('Wilson Wolf current and future stakes sum correctly',q==100 and d(r,'current_percent')<100,q,'100 percent split into current and future interests')
check('Fiscal report labels not treated as identical periods',v['R3-M07']['period_end']!=v['R3-M08']['period_end'],f"{v['R3-M07']['period_end']}/{v['R3-M08']['period_end']}",'different period ends')
pending=['R3-O02','R3-O03','R3-O04','R3-O06','R3-O07']
check('All five unproven closings retain null plus reason',all(v[r]['closing_date'] is None and v[r]['closing_date_reason'] for r in pending),len(pending),'5 held closing records')

def digest(path):
    b=path.read_bytes()
    return {'name':path.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
report={'kind':'local_research_artifact_validation','as_of':x['as_of'],'records':len(records),'source_ids':len(sources),'counts':{k:len(x[k]) for k in arrays},'structural_checks':'PASS: parsing/roundtrip, unique IDs, source closure, date bounds, null reasons and held-authority flags','deterministic_checks':checks,'application_cases_executed':0,'clinical_validation':False,'production_validation':False,'files':[digest(P),digest(M)]}
(ROOT/'R3_LOCAL_VALIDATION_RECEIPT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(report,indent=2))
