"""Render the shared guide consumer for isolated qualification, never site publication.

Production data must enter through scripts.build_market_reference's validators.
The fixture option is explicitly marked in both the HTML and the run receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from lib.market_guide import compile_guide, script_json


def render_html(manifest: dict, *, fixture_only: bool = False) -> str:
    """The full page and inline dialog use the exact same serialized record."""
    css = (HERE / 'prototype.css').read_text() + '\n' + (HERE / 'guide-view.css').read_text()
    scripts = (HERE / 'guide-client.js').read_text() + '\n' + (HERE / 'guide-view.js').read_text()
    fallback = []
    for record in manifest['entries']:
        title = html.escape(record['label']['en'] + ' / ' + record['label']['zh'])
        content = []
        for language in ['en', 'zh']:
            content.append(f'<p lang="{language}">{html.escape(record["definition"][language])}</p>')
            content.append(f'<p lang="{language}">{html.escape(record["why"][language])}</p>')
            if record['basis']:
                content.append(f'<p lang="{language}">{html.escape(record["basis"][language])}</p>')
            content.extend(f'<p lang="{language}">{html.escape(reading["text"][language])}</p>' for reading in record['presentation']['readings'])
            content.extend(f'<p lang="{language}">{html.escape(caveat)}</p>' for caveat in record['caveats'][language])
        content.extend(f'<p><a href="{html.escape(url, quote=True)}" rel="noopener noreferrer">{html.escape(url)}</a></p>' for url in record['public_source_refs'])
        fallback.append(f'<details id="fallback-{html.escape(record["id"], quote=True)}"><summary>{title}</summary>{"".join(content)}</details>')
    banner = ('Synthetic fixtures · Interaction test only · Not production data / 合成测试数据 · 非生产数据' if fixture_only
              else 'Source-backed review candidate · No live values · Not deployed / 来源支持的审查候选 · 非实时数据 · 尚未部署')
    return f'''<!doctype html>
<html lang="en" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Market Guide — shared consumer qualification</title><style>{css}</style></head>
<body><a class="skip" href="#app">Skip to guide / 跳转至指南</a><header><div class="brand"><span class="mark">M</span>MASTERMIND</div><span class="prototype-note">Market Guide · Review candidate</span><nav aria-label="Preview preferences"><button id="language" class="pill" type="button">中文</button><button id="theme" class="pill" type="button">Dark</button></nav></header>
<div class="guide-scope-note" data-fixture-only="{str(fixture_only).lower()}">{banner}</div>
<main><div id="app" hidden></div><section class="fallback"><h1>Market Guide / 市场指南</h1><p>Definitions, not live values. / 定义说明，非实时读数。</p>{''.join(fallback)}</section></main>
<dialog id="help" aria-labelledby="help-title"></dialog><script id="guide-manifest" type="application/json">{script_json(manifest)}</script>
<script>{scripts}\ntry {{ globalThis.guideApp=MastermindGuideView.mount({{host:document.getElementById('app'),dialog:document.getElementById('help'),manifest:JSON.parse(document.getElementById('guide-manifest').textContent),ownerOrigin:location.protocol==='file:'?'https://www.mastermind-x.com':location.origin}}); }} catch(error) {{ document.getElementById('app').hidden=false;document.getElementById('app').textContent='Interactive guide unavailable. Read the definitions below. / 交互指南暂不可用，请阅读下方说明。'; }}</script></body></html>'''


def compile_from_canonical_source() -> dict:
    """No sparse-checkout false green: require each real owner page before validation."""
    import yaml
    from scripts.build_market_reference import validate, validate_coverage_exceptions
    raw = yaml.safe_load((ROOT / 'config/market_reference.yml').read_text())
    pages = {entry['owner_ref'].partition('#')[0] for entry in raw['entries']}
    pages.update(item['surface'] for item in (raw.get('coverage_exceptions') or []))
    missing = sorted(page for page in pages if not (ROOT / 'site' / page).is_file())
    if missing:
        raise ValueError('Rendered owner pages missing; no source-backed qualification: ' + ', '.join(missing))
    return compile_guide(raw, json.loads((HERE / 'guide-presentation.json').read_text()),
                         validate_registry=lambda data: validate(data, repo_root=ROOT),
                         validate_coverage=validate_coverage_exceptions)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture-only', action='store_true', help='Use synthetic test records, prominently labeled. Never qualifies production.')
    parser.add_argument('--output', type=Path, required=True, help='New review HTML path outside site/. Existing files are not overwritten.')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or output.is_relative_to((ROOT / 'site').resolve()):
        parser.error('Use a new review path outside the production site directory')
    if args.fixture_only:
        raw = json.loads((ROOT / 'tests/fixtures/market-guide/synthetic-source.json').read_text())
        manifest = compile_guide(raw, json.loads((HERE / 'guide-presentation.json').read_text()),
                                 validate_registry=lambda data: data['entries'],
                                 validate_coverage=lambda data, entries: (data.get('coverage_exceptions') or []))
    else:
        manifest = compile_from_canonical_source()
    content = render_html(manifest, fixture_only=args.fixture_only)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as file:
        file.write(content)
    print(json.dumps({'output': str(output), 'fixture_only': args.fixture_only, 'entries': len(manifest['entries']),
                      'content_revision': manifest['content_revision'], 'sha256': hashlib.sha256(content.encode()).hexdigest(),
                      'production_changed': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
