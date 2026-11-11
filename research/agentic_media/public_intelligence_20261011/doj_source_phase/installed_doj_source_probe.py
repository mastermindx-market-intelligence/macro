"""Portable historical reviewed-DOJ source checks; no provider or public effects.

Uses a reviewed source manifest. Passing this probe does not establish
protected landing, publication approval or D14 credit.
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
assert checked == expected, 'reviewed source manifest drift'
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

    assert all(f['tier'] == 'third_party' for f in plain['validation_context']['facts'])
    with patch.object(S.writer, 'write', side_effect=AssertionError('provider reached')) as writer:
        with contextlib.redirect_stdout(io.StringIO()):
            refusal = S.stage_official_feed_candidate(fixture, cfg, **args(q0), now=clock)
        assert not refusal['staged'] and 'first-party' in refusal['reason'] and writer.call_count == 0
    assert not list((fixture / 'data/press/staging').glob('*.json'))
    controls.append('source-only-refused-before-provider-and-reservation')
    q = copy.deepcopy(q0); q['publication_approved'] = True
    refuses(q, 'candidate qualification')
    controls.append('qualification-cannot-grant-publication')
    (fixture / 'site/stocks/CVS.html').unlink()
    refuses(q0, 'existing dossier')
    controls.append('missing-canonical-dossier-refused')

assert before == snapshot() and before_head == head()
assert checked == {rel: sha(root / rel) for rel in expected}
print(json.dumps({'probe_passed': True, 'head': before_head, 'controls': controls,
    'execution_location': 'installed_vps' if root == Path('/opt/macro') else 'local_source',
    'checked_source_sha256': checked, 'real_provider_calls': 0,
    'production_inputs_unchanged': True, 'production_staging_writes': 0,
    'public_writes': 0, 'd14_credit': 0,
    'scope': 'Historical isolated source fixtures; no release or publication acceptance'}, indent=2))
