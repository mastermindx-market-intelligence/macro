"""Atlas's pure suites must execute through the incumbent code-pack manifest."""
from pathlib import Path
import yaml


def test_basket_suites_are_enrolled_in_existing_options_code_group():
    root=Path(__file__).resolve().parents[1]
    jobs=yaml.safe_load((root/'.github/ci/legacy-jobs.yml').read_text())['jobs']
    job=jobs['options-skew-engine']
    assert job['gate']=='code'
    required={
        '.github/ci/legacy-jobs.yml',
        'engine/options_basket_aggregation.py',
        'engine/options_basket_inputs.py',
        'tests/test_options_basket_aggregation.py',
        'tests/test_options_basket_inputs.py',
        'tests/test_options_basket_ci.py',
        'research/factor_atlas/session3/reproduce_native_scenarios.py',
    }
    assert required.issubset(set(job['paths'])), 'Atlas paths are dark to the existing code selector'
    steps=[s for s in job['steps'] if s.get('name')=='Factor Atlas basket options qualification and sparse-data guards']
    assert len(steps)==1
    command=steps[0]['run']
    assert 'python -m pytest' in command
    for path in sorted(p for p in required if p.startswith('tests/')):
        assert path in command, f'{path} is not actually executed'
    assert 'python -m research.factor_atlas.session3.reproduce_native_scenarios' in command
