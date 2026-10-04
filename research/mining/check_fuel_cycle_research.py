"""Pass 04 research arithmetic and deliberately incompatible-input examples.

Standard library only. Run beside the report: python check_fuel_cycle_research.py
No product imports, network access, orders, nuclear-process calculations or writes
outside the adjacent research-check receipt. Not a production financial model.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / 'MINING_URANIUM_FUEL_CYCLE_ECONOMICS_2026-09-23.md'
RECEIPT = ROOT / 'MINING_FUEL_CYCLE_RESEARCH_CHECKS_2026-09-23.json'
checks: list[dict[str, object]] = []

def check(name: str, condition: bool, evidence: object, source: str = 'ORIGINAL_PEDAGOGICAL_EXAMPLE') -> None:
    checks.append({'check': name, 'passed': bool(condition), 'evidence': evidence, 'source': source})

def pct(new: D, old: D) -> D:
    if old <= 0:
        raise ValueError('Positive baseline required for this illustrative growth ratio')
    return (new / old - 1) * 100

def rounded(value: D, places: str = '.01') -> D:
    return value.quantize(D(places))

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

# Deliberately limited teaching helper. This is not a new contract/identity owner.
@dataclass(frozen=True)
class ExampleMeasure:
    value: D
    unit: str
    currency: str | None
    basis: str
    start_year: int
    end_year: int

def comparable_window_change(new: ExampleMeasure, old: ExampleMeasure) -> D:
    if (new.unit, new.currency, new.basis, new.start_year, new.end_year) != (
        old.unit, old.currency, old.basis, old.start_year, old.end_year
    ):
        raise ValueError('Incompatible illustrative measure scope')
    return pct(new.value, old.value)

def rejected(name: str, fn, source: str = 'ORIGINAL_PEDAGOGICAL_EXAMPLE') -> None:
    try:
        fn()
    except ValueError as exc:
        check(name, True, str(exc), source)
    else:
        check(name, False, 'Incompatible example was accepted', source)

raw = REPORT.read_bytes()
text = raw.decode('utf-8')
cases = re.findall(r'^### (UF-C\d{2}) ', text, re.M)
refs = re.findall(r'^- \*\*(F\d{2}) — ', text, re.M)
requirements = re.findall(r'^\| (UF-\d{2}) \|', text, re.M)
check('ten_distinct_dossiers', cases == [f'UF-C{i:02d}' for i in range(1,11)], cases, 'DOCUMENT')
check('nineteen_source_records', refs == [f'F{i:02d}' for i in range(1,20)], refs, 'DOCUMENT')
check('twenty_four_proposed_requirements', requirements == [f'UF-{i:02d}' for i in range(1,25)], requirements, 'DOCUMENT')
check('source_references_resolve', set(re.findall(r'\bF\d{2}\b', text)) == set(refs), sorted(set(refs)), 'DOCUMENT')
urls = re.findall(r'https://\S+', text.split('## 10. Primary-source register and provenance',1)[1])
check('unique_source_urls', len(urls) == len(set(urls)) == 19, len(urls), 'DOCUMENT')
check('corrected_F09_actual_publishing_path', any('transition-haleu-production-cascade-to-commercial-operation/' in u for u in urls), 'Exact link followed from issuer news index', 'F09')
check('research_only_and_incomplete', '**Mission complete:** false.' in text and '**Final Fable implementation handoff:** not created.' in text, 'HOLD', 'DOCUMENT')
check('exact_source_pin', '4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2' in text, 'Mastermind exact pin', 'DOCUMENT')
check('existing_carrier', '#7795' in text and 'sol/mining-principal-research-20260923' in text, 'Same research operation', 'DOCUMENT')
view_table = text.split('## 4. Candidate research baskets and company-role mapping',1)[1].split('**Proposed weighting policy:**',1)[0]
rows = [line for line in view_table.splitlines() if line.startswith('|')]
check('eight_proposed_analytical_views', len(rows)-2 == 8, len(rows)-2, 'DOCUMENT')
check('four_discriminating_scenarios', all(f'**Scenario {c} — ' in text for c in 'ABCD'), 'A through D', 'DOCUMENT')
check('no_placeholder_markers', re.search(r'\b(TODO|TBD|FIXME)\b', text) is None, 'No placeholder markers', 'DOCUMENT')

weighted = (D(5998)*D('75.83') + D(40854)*D('55.91'))/D(46852)
check('EIA_price_covered_quantities_sum', D(5998)+D(40854)==D(46852), 'thousand lb equivalent with price', 'F02')
check('EIA_weighted_price', rounded(weighted)==D('58.46'), str(weighted), 'F02')
check('EIA_longterm_share', rounded(D(40854)/D(46852)*100)==D('87.20'), str(D(40854)/D(46852)*100), 'F02')
check('EIA_contracted_range_difference', D(174095)-D(132508)==D(41587), 'thousand lb; not additional demand', 'F03')
old_common = D(184211)-D(1924)
new_common = D(186278)-D(36429)
check('EIA_old_matched_horizon', old_common==D(182287), str(old_common), 'F04')
check('EIA_new_matched_horizon', new_common==D(149849), str(new_common), 'F04')
check('EIA_endpoint_extension_growth', rounded(pct(D(186278),D(184211)))==D('1.12'), str(pct(D(186278),D(184211))), 'F04')
check('EIA_matched_horizon_change', new_common-old_common==D(-32438) and rounded(pct(new_common,old_common))==D('-17.80'), str(pct(new_common,old_common)), 'F04')
old = ExampleMeasure(old_common,'thousand_lb_equivalent',None,'unfilled_requirements',2026,2034)
new = ExampleMeasure(new_common,'thousand_lb_equivalent',None,'unfilled_requirements',2026,2034)
check('compatible_comparison_accepted', rounded(comparable_window_change(new,old))==D('-17.80'), 'Matched observation scope, different publication vintages', 'F04 / PEDAGOGICAL_HELPER')
rejected('unmatched_delivery_horizon_rejected', lambda: comparable_window_change(ExampleMeasure(D(186278),'thousand_lb_equivalent',None,'unfilled_requirements',2026,2035),old))
rejected('mass_vs_service_unit_rejected', lambda: comparable_window_change(ExampleMeasure(new_common,'service_units',None,'unfilled_requirements',2026,2034),old))
rejected('suppressed_or_zero_baseline_not_growth', lambda: pct(D(100),D(0)))

check('Cameco_opposing_signs_preserved', D(14)>0 and D(-2)<0 and D(-12)<0, 'CAD million for +USD5/lb issuer scenario', 'F05')
check('Cameco_shocks_not_mirrored', (D(-28),D(-8),D(2)) != tuple(-x for x in (D(14),D(-2),D(-12))), 'Downward scenario not inverse of upward', 'F05')
check('Cameco_2026_finite_response', (D(67)-D(66))/(D(100)-D(80))==D('.05'), 'Rounded conditional scenario cells, not stock beta', 'F05')
check('Cameco_2030_finite_response', (D(88)-D(76))/(D(100)-D(80))==D('.60'), 'Rounded conditional scenario cells, not precise derivative', 'F05')
check('KAP_revenue_change', rounded(pct(D(717834),D(660167)))==D('8.74'), str(pct(D(717834),D(660167))), 'F07')
check('KAP_attributable_ebitda_change', rounded(pct(D(264840),D(302408)))==D('-12.42'), str(pct(D(264840),D(302408))), 'F07')
check('KAP_operating_cash_change', rounded(pct(D(239590),D(532870)))==D('-55.04'), str(pct(D(239590),D(532870))), 'F07')
rejected('attributable_vs_consolidated_rejected', lambda: comparable_window_change(ExampleMeasure(D(264840),'million','KZT','attributable_EBITDA',2026,2026),ExampleMeasure(D(371252),'million','KZT','group_adjusted_EBITDA',2026,2026)))

check('Centrus_backlog_segments_sum', D('3.7')+D('.8')==D('4.5'), 'USD billion', 'F08')
check('Centrus_contingent_share', rounded(D(3)/D('4.5')*100)==D('66.67'), 'Not an investment-success probability', 'F08')
check('Centrus_definitive_contingent_subset', D('2.4')/D(3)*100==D(80) and D('2.4')<D(3)<D('3.7'), 'Do not add nested subset again', 'F08')
check('Centrus_upfront_gross', D(500000)*D('199.64')+D(2005513)*D('199.54')==D('500000064.02'), 'USD gross, prior to costs', 'F12')
check('Centrus_prefunded_residual', D(2005513)*D('.10')==D('200551.30'), 'USD; separate from upfront consideration', 'F12')
check('Centrus_share_scenario_denominator', 500000+2005513==2505513, 'As-exercised scenario, not current legal/GAAP shares', 'F12–F13')
check('Centrus_common_warrant_cash_not_assured', 'cashless-exercise election' in text and 'not guaranteed additional funding' in text, 'No full-cash exercise assumption', 'F13 / DOCUMENT')
check('new_customer_event_after_quarter', date(2026,9,17)>date(2026,6,30), 'Cannot backdate customer event into June snapshot', 'F11')

check('Urenco_orderbook_change', rounded(pct(D('27.3'),D('21.3')))==D('28.17'), str(pct(D('27.3'),D('21.3'))), 'F14')
check('Urenco_revenue_change', rounded(pct(D('645.4'),D('830.4')))==D('-22.28'), str(pct(D('645.4'),D('830.4'))), 'F14')
check('Urenco_capital_accrual_bridge', D('259.2')-D('7.8')==D('251.4'), 'EUR million', 'F14')
check('Urenco_cash_less_cash_investment', D('220.4')-D('259.2')==D('-38.8'), 'Explicit calculation, not normalized FCF', 'F14')
check('Orano_reported_adjusted_directions', D(173)>D(109) and D(-39)<D(25), 'Different defined measures; not source error', 'F15')
check('Denison_inventory_sale_proceeds', D(750000)*D('122.16')==D(91620000), 'CAD', 'F16')
check('Denison_historical_acquisition_cost', D(750000)*D('36.67')==D('27502500'), 'CAD historical cost, not IFRS carrying value', 'F16')
check('Denison_historical_price_difference', D(750000)*(D('122.16')-D('36.67'))==D('64117500'), 'Not current-quarter IFRS gain', 'F16')
check('Denison_inventory_categories_not_identical', 950000+145926==1095926 and 'Future committed deliveries are not already shipped material.' in text, 'Total check does not erase category/commitment distinctions', 'F16 / DOCUMENT')
check('Yellow_Cake_held_plus_pending', 23214230+1160766==24374996, 'Scenario after delivery, not June held quantity', 'F17')
check('hypothetical_discount_offset', rounded((D('1.1')*D('.8')/D('.9')-1)*100)==D('-2.22'), 'Illustrative NAV+10%; discount10% to20%, not actual return')
check('hypothetical_buyback_accretion', rounded(D(92)/D(9),'.001')==D('10.222'), 'Assumes 100 assets/10 shares; one share bought for8, excludes costs')
check('Paladin_incompatible_margin_demonstrated', (D(70)-D('43.3'))*D('4.35')==D('116.145') and D('116.145')!=D('52.2'), 'USD million; not a profit estimate', 'F18–F19')
check('Paladin_annual_summary_residual_preserved', D('304.3')-D('250.0')-D('52.2')==D('2.1') and 'We do not force that reconciliation' in text, 'USD million, unclosed summary bridge', 'F19 / DOCUMENT')
check('native_history_not_claimed', 'not proof that Mastermind held it then' in text, 'Current retrieval is not contemporaneous native receipt', 'DOCUMENT')

receipt = {
    'operation': 'gmi-mining-principal-research-20260923-sol-001',
    'classification': 'LOCAL_RESEARCH_ARITHMETIC_DOCUMENT_AND_PEDAGOGICAL_COMPARISONS_ONLY',
    'run_utc': datetime.now(timezone.utc).isoformat(),
    'research_cutoff': '2026-09-23',
    'command': 'python check_fuel_cycle_research.py',
    'document': REPORT.name,
    'document_words': len(text.split()),
    'document_bytes': len(raw),
    'document_sha256': hashlib.sha256(raw).hexdigest(),
    'document_git_blob_sha1': git_blob(raw),
    'script_git_blob_sha1': git_blob(Path(__file__).read_bytes()),
    'total': len(checks), 'passed': sum(bool(c['passed']) for c in checks),
    'failed': sum(not bool(c['passed']) for c in checks),
    'checks': checks,
    'prepublication_notes': [
        'F09 initially drafted from an incorrect URL slug; corrected by following the live issuer index before publication.',
        'All arithmetic uses stated source inputs or explicitly invented pedagogical examples; no issuer figure was changed to force agreement.',
        'EIA matched-window calculation uses published cumulative endpoints; independent rounding remains a limitation.',
        'Paladin annual-summary difference remains unresolved; no full annual-PDF/accounting review is claimed.'
    ],
    'not_claimed': ['application tests','CI','independent research review','issuer-accounting reconciliation','contract settlement','native historical retention','source-rights approval','canonical Agent OS validation','investment validation','browser proof','Fable dispatch','product implementation']
}
RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
print(json.dumps({k:receipt[k] for k in ['document_words','document_bytes','document_sha256','document_git_blob_sha1','script_git_blob_sha1','total','passed','failed']},indent=2))
for c in checks:
    if not c['passed']: print('FAIL:', c['check'], c['evidence'])
if receipt['failed']: raise SystemExit(1)
