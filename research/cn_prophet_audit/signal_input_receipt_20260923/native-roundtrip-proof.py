"""Real cached Chinese semiconductor inputs; not live/admission/performance proof."""
from pathlib import Path
import hashlib, io, json, subprocess, sys
import pandas as pd
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from engine import signal_gate, china_board_rank
PIN = '722910e0028a982956769cc779673b12e7936e59'
def read(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{PIN}:{path}'])
raw = read('data/china_search/closes.parquet')
member_raw = read('data/baskets_china/membership.json')
frame = pd.read_parquet(io.BytesIO(raw)).sort_index()
members = json.loads(member_raw)['baskets']['cn_semis']['members']
board_asof = str(pd.Timestamp(frame.index.max()).date())
report = {'proof_kind': 'frozen repository input to native gate to JSON to existing consumer; not production', 'source_commit': PIN, 'board_snapshot_session': board_asof, 'price_sha256': hashlib.sha256(raw).hexdigest(), 'membership_sha256': hashlib.sha256(member_raw).hexdigest(), 'live_event_latch_used': False, 'input_rows': len(frame), 'members': [], 'missing': []}
for member in members:
    ticker = member['ticker']
    if member.get('removed') or ticker not in frame:
        report['missing'].append(ticker)
        continue
    close = frame[ticker].dropna()
    if close.empty:
        report['missing'].append(ticker)
        continue
    verdict = signal_gate.gate(ticker, close, event_latch=None)
    assert verdict.get("reason") != signal_gate.ENGINE_ERROR, (ticker, verdict.get("reason"))
    verdict['input_asof'] = str(pd.Timestamp(close.last_valid_index()).date())
    payload = json.loads(json.dumps(signal_gate.buy_signal(verdict), allow_nan=False))
    row, = china_board_rank.enrich_and_score_rows([{'ticker': ticker, 'sector': 'Semiconductors', 'signal': payload}], board_asof=board_asof)
    assert payload['input_asof'] == verdict['input_asof']
    assert signal_gate.is_buyable(payload) == signal_gate.is_buyable(verdict)
    assert china_board_rank._signal_is_fresh(row) == (payload['input_asof'] == board_asof)
    without = {k: v for k, v in payload.items() if k != 'input_asof'}
    legacy, = china_board_rank.enrich_and_score_rows([{'ticker': ticker, 'sector': 'Semiconductors', 'signal': without}], board_asof=board_asof)
    assert china_board_rank._signal_is_fresh(legacy) is False
    report['members'].append({'ticker': ticker, 'daily_input': payload['input_asof'], 'analytical_asof': str(verdict.get('asof')), 'bars': len(close), 'receipt_matches_board_snapshot': china_board_rank._signal_is_fresh(row), 'reason': verdict.get('reason'), 'signal_eligible': payload.get('eligible'), 'tier': payload.get('tier_cascade'), 'eligibility_unchanged_by_serialization': True})
report['tested_members'] = len(report['members'])
report['all_receipts_preserved'] = bool(report['members'])
Path(__file__).with_name('native-roundtrip-proof.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
