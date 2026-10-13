"""In-memory forbidden-mutation proof; does not change production templates."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import jinja2
from engine.i18n import tr
import scripts.build_site as bs


def run() -> None:
    paths = ['templates/_prophet_card.html.j2', 'templates/_us_prophet_plan_cards.html.j2']
    original = {p: (ROOT / p).read_text() for p in paths}
    before = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    spec = importlib.util.spec_from_file_location('record_trust_existing_test', ROOT / 'tests/test_p_mp1_shell_stance_projection.py')
    assert spec is not None and spec.loader is not None
    tests = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tests)
    plan = tests._record_plan(lifecycle_state='resolved', closed=True)
    episodes = {plan['id']: {'ep': 1, 'eps': 2, 'dopen_en': 'Aug 12', 'dopen_zh': '8月12日', 'newer': 'CVCO-BULL-20260915'}}

    def render(src: dict[str, str]) -> str:
        env = jinja2.Environment(loader=jinja2.DictLoader({Path(k).name: v for k, v in src.items()}))
        env.globals.update(us_stance_projection=bs.us_stance_projection, tr=tr)
        return env.get_template('_us_prophet_plan_cards.html.j2').render(items=[plan], cand_map={}, trg_map={}, episode_map=episodes)

    def invariant(html: str, key: str) -> bool:
        if key == 'record_mode':
            return 'data-record-only="1"' in html
        if key == 'original_zone':
            return 'Original zone' in html
        if key == 'attached_identity':
            return 'Cavco Industries' in html
        if key == 'no_nested_anchors':
            parser = tests._RecordAnchorAudit()
            parser.feed(html)
            return not parser.nested
        raise ValueError(key)

    mutations = [
        ('record_mode', paths[1], "'record_only': true", "'record_only': false"),
        ('original_zone', paths[0], "t('Original zone','原始区间')", "t('Zone','买区')"),
        ('attached_identity', paths[1], "_name_field.get('state') == 'available'", "_name_field.get('state') == 'never_available'"),
        ('no_nested_anchors', paths[0], '{% if _record_only %}<article{% else %}<a{% endif %}', '{% if _record_only %}<a{% else %}<a{% endif %}'),
    ]
    base_html = render(original)
    results = []
    for key, path, old, new in mutations:
        assert invariant(base_html, key), 'baseline not green: ' + key
        assert original[path].count(old) == 1, 'mutation seam mismatch: ' + key
        changed = dict(original)
        changed[path] = changed[path].replace(old, new)
        assert not invariant(render(changed), key), 'forbidden mutation survived: ' + key
        results.append({'mutation': key, 'baseline': True, 'mutant_rejected': True, 'failure_kind': 'intended output invariant; no template or collection error'})
        print('MUTATION_KILLED', key, flush=True)
    assert before == {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    receipt = {'scope': 'in-memory actual-template mutation proof; production files unchanged', 'status': 'PASS', 'source_sha256': before, 'mutations': results, 'source_unchanged': True, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    Path(__file__).with_name('mutation-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('MUTATIONS', len(results), 'PASS', flush=True)


if __name__ == '__main__':
    run()
