"""Pass 06 local research checks, not application or investment validation.

Run beside both Markdown reports: python check_specialty_research.py
Standard library only; no network, product imports, trades or process instructions.
Compatibility examples are pedagogical, not an accepted production contract.
"""
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
REPORT = 'MINING_SPECIALTY_ENABLER_ECONOMICS_2026-09-23.md'
COVERAGE = 'MINING_COVERAGE_AND_DESIGN_FRONTIER_2026-09-23.md'
checks: list[dict[str, object]] = []


def check(name: str, passed: bool, evidence: object) -> None:
    checks.append({'check': name, 'passed': bool(passed), 'evidence': evidence})


def blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def change(current: str, previous: str) -> D:
    if D(previous) == 0:
        raise ValueError('Undefined percentage with a zero comparison base')
    return (D(current) / D(previous) - 1) * 100


def same_basis(a: tuple[str, ...], b: tuple[str, ...]) -> None:
    """Illustrative labels: material, unit, scope, period-kind, basis."""
    if a != b:
        raise ValueError('Incompatible observation labels')


def refuses(name: str, a: tuple[str, ...], b: tuple[str, ...]) -> None:
    try:
        same_basis(a, b)
    except ValueError:
        check(name, True, 'Expected incompatible-label refusal')
    else:
        check(name, False, 'Incompatible inputs were accepted')


