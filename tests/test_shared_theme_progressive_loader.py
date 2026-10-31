"""Shared loader source regressions run through the normal pytest CI owner."""
from pathlib import Path
import subprocess

def test_actual_shared_theme_progressive_loader():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(['node', str(root / 'tests/test_shared_theme_progressive_loader.cjs')], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_page_preserves_auth_boot_before_finance_starts():
    from jinja2 import Environment, FileSystemLoader
    root = Path(__file__).resolve().parents[1]
    source = Environment(loader=FileSystemLoader(str(root / 'templates'))).get_template(
        'government_revenue.html.j2').render(payload_json='{}')
    assert source.index('<script data-sync src="supabase.js">') < source.index('<script data-sync src="theme.js">') < source.index('<script data-sync src="government-revenue-investor-start.js">')
