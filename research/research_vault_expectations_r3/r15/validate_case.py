"""Deterministic public-source case checks, not a production financial engine.

Inputs are assistant-entered figures and explicitly curated definitions. This
program verifies arithmetic and declared compatibility, not source authenticity,
financial extraction, current market conditions, investment skill or permissions.
It does not import or execute the held R14 reader review.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit


def number(value: object) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('A number must be an explicit decimal string, not missing/boolean')
    try:
        result = Decimal(value)
    except InvalidOperation as e:
        raise ValueError('Invalid decimal') from e
    if not result.is_finite():
        raise ValueError('Nonfinite value')
    return result


def bounds(row: dict) -> tuple[Decimal, Decimal]:
    if 'value' in row:
        if 'low' in row or 'high' in row:
            raise ValueError('Ambiguous point and range')
        n = number(row['value'])
        return n, n
    lo, hi = number(row.get('low')), number(row.get('high'))
    if lo > hi:
        raise ValueError('Inverted range')
    return lo, hi


def validate(data: dict) -> dict:
    sources, facts = data.get('sources'), data.get('facts')
    if not isinstance(sources, list) or not isinstance(facts, list):
        raise ValueError('Missing source/fact arrays')
    source_ids = {s['id'] for s in sources}
    if len(source_ids) != len(sources):
        raise ValueError('Duplicate source')
    for s in sources:
        if urlsplit(s['url']).scheme != 'https' or not s.get('publisher'):
            raise ValueError('Invalid source reference')
        datetime.date.fromisoformat(s['published_on'])
    if len({f['id'] for f in facts}) != len(facts):
        raise ValueError('Duplicate fact')
    for f in facts:
        if f.get('source_id') not in source_ids:
            raise ValueError('Unknown source reference')
        for key in ('issuer', 'metric', 'period', 'basis', 'kind', 'scale'):
            if not isinstance(f.get(key), str) or not f[key]:
                raise ValueError('Missing declared comparison dimension: ' + key)
        bounds(f)
    for rel in data.get('curated_relations', []):
        ids = {f['id'] for f in facts}
        if rel.get('before') not in ids or rel.get('after') not in ids or rel.get('source_id') not in source_ids:
            raise ValueError('Orphan relation')
    return {'sources': len(sources), 'facts': len(facts),
            'publishers': len({s['publisher'] for s in sources})}


def compare_guidance(a: dict, b: dict) -> dict:
    if a['kind'] != 'issuer_guidance' or b['kind'] != 'issuer_guidance':
        raise ValueError('This case compares issuer guidance, not actuals or broker opinions')
    for key in ('issuer', 'metric', 'period', 'scale'):
        if a[key] != b[key]:
            raise ValueError('Incompatible guidance dimension: ' + key)
    al, ah = bounds(a); bl, bh = bounds(b)
    dl, dh = bl-al, bh-ah
    same_basis = a['basis'] == b['basis']
    if not same_basis:
        classification = 'measurement_basis_changed'
    elif dl == 0 and dh == 0:
        classification = 'captured_values_unchanged'
    elif dl > 0 and dh == 0:
        classification = 'lower_bound_raised'
    elif dl == 0 and dh < 0:
        classification = 'upper_bound_lowered'
    elif dl > 0 and dh > 0:
        classification = 'both_bounds_raised'
    elif dl < 0 and dh < 0:
        classification = 'both_bounds_lowered'
    else:
        classification = 'range_reshaped'
    return {'before': a['id'], 'after': b['id'], 'classification': classification,
            'like_for_like': same_basis, 'reported_low_difference': str(dl),
            'reported_high_difference': str(dh),
            'range_width_difference': str((bh-bl)-(ah-al)),
            'scale': a['scale'], 'target': a['period'],
            'economic_change': None, 'expected_value_change': None,
            'interpretation': 'Declared-basis arithmetic only; neither physical investment volume nor distribution expectation is estimated.'}


def reconcile(rows: list[dict], signs: list[int], reported: dict) -> dict:
    if not rows or len(rows) != len(signs) or any(type(s) is not int or s not in (-1,1) for s in signs):
        raise ValueError('Explicit signed operands required')
    for r in rows:
        for key in ('issuer', 'period', 'scale'):
            if r[key] != reported[key]:
                raise ValueError('Mixed cash reconciliation dimension: '+key)
        if r['kind'] != 'reported_actual' or 'value' not in r:
            raise ValueError('Cash reconciliation needs point actuals')
    if reported['kind'] != 'reported_actual' or 'value' not in reported:
        raise ValueError('Expected reported point actual')
    result = sum((number(r['value'])*s for r,s in zip(rows,signs)), Decimal(0))
    return {'inputs': [r['id'] for r in rows], 'signs': signs,
            'reported_id': reported['id'], 'calculated': str(result),
            'reported': reported['value'], 'matches_reported': result == number(reported['value']),
            'scale': reported['scale'], 'period': reported['period'],
            'formula_selection': 'Explicit analyst-curated formula; code does not infer accounting equivalence.'}


def same_basis_total(rows: list[dict]) -> str:
    if not rows:
        raise ValueError('No observations')
    for r in rows:
        if 'value' not in r:
            raise ValueError('No automatic range aggregation')
        for key in ('metric', 'period', 'scale', 'basis', 'kind'):
            if r[key] != rows[0][key]:
                raise ValueError('Incompatible aggregation dimension: '+key)
    return str(sum((number(r['value']) for r in rows), Decimal(0)))


def analyze(data: dict) -> dict:
    counts = validate(data); f = {r['id']: r for r in data['facts']}
    change = [compare_guidance(f['ms-guide-old'],f['ms-guide-new']),
              compare_guidance(f['meta-guide-old'],f['meta-guide-new'])]
    recipes = [(['ms-cfo','ms-cash-ppe'],[1,-1],'ms-fcf'),
               (['meta-cfo','meta-ppe','meta-principal'],[1,-1,-1],'meta-fcf'),
               (['meta-cfo-prior','meta-ppe-prior','meta-principal-prior'],[1,-1,-1],'meta-fcf-prior'),
               (['amzn-ppe-gross','amzn-proceeds'],[1,-1],'amzn-ppe-net'),
               (['amzn-cfo','amzn-ppe-net'],[1,-1],'amzn-fcf')]
    checks = [reconcile([f[i] for i in inputs], signs, f[target]) for inputs,signs,target in recipes]
    if not all(c['matches_reported'] for c in checks):
        raise ValueError('One of the explicitly sourced cash bridges does not reconcile')
    try:
        same_basis_total([f['meta-fcf'],f['amzn-fcf']])
    except ValueError as e:
        aggregation = {'status':'not_comparable','reason':str(e)}
    else:
        raise AssertionError('Mixed source definitions/periods were accepted')
    return {'scope':'PUBLIC_PRIMARY_SOURCE_RESEARCH_CASE_NOT_PRODUCTION',
            'counts':counts, 'guidance_comparisons':change,
            'cash_reconciliations':checks, 'cross_company_fcf_total':aggregation,
            'no_model_run':True,'no_source_original_hash_attestation':True,
            'no_runtime_deployment':True,'no_held_r14_tests_executed':True}


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, default=Path(__file__).with_name('capex_evidence.json'))
    ap.add_argument('--output', type=Path, required=True)
    args=ap.parse_args()
    raw=args.input.read_bytes();result=analyze(json.loads(raw))
    result['executed_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    result['curated_input_sha256']=hashlib.sha256(raw).hexdigest()
    result['hash_meaning']='Identifies this curated review input, not the original issuer HTML/PDF.'
    # Exclusive creation prevents an old receipt silently being overwritten.
    with args.output.open('x',encoding='utf-8') as out:
        out.write(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'counts':result['counts'],'reconciled_cash_formulas':len(result['cash_reconciliations']),
                      'comparison_kinds':[c['classification'] for c in result['guidance_comparisons']],
                      'mixed_total':result['cross_company_fcf_total']['status']},indent=2))
    return 0
if __name__=='__main__':
    try: raise SystemExit(main())
    except (OSError,ValueError,KeyError,TypeError) as exc:
        ap_error='Public-source case validation failed: '+str(exc)
        raise SystemExit(ap_error)
