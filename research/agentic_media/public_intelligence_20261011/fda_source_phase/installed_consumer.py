"""Portable consumer proof on retained FDA bytes, never a current story attempt.

Usage: python -B installed-fda-consumer.py SOURCE_ROOT RETAINED_EVIDENCE
Requires no pytest, network, credentials, provider call or production fixture.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

source, evidence = [Path(p).resolve() for p in sys.argv[1:3]]
sys.dont_write_bytecode = True
sys.path.insert(0, str(source))
expected = {
    'engine/press/fda_document.py': '8df3567cd3a65b73ef064d6ecf9b037388d76f1466c5ba26b0caa791c6cce47f',
    'engine/press/official_feed_candidate.py': '2a0f9644017922847bdf9aaa5fe0105a54d8c904d797d4dbfff80858acc8cbef',
}
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert all(digest(source / p) == h for p, h in expected.items()), 'source drift'
head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
from tests import press_fixtures as F
from engine.press.official_feed_candidate import plan_official_feed_candidate

names = ('drugs.xml', 'release.html', 'policy.html', 'candidate-qualification.json')
inputs = {name: (evidence / name).read_bytes() for name in names}
original = json.loads(inputs['candidate-qualification.json'])
assert hashlib.sha256(inputs['drugs.xml']).hexdigest() == original['feed_sha256']
assert hashlib.sha256(inputs['release.html']).hexdigest() == original['release_sha256']
assert hashlib.sha256(inputs['policy.html']).hexdigest() == original['policy_sha256']

def production_snapshot():
    paths = [source / 'config/press.yml', source / 'data/press/published.jsonl']
    paths += list((source / 'data/press/staging').glob('*.json'))
    paths += list((source / 'content/seo/blog').glob('*.md'))
    return {str(p): digest(p) for p in paths if p.is_file()}

before = production_snapshot()
controls = []
protected = False
with tempfile.TemporaryDirectory(prefix='mmx-fda-consumer-') as temporary:
    temp = Path(temporary).resolve()
    root = F.fixture_root(temp / 'root')
    (root / 'site/stocks').mkdir(parents=True, exist_ok=True)
    (root / 'site/stocks/IBRX.html').write_text('Isolated dossier inventory fixture')
    for name, raw in inputs.items():
        (temp / name).write_bytes(raw)
    qpath = temp / 'candidate-qualification.json'

    def audit(event, args):
        if not protected:
            return
        if event in {'socket.connect', 'socket.getaddrinfo', 'os.system'}:
            raise RuntimeError('consumer proof forbids network/process effects')
        if event == 'subprocess.Popen':
            executable, argv, cwd, _ = args
            if executable == 'git' and list(argv) == ['git', 'ls-files', '-z', '--', str(root / 'site/stocks')] and cwd == str(root / 'site/stocks'):
                return
            raise RuntimeError('consumer proof forbids subprocess effects')
        if event == 'open':
            name, mode, flags = args
            writing = (isinstance(mode, str) and any(c in mode for c in 'wax+')) or flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            if writing and (not isinstance(name, (str, bytes)) or not Path(name).resolve().is_relative_to(temp)):
                raise RuntimeError('consumer proof forbids production writes')
        if event in {'os.remove', 'os.rename', 'os.mkdir', 'os.rmdir'}:
            raise RuntimeError('consumer proof forbids filesystem mutations')

    sys.addaudithook(audit)
    protected = True
    try:
        def invoke(patch=None, missing=None):
            q = copy.deepcopy(original)
            q.update(patch or {})
            qpath.write_text(json.dumps(q))
            return plan_official_feed_candidate(
                feed_path=temp / 'drugs.xml', feed_sha256=q['feed_sha256'],
                qualification_path=qpath, qualification_sha256=digest(qpath), root=root,
                as_of='2026-10-15T18:17:57+00:00',  # historical fixture clock only
                release_path=None if missing == 'release' else temp / 'release.html',
                policy_path=None if missing == 'policy' else temp / 'policy.html')

        plan = invoke()
        ctx = plan['validation_context']
        assert plan['source_ref'] == 'official_feed:636285888d44b4942b08620916c6c07b6bd3af77'
        assert len(ctx['raw_documents'][0]['text']) == 4178
        assert all(s in ctx['raw_documents'][0]['text'] for s in original['source_qualifiers'])
        controls.append('original-identity-full-body-and-cohort-warning-scope')
        assert all(f['tier'] == 'third_party' for f in ctx['facts'])
        assert all(plan[k] is False for k in ('allow_stage', 'allow_emit', 'publication_approved'))
        assert plan['operation'] == 'planning_only' and plan['cadence_consumed'] is False
        controls.append('source-only-cannot-admit-stage-publish-or-consume-cadence')

        negatives = [
            ('missing-release', {}, 'release'),
            ('missing-policy', {}, 'policy'),
            ('changed-release-digest', {'release_sha256': '0' * 64}, None),
            ('changed-policy-digest', {'policy_sha256': '0' * 64}, None),
            ('unrelated-issuer', {'reviewed_tickers': {'IBRX': 'Unrelated issuer'}}, None),
            ('stage-self-admission', {'allow_stage': True}, None),
            ('emit-self-admission', {'allow_emit': True}, None),
            ('publication-self-admission', {'publication_approved': True}, None),
            ('missing-source-qualifiers', {'source_qualifiers': []}, None),
            ('changed-event-date', {'event_date': '2026-10-13'}, None),
        ]
        for name, patch, missing in negatives:
            try:
                invoke(patch, missing)
            except ValueError:
                controls.append(name)
            else:
                raise AssertionError('expected source refusal: ' + name)
    finally:
        protected = False

assert before == production_snapshot()
assert inputs == {name: (evidence / name).read_bytes() for name in names}
assert head == subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
assert all(digest(source / p) == h for p, h in expected.items())
print(json.dumps({'accepted': True, 'head': head, 'controls': controls,
    'source_hashes': expected, 'retained_source_ref': plan['source_ref'],
    'execution_location': 'installed_vps' if source == Path('/opt/macro') else 'local_source',
    'production_inputs_unchanged': True, 'retained_inputs_unchanged': True,
    'real_provider_calls': 0, 'production_staging_writes': 0, 'public_writes': 0,
    'scope': 'Historical isolated consumer proof; no live source, writer or publication admission'}, indent=2))
