"""Compile an isolated design prototype from the canonical registry, without touching site/."""
from __future__ import annotations
import gzip
import hashlib
import html
import json
import re
from pathlib import Path
import yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
REGISTRY=ROOT/'config/market_reference.yml'
raw=yaml.safe_load(REGISTRY.read_text())
assert raw['schema']=='mastermind.market_reference/v1'
entries=raw['entries']
assert len({e['id'] for e in entries})==len(entries)
for entry in entries:
    assert entry['authority_ceiling']=='reference_only'
    for language in ['en','zh']:
        assert entry['label_'+language] and entry['short_definition_'+language]
    assert re.fullmatch(r'[a-z0-9_-]+\.html(?:#[a-zA-Z0-9_-]+)?',entry['owner_ref']),entry['owner_ref']

fallback=''.join(f'<details id="fallback-{html.escape(e["id"])}"><summary>{html.escape(e["label_en"])} / {html.escape(e["label_zh"])}</summary><p>{html.escape(e["short_definition_en"])}</p><p lang="zh">{html.escape(e["short_definition_zh"])}</p><p><a href="https://www.mastermind-x.com/{html.escape(e["owner_ref"])}">Open the owning dashboard</a></p></details>' for e in entries)
registry=json.dumps({'entries':entries,'coverage_exceptions':raw.get('coverage_exceptions',[])},ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
content='''<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="color-scheme" content="light dark"><title>Market Guide — interactive design prototype</title><style>__CSS__</style></head><body><a class="skip" href="#main">Skip to guide</a><header><a class="brand" href="#" id="brand" style="text-decoration:none;color:var(--text)"><span class="mark">M</span>MASTERMIND</a><span class="prototype-note">Market Guide · Design prototype · No live data</span><nav aria-label="Prototype preferences"><button id="language" class="pill" type="button">中文</button><button id="theme" class="pill" type="button">Dark</button></nav></header><main id="main"><div id="app" class="js-only"></div><section class="fallback"><h1>Market Guide / 市场指南</h1><p>Definitions, not current readings. Open a term to learn more. / 指标说明，非实时读数。</p>__FALLBACK__</section></main><dialog id="help" aria-labelledby="help-title"></dialog><script id="registry" type="application/json">__REGISTRY__</script><script>__JS__</script></body></html>'''
content=content.replace('__CSS__',(HERE/'prototype.css').read_text()).replace('__JS__',(HERE/'prototype.js').read_text()).replace('__FALLBACK__',fallback).replace('__REGISTRY__',registry)
(HERE/'prototype.html').write_text(content)
manifest={'kind':'design-prototype-not-production','registry_sha256':hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),'entry_count':len(entries),'prototype_sha256':hashlib.sha256(content.encode()).hexdigest(),'prototype_bytes':len(content.encode()),'prototype_gzip_bytes':len(gzip.compress(content.encode(),mtime=0)),'source_pin':'ff90f9beacb5109e43848faf0a76e45060bd07f9','live_values':False,'full_production_validator':'NOT_RUN: owner page visibility requires the rendered site; no production acceptance claimed'}
(HERE/'prototype-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest))