def main() -> None:
    docs = {}
    for name in (REPORT, COVERAGE):
        raw = (ROOT / name).read_bytes()
        text = raw.decode('utf-8')
        docs[name] = {'bytes': len(raw), 'words': len(text.split()),
                      'sha256': hashlib.sha256(raw).hexdigest(), 'git_blob_sha1': blob(raw)}
    text = (ROOT / REPORT).read_text(encoding='utf-8')
    coverage = (ROOT / COVERAGE).read_text(encoding='utf-8')
    cases = re.findall(r'^### (SE-C\d{2}) ', text, re.M)
    sources = re.findall(r'^- \*\*(S\d{2}) — ', text, re.M)
    hypotheses = re.findall(r'^### (SE-H\d{2}) ', text, re.M)
    personas = re.findall(r'^### (SE-P\d{2}) ', text, re.M)
    reqs = re.findall(r'^\| (MS-\d{2}) \|', text, re.M)
    check('eleven_dossiers', cases == [f'SE-C{i:02d}' for i in range(1, 12)], cases)
    check('sixteen_source_records', sources == [f'S{i:02d}' for i in range(1, 17)], sources)
    check('five_hypotheticals', hypotheses == [f'SE-H{i:02d}' for i in range(1, 6)], hypotheses)
    check('four_persona_workflows', personas == [f'SE-P{i:02d}' for i in range(1, 5)], personas)
    check('twenty_eight_proposals', reqs == [f'MS-{i:02d}' for i in range(1, 29)], reqs)
    check('all_source_ids_resolve', set(re.findall(r'\bS\d{2}\b', text)) == set(sources), sources)
    urls = re.findall(r'https://\S+', text.split('## 9. Primary-source register', 1)[1])
    check('unique_primary_urls', len(urls) == len(set(urls)) == 16, len(urls))
    for name, doc in [('report', text), ('coverage', coverage)]:
        check(name + '_held_mission', '**Mission complete:** false.' in doc and
              '**Final Fable implementation handoff:** not created.' in doc, 'Explicit scope')
        check(name + '_current_pin', 'a7d2b3049e5cdc523e91e61a6e9d70a1cb911157' in doc, 'Pinned procedure')
    check('canonical_p05_reference', '38690a0909799d5d2b80ef23ff467cd1a73006a4' in coverage and
          '42c90b4634b4b408c014b7ccb335744adb79bf48' in coverage, 'Canonical commit/blob')
    check('parallel_p05_excluded', 'DO_NOT_PUBLISH_DUPLICATE' in coverage and
          '587ee020adec174233c42ad987f531d767b7c0ea' in coverage, 'No duplicate publication')
    check('six_pass_references', all(f'| P{i:02d} |' in coverage for i in range(1, 7)), 'P01-P06')
    check('three_gap_classes', all(f'### G{i} —' in coverage for i in range(1, 4)), 'Local claim, regime, release')
    check('no_global_completeness_score', 'not a numerical completeness score' in coverage, 'No invented denominator')
    check('historical_checks_not_rerun', 'does not claim to rerun them' in coverage, 'Current suite only')

    values = [
        ('Kipushi_output_percent', change('70177', '65044'), '7.89'),
        ('Kipushi_payable_sales_percent', change('43424', '54940'), '-20.96'),
        ('FCX_primary_moly_output_percent', change('8', '9'), '-11.11'),
        ('FCX_primary_moly_unit_cost_percent', change('19.20', '14.20'), '35.21'),
        ('Sibanye_composite_ounces_percent', change('2788340', '1152079'), '142.03'),
        ('Sibanye_PGM_ounces_percent', change('194926', '155375'), '25.46'),
        ('Sibanye_silver_physical_share_percent', D('2498226') / D('2788340') * 100, '89.60'),
        ('Weir_ESCO_constant_currency_percent', change('360', '329'), '9.42'),
        ('Weir_group_aftermarket_share_percent', D('1047') / D('1269') * 100, '82.51'),
        ('Metso_represented_growth_percent', change('1334', '1257'), '6.13'),
        ('Metso_incompatible_old_base_percent', change('1334', '1213'), '9.98'),
        ('Metso_order_to_sales', D('1462') / D('1334'), '1.10'),
        ('Metso_Q2_cash_percent', change('206', '147'), '40.14'),
        ('Metso_H1_cash_percent', change('285', '343'), '-16.91'),
        ('Orica_H1_operating_cash_percent', change('230.6', '244.9'), '-5.84'),
    ]
    for name, value, rounded in values:
        check(name, value.quantize(D('.01')) == D(rounded), str(value))
    check('Almonty_revaluation_components', D('204.4') - D('30.7') - D('.6') == D('173.1'),
          'CAD million; not normalized earnings')
    check('Sibanye_component_sum', D('95188') + D('194926') + D('2498226') == D('2788340'),
          'Physical ounces only; separate copper pounds excluded')

    initial = D('100') * D('1') * D('.5') * D('.8')
    later = D('80') * D('1') * D('.6') * D('.8')
    check('H01_host_output_initial', initial == D('40'), str(initial))
    check('H01_host_output_later', later == D('38.4'), str(later))
    check('H01_higher_recovery_lower_output', later < initial and change(str(later), str(initial)) == -4,
          'Hypothetical host availability falls 20%')
    check('H02_feed_contribution_vs_volume', change('70', '100') == -30 and change('4500', '4000') == D('12.5'),
          'Invented feasible feed alternatives')
    new_parts = D('100') / D('1.25')
    check('H03_same_work_parts', new_parts == 80, str(new_parts))
    check('H03_buyer_spend', new_parts * 110 == 8800, 'vs 10000 before, hypothetical')
    check('H03_supplier_capture', new_parts * (110 - 70) == 3200, 'vs 3000 before')
    check('H03_supplier_cost_countercase', new_parts * (110 - 75) == 2800, 'Below original 3000')
    check('H04_inventory_funding_delta', D('1000') * (150 - 100) == 50000, 'No quantity or industrial-margin inference')
    check('H05_accrual_not_cash_or_volume', D('12') > 0 and D('0') == 0, 'Stipulated accrual 12; paid cash and incremental shipments both 0')

    base = ('zinc', 'tonnes', 'asset100percent', 'quarter', 'payable_sales')
    same_basis(base, base)
    check('matched_labels_permitted', True, 'Positive compatibility example')
    for name, position, alternate in [
        ('reject_wrong_element_recovery', 0, 'gallium'),
        ('reject_ounces_pounds_join', 1, 'pounds'),
        ('reject_business_area_issuer_join', 2, 'whole_issuer'),
        ('reject_lifetime_annual_join', 3, 'lifetime'),
        ('reject_production_payable_sales_join', 4, 'production')]:
        changed = list(base)
        changed[position] = alternate
        refuses(name, base, tuple(changed))
    refuses('reject_old_vs_represented_perimeter', ('sales', '2025_original'), ('sales', '2025_represented'))
    refuses('reject_aftermarket_as_ARR', ('aftermarket_revenue',), ('annual_recurring_revenue',))
    refuses('reject_conditional_payment_as_cash', ('conditional_upfront',), ('cash_received',))
    refuses('reject_accrual_as_delivery', ('compensation_accrual',), ('product_delivery',))
    refuses('reject_certificate_as_achieved_runrate', ('commercial_permission',), ('measured_steady_output',))
    effective = datetime(2026, 9, 17, tzinfo=timezone.utc)
    publication = datetime(2026, 9, 21, tzinfo=timezone.utc)
    cutoff = datetime(2026, 9, 23, 23, 59, tzinfo=timezone.utc)
    check('recognize_later_supported_milestone', effective <= publication <= cutoff,
          'Positive progression, not nameplate assertion or native historical receipt')
    check('report_preserves_access_limits', 'Screenshot of page 10 failed' in text and
          'not independent regulator readback' in text, 'Exact evidence limitations')
    check('report_numeric_examples_present', all(x in text for x in
          ['7.89%', '20.96%', '142.03%', '25.46%', '89.60%', '82.51%', '6.13%', '9.98%']),
          'Selected report values agree with independently computed rounding')

    receipt = {'operation': 'gmi-mining-principal-research-20260923-sol-001',
               'classification': 'LOCAL_RESEARCH_ARITHMETIC_DOCUMENT_AND_PEDAGOGICAL_EXAMPLES_ONLY',
               'run_utc': datetime.now(timezone.utc).isoformat(), 'research_cutoff': '2026-09-23',
               'command': 'python check_specialty_research.py', 'documents': docs,
               'script_git_blob_sha1': blob(Path(__file__).read_bytes()),
               'total': len(checks), 'passed': sum(c['passed'] for c in checks),
               'failed': sum(not c['passed'] for c in checks), 'checks': checks,
               'not_claimed': ['application tests', 'CI', 'independent research review', 'accounting audit',
                               'contract settlement', 'native source rights or historical retention',
                               'canonical Agent OS validator', 'customer confirmation', 'browser proof',
                               'investment validation', 'rerun of earlier research checks']}
    (ROOT / 'MINING_SPECIALTY_RESEARCH_CHECKS_2026-09-23.json').write_text(
        json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ['run_utc', 'documents', 'total', 'passed', 'failed']}, indent=2))
    if receipt['failed']:
        print(json.dumps([c for c in checks if not c['passed']], indent=2))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
