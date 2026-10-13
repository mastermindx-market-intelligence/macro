"""First-paint packaging keeps source comments, executable JS and all data."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader
from scripts import build_government_revenue as owner

ROOT = Path(__file__).resolve().parents[1]

def runtime(html):
    return next(b for b in re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.S)
                if '__hydrateGovernmentWorkspace' in b)

def executable(text):
    # Keep every newline (and therefore JS automatic-semicolon boundaries).
    text = re.sub(r'(?m)^(\s*)//[^\n]*$', lambda m: m.group(1) + '//', text)
    return '\n'.join(line.rstrip() for line in text.splitlines())

def test_source_and_generated_executable_runtime_are_identical():
    source = (ROOT/'templates/government_revenue.html.j2').read_text()
    rendered = Environment(loader=FileSystemLoader(str(ROOT/'templates')), autoescape=True).get_template(
        'government_revenue.html.j2').render(payload_json='{"companies":[]}', as_of=None, known_at=None)
    assert executable(runtime(source)) == executable(runtime(rendered))
    if shutil.which('node'):
        for js in (runtime(source), runtime(rendered)):
            subprocess.run(['node','--check'], input=js, text=True, capture_output=True, check=True)

def test_actual_projection_preserves_full_canonical_twins_and_projected_data(tmp_path):
    (tmp_path/'templates').symlink_to(ROOT/'templates', target_is_directory=True)
    payload = {'companies':[], 'as_of':'2026-10-13T08:55:00Z', 'known_at':'2026-10-13T08:50:00Z',
               'source_note':'Unmodified bilingual source context / 原始来源背景'}
    canonical = json.dumps(payload, ensure_ascii=False)
    html, latest = owner._write_site_projection(tmp_path, payload, latest_raw=canonical, workspace_raw='{"untouched":true}')
    assert latest.read_text() == canonical
    assert (tmp_path/'site/government-revenue-data/workspace.json').read_text() == '{"untouched":true}'
    embedded = re.search(r'<script id="gov-data" type="application/json">(.*?)</script>', html.read_text(), re.S).group(1)
    assert json.loads(embedded) == owner._display_payload(payload)
    assert owner.RAW_HTML_BUDGET_BYTES == 311296
    assert html.stat().st_size <= owner.RAW_HTML_BUDGET_BYTES
