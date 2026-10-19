"""Read-only installed-code probe using isolated fixtures and zero provider calls."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1]).resolve()
expected = json.loads(Path(sys.argv[2]).read_text())
sys.path.insert(0, str(root))
from engine.press import validators as V, writer as W, desk_planner as P
from scripts import run_press as R


def head():
    return subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()


def fingerprint():
    files = [root / 'config/press.yml', root / 'data/press/published.jsonl']
    files += sorted((root / 'data/press/staging').glob('*.json'))
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            if p.is_file() else None for p in files}


for name in ('engine/press/validators.py', 'scripts/run_press.py'):
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected[name], name
before_head, before_inputs = head(), fingerprint()
assert V.check_markup_safety({'body_html': '<p>Static <strong>article</strong> text.</p>'}, {}, {})['ok']
refusals = ['<script>unsafe()</script>', '<p onclick="unsafe()">x</p>',
            '<a href="java&#10;script:unsafe()">x</a>', '<svg><script>x</script></svg>',
            '<p style="display:none">x</p>', '<p title="unfinished',
            '<a href="/blog/" href="javascript:x">x</a>', '<p><em>x</p></em>']
for body in refusals:
    assert not V.check_markup_safety({'body_html': body}, {}, {})['ok'], body
calls = []
with tempfile.TemporaryDirectory(prefix='mmx-installed-safety-') as temporary:
    fixture = Path(temporary)
    cfg = P.load_config(root)
    desk = cfg['desks']['brief']
    slot = {**desk, 'desk': 'brief', 'id': 'press-brief-2000-01-01-static-proof',
            'as_of': '2000-01-01', 'seed_refs': ['fixture:markup'],
            'sources': ['fixture:markup'], 'facts': [], 'raw_documents': [],
            'story': {'kind': 'fixture', 'title_hint': 'Static proof'},
            'primary_source': {'kind': 'first_party'}, 'allowed_links': []}
    original = R.writer.write
    draft = {'title': 'Invalid private fixture', 'description': 'short',
             'slug': 'static-proof', 'body_html': '<p>Fixture only.</p><script>unsafe()</script>'}
    def fake_writer(*args, **kwargs):
        calls.append(kwargs.get('single_provider_attempt'))
        return {'ok': True, 'draft': dict(draft), 'provider': 'mock', 'model': 'mock', 'state': {}}
    try:
        R.writer.write = fake_writer
        with contextlib.redirect_stdout(io.StringIO()):
            summary = R._stage_preplanned_slots(fixture, cfg, slots=[slot],
                staging_dir=fixture/'data/press/staging', run_date='2000-01-01',
                state=W.RunState(), max_regenerations=0, taken_slugs=set(),
                single_provider_attempt=True)
            item = json.loads((fixture/'data/press/staging'/f"{slot['id']}.json").read_text())
            assert summary['quarantined'] == 1 and calls == [True]
            assert item['status'] == 'quarantined' and item['draft']['body_html'] == draft['body_html']
            assert 'markup_safety' in item['validator_report']['failed']
            assert item['retained_draft_attempt'] == 0 and item['provider'] == 'mock'
            snapshot = {str(p.relative_to(fixture)): p.read_bytes() for p in fixture.rglob('*') if p.is_file()}
            assert R.run_emit(fixture, cfg)['emitted'] == 0
            assert snapshot == {str(p.relative_to(fixture)): p.read_bytes() for p in fixture.rglob('*') if p.is_file()}
    finally:
        R.writer.write = original
assert head() == before_head and fingerprint() == before_inputs
print(json.dumps({'accepted': True, 'head': before_head, 'safe_fragment': True,
                  'markup_refusals': len(refusals), 'quarantined_draft_and_report_retained': True,
                  'fixture_emit_refused': True, 'production_inputs_unchanged': True,
                  'provider_calls': 0, 'fixture_writer_calls': len(calls),
                  'production_stage_writes': 0, 'public_writes': 0}))
