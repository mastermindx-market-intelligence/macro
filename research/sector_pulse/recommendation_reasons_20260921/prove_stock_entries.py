"""Replay existing detail-page stock inputs through the stock-entry owner, offline."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine import basket_score
from prove import read_blob


def run(source_ref: str) -> dict:
    if re.fullmatch(r'[0-9a-f]{40}', source_ref) is None:
        raise ValueError('Require the immutable full source commit.')
    payload = json.loads(read_blob(source_ref, 'site/basketdata/baskets.json'))
    themes = payload['theme_intel']['themes']
    records = []
    unavailable = []
    for row in themes:
        path = f"site/basket/{row['id']}.html"
        try:
            raw = read_blob(source_ref, path)
        except Exception as exc:
            unavailable.append({'id': row['id'], 'reason': type(exc).__name__})
            continue
        detail, _ = json.JSONDecoder().raw_decode(raw.decode().split('const DETAIL = ', 1)[1])
        if detail['as_of'] != payload['theme_intel']['as_of']:
            raise ValueError(f"Mixed detail/theme clock for {row['id']}")
        before = detail['act_now']
        after = basket_score.act_now_stocks(detail['members'], detail['theme'])
        for key in ['status', 'buys', 'uncovered']:
            if after[key] != before[key]:
                raise ValueError(f"Changed canonical {key} for {row['id']}")
        if len(after['entry_checks']) != len(detail['members']):
            raise ValueError('Lost a member from the explanation projection.')
        ready = {r['symbol'] for r in after['buys']}
        watch = {r['symbol'] for r in after['early_turn_watch']}
        if ready & watch:
            raise ValueError('A member is simultaneously actionable and waiting.')
        records.append({'id': row['id'], 'source_path': path,
                        'source_sha256': hashlib.sha256(raw).hexdigest(),
                        'as_of': detail['as_of'], 'canonical_status_buys_coverage_unchanged': True,
                        'summary': after['entry_summary'],
                        'reason_counts': dict(Counter(x['code'] for x in after['entry_checks'])),
                        'checks': after['entry_checks']})
    return {'source_ref': source_ref, 'as_of': payload['theme_intel']['as_of'],
            'theme_pages_expected': len(themes), 'theme_pages_replayed': len(records),
            'unavailable_pages': unavailable,
            'source_owner_sha256': hashlib.sha256(Path(basket_score.__file__).read_bytes()).hexdigest(),
            'canonical_status_buys_coverage_unchanged': True,
            'records': records,
            'limitations': ['Existing dated page inputs; not a full nightly or current market replay.',
                            'Repeated stocks in different baskets are separate member rows, not independent observations.',
                            'No new scores, entry permissions, prices, targets or sizing decisions.',
                            'Native research controls remain bound to their original frozen source commits.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source_ref)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}, indent=2))
