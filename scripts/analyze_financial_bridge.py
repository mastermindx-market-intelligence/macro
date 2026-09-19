"""Bounded stdin/stdout consumer for the pure conditional financial bridge.

Usage: python -m scripts.analyze_financial_bridge < scenario.json
No file path/provider/network/credential knobs; no persistence.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine.neuralweb.brain_financial_bridge import analyze_financial_bridge, invalid_result

MAX_INPUT_BYTES = 32768


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate_key')
        result[key] = value
    return result


def _constant(_value):
    raise ValueError('nonfinite')


def main() -> int:
    try:
        if sys.argv[1:] not in ([], ['--explain']):
            raise ValueError('unexpected_arguments')
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError('oversized_input')
        payload = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                             parse_float=str, parse_constant=_constant)
        result = analyze_financial_bridge(payload)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        result = invalid_result(['input:invalid_json_or_size'])
    if sys.argv[1:] == ['--explain'] and result['status'] != 'invalid_request':
        sys.stdout.write(_explain(result))
    else:
        sys.stdout.write(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n')
    return 2 if result['status'] == 'invalid_request' else 0




def _explain(result: dict) -> str:
    """Render only accepted inputs, computed cells and explicitly untested prompts."""
    lines = ['Conditional financial analysis',
             'Basis: caller-supplied, unverified assumptions; not company facts or a price target.',
             'No company evidence was retrieved. No causal explanation is established.',
             f"Amounts: {result['currency']} {result['amount_scale']}; periods: {result['period_months']} months.",
             '', 'Calculated results']
    def cell_line(key, cell):
        if cell['value'] is None:
            gap = ', '.join(cell['missing_inputs']) or cell['reason'] or 'not computable'
            return f'{key}: unavailable ({gap})'
        rounded = ' [rounded]' if cell['rounded'] else ''
        return f"{key}: {cell['value']} {cell['unit']}{rounded}"
    for key in ('prior.gross_profit', 'current.gross_profit', 'prior.operating_profit',
                'current.operating_profit', 'prior.simplified_operating_cash',
                'current.simplified_operating_cash', 'current.cash_after_capex',
                'change.eps_pct', 'change.implied_price_pct'):
        lines.append(cell_line(key, result['calculations'][key]))
    lines += ['', 'What would change the result?', result['reasoning']['test_assumption']]
    for key, cell in result['scenario_tests'].items():
        lines.append(cell_line(key, cell))
        lines.append('  Vary: '+cell['varied_input']+'; fixed references: '+', '.join(cell['fixed_inputs']))
        if cell['baseline_inputs']:
            lines.append('  Reference base: '+', '.join(cell['baseline_inputs']))
        if cell.get('within_value_range') is False:
            lines.append('  Outside the declared input range; not a feasible equality setting.')
    lines += ['', 'Interpretation and rival tests']
    if not result['reasoning']['findings']:
        lines.append('No supported pattern from the supplied inputs; do not fabricate a thesis.')
    for finding in result['reasoning']['findings']:
        lines.append(finding['conclusion'])
        lines.append('  Supports: '+', '.join(finding['supports']))
        for rival in finding['rivals']:
            lines.append('  Untested rival: '+rival['hypothesis'])
            lines.append('    Evidence to check: '+rival['evidence_to_check'])
            lines.append('    Would weaken: '+rival['would_weaken'])
    lines += ['', result['reasoning']['scope'], '', 'Limitations']
    lines.extend(result['limitations'])
    return '\n'.join(lines)+'\n'


if __name__ == '__main__':
    raise SystemExit(main())
