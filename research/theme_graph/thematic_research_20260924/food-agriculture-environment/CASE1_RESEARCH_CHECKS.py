"""Local GMI A research checks; not native product code or predictive validation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Callable

D = Decimal
OPERATION = 'gmi-theme-research-food-agriculture-environment-20260924-001'
SOURCES = {
    'N26': 'https://www.nutrien.com/news/press-releases/nutrien-reports-second-quarter-2026-results-1753',
    'N25': 'https://www.sec.gov/Archives/edgar/data/1725964/000119312525174610/d86630dex992.htm',
}

@dataclass(frozen=True)
class Aging:
    source: str
    period: str
    region: str
    current: int
    lt31: int
    d31_90: int
    gt90: int
    gross: int
    allowance: int
    net: int
    unit: str = 'USD_millions'

    @property
    def past_due(self) -> int:
        return self.lt31 + self.d31_90 + self.gt90

ROWS = [
    Aging('N25', '2025-06-30', 'North America', 3384, 192, 62, 257, 3895, 76, 3819),
    Aging('N25', '2025-06-30', 'International', 724, 55, 17, 43, 839, 13, 826),
    Aging('N25', '2025-06-30', 'Total', 4108, 247, 79, 300, 4734, 89, 4645),
    Aging('N26', '2026-06-30', 'North America', 3686, 157, 60, 226, 4129, 66, 4063),
    Aging('N26', '2026-06-30', 'International', 916, 70, 23, 36, 1045, 7, 1038),
    Aging('N26', '2026-06-30', 'Total', 4602, 227, 83, 262, 5174, 73, 5101),
]

def percent(numerator: int, denominator: int, basis: str = 'gross') -> Decimal:
    if basis != 'gross' or denominator <= 0:
        raise ValueError('Require a positive gross-receivables denominator.')
    return D(numerator) * 100 / D(denominator)

def seasonal_pair(old: Aging, new: Aging) -> None:
    if (old.region, old.unit, old.period[5:]) != (new.region, new.unit, new.period[5:]):
        raise ValueError('Reported region, units and seasonal date must match.')
    if int(new.period[:4]) != int(old.period[:4]) + 1:
        raise ValueError('This comparison is defined for adjacent years only.')

def ratio_text(numerator: int, denominator: int) -> str:
    return str(percent(numerator, denominator).quantize(D('0.01'), rounding=ROUND_HALF_UP))

def after_disposition(begin: int, cash: int, writeoff: int, extension: int) -> int:
    """Synthetic overdue-stock bridge; no new entries, FX or other movements."""
    if min(begin, cash, writeoff, extension) < 0 or cash + writeoff + extension > begin:
        raise ValueError('Invalid synthetic balance.')
    return begin - cash - writeoff - extension

def collection_inference(due_cash: int | None, dispositions_known: bool) -> str:
    # An aging snapshot is not a due-invoice cash observation.
    return 'MEASURED_COHORT_ONLY' if due_cash is not None and dispositions_known else 'NOT_IDENTIFIED'

def event_evidence_families(events: list[dict[str, str]]) -> int:
    return len({row['economic_event'] for row in events})

def observed_forecast_input(kind: str) -> None:
    if kind != 'reported_actual':
        raise ValueError('A management forecast is not an observed result.')

def earned_revenue(advance_received: int, delivered_amount: int) -> int:
    """Synthetic one-for-one application of a prepaid sale, not an issuer forecast."""
    if advance_received < 0 or not 0 <= delivered_amount <= advance_received:
        raise ValueError('Invalid synthetic prepaid-sale state.')
    return delivered_amount


def main() -> None:
    passed: list[str] = []
    rejected: list[str] = []

    def check(name: str, predicate: bool) -> None:
        if not predicate:
            raise AssertionError(name)
        passed.append(name)

    def rejects(name: str, action: Callable[[], object]) -> None:
        try:
            action()
        except ValueError:
            rejected.append(name)
        else:
            raise AssertionError('Corruption accepted: ' + name)

    for row in ROWS:
        check(f'{row.source}/{row.region}: aging sums to gross', row.current + row.past_due == row.gross)
        check(f'{row.source}/{row.region}: allowance bridge', row.gross - row.allowance == row.net)
    for offset in (0, 3):
        na, intl, total = ROWS[offset:offset + 3]
        for field in ('current', 'lt31', 'd31_90', 'gt90', 'gross', 'allowance', 'net'):
            check(f'{na.source}: regional sum {field}', getattr(na, field) + getattr(intl, field) == getattr(total, field))

    old, new = ROWS[0], ROWS[3]
    seasonal_pair(old, new)
    check('North America seasonal pair accepted', True)
    check('2025 NA past-due dollars', old.past_due == 511)
    check('2026 NA past-due dollars', new.past_due == 443)
    check('2025 NA past-due ratio rounds correctly', ratio_text(old.past_due, old.gross) == '13.12')
    check('2026 NA past-due ratio rounds correctly', ratio_text(new.past_due, new.gross) == '10.73')
    check('2025 NA over90 ratio rounds correctly', ratio_text(old.gt90, old.gross) == '6.60')
    check('2026 NA over90 ratio rounds correctly', ratio_text(new.gt90, new.gross) == '5.47')

    end_stocks = [after_disposition(100, 20, 0, 0), after_disposition(100, 0, 20, 0), after_disposition(100, 0, 0, 20)]
    check('Equal ending stocks under three different cash outcomes', end_stocks == [80, 80, 80])
    check('Absent due-cohort cash is not identified', collection_inference(None, True) == 'NOT_IDENTIFIED')
    check('Unknown dispositions do not identify collection quality', collection_inference(20, False) == 'NOT_IDENTIFIED')
    check('Known cohort cash remains a cohort-only observation', collection_inference(20, True) == 'MEASURED_COHORT_ONLY')
    check('New current balances can lower delinquency ratio with unchanged overdue dollars', percent(20, 200) < percent(20, 100))
    check('Synthetic cash advance before delivery earns no revenue', earned_revenue(200, 0) == 0)
    check('Synthetic later full delivery releases prepaid revenue', earned_revenue(200, 200) == 200)
    check('Synthetic receipt and later advance application are one cash inflow', 200 + 0 == 200)
    check('Joint announcement and filing are one economic event', event_evidence_families([
        {'document': 'joint_release', 'economic_event': 'rimisoxafen_prepurchase'},
        {'document': 'FMC_10Q', 'economic_event': 'rimisoxafen_prepurchase'},
    ]) == 1)

    rejects('net denominator substituted for gross', lambda: percent(new.gt90, new.net, 'net'))
    rejects('December substituted for June seasonal comparison', lambda: seasonal_pair(replace(old, period='2025-12-31'), new))
    rejects('International substituted for North America', lambda: seasonal_pair(ROWS[1], new))
    rejects('CAD substituted for USD', lambda: seasonal_pair(replace(old, unit='CAD_millions'), new))
    rejects('non-adjacent year accepted without redefinition', lambda: seasonal_pair(replace(old, period='2024-06-30'), new))
    rejects('forecast promoted to observed actual', lambda: observed_forecast_input('management_forecast'))
    rejects('negative synthetic disposition', lambda: after_disposition(100, -1, 0, 0))
    rejects('prepaid revenue exceeds the synthetic prepaid amount', lambda: earned_revenue(200, 201))

    results = {
        'operation': OPERATION,
        'scope': 'Hand-transcribed research arithmetic and local semantic counterexamples only',
        'source_locators': SOURCES,
        'source_rows': [asdict(row) for row in ROWS],
        'north_america': {
            'periods': [old.period, new.period],
            'gross_receivables_USD_millions': [old.gross, new.gross],
            'past_due_USD_millions': [old.past_due, new.past_due],
            'past_due_percent_of_gross': [ratio_text(old.past_due, old.gross), ratio_text(new.past_due, new.gross)],
            'over90_USD_millions': [old.gt90, new.gt90],
            'over90_percent_of_gross': [ratio_text(old.gt90, old.gross), ratio_text(new.gt90, new.gross)],
            'gross_growth_percent': str(((D(new.gross) / D(old.gross) - 1) * 100).quantize(D('0.01'))),
            'verdict': 'Lower reported aging ratios; actual repayment improvement is not identified from snapshots alone',
            'not_a_fixed_cohort': True,
            'terms_currency_mix_and_writeoff_adjustment': 'not established',
        },
        'synthetic_counterexample': {'begin_overdue': 100, 'end_overdue': end_stocks, 'actual_cash': [20, 0, 0]},
        'positive_checks_passed': len(passed),
        'corrupted_variants_rejected': len(rejected),
        'failures': 0,
        'positive_checks': passed,
        'rejected_variants': rejected,
        'implementation_tests_executed': 0,
        'forecast_backtests_executed': 0,
        'independent_review': False,
        'authority': {'source_admission': False, 'product_write': False, 'ranking': False, 'trade': False},
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    path = Path(__file__).with_name('CASE1_VERIFICATION.json')
    path.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'positive_pass': len(passed), 'negative_rejected': len(rejected), 'fail': 0, 'derived': results['north_america'], 'receipt_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}, indent=2))

if __name__ == '__main__':
    main()
