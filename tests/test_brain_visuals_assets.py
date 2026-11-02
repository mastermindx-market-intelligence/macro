"""Delivery contracts for the native widget's two public presentation assets."""
import ast
import hashlib
import re
import shlex
from pathlib import Path

import yaml

from lib import site_assets

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ('mm_brain.js', 'mm_brain_visuals.js', 'mm_brain_visuals.css',
          'mm_brain_presentation.js', 'mm_brain_markdown.js', 'mm_brain_finance.js',
          'mm_brain_finance.css', 'mm_brain_finance_math_v1.js', 'mm_brain_math.js')


def test_visual_assets_are_public_code_not_a_new_public_data_route():
    policy = yaml.safe_load((ROOT/'config/site_access.yml').read_text())
    assets = {'/'+name for name in ASSETS}
    assert assets <= set(policy['public']['exact'])
    caddy = (ROOT/'app/deploy/Caddyfile').read_text()
    for matcher in ('reg_asset', 'reg_asset_err', 'public_static', 'public_versioned'):
        block = re.search(rf'@{matcher}\s*\{{(.*?)^\s*\}}', caddy, flags=re.S|re.M)
        assert block, matcher
        directive = 'not path' if matcher.startswith('reg_') else 'path'
        paths = {p for line in block.group(1).splitlines() if line.lstrip().startswith(directive+' ')
                 for p in shlex.split(line.lstrip().removeprefix(directive).strip())}
        assert assets <= paths, matcher
        assert '/api/brain/*' not in paths
    assert not any(p.startswith('/api/brain') for p in policy['public']['exact'])


def test_both_widget_builders_emit_the_exact_native_asset_set(tmp_path):
    # Inspect the real builder's copy tuple, not a parallel test-only registry.
    tree = ast.parse((ROOT/'scripts/build_site.py').read_text())
    copies = [node for node in ast.walk(tree) if isinstance(node, ast.For)
              and isinstance(node.target,ast.Name) and node.target.id == 'asset'
              and isinstance(node.iter,ast.Tuple)]
    assert any(set(ASSETS) <= {elt.value for elt in node.iter.elts if isinstance(elt,ast.Constant)} for node in copies)
    module = ast.parse((ROOT/'scripts/build_mastermind.py').read_text())
    declared = next(node.value for node in module.body if isinstance(node,ast.Assign)
                    and any(isinstance(t,ast.Name) and t.id == 'ASSETS' for t in node.targets))
    assert set(ASSETS) <= set(ast.literal_eval(declared))
    for name in ASSETS:
        source = ROOT/'templates'/name
        site_assets.copy_asset(name, source, tmp_path)
        assert (tmp_path/name).read_bytes() == source.read_bytes() == (ROOT/'site'/name).read_bytes()


def test_lazy_urls_use_the_same_per_asset_content_hash_as_the_site_pipeline():
    script=(ROOT/'templates/mm_brain.js').read_text()
    for extension,key in [('js','visualScriptVersion'),('css','visualStyleVersion')]:
        expected=hashlib.sha256((ROOT/f'templates/mm_brain_visuals.{extension}').read_bytes()).hexdigest()[:8]
        assert f"var {key} = '{expected}';" in script
        assert f"mm_brain_visuals.{extension}?v=' + {key}" in script
    assert 'script.charset = \'utf-8\'' in script


def test_theme_is_baked_by_its_existing_owner_not_raw_copied():
    source=ROOT/'templates/theme.js'
    emitted=site_assets.emit_theme_js(source)
    expected=hashlib.sha256((ROOT/'templates/mm_brain.js').read_bytes()).hexdigest()[:8]
    # The canonical owner now minifies the final bundle; verify the baked value,
    # not whitespace that the required minifier deliberately removes.
    assert f'MM_BRAIN_VER="{expected}"' in emitted
    assert site_assets.SUPABASE_TOKEN not in emitted
    assert 'window.MDXTerminalOverlay' in emitted
