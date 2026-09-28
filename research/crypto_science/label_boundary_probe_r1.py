"""Exploratory reproduction of an immature-label boundary, not a gate writer."""
from pathlib import Path
import hashlib
import json
import sys
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine import btc_impulse_radar_backtest as baseline


def main():
    source = ROOT / 'engine/btc_impulse_radar_backtest.py'
    c = pd.Series([100.,101.,102.,103.,104.,105.,106.,107.],
                  index=pd.date_range('2026-01-01',periods=8))
    down, up = baseline._labels(c)
    obsolete = c.shift(-1).rolling(3).min()
    indexer = pd.api.indexers.FixedForwardWindowIndexer(window_size=3)
    correct = c.rolling(indexer,min_periods=3).min().shift(-1)
    result = {'classification':'EXPLORATORY_SOURCE_LABEL_AUDIT_NOT_PERFORMANCE_RESULT',
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'hypothesis':'The historical research snippet misaligns the forward window; current canonical extrema fix that but comparisons coerce immature tail NaNs to False.',
        'example_date':'2026-01-03','documented_snippet_min':float(obsolete.loc['2026-01-03']),
        'correct_forward_min':float(correct.loc['2026-01-03']),
        'expected_window':['2026-01-04','2026-01-05','2026-01-06'],
        'canonical_down_tail':down.tail(3).tolist(),'canonical_up_tail':up.tail(3).tolist(),
        'canonical_tail_nonnull':int(down.tail(3).notna().sum()),
        'mature_windows':int(correct.notna().sum()),'naive_label_nonnull':int(down.notna().sum()),
        'notes':'Did not call validate(), write_gate(), collectors, PnL or model promotion. Forward extrema implementation is correct; horizon-unavailable mask is not preserved by boolean comparison.'}
    # A matched result confirms reproduction of the defect, NOT a passing model.
    assert result['documented_snippet_min'] == 101
    assert result['correct_forward_min'] == 103
    assert result['mature_windows'] == 5
    assert result['naive_label_nonnull'] == 8
    assert result['canonical_tail_nonnull'] == 3
    assert result['canonical_down_tail'] == [False,False,False]
    target = Path(__file__).with_name('r1_label_boundary_exploratory.json')
    if target.exists():
        assert json.loads(target.read_text()) == result, 'Earlier reproduction differs; investigate'
    else:
        target.write_text(json.dumps(result,indent=2)+'\n')
    print('REPRODUCED: 5 mature outcomes, 8 non-null boolean labels; no gate write')


if __name__ == '__main__':
    main()
