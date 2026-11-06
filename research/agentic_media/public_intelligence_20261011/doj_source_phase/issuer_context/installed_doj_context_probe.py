"""Portable historical DOJ/issuer-context checks; no provider or public effects.

Prepared against a candidate manifest. Passing this probe does not establish
independent review, protected landing, publication rights or D14 credit.
Run with python -B, the installed repository, and a reviewed source manifest.
"""
import contextlib
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

root = Path(sys.argv[1]).resolve()
expected = json.loads(Path(sys.argv[2]).read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
checked = {rel: sha(root / rel) for rel in expected}
assert checked == expected, 'candidate source manifest drift'
sys.path.insert(0, str(root))
from engine.press import desk_planner as P
from engine.press.official_feed_candidate import plan_official_feed_candidate
from scripts import stage_official_feed_press as S
from tests import press_fixtures as F

def head():
    return subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
def snapshot():
    paths = [root / 'config/press.yml', root / 'data/press/published.jsonl',
             root / 'data/debt_maturity/cache/CIK0000064803.json',
             root / 'data/edgar/ticker_cik_ledger.json']
    paths += list((root / 'data/press/staging').glob('*.json'))
    paths += list((root / 'content/seo/blog').glob('*.md'))
    return {str(p.relative_to(root)): sha(p) for p in paths if p.is_file()}

before_head, before = head(), snapshot()
evidence = root / 'research/agentic_media/public_intelligence_20261011/doj_source_phase'
q0 = json.loads((evidence / 'cvs_candidate.json').read_text())
controls = []
clock = datetime(2026, 10, 14, 4, tzinfo=timezone.utc)
with tempfile.TemporaryDirectory(prefix='mmx-doj-context-probe-') as directory:
    tmp = Path(directory)
    fixture = F.fixture_root(tmp / 'fixture')
    (fixture / 'site/stocks').mkdir(parents=True, exist_ok=True)
    (fixture / 'site/stocks/CVS.html').write_text('<html>Historical fixture</html>')
    cfg = P.load_config(fixture)
    qualification = tmp / 'qualification.json'
    def args(q):
        qualification.write_text(json.dumps(q, sort_keys=True))
        return dict(feed_path=evidence / 'rss.xml', feed_sha256=q['feed_sha256'],
                    qualification_path=qualification, qualification_sha256=sha(qualification),
                    release_path=evidence / 'release.html', policy_path=evidence / 'policy.html')
    def plan(q):
        return plan_official_feed_candidate(**args(q), root=fixture, cfg=cfg, as_of=clock.isoformat())
    def refuses(q, match):
        try:
            plan(q)
        except ValueError as error:
            assert match in str(error), str(error)
        else:
            raise AssertionError('invalid source/context admitted')

    plain = plan(q0)
    assert plain['allow_stage'] is plain['allow_emit'] is plain['publication_approved'] is False
    assert len(plain['source_revisions']) == 3
    assert any('no determination of liability' in f['text'] for f in plain['validation_context']['facts'])
    assert 'https://www.mastermind-x.com/stocks/CVS.html' in plain['validation_context']['allowed_links']
    controls.append('retained-doj-release-policy-qualifier-and-existing-stock-link')

    for key, value, match in [('release_sha256', '0' * 64, 'hash'),
                              ('policy_sha256', '0' * 64, 'hash'),
                              ('source_qualifiers', [], 'qualifiers'),
                              ('published_at', '2026-10-13T13:00:00+00:00', 'clock')]:
        q = copy.deepcopy(q0); q[key] = value
        refuses(q, match)
    controls.append('release-policy-qualifier-and-publisher-clock-refusals')

    period = dict(end='2025-12-31', accn='0000064803-26-000010', fy=2025,
                  fp='FY', form='10-K', filed='2026-02-10')
    facts = {}
    def fact(tag, value, duration=False):
        row = dict(period, val=value)
        if duration:
            row['start'] = '2025-01-01'
        facts[tag] = {'units': {'USD': [row]}}
    fact('CashAndCashEquivalentsAtCarryingValue', 8453000000)
    fact('NetCashProvidedByUsedInOperatingActivities', 10639000000, True)
    fact('PaymentsToAcquirePropertyPlantAndEquipment', 2832000000, True)
    for tag, value in [('LongTermDebtMaturitiesRepaymentsOfPrincipalInNextTwelveMonths', 4007),
                       ('LongTermDebtMaturitiesRepaymentsOfPrincipalInYearTwo', 3379),
                       ('LongTermDebtMaturitiesRepaymentsOfPrincipalInYearThree', 5008),
                       ('LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFour', 3758),
                       ('LongTermDebtMaturitiesRepaymentsOfPrincipalInYearFive', 4258),
                       ('LongTermDebtMaturitiesRepaymentsOfPrincipalAfterYearFive', 43299)]:
        fact(tag, value * 1000000)
    cache = {'cik': 64803, 'fetched_at': '2026-09-23T08:01:58+00:00', 'facts': {'us-gaap': facts}}
    cache_path = fixture / 'data/debt_maturity/cache/CIK0000064803.json'
    identity_path = fixture / 'data/edgar/ticker_cik_ledger.json'
    def dump(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True))
        return sha(path)
    q = copy.deepcopy(q0)
    q['issuer_baseline_context'] = dict(ticker='CVS', cik='0000064803',
        cache_sha256=dump(cache_path, cache),
        identity_sha256=dump(identity_path, {'tickers': {'CVS': {'cik': '0000064803'}}}),
        event_quantity_literal='$315 million', relevance='Historical synthetic comparison, no current-liquidity inference.')
    with_context = plan(q)
    issuer = {f['id']: f for f in with_context['validation_context']['facts'] if f.get('id', '').startswith('issuer_')}
    assert len(issuer) == 10 and len(with_context['source_revisions']) == 9
    assert all(f['tier'] == 'third_party' and f['dated'] == '2025-12-31' for f in issuer.values())
    assert all(f['period']['filed'] == '2026-02-10' for f in issuer.values())
    for key, value in [('fcf', '7807000000.0'), ('cover', '210.96'), ('near_share', '6.29'),
                        ('event_cash', '3.73'), ('event_fcf', '4.03')]:
        assert issuer['issuer_CVS_' + key]['values'] == [value]
    assert 'not current liquidity' in issuer['issuer_CVS_event_cash']['text']
    controls.append('historical-external-arithmetic-and-filing-clocks')

    with patch.object(S.writer, 'write', side_effect=AssertionError('provider reached')) as writer:
        with contextlib.redirect_stdout(io.StringIO()):
            refusal = S.stage_official_feed_candidate(fixture, cfg, **args(q), now=clock)
        assert not refusal['staged'] and 'first-party' in refusal['reason'] and writer.call_count == 0
    assert not list((fixture / 'data/press/staging').glob('*.json'))
    controls.append('external-context-refused-before-provider-and-reservation')

    wrong = copy.deepcopy(q)
    wrong['issuer_baseline_context']['event_quantity_literal'] = '$315 billion'
    refuses(wrong, 'unqualified')
    controls.append('unreviewed-event-magnitude-refused')
    wrong_cache = copy.deepcopy(cache); wrong_cache['cik'] = 123
    wrong = copy.deepcopy(q); wrong['issuer_baseline_context']['cache_sha256'] = dump(cache_path, wrong_cache)
    refuses(wrong, 'CIK mismatch')
    controls.append('rebound-wrong-issuer-refused')
    wrong_cache = copy.deepcopy(cache); wrong_cache['fetched_at'] = '2026-10-14T23:00:00Z'
    wrong['issuer_baseline_context']['cache_sha256'] = dump(cache_path, wrong_cache)
    refuses(wrong, 'acquisition clock')
    controls.append('same-day-future-acquisition-refused')
    dump(cache_path, cache)
    outside = tmp / 'outside-identity.json'; outside.write_bytes(identity_path.read_bytes())
    identity_path.unlink(); identity_path.symlink_to(outside)
    refuses(q, 'symlink')
    controls.append('identity-symlink-refused')

assert before == snapshot() and before_head == head()
assert checked == {rel: sha(root / rel) for rel in expected}
print(json.dumps({'probe_passed': True, 'head': before_head, 'controls': controls,
    'execution_location': 'installed_vps' if root == Path('/opt/macro') else 'local_source',
    'checked_source_sha256': checked, 'real_provider_calls': 0,
    'production_inputs_unchanged': True, 'production_staging_writes': 0,
    'public_writes': 0, 'd14_credit': 0,
    'scope': 'Historical isolated fixtures; no independent review or release acceptance'}, indent=2))
