"""Synthetic contract proof of the existing label owner. No market stores read."""
import argparse, hashlib, importlib.util, sys, unittest
from pathlib import Path
import numpy as np
import pandas as pd
OWNER = None

def fixture():
    return pd.DataFrame({'as_of':['2020-01-02']*3,'ticker':['LOSS_BEATS','GAIN_LAGS','UNKNOWN'],
                         'horizon':[21]*3,'ret':[-.05,.03,np.nan],'spy_ret':[-.10,.05,0.],
                         'excess_spy':[.05,-.02,np.nan],'price_basis':['adjusted']*3,'lane':['buy']*3})

class LabelContractTests(unittest.TestCase):
    def test_hit_is_relative_not_absolute(self):
        out = OWNER.build_labels(frame=fixture()).frame.set_index('ticker')
        self.assertTrue(out.loc['LOSS_BEATS','hit'])
        self.assertFalse(out.loc['GAIN_LAGS','hit'])
    def test_unknown_is_not_a_loss(self):
        out = OWNER.build_labels(frame=fixture()).frame.set_index('ticker')
        self.assertTrue(pd.isna(out.loc['UNKNOWN','hit']))
    def test_entry_and_confidence_remain_deferred(self):
        out = OWNER.build_labels(frame=fixture())
        self.assertEqual(set(out.receipt['deferred_heads']), {'entry','confidence'})
    def test_mixed_price_bases_are_refused(self):
        d = fixture(); d.loc[1,'price_basis'] = 'unadjusted'
        with self.assertRaises(OWNER.PriceBasisPoolRefusal):
            OWNER.assert_poolable(OWNER.build_labels(frame=d))
    def test_empty_frame_is_refused(self):
        with self.assertRaises(OWNER.StoreEmptyRefusal):
            OWNER.build_labels(frame=fixture().iloc[:0])
    def test_disclosed_null_era_is_excluded(self):
        d = fixture(); d.loc[0,'as_of'] = '2026-08-04'
        out = OWNER.build_labels(frame=d)
        self.assertNotIn('LOSS_BEATS', set(out.frame.ticker))
        self.assertEqual(out.receipt['era_hygiene']['rows_excluded'], 1)

def git_blob(path):
    b = path.read_bytes()
    return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, required=True)
    args, rest = parser.parse_known_args()
    path = args.repo_root/'scripts/prophet_fusion_labels.py'
    assert git_blob(path)=='6f18763a30b14b28980a8140aeb8b9dd485855fb', 'Reviewed label source changed'
    gap = args.repo_root/'data/us_board_ledger/disclosed_gaps.json'
    assert git_blob(gap)=='3881c93009d169fe953d79e142715afff1f7ba8e', 'Reviewed gap metadata changed'
    spec = importlib.util.spec_from_file_location('verified_label_owner', path)
    OWNER = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = OWNER
    spec.loader.exec_module(OWNER)
    unittest.main(argv=[sys.argv[0]]+rest, verbosity=2)
