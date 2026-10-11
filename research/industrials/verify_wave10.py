"""Read-only research arithmetic and document checks; no product or trade logic.

Optional --native-schema checks an exact public repository schema locally with
jsonschema. It does not write or admit an evidence row. It does not exercise a
store, authenticated API, live deployment, or independent factual review.
"""
from __future__ import annotations
import argparse
from decimal import Decimal as D
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
SPEC = '2026-09-23-industrials-result-cash-dossier-design.md'
NOTE = 'INDUSTRIALS_WAVE10_INTERFACE_QUALIFICATION_2026-09-23.md'
SCHEMA_BLOB = '83dece15e98b9c8775a584afcd6ee09811dad220'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-schema', type=Path)
    args = parser.parse_args()
    results: list[dict[str, object]] = []

    def check(name: str, condition: bool) -> None:
        results.append({'check': name, 'passed': bool(condition)})

    # W10-S01/S02. USD thousands; the paired exclusion is our sensitivity,
    # not an issuer-defined adjusted operating-income measure.
    current_op, prior_op = D('28022'), D('17177')
    current_pair, prior_pair = D('11783'), D('16963')
    current_other, prior_other = D('12744'), D('19638')
    isolated_current, isolated_prior = current_op + current_pair, prior_op + prior_pair
    check('paired operating amounts', (isolated_current, isolated_prior) == (D('39805'), D('34140')))
    check('current paired pretax invariant', isolated_current + current_other - current_pair == current_op + current_other)
    check('prior paired pretax invariant', isolated_prior + prior_other - prior_pair == prior_op + prior_other)
    check('reported operating delta decomposes', current_op - prior_op == D('5665') + D('5180'))
    check('paired operating delta', isolated_current - isolated_prior == D('5665'))
    check('isolated growth lower than headline', Fraction(5665,34140) < Fraction(10845,17177))
    check('net and total revenue growth differ', Fraction(15992,132868) < Fraction(29650,141962))

    current_cfo = sum(map(D, ('58964','5193','2076','15738','2225','-39073','9428','2309','-4930','-25101','3085')))
    prior_cfo = sum(map(D, ('53203','5012','586','13426','-3094','-10191','7135','1756','4153','-23774','-4716')))
    check('current cash statement reconciliation', current_cfo == D('29914'))
    check('prior cash statement reconciliation', prior_cfo == D('43496'))
    check('after cash capex proxy', (current_cfo-D('4228'), prior_cfo-D('4028')) == (D('25686'),D('39468')))
    check('receivables and other operating offsets', current_cfo-prior_cfo == -D('28882')+D('15300'))
    check('cash balance rollforward', D('221930')+current_cfo-D('4228')-D('180833')-D('154') == D('66629'))
    check('cash change reconciles', current_cfo-D('4228')-D('180833')-D('154') == -D('155301'))
    check('profit and cash direction differ', D('58964')>D('53203') and current_cfo<prior_cfo)

    # W10-S04. USD millions. Current and comparative segment perimeters follow
    # the issuer's recast table. Do not infer a tariff-refund allocation.
    current_segments = sum(map(D, ('69.8','126.4','57.6')))
    prior_segments = sum(map(D, ('54.8','108.5','152.7')))
    check('segment totals', (current_segments,prior_segments) == (D('253.8'),D('316.0')))
    check('current corporate reconciliation', current_segments-D('17.2') == D('236.6'))
    check('prior corporate reconciliation', prior_segments-D('19.3') == D('296.7'))
    check('segment and corporate delta', D('15.0')+D('17.9')-D('95.1')+D('2.1') == D('236.6')-D('296.7'))
    check('quarterly cash sums to half year', -D('67.4')+D('571.8') == D('504.4'))
    check('quarterly free cash sums to half year', -D('85.7')+D('552.9') == D('467.2'))
    check('half year issuer cash formula', D('504.4')-D('37.4')+D('0.2') == D('467.2'))
    check('prior half year issuer cash formula', D('567.7')-D('27.7')+D('0.1') == D('540.1'))
    check('free cash change bridge', -D('63.3')-D('9.7')+D('0.1') == -D('72.9'))
    check('preview finalization is distinct arithmetic', (Fraction(114,100)-Fraction(112,100))/Fraction(112,100) == Fraction(1,56))

    spec_path = ROOT/SPEC
    if not spec_path.is_file():
        spec_path = ROOT.parents[1]/'docs'/'superpowers'/'specs'/SPEC
    spec, note = spec_path.read_text(encoding='utf-8'), (ROOT/NOTE).read_text(encoding='utf-8')
    ids = re.findall(r'^\| (IND-D\d{2}) \|', spec, re.M)
    check('30 unique sequential acceptance cases', ids == [f'IND-D{i:02d}' for i in range(1,31)])
    check('12 native references', len(set(re.findall(r'W10-R\d{2}', note)))==12)
    check('four primary source references', len(set(re.findall(r'W10-S\d{2}', note)))==4)
    check('spec references all source cases', all(f'W10-S{i:02d}' in spec for i in range(1,5)))
    check('proposed not accepted', 'PROPOSED / NOT ACCEPTED / NOT IMPLEMENTED' in spec and 'MISSION_COMPLETE: false' in spec)
    check('native read pin preserved', all('da092e5d4a64dbb7c3958826f8cd60d7cbd02cc5' in s for s in (spec,note)))
    check('same carrier and operation', all('gmi-industrials-sector-research-20260923-sol-001' in s and '#7789' in s for s in (spec,note)))
    check('time and publication limitations explicit', 'signature into an acceptance clock' in note and 'same-day' in spec.lower() and 'midnight' in spec)
    check('body semantics and private restrictions explicit', all(s in spec for s in ('transcript','public workspace','localStorage','Research Vault')))
    check('no accidental draft placeholders', not re.search(r'\b(?:TODO|TBD|FIXME)\b',spec))

    native = {'requested': bool(args.native_schema), 'executed': False}
    if args.native_schema:
        body=args.native_schema.read_bytes()
        blob=hashlib.sha1(f'blob {len(body)}\0'.encode()+body).hexdigest()
        if blob != SCHEMA_BLOB:
            raise ValueError(f'Native schema identity mismatch: {blob}')
        from jsonschema import Draft202012Validator
        schema=json.loads(body)
        Draft202012Validator.check_schema(schema)
        validator=Draft202012Validator(schema)
        # Hermetic shape example only. No native source/evidence ID is minted.
        baseline={
            'evidence_id':'hermetic-test-only', 'kind':'operator_curation',
            'published_at':'2026-09-23','source_ref':'test-only:not-for-publication',
            'licensing_internal_ok':False,'licensing_display_ok':False,
            'licensing_redistribution_ok':False,'computed_at':'2026-09-23T00:00:00Z',
        }
        check('native receipt baseline structurally valid', validator.is_valid(baseline))
        errors=list(validator.iter_errors({**baseline,'curation_assertion':{}}))
        check('native added body refused by closed schema', any(e.validator=='additionalProperties' for e in errors))
        missing={k:v for k,v in baseline.items() if k!='published_at'}
        check('native missing publication day refused', any(e.validator=='required' for e in validator.iter_errors(missing)))
        native={'requested':True,'executed':True,'schema_blob':blob,'local_only':True}

    output={
        'research_only':True,'product_tests_executed':False,
        'independent_factual_review':False,'predictive_validation':False,
        'native_schema':native,
        'calculations': {
            'expo_reported_op_growth_pct': str(((current_op/prior_op-1)*100).quantize(D('0.0001'))),
            'expo_paired_sensitivity_op_growth_pct': str(((isolated_current/isolated_prior-1)*100).quantize(D('0.0001'))),
            'expo_h1_operating_cash_growth_pct': str(((current_cfo/prior_cfo-1)*100).quantize(D('0.0001'))),
            'expo_h1_cash_after_capex_thousand_usd': str(current_cfo-D('4228')),
            'pnr_q2_adjusted_op_change_million_usd': str(D('236.6')-D('296.7')),
            'pnr_h1_issuer_free_cash_change_million_usd': str(D('467.2')-D('540.1')),
        },
        'passed':sum(r['passed'] for r in results),
        'failed':sum(not r['passed'] for r in results),'checks':results,
    }
    print(json.dumps(output,indent=2))
    return 0 if output['failed']==0 else 1


if __name__=='__main__':
    raise SystemExit(main())
