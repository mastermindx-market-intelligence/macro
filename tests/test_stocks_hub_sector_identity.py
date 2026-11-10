"""S&P consumer identity joins must precede summary and treemap aggregation."""
import copy
import unittest

from engine.market_heatmap import page_summary
from engine.spotlight import GICS_TO_ETF
from engine.stocks_hub import normalize_us_sector_payload, sector_ledger, treemap


def payload():
    return {'asof': '2026-11-06', 'default_tf': '1D', 'size_basis': 'marketcap',
            'timeframes': [{'key': '1D', 'available': True}],
            'sectors': [{'key': 'Healthcare', 'en': 'Healthcare', 'zh': '医疗保健'},
                        {'key': 'Health Care', 'en': 'Health Care', 'zh': '医疗保健'},
                        {'key': 'Technology', 'en': 'Technology', 'zh': '信息技术'}],
            'tiles': [{'t': 'A', 'sector': 'Healthcare', 'subindustry': 'Medical', 'size': 100, 'perf': {'1D': -1}},
                      {'t': 'B', 'sector': 'Health Care', 'size': 1, 'perf': {'1D': 10}},
                      {'t': 'C', 'sector': 'Technology', 'size': 100, 'perf': {'1D': 2}}]}


class SectorIdentityTests(unittest.TestCase):
    def test_real_consumers_join_before_weighting(self):
        p = payload()
        self.assertEqual(page_summary(p)['top']['en'], 'Health Care')
        q = normalize_us_sector_payload(p)
        summary = page_summary(q)
        self.assertEqual(len(summary['sectors']), 2)
        self.assertEqual(summary['top']['en'], 'Information Technology')
        self.assertEqual(summary['top']['pc'], '+2.00%')
        self.assertEqual(summary['bot']['pc'], '−0.89%')
        self.assertEqual(len(sector_ledger(summary)), 2)
        self.assertEqual(len(treemap(q)['sectors']), 2)

    def test_source_observations_and_other_summary_fields_preserved(self):
        p = payload(); before = copy.deepcopy(p)
        q = normalize_us_sector_payload(p)
        self.assertEqual(p, before)
        for a, b in zip(p['tiles'], q['tiles']):
            self.assertEqual({k:v for k,v in a.items() if k != 'sector'},
                             {k:v for k,v in b.items() if k != 'sector'})
        a, b = page_summary(p), page_summary(q)
        for key in ('tf', 'asof', 'n_tiles', 'pct_up', 'median', 'breadth', 'gainers', 'losers'):
            self.assertEqual(a[key], b[key], key)

    def test_all_established_aliases_have_eleven_identities(self):
        p = {'tiles': [{'sector': s} for s in GICS_TO_ETF]}
        q = normalize_us_sector_payload(p)
        self.assertEqual(len({t['sector'] for t in q['tiles']}), 11)
        for a,b in zip(p['tiles'], q['tiles']):
            self.assertEqual(GICS_TO_ETF[a['sector']], GICS_TO_ETF[b['sector']])

    def test_partial_labels_retain_translation(self):
        p = {'sectors': [{'key': 'Healthcare', 'en': 'Healthcare', 'zh': '医疗保健'}],
             'tiles': [{'sector': 'Health Care'}]}
        self.assertEqual(normalize_us_sector_payload(p)['sectors'],
                         [{'key': 'Health Care', 'en': 'Health Care', 'zh': '医疗保健'}])

    def test_unknown_labels_not_absorbed(self):
        p = {'tiles': [{'sector': 'Unknown'}, {'sector': 'Internet & Tech'}]}
        self.assertEqual(normalize_us_sector_payload(p)['tiles'], p['tiles'])

    def test_idempotent_and_empty(self):
        q = normalize_us_sector_payload(payload())
        self.assertEqual(normalize_us_sector_payload(q), q)
        self.assertIsNone(normalize_us_sector_payload(None))
        self.assertEqual(normalize_us_sector_payload({}), {})

    def test_shared_international_summary_is_not_normalized(self):
        p = payload(); p['market'] = 'china'
        self.assertEqual(len(page_summary(p)['sectors']), 3)


if __name__ == '__main__':
    unittest.main()
