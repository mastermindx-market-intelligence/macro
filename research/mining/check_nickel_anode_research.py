"""Pass08 research arithmetic, indexing and pedagogical compatibility checks.

Standard library only. Run beside both reports: python check_nickel_anode_research.py
No product imports, network, trading output or production accounting/contract model.
The only output file is the adjacent research receipt. Source facts are not audited.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / 'MINING_NICKEL_COBALT_ANODE_ECONOMICS_2026-09-23.md'
COVERAGE = ROOT / 'MINING_COVERAGE_AND_DESIGN_FRONTIER_2026-09-23.md'
OUT = ROOT / 'MINING_NICKEL_ANODE_RESEARCH_CHECKS_2026-09-23.json'
checks: list[dict[str, object]] = []

def check(name: str, passed: bool, evidence: object) -> None:
    checks.append({'check': name, 'passed': bool(passed), 'evidence': evidence})

def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()

def digest(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {'bytes': len(raw), 'words': len(raw.decode('utf-8').split()),
            'sha256': hashlib.sha256(raw).hexdigest(), 'git_blob_sha1': git_blob(raw)}

@dataclass(frozen=True)
class Share:
    fraction: D
    basis: str
    year: int

def nickel_kt(gwh: D, share: Share, kg_per_kwh: D, year: int) -> D:
    # GWh -> million kWh and kg -> thousand tonnes cancel numerically.
    if share.basis != 'capacity' or share.year != year:
        raise ValueError('Incompatible share basis or year')
    if not D(0) <= share.fraction <= D(1) or min(gwh, kg_per_kwh) < 0:
        raise ValueError('Invalid nonnegative demand input')
    return gwh * share.fraction * kg_per_kwh

def yield_fraction(output: D, feed: D, *, output_batch: str, input_batch: str,
                   same_material_basis: bool, measured_mass: bool) -> D:
    if output_batch != input_batch or not same_material_basis or not measured_mass:
        raise ValueError('An explicit measured batch transformation is required')
    if feed <= 0 or not D(0) <= output <= feed:
        raise ValueError('Invalid compatible mass quantities')
    return output / feed

def acceptance(states: list[str]) -> str:
    if not states or any(x not in {'pass', 'fail', 'unknown'} for x in states):
        raise ValueError('Explicit nonempty criterion states required')
    if 'fail' in states:
        return 'not_met'
    return 'unknown' if 'unknown' in states else 'met'

def rejected(name: str, fn) -> None:
    try:
        fn()
    except ValueError as exc:
        check(name, True, str(exc))
    else:
        check(name, False, 'Expected explicit rejection did not occur')

if not REPORT.is_file() or not COVERAGE.is_file():
    raise SystemExit('Run beside the Pass08 report and updated coverage document.')
t = REPORT.read_text(encoding='utf-8')
c = COVERAGE.read_text(encoding='utf-8')
check('ten_dossiers', re.findall(r'^### (NC-\d{2}) ', t, re.M) == [f'NC-{n:02}' for n in range(1,11)], 'NC-01..10')
check('fourteen_sources', re.findall(r'^- \*\*(S\d{2}) —', t, re.M) == [f'S{n:02}' for n in range(1,15)], 'S01..14')
check('source_references_resolve', set(re.findall(r'\bS\d{2}\b', t)) == {f'S{n:02}' for n in range(1,15)}, 'No orphan source identifier')
check('source_urls_unique', len(set(re.findall(r'https://\S+', t))) == 14, 'Fourteen distinct source URLs, not corpus-wide uniqueness')
check('twenty_eight_requirements', re.findall(r'^\| (MC-\d{2}) \|', t, re.M) == [f'MC-{n:02}' for n in range(1,29)], 'Prospective, not implemented')
check('six_hypothetical_cases', re.findall(r'^### (H\d{2}) ', t, re.M) == [f'H{n:02}' for n in range(1,7)], 'H01..06')
check('four_personas', re.findall(r'^### (U\d{2}) ', t, re.M) == [f'U{n:02}' for n in range(1,5)], 'U01..04')
check('held_mission_boundary', '**Mission complete:** false' in t and '**Final Fable implementation handoff:** not created' in t, 'Research only')
check('protected_revision_present', 'a7d2b3049e5cdc523e91e61a6e9d70a1cb911157' in t, 'Same compatible Skillpack pin')
check('eight_canonical_pass_rows', re.findall(r'^\| (P\d{2}) \|', c, re.M) == [f'P{n:02}' for n in range(1,9)], 'P01..P08 only')
check('duplicate_p05_stays_excluded', 'DO_NOT_PUBLISH_DUPLICATE' in c and '42c90b4634b4b408c014b7ccb335744adb79bf48' in c and '587ee020adec174233c42ad987f531d767b7c0ea' in c, 'Canonical and excluded identities preserved')
check('coverage_moves_to_native_design', 'begin current-interface design preparation' in c and 'do not dispatch the final Fable' in c, 'No indefinite new company-note cycle')
check('inaccessible_numeric_sources_excluded', 'Conflicting secondary cash figures' in t and 'CMOC numerical snippets were also excluded' in t, 'No substitution of unverified numerics')

n0 = nickel_kt(D(100), Share(D('.50'), 'capacity', 2025), D('.7'), 2025)
n1 = nickel_kt(D(130), Share(D('.35'), 'capacity', 2026), D('.7'), 2026)
check('H01_initial_nickel', n0 == D('35'), str(n0))
check('H01_new_nickel', n1 == D('31.85'), str(n1))
check('H01_change', (n1/n0-1)*100 == D('-9'), 'Modelled branch -9%; GWh +30%')
check('H01_capacity_growth', (D(130)/D(100)-1)*100 == D(30), '30%')
check('H01_graphite_growth_with_substitution', D(130)*D('.8') == D(104), '104 kt vs hypothetical 100 kt')
rejected('H01_count_share_rejected', lambda: nickel_kt(D(100), Share(D('.5'),'vehicles',2026), D('.7'), 2026))
rejected('H01_wrong_year_rejected', lambda: nickel_kt(D(100), Share(D('.5'),'capacity',2025), D('.7'), 2026))
rejected('H01_bad_fraction_rejected', lambda: nickel_kt(D(100), Share(D('1.2'),'capacity',2026), D('.7'), 2026))

check('H02_sell_instead_of_convert', D(18500)-D(2000)-D(17000) == D(-500), '-500 incremental dollars per stipulated unit')
check('H02_convert_when_spread_improves', D(20000)-D(2000)-D(17000) == D(1000), '+1000 incremental dollars')
check('H02_threshold', D(17000)+D(2000) == D(19000), '19000 final realization before other burdens')

shape = D(100)*D('.7')
processed = shape*D('.95')
accepted = processed*D('.90')
check('H03_shaping_quantity', shape == D(70), str(shape))
check('H03_second_stage', processed == D('66.5'), str(processed))
check('H03_saleable_quantity', accepted == D('59.85'), str(accepted))
check('H03_feed_cost_per_saleable', (D(60000)/accepted).quantize(D('.001')) == D('1002.506'), str(D(60000)/accepted))
check('H03_simplified_contribution', accepted*D(1500)-D(60000)-D(15000) == D(14775), '14775; not issuer or full cash flow')
check('H03_addition_is_not_final_output', D(100)+shape+processed+accepted != accepted, 'Serial intermediate stages are not extra tonnes')

check('H04_unknown_criterion', acceptance(['pass','pass','pass','unknown']) == 'unknown', 'Not 75% accepted')
check('H04_failed_criterion', acceptance(['pass','pass','pass','fail']) == 'not_met', 'No compensating mean score')
check('H04_all_technical_criteria_met', acceptance(['pass']*4) == 'met', 'Technical set only, not commercial readiness')
rejected('H04_empty_criteria_rejected', lambda: acceptance([]))
rejected('H04_numeric_score_rejected', lambda: acceptance(['pass','85.7%']))

available = D(30)-D(8)-D(7)
check('H05_funds_after_stipulated_obligations', available == D(15), 'USDm hypothetical only')
check('H05_base_shortfall', D(4)*D(4)-available == D(1), 'USD1m')
check('H05_delay_increment', D(2)*D(4) == D(8), 'USD8m')
check('H05_delayed_shortfall', D(6)*D(4)-available == D(9), 'USD9m')
check('H06_gross_less_credit', D(100)-D(20) == D(80), '80 net cost')
check('H06_repeated_credit_is_wrong', D(80)-D(20) != D(100)-D(20), '60 is not 80')

check('Eramet_indirect_interest', D('.43')*D('.90') == D('.387'), '38.7%; not a new entitlement estimate')
check('Eramet_ownership_differs_offtake', D('.387') != D('.43'), 'Separate scopes')
check('Terrafame_revenue_categories_sum', D('127.8')+D('138.3') == D('266.1'), 'EURm H1 reported categories')
check('Terrafame_EBITDA_growth', ((D('51.5')/D('25.5')-1)*100).quantize(D('.1')) == D('102.0'), 'Not a cash-flow or causal reconciliation')
check('Glencore_copper_change', ((D(397)/D('343.9')-1)*100).quantize(D('.1')) == D('15.4'), '100%-basis except source exceptions')
check('Glencore_cobalt_change', ((D('10.2')/D('18.9')-1)*100).quantize(D('.1')) == D('-46.0'), 'Different process-stage implications')
check('Sherritt_cash_geographic_sum', D('80.1')+D('119.8')+D('3.9') == D('203.8'), 'Canadian + Cuban + other cash; not all unrestricted')
check('NOVONIX_announced_first_payment', D(35)*D('.2') == D(7), 'US$7m required; no payment proof')
check('NOVONIX_conditional_remaining_balance', D(35)-D(7) == D(28), 'Only upon payment; not observed settlement')
rejected('unrelated_project_capacities_not_yield', lambda: yield_fraction(D(13), D(106), output_batch='anode_project', input_batch='mine_project', same_material_basis=False, measured_mass=False))
rejected('nominal_capacity_not_measured_yield', lambda: yield_fraction(D(60), D(100), output_batch='A', input_batch='A', same_material_basis=True, measured_mass=False))
check('explicit_measured_batch_yield', yield_fraction(D('59.85'), D(100), output_batch='A', input_batch='A', same_material_basis=True, measured_mass=True) == D('.5985'), 'Hypothetical measured batch only')

receipt = {
 'operation':'gmi-mining-principal-research-20260923-sol-001',
 'classification':'LOCAL_RESEARCH_ARITHMETIC_INDEXING_AND_PEDAGOGICAL_EXAMPLES_ONLY',
 'run_utc':datetime.now(timezone.utc).isoformat(), 'research_cutoff':'2026-09-23',
 'command':'python check_nickel_anode_research.py',
 'documents':{p.name:digest(p) for p in (REPORT,COVERAGE)},
 'script_git_blob_sha1':git_blob(Path(__file__).read_bytes()),
 'total':len(checks),'passed':sum(bool(x['passed']) for x in checks),
 'failed':sum(not bool(x['passed']) for x in checks), 'checks':checks,
 'not_claimed':['application tests','CI','independent research review','issuer-accounting audit',
 'contract settlement','customer confirmation','native historical retention','source rights',
 'Agent OS validation','browser proof','investment validation','earlier-suite rerun']
}
OUT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({k:receipt[k] for k in ('run_utc','documents','script_git_blob_sha1','total','passed','failed')},indent=2))
if receipt['failed']:
    print(json.dumps([x for x in checks if not x['passed']],indent=2))
    raise SystemExit(1)
