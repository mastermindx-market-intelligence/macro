"""Bounded local proof only: real committed input, stubbed model, actual producer/renderer."""
from __future__ import annotations
import copy, hashlib, json, sys, subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
PIN = 'a4d33f32dad140acdfa081b21f55ad6d8dcb94d4'
BASE: Path
sys.path.insert(0, str(ROOT))
from engine import master_brain as mb, i18n
from jinja2 import Environment, FileSystemLoader

def blob(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', PIN + ':' + path])

def digest(data):
    return hashlib.sha256(data).hexdigest()

def render_case(name, raw, response, reference_time=None):
    destination = BASE / name
    destination.mkdir(parents=True, exist_ok=True)
    data = destination / 'data'
    (data / 'regime').mkdir(parents=True, exist_ok=True)
    site = destination / 'site'
    site.mkdir(exist_ok=True)
    selected = mb._macro_summary(raw, root=None)
    selected['regime_path'] = mb._build_regime_path(raw, root=None, reference_time=reference_time)
    state = {'macro': selected, 'neural_web': {}}
    fixture = copy.deepcopy(response)
    fixture['regime_evidence'] = {'en': 'MODEL_AUTHORED_OVERRIDE', 'zh': 'MODEL_AUTHORED_OVERRIDE'}
    with patch.dict(mb.LENSES['macro'], {'state_fn': lambda root: state}), \
         patch.object(mb, '_cfg', return_value={'enabled': True}), \
         patch.object(mb, 'synthesize', return_value=fixture) as model, \
         patch.object(mb, '_translate_brief', return_value=None) as translator, \
         patch.object(mb, '_append_ledger', return_value=None) as ledger:
        brief = mb.run(persist=True, root=destination, force=True, lens='macro')
    assert isinstance(brief, dict) and isinstance(brief.get('regime_evidence'), dict)
    assert 'MODEL_AUTHORED_OVERRIDE' not in json.dumps(brief['regime_evidence'])
    assert model.call_count == 1 and translator.call_count == 1 and ledger.call_count == 1
    saved = json.loads((site / 'master_brief.json').read_text())
    assert saved['regime_evidence'] == brief['regime_evidence']
    assert not (data / 'master_brain' / 'theses.jsonl').exists()
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=False)
    env.globals.update(td=i18n.td, tr=i18n.tr, t=i18n.t)
    page = env.get_template('aibrief.html.j2').render(
        as_of='LOCAL PROOF — no production generation', master_brief=saved,
        china_brief=None, btc_brief=None,
        ctx_strip={'absent': True},
        fwd_panel={'absent': True, 'events': [], 'rebal_note_en': None, 'rebal_note_zh': None},
        record_panel={'absent': True})
    (site / 'aibrief.html').write_text(page)
    for asset in ('theme.css', 'theme.js', 'aibrief.js'):
        (site / asset).write_bytes((ROOT / 'templates' / asset).read_bytes())
    return {'case': name, 'site': str(site), 'reference_time': reference_time,
            'context': selected['regime_path'].get('probability_context'),
            'regime_evidence': saved['regime_evidence'], 'page_sha256': digest(page.encode()),
            'model_response_is_fixture': True, 'translation_stubbed': True,
            'thesis_append_intercepted': True, 'production_adoption': False}

def main():
    import argparse
    global BASE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True,
                        help='New empty directory outside this checkout; never a production data directory')
    args = parser.parse_args()
    BASE = args.output_root.resolve()
    if BASE == ROOT or ROOT in BASE.parents or BASE.exists():
        parser.error('output-root must be a new directory outside the checkout')
    BASE.mkdir(parents=True)
    raw_bytes = blob('data/regime/latest.json')
    brief_bytes = blob('data/regime/master_brief.json')
    raw, response = json.loads(raw_bytes), json.loads(brief_bytes)
    cases = [render_case('real_committed_input', raw, response)]
    disagreement = copy.deepcopy(raw)
    disagreement['quad_vector']['p'] = {'Q1': .6, 'Q2': .2, 'Q3': .1, 'Q4': .1}
    disagreement['quad_vector']['hard_label_agrees'] = False
    cases.append(render_case('fixture_disagreement', disagreement, response, '2026-09-09T00:00:00Z'))
    unavailable = copy.deepcopy(raw)
    unavailable['quad_vector']['p']['Q1'] = True
    cases.append(render_case('fixture_invalid', unavailable, response))
    missing = copy.deepcopy(raw)
    missing.pop('quad_vector', None)
    cases.append(render_case('fixture_missing', missing, response))
    evidence = {'input_pin': PIN, 'input_sha256': digest(raw_bytes),
                'response_fixture_sha256': digest(brief_bytes),
                'source_files': {p: digest((ROOT / p).read_bytes()) for p in (
                    'engine/master_brain.py', 'templates/_aibrief_body.html.j2')},
                'cases': cases, 'production_adoption': False,
                'scope': 'Real reader + actual saved-output code + real full template; model/translation/ledger mocked. Existing saved prose is a fixture, not newly generated wording or a model-quality result.'}
    (BASE / 'local_consumer_proof.json').write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(evidence, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
