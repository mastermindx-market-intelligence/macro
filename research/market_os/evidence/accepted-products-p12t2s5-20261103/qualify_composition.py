"""Current-base immutable source/normal-output qualification; no browser/transport."""
from pathlib import Path
from copy import deepcopy
import datetime
import hashlib
import json
import socket
import subprocess
import sys
from bs4 import BeautifulSoup
from jinja2 import Environment, meta

repo, out = map(Path, sys.argv[1:3])
sys.path.insert(0, str(repo))
network = []
def denied(*args, **kwargs):
    network.append('transport refused')
    raise AssertionError('No network in native composition qualification')
socket.socket.connect = socket.socket.connect_ex = socket.create_connection = socket.getaddrinfo = denied

def git(*args):
    return subprocess.check_output(['git', *args], cwd=repo)
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
preflight = json.loads((out / 'source-inputs-preflight.json').read_text())
base = preflight['base']
# Preserve every accepted source blob/mode. The sole test relocation is separately
# assertion-bound; its original source blob remains in immutable input history.
identities = {}
for family, source in preflight['sources'].items():
    rows = []
    for path in source['runtime']:
        if path == 'tests/test_macro_business_activity_depth.py':
            rows.append({'path': path, 'state': 'CI_RELOCATED_SAME_ASSERTION_AST', 'source_commit': source['head']})
            continue
        original = git('show', source['head'] + ':' + path)
        current = (repo / path).read_bytes() if (repo / path).is_file() else git('show', 'HEAD:' + path)
        assert current == original, (family, path)
        entry = git('ls-tree', 'HEAD', '--', path).decode().strip()
        original_entry = git('ls-tree', source['head'], '--', path).decode().strip()
        assert entry == original_entry, (family, path, entry, original_entry)
        rows.append({'path': path, 'git_entry': entry, 'sha256': sha(current), 'accepted_exact': True})
    identities[family] = rows

# Literal Jinja include/import closure is inspected once. Dynamic references remain
# explicit; native emission below is not replaced by an assumed static closure.
starts = {'Bonds': 'bonds.html.j2', 'Forensics': 'fundamental_forensics.html.j2',
          'BusinessActivity': 'macro_business_activity.html.j2', 'ChinaHub': 'china_intel.html.j2'}
closure = {}
for family, start in starts.items():
    pending = [start]; seen = set(); dynamic = []; changed = []
    source = preflight['sources'][family]
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        p = repo / 'templates' / name
        if not p.is_file():
            dynamic.append('unmaterialized:' + name)
            continue
        parsed = Environment().parse(p.read_text())
        for child in meta.find_referenced_templates(parsed):
            if child is None:
                dynamic.append('dynamic reference in ' + name)
            else:
                pending.append(child)
        path = 'templates/' + name
        old = subprocess.run(['git','show',source['preimage']+':'+path],cwd=repo,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        new = git('show', base + ':' + path)
        if old.returncode or old.stdout != new:
            changed.append(path)
    closure[family] = {'literal_template_paths': sorted(seen), 'dynamic_or_missing': dynamic,
                       'base_vs_accepted_preimage_dependency_drift': changed}

# Compare the CI dependency-free locator against the previous parser on the actual
# newly emitted 31-metric native page, without another native renderer/capture run.
from tests import test_macro_suite_pages as macro_tests
business_html = (repo / 'site/macro_business_activity.html').read_text()
old_cards = BeautifulSoup(business_html, 'html.parser').select('.mq-metric')
new_cards = macro_tests._business_document(business_html, 'html.parser').select('.mq-metric')
assert len(old_cards) == len(new_cards) == 31
for old, new in zip(old_cards, new_cards):
    a = [(r.select_one('dt .l-en').get_text(strip=True), r.select_one('dd').get_text(strip=True))
         for r in old.select('.mq-metric-meta > div')]
    b = [(r.select_one('dt .l-en').get_text(strip=True), r.select_one('dd').get_text(strip=True))
         for r in new.select('.mq-metric-meta > div')]
    assert a == b
try:
    macro_tests._business_document('', 'html.parser').select('.unsupported')
except ValueError:
    pass
else:
    raise AssertionError('Unsupported CI locator selector accepted')

# China has complete real frontend owner artifacts, so replay the exact production
# Jinja renderer. Do NOT call its bus producer or present this as normal full build.
from scripts.build_china_intel import _env
from lib.pages import write_unshimmed_html
braw = (out / 'retained/site/china_intel/briefing.json').read_bytes()
craw = (out / 'retained/site/china_intel/command.json').read_bytes()
briefing, command = json.loads(braw), json.loads(craw)
before = json.dumps([briefing, command], sort_keys=True)
html = _env().get_template('china_intel.html.j2').render(b=briefing, cmd_full=command)
assert json.dumps([briefing, command], sort_keys=True) == before
private = out / 'china-native-renderer-replay.html'
write_unshimmed_html(private, html)
assert (out / 'retained/site/china_intel/briefing.json').read_bytes() == braw
assert (out / 'retained/site/china_intel/command.json').read_bytes() == craw

record = {'base': base, 'composed_source_head': git('rev-parse','HEAD').decode().strip(),
          'accepted_source_blobs_and_modes': identities, 'template_dependency_closure': closure,
          'business_CI_locator': {'actual_native_metrics': 31, 'all_selected_metadata_names_and_text_equal_old_parser': True, 'unsupported_selectors_fail_closed': True},
          'ChinaHub': {'state': 'NATIVE_RENDERER_REPLAY_ONLY_NOT_BUS_BUILD',
                       'interface': 'scripts.build_china_intel._env().get_template(...).render(b,cmd_full)',
                       'input_briefing_sha256': sha(braw), 'input_command_sha256': sha(craw),
                       'output': str(private), 'output_sha256': sha(html.encode()),
                       'all_owner_payloads_unchanged': True, 'bus_or_collection_called': False,
                       'limitation': 'Private unshimmed source/semantic replay only; no tracked generated China page, full upstream producer emission, source download, browser or serving claim.'},
          'network_attempts': network, 'browser': 'HELD_NOT_RUN'}
assert not network
(out / 'composition-qualification.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'base':base,'accepted_runtime_exact':True,'closure_drift':{k:v['base_vs_accepted_preimage_dependency_drift'] for k,v in closure.items()},'dynamic':{k:v['dynamic_or_missing'] for k,v in closure.items()},'business_native_metadata_parity':31,'ChinaHub':record['ChinaHub'],'network_attempts':network},ensure_ascii=False,indent=2))
