"""The new source and browser tests must run in the existing Brain code gate."""
from pathlib import Path

import pytest
import yaml

from scripts import run_ci_pack

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / '.github/ci/legacy-jobs.yml'


@pytest.mark.parametrize('suite', ['tests/test_brain_visuals.py', 'tests/test_brain_visuals_review.py', 'tests/test_brain_visuals_integration.py', 'tests/test_brain_visuals_assets.py', 'tests/test_brain_visuals_browser.py', 'tests/test_brain_visuals_widget.py', 'tests/test_brain_visuals_ci_ownership.py'])
def test_native_illustration_suite_has_exactly_one_existing_code_gate_owner(suite):
    jobs = yaml.safe_load(MANIFEST.read_text())['jobs']
    owners = [(name, job.get('gate')) for name, job in jobs.items()
              for step in job.get('steps', []) if suite in str(step.get('run', ''))]
    assert owners == [('unrun-brain-gateway', 'code')]
    assert 'unrun-brain-gateway' in {job.job_id for job in run_ci_pack.load_legacy_jobs(MANIFEST, gate='code')}


@pytest.mark.parametrize('job', ['crypto-assistant-context', 'fif-kernel-guards', 'research-price-panel', 'ticker-news-qbus'])
def test_existing_exclusive_jobs_cover_the_new_transitive_module(job):
    definition = yaml.safe_load(MANIFEST.read_text())['jobs'][job]
    assert 'engine/neuralweb/brain_visuals.py' in definition['paths']
    assert definition['scope'] == 'exclusive' and definition['gate'] == 'code'
