"""Bounded stdin/stdout consumer for the pure conditional financial bridge.

Usage: python -m scripts.analyze_financial_bridge < scenario.json
No file path/provider/network/credential knobs; no persistence.
"""
from __future__ import annotations

import json
import sys
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
        if len(sys.argv) != 1:
            raise ValueError('unexpected_arguments')
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError('oversized_input')
        payload = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                             parse_float=str, parse_constant=_constant)
        result = analyze_financial_bridge(payload)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        result = invalid_result(['input:invalid_json_or_size'])
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n')
    return 2 if result['status'] == 'invalid_request' else 0


if __name__ == '__main__':
    raise SystemExit(main())
