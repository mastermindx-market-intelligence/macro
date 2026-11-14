"""Reproduce eight FIXED research examples, not a production financial engine.

Standard library only. No native-owner, network, model, identity or private-data
access. Optional --output writes an explicit local experiment receipt. The
source locators and interpretation limits are in the accompanying study.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from decimal import Decimal as D, getcontext
from fractions import Fraction as F
import json
from pathlib import Path

# id, issuer, source, unit, comparison, scope, prior output, current output,
# components: key, prior printed value, current printed value, coefficient.
CASES = [
 ('AB01','Meta','M2Q','USD million','Q2-2026 vs Q2-2025','consolidated operating income',20441,18775,
  [('revenue',47516,60801,1),('cost_of_revenue',8491,11330,-1),('R&D',12942,21656,-1),('marketing_sales',2979,3431,-1),('G&A',2663,5609,-1)]),
 ('AB02','Meta','M2Q','USD million','Q2-2026 vs Q2-2025','issuer-defined consolidated FCF',8549,784,
  [('CFO',25561,31862,1),('property_equipment_magnitude',16538,30116,-1),('lease_principal_magnitude',474,962,-1)]),
 ('AB03','Alphabet','G2Q','USD million','Q2-2026 vs Q2-2025','Google advertising revenue',71340,81629,
  [('Search_other',54190,63271,1),('YouTube_ads',9796,11055,1),('Network',7354,7303,1)]),
 ('AB04','Alphabet','G2Q','USD million','Q2-2026 vs Q1-2026','issuer-defined consolidated FCF',10116,-5855,
  [('CFO',45790,39069,1),('property_equipment_magnitude',35674,44924,-1)]),
 ('AB05','The Trade Desk','T2Q','USD thousand','Q2-2026 vs Q2-2025','consolidated operating income',116777,101577,
  [('revenue',694039,715057,1),('platform_operations',150980,184333,-1),('sales_marketing',161131,174404,-1),('technology_development',134251,140742,-1),('G&A',130900,114001,-1)]),
 ('AB06','Magnite','MG2Q','USD thousand','Q2-2026 vs Q2-2025','contribution ex-TAC',161956,189595,
  [('revenue',173332,192823,1),('derived_TAC_magnitude',11376,3228,-1)]),
 ('AB07','Magnite','MG2Q','USD thousand','Q2-2026 vs Q2-2025','GAAP gross profit',108379,130785,
  [('revenue',173332,192823,1),('cost_of_revenue',64953,62038,-1)]),
 ('AB08','Magnite','MG2Q','USD thousand','Q2-2026 vs Q2-2025','contribution ex-TAC by channel',161956,189595,
  [('CTV',71543,97133,1),('mobile',63772,65771,1),('desktop',26641,26691,1)]),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    getcontext().prec = 40
    checks = []
    killed = {k: 0 for k in ('inverted_sign','omitted_component','scale_error','duplicate_component')}

    def check(name, condition, **detail):
        if not condition:
            raise AssertionError(name)
        checks.append({'check': name, 'passed': True, **detail})

    def equation(prior, terms, kind=D):
        return kind(prior) + sum((kind(c)-kind(p))*coef for _,p,c,coef in terms)

    check('four_issuers_eight_ids', len({c[1] for c in CASES}) == 4 and len({c[0] for c in CASES}) == 8)
    for ident, issuer, source, unit, period, scope, prior, current, terms in CASES:
        check(ident+'_decimal', equation(prior,terms) == D(current), value=str(current),unit=unit)
        check(ident+'_fraction', equation(prior,terms,F) == F(current))
        check(ident+'_component_keys',len({x[0] for x in terms})==len(terms))
        scaled=[(k,p*1000,c*1000,coef) for k,p,c,coef in terms]
        check(ident+'_consistent_rescaling', equation(prior*1000,scaled)/1000 == D(current))
        for i in range(len(terms)):
            for mode in killed:
                bad=list(terms)
                key,p,c,coef=bad[i]
                if mode=='inverted_sign': bad[i]=(key,p,c,-coef)
                elif mode=='omitted_component': bad.pop(i)
                elif mode=='duplicate_component': bad.append(bad[i])
                else: bad[i]=(key,p*1000,c*1000,coef)
                check(f'{ident}_{mode}_{i}',equation(prior,bad)!=D(current))
                killed[mode]+=1

    check('TAC_is_derived',192823-189595==3228 and 173332-161956==11376)
    delta=D(189595-161956)
    check('same_outcome_two_partitions',D(19491+8148)==delta and D(25590+1999+50)==delta,
          lower_TAC_share_pct=str(D(8148)/delta*100),CTV_share_pct=str(D(25590)/delta*100))
    check('do_not_add_partitions',delta*2!=delta)
    # Synthetic revision of ONLY the total. No source correction is asserted.
    total=D(190595)
    derived_TAC=D(192823)-total
    channel_sum=D(97133+65771+26691)
    check('tautology_is_not_independent_confirmation',D(192823)-derived_TAC==total
          and total-channel_sum==1000,
          explanation='Derived cost identity balances while unchanged channels disagree by 1000. Do not allocate the residual.')
    a=CASES[3]
    period_changed=list(deepcopy(a));period_changed[4]='Q2-2026 vs Q2-2025'
    check('numbers_cannot_detect_wrong_period',equation(a[6],a[8])==equation(period_changed[6],period_changed[8])
          and a[4]!=period_changed[4],explanation='Native period binding remains untested and required.')
    scope_changed=list(deepcopy(a));scope_changed[5]='Search-only FCF'
    check('numbers_cannot_detect_wrong_scope',equation(a[6],a[8])==equation(scope_changed[6],scope_changed[8])
          and a[5]!=scope_changed[5],explanation='Native population binding remains untested and required.')
    check('TTM_and_quarter_are_different',24461+24551+10116-5855==53273 and a[7]<0)
    support=[F(995+i,10) for i in range(11)]
    check('same_operand_not_independent_intervals',{x-x for x in support}=={F(0)}
          and min(x-y for x in support for y in support)==-1
          and max(x-y for x in support for y in support)==1)
    report={'result':'PASS','checks_passed':len(checks),'numeric_mutations_detected':killed,
            'product_tests_run':0,'native_admission':False,'independent_audit':False,
            'limitations':'Fixed displayed-value research examples. Decimal/Fraction share transcribed inputs. No product code, source-retention, metadata-binding, identity, privacy or predictive test is executed.',
            'checks':checks}
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('result','checks_passed','numeric_mutations_detected','product_tests_run')},indent=2))


if __name__=='__main__':
    main()
