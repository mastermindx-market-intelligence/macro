"""Static HTML and build-adapter tests, not browser/production acceptance."""
from __future__ import annotations
import copy
import importlib.util
import json
import runpy
import sys
from pathlib import Path
from types import ModuleType
import pytest
import yaml
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'research/reference_rethink_20260921'
spec=importlib.util.spec_from_file_location('shared_preview',HERE/'render_shared_preview.py')
preview=importlib.util.module_from_spec(spec);spec.loader.exec_module(preview)

@pytest.fixture
def manifest(): return runpy.run_path(str(ROOT/'tests/fixtures/market-guide/compile_fixture.py'))['manifest']()

def test_fixture_banner_is_explicit(manifest):
    soup=BeautifulSoup(preview.render_html(manifest,fixture_only=True),'html.parser')
    assert soup.select_one('[data-fixture-only="true"]')
    assert 'Not production data' in soup.select_one('.guide-scope-note').get_text()

def test_one_manifest_feeds_page_and_dialog(manifest):
    soup=BeautifulSoup(preview.render_html(manifest,fixture_only=True),'html.parser')
    assert len(soup.select('#guide-manifest'))==1
    assert json.loads(soup.select_one('#guide-manifest').string)==manifest
    assert soup.select_one('dialog[aria-labelledby="help-title"]')
    assert soup.select_one('#app[hidden]')

def test_nojs_fallback_contains_every_definition_reading_and_limitation(manifest):
    soup=BeautifulSoup(preview.render_html(manifest,fixture_only=True),'html.parser')
    for entry in manifest['entries']:
        fallback=soup.select_one('#fallback-'+entry['id']);text=fallback.get_text()
        for lang in ['en','zh']:
            assert entry['definition'][lang] in text
            assert entry['why'][lang] in text
            for item in entry['caveats'][lang]:assert item in text
            for reading in entry['presentation']['readings']:assert reading['text'][lang] in text
    assert soup.select_one('.fallback a')['href']=='https://fred.stlouisfed.org/series/VIXCLS'

def test_hostile_text_cannot_close_script_or_create_img(manifest):
    manifest['entries'][0]['label']['en']='</script><img src=x onerror=alert(1)>'
    soup=BeautifulSoup(preview.render_html(manifest,fixture_only=True),'html.parser')
    assert not soup.select('img')
    assert len(soup.select('script'))==2
    assert json.loads(soup.select_one('#guide-manifest').string)['entries'][0]['label']['en']==manifest['entries'][0]['label']['en']

def test_owner_evidence_absence_stops_before_source_validation(tmp_path,monkeypatch):
    raw=json.loads((ROOT/'tests/fixtures/market-guide/synthetic-source.json').read_text())
    (tmp_path/'config').mkdir();(tmp_path/'config/market_reference.yml').write_text(yaml.safe_dump(raw))
    owner=ModuleType('scripts.build_market_reference')
    owner.validate=lambda *a,**k:pytest.fail('missing owner pages must fail before this')
    owner.validate_coverage_exceptions=lambda *a,**k:[]
    monkeypatch.setitem(sys.modules,'scripts.build_market_reference',owner);monkeypatch.setattr(preview,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='Rendered owner pages missing'):preview.compile_from_canonical_source()

def test_build_adapter_calls_existing_owner_with_exact_repo_root(tmp_path,monkeypatch):
    raw=json.loads((ROOT/'tests/fixtures/market-guide/synthetic-source.json').read_text())
    (tmp_path/'config').mkdir();(tmp_path/'config/market_reference.yml').write_text(yaml.safe_dump(raw))
    (tmp_path/'site').mkdir()
    for name in ['macro.html','us_stocks.html']:(tmp_path/'site'/name).write_text('<main id="regime-radar"></main>')
    calls=[];owner=ModuleType('scripts.build_market_reference')
    def validate(data,repo_root):calls.append(('registry',repo_root));return data['entries']
    def coverage(data,entries):calls.append(('coverage',len(entries)));return data['coverage_exceptions']
    owner.validate=validate;owner.validate_coverage_exceptions=coverage
    monkeypatch.setitem(sys.modules,'scripts.build_market_reference',owner);monkeypatch.setattr(preview,'ROOT',tmp_path)
    result=preview.compile_from_canonical_source()
    assert calls==[('registry',tmp_path),('coverage',8)]
    assert len(result['entries'])==8

def test_review_cli_refuses_existing_output(tmp_path,monkeypatch):
    target=tmp_path/'existing.html';target.write_text('keep me')
    monkeypatch.setattr(sys,'argv',['render_shared_preview.py','--fixture-only','--output',str(target)])
    with pytest.raises(SystemExit):preview.main()
    assert target.read_text()=='keep me'

def test_review_cli_refuses_production_site_target(tmp_path,monkeypatch):
    monkeypatch.setattr(preview,'ROOT',tmp_path)
    target=tmp_path/'site/reference.html'
    monkeypatch.setattr(sys,'argv',['render_shared_preview.py','--fixture-only','--output',str(target)])
    with pytest.raises(SystemExit):preview.main()
    assert not target.exists()


def test_shared_guide_suites_run_in_existing_help_code_gate():
    """Enrollment must execute, not merely make the unrun-suite audit quiet."""
    jobs = yaml.safe_load((ROOT / '.github/ci/legacy-jobs.yml').read_text())['jobs']
    job = jobs['public-render-fastlane']
    assert job['gate'] == 'code'
    commands = [step.get('run', '') for step in job['steps']]
    python_step = next(cmd for cmd in commands if 'tests/test_market_guide.py' in cmd)
    assert python_step.strip() == (
        'python -m pytest tests/test_market_guide.py tests/test_market_guide_preview.py -q'
    )
    node_step = next(cmd for cmd in commands if 'tests/test_market_guide_client.cjs' in cmd)
    assert node_step.strip() == (
        'node --test tests/test_market_guide_client.cjs tests/test_market_guide_view.cjs'
    )
    assert any('beautifulsoup4' in cmd and cmd.startswith('pip install') for cmd in commands)
    assert not any(step.get('continue-on-error') for step in job['steps'])
    # Existing glossary/help contracts remain enrolled, not replaced by this feature.
    assert any('tests/test_help_directory.py' in cmd for cmd in commands)
    assert any('tests/test_glossary.py' in cmd for cmd in commands)
